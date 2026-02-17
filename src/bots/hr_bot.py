"""HR Bot — agent fire/hire/status management."""

import sys
from typing import Any, Dict, Optional

from src.bots.base_bot import BaseMarketingBot
from src.bots.personas import HR_PERSONA
from src.executor import AIExecutor


def _log(msg: str):
    print(msg, file=sys.stderr)


# Normalize various bot name inputs to registry keys
_BOT_NAME_ALIASES: Dict[str, str] = {
    "threads": "threads",
    "threadsbot": "threads",
    "stitch": "threads",
    "linkedin": "linkedin",
    "linkedinbot": "linkedin",
    "summit": "linkedin",
    "instagram": "instagram",
    "instagrambot": "instagram",
    "pixel": "instagram",
    "news": "news",
    "newsbot": "news",
    "radar": "news",
    "researcher": "news",
    "researcherbot": "news",
    "teamlead": "lead",
    "captain": "lead",
    "lead": "lead",
    "teamleadbot": "lead",
    "hr": "hr",
    "hrbot": "hr",
}

# Protected bots that cannot be fired
_PROTECTED_KEYS = frozenset({"lead", "hr"})


class HRBot(BaseMarketingBot):
    """Human Resources bot for managing agent lifecycle.

    Actions:
    - FIRE_BOT: Deactivate a bot and clear its conversation history
    - HIRE_BOT: Reactivate a previously fired bot
    - STATUS_REPORT: Show status of all registered bots
    """

    def __init__(
        self,
        own_channel_id: int,
        team_channel_id: int,
        executor: Optional[AIExecutor] = None,
        clients: Optional[Dict[str, Any]] = None,
        bot_registry: Optional[Dict[str, BaseMarketingBot]] = None,
    ):
        super().__init__(
            bot_name="HR",
            persona=HR_PERSONA,
            own_channel_id=own_channel_id,
            team_channel_id=team_channel_id,
            executor=executor,
            clients=clients,
        )
        self.bot_registry: Dict[str, BaseMarketingBot] = bot_registry or {}

    def _resolve_bot(self, name: str) -> tuple:
        """Resolve a bot name to (registry_key, bot_instance) or (None, error_msg)."""
        key = _BOT_NAME_ALIASES.get(name.lower().strip())
        if not key:
            available = ", ".join(
                sorted({v for v in _BOT_NAME_ALIASES.values() if v in self.bot_registry})
            )
            return None, f"[HR] 알 수 없는 봇: {name!r}. 가능한 봇: {available}"
        bot = self.bot_registry.get(key)
        if not bot:
            return None, f"[HR] '{key}' 봇이 레지스트리에 등록되지 않았음."
        return key, bot

    async def _fire_bot(self, name: str) -> str:
        """Deactivate a bot and clear its history."""
        result = self._resolve_bot(name)
        key, bot_or_msg = result
        if key is None:
            return bot_or_msg

        if key in _PROTECTED_KEYS:
            label = "Captain(TeamLead)" if key == "lead" else "HR"
            return f"[HR] {label}은(는) 보호 대상이므로 해고 불가함."

        if not bot_or_msg._active:
            return f"[HR] {bot_or_msg.bot_name}은(는) 이미 비활성 상태임. 추가 조치 불요함."

        bot_or_msg._active = False
        bot_or_msg.clear_history()
        _log(f"[HR] FIRED: {bot_or_msg.bot_name} (key={key})")
        return f"[HR] {bot_or_msg.bot_name} 해고 처리 완료됨. 컨텍스트 초기화됨."

    async def _hire_bot(self, name: str) -> str:
        """Reactivate a previously fired bot."""
        result = self._resolve_bot(name)
        key, bot_or_msg = result
        if key is None:
            return bot_or_msg

        if bot_or_msg._active:
            return f"[HR] {bot_or_msg.bot_name}은(는) 이미 활성 상태임. 추가 조치 불요함."

        bot_or_msg._active = True
        _log(f"[HR] HIRED: {bot_or_msg.bot_name} (key={key})")
        return f"[HR] {bot_or_msg.bot_name} 채용(재활성화) 완료됨."

    def _status_report(self) -> str:
        """Generate a status report for all registered bots."""
        if not self.bot_registry:
            return "[HR] 등록된 봇 없음."

        lines = ["[HR] === 에이전트 현황 리포트 ==="]
        active_count = 0
        inactive_count = 0

        for key in sorted(self.bot_registry.keys()):
            bot = self.bot_registry[key]
            status = "활성" if bot._active else "비활성"
            protected = " (보호)" if key in _PROTECTED_KEYS else ""
            msg_count = sum(len(h) for h in bot._channel_history.values())

            if bot._active:
                active_count += 1
            else:
                inactive_count += 1

            lines.append(f"- {bot.bot_name} [{key}]: {status}{protected} | 히스토리: {msg_count}건")

        lines.append(f"합계: 활성 {active_count}명, 비활성 {inactive_count}명")
        return "\n".join(lines)

    async def _execute_action(self, action_type: str, body: str) -> str:
        """Handle HR-specific actions, delegate others to base."""
        if action_type == "FIRE_BOT":
            return await self._fire_bot(body.strip())
        elif action_type == "HIRE_BOT":
            return await self._hire_bot(body.strip())
        elif action_type == "STATUS_REPORT":
            return self._status_report()
        return await super()._execute_action(action_type, body)
