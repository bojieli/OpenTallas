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
  CB ID straps    all nine CB types: existing tile_id/sidx parameter bits become parent-tied ID inputs (zero cycles).
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
import cb_id_straps as CBIDS
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
    if "sle_fw_v1_e2" not in cpt:
        cpt["sle_fw_v1_e2"] = dict(copy.deepcopy(cpt["sle_fw_v1"]), instances=1)
        cpt["sle_fw_v1"]["instances"] -= 1
    if "sle_fw_v1" in ct and "sle_fw_v1_e2" not in ct:
        ct["sle_fw_v1_e2"] = copy.deepcopy(ct["sle_fw_v1"])
    path.write_text(json.dumps(n, indent=1) + "\n")


def vmr_core_latency(raw):
    """Measured s6kc insertion; D-INFRA-FIRST compensates at the die stub."""
    rows = []
    for tn in ("slw_su_c", "sle_su_c"):
        for tap in raw["partition_types"][tn]["clock"]["taps"]:
            if tap.get("name") not in {f"u_suvm_u_vm8q_u_v{v}.ck" for v in "abc"}:
                continue
            before = dict(TT=tap["insertion_ps"], FF=tap.get("insertion_ff_ps"))
            tap.update(insertion_ps=395.7, insertion_ff_ps=302.7,
                       budget_owner="vmr_s6kc measured routed native mean TT395.7/FF302.7; die compensates residual (D-INFRA-FIRST), no tile retap")
            rows.append(dict(type=tn, tap=tap["name"], before=before, after=dict(TT=395.7, FF=302.7)))
    if len(rows) != 6:
        raise ValueError(f"expected six VMR core taps, found {len(rows)}")
    return dict(taps=rows, cycles=0, note="absolute measured insertion, not an offset to the obsolete vmr_s6h budget")


def fw_source_split(raw):
    """The E2 FW has a different native ch_dn_i connection, so it is a real type."""
    old, new, part = "sle_fw_v1", "sle_fw_v1_e2", "sl_E2_fw"
    types = raw["partition_types"]
    if new in types:
        raise ValueError(f"{new} already exists; do not compose the source split twice")
    t = copy.deepcopy(types[old]);t["module"] += "_e2"
    t["note"] = t.get("note", "") + "; native E2 ch_dn_i connection differs from E0/E4; exact interface clone,0 cycles"
    types[new] = t
    ps = [p for p in raw["partitions"] if p["name"] == part]
    if len(ps) != 1 or ps[0]["type"] != old:
        raise ValueError(f"expected exactly one {part} with source type {old}")
    ps[0]["type"] = new
    return dict(base_type=old,new_type=new,part=part,cycles=0,
                reason="strict native source signature ch_dn_i differs; no generic type waiver")


def su_exact_product(raw):
    """Install the measured source-facing pin overlay; grouping is a final bind step."""
    product = ROOT / "results/qc_su_lane_cut_1026/params3"
    overlay = json.loads((product / "plan_overlay.json").read_text())
    rows = []
    for tn, item in overlay.items():
        typ = raw["partition_types"][tn]
        typ["hard_cores"] = copy.deepcopy(item["hard_cores"])
        cores = {c["inst"]: c for c in typ["hard_cores"]}
        for tap in typ["clock"].get("taps", []):
            if tap.get("kind") != "core":
                continue
            inst = tap["name"].split(".")[0]
            core = cores[inst]
            pins = json.loads((HERE / core["pins_file"]).read_text())["pins"]
            pin = next(p for p in pins if p["name"] == "clk")
            if core.get("orient", "R0") != "R0":
                raise ValueError(f"{tn}/{inst}: explicit orientation transform required")
            tap["name"] = inst + ".clk"
            tap["xy"] = [round(core["origin_um"][0] + pin["x"], 4), round(core["origin_um"][1] + pin["y"], 4)]
            rows.append(dict(type=tn, inst=inst, clock_pin="clk", xy=tap["xy"]))
    if len(rows) != 16:
        raise ValueError(f"expected16 actual SU core clock pins, found{len(rows)}")
    return dict(cores=16, clock_pins=rows, cycles=0,
                source="results/qc_su_lane_cut_1026/params3/source_manifest.json",
                final_bind_step="regenerate grouped frames from final qualified bind; add16 core RTL files to source closure")


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
    rep["deltas"]["D-QC-CB-STRAPS"] = CBIDS.apply(raw)
    rep["deltas"]["D-QC-VMR-LATENCY"] = vmr_core_latency(raw)
    rep["deltas"]["D-QC-FW-NATIVE-E2"] = fw_source_split(raw)
    rep["deltas"]["D-QC-SU-EXACT-CUT"] = su_exact_product(raw)

    # every type no delta names keeps its interface byte-identical
    touched = set(fe["types"]) | set(rep["deltas"]["D-QC-CB-STRAPS"]["types"]) | {"coll_ftm", *IOHOLD_SENDERS, SC_ROOT, "slw_su_c", "sle_su_c", "sle_fw_v1_e2", "slw_su_l0", "slw_su_l1", "sle_su_l0", "sle_su_l1"}
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
