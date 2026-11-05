# Day 19: Versioned Deployment

Status: Specified-commit images, old-result preservation, and new HTTP workflows
accepted from learner terminal output. Progress 19/30 (63.3%); hours unrecorded.
No update-window availability or zero-downtime claim.

## Image origin and architecture

Mac and kind-fabflow node were arm64/Ready. Initial fabflow-helm had API 2/2,
dashboard/DB 1/1, PVC Bound. Branch feat/day19-versioned-deployment committed
Day 18 closeout as 395df1ec02a010163ea46e68374feb607c0c39bd; tree was clean before
building both linux/arm64 targets from that commit, then loading into kind.
No CI image download or registry publication occurred. SHA tags identify source,
not bit-identical reproducibility: base digests/dependencies are not fully pinned.
Later values/docs commits do not change the built source SHA.

| Image | Local build ID |
| --- | --- |
| API | sha256:30ec324bd2e26ca6c963ac2db6a4c624815f772f183d687b04b4330a46792471 |
| Dashboard | sha256:a34e7e8fa814f28acab9c477ac18c68b4d8bc21c00061cb43129b15c18035989 |

Both inspected tags were the full SHA and platform linux/arm64; kind reported
loading and Pods subsequently used the specified tags.

## Helm configuration and rollout

values-kind.yaml pins both repositories/tags and IfNotPresent for preloaded local
kind images. Default values remain day13/day5: always pass the override explicitly.
A new cluster needs images reloaded. Lint passed (icon INFO); rendering showed both
SHA images plus postgres:17. Upgrade created revision 4 deployed, chart still 0.1.0.
New API Pods 77bbcb6b4d-2j8nz/cwpxr and dashboard 899996b87-fvxgt were Ready with
zero restarts. Runtime API imageID for both:
sha256:4c4651d4b055dee0dbab2c798f4e3f5fa7985267abe49f319c7a80d3166aa912;
dashboard: sha256:73126bbbe18ab992d475143308cb3bb67ffa55f453f6c7d9c44153f9bb9dd9f0.
Tools can expose different ID/digest types; equality to local build IDs is not claimed.
DB Pod 7b879c7d67-tsf4s and PVC/PV pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd
remained unchanged/Bound.

## Data and HTTP acceptance

Before upgrade, Service forwarding to localhost:8000 created run
fd6d54d2-67e0-4fbb-8682-e737b4cd6711 with 201/Location and Mac snapshot
/tmp/fabflow-day19-before-upgrade.json. After restarting forwarding, all three
complete responses matched and all unknown-ID endpoints returned 404. This used
the Service connection, not separate named-Pod checks.

Dashboard-container smoke passed baseline 175/70.5/0, AMHS 203/142.75/40,
dashboard health/HTML, readiness, and both create/query/metrics/events workflows.
No interactive browser acceptance occurred.

## Limits and handoff

No continuous request measurement, command timing, rollback, or zero-downtime
verification. A single local DB/PVC is not HA or cluster-loss recovery. Host rg
was unavailable during teaching, so grep was used; zsh custom-columns containing
brackets require quoting. Changes awaited commit/PR CI and full Pytest was not
rerun. Day 20 separately inspected strategy and measured rolling update; successful
upgrade here was not evidence that Day 20 acceptance was already complete.

## Recorded commands and examples

These blocks preserve the milestone procedures and recorded output in their original
order. They describe the historical configuration; review current manifests and
prerequisites before repeating them. Resource names and IP addresses are observations,
not fixed values.

```bash
FABFLOW_IMAGE_TAG=$(git rev-parse HEAD)
docker build --platform linux/arm64 --target api --tag "fabflow-api:$FABFLOW_IMAGE_TAG" .
docker build --platform linux/arm64 --target dashboard --tag "fabflow-dashboard:$FABFLOW_IMAGE_TAG" .
kind load docker-image "fabflow-api:$FABFLOW_IMAGE_TAG" "fabflow-dashboard:$FABFLOW_IMAGE_TAG" --name fabflow
```

```bash
helm lint deployments/helm/fabflow -f deployments/helm/fabflow/values-kind.yaml
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml | grep -E 'image:|imagePullPolicy:'
helm upgrade fabflow deployments/helm/fabflow --namespace fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml --wait --timeout 5m
```

```bash
python scripts/check_postgres_persistence.py prepare --api-url http://127.0.0.1:8000 \
  --snapshot /tmp/fabflow-day19-before-upgrade.json
```

```bash
kubectl exec -i -n fabflow-helm deployment/fabflow-dashboard -- \
  python - < scripts/smoke_containers.py
```
