# Day 24：Argo CD 本機示範

狀態：使用者逐步完成安裝、UI 登入、Application 手動同步、指定映像及 HTTP 驗收。
證據為本次使用者終端輸出與 UI 狀態回報；未另外保存完整 raw logs。
文件尚待提交/CI，實際時數未填。

## 環境與管理範圍

kind-fabflow、ARM64 單節點。開始時節點 Ready，fabflow-helm revision 9 deployed。
原 fabflow（raw manifests）、fabflow-helm（Helm）保留；新 fabflow-gitops 由 Argo CD 管理。
三個環境仍共享同一節點，namespace 隔離不提供節點故障隔離。
使用者確認 Day 23 commit 9448468 四個 CI jobs 全通過，遠端結果未由助理獨立取得。

## 初始化與 UI 連線

依 [Argo CD 官方流程](https://argo-cd.readthedocs.io/en/stable/getting_started/)：

```bash
kubectl config current-context
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl get pods -n argocd
```

上述 create/install 用於尚未安裝的環境。本次七個 Pod 初始全部 1/1 Running、零重啟。
使用浮動 stable manifests，未保存安裝檔 digest，因此日後重跑不保證相同版本。
Server 日誌顯示 v3.6.0、commit f55566445ee3a2a4f3339bf10df0f6bc1ecf7f23。

另一終端保持執行：

```bash
kubectl port-forward -n argocd \
  --address 127.0.0.1 service/argocd-server 18080:443
```

實際輸出 18080 -> 8080，為 Service targetPort 對應。開啟 https://127.0.0.1:18080，
確認本機網址後處理預設憑證警告；帳號 admin，密碼只在自己的終端取得，不貼出或提交：

```bash
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath='{.data.password}' | base64 -d
```

使用者確認登入 Applications UI。若轉發因 Pod 中斷，先確認 Server 恢復 Ready，
再重啟 port-forward。Ctrl+C 僅停止本機轉發，不移除 Argo CD。

## Application 設定與同步

在 repository root 預先建立 namespace 與外部 Secret（只在不存在時執行）：

```bash
kubectl create namespace fabflow-gitops
kubectl create secret generic postgres-credentials \
  -n fabflow-gitops --from-env-file=.env
```

.env 必須先依 .env.example 設定本機密碼並維持忽略。Secret 不由 chart 建立，
且無法跨 namespace 引用；新環境使用自己的 DB/PVC。

UI 建立的 Application 最終設定：

| 欄位 | 實際設定 |
| --- | --- |
| Name / Project | fabflow-gitops / default |
| Repository | https://github.com/j22868706/sideproject_fabflow.git |
| Target revision | 9448468（固定 commit，非追蹤 main） |
| Path | deployments/helm/fabflow |
| Helm valueFiles | values-kind.yaml |
| Helm releaseName | 未設定，預設使用 Application 名稱 fabflow-gitops |
| Destination server | https://kubernetes.default.svc |
| Destination namespace | fabflow-gitops |
| Sync policy | Manual，未啟用 auto sync；本次同步不勾 Prune/Force |

初次 UI 建立未保存 Helm values/releaseName，先部署了預設 day13/day5。
助理先前使用 fabflow-dashboard 驗收得到 NotFound；實際資源為 fabflow-gitops-*。
查詢 .spec.source.helm 為空，並確認實際映像後，使用以下 patch 修正 values：

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"spec":{"source":{"helm":{"valueFiles":["values-kind.yaml"]}}}}'
kubectl get application fabflow-gitops -n argocd \
  -o jsonpath='{.spec.source.helm}{"\n"}'
```

輸出 {"valueFiles":["values-kind.yaml"]}。保留實際 releaseName，不另改資源名稱。
patch 修改 Application 設定，本次仍須 UI Refresh、Sync、Synchronize 才更新工作負載。
Healthy/Synced 必須另搭配映像核對與 HTTP 驗收，單看 UI 不能證明使用指定 values。
Argo CD 使用 chart 產生資源；本環境不以 helm upgrade/rollback 管理。

## 更新期間異常與恢復

Argo CD Server port-forward 中斷：Pod 內 localhost:8080 connection refused。
Server 一度 0/1、重啟一次；目前容器日誌顯示重新監聽 8080，之後恢復 1/1。
沒有取得 previous logs/終止原因，不能把日誌中的 warning 當成重啟根因。

同步指定映像後曾 Synced/Progressing。事件包含多個探針逾時、NodeNotReady、
etcdserver request timed out，以及 Endpoint/EndpointSlice 更新失敗。
API 曾 3/2（更新暫存額外副本），DB Deployment/Pod 查詢也曾呈現不一致。
節點後續 Ready，Memory/Disk/PID Pressure 都為 False。

診斷輸出：節點約 3.825 GiB、8 CPU、29 個 Pod；requests 記憶體 59%、limits 178%，
Argo CD Pod 未配置 requests/limits。requests 不是實際用量，limits 超額不等於 OOM。
docker stats 單次 CPU 821.53%、記憶體 1.827/3.825 GiB（47.76%）；BLOCK I/O
108GB/12.4GB 為累積量，不是當下速度。ps 為程序存活期平均 CPU，不能與 stats
短時間取樣直接對照，也未定位單一異常程序。CPU 忙碌是可能因素，根因未確認。

本次沒有為排障刪 Pod、重啟 Docker 或修改探針。後續更新收斂：API 2/2、Dashboard/DB
各 1/1，Application Synced/Healthy。最終 GitOps API b44xc 重啟一次、sz8mt 零次，
Dashboard/DB 零次。此為最後觀察，不代表長期穩定或無中斷。

## 最終驗收

```bash
kubectl get application fabflow-gitops -n argocd \
  -o jsonpath='{.status.sync.status}{" / "}{.status.health.status}{"\n"}'
kubectl get deployments -n fabflow-gitops \
  -o 'custom-columns=NAME:.metadata.name,IMAGES:.spec.template.spec.containers[*].image'
kubectl exec -i -n fabflow-gitops deployment/fabflow-gitops-dashboard -- \
  python - < scripts/smoke_containers.py
```

使用者輸出確認：

- Synced / Healthy，UI source revision 9448468。
- API fabflow-api:794dbaafc1697a8812358b30b0808c6100242ebe。
- Dashboard fabflow-dashboard:395df1ec02a010163ea46e68374feb607c0c39bd。
- PostgreSQL postgres:17。
- baseline finish=175、cycle=70.5、transport_jobs=0；AMHS 203/142.75/40。
- 最後 Dashboard health/HTML、API readiness、兩情境 create/query/metrics/events 全 PASS。

此處 9448468 是 chart/values 的來源；映像 SHA 是各應用映像的來源，兩者可不同。
kind 須預載對應映像，CI 未提供 registry 發布。本次沒有啟用自動同步、測試 Git 變更
自動部署、完整舊資料跨更新比對或刪除 Application。
保留三套環境與 PVC；chart 無 keep policy，勿用 namespace/PVC 刪除作清理。

進度同步 24/30（80%），實際時數空白。僅修改文件與進度表，未改應用/chart，
未重跑本機 Pytest；文件待提交與 CI。下一課依 workbook 另行確認，一次一步進行。
