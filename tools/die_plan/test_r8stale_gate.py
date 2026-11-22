"""R8STALE-1122 (FLOW-OPS-R2, COORD): a station change on a lane whose R8 table was not re-derived is refused in seconds."""
import copy
import json
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402
from test_istcyc_gate import base  # noqa: E402


def tree(root, plan, table):
    (root / "tools" / "die_plan").mkdir(parents=True)
    pd = root / "physical" / "die_plan" / "kv" / "plan_of_record"; pd.mkdir(parents=True)
    plan = copy.deepcopy(plan)
    plan["asbuilt"] = {"land_r8": "physical/die_plan/kv/plan_of_record/r8_ev.json"}
    (pd / "r8_ev.json").write_text(json.dumps(table))
    (pd / "plan.json").write_text(json.dumps(plan))
    return str(pd / "plan.json")


TABLE = {"members": [{"id": "m1", "lane": "L1", "bound": 9}, {"id": "m2", "lane": "L3", "bound": 2}]}


def test_not_rederived_table_refused_with_recipe(tmp_path):
    b = base(); n = copy.deepcopy(b)
    n["partition_types"]["A"]["internal_stations"][0]["regs_um"].append([9, 9])     # L1 3 -> 4
    pb = tree(tmp_path / "base", b, TABLE)
    pn = tree(tmp_path / "new", n, TABLE)
    f = G.check_r8stale(str(tmp_path / "new"), pn, pb)
    assert len(f) == 1 and f[0].startswith("FAIL R8STALE") and "1 member(s) on 1 lane(s)" in f[0] and "L1 3->4" in f[0]
    assert "R8_FAIL_FAST" in f[0] and "r8_refresh.py" in f[0]


def test_rederived_or_untouched_passes(tmp_path):
    b = base(); n = copy.deepcopy(b)
    n["partition_types"]["A"]["internal_stations"][0]["regs_um"].append([9, 9])
    pb = tree(tmp_path / "base", b, TABLE)
    t2 = copy.deepcopy(TABLE); t2["members"][0]["bound"] = 10
    pn = tree(tmp_path / "new", n, t2)
    f = G.check_r8stale(str(tmp_path / "new"), pn, pb)
    assert len(f) == 1 and f[0].startswith("WARN R8STALE") and "differs" in f[0]
    pn2 = tree(tmp_path / "same", b, TABLE)
    assert G.check_r8stale(str(tmp_path / "same"), pn2, pb) == []
    assert G.check_r8stale(str(tmp_path / "same"), pn2, None) == []
