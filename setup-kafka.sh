# IMPORTANT: remember to set the right version to $VERSION before running the scripts
kubectl create namespace kafka

echo "Applying Strimzi installation file"
kubectl apply -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka

echo "Waiting for Strimzi operator be ready..."
sleep 10

echo "Provision the Apache Kafka cluster"
kubectl apply -f https://strimzi.io/examples/latest/kafka/kafka-persistent-single.yaml -n kafka 

echo "Deploy Kafka channel"
curl -L "https://github.com/knative/eventing-contrib/\
releases/download/${VERSION}/kafka-channel.yaml" \
 | sed 's/REPLACE_WITH_CLUSTER_URL/my-cluster-kafka-bootstrap.kafka:9092/' \
 | kubectl apply --filename -
kubectl apply -f yaml/kafka-channel.yaml


