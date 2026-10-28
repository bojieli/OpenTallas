"""DIE-KV-3/STATIONS / KV plan event D9c on hm_r26q9b (COORD 21:38: station probe/re-site, no FT move).
Chain re-site: every FT slot of hub_Wi that still has a station < CLR_ST (10.8 um, 1 gcell) from a hard core (the D9b
STUCK slit stations), and every FT slot of hub_Wi / hub_C / hub_Wo / hgi_WN_7 with a hop over its limit, gets ALL its
internal stations re-sited together by a DP on a 10.8-um grid (one station per stage, static schedule kept: station
count unchanged): entry face register (regs_um[0]) and exit face window fixed, every hop <= max(395, old hop + 0.5) um
(Manhattan, register to register, = D9b REACH_ST; G0C gate 405), each station keeps its bit-block shape, is >= CLR from
every hard core (10.8 hub_Wi, 0.3 neighbours = D9b) and overlaps no other station; cost = sum of station displacement.
Bits shift rigidly (dx multiple of 2.16, dy of 0.27 = the bit-site cell pitch).
usage: d9c_event.py RUNTIME_ROOT IN.json OUT.json LEDGER.json [--parts hub_Wi,hub_C,...]"""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy.ndimage import minimum_filter
R = Path(sys.argv[1]); inp, outp, ledp = sys.argv[2:5]
sys.path.insert(0, str(R / "tools/die_plan")); sys.path.insert(0, str(R))
import schema as S
raw = json.load(open(inp)); P = S.Plan(raw, Path(inp))
HUB = "hub_Wi"; NB = ["hub_C", "hub_Wo", "hgi_WN_7"]
PARTS = sys.argv[sys.argv.index("--parts") + 1].split(",") if "--parts" in sys.argv else [HUB] + NB
REACH_ST, CLR_ST, G, HOP_MAX = 395.0, 10.8, 10.8, 404.0
LED = dict(resited=[], failed=[], untouched_bad=[])

def frame(part):
    o = P.to_die(part, (0.0, 0.0)); ex = P.to_die(part, (1.0, 0.0)); ey = P.to_die(part, (0.0, 1.0))
    A = [[ex[0] - o[0], ey[0] - o[0]], [ex[1] - o[1], ey[1] - o[1]]]; det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    def to_type(p):
        dx, dy = p[0] - o[0], p[1] - o[1]
        return ((A[1][1] * dx - A[0][1] * dy) / det, (-A[1][0] * dx + A[0][0] * dy) / det)
    return to_type
def face_mean(part, pid, side):
    pr = P.ports[pid]; face = pr["face"] if side == "src" else S.OPP[pr["face"]]; x0, y0, x1, y1 = P.rect(part)
    pts = [((x0 if face == "W" else x1), c) if face in "EW" else (c, (y0 if face == "S" else y1)) for _, _, c in P.port_pins(pid)]
    tt = frame(part); tp = [tt(p) for p in pts]
    return [sum(p[0] for p in tp) / len(tp), sum(p[1] for p in tp) / len(tp)]
port_by_src = {(pr["src"]["part"], pr["src"]["bus"]): q for q, pr in P.ports.items()}
def bbox(st, cw, ch): return (min(p[0] for p in st), min(p[1] for p in st), max(p[0] for p in st) + cw, max(p[1] for p in st) + ch)
def man(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])

for part in PARTS:
    tn = P.parts[part]["type"]; ty = raw["partition_types"][tn]; W, H = ty["outline_um"]
    cores = [tuple(bx) for bx in S.placed_macro_boxes(P.ptype(part)).values()]
    clr = CLR_ST if part == HUB else 0.3
    nx, ny = int(W // G) + 1, int(H // G) + 1
    XS = np.arange(nx) * G; YS = np.arange(ny) * G
    allb = {}
    for s in ty.get("ft_slots", []):
        cw, ch = s.get("bit_site_cell_um", [0.0, 0.0])
        for j, st in enumerate(s.get("bit_sites_um", [])):
            if st: allb[(s["name"], j)] = bbox(st, cw, ch)
    def near_core(b):
        return any(b[0] < c[2] + clr and b[2] > c[0] - clr and b[1] < c[3] + clr and b[3] > c[1] - clr for c in cores)
    def hits_other(b, me):
        return any(k[0] != me and b[0] < o[2] and b[2] > o[0] and b[1] < o[3] and b[3] > o[1] for k, o in allb.items())
    def free_mask(off, me):
        """cells where a station with bbox offset off=(l,b,r,t) relative to its centre is legal"""
        m = np.ones((nx, ny), bool)
        X = XS[:, None]; Y = YS[None, :]
        m &= (X + off[0] > 1) & (X + off[2] < W - 1) & (Y + off[1] > 1) & (Y + off[3] < H - 1)
        e = clr + 1.2   # +1.2 um: snap allowance (dx <= 1.08, dy <= 0.135)
        obs = [(c[0] - e, c[1] - e, c[2] + e, c[3] + e) for c in cores]
        obs += [(o[0] - 1.2, o[1] - 1.2, o[2] + 1.2, o[3] + 1.2) for k, o in allb.items() if k[0] != me]
        for a0, b0, a1, b1 in obs:
            # station box [X+off0, X+off2] overlaps [a0, a1]  <=>  X in (a0-off2, a1-off0)
            ix = (XS > a0 - off[2]) & (XS < a1 - off[0]); iy = (YS > b0 - off[3]) & (YS < b1 - off[1])
            m[np.ix_(ix, iy)] = False
        return m
    for s in ty.get("ft_slots", []):
        cw, ch = s.get("bit_site_cell_um", [0.0, 0.0]); regs = s.get("regs_um"); bs = s.get("bit_sites_um", [])
        if not regs or not bs or len(regs) != len(bs) + 1 or any(not st for st in bs): continue
        pout = port_by_src.get((part, s["name"] + "_o")); exitp = face_mean(part, pout, "src") if pout else None
        chain = list(regs) + ([exitp] if exitp else [])
        hops = [man(a, b) for a, b in zip(chain, chain[1:])]
        lim = [REACH_ST if h <= REACH_ST else min(h + 0.5, HOP_MAX) for h in hops]   # never worsen a hop; G0C hop gate 405
        boxes = [bbox(st, cw, ch) for st in bs]
        def facest(b): return b[0] < 0.5 or b[2] > W - 0.5 or b[1] < 0.5 or b[3] > H - 0.5
        slit = [part == HUB and not facest(b) and near_core(b) for b in boxes]
        reach_bad = [h > l + 1e-6 for h, l in zip(hops, lim)]
        if not any(slit) and not any(reach_bad): continue
        if any(facest(b) for b in boxes):
            LED["untouched_bad"].append(dict(part=part, slot=s["name"], why="face station in chain")); continue
        k = len(bs); cen = [regs[j + 1] for j in range(k)]
        offs = [(b[0] - c[0], b[1] - c[1], b[2] - c[0], b[3] - c[1]) for b, c in zip(boxes, cen)]
        INF = 1e18
        masks = [free_mask(offs[j], s["name"]) for j in range(k)]
        disp = [np.abs(XS[:, None] - cen[j][0]) + np.abs(YS[None, :] - cen[j][1]) for j in range(k)]
        def ball(L):
            r = int(L // G); ii = np.arange(-r, r + 1)
            return (np.abs(ii)[:, None] + np.abs(ii)[None, :]) * G <= L + 1e-9
        D2 = lambda p: np.abs(XS[:, None] - p[0]) + np.abs(YS[None, :] - p[1])
        V = []
        v = np.where(masks[0] & (D2(regs[0]) <= lim[0] - 1.5), disp[0], INF); V.append(v)
        for j in range(1, k):
            fp = ball(lim[j] - 1.5); prev = minimum_filter(V[-1], footprint=fp, mode="constant", cval=INF)
            V.append(np.where(masks[j] & (prev < INF), prev + disp[j], INF))
        last = V[-1].copy()
        if exitp is not None: last[D2(exitp) > lim[k] - 1.5] = INF
        if last.min() >= INF:
            LED["failed"].append(dict(part=part, slot=s["name"], stations=k, slit=[j for j in range(k) if slit[j]], reach_bad=[j for j, r in enumerate(reach_bad) if r]))
            print("FAIL", part, s["name"]); continue
        pick = [None] * k; i = np.unravel_index(np.argmin(last), last.shape); pick[k - 1] = i
        for j in range(k - 2, -1, -1):
            q = (XS[pick[j + 1][0]], YS[pick[j + 1][1]])
            vv = np.where(D2(q) <= lim[j + 1] - 1.5, V[j], INF); pick[j] = np.unravel_index(np.argmin(vv), vv.shape)
        sh = []
        for j in range(k):
            tx, ty_ = XS[pick[j][0]], YS[pick[j][1]]
            sh.append([round((tx - cen[j][0]) / 2.16) * 2.16, round((ty_ - cen[j][1]) / 0.27) * 0.27])
        # revert pass: a station that was legal keeps its old site when both its hops (to the re-sited neighbours) allow it
        def pos(j): return regs[0] if j < 0 else (exitp if j >= k else [cen[j][0] + sh[j][0], cen[j][1] + sh[j][1]])
        for _ in range(3):
            for j in range(k):
                if slit[j] or sh[j] == [0, 0] or hits_other(boxes[j], s["name"]): continue
                if man(cen[j], pos(j - 1)) <= lim[j] and (j + 1 > k or pos(j + 1) is None or man(cen[j], pos(j + 1)) <= lim[j + 1]):
                    sh[j] = [0, 0]
        moved = []
        for j in range(k):
            dx, dy = sh[j]
            if abs(dx) < 1e-9 and abs(dy) < 1e-9: continue
            bs[j] = [[round(p[0] + dx, 4), round(p[1] + dy, 4)] for p in bs[j]]
            regs[j + 1] = [round(cen[j][0] + dx, 4), round(cen[j][1] + dy, 4)]
            allb[(s["name"], j)] = bbox(bs[j], cw, ch)
            moved.append(dict(station=j, shift_um=[round(dx, 3), round(dy, 3)], was_slit=bool(slit[j])))
        # exact re-check after snapping
        chain = list(regs) + ([exitp] if exitp else [])
        nh = [man(a, b) for a, b in zip(chain, chain[1:])]
        bad = [i for i, (h, l) in enumerate(zip(nh, lim)) if h > l + 1e-6]
        nb = [bbox(st, cw, ch) for st in bs]
        still = [j for j, b in enumerate(nb) if (part == HUB and near_core(b)) or hits_other(b, s["name"])]
        LED["resited"].append(dict(part=part, type=tn, slot=s["name"], width=s["width"] + 1, stations=k,
                                   slit_before=[j for j in range(k) if slit[j]], reach_bad_before=[j for j, r in enumerate(reach_bad) if r],
                                   moved=moved, hops_before=[round(h, 1) for h in hops], hops_after=[round(h, 1) for h in nh],
                                   hop_over_after=bad, clear_fail_after=still))
        print("RESITE", part, s["name"], "moved", len(moved), "hops max", round(max(nh), 1), "bad", bad, "still", still, flush=True)
note = " | DIE-KV-3/STATIONS D9c: chain re-site (DP, all stations of a slot) for slit/reach-bad FT slots"
raw["partition_types"]["kv3_hub_Wi"]["note"] = raw["partition_types"]["kv3_hub_Wi"].get("note", "") + note
Path(outp).write_text(json.dumps(raw, indent=1) + "\n")
Path(ledp).write_text(json.dumps(LED, indent=1) + "\n")
print("D9C resited", len(LED["resited"]), "failed", len(LED["failed"]), LED["failed"], "untouched", LED["untouched_bad"])
print("D9C_DONE")
