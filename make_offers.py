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
from websocket import create_connection

from time import sleep
from eth_account.messages import defunct_hash_message
from web3 import Web3,HTTPProvider
from web3.middleware import geth_poa_middleware

logging.basicConfig(level=logging.INFO)

KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_ADDR','localhost:31337')
PASSWORD = os.environ.get('PASSWORD','password')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
offer_nonce = 0
logging.debug('using account ' + ACCOUNT + "...")

EXPERT='0x05328f171b8c1463eafdacca478d9ee6a1d923f8'

HOST = os.environ.get('POLYSWARMD_ADDR','localhost:31337')
priv_key = web3.eth.account.decrypt(open(KEYFILE,'r').read(), PASSWORD)

class OfferChannel(object):
    """An assertion which has yet to be publically revealed"""

    def __init__(self, guid, offer_amount):
        """Initialize a secret assertion

        Args:
            guid (str): GUID of the bounty being asserted on
            index (int): Index of the assertion to reveal
            nonce (str): Secret nonce used to reveal assertion
            verdicts (List[bool]): List of verdicts for each artifact in the bounty
            metadata (str): Optional metadata
        """
        self.guid = guid
        self.offer_amount = offer_amount
        self.nonce = 0

    def save_assersion_state(self, state):
        # TODO: change to be a persistant database, mongo?
        pass

    def __eq__(self, other):
        return self.guid == other.guid

    def __lt__(self, other):
        return self.guid < other.guid


async def post_transactions(session, transactions):
    """Post a set of (signed) transactions to Ethereum via polyswarmd, parsing the emitted events

    Args:
        microengine (Microengine): The microengine instance
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
    """Post a set of (signed) tran sactions to Ethereum via polyswarmd, parsing the emitted events

    Args:
        microengine (Microengine): The microengine instance
        session (aiohttp.ClientSession): Client sesssion
        transactions (List[Transaction]): The transactions to sign and post
    Returns:
        Response JSON parsed from polyswarmd containing emitted events
    """
    async with session.post('http://' + HOST + '/offers?account=' + ACCOUNT, json={'ambassador': ACCOUNT, 'expert': EXPERT, 'settlementPeriodLength': 100}) as response:
        response = await response.json()

    transactions = response['result']['transactions']
    offer_info = (await post_transactions(session, transactions))['result']['offers_initialized'][0] # TODO this array is weird - should be a dict

    return offer_info

async def open_offer(session, guid, signiture):
    """Post a set of (signed) transactions to Ethereum via polyswarmd, parsing the emitted events

    Args:
        microengine (Microengine): The microengine instance
        session (aiohttp.ClientSession): Client sesssion
        transactions (List[Transaction]): The transactions to sign and post
    Returns:
        Response JSON parsed from polyswarmd containing emitted events
    """

    async with session.post('http://' + HOST + '/offers/' + guid + '/open?account=' + ACCOUNT, json=signiture) as response:
        response = await response.json()

    transactions = response['result']['transactions']

    ret = await post_transactions(session, transactions)

    return ret


async def run_sockets(testing, offers, loop = False):
    """Run this microengine

    Args:
        testing (int): Mode to process N bounties then exit (optional)
    """
    testing = testing
    offers = offers
# asyncio.ensure_future(listen_for_offers(loop)),
    tasks = [create_and_open_offer()]


    # if offers:
    #     tasks.append(asyncio.ensure_future(listen_for_offers(loop)))

    await asyncio.gather(*tasks)

def run(testing=-1, offers=True):

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_sockets(testing, offers, loop))
    finally:
        loop.close()

async def send_offer(session, ws, offer_channel, current_state):
    if current_state['state']['nonce'] == offer_channel.nonce:
        state = await generate_state(session, close_flag=1, nonce=offer_channel.nonce, ambassador=ACCOUNT, expert=EXPERT, msig_address= current_state['state']['msig_address'], ambassador_balance= current_state['state']['ambassador_balance'] - offer_channel.offer_amount, expert_balance= current_state['state']['expert_balance'] + offer_channel.offer_amount, ipfs_hash='test', guid=str(offer_channel.guid.int), offer_amount=offer_channel.offer_amount)
        sig = sign_state(state, priv_key)
        sig['type'] = 'offer'
        ws.send(
            json.dumps(sig)
        )

async def accept_state(session, ws, offer_channel, current_state):
    # need to sign and echo state back to the expert
    # check that the guid is corrent
    # checkout that the offer amount is the same
    # check that the balances are correct

    if current_state['state']['nonce'] == offer_channel.nonce + 1 and current_state['state']['ambassador_balance'] == current_state['ambassador_balance'] - offer_channel.offer_amount and current_state['state']['expert_balance'] == current_state['expert_balance'] + offer_channel.offer_amount and current_state['state']['guid'] == str(offer_channel.guid.int) and 'verdicts' in current_state:
        offer_channel.nonce += 1
        sig = sign_state(current_state, priv_key)
        sig['type'] = 'accept'

        await ws.send(
            json.dumps(sig)
        )


async def listen_for_messages(offer_channel, init_message = None):
    uri = 'ws://{0}/messages/{1}'.format(HOST, offer_channel.guid)
    async with aiohttp.ClientSession() as session:
        async with websockets.connect(uri) as ws:
            # send open message
            if init_message != None:
                await ws.send(
                    json.dumps(init_message)
                )

            while not ws.closed:
                print(offer_channel.guid)
                msg = json.loads(await ws.recv())
                if msg['type'] == 'decline':
                    pass
                elif msg['type'] == 'accept':
                    offer_channel.save_assersion_state(msg)

                    await accept_state(session, ws, offer_channel)
                    await send_offer(session, ws, offer_channel)

                elif msg['type'] == 'join':
                    await send_offer(session, ws, offer_channel, msg)

                elif msg['type'] == 'dispute':
                    pass
                elif msg['type'] == 'close':
                    pass

async def create_and_open_offer():
    async with aiohttp.ClientSession() as session:
        offer_info = await init_offer(session)
        offer_amount = 1
        # TODO polyswarmd should be sending over the string version of ids
        guid = UUID(int=offer_info['guid'], version=4)
        msig = offer_info['msig']
        state = await generate_state(session, close_flag=1, nonce=0, ambassador=ACCOUNT, expert=EXPERT, msig_address=msig, ambassador_balance=30, expert_balance=0, guid=str(guid.int), offer_amount=1)
        sig = sign_state(state, priv_key)
        open_message = await open_offer(session, str(guid), sig)
        sig['to_socket'] = 'ws://' + HOST + '/' + 'messages/' + str(guid)
        sig['from_socket'] = 'ws://localhost:31337/a9976b63-4384-4762-b931-7f4bff7cb672/messages'
        sig['type'] = 'open'
        offer_channel = OfferChannel(guid, offer_amount)

        await listen_for_messages(offer_channel, sig)

def sign_state(state, private_key):
    def to_32byte_hex(val):
       return web3.toHex(web3.toBytes(val).rjust(32, b'\0'))

    state_hash = to_32byte_hex(web3.sha3(hexstr=state))
    state_hash = defunct_hash_message(hexstr=state_hash)
    sig = web3.eth.account.signHash((state_hash), private_key=private_key)

    return {'r':web3.toHex(sig.r), 'v':sig.v, 's':web3.toHex(sig.s), 'state': state}

async def listen_for_offers(loop):
    """Listen for events via websocket connection to polyswarmd

    Args:
        microengine (Microengine): The microengine instance
    """
    uri = 'ws://{0}/events'.format(HOST)
    async with aiohttp.ClientSession() as session:
        async with websockets.connect(uri) as ws:
            while not ws.closed:
                event = json.loads(await ws.recv())
                print('Event from offers function %s', event)

                # if event['event'] == 'initialized_channel':
                #     print(event['data']['guid'])
                #     # loop.run_until_complete()
                #     # task = [(asyncio.ensure_future()]

                #     task = loop.create_task(listen_for_messages(event['data']['guid']))

if __name__ == "__main__":
        # TODO: Create cli option to select offers or bounties        
        run()

