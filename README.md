# SECURITY WARNING

`ambassador` implicitly trusts transaction signing requests from `polyswarmd`.
A malicious instance of `polyswarmd` or an attacker with sufficient network capabilities may abuse this trust relationship to cause `ambassador` to transfer all NCT, ETH or other tokens to an attacker address.

Therefore: 
1. **ONLY CONNECT `ambassador` TO `polyswarmd` INSTANCES THAT YOU TRUST**
2. **DO NOT ALLOW `ambassador` <-> `polyswarmd` COMMUNICATIONS TO TRAVERSE AN UNTRUSTED NETWORK LINK**

In other words, only run `ambassador` on a co-located `localhost` with `polyswarmd`.

This is a temporarily limitation - `ambassador`'s trust in `polyswarmd` will be eliminated in the near future.

# Introduction

`docker build -t polyswarm/ambassador -f docker/Dockerfile .`

This repo is for pumping malware through polyswarmd, for use with the `test.yml`, `tutorial[,1,2]` files of `polyswarm/orchestration` repo

## Configuration
By default, this program will only post 2 bounties, located in `ambassador/bounties`. You can tell it to post more via command line argument like so: `python3 ambassador.py 150`. 

If you are using this code in something other than our `dockerized` setup (located [here](https://github.com/polyswarm/orchestration) in `dev.yml`,`test.yml`, `tutorial[,1,2].yml`), you will need to likely overwrite these following default values with environment variables that correspond to your setup.
```py
w3=Web3(HTTPProvider(os.environ.get('GETH_ADDR','http://geth:8545')))
KEYFILE = os.environ.get('KEYFILE','keyfile')
HOST = os.environ.get('POLYSWARMD_ADDR','polyswarmd:31337')
PASSWORD = os.environ.get('PASSWORD','password')
ACCOUNT = '0x' + json.loads(open(KEYFILE,'r').read())['address']
ARTIFACT_DIRECTORY = os.environ.get('ARTIFACT_DIRECTORY','./bounties/')
```