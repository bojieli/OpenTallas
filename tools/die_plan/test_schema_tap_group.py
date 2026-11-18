"""KW-FIX-45 11-12: clock.tap_group is a schema key (gen_phys.tap_group_exports emitted OT_TAP_GROUP_RE from it, but
validate refused the key as unknown)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402

SRC = (Path(__file__).resolve().parent / "schema.py").read_text()


def test_tap_group_declared():
    assert '"tap_group": {"type": "object", "additionalProperties": False, "required": ["re"]' in SRC


def test_tap_group_export():
    t = {"clock": {"tap_group": {"re": "(?:^|[/.])u_(?:cland|bin)_(rec_tx_s0_i)[/.]"}}}
    assert gen_phys.tap_group_exports(t) == ["export OT_TAP_GROUP_RE = (?:^|[/.])u_(?:cland|bin)_(rec_tx_s0_i)[/.]"]


def test_tap_group_follow_re():
    """HEAD-TYPES-OPUS 11-18: follow_re "" turns the reset-relay follower rule off; absent keeps the clock_taps default."""
    t = {"clock": {"tap_group": {"re": "(u_l[ab]\\.u_ln\\.u\\.u_ep\\.credits)\\\\?\\[", "follow_re": ""}}}
    out = gen_phys.tap_group_exports(t)
    assert out[-1] == "export OT_TAP_FOLLOW_RE ="
    t["clock"]["tap_group"]["follow_re"] = "(?:^|[/.])(u_rrl_[0-9]+)[/.]"
    assert gen_phys.tap_group_exports(t)[-1] == "export OT_TAP_FOLLOW_RE = (?:^|[/.])(u_rrl_[0-9]+)[/.]"
    del t["clock"]["tap_group"]["follow_re"]
    assert not any("FOLLOW" in x for x in gen_phys.tap_group_exports(t))
    assert '"follow_re": {"type": "string"}' in SRC
