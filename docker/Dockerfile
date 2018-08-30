FROM python:3.5-jessie
LABEL maintainer="PolySwarm Developers <info@polyswarm.io>"

RUN apt-get update && apt-get install -y \
        curl \
        jq && \
    rm -rf /var/lib/apt/lists/*

    # Install dockerize
ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

ADD /bounties /bounties
add /requirements.txt /requirements.txt
run pip install -r requirements.txt
add . .
CMD ["python3", "ambassador.py"]
