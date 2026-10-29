#!/usr/bin/env python3
"""NUMBER-CHECK-KV-2: independent recompute of the DIE-KV-27/28 die STA headline numbers from the raw inputs.
Own code (no die_sta_related import).  Published inputs taken as given: spice_edge INV factors, AOCV table json,
register characterisation (regchar, spot-checked separately in OpenSTA), plan geometry via schema.Plan.to_die."""
import json, math, sys, hashlib, re, itertools
from collections import defaultdict
from pathlib import Path

W = Path(sys.argv[1])            # workdir
K27 = Path("/srv/opentallas-scratch2/claude/die-kv-27-1029")
PLAN = Path("/srv/opentallas-scratch2/claude/die-kv-26-1029/plan_e26a.json")
BIND = Path("/srv/opentallas-scratch2/claude/codex-kv-25-1029/native6/native_bind.json")
VIEWS = {f"kv3_head_eighth_e{n}": Path(f"/srv/opentallas-scratch2/claude/autopilot/closed/qwen_kvsys/kv3_head_eighth_e{n}__3e7fccd216/view/kv3_head_eighth_e{n}") for n in (1, 2, 5, 6)}
sys.path.insert(0, str(W / "main/tools/die_plan"))
import schema as S                                   # geometry only (to_die)

T = 833.333
UNC_S, UNC_H = 60.0, 25.0
CAL = {"TT": (0.9324, 1.0241), "FF": (0.938, 1.0487)}     # spice_edge INV late / early
LAT = {"TT": 250.0, "FF": 202.5}
DDF = {"TT": dict(logic=0.10, wire=0.05), "FF": dict(logic=0.08, wire=0.04)}
AOCV = json.loads((W / "main/tools/die_plan/clk_aocv_table_g021.json").read_text())["clock_aocv"]
plan = json.loads(PLAN.read_text())
bind = json.loads(BIND.read_text())
out = {}


def raw_rows(c):
    R = defaultdict(dict)
    for ln in (K27 / f"edges/arr_{c}.txt").read_text().splitlines():
        f = ln.split()
        if f and f[0] in "TFNM" and len(f[0]) == 1:
            R[f[0]][f[1]] = (float(f[2]), float(f[3]))
    return R


def load(c):
    J = json.loads((K27 / f"proofE/tap_arrivals_{c}.json").read_text())
    R = raw_rows(c)
    # identity raw readout -> proof taps
    bad = 0
    for t in J["taps"]:
        r, f = R["T"][t["port"]], R["F"][t["port"]]
        bad += abs(r[0] - t["late_ps"]) > 1e-6 or abs(r[1] - t["early_ps"]) > 1e-6
        bad += abs(f[0] - t["fall_late_ps"]) > 1e-6 or abs(f[1] - t["fall_early_ps"]) > 1e-6
    nvals = {round(v, 4) for k in "NM" for x in R[k].values() for v in x}
    nmiss = sum(1 for k in ("node_late_ps", "node_early_ps", "node_fall_late_ps", "node_fall_early_ps")
                for n, v in J[k].items() if v is not None and n != "h" and round(v, 4) not in nvals)
    fl, fe = CAL[c]
    taps = {}
    for t in J["taps"]:
        x = dict(t)
        for lk, ek in (("late_ps", "early_ps"), ("fall_late_ps", "fall_early_ps")):
            L = t[lk] * fl
            x[lk], x[ek] = L, min(t[ek] * fe, L)
        taps[t["port"]] = x
    nl = {k: v * fl for k, v in J["node_late_ps"].items() if v is not None}
    ne = {k: min(v * fe, nl[k]) for k, v in J["node_early_ps"].items() if v is not None and k in nl}
    nfl = {k: v * fl for k, v in J["node_fall_late_ps"].items() if v is not None}
    nfe = {k: min(v * fe, nfl[k]) for k, v in J["node_fall_early_ps"].items() if v is not None and k in nfl}
    rng = {k: max(0.0, nl[k] - ne[k]) for k in J["cppr_node_range_ps"] if k in nl and k in ne}
    for k, v in J["cppr_node_range_ps"].items():
        if k not in rng:
            rng[k] = v * fe
    meta = dict(nl=nl, ne=ne, nfl=nfl, nfe=nfe, rng=rng, stages=J["node_stages"], xy=J["node_xy_um"])
    return taps, meta, dict(raw_tap_mismatch=bad, node_values_not_in_raw=nmiss, taps=len(taps))


def lca(A, B):
    x, y = A["tree_path"], B["tree_path"]
    n = 0
    while n < min(len(x), len(y)) and x[n] == y[n]:
        n += 1
    return x[:max(1, n)]


def credit(rng, node, la, ea, lc, ec):
    c = node
    while c not in rng and len(c) > 1:
        c = c[:-1]
    return min(max(0.0, rng.get(c, 0.0)), max(0.0, la - ea), max(0.0, lc - ec))


# ---------- own AOCV (from the table json)
def var_units(n, rho):
    v = float(n)
    for l, r in enumerate(rho, 1):
        if l >= n:
            break
        v += 2.0 * (n - l) * r
    return max(v, 0.0)


def rfrac(c, stages):
    var = mu = 0.0
    for cls, n in stages.items():
        if n <= 0:
            continue
        q = AOCV["classes"][cls][c]
        var += (q["mu_cell_ps"] * q["s_cell"]) ** 2 * var_units(n, q.get("rho", []))
        mu += n * q["mu_cell_ps"]
    return 0.0 if mu <= 0 else AOCV["k_sigma"] * math.sqrt(var) / mu


def make_ocv(c, taps, meta, region):
    Bc = AOCV["classes"]["B"][c]
    fc = AOCV["classes"]["Ainv"][c]["cell_share"]
    lat = LAT[c]
    nB = max(1, round(lat / Bc["mu_stage_ps"]))
    g = AOCV["systematic"]["g_per_mm"]
    nf = AOCV["net_flat"]
    dl = AOCV["droop"]["one_sided_late_frac"]

    def br(r, node, late):
        arr = (r["late_ps"] if late else r["early_ps"]) - (meta["nl"] if late else meta["ne"])[node]
        return (fc * arr + Bc["cell_share"] * lat, (1 - fc) * arr + (1 - Bc["cell_share"]) * lat,
                {"Ainv": int(r["stages_from_root"]) - int(meta["stages"][node]), "B": nB})

    def fn(a, b, check):
        A, B = taps[a], taps[b]
        node = lca(A, B)
        ra = region.get(a, A["cppr_node"] if A["cppr_node"] != "h" else None)
        rb = region.get(b, B["cppr_node"] if B["cppr_node"] != "h" else None)
        same = ra is not None and ra == rb
        pts = [A["xy_um"], B["xy_um"], meta["xy"][node]]
        d = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        ba, bb = br(A, node, check == "setup"), br(B, node, check != "setup")
        late, early = (ba, bb) if check == "setup" else (bb, ba)
        s = g * d / 1000.0 / 2.0
        fl = rfrac(c, late[2]) + s
        fe = rfrac(c, early[2]) + s
        return late[0] * (fl + (0.0 if same else dl)) + early[0] * fe + late[1] * (nf["late"] - 1) + early[1] * (1 - nf["early"])
    return fn


def interval(A, B, rng, ocv, a, b, edge="rise"):
    node = lca(A, B)
    la, ea, lc, ec = A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]
    if edge == "fall":
        lc, ec = B["fall_late_ps"], B["fall_early_ps"]
    cr = credit(rng, node, la, ea, lc, ec)
    lo, hi = ec - la + cr, lc - ea - cr
    os_, oh = ocv(a, b, "setup"), ocv(a, b, "hold")
    return lo - os_, hi + oh


def regchar(c):
    return json.loads((W / f"regchar/{c}.json").read_text())


# ---------- pairs (own)
def pairs_of(taps):
    by = defaultdict(list)
    for p, r in taps.items():
        if r.get("part") is not None:
            by[r["part"]].append(p)
    intra, seam, landed = [], [], []
    for part, tl in by.items():
        for a, b in itertools.permutations(sorted(tl), 2):
            if taps[a]["cppr_node"] == taps[b]["cppr_node"]:
                intra.append((a, b, part))
    conn = set()
    for pr in plan["ports"]:
        s, t = pr["src"]["part"], pr["dst"]["part"]
        if s != t and s in by and t in by:
            conn.add((s, t))
    for s, t in conn:
        for a in by[s]:
            for b in by[t]:
                (seam if taps[a]["cppr_node"] == taps[b]["cppr_node"] else landed).append((a, b, f"{s}->{t}"))
    return intra, seam, landed, by


def count_align(c, taps, meta, ocv, reg, landed):
    pr = {p: v["region"] for p, v in bind["parts"].items() if isinstance(v, dict) and v.get("region")}
    named, byreg = defaultdict(list), defaultdict(list)
    for pid, q in bind["ports"].items():
        if q.get("src_part") is not None and q.get("dst_part") is not None:
            named[(q["src_part"], q["dst_part"])].append(pid)
        byreg[(q["src"], q["dst"])].append(pid)
    iv, ush, unb = {}, {}, set()
    for a, b, _ in landed:
        A, B = taps[a], taps[b]
        own = named.get((A["part"], B["part"])) or byreg.get((pr[A["part"]], pr[B["part"]]))
        if not own:
            unb.add((pr[A["part"]], pr[B["part"]]))
            continue
        lo, hi = interval(A, B, meta["rng"], ocv, a, b)
        node = lca(A, B)
        u = max(A["late_ps"], B["late_ps"]) - meta["nl"].get(node, 0.0)
        for pid in own:
            o = iv.get(pid)
            iv[pid] = (lo, hi) if o is None else (min(o[0], lo), max(o[1], hi))
            ush[pid] = max(ush.get(pid, u), u)
    rows = []
    for pid, q in bind["ports"].items():
        if pid not in iv:
            rows.append((pid, None, None))
            continue
        dl, dh = iv[pid]
        lo, hi = q["L_lo_ps"] + dl - q["d_lo_ps"], q["L_hi_ps"] + dh - q["d_hi_ps"]
        dw = max(0.0, 0.05 * ush[pid] - float(q.get("wander_ps", 0.0)))
        lo, hi = lo - dw, hi + dw
        rows.append((pid, lo - 0.5 * T, (int(q["depth"]) - 0.5) * T - hi, q["src"] + "->" + q["dst"]))
    ok = [r for r in rows if r[1] is not None]
    wl = min(ok, key=lambda r: r[1])
    wh = min(ok, key=lambda r: r[2])
    below = sum(1 for r in ok if min(r[1], r[2]) < 100.0)
    guard = sum(1 for r in ok if r[2] - T / 8 < 0)
    # start ports: virtual retime taps on tree nodes
    real = [t for t in taps.values() if len(t["tree_path"]) > 1 and t.get("part") is not None]
    med = lambda v: sorted(v)[len(v) // 2]
    leg = (med([t["late_ps"] - meta["nl"][t["tree_path"][:-1]] for t in real]),
           med([t["early_ps"] - meta["ne"][t["tree_path"][:-1]] for t in real]),
           med([int(t["stages_from_root"]) - int(meta["stages"][t["tree_path"][:-1]]) for t in real]))
    fleg = (med([t["fall_late_ps"] - meta["nfl"][t["tree_path"][:-1]] for t in real if t["tree_path"][:-1] in meta["nfl"]]),
            med([t["fall_early_ps"] - meta["nfe"][t["tree_path"][:-1]] for t in real if t["tree_path"][:-1] in meta["nfe"]]))
    cqmin, cqmax = reg["clkq_min_nowire_ps"], reg["clkq_max_wire_ps"]
    srows = []
    for pid, q in sorted(bind["start_ports"].items()):
        ends = []
        for k in (q["launch"], q["capture"]):
            if k in taps:
                ends.append(k)
            elif k.startswith("__st__"):
                path = k[6:].split("@", 1)[0]
                if path not in meta["nl"]:
                    ends.append(None)
                    continue
                taps[k] = dict(port=k, part=None, cppr_node="h", tree_path=path, late_ps=meta["nl"][path] + leg[0],
                               early_ps=meta["ne"][path] + leg[1], stages_from_root=int(meta["stages"][path]) + leg[2],
                               xy_um=meta["xy"][path])
                if path in meta["nfl"]:
                    taps[k]["fall_late_ps"] = meta["nfl"][path] + fleg[0]
                    taps[k]["fall_early_ps"] = meta["nfe"][path] + fleg[1]
                ends.append(k)
            else:
                ends.append(None)
        rg = bind["regions"].get(q["dst"], {})
        edge = "fall" if rg.get("edge_fall") else "rise"
        if None in ends:
            srows.append((pid, None, rg.get("start_skew_limit_ps"), edge))
            continue
        lo, hi = interval(taps[ends[0]], taps[ends[1]], meta["rng"], ocv, ends[0], ends[1], edge)
        off = T / 2 if edge == "fall" else 0.0
        elo, ehi = lo - cqmax, hi - cqmin
        k = math.floor((elo - off) / T)
        dist = min(elo - (off + k * T), off + (k + 1) * T - ehi) if math.floor((ehi - off) / T) == k else -1.0
        ok_ = int(rg.get("sync_values", 1)) == 1 and dist >= 26.5
        srows.append((pid, dist, rg.get("start_skew_limit_ps"), edge, ok_, round(lo, 2), round(hi, 2)))
    for k in [k for k in taps if k.startswith("__st__")]:
        taps.pop(k)
    sfail = sum(1 for r in srows if r[1] is None or not r[4])
    lim = [r[2] for r in srows if r[2] is not None]
    over = sum(1 for r in srows if r[2] is not None and max(abs(cqmin), abs(cqmax)) > r[2])
    wd = min((r for r in srows if r[1] is not None), key=lambda r: r[1])
    return dict(crossings=len(rows), unbound=len(unb), no_taps=sum(1 for r in rows if r[1] is None),
                worst_lo=(wl[0], wl[3], round(wl[1], 3)), worst_hi=(wh[0], wh[3], round(wh[2], 3)),
                below_100=below, guard_fail=guard, start_rows=len(srows), start_fail=sfail,
                start_skew_clkq=(round(cqmin, 3), round(cqmax, 3)), start_limit_min=min(lim) if lim else None,
                start_rows_limit_below_clkq=over, start_worst_sync_dist=(wd[0][:60], round(wd[1], 3), wd[3]),
                start_fall_rows=sum(1 for r in srows if r[3] == "fall"), leg=leg, fleg=fleg)


# ---------- ETM parse (own)
def parse_lib(lib, load_ff=6.0):
    txt = Path(lib).read_text()
    pin = tt = grp = idx = None
    ck = {}
    outs, setups, holds = [], [], []
    num = lambda s: [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s)]
    for line in txt.splitlines():
        s = line.strip()
        m = re.match(r'pin\("([^"]+)"\)', s)
        if m:
            pin = m.group(1); continue
        if s.startswith("timing()"):
            tt = None; continue
        m = re.match(r"timing_type\s*:\s*(\w+)", s)
        if m:
            tt = m.group(1); continue
        m = re.match(r"(cell_rise|cell_fall|rise_constraint|fall_constraint)\b", s)
        if m:
            grp, idx = m.group(1), None; continue
        if s.startswith("index_1"):
            idx = num(s.split("(", 1)[1]); continue
        if s.startswith("values(") and grp:
            v = num(s[7:])
            if tt in ("min_clock_tree_path", "max_clock_tree_path"):
                ck[tt] = max(v) if tt.startswith("max") else min(v)
            elif tt == "rising_edge" and grp.startswith("cell_"):
                if idx and len(idx) == len(v):
                    # linear interp in load
                    if load_ff <= idx[0]:
                        x = v[0]
                    elif load_ff >= idx[-1]:
                        x = v[-1]
                    else:
                        i = next(i for i in range(1, len(idx)) if load_ff <= idx[i])
                        x = v[i - 1] + (load_ff - idx[i - 1]) / (idx[i] - idx[i - 1]) * (v[i] - v[i - 1])
                    outs.append((x, x))
                else:
                    outs.append((max(v), min(v)))
            elif tt == "setup_rising" and grp.endswith("constraint"):
                setups.append(max(v))
            elif tt == "hold_rising" and grp.endswith("constraint"):
                holds.append(max(v))
            grp = None
    return dict(clkq_max=max(o[0] for o in outs), clkq_min=min(o[1] for o in outs), setup=max(setups), hold=max(holds),
                ck=ck)


def timeclass(c, taps, meta, ocv, reg, plist, views, dd):
    res = dict(n=0, ws=None, wh=None, rv_ws=None, rv_wh=None, rv_n=0, rv_negh=0, unmeasured=0)
    def ddl(ma, mb):
        la = max(0.0, ma["clkq_max"] - ma["ck"].get("max_clock_tree_path", 0.0)) if ma["real"] else max(0.0, ma["clkq_max"])
        cb = max(0.0, mb["setup"] + mb["ck"].get("min_clock_tree_path", 0.0)) if mb["real"] else 0.0
        return dd["logic"] * (la + cb)
    for a, b, tag in plist:
        A, B = taps[a], taps[b]
        node = lca(A, B)
        la, ea, lc, ec = A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]
        cr = credit(meta["rng"], node, la, ea, lc, ec)
        os_, oh = ocv(a, b, "setup"), ocv(a, b, "hold")
        res["n"] += 1
        res["unmeasured"] += any(not m["real"] for m in views[a] + views[b])
        for ma in views[a]:
            for mb in views[b]:
                s = (ec + mb["lat"] + T - mb["setup"]) - (la + ma["lat"] + ma["clkq_max"]) - UNC_S + cr - ddl(ma, mb) - os_
                h = (ea + ma["lat"] + ma["clkq_min"]) - (lc + mb["lat"] + mb["hold"]) - UNC_H + cr - oh
                if res["ws"] is None or s < res["ws"][0]:
                    res["ws"] = (round(s, 3), a, b, ma["name"], mb["name"])
                if res["wh"] is None or h < res["wh"][0]:
                    res["wh"] = (round(h, 3), a, b, ma["name"], mb["name"])
                if ma["real"] or mb["real"]:
                    if res["rv_ws"] is None or s < res["rv_ws"][0]:
                        res["rv_ws"] = (round(s, 3), a, b, ma["name"], mb["name"])
                    if res["rv_wh"] is None or h < res["rv_wh"][0]:
                        res["rv_wh"] = (round(h, 3), a, b, ma["name"], mb["name"], round(lc - ea - cr, 3))
        rc = [(ma, mb) for ma in views[a] for mb in views[b] if ma["real"] or mb["real"]]
        if rc:
            res["rv_n"] += 1
            hmin = min((ea + ma["lat"] + ma["clkq_min"]) - (lc + mb["lat"] + mb["hold"]) - UNC_H + cr - oh for ma, mb in rc)
            res["rv_negh"] += hmin < 0
    return res


def main():
    P = S.Plan(plan)
    ptype = {x["name"]: x["type"] for x in plan["partitions"]}
    for c in ("TT", "FF"):
        taps, meta, ident = load(c)
        reg = regchar(c)
        region = json.loads((K27 / "proofE/droop_regions.json").read_text())
        ocv = make_ocv(c, taps, meta, region)
        intra, seam, landed, by = pairs_of(taps)
        r = dict(ident=ident, pairs=dict(intra=len(intra), seam=len(seam), landed=len(landed)))
        r["ca"] = count_align(c, taps, meta, ocv, reg, landed)
        # views: budget everywhere + core ETM models on the nearest tap of the partition (pins sha match)
        bud = dict(name="budget", real=False, lat=LAT[c], clkq_max=reg["clkq_max_wire_ps"], clkq_min=reg["clkq_min_nowire_ps"],
                   setup=reg["setup_ps"], hold=reg["hold_ps"], ck={})
        cm = {}
        for m, vd in VIEWS.items():
            e = parse_lib(vd / f"{m}_{c.lower()}.lib")
            prov = json.loads((vd / "provenance.json").read_text())
            cm[m] = dict(e, name="core:" + m, real=True, lat=0.0, sha=prov["kit"]["pins_sha256"], verdict=prov.get("verdict"))
        views = {p: [bud] for p in taps}
        nreal = defaultdict(int)
        nmis = defaultdict(int)
        for n, prt in P.parts.items():
            for h in P.types[prt["type"]].get("hard_cores", []) or []:
                if h["module"] not in cm:
                    continue
                pf = PLAN.parent / h["pins_file"] if h.get("pins_file") else None
                sha = hashlib.sha256(pf.read_bytes()).hexdigest() if pf and pf.exists() else None
                if sha != cm[h["module"]]["sha"]:
                    nmis[h["module"]] += 1
                    continue
                cx = float(h["origin_um"][0]) + float(h["outline_um"][0]) / 2
                cy = float(h["origin_um"][1]) + float(h["outline_um"][1]) / 2
                X, Y = P.to_die(n, (cx, cy))
                tl = by.get(n)
                if not tl:
                    continue
                port = min(tl, key=lambda p: (taps[p]["xy_um"][0] - X) ** 2 + (taps[p]["xy_um"][1] - Y) ** 2)
                if cm[h["module"]] not in views[port]:
                    views[port] = views[port] + [cm[h["module"]]]
                nreal[h["module"]] += 1
        r["views"] = dict(real_by_module=dict(nreal), sha_mismatch=dict(nmis),
                          taps_real=sum(1 for v in views.values() if any(m["real"] for m in v)),
                          etm={m: {k: v for k, v in x.items() if k in ("clkq_max", "clkq_min", "setup", "hold", "verdict")} for m, x in cm.items()})
        dd = DDF[c] if c == "TT" else DDF[c]
        for nm, pl in (("intra", intra), ("seam", seam)):
            r[nm] = timeclass(c, taps, meta, ocv, reg, pl, views, dd)
        # 12.19 missing-view labels
        lab_intra = sorted({ptype[taps[a]["part"]] for a, b, _ in intra} | {ptype[taps[b]["part"]] for a, b, _ in intra})
        lab_seam = sorted({ptype[taps[x]["part"]] for a, b, _ in seam for x in (a, b)})
        r["missing_types"] = dict(intra=len(lab_intra), seam=len(lab_seam), union=len(set(lab_intra) | set(lab_seam)),
                                  seam_only=sorted(set(lab_seam) - set(lab_intra)))
        out[c] = r
        print(c, json.dumps(r, default=str)[:6000], flush=True)
    (W / "nckv2_out.json").write_text(json.dumps(out, indent=1, default=str))


main()
