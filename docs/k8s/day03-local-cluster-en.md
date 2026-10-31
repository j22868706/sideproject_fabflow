# Day 3: Creating and Understanding a Local Kubernetes Cluster

Day 3 taught you how to create a local Kubernetes environment, choose the correct
cluster, run a Pod, inspect it, execute a command inside it, and delete it.

Status: core acceptance completed, based on terminal output supplied during the
lesson. Cluster deletion and rebuilding were documented but not performed.

## 1. The environment you built

```text
Your Mac
└── Docker Desktop’s Linux environment
    └── kind node container: fabflow-control-plane
        ├── Kubernetes management components
        ├── containerd
        └── Test Pod: day3-smoke
            └── BusyBox container
                └── sleep 3600
```

| Term | Meaning and purpose |
| --- | --- |
| Kubernetes / K8s | A system that manages containerized applications through an API and controllers. |
| Cluster | A Kubernetes environment containing a control plane and nodes where workloads execute. |
| Node | A machine that runs Kubernetes components and Pods. It may be a physical machine, virtual machine, or—as in kind—a container. |
| kind | “Kubernetes IN Docker.” It creates local Kubernetes clusters using containers as nodes. |
| Pod | Kubernetes’ basic scheduling unit. It contains one or more containers that run together. |
| Container image | A packaged filesystem and configuration used to start a container. |
| Container | A running instance created from an image. |
| Container runtime | Software that manages container execution. Your kind node uses containerd. |

kind is designed for local development and testing. Your single-node environment
is useful for learning, but it does not demonstrate availability across multiple
machines. See the [kind documentation](https://kind.sigs.k8s.io/docs/user/quick-start/).

## 2. Docker Desktop, kind, and kubectl

```text
Docker Desktop → provides the container environment
kind           → creates Kubernetes nodes inside that environment
kubectl        → sends requests to the Kubernetes API
```

kubectl is a client. It does not run your application itself. It asks Kubernetes
to create, inspect, or change resources. For example, `kubectl get pods` asks the
selected Kubernetes API server for information about Pods.

| Component | Responsibility |
| --- | --- |
| API server | Receives Kubernetes API requests, validates them, and exposes cluster resources. |
| etcd | Stores Kubernetes cluster state and configuration. It does not automatically store FabFlow simulation results. |
| Scheduler | Chooses a suitable node for a Pod that has not yet been assigned one. |
| Controller manager | Runs controllers that work toward the desired state of resources. |
| kubelet | Runs on each node and ensures assigned Pods’ containers are running as specified. |
| containerd | Starts and manages containers at the kubelet’s request. |

The scheduler chooses a node; the kubelet on that node arranges container
execution through the runtime. See [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/).

## 3. Creating the cluster

```bash
kind create cluster --name fabflow --wait 120s
```

| Part | Purpose |
| --- | --- |
| kind | Run the kind tool. |
| create cluster | Create a Kubernetes cluster. |
| --name fabflow | Name the cluster fabflow. |
| --wait 120s | Wait up to this duration for the control plane to become ready during creation. |

kind created a node named `fabflow-control-plane` and configured access information
for kubectl. The existing `yunikorn-dev` cluster was left intact.

## 4. kubeconfig and context

```bash
kubectl config current-context
```

Observed output:

```text
kind-fabflow
```

| Term | Meaning |
| --- | --- |
| kubeconfig | Configuration kubectl uses to find clusters and authenticate. Its common default location is ~/.kube/config. |
| Context | A named combination of cluster, user credentials, and an optional default namespace. |
| Current context | The context kubectl uses when another is not explicitly selected. |

A context answers: which cluster should I contact, using which identity, and which
default namespace? Explicit selection makes the destination clear:

```bash
kubectl --context kind-fabflow get nodes -o wide
```

Docker context selects a Docker endpoint. Kubernetes context selects Kubernetes
connection settings. They are separate configurations.

See [kubeconfig and contexts](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/).

## 5. Reading node information

Your result included the following values:

| Field | Your value | Meaning |
| --- | --- | --- |
| NAME | fabflow-control-plane | Name of the node resource. |
| STATUS | Ready | The node reports readiness to accept Pods. |
| ROLES | control-plane | A role label indicating that the node hosts control-plane components. |
| AGE | 112s | Time since the node resource was created when observed. |
| VERSION | v1.37.0 | The kubelet version reported by the node. |
| INTERNAL-IP | 172.18.0.3 | The node’s internal network address. |
| EXTERNAL-IP | <none> | No external node IP is reported. |
| OS-IMAGE | Debian GNU/Linux 13 (trixie) | Operating system environment inside the node. |
| KERNEL-VERSION | 7.0.12-linuxkit (arm64) | Linux kernel used by the environment. |
| CONTAINER-RUNTIME | containerd://2.3.4 | Runtime managing containers on the node. |

`-o wide` requests additional output columns. This kind setup permits application
Pods on its control-plane node; your test Pod ran on that same node.

## 6. Creating a namespace

```bash
kubectl --context kind-fabflow create namespace fabflow
```

A namespace provides a scope for namespaced resources inside a cluster:

```text
Cluster: fabflow
├── Namespace: default
├── Namespace: kube-system
└── Namespace: fabflow
    └── Pod: day3-smoke
```

The cluster and namespace happen to share a name, but they are different resources.
Namespaces help organize applications, permissions, and resource quotas. They do
not automatically isolate network traffic. Some resources, including Nodes, belong
to the whole cluster rather than a namespace.

`-n fabflow` is shorthand for `--namespace fabflow`. If omitted, kubectl uses the
namespace configured in the selected context, or default if none is configured.
See [Namespaces](https://kubernetes.io/docs/concepts/overview/working-with-objects/namespaces/).

## 7. Creating the test Pod

```bash
kubectl --context kind-fabflow -n fabflow run day3-smoke \
  --image=busybox:1.37.0 \
  --restart=Never \
  --command -- sleep 3600
```

Read this as: in the kind-fabflow context and fabflow namespace, create a Pod named
day3-smoke using BusyBox, and run sleep 3600 without automatically restarting its
container after termination.

| Part | Explanation |
| --- | --- |
| run day3-smoke | Create a Pod with this name. |
| --image=busybox:1.37.0 | Use BusyBox tagged 1.37.0. BusyBox provides small Linux command-line utilities. |
| --restart=Never | Set the Pod’s container restart policy to Never. |
| --command | Treat the following executable as the container command. |
| -- | End kubectl option parsing; subsequent arguments belong to the container command. |
| sleep 3600 | Keep the main process running for 3,600 seconds so the container can be inspected. |
| Backslash at the end of a line | Continue the shell command on the next line. Do not place spaces after it. |

The BusyBox version and Kubernetes version identify different software; the matching
numbers do not imply a dependency.

## 8. What happens after Pod creation

```text
kubectl submits a Pod creation request
                  ↓
API server accepts and records the Pod
                  ↓
Scheduler assigns it to fabflow-control-plane
                  ↓
The node’s kubelet observes the assignment
                  ↓
containerd obtains the image if needed and starts the container
                  ↓
The container runs sleep 3600
                  ↓
Pod status is reported back through the API
```

A newly created Pod may briefly show Pending or ContainerCreating before Running.

## 9. Waiting for readiness

```bash
kubectl --context kind-fabflow -n fabflow wait \
  --for=condition=Ready pod/day3-smoke --timeout=120s
```

This waits for the Pod’s Ready condition to become true. It does not add a readiness
probe. Our test Pod had no custom readiness probe. Later, FabFlow will use an HTTP
readiness probe to check whether its API can accept requests.

## 10. Reading Pod information

Your observed values were:

| Field | Value and meaning |
| --- | --- |
| NAME | day3-smoke: Pod name. |
| READY | 1/1: one regular container ready out of one regular container. |
| STATUS | Running: the displayed status indicates the Pod is running. |
| RESTARTS | 0: the container has not restarted. |
| AGE | 19s when observed: time since the Pod resource was created. |
| IP | 10.244.0.5: the Pod’s cluster-network address. |
| NODE | fabflow-control-plane: the node to which the Pod was assigned. |
| NOMINATED NODE | <none>: no nominated node reported for scheduling/preemption purposes. |
| READINESS GATES | <none>: no additional custom readiness gates configured. |

Running and Ready describe different things. A container can run while its
application is unready. Also, the node IP 172.18.0.3 and Pod IP 10.244.0.5 represent
different network endpoints. A Pod IP does not automatically expose an application
to your Mac browser.

## 11. Executing a command inside the container

```bash
kubectl --context kind-fabflow -n fabflow exec day3-smoke -- echo hello-fabflow
```

Observed output:

```text
hello-fabflow
```

exec starts an additional process inside an existing container. Before `--`, the
arguments select the Pod and request execution. After `--`, they specify the
container command. The original sleep process continues while echo prints and exits.

For a Pod with multiple containers, select one explicitly:

```bash
kubectl --context kind-fabflow -n fabflow exec POD_NAME -c CONTAINER_NAME -- COMMAND
```

POD_NAME, CONTAINER_NAME, and COMMAND above are placeholders.

## 12. Deleting the Pod

```bash
kubectl --context kind-fabflow -n fabflow delete pod day3-smoke
kubectl --context kind-fabflow -n fabflow get pods
```

Observed output:

```text
pod "day3-smoke" deleted from fabflow namespace
No resources found in fabflow namespace.
```

Deletion requests Pod termination, normally allowing a graceful termination period
before forcing containers to stop. The final query returned no Pods in fabflow;
the namespace and cluster still exist.

## 13. Why the Pod did not return

This was a standalone Pod with no Deployment managing it.

| Mechanism | Responsibility |
| --- | --- |
| Container restart policy | Controls whether the kubelet restarts a terminated container inside an existing Pod. |
| Deployment and ReplicaSet controllers | Create replacement Pods to maintain the requested replica count. |

```text
Standalone Pod deleted
    → no managing controller creates a replacement

Deployment-managed Pod deleted
    → its controller works to restore the desired replica count
```

restart=Never controlled container restarts. The absence of a managing controller
explains why deleting the Pod did not produce a replacement.
See [Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/).

## 14. Rebuilding the environment

These commands are recorded for future practice. The first removes the entire
fabflow learning cluster and its resources. Do not execute it when you want to
retain the environment for Day 4, and do not delete the existing yunikorn-dev cluster.

```bash
kind delete cluster --name fabflow
kind create cluster --name fabflow --wait 120s
kubectl --context kind-fabflow create namespace fabflow
```

We did not perform this rebuild exercise during Day 3.

## 15. Learning checkpoint

You successfully followed this workflow:

```text
Choose a cluster
    → choose a namespace
    → create a Pod
    → observe its placement and status
    → execute a command
    → delete the Pod
    → verify the result
```

Practice explaining in English:

1. What is the difference between a node and a Pod?
2. What does a Kubernetes context select?
3. How is a namespace different from a cluster?
4. What is the difference between Running and Ready?
5. Why did the deleted test Pod not return?
6. How does restarting a container differ from creating a replacement Pod?

The original Chinese progress and acceptance record is available in
[Day 3: Local cluster](day03-local-cluster.md).
