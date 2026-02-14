"""MCP tools for SNS posting (X/Twitter and Threads)."""

from server.mcp_server import mcp
from server.state import get_state


@mcp.tool()
async def smol_claw_post_x(text: str) -> dict:
    """Post a tweet to X (Twitter).

    Args:
        text: The tweet text (max 280 characters, auto-truncated).
    """
    state = get_state()

    if not state.x_client.is_configured:
        return {"success": False, "error": "X API not configured. Set X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET."}

    result = await state.x_client.post(text)

    # Hormone feedback
    if state.hormones:
        if result.success:
            state.hormones.trigger_dopamine(0.1)
        else:
            state.hormones.trigger_cortisol(0.1)
        state.hormones.save_state()

    return {
        "success": result.success,
        "post_id": result.post_id,
        "text": result.text,
        "error": result.error,
    }


@mcp.tool()
async def smol_claw_reply_x(text: str, tweet_id: str) -> dict:
    """Reply to a tweet on X (Twitter).

    Args:
        text: The reply text (max 280 characters, auto-truncated).
        tweet_id: The ID of the tweet to reply to.
    """
    state = get_state()

    if not state.x_client.is_configured:
        return {"success": False, "error": "X API not configured."}

    result = await state.x_client.reply(text, tweet_id)

    if state.hormones:
        if result.success:
            state.hormones.trigger_dopamine(0.05)
        else:
            state.hormones.trigger_cortisol(0.1)
        state.hormones.save_state()

    return {
        "success": result.success,
        "post_id": result.post_id,
        "text": result.text,
        "error": result.error,
    }


@mcp.tool()
async def smol_claw_post_threads(text: str) -> dict:
    """Post to Threads (Meta).

    Args:
        text: The post text (max 500 characters, auto-truncated).
    """
    state = get_state()

    if not state.threads_client.is_configured:
        return {"success": False, "error": "Threads API not configured. Set THREADS_USER_ID and THREADS_ACCESS_TOKEN."}

    result = await state.threads_client.post(text)

    if state.hormones:
        if result.success:
            state.hormones.trigger_dopamine(0.1)
        else:
            state.hormones.trigger_cortisol(0.1)
        state.hormones.save_state()

    return {
        "success": result.success,
        "post_id": result.post_id,
        "text": result.text,
        "error": result.error,
    }


@mcp.tool()
async def smol_claw_reply_threads(text: str, post_id: str) -> dict:
    """Reply to a post on Threads (Meta).

    Args:
        text: The reply text (max 500 characters, auto-truncated).
        post_id: The ID of the Threads post to reply to.
    """
    state = get_state()

    if not state.threads_client.is_configured:
        return {"success": False, "error": "Threads API not configured."}

    result = await state.threads_client.reply(text, post_id)

    if state.hormones:
        if result.success:
            state.hormones.trigger_dopamine(0.05)
        else:
            state.hormones.trigger_cortisol(0.1)
        state.hormones.save_state()

    return {
        "success": result.success,
        "post_id": result.post_id,
        "text": result.text,
        "error": result.error,
    }
