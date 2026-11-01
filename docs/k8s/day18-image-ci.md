# Day 18：建立映像 CI

狀態：依使用者提供的 PR Checks 成功確認及兩份建置日誌，核心驗收完成。

## 實作與驗收

- `.github/workflows/ci.yml` 新增 `workflow_dispatch`。
- 新增 images job，`needs: [quality, containers]`，兩個檢查成功後才建置。
- matrix target 為 api、dashboard，對應既有 Dockerfile stages。
- 使用 `docker build --target "${{ matrix.target }}" --tag "fabflow-${{ matrix.target }}:${{ github.sha }}" .`。
- 修改提交為 `4a61034`，分支 `feat/k8s-deployment`，已推送。
- PR：https://github.com/j22868706/sideproject_fabflow/pull/1
- 使用者確認 quality、containers、images (api)、images (dashboard) 全部成功；助理無法直接讀取 PR 頁面，未獨立查證遠端結果。
- 使用者提供 API 完整建置日誌及 Dashboard naming 行，兩者皆使用完整 SHA：

```text
fabflow-api:45160aa86a58c4bdb4592d08addc655dc664e454
fabflow-dashboard:45160aa86a58c4bdb4592d08addc655dc664e454
```

這是 PR workflow 的 SHA；不能當作來源分支 head `4a61034`。

## 起始環境

使用者輸出確認 context kind-fabflow、節點 Ready；Helm release fabflow 在
fabflow-helm 為 revision 3 deployed、chart 0.1.0。API 2/2、Dashboard 與 DB 各
1/1，四個 Pod 皆 Running、0 restarts，PVC Bound。這是課程開始時的狀態，
本課未部署新映像或重新驗證 HTTP 業務流程。

## 範圍與後續

映像僅在 GitHub Actions runner 建置，未 push registry、未匯出 artifact。
Docker 日誌 naming to docker.io/library 不代表已上傳 Docker Hub。
未確認 PR 已合併、main push CI 或手動觸發驗收；本次為 PR CI 驗收。
workflow_dispatch 手動入口需要 workflow 存在於預設分支。

Day 18 達成 Excel 的成功建置紀錄與 commit SHA tag 標準。Excel 同步 18/30
（60%），實際時數仍空白；不把規劃日期當成實際完成日期。
下一課 Day 19：版本化部署，先決定映像保存／取得方式，並處理 CI runner 與
本機 kind 的架構相容性，再讓 Helm 使用指定版本。一次一步，等待使用者操作。
