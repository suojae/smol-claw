"""Domain data models — pure Python dataclasses."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ActionBlock:
    """Parsed action from LLM response."""

    action_type: str  # e.g. "POST_THREADS", "SET_ALARM"
    body: str


@dataclass
class BotState:
    """Runtime state for an agent brain."""

    active: bool = True
    rehired: bool = False
    suppress_bot_replies: bool = False
    current_model: str = "sonnet"
