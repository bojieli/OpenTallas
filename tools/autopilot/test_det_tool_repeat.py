"""KV-NOADVANCE 11-25: a deterministic tool exception on an unchanged plan block is not retried as INFRA."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

WHY = "infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: AttributeError: module 'reset_tree' has no attribute 'raw_tap_hold'"


def rec(n, **kw):
    r = dict(die="qwen_kvsys", item="kv3_pv_v12e", event="E", block_sha="b1", attempt=n, status="FAIL", reason=WHY, started=n)
    r["class"] = "INFRA"
    r.update(kw)
    return r


def cfg():
    return {"dies": {"qwen_kvsys": {"event": "E", "infra_attempts": 99}}}


def test_third_identical_tool_fail_is_not_infra_retry():
    st = {"items": {f"k{n}": rec(n) for n in (1, 2)}}
    assert not KW.deterministic_tool_repeat(st, st["items"]["k2"])
    assert KW.infra_relaunch_due(cfg(), st["items"]["k2"], st)
    st["items"]["k3"] = rec(3)
    assert KW.deterministic_tool_repeat(st, st["items"]["k3"])
    assert not KW.infra_relaunch_due(cfg(), st["items"]["k3"], st)
    assert KW.infra_relaunch_due(cfg(), st["items"]["k3"])        # no state: old behaviour
    st["items"]["k3"]["block_sha"] = "b2"                          # a changed plan block counts afresh
    assert not KW.deterministic_tool_repeat(st, st["items"]["k3"])


def test_host_faults_still_retry():
    w = "infra (python exception) @gen: Traceback ... No space left on device"
    st = {"items": {f"k{n}": rec(n, reason=w) for n in (1, 2, 3, 4)}}
    assert not KW.deterministic_tool_repeat(st, st["items"]["k4"])
