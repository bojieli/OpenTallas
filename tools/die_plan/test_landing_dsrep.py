"""DIE-S81-85 11-09: ring read-select replication (DSREP) on plain forwarded-clock landings.

ot_dp_clk_landing DSREP (default 1 = identical logic) passes through ot_meso_ring to ot_meso_dsel SREP (DSREP-1,
DIE-HEAD-58).  A landing sidecar row selects it with ring_params {"DSREP": n}; the S81 sidecar sets DSREP 4 on the six
landings into iqf (iqf__t1 slew class: ring read-select nets fanout 87-183) and on no other row.  Function: lock-step
bench bench/landing_dsrep/run.sh (DSREP 1 vs 4, W 513 / 514, default and CLAND_WCHK forms, plus a stuck-copy mutant).
"""
import json
import re
from pathlib import Path

import clock_landings as CL
from test_clock_landings import vehicle

ROOT = Path(__file__).resolve().parents[2]
BODY = ("module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
        " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\n"
        "endmodule\n")


def test_ring_params_dsrep_is_emitted_on_the_plain_ring():
    p, t = vehicle()
    t["ports"][0]["ring_params"] = {"DSREP": 4}
    assert "ot_dp_clk_landing #(.W(5), .DSREP(4)) u_cland_y (" in CL.Landings(p, t).type_rtl("B", BODY)
    p, t = vehicle()
    assert "ot_dp_clk_landing #(.W(5)) u_cland_y (" in CL.Landings(p, t).type_rtl("B", BODY)


def test_rtl_plumbs_dsrep_to_the_select_copies_with_default_one():
    land = (ROOT / "rtl/common/ot_dp_clk_landing.sv").read_text()
    fifo = (ROOT / "rtl/common/ot_meso_fifo.sv").read_text()
    head = land[land.index("module ot_dp_clk_landing #("):land.index(");", land.index("module ot_dp_clk_landing #("))]
    assert re.search(r"parameter integer DSREP = 1\b", head)
    assert re.search(r"\) u_ring \(", land) and ".DSREP(DSREP)) u_ring (" in land
    ring = fifo[fifo.index("module ot_meso_ring #("):fifo.index("module ot_meso_sel")]
    assert re.search(r"parameter int DSREP\s+= 1\b", ring)
    assert ".SREP(DSREP)) u_dsel (" in ring


def test_s81_sidecar_sets_dsrep_4_on_exactly_the_iqf_landings():
    side = json.loads((ROOT / "physical/die_plan/s81/h2_2249/landed_sidecar_h2.json").read_text())
    rows = [r for r in side["ports"] if "DSREP" in r.get("ring_params", {})]
    assert sorted(r["port"] for r in rows) == sorted(r["port"] for r in side["ports"] if r["dst"] == "iqf")
    assert len(rows) == 6 and all(r["ring_params"] == {"DSREP": 4} and "ring_module" not in r for r in rows)


def test_bench_is_present_with_its_mutant():
    run = (ROOT / "tools/die_plan/bench/landing_dsrep/run.sh").read_text()
    assert "ot_meso_fifo_mutant.sv" in run and "MUTANT NOT DETECTED" in run
    res = (ROOT / "tools/die_plan/bench/landing_dsrep/result.txt").read_text()
    assert "BENCH rc=0" in res and res.count("-> TB_DSREP PASS") == 4 and res.count("-> TB_DSREP FAIL") == 4
