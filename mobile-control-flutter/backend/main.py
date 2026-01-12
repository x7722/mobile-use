"""
FastAPI主应用 - 后端服务入口
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import Optional

from backend.services.device_service import DeviceService
from backend.services.ai_service import AIService
from backend.api.websocket import manager
from backend.models.schemas import (
    DeviceInfo,
    ConnectRequest,
    CommandRequest,
    CommandResponse,
    ScreenshotResponse
)

# 创建FastAPI应用
app = FastAPI(title="Mobile Control Backend", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例
device_service = DeviceService()
ai_service: Optional[AIService] = None


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Mobile Control Backend API",
        "version": "1.0.0"
    }


@app.get("/api/devices", response_model=list[DeviceInfo])
async def list_devices():
    """获取设备列表"""
    devices = device_service.list_devices()
    return devices


@app.post("/api/connect")
async def connect_device(request: ConnectRequest):
    """连接设备"""
    global ai_service
    
    result = device_service.connect_device(request.device_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    # 初始化AI服务
    ai_service = AIService(request.device_id)
    init_result = await ai_service.initialize()
    
    if not init_result.get("success"):
        print(f"Warning: AI service initialization failed: {init_result.get('error')}")
        # 不阻止连接,仅记录警告
    
    return result


@app.get("/api/screenshot")
async def get_screenshot():
    """获取截图"""
    try:
        screenshot = device_service.get_screenshot()
        return ScreenshotResponse(success=True, data=screenshot)
    except Exception as e:
        return ScreenshotResponse(success=False, error=str(e))


@app.post("/api/control/lock")
async def lock_screen():
    """锁屏"""
    try:
        result = device_service.press_power()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/control/refresh")
async def refresh_screen():
    """刷新屏幕(手动触发截图)"""
    return await get_screenshot()


@app.post("/api/control/disconnect")
async def disconnect_device():
    """断开连接"""
    global ai_service
    
    # 清理AI服务
    if ai_service:
        await ai_service.cleanup()
        ai_service = None
    
    # 停止屏幕更新
    manager.stop_screen_updates()
    
    # 断开设备
    result = device_service.disconnect()
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await manager.connect(websocket)
    
    # 启动屏幕更新任务
    if not manager.is_running:
        manager.screen_update_task = asyncio.create_task(
            manager.start_screen_updates(
                get_screenshot_func=device_service.get_screenshot,
                interval=0.5  # 每500ms更新一次
            )
        )
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ai_command":
                command = message.get("command", "")
                
                # 发送"思考中"消息
                await manager.send_personal_message({
                    "type": "ai_thinking",
                    "message": "AI正在分析并执行命令..."
                }, websocket)
                
                # 执行AI命令
                if ai_service and ai_service.initialized:
                    result = await ai_service.execute_command(command)
                    
                    # 发送结果
                    await manager.send_personal_message({
                        "type": "ai_response",
                        "result": result
                    }, websocket)
                else:
                    await manager.send_personal_message({
                        "type": "ai_response",
                        "result": {
                            "success": False,
                            "error": "AI服务未初始化"
                        }
                    }, websocket)
            
            elif message.get("type") == "ping":
                # 心跳响应
                await manager.send_personal_message({
                    "type": "pong"
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    print("Starting Mobile Control Backend...")
    print("API available at: http://127.0.0.1:8000")
    print("WebSocket available at: ws://127.0.0.1:8000/ws")
    print("API docs available at: http://127.0.0.1:8000/docs")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
