# 群聊监控插件项目说明

## 项目概述

这是一个为AstrBot开发的群聊监控插件，主要功能包括：
- 实时监控群聊在线人数
- 统计群聊活跃度（消息数量、活跃成员）
- 每日定时发送统计报告
- 提供Web配置接口

## 项目结构

```
group_monitor_plugin/
├── metadata.yaml          # 插件元数据
├── main.py                # 主插件类
├── web.py                 # Web API接口
├── __init__.py           # 包初始化
├── README.md             # 使用文档
├── config.example.json   # 配置示例
├── core/                 # 核心模块
│   ├── __init__.py
│   ├── database.py       # 数据库管理
│   ├── monitor.py        # 监控核心
│   └── scheduler.py      # 任务调度
└── web/                  # Web模块
    ├── __init__.py
    └── routes.py         # 路由定义
```

## 核心功能模块

### 1. 主插件类 (main.py)
- `GroupMonitorPlugin`: 插件主类，处理消息监听和指令响应
- 实现群聊消息监听、在线状态更新、活跃度统计
- 提供群聊统计和在线人数查询指令

### 2. 数据库管理 (core/database.py)
- `DatabaseManager`: 数据库管理器
- 管理在线成员记录、活跃度记录、群聊统计等数据表
- 提供数据查询、更新、清理等功能

### 3. 监控核心 (core/monitor.py)
- `GroupMonitor`: 群聊监控器
- 实现在线人数计算、活跃度统计、群聊健康度评估
- 缓存管理和数据同步

### 4. 任务调度 (core/scheduler.py)
- `ReportScheduler`: 报告调度器
- 配置和管理每日定时报告任务
- 支持数据清理和任务状态查询

### 5. Web接口 (web.py, web/routes.py)
- 提供HTTP API接口用于配置管理
- 支持获取/更新配置、查看状态、强制发送报告等

## 配置项

| 配置项 | 说明 |
|--------|------|
| send_time | 每日发送时间 (HH:MM) |
| target_groups | 目标群聊ID列表 |
| message_template | 消息模板 |
| enable_online_monitor | 启用在线监控 |
| enable_activity_summary | 启用活跃度统计 |
| activity_time_window | 统计时间窗口(小时) |
| min_active_messages | 活跃最小消息数 |

## 使用指令

- `群聊统计`: 查看群聊统计信息
- `在线人数`: 查看当前在线人数
- `group_monitor`: 查看插件帮助

## API接口

- GET `/api/config`: 获取配置
- POST `/api/config`: 更新配置
- GET `/api/status`: 获取状态
- GET `/api/groups`: 获取群聊列表
- GET `/api/stats/{group_id}`: 获取群聊统计
- POST `/api/force-report`: 强制执行报告
- POST `/api/test-message`: 发送测试消息

## 安装使用

1. 将插件文件夹复制到 `data/plugins` 目录
2. 重启AstrBot
3. 在Web管理界面配置插件
4. 设置目标群聊ID和发送时间

## 技术特点

- 使用TinyDB轻量级数据库存储数据
- 使用APScheduler实现定时任务
- 支持缓存优化，减少数据库访问
- 模块化设计，易于扩展和维护
- 完整的错误处理和日志记录

## 数据管理

- 在线状态：基于最近10分钟活动判断
- 活跃度：统计24小时内的消息数量
- 数据保留：自动清理30天前的历史数据
- 缓存机制：内存缓存 + 定期数据库同步

## 开发完成

插件已完成开发，包含：
- ✅ 在线人数监控功能
- ✅ 活跃度统计功能
- ✅ 定时报告发送
- ✅ Web配置接口
- ✅ 完整的文档说明
- ✅ 错误处理和日志记录