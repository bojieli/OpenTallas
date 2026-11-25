"""PRECHECK-R2: plan_advisory driver + plan_gate_pre ADVISORY class: WARN-only, never a FAIL, a crashing check is 'not checked'."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_advisory as PA  # noqa: E402
import plan_gate_pre as PGP  # noqa: E402


def test_crashing_check_is_not_checked(monkeypatch, tmp_path):
    mod = tmp_path / "adv_boom_r2.py"
    mod.write_text("def findings(raw, plan_path, tree=None, **kw):\n    raise RuntimeError('boom')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(PA, "CHECKS", (("BOOM", "adv_boom_r2"),))
    out = PA.run({}, "p.json")
    assert out == ["WARN ADV-BOOM not checked: RuntimeError: boom"]


def test_lines_forced_warn_capped_and_debug_dropped(monkeypatch, tmp_path):
    mod = tmp_path / "adv_many_r2.py"
    mod.write_text("def findings(raw, plan_path, tree=None, **kw):\n"
                   "    return ['# coverage x', 'FAIL t1: x'] + ['WARN ADV-MANY t%d: y' % i for i in range(40)]\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(PA, "CHECKS", (("MANY", "adv_many_r2"),))
    out = PA.run({}, "p.json")
    assert all(x.startswith("WARN ADV-MANY") for x in out) and len(out) == PA.MAX_LINES + 1
    assert not any("# coverage" in x for x in out)


def test_off_switch(monkeypatch):
    monkeypatch.setenv("OT_PLAN_ADVISORY", "off")
    assert PA.run({"partition_types": {}}, "p.json") == []


def test_gate_advisory_never_fails(monkeypatch, tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"partition_types": {}}))
    monkeypatch.setattr(PA, "run", lambda raw, plan, tree=None, **kw: ["ADV-X t: something", "WARN ADV-Y t: z"])
    out = PGP.advisory_lines(str(tmp_path), str(p))
    assert out == ["WARN ADV-X t: something", "WARN ADV-Y t: z"]
    assert "ADVISORY" in PGP.CLASSES


def test_real_checks_on_empty_plan_are_quiet():
    out = PA.run({"partition_types": {}, "ports": [], "lanes": []}, "p.json")
    assert all(x.startswith("WARN ADV-") for x in out)


def test_cellcap_reports_retained_and_estimated_counts_above_reference():
    p = {
        "die": {"name": "d"},
        "partition_types": {
            "tile__cl987654": {},
            "tile__cl123456": {},
            "at_limit": {"cells": 400_000},
            "plan_only": {"cells": 400_001},
            "unmeasured": {},
            "unused": {"cells": 900_000},
        },
        "partitions": [
            {"type": name} for name in ("tile__cl987654", "tile__cl123456", "at_limit", "plan_only", "unmeasured")
        ],
    }
    cache = {"cells": {
        "d": {"tile__cl987654": {"last": {"cells": 420_000, "t0": 1}}},
        "other": {"unmeasured": {"cells": 970_000}},
    }}
    out = PA.run(p, "p.json", checks=("CELLCAP",), cells_cache=cache, cap=False)
    assert all(line.startswith("WARN ADV-CELLCAP") for line in out)
    assert "tile__cl123456: 420,000 standard cells (estimate from base kit tile__cl987654)" in out[0]
    assert "tile__cl987654: 420,000 standard cells (retained kit count)" in out[1]
    assert "plan_only: 400,001 standard cells (estimate from plan type.cells)" in out[2]
    assert out[3].endswith("3 above reference, 1 retained kit counts, 3 estimates, 1 unmeasured")


def test_run_parallel_equals_serial(monkeypatch):
    import types
    import plan_advisory as PA
    mods = {}
    for i, n in enumerate(("AAA", "BBB", "CCC", "DDD")):
        def findings(raw, plan_path, tree=None, _n=n, _i=i, **kw):
            if _n == "CCC":
                raise RuntimeError("boom")
            return [f"WARN ADV-{_n} line {_i}", "# debug"]
        mods["m_" + n] = types.SimpleNamespace(findings=findings)
    monkeypatch.setattr(PA, "CHECKS", tuple((n, "m_" + n) for n in ("AAA", "BBB", "CCC", "DDD")))
    monkeypatch.setattr(PA.importlib, "import_module", lambda m: mods[m])
    t1, t2 = {}, {}
    ser = PA.run({}, "p.json", jobs=1, timing=t1)
    par = PA.run({}, "p.json", jobs=3, timing=t2)
    assert ser == par and list(t1) == list(t2) == ["AAA", "BBB", "CCC", "DDD"]
    assert [x.split()[1] for x in par] == ["ADV-AAA", "ADV-BBB", "ADV-CCC", "ADV-DDD"]
    assert "not checked: RuntimeError: boom" in par[2]           # one check failing never stops the others
    assert PA.run({}, "p.json", jobs=3, skip=("BBB",), checks=("AAA", "BBB", "DDD")) == [par[0], par[3]]
