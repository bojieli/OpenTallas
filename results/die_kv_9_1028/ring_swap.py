#!/usr/bin/env python3
"""DIE-KV-9 10-28 (COORD 07:05 (d)): die-local kit-RTL transform for the cell-count check (step 3).
Every ot_dp_clk_landing_cas #(.W(W), .DEPTH(D)) instance with W >= 1000 becomes the ring hard-core type
kv_ring_w<W>d<D> (rtl/qwen_sys/kv_ring_cores_1028, same ports, verbatim ring inside).  Instances with other
parameters stay soft.  usage: ring_swap.py BOUND.sv OUT.sv STUB.sv   -> json {class: count}"""
import json, re, sys
CLASSES = {(1045, 4), (1057, 4), (1057, 8), (1063, 4), (1063, 8), (1119, 4), (1119, 8), (1560, 4)}
PAT = re.compile(r"ot_dp_clk_landing_cas\s*#\(\s*\.W\((\d+)\),\s*\.DEPTH\((\d+)\)\s*\)(\s+\w+\s*\()")
src, out, stub = sys.argv[1:4]
n, other = {}, []
def sub(m):
    w, d = int(m.group(1)), int(m.group(2))
    if w < 1000:
        return m.group(0)
    if (w, d) not in CLASSES:
        raise SystemExit(f"ring_swap: W>=1000 ring ({w},{d}) outside the 8 hard-core classes")
    k = f"kv_ring_w{w}d{d}"; n[k] = n.get(k, 0) + 1
    return k + m.group(3)
txt = PAT.sub(sub, open(src).read())
open(out, "w").write(txt)
with open(stub, "w") as fh:
    for w, d in sorted(CLASSES):
        kw = {4: 6, 8: 7}[d]
        fh.write(f"(* blackbox *) module kv_ring_w{w}d{d} (input wire fclk, t_rst_n, clk, rst_n, input wire [{kw-1}:0] strap_k,"
                 f" input wire [{w-1}:0] d, output wire [{w-1}:0] q, output wire ready, fault); endmodule\n")
print(json.dumps(n))
