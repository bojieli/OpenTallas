#!/usr/bin/env python3
"""KV-D23-HUBWI 11-18 (OPT-IN row writer; nothing calls it): kv3_hub_Wi clustered host rows.

kv3_hub_Wi plans 21 hard cores at u_bound.u_host.host__qkd_hr_* (14 qkd_hr_* masters), but the as-built host
qkd_host_root_admission_obsx_bo1_c45 has no such instances: the cluster logic stays flat (1.155 M cells, KIT_PREFLIGHT
PLAN-SRC-MACRO x21).  The clustered host is the KV-HOST-WI form-S parent (physical/die_plan/qwen_kvsys/bind/kv_host_wi/
parent.sv: same module name, 21 qkd_hr_* leaf instances, flat glue) with wrappers_s/<m>/<m>.sv as the port-bind source of
each master.  This writer applies the smallest change, fail closed:

  plan     partition_types.kv3_hub_Wi.hard_cores[qkd_hr_*]: lef/lib = <views>/<module>/<module>.lef / _tt.lib
  asbuilt  files + prefer: the kv45 host file -> parent.sv; portbind_files + portbind_prefer += the 14 wrappers

Checked before anything is written: every row has physical_inst u_bound.u_host.<inst> and physical_master = module and no
view yet; parent.sv instantiates <module> <inst> exactly once per row; every wrapper and view file exists; the view LEF
SIZE equals the plan outline; the LEF signal pin set equals the plan pins_file pin set (bit exact, by name).  No cycle,
outline, origin or pin changes; a hard core is never reshaped.

usage: kv_hubwi_host_rows.py --tree TREE --plan PLAN --asbuilt ASBUILT --views REL_DIR --out-plan P --out-asbuilt A
                             [--report R.json] [--type kv3_hub_Wi]
"""
import argparse
import json
import re
import sys
from pathlib import Path

HOST_OLD = "physical/die_plan/qwen_kvsys/bind/kv45/qkd_host_root_admission_obsx_bo1_c45.sv"
HOST_DIR = "physical/die_plan/qwen_kvsys/bind/kv_host_wi"
NOTE = ("KV-D23-HUBWI 11-18: lef/lib = view of the signed qkd_hr master; bound u_host = clustered form-S parent "
        "(bind/kv_host_wi/parent.sv)")


class RowError(ValueError):
    pass


def lef_pins(path):
    """-> ({pin bit name}, (w, h)) of a macro LEF; scalar pins are named <pin>[0] as in the plan pins files."""
    pins, size = set(), None
    for line in Path(path).read_text().splitlines():
        s = line.split()
        if len(s) >= 2 and s[0] == "PIN" and s[1] not in ("VDD", "VSS"):
            pins.add(s[1] if re.search(r"\[\d+\]$", s[1]) else s[1] + "[0]")
        elif len(s) >= 4 and s[0] == "SIZE":
            size = (float(s[1]), float(s[3]))
    return pins, size


def apply(plan, asbuilt, tree, views, plan_dir, tname="kv3_hub_Wi"):
    """-> (plan, asbuilt, report); raises RowError and changes nothing unless every check passes."""
    tree, plan_dir = Path(tree), Path(plan_dir)
    t = plan["partition_types"][tname]
    rows = [h for h in t.get("hard_cores", []) if str(h.get("module", "")).startswith("qkd_hr_")]
    if not rows:
        raise RowError(f"{tname}: no qkd_hr_* hard_cores rows")
    parent = tree / HOST_DIR / "parent.sv"
    if not parent.is_file():
        raise RowError(f"clustered host missing: {parent}")
    ptxt = parent.read_text()
    errs, mods = [], []
    for h in rows:
        m, inst = h["module"], h["inst"]
        if h.get("physical_inst") != "u_bound.u_host." + inst or h.get("physical_master") != m:
            errs.append(f"{inst}: physical_inst/physical_master is not u_bound.u_host.{inst} / {m}")
        if h.get("lef") or h.get("lib"):
            errs.append(f"{inst}: row already binds a view")
        n = len(re.findall(r"^\s*" + re.escape(m) + r"\s+" + re.escape(inst) + r"\s*\(", ptxt, re.M))
        if n != 1:
            errs.append(f"{inst}: parent.sv has {n} instances `{m} {inst}`, expected 1")
        if m not in mods:
            mods.append(m)
    wrappers = [f"{HOST_DIR}/wrappers_s/{m}/{m}.sv" for m in mods]
    for w in wrappers:
        if not (tree / w).is_file():
            errs.append(f"wrapper missing: {w}")
    by_mod = {}
    for h in rows:
        by_mod.setdefault(h["module"], []).append(h)
    for m in mods:
        lef, lib = f"{views}/{m}/{m}.lef", f"{views}/{m}/{m}_tt.lib"
        if not (tree / lef).is_file() or not (tree / lib).is_file():
            errs.append(f"{m}: view missing ({lef} / {lib})")
            continue
        pins, size = lef_pins(tree / lef)
        for h in by_mod[m]:
            if size is None or [size[0], size[1]] != [float(x) for x in h["outline_um"]]:
                errs.append(f"{h['inst']}: LEF SIZE {size} != plan outline {h['outline_um']}")
            pf = plan_dir / h["pins_file"]
            if not pf.is_file():
                errs.append(f"{h['inst']}: pins_file missing {h['pins_file']}")
                continue
            want = {p["name"] for p in json.loads(pf.read_text())["pins"]}
            if want != pins:
                errs.append(f"{h['inst']}: LEF pins != plan pins_file ({len(pins - want)} only in LEF, "
                            f"{len(want - pins)} only in plan; e.g. {sorted(pins ^ want)[:3]})")
    for key in ("files", "prefer"):
        if list(asbuilt.get(key) or []).count(HOST_OLD) != 1:
            errs.append(f"asbuilt.{key}: {HOST_OLD} not listed exactly once")
    if errs:
        raise RowError("; ".join(errs))
    new = f"{HOST_DIR}/parent.sv"
    for h in rows:
        m = h["module"]
        h["lef"], h["lib"] = f"{views}/{m}/{m}.lef", f"{views}/{m}/{m}_tt.lib"
        h["note"] = (h.get("note", "") + " | " + NOTE) if h.get("note") else NOTE
    for key in ("files", "prefer"):
        asbuilt[key] = [new if f == HOST_OLD else f for f in asbuilt[key]]
    for key in ("portbind_files", "portbind_prefer"):
        asbuilt[key] = list(asbuilt.get(key) or []) + [w for w in wrappers if w not in (asbuilt.get(key) or [])]
    asbuilt["kv_host_wi_note"] = ("KV-D23-HUBWI 11-18: kv3_hub_Wi u_host = KV-HOST-WI form-S clustered parent (21 qkd_hr_* "
                                  "leaf instances, flat glue); wrappers_s = port-bind sources of the qkd_hr masters")
    report = dict(schema="kv_hubwi_host_rows.v1", type=tname, rows=[h["inst"] for h in rows], modules=mods,
                  host_old=HOST_OLD, host_new=new, portbind_added=wrappers, views=views, cycles_changed=0)
    return plan, asbuilt, report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--asbuilt", required=True)
    ap.add_argument("--views", required=True, help="view dir relative to the tree: <views>/<module>/<module>.lef, _tt.lib")
    ap.add_argument("--out-plan", required=True)
    ap.add_argument("--out-asbuilt", required=True)
    ap.add_argument("--report")
    ap.add_argument("--type", default="kv3_hub_Wi")
    a = ap.parse_args(argv)
    plan, asbuilt = json.loads(Path(a.plan).read_text()), json.loads(Path(a.asbuilt).read_text())
    try:
        plan, asbuilt, rep = apply(plan, asbuilt, a.tree, a.views.rstrip("/"), Path(a.plan).resolve().parent, a.type)
    except RowError as exc:
        print(f"KV_HUBWI_HOST_ROWS FAIL {exc}", file=sys.stderr)
        return 2
    Path(a.out_plan).write_text(json.dumps(plan, indent=1))
    Path(a.out_asbuilt).write_text(json.dumps(asbuilt, indent=1))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"KV_HUBWI_HOST_ROWS PASS rows {len(rep['rows'])} modules {len(rep['modules'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
