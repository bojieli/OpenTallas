"""KW-FIX-4 11-03: gen_hosts pick, spillable async PLACE argv default, restage of unstarted waiters"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


class FakeAP:
    DRY = False
    HUB_NAME = "intel2"
    def __init__(self):
        self.calls, self.logs = [], []
    def sh(self, argv, timeout=0):
        self.calls.append(argv); return 0, "", ""
    def log(self, m):
        self.logs.append(m)


def cfg(**d):
    base = {"gen_host": "intel1", "event": "e1", "plan": "/p", "src": "/s"}
    base.update(d)
    return {"dies": {"s81": base}}


ST = {"intel1": {"admit": 10, "load": 300, "cores": 256, "run": 9}, "epyc4": {"admit": 676, "load": 5, "cores": 256, "run": 0}}


def test_pick_default_unchanged():
    c = cfg(); c["_otrun_status"] = dict(ST)
    assert K.pick_gen_host(c, "s81") == "intel1"


def test_pick_most_admits_and_spreads():
    c = cfg(gen_hosts=["intel1", "epyc4"]); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    picks = [K.pick_gen_host(c, "s81", take=48) for _ in range(14)]
    assert picks[0] == "epyc4" and picks.count("epyc4") == 14 - picks.count("intel1")
    c2 = cfg(gen_hosts=["intel1", "epyc4"])               # no status -> configured gen host
    assert K.pick_gen_host(c2, "s81") == "intel1"


def _rec(tmp, g, argv=None, admitted=False):
    d = tmp / f"a_{g}_{bool(argv)}_{admitted}"
    d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_host": g}))
    if argv:
        (d / "place_service.json").write_text(json.dumps({"unit": "kwp-x", "launch": "launched", "argv": argv}))
    (d / "place.live.log").write_text("ot-run: -> intel1\n" + ("ot-heavy: admitted on intel1\n" if admitted else ""))
    return {"die": "s81", "status": "RUNNING", "unit": "kw-u", "dir": str(d), "attempt": 1, "item": "t1"}


def test_restage_multi_and_pinned(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_hosts=["intel1", "epyc4"], place_mem_gb=48); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    st = {"items": {"a": _rec(tmp_path, "intel1"), "b": _rec(tmp_path, "intel1", admitted=True),
                    "c": _rec(tmp_path, "epyc4")}}
    ap, notes = FakeAP(), {}
    assert K.restage_waiters(ap, c, st, notes) == 1
    assert st["items"]["a"]["status"] == "RETRY-INFRA" and st["items"]["b"]["status"] == "RUNNING"
    assert st["items"]["c"]["status"] == "RUNNING"
    assert ["systemctl", "--user", "stop", "kw-u"] in ap.calls
    assert K.infra_relaunch_due(c, st["items"]["a"])
    # pinned async PLACE waiter of a single-gen-host die
    c3 = cfg(place_mem_gb=48)
    d = tmp_path / "pin"; d.mkdir()
    (d / "spec.json").write_text(json.dumps({"gen_host": "intel2"}))
    (d / "place_service.json").write_text(json.dumps({"unit": "kwp-y", "launch": "launched", "argv": ["ot-run", "--hosts", "localhost"]}))
    (d / "place.live.log").write_text("ot-run: -> localhost (will queue)\n")
    st3 = {"items": {"p": {"die": "s81", "status": "RUNNING", "unit": "kw-p", "dir": str(d), "attempt": 1, "item": "t2"}}}
    ap3 = FakeAP()
    assert K.restage_waiters(ap3, c3, st3, {}) == 1
    assert ["systemctl", "--user", "stop", "kwp-y"] in ap3.calls
    c3["dies"]["s81"]["place_spill"] = False
    st3["items"]["p"]["status"] = "RUNNING"
    assert K.restage_waiters(FakeAP(), c3, st3, {}) == 0


def test_restage_skips_no_infra_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "stop_reason", lambda *a, **k: None)
    c = cfg(gen_hosts=["intel1", "epyc4"], place_mem_gb=48); c["_otrun_status"] = {h: dict(v) for h, v in ST.items()}
    r = _rec(tmp_path, "intel1"); r["attempt"] = 9
    st = {"items": {"a": r}}
    assert K.restage_waiters(FakeAP(), c, st, {}) == 0 and r["status"] == "RUNNING"


def test_spec_place_spill_default_and_epyc4_host():
    c = cfg(); c["dies"]["s81"]["hosts"] = None
    c["dies"]["s81"].pop("hosts")
    sp = K.spec_for(c, "s81", "t1", "intel2")
    assert sp["place_spill"] is True and "epyc4" in sp["hosts"] and sp["gen_host"] == "intel1"
    c["dies"]["s81"]["place_spill"] = False
    assert K.spec_for(c, "s81", "t1", "intel2")["place_spill"] is False


def test_place_async_argv_source():
    src = Path(K.__file__).read_text()
    i = src.index("def place_async(K, prun, m, t):")
    body = src[i:i + 2500]
    assert '"--stage", K, "--stage", prun' in body and 'otrun(m, t, K, cmd, [G])' in body
