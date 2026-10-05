#!/usr/bin/env python3
"""One source-pinned bridge F0 inventory; explicit descriptor HBM misses.

All stage durations are model proposals. No RTL, simulated tick or cold byte
replay is promoted to a physical endpoint or finite production upper bound.
"""
import argparse,gzip,hashlib,importlib.util,json,math
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_baseline_bridge_20261003/f0_r3'
PIN='5748660de2efe3633ea0b5f2b35226fa78ef88bfbb09251303ba0a567878b194'
EVENTS=('directory_lookup','owner_grant','tag_allocate','CDC_request','backend_accept','SRAM_read','refill','merge','SRAM_write','backend_visible','completion_match','completion_capture','RF_pair_read','RF_both_copy_write','RF_common_ACK','metadata_fence','consumer','child_reverse','parent_reverse','CDC_return','credit_release')
PHASES={
'KV_PV_consumer':('consumer',),'KV_SCORES_consumer':('consumer',),'KV_metadata_consumer':('consumer',),
'KV_metadata_grant':('directory_lookup','owner_grant','tag_allocate','CDC_request','backend_accept'),
'KV_metadata_mask_merge':('merge',),'KV_metadata_old_capture':('SRAM_read','completion_capture'),
'KV_metadata_reverse':('child_reverse','CDC_return','credit_release'),
'KV_metadata_write_visible':('SRAM_write','backend_visible','completion_match','metadata_fence'),
'KV_parent_grant':('owner_grant',),'KV_parent_reverse':('parent_reverse','credit_release'),
'KV_reader_acquire':('directory_lookup','owner_grant','metadata_fence'),
'KV_sector_consumer':('consumer',),'KV_sector_mask_merge':('merge',),
'KV_sector_old_capture':('SRAM_read','completion_capture'),
'KV_sector_read_capture':('SRAM_read','completion_capture'),
'KV_sector_reverse':('child_reverse','CDC_return','credit_release'),
'KV_sector_write_visible':('SRAM_write','backend_visible','completion_match'),
'KV_state_bitmap_visible':('backend_visible','metadata_fence'),
'KV_state_record_bitmap_fence':('metadata_fence',),
'KV_state_record_visible':('backend_visible','metadata_fence'),
'sector_grant':('directory_lookup','owner_grant','tag_allocate','CDC_request','backend_accept')}
def require(x,msg):
    if not x:raise ValueError(msg)
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def inputs():
    raw=(BASE/'input_manifest.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==PIN,'hard input manifest pin');result={}
    for row in json.loads(raw)['inputs']:
        p=(BASE/row['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'archive origin');v=p.read_bytes()
        require(len(v)==row['bytes'] and hashlib.sha256(v).hexdigest()==row['sha256'],'exact input hash');result[p.name]=v
    return result
def data(src,name):return json.loads(gzip.decompress(src[name]) if name.endswith('.gz') else src[name])
def protected(n):return math.ceil(n/64)*72
def lookup_profile(ingress):
    b=ingress['backend'];required=('REQ_PS','RSP_PS','CL_PS','BURST_PS','RCDRD_PS','RP_PS','RFC_PS')
    require(all(type(b[k])in(int,float) and math.isfinite(b[k]) and b[k]>0 for k in required),'positive explicit HBM source timing')
    # Deliberately serialized cold lookup: two real sector requests/returns.
    # Refresh and arbitrary contender waits are separate, not a claimed upper.
    sector=sum(b[k] for k in ('REQ_PS','RSP_PS','CL_PS','BURST_PS','RCDRD_PS','RP_PS'))/1000
    return dict(sector_read_ns_PROVISIONAL=sector,decode_FAST_edges=2,identity_FAST_edges=2,
        cold_serial_HBM_ns_PROVISIONAL=2*sector,cold_lookup_ns_PROVISIONAL=2*sector+4/1.2,
        hit_decode_match_ns_PROVISIONAL=4/1.2,refresh_episode_ns_PROVISIONAL=b['RFC_PS']/1000,
        finite_contender_wait_upper_ns=None,clock_target_hz=1200000000,hardware_admitted=False,
        scope='serialized model episode: request+closed-page+read+burst+return; no bank/refill/PHY receipt and no finite refresh/contender upper')
class DescriptorLookup:
    """Bounded 128-entry cache, actual two32B metadata reads.

    Directory offset is a software witness until a physical reservation/load
    receipt is paired. Returned bytes are metadata only, never numerical oracle.
    Cache fills retain immutable64B records; hits still pay decode/match.
    This fetch model returns protected bytes to the separate source decoder;
    latency charges do not themselves execute or qualify a hardware decoder.
    """
    def __init__(self,directory,sector_read_ns,decode_edges,match_edges,capacity=128):
        require(type(directory)is bytes and directory and len(directory)%64==0,'immutable fixed64B directory')
        require(type(sector_read_ns)in(int,float) and math.isfinite(sector_read_ns) and sector_read_ns>0,'positive HBM sector service')
        require(type(decode_edges)is int and decode_edges>0 and type(match_edges)is int and match_edges>0,'positive decode/match stages')
        require(type(capacity)is int and 1<=capacity<=128,'finite directory cache')
        self.raw=directory;self.cost=sector_read_ns;self.decode=decode_edges;self.match=match_edges;self.capacity=capacity;self.cache={};self.reads=0
    def lookup(self,index,occurrence):
        require(type(index)is int and 0<=index<len(self.raw)//64 and isinstance(occurrence,str) and occurrence,'exact source-order home index and event ID')
        hit=index in self.cache;events=[]
        if not hit:
            record=b''
            for sector in range(2):
                offset=index*64+sector*32;record+=self.raw[offset:offset+32];self.reads+=1
                events.append(dict(id=occurrence+f'.descriptor_sector{sector}',term='directory_HBM_read32B',bytes=32,directory_offset=offset,ns_PROVISIONAL=self.cost))
            if len(self.cache)==self.capacity:del self.cache[next(iter(self.cache))]
            self.cache[index]=record
        events.extend([dict(id=occurrence+'.decode',term='directory_decode',FAST_edges_PROVISIONAL=self.decode),dict(id=occurrence+'.match',term='directory_identity_match',FAST_edges_PROVISIONAL=self.match)])
        return dict(record=self.cache[index],hit=hit,events=events,physical_reservation_receipt=None,hardware_admitted=False)
def once(rows):
    """Merge cost occurrences supplied by calendar; never infer eligibility."""
    result={}
    for r in rows:
        require(set(r)=={'id','term','duration_ns','origin'},'cost occurrence ABI')
        require(isinstance(r['id'],str) and r['id'] and isinstance(r['term'],str) and r['term'],'concrete occurrence/term')
        require(type(r['duration_ns'])in(int,float) and math.isfinite(r['duration_ns']) and r['duration_ns']>0 and r['origin']=='provisional_model','mandatory positive model cost')
        require(r['id'] not in result or result[r['id']]==r,'same occurrence changed or double charged under different term')
        result[r['id']]=r
    total=sum(r['duration_ns'] for r in result.values());require(result and math.isfinite(total),'nonempty finite positive cost ledger')
    return dict(occurrences=len(result),serial_sum_ns_PROVISIONAL=total,finite_critical_path_upper_ns=None,hardware_admitted=False)
def outputs():
    src=inputs();pipe=data(src,'pipeline.json');ctx=data(src,'context.json');vias=data(src,'vias.json.gz');vh=data(src,'via_handoff.json');constructor=data(src,'constructor.json.gz');calendar=data(src,'calendar.json');authority=data(src,'authority.json');profile=lookup_profile(data(src,'ingress.json'))
    require(set(PHASES)==set(calendar['Qwen_KV_extension']['missing_phase_costs']),'exact21 emitted KV phases')
    homes={n:data(src,n+'_homes.json.gz') for n in ('Qwen','DS')};homes['Qwen']=homes['Qwen']['version_homes']
    directory={}
    for n,hs in homes.items():
        directory[n]=dict(entries=len(hs),HBM_reservation_bytes=len(hs)*64,miss_reads32B=2,miss_bytes=64,
            cold_all_entries_read_bytes=len(hs)*64,cold_all_entries_reads32B=len(hs)*2,
            missing_home_SM=sum('SM' not in h for h in hs),persistent_states=sum(h['home']['class']=='HBM_NATIVE_STATE' for h in hs),
            immutable_home_witness_sha256=hashlib.sha256(src[n+'_homes.json.gz']).hexdigest(),
            witness_not_a_free_physical_issuer=True,policy='runtime protected home descriptor; real requesting endpoint separate from offchip locality',
            physical_HBM_base=None,reservation_load_visibility_receipt=None,profile=profile)
    qwen=data(src,'Qwen_homes.json.gz');require(len(qwen['operations'])==1737,'actual1737 provider program')
    stage_edges={'directory_lookup':4,'owner_grant':2,'tag_allocate':1,'CDC_request':38,'backend_accept':1,'SRAM_read':2,'refill':1,'merge':1,'SRAM_write':1,'backend_visible':1,'completion_match':2,'completion_capture':1,'RF_pair_read':2,'RF_both_copy_write':1,'RF_common_ACK':1,'metadata_fence':1,'consumer':1,'child_reverse':2,'parent_reverse':2,'CDC_return':38,'credit_release':1}
    stages={k:dict(FAST_edges_PROVISIONAL=stage_edges[k],positive=True,ns_PROVISIONAL=stage_edges[k]/1.2,
        additional_HBM_miss_ns_PROVISIONAL=profile['cold_serial_HBM_ns_PROVISIONAL'] if k=='directory_lookup' else None,
        additional_HBM_refill_ns_PROVISIONAL=profile['sector_read_ns_PROVISIONAL'] if k=='refill' else None,
        decode_match_already_in_FAST_edges=k=='directory_lookup',
        CDC_receiver_sync_edges_each=2 if k in ('CDC_request','CDC_return') else None,
        required_source_authority='Dewey exact emitted event/hold and clock-domain receipts',finite_wait_upper_ns=None,installed_owner_admitted=False) for k in EVENTS}
    phase_join={k:dict(actual_occurrences=calendar['Qwen_KV_extension']['phase_counts'][k],required_terms=list(terms),
        occurrence_key_rule='actual emitted ID+term; same physical occurrence referenced by multiple phases is paid once',
        blanket_phase_count_product_is_not_an_interval_schedule=True) for k,terms in PHASES.items()}
    require(b'parameter integer NC=5' in src['PC.sv'],'actual five-client source PC arbiter')
    issuer_bits=128*protected(32+16+2+3+1+5)
    issuer_gates=128*(310+277+16+6+768)
    issuer_area=(issuer_bits*.2916+issuer_gates*.3)/.5/1e6
    allocations={};area=pipe['complete_unallocated_screen_upper_mm2_ASSUMED']+issuer_area;bits=pipe['complete_controller_bits_after_replacement']+issuer_bits;cut=2*1448
    for n in ('Qwen','DeepSeek'):
        a=ctx['models'][n]['area'];available=a['actual_reserved_strip_residual_um2_per_SM']*32/1e6
        allocations[n]=dict(SMs=32,existing_reserved_die_mm2=vias['models'][n]['full_reserved_die_mm2'],
            current_total_service_strip_residual_mm2=available,candidate_complete_bridge_screen_upper_mm2=area,
            conservative_additional_reservation_demand_mm2=max(0,area-available),
            candidate_cut_demand_per_SM_both_directions=cut,existing_min_local_margin_tracks=vh['models'][n]['minimum_local_margin_tracks'],
            conservative_uncredited_new_bus_margin_tracks=vh['models'][n]['minimum_local_margin_tracks']-cut,
            demand_replaces_old_route_only_after_exact_net_to_cut_map=True,known_existing_L2_cut_capacities=vh['models'][n]['corrected_L2_cut_capacities'],
            pipeline_cuts_to_L2_assignment=None,clock_PG_OBS_via_enlargement=None,old_ring_guard_um=2.088,
            strip_screen_fits=False,new_F0_allocation_admitted=False,source_geometry_reused_without_capacity_invention=True)
    cap=constructor['SS_clock_source_bounds']['actual_source_FF_CLK_capacitance_ff'];per_bit=max(cap.values());level=math.ceil(bits/32);clock_tree=[]
    while level>1:
        level=math.ceil(level/24);clock_tree.append(level)
    source_clock=constructor['models']['Qwen']['clock_source_allocations'][0]
    buffer_area=source_clock['incremental_buffer_footprint_um2']/(2*(source_clock['buffer_count']+source_clock['route_repeater_count']))
    clock_buffer_count=32*sum(clock_tree)+3 #32 SM roots require two fanout24 children and one root
    clock_area=clock_buffer_count*buffer_area*2/1e6
    for row in allocations.values():
        row['buffer_clock_connectivity_min_footprint_mm2']=clock_area
        row['complete_bridge_plus_clock_screen_mm2']=area+clock_area
        row['additional_area_demand_with_min_clock_mm2']=max(0,area+clock_area-row['current_total_service_strip_residual_mm2'])
    record=dict(schema='HBM_BRIDGE_COMPLETE_F0_R3',status='FAIL_F0_ALLOCATION_FINITE_CALENDAR_SOURCE_CONNECTION',
        source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in src.items()},runtime_directory=directory,
        directory_cache=dict(entries_per_PC=1,total_entries=128,coded_bits=128*protected(448),raw_record_bytes=64,
            capture_read32B=2,cache_hit_decode_and_identity_positive=True,eviction='source lease prevents eviction while referenced; executable directed cache used only between completed calls',
            active_metadata='homeID32/private immutable base64/span32/kind3/rankmask96/lifetime12+12; requesterSM from accepted endpoint',
            HBM_miss_cost_never_substituted_with_zero_decode=True),
        directory_issuer=dict(source_PC_clients=5,candidate_PC_clients=6,PC_replicas=128,
            source_PC_sha256=hashlib.sha256(src['PC.sv']).hexdigest(),new_live_home_tag_phase_counter_protected_bits=issuer_bits,
            mux_demux_match_ECC_gate_equivalents_ASSUMED=issuer_gates,incremental_footprint_mm2_ASSUMED=issuer_area,
            one_lookup_owner_per_PC_two_serial_sector_children=True,candidate_new_client_is_not_installed=True,
            original_PC_write_completion_owner_fix_still_required=True,actual_generic_client_to_PC_map=None),
        active_route_fields=dict(request={'data':256,'parent_tag':16,'sector_address':34,'length':6,'write':1},
            response={'data':256,'parent_tag':16,'beat':5},implicit='stack/PC by physical port; exact rank-to-die/W19 ownership map required',
            homeID_and_original_client_tag='private protected root mapping; namespace proof still required',
            no324bit_wire_identity=True,actual_literal_Qwen_provider_PC_count=len(qwen['operations']),actual_Qwen_opcode_classes=len({op['opcode'] for op in qwen['operations']}),
            requester_not_offchip_home_SM=True,DS_persistent_home_missing_SM_not_fabricated=True),
        pipeline=pipe,ports=dict(HBM_directory_miss_read32B=2,directory_lookup_per_PC_per_accept=1,
            RF_local_write_bits=4096,RF_local_both_mirrors_accept_bits=8192,RF_local_pair_read_bits=8192,
            shared_read_write_bytes=64,shared_physical_256bit_banks=2,partial_RMW_requires_old_capture_and_mask_merge=True,
            route_directions=2,route_lanes_per_SM=4,route_replicas_per_direction=128,held_route_source_II_FAST_edges=40,candidate_steady_pipeline_II=1,
            source_common_ACK_events_per_RF_write=1,RF_both_copy_write_events=1,all_replicas_mux_demux_fanout_cost_in_pipeline_screen=True),
        positive21_stage_inventory=stages,actual21_KV_phase_join=phase_join,
        RF_CDC_source_bindings=pipe['connected_cost_source_bindings'],F0_allocations=allocations,
        clock=dict(target_FAST_hz=1200000000,serial_hz=900000000,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
            worst_source_SS_FF_CLK_capacitance_ff=per_bit,complete_control_FF_bits_screen=bits,
            incremental_full_control_clock_load_ff_ASSUMED=bits*per_bit,
            fanout24_buffer_levels_per_SM_connectivity_min=clock_tree,SM_root_replicas=32,root_tree_buffer_count_min=3,
            buffer_instances_connectivity_min=clock_buffer_count,
            selected_buffer=source_clock['selected_buffer'],buffer_TT_geometric_area_um2=buffer_area,
            buffer_connectivity_min_footprint_mm2=clock_area,route_repeater_count_without_new_route_lengths=None,
            all_control_bits_clocked_bound_is_screen_not_extracted_netlist=True,
            reusing_existing_clock_tree_not_credited=True,buffer_source_table=constructor['SS_clock_source_bounds'],
            new_clock_PG_OBS_via_cuts=None,qualified_skew_slew_hold=False),
        owner_lifecycle='descriptor issue/capture -> grant/tag -> producer/backend acceptance -> bothcopies/commonACK -> visibility -> consumer -> matched child reverse -> parent reverse -> credit release',
        finite_sink_backpressure='candidate two seats per38hop lane;76 held beats/lane; does not bound downstream wait or release parent',
        authority_R4=dict(schema=authority['schema'],program_sha256=authority['exact_program']['sha256'],
            exact_program_ops=authority['exact_program']['operations'],legacy_to_actual_PC_equivalence=False,
            selected_FETCH_already_paid=True,no_automatic_delta=True),
        calendar=dict(source_actual_PC0_transactions=calendar['actual_PC0_transactions'],actual_PC0_sha256=calendar['actual_PC0_journal_sha256'],
            exact_KV_21phase_counts_reused=True,actual_event_interval_receipts=None,whole_operator_ns=None,whole_token_ns=None),
        hardware_admitted=False,engine_build_allowed=False,source_footprint_inventory_complete_but_allocation_FAIL=True)
    return {'model.json':canonical(record),'Dewey_21event_F0_contract.json':canonical(dict(stages=stages,phases=phase_join,directory_profile=profile,scope='model proposals and exact phase inventory, not actual finite interval receipts',hardware_admitted=False))}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
    for n,v in outputs().items():
        if a.verify:require((BASE/n).read_bytes()==v,'exact F0 replay '+n)
        else:
            require(a.output is not None,'explicit output');a.output.mkdir(parents=True,exist_ok=True);(a.output/n).write_bytes(v)
    print('PASS bridge F0 directory,21events and complete allocation refusal replay; hardware FAIL')
if __name__=='__main__':main()
