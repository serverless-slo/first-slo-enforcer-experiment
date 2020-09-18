NUM_PARTITIONS=200
kubectl create namespace kcontainer

echo "Cleanup the old setup"
kubectl delete pod cli -n kcontainer
kubectl delete -n kcontainer -f yaml/observer.yaml
kubectl delete rolebinding default-resource-view -n kcontainer
kubectl delete -n kcontainer -f yaml/channels.yaml
kubectl delete -f yaml/forwards.yaml
kubectl delete -f yaml/subscriptions.yaml

echo "Create channels"
kubectl apply -n kcontainer -f yaml/channels.yaml

echo "Setup observer and in/out components"
kubectl apply -n kcontainer -f yaml/slodesc.yaml
kubectl apply -n kcontainer -f yaml/observer.yaml
kubectl create rolebinding default-resource-view \
  --role=resource-reader \
  --serviceaccount=kcontainer:default \
  --namespace=kcontainer
kubectl -n kcontainer run cli --requests=cpu=1000m,memory=2Gi --env="eventtype=Order" --generator=run-pod/v1 --image=serverlessslo/ordercli -- block

echo "Create Knative functions"
kubectl apply -f yaml/forwards.yaml

echo "Functions subscribe to channels"
kubectl apply -f yaml/subscriptions.yaml

echo "Set number of partitions to a large enough number to prevent kafka channels from being performance bottlenecks if necessary"
kubectl exec -n kafka -it my-cluster-kafka-0 -- bin/kafka-topics.sh --alter --zookeeper localhost:2181 --topic knative-messaging-kafka.kcontainer.orders --partitions ${NUM_PARTITIONS}
kubectl exec -n kafka -it my-cluster-kafka-0 -- bin/kafka-topics.sh --alter --zookeeper localhost:2181 --topic knative-messaging-kafka.kcontainer.forward-1 --partitions ${NUM_PARTITIONS}
kubectl exec -n kafka -it my-cluster-kafka-0 -- bin/kafka-topics.sh --alter --zookeeper localhost:2181 --topic knative-messaging-kafka.kcontainer.forward-2 --partitions ${NUM_PARTITIONS}
kubectl exec -n kafka -it my-cluster-kafka-0 -- bin/kafka-topics.sh --alter --zookeeper localhost:2181 --topic knative-messaging-kafka.kcontainer.forward-3 --partitions ${NUM_PARTITIONS}

# Refresh number of paritions
kubectl delete -f yaml/subscriptions.yaml
kubectl apply -f yaml/subscriptions.yaml

