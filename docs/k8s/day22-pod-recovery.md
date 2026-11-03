# Day 22：API Pod 故障恢復量測

狀態：三次正常刪除單一 API Pod 的量測與最終資料驗收完成。實際時數未填；
尚未提交或執行本課 PR CI。原始檔位於 artifacts/day22/，助理已核對 JSONL 統計。

## 環境與基線修正

依使用者即時輸出，kind-fabflow 單節點 Ready（v1.37.0），fabflow-helm release
revision 7 deployed，API 2/2，Dashboard/DB 各 1/1，初始皆零重啟。
API SHA 794dbaafc1697a8812358b30b0808c6100242ebe，Dashboard SHA
395df1ec02a010163ea46e68374feb607c0c39bd。DB 單實例，PVC/PV 與 Day 21 相同。

初次試跑沿用 Day 21 快照，ready 10/10 成功但三個結果端點各 10 次 404。
Service EndpointSlice 指向兩個正確 API Pod（10.244.0.22、10.244.0.23），
Service 與直接 Pod 查詢均回 Run not found。API 連 fabflow-postgres/10.244.0.17，
查原 run 為 0 筆；localhost:8000 卻仍可完整 verify。
使用者 lsof/ps/docker ps 輸出確認 Compose 占用 IPv4 127.0.0.1:8000，
Helm port-forward 僅監聽 IPv6 [::1]:8000。故 Day 21 結果驗收實際屬 Compose，
非 Helm；已更正 Day 21 notes/AGENTS/Excel，未宣稱資料遺失。診斷終端輸出依本次對話，
未另保存完整原始終端日誌；初次失敗 JSONL 保留 trial.jsonl。

停止不需要的 port-forward 後，直接從固定 Dashboard Pod 經 http://fabflow-api:8000
執行 prepare，建立 run f0c1b40d-ccda-476c-982e-14360e17803a，HTTP 201 + Location PASS。
快照存 Dashboard /tmp/day22-helm-before-run.json，另複製至 Mac before-run.json。
正確基線試跑 5 秒四端點各 10 次、零失敗（trial-helm.jsonl）。

## 方法與時間定義

固定 Dashboard Pod fabflow-dashboard-899996b87-fvxgt 執行既有
scripts/probe_rolling_update.py，每次 120 秒，目標每 0.5 秒一輪，依序 GET readiness、
summary、metrics、events；三份結果逐次與完整快照比對，不重試。
timeout=2 是 urllib/socket 設定，不是嚴格的整筆請求總時間上限；慢請求或排程延遲
會使後續輪次延後。因此三次請求數可不同，不代表嚴格等間隔取樣或壓力測試。

Mac 以 Python monotonic 計時，送出 kubectl delete pod --wait=false（正常刪除，
未 force），每次查詢後等待 0.5 秒。終點為被刪 Pod 名稱已不存在，且兩個非刪除中
API Pod 都 Ready。觀察時間包含 kubectl、API server 與輪詢延遲；不是純啟動時間，
不是 HTTP 中斷時間。未獨立記錄新 Pod 首次 Ready 與 Deployment availableReplicas
到達 2 的各自時間；採兩 Ready Pod 作為操作性恢復條件。

## 三次結果（UTC，2026-11-03）

| 次數 | 刪除 Pod 尾碼 | 刪除開始 | 確認恢復 | 觀察恢復秒數 | 請求數 | 失敗數 |
| --- | --- | --- | --- | ---: | ---: | ---: |
| 1 | h8qbh | 03:47:58.562784 | 03:48:01.611242 | 3.049 | 960 | 2 |
| 2 | zxp8q | 03:49:58.051739 | 03:50:01.746065 | 3.694 | 908 | 1 |
| 3 | lb4bv | 03:52:50.448771 | 03:52:54.031848 | 3.583 | 960 | 0 |

三次刪除與恢復均在各自取樣窗口內。合計 2828 請求、3 失敗，約 0.1061%，
僅是三個完整 120 秒觀察窗口的比例，不是故障區間失敗率或長期可用性。
第一次各端點 240 次，metrics/events 各一次 connection refused，開始於
03:47:58.716155Z、03:47:58.721748Z，距刪除開始約 0.15 秒。
時間相近不足以判定具體根因；未抓逐請求目的 Pod 或當時 EndpointSlice 時序。
第二次各端點 227 次，metrics 在 03:51:18.798661Z 逾時，實際耗時 4146.716 ms，
距副本恢復約 77 秒，不能直接歸因於刪 Pod，根因未確認。
第三次各端點 240 次，零失敗。三次均未觀察到成功回應的快照不一致。
原始 JSONL 的 utc 是請求開始時間，不能把失敗開始時間跨度當成連續停機。

## 最終驗收與限制

直接從固定 Dashboard 經 Helm API Service 執行 verify：summary、metrics、events
與新快照完全一致，未知 ID 三端點皆 404。最終 API Pods 9dltm/xbk64 Ready、零重啟，
API 2/2；Dashboard/DB Pod 不變、PVC Bound，PV 仍為
pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd；Helm revision 7 deployed 不變。
刪 Pod 沒有變更 Helm release 或 image tag。本課未測強制終止、節點故障、DB 故障、
執行中 POST、性能或整個 cluster 恢復，不宣稱零停機或生產 HA。

原始 JSONL、三次計時、前後資源與快照保存在 artifacts/day22/；checked-summary.json
由助理從原始檔重新核對產生。本課只整理證據與文件，未修改程式/chart，未重跑 Pytest。
Excel 同步 22/30（約 73.3%），實際時數空白。下一課 Day 23：CI 與部署階段驗收，
尚未開始；先處理待提交/CI 的文件，再依 workbook 範圍逐步驗收。
