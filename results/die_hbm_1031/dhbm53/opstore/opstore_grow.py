#!/usr/bin/env python3
"""DIE-HBM-53 10-31: opstore_a / opstore_b q_b113 grow (GEOM-93 AUTO-GEOM FAIL PLAN: r2r, 12-um macro channels, clock
reach; COORD 12:19 -> DIE-HBM-53) as a die-local one-block plan delta (DIE-HBM-30-O opstore_a_v1.py method).

    opstore_grow.py SRC_PLAN_DIR OUT_PLAN_DIR VARIANT(A|B) LEF_DIR

 Both variants use free q_b113 area only (no other core moves, partition outline unchanged):
  opstore_a: origin (1080, 941.76) kept, height 483.84 -> 609.12 (top 1550.88 = ctl top, 21.6 below the partition N edge).
  opstore_b: top-right corner kept, width 760.32 -> 976.32 (A) / 868.32 (B), grows W into the empty x < 656.64 area.
  A: opstore_a 3 macro columns (60-um column channels / W-E bands), 2 bands (6 + 5 rows); opstore_b 4 columns, 57-um channels.
  B: opstore_a 4 columns as now (12.1-um channels), 4 bands of 2 rows (56-um logic channels); opstore_b 872.64 (origin on the 8.64 lattice), 4 columns, 36-um channels.
 Pin tables: same pins / faces / layers / order, the along-face coordinate re-spread over the new face span (spacing never
 reduced).  Clock entry: new centre on the 4.32 lattice (island in a macro channel, checked).  Stations touching the two
 cores: endpoints follow the cores (count kept), FF homes re-solved by station_resite.py afterwards.  core_macros: static
 grids written as S.json for core_macros_fix.py --static (it validates channels / outline / LEF sizes).
"""
import json, os, re, subprocess, sys, hashlib, math
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-49/physical/die_plan/hbm")
import core_macros_fix as F

SRC, OUT, VAR, LEF = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
assert VAR in ("A", "B") and not OUT.exists(), OUT
subprocess.check_call(["cp", "-al", str(SRC), str(OUT)])
SZ = F.lef_sizes(LEF)
def put(rel, obj):
    p = OUT / rel; tmp = p.with_name(p.name + ".tmp"); tmp.write_text(json.dumps(obj, indent=1)); os.replace(tmp, p)
P = json.loads((OUT / "die_plan.json").read_text())
CM = json.loads((OUT / "core_macros.json").read_text())["cores"]
CE = json.loads((OUT / "clock_entries.json").read_text())
TYPES = ["q_b113", "q_b113__physical_v1"]
OA, OB = "u_sfucore_Q_opstore_a", "u_sfucore_Q_opstore_b"
MA, MB = "ot_hgi_sfu_core_split3__opstore_a", "ot_hgi_sfu_core_split3__opstore_b"
G, RES, O4 = 0.048, 0.024, 0.012
NEW = {OA: dict(outline=[760.32, 609.12], origin=[1080.0, 941.76]),
       OB: dict(outline=[976.32 if VAR == "A" else 872.64, 691.2])}
NEW[OB]["origin"] = [round(656.64 + 760.32 - NEW[OB]["outline"][0], 3), 216.0]
rep = {"lane": "DIE-HBM-53", "variant": VAR, "src": str(SRC), "new": NEW, "types": {}, "pin_tables": {}}

# ---- 1. pin tables re-spread (DIE-HBM-30-O method) ------------------------------------------------------------------
h0 = {h["inst"]: h for h in P["partition_types"]["q_b113"]["hard_cores"]}
def face(p, W, H):
    if p["y"] < 1: return "S"
    if p["y"] > H - 1: return "N"
    if p["x"] < 1: return "W"
    if p["x"] > W - 1: return "E"
    return "I"     # interior pin (the plan centre clock pin): moved to the new entry in step 3
NEWPF = {}
for inst in (OA, OB):
    OW, OH = h0[inst]["outline_um"]; NW, NH = NEW[inst]["outline"]
    old = json.loads((OUT / h0[inst]["pins_file"]).read_text())
    new = [dict(p) for p in old]; fstat = {}
    for f in "NSEW":
        idx = [i for i, p in enumerate(old) if face(p, OW, OH) == f]
        if not idx: continue
        along = "x" if f in "NS" else "y"
        so, sn = (OW, NW) if f in "NS" else (OH, NH)
        ks = sorted(idx, key=lambda i: (old[i][along], old[i]["layer"]))
        k = [round((old[i][along] - RES) / G) for i in ks]
        assert all(abs(RES + kk * G - old[i][along]) < 1e-6 for kk, i in zip(k, ks)), (inst, f)
        lo, hi = k[0], k[-1]
        hi_new = round((sn - (so - old[ks[-1]][along]) - RES) / G)
        s = (hi_new - lo) / max(1, hi - lo) if sn != so else 1.0
        out, prev, prevk = [], None, None
        for kk in k:
            v = lo + round((kk - lo) * s)
            if prev is not None: v = max(v, prev + (kk - prevk))
            out.append(v); prev, prevk = v, kk
        assert out[-1] <= hi_new + 1e-9, (inst, f, out[-1], hi_new)
        for i, v in zip(ks, out):
            new[i][along] = round(RES + v * G, 3)
            if f == "E": new[i]["x"] = round(NW - (OW - old[i]["x"]), 3)
            if f == "N": new[i]["y"] = round(NH - (OH - old[i]["y"]), 3)
        fstat[f] = dict(pins=len(ks), scale=round(s, 4), span_new=[new[ks[0]][along], new[ks[-1]][along]])
    assert len({(p["layer"], p["x"], p["y"]) for p in new}) == len(new)
    mod = h0[inst]["module"]
    NEWPF[inst] = f"cores/{mod}__{NW}x{NH}__dhbm53{VAR}.json"
    (OUT / NEWPF[inst]).write_text(json.dumps(new, indent=1))
    rep["pin_tables"][inst] = dict(old=h0[inst]["pins_file"], new=NEWPF[inst], pins=len(new), faces=fstat)

# ---- 2. static macro grids ----------------------------------------------------------------------------------------
yu = lambda v: round(O4 + math.ceil(round((v - O4) / G, 6)) * G, 3)
xg = lambda v: round(round(v / G) * G, 3)
def grid(names, W, H, cols, bands, ch_x=None):
    """names in (col, row) order list of lists per column (bottom->top); bands = rows per band; equal channels."""
    mw, mh = SZ[names[0][0][1]]
    nb = len(bands); rows = sum(bands)
    hb = [b * mh + (b - 1) * G for b in bands]
    chy = (H - sum(hb)) / (nb + 1)
    ys, y = [], chy
    for b, hgt in zip(bands, hb):
        for r in range(b): ys.append(yu(y + r * (mh + G)))
        y += hgt + chy
    chx = (W - cols * mw) / (cols + 1) if ch_x is None else ch_x
    x0 = (W - cols * mw - (cols - 1) * chx) / 2
    xs = [xg(x0 + c * (mw + chx)) for c in range(cols)]
    out = []
    for c, col in enumerate(names):
        for r, (n, m) in enumerate(col):
            out.append(dict(name=n, master=m, origin_um=[xs[c], ys[r]], orient="R0"))
    return out, dict(chx=round(chx, 3), chy=round(chy, 3), xs=xs, ys=ys)
S, gi = {}, {}
for mod, inst in ((MA, OA), (MB, OB)):
    W, H = NEW[inst]["outline"]
    ms = CM[mod]["macros"]
    cxs = sorted({round(m["rect_um"][0], 3) for m in ms}); rys = sorted({round(m["rect_um"][1], 3) for m in ms})
    cell = {(cxs.index(round(m["rect_um"][0], 3)), rys.index(round(m["rect_um"][1], 3))): (m["name"], m["master"]) for m in ms}
    nr = len(rys)
    if mod == MA and VAR == "A":    # 3 columns x (6 + 5) rows: old row-major order kept (group 0 then group 1)
        order = [cell[(c, r)] for r in range(nr) for c in range(4)]
        cols = [[] for _ in range(3)]
        for i, nm in enumerate(order): cols[i % 3].append(nm)
        g, info = grid(cols, W, H, 3, [6, 5])
    elif mod == MA:                 # B: 4 columns x 4 bands of 2 rows (same bank -> column / row)
        g, info = grid([[cell[(c, r)] for r in range(nr)] for c in range(4)], W, H, 4, [2, 2, 2, 2], ch_x=12.096)
    else:                           # opstore_b: same 3 bands of 4 rows, columns spread
        g, info = grid([[cell[(c, r)] for r in range(nr)] for c in range(4)], W, H, 4, [4, 4, 4])
    gi[mod] = info
    S[mod] = dict(basis=f"DIE-HBM-53 10-31 variant {VAR} (GEOM-93 opstore FAIL PLAN, COORD 12:19): q_b113 grow "
                  f"{CM[mod]['outline_um']} -> {[W, H]}, static grid cols {len(info['xs'])} col channel {info['chx']} "
                  f"band channel {info['chy']}; same names/masters ({len(g)} x {g[0]['master']})", outline_um=[W, H], macros=g)
json.dump(S, open(OUT / "S_opstore.json", "w"), indent=1)
CMJ = json.loads((OUT / "core_macros.json").read_text())
for mod, inst in ((MA, OA), (MB, OB)):
    old = CMJ["cores"][mod]
    CMJ["cores"][mod] = dict(status="UNKNOWN", outline_um=NEW[inst]["outline"], why=f"DIE-HBM-53 {VAR} grow: re-sited by core_macros_fix --static",
                             previous={k: v for k, v in old.items() if k != "macros"})   # --static re-sites UNKNOWN cores only
put("core_macros.json", CMJ)
rep["grids"] = gi

# ---- 3. clock entries: centre on the 4.32 lattice inside a channel -----------------------------------------------
def in_macro(isl, ms):
    for m in ms:
        w, h = SZ[m["master"]]; x, y = m["origin_um"]
        if not (x + w <= isl[0] - 4.32 or x >= isl[2] + 4.32 or y + h <= isl[1] - 4.32 or y >= isl[3] + 4.32): return True
    return False
CEN = {}
for mod, inst in ((MA, OA), (MB, OB)):
    W, H = NEW[inst]["outline"]
    best = None
    for dx in range(-6, 7):
        for dy in range(-12, 13):
            x = round((round(W / 2 / 4.32) + dx) * 4.32, 2); y = round((round(H / 2 / 4.32) + dy) * 4.32, 2)
            isl = [round(x - 4.32, 2), round(y - 4.32, 2), round(x + 4.32, 2), round(y + 4.32, 2)]
            if not in_macro(isl, S[mod]["macros"]):
                d = abs(x - W / 2) + abs(y - H / 2)
                if best is None or d < best[0]: best = (d, x, y, isl)
    assert best, mod
    CEN[mod] = best[1:]
n_ce = 0
for blk in CE.values():
    for e in (blk.values() if isinstance(blk, dict) else []):
        if isinstance(e, dict) and e.get("module") in CEN:
            x, y, isl = CEN[e["module"]]; e["xy_um"] = [x, y]; e["island_um"] = isl
            e["source"] = e.get("source", "") + f" | DIE-HBM-53 {VAR}: nearest 4.32-lattice point to the grown outline centre clear of macros (+4.32 halo)"
            n_ce += 1
rep["clock_entries"] = {k: v for k, v in CEN.items()}; rep["clock_entries_updated"] = n_ce
for mod, inst in ((MA, OA), (MB, OB)):
    pt = json.loads((OUT / NEWPF[inst]).read_text()); W, H = NEW[inst]["outline"]; mv = []
    for p in pt:
        if 1 <= p["x"] <= W - 1 and 1 <= p["y"] <= H - 1:
            p["x"] = round(RES + round((CEN[mod][0] - RES) / G) * G, 3); p["y"] = CEN[mod][1]; mv.append(p["name"])
    (OUT / NEWPF[inst]).write_text(json.dumps(pt, indent=1)); rep["pin_tables"][inst]["interior_moved"] = mv

# ---- 4. die_plan types ---------------------------------------------------------------------------------------------
def xf(h, x, y):
    W, H = h["outline_um"]; o = h.get("orient", "R0"); tx, ty = h.get("track_offset_um", [0, 0])
    if o in ("MY", "R180"): x = W - x
    if o in ("MX", "R180"): y = H - y
    return [h["origin_um"][0] + tx + x, h["origin_um"][1] + ty + y]
def rect(h): return [h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]]
def clamp(r, p):
    x = min(max(p[0], r[0]), r[2]); y = min(max(p[1], r[1]), r[3])
    if r[0] < x < r[2] and r[1] < y < r[3]:
        d = [(x - r[0], "W"), (r[2] - x, "E"), (y - r[1], "S"), (r[3] - y, "N")]; e = min(d)[1]
        x = r[0] if e == "W" else r[2] if e == "E" else x; y = r[1] if e == "S" else r[3] if e == "N" else y
    return [round(x, 3), round(y, 3)]
port = lambda n: re.sub(r"\[\d+\]$", "", n)
for tn in TYPES:
    T = P["partition_types"][tn]; hc = {h["inst"]: h for h in T["hard_cores"]}; tr = rep["types"][tn] = {}
    for inst in (OA, OB):
        h = hc[inst]; tr[inst + "_before"] = dict(origin=h["origin_um"], outline=h["outline_um"])
        h["origin_um"] = NEW[inst]["origin"]; h["outline_um"] = NEW[inst]["outline"]; h["pins_file"] = NEWPF[inst]
        h["note"] = h.get("note", "") + f" | DIE-HBM-53 {VAR}: q_b113 grow {tr[inst + '_before']['outline']} -> {NEW[inst]['outline']} (GEOM-93 FAIL PLAN)"
    W, H = T["outline_um"]; rs = {i: rect(h) for i, h in hc.items()}; errs = []
    for i in rs:
        r = rs[i]
        if r[0] < 0 or r[1] < 0 or r[2] > W + 1e-6 or r[3] > H + 1e-6: errs.append(f"{i} outside")
        for j in rs:
            if i < j:
                q = rs[j]; dx = max(q[0] - r[2], r[0] - q[2]); dy = max(q[1] - r[3], r[1] - q[3])
                if max(dx, dy) < 17.28 - 1e-6: errs.append(f"{i}/{j} gap {max(dx, dy):.3f}")
    assert not errs, errs
    tr["core_rects"] = {i: [round(v, 3) for v in r] for i, r in rs.items()}
    for t in T["clock"]["taps"]:
        for inst, mod in ((OA, MA), (OB, MB)):
            if t["name"] == inst + ".clk":
                t0 = list(t["xy"]); t["xy"] = [round(v, 3) for v in xf(hc[inst], *CEN[mod][:2])]; tr["tap_" + inst] = [t0, t["xy"]]
    pins = {i: json.loads((OUT / hc[i]["pins_file"]).read_text()) for i in (OA, OB)}
    moved = 0
    for s in T["internal_stations"]:
        li, _, lp = s["launch"].partition("."); ci, _, cp = s["capture"].partition(".")
        if li not in (OA, OB) and ci not in (OA, OB): continue
        f0, t0 = list(s["from_um"]), list(s["to_um"])
        if li in (OA, OB):
            ps = [xf(hc[li], p["x"], p["y"]) for p in pins[li] if port(p["name"]) == lp]
            assert ps, s["launch"]
            s["from_um"] = clamp(rect(hc[li]), [sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)])
        if ci in (OA, OB):
            ps = [xf(hc[ci], p["x"], p["y"]) for p in pins[ci] if cp and port(p["name"]) == cp]
            s["to_um"] = clamp(rect(hc[ci]), [sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)] if ps else s["from_um"])
        if (f0, t0) != (s["from_um"], s["to_um"]):
            moved += 1; s["note"] = s.get("note", "") + f" | DIE-HBM-53 {VAR}: endpoints follow the opstore grow (count kept)"
    tr["station_endpoints_moved"] = moved
P["note"] = f"DIE-HBM-53 {VAR} opstore_a/b q_b113 grow <- " + P["note"]
put("die_plan.json", P); put("clock_entries.json", CE)
rep["out_sha256"] = hashlib.sha256((OUT / "die_plan.json").read_bytes()).hexdigest()[:12]
(OUT / "opstore_grow_report.json").write_text(json.dumps(rep, indent=1))
print(json.dumps({k: rep[k] for k in ("new", "grids", "clock_entries", "clock_entries_updated", "out_sha256")}))
for tn in TYPES: print(tn, {k: v for k, v in rep["types"][tn].items() if k != "core_rects"})
