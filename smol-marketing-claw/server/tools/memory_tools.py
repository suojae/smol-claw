"""MCP tool for vector memory search."""

from server.mcp_server import mcp
from server.state import get_state


@mcp.tool()
async def smol_claw_memory_query(query: str, n_results: int = 3) -> dict:
    """Search past experiences using vector similarity.

    Args:
        query: Natural language query to search for similar past episodes.
        n_results: Number of results to return (default: 3, max: 10).
    """
    state = get_state()
    n_results = max(1, min(10, n_results))

    # Vector DB search
    episodes = []
    if state.hormone_memory and state.hormone_memory.enabled:
        episodes = state.hormone_memory.recall_similar(query, n_results=n_results)

    # Also include recent decisions from JSON memory
    recent_decisions = state.memory.load_decisions()[-5:]

    return {
        "vector_results": episodes,
        "recent_decisions": recent_decisions,
        "vector_db_enabled": state.hormone_memory.enabled if state.hormone_memory else False,
    }
