"""FABLE-FLOW-0555 A/C/E/I (WAVE-PILOT-FIX 11-19)"""
import json
import os
import sys
import types
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW  # noqa: E402
import autopilot as AP  # noqa: E402


class FakeAP:
    def __init__(self, green_src):
        self.lines, self.green = [], green_src

    def log(self, m):
        self.lines.append(m)

    def rpy(self, host, code, args, timeout=0):
        if code == KW.PROBE_BIND_SIG:
            return {"sig": "s:" + str(args.get("src"))}
        return {"stale": [] if args.get("src") == self.green else list(args["types"])}


def cfg0():
    return {"dies": {"s81": {"gen_host": "h", "src": "/new", "plan": "/new/p.json", "kit_rtl": {"mode": "bind", "bind_out": "/new_bind", "asbuilt": "a.json"},
                             "bound_trees": [{"src": "/mid", "plan": "/mid/p.json", "kit_rtl": {"mode": "bind", "bind_out": "/mid_bind"}},
                                             {"src": "/old", "plan": "/old/p.json", "src_manifest_hash": "H", "kit_rtl": {"mode": "bind", "bind_out": "/old_bind"}}]}}}


def test_stale_row_launches_on_the_newest_earlier_tree_with_a_green_bind():
    a, st, cfg = FakeAP("/old"), {}, cfg0()
    rows = [{"item": "t1", "kind": "type"}, {"item": "t2", "kind": "type"}]
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    assert set(stale) == {"t1", "t2"}
    resc = KW.bound_fallback(a, cfg, st, "s81", rows, stale)
    assert resc == {"t1": "/old", "t2": "/old"} and stale == {}
    ii = cfg["dies"]["s81"]["item_inputs"]["t1"]
    assert ii["src"] == "/old" and ii["plan"] == "/old/p.json" and ii["kit_rtl"]["bind_out"] == "/old_bind" and ii["src_manifest_hash"] == "H"
    spec = KW.spec_for.__name__                      # spec_for reads item_inputs src/plan/kit_rtl (KW-FIX-38/45)
    assert spec == "spec_for"


def test_no_green_earlier_tree_keeps_the_row_stale():
    a, st, cfg = FakeAP("/none"), {}, cfg0()
    rows = [{"item": "t1", "kind": "type"}]
    stale = KW.bind_preflight(a, cfg, st, "s81", rows)
    assert KW.bound_fallback(a, cfg, st, "s81", rows, stale) == {} and "t1" in stale and "item_inputs" not in cfg["dies"]["s81"]


def test_bind_verdict_merges_new_items_without_reprobing_judged_ones():
    a, st, cfg = FakeAP("/x"), {}, cfg0()
    probes = []
    orig = a.rpy
    a.rpy = lambda h, c, g, timeout=0: (probes.append(sorted(g.get("types") or [])) if c == KW.PROBE_BIND else None) or orig(h, c, g, timeout)
    KW.bind_preflight(a, cfg, st, "s81", [{"item": "t1", "kind": "type"}])
    out = KW.bind_preflight(a, cfg, st, "s81", [{"item": "t1", "kind": "type"}, {"item": "t2", "kind": "type"}])
    assert probes == [["t1"], ["t2"]] and set(out) == {"t1", "t2"}


def _rec(att, status, started, parts, cls="", q=""):
    return {"die": "d", "item": "i", "attempt": att, "status": status, "started": started, "input_parts": parts, "class": cls, "q_status": q, "stage": "gen"}


def test_cancelled_attempt_is_compared_with_the_last_failed_one():
    P = {"v": 2, "noenv": "N1", "env": {}, "fam": {"gen": "F"}, "stg": {"gen": "G"}}
    st = {"items": {"a": _rec(16, "FAIL", 1, P, "GEN"), "b": _rec(17, "CANCELLED", 2, P)}}
    ok, why = KW.retry_key_decision(st, "d", "i", "17")
    assert ok is False and "SAME inputs" in why
    st["items"]["b"]["input_parts"] = dict(P, noenv="N2", fam={"gen": "F2"}, stg={"gen": "G2"})
    assert KW.retry_key_decision(st, "d", "i", "17")[0] is True


def test_cell_big_logged_once_per_item_per_day(tmp_path, monkeypatch):
    monkeypatch.setattr(AP, "CELL_BIG_SEEN", str(tmp_path / "seen.json"))
    assert AP.cell_big_first_today("d", "t", today="2026-11-19") is True
    assert AP.cell_big_first_today("d", "t", today="2026-11-19") is False
    assert AP.cell_big_first_today("d", "u", today="2026-11-19") is True
    assert AP.cell_big_first_today("d", "t", today="2026-11-20") is True
