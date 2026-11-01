# FabFlow Helm chart

Day 17 completed installation and replica-change upgrade acceptance on local kind
with Helm v4.3.1. The chart renders three Deployments, three ClusterIP Services,
two ConfigMaps, and one PVC. Default API/dashboard replicas are 2/1;
PostgreSQL is fixed at one replica with Recreate strategy.

From the repository root:

```bash
helm lint deployments/helm/fabflow
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm
cmp deployments/postgres/init/001_completed_runs.sql deployments/helm/fabflow/files/001_completed_runs.sql
```

Keep both SQL copies synchronized. Init SQL only runs against an empty PostgreSQL
data directory; chart upgrades do not migrate an existing schema.

Before a fresh installation, build/load the configured API/dashboard images into
kind. Default tags are fabflow-api:day13 and fabflow-dashboard:day5; they are local
images, not published registry images. The cluster needs the standard StorageClass.
The ignored local .env must contain only the intended POSTGRES_PASSWORD entry.
For a new namespace:

```bash
kubectl create namespace fabflow-helm
kubectl create secret generic postgres-credentials -n fabflow-helm --from-env-file=.env
helm install fabflow deployments/helm/fabflow -n fabflow-helm --wait --timeout 5m
helm list -n fabflow-helm
kubectl get deployment,pods,pvc -n fabflow-helm
kubectl exec -i -n fabflow-helm deployment/fabflow-dashboard -- python - < scripts/smoke_containers.py
```

Use upgrade for an existing release. Day 17 tested a temporary API scale-down,
then restored chart defaults:

```bash
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm --set api.replicaCount=1 --wait --timeout 5m
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm --reset-values --wait --timeout 5m
```

Reset clears all previous overrides, not only replicaCount. Review values before
using it in a differently configured environment. Chart version 0.1.0 and release
revision are independent; image tags are configured in values.yaml.

Resources use the release name as a prefix and the release namespace. API and DB
reference an externally created Secret; the chart contains no passwords and does
not create that Secret. A ConfigMap provides the dashboard API URL. Manage the
original fabflow namespace with deployments/k8s, and fabflow-helm with Helm.

The PVC is chart-managed without a keep policy. Uninstalling this release or
deleting its namespace can remove the PVC and reclaim DB data with the current
Delete StorageClass policy. Preserve data before cleanup. A single local DB is
not HA or a backup; API readiness does not check database availability.

See [Day 16 skeleton evidence](../../../docs/k8s/day16-helm-skeleton.md) and
[Day 17 installation/upgrade evidence](../../../docs/k8s/day17-helm-install-upgrade.md).
