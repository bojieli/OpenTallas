#!/usr/bin/env python3
"""QC-EVENT-S25 SHAPE_CHECK: every hard core of the 4 newly bound modules in plan_qc99_s25 vs its bound signed LEF:
outline (LEF SIZE vs plan outline_um), pin names, layers, and every plan pin centre (pins_file) inside a LEF PIN rect
of the same layer (tol 0.02 um).  crh_rp1/vmr: the LEF pins beyond the canonical table must be exactly the 4 declared
physical_ft pins (proof ft_ports.json).  Also runs core_ft_physical.load (proof closure, isolation, canonical pins).
usage: shape_check.py REPO PLAN_DIR PLAN.json OUT.json"""
import json, re, sys
from pathlib import Path
R, PD, PL, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
sys.path.insert(0, str(R / "tools/die_plan"))
MODS = ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c", "qfd_dv_s8_crh_rp1", "qfd_dv_s8x_vmr")
TOL = 0.02


def lef_pins(text, mod):
    m = re.search(r"MACRO\s+" + re.escape(mod) + r"\b(.*?)END\s+" + re.escape(mod) + r"\b", text, re.S)
    body = m.group(1)
    size = [float(v) for v in re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body).groups()]
    pins = {}
    for name, pb in re.findall(r"^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$", body, re.M | re.S):
        if re.search(r"USE\s+(POWER|GROUND)", pb):
            continue
        rects, layer = [], None
        for ln in pb.splitlines():
            a = re.match(r"\s*LAYER\s+(\S+)\s*;", ln)
            if a:
                layer = a.group(1); continue
            b = re.match(r"\s*RECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;", ln)
            if b:
                rects.append((layer,) + tuple(float(v) for v in b.groups()))
        pins[name] = rects
    return size, pins


def plan_pins(doc):
    if isinstance(doc, list):
        return {(p.get("name") or (f"{p['bus']}[{p['bit']}]" if p.get("bit") is not None else p["bus"])): (p["layer"], p["x"], p["y"]) for p in doc}
    return {p["name"]: (p["layer"], p["x"], p["y"]) for p in doc["pins"]}


P = json.load(open(PL))
res, seen = {}, {}
for tn, t in sorted(P["partition_types"].items()):
    for h in t.get("hard_cores") or []:
        m = h["module"]
        if m not in MODS:
            continue
        key = (m, h["lef"], h["pins_file"])
        if key in seen:
            seen[key]["n_entries"] += 1; seen[key]["types"].add(tn); continue
        size, lp = lef_pins((R / h["lef"]).read_text(), m)
        pp = plan_pins(json.loads((PD / h["pins_file"]).read_text()))
        extra = sorted(set(lp) - set(pp)); missing = sorted(set(pp) - set(lp))
        bad_layer, outside, maxdev = [], [], 0.0
        for n, (L, x, y) in pp.items():
            rs = [r for r in lp.get(n, []) if r[0] == L]
            if n in lp and not rs:
                bad_layer.append(n); continue
            if not rs:
                continue
            ok = any(r[1] - TOL <= x <= r[3] + TOL and r[2] - TOL <= y <= r[4] + TOL for r in rs)
            dev = min(max(r[1] - x, 0, x - r[3]) + max(r[2] - y, 0, y - r[4]) for r in rs)
            maxdev = max(maxdev, dev)
            if not ok:
                outside.append(n)
        row = dict(module=m, lef=h["lef"], pins_file=h["pins_file"], n_entries=1, types={tn},
                   lef_size=size, plan_outline=h["outline_um"],
                   outline_equal=all(abs(a - b) < 1e-3 for a, b in zip(size, h["outline_um"])),
                   plan_pins=len(pp), lef_pins=len(lp), missing_in_lef=missing[:10], extra_in_lef=extra,
                   layer_mismatch=bad_layer[:10], outside_lef_rect=outside[:10], max_dev_um=round(maxdev, 4),
                   ck=dict(plan=pp.get("ck"), lef=lp.get("ck")))
        if h.get("physical_ft"):
            import core_ft_physical as CF
            pr = json.loads((R / h["physical_ft"]["proof"]).read_text())
            decl = json.loads((R / h["physical_ft"]["proof"]).parent.joinpath(pr["files"]["declaration"]["path"]).read_text())
            row["ft_declared"] = sorted(p["name"] for p in decl["ports"])
            row["extra_equals_declared_ft"] = row["ft_declared"] == extra
            lef, tt = R / h["lef"], R / h["lib"]
            ff = tt.with_name(tt.name.replace("_tt.lib", "_ff.lib"))
            try:
                v = CF.load(h, m, lef, tt, ff, root=R, plan_dir=PD)
                row["core_ft_physical_load"] = dict(ok=True, isolation=v["isolation"], ports=v["ports"])
            except Exception as e:  # noqa: BLE001
                row["core_ft_physical_load"] = dict(ok=False, error=str(e))
            row["equal"] = (row["outline_equal"] and not missing and row["extra_equals_declared_ft"] and not bad_layer
                            and not outside and row["core_ft_physical_load"]["ok"])
        else:
            row["equal"] = row["outline_equal"] and not missing and not extra and not bad_layer and not outside
        seen[key] = row
for row in seen.values():
    row["types"] = sorted(row["types"])
out = dict(schema="opentallas.qc_event_s25.shape_check.v1", plan=PL, tol_um=TOL, rows=list(seen.values()),
           all_equal=all(r["equal"] for r in seen.values()))
Path(OUT).write_text(json.dumps(out, indent=1, default=list) + "\n")
for r in seen.values():
    print(r["module"], r["n_entries"], "outline", r["outline_equal"], "pins", r["plan_pins"], "/", r["lef_pins"], "extra", r["extra_in_lef"],
          "missing", len(r["missing_in_lef"]), "layer", len(r["layer_mismatch"]), "outside", len(r["outside_lef_rect"]),
          "maxdev", r["max_dev_um"], "ft_load", (r.get("core_ft_physical_load") or {}).get("ok"), "EQUAL", r["equal"])
print("ALL_EQUAL", out["all_equal"])
