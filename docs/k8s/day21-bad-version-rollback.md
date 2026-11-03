# Day 21：壞版本與回復演練

狀態：故障診斷與手動 Helm rollback 完成；原資料驗收於 Day 22 確認連到 Compose，不作為 Helm 資料完整性證據。使用者接受快速觀念教學並確認了解；未另作答。實際時數未填，尚未提交或執行本課 PR CI。

## 基線與證據

依使用者終端輸出與 artifacts/day21/ 保存的原始資料：kind-fabflow 單節點 Ready，
namespace fabflow-helm，起始 Helm revision 5 deployed。API 2/2，Dashboard/DB 各 1/1，
Pod 零重啟。API SHA 794dbaafc1697a8812358b30b0808c6100242ebe，Dashboard SHA
395df1ec02a010163ea46e68374feb607c0c39bd。API RollingUpdate maxSurge=1、maxUnavailable=0。
PVC Bound，PV pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd。

演練前原欲透過 Service port-forward 驗收，但 check_postgres_persistence.py prepare 實際連到 Compose 的 IPv4 localhost:8000，
建立 run 5edf7556-d9e5-404b-adb1-3bc512cac086，HTTP 201 + Location 通過。
完整外部快照保存於 artifacts/day21/before-run.json。

## 故障與診斷

```bash
helm upgrade fabflow deployments/helm/fabflow --namespace fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml \
  --set-string api.image.tag=day21-intentionally-missing --wait --timeout 90s
```

未啟用自動回復。2026-11-03T03:27:08Z 開始，03:28:38Z 結束，
exit 1，整秒計數 90 秒，Helm revision 6 failed：Deployment 未 Ready、Updated 1/2、
context deadline exceeded。這是命令等待耗時，不是停機時間。

新 Pod fabflow-api-67756b6786-86fb6 為 0/1、ImagePullBackOff，容器未啟動。
Events 顯示拉取 docker.io/library/fabflow-api:day21-intentionally-missing，
收到 pull access denied / insufficient_scope: authorization failed，
由 ErrImagePull 進入 ImagePullBackOff。此 tag 未預載，IfNotPresent 因而嘗試遠端拉取；
事件不能單獨區分遠端 repository 不存在或授權不足，不需要為本演練補 registry 登入。

Deployment READY 2/2、AVAILABLE 2 來自兩個舊 Pod；UP-TO-DATE 1 表示一個 Pod
採用新設定，不表示它已 Ready。兩個舊 API Pod h8qbh/zxp8q 持續 Running/Ready。
maxSurge=1 允許額外 Pod，maxUnavailable=0 保留可用副本；這不保證每次 HTTP 請求成功。

## 手動回復與驗收

```bash
helm rollback fabflow 5 --namespace fabflow-helm --wait --timeout 90s
```

2026-11-03T03:32:58Z 開始、03:32:59Z 結束，exit 0，shell SECONDS 記錄 0。
時間只有整秒精度，不能據此宣稱精確 0 秒或瞬間回復。這是回復命令耗時，
不是服務停機恢復時間。rollback 使用 revision 5 的設定建立 revision 7 deployed；
revision 6 保留 failed，revision 5 轉為 superseded。

回復後 API SHA 恢復 794dbaa…，READY/UP-TO-DATE/AVAILABLE 都是 2。
故障 Pod 已移除，原兩個 API Pod 保留且零重啟；Dashboard、DB Pod 及 PVC/PV 不變。
verify 完整比對 summary、metrics、events 全 PASS，未知 ID 三端點皆 HTTP 404。
上述 verify 實際連到 Compose，不能證明 Helm rollback 前後資料一致。Day 22 發現並修正環境歸屬，詳見下節。

## 教學與限制

快速教學涵蓋 Ready 舊副本與更新完成的差別、rollback 新增 revision，以及已 Ready
但功能錯誤或 DB schema 不相容時，回復風險可能不同。使用者確認了解。
本次未持續 HTTP 探測，沒有故障期間失敗請求數或零停機證據；未測功能錯誤版本、
DB schema 回復、DB HA 或整個 cluster 恢復。未改應用程式或 chart；未重跑完整 Pytest。
原始命令日誌、事件、前後狀態與快照保存於 artifacts/day21/，log 加入忽略例外。

Excel 同步 21/30（70%），實際時數保留空白。下一課 Day 22：固定頻率探測下的
API Pod 故障恢復量測，重複三次。尚未開始，先重新確認 live 狀態，一次一步進行。

## Day 22 更正：IPv4/IPv6 連線環境不同

使用者輸出顯示 Docker/Compose API 監聽 127.0.0.1:8000，而 kubectl port-forward
僅監聽 [::1]:8000。Day 21 prepare/verify 明確使用 http://127.0.0.1:8000，
因此 run 5edf7556-d9e5-404b-adb1-3bc512cac086 與成功比對屬於 Compose。
Day 22 從 Dashboard 經 Helm Service 及直接對兩個 Helm API Pod 查詢皆 404；
Helm API 設定 postgres、PGHOST=fabflow-postgres，DB 10.244.0.17 中該 run 為 0 筆。
localhost:8000 同時仍可完整比對原快照。這不是 Helm DB 資料遺失的證據。
原驗收檔保留，不改寫其內容；助理先前將 localhost 成功視為 Helm 驗收，判斷過早。

壞版本、診斷、rollback 與工作負載狀態的核心驗收仍成立；Helm rollback 前後
資料完整性未驗證。Day 22 改從固定 Dashboard 直接連 Helm Service 建立新快照，
驗證三次 API Pod 刪除後資料一致；這不追溯補足 Day 21 rollback 的資料驗收。
