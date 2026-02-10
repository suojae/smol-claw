"""Tests for HormoneMemory (vector DB emotional episode memory)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.hormone_memory import (
    HormoneEpisode,
    HormoneMemory,
    VECTOR_DB_AVAILABLE,
)


# ----------------------------------------------------------------
# Skip vector DB tests if dependencies are not installed
# ----------------------------------------------------------------
needs_vector_db = pytest.mark.skipif(
    not VECTOR_DB_AVAILABLE,
    reason="chromadb or sentence-transformers not installed",
)


def _make_episode(**kwargs) -> HormoneEpisode:
    """Helper to create a test episode with defaults."""
    defaults = dict(
        timestamp="2025-01-01T00:00:00",
        dopamine=0.5,
        cortisol=0.0,
        energy=1.0,
        emotional_state="balanced",
        events="git push detected",
        decision_action="notify",
        decision_message="New commit pushed",
        outcome_summary="User acknowledged",
    )
    defaults.update(kwargs)
    return HormoneEpisode(**defaults)


class TestGracefulFallback:
    def test_disabled_when_imports_missing(self, tmp_path):
        """HormoneMemory should disable gracefully when deps are missing."""
        with patch("src.hormone_memory.VECTOR_DB_AVAILABLE", False):
            mem = HormoneMemory.__new__(HormoneMemory)
            mem.enabled = False
            mem._collection = None
            mem._embedder = None

            # record and recall should be no-ops
            mem.record_episode(_make_episode())
            result = mem.recall_similar("test query")
            assert result == []

    def test_experience_context_empty_when_disabled(self):
        """get_experience_context should return empty string when disabled."""
        mem = HormoneMemory.__new__(HormoneMemory)
        mem.enabled = False
        mem._collection = None
        mem._embedder = None

        ctx = mem.get_experience_context("test")
        assert ctx == ""


@needs_vector_db
class TestEpisodeRecording:
    def test_record_and_count(self, tmp_path):
        """Recording an episode should increase collection count."""
        mem = HormoneMemory(persist_dir=str(tmp_path / "chroma"))
        assert mem.enabled

        mem.record_episode(_make_episode())
        assert mem._collection.count() == 1

    def test_record_multiple(self, tmp_path):
        """Multiple episodes should all be stored."""
        mem = HormoneMemory(persist_dir=str(tmp_path / "chroma"))

        mem.record_episode(_make_episode(emotional_state="excited", events="positive feedback"))
        mem.record_episode(_make_episode(emotional_state="defensive", events="error occurred"))
        mem.record_episode(_make_episode(emotional_state="balanced", events="routine check"))

        assert mem._collection.count() == 3


@needs_vector_db
class TestSimilaritySearch:
    def test_recall_returns_results(self, tmp_path):
        """recall_similar should return past episodes."""
        mem = HormoneMemory(persist_dir=str(tmp_path / "chroma"))

        mem.record_episode(_make_episode(
            emotional_state="excited",
            events="positive user feedback",
            decision_action="notify",
            outcome_summary="good engagement",
        ))
        mem.record_episode(_make_episode(
            emotional_state="defensive",
            events="deployment failure",
            decision_action="none",
            outcome_summary="waited and recovered",
        ))

        results = mem.recall_similar("감정:excited 이벤트:positive feedback")
        assert len(results) > 0
        assert "emotional_state" in results[0]
        assert "action" in results[0]

    def test_recall_empty_collection(self, tmp_path):
        """recall_similar should return empty list when no episodes exist."""
        mem = HormoneMemory(persist_dir=str(tmp_path / "chroma"))
        results = mem.recall_similar("test query")
        assert results == []


@needs_vector_db
class TestExperienceContext:
    def test_context_format(self, tmp_path):
        """get_experience_context should return formatted context string."""
        mem = HormoneMemory(persist_dir=str(tmp_path / "chroma"))

        mem.record_episode(_make_episode(
            emotional_state="defensive",
            decision_action="none",
            outcome_summary="safe outcome",
        ))

        ctx = mem.get_experience_context("감정:defensive 이벤트:error")
        assert "[Past Similar Experiences]" in ctx
        assert "defensive" in ctx
        assert "none" in ctx

    def test_context_empty_when_no_episodes(self, tmp_path):
        """get_experience_context should return empty string when no episodes."""
        mem = HormoneMemory(persist_dir=str(tmp_path / "chroma"))
        ctx = mem.get_experience_context("test")
        assert ctx == ""


class TestEpisodeToText:
    def test_text_contains_fields(self):
        """_episode_to_text should include all key fields."""
        ep = _make_episode(
            emotional_state="excited",
            events="git push",
            decision_action="notify",
            outcome_summary="acknowledged",
        )
        text = HormoneMemory._episode_to_text(ep)
        assert "excited" in text
        assert "git push" in text
        assert "notify" in text
        assert "acknowledged" in text
