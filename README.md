The First SLO Enforcer Experiment
by Hai Duc Nguyen, Aleksander Slominski, and Lionel Villard

For more information, please see our online blog post at [TODO: Add link here]

```
export VERSION=v0.15.1
export DOCKER_USERNAME=your_username
./setup-kind.sh
./setup-knative.sh
./setup-kafka.sh
./setup-slo-enforcer.sh
./test.sh
./test-cleanup.sh
```


```
./setup-exp-without-slo.sh
./generate-workload-without-slo.sh
```


```
./monitor.sh
```

```
python3 plot_live_metrics.py results/without-slo forward-1,forward-2,forward-3 100,100,100
```


```
./setup-exp-with-slo.sh
./generate-workload-with-slo.sh
```


```
./monitor.sh
```

```
python3 plot_live_metrics.py results/without-slo forward-1,forward-2,forward-3 100,100,100
```


generate-workload-without-slo.sh
vs
generate-workload-without-slo.sh 

???

burst.sh ???


Cleanup - delete KinD cluster.

```
./cleanup.sh
```