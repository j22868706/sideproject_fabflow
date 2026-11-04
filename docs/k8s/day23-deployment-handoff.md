# Day 23：CI 與部署交接

狀態：使用者依文件逐步完成指定版本重新部署、手動回復及完整資料/HTTP 驗收。
Day 23 操作驗收完成；文件尚待提交與 CI。未由另一位獨立操作者驗收。

## 本次驗收紀錄

使用者確認 commit `cd361fe` 的 quality、containers、images (api/dashboard) 四個
CI jobs 通過；助理未獨立取得遠端 CI 結果。CI 建置映像但未推送 registry、保存映像
供下載或部署到 kind。目前部署仍使用本機建置並載入 kind 的映像。

助理即時查詢及使用者輸出確認 context 為 kind-fabflow，namespace 為 fabflow-helm：

| 元件 | Ready | 映像 |
| --- | --- | --- |
| API | 2 | fabflow-api:794dbaafc1697a8812358b30b0808c6100242ebe |
| Dashboard | 1 | fabflow-dashboard:395df1ec02a010163ea46e68374feb607c0c39bd |
| PostgreSQL | 1 | postgres:17 |

Helm revision 7 deployed，為 Day 21 rollback to 5 產生的 revision。
使用者提供的 `helm get values --revision 7` 與 values-kind.yaml 映像設定一致。
postgres-credentials Secret 存在，類型 Opaque；未輸出密碼。
助理查詢時四個 Pod 零重啟，PVC Bound。

使用者執行並提供以下通過結果：

- Helm lint：0 failed，只有可選 icon INFO。
- Helm template：三個映像及 IfNotPresent 正確。
- kubectl apply server dry run：九個資源全部通過。annotation 警告不代表實際寫入。
- Dashboard Pod 內 HTTP smoke：baseline finish=175/cycle=70.5/jobs=0；
  AMHS finish=203/cycle=142.75/jobs=40。Dashboard health/HTML、API readiness、
  兩情境 create/query/metrics/events 全通過；不是真實瀏覽器驗收。

## 部署前準備

以下命令從 repository root 執行，適用本機 ARM64 kind-fabflow，release fabflow、
namespace fabflow-helm。原 fabflow namespace 使用 raw manifests，勿混用。
執行前先核對 context、架構、工作目錄與目標 SHA：

```bash
git status --short
kubectl config current-context
kubectl get nodes -o wide
helm history fabflow -n fabflow-helm
helm get values fabflow -n fabflow-helm
kubectl get pods,pvc -n fabflow-helm
kubectl get secret postgres-credentials -n fabflow-helm \
  -o custom-columns=NAME:.metadata.name,TYPE:.type
```

本次已驗收的回復基準為 revision 7；每次部署前重新確認並記錄當時可用的 revision。
僅有 deployed 狀態不足以證明功能正確，還須搭配 HTTP 驗收。

首次安裝到新 namespace 時，先從 .env.example 複製 .env 並設定本機密碼，保持忽略。
以下兩行只用於 namespace 與 Secret 尚不存在時：

```bash
kubectl create namespace fabflow-helm
kubectl create secret generic postgres-credentials -n fabflow-helm --from-env-file=.env
```

既有資料庫不可直接藉替換 Secret 輪替密碼。Chart 會建立初始化 ConfigMap/PVC；
SQL 只初始化空資料目錄，不是 migration。Secret 不由 chart 建立。
請保留既有 namespace、PVC 與資料；standard/Delete 與 chart 無 keep policy，
uninstall、刪除 PVC/namespace/cluster 可能造成資料遺失。

## 指定版本映像與檢查

目前 values-kind.yaml 分別指定上述 API 與 Dashboard SHA。新 kind 節點須先取得
兩個對應映像；IfNotPresent 在節點缺少映像時仍會嘗試遠端拉取。
若需重建，請在各自對應的乾淨 source checkout 中建置對應 target，例如：

```bash
FABFLOW_SOURCE_SHA=$(git rev-parse HEAD)
docker build --platform linux/arm64 --target api \
  --tag "fabflow-api:$FABFLOW_SOURCE_SHA" .
kind load docker-image "fabflow-api:$FABFLOW_SOURCE_SHA" --name fabflow
```

Dashboard 同理以 target dashboard、repository fabflow-dashboard 建置及載入。
新版本須先更新 override 檔的對應 tag，再檢查渲染；不要把目前 checkout 建出的
映像標成其他來源 SHA。SHA tag 表示來源，不保證重建位元相同，依賴尚未完全鎖定。

```bash
helm lint deployments/helm/fabflow -f deployments/helm/fabflow/values-kind.yaml
helm template fabflow deployments/helm/fabflow -n fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml
helm template fabflow deployments/helm/fabflow -n fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml \
  | kubectl apply --dry-run=server -f -
```

核對渲染映像與副本數。上述命令不更新叢集；不要移除 dry-run 後用 apply 管理 Helm 資源。

## 更新與功能驗收

以下 upgrade 會變更 release；本次已執行並產生 revision 8。首次部署使用 install 取代 upgrade。
明確提供 values-kind.yaml，避免落回預設 day13/day5 映像。

```bash
helm upgrade fabflow deployments/helm/fabflow -n fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml --wait --timeout 5m
helm history fabflow -n fabflow-helm
kubectl get deployments -n fabflow-helm \
  -o 'custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,IMAGES:.spec.template.spec.containers[*].image'
kubectl exec -i -n fabflow-helm deployment/fabflow-dashboard -- \
  python - < scripts/smoke_containers.py
```

smoke 會建立兩份新結果。它透過 Dashboard 的 FABFLOW_API_URL 連到 Helm API Service，
避開主機 localhost:8000 可能連到 Compose 的問題。預期輸出見本頁驗收紀錄。
readiness 未檢查 DB；必須實際 create/query 才能涵蓋目前資料庫流程。
若須證明舊結果保留，另使用 check_postgres_persistence.py 在更新前 prepare、更新後
verify，並將快照保存到 Pod 外；smoke 的新結果查詢不能取代舊結果完整比對。

## 失敗診斷與手動回復

```bash
helm history fabflow -n fabflow-helm
kubectl get pods -n fabflow-helm
kubectl describe deployment fabflow-api -n fabflow-helm
kubectl get events -n fabflow-helm --sort-by=.metadata.creationTimestamp
```

依故障 Pod 的實際名稱查看 describe；容器已啟動時再查 logs。
ImagePullBackOff 先核對 tag 與 kind 映像是否存在。Day 21 的失敗案例見
[故障與回復紀錄](day21-bad-version-rollback.md)。

若本次更新失敗且需回復到本頁已驗收基準，使用：

```bash
helm rollback fabflow 7 -n fabflow-helm --wait --timeout 5m
```

此命令會建立新 revision；後續演練須將 7 替換成更新前重新確認的基準。
回復後重跑 history、Deployment 映像/Ready 查詢、HTTP smoke，以及事先保存的
完整快照 verify。Helm rollback 不會回復資料庫內容，也不保證 schema 相容。
Day 21 的 localhost 資料比對屬於 Compose，不能當成 Helm rollback 資料完整性證據。

## 依文件執行結果（使用者終端輸出）

使用者確認 kind 節點內已存在兩個指定 SHA 映像。兩個 API SHA tag 顯示相同
crictl image ID；本課未重建映像，不據此推論來源完全一致。

1. 明確以 `--address 127.0.0.1` 將 Helm API Service 轉發到主機 18023，
   避免 Compose 8000/IPv4/IPv6 混淆。
2. prepare 建立 run `c9bffe27-def9-466a-ab05-4c87b5b31e05`，HTTP 201 + Location
   通過，完整快照保存於 Mac `/tmp/fabflow-day23-before-deploy.json`。
3. 使用本頁 upgrade 命令，revision 8 deployed，終端時間 2026-11-03 21:16:47。
4. verify：summary、metrics、ordered events 完全相同；未知 ID 三端點均 404。
5. rollback to 7 成功，新增 revision 9 deployed，終端時間 2026-11-03 21:17:31。
   未由這兩個歷史時間差推算命令耗時或停機時間。
6. API 2/2、Dashboard/DB 各 1/1。四個 Pod 名稱與零重啟不變，PVC Bound、
   PV 仍為 pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd。
7. 回復後 verify 再次通過完整結果與未知 ID 404。
   首次誤漏 --snapshot 導致讀取預設 Day 12 路徑失敗，補上參數後通過；不是 DB 錯誤。
8. 回復後 Dashboard Pod 內 smoke 全通過：baseline 175/70.5/0，AMHS 203/142.75/40，
   並印出最後的 Dashboard health/HTML、API readiness、兩情境 HTTP workflows PASS。

本次部署與回復採相同設定，沒有 Pod 重建；驗證操作流程及完整資料保留，
不代表新應用版本 rollout、故障版本恢復或 DB schema 回復測試。
Day 21 的壞映像演練及其資料證據限制仍維持原紀錄。
終端輸出由使用者提供，未另存完整 raw logs；快照仍位於 Mac /tmp，非永久備份。
後續部署應重新核對當時基準；本次結束後為 revision 9。

進度同步 23/30（約 76.7%），實際時數空白。文件變更通過 git diff --check；
未修改程式/chart，未重跑本機 Pytest。最新文件提交仍須 CI。
下一課依 workbook 為 Day 24：建立 Argo CD 本機示範，尚未開始。
未量測本課更新期間請求失敗率，不宣稱零停機或資料庫 HA。
