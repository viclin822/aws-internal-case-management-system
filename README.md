# AWS 雲端內部案件管理系統
### AWS Cloud-Based Internal Case Management System

> 🚀 自主開發的雲端全端專案，結合 4 年客服營運實戰經驗，完整實作 AWS 多服務架構部署。

**線上展示：** http://13.54.242.189:5000

---

## 📌 專案背景

本人具備 4 年以上平台客服與營運支援經驗，目前轉職 IT 領域，就讀國立臺北商業大學資訊管理系（2026/07 畢業）並同步參加 TibaMe AWS 雲端工程師培訓。

此專案為應徵期間**自主開發**的實戰作品，非課程指定作品。結合過去客服流程的第一線經驗，獨立設計並實作此內部案件管理系統，涵蓋雲端架構設計、資料庫設計、後端開發與 AWS 多服務整合全流程。

---

## 🏗️ 系統架構

```
使用者瀏覽器
     │
     ▼
[ EC2 - Flask App ]  ←── systemd 自動管理服務
     │
     ├──► [ RDS - MySQL 8.0 ]   案件 / 使用者 / 留言資料
     │
     └──► [ S3 Bucket ]         附件儲存（Presigned URL 安全存取）
              ▲
         IAM Role（EC2 綁定，無需 Access Key）
```

| AWS 服務 | 用途 |
|----------|------|
| EC2（t3.micro, Ubuntu 24.04） | 部署 Flask 應用程式 |
| RDS（MySQL 8.0, db.t3.micro） | 關聯式資料庫，Multi-AZ 可擴充 |
| S3 | 附件儲存，Presigned URL 控制存取權限 |
| IAM Role | EC2 綁定 Role，最小權限原則，無硬編碼金鑰 |
| Elastic IP | 固定對外 IP，避免重啟後 IP 變動 |
| Security Group | 最小化開放埠（SSH 22、HTTP 5000） |

---

## ⚙️ 技術堆疊

| 層級 | 技術 |
|------|------|
| 後端框架 | Python 3.12 / Flask |
| 資料庫 | MySQL 8.0（AWS RDS） |
| 雲端平台 | AWS EC2 / RDS / S3 / IAM |
| 服務管理 | systemd（自動重啟） |
| 附件儲存 | AWS S3 + boto3 + Presigned URL |
| 前端 | HTML / CSS / Jinja2 Template |
| 版本控制 | Git / GitHub |
| 環境設定 | python-dotenv（.env 分離敏感資訊） |

---

## 🔐 資安設計重點

- **IAM Role 綁定 EC2**：不使用 Access Key，符合 AWS 最小權限原則
- **S3 全私有**：Bucket 封鎖所有公開存取，附件透過 Presigned URL（15分鐘時效）存取
- **環境變數分離**：資料庫密碼、Secret Key 透過 `.env` 管理，不進版本控制
- **RBAC 權限控管**：三種角色各自有獨立的存取限制

---

## 👥 系統功能

### 角色權限（RBAC）

| 角色 | 權限說明 |
|------|----------|
| **Admin（管理員）** | 完整權限，查看所有案件、管理使用者 |
| **Agent（客服人員）** | 查看所有案件、更新狀態、新增留言 |
| **Submitter（申請者）** | 建立案件、查看自己的案件、新增留言 |

### 案件管理
- 建立、查看、編輯案件
- 狀態流程：`待處理` → `處理中` → `待追蹤` → `已結案`
- 優先級設定（高 / 中 / 低）
- 問題類別分類（8 種）
- 是否歸還點數標記

### 附件管理
- 支援圖片（jpg/png/gif）、影片（mp4/mov）、文件（pdf/doc/docx）
- 上傳至 AWS S3，透過 Presigned URL 安全存取
- 建立工單時可上傳，詳情頁可補傳或刪除

### 留言與稽核
- 案件留言紀錄
- 狀態變更自動寫入稽核日誌（`case_status_logs`）

---

## 🗄️ 資料庫設計

| 資料表 | 說明 |
|--------|------|
| `cases` | 主要案件資料，含標題、分類、狀態、優先級等 |
| `users` | 使用者帳號、角色、部門 |
| `case_comments` | 案件留言紀錄 |
| `case_status_logs` | 狀態變更稽核日誌（含操作者、時間戳） |
| `case_attachments` | 附件元資料（S3 Key、原始檔名、類型） |

---

## 🚀 本機安裝與執行

```bash
# 1. Clone 專案
git clone https://github.com/viclin822/aws-internal-case-management-system.git
cd aws-internal-case-management-system

# 2. 建立虛擬環境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝套件
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 填入資料庫與 S3 設定

# 5. 初始化資料庫
python3 init_db.py

# 6. 啟動應用
python app.py
```

### 環境變數說明（.env）

```
SECRET_KEY=your-secret-key
DB_HOST=your-rds-endpoint
DB_PORT=3306
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_NAME=ticketdb
S3_BUCKET_NAME=your-bucket-name
S3_REGION=ap-southeast-2
```

---

## 🌐 線上展示

- **系統網址**：http://13.54.242.189:5000
- **測試帳號**：

| 角色 | 帳號 | 密碼 |
|------|------|------|
| Admin | admin | admin123 |
| Agent | agent01 | agent123 |
| Submitter | submitter01 | submitter123 |

---

## 👨‍💻 開發者

**林峻毅（Vic Lin）**
- 🎓 國立臺北商業大學 資訊管理系（2026/07 畢業）
- ☁️ TibaMe AWS 雲端工程師培訓（2026/02 - 2026/07）
- 💼 4 年以上平台客服與營運支援經驗
- 🐙 GitHub：https://github.com/viclin822
