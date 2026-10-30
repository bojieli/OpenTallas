#!/usr/bin/env python3
"""HBM core_macros.json repair (DIE-HBM-26, HBM-053/HBM-054; die-local plan tool, no new check).

    python3 physical/die_plan/hbm/core_macros_fix.py PLANDIR --out OUTDIR --lef-dir DIR [--evidence E.json]
            [--static S.json]

(1) MASTER FIELD (HBM-053).  Every core_macros macro row must name a real LEF macro master.  Since d21h three cores
    (lane_exp0, lane_exp__canon_7cd691, programme_pslice_c5; 112 rows) carry master="width" -- a field-name leak from
    the writer that built them -- and three rows carry no master at all; any consumer (cm2mp, kit_preflight) KeyErrors.
    A row whose master is not a LEF macro is resolved FAIL-CLOSED: the LEF masters whose SIZE equals the row rect
    (orientation-aware) intersected with the core's evidence masters (E.json {core: [master, ...]}: the RTL
    instantiation, the kit macro placement or the recipe list).  Exactly one candidate -> fixed; else SystemExit.
    Size alone is never enough: 94.824x41.064 is both ot_sram_1r1w_128x256_m1_r2c2 and ..._r0c0_pc.
    Rows that name a hard sub-core (not a LEF macro, e.g. hnx_lane_x) are left alone when --keep lists them.
(2) STATIC PLACEMENT (HBM-054).  S.json {core: {"basis": str, "macros": [{name, master, origin_um, orient}]}} turns a
    status UNKNOWN core into KNOWN with those sites.  Each site is validated against the plan outline (4.32-um core
    inset), no overlap, the LEF size, and the same 10.8-um macro channel arithmetic kit_contract.macro_channels uses
    (every macro column has >= 10.8 um on both sides incl. the core edge; a stacked column has an interior horizontal
    channel >= 10.8 um).  The kit generator snaps M4 pins itself; sites here are already on y = 0.012 mod 0.048.
Writes OUTDIR/core_macros.json + OUTDIR/core_macros_fix_report.json; every other PLANDIR file is hard-linked.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

CH = 10.8          # MIN_CHANNEL_UM (kit_contract.py)
INSET = 4.32       # CORE_AREA inset of every HBM core kit
EPS = 1e-6
SWAP = {"R90", "R270", "MXR90", "MYR90"}


def lef_sizes(lef_dir):
    out = {}
    for f in sorted(glob.glob(os.path.join(lef_dir, "*", "*.lef")) + glob.glob(os.path.join(lef_dir, "*.lef"))):
        for m in re.finditer(r"^MACRO\s+(\S+).*?^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", Path(f).read_text(errors="replace"),
                             re.M | re.S):
            out.setdefault(m.group(1), (float(m.group(2)), float(m.group(3))))
    return out


def rect_wh(row):
    x0, y0, x1, y1 = row["rect_um"]
    w, h = x1 - x0, y1 - y0
    return (h, w) if row.get("orient") in SWAP else (w, h)


def size_match(wh, size, tol=0.002):
    return abs(wh[0] - size[0]) <= tol and abs(wh[1] - size[1]) <= tol


def resolve_master(core, row, sizes, evidence):
    wh = rect_wh(row)
    cands = sorted(m for m, s in sizes.items() if size_match(wh, s))
    ev = evidence.get(core)
    if not ev:
        raise SystemExit(f"{core}: {row.get('name')} master={row.get('master')!r}, size {wh} matches {cands}; no "
                         f"evidence masters for this core (pass --evidence)")
    pick = [m for m in cands if m in ev]
    if len(pick) != 1:
        raise SystemExit(f"{core}: {row.get('name')} master={row.get('master')!r}: size candidates {cands} x evidence "
                         f"{ev} -> {pick} (need exactly one)")
    return pick[0]


def channel_errors(rows, outline):
    """kit_contract.macro_channels arithmetic on plan rows (core frame)."""
    W, H = outline
    core = (INSET, INSET, W - INSET, H - INSET)
    boxes = sorted((r["rect_um"] for r in rows), key=lambda b: b[0])
    err = []
    for b in boxes:
        if b[0] < core[0] - EPS or b[1] < core[1] - EPS or b[2] > core[2] + EPS or b[3] > core[3] + EPS:
            err.append(f"rect {b} outside core area {core}")
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS:
                err.append(f"overlap {a} {b}")
    cols = []
    for b in boxes:
        if cols and b[0] < max(x[2] for x in cols[-1]) - EPS:
            cols[-1].append(b)
        else:
            cols.append([b])
    edges = [core[0]] + [v for c in cols for v in (min(b[0] for b in c), max(b[2] for b in c))] + [core[2]]
    for i, c in enumerate(cols):
        lo, hi = min(b[0] for b in c), max(b[2] for b in c)
        for side, g in (("W", lo - edges[2 * i]), ("E", edges[2 * i + 3] - hi)):
            if g < CH - EPS:
                err.append(f"column {i} x[{lo:g},{hi:g}] {side} channel {g:.3f} < {CH}")
        st = sorted(c, key=lambda b: b[1])
        if len(st) > 1 and max(st[k + 1][1] - st[k][3] for k in range(len(st) - 1)) < CH - EPS:
            err.append(f"column {i}: {len(st)} stacked macros, no interior channel >= {CH}")
    return err, len(cols)


def fix(cm, sizes, evidence, static, keep):
    rep = dict(master_fixed={}, static={})
    for core, ent in cm["cores"].items():
        for row in ent.get("macros", []) or []:
            m = row.get("master")
            if m in sizes or m in keep:
                continue
            new = resolve_master(core, row, sizes, evidence)
            rep["master_fixed"].setdefault(core, {}).setdefault(f"{m}->{new}", 0)
            rep["master_fixed"][core][f"{m}->{new}"] += 1
            row["master"] = new
    for core, spec in static.items():
        ent = cm["cores"].get(core)
        if ent is None:
            raise SystemExit(f"{core}: not in core_macros")
        if ent.get("status") == "KNOWN" and ent.get("macros"):
            raise SystemExit(f"{core}: already KNOWN with {len(ent['macros'])} macros; refusing to overwrite")
        rows = []
        for s in spec["macros"]:
            if s["master"] not in sizes:
                raise SystemExit(f"{core}: {s['name']} master {s['master']} has no LEF")
            w, h = sizes[s["master"]]
            if s.get("orient", "R0") in SWAP:
                w, h = h, w
            x, y = s["origin_um"]
            rows.append(dict(name=s["name"], master=s["master"], orient=s.get("orient", "R0"),
                             rect_um=[round(x, 4), round(y, 4), round(x + w, 4), round(y + h, 4)]))
        err, ncols = channel_errors(rows, ent["outline_um"])
        if err:
            raise SystemExit(f"{core}: {err[:5]}")
        names = [r["name"] for r in rows]
        if len(set(names)) != len(names):
            raise SystemExit(f"{core}: duplicate macro names")
        old = dict(status=ent.get("status"), why=ent.get("why"))
        outline = ent["outline_um"]
        ent.clear()
        ent.update(status="KNOWN", outline_um=outline, basis=spec["basis"], macros=rows, channel_rule_um=CH,
                   previous=old)
        rep["static"][core] = dict(macros=len(rows), columns=ncols, masters=sorted({r["master"] for r in rows}))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lef-dir", required=True, action="append", help="repeatable; first dir wins per master")
    ap.add_argument("--evidence")
    ap.add_argument("--static")
    ap.add_argument("--keep", default="hnx_lane_x", help="comma list of non-LEF hard sub-core masters left as is")
    a = ap.parse_args()
    plan, out = Path(a.plan), Path(a.out)
    raw = (plan / "core_macros.json").read_bytes()
    cm = json.loads(raw)
    sizes = {}
    for d in a.lef_dir:
        for k, v in lef_sizes(d).items():
            sizes.setdefault(k, v)
    evidence = json.loads(Path(a.evidence).read_text()) if a.evidence else {}
    static = json.loads(Path(a.static).read_text()) if a.static else {}
    # spec outline must equal the plan outline
    for core, spec in static.items():
        if "outline_um" in spec and cm["cores"].get(core, {}).get("outline_um") != spec["outline_um"]:
            raise SystemExit(f"{core}: spec outline {spec['outline_um']} != plan {cm['cores'][core].get('outline_um')}")
    rep = fix(cm, sizes, evidence, static, set(filter(None, a.keep.split(","))))
    bad = [(c, r.get("name"), r.get("master")) for c, e in cm["cores"].items() for r in e.get("macros", []) or []
           if r.get("master") not in sizes and r.get("master") not in a.keep.split(",")]
    if bad:
        raise SystemExit(f"unresolved masters remain: {bad[:5]}")
    cm["note"] = cm.get("note", "") + " | DIE-HBM-26 core_macros_fix (HBM-053 master field, HBM-054 static sites)"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for f in os.listdir(plan):
        if f in ("core_macros.json", "core_macros_fix_report.json") or f.startswith("g0"):
            continue
        s = plan / f
        shutil.copytree(s, out / f, copy_function=os.link) if s.is_dir() else os.link(s, out / f)
    txt = json.dumps(cm, indent=1)
    (out / "core_macros.json").write_text(txt)
    rep.update(schema="opentallas.hbm.core_macros_fix.v1", source_sha256=hashlib.sha256(raw).hexdigest(),
               core_macros_sha256=hashlib.sha256(txt.encode()).hexdigest(),
               die_plan_sha256=hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest())
    (out / "core_macros_fix_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
