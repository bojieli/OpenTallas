"""Decomposition of the Qwen ROM KV source service area (credit17 model-r3 cells.total_known_service_mm2 = 19.2213 mm2)
into its component families, re-summed from the four generators' own formulas (zero residual).

Lineage: parent_context_service model-r7 (2.0924 baseline) + kv_bank_groups model-r4 (+6.6498) + kv_credit_allocator
model-r4 (+9.6223 successor, +0.0170 credit allocator) + kv_credit17 model-r3 (+0.8397).  Clock/reset collectors are
charged per family from each generator's own tree_count replica trees; mux/equality reservations are split by the
generators' listed terms.  One inferred mapping: bank_groups' unnamed mux terms 4*4096*8*6 -> shared_tag_group_owner_map
and 4*4*7*339 -> command_lookahead_head_holds (their sum is asserted equal to the record's mux_bits).

Used by tools/qwen_rom_floorplan_nearhbm_r2.py; no outputs are written.
"""
import json
import sys
from pathlib import Path


def families(root):
    R = str(Path(root)) + '/'
    sys.path.insert(0, R + 'tools')
    from uarch_model_qwen_parent_context import tree_count
    J = lambda p: json.load(open(R + p))
    pc=J('results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json')
    c=pc['cells'];ff=c['ASR_area_um2']+c['INV_area_um2'];a=c['AND3_area_um2'];inv=c['INV_area_um2'];buf=c['BUF_area_um2']
    mux=3*a+2*inv;eq=3*a+5*inv;cmp_=5*a+5*inv
    fam={}
    def add(k,um2,stage):
        fam.setdefault(k,{}); fam[k][stage]=fam[k].get(stage,0)+um2/1e6
    # ---- baseline 2.0924
    A=pc['joint_service_architecture']['area']
    coll={x['name']:x['replicas']*(tree_count(x['clock_sinks'],8)['nodes']+tree_count(x['reset_sink_upper'],8)['nodes'])*buf for x in A['per_domain_replica_collector_allocation']}
    add('B:FAST request/response/reverse route pipes+ingress mux',A['extra_route_mux_arb_reservation_um2']+coll['route455_delta']+coll['route467_delta']+coll['route404_delta'],'b')
    add('B:tagged owner pipeline (flights/outputs/dup masks)',A['tagged_owner_pipeline_cell_reservation_um2']+coll['tagged_owner_flights'],'b')
    add('B:producer CDC route+source FIFO',A['producer_CDC_and_source_fifo_reservation_um2']+coll['producer_route']+coll['producer_source_FIFO_metadata']+coll['producer_destination_FIFO'],'b')
    add('B:tag quarantine',A['quarantine_cell_reservation_um2']+coll['quarantine_per_stack'],'b')
    add('B:shared return arbiter',A['shared_return_arbiter_cell_reservation_um2']+coll['return_arbiter'],'b')
    add('B:stage-window leases+per-tile operand stage',A['stage_window_cell_reservation_um2']+coll['window_operand_stage_per_tile']+coll['window_leases'],'b')
    add('B:extra owner',coll['extra_owner'],'b')
    # ---- bank groups 6.6498
    bg=J('results/uarch/qwen_rom_kv_bank_groups_20261002/model-r4.json')['cells']
    for k,n in bg['delta_FF'].items(): add('G:'+k,n*ff+bg['collector_buffers_by_local_replica_family'][k]*buf,'g')
    mt={'G:assembly (8x512 pools, write mux)':8*512*4*(128+16),'G:seven_additional_group_flight_and_output_rings':4*7*32*(542+467),
     'G:command_lookahead_head_holds':4*4*7*339,'G:fill_root_registers_total':6*31*1048,'G:PC_frozen16_record_lookahead':4*32*15*472,
     'G:shared_tag_group_owner_map':4*4096*8*6,'G:per_tile_per_window_row_visibility':1536*107}
    assert sum(mt.values())==bg['mux_bits']
    for k,v in mt.items(): add(k,v*mux,'g')
    add('G:response extra 48 macros (64x512)',bg['extra_response_macro_area_mm2']*1e6,'g')
    add('G:fill fanout buffers',bg['fill_fanout_cell_reservation_mm2']*1e6,'g')
    add('G:assembly (8x512 pools, write mux)',(bg['assembly_cell_delta_mm2']+bg['assembly_clock_reset_reservation_mm2'])*1e6,'g')
    # ---- successor 9.6223
    sc=J('results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json')['cells']
    for k,n in sc['successor_delta_FF'].items():
        r=sc['replicas'][k]; cb=0 if k=='extra_lane_partitioned_assembly_words' else 2*r*tree_count(n//r,8)['nodes']
        add('S:'+k,n*ff+cb*buf,'s')
    add('S:assembly_collectors_56pool_delta',sc['assembly_collector_delta']*buf,'s')
    add('S:pending_key_comparison_holds',(sc['pending_mux_bits'])*mux+sc['pending_equality_bits']*eq,'s')  # pending mux+eq
    add('S:gross_native_PC_bank_and_held_state',sc['extra_bank_register_selection_bits']*mux,'s')
    add('S:eligibility_four_register_levels',sc['eligibility_comparison_bits']*eq,'s')
    add('S:RW alias hazard eq',sc['read_write_alias_equality_bits']*eq,'s')
    add('S:assembly_selection_metadata_pipeline',(56*79*787+sc['assembly_extra_quarter_mux_bits'])*mux+sc['assembly_ready_comparison_bits']*eq,'s')
    add('S:fill_root',7*7*1048*mux+sc['delta_fill_distribution_buffers']*buf,'s')
    ca=sc
    cnt=dict(descriptor_epoch_extent_release=4*8*(192+32+3+26+64+1),request_selection_three_registers=4*3*(455+192+3+32),round_robin_and_inflight_group_reservations=4*(3+8*3),matched_stack_accept_holds=4*(192+8+1))
    add('S:credit allocator (cohort 8-way arbiter)',ca['credit_allocator_delta_mm2']*1e6,'s')
    # ---- credit17 0.8397
    k7=J('results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json')['cells']
    for k,n in k7['FF_increment'].items():
        r=k7['replicas'][k]; cb=0 if k=='assembly_extra_words' else 2*r*tree_count(n//r,8)['nodes']
        add('C:'+k,n*ff+cb*buf,'c')
    add('C:assembly_extra_words',(k7['assembly_new_collectors']-k7['assembly_old_collectors'])*buf,'c')
    m=k7['mux_increment_bits']
    add('C:pending_four_FF_spill',(m['pending68_vs64']+m['spill_write_enable_hold']+m['spill_four_way_read_and_RAM_join'])*mux,'c')
    add('C:assembly_extra_words',(m['assembly85_vs80']+m['extra_quarter_write'])*mux,'c')
    add('C:reverse_protection_two_registers',32*3*(192+12+5+34+64+32+16)*mux,'c')
    add('C:namespace_atomic_alloc_retire_protection',4*3*(12+32+3+8)*mux,'c')
    e=k7['equality_check_bits'];u=k7['unsigned_compare_bits'];rd=k7['reduction_bits']
    add('C:pending_key_register_increment',e['pending_extra_key']*eq,'c')
    add('C:pending_four_FF_spill',e['extra_pending_vs16cache_RW_alias']*eq+u['pending68_capacity7']*cmp_,'c')
    add('C:assembly_extra_words',e['assembly_extra_ready']*eq,'c')
    add('C:return_protection_two_registers',e['selected_return_identity_gross']*eq+(u['return_due64']+u['return_sector_aperture34'])*cmp_+rd['selected_return_fault_reduce']*a,'c')
    add('C:reverse_protection_two_registers',e['reverse_identity_gross']*eq+u['reverse_due_and_length']*cmp_+rd['reverse_reserved_zero_and_match']*a,'c')
    add('C:namespace_atomic_alloc_retire_protection',e['namespace_joint_epoch_gross']*eq+u['namespace_remaining_PC_and_tag']*cmp_+rd['namespace_refusal_reduce']*a,'c')
    add('C:matched_cohort_increment',u['group17_global136_credit']*cmp_,'c')
    tot = {k: sum(v.values()) for k, v in fam.items()}
    stage = {}
    for v in fam.values():
        for s, x in v.items():
            stage[s] = stage.get(s, 0) + x
    return tot, stage
