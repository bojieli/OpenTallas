#!/usr/bin/env python3
"""QTILE-R 10-23: HP13 cpub39 physical top + face pin registers (one keep flop per bit on every port whose bits are not
flop-direct in the synthesized netlist).  Text transform of the flat physical-ABI netlist: the module is renamed
<top>_pr, each registered input port P is captured into P__pr (posedge of its entry-domain clock) and every `assign ... = P;`
reads P__pr; each registered output port O is driven by O__pq <= (the original assign RHS).  No other line changes, so
every instance name (macros, soft roots, reset leaves) is byte-identical.  +1 cycle per registered port (static schedule).
usage: hp13_pinreg_top.py IN.sv OUT.sv --top TOP --spec spec.json --ports p1,p2,...  (clock per port from
spec clock_entry_domains)"""
import argparse, json, re, sys
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--top", required=True)
ap.add_argument("--spec", required=True); ap.add_argument("--ports", required=True); ap.add_argument("--suffix", default="_pr")
a = ap.parse_args()
spec = json.load(open(a.spec))
dom = {}
for d in spec["clock_entry_domains"].values():
    ck = d["ports"][0].split("[")[0]
    for p in d["inputs"] + d["outputs"]: dom[p] = ck
ports = [p for p in a.ports.split(",") if p]
txt = open(a.src).read()
m = re.search(r"^module " + re.escape(a.top) + r"\(", txt, re.M)
if not m: sys.exit("top not found")
end = txt.index("\nendmodule", m.start())
head, body, tail = txt[:m.start()], txt[m.start():end], txt[end:]
decl = {}
for d, hi, lo, n in re.findall(r"^(input|output) wire \[(\d+):(\d+)\] (\w+);", body, re.M):
    decl[n] = (d, int(hi), int(lo))
add, table = [], []
lines = body.split("\n")
for p in ports:
    if p not in decl: sys.exit(f"port {p} not declared")
    d, hi, lo = decl[p]; ck = dom[p]; w = f"[{hi}:{lo}]"
    hits = 0
    if d == "input":
        rx = re.compile(r"^(assign .*=\s*)" + re.escape(p) + r"(\s*(\[[^\]]*\])?\s*;)$")
        for i, l in enumerate(lines):
            mm = rx.match(l)
            if mm: lines[i] = mm.group(1) + p + "__pr" + mm.group(2); hits += 1
        add.append(f"(* keep = 1 *) reg {w} {p}__pr;\nalways @(posedge {ck}) {p}__pr <= {p};")
    else:
        rx = re.compile(r"^assign " + re.escape(p) + r"(\s*(\[[^\]]*\])?\s*=)")
        for i, l in enumerate(lines):
            mm = rx.match(l)
            if mm: lines[i] = "assign " + p + "__pd" + l[len("assign " + p):]; hits += 1
        add.append(f"wire {w} {p}__pd;\n(* keep = 1 *) reg {w} {p}__pq;\nalways @(posedge {ck}) {p}__pq <= {p}__pd;\nassign {p} = {p}__pq;")
    if hits == 0: sys.exit(f"port {p}: no assign site")
    table.append((p, d, hi - lo + 1, ck, 1))
last = max(i for i, l in enumerate(lines) if re.match(r"^(input|output) wire ", l))
lines[last + 1:last + 1] = ["// QTILE-R face pin registers (+1 cycle per port below)"] + add
body = "\n".join(lines)
body = body.replace(f"module {a.top}(", f"module {a.top}{a.suffix}(", 1)
open(a.out, "w").write(head + body + tail)
json.dump({"schema": "opentallas.qtile_r.pin_regs.v1", "top": a.top + a.suffix, "base_top": a.top,
           "ports": [{"port": p, "dir": d, "width": w, "clock": c, "added_cycles": n} for p, d, w, c, n in table],
           "bits_in": sum(w for p, d, w, c, n in table if d == "input"),
           "bits_out": sum(w for p, d, w, c, n in table if d == "output")}, open(a.out + ".pin_regs.json", "w"), indent=1)
print("ok", len(table), "ports")
