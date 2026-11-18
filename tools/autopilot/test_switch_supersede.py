"""WAVE-FLOW-R2 11-17 (COORD urgent): a die tree / event switch supersedes every live attempt on another event, so the new pilots are not blocked by one-live-attempt-per-item."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW


class AP:
    DRY = False
    HUB_NAME = "intel2"
    logs, shs = [], []
    log = staticmethod(lambda m: AP.logs.append(m))
    sh = staticmethod(lambda argv, timeout=0: (AP.shs.append(argv) or (0, "", "")))
    coord_append = staticmethod(lambda *a: None)


def cfg(event="NF15f", hold=None):
    return {"dies": {"head": {"enabled": True, "src": "/k/t2", "event": event, "plan_event": None, "hold_items": hold or {}}}}


def rows():
    mk = lambda **kw: dict(die="head", **kw)
    return {"items": {
        "a": mk(item="hd_lep0N", status="ENQUEUED", q_status="RUNNING", q_id="j1", event="NF13a", attempt="3", block_sha="old1"),
        "b": mk(item="hd_mesh", status="RUNNING", unit="kw-head-mesh", event="NF15d2r1", attempt="2", stage="place", dir="/nonexistent/a2", block_sha="old2"),
        "c": mk(item="hd_same", status="RUNNING", unit="kw-head-same", event="NF15d2r1", attempt="1", stage="place", dir="/nonexistent/a1", block_sha="same1"),
        "d": mk(item="hd_new", status="RUNNING", unit="kw-head-new", event="NF15f", attempt="1", stage="place", dir="/nonexistent/n1", block_sha="n"),
        "e": mk(item="hd_done", status="FAIL", event="NF13a", attempt="1", block_sha="x"),
        "f": mk(item="hd_held", status="RUNNING", unit="kw-head-held", event="NF13a", attempt="1", stage="place", dir="/nonexistent/h1", block_sha="old3"),
    }, "adopt_seen": {"head": dict(src="/k/t2", sig=["NF15f", None], switched=True, ticks=0, sup_ticks=0)}}


def run(monkeypatch, st, c=None, tmp=None):
    AP.logs.clear(); AP.shs.clear()
    stops = []
    monkeypatch.setattr(KW, "current_blocks", lambda cfg_, st_: {"head": {"hd_same": "same1"}})
    monkeypatch.setattr(KW, "attempt_root", lambda r: "/root/" + r["item"])
    monkeypatch.setattr(KW.WJ, "stop_on_fleet", lambda sh, hub, roots: (stops.append(list(roots)) or {}))
    monkeypatch.setattr(KW.WJ, "stopped_names", lambda res: [])
    n = KW.supersede_on_switch(AP, c or cfg(), st, {}, ap_dir=tmp)
    return n, stops


def test_live_attempts_on_another_event_are_superseded(monkeypatch, tmp_path):
    import json
    (tmp_path / "state.json").write_text(json.dumps({"jobs": {"j1": {"status": "RUNNING", "unit": "ap-j1-a1"}}}))
    st = rows()
    n, stops = run(monkeypatch, st, tmp=str(tmp_path))
    assert n == 3                                                                     # hd_lep0N (queue job), hd_mesh and hd_held (wave units)
    for k in ("a", "b", "f"):
        assert st["items"][k]["status"] == "CANCELLED" and st["items"][k]["class"] == "SUPERSEDED"      # not FAIL
    assert st["items"]["c"]["status"] == "RUNNING" and "SWITCH-SUPERSEDE-KEEP" in " ".join(AP.logs)     # own plan block is current: kept
    assert st["items"]["d"]["status"] == "RUNNING" and st["items"]["e"]["status"] == "FAIL"             # the new event and finished rows are untouched
    stopped = [a[-1] for a in AP.shs]
    assert "ap-j1-a1" in stopped and "kw-head-mesh" in stopped and "kw-head-same" not in stopped
    assert stops and sorted(stops[0]) == ["/root/hd_held", "/root/hd_lep0N", "/root/hd_mesh"]


def test_only_in_the_window_after_a_switch_and_only_when_switched(monkeypatch):
    st = rows()
    st["adopt_seen"]["head"]["switched"] = False
    assert run(monkeypatch, st)[0] == 0                                               # no switch recorded: nothing is cancelled
    st = rows()
    for _ in range(3):
        run(monkeypatch, {"items": {}, "adopt_seen": st["adopt_seen"]})               # three empty ticks use up the window
    assert run(monkeypatch, st)[0] == 0 and st["items"]["a"]["status"] == "ENQUEUED"
    c = cfg(); c["dies"]["head"]["supersede_on_switch"] = False
    assert run(monkeypatch, rows(), c)[0] == 0                                        # die option off


def test_hold_items_protect_a_running_row(monkeypatch):
    monkeypatch.setattr(KW, "hold_protects_running", lambda cfg_, d, r, text: r.get("item") == "hd_held")
    st = rows()
    n, _ = run(monkeypatch, st, cfg(hold={"hd_held": "operator: do not stop"}))
    assert st["items"]["f"]["status"] == "RUNNING" and n == 1                         # hd_lep0N has no queue job in this dir: only hd_mesh stops


def test_adopt_rows_tick_detects_an_event_switch_without_a_tree_change():
    AP.logs.clear()
    st = {"items": {}}
    c = cfg("E1")
    KW.adopt_rows_tick(AP, c, st)
    assert not st["adopt_seen"]["head"]["switched"]
    c["dies"]["head"]["event"] = "E2"                                                  # same tree, new event: also a switch
    KW.adopt_rows_tick(AP, c, st)
    assert st["adopt_seen"]["head"]["switched"] and st["adopt_seen"]["head"]["sig"] == ["E2", None]
