import click
import logging
import sys
from artifacts import File, Artifact
import os
from web3.auto import w3 as web3
from web3 import Web3,HTTPProvider
from web3.middleware import geth_poa_middleware
from test import run_test

@click.command()
@click.option('--log', default='DEBUG',
        help='Logging level')
@click.option('--polyswarmd-addr', envvar='POLYSWARMD_HOST', default='localhost:31337',
        help='Address of polyswarmd instance')
@click.option('--keyfile', envvar='MICROENGINE_KEYFILE', type=click.Path(exists=True), default='keyfile',
        help='Keystore file containing the private key to use with this microengine')
@click.option('--password', envvar='KEYFILE_PASSWORD', prompt=True, hide_input=True,
        help='Password to decrypt the keyfile with')
@click.option('--bounty-directory', envvar='BOUNTY_DIRECTORY', type=click.Path(exists=True),
        help='Directory with file you want to submit for bounties')
@click.option('--bid', default=0,
        help='Bid for the bounties you want to submit')
@click.option('--duration', default=0,
        help='How long you want the bounties to run')
@click.option('--api-key', envvar='API_KEY', default='',
        help='API key to use with polyswarmd')
@click.option('--artifact_number', envvar='NUM_TO_POST', default=100000,
        help='run in testing mode')
@click.option('--testing', envvar='TESTING', default=False,
        help='run in testing mode')

def main(log, polyswarmd_addr, keyfile, password, bounty_directory, bid, duration, api_key, artifact_number, testing):
    loglevel = getattr(logging, log.upper(), None)
    priv_key = None
    address = None

    if testing:
        run_test()
    else:
        with open(keyfile, 'r') as f:
            priv_key = web3.eth.account.decrypt(f.read(), password)

        address = web3.eth.account.privateKeyToAccount(priv_key).address
        
        logging.info('Using account: %s', address)
        file_count = 0
        if bounty_directory != None:
            for file in os.listdir(bounty_directory):
                if file_count < artifact_number:
                    artifact = Artifact(File(file, bounty_directory), bid, polyswarmd_addr, api_key)
                    artifact.postArtifact()
                    artifact.postBounty(duration, keyfile, password, address)


if __name__ ==  '__main__':
    main()
