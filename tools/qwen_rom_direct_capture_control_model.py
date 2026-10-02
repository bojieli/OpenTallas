#!/usr/bin/env python3
"""Source-pinned direct capture/local selector pricing; no RTL or tool launches."""
import argparse,gzip,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_rom_direct_capture_control_20261002'

def cell_area(name,lib):
    s=gzip.decompress((OUT/'inputs'/lib).read_bytes()).decode()
    m=re.search(r'cell\s*\(\s*'+re.escape(name)+r'\s*\)\s*\{.*?area\s*:\s*([\d.]+)',s,re.S)
    if not m:raise ValueError('cell absent '+name)
    return float(m[1])

def tree(sinks):
    # Fixed reference fanout8; buffers are prospective counts, not measured drive.
    n=0
    while sinks>1:
        sinks=math.ceil(sinks/8);n+=sinks
    return n

def build():
    h=json.loads((OUT/'inputs/euclid_handoff.json').read_text())
    p=json.loads((OUT/'inputs/proof.json').read_text())
    physical=json.loads((OUT/'inputs/physical_context.json').read_text())
    if p['status']!='PASS_SOURCE_TRANSITION_INDUCTION_NOT_RTL_QUALIFICATION':raise ValueError('proof not ready')
    if len(p['queries'])!=11 or any(q['result']!='unsat' for q in p['queries']):raise ValueError('positive query changed')
    if len(p['negative_controls'])!=2 or any(q['result']!='sat' for q in p['negative_controls']):raise ValueError('mutant control changed')
    if hashlib.sha256((OUT/'inputs/proof.json').read_bytes()).hexdigest()!=h['proof_sha256']:raise ValueError('proof pin changed')
    ff=cell_area('DFFHQNx1_ASAP7_75t_R','seq_ss.lib.gz')
    reset_ff=cell_area('DFFASRHQNx1_ASAP7_75t_R','seq_ss.lib.gz')
    buf=cell_area('BUFx4_ASAP7_75t_R','invbuf_ss.lib.gz')
    nand=cell_area('NAND2x1_ASAP7_75t_R','simple_ss.lib.gz')
    inv=cell_area('INVx1_ASAP7_75t_R','invbuf_ss.lib.gz')
    mask=cell_area('AND2x2_ASAP7_75t_R','simple_ss.lib.gz')
    merge=cell_area('OR2x2_ASAP7_75t_R','simple_ss.lib.gz')
    # Fixed ONE80-selector scenario from Euclid:16local32bit chunks/bank.
    # Original11 metadata FFs remain counted; additional75 have async reset.
    buffers=dict(mask_local_leaf_and_root=80*tree(32),early_selector=5*tree(16),
                 old_read_strobe_enable=tree(80),incremental_clock_reference=tree(75),
                 incremental_reset_reference=tree(75))
    full_cells=dict(capture_FF=2560*ff,selector_reset_FF=86*reset_ff,
        selector_hold_mux_reference=85*3*nand,mask_AND=2560*mask,
        OR_merge=2048*merge,retained_AW24_bank_CE_decode=60*mask+12*inv,
        shared_hold_control_inverters=2*inv,reference_buffers=sum(buffers.values())*buf)
    incremental=dict(selector_reset_FF=75*reset_ff,selector_hold_mux_reference=75*3*nand,
        reference_buffers=sum(buffers.values())*buf,shared_hold_control_inverters=2*inv)
    # Keep full old logic in ledger; no mapped feedback-mux removal credit.
    # Clear routing/PG/cell occupancy is policy, never asserted source availability.
    positive_route_clock_PG_allowance=.25*sum(incremental.values())
    inc_cell_and_corridor=sum(incremental.values())+positive_route_clock_PG_allowance
    inc_slot=inc_cell_and_corridor/.5
    return dict(schema='opentallas.qwen-rom.direct-capture-control.v1',
      source_commits=dict(proof='bf7efd5506e919a31aebcf091d1b7d6d38dbdffa',rejected_cone='f0d82bebdad800cee19b6bb790b505768beb08ca'),
      source_sha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((OUT/'inputs').iterdir())},
      generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      selected_model_scenario='5banks_2columns_directcapture_16local32bitmask_chunks_perbank',
      optin=dict(parameter='ROM_HOLD_DIRECT_CAPTURE',default=0,RTL_preparation_admitted=True,RTL_implemented=False,
                actual_variant_equivalence_and_four_state_gate_required_before_mapping=True),
      proof=dict(status=p['status'],positive_UNSAT_queries=11,SAT_mutants=2,
          scope=p['source_event_contract']['four_state_scope'],replicated_selector_equivalence_not_yet_proved=True),
      inventory=dict(ROM_macros=10,raw_ROM_bits=2660,consumed_bits=2560,selected_bits=512,
          capture_FF_bits=2560,capture_clock_pins_unchanged=2560,
          delayed_mask_FFs_before=5,after=80,added_FFs=75,total_metadata_FFs_before=11,after_total=86,
          feedback_data_mux_bits_removed=2560,selector_hold_mux_bits_before=10,after_mux=85,
          mask_AND_bits_retained=2560,OR_merge_bits_retained=2048,
          original_mask_loads_per_bank=512,new_mask_loads_per_leaf=32,
          early_selector_loads_per_bank=16,read_strobe_hold_enable_loads=80,
          added_clock_pins=75,added_reset_pins=75,buffer_reference_counts=buffers,
          fanout8_is_provisional_drive_policy=True,replica_preservation_must_be_checked_after_synthesis=True),
      area=dict(source_library_corner='RVT_SS',FF_um2=ff,async_reset_FF_reference_um2=reset_ff,BUF_reference_um2=buf,
          lower_bound_added75_plainFF_um2=75*ff,
          incremental_source_cell_reference_um2=incremental,
          full_retained_ROM_capture_control_logic_reference_um2=full_cells,
          full_reference_logic_not_entire_arithmetic_tile=True,
          mapped_data_mux_saving_credit_um2=0,
          positive_extra_route_clock_PG_policy_um2=positive_route_clock_PG_allowance,
          incremental_slot_policy_um2=inc_slot,slot_policy_cell_occupancy=.5,
          tiles_per_TP4_die=1536,incremental_die_slot_policy_mm2=inc_slot*1536/1e6,
          prior_macro_collar_envelope_um=[263.520,416.880],prior_macro_collar_sum_mm2=physical['macro_context']['macro_collar_sum_mm2'],
          existing_macro_collar_is_not_complete_tile_slot=True,
          new_clear_slot_containment_and_available_tracks_unproved=True,
          no_clock_PG_or_wire_cost_is_assumed_zero=True),
      routing=dict(proposed_independent_mask_nets_per_bank=16,total_mask_nets=80,
          actual_per_edge_available_tracks=False,actual_wire_capacitance_or_clock_skew_measured=False,
          source_pin_OBS_PG_geometry_required_before_tile_PR=True),
      latency=dict(existing_MEM_EXTRA_cycles=1,new_cycles=0,selected_scenario_has_no_retiming=True,
          exact_same_program_55_reference=h['same_program_55_bridge_reference'],
          new_cycle_delta_against_that_reference=0,
          no_new_fulltoken_simulation_required_for_same_edge_control_variant=True,
          any_extra_capture_stage_requires_separate_actual_instruction_calendar_reprice=True),
      signoff=dict(target_period_ps=1000/1.2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
          prior_failed_SS_data_slack_ps=-118.679901,prior_failed_control_slack_ps=-930.330505,
          prior_failure_preserved=True,ideal7p895628ps_macro_margin_not_transferred=True,
          direct_macro_pin_load_wire_clock_and_full_output_control_paths_must_be_measured=True),
      block_gates=dict(default_off_RTL='Write only the source-proved directcapture plus this fixed replicated selector scenario. Preserve macro,mask,strobe,metadata and MEM_EXTRA1 edges; prove actual source equivalence and 4state cases.',
          mapped_cone='After actualvariant proof: all10ROMs,2560capture bits,80localmask FFs,full2560AND/2048OR and hold/control cones active; replicas survive synthesis; report complete SS/FF paths and loaded pins; no fulltoken calendar prerequisite.',
          tile_PR='Own full arithmetic tile slot, actual pin/OBS/PG/corridor, CTS/reset/controlbuffers and SSsetup/FFhold price before hardening. No unrelated DS-calendar gate.'),
      mapped_cone_characterization_admitted_after_actual_variant_gate=True,tile_PR_admitted=False,
      hardware_adoption=False,fulltoken_rate_credit=False,new_hardware_jobs=0)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('fresh record required')
    a.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
