#!/usr/bin/env python3
"""HBM-PLAN-1 11-09 pilot (COORD 04:1x, q_b010 only): alternating-polarity station chains.

ASAP7 has only QN-output flops (DFFHQNx1), so every `q <= d` station costs DFFHQN + a restoring INV per bit.  In a chain of
ot_dp_st stations where each station's data input is exactly the previous station's data output (and that wire has no
other reader), the data may travel inverted between stations: ot_dp_stn stores d in q and drives port qn = ~q, i.e. the QN pin
itself (no INV); two stn in a row restore polarity.  A chain of k stations becomes stn x (k - k%2) + one plain st when k
is odd, so every chain output keeps its polarity and depth: same cycles, same epoch bit (eq stays true polarity), only
the polarity of INTERNAL chain wires changes.  Nothing else in the file is touched.

usage: qn_alternate.py IN.sv OUT.sv REPORT.json"""
import json, re, sys
from collections import defaultdict

INST = re.compile(r"^(\s*)ot_dp_st #\(\.W\((\d+)\)\) (\w+) \(\.clk\(clk\), \.rst_n\(rst_n\), \.d\((.+?)\), \.ea\((.+?)\), "
                  r"\.q\((.+?)\), \.eq\((.+?)\)\);(.*)$")
STN = """
// HBM-PLAN-1 11-09 pilot: QN-polarity station (qn = ~stored d); used only in pairs inside one chain, see qn_alternate.py.
// Same kept hierarchy and register names as ot_dp_st (inst/q[b], inst/eq) so the place-stage station scripts
// (istations / face_flops / ft_polarity_local) find it unchanged; the output port is qn, driven by the QN pin.
(* keep_hierarchy, keep *)
module ot_dp_stn #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    input  wire         ea,
    output wire [W-1:0] qn,
    output reg          eq
);
    reg [W-1:0] q;
    always @(posedge clk) q <= d;
    assign qn = ~q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
"""

def base(expr):
    m = re.fullmatch(r"(\w+)(\[[^\]]+\])?", expr.strip())
    return m.group(1) if m else None

def main(src, dst, rep):
    lines = open(src).read().split("\n")
    insts = {}
    for i, ln in enumerate(lines):
        m = INST.match(ln)
        if m:
            insts[i] = dict(line=i, W=int(m.group(2)), name=m.group(3), d=m.group(4), ea=m.group(5), q=m.group(6), eq=m.group(7))
    text = "\n".join(lines)
    # readers of each wire base: count word occurrences (declaration + driver + readers)
    occ = defaultdict(int)
    for w in re.findall(r"\b[A-Za-z_]\w*\b", text):
        occ[w] += 1
    by_d = defaultdict(list)
    for i, s in insts.items():
        by_d[s["d"].strip()].append(i)
    nxt, prv = {}, {}
    for i, s in insts.items():
        cand = by_d.get(s["q"].strip(), [])
        b = base(s["q"])
        if len(cand) != 1 or b is None:
            continue
        j = cand[0]
        # q wire must be read only by the next station's d (and, when the epoch shares the vector, its ea)
        shared = base(s["eq"]) == b
        expected = 2 + (1 if True else 0)          # declaration + this q + next d
        expected = 3 + (2 if shared else 0)        # + this eq + next ea when one vector carries both
        decl = len(re.findall(rf"^\s*(?:wire|logic)\b[^;]*\b{re.escape(b)}\b", text, re.M))
        if decl != 1 or occ[b] != expected:
            continue
        if shared and insts[j]["ea"].strip() != s["eq"].strip():
            continue
        nxt[i], prv[j] = j, i
    chains = []
    for i in insts:
        if i in prv:
            continue
        c = [i]
        while c[-1] in nxt:
            c.append(nxt[c[-1]])
        chains.append(c)
    conv = set()
    for c in chains:
        k = len(c)
        conv.update(c[: k - k % 2])
    for i in conv:
        lines[i] = lines[i].replace("ot_dp_st #(", "ot_dp_stn #(", 1).replace(" .q(", " .qn(", 1)
        assert " .qn(" in lines[i], lines[i]
    out = "\n".join(lines)
    if "endmodule" in out:
        out = out.rstrip("\n") + "\n" + STN
    open(dst, "w").write(out)
    hist = defaultdict(int)
    for c in chains:
        hist[len(c)] += 1
    bits = sum(insts[i]["W"] for i in conv)
    json.dump(dict(stations=len(insts), chains=len(chains), chain_len_hist=dict(sorted(hist.items())),
                   converted=len(conv), converted_bits=bits,
                   kept_plain=len(insts) - len(conv),
                   chains_detail=[[insts[i]["name"] for i in c] for c in chains if len(c) > 1][:5000]),
              open(rep, "w"), indent=1)
    print(json.dumps(dict(stations=len(insts), chains=len(chains), converted=len(conv), converted_bits=bits,
                          hist=dict(sorted(hist.items())))))

if __name__ == "__main__":
    main(*sys.argv[1:4])
