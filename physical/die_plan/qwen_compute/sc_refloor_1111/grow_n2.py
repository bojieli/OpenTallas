"""SC-REFLOOR-1 v1 fallback (N-face outline growth, face-aware): outline H += DY at the N face of matching types.
Moves up DY: landing bands of N-face ft slots / N-face buses; regs/bit sites at y >= YCUT of ft slots that enter or
leave through N; clock taps / straps / relays / reset points at y >= YCUT.  E/W face windows, E/W slot geometry,
core and everything below YCUT stay (die abutment with fw/stm/fe unchanged; ctl row moves up DY at die level).
usage: grow_n2.py IN OUT DY TYPE_RE [YCUT]"""
import json, re, sys
P = json.load(open(sys.argv[1])); DY = float(sys.argv[3]); RX = re.compile(sys.argv[4])
YCUT = float(sys.argv[5]) if len(sys.argv) > 5 else 1225.0
def pts(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("outline_um", "window_um", "out_window_um", "in_window_um", "width", "bit_site_cell_um", "rect_um"):
                continue
            pts(v)
    elif isinstance(o, list):
        if len(o) == 2 and all(isinstance(x, (int, float)) for x in o):
            if o[1] >= YCUT - 1e-6:
                o[1] += DY
        else:
            for v in o: pts(v)
n = 0; rep = []
for tn, t in P["partition_types"].items():
    if not RX.search(tn): continue
    n += 1
    t["outline_um"][1] += DY
    nface = {s["name"] for s in t["ft_slots"] if "N" in (s["in_face"], s["out_face"])}
    nbands = {s["name"] + "_i" for s in t["ft_slots"] if s["in_face"] == "N"} | \
             {s["name"] + "_o" for s in t["ft_slots"] if s["out_face"] == "N"} | \
             {b["name"] for b in t["buses"] if b["face"] == "N"} | {b["name"] + "_i" for b in t["buses"] if b["face"] == "N"}
    for bn, bd in t["clock"]["landing_contract"]["bands"].items():
        r = bd.get("rect_um")
        if r and bn in nbands:
            r[1] += DY; r[3] += DY; rep.append((tn, bn))
    for s in t["ft_slots"]:
        if s["name"] in nface:
            for key in ("regs_um", "bit_sites_um"):
                if s.get(key): pts(s[key])
    for k, v in t.items():
        if k in ("outline_um", "buses", "ft_slots"): continue
        if k == "clock":
            pts({kk: vv for kk, vv in v.items() if kk != "landing_contract"})
        else:
            pts(v)
# die level: partitions of the grown types grow up; every partition whose origin y >= the top of a grown instance and
# that overlaps it in x moves up DY (column above the slice), so ctl / st / hc rows keep abutting the grown sc
print("grown", n, "types by", DY, "bands moved", len(rep))
json.dump(P, open(sys.argv[2], "w"))
