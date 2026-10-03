#!/usr/bin/env python3
"""One 17/group capacity delta on the frozen KV7 native-PHY allocation.

Constructive cell/route reservation, not a replay or source admission. Mutable
record protection is priced explicitly; fault-free ROM policy is unchanged.
"""
import copy
import json
import math
from pathlib import Path
import qwen_rom_channel_parent_admission as C
R=C.R
OUT=Path('results/uarch/qwen_rom_kv_credit17_physical_20261003')


def tree(n):
    count=0
    while n>1:
        n=math.ceil(n/8);count+=n
    return count


def parity_layout(width):
    r=1
    while 2**r<width+r+1:r+=1
    positions=[i for i in range(1,width+r+1) if i&(i-1)]
    masks=[[i for i in positions if i&(1<<bit)] for bit in range(r)]
    return r,positions,masks


def protection(width,entries,replicas):
    r,pos,masks=parity_layout(width);code=width+r+1
    #One write encoder/read decoder per local replica, not per stored entry.
    encoder=sum(len(m)-1 for m in masks)+(width+r-1)
    decoder=sum(sum(bool(i&(1<<b)) for i in range(1,code))-1 for b in range(r))+(code-1)
    syndrome_compare=width*r+(r-1)+3
    correction_xors=width
    buffers=sum(tree(sum(bool(i in m) for m in masks)+1) for i in pos)*2
    return dict(data_bits=width,check_bits=r+1,code_bits=code,stored_check_FFs=entries*(r+1),
        pipeline_FFs=replicas*2*(code+2),encoder_XOR2=replicas*encoder,
        decoder_XOR2=replicas*(decoder+correction_xors),syndrome_AND2=replicas*syndrome_compare,
        decoder_inverters=replicas*(r+3),fanout_buffers=replicas*buffers,local_replicas=replicas,
        construction='extended Hamming SECDED; one registered encoder and decoder per local port',
        candidate_new_record_protection=True,existing_record_protection_qualified=False,
        encoder_edges=1,decoder_edges=1,combinational_SSFF_closed=False)


def price():
    peer=R.obj(OUT/'inputs/Russell-af7c-peer-contract-r1.json')
    assert R.sha(OUT/'inputs/Russell-af7c-model-r3.json')==peer['model_sha256']
    assert R.sha(OUT/'inputs/Russell-af7c-bound-contract-r1.json')==peer['bound_sha256']
    target=peer['ONE_next_target']
    assert [target[k] for k in ('group_credits','regular_total_cohort_capacity','pending_entries_per_PC','words_per_group_lane_pool','total_assembly_words')]==[17,136,68,85,4760]
    parent=R.obj(C.OUT/'model-r6.json');result=copy.deepcopy(parent)
    cells=R.obj(OUT/'inputs/model-r7.json')['cells']
    ff=cells['ASR_area_um2']+cells['INV_area_um2'];buf=cells['BUF_area_um2'];and3=cells['AND3_area_um2'];inv=cells['INV_area_um2']
    buffer8=C.Q.J.A.abstracts()['BUFx8_ASAP7_75t_R']['size_um']
    sized_buf=buffer8[0]*buffer8[1]
    mux=3*and3+2*inv;xor=3*and3+5*inv
    #Widths are frozen predecessor formulas: 471-bit pending+valid, 787-bit
    #assembly words, 259-bit matched header, 345-bit per-stack burst receipt.
    families={
        'pending_spill':dict(FFs=128*4*472,replicas=128,domain='service'),
        'pending_match_hold':dict(FFs=128*4*17,replicas=128,domain='service'),
        'assembly_words':dict(FFs=56*5*787,replicas=56,domain='stream'),
        'assembly_selection_pipeline':dict(FFs=56*(85+43+22+11-80-40-20-10)*72,replicas=56,domain='stream'),
        'matched_headers':dict(FFs=8*259,replicas=8,domain='stream'),
        'burst_receipts':dict(FFs=32*345,replicas=32,domain='service'),
        'spill_arbiter':dict(FFs=128*(4+2+1+1),replicas=128,domain='service'),
        'credit_address_growth':dict(FFs=2*(8+1),replicas=1,domain='stream')}
    protections={name:protection(w,e,reps) for name,w,e,reps in [
        ('pending_spill',472,128*4,128),('assembly_words',787,56*5,56),
        ('matched_headers',259,8,8),('burst_receipts',345,32,32)]}
    for name,p in protections.items():
        original=families[name]
        families[name+'_protection']=dict(FFs=p['stored_check_FFs']+p['pipeline_FFs'],
            replicas=p['local_replicas'],domain=original['domain'])
    #Price actual local replica tree deltas against existing endpoints, not
    #one aggregated rank tree and not a second global padding chain.
    base_per_rep={'pending_spill':64*472,'pending_match_hold':64*17,
        'assembly_words':80*787,'assembly_selection_pipeline':150*72,
        'matched_headers':16*259,'burst_receipts':128//8*345}
    for name,f in families.items():
        baseline=base_per_rep.get(name,0);new=math.ceil(f['FFs']/f['replicas'])
        f['clock_reset_collector_delta']=2*f['replicas']*(tree(baseline+new)-tree(baseline))
        f['existing_affected_collector_buffers']=2*f['replicas']*tree(baseline)
        f['collector_scope']='fanout8 count reservation; geometry/slew below, no CTS qualification'
    selectors=dict(pending_read_mux_bits=128*4*471,pending_write_select_bits=128*4*472,
        pending_key_equality_bits=128*4*17,pending_valid_decode_bits=128*68*7,
        pending_cache_alias_equality_bits=128*4*16*34,
        assembly_read_mux_bits=56*5*787,assembly_quarter_write_mux_bits=56*5*4*(128+16),
        assembly_ready_equality_bits=56*5*32,header_mux_bits=8*259,
        header_decode_bits=8*17*5,burst_receipt_mux_bits=32*345)
    mux_bits=sum(v for k,v in selectors.items() if 'mux' in k or 'select' in k)
    compare_bits=sum(v for k,v in selectors.items() if 'equality' in k or 'decode' in k)
    selector_area=mux_bits*mux+compare_bits*xor
    protection_area=sum((p['encoder_XOR2']+p['decoder_XOR2'])*xor+p['syndrome_AND2']*and3+p['decoder_inverters']*inv+p['fanout_buffers']*sized_buf for p in protections.values())
    ff_count=sum(f['FFs'] for f in families.values());collectors=sum(f['clock_reset_collector_delta'] for f in families.values())
    #Finite per-replica32um collector segments. Characterize the unchanged
    #fanout8 and upper-wire load at both corners; don't assume ideal feed.
    feed={}
    for corner in ('ss','ff'):
        _,lib,caps=C.Q.R.library(corner)
        cap=max(caps[('DFFASRHQNx1_ASAP7_75t_R',pin)]['cap_fF'] for pin in ['CLK','RESETN'])
        cap=max(cap,caps[('BUFx8_ASAP7_75t_R','A')]['cap_fF'])
        load=8*cap+(32+8*16)*C.Q.J.C
        feed[corner]=dict(load_fF=load,fanout=8,segment_um=32,
            terminal_spurs_per_driver=8,terminal_spur_um=16,cell='BUFx8_ASAP7_75t_R',
            rise_slew_ps=R.envelope(lib['BUFx8_ASAP7_75t_R'],'rise_transition',load,5,80),
            fall_slew_ps=R.envelope(lib['BUFx8_ASAP7_75t_R'],'fall_transition',load,5,80),
            clock_delay_ps=R.envelope(lib['BUFx8_ASAP7_75t_R'],'cell_rise',load,5,80),
            BUF4_with_same_spurs_rise_slew_ps=R.envelope(lib['BUFx4_ASAP7_75t_R'],'rise_transition',load,5,80),
            route_segment_load_fF=cap+128*C.Q.J.C,
            route_segment_rise_slew_ps=R.envelope(lib['BUFx8_ASAP7_75t_R'],'rise_transition',cap+128*C.Q.J.C,5,80),
            route_segment_fall_slew_ps=R.envelope(lib['BUFx8_ASAP7_75t_R'],'fall_transition',cap+128*C.Q.J.C,5,80),
            whole_clock_or_reset_timing_qualified=False)
    #Boundary43256 differs from earlier42452. Pay all804 new service bits
    #over the frozen four PHY/controller spans; no new transport port.
    boundary_delta=43256-parent['service_boundary_cut_ledger']['source_boundary_bits']
    routes=[];route_buf=0
    for prior in parent['source_to_controller_route_lower_bounds']:
        bits=boundary_delta//4
        n=bits*(prior['segments_per_bit']+1);route_buf+=n
        routes.append(dict(stack=prior['stack'],additional_service_bits=bits,
            nominal_endpoint_distance_um=prior['nominal_endpoint_distance_um'],
            segments_per_bit=prior['segments_per_bit'],maximum_segment_um=128,
            buffers=n,actual_pin_binding_complete=False))
    affected=sum(f['existing_affected_collector_buffers'] for f in families.values())
    upgrade=affected*(sized_buf-buf)
    delta=(ff_count*ff+(collectors+route_buf)*sized_buf+upgrade+selector_area+protection_area)/1e6
    result['schema']='QROM_CREDIT17_PHYSICAL_INCREMENT_R4'
    result['Russell_credit_contract_commit']='af7c7112'
    result['credit17']=dict(target=target,protected_new_records=protections,FF_families=families,
        selector_bits=selectors,selector_area_um2=selector_area,protection_logic_area_um2=protection_area,
        new_FFs=ff_count,collector_buffers=collectors,collector_wire_um=collectors*(32+8*16),
        affected_existing_collector_buffers_upgraded=affected,existing_collector_drive_upgrade_um2=upgrade,
        collector_load_and_slew=feed,additional_boundary_bits=boundary_delta,
        additional_route_buffer_reservation=route_buf,route_reservations=routes,
        delta_known_mm2=delta,cell_prices_um2=dict(FF_with_restoring_INV=ff,BUF4=buf,selected_BUF8=sized_buf,mux_bit=mux,XOR2=xor),
        payload_protection_scope='new mutable FF records only; no ROM ECC added',
        protection_added_path_edges=dict(encoder=1,decoder=1),
        candidate_replayed=False,capacity_admitted=False,exact_parent_protection_and_atomic_update_binding=False,
        local_controller_sites_and_per_family_pin_landing_complete=False,
        constructor_logic_policy='AND3 spare input tied high; ties/source hold and gate mapping remain prerequisites')
    result['known_composed_area_mm2']+=delta
    result['remaining_area_before_unknown_placements_mm2']-=delta
    result['service_known_reservation_mm2']+=delta
    for slot in result['controller_slots']:
        before=slot['service_known_reservation_mm2']+slot['inherited_other_service_debit_reserved_mm2']
        slot['service_known_reservation_mm2']+=delta/4
        slot['minimum_cell_macro_utilization']*=(before+delta/4)/before
    result['source_sized_clock_pins']+=ff_count
    result['source_reset_upper']+=ff_count
    result['credit17_added_clock_pins_by_domain']={domain:sum(f['FFs'] for f in families.values() if f['domain']==domain) for domain in ['service','stream']}
    result['service_boundary_cut_ledger']['source_boundary_bits']=43256
    result['service_boundary_cut_ledger']['remaining_nonfill_bits']=43256-7336
    result['credit17_fixed_work_bounds']=peer['fixed_lease']
    result['credit17_full_token_latency_s']=None
    result['latency_binding']='Existing16/128 measured calendar preserved;17/136 must replay with paid encode/decode edges, spills/holds/strict refresh. Fixed-work floor is necessity, not achievable latency.'
    result['admission_failures']+=['17/136 finite spill/protection calendar not replayed','new local sites/atomic credit protection and selectors not mapped or SSFF-qualified']
    result['status']='FAIL_G0_CREDIT17_PRICED_RESERVATION_NO_CAPACITY_ADMISSION'
    return result


if __name__=='__main__':
    p=R.ROOT/OUT/'model-r4.json'
    if p.exists():raise ValueError('preserve verdict')
    C.Q.M.write(p,price())
