# AstrBot 群聊活跃统计插件

📊 自动记录群聊活跃度，每日推送昨日数据，支持 WebUI 勾选群号 & 时间。

## 功能特性

- ✅ 自动记录群聊消息活跃度
- ✅ 每日自动推送昨日活跃统计
- ✅ 支持多群独立统计
- ✅ 实时查询今日活跃数据
- ✅ 查询群成员总数
- ✅ 活跃率计算
- ✅ 数据持久化存储

## 安装方式

### 从仓库安装（推荐）
1. 打开 AstrBot WebUI
2. 进入插件管理页面
3. 点击"安装插件" → "从链安装"
4. 输入仓库地址：`https://github.com/zh-hlj/astrbot_plugin_group_stats`
5. 点击安装

### 手动安装
1. 下载 ZIP 文件
2. 解压到 `AstrBot/data/plugins/` 目录
3. 重启 AstrBot

## 配置说明

### 目标群设置
- 在 `_conf_schema.json` 中配置 `target_groups`
- 支持勾选多个群聊
- 留空则统计所有群

### 推送时间设置
- 配置 `push_time` 为每日自动推送时间
- 格式：HH:MM（如 09:00, 22:30）

## 命令使用

### /昨日活跃
显示昨天的活跃统计数据：
- 群成员总数
- 昨日活跃用户数
- 昨日消息总数
- 活跃率计算

### /今日统计
显示今天的实时活跃数据：
- 群成员总数
- 今日已活跃用户数
- 今日消息总数
- 活跃率计算

### /在线人数
显示当前群聊的成员总数

## 数据存储

- 数据存储在 `data/plugin_data/astrbot_plugin_group_stats/group_stats.db`
- 使用 SQLite 数据库
- 包含表：activity (group_id, user_id, date, msg_count)

## 技术实现

- 监听群聊消息事件
- 实时更新活跃数据
- 支持异步操作
- 遵循 AstrBot 插件规范

## 版本要求

- AstrBot ≥ 3.4.0
- Python ≥ 3.8

## 文件结构

```
astrbot_plugin_group_stats/
├── main.py              # 主插件文件
├── __init__.py          # 包初始化文件
├── metadata.yaml        # 插件元数据
├── _conf_schema.json    # 配置模式
├── README.md            # 说明文档
└── LICENSE              # 许可证
```

## 更新日志

### v1.2.1
- 修复插件加载问题
- 更新装饰器和参数名
- 改进数据存储路径

### v1.1.0
- 添加今日统计命令
- 添加在线人数查询
- 更新版本号

### v1.0.0
- 初始版本发布
- 支持活跃统计和每日推送

## 支持与反馈

- 项目地址：[GitHub](https://github.com/zh-hlj/astrbot_plugin_group_stats)
- 问题反馈：[Issues](https://github.com/zh-hlj/astrbot_plugin_group_stats/issues)
- AstrBot 文档：[插件开发](https://docs.astrbot.app/dev/star/plugin-new.html)

## 许可证

本项目采用 MIT 许可证。
