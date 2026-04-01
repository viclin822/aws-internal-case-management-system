# AWS 雲端內部案件管理系統

**AWS Internal Case Management System**

> 結合第一線客服工作場景，獨立設計並實作的雲端內部案件管理系統，  
> 涵蓋雲端架構設計、資料庫設計、後端開發、AWS 多服務整合與監控全流程。

---

## 專案背景

本人具備近 5 年平台客服與營運支援經驗，現轉職 IT 領域，  
就讀國立臺北商業大學資訊管理系（預計 2026 年 7 月畢業），  
並同步參與緯育 TibaMe AWS 雲端工程師培訓計畫。

此專案並非課程指定作品（TibaMe 個人專題預計 2026/05 後啟動），  
而是基於第一線客服工作經驗，獨立發起並完整實作的雲端系統。

長期接觸案件處理流程，深刻理解現有工具在追蹤、協作與歷程記錄上的痛點，  
因此自行設計並建構此內部案件管理系統，整合多項 AWS 服務，完整實作從開發到部署維運的全流程。

---

## 系統功能

### 角色權限控管（RBAC）
| 角色 | 說明 |
|------|------|
| Submitter（業務） | 提交案件、查看自己的案件、新增外部留言 |
| Agent（客服） | 處理所有案件、新增內外部留言、更新狀態 |
| Admin（主管） | 全部權限 ＋ KPI 報表 ＋ 管理使用者 |

### 案件管理
- 工單建立與追蹤
- 狀態管理（待處理 / 處理中 / 待追蹤 / 已結案）
- 問題分類 → 自動優先度指派
- 歸還點數狀態標記
- 內部留言（僅 Agent / Admin 可見）
- 外部留言（Submitter 可見）
- 附件上傳（整合 S3 Presigned URL）

### 管理功能
- Admin KPI 報表（各客服案件數量、長條圖）
- 問題分類圓餅圖（含日期篩選）
- 使用者管理

### 站內通知系統
- 導覽列鈴鐺圖示，即時顯示未讀通知數量紅點
- 觸發條件：
  - 新案件建立 → 通知所有 Agent / Admin
  - 案件狀態更新 → 通知該案件的 Submitter
  - 新增留言 → 通知相關人員（外部留言通知 Submitter，所有留言通知 Agent）
  - 歸還點數狀態更新 → 通知 Submitter
- 通知分類標籤（新案件 / 狀態更新 / 新留言 / 歸還點數）
- 點擊通知直接跳轉對應案件
- 一鍵全部已讀
- 通知中心頁面（查看全部歷史通知）

---

## 系統架構

![架構圖](docs/architecture.png)

詳細架構請參考：[docs/architecture.html](docs/architecture.html)

### AWS 服務架構

```
使用者（瀏覽器）
    │ HTTP port 80
    ▼
┌─────────────────────────────── AWS VPC ───────────────────────────────┐
│  ┌─────────────────── Public Subnet ──────────────────────────────┐   │
│  │  ┌─────────────── Amazon EC2（t3.micro）──────────────────┐    │   │
│  │  │  Nginx（反向代理）port 80 → Flask port 5000            │    │   │
│  │  │  Flask Web Application（app.py）                        │    │   │
│  │  │  IAM Role ／ systemd（aws-ticket.service）             │    │   │
│  │  └────────────────────────────────────────────────────────┘    │   │
│  └────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────── Private Subnet ─────────────────────────────┐   │
│  │  Amazon RDS MySQL（SG: port 3306，EC2 專屬存取）               │   │
│  └────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
         │ Presigned URL                    │ 指標送出
         ▼                                  ▼
   Amazon S3                        Amazon CloudWatch
   vic-ticket-attachments           EC2-Monitor 儀表板
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
| 資料庫 | AWS RDS MySQL 8.4.7 |
| 檔案儲存 | AWS S3（Presigned URL） |
| 伺服器 | AWS EC2 t3.micro（Ubuntu 24.04） |
| 反向代理 | Nginx |
| 服務管理 | systemd |
| 權限控管 | AWS IAM Role / Policy |
| 網路 | AWS VPC / Public & Private Subnet / Security Group |
| 監控 | AWS CloudWatch + Amazon SNS |
| 版本控管 | Git / GitHub |

---

## CloudWatch 監控與維運

使用 AWS CloudWatch 建立 EC2 監控儀表板（AWS-CaseSystem-Monitor），  
集中追蹤主機效能與資源使用狀況，實作雲端系統的可觀測性。

**儀表板監控項目：**
- CPU Utilization — 主機 CPU 使用率趨勢
- Network Traffic — NetworkIn / NetworkOut 流量
- EBS Read / Write Bytes — 磁碟讀寫負載
- Network Packets — 封包進出數量
- EC2 Status Checks — 系統層與執行個體層健康狀態
- Alarm Overview — 告警狀態總覽

**告警設定：**
- `CPU-High-Alert`：CPU 使用率超過閾值時觸發
- `EC2-Status-Check-Failed`：EC2 狀態檢查失敗時觸發
- 兩者皆整合 Amazon SNS，異常發生時自動發送 Email 通知

![CloudWatch 監控儀表板](docs/cloudwatch-dashboard.png)

---

## 部署資訊

| 項目 | 說明 |
|------|------|
| 雲端平台 | AWS ap-southeast-2（雪梨） |
| EC2 | t3.micro / Ubuntu 24.04 / Elastic IP |
| 對外存取 | http://13.54.242.189 |
| 資料庫 | RDS MySQL（Private Subnet，port 3306） |
| 備份 | RDS 自動備份啟用 ／ KMS 加密 |
| 儲存 | S3 vic-ticket-attachments |

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

# 4. 設定環境變數（複製 .env.example 並填入）
cp .env.example .env

# 5. 啟動應用
python app.py
```

---

## 專案結構

```
aws-internal-case-management-system/
├── app.py                  # 主應用程式
├── requirements.txt        # 依賴套件
├── .env.example            # 環境變數範本
├── templates/              # Jinja2 HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── tickets.html
│   ├── ticket_detail.html
│   ├── create_ticket.html
│   ├── edit_ticket.html
│   └── admin_stats.html
├── static/                 # 靜態資源
└── docs/                   # 專案文件
    ├── architecture.html   # 系統架構圖
    └── cloudwatch-dashboard.png
```

---

## 作者

**Vic Lin（林峻毅）**  
國立臺北商業大學 資訊管理系  
緯育 TibaMe AWS 雲端工程師培訓  
GitHub：[@viclin822](https://github.com/viclin822)
