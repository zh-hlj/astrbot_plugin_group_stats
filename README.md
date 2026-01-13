# AstrBot 群聊活跃统计插件（兼容 __init__.py）

📊 自动记录群聊活跃度，每日推送昨日数据，支持 WebUI 勾选群号 & 时间。

## 一键安装
1. 把本仓库整个文件夹放到 `AstrBot/data/plugins/`
2. 重启 AstrBot
3. WebUI → 插件管理 → 群聊活跃统计 → 设置 → 勾选要用的群 + 选择推送时间 → 保存即可

## 群内命令
- `/昨日活跃`  返回昨天数据
- `/今日统计`  返回今天实时数据

## 文件说明
- `__init__.py` 空文件，保证旧加载器也能识别
- 数据文件：`group_stats.db`（SQLite，插件目录内）

## 版本要求
AstrBot ≥ 3.4.0

# 支持

- [插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
