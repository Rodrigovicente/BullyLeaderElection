import socket
import struct
import select
import sys
import os
import netifaces
import pickle
import time as t
from threading import Thread
from random import randint


INICIA_ELEICAO = 10
RESPOSTA_ELEICAO = 11
LIDER_ATUAL = 20
INICIA_BERKELEY = 30
RESPOSTA_BERKELEY = 31
AJUSTE_BERKELEY = 32

GRUPO_MC = '224.0.0.0'
PORTA = 8888
PID = str(os.getpid())

global isLeader
global currentLeaderAddr
global timeList
global currentTime

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
	print('Iniciando eleição.')
	msg = Mensagem(INICIA_ELEICAO, PID)
	serial_data = pickle.dumps(msg)
	print('Enviando para todos em multicast.')
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))

	print('Esperando respostas.')
	timeoutMark = t.time() + 1.0
	while True:
		timeOut = timeoutMark - t.time()
		if timeOut > 0:
			readables, writeables, exceptions = select.select([mySocket], [], [mySocket], timeOut)
		else:
			print('Timout: não houve resposta. Torna-se lider.')
			isLeader = True
			currentLeaderAddr = myAddr
			send_leader()
			run_berkeley()
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

	global currentTime

	if sender_addr[0] != myAddr:
		print('')
		if received_data.action == INICIA_ELEICAO:
			print('Pedido de eleição recebido.')
			if int(PID) > int(received_data.msg):
				print('\t- Tem PID maior (', PID, ' > ', int(received_data.msg), '). Enviando resposta.')
				response = Mensagem(RESPOSTA_ELEICAO, 0)
				serial_response = pickle.dumps(response)
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

		elif received_data.action == INICIA_BERKELEY:
			adjust = received_data.msg - currentTime
			print('Pedido de valor de ajuste para o algoritmo de Berkeley.')
			print('Tempo atual: ', currentTime,' - Ajuste enviado: ', adjust, '.')
			response = Mensagem(RESPOSTA_BERKELEY, adjust)
			serial_response = pickle.dumps(response)
			mySocket.sendto(serial_response, sender_addr)
			return (INICIA_BERKELEY, True)

		elif received_data.action == RESPOSTA_BERKELEY:
			print('Adiciona o ajuste do escravo à lista de tempo (', received_data.msg, ').')
			timeList.append((sender_addr, received_data.msg))
			return (RESPOSTA_BERKELEY, True)

		elif received_data.action == AJUSTE_BERKELEY:
			print('Ajusta o tempo de acordo com o enviado pelo lider (', received_data.msg,').')
			print(' - Tempo antes do ajuste: ', currentTime, '.')
			currentTime = received_data.msg + currentTime
			print(' - Tempo ajustado: ', currentTime, '.')
			return (AJUSTE_BERKELEY, True)

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
BERKELEY
"""
def run_berkeley():
	global currentTime
	print('Inicia o algoritmo de Berkeley. Envia mensagem em multicast com o tempo do lider (', currentTime, ').')
	msg = Mensagem(INICIA_BERKELEY, currentTime)
	serial_data = pickle.dumps(msg)
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))

	print('Esperando respostas.')
	timeoutMark = t.time() + 1.0 # 1.0 é o tempo de espera em s
	while True:
		timeOut = timeoutMark - t.time()
		if timeOut > 0:
			readables, writeables, exceptions = select.select([mySocket], [], [mySocket], timeOut)
		else:
			break

		if readables:
			receive_message()

	print('Calcula dos ajustes.')
	timeSum = 0
	# print('Valores para a média de tempo:')
	for _, time in timeList:
		timeSum += int(time)
		# print(' - ', time)
	# print('Somatorio: ', timeSum)

	timeAvg = int(timeSum / (len(timeList) + 1))
	# print('Média de tempo: ', timeAvg)
	print('Envia os ajustes aos escravos.')
	for addr, time in timeList:
		timeAdjust = timeAvg + int(time)
		msg = Mensagem(AJUSTE_BERKELEY, timeAdjust)
		serial_data = pickle.dumps(msg)
		mySocket.sendto(serial_data, addr)
	timeList.clear()
	print(' - Tempo antes do ajuste: ', currentTime, '.')
	currentTime += timeAvg
	print(' - Tempo ajustado: ', currentTime, '.')


def start_clock():
	global currentTime
	# timeStep = randint(1,5)
	timeStep = 1
	while True:
		currentTime += timeStep
		t.sleep(0.25)



""" MAIN """

mySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
mySocket.bind(('', PORTA))
mreq = struct.pack('4sL', socket.inet_aton(GRUPO_MC), socket.INADDR_ANY)
mySocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

list_target = 1
myAddr = netifaces.ifaddresses(netifaces.interfaces()[list_target])[2][0]['addr']
print('IP: ', myAddr)
print('PID: ', PID)

Thread(target = start_clock).start()

while True:
	print('Aperte enter para iniciar a eleição.')
	readables, writeables, exceptions = select.select([mySocket, sys.stdin], [], [mySocket])
	for sock in readables:
		if sock == mySocket:
			received = receive_message()
			if (received[0] == INICIA_ELEICAO) and (received[1] == True):
				start_election()

		elif sock == sys.stdin:
			sys.stdin.readline()
			start_election()
