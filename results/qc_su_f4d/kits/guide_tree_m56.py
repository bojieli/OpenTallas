#!/usr/bin/env python3
"""QC-SU-F4D tree-net-only guide rewrite, v2 (fixes two F4C defects found on the F4C trial, CHECKED):
  (1) F4C v1 kept every GRT box that touched a pin GCell on its original layer; GRT boxes are whole segments, so all 481
      tree M4 boxes touched a pin GCell and stayed on M4 -> DRT routed the feeds on M4 again;
  (2) DRT (ORFS detail_route.tcl) loads 5_1_grt.odb and uses the dbGuides stored in the ODB, not route.guide, so a
      file rewrite alone never reached DRT.  The flow must load the rewritten file with read_guides in
      PRE_DETAIL_ROUTE_TCL (see pre_drt_guides.tcl); a probe showed read_guides replaces the tree-net ODB guides and
      leaves all other nets' guides unchanged.
Rule (only nets named ot_ms_*_n, the plan tree nets): every M2-M5 box -> horizontal M6 / vertical M5 / single GCell
M5+M6; every pin GCell (the net's M1 boxes) gets the via stack M1..M6 at that GCell only.  Every other net is copied
byte-identical; assert 0 non-tree nets carry an M6 guide.
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
istree = lambda n: n.startswith("ot_ms_") and n.endswith("_n")
ntree = nbox_in = nbox_out = 0
lay_out = {}
out = []
for n in order:
    bx = nets[n]
    if istree(n):
        ntree += 1; nbox_in += len(bx)
        new = set()
        for b in bx:
            if b[4] == "M1":
                for l in L:
                    new.add(b[:4] + (l,))
            elif b[4] in ("M2", "M3", "M4", "M5", "M6"):
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
        for b in bx:
            lay_out[b[4]] = lay_out.get(b[4], 0) + 1
    out.append(n + "\n(\n" + "".join("%d %d %d %d %s\n" % b for b in bx) + ")\n")
open(dst, "w").write("".join(out))
other_m6 = sum(1 for n in order if not istree(n) and any(b[4] == "M6" for b in nets[n]))
r = dict(version=2, nets=len(order), tree_nets=ntree, tree_boxes_in=nbox_in, tree_boxes_out=nbox_out,
         tree_boxes_by_layer=lay_out, non_tree_nets_with_M6=other_m6)
json.dump(r, open(rep, "w"), indent=1); print("GUIDE_M56", r)
assert other_m6 == 0, "a non-tree net carries an M6 guide from GRT"
