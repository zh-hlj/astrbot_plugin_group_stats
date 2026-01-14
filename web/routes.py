"""
Web配置页面路由
提供插件的Web管理界面
"""
import json
import os
from typing import Dict, List, Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates


class WebRoutes:
    """Web路由管理器"""
    
    def __init__(self, plugin_instance):
        """
        初始化Web路由
        
        Args:
            plugin_instance: 插件实例
        """
        self.plugin = plugin_instance
        
        # 创建路由
        self.router = APIRouter()
        
        # 设置模板目录
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = Jinja2Templates(directory=template_dir)
        
        # 注册路由
        self._register_routes()
        
        logger.info("Web路由已初始化")
    
    def _register_routes(self):
        """注册路由"""
        # 主页面
        self.router.add_api_route("/", self.index, methods=["GET"])
        
        # API接口
        self.router.add_api_route("/api/config", self.get_config, methods=["GET"])
        self.router.add_api_route("/api/config", self.update_config, methods=["POST"])
        self.router.add_api_route("/api/status", self.get_status, methods=["GET"])
        self.router.add_api_route("/api/groups", self.get_groups, methods=["GET"])
        self.router.add_api_route("/api/stats/{group_id}", self.get_group_stats, methods=["GET"])
        self.router.add_api_route("/api/force-report", self.force_report, methods=["POST"])
        self.router.add_api_route("/api/test-message", self.test_message, methods=["POST"])
    
    async def index(self, request: Request):
        """
        主页面
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            HTML响应
        """
        try:
            return self.templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "plugin_name": "群聊监控插件",
                    "plugin_version": "1.0.0"
                }
            )
            
        except Exception as e:
            logger.error(f"渲染主页失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_config(self):
        """
        获取插件配置
        
        Returns:
            JSON响应
        """
        try:
            config = self.plugin.config if hasattr(self.plugin, 'config') else {}
            
            # 返回配置
            return JSONResponse({
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
                    "min_active_messages": config.get("min_active_messages", 3),
                    "data_retention_days": config.get("data_retention_days", 30)
                }
            })
            
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    async def update_config(self, request: Request):
        """
        更新插件配置
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            JSON响应
        """
        try:
            # 获取请求数据
            data = await request.json()
            
            # 验证配置
            validated_config = self._validate_config(data)
            
            # 更新插件配置
            if hasattr(self.plugin, 'config'):
                self.plugin.config.update(validated_config)
            else:
                self.plugin.config = validated_config
            
            # 如果调度器存在，更新配置
            if hasattr(self.plugin, 'report_scheduler') and self.plugin.report_scheduler:
                await self.plugin.report_scheduler.update_config(validated_config)
            
            logger.info("配置已更新")
            
            return JSONResponse({
                "success": True,
                "message": "配置更新成功",
                "data": validated_config
            })
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    async def get_status(self):
        """
        获取插件状态
        
        Returns:
            JSON响应
        """
        try:
            status = {
                "plugin_running": True,
                "monitor_enabled": self.plugin.config.get("enable_online_monitor", True),
                "activity_enabled": self.plugin.config.get("enable_activity_summary", True),
                "target_groups_count": len(self.plugin.config.get("target_groups", [])),
                "database_path": self.plugin.db_manager.db.storage.path if hasattr(self.plugin, 'db_manager') else None
            }
            
            # 获取调度器状态
            if hasattr(self.plugin, 'report_scheduler') and self.plugin.report_scheduler:
                scheduler_status = await self.plugin.report_scheduler.get_job_status()
                status["scheduler"] = scheduler_status
            
            return JSONResponse({
                "success": True,
                "data": status
            })
            
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    async def get_groups(self):
        """
        获取群聊列表
        
        Returns:
            JSON响应
        """
        try:
            # 从数据库获取群聊列表
            if hasattr(self.plugin, 'db_manager'):
                group_list = await self.plugin.db_manager.get_group_list()
            else:
                group_list = []
            
            return JSONResponse({
                "success": True,
                "data": {
                    "groups": group_list,
                    "count": len(group_list)
                }
            })
            
        except Exception as e:
            logger.error(f"获取群聊列表失败: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    async def get_group_stats(self, group_id: str):
        """
        获取指定群聊的统计信息
        
        Args:
            group_id: 群聊ID
            
        Returns:
            JSON响应
        """
        try:
            # 获取监控器实例
            if hasattr(self.plugin, 'monitor'):
                stats = await self.plugin.monitor.get_group_summary(group_id)
                
                return JSONResponse({
                    "success": True,
                    "data": stats
                })
            else:
                return JSONResponse({
                    "success": False,
                    "error": "监控器未初始化"
                }, status_code=404)
            
        except Exception as e:
            logger.error(f"获取群聊统计失败: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    async def force_report(self):
        """
        强制立即发送报告
        
        Returns:
            JSON响应
        """
        try:
            # 检查调度器
            if not (hasattr(self.plugin, 'report_scheduler') and self.plugin.report_scheduler):
                return JSONResponse({
                    "success": False,
                    "error": "调度器未初始化"
                }, status_code=404)
            
            # 强制执行报告
            success = await self.plugin.report_scheduler.force_run_report()
            
            if success:
                return JSONResponse({
                    "success": True,
                    "message": "报告已强制执行"
                })
            else:
                return JSONResponse({
                    "success": False,
                    "error": "报告执行失败"
                }, status_code=500)
            
        except Exception as e:
            logger.error(f"强制执行报告失败: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    async def test_message(self, request: Request):
        """
        发送测试消息
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            JSON响应
        """
        try:
            data = await request.json()
            group_id = data.get("group_id")
            message = data.get("message", "这是测试消息")
            
            if not group_id:
                return JSONResponse({
                    "success": False,
                    "error": "群聊ID不能为空"
                }, status_code=400)
            
            # 发送测试消息
            if hasattr(self.plugin, 'send_group_message'):
                await self.plugin.send_group_message(group_id, message)
                
                return JSONResponse({
                    "success": True,
                    "message": f"测试消息已发送到群 {group_id}"
                })
            else:
                return JSONResponse({
                    "success": False,
                    "error": "消息发送功能不可用"
                }, status_code=404)
            
        except Exception as e:
            logger.error(f"发送测试消息失败: {e}")
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=500)
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证配置数据
        
        Args:
            config: 配置数据
            
        Returns:
            验证后的配置
        """
        validated = {}
        
        # 验证发送时间
        send_time = config.get("send_time", "09:00")
        try:
            hour, minute = map(int, send_time.split(":"))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                validated["send_time"] = send_time
            else:
                raise ValueError("时间格式无效")
        except:
            validated["send_time"] = "09:00"  # 使用默认值
        
        # 验证目标群聊
        target_groups = config.get("target_groups", [])
        if isinstance(target_groups, list):
            validated["target_groups"] = [str(g) for g in target_groups]
        else:
            validated["target_groups"] = []
        
        # 验证消息模板
        message_template = config.get("message_template")
        if isinstance(message_template, str) and message_template.strip():
            validated["message_template"] = message_template
        else:
            validated["message_template"] = "📊 今日群聊报告\n在线人数: {online_count}\n昨日活跃: {active_count}\n活跃成员: {active_members}"
        
        # 验证布尔值配置
        validated["enable_online_monitor"] = bool(config.get("enable_online_monitor", True))
        validated["enable_activity_summary"] = bool(config.get("enable_activity_summary", True))
        
        # 验证数值配置
        validated["activity_time_window"] = max(1, int(config.get("activity_time_window", 24)))
        validated["min_active_messages"] = max(1, int(config.get("min_active_messages", 3)))
        validated["data_retention_days"] = max(1, int(config.get("data_retention_days", 30)))
        
        return validated


# 延迟导入logger
from astrbot.api import logger