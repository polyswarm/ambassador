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
	def __init__(self, address, password, correct, bid):
		self.address = address
		self.password = password
		self.correct = correct
		self.bid = bid

	#TODO: mint NCT/ ETH(?)
	#Find out how to observe balance differences/payouts
	@classmethod
	def createUser(self):
		self.address = ''
		self.password = 'password'
		self.correct = False


	# Description: Relay verdict to swarm
	# Params: Verdict - true or false, guid - the bounty that was scanned
	# return: status of post
	# TODO: Parse response
	def assertVerdict(self, guid, metaData):
		response = ''
		status = ''
		verdict = ''

		if self.verdict is True:
			verdict = 'true'
		else:
			verdict = 'false'


		headers = {'Content-Type': 'application/json',}
		data = '{"bid": '+self.bid+', "mask": [true], "verdicts": ['+verdict+'], "metadata": "'+metaData+'"}'

		try:
			response = requests.post(HOST+'/bounties/'+self.guid+'/assertions', headers=headers, data=data)
		except:
			print("Error in user.assertVerdict: ", sys.exc_info()[0])
			return -1

		response = jsonify(response)

		if response['status']:
			status = response['status']
		else:
			print("Error in user.assertVerdict: ", sys.exc_info()[0])
			return -1


		if status is not 'OK':
			print("Error in user.assertVerdict: ", sys.exc_info()[0])
			return -1	
		print("Verdict made")
		print(response)
		return 1

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
	#hold all bounties
	bountyArr = []
	#unlock poster
	poster.unlockAccount()
	for i in range(0, numToPost):
		tempBounty = Artifact(files[i], '625000000000000000')
		tempBounty.postArtifact()
		tempBounty.postBounty('50')
		bountyArr.append(tempBounty)
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
def createUsers(dir, numToCreate, percentCorrect, bid):
	users = []
	addresses = []

	#calc how many users will be correct
	percent = percentCorrect/100
	correctXperts = int(math.floor(percent*numToCreate))


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


	#create user
	for i in range(0, numToCreate):
		if i < correctXperts:
			users.append(User(addresses[i], 'password', True, bid))
		else:
			users.append(User(addresses[i], 'password', False, bid))


	return users

# Description: Unlock user accounts to make actions
# Params: user array
# return: N/A
def unlockUsers(users):
	for cur in users:
		cur.unlockAccount()
	return

# Description: Experts make asasertions assert on bounties
# Params:	userList - list of experts
#			bountyList - list of bounties
#			artifactsAssessed - # artifacts to assert on
#			expertsPerArtifact - Avg. amount of experts per artifact
# return: N/A
# TODO: WORK IN PROGRESS
#		Must account for #of users per artifact and maek sure average accuracy
#		for each artifact
def makeAllAssertions(userList, bountyList, artifactsAssessed, expertsPerArtifact):
	
	random.seed()
	curGUID = ''
	curBountyName = ''
	percent = artifactsAssessed/100
	numArtifacts = int(math.ceil(percent*len(bountyList)))


	#make assertions on % of random bounties
	#have x amount of experts assert on them
	for i in range(0, numArtifacts):
		random.randrange(0, len(bountyList)-1, 1)
		curGUID = bountyList[i].getGUID()
		curName = bountyList[i].getName()
		for expert in userList:
			print(expert)
			expert.assertVerdict(curGUID, curName)

	return

if __name__ == "__main__":
	#main

	#get data points from user
	#bid = input("Average bid: ")

	#accuracy = input("Average Accuracy: ")

	#bounty = input("Initial bounty pot: ")

	#artifactsAssessed = input("Percent artifacts assessed by expert: ")

	#expertsPerArtifact = input("Number of experts per artifact: ")

	#arbiters = input("Number of arbiters: ")

	#verified = input("Percent of artifacts verified by arbiter per day: ")

	#numUsers = input("Number of users to create(1-: ")


	keystore = './keystore'
	accuracy = 70
	bid = 10000000000
	artifactsAssessed = 35
	expertsPerArtifact = 5
	
	print("********************************")
	print("CREATING USERS")
	print("********************************")	
	userList = createUsers(keystore, expertsPerArtifact, accuracy, bid)
	
	print("\n\n********************************")
	print("UNLOCKING USERS - OMITTED AT THE MOMENT")
	print("********************************")	
	#unlockUsers(userList)
	
	print("\n\n********************************")
	print("OBTAINING FILES")
	print("********************************")
	fileList = getFiles()	
	
	print("\n\n********************************")
	print("CREATING BOUNTIES")
	print("********************************")
	#unlock account at [0] as thisaccount has eth
	bountyList = postBounties(1, fileList, userList[0])
	
	print("\n\n********************************")
	print("MAKING ASSERTIONS")
	print("********************************")
	makeAllAssertions(userList, bountyList, artifactsAssessed, expertsPerArtifact)	
	
	#TODO: Watch payouts. Arbiter(s) make verdicts
	print("\n\n********************************")
	print("GET DATA")
	print("********************************")

	#Create text file to show data