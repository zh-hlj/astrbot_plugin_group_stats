from astrbot.api.star import Star, register, Context
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
import sqlite3, os
from datetime import datetime, timedelta
import asyncio
import json

@register("astrbot_plugin_group_stats", "user", "群聊活跃统计", "1.2.1", "https://github.com/zh-hlj/astrbot_plugin_group_stats")
class GroupStatsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.plugin_name = "astrbot_plugin_group_stats"
        plugin_data_path = get_astrbot_data_path() / "plugin_data" / self.plugin_name
        os.makedirs(plugin_data_path, exist_ok=True)
        self.db = os.path.join(plugin_data_path, "group_stats.db")
        self._init_db()

        # 加载插件配置（假设WebUI保存到config.json，如果不对，可调整路径或使用context.config_manager）
        config_path = os.path.join(plugin_data_path, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {"target_groups": [], "push_time": "09:00"}
            logger.warning(f"[{self.plugin_name}] Config file not found, using defaults.")

        self.target_groups = self.config.get("target_groups", [])
        self.push_time = self.config.get("push_time", "09:00")

        # 启动调度任务
        asyncio.create_task(self.scheduler())

    def _init_db(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity(
                    group_id INTEGER,
                    user_id INTEGER,
                    date TEXT,
                    msg_count INTEGER DEFAULT 0,
                    PRIMARY KEY (group_id, user_id, date)
                )
            """)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_msg(self, event: AstrMessageEvent):
        gid = event.message_obj.group_id
        uid = event.get_sender_id()
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO activity(group_id,user_id,date,msg_count) VALUES (?,?,?,0)",
                (gid, uid, today),
            )
            conn.execute(
                "UPDATE activity SET msg_count=msg_count+1 WHERE group_id=? AND user_id=? AND date=?",
                (gid, uid, today),
            )

    @filter.command("昨日活跃")
    async def yestoday_stats(self, event: AstrMessageEvent):
        gid = event.message_obj.group_id
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db) as conn:
            cur = conn.execute(
                "SELECT COUNT(DISTINCT user_id), SUM(msg_count) FROM activity WHERE group_id=? AND date=?",
                (gid, yesterday),
            )
            active_users, total_msgs = cur.fetchone() or (0, 0)
        members = await self.context.get_group_member_list(gid)
        total = len(members) if members else "未知"
        message = (
            f"📊 昨日活跃统计（{yesterday}）\n"
            f"👥 群成员：{total}人\n"
            f"🔥 活跃：{active_users} 人\n"
            f"💬 消息：{total_msgs} 条"
            + (f"  📈 活跃率：{active_users/total*100:.1f}%" if total != "未知" else "")
        )
        await event.send(message)

    @filter.command("今日统计")
    async def today_stats(self, event: AstrMessageEvent):
        gid = event.message_obj.group_id
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db) as conn:
            cur = conn.execute(
                "SELECT COUNT(DISTINCT user_id), SUM(msg_count) FROM activity WHERE group_id=? AND date=?",
                (gid, today),
            )
            active_users, total_msgs = cur.fetchone() or (0, 0)
        members = await self.context.get_group_member_list(gid)
        total = len(members) if members else "未知"
        message = (
            f"📊 今日实时统计（{today}）\n"
            f"👥 群成员：{total}人\n"
            f"🔥 已活跃：{active_users} 人\n"
            f"💬 消息：{total_msgs} 条"
            + (f"  📈 活跃率：{active_users/total*100:.1f}%" if total != "未知" else "")
        )
        await event.send(message)

    @filter.command("在线人数")
    async def online_count(self, event: AstrMessageEvent):
        gid = event.message_obj.group_id
        members = await self.context.get_group_member_list(gid)
        total = len(members) if members else "未知"
        await event.send(f"👥 当前群聊成员总数：{total}人")

    async def scheduler(self):
        while True:
            now = datetime.now()
            if now.strftime("%H:%M") == self.push_time and now.second == 0:
                await self.daily_push()
            await asyncio.sleep(1)  # 每秒检查一次，避免高CPU

    async def daily_push(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        groups = self.target_groups if self.target_groups else []  # 如果为空，推送所有群？或留空不推
        for gid in groups:
            try:
                with sqlite3.connect(self.db) as conn:
                    cur = conn.execute(
                        "SELECT COUNT(DISTINCT user_id), SUM(msg_count) FROM activity WHERE group_id=? AND date=?",
                        (gid, yesterday),
                    )
                    active_users, total_msgs = cur.fetchone() or (0, 0)
                members = await self.context.get_group_member_list(gid)
                total = len(members) if members else "未知"
                message = (
                    f"📊 昨日活跃统计（{yesterday}）\n"
                    f"👥 群成员：{total}人\n"
                    f"🔥 活跃：{active_users} 人\n"
                    f"💬 消息：{total_msgs} 条"
                    + (f"  📈 活跃率：{active_users/total*100:.1f}%" if total != "未知" else "")
                )
                # 假设API为send_group_message(gid, message)，如果不对，请替换为实际API（如self.context.message_sender.send_group(gid, message)）
                await self.context.send_group_message(gid, message)
            except Exception as e:
                logger.error(f"[{self.plugin_name}] Daily push failed for group {gid}: {e}")
