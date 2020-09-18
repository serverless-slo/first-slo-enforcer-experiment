package main

import (
	"context"
	"io"
	"log"
	"os"
	"runtime"
	"time"

	cloudevents "github.com/cloudevents/sdk-go/v2"
	"github.com/google/uuid"
)

func parseOrder(event cloudevents.Event) (order *OrderEvent, err error) {
	if err := event.DataAs(&order); err != nil {
		log.Printf("Error while extracting cloudevent Data: %s\n", err.Error())
	}
	return
}

func parseContainer(event cloudevents.Event) (container *ContainerAssignedToOrder, err error) {
	if err := event.DataAs(&container); err != nil {
		log.Printf("Error while extracting cloudevent Data: %s\n", err.Error())
	}
	return
}

var sleepduration = 100

func receive(ctx context.Context, event cloudevents.Event) (*cloudevents.Event, cloudevents.Result) {
	// Here is where your code to process the event will go.
	// In this example we will log the event msg
	//log.Printf("Event received. \n%s\n", event)
	time.Sleep(time.Duration(sleepduration) * time.Millisecond)
	var result = cloudevents.NewHTTPResult(200, "OK") //cloudevents.Result = nil
	switch eventType := event.Type(); eventType {
	case "OrderEvent":
		if order, err := parseOrder(event); err != nil {
			result = cloudevents.NewHTTPResult(400, "failed to convert data: %s", err)
		} else {
			t := time.Now()
			if order.Payload.Timestamp == 0 {
				order.Payload.Timestamp = order.Timestamp
			}
			order.Payload.MidTimestamp = append(order.Payload.MidTimestamp, t.UnixNano()/1000000)
			newEvent := cloudevents.NewEvent()
			newEvent.SetID(uuid.New().String())
			newEvent.SetSource("dev.knative.containerproducerimpl")
			newEvent.SetType("OrderEvent")
			newEvent.SetTime(t)
			msg := OrderEvent{
				Timestamp: t.UnixNano() / 1000000,
				Type:      order.Type,
				Payload:   order.Payload,
			}
			if err := newEvent.SetData(cloudevents.ApplicationJSON, msg); err != nil {
				return nil, cloudevents.NewHTTPResult(500, "failed to set response data: %s", err)
			}
			//log.Printf("Received order %s and response with %s", event, newEvent)
			log.Printf("Received order ID = %s", order.Payload.OrderID)
			// sum := 0
			// for i := 1; i < 10000000; i++ {
			// 	sum += i
			// }

			log.Printf("Forwarded %s", order.Payload.OrderID)
			c.Send(ctx, newEvent)
			// log.Printf("Forwarded %s", newEvent)
		}
	default:
		log.Printf("Skip event type: %s\n", eventType)
		// log.Printf("Finish skipping event %d", t.UnixNano())
	}

	return nil, result

}

var c cloudevents.Client

func main() {

	logFile, err := os.OpenFile("log", os.O_CREATE|os.O_APPEND|os.O_RDWR, 0666)
	if err != nil {
		panic(err)
	}
	mw := io.MultiWriter(os.Stdout, logFile)
	log.SetOutput(mw)

	log.Printf("Forward Spring Container")
	log.Printf("Initalizing sender\n")

	log.Printf("Sleep duration: %d", sleepduration)

	numcpu := runtime.NumCPU()
	mcpus := 1000
	runtime.GOMAXPROCS(mcpus)
	log.Printf("Number of available CPU: %d Expected Paralleism: %d\n", numcpu, mcpus)
	//runtime.GOMAXPROCS(2)

	mcpus = runtime.GOMAXPROCS(0)
	log.Printf("Current parallelism: %d\n", mcpus)

	addr := os.Getenv("ORDER_ENDPOINT")
	log.Printf("Order endpoint: %s", addr)
	ctx := cloudevents.ContextWithTarget(context.Background(), addr)
	//ctx := cloudevents.ContextWithTarget(context.Background(), "http://order-observer.kcontainer.svc.cluster.local")

	p, err := cloudevents.NewHTTP()
	if err != nil {
		log.Fatalf("failed to create protocol: %s", err.Error())
	}

	c, err = cloudevents.NewClient(p, cloudevents.WithTimeNow(), cloudevents.WithUUIDs())
	if err != nil {
		log.Fatalf("failed to create sender, %v", err)
	}

	log.Printf("Starting receiver\n")
	log.Fatal(c.StartReceiver(ctx, receive))

}
