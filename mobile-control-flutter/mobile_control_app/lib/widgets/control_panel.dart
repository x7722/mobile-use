"""
Control Panel Widget - 设备控制面板
"""
import 'package:flutter/material.dart';

class ControlPanel extends StatelessWidget {
  final VoidCallback onRefresh;
  final VoidCallback onLock;
  final VoidCallback onDisconnect;
  
  const ControlPanel({
    Key? key,
    required this.onRefresh,
    required this.onLock,
    required this.onDisconnect,
  }) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        border: Border(top: BorderSide(color: Colors.grey.shade300)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _buildControlButton(
            icon: Icons.refresh,
            label: '刷新',
            onPressed: onRefresh,
            color: Colors.blue,
          ),
          _buildControlButton(
            icon: Icons.lock,
            label: '锁屏',
            onPressed: onLock,
            color: Colors.orange,
          ),
          _buildControlButton(
            icon: Icons.link_off,
            label: '断开',
            onPressed: onDisconnect,
            color: Colors.red,
          ),
        ],
      ),
    );
  }
  
  Widget _buildControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
    required Color color,
  }) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      ),
    );
  }
}
