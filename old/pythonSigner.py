#! /usr/bin/env python

import asyncio
import json
import websockets

from websockets.exceptions import ConnectionClosed
from web3.auto import w3 as web3

POLYSWARMD_URI = 'ws://polyswarmd:31337/transactions'
KEYFILE = 'keyfile'
PASSWORD = 'password'
f = open(KEYFILE,'r')
acct = json.loads(f.read())
acct = '0x'+ acct['address']
print("signer init: using account: "+acct)
@asyncio.coroutine
def txsigner(account):
    websocket = yield from websockets.connect(POLYSWARMD_URI)

    with open(KEYFILE, 'r') as f:
        key = web3.eth.account.decrypt(f.read(), PASSWORD)
    try:
        while websocket.open:
            print ("websocket is open. account in use: "+account)
            msg = yield from websocket.recv()
            msg = json.loads(msg)
            msgto = ''+msg['to']
            print (msgto.upper()==account.upper())
#            if (msgto.upper()!=account.upper()):
#                print ('closing socket..')
#                websocket.close()
            print ('to field of message:'+msg['to'])
            if (msgto.upper()==account.upper()):
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
    print("signer main: account is"+acct)
    while True:
        try:
            asyncio.get_event_loop().run_until_complete(txsigner(acct))
        except ConnectionClosed as e:
            print('Hit a connectionclosed event - attempting to restart : ' + str(e))
