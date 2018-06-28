#! /usr/bin/env python

import asyncio
import json
import websockets

from web3.auto import w3 as web3

POLYSWARMD_URI = 'ws://polyswarmd:31337/transactions'
KEYFILE = 'keyfile'
PASSWORD = 'password'


@asyncio.coroutine
def txsigner():
    websocket = yield from websockets.connect(POLYSWARMD_URI)

    with open(KEYFILE, 'r') as f:
        g=f
        key = web3.eth.account.decrypt(f.read(), PASSWORD)
        acct = json.loads(g.read())
        acct = '0x'+ acct['address']
    try:
        while websocket.open:
            msg = yield from websocket.recv()
            msg = json.loads(msg)
            if (msg['to']==acct):
                id_ = msg['id']
                tx = msg['data']
                chainId = tx['chainId']

                signed = web3.eth.account.signTransaction(tx, key)
                data = bytes(signed['rawTransaction']).hex()

                print(tx, data)

                reply = {
                    'id': id_,
                    'chainId': chainId,
                    'data': data,
                }

                print(reply)

                yield from websocket.send(json.dumps(reply))
    finally:
        yield from websocket.close()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(txsigner())
