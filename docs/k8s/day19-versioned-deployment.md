# Day 19：版本化部署

狀態：依使用者終端輸出，指定 commit 映像部署、舊結果與新模擬 HTTP 驗收完成。
實際時數未填。未驗證零停機或更新期間失敗率。

## 環境與映像來源

使用者確認 Mac arm64、kind-fabflow context、fabflow-control-plane Ready/arm64。
起始 Helm namespace fabflow-helm，API 2/2、Dashboard/DB 各 1/1，PVC Bound。
建立分支 feat/day19-versioned-deployment，提交 Day 18 收尾文件為
395df1ec02a010163ea46e68374feb607c0c39bd；建置前工作目錄乾淨。

本課採本機 Docker 建置、載入 kind，未取得 Day 18 CI runner 的映像，未發布 registry。
SHA tag 表示建置來源 commit；目前未鎖定基底映像 digest 或所有依賴，重新建置不保證
產生完全相同的映像。後續 values/文件提交也不會改變此次映像的來源 SHA。

```bash
FABFLOW_IMAGE_TAG=$(git rev-parse HEAD)
docker build --platform linux/arm64 --target api --tag "fabflow-api:$FABFLOW_IMAGE_TAG" .
docker build --platform linux/arm64 --target dashboard --tag "fabflow-dashboard:$FABFLOW_IMAGE_TAG" .
kind load docker-image "fabflow-api:$FABFLOW_IMAGE_TAG" "fabflow-dashboard:$FABFLOW_IMAGE_TAG" --name fabflow
```

使用者 inspect 確認兩映像 linux/arm64、tag 皆為上述完整 SHA。
API image ID：sha256:30ec324bd2e26ca6c963ac2db6a4c624815f772f183d687b04b4330a46792471。
Dashboard image ID：sha256:a34e7e8fa814f28acab9c477ac18c68b4d8bc21c00061cb43129b15c18035989。
kind load 輸出兩映像 loading，後續 Pod 成功使用指定 tag。

## Helm 版本設定與更新

新增 deployments/helm/fabflow/values-kind.yaml，兩服務 tag 固定上述 SHA，
repository 分別 fabflow-api/fabflow-dashboard，pullPolicy 為 IfNotPresent。
此檔案只適用已預載映像的本機 kind；新建 cluster 須重新建置或載入映像。
預設 values.yaml 仍為 day13/day5；後續 upgrade 應明確提供 values-kind.yaml。

```bash
helm lint deployments/helm/fabflow -f deployments/helm/fabflow/values-kind.yaml
helm template fabflow deployments/helm/fabflow --namespace fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml | grep -E 'image:|imagePullPolicy:'
helm upgrade fabflow deployments/helm/fabflow --namespace fabflow-helm \
  -f deployments/helm/fabflow/values-kind.yaml --wait --timeout 5m
```

lint 通過（只有 icon INFO），渲染確認兩個 SHA tag、postgres:17。
升級結果 revision 4、deployed；chart 未改版，仍 0.1.0。
兩個新 API Pod 77bbcb6b4d-2j8nz/cwpxr、新 Dashboard 899996b87-fvxgt 皆 Ready、
0 restarts，均使用指定 SHA tag。兩 API runtime imageID 相同：
sha256:4c4651d4b055dee0dbab2c798f4e3f5fa7985267abe49f319c7a80d3166aa912。
Dashboard runtime imageID：sha256:73126bbbe18ab992d475143308cb3bb67ffa55f453f6c7d9c44153f9bb9dd9f0。
不同工具的 image ID/digest 類型可能不同，未據此宣稱本機 ID 與 runtime digest 相等。
DB Pod 7b879c7d67-tsf4s 保持不變；PVC Bound，PV 仍為
pvc-5b243a9e-ec4c-4f0a-a87e-2650a639b1dd。

## 結果與服務驗收

更新前以 Service port-forward 到 localhost:8000，prepare 保存 Mac 外部快照：

```bash
python scripts/check_postgres_persistence.py prepare --api-url http://127.0.0.1:8000 \
  --snapshot /tmp/fabflow-day19-before-upgrade.json
```

run_id：fd6d54d2-67e0-4fbb-8682-e737b4cd6711，HTTP 201 + Location 與完整快照 PASS。
更新後重新建立 port-forward，以同一路徑執行 verify：summary、metrics、events
完全一致，未知 ID 三端點皆 404。這是 Service 連線驗收，未逐一指定兩個 API Pod。

```bash
kubectl exec -i -n fabflow-helm deployment/fabflow-dashboard -- \
  python - < scripts/smoke_containers.py
```

使用者結果：baseline finish=175、cycle=70.5、transport_jobs=0；AMHS bottleneck
finish=203、cycle=142.75、transport_jobs=40。Dashboard health/HTML、API readiness、
兩情境 create/query/metrics/events workflows 全 PASS。未執行真實瀏覽器互動。

## 限制與接續

未量測更新期間請求失敗數／耗時，未演練 rollback；不宣稱 rolling update 或零停機。
單實例本機 PostgreSQL/PVC 不代表 HA 或 cluster 刪除後可恢復。
主機未安裝 rg，教學改用 grep；zsh 的 custom-columns 含方括號時需引號。
本課變更尚待提交與 PR CI；未重新執行完整 Pytest。
Excel 更新 19/30（約 63.3%），實際時數空白。
下一課 Day 20 驗證 rolling update，先查現有 Deployment strategy 與即時環境，
再設計持續探測與更新量測；不可把本課 Helm upgrade 成功當作 Day 20 已驗收。
