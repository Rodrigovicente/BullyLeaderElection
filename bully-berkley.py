import socket
import struct
import select
import sys
import os
import netifaces
import time
import pickle
from threading import Thread
from random import randint


INICIA_ELEICAO = 10
RESPOSTA_ELEICAO = 11
LIDER_ATUAL = 20

GRUPO_MC = '224.0.0.0'
PORTA = 8888
PID = str(os.getpid())

isLeader = False
currentLeaderAddr = ''
timeList = []
currentTime = 0


class Mensagem():
	def __init__(self, action, msg):
		self.action = action
		self.msg = msg


"""
ALGORITMO DO BULLY
"""
def start_election():
	msg = Mensagem(INICIA_ELEICAO, PID)
	serial_data = pickle.dumps(msg)
	print('Enviando para todos em multicast.')
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))

	print('Esperando respostas.')
	timeoutMark = time.time() + 1.0
	while True:
		timeOut = timeoutMark - time.time()
		if timeOut > 0:
			readables, writeables, exceptions = select.select([mySocket], [], [mySocket], timeOut)
		else:
			print('Timout: não houve resposta. Torna-se lider.')
			isLeader = True
			currentLeaderAddr = myAddr
			send_leader()
			break

		if readables:
			received_data = receive_message()

			if received_data[0] == RESPOSTA_ELEICAO:
				print('Não é lider. Há um PID maior.')
				isLeader = False
				break


"""
GERENCIA MENSAGENS
"""
def receive_message():
	print('Lendo mensagem...', end="", flush=True)
	serial_data, sender_addr = mySocket.recvfrom(512)
	received_data = pickle.loads(serial_data)

	if sender_addr[0] != myAddr:
		print('\n')
		""" para INICIA_ELEICAO """
		if received_data.action == INICIA_ELEICAO:
			print('Pedido de eleição recebido.')
			if PID > int(received_data.msg):
				print('\t- Tem PID maior (', PID, ' > ', int(received_data.msg), '). Enviando resposta.')
				serial_response = pickle.dumps(RESPOSTA_ELEICAO)
				mySocket.sendto(serial_response, sender_addr)
				return (INICIA_ELEICAO, True)

			print('\t- Tem PID menor (', PID, ' < ', int(received_data.msg), '). NAO envia nada.')
			return (INICIA_ELEICAO, False)

		elif received_data.action == RESPOSTA_ELEICAO:
			print('Rebendo resposta de eleição.')
			return (RESPOSTA_ELEICAO, True)

		elif received_data.action == LIDER_ATUAL:
			print('Definindo novo lider para: ', received_data.msg)
			currentLeaderAddr = received_data.msg
			return (LIDER_ATUAL, True)

		elif received_data.action == INICIA_BERKLEY:
			adjust = int(received_data.msg) - currentTime
			print('Pedido de valor de ajuste para o algoritom Berkley. Ajuste enviado: ', adjust)
			response = Mensagem(RESPOSTA_BERKLEY, adjust)
			serial_response = pickle.dumps(response)
			mySocket.sendto(serial_response, sender_addr)
			return (INICIA_BERKLEY, True)

		elif received_data.action == RESPOSTA_BERKLEY:
			timeList.append((sender_addr, received_data.msg))
			return (RESPOSTA_BERKLEY, True)

		elif received_data.action == AJUSTE_BERKLEY:
			currentTime = received_data.msg + currentTime

		else:
			print('Padrão de mensagem não reconhecido.')
			return None
	else:
		print(' loopback.')
		return (None, None)

"""
ANUNCIA LIDER
"""
def send_leader():
	print('Enviando mensagem em multicast anunciando novo lider.')
	msg = Mensagem(LIDER_ATUAL, myAddr)
	serial_data = pickle.dumps(msg)
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))


"""
BERKLEY
"""
def run_berkley():
	msg = Mensagem(INICIA_BERKLEY, currentTime)
	serial_data = pickle.dumps(msg)
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))

	timeoutMark = time.time() + 1.0
	while True:
		timeOut = timeoutMark - time.time()
		if timeOut > 0:
			readables, writeables, exceptions = select.select([mySocket], [], [mySocket], timeOut)
		else:
			break

		receive_message()

	timeSum = 0
	for _, time in timeList:
		timeSum += int(time)

	timeAvg = int(timeSum / (len(timeList) + 1))

	for addr, time in timeList:
		timeAdjust = timeAvg - int(time)
		msg = Mensagem(AJUSTE_BERKLEY, timeAdjust)
		serial_data = pickle.dumps(msg)
		mySocket.sendto(serial_data, addr)
	currentTime += timeAvg 
	timeList.clear()


def start_clock():
	currentTime = 0
	timeStep = randint(1,5)
	# timeStep = 1
	while True:
		currentTime += timeStep
		time.sleep(0.25)



""" MAIN """

mySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
mySocket.bind(('', PORTA))
mreq = struct.pack('4sL', socket.inet_aton(GRUPO_MC), socket.INADDR_ANY)
mySocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

list_target = 1
myAddr = netifaces.ifaddresses(netifaces.interfaces()[list_target])[2][0]['addr']
print('IP: ', myAddr)

Thread(target = start_clock).start()

while True:
	print('Aperte enter para iniciar a eleição.')
	readables, writeables, exceptions = select.select([mySocket, sys.stdin], [], [mySocket])
	for sock in readables:
		if sock == mySocket:
			receive_message()

		elif sock == sys.stdin:
			sys.stdin.readline()
			print('Iniciando eleição.')
			start_election()
