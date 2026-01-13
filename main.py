import os
import sqlite3
from datetime import datetime, timedelta

from astrbot.api import Context
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Star, register


@register("group_stats", "your_name", "群聊活跃统计插件", "1.0.0")
class GroupStatsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 数据库路径：AstrBot/data/group_stats.db
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "group_stats.db",
        )
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                group_id INTEGER,
                user_id INTEGER,
                date TEXT,
                message_count INTEGER DEFAULT 0,
                PRIMARY KEY (group_id, user_id, date)
            )
        """)
        conn.commit()
        conn.close()

    @filter.on_message_type(["group"])  # 只监听群消息
    async def on_group_message(self, event: AstrMessageEvent):
        """自动记录活跃"""
        group_id = event.message_obj.group_id
        user_id = event.get_sender_id()
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO activity (group_id, user_id, date, message_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(group_id, user_id, date)
            DO UPDATE SET message_count = message_count + 1
        """,
            (group_id, user_id, today),
        )
        conn.commit()
        conn.close()

    @filter.command("昨日活跃")
    async def cmd_yesterday_stats(self, event: AstrMessageEvent):
        """查询昨日活跃数据"""
        group_id = event.message_obj.group_id

        # 获取昨日数据
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(DISTINCT user_id), SUM(message_count)
            FROM activity
            WHERE group_id = ? AND date = ?
        """,
            (group_id, yesterday),
        )

        result = cursor.fetchone()
        if result:
            active_users, total_msgs = result
        else:
            active_users, total_msgs = 0, 0
        conn.close()

        # 获取群成员总数（调用AstrBot API）
        members = await self.context.get_group_member_list(group_id)
        total_members = len(members) if members else "未知"

        await event.send(
            "📊 昨日活跃统计\n"
            f"👥 群成员: {total_members}人\n"
            f"🔥 活跃人数: {active_users or 0}人\n"
            f"💬 总消息: {total_msgs or 0}条\n"
            f"📈 活跃率: {(active_users / total_members * 100):.1f}%"
            if total_members != "未知" and total_members > 0
            else ""
        )

    @filter.command("今日统计")
    async def cmd_today_stats(self, event: AstrMessageEvent):
        """查询今日实时数据"""
        group_id = event.message_obj.group_id
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(DISTINCT user_id), SUM(message_count)
            FROM activity
            WHERE group_id = ? AND date = ?
        """,
            (group_id, today),
        )

        result = cursor.fetchone()
        if result:
            active_users, total_msgs = result
        else:
            active_users, total_msgs = 0, 0
        conn.close()

        await event.send(
            f"🕐 今日实时统计\n"
            f"🔥 已活跃: {active_users or 0}人\n"
            f"💬 消息数: {total_msgs or 0}条"
        )
