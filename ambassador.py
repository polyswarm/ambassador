import aiohttp
import asyncio
import json
import sys
import os
import asyncio
import logging

from web3.auto import w3 as web3

logging.basicConfig(level=logging.INFO)

KEYFILE = os.environ.get('KEYFILE', 'keyfile')
POLYSWARMD_ADDR = os.environ.get('POLYSWARMD_ADDR', 'polyswarmd:31337')
PASSWORD = os.environ.get('PASSWORD', 'password')
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY', './bounties/')
MINIMUM_AMOUNT = 62500000000000000
BOUNTY_DURATION = os.environ.get('BOUNTY_DURATION', 25)

def check_response(response):
    """Check the status of responses from polyswarmd

    Args:
        response: Response dict parsed from JSON from polyswarmd
    Returns:
        (bool): True if successful else False
    """
    return response['status'] == 'OK'


def is_valid_ipfs_hash(ipfs_hash):
    """Check if a string represents a valid IPFS multihash

    Args:
        ipfs_hash (str): String to check
    Returns:
        (bool): True if valid IPFS multihash value else False
    """
    # TODO: Further multihash validation
    try:
        return len(ipfs_hash) < 100 and base58.b58decode(ipfs_hash)
    except:
        pass

    return False


class Ambassador(object):
    """Example ambassador, interacts with polyswarmd to post bounties"""

    def __init__(self,
                 polyswarmd_addr,
                 keyfile,
                 password,
                 artifact_directory,
                 cert=None,
                 cert_password=None):
        """Initialize an ambassador

        Args:
            polyswarmd_addr (str): Address of polyswarmd
            keyfile (str): Path to private key file to use to sign transactions
            password (str): Password to decrypt the encrypted private key
            artifact_directory (str): Path of directory containing artifacts
            cert (str): Optional PEM file containing client TLS certificate
            cert_password (str): Optional password with which to decrypt the client TLS certificate
        """
        self.polyswarmd_addr = polyswarmd_addr

        with open(keyfile, 'r') as f:
            self.priv_key = web3.eth.account.decrypt(f.read(), password)

        self.address = web3.eth.account.privateKeyToAccount(
            self.priv_key).address
        logging.info('Using account: %s', self.address)

        self.files = os.listdir(artifact_directory)

        self.cert = cert
        self.cert_password = cert_password

    def run(self, n=2):
        """Posts a number of bounties equal to or less than num files we have

        Args:
            n (int): Number of bounties to post
        """

        n = min(n, len(self.files))

        async with aiohttp.ClientSession() as session:
            for i in range(n):
                uri = await self.__post_artifact(session, self.files[i])
                if not uri:
                    logging.error('Error uploading artifact: %s', self.files[i])

                bounties = await self.__post_bounty(session, uri, MINIMUM_AMOUNT, BOUNTY_DURATION)
                logging.info('Posted bounties: %s', bounties)

    async def __post_artifact(self, session, path, name=None):
       """Post an artifact from path and return IPFS hash

        Args:
            session (aiohttp.ClientSession): Client session
            path (str): Path to a file
            name (str): Optional artifact name, if ommitted os.path.basename(path)

        Returns:
            (str): IPFS hash referring to artifact
        """
        if name is None:
            name = os.path.basename(path)

        protocol = 'http' if not self.cert else 'https'
        uri = '{0}://{1}/artifacts/'.format(protocol, self.polyswarmd_addr)
        data = aiohttp.FormData()
        data.add_field('file',
                open(path, 'rb'),
                filename=name,
                content_type='application/octet-stream')
        async with session.post(uri, data=data) as response:
            j = await response.json()
            return j.get('result')


    async def __post_transactions(self, session, transactions):
        """Post a set of (signed) transactions to Ethereum via polyswarmd, parsing the emitted events

        Args:
            session (aiohttp.ClientSession): Client sesssion
            transactions (List[Transaction]): The transactions to sign and post
        Returns:
            Response JSON parsed from polyswarmd containing emitted events
        """
        signed = []
        for tx in transactions:
            s = web3.eth.account.signTransaction(tx, self.priv_key)
            raw = bytes(s['rawTransaction']).hex()
            signed.append(raw)

        protocol = 'http' if not self.cert else 'https'
        uri = '{0}://{1}/transactions'.format(protocol, self.polyswarmd_addr)

        async with session.post(
                uri, json={'transactions': signed}) as response:
            j = await response.json()
            if self.testing >= 0 and 'errors' in j.get('result', {}):
                logging.error('Received transaction error in testing mode: %s',
                              j)
                sys.exit(1)

            return j


    async def __post_bounty(self, session, uri, amount, duration):
        """Post a bounty to polyswarmd

        Args:
            session (aiohttp.ClientSession): Client sesssion
            uri (str): URI of the bounty
            amount (int): Amount of the bounty
            duration (int): Duration of the bounty
        Returns:
            Response JSON parsed from polyswarmd containing emitted events
        """
        protocol = 'http' if not self.cert else 'https'
        uri = '{0}://{1}/bounties?account={3}'.format(protocol, self.polyswarmd_addr, self.address)
        bounty = {
            'amount': str(amount),
            'uri': uri,
            'duration': duration,
        }

        async with session.post(uri, json=bounty) as response:
            response = await response.json()

        if not check_response(response):
            return []

        response = await self.__post_transactions(
            session, response['result']['transactions'])

        if not check_response(response):
            return []

        try:
            return response['result']['bounties']
        except:
            logging.warning('expected bounty, got: %s', response)
            return []


if __name__ == "__main__":
    ambassador = Ambassador(POLYSWARMD_ADDDR, KEYFILE, PASSWORD, ARTIFACT_DIRECTORY)
    ambassador.run()
