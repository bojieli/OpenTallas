#!/usr/bin/env python3
"""Model-only W18 baseline closure plan; never authorizes RTL or a physical job."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uarch_model as U

ROOT = Path(__file__).resolve().parents[1]


def plan():
    baseline = U.w10_baseline_model()
    composition = baseline['composition']['checked_in_lat8_audit']
    karb = U.cons_karb_delta(S=baseline['composition']['stage_count'], clock_hz=1.2e9)
    requests = karb['rows']['w18b_merge2_headreg_worst']['requests_on_path']
    # Actual interface declaration: TAGW=16, BEATW=4, DW=256; valid travels with payload.
    response_bits = 16 + 4 + 256 + 1
    # Physical baseline AW=30, LENW=4, TAGW=16, DW=256, NPC=32.
    dispatch_bits = 30 + 4 + 16 + 1 + 256 + 32 + 5 + 1
    rows = []
    for dispatch in (False, True):
        added = 1 + int(dispatch)
        delta_us = requests * added / 1.2e9 * 1e6
        token_us = composition['token_us'] + delta_us
        rows.append(dict(response_boundary_cycles=1, dispatch_pipeline_cycles=int(dispatch),
                         extra_cycles_per_critical_request=added, requests_on_token_path=requests,
                         incremental_token_us=delta_us, baseline_lat8_token_us=composition['token_us'],
                         conditional_token_us=token_us, conditional_ar_tokens_s=1e6/token_us,
                         rate_delta_pct=(composition['token_us']/token_us-1)*100,
                         region_roundtrip_cycles=[x+added for x in U.KARB_W18B_HEADREG]))
    registers = 32 * response_bits
    return dict(schema='opentallas.w18.baseline.boundary.plan.v1',
                verdict='MODEL_PLAN_ONLY_NOT_BUILD_QUALIFIED', adopted=False,
                scope='necessary baseline 1.2GHz closure; no DLV or KSREG reroute',
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                               ['tools/uarch_model.py','rtl/chip/ot_chip_v41x_karb_pregion.sv',
                                'rtl/chip/ot_chip_v41x_karb_proot.sv','tools/w18_baseline_boundary_plan.py']},
                timing=dict(period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                            reported_macro_clkq_ps=585, reported_postmacro_logic_ps=524,
                            report_source='parent steering; exact endpoint report must be pinned before build',
                            unsplit_data_ps=1109, ideal_budget_before_setup_skew_ps=773,
                            split_stage1_margin_before_setup_skew_wire_ps=188,
                            split_stage2_margin_before_clkq_setup_skew_ps=249,
                            interpretation='split is plausible only; these margins exclude register timing and new routed wire'),
                ports=dict(pseudochannels_per_die=32, regions_per_die=8,
                           response_bits_per_pc_per_cycle=response_bits, response_bytes_per_pc_per_cycle=32,
                           response_total_bits_per_cycle=registers, request_bits_per_cycle=dispatch_bits,
                           external_bandwidth_delta=0, compute_macs_per_cycle=0,
                           response_mux='capture at each real macro response edge before existing queue/select cone',
                           dispatch_mux='conditional registered selected-credit decision and matching payload; reserve credit atomically'),
                hardware=dict(response_register_bits_per_die=registers,
                              response_register_area_um2=registers*U.DFF_UM2,
                              response_placement_um2_at_50pct=registers*U.DFF_UM2/.5,
                              optional_dispatch_register_bits=dispatch_bits,
                              optional_dispatch_area_um2=dispatch_bits*U.DFF_UM2,
                              local_tracks_per_pc_lower_bound=response_bits,
                              track_capacity=None, slot_fit=None,
                              missing='actual macro edge slots, local routing capacity, buffer/hold/clock cost and power'),
                latency=rows,
                exact_contract=['carry valid/tag/beat/data together; unchanged per-tag ordering and golden arithmetic',
                                'reserve response capacity before accepting a beat; no lost credit under stalls',
                                'reset flushes new valid state; no phantom response or credit',
                                'dispatch credit decremented once at reservation, including same-cycle return',
                                'full legal shape baseline transaction equality; measure the priced added cycles'],
                gates=['pin actual 585ps/524ps endpoint evidence and actual macro corner abstract',
                       'derive full-goal routing capacity and macro edge slot fit before any RTL',
                       'W10 full-goal element structure and exactness first',
                       'off-by-default companion; exact reset/stall/drain/credit and negative gates',
                       'one qualified context at unchanged SS/FF, including boundary and recovery/removal',
                       'actual final q/column LEFs and ETMs before die rebase; actual-element IR'],
                other_designs={'qwen_rom':'unchanged','qwen_hbm':'unchanged','v41_hbm':'shared arbiter applicability requires its own token graph'})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    record = plan()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(record,indent=2)+'\n')
