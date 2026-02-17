"""Tests for BaseMarketingBot alarm integration — actions, commands, fire_alarm."""

import asyncio
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bots.base_bot import BaseMarketingBot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OWN_CHANNEL = 100
TEAM_CHANNEL = 200
BOT_USER_ID = 999


def _make_bot(executor=None, tmp_dir=None) -> BaseMarketingBot:
    """Create a BaseMarketingBot with alarm scheduler using temp storage."""
    bot = BaseMarketingBot(
        bot_name="TestBot",
        persona="You are a test bot.",
        own_channel_id=OWN_CHANNEL,
        team_channel_id=TEAM_CHANNEL,
        executor=executor,
    )
    if tmp_dir:
        from src.bots.alarm_scheduler import AlarmScheduler
        bot._alarm_scheduler = AlarmScheduler(bot_name="TestBot", storage_dir=tmp_dir)
    fake_user = MagicMock()
    fake_user.id = BOT_USER_ID
    fake_user.name = "TestBot"
    fake_user.display_name = "TestBot"
    fake_user.mentioned_in = MagicMock(return_value=False)
    bot._connection = MagicMock()
    bot._connection.user = fake_user
    return bot


def _make_message(content: str, channel_id: int, *, is_bot: bool = False) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.channel = MagicMock()
    msg.channel.id = channel_id
    msg.channel.send = AsyncMock()
    msg.channel.typing = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(), __aexit__=AsyncMock(),
    ))
    msg.author = MagicMock()
    msg.author.bot = is_bot
    msg.author.id = 1234
    msg.author.__str__ = lambda s: "user#1234"
    msg.role_mentions = []
    return msg


# ---------------------------------------------------------------------------
# _execute_action SET_ALARM
# ---------------------------------------------------------------------------

class TestSetAlarm:
    @pytest.mark.asyncio
    async def test_set_alarm_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("", TEAM_CHANNEL)
            body = "schedule: daily 09:00\nprompt: 마케팅 트렌드 Top 5"
            result = await bot._execute_action("SET_ALARM", body, message=msg)
            assert "등록 완료" in result
            assert "매일 09:00" in result
            alarms = bot._alarm_scheduler.list_alarms()
            assert len(alarms) == 1
            assert alarms[0].prompt == "마케팅 트렌드 Top 5"

    @pytest.mark.asyncio
    async def test_set_alarm_missing_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("", TEAM_CHANNEL)
            result = await bot._execute_action("SET_ALARM", "prompt: test", message=msg)
            assert "schedule 필드 누락" in result

    @pytest.mark.asyncio
    async def test_set_alarm_missing_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("", TEAM_CHANNEL)
            result = await bot._execute_action("SET_ALARM", "schedule: daily 09:00", message=msg)
            assert "prompt 필드 누락" in result

    @pytest.mark.asyncio
    async def test_set_alarm_invalid_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("", TEAM_CHANNEL)
            body = "schedule: weekly 09:00\nprompt: test"
            result = await bot._execute_action("SET_ALARM", body, message=msg)
            assert "실패" in result

    @pytest.mark.asyncio
    async def test_set_alarm_no_message_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            result = await bot._execute_action("SET_ALARM", "schedule: daily 09:00\nprompt: test")
            assert "메시지 컨텍스트 없음" in result


# ---------------------------------------------------------------------------
# _execute_action CANCEL_ALARM
# ---------------------------------------------------------------------------

class TestCancelAlarm:
    @pytest.mark.asyncio
    async def test_cancel_alarm_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            entry = bot._alarm_scheduler.add_alarm("daily 09:00", "test", 1, "u")
            result = await bot._execute_action("CANCEL_ALARM", f"alarm_id: {entry.alarm_id}")
            assert "취소 완료" in result
            assert bot._alarm_scheduler.list_alarms() == []

    @pytest.mark.asyncio
    async def test_cancel_alarm_raw_id(self):
        """Body can be just the alarm ID without key:value format."""
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            entry = bot._alarm_scheduler.add_alarm("daily 09:00", "test", 1, "u")
            result = await bot._execute_action("CANCEL_ALARM", entry.alarm_id)
            assert "취소 완료" in result

    @pytest.mark.asyncio
    async def test_cancel_alarm_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            result = await bot._execute_action("CANCEL_ALARM", "alarm_id: nonexist")
            assert "찾을 수 없음" in result

    @pytest.mark.asyncio
    async def test_cancel_alarm_empty_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            result = await bot._execute_action("CANCEL_ALARM", "")
            assert "비어있음" in result


# ---------------------------------------------------------------------------
# !alarms command
# ---------------------------------------------------------------------------

class TestAlarmsCommand:
    @pytest.mark.asyncio
    async def test_alarms_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("!alarms", OWN_CHANNEL)
            await bot.on_message(msg)
            msg.channel.send.assert_awaited_once()
            assert "등록된 알람 없음" in msg.channel.send.call_args[0][0]

    @pytest.mark.asyncio
    async def test_alarms_with_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            bot._alarm_scheduler.add_alarm("daily 09:00", "뉴스 요약해줘", 1, "u")
            bot._alarm_scheduler.add_alarm("every 2h", "가격 체크", 2, "u")
            msg = _make_message("!alarms", OWN_CHANNEL)
            await bot.on_message(msg)
            msg.channel.send.assert_awaited_once()
            text = msg.channel.send.call_args[0][0]
            assert "2건" in text
            assert "매일 09:00" in text
            assert "2시간마다" in text

    @pytest.mark.asyncio
    async def test_alarms_team_channel_requires_mention(self):
        """!alarms in team channel without mention → no response."""
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("!alarms", TEAM_CHANNEL)
            await bot.on_message(msg)
            msg.channel.send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_alarms_cancel_by_id(self):
        """!alarms cancel <id> should remove specific alarm."""
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            entry = bot._alarm_scheduler.add_alarm("daily 09:00", "test", 1, "u")
            msg = _make_message(f"!alarms cancel {entry.alarm_id}", OWN_CHANNEL)
            await bot.on_message(msg)
            msg.channel.send.assert_awaited_once()
            assert "취소 완료" in msg.channel.send.call_args[0][0]
            assert bot._alarm_scheduler.list_alarms() == []

    @pytest.mark.asyncio
    async def test_alarms_cancel_not_found(self):
        """!alarms cancel <bad_id> should report not found."""
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("!alarms cancel nonexist", OWN_CHANNEL)
            await bot.on_message(msg)
            msg.channel.send.assert_awaited_once()
            assert "찾을 수 없음" in msg.channel.send.call_args[0][0]

    @pytest.mark.asyncio
    async def test_alarms_cancel_all(self):
        """!alarms cancel all should remove all alarms."""
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            bot._alarm_scheduler.add_alarm("daily 09:00", "p1", 1, "u")
            bot._alarm_scheduler.add_alarm("every 2h", "p2", 2, "u")
            msg = _make_message("!alarms cancel all", OWN_CHANNEL)
            await bot.on_message(msg)
            msg.channel.send.assert_awaited_once()
            text = msg.channel.send.call_args[0][0]
            assert "2건" in text
            assert "취소 완료" in text
            assert bot._alarm_scheduler.list_alarms() == []

    @pytest.mark.asyncio
    async def test_alarms_cancel_all_empty(self):
        """!alarms cancel all with no alarms."""
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            msg = _make_message("!alarms cancel all", OWN_CHANNEL)
            await bot.on_message(msg)
            msg.channel.send.assert_awaited_once()
            assert "취소할 알람 없음" in msg.channel.send.call_args[0][0]


# ---------------------------------------------------------------------------
# _fire_alarm
# ---------------------------------------------------------------------------

class TestFireAlarm:
    @pytest.mark.asyncio
    async def test_fire_alarm_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = MagicMock()
            executor.execute = AsyncMock(return_value="오늘의 마케팅 트렌드 요약입니다.")
            bot = _make_bot(executor=executor, tmp_dir=tmp)

            entry = bot._alarm_scheduler.add_alarm("daily 09:00", "트렌드 요약", 100, "u")

            mock_channel = MagicMock()
            mock_channel.send = AsyncMock()
            bot.get_channel = MagicMock(return_value=mock_channel)

            await bot._fire_alarm(entry)

            executor.execute.assert_awaited_once()
            mock_channel.send.assert_awaited()
            sent_text = mock_channel.send.call_args[0][0]
            assert "알람" in sent_text
            assert entry.alarm_id in sent_text
            assert "마케팅 트렌드" in sent_text

            # Verify last_run updated
            updated = bot._alarm_scheduler.list_alarms()[0]
            assert updated.last_run != ""

    @pytest.mark.asyncio
    async def test_fire_alarm_strips_action_blocks(self):
        """Action blocks in alarm-triggered LLM responses should be stripped."""
        with tempfile.TemporaryDirectory() as tmp:
            response = "결과입니다. [ACTION:POST_THREADS]spam[/ACTION] 끝."
            executor = MagicMock()
            executor.execute = AsyncMock(return_value=response)
            bot = _make_bot(executor=executor, tmp_dir=tmp)
            entry = bot._alarm_scheduler.add_alarm("daily 09:00", "test", 100, "u")

            mock_channel = MagicMock()
            mock_channel.send = AsyncMock()
            bot.get_channel = MagicMock(return_value=mock_channel)

            await bot._fire_alarm(entry)

            sent_text = mock_channel.send.call_args[0][0]
            assert "[ACTION:" not in sent_text
            assert "결과입니다." in sent_text

    @pytest.mark.asyncio
    async def test_fire_alarm_channel_not_found(self):
        """If channel is not accessible, mark_run still happens."""
        with tempfile.TemporaryDirectory() as tmp:
            bot = _make_bot(tmp_dir=tmp)
            entry = bot._alarm_scheduler.add_alarm("daily 09:00", "test", 99999, "u")
            bot.get_channel = MagicMock(return_value=None)

            await bot._fire_alarm(entry)

            updated = bot._alarm_scheduler.list_alarms()[0]
            assert updated.last_run != ""

    @pytest.mark.asyncio
    async def test_fire_alarm_executor_error(self):
        """On executor error, mark_run still happens to prevent infinite retry."""
        with tempfile.TemporaryDirectory() as tmp:
            executor = MagicMock()
            executor.execute = AsyncMock(side_effect=Exception("LLM error"))
            bot = _make_bot(executor=executor, tmp_dir=tmp)
            entry = bot._alarm_scheduler.add_alarm("daily 09:00", "test", 100, "u")

            mock_channel = MagicMock()
            mock_channel.send = AsyncMock()
            bot.get_channel = MagicMock(return_value=mock_channel)

            await bot._fire_alarm(entry)

            updated = bot._alarm_scheduler.list_alarms()[0]
            assert updated.last_run != ""


# ---------------------------------------------------------------------------
# _format_schedule
# ---------------------------------------------------------------------------

class TestFormatSchedule:
    def test_daily(self):
        from src.bots.alarm_scheduler import AlarmEntry
        a = AlarmEntry("id", "daily", 9, 0, None, "UTC", "", 0, "", "")
        assert BaseMarketingBot._format_schedule(a) == "매일 09:00"

    def test_weekday(self):
        from src.bots.alarm_scheduler import AlarmEntry
        a = AlarmEntry("id", "weekday", 14, 30, None, "UTC", "", 0, "", "")
        assert BaseMarketingBot._format_schedule(a) == "평일 14:30"

    def test_interval_hours(self):
        from src.bots.alarm_scheduler import AlarmEntry
        a = AlarmEntry("id", "interval", None, None, 120, "UTC", "", 0, "", "")
        assert BaseMarketingBot._format_schedule(a) == "2시간마다"

    def test_interval_minutes(self):
        from src.bots.alarm_scheduler import AlarmEntry
        a = AlarmEntry("id", "interval", None, None, 30, "UTC", "", 0, "", "")
        assert BaseMarketingBot._format_schedule(a) == "30분마다"


# ---------------------------------------------------------------------------
# _parse_alarm_body
# ---------------------------------------------------------------------------

class TestParseAlarmBody:
    def test_basic(self):
        body = "schedule: daily 09:00\nprompt: 마케팅 트렌드"
        result = BaseMarketingBot._parse_alarm_body(body)
        assert result["schedule"] == "daily 09:00"
        assert result["prompt"] == "마케팅 트렌드"

    def test_with_timezone(self):
        body = "schedule: every 2h\nprompt: check\ntimezone: UTC"
        result = BaseMarketingBot._parse_alarm_body(body)
        assert result["timezone"] == "UTC"

    def test_empty_body(self):
        result = BaseMarketingBot._parse_alarm_body("")
        assert result == {}
