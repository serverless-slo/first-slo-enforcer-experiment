#!/bin/zsh
#if [ -z ${DOCKER_USERNAME+x} ]; then DOCKER_USERNAME=ngduchai; fi
IMAGE=sloorder-observer
docker build -t ${DOCKER_USERNAME}/${IMAGE} .
docker push ${DOCKER_USERNAME}/${IMAGE}
