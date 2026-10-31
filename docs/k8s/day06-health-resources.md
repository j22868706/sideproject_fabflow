# Day 6：健康檢查與資源設定

狀態：已完成核心驗收（依使用者提供的終端輸出、UI 確認與觀念問答）。預估 2 小時；實際時數待填。
依據 Kubernetes 30 天進度表 Day 6；Day 5 已完成。

## 今天的變更

在 API 與 Dashboard 的容器設定加入 startup、readiness、liveness probes，
以及 CPU／記憶體 requests、limits。沿用 day4、day5 映像，不需重新 build 或 kind load。

更新 Pod template 會替換 Pod。API 使用 Recreate，會短暫中斷服務，原有記憶體結果遺失；
驗收時建立新的 run。Dashboard Pod 替換也可能中斷既有瀏覽器 session，
舊 port-forward 可能需要重新執行。

## 1. 套用前確認

```bash
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
```

預期節點 Ready，API 與 Dashboard 都為 1/1。先確認目前狀態再套用變更。

## 2. 理解健康檢查

HTTP probe 由節點的 kubelet 對 Pod IP 與指定埠發出請求，不依賴 Mac port-forward。

| Probe | 成功時 | 持續失敗達門檻時 |
| --- | --- | --- |
| startup | 開始執行 readiness、liveness | 觸發容器重啟 |
| readiness | Pod 可被標示 Ready，成為一般 Service 流量的後端 | Pod 不就緒，停止接收一般 Service 新流量；不因此重啟容器 |
| liveness | 繼續執行容器 | 觸發容器重啟；依重啟策略重新啟動 |

API startup、liveness 使用 `/health/live`，readiness 使用 `/health/ready`。
live 確認 API 能回應；ready 另外檢查應用生命週期與 RunService 是否存在，
不執行模擬，也不保證任何指定 run ID 仍存在。

Dashboard 三種 probe 使用 Streamlit 的 `/_stcore/health`，只檢查 Dashboard 本身。
API 連線失敗時 Dashboard 仍應能顯示錯誤，不應因 API 故障持續重啟。

本次設定：

| Probe | periodSeconds | timeoutSeconds | failureThreshold |
| --- | ---: | ---: | ---: |
| startup | 2 | 2 | 60 |
| readiness | 5 | 2 | 3 |
| liveness | 10 | 3 | 6 |

period 是探測間隔，timeout 是單次等待上限，failureThreshold 是連續失敗門檻。
startup 提供約 120 秒的啟動容忍窗口；實際觸發時間受排程與執行時間影響，
不能把間隔乘門檻當作精確倒數。未另外設定 successThreshold，使用預設 1。
startup 成功前不執行 readiness 與 liveness。

參考：[Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)。

## 3. 理解 requests 與 limits

| 容器 | CPU request | CPU limit | Memory request | Memory limit |
| --- | --- | --- | --- | --- |
| API | 100m | 1000m | 128Mi | 512Mi |
| Dashboard | 100m | 1000m | 256Mi | 512Mi |

100m 是 0.1 CPU，1000m 是 1 CPU；Mi 為二進位記憶體單位，128Mi 為 128 × 2^20 bytes。
requests 用於排程判斷節點是否有足夠可分配資源，不是程式當下的實際用量。
CPU request 也影響資源競爭時的 CPU 權重。CPU 超過 limit 會受到節流，
不是一超過就被終止；記憶體超限可能造成 OOM kill。

這些數值是本機教學起始設定，尚未以負載測試量測調校。兩個服務的 requests
合計 200m CPU、384Mi 記憶體；仍需容納 cluster 元件及其他工作負載。
API 結果無持久化且持續累積在記憶體，設定 limit 不會自動清理結果。
若出現 OOMKilled 或探測超時，先讀 events、logs 與終止原因再決定調整。

參考：[Kubernetes 資源管理](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)。

## 4. 套用變更與檢查

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/api --timeout=180s
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow get deployments,pods -o wide
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-api
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-dashboard
```

預期兩個 Deployment 1/1，新 Pod Running、Ready，describe 可看到三種 probes 與
requests／limits，沒有持續重啟。初始短暫未就緒應觀察後續是否恢復，不能只憑單次事件判定失敗。

## 5. 驗證 Service 與 UI

```bash
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api -o yaml
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=dashboard -o yaml
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode()); print(urllib.request.urlopen("http://127.0.0.1:8501/_stcore/health",timeout=5).read().decode())'
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

確認 EndpointSlice 的目前 Pod endpoint 為 ready: true、HTTP 分別回傳 ready 與 ok。
開啟 http://127.0.0.1:18501，Check connection，重新建立 baseline（FIFO、aging 60），
Load KPIs、Refresh KPIs；預期 20 lots、finish 175、平均 cycle 70.50 分鐘。
另外在另一終端重新 get pods，確認操作期間沒有新增重啟。

## 排錯與收尾

```bash
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=100
kubectl --context kind-fabflow -n fabflow logs deployment/dashboard --tail=100
```

若 Pending，describe 檢查是否 Insufficient cpu／memory；若探測失敗，核對 path、port、
容器 logs；若曾重啟，使用實際 Pod 名稱的 `logs POD_NAME --previous` 檢查上一個容器輸出，
並查看 describe 的 Last State、Reason。不要把 readiness 失敗誤認成自動重啟。
本日不刻意製造故障；故障演練留到 Day 7。

完成後 Ctrl+C 停止轉送，保留部署。理解確認：readiness 與 liveness 持續失敗，
分別對 Service 流量與容器造成什麼影響？requests 與 limits 的差別是什麼？

## 驗收紀錄

| 項目 | 結果 |
| --- | --- |
| 套用、rollout、新 Pod Ready | API、Dashboard rollout 成功；api-9fcdd7f99-fffb6（10.244.0.8）、dashboard-5b6b6bc85c-kt5rk（10.244.0.9）均 1/1 Running |
| describe：probes、requests、limits | 兩個容器的三種 probes、CPU／記憶體 requests／limits 均符合本文件；Ready True；Events 全為 Normal；QoS Burstable |
| EndpointSlice | 尚未提供查詢輸出，不宣稱完成此項直接檢查 |
| HTTP、UI、重啟次數 | Pod 內回傳 {"status":"ready"} 與 ok；使用者確認 Check connection、新 baseline、KPI load/refresh 全成功；後續 get pods 顯示兩個 Pod 重啟皆為 0 |
| 觀念問答 | 使用者正確說明 readiness 停止一般 Service 流量、liveness 觸發重啟，以及 requests 為需求、limits 為上限 |
| 問題、實際時數 | 未回報錯誤；實際時數待填 |

## 本次觀察與理解確認

本次實機操作日期：2026-10-30（依提供的 Pod Start Time，時區 -0500）。
API 與 Dashboard 的映像仍為 day4、day5，無需重新建置；改變 Pod template 後，
Pod 名稱與 IP 更新，而 Service 維持原入口。兩次 describe 皆顯示映像已存在節點，
排程、容器建立與啟動為 Normal。CPU limit 顯示 1，等同 YAML 的 1000m。

兩個 Pod 的 QoS Class 為 Burstable，這與本次 requests 與 limits 不相等的設定一致。
UI 驗收後 API Pod AGE 3m30s、Dashboard AGE 2m34s，兩者均 Ready、重啟 0 次。
此紀錄確認本次觀察期間正常，並非長期穩定性或負載測試結論。

觀念問答已確認：

- Readiness 連續失敗達門檻，Pod 變成不就緒，停止接收一般 Service 新流量，
  不因此重啟。Liveness 連續失敗達門檻，觸發容器重啟。
- Requests 是排程用的資源需求值，不代表當下實際用量；limits 是執行上限。
  CPU 超限受到節流，記憶體超限可能造成 OOM 終止。

驗收依據為使用者貼出的輸出與 UI 操作確認，助理未重新操作 cluster 或瀏覽器。
未提供 EndpointSlice 輸出、run ID、截圖及停止 port-forward 的確認。
進度表 Day 6 已完成；下一課 Day 7 練習 Kubernetes 故障排查，保存症狀、根因與修復步驟。
