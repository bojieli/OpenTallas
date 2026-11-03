#!/usr/bin/env python3
"""DIE-QC-66/PLAN 11-03: coll_ucie bound-kit macro identity (one-content kit fix, no geometry/RTL/cycle change).

Class: KIT_PREFLIGHT macro_instances FAIL on coll_ucie (CERTAIN tool failure: macro_place.tcl `place_macro -macro_name
{u_io_ucie}` names no instance of the kit top).  The QC wave builds every type in bind mode: the kit top
qfd_qc_coll_ucie_part is a port-only wrapper around qfd_qc_coll_ucie_part_bound u_bound, and the PHY is
u_bound.u_io_ucie (bind kit-rtl).  Every other QC plan macro already names the bound path (u_bound.*, e.g. native59
u_bound.u_core.u_qb...); coll_ucie's content u_io_ucie (ot_qfd_ucie_x64_phy, origin 0,0) is the single outlier.
Fix = the existing kit-only physical identity form (gen_phys.content_physical_identity, DIE-KV-49 10-31):
physical_inst u_bound.u_io_ucie + physical_master ot_qfd_ucie_x64_phy on that content.  Logical bind identity
(inst u_io_ucie) is unchanged; kit_contract / fully_fixed_macros / native_clock_domains / die_io read physical_inst.
Idempotent.  usage: python3 -I delta_coll_ucie_physinst_1103.py PLAN [--out OUT]   (default: edit PLAN in place)
"""
import argparse, json

TYPE, INST, PINST, MASTER = "coll_ucie", "u_io_ucie", "u_bound.u_io_ucie", "ot_qfd_ucie_x64_phy"


def apply(plan):
    t = plan["partition_types"][TYPE]
    hits = [c for c in t.get("contents", []) if c.get("inst") == INST]
    if len(hits) != 1 or hits[0].get("module") != MASTER or not hits[0].get("lef"):
        raise SystemExit(f"{TYPE}: expected exactly one macro content {INST} ({MASTER}) with a lef, found {len(hits)}")
    c = hits[0]
    if c.get("physical_inst") not in (None, PINST) or c.get("physical_master") not in (None, MASTER):
        raise SystemExit(f"{TYPE}.{INST}: a different physical identity is already declared")
    changed = c.get("physical_inst") != PINST
    c["physical_inst"], c["physical_master"] = PINST, MASTER
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out")
    a = ap.parse_args()
    raw = open(a.plan).read()
    plan = json.loads(raw)
    changed = apply(plan)
    out = a.out or a.plan
    with open(out, "w") as f:
        json.dump(plan, f, **({"indent": 1} if raw.startswith("{\n") else {}))
        if raw.endswith("\n"):
            f.write("\n")
    print(f"{TYPE}.{INST} physical_inst={PINST} ({'changed' if changed else 'already set'}) -> {out}")


if __name__ == "__main__":
    main()
