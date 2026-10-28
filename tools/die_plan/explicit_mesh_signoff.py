#!/usr/bin/env python3
"""EXPLICIT-MESH SIGN-OFF ADAPTER (HEAD-R24, shared tool; METHODOLOGY 12.8e / 12.4a b exception).

Feeds the ONE shared die timing model (die_sta_related.py --mesh-signoff) from a die_clock_mesh build whose clock is an
EXPLICIT multi-driver mesh (explicit_clock_mesh.py: mesh.json 'explicit_mesh' graph, no ckm_* strap cells; HEAD die).
The ckm_* strap-mesh path (die_clock_mesh post/report -> kv_r18/mesh_rec18.py -> kv_r18/mesh_mc18.py) is untouched; this
tool produces the same three proof files from the explicit graph, with the same variation model:

  tree   BUILD --out W        OpenSTA (docker, openroad) on the ROUTED combo_<C>.odb + the build's native_<C>.spef
                              (fixed-geometry tree ladder, the basis KV's tree_<C>.txt uses) with the explicit mesh net
                              removed (it only loads the driver outputs; the mesh is solved below): per clock-tree unit
                              A/Y arrival max/min + slew -> W/tree_<C>.txt.
  rec    BUILD --tree W --out rec.json
                              tree nodes = buffer groups (units of one group drive one net), parent group, xy, arrivals
                              (Y; mesh drivers: A input = the transient's driver stimulus, as mesh_rec18 'D' lines);
                              mesh RC = the explicit conductor graph split <= 54 um (qc_clk_mesh2 RC_R6 per-um R/C of the
                              mesh NDR, the KV MC basis; VIA89 = die_clock VIA_KOHM M9-M8); loads = every mesh port
                              (local-tree boundary) at its port node, so each endpoint's real jog RC is in the graph.
  mc     rec.json --thev T --corner C --samples N --out mc_C.json
                              linear transient of the whole mesh (qc_clk_mesh2.solve_netlist, unchanged) behind the
                              ngspice-fitted Thevenin BUFx24 pair (KV R17 thev, mult 2 = the 2 units of a group); MC over
                              driver Vt mismatch, per-segment wire RC, hierarchical tree random + tree wire RC (KV R18
                              sigma keys, same defaults) + the 12.4a b1 gradient (0.21 %/mm, 2 extra solves -> per-load
                              shift vectors).  Output = the mesh_mc18 JSON contract die_sta_related.mesh_signoff reads.
  proof  BUILD --rec rec.json --mc TT=..,FF=.. --out PROOF
                              tap_arrivals_<C>.json (taps = mesh ports, late/early = nominal transient with the tree's
                              late/early driver arrivals), mesh_<C>.json (stubs: port -> late/early; the 'routed' nominal is
                              the same solve, so the routed-vs-sim gap is 0 by construction), mesh.json (taps with
                              stub = port: the load IS the boundary port; the explicit graph for the continuity check).

Below the mesh port nothing is simulated here: die_sta_related's block models carry it (signed core views via
--core-view = ETM arcs incl. the core's own insertion; soft tiles = the declared 12.3 budget).  Load at a port: the
declared --tap-load-ff per endpoint kind (default native_core_clock 2.94 = max signed elemA/elemB clock pin cap,
published_grid_clock 2.3 = qc_clk_mesh2.BUF_CIN_FF, one local-tree root buffer input).  Every number UNCHECKED until
NUMBER-CHECK.
"""
import argparse
import copy
import json
import math
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "kv_r7"))

SEG_UM = 54.0
DEF_LOAD = {"native_core_clock": 2.94, "published_grid_clock": 2.3}
DEF_SIGMA = '{"vt_mV": 10.0, "wire_rel": 0.05, "tree_ps_per_stage": 2.0, "tree_wire_rel": 0.03, ' \
            '"tree_wire_share": {"TT": 0.4674, "FF": 0.5415}}'
MESH_NET = "ck_mesh_explicit"
T_EXTRA_PS = 4000.0    # transient horizon after the last driver ramp (stops early once every load crossed); the KV
                       # 500-ps default is too short for a ~0.9 nF die mesh

TREE_TCL = r"""
# liberty BEFORE the db: dbSta links instances to liberty cells at read_db; the reverse order leaves the timing graph
# without the clock buffers (OpenROAD SIGSEGV in Graph::pinVertices on the first arrival query; HEAD-R22 exit 139).
foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }
read_db /b/combo_$::env(CORNER).odb
read_spef /w/tree_$::env(CORNER).spef
create_clock -name vclk -period 833.000
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
# the explicit mesh is one net with every mesh-driver output on it (528 drivers x 3654 ports): OpenSTA's delay calc on
# that multi-driver net never finishes (>10 min).  Its arrivals are not wanted here (the mesh is solved by the MC), so
# the drivers' A->Y arcs are disabled, as die_clock_mesh combo disables ckm_d_*; A-pin arrivals are unaffected.
set fh [open /w/mesh_drivers.txt r]
foreach u [split [string trim [read $fh]] "\n"] { set_disable_timing [get_cells $u] }
close $fh
report_tns
set fh [open /w/tree_$::env(CORNER).txt w]
foreach c [get_cells {h*_u*}] {
  set n [get_full_name $c]
  foreach pn {A Y} {
    set p [get_pins $n/$pn]
    puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
  }
}
close $fh
puts OT_TREE_DONE
"""


def _qcm2():
    """kv_r7/qc_clk_mesh2.py -- the KV MC basis (kv_r18/mesh_mc18.py --qc tools/die_plan/kv_r7), loaded by path: a
    second, older tools/die_plan/qc_clk_mesh2.py exists and may already sit in sys.modules under the same name."""
    m = sys.modules.get("_kv_r7_qc_clk_mesh2")
    if m is None:
        import importlib.util
        sp_ = importlib.util.spec_from_file_location("_kv_r7_qc_clk_mesh2", HERE / "kv_r7" / "qc_clk_mesh2.py")
        m = importlib.util.module_from_spec(sp_)
        sys.modules["_kv_r7_qc_clk_mesh2"] = m
        sp_.loader.exec_module(m)
    return m


def _load(p):
    return json.loads(Path(p).read_text())


def strip_spef(src, dst, net=MESH_NET):
    """copy the native SPEF without the explicit mesh D_NET section."""
    out, skip, n = [], False, 0
    for ln in Path(src).read_text().splitlines(True):
        if ln.startswith("*D_NET "):
            skip = ln.split()[1] == net
            n += skip
        if not skip:
            out.append(ln)
        if skip and ln.startswith("*END"):
            skip = False
    if n != 1:
        raise SystemExit(f"{src}: expected one *D_NET {net}, found {n}")
    Path(dst).write_text("".join(out))


def cmd_tree(a):
    b, w = Path(a.build).resolve(), Path(a.out).resolve()
    w.mkdir(parents=True, exist_ok=True)
    (w / "tree.tcl").write_text(TREE_TCL)
    G = _load(b / "mesh.json")["explicit_mesh"]
    (w / "mesh_drivers.txt").write_text("\n".join(u for d in G["drivers"] for u in d["units"]) + "\n")
    procs = []
    for c in a.corner:
        strip_spef(b / f"native_{c}.spef", w / f"tree_{c}.spef")
        cmd = ["docker", "run", "--rm", "--memory", a.mem, "-e", f"CORNER={c}",
               "-e", "LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM",
               "-v", f"{b}:/b:ro", "-v", f"{w}:/w", a.image, "bash", "-lc",
               "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /w/tree.tcl"
               f" > /w/tree_{c}.log 2>&1; rc=$?; chown -R {_uid()} /w; exit $rc"]
        procs.append((c, subprocess.Popen(cmd)))
    rc = 0
    for c, p in procs:
        rc |= p.wait()
        print(c, "rc", p.returncode, "lines", sum(1 for _ in open(w / f"tree_{c}.txt")) if (w / f"tree_{c}.txt").exists() else 0)
    return rc


def _uid():
    import os
    return f"{os.getuid()}:{os.getgid()}"


def read_tree(p):
    """{unit: {'A': (max, min, slew), 'Y': (...)}}; unset (+-inf) arrivals are dropped (mesh-driver Y: arcs disabled);
    cmd_rec refuses any pin it needs that is missing."""
    t = defaultdict(dict)
    for ln in open(p):
        f = ln.split()
        if len(f) < 5:
            continue
        try:
            v = tuple(float(x) for x in f[2:5])
        except ValueError:
            continue
        if any(x != x or abs(x) > 1e19 for x in v):
            continue
        t[f[1]][f[0]] = v
    return t


def mesh_rc(graph, ndr, rc_mode="r6"):
    """segments [(node_a, node_b, ohm, fF)] of the explicit conductor graph, every metal edge split <= SEG_UM;
    VIA89 edges = die_clock VIA_KOHM M9 - M8 (as explicit_clock_mesh.mesh_spef_section).  Node ids are the graph's
    'L:x:y' keys; split points 'L:x:y#k'."""
    Q = _qcm2()
    import die_clock as DC
    if rc_mode == "r6":
        rcl = Q.RC_R6[ndr]
    else:
        rf, cf = Q.NDR[ndr]
        rcl = {k: (v[0] * rf * 1e3, v[1] * cf) for k, v in Q.LAYER_RC.items()}
    rvia = max(1e-6, (DC.VIA_KOHM["M9"] - DC.VIA_KOHM["M8"]) * 1e3)
    key = lambda p: f"{p[0]}:{float(p[1]):.4f}:{float(p[2]):.4f}"
    segs = []
    for a_, b_ in graph["edges"]:
        ka, kb = key(a_), key(b_)
        if a_[0] != b_[0]:
            segs.append((ka, kb, rvia, 0.0))
            continue
        L = abs(float(b_[1]) - float(a_[1])) + abs(float(b_[2]) - float(a_[2]))
        r, c = rcl[a_[0]]
        n = max(1, int(math.ceil(L / SEG_UM - 1e-9)))
        prev = ka
        for q in range(1, n + 1):
            cur = kb if q == n else f"{ka}>{kb}#{q}"
            segs.append((prev, cur, r * L / n, c * L / n))
            prev = cur
    return segs, dict(mode=rc_mode, per_um={k: list(v) for k, v in rcl.items()}, via_ohm=rvia, seg_um=SEG_UM)


def cmd_rec(a):
    b = Path(a.build)
    M = _load(b / "mesh.json")
    G = M.get("explicit_mesh")
    if not G:
        raise SystemExit(f"{b}/mesh.json has no explicit_mesh graph (ckm_* strap meshes use kv_r18/mesh_rec18.py)")
    if G.get("connected_components") != 1:
        raise SystemExit("explicit mesh is not one connected component")
    nets = _load(b / "nets.json")["nets"]
    P = _load(b / "place.json")
    tr = {c: read_tree(Path(a.tree) / f"tree_{c}.txt") for c in ("TT", "FF")}
    grp = {u: f"g{P[u]['group']}" for u in P}
    units = defaultdict(list)
    for u, g in grp.items():
        units[g].append(u)
    parent = {}
    for n in nets:
        if n["drv"].startswith("port:"):
            for l_ in n["loads"]:
                parent[grp[l_]] = None
            continue
        pg = grp[n["drv"]]
        for l_ in n["loads"]:
            if l_.startswith("port:"):
                continue
            g = grp[l_]
            if parent.get(g, pg) != pg:
                raise SystemExit(f"group {g} fed by two parents")
            parent[g] = pg
    roots = [g for g, p in parent.items() if p is None]
    if len(roots) != 1:
        raise SystemExit(f"tree has {len(roots)} roots")
    drv_groups = {d["group"]: d for d in G["drivers"]}
    for g in drv_groups:
        if set(units[g]) != set(drv_groups[g]["units"]):
            raise SystemExit(f"mesh driver {g}: unit set differs from place.json")
    depth = {}

    def dep(g):
        if g not in depth:
            depth[g] = 1 if parent[g] is None else dep(parent[g]) + 1
        return depth[g]
    xy = lambda g: [round(sum(P[u]["x"] for u in units[g]) / len(units[g]), 3),
                    round(sum(P[u]["y"] for u in units[g]) / len(units[g]), 3)]

    def arr(g, pin):
        out = {}
        for c in ("TT", "FF"):
            miss = [u for u in units[g] if pin not in tr[c][u]]
            if miss:
                raise SystemExit(f"tree_{c}.txt: no {pin} arrival on {miss[:3]}")
            v = [tr[c][u][pin] for u in units[g]]
            out[c] = dict(late=round(max(x[0] for x in v), 4), early=round(min(x[1] for x in v), 4),
                          slew=round(max(x[2] for x in v), 3))
        return out
    nodes = []
    for g in sorted(parent, key=lambda g: (dep(g), int(g[1:]))):
        drv = g in drv_groups
        nodes.append(dict(tag=g, parent=parent[g], depth=dep(g), driver=drv, mult=len(units[g]), xy=xy(g),
                          arr=arr(g, "A" if drv else "Y"),
                          anchor=drv_groups[g]["anchor"] if drv else None, units=sorted(units[g]),
                          leg_um=450.0))
    missing = [g for g in drv_groups if g not in parent]
    if missing:
        raise SystemExit(f"mesh drivers not in the tree: {missing[:5]}")
    ndr = (M["meta"].get("explicit_mesh") or {}).get("ndr") or M["meta"].get("ndr", "8w")
    segs, rcm = mesh_rc(G, ndr, a.rc)
    loads = dict(DEF_LOAD, **{k: float(v) for k, v in (x.split("=", 1) for x in a.tap_load_ff)})
    taps = []
    for t in G["taps"]:
        k = t.get("endpoint_kind")
        if k not in loads:
            raise SystemExit(f"tap {t['port']}: no declared load for endpoint kind {k}")
        taps.append(dict(port=t["port"], part=t.get("part"), kind=k, endpoint_port=t.get("endpoint_port"),
                         node=f"{t['port_node'][0]}:{float(t['port_node'][1]):.4f}:{float(t['port_node'][2]):.4f}",
                         xy=[float(t["port_node"][1]), float(t["port_node"][2])], pin_xy=t.get("xy"),
                         jog_um=t.get("jog_um"), stub_um=t.get("stub_um"), load_ff=loads[k]))
    rootn = nodes[0]
    rec = dict(schema="opentallas.explicit_mesh_rec.v1", source=str(b.resolve()), ndr=ndr, rc=rcm, nodes=nodes,
               segs=segs, taps=taps, root_xy=rootn["xy"], root=rootn["tag"], tap_load_ff=loads,
               die_root_um=M["meta"].get("root_um"), plan_sha256=M["meta"].get("plan_sha256"),
               graph=dict(nodes=len(G["nodes"]), edges=len(G["edges"]), vias=G.get("vias"),
                          strap_crossings=G.get("strap_crossings"), components=G.get("connected_components")),
               note=__doc__.split("\n\n")[0], checked="UNCHECKED")
    Path(a.out).write_text(json.dumps(rec))
    dg = [n for n in nodes if n["driver"]]
    print("nodes", len(nodes), "drivers", len(dg), "units", sum(n["mult"] for n in dg), "max depth",
          max(n["depth"] for n in dg), "min depth", min(n["depth"] for n in dg), "segs", len(segs), "taps", len(taps),
          "mesh C pF", round(sum(s[3] for s in segs) / 1e3, 3),
          "driver A TT late spread", round(max(n["arr"]["TT"]["late"] for n in dg) - min(n["arr"]["TT"]["late"] for n in dg), 2))
    return 0


# ------------------------------------------------------------------------------------------------ MC
def tree_offsets(rec, corner, sig, seed):
    """hierarchical tree variation (KV R18 sigma semantics): random N(0, s*sqrt(stages)) per tree edge + wire N(0,
    tree_wire_rel * wire_share * edge delay) per edge, both shared by everything below the edge."""
    off = {n["tag"]: 0.0 for n in rec["nodes"]}
    if not seed:
        return off
    by = {n["tag"]: n for n in rec["nodes"]}
    rnd, rw = random.Random(1000 * seed + 17), random.Random(1000 * seed + 29)
    ws = (sig.get("tree_wire_share") or {}).get(corner, 0.5)
    for n in rec["nodes"]:                       # nodes are in depth order (parents first)
        if n["parent"] is None:
            continue
        p = by[n["parent"]]
        o = off[p["tag"]]
        if sig.get("tree_ps_per_stage"):
            o += rnd.gauss(0.0, sig["tree_ps_per_stage"] * math.sqrt(max(1, math.ceil(n["leg_um"] / 450.0 - 1e-9))))
        if sig.get("tree_wire_rel"):
            d_e = max(0.0, n["arr"][corner]["late"] - p["arr"][corner]["late"])
            o += rw.gauss(0.0, sig["tree_wire_rel"] * ws * d_e)
        off[n["tag"]] = o
    return off


def netlist(rec, corner, sig, seed, which="late", shift=None):
    """qc_clk_mesh2.solve_netlist input from the explicit graph: one driver per group at its anchor (thev mult = the
    group's units), loads at the port nodes."""
    rnd = random.Random(1000 * seed + 41)
    wr = sig.get("wire_rel", 0.0) if seed else 0.0
    R, C = [], defaultdict(float)
    for a_, b_, r, c in rec["segs"]:
        f = rnd.gauss(1.0, wr) if wr else 1.0
        R.append((a_, b_, r * f))
        if c:
            C[a_] += c / 2 * f
            C[b_] += c / 2 * f
    off = tree_offsets(rec, corner, sig, seed)
    key = lambda p: f"{p[0]}:{float(p[1]):.4f}:{float(p[2]):.4f}"
    drv = []
    dv = random.Random(1000 * seed + 53)
    for n in rec["nodes"]:
        if not n["driver"]:
            continue
        t = n["arr"][corner][which] + off[n["tag"]] + (shift or {}).get(n["tag"], 0.0)
        g = sig.get("vt_mV", 0) / 1e3 if seed else 0.0
        drv.append(dict(tag=n["tag"], node=key(n["anchor"]), arr=t,
                        dvn=[dv.gauss(0, g) if g else 0.0], dvp=[dv.gauss(0, g) if g else 0.0]))
    taps = []
    for t in rec["taps"]:
        C[t["node"]] += t["load_ff"]
        taps.append(dict(part=t["port"], node=t["node"], inside=True))
    return dict(R=R, C=C, drv=drv, taps=taps, xnodes={}, nodes=len(C))


def solve(rec, corner, thev, sig, seed, which="late", shift=None, slew=False):
    Q = _qcm2()
    th = {corner: dict(thev)}          # thev = this corner's Thevenin block; solve_netlist indexes by corner
    mult = {n["mult"] for n in rec["nodes"] if n["driver"]}
    if mult != {int(thev.get("mult", 1))}:
        raise SystemExit(f"mesh driver groups have {sorted(mult)} units; the Thevenin model is for mult {thev.get('mult', 1)}")
    N = netlist(rec, corner, sig, seed, which, shift)
    t = time.time()
    if slew:
        res, t0, sl = Q.solve_netlist(N, corner, th, t_extra=T_EXTRA_PS, slew=True)
    else:
        res, t0 = Q.solve_netlist(N, corner, th, t_extra=T_EXTRA_PS)
        sl = None
    tp = {k[1]: v + t0 for k, v in res.items() if k[0] == "t"}
    nan = [k for k, v in tp.items() if v != v]
    if nan:
        raise SystemExit(f"sample {seed}: {len(nan)} loads never crossed vdd/2 (e.g. {nan[:3]})")
    return tp, (sl and {k[1]: v for k, v in sl.items()}), time.time() - t


def grad_vectors(rec, corner):
    """per tree node shift (ps * mm along x, y) of the 12.4a b1 gradient: G(n) = G(p) + d_e * (mid_e - root)/1000."""
    by = {n["tag"]: n for n in rec["nodes"]}
    rx, ry = rec["root_xy"]
    G = {}
    for n in rec["nodes"]:
        if n["parent"] is None:
            G[n["tag"]] = (0.0, 0.0)
            continue
        p = by[n["parent"]]
        d = n["arr"][corner]["late"] - p["arr"][corner]["late"]
        mx, my = (n["xy"][0] + p["xy"][0]) / 2 - rx, (n["xy"][1] + p["xy"][1]) / 2 - ry
        G[n["tag"]] = (G[p["tag"]][0] + d * mx / 1000.0, G[p["tag"]][1] + d * my / 1000.0)
    return G


_W = {}


def _mc_job(job):
    """one transient (MC sample seed, or the nominal with a gradient shift); module-level for a fork pool."""
    seed, shift = job
    tp, _, dt = solve(_W["rec"], _W["C"], _W["th"], _W["sig"], seed, shift=shift)
    return tp, dt


def cmd_mc(a):
    rec = _load(a.rec)
    thev = _load(a.thev)
    C = a.corner
    sig = json.loads(a.sigma)
    g = a.grad_pct_per_mm / 100.0
    th = thev[C]
    G = grad_vectors(rec, C)
    gs = g if g else 0.0021
    jobs = [(s, None) for s in range(a.samples + 1)] + [(0, {k: gs * v[ax] for k, v in G.items()}) for ax in (0, 1)]
    _W.update(rec=rec, C=C, th=th, sig=sig)
    if a.jobs > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(min(a.jobs, len(jobs))) as pool:
            res = pool.map(_mc_job, jobs, chunksize=1)
    else:
        res = [_mc_job(j) for j in jobs]
    samples = []
    for s, (tp, dt) in enumerate(res[:a.samples + 1]):
        samples.append(tp)
        print(json.dumps(dict(sample=s, loads=len(tp), skew=round(max(tp.values()) - min(tp.values()), 3),
                              sec=round(dt, 1))), flush=True)
    grad = {}
    for ax in (0, 1):
        tp = res[a.samples + 1 + ax][0]
        grad[ax] = {k: (tp[k] - samples[0][k]) / gs for k in tp}
        print("grad axis", ax, "shift range per unit g", round(min(grad[ax].values()), 1),
              round(max(grad[ax].values()), 1), flush=True)
    loads = sorted(samples[0])
    gv = {k: [round(g * grad[0][k], 4), round(g * grad[1][k], 4)] for k in loads}
    mc = samples[1:]
    dev = [s_[k] - samples[0][k] - (sum(x[k] for x in mc) / len(mc) - samples[0][k]) for s_ in mc for k in loads] if mc else [0.0]
    sd = (sum(v * v for v in dev) / max(1, len(dev) - 1)) ** 0.5
    gw = 0.0
    for i in range(64):
        t_ = math.pi * i / 64
        pr = [gv[k][0] * math.cos(t_) + gv[k][1] * math.sin(t_) for k in loads]
        gw = max(gw, max(pr) - min(pr))
    sk = lambda s_: max(s_.values()) - min(s_.values())
    mcw = max(sk(s_) for s_ in mc) if mc else sk(samples[0])
    out = dict(lane="HEAD-R24 explicit_mesh_signoff", method=__doc__.split("\n\n")[0], rec=str(a.rec), corner=C,
               thev=th, sigma=sig, grad_pct_per_mm=a.grad_pct_per_mm, samples_n=a.samples, loads=loads,
               arr=[[round(s_[k], 3) for k in loads] for s_ in samples],
               routed=[round(samples[0][k], 3) for k in loads], grad_vec_ps=[gv[k] for k in loads],
               summary=dict(nominal_skew_ps=round(sk(samples[0]), 2), mc_worst_skew_ps=round(mcw, 2),
                            per_load_sigma_ps=round(sd, 2), pair_3sigma_ps=round(3 * sd * 2 ** 0.5, 2),
                            gradient_worst_pair_ps=round(gw, 2), routed_minus_sim_mean_ps=0.0,
                            routed_minus_sim_spread_ps=0.0, dieU_bound_ps=round(mcw + gw, 2),
                            dieU_bound_note="die-wide bound (not a per-pair gate number); routed nominal = sample 0 "
                                            "of this solve (same graph), gap 0 by construction"),
               checked="UNCHECKED")
    Path(a.out).write_text(json.dumps(out))
    print("SUMMARY", C, json.dumps(out["summary"]))
    return 0


# ------------------------------------------------------------------------------------------------ proof dir
def cmd_proof(a):
    b, d = Path(a.build), Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    rec = _load(a.rec)
    thev = _load(a.thev)
    sig = json.loads(DEF_SIGMA)
    M = _load(b / "mesh.json")
    G = M["explicit_mesh"]
    by = {n["tag"]: n for n in rec["nodes"]}
    root = by[rec["root"]]
    so = dict(x.split("=", 1) for x in a.mc.split(",")) if a.mc else {}
    for C in a.corner:
        late, sl, _ = solve(rec, C, thev[C], sig, 0, "late", slew=True)
        # early = the same nominal solve.  The tree's OpenSTA min arrivals are NOT used: on the stacked multi-unit tree
        # nets (2-4 tied BUFx24 per group) OpenSTA 26Q3 reports ~0 wire delay for min (HEAD-R24 tree_<C>.txt: A min =
        # previous Y min on every hop), so they are not a basis.  Under --mesh-signoff every mesh pair is re-referenced
        # to the signed mesh (late = early = M0, credit 0, U from the MC), so absolute early arrivals enter no gate
        # number; the KV MC likewise drives its mesh with the late (arrival_max) tree arrivals.
        early = late
        if C in so:          # the sign-off's nominal must be this same solve (gap 0 by construction)
            S = _load(so[C])
            r0 = dict(zip(S["loads"], S["arr"][0]))
            bad = [k for k in late if abs(r0.get(k, 1e9) - late[k]) > 0.01]
            if bad:
                raise SystemExit(f"{so[C]}: nominal differs from this rec's solve on {len(bad)} loads (e.g. {bad[:3]})")
        taps = []
        for t in rec["taps"]:
            p = t["port"]
            # stages = buffers from the die root up to and including the driving cell (the mesh driver feeding the port);
            # every port is fed by the whole mesh, so the shallowest driver depth is the stage count above the port.
            taps.append(dict(part=t["part"], tap=t["endpoint_port"], port=p, late_ps=round(late[p], 3),
                             early_ps=round(early[p], 3), slew_ps=round(sl[p], 3), region=None, cppr_node="h",
                             stages_from_root=min(n["depth"] for n in rec["nodes"] if n["driver"]),
                             xy_um=t["xy"], kind=t["kind"], jog_um=t["jog_um"], load_ff=t["load_ff"]))
        ra = root["arr"][C]
        meta = dict(corner=C, basis="explicit mesh: OpenSTA tree arrivals on the routed combo ODB + native fixed-geometry "
                    "tree SPEF -> linear transient of the routed explicit mesh graph (RC_R6 per um, real jog RC, "
                    "declared port loads), raw (no offsets)",
                    cppr="credit only at the last common tree node: die root 'h' (one tree); signed mesh via "
                         "--mesh-signoff", cppr_node_range_ps={"h": 0.0},
                    taps=taps, node_stages={"h": 1}, node_xy_um={"h": root["xy"]},
                    node_late_ps={"h": ra["late"]}, node_early_ps={"h": ra["late"]},
                    early_basis="= late (single nominal solve; OpenSTA min arrivals on stacked tree nets not used)",
                    aocv_fold="stages = buffers from the die root up to and including the cell (tap: the mesh driver)",
                    source=dict(build=str(b.resolve()), rec=str(Path(a.rec).resolve())), checked="UNCHECKED")
        (d / f"tap_arrivals_{C}.json").write_text(json.dumps(meta, indent=0))
        (d / f"mesh_{C}.json").write_text(json.dumps(dict(
            corner=C, stubs={t["port"]: dict(late=round(late[t["port"]], 3), early=round(early[t["port"]], 3))
                             for t in rec["taps"]},
            note="explicit mesh: load = boundary port; routed nominal = rec solve sample 0")))
        sk = max(late.values()) - min(late.values())
        print(C, "taps", len(taps), "late", round(min(late.values()), 2), "..", round(max(late.values()), 2),
              "skew", round(sk, 2), "slew max", round(max(sl.values()), 2))
    pm = dict(meta=dict(M["meta"], proof="explicit_mesh_signoff"), xs=[], ys=[], drivers={}, htree=[], stubs=[],
              taps=[dict(port=t["port"], part=t["part"], xy=t["xy"], stub=t["port"], kind=t["kind"]) for t in rec["taps"]],
              explicit_mesh=G)
    (d / "mesh.json").write_text(json.dumps(pm))
    for f in ("encoder_receipt.json", "attachment_receipt.json", "shield_ties.json"):
        if (b / f).exists():
            (d / f).write_text((b / f).read_text())
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("tree")
    t.add_argument("build")
    t.add_argument("--out", required=True)
    t.add_argument("--corner", action="append")
    t.add_argument("--mem", default="24g")
    t.add_argument("--image", default="openroad/orfs:latest")
    r = sp.add_parser("rec")
    r.add_argument("build")
    r.add_argument("--tree", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--rc", choices=("r6", "native"), default="r6")
    r.add_argument("--tap-load-ff", action="append", default=[], help="KIND=fF port load per endpoint kind")
    m = sp.add_parser("mc")
    m.add_argument("rec")
    m.add_argument("--thev", required=True)
    m.add_argument("--corner", default="TT")
    m.add_argument("--samples", type=int, default=24)
    m.add_argument("--out", required=True)
    m.add_argument("--sigma", default=DEF_SIGMA)
    m.add_argument("--grad-pct-per-mm", type=float, default=0.21)
    m.add_argument("--jobs", type=int, default=1, help="parallel transients (fork pool); results identical to --jobs 1")
    p = sp.add_parser("proof")
    p.add_argument("build")
    p.add_argument("--rec", required=True)
    p.add_argument("--thev", required=True)
    p.add_argument("--mc", help="TT=mc.json,FF=mc.json (cross-check: nominal == this solve)")
    p.add_argument("--out", required=True)
    p.add_argument("--corner", action="append")
    a = ap.parse_args(argv)
    if getattr(a, "corner", None) is None and a.cmd in ("tree", "proof"):
        a.corner = ["TT", "FF"]
    return dict(tree=cmd_tree, rec=cmd_rec, mc=cmd_mc, proof=cmd_proof)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
