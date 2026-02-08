"""Smol Claw — Autonomous AI Server package."""

from src.config import CONFIG, event_queue
from src.context import ContextCollector
from src.usage import UsageLimitExceeded, UsageTracker
from src.watcher import GitFileHandler
from src.executor import ClaudeExecutor
from src.memory import SimpleMemory, GuardrailMemory
from src.discord_bot import DiscordBot
from src.webhook import format_github_event, send_direct_discord_notification
from src.engine import AutonomousEngine
from src.app import app

__all__ = [
    "CONFIG",
    "event_queue",
    "ContextCollector",
    "UsageLimitExceeded",
    "UsageTracker",
    "GitFileHandler",
    "ClaudeExecutor",
    "SimpleMemory",
    "GuardrailMemory",
    "DiscordBot",
    "format_github_event",
    "send_direct_discord_notification",
    "AutonomousEngine",
    "app",
]
