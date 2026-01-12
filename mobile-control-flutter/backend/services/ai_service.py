"""
AI Service - AI Agent服务
集成mobile-use的AI Agent进行自然语言命令执行
"""
import sys
import asyncio
from pathlib import Path
from typing import Optional

# 添加mobile-use到Python路径
mobile_use_path = Path(__file__).parent.parent.parent.parent / "minitap"
sys.path.insert(0, str(mobile_use_path))

from minitap.mobile_use.sdk import Agent
from minitap.mobile_use.sdk.builders import Builders
from minitap.mobile_use.sdk.types.task import AgentProfile
from minitap.mobile_use.config import initialize_llm_config


class AIService:
    """AI服务 - 处理自然语言命令执行"""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.agent: Optional[Agent] = None
        self.initialized = False
        
    async def initialize(self):
        """初始化AI Agent"""
        try:
            # 初始化LLM配置
            llm_config = initialize_llm_config()
            
            # 创建Agent配置
            agent_profile = AgentProfile(name="default", llm_config=llm_config)
            config = Builders.AgentConfig.with_default_profile(profile=agent_profile)
            
            # 指定设备
            config.with_device_id(self.device_id)
            
            # 创建Agent
            self.agent = Agent(config=config.build())
            
            # 初始化Agent
            await self.agent.init(retry_count=3, retry_wait_seconds=2)
            
            self.initialized = True
            return {"success": True, "message": "AI Agent initialized"}
        except Exception as e:
            self.initialized = False
            return {"success": False, "error": str(e)}
    
    async def execute_command(self, command: str, callback=None) -> dict:
        """
        执行AI命令
        
        Args:
            command: 自然语言命令
            callback: 回调函数,用于实时发送思考过程
        """
        if not self.initialized or not self.agent:
            return {
                "success": False,
                "error": "Agent not initialized"
            }
        
        try:
            # 创建任务
            task = self.agent.new_task(command)
            
            # 可以添加思考过程输出到临时文件
            # task.with_thoughts_output_saving(path="thoughts.txt")
            
            # 执行任务
            result = await self.agent.run_task(request=task.build())
            
            return {
                "success": True,
                "command": command,
                "result": str(result) if result else "命令执行完成"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cleanup(self):
        """清理资源"""
        if self.agent:
            try:
                await self.agent.clean()
            except Exception as e:
                print(f"Error cleaning up agent: {e}")
