#!/usr/bin/env python3
"""DIE-HBM-53: hand wrapper for a plan single-clock pin table over a multi-clock RTL cut (recipe rename_top).
 mkclkwrap.py RECIPE.json PINS.json WORKDIR OUT.sv   (run from the repo root; the RTL top is renamed rename_top)"""
import sys, json
sys.path.insert(0, "physical/die_plan/hbm_arch_cores")
import gen_core_kit_hbm as G
from kit_contract import _kit_pins
rec, pins, wd, out = json.load(open(sys.argv[1])), _kit_pins(json.load(open(sys.argv[2]))), sys.argv[3], sys.argv[4]
module, nt = rec["top"], rec["rename_top"]
ports = G.yosys_ports(rec["files"], module, rec.get("params", {}), rec.get("defines", []), wd)
pb = G.buses_of([p["name"] for p in pins])
pn = {n for n, _, _ in ports}
W = {n: w for n, d, w in ports}
clocks = [n for n, d, w in ports if n not in pb]
assert clocks and all(("clk" in n or n.endswith("_ck")) and d == "input" for n, d, w in ports if n in clocks), clocks
bad = [n for n, d, w in ports if n in pb and pb[n][0] != w] + [b for b in pb if b != "clk" and b not in pn]
assert not bad and "clk" in pb and "clk" not in pn, bad
rng = lambda n, w: "" if (w == 1 and pb[n][1]) else "[%d:0] " % (w - 1)
decl = ["    input wire clk"] + ["    %s wire %s%s" % (d, rng(n, w), n) for n, d, w in ports if n in pb]
conn = ["        .%s(%s)" % (n, "clk" if W[n] == 1 else "{%d{clk}}" % W[n]) for n in clocks] + \
       ["        .%s(%s)" % (n, n) for n, d, w in ports if n in pb]
txt = ["// DIE-HBM-53 10-31 hand wrapper (recipe rename_top = %s): the plan pin table has ONE clock pin clk (plan centre" % nt,
       "// clock entry); the RTL cut has %d clock ports (%d bits: %s), all driven by clk." % (
           len(clocks), sum(W[n] for n in clocks), ", ".join(clocks)),
       "// Every other plan bus = the RTL port of the same name and width (checked by mkclkwrap.py and at generation). Pure wiring.",
       "`default_nettype none", "module %s (" % module, ",\n".join(decl), ");",
       "    %s u_core (" % nt, ",\n".join(conn), "    );", "endmodule", "`default_nettype wire", ""]
open(out, "w").write("\n".join(txt))
print(module, len(clocks), "clock ports ->clk;", len(pb), "plan buses")
