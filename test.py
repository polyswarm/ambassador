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
from artifacts import File, Artifact

logging.basicConfig(level=logging.DEBUG)
w3=Web3(HTTPProvider(os.environ.get('GETH_ADDR','http://geth:8545')))
w3.middleware_stack.inject(geth_poa_middleware,layer=0)

KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_HOST','polyswarmd:31337')
PASSWORD = os.environ.get('PASSWORD','password')
API_KEY = os.environ.get('API_KEY', '95911a507379061cd32218ea0e511408')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
BOUNTY_DURATION = os.environ.get('BOUNTY_DURATION',25)

logging.debug('using account ' + ACCOUNT + "...")


# Description: Posts # of bounties equal to or less than num files we have
# Params: # to post 
# return: array of bounty objects
def postBounties(numToPost, files):
        #hold all artifacts and bounties
        artifactArr = []
        bountyArr = [];
        logging.debug("trying to get nonce")
        headers = {'Authorization': API_KEY}

        nonce=json.loads(requests.get('http://'+HOST + '/nonce', headers=headers).text)['result']
        logging.debug("nonce received: "+str(nonce))
        #create and post artifacts 
        for i in range(0, numToPost):
                #stop early if bounties to post is greater than the number of files
                if numToPost > len(files):
                        break;
                tempArtifact = Artifact(files[i], '625000000000000000', HOST, API_KEY)
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
                tempBounty.postBounty(BOUNTY_DURATION, KEYFILE, PASSWORD, ACCOUNT)
                logging.debug('posted bounty with nonce '+ str(nonce))
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

def run_test():
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
    logging.debug( str(bountyList) )
    logging.debug("\n\n********************************")
    logging.debug("FINISHED BOUNTY CREATION, EXITING AMBASSADOR")
    logging.debug("********************************\n\n")
    sys.exit(0)

if __name__ == "__main__":
    run_test()