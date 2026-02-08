"""GitHub event formatter and direct Discord notification."""

from datetime import datetime
from typing import Dict, Any, List, Optional

import aiohttp

from src.discord_bot import DiscordBot
from src.config import CONFIG


def format_github_event(gh_event: str, body: Dict[str, Any]) -> tuple:
    """Parse GitHub webhook event into (event_type, detail, discord_message).

    Returns discord_message=None for events that should NOT trigger
    an immediate Discord notification (e.g. check_run).
    """
    event_map = {
        "pull_request_review": "pr_review",
        "issues": "new_issue",
        "push": "push",
        "check_run": "ci_status",
        "issue_comment": "issue_comment",
        "pull_request": "pull_request",
        "pull_request_review_comment": "pr_review_comment",
    }
    event_type = event_map.get(gh_event, gh_event)

    detail = f"GitHub {gh_event}"
    discord_message = None

    if gh_event == "push":
        pusher = body.get("pusher", {}).get("name", "unknown")
        ref = body.get("ref", "")
        branch = ref.replace("refs/heads/", "")
        commits = body.get("commits", [])
        detail = f"Push by {pusher} to {branch}"
        commit_lines = "\n".join(
            [f"  - `{c.get('id', '')[:7]}` {c.get('message', '').split(chr(10))[0]}" for c in commits[:5]]
        )
        discord_message = (
            f"**Push** by `{pusher}` to `{branch}`\n"
            f"Commits ({len(commits)}):\n{commit_lines}"
        )

    elif gh_event == "issues":
        action = body.get("action", "")
        issue = body.get("issue", {})
        title = issue.get("title", "")
        number = issue.get("number", "")
        user = issue.get("user", {}).get("login", "")
        url = issue.get("html_url", "")
        detail = f"Issue {action}: {title}"
        discord_message = (
            f"**Issue #{number}** {action} by `{user}`\n"
            f"**{title}**\n{url}"
        )

    elif gh_event == "issue_comment":
        action = body.get("action", "")
        issue = body.get("issue", {})
        comment = body.get("comment", {})
        number = issue.get("number", "")
        user = comment.get("user", {}).get("login", "")
        comment_body = comment.get("body", "")[:200]
        url = comment.get("html_url", "")
        detail = f"Comment on #{number} by {user}"
        discord_message = (
            f"**Comment** on #{number} by `{user}`\n"
            f"> {comment_body}\n{url}"
        )

    elif gh_event == "pull_request":
        action = body.get("action", "")
        pr = body.get("pull_request", {})
        number = pr.get("number", "")
        title = pr.get("title", "")
        user = pr.get("user", {}).get("login", "")
        url = pr.get("html_url", "")
        detail = f"PR #{number} {action}: {title}"
        discord_message = (
            f"**PR #{number}** {action} by `{user}`\n"
            f"**{title}**\n{url}"
        )

    elif gh_event == "pull_request_review":
        action = body.get("action", "")
        review = body.get("review", {})
        pr = body.get("pull_request", {})
        reviewer = review.get("user", {}).get("login", "")
        state = review.get("state", "")
        number = pr.get("number", "")
        url = review.get("html_url", "")
        detail = f"PR review {action} by {reviewer}"
        state_emoji = {"approved": "approved", "changes_requested": "changes requested", "commented": "commented"}.get(state, state)
        discord_message = (
            f"**PR #{number} Review** — {state_emoji} by `{reviewer}`\n{url}"
        )

    elif gh_event == "pull_request_review_comment":
        action = body.get("action", "")
        comment = body.get("comment", {})
        pr = body.get("pull_request", {})
        user = comment.get("user", {}).get("login", "")
        number = pr.get("number", "")
        comment_body = comment.get("body", "")[:200]
        url = comment.get("html_url", "")
        detail = f"Review comment on PR #{number} by {user}"
        discord_message = (
            f"**Review comment** on PR #{number} by `{user}`\n"
            f"> {comment_body}\n{url}"
        )

    # check_run, ping, etc. -> discord_message stays None

    return event_type, detail, discord_message


async def send_direct_discord_notification(
    message: str,
    discord_bot: Optional["DiscordBot"] = None,
    webhook_url: str = "",
):
    """Send Discord notification directly — independent of AutonomousEngine.

    Tries Discord bot channel first, then falls back to webhook URL.
    """
    sent = False

    # 1) Try Discord bot channel
    if discord_bot and discord_bot.notification_channel:
        try:
            for chunk in DiscordBot._split_message(message):
                await discord_bot.notification_channel.send(chunk)
            print("Direct Discord notification sent (bot channel)")
            sent = True
        except Exception as e:
            print(f"Discord bot send failed: {e}")

    # 2) Fallback to webhook URL
    if not sent and webhook_url:
        try:
            embed = {
                "title": "GitHub Event",
                "description": message,
                "color": 5814783,  # Blue (#58ACFF)
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Smol Claw — instant webhook notification"},
            }
            payload = {
                "username": "Smol Claw",
                "avatar_url": "https://raw.githubusercontent.com/suojae/smol-claw/main/.github/crayfish.svg",
                "embeds": [embed],
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status == 204:
                        print("Direct Discord notification sent (webhook)")
                    else:
                        print(f"Discord webhook returned {resp.status}")
        except Exception as e:
            print(f"Direct Discord notification failed: {e}")
