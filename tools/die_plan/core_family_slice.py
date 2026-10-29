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
import argparse, collections, gzip, json, math, os, re, subprocess, sys, tempfile
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
        # the leaf's own wire edge starts at its '_br' branch buffer; a repeated leaf edge (node[u][1] = u_rK) keeps
        # its repeater count on every part, so siblings hang on the branch's driver with the same stage count
        sinks = P['leafsinks'][u]; br = u + '_br'; drv = node[br][1]; hub = node[br][2]
        nseg = len(next(w['segs'] for w in P['wires'] if w['edge'] == u))
        if nseg > 1:
            reps = {u + '_r%d' % i for i in range(nseg - 1)}
            P['nodes'] = [n for n in P['nodes'] if n[0] not in reps]
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
            else:
                bcell = mz.cell((mz.xy(hub)[0], mz.xy(hub)[1] + (nsib + i - 1) * 1.08))
                P['nodes'].append((nm + '_br', drv, bcell, H.BIG, 'branch'))
            pts = H.exact_points(mz, bcell, c, mz.md(bcell, c), nseg) if nseg > 1 else []
            prev = nm + '_br'
            for j, q in enumerate(pts):
                P['nodes'].append((nm + '_r%d' % j, prev, q, H.REP, 'rep')); prev = nm + '_r%d' % j
            if i == 0:
                P['nodes'] = [(n[0], prev if n[0] == u else n[1], c if n[0] == u else n[2], n[3], n[4]) for n in P['nodes']]
                P['wires'] = [w for w in P['wires'] if w['edge'] != u]
            else:
                P['nodes'].append((nm, prev, c, H.BIG, 'leaf'))
            chain = [bcell] + pts + [c]
            P['wires'].append(dict(level=len(P['splits']), edge=nm, segs=[mz.md(chain[j], chain[j + 1]) for j in range(len(chain) - 1)],
                                   cells=[mz.path(chain[j], chain[j + 1]) for j in range(len(chain) - 1)]))
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
    # R14: a leaf that is nobody's nearest driver is REMOVED with its exclusive chain (prune_empty_leaves); the R13
    # fallback copied one of its old sinks back into it, so that sink sat in two leaves (gunit_l2, sstn_base566).
    P['leafsinks'] = new
    pruned = prune_empty_leaves(P)
    new = P['leafsinks']
    cell = {u: mz.cell((sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g))) for u, g in new.items()}
    P['nodes'] = [(n[0], n[1], cell[n[0]] if n[0] in cell else n[2], n[3], n[4]) for n in P['nodes']]
    node = {n[0]: n for n in P['nodes']}
    for w in P['wires']:
        if w['edge'] in cell:
            k = len(w['segs']); b = node[w['edge'] + ('_br' if k == 1 else '_r%d' % (k - 2))][2]
            w['segs'][-1] = mz.md(b, cell[w['edge']]); w['cells'][-1] = mz.path(b, cell[w['edge']])
    return dict(moved=moved, cap=cap, pruned=pruned)


def _edge_of(name):
    """plan node name -> its wire edge (T0123_br / T0123_r1 / T0123 -> T0123)."""
    m = re.match(r"(.*)_(br|r\d+)$", name)
    return m.group(1) if m else name


def prune_empty_leaves(P):
    """structure, no wire: a leaf left without sinks is REMOVED together with its exclusive driver chain (branch
    buffer, repeaters, wire edge, landing); any driver left without children is removed the same way (recursive).
    No sink is ever copied (each census sink stays in exactly one leaf) and no driver drives nothing; the surviving
    root->sink paths keep their stage count.  Returns the removed node names (sorted)."""
    empty = sorted(u for u, v in P['leafsinks'].items() if not v)
    if not empty:
        return []
    for u in empty:
        del P['leafsinks'][u]
    gone = set(empty)
    while True:
        alive = [n for n in P['nodes'] if n[0] not in gone]
        haskid = {n[1] for n in alive if n[1]}
        more = {n[0] for n in alive if n[4] not in ('entry', 'leaf') and n[0] not in haskid}
        if not more:
            break
        gone |= more
    P['nodes'] = [n for n in P['nodes'] if n[0] not in gone]
    live = {_edge_of(n[0]) for n in P['nodes']}
    P['wires'] = [w for w in P['wires'] if w['edge'] in live]
    if 'land' in P:
        P['land'] = {k: v for k, v in P['land'].items() if k not in gone and v[1] in live}
    return sorted(gone)


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


def clock_bterm_from_log(log, declared):
    """R14: the census tcl resolves the declared clock port to the placed ODB's BTerm (a 1-bit bus port `clk` is the
    BTerm `clk[0]`; bk_g, qbank_S) and prints DUMP_GEO_CLKPORT <bterm>; the slice names that exact BTerm."""
    got = re.findall(r"^DUMP_GEO_CLKPORT (\S+)\s*$", log, re.M)
    if len(got) != 1:
        raise SystemExit("census: clock port %s not resolved to one BTerm (%d DUMP_GEO_CLKPORT lines)" % (declared, len(got)))
    b = got[0]
    if b != declared and b != declared + "[0]":
        raise SystemExit("census: clock BTerm %s does not match declared port %s" % (b, declared))
    return b


def census(kit, work, gated=False):
    """gated (family icg_copies, CORES-EARLY-5): a separate census geo_gated.txt with GATED=1 (GATE lines + every gated
    sink tagged gate=<ICG>); the default geo.txt census is unchanged."""
    kit = Path(kit).resolve(); work.mkdir(parents=True, exist_ok=True)
    base = sorted(kit.glob("run/results/asap7/*/base"))
    if not base or not (base[-1] / "3_place.odb").is_file():
        raise SystemExit("census: %s has no 3_place.odb (submit the trial census kit with GOAL=place first)" % kit)
    rel = base[-1].relative_to(kit)
    ctx = json.loads((kit / "boundary_guard_context.json").read_text())
    clk = ctx["clock_ports"][0]
    if gated and not (work / "geo_gated.txt").is_file():
        docker_or(kit, "core_family_geo.tcl", dict(ODB="/work/%s/3_place.odb" % rel, OUT="/work/r13_geo_gated.txt", CLK=clk, GATED="1"),
                  work / "geo_gated.log")
        (kit / "r13_geo_gated.txt").replace(work / "geo_gated.txt")
    if not (work / "geo.txt").is_file():
        docker_or(kit, "core_family_geo.tcl", dict(ODB="/work/%s/3_place.odb" % rel, OUT="/work/r13_geo.txt", CLK=clk), work / "geo.log")
        (kit / "r13_geo.txt").replace(work / "geo.txt")
        (work / "clkport.txt").write_text(clock_bterm_from_log((work / "geo.log").read_text(), clk) + "\n")
    if (work / "clkport.txt").is_file():
        clk = (work / "clkport.txt").read_text().strip()
    if not (work / "sites.txt").is_file():
        docker_or(kit, "core_family_sites.tcl", dict(ODB="/work/%s/2_floorplan.odb" % rel, OUT="/work/r13_sites.txt"), work / "sites.log")
        (kit / "r13_sites.txt").replace(work / "sites.txt")
    return clk


# ------------------------------------------------------------------ 12.8c fixed entry trunk (R14)
TRUNK_MENU = ['BUFx8_ASAP7_75t_R', 'BUFx10_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx16f_ASAP7_75t_R', 'BUFx24_ASAP7_75t_R']
TRUNK_NMAX = 16


def add_entry_trunk(P, master, n):
    """12.8c: ONE designed fixed trunk at the entry of a shallow core: n identical buffers in series between the entry
    root and the root's children (the W/E branch buffers), on a straight column below the entry at 1.08 um pitch; the
    LAST stage sits next to the branch buffers (stubs <= 2.2 um), the root drives the first stage.  Same cell chain
    for every instance of the type; kind 'trunk' (never resized by d1 sizing); every root->sink path gains n stages."""
    if n <= 0:
        return []
    mz = P['mz']; ex, ey = mz.xy(P['ent'])
    names = ['K_r%d' % i for i in range(n)]
    tr = [(nm, 'root' if i == 0 else names[i - 1], mz.cell((ex, ey - 1.08 * (n - i) - 0.54)), master, 'trunk')
          for i, nm in enumerate(names)]
    out = []
    for nd in P['nodes']:
        if nd[1] == 'root':
            nd = (nd[0], names[-1], nd[2], nd[3], nd[4])
        out.append(nd)
        if nd[0] == 'root':
            out += tr
    P['nodes'] = out
    return names


def remove_entry_trunk(P):
    names = {n[0] for n in P['nodes'] if n[4] == 'trunk'}
    if not names:
        return
    last = [n[0] for n in P['nodes'] if n[4] == 'trunk'][-1]
    P['nodes'] = [(n[0], 'root' if n[1] == last else n[1], n[2], n[3], n[4]) for n in P['nodes'] if n[0] not in names]


def choose_entry_trunk(P, libs, r, c, wc, cal):
    """plan-computed trunk (12.8c + d1: deterministic, before the build).  cal = the core's own BUILT CTS insertion and
    the plan-model number of that same built slice (COORD RULING S81-CORE-LAT-R13: calibrate on the built CTS, not on
    the plan number): offset[c] = built[c] - plan[c]; for every (master, n) in TRUNK_MENU x 1..TRUNK_NMAX the predicted
    built latency = model(plan + trunk) + offset; pick min |TT - 250| + |FF - 202.5| (tie: fewer cells, smaller master)."""
    off = {k: float(cal["built_" + k]) - float(cal["plan_" + k]) for k in ("TT", "FF")}
    base, _ = M7.model_x(P, libs, r, c, wc)
    best = None
    for m in TRUNK_MENU:
        for n in range(1, TRUNK_NMAX + 1):
            add_entry_trunk(P, m, n)
            res, _ = M7.model_x(P, libs, r, c, wc)
            remove_entry_trunk(P)
            pred = {k: res[k]["mean"] + off[k] for k in ("TT", "FF")}
            err = abs(pred["TT"] - BAND["TT"][0]) + abs(pred["FF"] - BAND["FF"][0])
            key = (round(err, 1), n, TRUNK_MENU.index(m))
            if best is None or key < best[0]:
                best = (key, m, n, pred, {k: res[k]["mean"] for k in ("TT", "FF")})
    _, m, n, pred, mod = best
    add_entry_trunk(P, m, n)
    return dict(rule="12.8c fixed entry trunk, plan-computed (d1) from the core's own built CTS insertion (COORD RULING S81-CORE-LAT-R13)",
                master=m, stages=n, offset_ps={k: round(v, 2) for k, v in off.items()}, calibration=cal,
                model_no_trunk={k: base[k]["mean"] for k in ("TT", "FF")}, model_with_trunk=mod,
                predicted_built={k: round(v, 2) for k, v in pred.items()},
                predicted_band={k: ("IN" if abs(pred[k] - BAND[k][0]) <= BAND[k][1] else "OUT") for k in ("TT", "FF")},
                label="PLAN MODEL + one-build calibration, UNCHECKED until the trunk build is measured")


# ------------------------------------------------------------------ family template -> splits
def splits_for(n, fam):
    """2 (W/E) x 2 (islands per side) x leaf levels; leaf levels a<=b from the family menu so that leaves ~ n/target.
    A calibrated re-plan (replan_structure) passes its menu candidate as fam['splits_override']."""
    if fam.get("splits_override"):
        return list(fam["splits_override"])
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


_PLANS = {}   # plan name -> (P, libs, r, c, wire classes) of the last plan() call (refresh_after_d1)


def refresh_after_d1(rec0, rec):
    """S81-CORE-LAT-R20: after the R9 uf_phys3 d1 descent the plan carries NEW frozen masters, but the record kept the
    R7 NLDM numbers of the PRE-d1 masters -- the window/slew gates and the converter's model_qualification then judged
    a tree that is not the one being built (gunit_l2: gate R7 window 20.28/20.36 on pre-d1 masters vs 15.49/17.13 on the
    d1 masters it ships).  Re-evaluate the SAME R7 chain on the shipped masters; the pre-d1 numbers stay as info.
    Deterministic, plan-model only (12.8 d1), no measurement input."""
    P, libs, r, c, wc = _PLANS[rec0["name"]]
    fm = rec["frozen_masters"]
    miss = sorted(n[0] for n in P["nodes"] if n[0] not in fm)
    if miss:
        raise SystemExit("refresh_after_d1: d1 record lacks frozen masters for %s" % miss[:4])
    P["nodes"] = [(n[0], n[1], n[2], fm[n[0]], n[4]) for n in P["nodes"]]
    if sorted((n[0], n[3]) for n in P["nodes"]) != sorted((n[0], n[3]) for n in rec["nodes_xy"]):
        raise SystemExit("refresh_after_d1: d1 nodes_xy masters differ from frozen_masters")
    res, _ = M7.model_x(P, libs, r, c, wc)
    rec["model_pre_d1"] = {k: rec0[k] for k in ("TT", "FF")}
    calibrated = rec.get("d1_uf3", {}).get("prediction")
    if calibrated is not None:
        for corner in ("TT", "FF"):
            q = calibrated[corner]
            needed = {"mean", "window", "sink_min", "sink_max", "leaf_out_slew_max", "leaf_slew_in_max"}
            if needed - set(q) or q.get("model") != "uf_phys3 v1" or q.get("basis") != "GRT":
                raise SystemExit("refresh_after_d1: malformed calibrated prediction at " + corner)
        rec["model_r7_info"] = res
        rec["TT"], rec["FF"] = calibrated["TT"], calibrated["FF"]
        rec["model"] = "uf_phys3 v1 GRT, TT max-rise / FF min-rise-fall; SAME frozen masters and kernel as d1 (R21); R7 retained as info"
    else:
        rec["TT"], rec["FF"] = res["TT"], res["FF"]
        rec["model"] = rec0["model"] + "; R7 re-evaluated on the d1 (uf_phys3) masters (R20)"
    return rec


def plan(geo, fam, libtt, libff, name, trunk_cal=None):
    sinks = sum(1 for l in open(geo) if l.startswith("SINK"))
    sp = splits_for(sinks, fam)
    M7.BUFS = list(ENV)
    P = H.plan(str(geo), sp, fam.get("smax", 70.0), [list(k) for k in fam.get("keepout_um", [])])
    rea = reassign_nearest(P, int(fam.get("reassign_cap", 1.5) * max(len(v) for v in P["leafsinks"].values()))) if fam.get("reassign") else None
    split = split_long_leaves(P, fam.get("leaf_limit", 35.0))
    kr, kc = map(float, fam.get("rc", "0.8,0.9").split(","))
    r = 0.5 * (1.80365e-2 + 1.89935e-2) * kr; c = 0.5 * (1.78475e-1 + 1.64264e-1) * kc
    cells = sorted(set(ENV + [H.REP, H.BIG]))
    libs = {"TT": H.lib_cells(libtt, cells), "FF": H.lib_cells(libff, cells)}
    M7.apply_masters(P, {"rep": "BUFx24_ASAP7_75t_R"})
    wc = {l: fam.get("wire", "std") for l in range(1, len(sp) + 2)}
    sized = M7.size_d1(P, libs, r, c, wc)
    trunk = choose_entry_trunk(P, libs, r, c, wc, trunk_cal) if trunk_cal else None
    res, st = M7.model_x(P, libs, r, c, wc)
    _PLANS[name] = (P, libs, r, c, wc)
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
               sinks=sinks, split_leaves=split, reassign=rea, entry_trunk=trunk, level_len_um=[round(x, 2) for x in P["T"]],
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
    if fam.get("keepout_um"):
        rec["macro_keepout_um"] = [list(k) for k in fam["keepout_um"]]
    return rec


# ------------------------------------------------------------------ calibrated structural re-plan (R16)
WIRE_MENU = ("std", "ndr2w")


def _menu_splits(fam):
    menu = fam.get("menu", [1, 2, 4, 8]); out = []
    for a in menu:
        for b in menu:
            if a <= b:
                sp = [2, 2] + [x for x in (a, b) if x > 1]
                sp = sp if len(sp) > 2 else [2, 2, 1]
                if sp not in out:
                    out.append(sp)
    return out


def _replan_one(args):
    geo, fam, libtt, libff, name, off = args
    try:
        rec = plan(geo, fam, libtt, libff, name)
    except ValueError as e:                       # the H planner refuses some menu shapes (shared wire): not a candidate
        return dict(splits=fam["splits_override"], wire=fam["wire"], error=str(e)[:120]), None
    pred = {k: round(rec[k]["mean"] + off[k], 2) for k in ("TT", "FF")}
    gates = []
    for c in ("TT", "FF"):
        if rec[c]["window"] > GATES["window_ps"]: gates.append("%s window %.1f" % (c, rec[c]["window"]))
        if rec[c]["leaf_out_slew_max"] > GATES["slew_ps"]: gates.append("%s slew %.1f" % (c, rec[c]["leaf_out_slew_max"]))
    if rec["leaf_spread_max"]["n_gt_40"]: gates.append("leaf spread")
    if len(rec["stages"]) != 1: gates.append("stages %s" % rec["stages"])
    err = abs(pred["TT"] - BAND["TT"][0]) + abs(pred["FF"] - BAND["FF"][0])
    row = dict(splits=fam["splits_override"], wire=fam["wire"], stages=rec["stages"], cells=rec["n_cells"],
               plan={k: rec[k]["mean"] for k in ("TT", "FF")}, window={k: rec[k]["window"] for k in ("TT", "FF")},
               predicted_built=pred, band={k: ("IN" if abs(pred[k] - BAND[k][0]) <= BAND[k][1] else "OUT") for k in pred},
               gate_fails=gates, err=round(err, 2))
    return row, rec


def replan_structure(geo, fam, libtt, libff, name, cal, jobs=8):
    """12.3 calibrated re-plan for a core whose BUILT CTS insertion is out of band HIGH (a trunk only lengthens).
    offset[c] = built[c] - plan[c] of the core's own built slice (COORD RULING S81-CORE-LAT-R13: calibrate on the built CTS);
    every family-menu structure (leaf levels from fam menu) x wire class (std / 2W NDR) is planned with the same
    deterministic planner + d1 sizing; candidates that fail a plan gate (window 20, slew 80, spread 40, equal stages) are
    out; pick min |pred TT - 250| + |pred FF - 202.5| (tie: fewer cells, std wire).  No per-core hand tuning: the rule and
    menu are the family's; the offset is applied unchanged to NDR candidates (NDR halves wire R, so the std offset is the
    conservative high side).  PLAN MODEL + one-build calibration, UNCHECKED until the re-planned build is measured."""
    from concurrent.futures import ProcessPoolExecutor
    off = {k: float(cal["built_" + k]) - float(cal["plan_" + k]) for k in ("TT", "FF")}
    cands = [dict(fam, splits_override=sp, wire=w) for w in WIRE_MENU for sp in _menu_splits(fam)]
    args = [(str(geo), f, libtt, libff, name, off) for f in cands]
    if jobs <= 1:
        res = [_replan_one(x) for x in args]
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            res = list(ex.map(_replan_one, args))
    ok = [(r, rec, f) for (r, rec), f in zip(res, cands) if rec is not None and not r["gate_fails"]]
    if not ok:
        raise SystemExit("replan: no family-menu structure passes the plan gates")
    r, rec, f = min(ok, key=lambda t: (t[0]["err"], t[0]["cells"], WIRE_MENU.index(t[0]["wire"])))
    rec["calibrated_replan"] = dict(rule=replan_structure.__doc__.split(".")[0], offset_ps={k: round(v, 2) for k, v in off.items()},
                                    calibration=cal, chosen=r, candidates=[x for x, _ in res],
                                    label="PLAN MODEL + one-build calibration, UNCHECKED until the re-planned build is measured")
    return rec, f


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
    if rec.get("entry_trunk"):
        tk = rec["entry_trunk"]
        out["entry_trunk"] = dict(master=tk["master"], stages=tk["stages"], predicted_built=tk["predicted_built"],
                                  band_info=tk["predicted_band"], offset_ps=tk["offset_ps"])
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
    ax.plot(*rec["entry"], "k*", ms=16, label="sink-centroid entry" if Path(geo).name == "geo_entry.txt" else "centre entry (12.8a)", zorder=5)
    cr = rec["core"]; ax.set_xlim(cr[0] - 3, cr[2] + 3); ax.set_ylim(cr[1] - 3, cr[3] + 3); ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
    t, f = rec["TT"], rec["FF"]
    ax.set_title("%s [%s] splits %s, %s stages, leaf spread max %.1f um\nPLAN MODEL TT %.1f w%.1f / FF %.1f w%.1f (UNCHECKED)"
                 % (rec["name"], rec["family"], rec["splits"], rec["stages"], rec["leaf_spread_max"]["all"], t["mean"], t["window"], f["mean"], f["window"]), fontsize=9)
    fig.savefig(out_png, dpi=110); plt.close(fig)


# ------------------------------------------------------------------ entry (12.16e by intent, COORD dfd33a253)
ENTRY_MODES = ("centre", "sink_centroid")
MACRO_KEEPOUT_HALO_UM = 2.2     # = core_infra_htree.Maze macro halo


def macro_keepouts(sites, halo=MACRO_KEEPOUT_HALO_UM):
    """hard-macro rects of the kit floorplan (sites.txt FIXED lines taller than one row = blocks, not tap/endcap cells),
    grown by the planner's macro halo.  The census (core_family_geo.tcl) writes MACRO lines only for blocks whose clock
    pin is ON the core clock net, so a block clocked through an ICG (S81 rom_elem_q _gb: 4 ot_rom_4096x274_m8, clk via
    u_cg_r*.gclk) is invisible to the maze: the plan put branch drivers inside a ROM (mp_ck_T00_br at (71.28,152.82),
    26 um from the nearest legal row site) and the converter refused."""
    L = Path(sites).read_text().splitlines(); sh = None; out = []
    for l in L:
        f = l.split()
        if f[:1] == ["ROW0"]:
            sh = float(f[6])
    if sh is None:
        raise SystemExit("macro_keepout: %s has no ROW0 line" % sites)
    for l in L:
        f = l.split()
        if f[:1] == ["FIXED"]:
            x0, y0, x1, y1 = map(float, f[3:7])
            if y1 - y0 > 1.5 * sh:
                out.append([round(x0 - halo, 4), round(y0 - halo, 4), round(x1 + halo, 4), round(y1 + halo, 4)])
    return sorted(out)


def keepout_mode(fam, core):
    """family 'macro_keepout': absent/false = no node keep-out (unchanged); true for every member, or {member: bool}.
    true = every hard macro of the member's floorplan is a NODE keep-out for the plan (no driver/repeater/branch site
    inside macro + halo); wires may still pass over it (the plan's wire layers sit above the macro OBS)."""
    k = fam.get("macro_keepout", False)
    return bool(k.get(core, False)) if isinstance(k, dict) else bool(k)



def icg_copies_mode(fam, core):
    """family 'icg_copies' (CORES-EARLY-5, COORD form C): absent/false = unchanged; true for every member, or
    {member: bool}. true = the core's RTL clock gates become planned stages: one ICG copy (core_infra clone_of, same
    ENA/SE nets) per (gate, locality tile) as the planned parent of that group's planned leaves."""
    k = fam.get("icg_copies", False)
    return bool(k.get(core, False)) if isinstance(k, dict) else bool(k)


def gate_tile_groups(geo, tile_um):
    """form C grouping from a GATED census: {(gate or 'ROOT', ix, iy): [sink names]} on a tile_um grid (outline origin),
    every SINK in exactly one group; MACRO lines with gate= are group members too (macro leaves)."""
    if not tile_um > 0:
        raise SystemExit("gate_tile_groups: tile_um must be > 0")
    groups, gates = collections.defaultdict(list), set()
    for l in open(geo):
        f = l.split()
        if not f:
            continue
        tag = [t[5:] for t in f if t.startswith("gate=")]
        g = tag[0] if tag else "ROOT"
        if f[0] == "GATE":
            gates.add(f[1]); continue
        if f[0] == "SINK":
            x, y, name = float(f[1]), float(f[2]), "%s/%s" % (f[4], f[5])
        elif f[0] == "MACRO":
            x, y, name = float(f[8]), float(f[9]), "%s/%s" % (f[1], f[7])
        else:
            continue
        groups[(g, int(x // tile_um), int(y // tile_um))].append(name)
    bad = {k[0] for k in groups if k[0] != "ROOT"} - gates
    if bad:
        raise SystemExit("gate_tile_groups: gated sinks of undeclared gates %s" % sorted(bad)[:3])
    return dict(groups)


def icg_groups_summary(groups, small=25):
    n = [len(v) for v in groups.values()]
    gated = [k for k in groups if k[0] != "ROOT"]
    return dict(groups=len(groups), gated_groups=len(gated), gates=len({k[0] for k in gated}),
                tiles=len({k[1:] for k in groups}), sinks=sum(n), small_groups=sum(1 for v in n if v < small),
                sinks_in_small=sum(v for v in n if v < small))


def entry_mode(fam, core):
    """family 'entry': absent = 'centre' (12.8a outline centre from the census, unchanged); a mode string for every
    member, or {member: mode}.  'sink_centroid' = the core clock entry at the mean of the placed clock sinks (COORD
    dfd33a253: bf_col sinks hug the E face, a centre entry gives 168-220 um L1 legs and a 58 ps window)."""
    e = fam.get("entry", "centre")
    m = e.get(core, "centre") if isinstance(e, dict) else e
    if m not in ENTRY_MODES:
        raise SystemExit("family %s: entry %r for %s: one of %s" % (fam.get("name"), m, core, ENTRY_MODES))
    return m


def entry_geo(geo, mode):
    """the census geo for the chosen entry: 'centre' = geo.txt itself (byte-identical); 'sink_centroid' = geo_entry.txt,
    geo.txt with its 'PIN ck' line moved to the sink centroid (H.plan snaps it to the nearest legal maze cell)."""
    if mode == "centre":
        return geo
    L = geo.read_text().splitlines()
    S = [l.split() for l in L if l.split()[:1] == ["SINK"]]
    if not S:
        raise SystemExit("entry sink_centroid: no SINK lines in %s" % geo)
    cx = sum(float(f[1]) for f in S) / len(S); cy = sum(float(f[2]) for f in S) / len(S)
    n = sum(1 for l in L if l.split()[:2] == ["PIN", "ck"])
    if n != 1:
        raise SystemExit("entry sink_centroid: %d 'PIN ck' lines in %s" % (n, geo))
    out = geo.parent / "geo_entry.txt"
    out.write_text("\n".join("PIN ck %.3f %.3f" % (cx, cy) if l.split()[:2] == ["PIN", "ck"] else l for l in L) + "\n")
    return out


# ------------------------------------------------------------------ driver
def run_core(fams, core, kit, work, a):
    fam = next(f for f in fams["families"] if core in f["members"])
    work = Path(work) / core; work.mkdir(parents=True, exist_ok=True)
    icg = icg_copies_mode(fam, core)
    clk = census(kit, work, gated=True) if icg else census(kit, work)
    if icg:
        # form C stage 1 (CORES-EARLY-5): GATED census + (gate, tile) grouping only. The planner/converter/core_infra
        # stages (ICG copy nodes, planned leaves under a gate, kit clone hook + post-clone LEC) are not built yet, so
        # the run stops here FAIL-CLOSED instead of planning the gated flops as if they were on the core clock.
        tile = float(fam.get("icg_tile_um", 50.0))
        gs = icg_groups_summary(gate_tile_groups(work / "geo_gated.txt", tile))
        (work / "icg_groups.json").write_text(json.dumps(dict(tile_um=tile, **gs), indent=1))
        raise SystemExit("run: icg_copies census + grouping written (%s); planner stage not implemented -> no plan" % json.dumps(gs))
    geo = entry_geo(work / "geo.txt", entry_mode(fam, core))
    if keepout_mode(fam, core):
        fam = dict(fam, keepout_um=macro_keepouts(work / "sites.txt"))
    cal = json.loads(Path(a.trunk_cal).read_text()).get(core) if getattr(a, "trunk_cal", None) else None
    rcal = json.loads(Path(a.replan_cal).read_text()).get(core) if getattr(a, "replan_cal", None) else None
    if rcal and cal:
        raise SystemExit("run: --trunk-cal and --replan-cal both name %s (trunk = built LOW, re-plan = built HIGH)" % core)
    if rcal:
        rec, fam = replan_structure(geo, fam, a.libtt, a.libff, "%s_r16_%s_rp" % (core, fam["name"]), rcal)
    else:
        rec = plan(geo, fam, a.libtt, a.libff, "%s_r13_%s%s" % (core, fam["name"], "_tk" if cal else ""), trunk_cal=cal)
    pj = work / "plan.json"; pj.write_text(json.dumps([rec]))
    if a.fit:
        r = subprocess.run([sys.executable, str(REPO / "results/core_lat_r9_1026/l0r_r9_d1.py"), str(pj), str(geo), a.libdir, a.fit,
                            str(work / "plan_d1.json"), "--steps", str(a.d1_steps)], capture_output=True, text=True)
        (work / "d1.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            # R20 fail-closed: S81-CORES-R1 sparse worktrees lacked results/core_lat_r9_1026 + model_refit2_1026, the d1
            # step died (No such file / ModuleNotFoundError) and the slice silently shipped the pre-d1 masters
            raise SystemExit("run: --fit given but the R9 d1 step failed rc %d (see %s): %s"
                             % (r.returncode, work / "d1.log", (r.stdout + r.stderr).strip()[-200:]))
        rec2 = json.loads((work / "plan_d1.json").read_text())[0]
        # refresh the NLDM numbers with the d1 masters (same chain the checks read)
        rec2["d1_from"] = "uf_phys3 v1 coordinate descent (R9)"
        if rec["name"] not in _PLANS:   # re-plan ran in worker processes: rebuild the chosen plan here (deterministic)
            plan(geo, fam, a.libtt, a.libff, rec["name"], trunk_cal=cal)
        rec = refresh_after_d1(rec, rec2)
        pj = work / "plan_d1.json"; pj.write_text(json.dumps([rec]))
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
                TT=rec["TT"]["mean"], TTw=rec["TT"]["window"], FF=rec["FF"]["mean"], FFw=rec["FF"]["window"], verdict=ck["verdict"], fails=ck["fails"],
                **({"trunk": ck["entry_trunk"]} if ck.get("entry_trunk") else {}))
    print("CORE_FAMILY_SLICE", json.dumps(line), flush=True)
    return line


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=("run", "family"))
    ap.add_argument("--family", required=True); ap.add_argument("--core"); ap.add_argument("--kit"); ap.add_argument("--name")
    ap.add_argument("--kits", help="dir holding <module>_<suffix> trial census kits"); ap.add_argument("--suffix", default="c13")
    ap.add_argument("--work", required=True)
    ap.add_argument("--libtt", required=True); ap.add_argument("--libff", required=True)
    ap.add_argument("--trunk-cal", default=None, help="JSON {core: {built_TT, built_FF, plan_TT, plan_FF, basis, source}}: "
                    "12.8c entry trunk calibrated on the core's own built CTS insertion")
    ap.add_argument("--replan-cal", default=None, help="JSON {core: {built_TT, built_FF, plan_TT, plan_FF, basis, source}}: "
                    "calibrated family-menu structure re-plan for a core built out of band HIGH")
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
