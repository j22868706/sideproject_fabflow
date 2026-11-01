# Day 15：持久化階段驗收

狀態：核心故障與恢復驗收、品質檢查及觀念確認完成。
操作證據為使用者終端輸出；最後品質檢查與即時狀態另由助理執行確認。
Excel 日期為規劃日期，實際時數待填。

## 本課範圍

沿用 Day 14 的兩個 API 副本與同一 PostgreSQL，不新增應用程式儲存邏輯。
先驗證故障前基線，再將 DB Deployment 縮為 0；兩個 API 分別驗證 GET/POST
故障行為，最後 DB 縮回 1，確認舊結果完整、新結果可寫，及失敗 POST 沒有資料列。
過程保留原 PVC，未刪 namespace、PVC 或 cluster。

本課新增驗收腳本 `unavailable-create` 模式，並將 comparison request 組裝抽成
`comparison_payload()`。每次失敗 POST 使用唯一 scenario ID，送出前以 exclusive
create 保存嘗試紀錄；檢查 503、泛用 JSON、沒有 Location。紀錄檔不能覆寫，
重跑須指定新的 --snapshot 路徑。腳本透過 stdin 傳入 API Pod，不需重建映像。

## 起始狀態與基線

課程開始確認 kind-fabflow 節點 Ready、兩 API 與 DB Ready、postgres-data Bound。
Day 14 的變更仍在工作區，未另行提交或推送；本課持續保留。

- API A：api-5ffdfc4f9-w6r5t。
- API B：api-5ffdfc4f9-sr8s4。
- 故障前 DB：postgres-68b5ffb575-2k8mj。
- PVC：postgres-data，PV pvc-60e544b2-48ce-4579-b74c-49669e01b4a9，1Gi、RWO。
- 基線 run：be4c1d60-b9d0-4ca1-9fa5-e95aae5448d1。

兩個 API 各自執行既有 verify 模式，三份結果與 Day 14 快照一致，未知 ID 的
三個端點皆回 404。快照位於兩個 API Pod 的 /tmp/fabflow-day14-check.json。

## DB 停機與錯誤回應

使用者依序執行：

```bash
kubectl scale deployment/postgres -n fabflow --replicas=0
kubectl wait --for=delete pod -n fabflow -l app=fabflow-postgres --timeout=120s
kubectl get deployment postgres -n fabflow
kubectl get pvc postgres-data -n fabflow
```

實際 Deployment 為 0/0，PVC 仍 Bound。縮容防止 Deployment 自動建立替代 Pod，
不同於只刪 Pod。manifest 中 postgres replicas 仍為 1，縮容是本次臨時演練。

```bash
for api_pod in api-5ffdfc4f9-w6r5t api-5ffdfc4f9-sr8s4; do
  kubectl exec -i -n fabflow "$api_pod" -- \
    python - unavailable --snapshot /tmp/fabflow-day14-check.json \
    < scripts/check_postgres_persistence.py
done
```

兩個 API 各對已知 ID 與新產生的未知 UUID 查詢 summary、metrics、events，
共 12 項全部 PASS，回應均為 HTTP 503 與
`{"detail": "Result storage is unavailable"}`，沒有將連線失敗誤報為 404。
這是腳本 unavailable 模式首次完成真實 K8s DB 停機驗收，取代先前「尚未執行」狀態。

接著在兩個 API 執行失敗寫入驗收：

```bash
for api_pod in api-5ffdfc4f9-w6r5t api-5ffdfc4f9-sr8s4; do
  kubectl exec -i -n fabflow "$api_pod" -- \
    python - unavailable-create --snapshot /tmp/fabflow-day15-failed-post.json \
    < scripts/check_postgres_persistence.py
done
```

兩者均 PASS：HTTP POST 503、泛用 JSON、沒有 Location。唯一 scenario ID 為：

| API | scenario_id |
| --- | --- |
| A | outage-6b84ef40-b6bb-4133-af98-5bf9e12a073e |
| B | outage-034b7724-a0f5-4b86-9d73-e6999575ab39 |

嘗試紀錄各保存在原 API Pod 的 /tmp/fabflow-day15-failed-post.json。
兩次模擬使用有效請求，失敗發生在結果保存時，未回報成功。

## 恢復與資料檢查

```bash
kubectl scale deployment/postgres -n fabflow --replicas=1
kubectl rollout status deployment/postgres -n fabflow --timeout=180s
kubectl get pods,pvc -n fabflow
```

新的 DB Pod postgres-68b5ffb575-slbvt 為 1/1 Running，掛載相同 PVC/PV。
兩個 API 未重啟，各自再執行 verify：三份完整結果與故障前一致，未知 UUID
三端點恢復 404。這次補上了 K8s PostgreSQL Pod 重建沿用原 PVC 的實測證據。

兩個 API 再讀取各自的失敗嘗試紀錄，以參數化 SQL 檢查：

```sql
SELECT count(*) FROM completed_runs WHERE summary ->> 'scenario_id' = %s;
```

兩個唯一 scenario ID 的 count 都為 0，實際輸出均為
`PASS: failed POST left no completed result`。
此證據限於本次 DB 無法連線的兩次請求，不能推論所有錯誤都一定沒保存資料。

DB 恢復後由 B 進行新寫入：

```bash
kubectl exec -i -n fabflow api-5ffdfc4f9-sr8s4 -- \
  python - prepare --snapshot /tmp/fabflow-day15-recovery.json \
  < scripts/check_postgres_persistence.py
```

實際新 run 為 32a2a591-91eb-4225-8e98-21b52809e53b，HTTP 201、Location，
三份結果可讀，12 lots、142 events 檢查通過。未再對 A 比對這筆恢復後新結果。

## 完整性與同步執行限制

目前完整 summary、metrics、events 轉換完成後才以一列 INSERT 寫入，
save 在交易提交後才正常返回。已驗證既有結果完整保留、兩次連線失敗沒有新增列、
恢復後可建立完整新結果。沒有實測提交中斷、部分 INSERT、資料損毀、交易未提交
可見性或重複 ID DB 分支；不能把本次驗收宣稱涵蓋所有原子性故障情境。

使用者回答同步模擬中斷時無法續跑，但最初認為新 Pod 會從頭開始，已補充：

- 模擬進度在原 API 程序記憶體中，沒有 checkpoint 或背景工作佇列。
- Pod 中途終止，客戶端可能收到連線中斷或錯誤，新 Pod 不自動重試原請求。
- 只有重新送 POST 才會從頭執行並產生新的 run ID。
- 若提交已成功、回覆途中斷線，DB 可能已有結果；目前沒有 idempotency key，
  不應假設重送會沿用原結果。

本課是觀念說明，沒有實際在模擬中途終止 API Pod。

## 最後驗證與交接

使用者最後貼文未顯示完整輸出，助理因此直接重跑，實際結果：

```text
ruff check .                         All checks passed!
ruff format --check .                98 files already formatted
pytest -q                            184 passed, 1 warning
git diff --check                     無輸出
kubectl apply --dry-run=server ...    全目錄 manifests 通過
```

warning 為上游 Starlette TestClient/HTTPX 棄用提醒。主機使用 Python 3.14，
真實 HTTP/DB 驗收在 Python 3.12 API 容器執行；未重跑完整容器 Pytest、Dashboard
或瀏覽器驗收，未確認遠端 CI。

助理最後讀取：兩個 API 1/1 Running、0 restarts；新 PostgreSQL Pod
1/1 Running、0 restarts；Dashboard 1/1 Running，維持既有一次 restart；
原 postgres-data PVC Bound。Server dry run 不會套用或修復設定。

仍是單節點 kind、單實例 DB；Recreate 更新可能中斷，API readiness 不檢查 DB，
未做備份或 HA，PVC 不保護 cluster 刪除。本次沒有量測故障或恢復耗時，
沒有吞吐量、節點容錯或零停機宣稱。

Excel 同步 Day 15 完成，15/30（50%），實際時數仍空白。下一課 Day 16 依 Excel
建立 Helm chart 骨架與 values，先確認現有檔案與狀態，再按一次一步方式教學。
