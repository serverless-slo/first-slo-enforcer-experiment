# IMPORTANT: remember to set the right version to $VERSION before running the scripts

echo "Install Knative serving"
kubectl apply --filename https://github.com/knative/serving/releases/download/${VERSION}/serving-crds.yaml
kubectl apply --filename https://github.com/knative/serving/releases/download/${VERSION}/serving-core.yaml

echo "Setup the network using Kourier"
kubectl apply --filename yaml/kourier.yaml
kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress.class":"kourier.ingress.networking.knative.dev"}}'
kubectl patch configmap/config-domain \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"127.0.0.1.nip.io":""}}'

echo "Install Knative eventing"
kubectl apply --filename https://github.com/knative/eventing/releases/download/${VERSION}/eventing-crds.yaml
kubectl apply --filename https://github.com/knative/eventing/releases/download/${VERSION}/eventing-core.yaml
kubectl apply --filename https://github.com/knative/eventing/releases/download/${VERSION}/mt-channel-broker.yaml

# Install Prometheus and Grafana then showing performance metrics on browser
kubectl create namespace istio-system
kubectl apply --filename https://github.com/knative/serving/releases/download/${VERSION}/monitoring-core.yaml

# Install Prometheus and Grafana
kubectl apply --filename https://github.com/knative/serving/releases/download/${VERSION}/monitoring-metrics-prometheus.yaml


