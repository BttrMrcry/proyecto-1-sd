import socket
import json
import time
from threading import Thread, Lock
from enum import Enum
from fake_time import fakeTimer

MAX_SELECTION_DIFFERENCE = 500

class MessageAtributes(Enum):
    TYPE = 'type'
    DATA = 'data'

class MessageTypes(Enum):
    TIME_RESPONSE = 'time_response'
    ENROLLMENT_REQUEST = 'enrollment'
    CORRECTION = 'correction'
    TIME_REQUEST = 'time_request'
    LIST_UPDATE = 'list_update'

class TimeResponseData(Enum):
    TIME = 'time'

class TimeCorrectionData(Enum):
    CORRECTION = 'correction'

class EnrollmentRequestData(Enum):
    INTENTIONAL_DELAY = 'delay'

class UpdateCurrentClientList(Enum):
    UPDATE_CLIENT_LIST = 'update_client_list'


class SyncServer:
    def __init__(self, port: int = 8000, host:str = '', timeout:int = 1):
        self.__timer = fakeTimer()
        self.__timer.start_timer()
        self.__port = port
        self.__host = host
        self.__print_lock = Lock()
        self.__client_sockets = list[dict]()
        self.__client_list_lock = Lock()
        self.__timeout = timeout
        self.__current_client_list = list[dict]()

    def __listen_for_client(self, server_socket: socket.socket):
        while True:
            # accepting a client
            client_connector, addr = server_socket.accept()
            str_message = client_connector.recv(1024).decode()
            message = json.loads(str_message)
            intentional_delay = 0
            try:
                if message[MessageAtributes.TYPE.value] == MessageTypes.ENROLLMENT_REQUEST.value:
                    intentional_delay = message[MessageAtributes.DATA.value][EnrollmentRequestData.INTENTIONAL_DELAY.value]
                else:
                    with self.__print_lock:
                        print(f'Bad enrollment request from {addr}')
                    client_connector.close()
                    continue
            except:
                with self.__print_lock:
                    print(f'Bad enrollment request from {addr}')
                client_connector.close()
                continue
            
            client_connector.settimeout(self.__timeout)
            
            with self.__client_list_lock:
                self.__client_sockets.append(
                    {
                        'socket': client_connector,
                        'time': 0,
                        'still_active': True,
                        'intentional_delay': intentional_delay,
                        'address': addr,
                        'one_way_trip': 0
                    }
                )
                self.__update_current_client_list()
            with self.__print_lock:
                print(f'{addr} is now in the syncronization list')
    
    def __request_time(self, client: dict):
        message = {
            MessageAtributes.TYPE.value: MessageTypes.TIME_REQUEST.value
        }
        str_message = json.dumps(message)
        time.sleep(client['intentional_delay'])
        try:
            client['socket'].send(str_message.encode())
        except:
            client['still_active'] = False
        
    def __receive_time(self, client: dict, start_time: int):
        end_time = 0
        try:
            str_answer = client['socket'].recv(1024).decode()
            end_time = self.__timer.get_time()
        except:
            client['still_active'] = False
            return
    
        answer = json.loads(str_answer)
        received_time = 0
        try:
            if answer[MessageAtributes.TYPE.value] == MessageTypes.TIME_RESPONSE.value:
                received_time = answer[MessageAtributes.DATA.value][TimeResponseData.TIME.value]
        except:
            client['still_active'] = False
            return
        one_way_trip = (end_time - start_time) // 2
        server_time = self.__timer.get_time() 
        client['time'] = (received_time + one_way_trip) - server_time
        client['one_way_trip'] = one_way_trip
    
    def __send_correction(self, client: dict, correction: int):
        message = {
            MessageAtributes.TYPE.value: MessageTypes.CORRECTION.value,
            MessageAtributes.DATA.value: {
                TimeCorrectionData.CORRECTION.value: correction
            }
        }
        str_message = json.dumps(message)
        time.sleep(client['intentional_delay'])
        client['socket'].send(str_message.encode())
    
    def __syncronize(self):
        with self.__print_lock:
            print('starting sync round')
        with self.__client_list_lock:
            start_time_request = self.__timer.get_time()
            for client in self.__client_sockets:
                t = Thread(target= self.__request_time, args = (client,))
                t.start()
            threads = [Thread(target = self.__receive_time, args=(client, start_time_request))  for client in self.__client_sockets]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            #If we do not receive a response we mark the sockets as inactive
            still_connected:list[dict] = list(filter(lambda x: x['still_active'] == True, self.__client_sockets))
            valid_for_avg = list(filter(lambda x: abs(x['time']) < MAX_SELECTION_DIFFERENCE, still_connected))
            
            if not valid_for_avg:
                avg_difference = 0
            else:
                sum_time = sum([client['time'] for client in valid_for_avg])
                avg_difference = sum_time//(len(valid_for_avg) + 1)
            
            
            for client in still_connected:
                correction = -client['time'] + avg_difference
                t = Thread(target=self.__send_correction, args=(client, avg_difference + correction))
                t.start()
            
            self.__timer.set_time(self.__timer.get_time() + avg_difference)
            #Cleaning of socket list
            disconnected:list[dict] = list(filter(lambda x: x['still_active'] == False, self.__client_sockets))
            #update socket list to only responsive sockets
            self.__client_sockets = still_connected
            #close connection with unresponsive clients
            self.__update_current_client_list()
            
            with self.__print_lock:
                print(f'{len(disconnected)} were dropped')
                print(f'{len(still_connected)} were syncronized')
                for client in disconnected:
                    print(f'{client["address"]} did not respond and was dropped from the sync list')
                    client['socket'].close()
                for client in still_connected:
                    print(f'client {client["address"]} received time: {client["time"]}. One way trip: {client["one_way_trip"]}')
    

    def start_server(self):
        s = socket.socket()
        with self.__print_lock:
            print('socket created')
        s.bind((self.__host, self.__port))
        s.listen(5)
        with self.__print_lock:
            print('socket is listening...')
        #wait for conections
        listener = Thread(target=self.__listen_for_client, name='listening thread', args=[s])
        listener.start()  
        #update clients time periodically
        updater = Thread(target = self.__update_time_periodicaly, args = ())
        updater.start()
    
    def __update_time_periodicaly(self, period:int = 60, intentional_delay:int = 0):
        while True:
            self.__syncronize()
            time.sleep(period)
    
    def __update_current_client_list(self):
        self.__current_client_list.clear
        for client in self.__client_sockets:
            self.__current_client_list.append(
                {
                    'socket' : client['socket'].getsockname()[1],
                    'address' : client['address']
                }
            )

        message = {
            MessageAtributes.TYPE.value: MessageTypes.LIST_UPDATE.value,
            MessageAtributes.DATA.value: {
                UpdateCurrentClientList.UPDATE_CLIENT_LIST.value : self.__current_client_list
            }
        }
        str_message = json.dumps(message)

        for client in self.__client_sockets:
            client['socket'].send(str_message.encode())


class SyncClient:
    def __init__(self, port: int = 8000, host:str = '127.0.0.1', intentional_delay:int = 0):
        self.timer = fakeTimer()
        self.timer.start_timer()
        self.__print_lock = Lock()
        self.__port = port
        self.__host = host
        self.__intentional_delay = intentional_delay
        self.__client_list = list[dict]()
        self.__my_port : int
        self.__my_host : str

    def start_syncronizing(self):
        listener = Thread(target=self.__listen_for_message, args=())
        listener.start()
        while len(self.__client_list) > 0:
            client = self.__client_list.pop(0)
            if client['socket'] == self.__my_port and client['address'] == self.__my_host:
                return [self.__my_port, self.__my_host]
            else:
                time.sleep(60)
                self.__port = client['socket']
                self.__host = client['address']
                newListener = Thread(target=self.__listen_for_message, args=())
                newListener.start()


    def __enroll_to_server(self):
        self.__socket = socket.socket()
        with self.__print_lock:
            print('socket created')
        time.sleep(self.__intentional_delay)
        self.__socket.connect((self.__host, self.__port))
        message = {
            MessageAtributes.TYPE.value: MessageTypes.ENROLLMENT_REQUEST.value,
            MessageAtributes.DATA.value: {
                EnrollmentRequestData.INTENTIONAL_DELAY.value: self.__intentional_delay
            }
        }
        str_message = json.dumps(message)
        self.__socket.send(str_message.encode())
        self.__my_host = self.__socket.getsockname()[0]
        self.__my_port = self.__socket.getsockname()[1]
        with self.__print_lock:
            print('Connected to server')

   
    def __send_time(self):
            cur_time = self.timer.get_time()
            message = {
                MessageAtributes.TYPE.value: MessageTypes.TIME_RESPONSE.value,
                MessageAtributes.DATA.value: {
                    TimeResponseData.TIME.value: cur_time
                }
            }
            str_message = json.dumps(message)
            time.sleep(self.__intentional_delay)
            self.__socket.send(str_message.encode())
            with self.__print_lock:
                print(f'Time {cur_time} was send to the server')

    def __fix_time(self, message: dict):
        old_time = self.timer.get_time()
        correction = message[MessageAtributes.DATA.value][TimeCorrectionData.CORRECTION.value]
        new_time = old_time + correction
        self.timer.set_time(new_time)
        with self.__print_lock:
            print(f'Correction received from server. Old time: {old_time} -> New time: {new_time}. Correction: {correction}')

    def __update_client_list(self, message: dict):
        self.__client_list = message[MessageAtributes.DATA.value][UpdateCurrentClientList.UPDATE_CLIENT_LIST.value]


    def __listen_for_message(self):
        self.__enroll_to_server()
        timeout = time.time() + 90
        while time.time() > timeout:
            request = self.__socket.recv(1024).decode()
            if not request:
                print('Something is wrong with the connection')
                return 
            
            message = json.loads(request)
            try:
                message_type = message[MessageAtributes.TYPE.value]
            except:
                print('Something is wring with the connection')
                return
            
            match message_type:
                case MessageTypes.TIME_REQUEST.value:
                    t = Thread(target=self.__send_time(), args=())
                    t.start()
                    timeout = time.time() + 90
                case MessageTypes.CORRECTION.value:
                    self.__fix_time(message)
                    timeout = time.time() + 90
                case MessageTypes.LIST_UPDATE.value:
                    self.__update_client_list(message)
                    timeout = time.time() + 90
        

