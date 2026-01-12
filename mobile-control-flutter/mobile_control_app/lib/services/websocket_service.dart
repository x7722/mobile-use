"""
WebSocket Service - 后端通信服务
"""
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  
  // 回调函数
  Function(String)? onScreenUpdate;
  Function(Map<String, dynamic>)? onAIResponse;
  Function(String)? onAIThinking;
  Function(String)? onError;
  Function()? onConnected;
  Function()? onDisconnected;
  
  bool _isConnected = false;
  
  bool get isConnected => _isConnected;
  
  /// 连接到WebSocket服务器
  void connect(String url) {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _isConnected = true;
      onConnected?.call();
      
      // 监听消息
      _channel!.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message);
            _handleMessage(data);
          } catch (e) {
            print('Error parsing message: $e');
          }
        },
        onError: (error) {
          print('WebSocket error: $error');
          _isConnected = false;
          onError?.call(error.toString());
        },
        onDone: () {
          print('WebSocket connection closed');
          _isConnected = false;
          onDisconnected?.call();
        },
      );
    } catch (e) {
      print('Error connecting to WebSocket: $e');
      _isConnected = false;
      onError?.call(e.toString());
    }
  }
  
  /// 处理接收到的消息
  void _handleMessage(Map<String, dynamic> data) {
    final type = data['type'];
    
    switch (type) {
      case 'screen_update':
        onScreenUpdate?.call(data['data']);
        break;
        
      case 'ai_response':
        onAIResponse?.call(data['result']);
        break;
        
      case 'ai_thinking':
        onAIThinking?.call(data['message']);
        break;
        
      case 'error':
        onError?.call(data['message']);
        break;
        
      default:
        print('Unknown message type: $type');
    }
  }
  
  /// 发送AI命令
  void sendCommand(String command) {
    if (!_isConnected || _channel == null) {
      onError?.call('未连接到服务器');
      return;
    }
    
    final message = jsonEncode({
      'type': 'ai_command',
      'command': command,
    });
    
    try {
      _channel!.sink.add(message);
    } catch (e) {
      print('Error sending command: $e');
      onError?.call('发送命令失败: $e');
    }
  }
  
  /// 发送心跳
  void sendPing() {
    if (!_isConnected || _channel == null) return;
    
    final message = jsonEncode({'type': 'ping'});
    try {
      _channel!.sink.add(message);
    } catch (e) {
      print('Error sending ping: $e');
    }
  }
  
  /// 断开连接
  void dispose() {
    _channel?.sink.close();
    _isConnected = false;
  }
}
