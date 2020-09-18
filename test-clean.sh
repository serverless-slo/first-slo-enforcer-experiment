kubectl delete -f yaml/hello.yaml
kubectl delete pod cli -n kcontainer
kubectl delete -f yaml/slodesc.yaml
kubectl delete -f yaml/observer.yaml
kubectl delete -f yaml/channels.yaml
kubectl delete rolebinding default-resource-view -n kcontainer
exit 0
