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
from pprint import pprint, pformat
import click
import logging
import sys

logging.basicConfig(level=logging.INFO)

OFFER_AMOUNT = os.environ.get('OFFER_AMOUNT', 2500000000000000)
AMBASSADOR_BALANCE = os.environ.get('AMBASSADOR_BALANCE', 90000000000000000)
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_ADDR','polyswarmd:31337')
PASSWORD = os.environ.get('PASSWORD','password')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
logging.info('using account ' + ACCOUNT + "...")
API_KEY = os.environ.get('API_KEY', '')
headers = { 'Authorization': API_KEY }
EXPERT= os.environ.get('OFFER_EXPERT', '0x05328f171b8c1463eafdacca478d9ee6a1d923f8')

priv_key = web3.eth.account.decrypt(open(KEYFILE,'r').read(), PASSWORD)

class OfferChannel(object):
    def __init__(self, guid, offer_amount, ambassador_balance, expert_balance, offer_directory = None, testing=0):
        self.guid = guid
        self.offer_amount = offer_amount
        self.ambassador_balance = ambassador_balance
        self.expert_balance = expert_balance
        self.nonce = 0
        self.last_message = None
        self.artifacts = Queue()
        self.testing = testing
        self.event_socket = None
        self.msg_socket = None

        if offer_directory != None:
            for testing_count in range(0, testing):
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

    async def close_sockets(self):
        if self.event_socket:
            await self.event_socket.close()

        if self.msg_socket:
            await self.msg_socket.close()

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

    async with session.post(uri, json={'transactions': signed}, params={'account': ACCOUNT}) as response:
        j = await response.json()

        return j

async def generate_state(session, **kwargs):
    async with session.post('http://' + HOST + '/offers/state', json=kwargs, params={'account': ACCOUNT}) as response:
        return (await response.json())['result']['state']

async def init_offer(session):
    async with session.post('http://' + HOST + '/offers?account=' + ACCOUNT, json={'ambassador': ACCOUNT, 'expert': EXPERT, 'settlementPeriodLength': 10 }) as response:
        response = await response.json()

    transactions = response['result']['transactions']
    offer_info = await post_transactions(session, transactions)
    offer_info = offer_info['result']['offers_initialized'][0]

    return offer_info

async def open_offer(session, guid, signiture):
    async with session.post('http://' + HOST + '/offers/' + guid + '/open?account=' + ACCOUNT, json=signiture) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret


async def run_sockets(testing, loop = False):
    if testing > 0:
        # testing 1 dispute
        await create_offer_dispute(loop, 1)

    await create_and_open_offer(loop, testing)

async def send_offer(session, ws, offer_channel, current_state):
    if current_state['state']['nonce'] == offer_channel.nonce:
        artifact = offer_channel.get_next_artifact()
        if artifact:
            offer_state = dict(offer_channel.last_message['state'])
            offer_state['close_flag'] = 1
            offer_state['artifact_hash'] = artifact.uri
            offer_state['nonce'] = offer_channel.nonce # this is the updated nonce
            offer_state['offer_amount'] = offer_channel.offer_amount
            offer_state['guid'] = str(offer_channel.guid.int)

            # delete previous offer verdicts/mask
            if 'verdicts' in offer_state:
                del offer_state['verdicts']

            if 'mask' in offer_state:
                del offer_state['mask']

            state = await generate_state(session, **offer_state)
            sig = sign_state(state, priv_key)

            sig['type'] = 'offer'
            sig['artifact'] = artifact.uri

            logging.info('Sending New Offer: \n%s', pformat(offer_state))

            await ws.send(
                json.dumps(sig)
            )                                        

def create_signiture_dict(ambassador_sig, expert_sig, state):
    ret = { 'v': [], 'r': [], 's': [], 'state':state }

    ret['v'].append(int(ambassador_sig['v']))
    ret['r'].append(ambassador_sig['r'])
    ret['s'].append(ambassador_sig['s'])

    ret['v'].append(int(expert_sig['v']))
    ret['r'].append(expert_sig['r'])
    ret['s'].append(expert_sig['s'])

    return ret

async def dispute_channel(session, ws, offer_channel):
    prev_state = offer_channel.last_message
    sig = sign_state(prev_state['raw_state'], priv_key)

    async with session.post('http://' + HOST + '/offers/' + str(offer_channel.guid) + '/settle?account=' + ACCOUNT,
        json=create_signiture_dict(sig, prev_state, prev_state['raw_state'])) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret

async def close_channel(session, ws, offer_channel, current_state):
    sig = sign_state(current_state['raw_state'], priv_key)

    async with session.post('http://' + HOST + '/offers/' + str(offer_channel.guid) + '/close?account=' + ACCOUNT,
        json=create_signiture_dict(sig, current_state, current_state['raw_state'])) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret

async def challenge_settle(session, ws, offer_channel):
    prev_state = offer_channel.last_message

    sig = sign_state(prev_state['raw_state'], priv_key)

    async with session.post('http://' + HOST + '/offers/' + str(offer_channel.guid) + '/challenge?account=' + ACCOUNT,
        json=create_signiture_dict(sig, prev_state, prev_state['raw_state'])) as response:
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
        offer_amount = OFFER_AMOUNT
        ambassador_balance = AMBASSADOR_BALANCE
        expert_balance = 0
        nonce = 0

        # TODO polyswarmd should be sending over the string version of ids
        guid = UUID(int=offer_info['guid'], version=4)
        msig = offer_info['msig']
        state = await generate_state(session, close_flag=1, nonce=nonce, ambassador=ACCOUNT, expert=EXPERT,
            msig_address=msig, ambassador_balance=ambassador_balance, expert_balance=expert_balance,
            guid=str(guid.int), offer_amount=offer_amount)
        sig = sign_state(state, priv_key)
        open_message = await open_offer(session, str(guid), sig)
        sig['type'] = 'open'
        offer_channel = OfferChannel(guid, offer_amount, ambassador_balance, expert_balance, ARTIFACT_DIRECTORY, testing)

        tasks = [loop.create_task(listen_for_messages(offer_channel, sig)), loop.create_task(listen_for_offer_events(offer_channel))]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        offer_channel.tasks = pending
        for pending_task in pending:
            pending_task.cancel()

async def create_offer_dispute(loop, testing):
    async with aiohttp.ClientSession(headers=headers) as session:
        offer_info = await init_offer(session)
        offer_amount = OFFER_AMOUNT
        ambassador_balance = AMBASSADOR_BALANCE
        expert_balance = 0
        nonce = 0

        # TODO polyswarmd should be sending over the string version of ids
        guid = UUID(int=offer_info['guid'], version=4)
        msig = offer_info['msig']
        state = await generate_state(session, close_flag=1, nonce=nonce, ambassador=ACCOUNT, expert=EXPERT,
            msig_address=msig, ambassador_balance=ambassador_balance, expert_balance=expert_balance,
            guid=str(guid.int), offer_amount=offer_amount)
        sig = sign_state(state, priv_key)
        open_message = await open_offer(session, str(guid), sig)
        sig['type'] = 'open'

        # change offer amount to 0 to cause a dispute
        offer_amount = 0
        offer_channel = OfferChannel(guid, offer_amount, ambassador_balance, expert_balance, ARTIFACT_DIRECTORY, testing)

        tasks = [loop.create_task(listen_for_messages(offer_channel, sig)), loop.create_task(listen_for_offer_events(offer_channel))]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        for pending_task in pending:
            pending_task.cancel()

def sign_state(state, private_key):
    def to_32byte_hex(val):
       return web3.toHex(web3.toBytes(val).rjust(32, b'\0'))

    state_hash = to_32byte_hex(web3.sha3(hexstr=state))
    state_hash = defunct_hash_message(hexstr=state_hash)
    sig = web3.eth.account.signHash((state_hash), private_key=private_key)

    return {'r':web3.toHex(sig.r), 'v':sig.v, 's':web3.toHex(sig.s), 'state': state}

async def listen_for_messages(offer_channel, init_message = None):
    uri = 'ws://{0}/messages/{1}'.format(HOST, offer_channel.guid)
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with websockets.connect(uri, extra_headers=headers) as ws:
                offer_channel.msg_socket = ws;

                # send open message on init
                if init_message != None:
                    logging.info('Sending Open Channel Message: \n%s', pformat(init_message['state']))
                    await ws.send(
                        json.dumps(init_message)
                    )

                while not ws.closed:
                    msg = json.loads(await ws.recv())
                    if msg['type'] == 'decline':
                        pass
                    elif msg['type'] == 'accept':
                        accepted = await accept_state(session, ws, offer_channel, msg)

                        if offer_channel.testing > 0:
                            offer_channel.testing = offer_channel.testing - 1
                            logging.info('Offers left to send %s', offer_channel.testing)


                        if accepted:
                            logging.info('Offer Accepted: \n%s', pformat(msg['state']))
                            offer_channel.set_state(msg)
                            await send_offer(session, ws, offer_channel, msg)
                        elif offer_channel.last_message['state']['isClosed'] == 1:
                            logging.info('Rejected State: \n%s', pformat(msg['state']))
                            logging.info('Closing channel with: \n%s', pformat(offer_channel.last_message['state']))
                            await close_channel(session, ws, offer_channel, offer_channel.last_message)
                        else:
                            logging.info('Rejected State: \n%s', pformat(msg['state']))
                            logging.info('Dispting channel with: \n%s', pformat(offer_channel.last_message['state']))
                            await dispute_channel(session, ws, offer_channel)

                        if offer_channel.testing == 0:
                            await close_channel(session, ws, offer_channel, offer_channel.last_message)
                            logging.info('Closing Channel: \n%s', pformat(msg['state']))
                            await offer_channel.close_sockets()
                            sys.exit(0)

                    elif msg['type'] == 'join':
                        offer_channel.set_state(msg)
                        logging.info('Channel Joined \n%s', pformat(msg['state']))

                        if offer_channel.testing > 0:
                            offer_channel.testing = offer_channel.testing - 1
                            logging.info('Offers left to send %s', offer_channel.testing)
                        await send_offer(session, ws, offer_channel, msg)

                    elif msg['type'] == 'close':
                        await close_channel(session, ws, offer_channel, msg)
                        await offer_channel.close_sockets()
    except Exception as e:
        logging.error('ERROR IN MESSAGE SOCKET!')
        logging.error(str(e))
        raise e
    else:
        pass

async def listen_for_offer_events(offer_channel):
    uri = 'ws://{0}/events/{1}'.format(HOST, offer_channel.guid)
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with websockets.connect(uri, extra_headers=headers) as ws:
                offer_channel.event_socket = ws;
                while not ws.closed:
                    event = json.loads(await ws.recv())

                    if event['event'] == 'closed_agreement':
                        logging.info('Offer Closed: \n%s', pformat(event['data']))

                        await offer_channel.close_sockets()

                    elif event['event'] == 'settle_started':
                        nonce = int(event['data']['nonce'])
                        logging.info('Offer Dispute Settle Started: \n%s', pformat(event['data']))

                        if nonce < offer_channel.nonce:
                            await challenge_settle(session, ws, offer_channel, offer_channel.last_message)

                    elif event['event'] == 'settle_challenged':
                        if nonce < offer_channel.nonce:
                            logging.info('Offer Dispute Settle Challenged: \n%s', pformat(event['data']))
                            await challenge_settle(session, ws, offer_channel, offer_channel.last_message)

    except Exception as e:
        logging.error('ERROR IN EVENT SOCKET!')
        logging.error(str(e))
        raise e

    else:
        pass


def run(testing=-1):
    # will create an offer, wait for it to be joined, and send all the offers in ARTIFACT_DIRECTORY to the OFFER_EXPERT
    # when `testing` is non-zero the script exits with 0 and closes the offer channel after sending payout msgs a number of time defined by `testing`

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_sockets(testing, loop))
    finally:
        loop.close()


if __name__ ==  '__main__':
    run()
