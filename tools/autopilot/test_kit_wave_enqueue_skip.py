"""KIT-OPS-5 11-15: enqueue refuses held items and attempts of an older plan event (SKIP-HELD / SKIP-OLDPLAN)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

CFG = {"dies": {"qwen_compute": {"event": "s29q103S4C", "hold_items": {"cbn_q11__*": "cb class", "sle_stm_v1__cl27746664": "hold-stall"}}}}


def row(item, event="s29q103S4C"):
    return {"die": "qwen_compute", "item": item, "event": event, "attempt": 3}


def test_held_item_is_skipped_even_on_the_current_plan():
    tag, text = KW.enqueue_skip_reason(CFG, row("cbn_q11__cl49ae4555"))
    assert tag == "SKIP-HELD" and "cb class" in text
    assert KW.enqueue_skip_reason(CFG, row("sle_stm_v1__cl27746664"))[0] == "SKIP-HELD"


def test_old_plan_attempt_is_skipped():
    tag, text = KW.enqueue_skip_reason(CFG, row("sle_fw_v1__clf58b4dfb", event="s29q103S3R"))
    assert tag == "SKIP-OLDPLAN" and "s29q103S3R" in text and "s29q103S4C" in text


def test_current_unheld_row_passes():
    assert KW.enqueue_skip_reason(CFG, row("sle_fw_v1__clf58b4dfb")) is None


def test_missing_event_never_blocks():
    assert KW.enqueue_skip_reason(CFG, {"die": "qwen_compute", "item": "x"}) is None
    assert KW.enqueue_skip_reason({"dies": {}}, row("x")) is None


def test_old_event_with_unchanged_plan_block_is_not_skipped(monkeypatch):
    monkeypatch.setattr(KW, "_plan_current", lambda cfg, st, rec: True)
    assert KW.enqueue_skip_reason(CFG, row("sle_fw_v1__clf58b4dfb", event="s29q103S3R"), {}) is None
    monkeypatch.setattr(KW, "_plan_current", lambda cfg, st, rec: False)
    assert KW.enqueue_skip_reason(CFG, row("sle_fw_v1__clf58b4dfb", event="s29q103S3R"), {})[0] == "SKIP-OLDPLAN"
    monkeypatch.setattr(KW, "_plan_current", lambda cfg, st, rec: None)      # WAVE-PILOT-FIX 11-19: an unprobed new event is unknown, not old: the row routes
    assert KW.enqueue_skip_reason(CFG, row("sle_fw_v1__clf58b4dfb", event="s29q103S3R"), {}) is None
