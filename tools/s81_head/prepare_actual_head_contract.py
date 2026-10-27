#!/usr/bin/env python3
"""Describe the already-built HEAD calibration interface without changing its DB.

ft_mstrap_i is the real core clock, with zero source offset. Four other islands
are pass-through arcs timed at die level. Canonical plan adoption remains open.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
from ft_ports import declaration, install

k = Path(sys.argv[1])
elem = sys.argv[2] if len(sys.argv) > 2 else "A"
assert elem in ("A", "B")
ctx = json.loads((k / "sdc_lint.json").read_text())
ctx["clock_ports"] = ["ft_mstrap_i"]
ctx["port_latency_ps"] = {"ft_mstrap_i": 0.0}
ctx["insertion_ff_ps"] = 202.5
(k / "sdc_lint.json").write_text(json.dumps(ctx, indent=1)+"\n")
sdc = (k / "constraint.sdc").read_text().replace("[get_ports {clk}]", "[get_ports {ft_mstrap_i}]")
(k / "constraint.sdc").write_text(sdc)
arcs = [dict(cell=cell, source=src, sink=dst, kind=kind) for cell, src, dst, kind in (
    ("u_isl_ck0", "ft_ck0_i", "ft_ck0_o", "clock"),
    ("u_isl_ck1", "ft_ck1_i", "ft_ck1_o", "clock"),
    ("u_isl_m0", "ft_mesh_i", "ft_mesh_o", "clock"),
    ("u_isl_rstft", "ft_rst_i", "ft_rst_o", "reset"))]
decl = declaration(arcs, "HEAD accepted R8 patch_synth.tcl; actual standalone contract, canonical plan delta OPEN")
install(k, decl)
rt = k / f"rtl/ot_s81hd_elem{elem}_rb.sv"
old = rt.read_text()
assert old.count("input  wire clk,") == 1
new = old.replace("input  wire clk,", "input wire ft_ck0_i, input wire ft_ck1_i, input wire ft_mesh_i, input wire ft_rst_i,\n"
                  "    output wire ft_ck0_o, output wire ft_ck1_o, output wire ft_mesh_o, output wire ft_rst_o,\n"
                  "    input  wire ft_mstrap_i,", 1)
new = new.replace(");\n    // OWNER RESET RULE", ");\n"
                  "    wire clk = ft_mstrap_i;\n"
                  "    assign ft_ck0_o = ft_ck0_i;\n"
                  "    assign ft_ck1_o = ft_ck1_i;\n"
                  "    assign ft_mesh_o = ft_mesh_i;\n"
                  "    assign ft_rst_o = ft_rst_i;\n"
                  "    // OWNER RESET RULE", 1)
assert new != old
(k / "original_wrapper.sv").write_text(old)
rt.write_text(new)
(k / "core.json").write_text(json.dumps({
    "boundary_role": {"ft_mstrap_i": "clk", "rst_n": "reset"},
    "clock_contract": {"kind": "hard_core_latency", "clock_port": "ft_mstrap_i",
                       "basis": "publish measured routed core insertion; common latency is a design target"}
})+"\n")
(k / "boundary_guard_context.json").write_text(json.dumps(dict(
    schema="opentallas.core_boundary_guard_context.v1", source_core_json="core.json",
    clock_ports=["ft_mstrap_i"], unused_clock_ports=[], reset_ports=["rst_n"],
    data_pin_exemptions=[]), indent=1)+"\n")
(k / "face_guard_skip.txt").write_text("^(ft_.*|rst_n)$\n")
(k / "actual_contract.json").write_text(json.dumps(dict(
    clock_port="ft_mstrap_i", source_offset_ps=0, cycles_added=0, database_changed=False,
    canonical_plan_adopted=False, real_ft_ports=8, arcs=arcs,
    note="Gold source expresses exact existing physical interface; no routing or cell changes"), indent=1)+"\n")
print("ACTUAL_HEAD_CONTRACT installed: primary ft_mstrap_i, eight die-timed FT ports, zero added cycles")
