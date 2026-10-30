# Day 2：驗證既有 Docker 基線

狀態：已完成核心驗收（依使用者提供的終端輸出與 UI 操作確認）。進度表日期：2026-10-30；預估 3 小時。

依據：根目錄 `FabFlow_K8s_30天進度表.xlsx` 的 Day 2，以及
[Day 1 筆記](day01-architecture.md) 的 Next session。
原七天 MVP 的 Day 2 是模擬引擎實作，已完成；本文件接續 Kubernetes 30 天計畫。

## 今天的目標與順序

| 時間 | 工作 | 完成條件 |
| --- | --- | --- |
| 0–15 分鐘 | 不看筆記重畫 Day 1 的建立 run、查詢 KPI 路徑，再對照程式 | 標出 API 邊界、同步模擬、記憶體 dictionary；補完 Day 1 複習項目 |
| 15–40 分鐘 | 閱讀 Dockerfile、compose.yaml；記錄環境版本 | 能解釋兩個 build target、ports、健康檢查、單 worker、API URL |
| 40–85 分鐘 | 建置並啟動 Compose，確認兩個服務 healthy | readiness 成功，Dashboard 首頁可開啟 |
| 85–115 分鐘 | 執行現有 HTTP smoke test，保存輸出 | 兩種預設情境的建立、summary、metrics、events 查詢通過 |
| 115–150 分鐘 | 手動操作 Dashboard 的兩種情境 | FIFO、aging 60；各完成模擬、載入及重新整理 KPI，保存畫面與 run ID |
| 150–180 分鐘 | 整理實測紀錄、排錯與停止步驟 | 留下可重現的操作與驗收證據，銜接 Day 3 |

## 1. 環境與設定

從 repository root 執行。先啟動 Docker Desktop／Engine；確認沒有其他程式占用
8000、8501。只記錄本次實際結果，不沿用 MVP 先前的驗收結論。

```bash
mkdir -p artifacts/k8s/day02
date -Iseconds
git rev-parse HEAD
git status --short
docker version
docker compose version
docker context show
docker compose config --quiet
```

將日期、commit、工作目錄是否有修改、OS／CPU 架構、Docker client/server 與 Compose
版本填入下方紀錄。首次建置需要下載映像與 Python 套件。

閱讀 [Dockerfile](../../Dockerfile) 與 [compose.yaml](../../compose.yaml)，確認：

- API 使用 8000、Dashboard 使用 8501；API 只有一個 worker。
- 瀏覽器連 `http://localhost:8501`；Dashboard 容器連 `http://api:8000`。
- `depends_on: service_healthy` 控制啟動順序；各服務的 healthcheck 檢查自身狀態。
- 結果仍在 API 記憶體，重啟會遺失；今天的部署沒有新增持久化。

## 2. 啟動與 HTTP 驗收

```bash
docker compose up --build --wait --wait-timeout 120
docker compose ps
docker compose images
docker compose exec -T api python --version
docker compose exec -T dashboard python --version
curl --fail-with-body http://127.0.0.1:8000/health/ready
docker compose exec -T dashboard python - < scripts/smoke_containers.py > artifacts/k8s/day02/http-smoke.log 2>&1
```

確認 smoke 指令的退出碼為 0，並查看 `artifacts/k8s/day02/http-smoke.log`。
預期 readiness 為 `{"status":"ready"}`，smoke 有兩種情境及最後整體檢查的 PASS。
腳本同時檢查 Dashboard health／HTML，以及 API 的 POST、summary、metrics、events。
它沒有操作瀏覽器按鈕；下一步另外驗證 UI。

| 情境（FIFO、aging 60） | 完成 lots | finished_at（分鐘） | 平均 cycle（分鐘） | transport jobs |
| --- | ---: | ---: | ---: | ---: |
| Three-stage baseline | 20 | 175 | 70.50 | 0 |
| AMHS bottleneck | 20 | 203 | 142.75 | 40 |

以上是現有腳本的預期值，本次實測後才可標記通過。

## 3. Dashboard 驗收

1. 開啟 `http://localhost:8501`，保留 API base URL 為 `http://api:8000`。
2. 按 **Check connection**，確認成功。
3. 選 baseline、FIFO、aging 60，按 **Run simulation**。
4. 記錄 run ID，按 **Load KPIs**，比對上表；再按 **Refresh KPIs** 確認可查詢。
5. 換 AMHS 情境，重做上述操作，確認運輸 KPI 出現。
6. 各保存一張含情境、run ID 或結果與 KPI 的畫面到 `artifacts/k8s/day02/`。

## 4. 排錯與收尾

失敗時先保留輸出、讀 logs，再決定修正；不要把失敗寫成已通過。

```bash
docker compose ps
docker compose logs --no-color --tail=200 api dashboard > artifacts/k8s/day02/compose.log 2>&1
```

優先檢查 Docker 是否啟動、port 是否被占用、映像或套件下載是否成功，以及 Dashboard
的 API URL。詳細處理方式參考 [runbook](../runbook.md)。驗收與畫面保存完成後：

```bash
docker compose down
```

停止會清除 API 記憶體中的結果。重啟遺失與跨副本查詢的正式演練留到後續進度。

## 本次實測紀錄

| 項目 | 實測結果／證據 |
| --- | --- |
| 執行日期、實際時數 | 待填 |
| Commit、工作目錄修改 | 待填 |
| OS、CPU 架構、Docker context | Client macOS darwin/arm64；Server linux/arm64；desktop-linux |
| Docker、Compose、容器 Python 版本 | Client／Engine 29.7.2；Desktop 4.87.0；Compose v5.4.0；容器 Python 版本未提供 |
| API／Dashboard 映像 ID | 待填 |
| Compose health、readiness | 使用者輸出：api、dashboard 均 healthy；readiness 回傳 ready |
| HTTP smoke 退出碼、輸出 | 使用者貼出兩種情境與整體檢查皆 PASS；退出碼未另提供；輸出保存如下 |
| Baseline run ID、KPI、畫面 | 使用者確認 KPI 符合上表、Refresh 成功；run ID 與畫面未提供 |
| AMHS run ID、KPI、畫面 | 使用者確認 KPI 符合上表、Refresh 成功；run ID 與畫面未提供 |
| 問題、根因、處理步驟 | 誤輸入 docker show；改用 docker context show 後成功；未回報其他問題 |
| 停止指令結果 | 尚未確認執行；收尾指令見上方 |

使用者提供的 HTTP smoke 原始輸出：

```text
PASS: Three-stage baseline; finish=175, cycle=70.5, transport_jobs=0
PASS: AMHS bottleneck; finish=203, cycle=142.75, transport_jobs=40
PASS: dashboard health/HTML, API readiness, and both create/query/metrics/events workflows
```

Day 1、Day 2 已標示完成；實際時數待學習者填寫。上述實測依據為使用者在教學對話
提供的輸出與確認，並非助理重新執行；未提供的版本、畫面與 run ID 不宣稱已保存。
Day 3 接續建立 kind 或 k3d cluster、確認 kubectl context 及 namespace。
目前依使用者要求暫停 Kubernetes 教學；尚未建立或驗收 cluster。

## Day 2 教學重點與理解確認

Dockerfile 定義映像的建置與容器啟動方式；Compose 定義兩個服務的網路、port、
環境變數、健康檢查與啟動相依性。映像是執行材料，容器才是實際執行的實例。

```text
Mac 瀏覽器 → localhost:8501 → Dashboard 容器
                                   ↓ http://api:8000
                                API 容器
                                   ↓
                        同步模擬 → 記憶體結果
```

- Mac 的 localhost 指向 Mac；Dashboard 容器的 localhost 指向該容器自己。
  Dashboard 透過 Compose 服務名稱 api 呼叫 API。
- healthy 表示設定的健康檢查通過；HTTP smoke 另外確認完整 API 流程，
  瀏覽器操作再確認按鈕、結果與 KPI 更新。
- POST 建立模擬並等待完成；後續 GET 查詢已儲存的結果，不重新執行模擬。

使用者已透過問答確認：API 重啟會遺失記憶體結果；不同 API 程序的記憶體不共用，
因此跨副本查詢可能回傳 404；替代 Pod 不會恢復舊記憶體，需要共用的持久化儲存。

為銜接後續課程，也介紹以下概念；本次沒有執行 Kubernetes 驗證：

| 元件／檢查 | 責任 |
| --- | --- |
| Deployment | 管理 Pod 副本數與版本更新；Pod 被刪除後建立替代 Pod |
| Service | 提供穩定連線入口，將流量送到符合條件且就緒的 Pod |
| Readiness | 判斷是否可接請求；失敗時移出一般 Service 流量，不因此重啟容器 |
| Liveness | 判斷是否需重啟容器；連續失敗達門檻時觸發重啟 |
| PostgreSQL（後續實作） | 保存並共用已完成結果；不會自動接手中斷的模擬 |

使用者已正確回答 readiness 用於「程序正常，但暫時尚未準備好接請求」的情況。
