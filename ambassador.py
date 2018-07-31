#! /usr/bin/env python
import requests
import json
import sys
import os
import asyncio
import logging

from web3.auto import w3 as web3
from web3 import Web3,HTTPProvider
from web3.middleware import geth_poa_middleware

logging.basicConfig(level=logging.INFO)
w3=Web3(HTTPProvider(os.environ.get('GETH_ADDR','http://geth:8545')))
w3.middleware_stack.inject(geth_poa_middleware,layer=0)

KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_ADDR','polyswarmd:31337')
PASSWORD = os.environ.get('PASSWORD','password')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
logging.debug('using account ' + ACCOUNT + "...")


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

        # Description: POST current artifact and store uri
        # Params: self object
        # return: uri string to access artifact
        def postArtifact(self):

                logging.debug("Attempting to post "+ self.file.name)
                response = ''

                params = (('account', ACCOUNT))
                file = {'file': (self.file.name, open(self.file.path, 'rb'))}
                url = 'http://'+HOST+'/artifacts'

                #send post to polyswarmd
                try:
                        response = requests.post(url, files=file)
                except:
                        logging.debug("Error in artifact.postArtifact: ", sys.exc_info())
                        logging.debug(self.file.name +" not posted")
                        sys.exit()

                response = jsonify(response)
                #check response is ok
                if 'status' not in response or 'result' not in response:
                                logging.debug('Missing key in response. Following error received:')
                                logging.debug(response['message'])
                                sys.exit()


                if response['status'] is 'FAIL':
                        logging.debug(response['message'])
                        sys.exit()

                #hold response URI
                logging.debug("Posted to IPFS successfully \n")
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
                logging.debug('base nonce is ' + postnonce)
                data = dict()
                data['amount']=self.bid
                data['uri']=self.uri
                data['duration']=duration
                
                url = 'http://'+HOST+'/bounties?account='+ACCOUNT+'&base_nonce='+postnonce
                response = ''
                logging.debug('attempting to post bounty: ' + self.uri + ' to: ' + url + '\n*****************************')  
                try:
                        response = requests.post(url, headers=headers, data=json.dumps(data))
                except:
                        logging.debug("Error in artifact.postBounty: ", sys.exc_info())
                        logging.debug(self.file.name +" bounty not posted.")


                logging.debug(response)
                #parse result
                transactions = response.json()['result']['transactions']
                #sign transactions 
                signed = []
                key = web3.eth.account.decrypt(open(KEYFILE,'r').read(), PASSWORD)
                cnt = 0
                for tx in transactions:
                    cnt+=1
                    logging.debug('tx:to= ' +tx['to'].upper())
                    logging.debug('account: ' +ACCOUNT.upper()) 
                    logging.debug('\n\n*****************************\n' + 'TRANSACTION RESPONSE\n')
                    logging.info(tx)
                    logging.debug('******************************\n')


                    s = web3.eth.account.signTransaction(tx, key)
                    raw = bytes(s['rawTransaction']).hex()
                    signed.append(raw)
                logging.debug('***********************\nPOSTING SIGNED TXNs, count #= ' + str(cnt) + '\n***********************\n')
                r = requests.post('http://polyswarmd:31337/transactions', json={'transactions': signed})
                logging.debug(r.json())
                if r.json()['status'] == 'OK':
                	logging.info("Bounty "+self.file.name+" sent to polyswarmd.")
                else:
                	logging.warning("BOUNTY NOT POSTED!!!!!!!!!!! CHECK TX")

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
        logging.debug("trying to get nonce")
        nonce=json.loads(requests.get('http://'+HOST + '/nonce?account='+ACCOUNT).text)['result']
        logging.debug("nonce received: "+str(nonce))
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
                tempBounty.postBounty(25,nonce)
                logging.debug('posted bounty with nonce '+ str(nonce))
                nonce +=2
                bountyArr.append(tempBounty)
                curArtifact+=1
        return bountyArr

# Description: Retrieve files from directories to use as artifacts
# Params:
# return: array of file objects
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


        logging.debug("\n\n********************************")
        logging.debug("OBTAINING FILES")
        logging.debug("********************************")
        fileList = getFiles()
        if numBountiesToPost<10:
            logging.debug(os.listdir(ARTIFACT_DIRECTORY))
        logging.debug("\n\n******************************************************")
        logging.debug("CREATING "+ str(numBountiesToPost) + "BOUNTIES")
        logging.debug("********************************************************")
        bountyList = postBounties(numBountiesToPost, fileList)
        logging.debug("\n\n********************************")
        logging.debug("FINISHED BOUNTY CREATION, EXITING AMBASSADOR")
        logging.debug("********************************\n\n")
        sys.exit(0)

