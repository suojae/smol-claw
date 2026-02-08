"""Tests for event-driven architecture (FileWatcher, Queue, Webhook)"""

import asyncio
import hashlib
import hmac
import json
from unittest.mock import patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import CONFIG, event_queue
from src.watcher import GitFileHandler
from src.webhook import format_github_event, send_direct_discord_notification
from src.app import app, discord_bot


def run(coro):
    """Helper to run async functions in sync tests"""
    return asyncio.get_event_loop().run_until_complete(coro)


def drain_queue():
    """Clear the event queue between tests"""
    while not event_queue.empty():
        try:
            event_queue.get_nowait()
        except asyncio.QueueEmpty:
            break


class TestGitFileHandler:
    def test_ignores_git_directory(self):
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop)

        assert handler._should_ignore("/repo/.git/objects/abc") is True
        assert handler._should_ignore("/repo/__pycache__/mod.pyc") is True
        assert handler._should_ignore("/repo/node_modules/pkg/index.js") is True

    def test_does_not_ignore_source_files(self):
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop)

        assert handler._should_ignore("/repo/main.py") is False
        assert handler._should_ignore("/repo/src/app.js") is False

    def test_emits_event_to_queue(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=0)

        handler._emit("/repo/main.py", "modified")
        # Spin loop to process call_soon_threadsafe callback
        loop.run_until_complete(asyncio.sleep(0))

        assert not event_queue.empty()
        event = event_queue.get_nowait()
        assert event["type"] == "file_changed"
        assert "main.py" in event["detail"]

    def test_debounce_prevents_rapid_events(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=10)

        handler._emit("/repo/a.py", "modified")
        handler._emit("/repo/b.py", "modified")  # should be debounced
        loop.run_until_complete(asyncio.sleep(0))

        count = 0
        while not event_queue.empty():
            event_queue.get_nowait()
            count += 1
        assert count == 1

    def test_on_modified_pushes_event(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=0)

        mock_event = MagicMock()
        mock_event.is_directory = False
        mock_event.src_path = "/repo/server.py"

        handler.on_modified(mock_event)
        loop.run_until_complete(asyncio.sleep(0))

        assert not event_queue.empty()

    def test_on_modified_ignores_directory(self):
        drain_queue()
        loop = asyncio.get_event_loop()
        handler = GitFileHandler(loop, debounce_seconds=0)

        mock_event = MagicMock()
        mock_event.is_directory = True
        mock_event.src_path = "/repo/src"

        handler.on_modified(mock_event)

        assert event_queue.empty()


class TestEventQueue:
    def test_queue_is_async(self):
        drain_queue()
        event_queue.put_nowait({"type": "test", "detail": "hello"})

        assert not event_queue.empty()
        event = run(event_queue.get())
        assert event["type"] == "test"

    def test_batch_drain(self):
        """Multiple events can be batched by draining the queue"""
        drain_queue()
        event_queue.put_nowait({"type": "a", "detail": "1"})
        event_queue.put_nowait({"type": "b", "detail": "2"})
        event_queue.put_nowait({"type": "c", "detail": "3"})

        events = []
        while not event_queue.empty():
            events.append(event_queue.get_nowait())

        assert len(events) == 3
        assert [e["type"] for e in events] == ["a", "b", "c"]


class TestWebhookParsing:
    def test_github_event_types_mapped(self):
        """Verify event type mapping via format_github_event"""
        etype, _, _ = format_github_event("pull_request_review", {"action": "submitted", "review": {"user": {"login": "u"}, "state": "approved", "html_url": ""}, "pull_request": {"number": 1}})
        assert etype == "pr_review"

        etype, _, _ = format_github_event("push", {"pusher": {"name": "t"}, "ref": "refs/heads/main", "commits": []})
        assert etype == "push"

        etype, _, _ = format_github_event("unknown_event", {})
        assert etype == "unknown_event"

    def test_push_event_detail(self):
        body = {"pusher": {"name": "alice"}, "ref": "refs/heads/main", "commits": [{"id": "abc1234567", "message": "fix bug"}]}
        etype, detail, msg = format_github_event("push", body)
        assert etype == "push"
        assert "alice" in detail
        assert "main" in detail
        assert msg is not None
        assert "alice" in msg
        assert "fix bug" in msg

    def test_issues_event_detail(self):
        body = {"action": "opened", "issue": {"title": "Bug report", "number": 42, "user": {"login": "bob"}, "html_url": "https://github.com/test/1"}}
        etype, detail, msg = format_github_event("issues", body)
        assert etype == "new_issue"
        assert "Bug report" in detail
        assert msg is not None
        assert "#42" in msg
        assert "bob" in msg

    def test_issue_comment_event(self):
        body = {"action": "created", "issue": {"number": 10}, "comment": {"user": {"login": "carol"}, "body": "Looks good!", "html_url": "https://github.com/test/c"}}
        etype, detail, msg = format_github_event("issue_comment", body)
        assert etype == "issue_comment"
        assert "carol" in detail
        assert msg is not None
        assert "Looks good!" in msg

    def test_pull_request_event(self):
        body = {"action": "opened", "pull_request": {"number": 7, "title": "Add feature", "user": {"login": "dave"}, "html_url": "https://github.com/test/pr/7"}}
        etype, detail, msg = format_github_event("pull_request", body)
        assert etype == "pull_request"
        assert "#7" in detail
        assert msg is not None
        assert "dave" in msg

    def test_pr_review_comment_event(self):
        body = {"action": "created", "comment": {"user": {"login": "eve"}, "body": "Nit: typo", "html_url": "https://github.com/test/rc"}, "pull_request": {"number": 5}}
        etype, detail, msg = format_github_event("pull_request_review_comment", body)
        assert etype == "pr_review_comment"
        assert "eve" in detail
        assert msg is not None
        assert "Nit: typo" in msg

    def test_check_run_no_discord_message(self):
        """check_run should NOT produce a discord message"""
        etype, detail, msg = format_github_event("check_run", {"action": "completed"})
        assert etype == "ci_status"
        assert msg is None

    def test_ping_no_discord_message(self):
        """ping event should NOT produce a discord message"""
        etype, detail, msg = format_github_event("ping", {"zen": "test"})
        assert msg is None


def _sign(secret: str, body: bytes) -> str:
    """Compute GitHub-style HMAC-SHA256 signature"""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


PUSH_PAYLOAD = {"pusher": {"name": "tester"}, "ref": "refs/heads/main"}


@pytest.mark.asyncio
class TestWebhookSignatureVerification:
    async def test_valid_signature_returns_200(self):
        hmac_key = "test-key"
        original = CONFIG["github_webhook_secret"]
        CONFIG["github_webhook_secret"] = hmac_key
        try:
            drain_queue()
            body = json.dumps(PUSH_PAYLOAD).encode()
            sig = _sign(hmac_key, body)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/webhook/github",
                    content=body,
                    headers={
                        "X-GitHub-Event": "push",
                        "X-Hub-Signature-256": sig,
                        "Content-Type": "application/json",
                    },
                )
            assert resp.status_code == 200
            assert resp.json()["event_type"] == "push"
        finally:
            CONFIG["github_webhook_secret"] = original

    async def test_invalid_signature_returns_403(self):
        hmac_key = "test-key"
        original = CONFIG["github_webhook_secret"]
        CONFIG["github_webhook_secret"] = hmac_key
        try:
            body = json.dumps(PUSH_PAYLOAD).encode()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/webhook/github",
                    content=body,
                    headers={
                        "X-GitHub-Event": "push",
                        "X-Hub-Signature-256": "sha256=invalid",
                        "Content-Type": "application/json",
                    },
                )
            assert resp.status_code == 403
        finally:
            CONFIG["github_webhook_secret"] = original

    async def test_no_secret_skips_verification(self):
        original = CONFIG["github_webhook_secret"]
        CONFIG["github_webhook_secret"] = ""
        try:
            drain_queue()
            body = json.dumps(PUSH_PAYLOAD).encode()
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/webhook/github",
                    content=body,
                    headers={
                        "X-GitHub-Event": "push",
                        "Content-Type": "application/json",
                    },
                )
            assert resp.status_code == 200
        finally:
            CONFIG["github_webhook_secret"] = original


@pytest.mark.asyncio
class TestDirectDiscordNotification:
    """Verify send_direct_discord_notification tries bot then webhook"""

    async def test_sends_via_webhook_when_no_bot(self):
        """When discord_bot is None, falls back to webhook URL"""
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = MagicMock()
            mock_resp.status = 204
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = asyncio.coroutine(lambda s: mock_resp)
            mock_ctx.__aexit__ = asyncio.coroutine(lambda s, *a: None)
            mock_session = MagicMock()
            mock_session.post.return_value = mock_ctx
            mock_session.__aenter__ = asyncio.coroutine(lambda s: mock_session)
            mock_session.__aexit__ = asyncio.coroutine(lambda s, *a: None)
            mock_session_cls.return_value = mock_session

            await send_direct_discord_notification(
                "Test message",
                discord_bot=None,
                webhook_url="https://discord.com/api/webhooks/test/fake",
            )
            mock_session.post.assert_called_once()

    async def test_webhook_endpoint_triggers_notification(self):
        """POST to /webhook/github with a supported event fires create_task"""
        original_secret = CONFIG["github_webhook_secret"]
        CONFIG["github_webhook_secret"] = ""
        try:
            drain_queue()
            payload = {"action": "opened", "issue": {"title": "Test", "number": 1, "user": {"login": "u"}, "html_url": ""}}
            body = json.dumps(payload).encode()
            with patch("asyncio.create_task") as mock_ct:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    resp = await ac.post(
                        "/webhook/github",
                        content=body,
                        headers={"X-GitHub-Event": "issues", "Content-Type": "application/json"},
                    )
                assert resp.status_code == 200
                mock_ct.assert_called_once()
        finally:
            CONFIG["github_webhook_secret"] = original_secret

    async def test_check_run_does_not_trigger_notification(self):
        """check_run should NOT fire create_task for discord"""
        original_secret = CONFIG["github_webhook_secret"]
        CONFIG["github_webhook_secret"] = ""
        try:
            drain_queue()
            body = json.dumps({"action": "completed"}).encode()
            with patch("asyncio.create_task") as mock_ct:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    resp = await ac.post(
                        "/webhook/github",
                        content=body,
                        headers={"X-GitHub-Event": "check_run", "Content-Type": "application/json"},
                    )
                assert resp.status_code == 200
                mock_ct.assert_not_called()
        finally:
            CONFIG["github_webhook_secret"] = original_secret
