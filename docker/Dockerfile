FROM python:3.5-jessie
LABEL maintainer="PolySwarm Developers <info@polyswarm.io>"

RUN apt-get update && apt-get install -y \
        curl \
        jq && \
    rm -rf /var/lib/apt/lists/*

ADD /bounties /bounties 
add /requirements.txt /requirements.txt
run pip install -r requirements.txt
add . .
CMD ["python3", "ambassador.py"]
