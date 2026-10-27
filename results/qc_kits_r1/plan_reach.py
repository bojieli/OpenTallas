"""Plan-level per-bit ft reach check (QC-KITS-R1): station0 = regs_um[0] (or in window), stations 1.. = bit_sites_um
per bit, last = out window pin (bit-ordered spread; also the window-extreme bound). Manhattan hop, reach 405."""
import json, sys
R = 405.0
def face_pt(face, W, H, c):
    return {"N": (c, H), "S": (c, 0.0), "E": (W, c), "W": (0.0, c)}[face]
def run(path, only=None):
    d = json.load(open(path)); out = {}
    for tn, t in sorted(d["partition_types"].items()):
        if only and tn not in only: continue
        W, H = t["outline_um"]; worst = (0, None)
        nfail = {}
        for s in t.get("ft_slots") or []:
            n = int(s["width"]); regs = s.get("regs_um") or []; bs = s.get("bit_sites_um") or []
            win_in = s.get("in_window_um"); win_out = s.get("out_window_um")
            for b in range(n):
                pts = []
                if win_in:
                    lo, hi = win_in; pts.append(face_pt(s["in_face"], W, H, lo + (b + .5) * (hi - lo) / n))
                elif regs: pts.append(tuple(regs[0]))
                for st in bs:
                    pts.append(tuple(st[b]) if b < len(st) else tuple(st[-1]))
                if win_out:
                    lo, hi = win_out; pts.append(face_pt(s["out_face"], W, H, lo + (b + .5) * (hi - lo) / n))
                elif len(regs) > len(bs) + 1: pts.append(tuple(regs[-1]))
                for i in range(len(pts) - 1):
                    h = abs(pts[i][0] - pts[i+1][0]) + abs(pts[i][1] - pts[i+1][1])
                    if h > R + 1e-6: nfail[s["name"]] = nfail.get(s["name"], 0) + 1
                    if h > worst[0]: worst = (h, (s["name"], b, i, pts[i], pts[i+1]))
        out[tn] = dict(max_hop=round(worst[0], 2), worst=worst[1], over_bits=nfail)
    return out
if __name__ == "__main__":
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 and sys.argv[2] else None
    r = run(sys.argv[1], only)
    for k, v in r.items():
        flag = "FAIL" if v["over_bits"] else "ok"
        print(f"{k:34s} {flag:4s} max {v['max_hop']:8.2f} over {v['over_bits']} worst {v['worst']}")
