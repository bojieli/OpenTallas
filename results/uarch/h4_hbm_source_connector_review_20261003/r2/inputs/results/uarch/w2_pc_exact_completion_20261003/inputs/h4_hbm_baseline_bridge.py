#!/usr/bin/env python3
"""Frozen mandatory comparator owner/ACK/CDC implementation model.
No engine RTL is emitted before full composed G0 admission.
"""
import argparse,gzip,hashlib,json,math
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_baseline_bridge_20261003'
PIN='719d763c5f8699458cd03774d8b5a2b7bdeda7721bd0157dcca23f9f6a9eb491'
EVENTS=('directory_lookup','owner_grant','tag_allocate','CDC_request','backend_accept','SRAM_read','refill','merge','SRAM_write','backend_visible','completion_match','completion_capture','RF_pair_read','RF_both_copy_write','RF_common_ACK','metadata_fence','consumer','child_reverse','parent_reverse','CDC_return','credit_release')
FIELDS=(('id',32),('reference',32),('base',64),('span',32),('birth',12),('retire',12),('ranks',96),('SM',5),('kind',3),('words',32),('flags',8))
def require(x,msg):
    if not x:raise ValueError(msg)
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def inputs():
    raw=(BASE/'input_manifest.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==PIN,'hard manifest pin');out={}
    for r in json.loads(raw)['inputs']:
        p=(BASE/r['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'archive origin containment');v=p.read_bytes()
        require(len(v)==r['bytes'] and hashlib.sha256(v).hexdigest()==r['sha256'],'exact archived input');out[p.name]=v
    return out

DATA_POSITIONS=tuple(pos for pos in range(1,72) if pos&(pos-1))
BYTE_ENCODE=tuple(tuple(sum(((value>>bit)&1)<<(DATA_POSITIONS[byte*8+bit]-1) for bit in range(8)) for value in range(256)) for byte in range(8))
PARITY_MASKS=tuple(sum(1<<(pos-1) for pos in range(1,72) if pos&parity) for parity in (1,2,4,8,16,32,64))
def secded64(value):
    require(type(value)is int and 0<=value<2**64,'64bit codeword')
    code=sum(BYTE_ENCODE[byte][(value>>(byte*8))&255] for byte in range(8))
    for parity,mask in zip((1,2,4,8,16,32,64),PARITY_MASKS):code|=((code&mask).bit_count()&1)<<(parity-1)
    return code|((code.bit_count()&1)<<71)

def decode_home(raw,*,rank,SM,PC):
    require(type(raw)is bytes and len(raw)==64 and raw[-1]==0,'fixed protected home record')
    bits=0
    for i in range(7):
        code=int.from_bytes(raw[i*9:i*9+9],'little');syndrome=0
        for parity,mask in zip((1,2,4,8,16,32,64),PARITY_MASKS):
            if (code&mask).bit_count()&1:syndrome|=parity
        odd=code.bit_count()&1
        if syndrome:
            require(odd and syndrome<=71,'uncorrectable metadata ECC');code^=1<<(syndrome-1)
        elif odd:code^=1<<71
        value=sum(((code>>(pos-1))&1)<<j for j,pos in enumerate(DATA_POSITIONS));bits|=value<<(64*i)
    out={};shift=0
    for name,width in FIELDS:out[name]=(bits>>shift)&((1<<width)-1);shift+=width
    require(out['flags']&7==7,'source SM/retirement missing; physical lifetime admission refused')
    require(type(rank)is int and 0<=rank<96 and out['ranks']&(1<<rank),'source rank ownership')
    require(type(SM)is int and out['SM']==SM,'actual SM directory binding')
    require(type(PC)is int and 0<=PC<4095,'documented program PC')
    require(out['birth']==4095 or out['birth']<=PC,'source producer not live')
    require(out['retire']==4095 or PC<=out['retire'],'source lifetime expired; no alias waiver')
    return out

def encode_home(home,index,model):
    h=home['home'];kind={'RF':0,'spill':1,'HBM_NATIVE_STATE':2}.get(h['class']);require(kind is not None,'documented directory kind')
    ranks=[home['rank']] if model=='Qwen' else home['rank_group']
    require(ranks and len(set(ranks))==len(ranks) and all(type(r)is int and 0<=r<96 for r in ranks),'exact rank mask')
    base=h['slot_first'] if kind==0 else h.get('global_byte_base',h.get('base'))
    span=h['vectors']*512 if kind==0 else h['bytes']
    if kind==0:require(0<=base<512 and base+h['vectors']<=512,'source RF vector aperture')
    birth=home.get('birth_pc',home.get('binding',{}).get('PC'));require(birth is not None,'source producer PC')
    retire=home.get('retire_pc');sm=home.get('SM')
    flags=int(sm is not None)|(int(retire is not None)<<1)|(1<<2)
    vals=dict(id=index+1,reference=index+1,base=base,span=span,birth=birth if birth>=0 else 4095,
        retire=retire if retire is not None and retire>=0 else 4095,ranks=sum(1<<r for r in ranks),SM=sm if sm is not None else 0,kind=kind,words=home['word_count'],flags=flags)
    bits=0;shift=0
    for name,width in FIELDS:
        v=vals[name];require(type(v)is int and 0<=v<1<<width,'bounded home '+name);bits|=v<<shift;shift+=width
    require(shift<=448,'seven protected64bit words')
    raw=b''.join(secded64((bits>>(64*i))&((1<<64)-1)).to_bytes(9,'little') for i in range(7))+b'\x00'
    return raw

def dictionaries(src):
    result={};stats={}
    for name in ('Qwen','DS'):
        data=json.loads(gzip.decompress(src[name+'_homes.json.gz']));homes=data['version_homes'] if name=='Qwen' else data
        payload=b''.join(encode_home(h,i,name) for i,h in enumerate(homes));result[name+'_directory.bin.gz']=gzip.compress(payload,mtime=0)
        stats[name]=dict(entries=len(homes),source_order_preserved=True,unique_versions=len({h['version'] for h in homes}),
            exact_source_sha256=hashlib.sha256(src[name+'_homes.json.gz']).hexdigest(),descriptor_payload_bits=sum(w for n,w in FIELDS),
            descriptor_bytes=64,dictionary_bytes=len(payload),directory_sectors=len(payload)//32,
            rows_missing_source_SM=sum('SM' not in h for h in homes),rows_missing_source_retirement=sum('retire_pc' not in h for h in homes),
            unknown_field_flags_require_refusal_not_zero_latency=True,protected_bits=7*72*len(homes),dictionary_payload_sha256=hashlib.sha256(payload).hexdigest(),
            residence='bounded HBM descriptor table; physical reservation/initialization receipt required, no invented base',
            directory_base=None,lookup_miss_reads32B=2,lookup_hit='resident live owner descriptor; no zero-cost claim',
            per_request_use='compiler supplies exact source-order home ID; rank/SM/kind/range/lifetime checked before acceptance',
            final_actual_runtime_directory_admitted=False)
    return result,stats

def protected(bits):return math.ceil(bits/64)*72

def model(src,stats):
    audit=json.loads(src['hbm_owner_ack_gaps.json']);calendar=json.loads(src['emitted_calendar_summary.json']);old=json.loads(src['predecessor_model.json'])
    require('assign commit_ready=0' in src['provider.sv'].decode(),'preserve audited disabled-branch defect')
    require('ack_valid<=1' in src['RF.sv'].decode() and 'ack_ready' in src['RF.sv'].decode(),'common held ACK source')
    require('p_wr_done_rdy' not in src['PC.sv'].decode(),'baseline lacks completion ready')
    # All packets carry the owner tuple; packet payload never implies retirement.
    identity={'generation':64,'lease':64,'sequence':40,'physical_tag':35,'rank':7,'SM':5,'address':64,'provider_reference':32,'home_id':32,'write':1}
    ident=sum(identity.values());widths={'request':ident+256+32+10+3,'read_return':ident+256+2,'write_completion':ident+2,'reverse':ident+2}
    lanes={}
    for name,w in widths.items():
        # Actual bridge: two FIFO2 memories (4 words), route packet (1word),
        # twoFIFO control26bits each and route control7bits. Protect all state.
        lanes[name]=dict(width_bits=w,replicas=128,FIFO2_per_lane=2,route_words_per_lane=1,
            source_unprotected_bits_per_lane=5*w+59,protected_state_bits_per_lane=5*protected(w)+3*protected(26),
            route_FAST_edges=38,minimum_route_ns_at1p2GHz=38/1.2,
            source_fifo_control_bits=26,source_route_control_bits=7,valid_ready_bits=2,
            max_payload_bytes_per_accept=32 if name in ('request','read_return') else 0,
            acceptance_gap_upper_ns=None,consumer_wait_upper_ns=None,CDC_synchronizer_MTBF_admitted=False,
            selected_route_geometry_for_new_width=False)
    cdc_bits=sum(v['replicas']*v['protected_state_bits_per_lane'] for v in lanes.values())
    gate_payload=64+40+7+5+64+32+32+1+32+3+3+1
    gate_entries=32+32+32
    gates=gate_entries*(protected(gate_payload)+protected(3))
    queue_bits=6*32*(protected(gate_payload+4096)+protected(gate_payload+512)+protected(gate_payload+256))
    ack_bits=64*protected(ident+10+2)
    fill_bits=32*protected(ident+256+32+4+4+3) # one fixed pending fill/RMW word per actual selected bank
    cache_bits=128*96*protected(448) # finite decoded home row per live context; replaces no unbounded lookup
    added=cdc_bits+gates+queue_bits+ack_bits+fill_bits+cache_bits
    words=added//72;ecc_gates=words*768
    mux_gates=2*queue_bits+3*gate_entries*gate_payload+128*96*448
    footprint=(added*.2916+(ecc_gates+mux_gates)*.3)/.5/1e6
    total_area=old['footprint_mm2_per_die_ASSUMED']+footprint
    contexts={k:dict(retained_reserved_die_mm2=v['retained_reserved_die_mm2'],baseline_bridge_unallocated_area_mm2_ASSUMED=total_area,
        retained_plus_bridge_screen_mm2=v['retained_reserved_die_mm2']+total_area,
        existing_cut_count=v['retained_cut_count'],retained_SMs=v['retained_SMs'],new_clock_sinks=old['storage_bits_per_die']+added,
        new_clock_PG_via_allocation=None,new_bus_cut_capacity=None,fit=False) for k,v in old['physical']['source_bound_retained_context'].items()}
    node_defs=[
      ('G0_SOURCE',[''],'freeze exact audit, home directories, ABI and complete resources'),
      ('G0_CALENDAR',['G0_SOURCE'],'Dewey: actual emitted contenders/leases and all21 costs, reused IDs once-only'),
      ('G0_PHYSICAL',['G0_SOURCE','G0_CALENDAR'],'selected full32SM slot/macro/OBS/clock/PG/via/cuts and proposed stage feasibility'),
      ('W1',['G0_SOURCE'],'new uniquely named provider hygiene successor; commit_r=0 disabled branch; pinned original preserved'),
      ('W2',['G0_PHYSICAL'],'PC successor exact reserved tag-generation capture; fault gates grants; held c_wr_done_ready'),
      ('W3',['G0_PHYSICAL','W1','W2'],'r14 successor matching live read/write generation credit, not unmatched read grant'),
      ('W4',['G0_PHYSICAL'],'RF successor registers owner/gen at common two-copy write_go, held identity ACK'),
      ('W5',['G0_PHYSICAL'],'96endpoint owner gate, six traffic contenders; held lease and cursor advances on reverse'),
      ('W6',['W4','W5'],'owner-bearing visibility, consumer and reverse ports; no8bit epoch alias'),
      ('W8',['W2','W3','W5','W6'],'valid-old-sector/refill mask merge and bitmap-before-record under writer exclusion'),
      ('W9',['W5','W6'],'generic L2 bank owner/word capture, line validity fence; GU Qwen-only'),
      ('W10',['W2','W3','W4','W5','W6'],'four comparator CDC lanes, paired source/destination receipts, reset quiescence'),
      ('W7',['W8','W9','W10'],'connected endpoint_trace replay; software ACK is not observed source ACK'),
      ('W11',['W7'],'source bound acceptance/consumer/credit wait then contextual SS/FF verification'),
      ('W12',['W5','W10','W11'],'actual emitted finite contention reachability; installed fair policy if exhaustion proof absent'),
      ('W13',['W7','W11','W12'],'reconcile each historical zero placeholder with existing receipt interval or positive new cost'),
      ('DS_CONNECT',['W2','W4','W5','W6','W9','W10'],'instantiate same generic bridge for DS; no Qwen/GU connection credit transferred'),
      ('BASELINE_GATE',['W13','DS_CONNECT'],'both comparator connected trace, bounded operator calendars and complete-context SS/FF')]
    graph=[]
    audit_work={w['id']:w for w in audit['work_items']}
    for name,deps,action in node_defs:
        graph.append(dict(id=name,depends_on=[d for d in deps if d],action=action,
            owner='Dewey' if name=='G0_CALENDAR' else 'Popper_source_physical',mandatory_baseline=True,
            implementation_done=False,gates=audit_work.get(name,{}).get('gates',[])))
    return dict(schema='HBM_BASELINE_OWNER_ACK_CDC_FROZEN_G0_R1',frozen=True,
        classification='mandatory baseline integration; generic GPU owner control, no ROM-specific novelty',
        performance_opt_in=False,source_successors_separate_from_pinned_originals=True,
        status='FROZEN_DESIGN_FAIL_COMPOSED_CALENDAR_AND_PHYSICAL_ALLOCATION',
        source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in src.items()},audit_main=audit['main'],
        default_off_bug=dict(original_sha256=hashlib.sha256(src['provider.sv']).hexdigest(),
            successor_fix='assign commit_r=0 instead of undeclared commit_ready=0; uniquely named additive module',
            added_state_bits=0,added_clock_load=0,added_active_path_logic=0,reason='correct existing intended off-branch constant driver; enabled branch unchanged',
            installed_fix=False,hygiene_lint_is_not_engine_or_context_admission=True),
        common_RF_ACK=dict(identity_fields=identity,payload_bits=ident+10+2,held_owner_entries=64,
            mirrors='one common ACK covers both source write copies; never two independently timed ACKs',
            owner_captured_on='actual source write_go edge; one source commonACK handshake releases local accepted command',
            consumer_reverse='commonACK does not release parent lease; visibility->consumer->reverse remain mandatory',new_state_bits=ack_bits),
        directory_schema=dict(fields=FIELDS,SECDED='64data+8checkbits,7codewords plus1paddingbyte per64B descriptor',
            source_strings_and_archive_hashes='compile-time provenance only; fixed IDs and protected bounded table required',
            actual_source_statistics=stats,decoded_live_row_cache_entries=12288,decoded_live_row_cache_bits=cache_bits,
            physical_HBM_reservation=None,load_visibility_receipt=None,directory_port32B_reads_per_miss=2),
        owner_gate=dict(SMs=32,logical_RF_owners=32,logical_shared_owners=32,shared_physical_banks_held_together=64,
            selected_L2_banks=32,endpoint_entries=gate_entries,contenders=['C0','SIMD','matrix','KV_read','KV_write','L2'],
            six_one_entry_queues_per_endpoint=True,owner_state_bits=gates,queue_bits=queue_bits,
            cursor_policy='advance only after matching reverse grant; eligibility and wait gaps must come from emitted calendar',
            phase='grant->SRAM accept/capture->commonACK->visibility->consumer->reverse',gate_is_not_external_grant_bit=True,
            fairness_installed=False,DS_production_instantiation=False),
        CDC=dict(identity_fields=identity,lanes=lanes,protected_bits=cdc_bits,
            source_reset='either reset flushes both domains; new generation resumes only with external quiescence/ownership invalidation',
            target_domains=dict(SM_stream_GHz=1.2,HBM_service_GHz=1.2,serial_chain_GHz=.9),
            target_frequency_is_not_measured_closure=True,forward_and_reverse_edge_ordinals_required=True),
        refill_metadata=dict(finite_pending_entries=32,new_state_bits=fill_bits,oldsector_validity_not_implicit_zero=True,
            dictionary_lookup_miss_scheduled_with_real_HBM_clients=True,full_sector_mask_merge=True,
            release='backend write visibility then consumer and matching reverse; payload bitmap before producer record',
            existing_L2_macro_capacity_not_expanded=True,new_controller_reservation=None),
        resource_ledger=dict(predecessor_completion_owner_bits=old['storage_bits_per_die'],bridge_additional_bits=added,
            total_protected_state_bits_per_die=old['storage_bits_per_die']+added,ECC_gate_equivalents_ASSUMED=ecc_gates,
            mux_gate_equivalents_ASSUMED=mux_gates,total_unallocated_area_mm2_per_die_ASSUMED=total_area,
            FF_um2_ASSUMED=.2916,gate_um2_ASSUMED=.3,utilization_ASSUMED=.5,
            conservative_envelope_not_area_optimized=True,predecessor_reuse_not_double_charged=True,HBM_dictionary_bytes_not_counted_as_FFs=True),
        ports_routes=dict(PC_lanes=128,SM_endpoints=32,local_RF_write_bits=4096,local_RF_read_pair_bits=8192,
            shared_bits=512,L2_word_bits=256,owner_messages_bits=ident,CDC_cut_widths={k:v['width_bits']+2 for k,v in lanes.items()},
            RF_ACK_cut_width_bits=ident+10+2+2,gate_state_read_ports=1,gate_state_write_ports=1,
            directory_capture_ports_per_PC=1,completion_capture_ports_per_PC=dict(read=1,write=1),
            tracks_required_by_cut=None,actual_PG_clock_via_exclusions_charged=False),
        full_context=contexts,latency=dict(required_positive_events=list(EVENTS),
            proposed_logic_stages=dict(directory_decode=2,owner_match=2,ACK_capture=1,ACK_match=2,fence=1,consumer=1,reverse_match=2,release=1),
            route_FAST_edges_per_CDC=38,backpressure_waits_ns=None,whole_operator_critical_path_ns=None,whole_token_ns=None,
            no_placeholder_zero_duration_retire=True,existing_ID_reuse_requires_source_receipt=True,
            costs_are_proposals_not_installed_SS_FF=True),
        emitted_calendar_join=dict(source_sha256=hashlib.sha256(src['emitted_calendar_summary.json']).hexdigest(),
            actual_phase_counts=calendar['Qwen_KV_extension']['phase_counts'],missing_physical_phase_costs=calendar['Qwen_KV_extension']['missing_phase_costs'],
            actual_PC0_transactions=calendar['actual_PC0_transactions'],actual_PC0_journal_sha256=calendar['actual_PC0_journal_sha256'],
            source_resolved_DS_scope=calendar['DS_retained_shared_source_join'],existing_interval_reuse_not_proven=True),
        historical_zero_cost_findings=audit['zero_cost_flags'],implementation_dependency_graph=graph,
        prerequisites=['actual emitted finite owner/operator calendar, all positive21cost terms and exact reused interval IDs',
            'descriptor table actual source-controlled reservation/load and lifetime handshake',
            'complete-context owner/storage/ports/cuts/clock/PG/OBS allocation and protected logic stage timing'],
        installed_source=False,hardware_admitted=False,engine_build_ready=False)

def consumer_delta(src):
    ingress=json.loads(src['ingress_model.json']);audit=json.loads(src['hbm_bridge_dependency_and_fields.json'])
    perf=ingress['performance'];service=perf['selected_service_ceiling_Bpc'];worst=perf['loaded_round_trip_cycles']+perf['worst_jitter_cycles']
    # Keep original source tags in context, not on all hardware boundaries.
    fields=dict(valid=1,write=1,generation=4,client=3,SM=5,rank=7,original_tag=32,home_id=32,
        home_offset=32,byte_count=32,physical_sector=34,physical_stack=2,RF_slot=9,phase=3,captured=1,reverse_seen=1)
    rowbits=protected(sum(fields.values()));metadata=128*6*16*rowbits
    capture=128*protected(35+256+1)+128*protected(96)
    directories=128*protected(448)
    gate=32*protected(30)+32*protected(58)
    common_ACK=32*protected(16+9+1);fence=32*protected(3)
    widths=dict(request=4*(34+16+6+1+256),read_return=4*(16+5+256),write_completion=16+5+2,reverse=16+5+2)
    fifo={k:dict(payload_bits_per_entry=w,depth=16,replicas=32,protected_data_bits=32*16*protected(w),
        source_control_bits_per_FIFO16_candidate=50,protected_control_bits=32*protected(50),
        qualification='new FIFO16 implementation, not installed FIFO2 credit') for k,w in widths.items()}
    fifo_bits=sum(r['protected_data_bits']+r['protected_control_bits'] for r in fifo.values())
    # The actual route cannot accept one packet everyedge. Throughput pipeline
    # is separately priced, never transferred from the old held register.
    pipeline_bits=32*38*(protected(widths['request'])+protected(widths['read_return'])+2*protected(4))
    rmw_bits=32*protected(256+32+16+4+3)
    data_bits=metadata+capture+directories+gate+common_ACK+fence+fifo_bits+pipeline_bits+rmw_bits
    # ECC shared at three context reads/one contextwrite and FIFO read/write,
    # instead of one decoder per every quiescent FF codeword.
    ecc_gates=128*4*math.ceil(sum(fields.values())/64)*768+32*2*sum(math.ceil(w/64)*768 for w in widths.values())
    mux_gates=128*3*95*rowbits+2*fifo_bits+32*5*(30+58)
    area=(data_bits*.2916+(ecc_gates+mux_gates)*.3)/.5/1e6
    return dict(schema='HBM_ACTUAL_CONSUMER_FIELD_CDC_DELTA_R1',audit_main=audit['main'],generic324bit_identity_rejected=True,
        physical_tag_candidate_bits=16,software_generation64_sequence40_lease64_provenance_refs_are_not_wire_fields=True,
        fields_remain_private_context=fields,protected_PC_context_bits=metadata,
        original_source_tag32_is_retained=True,source_bulk_ring=dict(depth1024=True,outstanding512=True,tag10=True,return_ready=False,exact_completion_validation=False),
        tag_namespaces=['PC {client3,SM5,slot4,generation4}=16; namespace implicit at PC lane',
            'coalescer {client6,batch_slot6,generation4}=16; NOT the same numeric identity',
            'SM line ring needs original10bit slot plus generation; source ring lacks matching/ready'],
        required_maps='PC exact live context->coalescer original line->SM ring; map complete BEFORE SM CDC, do not dropPC when aggregating',
        source_KV_RMW=dict(actual_partial_sector_mask_merge_count=json.loads(src['emitted_calendar_summary.json'])['Qwen_KV_extension']['phase_counts']['KV_sector_mask_merge'],
            fullhead128B_RMW_avoidance_not_transferred=True,reason='actual source strided partialsector requests preserve neighboring bytes; wholehead packing is another source change'),
        onebit_generation_not_admitted=True,generation_reason='requires all forward/completion/commonACK/consumer/reverse copies drained before slot reuse; current source has no such composite proof',
        minimal_20bit_claim='selected reduced key only, not sufficient for generic current32bit client tags, rank-multiplexed homes or source bulk ring512outstanding',
        W2_table3bit_lower=128*6*16*3,complete_PC_metadata_bits=metadata,read_capture_bits=capture,
        common_RF_ACK='one identity-bearing combined copy ACK, not two mirror events',common_ACK_bits=common_ACK,
        compact_gate_bits=gate,local_gate_fields=dict(tag=16,phase=3,valid=1,write=1,client_class=3,common_ACK=1,consumer_seen=1,reverse_pending=1,endpoint_kind=2,fault=1),
        bank_gate_fields=dict(tag=16,word_offset=13,client_class=3,phase=3,valid=1,endpoint_kind=2,nwords=2,word_valid_mask=4,parent_beat=5,parent_generation=4,remaining_words=3,ACK=1,reverse=1),
        cache_RMW_pending_bits=rmw_bits,fence_bits=fence,decoded_directory_capture_bits=directories,
        FIFO_candidate=fifo,pipelined_route_candidate_bits=pipeline_bits,total_candidate_bits=data_bits,
        candidate_FF_mux_ECC_area_mm2_ASSUMED=area,area_is_screen_only=True,
        existing_ingress_gather_MACRO_area_mm2_ASSUMED=ingress['area']['additional_data_SRAM_footprint_mm2'],
        existing_ingress_gather_not_credited_as_installed=True,
        source_route=dict(EDGES=38,single_owned=True,minimum_packet_acceptance_spacing_FAST_edges=40,
            same_edge_release_and_reaccept=False,ceiling32SM_1lane_Bpc=32*32/40,ceiling128PC_1lane_Bpc=128*32/40,
            cannot_replace_with_one_entry_per_cycle=True),
        service=dict(source_ceiling_Bpc=service,priced320bit_FIFO_payload_Bpc_equalclock=1024,
            priced320bit_FIFO_fraction_equalclock=1024/service,priced320bit_FIFO_payload_Bpc_3to4=768,
            priced320bit_FIFO_fraction_3to4=768/service,candidate4lane_payload_Bpc_3to4=3072,
            candidate4lane_payload_Bpc_equalclock=4096,full128B_line_return_requires_four32B_sector_lanes=True,
            proposed_depth16_does_not_prove_contender_wait=True),
        credit=dict(installed_PC_accepted_slots=128*6*16,conditional32B_slot_Bpc_upper=128*6*16*32/worst,
            conditional128B_line_slot_Bpc_upper=128*6*16*128/worst,
            minimum_sector_slots_per_client_PC=math.ceil(service*worst/(128*6*32)),
            minimum_line_slots_per_client_PC=math.ceil(service*worst/(128*6*128)),
            source_bulk_512line_SM_capacity_Bpc=32*512*128/worst,
            source_backend_loaded_plus_jitter_FAST_edges_PROVISIONAL=worst,
            no_wholeprogram_service_rate_until_slot_unit_and_root_line_maps_connected=True),
        address_mapping=dict(legacy_PC_service='PC selects address low7 bits',physical_provider='r17 fourstack stripe and pc_of mapping use fullphysical source address; must not substitute legacy low7 selector',
            concrete_translate_and_retained_original_address_required=True,qualified=False),
        critical_path=dict(proposed_forward_reverse_route_FAST_edges=76,proposed_route_pair_ns_at1p2GHz=76/1.2,
            route_component_may_overlap_existing72wire_edges_only_with_emitted_ID_receipt=True,incremental_route_ns=None,priced_one_lane_transfer_lower_bound_ratio_equalclock=service/1024,
            priced_one_lane_transfer_lower_bound_ratio_3to4=service/768,
            reused_held_route_transfer_ratio_128PC=service/(128*32/40),
            visibility_consumer_reverse_min_NEW_edges=2,onebit_or_zero_added_match_stage_not_SS_FF_qualified=True,
            proposed_owner_match_edges=1,proposed_commonACK_match_edges=1,proposed_credit_release_edges=1,
            CDC_forward_and_reverse_finite_wait_upper=None,whole_operator_ns=None,whole_token_ns=None),
        source_constraints=['actual source mapping from PC completion to each line/SM consumer',
            'Dewey exact returned-line/sector eligibility, leases and finite contend/hold intervals',
            'rank and original32bit client tags cannot be discarded without source compiler/consumer contract',
            'new FIFO16 and throughput pipeline must fit actual clock/PG/via/widened cuts before W10RTL'],
        W10_RTL_admitted=False,hardware_admitted=False)

def corrected_graph(old):
    by={r['id']:dict(r) for r in old}
    by['F0']=dict(id='F0',depends_on=['G0_SOURCE'],action='actual consumer field/namespace widths; no software324bit physical identity assumption',owner='Popper_source_physical',mandatory_baseline=True,implementation_done=False,gates=[])
    by['G0_CALENDAR']['depends_on']=['F0']
    by['W2']['depends_on']=['F0','G0_PHYSICAL']
    by['W4']['depends_on']=['F0','G0_PHYSICAL']
    by['W6']['depends_on']=['F0','G0_PHYSICAL'];by['W6']['action']='standalone identity fence ports first; instantiate behind gate in W5, breaksW5/W6 cycle'
    by['W5']['depends_on']=['W2','W4','W6','G0_PHYSICAL']
    by['W10']['depends_on']=['W2','W6','G0_PHYSICAL']
    order=['G0_SOURCE','F0','G0_CALENDAR','G0_PHYSICAL','W1','W2','W3','W4','W6','W5','W8','W9','W10','W7','W11','W12','W13','DS_CONNECT','BASELINE_GATE']
    return [by[k] for k in order]

def outputs():
    src=inputs();data,stats=dictionaries(src);m=model(src,stats);delta=consumer_delta(src)
    m['unadopted_wide_tuple_screen']=dict(state_bits=m['resource_ledger']['total_protected_state_bits_per_die'],area_mm2=m['resource_ledger']['total_unallocated_area_mm2_per_die_ASSUMED'],selected=False)
    m['actual_consumer_delta']=delta;m['implementation_dependency_graph']=corrected_graph(m['implementation_dependency_graph'])
    m['latency']['positive_elapsed_costs_not_replaced_by_edgefree_compare']=True
    m['physical_identity_selected']='16bit namespace-specific context ID candidate; maps/protocol not yet admitted, never software tuple'
    m['resource_ledger']=dict(candidate_control_bits=delta['total_candidate_bits'],candidate_FF_mux_ECC_area_mm2_ASSUMED=delta['candidate_FF_mux_ECC_area_mm2_ASSUMED'],
        candidate_FIFOs_and_throughput_pipeline_included=True,source_metadata_strings_not_live_Hardware=True,HBM_dictionaries_included_separately=True,screen_only=True)
    m['CDC']=dict(candidate=delta['FIFO_candidate'],source_held_route=delta['source_route'],pipeline_candidate_bits=delta['pipelined_route_candidate_bits'],
        full_fixed_software_identity_not_sent=True,admitted=False)
    m['directory_schema']['decoded_live_row_cache_entries']=128;m['directory_schema']['decoded_live_row_cache_bits']=128*protected(448)
    m['owner_gate']['endpoint_entries']=64;m['owner_gate']['logical_shared_owners']=32;m['owner_gate']['shared_and_RF_hold_one_local_SM_lease']=True
    m['owner_gate']['local_entry_fields']=delta['local_gate_fields'];m['owner_gate']['bank_entry_fields']=delta['bank_gate_fields']
    m['owner_gate']['owner_state_bits']=delta['compact_gate_bits'];m['owner_gate']['queue_bits']=None
    m['owner_gate']['six_one_entry_queues_per_endpoint']=False;m['owner_gate']['source_validthroughready_required']=True
    m['common_RF_ACK']['payload_bits']=16+9+1;m['common_RF_ACK']['identity_fields']={'context_tag':16,'RF_slot':9,'common_copy_ACK':1};m['common_RF_ACK']['new_state_bits']=delta['common_ACK_bits']
    m['ports_routes']['CDC_cut_widths']={k:v['payload_bits_per_entry']+2 for k,v in delta['FIFO_candidate'].items()}
    m['ports_routes']['owner_messages_bits']=16;m['ports_routes']['RF_ACK_cut_width_bits']=28
    m['refill_metadata']['new_state_bits']=delta['cache_RMW_pending_bits']
    for c in m['full_context'].values():
        c['baseline_bridge_unallocated_area_mm2_ASSUMED']=delta['candidate_FF_mux_ECC_area_mm2_ASSUMED'];c['retained_plus_bridge_screen_mm2']=c['retained_reserved_die_mm2']+delta['candidate_FF_mux_ECC_area_mm2_ASSUMED'];c['new_clock_sinks']=delta['total_candidate_bits']
    m['latency']['controller_cost_keys_are_not_identical_to_actual_KV_phase_cost_keys']=True
    data['model.json']=canonical(m);data['implementation_graph.json']=canonical(m['implementation_dependency_graph']);data['consumer_delta.json']=canonical(delta);return data

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args();data=outputs()
    if a.verify:
        for n,v in data.items():require((BASE/n).read_bytes()==v,'byte-exact frozen replay '+n)
        print('PASS frozen model, implementation graph and both protected home dictionaries')
    else:
        require(a.output is not None,'explicit output');a.output.mkdir(parents=True,exist_ok=True)
        for n,v in data.items():(a.output/n).write_bytes(v)
if __name__=='__main__':main()
