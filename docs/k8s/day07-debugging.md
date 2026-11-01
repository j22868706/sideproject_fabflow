# Day 7：Kubernetes 排錯練習

狀態：已完成（依使用者終端輸出、恢復確認、UI 驗收與觀念問答）。預估 3 小時；實際時數待填。
目標：保存至少兩種故障的症狀、根因、排查證據、修復步驟及恢復結果。
沿用 Day 6 健康檢查與資源設定，一次只改一項，恢復後才做下一項。

## 1. 確認正常基線

從 repository root 執行：

```bash
kubectl --context kind-fabflow get nodes
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode())'
```

預期節點 Ready，兩服務 1/1、Pod Running，HTTP 回傳 ready。
若不符合，先排除既有問題，不直接注入新故障。

## 2. 故障一：Service targetPort 錯誤

只修改 cluster 的 Service，保留 repo 的正確 YAML 作為還原依據。
此步驟會暫時中斷經 API Service 的請求，但不替換 API Pod。

```bash
kubectl --context kind-fabflow -n fabflow patch service api --type=json -p='[{"op":"replace","path":"/spec/ports/0/targetPort","value":9999}]'
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode())'
```

預期請求失敗，可能是拒絕連線或逾時，保留實際錯誤，不預先寫成固定訊息。

```bash
kubectl --context kind-fabflow -n fabflow get pods
kubectl --context kind-fabflow -n fabflow describe service api
kubectl --context kind-fabflow -n fabflow get endpointslices -l kubernetes.io/service-name=api -o yaml
kubectl --context kind-fabflow -n fabflow logs deployment/api --tail=50
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
kubectl --context kind-fabflow -n fabflow exec deployment/api -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=5).read().decode())'
```

對照：API 容器監聽 8000，Service 卻把流量送到 9999。
Pod 可保持 Ready，因為 kubelet probe 直接檢查 Pod 的 8000，不經 Service。
EndpointSlice 可出現 ready: true 但 port 為 9999；就緒不代表服務埠設定正確。
這是有效但錯誤的設定，不一定產生 Warning events；API logs 也可能只有正常探測。
Pod 內 localhost:8000 成功，有助於將問題定位到 Service 路徑。
不要靠 Service port-forward 驗證此故障，從另一個 Pod 發 HTTP 請求才能測到叢集內路徑。

還原並重測：

```bash
kubectl --context kind-fabflow apply -f deployments/k8s/api.yaml
kubectl --context kind-fabflow -n fabflow get service api -o yaml
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; print(urllib.request.urlopen(os.environ["FABFLOW_API_URL"]+"/health/ready",timeout=5).read().decode())'
```

確認 targetPort 回到 http，HTTP 恢復 ready，再繼續。
參考：[Debug Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)。

## 3. 故障二：Dashboard API URL 錯誤

將 Dashboard 環境變數暫時覆寫成 localhost:8000。程式會以此環境變數作為 UI 的預設 API URL，
並會替換 Dashboard Pod，瀏覽器 session 與 port-forward 可能中斷。
使用 set env 覆寫 Deployment，repo 與 ConfigMap 保持正確值，以便對照及還原。

```bash
kubectl --context kind-fabflow -n fabflow set env deployment/dashboard FABFLOW_API_URL=http://127.0.0.1:8000
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; url=os.environ["FABFLOW_API_URL"]; print("API URL:",url,flush=True); print(urllib.request.urlopen(url+"/health/ready",timeout=5).read().decode())'
```

預期 URL 顯示 localhost 位址、請求失敗，但 Dashboard Pod 仍能 Ready。
它的 probes 檢查 Streamlit 8501，不檢查 API 連線。

```bash
kubectl --context kind-fabflow -n fabflow get pods
kubectl --context kind-fabflow -n fabflow describe pods -l app=fabflow-dashboard
kubectl --context kind-fabflow -n fabflow get configmap dashboard-config -o yaml
kubectl --context kind-fabflow -n fabflow logs deployment/dashboard --tail=50
kubectl --context kind-fabflow -n fabflow get events --sort-by=.metadata.creationTimestamp
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import urllib.request; print(urllib.request.urlopen("http://api:8000/health/ready",timeout=5).read().decode())'
```

同 Pod 用正確的 api:8000 能連線，可定位為應用設定問題。
如需觀察 UI，重開 Dashboard port-forward 並使用新瀏覽器 session，確認 API base URL
為錯誤值，再按 Check connection。既有 session 的輸入可能保留舊值，因此容器環境變數
與直接 HTTP 檢查才是此練習的主要證據。UI 處理過的連線錯誤不一定出現在 logs。

還原 ConfigMap 引用與原部署設定。先移除 set env 加入的固定值，再 apply；
直接 apply 在本次實測遇到 value 與 valueFrom 衝突：

```bash
kubectl --context kind-fabflow -n fabflow set env deployment/dashboard FABFLOW_API_URL-
kubectl --context kind-fabflow apply -f deployments/k8s/dashboard.yaml
kubectl --context kind-fabflow -n fabflow rollout status deployment/dashboard --timeout=180s
kubectl --context kind-fabflow -n fabflow exec deployment/dashboard -- python -c 'import os,urllib.request; url=os.environ["FABFLOW_API_URL"]; print("API URL:",url); print(urllib.request.urlopen(url+"/health/ready",timeout=5).read().decode())'
```

預期 URL 恢復 http://api:8000，readiness 回傳 ready。

## 4. 最後恢復驗收

```bash
kubectl --context kind-fabflow -n fabflow get deployments,pods,services -o wide
kubectl --context kind-fabflow -n fabflow port-forward service/dashboard 18501:8501
```

重新開啟 http://127.0.0.1:18501，確認 API URL，Check connection，
建立新的 baseline（FIFO、aging 60），Load／Refresh KPIs。
預期 20 lots、finish 175、平均 cycle 70.50。完成後再 get pods 確認重啟次數。
Ctrl+C 停止轉送，保留部署，Day 8 從乾淨 namespace 重建與整理文件。

## 排錯順序與紀錄

先確認 context／namespace，再看症狀與受影響路徑，依 get、describe、logs、events
收集證據。一次改一項，比較故障前後；不要把「沒有 Warning」當成設定正確。
參考：[Debug Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/)。

| 項目 | 症狀／證據 | 根因 | 修復與恢復驗收 |
| --- | --- | --- | --- |
| 正常基線 | 使用者提供 readiness 回傳 ready | — | HTTP 基線正常；未另提供本次起始 get nodes／get deployments 輸出 |
| 故障一：Service port | Connection refused、退出碼 1；兩 Pod 1/1 Running、重啟 0；Service TargetPort 9999，Endpoints 10.244.0.8:9999，Events none | Service 目的埠與 API 監聽 8000 不符 | 使用者確認依指示還原後順利排錯；未另提供還原查詢原始輸出 |
| 故障二：API URL | 環境變數為 http://127.0.0.1:8000，Connection refused；同 Pod 呼叫 api:8000 則回 ready；Dashboard Ready、重啟 0 | localhost 指向 Dashboard Pod，API 位於另一 Pod | 先移除固定環境變數，再 apply 還原 ConfigMap 引用；使用者確認修復成功 |
| 最終 UI 與 Pod 狀態 | 使用者確認 Check connection、新 baseline、Load／Refresh KPIs 全成功 | — | api-9fcdd7f99-fffb6 與 dashboard-5b6b6bc85c-rxb7p 皆 1/1 Running、重啟 0 |

本次結果依使用者輸出與確認記錄；未提供 run ID、截圖或實際時數。
理解確認：Pod Ready 為什麼仍可能無法使用 Service？沒有 Warning events 能排除設定錯誤嗎？


## 實測補充：還原時的環境變數衝突

使用者直接 apply dashboard.yaml 時得到：

```text
The Deployment "dashboard" is invalid:
spec.template.spec.containers[0].env[0].valueFrom:
Invalid value: "": may not be specified when `value` is not empty
```

set env 將 Deployment 的環境變數改為固定 value；本次 client-side apply 的合併
沒有移除該值，新增 valueFrom 時違反同一變數不能同時使用兩者的規則。
這不是 API 或 DNS 故障，且被拒絕的 Deployment 更新未成功生效。
先執行 `set env deployment/dashboard FABFLOW_API_URL-`，再 apply 正確 YAML，
等待 rollout 並重新檢查 API URL 與 readiness。使用者確認排錯成功。
移除與重新套用可能造成短暫的中間 Pod，應等待最後 rollout，不使用中間狀態驗收。
原先直接 apply 的還原步驟已修正為上述流程。

## 證據與學習重點

故障一 describe 顯示 Service IP 10.96.124.176、Port 8000、TargetPort 9999，
Pod 仍正常。故障二的 Dashboard Pod 為 dashboard-6dc7857bdf-27hvx，IP 10.244.0.10；
describe 顯示錯誤環境變數，三種 probes 仍檢查 /_stcore/health，Events 全為 Normal。
最終 API Pod AGE 76m、Dashboard Pod AGE 62s，均 Running、Ready、重啟 0 次。
新 Dashboard Pod 的 Restart Count 0 不表示整個演練沒有替換 Pod；它只描述該 Pod 的容器。

使用者正確說明：probe 不經 Service，而是直接檢查 Pod，因此不能發現錯誤的
Service targetPort。補充：Dashboard probe 只確認 Streamlit 自身，不檢查 API URL；
Ready 的意義取決於實際探測範圍，不能視為完整業務流程全部正常。
有效但錯誤的設定不一定有 Warning events，需對照設定與實際請求路徑。

logs 與 namespace events 的收集指令已提供，但未收到其獨立輸出；
本次保留的實際證據為 HTTP traceback、get pods、describe service／pod、使用者修復與 UI 確認。
助理未另行操作 cluster 或瀏覽器，不宣稱已保存未提供的輸出與截圖。
Day 7 已完成，下一課 Day 8 從乾淨 namespace 重建部署，整理文件並驗證記憶體結果遺失。
