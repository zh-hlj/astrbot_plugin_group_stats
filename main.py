"""
群聊在线人数监控与活跃度统计插件
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from astrbot.api.event import (
    filter, AstrMessageEvent, MessageEventResult, GroupMessageEvent
)
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


@register(
    "group_monitor",
    "AstrBot Developer",
    "群聊在线人数监控与活跃度统计插件",
    "1.0.0",
    "https://github.com/astrbot/group_monitor_plugin"
)
class GroupMonitorPlugin(Star):
    """群聊监控插件主类"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self.config = context.get_config("group_monitor") or {}
        
        # 数据文件路径
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 数据文件
        self.online_file = os.path.join(self.data_dir, "online_members.json")
        self.activity_file = os.path.join(self.data_dir, "activity_records.json")
        
        # 确保数据文件存在
        self._init_data_files()
        
        # 缓存
        self.online_members: Dict[str, Dict[str, str]] = {}
        self.activity_records: Dict[str, Dict[str, Dict[str, int]]] = {}
        
        # 加载数据
        self._load_data()
        
        # 调度器
        self.scheduler = None
        
        logger.info("群聊监控插件初始化完成")
    
    def _init_data_files(self):
        """初始化数据文件"""
        for file_path in [self.online_file, self.activity_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
    
    def _load_data(self):
        """加载数据"""
        try:
            # 加载在线成员数据
            if os.path.exists(self.online_file):
                with open(self.online_file, 'r', encoding='utf-8') as f:
                    self.online_members = json.load(f)
            
            # 加载活跃度数据
            if os.path.exists(self.activity_file):
                with open(self.activity_file, 'r', encoding='utf-8') as f:
                    self.activity_records = json.load(f)
                    
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self.online_members = {}
            self.activity_records = {}
    
    def _save_data(self, data_type: str):
        """保存数据"""
        try:
            if data_type == "online":
                with open(self.online_file, 'w', encoding='utf-8') as f:
                    json.dump(self.online_members, f, ensure_ascii=False, indent=2)
            elif data_type == "activity":
                with open(self.activity_file, 'w', encoding='utf-8') as f:
                    json.dump(self.activity_records, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    async def initialize(self):
        """插件初始化"""
        try:
            # 初始化调度器
            self.scheduler = AsyncIOScheduler()
            self.scheduler.start()
            
            # 配置定时任务
            await self._schedule_daily_report()
            
            logger.info("群聊监控插件调度器已启动")
            
        except Exception as e:
            logger.error(f"插件初始化失败: {e}")
    
    @filter.on_group_message
    async def on_group_message(self, event: GroupMessageEvent):
        """监听群聊消息"""
        try:
            group_id = str(event.group_id)
            member_id = str(event.sender.user_id)
            current_time = datetime.now()
            
            # 更新在线状态
            if group_id not in self.online_members:
                self.online_members[group_id] = {}
            self.online_members[group_id][member_id] = current_time.isoformat()
            
            # 更新活跃度
            if group_id not in self.activity_records:
                self.activity_records[group_id] = {}
            
            current_date = current_time.date().isoformat()
            if member_id not in self.activity_records[group_id]:
                self.activity_records[group_id][member_id] = {}
            
            if current_date not in self.activity_records[group_id][member_id]:
                self.activity_records[group_id][member_id][current_date] = 0
            
            self.activity_records[group_id][member_id][current_date] += 1
            
            # 异步保存数据
            asyncio.create_task(self._save_data_async())
            
        except Exception as e:
            logger.error(f"处理群聊消息失败: {e}")
    
    async def _save_data_async(self):
        """异步保存数据"""
        try:
            self._save_data("online")
            self._save_data("activity")
        except Exception as e:
            logger.error(f"异步保存数据失败: {e}")
    
    @filter.command("群聊统计")
    async def get_group_stats(self, event: AstrMessageEvent):
        """获取群聊统计"""
        try:
            group_id = str(event.group_id)
            
            # 获取在线人数
            online_count = await self._get_online_count(group_id)
            
            # 获取昨日活跃人数
            active_count, active_members = await self._get_activity_summary(
                group_id, hours=24, min_messages=3
            )
            
            # 构建回复
            reply = f"""📊 群聊统计信息

当前在线: {online_count} 人
昨日活跃: {active_count} 人

活跃成员:
"""
            for member_id, count in active_members[:5]:
                reply += f"• {member_id}: {count} 条消息\n"
            
            if len(active_members) > 5:
                reply += f"... 还有 {len(active_members) - 5} 位\n"
            
            event.set_result(MessageEventResult().message(reply))
            
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            event.set_result(MessageEventResult().message("获取统计失败"))
    
    @filter.command("在线人数")
    async def get_online_count_cmd(self, event: AstrMessageEvent):
        """获取在线人数"""
        try:
            group_id = str(event.group_id)
            count = await self._get_online_count(group_id)
            
            event.set_result(
                MessageEventResult().message(f"当前在线: {count} 人")
            )
            
        except Exception as e:
            logger.error(f"获取在线人数失败: {e}")
            event.set_result(MessageEventResult().message("获取在线人数失败"))
    
    async def _get_online_count(self, group_id: str) -> int:
        """获取在线人数"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=10)
            
            if group_id not in self.online_members:
                return 0
            
            online_count = 0
            for member_id, last_seen_str in self.online_members[group_id].items():
                try:
                    last_seen = datetime.fromisoformat(last_seen_str)
                    if last_seen > cutoff_time:
                        online_count += 1
                except:
                    continue
            
            return online_count
            
        except Exception as e:
            logger.error(f"获取在线人数失败: {e}")
            return 0
    
    async def _get_activity_summary(
        self, group_id: str, hours: int = 24, min_messages: int = 3
    ) -> Tuple[int, List[Tuple[str, int]]]:
        """获取活跃度摘要"""
        try:
            start_date = (datetime.now() - timedelta(hours=hours)).date().isoformat()
            
            if group_id not in self.activity_records:
                return 0, []
            
            member_stats = {}
            for member_id, dates in self.activity_records[group_id].items():
                total_messages = 0
                for date_str, count in dates.items():
                    if date_str >= start_date:
                        total_messages += count
                
                if total_messages >= min_messages:
                    member_stats[member_id] = total_messages
            
            # 排序
            sorted_members = sorted(
                member_stats.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return len(sorted_members), sorted_members
            
        except Exception as e:
            logger.error(f"获取活跃度摘要失败: {e}")
            return 0, []
    
    async def _schedule_daily_report(self):
        """配置每日报告任务"""
        try:
            send_time = self.config.get("send_time", "09:00")
            hour, minute = map(int, send_time.split(":"))
            
            trigger = self.scheduler.schedulers[0].CronTrigger(hour=hour, minute=minute, second=0)
            
            self.scheduler.add_job(
                func=self._send_daily_report,
                trigger=trigger,
                id="daily_report",
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"每日报告已配置: {send_time}")
            
        except Exception as e:
            logger.error(f"配置每日报告失败: {e}")
    
    async def _send_daily_report(self):
        """发送每日报告"""
        try:
            target_groups = self.config.get("target_groups", [])
            template = self.config.get(
                "message_template",
                "📊 今日群聊报告\n在线人数: {online_count}\n昨日活跃: {active_count}\n活跃成员: {active_members}"
            )
            
            for group_id in target_groups:
                try:
                    # 获取统计
                    online_count = await self._get_online_count(group_id)
                    active_count, active_members = await self._get_activity_summary(
                        group_id, hours=24, min_messages=3
                    )
                    
                    # 格式化活跃成员
                    active_members_str = ""
                    for member_id, count in active_members[:3]:
                        active_members_str += f"{member_id}({count}条) "
                    
                    # 发送消息
                    message = template.format(
                        online_count=online_count,
                        active_count=active_count,
                        active_members=active_members_str.strip()
                    )
                    
                    await self._send_group_message(group_id, message)
                    
                    logger.info(f"已向群 {group_id} 发送报告")
                    
                except Exception as e:
                    logger.error(f"向群 {group_id} 发送报告失败: {e}")
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"发送每日报告失败: {e}")
    
    async def _send_group_message(self, group_id: str, message: str):
        """发送群消息"""
        try:
            platforms = self.context.platform_manager.get_insts()
            
            for platform in platforms:
                try:
                    await platform.send_group_message(
                        group_id=int(group_id),
                        message=message
                    )
                    break
                except Exception as e:
                    logger.warning(f"平台发送失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"发送群消息失败: {e}")
    
    async def terminate(self):
        """插件卸载"""
        try:
            if self.scheduler:
                self.scheduler.shutdown()
            
            # 保存最终数据
            self._save_data("online")
            self._save_data("activity")
            
            logger.info("群聊监控插件已卸载")
            
        except Exception as e:
            logger.error(f"插件卸载失败: {e}")
    
    @filter.command("group_monitor", "群聊监控管理")
    async def manage_plugin(self, event: AstrMessageEvent):
        """插件管理"""
        config = self.config
        help_text = f"""📋 群聊监控插件

指令:
• 群聊统计 - 查看统计信息
• 在线人数 - 查看在线人数

配置:
• 发送时间: {config.get('send_time', '09:00')}
• 目标群聊: {len(config.get('target_groups', []))} 个
• 在线监控: {config.get('enable_online_monitor', True)}
• 活跃统计: {config.get('enable_activity_summary', True)}
        """
        event.set_result(MessageEventResult().message(help_text))