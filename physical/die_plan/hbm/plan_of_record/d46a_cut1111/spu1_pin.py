import sys, json
SRC, PB, PN = sys.argv[1:4]
sys.path.insert(0, SRC); sys.path.insert(0, SRC + "/tools/die_plan")
from tools.die_plan import schema, partition_ft_reserve as F
PITCH = {"M5": .048, "M7": .064}
def cov(rs, L, x0, x1, y0, y1):
    """fraction of tracks (vertical layers M5/M7: x-extent) in [x0,x1] blocked anywhere in the y-strip [y0,y1]"""
    iv = sorted((max(x0, r[0]), min(x1, r[2])) for q in rs if q["layer"] == L for r in [q["rect"]]
                if r[0] < x1 and r[2] > x0 and r[1] < y1 and r[3] > y0)
    c = 0; s = e = None
    for a, b in iv:
        if s is None: s, e = a, b
        elif a > e: c += e - s; s, e = a, b
        else: e = max(e, b)
    if s is not None: c += e - s
    return c / (x1 - x0)
for tag, p in (("base", PB), ("new", PN)):
    P = schema.Plan(json.load(open(p)))
    for tn in ("q_spu1__physical_v1", "q_spu1"):
        t = P.types[tn]; w, h = t["outline_um"]
        r = F.reservation(P, tn)["rectangles_um"]
        out = []
        for s in t["ft_slots"]:
            for side, face, win in (("in", s["in_face"], s["in_window_um"]), ("out", s["out_face"], s["out_window_um"])):
                if face not in "NS": continue
                lo, hi = win; y0, y1 = (0, 20) if face == "S" else (h - 20, h)
                if hi < 276.48 or lo > 786.24: continue
                free = sum((1 - cov(r, L, lo, hi, y0, y1)) * (hi - lo) / PITCH[L] for L in PITCH)
                out.append(f"{s['name']}.{side}{face}[{lo:.0f},{hi:.0f}] bits {s['width']} free_tracks {free:.0f} M7blk {cov(r,'M7',lo,hi,y0,y1):.2f} M5blk {cov(r,'M5',lo,hi,y0,y1):.2f}")
        print(tag, tn); [print("   ", o) for o in out]
