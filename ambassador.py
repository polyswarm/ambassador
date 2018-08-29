import click
import logging
import sys
from artifacts import File, Artifact
import os
import json
from web3.auto import w3 as web3
from web3 import Web3,HTTPProvider
from web3.middleware import geth_poa_middleware
<<<<<<< HEAD
from test import run_test

KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_HOST','localhost:31337')
PASSWORD = os.environ.get('PASSWORD','password')
API_KEY = os.environ.get('API_KEY', '')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
BOUNTY_DURATION = os.environ.get('BOUNTY_DURATION',25)
BID = os.environ.get('BID','625000000000000000')

@click.command()
@click.option('--log', default='DEBUG',
        help='Logging level')
@click.option('--polyswarmd-addr', envvar='POLYSWARMD_HOST', default=HOST,
        help='Address of polyswarmd instance')
@click.option('--keyfile', envvar='MICROENGINE_KEYFILE', type=click.Path(exists=True), default=KEYFILE,
        help='Keystore file containing the private key to use with this microengine')
@click.option('--password', envvar='PASSWORD', default=PASSWORD,
        help='Password to decrypt the keyfile with')
@click.option('--bounty-directory', envvar='BOUNTY_DIRECTORY', default=ARTIFACT_DIRECTORY, type=click.Path(exists=True),
        help='Directory with file you want to submit for bounties')
@click.option('--bid', default=BID, envvar='BID',
        help='Bid for the bounties you want to submit')
@click.option('--duration', default=BOUNTY_DURATION,
        help='How long you want the bounties to run')
@click.option('--api-key', envvar='API_KEY', default=API_KEY,
        help='API key to use with polyswarmd')

def main(log, polyswarmd_addr, keyfile, password, bounty_directory, bid, duration, api_key):
    loglevel = getattr(logging, log.upper(), None)
    priv_key = None
    address = None

    account = '0x' + json.loads(open(keyfile,'r').read())['address']

    logging.debug('using account ' + ACCOUNT + "...")

    run_test(polyswarmd_addr, keyfile, password, bounty_directory, bid, duration, api_key, account)

if __name__ ==  '__main__':
    main()
=======
from artifacts import File, Artifact

logging.basicConfig(level=logging.DEBUG)
w3=Web3(HTTPProvider(os.environ.get('GETH_ADDR','http://geth:8545')))
w3.middleware_stack.inject(geth_poa_middleware,layer=0)

KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_HOST','polyswarmd:31337')
PASSWORD = os.environ.get('PASSWORD','password')
API_KEY = os.environ.get('API_KEY', '')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
BOUNTY_DURATION = os.environ.get('BOUNTY_DURATION',25)

logging.debug('using account ' + ACCOUNT + "...")

EXPERT='0x05328f171b8c1463eafdacca478d9ee6a1d923f8'

#Description: POST self as artifact
# Params:       Duration - how long to keep bounty active for test
#                       Amount -
# return: artifact file contents
def postBounty(artifact, duration,basenonce):
        #create data for post
        headers = {'Content-Type': 'application/json'}
        postnonce = ''
        postnonce = str(basenonce)
        logging.debug('base nonce is ' + postnonce)
        data = dict()
        data['amount']=artifact.bid
        data['uri']=artifact.uri
        data['duration']=duration

        url = 'http://'+HOST+'/bounties?account='+ACCOUNT+'&base_nonce='+postnonce
        response = ''
        logging.debug('attempting to post bounty: ' + artifact.uri + ' to: ' + url + '\n*****************************')
        try:
                response = requests.post(url, headers=headers, data=json.dumps(data))
        except:
                logging.debug("Error in artifact.postBounty: ", sys.exc_info())
                logging.debug(artifact.file.name +" bounty not posted.")


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
        r = requests.post('http://' + HOST + '/transactions', json={'transactions': signed})
        logging.debug(r.json())
        if r.json()['status'] == 'OK':
            logging.info("\n\nBounty "+artifact.file.name+" sent to polyswarmd.\n\n")
        else:
            logging.warning("BOUNTY NOT POSTED!!!!!!!!!!! CHECK TX")

def jsonify(encoded):
        decoded = '';
        try:
                decoded = encoded.json()
        except ValueError:
                logging.debug('account: ' +ACCOUNT.upper())

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
        headers = {'Authorization': API_KEY}
        nonce=json.loads(requests.get('http://'+HOST + '/nonce', headers=headers).text)['result']
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

                artifact = artifactArr[curArtifact]
                #will need to change time to account for
                postBounty(artifact, BOUNTY_DURATION,nonce)
                logging.debug('posted bounty with nonce '+ str(nonce))
                nonce +=2
                bountyArr.append(artifact)
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

def post_transaction(transactions, key):
    signed = []

    for tx in transactions:
        s = web3.eth.account.signTransaction(tx, key)
        raw = bytes(s['rawTransaction']).hex()
        signed.append(raw)

    r = requests.post('http://' + HOST + '/transactions', json={'transactions': signed})

    return r

def sign_state(state, private_key):
    state_hash = defunct_hash_message(text=state)
    signed_state = w3.eth.account.signHash(state_hash, private_key=private_key)

    return signed_state

def gen_state(**kwargs):

    print(kwargs)

    r = requests.post('http://' + HOST + '/offers/state', json=kwargs)
    return (r.json())


if __name__ == "__main__":
        # TODO: Create cli option to select offers or bounties
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
>>>>>>> add auto dispute
