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


# Description: Posts # of bounties equal to or less than num files we have
# Params: # to post 
# return: array of bounty objects
def postBounties(numToPost, files, host, keyfile, password, bid, duration, api_key, account):
        #hold all artifacts and bounties
        artifactArr = []
        bountyArr = []
        
        logging.debug("trying to get nonce")
        headers = {'Authorization': api_key}
        # always put account into our requests
        nonce=json.loads(requests.get('http://'+ host + '/nonce', headers=headers, params={'account': account}).text)['result']
        logging.debug("nonce received: "+str(nonce))
        #create and post artifacts 
        for i in range(0, numToPost):
                #stop early if bounties to post is greater than the number of files
                if numToPost > len(files):
                        break;
                tempArtifact = Artifact(files[i], bid, host, api_key=api_key, account=account)
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
                tempBounty.postBounty(duration, keyfile, password, account)
                logging.debug('posted bounty with nonce '+ str(nonce))
                bountyArr.append(tempBounty)
                curArtifact+=1
        return bountyArr

# Description: Retrieve files from directories to use as artifacts
# Params:
# return: array of file objects
def getFiles(directory):
        files = []

        for file in os.listdir(directory):
                tmp = File(file, directory)
                files.append(tmp)

        return files

def run_test(polyswarmd_addr, keyfile, password, bounty_directory, bid, duration, api_key, account):
    #default bounties to post

    logging.debug("\n\n********************************")
    logging.debug("OBTAINING FILES")
    logging.debug("********************************")
    fileList = getFiles(bounty_directory)
    logging.debug(os.listdir(bounty_directory))
    logging.debug("\n\n******************************************************")
    logging.debug("CREATING "+ str(len(fileList)) + "BOUNTIES")
    logging.debug("********************************************************")
    bountyList = postBounties(len(fileList), fileList, polyswarmd_addr, keyfile, password, bid, duration, api_key, account)
    logging.debug( str(bountyList) )
    logging.debug("\n\n********************************")
    logging.debug("FINISHED BOUNTY CREATION, EXITING AMBASSADOR")
    logging.debug("********************************\n\n")

if __name__ == "__main__":
    run_test()