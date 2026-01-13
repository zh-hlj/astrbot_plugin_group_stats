from astrbot.api.star import Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import sqlite3, os, json
from datetime import datetime, timedelta

@register("group_stats", "user", "群聊活跃统计", "1.1.0")
class GroupStatsPlugin(Star):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.db = os.path.join(self.context.path, "group_stats.db")
        self._init_db()
        # 启动时读一次配置
        self._load_cfg()
        # 启动定时器
        self._start_scheduler()

    # ------- 配置读写 -------
    def _load_cfg(self):
        cfg = self.context.get_config("target_groups", [])          # list[int]
        self.push_time = self.context.get_config("push_time", "09:00")
        self.target_groups = set(cfg)                               # 转成 set 便于 in 判断
        logger.info(f"[GroupStats] 已应用群号: {list(self.target_groups)}  推送时间: {self.push_time}")

    # 配置被用户在 WebUI 修改后会自动回调
    async def config_changed(self, new_conf: dict):
        self._load_cfg()
        self._restart_scheduler()   # 时间可能改了，重启定时器
        logger.info("[GroupStats] 配置已更新")

    # ------- 数据库 -------
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

    # ------- 消息监听 -------
    @filter.on_message_type(["group"])
    async def on_group_msg(self, event: AstrMessageEvent):
        gid = event.message_obj.group_id
        # 如果用户配置了白名单且当前群不在白名单，直接 return
        if self.target_groups and gid not in self.target_groups:
            return
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

    # ------- 统计命令 -------
    @filter.command("昨日活跃")
    async def yestoday_stats(self, event: AstrMessageEvent):
        gid = event.message_obj.group_id
        if self.target_groups and gid not in self.target_groups:
            return
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

    # ------- 定时推送 -------
    def _start_scheduler(self):
        self.sched = AsyncIOScheduler()
        hour, minute = map(int, self.push_time.split(":"))
        self.sched.add_job(self._daily_push, "cron", hour=hour, minute=minute)
        self.sched.start()
        logger.info(f"[GroupStats] 定时推送已启动：{self.push_time}")

    def _restart_scheduler(self):
        if self.sched.running:
            self.sched.shutdown()
        self._start_scheduler()

    async def _daily_push(self):
        # 只推用户勾选的群
        for gid in self.target_groups:
            await self.yestoday_stats(AstrMessageEvent.fake_event(gid))