# Day 9：結果儲存介面與 PostgreSQL 設計

狀態：設計與逐步觀念練習已完成；尚未實作或驗證 PostgreSQL。
依據根目錄 `FabFlow_K8s_30天進度表.xlsx` Day 9；實際時數待填。
Day 10 建立 Compose DB，Day 11 寫入，Day 12 查詢與重啟測試。

## 現況與目標

`app/services/runs.py` 的 RunService 同時執行模擬與保存 `_runs` 字典，
以 Lock 保護存取。StoredRun 已把 summary、metrics、events 集合成一份
完成結果；目前所有 response 轉換成功後才發布。API routes 透過 create/get
存取結果，未知 ID 回傳 404。重啟會清空字典，不同程序不共享結果。

保留同步模擬與所有既有 HTTP response 欄位，將完成結果交給可替換的儲存介面。
本階段只保存完成結果，不新增 running/failed 狀態、背景工作或中斷恢復。

## 儲存介面

以下是預定介面，尚未加入執行程式：

```python
class RunStore(Protocol):
    def save(self, run: StoredRun) -> None: ...
    def get(self, run_id: str) -> StoredRun | None: ...
```

- save：新增完整結果，成功返回代表已提交；重複 ID 拋出衝突錯誤，不覆寫。
- get：找不到才回 None；連線、查詢或資料解碼失敗須拋出錯誤，不假裝 404。
- 儲存實作將驅動程式錯誤轉成儲存層錯誤，由 API 層處理，不暴露連線字串。
- MemoryRunStore 保留鎖與程序內儲存供既有測試使用；PostgresRunStore 共用 DB。
- RunService 接收 store，由 create_app 組裝；明確選擇 PostgreSQL 時禁止自動
  fallback 到記憶體，避免回報成功卻遺失結果。連線池於 lifespan 關閉。
- StoredRun 與 Protocol 可移至獨立儲存模組，避免 service 與 adapter 循環匯入。

## PostgreSQL schema 草案

目前只依 run_id 讀取整份結果，因此先採一筆 run 一列，避免不必要的事件拆表。
主鍵用 text，維持現有 API 的字串 ID 契約；service 繼續產生 UUID 字串。

```sql
CREATE TABLE completed_runs (
    run_id text PRIMARY KEY,
    summary jsonb NOT NULL CHECK (jsonb_typeof(summary) = 'object'),
    metrics jsonb NOT NULL CHECK (jsonb_typeof(metrics) = 'object'),
    events jsonb NOT NULL CHECK (jsonb_typeof(events) = 'array'),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (summary ->> 'run_id' IS NOT NULL AND summary ->> 'run_id' = run_id)
);
```

summary 保存 RunResponse；metrics 保存 MetricsResponse；events 保存完整
EventResponse JSON array。created_at 為資料庫寫入時間，finished_at 仍為模擬
分鐘，兩者不混用。CURRENT_TIMESTAMP 取目前交易開始時間。
主鍵索引已涵蓋目前查詢，不預先增加 JSON 索引。

以 Pydantic `model_dump(mode="json")` 轉換，再使用參數化 SQL 與驅動程式 JSON
adapter 寫入；讀取以現有 response models 驗證，events 還原為 tuple。
儲存前驗證三份資料完整、ID 一致，數字與字串能由 PostgreSQL JSONB 接受。
SQL 的形狀檢查不能取代完整 Pydantic 驗證。

JSONB 不保留 object key 排序，API 契約依欄位值比對；events 必須保存 array
原始順序，禁止只依 timestamp 重新排序，因為同時間可能存在多個有序事件。
未來若需要事件條件搜尋或分頁，再設計拆表與穩定事件序號。
參考 [PostgreSQL JSON types](https://www.postgresql.org/docs/18/datatype-json.html)。

## 寫入時機與失敗處理

```text
驗證 request → 完成模擬 → 轉換全部 response → save 完整一列
                                           → COMMIT 確認 → HTTP 201 + Location
```

模擬執行期間不持有資料庫交易。單一 INSERT 包含全部結果，於交易提交後才
讓 create 返回；失敗須 rollback 並釋放連線，不可先發布 summary。
PostgreSQL 交易提供全部成功或全部失敗及提交前不可見的語意，見
[Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)。

| 情況 | 預定行為 |
| --- | --- |
| 請求不合法 | 維持 422，不執行模擬或寫入 |
| 模擬或 response 轉換失敗 | 不寫入，維持泛用 500 |
| DB 無法連線或暫時不可用 | 回泛用 503，不回 201，不 fallback |
| 完整性約束、資料解碼或未預期錯誤 | 泛用 500，記錄診斷資訊但不洩漏憑證 |
| 未知 run_id | 查詢成功且無列才回既有 404 |
| 提交成功，但回覆途中連線中斷 | DB 可能已有完整結果；不保證客戶端知道成功 |

最後一種情況不能宣稱「任何錯誤都代表 DB 沒資料」。不自動重試 POST；
目前沒有 idempotency key，使用者重送會產生另一個 run。提交結果不明時也
不可宣稱 rollback 一定生效，但資料仍應完整一列，不會只有部分欄位。

查詢端點、201 summary、Location、metrics 與 events 格式保持原樣。
readiness 後續需檢查儲存可用性並設定短 timeout；liveness 只檢查程序，
避免 DB 故障造成 API 重啟迴圈。初始化 schema 與版本檢查由 Day 10 明確安排。

## 後續驗收

Day 11–12 驗證完整 JSON round-trip（包含同時間事件順序與 null）、
寫入失敗不回 201、交易未提交不可見、未知 ID 404 與 DB 故障不誤回 404。
以真正 PostgreSQL 驗證重啟後仍可查 summary、metrics、events；mock 不能證明持久化。
Day 14 再由兩個 API Pod 各自查詢相同結果。既有 API 測試保護 response 契約。

本機單實例 DB 與 PVC 不等於高可用或備份；資料庫及儲存遺失仍可能丟資料。
執行中的同步模擬仍可能因 API Pod 終止而失敗。

## 逐步練習與理解確認

本次先由使用者逐題回答與補寫介面、SQL，再整理筆記；以下均為文字練習，
未建立資料庫、執行 SQL 或修改應用程式。最初助理先產出的設計已調整為
本次練習的基本 schema；連線池、readiness 等項目仍屬後續實作規劃。

| 主題 | 本次確認與修正 |
| --- | --- |
| 記憶體限制 | 使用者指出 API 重啟會失去結果；查舊 ID 回 404 |
| 保存時機 | 模擬與三份 response 都完成後才 save，提交成功後才能回 201 |
| 查無與故障 | 查無資料回 None；連線失敗拋例外，不能誤回 404 |
| 原子性 | 使用者說明需撤銷全部寫入，避免有 summary 卻沒有 metrics |
| 重試限制 | 提交後連線中斷不代表 DB 無資料；重送會用新 ID 新增結果 |
| 介面 | 使用者完成 save → None、get → StoredRun 或 None 的型別 |
| 委派 | save 傳 stored；get 傳 run_id 並 return；建構子保存傳入 store |
| JSONB | summary、metrics 為 object，events 為 array；修正 metrics/array 混淆 |
| 約束 | NOT NULL 禁止 SQL NULL；CHECK 限制形狀，不保證 KPI 欄位完整 |
| ID 一致性 | summary 的 ID 須非 NULL 且與主鍵一致；不一致則拒絕 INSERT |
| 時間與順序 | created_at 使用預設時間；events 保留原順序，時間仍重要但同時事件不能只靠 timestamp 排序 |
| 可替換性 | 儲存介面固定，因此更換後端不需修改模擬邏輯 |

練習中串接出的 service 片段如下，尚未套用至程式：

```python
def __init__(self, store: RunStore) -> None:
    self._store = store


# create() 完成模擬與 response 轉換後，取代原字典寫入：
# self._store.save(stored)


def get(self, run_id: str) -> StoredRun | None:
    return self._store.get(run_id)
```

下一課 Day 10 從檢查現有 Compose 開始，一步一步建立 PostgreSQL 開發環境。
依使用者偏好，每次說明與練習一步，等待完成後再繼續，不直接完成整課實作。
原始 Excel 進度表尚未同步 Day 8–9 狀態；本次完成紀錄以 Markdown 為準。

