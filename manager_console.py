from queue_model import *

HELP = """stop - stop manager
pause - pause manager
continue - unpause manager
db - print queue data base
state - print manager queue and current frame processor tasks"""

class Console:
    def __init__(self, manager):
        self.manager = manager
    
    @staticmethod
    def print_table(data, keys):
        max_len = {}
        for key in keys:
            max_len[key] = max([len(str(line[key])) for line in data])
            if len(key) > max_len[key]:
                max_len[key] = len(key)
            max_len[key] += 5
        Console.print_row(keys, keys, max_len)
        for line in data:
            Console.print_row(list(line.values()), keys, max_len)
    
    @staticmethod
    def print_row(args, keys, max_len):
        for i, key in enumerate(keys):
            print('{arg:<{len_}}'.format(arg=args[i], len_=max_len[key]), end='')
        print()
       
    def print_manager_state(self):
        print('Frame processor tasks:')
        for fp in self.manager.frame_processors:
            print('    {}:{}'.format(fp.name, fp.current_qid))
        print('Manager queue:')
        for cl in self.manager.camera_listeners:
            print('    {}'.format(cl.qid)) 
        
    def launch(self):
        assert not self.manager.stopped, 'Tryed to start manager after it was stopped'
        if not self.manager.running:
            self.manager.start()
        while True:
            line = input('(User):')
            cid, *args = line.split()
            if cid == 'help':
                print(HELP)
            elif cid == 'stop':
                self.manager.stop()
                break
            elif cid == 'pause':
                self.manager.pause()
            elif cid == 'continue':
                self.manager.continue_()
            elif cid == 'db':
                data = list(QueueModel.select().dicts())
                if args != []:
                    keys = args
                else:
                    keys = list(data[0].keys())
                try:
                    Console.print_table(data, keys)
                except KeyError:
                    print('Unknown collumns')
            elif cid == 'state':
                self.print_manager_state()
            else:
                print('Unknown command')