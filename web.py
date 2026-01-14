"""
Web配置API接口
提供插件配置的HTTP接口
"""
import json
from typing import Dict, Any
from astrbot.api import logger


class WebAPI:
    """Web API接口类"""
    
    def __init__(self, plugin_instance):
        """
        初始化Web API
        
        Args:
            plugin_instance: 插件实例
        """
        self.plugin = plugin_instance
        logger.info("Web API接口已初始化")
    
    async def handle_request(self, path: str, method: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理HTTP请求
        
        Args:
            path: 请求路径
            method: 请求方法
            data: 请求数据
            
        Returns:
            响应数据
        """
        try:
            if path == "/api/config" and method == "GET":
                return await self.get_config()
            elif path == "/api/config" and method == "POST":
                return await self.update_config(data or {})
            elif path == "/api/status" and method == "GET":
                return await self.get_status()
            elif path == "/api/groups" and method == "GET":
                return await self.get_groups()
            elif path.startswith("/api/stats/") and method == "GET":
                group_id = path.split("/")[-1]
                return await self.get_group_stats(group_id)
            elif path == "/api/force-report" and method == "POST":
                return await self.force_report()
            elif path == "/api/test-message" and method == "POST":
                return await self.test_message(data or {})
            else:
                return {"success": False, "error": "接口不存在"}
                
        except Exception as e:
            logger.error(f"API请求处理失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        config = self.plugin.config if hasattr(self.plugin, 'config') else {}
        
        return {
            "success": True,
            "data": {
                "send_time": config.get("send_time", "09:00"),
                "target_groups": config.get("target_groups", []),
                "message_template": config.get(
                    "message_template",
                    "📊 今日群聊报告\n在线人数: {online_count}\n昨日活跃: {active_count}\n活跃成员: {active_members}"
                ),
                "enable_online_monitor": config.get("enable_online_monitor", True),
                "enable_activity_summary": config.get("enable_activity_summary", True),
                "activity_time_window": config.get("activity_time_window", 24),
                "min_active_messages": config.get("min_active_messages", 3)
            }
        }
    
    async def update_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置"""
        try:
            # 验证配置
            validated = self._validate_config(data)
            
            # 更新配置
            if hasattr(self.plugin, 'config'):
                self.plugin.config.update(validated)
            else:
                self.plugin.config = validated
            
            # 重新调度任务
            if hasattr(self.plugin, 'scheduler') and self.plugin.scheduler:
                jobs = self.plugin.scheduler.get_jobs()
                for job in jobs:
                    if job.id == "daily_report":
                        self.plugin.scheduler.remove_job(job.id)
                
                await self.plugin._schedule_daily_report()
            
            logger.info("配置已更新")
            
            return {
                "success": True,
                "message": "配置更新成功",
                "data": validated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        config = self.plugin.config if hasattr(self.plugin, 'config') else {}
        
        status = {
            "plugin_running": True,
            "monitor_enabled": config.get("enable_online_monitor", True),
            "activity_enabled": config.get("enable_activity_summary", True),
            "target_groups_count": len(config.get("target_groups", [])),
            "send_time": config.get("send_time", "09:00")
        }
        
        # 获取下次执行时间
        if hasattr(self.plugin, 'scheduler') and self.plugin.scheduler:
            jobs = self.plugin.scheduler.get_jobs()
            for job in jobs:
                if job.id == "daily_report" and job.next_run_time:
                    status["next_run_time"] = job.next_run_time.isoformat()
        
        return {"success": True, "data": status}
    
    async def get_groups(self) -> Dict[str, Any]:
        """获取群聊列表"""
        try:
            # 从在线数据获取群聊列表
            if hasattr(self.plugin, 'online_members'):
                groups = list(self.plugin.online_members.keys())
            else:
                groups = []
            
            return {
                "success": True,
                "data": {
                    "groups": groups,
                    "count": len(groups)
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_group_stats(self, group_id: str) -> Dict[str, Any]:
        """获取群聊统计"""
        try:
            # 获取在线人数
            online_count = await self.plugin._get_online_count(group_id)
            
            # 获取活跃度
            active_count, active_members = await self.plugin._get_activity_summary(
                group_id, hours=24, min_messages=3
            )
            
            stats = {
                "group_id": group_id,
                "online_count": online_count,
                "active_count_24h": active_count,
                "active_members": active_members[:10],  # 前10名
                "timestamp": "2026-01-14T13:41:56"  # 示例时间
            }
            
            return {"success": True, "data": stats}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def force_report(self) -> Dict[str, Any]:
        """强制执行报告"""
        try:
            await self.plugin._send_daily_report()
            return {"success": True, "message": "报告已强制执行"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送测试消息"""
        try:
            group_id = data.get("group_id")
            message = data.get("message", "测试消息")
            
            if not group_id:
                return {"success": False, "error": "群聊ID不能为空"}
            
            await self.plugin._send_group_message(group_id, message)
            
            return {
                "success": True,
                "message": f"测试消息已发送到群 {group_id}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证配置"""
        validated = {}
        
        # 验证时间
        send_time = config.get("send_time", "09:00")
        try:
            hour, minute = map(int, send_time.split(":"))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                validated["send_time"] = send_time
        except:
            validated["send_time"] = "09:00"
        
        # 验证群聊列表
        target_groups = config.get("target_groups", [])
        if isinstance(target_groups, list):
            validated["target_groups"] = [str(g) for g in target_groups]
        else:
            validated["target_groups"] = []
        
        # 验证消息模板
        template = config.get("message_template")
        if isinstance(template, str) and template.strip():
            validated["message_template"] = template
        else:
            validated["message_template"] = "📊 今日群聊报告\n在线人数: {online_count}\n昨日活跃: {active_count}\n活跃成员: {active_members}"
        
        # 验证布尔值
        validated["enable_online_monitor"] = bool(config.get("enable_online_monitor", True))
        validated["enable_activity_summary"] = bool(config.get("enable_activity_summary", True))
        
        # 验证数值
        validated["activity_time_window"] = max(1, int(config.get("activity_time_window", 24)))
        validated["min_active_messages"] = max(1, int(config.get("min_active_messages", 3)))
        
        return validated