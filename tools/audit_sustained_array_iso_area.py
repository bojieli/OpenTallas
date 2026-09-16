#!/usr/bin/env python3
"""Sustained array-level iso-area throughput against the A100, from the dispatch tree.

WHAT THIS REPLACES
------------------
``tools/audit_abi3_iso_area_three_level.py`` reports PEAK density at three levels
of inclusion and then de-rates it with a ONE-UNIT starvation measurement
(``tb_kernel_dispatch_throughput.sv``, one ot_compute_unit behind one
ot_kernel_dispatcher) multiplied onto 16-, 32- and 512-unit chips. That
multiplication is only legal if one descriptor is expanded in hardware onto every
unit, and ``tools/audit_control_path_throughput.py`` reported the fan-out SHORT on
all nine capabilities: required_fanout 34, 68 and 1,076 against a flat dispatcher
routed at 16.

``ot_dispatch_tree`` supplies the fan-out and
``results/rtl/dispatch_tree_campaign.json`` measures utilisation on real
ot_compute_unit instances AT WIDTH, so the extrapolation is no longer needed. This
tool computes the sustained figure from the width-resolved measurement instead.

WHAT THE TREE DID AND DID NOT IMPROVE
-------------------------------------
It improved the FREQUENCY term and the EXISTENCE of a routed record at width. It
did NOT improve the utilisation term: at the same control interval, the same
passes-per-descriptor and the same refill regime the tree and the flat dispatcher
retire within 0.04 pp of each other (99.13 % vs 99.12 % at three passes). Any
statement that the tree "improved utilisation" is false and this tool prints the
parity row to make that checkable.

THE THREE TERMS, EACH FROM A RECORD
-----------------------------------
sustained = utilisation x binding_frequency x units x lanes x 2

  utilisation          results/rtl/dispatch_tree_campaign.json, cycle-accurate
                       Verilator 5.050 on real ot_compute_unit instances with
                       their fakeram macros, at the exact width.
  binding_frequency    min(compute unit, distributor). Both are post-route
                       records; which one binds is reported per width, and so is
                       each record's target_headroom, because above ~0.35 an fmax
                       describes the target and not the design.
  units                the width both the campaign row and the distributor
                       record were elaborated at -- never a width only one of
                       them covers.

AND THE DENOMINATOR, WHICH IS WHERE ISO-AREA COMPARISONS GO WRONG
----------------------------------------------------------------
The area charged is every compute unit's placed core area -- which includes its
two ganged weight SRAM macros, i.e. the operand delivery -- plus the
distributor's placed core area. what_is_out lists what an array-level denominator
does not carry, and the ratio is taken against the A100's STANDARD-CELL LOGIC
area rather than its whole die, because an array is not a product and the logic
denominator is the less flattering of the two available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "results/rtl/dispatch_tree_campaign.json"

#: THE REFILL REGIME IS A DESIGN CHOICE AND THE HEADLINE ONLY KNEW ONE OF THEM.
#: ``CAMPAIGN`` measures the LOCKSTEP control, where a unit waiting on an
#: unbacked refill holds the array. Two mitigations were measured at the same
#: width, the same K, the same passes and the same control interval, and each has
#: its own placed core area, so the comparison can be charged rather than
#: asserted:
#:
#:   fill frontier (WGT_BANKS=1)  a unit may run ahead of the slowest peer
#:   double buffer (WGT_BANKS=2)  and may also hold the next weight column
#:
#: Every row retires the SAME 576 completions, so the regimes differ only in the
#: cycles they take -- which is the cleanest form this comparison can take.
REFILL_REGIMES = (
    {
        "regime": "lockstep",
        "campaign": ROOT / "results/rtl/dispatch_tree_campaign.json",
        "area_record": ROOT / "results/physical_abi3/asap7/compute_unit/pnr_lockstep_control_0p8.json",
        "refill_decoupled": 0,
        "weight_banks": 1,
    },
    {
        "regime": "fill_frontier",
        "campaign": ROOT / "results/rtl/dispatch_tree_campaign_frontier_only.json",
        "area_record": ROOT / "results/physical_abi3/asap7/compute_unit/pnr_decoupled_banks1_0p8.json",
        "refill_decoupled": 1,
        "weight_banks": 1,
    },
    {
        "regime": "frontier_double_buffer",
        "campaign": ROOT / "results/rtl/dispatch_tree_campaign_decoupled_refill.json",
        "area_record": ROOT / "results/physical_abi3/asap7/compute_unit/pnr_decoupled_banks2_0p8.json",
        "refill_decoupled": 1,
        "weight_banks": 2,
    },
)
#: The width every regime was measured at. Never a width only one of them covers.
REGIME_WIDTH = 16
THREE_LEVEL = ROOT / "results/derived/abi3_iso_area_three_level_audit.json"
UNIT_PNR = ROOT / "results/physical_abi3/asap7/compute_unit/pnr.json"
TECH_INPUTS = ROOT / "configs/hardware/technology_inputs.json"
TECHNOLOGY = ROOT / "configs/hardware/technology.json"

#: Lanes in one ot_compute_unit, read back from the record's own RTL below.
LANES_PER_UNIT = 16
FLOPS_PER_MAC = 2

#: Rule: target_headroom = setup WNS / target period. Above this an fmax
#: describes the target rather than the design.
HEADROOM_SUSPECT = 0.35

#: The distributor record to charge at each array width. Every entry is a width
#: the campaign ALSO measured at, so no row mixes a distributor elaborated at one
#: width with a utilisation measured at another.
DISTRIBUTORS = {
    16: [("results/physical_abi3/asap7/cluster_dispatcher/pnr.json", "flat")],
    512: [("results/physical_abi3/asap7/dispatch_tree/pnr_g16_l32_0p8.json", "tree")],
    1088: [("results/physical_abi3/asap7/dispatch_tree/pnr_g16_l68_1p2.json", "tree"),
           ("results/physical_abi3/asap7/dispatch_tree/pnr_g16_l68_0p8.json", "tree")],
}

#: The regime the campaign parameterises as SKEW, in the testbench's own words.
SKEW_MEANING = {
    0: "every unit always fed: refill_valid asserted every cycle at every unit",
    1: "every unit slowed a little and by a different amount",
    2: "STRAGGLERS -- one unit in sixteen at a 50% refill duty",
}


def git_state(input_paths: set[str] | None = None) -> dict[str, Any]:
    """HEAD, and whether any path this audit actually READ is dirty.

    A dirty worktree is not by itself a defect -- 89 unrelated files can be
    modified without touching a single input. What matters is the intersection,
    so that is what is reported, alongside the total so the reader can see the
    filter is doing work.
    """
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    porcelain = run("status", "--porcelain").splitlines()
    dirty = {l[3:].strip() for l in porcelain}
    inputs = input_paths or set()
    overlap = sorted(dirty & inputs)
    return {
        "commit": run("rev-parse", "HEAD") or None,
        "branch": run("rev-parse", "--abbrev-ref", "HEAD") or None,
        "worktree_dirty": bool(porcelain),
        "dirty_path_count": len(porcelain),
        "input_path_count": len(inputs),
        "input_paths": sorted(inputs),
        "dirty_input_paths": overlap,
        "any_input_dirty": bool(overlap),
        "note": ("dirty_input_paths is the intersection of the dirty worktree "
                 "with the files and records this audit read. An empty list "
                 "means every number here came from a file identical to its "
                 "committed state, whatever else in the tree is modified. "
                 "Source-currency is checked separately and per record: a "
                 "record whose RTL has changed since it was built is flagged in "
                 "its own source_currency block even when the tree is clean."),
    }


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def source_currency(rec: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for s in rec.get("sources") or []:
        cur = sha(ROOT / s["path"])
        rows.append({"path": s["path"], "recorded_sha256": s.get("sha256"),
                     "current_sha256": cur, "current": cur == s.get("sha256")})
    return {"all_current": all(r["current"] for r in rows) if rows else None,
            "files": rows,
            "drifted": [r["path"] for r in rows if not r["current"]]}


def comparator() -> dict[str, Any]:
    facts = json.loads(TECH_INPUTS.read_text())["source_facts"]["a100_sxm_80gb"]
    tech = json.loads(TECHNOLOGY.read_text())
    die = tech["reference_parts"]["a100_sxm_80gb"]["die_area_mm2"]
    frac = tech["power"]["gpu_logic_area_fraction"]
    ops = float(facts["bf16_dense_ops_s"])
    die_mm2 = float(die["value"])
    logic_mm2 = die_mm2 * float(frac["value"])
    return {
        "part": "a100_sxm_80gb",
        "process": facts["process"],
        "bf16_dense_ops_s": ops,
        "bf16_source": "configs/hardware/technology_inputs.json :: "
                       "source_facts.a100_sxm_80gb.bf16_dense_ops_s",
        "bf16_evidence": facts["evidence"],
        "die_area_mm2": die_mm2,
        "die_area_grade": die.get("grade"),
        "logic_area_fraction": float(frac["value"]),
        "logic_area_fraction_grade": frac.get("grade"),
        "logic_area_mm2": logic_mm2,
        "logic_level_ops_s_per_mm2": ops / logic_mm2,
        "device_level_ops_s_per_mm2": ops / die_mm2,
        "why_logic_and_not_die": ("an array of compute units and its distributor "
                                 "is not a product: it has no KV cache, no "
                                 "activation buffer, no PHY and no pads. Charging "
                                 "it against the A100's whole 826 mm2 die would "
                                 "credit it with every square millimetre it does "
                                 "not have, which is the error "
                                 "tools/audit_mac_array_density.py exists to "
                                 "refuse. The logic denominator is the narrower "
                                 "and therefore less flattering of the two."),
    }


def physical(path: Path) -> dict[str, Any]:
    body = json.loads(path.read_text())
    d = body["design"]
    metrics = (body.get("place_and_route") or {}).get("metrics") or {}
    period = d.get("clock_period_ns")
    wns = d.get("setup_wns_ns")
    headroom = (wns / period) if (period and wns is not None) else None
    sta = body.get("static_timing") or {}
    acc = body.get("acceptance") or {}
    post = [c for c in acc.get("checks", [])
            if c.get("scope") == "post-route, extracted parasitics"]
    pre = [c for c in acc.get("checks", [])
           if c.get("scope") == "pre-layout, ideal clock"]
    return {
        "record": str(path.relative_to(ROOT)),
        "record_sha256": sha(path),
        "block": d.get("block"),
        "top": d.get("top"),
        "parameters": d.get("parameters"),
        "target_clock_period_ns": period,
        "post_route_fmax_hz": d.get("fmax_hz"),
        "standard_cell_count": d.get("cells"),
        "standard_cell_area_um2": d.get("area_um2"),
        "core_area_um2": d.get("core_area_um2"),
        "macro_area_um2": metrics.get("macro_area_um2"),
        "macro_count": metrics.get("macro_count"),
        "utilization_fraction": d.get("utilization_fraction"),
        "power_total_w_default_activity": metrics.get("power_total_w"),
        "setup_wns_ns": wns,
        "target_headroom": headroom,
        "target_headroom_suspect": (headroom is not None
                                    and headroom > HEADROOM_SUSPECT),
        "signal_integrity_violations": d.get("signal_integrity_violations"),
        "closed": d.get("closed"),
        "acceptance_status": acc.get("status"),
        "acceptance_reason": acc.get("reason"),
        "post_route_check_met": (post[0].get("met") if post else None),
        "pre_layout_check_met": (pre[0].get("met") if pre else None),
        "pre_layout_setup_wns_ns": sta.get("setup_wns_ns"),
        "pre_layout_setup_violating_paths": sta.get("setup_violating_paths"),
        "closure_verdict_is_a_flow_artifact": bool(
            post and post[0].get("met") and pre and pre[0].get("met") is False),
        "evidence_class": ("ROUTED AND CLOSED" if d.get("closed")
                           else ("ROUTED, POST-ROUTE CLEAN, NOT CLOSED"
                                 if (post and post[0].get("met"))
                                 else "ROUTED, NOT CLOSED")),
        "source_currency": source_currency(d),
    }


def refill_regime_comparison(k: int, passes: int) -> dict[str, Any]:
    """Work per unit area for each refill regime, at each measured skew.

    THE ANSWER DEPENDS ON THE STRAGGLER MODEL, which is why this is a table and
    not a recommendation. Charging each regime's own placed core area against the
    work it retires, the lockstep control wins at skew 1 and loses badly at skew
    2, and the double buffer is the reverse: it earns its ~30 % area only when
    there are stragglers to absorb. A flat claim either way is wrong at one of
    the two points.

    ``mac_active`` is the honest metric here and occupancy is not: occupancy
    counts a unit as busy while it STALLS on an unbacked refill, which is exactly
    the thing these regimes exist to remove, so it flatters every one of them.
    """
    base_area: float | None = None
    rows: list[dict[str, Any]] = []
    for spec in REFILL_REGIMES:
        if not spec["campaign"].exists() or not spec["area_record"].exists():
            rows.append({"regime": spec["regime"], "refused":
                         "no campaign or area record at this regime"})
            continue
        area = float(json.loads(spec["area_record"].read_text())
                     ["design"]["core_area_um2"])
        if spec["regime"] == "lockstep":
            base_area = area
        body = json.loads(spec["campaign"].read_text())
        for rec in body["records"]:
            if int(rec["compute_units"]) != REGIME_WIDTH:
                continue
            if rec["structure"] != "tree":
                continue
            for u in rec.get("utilisation", []):
                if (int(u["kernel_depth_k"]) != k
                        or int(u["passes_per_descriptor"]) != passes):
                    continue
                completions = int(u["unit_completions"])
                if not completions:
                    continue
                elapsed = int(u["elapsed_cycles"])
                rows.append({
                    "regime": spec["regime"],
                    "refill_decoupled": spec["refill_decoupled"],
                    "weight_banks": spec["weight_banks"],
                    "refill_skew": int(rec["refill_skew"]),
                    "refill_skew_meaning": SKEW_MEANING.get(int(rec["refill_skew"])),
                    "compute_units": REGIME_WIDTH,
                    "kernel_depth_k": k,
                    "passes_per_descriptor": passes,
                    "control_interval_datapath_cycles":
                        int(u["control_interval_datapath_cycles"]),
                    "unit_completions": completions,
                    "elapsed_cycles": elapsed,
                    "occupancy_utilisation": u["array_utilisation_percent"] / 100.0,
                    "mac_active_utilisation":
                        (completions / REGIME_WIDTH) * k / elapsed,
                    "unit_core_area_um2": area,
                    "campaign": str(spec["campaign"].relative_to(ROOT)),
                    "campaign_sha256": sha(spec["campaign"]),
                    "area_record": str(spec["area_record"].relative_to(ROOT)),
                    "area_record_sha256": sha(spec["area_record"]),
                })
    for row in rows:
        if "refused" in row or base_area is None:
            continue
        multiplier = row["unit_core_area_um2"] / base_area
        row["area_multiplier_vs_lockstep"] = multiplier
        row["mac_active_per_unit_area"] = row["mac_active_utilisation"] / multiplier
        row["occupancy_per_unit_area"] = row["occupancy_utilisation"] / multiplier

    best: dict[int, dict[str, Any]] = {}
    for row in rows:
        if "refused" in row:
            continue
        skew = row["refill_skew"]
        if (skew not in best
                or row["mac_active_per_unit_area"] > best[skew]["mac_active_per_unit_area"]):
            best[skew] = row
    return {
        "question": ("charging each refill regime's own placed core area, which "
                     "one retires the most work per unit area at each measured "
                     "straggler level?"),
        "width": REGIME_WIDTH,
        "kernel_depth_k": k,
        "passes_per_descriptor": passes,
        "metric": ("mac_active_utilisation / (unit core area / the lockstep "
                   "control's unit core area)"),
        "why_not_occupancy": ("occupancy counts a unit as busy while it stalls on "
                             "an unbacked refill, which is the very thing these "
                             "regimes remove, so it flatters all of them"),
        "same_work_basis": ("every row retires the same unit_completions, so the "
                            "regimes differ in elapsed cycles alone"),
        "rows": rows,
        "best_per_skew": {
            str(skew): {
                "regime": row["regime"],
                "weight_banks": row["weight_banks"],
                "mac_active_per_unit_area": row["mac_active_per_unit_area"],
            }
            for skew, row in sorted(best.items())
        },
        "refusals": [
            "no-single-recommendation: the winner changes with the straggler "
            "model, so this reports a table and a per-skew best rather than one "
            "operating point.",
            "one-width-only: every regime was measured at "
            f"{REGIME_WIDTH} compute units, and no regime row is extrapolated to "
            "a width it was not elaborated at.",
            "skew0-not-measured-for-the-mitigations: the two decoupled campaigns "
            "carry skew 1 and skew 2 only, so no regime comparison is made at "
            "skew 0 -- where by construction there is nothing for them to fix.",
        ],
    }


def _skew2_best(regimes: dict[str, Any], srow: dict[str, Any]) -> dict[str, Any]:
    """Rescale the LOCKSTEP skew-2 ratios by the best regime's work per area.

    The sustained figures are computed from the lockstep campaign, so their
    skew-2 rows carry a utilisation the design need not accept: two mitigations
    are measured and placed. The rescale is the ratio of work per UNIT AREA at
    the same skew, width, kernel depth and passes -- so the mitigation's own area
    is charged and the comparison stays iso-area.

    It is a DERIVED number and says so: the sustained pipeline was not re-run at
    the mitigated width, and a regime's own fmax may differ from the binding term
    the headline used. Treat it as the size of the recoverable gap, not as a
    second measurement.
    """
    rows = [r for r in regimes["rows"]
            if "refused" not in r and r["refill_skew"] == 2]
    if not rows:
        return {"refused": "no skew-2 regime row is available"}
    lockstep = next((r for r in rows if r["regime"] == "lockstep"), None)
    best = max(rows, key=lambda r: r["mac_active_per_unit_area"])
    if lockstep is None or not lockstep["mac_active_per_unit_area"]:
        return {"refused": "no lockstep skew-2 row to scale from"}
    gain = best["mac_active_per_unit_area"] / lockstep["mac_active_per_unit_area"]
    return {
        "regime": best["regime"],
        "weight_banks": best["weight_banks"],
        "work_per_area_gain_vs_lockstep_at_skew2": gain,
        "rescaled_ratio_at_skew2_occupancy":
            srow["sustained_occupancy"]["ratio_vs_a100_logic"] * gain,
        "rescaled_ratio_at_skew2_mac_active":
            srow["sustained_mac_active"]["ratio_vs_a100_logic"] * gain,
        "basis": ("lockstep skew-2 sustained ratio x (best regime work per unit "
                  "area / lockstep work per unit area), both at "
                  f"{regimes['width']} units, K={regimes['kernel_depth_k']}, "
                  f"{regimes['passes_per_descriptor']} passes"),
        "derived_not_measured": ("the sustained pipeline was not re-run with this "
                                 "regime's own campaign and fmax; this is the "
                                 "recoverable gap, not a second measurement"),
    }


def campaign_rows() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Utilisation, occupancy AND work-based, at the measured control interval."""
    body = json.loads(CAMPAIGN.read_text())
    interval = int(body["control_model"]["interval_datapath_cycles"])
    rows = []
    for rec in body["records"]:
        n = int(rec["compute_units"])
        for u in rec["utilisation"]:
            if int(u["control_interval_datapath_cycles"]) != interval:
                continue
            k = int(u["kernel_depth_k"])
            compl = int(u["unit_completions"])
            elapsed = int(u["elapsed_cycles"])
            #: Occupancy counts a unit as busy while it STALLS on an unbacked
            #: refill -- the testbench says so. The work figure divides the
            #: K cycles a completed pass actually spends multiplying by the
            #: elapsed cycles, so a stalled unit earns nothing for stalling.
            mac = (compl / n) * k / elapsed if compl else None
            rows.append({
                "structure": rec["structure"],
                "distributor_module": rec["distributor_module"],
                "compute_units": n,
                "leaves": rec["leaves"], "group": rec["group"],
                "radix": rec["radix"], "credits": rec["credits"],
                "refill_skew": rec["refill_skew"],
                "refill_skew_meaning": SKEW_MEANING.get(rec["refill_skew"]),
                "kernel_depth_k": k,
                "passes_per_descriptor": int(u["passes_per_descriptor"]),
                "control_interval_datapath_cycles": interval,
                "occupancy_utilisation": u["array_utilisation_percent"] / 100.0,
                "mac_active_utilisation": mac,
                "mac_active_basis": ("unit_completions/compute_units x "
                                     "kernel_depth_k / elapsed_cycles"),
                "mac_active_refused": (None if compl else
                                       "the flat harness does not instrument "
                                       "unit_completions, so no work-based "
                                       "figure is derivable for this row"),
                "elapsed_cycles": elapsed,
                "unit_completions": compl,
                "pass_rate_per_unit_cycles": u["pass_rate_per_unit_cycles"],
                "root_stalled_for_credit_percent": u["root_stalled_for_credit_percent"],
                "root_idle_queue_empty_percent": u["root_idle_queue_empty_percent"],
                "functional_pass": rec["functional_pass"],
                "work_conserved_all_cases": rec["work_conserved_all_cases"],
            })
    meta = {
        "record": str(CAMPAIGN.relative_to(ROOT)),
        "record_sha256": sha(CAMPAIGN),
        "schema": body["schema"],
        "simulator": body["simulator"],
        "git_at_measurement": body["git"],
        "control_model": body["control_model"],
        "source_currency": source_currency(body),
        "vector_currency": source_currency({"sources": body["vectors"]}),
        "refusals": body["refusals"],
        "evidence_class": ("CYCLE-ACCURATE RTL, real ot_compute_unit instances "
                           "with their fakeram macros, at width"),
    }
    return meta, rows


def pick(rows: list[dict[str, Any]], **kw: Any) -> dict[str, Any] | None:
    for r in rows:
        if all(r.get(k) == v for k, v in kw.items()):
            return r
    return None


def verify_borrowed(a100: dict[str, Any], three: dict[str, Any],
                    L3: dict[str, Any]) -> dict[str, Any]:
    """Re-derive, from PRIMARY place-and-route records, every figure this audit
    borrows from ``results/derived/abi3_iso_area_three_level_audit.json``.

    That file is UNTRACKED -- it exists on disk and not in any commit -- so it is
    treated as a convenience index and never as a source of truth. Each borrowed
    number is recomputed here from the records it was itself computed from, and
    the two are compared. A divergence means the on-disk file is stale and the
    re-derived value is the one to trust.
    """
    def ratio(record: str, lanes: int, comparator_key: str) -> dict[str, Any]:
        r = physical(ROOT / record)
        peak = lanes * FLOPS_PER_MAC * float(r["post_route_fmax_hz"])
        area = float(r["core_area_um2"]) / 1e6
        return {"record": record, "lanes": lanes,
                "post_route_fmax_hz": r["post_route_fmax_hz"],
                "core_area_mm2": area, "peak_bf16_ops_s": peak,
                "ops_s_per_mm2": peak / area,
                "ratio": (peak / area) / a100[comparator_key],
                "evidence_class": r["evidence_class"]}

    checks = []

    def add(name: str, recomputed: float, recorded: float,
            basis: str, extra: dict[str, Any] | None = None) -> None:
        agree = (recorded is not None
                 and abs(recomputed - recorded) <= 1e-9 * max(1.0, abs(recorded)))
        checks.append({"figure": name, "re_derived": recomputed,
                       "value_in_untracked_file": recorded,
                       "agrees": agree, "basis": basis, **(extra or {})})

    l1 = ratio("results/physical_abi3/asap7/mac_tile/pnr_lanes16.json", 16,
               "logic_level_ops_s_per_mm2")
    add("L1_array_level_peak_ratio_vs_a100_logic", l1["ratio"],
        next(L["ratio"] for L in three["levels"] if L["level"].startswith("L1")),
        "LANES x 2 x post-route fmax over the record's own placed core area",
        {"detail": l1})
    l2 = ratio("results/physical_abi3/asap7/compute_unit/pnr.json", 16,
               "logic_level_ops_s_per_mm2")
    add("L2_unit_level_peak_ratio_vs_a100_logic", l2["ratio"],
        next(L["ratio"] for L in three["levels"] if L["level"].startswith("L2")),
        "LANES x 2 x post-route fmax over the record's own placed core area",
        {"detail": l2})

    #: L3 per capability: rebuild the chip area from its own component records
    #: and the binding datapath clock from the slowest datapath block in it.
    dev_checks = []
    for cap in L3["per_capability"]:
        total = 0.0
        clocks = []
        comps = []
        for c in cap["components"]:
            rp = ROOT / c["record"]
            if not rp.exists():
                comps.append({"name": c["name"], "record": c["record"],
                              "re_derived": None,
                              "why": "record not on disk"})
                total = None
                break
            r = physical(rp)
            each = float(r["core_area_um2"])
            total += each * int(c["instances"])
            comps.append({"name": c["name"], "record": c["record"],
                          "instances": c["instances"],
                          "core_area_um2_each_re_derived": each,
                          "core_area_um2_each_in_file": c["core_area_um2_each"],
                          "agrees": abs(each - float(c["core_area_um2_each"])) < 1e-6,
                          "post_route_fmax_hz": r["post_route_fmax_hz"],
                          "closed": r["closed"]})
            if c["name"] != "microsequencer":
                clocks.append((c["name"], float(r["post_route_fmax_hz"])))
        if total is None:
            dev_checks.append({"capability": cap["capability"],
                               "re_derivable": False, "components": comps})
            continue
        fbind = min(f for _, f in clocks)
        binds = next(n for n, f in clocks if f == fbind)
        peak = int(cap["tensor_lanes"]) * FLOPS_PER_MAC * fbind
        area_mm2 = total / 1e6
        dev_checks.append({
            "capability": cap["capability"],
            "re_derivable": True,
            "chip_area_mm2_re_derived": area_mm2,
            "chip_area_mm2_in_file": cap["chip_area_mm2"],
            "area_agrees": abs(area_mm2 - float(cap["chip_area_mm2"])) < 1e-6,
            "datapath_clock_hz_re_derived": fbind,
            "datapath_clock_binding_block_re_derived": binds,
            "datapath_clock_binding_block_in_file":
                cap["datapath_clock_binding_block"],
            "peak_bf16_ops_s_re_derived": peak,
            "peak_bf16_ops_s_in_file": cap["peak_bf16_ops_s"],
            "peak_ratio_vs_a100_device_re_derived":
                (peak / area_mm2) / a100["device_level_ops_s_per_mm2"],
            "peak_ratio_vs_a100_device_in_file": cap["ratio"],
            "ratio_agrees": abs((peak / area_mm2)
                                / a100["device_level_ops_s_per_mm2"]
                                - float(cap["ratio"])) < 1e-9,
            "components": comps,
        })

    #: the energy attribution, from the three routed records it subtracts
    u = physical(ROOT / "results/physical_abi3/asap7/compute_unit/pnr.json")
    t = physical(ROOT / "results/physical_abi3/asap7/mac_tile/pnr_lanes16.json")
    lp = physical(ROOT / "results/physical_abi3/asap7/mac_lanes/lane_bf16.json")
    pu = float(u["power_total_w_default_activity"])
    pt = float(t["power_total_w_default_activity"])
    pl = float(lp["power_total_w_default_activity"])
    att = three["attribution"]
    add("operand_delivery_power_fraction_by_tile_subtraction", (pu - pt) / pu,
        att["power_by_tile_subtraction"]["operand_delivery_fraction"],
        "(compute unit power - 16-lane tile power) / compute unit power, both "
        "from place_and_route.metrics.power_total_w")
    add("operand_delivery_power_fraction_by_lane_subtraction",
        (pu - 16 * pl) / pu,
        att["power_by_lane_probe_subtraction"]["operand_delivery_fraction"],
        "(compute unit power - 16 x lane probe power) / compute unit power")
    occ = float(u["standard_cell_area_um2"]) + float(u["macro_area_um2"])
    add("operand_delivery_area_fraction",
        (occ - float(t["standard_cell_area_um2"])) / occ,
        att["area_by_tile_subtraction"]["operand_delivery_fraction"],
        "(compute unit standard cells + SRAM macros - tile standard cells) / "
        "compute unit occupied area")

    return {
        "why": ("results/derived/abi3_iso_area_three_level_audit.json is "
                "UNTRACKED: it is on disk and in no commit. Every figure this "
                "audit borrows from it is therefore re-derived from the primary "
                "place-and-route records and compared. The comparator itself is "
                "NOT borrowed -- it is read directly from "
                "configs/hardware/technology.json and technology_inputs.json, "
                "which are tracked."),
        "all_agree": (all(c["agrees"] for c in checks)
                      and all(d.get("area_agrees") and d.get("ratio_agrees")
                              for d in dev_checks if d["re_derivable"])),
        "scalar_checks": checks,
        "device_level_checks": dev_checks,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kernel-depth", type=int, default=256)
    ap.add_argument("--headline-passes", type=int, default=3,
                    help="passes per descriptor the headline quotes (default 3)")
    ap.add_argument("--headline-width", type=int, default=512,
                    help="array width the headline quotes (default 512)")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/derived/sustained_array_iso_area_audit.json")
    args = ap.parse_args()

    a100 = comparator()
    unit = physical(UNIT_PNR)
    cmeta, crows = campaign_rows()
    k = args.kernel_depth

    #: every file this audit reads, so the git block can intersect it with the
    #: dirty worktree instead of guessing by path prefix.
    inputs: set[str] = {
        str(CAMPAIGN.relative_to(ROOT)), str(THREE_LEVEL.relative_to(ROOT)),
        str(UNIT_PNR.relative_to(ROOT)), str(TECH_INPUTS.relative_to(ROOT)),
        str(TECHNOLOGY.relative_to(ROOT)),
        "tools/audit_control_path_throughput.py",
    }
    inputs |= {f["path"] for f in cmeta["source_currency"]["files"]}
    inputs |= {f["path"] for f in cmeta["vector_currency"]["files"]}
    inputs |= {f["path"] for f in unit["source_currency"]["files"]}
    for _specs in DISTRIBUTORS.values():
        for _p, _ in _specs:
            inputs.add(_p)
            inputs |= {f["path"]
                       for f in physical(ROOT / _p)["source_currency"]["files"]}
    #: The refill-regime records too, or the currency note would claim every
    #: number came from a committed file while the regime comparison read files
    #: the filter never looked at.
    for _spec in REFILL_REGIMES:
        for _path in (_spec["campaign"], _spec["area_record"]):
            if _path.exists():
                inputs.add(str(_path.relative_to(ROOT)))

    f_unit = float(unit["post_route_fmax_hz"])
    unit_area = float(unit["core_area_um2"])

    widths = []
    for n, specs in sorted(DISTRIBUTORS.items()):
        dist_variants = [ {**physical(ROOT / p), "structure": st} for p, st in specs ]
        for dv in dist_variants:
            #: the frequency an array of this width can be clocked at is the
            #: lower of the two blocks that have to run at the same rate.
            f_bind = min(f_unit, float(dv["post_route_fmax_hz"]))
            binds = ("compute_unit" if f_bind == f_unit else dv["block"])
            units_area = n * unit_area
            area_um2 = units_area + float(dv["core_area_um2"])
            area_mm2 = area_um2 / 1e6
            peak = n * LANES_PER_UNIT * FLOPS_PER_MAC * f_bind
            rows = []
            for st in ("tree", "flat"):
                for skew in (0, 1, 2):
                    for p in (1, 2, 3, 4, 8):
                        r = pick(crows, structure=st, compute_units=n,
                                 refill_skew=skew, passes_per_descriptor=p,
                                 kernel_depth_k=k)
                        if r is None:
                            continue
                        entry = {
                            "utilisation_structure": st,
                            "structure_matches_charged_distributor":
                                st == dv["structure"],
                            "refill_skew": skew,
                            "refill_skew_meaning": SKEW_MEANING[skew],
                            "passes_per_descriptor": p,
                            "occupancy_utilisation": r["occupancy_utilisation"],
                            "mac_active_utilisation": r["mac_active_utilisation"],
                            "functional_pass": r["functional_pass"],
                        }
                        for basis, u in (("occupancy", r["occupancy_utilisation"]),
                                         ("mac_active", r["mac_active_utilisation"])):
                            if u is None:
                                entry[f"sustained_{basis}"] = None
                                continue
                            ops = peak * u
                            entry[f"sustained_{basis}"] = {
                                "sustained_bf16_ops_s": ops,
                                "ops_s_per_mm2": ops / area_mm2,
                                "ratio_vs_a100_logic":
                                    (ops / area_mm2) / a100["logic_level_ops_s_per_mm2"],
                            }
                        rows.append(entry)
            widths.append({
                "compute_units": n,
                "distributor": dv,
                "frequency": {
                    "compute_unit_hz": f_unit,
                    "compute_unit_record": unit["record"],
                    "compute_unit_standard_cell_count": unit["standard_cell_count"],
                    "compute_unit_target_headroom": unit["target_headroom"],
                    "distributor_hz": dv["post_route_fmax_hz"],
                    "distributor_standard_cell_count": dv["standard_cell_count"],
                    "distributor_target_headroom": dv["target_headroom"],
                    "binding_hz": f_bind,
                    "binding_term": binds,
                    "note": ("the distributor and the units are one clock domain "
                             "in this arithmetic, so the array runs at the lower "
                             "of the two post-route figures"),
                },
                "area_denominator": {
                    "compute_units_core_area_um2_each": unit_area,
                    "compute_units_core_area_um2_total": units_area,
                    "compute_unit_macro_area_um2_each": unit["macro_area_um2"],
                    "compute_unit_macro_count_each": unit["macro_count"],
                    "distributor_core_area_um2": dv["core_area_um2"],
                    "distributor_share_of_array_area":
                        float(dv["core_area_um2"]) / area_um2,
                    "total_um2": area_um2,
                    "total_mm2": area_mm2,
                    "area_basis": ("place_and_route.metrics.core_area_um2 -- the "
                                   "PLACED core of each block, not its cell area: "
                                   "cell area ignores the utilisation a real "
                                   "floorplan must leave and excludes SRAM macros"),
                    "what_is_in": [
                        "every ot_compute_unit's placed core: 16 MAC lanes, the "
                        "operand broadcast tree, the accumulators, the K-walking "
                        "sequencer, the activation register file AND the two "
                        "ganged fakeram_256x128 weight SRAM macros",
                        "the descriptor distributor's placed core at this exact "
                        "width",
                    ],
                    "what_is_out": [
                        "the microsequencer that produces the descriptors (its "
                        "rate is charged, via the 567-cycle control interval, but "
                        "its 136,926 um2 core is not)",
                        "vector engines", "reduction endpoints",
                        "KV-cache SRAM", "global activation buffer",
                        "HBM PHY and memory controller",
                        "the mask-ROM array itself, for the ROM capabilities",
                        "clock distribution and power delivery",
                        "pad ring and I/O",
                        "the array floorplan: this is a sum of separately placed "
                        "blocks, not one route of N units around a distributor, "
                        "so the wire from a leaf to its unit is not in any "
                        "record's area or timing",
                    ],
                },
                "peak_bf16_ops_s_at_binding_clock": peak,
                "peak_ops_s_per_mm2": peak / area_mm2,
                "peak_ratio_vs_a100_logic":
                    (peak / area_mm2) / a100["logic_level_ops_s_per_mm2"],
                "sustained": rows,
            })

    #: ---- tree vs flat: the parity that says what the tree did NOT fix -------
    parity = []
    for n in sorted({r["compute_units"] for r in crows}):
        for skew in (0, 1, 2):
            for p in (1, 3):
                t = pick(crows, structure="tree", compute_units=n,
                         refill_skew=skew, passes_per_descriptor=p,
                         kernel_depth_k=k)
                f = pick(crows, structure="flat", compute_units=n,
                         refill_skew=skew, passes_per_descriptor=p,
                         kernel_depth_k=k)
                if not (t and f):
                    continue
                parity.append({
                    "compute_units": n, "refill_skew": skew,
                    "passes_per_descriptor": p,
                    "tree_occupancy": t["occupancy_utilisation"],
                    "flat_occupancy": f["occupancy_utilisation"],
                    "difference_pp": (t["occupancy_utilisation"]
                                      - f["occupancy_utilisation"]) * 100,
                })

    #: ---- width invariance, at the headline operating point -----------------
    inv = [r for r in crows
           if r["structure"] == "tree" and r["refill_skew"] == 0
           and r["passes_per_descriptor"] == args.headline_passes
           and r["kernel_depth_k"] == k]
    inv.sort(key=lambda r: r["compute_units"])
    occ = [r["occupancy_utilisation"] for r in inv]
    macs = [r["mac_active_utilisation"] for r in inv if r["mac_active_utilisation"]]

    #: ---- device level: the same de-rating on the whole-chip denominator ----
    three = json.loads(THREE_LEVEL.read_text())
    L3 = next(L for L in three["levels"] if L["level"].startswith("L3"))
    dev = []
    for cap in L3["per_capability"]:
        tcu = next((c for c in cap["components"]
                    if c["name"] == "tensor_compute_unit"), None)
        n = int(tcu["instances"]) if tcu else None
        old_disp = next((c for c in cap["components"]
                         if c["name"] == "cluster_dispatcher"), None)
        #: the recorded chip substitutes a 16-wide FLAT dispatcher at every
        #: width, including 512. Charge the routed tree at the array's own width
        #: instead, and say what that costs.
        tree_specs = DISTRIBUTORS.get(n)
        tree = physical(ROOT / tree_specs[0][0]) if tree_specs else None
        corr = None
        if tree and old_disp and n not in (16,):
            delta = (float(tree["core_area_um2"])
                     - float(old_disp["area_um2_total"]))
            corr = {
                "recorded_distributor": old_disp["record"],
                "recorded_distributor_instances": old_disp["instances"],
                "recorded_distributor_area_um2_each":
                    old_disp["core_area_um2_each"],
                "recorded_distributor_area_um2_total":
                    old_disp["area_um2_total"],
                "recorded_distributor_routed_width_each": 16,
                "substituted_distributor": tree["record"],
                "substituted_distributor_instances": 1,
                "substituted_distributor_area_um2": tree["core_area_um2"],
                "substituted_width": n,
                "area_delta_um2": delta,
                "area_delta_share_of_recorded_chip":
                    delta / (cap["chip_area_mm2"] * 1e6),
                "corrected_chip_area_mm2": cap["chip_area_mm2"] + delta / 1e6,
                "why": ("the recorded %d-unit chip charges %s instances of the "
                        "16-wide FLAT ot_cluster_dispatcher and puts nothing "
                        "between them and the single microsequencer, so no block "
                        "in it expands one descriptor onto all %d units -- the "
                        "sequencer would have to issue %s descriptors per kernel, "
                        "which is the rate shortfall "
                        "tools/audit_control_path_throughput.py reports. One "
                        "routed ot_dispatch_tree at the array's own width is "
                        "charged instead, and it is SMALLER than the %s flat "
                        "dispatchers it replaces."
                        % (n, old_disp["instances"], n,
                           old_disp["instances"], old_disp["instances"])),
            }
        area_mm2 = (corr["corrected_chip_area_mm2"] if corr
                    else cap["chip_area_mm2"])
        row = {"capability": cap["capability"], "tensor_compute_units": n,
               "tensor_lanes": cap["tensor_lanes"],
               "recorded_peak_bf16_ops_s": cap["peak_bf16_ops_s"],
               "recorded_chip_area_mm2": cap["chip_area_mm2"],
               "distributor_area_correction": corr,
               "chip_area_mm2_used": area_mm2,
               "datapath_clock_binding_block": cap["datapath_clock_binding_block"],
               "datapath_clock_hz": cap["datapath_clock_hz"],
               "peak_ratio_vs_a100_device": cap["ratio"],
               "utilisation_evidence": None, "sustained": {}}
        row["utilisation_structure_note"] = (
            "the utilisation row used is the TREE row at this width. The recorded "
            "chip charges flat ot_cluster_dispatcher instances, and the "
            "tree_vs_flat_cycle_parity block shows the two are within 0.09 pp at "
            "every matched point, so the choice moves no digit that is quoted "
            "here. The area correction above swaps the flat instances for the "
            "tree that actually supplies the fan-out.")
        u_row = pick(crows, structure="tree", compute_units=n, refill_skew=0,
                     passes_per_descriptor=args.headline_passes,
                     kernel_depth_k=k)
        if u_row is None:
            row["utilisation_evidence"] = (
                "REFUSED: no dispatch_tree campaign row at %s compute units, and "
                "borrowing a row measured at another width would be exactly the "
                "extrapolation this audit exists to remove" % n)
        else:
            row["utilisation_evidence"] = {
                "compute_units_measured_at": n,
                "passes_per_descriptor": args.headline_passes,
                "refill_skew": 0,
                "occupancy_utilisation": u_row["occupancy_utilisation"],
                "mac_active_utilisation": u_row["mac_active_utilisation"],
            }
            for basis, u in (("occupancy", u_row["occupancy_utilisation"]),
                             ("mac_active", u_row["mac_active_utilisation"])):
                ops = cap["peak_bf16_ops_s"] * u
                row["sustained"][basis] = {
                    "sustained_bf16_ops_s": ops,
                    "ops_s_per_mm2": ops / area_mm2,
                    "ratio_vs_a100_device":
                        (ops / area_mm2) / a100["device_level_ops_s_per_mm2"],
                }
        dev.append(row)

    #: ---- re-run the fan-out audit, at one pass and at the headline ---------
    #: The nine verdicts are the reviewer's question, and they are a function of
    #: passes-per-descriptor alone -- the knob is independent of the distributor.
    fanout = {}
    for passes in sorted({1, args.headline_passes}):
        out = ROOT / "results/derived" / f".cpt_p{passes}.json"
        proc = subprocess.run(
            ["python3", str(ROOT / "tools/audit_control_path_throughput.py"),
             "--kernel-depth", str(k), "--passes-per-descriptor", str(passes),
             "--output", str(out)],
            cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            fanout[f"passes_{passes}"] = {"error": proc.stderr[-2000:]}
            continue
        sub = json.loads(out.read_text())
        out.unlink()
        fanout[f"passes_{passes}"] = {
            "invocation": ("tools/audit_control_path_throughput.py "
                           f"--kernel-depth {k} --passes-per-descriptor {passes}"),
            "busy_cycles_per_descriptor":
                sub["datapath"]["busy_cycles_per_descriptor"],
            "control_interval_datapath_cycles":
                sub["control"]["interval_in_datapath_cycles"],
            "capabilities_total": len(sub["accelerators"]),
            "verdict_ok": sum(1 for r in sub["accelerators"]
                              if r["sufficient_with_fanout"]),
            "verdict_short": sum(1 for r in sub["accelerators"]
                                 if not r["sufficient_with_fanout"]),
            "fanout_routed": sum(1 for r in sub["accelerators"]
                                 if r["fanout_routed"]),
            "widest_closed_fanout":
                sub["fanout_implementation"]["widest_closed_fanout"],
            "rows": [{
                "capability": r["capability"],
                "compute_units": r["compute_units"],
                "required_fanout_rate_factor": r["required_fanout"],
                "fanout_width_required": r["fanout_width_required"],
                "sufficient_with_fanout": r["sufficient_with_fanout"],
                "verdict": "OK" if r["sufficient_with_fanout"] else "SHORT",
                "fanout_routed": r["fanout_routed"],
                "fanout_routed_structures": r["fanout_routed_structures"],
                "analytic_utilisation_with_fanout": r["utilisation_with_fanout"],
                "utilisation_is_conditional_on_unbuilt_fanout":
                    r["utilisation_is_conditional_on_unbuilt_fanout"],
            } for r in sub["accelerators"]],
        }
    fanout["reading"] = (
        "at one K=%d pass per descriptor all nine capabilities are SHORT: one "
        "descriptor covers %s datapath cycles against a %d-cycle control "
        "interval. At %d passes all nine are OK and all nine have a CLOSED "
        "post-route fan-out record at their width, so no verdict is conditional "
        "on unbuilt hardware any more. The knob that flips them is descriptor "
        "coarseness, not the distributor: the distributor supplies the WIDTH, "
        "and without it every OK verdict would be conditional."
        % (k, fanout["passes_1"]["busy_cycles_per_descriptor"],
           round(fanout["passes_1"]["control_interval_datapath_cycles"]),
           args.headline_passes))

    #: ---- the refill regimes, needed by the headline's skew-2 rescale -------
    refill_regimes = refill_regime_comparison(
        args.kernel_depth, args.headline_passes
    )

    #: ---- what the figure was before the tree, computed not asserted --------
    before_rows = []
    for r in fanout["passes_1"]["rows"]:
        cap = next((c for c in L3["per_capability"]
                    if c["capability"] == r["capability"]), None)
        if cap is None:
            continue
        rf = r["required_fanout_rate_factor"]
        before_rows.append({
            "capability": r["capability"],
            "compute_units": r["compute_units"],
            "required_fanout_rate_factor": rf,
            "utilisation_without_fanout": 1.0 / rf,
            "recorded_peak_device_ratio_vs_a100": cap["ratio"],
            "sustained_device_ratio_without_fanout": cap["ratio"] / rf,
            "sustained_device_ratio_now_at_%d_passes" % args.headline_passes: (
                next((d["sustained"]["occupancy"]["ratio_vs_a100_device"]
                      for d in dev
                      if d["capability"] == r["capability"] and d["sustained"]),
                     None)),
        })

    #: ---- headline ----------------------------------------------------------
    hw = next(w for w in widths
              if w["compute_units"] == args.headline_width
              and w["distributor"]["closed"])
    hrow = next(r for r in hw["sustained"]
                if r["utilisation_structure"] == "tree" and r["refill_skew"] == 0
                and r["passes_per_descriptor"] == args.headline_passes)
    headline = {
        "sustained_array_level_ratio_vs_a100_logic_occupancy":
            hrow["sustained_occupancy"]["ratio_vs_a100_logic"],
        "sustained_array_level_ratio_vs_a100_logic_mac_active":
            hrow["sustained_mac_active"]["ratio_vs_a100_logic"],
        "compute_units": args.headline_width,
        "passes_per_descriptor": args.headline_passes,
        "refill_skew": 0,
        "binding_term": hw["frequency"]["binding_term"],
        "binding_frequency_hz": hw["frequency"]["binding_hz"],
        "distributor_no_longer_binds": hw["frequency"]["binding_term"] == "compute_unit",
        "peak_array_level_ratio_vs_a100_logic": hw["peak_ratio_vs_a100_logic"],
        "what_the_tree_fixed": ("the FREQUENCY term and the existence of a routed "
                               "record at width. NOT the utilisation term."),
        "new_binding_constraint": "operand delivery",
    }
    #: The headline number above assumes SKEW=0, which is a perfect operand
    #: supply. That assumption is the whole remaining result, so it belongs in the
    #: headline rather than under it.
    srow = next(r for r in hw["sustained"]
                if r["utilisation_structure"] == "tree" and r["refill_skew"] == 2
                and r["passes_per_descriptor"] == args.headline_passes)
    headline["skew0_is_an_assumption_about_operand_supply"] = {
        "skew0_meaning": SKEW_MEANING[0],
        "skew2_meaning": SKEW_MEANING[2],
        "ratio_at_skew2_occupancy":
            srow["sustained_occupancy"]["ratio_vs_a100_logic"],
        "ratio_at_skew2_mac_active":
            srow["sustained_mac_active"]["ratio_vs_a100_logic"],
        "reading": ("the headline holds only while every unit is fed every cycle. "
                    "With one unit in sixteen at a 50%% refill duty the same array "
                    "at the same width and the same descriptor coarseness falls "
                    "to %.3fx on occupancy and %.3fx on MAC-active work -- at or "
                    "barely above parity with the A100. The band between those "
                    "two numbers is the size of the operand-delivery problem, and "
                    "it is not closed by anything in the control path."
                    % (srow["sustained_occupancy"]["ratio_vs_a100_logic"],
                       srow["sustained_mac_active"]["ratio_vs_a100_logic"])),
        #: AND THE OPERAND PATH DOES CLOSE MOST OF IT, which the sentence above
        #: does not say because it was written before the mitigations were
        #: measured. The skew-2 rows are LOCKSTEP; scaling them by the best
        #: regime's work per unit area at the same skew, width, K and passes is
        #: the same array with a refill regime that exists and is placed.
        "skew2_with_the_best_measured_refill_regime": _skew2_best(
            refill_regimes, srow),
    }

    body = {
        "schema": "opentallas.derived.sustained_array_iso_area.v1",
        "unit": ("the array-level SUSTAINED throughput measurement after the "
                 "dispatch-tree fix"),
        "question": ("what is the SUSTAINED array-level iso-area throughput "
                     "against the A100 when the utilisation term comes from a "
                     "width-resolved measurement on real compute units instead "
                     "of a one-unit figure multiplied onto a wide array?"),
        "git": git_state(inputs),
        "comparator": a100,
        "compute_unit": unit,
        "utilisation_measurement": cmeta,
        "utilisation_rows": crows,
        "widths": widths,
        "tree_vs_flat_cycle_parity": {
            "claim": ("the tree did NOT improve utilisation. At matched width, "
                      "skew and passes-per-descriptor the two structures are "
                      "within a small fraction of a point, so the tree's "
                      "advantage is PHYSICAL -- it has a routed closed record at "
                      "512 and 1,088 units where the flat dispatcher has one only "
                      "at 16 -- and not cycle-level."),
            "max_absolute_difference_pp": max(abs(p["difference_pp"])
                                              for p in parity) if parity else None,
            "rows": parity,
        },
        "width_invariance_at_headline_point": {
            "structure": "tree", "refill_skew": 0,
            "passes_per_descriptor": args.headline_passes,
            "kernel_depth_k": k,
            "widths_measured": [r["compute_units"] for r in inv],
            "occupancy_utilisation": occ,
            "occupancy_span_pp": (max(occ) - min(occ)) * 100 if occ else None,
            "mac_active_utilisation": macs,
            "mac_active_span_pp": (max(macs) - min(macs)) * 100 if macs else None,
        },
        "device_level": {
            "comparator_level": "a100_device_level",
            "what_is_in": L3["what_is_in"],
            "what_is_out": L3["what_is_out"],
            "closure_note": L3["closure_note"],
            "per_capability": dev,
        },
        "level_naming_guard": {
            "warning": ("'array level' means something DIFFERENT in "
                        "tools/audit_abi3_iso_area_three_level.py and must not be "
                        "compared digit-for-digit with the figures here."),
            "three_level_audit_L1_array_level": {
                "what_it_is": next(L["what_is_in"] for L in three["levels"]
                                   if L["level"].startswith("L1")),
                "what_is_out": next(L["what_is_out"] for L in three["levels"]
                                    if L["level"].startswith("L1")),
                "peak_ratio_vs_a100_logic":
                    next(L["ratio"] for L in three["levels"]
                         if L["level"].startswith("L1")),
                "evidence_class": next(L["evidence_class"] for L in three["levels"]
                                       if L["level"].startswith("L1")),
            },
            "this_audit_array_level": {
                "what_it_is": ("N ot_compute_unit instances plus the descriptor "
                               "distributor that reaches all of them"),
                "peak_ratio_vs_a100_logic": widths[1]["peak_ratio_vs_a100_logic"],
                "evidence_class": "ROUTED AND CLOSED on both blocks",
            },
            "why_they_differ": ("the three-level audit's L1 is ot_mac_tile with "
                                "NO operand storage, which is why it reaches "
                                "4.6x; this audit's denominator is the same "
                                "arithmetic plus the two weight SRAM macros, the "
                                "activation register file and the K-walking "
                                "sequencer that keep it fed, plus the "
                                "distributor. The drop from 4.6x to 2.1x is the "
                                "cost of INCLUSION, not a regression, and it is "
                                "the same drop the three-level audit records "
                                "between its L1 and its L2."),
            "closest_comparable_is_L2": {
                "L2_peak_ratio_vs_a100_logic":
                    next(L["ratio"] for L in three["levels"]
                         if L["level"].startswith("L2")),
                "note": ("this audit's array-level peak differs from L2 only by "
                         "the distributor's share of the denominator, which is "
                         "under 0.17% at every width reported."),
            },
        },
        "before_and_after_the_dispatch_tree": {
            "what_the_old_sustained_figure_was": (
                "the utilisation term was a ONE-UNIT starvation measurement, and "
                "the fan-out that would license applying it to a wide array did "
                "not exist. Without fan-out a single global sequencer serves the "
                "array round-robin, so a unit's duty cycle is 1/required_fanout."),
            "basis": ("the rate factor is read from the ONE-PASS re-run of "
                      "tools/audit_control_path_throughput.py in "
                      "control_path_fanout_verdicts.passes_1, which is the "
                      "descriptor coarseness the old figure assumed."),
            "rows": before_rows,
            "what_changed": ("the distributor now exists as a CLOSED post-route "
                             "record at 512 and 1,088 units, so the 1/required_"
                             "fanout de-rating is gone and the utilisation term "
                             "is a direct measurement at the array's own width. "
                             "The frequency term improved with it. The "
                             "utilisation term at a GIVEN descriptor coarseness "
                             "did not change at all -- see "
                             "tree_vs_flat_cycle_parity."),
        },
        "borrowed_figure_verification": verify_borrowed(a100, three, L3),
        "control_path_fanout_verdicts": fanout,
        #: Which refill regime retires the most work per unit area, at each
        #: measured straggler level. The headline below is a LOCKSTEP figure; this
        #: is what the same array does with the mitigations that exist.
        "refill_regime_comparison": refill_regimes,
        "binding_constraint": {
            "verdict": "operand delivery",
            "why": ("passes-per-descriptor and descriptor fan-out are both now "
                    "sufficient: at three K=256 passes the control interval is "
                    "covered and all nine capabilities' fan-out verdicts clear. "
                    "What does NOT clear is the refill regime. At SKEW=2 -- one "
                    "unit in sixteen at a 50% refill duty -- utilisation collapses "
                    "and stays collapsed at every passes-per-descriptor and every "
                    "width, because coarsening a descriptor cannot manufacture an "
                    "operand that has not arrived."),
            "skew_sensitivity_at_headline_passes": [
                {"refill_skew": s,
                 "meaning": SKEW_MEANING[s],
                 "occupancy_utilisation": r["occupancy_utilisation"],
                 "mac_active_utilisation": r["mac_active_utilisation"]}
                for s in (0, 1, 2)
                for r in [pick(crows, structure="tree", compute_units=512,
                               refill_skew=s,
                               passes_per_descriptor=args.headline_passes,
                               kernel_depth_k=k)]
                if r
            ],
            "passes_do_not_rescue_skew": [
                {"passes_per_descriptor": p,
                 "occupancy_utilisation": r["occupancy_utilisation"],
                 "mac_active_utilisation": r["mac_active_utilisation"]}
                for p in (1, 2, 3, 4, 8)
                for r in [pick(crows, structure="tree", compute_units=512,
                               refill_skew=2, passes_per_descriptor=p,
                               kernel_depth_k=k)]
                if r
            ],
            "corroborating_energy_attribution": {
                "source": str(THREE_LEVEL.relative_to(ROOT)),
                "area": three["attribution"]["area_by_tile_subtraction"],
                "power_by_lane_probe_subtraction":
                    three["attribution"]["power_by_lane_probe_subtraction"],
                "power_by_tile_subtraction":
                    three["attribution"]["power_by_tile_subtraction"],
                "reading": ("inside one routed compute unit, operand delivery is "
                            "59.6% of the occupied AREA and 75.0-76.3% of the "
                            "POWER, arithmetic the remaining ~25%. The same term "
                            "is now what bounds throughput under SKEW. Area, "
                            "energy and now sustained throughput all point at the "
                            "same block, which is the most useful thing this "
                            "audit reports."),
            },
        },
        "headline": headline,
        "refusals": [
            "not-a-silicon-claim: ASAP7 is a predictive, non-manufacturable PDK. "
            "Every frequency and area here comes from it, and the A100 "
            "comparator is TSMC N7 silicon, so this is a predictive-PDK design "
            "against a shipped part.",
            "peak-is-arithmetic-only: the numerator is lanes x 2 x clock x "
            "utilisation. It charges no weight traffic beyond what the weight "
            "SRAM macros in the denominator supply, no attention over a KV cache "
            "and no interconnect. A real decode step at batch 1 is usually "
            "memory-bound, so this is an upper bound on sustained throughput.",
            "utilisation-is-a-kernel-figure-not-a-workload: the campaign drives "
            "an output-stationary GEMM where every unit walks the same K and "
            "differs only by sub-range index, from a PERIODIC descriptor source. "
            "A real sequencer's stream is bursty and interleaved with vector, "
            "attention and reduction commands, and an unequal extent split is out "
            "of scope for this distributor. This is not a token-generation "
            "measurement and must not be quoted as one.",
            "occupancy-is-not-work: the campaign's array_utilisation_percent "
            "counts a unit as busy while it stalls on an unbacked refill, which "
            "is what the testbench header says it does. mac_active_utilisation is "
            "derived from completed passes instead and is 5.2% lower at SKEW=0 "
            "and 10-12% lower under SKEW. Both are reported; neither is "
            "collapsed, and the flat rows have no work-based figure at all "
            "because that harness does not instrument unit_completions.",
            "area-is-a-sum-of-blocks-not-a-floorplan: the denominator adds "
            "separately placed cores. No record routes N compute units around a "
            "distributor, so the wire from a leaf to its unit carries no delay "
            "and no area here. That omission flatters both the frequency and the "
            "area term, and closing it needs an array-level route that does not "
            "exist.",
            "microsequencer-area-not-charged-at-array-level: the control plane's "
            "136,926 um2 core is excluded from the array denominator while its "
            "issue RATE is charged through the 567-cycle interval. The "
            "device-level leg charges both. Quote the array figure only against "
            "the A100's logic area, never its die.",
            "control-interval-comes-from-a-NOT-CLOSED-sequencer-record: the 567 "
            "cycles derive from ot_a3_microsequencer at 264.8 MHz "
            "(results/physical_abi3/asap7/a3_microsequencer/pnr.json, 416,715 "
            "cells, closed FALSE -- 3,204 max-slew and 3 max-cap violations). "
            "The CLOSED full-hierarchy record is 317.1 MHz at 430,151 cells "
            "(pnr_3p4ns_full_hierarchy_closed.json, zero SI violations, "
            "target_headroom 0.073), which would shorten the interval to ~473 "
            "cycles and RAISE utilisation. Using the slower record is the "
            "conservative choice and it is not re-measured here, because the "
            "campaign was run at 567.",
            "one-workload-behind-the-interval: 116.4 control cycles per engine "
            "command is G1e's measurement of the SHIPPED Qwen3 program. A "
            "different lowering or a different model issues commands at a "
            "different rate and would move the interval and therefore the "
            "utilisation.",
            "closed-vs-post-route-clean-at-1088: the 1,088-unit tree has a CLOSED "
            "record at 1,323.0 MHz whose target_headroom is 0.370, above the 0.35 "
            "line at which an fmax describes the target rather than the design; "
            "and a 1,475.4 MHz record at a 0.8 ns target that is post-route clean "
            "and MET (setup WNS +0.122 ns, zero violating paths, zero DRC, zero "
            "antenna, zero max-slew/cap/fanout) but is marked not_met because the "
            "PRE-LAYOUT ideal-clock STA leg missed by 62 ps on 9 paths. Both are "
            "reported. The conclusion does not turn on the choice: either figure "
            "is above the compute unit's 1,289.7 MHz, so the compute unit binds.",
            "no-distributor-record-at-32-units: rom_qwen3 declares 512 tensor "
            "lanes, i.e. 32 compute units, and no distributor has been elaborated "
            "at 32. Charging the 512-wide tree's area would overcharge it and "
            "charging its timing would credit a different elaboration, so the "
            "array-level row for 32 units is REFUSED rather than interpolated. "
            "The device-level leg still reports it, from the recorded chip.",
            "sixteen-unit-row-is-structure-mismatched: at 16 units the charged "
            "distributor is the routed closed FLAT ot_cluster_dispatcher, so the "
            "flat utilisation rows are the structure-matched ones and the tree "
            "rows at 16 are reported for comparison only. "
            "structure_matches_charged_distributor says which is which.",
            "device-level-instantiates-one-not-closed-block: the device rows "
            "carry the full 12-module microsequencer, which is routed but NOT "
            "closed. That is the recorded chip's own caveat and it is repeated "
            "here rather than quietly swapped for the closed frontend-only "
            "subset, which omits five modules and would understate the area.",
            "a100-logic-fraction-is-assumed: gpu_logic_area_fraction 0.6 carries "
            "grade 'assumed' in configs/hardware/technology.json. The die area "
            "and the BF16 rate are published. A different logic fraction moves "
            "every logic-level ratio here proportionally.",
            "one-input-is-untracked: results/derived/"
            "abi3_iso_area_three_level_audit.json, the source of the L3 chip "
            "areas, the L1/L2 peak ratios and the energy attribution quoted here, "
            "is on disk and in NO commit. Every figure taken from it is "
            "re-derived from the primary place-and-route records in "
            "borrowed_figure_verification and all 14 checks agree exactly, so "
            "nothing here depends on an uncommitted number -- but the file itself "
            "is not reproducible from this commit and a reader cannot check it "
            "out. The comparator is read directly from the tracked "
            "configs/hardware/technology*.json and is not borrowed.",
            "we-charge-ourselves-for-SRAM-the-comparator-does-not: the array "
            "denominator includes each unit's two weight SRAM macros, while the "
            "A100 logic-area denominator is a fraction of die intended as logic. "
            "That asymmetry makes the logic-level ratio CONSERVATIVE on this "
            "axis.",
        ],
    }

    #: ---- terminal report ---------------------------------------------------
    print(f"A100 comparator: {a100['bf16_dense_ops_s']/1e12:.0f} TFLOP/s BF16 "
          f"dense over {a100['logic_area_mm2']:.1f} mm2 logic "
          f"({a100['logic_level_ops_s_per_mm2']/1e9:.1f} Gops/s/mm2) "
          f"and {a100['die_area_mm2']:.0f} mm2 die "
          f"({a100['device_level_ops_s_per_mm2']/1e9:.1f} Gops/s/mm2)")
    print(f"compute unit: {f_unit/1e6:.1f} MHz, {unit['standard_cell_count']} "
          f"cells, {unit_area} um2 core ({unit['macro_count']} macros, "
          f"{unit['macro_area_um2']} um2), headroom "
          f"{unit['target_headroom']:.3f}, {unit['evidence_class']}\n")

    print("ARRAY LEVEL -- units + distributor, against the A100's logic area")
    for w in widths:
        d = w["distributor"]
        fr = w["frequency"]
        print(f"\n  {w['compute_units']} units + {d['block']} "
              f"({d['structure']}, {d['parameters']})")
        print(f"    distributor {fr['distributor_hz']/1e6:.1f} MHz, "
              f"{d['standard_cell_count']} cells, headroom "
              f"{d['target_headroom']:.3f}"
              f"{'  <-- LOOSE TARGET' if d['target_headroom_suspect'] else ''}, "
              f"{d['evidence_class']}")
        if d["closure_verdict_is_a_flow_artifact"]:
            print(f"      closed=False is a FLOW ARTIFACT: post-route MET "
                  f"(+{d['setup_wns_ns']:.3f} ns, clean), pre-layout STA missed "
                  f"{d['pre_layout_setup_wns_ns']*1000:.0f} ps on "
                  f"{d['pre_layout_setup_violating_paths']} paths")
        print(f"    BINDS: {fr['binding_term']} at {fr['binding_hz']/1e6:.1f} MHz")
        ad = w["area_denominator"]
        print(f"    area {ad['total_mm2']:.4f} mm2 = {w['compute_units']} x "
              f"{ad['compute_units_core_area_um2_each']} um2 + "
              f"{ad['distributor_core_area_um2']} um2 distributor "
              f"({ad['distributor_share_of_array_area']*100:.4f}% of it)")
        print(f"    PEAK {w['peak_bf16_ops_s_at_binding_clock']/1e12:.2f} TFLOP/s "
              f"-> {w['peak_ops_s_per_mm2']/1e9:.1f} Gops/s/mm2 "
              f"= {w['peak_ratio_vs_a100_logic']:.3f}x A100 logic")
        print(f"      {'struct':<7}{'skew':>5}{'p':>3} {'occup':>7} {'ratio':>7} "
              f"{'macact':>8} {'ratio':>7}  match")
        for r in w["sustained"]:
            if r["passes_per_descriptor"] not in (1, 3):
                continue
            so = r["sustained_occupancy"]
            sm = r["sustained_mac_active"]
            mu = (f"{r['mac_active_utilisation']*100:>7.2f}%"
                  if r["mac_active_utilisation"] else f"{'refused':>8}")
            mr = (f"{sm['ratio_vs_a100_logic']:>6.3f}x" if sm
                  else f"{'-':>7}")
            print(f"      {r['utilisation_structure']:<7}{r['refill_skew']:>5}"
                  f"{r['passes_per_descriptor']:>3} "
                  f"{r['occupancy_utilisation']*100:>6.2f}% "
                  f"{so['ratio_vs_a100_logic']:>6.3f}x "
                  f"{mu} {mr}  "
                  f"{'yes' if r['structure_matches_charged_distributor'] else 'NO'}")

    wi = body["width_invariance_at_headline_point"]
    print(f"\nWIDTH INVARIANCE (tree, skew 0, {args.headline_passes} passes, "
          f"K={k}): widths {wi['widths_measured']}")
    print(f"  occupancy {[round(x*100,2) for x in wi['occupancy_utilisation']]} "
          f"-> span {wi['occupancy_span_pp']:.3f} pp")
    print(f"  mac-active {[round(x*100,2) for x in wi['mac_active_utilisation']]} "
          f"-> span {wi['mac_active_span_pp']:.3f} pp")

    tvf = body["tree_vs_flat_cycle_parity"]
    print(f"\nTREE vs FLAT cycle parity: max |difference| "
          f"{tvf['max_absolute_difference_pp']:.3f} pp over {len(tvf['rows'])} "
          f"matched points. The tree did NOT improve utilisation.")

    bv = body["borrowed_figure_verification"]
    print(f"\nBORROWED-FIGURE VERIFICATION (the three-level audit JSON is "
          f"UNTRACKED): all_agree={bv['all_agree']}")
    for c in bv["scalar_checks"]:
        print(f"  {'OK ' if c['agrees'] else 'DIVERGES'} {c['figure']}: "
              f"re-derived {c['re_derived']:.9g} vs file "
              f"{c['value_in_untracked_file']:.9g}")
    bad = [d for d in bv["device_level_checks"]
           if d["re_derivable"] and not (d["area_agrees"] and d["ratio_agrees"])]
    print(f"  device-level: "
          f"{sum(1 for d in bv['device_level_checks'] if d['re_derivable'])}"
          f"/{len(bv['device_level_checks'])} re-derivable, "
          f"{len(bad)} diverging")

    print("\nFAN-OUT AUDIT RE-RUN (tools/audit_control_path_throughput.py)")
    for key in sorted(k2 for k2 in fanout if k2.startswith("passes_")):
        f = fanout[key]
        print(f"  {key.replace('passes_','')} pass(es)/descriptor: descriptor "
              f"covers {f['busy_cycles_per_descriptor']} cycles vs a "
              f"{f['control_interval_datapath_cycles']:.0f}-cycle interval -> "
              f"{f['verdict_ok']} OK / {f['verdict_short']} SHORT of "
              f"{f['capabilities_total']}, fan-out ROUTED for "
              f"{f['fanout_routed']}/{f['capabilities_total']} "
              f"(widest closed {f['widest_closed_fanout']})")

    bc = body["binding_constraint"]
    print(f"\nBINDING CONSTRAINT: {bc['verdict']}")
    for s in bc["skew_sensitivity_at_headline_passes"]:
        print(f"  skew {s['refill_skew']} ({s['meaning'][:52]}): occupancy "
              f"{s['occupancy_utilisation']*100:.2f}%  mac-active "
              f"{s['mac_active_utilisation']*100:.2f}%")
    print("  and coarsening the descriptor does not rescue it:")
    for s in bc["passes_do_not_rescue_skew"]:
        print(f"    skew 2, {s['passes_per_descriptor']} passes: occupancy "
              f"{s['occupancy_utilisation']*100:.2f}%  mac-active "
              f"{s['mac_active_utilisation']*100:.2f}%")

    rr = body["refill_regime_comparison"]
    print(f"\nREFILL REGIME, work per unit area at {rr['width']} units, "
          f"K={rr['kernel_depth_k']}, {rr['passes_per_descriptor']} passes")
    print("  every row retires the same completions, so only the cycles differ")
    print(f"  {'skew':>4} {'regime':<24}{'cycles':>8}{'mac%':>8}{'x area':>8}"
          f"{'mac/area':>10}")
    for row in rr["rows"]:
        if "refused" in row:
            print(f"  {'':>4} {row['regime']:<24}  REFUSED: {row['refused']}")
            continue
        print(f"  {row['refill_skew']:>4} {row['regime']:<24}"
              f"{row['elapsed_cycles']:>8}"
              f"{row['mac_active_utilisation']*100:>8.2f}"
              f"{row['area_multiplier_vs_lockstep']:>8.4f}"
              f"{row['mac_active_per_unit_area']*100:>10.2f}")
    for skew, best in rr["best_per_skew"].items():
        print(f"  best at skew {skew}: {best['regime']} "
              f"(WGT_BANKS={best['weight_banks']}) at "
              f"{best['mac_active_per_unit_area']*100:.2f}% work per unit area")
    print("  THE WINNER CHANGES WITH THE STRAGGLER MODEL, so no single operating "
          "point is recommended here.")

    print("\nDEVICE LEVEL -- whole recorded chip, against the A100's 826 mm2 die")
    print(f"  {'capability':<38}{'units':>6}{'area mm2':>10}{'peak x':>8}"
          f"{'occ x':>8}{'mac x':>8}")
    for r in dev:
        if not r["sustained"]:
            print(f"  {r['capability']:<38}{str(r['tensor_compute_units']):>6}"
                  f"{r['chip_area_mm2_used']:>10.4f}"
                  f"{r['peak_ratio_vs_a100_device']:>7.3f}x    REFUSED (no "
                  f"campaign row at this width)")
            continue
        print(f"  {r['capability']:<38}{r['tensor_compute_units']:>6}"
              f"{r['chip_area_mm2_used']:>10.4f}"
              f"{r['peak_ratio_vs_a100_device']:>7.3f}x"
              f"{r['sustained']['occupancy']['ratio_vs_a100_device']:>7.3f}x"
              f"{r['sustained']['mac_active']['ratio_vs_a100_device']:>7.3f}x")

    h = headline
    print(f"\nHEADLINE: sustained ARRAY-LEVEL "
          f"{h['sustained_array_level_ratio_vs_a100_logic_occupancy']:.3f}x the "
          f"A100's standard-cell-logic density on occupancy, "
          f"{h['sustained_array_level_ratio_vs_a100_logic_mac_active']:.3f}x on "
          f"MAC-active work,")
    print(f"  at {h['compute_units']} compute units, "
          f"{h['passes_per_descriptor']} K={k} passes per descriptor, refill "
          f"skew 0, binding term {h['binding_term']} at "
          f"{h['binding_frequency_hz']/1e6:.1f} MHz.")
    print(f"  Peak at the same width and denominator is "
          f"{h['peak_array_level_ratio_vs_a100_logic']:.3f}x. The tree fixed the "
          f"frequency term, not the utilisation term.")
    sk = h["skew0_is_an_assumption_about_operand_supply"]
    print(f"  That holds at SKEW=0 (every unit fed every cycle). At SKEW=2 "
          f"(one unit in sixteen at 50% refill duty) the same array falls to "
          f"{sk['ratio_at_skew2_occupancy']:.3f}x / "
          f"{sk['ratio_at_skew2_mac_active']:.3f}x.")
    rescue = sk.get("skew2_with_the_best_measured_refill_regime", {})
    if "refused" in rescue:
        print(f"  Skew-2 rescale REFUSED: {rescue['refused']}")
    else:
        print(f"  BUT THE SKEW-2 ROW IS LOCKSTEP. With {rescue['regime']} "
              f"(WGT_BANKS={rescue['weight_banks']}), which is measured and "
              f"placed, the same skew-2 array reaches "
              f"{rescue['rescaled_ratio_at_skew2_occupancy']:.3f}x / "
              f"{rescue['rescaled_ratio_at_skew2_mac_active']:.3f}x --")
        print(f"    a {rescue['work_per_area_gain_vs_lockstep_at_skew2']:.3f}x "
              f"gain in work per unit area, with that regime's own area charged. "
              f"DERIVED, not re-measured: {rescue['derived_not_measured']}.")
    print(f"  New binding constraint: {h['new_binding_constraint']}.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    try:
        shown = args.output.relative_to(ROOT)
    except ValueError:
        shown = args.output
    print(f"\nwrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
