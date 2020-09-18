module github.com/ngduchai/faasslo

go 1.13

require (
	github.com/go-logr/logr v0.1.0
	github.com/onsi/ginkgo v1.12.1
	github.com/onsi/gomega v1.10.1
	k8s.io/apimachinery v0.18.7-rc.0
	k8s.io/client-go v11.0.1-0.20190805182717-6502b5e7b1b5+incompatible
	knative.dev/serving v0.17.1
	sigs.k8s.io/controller-runtime v0.6.1
)

replace (
	github.com/go-logr/logr => github.com/go-logr/logr v0.1.0
	github.com/onsi/ginkgo => github.com/onsi/ginkgo v1.12.1
	github.com/onsi/gomega => github.com/onsi/gomega v1.10.1
	k8s.io/apiextensions-apiserver => k8s.io/apiextensions-apiserver v0.17.6
	k8s.io/apimachinery => k8s.io/apimachinery v0.17.6
	k8s.io/apimachinery/pkg/runtime => k8s.io/apimachinery/pkg/runtime v0.17.6
	k8s.io/client-go => k8s.io/client-go v0.17.6
	k8s.io/client-go/tools/metrics => k8s.io/client-go/tools/metrics v0.17.6
	knative.dev/serving => knative.dev/serving v0.17.1
	sigs.k8s.io/controller-runtime => sigs.k8s.io/controller-runtime v0.5.2
)
