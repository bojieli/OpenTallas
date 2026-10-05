#!/usr/bin/env python3
"""Additive source-selected STREAM4 landing closure price; no baseline mutation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import uarch_model as unified
import qwen_rom_kv_fullbw_model as service
ROOT = Path(__file__).resolve().parents[1]
OUT = "results/rtl/qwen_stream4_land_merge_20261005"


def model():
    old = json.loads((ROOT/OUT/"inputs/r3b/physical.json").read_text())
    cells = old["design"]["area_um2"]
    frame = old["place_and_route"]["metrics"]["core_area_um2"]
    n, dw, replicas = 12, 512, service.TILES
    # Conservative positive growth; no credit for moving/removing old logic.
    def price(bits, mux_bits, control_buffers, reset_bits=0):
        ff = bits * unified.DFF_UM2 + reset_bits*(0.37908-unified.DFF_UM2)
        inv = bits * 0.04374
        clock = math.ceil(bits/16)*0.10206
        fanout = control_buffers*0.10206
        hold = 2*(bits+256)*0.10206
        comb = mux_bits*0.2
        wires = .2*(ff+inv+comb)
        growth = ff+inv+clock+fanout+hold+comb+wires
        return dict(new_state_bits=bits, new_clock_pins=bits,
                    new_reset_pins=reset_bits,
                    new_clock_pin_cap_upper_proxy_fF=bits*1.0,
                    pin_cap_proxy_not_SS_characterization=True,
                    FF_master_body_um2=ff, restoring_INV_um2=inv,
                    local_clock_buffer_floor_um2=clock, fanout_reservation_um2=fanout,
                    hold_repair_reservation_um2=hold, gross_logic_reservation_um2=comb,
                    wire_locality_reservation_um2=wires,
                    old_cell_removal_credit_um2=0,
                    added_cell_bound_um2=growth,
                    complete_screen_cell_bound_um2=cells+growth,
                    complete_screen_replicated_mm2=(cells+growth)*replicas/1e6,
                    positive_growth_mm2_per_die=growth*replicas/1e6,
                    modeled_screen_density_fit=cells+growth <= frame*.6,
                    screen_is_not_production_parent_allocation=True)
    pre = price(n*256+n*(8-4), n*512, n*3*17)
    split = price(2*(2*dw)+7+1, 2*dw, 64, 1)
    sources = ["tools/uarch_model.py", "tools/qwen_rom_kv_fullbw_model.py",
       "tools/qwen_rom_fulldie.py", "rtl/hdc/kv/ot_qwen_kv_land_merge.sv",
       "rtl/hdc/kv/ot_qwen_kv_land_merge_screen.sv",
       "rtl/hdc/kv/ot_qwen_rt_kv_stream4_service.sv",
       "rtl/test/qwen_rom_runtime/realmem/tb_qwen_kv_land_merge.sv",
       "results/rtl/qwen_rom_kv_fullbw_20261004/standalone/ISO_P8191.log",
       "results/rtl/qwen_rom_kv_fullbw_20261004/standalone/CHAIN_P8191_base.log",
       "results/rtl/qwen_rom_kv_fullbw_20261004/standalone/CHAIN_P8191_early_posted.log",
       OUT+"/inputs/r3b/physical.json", OUT+"/inputs/r3b/6_finish.rpt"]
    return dict(schema="opentallas.qwen_stream4_land_merge_recipe.v1",
       selected="stage1_preplaced_data_and_quarter_mask_flags",
       model_precedes_RTL=True, baseline_original_unchanged=True,
       baseline=dict(cell_area_um2=cells, die_area_um2=40000, core_area_um2=frame,
                     screen_replicated_mm2=cells*replicas/1e6,
                     mapped_clock_sinks=old["place_and_route"]["metrics"]["sequential_cell_count"],
                     SS_setup_ps=-18.4986, FF_hold_ps=-5.28846,
                     setup_paths=15, hold_paths=256, DRC=0,
                     actual_route_terminal_rc=0, verdict="NOT_MET",
                     scope="registered-IO screen; outer IO and reset false-pathed in inherited fixture, not full tile signoff"),
       cone=dict(setup="u.sel_q[7] -> placement decode/buffers -> 12-source merge -> u.kvw_data[55]",
                 selector_clk_q_ps=132.69, selector_QN_load_fF=10.46,
                 hold="screen.beat_q[1734] -> INV -> merge.beat_q[1734]",
                 hold_data_arrival_ps=249.99, hold_required_ps=255.28,
                 hold_is_internal_register_to_register=True),
       alternatives=dict(preplaced=pre, extra_OR_stage=split),
       selection_reason="Remove the measured selector/placement cone from stage2 without changing grant or fill edges. Existing 200um screen fits conservative positive growth. Extra OR stage is cheaper state but leaves placement in stage2 and charges a real extra fill edge.",
       protocol=dict(NSRC=n, DW=dw, PW=7, LW=7, default_enabled=False,
                     grant_rule="exact original rotating-order E, pairwise location equality, earlier-valid quarter blocking; token wins",
                     grant_edge_change=0, write_edges_after_request=2,
                     arbitration_II_cycles=1, no_grant_enable_on_payload_registers=True,
                     local_mask_flags="4 full-quarter and 4 tail-quarter bits per source; one existing128-bit tail mask register",
                     tail_changes_only_at_layer_start=True, no_extra_FIFO_or_credit=True),
       ports=dict(source_payload_bits_per_cycle=n*256, source_selector_bits=2*n,
                  source_location_bits=7*n, source_port_bits=7*n,
                  source_control_bits=3*n, token_payload_and_mask_bits=1024,
                  slice_write_payload_bytes_per_cycle=64, slice_write_mask_bits=512,
                  slice_write_address_bits=7, slice_write_enable_bits=1,
                  grants_reverse_bits=n, MACs_per_cycle=0,
                  new_memory_ports=0, new_boundary_tracks=0,
                  internal_preplaced_data_wires=n*512,
                  internal_flag_wires=n*8, stage2_merge_fanin=n,
                  per_die_replicas=replicas,
                  actual_parent_cut_capacity=None),
       slot=dict(screen_die_um=[200,200], screen_core_um=[5,5,195,195],
                 screen_max_cells_um2=frame*.6,
                 current_die_tile_slot_um=[313.632,1291.68],
                 current_die_tile_body_width_um=313.632-52.704,
                 current_tile_total_cell_ceiling_um2=125000,
                 parent_landing_region_allocation=None,
                 full_tile_area_or_PDN_or_route_admitted=False,
                 once_only_area_rule="screen6915.13um2 is conservative once-only landing reservation; upstream wrapper reuse/removal gets no credit. Do not add it twice if parent already reserves landing."),
       latency=dict(existing_FILL_LAT=8, existing_service_kvw_edge=9,
                    existing_tile_SRAM_edge=10,
                    selected_added_network_cycles=0, selected_added_token_cycles=0,
                    selected_network_stage_replacement="same first two of existing FILL_LAT stages; parent physical installation still pending",
                    extra_OR_stage_FILL_LAT=9,
                    extra_OR_stage_service_kvw_edge=10,
                    extra_OR_stage_tile_SRAM_edge=11,
                    extra_OR_stage_added_cycles_per_fill=1,
                    extra_OR_stage_serial36_fill_bound_cycles=36,
                    extra_OR_stage_serial36_fill_bound_ns=36/1.2,
                    startup_or_repeated_fill_not_priced_zero=True,
                    observed_ISO_P8191_fill_cycles=1353,
                    observed_ISO_P8191_kv_ok_after_start=1803,
                    observed_CHAIN_B_fill_cycles=1312,
                    extra_stage_exposure_formula="max(0,1312+1-actual_MLP_overlap_cycles); no perfect-overlap assumption",
                    observed_early_posted_fixture_overlap_cycles=3000,
                    observed_short_overlap_cycles=400,
                    extra_stage_short_overlap_exposed_cycles=913,
                    full36_live_baseline_timing_transfer=False),
       physical=dict(period_ns=.833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                     repair_hold_margin_ps=20, repair_is_stricter_not_relaxed=True,
                     existing_max_transition_ns=.32, existing_slew_margin_percent=40,
                     measured_gain_or_closure=False, full_parent_context_admitted=False,
                     one_selected_screen_route_after_lockstep=True,
                     no_variant_sweep=True, no_DS_spine_or_live_baseline_changes=True,
                     prospective_timing_credit_ps=0,
                     reset_recovery_and_outer_IO_not_qualified_by_screen=True),
       sourcepins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path)
    a=p.parse_args()
    t=json.dumps(model(),indent=2,sort_keys=True)+"\n"
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(t)
    else: print(t,end="")

if __name__=="__main__": main()
