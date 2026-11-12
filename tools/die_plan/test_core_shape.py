"""CORE-SHAPE-GATE-1 tests: G0 ERROR core_shape_change (python3 -m pytest -q tools/die_plan/test_core_shape.py)"""
import copy
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import core_shape as CS  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _index(tmp_path, mods):
    p = tmp_path / "idx.json"
    p.write_text(json.dumps(dict(schema=CS.INDEX_SCHEMA, modules={m: [dict(outline_nm=[nm(w), nm(h)]) for w, h in v] for m, v in mods.items()})))
    return str(p)


def nm(v):
    return int(round(v * 1000))


def _plan(outline=(10.0, 20.0), module="core_a", exceptions=None):
    p = copy.deepcopy(EX)
    t = next(iter(p["partition_types"].values()))
    t.setdefault("hard_cores", []).append(dict(inst="u_a", module=module, origin_um=[1.0, 1.0], outline_um=list(outline)))
    if exceptions is not None:
        p["core_shape_exceptions"] = exceptions
    return p


def _errs(p, idx):
    R, _ = check.run(p, completeness=True, core_shape_index=idx)
    return [i["msg"] for i in R.errors() if i["check"] == "core_shape_change"]


def test_reshape_flags(tmp_path):
    idx = _index(tmp_path, {"core_a": [(10.0, 20.0), (30.0, 40.0)]})
    assert _errs(_plan((11.0, 20.0)), idx)
    e = _errs(_plan((11.0, 20.0)), idx)[0]
    assert "core_a" in e and "10x20" in e


def test_signed_shape_passes(tmp_path):
    idx = _index(tmp_path, {"core_a": [(10.0, 20.0), (30.0, 40.0)]})
    assert not _errs(_plan((30.0, 40.0)), idx)


def test_exception_passes(tmp_path):
    idx = _index(tmp_path, {"core_a": [(10.0, 20.0)]})
    ex = [dict(core="core_a", old=[10.0, 20.0], new=[11.0, 20.0], reason="overload", measured_by="GRT0 run x")]
    assert not _errs(_plan((11.0, 20.0), exceptions=ex), idx)
    # an exception for another shape does not cover this one
    ex[0]["new"] = [12.0, 20.0]
    assert _errs(_plan((11.0, 20.0), exceptions=ex), idx)


def test_new_core_passes(tmp_path):
    idx = _index(tmp_path, {"other": [(10.0, 20.0)]})
    assert not _errs(_plan((11.0, 20.0)), idx)


def test_exception_schema_validated():
    p = _plan(exceptions=[dict(core="core_a", old=[1, 2], new=[1, 3])])
    R, _ = check.run(p)
    assert any(i["check"] == "schema" for i in R.errors())


def test_default_byte_identical(tmp_path):
    p = _plan((11.0, 20.0))
    R1, s1 = check.run(copy.deepcopy(p), completeness=True)
    R2, s2 = check.run(copy.deepcopy(p), completeness=True, core_shape_index=None)
    assert json.dumps(R1.items, sort_keys=True) == json.dumps(R2.items, sort_keys=True)
    assert json.dumps(s1, sort_keys=True, default=str) == json.dumps(s2, sort_keys=True, default=str)
    assert "core_shape" not in s1 and not any(i["check"] == "core_shape_change" for i in R1.items)


def test_cli_flag(tmp_path):
    idx = _index(tmp_path, {"core_a": [(10.0, 20.0)]})
    pj = tmp_path / "die_plan.json"
    pj.write_text(json.dumps(_plan((11.0, 20.0))))
    out = tmp_path / "o"
    cmd = [sys.executable, "-I", str(HERE / "check.py"), str(pj), "--out", str(out), "--quiet"]
    subprocess.run(cmd, capture_output=True, text=True)
    base = json.loads((out / "g0_report.json").read_text())
    subprocess.run(cmd + ["--core-shape-index", idx], capture_output=True, text=True)
    new = json.loads((out / "g0_report.json").read_text())
    assert not any(i["check"] == "core_shape_change" for i in base["findings"])
    assert sum(i["check"] == "core_shape_change" for i in new["findings"]) == 1


def test_variant_family(tmp_path):
    # a module with no signed record of its own is checked against its base-name family (_bfp / _cs1 / __cdN): WARN, not ERROR
    idx = _index(tmp_path, {"core_a": [(10.0, 20.0)], "dsdv_gunit_l1": [(5.0, 6.0)]})
    assert not _errs(_plan((11.0, 20.0), module="core_a_bfp"), idx)          # not an ERROR
    R, _ = check.run(_plan((11.0, 20.0), module="core_a_bfp"), completeness=True, core_shape_index=idx)
    assert [i for i in R.items if i["check"] == "core_shape_change" and i["level"] == "WARN"]
    R, _ = check.run(_plan((10.0, 20.0), module="core_a_cs1"), completeness=True, core_shape_index=idx)
    assert not [i for i in R.items if i["check"] == "core_shape_change"]
    # gunit pieces are different cores, never one family
    assert not CS.violations(_plan((9.0, 6.0), module="dsdv_gunit_l1f_ba0"), CS.load_index(idx))
    assert CS.base_name("ot_hbm_sm_attn_be__cd13") == "ot_hbm_sm_attn_be"
