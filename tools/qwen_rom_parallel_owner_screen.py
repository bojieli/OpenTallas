#!/usr/bin/env python3
"""One source-backed parallel-owner screen, sized to the existing command bus.
Not an architecture adoption, parameter sweep, or sustained-bandwidth receipt.
"""
import json
import math
from pathlib import Path
import qwen_rom_owned_ready_context as Q
R=Q.R
OUT=Path('results/uarch/qwen_rom_parallel_owner_screen_20261002')


def price():
    peer=R.obj(Q.OUT/'inputs/KV-model-r3.json')
    ports=peer['actual_ports']; b=peer['logical_bytes']; area=peer['area']
    owners=math.ceil(ports['column_payload_ceiling_Bps_per_stack']/ports['owner_payload_ceiling_Bps_per_stack'])
    assert owners==14 and ports['owner_FSM']['min_accept_interval_edges']==14
    extra=(owners-1)*ports['stacks_per_rank']
    # Actual owner declarations. This is a conservative discrete FF reservation
    #for these four arrays only, not a mapped census or complete controller area.
    arrays={'cam':32*128*13,'seen':32*128*32,'live':4096,'remaining_PC':4096*6}
    source_bits=sum(arrays.values());newbits=extra*source_bits
    macros=extra*32
    macro=R.obj(Path('physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json'))
    macroarea=macros*macro['area']['macro_area_um2']/1e6
    statearea=newbits*(.37908+.04374)/1e6
    collectors=2*extra*R.tree_count(source_bits,8)['buffers']
    collectorarea=collectors*.10206/1e6
    oldknown=area['service_plus_tail_macro_mm2']+area['assembly_logic_lower_bound_mm2']
    incremental=macroarea+statearea+collectorarea
    debit=oldknown+incremental+Q.price()[0]['FF_plus_restoring_INV_plus_collector_area_um2']/1e6
    # No stale charge: selected tail bypass/read/write bytes replace the old
    #one-owner transport charge once, and no extra full reload is invented.
    owner_rate=min(owners*ports['owner_payload_ceiling_Bps_per_rank'],ports['column_payload_ceiling_Bps_per_rank'])
    byte_slots=b['conditional_offchip_read_rank']+b['conditional_selected_closing_K_V_write_rank']
    owner_s=byte_slots/owner_rate
    fill_s=peer['token_lower_bounds']['tail_bypass_masked_fill_s']
    compute=peer['token_lower_bounds']['conditional_compute_s']
    transport=max(owner_s,fill_s)
    return dict(schema='qwen-source-parallel-owner-screen-r1',status='NOT_ADMITTED_TAG_ROUTING_AND_FULL_PARENT_COST_MISSING',
        source_policy='Same selected8191 die-local refill/two K-tail bypass/new V forward policy; no second decode.',
        parameter_sweep=False,owners_per_stack=owners,replica_derivation='ceil(existing32GB/s command bus / existing32B-per14edge owner ceiling)',
        extra_owner_instances_per_rank=extra,extra_owner_macros_per_rank=macros,
        owner_array_source_bits=arrays,extra_owner_source_state_bits=newbits,
        source_state_scope='Four declared arrays reserved as ASR+restoring INV; logic, scalar state, allocation arbiter and protection additional; not a mapped count.',
        extra_owner_clock_pins=newbits+macros,extra_owner_reset_pins_reserved=newbits,
        collector_buffers_reserved=collectors,collector_routes_slew_and_PG_closed=False,
        extra_macro_area_mm2=macroarea,source_state_cell_reservation_mm2=statearea,
        clock_reset_collector_cell_reservation_mm2=collectorarea,incremental_known_reservation_mm2=incremental,
        existing_service_tail_512macro_clocks_rank_once=512,
        proposed_service_tail_macro_clocks_rank=512+macros,
        baseline_authority=area['authority'],baseline_mm2=area['baseline_mm2'],envelope_mm2=area['envelope_mm2'],
        named_baseline_component_debits=area['debits_already_in_Maxwell_baseline'],
        conditional_remaining_mm2_if_all_service_new=area['other_services_budget_mm2']-debit,
        conditional_remaining_mm2_if_PHY_also_new=area['other_services_budget_mm2']-debit-area['four_PHY_abstract_footprint_mm2'],
        complete_area=False,complete_floorplan_fit=False,
        source_command_buses_per_stack_unchanged=1,command_payload_rank_ceiling_Bps=owner_rate,
        shared_fill_lanes_unchanged=1,fill_bits_unchanged=1048,selected_corridor_um=96.768,
        owner_ingress_arbitration='14 request/return owners require exclusive allocation selection and identity-directed returns; one command per stack per edge remains.',
        candidate_internal_owner_route_bits=4,
        identity_blocker='Existing physical_tag/command.tag are12 bits, source allocator emits all4096 tags and zeros upper4 wire bits. Replication aliases tags unless allocation namespace/owner routing is implemented and priced; no boundary constant or free demux.',
        readiness_join_delta='Per-stack predicate must test all14 owner states/held/live_tags, not just one. Add13*19=247 source predicate bits/stack; same33-bit acknowledged snapshot only after true local reduction.',
        additional_readiness_predicate_bits_rank=4*13*19,
        selected_read_bytes_rank_token=b['conditional_offchip_read_rank'],
        selected_closing_write_bytes_rank_token=b['conditional_selected_closing_K_V_write_rank'],
        logical_read_debit_replaced_once=True,incremental_full_reload_bytes=0,
        old_current_owner_lower_bound_s=peer['token_lower_bounds']['selected_closing_read_plus_write_owner_slot_ceiling_s'],
        old_current_policy_rate_ceiling=peer['token_lower_bounds']['conditional_max_token_rate'],
        candidate_owner_command_slot_lower_bound_s=owner_s,
        candidate_fill_lower_bound_s=fill_s,conditional_perfect_compute_overlap_lower_bound_s=transport,
        conditional_candidate_rate_ceiling=1/transport,
        conditional_no_overlap_at_ceiling_s=transport+compute,
        compute_scope=peer['token_lower_bounds']['compute_scope'],
        actual_serial_compute_or_stage_overlap_closed=False,actual_sustained_transport_Bps=None,
        final_target_prediction=False,adopted_rate=None,source_map_admission=False,PnR=False,numerical_positions=0,
        resident_literal_overflow_mm2_preserved=area['literal_resident_overflow_before_other_services_mm2'],
        rejection_of_3k='One1048-bit fill lane still costs1.96224ms at its ceiling. More owners alone cannot meet333.333us; widening fill is not silently added.',
        next_source_step='Bind identity-directed owner ingress/returns and actual window/tile fill acceptance calendar. Price arbitration, tag namespace, causal exporters, mutable-state protection, CDC and legal clock/PG routes, then compose actual stage timing without perfect overlap credit.')


def generate():
    out=R.ROOT/OUT;out.mkdir(parents=True,exist_ok=True)
    result=price();(out/'model-r1.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    paths=[Path(__file__).relative_to(R.ROOT),Path('tests/test_qwen_rom_parallel_owner_screen.py'),Path('tools/uarch_model_qwen_owned_ready.py'),
        Q.OUT/'inputs/KV-model-r3.json',Q.OUT/'inputs/source/rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv',
        Q.OUT/'model-r1.json',Path('physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json')]
    (out/'sourcepins-r1.json').write_text(json.dumps({str(p):R.sha(p) for p in paths},sort_keys=True,indent=2)+'\n')
    (out/'artifact-sha256-r1.json').write_text(json.dumps({str(OUT/'model-r1.json'):R.sha(OUT/'model-r1.json')},indent=2)+'\n')
    return result


if __name__=='__main__':print(json.dumps(generate(),indent=2))
