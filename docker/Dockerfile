FROM golang:latest
LABEL maintainer="PolySwarm Developers <info@polyswarm.io>"

ENV GOPATH /go
ENV PATH $GOPATH/bin:$PATH

RUN mkdir -p $GOPATH/src/ambassador-microengine/
ADD . $GOPATH/src/ambassador-microengine/

#RUN set -x && \
#    cd $GOPATH/src/ambassador-microengine && \
#    go get . && \
#    go install
ADD ambassador-microengine $GOPATH/bin/ambassador-microengine

RUN useradd -ms /bin/bash microengine
WORKDIR /home/microengine
USER microengine

ENTRYPOINT $GOPATH/bin/ambassador-microengine
