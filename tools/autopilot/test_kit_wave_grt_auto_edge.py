"""KW-FIX-45 11-11 (COORD/OWNER edge-only halving default): the GRT-overflow fail class is recorded per row and an
auto edge_outline env is added to the next attempt of such a row."""
import json
import kit_wave as KW


def run(tmp_path, monkeypatch, why):
    d = tmp_path / "ap"; d.mkdir(exist_ok=True)
    (d / "state.json").write_text(json.dumps({"jobs": {"j1": {"id": "j1", "kit": "h:/k/x", "updated": 1}}}))
    monkeypatch.setattr(KW, "queue_class", lambda j: ("route", "FAIL", "FLOW", why))
    st = {"items": {"k": {"die": "hbm", "item": "x", "attempt": 1, "status": "ENQUEUED", "kit": "h:/k/x"}}}
    KW.follow_queue(st, d, {})
    return st["items"]["k"]


def test_overflow_fail_is_recorded(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, "flow-error: [ERROR GRT-0116] Global routing finished with overflow")["grt_overflow"] is True
    assert run(tmp_path, monkeypatch, "overflow 0.253 > 0.1 (capped pass 1)")["grt_overflow"] is True


def test_other_fail_is_not_overflow(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, "flow-error: [ERROR GRT-0080] Invalid pin placement.")["grt_overflow"] is False
    assert run(tmp_path, monkeypatch, "gate: setup slack -12 ps")["grt_overflow"] is False


def test_launch_hook_present_and_opt_out():
    src = open(KW.__file__).read()
    assert "prev.get(\"grt_overflow\")" in src and "auto_grt_edge" in src
    assert "\"OT_GRT_TRANSITION_MODE\" not in sp[\"gen_env\"]" in src
