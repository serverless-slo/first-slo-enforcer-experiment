package main

import (
	"context"
	"io"
	"io/ioutil"
	"log"
	"math"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	cloudevents "github.com/cloudevents/sdk-go/v2"
	"github.com/jasonlvhit/gocron"
	faasslo "github.com/ngduchai/faasslo/api/v1alpha1"
	appsv1 "k8s.io/api/apps/v1"
	apiextclientset "k8s.io/apiextensions-apiserver/pkg/client/clientset/clientset/typed/apiextensions/v1beta1"
	kubeinformers "k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/cache"
)

func parseOrder(event cloudevents.Event) (order *OrderEvent, err error) {
	if err := event.DataAs(&order); err != nil {
		log.Printf("Error while extracting cloudevent Data: %s\n", err.Error())
	}
	return
}

var pendingOrders sync.Map
var runningPods sync.Map
var desiredPods sync.Map
var inputTracking int64

const trackingLength = 10
const supportingPeriod = 5

var latencyTrackingLock sync.Mutex
var latencyTracking []int64

func reportOrders(ctx context.Context, event cloudevents.Event) (*cloudevents.Event, cloudevents.Result) {
	// Logging orders
	var result = cloudevents.NewHTTPResult(200, "OK") //cloudevents.Result = nil
	switch eventType := event.Type(); eventType {
	case "OrderEvent":
		if order, err := parseOrder(event); err != nil {
			result = cloudevents.NewHTTPResult(400, "failed to convert data: %s", err)
		} else {
			id := order.Payload.OrderID
			if order.Type == "Order" {
				log.Printf("Get event: %s", event)
				if oldOrder, ok := pendingOrders.Load(id); ok {
					// log.Printf("[ORDER] [%s] Id %s placed %d closed %d", order.Type, id, oldOrder.(*OrderEvent).Timestamp, order.Timestamp)
					msg := "[ORDER] [" + order.Type + "] Id " + id + " input "
					latency := (int64)(order.Timestamp - oldOrder.(*OrderEvent).Timestamp)
					if latency < 0 {
						latency = -latency
						msg += strconv.FormatInt(order.Timestamp, 10)
					} else {
						msg += strconv.FormatInt(oldOrder.(*OrderEvent).Timestamp, 10)
					}
					mids := order.Payload.MidTimestamp
					if len(mids) == 0 {
						mids = oldOrder.(*OrderEvent).Payload.MidTimestamp
					}
					for i, name := range monitorReplicaSets {
						msg += " " + name + " " + strconv.FormatInt(mids[i], 10)
					}
					log.Printf(msg)
					latencyTrackingLock.Lock()
					latencyTracking = append(latencyTracking, latency)
					latencyTrackingLock.Unlock()
					pendingOrders.Delete(id)
				} else {
					atomic.AddInt64(&inputTracking, 1)
					pendingOrders.Store(id, order)
				}
			}
		}
	default:
		log.Printf("Skip event type: %s\n", eventType)
	}

	return nil, result
}

func rawHandle(w http.ResponseWriter, req *http.Request) {
	log.Print("Header:\n")
	for k, v := range req.Header {
		log.Printf("Header field %q, Value %q\n", k, v)
	}
	body, err := ioutil.ReadAll(req.Body)
	if err != nil {
		log.Printf("Error reading body: %v", err)
		http.Error(w, "can't read body", http.StatusBadRequest)
		return
	}
	log.Printf("Get event body: %s", body)
}

var monitorReplicaSets = []string{"springcontainerms"}

func updateScaling(replicaset *appsv1.ReplicaSet) {
	for _, rsName := range monitorReplicaSets {
		if strings.Contains(replicaset.Name, rsName) {
			timestamp := time.Now().UnixNano() / 1000000
			desired := replicaset.Spec.Replicas
			current := replicaset.Status.Replicas
			ready := replicaset.Status.ReadyReplicas
			log.Printf("[SCALE] %s %d Ready %d Current %d Desired %d\n", replicaset.Name, timestamp, ready, current, *desired)
			runningPods.Store(rsName, int64(ready))
			desiredPods.Store(rsName, int64(*desired))
		}
	}
}

func updateSLOEnforcement() error {
	// cdf := exclientset.CustomResourceDefinitions()
	// opts := v1.GetOptions{}
	// slodef, err := cdf.Get(ctx, "slodesc.slo.ibm.com", opts)
	// if err != nil {
	// 	return err
	// }
	// slostatus := slodef.Status

	ctx := context.Background()
	slo, err := crdclient.SloDescs("kcontainer").Get("forward", ctx)
	if err != nil {
		log.Printf("error while getting the SLODesc %v\n", err)
		return err
	}
	//log.Printf("SLODesc Objects Found: \n%v\n", slo)
	latencyTrackingLock.Lock()
	latencies := latencyTracking
	latencyTracking = latencyTracking[:0]
	latencyTrackingLock.Unlock()
	sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
	meanlat := 0.0
	stddev := 0.0
	for _, lat := range latencies {
		meanlat += float64(lat)
		stddev += float64(lat * lat)
	}
	meanlat = meanlat / float64(len(latencies))
	stddev = math.Sqrt((stddev - meanlat*meanlat) / float64(len(latencies)))

	taillat := int64(-1)
	if len(latencies) > 0 {
		taillat = latencies[int(0.99*float64(len(latencies)))]
	}
	inputrate := float64(inputTracking) / float64(supportingPeriod)
	atomic.StoreInt64(&inputTracking, 0)
	running := map[string]int64{}
	desired := map[string]int64{}
	for _, task := range monitorReplicaSets {
		if r, ok := runningPods.Load(task); ok {
			running[task] = r.(int64)
		} else {
			running[task] = -1
		}
		if d, ok := desiredPods.Load(task); ok {
			desired[task] = d.(int64)
		} else {
			desired[task] = -1
		}
	}
	metrics := faasslo.WorkflowStatus{
		MeanLatency:   int64(meanlat),
		TailLatency:   int64(taillat),
		StddevLatency: int64(stddev),
		InputRate:     int64(inputrate),
		RunningPods:   running,
		DesiredPods:   desired,
	}
	if len(slo.Status.Metrics) < trackingLength {
		slo.Status.Metrics = append(slo.Status.Metrics, metrics)
	} else {
		slo.Status.Metrics = append(slo.Status.Metrics[1:], metrics)
	}
	_, err = crdclient.SloDescs("kcontainer").UpdateStatus("forward", slo, ctx)
	//_, err = crdclient.SloDescs("kcontainer").Update("forward", slo, ctx)
	if err != nil {
		log.Printf("error while updating the SLODesc: %v\n", err)
	} else {
		log.Printf("Update SLODesc status %v\n", slo.Status)
	}
	return nil
}

func executeCronJob() {
	gocron.Every(supportingPeriod).Second().Do(updateSLOEnforcement)
	<-gocron.Start()
}

var clientset *kubernetes.Clientset
var exclientset *apiextclientset.ApiextensionsV1beta1Client
var crdclient *FaaSSloV1Alpha1Client

func main() {

	logFile, err := os.OpenFile("log", os.O_CREATE|os.O_APPEND|os.O_RDWR, 0666)
	if err != nil {
		panic(err)
	}
	mw := io.MultiWriter(os.Stdout, logFile)
	log.SetOutput(mw)

	log.Print("Observer started.")

	log.Print("Collecting Kubenetes configurations")
	config, err := rest.InClusterConfig()
	if err != nil {
		panic(err.Error())
	}
	clientset, err = kubernetes.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	exclientset, err = apiextclientset.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	crdclient, err = NewFaaSSloClient(config)
	if err != nil {
		panic(err)
	}

	log.Print("Collect SLO descriptions")
	ctx := context.Background()
	for true {
		slo, err := crdclient.SloDescs("kcontainer").Get("forward", ctx)
		if err == nil {
			monitorReplicaSets = slo.Spec.Workflow.Tasks
			log.Print("Save observered tasks:")
			for _, task := range monitorReplicaSets {
				log.Print(task)
			}
			break
		}
		log.Printf("SLODesc not found: %s\n", err)
		time.Sleep(1000 * time.Millisecond)
	}

	options := kubeinformers.WithNamespace("kcontainer")

	kubeInformerFactory := kubeinformers.NewSharedInformerFactoryWithOptions(clientset, time.Second*1, options)
	kubeInformer := kubeInformerFactory.Apps().V1().ReplicaSets().Informer()
	informerChan := make(chan struct{})
	defer close(informerChan)

	kubeInformer.AddEventHandler(
		cache.ResourceEventHandlerFuncs{
			AddFunc: func(obj interface{}) {
				updateScaling(obj.(*appsv1.ReplicaSet))
			},
			UpdateFunc: func(old, new interface{}) {
				updateScaling(new.(*appsv1.ReplicaSet))
			},
			DeleteFunc: func(obj interface{}) {
				updateScaling(obj.(*appsv1.ReplicaSet))
			},
		})

	kubeInformerFactory.Start(informerChan)
	//kubeInformer.Run(informerChan)
	//kubeInformer.GetController().Run(informerChan)

	go executeCronJob()

	c, err := cloudevents.NewDefaultClient()
	if err != nil {
		log.Fatalf("failed to create client, %v", err)
	}

	// log.Fatal(c.StartReceiver(context.Background(), receive))

	log.Fatal(c.StartReceiver(context.Background(), reportOrders))

	// http.HandleFunc("/", rawHandle)
	// http.ListenAndServe(":8080", nil)

}
