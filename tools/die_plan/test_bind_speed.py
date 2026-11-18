#!/usr/bin/env python3
"""BIND-SPEED-1118: plan_package gate cache, plan-row precheck classes (bind_rowcheck), bind_fast, r8-prepass."""
import json
import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind_rowcheck as RC  # noqa: E402
import plan_package as PP  # noqa: E402


# ------------------------------------------------------------------ plan_package gate cache
def _plan_dir(tmp_path):
    d = tmp_path / "plan"
    d.mkdir()
    (d / "die_plan.json").write_text("{}")
    (d / "pins.json").write_text('{"p": "/srv/other/lane/x.json"}')
    return d


def test_gate_cache_hit_and_invalidation(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BIND_GATE_CACHE", str(tmp_path / "cache"))
    d = _plan_dir(tmp_path)
    calls = []
    real = PP._gate_uncached
    monkeypatch.setattr(PP, "_gate_uncached", lambda *a: (calls.append(1), real(*a))[1])
    ok1, msg1 = PP.gate(str(d / "die_plan.json"), "warn")
    ok2, msg2 = PP.gate(str(d / "die_plan.json"), "warn")
    assert (ok1, msg1) == (ok2, msg2) and "not self-contained" in msg1 and len(calls) == 1      # second call: cache
    (d / "pins.json").write_text('{"p": "relative.json"}')                                         # file rewritten: new key
    ok3, msg3 = PP.gate(str(d / "die_plan.json"), "warn")
    assert ok3 and msg3 == "" and len(calls) == 2
    (d / "new.json").write_text("{}")                                                              # file added: new key
    PP.gate(str(d / "die_plan.json"), "warn")
    assert len(calls) == 3
    PP.gate(str(d / "die_plan.json"), "require")                                                   # mode is part of the key
    assert len(calls) == 4


def test_gate_cache_off(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BIND_GATE_CACHE", "off")
    d = _plan_dir(tmp_path)
    calls = []
    real = PP._gate_uncached
    monkeypatch.setattr(PP, "_gate_uncached", lambda *a: (calls.append(1), real(*a))[1])
    PP.gate(str(d / "die_plan.json"), "warn")
    PP.gate(str(d / "die_plan.json"), "warn")
    assert len(calls) == 2


# ------------------------------------------------------------------ FIXEDCYC
def _plan(fixed=0, row_fixed=0, natural=3, cycles=3, pad=0):
    return {"lanes": [{"id": "L1", "fixed_cycles": fixed}],
            "latency": {"lanes": {"L1": {"cycles": cycles, "natural": natural, "pad": pad, "boundary": 2, "stations": 1,
                                         "fixed": row_fixed}}}}


def test_fixedcyc():
    assert RC.check_fixedcyc(_plan()) == []
    assert RC.check_fixedcyc(_plan(fixed=2, row_fixed=2, natural=5, cycles=5)) == []
    f = RC.check_fixedcyc(_plan(fixed=2, row_fixed=0))
    assert len(f) == 1 and f[0].startswith("FAIL FIXEDCYC lane L1: fixed_cycles 2 != latency row fixed 0")
    f = RC.check_fixedcyc(_plan(fixed=2, row_fixed=2, natural=5 + 2, cycles=7))          # table bumped twice
    assert f and "natural 7" in f[0]
    assert RC.check_fixedcyc({"lanes": [{"id": "L1"}], "latency": {"lanes": {}}})[0].endswith("missing from the latency table")


# ------------------------------------------------------------------ ROWSINK / MODULES on a toy yosys netlist
def _yjs():
    return {"modules": {
        "top": {"cells": {"u_r0": {"type": "mid", "connections": {}}, "u_core": {"type": "leafm", "connections": {"d": [2]}}},
                "attributes": {}},
        "mid": {"cells": {"u_x": {"type": "leafm", "connections": {"d": [3], "q": [4]}}}, "attributes": {}},
        "leafm": {"cells": {}, "attributes": {"blackbox": "1"}}}}


def test_leaf_paths_walks_dissolved_modules():
    c = RC.leaf_paths(_yjs(), "top")
    assert set(c) == {"u_r0.u_x", "u_core"} and c["u_r0.u_x"][1] == {"d", "q"}


def _ab(tmp_path, members):
    t = tmp_path / "r8.json"
    t.write_text(json.dumps({"members": members}))
    return {"top": "top", "land_align": "r8", "land_r8": str(t), "base": str(tmp_path)}


def _m(sink, port="d", pad=1):
    return {"id": f"{sink}.{port}", "sink": sink, "sink_port": port, "pad": pad}


def test_rowsink(tmp_path):
    ab = _ab(tmp_path, [_m("u_r0.u_x"), _m("u_r0_u_x", "q"), _m("u_r0.u_gone"), _m("u_r0.u_x", "nope"), _m("u_r0.u_none", pad=0),
                        _m("u_r0.$procdff$12.D")])
    f = RC.check_rowsink("plan.json", {}, ab, None, tmp_path, yjs=_yjs())
    msgs = "\n".join(f)
    assert "u_r0.u_gone is no leaf" in msgs and "has no port nope" in msgs
    assert "u_r0_u_x" not in msgs.replace("normalized u_r0_u_x form", "")          # the normalized instance-name form is a hit
    assert "u_none" not in msgs                                                       # pad 0: the RTL removed it, no pad due
    assert "1 numbered `$`" in msgs and sum(x.startswith("FAIL") for x in f) == 2
    ab2 = _ab(tmp_path, [_m("u_r0.u_x")])
    assert RC.check_rowsink("plan.json", {}, ab2, None, tmp_path, yjs=_yjs()) == []


def test_modules(tmp_path):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "a.sv").write_text("module have_mod(input a); endmodule\n")
    ab = {"base": str(tmp_path), "rtl_roots": ["rtl"], "substitute_inst": [{"inst": "x", "module": "have_mod"},
                                                                              {"inst": "y", "module": "lost_mod"}]}
    f = RC.check_modules("plan.json", {}, ab, None, None, yjs=_yjs())
    assert len(f) == 1 and "lost_mod" in f[0] and f[0].startswith("FAIL MODULES")



def test_modules_sub_core_leaf_is_a_leaf_instance(tmp_path):
    """KV-D24: asbuilt.sub_core_leaf values are bound leaf INSTANCE names (KV hub_C {"pvfin": "pvfin"}), never modules"""
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "a.sv").write_text("module have_mod(input a); endmodule\n")
    ab = {"base": str(tmp_path), "rtl_roots": ["rtl"], "top": "top", "sub_core_leaf": {"pa": "u_core", "pb": "u_r0_u_x", "pc": "u_x"}}
    assert RC.check_modules("plan.json", {}, ab, None, None, yjs=_yjs()) == []
    ab["sub_core_leaf"]["pd"] = "u_gone"
    f = RC.check_modules("plan.json", {}, ab, None, None, yjs=_yjs())
    assert len(f) == 1 and f[0].startswith("FAIL MODULES sub_core_leaf u_gone")
    f = RC.check_modules("plan.json", {}, dict(ab, sub_core_leaf={"pvfin": "pvfin"}), None, None)   # no elab: not decidable
    assert f and all(x.startswith("WARN") for x in f)

# ------------------------------------------------------------------ TOOLSTALE
def test_toolstale(tmp_path):
    tree, ref = tmp_path / "tree", tmp_path / "ref"
    for r in (tree, ref):
        (r / "tools" / "die_plan").mkdir(parents=True)
    (tree / "tools/die_plan/bind.py").write_text("old")
    (ref / "tools/die_plan/bind.py").write_text("new")
    (ref / "tools/die_plan/extra.py").write_text("x")
    old = time.time() - 3600
    os.utime(tree / "tools/die_plan/bind.py", (old, old))
    f = RC.check_toolstale(tree, ref)
    assert f[0].startswith("FAIL TOOLSTALE 1 tools/die_plan file(s)") and "bind.py" in f[0] and f[1].startswith("WARN")
    assert RC.check_toolstale(tree, ref, "WARN")[0].startswith("WARN TOOLSTALE")
    os.utime(ref / "tools/die_plan/bind.py", (old - 10, old - 10))                    # reference older than the tree: a local patch
    assert not [x for x in RC.check_toolstale(tree, ref) if x.startswith("FAIL")]
    assert RC.check_toolstale(tree, tree) == []


# ------------------------------------------------------------------ bind_fast host / kits
def test_bind_fast_kits_runs_in_parallel(tmp_path):
    import bind_fast as BF
    tree = tmp_path / "tree"
    (tree / "tools/die_plan").mkdir(parents=True)
    (tree / "tools/die_plan/bind.py").write_text(
        "import sys,time\nt=sys.argv[sys.argv.index('--type')+1]\ntime.sleep(1.0)\nsys.exit(3 if t=='bad' else 0)\n")
    out = tmp_path / "out"
    t0 = time.time()
    rc = BF.main(["kits", "--plan", "p.json", "--out", str(out), "--types", "a,b,c,d,bad", "-j", "5", "--tree", str(tree)])
    assert rc == 1 and time.time() - t0 < 4.5                                         # 5 x 1 s serial = 5 s+
    assert (out / "kit_rtl_logs" / "a.log").exists()


# ------------------------------------------------------------------ r8-prepass on the bind_tiny example (needs yosys like test_bind)
def test_r8_prepass_derives_the_table_the_full_bind_needs(tmp_path):
    import test_bind as TB
    if not TB.HAVE_YOSYS:
        pytest.skip("no Yosys")
    import bind
    import r8 as R8
    out0 = tmp_path / "o0"
    assert TB.run(TB.plan_copy(tmp_path, "die_plan_lanes.json", TB._split_d0), out0, "elab", "bind") == 0
    bg = json.loads((out0 / "bus_groups.json").read_text())

    def edit(p):
        TB._split_d0(p)
        p["asbuilt"]["land_align"] = "r8"
    plan = TB.plan_copy(tmp_path, "die_plan_lanes.json", edit)
    good, _ = R8.write_pads(json.loads(plan.read_text()), bg, tmp_path / "r8")
    stale = json.loads(good.read_text())
    for m in stale["members"]:
        m["bound"] += 1                                                               # a table of another bind
    good.write_text(json.dumps(stale))
    out = tmp_path / "o"
    assert bind.main(["elab", str(plan), "--out", str(out), "--mem", "4"]) == 0
    new = tmp_path / "r8_new.json"
    assert bind.main(["r8-prepass", str(plan), "--out", str(out), "--r8-out", str(new)]) == 0
    assert (out / "bus_groups.json").is_file() and not (out / "bind_report.json").exists()     # head only: no emit
    t = json.loads(new.read_text())
    assert len(t["members"]) == len(stale["members"])
    assert [m["bound"] for m in t["members"]] != [m["bound"] for m in stale["members"]]      # the +1 of the stale table is gone
    good.write_text(new.read_text())                                                  # the ONE full bind on the derived table passes
    out2 = tmp_path / "o2"
    assert TB.run(plan, out2, "elab", "bind") == 0, TB.report(out2)["errors"][:5]
    assert not [e for e in TB.report(out2)["errors"] if e.startswith("R8_STALE")]
