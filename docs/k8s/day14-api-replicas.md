# Day 14：雙 API 副本查詢一致性

狀態：逐步操作、核心驗收與觀念確認完成，依使用者提供的終端輸出及工作區檢查。
Excel 日期是規劃日期，實際時數待填。

## 變更與目標

`deployments/k8s/api.yaml` 的 replicas 從 1 改為 2。沿用 fabflow-api:day13、
FABFLOW_RUN_STORE=postgres、PGHOST=postgres 與 Secret 密碼，PostgreSQL 仍為單副本。
本課沒有更改模擬、API response、資料表、DB 副本數或 Deployment Recreate 策略。

目標是在 Pod A 建立結果，直接向 A、B 各自的 HTTP API 查詢相同 run，
逐值比對 summary、metrics、events，另確認兩個 Pod 實際連到同一個 DB server。
不以多次請求 Service 推測已碰到不同 Pod。

## 起始狀態與擴容

助理重新讀取 cluster：kind-fabflow 節點 Ready，API、Dashboard、PostgreSQL
各 1/1 Running，postgres-data PVC Bound、1Gi、RWO。Git 工作目錄起初乾淨。
依 Excel Day 14，使用者修改 replicas 並套用：

```bash
kubectl apply -f deployments/k8s/api.yaml
kubectl rollout status deployment/api -n fabflow --timeout=180s
kubectl get pods -n fabflow -l app=fabflow-api -o wide
```

實際觀察：

| 角色 | Pod | IP | 狀態 | 節點 |
| --- | --- | --- | --- | --- |
| A | api-5ffdfc4f9-w6r5t | 10.244.0.10 | 1/1 Running、0 restarts | fabflow-control-plane |
| B | api-5ffdfc4f9-sr8s4 | 10.244.0.11 | 1/1 Running、0 restarts | fabflow-control-plane |

Pod 名稱與 IP 是本次實測值，重跑時先查詢當前名稱。兩個副本位於同一個 kind 節點，
不能宣稱節點故障容錯。原策略仍為 Recreate，兩副本也不能直接推論更新零停機。

## 指定 Pod 的完整結果比對

在 A 的 127.0.0.1:8000 發 HTTP POST，並保存三份回應快照：

```bash
kubectl exec -i -n fabflow api-5ffdfc4f9-w6r5t -- \
  python - prepare --snapshot /tmp/fabflow-day14-check.json \
  < scripts/check_postgres_persistence.py
kubectl exec -n fabflow api-5ffdfc4f9-w6r5t -- \
  cat /tmp/fabflow-day14-check.json > /tmp/fabflow-day14-snapshot.json
```

使用者回報：

```text
run_id: be4c1d60-b9d0-4ca1-9fa5-e95aae5448d1
snapshot: /tmp/fabflow-day14-check.json
PASS: HTTP 201 + Location; complete pre-restart snapshot saved
```

prepare 同時檢查 12 lots、142 events。Mac 的 /tmp 快照再傳入 B：

```bash
kubectl exec -i -n fabflow api-5ffdfc4f9-sr8s4 -- \
  python -c 'import sys; from pathlib import Path; Path("/tmp/fabflow-day14-check.json").write_bytes(sys.stdin.buffer.read())' \
  < /tmp/fabflow-day14-snapshot.json
kubectl exec -i -n fabflow api-5ffdfc4f9-sr8s4 -- \
  python - verify --snapshot /tmp/fabflow-day14-check.json \
  < scripts/check_postgres_persistence.py
kubectl exec -i -n fabflow api-5ffdfc4f9-w6r5t -- \
  python - verify --snapshot /tmp/fabflow-day14-check.json \
  < scripts/check_postgres_persistence.py
```

快照只供預期值比對，未匯入 DB 或 API store；verify 是發出 HTTP GET，
不是從快照模擬 API 回應。B 與 A 各自均輸出：

```text
PASS: summary matches pre-restart snapshot
PASS: metrics matches pre-restart snapshot
PASS: events matches pre-restart snapshot
PASS: unknown ID returns HTTP 404 for summary
PASS: unknown ID returns HTTP 404 for metrics
PASS: unknown ID returns HTTP 404 for events
run_id: be4c1d60-b9d0-4ca1-9fa5-e95aae5448d1
```

沿用腳本的 pre-restart 字樣，本課實際是在不同 Pod 比對；本課沒有新增 restart
驗收。events 比較完整內容與順序，不只檢查事件數量。

## 確認共用資料庫

對兩個指定 Pod 分別執行 psycopg 查詢，使用各自 PG* 環境設定：

```sql
SELECT current_database(), inet_server_addr(), inet_server_port();
SELECT count(*) FROM completed_runs WHERE run_id = %s;
```

第二個查詢以參數傳入上述 run ID，兩個 Pod 均確認 count=1。實際輸出：

```text
pod: api-5ffdfc4f9-w6r5t
PGHOST: postgres
database server: ('fabflow', IPv4Address('10.244.0.8'), 5432)
PASS: shared database contains the verified run
pod: api-5ffdfc4f9-sr8s4
PGHOST: postgres
database server: ('fabflow', IPv4Address('10.244.0.8'), 5432)
PASS: shared database contains the verified run
```

這確認兩個程序連到同一個 DB server，未輸出密碼。IP 是觀察值，設定仍使用
Service DNS postgres，不將 Pod IP 寫死。

## 觀念、範圍與後續

使用者正確回答：若 PostgreSQL 停止，兩個 API 副本都無法連線查詢。
雙 API 副本不等於 DB 高可用；預期的查詢故障回應仍是 503，而非 404。
本課沒有實際停止 K8s DB，503 的真實停機證據仍是 Day 12 的 Compose 驗收。

- 已驗證 A 建立、A/B 直接 HTTP 讀取同一結果，以及共用實際 DB。
- 尚未驗證 B 建立再由 A 查詢、併發 POST、Service 流量分配、API 故障恢復或效能。
- 未重新執行 Dashboard/瀏覽器驗收，未量測吞吐量或可用性提升。
- DB 仍是單實例；兩個 API 同節點；本機 PVC 仍不保護 cluster 刪除，沒有備份或 HA。
- API readiness 仍不檢查 DB，不能以兩個 Pod Ready 推論儲存可用。
- Day 13 的 API Pod 重建證據仍有效於當時實測；本課沒有額外刪除 Pod。

依 Excel，Day 15 是持久化階段驗收：品質與 API 回歸、DB 暫時不可用及恢復、
完整結果與錯誤處理範圍整理，並說明同步執行中的模擬仍可能因 Pod 終止失敗。
開始前重新確認即時 cluster 狀態，依使用者偏好一次一步。

## 最後檢查

使用者提供：

```text
ruff check .                 All checks passed!
ruff format --check .        97 files already formatted
pytest -q                    184 passed, 1 warning
git diff --check             無輸出
API server dry run           deployment configured；service unchanged
```

警告是上游 Starlette TestClient/HTTPX 棄用提醒。主機使用 Python 3.14，真實 HTTP/DB
命令在 Python 3.12 API 容器內執行；未在容器跑完整 Pytest，未檢查遠端 CI。
server dry run 不修改 cluster；兩個 Running Pod 的證據來自先前實際 apply 後的輸出。
以上格式檔案數照錄使用者輸出，不作為功能驗收條件。

Excel 同步 Day 14 完成，14/30（約 46.7%），實際時數保持空白。
