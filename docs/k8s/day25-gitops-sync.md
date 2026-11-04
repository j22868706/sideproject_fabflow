# Day 25：GitOps 同步、drift 與版本回復

狀態：使用者逐步操作完成，最終 Synced/Healthy、API 2/2、Dashboard/DB 各 1/1，
回復後 HTTP 回歸全通過。證據為使用者終端輸出；未保存完整 raw logs。
文件尚待提交與 CI，實際時數未填。

## 起始條件

沿用 [Day 24](day24-argocd-local.md) 的 kind-fabflow ARM64 單節點、Argo CD v3.6.0、
Application fabflow-gitops，目標 namespace fabflow-gitops。外部 Secret/PVC 保留。
原 fabflow/raw manifests 與 fabflow-helm/Helm 環境保留，不由本課 Application 管理。

Application 原固定 9448468，helm.valueFiles=[values-kind.yaml]，手動同步。
將 targetRevision 改為 main，刷新後解析至 63a5de770ce2e7139afb4bec7ad40e94b708a226，
仍 Synced/Healthy：文件 commit 改變不一定造成渲染資源差異。

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"spec":{"source":{"targetRevision":"main"}}}'
kubectl annotate application fabflow-gitops -n argocd \
  argocd.argoproj.io/refresh=hard --overwrite
```

本課沒有啟用 auto sync/self-heal。追蹤 main 會更新比較對象，套用仍須手動同步。

## Git 版本切換

節點確認 API 兩個完整 SHA tag 都已預載，crictl 顯示相同 image ID 3c86c5d31210f。
因此這次是部署設定/tag 切換，不代表應用功能改版或兩份不同映像內容。

使用者只修改 values-kind.yaml 的 API tag：794dbaa… → 395df1e…；Dashboard 不變。
helm lint 通過（僅 icon INFO），git diff --check 無錯誤。
提交並 push b05f4236e21d803ec8c0a2cc05a96c7668c3ab27。
刷新後 Application 顯示該 SHA、OutOfSync/Healthy；實際 Deployment 仍為
fabflow-api:794dbaafc1697a8812358b30b0808c6100242ebe，證明 Git 變更尚未套用。

UI Sync 遇到 Request has been terminated，port-forward 多次報 Pod 內 8080
connection refused。查詢 .operation 為空、最後成功 revision 仍 9448468，且映像未變；
因此當時未觀察到新同步的伺服器端執行紀錄，沒有直接重複送出要求。
改透過 Kubernetes API 提交手動同步 operation：

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"operation":{"initiatedBy":{"username":"kubectl-manual"},"sync":{"revision":"b05f4236e21d803ec8c0a2cc05a96c7668c3ab27","prune":false}}}'
```

initiatedBy 是操作紀錄欄位，不是認證或權限變更。此操作由 Argo CD controller 執行，
不依賴 UI port-forward；仍使用目前 kubectl 身分的 Kubernetes 權限。
結果 Succeeded、revision b05f423…，API tag 變為
fabflow-api:395df1ec02a010163ea46e68374feb607c0c39bd。
Synced/Progressing 後 rollout status 成功；第一次 HTTP smoke 全通過。

## drift 與手動修正

直接修改 live Deployment，Git 保留 replicas=2：

```bash
kubectl scale deployment fabflow-gitops-api -n fabflow-gitops --replicas=1
```

使用者查詢 replicas=1 ready=1，Application OutOfSync/Healthy。
這顯示健康工作負載仍可能偏離 Git；此為刻意製造的 live drift。
再次提交上述 b05f423 的同步 operation，結果 replicas=2 ready=2、Succeeded、
Synced/Healthy。這是手動 drift 修正，不是自動 self-heal 驗收。

## 以 Git revert 回復版本

確認工作目錄乾淨，b05f423 僅一個檔案的 API tag 變更後：

```bash
git revert --no-edit b05f423
git show --oneline HEAD -- deployments/helm/fabflow/values-kind.yaml
git push origin main
```

產生回復提交 12477cc672179bc12dd9abf3d842f18f42b1bbd3，將 Git API tag 恢復為
794dbaafc1697a8812358b30b0808c6100242ebe。使用者確認 push；助理後續本機查詢
確認 main/origin/main 同步位於此 commit。未獨立查詢本課遠端 CI 狀態。

刷新後 Application 顯示 12477cc…、OutOfSync/Healthy，再同步明確回復 commit：

```bash
kubectl patch application fabflow-gitops -n argocd --type merge \
  -p '{"operation":{"initiatedBy":{"username":"kubectl-manual"},"sync":{"revision":"12477cc672179bc12dd9abf3d842f18f42b1bbd3","prune":false}}}'
kubectl rollout status deployment/fabflow-gitops-api -n fabflow-gitops --timeout=60s
```

結果 Succeeded、syncResult.revision=12477cc…、API tag 恢復 794dbaa…。
rollout 成功後 Argo CD 曾短暫 Progressing，後續使用者輸出確認：
API 2/2、Dashboard 1/1、PostgreSQL 1/1、Synced/Healthy。

本次回復同時修改 Git desired state，再同步至 live；若只改 live 而 Git 不改，
下次同步仍會套用 Git 中的版本。本課未使用 Helm rollback 管理 GitOps 環境。

## 最後 HTTP 回歸

```bash
kubectl exec -i -n fabflow-gitops deployment/fabflow-gitops-dashboard -- \
  python - < scripts/smoke_containers.py
```

使用者完整輸出：baseline finish=175、cycle=70.5、transport_jobs=0；
AMHS finish=203、cycle=142.75、transport_jobs=40。
最後 Dashboard health/HTML、API readiness、兩情境 create/query/metrics/events 全 PASS。

## Argo CD 異常證據與限制

課程中 Server 反覆拒絕 8080 連線。describe 顯示前次 Completed/exit 0，
同時有 liveness 失敗後 Killing 事件；exit 0 不能排除探針觸發終止。
後續 Server restart count 增為 2，notifications 為 2；repo-server 曾 0/1、零重啟。
repo-server 有 HTTP readiness/liveness 逾時，但日誌 GenerateManifest 與後續 gRPC
health checks 回傳 OK；不等於所有 HTTP 探針當時正常。後續七個元件均恢復 Ready。
節點當時 Ready，仍不能判定間歇拒絕連線/探針逾時的根因。
未修改探針、刪 Pod 或重啟 Docker 作為本課恢復手段。

沒有持續 HTTP/效能量測、沒有證明零停機，沒有完整舊結果跨更新快照比對。
本課並未獨立驗證原兩個 namespace 在異常期間的可用性。
未新增/刪除 PVC，未測 prune、DB schema 回復、auto sync 或自動 self-heal。

進度同步 25/30（約 83.3%），實際時數空白。Day 25 文件尚待提交/CI；
僅整理紀錄，未重跑本機 Pytest。下一課 Day 26：整理量測與架構文件，尚未開始。
