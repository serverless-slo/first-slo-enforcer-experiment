/*


Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package controllers

import (
	"context"
	"flag"
	"log"
	"os"
	"path/filepath"
	"strconv"

	"github.com/go-logr/logr"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/tools/clientcmd"
	knativeclient "knative.dev/serving/pkg/client/clientset/versioned"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	sloibmcomv1alpha1 "github.com/ngduchai/faasslo/api/v1alpha1"
)

// SLODescReconciler reconciles a SLODesc object
type SLODescReconciler struct {
	client.Client
	Log    logr.Logger
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=slo.ibm.com,resources=slodescs,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=slo.ibm.com,resources=slodescs/status,verbs=get;update;patch

func (r *SLODescReconciler) Reconcile(req ctrl.Request) (ctrl.Result, error) {
	ctx := context.Background()
	_ = r.Log.WithValues("slodesc", req.NamespacedName)

	// your logic here
	rst := ctrl.Result{}
	slo := &sloibmcomv1alpha1.SLODesc{}
	err := r.Get(ctx, req.NamespacedName, slo)
	if err != nil {
		return rst, err
	}
	if len(slo.Status.Metrics) == 0 {
		log.Printf("New SLODesc created, waiting for performance inputs")
	} else {
		latestMetric := slo.Status.Metrics[len(slo.Status.Metrics)-1]
		inputrate := latestMetric.InputRate
		meanlat := latestMetric.MeanLatency
		taillat := latestMetric.TailLatency
		stddev := latestMetric.StddevLatency

		log.Printf("Input rate: %d Mean lat %d stddev %d Tail lat %d\n", inputrate, meanlat, stddev, taillat)

		expectedInputrate := slo.Spec.RateLimit
		// expected_taillat := slo.Spec.Tail.Latency

		if inputrate < expectedInputrate {
			opts := metav1.GetOptions{}
			// Load related functions

			// listops := metav1.ListOptions{}
			// serviceList, err := kc.ServingV1().Services("kcontainer").List(listops)
			// if err != nil {
			// 	log.Printf("Unable to load services %s", err)
			// } else {
			// 	log.Print("Found service list")
			// 	for _, service := range serviceList.Items {
			// 		log.Printf("Service: %s", service.Name)
			// 	}
			// }

			for _, serviceName := range slo.Spec.Workflow.Tasks {
				service, err := kc.ServingV1().Services("kcontainer").Get(serviceName, opts)
				if err != nil {
					log.Printf("Unable to get service %s: %s", serviceName, err)
				} else {
					reservation := 1
					if podmin, ok := service.Spec.Template.Annotations["autoscaling.knative.dev/minScale"]; ok {
						reservation, err = strconv.Atoi(podmin)
						if err != nil {
							log.Printf("Invalid minscale = %s (%s)", podmin, serviceName)
							reservation = 0
						}
					} else {
						reservation = 0
					}
					// if taillat > expected_taillat {
					// 	if reservation == 0 {
					// 		reservation = 1
					// 	} else {
					// 		reservation = reservation * 2
					// 	}
					// 	if reservation > 10 {
					// 		reservation = 10
					// 	}
					// } else {
					// 	if reservation > 0 {
					// 		reservation--
					// 	}
					// }
					// service.Spec.Template.Annotations["autoscaling.knative.dev/minScale"] = strconv.Itoa(reservation)
					// log.Printf("Tail lat = %d, Expected tail lat = %d, Set reservation for %s to %d", taillat, expected_taillat, serviceName, reservation)
					// _, err := kc.ServingV1().Services("kcontainer").Update(service)
					// if err != nil {
					// 	log.Printf("Unable to update service %s", err)
					// }
					if reservation != 1 {
						reservation = 1
						service.Spec.Template.Annotations["autoscaling.knative.dev/minScale"] = strconv.Itoa(reservation)
						service.Spec.Template.Annotations["autoscaling.knative.dev/target"] = "100"
						service.Spec.ConfigurationSpec.Template.Spec.Containers[0].Resources.Requests["cpu"] = resource.MustParse("500m")
						service.Spec.ConfigurationSpec.Template.Spec.Containers[0].Resources.Requests["memory"] = resource.MustParse("1500Mi")
						service.Spec.ConfigurationSpec.Template.Spec.Containers[0].Resources.Limits["cpu"] = resource.MustParse("500m")
						service.Spec.ConfigurationSpec.Template.Spec.Containers[0].Resources.Limits["memory"] = resource.MustParse("1500Mi")
						log.Printf("Update service %s configuration to 500m+1", serviceName)
						_, err := kc.ServingV1().Services("kcontainer").Update(service)
						if err != nil {
							log.Printf("Unable to update service %s", err)
						}
					}
				}
			}
		}

	}

	return ctrl.Result{}, nil
}

// func newRestClient(cfg *rest.Config) (*rest.RESTClient, error) {
// 	scheme := runtime.NewScheme()
// 	SchemeBuilder := runtime.NewSchemeBuilder(knativescheme.AddKnownTypes)
// 	if err := SchemeBuilder.AddToScheme(scheme); err != nil {
// 		return nil, err
// 	}
// 	config := *cfg
// 	config.GroupVersion = &SchemeGroupVersion
// 	config.APIPath = "/apis"
// 	config.ContentType = runtime.ContentTypeJSON
// 	config.NegotiatedSerializer = serializer.NewCodecFactory(scheme)
// 	client, err := rest.RESTClientFor(&config)
// 	if err != nil {
// 		return nil, err
// 	}
// 	return client, nil
// }

var kc *knativeclient.Clientset

func (r *SLODescReconciler) SetupWithManager(mgr ctrl.Manager) error {
	home := os.Getenv("HOME")
	log.Printf("Load config from %s", home)
	kubeconfig := flag.String("cmdconfig", filepath.Join(home, ".kube", "config"), "(optional) absolute path to the kubeconfig file")
	flag.Parse()
	config, err := clientcmd.BuildConfigFromFlags("", *kubeconfig)
	if err != nil {
		panic(err.Error())
	}

	kc, err = knativeclient.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	return ctrl.NewControllerManagedBy(mgr).
		For(&sloibmcomv1alpha1.SLODesc{}).
		Complete(r)
}
