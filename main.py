from astrbot.api.star import Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger
import sqlite3, os
from datetime import datetime, timedelta

@register("group_stats", "user", "群聊活跃统计", "1.2.1")
class GroupStatsPlugin(Star):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.db = os.path.join(self.context.path, "group_stats.db")
        self._init_db()

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

    @filter.on_message_type(["group"])
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
            active_users, total_msgs = cur.fetchone()
            active_users = active_users or 0
            total_msgs = total_msgs or 0
        members = await self.context.get_group_member_list(gid)
        total = len(members) if members else "未知"
        await event.send(
            f"📊 昨日活跃统计（{yesterday}）\n"
            f"👥 群成员：{total}人\n"
            f"🔥 活跃：{active_users} 人\n"
            f"💬 消息：{total_msgs} 条"
            + (f"  📈 活跃率：{active_users/total*100:.1f}%" if total != "未知" else "")
        )
