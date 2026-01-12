"""
数据模型定义
"""
from pydantic import BaseModel
from typing import Optional


class DeviceInfo(BaseModel):
    """设备信息"""
    serial: str
    state: str


class ConnectRequest(BaseModel):
    """连接请求"""
    device_id: str


class CommandRequest(BaseModel):
    """AI命令请求"""
    command: str


class CommandResponse(BaseModel):
    """命令响应"""
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None


class ScreenshotResponse(BaseModel):
    """截图响应"""
    success: bool
    data: Optional[str] = None
    error: Optional[str] = None
