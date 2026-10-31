# Day 8：Namespace 重建與記憶體結果驗證

狀態：核心操作驗收已完成（依使用者提供的終端輸出與 UI 確認）。
實際時數待填。使用者已回答 Service 連線觀念，DNS 與 label selector 的分工已補充說明。

## 目標與範圍

刪除並重建 kind-fabflow 的 fabflow namespace，從 repository YAML 恢復
API 與 Dashboard，驗證舊 API 記憶體結果遺失，以及新模擬可正常執行。
本次保留 kind cluster 與節點內映像，不是從空白節點重建映像的演練。

## 重建前

助理唯讀查詢確認 fabflow-control-plane 為 Ready，API、Dashboard Deployment
皆 1/1，Pod Running、重啟 0。使用者透過 Dashboard 執行 baseline、FIFO、
aging 60，確認 20 lots、finish 175 分鐘、平均 cycle 70.50 分鐘。

舊 run ID：`70a9bf85-0d8a-47d4-90ca-c12f628ea443`。

## 重建步驟

先停止舊 port-forward，再依序執行：

```bash
kubectl --context kind-fabflow delete namespace fabflow --wait=true --timeout=180s
kubectl --context kind-fabflow create namespace fabflow
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/api --timeout=180s
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
```

刪除 namespace 會移除其中所有資源與 API 程序中的結果。
本次既有映像 fabflow-api:day4、fabflow-dashboard:day5 仍在 kind 節點內，
未要求重新 build 或 load。使用者提供的重建後輸出：

| 資源 | 結果 |
| --- | --- |
| API Deployment | 1/1，映像 fabflow-api:day4 |
| Dashboard Deployment | 1/1，映像 fabflow-dashboard:day5 |
| API Pod | api-9fcdd7f99-xl2j2，10.244.0.13，1/1 Running，重啟 0 |
| Dashboard Pod | dashboard-5b6b6bc85c-4f5bd，10.244.0.14，1/1 Running，重啟 0 |
| API Service | ClusterIP 10.96.14.134，8000/TCP |
| Dashboard Service | ClusterIP 10.96.112.81，8501/TCP |

## 驗證服務恢復與舊結果遺失

從 Dashboard Pod 使用 FABFLOW_API_URL 呼叫 API。
使用者提供的實際輸出：

```text
/health/ready 200 {"status":"ready"}
/api/v1/runs/70a9bf85-0d8a-47d4-90ca-c12f628ea443 404 {"detail":"Run not found"}
```

Readiness 成功與舊 run 不存在可同時成立。應用已恢復，但結果只存在舊 API
程序記憶體，YAML 重建不會還原它們；本次未加入持久化儲存。

## 新模擬與最後驗收

重新啟動 Dashboard port-forward：

```bash
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

使用者確認 Check connection、新 baseline（FIFO、aging 60）、Load KPIs、
Refresh KPIs 均成功；20 lots、finish 175、平均 cycle 70.50 符合預期。
新 run ID：`3a948935-c040-4404-96af-4fa075395b5b`。
最後 get pods 顯示上述兩個新 Pod 皆 1/1 Running、重啟 0。
未提供截圖、實際時數或停止 port-forward 的確認。

## 觀念補充

使用者指出 Service 透過標籤選擇後端，不綁定特定 Pod ID；方向正確。
本專案的實際 selector 為 app=fabflow-api，不是 tag api。
Dashboard 使用的 api 是 Service 名稱：同 namespace 內的 DNS 將 api
解析到目前 API Service 的 ClusterIP。Service 再透過 label selector 與
EndpointSlice 找到可接收流量的 Pod。因此 Service 以相同名稱重建後，
即使 ClusterIP 改變，Dashboard 設定仍可保留 http://api:8000。

本次重建、HTTP 與 UI 驗收依使用者輸出與確認記錄；助理僅直接執行重建前的
唯讀狀態查詢，未另行操作 namespace 刪除、重建或瀏覽器。

## 後續現況與 Service 路徑查核（2026-10-31）

助理重新直接查詢 kind-fabflow，節點 Ready；API 與 Dashboard Deployment
皆 1/1，兩個 Pod 皆 Running、重啟 0，Pod 名稱與上述重建紀錄一致。
本次未修改叢集設定。

從 Dashboard Pod 執行 DNS 與 HTTP 查核，實際結果：

```text
FABFLOW_API_URL=http://api:8000
api DNS=10.96.14.134
readiness=200 {"status":"ready"}
```

同次 Service 與 EndpointSlice 查詢顯示：

```text
Service api: ClusterIP 10.96.14.134, selector app=fabflow-api
EndpointSlice api-cz4l9: 10.244.0.13:8000
API Pod api-9fcdd7f99-xl2j2: 10.244.0.13
```

這些結果驗證 Dashboard 使用的 api 名稱解析至 Service ClusterIP，
且 Service 的後端端點對應目前 API Pod。HTTP readiness 回傳成功。
本次未重新執行模擬或 UI 驗收。使用者後續回答固定 Service 名稱能避免追蹤
Pod IP；助理補充 DNS 解析 Service、selector 選取 Pod 的分工。

後續查到根目錄 `FabFlow_K8s_30天進度表.xlsx`：Day 9 為結果儲存介面與
PostgreSQL schema 設計，接續見 day09-storage-design.md。先前僅查 Markdown
而判斷未記載課程，已依原始進度表更正。
