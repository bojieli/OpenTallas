"""ot-build bind stage on a stub runtime pin: only stale nodes run, the R8 tables follow the plan, bad inputs stop before elab."""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ot_build as OB  # noqa: E402

STUB_BIND = r'''
import json, os, sys
from pathlib import Path
a = sys.argv[1:]
cmd, plan = a[0], a[1]
out = Path(a[a.index("--out") + 1])
ab = json.loads(Path(a[a.index("--asbuilt") + 1]).read_text())
open(os.environ["STUB_LOG"], "a").write("bind.py " + cmd + " J=" + os.environ.get("OT_BIND_EMIT_J", "") + "\n")
out.mkdir(parents=True, exist_ok=True)
P = json.loads(Path(plan).read_text())
if cmd == "elab":
    (out / "asbuilt.json").write_text(json.dumps({"top": ab["top"]}))
    (out / "asbuilt_sources.json").write_text("[]")
elif cmd == "r8-prepass":
    (out / "bus_groups.json").write_text(json.dumps({"depth": P["depth"]}))
elif cmd == "bind":
    t = json.loads(Path(ab["land_r8"]).read_text()) if ab.get("land_r8") else {"depth": P["depth"]}
    x = json.loads(Path(ab["land_r8_extra"][0]).read_text()) if ab.get("land_r8_extra") else {"depth": P["depth"]}
    errs = [] if t["depth"] == P["depth"] == x["depth"] else ["R8_STALE x bit 0: bound %d, table %d" % (P["depth"], t["depth"])]
    errs += ["EMIT gap"] if P.get("bad") else []
    (out / "rtl").mkdir(exist_ok=True)
    (out / "rtl" / "t.sv").write_text("// depth %d\n" % P["depth"])
    (out / "bind_report.json").write_text(json.dumps({"n_errors": len(errs), "errors": errs}))
    sys.exit(1 if errs else 0)
'''
STUB_PGP = r'''
import json, sys
from pathlib import Path
a = sys.argv[1:]
plan = json.loads(Path(a[a.index("--plan") + 1]).read_text())
known = json.loads((Path(__file__).parent / "schema_keys.json").read_text())
f = ["FAIL SCHEMA-UNKNOWN-KEY '%s' x1 not in %s/tools/die_plan/schema.py" % (k, a[a.index("--tree") + 1]) for k in plan if k not in known]
Path(a[a.index("--json") + 1]).write_text(json.dumps({"findings": f}))
sys.exit(1 if f else 0)


def manifest_paths(ab, manifest_dir, tree):
    return Path(tree), [("rtl_roots", Path(tree) / "rtl", "dir")]
'''.replace("sys.exit(1 if f else 0)", "if __name__ == '__main__':\n    sys.exit(1 if f else 0)").replace(
    "a = sys.argv[1:]\nplan = json", "a = sys.argv[1:]\nif __name__ != '__main__':\n    a = ['--plan', '/dev/null', '--tree', '', '--json', '/dev/null']\nplan = json")
STUB_DERIVE = r'''
import json, sys
from pathlib import Path
a = sys.argv[1:]
bg = json.loads(Path(a[2]).read_text()); t = json.loads(Path(a[a.index("--table") + 1]).read_text())
sys.exit(0 if bg["depth"] == t["depth"] else 1)
'''
STUB_REFRESH = r'''
import json, os, sys
from pathlib import Path
a = sys.argv[1:]
open(os.environ["STUB_LOG"], "a").write("r8_refresh.py\n")
bg = json.loads(Path(a[1]).read_text())
ab = json.loads(Path(a[a.index("--asbuilt") + 1]).read_text()); root = Path(a[a.index("--root") + 1])
for p in [Path(a[2])] + [Path(x) if Path(x).is_absolute() else root / x for x in ab.get("land_r8_extra", [])]:
    d = json.loads(p.read_text()); d["depth"] = bg["depth"]
    tmp = p.with_name(p.name + ".tmp"); tmp.write_text(json.dumps(d)); os.replace(tmp, p)
print("R8_REFRESH OK table", a[2])
'''
STUB_OK = "import os, sys\nopen(os.environ['STUB_LOG'], 'a').write(os.path.basename(sys.argv[0]) + '\\n')\n"


def repo_file(name):
    for p in (HERE / name, HERE.parent / "autopilot" / name):
        if p.is_file():
            return p
    pytest.skip(f"{name} not next to the test")


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BUILD_HASH_CACHE", "off")
    monkeypatch.setenv("STUB_LOG", str(tmp_path / "calls.log"))
    rt = tmp_path / "rt" / "abcdef012345"
    dp = rt / "tools" / "die_plan"
    dp.mkdir(parents=True)
    (rt / "tools" / "autopilot").mkdir()
    shutil.copy(repo_file("rt_launch_tree.sh"), rt / "tools" / "autopilot" / "rt_launch_tree.sh")
    for n, s in (("bind.py", STUB_BIND), ("plan_gate_pre.py", STUB_PGP), ("land_r8_derive.py", STUB_DERIVE), ("r8_refresh.py", STUB_REFRESH),
                 ("lane_asbuilt_latency.py", STUB_OK), ("bound_param_check.py", STUB_OK)):
        (dp / n).write_text(s)
    (dp / "schema_keys.json").write_text(json.dumps(["die", "depth", "partition_types", "bad"]))
    src = tmp_path / "src"
    pd = src / "physical" / "die_plan" / "d" / "plan_of_record"
    (pd / "inputs").mkdir(parents=True)
    (src / "rtl").mkdir()
    (src / "rtl" / "m.sv").write_text("module m; endmodule\n")
    (src / "tools").mkdir()
    (pd / "plan.json").write_text(json.dumps({"die": {"name": "d"}, "depth": 3, "partition_types": {
        "t": {"outline_um": [100, 50], "clock": {"tap_um": [50, 25], "taps": [{"name": "a", "xy": [10, 10]}]}}}}))
    (pd / "r8.json").write_text(json.dumps({"die": "d", "depth": 3}))
    (pd / "inputs" / "x.json").write_text(json.dumps({"depth": 3}))
    (pd / "asbuilt.json").write_text(json.dumps({"top": "m", "base": "../../../..", "land_align": "r8", "rtl_roots": ["rtl"],
                                                "land_r8": "physical/die_plan/d/plan_of_record/r8.json",
                                                "land_r8_extra": ["physical/die_plan/d/plan_of_record/inputs/x.json"]}))
    return dict(tmp=tmp_path, rt=rt, src=src, pd=pd, root=tmp_path / "ob")


def run(e, plan=None, extra=()):
    argv = ["bind", "--tree", str(e["src"]), "--plan", str(plan or e["pd"] / "plan.json"), "--asbuilt", str(e["pd"] / "asbuilt.json"),
            "--out-root", str(e["root"]), "--rt", str(e["rt"]), "--emit-j", "4"] + list(extra)
    return OB.main(argv)


def calls(e, clear=True):
    p = e["tmp"] / "calls.log"
    s = p.read_text().split("\n")[:-1] if p.exists() else []
    if clear and p.exists():
        p.unlink()
    return s


def seal(e):
    (e["src"] / ".src-manifest.sha256").write_text("5" * 64 + "\n")


def test_first_build_then_fresh(env, capsys):
    assert run(env) == 0
    assert calls(env) == ["bind.py elab J=", "bind.py r8-prepass J=", "bind.py bind J=4", "lane_asbuilt_latency.py", "bound_param_check.py"]
    out = capsys.readouterr().out
    assert "OT-BUILD OUT " in out and "OT-BUILD EFFECTIVE " in out
    assert run(env) == 0 and calls(env) == []
    assert run(env, extra=["--status"]) == 0 and calls(env) == []


def test_plan_row_change_adopts_elab_and_refreshes_stale_tables_outside_a_sealed_tree(env, capsys):
    seal(env)
    assert run(env) == 0
    calls(env)
    capsys.readouterr()
    od = env["tmp"] / "delta"
    assert OB.main(["plan-overlay", "--from", str(env["pd"]), "--to", str(od), "--copy", "plan.json"]) == 0
    p = json.loads((od / "plan.json").read_text())
    p["depth"] = 4                                        # the row change moves a bound depth: the carried tables (3) are stale
    (od / "plan.json").write_text(json.dumps(p))
    assert run(env, plan=od / "plan.json", extra=["--status"]) == 3 and calls(env) == []
    assert run(env, plan=od / "plan.json") == 0
    assert calls(env) == ["bind.py r8-prepass J=", "r8_refresh.py", "bind.py bind J=4", "lane_asbuilt_latency.py", "bound_param_check.py"]
    out = capsys.readouterr().out
    assert "elab adopted from" in out and "R8 tables were STALE" in out
    eff = json.loads([ln for ln in out.splitlines() if ln.startswith("OT-BUILD EFFECTIVE ")][-1].split(" ", 2)[2])
    assert "/.ot-build/plan/" in eff["asbuilt"] and eff["rc"] == 0
    ab = json.loads(Path(eff["asbuilt"]).read_text())
    assert json.loads(Path(ab["land_r8"]).read_text())["depth"] == 4 and json.loads(Path(ab["land_r8_extra"][0]).read_text())["depth"] == 4
    assert json.loads((env["pd"] / "r8.json").read_text())["depth"] == 3            # the sealed tree is untouched
    assert json.loads((env["pd"] / "inputs" / "x.json").read_text())["depth"] == 3
    assert len(list(env["root"].glob("b_*"))) == 2                                 # the first plan's bind is still there
    assert run(env, plan=od / "plan.json") == 0 and calls(env) == []


def test_unsealed_lane_tree_tables_refreshed_in_place(env, capsys):
    p = json.loads((env["pd"] / "plan.json").read_text())
    p["depth"] = 5
    (env["pd"] / "plan.json").write_text(json.dumps(p))
    assert run(env) == 0
    assert "r8_refresh.py" in calls(env)
    assert json.loads((env["pd"] / "r8.json").read_text())["depth"] == 5
    assert "in place" in capsys.readouterr().out


def test_unknown_plan_key_refused_before_elab(env, capsys):
    p = json.loads((env["pd"] / "plan.json").read_text())
    p["band_fixed_um"] = 1
    (env["pd"] / "plan.json").write_text(json.dumps(p))
    assert run(env) == 1
    assert calls(env) == []
    out = capsys.readouterr().out
    assert "SCHEMA-UNKNOWN-KEY 'band_fixed_um'" in out and "runtime pin rt/abcdef012345" in out and "nothing was elaborated" in out


def test_tap_outside_outline_refused_before_elab(env, capsys):
    p = json.loads((env["pd"] / "plan.json").read_text())
    p["partition_types"]["t"]["clock"]["taps"].append({"name": "b", "xy": [130.5, 10]})
    (env["pd"] / "plan.json").write_text(json.dumps(p))
    assert run(env) == 1 and calls(env) == []
    assert "FAIL TAPS type t: 1 clock.taps point(s) outside the outline 100 x 50 um (first: 130.5,10)" in capsys.readouterr().out


def test_failed_bind_is_not_stamped_and_reruns(env, capsys):
    p = json.loads((env["pd"] / "plan.json").read_text())
    p["bad"] = True
    (env["pd"] / "plan.json").write_text(json.dumps(p))
    assert run(env) == 1
    assert calls(env)[-1] == "bind.py bind J=4"
    assert "bind.py rc=1" in capsys.readouterr().out
    assert run(env) == 1 and calls(env) == ["bind.py bind J=4"]                    # elab / r8 are fresh, the bind runs again


def test_rtl_change_in_unsealed_tree_restales_elab(env):
    assert run(env) == 0
    calls(env)
    (env["src"] / "rtl" / "m.sv").write_text("module m; wire x; endmodule\n")
    assert run(env) == 0
    assert calls(env)[0] == "bind.py elab J="


def test_taps_findings_shapes():
    plan = {"partition_types": {"a": {"outline_um": [10, 10], "clock": {"tap_um": [5, 5], "added_taps": [[1, 1], [11, 1]]},
                                      "reset": {"local_taps_um": [[0, 0], [10, 10]], "tap_um": [5, -1]}},
                                "b": {"clock": {"tap_um": [99, 99]}}}}
    f = OB.taps_findings(plan)
    assert len(f) == 2 and "clock.added_taps" in f[0] and "reset.tap_um" in f[1]


def test_runtime_pin_move_without_bind_tool_change_keeps_everything_fresh(env):
    assert run(env) == 0
    calls(env)
    rt2 = env["tmp"] / "rt" / "fedcba987654"
    shutil.copytree(env["rt"], rt2)
    (rt2 / "tools" / "autopilot" / "unrelated.py").write_text("x = 1\n")
    (rt2 / "tools" / "die_plan" / "test_something.py").write_text("x = 1\n")        # not in any tool's import closure
    env2 = dict(env, rt=rt2)
    assert run(env2) == 0 and calls(env) == []
    rt3 = env["tmp"] / "rt" / "0123456789ab"                                         # an rt snapshot is immutable: a third one
    shutil.copytree(env["rt"], rt3)
    (rt3 / "tools" / "die_plan" / "helper.py").write_text("x = 1\n")
    (rt3 / "tools" / "die_plan" / "bind.py").write_text("import os, sys\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\nimport helper\n" + (env["rt"] / "tools" / "die_plan" / "bind.py").read_text())
    assert run(dict(env, rt=rt3)) == 0
    assert calls(env)[0] == "bind.py elab J="                                      # a tool the bind loads changed: new OUT, rebuilt


def test_tool_closure(tmp_path):
    d = tmp_path / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "a.py").write_text("import b\ndef f():\n    from c import g\n    import importlib\n    importlib.import_module('e')\n")
    for n in ("b", "c", "d", "e", "test_a"):
        (d / f"{n}.py").write_text("")
    (d / "cells.tcl").write_text("")
    assert OB.tool_closure(tmp_path, ["a.py"]) == ["a.py", "b.py", "c.py", "e.py", "cells.tcl"]
