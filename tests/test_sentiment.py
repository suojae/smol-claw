"""Tests for sentiment-based hormone triggers in DiscordBot."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.discord_bot import DiscordBot


def run(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_bot(mock_claude, hormones):
    with patch.dict("os.environ", {"DISCORD_CHANNEL_ID": "0"}):
        return DiscordBot(claude=mock_claude, hormones=hormones)


class TestPraiseMessage:
    def test_praise_triggers_dopamine(self):
        """Praise should trigger positive dopamine delta."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": 0.15, "cortisol_delta": -0.05}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("잘했어! 정말 대단해!"))

        mock_hormones.trigger_dopamine.assert_called_once_with(0.15)
        mock_hormones.trigger_cortisol.assert_called_once_with(-0.05)


class TestCriticismMessage:
    def test_criticism_triggers_cortisol(self):
        """Criticism should trigger positive cortisol delta."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": -0.1, "cortisol_delta": 0.18}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("왜 이렇게 못하냐? 빨리 제대로 해!"))

        mock_hormones.trigger_dopamine.assert_called_once_with(-0.1)
        mock_hormones.trigger_cortisol.assert_called_once_with(0.18)


class TestNeutralMessage:
    def test_neutral_no_trigger(self):
        """Neutral message should not trigger any hormone change."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": 0.0, "cortisol_delta": 0.0}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("오늘 날씨 어때?"))

        mock_hormones.trigger_dopamine.assert_not_called()
        mock_hormones.trigger_cortisol.assert_not_called()


class TestParseFailure:
    def test_invalid_json_no_crash(self):
        """Invalid JSON should be silently ignored."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = "this is not json"
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("아무 메시지"))

        mock_hormones.trigger_dopamine.assert_not_called()
        mock_hormones.trigger_cortisol.assert_not_called()

    def test_executor_exception_no_crash(self):
        """Executor failure should be silently ignored."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.side_effect = Exception("API error")
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("아무 메시지"))

        mock_hormones.trigger_dopamine.assert_not_called()
        mock_hormones.trigger_cortisol.assert_not_called()


class TestHormonesDisabled:
    def test_skip_when_no_hormones(self):
        """Should skip analysis entirely when hormones is None."""
        mock_claude = AsyncMock()
        bot = _make_bot(mock_claude, hormones=None)

        run(bot._analyze_sentiment("칭찬해줄게!"))

        mock_claude.execute.assert_not_called()


class TestDeltaClamping:
    def test_clamps_to_max(self):
        """Deltas exceeding 0.2 should be clamped."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = json.dumps(
            {"dopamine_delta": 0.5, "cortisol_delta": -0.5}
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("극단적 메시지"))

        mock_hormones.trigger_dopamine.assert_called_once_with(0.2)
        mock_hormones.trigger_cortisol.assert_called_once_with(-0.2)


class TestCodeFenceStripping:
    def test_strips_markdown_fences(self):
        """Should handle haiku responses wrapped in markdown code fences."""
        mock_claude = AsyncMock()
        mock_hormones = MagicMock()
        mock_claude.execute.return_value = (
            '```json\n{"dopamine_delta": 0.1, "cortisol_delta": 0.0}\n```'
        )
        bot = _make_bot(mock_claude, mock_hormones)

        run(bot._analyze_sentiment("고마워!"))

        mock_hormones.trigger_dopamine.assert_called_once_with(0.1)
        mock_hormones.trigger_cortisol.assert_not_called()
