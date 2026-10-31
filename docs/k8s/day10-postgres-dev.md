# Day 10：PostgreSQL 開發環境

狀態：設定與逐步操作驗收完成，依使用者提供的終端輸出與問答記錄。
依據 `FabFlow_K8s_30天進度表.xlsx` Day 10；實際時數待填。
本課只建立開發環境與驗證連線，尚未將 RunService 接到資料庫。

## 本次變更

- `compose.yaml`：新增 PostgreSQL 17 的 db 服務，使用者與資料庫皆為 fabflow。
- `postgres_data` 具名 volume 掛載 `/var/lib/postgresql/data`。
- 初始化目錄唯讀掛載 `/docker-entrypoint-initdb.d`。
- `.env` 保存本機密碼且被 Git 忽略；`.env.example` 只保存佔位值。
- API 加入 PGHOST=db、PGPORT=5432、PGDATABASE/PGUSER=fabflow 與 PGPASSWORD。
- `pyproject.toml` 加入 `psycopg[binary]>=3.2,<4.0`，重建 API 映像安裝驅動程式。

db 沒有對主機發布連接埠。API 在 Compose 網路以 db 服務名稱連線，
不使用 localhost。Compose 要求 POSTGRES_PASSWORD 非空，否則停止並提示。
設定了環境變數不代表應用程式已改用 PostgreSQL；模擬結果仍在 API 記憶體。

## 操作與實際結果

開始時 `docker compose version` 為 v5.4.0，`docker compose ps` 沒有容器。
使用者逐步加入 db、環境變數、volume 與初始化 SQL，修正 db 層級、
volumes 誤放 environment 內的縮排，以及密碼變數缺少非空檢查。

建立本機 `.env` 後：

```bash
docker compose config --quiet
docker compose up -d db
docker compose ps db
docker compose exec db pg_isready -U fabflow -d fabflow
docker compose exec db psql -U fabflow -d fabflow \
  -c "SELECT current_database(), current_user;"
```

使用者輸出確認映像下載成功、fabflow_postgres_data 建立、fabflow-db-1 啟動。
pg_isready 回 accepting connections，SQL 回傳 fabflow / fabflow。
容器 Up 本身不等於資料庫已可用，因此另做 readiness 與查詢驗證。

## Schema 初始化

使用者建立 `deployments/postgres/init/001_completed_runs.sql`，內容沿用
Day 9：run_id 主鍵、三個 JSONB、created_at、JSON 形狀與 ID 一致性約束。

本次先啟動 DB，之後才加入初始化 SQL，所以既有 volume 不會自動執行腳本。
使用者手動套用一次：

```bash
docker compose exec -T db psql -U fabflow -d fabflow \
  -v ON_ERROR_STOP=1 < deployments/postgres/init/001_completed_runs.sql
docker compose exec db psql -U fabflow -d fabflow -c '\d completed_runs'
```

實際回傳 CREATE TABLE；表結構列出五個 NOT NULL 欄位、run_id 主鍵、
三個 JSON 形狀 CHECK 及 summary.run_id 非 NULL 且等於主鍵的 CHECK。
此腳本供空資料目錄首次初始化使用，不是 migration，也不應在已有表時重跑。

加入掛載後重新執行 `docker compose up -d db`，容器中可見
`/docker-entrypoint-initdb.d/001_completed_runs.sql`。再次查詢：

```bash
docker compose exec db psql -U fabflow -d fabflow \
  -c "SELECT to_regclass('public.completed_runs');"
```

回傳 completed_runs，確認本次容器重建後表結構仍保留。
本次未插入模擬結果，因此不能宣稱已驗證結果資料重建後持久化。
也尚未實測空白 volume 的自動初始化路徑。

## API 容器連線

使用者重建 API：

```bash
docker compose up -d --build api
docker compose ps api db
```

提供的狀態為 API Up、health: starting，DB Up；未另提供 API healthy 的最終輸出。
接著在 API 容器執行：

```bash
docker compose exec -T api python - <<'PY'
import psycopg

with psycopg.connect(connect_timeout=5) as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        print(cursor.fetchone())
        cursor.execute("SELECT to_regclass('public.completed_runs')")
        print(cursor.fetchone())
PY
```

使用者分兩次執行上述查詢，分別得到：

```text
('fabflow', 'fabflow')
('completed_runs',)
```

這驗證 Python 驅動程式、Compose 服務連線、帳密與表可見性，
尚未實作或測試 RunStore.save/get 的 PostgreSQL adapter。

## 敏感設定、檢查與觀念

`git check-ignore .env` 回傳 .env，且使用者提供的 git status 沒有 .env。
`.env.example` 以佔位值提交；不記錄或提交真實開發密碼。
Compose config --quiet 通過；git diff --check 曾指出 postgres_data 行尾空白，
使用者回報已修正。交付前再由助理檢查並補齊文字檔末尾換行。

使用者確認初始化腳本不會在既有資料目錄重啟時重跑。
容器與 volume 的生命週期問答最初答錯，補充後使用者確認：
容器重建但原 volume 未刪除，資料仍保留。普通 down 保留 volume；
down -v 會刪除具名 volume，本次未執行刪除。

交付時同步在 CI containers job 設定僅供一次性測試 DB 的密碼，避免新增的
Compose 非空檢查阻斷既有容器驗收；README 與 runbook 補上 .env 設定步驟。
這不使用或公開本機真實憑證，遠端 CI 結果另以實際 workflow 為準。

單實例本機 DB 與 volume 不等於備份或高可用。原始 Excel 尚未同步
Day 8–10 狀態，完成紀錄以各課 Markdown 為準。下一課 Day 11
逐步實作完整結果寫入，確認提交成功後才回 201；仍依一步一步教學方式進行。

## 交付前本機驗證

助理執行 Ruff lint、format check、pytest -q、git diff --check 與
Compose config --quiet，皆通過。Pytest 為 179 passed，使用既有 Python 3.14
虛擬環境；有一項上游 TestClient/HTTPX 棄用警告。本次未重跑 Python 3.12、
容器 HTTP smoke 或瀏覽器驗收。Ruff 另補齊 Day 9 Python 範例的空行格式。
