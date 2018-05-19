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
		#original curl command
		cmd = shlex.split("curl -F file=@"+self.file.path+" "+HOST+"/artifacts")		
		self.uri = curl(cmd, 'result')

	# Description: POST self as artifact
	# Params: 	Duration - how long to keep bounty active for test
	#			Amount - 
	# return: artifact file contents
	def postBounty(self, duration):
		#cmd = shlex.split("curl -H 'Content-Type: application/json' -d '{'amount': '"+self.bid+"', 'uri': '"+self.uri+"', 'duration': '"+duration+"'}' "+HOST+"/bounties")		
		
		headers = {'Content-Type': 'application/json'}
		data = '{"amount": "'+self.bid+'", "uri": "'+self.uri+'", "duration": '+duration+'}'
		response = requests.post(HOST+'/bounties', headers=headers, data=data)

		response = jsonify(response)

		if 'status' not in response:
				print(response['message'])
				sys.exit()			

		if response['status']:
			if response['status'] is 'FAIL':
				print(response['message'])
				sys.exit()
			else:
				print("error")
		else:
			print("error")

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

	@classmethod
	def createUser(self):
		self.address = ''
		self.password = 'password'
		self.correct = False

	# Description: Unlock test account for use
	# Params: N/A
	# return: True for success, False for fail
	# TODO: handle errors better
	def unlockAccount(self):
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

		if response['status']:
			status = response['status']
		else:
			print("Error in user.assertVerdict: ", sys.exc_info()[0])
			
		print("Unlocked: "+self.address)
		return 1


# Description: Helper function to create  JOSNobject of given object 
# Params: str to be decoded
# return: json object
# TODO: 
def curl(command, label):
	response = subprocess.check_output(command)

	#change from binary string to string string
	strResponse = response.decode("utf-8")

	#split string into array
	responseArr = strResponse.split('"')[1::2]

	print(responseArr)

	resultIndex = ''
	if 'FAIL' in responseArr:
		print (strResponse)
		sys.exit()

	resultIndex = ''
	try:
		resultIndex = responseArr.index(label)
	except ValueError as e:
		print(e)
		sys.exit()

	#next index is hash
	return responseArr[resultIndex+1]


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
def postBounties(numToPost, files, poster):
	#hold all artifacts and bounties
	artifactArr = []
	bountyArr = [];

	#unlock poster
	poster.unlockAccount()

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


# Description: Create experts, assign correct users from alreayd created addresses
# Params: 	dir - keystore with user addresses
#			numToCreate - number of experts to create	
#			percentCorrect - overall accuracy of experts 
#			bid - average bid on a bounty		
# return: array of class objects
# TODO: Automate creation of users
def createAmbassador(dir):
	addresses = []

	#get file contents into local array
	for file in sorted(os.listdir(dir)):
		path = os.path.join(dir, file)
		f = open(path, 'r')
		contents = f.readline()
		f.close()
		contents = contents.split('"')[1::2]
		#address is always in same spot
		print(contents[1])
		addresses.append(contents[1])

	#Only create one ambassador since its the only account with eth at the moment
	ambassador = User(addresses[0], PASSWORD)

	return ambassador


if __name__ == "__main__":

	#default bounties to post
	numBountiesToPost = 1

	#if an int is used in cmd arg then use that as # bounties to post
	if (len(sys.argv) is 2):
		if isinstance(sys.argv[1], int):
			numBountiesToPost = sys.argv[1]

	keystore = './keystore'
	bid = 10000000000
	
	print("\n\n********************************")
	print("OBTAINING FILES")
	print("********************************")
	fileList = getFiles()	

	ambassador = createAmbassador(keystore)
	
	print("\n\n********************************")
	print("CREATING "+ str(numBountiesToPost) +"BOUNTIES")
	print("********************************")
	bountyList = postBounties(numBountiesToPost, fileList, ambassador)
	print("\n\n********************************")
	print("FINISHED BOUNTY CREATION")
	print("********************************")
