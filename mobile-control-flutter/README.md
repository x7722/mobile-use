# Android设备控制Flutter应用

基于mobile-use开源项目开发的Flutter Windows应用,可实时查看Android手机屏幕并通过AI自然语言控制设备。

## 项目架构

```
mobile-control-flutter/
├── backend/                    # Python后端服务
│   ├── services/              # 设备控制和AI服务
│   ├── api/                   # REST API和WebSocket
│   ├── models/                # 数据模型
│   └── main.py                # FastAPI主入口
└── mobile_control_app/        # Flutter Windows应用
    └── lib/
        ├── main.dart          # 应用入口
        ├── screens/           # 主界面
        ├── widgets/           # UI组件
        ├── services/          # WebSocket通信
        └── models/            # 数据模型
```

## 核心功能

### 1. 实时屏幕显示
- 通过WebSocket实时获取Android设备截图
- 每500ms自动更新显示
- 自动适应窗口大小

### 2. 设备控制
- **刷新**: 手动触发屏幕更新
- **锁屏**: 发送电源键命令锁定/唤醒设备
- **断开**: 断开设备连接

### 3. AI对话控制
- 使用自然语言发送命令
- 实时显示AI思考过程
- 查看执行结果反馈
- 支持多轮对话

## 技术栈

### 后端(Python)
- **FastAPI**: Web服务框架
- **WebSocket**: 实时通信
- **adbutils**: Android设备连接
- **uiautomator2**: UI自动化
- **mobile-use SDK**: AI Agent集成

### 前端(Flutter)
- **Flutter**: Windows桌面应用框架
- **web_socket_channel**: WebSocket客户端
- **http**: HTTP请求

## 安装和使用

### 前置要求

1. **Python 3.12+**
2. **ADB (Android Debug Bridge)**
   - 下载: https://developer.android.com/studio/releases/platform-tools
   - 添加到系统PATH

3. **Flutter SDK** (可选,用于重新编译)
   - 下载: https://flutter.dev/

4. **Android设备**
   - 启用USB调试
   - 通过USB连接到PC

### 后端安装

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 确保mobile-use已安装
# 项目会自动引用上层目录的mobile-use
```

### 后端启动

```bash
# 启动FastAPI服务
python main.py
```

服务将在以下地址运行:
- API: http://127.0.0.1:8000
- WebSocket: ws://127.0.0.1:8000/ws
- API文档: http://127.0.0.1:8000/docs

### Flutter应用启动

如果您已安装Flutter SDK:

```bash
cd mobile_control_app

# 获取依赖
flutter pub get

# 运行应用(Windows)
flutter run -d windows
```

如果没有Flutter SDK,您需要:
1. 访问 https://flutter.dev/ 下载Flutter
2. 按照官方文档配置环境
3. 重新执行上述命令

## 使用流程

1. **连接设备**
   - 通过USB连接Android设备
   - 启用USB调试
   - 启动后端服务
   - 启动Flutter应用
   - 应用会自动检测并连接设备

2. **查看屏幕**
   - 连接成功后,左侧会显示手机实时屏幕
   - 屏幕每500ms自动更新

3. **使用AI控制**
   - 在右侧对话框输入自然语言命令
   - 例如: "打开设置"、"返回主屏幕"、"打开微信"
   - AI会分析并自动执行操作
   - 查看执行结果反馈

4. **手动控制**
   - 点击"刷新"按钮手动更新屏幕
   - 点击"锁屏"按钮锁定设备
   - 点击"断开"按钮断开连接

## API接口文档

### REST API

```
GET  /api/devices          # 获取设备列表
POST /api/connect          # 连接设备
GET  /api/screenshot       # 获取截图
POST /api/control/lock     # 锁屏
POST /api/control/refresh  # 刷新屏幕
POST /api/control/disconnect # 断开连接
```

### WebSocket

```
WS /ws                     # WebSocket连接

# 客户端 -> 服务器
{
  "type": "ai_command",
  "command": "打开设置"
}

# 服务器 -> 客户端
{
  "type": "screen_update",
  "data": "base64_screenshot"
}

{
  "type": "ai_thinking",
  "message": "AI正在分析..."
}

{
  "type": "ai_response",
  "result": {
    "success": true,
    "result": "命令执行完成"
  }
}
```

## 项目特点

### 基于mobile-use
- 复用mobile-use的设备控制能力
- 集成multi-agent AI系统
- 支持复杂的自然语言命令

### 实时通信
- WebSocket实现双向通信
- 低延迟屏幕更新
- 实时AI响应反馈

### 跨平台架构
- Python后端易于扩展
- Flutter支持多平台(Windows/macOS/Linux)
- 前后端分离,便于维护

## 故障排除

### 设备未找到
- 确认USB调试已启用
- 运行 `adb devices` 检查设备连接
- 尝试断开重连USB线

### 后端无法启动
- 检查端口8000是否被占用
- 确认Python依赖已正确安装
- 检查mobile-use路径是否正确

### Flutter应用无法连接
- 确认后端服务已启动
- 检查防火墙设置
- 查看后端日志排查错误

### AI命令执行失败
- 检查.env文件是否配置API密钥
- 查看后端日志获取详细错误
- 确认LLM服务可访问

## 开发者信息

本项目基于 [mobile-use](https://github.com/minitap-ai/mobile-use) 开发,感谢原作者的贡献。

## 许可证

MIT License - 与mobile-use项目保持一致
