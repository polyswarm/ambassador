#! /bin/bash

./scripts/wait_for_it.sh $POLYSWARM_HOST:$POLYSWARM_PORT -t 60
sleep 5
python dummyAmbassador.py & python pythonSigner.py

