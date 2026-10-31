# Day 5：部署 Dashboard 與服務連線

狀態：已完成（依使用者提供的終端輸出、UI 操作確認及 Service DNS 問答）。預估 3 小時，實際時數待填。
依據 Kubernetes 30 天進度表 Day 5；Day 4 API 核心驗收已完成。

## 目標與連線路徑

建立 Dashboard Deployment、ClusterIP Service、ConfigMap，從 UI 完成模擬與 KPI 查詢，
並能解釋 Service DNS。沿用單副本 API；probes、requests、limits 留到 Day 6。

```text
Mac 瀏覽器 http://127.0.0.1:18501
          ↓ kubectl port-forward
Dashboard Pod：Streamlit 8501
          ↓ Python HTTP 請求 http://api:8000
API Service → API Pod：Uvicorn 8000
          ↓
同步模擬與記憶體結果
```

瀏覽器只需連 Dashboard；API 請求由 Dashboard 的 Python 程序送出，
因此 FABFLOW_API_URL 必須是 Dashboard Pod 可到達的位址。
`localhost` 在 Dashboard Pod 中代表該 Pod，不是 API Pod 或 Mac。

## 1. 確認既有 API

從 repository root 執行：

```bash
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
```

預期節點 Ready、api Deployment 1/1、Pod Running、api Service 存在。
若尚未部署，依 Day 4 筆記完成。今天不需要保留 Day 4 的 API port-forward。

## 2. 建置與載入 Dashboard 映像

```bash
docker build --target dashboard -t fabflow-dashboard:day5 .
kind load docker-image fabflow-dashboard:day5 --name fabflow
```

target dashboard 會安裝 dashboard 額外套件，包含 Streamlit 與 httpx，
沿用 Dockerfile 的 Streamlit 啟動命令，監聽 0.0.0.0:8501。
build、load、YAML 的映像名稱與 tag 必須完全一致。

## 3. 閱讀與套用三種資源

部署檔：[dashboard.yaml](../../deployments/k8s/dashboard.yaml)。

| 資源 | 本次用途 |
| --- | --- |
| ConfigMap dashboard-config | 保存非機密設定 FABFLOW_API_URL=http://api:8000 |
| Deployment dashboard | 建立帶有環境變數的 Dashboard Pod |
| Service dashboard | 透過 app=fabflow-dashboard 選取 Pod，提供 8501 入口 |

Deployment 的 env.valueFrom.configMapKeyRef 以名稱與 key 讀取同 namespace 的 ConfigMap。
Dashboard 從環境變數取得 UI 的預設 API URL。修改 ConfigMap 後，既有程序的環境變數
不會自動更新；需要重新建立 Pod，例如 rollout restart deployment/dashboard，
並在新瀏覽器 session 確認預設設定。
參考：[ConfigMap 環境變數](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-configmap/)。

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=120s
kubectl --context kind-fabflow -n fabflow get deployments,pods,services,configmaps
```

預期 dashboard 1/1、Pod Running、Service 為 ClusterIP。Kubernetes 沒有套用 Compose 的
depends_on；rollout 成功也不代表 API 連線成功，下一步另外驗證。

## 4. 從 Dashboard Pod 驗證 DNS、設定與 API

```bash
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,socket,urllib.request; url=os.environ["FABFLOW_API_URL"]; print("API URL:",url); print("api DNS:",socket.gethostbyname("api")); print(urllib.request.urlopen(url+"/health/ready",timeout=5).read().decode())'
```

預期 API URL 為 http://api:8000，api DNS 解析成 API Service ClusterIP，
HTTP 回傳 {"status":"ready"}。這次請求從 Dashboard Pod 出發，驗證了叢集內的連線。
同 namespace 可用 Service 短名稱 api；跨 namespace 可使用 api.fabflow。
名稱中的 api 指向 Service，不是 Deployment 名稱、Pod 名稱或 Node 名稱。

## 5. 開啟 Dashboard 與完整 UI 驗收

終端 A 保持執行：

```bash
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

瀏覽器開啟 http://127.0.0.1:18501，避開 Compose 可能占用的 8501。

1. 確認 API base URL 預設為 http://api:8000，按 Check connection，看到 API ready。
2. 選 Three-stage baseline、FIFO、aging 60，按 Run simulation，記錄 run ID。
3. 按 Load KPIs，比對下表；再按 Refresh KPIs 確認重新查詢成功。
4. 換 AMHS bottleneck，以相同 policy、aging 重做，記錄 run ID 與 KPI。
5. 可將含情境、run ID 與結果的截圖保存到 artifacts/k8s/day05/。

| 情境 | 完成 lots | finish（分鐘） | 平均 cycle（分鐘） | transport jobs |
| --- | ---: | ---: | ---: | ---: |
| Three-stage baseline | 20 | 175 | 70.50 | 0 |
| AMHS bottleneck | 20 | 203 | 142.75 | 40 |

以上為驗收比對值；使用者已依上述流程確認兩種情境成功，證據範圍見驗收紀錄。
結果仍存 API 記憶體；Refresh 會再次查 API，API 重啟後舊 run 可能 404。

## 排錯與收尾

```bash
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-dashboard
kubectl --context kind-fabflow -n fabflow logs deployment/dashboard --tail=100
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=100
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api
kubectl --context kind-fabflow -n fabflow get configmap dashboard-config -o yaml
```

映像錯誤先對照 tag 與 kind load；設定錯誤檢查 ConfigMap 引用；API 連不上先檢查
API Pod、Service selector、EndpointSlice，再檢查 DNS。既有 UI 手動改過 URL 時，
先將欄位改回 http://api:8000。完成後 Ctrl+C 停止 port-forward，保留兩個服務接續 Day 6。

## 驗收紀錄

| 項目 | 結果 |
| --- | --- |
| build、load、Dashboard rollout | fabflow-dashboard:day5 build 完成；kind load 正常結束；rollout 成功，Dashboard 1/1，Pod dashboard-78f4745f-5jdlh Running、重啟 0 次 |
| ConfigMap 環境變數、DNS、Pod 內 readiness | API URL: http://api:8000；api DNS: 10.96.124.176；回傳 {"status":"ready"} |
| UI 連線、兩種情境、KPI load/refresh | 使用者確認 baseline 全流程成功，接著確認 AMHS 驗收成功；依上述步驟比對預期值與 refresh |
| run ID、截圖、問題、實際時數 | 未提供 run ID 或截圖；未回報錯誤；實際時數待填 |

理解確認：為什麼 Dashboard 的 API URL 使用 api:8000，而瀏覽器開啟 localhost:18501？

### 本次驗收依據

使用者提供兩個 Deployment 1/1、兩個 Pod Running 且重啟 0 次，
API Service 10.96.124.176:8000、Dashboard Service 10.96.66.94:8501，
以及 dashboard-config DATA 1 的輸出。上述 IP 為本次分配，不應寫死到設定。
Pod 內驗證輸出如下：

```text
API URL: http://api:8000
api DNS: 10.96.124.176
{"status":"ready"}
```

UI 結果依使用者確認記錄，助理未自行操作瀏覽器，也未另存 run ID 或截圖。
使用者以「直接指向 api 服務」說明 API URL 的用途，已確認 Service DNS 概念。
補充：api 是同 namespace 的 Service DNS 名稱；Dashboard Pod 中的 localhost 指向
Dashboard Pod 自己，並非 API Pod。Day 5 已完成。
下一課 Day 6 加入 probes、requests 與 limits。

## 操作原理與學習整理

### 為什麼設定與映像分開

Dockerfile 的 dashboard 階段安裝 `.[dashboard]`，映像包含程式、Streamlit 與 httpx。
ConfigMap 保存部署時決定的 API 位址，因此同一映像可搭配不同環境的設定使用。
本次 build 顯示 CACHED，表示 Docker 重用既有建置層；kind load 顯示
not yet present / loading，代表節點尚未有該映像，正在載入，並不是失敗訊息。

`configMapKeyRef.name` 指定 dashboard-config，key 指定 FABFLOW_API_URL；
容器中的環境變數使用同名 FABFLOW_API_URL。dashboard-config 的 DATA 1 表示一個設定鍵，
不代表一個 Pod。此次未修改 API 程式碼或映像。

### 三個連線位址的角色

| 位址 | 使用者／程序 | 用途 |
| --- | --- | --- |
| 127.0.0.1:18501 | Mac 瀏覽器 | 經 port-forward 開啟 Dashboard |
| Dashboard Pod:8501 | Streamlit 程序 | 接收 Dashboard 網頁連線 |
| api:8000 | Dashboard 的 Python 程序 | 經 API Service 呼叫 FastAPI |

18501 是本機轉送埠，8501 是 Dashboard Service 與容器埠，8000 是 API Service 與容器埠。
同 namespace 的 api 短名稱由叢集 DNS 解析成本次 Service IP 10.96.124.176。
DNS 解析名稱，Service selector 選取帶有 app=fabflow-api 的 Pod，兩者責任不同。

### 為什麼從 Pod 內檢查

`kubectl exec deployment/dashboard -- python -c '...'` 在 Dashboard 容器內啟動額外的
Python 程序，不會停止原本的 Streamlit。它依序驗證環境變數、DNS、HTTP readiness，
可區分設定未注入、名稱無法解析，以及 API 無法連線等問題。
這次驗證不依賴 Mac 上的 API port-forward，實際使用了叢集內服務連線。

Deployment rollout 成功只表示部署達到完成條件；本次尚未設定 probes，
仍需 Pod 內 HTTP 檢查與 UI 操作，才能確認應用程式間的流程。

### UI 驗收驗證了什麼

Check connection 呼叫 API readiness。Run simulation 送出 POST，等待同步模擬完成後
取得 run ID；Load KPIs 與 Refresh KPIs 用 run ID 發送 GET，查詢已保存結果，
不會再次執行模擬。兩種情境的 KPI 比對確認了 Dashboard → Service → API 的操作流程。
結果仍在 API 記憶體，Dashboard 能顯示已載入資料不代表 API 重啟後仍能重新查詢。

### 收尾與後續

本次沒有回報操作錯誤。停止 port-forward 不會刪除 Dashboard、API 或 ConfigMap；
尚未收到停止指令的執行確認。保留 cluster 與部署，Day 6 加入健康檢查及資源設定。
實際時數、run ID 與截圖沒有提供，不補填或宣稱已保存。
