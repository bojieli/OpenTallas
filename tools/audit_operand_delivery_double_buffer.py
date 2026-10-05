#!/usr/bin/env python3
"""What does closing the operand-delivery gap buy, and what does it cost in area?

THE GAP, AS results/derived/sustained_array_iso_area_audit.json LEFT IT
----------------------------------------------------------------------
That audit puts 512 compute units plus their distributor at 2.059x the A100's
standard-cell-logic density on occupancy and 1.952x on MAC-active work -- at
REFILL SKEW 0, every unit fed every cycle. At SKEW 2, one unit in sixteen at a
50 % refill duty, the same array at the same width and the same descriptor
coarseness falls to 1.124x and 1.006x. Its own words: "the band between those two
numbers is the size of the operand-delivery problem, and it is not closed by
anything in the control path." Its verdict names OPERAND DELIVERY, and an earlier
energy attribution puts 75 % of a compute unit's power and 59.6 % of its occupied
area in the same block.

WHAT WAS CHANGED, AND WHY THOSE TWO THINGS
------------------------------------------
``rtl/proto/ot_compute_unit.sv`` gained two parameters, and the old behaviour is
one of the settings so the baseline stays reproducible from the same file:

  REFILL_DECOUPLED  0 is the LOCKSTEP handshake the baseline was measured on: a
                    column could only be consumed on a cycle when refill_valid
                    happened to be high, refill_ready was only asserted while
                    walking, and every pass of a descriptor re-ran the handshake
                    for weights already sitting in the SRAM. 1 is a FILL FRONTIER:
                    the port delivers a numbered column into a bank, residency is
                    tracked, delivery may run ahead of the walk and through drain
                    and idle, and it is charged ONCE PER TILE. ``wgt_reload``, new
                    on the unit and derived by ot_dispatch_tree from the last-pass
                    flag already in its payload, is what says a tile is new.
  WGT_BANKS         1 keeps one weight bank, so fetch and compute SERIALISE.
                    2 is the double buffer: the next descriptor's tile lands in
                    the other bank while this one is walked.

THE THREE THINGS THIS COMPOSES, EACH FROM A RECORD
--------------------------------------------------
  stall cycles   results/rtl/refill_stall_campaign.json -- the unit-level table,
                 with the published 46/78/142/266 reproduced digit for digit at
                 the baseline setting as a gate.
  utilisation    the dispatch-tree campaigns, cycle-accurate on real units at
                 width, with every configuration's results bit-identical to
                 testdata/rtl/a3_mac_tile/expected.hex or its utilisation refused.
  area and f     post-route records on ot_compute_unit at each parameter setting,
                 read back with their own recorded parameters so a record cannot
                 be mislabelled here.

THE RATIO IS RECOMPUTED PER VARIANT, WHICH IS THE POINT
-------------------------------------------------------
A second weight bank is one more macro pair. So the sustained figure is NOT the
baseline ratio times a better utilisation: the denominator moved too, and this
tool recomputes peak density from each variant's OWN routed area and OWN routed
frequency before multiplying by that variant's OWN measured utilisation. A
version of this audit that reused the baseline's 2.077x peak would be claiming a
free second SRAM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TECH_INPUTS = ROOT / "configs/hardware/technology_inputs.json"
TECHNOLOGY = ROOT / "configs/hardware/technology.json"

LANES_PER_UNIT = 16
FLOPS_PER_MAC = 2
HEADROOM_SUSPECT = 0.35

#: the distributor charged into the array's area, per width. Same records
#: tools/audit_sustained_array_iso_area.py charges, so the denominators agree.
DISTRIBUTORS = {
    16: "results/physical_abi3/asap7/cluster_dispatcher/pnr.json",
    512: "results/physical_abi3/asap7/dispatch_tree/pnr_g16_l32_0p8.json",
    1088: "results/physical_abi3/asap7/dispatch_tree/pnr_g16_l68_0p8.json",
}

SKEW_MEANING = {
    0: "every unit always fed: refill_valid asserted every cycle at every unit",
    1: "every unit slowed a little and by a different amount",
    2: "STRAGGLERS -- one unit in sixteen at a 50% refill duty",
    3: "one unit in sixteen at a 25% refill duty",
    4: "EVERY unit at a 50% refill duty",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "branch": run("rev-parse", "--abbrev-ref", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def physical(path: Path) -> dict[str, Any]:
    body = json.loads(path.read_text())
    d = body["design"]
    metrics = (body.get("place_and_route") or {}).get("metrics") or {}
    period = d.get("clock_period_ns")
    wns = d.get("setup_wns_ns")
    acc = body.get("acceptance") or {}
    post = [c for c in acc.get("checks", [])
            if c.get("scope") == "post-route, extracted parasitics"]
    cell = d.get("area_um2")
    macro = metrics.get("macro_area_um2") or 0.0
    return {
        "record": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "record_sha256": sha(path),
        "block": d.get("block"),
        #: read back from the record, so a variant cannot be mislabelled here.
        "parameters": d.get("parameters") or {},
        "target_clock_period_ns": period,
        "post_route_fmax_hz": d.get("fmax_hz"),
        "standard_cell_count": d.get("cells"),
        "standard_cell_area_um2": cell,
        "macro_area_um2": macro,
        "macro_count": metrics.get("macro_count"),
        "occupied_area_um2": (cell + macro) if cell is not None else None,
        "core_area_um2": d.get("core_area_um2"),
        "utilization_fraction": d.get("utilization_fraction"),
        "power_total_w_default_activity": metrics.get("power_total_w"),
        "setup_wns_ns": wns,
        "target_headroom": (wns / period) if (period and wns is not None) else None,
        "target_headroom_suspect": (period and wns is not None
                                    and wns / period > HEADROOM_SUSPECT),
        "signal_integrity_violations": d.get("signal_integrity_violations"),
        "closed": d.get("closed"),
        "acceptance_status": acc.get("status"),
        "post_route_check_met": (post[0].get("met") if post else None),
        "stages_requested": body.get("stages_requested"),
        "stages_completed": body.get("stages_completed"),
        #: the three-way class results/derived/sustained_array_iso_area_audit.json
        #: uses.  A block can meet setup and hold with zero violating paths, zero
        #: DRC and zero antenna violations and STILL not be closed, because this
        #: project's `closed` additionally requires a routed netlist with no
        #: max-slew, max-cap or max-fanout violations.  That distinction is the
        #: difference between the two decoupled variants below and it is not
        #: allowed to disappear into a frequency number.
        "evidence_class": ("ROUTED AND CLOSED" if d.get("closed")
                           else ("ROUTED, POST-ROUTE CLEAN ON TIMING AND DRC, "
                                 "NOT CLOSED"
                                 if (post and post[0].get("met"))
                                 else "ROUTED, NOT CLOSED")),
    }


def comparator() -> dict[str, Any]:
    facts = json.loads(TECH_INPUTS.read_text())["source_facts"]["a100_sxm_80gb"]
    tech = json.loads(TECHNOLOGY.read_text())
    ops = float(facts["bf16_dense_ops_s"])
    die_entry = tech["reference_parts"]["a100_sxm_80gb"]["die_area_mm2"]
    die = float(die_entry["value"])
    #: the SAME assumed logic fraction tools/audit_sustained_array_iso_area.py
    #: uses, read from the same place, so the two audits share a denominator.
    frac_entry = tech["power"]["gpu_logic_area_fraction"]
    frac = float(frac_entry["value"])
    return {
        "part": "a100_sxm_80gb",
        "bf16_dense_ops_s": ops,
        "die_area_mm2": die,
        "die_area_grade": die_entry.get("grade"),
        "bf16_source": ("configs/hardware/technology_inputs.json :: "
                        "source_facts.a100_sxm_80gb.bf16_dense_ops_s"),
        "logic_area_fraction": frac,
        "logic_area_fraction_grade": frac_entry.get("grade"),
        "logic_area_fraction_source":
            "configs/hardware/technology.json :: power.gpu_logic_area_fraction",
        "logic_mm2": die * frac,
        "logic_level_ops_s_per_mm2": ops / (die * frac),
        "device_level_ops_s_per_mm2": ops / die,
        "why_logic_and_not_die": (
            "an array of compute units and its distributor is not a product: no "
            "KV cache, no activation buffer, no PHY, no pads. The logic "
            "denominator is the narrower and therefore less flattering of the two."),
    }


def campaign_rows(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, metas = [], []
    for p in paths:
        body = json.loads(p.read_text())
        interval = int(body["control_model"]["interval_datapath_cycles"])
        metas.append({
            "record": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
            "record_sha256": sha(p),
            "schema": body["schema"],
            "simulator": body["simulator"],
            "git_at_measurement": body["git"],
            "sources": body["sources"],
            "vectors": body["vectors"],
            "control_model": body["control_model"],
        })
        for rec in body["records"]:
            n = int(rec["compute_units"])
            #: a record written before the parameters existed is the lockstep
            #: single-buffer design by definition.
            dec = int(rec.get("refill_decoupled", 0))
            banks = int(rec.get("weight_banks", 1))
            for u in rec["utilisation"]:
                if int(u["control_interval_datapath_cycles"]) != interval:
                    continue
                k = int(u["kernel_depth_k"])
                compl = int(u["unit_completions"])
                elapsed = int(u["elapsed_cycles"])
                rows.append({
                    "source_record": metas[-1]["record"],
                    "structure": rec["structure"],
                    "compute_units": n,
                    "refill_skew": int(rec["refill_skew"]),
                    "refill_skew_meaning": SKEW_MEANING.get(int(rec["refill_skew"])),
                    "refill_decoupled": dec,
                    "weight_banks": banks,
                    "kernel_depth_k": k,
                    "passes_per_descriptor": int(u["passes_per_descriptor"]),
                    "elapsed_cycles": elapsed,
                    "unit_completions": compl,
                    #: occupancy counts a unit as busy while it STALLS on an
                    #: unbacked refill -- the bench says so.  The work figure
                    #: divides the K cycles a completed pass actually spends
                    #: multiplying by the elapsed cycles, so a stalled unit earns
                    #: nothing for stalling.
                    "occupancy_utilisation": u["array_utilisation_percent"] / 100.0,
                    "mac_active_utilisation": ((compl / n) * k / elapsed
                                               if compl else None),
                    "refill_grants": u.get("refill_grants"),
                    "refill_grants_per_consumed_column":
                        u.get("refill_grants_per_unit_pass_column"),
                    "functional_pass": rec["functional_pass"],
                    "work_conserved_all_cases": rec["work_conserved_all_cases"],
                    "utilisation_refused": rec.get("utilisation_refused"),
                })
    return rows, metas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--unit", action="append", required=True,
                    metavar="LABEL=PATH",
                    help="post-route record for one ot_compute_unit variant, "
                         "repeatable. The first is the baseline every delta is "
                         "taken against")
    ap.add_argument("--campaign", action="append", required=True, type=Path,
                    help="dispatch-tree campaign record, repeatable")
    ap.add_argument("--stall-campaign", type=Path,
                    default=ROOT / "results/rtl/refill_stall_campaign.json")
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--kernel-depth", type=int, default=256)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    a100 = comparator()
    variants = []
    for item in args.unit:
        label, _, path = item.partition("=")
        rec = physical(Path(path).resolve())
        rec["label"] = label
        p = rec["parameters"]
        rec["refill_decoupled"] = int(p.get("REFILL_DECOUPLED", 0))
        rec["weight_banks"] = int(p.get("WGT_BANKS", 1))
        variants.append(rec)
    base = variants[0]

    crows, cmetas = campaign_rows([p.resolve() for p in args.campaign])
    dist_path = ROOT / DISTRIBUTORS[args.width]
    dist = physical(dist_path)

    #: AREA: what the second bank costs, as a fraction of the unit it serves.
    area_rows = []
    for v in variants:
        area_rows.append({
            "label": v["label"],
            "refill_decoupled": v["refill_decoupled"],
            "weight_banks": v["weight_banks"],
            "macro_count": v["macro_count"],
            "weight_sram_macro_um2": v["macro_area_um2"],
            "standard_cell_um2": v["standard_cell_area_um2"],
            "standard_cell_count": v["standard_cell_count"],
            "occupied_um2": v["occupied_area_um2"],
            "core_um2": v["core_area_um2"],
            "post_route_fmax_hz": v["post_route_fmax_hz"],
            "setup_wns_ns": v["setup_wns_ns"],
            "target_headroom": v["target_headroom"],
            "closed": v["closed"],
            "evidence_class": v["evidence_class"],
            "signal_integrity_violations": v["signal_integrity_violations"],
            "post_route_check_met": v["post_route_check_met"],
            "delta_vs_baseline": {
                "weight_sram_fraction": ((v["macro_area_um2"] / base["macro_area_um2"] - 1)
                                         if base["macro_area_um2"] else None),
                "standard_cell_fraction": (v["standard_cell_area_um2"]
                                           / base["standard_cell_area_um2"] - 1),
                "occupied_fraction": (v["occupied_area_um2"]
                                      / base["occupied_area_um2"] - 1),
                "core_fraction": (v["core_area_um2"] / base["core_area_um2"] - 1),
                "fmax_fraction": ((v["post_route_fmax_hz"] / base["post_route_fmax_hz"] - 1)
                                  if (v["post_route_fmax_hz"] and base["post_route_fmax_hz"])
                                  else None),
            },
            #: the operand-delivery share of the unit, the way
            #: results/derived/sustained_array_iso_area_audit.json states it: the
            #: routed 16-lane tile's own cell area is the arithmetic term.
            "weight_sram_share_of_occupied": (v["macro_area_um2"] / v["occupied_area_um2"]
                                              if v["occupied_area_um2"] else None),
        })

    #: THE RATIOS, recomputed per variant from its own area and frequency.
    ratio_rows = []
    for v in variants:
        f_unit = float(v["post_route_fmax_hz"])
        f_bind = min(f_unit, float(dist["post_route_fmax_hz"]))
        binds = "compute_unit" if f_bind == f_unit else dist["block"]
        area_um2 = args.width * float(v["core_area_um2"]) + float(dist["core_area_um2"])
        area_mm2 = area_um2 / 1e6
        peak = args.width * LANES_PER_UNIT * FLOPS_PER_MAC * f_bind
        peak_ratio = (peak / area_mm2) / a100["logic_level_ops_s_per_mm2"]
        for skew in sorted(SKEW_MEANING):
            r = next((c for c in crows
                      if c["structure"] == "tree"
                      and c["compute_units"] == args.width
                      and c["refill_skew"] == skew
                      and c["passes_per_descriptor"] == args.passes
                      and c["kernel_depth_k"] == args.kernel_depth
                      and c["refill_decoupled"] == v["refill_decoupled"]
                      and c["weight_banks"] == v["weight_banks"]), None)
            if r is None:
                continue
            if not r["functional_pass"] or r["work_conserved_all_cases"] is False:
                ratio_rows.append({
                    "label": v["label"], "refill_skew": skew,
                    "refused": "the utilisation measurement did not pass its "
                               "functional or work-conservation check"})
                continue
            row = {
                "label": v["label"],
                "refill_decoupled": v["refill_decoupled"],
                "weight_banks": v["weight_banks"],
                "compute_units": args.width,
                "passes_per_descriptor": args.passes,
                "kernel_depth_k": args.kernel_depth,
                "refill_skew": skew,
                "refill_skew_meaning": SKEW_MEANING[skew],
                "binding_term": binds,
                "binding_frequency_hz": f_bind,
                "array_area_mm2": area_mm2,
                "peak_bf16_ops_s": peak,
                "peak_ratio_vs_a100_logic": peak_ratio,
                "occupancy_utilisation": r["occupancy_utilisation"],
                "mac_active_utilisation": r["mac_active_utilisation"],
                "elapsed_cycles": r["elapsed_cycles"],
                "refill_grants_per_consumed_column":
                    r["refill_grants_per_consumed_column"],
                "sustained_ratio_vs_a100_logic_occupancy":
                    peak_ratio * r["occupancy_utilisation"],
                "sustained_ratio_vs_a100_logic_mac_active":
                    (peak_ratio * r["mac_active_utilisation"]
                     if r["mac_active_utilisation"] else None),
                "source_record": r["source_record"],
            }
            ratio_rows.append(row)

    def pick_ratio(label: str, skew: int):
        return next((r for r in ratio_rows if r.get("label") == label
                     and r.get("refill_skew") == skew and "refused" not in r), None)

    headline = {}
    best = variants[-1]["label"]
    for skew in sorted(SKEW_MEANING):
        b, n = pick_ratio(base["label"], skew), pick_ratio(best, skew)
        if not (b and n):
            continue
        headline[f"skew_{skew}"] = {
            "meaning": SKEW_MEANING[skew],
            "before_occupancy": b["sustained_ratio_vs_a100_logic_occupancy"],
            "after_occupancy": n["sustained_ratio_vs_a100_logic_occupancy"],
            "before_mac_active": b["sustained_ratio_vs_a100_logic_mac_active"],
            "after_mac_active": n["sustained_ratio_vs_a100_logic_mac_active"],
            "before_elapsed_cycles": b["elapsed_cycles"],
            "after_elapsed_cycles": n["elapsed_cycles"],
            "mac_active_utilisation_before": b["mac_active_utilisation"],
            "mac_active_utilisation_after": n["mac_active_utilisation"],
        }

    #: GATE -- the baseline utilisation, re-measured on the CHANGED bench and the
    #: CHANGED distributor at the lockstep setting, against the committed record
    #: every published figure came from.  A single differing cycle count would
    #: mean the comparison above is against a moved baseline.
    baseline_repro = {"cases": [], "all_identical": None}
    by_key: dict[tuple, list] = {}
    for c in crows:
        if c["refill_decoupled"] or c["weight_banks"] != 1:
            continue
        key = (c["structure"], c["compute_units"], c["refill_skew"],
               c["kernel_depth_k"], c["passes_per_descriptor"])
        by_key.setdefault(key, []).append(c)
    for key, group in sorted(by_key.items()):
        if len(group) < 2:
            continue
        cyc = {g["elapsed_cycles"] for g in group}
        baseline_repro["cases"].append({
            "structure": key[0], "compute_units": key[1], "refill_skew": key[2],
            "kernel_depth_k": key[3], "passes_per_descriptor": key[4],
            "elapsed_cycles_by_record": {g["source_record"]: g["elapsed_cycles"]
                                         for g in group},
            "identical": len(cyc) == 1,
        })
    if baseline_repro["cases"]:
        baseline_repro["all_identical"] = all(c["identical"]
                                              for c in baseline_repro["cases"])
        baseline_repro["why_it_gates"] = (
            "the bench gained parameters and new skew regimes and "
            "ot_dispatch_tree gained an output, so the lockstep rows were "
            "re-measured on the changed files. Every comparable case matching "
            "the committed record cycle for cycle is what licenses comparing the "
            "new rows against the published 2.059x / 1.006x.")

    #: every measured row, at every width in the campaigns given, so the
    #: single-buffer variant and the width agreement are in the artifact even
    #: where this run's headline width has no row for them.
    all_rows = sorted(crows, key=lambda c: (c["structure"], c["refill_decoupled"],
                                            c["weight_banks"], c["compute_units"],
                                            c["refill_skew"],
                                            c["passes_per_descriptor"]))

    stall = None
    if args.stall_campaign.exists():
        sb = json.loads(args.stall_campaign.read_text())
        def pick_stall(d, bk, P, per):
            return next((r for r in sb["rows"]
                         if r.get("refill_decoupled") == d
                         and r.get("weight_banks") == bk
                         and r.get("passes") == P and r.get("refill_period") == per
                         and r.get("nopreload") == bool(d)), None)
        table = []
        for P in sorted({r["passes"] for r in sb["rows"]}):
            for per in sorted({r["refill_period"] for r in sb["rows"]}):
                entry = {"passes_per_descriptor": P, "refill_period": per}
                for v in variants:
                    r = pick_stall(v["refill_decoupled"], v["weight_banks"], P, per)
                    if r:
                        entry[v["label"]] = {
                            "cycles": r.get("cycles"),
                            "stall_cycles": r.get("stall_cycles"),
                            "refill_grants": r.get("refill_grants"),
                            "bit_exact": r.get("bit_exact"),
                        }
                table.append(entry)
        stall = {
            "record": str(args.stall_campaign.relative_to(ROOT)),
            "record_sha256": sha(args.stall_campaign),
            "published_baseline_reproduced":
                sb["published_baseline_reproduced"]["all_agree"],
            "refill_is_the_only_weight_source":
                sb["refill_is_the_only_weight_source"][
                    "all_decoupled_modes_bit_exact_without_the_host_port"],
            "table": table,
        }

    body = {
        "schema": "opentallas.derived.operand_delivery_double_buffer.v1",
        "question": ("Does decoupling weight refill from the MAC tile and double "
                     "buffering the weight bank close the SKEW-2 operand-delivery "
                     "gap, and what does it cost in area and frequency?"),
        "unit": "the operand-delivery change to ot_compute_unit and what it buys",
        "git": git_state(),
        "comparator": a100,
        "compute_unit_variants": variants,
        "distributor_charged": dist,
        "area_cost": area_rows,
        "ratios": ratio_rows,
        "headline": headline,
        "baseline_utilisation_reproduced": baseline_repro,
        "utilisation_rows_all_widths": all_rows,
        "stall_cycles": stall,
        "utilisation_measurements": cmetas,
        "refusals": [
            "the-second-bank-is-in-the-denominator: a variant's sustained ratio "
            "is computed from ITS OWN routed core area and ITS OWN routed "
            "frequency. The double buffer's extra macro pair therefore lowers the "
            "peak density it is multiplied into, and at SKEW 0 that makes the "
            "changed design WORSE than the baseline. Both directions are in the "
            "headline block.",
            "one-pass-descriptors-regress: the fill frontier charges a tile fetch "
            "per descriptor, so with one pass per descriptor there is nothing to "
            "amortise it over and the changed design loses. That regime is also "
            "the one in which every capability's control-path verdict is SHORT "
            "(tools/audit_control_path_throughput.py at --passes-per-descriptor "
            "1), so it is not an operating point -- but it is measured and "
            "reported rather than omitted.",
            "skew-is-a-model-not-a-measurement: SKEW 0-4 are duty cycles imposed "
            "on refill_valid by a testbench. No memory system, interconnect or "
            "DRAM page behaviour produced them, and nothing here says which duty "
            "a real operand-delivery network would deliver.",
            "activation-delivery-not-modelled: the fill frontier covers the "
            "WEIGHT path only. Activations are written at full rate through a "
            "bench port, so an activation-starved array is out of scope and the "
            "75 % operand-delivery energy share includes paths not touched here.",
            "fakeram-is-not-characterised-silicon: the weight banks are FakeRAM "
            "2.0 parts -- plausible geometry with a black-box timing model. The "
            "AREA of a second bank is read from the same LEF the first one came "
            "from, so the RATIO of the two is sound, but no absolute memory "
            "energy or array timing figure may be derived from them.",
            "the-delivery-NETWORK-is-not-designed-or-charged: the fill frontier "
            "needs a 256-bit weight column delivered to each unit. The PORT is on "
            "the routed block, so its input load and the wiring inside the unit "
            "are in the record, but the network that drives 512 of those ports is "
            "not designed here and its area, power and achievable duty are not in "
            "any number above. The refill duty is an input to this measurement, "
            "not an output of it. A design that pays for the buffer and then "
            "cannot build the network that fills it has not closed the gap.",
            "distributor-record-predates-the-new-output: ot_dispatch_tree gained "
            "cu_wgt_reload -- one flop and one AND term per leaf -- after "
            "results/physical_abi3/asap7/dispatch_tree/pnr_g16_l32_0p8.json was "
            "routed, so the distributor area charged here is the version WITHOUT "
            "it. Bound on the error: about two cells per leaf on 32 leaves "
            "against that record's 54,729, and the whole distributor is under "
            "0.17 % of the array's area, so the array denominator moves by less "
            "than one part in 400,000. Stated rather than re-routed.",
            "logic-area-fraction-is-assumed: the A100's 60 % logic fraction is an "
            "assumption, not a published figure, and it sets the denominator of "
            "every ratio here.",
            "core-area-includes-whitespace: the array denominator is the ORFS "
            "CORE area at CORE_UTILIZATION=30, which is what "
            "results/derived/sustained_array_iso_area_audit.json charges, so the "
            "two audits are comparable. The occupied area (standard cells plus "
            "macros) is reported alongside it and is the smaller, more flattering "
            "denominator -- deliberately not the one used.",
        ],
    }

    print(f"comparator: A100 logic-level {a100['logic_level_ops_s_per_mm2']/1e9:.1f} "
          f"Gops/s/mm2 ({a100['logic_area_fraction']*100:.0f}% of "
          f"{a100['die_area_mm2']:.0f} mm2, assumed)")
    print(f"\nAREA, per ot_compute_unit variant (post-route, {args.width}-unit array):")
    print(f"  {'variant':<26} {'macros':>6} {'sram um2':>9} {'cells um2':>10} "
          f"{'occupied':>9} {'core':>9} {'fmax MHz':>9} {'headroom':>8} {'closed':>6}")
    for a in area_rows:
        print(f"  {a['label']:<26} {a['macro_count'] or 0:>6} "
              f"{a['weight_sram_macro_um2'] or 0:>9.1f} "
              f"{a['standard_cell_um2']:>10.1f} {a['occupied_um2']:>9.1f} "
              f"{a['core_um2']:>9.1f} "
              f"{(a['post_route_fmax_hz'] or 0)/1e6:>9.1f} "
              f"{a['target_headroom'] or 0:>8.4f} {str(a['closed']):>6}"
              f"  slew_viol={(a['signal_integrity_violations'] or {}).get('max_slew_violations')}")
    for a in area_rows[1:]:
        d = a["delta_vs_baseline"]
        print(f"  {a['label']} vs {area_rows[0]['label']}: weight SRAM "
              f"{d['weight_sram_fraction']*100:+.1f}%, standard cells "
              f"{d['standard_cell_fraction']*100:+.1f}%, occupied "
              f"{d['occupied_fraction']*100:+.1f}%, core "
              f"{d['core_fraction']*100:+.1f}%, fmax "
              f"{(d['fmax_fraction'] or 0)*100:+.1f}%")

    print(f"\nSUSTAINED RATIO vs the A100's logic area, {args.width} units, "
          f"{args.passes} K={args.kernel_depth} passes per descriptor:")
    print(f"  {'variant':<26} {'skew':>4} {'peak':>7} {'occ%':>7} {'mac%':>7} "
          f"{'sust-occ':>9} {'sust-mac':>9} {'cycles':>7} {'g/col':>6}")
    for r in ratio_rows:
        if "refused" in r:
            print(f"  {r['label']:<26} {r['refill_skew']:>4} REFUSED {r['refused']}")
            continue
        print(f"  {r['label']:<26} {r['refill_skew']:>4} "
              f"{r['peak_ratio_vs_a100_logic']:>6.3f}x "
              f"{r['occupancy_utilisation']*100:>6.2f}% "
              f"{(r['mac_active_utilisation'] or 0)*100:>6.2f}% "
              f"{r['sustained_ratio_vs_a100_logic_occupancy']:>8.3f}x "
              f"{(r['sustained_ratio_vs_a100_logic_mac_active'] or 0):>8.3f}x "
              f"{r['elapsed_cycles']:>7} "
              f"{r['refill_grants_per_consumed_column'] or 0:>6.3f}")

    if baseline_repro["all_identical"] is not None:
        print(f"\nbaseline utilisation re-measured on the changed bench and "
              f"distributor: {len(baseline_repro['cases'])} comparable cases, "
              f"all identical to the committed record: "
              f"{baseline_repro['all_identical']}")
    print("\nHEADLINE, before -> after:")
    for k, h in headline.items():
        print(f"  {k} ({h['meaning'][:44]}): occupancy "
              f"{h['before_occupancy']:.3f}x -> {h['after_occupancy']:.3f}x, "
              f"MAC-active {h['before_mac_active']:.3f}x -> "
              f"{h['after_mac_active']:.3f}x, "
              f"{h['before_elapsed_cycles']} -> {h['after_elapsed_cycles']} cycles")

    if stall:
        print(f"\nSTALL CYCLES (K=32 unit bench), published baseline reproduced: "
              f"{stall['published_baseline_reproduced']}, refill-only delivery "
              f"bit-exact: {stall['refill_is_the_only_weight_source']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
