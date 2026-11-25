"""PLAN-LEAF-PARAMS (S81-WREG-PARAM 11-24): partition_types[T].leaf_params sets a leaf parameter per instance on one plan
type only (the S81 OT_S81SL_VP_WREG define was read by a file every leaf type shares: TYPE_DEFINE_CONFLICT).  Types
without leaf_params bind byte-identically; unknown masters, keys and parameters fail closed."""
import json

import pytest

import bind
from test_bind import EX, HAVE_YOSYS, report, run

pytestmark = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")


def _plan(tmp_path, name, rules):
    p = json.loads((EX / "die_plan_lanes.json").read_text())
    p["asbuilt"]["base"] = str(EX)
    if rules is not None:
        p["partition_types"]["ta"]["leaf_params"] = rules
    f = tmp_path / name
    f.write_text(json.dumps(p))
    return f


def _rtl(out):
    return {f.name: f.read_text() for f in sorted((out / "rtl").glob("*.sv"))}


def test_leaf_params_one_type_others_identical(tmp_path):
    base = tmp_path / "base"
    assert run(_plan(tmp_path, "p0.json", None), base, "elab", "bind") == 0
    assert not (base / "param_regen.json").exists()
    out = tmp_path / "row"
    assert run(_plan(tmp_path, "p1.json", [dict(module="lf_a", params=dict(ID=5))]), out, "elab", "bind") == 0
    pr = json.loads((out / "param_regen.json").read_text())
    assert pr["plan_leaf_params"] == [dict(type="ta", module="lf_a", params=dict(ID=5), local_re=None, partitions=2,
                                           leaves=2)]
    assert sorted(r["inst"] for r in pr["derived"]) == sorted({r["inst"] for r in pr["derived"]}) and len(pr["derived"]) == 2
    assert all(r["param"] == "ID" and r["bound"] == 5 for r in pr["derived"])
    a, b = _rtl(base), _rtl(out)
    assert a.keys() == b.keys()
    assert ".ID(5)" in b["bt_ta.sv"] and ".ID(5)" not in a["bt_ta.sv"]
    top = [n for n in a if n.endswith("_bound_top.sv")]
    assert len(top) == 1
    # every other type: the same bound RTL, byte for byte
    assert all(a[n] == b[n] for n in a if n not in ("bt_ta.sv", top[0])), [n for n in a if a[n] != b[n]]
    # the die top: only the two ta instance lines lose their per-instance ID override (the type now fixes ID 5)
    la, lb = a[top[0]].splitlines(), b[top[0]].splitlines()
    assert len(la) == len(lb)
    diff = [(x, y) for x, y in zip(la, lb) if x != y]
    assert len(diff) == 2 and all("bt_ta" in x and "P_u_a_ID" in x and "P_u_a_ID" not in y for x, y in diff)


@pytest.mark.parametrize("rules,msg", [
    ([dict(module="lf_nope", params=dict(ID=1))], "PLAN_LEAF_PARAMS ta[0]: no lf_nope leaf"),
    ([dict(module="lf_a", params=dict(NOT_A_PARAM=1))], "NOT_A_PARAM: not a parameter"),
    ([dict(module="lf_a", params=dict(ID=1), typo=1)], "unknown keys ['typo']"),
    ([dict(module="lf_a", params=dict(ID=1), local_re="u_zz")], "matching u_zz"),
])
def test_leaf_params_fail_closed(tmp_path, rules, msg):
    out = tmp_path / "o"
    pp = _plan(tmp_path, "p.json", rules)
    assert run(pp, out, "elab") == 0
    assert bind.main(["bind", str(pp), "--out", str(out), "--strict"]) != 0
    assert any(msg in e for e in report(out)["errors"]), report(out)["errors"]


def test_schema_knows_leaf_params():
    import schema
    sub = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["leaf_params"]
    assert sub["items"]["required"] == ["module", "params"]
