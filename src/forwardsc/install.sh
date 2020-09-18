#!/bin/zsh
#if [ -z ${DOCKER_USERNAME+x} ]; then DOCKER_USERNAME=ngduchai; fi
kubectl delete -f app.yaml -n kcontainer
cat app.yaml | sed 's/\${DOCKER_USERNAME}'"/${DOCKER_USERNAME}/g" | kubectl -n kcontainer apply -f -
#kubectl apply -f app.yaml -n kcontainer
