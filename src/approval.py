"""Manual approval queue for SNS posting.

Provides a simple, file‑backed queue so posts are never published
without an explicit human approval. Designed to be light‑touch and
work in both MCP tool path and FastAPI routes.

States: pending -> approved -> posted | failed
         \-> rejected
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from src.config import CONFIG
from src.threads_client import ThreadsClient
from src.x_client import XClient


MEMORY_DIR = Path("memory")
MEMORY_DIR.mkdir(exist_ok=True)
QUEUE_FILE = MEMORY_DIR / "post_approvals.jsonl"


@dataclass
class PostApproval:
    id: str
    platform: str  # "threads" | "x" | "linkedin" | "instagram"
    action: str  # "post" | "reply"
    text: str
    meta: Dict[str, Any]
    status: str  # "pending" | "approved" | "rejected" | "posted" | "failed"
    created_at: str
    updated_at: str
    post_id: Optional[str] = None
    error: Optional[str] = None


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _ensure_file():
    if not QUEUE_FILE.exists():
        QUEUE_FILE.touch()


def _append_record(rec: PostApproval) -> None:
    _ensure_file()
    with QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def _read_all() -> List[PostApproval]:
    _ensure_file()
    out: List[PostApproval] = []
    with QUEUE_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            out.append(PostApproval(**data))
    return out


def _write_all(recs: List[PostApproval]) -> None:
    tmp = QUEUE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    tmp.replace(QUEUE_FILE)


async def _notify_pending(rec: PostApproval) -> None:
    """Notify via Discord webhook if configured. Non‑blocking best effort."""
    webhook = CONFIG.get("discord_webhook_url")
    if not webhook:
        return

    title = f"Approval Needed · {rec.platform}/{rec.action}"
    desc_lines = [
        f"ID: `{rec.id}`",
        f"Status: `{rec.status}`",
        f"Text:\n```\n{rec.text[:1800]}\n```",
        "Approve: reply `!approve <ID>` · Reject: `!reject <ID>`",
    ]
    payload = {
        "username": "Smol Claw",
        "embeds": [
            {
                "title": title,
                "description": "\n".join(desc_lines),
                "color": 5793266,  # teal
                "timestamp": _now_iso(),
            }
        ],
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook, json=payload) as resp:
                # Discord webhook returns 204 on success
                _ = await resp.text()
    except Exception:
        pass


async def enqueue_post(platform: str, action: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rec = PostApproval(
        id=str(uuid.uuid4())[:8],
        platform=platform,
        action=action,
        text=text,
        meta=meta or {},
        status="pending",
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )
    _append_record(rec)
    # Fire‑and‑forget notification
    asyncio.create_task(_notify_pending(rec))
    return {"success": False, "queued": True, "approval_id": rec.id, "text": text}


def list_pending() -> List[Dict[str, Any]]:
    return [asdict(r) for r in _read_all() if r.status == "pending"]


def _update_status(rec_id: str, status: str, **kw) -> Optional[PostApproval]:
    recs = _read_all()
    found = None
    for r in recs:
        if r.id == rec_id:
            r.status = status
            r.updated_at = _now_iso()
            for k, v in kw.items():
                setattr(r, k, v)
            found = r
            break
    if found:
        _write_all(recs)
    return found


async def approve_and_execute(rec_id: str) -> Dict[str, Any]:
    recs = _read_all()
    target = next((r for r in recs if r.id == rec_id), None)
    if not target:
        return {"success": False, "error": "not_found"}
    if target.status != "pending":
        return {"success": False, "error": f"invalid_status:{target.status}"}

    # Mark approved first (audit trail)
    _update_status(rec_id, "approved")

    try:
        if target.platform == "threads":
            client = ThreadsClient()
            if target.action == "post":
                res = await client.post(target.text)
            elif target.action == "reply":
                res = await client.reply(target.text, target.meta.get("post_id", ""))
            else:
                raise ValueError("unsupported action")
        elif target.platform == "x":
            client = XClient()
            if target.action == "post":
                res = await client.post(target.text)
            elif target.action == "reply":
                res = await client.reply(target.text, target.meta.get("tweet_id", ""))
            else:
                raise ValueError("unsupported action")
        else:
            raise ValueError("unsupported platform")

        if res.success:
            _update_status(rec_id, "posted", post_id=res.post_id)
            return {"success": True, "post_id": res.post_id, "text": target.text}
        else:
            _update_status(rec_id, "failed", error=res.error)
            return {"success": False, "error": res.error}
    except Exception as e:
        _update_status(rec_id, "failed", error=str(e))
        return {"success": False, "error": str(e)}


def reject(rec_id: str) -> Dict[str, Any]:
    updated = _update_status(rec_id, "rejected")
    if not updated:
        return {"success": False, "error": "not_found"}
    return {"success": True}

