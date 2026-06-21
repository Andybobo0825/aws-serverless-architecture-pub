# Magic Cloud 維護書（prod v1.0）

版本：prod v1.0  
維護範圍：`magic-mvp` production-lite AWS 環境  
主要區域：`ap-northeast-1`（CloudFront / ACM for CloudFront 例外依 AWS 需求使用 global / us-east-1）  
最後更新：2026-06-06

本文件是雲端服務維護與備份管理總入口。所有實際設定以 Terraform (`infra/`) 為準；本文件用來讓日常維運、備份確認、告警處理與還原操作有固定 SOP。

## 1. 系統服務總覽

| 類別 | AWS 服務 / 資源 | 用途 | Terraform / 文件來源 | 維護優先級 |
| --- | --- | --- | --- | --- |
| 身分 | Cognito User Pool / Groups / Client | Admin / Teacher / Student 登入與角色 | `infra/cognito.tf` | 高 |
| API | API Gateway HTTP API + Lambda | JWT 驗證後進入後端 API | `infra/api_gateway.tf`, `infra/lambda.tf` | 高 |
| 資料 | DynamoDB `users`, `weeks`, `class-access` | 帳號 profile、週次教材、班級可見週次 | `infra/dynamodb.tf` | 最高 |
| 物件 | S3 `content` | private magic pages / 教材內容 | `infra/s3.tf`, `scripts/deploy-static.sh` | 高 |
| 前端 | S3 `app_frontend`, `admin_frontend` + CloudFront | App / Admin PWA hosting | `infra/s3.tf`, `infra/cloudfront.tf` | 中 |
| 觀測 | CloudWatch Logs / Alarms + SNS | Lambda log、API/Lambda error alarm | `infra/lambda.tf`, `infra/alarms.tf` | 高 |
| 成本 | AWS Budgets + Cost Allocation Tag | 月費提醒與成本邊界 | `infra/budgets.tf` | 中 |
| 發佈 | Terraform + static deploy scripts | infra/app/admin/content release | `docs/release-checklist.md`, `scripts/` | 高 |

## 2. 備份與保留政策

> 時間基準：所有日常檢查建議以 Asia/Taipei 管理；AWS 事件時間通常顯示 UTC，排障時需換算。

| 服務 | 備份/保留方式 | 目前設定 | 可還原時間點 | 例行確認時間 | 還原責任 |
| --- | --- | --- | --- | --- | --- |
| DynamoDB `users` | Point-in-Time Recovery (PITR) 連續備份 | `point_in_time_recovery.enabled = true` | 可還原至 PITR 保留期間內任一秒；目前 Terraform 未設定較短 recovery period，按 AWS 預設/上限 35 天管理 | 每週一 10:00 確認三張表 PITR 仍為 enabled | Cloud maintainer |
| DynamoDB `weeks` | PITR 連續備份 | enabled | 同上 | 每週一 10:00 | Cloud maintainer + teacher/admin 確認資料正確 |
| DynamoDB `class-access` | PITR 連續備份 | enabled | 同上 | 每週一 10:00 | Cloud maintainer |
| S3 `content` | S3 Versioning | `status = "Enabled"` | 可回復到物件前一版本；無固定排程快照、無 lifecycle retention | 每週一 10:15 抽查 versioning 與教材物件版本 | Cloud maintainer |
| S3 `app_frontend` | S3 Versioning + 可重新部署前端 artifact | enabled | 可回復前一版 `index.html` / assets；也可由 git tag `v1.0` 重新 build/deploy | 每次 release 後確認；每月第一個工作日抽查 | Release owner |
| S3 `admin_frontend` | S3 Versioning + 可重新部署前端 artifact | enabled | 可回復前一版 `admin.html` / assets；也可由 git tag 重新 build/deploy | 每次 release 後確認；每月第一個工作日抽查 | Release owner |
| Cognito User Pool | 無 Terraform 管理的自動備份；以 deletion protection + `prevent_destroy` 降低誤刪風險 | `protect_identity_data = true` 時 deletion protection ACTIVE | 無直接 PITR；帳號可由 admin 重建，角色/profile 需和 DynamoDB `users` 對齊 | 每週一 10:30 確認 deletion protection 與 admin 帳號可登入 | Cloud maintainer + admin |
| Lambda 程式碼 | Git commit/tag + Terraform package | `v1.0` tag / `infra/build/magic-api.zip` 本地產物 | 回復到指定 git tag 後 `terraform apply` | 每次 release | Release owner |
| CloudWatch Logs | Log retention | `/aws/lambda/magic-mvp-api` retention `14` 天 | 只保留 14 天 logs，不是資料備份 | 每週一 11:00 確認 log group retention | Cloud maintainer |
| API Gateway / CloudFront | Terraform 狀態與 IaC | 無資料備份需求 | 由 Terraform 重建 | 每次 infra 變更後 `terraform plan` | Cloud maintainer |
| Terraform state | 本地 `infra/terraform.tfstate` + `terraform.tfstate.backup` | 目前 repo 有本地 state 檔；不得提交敏感 tfvars/state | 依本機檔案與備份恢復 | 每次 infra apply 後備份至安全位置 | Cloud maintainer |

### 刪除保護範圍

`var.protect_identity_data = true` 是 production-lite 的預設值，現在同時控制關鍵資料與入口服務的刪除保護：

- Cognito User Pool：`deletion_protection = ACTIVE`，並加上 Terraform `prevent_destroy`。
- DynamoDB `users` / `weeks` / `class-access`：PITR + `deletion_protection_enabled` + `prevent_destroy`。
- S3 `content` / `app_frontend` / `admin_frontend`：`force_destroy = false` + `prevent_destroy`，避免 Terraform 誤刪 bucket 與版本化物件。
- CloudFront app/admin distributions：`retain_on_delete = true` + `prevent_destroy`，避免入口 CDN 被直接刪除。
- API Gateway、Lambda、Lambda CloudWatch Log Group、ACM certificate：用 Terraform `prevent_destroy` 擋住 destroy / replacement plan。

若真的要執行破壞性重建，需先在獨立變更中明確移除對應 `prevent_destroy`，保存 state/備份，並在維護窗口內執行。

### 備份缺口與改善建議

1. **DynamoDB 沒有長期月備份**：目前 PITR 適合誤刪/誤改的 35 天內回復；若課程結束後需保留學員資料超過 35 天，應新增 AWS Backup 或 DynamoDB on-demand backup 策略。
2. **S3 Versioning 沒有 lifecycle 規則**：舊版本會持續累積成本。課程結束後需決定保留期，例如 90/180 天後清除 noncurrent versions。
3. **Cognito 沒有自動備份**：若需要可稽核的人員清單，建議每週匯出 username/email/group 到安全儲存位置；目前文件先以 deletion protection + DynamoDB profile 作為營運保護。
4. **Terraform state 目前是本地管理**：production 長期運作建議改為 S3 backend + DynamoDB state lock，並開啟 state bucket versioning。

## 3. 每日 / 每週 / 每月維護排程

### 每日（上課期間 09:30 Asia/Taipei）

| 項目 | 操作 | 通過標準 |
| --- | --- | --- |
| App / Admin 健康檢查 | 執行 `./scripts/smoke-test.sh` | static smoke checks passed |
| CloudWatch alarms | 檢查 `magic-mvp-lambda-errors`、`magic-mvp-api-5xx` | 無 ALARM；若有需看 Lambda logs |
| Admin 登入 | 用 admin 帳號進入 console | Users / Weeks / device reset 介面可載入 |
| Student smoke | 用測試 student 查看開放 week | 只看到應開放週次，教材 card 可開新分頁 |

### 每週一（10:00–11:00 Asia/Taipei）

| 時間 | 項目 | 操作 |
| --- | --- | --- |
| 10:00 | DynamoDB PITR | 確認 `users`、`weeks`、`class-access` PITR enabled |
| 10:15 | S3 Versioning | 確認三個 bucket versioning enabled；抽查 `content/magic-pages/` 物件版本 |
| 10:30 | 刪除保護 | 確認 Cognito deletion protection、DynamoDB deletion protection、S3 `force_destroy=false`、CloudFront retain-on-delete 與 Terraform `prevent_destroy` 仍在 |
| 10:45 | 成本 | 看 AWS Budget 是否接近 10 / 20 / 50 USD threshold |
| 11:00 | Logs | 確認 Lambda log group retention 為 14 天，近 24h 無大量 `api_error` / `unexpected_error` |

### 每月第一個工作日

| 項目 | 操作 | 備註 |
| --- | --- | --- |
| Terraform drift | `cd infra && terraform plan` | 應為 no changes；有差異需記錄原因 |
| 成本檢查 | AWS Cost Explorer / Budget | 確認 `magic=true` tag 成本分類仍有效 |
| 還原演練 | 選一張非 production restore target 表演練 DynamoDB restore | 不覆蓋原 production table |
| S3 舊版本成本 | 檢查三個 bucket noncurrent versions 數量 | 若成本上升，評估 lifecycle policy |
| 文件更新 | 更新本文件與 `docs/release-checklist.md` | 所有實際變更需反映到文件 |

## 4. 服務操作手冊

### 4.1 Cognito 身分服務

- **用途**：登入、JWT issuer、角色群組 (`admin`, `teacher`, `student`)。
- **重要設定**：
  - deletion protection 由 `var.protect_identity_data` 控制，並透過 Terraform `prevent_destroy` 擋住誤刪。
  - access/id token 3 小時；refresh token 7 天。
  - temporary password 有效 7 天。
- **日常管理**：
  - 建立/刪除/同步帳號優先使用 Admin Console。
  - 刪除 Cognito user 前確認 DynamoDB `users` profile 也會同步刪除。
- **備份策略**：目前無自動備份。需要長期 audit 時，新增定期匯出 Cognito users/groups 的腳本。
- **事故處理**：若登入大範圍失敗，先檢查 User Pool ID、Client ID、JWT issuer 與 frontend runtime config 是否一致。

### 4.2 DynamoDB 資料表

- **表**：
  - `magic-mvp-users`：app profile、role、status、classes、device authorization metadata。
  - `magic-mvp-weeks`：week number、title、教材、URL cards。
  - `magic-mvp-class-access`：各班開放 week ids。
- **備份**：PITR enabled。AWS 官方文件說明 PITR 是全託管連續備份，可在設定保留期內以秒級精度還原；目前服務支援 1–35 天保留期。
- **還原 SOP**：
  1. 不要直接覆蓋 production table。
  2. 從 DynamoDB Console 或 CLI restore 到新表，例如 `magic-mvp-users-restore-YYYYMMDD-HHMM`。
  3. 比對復原資料與目前 production table。
  4. 若只需修復少數 item，將 item 寫回 production table。
  5. 若需全表切換，先規劃停機窗口，更新 Terraform / Lambda env 或資料搬遷策略。
- **驗證指令範例**：
  ```bash
  aws dynamodb describe-continuous-backups --table-name magic-mvp-users
  aws dynamodb describe-continuous-backups --table-name magic-mvp-weeks
  aws dynamodb describe-continuous-backups --table-name magic-mvp-class-access
  ```

### 4.3 S3 內容與前端 bucket

- **Bucket**：
  - `magic-mvp-content-<account>`：private教材內容，Lambda 產生 signed URL。
  - `magic-mvp-app-frontend-<account>`：student/teacher PWA static assets。
  - `magic-mvp-admin-frontend-<account>`：admin console static assets。
- **備份**：三個 bucket 都啟用 Versioning。AWS S3 Versioning 可保留、取回與復原同一 object 的多個版本。
- **還原 SOP（單一物件）**：
  1. 在 S3 Console 開啟 Show versions。
  2. 找到要回復的 key，例如 `magic-pages/讀心術.html` 或 `admin.html`。
  3. 下載舊版本確認內容。
  4. 用舊版本重新上傳為最新版本，或刪除錯誤的新版本使前版成為目前版本。
  5. 若是 frontend/admin bucket，執行 CloudFront invalidation。
- **發佈 SOP**：
  ```bash
  ./scripts/fetch-magic-pages.sh
  ./scripts/deploy-static.sh
  ./scripts/smoke-test.sh
  ```

### 4.4 Lambda API

- **用途**：承接 app/admin/teacher/student API，讀寫 DynamoDB、產生 S3 signed URL、同步 Cognito。
- **備份**：程式碼以 git commit/tag 管理；prod v1.0 對應 local tag `v1.0`。
- **Log retention**：CloudWatch Log Group `/aws/lambda/magic-mvp-api` 保留 14 天。
- **告警**：任一 5 分鐘 period Lambda `Errors >= 1` 觸發 SNS email。
- **Rollback SOP**：
  ```bash
  git checkout v1.0
  cd infra
  terraform plan
  terraform apply
  cd ..
  ./scripts/smoke-test.sh
  ```

### 4.5 API Gateway

- **用途**：HTTP API，JWT authorizer 驗 Cognito access token。
- **備份**：無資料狀態；由 Terraform 重建。
- **告警**：API Gateway `5xx >= 1` / 5 分鐘會通知 SNS。
- **排障順序**：
  1. `./scripts/smoke-test.sh` 確認 API endpoint 存活。
  2. CloudWatch Alarm 看是 5xx 還是 Lambda Errors。
  3. Lambda log 找 `api_error` / `unexpected_error`。
  4. 檢查 Cognito issuer/audience 是否和 frontend config 一致。

### 4.6 CloudFront + ACM

- **用途**：app/admin HTTPS 靜態入口。
- **備份**：無資料狀態；distribution 由 Terraform 重建，內容由 S3 versioning / git 發佈還原。
- **日常維護**：
  - 每次 deploy-static 後確認 invalidation completed。
  - 若 DNS / certificate 異常，檢查 `infra/acm.tf` 與 Route 53 validation records。
- **Smoke URLs**：以 `terraform output` 為準；目前部署曾輸出：
  - App CloudFront：`<app-cloudfront-domain>`
  - Admin CloudFront：`<admin-cloudfront-domain>`

### 4.7 CloudWatch / SNS 告警

- **SNS topic**：`magic-mvp-alerts`。
- **Email endpoint**：`var.initial_admin_email`。
- **告警**：
  - `magic-mvp-lambda-errors`：Lambda `Errors` sum >= 1 / 300 秒。
  - `magic-mvp-api-5xx`：API Gateway `5xx` sum >= 1 / 300 秒。
- **處理 SLA 建議**：上課時間 15 分鐘內確認，非上課時間 4 小時內確認。
- **處理紀錄**：每次 ALARM 都應在維護紀錄中記錄時間、原因、處理方式、是否需要修 code。

### 4.8 AWS Budgets / Cost

- **Budget**：`magic-mvp-monthly-budget`，依 `magic=true` 成本標籤過濾。
- **通知門檻**：Actual cost > 10 / 20 / 50 USD。
- **每月維護**：
  - 確認 Cost Allocation Tag `magic` 仍 active。
  - 成本異常優先查 CloudFront request、S3 storage versions、DynamoDB on-demand、Lambda invocation。

### 4.9 Terraform state / IaC

- **目前狀態**：本 repo 使用本地 Terraform state；`infra/terraform.tfvars`、`*.tfstate` 不應提交。
- **每次 apply 後**：
  1. 執行 `terraform plan` 確認 no changes。
  2. 將 state 備份到安全位置（不要放公開 repo）。
  3. 若多人維護，優先導入 S3 backend + state lock。

## 5. 事故 Runbook

### 5.1 學員/老師資料誤刪

1. 立刻停止進一步批次操作。
2. 確認誤刪時間點（Asia/Taipei 與 UTC 都記錄）。
3. 使用 DynamoDB PITR 還原到新表。
4. 從新表取回受影響 user/week/class-access item。
5. 寫回 production table 後請 admin/teacher 驗證 UI。
6. 記錄事故與防呆改善。

### 5.2 教材 HTML 或 URL card 錯誤

1. 若是 S3 HTML 內容錯誤：用 S3 Versioning 找前一版，先下載比對。
2. 還原 S3 物件或重新跑 `./scripts/deploy-static.sh`。
3. 若是 URL card/週次設定錯誤：從 teacher/admin UI 修正；必要時用 DynamoDB PITR 找舊 item。
4. 確認 student week card 只顯示名稱，不顯示 URL/副檔名。

### 5.3 API 5xx 或 Lambda Error

1. 看 CloudWatch alarm 觸發時間。
2. 到 `/aws/lambda/magic-mvp-api` 查同時段 error log。
3. 確認是資料錯誤、Cognito 權限、S3 signed URL、或 code regression。
4. 若是 regression，回到上一個穩定 git tag/commit，重新 package/apply/deploy。
5. `./scripts/smoke-test.sh` 通過後關閉事件。

### 5.4 前端白屏或管理頁無法載入

1. 打開 CloudFront app/admin URL 確認是否為 403/404/JS error。
2. 重新執行 `npm --prefix frontend run build`。
3. 重新跑 `./scripts/deploy-static.sh` 並等 invalidation completed。
4. 若只是一個檔案錯誤，可用 S3 Versioning 還原前一版 asset/html。
5. 清瀏覽器 cache 或以 incognito 測試。

## 6. 變更管理規則

- 所有 infra 變更都要跑：
  ```bash
  terraform -chdir=infra fmt -recursive -check
  terraform -chdir=infra validate
  terraform -chdir=infra plan
  ```
- 所有 app/backend 變更都要跑：
  ```bash
  backend/.venv/bin/pytest -q
  backend/.venv/bin/ruff check backend
  npm --prefix frontend run build
  ./scripts/smoke-test.sh
  ```
- production release 後更新：
  - `docs/release-checklist.md`
  - 本文件 `docs/cloud-maintenance.md`
  - git tag / release note

## 7. 官方參考

- DynamoDB PITR：AWS 官方文件說明 Point-in-Time Recovery 可提供連續備份與秒級還原點，並支援 1–35 天 recovery period。<https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html>
- DynamoDB configurable PITR period 公告：<https://aws.amazon.com/about-aws/whats-new/2025/01/amazon-dynamodb-configurable-point-in-time-recovery-periods/>
- S3 Versioning：AWS 官方文件說明 Versioning 可保存、取回與還原同一 bucket 內每個 object 的多個版本。<https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html>
- S3 restore previous versions：<https://docs.aws.amazon.com/AmazonS3/latest/userguide/RestoringPreviousVersions.html>
