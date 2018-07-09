#! /bin/bash

./scripts/wait_for_it.sh $POLYSWARMD_HOST:$POLYSWARMD_PORT -t 0
#sleep 5
#echo "starting signer..."
#python3 pythonSigner.py& # >/dev/null & 
for i in `seq 1 10`
do
	python newAmbassador.py | grep value
done
