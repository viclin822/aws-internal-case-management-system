# AWS 雲端內部案件管理系統

**AWS Internal Case Management System**

> 這是一套針對內部案件協作流程設計的雲端管理系統，  
> 主要服務對象為業務、客服與主管，解決原本以 Google 表單與表格分散追蹤案件時，  
> 在權限分流、處理進度追蹤、留言協作、附件整合與歷程管理上的不便。

---

## 專案簡介

本專案為一套以真實工作場景為基礎發想的內部案件管理系統，  
聚焦於「案件提報、案件處理、狀態追蹤、站內通知、權限控管、統計報表」等核心需求。

系統依不同使用角色區分權限範圍：

- **Submitter（業務）**：提交案件、查看自己案件、追蹤進度
- **Agent（客服）**：查看全部案件、更新狀態、留言協作、處理案件
- **Admin（主管）**：完整權限、KPI 報表、管理使用者

本專案整合 AWS EC2、RDS、S3、CloudWatch、SNS 等服務，  
實作從需求發想到資料庫設計、功能開發、雲端部署與基礎維運監控的完整流程。

---

## 專案動機

目前第一線客服與業務回報流程，常透過 Google 表單提交、表格追蹤進度。  
雖然能完成基本紀錄，但在角色權限分流、案件狀態管理、留言協作、附件整合與歷程追蹤上仍有整合空間。

因此，我以真實工作場景為基礎，獨立設計並實作此內部案件管理系統，  
希望將原本分散的提報、處理與追蹤流程整合為單一平台。

---

## 專案定位

本專案並非課程指定作業，而是在 AWS 雲端工程師培訓正式個人專題啟動前，  
為驗證自己在系統開發與維運方向的能力，主動完成的實作作品。

專案重點不只是完成功能頁面，而是同時納入：

- 角色權限控管（RBAC）
- 案件流程設計
- 附件儲存整合
- 狀態歷程記錄
- 站內通知機制
- AWS 雲端部署
- CloudWatch 監控與 SNS 告警

---

## 系統功能

### 角色權限控管（RBAC）

| 角色 | 說明 |
|------|------|
| Submitter（業務） | 提交案件、查看自己的案件、新增外部留言 |
| Agent（客服） | 處理所有案件、新增內外部留言、更新狀態 |
| Admin（主管） | 全部權限 + KPI 報表 + 管理使用者 |

### 案件管理

- 工單建立與追蹤
- 狀態管理（待處理 / 處理中 / 待追蹤 / 已結案）
- 問題分類與優先級設計
- 歸還點數狀態標記
- 附件上傳（整合 S3 Presigned URL）
- 留言協作（外部留言 / 內部備註）
- 狀態歷程紀錄

### 管理功能

- Admin KPI 報表（各客服已結案件數量統計）
- 問題分類圓餅圖（含日期區間篩選）
- 使用者管理

### 站內通知系統

- 導覽列鈴鐺圖示，即時顯示未讀通知紅點
- 新案件建立 → 通知 Agent / Admin
- 案件狀態更新 → 通知 Submitter
- 新增留言 → 通知相關人員
- 歸還點數狀態更新 → 通知 Submitter
- 通知分類標籤（新案件 / 狀態更新 / 新留言 / 歸還點數）
- 點擊通知可跳轉對應案件
- 一鍵全部已讀
- 通知中心頁面（查看完整歷史通知）

---

## 系統架構

![系統架構圖](docs/architecture.png)

### 架構說明

系統採用 AWS 雲端部署，主要架構如下：

- 使用者透過瀏覽器以 HTTP 存取系統
- 請求先進入 EC2 上的 **Nginx**
- Nginx 反向代理至 **Gunicorn**
- Gunicorn 執行 **Flask Web Application**
- 應用程式連接 **AWS RDS MySQL**
- 附件檔案透過 **AWS S3 Presigned URL** 上傳
- 主機與應用監控透過 **CloudWatch**
- 異常告警透過 **Amazon SNS** 發送通知

### AWS 服務架構

```text
使用者（瀏覽器）
    │ HTTP port 80
    ▼
┌─────────────────────────────── AWS VPC ───────────────────────────────┐
│  ┌─────────────────── Public Subnet ──────────────────────────────┐   │
│  │  ┌─────────────── Amazon EC2（t2.micro）──────────────────┐    │   │
│  │  │  Nginx（反向代理）port 80                             │    │   │
│  │  │        │                                               │    │   │
│  │  │        ▼                                               │    │   │
│  │  │  Gunicorn（WSGI Server）port 5000                     │    │   │
│  │  │        │                                               │    │   │
│  │  │        ▼                                               │    │   │
│  │  │  Flask Web Application（app.py）                      │    │   │
│  │  │                                                        │    │   │
│  │  │  IAM Role ／ systemd（aws-ticket.service）            │    │   │
│  │  └────────────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────── Private Subnet ─────────────────────────────┐   │
│  │  Amazon RDS MySQL（SG: port 3306，EC2 專屬存取）               │   │
│  └────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
         │ Presigned URL                    │ 指標送出
         ▼                                  ▼
   Amazon S3                        Amazon CloudWatch
   vic-ticket-attachments           AWS-CaseSystem-Monitor 儀表板
   （VPC 外，全球服務）              CPU ／ 狀態檢查警報
                                          │ 警報觸發
                                          ▼
                                    Amazon SNS
                                    Email 告警通知
```

---

## 技術棧

| 類別 | 技術 |
|------|------|
| 後端 | Python Flask |
| WSGI 伺服器 | Gunicorn |
| 容器化 | Docker / Docker Compose |
| 資料庫 | AWS RDS MySQL 8.4 |
| 檔案儲存 | AWS S3（Presigned URL） |
| 伺服器 | AWS EC2 t2.micro（Ubuntu 24.04） |
| 反向代理 | Nginx |
| 服務管理 | systemd |
| 權限控管 | AWS IAM Role / Policy |
| 網路 | AWS VPC / Public & Private Subnet / Security Group |
| 監控 | AWS CloudWatch + Amazon SNS |
| 版本控管 | Git / GitHub |

---

## 系統畫面展示

### Submitter（業務）

#### 1. 登入後首頁
說明：顯示登入者資訊、角色權限、快捷操作與案件統計；Submitter 僅可查看自己提報的案件。

![Submitter Dashboard](docs/submitter-dashboard.png)

#### 2. 案件列表
說明：支援案件列表查詢、狀態篩選、關鍵字搜尋與問題類別占比圖表，方便業務快速追蹤自己提報的案件。

![Submitter Ticket List](docs/submitter-ticket-list.png)

#### 3. 新增案件
說明：提供案件提報入口，支援案件標題、問題類別、學員資訊、Tutor、案件內容說明、附件上傳與是否歸還點數等欄位。

![Submitter Create Ticket](docs/submitter-create-ticket.png)

#### 4. 自動優先級判斷
說明：依問題類別自動帶出建議優先級，減少提交者判斷負擔，並讓客服能快速辨識需要優先處理的案件。

![Submitter Priority Logic](docs/submitter-priority-logic.png)

#### 5. 案件明細
說明：可查看案件基本資料、附件、留言記錄與狀態歷程，完整呈現案件處理過程。

![Submitter Ticket Detail](docs/submitter-ticket-detail.png)

---

### Agent（客服）

#### 1. 登入後首頁
說明：客服角色可查看全部案件，並透過首頁快速進入案件列表與處理流程。

![Agent Dashboard](docs/agent-dashboard.png)

#### 2. 案件列表
說明：客服可查看全部案件，並透過篩選與搜尋快速定位案件，協助案件分流與追蹤。

![Agent Ticket List](docs/agent-ticket-list.png)

#### 3. 案件明細與處理功能
說明：客服可於案件明細頁更新案件狀態、調整是否歸還點數，並新增內部備註或對外留言。

![Agent Ticket Detail](docs/agent-ticket-detail.png)

#### 4. 站內通知提醒
說明：新案件、新留言等事件會透過站內提醒通知客服，降低漏接案件風險。

![Agent Notifications](docs/agent-notifications.png)

---

### Admin（主管）

#### 1. 登入後首頁
說明：主管角色除可查看全部案件外，另提供 KPI 報表等管理功能入口。

![Admin Dashboard](docs/admin-dashboard.png)

#### 2. KPI 報表
說明：主管可依日期區間查看客服人員已結案件數量統計，作為追蹤處理量與管理參考。

![Admin KPI Report](docs/admin-kpi-report.png)

#### 3. 案件明細與內部資訊
說明：主管可查看案件明細與客服端可見的內部備註資訊，作為案件追蹤、溝通與管理參考；此類內部資訊不對提交者（業務）開放。

![Admin Ticket Detail](docs/admin-ticket-detail.png)

---

## CloudWatch 監控與維運

使用 AWS CloudWatch 建立 **AWS-CaseSystem-Monitor** 儀表板，  
集中追蹤主機效能與資源使用狀況，提升服務可觀測性與基本維運能力。

### 儀表板監控項目

- CPU Utilization：主機 CPU 使用率趨勢
- Network Traffic：NetworkIn / NetworkOut 流量
- EBS Read / Write Bytes：磁碟讀寫負載
- EC2 Status Checks：系統層與執行個體層健康狀態
- Alarm Overview：告警狀態總覽

### 告警設定

- `CPU-High-Alert`：CPU 使用率超過閾值時觸發
- `EC2-Status-Check-Failed`：EC2 狀態檢查失敗時觸發
- 整合 Amazon SNS，異常發生時自動發送 Email 通知

![CloudWatch Dashboard](docs/cloudwatch-dashboard.png)

---

## CI/CD 自動部署

本專案導入 GitHub Actions 建立自動部署流程，讓程式碼 push 後可自動部署至 AWS EC2，降低手動更新造成的遺漏與版本不一致問題。

### 部署流程

1. 開發完成後將程式碼 push 至 GitHub `main` 分支
2. GitHub Actions workflow 自動觸發
3. Workflow 透過 SSH 連線至 EC2
4. EC2 端執行 `git pull origin main` 取得最新版本
5. 執行 `sudo systemctl restart aws-ticket` 重新啟動應用服務

### 敏感資訊管理

部署所需連線資訊透過 GitHub Secrets 管理，不寫死於程式碼中：

| Secret 名稱 | 說明 |
|-------------|------|
| EC2_HOST | EC2 Elastic IP |
| EC2_USER | SSH 登入使用者名稱 |
| EC2_SSH_KEY | PEM 私鑰內容 |

### 設定檔位置

`.github/workflows/deploy.yml`

---

## Health Check 與維運設計

本專案提供 `/health` 健康檢查端點，回傳 JSON 格式，同時確認應用程式、資料庫與檔案儲存的連線狀態。

### 回傳範例
```json
{"db": "connected", "s3": "connected", "status": "ok"}
```

### 檢查項目

| 項目 | 說明 |
|------|------|
| status | Flask 應用程式是否正常運作 |
| db | RDS MySQL 連線是否正常 |
| s3 | S3 儲存桶連線是否正常 |

### 用途

- 部署後快速確認服務是否正常上線
- 可搭配外部監控工具定期呼叫做存活檢查
- 展現應用層健康檢查思維，不只確認主機存活，也驗證後端服務連線狀態

### 目前維運設計整體架構

| 元件 | 角色 |
|------|------|
| Nginx | 反向代理，統一接收外部 HTTP 請求 |
| Gunicorn | WSGI Server，承接 Flask 應用服務 |
| systemd | 管理服務啟動與重啟，降低異常中斷風險 |
| CloudWatch | 集中查看主機與系統指標 |
| SNS | 告警觸發時發送 Email 通知 |
| IAM Role | 讓 EC2 安全存取 AWS 資源，避免長期金鑰外洩 |
| /health | 應用層健康檢查，同時驗證 DB 與 S3 連線 |

---

## Backup / Recovery 設計

在維運設計上，本專案同時考慮資料備份與異常後的復原需求。

### 資料備份設計

本專案的資料主要分為兩類：

**結構化資料**

案件、留言、通知、使用者等資料儲存在 Amazon RDS MySQL，啟用自動備份與 KMS 加密。

**附件資料**

案件附件儲存在 Amazon S3，透過 Presigned URL 上傳，與主機本身解耦，降低 EC2 磁碟負擔。

### Recovery 思維

| 異常情境 | 對應處理方式 |
|----------|-------------|
| 應用服務異常 | systemd 自動重啟服務 |
| 主機異常 | 重新部署應用程式並接回 RDS / S3 |
| 資料庫層異常 | 依 RDS 自動備份機制進行還原 |
| 附件資料 | 集中於 S3，不受應用程式重啟影響 |

### 設計價值

- 應用程式、資料庫、附件儲存三層分離
- 主機故障時資料不隨之消失
- 符合「應用層 / 資料層 / 儲存層分離」的維運思維
- 有利於後續擴充、搬遷與災難復原規劃

---

## 部署資訊

| 項目 | 說明 |
|------|------|
| 雲端平台 | AWS ap-southeast-2（Sydney） |
| EC2 | t2.micro / Ubuntu 24.04 / Elastic IP |
| 資料庫 | RDS MySQL（Private Subnet，port 3306） |
| 備份 | RDS 自動備份啟用 / KMS 加密 |
| 儲存 | S3 vic-ticket-attachments |

> 線上展示環境可能因部署調整或成本控管暫時關閉，若無法連線，請以 GitHub 原始碼、系統架構圖與畫面截圖為主。

---

## 本機開發環境設定

```bash
# 1. clone 專案
git clone https://github.com/viclin822/aws-internal-case-management-system.git
cd aws-internal-case-management-system

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env

# 5. 啟動應用
python app.py
```

### Docker 啟動（選用）

```bash
docker compose up --build
docker compose up --build -d
```

---

## 專案結構

```text
aws-internal-case-management-system/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── logs/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── ticket_list.html
│   ├── ticket_detail.html
│   ├── create_ticket.html
│   ├── edit_ticket.html
│   ├── notifications.html
│   └── admin_stats.html
└── docs/
    ├── architecture.png
    ├── cloudwatch-dashboard.png
    ├── submitter-dashboard.png
    ├── submitter-ticket-list.png
    ├── submitter-create-ticket.png
    ├── submitter-priority-logic.png
    ├── submitter-ticket-detail.png
    ├── agent-dashboard.png
    ├── agent-ticket-list.png
    ├── agent-ticket-detail.png
    ├── agent-notifications.png
    ├── admin-dashboard.png
    ├── admin-kpi-report.png
    └── admin-ticket-detail.png
```

---

## 專案亮點

- 以真實工作場景為基礎發想，而非單純練習型題目
- 實作 Submitter / Agent / Admin 三角色權限設計
- 完成案件建立、追蹤、留言、通知、歷程記錄等完整流程
- 整合 AWS EC2、RDS、S3、CloudWatch、SNS
- 使用 Nginx + Gunicorn + Flask 完成部署
- 導入 CloudWatch 與 SNS 建立監控儀表板與自動化告警機制
- 具備從需求分析、資料庫設計、後端開發、部署到維運的完整實作流程
- 導入 GitHub Actions 實現 push 觸發自動部署至 EC2
- 提供 /health 端點同時檢查 DB 與 S3 連線狀態

---

## 作者

**Vic Lin（林峻毅）**  
國立臺北商業大學 資訊管理系  
緯育 TibaMe AWS 雲端工程師培訓  
GitHub：[@viclin822](https://github.com/viclin822)
