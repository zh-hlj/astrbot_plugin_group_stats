"""
群聊在线人数监控与活跃度统计插件
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tinydb import TinyDB, Query, where
from tinydb.operations import increment

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
        
        # 初始化数据库
        db_path = os.path.join(os.path.dirname(__file__), "data", "group_monitor.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = TinyDB(db_path)
        
        # 数据表
        self.online_members = self.db.table("online_members")
        self.activity_records = self.db.table("activity_records")
        
        # 缓存
        self.online_cache: Dict[str, Dict[str, datetime]] = {}
        self.activity_cache: Dict[str, Dict[str, int]] = {}
        
        # 调度器
        self.scheduler = None
        
        logger.info("群聊监控插件初始化完成")
    
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
            if group_id not in self.online_cache:
                self.online_cache[group_id] = {}
            self.online_cache[group_id][member_id] = current_time
            
            # 更新活跃度
            if group_id not in self.activity_cache:
                self.activity_cache[group_id] = {}
            self.activity_cache[group_id][member_id] = \
                self.activity_cache[group_id].get(member_id, 0) + 1
            
            # 异步保存到数据库
            asyncio.create_task(self._save_to_db(group_id, member_id))
            
        except Exception as e:
            logger.error(f"处理群聊消息失败: {e}")
    
    async def _save_to_db(self, group_id: str, member_id: str):
        """保存数据到数据库"""
        try:
            current_time = datetime.now()
            current_date = current_time.date().isoformat()
            
            # 保存在线状态
            self.online_members.upsert({
                "group_id": group_id,
                "member_id": member_id,
                "last_seen": current_time.isoformat()
            }, (where("group_id") == group_id) & (where("member_id") == member_id))
            
            # 保存活跃度
            self.activity_records.upsert({
                "group_id": group_id,
                "member_id": member_id,
                "date": current_date,
                "message_count": 1
            }, (where("group_id") == group_id) & 
               (where("member_id") == member_id) & 
               (where("date") == current_date))
            
            # 增加消息计数
            self.activity_records.update(
                {"message_count": increment("message_count")},
                (where("group_id") == group_id) & 
                (where("member_id") == member_id) & 
                (where("date") == current_date)
            )
            
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
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
            
            # 从缓存获取
            if group_id in self.online_cache:
                online_count = sum(
                    1 for last_seen in self.online_cache[group_id].values()
                    if last_seen > cutoff_time
                )
                return online_count
            
            # 从数据库获取
            Member = Query()
            records = self.online_members.search(
                (Member.group_id == group_id) & 
                (Member.last_seen > cutoff_time.isoformat())
            )
            
            return len(records)
            
        except Exception as e:
            logger.error(f"获取在线人数失败: {e}")
            return 0
    
    async def _get_activity_summary(
        self, group_id: str, hours: int = 24, min_messages: int = 3
    ) -> Tuple[int, List[Tuple[str, int]]]:
        """获取活跃度摘要"""
        try:
            start_date = (datetime.now() - timedelta(hours=hours)).date().isoformat()
            
            # 合并缓存和数据库数据
            member_stats = {}
            
            # 从缓存获取
            if group_id in self.activity_cache:
                for member_id, count in self.activity_cache[group_id].items():
                    member_stats[member_id] = count
            
            # 从数据库获取
            Member = Query()
            records = self.activity_records.search(
                (Member.group_id == group_id) & 
                (Member.date >= start_date) &
                (Member.message_count >= min_messages)
            )
            
            for record in records:
                member_id = record["member_id"]
                count = record.get("message_count", 0)
                member_stats[member_id] = member_stats.get(member_id, 0) + count
            
            # 排序并过滤
            sorted_members = [
                (member_id, count) 
                for member_id, count in member_stats.items() 
                if count >= min_messages
            ]
            sorted_members.sort(key=lambda x: x[1], reverse=True)
            
            return len(sorted_members), sorted_members
            
        except Exception as e:
            logger.error(f"获取活跃度摘要失败: {e}")
            return 0, []
    
    async def _schedule_daily_report(self):
        """配置每日报告任务"""
        try:
            send_time = self.config.get("send_time", "09:00")
            hour, minute = map(int, send_time.split(":"))
            
            trigger = CronTrigger(hour=hour, minute=minute, second=0)
            
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
                
                await asyncio.sleep(1)  # 避免发送过快
                
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
            
            # 清理过期数据
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            self.online_members.remove(where("last_seen") < cutoff_date)
            
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