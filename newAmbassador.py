#! /usr/bin/env python
import requests
import json
import sys
import os
import asyncio
import threading
from time import sleep
import time
from web3.auto import w3 as web3
from web3 import Web3,HTTPProvider
from web3.middleware import geth_poa_middleware
w3=Web3(HTTPProvider('http://geth:8545'))
w3.middleware_stack.inject(geth_poa_middleware,layer=0)
KEYFILE = 'keyfile'
HOST = 'polyswarmd:31337'
PASSWORD = 'password'
ACCOUNT = '0x'+json.loads(open('keyfile','r').read())['address']
ARTIFACT_DIRECTORY = './bounties/'
POLYSWARMD_BOUNTY_ADDRESS='0xdE4E1Da8AcD61253948eE0dfa2377137a42240B8'
POLYSWARMD_NECTAR_ADDRESS='0x21262bf29ff08691c8a72bc6f22f791996e1891f'
print('using account ' + ACCOUNT + " ...")
#web3.eth.enable_unaudited_features()

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
                self.bid = bid

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
                print("Posted to IPFS successfully \n")
                self.uri = response['result']

	#Description: POST self as artifact
        # Params:       Duration - how long to keep bounty active for test
        #                       Amount - 
        # return: artifact file contents
        def postBounty(self, duration,basenonce):
                #create data for post
                headers = {'Content-Type': 'application/json'}
                postnonce = ''
                postnonce = str(basenonce)
                print ('base nonce is ' + postnonce)
                data = dict()
                data['amount']=self.bid
                data['uri']=self.uri
                data['duration']=duration
                
                url = 'http://'+HOST+'/bounties?account='+ACCOUNT+'&base_nonce='+postnonce
                response = ''
                print('attempting to post bounty: ' + self.uri + ' to: ' + url + '\n*****************************')  
                try:
                        response = requests.post(url, headers=headers, data=json.dumps(data))
                except:
                        print("Error in artifact.postBounty: ", sys.exc_info())
                        print(self.file.name +" bounty not posted.")


                print(response)
                #parse result
                transactions = response.json()['result']['transactions']
                #sign transactions 
                signed = []
                key = web3.eth.account.decrypt(open(KEYFILE,'r').read(), PASSWORD)
                cnt =0
                for tx in transactions:
                    cnt+=1
                    print ('tx:to= ' +tx['to'].upper())
                    print ('account: ' +ACCOUNT.upper()) 
                    #print ((tx)['to'].upper()==ACCOUNT.upper())
                    print ('\n\n*****************************\n' + 'TRANSACTION RESPONSE\n')
                    print(tx)
                    print('******************************\n')


                    s = web3.eth.account.signTransaction(tx, key)
                    raw = bytes(s['rawTransaction']).hex()
                    signed.append(raw)
                print('***********************\nPOSTING SIGNED TXNs, count #= ' + str(cnt) + '\n***********************\n')
                r = requests.post('http://polyswarmd:31337/transactions', json={'transactions': signed})
                print(r.json())
                        
                print("Bounty "+self.file.name+" sent to polyswarmd. May not have been created unless response is [200] and you signed it successfully.")

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
        print ("trying to get nonce")
        nonce=json.loads(requests.get('http://'+HOST + '/nonce?account='+ACCOUNT).text)['result']
        print ("nonce received: "+str(nonce))
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
                tempBounty.postBounty(5,nonce)
                print('posted bounty with nonce '+ str(nonce))
                nonce +=2
                #buffer bounty posts
                time.sleep(1)
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
        if numBountiesToPost<10:
            print(os.listdir(ARTIFACT_DIRECTORY))
        print("\n\n******************************************************")
        print("CREATING "+ str(numBountiesToPost) +" BOUNTIES EVERY 10 SEC")
        print("********************************************************")
        #cnt=0
        #while (cnt<10):
        bountyList = postBounties(numBountiesToPost, fileList)
        #cnt +=1
        print("iteration complete,sleeping 10...")
        sleep(5)
        print("\n\n********************************")
        print("FINISHED BOUNTY CREATION, EXITING AMBASSADOR")
        print("********************************\n\n")

