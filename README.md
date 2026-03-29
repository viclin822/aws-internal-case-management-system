# AWS 雲端內部案件管理系統

## 專案簡介

本專案為模擬企業內部客服案件管理流程所開發的 Web 應用系統，部署於 AWS EC2，採用 Flask + MySQL 架構，實作角色權限控管、案件生命週期管理、留言紀錄與稽核日誌等功能。

---

## 系統功能

### 角色權限（RBAC）
- **Submitter（申請者）**：建立案件、查看自己的案件、新增留言
- **Agent（客服人員）**：查看所有案件、更新案件狀態、新增內部/外部留言
- **Admin（管理員）**：完整權限，包含刪除案件、管理使用者

### 案件管理
- 建立、查看、編輯、刪除案件
- 案件狀態流程：待處理 → 處理中 → 待確認 → 已結案
- 優先級設定（高 / 中 / 低）
- 問題類別分類

### 留言與稽核
- 支援對外可見 / 內部備註兩種留言類型
- 狀態變更自動寫入稽核日誌（case_status_logs）
- 附件管理（case_attachments）

---

## 技術架構

| 層級 | 技術 |
|------|------|
| 後端框架 | Python Flask |
| 資料庫 | MySQL 8.0 |
| 雲端平台 | AWS EC2（Ubuntu 24.04） |
| 服務管理 | systemd |
| 版本控制 | Git / GitHub |
| 前端 | HTML / CSS（Jinja2 Template） |

---

## AWS 服務應用

- **EC2**：部署 Flask 應用程式與 MySQL 資料庫
- **Security Group**：設定 SSH（22）、HTTP（5000）存取規則
- **Elastic IP**（可擴充）：固定對外 IP，避免重啟後 IP 變動

---

## 資料庫設計

| 資料表 | 說明 |
|--------|------|
| cases | 主要案件資料表 |
| users | 使用者帳號與角色 |
| case_comments | 案件留言紀錄 |
| case_status_logs | 狀態變更稽核日誌 |
| case_attachments | 附件資料 |

---

## 本機安裝與執行

1. Clone 專案
   git clone https://github.com/viclin822/aws-internal-case-management-system.git
   cd aws-internal-case-management-system

2. 建立虛擬環境
   python3 -m venv venv
   source venv/bin/activate

3. 安裝套件
   pip install -r requirements.txt

4. 設定資料庫（MySQL）
   python3 init_db.py

5. 啟動應用
   python app.py

---

## 線上展示

- **系統網址**：http://13.54.242.189:5000
- **測試帳號**：
  - Admin：admin / admin123
  - Agent：agent01 / agent123
  - Submitter：submitter01 / submitter123

---

## 開發者

**林峻毅（Vic Lin）**
- 國立臺北商業大學 資訊管理系 應屆畢業（2026/07）
- TibaMe AWS 雲端工程師培訓（2026/02 開始，2026/07 結訓）
- GitHub：https://github.com/viclin822

---

## 開發背景

本人具備 4 年以上平台客服與營運支援經驗，目前轉職 IT 領域。

由於 TibaMe 課程個人專題須於 2026/05/09 後才會正式開始，本專案並非課程指定作品，而是應徵期間自主開發的實戰作品集。結合過去 4 年客服流程的第一線經驗，獨立設計並實作此內部案件管理系統，涵蓋雲端部署、資料庫設計與後端開發全流程。
