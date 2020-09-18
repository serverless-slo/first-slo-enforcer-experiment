#!/bin/zsh
#if [ -z ${DOCKER_USERNAME+x} ]; then DOCKER_USERNAME=ngduchai; fi
kubectl delete -f app.yaml -n kcontainer
cat app.yaml | sed 's/\${DOCKER_USERNAME}'"/${DOCKER_USERNAME}/g" | kubectl -n kcontainer apply -f -
#kubectl apply -f app.yaml -n kcontainer
# Allow observer to get pod status
kubectl delete rolebinding default-resource-view -n kcontainer
kubectl create rolebinding default-resource-view \
  --role=resource-reader \
  --serviceaccount=kcontainer:default \
  --namespace=kcontainer
