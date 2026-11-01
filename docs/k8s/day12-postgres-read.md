# Day 12：PostgreSQL 查詢與持久化驗證

狀態：逐步實作與核心驗收完成，依使用者終端輸出與助理工作區檢查。
Excel 規劃日期不代表實際完成日期；實際時數待填。

## 實作

- `PostgresRunStore.get()` 以參數化 SELECT 查詢完整一列，透過 Pydantic
  還原 summary、metrics、events；events 依原順序轉回 tuple。
- 查詢成功但無列才回 None；OperationalError 轉成 RunStoreUnavailable，
  其他 psycopg.Error 或結果驗證錯誤轉成 RunStoreError。另確認 summary ID
  與查詢 ID 一致；儲存不可用回 503，不能假裝是未知 ID 的 404。
- `create_app()` 在建立 RunService 之前選擇後端：未設定
  FABFLOW_RUN_STORE 時使用 memory；postgres 使用 PostgresRunStore；
  其他值直接 ValueError。明確注入 store 時優先使用該實例，不自動 fallback。
- Compose API 設定 FABFLOW_RUN_STORE=postgres，沿用 PG* 連線參數。
  DB 保留 POSTGRES_DB、POSTGRES_USER、POSTGRES_PASSWORD 初始化設定。
  本機未選擇 postgres 的 API、既有測試與尚未更新的 K8s 仍使用記憶體。
- 新增三個參數化 HTTP 測試，確認 get 拋出不可用例外時，summary、metrics、
  events 端點均回泛用 503。
- `scripts/check_postgres_persistence.py` 提供 prepare、verify、unavailable
  三個模式，透過真實 HTTP 驗收。腳本不負責啟停容器。

## 真實資料與 HTTP 驗收

使用者依序執行，以下非 mock 結果：

1. 新 get 讀取 Day 11 的 `3dd70628-60ba-497c-b733-cb8f510dfbe6`，
   12 lots、142 events；與獨立 SQL 查詢的三份 JSON 逐值一致，未知 UUID 回 None。
2. 重建 Compose API，啟用 PostgreSQL。透過正式 8000 埠查詢上述 run 的
   summary、metrics、events，均為 200 且與 DB 一致；未知 UUID 三端點均為 404。
3. 透過正式 HTTP POST 建立 `d1ff784b-c208-48a9-b06e-8c8fd8b88f02`，
   回 201、Location；12 lots、142 events。容器內保存完整回應快照至
   `/tmp/fabflow-day12-before-restart.json`。
4. `docker compose restart api` 後 API healthy，三份 GET 與原快照完全一致。
5. `docker compose stop db` 後，對該已知 ID 的三份 GET 全部回 503，
   JSON 為 `{"detail": "Result storage is unavailable"}`，沒有誤回 404。
6. DB 恢復、API healthy 後，三份結果仍與故障前快照一致。過程包含 DB
   容器 force-recreate 與 Docker Desktop 重啟，沿用原 named volume。
7. 可重跑腳本 prepare 建立 `77f03e37-0ac1-43f4-b0e3-2b8556693a50`；
   restart API 後 verify 的六項檢查全部通過：三份完整快照比對與三個未知 ID 404。

腳本 prepare/verify 已實測；unavailable 模式尚未執行，不能將上面的手動
停機驗證宣稱為該模式已通過。該模式另外檢查未知 ID 在 DB 故障時也回 503。

## 可重跑的重啟驗收

在專案根目錄，Compose API 與 DB 已就緒後：

```bash
docker compose exec -T api python - prepare < scripts/check_postgres_persistence.py
docker compose restart api
docker compose ps api db
# 等 API healthy 後：
docker compose exec -T api python - verify < scripts/check_postgres_persistence.py
```

預設快照為 API 容器內 `/tmp/fabflow-day12-check.json`，不放在 DB 或 Git。
restart 保留同一容器的快照；API force-recreate 或 down 會移除快照，
驗證容器重建時須先另行保存快照。prepare 遇既有檔案會拒絕覆寫，可指定新路徑：

```bash
docker compose exec -T api python - prepare --snapshot /tmp/day12-repeat.json \
  < scripts/check_postgres_persistence.py
docker compose exec -T api python - verify --snapshot /tmp/day12-repeat.json \
  < scripts/check_postgres_persistence.py
```

兩次命令之間需要實際 restart，才能宣稱驗證重啟持久化。腳本本身不證明
所選後端為 PostgreSQL；本課另以 Compose 設定、DB 查詢及真實停機確認。
腳本建立真實結果且不刪除驗收資料。

## 掛載故障與恢復

DB stop 後 start 失敗，OCI runtime 提示
`/host_mnt/Volumes/externalssd/swe/fabflow/deployments/postgres/init: not a directory`。
此錯誤發生於容器掛載階段，PostgreSQL 尚未啟動，不代表 SQL 或寫入錯誤。

助理確認本機 init 是目錄、SQL 是檔案，Compose 的 bind mount 正確；
docker inspect 顯示資料掛在 `fabflow_postgres_data`，初始化 SQL 為唯讀 bind mount。
`docker compose up -d --force-recreate --no-deps db` 仍發生相同錯誤。
使用者畫面確認 Docker Desktop File sharing 已包含 `/Volumes`，因此未新增共享。

重啟 Docker Desktop 後一度出現 docker.sock 不存在，等待 Engine 啟動，
以 docker info 確認 Server 恢復後再執行：

```bash
docker compose up -d db
docker compose exec db pg_isready -U fabflow -d fabflow
docker compose up -d api
docker compose ps api db
```

實際為 accepting connections、API healthy，資料比對成功。未刪除 volume，
未重新初始化 DB。重啟後掛載恢復，但確切根因未確認，不能宣稱已證實某個
Docker Desktop 缺陷或權限問題。不要以 down -v 處理此類問題。

## 操作修正與觀念

- get 一度誤放在 save 內，助理修復為同層方法並執行 24 項 API 回歸測試。
- main 一度重複建立 FastAPI 且先傳入 None store，已由使用者調整順序。
- FABFLOW_RUN_STORE 一度放在 db，且 DB 初始化變數被 PG* 取代；後續修正。
  api environment 內重複的 environment 空項也已移除。Compose config 通過
  只保證設定格式可接受，不能證明變數放在正確服務。
- 本機最初缺 psycopg 導致測試收集失敗，重新安裝 editable 開發依賴後恢復。
- 使用者最初將 DB 連線失敗與寫入失敗混淆；已補充 404 表示查詢成功但無列，
  503 表示目前不能判斷資料是否存在，既有資料可能仍完整保留。
- 使用者正確回答 DB 容器重建後資料保留是因原 named volume，而非 API 記憶體。

## 最後驗證與限制

使用者提供 format check：95 files already formatted；pytest：184 passed，
1 項上游 Starlette TestClient/HTTPX 棄用警告；git diff --check 無輸出。
助理另執行 ruff check . 通過。主機完整測試使用 Python 3.14；真實 DB/HTTP
驗收使用 Python 3.12 API 容器。未重跑完整容器 Pytest、Dashboard 或 browser acceptance，
也未驗證遠端 CI。

API readiness 仍只檢查程序生命週期與 service 存在，不檢查 DB；DB stop 時
健康檢查可能仍通過，不能視為持久化儲存可用。每次操作仍建立連線，尚未有
連線池、migration、備份或 HA；單一 named volume 也無法保護整個 Docker VM 遺失。
執行中的同步模擬可能因 API 終止而失敗；只保護已提交結果。
本課未實測資料解碼損毀、重複 ID 的 DB 路徑與提交故障，未量測恢復時間。

課程開始時曾確認 kind-fabflow 的 API、Dashboard 各 1/1 Running；
Docker Desktop 重啟後未重新驗證 K8s，不能延用舊狀態。下一課 Day 13 依 Excel
逐步建立 K8s 單實例 PostgreSQL、PVC 與 Secret，開始前重新檢查 cluster。
進度同步為 12/30（40%）；實際時數保持空白。
