# Day 20：Rolling update 量測

狀態：指定 API 映像更新、持續 HTTP 量測與資料驗收完成；觀察到 5 次連線失敗，
不宣稱零停機。實際時數未填。PR 與 main CI 已依使用者確認全部成功，收尾完成。

## 環境與設定

kind-fabflow 單節點 ARM64，namespace fabflow-helm，API 兩副本，DB 單實例。
起始 Helm revision 4，工作目錄乾淨。原 API strategy 為預設 RollingUpdate，
maxSurge/maxUnavailable 各 25%。本課在 templates/api.yaml 明確設定
maxSurge: 1、maxUnavailable: 0。readiness 仍不檢查 DB，MinReadySeconds 為 0。

分支 feat/day20-rolling-update，提交 794dbaafc1697a8812358b30b0808c6100242ebe
加入明確策略與 scripts/probe_rolling_update.py。從乾淨提交本機建置 linux/arm64
API 映像並載入 kind，image ID：
sha256:63322f0667620930a6f33279aa95d9124eae776795f19e29cda92cfbdf884b98。
values-kind.yaml 僅 API tag 改為此 SHA；Dashboard 保留
395df1ec02a010163ea46e68374feb607c0c39bd，避免量測端隨更新替換。
API 應用程式碼未變，此次測的是更換映像 tag 所觸發的部署行為。

## 探測方式

從固定 Dashboard Pod 透過 http://fabflow-api:8000 Service，依序 GET readiness、
已保存 run 的 summary、metrics、events。每輪目標間隔 0.5 秒，每請求 timeout
2 秒，不自動重試；慢請求會延後後續輪次。三份結果逐次與快照完整比對。
每筆 JSONL 包含開始 UTC、monotonic elapsed、狀態、延遲與錯誤。
這不是壓力測試，也沒有驗證每次請求落在哪個 API Pod。

run_id：35e5a9c1-87e2-4eb6-a08b-9428c61a2d47，142 events。
快照原存 Dashboard /tmp，更新前已複製到 Mac；5 秒試跑每端點 10 次，零失敗。

正式探測：2026-11-01T22:50:47.480291Z 至 22:55:47.454167Z（請求開始時間），
總執行約 300.000 秒。Helm upgrade --wait --timeout 2m 執行區間紀錄
22:53:06Z 至 22:53:12Z（秒精度），命令耗時 6.818 秒、exit 0，revision 5 deployed。
此耗時為 Helm 命令耗時，不是中斷時間。

| 端點 | 請求數 | 失敗數 |
| --- | ---: | ---: |
| readiness | 594 | 0 |
| summary | 594 | 2 |
| metrics | 594 | 0 |
| events | 594 | 3 |
| 合計 | 2376 | 5 |

整段取樣失敗比例約 0.2104%，不是僅更新區間的失敗率，也不是長期可用性。
失敗為 3 次 connection refused、2 次 timeout，均無 HTTP 狀態碼。
失敗請求開始於 22:53:10.219356Z 至 22:53:13.703797Z；逾時延遲約 2004 ms，
所以最後一次失敗完成晚於最後開始時間。這個時間跨度不代表連續完全中斷。

## 更新與資料驗收

Deployment events 顯示新 RS 0→1、舊 RS 2→1、新 RS 1→2、舊 RS 1→0。
新 API Pods 7bfd9c659d-h8qbh/zxp8q 皆 Ready、零重啟，指定 SHA tag 正確。
Dashboard Pod 899996b87-fvxgt 與 DB Pod 7b879c7d67-tsf4s 保持不變。
Deployment revision 3 與 Helm release revision 5 是不同計數。

更新後 verify 三份結果與快照一致，未知 ID 三端點均 404。
未在本課重新執行兩情境 HTTP smoke 或瀏覽器測試。

失敗發生在替換舊 Pod 前後，可能涉及終止與 Service 路由傳播時間差；
未收集逐請求目的 Pod、終止中舊容器日誌或當時 EndpointSlice 變化，根因未確認。
事件中的 DB/API readiness timeout 約在本次更新前 24 分鐘，不能作此次根因證據。
maxUnavailable: 0 約束 Deployment 可用副本，不保證所有 HTTP 請求成功。
未修改 preStop、grace period 或應用程式關閉流程，未重測改善效果或 rollback。

## 原始資料與檢查

artifacts/day20/ 保存 JSONL、升級日誌、快照、更新後 Deployment YAML、events JSON。
全域 *.log 忽略規則會排除升級日誌，本課新增此目錄 log 例外以保留原始證據。
升級日誌含 shell session 結束輸出；命令成功證據為 EXIT_CODE=0 與 Helm 結果。
助理讀取本機原始 JSONL，核對計數、錯誤類型、時間與上述統計。
probe 腳本 Ruff/format、模擬 HTTP 回應一致／不一致分支檢查通過；使用者 Helm lint
通過（只有 icon INFO）。本課 PR 與 main CI 結果見下方收尾紀錄。

Excel 更新 20/30（約 66.7%），實際時數空白。
下一課依計畫為 Day 21 壞版本與回復演練，尚未開始。開始前重新確認 live cluster；
一次一步，不預先操作故障或回復。

## PR 與 main 收尾

- 量測設定與 probe 提交：794dbaa；驗收紀錄與原始證據提交：a084f55。
- PR #3：https://github.com/j22868706/sideproject_fabflow/pull/3
- 使用者確認 PR 全部 Checks 成功、無衝突，並完成合併。
- 使用者終端確認：`c750798 (HEAD -> main, origin/main, origin/HEAD) Merge pull request #3 from j22868706/feat/day20-rolling-update`。
- 使用者確認 c750798 的 main CI：quality、containers、images (api)、images (dashboard) 全部成功。
- 遠端 Checks 依使用者確認，助理未獨立取得遠端 Actions 日誌；不推定有額外量測。
- main 合併不會自動更新本機 Helm release；最後已驗證的部署仍為 revision 5、API SHA 794dbaa。

Day 20 的原始資料、統計、限制、資料完整性驗收及合併／CI 收尾紀錄齊全。
