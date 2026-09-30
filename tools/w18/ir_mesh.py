#!/usr/bin/env python3
"""W18: full-die static IR of the V4.1 ROM layer die's top power grid (M8/M9 + micro-bumps), solved as a
resistive mesh with scipy -- the die-level level of the hierarchical PDN.

Why not PSM at this level: OpenROAD PSM draws an instance's current at one node, so an 815 mm^2 die needs
tens of thousands of current-map tiles; the flat run went out of memory at 115 GB in check_power_grid, and
windowed runs could not connect point-load tiles to the M8/M9 grid (PSM-0069).  The cluster and element
levels below are PSM runs (tools/w18/die_pdn.py cluster, the routed pair); this level is a mesh whose
resistances come from the same ASAP7 constants PSM uses (platform setRC.tcl), checked against a closed form.

Grid: a uniform mesh of pitch p um; each node is an M8/M9 crossing region.  One net (VDD; VSS is its mirror):
  * M9 vertical and M8 horizontal straps, 2.0 um wide per 16 um per net (tools/w18/die_pdn.py M8/M9):
    effective sheet resistance = R_sheet x (16 / 2); R_sheet = setRC R/um x the min width;
  * micro-bumps on a 40 um array, 1/3 VDD, each R_bump (ASSUMED) to an ideal regulator at VDD;
  * loads: every block's power (tools/w18/die_pdn.py power map: clusters per pair row, hub, service, PHYs,
    links) spread over the nodes its rectangle covers, drawn as constant current P / VDD.

    python3 tools/w18/ir_mesh.py --floorplan F --pack P --pair-w 0.2663 [--duty D] --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/w18"))
import die_floorplan as DF  # noqa: E402

VDD = 0.7
# platform setRC.tcl: kohm/um at the layer's minimum width (M8/M9 0.040 um)
R_UM = {"M8": 8.44765e-3 * 1e3, "M9": 8.89556e-3 * 1e3}
WMIN = {"M8": 0.040, "M9": 0.040}
STRAP_W, STRAP_PITCH = 2.0, 16.0            # per net
BUMP_PITCH = 40.0
BUMP_R = 0.05                               # ohm per VDD bump incl. interposer/package path (ASSUMED)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def blocks(fp: dict, pk: dict, a) -> list[tuple[str, float, float, float, float, float]]:
    """(kind, x, y, w, h, watts) for every block of the die."""
    out = []
    rp = fp["cluster_rule"]["row_pitch_um"]
    for c in fp["clusters"]:
        for r in range(c["rows"]):
            w = (a.duty * a.pair_w + (1 - a.duty) * a.pair_idle_w) if r < c["used_rows"] else a.pair_idle_w
            out.append(("cluster", c["x"], c["y"] + r * rp, c["w"], rp, w))
    for nm, r in fp["hub"]["parts"].items():
        out.append(("hub", r["x"], r["y"], r["w"], r["h"], a.hub_w_total * r["w"] * r["h"] /
                    sum(v["w"] * v["h"] for v in fp["hub"]["parts"].values())))
    for nm, r in fp["service"].items():
        out.append(("service", r["x"], r["y"], r["w"], r["h"], a.service_w))
    for nm, master, x, y, o, grp in pk["instances"]:
        if grp == "HBM_PHY":
            m = DF.lef_macro(DF.PK.MACRO_DIR / master / f"{master}.lef")
            out.append(("hbm_phy", x, y, m["w"], m["h"], a.phy_w))
        elif grp == "SERDES":
            out.append(("serdes", x, y, 1000.08, 401.76, a.serdes_w))
        elif grp == "UCIE":
            out.append(("ucie", x, y, 1043.28, 388.8, a.ucie_w))
    return out


def solve(W, H, blk, p):
    nx, ny = int(math.ceil(W / p)) + 1, int(math.ceil(H / p)) + 1
    n = nx * ny
    idx = lambda i, j: j * nx + i  # noqa: E731
    rsq = {l: R_UM[l] * WMIN[l] * (STRAP_PITCH / STRAP_W) for l in R_UM}     # effective ohm/sq per net
    gx = 1.0 / rsq["M8"]          # horizontal branch between x-neighbours: R = rsq * (p / p)
    gy = 1.0 / rsq["M9"]
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    I = np.zeros(n)
    for j in range(ny):
        base = j * nx
        i = np.arange(nx - 1)
        a_ = base + i
        rows += [a_, a_ + 1]; cols += [a_ + 1, a_]; vals += [np.full(nx - 1, -gx)] * 2
        diag[a_] += gx; diag[a_ + 1] += gx
    for j in range(ny - 1):
        a_ = j * nx + np.arange(nx)
        rows += [a_, a_ + nx]; cols += [a_ + nx, a_]; vals += [np.full(nx, -gy)] * 2
        diag[a_] += gy; diag[a_ + nx] += gy
    # bumps: 1/3 of a 40 um array; a bump ties its nearest node to VDD through BUMP_R
    gb = 1.0 / BUMP_R
    nb = 0
    bx = np.arange(BUMP_PITCH / 2, W, BUMP_PITCH)
    by = np.arange(BUMP_PITCH / 2, H, BUMP_PITCH)
    for kj, y in enumerate(by):
        for ki, x in enumerate(bx):
            if (ki + kj) % 3 != 0:
                continue
            k = idx(int(round(x / p)), int(round(y / p)))
            diag[k] += gb
            I[k] += gb * VDD
            nb += 1
    # loads
    total = 0.0
    for kind, x, y, w, h, watts in blk:
        i0, i1 = int(math.floor(x / p)), int(math.ceil((x + w) / p))
        j0, j1 = int(math.floor(y / p)), int(math.ceil((y + h) / p))
        i1, j1 = max(i1, i0 + 1), max(j1, j0 + 1)
        ii, jj = np.meshgrid(np.arange(i0, min(i1, nx)), np.arange(j0, min(j1, ny)))
        ks = (jj * nx + ii).ravel()
        cur = watts / VDD
        I[ks] -= cur / len(ks)
        total += cur
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag)
    G = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
    M = spla.spilu(G.tocsc(), drop_tol=1e-4, fill_factor=10)
    v, info = spla.cg(G, I, rtol=1e-10, maxiter=5000, M=spla.LinearOperator(G.shape, M.solve))
    return v.reshape(ny, nx), dict(nodes=n, nx=nx, ny=ny, vdd_bumps=nb, total_current_a=round(total, 1),
                                   cg_info=int(info), rsq_eff=rsq)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--floorplan", type=Path, required=True)
    ap.add_argument("--pack", type=Path, required=True)
    ap.add_argument("--pair-w", type=float, default=0.2663, help="busy W per pair (1.2 GHz: 0.2296 x 1.16)")
    ap.add_argument("--pair-idle-w", type=float, default=0.00022)
    ap.add_argument("--duty", type=float, default=1.0)
    ap.add_argument("--hub-w-total", type=float, default=10.7, help="model hub (clock + leakage, uncalibrated)")
    ap.add_argument("--service-w", type=float, default=2.0)
    ap.add_argument("--phy-w", type=float, default=7.7)
    ap.add_argument("--serdes-w", type=float, default=0.5)
    ap.add_argument("--ucie-w", type=float, default=0.5)
    ap.add_argument("--pitch-um", type=float, default=20.0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    fp, pk = json.loads(a.floorplan.read_text()), json.loads(a.pack.read_text())
    W, H = fp["die"]["w_um"], fp["die"]["h_um"]
    blk = blocks(fp, pk, a)
    v, info = solve(W, H, blk, a.pitch_um)
    drop = VDD - v
    # per-kind worst drop under each block
    p = a.pitch_um
    kinds = {}
    for kind, x, y, w, h, watts in blk:
        sl = drop[int(y // p):int(math.ceil((y + h) / p)) + 1, int(x // p):int(math.ceil((x + w) / p)) + 1]
        k = kinds.setdefault(kind, dict(blocks=0, watts=0.0, worst_mv=0.0))
        k["blocks"] += 1
        k["watts"] += watts
        k["worst_mv"] = max(k["worst_mv"], float(sl.max()) * 1e3)
    for k in kinds.values():
        k["watts"] = round(k["watts"], 2)
        k["worst_mv"] = round(k["worst_mv"], 3)
    # closed-form check: uniform current density J over the bump array -> per-bump current I_b = J * A_b;
    # drop ~ I_b * R_bump + spreading (small); compared at the ROM field centre
    field = [b for b in blk if b[0] == "cluster"]
    jdens = sum(b[5] for b in field) / VDD / sum(b[3] * b[4] for b in field)
    ib = jdens * BUMP_PITCH ** 2 * 3
    heat = drop[::max(1, int(200 / p)), ::max(1, int(200 / p))]
    rec = dict(schema="opentallas.v41.w18_ir_mesh.v1", tag=a.tag, level="die (M8/M9 + bumps)",
               die_um=[W, H], mesh=info | dict(pitch_um=p), bump=dict(pitch_um=BUMP_PITCH, r_ohm=BUMP_R,
                                                                   vdd_fraction="1/3", basis="ASSUMED"),
               straps=dict(width_um=STRAP_W, pitch_per_net_um=STRAP_PITCH, r_um_kohm=R_UM, min_width_um=WMIN),
               power=dict(pair_w=a.pair_w, duty=a.duty, pair_idle_w=a.pair_idle_w, hub_w=a.hub_w_total,
                          service_w=a.service_w, phy_w=a.phy_w, serdes_w=a.serdes_w, ucie_w=a.ucie_w,
                          total_w=round(sum(b[5] for b in blk), 1)),
               vdd_drop_mv=dict(worst=round(float(drop.max()) * 1e3, 3), mean=round(float(drop.mean()) * 1e3, 3),
                                p99=round(float(np.percentile(drop, 99)) * 1e3, 3)),
               by_kind=kinds,
               closed_form=dict(field_current_density_a_per_um2=jdens, current_per_vdd_bump_a=round(ib, 5),
                                bump_drop_mv=round(ib * BUMP_R * 1e3, 3)),
               drop_map_200um_mv=np.round(heat * 1e3, 2).tolist(),
               inputs=dict(floorplan=str(a.floorplan), floorplan_sha256=sha(a.floorplan), pack=str(a.pack),
                           pack_sha256=sha(a.pack)),
               tool_sha256=sha(Path(__file__)),
               note="VDD only; VSS mirrors it (ground bounce of the same magnitude), so the supply loss across a "
                    "cell is twice these figures at this level")
    a.output.write_text(json.dumps(rec) + "\n")
    print(json.dumps({k: rec[k] for k in ("mesh", "power", "vdd_drop_mv", "by_kind", "closed_form")}, indent=1))


if __name__ == "__main__":
    main()
