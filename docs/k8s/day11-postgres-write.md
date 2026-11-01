# Day 11：完成結果寫入 PostgreSQL

狀態：核心寫入實作與逐步驗收完成。依據使用者提供的終端輸出，
以及助理對工作區程式的檢查；實際時數待填。課程編號依原始 Excel，
表內日期為規劃日期，不代表實際完成日期。

## 實作範圍

- `app/services/run_store.py`：StoredRun、RunStore Protocol、MemoryRunStore，
  以及 RunStoreError、RunStoreUnavailable、RunAlreadyExists。
- `app/services/runs.py`：透過建構子取得 store，完整 response 轉換後才 save；
  save 正常返回後才回傳結果，get 委派給 store。
- `app/services/postgres_run_store.py`：實作 save，以單一參數化 INSERT 保存
  summary、metrics、events；Pydantic JSON 模式搭配 psycopg Jsonb。
- psycopg 連線 context 正常退出時提交，例外時 rollback 並關閉連線；
  模擬不在資料庫交易內執行。每次 save 建立一條連線，尚未使用連線池。
- UniqueViolation 轉成 RunAlreadyExists，OperationalError 轉成
  RunStoreUnavailable，其餘 psycopg.Error 轉成 RunStoreError。
- `create_app(store=None)` 可注入儲存後端；只有未指定時才使用記憶體，
  已指定的後端失敗不會 fallback。
- 儲存不可用回泛用 503，其餘儲存錯誤沿用泛用 500；失敗不產生 Location。
  503 handler 不將底層連線診斷寫入回應或該筆 log。

## 真實 PostgreSQL 驗收

Compose API 重建後 healthy，PostgreSQL 17 容器 Up。以下為使用者實際輸出，
非 mock 結果。測試不使用或公開真實密碼。

1. 直接建立 RunService(PostgresRunStore()) 執行 comparison scenario，
   FIFO、normal_wait_threshold=15。另一條連線查詢並逐值比對三份 JSON，
   包含 events 順序：

   ```text
   run_id: 3dd70628-60ba-497c-b733-cb8f510dfbe6
   completed_lots: 12
   event_count: 142
   PASS: committed summary, metrics, and events match
   ```

2. 讀取上述結果並重建 StoredRun，只在驗證程序內設定 PGPORT=1，再呼叫 save：

   ```text
   PASS: connection failure raises RunStoreUnavailable
   ```

3. 在 API 容器內以執行緒啟動臨時 Uvicorn，127.0.0.1:8765，
   使用 create_app(store=PostgresRunStore())；以 urllib 發出真實 HTTP POST。
   驗證 201、Location、獨立 DB 連線可見結果、summary 相等，metrics/events 非空：

   ```text
   run_id: 6d706057-52b1-4f63-8cab-56e15edb549a
   PASS: HTTP 201 + Location; committed result found in PostgreSQL
   ```

4. 同樣的臨時 HTTP 伺服器，在測試程序設定 PGPORT=1，驗證 HTTP 503、
   泛用 JSON 與沒有 Location，並於 finally 關閉測試伺服器：

   ```text
   Result storage unavailable on /api/v1/runs
   PASS: real database connection failure returns HTTP 503
   ```

錯誤連接埠僅作用於 docker compose exec 啟動的測試程序，未停止 DB，
未更改既有 API 程序的環境。上述驗證腳本於對話中逐步執行，尚未整理為
可重跑的儲存整合測試檔。

## 修正與觀念確認

- 新增例外類別時曾誤將 dataclass decorator 留在 RunStoreError 上，
  已移回 StoredRun，並通過 API 回歸測試。
- 第一版驗證腳本用 asdict 後只轉換 route，保留 lot 的內部狀態欄位，
  導致 48 項 extra_forbidden。錯誤發生於 RunCreate 驗證，尚未執行模擬或寫入。
  後改為明確保留 lot_id、arrival_time、due_date、priority、route，驗收成功。
- 使用者確認 save 拋出例外後不執行 return。補充正常返回代表提交已完成，
  不需再查詢一次才回 201；提交後回覆連線中斷仍可能已有資料，不能反推
  未收到 201 就一定沒有保存。POST 仍沒有 idempotency key，不自動重試。

## 品質檢查

使用者提供的最後完整驗證：

```text
ruff check .                  All checks passed!
ruff format --check .         93 files already formatted
pytest -q                     181 passed, 1 warning
git diff --check              無輸出
```

主機使用既有 Python 3.14 虛擬環境；警告為上游 Starlette TestClient/HTTPX
棄用提醒。真實 DB/HTTP 驗收在 Python 3.12 API 容器執行，未在容器重跑完整
Pytest。交付整理另將 MemoryRunStore 重複 ID 分支由 ValueError 修正為
既定的 RunAlreadyExists；小範圍驗證另由助理執行。

## 限制與 Day 12 交接

正式 `app = create_app()` 仍使用 MemoryRunStore；Compose 與 K8s 尚未正式
切換 PostgreSQL。PostgresRunStore 目前只有 save，缺少 get，尚未完整符合
RunStore Protocol；本次注入該類別僅驗證 POST，不支援結果查詢端點。

Day 12 依一步一步教學方式補 get 與 Pydantic 還原、正式後端選擇，並驗證
重啟後查詢、未知 ID 404、查詢故障不誤回 404。同時補可重跑的整合測試。
重複 ID 的真實 DB 路徑、提交前不可見、提交時故障、rollback 與 volume
重建後結果仍在，本次均未另外實測；不能以連線拒絕測試宣稱涵蓋所有故障。
readiness 目前未檢查 DB，連線池、K8s DB/PVC 與雙副本驗收也尚未完成。
本課未檢查即時 K8s Pod 健康，不能以 Compose healthy 推論 cluster 健康。

Excel 同步至 Day 11：11/30 完成；實際時數維持空白。
