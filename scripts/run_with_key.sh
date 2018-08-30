#!/bin/bash

# Add a new user
USER_ID=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"email\": \"${EMAIL}\"}" http://${API_KEY_HOST}/users | jq .id)

# Add a new eth address
curl -s -X POST -H "Content-Type: application/json" -d "{\"address\": \"${ADDRESS}\"}" http://${API_KEY_HOST}/users/${USER_ID}/addresses > /dev/null

# Add a new API key
export API_KEY=$(curl -s -X POST http://${API_KEY_HOST}/users/${USER_ID}/addresses/${ADDRESS}/apikeys | jq -r .key)

# Echo the API key to use
echo "ambassador API key: ${API_KEY}"

for i in `seq 1 10`
do
	python ambassador.py
done

