#!/usr/bin/env python3
"""Finite PAR2 local parity service, explicit provisional costs; not an RTL trace."""
import argparse,ast,collections,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'results/uarch/dsrom_par2_raw_parity_replica_20261002'

def check(p):
    required=('macro_capture_cycles','raw_decode_cycles','delivery_cycles','weight_ECC_cycles',
              'first_main_codeword_capture_cycles','read_II','decoder_II','delivery_II','decoder_lanes','delivery_lanes',
              'read_credits_per_leaf','response_slots','delivery_queue_slots')
    if any(not isinstance(p.get(k),int) or isinstance(p[k],bool) or p[k]<=0 for k in required):
        raise ValueError('all service durations and finite capacities must be explicit positive integers')
    if p.get('latency_status')!='PROVISIONAL_ANALYTICAL_NOT_MEASURED':raise ValueError('no hardware measurement receipt supplied')
    if p.get('decoder_topology') not in ('leaf_local','shared'):raise ValueError('explicit decoder topology required')
    if p['decoder_topology']=='leaf_local' and p['decoder_lanes']!=412:raise ValueError('physical owner reserves412 leaf-local decoders')
    if p['read_credits_per_leaf']!=1:raise ValueError('current area ledger reserves exactly1credit/leaf; extra credits need reprice')


def calendar(counts,p,trace=False,fault_read=None,cancel_tick=None,deadline=None):
    """Each bank's count is its exact set of unique canonical protected words.
    All grants within this one physical die are shared. Lease begins only after
    external authenticated cfg/operand readiness; no cost for that fence is erased.
    """
    check(p)
    if not counts or any(not isinstance(n,int) or n<=0 for n in counts):raise ValueError('positive bank demands required')
    if len(counts)>412:raise ValueError('raw leaf count exceeds existing mirror')
    remaining=list(counts);debt=[0]*len(counts);next_read=[0]*len(counts)
    macro=[];response=[];decoding=[];gather=[];delivery=[]
    dec_free=[0]*p['decoder_lanes'];del_free=[0]*p['delivery_lanes']
    accepted=good=bad=0;peak_reserved=peak_gather=peak_debt=0;events=[];canceled=False
    t=0
    while True:
        if cancel_tick is not None and t>=cancel_tick:canceled=True
        done=[e for e in delivery if e['end']==t];delivery=[e for e in delivery if e['end']!=t]
        for e in done:
            debt[e['bank']]-=1;bad+=e['fault'];good+=not e['fault']
            if trace:events.append(dict(edge='raw_terminal_and_credit_release',tick=t,**e))
        due=[e for e in decoding if e['end']==t];decoding=[e for e in decoding if e['end']!=t]
        gather.extend(due)
        # Same-edge departures before registered queue occupancy is measured.
        for lane in range(len(del_free)):
            if gather and del_free[lane]<=t:
                e=gather.pop(0);e=dict(e,end=t+p['delivery_cycles']);delivery.append(e);del_free[lane]=t+p['delivery_II']
                if trace:events.append(dict(edge='gather_delivery_accept',tick=t,lane=lane,**e))
        peak_gather=max(peak_gather,len(gather))
        if len(gather)>p['delivery_queue_slots']:raise ValueError('finite gather queue overflow; grant schedule rejected')
        response.extend(e for e in macro if e['end']==t);macro=[e for e in macro if e['end']!=t]
        for lane in range(len(counts) if p['decoder_topology']=='leaf_local' else len(dec_free)):
            eligible=next((i for i,e in enumerate(response) if p['decoder_topology']=='shared' or e['bank']==lane),None)
            if eligible is not None and dec_free[lane]<=t and len(decoding)+len(gather)<p['delivery_queue_slots']:
                e=response.pop(eligible);e=dict(e,end=t+p['raw_decode_cycles']);decoding.append(e);dec_free[lane]=t+p['decoder_II']
                if trace:events.append(dict(edge='raw_SECDED_accept',tick=t,lane=lane,**e))
        # Reserve response space at read acceptance: macro cannot be backpressured later.
        reserved=len(macro)+len(response)
        for bank in range(len(counts)):
            if not canceled and remaining[bank] and debt[bank]<1 and next_read[bank]<=t and reserved<p['response_slots']:
                e=dict(bank=bank,ordinal_in_bank=counts[bank]-remaining[bank],read_id=accepted,
                       fault=accepted==fault_read,end=t+p['macro_capture_cycles'])
                macro.append(e);reserved+=1;remaining[bank]-=1;debt[bank]+=1
                next_read[bank]=t+p['read_II'];accepted+=1
                if trace:events.append(dict(edge='local_read_accept',tick=t,**e))
        peak_reserved=max(peak_reserved,reserved);peak_debt=max(peak_debt,sum(debt))
        if not any(debt) and (canceled or not any(remaining)):break
        t+=1
        if t>sum(counts)*sum(p[k] for k in ('macro_capture_cycles','raw_decode_cycles','delivery_cycles','first_main_codeword_capture_cycles','read_II','decoder_II','delivery_II'))+10000:
            raise ValueError('non-draining finite schedule')
    complete=not canceled and bad==0 and good==sum(counts)
    visibility=t+p['first_main_codeword_capture_cycles']+p['weight_ECC_cycles'] if complete else 'REFUSED_ECC_OR_CANCEL'
    delta='ORIGINAL_DEADLINE_UNBOUND' if deadline is None else (max(0,visibility-deadline) if complete else 'REFUSED')
    return dict(accepted_reads=accepted,good_reads=good,fault_reads=bad,canceled=canceled,
        final_read_debt=sum(debt),peak_read_debt=peak_debt,peak_reserved_response_slots=peak_reserved,
        peak_delivery_queue_slots=peak_gather,raw_prefetch_terminal_tick=t,
        earliest_compute_relative_to_authenticated_external_ready=visibility,
        first_main_word_capture_cycles=p['first_main_codeword_capture_cycles'],
        source_main_capture_not_added_twice_to_existing_field_cost=True,
        incremental_prefetch_and_new_ECC_cycles=t+p['weight_ECC_cycles'] if complete else 'REFUSED',
        weight_ECC_increment_cycles=p['weight_ECC_cycles'],compute_permission=complete,permission_scope='Temporal provisional gate only; actual arithmetic additionally requires source24 terminal_join for every matched mainword and authenticated native mode/owner proof',
        exposed_deadline_delta=delta,actual_RTL_accepted_events=False,ECC_status_is_symbolic_fault_injection_not_payload_decode=True,
        event_trace=events if trace else [],hardware_no_token_loss_proven=False)


def owner_authorize(request,terminal):
    """Reuse frozen existing-owner authentication, not a second ledger."""
    p=ROOT/'results/uarch/dsrom_par2_local_ECC_calendar_20261002/inputs/owner_terminal_source_24a.py'
    tree=ast.parse(p.read_text());names={'read_identity','terminal_join'}
    ns={'CANDIDATE':'DS4096-TP4-S58-PAR2-NP2048'}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'frozen24-owner','exec'),ns)
    return ns['terminal_join'](request,terminal)


def extract_witness(journal):
    if hashlib.sha256(journal.read_bytes()).hexdigest()!='c91855b5b33c21c56dac3ea9ebc69a201ff582a3a6ad67a19024e89cd113881f':raise ValueError('not corrected622 metadata journal')
    provider=next(json.loads(l) for l in gzip.open(INPUT/'inputs/canonical_ECC_directory.jsonl.gz','rt') if json.loads(l)['stage']==0)
    tree=ast.parse((INPUT/'inputs/cfg_export_f607.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sidecar_address')
    ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'f607-source-address','exec'),ns)
    with gzip.open(journal,'rt') as f:
        for ordinal,line in enumerate(f):
            if ordinal==12:r=json.loads(line);break
    if r['stage']!=0 or r['alias']!='exp0.w2':raise ValueError('witness identity changed')
    banks=collections.defaultdict(set);prefix=0
    for seg,pair,first,n,stride,start,words in r['plans']:
        if pair>=2048:
            for j in range(n*words):
                a=ns['sidecar_address'](provider,r['ecc_bit_base']+prefix+j*16)
                key=','.join(map(str,(provider['pairs'].index(a['pair']),a['mb'],a['parity'])))
                banks[key].add(a['physical_row'])
        prefix+=n*words*16
    return dict(source_journal_sha256='c91855b5b33c21c56dac3ea9ebc69a201ff582a3a6ad67a19024e89cd113881f',
        ordinal=12,source_record_sha256=hashlib.sha256(line.encode()).hexdigest(),
        canonical_source_API='f607 sidecar_address unchanged; protected word reused16times maximum',
        unique_rows_by_pidx_MB_parity={k:sorted(v) for k,v in sorted(banks.items())},
        payload_read=False,allocator_or_encoder_rerun=False)


def build(p):
    check(p)
    profiles=json.loads(gzip.decompress((INPUT/'inputs/demand_profiles.json.gz').read_bytes()))
    aliases=[json.loads(x) for x in gzip.open(INPUT/'inputs/local_ECC_mirror_option.jsonl.gz','rt')]
    bystage={x['stage']:x for x in aliases};cache={};records=[];witness=None
    wordrows=json.loads((ROOT/'results/uarch/dsrom_par2_local_ECC_calendar_20261002/witness_word_rows.json').read_text())
    for r in profiles['records']:
        banks=sorted(r['unique_raw256_reads_by_leaf']);counts=tuple(r['unique_raw256_reads_by_leaf'][b] for b in banks)
        if counts not in cache:cache[counts]=calendar(counts,p)
        c=cache[counts]
        records.append(dict(matrix_journal_ordinal=r['matrix_journal_ordinal'],stage=r['stage'],phase=r['phase'],
            layer=r['layer'],expert=r['expert'],alias=r['alias'],bank_order_pidx_MB_parity=banks,
            accepted_reads=c['accepted_reads'],prefetch_terminal=c['raw_prefetch_terminal_tick'],
            compute_relative_ready=c['earliest_compute_relative_to_authenticated_external_ready'],
            incremental_prefetch_and_new_ECC_cycles=c['incremental_prefetch_and_new_ECC_cycles'],
            original_consumer_deadline='UNBOUND_NO_ZERO_COST_OR_OVERLAP_CREDIT'))
        if r['matrix_journal_ordinal']==12:
            c=calendar(counts,p,trace=True);mapping=[]
            for b in banks:
                i,mb,parity=map(int,b.split(','));a=bystage[r['stage']]
                mapping.append(dict(logical_bank=b,original_global_pair=a['original_pairs'][i],
                    mirror_global_pair=a['mirror_pairs'][i],mirror_local_pair=a['mirror_pairs'][i]-2048,
                    MB=mb,parity=parity,physical_row_unchanged=True,protected_data_and_SECDED_copy='256+10 unchanged'))
            for e in c['event_trace']:
                b=banks[e['bank']];rows=wordrows['unique_rows_by_pidx_MB_parity'][b]
                if len(rows)!=counts[e['bank']]:raise ValueError('actual protected word address count mismatch')
                e['physical_row']=rows[e['ordinal_in_bank']];e['pidx_MB_parity']=b
                e['original_global_pair']=mapping[e['bank']]['original_global_pair'];e['mirror_global_pair']=mapping[e['bank']]['mirror_global_pair']
                e['same_protected256_plus10_identity']=True
                i,mb,pa=map(int,b.split(','));e['physical_decoder_leaf']=4*i+2*mb+pa
            witness=dict(phase_identity={k:r[k] for k in ('matrix_journal_ordinal','stage','phase','layer','expert','alias')},
                bank_aliases=mapping,calendar=c)
    groups=collections.defaultdict(list)
    for r in records:groups[r['layer'],r['expert']].append(r)
    if len(records)!=46080 or len(groups)!=15360 or any(len(v)!=3 for v in groups.values()):raise ValueError('full expert demand lost')
    lo=hi=0
    for l in range(40):
        v=sorted(sum(r['incremental_prefetch_and_new_ECC_cycles'] for r in groups[l,e]) for e in range(384));lo+=sum(v[:6]);hi+=sum(v[-6:])
    body=json.loads((INPUT/'model-r1.json').read_text())
    context=ROOT/'results/uarch/dsrom_par2_local_ECC_calendar_20261002/inputs'
    physical=json.loads((context/'physical_padding_3010.json').read_text())
    enabled=json.loads((context/'physical_context_f934.json').read_text())
    if physical['candidate']!=body['candidate_id'] or enabled['candidate']!=body['candidate_id']:raise ValueError('one physical candidate required')
    model=dict(schema='opentallas.dsrom.PAR2-local-ECC-finite-calendar.v1',
        candidate=body['candidate_id'],variant=body['variant_id'],parameters=p,
        source_input_sha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in
            (INPUT/'model-r1.json',INPUT/'inputs/demand_profiles.json.gz',INPUT/'inputs/local_ECC_mirror_option.jsonl.gz',ROOT/'results/uarch/dsrom_par2_local_ECC_calendar_20261002/witness_word_rows.json')},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        authoritative_storage_commit='13cc65fb416b9d0cbe5f94c50379c9a54e24222f',alias_commit='124e870c5',
        current_physical_owner_join=dict(source_padding_commit='3010a732e',enabled_context_commit='f9344909c',
            input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in context.iterdir() if p.is_file()},
            source_area_ledger=physical['area'],
            current_clearance_and_parity_construction_screen_mm2=physical['area']['with_existing_clearances_screen_mm2'],
            old694p9_screen_is_history_not_current_budget=True,
            source_first_batch_conflict_rounds=physical['source_service']['retained_first_address_bank_conflict_read_rounds'],
            batch128_vs_wholephase='Physical witness64rounds concerns first128request seats; full-phase prefetch400unique reads/leaf is a different conservative policy, not contradictory traces. No batch temporal trace or consumer slack supplied.',
            leaf_local_decoders=412,main_codeword_decoders=256,reply_lanes=128,
            owner_area_allowance_not_double_added_to_prior_0p302_storage_proxy=True,
            additional_fullphase_pool_containment_unproved=True,
            temporal_profile_does_not_qualify_physical_screen=True),
        existing_owner_authentication=dict(source_commit='24a072f17',source_snapshot=str((context/'owner_terminal_source_24a.py').relative_to(ROOT)),
            APIs=['mirror_fence','read_identity','terminal_join'],
            scope='Reuse Nash accepted external owner lease, initialization source manifest and paired raw/ECC terminal authentication. New per-leaf read debt is local service capacity, not a second native owner ledger.',
            actual_mirror_initialization_copy_visibility_not_qualified=True),
        full46080_FP4_phases_bound=True,distinct_bank_count_profiles=len(cache),
        phase_lease='One accepted native owner per logical phase; both cfg/operand readiness authenticates external start. This service models parity after that fence, not a free cfg or activation path.',
        bank_credit='ONE/leaf held until protected raw word is corrected and delivered; canceled/faulted accepted reads drain before reuse.',
        prefetch='Fresh full-phase parity prefetch; all arithmetic waits for good terminal; weight_ECC adds positive pipeline before compute. Immutable256word reuse within phase only.',
        all_macro_instances_already_charged=True,new_macro_instances=0,
        historical_storage_and_admission_proxies_not_current_wholebudget=body['replica'],
        decoder_delivery_pipeline_slots=dict(raw_decoder_inflight_bound=p['decoder_lanes']*((p['raw_decode_cycles']+p['decoder_II']-1)//p['decoder_II']),
            gather_inflight_bound=p['delivery_lanes']*((p['delivery_cycles']+p['delivery_II']-1)//p['delivery_II']),
            additional_tag_and_pipeline_area_requires_reprice=True),
        provisional_selected_six_expert_work=dict(minimum=lo,maximum=hi,phase_calls=720,
            unit='model-relative stream ticks after authenticated external ready',
            is_whole_token_cycles_or_measured_latency=False,
            no_actual_EIDs_or_original_deadlines=True,
            nonoverlap_prefetch_policy_not_architectural_minimum=True),
        witness=witness,
        missing_actual_calibration=['enabled macro capture SS/FF','raw SECDED256+10 code map/decoder SSFF','paired weight SECDED272+10',
            'gather queue/pins/control/PG/routing','accepted cfg/activation and original issue deadlines','root/cancel/reverse-credit cross-die calendar'],
        physical_area_route_and_SSFF_admitted=False,build_admitted=False,no_token_loss_proven=False,
        original_remote_service_unpriced_not_used_as_zero_baseline=True,
        historical_FAILs_preserved=True)
    return model,records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--extract-journal',type=Path);p.add_argument('--parameters',type=Path);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    if a.output_dir.exists():raise ValueError('fresh directory required; preserve prior evidence')
    if a.extract_journal:
        witness=extract_witness(a.extract_journal);a.output_dir.mkdir(parents=True)
        (a.output_dir/'witness_word_rows.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n');raise SystemExit(0)
    model,records=build(json.loads(a.parameters.read_text()));a.output_dir.mkdir(parents=True)
    (a.output_dir/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    (a.output_dir/'phase_calendar.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(r,sort_keys=True) for r in records)+'\n').encode(),mtime=0))
