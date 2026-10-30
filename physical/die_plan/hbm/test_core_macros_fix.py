"""DIE-HBM-26: core_macros_fix (HBM-053 master field, HBM-054 static sites)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("core_macros_fix", HERE / "core_macros_fix.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

LEF = """MACRO {m}
  CLASS BLOCK ;
  SIZE {w} BY {h} ;
END {m}
"""


def _lefs(d):
    for m, w, h in (("ot_sram_1r1w_128x256_m1_r2c2", 94.824, 41.064), ("ot_sram_1r1w_128x256_m1_r0c0_pc", 94.824, 41.064),
                    ("ot_sram_1r1w_256x256_m2_r2c2", 172.824, 41.064)):
        (d / m).mkdir(parents=True)
        (d / m / f"{m}.lef").write_text(LEF.format(m=m, w=w, h=h))
    return F.lef_sizes(str(d))


def _plan(d, cores):
    d.mkdir()
    (d / "die_plan.json").write_text("{}")
    (d / "core_macros.json").write_text(json.dumps(dict(cores=cores)))
    return d


def test_width_master_resolved_by_size_and_evidence(tmp_path):
    sizes = _lefs(tmp_path / "lef")
    row = dict(name="u_m", master="width", orient="R0", rect_um=[64.8, 53.73, 159.624, 94.794])
    with pytest.raises(SystemExit):           # size alone is ambiguous (r2c2 vs r0c0_pc)
        F.resolve_master("c", row, sizes, {})
    assert F.resolve_master("c", row, sizes, {"c": ["ot_sram_1r1w_128x256_m1_r2c2"]}) == "ot_sram_1r1w_128x256_m1_r2c2"
    with pytest.raises(SystemExit):           # evidence that does not fit the size
        F.resolve_master("c", row, sizes, {"c": ["ot_sram_1r1w_256x256_m2_r2c2"]})


def test_channel_rule(tmp_path):
    ok = [dict(rect_um=[20, 20, 114.824, 61.064]), dict(rect_um=[20, 80, 114.824, 121.064])]
    assert F.channel_errors(ok, [200, 200])[0] == []
    near_edge = [dict(rect_um=[10, 20, 104.824, 61.064])]
    assert any("W channel" in e for e in F.channel_errors(near_edge, [200, 200])[0])
    stacked = [dict(rect_um=[20, 20, 114.824, 61.064]), dict(rect_um=[20, 61.088, 114.824, 102.152])]
    assert any("interior" in e for e in F.channel_errors(stacked, [200, 200])[0])


def test_cli_end_to_end(tmp_path):
    _lefs(tmp_path / "lef")
    plan = _plan(tmp_path / "p", {
        "a": dict(status="KNOWN", outline_um=[200, 200],
                  macros=[dict(name="u_m", master="width", orient="R0", rect_um=[20, 20, 114.824, 61.064])]),
        "b": dict(status="UNKNOWN", outline_um=[300, 200], why="no placement")})
    ev = tmp_path / "ev.json"
    ev.write_text(json.dumps({"a": ["ot_sram_1r1w_128x256_m1_r2c2"]}))
    st = tmp_path / "st.json"
    st.write_text(json.dumps({"b": dict(basis="t", macros=[
        dict(name="m0", master="ot_sram_1r1w_256x256_m2_r2c2", origin_um=[20, 20], orient="R0")])}))
    out = tmp_path / "o"
    subprocess.run([sys.executable, str(HERE / "core_macros_fix.py"), str(plan), "--out", str(out), "--lef-dir",
                    str(tmp_path / "lef"), "--evidence", str(ev), "--static", str(st)], check=True,
                   capture_output=True)
    cm = json.loads((out / "core_macros.json").read_text())["cores"]
    assert cm["a"]["macros"][0]["master"] == "ot_sram_1r1w_128x256_m1_r2c2"
    assert cm["b"]["status"] == "KNOWN" and cm["b"]["macros"][0]["rect_um"] == [20, 20, 192.824, 61.064]
    assert (out / "die_plan.json").read_text() == "{}"


def test_static_rejects_channel_violation(tmp_path):
    sizes = _lefs(tmp_path / "lef")
    cm = dict(cores={"b": dict(status="UNKNOWN", outline_um=[200, 200])})
    bad = {"b": dict(basis="t", macros=[dict(name="m0", master="ot_sram_1r1w_256x256_m2_r2c2", origin_um=[8, 20])])}
    with pytest.raises(SystemExit):
        F.fix(cm, sizes, {}, bad, set())
