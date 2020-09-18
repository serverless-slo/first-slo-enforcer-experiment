from multiprocessing import Pool, TimeoutError
import time
import os
import requests
import sys

import itertools
import threading
import queue
import random

import uuid
import datetime
import json

import numpy as np
import matplotlib.pyplot as plt

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

#endpoint = "http://orders-kn-channel.kcontainer.svc.cluster.local"
endpoint = "http://forward-1.kcontainer.127.0.0.1.nip.io"
#endpoint = "http://127.0.0.1:8080"
#endpoint = "http://springcontainerms-service.kcontainer.127.0.0.1.nip.io/orderevents"

eventtype = "OrderCreated"

def memoryless_idle_time(rate):
    # TODO: Need implementation
    return 1/rate

def gaussian_ilde_time(rate):
    # TODO: Need implementation
    return 1/rate

class Counter:
    def __init__(self):
        self.number_of_read = 0
        self.counter = itertools.count()
        self.lock = threading.Lock()
    
    def inc(self):
        next(self.counter)
    
    def value(self):
        with self.lock:
            value = next(self.counter) - self.number_of_read
            self.number_of_read += 1
        return value

def createOrder():
    addresses = [ 
      {"street": "100 Main street", "city": "Oakland", "country": "USA", "state": "CA", "zipcode": "94501"},
      {"street": "150 Meilong Road", "city": "Shanghai", "country": "China", "state": "", "zipcode": "200237"},
      {"street": "476 9th Ave", "city": "NYC", "country": "USA", "state": "NY", "zipcode": "10018"},
      {"street": "27-28, Rail Arch, New Mill Rd, Nine Elms", "city": "London", "country": "United Kingdom", "state": "", "zipcode": "SW8 5PP"},
      {"street": "1628, 2095 Jerrold Ave", "city": "San Francisco", "country": "USA", "state": "CA", "zipcode": "94124"}
    ]
    manuf = ['GoodManuf','OtherManuf']
    products = ['Fresh product 1','Medical vaccin','Carrot','Fresh Product']
    currentDate = datetime.datetime.now()
    pickupDate = currentDate + datetime.timedelta(days=3)
    expectedDeliveryDate = currentDate + datetime.timedelta(days=23)
    # get a random index for pickup location
    pickupIndex = random.randint(0, len(addresses)-1)
    # get a random index for delivery location - and ensure not the same index of pickup
    deliveryIndex = random.randint(0, len(addresses)-1)
    while (pickupIndex == deliveryIndex):
        deliveryIndex = random.randint(0, len(addresses)-1)
    # get random indexes for the other arrays
    manufIndex = random.randint(0, len(manuf)-1)
    prodIndex = random.randint(0, len(products)-1)
    
    payload = {
      "orderID": str(uuid.uuid4()),
      "productID": products[prodIndex],
      "quantity": 1000,
      "customerID": manuf[manufIndex],
      "expectedDeliveryDate": expectedDeliveryDate.strftime("yyyy-MM-dd'T'HH:mm:ssXXX"),
      "pickupDate": pickupDate.strftime("yyyy-MM-dd'T'HH:mm:ssXXX"),
      "pickupAddress": addresses[pickupIndex],
      "destinationAddress": addresses[deliveryIndex],
      "status": "pending",
    }

    order = {
      "timestamp": int(time.time() * 1000),
      "version": 1,
      "payload": payload,
      "type": eventtype,
    }

    return order


def reqfunc():
    #print("Sending:", knative_cluster)
    #return requests.get(knative_cluster, headers={"Host": "greeter.knativetutorial.example.com"})
    eventId = uuid.uuid4()
    headers = {
        "X-B3-Flags": "1",
        "CE-SpecVersion": "1.0",
        "CE-Type": "OrderEvent",
        "CE-ID": str(eventId),
        "CE-Source": "dev.knative.ordereventsource",
        "Content-Type": "application/json"
    }
    order = json.dumps(createOrder())
    # print(order)
    return requests.post(endpoint, headers=headers, data=order)


sentRequests = Counter()
recvRequests = Counter()
succRequests = Counter()
pendingRequests = queue.Queue()

running = True

rates = []
latencies = []

def generate_requests(pool, srate, erate, step):
    global rates
    global latencies

    # warmup
    for i in range(10):
        r = pool.apply_async(func=reqfunc)
    time.sleep(20)

    for rate in range(srate, erate, step):
        success = 0
        responses = []
        start = time.time()
        for i in range(rate):
            r = pool.apply_async(func=reqfunc)
            responses.append(r)
        remain_res = []
        while True:
            for res in responses:
                if res.ready():
                    r = res.get()
                    if r.status_code == 200:
                        success += 1
                else:
                    remain_res.append(res)
            if len(remain_res) == 0:
                break
            responses = remain_res
            remain_res = []
        end = time.time()
        rates.append(rate)
        latencies.append(end-start)
        print("Send:", rate, "Successed:", success, "Time:", end-start)

    running = False

if __name__ == '__main__':
    parallelism = 1
    srate = 1.0
    erate = 10.0
    step = 1.0
    if len(sys.argv) != 5:
        eprint("Usage: python genconcurrency.py [parallelism] [srate] [erate] [step]")
        exit(1)
    else:
        parallelism = int(sys.argv[1])
        srate = int(sys.argv[2])
        erate = int(sys.argv[3])
        step = int(sys.argv[4])
    
    if "eventtype" in os.environ:
        eventtype = os.environ["eventtype"]

    pool = Pool(processes=parallelism)
    print("Generating new request, press [Ctrl + C] to stop")
    running = True
    
    sender = threading.Thread(target=generate_requests, args=(pool, srate, erate, step))
    sender.start()

    sender.join()


    # plt.plot(rates, latencies)
    # plt.xlabel("Concurrency (requests)")
    # plt.ylabel("Time (Second)")
    # plt.tight_layout()
    # plt.show()





