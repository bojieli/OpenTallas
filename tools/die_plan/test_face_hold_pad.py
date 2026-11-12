"""S81-CORES-1: face_hold_pad.py (per-endpoint sizing, spec emission, kit staging) and its Tcl hook."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_hold_pad as F

REPORT = """\
Endpoint                                  Required    Actual     Slack
-------------------------------------------------------------------
u_bound.u_cland_ft2_i/g_freg.u_face/q[0]$_DFF_P_/D   150.00   53.07   -96.93 (VIOLATED)
u_bound.u_cland_ft2_i/g_freg.u_face/q[1]$_DFF_P_/D   150.00   140.00   -10.00 (VIOLATED)
u_bound.u_cland_ft3_i/g_freg.u_face/q[9]$_DFF_P_/D   150.00   180.00   30.00 (MET)
u_bound.u_cland_ft3_i/g_freg.u_face/q[9]$_DFF_P_/D   150.00   150.00   0.00 (MET)
some/other/line
u_x/ff/CLK   1.0 2.0 3.0
"""


def test_cells_for_is_per_slack_not_flat():
    assert F.cells_for(-96.93) == 3          # (10 + 96.93) / 37 = 2.89 -> 3
    assert F.cells_for(-10.0) == 1
    assert F.cells_for(0.0) == 1             # below guard 10
    assert F.cells_for(10.0) == 0 and F.cells_for(55.0) == 0
    assert F.cells_for(-1000.0) == F.N_MAX   # capped, never silently larger
    assert F.cells_for(-96.93, per_cell=20.0) == 6
    with pytest.raises(ValueError):
        F.cells_for(0, per_cell=0)


def test_parse_takes_D_pins_and_worst_slack():
    s = F.parse_end_report(REPORT)
    assert s == {"u_bound.u_cland_ft2_i/g_freg.u_face/q[0]$_DFF_P_": -96.93,
                 "u_bound.u_cland_ft2_i/g_freg.u_face/q[1]$_DFF_P_": -10.0,
                 "u_bound.u_cland_ft3_i/g_freg.u_face/q[9]$_DFF_P_": 0.0}


def test_make_spec_pads_only_failing_endpoints():
    spec = F.make_spec(F.parse_end_report(REPORT), source="r")
    assert spec["endpoints"] == 3 and spec["padded"] == 3 and spec["cells"] == 3 + 1 + 1
    spec2 = F.make_spec({"a": 40.0, "b": -5.0}, guard=0.0)
    assert spec2["per_endpoint"] == {"b": 1} and spec2["endpoints"] == 2


def test_tcl_dict_validates_and_quotes():
    spec = F.make_spec({"u/q[0]$_DFF_P_": -50.0})
    t = F.tcl_dict(spec)
    assert "set ::ot_fp_default 0" in t and "{u/q[0]$_DFF_P_} 2" in t and "{*g_freg.u_face*}" in t
    bad = dict(spec, per_endpoint={"x": 99})
    with pytest.raises(ValueError):
        F.tcl_dict(bad)
    with pytest.raises(ValueError):
        F.tcl_dict(dict(spec, schema="nope"))
    with pytest.raises(ValueError):
        F.tcl_dict(dict(spec, per_endpoint={"a{b": 1}))


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_tcl_dict_parses_in_tclsh(tmp_path):
    spec = F.make_spec({"u/q[0]$_DFF_P_": -50.0, "u/q[1]$_DFF_P_": -5.0})
    p = tmp_path / "n.tcl"
    p.write_text(F.tcl_dict(spec))
    out = subprocess.run(["tclsh"], input=f"source {p}\nputs [dict size $::ot_fp_per]\nputs [dict get $::ot_fp_per {{u/q[0]$_DFF_P_}}]\n",
                         capture_output=True, text=True)
    assert out.stdout.split() == ["2", "2"], out.stderr


def test_stage_installs_hook_idempotently(tmp_path):
    kd = tmp_path
    (kd / "hold_budget.tcl").write_text("# GENERATED\nsource /work/face_capture_release.tcl\n")
    spec = F.make_spec({"a/q": -50.0})
    r = F.stage(kd, spec)
    assert r["padded"] == 1 and r["cells"] == 2
    hb = (kd / "hold_budget.tcl").read_text().splitlines()
    assert hb[1] == "source /work/face_hold_pad.tcl" and hb[2] == "source /work/face_capture_release.tcl"
    F.stage(kd, spec)
    assert (kd / "hold_budget.tcl").read_text().count("face_hold_pad.tcl") == 1
    for f in ("face_hold_pad.tcl", "face_hold_pad_n.tcl", "face_hold_pad.json"):
        assert (kd / f).is_file()


def test_stage_fails_closed_without_pre_cts_hook(tmp_path):
    with pytest.raises(SystemExit):
        F.stage(tmp_path, F.make_spec({"a": -50.0}))


def test_hook_tcl_guards():
    t = (Path(F.__file__).resolve().parent / "face_hold_pad.tcl").read_text()
    for needle in ("HB4xp67_ASAP7_75t_R", "stale sizing", "OT_FACE_PAD_ALLOW_MISSING", "ot_fp_per", "$ot_fp_dt disconnect"):
        assert needle in t


def test_cli_size(tmp_path):
    rep = tmp_path / "r.txt"
    rep.write_text(REPORT)
    out = tmp_path / "s.json"
    assert F.main(["size", "--report", str(rep), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["cells"] == 5
    empty = tmp_path / "e.txt"
    empty.write_text("nothing\n")
    assert F.main(["size", "--report", str(empty), "--out", str(out)]) == 2


def test_generator_wires_option_after_hold_budget():
    g = (Path(__file__).resolve().parents[2] / "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py").read_text()
    assert "--face-hold-pad" in g and "face_hold_pad.stage(kd" in g
    assert g.index("face_hold_pad.stage(kd") > g.index("(kd / \"hold_budget.tcl\").write_text(")


def test_parse_real_openroad_end_rows_with_master_column():
    rep = ("u_bound.u_cland_ft2_i/g_freg.u_face/q[217]$_DFF_P_/D (DFFHQNx2_ASAP7_75t_R)  274.53  177.60  -96.93 (VIOLATED)\n"
           "u_bound.u_cland_ft3_i/g_freg.u_face/q[508]$_DFF_P_/D (DFFHQNx1_ASAP7_75t_R)  224.48  194.15  -30.33 (VIOLATED)\n")
    assert F.parse_end_report(rep) == {"u_bound.u_cland_ft2_i/g_freg.u_face/q[217]$_DFF_P_": -96.93,
                                       "u_bound.u_cland_ft3_i/g_freg.u_face/q[508]$_DFF_P_": -30.33}
