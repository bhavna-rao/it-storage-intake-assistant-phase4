"""
Unit tests for the deterministic decision logic in intake_assistant.py.

Scope, deliberately narrow: this tests ONLY `decide()` — the one piece of
the Phase 4 prototype that must always be correct, per the design
principle stated in the README (the AI extracts free text; a fixed
Python rule makes the approve/route decision, never the AI).

This does NOT test `extract_fields()` (that calls the live Anthropic API
and is instead verified with real conversations — see
Phase4_Live_Verification_Record.docx for that evidence). Keeping these
two kinds of testing separate is intentional: `decide()` is pure and
deterministic, so it can be checked exhaustively and instantly, with no
API key and no network call required.

Run with:
    pip install -r requirements-dev.txt
    pytest test_intake_assistant.py -v
"""

import pytest
from intake_assistant import decide, AUTO_APPROVE_THRESHOLD_GB


class TestDecideBoundary:
    """The cases that actually matter for a threshold rule: exactly on
    the line, and one unit on either side of it. Neither of the two
    live Colab scenarios (5 GB and 50 GB) landed on this boundary, so
    this is the coverage those runs didn't provide."""

    def test_exactly_at_threshold_is_auto_approved(self):
        # decide() uses <=, so the threshold itself is inclusive.
        assert decide(AUTO_APPROVE_THRESHOLD_GB) == "auto_approved"

    def test_just_below_threshold_is_auto_approved(self):
        assert decide(AUTO_APPROVE_THRESHOLD_GB - 0.01) == "auto_approved"

    def test_just_above_threshold_is_routed_for_review(self):
        assert decide(AUTO_APPROVE_THRESHOLD_GB + 0.01) == "routed_for_review"


class TestDecideNormalCases:
    """Mirrors the two live-verified Colab scenarios, so the same
    outcomes are also checked here without needing the API."""

    def test_small_request_is_auto_approved(self):
        assert decide(5.0) == "auto_approved"  # matches Live Verification Scenario 1

    def test_large_request_is_routed_for_review(self):
        assert decide(50.0) == "routed_for_review"  # matches Live Verification Scenario 2

    def test_zero_gb_is_auto_approved(self):
        assert decide(0) == "auto_approved"


class TestDecideMissingInput:
    """decide() explicitly raises rather than guessing when amount_gb
    is missing — this confirms that contract instead of assuming it."""

    def test_none_raises_value_error(self):
        with pytest.raises(ValueError):
            decide(None)


class TestDecideCustomThreshold:
    """decide() accepts an explicit threshold override — confirms the
    function isn't secretly hardcoded to the module-level constant."""

    def test_custom_threshold_below(self):
        assert decide(15, threshold=20) == "auto_approved"

    def test_custom_threshold_above(self):
        assert decide(25, threshold=20) == "routed_for_review"

    def test_custom_threshold_at_boundary(self):
        assert decide(20, threshold=20) == "auto_approved"


class TestKnownGap:
    """Documents current behavior rather than silently hiding it: decide()
    does not validate that amount_gb is non-negative. A negative number
    is nonsensical for a storage request, but as written it is treated
    like any other number below the threshold and auto-approved. This
    test exists to make that gap visible and intentional to a reader,
    not to assert it's correct — it's a known, undecided edge case,
    flagged rather than fixed silently."""

    def test_negative_amount_is_currently_auto_approved_not_rejected(self):
        assert decide(-5) == "auto_approved"
