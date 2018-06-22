#TODO: Error handling

import requests
import sys
import os
import websockets
import asyncio
import threading
import time
import json
from web3.auto import w3

HOST = 'localhost:31337'
PASSWORD = 'password'
ACCOUNT = 'af8302a3786a35abeddf19758067adc9a23597e5'
ARTIFACT_DIRECTORY = './artifacts/'


# Description: File class to hold sufficient data for bounty creation
# TODO: 
class File:
	def __init__(self, name, path):
		self.name = name
		self.path = path+name

class Artifact:
	def __init__(self, file, bid):
		#file object
		self.file = file
		self.uri = ''
		self.guid = ''
		self.bid = bid
		postedFlag = False

	# Description: POST currenty artifact and store uri
	# Params: self object
	# return: uri string to access artifact
	def postArtifact(self):

		print("Attempting to post "+ self.file.name)
		response = ''

		params = (('account', ACCOUNT))
		file = {'file': (self.file.name, open(self.file.path, 'rb'))}
		url = 'http://'+HOST+'/artifacts'

		#send post to polyswarmd
		try:
			response = requests.post(url, files=file)
		except:
			print("Error in artifact.postArtifact: ", sys.exc_info())
			print(self.file.name +" not posted")
			sys.exit()

		response = jsonify(response)


		#check response is ok
		if 'status' not in response or 'result' not in response:
				print('Missing key in response. Following error received:')
				print(response['message'])
				sys.exit()		


		if response['status'] is 'FAIL':
			print(response['message'])
			sys.exit()

		#hold response URI
		print("Posted successfully \n")
		self.uri = response['result']

	# Description: POST self as artifact
	# Params: 	Duration - how long to keep bounty active for test
	#			Amount - 
	# return: artifact file contents
	def postBounty(self, duration):
		print("Attempting to post bounty "+ self.uri)

		#create data for post
		headers = {'Content-Type': 'application/json'}
		data = '{"amount": "'+self.bid+'", "uri": "'+self.uri+'", "duration": '+duration+'}'
		url = 'http://'+HOST+'/bounties?account='+ACCOUNT
		response = ''

		try:
			response = requests.post(url, headers=headers, data=data)
		except:
			print("Error in artifact.postBounty: ", sys.exc_info())
			print(self.file.name +" bounty not posted.")


		response = jsonify(response)

		#check status is ok 
		if 'status' not in response:
				print('No status found in response:')
				print(response['message'])
				sys.exit()			

		if response['status'] is not 'OK':
			print("Status not OK:")
			print(response['message'])
			sys.exit()

		#keep guid
		self.guid = response['guid']

		#done with bounty
		print("Bounty "+self.guid+" created")


	#Return guid
	def getGUID(self):
		return self.guid

	#return name
	def getName(self):
		return self.name

# Description: Helper function to create  JOSNobject of given object 
# Params: str to be decoded
# return: json object
# TODO: 
def jsonify(encoded):
	decoded = '';

	try:
		decoded = encoded.json()
	except ValueError:
		sys.exit("Error in jsonify: ", sys.exc_info()[0])

	return decoded

# Description: Posts # of bounties equal to or less than num files we have
# Params: # to post 
# return: array of bounty objects
def postBounties(numToPost, files):
	#hold all artifacts and bounties
	artifactArr = []
	bountyArr = [];

	#create and post artifacts 
	for i in range(0, numToPost):
		#stop early if bounties to post is greater than the number of files
		if numToPost > len(files):
			break;
		tempArtifact = Artifact(files[i], '625000000000000000')
		tempArtifact.postArtifact()
		artifactArr.append(tempArtifact)

	#post bounties
	#artifactList iterator
	numArtifacts = len(artifactArr)
	curArtifact = 0
	for i in range(0, numToPost):
		#loop over artifacts when creating many bounties
		if curArtifact > numArtifacts:
			curArtifact = 0

		tempBounty = artifactArr[curArtifact]
		#will need to change time to account for 
		tempBounty.postBounty('50')
		bountyArr.append(tempBounty)
		curArtifact+=1

	return bountyArr


# Description: Create websocket thread to handle transaction signing for sent bounties
class transactionListener(threading.Thread):
	def run(self):
		eventLoop = asyncio.new_event_loop()
		asyncio.set_event_loop(eventLoop)
		asyncio.ensure_future(waitForEvent())
		eventLoop.run_forever()

async def waitForEvent():	
	print("Listening for transactions...")
	async with 	websockets.connect('ws://'+HOST+'/transactions') as websocket:
		while True:
			try:
				event = await websocket.recv()

				#catch transaction
				signedTx = signTransaction(event)

				print('Sending signed object...')
				websocket.send(json.dumps(signedTx))
				print('Sent')
			except Exception as e:
				#print error and close connection
				print(e)
				break
	eventLoop.stop()


# Description: 	Given a transaction, get the private key for the current account. 
#				sign the transactio nadn return an object with id, chainid, and signedtx
# Params: event - raw transaction
# Return: object with {id, chaindId, rawTx}
# TODO: CHANGE DIR WITH ACCOUNT
def signTransaction(event):
	print('Transaction received. Attempting to sign...')

	#change format to json for easy access
	tx = json.loads(event)
	data = tx['data']
	transaction = {}
	toSend = {}

	# event comes in as json object and must be pieced back together to create a transaction
	#increment nonce by one for signing
	try:
		transaction = {
			'to': data['to'],
			'value': data['value'],
			'gas': data['gas'],
			'gasPrice': data['gasPrice'],
			'nonce': data['nonce']
		}
	except KeyError as e:
		print('*****KeyError*****')
		print(e+' does not exist in transaction received from polsywarmd')
		sys.exit()



	#get private key to sign
	private_key = ''
	with open('./keystore/UTC--2018-03-08T04-05-00.589797373Z--af8302a3786a35abeddf19758067adc9a23597e5', 'r') as keyfile:
		encrypted_key = keyfile.read()
		private_key = w3.eth.account.decrypt(encrypted_key, 'password')
	
	#sign
	sign = w3.eth.account.signTransaction(transaction, private_key)
	print('Signed')
	try:
		#to send consists of id, chaindid, and signedtx data
		#Note txsign is 
		toSend = {
			'id': tx['id'], 
			'chainId': data['chainId'],
			'data': bytes(sign['rawTransaction']).hex()
		}
	except KeyError as e:
		print('*****KeyError*****')
		print(e)
		sys.exit()


	return toSend

# Description: Retrieve files from directories to use as artifacts
# Params:
# return: array of file objects
# TODO: Acquire true intent of malware files from nick/check file name against
# database of true intent to easily settle verdicts when needed. 
def getFiles():
	files = []

	for file in os.listdir(ARTIFACT_DIRECTORY):
		tmp = File(file, ARTIFACT_DIRECTORY)
		files.append(tmp)	

	return files

if __name__ == "__main__":

	#default bounties to post
	numBountiesToPost = 2

	#if an int is used in cmd arg then use that as # bounties to post
	if (len(sys.argv) is 2):
		if isinstance(sys.argv[1], int):
			numBountiesToPost = sys.argv[1]

	
	print("\n\n********************************")
	print("OBTAINING FILES")
	print("********************************")
	fileList = getFiles()	
	
	print("\n\n********************************")
	print("Starting Transaction Listener")
	print("********************************")
	listener = transactionListener()
	listener.start()
	time.sleep(1)


	print("\n\n********************************")
	print("CREATING "+ str(numBountiesToPost) +" BOUNTIES")
	print("********************************")
	bountyList = postBounties(numBountiesToPost, fileList)


	print("\n\n********************************")
	print("FINISHED BOUNTY CREATION")
	print("********************************")
