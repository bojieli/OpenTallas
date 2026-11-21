"""FLOW-FIX-0100 (FABLE-FLOW-2350 d): a retry key names fix=<sha or row>; an unchanged input digest is refused except for INFRA failures."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def cfg_with(retry):
    return KW.load_config('{"dies": {"s81": {"retry": %s}}}' % __import__("json").dumps(retry))


def st_with(status="FAIL", reason="make Error 1 in place", cls="FLOW", attempt=2):
    return {"items": {"a": {"die": "s81", "item": "t4", "attempt": attempt, "status": status, "reason": reason, "class": cls, "started": 10}}}


def test_fix_suffix_is_normalised_and_plain_keys_need_infra():
    cfg = cfg_with(["t4@2:fix=abc1234", "t5@1"])
    d = cfg["dies"]["s81"]
    assert d["retry"] == ["t4@2", "t5@1"] and d["_retry_fix"] == {"t4@2": "abc1234"}
    st = st_with()
    assert KW.retry_key_allowed(cfg, st, "s81", "t4", "t4@2") is True
    st5 = {"items": {"b": {"die": "s81", "item": "t5", "attempt": 1, "status": "FAIL", "reason": "cone has more than 47400 cells", "class": "FLOW", "started": 1}}}
    assert KW.retry_key_allowed(cfg, st5, "s81", "t5", "t5@1") is False
    st5["items"]["b"]["class"] = "INFRA"
    assert KW.retry_key_allowed(cfg, st5, "s81", "t5", "t5@1") is True            # INFRA: no fix needed


def test_explicit_retry_pending_ignores_a_key_without_fix():
    st = st_with()
    assert KW.explicit_retry_pending(cfg_with(["t4@2"]), st, "s81", "t4") is False
    assert KW.explicit_retry_pending(cfg_with(["t4@2:fix=row-17"]), st, "s81", "t4") is True
    assert KW.explicit_retry_pending(cfg_with(["t4@2"]), st_with(cls="INFRA", reason="make Error 247"), "s81", "t4") is True
