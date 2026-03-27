# AWS Internal Case Management System

AWS 雲端內部案件管理系統

## 專案說明
這個專案原本是我練習 Flask + MySQL 的基礎工單系統，先完成了工單新增、查詢、編輯、刪除等功能，並部署到 AWS EC2。

後續我打算把它升級成一套比較完整的「內部案件管理系統」，模擬公司內部提報、處理、追蹤案件的流程，也當作自己應徵系統開發及維運工程師的作品集專案。

## 目前已完成
- 工單列表 / 新增 / 詳情 / 編輯 / 刪除
- 關鍵字搜尋與狀態篩選
- RESTful API（GET / POST / PUT / DELETE）
- AWS EC2 部署
- MySQL 資料庫連線
- 環境變數設定

## 預計升級方向
- 三種角色：Submitter / Agent / Admin
- Submitter 只能查看自己建立的案件
- Agent 可查看全部案件、接手案件、更新狀態
- Admin 負責少量管理功能
- 附件上傳到 Amazon S3
- 區分「對外可見處理說明」與「內部備註」
- 補上案件操作紀錄
- 加入基本 log / 監控概念

## 使用技術
- Python
- Flask
- MySQL
- HTML / CSS
- AWS EC2
- Amazon S3（規劃中）

## 專案狀態
目前是第一版，先把基本工單功能完成，接下來會往 AWS 內部案件管理系統的方向繼續升級。