# Day 4：部署 API

狀態：核心驗收已完成（依使用者提供的終端輸出與 Swagger 截圖）。預估 3 小時；實際時數待填。
依據根目錄 Kubernetes 30 天進度表；Day 1–3 已完成。

## 目標與概念

今天將既有 API 映像部署到 `kind-fabflow`，透過 port-forward 存取 readiness
與 API 文件。Dashboard 留到 Day 5；probes、requests、limits 留到 Day 6。

- Deployment 宣告期望的 Pod 副本數，透過 ReplicaSet 維持 Pod。
- Service 透過 selector 找到 Pod，提供固定的叢集內入口。
- `containerPort` 描述容器的服務埠，不會發布 Mac 的 port。
- ClusterIP 供叢集內連線；本次用 port-forward 建立暫時的本機連線。
- API 結果在程序記憶體，因此保持單副本、單 worker。更新策略使用 Recreate，
  避免更新時新舊 API Pod 同時提供各自獨立的結果；更新會中斷服務且遺失結果。

部署檔：[api.yaml](../../deployments/k8s/api.yaml)。

## 1. 確認環境

從 repository root 執行：

```bash
docker context show
kind get clusters
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow get namespace fabflow
```

預期 Docker 為先前使用的 desktop-linux，fabflow cluster 存在、節點 Ready，
namespace fabflow 存在。若不符合，先依 Day 3 筆記恢復環境。

## 2. 建置並載入映像

```bash
docker build --target api -t fabflow-api:day4 .
kind load docker-image fabflow-api:day4 --name fabflow
```

`--target api` 選擇 Dockerfile 的 API 階段，沿用其中單 worker 啟動命令。
Docker 的映像儲存區與 kind 節點內的儲存區不同，因此建置後需要 load。
部署檔指定 `IfNotPresent`，優先使用已載入的映像。
參考：[kind 載入映像](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster)。

## 3. 閱讀並套用部署檔

對照 YAML 找出 replicas、image、matchLabels、Pod labels、Service selector，
以及 Service port 與 targetPort 的對應，再執行：

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/api --timeout=120s
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api
```

預期 Deployment 為 1/1、一個 API Pod Running、Service 類型 ClusterIP，
EndpointSlice 有 Pod IP。目前未設定 readiness probe，Pod Ready 並不代表
`/health/ready` 已被 Kubernetes 檢查；下一步自行呼叫驗證。

## 4. Port-forward 與 HTTP 驗收

終端 A 執行並保持開啟；本機使用 18000，避開 Compose 的 8000：

```bash
kubectl --context kind-fabflow -n fabflow port-forward service/api 18000:8000
```

終端 B 執行：

```bash
curl --fail-with-body http://127.0.0.1:18000/health/ready
curl --fail-with-body http://127.0.0.1:18000/openapi.json
```

預期 readiness 為 `{"status":"ready"}`，OpenAPI 回傳 JSON。
瀏覽器開啟 `http://127.0.0.1:18000/docs`，應看到 API 文件與 runs 路由。
port-forward 使用 Service 選取 Pod，並不能證明 ClusterIP 的封包路徑或 Service DNS
已通過驗收；Day 5 再從 Dashboard 驗證叢集內服務連線。
參考：[kubectl port-forward](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/)。

## 排錯與收尾

```bash
kubectl --context kind-fabflow -n fabflow describe deployment api
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-api
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=100
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
```

ImagePullBackOff 時確認 image tag 與 load 的 cluster 名稱；CrashLoopBackOff 時讀 logs；
Service 找不到 Pod 時對照 selector 與 labels。若本機 port 已占用，改用 18001:8000。
重新建置時建議換新 tag，同時更新 YAML 並重新 load、apply，避免沿用節點快取。

完成後在終端 A 按 Ctrl+C 停止 port-forward，保留 Deployment 與 Service 接續 Day 5。
Pod 被替換後若需繼續連線，重新執行 port-forward。

## 驗收紀錄

| 項目 | 結果 |
| --- | --- |
| API build、kind load | build 成功；最初建為 day，後續 Deployment 使用 day4 並成功啟動；未另提供 load 成功輸出 |
| Deployment、Pod、Service | rollout 成功；Deployment 1/1；api-747d5d89c5-6h6jp Running、重啟 0 次，IP 10.244.0.6；Service ClusterIP 10.96.124.176:8000 |
| EndpointSlice | 未另提供查詢輸出 |
| readiness、API 文件 | port-forward 18000 → 8000 成功；curl 回傳 {"status":"ready"}；截圖顯示 Swagger runs 與 health 路由；未另提供直接查詢 openapi.json 輸出 |
| 問題與處理 | image not present locally：build tag day 與預期 day4 不一致，提供 docker tag 修正；部署路徑誤輸入 deployment/k8s/api/yaml，改為 deployments/k8s/api.yaml 後成功 |
| 實際時數 | 待填 |

能解釋「Docker build 後為何還要 kind load」、「Service 如何找到 Pod」、
「18000、Service 8000、容器 8000 的關係」後，再整理完成紀錄。

本次紀錄依據為使用者提供的輸出與截圖，助理未重新執行 cluster 操作。
進度表 Day 4 標示已完成；保留單副本 API，下一課部署 Dashboard 並驗證 Service DNS。

## 逐步操作與原理筆記

本次學習日期：2026-10-30。進度表 Day 4 的原規劃日期為 2026-11-01，
以實際學習順序完成，未修改原排程日期。

### 環境、映像與執行位置

```text
程式碼 + Dockerfile
        ↓ docker build --target api
Mac Docker 環境中的 fabflow-api:day4
        ↓ kind load docker-image --name fabflow
kind 節點中的映像
        ↓ Deployment → ReplicaSet → Pod
API 容器執行 Uvicorn，監聽 8000
```

`kubectl --context kind-fabflow get nodes` 明確選擇 cluster，避免操作到既有的
`yunikorn-dev`。Context 組合 cluster 連線設定、身分與預設 namespace；
`-n fabflow` 則明確指定本次資源的 namespace。節點 Ready 表示節點回報可用，
不代表 FabFlow API 已完成 HTTP 驗收。本次節點為單節點 control-plane，亦承載 API Pod。

`docker build --target api -t fabflow-api:day4 .`：

- `--target api` 選擇多階段 Dockerfile 的 api 階段，不建置 dashboard 階段。
- `-t` 設定映像名稱與 tag；tag 必須與 load 指令、Deployment 的 image 一致。
- `.` 是 build context，COPY 來源來自此範圍，所以從 repository root 執行。
- 輸出的 CACHED 表示重用符合快取條件的建置層，不需再次安裝套件。

Dockerfile 使用 Python 3.12 slim、設定 `/opt/fabflow` 工作目錄、複製 app 與 simulator，
再以 `pip install .` 安裝專案依賴，最後由一般使用者 fabflow 執行。
容器使用映像預設 CMD 啟動 `uvicorn app.main:app`；`0.0.0.0` 讓它監聽容器所有網路介面，
8000 為監聽埠，workers 1 表示一個 API worker。EXPOSE 是埠的描述，不會發布 Mac 的埠。

`kind load` 將映像載入 kind 節點的映像儲存區。Mac Docker 已有映像，不代表節點的
container runtime 也有。`--name fabflow` 是 kind cluster 名稱，kubectl context 則是
`kind-fabflow`。`IfNotPresent` 讓節點在已有指定映像時直接使用，缺少時才嘗試拉取。

### Deployment、ReplicaSet 與 Pod

Deployment 的 `apiVersion: apps/v1` 與 `kind: Deployment` 指定資源種類，
metadata 的 name 與 namespace 指定名稱和資源範圍。
`replicas: 1` 是期望副本數；Deployment 透過 ReplicaSet 維持 Pod 數量。
與 Day 3 的獨立 Pod 不同，受此控制器管理的 Pod 被刪除後會建立替代 Pod。
替代 Pod 不會恢復舊程序的記憶體結果。

`spec.template` 是 Pod 範本，內含 labels 與 containers；Deployment 的
`selector.matchLabels` 必須符合範本 labels。容器 image 指向 fabflow-api:day4，
未覆寫 command，因此沿用 Dockerfile CMD。`containerPort: 8000` 為埠的描述，
真正開始監聽的是 Uvicorn；`name: http` 讓 Service 可用名稱引用此埠。

更新策略 Recreate 先停止舊 Pod，再啟動新版，期間會中斷服務。
本次維持單 Pod、單 worker，避免不同 API 程序各自保存結果造成跨程序查詢 404；
這個設定仍無法讓結果在重啟後保留。

### Service 如何找到 API

Service 不是記錄 API Node 的位置，而是透過 selector 選擇 Pod：

```yaml
# API Pod 的標記
labels:
  app: fabflow-api

# Service 的選擇條件
selector:
  app: fabflow-api
```

Kubernetes 將符合條件的 Pod 位址、埠與就緒狀態維護在 EndpointSlice。
Pod 被替換、IP 改變後，只要 label 符合條件，Service 的後端就能更新。
本次 Pod IP 為 10.244.0.6；Service IP 為 10.96.124.176，在該 Service 存續期間維持穩定。
這些是本次分配結果，重建環境時不應寫死。

Service 的 `port: 8000` 是服務入口埠；`targetPort: http` 引用 Pod 中名為 http
的容器埠，也就是 8000。ClusterIP 提供叢集內入口，因此 EXTERNAL-IP 顯示 none 是正常的。

### Apply 與狀態檢查

`kubectl apply -f deployments/k8s/api.yaml` 將 YAML 宣告送到 API server。
檔案以 `---` 分隔兩份資源，因此一次建立 Deployment 與 Service。
created 只表示資源建立成功，還要等待控制器建立 Pod、容器啟動。

`rollout status deployment/api --timeout=120s` 等待這次部署完成，最多 120 秒。
`get deployments,pods,services -o wide` 同時查看三種資源，wide 額外顯示 IP、節點等資訊。

| 欄位 | 本次結果與含義 |
| --- | --- |
| Deployment READY | 1/1，期望一個副本，目前一個就緒 |
| UP-TO-DATE | 1，一個副本使用目前的 Pod 範本 |
| AVAILABLE | 1，一個副本符合可用條件 |
| Pod STATUS | Running；仍須額外確認應用程式 HTTP 行為 |
| Pod READY | 1/1，一個容器被判定就緒；目前未配置 readiness probe |
| RESTARTS | 0，此 Pod 的容器尚未重啟 |

### Port-forward 與 HTTP 驗收的意義

`port-forward service/api 18000:8000` 的順序是本機埠:Service 埠。
kubectl 依 Service 選到 Pod，透過 Kubernetes 的轉送通道連到該 Pod。
這與叢集內客戶端直接連線 ClusterIP 的路徑不同。

本機的 `127.0.0.1:18000` 與 `[::1]:18000` 分別是 IPv4、IPv6 回送位址。
Handling connection 表示有連線進入轉送埠，不是錯誤。
終端需持續執行；Ctrl+C 只停止轉送，不會刪除 Kubernetes 資源。

瀏覽器 `/docs` 成功載入 Swagger，確認文件可存取；curl `/health/ready` 回傳 ready，
確認應用程式生命週期就緒、RunService 存在，沒有額外執行模擬。
curl 輸出最後的 `%` 為終端對未以換行結尾的輸出所顯示的提示，不屬於 JSON。
尚未設定 probe，所以這次 readiness 是手動呼叫，不是 Kubernetes 定期檢查。

### 本次排錯與理解確認

1. `image not present locally`：建置 tag 為 day，預期為 day4。
   提供 `docker tag fabflow-api:day fabflow-api:day4`，為同一映像增加名稱，不需重新建置。
2. YAML 路徑不存在：誤寫 deployment/k8s/api/yaml；正確為 deployments/k8s/api.yaml。
3. 使用者已能說明 kind load 複製映像，讓節點使用；補充兩個映像儲存區不同。
4. 將「Service 記錄 API Node 位置」修正為 selector 配對 Pod labels，
   由 EndpointSlice 維護後端位址。修正後尚未再次以問答確認。

Day 5 接續建立 Dashboard Deployment、Service、ConfigMap，設定 FABFLOW_API_URL，
從 Dashboard 完成模擬與 KPI 查詢並驗證 Service DNS。
