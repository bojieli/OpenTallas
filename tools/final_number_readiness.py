#!/usr/bin/env python3
"""Cross-check independent records before promoting a four-target rate claim.

The report is expected to contain blocked gates during development.  ``--check``
requires the committed report to reflect current sources; ``--require-final``
additionally refuses publication while any terminal gate is blocked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/final_number_readiness.json"


def read(path: str, used: dict[str, str]) -> dict:
    p = ROOT / path
    if not p.is_file():
        used[path] = "missing"
        return {}
    used[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text())


def gate(ok: bool, observed: object, required: str, evidence: str) -> dict:
    return {"status": "pass" if ok else "blocked", "observed": observed,
            "required": required, "evidence": evidence}


def build() -> dict:
    used: dict[str, str] = {}
    golden_p = "results/rtl/hdc_v41x_fullshape_golden.json"
    layout_p = "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json"
    width_p = "results/rtl/hdc_v41x_fullshape_weight_rtl_preflight.json"
    rate_p = "results/arch/v41_tp_rowsplit_measured_reprice.json"
    load_p = "results/arch/v41_fullshape_load_floor.json"
    coll_p = "results/rtl/v41_collective_depth_campaign.json"
    index_p = "results/rtl/hdc_v41x_idx_shard_reader_pc.json"
    route_p = "results/physical_abi3/asap7/chip/v41x_hbm_karb/strip_pin_placement.json"
    die_route_p = "results/physical_abi3/asap7/chip/v41x_full_die/physical.json"
    v41_rtl_p = "results/rtl/hdc_v41x_fullshape_token_rtl.json"
    v41_hbm_p = "results/rtl/hdc_v41x_fullshape_hbm_matched.json"
    program_p = "results/rtl/hdc_v41x_fullshape_program_bind.json"
    qwen_p = "results/rtl/hdc_qwen_int8_tp2_ar.json"
    qwen_full_p = "results/rtl/qwen_o4_fullshape_tp2_ar.json"
    qwen_dflash_p = "results/rtl/qwen_o4_fullshape_tp2_dflash.json"
    qwen_hbm_p = "results/rtl/qwen_o4_fullshape_hbm_matched.json"
    g = read(golden_p, used)
    layout = read(layout_p, used)
    width = read(width_p, used)
    rate = read(rate_p, used)
    load = read(load_p, used)
    coll = read(coll_p, used)
    index = read(index_p, used)
    route = read(route_p, used)
    die_route = read(die_route_p, used)
    v41_rtl = read(v41_rtl_p, used)
    v41_hbm = read(v41_hbm_p, used)
    program = read(program_p, used)
    qwen = read(qwen_p, used)
    qwen_full = read(qwen_full_p, used)
    qwen_dflash = read(qwen_dflash_p, used)
    qwen_hbm = read(qwen_hbm_p, used)
    used["tools/final_number_readiness.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    contexts = g.get("contexts", {})
    golden_ok = g.get("status") == "golden_only" and all(
        contexts.get(str(c), {}).get("layer_count") == 40 for c in (200_000, 1_048_576))
    gaps = width.get("rtl_engine_preflight", {}).get("gaps", {})
    old = rate.get("points", {}).get("1048576", {}).get("ar", {})
    ld = load.get("points", {}).get("1048576", {}).get("gw1_depth128_exact_stage", {})
    tails = coll.get("summary", {})
    measured_index = index.get("timed_1040_key_scan", {}).get("sectors_per_cycle", 0)
    # The adopted 3.6 TB/s per die at 1.087 GHz is 103.5 32-byte sectors/cycle.
    effective_index_target = 3.6e12 / (1.087e9 * 32)
    model_ar = old.get("row_split_measured_gathers", 0)
    load_ar = ld.get("proposed_wo_load_ar_tok_s", 0)
    required = {
        "v41_reference_200k_1m": gate(golden_ok,
            {str(c): contexts.get(str(c), {}).get("layer_count") for c in (200_000, 1_048_576)},
            "40 source-pinned golden layers at both contexts (reference only)", golden_p),
        "v41_executable_weight_program": gate(
            bool(layout.get("token_runnable")) and not gaps and
            program.get("status") == "pass_exact_layout",
            {"token_runnable": layout.get("token_runnable"), "rtl_geometry_gaps": gaps,
             "program_binding": program.get("status", "missing")},
            "same full-shape ISA, packed images, ROM address units and RTL geometry; exact layer replay",
            f"{layout_p}; {width_p}; {program_p}"),
        "v41_rate_covers_activation_load": gate(
            bool(model_ar and load_ar and model_ar <= load_ar),
            {"gather_only_ar_tok_s": model_ar, "wo_a_load_floor_ar_tok_s": load_ar},
            "headline rate no greater than a source-pinned critical-path load floor, or widen and remeasure the load path",
            f"{rate_p}; {load_p}"),
        "v41_collective_model_binding": gate(
            bool(tails.get("act") and
                 rate.get("measured_tail_cycles", {}).get("act") == tails["act"].get("selected_tail_cycles") and
                 rate.get("measured_tail_cycles", {}).get("y") == tails.get("y", {}).get("selected_tail_cycles")),
            {"model_tails": rate.get("measured_tail_cycles"),
             "exact_stage_tails": {k: tails.get(k, {}).get("selected_tail_cycles") for k in ("act", "y")},
             "act_one_write_port_floor": tails.get("act", {}).get("output_port_minimum_cycles")},
            "model binds both exact adopted-width tails; any new bank/packing result must reprice from its own gate",
            f"{coll_p}; {rate_p}"),
        "v41_index_bandwidth": gate(measured_index >= effective_index_target,
            {"measured_sectors_per_cycle": measured_index,
             "effective_modeled_sectors_per_cycle": round(effective_index_target, 3)},
            "four-stack concurrent exact scan at or above the adopted effective HBM rate, with user isolation",
            index_p),
        "v41_hbm_pin_layout": gate(route.get("verdict") == "pin_placement_pass",
            {"pin_placement": route.get("verdict"), "route_completed": route.get("route_completed")},
            "all pseudo-channel pins placed in physical PHY windows; routing is a separate full-die gate", route_p),
        "v41_fullshape_rom_token": gate(v41_rtl.get("status") == "pass_exact_fullshape",
            v41_rtl.get("status", "missing"),
            "same checkpoint/ISA/image as golden, all 40 layers, exact terminal token/logits/KV/index and cycles",
            v41_rtl_p),
        "v41_fullshape_hbm_matched": gate(v41_hbm.get("status") == "pass_exact_matched_fullshape",
            v41_hbm.get("status", "missing"),
            "same full-shape program and images, all weight families sourced from shared HBM, both arms exact",
            v41_hbm_p),
        "v41_full_die_route": gate(die_route.get("flow_completed") is True and
            die_route.get("setup_hold_drc_power_fmax", {}).get("fmax_hz", 0) >= 1.087e9,
            {"flow_completed": die_route.get("flow_completed", False),
             "fmax_hz": die_route.get("setup_hold_drc_power_fmax", {}).get("fmax_hz")},
            "full adopted die detailed route with extracted setup/hold/DRC/power and >=1.087 GHz",
            die_route_p),
        "qwen_fullshape_rom": gate(qwen_full.get("status") == "pass_exact_fullshape" and
            qwen_dflash.get("status") == "pass_exact_fullshape",
            {"reduced_tp2": qwen.get("status"), "fullshape_ar": qwen_full.get("status", "missing"),
             "fullshape_dflash": qwen_dflash.get("status", "missing")},
            "real-checkpoint two-die INT8 full-shape bit-exact AR and DFlash token records", qwen_p),
        "qwen_fullshape_hbm": gate(qwen_hbm.get("status") == "pass_exact_matched_fullshape",
            qwen_hbm.get("status", "fullshape matched A/B and routed weight supply missing"),
            "same full-shape program/images, all weights in HBM, exact state, sustained controller and route",
            qwen_hbm_p),
    }
    return {"schema": "opentallas.final-number-readiness.v1", "source_sha256": used,
            "claim_boundary": "a passed reference or reduced gate does not imply chip throughput",
            "gates": required,
            "terminal_ready": all(x["status"] == "pass" for x in required.values())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--require-final", action="store_true")
    args = ap.parse_args()
    result = build()
    if args.check:
        if not OUT.is_file() or json.loads(OUT.read_text()) != result:
            print(f"stale final-number readiness report: regenerate {OUT}")
            return 2
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for name, item in result["gates"].items():
        print(f"{item['status']:7} {name}")
    return 1 if args.require_final and not result["terminal_ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
