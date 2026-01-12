"""
Main Screen - 主界面
"""
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/websocket_service.dart';
import '../models/message.dart';
import '../widgets/screen_display.dart';
import '../widgets/control_panel.dart';
import '../widgets/chat_widget.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({Key? key}) : super(key: key);
  
  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  final WebSocketService _wsService = WebSocketService();
  String? _currentScreenshot;
  List<ChatMessage> _messages = [];
  bool _isConnected = false;
  String _statusMessage = '未连接';
  
  static const String baseUrl = 'http://127.0.0.1:8000';
  static const String wsUrl = 'ws://127.0.0.1:8000/ws';
  
  @override
  void initState() {
    super.initState();
    _initWebSocket();
    _checkDevices();
  }
  
  /// 初始化WebSocket连接
  void _initWebSocket() {
    _wsService.onScreenUpdate = (screenshot) {
      setState(() {
        _currentScreenshot = screenshot;
      });
    };
    
    _wsService.onAIThinking = (message) {
      setState(() {
        // 移除之前的思考消息
        _messages.removeWhere((m) => m.isThinking);
        _messages.add(ChatMessage(
          text: message,
          isUser: false,
          isThinking: true,
        ));
      });
    };
    
    _wsService.onAIResponse = (response) {
      setState(() {
        // 移除思考消息
        _messages.removeWhere((m) => m.isThinking);
        
        // 添加响应消息
        final success = response['success'] ?? false;
        final result = response['result'] ?? response['error'] ?? '未知响应';
        
        _messages.add(ChatMessage(
          text: success ? '✓ $result' : '✗ $result',
          isUser: false,
        ));
      });
    };
    
    _wsService.onError = (error) {
      _showSnackBar('错误: $error', isError: true);
    };
    
    _wsService.onConnected = () {
      setState(() {
        _statusMessage = '已连接';
      });
    };
    
    _wsService.onDisconnected = () {
      setState(() {
        _statusMessage = '连接断开';
        _isConnected = false;
      });
    };
  }
  
  /// 检查并连接设备
  Future<void> _checkDevices() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/devices'));
      
      if (response.statusCode == 200) {
        final devices = jsonDecode(response.body) as List;
        
        if (devices.isNotEmpty) {
          final deviceId = devices[0]['serial'];
          await _connectDevice(deviceId);
        } else {
          _showSnackBar('未找到设备,请连接Android设备', isError: true);
        }
      }
    } catch (e) {
      _showSnackBar('无法连接到后端服务: $e', isError: true);
    }
  }
  
  /// 连接设备
  Future<void> _connectDevice(String deviceId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/connect'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'device_id': deviceId}),
      );
      
      if (response.statusCode == 200) {
        setState(() {
          _isConnected = true;
          _statusMessage = '设备已连接: $deviceId';
        });
        
        // 连接WebSocket
        _wsService.connect(wsUrl);
        
        _showSnackBar('设备连接成功');
      } else {
        _showSnackBar('设备连接失败', isError: true);
      }
    } catch (e) {
      _showSnackBar('连接错误: $e', isError: true);
    }
  }
  
  /// 刷新屏幕
  Future<void> _refreshScreen() async {
    try {
      await http.post(Uri.parse('$baseUrl/api/control/refresh'));
      _showSnackBar('屏幕已刷新');
    } catch (e) {
      _showSnackBar('刷新失败: $e', isError: true);
    }
  }
  
  /// 锁屏
  Future<void> _lockScreen() async {
    try {
      await http.post(Uri.parse('$baseUrl/api/control/lock'));
      _showSnackBar('已发送锁屏命令');
    } catch (e) {
      _showSnackBar('锁屏失败: $e', isError: true);
    }
  }
  
  /// 断开连接
  Future<void> _disconnect() async {
    try {
      await http.post(Uri.parse('$baseUrl/api/control/disconnect'));
      _wsService.dispose();
      
      setState(() {
        _isConnected = false;
        _currentScreenshot = null;
        _statusMessage = '已断开';
        _messages.clear();
      });
      
      _showSnackBar('设备已断开');
    } catch (e) {
      _showSnackBar('断开失败: $e', isError: true);
    }
  }
  
  /// 发送AI命令
  void _sendCommand(String command) {
    if (!_isConnected) {
      _showSnackBar('请先连接设备', isError: true);
      return;
    }
    
    setState(() {
      _messages.add(ChatMessage(text: command, isUser: true));
    });
    
    _wsService.sendCommand(command);
  }
  
  /// 显示提示消息
  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red : Colors.green,
        duration: Duration(seconds: 2),
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Android设备控制中心'),
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
        actions: [
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Center(
              child: Row(
                children: [
                  Icon(
                    _isConnected ? Icons.circle : Icons.circle_outlined,
                    color: _isConnected ? Colors.green : Colors.grey,
                    size: 12,
                  ),
                  SizedBox(width: 8),
                  Text(_statusMessage),
                ],
              ),
            ),
          ),
        ],
      ),
      body: Row(
        children: [
          // 左侧: 屏幕显示和控制面板
          Expanded(
            flex: 1,
            child: Column(
              children: [
                Expanded(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: ScreenDisplay(screenshot: _currentScreenshot),
                  ),
                ),
                ControlPanel(
                  onRefresh: _refreshScreen,
                  onLock: _lockScreen,
                  onDisconnect: _disconnect,
                ),
              ],
            ),
          ),
          
          // 右侧: 对话界面
          Expanded(
            flex: 1,
            child: ChatWidget(
              messages: _messages,
              onSendMessage: _sendCommand,
            ),
          ),
        ],
      ),
    );
  }
  
  @override
  void dispose() {
    _wsService.dispose();
    super.dispose();
  }
}
