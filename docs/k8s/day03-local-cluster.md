# Day 3：建立本機 Kubernetes 環境

狀態：核心驗收已完成（依使用者貼出的終端輸出）。預估 2 小時；實際時數待填。

目標：使用 kind 建立獨立的 FabFlow 學習 cluster，確認 kubectl context，建立
namespace，建立並刪除測試 Pod，留下重建方法。FabFlow API 部署留到 Day 4。

## 起始狀態

助理讀取本機工具：kind v0.33.0、kubectl client v1.36.1。
既有 kind cluster 為 `yunikorn-dev`；本課另用 `fabflow`，保留既有環境。
起始時尚未建立本課 cluster；後續驗收結果見下方。

## 概念

- kind 使用容器作為 Kubernetes 節點，適合本機練習。
- kubectl 是 Kubernetes API 的操作工具。
- kubectl context 組合 cluster、使用者與預設 namespace；它不同於 Docker context。
- Namespace 區分同一 cluster 內的資源；不代表獨立 cluster，也不自動隔離網路。
- 本課單節點同時執行控制平面與工作負載，不代表正式環境的高可用架構。

## 1. 建立與確認（教學時逐步執行）

先確認 Docker Desktop 已啟動，再執行：

```bash
kind version
kubectl version --client
kind get clusters
kind create cluster --name fabflow --wait 120s
kubectl config current-context
kubectl --context kind-fabflow cluster-info
kubectl --context kind-fabflow get nodes -o wide
```

預期 context 為 `kind-fabflow`，節點 `fabflow-control-plane` 為 Ready。
kind 建立環境後會設定 kubeconfig；以下指令明確指定 context，避免操作其他 cluster。
記錄 server 版本；kubectl 與 API server 的支援版本差距需依官方版本相容規則確認。

## 2. Namespace 與測試 Pod（待上一階段確認後執行）

```bash
kubectl --context kind-fabflow create namespace fabflow
kubectl --context kind-fabflow -n fabflow run day3-smoke --image=busybox:1.37.0 --restart=Never --command -- sleep 3600
kubectl --context kind-fabflow -n fabflow wait --for=condition=Ready pod/day3-smoke --timeout=120s
kubectl --context kind-fabflow -n fabflow get pods -o wide
kubectl --context kind-fabflow -n fabflow exec day3-smoke -- echo hello-fabflow
kubectl --context kind-fabflow -n fabflow delete pod day3-smoke
kubectl --context kind-fabflow -n fabflow get pods
```

預期 echo 輸出 hello-fabflow；刪除後 namespace 沒有 Pod。
這是直接建立的獨立 Pod，沒有 Deployment 管理，因此刪除後不會自動補上。
若等待失敗，使用同一 context／namespace 執行 `describe pod day3-smoke` 檢查事件。

## 重建參考

以下刪除會移除整個 fabflow 學習 cluster 與其中資源，僅於刻意練習重建時執行；
平常保留 cluster 銜接 Day 4。不要刪除既有的 yunikorn-dev。

```bash
kind delete cluster --name fabflow
kind create cluster --name fabflow --wait 120s
kubectl --context kind-fabflow create namespace fabflow
```

## 驗收紀錄

| 項目 | 結果 |
| --- | --- |
| Cluster 建立、節點版本 | kind-fabflow 已可查詢；節點 Kubernetes v1.37.0（未另提供 API server version 輸出） |
| Context、節點 Ready | current-context 為 kind-fabflow；fabflow-control-plane 為 Ready |
| Namespace 建立 | fabflow namespace 可成功建立、查詢與刪除測試 Pod |
| Pod Ready、exec 輸出 | day3-smoke：1/1 Running、重啟 0 次；exec 輸出 hello-fabflow |
| Pod 刪除後沒有自動補上 | 刪除成功；緊接查詢顯示 No resources found in fabflow namespace. |
| 問題與處理、實際時數 | 本段操作未回報錯誤；實際時數待填 |

參考：[kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/)、
[kubectl context 與 kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)。

## 本次觀察與學習重點

使用者提供的節點輸出：IP 172.18.0.3、角色 control-plane、OS Debian GNU/Linux 13、
container runtime containerd://2.3.4。測試 Pod IP 為 10.244.0.5，位於
fabflow-control-plane；節點 IP 與 Pod IP 屬於不同網路層級。

使用者提供的最終驗收輸出：

```text
hello-fabflow
pod "day3-smoke" deleted from fabflow namespace
No resources found in fabflow namespace.
```

`exec` 在既有容器中執行額外指令，`--` 分隔 kubectl 參數與容器命令。
本次使用獨立 Pod，沒有 Deployment 管理；刪除後沒有控制器補建。
`--restart=Never` 控制容器重啟策略，與 Deployment 是否建立替代 Pod 是不同機制。

重建指令已記錄，未實際刪除並重建 cluster；保留環境銜接 Day 4。
驗收依據為使用者在教學對話提供的輸出，助理未重新執行或另存終端截圖。
