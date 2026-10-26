#!/usr/bin/env python3
"""INFRA-FIRST step 1 (owner D-INFRA-FIRST 2026-10-26): size the die power grid (M9 + part of M8) from per-region IR.

    infra_pg.py size PLAN.json --out DIR [--ir-budget-frac 0.05] [--core-w-mm2 X] [--phy-w 4.37] [--bump-pitch 150]
        -> DIR/pg.json  {grid (die.pg.grid schema), regions, tracks, basis, candidates}
    infra_pg.py psm  PLAN.json --pg DIR/pg.json --kit KITDIR [--out RUN] [--mode window|die] [--window NAME ...]
        -> PDNSim run dir(s) (die_trial style: run_psm.sh + psm/*.tcl) that verify the estimate with the sized grid
    infra_pg.py report RUN    -> RUN/result.json (die_trial.psm_report + the model's estimate on the same domain)

REGIONS.  A region is a uniform-density area: every die IO window (die.io / die_io.json: SerDes, UCIe, HBM PHY) is its
own region at its published PHY power; the core is the union of the remaining partitions at the core density (per type
when `power["types"]` gives one).  Die channels (bump keep-out, no logic) carry no load and no bumps.

IR MODEL (VDD net; PDNSim reports the VDD drop with ideal bump sources, so the model does too):
  * coarse: the die's M8 (H) / M9 (V) mesh of ONE net as an anisotropic sheet, Rx = Rsq(M8) * pitch8 / w8 and
    Ry = Rsq(M9) * pitch9 / w9 (Rsq = setRC per-um resistance x min width, the values PDNSim uses), finite differences
    on a lattice aligned with the C4 bump lattice (die_trial.bump_grid: pitch p, VDD/VSS by parity, none in IO
    windows or channels), h = p/2, VDD bumps are ideal 0-drop nodes, loads = region density x cell area.
  * local: the coarse lattice cannot see the discrete stripes or the bump's point spreading, so a periodic unit cell
    (2p x 2p, two VDD bumps) is solved on the exact stripe-crossing network (one node per M9 x M8 VDD crossing, segment
    resistances Rsq*length/width) and the difference cell_max - coarse_cell_max is added (scaled by core density).
  ir_est(region) = max over the region of (coarse + local).  Linear in power: IR scales with every density.
SIZING.  Stripes stay at 0.48 um (the widest M8/M9 width below the 0.5-um wide-wire spacing step of the ASAP7 tech
LEF: 0.48 blocks 7.5 tracks for 0.48 um of metal, 0.96 blocks 25).  Candidate pitches are 8.64 / n and 8.64 x 2^k
(VDD at pitch/2, VSS at pitch, as the plan's grid).  The chosen grid is the smallest M8 track share (then smallest M9)
whose worst region IR <= ir_budget_frac x VDD, with M8 <= m8_max_frac and M9 <= m9_max_frac.
The die.pg.grid schema is die-wide stripes only (pg_regions.regions keys a region on its own nets), so M8 is a coarser
die-wide pitch, never region-limited stripes.

Read-only: nothing is written into the plan.
"""
import argparse
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as D  # noqa: E402
import schema as S  # noqa: E402

# ---------------------------------------------------------------------------------------------- published basis
# ASAP7 setRC.tcl (kohm/um at the 0.04-um minimum width) -> ohm/sq
RSQ = {"M8": 8.44765e-3 * 1e3 * 0.04, "M9": 8.89556e-3 * 1e3 * 0.04}
MIN_W = {"M8": 0.04, "M9": 0.04}


def spacing(w):
    """ASAP7 tech LEF M8/M9 SPACINGTABLE (long parallel run): width >= 0.49975 -> 0.5, >= 0.99975 -> 1.0."""
    return 1.0 if w >= 0.99975 else (0.5 if w >= 0.49975 else 0.04)


STRIPE_W = 0.48
BASE_PITCH = 8.64
PITCHES = sorted({round(BASE_PITCH / n, 4) for n in (1, 2, 3, 4, 5, 6)} | {BASE_PITCH * 2 ** k for k in (1, 2, 3, 4)})

# core density per die (W/mm2) -- the hot, conservative end of what the repo publishes (power_scenarios rule)
DIE_CORE = {
    "qwen_compute": (0.582282, "results/arch/power_scenarios.json scenarios.A_measured_implementation.qwen3_8b_rom_8k."
                     "ar_batch1.cooling_classes.liquid.die_w_per_mm2_at_cap = 474.56 W / 815 mm2 (design-rate die power "
                     "618.55 W exceeds the liquid cap, so the die runs at the cap); one density for every core type"),
    "s81": (None, "docs/RELEASE_RACK.md 2.4: 84.1 W per S81 die (old 10-04 die report, PHY share unknown -> all of it "
                  "charged to the core area)", 84.1),
    "s81_head": (None, "docs/RELEASE_RACK.md 2.4: 84.1 W per S81 die (old 10-04 die report, PHY share unknown -> all of "
                       "it charged to the core area)", 84.1),
}
FALLBACK_CORE = (0.15, "die_trial.py part_power default 0.15 W/mm2 (no die power figure for this die)")
# UCIe x64 PHY power basis (COORD default 2026-10-26 11:48, owner may veto; NUMBER-CHECK 11:46 CHECKED by PDNSim
# re-solve: VDDPHY 10.9 mV M7-only at this load): the PHY abstract the QC / KV dies instantiate
# (physical/die_plan/qwen_kvsys/cores/sys_c_views_m6/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy.json: x64, 64 TX + 64 RX
# at 16 GT/s, 0.29 pJ/b; liberty read_energy 169,070 fJ = 583-bit flit x 0.29 pJ/b), raw rate in both directions with
# the full pJ/b charged to EACH end: 2 x 64 x 16 GT/s x 0.29 pJ/b = 0.59392 W per PHY.  The earlier 2.4576 W
# (128 lanes x 32 GT/s x 0.6 pJ/b, UCIe-A upper spec at 2x the abstract's lane rate) stays as UCIE_X64_W_SPEC_UPPER,
# a sensitivity value only.
UCIE_X64_W_SPEC_UPPER = 128 * 32e9 * 0.6e-12
UCIE_X64_W = 2 * 64 * 16e9 * 0.29e-12
PHY_W_MM2 = 1.30                    # PHY_ASSUMPTIONS "PHY power density" (4.37 W / 3.36 mm2), for other PHY kinds
UBUMP_UM = 45.0                     # PHY_ASSUMPTIONS BUMP.UBUMP (2.5D micro-bump field, bump contract 1)
PHY_PG_SHARE = {"ucie": 0.30, "serdes": 0.45, "hbm": 0.45, "other": 0.45}   # UCIE.A.PG_SHARE / UCIE.S.PG_SHARE / HBM 45%


def _pg_io(P, plan_dir):
    """die IO windows that carry PHY supply/power: a die_root_pad (one signal pad, e.g. the KV POR pin) is not a PHY window."""
    return [w for w in D.io_windows(P, plan_dir) if w.get("kind") != "die_root_pad"]


def phy_kind(iface, mod=""):
    t = f"{iface} {mod}".lower()
    return next((k for k in ("serdes", "ucie", "hbm") if k in t), "other")


def phy_pg_pitch(kind):
    """Effective VDD/VSS lattice pitch of a PHY window's own PG micro-bumps: 45 um / sqrt(PG share)."""
    return round(UBUMP_UM / math.sqrt(PHY_PG_SHARE[kind]), 3)


def pg_bumps(P, io, pitch=150.0, phy=True):
    """Core C4 power bumps (die_trial.bump_grid) + every PHY window's own PG micro-bump lattice (VDD/VSS by parity).
    The plan uses every 150-um site of a PHY window for signals, so without these a PHY window has no supply at all."""
    out = list(D.bump_grid(P, io, pitch=pitch))
    if phy:
        for w in io:
            out += _phy_lattice(w["rect_um"], phy_pg_pitch(phy_kind(w.get("iface") or "", w.get("name", ""))))[1]
    return out


def _rect_of(P, n):
    p = P.parts[n]
    w, h = P.types[p["type"]]["outline_um"]
    if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    x, y = p["origin_um"]
    return [x, y, x + w, y + h]


def _ov(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def phy_power(P, w, phy_w_per_macro):
    """(W, basis) of one die IO window."""
    iface = (w.get("iface") or "").lower()
    mod = ""
    if w.get("part") in P.parts:
        t = P.types[P.parts[w["part"]]["type"]]
        mod = " ".join(c.get("module", "") for c in t.get("contents", []) or []) or t.get("module", "")
    if "serdes" in iface or "serdes" in mod:
        m = re.search(r"_x(\d+)", mod)
        lanes = int(m.group(1)) if m else 6
        return phy_w_per_macro * lanes / 6.0, (f"SerDes {lanes} lanes = {lanes / 6:g} x {phy_w_per_macro:g} W per active "
                                              f"6-lane 112G macro (PHY_ASSUMPTIONS SER.MACRO6_POWER)")
    if "ucie" in iface or "ucie" in mod:
        return UCIE_X64_W, ("UCIe x64: PHY abstract ot_qkvd_ucie_x64_phy 2 x 64 lanes x 16 GT/s x 0.29 pJ/b = %.4f W "
                            "(COORD default 10-26 11:48, owner may veto; spec upper %.4f W = sensitivity only)"
                            % (UCIE_X64_W, UCIE_X64_W_SPEC_UPPER))
    r = w.get("rect_um") or w["rect"]          # load_model passes its window rows as {name, rect, part, iface}
    a = (r[2] - r[0]) * (r[3] - r[1]) * 1e-6
    return PHY_W_MM2 * a, f"{iface or 'PHY'}: {PHY_W_MM2} W/mm2 x {a:.3f} mm2 (PHY_ASSUMPTIONS PHY power density)"


def load_model(P, plan_dir, power=None, phy_w_per_macro=4.37, core_w_mm2=None, core_watts=None):
    """-> dict(loads=[(rect, W/mm2)], regions=[...], part_w={part: W}, basis=[...])"""
    power = power or {}
    io = _pg_io(P, plan_dir)
    basis = []
    if core_w_mm2 is None:
        core_w_mm2 = power.get("core_w_mm2")
    if core_w_mm2 is not None:
        core, src = float(core_w_mm2), "core density given on the command line / power['core_w_mm2']"
    else:
        ent = DIE_CORE.get(P.name)
        core = None
        if ent and ent[0] is not None:
            core, src = ent[0], ent[1]
        elif ent:
            src = ent[1]
        else:
            core, src = FALLBACK_CORE
    core_watts = core_watts if core_watts is not None else power.get("core_watts")
    if core_watts is not None:
        if core_w_mm2 is not None: raise ValueError("choose core watts or core density, not both")
        if float(core_watts) < 0: raise ValueError("core watts must be non-negative")
        core, src = None, "explicit non-PHY core watts (PHY power added separately)"
    rects = {n: _rect_of(P, n) for n in P.parts}
    win = [dict(name=w["name"], rect=list(map(float, w["rect_um"])), part=w.get("part")) for w in io]
    phy_parts = {n for n, r in rects.items() if any(all(abs(r[i] - x["rect"][i]) < 1.0 for i in range(4)) for x in win)}
    core_parts = [n for n in sorted(P.parts) if n not in phy_parts]
    core_area = sum((rects[n][2] - rects[n][0]) * (rects[n][3] - rects[n][1]) for n in core_parts) \
        - sum(_ov(x["rect"], rects[n]) for x in win for n in core_parts)
    if core is None:   # die-watt form
        core = (float(core_watts) if core_watts is not None else DIE_CORE[P.name][2]) / (core_area * 1e-6)
        src += f" -> {core:.4f} W/mm2 over {core_area * 1e-6:.1f} mm2 of core partitions"
    basis.append(f"core: {core:.6g} W/mm2 -- {src}")
    tdens = {tn: float(v) for tn, v in (power.get("types") or {}).items()}
    if tdens:
        basis.append("per-type core densities (power['types']): " + ", ".join(f"{k} {v:g}" for k, v in sorted(tdens.items())))
    loads, part_w, regions = [], {}, []
    for n in core_parts:
        d = tdens.get(P.parts[n]["type"], core)
        r = rects[n]
        loads.append((r, d))
        part_w[n] = d * ((r[2] - r[0]) * (r[3] - r[1]) - sum(_ov(x["rect"], r) for x in win)) * 1e-6
    core_part_w = dict(part_w)  # PHY watts below belong to the physical owner, not the core region.
    for x in win:
        wpw, b = phy_power(P, dict(x, iface=next((w.get("iface") for w in io if w["name"] == x["name"]), "")),
                           phy_w_per_macro)
        r = x["rect"]
        a = (r[2] - r[0]) * (r[3] - r[1]) * 1e-6
        for n in core_parts:   # the window replaces the core load where it sits inside a core partition
            o = _ov(r, rects[n])
            if o > 0:
                loads.append(([max(r[0], rects[n][0]), max(r[1], rects[n][1]), min(r[2], rects[n][2]),
                               min(r[3], rects[n][3])], -tdens.get(P.parts[n]["type"], core)))
        loads.append((r, wpw / a))
        owner = x["part"] if x["part"] in phy_parts else next((n for n in phy_parts if rects[n] == r), None)
        host = x["part"] if x["part"] in P.parts else None
        if owner is None:
            owner = next((n for n in phy_parts if all(abs(rects[n][i] - r[i]) < 1 for i in range(4))), host)
        part_w[owner] = part_w.get(owner, 0.0) + wpw
        kind = phy_kind(next((w.get("iface") or "" for w in io if w["name"] == x["name"]), ""), x["name"])
        regions.append(dict(name=x["name"], kind="phy", rect_um=r, power_w=round(wpw, 4), area_mm2=round(a, 4),
                            w_mm2=round(wpw / a, 4), part=owner, phy=kind, pg_bump_pitch_um=phy_pg_pitch(kind)))
        basis.append(f"{x['name']}: {wpw:.3f} W -- {b}")
    if tdens:
        for tn in sorted({P.parts[n]["type"] for n in core_parts}):
            ns = [n for n in core_parts if P.parts[n]["type"] == tn]
            a = sum((rects[n][2] - rects[n][0]) * (rects[n][3] - rects[n][1]) for n in ns) * 1e-6
            regions.append(dict(name=f"core:{tn}", kind="core", rect_um=[0, 0, P.W, P.H], parts=ns,
                                power_w=round(sum(core_part_w[n] for n in ns), 3), area_mm2=round(a, 3),
                                w_mm2=round(tdens.get(tn, core), 4)))
    regions.insert(0, dict(name="core", kind="core", rect_um=[0.0, 0.0, P.W, P.H], parts=core_parts,
                           power_w=round(sum(core_part_w[n] for n in core_parts), 3), area_mm2=round(core_area * 1e-6, 3),
                           w_mm2=round(core, 4)))
    basis.append("channels (die.channels): bump keep-out, no logic -> 0 W; whitespace between partitions -> 0 W")
    basis.append("PHY windows: no core bumps (die_trial.bump_grid excludes IO windows); PHY supply on core VDD "
                 "(no die.pg.domains on this plan)" if not P.die.get("pg", {}).get("domains") else
                 "PHY windows: no core bumps; plan declares pg.domains (modelled on the core VDD mesh here)")
    return dict(loads=loads, regions=regions, part_w=part_w, core_w_mm2=core, basis=basis, core_parts=core_parts,
                rects=rects)


# ------------------------------------------------------------------------------------------------------ IR model
def _rx_ry(grid):
    """Per-net effective sheet resistance (ohm/sq) of the M8 (x) and M9 (y) stripes: each net has one stripe per pitch
    (die_trial.pg_stripes places one stripe per net per pitch)."""
    g = {s["layer"]: s for s in grid}
    return (RSQ["M8"] * g["M8"]["pitch_um"] / g["M8"]["width_um"], RSQ["M9"] * g["M9"]["pitch_um"] / g["M9"]["width_um"])


def _solve(nx, ny, gx, gy, load, fixed, periodic=False):
    """Drop u (V) on an nx x ny lattice: sum_links g (u_i - u_j) = load_i, u = 0 on fixed (flat index array)."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    N = nx * ny
    idx = np.arange(N).reshape(ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(N)
    pairs = [(idx[:, :-1], idx[:, 1:], gx), (idx[:-1, :], idx[1:, :], gy)]
    if periodic:
        pairs += [(idx[:, -1:], idx[:, :1], gx), (idx[-1:, :], idx[:1, :], gy)]
    for a, b, g in pairs:
        a, b = a.ravel(), b.ravel()
        rows += [a, b]
        cols += [b, a]
        vals += [np.full(a.size, -g), np.full(a.size, -g)]
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N)) + sp.diags(diag)
    fixed = np.unique(np.asarray(fixed, dtype=int))
    u = np.zeros(N)
    if fixed.size == 0:
        raise ValueError("no VDD bump in the solve domain")
    free = np.setdiff1d(np.arange(N), fixed)
    A = A.tocsr()
    u[free] = spl.spsolve(A[free][:, free].tocsc(), load.ravel()[free])
    return u.reshape(ny, nx)


def cell_drop(grid, w_mm2, bump_pitch, vdd=0.7, load_step=8.64):
    """Max VDD drop (V) in a periodic fully-bumped cell on the exact stripe network of one net: M8 rows (pitch p8) and
    M9 columns (pitch p9) as resistor chains, nodes at every crossing and every `load_step` (the partitions' M7 PG
    pitch: the load enters M8 through the M7-M8 vias) along each stripe; VDD bumps on the checkerboard lattice, each
    tied to the nearest point of its nearest M9 column (die_trial.bumps_tcl ties a bump to the nearest M9 stripe)."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    g = {s["layer"]: s for s in grid}
    p8, p9 = g["M8"]["pitch_um"], g["M9"]["pitch_um"]
    p = bump_pitch
    kx = max(1, round(p9 / (2 * p)))
    ky = max(1, round(p8 / (2 * p)))
    Lx, Ly = 2 * p * kx, 2 * p * ky
    ncol, nrow = max(1, round(Lx / p9)), max(1, round(Ly / p8))
    mx, my = max(1, round(Lx / ncol / load_step)), max(1, round(Ly / nrow / load_step))
    NX, NY = ncol * mx, nrow * my
    dx, dy = Lx / NX, Ly / NY
    nid = -np.ones((NY, NX), int)
    on = np.zeros((NY, NX), bool)
    on[::my, :] = True
    on[:, ::mx] = True
    nid[on] = np.arange(on.sum())
    N = int(on.sum())
    rows, cols, vals = [], [], []
    diag = np.zeros(N)

    def link(a, b, gg):
        rows.extend([a, b]); cols.extend([b, a]); vals.extend([-gg, -gg]); diag[a] += gg; diag[b] += gg
    g8 = g["M8"]["width_um"] / (RSQ["M8"] * dx)
    g9 = g["M9"]["width_um"] / (RSQ["M9"] * dy)
    for j in range(0, NY, my):
        for i in range(NX):
            link(nid[j, i], nid[j, (i + 1) % NX], g8)
    for i in range(0, NX, mx):
        for j in range(NY):
            link(nid[j, i], nid[(j + 1) % NY, i], g9)
    load = np.zeros(N)
    load[nid[::my, :].ravel()] = w_mm2 * 1e-6 / vdd * (Ly / nrow) * dx     # M8 row strip area per row node
    fixed = set()
    for i in range(2 * kx):
        for j in range(2 * ky):
            if (i + j) % 2 == 0:
                c = (int(round(i * p / (Lx / ncol))) % ncol) * mx
                fixed.add(int(nid[int(round(j * p / dy)) % NY, c]))
    A = sp.csr_matrix((vals, (rows, cols)), shape=(N, N)) + sp.diags(diag)
    fixed = np.array(sorted(fixed))
    free = np.setdiff1d(np.arange(N), fixed)
    u = np.zeros(N)
    u[free] = spl.spsolve(A.tocsr()[free][:, free].tocsc(), load[free])
    return float(u.max())


def coarse_h(pitch):
    """Coarse lattice spacing for a bump lattice pitch: pitch/2 (>= 120 um), pitch (60-120), else a multiple of 2 x pitch
    (every node is then a VDD bump; the exact-stripe cell carries the whole local drop)."""
    if pitch >= 120:
        return pitch / 2
    if pitch >= 60:
        return pitch
    return 2 * pitch * math.ceil(30 / pitch)


def _coarse_cell(rx, ry, w_mm2, bump_pitch, vdd=0.7):
    """Max drop of the coarse model itself on a periodic fully-bumped torus (subtracted from the exact cell)."""
    import numpy as np
    h = coarse_h(bump_pitch)
    if h > bump_pitch:
        return 0.0
    n = int(round(2 * bump_pitch / h))
    k = int(round(bump_pitch / h))
    fixed = [j * n + i for i in range(0, n, k) for j in range(0, n, k) if ((i // k) + (j // k)) % 2 == 0]
    load = np.full((n, n), w_mm2 * 1e-6 / vdd * h * h)
    return float(_solve(n, n, 1 / rx, 1 / ry, load, fixed, periodic=True).max())


def _lattice(lo, hi, origin, h):
    import numpy as np
    k0, k1 = math.ceil((lo - origin) / h - 0.5), math.floor((hi - origin) / h - 0.5)
    return k0, origin + h * np.arange(k0, k1 + 1)


def coarse_map(P, model, grid, pitch, origin, domain, bumps, fixed_rects=(), vdd=0.7):
    """Coarse VDD drop map (V): anisotropic sheet FD on a lattice of spacing coarse_h(pitch) aligned with the bump
    lattice (origin, pitch); VDD bumps and every node inside `fixed_rects` (separately supplied PHY windows) are 0-drop
    nodes; window edges are open.  -> (xs, ys, u)"""
    import numpy as np
    X0, Y0, X1, Y1 = domain
    h = coarse_h(pitch)
    kx0, xs = _lattice(X0, X1, origin[0], h)
    ky0, ys = _lattice(Y0, Y1, origin[1], h)
    cx0, cx1 = np.maximum(xs - h / 2, X0), np.minimum(xs + h / 2, X1)
    cy0, cy1 = np.maximum(ys - h / 2, Y0), np.minimum(ys + h / 2, Y1)
    dens = np.zeros((ys.size, xs.size))
    for r, d in model["loads"]:
        ox = np.clip(np.minimum(cx1, r[2]) - np.maximum(cx0, r[0]), 0, None)
        oy = np.clip(np.minimum(cy1, r[3]) - np.maximum(cy0, r[1]), 0, None)
        if ox.any() and oy.any():
            dens += d * np.outer(oy, ox)          # W/mm2 x um2
    load = np.clip(dens, 0, None) * 1e-6 / vdd    # A
    fixed = []
    for net, x, y in bumps:
        if net != "VDD" or not (X0 <= x <= X1 and Y0 <= y <= Y1):
            continue
        i, j = int(round((x - origin[0]) / h)) - kx0, int(round((y - origin[1]) / h)) - ky0
        if 0 <= i < xs.size and 0 <= j < ys.size:
            fixed.append(j * xs.size + i)
    for r in fixed_rects:
        ii = np.nonzero((xs >= r[0]) & (xs <= r[2]))[0]
        jj = np.nonzero((ys >= r[1]) & (ys <= r[3]))[0]
        fixed += [j * xs.size + i for j in jj for i in ii]
    rx, ry = _rx_ry(grid)
    u = _solve(xs.size, ys.size, 1 / rx, 1 / ry, load, fixed)
    return xs, ys, u


def _bump_origin(P, pitch):
    nxb, nyb = int(P.W // pitch), int(P.H // pitch)
    return (P.W - (nxb - 1) * pitch) / 2, (P.H - (nyb - 1) * pitch) / 2


def _phy_lattice(rect, q):
    x0, y0, x1, y1 = rect
    nx, ny = max(1, int((x1 - x0) // q)), max(1, int((y1 - y0) // q))
    sx, sy = x0 + ((x1 - x0) - (nx - 1) * q) / 2, y0 + ((y1 - y0) - (ny - 1) * q) / 2
    return (sx, sy), [("VDD" if (i + j) % 2 == 0 else "VSS", round(sx + i * q, 3), round(sy + j * q, 3))
                      for i in range(nx) for j in range(ny)]


def estimate(P, model, grid, bump_pitch=150.0, vdd=0.7, domain=None, regions=None):
    """Per-region worst VDD drop (mV) for `grid`.  -> ({region: mV}, worst mV, detail)
      core: die coarse map (core C4 lattice; PHY windows held as separately supplied) + the exact-stripe cell
            correction (cell - coarse cell) at the core density and core bump pitch;
      PHY window: the window alone (its own PG micro-bump lattice, edges open) coarse + its cell correction.
    `domain` restricts the core solve to a window (open edges, window-local bumps) for like-for-like PDNSim checks."""
    import numpy as np
    rx, ry = _rx_ry(grid)
    core = model["core_w_mm2"]
    loc = (cell_drop(grid, core, bump_pitch, vdd) - _coarse_cell(rx, ry, core, bump_pitch, vdd=vdd)) if core > 0 else 0.0
    dom = domain or (0.0, 0.0, P.W, P.H)
    io = _pg_io(P, Path(P.path).parent if getattr(P, "path", None) else ".")
    phy = [r for r in model["regions"] if r["kind"] == "phy"]
    xs, ys, u = coarse_map(P, model, grid, bump_pitch, _bump_origin(P, bump_pitch), dom,
                           D.bump_grid(P, io, pitch=bump_pitch), [r["rect_um"] for r in phy], vdd=vdd)
    inphy = np.zeros(u.shape, bool)
    for r in phy:
        q = r["rect_um"]
        inphy |= np.outer((ys >= q[1]) & (ys <= q[3]), (xs >= q[0]) & (xs <= q[2]))
    out = {}
    for r in regions if regions is not None else model["regions"]:
        best = 0.0
        if r["kind"] == "phy":
            q = r["rect_um"]
            dq = [max(q[0], dom[0]), max(q[1], dom[1]), min(q[2], dom[2]), min(q[3], dom[3])]
            if dq[2] > dq[0] and dq[3] > dq[1]:
                pq = r["pg_bump_pitch_um"]
                org, pb = _phy_lattice(q, pq)
                _, _, up = coarse_map(P, model, grid, pq, org, dq, pb, vdd=vdd)
                cc = cell_drop(grid, r["w_mm2"], pq, vdd) - _coarse_cell(rx, ry, r["w_mm2"], pq, vdd=vdd)
                best = float(up.max()) + max(0.0, cc)
        else:
            d = r.get("w_mm2", core)
            add = max(0.0, loc) * (d / core if core else 0.0)
            for q in [model["rects"][n] for n in r["parts"]]:
                mk = np.outer((ys >= q[1]) & (ys <= q[3]), (xs >= q[0]) & (xs <= q[2])) & ~inphy
                if mk.any():
                    best = max(best, float(u[mk].max()) + add)
        out[r["name"]] = round(best * 1e3, 3)
    worst = max(out.values()) if out else 0.0
    return out, worst, dict(local_mv=round(loc * 1e3, 3), coarse_max_mv=round(float(u.max()) * 1e3, 3),
                            rx_ohm_sq=round(rx, 4), ry_ohm_sq=round(ry, 4), nodes=int(u.size))


# --------------------------------------------------------------------------------------------------------- tracks
def track_frac(P, layer, stripes_w, pitch, offset, nets=2, span=None):
    """Share of `layer` routing tracks a die-wide stripe set takes: a track is taken when its wire (min width) would sit
    closer than the stripe's spacing rule (ASAP7 SPACINGTABLE by stripe width) -- i.e. stripe width + spacing to the
    neighbouring track, counted on the P.layers track lattice."""
    L = P.layers[layer]
    tp, to = L["pitch_um"], L.get("offset_um", 0.0)
    span = span or BASE_PITCH * 16 * max(1, round(pitch / BASE_PITCH))
    reach = stripes_w / 2 + spacing(stripes_w) + MIN_W.get(layer, tp / 2) / 2 - 1e-9
    centers = []
    pos = offset
    while pos < span + pitch:
        for j in range(nets):
            centers.append(pos + j * pitch / nets)
        pos += pitch
    n = int(span / tp)
    taken = 0
    import bisect
    centers.sort()
    for i in range(n):
        c = to + i * tp
        k = bisect.bisect_left(centers, c)
        if any(abs(c - centers[q]) < reach for q in (k - 1, k) if 0 <= q < len(centers)):
            taken += 1
    return taken / n


def grid_entry(layer, pitch, w=STRIPE_W):
    return dict(layer=layer, width_um=w, pitch_um=round(pitch, 4), offset_um=round(pitch / 2, 4), nets=["VDD", "VSS"])


def tracks_of(P, grid):
    return {s["layer"]: round(track_frac(P, s["layer"], s["width_um"], s["pitch_um"], s["offset_um"],
                                         len(s.get("nets", ["VDD", "VSS"]))), 4) for s in grid}


# --------------------------------------------------------------------------------------------------------- sizing
def size_grid(P, plan_dir, power=None, ir_budget_frac=0.05, vdd=0.7, phy_w_per_macro=4.37, core_w_mm2=None,
              m8_max_frac=0.5, m9_max_frac=0.85, bump_pitch_um=150.0, gate="all", core_watts=None):
    """Smallest M8 share (then M9) whose worst per-region VDD IR <= ir_budget_frac x vdd.
    gate="all": every region (core + PHY windows) must meet the budget; "core": only the core region (PHY windows
    reported, to be met by a PHY-local grid / domain)."""
    model = load_model(P, plan_dir, power, phy_w_per_macro, core_w_mm2, core_watts)
    budget = ir_budget_frac * vdd * 1e3
    opts = []
    for p in PITCHES:
        opts.append((p, track_frac(P, "M8", STRIPE_W, p, p / 2), track_frac(P, "M9", STRIPE_W, p, p / 2)))
    m8o = sorted([(f8, p) for p, f8, _ in opts if f8 <= m8_max_frac])
    m9o = sorted([(f9, p) for p, _, f9 in opts if f9 <= m9_max_frac])
    cands, chosen = [], None
    current = [s for s in P.die.get("pg", {}).get("grid", [])]
    if {s["layer"] for s in current} >= {"M8", "M9"}:
        r, w, det = estimate(P, model, current, bump_pitch_um, vdd)
        cands.append(dict(label="plan die.pg.grid", grid=current, tracks=tracks_of(P, current), worst_mv=w,
                          regions_mv=r, **det))
    for f8, p8 in m8o:
        hit = None
        for f9, p9 in m9o:
            g = [grid_entry("M8", p8), grid_entry("M9", p9)]
            r, w, det = estimate(P, model, g, bump_pitch_um, vdd)
            cands.append(dict(label=f"M8 {p8:g} / M9 {p9:g}", grid=g, tracks=dict(M8=round(f8, 4), M9=round(f9, 4)),
                              worst_mv=w, regions_mv=r, **det))
            gw = w if gate == "all" else max(v for k, v in r.items() if k == "core" or k.startswith("core:"))
            if gw <= budget:
                hit = cands[-1]
                break
        if hit:
            chosen = hit
            break
    best = chosen or min(cands, key=lambda c: c["worst_mv"])
    regions = []
    for rg in model["regions"]:
        row = {k: rg[k] for k in ("name", "rect_um", "power_w", "area_mm2", "w_mm2")}
        row.update(kind=rg["kind"], ir_est_mv=best["regions_mv"].get(rg["name"]))
        if rg["kind"] == "phy":
            row["part"] = rg.get("part")
        regions.append(row)
    basis = model["basis"] + [
        f"VDD {vdd} V; IR budget {ir_budget_frac:g} x VDD = {budget:.1f} mV per region (VDD net, ideal bump sources, "
        f"as PDNSim)",
        f"core C4 power bumps: die_trial.bump_grid pitch {bump_pitch_um:g} um, VDD/VSS by parity, none in IO windows / "
        "channels",
        "PHY windows: ASSUMPTION their own PG micro-bumps (PHY_ASSUMPTIONS bump contract 1-3, BUMP.UBUMP 45 um) at PG "
        "share UCIe 0.30 (UCIE.A.PG_SHARE) / SerDes + HBM 0.45 (UCIE.S.PG_SHARE as nearest published proxy) -> "
        "VDD/VSS lattice %g / %g um; the plan's 150-um window sites are all signal" % (phy_pg_pitch("ucie"), phy_pg_pitch("serdes")),
        "metal: ASAP7 setRC M8 %.4f / M9 %.4f ohm/sq (per-um R x 0.04-um min width); vias ignored" % (RSQ["M8"], RSQ["M9"]),
        f"stripes {STRIPE_W} um (below the 0.5-um wide-spacing step), VDD at pitch/2, VSS at pitch, die-wide (schema "
        "die.pg.grid has no region-limited stripes)",
        "tracks taken: track centre closer than stripe half-width + SPACINGTABLE spacing + half min width, on the "
        "P.layers track lattice",
        "IR model: coarse anisotropic FD on the bump lattice (h = pitch/2) + periodic exact-stripe unit cell correction"]
    basis.append(f"gate: {gate} (" + ("every region" if gate == "all" else "core region only; PHY windows reported") + ")")
    return dict(die=P.name, grid=best["grid"], regions=regions, tracks=best["tracks"], basis="\n".join(basis), gate=gate,
                feasible=chosen is not None, budget_mv=round(budget, 3), worst_mv=best["worst_mv"],
                model=dict(local_mv=best["local_mv"], coarse_max_mv=best["coarse_max_mv"], rx_ohm_sq=best["rx_ohm_sq"],
                           ry_ohm_sq=best["ry_ohm_sq"], nodes=best["nodes"]),
                bump_pitch_um=bump_pitch_um, vdd=vdd, ir_budget_frac=ir_budget_frac,
                part_w={k: round(v, 6) for k, v in model["part_w"].items()},
                candidates=[{k: c[k] for k in ("label", "tracks", "worst_mv", "regions_mv", "grid")} for c in cands])


# ------------------------------------------------------------------------------------------------- PDNSim runs
class _PG:
    """Plan view with a replaced die.pg.grid (die_trial helpers read P.die['pg']['grid'])."""
    def __init__(self, P, grid):
        self.__dict__.update(P.__dict__)
        self.die = dict(P.die, pg=dict(P.die.get("pg", {}), grid=grid))


def _snap(v, q):
    return math.floor(v / q + 1e-9) * q


def default_windows(P, pg, margin=600.0, core_um=1500.0):
    """Verification windows: the worst core spot and every distinct PHY window (with `margin` of core around it)."""
    win = []
    for r in pg["regions"]:
        if r["kind"] != "phy":
            continue
        x0, y0, x1, y1 = r["rect_um"]
        win.append(dict(name=r["name"], rect_um=[max(0, x0 - margin), max(0, y0 - margin), min(P.W, x1 + margin),
                                                 min(P.H, y1 + margin)]))
    cx, cy = P.W / 2, P.H / 2
    win.append(dict(name="core_centre", rect_um=[cx - core_um / 2, cy - core_um / 2, cx + core_um / 2, cy + core_um / 2]))
    return win


def window_kit(P, plan_dir, pg, out, name, rect, tile=86.4, power=None, phy_w=4.37, core_w_mm2=None):
    """PDNSim on a die window (phy_ir._window_kit style): the sized die grid, the die's own bumps inside the window,
    load blocks (M7 PG pins, as the partition kits) tiling the window, each at the region density under it."""
    import numpy as np
    q = max(s["pitch_um"] for s in pg["grid"])
    q = max(q, BASE_PITCH)
    x0, y0 = _snap(rect[0], q), _snap(rect[1], q)
    x1, y1 = min(P.W, x0 + _snap(rect[2] - x0, q) or q), min(P.H, y0 + _snap(rect[3] - y0, q) or q)
    w, h = x1 - x0, y1 - y0
    Pg = _PG(P, pg["grid"])
    model = load_model(P, plan_dir, power, phy_w, core_w_mm2 if core_w_mm2 is not None else pg.get("core_w_mm2"))
    io = _pg_io(P, plan_dir)
    bp = pg.get("bump_pitch_um", 150.0)
    allb = pg_bumps(P, io, pitch=bp)
    bumps = [(n, round(x - x0, 3), round(y - y0, 3)) for n, x, y in allb if x0 < x < x1 and y0 < y < y1]
    out = Path(out)
    (out / "psm").mkdir(parents=True, exist_ok=True)
    nx_t, ny_t = max(1, int(round(w / tile))), max(1, int(round(h / tile)))
    bw, bh = w / nx_t, h / ny_t
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "MACRO irblk", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;",
         f"  SIZE {bw:.4f} BY {bh:.4f} ;"]
    for net, j in (("VDD", 0), ("VSS", 1)):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {'POWER' if net == 'VDD' else 'GROUND'} ;", "    PORT"]
        c = 4.128 + j * (0.288 + 0.096)
        while c + 0.144 < bw:
            L += ["      LAYER M7 ;", f"        RECT {c - 0.144:.4f} 0 {c + 0.144:.4f} {bh:.4f} ;"]
            c += 8.64
        L += ["    END", f"  END {net}"]
    L += ["  OBS", f"    LAYER M1 ;\n      RECT 0 0 {bw:.4f} {bh:.4f} ;", "  END", "END irblk", "END LIBRARY", ""]
    (out / "psm" / "irblk.lef").write_text("\n".join(L))
    blks = []
    for i in range(nx_t):
        for j in range(ny_t):
            r = [x0 + i * bw, y0 + j * bh, x0 + (i + 1) * bw, y0 + (j + 1) * bh]
            pw = sum(d * _ov(r, lr) for lr, d in model["loads"]) * 1e-6
            blks.append((f"u_b{i}_{j}", i * bw, j * bh, max(0.0, pw)))
    (out / "psm" / "psm.v").write_text("module irwin ();\n" + "".join(f"  irblk {n} ();\n" for n, *_ in blks) + "endmodule\n")
    (out / "psm" / "pdn.tcl").write_text(D.psm_pdn_tcl(Pg))
    (out / "psm" / "bumps.tcl").write_text(D.bumps_tcl(Pg, bumps))
    t = ["set t0 [clock seconds]", f"read_lef {D.TECH_LEF}", f"read_lef {D.SC_LEF}", "read_lef /work/psm/irblk.lef",
         f"foreach f [glob {D.PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{ read_liberty $f }}",
         "read_verilog /work/psm/psm.v", "link_design irwin",
         f"initialize_floorplan -die_area {{0 0 {D.gen_phys._um(w)} {D.gen_phys._um(h)}}} -core_area {{0 0 {D.gen_phys._um(w)} {D.gen_phys._um(h)}}} -site asap7sc7p5t",
         "source /work/psm/tracks.tcl", "set dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
         "proc ot_pl {n x y} { global dbu; set i [[ord::get_db_block] findInst $n]; $i setOrient R0; "
         "$i setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]; $i setPlacementStatus FIRM }"]
    t += [f"ot_pl {n} {x:.4f} {y:.4f}" for n, x, y, _ in blks]
    t += ["source /work/psm/pdn.tcl", "pdngen", "puts \"OT_T pdngen [expr {[clock seconds]-$t0}]\"",
          "source /work/psm/bumps.tcl", "puts \"OT_T bumps [expr {[clock seconds]-$t0}]\"", f"source {D.PLAT}/setRC.tcl"]
    t += [f"set_pdnsim_inst_power -inst {n} -power {pw:.8f}" for n, _, _, pw in blks if pw > 0]
    t += ["foreach n {VDD VSS} { if {[catch {check_power_grid -net $n} e]} { puts \"OT_PG_CHECK_FAIL $n $e\" } "
          "else { puts \"OT_PG_CHECK_OK $n\" } }",
          "if {[catch {analyze_power_grid -net VDD -error_file /work/psm/psm_VDD.rpt -voltage_file /work/psm/ir_VDD.csv} e]} "
          "{ puts \"OT_PSM_FAIL $e\" } else { puts OT_PSM_OK }",
          "puts \"OT_T psm [expr {[clock seconds]-$t0}]\"", "puts OT_DONE"]
    (out / "psm" / "tracks.tcl").write_text(D.coarse_tracks(P, 0.72))
    (out / "psm" / "psm.tcl").write_text("\n".join(t) + "\n")
    (out / "run_psm.sh").write_text(D.run_sh("psm", 64, 8, "/usr/bin/time -v openroad -no_init -threads 8 -exit "
                                                       "/work/psm/psm.tcl > /work/psm/psm.log 2>&1; ot_psm_rc=\\$?; echo EXIT \\$ot_psm_rc >> /work/psm/psm.log; (exit \\$ot_psm_rc)"))
    os.chmod(out / "run_psm.sh", 0o755)
    # the model's own estimate on the same domain (window-local bumps, open window edges) -> like-for-like check
    regs = [r for r in model["regions"] if r["kind"] == "phy" and _ov(r["rect_um"], [x0, y0, x1, y1]) > 0]
    regs.append(dict(name="core", kind="core", parts=[n for n in model["core_parts"]
                                                      if _ov(model["rects"][n], [x0, y0, x1, y1]) > 0]))
    est, worst, det = estimate(P, model, pg["grid"], bp, pg.get("vdd", 0.7), domain=(x0, y0, x1, y1), regions=regs)
    meta = dict(die=P.name, ir_budget_mv=pg.get("budget_mv"), window=name, window_um=[x0, y0, x1, y1], area_mm2=round(w * h * 1e-6, 3), grid=pg["grid"],
                power_w=round(sum(b[3] for b in blks), 4), load_blocks=len(blks), bumps=len(bumps),
                bumps_vdd=sum(1 for b in bumps if b[0] == "VDD"), est_regions_mv=est, est_worst_mv=worst, est_detail=det,
                scope="window PDNSim: window edges open (no feed from outside), window-local bumps; the estimate "
                      "above is the same model on the same domain")
    (out / "irwin.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def die_kit(P, plan_dir, pg, kit, out):
    """Full-die PDNSim on a die_trial kit's abstracts with the sized grid and per-partition power (die_trial psm form).
    NOTE: a 307-mm2 full-die PSM segfaulted in IRSolver::solve at 119 GB (TRIAL-S81 10-24); prefer --mode window."""
    out = Path(out)
    (out / "psm").mkdir(parents=True, exist_ok=True)
    if Path(kit).resolve() != out.resolve():
        shutil.copytree(Path(kit) / "abstracts", out / "abstracts", dirs_exist_ok=True)
        shutil.copytree(Path(kit) / "grt", out / "grt", dirs_exist_ok=True)
        shutil.copy(Path(kit) / "psm" / "psm.v", out / "psm" / "psm.v")
    Pg = _PG(P, pg["grid"])
    lefs = sorted(f.name for f in (out / "abstracts").glob("*.lef"))
    power = {n: pg["part_w"].get(n, 0.0) for n in P.parts}
    bumps = pg_bumps(P, _pg_io(P, plan_dir), pitch=pg.get("bump_pitch_um", 150.0))
    (out / "psm" / "pdn.tcl").write_text(D.psm_pdn_tcl(Pg))
    (out / "psm" / "bumps.tcl").write_text(D.bumps_tcl(Pg, bumps))
    (out / "psm" / "power.tcl").write_text("\n".join(f"set_pdnsim_inst_power -inst {D.sv(n)} -power {w:.6f}"
                                                     for n, w in sorted(power.items())) + "\n")
    (out / "psm" / "psm.tcl").write_text(D.psm_tcl(Pg, lefs, power, bumps))
    (out / "run_psm.sh").write_text(D.run_sh("psm", 64, 16, "/usr/bin/time -v openroad -no_init -threads 16 -exit "
                                                        "/work/psm/psm.tcl > /work/psm/psm.log 2>&1"))
    os.chmod(out / "run_psm.sh", 0o755)
    meta = dict(die=P.name, ir_budget_mv=pg.get("budget_mv"), mode="die", grid=pg["grid"], total_w=round(sum(power.values()), 3), bumps=len(bumps),
                est_regions_mv={r["name"]: r["ir_est_mv"] for r in pg["regions"]}, est_worst_mv=pg["worst_mv"])
    (out / "irwin.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def report(run):
    run = Path(run)
    r = D.psm_report(run)
    m = json.loads((run / "irwin.json").read_text())
    vf = run / "psm" / "ir_VDD.csv"
    if vf.is_file() and m.get("mode") != "die":
        import csv
        x0, y0 = m["window_um"][:2]
        rows = list(csv.DictReader(vf.open()))
        pts = [(float(q["X location"]) + x0, float(q["Y location"]) + y0, (0.7 - float(q["Voltage"])) * 1e3) for q in rows]
        P = S.Plan(S.load(m["plan"]), Path(m["plan"])) if m.get("plan") else None
        per = {}
        if P:
            model = load_model(P, Path(m["plan"]).parent)
            for rg in model["regions"]:
                rr = [rg["rect_um"]] if rg["kind"] == "phy" else [model["rects"][n] for n in rg["parts"]]
                v = [d for x, y, d in pts if any(q[0] <= x <= q[2] and q[1] <= y <= q[3] for q in rr)]
                if v:
                    per[rg["name"]] = round(max(v), 3)
        r["psm_regions_mv"] = per
    budget = m.get("ir_budget_mv")
    drop = r.get("worst_ir_drop_mv")
    r["ir_budget_mv"] = budget
    r["ir_verdict"] = ("NOT RUN" if r.get("status") != "OK" or budget is None or drop is None
                       else "PASS" if drop <= budget else "FAIL")
    r.update({k: m.get(k) for k in ("die", "window", "window_um", "grid", "power_w", "est_regions_mv", "est_worst_mv")})
    (run / "result.json").write_text(json.dumps(r, indent=1) + "\n")
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("size")
    s.add_argument("plan")
    s.add_argument("--out", required=True)
    s.add_argument("--ir-budget-frac", type=float, default=0.05)
    s.add_argument("--core-w-mm2", type=float)
    s.add_argument("--core-watts", type=float, help="explicit non-PHY watts; PHY windows are charged separately")
    s.add_argument("--phy-w", type=float, default=4.37)
    s.add_argument("--vdd", type=float, default=0.7)
    s.add_argument("--m8-max-frac", type=float, default=0.5)
    s.add_argument("--m9-max-frac", type=float, default=0.85)
    s.add_argument("--bump-pitch", type=float, default=150.0)
    s.add_argument("--power", help="JSON {core_w_mm2, types: {type: W/mm2}}")
    s.add_argument("--gate", choices=("all", "core"), default="all")
    p = sub.add_parser("psm")
    p.add_argument("plan")
    p.add_argument("--pg", required=True)
    p.add_argument("--kit", help="die_trial kit dir (mode die: its abstracts)")
    p.add_argument("--out", help="run dir (default KIT/psm_infra or PG_DIR/psm)")
    p.add_argument("--mode", choices=("window", "die"), default="window")
    p.add_argument("--window", action="append", help="NAME=x0,y0,x1,y1 (default: every PHY window + core centre)")
    p.add_argument("--only", action="append", help="default windows: keep only these names")
    p.add_argument("--margin", type=float, default=600.0, help="core margin around each PHY window (um)")
    p.add_argument("--core-um", type=float, default=1500.0, help="core-centre window edge (um)")
    p.add_argument("--grid-from-plan", action="store_true", help="verify the plan's own die.pg.grid instead of pg.json's")
    r = sub.add_parser("report")
    r.add_argument("run")
    a = ap.parse_args(argv)
    if a.cmd == "report":
        result = report(a.run)
        print(json.dumps(result, indent=1))
        return 0 if result["ir_verdict"] == "PASS" else 1
    P = S.Plan(S.load(a.plan), Path(a.plan))
    plan_dir = Path(a.plan).parent
    if a.cmd == "size":
        power = json.loads(Path(a.power).read_text()) if a.power else None
        res = size_grid(P, plan_dir, power, a.ir_budget_frac, a.vdd, a.phy_w, a.core_w_mm2, a.m8_max_frac,
                        a.m9_max_frac, a.bump_pitch, a.gate, a.core_watts)
        res.update(plan=os.path.relpath(Path(a.plan).resolve(), HERE.parent.parent),
                   plan_sha256=__import__("hashlib").sha256(Path(a.plan).read_bytes()).hexdigest(),
                   core_w_mm2=a.core_w_mm2, phy_w_per_macro=a.phy_w, tool="tools/die_plan/infra_pg.py")
        res["core_w_mm2"] = next(r["w_mm2"] for r in res["regions"] if r["name"] == "core")
        Path(a.out).mkdir(parents=True, exist_ok=True)
        (Path(a.out) / "pg.json").write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({k: res[k] for k in ("grid", "tracks", "worst_mv", "budget_mv", "feasible")}, indent=1))
        for row in res["regions"]:
            print(f"  {row['name']:34s} {row['power_w']:9.3f} W {row['w_mm2']:7.3f} W/mm2  IR est {row['ir_est_mv']} mV")
        return 0
    pg = json.loads(Path(a.pg).read_text())
    if a.mode == "die":
        if not a.kit:
            ap.error("--mode die needs --kit")
        out = Path(a.out or Path(a.kit) / "psm_infra")
        print(json.dumps(die_kit(P, plan_dir, pg, a.kit, out), indent=1))
        return 0
    out = Path(a.out or Path(a.pg).parent / "psm")
    if a.grid_from_plan:
        pg = dict(pg, grid=P.die["pg"]["grid"])
    wins = default_windows(P, pg, a.margin, a.core_um)
    if a.only:
        wins = [w for w in wins if w["name"] in a.only]
    if a.window:
        wins = [dict(name=w.split("=")[0], rect_um=[float(v) for v in w.split("=")[1].split(",")]) for w in a.window]
    for w in wins:
        m = window_kit(P, plan_dir, pg, out / w["name"], w["name"], w["rect_um"], phy_w=pg.get("phy_w_per_macro", 4.37),
                       core_w_mm2=pg.get("core_w_mm2"))
        m["plan"] = str(Path(a.plan).resolve())
        (out / w["name"] / "irwin.json").write_text(json.dumps(m, indent=1) + "\n")
        print(w["name"], m["window_um"], m["area_mm2"], "mm2", m["power_w"], "W est", m["est_worst_mv"], "mV")
    return 0


if __name__ == "__main__":
    sys.exit(main())
