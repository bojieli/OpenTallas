#!/usr/bin/env python3
"""QC-SU-F4C GUIDE REWRITE LIMITED TO THE TREE NETS (COORD RULING QC-SU-F4B (2); DRT-0155 lesson: a clock layer range
alone also gave M6 guides to signal nets).  GRT runs unchanged (signal M2-M5, clock M4-M5); then ONLY nets named
ot_ms_*_n (plan tree nets: root / island / B / repeater / leaf-driver feeds) are rewritten:
  * a guide box that touches a pin GCell of the net (any M1 box of the net) is kept and gets M2..M6 copies (pin stack);
  * any other box on M2-M5: horizontal -> M6, vertical -> M5, single GCell (bend) -> M5 + M6.
Every other net's guides are copied byte-identical (so no signal net can see M6).  DRT then runs with top layer M6;
the post-DRT census must show tree nets on M5/M6 (+ pin stacks) and 0 non-tree nets on M6.
usage: guide_tree_m56.py IN.guide OUT.guide REPORT.json"""
import json, sys
src, dst, rep = sys.argv[1:4]
L = ["M1", "M2", "M3", "M4", "M5", "M6"]
nets, order, cur, buf = {}, [], None, None
for line in open(src):
    s = line.strip()
    if not s:
        continue
    if s == "(":
        buf = []
    elif s == ")":
        nets[cur] = buf; order.append(cur); buf = None
    elif buf is None:
        cur = s
    else:
        f = s.split(); buf.append((int(f[0]), int(f[1]), int(f[2]), int(f[3]), f[4]))
ntree = nbox_in = nbox_out = 0
out = []
for n in order:
    bx = nets[n]
    if n.startswith("ot_ms_") and n.endswith("_n"):
        ntree += 1; nbox_in += len(bx)
        pins = [b for b in bx if b[4] == "M1"]
        hit = lambda b: any(b[0] < p[2] and b[2] > p[0] and b[1] < p[3] and b[3] > p[1] for p in pins)
        new = set()
        for b in bx:
            if b[4] == "M1":
                new.add(b); [new.add(b[:4] + (l,)) for l in L[1:]]
            elif hit(b):
                new.add(b); new.add(b[:4] + ("M5",)); new.add(b[:4] + ("M6",))
            elif b[4] in ("M2", "M3", "M4", "M5"):
                w, h = b[2] - b[0], b[3] - b[1]
                if w > h:
                    new.add(b[:4] + ("M6",))
                elif h > w:
                    new.add(b[:4] + ("M5",))
                else:
                    new.add(b[:4] + ("M5",)); new.add(b[:4] + ("M6",))
            else:
                new.add(b)
        bx = sorted(new, key=lambda b: (L.index(b[4]) if b[4] in L else 9, b))
        nbox_out += len(bx)
    out.append(n + "\n(\n" + "".join("%d %d %d %d %s\n" % b for b in bx) + ")\n")
open(dst, "w").write("".join(out))
other_m6 = sum(1 for n in order if not (n.startswith("ot_ms_") and n.endswith("_n")) and any(b[4] == "M6" for b in nets[n]))
r = dict(nets=len(order), tree_nets=ntree, tree_boxes_in=nbox_in, tree_boxes_out=nbox_out, non_tree_nets_with_M6=other_m6)
json.dump(r, open(rep, "w"), indent=1); print("GUIDE_M56", r)
assert other_m6 == 0, "a non-tree net carries an M6 guide from GRT"
