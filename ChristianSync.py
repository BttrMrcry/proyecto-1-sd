import socket
import json
import time
from threading import Thread, Lock
from enum import Enum
from fake_time import fakeTimer

class ResponseElemens(Enum):
    TIME = 'time'

class RequestElements(Enum):
    INTENTIONAL_DELAY = 'delay'

class SyncServer:
    def __init__(self, port: int = 8000, host:str = ''):
        self.__timer = fakeTimer()
        self.__timer.start_timer()
        self.__port = port
        self.__host = host
        self.__print_lock = Lock()

    def __send_time(self, client_connection: socket.socket, address:str):
        received_message:dict[str, int] = json.loads(client_connection.recv(1024).decode())
        intentional_delay:int = 0
        try:
            intentional_delay = received_message[RequestElements.INTENTIONAL_DELAY.value]
        except:
            with self.__print_lock:
                print('The request format is incorrect')
            return
        response_message = {
            ResponseElemens.TIME.value: self.__timer.get_time()
        }
        str_message = json.dumps(response_message, indent=4)
        time.sleep(intentional_delay)
        client_connection.send(str_message.encode())
        client_connection.close()
        with self.__print_lock:
            print(f'Time update send to {address}')

    def start_server(self):
        s = socket.socket()
        print('socket created')
        s.bind((self.__host, self.__port))
        s.listen(5)
        print('socket is listening...')
        
        while True:
            connection, address = s.accept()
            t:Thread = Thread(target = self.__send_time, name = 'sending_thread', args = [connection, address])
            t.start()
            
class SyncClient:
    def __init__(self, port: int = 8000, host:str = '127.0.0.1'):
        self.timer = fakeTimer()
        self.timer.start_timer()
        self.__port = port
        self.__host = host
        self.__print_lock = Lock()
    
    def __update_time(self, intentional_delay: int = 0):
        s = socket.socket()
        print('socket created')
        s.connect((self.__host, self.__port))
        request_message = {
            RequestElements.INTENTIONAL_DELAY.value: intentional_delay
        } 
        str_message = json.dumps(request_message)
        sending_time = self.timer.get_time()
        time.sleep(intentional_delay)
        s.send(str_message.encode())
        server_message:dict[str, int] = json.loads(s.recv(1024).decode())
        response_time = self.timer.get_time()
        server_time = 0
        try:
            server_time = server_message[ResponseElemens.TIME.value]
        except:
            with self.__print_lock:
                print('The server response format is incorrect')
            return
        
        latency = response_time - sending_time
        new_time = server_time + latency // 2
        self.timer.set_time(new_time)
        with self.__print_lock:
            print(f'Previous time: {response_time} -> New time: {new_time}. The one way travel time was: {latency // 2}')
        s.close()

    def update_time_periodicaly(self, period: int, intentional_delay: int = 0):
        while True:
            self.__update_time(intentional_delay)
            time.sleep(period)
