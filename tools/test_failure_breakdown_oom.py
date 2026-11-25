"""DIECLASS_1125 (COORD 11-25): a kit whose OOM retry budget is spent is listed as OOM-EXHAUSTED, never folded into stopped / other."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failure_breakdown as FB  # noqa: E402


def test_oom_exhausted_class():
    r = {"status": "CRASH", "class": "INFRA", "reason": "OOM-EXHAUSTED (2 OOM retries used, --mem 54) infra-oom: make: *** [x] Error 137"}
    assert FB.label(r) == "OOM-EXHAUSTED"
    assert FB.label(dict(r, reason="infra-stopped: exit 143, no OOM line in the run logs: stopped from outside")) == "stopped (ruling/infra)"
