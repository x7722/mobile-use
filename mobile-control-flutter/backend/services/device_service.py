"""
Device Service - 设备连接和控制服务
复用mobile-use项目的Android设备控制功能
"""
import sys
import os
from typing import Optional
from pathlib import Path

# 添加mobile-use到Python路径
mobile_use_path = Path(__file__).parent.parent.parent.parent / "minitap"
sys.path.insert(0, str(mobile_use_path))

from adbutils import AdbClient, AdbDevice
from minitap.mobile_use.clients.ui_automator_client import UIAutomatorClient
from minitap.mobile_use.controllers.android_controller import AndroidDeviceController
import base64


class DeviceService:
    """设备服务 - 管理Android设备连接和控制"""
    
    def __init__(self):
        self.adb_client = AdbClient(host="127.0.0.1", port=5037)
        self.device_controller: Optional[AndroidDeviceController] = None
        self.ui_client: Optional[UIAutomatorClient] = None
        self.current_device_id: Optional[str] = None
        self.device_width: int = 0
        self.device_height: int = 0
        
    def list_devices(self) -> list[dict]:
        """列出所有连接的设备"""
        devices = []
        try:
            for device in self.adb_client.device_list():
                devices.append({
                    "serial": device.serial,
                    "state": device.state
                })
        except Exception as e:
            print(f"Error listing devices: {e}")
        return devices
    
    def connect_device(self, device_id: str) -> dict:
        """连接到指定设备"""
        try:
            self.current_device_id = device_id
            
            # 初始化UIAutomator客户端
            self.ui_client = UIAutomatorClient(device_id)
            
            # 获取设备尺寸
            device = self.adb_client.device(device_id)
            size = device.window_size()
            self.device_width = size.width
            self.device_height = size.height
            
            # 初始化设备控制器
            self.device_controller = AndroidDeviceController(
                device_id=device_id,
                adb_client=self.adb_client,
                ui_adb_client=self.ui_client,
                device_width=self.device_width,
                device_height=self.device_height
            )
            
            return {
                "success": True,
                "device_id": device_id,
                "width": self.device_width,
                "height": self.device_height
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_screenshot(self) -> str:
        """获取设备截图(base64编码)"""
        if not self.device_controller:
            raise ValueError("No device connected")
        
        try:
            # 获取截图(base64格式)
            screenshot_b64 = self.device_controller.screenshot()
            return screenshot_b64
        except Exception as e:
            raise Exception(f"Failed to get screenshot: {e}")
    
    def press_power(self):
        """按电源键(锁屏/唤醒)"""
        if not self.ui_client:
            raise ValueError("No device connected")
        
        try:
            self.ui_client.press_key("power")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def disconnect(self):
        """断开设备连接"""
        try:
            if self.ui_client:
                self.ui_client.disconnect()
            
            self.device_controller = None
            self.ui_client = None
            self.current_device_id = None
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_device_info(self) -> dict:
        """获取当前连接的设备信息"""
        if not self.current_device_id:
            return {"connected": False}
        
        return {
            "connected": True,
            "device_id": self.current_device_id,
            "width": self.device_width,
            "height": self.device_height
        }
