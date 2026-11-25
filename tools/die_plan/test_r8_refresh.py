import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r8_refresh as RR


def _m(i, bound, pad=0):
    return dict(id=i, bound=bound, landed=bound, pad=pad)


def test_rebound_takes_derived_bound_keeps_pad_and_inner():
    derived = dict(members=[_m("a", 22), _m("b", 19), _m("c", 5)])
    extra = dict(members=[_m("a", 20, pad=3), _m("b", 19, pad=1), _m("INNER:x", 7, pad=2), _m("z", 4)])
    X, n, delta = RR.rebound_extra(derived, extra)
    by = {m["id"]: m for m in X["members"]}
    assert n == 1 and delta == {2: 1}
    assert by["a"]["bound"] == 22 and by["a"]["landed"] == 22 and by["a"]["pad"] == 3
    assert by["b"] == _m("b", 19, pad=1) and by["INNER:x"] == _m("INNER:x", 7, pad=2) and by["z"] == _m("z", 4)
    assert extra["members"][0]["bound"] == 20          # input untouched


def test_main_rewrites_only_changed_extras(tmp_path, monkeypatch):
    table = tmp_path / "r8.json"; table.write_text(json.dumps(dict(members=[_m("a", 9)])))
    x0, x1 = tmp_path / "x0.json", tmp_path / "x1.json"
    x0.write_text(json.dumps(dict(members=[_m("a", 7, pad=2)]))); x1.write_text(json.dumps(dict(members=[_m("q", 1)])))
    before = x1.read_bytes()
    ab = tmp_path / "ab.json"; ab.write_text(json.dumps(dict(land_r8_extra=["x0.json", str(x1)])))

    class R:
        returncode, stdout, stderr = 0, "LAND_R8 DERIVED\n", ""
    monkeypatch.setattr(RR.subprocess, "run", lambda *a, **k: R())
    assert RR.main(["p.json", "bg.json", str(table), "--asbuilt", str(ab), "--root", str(tmp_path)]) == 0
    assert json.loads(x0.read_text())["members"][0] == dict(id="a", bound=9, landed=9, pad=2)
    assert x1.read_bytes() == before


def test_main_derive_failure_propagates(tmp_path, monkeypatch):
    class R:
        returncode, stdout, stderr = 3, "", "boom"
    monkeypatch.setattr(RR.subprocess, "run", lambda *a, **k: R())
    ab = tmp_path / "ab.json"; ab.write_text("{}")
    assert RR.main(["p", "bg", str(tmp_path / "t.json"), "--asbuilt", str(ab)]) == 3


def test_main_finds_derive_under_cwd_when_copied(tmp_path, monkeypatch):
    import importlib.util
    import shutil
    d = tmp_path / "copy"; d.mkdir(); shutil.copy(RR.__file__, d / "r8_refresh.py")
    root = tmp_path / "tree"; (root / "tools/die_plan").mkdir(parents=True)
    (root / "tools/die_plan/land_r8_derive.py").write_text("")
    spec = importlib.util.spec_from_file_location("rr_copy", d / "r8_refresh.py"); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    seen = {}

    class R:
        returncode, stdout, stderr = 0, "", ""

    def run(cmd, **k):
        seen["cmd"] = cmd
        return R()
    monkeypatch.setattr(m.subprocess, "run", run)
    table = tmp_path / "t.json"; table.write_text(json.dumps(dict(members=[])))
    ab = tmp_path / "ab.json"; ab.write_text("{}")
    monkeypatch.chdir(root)
    assert m.main(["p", "bg", str(table), "--asbuilt", str(ab)]) == 0
    assert seen["cmd"][2] == str(root / "tools/die_plan/land_r8_derive.py")


# ---- UNDERIVED-1125: a stale table the derive cannot produce fails loudly -----------------------------------------------------------
def _run_main(tmp_path, monkeypatch, stale_by_table, stale_age=0, rebound_member=False):
    import os
    table = tmp_path / "r8.json"; table.write_text(json.dumps(dict(members=[_m("a", 9)])))
    x0 = tmp_path / "pv_v_pads.json"
    x0.write_text(json.dumps(dict(kind="kv_pv_v_landing", members=[_m("a", 7, pad=2)] if rebound_member else [_m("pvw_q", 7, pad=2)])))
    ab = tmp_path / "ab.json"; ab.write_text(json.dumps(dict(land_r8_extra=["pv_v_pads.json"])))
    bgp = tmp_path / "bus_groups.json"; bgp.write_text("{}")
    if stale_by_table is not None:
        sf = tmp_path / "r8_stale_all.json"; sf.write_text(json.dumps(dict(by_table=stale_by_table)))
        t = os.path.getmtime(bgp) + stale_age; os.utime(sf, (t, t))

    class R:
        returncode, stdout, stderr = 0, "", ""
    monkeypatch.setattr(RR.subprocess, "run", lambda *a, **k: R())
    return RR.main(["p.json", str(bgp), str(table), "--asbuilt", str(ab), "--root", str(tmp_path)])


def test_underived_stale_table_fails_loudly(tmp_path, monkeypatch, capsys):
    assert _run_main(tmp_path, monkeypatch, {"pv_v_pads.json": 68}) == 5
    out = capsys.readouterr().out
    assert "UNDERIVED pv_v_pads.json: 68" in out and "kv_pv_v_pads.py pads" in out and "R8_REFRESH OK" not in out


def test_underived_quiet_when_rebound_or_absent_or_old(tmp_path, monkeypatch):
    assert _run_main(tmp_path / "a", monkeypatch, {"pv_v_pads.json": 3}, rebound_member=True) == 0 if (tmp_path / "a").mkdir() is None else 1   # rebound > 0
    (tmp_path / "b").mkdir(); assert _run_main(tmp_path / "b", monkeypatch, None) == 0                           # no stale report
    (tmp_path / "c").mkdir(); assert _run_main(tmp_path / "c", monkeypatch, {"pv_v_pads.json": 9}, stale_age=-3600) == 0   # report from an older bind
    (tmp_path / "d").mkdir(); assert _run_main(tmp_path / "d", monkeypatch, {"other.json": 9}) == 0              # stale table is not one of the extras
    (tmp_path / "e").mkdir(); assert _run_main(tmp_path / "e", monkeypatch, {"pv_v_pads.json": 0}) == 0          # zero stale members


def test_underived_mutants_are_killed(tmp_path, monkeypatch):
    src = open(RR.__file__).read()
    muts = [('if n and name in tables and (summary.get(name) or {}).get("rebound", 0) == 0:', 'if False:'),
            ('if clock(sf) < clock(bg) - 60:', 'if False:'),
            ('        return 5\n    print("R8_REFRESH OK table"', '        return 0\n    print("R8_REFRESH OK table"'),
            ('== 0:\n            kind', '>= 0:\n            kind')]
    for i, (a, b) in enumerate(muts):
        assert src.count(a) == 1, a
        ns = {"__name__": f"rr_mut{i}", "__file__": RR.__file__}
        exec(compile(src.replace(a, b), RR.__file__, "exec"), ns)
        loud = tmp_path / f"m{i}"; loud.mkdir()
        mon = monkeypatch
        class R:
            returncode, stdout, stderr = 0, "", ""
        mon.setattr(ns["subprocess"], "run", lambda *a_, **k: R())
        def go(d, by, age=0, reb=False):
            import os
            table = d / "r8.json"; table.write_text(json.dumps(dict(members=[_m("a", 9)])))
            (d / "x.json").write_text(json.dumps(dict(kind="kv_pv_v_landing", members=[_m("a", 7) if reb else _m("pvw_q", 7)])))
            ab = d / "ab.json"; ab.write_text(json.dumps(dict(land_r8_extra=["x.json"])))
            bg = d / "bus_groups.json"; bg.write_text("{}")
            sf = d / "r8_stale_all.json"; sf.write_text(json.dumps(dict(by_table={"x.json": by}))); t = os.path.getmtime(bg) + age; os.utime(sf, (t, t))
            return ns["main"](["p.json", str(bg), str(table), "--asbuilt", str(ab), "--root", str(d)])
        quiet = tmp_path / f"q{i}"; quiet.mkdir()
        old = tmp_path / f"o{i}"; old.mkdir()
        rb = tmp_path / f"r{i}"; rb.mkdir()
        got = (go(loud, 5), go(quiet, 0), go(old, 5, -3600), go(rb, 5, 0, True))
        assert got != (5, 0, 0, 0), f"mutant {i} survived: {got}"
