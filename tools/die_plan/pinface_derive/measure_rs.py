"""SUL0-FORM-1 (DIE-QC-97 11-10) measure: for every lane-facing bus of an su_l0 parent type, the lane hard-core pin
face of each lane macro, the direct hop face pin <-> lane pin (the landing register sits at the face pin), and the
kit knee rule (istations.tcl is_knee_site, limit 403, margin 400) sizing of a per-lane station chain.
Read only: bound RTL (bind.py, the kit's own), io.tcl (face pins), plan hard_cores + core pins files.
usage: measure.py PLAN TYPE BOUND_SV IO_TCL CORES_DIR OUT_JSON [--margin 400]"""
import json, re, sys
from collections import defaultdict

PLAN, TN, SV, IO, CORES, OUT = sys.argv[1:7]
MAR = float(sys.argv[sys.argv.index("--margin") + 1]) if "--margin" in sys.argv else 400.0
# --share BUS=instA+instB : those lanes' pins of BUS on one lane face share ONE chain (DIE-QC-97 11-10 cws0 strip)
CLEAR = "--clear-leaf" in sys.argv     # pick leaf_um so no station L route crosses a hard macro (DIE-QC-97 11-11)
# SU-RS-1 (DIE-QC-97 11-11) --spread [UM]: routing-supply form.  Among macro-clear leaves with the minimum station
# count, also try the leaf pushed up to UM (default 162) away from its lane macro in 10.8-um steps, and pick the one whose
# chain legs (face centroid -> kit corner -> leaf -> lane pins) cross the least already-planned chain traffic per
# routing bin (V legs vs V, H vs H, +-2 bins); chains are placed biggest first.  Without --spread nothing changes.
SPREAD = (float(sys.argv[sys.argv.index("--spread") + 1]) if "--spread" in sys.argv else 0.0)
RSB = 10.8
# --nbus MEAS_JSON: the bus latency is one per bus (mk_cand pads every chain to the bus max), so a leaf whose chain
# needs more stations than its own minimum but not more than the bus max costs no cycle: rank by traffic first then
NB = {}
if "--nbus" in sys.argv:
    for r_ in json.load(open(sys.argv[sys.argv.index("--nbus") + 1]))["rows"]:
        if "err" not in r_:
            NB[r_["bus"]] = max(NB.get(r_["bus"], 0), r_["n_kit_sim"])
from collections import defaultdict as _dd
GV, GH = _dd(float), _dd(float)
# KIT-CHAN-1 (DIE-QC-97 11-11) --channel FACE:LO:HI (repeatable): chains of a FACE bus also try plan leg_order "channel"
# with channel_um [LO, HI] (istation_channel.py: per-bit Z route through column LO + (HI - LO) (b + 0.5) / nbits), ranked
# with the other orders by the same key; the row then carries leg_order "channel" + channel_um.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
import istation_channel as IC
CHAN = {}
for i_, a_ in enumerate(sys.argv):
    if a_ == "--channel":
        f_, lo_, hi_ = sys.argv[i_ + 1].split(":")
        CHAN[f_] = (float(lo_), float(hi_))
NCHS = 4          # channel traffic is priced on NCHS sample columns, each carrying 1/NCHS of the chain's bits


def _samples(a, leaf, cc, face_ew, order, face_=None):
    """[(legs, weight)] of a chain for the traffic grid: one representative route, or NCHS channel columns"""
    if order != "channel":
        return [(_legs(a, None, leaf, cc, face_ew, order), 1.0)]
    lo, hi = CHAN[face_]
    out = []
    for s in range(NCHS):
        col = lo + (hi - lo) * (s + 0.5) / NCHS
        k1, k2 = ((col, a[1]), (col, leaf[1])) if face_ew else ((a[0], col), (leaf[0], col))
        legs = []
        for p, q in ((a, k1), (k1, k2), (k2, leaf), (leaf, (leaf[0], cc[1])), ((leaf[0], cc[1]), cc)):
            if abs(p[0] - q[0]) > 1e-6:
                legs.append(("H", p[1], min(p[0], q[0]), max(p[0], q[0])))
            elif abs(p[1] - q[1]) > 1e-6:
                legs.append(("V", p[0], min(p[1], q[1]), max(p[1], q[1])))
        out.append((legs, 1.0 / NCHS))
    return out


def _legs(a, c, leaf, cc, face_ew, order):
    """representative legs [(dir, fixed, lo, hi)] of a chain: a -> corner -> leaf -> cc (tail corner leaf.x, cc.y)"""
    k = (leaf[0], a[1]) if face_ew != (order == "along") else (a[0], leaf[1])
    out = []
    for p, q in ((a, k), (k, leaf), (leaf, (leaf[0], cc[1])), ((leaf[0], cc[1]), cc)):
        if abs(p[0] - q[0]) > 1e-6:
            out.append(("H", p[1], min(p[0], q[0]), max(p[0], q[0])))
        elif abs(p[1] - q[1]) > 1e-6:
            out.append(("V", p[0], min(p[1], q[1]), max(p[1], q[1])))
    return out


def _load(legs):
    worst = 0.0
    for d, f, lo, hi in legs:
        G = GV if d == "V" else GH
        fc = int(f // RSB)
        for r in range(int(lo // RSB), int(hi // RSB) + 1):
            worst = max(worst, sum(G[(fc + j, r)] for j in range(-2, 3)))
    return worst


def _add(legs, w):
    for d, f, lo, hi in legs:
        G = GV if d == "V" else GH
        for r in range(int(lo // RSB), int(hi // RSB) + 1):
            G[(int(f // RSB), r)] += w

SHARE = {}
for i, a in enumerate(sys.argv):
    if a == "--share":
        bn_, ins_ = sys.argv[i + 1].split("=", 1)
        SHARE.setdefault(bn_, []).append(ins_.split("+"))
LIM = 403.0
raw = json.load(open(PLAN))
t = raw["partition_types"][TN]
txt = open(SV).read()

face = {}
for m in re.finditer(r"place_pin -pin_name \{([^\[}]+)\[(\d+)\]\} \S+ \S+ -location \{([\d.\-]+) ([\d.\-]+)\}", open(IO).read()):
    face.setdefault(m.group(1), {})[int(m.group(2))] = (float(m.group(3)), float(m.group(4)))

# wire widths, to expand whole-wire references
wid = {}
for m in re.finditer(r"^\s*wire\s+(?:\[(\d+):(\d+)\]\s+)?([\w$]+)\s*;", txt, re.M):
    wid[m.group(3)] = (int(m.group(1)), int(m.group(2))) if m.group(1) else (0, 0)


def expand(cat):
    """'{a[3], b[1:0], c}' -> MSB-first list of 'name[bit]'"""
    cat = cat.strip()
    if cat.startswith("{"):
        cat = cat[1:-1]
    out = []
    for el in [x.strip() for x in cat.split(",") if x.strip()]:
        m = re.fullmatch(r"([\w$]+)\s*\[(\d+):(\d+)\]", el)
        if m:
            hi, lo = int(m.group(2)), int(m.group(3))
            out += [f"{m.group(1)}[{b}]" for b in range(hi, lo - 1, -1)]
            continue
        m = re.fullmatch(r"([\w$]+)\s*\[(\d+)\]", el)
        if m:
            out.append(el.replace(" ", ""))
            continue
        if re.fullmatch(r"[\w$]+", el):
            hi, lo = wid.get(el, (0, 0))
            if el not in wid:
                out.append(el)          # 1-bit wire / constant-like
            else:
                out += [f"{el}[{b}]" for b in range(hi, lo - 1, -1)] if (hi, lo) != (0, 0) else [el]
            continue
        out.append(el)                  # constant
    return out


def ports(line):
    d = {}
    for m in re.finditer(r"\.(\w+)\(((?:\{[^}]*\})|[^()]*)\)", line):
        d[m.group(1)] = m.group(2)
    return d


# SUL0-PINFACE-1 11-11 (COORD ruling A): a bus whose face register u_bin_<bus> takes a landing macro's q wire starts
# its chain at that macro's q pins (kit_istations start_core/start_port), not at the face BTerm
START = {}
TRUE_START = {}     # --face-start BUS: route the chain from the face BTerm (no clear L from the landing q pins) but price
FACE_START = {sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--face-start"}   # its first hop from them
if "--clear-leaf" in sys.argv:
    for hc in t["hard_cores"]:
        im = re.search(rf"^\s*{re.escape(hc['module'])}\s+[\w$]+\s*\((.*?)\);\s*$", txt, re.M | re.S)
        qm = im and re.search(r"\.q\(\s*([\w$]+)\s*\)", im.group(1))
        if not qm:
            continue
        w_ = qm.group(1)
        for bm in re.finditer(rf"\bu_bin_(\w+)\s*\(.*?\.d\({re.escape(w_)}\[(\d+):0\]\),\s*\.ea\({re.escape(w_)}\[(\d+)\]\)", txt):
            bn_, W_ = bm.group(1), int(bm.group(3))
            if int(bm.group(2)) != W_ - 1:
                continue
            pj = json.load(open(f"{CORES}/{hc['pins_file'].split('cores/', 1)[1]}"))
            if hc.get("orient", "R0") != "R0":
                raise SystemExit(f"{hc['inst']}: orient not handled")
            ox_, oy_ = hc["origin_um"]
            pp = {p["name"]: (round(ox_ + p["x"], 3), round(oy_ + p["y"], 3)) for p in pj["pins"]}
            if bn_ in FACE_START:
                TRUE_START[bn_] = {k: pp[f"q[{k}]"] for k in range(W_ + 1)}
                continue
            face[bn_] = {k: pp[f"q[{k}]"] for k in range(W_ + 1)}
            START[bn_] = hc["inst"]

lanes = {}
for hc in t["hard_cores"]:
    inst = hc["inst"]
    if "su_lane" not in hc["module"]:
        continue
    m = re.search(rf"^\s*{re.escape(hc['module'])}\s+{re.escape(inst)}\s*\((.*)\);\s*$", txt, re.M)
    if not m:
        raise SystemExit(f"{inst}: instance line not found")
    pj = json.load(open(f"{CORES}/{hc['pins_file'].split('cores/', 1)[1]}"))
    ox, oy = hc["origin_um"]
    if hc.get("orient", "R0") != "R0":
        raise SystemExit(f"{inst}: orient {hc['orient']} not handled")
    pins = {p["name"]: (round(ox + p["x"], 3), round(oy + p["y"], 3)) for p in pj["pins"]}
    lanes[inst] = dict(ports=ports(m.group(1)), pins=pins, origin=hc["origin_um"], outline=hc["outline_um"])

buses = {b["name"]: b for b in t["buses"]}
# in buses: bus bit -> [(lane, lane pin)]
reader = defaultdict(lambda: defaultdict(list))
driver_wire = {}     # wire bit -> (lane, lane pin)
for inst, L in lanes.items():
    for pn, cat in L["ports"].items():
        if pn in ("clk", "rst_n"):
            continue
        els = expand(cat)
        W = len(els)
        for i, el in enumerate(els):
            pin = f"{pn}[{W - 1 - i}]" if W > 1 or f"{pn}[0]" in L["pins"] else pn
            m = re.fullmatch(r"(\w+)_q\[(\d+)\]", el) or re.fullmatch(r"(\w+)_q()", el)   # bare = 1-bit bus, bit 0
            if m and m.group(1) in buses and buses[m.group(1)]["dir"] == "in":
                reader[m.group(1)][int(m.group(2) or 0)].append((inst, pin))
            else:
                driver_wire[el] = (inst, pin)
# out buses: u_bout_<bus> .d concat
outmap = defaultdict(lambda: defaultdict(list))
nonlane = defaultdict(list)
for bn, b in buses.items():
    if b["dir"] != "out":
        continue
    m = re.search(rf"\bu_bout_{bn}\s*\((.*)\);", txt)
    if not m:
        continue
    d = ports(m.group(1))["d"]
    els = expand(d)
    W = len(els)
    for i, el in enumerate(els):
        bit = W - 1 - i
        el0 = el[:-3] if el.endswith("[0]") and wid.get(el[:-3]) == (0, 0) else el
        if el0 in driver_wire:
            outmap[bn][bit].append(driver_wire[el0])
        else:
            nonlane[bn].append((bit, el))


def knee(first, second, edges):
    if first < 1e-8:
        return second / edges, 0
    if second < 1e-8:
        return first / edges, edges
    if edges < 2:
        return 1e99, -1
    return min((max(first / j, second / (edges - j)), j) for j in range(1, edges))


def need(first, second, lim):
    n = 0
    while knee(first, second, n + 1)[0] > lim and n < 30:
        n += 1
    return n


def site(px, py, lx, ly, fc, edge, edges, d, geo, order="normal"):
    """istations.tcl is_knee_site, verbatim (order "along" = plan leg_order along_first)"""
    xmin, ymin, xmax, ymax = geo
    if fc in "EW":
        normal, along = max(abs(xmin - lx), abs(xmax - lx)), max(abs(ymin - ly), abs(ymax - ly)); cx, cy = lx, py
    else:
        normal, along = max(abs(ymin - ly), abs(ymax - ly)), max(abs(xmin - lx), abs(xmax - lx)); cx, cy = px, ly
    n1, a1 = normal, along
    if order == "along":
        cx, cy = (px, ly) if fc in "EW" else (lx, py)
        n1, a1 = along, normal
    if d == "in":
        first, second, ax, ay, bx, by = n1, a1, px, py, lx, ly
    else:
        first, second, ax, ay, bx, by = a1, n1, lx, ly, px, py
    worst, split = knee(first, second, edges)
    if edge <= split:
        f = edge / split
        return (ax + f * (cx - ax), ay + f * (cy - ay)), worst
    f = (edge - split) / (edges - split)
    return (cx + f * (bx - cx), cy + f * (by - cy)), worst


def sim(bn, b, bp, n, leaf, order="normal"):
    """(kit knee worst, true max hop incl. the lane pin leg) of an n-station per_bit chain to leaf; bp = [(bit, inst,
    pin)], a bit read by several lanes of a shared chain has one station column and one last leg per consumer"""
    fp = face[bn]
    allp = list(fp.values())          # kit geometry: every bus BTerm / start (payload + epoch)
    geo = (min(p[0] for p in allp), min(p[1] for p in allp), max(p[0] for p in allp), max(p[1] for p in allp))
    worst, hmax = 0.0, 0.0
    for bit, inst, pin in bp:
        P = fp[bit]; C = lanes[inst]["pins"][pin]
        pts = []
        if order == "channel":                       # KIT-CHAN-1: kit is_chan_site, per-bit arclength split
            lo, hi = CHAN[b["face"]]
            if n:
                worst = max(worst, IC.worst_hop(P[0], P[1], leaf[0], leaf[1], b["face"], b["dir"], lo, hi, bit, len(fp), n))
            pts = IC.sites(P[0], P[1], leaf[0], leaf[1], b["face"], b["dir"], lo, hi, bit, len(fp), n)
        for k in range(n if order != "channel" else 0):
            xy, w = site(P[0], P[1], leaf[0], leaf[1], b["face"], k + 1, n + 1, b["dir"], geo, order)
            worst = max(worst, w); pts.append(xy)
        P1 = TRUE_START.get(bn, {}).get(bit, P)     # the real launch point (landing q pin) prices the first hop
        chain = ([P1] + pts + [C]) if b["dir"] == "in" else ([C] + pts + [P])
        hmax = max(hmax, max(abs(a[0] - c[0]) + abs(a[1] - c[1]) for a, c in zip(chain, chain[1:])))
    return (round(worst, 1) if n else 0.0), round(hmax, 1)


BOXES = {c["inst"]: (c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                     c["origin_um"][1] + c["outline_um"][1]) for c in t["hard_cores"]}   # every hard macro (R0 checked for lanes)
MG = 1.0          # leaf / leg clearance from a macro edge, um


TOL = 0.5          # = kit_istations.MACRO_TOL_UM (the validate / --apply gate)


def legs_hit(b, bp, leaf, order="normal"):
    """macros whose box (shrunk by TOL) a bit's kit L route (start -> corner -> leaf, is_knee_site) enters: stations on
    it would be sited on the macro (ff_put_near then moves them to the nearest free site, off the planned hop)"""
    lx, ly = leaf
    hit = set()
    for bit in {x[0] for x in bp} | {len(face[b["name"]]) - 1}:     # + the epoch bit (kept by synthesis)
        px, py = face[b["name"]][bit]
        c = (lx, py) if (b["face"] in "EW") != (order == "along") else (px, ly)
        segs = (((px, py), c), (c, (lx, ly)))
        if order == "channel":
            segs = IC.legs(px, py, lx, ly, b["face"], *CHAN[b["face"]], bit, len(face[b["name"]]))
        for (ax, ay), (cx_, cy_) in segs:
            x0, x1, y0, y1 = min(ax, cx_), max(ax, cx_), min(ay, cy_), max(ay, cy_)
            for nm, (bx0, by0, bx1, by1) in BOXES.items():
                if x0 < bx1 - TOL and x1 > bx0 + TOL and y0 < by1 - TOL and y1 > by0 + TOL:
                    hit.add(nm)
    return sorted(hit)


def seg_hit(a, c):
    x0, x1, y0, y1 = min(a[0], c[0]), max(a[0], c[0]), min(a[1], c[1]), max(a[1], c[1])
    return any(x0 < bx1 and x1 > bx0 and y0 < by1 and y1 > by0 for bx0, by0, bx1, by1 in BOXES.values())


def tail_clear(bp, leaf):
    """the last leg leaf -> every consumer lane pin has an L (either corner) off all macros (the pin itself sits on its
    macro edge, so the final MG um into the pin is not checked)"""
    for _, inst, pin in bp:
        cx, cy = lanes[inst]["pins"][pin]
        ok = False
        for k in ((leaf[0], cy), (cx, leaf[1])):
            if not seg_hit(leaf, k) and not seg_hit(k, shrink(k, (cx, cy))):
                ok = True
                break
        if not ok:
            return False
    return True


def shrink(a, c):
    """segment a -> c minus its last MG um (stop just outside the macro the pin c sits on)"""
    dx, dy = c[0] - a[0], c[1] - a[1]
    L = abs(dx) + abs(dy)
    if L <= MG:
        return a
    f = (L - MG) / L
    return (a[0] + dx * f, a[1] + dy * f)


def clear_leaf(bn, b, bp, side, cc):
    """(leaf_um, n, how, order): every bit's kit L route (start -> corner -> leaf, either leg order) and the last leg
    leaf -> lane pins stay off all macros.  Candidates: the pin centroid pushed MG out of its macro side, for S/N lane
    pins also the channel point at the macro column edge on the bus-face side, then (if none clears) the grid of macro
    edges +- MG.  Min stations (sim: kit worst <= MAR, true per-bit hop incl. last station -> lane pin <= MAR), then
    min hop, then normal-first.  Fails closed if none is clear."""
    inst0 = bp[0][1]
    ox, oy = lanes[inst0]["origin"]; w, h = lanes[inst0]["outline"]
    p0 = {"E": (ox + w + MG, cc[1]), "W": (ox - MG, cc[1]), "N": (cc[0], oy + h + MG), "S": (cc[0], oy - MG)}[side]
    cands = [("pin face +1um", p0)]
    if side in "NS" and b["face"] in "EW":
        cands.append(("channel at macro column edge", (ox + w + MG if b["face"] == "E" else ox - MG, p0[1])))
    xs = sorted({cc[0], p0[0]} | {v for x0, _, x1, _ in BOXES.values() for v in (x0 - MG, x1 + MG)})
    ys = sorted({cc[1], p0[1]} | {v for _, y0, _, y1 in BOXES.values() for v in (y0 - MG, y1 + MG)})
    W_, H_ = t["outline_um"]
    grid = [("macro-edge grid", (x, y)) for x in xs for y in ys if 0 < x < W_ and 0 < y < H_
            and not any(bx0 < x < bx1 and by0 < y < by1 for bx0, by0, bx1, by1 in BOXES.values())]
    if SPREAD:
        dv = {"W": (-1, 0), "E": (1, 0), "S": (0, -1), "N": (0, 1)}
        ext = []
        for how, (x, y) in cands:
            d = dv[side] if how.startswith("pin face") else dv[b["face"]]
            k = 1
            while k * RSB <= SPREAD + 1e-6:
                q = (x + d[0] * k * RSB, y + d[1] * k * RSB)
                if 0 < q[0] < t["outline_um"][0] and 0 < q[1] < t["outline_um"][1] and not any(
                        bx0 < q[0] < bx1 and by0 < q[1] < by1 for bx0, by0, bx1, by1 in BOXES.values()):
                    ext.append((how + f" spread {k * RSB:.1f}", q))
                k += 1
        cands = cands + ext
    best, tried = None, []
    for group in (cands, grid):
        for how, (x, y) in group:
            leaf = (round(x, 3), round(y, 3))
            if not tail_clear(bp, leaf):
                tried.append((how, leaf, "tail"))
                continue
            for order in ("normal", "along") + (("channel",) if b["face"] in CHAN else ()):
                lh = legs_hit(b, bp, leaf, order)
                if lh:
                    tried.append((how, leaf, order, lh))
                    continue
                n = 0
                while n < 12:
                    kw, hm = sim(bn, b, bp, n, leaf, order)
                    if kw <= MAR and hm <= MAR:
                        break
                    n += 1
                # with --channel the key is the peak AFTER adding this chain (a channel splits its bits over NCHS
                # columns); the + bits shift is the same for every non-channel candidate, so their ranking is unchanged
                ld = max(_load(l_) + (_w * len(bp) if CHAN else 0.0)
                         for l_, _w in _samples(FC, leaf, cc, b["face"] in "EW", order, b["face"])) if SPREAD else 0.0
                key = ((n, ld, hm, order != "normal") if not (SPREAD and bn in NB) else
                       ((0 if n <= NB[bn] else 1), ld, n, hm, order != "normal"))
                if best is None or key < best[0]:
                    best = (key, leaf, n, how, order)
        if best is not None and best[2] < 12:
            break
    if best is None or best[2] >= 12:
        raise SystemExit(f"{TN} {bn} {inst0}.{side}: no macro-clear leaf with n < 12: best {best} tried {tried[:6]}")
    return best[1], best[2], best[3], best[4]


rows = []
for bn, b in buses.items():
    src = reader.get(bn) if b["dir"] == "in" else outmap.get(bn)
    if not src:
        continue
    fp = face.get(bn, {})
    per = defaultdict(list)
    for bit, lst in src.items():
        for inst, pin in lst:
            ox, oy = lanes[inst]["origin"]; w, h = lanes[inst]["outline"]; x, y = lanes[inst]["pins"][pin]
            dd = {"S": abs(y - oy), "N": abs(y - oy - h), "W": abs(x - ox), "E": abs(x - ox - w)}
            grp = next(("+".join(g) for g in SHARE.get(bn, []) if inst in g), inst)
            per[(grp, min(dd, key=dd.get))].append((bit, inst, pin))
    for key in (sorted(per, key=lambda k_: (-len(per[k_]), k_)) if SPREAD else sorted(per)):
        inst, side = key
        bp = per[key]
        F = [fp[bit] for bit, _, _ in bp if bit in fp]
        C = [lanes[i]["pins"][pin] for _, i, pin in bp if pin in lanes[i]["pins"]]
        if len(F) != len(bp) or len(C) != len(bp):
            rows.append(dict(bus=bn, lane=inst, bits=len(bp), err=f"face {len(F)} core {len(C)} of {len(bp)}"))
            continue
        hop = [abs(f[0] - c[0]) + abs(f[1] - c[1]) for f, c in zip(F, C)]
        fx, fy = [p[0] for p in F], [p[1] for p in F]
        cx, cy = [p[0] for p in C], [p[1] for p in C]
        fc = (sum(fx) / len(fx), sum(fy) / len(fy))
        cc = (sum(cx) / len(cx), sum(cy) / len(cy))
        # knee geometry (is_knee_site form): normal = across the bus face, along = parallel to it, extremes of both bboxes
        if b["face"] in "EW":
            normal = max(abs(a - c) for a in (min(fx), max(fx)) for c in (min(cx), max(cx)))
            along = max(abs(a - c) for a in (min(fy), max(fy)) for c in (min(cy), max(cy)))
        else:
            normal = max(abs(a - c) for a in (min(fy), max(fy)) for c in (min(cy), max(cy)))
            along = max(abs(a - c) for a in (min(fx), max(fx)) for c in (min(cx), max(cx)))
        first, second = (normal, along) if b["dir"] == "in" else (along, normal)
        nm, nl = need(first, second, MAR), need(first, second, LIM)
        leaf0 = (round(cc[0], 3), round(cc[1], 3))
        if CLEAR:
            FC = fc
            leaf, ns, leaf_how, order = clear_leaf(bn, b, bp, side, cc)
            if SPREAD:
                for l_, w_ in _samples(fc, leaf, cc, b["face"] in "EW", order, b["face"]):
                    _add(l_, float(len(bp)) * w_)
        else:
            leaf, leaf_how, order = leaf0, "pin centroid", "normal"
            ns = 0
            while ns < 12:
                kw, hm = sim(bn, b, bp, ns, leaf)
                if kw <= MAR and hm <= MAR:
                    break
                ns += 1
        sims = {k: sim(bn, b, bp, k, leaf, order) for k in range(0, 6)}
        lanepins = sorted({p.split("[")[0] for _, _, p in bp})
        # lane pin face of these pins (which side of the macro box)
        sides = set()
        for (_, i_, _), (x, y) in zip(bp, C):
            ox, oy = lanes[i_]["origin"]; w, h = lanes[i_]["outline"]
            d = {"S": abs(y - oy), "N": abs(y - oy - h), "W": abs(x - ox), "E": abs(x - ox - w)}
            sides.add(min(d, key=d.get))
        rows.append(dict(bus=bn, dir=b["dir"], face=b["face"], lane=inst, side=side, bits=len({bit for bit, _, _ in bp}), consumers=len(bp), core_bits=sorted({bit for bit, _, _ in bp}), bound_width=len(face.get(bn, {})) - 1, lane_ports=lanepins,
                         lane_face=sorted(sides),
                         face_bbox=[round(min(fx), 1), round(min(fy), 1), round(max(fx), 1), round(max(fy), 1)],
                         lane_pin_bbox=[round(min(cx), 1), round(min(cy), 1), round(max(cx), 1), round(max(cy), 1)],
                         face_centroid=[round(fc[0], 2), round(fc[1], 2)], lane_pin_centroid=[round(cc[0], 2), round(cc[1], 2)],
                         hop_max_um=round(max(hop), 1), hop_mean_um=round(sum(hop) / len(hop), 1),
                         knee_first=round(first, 1), knee_second=round(second, 1),
                         knee_worst_0=round(knee(first, second, 1)[0], 1),
                         n_need_400=nm, n_need_403=nl, knee_worst_at_n=round(knee(first, second, nm + 1)[0], 1),
                         l1_over_edges=round(max(hop) / (nm + 1), 1), leaf_um=list(leaf), leaf_how=leaf_how, start_core=START.get(bn), start_um=([list(face[bn][k]) for k in range(len(face[bn]))] if bn in START else None), face_start_priced_from=('landing q' if bn in TRUE_START else None),
                         leaf_legs_in_macro=legs_hit(b, bp, leaf, order), leg_order=order, n_kit_sim=ns,
                         **({"channel_um": list(CHAN[b["face"]])} if order == "channel" else {}),
                         sim_by_n={k: list(v) for k, v in sims.items()}))
json.dump(dict(type=TN, margin=MAR, rows=rows, nonlane_out_bits={k: len(v) for k, v in nonlane.items()},
               nonlane_examples={k: v[:5] for k, v in nonlane.items()},
               in_bits_per_lane={bn: {i: sum(1 for b_ in r.values() for x in b_ if x[0] == i) for i in lanes}
                                 for bn, r in reader.items()},
               in_multicast_bits={bn: sum(1 for v in r.values() if len(v) > 1) for bn, r in reader.items()},
               out_multi_driver_bits={bn: sum(1 for v in r.values() if len(v) > 1) for bn, r in outmap.items()}),
          open(OUT, "w"), indent=1)
print(f"{'bus':14} {'dir':3} F {'lane':7} {'bits':>4} lanefc {'hopmax':>7} {'first':>6} {'second':>6} n400 worst  nsim sim(n): kitworst/truehop")
for r in rows:
    if "err" in r:
        print("ERR", r)
        continue
    print(f"{r['bus']:14} {r['dir']:3} {r['face']} {r['lane']+'.'+r['side']:9} {r['bits']:4} {''.join(r['lane_face']):6} {r['hop_max_um']:7.1f} "
          f"{r['knee_first']:6.1f} {r['knee_second']:6.1f} {r['n_need_400']:4} {r['knee_worst_at_n']:6.1f} {r['n_kit_sim']:4} "
          + " ".join(f"{k}:{v[0]:.0f}/{v[1]:.0f}" for k, v in r['sim_by_n'].items()))
print("nonlane out bits", {k: len(v) for k, v in nonlane.items()})
