# AWS Serverless Architecture — Magic Learning Platform

這個 repository 是一個以 AWS serverless 為核心的教學平台架構範例，包含前端 PWA、管理介面、Lambda API、Terraform 基礎設施，以及維運文件。專案重點放在低維運成本、可控權限、教材內容保護、週次課程管理與 production-lite 防呆保護。

## Repo 內容

| 目錄 | 說明 |
| --- | --- |
| `frontend/` | Student / Teacher PWA 與 Admin Console 的 TypeScript/Vite 前端。 |
| `backend/` | Python Lambda API，負責 Cognito JWT 驗證、角色授權、週次教材、班級開放週次、裝置授權與 admin 管理。 |
| `infra/` | Terraform AWS serverless 架構，包含 Cognito、API Gateway、Lambda、DynamoDB、S3、CloudFront、Route 53、ACM、CloudWatch、SNS 與 AWS Budgets。 |
| `docs/` | 架構圖、教師流程圖、雲端維護書、部署與 release checklist。 |
| `scripts/` | 靜態資產發佈、Lambda package、smoke check 與教材同步相關腳本。 |

## Product Workflow

平台以三個角色切分操作流程：

1. **Admin**：建立與維護帳號、設定角色與班級、重設學員裝置授權、刪除帳號、管理週次與班級開放狀態。
2. **Teacher**：設定每週主題名稱、選擇教材內容、建立 URL card、決定各班可見週次。
3. **Student**：登入後只能看到自己班級已開放的週次，教材與 URL card 以 card 呈現，點選後以新分頁載入內容。

## AWS Architecture

架構採用 serverless 與受管服務：

- **CloudFront + S3**：分別承載 app/admin 靜態前端，使用 Origin Access Control 保護 bucket。
- **Cognito**：管理 Admin / Teacher / Student 登入與群組角色。
- **API Gateway + Lambda**：統一承接前端 JWT API request，Lambda 依角色與班級執行授權。
- **DynamoDB**：保存 users、weeks、class-access 三類核心資料，啟用 PITR 與 deletion protection。
- **S3 Content Bucket**：保存 private 教材內容，由 Lambda 簽發短效 URL。
- **CloudWatch + SNS**：追蹤 Lambda/API error 與告警通知。
- **AWS Budgets**：以 `magic=true` cost allocation tag 管理 production-lite 成本邊界。

![AWS Architecture](docs/architecture/aws%20-architecture.png)

## Operational Guardrails

Terraform 預設使用 `protect_identity_data = true` 保護重要服務：

- Cognito User Pool deletion protection 與 Terraform `prevent_destroy`。
- DynamoDB PITR、deletion protection 與 Terraform `prevent_destroy`。
- S3 bucket versioning、`force_destroy = false` 與 Terraform `prevent_destroy`。
- CloudFront `retain_on_delete` 與 Terraform `prevent_destroy`。
- API Gateway、Lambda、Lambda log group、ACM certificate 使用 Terraform `prevent_destroy`。

詳細維運責任、備份時間與事故處理請看 [`docs/cloud-maintenance.md`](docs/cloud-maintenance.md)。
