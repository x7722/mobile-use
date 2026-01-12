"""
Screen Display Widget - 显示手机屏幕
"""
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';

class ScreenDisplay extends StatelessWidget {
  final String? screenshot;
  
  const ScreenDisplay({Key? key, this.screenshot}) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.black,
        border: Border.all(color: Colors.grey.shade300, width: 2),
        borderRadius: BorderRadius.circular(8),
      ),
      child: screenshot != null
          ? ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: Image.memory(
                base64Decode(screenshot!)  ,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.error_outline, size: 48, color: Colors.red),
                        SizedBox(height: 16),
                        Text(
                          '加载截图失败',
                          style: TextStyle(color: Colors.white),
                        ),
                      ],
                    ),
                  );
                },
              ),
            )
          : Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.phone_android,
                    size: 64,
                    color: Colors.grey.shade600,
                  ),
                  SizedBox(height: 16),
                  Text(
                    '请连接设备',
                    style: TextStyle(
                      color: Colors.grey.shade600,
                      fontSize: 18,
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
