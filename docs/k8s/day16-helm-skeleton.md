# Day 16：Helm chart 骨架與 values

狀態：本機 chart 骨架、lint、template 與參數覆寫驗收完成，尚未安裝至 cluster。
依使用者操作輸出與助理最後渲染檢查；Excel 日期為規劃日期，實際時數待填。

## 工具與起始狀態

開始時 Git 工作目錄乾淨，kind-fabflow 節點 Ready；兩 API、Dashboard、PostgreSQL
均 Ready，postgres-data PVC Bound。助理確認本機有 Homebrew，但沒有 helm。
使用者安裝後提供 `helm version --short`：`v4.3.1+gc0d08d0`。

本課只建立與渲染本機檔案，未執行 helm install、helm upgrade 或套用渲染結果。
不以本課輸出宣稱完成 Helm 安裝驗收、零停機升級或資料持久化的新驗收。

## 檔案與參數

```text
deployments/helm/fabflow/
├── Chart.yaml
├── README.md
├── values.yaml
└── templates/
    ├── api.yaml
    ├── dashboard.yaml
    └── postgres.yaml
```

Chart.yaml：apiVersion v2、name fabflow、type application、version 0.1.0。
chart apiVersion 與 Helm CLI 主版本不同；v2 chart 可由 Helm 4 使用。
chart version 表示部署封裝版本，不代表 API 或 PostgreSQL 映像標籤。

| 元件 | 預設映像 | 副本數 | Service port |
| --- | --- | --- | --- |
| API | fabflow-api:day13 | 2，來自 values | 8000 |
| Dashboard | fabflow-dashboard:day5 | 1，來自 values | 8501 |
| PostgreSQL | postgres:17 | 模板固定為 1，Recreate | 5432 |

三個元件的 image repository、tag、pullPolicy 與 Service port 來自 values.yaml。
容器監聽埠仍固定為 8000、8501、5432；Service targetPort 使用對應的具名埠。
變更 Service port 不代表容器程序也改用該埠。

模板使用 `.Release.Name` 作名稱前綴、`.Release.Namespace` 指定 namespace。
Pod labels、Deployment selector、Service selector 同時使用 release instance 與
component，以區分三個元件及不同 release。chart 不建立 Namespace。

## 逐步操作與結果

使用者手動建立 Chart.yaml、values.yaml，分別通過 helm show chart、helm show values。
接著依序建立三個模板，各自用 --show-only 渲染並確認名稱、映像、副本數與埠。

```bash
helm show chart deployments/helm/fabflow
helm show values deployments/helm/fabflow
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --show-only templates/api.yaml
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --show-only templates/dashboard.yaml
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --show-only templates/postgres.yaml
helm lint deployments/helm/fabflow
```

使用者與助理皆執行 lint，實際為 `1 chart(s) linted, 0 chart(s) failed`。
`Chart.yaml: icon is recommended` 是 INFO 建議，不是 lint failure。

覆寫參數的實際指令：

```bash
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  --set api.replicaCount=3 --set-string api.image.tag=day16-check \
  --show-only templates/api.yaml
```

實際產出 replicas 3、image fabflow-api:day16-check。此 tag 僅用來示範，未建置或載入。
values.yaml 仍為 replicas 2、tag day13。產生 YAML 不需要先建立 fabflow-helm namespace。

助理另外重新渲染完整 chart 並以 YAML parser 檢查：

- 恰為 3 個 Deployment 與 3 個 Service，皆使用 fabflow-helm namespace。
- 三個元件的 Pod labels、Deployment selector、Service selector 一致。
- 預設映像與副本數符合上表；Service targetPort 對應 container named port。
- 參數覆寫後 API 為 3 副本與 day16-check 映像。

以上本機解析與 lint 不等於 Kubernetes server validation 或實際啟動成功。

## 觀念確認

使用者最初認為 helm template --set replicas=3 會改動 cluster，已修正：
template 只產出 YAML。設定需由 helm install、helm upgrade 或 kubectl apply
送至 Kubernetes 才會生效；kubectl rollout status 只觀察進度，不觸發更新。
使用者補充需要把產物交給 K8s 更新部署。現有 kind 部署不受本課渲染影響。

## 最後品質檢查

使用者提供：ruff check . 通過；format check 為 99 files already formatted；
pytest -q 為 184 passed、1 項上游 Starlette TestClient/HTTPX 棄用警告；
git diff --check 無輸出。主機使用既有 Python 3.14 虛擬環境。
助理最後重跑 lint 與 template 並檢查完整產物，未重跑未變更的完整 Python 測試。
尚未確認遠端 CI，未執行 Helm release 安裝、升級或 Helm 場景 HTTP/瀏覽器驗收。

## Day 17 交接

目前 chart 缺少 API PostgreSQL 連線、Dashboard API URL、ConfigMap、Secret 引用、
DB 初始化 SQL、PVC、probes 與 resources。PostgreSQL 未提供密碼，API 也未選擇
postgres store；本課產物不可視為可正常運行的完整堆疊。

下一課依 Excel 一步一步補齊上述設定，在獨立乾淨 namespace 安裝並驗證 HTTP
建立及查詢，不直接套用到現有 fabflow namespace。既有資料與 PVC 保留，避免
為練習而刪除 Day 13–15 的資料。原始部署 YAML 為既有驗收基線，尚未遷移成
Helm release；後續須清楚指定各自管理的 namespace 與部署入口。

Excel 同步至 Day 16：16/30（約 53.3%），實際時數維持空白。
