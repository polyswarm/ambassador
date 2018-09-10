import click
import logging
import sys
from artifacts import File, Artifact
import os
import json
from web3.auto import w3 as web3
from web3 import Web3,HTTPProvider
from web3.middleware import geth_poa_middleware
from bounties import run_test as run_bounties 
from offers import run as run_offers

KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_HOST','localhost:31337')
PASSWORD = os.environ.get('PASSWORD','password')
API_KEY = os.environ.get('API_KEY', '')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
BOUNTY_DURATION = os.environ.get('BOUNTY_DURATION',25)
BID = os.environ.get('BID','625000000000000000')

@click.command()
@click.option('--log', default='INFO',
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
@click.option('--testing', envvar='TESTING', default=-1,
        help='Activate testing mode for integration testing, send N bounties and N offers then exit')
@click.option('--api-key', envvar='API_KEY', default=API_KEY,
        help='API key to use with polyswarmd')
@click.option('--offers', envvar='OFFERS', default=False, is_flag=True,
        help='Should the abassador send offers')

def main(log, polyswarmd_addr, keyfile, password, bounty_directory, bid, duration, testing, api_key, offers):
    loglevel = getattr(logging, log.upper(), None)
    priv_key = None
    address = None
    testing = int(testing)
    account = '0x' + json.loads(open(keyfile,'r').read())['address']

    logging.info('using account + %s + ...', ACCOUNT)


    run_bounties(polyswarmd_addr, keyfile, password, bounty_directory, bid, duration, api_key, account)

    for i in range(0, testing):
        logging.debug('testing: %s ...', i)
        run_bounties(polyswarmd_addr, keyfile, password, bounty_directory, bid, duration, api_key, account)

    if offers:
        run_offers(testing)

    sys.exit(0)

if __name__ ==  '__main__':
    main()

