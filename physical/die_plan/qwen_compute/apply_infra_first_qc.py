#!/usr/bin/env python3
"""QC INFRA-FIRST plan event (owner D-INFRA-FIRST 2026-10-26 01:37 PDT): ONE QC plan = main QC plan + batch 2 + deltas.

Input: the QC batch 1+2 plan (main 54a1aeb5 + claude/die-proto-qcb2-2325@1693a2b60 = plan 2dd204af: SRAM inventory
d4ae52687 + DEAD-FAULT 773a8e2ad + D-QC-STM-ROM-INVENTORY). This script adds, in order:
  D-QC-FE-REACH   gen_plan.declare_fe_reach_stations (fe_reach.py, inputs/fe_fwd_map.json): FIRM stations on every FE
                  u_fup crossing over 405 um; lanes landing on the bus get fixed_cycles += n. Report fe_reach_report.json.
  D-QC-COLLFTM-CTL partition_types.coll_ftm.clock.control_sinks = true (taps.control_pin_sinks, COORD 00:19).
  D-QC-IOHOLD40   coll_ftm.clock.io_hold = sender_min; coll_core / coll_ftc clock.out_hold_check_ps = 40 (senders of the
                  coll_ftm vector inputs; COORD 00:19 two-sided 40 ps budget).
  D-QC-SCROOT     new type slw_sc_v1r = clone of slw_sc_v1 (same module/outline/pins/ft/clock/reset), used only by the
                  reset root partition sl_W0_sc, so gen_phys.root_async_reset is True for exactly ONE type (owner reset
                  rule). wf_solve root must stay sl_W0_sc.
NOT in this script (recorded in the report as pending):
  D-QC-CLKMESH    driver islands: CLOCK-MESH / INFRA-FIRST apply them with tools/die_plan/apply_clkmesh_sites.py once the
                  QC regional mesh exists (plan.clock.mesh + clock_mesh_sites.json); run it AFTER this script.
  CB ID straps    cbf_q00/cbf_q11/cbn_q11 (COORD 00:59 (2), owner straps option B): no PATH-QC branch yet.
Usage: apply_infra_first_qc.py die_plan.json [--report infra_first_qc_report.json]   (in place)
Then: tools/die_plan/gen.py latency --inplace; die_io.py plan; check.py --completeness (G0C).
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import gen_plan as G          # noqa: E402
import schema as S            # noqa: E402
import reset_tree as RT       # noqa: E402
import gen_phys as GP         # noqa: E402

SC_BASE, SC_ROOT, ROOT_PART = "slw_sc_v1", "slw_sc_v1r", "sl_W0_sc"
IOHOLD_SENDERS = ("coll_core", "coll_ftc")


def iface(t):
    c = t.get("clock", {})
    return json.dumps(dict(outline=t["outline_um"], buses=t["buses"], ft=t.get("ft_slots"), reset=t.get("reset"),
                           ck_tap=c.get("tap_um"), ck_layer=c.get("layer"), ck_ins=c.get("insertion_ps")),
                      sort_keys=True)


def root_info(raw):
    P = S.Plan(copy.deepcopy(raw))
    w = RT.wf_solve(P)
    sc = sorted({p["type"] for p in P.parts.values() if p["type"].startswith("slw_sc")})
    ra = {}
    for tn in sc:
        try:
            ra[tn] = GP.root_async_reset(P, tn)
        except ValueError as e:         # base plan: the shared root type is the illegal case this delta removes
            ra[tn] = f"ERROR: {e}"
    return dict(root_part=w.get("root"), root_type=w["root_type"], est_rel_max=max(w["est_rel"].values()),
                est_rel={k: w["est_rel"].get(k) for k in ("sl_W0_sc", "sl_W2_sc", "sl_W4_sc")},
                root_async_reset=ra)


def scroot_notes(path):
    """plan_notes.json (gen_plan sidecar, read by cells.py / check.py G0C cells): give the clone its own rows."""
    path = Path(path)
    n = json.loads(path.read_text())
    cpt = n["cells_per_type"]
    if SC_ROOT not in cpt:
        cpt[SC_ROOT] = dict(copy.deepcopy(cpt[SC_BASE]), instances=1)
        cpt[SC_BASE]["instances"] -= 1
    ct = n.get("clock_taps", {}).get("types", {})
    if SC_BASE in ct and SC_ROOT not in ct:
        ct[SC_ROOT] = copy.deepcopy(ct[SC_BASE])
    path.write_text(json.dumps(n, indent=1) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--map", default=str(HERE / "inputs" / "fe_fwd_map.json"))
    ap.add_argument("--report", default=str(HERE / "infra_first_qc_report.json"))
    ap.add_argument("--fe-report", default=str(HERE / "fe_reach_report.json"))
    ap.add_argument("--notes", default=str(HERE / "plan_notes.json"))
    a = ap.parse_args(argv)
    path = Path(a.plan)
    raw = json.loads(path.read_text())
    base = copy.deepcopy(raw)
    types = raw["partition_types"]
    rep = dict(schema="opentallas.die_plan.qc_infra_first.v1", deltas={})

    # D-QC-FE-REACH
    fmap = json.loads(Path(a.map).read_text())
    fe = G.declare_fe_reach_stations(raw, fmap)
    Path(a.fe_report).write_text(json.dumps(fe, indent=1) + "\n")
    rep["deltas"]["D-QC-FE-REACH"] = dict(stations=fe["stations"], lanes=fe["lanes"], worst_hop_um=fe["worst_hop_um"],
                                          role_stations=fe["role_stations"],
                                          added_cycles=sum(r["added"] for r in fe["lane_rows"]),
                                          types=sorted(fe["types"]))

    # D-QC-COLLFTM-CTL + D-QC-IOHOLD40
    ck = types["coll_ftm"].setdefault("clock", {})
    ck["control_sinks"] = True
    ck["io_hold"] = "sender_min"
    for tn in IOHOLD_SENDERS:
        types[tn].setdefault("clock", {})["out_hold_check_ps"] = 40
    rep["deltas"]["D-QC-COLLFTM-CTL"] = dict(types=["coll_ftm"], key="clock.control_sinks=true", cycles=0)
    rep["deltas"]["D-QC-IOHOLD40"] = dict(types=["coll_ftm", *IOHOLD_SENDERS], cycles=0,
                                          keys=["coll_ftm.clock.io_hold=sender_min",
                                                *(f"{t}.clock.out_hold_check_ps=40" for t in IOHOLD_SENDERS)])

    # D-QC-SCROOT
    before = root_info(raw)
    if before["root_type"] != SC_BASE or SC_ROOT in types:
        raise SystemExit(f"D-QC-SCROOT: expected wf_solve root type {SC_BASE} and no {SC_ROOT}: {before}")
    t = copy.deepcopy(types[SC_BASE])
    t["note"] = (t.get("note", "") + f"; D-QC-SCROOT 10-26: clone of {SC_BASE} for the unique reset root partition "
                 f"{ROOT_PART} (owner reset rule: ONE async root exception)").lstrip("; ")
    types[SC_ROOT] = t
    n = 0
    for p in raw["partitions"]:
        if p["name"] == ROOT_PART:
            assert p["type"] == SC_BASE, p
            p["type"] = SC_ROOT
            n += 1
    assert n == 1, n
    after = root_info(raw)
    ra = after["root_async_reset"]
    if after["root_type"] != SC_ROOT or [k for k, v in ra.items() if v is not False] != [SC_ROOT] or ra[SC_ROOT] is not True:
        raise SystemExit(f"D-QC-SCROOT: root check failed: {after}")
    if after["est_rel_max"] != before["est_rel_max"]:
        raise SystemExit(f"D-QC-SCROOT: max reset release changed {before['est_rel_max']} -> {after['est_rel_max']}")
    rep["deltas"]["D-QC-SCROOT"] = dict(new_type=SC_ROOT, cloned_from=SC_BASE, partitions=[ROOT_PART], cycles=0,
                                        before=before, after=after)

    rep["deltas"]["D-QC-CLKMESH"] = dict(status="PENDING: apply tools/die_plan/apply_clkmesh_sites.py after the QC "
                                                "regional mesh exists (CLOCK-MESH / INFRA-FIRST step 2)")
    rep["deltas"]["D-QC-CB-STRAPS"] = dict(status="MISSING: no PATH-QC branch (cbf_q00/cbf_q11/cbn_q11, option B; "
                                                  "sidx not yet in parent_id_straps.ID_PORTS)")

    # every type no delta names keeps its interface byte-identical
    touched = set(fe["types"]) | {"coll_ftm", *IOHOLD_SENDERS, SC_ROOT}
    for tn, bt in base["partition_types"].items():
        if tn not in touched:
            assert iface(types[tn]) == iface(bt), tn
            assert types[tn] == bt or tn == SC_BASE, tn
    errs = S.validate(raw)
    if errs:
        raise SystemExit(f"schema: {len(errs)} errors: {errs[:5]}")
    path.write_text(json.dumps(raw, indent=1) + "\n")
    scroot_notes(a.notes)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("before", "after", "role_stations")}
                      for k, v in rep["deltas"].items()}, indent=1))
    print("SCROOT before", before, "\nSCROOT after", after)


if __name__ == "__main__":
    sys.exit(main())
