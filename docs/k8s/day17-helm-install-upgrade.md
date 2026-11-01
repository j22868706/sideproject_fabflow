# Day 17：Helm 安裝與升級

狀態：逐步設定、乾淨 namespace 安裝、HTTP 驗收與副本調整升級完成。
依使用者終端輸出與助理本機渲染檢查；Excel 日期為規劃日期，實際時數待填。

## Chart 設定

沿用 Helm v4.3.1、Chart.yaml 0.1.0，補齊以下設定：

- values：postgres.database/username、existingSecret/passwordKey、persistence
  storageClass/size。密碼不寫入 values。
- postgres-pvc.yaml：release-prefixed PVC，standard、1Gi、ReadWriteOnce。
- files/001_completed_runs.sql：複製既有 SQL；postgres-init.yaml 使用 required、
  Files.Get、nindent 4 產生 ConfigMap，兩份 SQL 須保持同步。
- PostgreSQL 引用外部 Secret，PVC 掛載 /var/lib/postgresql/data，PGDATA 指向
  pgdata 子目錄；SQL ConfigMap 唯讀掛載 /docker-entrypoint-initdb.d。
- API 啟用 postgres store，以 release-prefixed DB Service 連線，引用同一 Secret。
- dashboard-config.yaml 提供 API URL，Dashboard 透過 configMapKeyRef 讀取；
  此 release 實際位址為 http://fabflow-api:8000。
- API/Dashboard 加入 startup、readiness、liveness；DB 加入 startup/readiness，
  以 pg_isready -h 127.0.0.1 檢查 TCP。此檢查不等於帳密/schema 驗證。
- 各容器補 requests/limits，目前寫在模板，尚未參數化。API 100m/128Mi、
  Dashboard 100m/256Mi、DB 100m/128Mi；各 limit 1000m/512Mi。

完整產物為 9 個資源：3 Deployment、3 Service、2 ConfigMap、1 PVC。
Secret 由使用者事先建立，未由 chart 管理。

## 起始狀態與安裝

開始前重新確認 kind-fabflow 節點 Ready，原 fabflow namespace 兩 API、Dashboard、
PostgreSQL Ready、PVC Bound；fabflow-helm 尚不存在。逐一編輯與渲染模板後：

```bash
helm lint deployments/helm/fabflow
kubectl create namespace fabflow-helm
kubectl create secret generic postgres-credentials -n fabflow-helm --from-env-file=.env
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  | kubectl apply --dry-run=server -f -
helm install fabflow deployments/helm/fabflow -n fabflow-helm --wait --timeout 5m
```

Secret 為 Opaque、DATA=1，未輸出或提交密碼，.env 保持忽略。Secret 為 namespace
範圍，不能直接引用原 fabflow 中的 Secret。9 個資源 server dry run 全通過。
實際安裝後 release fabflow 為 deployed、revision 1、chart fabflow-0.1.0。
兩 API、Dashboard、PostgreSQL 全部 Ready、0 restarts；新 PVC Bound，PV 為
pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd，1Gi、RWO。
既有 fabflow namespace 與其資料保留，新 release 使用另一個 DB，未搬移舊結果。

## 連線與 HTTP 驗收

從 Helm API Pod 使用 psycopg 與環境設定，查詢 current_database、current_user、
to_regclass('public.completed_runs')，回 fabflow / fabflow / completed_runs。
這驗證 API 到 DB Service 的連線、Secret 帳密與空資料目錄的 SQL 初始化。

```bash
kubectl exec -i -n fabflow-helm deployment/fabflow-dashboard -- \
  python - < scripts/smoke_containers.py
```

實際結果：

```text
PASS: Three-stage baseline; finish=175, cycle=70.5, transport_jobs=0
PASS: AMHS bottleneck; finish=203, cycle=142.75, transport_jobs=40
PASS: dashboard health/HTML, API readiness, and both create/query/metrics/events workflows
```

此為真實 Dashboard HTTP/HTML、API Service 與兩情境 KPI 驗收，未做瀏覽器互動。

## 升級與外部快照

prepare 建立 run d5c0555d-4b4c-4833-9ab8-153cc6cb9f60，12 lots、142 events，
201 與 Location 通過。Pod 快照 /tmp/fabflow-day17-check.json 複製至 Mac
/tmp/fabflow-day17-before-upgrade.json，解析確認 ID、metrics 非空與事件數完整。
建立與複製均使用 deployment/fabflow-api，當時成功；重跑時建議指定同一具名 Pod，
不假設兩次 Deployment exec 一定選到相同副本。

```bash
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm \
  --set api.replicaCount=1 --wait --timeout 5m
```

revision 2 deployed，API 1/1。傳入 Mac 快照後 verify 通過：三份結果一致、
未知 ID 三端點 404。接著恢復預設值：

```bash
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm \
  --reset-values --wait --timeout 5m
helm history fabflow -n fabflow-helm
kubectl get deployment,pods,pvc -n fabflow-helm
```

revision 3 deployed，1/2 superseded；chart 三次皆 0.1.0。API 恢復 2/2，
DB/Dashboard 各 1/1，四個 Pod 均 0 restarts，PVC/PV 相同。reset-values 清除全部
前次覆寫，不只 replicaCount；本次適用全部預設值。

最後將外部快照傳入新增 Pod fabflow-api-b6c874b7-xsvxg，verify 再次輸出：

```text
PASS: summary matches pre-restart snapshot
PASS: metrics matches pre-restart snapshot
PASS: events matches pre-restart snapshot
PASS: unknown ID returns HTTP 404 for summary
PASS: unknown ID returns HTTP 404 for metrics
PASS: unknown ID returns HTTP 404 for events
run_id: d5c0555d-4b4c-4833-9ab8-153cc6cb9f60
```

此為副本參數升級，未改 image 或 Pod template。使用者正確說明 release revision
因 upgrade 增加，chart version 因 Chart.yaml 未改仍為 0.1.0。
未量測更新中的失敗請求，未驗證 image rolling update、rollback 或零停機。

## 最後檢查與警告

使用者提供的最終結果：helm lint 1 chart、0 failed（只有 icon INFO）；
9 資源 server dry run 通過；cmp 兩份 SQL 一致；ruff check 通過；format check
101 files already formatted；pytest 184 passed、1 項上游 TestClient/HTTPX 棄用
警告；git diff --check 無輸出。助理另讀取並重新渲染最後 chart。

server dry run 對 Helm 資源出現缺少 kubectl last-applied annotation 警告，
因資源由 Helm 建立；dry run 沒有實際新增 annotation，不需轉用 kubectl 管理。
後續實際更新用 Helm，避免雙重管理。主機測試使用 Python 3.14，API 為 Python 3.12；
未在容器重跑完整 Pytest，未確認遠端 CI。

## 管理範圍與限制

原始 YAML 管理 fabflow，Helm release 管理 fabflow-helm。chart PVC 無 keep policy，
helm uninstall 或刪 namespace 可能刪 PVC，standard/Delete policy 可連帶回收資料；
清理前須另行保存資料，本課未測卸載。Secret 不由 release 管理，但 namespace 刪除
仍會移除 Secret。

DB 單實例、本機儲存，沒有 HA/備份；API readiness 不檢查 DB。SQL 只用於空目錄，
不是 migration，Secret 改變也不會自動輪替既有 DB 密碼。預設映像是已載入 kind
的 day13/day5 本機 tag，尚未發布 registry。

Excel 同步 Day 17 完成，17/30（約 56.7%），實際時數空白。下一課 Day 18 依 Excel
建立映像 CI 與 commit SHA tag；開始前檢查 repo/CI 狀態，繼續一次一步教學。
