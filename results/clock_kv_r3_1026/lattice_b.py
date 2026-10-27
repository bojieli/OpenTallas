"""CLOCK-KV-R3 option (b) lattice (COORD 17:05): commensurate 380.16 um y pitch (row/4, phase 267.84, mirror axis
13003.2), 32 x columns symmetric about the die x centre, 12.8e regions = one mesh per dataflow band
(S rows 0-31 | hub 32-35 | N 36-67 | sys 68-70), each fed by its own equal-length binary tree whose split order is
declared (default y-first: spine levels in the single-instance centre pv / hub_C column, then x splits inside a
partition row, then the in-row y splits).  Global legs root -> region roots along x = die centre.
Every element (mesh driver, tree node, leg repeater) -> site; census by partition type and core module (12.2a1
identity), in-core hits; writes ot_clock_sites/1 style JSON for --plan-sites experiments.
usage: lattice_b.py TOOLDIR PLAN OUTDIR [axes_S] [axes_H] [axes_Y]"""
import sys, json, math, collections, hashlib
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import schema as S
plan_path, outd = sys.argv[2], Path(sys.argv[3]); outd.mkdir(parents=True, exist_ok=True)
P = S.Plan(S.load(plan_path))
W, H = float(P.W), float(P.H)
PY, Y0, NXC = 380.16, 267.84, 32
REP = 450.0
import os
XP = float(os.environ.get("XP", W / NXC)); XC = W / 2
xs = [XC + (i - (NXC - 1) / 2) * XP for i in range(NXC)]
ys = [Y0 + k * PY for k in range(int((H - Y0) // PY) + 1)]
REG = [("S", 0, 32), ("H", 32, 36), ("N", 36, 68), ("Y", 68, len(ys))]
axes_arg = dict(S=sys.argv[4] if len(sys.argv) > 4 else "yyyxxxxxyy", H=sys.argv[5] if len(sys.argv) > 5 else "yxxxxxy",
                Y=sys.argv[6] if len(sys.argv) > 6 else "yxxxxxy")
axes_arg["N"] = axes_arg["S"]
pts = []     # (role, region, name, x, y, level)
roots = {}
def leg(a, b, region, tag):
    L = abs(b[0]-a[0]) + abs(b[1]-a[1]); n = max(1, math.ceil(L / REP - 1e-9))
    for k in range(1, n):
        f = k / n
        pts.append(("rep", region, f"{tag}_r{k}", a[0] + (b[0]-a[0]) * f, a[1] + (b[1]-a[1]) * f, None))
    return L
pathlen = collections.defaultdict(float)
for rg, j0, j1 in REG:
    ax = axes_arg[rg]
    rows = list(range(j0, j1))
    # virtual rows (pruned dead branches) pad a non-pow2 band to pow2 at the far side
    nyp = 1 << (len(rows) - 1).bit_length()
    def cy(a, b):
        real = [ys[k] for k in range(j0 + a, j0 + b) if k < j1]
        vy = [Y0 + (j0 + k) * PY for k in range(a, b)]
        return sum(vy) / len(vy), bool(real)
    def rec(i0, i1, a, b, lvl, tag, here, plen):
        if (i1 - i0) * (b - a) == 1:
            if j0 + a < j1:
                pts.append(("driver", rg, f"d_{i0}_{j0+a}", xs[i0], ys[j0 + a], lvl)); pathlen[(rg, i0, j0 + a)] = plen
            return
        axis = (0 if ax[lvl] == "x" else 1) if lvl < len(ax) else (0 if (i1 - i0) > 1 else 1)
        if axis == 0:
            h = (i0 + i1) // 2; kids = [(i0, h, a, b), (h, i1, a, b)]
        else:
            h = (a + b) // 2; kids = [(i0, i1, a, h), (i0, i1, h, b)]
        for c, (ki0, ki1, ka, kb) in enumerate(kids):
            yv, live = cy(ka, kb)
            if not live:
                continue
            kp = (sum(xs[ki0:ki1]) / (ki1 - ki0), yv)
            L = leg(here, kp, rg, f"{rg}{tag}{c}")
            if (ki1 - ki0) * (kb - ka) > 1:
                pts.append(("node", rg, f"n{rg}{tag}{c}", kp[0], kp[1], lvl + 1))
            rec(ki0, ki1, ka, kb, lvl + 1, tag + str(c), kp, plen + L)
    root = (sum(xs) / NXC, cy(0, nyp)[0])
    roots[rg] = root
    pts.append(("node", rg, f"n{rg}", root[0], root[1], 0))
    rec(0, NXC, 0, nyp, 0, "", root, 0.0)
die_root = roots["H"]
glen = {}
for rg, r in roots.items():
    glen[rg] = leg(die_root, r, "G", f"G{rg}") if rg != "H" else 0.0
# -- geometry indices
parts = {n: P.rect(n) for n in P.parts}
cores = []
for n, p in P.parts.items():
    for hc in P.types[p["type"]].get("hard_cores", []) or []:
        (x0, y0_), (w, h) = hc["origin_um"], hc["outline_um"]
        a, b = P.to_die(n, (x0, y0_)), P.to_die(n, (x0 + w, y0_ + h))
        cores.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), n, hc["inst"], hc["module"], (x0, y0_)))
def local(n, x, y):
    o = P.to_die(n, (0, 0)); ex = P.to_die(n, (1, 0)); ey = P.to_die(n, (0, 1))
    a, b, c, d = ex[0]-o[0], ey[0]-o[0], ex[1]-o[1], ey[1]-o[1]
    det = a*d - b*c; dx, dy = x - o[0], y - o[1]
    return (round((d*dx - b*dy)/det, 1), round((-c*dx + a*dy)/det, 1))
sites, roles, incore = [], collections.Counter(), collections.Counter()
inst_pts = collections.defaultdict(set); inst_pts_role = collections.defaultdict(set)
core_pts = collections.defaultdict(set)
for role, rg, name, x, y, lvl in pts:
    part = next((n for n, r in parts.items() if r[0] <= x < r[2] and r[1] <= y < r[3]), None)
    core = next((c for c in cores if c[0] <= x <= c[2] and c[1] <= y <= c[3]), None)
    roles[(role, "core" if core else ("part" if part else "none"))] += 1
    lx = local(part, x, y) if part else None
    if core:
        incore[(core[6], role)] += 1
        core_pts[(core[4], core[5])].add((round(lx[0] - core[7][0], 1), round(lx[1] - core[7][1], 1)))
    if part:
        inst_pts[part].add(lx + (core[5] if core else "-",))
        inst_pts_role[part].add((role,) + lx)
    sites.append(dict(name=f"{part}:{name}" if part else name, role=role, region=rg, inst=part, island=name,
                      type=P.parts[part]["type"] if part else None, kind="core" if core else "partition",
                      core=core[5] if core else None, module=core[6] if core else None,
                      xy_um=[round(x, 4), round(y, 4)], local_um=list(lx) if lx else None, level=lvl))
Q = 0.5   # site snap (SNAP_UM): coordinates equal within the PG/site snap are the same island
def canon(st):
    return frozenset(tuple(round(v / Q) if isinstance(v, float) else v for v in t) for t in st)
bytype = collections.defaultdict(list)
for n, p in P.parts.items(): bytype[p["type"]].append(n)
multi = {t: ns for t, ns in bytype.items() if len(ns) > 1}
ident = {}
for t, ns in sorted(multi.items()):
    sets = {canon(inst_pts.get(n, set())) for n in ns}
    rsets = {canon(inst_pts_role.get(n, set())) for n in ns}
    ident[t] = dict(n=len(ns), site_sets=len(sets), role_sets=len(rsets),
                    sites_per_inst=sorted({len(inst_pts.get(n, ())) for n in ns}))
# core-module identity: all instances of a module (across all partitions) same core-local site set
bymod = collections.defaultdict(list)
for c in cores: bymod[c[6]].append((c[4], c[5]))
mod_ident = {}
for m_, insts in bymod.items():
    sets = {canon(core_pts.get(k, set())) for k in insts}
    hit = sum(1 for k in insts if core_pts.get(k))
    union = set()
    for k in insts: union |= set(canon(core_pts.get(k, set())))
    if hit:
        mod_ident[m_] = dict(instances=len(insts), with_sites=hit, site_sets=len(sets),
                             sites=sorted({len(core_pts.get(k, ())) for k in insts}), union_sites=len(union),
                             partition_types=sorted({P.parts[k[0]]["type"] for k in insts}))
# path-length check (equal by construction within a region)
pl = collections.defaultdict(list)
for (rg, i, j), L in pathlen.items(): pl[rg].append(L + glen[rg])
summary = dict(lattice=dict(nx=NXC, ny=len(ys), x_pitch=round(XP, 4), y_pitch=PY, y_phase=Y0,
                            y_range=[ys[0], ys[-1]], mirror_y=round((ys[0] + ys[31] + ys[36] + ys[67]) / 4, 3)),
               regions={rg: dict(rows=[j0, j1], axes=axes_arg[rg], root=[round(v, 2) for v in roots[rg]],
                                 global_leg_um=round(glen[rg], 2),
                                 path_um=[round(min(pl[rg]), 2), round(max(pl[rg]), 2)]) for rg, j0, j1 in REG},
               points=dict((f"{a}/{b}", v) for (a, b), v in sorted(roles.items())),
               incore_by_module=dict((f"{a}/{b}", v) for (a, b), v in sorted(incore.items())),
               multi_instance_types=len(multi),
               identity_fail_sites=sorted(t for t, v in ident.items() if v["site_sets"] > 1),
               identity_fail_roles=sorted(t for t, v in ident.items() if v["role_sets"] > 1),
               identity=ident,
               core_module_identity_fail=sorted(m_ for m_, v in mod_ident.items() if v["site_sets"] > 1),
               core_modules=mod_ident)
(outd / "lattice_b_summary.json").write_text(json.dumps(summary, indent=1))
(outd / "lattice_b_sites.json").write_text(json.dumps(dict(
    schema="ot_clock_sites/1", plan_sha256=hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
    source="CLOCK-KV-R3 lattice_b.py (census draft, not a master-plan slice)", snap_um=0.5, sites=sites)))
print(json.dumps({k: v for k, v in summary.items() if k not in ("identity", "core_modules")}, indent=1))
