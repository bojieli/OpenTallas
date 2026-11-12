"""SC-ECHAN check: ft bit-site overlaps (cell 1.404 x 0.27) and ft points under the u_core footprint, before/after."""
import json, sys, re, collections
def load(p): return json.load(open(p))
def rect(h):
    (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]; dx, dy = h.get("track_offset_um", [0, 0])
    return (ox + dx, oy + dy, ox + dx + w, oy + dy + hh)
def stats(t):
    pts = []
    for s in t.get("ft_slots") or []:
        for j, bs in enumerate(s.get("bit_sites_um") or []):
            for b in bs: pts.append((b[0], b[1], s["name"], j))
    cw, ch = 1.404, 0.27
    grid = collections.defaultdict(list)
    for i, (x, y, *_ ) in enumerate(pts): grid[(int(x // 2), int(y // 1))].append(i)
    ov = 0
    for i, (x, y, n, j) in enumerate(pts):
        gx, gy = int(x // 2), int(y // 1)
        for ax in (gx - 1, gx, gx + 1):
            for ay in (gy - 1, gy, gy + 1):
                for k in grid.get((ax, ay), []):
                    if k > i:
                        X, Y, N, J = pts[k]
                        if abs(X - x) < cw - 1e-6 and abs(Y - y) < ch - 1e-6: ov += 1
    r = rect(t["hard_cores"][0])
    under = sum(1 for x, y, *_ in pts if r[0] <= x <= r[2] and r[1] <= y <= r[3])
    regs = sum(1 for s in t.get("ft_slots") or [] for x, y in (s.get("regs_um") or [])[1:] if r[0] <= x <= r[2] and r[1] <= y <= r[3])
    return dict(bits=len(pts), overlaps=ov, bits_under_core=under, regs_under_core=regs,
                e_gap=round(t["outline_um"][0] - r[2], 2), w_gap=round(r[0], 2))
A, B = load(sys.argv[1]), load(sys.argv[2])
for tn in sorted(A["partition_types"]):
    if not re.match(r"^(sle|slw)_sc_", tn): continue
    print(tn, "before", stats(A["partition_types"][tn]), "after", stats(B["partition_types"][tn]))
