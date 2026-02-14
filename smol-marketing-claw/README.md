# Smol Marketing Claw — Claude Code Plugin

Autonomous marketing AI with digital hormone system, SNS posting, and Discord integration — packaged as a Claude Code plugin.

## Quick Start

```bash
# Install dependencies
pip install -r smol-marketing-claw/requirements.txt

# Load plugin
claude --plugin-dir ./smol-marketing-claw
```

## Setup

Set environment variables (or create a `.env` file in the project root):

```bash
# X (Twitter) API
export X_CONSUMER_KEY="..."
export X_CONSUMER_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_ACCESS_TOKEN_SECRET="..."

# Threads (Meta) API
export THREADS_USER_ID="..."
export THREADS_ACCESS_TOKEN="..."

# Discord
export DISCORD_BOT_TOKEN="..."
export DISCORD_CHANNEL_ID="..."
```

Or use the interactive setup:
```
/smol-claw:setup
```

## Skills (Slash Commands)

| Command | Description |
|---------|-------------|
| `/smol-claw:status` | Show hormones, usage, SNS config |
| `/smol-claw:think` | Run autonomous think cycle |
| `/smol-claw:hormone-nudge 0.2 -0.1` | Adjust hormones manually |
| `/smol-claw:post x "text"` | Post to X/Twitter |
| `/smol-claw:post threads "text"` | Post to Threads |
| `/smol-claw:discord start` | Start Discord bot |
| `/smol-claw:setup` | Environment setup guide |

## MCP Tools (10)

| Tool | Description |
|------|-------------|
| `smol_claw_status` | Full system status |
| `smol_claw_context` | Git, TODOs, time context |
| `smol_claw_hormone_nudge` | Manual hormone adjustment |
| `smol_claw_think` | Autonomous think cycle |
| `smol_claw_record_outcome` | Record think cycle result |
| `smol_claw_memory_query` | Vector similarity search |
| `smol_claw_post_x` | Post to X/Twitter |
| `smol_claw_reply_x` | Reply on X/Twitter |
| `smol_claw_post_threads` | Post to Threads |
| `smol_claw_reply_threads` | Reply on Threads |
| `smol_claw_discord_control` | Discord bot start/stop/status |

## Architecture

```
smol-marketing-claw/
├── .claude-plugin/plugin.json    # Plugin manifest
├── .mcp.json                     # MCP server config
├── server/                       # MCP stdio server
│   ├── mcp_server.py            # FastMCP entrypoint
│   ├── state.py                 # Global state manager
│   └── tools/                   # Tool implementations
├── skills/                       # Slash command definitions
├── hooks/                        # Session/tool hooks
├── scripts/                      # Hook scripts
├── agents/                       # Sub-agent definitions
└── requirements.txt
```

The plugin reuses modules from `src/` (hormones, memory, SNS clients, etc.) without modification. The MCP server replaces FastAPI — HTTP endpoints become MCP tools, REST routes become skills.

## Digital Hormone System

Three-axis emotional state that controls AI behavior:

- **Dopamine** (0-1): Reward signal. High = creative/bold, Low = cautious
- **Cortisol** (0-1): Stress signal. High = defensive, Low = adventurous
- **Energy** (0-1): Resource budget from usage quota remaining

Hormones decay naturally and respond to events (successful posts, errors, user sentiment).
