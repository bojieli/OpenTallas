"""DIE-HBM-10: capacity of corridor-free idx piece homes per partition type (C21 G0C: 41 street_die_leg + 19 geometry
errors = idx Q2 pieces placed over ft lane stations).  Blocked = C21 hard cores/contents EXCEPT the Q2 pieces, plus every
ft slot station box (bbox of its bit sites + its regs_um point, + HALO).  usage: idx_cap.py PLAN TYPE..."""
import json, sys
import numpy as np
EXACT = True   # block the actual bit cells + station reg points (what check.py geometry / street_die_leg test), not bboxes
P = json.load(open(sys.argv[1])); T = P["partition_types"]
W, H = 218.592, 187.488; HALO = 8.64; G = 8.64
def boxes(t, drop_q2=True):
    occ = []
    for h in t.get("hard_cores", []):
        if drop_q2 and h["inst"].startswith("u_hb_idx__s_Q2"): continue
        o, s = h["origin_um"], h["outline_um"]; occ.append((o[0], o[1], o[0] + s[0], o[1] + s[1]))
    for c in t.get("contents", []):
        if c.get("origin_um") and c.get("outline_um"):
            o, s = c["origin_um"], c["outline_um"]; occ.append((o[0], o[1], o[0] + s[0], o[1] + s[1]))
    st = []
    for s in t.get("ft_slots", []):
        cw, ch = s.get("bit_site_cell_um", (1.404, .27))
        for j, sites in enumerate(s.get("bit_sites_um") or []):
            if not sites: continue
            xs = [x for x, y in sites]; ys = [y for x, y in sites]
            st.append((min(xs), min(ys), max(xs) + cw, max(ys) + ch))
        for r in s.get("regs_um") or []:
            st.append((r[0] - 10, r[1] - 10, r[0] + 10, r[1] + 10))
    return occ, st
for tn in sys.argv[2:]:
    t = T[tn]; Wt, Ht = t["outline_um"]; occ, st = boxes(t)
    q2 = sum(1 for h in t.get("hard_cores", []) if h["inst"].startswith("u_hb_idx__s_Q2"))
    hit0 = lambda r, bs, hl: any(r[0] < o[2] + hl and o[0] < r[2] + hl and r[1] < o[3] + hl and o[1] < r[3] + hl for o in bs)
    R = 2.16; M = np.zeros((int(Wt / R) + 2, int(Ht / R) + 2), bool)
    for s in t.get("ft_slots", []):
        cw, ch = s.get("bit_site_cell_um", (1.404, .27))
        for sites in s.get("bit_sites_um") or []:
            for x, y in sites: M[int(x / R):int((x + cw) / R) + 1, int(y / R):int((y + ch) / R) + 1] = True
        for r in s.get("regs_um") or []: M[max(0, int((r[0] - 2) / R)):int((r[0] + 2) / R) + 1, max(0, int((r[1] - 2) / R)):int((r[1] + 2) / R) + 1] = True
    C = M.cumsum(0).cumsum(1)
    def mhit(r):
        a, b, c, d = int(r[0] / R), int(r[1] / R), int(r[2] / R) + 1, int(r[3] / R) + 1
        return (C[c, d] - C[a - 1, d] - C[c, b - 1] + C[a - 1, b - 1]) > 0
    def hit(r, bs, hl):
        if bs is st: return mhit(r)
        return hit0(r, bs, hl)
    placed = []
    y = 17.28
    while y + H <= Ht - 17.28:
        x = 17.28
        while x + W <= Wt - 17.28:
            r = (x, y, x + W, y + H)
            if not hit(r, occ + placed, HALO) and not hit(r, st, HALO):
                placed.append(r); x += W + HALO; continue
            x += G
        y += G
    # area of station boxes
    sa = sum((b[2] - b[0]) * (b[3] - b[1]) for b in st)
    print(tn, dict(outline=[Wt, Ht], q2_in_c21=q2, corridor_free_slots=len(placed), station_boxes=len(st),
                   station_box_area_mm2=round(sa / 1e6, 3), other_hard=len(occ)))
