import time
import os
from fchd.src.head_detector_vgg16 import Head_Detector_VGG16
from fchd.trainer import Head_Detector_Trainer
import numpy as np
from fchd.data.dataset import preprocess
import fchd.src.array_tool as at
import fchd.src.utils as utils
from threading import Thread, Lock, Event
import cv2
from collections import deque

THRESH = 0.02

class Manager(object):
    def __init__(self, camera_listeners, data_base_update_info, n_threads,
                 model_path, exception_delay, logging):
        self.n_threads = n_threads
        self.camera_listeners = deque()
        self.camera_listeners_put_lock = Lock()
        self.camera_listeners_get_lock = Lock()
        for cl in camera_listeners:
            self.camera_listeners.append(cl)
        self.logging = logging
        self.data_base_update_info = data_base_update_info
        self.data_base_lock = Lock()
        self.frame_processors = [FrameProcessor(self, exception_delay, model_path) for _ in range(n_threads)]
        self.running = False
        self.stopped = False
        self.paused = Event()
        self.paused.set()
        
    def start(self):
        if not self.stopped:
            if not self.running:
                self.running = True
                self.logging.info(f'Starting manager...')
                for cl in self.camera_listeners:
                    cl.captureVideo()
                for fp in self.frame_processors:
                    fp.start()
                self.logging.info(f'Manager started working')
            else:
                self.logging.error(f'Tryed to start manager, while it was already working')
        else:
            self.logging.error(f'Tryed to start manager after it was stopped')

    def stop(self):
        if not self.stopped:
            if self.running:
                self.logging.info(f'Stopping manager work...')
                self.continue_()
                for fp in self.frame_processors:
                    fp.stop()
                    fp.join()
                for cl in self.camera_listeners:
                    cl.releaseVideo()
                self.running = False
                self.stopped = True
                self.logging.info(f'Manager stopped working')
            else:
                self.logging.error(f'Tryed to stop manager, while it wasn\'t working')
        else:
            self.logging.error(f'Tryed to stop manager after it was stopped')
            
    def pause(self):
        if self.paused.isSet():
            self.paused.clear()
            self.logging.info(f'Manager work paused')
        
    def continue_(self):
        if not self.paused.isSet():
            self.paused.set()
            self.logging.info(f'Manager work continued')
        
class FrameProcessor(Thread):
    def __init__(self, manager, exception_delay, model_path):
        Thread.__init__(self)
        self.manager = manager
        self.exception_delay = exception_delay
        self.running = True
        self.head_detector = Head_Detector_VGG16(ratios=[1], anchor_scales=[2,4])
        self.trainer = Head_Detector_Trainer(self.head_detector).cuda()
        self.trainer.load(model_path)
        self.current_qid = None

    def stop(self):
        self.running = False
    
    def run(self):
        self.running = True
        while self.running and self.manager.running:
            self.manager.paused.wait()
            self.manager.camera_listeners_get_lock.acquire()
            try:
                if len(self.manager.camera_listeners) > 0:
                    camera_listener = self.manager.camera_listeners.pop()
                    self.current_qid = camera_listener.qid
                else:
                    camera_listener = False
            except:
                camera_listener = False
                self.manager.logging.error(f'Got unexpected error while getting camera listner from manager queue')
                time.sleep(self.exception_delay)
            finally:
                self.manager.camera_listeners_get_lock.release()
            
            if camera_listener:
                ret, frame = camera_listener.getFrame()
                if ret:
                    number_of_people = self.processFrame(frame)
                    if number_of_people is not None:
                        self.manager.data_base_lock.acquire()
                        try:
                            self.manager.data_base_update_info(camera_listener.qid, number_of_people, time.time())
                        except:
                            self.manager.logging.error(f'Got unexpected error while updating data base')
                            time.sleep(self.exception_delay)
                        finally:
                            self.manager.data_base_lock.release()

                self.manager.camera_listeners_put_lock.acquire()
                try:
                    self.manager.camera_listeners.appendleft(camera_listener)
                except:
                    self.manager.logging.error(f'Got unexpected error while putting camera listner into manager queue')
                    time.sleep(self.exception_delay)
                finally:
                    self.manager.camera_listeners_put_lock.release()
                    self.current_qid = None
            else:
                time.sleep(self.exception_delay)
                
    def processFrame(self, f):
        f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        img_raw = np.asarray(f, dtype=np.uint8)
        img_raw_final = img_raw.copy()
        img = np.asarray(f, dtype=np.float32)
        _, H, W = img.shape
        img = img.transpose((2,0,1))
        img = preprocess(img)
        _, o_H, o_W = img.shape
        scale = o_H / H
        img = at.totensor(img)
        img = img[None, : ,: ,:]
        img = img.cuda().float()

        pred_bboxes_, _ = self.head_detector.predict(img, scale, mode='evaluate', thresh=THRESH)
        
        k = f.shape[0]/img.shape[2]
        for i in range(pred_bboxes_.shape[0]):
            ymin, xmin, ymax, xmax = map(lambda x: x*k, pred_bboxes_[i,:])
            utils.draw_bounding_box_on_image_array(f, ymin, xmin, ymax, xmax)
        f = cv2.cvtColor(f, cv2.COLOR_RGB2BGR)
        cv2.imwrite(f'processed_frames//{self.current_qid}.jpg', f)
        
        return pred_bboxes_.shape[0]

class CameraListener(object):
    def __init__(self, qid, url, logging, mask_path=None, frame_size=None,
                 connection_attempts=3, capture_delay=3600):
        self.qid = qid
        self.url = url
        self.logging = logging
        self.frame_size = frame_size
        self.connection_attempts = connection_attempts
        self.capture_delay = capture_delay
        self.mask = cv2.imread(mask_path, 0)  if (mask_path is not None) else None
        self.time_cpatured = None
        self.capture = False
        
    def captureVideo(self):
        for attempt in range(self.connection_attempts):
            cap = cv2.VideoCapture(self.url)
            if cap.isOpened():
                self.logging.info(f'Successfully captured video from \'{self.qid}\'')
                self.capture = cap
                self.time_cpatured = time.time()
                return True
        self.logging.error(f'Failed to capture video from \'{self.qid}\'')
        self.capture = False
        return False
    
    def releaseVideo(self):
        if self.capture:
            self.capture.release()
            self.capture = False
    
    def handleReadingError(self):
        if not self.capture or not self.capture.isOpened():
            if (self.time_cpatured is None 
                or time.time() - self.time_cpatured >= self.capture_delay):
                return self.captureVideo()
        return False
        
    def getFrame(self):
        if self.capture and self.capture.isOpened():
            ret, frame = self.capture.read()
            if self.mask is not None:
                if self.mask.shape != frame.shape[:2]:
                    self.mask = cv2.resize(self.mask, frame.shape[1::-1])
                frame = cv2.bitwise_and(frame, frame, mask=self.mask)
            return ret, frame
        if self.handleReadingError():
            return self.getFrame()
        else:
            self.logging.error(f'Cannot read frame from \'{self.qid}\'')
            return False, None