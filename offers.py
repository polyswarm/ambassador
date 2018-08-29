import aiohttp
import asyncio
import base58
import functools
import json
import logging
import sys
import websockets

from queue import PriorityQueue
from web3.auto import w3 as web3
import os

import uuid
from uuid import UUID
import logging

from time import sleep
from eth_account.messages import defunct_hash_message
from web3 import Web3,HTTPProvider
from web3.middleware import geth_poa_middleware
from artifacts import File, Artifact
from queue import Queue

import click
import logging
import sys

logging.basicConfig(level=logging.INFO)

ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_ADDR','polyswarmd:31337')
PASSWORD = os.environ.get('PASSWORD','password')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
logging.debug('using account ' + ACCOUNT + "...")
API_KEY = os.environ.get('API_KEY', '')
headers = { 'Authorization': API_KEY }
EXPERT= os.environ.get('OFFER_EXPERT', '0x05328f171b8c1463eafdacca478d9ee6a1d923f8')

HOST = os.environ.get('POLYSWARMD_ADDR','polyswarmd:31337')
priv_key = web3.eth.account.decrypt(open(KEYFILE,'r').read(), PASSWORD)

class OfferChannel(object):
    def __init__(self, guid, offer_amount, ambassador_balance, expert_balance, offer_directory = None):
        self.guid = guid
        self.offer_amount = offer_amount
        self.ambassador_balance = ambassador_balance
        self.expert_balance = expert_balance
        self.nonce = 0
        self.last_message = None
        self.artifacts = Queue()

        if offer_directory != None:
            for file in os.listdir(offer_directory):
                artifact = Artifact(File(file, offer_directory))
                artifact.postArtifact()
                self.artifacts.put(artifact)

    def set_state(self, state):
        # TODO: change to be a persistant database so all the assersions can be saved
        # cureent saving jest the last state/signiture for disputes
        self.last_message = state

    def get_next_artifact(self):
        if not self.artifacts.empty():
            return self.artifacts.get()

    def __eq__(self, other):
        return self.guid == other.guid

    def __lt__(self, other):
        return self.guid < other.guid


async def post_transactions(session, transactions):
    """Post a set of (signed) transactions to Ethereum via polyswarmd, parsing the emitted events

    Args:
        session (aiohttp.ClientSession): Client sesssion
        transactions (List[Transaction]): The transactions to sign and post
    Returns:
        Response JSON parsed from polyswarmd containing emitted events
    """
    signed = []
    for tx in transactions:
        s = web3.eth.account.signTransaction(tx, priv_key)
        raw = bytes(s['rawTransaction']).hex()
        signed.append(raw)

    uri = 'http://{0}/transactions'.format(HOST)

    async with session.post(uri, json={'transactions': signed}) as response:
        j = await response.json()

        return j

async def generate_state(session, **kwargs):
    async with session.post('http://' + HOST + '/offers/state', json=kwargs) as response:
        return (await response.json())['result']['state']

async def init_offer(session):
    async with session.post('http://' + HOST + '/offers?account=' + ACCOUNT, json={'ambassador': ACCOUNT, 'expert': EXPERT, 'settlementPeriodLength': 100}) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    offer_info = (await post_transactions(session, transactions))['result']['offers_initialized'][0] # TODO this array is weird - should be a dict

    return offer_info

async def open_offer(session, guid, signiture):
    async with session.post('http://' + HOST + '/offers/' + guid + '/open?account=' + ACCOUNT, json=signiture) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret


async def run_sockets(testing, loop = False):

    tasks = [create_and_open_offer(loop, testing)]

    await asyncio.gather(*tasks)

async def send_offer(session, ws, offer_channel, current_state):

    if current_state['state']['nonce'] == offer_channel.nonce:
        artifact = offer_channel.get_next_artifact()
        if artifact:
            state = await generate_state(session, close_flag=1, nonce=offer_channel.nonce, ambassador=ACCOUNT, expert=EXPERT, msig_address= current_state['state']['msig_address'], ambassador_balance= current_state['state']['ambassador_balance'], expert_balance= current_state['state']['expert_balance'], artifact_hash=artifact.uri, guid=str(offer_channel.guid.int), offer_amount=offer_channel.offer_amount)
            sig = sign_state(state, priv_key)
            sig['type'] = 'offer'
            # TODO: can't fit hash on state and moving to be apart of the message object
            sig['artifact'] = artifact.uri
            await ws.send(
                json.dumps(sig)
            )                             

def create_signiture_dict(ambassador_sig, expert_sig, state):
    ret = { 'v': [], 'r': [], 's': [], 'state':state }

    ret['v'].append(ambassador_sig['v'])
    ret['r'].append(ambassador_sig['r'])
    ret['s'].append(ambassador_sig['s'])

    ret['v'].append(expert_sig['v'])
    ret['r'].append(expert_sig['r'])
    ret['s'].append(expert_sig['s'])

    return ret

async def dispute_channel(session, ws, offer_channel):
    prev_state = offer_channel.last_message
    sig = sign_state(prev_state['raw_state'], priv_key)

    async with session.post('http://' + HOST + '/offers/' + str(offer_channel.guid) + '/settle?account=' + ACCOUNT, json=create_signiture_dict(sig, prev_state, prev_state['raw_state'])) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret

async def close_channel(session, ws, offer_channel, current_state):
    sig = sign_state(current_state['raw_state'], priv_key)

    async with session.post('http://' + HOST + '/offers/' + str(offer_channel.guid) + '/close?account=' + ACCOUNT, json=create_signiture_dict(sig, current_state, current_state['raw_state'])) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret

async def challenge_settle(session, ws, offer_channel):
    prev_state = offer_channel.last_message

    sig = sign_state(prev_state['raw_state'], priv_key)

    async with session.post('http://' + HOST + '/offers/' + str(offer_channel.guid) + '/challenge?account=' + ACCOUNT, json=create_signiture_dict(sig, prev_state, prev_state['raw_state'])) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret

async def accept_state(session, ws, offer_channel, current_state):
    # need to sign and echo state back to the expert
    # check that the guid is current
    # checkout that the offer amount is the same
    # check that the balances are correct

    # TODO: Check signiture came from right participant

    if current_state['state']['nonce'] == offer_channel.nonce + 1 and offer_channel.ambassador_balance == current_state['state']['ambassador_balance'] + offer_channel.offer_amount and offer_channel.expert_balance == current_state['state']['expert_balance'] - offer_channel.offer_amount and current_state['state']['guid'] == offer_channel.guid.int and 'verdicts' in current_state['state']:
        offer_channel.nonce += 1
        offer_channel.ambassador_balance = current_state['state']['ambassador_balance']
        offer_channel.expert_balance = current_state['state']['expert_balance']

        sig = sign_state(current_state['raw_state'], priv_key)
        sig['type'] = 'payout'
        await ws.send(
            json.dumps(sig)
        )
        return True
    else:
        return False


async def create_and_open_offer(loop, testing):
    async with aiohttp.ClientSession(headers=headers) as session:
        offer_info = await init_offer(session)
        offer_amount = 1
        ambassador_balance = 30
        expert_balance = 0
        nonce = 0

        # TODO polyswarmd should be sending over the string version of ids
        guid = UUID(int=offer_info['guid'], version=4)
        msig = offer_info['msig']
        state = await generate_state(session, close_flag=1, nonce=nonce, ambassador=ACCOUNT, expert=EXPERT, msig_address=msig, ambassador_balance=ambassador_balance, expert_balance=expert_balance, guid=str(guid.int), offer_amount=1)
        sig = sign_state(state, priv_key)
        open_message = await open_offer(session, str(guid), sig)
        sig['type'] = 'open'
        offer_channel = OfferChannel(guid, offer_amount, ambassador_balance, expert_balance, ARTIFACT_DIRECTORY)
        tasks = [listen_for_messages(offer_channel, testing, sig), listen_for_offer_events(offer_channel)]

        await asyncio.gather(*tasks)

def sign_state(state, private_key):
    def to_32byte_hex(val):
       return web3.toHex(web3.toBytes(val).rjust(32, b'\0'))

    state_hash = to_32byte_hex(web3.sha3(hexstr=state))
    state_hash = defunct_hash_message(hexstr=state_hash)
    sig = web3.eth.account.signHash((state_hash), private_key=private_key)

    return {'r':web3.toHex(sig.r), 'v':sig.v, 's':web3.toHex(sig.s), 'state': state}

async def listen_for_messages(offer_channel, testing=False, init_message = None):
    uri = 'ws://{0}/messages/{1}'.format(HOST, offer_channel.guid)
    async with aiohttp.ClientSession(headers=headers) as session:
        async with websockets.connect(uri, extra_headers=headers) as ws:
            # send open message on init
            if init_message != None:
                await ws.send(
                    json.dumps(init_message)
                )

            while not ws.closed:
                msg = json.loads(await ws.recv())
                if msg['type'] == 'decline':
                    pass
                elif msg['type'] == 'accept':
                    accepted = await accept_state(session, ws, offer_channel, msg)

                    if accepted and testing:
                        await close_channel(session, ws, offer_channel, offer_channel.last_message)
                        sys.exit(0)

                    if accepted:
                        offer_channel.set_state(msg)
                        await send_offer(session, ws, offer_channel, msg)
                    elif offer_channel.last_message['state']['isClosed'] == 1:
                        await close_channel(session, ws, offer_channel, offer_channel.last_message)
                    else:
                        await dispute_channel(session, ws, offer_channel)

                elif msg['type'] == 'join':
                    await send_offer(session, ws, offer_channel, msg)
                    offer_channel.set_state(msg)

                elif msg['type'] == 'close':
                    await close_channel(session, ws, offer_channel, msg)


async def listen_for_offer_events(offer_channel):
    uri = 'ws://{0}/events/{1}'.format(HOST, offer_channel.guid)
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with websockets.connect(uri, extra_headers=headers) as ws:
                while not ws.closed:
                    event = json.loads(await ws.recv())

                    if event['event'] == 'closed_agreement':
                        ws.close()
                        pass
                    elif event['event'] == 'settle_started':
                        nonce = int(event['data']['nonce'])
                        if nonce < offer_channel.nonce:
                            await challenge_settle(session, ws, offer_channel, offer_channel.last_message)
                    elif event['event'] == 'settle_challenged':
                        if nonce < offer_channel.nonce:
                            await challenge_settle(session, ws, offer_channel, offer_channel.last_message)

    except Exception as e:
        raise e
    else:
        pass


@click.command()
@click.option('--testing', default=False,
        help='Activate testing mode for integration testing, respond to 2 offers then exit')

def run(testing=False):

    # will create an offer, wait for it to be joined, and send all the offers in ARTIFACT_DIRECTORY to the OFFER_EXPERT
    # when testing is true the script exits with 0 and closes the offer after receiving two offers

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_sockets(testing, loop))
    finally:
        loop.close()


if __name__ ==  '__main__':
    run()
