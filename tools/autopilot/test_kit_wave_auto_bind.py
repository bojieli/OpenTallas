"""kit_wave auto_rebind (die option auto_bind): BIND-STALE rows of the die's own tree launch on the fresh ot-build bind."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


class AP:
    def __init__(self):
        self.lines = []

    def log(self, s):
        self.lines.append(s)


def cfg():
    return {"dies": {"kv": {"src": "/s/t", "plan": "/s/t/p.json", "lane": "KIT-WAVE-1", "gen_hosts": ["h1", "h2"], "gen_host": "h1",
                            "kit_rtl": {"mode": "bind", "bind_out": "/s/t_bind_old", "asbuilt": "/s/t/ab.json"}, "auto_bind": True}}}


def test_fresh_bind_rescues_rows_whose_preflight_turns_green(monkeypatch):
    seen = {}

    def preflight(ap, c, st, die, rows, now=None, rpy=None):
        seen["bind_out"] = c["dies"][die]["item_inputs"][rows[0]["item"]]["kit_rtl"]["bind_out"]
        seen["gen_host"] = c["dies"][die]["gen_host"]
        return {"tb": "KIT_TOPOLOGY_BIND_STALE preflight: still"}
    monkeypatch.setattr(KW, "bind_preflight", preflight)
    c, st, ap = cfg(), {}, AP()
    rows = [{"item": "ta"}, {"item": "tb"}, {"item": "tc"}]
    pending = f"{KW.BIND_PREFLIGHT_PENDING} own bind running"
    stale = {"ta": "stale", "tb": "stale", "tc": pending}
    res = KW.auto_rebind(ap, c, st, "kv", rows, stale, rebind=lambda *a, **k: dict(state="FRESH", out="/o/b_1", asbuilt="/s/t/ab.json", host="h2"))
    assert res == {"ta": "/o/b_1"} and stale == {"tb": "stale", "tc": pending}
    assert seen == {"bind_out": "/o/b_1", "gen_host": "h2"}
    d = c["dies"]["kv"]
    assert d["item_inputs"]["ta"]["kit_rtl"] == {"mode": "bind", "bind_out": "/o/b_1", "asbuilt": "/s/t/ab.json"}
    assert "tb" not in d["item_inputs"] and d["kit_rtl"]["bind_out"] == "/s/t_bind_old"      # the die config itself is not edited
    assert c["_item_incomplete"]["h1"]["kv"]["ta"].startswith("auto bind /o/b_1 not on h1")
    assert any("AUTO-BIND kv: FRESH on h2" in x for x in ap.lines) and any("1 BIND-STALE row(s) launch" in x for x in ap.lines)


def test_running_or_failed_bind_rescues_nothing_and_logs_once(monkeypatch):
    monkeypatch.setattr(KW, "bind_preflight", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no probe while the bind runs")))
    c, st, ap = cfg(), {}, AP()
    stale = {"ta": "stale"}
    for _ in range(3):
        assert KW.auto_rebind(ap, c, st, "kv", [{"item": "ta"}], stale, rebind=lambda *a, **k: dict(state="RUNNING", host="h2")) == {}
    assert stale == {"ta": "stale"} and len(ap.lines) == 1
    assert KW.auto_rebind(ap, c, st, "kv", [{"item": "ta"}], stale,
                          rebind=lambda *a, **k: dict(state="FAILED", why="FAIL SCHEMA-UNKNOWN-KEY 'x'")) == {}
    assert "SCHEMA-UNKNOWN-KEY" in ap.lines[-1] and len(ap.lines) == 2


def test_tables_refreshed_outside_a_sealed_tree_do_not_launch(monkeypatch):
    monkeypatch.setattr(KW, "bind_preflight", lambda *a, **k: {})
    c, st, ap = cfg(), {}, AP()
    stale = {"ta": "stale"}
    r = KW.auto_rebind(ap, c, st, "kv", [{"item": "ta"}], stale,
                       rebind=lambda *a, **k: dict(state="FRESH", out="/o/b_1", asbuilt="/o/b_1/.ot-build/plan/ab.json", host="h2"))
    assert r == {} and stale == {"ta": "stale"} and "OUTSIDE the sealed tree" in ap.lines[-1]


def test_pending_current_probe_starts_neither_fallback_nor_rebind(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("pending current probe must finish before bind recovery")

    monkeypatch.setattr(KW, "bound_holders", unexpected)
    c, st, ap = cfg(), {}, AP()
    c["dies"]["kv"]["bound_trees"] = [{"src": "/older", "kit_rtl": {"bind_out": "/older/bind"}}]
    rows = [{"item": "ta"}]
    pending = {"ta": f"{KW.BIND_PREFLIGHT_PENDING} own bind running"}
    assert KW.bound_fallback(ap, c, st, "kv", rows, pending) == {}
    assert KW.auto_rebind(ap, c, st, "kv", rows, pending, rebind=unexpected) == {}
    assert list(pending) == ["ta"]
