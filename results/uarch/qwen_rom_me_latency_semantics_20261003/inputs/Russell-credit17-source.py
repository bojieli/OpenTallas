#!/usr/bin/env python3
"""ONE17/136/68/85 credit successor in the unified QROM model. No adoption."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import inspect
import json
import math
from pathlib import Path
import uarch_model as U
import uarch_model_qwen_kv_credit_allocator as A
from uarch_model_qwen_parent_context import tree_count
ROOT=A.ROOT
OUT=ROOT/'results/uarch/qwen_rom_kv_credit17_20261003'

class SpillPending:
    """Source471-bit returned record + valid;64RAM positions,4FF positions.

    One accepted return and one consume perPC/edge. Mutable records never
    reuse before consume; wrong epoch/address/tag/beat/due rejects atomically.
    Two candidate validation stages retained before raw can be consumed.
    Functional caller payload is not a production provider qualification.
    """
    def __init__(self):
        self.records={};self.keys={};self.raw={};self.last_write=None;self.last_read=None
    def issue(self,key,sector,producer,transport,column):
        if len(key)!=2 or not 0<=key[0]<4096 or not 0<=key[1]<32:raise ValueError('physical tag12/beat5')
        if key in self.keys:raise ValueError('duplicate live identity')
        if not 0<=sector<703125000 or not 0<=producer<2**64 or not 0<=transport<2**32:raise ValueError('source field bounds')
        if len(self.records)>=68:raise ValueError('68 combined pending/raw capacity')
        slot=next(i for i in range(68) if i not in self.records)
        self.records[slot]=(key,sector,producer,transport,column+25);self.keys[key]=slot
        return dict(slot=slot,storage='RAM' if slot<64 else 'FF_SPILL')
    def returned(self,key,sector,producer,transport,edge,payload):
        if key not in self.keys:raise ValueError('unallocated identity')
        slot=self.keys[key];r=self.records[slot]
        if slot in self.raw:raise ValueError('duplicate raw return')
        if (sector,producer,transport)!=r[1:4] or edge<r[4]:raise ValueError('identity/epoch/due')
        if not isinstance(payload,bytes) or len(payload)!=32:raise ValueError('actual32B provider required')
        if self.last_write is not None and edge<=self.last_write:raise ValueError('one response capture perPC/edge')
        self.raw[slot]=(edge+3+2,payload);self.last_write=edge
    def consume(self,key,edge):
        if key not in self.keys or self.keys[key] not in self.raw:raise ValueError('owned raw absent')
        slot=self.keys[key];due,payload=self.raw[slot]
        if edge<due:raise ValueError('three raw capture plus two validation stages')
        if self.last_read is not None and edge<=self.last_read:raise ValueError('one held capture perPC/edge')
        del self.raw[slot];del self.records[slot];del self.keys[key];self.last_read=edge
        return payload

# Exact frozen allocator/PC policy; only credit/storage capacities and two
#proposed protection registers in each direction change. No alternate policy.
cal=inspect.getsource(A.credit_layer_calendar).replace('def credit_layer_calendar(', 'def credit17_calendar(')
changes={
 'credit=[16]*8;globalcredit=128':'credit=[17]*8;globalcredit=136',
 'pending[key]+n<=64':'pending[key]+n<=68',
 '128-globalcredit':'136-globalcredit',
 'if peak_pool>80':'if peak_pool>85',
 "'80 actual slots/group/lane'":"'85 actual slots/group/lane'",
 'globalcredit!=128 or credit!=[16]*8':'globalcredit!=136 or credit!=[17]*8',
 'assembly_slots_per_pool=80':'assembly_slots_per_pool=85',
 'global_assembly_slots=4480':'global_assembly_slots=4760',
 'col+25000+3000+12000+link':'col+25000+3000+2000+12000+link',
 'owned(st,g,visible+link)':'owned(st,g,visible+link+2000)'}
for old,new in changes.items():
    if old not in cal:raise ValueError('frozen source anchor '+old)
    cal=cal.replace(old,new)
ns=dict(A.__dict__);exec(cal,ns);credit17_calendar=ns['credit17_calendar']


def sizing(old):
    c=json.loads((ROOT/'results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json').read_text())['cells']
    ff=c['ASR_area_um2']+c['INV_area_um2'];a=c['AND3_area_um2'];inv=c['INV_area_um2'];buf=c['BUF_area_um2']
    muxbit=3*a+2*inv;eqbit=3*a+5*inv
    # Source returned_t471 plus valid; source request/return macros remain64x512.
    # No anonymous baseline credits: newly specified validators charged gross.
    counts=dict(pending_four_FF_spill=128*4*472,pending_key_register_increment=128*4*17,
        assembly_extra_words=56*5*787,assembly_metadata_register_increment=56*11*72,
        burst_receipt_increment=4*8*(192+12+6+3+16*8+4),matched_cohort_increment=8*(100+32+3+4*12+4+32+32+8),
        cohort_index_width_increment=136*3,spill_pointer_valid_controls=128*10,
        return_protection_two_registers=128*(151+64+34+21+8),
        reverse_protection_two_registers=4*8*(404+192+12+5+34+64+32+16+9),
        namespace_atomic_alloc_retire_protection=4*(2*(12+32+3+8)+192+32+16))
    reps=dict(pending_four_FF_spill=128,pending_key_register_increment=128,assembly_extra_words=56,
        assembly_metadata_register_increment=56,burst_receipt_increment=32,matched_cohort_increment=8,
        cohort_index_width_increment=136,spill_pointer_valid_controls=128,
        return_protection_two_registers=128,reverse_protection_two_registers=32,namespace_atomic_alloc_retire_protection=4)
    oldassembly=2*56*tree_count(80*787,8)['nodes'];newassembly=2*56*tree_count(85*787,8)['nodes']
    collectors=newassembly-oldassembly
    for name,n in counts.items():
        if n%reps[name]:raise ValueError('replica partition '+name)
        if name!='assembly_extra_words':collectors+=2*reps[name]*tree_count(n//reps[name],8)['nodes']
    mux=dict(pending68_vs64=128*4*471,spill_write_enable_hold=128*4*471,
        spill_four_way_read_and_RAM_join=128*(3+1)*471,assembly85_vs80=56*5*787,
        extra_quarter_write=56*5*4*144,
        reverse_expected_context_and_atomic_update=32*3*(192+12+5+34+64+32+16)+4*3*(12+32+3+8))
    equality=dict(pending_extra_key=128*4*17,extra_pending_vs16cache_RW_alias=128*4*16*34,
        assembly_extra_ready=56*5*32,selected_return_identity_gross=128*151,
        reverse_identity_gross=32*(192+12+5+34+64+32+16),namespace_joint_epoch_gross=4*(192+32+12))
    # Unsigned due and capacity/address comparisons:64-bit compare tree plus
    # per-bit prefix gates; not treated as a free equality gate.
    compare=dict(return_due64=128*64,return_sector_aperture34=128*34,
        pending68_capacity7=128*7,reverse_due_and_length=32*(64+6),
        group17_global136_credit=8*5+8,namespace_remaining_PC_and_tag=4*(6+12))
    reduction=dict(selected_return_fault_reduce=128*(151+64+34+21),
        reverse_reserved_zero_and_match=32*(404+192+12+5+34+64+32+16),namespace_refusal_reduce=4*(192+32+12))
    statearea=sum(counts.values())*ff;selectarea=sum(mux.values())*muxbit
    protectionarea=sum(equality.values())*eqbit+sum(compare.values())*(5*a+5*inv)+sum(reduction.values())*a
    delta=(statearea+selectarea+protectionarea+collectors*buf)/1e6
    return dict(FF_increment=counts,replicas=reps,mux_increment_bits=mux,equality_check_bits=equality,
        unsigned_compare_bits=compare,reduction_bits=reduction,clock_reset_collector_increment=collectors,
        assembly_old_collectors=oldassembly,assembly_new_collectors=newassembly,
        FF_cell_um2=ff,mux_bit_cell_um2=muxbit,equality_bit_cell_um2=eqbit,
        state_um2=statearea,select_um2=selectarea,transaction_protection_um2=protectionarea,
        collector_um2=collectors*buf,delta_known_mm2=delta,
        total_known_service_mm2=old['cells']['total_known_service_mm2']+delta,
        conditional_remaining_mm2=old['physical']['conditional_remaining_mm2']-delta,
        existing_macro_arrays_recharged=False,fill_fanout_recharged=False,
        protection_scope='Source transaction validity/immutable identity,duplicate,epoch,bounds,due,credit,ACK/alloc-retire checks charged; register/gate reservations are proposals, not SS/FF mapped cells. No ROM ECC or mandatory parity/CRC added.',
        mutable_storage_protection_implementation=None,mutable_storage_protection_area_mm2=None,
        protection_blocker='Source pending/return/context mutable memory fault-protection realization lacks a named priced baseline receipt. Existing protection is not removed; missing protection is not assigned zero or claimed qualified.')


def build():
    original=ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json';old=json.loads(original.read_text())
    bound=ROOT/'results/uarch/qwen_rom_kv_stall_attribution_20261002/bound-contract-r1.json'
    b=json.loads(bound.read_text())
    if b['fixed_lease']['minimum_uniform_group_credits']!=17:raise ValueError('not dimensioned17 seed')
    for p,h in old['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('pinned production source changed '+p)
    point=U.qwen_tp_point(4,6144,'ucie_measured',clock_hz=1200000000,me_lat_extra=55,ctx=8192,su_width=64)
    if point['layer_chain_cycles']!=3338 or point['exchange']['per_allreduce_cycles']!=71:raise ValueError('unified layer cost changed')
    prefix_cycles=451;ar=F(str(point['exchange']['per_allreduce_cycles']))*2*F(128,100)
    rest=(F(point['layer_chain_cycles']-prefix_cycles)+ar)*F(2500,3)
    extra_cycles=F(point['cycles'])-36*(F(point['layer_chain_cycles'])+2*F(str(point['exchange']['per_allreduce_cycles'])))
    extra=extra_cycles*F(2500,3)
    if abs(extra-F(str(old['calendar']['extra_nonlayer_compute_s']))*10**12)>1:raise ValueError('unified nonlayer debit exceeds1ps serialization rounding')
    t=F(0);compute=F(0);windows=[F(0)]*2;service=A.S.PCService();rows=[]
    for layer in range(36):
        begin=max(t,windows[layer%2]);prefix_begin=compute;prefix=compute+prefix_cycles*F(2500,3)
        row=credit17_calendar(layer,begin,prefix,service);t=row.pop('end_ps');ready=row.pop('fill_end_ps')
        compute=max(ready,prefix)+rest;windows[layer%2]=max(t,compute)
        rows.append(dict(layer=layer,begin_ps=float(begin),prefix_begin_ps=float(prefix_begin),prefix_ready_ps=float(prefix),
            fill_ready_ps=float(ready),all_grants_ps=float(t),compute_done_ps=float(compute),**row))
    total=float((max(t,compute)+extra)/10**12);gain=old['calendar']['composed_conditional_s']/total-1
    cells=sizing(old)
    # All added cross-block protected acceptance is declared; local selector
    #cuts are charged separately and must receive actual route/clock slots.
    ports=dict(MACs_per_cycle_added=0,context_banks_per_stack=32,context_depth_records=128,
        request_RAM_entries_per_PC=64,return_RAM_entries_per_PC=64,return_RAM_width_bits=512,
        return_RAM_read_B_per_PC_edge=64,return_RAM_write_B_per_PC_edge=64,
        FF_spill_entries_per_PC=4,FF_spill_record_bits=471,FF_spill_read_B_per_PC_edge=32,FF_spill_write_B_per_PC_edge=32,
        combined_RAM_spill_accepts_per_PC_edge=1,combined_RAM_spill_consumes_per_PC_edge=1,
        return_groups_per_stack=8,column_paths_per_stack=4,column_payload_B_per_stack_edge=128,
        owned_payload_B_per_stack_edge=8*32,owned_DATA_GRANT_share_each_group_port=True,
        global_fill_lanes=7,global_fill_payload_B_per_stream_edge=7*64,per_tile_write_ports=1,
        request_paths_per_stack=1,global_cohort_slots=136,group_cohort_slots=17,pending_per_PC=68,
        group_lane_word_pools=56,words_per_pool=85,total_assembly_words=4760,
        response_flight_output_credits_per_group=32,lookahead_entries_per_PC=16,write_slots_per_PC=4,
        lookup_latency_edges=12,raw_capture_RAM_or_spill_edges=3,return_validation_edges=2,reverse_validation_edges=2,
        service_Hz=1000000000,stream_Hz=1200000000,serial_Hz=900000000,
        ports_or_MACs_multiplied_by1536=False)
    cuts=dict(fill_control_bits=7973,existing_service_boundary_bits=old['physical']['global_boundary_bits'],
        return_validation_status_bits=128*8,reverse_validation_status_bits=32*9,namespace_fault_ready_bits=4*4,
        global_boundary_reserved_bits=old['physical']['global_boundary_bits']+128*8+32*9+4*4,
        local_RAM_spill_select_bundle_bits_per_PC=471+7+2+4+1,
        local_85word_pool_read_bundle_bits=787+7+1,local_cohort_header_index_bits=8,
        existing_fill_control_available_tracks=1360,return_status_channels_allocated=False,
        named_legal_separate_channels_owner='Ampere',uniform_widening_selected=False,
        area_for_loaded_wires_routes_vias_PG_hold_mm2=None,SSFF_or_CDC_closed=False)
    return dict(schema='qrom-unified-one17-credit-successor.v1',status='G0_FAIL_UNQUALIFIED_FINITE_CANDIDATE',
        predecessor_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),dimensioning_bound_sha256=hashlib.sha256(bound.read_bytes()).hexdigest(),
        source_sha256=old['source_sha256'],source_parent=old['parent'],
        unified_model_join=dict(authority='tools/uarch_model.py:qwen_tp_point',opt_in_only=True,
            baseline_cycles=point['cycles'],baseline_layer_cycles=point['layer_chain_cycles'],baseline_unit_busy=point['unit_busy'],
            prefix_cycles=prefix_cycles,AR_stream_equivalent_cycles_per_layer=float(ar),nonlayer_cycles=float(extra_cycles),
            nonlayer_cost_s=float(extra/10**12),existing_KV_HBM_debit_replaced_once=True,incremental_compulsory_refill_bytes=0,
            modeled_source_KV_bytes_per_token=32736*32*4*36,
            legacy_KV_stream_rate_or_aggregate_tile_ports_used_as_PHY=False,
            compute_then_service_doublecharge=False,declared_overlap='Prefix/compute and source service overlap only as the finite two-window36-layer calendar permits; nextcold service begins after priorallgrants. Actual production earlyrelease remains unbound.'),
        ONE_configuration=ports,cells=cells,cuts=cuts,
        controller=dict(source_native_deadlines_retained=True,per_PC_accept_II_edges=5,read_due_edges=25,
            command_counts=dict(service.count),commands_per_shared_path=[[len(v) for v in paths] for paths in service.bus],
            command_event_sha256=service.digest.hexdigest(),max_lazy_refresh_lateness_edges=service.max_refresh_lateness,
            strict_idle_refresh_qualified=False,source_CTX_namespace_or_macros_replicated=False,
            immutable_header_BITS=dict(returned=471,request=455,command=339,reverse=404,identity=192),
            actual_mutable_protection_or_ACK_implementation_qualified=False),
        calendar=dict(rows=rows,full36_sequential=True,all1536_destinations=True,total_conditional_s=total,
            predecessor_conditional_s=old['calendar']['composed_conditional_s'],conditional_rate_gain_fraction=gain,
            clears_model_1percent=gain>=.01,meets_3k_conditional=total<=1/3000,margin_to_3k_s=1/3000-total,
            source_policy_scope='Same conditional source8191 cold-per-layer lease and tail/Vforward policy, LEN1 writes, group-order/whole-cohort visibility/grants retained.17 capacity changes queueing/refresh; no unchanged-lifetime assumption.',
            actual_payload_state_or_demand_journal_bound=False,adopted_rate=None,production_qualified=False),
        physical=dict(required_sustained_PHY_Bps_per_stack=old['physical']['required_sustained_PHY_Bps_per_stack'],
            actual_sustained_PHY_Bps=None,extra_PHY_replicas=0,baseline_array_mm2=old['physical']['parent_baseline_mm2'],
            source_SS_context_capture_setup_route_budget_ps=old['physical']['source_SS_macro_capture_budget_ps'],
            SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,complete_service_slot_fit=None,
            source_379bit_instruction_and128x_capture_repriced=False),
        admission=dict(model_only=True,hardware=False,new_RTL=False,new_PnR=False,physical=False,
            adoption=False,requires_measured_RTL_gain=True,
            blockers=['Finite target/1percent screen as reported','Source-owned payload/state/actual producer policy and ACK lifecycle','Named mutable-storage protection realization and price','Ampere legal channels/loaded clocks/reset/CDC/hold/PG slots and sustainedPHY','Strict refresh and Maxwell named baseline debit join']),
        implementation_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('tools/uarch_model_qwen_kv_credit17.py','tools/uarch_model_qwen_kv_credit_allocator.py','tools/uarch_model_qwen_kv_successor.py')})

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);args=ap.parse_args()
    with args.result.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')
