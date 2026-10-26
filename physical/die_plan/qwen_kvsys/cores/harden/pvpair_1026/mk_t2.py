#!/usr/bin/env python3
"""CORES-KITS/KVX t2 = t1 + (a) IO-HOLD option A sender_min input-min (gen_core_kit_kv.sender_min_ports rule: vector data
inputs 12.5 ps, scalars/clock/reset keep -40) + (b) early core tap re-landed on the t1 post-CTS measured pin-reg
insertion (port->pin-reg TT 321.2 / FF 259.5 on placement RCX RC): -53 ps puts TT 268 (+18) / FF 206.5 (+4) on the plan
basis 250 / 202.5 (+-20).  Usage: mk_t2.py KITDIR"""
import json, re, sys
from pathlib import Path
k = Path(sys.argv[1])
cj = json.loads((k / "core.json").read_text())
sdc = (k / "constraint.sdc").read_text()
clks = ["s0__clk", "s1__clk"]
rsts = [b for b in cj["port_decl"] if re.search(r"(^|__)(rst_n|arst_n)$", b)]
ioa = {b: 12.5 for b, d in cj["port_decl"].items()
       if d[0] == "input" and b not in clks and b not in rsts and int(d[1]) > int(d[2])}
assert "set_clock_latency -source -35.0000 [get_ports {s1__clk}]" in sdc
sdc = sdc.replace("set_clock_latency -source -35.0000 [get_ports {s1__clk}]",
                  "# CORES-KITS/KVX t2: re-landed on t1 post-CTS measured port->pin-reg TT 321.2 / FF 259.5 (-53 -> TT 268 / FF 206.5)\n"
                  "set_clock_latency -source -53.0000 [get_ports {s1__clk}]")
anchor = "set_output_delay -min 0.0000 -clock vclk [all_outputs]\n"
assert anchor in sdc
add = ("# IO-HOLD option A (OT_IO_HOLD=sender_min): sender output-min guarantee; parent io_hold_parent.py check required\n"
       + "set_input_delay -min 12.5000 -clock vclk [get_ports {" + " ".join(p + "[*]" for p in sorted(ioa)) + "}]\n")
sdc = sdc.replace(anchor, anchor + add, 1)
(k / "constraint.sdc").write_text(sdc)
(k / "io_hold.tcl").write_text(
    "# GENERATED (CORES-KITS/KVX t2, gen_core_kit_kv.py format): IO-HOLD option A per-port min input delays (OT_IO_HOLD=sender_min)\n"
    "proc ot_io_hold_apply {vclk} {\n"
    + "  set_input_delay -min 12.5000 -clock $vclk [get_ports {" + " ".join(p + "[*]" for p in sorted(ioa)) + "}]\n"
    + f"  puts \"OT_IO_HOLD sender_min ports {len(ioa)} fallback 40\"\n}}\n")
lj = json.loads((k / "sdc_lint.json").read_text())
lj["hold_in_min_ports_ps"] = ioa
(k / "sdc_lint.json").write_text(json.dumps(lj, indent=1) + "\n")
print("ports", len(ioa), "inputs", sum(1 for d in cj["port_decl"].values() if d[0] == "input"))
