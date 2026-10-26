#!/usr/bin/env python3
"""TR3-KV-LEC 2026-10-25: gate side of the master-vs-old-variant kit LEC (OWNER option B: LEC each strap master against
every old constant variant it replaces).

    python3 tie_strap.py MASTER_NETLIST.v OUT.v --variant N --bsel XX

MASTER_NETLIST = the synthesised odd head strap master (kv3_head_eighth_e1 or _e5, 1_2_yosys.v of its kit).  OUT = the
same netlist with the ID strap tied exactly as the parent ties it for variant eN (strap_bsel := 2'bXX, an assign of a
constant to the former input net; no other logic change) and alpha-renamed to the variant's names:
  * top module kv3_head_eighth_e<M> -> kv3_head_eighth_e<N>
  * lane prefixes g_t_<a>_ -> g_t_<b>_ for the master's two lanes (e1: 2/3, e3: 6/7, e5: 10/11, e7: 14/15) in EVERY
    identifier (ports, nets, instance names): a consistent renaming of a netlist is the same circuit, and it lets lec.py
    match ports and registers by name exactly as the plan's core_conns lane-prefix map does.
Fails closed if a target name already exists in the master netlist (no collision) or the strap declaration is missing.
lec.py then proves OUT (gate) == old variant eN kit RTL (gold).
"""
import argparse
import re
from pathlib import Path

LANES = {1: (2, 3), 3: (6, 7), 5: (10, 11), 7: (14, 15)}
MASTER = {1: 1, 3: 1, 5: 5, 7: 5}

ap = argparse.ArgumentParser()
ap.add_argument("netlist")
ap.add_argument("out")
ap.add_argument("--variant", type=int, required=True)
ap.add_argument("--bsel", required=True)
a = ap.parse_args()
assert re.fullmatch(r"[01]{2}", a.bsel)
n, m = a.variant, MASTER[a.variant]
t = Path(a.netlist).read_text()
top = f"kv3_head_eighth_e{m}"
mt = re.search(rf"^module {top}\s*\((.*?)\);", t, re.M | re.S)
assert mt, "master top module not found"
end = t.index("endmodule", mt.end())
body = t[mt.start():end]
# 1. strap_bsel: drop from the port list, input -> constant-driven wire
hdr = mt.group(0)
hdr2, k = re.subn(r"\s*\bstrap_bsel\s*,|,\s*\bstrap_bsel\b(?=\s*\))", "", hdr, count=1)
assert k == 1, "strap_bsel not in the port list"
body = body.replace(hdr, hdr2, 1)
body, k = re.subn(r"^\s*input\s+\[1:0\]\s+strap_bsel\s*;\n", "", body, count=1, flags=re.M)
assert k == 1, "input [1:0] strap_bsel; declaration not found"
if re.search(r"^\s*wire\s+\[1:0\]\s+strap_bsel\s*;", body, re.M):   # yosys writes input + wire declarations
    body, k = re.subn(r"^(\s*)(wire\s+\[1:0\]\s+strap_bsel\s*;)", rf"\1\2\n\1assign strap_bsel = 2'b{a.bsel};",
                      body, count=1, flags=re.M)
else:
    body, k = re.subn(r"^(module [^;]*;\n)", rf"\1  wire [1:0] strap_bsel;\n  assign strap_bsel = 2'b{a.bsel};\n", body,
                      count=1, flags=re.S)
assert k == 1, "could not tie strap_bsel"
t = t[:mt.start()] + body + t[end:]
# 2. rename top module and lane prefixes (variant names)
if n != m:
    (a0, a1), (b0, b1) = LANES[m], LANES[n]
    for b in (b0, b1):
        assert not re.search(rf"g_t_{b}_", t), f"collision: g_t_{b}_ already in the master netlist"
    assert not re.search(rf"\bkv3_head_eighth_e{n}\b", t)
    t = re.sub(r"g_t_(\d+)_", lambda x: {a0: f"g_t_{b0}_", a1: f"g_t_{b1}_"}.get(int(x.group(1)), x.group(0)), t)
    t = re.sub(rf"^module {top}\b", f"module kv3_head_eighth_e{n}", t, count=1, flags=re.M)
Path(a.out).write_text(t)
print(f"tied strap_bsel=2'b{a.bsel}, master e{m} -> variant e{n} names: {a.out}")
