"""DIE-KV-2 / KV-PLAN-DELTA-9b (COORD 10-27 20:38 ruling (a) A): no FT move.  On hq_r26q9:
 (1) F2: every FT port on a hub_Wi face (neighbours hub_C / hub_Wo / hgi_WN_7, all single-instance types, hub_Wi x1) packed
     above 8 b/um is re-windowed to <= 8 b/um (S.window_for per_um=8, track_max 0.6), core-clear (20 um each side) and clear
     of every other port on that face (1.08-um gap); order along the face kept; a port that meets an obstacle is split over
     the free spans as a multi-window hop (schema `segments`, D9a tool).
 (2) hub_Wi FT stations in core slits: every station whose bit-site bbox is closer than CLR_ST to a hard core is rigidly
     shifted to the nearest spot >= CLR_ST from every core and not overlapping another station (else reported stuck).
usage: d9b_event.py RUNTIME_ROOT IN.json OUT.json LEDGER.json [--estimate]"""
import copy, json, math, sys
from pathlib import Path
R = Path(sys.argv[1]); inp, outp, ledp = sys.argv[2:5]; EST = "--estimate" in sys.argv
KEEP = set(open(sys.argv[sys.argv.index('--keep') + 1]).read().split()) if '--keep' in sys.argv else set()
sys.path.insert(0, str(R / "tools/die_plan")); sys.path.insert(0, str(R))
import schema as S
raw = json.load(open(inp)); P = S.Plan(raw, Path(inp))
PER_UM, GAP, CLEAR, CLR_ST, MIN_SEG, REACH_ST = 8.0, 1.08, 20.0, 10.8, 32, 395.0
ports = {p["id"]: p for p in raw["ports"]}
HUB = "hub_Wi"; NB = ["hub_C", "hub_Wo", "hgi_WN_7"]
LED = dict(kept_by_reach=sorted(KEEP), estimate=[], windows=[], stations=[], stuck=[])

def shared(a, b):
    ax0, ay0, ax1, ay1 = P.rect(a); bx0, by0, bx1, by1 = P.rect(b)
    if abs(ax1 - bx0) < 1e-3: return "E", max(ay0, by0), min(ay1, by1), ax1
    if abs(ax0 - bx1) < 1e-3: return "W", max(ay0, by0), min(ay1, by1), ax0
    if abs(ay1 - by0) < 1e-3: return "N", max(ax0, bx0), min(ax1, bx1), ay1
    if abs(ay0 - by1) < 1e-3: return "S", max(ax0, bx0), min(ax1, bx1), ay0
    raise ValueError((a, b))

def die_boxes(part):
    out = []
    for bx in S.placed_macro_boxes(P.ptype(part)).values():
        p1 = P.to_die(part, (bx[0], bx[1])); p2 = P.to_die(part, (bx[2], bx[3]))
        out.append((min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])))
    return out

def is_ft(pr):
    return any(pr[k]["part"] != "@die" and P.buses(pr[k]["part"]).get(pr[k]["bus"], {}).get("slot") for k in ("src", "dst"))

def wlen(n, lays):
    return S.window_for(0.0, n, lays, per_um=PER_UM, track_max=0.6)

def ivl(pid):
    cs = [c for _, _, c in P.port_pins(pid)]
    return min(cs), max(cs)

total_moved = 0
for nb in NB:
    face, lo, hi, line = shared(HUB, nb)
    pp = [pid for pid, pr in P.ports.items() if {pr["src"]["part"], pr["dst"]["part"]} == {HUB, nb}]
    tgt, fixed = [], []
    for pid in pp:
        pr = P.ports[pid]; a, b = ivl(pid); n = S.port_pins_count(pr)
        if pid not in KEEP and is_ft(pr) and n >= 16 and n / max(b - a, 0.05) > PER_UM + 1e-6:
            tgt.append(pid)
        else:
            fixed.append((a - GAP, b + GAP, pid))
    cuts = [(f[0], f[1]) for f in fixed]
    for part in (HUB, nb):
        for x0, y0, x1, y1 in die_boxes(part):
            if face in "EW":
                if x1 > line - CLEAR and x0 < line + CLEAR: cuts.append((y0, y1))
            elif y1 > line - CLEAR and y0 < line + CLEAR: cuts.append((x0, x1))
    cuts.sort(); cur = lo + 4.32; spans = []
    for c0, c1 in cuts:
        if c0 > cur: spans.append([cur, min(c0, hi - 4.32)])
        cur = max(cur, c1)
    if hi - 4.32 > cur: spans.append([cur, hi - 4.32])
    spans = [s for s in spans if s[1] - s[0] > 2 * GAP + 1.0]
    # targets freed: their own old windows are free space too (they were not in cuts)
    lays_of = {pid: list(P.ports[pid]["layers"]) for pid in tgt}
    need = sum(wlen(S.port_pins_count(P.ports[pid]), lays_of[pid]) + 2 * GAP for pid in tgt)
    have = sum(s[1] - s[0] for s in spans)
    LED["estimate"].append(dict(pair=f"{HUB}|{nb}", face=face, edge_um=round(hi - lo, 1), ports=len(pp), ft_over8=len(tgt),
                                ft_over8_bits=sum(S.port_pins_count(P.ports[p]) for p in tgt),
                                need_um_at8=round(need, 1), free_um=round(have, 1), fixed_ports=len(fixed)))
    print("EST", LED["estimate"][-1], flush=True)
    if "--spans" in sys.argv: print("SPANS", nb, [(round(a,1), round(b_,1)) for a, b_ in spans]); print("FIXED", sorted((round(f[0],1),round(f[1],1),f[2]) for f in fixed))
    if EST or not tgt: continue
    # pack in order of current centre, left to right, each start >= its ideal (centre - L/2) when room allows
    order = sorted(tgt, key=lambda p: sum(ivl(p)) / 2)
    tot_need = need
    def pack(order, spans, use_ideal=True, tail=1.0):
        # free coordinate u: spans concatenated; ideal u from the old centre; isotonic clamp keeps the order and room
        cum = [0.0]
        for s_ in spans: cum.append(cum[-1] + s_[1] - s_[0])
        have_ = cum[-1]
        def to_u(x):
            for i, s_ in enumerate(spans):
                if x <= s_[1]: return cum[i] + max(0.0, x - s_[0])
            return have_
        Ls = [wlen(S.port_pins_count(P.ports[p]), lays_of[p]) + 2 * GAP for p in order]
        Ls = [l * 1.06 for l in Ls]                       # span-break / PG-snap allowance
        us = []
        for k, pid in enumerate(order):                   # pass 1: ideal, order kept
            c0 = sum(ivl(pid)) / 2
            us.append(max(us[-1] + Ls[k - 1] if us else 0.0, to_u(c0) - Ls[k] / 2) if use_ideal else (us[-1] + Ls[k - 1] if us else 0.0))
        nxt = have_ * tail
        for k in range(len(order) - 1, -1, -1):           # pass 2: push left only as far as the room needs
            us[k] = max(0.0, min(us[k], nxt - Ls[k])); nxt = us[k]
        res = {}; si = 0; cur = spans[0][0]
        for k, pid in enumerate(order):
            pr = P.ports[pid]; npins = S.port_pins_count(pr); lays = lays_of[pid]
            u = us[k]
            # real start for u
            for i in range(len(spans)):
                if u <= cum[i + 1] + 1e-9: break
            x = spans[i][0] + (u - cum[i])
            if (i, x) > (si, cur): si, cur = i, x
            segs = []; left = npins
            while left > 0:
                if si >= len(spans): return None
                room = spans[si][1] - cur - 2 * GAP
                if wlen(left, lays) <= room:
                    w0 = round(cur + GAP, 4); w1 = S.window_for(w0, left, lays, per_um=PER_UM, track_max=0.6)
                    if w1 > spans[si][1] - GAP + 1e-6:
                        si += 1
                        if si < len(spans): cur = spans[si][0]
                        continue
                    segs.append((left, [w0, round(w1, 4)]))
                    cur = w1 + GAP; left = 0; break
                n0, n1 = 0, left
                while n0 < n1:
                    m = (n0 + n1 + 1) // 2
                    if wlen(m, lays) <= room: n0 = m
                    else: n1 = m - 1
                if n0 % 2: n0 -= 1
                if n0 >= MIN_SEG:
                    w0 = round(cur + GAP, 4); w1 = S.window_for(w0, n0, lays, per_um=PER_UM, track_max=0.6)
                    if w1 <= spans[si][1] - GAP + 1e-6: segs.append((n0, [w0, round(w1, 4)])); left -= n0
                si += 1
                if si < len(spans): cur = spans[si][0]
            res[pid] = segs
        return res
    res = None
    for tail in (1.0, 0.98, 0.96, 0.94, 0.92, 0.9, 0.85, 0.8):
        res = pack(order, spans, True, tail)
        if res is not None: LED.setdefault("tail", {})[nb] = tail; break
    if res is None:
        raise SystemExit(f"PACK FAIL {HUB}|{nb}: need {need:.1f} um, free {have:.1f} um")
    for pid, segs in res.items():
        pr = ports[pid]; old = ivl(pid)
        pr["window_um"] = [min(w[0] for _, w in segs), max(w[1] for _, w in segs)]
        pr.pop("segments", None)
        if len(segs) > 1:
            pr["segments"] = [dict(pins=n, window_um=w) for n, w in segs]
        pr["note"] = (pr.get("note", "") + " | DIE-KV-2 D9b F2: re-windowed to <= 8 b/um").lstrip(" |")
        total_moved += 1
        LED["windows"].append(dict(port=pid, pair=f"{HUB}|{nb}", pins=S.port_pins_count(pr), old=[round(old[0], 2), round(old[1], 2)],
                                   new=[dict(pins=n, window_um=w, b_per_um=round(n / (w[1] - w[0]), 3)) for n, w in segs],
                                   shift_um=round((pr["window_um"][0] + pr["window_um"][1]) / 2 - sum(old) / 2, 1)))
if EST:
    Path(ledp).write_text(json.dumps(LED, indent=1) + "\n"); raise SystemExit(0)
P = S.Plan(raw, Path(inp))

# (2) entry-face register refresh for slots fed by a re-windowed port, then stations: slit escape (hub_Wi) + reach repair
moved_ports = {w["port"] for w in LED["windows"]}
LED["regs0"] = []; LED["repair"] = []
def frame(part, PP=None):
    PP = PP or P
    o = PP.to_die(part, (0.0, 0.0)); ex = PP.to_die(part, (1.0, 0.0)); ey = PP.to_die(part, (0.0, 1.0))
    A = [[ex[0] - o[0], ey[0] - o[0]], [ex[1] - o[1], ey[1] - o[1]]]; det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    def to_type(p):
        dx, dy = p[0] - o[0], p[1] - o[1]
        return ((A[1][1] * dx - A[0][1] * dy) / det, (-A[1][0] * dx + A[0][0] * dy) / det)
    return to_type
def face_mean(part, pid, side, PP=None):
    PP = PP or P
    pr = PP.ports[pid]; face = pr["face"] if side == "src" else S.OPP[pr["face"]]; x0, y0, x1, y1 = PP.rect(part)
    pts = [((x0 if face == "W" else x1), c) if face in "EW" else (c, (y0 if face == "S" else y1)) for _, _, c in PP.port_pins(pid)]
    tt = frame(part, PP); tp = [tt(p) for p in pts]
    return [round(sum(p[0] for p in tp) / len(tp), 4), round(sum(p[1] for p in tp) / len(tp), 4)]
port_by_dst = {(pr["dst"]["part"], pr["dst"]["bus"]): q for q, pr in P.ports.items()}
port_by_src = {(pr["src"]["part"], pr["src"]["bus"]): q for q, pr in P.ports.items()}
for part in [HUB] + NB:
    tn = P.parts[part]["type"]
    for sl in raw["partition_types"][tn].get("ft_slots", []):
        pid = port_by_dst.get((part, sl["name"] + "_i"))
        if pid in moved_ports and sl.get("regs_um"):
            m = face_mean(part, pid, "dst"); LED["regs0"].append(dict(type=tn, slot=sl["name"], port=pid, old=sl["regs_um"][0], new=m)); sl["regs_um"][0] = m
P0 = S.Plan(json.load(open(inp)), Path(inp))
p0_src = {(pr["src"]["part"], pr["src"]["bus"]): q for q, pr in P0.ports.items()}
BASE = {}
for part in [HUB] + NB:
    for sl in P0.types[P0.parts[part]["type"]].get("ft_slots", []):
        rg = sl.get("regs_um") or []; po = p0_src.get((part, sl["name"] + "_o"))
        ex0 = face_mean(part, po, "src", P0) if po else None
        for j in range(len(sl.get("bit_sites_um", []))):
            if j + 1 >= len(rg): continue
            nx0 = rg[j + 2] if j + 2 < len(rg) else ex0
            BASE[(part, sl["name"], j)] = (abs(rg[j+1][0]-rg[j][0]) + abs(rg[j+1][1]-rg[j][1]),
                                            abs(rg[j+1][0]-nx0[0]) + abs(rg[j+1][1]-nx0[1]) if nx0 else 0.0)
STEP = 1.08
CAND = sorted(((abs(i) + abs(j2)) * STEP, i * STEP, j2 * STEP) for i in range(-185, 186) for j2 in range(-185, 186))
def bbox(st, cw, ch): return (min(p[0] for p in st), min(p[1] for p in st), max(p[0] for p in st) + cw, max(p[1] for p in st) + ch)
def man(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
def process(part, slit):
    tn = P.parts[part]["type"]; ty = raw["partition_types"][tn]; W, H = ty["outline_um"]
    cores = [tuple(bx) for bx in S.placed_macro_boxes(P.ptype(part)).values()]
    clr = CLR_ST if slit else 0.3
    def near_core(b, c_=None):
        c_ = clr if c_ is None else c_
        return any(b[0] < c[2] + c_ and b[2] > c[0] - c_ and b[1] < c[3] + c_ and b[3] > c[1] - c_ for c in cores)
    allb = []
    for s in ty.get("ft_slots", []):
        cw, ch = s.get("bit_site_cell_um", [0.0, 0.0])
        for j, st in enumerate(s.get("bit_sites_um", [])):
            if st: allb.append([s["name"], j, bbox(st, cw, ch)])
    def hits_other(b, me):
        return any(o[:2] != me and b[0] < o[2][2] and b[2] > o[2][0] and b[1] < o[2][3] and b[3] > o[2][1] for o in allb)
    for s in ty.get("ft_slots", []):
        cw, ch = s.get("bit_site_cell_um", [0.0, 0.0]); regs = s.get("regs_um"); bs = s.get("bit_sites_um", [])
        if not regs or not bs: continue
        pout = port_by_src.get((part, s["name"] + "_o"))
        exitp = face_mean(part, pout, "src") if pout else None
        for j, st in enumerate(bs):
            if not st: continue
            b = bbox(st, cw, ch); cen = regs[j + 1] if j + 1 < len(regs) else None
            if cen is None: continue
            prv = regs[j]; nxt_ = regs[j + 2] if j + 2 < len(regs) else exitp
            bp, bn = BASE.get((part, s["name"], j), (0.0, 0.0))
            lp, ln = max(REACH_ST, bp + 0.5), max(REACH_ST, bn + 0.5)
            reach_bad = man(cen, prv) > lp or (nxt_ is not None and man(cen, nxt_) > ln)
            facest = b[0] < 0.5 or b[2] > W - 0.5 or b[1] < 0.5 or b[3] > H - 0.5
            slit_bad = slit and not facest and near_core(b)
            if not (reach_bad or slit_bad): continue
            def ok_reach(c):
                return man(c, prv) <= lp and (nxt_ is None or man(c, nxt_) <= ln)
            best = None
            for _, dx, dy in CAND:
                if dx == 0 and dy == 0: continue
                nb_ = (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)
                if not (nb_[0] > 1 and nb_[2] < W - 1 and nb_[1] > 1 and nb_[3] < H - 1): continue
                if not ok_reach((cen[0] + dx, cen[1] + dy)): continue
                if (slit and near_core(nb_)) or (not slit and near_core(nb_)) or hits_other(nb_, [s["name"], j]): continue
                best = (round(dx, 3), round(dy, 3)); break
            if best:
                bs[j] = [[round(p[0] + best[0], 4), round(p[1] + best[1], 4)] for p in st]
                regs[j + 1] = [round(cen[0] + best[0], 4), round(cen[1] + best[1], 4)]
                nbx = (b[0] + best[0], b[1] + best[1], b[2] + best[0], b[3] + best[1])
                for o in allb:
                    if o[:2] == [s["name"], j]: o[2] = nbx
                LED["stations" if slit_bad else "repair"].append(dict(type=tn, slot=s["name"], station=j, shift_um=list(best), why="slit" if slit_bad else "reach"))
                continue
            # reshape (k-column block, cell pitch 2.16 x 0.27)
            nb_bits = len(st); cx0, cy0 = cen; found = None
            for k in (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64):
                rows = math.ceil(nb_bits / k); bw = (k - 1) * 2.16 + cw; bh = rows * 0.27
                if bh > H - 4 or bw > W - 4: continue
                for _, dx, dy in CAND:
                    cx, cy = cx0 + dx, cy0 + dy
                    nb_ = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
                    if not (nb_[0] > 1 and nb_[2] < W - 1 and nb_[1] > 1 and nb_[3] < H - 1): continue
                    if not ok_reach((cx, cy)) or near_core(nb_) or hits_other(nb_, [s["name"], j]): continue
                    d = abs(dx) + abs(dy)
                    if found is None or d < found[0]: found = (d, k, rows, nb_)
                    break
            if found:
                d, k, rows, nb_ = found
                pts = [[round(nb_[0] + (i % k) * 2.16, 4), round(nb_[1] + (i // k) * 0.27, 4)] for i in range(nb_bits)]
                bs[j] = pts
                regs[j + 1] = [round(sum(p[0] for p in pts) / nb_bits + cw / 2, 4), round(sum(p[1] for p in pts) / nb_bits + ch / 2, 4)]
                for o in allb:
                    if o[:2] == [s["name"], j]: o[2] = nb_
                LED["stations" if slit_bad else "repair"].append(dict(type=tn, slot=s["name"], station=j, why="slit" if slit_bad else "reach",
                                       reshaped=dict(cols=k, rows=rows, bbox=[round(v, 2) for v in nb_]), bbox_old=[round(v, 2) for v in b], move_um=round(d, 1)))
            else:
                LED["stuck"].append(dict(type=tn, slot=s["name"], station=j, why="slit" if slit_bad else "reach", bbox=[round(v, 2) for v in b]))
for it in range(2):
    LED["stuck"] = []
    process(HUB, True)
    for nb in NB: process(nb, False)
raw["partition_types"]["kv3_hub_Wi"]["note"] = raw["partition_types"]["kv3_hub_Wi"].get("note", "") + " | DIE-KV-2 D9b: FT stations >= 10.8 um from hard cores (slit stations moved/reshaped)"
Path(outp).write_text(json.dumps(raw, indent=1) + "\n")
Path(ledp).write_text(json.dumps(LED, indent=1) + "\n")
print("PORTS re-windowed", total_moved, "segmented", sum(1 for w in LED["windows"] if len(w["new"]) > 1),
      "max shift", max((abs(w["shift_um"]) for w in LED["windows"]), default=0))
print("STATIONS slit-moved", len(LED["stations"]), "reach-repaired", len(LED["repair"]), "stuck", len(LED["stuck"]), LED["stuck"])
print("REGS0 refreshed", len(LED["regs0"]))
print("D9B_DONE")
