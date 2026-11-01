# Day 13：Kubernetes PostgreSQL、PVC 與 Secret

狀態：逐步實作、核心驗收與觀念確認完成。依據使用者終端輸出及助理工作區檢查。
Excel 日期為規劃日期，實際時數待填；進度 13/30。

## 本課部署

- `postgres-pvc.yaml`：fabflow namespace 的 postgres-data PVC，1Gi、ReadWriteOnce，
  指定 standard StorageClass。
- `postgres.yaml`：PostgreSQL 17，單副本 Deployment、Recreate 策略；資料 PVC
  掛載 /var/lib/postgresql/data，PGDATA 指向其中 pgdata 子目錄。
- 密碼從 postgres-credentials Secret 的 POSTGRES_PASSWORD 取得，DB/user 皆為 fabflow。
  不保存或輸出 Secret 內容；本機 .env 保持忽略，不提交真實憑證。
- postgres-init ConfigMap 使用既有 001_completed_runs.sql，唯讀掛載到
  /docker-entrypoint-initdb.d；只在空資料目錄首次啟動時初始化，不是 migration。
- DB startup/readiness probes 使用 pg_isready；requests 為 100m/128Mi，
  limits 為 1000m/512Mi。pg_isready 不等於已驗證密碼與資料表，因此另做 SQL 查詢。
- `postgres-service.yaml`：ClusterIP postgres:5432，以 `app: fabflow-postgres` 的
  Pod label 選擇後端。
- `api.yaml`：由 fabflow-api:day4 更新至 day13；新增 FABFLOW_RUN_STORE=postgres，
  PGHOST=postgres、PGPORT=5432、PGDATABASE/PGUSER=fabflow，PGPASSWORD 引用同一 Secret。

## 起始狀態與儲存

課程開始重新確認 kind-fabflow：fabflow-control-plane Ready；API 與 Dashboard
均 1/1 Running，Docker Desktop 重啟後各有一次 restart，當時尚無 PVC。
standard 為預設 StorageClass，rancher.io/local-path provisioner、Delete reclaim
policy、WaitForFirstConsumer、不可擴容。PVC 建立後 Pending，建立使用它的 DB
Pod 後 Bound，符合延後配置的行為。

這是本機 kind 儲存，沒有配置雲端磁碟，也沒有該項雲端磁碟費用，仍占用本機
Docker 磁碟空間。PVC 並非一律免費，雲端 StorageClass 可能對應收費磁碟。

## 建立與重現步驟

以下假設 kind cluster、fabflow namespace 與既有 Dashboard 已建立，且有 standard
StorageClass；不是從空白環境重建的驗收。建立 Secret 前確認本機 .env 只含
POSTGRES_PASSWORD，避免把不相關設定帶入。以下 create 指令適用於資源尚不存在時；
已有 Secret 不要盲目替換密碼，既有 DB 資料目錄不會因此自動更新角色密碼。

```bash
kubectl apply -f deployments/k8s/postgres-pvc.yaml
kubectl create secret generic postgres-credentials -n fabflow --from-env-file=.env
kubectl create configmap postgres-init -n fabflow \
  --from-file=001_completed_runs.sql=deployments/postgres/init/001_completed_runs.sql
kubectl apply -f deployments/k8s/postgres.yaml
kubectl rollout status deployment/postgres -n fabflow --timeout=180s
kubectl get pods,pvc -n fabflow
kubectl exec -n fabflow deployment/postgres -- \
  psql -U fabflow -d fabflow -v ON_ERROR_STOP=1 \
  -c "SELECT current_database(), current_user, to_regclass('public.completed_runs');"
kubectl apply -f deployments/k8s/postgres-service.yaml
kubectl get endpointslices -n fabflow -l kubernetes.io/service-name=postgres
docker build --target api -t fabflow-api:day13 .
kind load docker-image fabflow-api:day13 --name fabflow
kubectl apply --dry-run=server -f deployments/k8s/api.yaml
kubectl apply -f deployments/k8s/api.yaml
kubectl rollout status deployment/api -n fabflow --timeout=180s
```

kubectl apply 整個 deployments/k8s 目錄不會自動建立上面的 Secret 與 SQL ConfigMap，
須先依指令準備。Secret 與 ConfigMap 的建立方式記錄於此，未新增含密碼的 manifest。
day13 映像須明確建置並載入 kind；這個本機 tag 不代表已推送 registry。

使用者輸出確認：

- Secret Opaque、DATA=1；ConfigMap DATA=1。
- postgres-68b5ffb575-2k8mj 為 1/1 Running、0 restarts。
- PVC postgres-data Bound，PV pvc-60e544b2-48ce-4579-b74c-49669e01b4a9、1Gi、RWO。
- SQL 回 fabflow / fabflow / completed_runs，證實首次初始化建立表。
- Service ClusterIP 10.96.63.238:5432；EndpointSlice 對應 10.244.0.8:5432。
  IP 為本次觀察值，重建時可能改變，連線使用 Service DNS 而非固定 IP。
- 新版 API Pod api-5ffdfc4f9-ksk42 為 1/1 Running，從 API 容器以 psycopg
  使用環境設定連 postgres Service，SQL 驗證資料庫、使用者、資料表皆符合預期。

## API Pod 重建驗收

以既有腳本經由 API Pod 的 127.0.0.1:8000 發出真實 HTTP POST，建立
`1ab982bf-4c71-4051-94f2-e7f95f53dab5`，12 lots、142 events；201 與 Location 通過。
這是新的 K8s DB 結果，不是 Compose DB 資料搬移。

```bash
kubectl exec -i -n fabflow deployment/api -- \
  python - prepare --snapshot /tmp/fabflow-day13-check.json \
  < scripts/check_postgres_persistence.py
kubectl exec -n fabflow deployment/api -- cat /tmp/fabflow-day13-check.json \
  > /tmp/fabflow-day13-before-pod-rebuild.json
```

Mac 上解析 JSON，確認 run ID 一致、12 lots、142 events、metrics 非空。快照已在
Pod 外，才刪除當時的 API Pod。以下舊 Pod 名稱僅為本次實際操作，重跑須查詢當前名稱：

```bash
kubectl delete pod -n fabflow api-5ffdfc4f9-ksk42
kubectl rollout status deployment/api -n fabflow --timeout=180s
kubectl get pods -n fabflow
```

新 Pod 為 api-5ffdfc4f9-w6r5t，1/1 Running、0 restarts。傳回外部快照再比對：

```bash
kubectl exec -i -n fabflow deployment/api -- \
  python -c 'import sys; from pathlib import Path; Path("/tmp/fabflow-day13-check.json").write_bytes(sys.stdin.buffer.read())' \
  < /tmp/fabflow-day13-before-pod-rebuild.json
kubectl exec -i -n fabflow deployment/api -- \
  python - verify --snapshot /tmp/fabflow-day13-check.json \
  < scripts/check_postgres_persistence.py
```

使用者實際結果：

```text
PASS: summary matches pre-restart snapshot
PASS: metrics matches pre-restart snapshot
PASS: events matches pre-restart snapshot
PASS: unknown ID returns HTTP 404 for summary
PASS: unknown ID returns HTTP 404 for metrics
PASS: unknown ID returns HTTP 404 for events
run_id: 1ab982bf-4c71-4051-94f2-e7f95f53dab5
```

比對包含完整 events 內容與順序；舊 API Pod 已刪除，結果不依賴其記憶體。
本機快照在 /tmp，不提交 Git，也不是 DB 備份。

## 觀念與限制

使用者最初認為只要存入 PostgreSQL，刪除 kind cluster 後也會保留；補充後已確認
需要看實際儲存位置。目前資料位於 kind 節點的本機儲存，刪除整個 cluster
可能連資料一起移除，不能保證保留。API Pod 重建、DB Pod 重建與 cluster 刪除
是不同故障範圍。

- 已實測：API Pod 重建後完整結果與未知 ID 行為。
- 尚未實測：PostgreSQL Pod 重建、PVC/namespace 刪除、整個 cluster 重建。
- 單實例 DB 不具備高可用，Recreate 更新期間 DB 會暫時不可用，尚未建立備份。
- standard 的 Delete reclaim policy 表示刪除 PVC 可能連帶回收底層資料，
  不要直接重複 Day 8 的刪 namespace 練習；先另行規劃備份與恢復。
- DB readiness 不驗證完整 schema，API readiness 也仍未檢查 DB。
- 本課未驗證 Dashboard UI、API Service/port-forward 流程或 K8s DB outage；
  HTTP 寫入與比對均在 API Pod 內執行。沒有量測恢復耗時、效能或零停機。
- 尚未驗證雙 API Pod 查詢一致性；那是 Excel Day 14 的下一課。

## 最後檢查

使用者提供：ruff format --check . 為 96 files already formatted，pytest -q
為 184 passed、1 項上游 TestClient/HTTPX 棄用警告，git diff --check 無輸出。
三個 PostgreSQL manifest 的 server dry run 通過：PVC unchanged、Deployment
configured、Service unchanged；dry run 不會修改 cluster，configured 不等於已套用。
助理另執行 ruff check . 通過。主機測試使用既有 Python 3.14，API 映像以
Python 3.12 建置；本課未重跑完整容器 Pytest 或遠端 CI。

Excel 同步為 Day 13 完成：13/30（約 43.3%），實際時數空白。Day 14 開始前仍需
重新確認 cluster 與 DB 狀態，依一步一步教學方式驗證雙 API 副本。
