#! /bin/bash

./scripts/wait_for_it.sh $POLYSWARMD_HOST:$POLYSWARMD_PORT -t 0
for i in `seq 1 10`
do
	python ambassador.py
done
