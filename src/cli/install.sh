#!/bin/zsh
#if [ -z ${DOCKER_USERNAME+x} ]; then DOCKER_USERNAME=ngduchai; fi
kubectl delete pod cli -n kcontainer
kubectl -n kcontainer run cli --requests=cpu=2000m,memory=2Gi --env="eventtype=OrderCreated" --generator=run-pod/v1 --image=${DOCKER_USERNAME}/ordercli -- block
