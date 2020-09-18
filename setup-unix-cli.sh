curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.8.1/kind-$(uname)-amd64
chmod +x ./kind
mv ./kind /usr/local/bin/kind
curl -Lo ./stern https://github.com/wercker/stern/releases/download/1.11.0/stern_$(uname)_amd64
chmod +x ./stern
mv ./stern /usr/local/bin/stern
