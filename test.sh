
kubectl create namespace kcontainer

echo "Testing Knative serving..."
kubectl apply -f yaml/hello.yaml
kubectl wait --for=condition=Ready pod --all -n kcontainer
curl http://helloworld.kcontainer.127.0.0.1.nip.io

if [ $? -eq 0 ]; then
    echo "KNATIVE WORKS AS EXPECTED"
else
    echo "KNATIVE IS NOT INSTALLED CORRECTLY"
fi

# Deploy the in/out
kubectl apply -f yaml/slodesc.yaml
kubectl apply -f yaml/observer.yaml
kubectl apply -f yaml/channels.yaml
kubectl create rolebinding default-resource-view \
  --role=resource-reader \
  --serviceaccount=kcontainer:default \
  --namespace=kcontainer

# Deploy workload genetator
kubectl -n kcontainer run cli --requests=cpu=1000m,memory=2Gi --env="eventtype=Order" --generator=run-pod/v1 --image=serverlessslo/ordercli -- block

# Wait until the cluster is ready
echo "Waiting for all pods to ready..."
kubectl wait --for=condition=Ready pod --all -n kcontainer

# Create a single order and push it into the order channel
kubectl exec -n kcontainer cli -- orders create 1

# Check if we receive it in observer
echo "Read observer log, there should be lines indicating order arrival. Press Ctrl + C to continue"
stern sloorder-observer -n kcontainer



