echo "Setting up observer"
kubectl delete -f yaml/observer.yaml
kubectl apply -f yaml/observer.yaml
echo "Waiting for pods to ready..."
sleep 10
kubectl wait --for=condition=Ready pod --all -n kcontainer --timeout=20s

path=results/${1}
if [ ! -f ${path} ]; then mkdir -p ${path}; fi
echo "Results will be stored in ${path}"
echo "Generating new orders..."
kubectl exec -n kcontainer cli > ${path}/clilog -- python3 genburst.py 200 0 120 4 40 40 3 uniform
echo "Waiting for all orders processed..."
sleep 120
echo "Collecting and ploting results from ${observername}"
observername=`kubectl get pods -n kcontainer | grep order-observer | cut -d " " -f1`
kubectl exec -n kcontainer ${observername} -- cat log | grep ORDER > ${path}/observerlog
kubectl exec -n kcontainer ${observername} -- cat log | grep SCALE > ${path}/scalelog
python3 plot_live_metrics.py ${path} forward-1,forward-2,forward-3 ${2}



