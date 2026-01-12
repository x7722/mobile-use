"""
Chat Message Model
"""
class ChatMessage {
  final String text;
  final bool isUser;
  final bool isThinking;
  final DateTime timestamp;
  
  ChatMessage({
    required this.text,
    required this.isUser,
    this.isThinking = false,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}
