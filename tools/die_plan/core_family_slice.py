#!/usr/bin/env python3
"""ONE scripted 12.3 core-latency path for a core FAMILY (S81-CORE-LAT-R13; COORD RULING S81-CORE-LAT-R12; OWNER 10-27
type reduction + automated work; METHODOLOGY 12.2a1 / 12.3 / 12.8 a-d1).

  placed sink census -> tree plan -> 12.3 plan slice (planned tree, centre entry, in-core islands) -> geometry checks
  -> render, for every member core of a family, with the FAMILY TEMPLATE's parameters (no per-core hand tuning).

Stages (all deterministic, plan model only; no measured timing input, no residual tools):
  census  : OpenROAD (docker, memory cap) dumps the placed clock sinks of the core's own trial kit (3_place.odb, current
            RTL) with the 12.8a centre entry (outline centre), and the legal-site/PG description of its floorplan ODB.
  plan    : equal-count H partition entry -> W/E -> 2 islands per side (= the 4 in-core islands, 12.2a1) -> family
            leaf levels chosen from the sink count and the family leaf target; every edge = its own SHORTEST legal maze
            path (no length padding / meander, COORD 18:5x); long leaves split into equal-count siblings on the same
            driver (same stage count); 12.8 d1 plan-computed sizing (BUFx8..x24 envelope) under the R7 NLDM chain,
            then (if the uf_phys3 fit is given) the R9 uf_phys3 coordinate descent.
  slice   : tools/die_plan/core_plan_to_infra.py (legal row sites, PG obstructions, --band info, --ndr per family).
  check   : automated geometry gates (GEOM-REVIEW-10 form): every leg <= 1.10 x Manhattan of its endpoints, leaf
            spread <= 40 um, every census sink in exactly one leaf, equal stage count on every root->sink path, driver
            displacement <= 2 um, plan TT/FF window <= 20, leaf slew <= 80; plan latency vs 250/202.5 +-20 = INFO.
  render  : PNG of sinks + legs by level + drivers at the converted legal sites.
usage:
  core_family_slice.py run --family FAMILIES.json --core MODULE --kit KITDIR --work DIR [--fit FIT --libdir DIR]
  core_family_slice.py family --family FAMILIES.json --name FAMILY --kits DIR --work DIR   (every member with a 3_place)
PLAN MODEL numbers are UNCHECKED until a build measures them."""
import argparse, collections, gzip, json, math, os, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "results" / "core_lat_r7_1026"))
sys.path.insert(0, str(REPO / "results" / "core_lat_r8_1026"))
import core_infra_htree as H          # noqa: E402
import l0r_r7_model as M7             # noqa: E402  (R7 NLDM predictor + 12.8 d1 sizing)
import l0r_r8_model as M8             # noqa: E402  (split_long_leaves, leaf_spread, leaf_mst)

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
ENV = ['BUFx24_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx12_ASAP7_75t_R', 'BUFx10_ASAP7_75t_R',
       'BUFx8_ASAP7_75t_R']
GATES = dict(leg_detour_max=1.10, leaf_spread_um=40.0, disp_um=2.0, window_ps=20.0, slew_ps=80.0)
BAND = {"TT": (250.0, 20.0), "FF": (202.5, 20.0)}
_exact = H.exact_points


def _straight(mz, a, b, T, k):
    """every leg = its own shortest legal maze path (no padding to the level maximum; COORD 18:5x meander ruling)."""
    return _exact(mz, a, b, mz.md(a, b), k)


H.exact_points = _straight
M8.H.exact_points = _straight


# ------------------------------------------------------------------ long-leaf split (generic; replaces the R8 helper)
NAME_POOL = "pqrstuvwxyzabcdefghijklmnoPQRSTUVWXYZABCDEFGHIJKLMNO"


def farthest_clusters(pts, limit):
    """deterministic farthest-point (k-centre) clustering, k grows until every part's centroid->farthest-sink
    Manhattan spread <= limit; parts may hold unequal counts (joint_nldm_plan load balance + d1 sizing absorb it).
    Isolated face/pin/reset registers get their own small leaf instead of stretching a big one (structure, no wire)."""
    def spread(g):
        cx = sum(p[0] for p in g) / len(g); cy = sum(p[1] for p in g) / len(g)
        return max(abs(p[0] - cx) + abs(p[1] - cy) for p in g)
    for k in range(2, 60):
        seeds = [min(pts, key=lambda p: (p[0], p[1]))]
        while len(seeds) < k:
            seeds.append(max(pts, key=lambda p: (min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in seeds), p[0], p[1])))
        for _ in range(12):
            grp = [[] for _ in seeds]
            for p in pts:
                grp[min(range(len(seeds)), key=lambda i: (abs(p[0] - seeds[i][0]) + abs(p[1] - seeds[i][1]), i))].append(p)
            grp = [g for g in grp if g]
            seeds = [(sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)) for g in grp]
        if max(spread(g) for g in grp) <= limit:
            return grp
    return grp


def split_long_leaves(P, limit_um):
    """every leaf whose driver->farthest-sink spread exceeds limit_um becomes k sibling leaves on the SAME parent
    driver (same level, same stage count, natural leg length); leaf driver at each part's centroid; names keep the
    level length (letters from NAME_POOL) so level bookkeeping is unchanged.  Every sink stays in exactly one leaf."""
    mz = P['mz']; out = []; sp = M8.leaf_spread(P); node = {n[0]: n for n in P['nodes']}
    taken = {n[0] for n in P['nodes']}
    for u in sorted(sp):
        if sp[u] <= limit_um:
            continue
        sinks = P['leafsinks'][u]; br = node[u][1]; drv = node[br][1]; hub = node[br][2]
        parts = farthest_clusters(sinks, limit_um)
        cells = [mz.cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))) for g in parts]
        free = [u[:-1] + ch for ch in NAME_POOL if u[:-1] + ch not in taken]
        if len(free) < len(parts) - 1:
            raise SystemExit('split_long_leaves: name pool exhausted at %s (%d parts)' % (u, len(parts)))
        names = [u] + free[:len(parts) - 1]; taken.update(names)
        nsib = sum(1 for n in P['nodes'] if n[4] == 'branch' and n[1] == drv)
        for i, (nm, g, c) in enumerate(zip(names, parts, cells)):
            if i == 0:
                bcell = node[br][2]
                P['nodes'] = [(n[0], n[1], c if n[0] == u else n[2], n[3], n[4]) for n in P['nodes']]
                P['wires'] = [w for w in P['wires'] if w['edge'] != u]
            else:
                bcell = mz.cell((mz.xy(hub)[0], mz.xy(hub)[1] + (nsib + i - 1) * 1.08))
                P['nodes'].append((nm + '_br', drv, bcell, H.BIG, 'branch'))
                P['nodes'].append((nm, nm + '_br', c, H.BIG, 'leaf'))
            P['wires'].append(dict(level=len(P['splits']), edge=nm, segs=[mz.md(bcell, c)], cells=[mz.path(bcell, c)]))
            P['leafsinks'][nm] = g
        out.append(dict(leaf=u, spread_um=sp[u], parts=len(parts), part_sinks=[len(g) for g in parts]))
    order, seen, rest = [], set(), list(P['nodes'])
    while rest:
        nxt = [n for n in rest if n[1] is None or n[1] in seen]
        if not nxt:
            raise SystemExit('cycle in plan nodes')
        for n in nxt:
            order.append(n); seen.add(n[0])
        rest = [n for n in rest if n[0] not in seen]
    P['nodes'] = order
    return out


def reassign_nearest(P, cap):
    """structure, no wire: every sink goes to the NEAREST leaf driver (Manhattan, deterministic, capacity cap sinks per
    leaf, farthest-first), so isolated face/pin/reset registers join the closest leaf instead of stretching the
    equal-count partition leaf they fell into.  Leaf drivers then move to their new centroid (legal cell)."""
    mz = P['mz']; pos = {n[0]: mz.xy(n[2]) for n in P['nodes'] if n[4] == 'leaf'}
    allp = [s_ for v in P['leafsinks'].values() for s_ in v]; leaves = sorted(pos)
    d = lambda s_, u: abs(s_[0] - pos[u][0]) + abs(s_[1] - pos[u][1])
    order = sorted(allp, key=lambda s_: (-min(d(s_, u) for u in leaves), s_[2], s_[3]))
    new = {u: [] for u in leaves}
    for s_ in order:
        for u in sorted(leaves, key=lambda u: (d(s_, u), u)):
            if len(new[u]) < cap: new[u].append(s_); break
    moved = sum(1 for u in leaves for s_ in new[u] if s_ not in set(map(tuple, P['leafsinks'][u])))
    for u in leaves:
        if not new[u]: new[u] = P['leafsinks'][u][:1]   # never empty (cannot happen with cap >= mean)
    P['leafsinks'] = new
    cell = {u: mz.cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))) for u, g in new.items()}
    P['nodes'] = [(n[0], n[1], cell[n[0]] if n[0] in cell else n[2], n[3], n[4]) for n in P['nodes']]
    node = {n[0]: n for n in P['nodes']}
    for w in P['wires']:
        if w['edge'] in cell:
            k = len(w['segs']); b = node[w['edge'] + ('_br' if k == 1 else '_r%d' % (k - 2))][2]
            w['segs'][-1] = mz.md(b, cell[w['edge']]); w['cells'][-1] = mz.path(b, cell[w['edge']])
    return dict(moved=moved, cap=cap)


# ------------------------------------------------------------------ census
def docker_or(kit, tcl, env, log):
    kit = Path(kit).resolve()
    e = []
    for k, v in env.items():
        e += ["-e", "%s=%s" % (k, v)]
    cmd = ["docker", "run", "--rm", "--memory=8g", "--memory-swap=8g", "-v", "%s:/work" % kit, "-v", "%s:/tcl:ro" % HERE] + e + \
          [IMAGE, "bash", "-lc", "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /tcl/%s" % tcl]
    with open(log, "w") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
    if rc:
        raise SystemExit("census: %s rc %d (see %s)" % (tcl, rc, log))


def census(kit, work):
    kit = Path(kit).resolve(); work.mkdir(parents=True, exist_ok=True)
    base = sorted(kit.glob("run/results/asap7/*/base"))
    if not base or not (base[-1] / "3_place.odb").is_file():
        raise SystemExit("census: %s has no 3_place.odb (submit the trial census kit with GOAL=place first)" % kit)
    rel = base[-1].relative_to(kit)
    ctx = json.loads((kit / "boundary_guard_context.json").read_text())
    clk = ctx["clock_ports"][0]
    if not (work / "geo.txt").is_file():
        docker_or(kit, "core_family_geo.tcl", dict(ODB="/work/%s/3_place.odb" % rel, OUT="/work/r13_geo.txt", CLK=clk), work / "geo.log")
        (kit / "r13_geo.txt").replace(work / "geo.txt")
    if not (work / "sites.txt").is_file():
        docker_or(kit, "core_family_sites.tcl", dict(ODB="/work/%s/2_floorplan.odb" % rel, OUT="/work/r13_sites.txt"), work / "sites.log")
        (kit / "r13_sites.txt").replace(work / "sites.txt")
    return clk


# ------------------------------------------------------------------ family template -> splits
def splits_for(n, fam):
    """2 (W/E) x 2 (islands per side) x leaf levels; leaf levels a<=b from the family menu so that leaves ~ n/target."""
    tgt = fam.get("leaf_target", 48); menu = fam.get("menu", [1, 2, 4, 8])
    want = max(1.0, n / (4.0 * tgt)); best = None
    for a in menu:
        for b in menu:
            if a > b: continue
            v = (abs(math.log(a * b / want)), a + b)
            if best is None or v < best[0]: best = (v, (a, b))
    a, b = best[1]
    sp = [2, 2] + [x for x in (a, b) if x > 1]
    return sp if len(sp) > 2 else [2, 2, 1]


def plan(geo, fam, libtt, libff, name):
    sinks = sum(1 for l in open(geo) if l.startswith("SINK"))
    sp = splits_for(sinks, fam)
    M7.BUFS = list(ENV)
    P = H.plan(str(geo), sp, fam.get("smax", 70.0), [])
    rea = reassign_nearest(P, int(fam.get("reassign_cap", 1.5) * max(len(v) for v in P["leafsinks"].values()))) if fam.get("reassign") else None
    split = split_long_leaves(P, fam.get("leaf_limit", 35.0))
    kr, kc = map(float, fam.get("rc", "0.8,0.9").split(","))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    cells = sorted(set(ENV + [H.REP, H.BIG]))
    libs = {"TT": H.lib_cells(libtt, cells), "FF": H.lib_cells(libff, cells)}
    M7.apply_masters(P, {"rep": "BUFx24_ASAP7_75t_R"})
    wc = {l: fam.get("wire", "std") for l in range(1, len(sp) + 2)}
    sized = M7.size_d1(P, libs, r, c, wc)
    res, st = M7.model_x(P, libs, r, c, wc)
    par = {n[0]: n[1] for n in P["nodes"]}; depths = set()
    for n in P["nodes"]:
        if n[4] == "leaf":
            d = 1; u = n[0]
            while par[u]: u = par[u]; d += 1
            depths.add(d)
    mz = P["mz"]

    def corners(cs):
        pts = [mz.xy(x) for x in cs]; kp = [pts[0]]
        for i in range(1, len(pts) - 1):
            if (pts[i][0] - kp[-1][0]) * (pts[i + 1][1] - pts[i][1]) != (pts[i][1] - kp[-1][1]) * (pts[i + 1][0] - pts[i][0]): kp.append(pts[i])
        return kp + [pts[-1]]
    spread = M8.leaf_spread(P)
    islands = sorted({mz.xy(P["site"][g]) for g in P["site"] if len(g) == 2})
    rec = dict(name=name, family=fam["name"], splits=",".join(map(str, sp)), smax=fam.get("smax", 70.0), wire=fam.get("wire", "std"),
               sinks=sinks, split_leaves=split, reassign=rea, level_len_um=[round(x, 2) for x in P["T"]],
               repeaters_per_edge=[k - 1 for k in P["K"]], stages=sorted(depths), n_cells=len(P["nodes"]),
               sized_masters={"%s:%s" % k: v for k, v in sorted(sized.items())},
               frozen_masters={n[0]: n[3] for n in P["nodes"]}, TT=res["TT"], FF=res["FF"],
               entry=mz.xy(P["ent"]), islands_xy=islands, core=list(mz.core), maze_g_um=mz.G,
               nodes_xy=[(n[0], n[1], mz.xy(n[2]), n[3], n[4]) for n in P["nodes"]],
               wire_paths=[dict(level=w["level"], edge=w["edge"], segs=[round(x, 2) for x in w["segs"]],
                                paths=[corners(cs) for cs in w["cells"]]) for w in P["wires"]],
               leaf_members={u: len(v) for u, v in P["leafsinks"].items()},
               leaf_sinks={u: ["%s/%s" % (s[2], s[3]) for s in v] for u, v in P["leafsinks"].items()},
               leaf_spread_um=spread, leaf_mst_um=M8.leaf_mst(P),
               leaf_spread_max=dict(all=max(spread.values()), main=max(spread.values()), strip=0.0,
                                    n_gt_40=sum(v > 40 for v in spread.values()), top=sorted(spread.items(), key=lambda kv: -kv[1])[:8]),
               model="R7 NLDM+Elmore chain + 12.8 d1 (core_family_slice); PLAN MODEL, UNCHECKED")
    return rec


# ------------------------------------------------------------------ checks
def checks(rec, slice_, geo):
    out = {}; fails = []
    # (1) every leg <= 1.10 x Manhattan of its own endpoints
    worst = 0.0; nover = 0; nleg = 0
    for w in rec["wire_paths"]:
        for seg, pts in zip(w["segs"], w["paths"]):
            a, b = pts[0], pts[-1]; man = abs(a[0] - b[0]) + abs(a[1] - b[1]); nleg += 1
            if man > 1.0:
                q = seg / man; worst = max(worst, q); nover += q > GATES["leg_detour_max"] + 1e-9
    out["legs"] = dict(n=nleg, over_1p10=nover, worst_ratio=round(worst, 3))
    if nover: fails.append("legs over 1.10x Manhattan: %d" % nover)
    sp = rec["leaf_spread_um"]; out["leaf_spread"] = dict(max=max(sp.values()), n_gt_40=sum(v > GATES["leaf_spread_um"] for v in sp.values()))
    if out["leaf_spread"]["n_gt_40"]: fails.append("leaves over 40 um spread: %d" % out["leaf_spread"]["n_gt_40"])
    cen = {"%s/%s" % (l.split()[4], l.split()[5]) for l in open(geo) if l.startswith("SINK")}
    got = collections.Counter(s for v in rec["leaf_sinks"].values() for s in v)
    out["sinks"] = dict(census=len(cen), planned=len(got), missing=len(cen - set(got)), dup=sum(1 for v in got.values() if v > 1),
                        extra=len(set(got) - cen))
    if out["sinks"]["missing"] or out["sinks"]["dup"] or out["sinks"]["extra"]: fails.append("sink coverage %s" % out["sinks"])
    out["stages"] = rec["stages"]
    if len(rec["stages"]) != 1: fails.append("unequal stage count %s" % rec["stages"])
    for c in ("TT", "FF"):
        m, tol = BAND[c]; x = rec[c]
        out[c] = dict(mean=x["mean"], window=x["window"], leaf_out_slew_max=x["leaf_out_slew_max"],
                      band_info="IN" if abs(x["mean"] - m) <= tol else "OUT")
        if x["window"] > GATES["window_ps"]: fails.append("%s window %.1f > 20" % (c, x["window"]))
        if x["leaf_out_slew_max"] > GATES["slew_ps"]: fails.append("%s leaf slew %.1f > 80" % (c, x["leaf_out_slew_max"]))
    if slice_ is not None:
        disp = slice_["plan_conversion"]["displacement_um"]["max"]
        out["disp_max_um"] = disp
        out["pg_clearance"] = slice_["plan_conversion"].get("trunk_pg_clearance", {}).get("verdict")
        if disp > GATES["disp_um"]: fails.append("driver displacement %.2f > 2" % disp)
        if out["pg_clearance"] not in (None, "PASS"): fails.append("trunk PG clearance %s" % out["pg_clearance"])
    nmac = sum(1 for l in open(geo) if l.startswith("MACRO"))
    out["macro_clock_pins"] = nmac
    if nmac: fails.append("%d macro clock pins: family template has no macro (early-tap, v5.0) leaf yet" % nmac)
    out["verdict"] = "FAIL" if fails else "PASS"; out["fails"] = fails
    out["scope"] = "automated geometry gates on the PLAN (GEOM-REVIEW-10 form); latency numbers PLAN MODEL, UNCHECKED"
    return out


# ------------------------------------------------------------------ render
def render(geo, rec, slice_, out_png):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    S = [l.split() for l in open(geo) if l.startswith("SINK")]
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.scatter([float(s[1]) for s in S], [float(s[2]) for s in S], s=0.3, c="0.72", label="%d placed sinks" % len(S))
    col = {1: "tab:red", 2: "tab:blue", 3: "tab:green", 4: "tab:orange", 5: "tab:purple"}
    lv = collections.defaultdict(list)
    for w in rec["wire_paths"]:
        lv[w["level"]].append(sum(w["segs"]))
        for pts in w["paths"]:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], c=col.get(w["level"], "k"), lw=1.6 if w["level"] <= 2 else 0.8)
    for l in sorted(lv):
        ax.plot([], [], c=col.get(l, "k"), lw=2, label="L%d legs %d: %.1f-%.1f um" % (l, len(lv[l]), min(lv[l]), max(lv[l])))
    pos = {n[0]: n[2] for n in rec["nodes_xy"]}
    if slice_:
        for n in slice_["core_tree"]["nodes"]:
            pos[n["name"].split("mp_ck_", 1)[-1]] = n["xy_um"]
    for kind, mk, c in (("branch", "s", "k"), ("rep", "D", "tab:brown"), ("leaf", "o", "tab:cyan")):
        ns = [n for n in rec["nodes_xy"] if n[4] == kind and n[0] in pos]
        ax.scatter([pos[n[0]][0] for n in ns], [pos[n[0]][1] for n in ns], s=8, marker=mk, c=c, label="%s drivers %d" % (kind, len(ns)), zorder=3)
    ix = rec["islands_xy"]
    ax.scatter([p[0] for p in ix], [p[1] for p in ix], s=160, facecolors="none", edgecolors="magenta", lw=2, label="in-core islands %d" % len(ix), zorder=4)
    ax.plot(*rec["entry"], "k*", ms=16, label="centre entry (12.8a)", zorder=5)
    cr = rec["core"]; ax.set_xlim(cr[0] - 3, cr[2] + 3); ax.set_ylim(cr[1] - 3, cr[3] + 3); ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
    t, f = rec["TT"], rec["FF"]
    ax.set_title("%s [%s] splits %s, %s stages, leaf spread max %.1f um\nPLAN MODEL TT %.1f w%.1f / FF %.1f w%.1f (UNCHECKED)"
                 % (rec["name"], rec["family"], rec["splits"], rec["stages"], rec["leaf_spread_max"]["all"], t["mean"], t["window"], f["mean"], f["window"]), fontsize=9)
    fig.savefig(out_png, dpi=110); plt.close(fig)


# ------------------------------------------------------------------ driver
def run_core(fams, core, kit, work, a):
    fam = next(f for f in fams["families"] if core in f["members"])
    work = Path(work) / core; work.mkdir(parents=True, exist_ok=True)
    clk = census(kit, work)
    geo = work / "geo.txt"
    rec = plan(geo, fam, a.libtt, a.libff, "%s_r13_%s" % (core, fam["name"]))
    pj = work / "plan.json"; pj.write_text(json.dumps([rec]))
    if a.fit:
        r = subprocess.run([sys.executable, str(REPO / "results/core_lat_r9_1026/l0r_r9_d1.py"), str(pj), str(geo), a.libdir, a.fit,
                            str(work / "plan_d1.json"), "--steps", str(a.d1_steps)], capture_output=True, text=True)
        (work / "d1.log").write_text(r.stdout + r.stderr)
        if r.returncode == 0:
            rec2 = json.loads((work / "plan_d1.json").read_text())[0]
            # refresh the NLDM numbers with the d1 masters (same chain the checks read)
            rec2["d1_from"] = "uf_phys3 v1 coordinate descent (R9)"; rec = rec2; pj = work / "plan_d1.json"
    slice_dir = work / "slice"; slice_dir.mkdir(exist_ok=True)
    cmd = [sys.executable, str(HERE / "core_plan_to_infra.py"), str(pj), "--sites", str(work / "sites.txt"), "--module", core,
           "--clock-port", clk, "--band", "info", "--ndr", "none" if fam.get("wire", "std") == "std" else "2,2",
           "--out", str(slice_dir / ("%s.json" % core))]
    r = subprocess.run(cmd, capture_output=True, text=True); (work / "convert.log").write_text(r.stdout + r.stderr)
    sl = json.loads((slice_dir / ("%s.json" % core)).read_text()) if r.returncode == 0 else None
    ck = checks(rec, sl, geo)
    if sl is None: ck["verdict"] = "FAIL"; ck["fails"].append("converter rc %d: %s" % (r.returncode, (r.stdout + r.stderr).strip()[-300:]))
    (work / "checks.json").write_text(json.dumps(ck, indent=1))
    render(geo, rec, sl, work / ("%s_r13.png" % core))
    line = dict(core=core, family=fam["name"], splits=rec["splits"], sinks=rec["sinks"], cells=rec["n_cells"], stages=rec["stages"],
                TT=rec["TT"]["mean"], TTw=rec["TT"]["window"], FF=rec["FF"]["mean"], FFw=rec["FF"]["window"], verdict=ck["verdict"], fails=ck["fails"])
    print("CORE_FAMILY_SLICE", json.dumps(line), flush=True)
    return line


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=("run", "family"))
    ap.add_argument("--family", required=True); ap.add_argument("--core"); ap.add_argument("--kit"); ap.add_argument("--name")
    ap.add_argument("--kits", help="dir holding <module>_<suffix> trial census kits"); ap.add_argument("--suffix", default="c13")
    ap.add_argument("--work", required=True)
    ap.add_argument("--libtt", required=True); ap.add_argument("--libff", required=True)
    ap.add_argument("--fit", default=None); ap.add_argument("--libdir", default=None); ap.add_argument("--d1-steps", type=int, default=60)
    a = ap.parse_args()
    fams = json.loads(Path(a.family).read_text())
    if a.mode == "run":
        run_core(fams, a.core, a.kit, a.work, a); return
    fam = next(f for f in fams["families"] if f["name"] == a.name); rows = []
    for m in fam["members"]:
        kit = Path(a.kits) / ("%s_%s" % (fam.get("kit_name", {}).get(m, m), a.suffix))
        try:
            rows.append(run_core(fams, m, kit, a.work, a))
        except SystemExit as e:
            rows.append(dict(core=m, family=fam["name"], verdict="NO-CENSUS", fails=[str(e)])); print("CORE_FAMILY_SLICE", json.dumps(rows[-1]))
    Path(a.work, "family_%s.json" % fam["name"]).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
