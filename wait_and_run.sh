#! /bin/bash

./scripts/wait_for_it.sh $POLYSWARM_HOST:$POLYSWARM_PORT -t 0
#sleep 5
python pythonSigner.py  & 
for i in `seq 1 10`
do
	python dummyAmbassador.py  
done
