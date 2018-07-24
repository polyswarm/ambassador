# Introduction

`docker build -t polyswarm/ambassador -f docker/Dockerfile .`

This repo is for pumping malware through polyswarmd, for use with the `test.yml`, `tutorial[,1,2]` files of `polyswarm/orchestration` repo

# SECURITY WARNING

`ambassador` implicitly trusts transaction signing requests from `polyswarmd`.
A malicious instance of `polyswarmd` or an attacker with sufficient network capabilities may abuse this trust relationship to cause `ambassador` to transfer all NCT, ETH or other tokens to an attacker address.

Therefore: 
1. **ONLY CONNECT `ambassador` TO `polyswarmd` INSTANCES THAT YOU TRUST**
2. **DO NOT ALLOW `ambassador` <-> `polyswarmd` COMMUNICATIONS TO TRAVERSE AN UNTRUSTED NETWORK LINK**

In other words, only run `ambassador` on a co-located `localhost` with `polyswarmd`.

This is a temporarily limitation - `ambassador`'s trust in `polyswarmd` will be eliminated in the near future.
