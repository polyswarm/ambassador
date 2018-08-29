#! /bin/bash

./scripts/wait_for_it.sh $POLYSWARMD_HOST -t 0
./scripts/wait_for_it.sh $API_KEY_HOST -t 0

export API_KEY=$(./scripts/get_api_key.sh)

echo "ambassador API key: ${API_KEY}"

for i in `seq 1 10`
do
	python ambassador.py
done
