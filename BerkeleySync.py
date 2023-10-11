import socket
import json
import time
from threading import Thread, Lock
from enum import Enum
from fake_time import fakeTimer

## solicitud de subscripción
## Solicitud al cliente de su tiempo
## envio de la corrrección de tiempo


MAX_SELECTION_DIFFERENCE = 500


class MessageType(Enum):
    TIME_RESPONSE = 'time_response'
    CORRECTION = 'correction'
    TIME_REQUEST = 'time_request'

class SyncServer:
    def __init__(self, port: int = 8000, host:str = ''):
        self.__timer = fakeTimer()
        self.__timer.start_timer()
        self.__port = port
        self.__host = host
        self.__print_lock = Lock()
        self.__client_sockets = list[dict]()
        self.__client_list_lock = Lock()

    def __listen_for_client(self, server_socket: socket.socket):
        while True:
            # accepting a client / slave clock client
            client_connector, addr = server_socket.accept()
            client_address = str(addr[0]) + ":" + str(addr[1])
            print(client_address + " got connected successfully")
            with self.__client_list_lock:
                self.__client_sockets.append(
                    {
                        'socket': client_connector,
                        'time': 0,
                        'still_active': True
                    }
                )
    
    def __request_time(self, socket: socket.socket, intentional_delay: int = 0):
        socket.send(MessageType.TIME_REQUEST.value.encode())

    def __send_time(self, socket: socket.socket, message: str, intentional_delay: int = 0):
        socket.send(message.encode())
    def __syncronize(self, intentional_delay: int = 0):
        with self.__client_list_lock:
            for client in self.__client_sockets:
                t = Thread(target=self.__request_time, args=[client['socket'], intentional_delay])
                t.start()
        time.sleep(1)
        with self.__client_list_lock:
            for client in self.__client_sockets:
                str_answer = client['socket'].recv(1024).decode()
                if not str_answer:
                    client['still_active'] = False
                    continue
                else:
                    answer = json.loads(str_answer)
                    received_time = 0
                    try:
                        receibed_time = answer[MessageType.TIME_RESPONSE.value]
                    except:
                        client['still_active'] = False
                        continue
                    client['time'] = received_time
        still_connected = list()
        with self.__client_list_lock:
            still_connected:list[dict] = list(filter(lambda x: x['still_active'] == True, self.__client_sockets))
        current_server_time = self.__timer.get_time()
        valid_for_avg = list(filter(lambda x: abs(x['time'] - current_server_time) < MAX_SELECTION_DIFFERENCE, still_connected))
        sum_time = sum([client['time'] for client in valid_for_avg]) + current_server_time
        avg_time = sum_time//(len(valid_for_avg) + 1)

        
        for client in still_connected:
            correction = avg_time - client['time']
            message = {
                MessageType.CORRECTION.value: correction
            }
            str_message = json.dumps(message)
            t = Thread(target=self.__send_time, args=[client['socket'], str_message, intentional_delay])
            t.start()

        
    def start_server(self):
        s = socket.socket()
        print('socket created')
        s.bind((self.__host, self.__port))
        s.listen(5)
        print('socket is listening...')
        #wait for conections
        t = Thread(target=self.__listen_for_client, name='listening thread', args=[s])
        t.start()  

    def update_time_periodicaly(self, period:int = 60, intentional_delay:int = 0):
        while True:
            self.__syncronize(intentional_delay=intentional_delay)
            time.sleep(period)

class SyncClient:
    def __init__(self, port: int = 8000, host:str = '127.0.0.1'):
        self.timer = fakeTimer()
        self.timer.start_timer()
        self.__print_lock = Lock()
        self.__port = port
        self.__host = host

    def __enroll_to_server(self):
        self.__socket = socket.socket()
        print('socket created')
        self.__socket.connect((self.__host, self.__port))
   
    def __send_time(self):
            message = {
                MessageType.TIME_RESPONSE
            }
    def __listen_for_updates(self):
        while True:
            request = self.__socket.recv(1024).decode()
            if not request:
                continue
            else:
                message = json.loads(request)
                try:
                    message[MessageType.TIME_REQUEST.value]
                except:
                    continue
            
    
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
