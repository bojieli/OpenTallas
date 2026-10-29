#!/usr/bin/env python3
"""Plan -> core_infra slice converter (S81-CORE-LAT-R8; METHODOLOGY 12.2a1 / 12.7c / 12.8 a-d1).

Turns a FROZEN in-core clock plan record (core_infra_htree / l0r_r7_model / l0r_r8_model output: nodes_xy, frozen
masters, leaf_sinks, entry, plan-model TT/FF) into a core_infra slice (core_tree + clock_ndr + pg_obstructions_um +
cell_placements) that tools/die_plan/core_infra.py compiles into the kit's PRE_GLOBAL_PLACE hook.

What it decides, all from plan geometry + the kit floorplan (rows, fixed tap cells, PG shapes) -- never from a
measurement (12.8 d / d1):
  * every planned driver keeps its plan master (12.8 d1 per-driver sizing, frozen in the plan) -- the converter refuses
    a master outside the declared envelope (default BUFx8..x24, GEOM-REVIEW-7 (3)) unless --calibration is given;
  * every driver gets a distinct legal row site (GEOM-7 (4)): row by y, site-grid x, no overlap with another planned
    driver or a fixed (tap) cell, centre x not under an M5 PG strap; the nearest free site is found by a deterministic
    ring search (same input -> same sites), displacement reported per cell and as a max;
  * the trunk wire class: one NDR (default 2x width / 2x spacing) on M4/M5 for every tree net (core_infra applies it to
    all tree nets incl. leaf nets);
  * pg_obstructions_um for the trunk-PG clearance gate: M5 = the PG straps, M4 = the M2->M5 via-stack landing bands at
    every row boundary (conservative: full-width bands);
  * joint_nldm_plan load balance (leaf sink counts differ) with the plan model's TT/FF sink window as qualification
    (core_infra refuses the build outside 230-270 TT / 182.5-222.5 FF, window <= 20, slew <= 80; with --band info
    (12.3a v5.0, COORD RULING S81-CORE-LAT-R9) the band is reported as INFO and only window <= 20 + slew <= 80 gate).
Sites file = OpenROAD dump (ROW0/ROW/FIXED/MASTER/PG lines) of the kit's 2_4_floorplan_pdn.odb.
"""
import argparse, gzip, json, math, re, sys
from pathlib import Path

ENVELOPE = re.compile(r"BUFx(8|10|12|12f|16f|20|24)_ASAP7_75t_R\Z")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class ConvertError(ValueError):
    pass


def read_sites(path):
    rows, fixed, masters, pg = [], [], {}, {"M4": [], "M5": []}
    row0 = None
    for l in Path(path).read_text().splitlines():
        f = l.split()
        if not f:
            continue
        if f[0] == "ROW0":
            row0 = dict(x=float(f[1]), y=float(f[2]), site_w=float(f[4]), site_h=float(f[6]), nrows=int(f[8]),
                        nsites=int(f[10]))
        elif f[0] == "ROW":
            rows.append((float(f[1]), float(f[2]), f[3], int(f[4])))
        elif f[0] == "FIXED":
            fixed.append(tuple(map(float, f[3:7])))
        elif f[0] == "MASTER":
            masters[f[1]] = (float(f[2]), float(f[3]))
        elif f[0] == "PG" and f[2] in pg:
            pg[f[2]].append(tuple(map(float, f[3:7])))
    if row0 is None or not rows or not masters:
        raise ConvertError(f"{path}: sites file needs ROW0, ROW and MASTER lines")
    return dict(row0=row0, rows=sorted(rows, key=lambda r: r[1]), fixed=fixed, masters=masters, pg=pg)


def pg_obstructions(sites, pad_half_um=0.04):
    """M5: PG straps as dumped.  M4: the via-stack landing band at every row boundary (follow-pin rail y), full width."""
    r0 = sites["row0"]; rows = sites["rows"]
    xs = [r[0] for r in rows]; x0 = min(xs); x1 = max(r[0] + r[3] * r0["site_w"] for r in rows)
    ys = sorted({r[1] for r in rows} | {rows[-1][1] + r0["site_h"]})
    m4 = [[round(x0, 4), round(y - pad_half_um, 4), round(x1, 4), round(y + pad_half_um, 4)] for y in ys]
    return {"M5": [list(r) for r in sites["pg"]["M5"]], "M4": m4}


class SiteMap:
    """Occupancy on the row/site grid of the kit floorplan.  Integer site/row indices only."""

    def __init__(self, sites, strap_clear_um=0.024):
        self.r0 = sites["row0"]; self.rows = sites["rows"]; self.masters = sites["masters"]
        self.sw = self.r0["site_w"]; self.sh = self.r0["site_h"]; self.ns = self.r0["nsites"]
        self.occ = [dict() for _ in self.rows]          # row -> {site index: owner}
        self.straps = [(r[0] - strap_clear_um, r[2] + strap_clear_um) for r in sites["pg"]["M5"]]
        for (a, b, c, d) in sites["fixed"]:
            for k, row in enumerate(self.rows):
                if row[1] < d - 1e-6 and row[1] + self.sh > b + 1e-6:
                    for s in range(self._s(a), self._s(c - 1e-6) + 1):
                        self.occ[k][s] = "#fixed"

    def _s(self, x):
        return int(math.floor((x - self.rows[0][0]) / self.sw + 1e-6))

    def width_sites(self, master):
        if master not in self.masters:
            raise ConvertError(f"master {master} has no width in the sites file")
        return int(round(self.masters[master][0] / self.sw))

    def free(self, k, s, n):
        if s < 0 or s + n > self.ns or k < 0 or k >= len(self.rows):
            return False
        if any(q in self.occ[k] for q in range(s, s + n)):
            return False
        cx = self.rows[k][0] + (s + n / 2) * self.sw
        return not any(a <= cx <= b for a, b in self.straps)

    def place(self, name, master, x, y, max_um=20.0):
        """Nearest free legal slot to centre (x, y) by Manhattan distance (um) within growing windows; ties broken by
        (distance, |row offset|, site, row) -> deterministic for the same input."""
        n = self.width_sites(master)
        k0 = min(range(len(self.rows)), key=lambda k: abs(self.rows[k][1] + self.sh / 2 - y))
        s0 = int(round((x - n * self.sw / 2 - self.rows[0][0]) / self.sw))
        R = 0.6
        while R <= max_um + 1e-9:
            dk_max = int(R / self.sh) + 1; ds_max = int(R / self.sw) + 1; cands = []
            for k in range(k0 - dk_max, k0 + dk_max + 1):
                for s in range(s0 - ds_max, s0 + ds_max + 1):
                    if not self.free(k, s, n):
                        continue
                    cx = self.rows[0][0] + (s + n / 2) * self.sw; cy = self.rows[k][1] + self.sh / 2
                    dist = abs(cx - x) + abs(cy - y)
                    if dist <= R + 1e-9:
                        cands.append((round(dist, 6), abs(k - k0), s, k))
            if cands:
                _, _, s, k = min(cands)
                for q in range(s, s + n):
                    self.occ[k][q] = name
                ox = self.rows[0][0] + s * self.sw; oy = self.rows[k][1]
                w, h = self.masters[master]
                return dict(origin_um=[round(ox, 4), round(oy, 4)], centre_um=[round(ox + w / 2, 4), round(oy + h / 2, 4)],
                            orient=self.rows[k][2], displacement_um=round(abs(ox + w / 2 - x) + abs(oy + h / 2 - y), 4))
            R *= 2
        raise ConvertError(f"{name}: no free legal site within {max_um} um of ({x}, {y})")


def ident(plan_name, prefix):
    n = prefix + plan_name
    if not IDENT.fullmatch(n):
        raise ConvertError(f"plan node {plan_name!r} does not give a legal instance name")
    return n


def convert(rec, sites, module, clock_port="clk", outline=None, calibration=False, ndr=(2, 2), prefix="mp_ck_",
            corner_keys=("sink_min", "sink_max"), die="s81", schema=None,
            master_plan_sha256="TRIAL-no-frozen-master-plan"):
    if schema is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import master_slice as MS
        schema = MS.SCHEMA
    nodes = rec.get("nodes_xy") or []
    if not nodes or not rec.get("leaf_sinks"):
        raise ConvertError("plan record needs nodes_xy and leaf_sinks (a frozen named-sink plan)")
    if rec.get("frozen_masters") is None:
        raise ConvertError("plan record has no frozen masters (12.8 d1 sizing must be frozen in the plan)")
    roots = [n for n in nodes if n[1] is None]
    if len(roots) != 1 or roots[0][4] != "entry":
        raise ConvertError("plan needs exactly one entry root")
    # form C (CORES-EARLY-6): kind 'icg' nodes are planned clock-gate stages (RTL gate or clone_of copy, rec icg_copies),
    # emitted as core_tree.gates (domain planned), not as buffer cells; their master is the RTL gate's, outside the envelope
    icg_rows = {r["node"]: r for r in rec.get("icg_copies", [])}
    if {n[0] for n in nodes if n[4] == "icg"} != set(icg_rows):
        raise ConvertError("plan icg nodes and icg_copies rows differ")
    bad = sorted({n[3] for n in nodes if n[4] != "icg" and not ENVELOPE.fullmatch(n[3])})
    if bad and not calibration:
        raise ConvertError(f"masters outside the BUFx8..x24 gating envelope: {bad} (re-plan, or --calibration)")
    for n in nodes:
        if rec["frozen_masters"].get(n[0]) != n[3]:
            raise ConvertError(f"{n[0]}: node master {n[3]} differs from the frozen plan master")
    sm = SiteMap(sites)
    outline = outline or [sites["rows"][0][0] * 2 + sites["row0"]["nsites"] * sites["row0"]["site_w"],
                          sites["rows"][0][1] * 2 + len(sites["rows"]) * sites["row0"]["site_h"]]
    names = {n[0]: ident(n[0], prefix) for n in nodes}
    for nm_, r in icg_rows.items():
        names[nm_] = r["gate"] if r["first"] else ident(nm_[:-2] + "_icg", prefix)
    # placement order: plan order (parents before children) -> deterministic
    placements, tree_nodes, seen, gates = {}, [], set(), []
    for n in nodes:
        nm, par, xy, master, kind = n
        if par is not None and par not in seen:
            raise ConvertError(f"{nm}: parent {par} must precede it")
        seen.add(nm)
        p = sm.place(names[nm], master, float(xy[0]), float(xy[1]))
        if kind == "icg":
            r = icg_rows[nm]
            g = dict(inst=names[nm], master=master, parent=names[par], xy_um=p["centre_um"], domain="planned")
            if not r["first"]:
                g.update(clone_of=r["gate"], members=list(r["members"]))
            gates.append(g)
            tree_nodes.append(dict(name=names[nm], master=master, xy_um=p["centre_um"], parent=names[par], plan_xy_um=list(xy),
                                   displacement_um=p["displacement_um"], kind=kind))
            continue
        placements[names[nm]] = dict(master=master, **{k: p[k] for k in ("centre_um", "origin_um", "orient")})
        tree_nodes.append(dict(name=names[nm], master=master, xy_um=p["centre_um"],
                               parent=("port:" + clock_port) if par is None else names[par],
                               plan_xy_um=list(xy), displacement_um=p["displacement_um"], kind=kind))
    leaves = []
    for leaf, sinks in sorted(rec["leaf_sinks"].items()):
        if leaf not in names:
            raise ConvertError(f"leaf {leaf} is not a plan node")
        leaves.append(dict(node=names[leaf], sinks=list(sinks), load_class="register"))
    allsinks = [s for l in leaves for s in l["sinks"]]
    if len(set(allsinks)) != len(allsinks):
        raise ConvertError("a clock sink is assigned to two leaves")
    q = {}
    for corner in ("TT", "FF"):
        m = rec[corner]
        q[corner] = dict(leaf_min=m[corner_keys[0]], leaf_max=m[corner_keys[1]], leaf_window=m["window"],
                         slew_max=max(m.get("leaf_out_slew_max", 0), m.get("leaf_slew_in_max", 0)), mean=m["mean"])
    disp = [t["displacement_um"] for t in tree_nodes]
    macro_leaves = set(rec.get("macro_leaves", []))
    for leaf in leaves:
        if leaf["node"] in {names[u] for u in macro_leaves}:
            leaf["load_class"] = "macro"
    ex, ey = rec["entry"]
    gates = [g for g in gates if "clone_of" not in g] + [g for g in gates if "clone_of" in g]   # originals before copies
    if gates:
        icg_conv = dict(gates=len(gates), originals=sum(1 for g in gates if "clone_of" not in g),
                        copies=sum(1 for g in gates if "clone_of" in g))
    sl = dict(schema=schema, die=die, kind="core", type=module, module=module, instances=[],
              master_plan_sha256=master_plan_sha256, frozen=False, outline_um=[round(v, 4) for v in outline],
              latency=dict(common_clock_latency_ps={"TT": 250, "FF": 202.5}, tol_ps=20, early_taps=False),
              keepouts=[], bays=[], entry_pins=[], hard_cores=[], corridors=[], gates={},
              core_clock_port=clock_port,
              islands=[dict(name="ck_entry", rect_um=[ex - 2.16, ey - 2.16, ex + 2.16, ey + 2.16], centre_um=[ex, ey],
                            use="clock_driver", via_stack=["M9", "M5"], clock_pin=dict(layer="M5", xy_um=[ex, ey]))],
              pushdown=dict(islands=[], clock_repeaters=[], note="in-core clock tree only (core_tree); no feedthrough ports"),
              core_tree=dict(clock_port=clock_port, nodes=[{k: t[k] for k in ("name", "master", "xy_um", "parent")} for t in tree_nodes
                                                           if t["kind"] != "icg"],
                             leaves=leaves, equal_load=False, load_balance="joint_nldm_plan", trunk_layers=["M4", "M5"],
                             **({"gates": gates} if gates else {}),
                             model_qualification=dict(measured_timing_used=False, source=rec.get("name"),
                                                      model=rec.get("model", "plan model"), corners=q)),
              clock_ndr=dict(name="ot_core_ck_%dw%ds" % ndr, layers=["M4", "M5"], width_multiplier=ndr[0], spacing_multiplier=ndr[1]),
              pg_obstructions_um=pg_obstructions(sites),
              cell_placements=placements,
              plan_conversion=dict(source=rec.get("name"), calibration=bool(bad), masters_outside_envelope=bad,
                                   cells=len(tree_nodes), sinks=len(allsinks), leaves=len(leaves),
                                   displacement_um=dict(max=max(disp), mean=round(sum(disp) / len(disp), 4),
                                                        over_2um=sum(d > 2 for d in disp)),
                                   site_rule="row by y, site-grid x, no overlap with planned/fixed cells, centre x off M5 straps"))
    if gates:
        sl["plan_conversion"]["icg"] = icg_conv
    return sl


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", help="plan json (list of records or one record; .gz ok)")
    ap.add_argument("--name", help="record name when the file holds several")
    ap.add_argument("--sites", required=True); ap.add_argument("--module", required=True)
    ap.add_argument("--clock-port", default="clk"); ap.add_argument("--calibration", action="store_true")
    ap.add_argument("--die", default="s81"); ap.add_argument("--outline", default=None, help="W,H um (default: rows + symmetric margin)")
    ap.add_argument("--ndr", default="2,2", help="trunk NDR width,spacing multipliers (default 2,2); \"none\" = standard-width clock nets (no clock_ndr)")
    ap.add_argument("--band", choices=("gate", "info"), default="gate",
                    help="core latency band policy in core_infra (default gate = unchanged); info = 12.3a design target, "
                         "only window <= 20 + slew <= 80 gate (COORD RULING S81-CORE-LAT-R9)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    op = gzip.open if a.plan.endswith(".gz") else open
    d = json.load(op(a.plan, "rt"))
    recs = d if isinstance(d, list) else [d]
    rec = next((r for r in recs if a.name in (None, r.get("name"))), None)
    if rec is None:
        raise SystemExit(f"no record {a.name!r}")
    ol = [float(v) for v in a.outline.split(",")] if a.outline else None
    ndr = None if a.ndr == "none" else tuple(int(v) for v in a.ndr.split(","))
    sl = convert(rec, read_sites(a.sites), a.module, a.clock_port, outline=ol, calibration=a.calibration, die=a.die,
                 ndr=ndr or (2, 2))
    if ndr is None:
        sl.pop("clock_ndr", None)       # standard-width trunk (S81-CORE-LAT-R9 track b)
    if a.band == "info":
        sl["core_tree"]["model_qualification"]["band_policy"] = "info"   # 12.3a v5.0 (S81-CORE-LAT-R10)
    # compile through core_infra: the same refusals the kit hook applies (fail before any build)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import core_infra as CI
    import master_slice as MS
    errs = MS.validate(sl)
    if errs:
        raise SystemExit("slice schema: " + "; ".join(errs[:10]))
    plan = CI.compile_slice(sl)
    pgc = CI.trunk_pg_clearance(sl, plan)
    CI.emit_tcl(sl)
    sl["plan_conversion"]["trunk_pg_clearance"] = {k: pgc[k] for k in pgc if k != "examples"}
    Path(a.out).write_text(json.dumps(sl, indent=1) + "\n")
    pc = sl["plan_conversion"]
    print(f"CORE_PLAN_TO_INFRA {a.module}: cells={pc['cells']} leaves={pc['leaves']} sinks={pc['sinks']} "
          f"displacement max={pc['displacement_um']['max']} mean={pc['displacement_um']['mean']} "
          f"pg_clearance={pgc['verdict']} calibration={pc['calibration']}")


if __name__ == "__main__":
    main()
