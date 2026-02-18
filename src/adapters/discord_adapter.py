"""Discord adapter — bridges discord.Client to AgentBrain.

This module provides DiscordBotAdapter, a thin discord.Client subclass
that converts Discord messages to IncomingMessage and delegates to AgentBrain.

For backward compatibility, BaseMarketingBot in src/bots/base_bot.py remains
the primary class used by existing code. This adapter demonstrates how the
full hexagonal split will work.
"""

import discord

from src.domain.agent import AgentBrain
from src.ports.inbound import IncomingMessage


class DiscordNotificationAdapter:
    """NotificationPort implementation using discord.Client."""

    def __init__(self, client: discord.Client):
        self._client = client

    async def send(self, channel_id: int, text: str) -> None:
        channel = self._client.get_channel(channel_id)
        if channel:
            # Split long messages
            while text:
                await channel.send(text[:2000])
                text = text[2000:]

    async def send_typing(self, channel_id: int) -> None:
        channel = self._client.get_channel(channel_id)
        if channel:
            await channel.typing()


class DiscordBotAdapter(discord.Client):
    """Thin Discord adapter that delegates to AgentBrain.

    Converts discord.Message -> IncomingMessage for platform-agnostic processing.
    """

    def __init__(self, brain: AgentBrain, token: str, **discord_kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **discord_kwargs)
        self._brain = brain
        self._token = token

    def _to_incoming(self, message: discord.Message) -> IncomingMessage:
        """Convert a Discord message to platform-agnostic IncomingMessage."""
        is_mention = (
            (self.user and self.user.mentioned_in(message))
            or self._is_role_mentioned(message)
            or self._is_text_mentioned(message.content)
        )
        return IncomingMessage(
            content=message.content,
            channel_id=message.channel.id,
            author_name=str(message.author),
            author_id=message.author.id,
            is_bot=message.author.bot,
            is_mention=is_mention,
            is_team_channel=message.channel.id in self._brain._team_channel_ids,
            is_own_channel=message.channel.id == self._brain.own_channel_id,
        )

    def _is_role_mentioned(self, message: discord.Message) -> bool:
        if not message.role_mentions or not self.user:
            return False
        bot_names = {self._brain.bot_name.lower()} | {a.lower() for a in self._brain._aliases}
        return any(role.name.lower() in bot_names for role in message.role_mentions)

    def _is_text_mentioned(self, content: str) -> bool:
        if not self.user:
            return False
        names = {self._brain.bot_name, self.user.name}
        if self.user.display_name:
            names.add(self.user.display_name)
        names.update(self._brain._aliases)
        content_lower = content.lower()
        return any(f"@{name.lower()}" in content_lower for name in names)

    async def on_ready(self):
        print(f"[{self._brain.bot_name}] logged in as {self.user}")
        # Wire up notification port
        notification = DiscordNotificationAdapter(self)
        self._brain._notification = notification
        self._brain._get_channel = self.get_channel
        self._brain._is_closed = self.is_closed
        await self._brain.start_alarm_loop()
