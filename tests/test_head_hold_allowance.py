"""HEAD-CORE-R18: per-view ledgered allowance for the structural FF hold stop (head_hold_allowance.py + the
ot_hold_allowance_ok branch of tools/orfs_hold_mm.tcl ot_hold_structural_gate) fails closed."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import head_hold_allowance as H  # noqa: E402

CFG = "export DESIGN_NICKNAME = hd_elemA_rb\nexport OT_VCLK_TT = 250\nexport OT_VCLK_FF = 202.5\n"
SDC = ("create_clock -name clk -period 833 [get_ports ft_mstrap_i]\ncreate_clock -name vclk -period 833\n"
       "set_clock_latency -source 250.0000 [get_clocks vclk]\nset_input_delay -min -40 -clock vclk [all_inputs]\n")
VFF = "set_clock_latency -source 202.5 [get_clocks vclk]\n"


def tsv_text(vals, basis="RCX /work/x/6_final.spef corner FF"):
    return f"# basis {basis}\n" + "".join(f"r{i}/CLK\tn\t{v}\t{v}\t{v}\t{v}\n" for i, v in enumerate(vals))


def mk(tmp, vals=(200.0, 210.0), kit_name="elemA_m2.eco_r18", **over):
    kit = tmp / kit_name
    kit.mkdir()
    (kit / "config.mk").write_text(over.pop("cfg", CFG))
    (kit / "constraint.sdc").write_text(SDC)
    (kit / "vclk_ff.sdc").write_text(over.pop("vff", VFF))
    tsv = tmp / "ins_FF.tsv"
    tsv.write_text(tsv_text(vals, over.pop("basis", "RCX /work/x/6_final.spef corner FF")))
    a = dict(schema=H.SCHEMA, id="HEAD-R18-elemA_m2", ruling="COORD 2026-10-27 07:47 HEAD-CORE-R17 (2)",
             ledger="lanes/HEAD-CORE-LAT.md R18", design_nickname="hd_elemA_rb", kit_dir="elemA_m2",
             stage="post_route_eco", limits=dict(ws_floor_ps=-108.0, max_endpoints=2000, classes=["I2R"]),
             binding=dict(ot_vclk_tt=250, ot_vclk_ff=202.5,
                          constraint_sdc_sha256=hashlib.sha256(SDC.encode()).hexdigest()),
             insertion=dict(corner="FF", statistic="mean", band_ps=[182.5, 222.5],
                            tsv_sha256=hashlib.sha256(tsv.read_bytes()).hexdigest(),
                            mean_ps=sum(vals) / len(vals), n=len(vals)))
    for k, v in over.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            a[k].update(v)
        else:
            a[k] = v
    ap = tmp / "allow.json"
    ap.write_text(json.dumps(a))
    return ap, kit, tsv


def run(ap, kit, tsv, out=None):
    return H.main([str(ap), "--kit", str(kit), "--tsv", str(tsv)] + (["--write", str(out)] if out else []))


def test_ok_writes_dict(tmp_path, capsys):
    ap, kit, tsv = mk(tmp_path)
    out = kit / "hold_allowance.tcl"
    assert run(ap, kit, tsv, out) == 0
    assert "HEAD_HOLD_ALLOWANCE ok id HEAD-R18-elemA_m2" in capsys.readouterr().out
    t = out.read_text()
    assert "nickname hd_elemA_rb" in t and "ws_floor_ps -108" in t and "classes [list I2R]" in t


@pytest.mark.parametrize("over", [
    dict(design_nickname="hd_elemB_rb"),                     # other view
    dict(kit_dir="elemA_m12"),                               # other kit
    dict(limits=dict(ws_floor_ps=-140.0)),                   # structural, not an allowance
    dict(limits=dict(max_endpoints=5000)),                   # widens the default cap
    dict(binding=dict(ot_vclk_ff=170)),                      # vclk binding changed
    dict(binding=dict(constraint_sdc_sha256="0" * 64)),      # die IO contract changed
    dict(insertion=dict(band_ps=[150, 190])),                # insertion outside band -> tree fix
    dict(insertion=dict(mean_ps=190.0)),                     # recorded mean does not match the TSV
    dict(insertion=dict(tsv_sha256="0" * 64)),               # TSV is not the recorded one
    dict(insertion=dict(corner="TT")),
    dict(ledger=""),
    dict(schema="x"),
])
def test_fail_closed(tmp_path, over, capsys):
    ap, kit, tsv = mk(tmp_path, **over)
    out = kit / "hold_allowance.tcl"
    assert run(ap, kit, tsv, out) == 2
    assert "HEAD_HOLD_ALLOWANCE FAIL" in capsys.readouterr().out
    assert not out.exists()


def test_fail_insertion_out_of_band(tmp_path):
    ap, kit, tsv = mk(tmp_path, vals=(230.0, 240.0))
    assert run(ap, kit, tsv) == 2


def test_fail_grt_basis(tmp_path):
    ap, kit, tsv = mk(tmp_path, basis="GRT estimate_parasitics corner FF")
    assert run(ap, kit, tsv) == 2


def test_fail_vclk_ff_file(tmp_path):
    ap, kit, tsv = mk(tmp_path, vff="set_clock_latency -source 170 [get_clocks vclk]\n")
    assert run(ap, kit, tsv) == 2


def test_fail_cfg_vclk(tmp_path):
    ap, kit, tsv = mk(tmp_path, cfg=CFG.replace("202.5", "190"))
    assert run(ap, kit, tsv) == 2


# ---- the Tcl gate branch, with the STA commands mocked ----
GATE_MOCK = r"""
set ::ot_mm_active 1; set ::ot_mm_synced 1
set ::env(DESIGN_NICKNAME) hd_elemA_rb
proc ot_hold_stats {} { return [list $::W 0 $::N] }
proc ot_hold_stage {} { return grt }
proc ot_hold_paths {{limit 0}} { return $::PATHS }
proc get_property {p k} { return [dict get $p $k] }
proc get_full_name {x} { return $x }
proc ot_pin_class {name} { expr {[string first "/" $name] < 0 ? "port" : "reg"} }
"""


def gate_src():
    t = (ROOT / "tools" / "orfs_hold_mm.tcl").read_text()
    a = t.index("proc ot_hold_allowance_ok")
    b = t.index("proc ot_repair_timing")
    return t[a:b]


def tcl(tmp, w, n, paths, allow=None, stage=None):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    s = GATE_MOCK + gate_src() + f"set ::env(REPORTS_DIR) {tmp}\nset ::W {w}; set ::N {n}\nset ::PATHS [list {paths}]\n"
    if allow is not None:
        (tmp / "a.tcl").write_text(allow)
        s += f"set ::env(OT_HOLD_ALLOWANCE_TCL) {tmp / 'a.tcl'}\n"
    if stage:
        s += f"set ::ot_hold_gate_stage {stage}\n"
    s += "if {[catch {ot_hold_structural_gate} e]} { puts \"GATE_STOP $e\" } else { puts GATE_PASS }\n"
    (tmp / "t.tcl").write_text(s)
    return subprocess.run(["tclsh", str(tmp / "t.tcl")], capture_output=True, text=True).stdout


ALLOW = ("set ::ot_hold_allowance [dict create id X nickname hd_elemA_rb stage post_route_eco "
         "ws_floor_ps -108 max_endpoints 2000 classes [list I2R]]\n")
I2R = "{slack -102 startpoint in_a endpoint u/r1/D} {slack -90 startpoint in_b endpoint u/r2/D}"


def test_gate_default_unchanged(tmp_path):
    assert "GATE_PASS" in tcl(tmp_path, -99.0, 10, I2R)
    assert "GATE_STOP OT_HOLD_STRUCTURAL" in tcl(tmp_path, -102.8, 795, I2R)


def test_gate_allowance_applies(tmp_path):
    o = tcl(tmp_path, -102.8, 795, I2R, ALLOW, "post_route_eco")
    assert "OT_HOLD_STRUCTURAL_ALLOWED stage=post_route_eco id=X" in o and "I2R=2" in o and "GATE_PASS" in o


@pytest.mark.parametrize("w,n,paths,stage,why", [
    (-110.0, 795, I2R, "post_route_eco", "floor"),
    (-102.8, 2500, I2R, "post_route_eco", "cap"),
    (-102.8, 795, I2R, None, "stage"),
    (-102.8, 795, I2R + " {slack -50 startpoint u/q/CLK endpoint u/r3/D}", "post_route_eco", "class"),
])
def test_gate_allowance_refuses(tmp_path, w, n, paths, stage, why):
    o = tcl(tmp_path, w, n, paths, ALLOW, stage)
    assert "NOT APPLIED" in o and "GATE_STOP OT_HOLD_STRUCTURAL" in o, (why, o)


def test_gate_allowance_other_view(tmp_path):
    o = tcl(tmp_path, -102.8, 795, I2R, ALLOW.replace("hd_elemA_rb", "hd_elemB_rb"), "post_route_eco")
    assert "GATE_STOP OT_HOLD_STRUCTURAL" in o


def test_gate_allowance_unreadable(tmp_path):
    o = tcl(tmp_path, -102.8, 795, I2R, "set x {", "post_route_eco")
    assert "GATE_STOP OT_HOLD_STRUCTURAL: allowance" in o
