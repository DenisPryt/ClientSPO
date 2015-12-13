import os
import socket as SocketLib
import struct as StructLib
import collections
import time

__author__ = 'Prychkovsky'

SERVER_PORT = 1091
SERVER_ADDRESS = '127.0.0.1'

SERVER_TIMEOUT = 15.0
ANSWER_TIMEOUT = 10.0

FILE_MSG = b'\x03'
TIME_MSG = b'\x04'
ECHO_MSG = b'\x05'

KEEP_ALIVE_MSG_OOB = b'\x0A'
BYTES_TRANSFERRED_MSG_OOB = b'\x0B'

class Client:
    def __init__(self):
        self._socketTcp = SocketLib.socket( SocketLib.AF_INET, SocketLib.SOCK_STREAM )
        self._socketUdp = SocketLib.socket( SocketLib.AF_INET, SocketLib.SOCK_DGRAM )

    def start(self):
        while True:
            if self._connect():
                break

        while True:
            try:
                command = input( 'Input command : ' )
                if command.startswith('exit'):
                    return
                self._sendCommand( command )
                self._socketTcp.settimeout( ANSWER_TIMEOUT )
                print( 'Answer :', self._socketTcp.recv(1024) )
            except SocketLib.timeout:
                print( 'No answer' )
            except (ConnectionAbortedError, ConnectionResetError):
                print( 'Connection Aborted' )
                break

    def _connect(self):
        try:
            print( 'Connecting to ', (SERVER_ADDRESS, SERVER_PORT) )
            self._socketTcp.settimeout( SERVER_TIMEOUT )
            self._socketTcp.connect( (SERVER_ADDRESS, SERVER_PORT) )
        except SocketLib.timeout:
            print( 'Timeout' )
            return False
        except InterruptedError:
            print( 'Error' )
            return False
        except ConnectionRefusedError:
            print( "Server Refused connection" )
            return False
        else:
            return True

    def _sendCommand(self, command):
        command = str(command)
        if command.startswith('echo'):
            self._socketTcp.send( ECHO_MSG + command[5:].encode() + b'\0' )
        elif command.startswith('time'):
            self._socketTcp.send( TIME_MSG )
        elif command.startswith('ufile'):
            self._ufileCommand( command )
        elif command.startswith('exit'):
            exit(0)
        elif command.startswith('file'):
            name = command[5:]
            try:
                file = open( name, 'rb' )
            except OSError:
                print( 'file ', name, ' is not open' )
                return None
            else:
                self._socketTcp.settimeout( None )
                self._socketTcp.send( FILE_MSG )
                sizePack = StructLib.pack( '!q', os.path.getsize(name) )
                name = name.split('/')[-1].encode()
                self._socketTcp.send( StructLib.pack( '!h', len(name) ) + name )
                self._socketTcp.send( sizePack )
                while True:
                    chunk = file.read( 1024 )
                    if chunk is None or chunk == b'':
                        break
                    self._socketTcp.send( chunk )


    def _ufileCommand(self, command):
        name = command[6:]
        try:
            file = open( name, 'rb' )
        except OSError:
            print( 'file ', name, ' is not open' )
            return None
        else:
            fileSize = os.path.getsize( name )
            maxChunk = (int)(fileSize / 500)
            if fileSize % 500 != 0:
                maxChunk += 1
            message = bytearray( StructLib.pack( '!q', fileSize ) )
            message += name.split('/')[-1].encode()
            self._socketUdp.settimeout( 2.0 )
            self._socketUdp.sendto( message, (SERVER_ADDRESS, SERVER_PORT) )     #send fileSize + Name

            minTransferChunk = 0
            datagramCount = 1
            while True:
                self._socketUdp.setblocking(False)
                try:
                    recvData, recvAdr = self._socketUdp.recvfrom( 500 )
                    if recvAdr != (SERVER_ADDRESS, SERVER_PORT):
                       print( "Unknown address ", recvAdr )
                    if recvData is None:
                        print( "Disconnected" )
                        return
                    waitingChunk = StructLib.unpack( 'Q', recvData[:8] )[0]
                    if waitingChunk == maxChunk + 1:
                        print( 'Done' )
                        break

                    prevFilePos = file.tell()
                    file.seek( (waitingChunk - 1) * 500 )
                    waitingMsg = StructLib.pack('!Q', waitingChunk) + file.read( 500 )
                    self._socketUdp.sendto( waitingMsg, (SERVER_ADDRESS, SERVER_PORT) )
                    file.seek( prevFilePos )
                except BlockingIOError:
                    chunk = b''
                    if datagramCount <= maxChunk:
                        chunk = file.read( 500 )            # UDP garanted transfer size = 576 bytes
                    if chunk is not None and chunk != b'':
                        chunk = StructLib.pack( '!Q', datagramCount ) + chunk;      #4 bytes for chunk id
                        self._socketUdp.settimeout( 2 )
                        self._socketUdp.sendto( chunk, (SERVER_ADDRESS, SERVER_PORT) )
                        datagramCount += 1
                except SocketLib.timeout:
                    pass
                    #datagramCount -= 1;
                    #file.seek( -500, 1 )


if __name__ == '__main__':
    #data = b'Hi'
    #data.decode()
    #print(dir(data))
    client = Client()
    client.start()