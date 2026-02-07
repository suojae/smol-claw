# 🦞 Smol Claw

> My tiny, cute autonomous AI assistant

An autonomous AI server that **thinks for itself** and **contacts you first** — just like OpenClaw, but smaller and cuter! 🦞

[한국어 문서](./README.ko.md)

## ✨ Features

- ✅ **While(true) Server** - Runs continuously
- ✅ **Autonomous Thinking** - AI judges by itself
- ✅ **Proactive Contact** - Notifies without commands
- ✅ **Context-Aware** - Analyzes Git, TODO, time, etc.

## 🚀 Quick Start

### 1. Install

```bash
cd ~/Documents/ai-assistant
pip install -r requirements.txt
```

### 2. Run

```bash
python autonomous-ai-server.py
```

### 3. Check

- Web: http://localhost:3000
- API: `curl http://localhost:3000/status`

## 📖 Usage

### Manual Question

```bash
curl -X POST http://localhost:3000/ask \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

### Manual Think Trigger

```bash
curl http://localhost:3000/think
```

### Status Check

```bash
curl http://localhost:3000/status
```

## 🧠 Autonomous Examples

### Scenario 1: Git Changes Detected

```
[10:30] AI thinking...
📊 Context: 5 Git changes found
🤖 AI Decision: "Uncommitted files detected"

📢 Notification:
━━━━━━━━━━━━━━━━━━━
Hi! 🤖

You have 5 uncommitted changes
in Git. Would you like to commit?
━━━━━━━━━━━━━━━━━━━
```

### Scenario 2: Time-Based Reminder

```
[14:00] AI thinking...
📊 Context: After lunch time
🤖 AI Decision: "Suggest afternoon work"

📢 Notification:
━━━━━━━━━━━━━━━━━━━
Had lunch? 🍽️

You have 3 tasks left on
your TODO. Ready to start?
━━━━━━━━━━━━━━━━━━━
```

## ⚙️ Configuration

Edit the `CONFIG` object in `autonomous-ai-server.py`:

```python
CONFIG = {
    "port": 3000,                    # Port number
    "check_interval": 30 * 60,       # 30 minutes (in seconds)
    "autonomous_mode": True          # Autonomous mode on/off
}
```

## 📊 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web dashboard |
| GET | `/status` | Server status |
| GET | `/think` | Manual think trigger |
| POST | `/ask` | Manual question |

## 🔄 Auto-Start on macOS Boot

### Using launchd (macOS)

1. Create plist file:

```bash
cat > ~/Library/LaunchAgents/com.smolclaw.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.smolclaw</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/jeon/Documents/ai-assistant/autonomous-ai-server.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
```

2. Load:

```bash
launchctl load ~/Library/LaunchAgents/com.smolclaw.plist
```

3. Check status:

```bash
launchctl list | grep smolclaw
```

## 🔌 Extensions

### Telegram Integration

```python
# Add to notify_user() method
from telegram import Bot

bot = Bot(token='YOUR_TOKEN')
await bot.send_message(chat_id='YOUR_CHAT_ID', text=message)
```

### Slack Integration

```python
# Add to notify_user() method
from slack_sdk.web.async_client import AsyncWebClient

slack = AsyncWebClient(token='YOUR_TOKEN')
await slack.chat_postMessage(
    channel='YOUR_CHANNEL',
    text=message
)
```

## 🆚 Comparison: OpenClaw vs Smol Claw

| Feature | OpenClaw | Smol Claw |
|---------|----------|-----------|
| While(true) | ✅ | ✅ |
| AI Autonomous Thinking | ✅ | ✅ |
| Proactive Contact | ✅ | ✅ |
| Multi-Channel | ✅ 16 channels | ⚠️ DIY |
| Complexity | High | Low (~400 lines) |
| Customization | Difficult | Easy |
| Language | TypeScript | Python |

## 📚 References

- [OpenClaw](https://github.com/openclaw/openclaw) - Inspiration for autonomous AI
- [Claude Code](https://claude.ai/code) - AI programming assistant

## ⚠️ Requirements

- Claude Pro subscription or API key
- MacBook must be running (or deploy to server for 24/7)
- Claude Code CLI installed

## 📄 License

MIT

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

Made with 💙 by a human and Claude Code
