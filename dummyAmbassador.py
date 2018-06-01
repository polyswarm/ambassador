#TODO: Error handling

import subprocess
import requests
import sys
import shlex
import os
import math
import random

HOST = 'http://localhost:31337'
PASSWORD = 'password'


# Description: File class to hold sufficient data for bounty creation
# TODO: 
class File:
	def __init__(self, name, path, intent):
		self.name = name
		self.path = path+name
		self.intent = intent

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


		file = {'file': (self.file.name, open(self.file.path, 'rb'))}

		#send post to polyswarmd
		try:
			response = requests.post(HOST+'/artifacts', files=file)
		except:
			print("Error in artifact.postArtifact: ", sys.exc_info()[0])
			print(self.file.name +" not posted")


		response = jsonify(response)

		#check response is ok
		if 'status' not in response:
				print('No status found in response. Following error received:')
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
		response = ''

		try:
			response = requests.post(HOST+'/bounties', headers=headers, data=data)
		except:
			print("Error in artifact.postBounty: ", sys.exc_info()[0])
			print(self.file.name +" bounty not posted.")
		#
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

#Description: 	User class to retain info to make an assertion and whether
#				or not current user is correct or not
class User:
	def __init__(self, address, password):
		self.address = address
		self.password = password

	# Description: Unlock test account for use
	# Params: N/A
	# return: True for success, False for fail
	# TODO: handle errors better
	def unlockAccount(self):
		print("Attempting to unlock user "+self.address)
		response = ''
		status = ''

		headers = {'Content-Type': 'application/json'}
		dataUnlock = '{"password": "'+self.password+'"}'
		try:
			response = requests.post(HOST+'/accounts/'+self.address+'/unlock', headers=headers, data=dataUnlock)
		
		except:
			print("Error in user.unlockAccount: ", sys.exc_info()[0])
			return -1

		response = jsonify(response)

		#check status is ok
		if 'status' not in response:
			print(response)
			print("Error in user.unlockAccount: ", sys.exc_info()[0])
			sys.exit()

		status = response['status']
		
		if status != 'OK':
			print("Error in user.unlockAccount: ", sys.exc_info()[0])
			print(status)
			sys.exit()


		print("Succesfully unlocked: "+self.address)


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


# Description: Retrieve files from directories to use as artifacts
# Params:
# return: array of file objects
# TODO: Acquire true intent of malware files from nick/check file name against
# database of true intent to easily settle verdicts when needed. 
def getFiles():
	files = []

	#benign files
	for file in os.listdir("./benignFiles/"):
		tmp = File(file, "./benignFiles/", "benign")
		print("Benign: "+file+"\n")
		files.append(tmp)

	#malicious files
	for file in os.listdir("./maliciousFiles/"):
		tmp = File(file, "./maliciousFiles/", "malicious")
		print("Malicious: "+file+"\n")
		files.append(tmp)		

	return files


# Description: Obtain list of accounts from polyswarmd and return the first entry		
# return: address of a user
# TODO: Handle no users
def setAccount():
	response = ''

	try:
		response = requests.get(+HOST+'/accounts')
	except:
		print(response)
		print("Error in setAccount: ", sys.exc_info()[0])
		sys.exit()

	accountList = jsonify(response)


	if accountList['status'] != "OK":
		sys.exit("invalid accounts")

	#A bit hardcoded
	# Might want to change to looking at keystore or unlocking out of module
	return accountList['result'][0]

if __name__ == "__main__":

	#default bounties to post
	numBountiesToPost = 1

	#if an int is used in cmd arg then use that as # bounties to post
	if (len(sys.argv) is 2):
		if isinstance(sys.argv[1], int):
			numBountiesToPost = sys.argv[1]

	
	print("\n\n********************************")
	print("OBTAINING FILES")
	print("********************************")
	fileList = getFiles()	
	

	print("\n\n********************************")
	print("CREATING "+ str(numBountiesToPost) +" BOUNTIES")
	print("********************************")
	bountyList = postBounties(numBountiesToPost, fileList)


	print("\n\n********************************")
	print("FINISHED BOUNTY CREATION")
	print("********************************")
