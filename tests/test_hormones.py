"""Tests for DigitalHormones system."""

import json
from unittest.mock import MagicMock

import pytest

from src.hormones import DigitalHormones, HormoneState, HormoneControlParams


@pytest.fixture
def tracker_mock():
    """Mock UsageTracker returning 50% usage."""
    mock = MagicMock()
    mock.get_status.return_value = {
        "calls_today": 250,
        "limits": {"per_day": 500},
    }
    return mock


@pytest.fixture
def hormones(tmp_path, tracker_mock):
    """Create a DigitalHormones with temp state file."""
    state_file = tmp_path / "hormones.json"
    return DigitalHormones(state_file=str(state_file), usage_tracker=tracker_mock)


class TestInitialization:
    def test_default_values(self, hormones):
        """Should start with default hormone values."""
        assert hormones.state.dopamine == 0.5
        assert hormones.state.cortisol == 0.0
        assert hormones.state.tick_count == 0

    def test_energy_from_usage_tracker(self, hormones):
        """Energy should be derived from UsageTracker (50% used → 0.5 energy)."""
        assert hormones.state.energy == 0.5

    def test_energy_without_tracker(self, tmp_path):
        """Energy should default to 1.0 when no tracker is provided."""
        h = DigitalHormones(state_file=str(tmp_path / "h.json"))
        assert h.state.energy == 1.0


class TestDecay:
    def test_dopamine_decays_toward_half(self, hormones):
        """Dopamine should decay toward 0.5."""
        hormones.state.dopamine = 1.0
        for _ in range(50):
            hormones.decay()
        assert abs(hormones.state.dopamine - 0.5) < 0.01

    def test_dopamine_rises_toward_half(self, hormones):
        """Low dopamine should rise toward 0.5."""
        hormones.state.dopamine = 0.0
        for _ in range(50):
            hormones.decay()
        assert abs(hormones.state.dopamine - 0.5) < 0.01

    def test_cortisol_decays_toward_zero(self, hormones):
        """Cortisol should decay toward 0."""
        hormones.state.cortisol = 0.8
        for _ in range(80):
            hormones.decay()
        # 0.8 * 0.98^80 ≈ 0.16
        assert hormones.state.cortisol < 0.2

    def test_tick_count_increments(self, hormones):
        """Tick count should increase each decay call."""
        hormones.decay()
        hormones.decay()
        assert hormones.state.tick_count == 2


class TestTriggers:
    def test_dopamine_increase(self, hormones):
        """trigger_dopamine should increase dopamine."""
        initial = hormones.state.dopamine
        hormones.trigger_dopamine(0.2)
        assert hormones.state.dopamine == pytest.approx(initial + 0.2)

    def test_cortisol_increase(self, hormones):
        """trigger_cortisol should increase cortisol."""
        hormones.trigger_cortisol(0.3)
        assert hormones.state.cortisol == pytest.approx(0.3)

    def test_dopamine_clamped_at_one(self, hormones):
        """Dopamine should not exceed 1.0."""
        hormones.trigger_dopamine(1.0)
        assert hormones.state.dopamine == 1.0

    def test_cortisol_clamped_at_zero(self, hormones):
        """Cortisol should not go below 0.0."""
        hormones.trigger_cortisol(-1.0)
        assert hormones.state.cortisol == 0.0

    def test_dopamine_clamped_at_zero(self, hormones):
        """Dopamine should not go below 0.0."""
        hormones.trigger_dopamine(-2.0)
        assert hormones.state.dopamine == 0.0


class TestPersistence:
    def test_cortisol_persists_across_restarts(self, tmp_path, tracker_mock):
        """Cortisol should survive restarts."""
        state_file = str(tmp_path / "hormones.json")

        h1 = DigitalHormones(state_file=state_file, usage_tracker=tracker_mock)
        h1.trigger_cortisol(0.7)
        h1.save_state()

        h2 = DigitalHormones(state_file=state_file, usage_tracker=tracker_mock)
        assert h2.state.cortisol == pytest.approx(0.7)

    def test_dopamine_resets_on_restart(self, tmp_path, tracker_mock):
        """Dopamine should reset to 0.5 on restart."""
        state_file = str(tmp_path / "hormones.json")

        h1 = DigitalHormones(state_file=state_file, usage_tracker=tracker_mock)
        h1.trigger_dopamine(0.4)  # dopamine → 0.9
        h1.save_state()

        h2 = DigitalHormones(state_file=state_file, usage_tracker=tracker_mock)
        assert h2.state.dopamine == 0.5

    def test_tick_count_persists(self, tmp_path, tracker_mock):
        """Tick count should survive restarts."""
        state_file = str(tmp_path / "hormones.json")

        h1 = DigitalHormones(state_file=state_file, usage_tracker=tracker_mock)
        h1.decay()
        h1.decay()
        h1.save_state()

        h2 = DigitalHormones(state_file=state_file, usage_tracker=tracker_mock)
        assert h2.state.tick_count == 2


class TestControlParams:
    def test_high_cortisol_gives_cautious(self, hormones):
        """High cortisol should yield cautious instructions."""
        hormones.state.cortisol = 0.9
        params = hormones.get_control_params()
        assert "cautious" in params.creativity_instruction.lower()

    def test_high_dopamine_gives_creative(self, hormones):
        """High dopamine should yield creative instructions."""
        hormones.state.dopamine = 0.8
        hormones.state.cortisol = 0.0  # ensure cortisol doesn't override
        params = hormones.get_control_params()
        assert "creative" in params.creativity_instruction.lower()

    def test_low_energy_gives_haiku(self, tmp_path):
        """Low energy should select haiku model."""
        mock = MagicMock()
        mock.get_status.return_value = {
            "calls_today": 450,
            "limits": {"per_day": 500},
        }
        h = DigitalHormones(state_file=str(tmp_path / "h.json"), usage_tracker=mock)
        # energy = 1 - 450/500 = 0.1
        params = h.get_control_params()
        assert params.model == "haiku"

    def test_normal_energy_gives_sonnet(self, hormones):
        """Normal energy should select sonnet model."""
        params = hormones.get_control_params()
        assert params.model == "sonnet"

    def test_high_cortisol_low_posting(self, hormones):
        """High cortisol should reduce posting frequency."""
        hormones.state.cortisol = 0.8
        params = hormones.get_control_params()
        assert params.posting_frequency_multiplier < 1.0

    def test_high_dopamine_verbose_response(self, hormones):
        """High dopamine should yield verbose responses."""
        hormones.state.dopamine = 0.8
        hormones.state.cortisol = 0.0
        params = hormones.get_control_params()
        assert params.max_response_length == "verbose"


class TestStatusDict:
    def test_has_required_keys(self, hormones):
        """get_status_dict should contain all expected keys."""
        status = hormones.get_status_dict()
        expected = {
            "dopamine", "cortisol", "energy", "tick_count",
            "label", "effective_model", "creativity_mode",
            "posting_multiplier", "response_length",
        }
        assert expected.issubset(status.keys())

    def test_label_defensive(self, hormones):
        """High cortisol should label as defensive."""
        hormones.state.cortisol = 0.9
        assert hormones._label_state() == "defensive"

    def test_label_excited(self, hormones):
        """High dopamine should label as excited."""
        hormones.state.dopamine = 0.8
        hormones.state.cortisol = 0.0
        assert hormones._label_state() == "excited"

    def test_label_balanced(self, hormones):
        """Default state should be balanced."""
        assert hormones._label_state() == "balanced"

    def test_label_lethargic(self, hormones):
        """Low dopamine should label as lethargic."""
        hormones.state.dopamine = 0.2
        hormones.state.cortisol = 0.0
        assert hormones._label_state() == "lethargic"
