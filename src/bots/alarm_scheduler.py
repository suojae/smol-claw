"""Alarm scheduler — dynamic alarm registration, persistence, and due-checking."""

import json
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _log(msg: str):
    print(msg, file=sys.stderr)


@dataclass
class AlarmEntry:
    alarm_id: str
    schedule_type: str  # "daily" | "weekday" | "interval"
    hour: Optional[int]  # daily/weekday: 0-23
    minute: Optional[int]  # daily/weekday: 0-59
    interval_minutes: Optional[int]  # interval: minutes
    tz: str  # e.g. "Asia/Seoul"
    prompt: str
    channel_id: int
    created_by: str
    created_at: str  # ISO datetime
    last_run: str = ""  # ISO datetime or empty
    enabled: bool = True


# Schedule string patterns
_DAILY_RE = re.compile(r"^daily\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)
_WEEKDAY_RE = re.compile(r"^weekday\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)
_INTERVAL_H_RE = re.compile(r"^every\s+(\d+)h$", re.IGNORECASE)
_INTERVAL_M_RE = re.compile(r"^every\s+(\d+)m$", re.IGNORECASE)

_MAX_ALARMS_PER_BOT = 20
_MIN_INTERVAL_MINUTES = 10


class AlarmScheduler:
    """Manages alarm entries for a single bot: CRUD, persistence, due-checking."""

    def __init__(self, bot_name: str, storage_dir: str = "memory"):
        self._bot_name = bot_name
        self._storage_path = Path(storage_dir) / f"alarms_{bot_name}.json"
        self._alarms: Dict[str, AlarmEntry] = {}
        self._load()

    def add_alarm(
        self,
        schedule_str: str,
        prompt: str,
        channel_id: int,
        created_by: str,
        tz: str = "Asia/Seoul",
    ) -> AlarmEntry:
        """Parse schedule string, create alarm, persist, and return entry."""
        if len(self._alarms) >= _MAX_ALARMS_PER_BOT:
            raise ValueError(f"알람 개수 제한 초과 (최대 {_MAX_ALARMS_PER_BOT}개)")

        parsed = self._parse_schedule(schedule_str)
        # Validate timezone
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, KeyError):
            raise ValueError(f"잘못된 타임존: {tz!r}")

        alarm_id = uuid.uuid4().hex[:8]
        entry = AlarmEntry(
            alarm_id=alarm_id,
            schedule_type=parsed["type"],
            hour=parsed.get("hour"),
            minute=parsed.get("minute"),
            interval_minutes=parsed.get("interval_minutes"),
            tz=tz,
            prompt=prompt,
            channel_id=channel_id,
            created_by=created_by,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._alarms[alarm_id] = entry
        self._save()
        return entry

    def remove_alarm(self, alarm_id: str) -> bool:
        """Remove alarm by ID. Returns True if found and removed."""
        if alarm_id in self._alarms:
            del self._alarms[alarm_id]
            self._save()
            return True
        return False

    def list_alarms(self) -> List[AlarmEntry]:
        """Return all alarms."""
        return list(self._alarms.values())

    def get_due_alarms(self, now_utc: datetime) -> List[AlarmEntry]:
        """Return alarms that should fire now."""
        due = []
        for alarm in self._alarms.values():
            if not alarm.enabled:
                continue
            if self._is_due(alarm, now_utc):
                due.append(alarm)
        return due

    def mark_run(self, alarm_id: str, now_utc: datetime):
        """Update last_run timestamp after execution."""
        alarm = self._alarms.get(alarm_id)
        if alarm:
            alarm.last_run = now_utc.isoformat()
            self._save()

    @staticmethod
    def _parse_schedule(schedule_str: str) -> dict:
        """Parse schedule string into structured dict."""
        s = schedule_str.strip()

        m = _DAILY_RE.match(s)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"잘못된 시간: {s}")
            return {"type": "daily", "hour": hour, "minute": minute}

        m = _WEEKDAY_RE.match(s)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"잘못된 시간: {s}")
            return {"type": "weekday", "hour": hour, "minute": minute}

        m = _INTERVAL_H_RE.match(s)
        if m:
            hours = int(m.group(1))
            minutes = hours * 60
            if minutes < _MIN_INTERVAL_MINUTES:
                raise ValueError(f"최소 간격은 {_MIN_INTERVAL_MINUTES}분 (요청: {hours}시간)")
            return {"type": "interval", "interval_minutes": minutes}

        m = _INTERVAL_M_RE.match(s)
        if m:
            minutes = int(m.group(1))
            if minutes < _MIN_INTERVAL_MINUTES:
                raise ValueError(f"최소 간격은 {_MIN_INTERVAL_MINUTES}분 (요청: {minutes}분)")
            return {"type": "interval", "interval_minutes": minutes}

        raise ValueError(f"잘못된 스케줄 형식: {s!r}. "
                         f"지원: daily HH:MM, weekday HH:MM, every Nh, every Nm")

    @staticmethod
    def _is_due(alarm: AlarmEntry, now_utc: datetime) -> bool:
        """Check if alarm should fire at this time."""
        try:
            tz = ZoneInfo(alarm.tz)
        except (ZoneInfoNotFoundError, KeyError):
            return False

        now_local = now_utc.astimezone(tz)

        if alarm.schedule_type in ("daily", "weekday"):
            # weekday: skip weekends (5=Saturday, 6=Sunday)
            if alarm.schedule_type == "weekday" and now_local.weekday() >= 5:
                return False

            scheduled_time = now_local.replace(
                hour=alarm.hour, minute=alarm.minute, second=0, microsecond=0
            )
            # Must be past the scheduled time
            if now_local < scheduled_time:
                return False

            # Check last_run — should not have run today
            if alarm.last_run:
                try:
                    last_run_utc = datetime.fromisoformat(alarm.last_run)
                    last_run_local = last_run_utc.astimezone(tz)
                    if last_run_local.date() == now_local.date():
                        return False
                except (ValueError, TypeError):
                    pass

            return True

        if alarm.schedule_type == "interval":
            if not alarm.last_run:
                return True  # Never run — fire immediately
            try:
                last_run_utc = datetime.fromisoformat(alarm.last_run)
                elapsed = (now_utc - last_run_utc).total_seconds() / 60
                return elapsed >= alarm.interval_minutes
            except (ValueError, TypeError):
                return True

        return False

    def _load(self):
        """Load alarms from JSON file."""
        self._alarms.clear()
        try:
            if self._storage_path.exists():
                raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    for item in raw:
                        if isinstance(item, dict) and "alarm_id" in item:
                            entry = AlarmEntry(
                                alarm_id=str(item["alarm_id"]),
                                schedule_type=str(item.get("schedule_type", "")),
                                hour=item.get("hour"),
                                minute=item.get("minute"),
                                interval_minutes=item.get("interval_minutes"),
                                tz=str(item.get("tz", "Asia/Seoul")),
                                prompt=str(item.get("prompt", "")),
                                channel_id=int(item.get("channel_id", 0)),
                                created_by=str(item.get("created_by", "")),
                                created_at=str(item.get("created_at", "")),
                                last_run=str(item.get("last_run", "")),
                                enabled=bool(item.get("enabled", True)),
                            )
                            self._alarms[entry.alarm_id] = entry
        except Exception as e:
            _log(f"[AlarmScheduler:{self._bot_name}] load failed: {e}")

    def _save(self):
        """Persist alarms to JSON file."""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = [asdict(a) for a in self._alarms.values()]
            self._storage_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            _log(f"[AlarmScheduler:{self._bot_name}] save failed: {e}")
