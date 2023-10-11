import time
from threading import Thread, Lock


class fakeTimer:
    def __init__(self):
        self.__should_timer_run = False
        self.__i_time = 0
        self.__fake_timer_lock = Lock()
    
    def __run_timer(self):
        while True:
            time.sleep(0.002)
            with self.__fake_timer_lock:
                if self.__should_timer_run:
                    self.__i_time += 1
                else:
                    break
        return

    def start_timer(self):
        with self.__fake_timer_lock:
            if self.__should_timer_run:
                print("timer already running")
            else:
              self.__should_timer_run = True
        t = Thread(target= self.__run_timer, name = 'Timer_counter', args=())
        t.start()
    
    def stop_timer(self):
        with self.__fake_timer_lock:
            self.__should_timer_run = False

    def get_time(self) -> int:
        result = 0
        with self.__fake_timer_lock:
            result = self.__i_time
        return result
    def set_time(self, new_time:int):
        with self.__fake_timer_lock:
            self.__i_time = new_time
