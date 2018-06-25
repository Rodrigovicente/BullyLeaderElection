import socket
import struct
import select
import sys
import os
import netifaces
import time
import pickle
from threading import Thread

PID = str(os.getpid())

INICIA_ELEICAO = 10
RESPOSTA_ELEICAO = 11

GRUPO_MC = '224.0.0.0'
PORTA = 1000

mySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
mySocket.bind(('', PORT))
mreq = struct.pack('4sL', socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
mySocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

myAddr = netifaces.ifaddresses(netifaces.interfaces()[1])[2][0]['addr']
print(myAddr)


class Mensagem():
	def __init__(self, action, msg):
		self.action = action
		self.msg = msg


while True:
    readables, writeables, exceptions = select([mySocket, sys.stdin], [], [mySocket])
    for sock in readables:
        if sock == mySocket:
			serial_data, sender_addr = mySocket.recvfrom(512)
			if sender_addr[0] == myAddr:
				continue

			received_data = pickle.loads(serial_data)

        elif sock == sys.stdin:
			inicia_eleicao(mySocket)

	print("Aperte enter para iniciar a eleição.")
	sys.stdin.readline()

"""
ALGORITMO DO BULLY
"""
def start_election():
	msg = Mensagem(INICIA_ELEICAO, PID)
	serial_data = pickle.dumps(msg)

	sock.sendto(serial_data, (GRUPO_MC, PORTA))

	timeout_mark = time.time() + 1000
	while True:
	    readables, writeables, exceptions = select([mySocket], [], [mySocket], timeout_mark - time.time())

		serial_data, sender_addr = mySocket.recvfrom(512)
		if sender_addr[0] == myAddr:
			continue

		received_data = pickle.loads(serial_data)

		if received_data.action == RESPOSTA_ELEICAO:
			break

		if received_data.action == INICIA_ELEICAO:


		if (timeout_mark - time.time()) <= 0:
			break

def receiveMessage():
