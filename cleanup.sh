#!/bin/zsh

# echo "--> Delete KContainer and related pods ----------------------------"
# kubectl delete -f kcontainer/spring-container-ms/k8s/base/faas
# kubectl delete pod cli -n kcontainer
# kubectl delete -f app.yaml -n kcontainer

# echo "--> Uninstall PostGRE SQL --------------------------"
# kubectl delete -f postgresql -n kcontainer

# VERSION=0.15.1
# echo "--> Cleanup environment -----------------------"
# #kubectl delete -f https://operatorhub.io/install/composable-operator.yaml
# #kubectl delete -f https://operatorhub.io/install/knative-eventing-operator.yaml
# #kubectl delete -f https://operatorhub.io/install/strimzi-kafka-operator.yaml

# kubectl delete -f https://operatorhub.io/install/ibmcloud-operator.yaml
# kubectl delete -f https://operatorhub.io/install/event-streams-topic.yaml
# kubectl delete -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/${VERSION}/crds.yaml
# kubectl delete -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/${VERSION}/olm.yaml

# # Delete the namespace
# kubectl delete namespace kcontainer

kind delete cluster --name knative

