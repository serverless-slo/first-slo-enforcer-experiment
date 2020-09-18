import os
import numpy as np
import matplotlib.pyplot as plt
import math
import subprocess

import sys

path = sys.argv[1]
services = sys.argv[2].split(",")
pservices = {}
pservices[services[0]] = ""
for i in range(1, len(services)):
    pservices[services[i]] = services[i-1]

concurrency_mapper = {}
concurrency_mapper[100] = 10
concurrency_mapper[200] = 20
concurrency_mapper[300] = 30
concurrency_mapper[400] = 50
concurrency_mapper[500] = 100
concurrency_mapper[1000] = 100

concurrency_factor = []
podconfig = sys.argv[3]
pod_sizes = podconfig.split(",")
for i in range(len(pod_sizes)):
    pod_sizes[i] = int(pod_sizes[i])
    concurrency_factor.append(concurrency_mapper[pod_sizes[i]])

resolution = 5000
taillat = 1500
gap = 10
agap = int(gap / (resolution / 1000))
rate_limit = 120

#observername = subprocess.Popen("kubectl get pods -n kcontainer | grep order-observer | cut -d \" \" -f1", shell=True, stdout=subprocess.PIPE).stdout.read().decode()[:-1]

#print(observername)

# Collect from the traces
#cmd = "kubectl logs -l app=order-observer -n kcontainer --tail=-1 | grep ORDER > observerlog"
#cmd = "kubectl exec -n kcontainer " + observername + " -- cat log | grep ORDER > " + path + "/observerlog"
#os.system(cmd)
with open(path + "/observerlog", "r") as f:
    lines = f.readlines()
    starttimes = []
    endtimes = {}
    for s in services:
        endtimes[s] = []
    for line in lines:
        tokens = line.split(" ")
        starttimes.append(int(tokens[7]))
        i = 8
        while i < len(tokens):
            endtimes[tokens[i]].append(int(tokens[i+1]))
            i += 2
    starttimes = np.array(starttimes)
    for s in services:
        endtimes[s] = np.array(endtimes[s])
    btime = 100000000000000
    for t in starttimes:
        if t < btime and t > 0:
            btime = t
    btime = min(np.min(endtimes[services[-1]]), btime)
    etime = max(np.max(starttimes), np.max(endtimes[services[-1]]))
    starttimes = starttimes - btime
    for s in services:
        endtimes[s] = endtimes[s] - btime
    size = int(math.ceil((etime - btime) / resolution)) + agap
    input_rate = np.zeros(size + agap)
    order_rate = {}
    latencies = {}
    concurrencies = {}
    slatencies = {}
    landist = {}
    landist_count = {}
    for s in services:
        latencies[s] = endtimes[s] - starttimes
        print(s, pservices[s])
        if pservices[s] == "":
            slatencies[s] = endtimes[s] - starttimes
        else:
            slatencies[s] = endtimes[s] - endtimes[pservices[s]]
        landist[s] = []
        for i in range(size + 10):
            landist[s].append([])
        #landist_count[s] = np.zeros(size + 10)
        order_rate[s] = np.zeros(size + 10)
        concurrencies[s] = np.zeros(size * int(resolution/1000) + 10)

        for i in range(len(endtimes[s])):
            if starttimes[i] > 0:
                input_rate[int(starttimes[i] / resolution) + agap] += 1
                landist[s][int(starttimes[i] / resolution) + agap].append(latencies[s][i])
                #landist_count[s][int(starttimes[i] / resolution) + agap] += 1
                for j in range(int(starttimes[i] / 1000), int(endtimes[s][i] / 1000), 1):
                    concurrencies[s][j + 10] += 1
            order_rate[s][int(endtimes[s][i] / resolution) + agap] += 1
        if pservices[s] != "":
            concurrencies[s] = np.array(concurrencies[s]) - np.array(concurrencies[pservices[s]])
        order_rate[s] /= (resolution / 1000)
        for i in range(len(landist[s])):
            if len(landist[s][i]) > 0:
                landist[s][i] = np.percentile(np.array(landist[s][i]), 95)
            else:
                landist[s][i] = 0
            """
            if landist_count[s][i] > 0:
                landist[s][i] /= landist_count[s][i]
            else:
                landist[s][i] = landist[s][i-1]
            """
    input_rate /= (len(services) * (resolution / 1000))

with open(path + "/clilog", "r") as f:
    lines = f.readlines()
    times = []
    cli_rate = []
    for i in range(gap):
        cli_rate.append(0)
    for line in lines:
        tokens = line.split(" ")
        if "Generating" in line:
            continue
        times.append(int(tokens[0]))
        cli_rate.append(int(tokens[2]))
    for i in range(len(cli_rate)-1):
        cli_rate[i] = cli_rate[i+1] - cli_rate[i]
    cli_rate.pop(len(cli_rate)-1)
    for i in range(0):
        cli_rate.insert(0, 0)
    while len(cli_rate) < len(order_rate):
        cli_rate.append(0)


print("Number of order received:", len(endtimes[services[-1]]), "Duration:", size, "seconds")

colors = ['orange', 'blue', 'green']

for i in range(len(services)):
    s = services[i]
    plt.plot(np.arange(0, len(order_rate[s]))*resolution/1000, order_rate[s], label="Output rate (" + s + ")", color=colors[i])
plt.plot(np.arange(0, len(input_rate))*resolution/1000, input_rate, label="Input rate")
plt.plot(cli_rate, label="Generation Rate")
plt.axhline(y=rate_limit, color="black", linestyle="--")
plt.xlabel("Time (second)")
#plt.xlim(0, 400)
plt.ylabel("Throughput (order/sec)")
#plt.ylim(0, 500)
plt.legend(loc="best")
plt.title("Throughput")

plt.tight_layout()
plt.savefig(path + "/throughput.png")

plt.figure()
for i in range(len(services)):
    s = services[i]
    plt.plot(np.arange(0, len(landist[s]))*resolution/1000, landist[s], label=s, color=colors[i])
plt.xlabel("Time (second)")
plt.ylabel("95th Latency (ms)")
plt.axhline(y = taillat, linestyle="--", color="black")
plt.legend(loc="best")
plt.title("Tail accumulated Latency per supporting period")

plt.tight_layout()
plt.savefig(path + "/latency.png")

plt.figure()
for i in range(len(services)):
    s = services[i]
    plt.hist(latencies[s], bins=1000, density=True, cumulative=True, label=s, histtype='step', alpha=0.8, color=colors[i])
plt.axvline(x = taillat, linestyle="--", color="black")
plt.xlabel("Time (ms)")
plt.xscale("symlog")
plt.xlim(100, 200000)
plt.ylabel("Probability")
plt.legend(loc="best")
plt.title("per-function Latency CDF")

plt.tight_layout()
plt.savefig(path + "/latdist.png")

plt.figure()
for i in range(len(services)):
    s = services[i]
    plt.hist(slatencies[s], bins=1000, density=True, cumulative=True, label=s, histtype='step', alpha=0.8, color=colors[i])
plt.axvline(x = taillat, linestyle="--", color="black")
plt.xlabel("Time (ms)")
plt.ylabel("Probability")
plt.legend(loc="best")
plt.title("Per-function Accumulated latency distribution")

plt.tight_layout()
plt.savefig(path + "/latdist-single.png")

#cmd = "kubectl logs -l app=order-observer -n kcontainer --tail=-1 | grep SCALE > scalelog"
#cmd = "kubectl exec -n kcontainer " + observername + " -- cat log | grep SCALE > " + path + "/scalelog"
#os.system(cmd)
scale_times = {}
total_pods = {}
readies_pods = {}
allpods_avg = {}
for s in services:
    scale_times[s] = []

with open(path + "/scalelog", "r") as f: 
    lines = f.readlines()
    totals = {}
    readies = {}
    allpods = {}
    for s in services:
        totals[s] = []
        readies[s] = []
        allpods[s] = []
    for line in lines:
        tokens = line.split(" ")
        timestamp = int(tokens[4])
        if timestamp < btime or timestamp > etime:
            continue
        dname = tokens[3]
        for s in services:
            if s in dname:
                scale_times[s].append(timestamp)
                readies[s].append(int(tokens[6]))
                #totals.append(int(tokens[8]))
                total = int(tokens[8])
                # if total == 0:
                #     print(timestamp - btime, "get", total, "pods")
                totals[s].append(total)
                allpods[s].append(int(tokens[10]))
                break
    for s in services:
        scaleresol = 1000
        size = int(math.ceil((etime - btime) / scaleresol)) + gap
        scale_times[s] = np.array(scale_times[s]) - btime
        total_pods[s] = np.zeros(size + gap)
        readies_pods[s] = np.zeros(size + gap)
        allpods_avg[s] = np.zeros(size + gap)
        totalcount = np.zeros(size + gap)
        readiescount = np.zeros(size + gap)
        allpodscount = np.zeros(size + gap)
        for i in range(len(scale_times[s])):
            total_pods[s][int(scale_times[s][i] / scaleresol) + gap] += totals[s][i]
            readies_pods[s][int(scale_times[s][i] / scaleresol) + gap] += readies[s][i]
            allpods_avg[s][int(scale_times[s][i] / scaleresol) + gap] += allpods[s][i]
            totalcount[int(scale_times[s][i] / scaleresol) + gap] += 1
            readiescount[int(scale_times[s][i] / scaleresol) + gap] += 1
            allpodscount[int(scale_times[s][i] / scaleresol) + gap] += 1
        # for i in range(len(total_pods[s])):
        #     print(total_pods[s][i], totalcount[i])
        for i in range(1, len(total_pods[s])):
            if totalcount[i] > 0:
                total_pods[s][i] /= totalcount[i]
            else:
                total_pods[s][i] = total_pods[s][i-1]
            if readiescount[i] > 0:
                readies_pods[s][i] /= readiescount[i]
            else:
                readies_pods[s][i] = readies_pods[s][i-1]
            if allpodscount[i] > 0:
                allpods_avg[s][i] /= allpodscount[i]
            else:
                allpods_avg[s][i] = allpods_avg[s][i-1]

plt.figure()
for i in range(len(services)):
    s = services[i]
    plt.plot(total_pods[s], label= s + " - Current", color=colors[i])
    plt.plot(readies_pods[s], label= s + " - Ready", color=colors[i], linestyle=":")
    # plt.plot(allpods_avg, label="Desired")
plt.xlabel("Time (second)")
plt.ylabel("# Pods")
plt.legend(loc="best")
plt.title("Autoscaling")

plt.tight_layout()
plt.savefig(path + "/scaling.png")


plt.figure()
colors = ['orange', 'blue', 'green']
for i in range(len(services)):
    s = services[i]
    plt.plot(total_pods[s] * concurrency_factor[i], label= s + " - Current", color=colors[i])
    plt.plot(readies_pods[s] * concurrency_factor[i], label= s + " - Ready", color=colors[i], linestyle=":")
    plt.plot(concurrencies[s], label= s + " - Demand", color=colors[i], linestyle="--")
    # plt.plot(allpods_avg, label="Desired")
plt.xlabel("Time (second)")
plt.ylabel("Concurrency")
plt.yscale("symlog")
plt.legend(loc="best")
plt.title("Concurrency")

plt.tight_layout()
plt.savefig(path + "/concurrencies.png")

plt.show()






