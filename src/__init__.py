"""Smol Claw — Autonomous AI Server package."""

from src.config import CONFIG, event_queue, MODEL_ALIASES, DEFAULT_MODEL
from src.context import ContextCollector
from src.usage import UsageLimitExceeded, UsageTracker
from src.watcher import GitFileHandler
from src.executor import ClaudeExecutor
from src.memory import SimpleMemory, GuardrailMemory
from src.persona import BOT_PERSONA
from src.hormones import DigitalHormones, HormoneState, HormoneControlParams
from src.hormone_memory import HormoneMemory, HormoneEpisode
from src.discord_bot import DiscordBot
from src.engine import AutonomousEngine
from src.x_client import XClient, XPostResult
from src.threads_client import ThreadsClient, ThreadsPostResult
from src.app import app

__all__ = [
    "CONFIG",
    "event_queue",
    "MODEL_ALIASES",
    "DEFAULT_MODEL",
    "ContextCollector",
    "UsageLimitExceeded",
    "UsageTracker",
    "GitFileHandler",
    "ClaudeExecutor",
    "SimpleMemory",
    "GuardrailMemory",
    "BOT_PERSONA",
    "DigitalHormones",
    "HormoneState",
    "HormoneControlParams",
    "HormoneMemory",
    "HormoneEpisode",
    "DiscordBot",
    "AutonomousEngine",
    "XClient",
    "XPostResult",
    "ThreadsClient",
    "ThreadsPostResult",
    "app",
]
