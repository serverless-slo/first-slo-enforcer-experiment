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

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

endpoint = "http://orders-kn-channel.kcontainer.svc.cluster.local"
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

def generate_requests(pool, idle_time, rate, duration, final=True):
    global sentRequests
    global pendingRequests
    global running
    
    n = int(rate * duration)
    for i in range(n):
        res = pool.apply_async(func=reqfunc)
        pendingRequests.put(res)
        sentRequests.inc()
        time.sleep(idle_time(rate))
        if running != True:
            break
    if final:
        running = False

def generate_ramp(pool, idle_time, rampup, srate, erate, stepsize, final):
    global sentRequests
    global pendingRequests
    global running

    rate = srate
    while (srate < erate and rate < erate) or (srate > erate and rate > erate):
        n = int(rate * stepsize)
        for i in range(n):
            res = pool.apply_async(func=reqfunc)
            pendingRequests.put(res)
            sentRequests.inc()
            time.sleep(idle_time(rate))
        if running != True:
            break
        rate += stepsize
    if final:
        running = True
        

def tracking():
    global sentRequests
    global recvRequests
    global succRequests
    global pendingRequests
    global running

    while running:
        num = pendingRequests.qsize()
        waiting = []
        for _ in range(num):
            try:
                res = pendingRequests.get_nowait()
                if res.ready():
                    response = res.get()
                    recvRequests.inc()
                    if response.status_code == 200:
                        succRequests.inc()
                else:
                    waiting.append(res)
            except queue.Empty:
                break
            except:
                eprint("Error occur when trying to read the response...")
        for res in waiting:
            pendingRequests.put(res)
        print(int(round(time.time() * 1000)), "Sent:", sentRequests.value(), "Received:", recvRequests.value(), "Successed:", succRequests.value())
        time.sleep(1)
    
    


if __name__ == '__main__':
    parallelism = 1
    rate = 1.0
    dist = "uniform"
    duration = 10
    if len(sys.argv) != 5:
        eprint("Usage: python reqgen.py [parallelism] [rate] [duration] [uniform|memoryless|gaussian]")
        exit(1)
    else:
        parallelism = int(sys.argv[1])
        rate = float(sys.argv[2])
        duration = int(sys.argv[3])
        dist = sys.argv[4]
    
    # Select arrival distribution
    
    if dist == "uniform":
        idle_time = lambda r: 1/r
    elif dist == "memoryless":
        idle_time = memoryless_idle_time
    elif dist == "gaussian":
        idle_time = gaussian_ilde_time
    else:
        print("Invalid arrival distribution:", dist)
        exit(1)
    
    if "eventtype" in os.environ:
        eventtype = os.environ["eventtype"]

    pool = Pool(processes=parallelism)
    print("Generating new request, press [Ctrl + C] to stop")
    running = True
    
    sender = threading.Thread(target=generate_requests, args=(pool, idle_time, rate, duration))
    sender.start()

    tracker = threading.Thread(target=tracking)
    tracker.start()

    sender.join()
    tracker.join()
    
    




