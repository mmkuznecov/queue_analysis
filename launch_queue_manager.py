from queue_model import *
from queue_manager import Manager, CameraListener
from manager_console import Console
import logging
import time
import os

#It is an example, not a proper way to work with this process.
if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read("config.ini")
    log_dir             = config['Path']['log_dir']
    mask_dir            = config['Path']['mask_dir']
    model_path          = config['Manager']['model_path']
    n_threads           = int(config['Manager']['n_threads'])
    exception_delay     = int(config['Manager']['exception_delay'])
    connection_attempts = int(config['CameraListener']['connection_attempts'])
    capture_delay       = int(config['CameraListener']['capture_delay'])
    
    logging.basicConfig(filename=os.path.join(log_dir, f'{time.time()}.txt'), level=logging.INFO)

    camera_listeners = []
    for queue in QueueModel.select():
        qid = queue.id
        camera_url = queue.camera_url
        mask_path = os.path.join(mask_dir, queue.mask_path)
        camera_listeners.append(CameraListener(qid, camera_url, logging, mask_path,
                                               connection_attempts, capture_delay))
    
    manager = Manager(camera_listeners, update_info, n_threads, model_path, exception_delay, logging)
    
    console = Console(manager)
    console.launch()