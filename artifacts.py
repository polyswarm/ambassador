import logging
import json
import os
import sys
import requests
from web3.auto import w3 as web3
KEYFILE = os.environ.get('KEYFILE','keyfile')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
HOST = os.environ.get('POLYSWARMD_ADDR','polyswarmd:31337')
API_KEY = os.environ.get('API_KEY', '')

class File:
        def __init__(self, name, path):
                self.name = name
                self.path = path+name

class Artifact:
        def __init__(self, file, bid = None, polyswarmd_host = HOST, api_key = API_KEY):
                #file object
                self.file = file
                self.uri = ''
                self.bid = bid
                self.polyswarmd_host = polyswarmd_host
                self.api_key = api_key

        # Description: POST current artifact and store uri
        # Params: self object
        # return: uri string to access artifact
        def postArtifact(self):

                logging.debug("Attempting to post "+ self.file.name)
                response = ''

                url = 'http://'+self.polyswarmd_host+'/artifacts'
                headers = {'Authorization': self.api_key}
                file = {'file': (self.file.name, open(self.file.path, 'rb'))}

                #send post to polyswarmd
                try:
                        response = requests.post(url, headers=headers, files=file)
                except:
                        logging.debug("Error in artifact.postArtifact: ", sys.exc_info())
                        logging.debug(self.file.name +" not posted")
                        sys.exit()

                response = (response.json())
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
        def postBounty(self, duration, keyfile = KEYFILE, password = '', account=ACCOUNT):
                #create data for post
                headers = {'Authorization': self.api_key, 'Content-Type': 'application/json'}

                data = dict()
                data['amount']=str(self.bid)
                data['uri']=self.uri
                data['duration']=duration
                
                url = 'http://'+self.polyswarmd_host+'/bounties'

                try:
                        response = requests.post(url, headers=headers, data=json.dumps(data))
                except:
                        logging.debug("Error in artifact.postBounty: ", sys.exc_info())
                        logging.debug(self.file.name +" bounty not posted.")

                logging.debug(response)
                transactions = response.json()['result']['transactions']

                signed = []
                key = web3.eth.account.decrypt(open(keyfile,'r').read(), password)

                for tx in transactions:
                    s = web3.eth.account.signTransaction(tx, key)
                    raw = bytes(s['rawTransaction']).hex()
                    signed.append(raw)

                r = requests.post('http://' + self.polyswarmd_host + '/transactions', headers=headers, json={'transactions': signed})

                if r.json()['status'] == 'OK':
                    logging.info("\n\nBounty "+self.file.name+" sent to polyswarmd.\n\n")
                else:
                    logging.warning("BOUNTY NOT POSTED!!!!!!!!!!! CHECK TX")