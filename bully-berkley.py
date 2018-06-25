import socket
import struct
import select
import sys
import os
import netifaces
import time
import pickle
from threading import Thread


INICIA_ELEICAO = 10
RESPOSTA_ELEICAO = 11

GRUPO_MC = '224.0.0.0'
PORTA = 8888
PID = str(os.getpid())

isLeader = False
currentLeaderAddr = ''

mySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
mySocket.bind(('', PORTA))
mreq = struct.pack('4sL', socket.inet_aton(GRUPO_MC), socket.INADDR_ANY)
mySocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

myAddr = netifaces.ifaddresses(netifaces.interfaces()[1])[2][0]['addr']
print(myAddr)


class Mensagem():
	def __init__(self, action, msg):
		self.action = action
		self.msg = msg


while True:
	print("Esperando mensagem")
	readables, writeables, exceptions = select.select([mySocket, sys.stdin], [], [mySocket])
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

	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))

	timeout_mark = time.time() + 1000
	while True:
		readables, writeables, exceptions = select.select([mySocket], [], [mySocket], timeout_mark - time.time())

		received_data = receiveMessage()

		if received_data[0] == RESPOSTA_ELEICAO:
			isLeader = False
			break

		if (timeout_mark - time.time()) <= 0:
			print("Torna-se lider.")
			isLeader = True
			currentLeaderAddr = myAddr
			sendLeader()
			break


"""
GERENCIA MENSAGENS
"""
def receiveMessage():
	serial_data, sender_addr = mySocket.recvfrom(512)
	received_data = pickle.loads(serial_data)

	if sender_addr[0] != myAddr:
		""" para INICIA_ELEICAO """
		if received_data.action == INICIA_ELEICAO:
			if PID > int(received_data.msg):
				serial_response = pickle.dumps(RESPOSTA_ELEICAO)
				mySocket.sendto(serial_response, sender_addr)
				return (INICIA_ELEICAO, True)

			return (INICIA_ELEICAO, False)

		""" para RESPOSTA_ELEICAO """
		elif received_data.action == RESPOSTA_ELEICAO:
			return (RESPOSTA_ELEICAO, True)

		""" para DEFINE_LIDER """
		elif received_data.action == DEFINE_LIDER:
			currentLeaderAddr = received_data.msg
			return (DEFINE_LIDER, True)

	return (None, None)

"""
ANUNCIA LIDER
"""
def sendLeader():
	msg = Mensagem(DEFINE_LIDER, myAddr)
	serial_data = pickle.dumps(msg)
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))
