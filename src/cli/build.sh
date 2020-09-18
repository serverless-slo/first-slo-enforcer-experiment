#!/bin/zsh
#if [ -z ${DOCKER_USERNAME+x} ]; then DOCKER_USERNAME=ngduchai; fi
docker build -t ${DOCKER_USERNAME}/ordercli .
docker push ${DOCKER_USERNAME}/ordercli
