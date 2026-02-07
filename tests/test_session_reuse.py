"""Tests for AutonomousEngine session reuse"""

import os
import sys
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Import from the server module
import importlib.util

spec = importlib.util.spec_from_file_location(
    "server", os.path.join(os.path.dirname(os.path.dirname(__file__)), "autonomous-ai-server.py")
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

AutonomousEngine = server.AutonomousEngine
ClaudeExecutor = server.ClaudeExecutor
ContextCollector = server.ContextCollector
GuardrailMemory = server.GuardrailMemory


class TestSessionReuse:
    def _make_engine(self):
        claude = ClaudeExecutor()
        context = ContextCollector()
        engine = AutonomousEngine(claude, context)
        return engine

    def test_first_call_creates_session(self):
        engine = self._make_engine()
        assert engine._session_id is None
        assert engine._session_call_count == 0

        session_id = engine._get_or_reset_session()
        assert session_id is not None
        assert engine._session_call_count == 0

    def test_session_persists_within_limit(self):
        engine = self._make_engine()
        first_id = engine._get_or_reset_session()

        # Simulate calls within limit
        engine._session_call_count = 10
        second_id = engine._get_or_reset_session()

        assert first_id == second_id

    def test_session_resets_at_limit(self):
        engine = self._make_engine()
        first_id = engine._get_or_reset_session()

        # Simulate reaching the limit
        engine._session_call_count = engine.MAX_CALLS_PER_SESSION
        second_id = engine._get_or_reset_session()

        assert first_id != second_id
        assert engine._session_call_count == 0

    def test_is_first_call_in_session(self):
        engine = self._make_engine()
        engine._get_or_reset_session()

        assert engine.is_first_call_in_session is True

        engine._session_call_count = 1
        assert engine.is_first_call_in_session is False

    def test_max_calls_per_session_default(self):
        assert AutonomousEngine.MAX_CALLS_PER_SESSION == 50

    def test_session_resets_multiple_times(self):
        engine = self._make_engine()
        seen_ids = set()

        for _ in range(3):
            session_id = engine._get_or_reset_session()
            seen_ids.add(session_id)
            engine._session_call_count = engine.MAX_CALLS_PER_SESSION

        # Should have created 3 different sessions
        assert len(seen_ids) == 3
