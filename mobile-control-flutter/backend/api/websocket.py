"""
WebSocket管理器 - 处理实时通信
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Optional, Callable
import asyncio
import json


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.screen_update_task: Optional[asyncio.Task] = None
        self.is_running = False
        
    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 如果没有活动连接,停止屏幕更新
        if not self.active_connections and self.screen_update_task:
            self.is_running = False
        
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送消息给特定客户端"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message: {e}")
        
    async def broadcast(self, message: dict):
        """广播消息给所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # 移除断开的连接
        for conn in disconnected:
            self.disconnect(conn)
            
    async def start_screen_updates(self, get_screenshot_func: Callable, interval: float = 0.5):
        """
        启动屏幕更新循环
        
        Args:
            get_screenshot_func: 获取截图的函数
            interval: 更新间隔(秒)
        """
        self.is_running = True
        
        while self.is_running and self.active_connections:
            try:
                # 获取截图
                screenshot_b64 = get_screenshot_func()
                
                # 广播给所有客户端
                await self.broadcast({
                    "type": "screen_update",
                    "data": screenshot_b64
                })
                
            except Exception as e:
                print(f"Screen update error: {e}")
                # 发送错误消息
                await self.broadcast({
                    "type": "error",
                    "message": f"屏幕更新失败: {str(e)}"
                })
            
            # 等待下一次更新
            await asyncio.sleep(interval)
        
        self.is_running = False
    
    def stop_screen_updates(self):
        """停止屏幕更新"""
        self.is_running = False


# 全局连接管理器实例
manager = ConnectionManager()
