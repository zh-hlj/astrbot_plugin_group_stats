# 群聊监控插件 (group_monitor)

AstrBot的群聊在线人数监控与活跃度统计插件。

## 功能特性

- **在线人数监控**: 实时监控群聊在线成员数量
- **活跃度统计**: 统计每日群聊活跃成员及消息数量
- **定时报告**: 每日自动发送群聊统计报告
- **灵活配置**: 支持自定义发送时间、目标群聊和消息模板

## 安装方法

1. 将插件文件夹复制到 AstrBot 的 `data/plugins` 目录下
2. 重启 AstrBot
3. 在 Web 管理界面中启用插件并进行配置

## 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `send_time` | string | "09:00" | 每日报告发送时间 (HH:MM格式) |
| `target_groups` | list | [] | 目标群聊ID列表 |
| `message_template` | string | 见下文 | 发送消息模板 |
| `enable_online_monitor` | bool | true | 启用在线人数监控 |
| `enable_activity_summary` | bool | true | 启用活跃度统计 |
| `activity_time_window` | int | 24 | 活跃度统计时间窗口(小时) |
| `min_active_messages` | int | 3 | 定义为活跃成员的最小消息数 |

### 消息模板变量

- `{online_count}`: 在线人数
- `{active_count}`: 活跃人数
- `{active_members}`: 活跃成员列表

示例模板:
```
📊 今日群聊报告
在线人数: {online_count} 人
昨日活跃: {active_count} 人
活跃成员: {active_members}
```

## 使用指令

### 群聊统计
```
群聊统计
```
显示当前群聊的统计信息，包括在线人数、昨日活跃人数和活跃成员列表。

### 在线人数
```
在线人数
```
显示当前群聊的在线人数。

### 插件管理
```
group_monitor
```
显示插件帮助信息和当前配置。

## API 接口

插件提供以下 HTTP API 接口用于配置管理：

### 获取配置
```
GET /api/config
```

### 更新配置
```
POST /api/config
Content-Type: application/json

{
    "send_time": "09:00",
    "target_groups": ["123456", "789012"],
    "message_template": "自定义消息模板"
}
```

### 获取状态
```
GET /api/status
```

### 获取群聊列表
```
GET /api/groups
```

### 获取群聊统计
```
GET /api/stats/{group_id}
```

### 强制执行报告
```
POST /api/force-report
```

### 发送测试消息
```
POST /api/test-message
Content-Type: application/json

{
    "group_id": "123456",
    "message": "测试消息内容"
}
```

## 数据存储

插件使用 JSON 文件存储数据，数据文件位于:
- `data/online_members.json`: 在线成员记录
- `data/activity_records.json`: 活跃度记录

## 注意事项

1. 确保 AstrBot 具有发送群消息的权限
2. 目标群聊ID需要正确配置才能接收报告
3. 插件会自动清理30天前的历史数据
4. 在线状态基于最近10分钟内的活动判断

## 更新日志

### v1.0.0
- 初始版本发布
- 实现在线人数监控
- 实现活跃度统计
- 实现定时报告功能
- 提供Web配置接口

## 支持与反馈

如有问题或建议，请提交 Issue 或 Pull Request。