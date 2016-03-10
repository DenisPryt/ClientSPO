import os
import socket
import struct

__author__ = 'Prychkovsky'

SERVER_PORT = 1091
SERVER_ADDRESS = '127.0.0.1'

KEEP_ALIVE_MSG_OOB = b'\x0A'
BYTES_TRANSFERRED_MSG_OOB = b'\x0B'


class Client(object):
    FILE_MSG = b'\x03'
    TIME_MSG = b'\x04'
    ECHO_MSG = b'\x05'
    #COMMANDS_TO_MSG = {'echo': ECHO_MSG, 'time': TIME_MSG, 'file': FILE_MSG}

    def __init__(self):
        self._socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__port = 0
        self.__address = ''

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, port):
        self.__port = port

    @property
    def address(self):
        return self.__address

    @address.setter
    def address(self, address):
        self.__address = address

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._socket_tcp.close()

    def process_command(self, command, answer_timeout=10.0):
        """Try to send message to server according to command"""
        try:
            self._send_command(command)
            self._socket_tcp.settimeout(answer_timeout)
            return self._socket_tcp.recv(1024)
        except socket.timeout:
            return b''
        except (ConnectionAbortedError, ConnectionResetError):
            raise ConnectionAbortedError("Connection Aborted")

    def connect(self, timeout=15.0, max_attempts=5):
        attempt = 0
        while not self._connect(timeout):
            attempt += 1
            if attempt == max_attempts:
                break
            raise ConnectionAbortedError("Can't connect to the server")

    def _connect(self, timeout):
        try:
            serv_endpoint = (self.address, self.port)
            print('Connecting to ', serv_endpoint)
            self._socket_tcp.settimeout(timeout)
            self._socket_tcp.connect(serv_endpoint)
        except socket.timeout:
            print('Timeout')
            return False
        except InterruptedError:
            print('Error')
            return False
        except (ConnectionRefusedError, OSError):
            print("Server Refused connection")
            return False
        else:
            return True

    def _send_command(self, command):
        if command.startswith('echo'):
            self._socket_tcp.send(Client.ECHO_MSG + command[5:].encode() + b'\0')
        elif command.startswith('time'):
            self._socket_tcp.send(Client.TIME_MSG)
        elif command.startswith('file'):
            fpath = command[5:]
            with open(fpath, 'rb') as file:
                self._socket_tcp.settimeout(None)
                self._socket_tcp.send(Client.FILE_MSG)

                fsize = struct.pack('!q', os.path.getsize(fpath))
                fname = fpath.split('/')[-1].encode()
                fnamelen = struct.pack('!h', len(fname))

                self._socket_tcp.send(fnamelen + fname)
                self._socket_tcp.send(fsize)

                while True:
                    chunk = file.read(1024)
                    if chunk is None or chunk == b'':
                        break
                    self._socket_tcp.send(chunk)
        else:
            raise RuntimeError("Unknown command")


def main():
    with Client() as client:
        client.address = SERVER_ADDRESS
        client.port = SERVER_PORT
        client.connect()
        while True:
            command = input('Input command : ')
            if command.startswith('exit'):
                return
            try:
                answer = client.process_command(command)
                if answer == b'':
                    print('No answer')
                elif answer is None:
                    print('Connection Aborted')
                else:
                    print(answer)
            except RuntimeError as err:
                print(err)


if __name__ == '__main__':
    try:
        main()
    except ConnectionAbortedError as err:
        print(err)
