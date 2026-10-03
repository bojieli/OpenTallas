#!/usr/bin/env python3
"""Pin peer ledgers and compose additive W2 records; all results are model unvalidated."""
import argparse, collections, gzip, hashlib, json, math, subprocess
from pathlib import Path
from dsrom_s73_pair1 import ROOT, BASE, PIN, save, digest
import dsrom_return_storage_hbm as B
import dsrom_full_owner_compiler as C

W4='d1b6dd52a'
W3='7c5b6a79b'
W1='046bf5026'

def build(out,maproot=BASE/'baseline_s82_successor_r1'):
    out.mkdir(parents=True,exist_ok=True)
    inv=json.loads((maproot/'inventory.json').read_text())
    S=inv['stages'];NP=inv['pairs_per_rank_die']
    def display(path):
        try:return str(path.relative_to(ROOT))
        except ValueError:return str(path)
    pins=[]
    def read(commit,path,copy=None):
        full=subprocess.check_output(['git','rev-parse',commit],cwd=ROOT,text=True).strip()
        b=subprocess.check_output(['git','show',full+':'+path],cwd=ROOT)
        pins.append(dict(commit=full,path=path,sha256=hashlib.sha256(b).hexdigest()))
        if copy: (out/'inputs'/copy).write_bytes(b)
        return json.loads(b)
    (out/'inputs').mkdir(exist_ok=True)
    scenario=read(PIN,'results/uarch/dsrom_return_storage_hbm_20261003/model.json')
    for key,expected in scenario['pins'].items():
        commit,path=key.split(':',1);read(commit,path)
        assert pins[-1]['sha256']==expected
    w4=read(W4,'results/uarch/dsrom_c_w4_20261003/model.json','W4.json')
    caller=read(W4,'results/uarch/dsrom_c_w4_20261003/inputs/caller.json')['whole_reticle_join']
    w3=read(W3,'results/uarch/dsrom_c_w3_kv_shoreline_20261003/model.json','W3.json')
    w1=read(W1,'results/uarch/dsrom_c_w1_20261003/actual_r1/result.json','W1_RD4_rejection.json')
    assert w1['results']['nodes']['measured_saturated_slot_reuse_cycles']==9
    r4=read(PIN,'results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002/model-r4.json')
    cap=read(PIN,'results/uarch/dsrom_capture_home_20261002/model.json')
    union=read(PIN,'results/uarch/dsrom_capture_clock_selected_union_20261002/model.json')
    budget=read(PIN,'results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002/inputs/compiled_budget.json')
    terms=[]
    for t in w4['terms']:
        s=t['scaling'];mode=('BF' if s=='per BF element' else 'q' if s=='per q element' else 'die' if s in ('per-die service','per-die accounting') else 'sites')
        terms.append(dict(t,mode=mode,reference_sites=2048,reference_BF=362,reference_q=1686))
    for t in caller['additions']:
        terms.append(dict(name=t['id'],mm2=t['mm2'],mode='die' if t['id']=='selector_source_correct_station' else 'sites',scaling=t['basis']))
    with gzip.open(ROOT/'results/uarch/dsrom_capture_home_20261002/inputs/budget.json.gz','rt') as f: cb=json.load(f)['composed_whole_area']
    terms += [dict(name='terminal delta',mm2=cb['allowed_terminal_delta_mm2'],mode='die'),
              dict(name='enable replacement delta',mm2=cb['replacement_enable_delta_mm2'],mode='sites'),
              dict(name='PAR2 two-port corridor REMOVED',mm2=cb['new_two_port_corridor_reservation_mm2'],mode='removed'),
              dict(name='initial capture proxy',mm2=cb['capture_whole_owner_proxy_mm2'],mode='die'),
              dict(name='capture enclosure replaces old proxy',mm2=cap['whole_area']['new_capture_enclosure_mm2']-cap['whole_area']['replaced_old_capture_proxy_mm2'],mode='die'),
              dict(name='selected clock island delta',mm2=union['whole_selector_replacement_screen_mm2']-cap['whole_area']['no_containment_screen_mm2'],mode='die')]
    delta=union['whole_selector_replacement_screen_mm2']-r4['single_parallel_successor']['conservative_priced_per_shard_mm2']
    assert abs(sum(t['mm2'] for t in terms)-delta)<1e-8
    fixed=w4['inherited_fixed_mm2']+w4['native_residual_47_mm2']
    eo=budget['exact_once_area_ledger_mm2']
    var=(sum(eo[k] for k in ['full_compiled_q_BF_catalog_frames','config_prospective_body_plus_local_mux','RNE_BF724_upper_proxy','WAKE_full_compiled_upper_proxy'])+2*26.79)/4096
    def area(S,mode):
        n=math.ceil(195750/S);bf=math.ceil(41984/S);q=n-bf
        priced=[]
        for t in terms:
            factor={'die':1,'BF':bf/362,'q':q/1686,'sites':n/2048,'removed':0}[t['mode']]
            if mode=='historical_all_scale' and t['mode']!='removed':factor=n/2048
            if mode=='fixed_per_die_upside' and t['mode']!='removed':factor=1
            priced.append(dict(name=t['name'],mm2=t['mm2']*factor,factor=factor))
        # Preserve the existing NP4096/R128/RD64 declaration until a baseline-
        # depth ragged return is qualified. Inactive return inputs do not create
        # padding weight banks or element frames. No credit-return area saving.
        ret=B.return_bits(4096,R=128,RD=64,ROOTD=128,pair_buf=0)*B.MM2_PER_BIT
        total=fixed+var*n+ret+sum(t['mm2'] for t in priced)
        return dict(stages=S,pairs=n,BF=bf,q=q,base_fixed_mm2=fixed,base_variable_mm2=var*n,
                    retained_return_FF50_reservation_mm2=ret,increment_terms=priced,screen_mm2=total,
                    margin_mm2=858-total,screen_pass=total<=858,physical_fit=False)
    sensitivity={mode:dict(S69=area(69,mode),S73=area(73,mode),first_area_screen=next(area(s,mode) for s in range(40,200) if area(s,mode)['screen_pass'])) for mode in ['source_classified','historical_all_scale','fixed_per_die_upside']}
    save(out/'area_ledger.json',dict(historical_delta_mm2=delta,traced_58_mm2=w4['increment_mm2'],terms=terms,
        classification='Whitespace remains charged as packing-dependent; generic provider/cell floors conservatively scale by sites pending actual counts.',
        inherited_fixed_mm2=w4['inherited_fixed_mm2'],unmapped_complement_mm2=w4['unmapped_complement_mm2'],
        complement_credit_mm2=0,PAR2_corridor_credit_mm2=cb['new_two_port_corridor_reservation_mm2'],
        RNE_WAKE_config_and_reframe_retained=True,S69_adopted=False,S73_provisional=True,sensitivity=sensitivity,
        exact_cost_gaps=['W1 adder/tag/counter/flow logic and contextual CTS/routes excluded from historical FF return proxy',
                         'Actual per-stage PHW macro counts and source repair geometries must replace proportional proxies',
                         'W4 replacement rectangles and W3 PHY/controller/service map not complete'],
        candidate_screen=area(S,'source_classified'),
        every_die_858_gate='BLOCKED: area proxy alone is insufficient'))
    baseline=dict(label='MODEL_UNVALIDATED_BASELINE_BINDING',source_commit=W1,selected='EXISTING_RETURN_RD64_ROOT128',
        rejected_RD4_reuse_cycles=9,target_cycles=4,rejected_fixture_cycles=dict(credit=582,reference=267),
        fixture_is_not_program_rate_loss=True,RD4_credit_area_or_gain_claim=False,
        rejected_RD4_area_proxy_mm2=9.983,proxy_excludes_control=True,
        existing_storage_NP=4096,existing_roots=128,RD=64,ROOTD=128,pair_buf=0,
        bits=B.return_bits(4096),FF50_reservation_mm2=B.return_bits(4096)*B.MM2_PER_BIT,
        field_pairs=NP,weight_padding_pairs=0,unused_return_input_pairs=4096-NP,
        binding=f'field pair p in ragged region r connects to retained return pair 32*r+p-floor(r*{NP}/128); unused return valid inputs inactive',
        area_credit_for_unconnected_return_nodes_mm2=0,
        baseline_depth_ragged_return_NOT_QUALIFIED=True,successor_interface_exactness_and_loaded_timing_NOT_QUALIFIED=True,
        measured_program_loss=None,latency_credit_cycles=0)
    save(out/'return_baseline.json',baseline)
    def mapping_input(name):
        path=maproot/name
        if not path.exists() and maproot==BASE/'baseline_s82_successor_r1':
            path=BASE/'baseline_s82_mapping_r1'/name
        return path
    mapping=json.loads(mapping_input('mapping_verdict.json').read_text())
    stages=json.loads((maproot/'stage_map.json').read_text())
    # A complete source directory is a conservation record, not a claim that every entry has a legal runtime owner.
    headers=C.load_headers(ROOT/'results/uarch/dsrom_fixed4096_owner_compiler_20261002/inputs/tensor_headers.jsonl.gz')
    owners=collections.defaultdict(list);used=collections.defaultdict(set);matrix_rectangles=collections.defaultdict(list)
    final_matrices=[];broadcasts=[]
    for m in C.readrows(maproot/'matrix_map.jsonl.gz'):
        unique=[];canonical_ranks=[]
        for rank,s in enumerate(m['rank_slices']):
            if s not in unique:unique.append(s);canonical_ranks.append(rank)
        m=dict(m,physical_owner_ranks=canonical_ranks,reference_rank_slices=m['rank_slices'],
               duplicate_source_payload_storage_removed=4-len(unique),reserved_frames_credit_mm2=0)
        if len(unique)!=4:
            assert len(unique)==1
            rows=m['rows'];fanout=3
            broadcasts.append(dict(tensor=m['tensor'],alias=m['alias'],stage=m['stage'],source_rank=0,destination_ranks=[1,2,3],
                result_rows=rows,result_record_bits=69,delivered_bits=rows*69*fanout,
                serialized_cycles_at_one_record_per_cycle_per_link=rows,
                serialized_cycles_at_one_shared_link=fanout*rows,CDC_cycles_assumed=2,
                parallel_ports_assumed=True,physical_link_lane_allocation_qualified=False,
                lower_model_us=(rows+2)/1200+0.075,shared_link_model_us=(fanout*rows+2)/1200+0.075,
                exactness='Compute identical full indexer projection once; multicast its rounded result in original row/tag order; RTL proof pending'))
            m['result_multicast_contract']=broadcasts[-1]
        final_matrices.append(m)
        if m['stage'] is not None:
            used[m['stage']].update(p for _,p,*_ in m['plans'])
            matrix_rectangles[m['tensor']].extend((s['rows'][0],s['cols'][0],s['rows'][1],s['cols'][1]) for s in unique)
        for name in [m['tensor'],m['source_scale_tensor']]:
            if name:owners[name].append(dict(kind='matrix',stage=m['stage'],alias=m['alias'],rank_slices=unique,physical_owner_ranks=canonical_ranks))
    C.gzrows(out/'matrix_map.jsonl.gz',final_matrices)
    save(out/'indexer_multicast_model.json',dict(label='MODEL_UNVALIDATED',calls=broadcasts,
         compute_result_multicast_not_weight_replicas=True,frame_credit_mm2=0,
         additional_token_us_lower=sum(x['lower_model_us'] for x in broadcasts),
         additional_token_us_shared_link=sum(x['shared_link_model_us'] for x in broadcasts),
         all_calls_serially_charged=True,source_schedule_and_link_port_gates_open=True,
         adoption=False))
    providers=json.loads(mapping_input('providers.json').read_text())
    for p in providers:
        used[p['stage']].update(p['pairs'])
        for t in p['declarations']:owners[t['tensor']].append(dict(kind=p['kind'],stage=p['stage'],canonical_source_rank=0,
                 rank_delivery='Existing replicas replaced by exact source reads/multicast; delivery calendar is unqualified; area credit zero'))
    for t in inv['dedicated_storage']['tables']:
        for name in [t['tensor'],t['scale_tensor']]:owners[name].append(dict(kind='table',pair_start=t['pair_start'],pairs=t['pairs']))
    for t in inv['dedicated_storage']['global_tensors']:owners[t['tensor']].append(dict(kind='head',pair_start=t['pair_start'],pairs=t['pairs']))
    # Retain auxiliary payloads in empty q-only pairs of the same 73-stage array.
    # Byte copying is exact and changes no arithmetic; executing those providers
    # still requires a source-specific ABI and composed latency before adoption.
    bf=set(stages['BF_site_IDs']);free=[(s,p) for s in range(S) for p in range(NP) if p not in bf and p not in used[s]]
    auxiliary=[h for n,h in sorted(headers.items()) if n not in owners]
    cursor=0;capacity=len(free)*4*16384*32;auxmap=[];auxspans=collections.defaultdict(list)
    for h in auxiliary:
        n=h['source_storage_bytes'];start=cursor;stop=start+n
        if stop>capacity:raise ValueError('Auxiliary payload needs additional priced capacity')
        spans=[];a=start
        while a<stop:
            slot,offset=divmod(a,16384*32);pairslot,rank=divmod(slot,4);s,p=free[pairslot]
            b=min(stop,a+16384*32-offset)
            spans.append(dict(stage=s,rank=rank,pair=p,source_byte_range=[a-start,b-start],pair_data_byte_range=[offset,offset+b-a]))
            auxspans[(s,rank,p)].append((offset,offset+b-a));a=b
        cursor=(stop+31)//32*32
        item=dict(h,payload_spans=spans,word_data_bits=256,physical_word_bits=274,ROM_ECC=False,
                  physical_address='word=byte//32; logical_slot=word//8192; parity=word%2; row=(word%8192)//2; macro=4*pair+2*logical_slot+parity; bit=8*(byte%32)',
                  source_byte_copy_exact=True,execution_ABI_qualified=False)
        auxmap.append(item);owners[h['tensor']].append(dict(kind='auxiliary_raw_payload',payload_spans=spans))
    for ss in auxspans.values():
        ss.sort();assert all(a[1]<=b[0] for a,b in zip(ss,ss[1:]))
    save(out/'auxiliary_map.json',dict(tensors=auxmap,payload_bytes=sum(h['source_storage_bytes'] for h in auxiliary),
          reserved_bytes=cursor,available_bytes=capacity,used_die_ids=sorted({4*s+r for s,r,p in auxspans}),
          pair_instances=len(auxspans),additional_dies=0,additional_ROM_macros=0,
          no_free_transport_assumed=True,execution_ABI_and_latency='UNPRICED_BLOCKS_ADOPTION',
          bit_address_bounds_and_span_overlap_PASS=True))
    # Rectangle coverage proves every matrix code coordinate is present once
    # across the four rank slices and any output-row fragments.
    def matrix_coverage(rects,rows,cols):
        xs=sorted({0,rows}|{v for a,_,b,_ in rects for v in [a,b]})
        for a,b in zip(xs,xs[1:]):
            ys=sorted((c,d) for x,c,y,d in rects if x<=a and y>=b)
            end=0
            for c,d in ys:
                if c!=end:return False
                end=d
            if end!=cols:return False
        return xs[0]==0 and xs[-1]==rows
    matrix_checks=[]
    for name,rects in sorted(matrix_rectangles.items()):
        h=headers[name];rows,cols=h['shape'];cols*=2 if h['dtype']=='I8' else 1
        matrix_checks.append(dict(tensor=name,code_coordinate_exactonce_PASS=matrix_coverage(rects,rows,cols)))
    save(out/'matrix_coordinate_coverage.json',dict(checks=matrix_checks,all_PASS=all(x['code_coordinate_exactonce_PASS'] for x in matrix_checks)))
    missing=[];directory=[]
    for name,h in sorted(headers.items()):
        entries=owners.get(name,[])
        if not entries:missing.append(name)
        directory.append(dict(h,source_key_exactonce=True,placement_entries=entries,placement_status='OWNER_RECORD' if entries else 'UNPLACED_CHARGED_OBLIGATION'))
    assert len(directory)==len(headers)==96085
    C.gzrows(out/'shipped_weight_directory.jsonl.gz',directory)
    save(out/'weight_conservation.json',dict(shipped_source_keys=96085,source_bytes=sum(h['source_storage_bytes'] for h in headers.values()),
        source_directory_keys_exactonce_PASS=True,symbolic_all_shipped_provider_coverage_PASS=not missing,
        matrix_code_coordinates_exactonce_PASS=all(x['code_coordinate_exactonce_PASS'] for x in matrix_checks),
        physically_placed_exactonce_PASS=False,
        unplaced_keys=missing,unplaced_bytes=sum(headers[n]['source_storage_bytes'] for n in missing),
        no_missing_weight_hidden=True,scales_and_constants_included=True,
        scale_replication_and_rank_provider_copies_need_actual_payload_address_bijection=True))
    save(out/'physical_contract.json',dict(label='MODEL_UNVALIDATED',die_outline_mm=[26,33],one_die_per_rank=True,
        UCIe_owner_crossings=0,PAR2_ports=0,root_count=128,region_bounds=stages['region_bounds'],
        ROM_macro=dict(rows=4096,word_bits=274,macros_per_pair=4,ROM_ECC=False,real_capture_timing_retained=True),
        domains_Hz=dict(stream=1200000000,serial=900000000),SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        stage_hop_us=0.407+0.075,stage_boundaries=S-1,ordered_K_reduction_unchanged=True,
        output_row_split_added_delivery='Explicit row fragments; gather/dispatch/stalls unqualified and not credited as zero latency',
        stage_service_homes=stages['scan_service_homes'],W3_stack_count=4*S+128,W3_stack_count_status='PROVISIONAL_REQUIRES_ACTUAL_SERVICE_JOIN',
        source_ports=dict(q_forward_bits_per_cycle=549,BF_forward_bits_per_cycle=1067,return_bits_per_pair=126,ROM_bytes_per_pair_active_cycle=68.5),
        reverse_credits_and_transaction_identity_required=True,SRAM_HBM_link_protection_retained=True,
        return_contract=baseline,
        hub_routing_layer_check='NOT_RUN',SSFF_contextual_timing='NOT_RUN',physical_admission=False))
    save(out/'model.json',dict(schema='opentallas.dsrom.S73.PAIR1.successor.v1',label='MODEL_UNVALIDATED',
        provisional_S=S,provisional_pairs=NP,decoder_packing_reference=mapping,
        map_source_directory=display(maproot),
        candidate_inventory=dict(layer_dies=4*S,total_dies=4*S+44,packages_if_paired=2*S+22,
            provisional_stacks_if_exactly_eight_scan_service_homes=4*S+128,
            delta_dies_vs_historical_C=4*(S-73),delta_stage_hop_us_vs_C=(S-73)*0.482,
            additional_stage_hops_only_not_complete_token_delta=True,
            layer_area_screen_sum_mm2=4*S*area(S,'source_classified')['screen_mm2'],
            layer_reticle_outline_mm2=4*S*858,power_kW_and_rate_NOT_REPRICED=True),
        selected_return=baseline,
        S69='Sensitivity only: W4 does not trace >=50mm2 as fixed per die',
        six_historical_pins_match=True,source_pins=pins,W4_commit=W4,W3_commit=W3,W1_commit=W1,
        delta_vs_C_adopted=dict(tok_s=0,mm2=0,kW=0,dies=0),adopted=False,
        indexer_multicast_token_us_model=[sum(x['lower_model_us'] for x in broadcasts),sum(x['shared_link_model_us'] for x in broadcasts)],
        rate='Inherited2490/2600 rates are not transferred to this packing or new PHW and split-delivery contract',
        gates=dict(source_directory='PASS_96085_KEYS',complete_symbolic_provider_directory='PASS' if not missing else 'FAIL',complete_physical_weight_map='UNVALIDATED',
                   decoder_capacity='PASS' if not mapping['failures'] else 'FAIL',reticle='BLOCKED_CONTEXTUAL_FIT' if area(S,'source_classified')['screen_pass'] else 'FAIL_AREA_SCREEN',W1_RD='RD4_REJECTED_BASELINE_RETAINED',W3='BLOCKED',W4='ATTRIBUTION_ONLY'),
        original_records_changed=False,RTL_PnR_inference=False))
    save(out/'coordination.json',dict(W1=dict(owner='Rawls',commit=W1,region_bounds=stages['region_bounds'],root_count=128,field_NP=NP,return_NP=4096,RD=64,
                                            contract='RD4 rejected; retain full baseline return and inactive input wires; exact stream/flow join remains open'),
                                    W3=dict(owner='Chandra',commit=W3,provider_homes=stages['provider_homes'],matrix_stages=stages['layer_matrix_stages'],
                                            request='Join actual scan and CKV/index service placement; derive per-die KV and stack/controller demand'),
                                    W4=dict(owner='Maxwell',commit=W4,inventory=display(maproot/'inventory.json'),ledger='area_ledger.json',
                                            request='Use exact active/BF/site counts and PHW; no legacy-complement credit until disjoint rectangles close'),
                                    peer_acknowledgments='NOT_RECORDED',packet='/tmp/dsrom-c-w2-coordination-20261003/W2-active-contract.json'))
    auxpairs=collections.defaultdict(set)
    for item in auxmap:
        for span in item['payload_spans']:auxpairs[(span['stage'],span['rank'])].add(span['pair'])
    inv=dict(inv,return_baseline=baseline,numbers='MODEL_UNVALIDATED')
    inv['configuration_macro_inventory']=dict(label='MODEL_SOURCE_EQUIVALENT_DECLARATION_NOT_PHYSICAL_BINDING',
        master='ot_rom_4096x72_m8',ROM_ECC=False,
        words_per_pair_by_stage=[25*(1<<p) for p in stages['PHW_required_by_stage']],
        macros_per_pair_by_stage=[(25*(1<<p)+4095)//4096 for p in stages['PHW_required_by_stage']],
        packing_credit=False,read_capture_clock_and_dispatch_qualified=False)
    BF=inv['BF_dual_pairs']
    inv['per_die']=[dict(stage=s,rank=r,die_id=4*s+r,active_field_pairs=NP,q_only_pairs=NP-BF,
        BF_dual_pairs=BF,weight_macros=4*NP,padding_weight_macros=0,
        auxiliary_used_pair_count=len(auxpairs[(s,r)]),PHW=stages['PHW_required_by_stage'][s]) for s in range(S) for r in range(4)]
    save(out/'inventory.json',inv);save(out/'stage_map.json',stages)
    save(out/'uarch_contract.json',dict(label='MODEL_UNVALIDATED',
        per_pair=dict(MACs_per_cycle=dict(fp4=128,fp8=64,BF16=32),
            mode_exclusivity='BF dual stores/computes q or BF; do not sum both modes',ROM_captured_bytes_per_active_cycle=68.5,
            compute_intensity_MAC_per_ROM_byte=dict(fp4=128/68.5,fp8=64/68.5,BF16=32/68.5),producer_partial_bits_per_cycle=126),
        per_die=dict(q_compatible_pairs=NP,BF_capable_pairs=BF,peak_fp4_MACs_per_cycle=NP*128,
            peak_BF_MACs_per_cycle=BF*32,ROM_bytes_per_cycle_if_all_pairs_active=NP*68.5,
            field_return_cut_bits_per_cycle=NP*126,forward_q_bus_bits=549,forward_BF_bus_bits=1067,
            stream_broadcast_site_fanout=NP,source_descriptor_word_bits=48,retained_return_root_records_per_cycle=128),
        routing=dict(local_q_needed_tracks=549,local_BF_needed_tracks=1067,capacity_binding=None,
            route_layer_check='NOT_RUN',unpriced_channel_growth_not_zero=True),
        latency=dict(existing_stage_hop_us=.482,extra_stage_hops_vs_C=S-73,extra_hop_us_vs_C=(S-73)*.482,
            matrix_issue_cycles='Each matrix_map record retains native ordered-segment LAT8 issue count',return_storage_credit_cycles=0,
            indexer_multicast='indexer_multicast_model.json: positive model bounds',
            row_fragment_gather_and_auxiliary_access='Not qualified; complete source calendar required before build',
            complete_token_rate_qualified=False),
        replicas=dict(stage_rank_dies=4*S,complete_pairs=4*S*NP,main_weight_macros=16*S*NP,return_blocks=4*S,ROM_ECC_sidecars=0),
        area='area_ledger.json retains fixed/residual/halo/whitespace/cfg/RNE/WAKE/full return; only PAR2 corridor removed',floorplan_admission=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--map-dir',type=Path,default=BASE/'baseline_s82_successor_r1');a=ap.parse_args();build(a.out,a.map_dir)
