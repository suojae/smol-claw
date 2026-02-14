"""MCP tools for hormone system status and manual nudge."""

from server.mcp_server import mcp
from server.state import get_state


@mcp.tool()
async def smol_claw_status() -> dict:
    """Return full system status: hormones, usage stats, and SNS configuration.

    Use this to check the current emotional state, API usage,
    and which SNS platforms are configured.
    """
    state = get_state()
    state.reload_hormones_if_stale()

    hormone_status = state.hormones.get_status_dict()
    usage_status = state.usage_tracker.get_status()

    sns_config = {
        "x_configured": state.x_client.is_configured,
        "threads_configured": state.threads_client.is_configured,
    }

    discord_status = "stopped"
    if state.discord_bot is not None:
        discord_status = "running" if not state.discord_bot.is_closed() else "stopped"

    return {
        "hormones": hormone_status,
        "usage": usage_status,
        "sns": sns_config,
        "discord": discord_status,
    }


@mcp.tool()
async def smol_claw_hormone_nudge(
    dopamine_delta: float = 0.0,
    cortisol_delta: float = 0.0,
) -> dict:
    """Manually adjust hormone levels.

    Args:
        dopamine_delta: Dopamine change (-0.3 to 0.3). Positive = reward, negative = boredom.
        cortisol_delta: Cortisol change (-0.3 to 0.3). Positive = stress, negative = calm.
    """
    state = get_state()
    state.reload_hormones_if_stale()

    # Clamp deltas
    dopamine_delta = max(-0.3, min(0.3, dopamine_delta))
    cortisol_delta = max(-0.3, min(0.3, cortisol_delta))

    if dopamine_delta:
        state.hormones.trigger_dopamine(dopamine_delta)
    if cortisol_delta:
        state.hormones.trigger_cortisol(cortisol_delta)

    state.hormones.save_state()

    return {
        "applied": {
            "dopamine_delta": dopamine_delta,
            "cortisol_delta": cortisol_delta,
        },
        "new_state": state.hormones.get_status_dict(),
    }
