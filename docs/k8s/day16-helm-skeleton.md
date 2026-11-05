# Day 16: Helm Chart Skeleton and Values

Status: Local chart, lint, rendering, and overrides accepted. No chart installation
at this milestone. Evidence: learner output and assistant rendering checks.
Progress 16/30 (53.3%); actual hours unrecorded.

## Initial state and structure

Working tree clean; kind node Ready, both APIs/dashboard/DB Ready, PVC Bound.
Homebrew was present but Helm absent. Learner installed Helm v4.3.1+gc0d08d0.
Files: Chart.yaml, README.md, values.yaml, and API/dashboard/postgres templates.
Chart API v2, name fabflow, application type, version 0.1.0; chart API version is
separate from Helm CLI major version, and chart version is not an image tag.

| Component | Default image | Replicas | Service port |
| --- | --- | ---: | ---: |
| API | fabflow-api:day13 | 2, from values | 8000 |
| Dashboard | fabflow-dashboard:day5 | 1, from values | 8501 |
| PostgreSQL | postgres:17 | 1, fixed/Recreate | 5432 |

Values parameterize repositories/tags/pullPolicy and Service ports; container ports
remain fixed and targetPort references their names. Changing a Service port does
not change the process listener. Release.Name prefixes resource names;
Release.Namespace scopes resources. Instance/component labels consistently match
Deployment and Service selectors. The chart does not create Namespace.

## Rendering acceptance

The learner built Chart.yaml/values, checked show chart/show values, and rendered
each template with show-only. Both learner and assistant lint: one chart, zero
failures; optional icon recommendation was INFO. Override api.replicaCount=3 and
api.image.tag=day16-check rendered three API replicas with that tag; it did not
edit values.yaml or build/load the example image. Rendering needs no existing
namespace. Full assistant YAML parsing verified three Deployments/three Services,
namespace, selectors, default images/replicas, and named ports, plus the override.

The learner initially thought template changes live replicas. Correction: template
only generates YAML; install/upgrade/apply submits changes, while rollout status
only observes. No install, upgrade, apply, or workload change occurred here.
Lint/local parsing do not establish server acceptance or running applications.

## Quality and incomplete runtime configuration

Learner checks: Ruff, format 99 files, 184 tests/one upstream warning, diff checks
passed on Python 3.14. Assistant reran lint/rendering, not unchanged full Python
tests. Remote CI, Helm runtime HTTP/UI acceptance, and persistence were not tested.

The skeleton lacked API DB connection/backend settings, dashboard API URL,
ConfigMaps, Secret references, init SQL, PVC, probes, and resources. DB had no
password; it was not a runnable full stack. Day 17 completed these in a separate
namespace without replacing the raw-manifest deployment or deleting existing data.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```text
deployments/helm/fabflow/
├── Chart.yaml
├── README.md
├── values.yaml
└── templates/
    ├── api.yaml
    ├── dashboard.yaml
    └── postgres.yaml
```

```bash
helm show chart deployments/helm/fabflow
helm show values deployments/helm/fabflow
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --show-only templates/api.yaml
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --show-only templates/dashboard.yaml
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --show-only templates/postgres.yaml
helm lint deployments/helm/fabflow
```

```bash
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --set api.replicaCount=3 --set-string api.image.tag=day16-check \
  --show-only templates/api.yaml
```
