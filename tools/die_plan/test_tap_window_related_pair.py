"""TAPWIN-1109 (COORD ruling tapwin-1109, DIE-S81-85): an unmeasured type's kit SDC charges a cross-tap pair the
inter-tap related-pair budget X (gen_phys.tap_related_pair_ps, default 40 ps), not the full die band window_ps
(S81 iqf__t1: 180 ps on every cross-tap reg2reg path).  Same-tap pairs keep CRPR at the common port; measured
windows (per_type_ps / per_port_ps) are unchanged; the die STA kit contract checks every real tap pair against X.
The OpenSTA test times a two-tap netlist with the exact emitted window lines (skipped without docker / the image)."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import die_sta_related as DSR
import gen_phys
import schema
import sdc_lint

HERE = Path(__file__).parent
X = gen_phys.TAP_RELATED_PAIR_PS


def _raw(window=180.0, **tw):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    raw["clock"]["tap_window"] = dict(window_ps=window, **tw)
    return raw


def _sdc(P, tn="src"):
    return gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn))


def _early(s):
    return sorted({float(v) for v in re.findall(r"^set_clock_latency -source -early -clock clk (-?[\d.]+) ", s, re.M)})


def test_unmeasured_type_charges_related_pair_budget_not_band():
    P = schema.Plan(_raw())
    assert X == 40.0 and gen_phys.tap_window_band_ps(P, "src") == 180.0
    assert gen_phys.tap_window_ps(P, "src") == gen_phys.tap_window_ps(P) == X
    s = _sdc(P)
    assert _early(s) == [-X]
    assert "-180.0000" not in s and "TAPWIN-1109: W = related-pair budget 40 ps (die band 180 ps" in s
    # IO contract exact: the IO shift follows the charged window (input max -X, output min +X)
    assert gen_phys.tap_window_io_shift(P, "src") == (-X, X)
    assert "set_input_delay -max 126.6000 -clock vclk $non_clk_in" in s       # 166.6 - 40
    ctx = sdc_lint.kit_context(P, "src")
    assert ctx["tap_window_ps"] == X and sdc_lint.lint(s, **ctx) == []
    assert sdc_lint.lint(s.replace("-early -clock clk -40.0000", "-early -clock clk -180.0000"), **ctx)


def test_override_and_byte_identical_when_budget_not_below_band():
    old = _sdc(schema.Plan(_raw(80.0, related_pair_ps=80.0)))
    assert _sdc(schema.Plan(_raw(80.0, related_pair_ps=200.0))) == old        # X >= W: pre-TAPWIN form
    assert "TAPWIN-1109" not in old
    P = schema.Plan(_raw(related_pair_ps=25.0))
    assert gen_phys.tap_window_ps(P, "src") == 25.0 and _early(_sdc(P)) == [-25.0]
    with pytest.raises(ValueError):
        gen_phys.tap_related_pair_ps(schema.Plan(_raw(related_pair_ps=-1.0)))


def test_measured_windows_unchanged():
    P = schema.Plan(_raw(per_type_ps={"src": 120.0}))
    assert gen_phys.tap_window_ps(P, "src") == 120.0 and _early(_sdc(P, "src")) == [-120.0]
    assert gen_phys.tap_window_ps(P, "mid") == X                               # unlisted type: budget
    ports = [n for n, _x, _y in gen_phys.clock_pins(P, "src")]
    Q = schema.Plan(_raw(per_port_ps={"src": {ports[0]: 70.0, **{n: 30.0 for n in ports[1:]}}}))
    assert gen_phys.port_window_ps(Q, "src", ports[0]) == 70.0
    assert _early(_sdc(Q, "src")) == [-70.0, -30.0]


def test_die_sta_contract_checks_pairs_against_budget():
    pc = dict(insertion_tol_ps=40, seam_hold=dict(sender_ps=25, seam_ps=80), tap_window=dict(window_ps=180))
    wi = DSR.kit_windows(pc)["intra"]
    assert wi["ps"] == X and wi["band_ps"] == 180.0 and wi["related_pair_ps"] == X
    assert "TAPWIN-1109" in wi["basis"]


STA_NET = """module two_tap (clk, clk_t1, d, q);
  input clk, clk_t1, d; output q;
  wire ca, cb, cc, qan, qbn, qcn;
  BUFx2_ASAP7_75t_R bca (.A(clk), .Y(ca));
  BUFx2_ASAP7_75t_R bcb (.A(clk), .Y(cb));
  BUFx2_ASAP7_75t_R bcc (.A(clk_t1), .Y(cc));
  DFFHQNx1_ASAP7_75t_R fa (.CLK(ca), .D(d), .QN(qan));
  DFFHQNx1_ASAP7_75t_R fb (.CLK(cb), .D(qan), .QN(qbn));
  DFFHQNx1_ASAP7_75t_R fc (.CLK(cc), .D(qan), .QN(qcn));
  AND2x2_ASAP7_75t_R o (.A(qbn), .B(qcn), .Y(q));
endmodule
"""
STA_TCL = """set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_liberty $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_verilog /w/two_tap.v
link_design two_tap
set sta_crpr_enabled 1
proc slk {to kind} {
  set p [find_timing_paths -from [get_pins fa/CLK] -to [get_pins $to/D] -path_delay $kind]
  return [format %.3f [get_property [lindex $p 0] slack]]
}
foreach n {base win} {
  read_sdc /w/$n.sdc
  set_propagated_clock [all_clocks]
  puts "FORM $n [slk fb max] [slk fc max] [slk fb min] [slk fc min]"
}
"""


def _sta_image():
    img = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
    if not shutil.which("docker"):
        return None
    r = subprocess.run(["docker", "image", "inspect", img], capture_output=True)
    return img if r.returncode == 0 else None


def test_opensta_two_tap_cross_pays_budget_same_tap_unchanged(tmp_path):
    img = _sta_image()
    if not img:
        pytest.skip("no docker / ORFS image for the OpenSTA two-tap run")
    P = schema.Plan(_raw())
    win = [l.replace(re.search(r"\[get_ports \{([^}]*)\}\]", l).group(0), "[get_ports {clk clk_t1}]")
           for l in gen_phys.tap_window_tcl(P, "src", core=False).splitlines() if "-clock clk " in l]
    assert len(win) == 2 and "-early -clock clk -40.0000" in win[0] and "-late -clock clk 0.0000" in win[1]
    clk = "create_clock -name clk -period 833 [get_ports {clk clk_t1}]\n"
    (tmp_path / "two_tap.v").write_text(STA_NET)
    (tmp_path / "run.tcl").write_text(STA_TCL)
    (tmp_path / "base.sdc").write_text(clk)
    (tmp_path / "win.sdc").write_text(clk + "\n".join(win) + "\n")
    os.chmod(tmp_path, 0o777)
    r = subprocess.run(["docker", "run", "--rm", "--memory", "2g", "-v", f"{tmp_path}:/w", img,
                        "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta", "-no_init", "-exit", "/w/run.tcl"],
                       capture_output=True, text=True, timeout=600)
    rows = {m[0]: [float(v) for v in m[1:]] for m in re.findall(r"^FORM (\w+) (\S+) (\S+) (\S+) (\S+)$", r.stdout, re.M)}
    assert set(rows) == {"base", "win"}, r.stdout + r.stderr
    (bs_same, bs_cross, bh_same, bh_cross), (ws_same, ws_cross, wh_same, wh_cross) = rows["base"], rows["win"]
    assert ws_same == pytest.approx(bs_same, abs=0.01) and wh_same == pytest.approx(bh_same, abs=0.01)  # CRPR
    assert bs_cross - ws_cross == pytest.approx(X, abs=0.01)                    # setup: capture early -X
    assert bh_cross - wh_cross == pytest.approx(X, abs=0.01)                    # hold: launch early -X
