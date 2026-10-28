"""DIE-HBM C20 = ONE HBM re-plan event on C19 (COORD 20:21 HBM-STREETS-3 rulings (a)-(d), 12.13e).
usage: apply_c20.py REPO C19DIR C20DIR '{"repack": "path/c20_repack_delta.json", "islands": "path/core_islands.json",
                                         "regions": "path/regions.json"}'
(a) SM street: q_sm0/q_sm2/q_sm3 widened by D=34.56 um, taken from the spb (sm2/sm3) and spt (sm0) partitions; the spb0
    PHY (die.io rect = bump field) and its clock keepout keep their DIE coordinates (the 34.56-um W margin of
    clock_keepout_0 that now lies in q_sm2 is carried as a q_sm2 clock keepout).  sm0/sm2: core array moves D away from
    the die edge (die-edge street); sm3: array keeps its local frame, the partition grows on the spb side (t07 street).
(b) L12 re-route root->b101->hub (b101 N face -> hub S face); su31 slot L12x2 removed; latency kept (fixed_cycles pad).
(c) C17g outline growth re-pack + vms_glue E-face cap: folded from the REPACK delta (sub-lane), if given.
(d) 12.2a1 in-core island slices: clock.mesh.core_islands from the KITS sub-lane core_islands.json, if given.
(e) region map: LAND-HBM quad partition->region + feed tree (side file regions_c20.json; off-feed crossings listed).
(f) station relax (as C19) for any die-lane station that now falls inside a core.
"""
import json, sys, shutil, hashlib, os, copy
from pathlib import Path
REPO, SRC, OUT = map(Path, sys.argv[1:4]); OPT = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
raw = json.load(open(SRC / "die_plan.json")); T = raw["partition_types"]; parts = {p["name"]: p for p in raw["partitions"]}
rep = dict(source=str(SRC / "die_plan.json"), source_sha=hashlib.sha256((SRC / "die_plan.json").read_bytes()).hexdigest()[:12], opt=OPT)
D = OPT.get("d", 34.56)
def r4(v): return round(v, 4)
OUT.mkdir(parents=True, exist_ok=True)
if not (OUT / "cores").exists(): shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")

# ---------------- (a) SM widen / spb, spt shrink
def shift_type(t, dx, split=None):
    """shift every type-frame x coordinate by dx (windows only on N/S faces).  split=(xm, dx2): points at x >= xm shift
    by dx2 instead (a partition that loses width on both sides keeps every object's distance to its nearer edge)."""
    n = 0
    def mx(x):
        v = r4(x + (dx2 if split and x >= xm else dx))
        return v if v >= 0 else r4(x)   # edge-riding objects (W-edge stations / bit sites) stay on the new edge side
    if split: xm, dx2 = split
    def sx(pt): return [mx(pt[0]), pt[1]] + list(pt[2:])
    def sw(w):
        c = (w[0] + w[1]) / 2; d = (dx2 if split and c >= xm else dx); return [r4(w[0] + d), r4(w[1] + d)]
    for c in t.get("hard_cores") or []:
        cx = c["origin_um"][0] + c["outline_um"][0] / 2; d = (dx2 if split and cx >= xm else dx)
        c["origin_um"] = [r4(c["origin_um"][0] + d), c["origin_um"][1]]; n += 1
    for c in t.get("contents") or []:
        if c.get("origin_um") and c.get("outline_um") and c["outline_um"][0] < t["outline_um"][0] - 1e-6:
            c["origin_um"] = sx(c["origin_um"])
    ck = t.get("clock") or {}
    if ck.get("tap_um"): ck["tap_um"] = sx(ck["tap_um"])
    for tp in ck.get("taps") or []:
        if tp.get("xy"): tp["xy"] = sx(tp["xy"])
    if ck.get("keepouts_um"): ck["keepouts_um"] = [[sw([k[0], k[2]])[0], k[1], sw([k[0], k[2]])[1], k[3]] for k in ck["keepouts_um"]]
    rs = t.get("reset") or {}
    if rs.get("tap_um"): rs["tap_um"] = sx(rs["tap_um"])
    for ch in t.get("channels") or []:
        if ch.get("rect_um"): w = sw([ch["rect_um"][0], ch["rect_um"][2]]); ch["rect_um"] = [w[0], ch["rect_um"][1], w[1], ch["rect_um"][3]]
    for s in t.get("internal_stations") or []:
        for k in ("from_um", "to_um"):
            if s.get(k): s[k] = sx(s[k])
        if s.get("regs_um"): s["regs_um"] = [sx(q) for q in s["regs_um"]]
    for b in t.get("buses") or []:
        if b.get("window_um") and b.get("face") in ("N", "S"): b["window_um"] = sw(b["window_um"])
    for s in t.get("ft_slots") or []:
        if s.get("regs_um"): s["regs_um"] = [sx(q) for q in s["regs_um"]]
        if s.get("bit_sites_um"): s["bit_sites_um"] = [[sx(q) for q in st] for st in s["bit_sites_um"]]
        for f, w in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if s.get(w) and s.get(f) in ("N", "S"): s[w] = sw(s[w])
    for b in t.get("die_ft_bands") or []:
        if b.get("dir") == "NS": b["span_um"] = sw(b["span_um"])
    return n
def widen(tn, dw):
    t = T[tn]; W0 = t["outline_um"][0]; t["outline_um"] = [r4(W0 + dw), t["outline_um"][1]]
    for c in t.get("contents") or []:
        if c.get("outline_um") and abs(c["outline_um"][0] - W0) < 1e-6: c["outline_um"] = [r4(W0 + dw), c["outline_um"][1]]
def bounds_issues(tn):
    t = T[tn]; W, H = t["outline_um"]; bad = []
    def chk(what, x):
        if x < -1e-6 or x > W + 1e-6: bad.append(f"{what} x={x}")
    for c in t.get("hard_cores") or []: chk(c["inst"], c["origin_um"][0]); chk(c["inst"] + "+w", c["origin_um"][0] + c["outline_um"][0])
    for s in t.get("ft_slots") or []:
        for q in (s.get("regs_um") or []): chk(s["name"] + " reg", q[0])
        nb = sum(1 for st in (s.get("bit_sites_um") or []) for q in st if q[0] < 0 or q[0] > W)
        if nb: bad.append(f"{s['name']} bit_sites outside: {nb}")
    for s in t.get("internal_stations") or []:
        for q in (s.get("regs_um") or []): chk(s["conn"] + " ist", q[0])
    for b in t.get("buses") or []:
        if b.get("window_um") and b.get("face") in ("N", "S"): chk(b["name"] + " win", b["window_um"][0]); chk(b["name"] + " win", b["window_um"][1])
    return bad
sm = {}
# q_sm0 / q_sm2: grow on the local E (spt/spb) side, array moves +D (die-edge street); NE (MY) origin -D
for tn in ("q_sm0", "q_sm2"):
    keep = copy.deepcopy([b.get("window_um") for b in T[tn].get("buses") or []])
    widen(tn, D); sm[tn] = dict(cores_shifted=shift_type(T[tn], D))
    for b, w in zip(T[tn].get("buses") or [], keep):
        if w is not None: b["window_um"] = w      # N/S windows keep their die position (NW origin fixed, NE grows left)
    for p in raw["partitions"]:
        if p["type"] == tn and p.get("orient", "R0") == "MY": p["origin_um"] = [r4(p["origin_um"][0] - D), p["origin_um"][1]]
# q_sm3: grow on the local W (spb) side keeping the array in the local frame -> street on the local E (root/vsN) side
widen("q_sm3", D); sm["q_sm3"] = dict(cores_shifted=0)
for b in T["q_sm3"].get("buses") or []:
    if b.get("window_um") and b.get("face") in ("N", "S"): b["window_um"] = [r4(b["window_um"][0] + D), r4(b["window_um"][1] + D)]
for p in raw["partitions"]:
    if p["type"] == "q_sm3" and p.get("orient", "R0") == "R0": p["origin_um"] = [r4(p["origin_um"][0] - D), p["origin_um"][1]]
# NOTE q_sm3 local W is the spb side for both instances: NW R0 origin moves -D; NE MY origin fixed (grows to the right).
# spb0..2: lose D on each side; spt0..2: lose D on the SM side
ko_carry = None
for tn in ("q_spb0", "q_spb1", "q_spb2"):
    t = T[tn]
    if tn == "q_spb0":
        ko = t["clock"]["keepouts_um"]
        ko_carry = [[r4(T["q_sm2"]["outline_um"][0] - D), k[1], r4(T["q_sm2"]["outline_um"][0] - D + min(D, k[2]) - k[0]) if k[0] < D else 0, k[3]] for k in ko if k[0] < D - 1e-6]
    shift_type(t, -D, split=(t["outline_um"][0] / 2, -2 * D)); widen(tn, -2 * D)
    if tn == "q_spb0":
        t["clock"]["keepouts_um"] = [[max(0.0, k[0]), k[1], k[2], k[3]] for k in t["clock"]["keepouts_um"]]
    for p in raw["partitions"]:
        if p["type"] == tn: p["origin_um"] = [r4(p["origin_um"][0] + D), p["origin_um"][1]]
# carried keepout strip: die x [old spb W edge, +D) -> q_sm2 local [W'-D, W'] (same for MY by symmetry)
Wsm2 = T["q_sm2"]["outline_um"][0]
carry = [[r4(Wsm2 - D), k[1], r4(Wsm2), k[3]] for k in [[0, 0, 0, 1113.64]]] if ko_carry else []
if ko_carry:
    orig = [k for k in json.load(open(SRC / "die_plan.json"))["partition_types"]["q_spb0"]["clock"]["keepouts_um"] if k[0] < D - 1e-6]
    carry = [[r4(Wsm2 - (D - k[0])), k[1], r4(Wsm2), k[3]] for k in orig]
    T["q_sm2"]["clock"].setdefault("keepouts_um", []).extend(carry)
rep["spb0_keepout_carried_to_q_sm2"] = carry
for tn in ("q_spt0", "q_spt1", "q_spt2"):
    shift_type(T[tn], -D); widen(tn, -D)
    for p in raw["partitions"]:
        if p["type"] == tn and p.get("orient", "R0") == "R0": p["origin_um"] = [r4(p["origin_um"][0] + D), p["origin_um"][1]]
rep["sm_widen"] = dict(d=D, types=sm, bounds={tn: bounds_issues(tn) for tn in ("q_sm0", "q_sm2", "q_sm3", "q_spb0", "q_spb1", "q_spb2", "q_spt0", "q_spt1", "q_spt2")},
                       outlines={tn: T[tn]["outline_um"] for tn in ("q_sm0", "q_sm2", "q_sm3", "q_spb0", "q_spt0")})
# die.io rect of the spb0 PHYs must still sit in its partition
io_chk = []
for io in (raw["die"].get("io") or []):
    if io.get("part") in parts and io.get("rect_um"):
        p = parts[io["part"]]; W, H = T[p["type"]]["outline_um"]; x0, y0 = p["origin_um"]; r = io["rect_um"]
        io_chk.append(dict(io=io["name"], inside=bool(r[0] >= x0 - 1e-6 and r[2] <= x0 + W + 1e-6 and r[1] >= y0 - 1e-6 and r[3] <= y0 + H + 1e-6)))
rep["io_inside"] = [c for c in io_chk if not c["inside"]] or "all inside"

# ---------------- (b) L12 (+ mirror L12m) re-route root -> b101 -> hub
P_ = {p["id"]: p for p in raw["ports"]}
rep["L12"] = {}
WW = OPT.get("l12_win_w", 499.584)
REGS = OPT.get("l12_regs", [[721.44, 552.084], [721.44, 900.0], [640.0, 1200.0], [480.0, 1430.0]])
for lid, bpart, btype, hub in (("L12", "NW_b101", "q_b101_nw", "NW_hub"), ("L12m", "NE_b101", "q_b101", "NE_hub")):
    lane = next(l for l in raw["lanes"] if l["id"] == lid)
    old_nat = dict(raw["latency"]["lanes"][lid])
    bt = T[btype]; slot = next(s for s in bt["ft_slots"] if s["name"] == "L12x1")
    slot["out_face"] = "N"; slot["regs_um"] = [list(q) for q in REGS]; slot["stations"] = len(REGS)
    slot["note"] = "DIE-HBM C20: L12 re-routed root->b101->hub (COORD 20:21 ruling b): E in, N out to the hub S face; " + slot.get("note", "")
    for k in ("bit_sites_um", "bit_site_cell_um"): slot.pop(k, None)
    pb = parts[bpart]; x0 = pb["origin_um"][0]; Wb = bt["outline_um"][0]
    llo = round(((Wb - WW) / 2) / 0.048) * 0.048; lhi = llo + WW
    if pb.get("orient", "R0") == "MY": llo, lhi = Wb - lhi, Wb - llo
    lo = r4(x0 + llo)
    p1, p2 = lane["ports"][1], lane["ports"][2]
    P_[p1].update(dst={"part": hub, "bus": "L12_i"}, face="N", window_um=[lo, r4(lo + WW)], layers=["M7", "M5"])
    raw["ports"] = [p for p in raw["ports"] if p["id"] != p2]
    lane["ports"] = lane["ports"][:2]
    lane["note"] = lane.get("note", "") + " | DIE-HBM C20: root->b101->hub (b101 N face -> hub S face), su31 no longer crossed"
    lane["_old_nat"] = old_nat
    rep["L12"][lid] = dict(old=old_nat, window=P_[p1]["window_um"], b101_regs=REGS)
su31 = T["q_su31"]
su31["ft_slots"] = [s for s in su31["ft_slots"] if s["name"] != "L12x2"]
su31["buses"] = [b for b in su31.get("buses") or [] if b["name"] not in ("L12x2_i", "L12x2_o")]

# ---------------- (c) REPACK delta (C17g outline growth + vms_glue E cap)
rp = OPT.get("repack")
rep["repack"] = "not given"
if rp and Path(rp).is_file():
    dl = json.load(open(rp)); dl = dl.get("entries", dl) if isinstance(dl, dict) else dl
    done = []
    for e in dl:
        t = T[e["type"]]; c = next((c for c in t["hard_cores"] if c["inst"] == e["inst"]), None)
        if c is None: done.append(dict(e=e["inst"], err="inst not found")); continue
        ox, oy = c["origin_um"]; nx, ny = e.get("new_origin") or c["origin_um"]
        c["origin_um"] = [r4(nx), r4(ny)]
        if e.get("new_outline"): c["outline_um"] = list(e["new_outline"])
        if e.get("new_pins_file"):
            src = Path(e["new_pins_file"]); dst = OUT / "cores" / src.name
            if src.is_file(): shutil.copy2(src, dst); c["pins_file"] = "cores/" + src.name
        for tp in (t.get("clock") or {}).get("taps") or []:
            if str(tp.get("name", "")).split(".")[0] == e["inst"] and tp.get("xy"):
                if e.get("new_tap_xy"): tp["xy"] = list(e["new_tap_xy"])
                else: tp["xy"] = [r4(tp["xy"][0] + nx - ox), r4(tp["xy"][1] + ny - oy)]
        c["note"] = c.get("note", "") + " | DIE-HBM C20: C17g outline growth re-pack (REPACK sub-lane)"
        done.append(dict(type=e["type"], inst=e["inst"]))
    rep["repack"] = dict(applied=len([d for d in done if "err" not in d]), errors=[d for d in done if "err" in d])

# ---------------- (d) 12.2a1 in-core island slices
isl = OPT.get("islands")
rep["core_islands"] = "not given"
if isl and Path(isl).is_file():
    ci = json.load(open(isl))
    mesh = raw["clock"].setdefault("mesh", {})
    mesh.setdefault("core_islands", {}).update(ci)
    rep["core_islands"] = dict(modules=len(ci))

# ---------------- (e) region map
rg = OPT.get("regions")
if rg and Path(rg).is_file():
    R = json.load(open(rg)); pr = R.get("partition_region") or R.get("part_region") or {}
    miss = [p for p in parts if p not in pr]
    feed = OPT.get("feed", {"ROOT": None, "NW": "ROOT", "NE": "ROOT", "TOP": "ROOT"})
    off = []
    for p in raw["ports"]:
        a, b = p["src"]["part"], p["dst"]["part"]
        if a in pr and b in pr and pr[a] != pr[b] and feed.get(pr[a]) != pr[b] and feed.get(pr[b]) != pr[a]:
            off.append(dict(port=p["id"], src=a, dst=b, regions=[pr[a], pr[b]], width=p["width"]))
    xing = [p["id"] for p in raw["ports"] if p["src"]["part"] in pr and p["dst"]["part"] in pr and pr[p["src"]["part"]] != pr[p["dst"]["part"]]]
    out = dict(source=rg, partition_region=pr, feed_tree_parent=feed, unmapped=miss, crossings=len(xing),
               crossing_bits=sum(P_[i]["width"] for i in xing if i in P_), off_feed=off,
               off_feed_bits=sum(o["width"] for o in off),
               note="12.13: the crossing graph must be the feed tree; off-feed crossings are re-timed as hop chains through ROOT (LOCALITY v2 'hop' mode) until re-cut")
    (OUT / "regions_c20.json").write_text(json.dumps(out, indent=1))
    rep["regions"] = dict(n=len(set(pr.values())), unmapped=len(miss), crossings=len(xing), off_feed=len(off), off_feed_bits=out["off_feed_bits"])

# ---------------- (f) station relax (C19 method, die frame), then report stations in cores
sys.path.insert(0, str(REPO / "tools/die_plan"))
def tf(p, x, y):
    W = T[p["type"]]["outline_um"][0]; ox, oy = p["origin_um"]
    return (ox + x, oy + y) if p.get("orient", "R0") == "R0" else (ox + W - x, oy + y)
def itf(p, X, Y):
    W = T[p["type"]]["outline_um"][0]; ox, oy = p["origin_um"]
    return (X - ox, Y - oy) if p.get("orient", "R0") == "R0" else (ox + W - X, Y - oy)
DR = []
for p in raw["partitions"]:
    for c in T[p["type"]].get("hard_cores") or []:
        a = tf(p, *c["origin_um"]); b = tf(p, c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
        DR.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), p["name"] + "/" + c["inst"]))
def inside(q, m=0.0): return [r for r in DR if r[0] - m < q[0] < r[2] + m and r[1] - m < q[1] < r[3] + m]
inst_of = {}
for p in raw["partitions"]: inst_of.setdefault(p["type"], []).append(p)
HALO, MAXHOP = 4.32, 400.0
relaxed, failed = [], []
for tn, ps in inst_of.items():
    t = T[tn]; W, H = t["outline_um"]
    for s in t.get("ft_slots") or []:
        regs = s.get("regs_um") or []
        for i, loc in enumerate(regs):
            p0 = next((p for p in ps if inside(tf(p, *loc))), None)
            if p0 is None: continue
            r = inside(tf(p0, *loc))[0]; P0 = tf(p0, *loc)
            cands = [(r[0] - HALO, P0[1]), (r[2] + HALO, P0[1]), (P0[0], r[1] - HALO), (P0[0], r[3] + HALO)]
            cands += [(e, f) for e in (r[0] - HALO, r[2] + HALO) for f in (r[1] - HALO, r[3] + HALO)]
            best = None
            for Q in cands:
                q = itf(p0, *Q); q = (r4(q[0]), r4(q[1]))
                if not (0 <= q[0] <= W and 0 <= q[1] <= H): continue
                if any(inside(tf(p, *q), HALO * 0.5) for p in ps): continue
                nb = [regs[j] for j in (i - 1, i + 1) if 0 <= j < len(regs)]
                if any(abs(q[0] - b[0]) + abs(q[1] - b[1]) > MAXHOP for b in nb): continue
                dd = abs(q[0] - loc[0]) + abs(q[1] - loc[1])
                if best is None or dd < best[0]: best = (dd, q)
            if best:
                relaxed.append(dict(type=tn, slot=s["name"], i=i, core=r[4], frm=list(loc), to=list(best[1]))); regs[i] = list(best[1])
            else:
                failed.append(dict(type=tn, slot=s["name"], i=i, core=r[4], at=list(loc)))
rep["stations_relaxed"] = relaxed; rep["stations_failed_in_core"] = failed
# port geometry reconciliation: where both ends declare a type window and they now differ, the end in a type this
# event did not reshape follows the reshaped end (same die window, same face; delta applied in that type's frame)
import schema as SC
CHG = {"q_sm0", "q_sm2", "q_sm3", "q_spb0", "q_spb1", "q_spb2", "q_spt0", "q_spt1", "q_spt2"}
Pl = SC.Plan(raw, OUT / "die_plan.json")
recon, unres = [], []
for pr in raw["ports"]:
    if "window_um" in pr and "face" in pr: continue
    try:
        gs, gd = Pl.port_geom_from(pr, "src"), Pl.port_geom_from(pr, "dst")
    except Exception:
        continue
    if not gs or not gd or (gs[0] == gd[0] and abs(gs[1][0] - gd[1][0]) < 1e-6 and abs(gs[1][1] - gd[1][1]) < 1e-6): continue
    ts, td = parts[pr["src"]["part"]]["type"], parts[pr["dst"]["part"]]["type"]
    side, ref, mov = ("dst", gs, gd) if td not in CHG else (("src", gd, gs) if ts not in CHG else (None, None, None))
    if side is None: unres.append(pr["id"]); continue
    part = pr[side]["part"]; t = T[parts[part]["type"]]; bus = pr[side]["bus"]
    dd = ref[1][0] - mov[1][0]
    if parts[part].get("orient", "R0") in ("MY", "R180") and ref[0] in ("N", "S"): dd = -dd
    hit = False
    for b in t.get("buses") or []:
        if b["name"] == bus and b.get("window_um"): b["window_um"] = [r4(b["window_um"][0] + dd), r4(b["window_um"][1] + dd)]; hit = True
    for s_ in t.get("ft_slots") or []:
        for sfx, wk in (("_i", "in_window_um"), ("_o", "out_window_um")):
            if bus == s_["name"] + sfx and s_.get(wk): s_[wk] = [r4(s_[wk][0] + dd), r4(s_[wk][1] + dd)]; hit = True
    (recon if hit else unres).append(dict(port=pr["id"], moved=f"{part}.{bus}", d=r4(dd)) if hit else pr["id"])
rep["ports_reconciled"] = recon; rep["ports_unresolved"] = unres
# latency: keep L12 at its C19 cycle count (no RTL change) via fixed_cycles; refresh the table from Plan.lane_latency
import schema as SC
for lane in raw["lanes"]:
    if "_old_nat" in lane:
        old_nat = lane.pop("_old_nat"); lane["fixed_cycles"] = 0
        Pl = SC.Plan(raw, OUT / "die_plan.json")
        nat = Pl.lane_natural(lane["id"])["cycles"]
        lane["fixed_cycles"] = max(0, int(old_nat["cycles"]) - nat - int(old_nat.get("pad", 0)))
Pl = SC.Plan(raw, OUT / "die_plan.json")
diffs = {}
for lid in Pl.lanes:
    new = Pl.lane_latency(lid); old = raw["latency"]["lanes"].get(lid)
    if old is None or any(old.get(k) != new.get(k) for k in ("cycles", "stations", "boundary", "faces", "fixed", "pad")):
        diffs[lid] = dict(old=old, new=new)
    raw["latency"]["lanes"][lid] = dict(new, param=(old or {}).get("param", f"LAT_{lid}"))
rep["latency_changed"] = {k: (v["old"] or {}).get("cycles") != v["new"]["cycles"] for k, v in diffs.items()}
raw["die"]["label"] = "C20 = C19 + DIE-HBM re-plan event (SM street widen, L12 re-route, C17g re-pack, islands, region map) | " + raw["die"].get("label", "")
(OUT / "die_plan.json").write_text(json.dumps(raw, indent=1))
for f in SRC.iterdir():
    if f.is_file() and not (OUT / f.name).exists() and f.suffix == ".json" and f.name != "die_plan.json":
        shutil.copy2(f, OUT / f.name)
(OUT / "die_plan.sha256").write_text(hashlib.sha256((OUT / "die_plan.json").read_bytes()).hexdigest() + "\n")
(OUT / "c20_event_report.json").write_text(json.dumps(rep, indent=1, default=str))
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in rep.items()}, indent=0, default=str)[:3000])
