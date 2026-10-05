#!/usr/bin/env python3
"""Exact retained-phase coverage and canonical all-layer structural census.

Structural class membership selects the smallest additional observer set. It
does not certify a different payload, chosen expert, rank or physical owner.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re

import dsrom_recovery_decision_gate as D

OUT=D.A.RECOVERY/'coverage_manifest'
CAN=D.ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical'


def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def alias_class(a):
    return re.sub(r'exp\d+\.', 'expert.', a)


def signature(phases, plan):
    rb=plan['region_bounds']; bf=set(plan['bf_sites'])
    result=[]
    for p in phases:
        regions=[]
        for r in p['regions']:
            entries=[]
            for mindex,m in enumerate(p['mats']):
                for sr,seg,pair in m['regions'].get(str(r),[]):
                    entries.append((pair-rb[r],pair in bf,mindex,sr,seg))
            # Physical pair address/format/segment and ordered row-to-root map
            # stay in the signature; merely equal K does not establish reuse.
            regions.append((r,sorted(entries)))
        result.append(dict(K=p['K'],out=p['out'],formats=p['fmts'],regions=regions,
            matrices=[dict(format=m['fmt'],K=m['K'],rows=m['rows'],cols=m['cols'],
                segments=m['segments'],read=m['t_read_words_max'],
                issue=m['issue_cycles_LAT8_condition']) for m in p['mats']]))
    return digest(result)


def hc_pair_census():
    """Count literal retained T write/read pairs, without pricing every layer as L20."""
    path=D.ROOT/'results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz'
    demand=json.loads(gzip.decompress(path.read_bytes()))
    nodes={n['id']:n for n in demand['nodes']}
    pairs=[]
    for n in demand['nodes']:
        x=n.get('instruction',{})
        if (x.get('unit'),x.get('su_nin'),x.get('su_nout'),x.get('m1'),x.get('ad'),x.get('qm'))!=(2,5120,1,1,1,1):
            continue
        successor=n['id'].rsplit('I',1)[0]+'I'+str(n['instruction_index']+1)
        following=nodes.get(successor)
        y=following['instruction'] if following else {}
        if (y.get('unit'),y.get('su_nin'),y.get('su_nout'),y.get('m1'),y.get('ad'),y.get('c_base'),y.get('o_base'))!=(2,5120,1,1,2,x.get('o_base'),x.get('o_base')):
            continue
        if 'T' not in x.get('_writes',[]) or 'T' not in y.get('_reads',[]):
            raise ValueError('pair lacks actual T write/read')
        pairs.append(dict(first=n['id'],second=successor,scope=n['scope'],
            tag=x['_tag'],T_address=x['o_base'],
            first_template_sha256=n['template_word_sha256'],
            second_template_sha256=following['template_word_sha256']))
    base=D.load(D.OUT/'model.json')['scenarios']['baseline']
    edge=next(e for e in base['attribution']['edges'] if e['node']=='L20.attn.hc_pre')
    ar=base['known_terms_projection']['AR_us']
    ceiling=edge['exposed_us']
    return dict(source=str(path.relative_to(D.ROOT)),literal_pairs=pairs,
        count=len(pairs),layers=sorted({p['scope'] for p in pairs if isinstance(p['scope'],int)}),
        head_pairs=sum(p['scope']=='head' for p in pairs),
        interpretation='Literal T write/read census, not measured all-layer incremental exposure. Existing graph fusion already removes eligible inter-node network costs; these internal source pairs still publish T.',
        selected_scope='L20.attn.hc_pre first two ops only',
        baseline_entire_three_op_node_us=ceiling,
        baseline_AR_us=ar,
        impossible_entire_node_elimination_rate_gain_percent=100*(ar/(ar-ceiling)-1),
        verdict='REJECT_SCOPED_PAIR_BELOW_ONE_PERCENT',rtl_authorized=False,
        current_incremental_gain_us=None,
        forbidden_credit='Do not multiply standalone .353333us by81. Native-port 789-cycle candidate calendar and1107-cycle baseline are not the actual188-cycle wired whole-node baseline.',
        next_action='Release Arendt to a concrete current integration bug; no candidate RTL or broader extrapolation. Field issuer and exact all40 phase binding remain active.')


def build():
    plan=json.loads(gzip.decompress((OUT/'inputs/retained_plan.json.gz').read_bytes()))
    golden_sources=json.loads(gzip.decompress((OUT/'inputs/all40_golden_json.json.gz').read_bytes()))
    gold={r['layer']:json.loads(r['json_bytes']) for r in golden_sources}
    if set(gold)!=set(range(40)):
        raise ValueError('missing actual golden layer identity')
    for L,g in gold.items():
        if g['layer']!=L or g['context']!=1048576 or g['position']!=1048575 or g['arith']!='chunk8':
            raise ValueError('wrong golden context/arithmetic')
        if len(g['experts'])!=6 or len(set(g['experts']))!=6:
            raise ValueError('actual six-expert selection absent')
        if str(L) in plan['experts'] and plan['experts'][str(L)]!=g['experts']:
            raise ValueError('golden does not match existing retained phase selection')
    paired=D.load(D.A.RECOVERY/'paired_field_gate/model.json')
    grouped=defaultdict(list)
    aliases=defaultdict(set)
    for p in plan['phases']:
        key=f"L{p['layer']}.{p['node']}.st{p['stage']}"
        grouped[key].append(p)
        for m in p['mats']:
            aliases[alias_class(m['alias'])].add(p['node'])
    critical={e['node'] for e in D.load(D.OUT/'model.json')['scenarios']['baseline']['attribution']['edges']}
    classes=defaultdict(list); identities=[]
    for key, phases in grouped.items():
        regions=sorted({r for p in phases for r in p['regions']})
        sig=signature(phases,plan)
        row=dict(group=key,signature=sig,phases=[p['phase'] for p in phases],
            regions=regions,phase_count=len(phases),
            original_plan_phase_hashes=[digest(p) for p in phases],
            payload_sources=[dict(phase=p['phase'],K=p['K'],x_source=p['x_source'],
                tensors=[m['tensor'] for m in p['mats']]) for p in phases],
            expected_output_rows=sum(m['rows'][1]-m['rows'][0] for p in phases for m in p['mats']),
            input_bytes_per_die_node=sum(((p['K']+63)//64)*256 for p in phases),
            exact_pair_coverage=key in paired['groups'],
            critical_in_current_DAG=key.rsplit('.st',1)[0] in critical,
            needs_admission_pair=len(phases)>1)
        identities.append(row);classes[sig].append(row)
    pending=[]
    for sig, members in classes.items():
        if not any(m['needs_admission_pair'] for m in members):continue
        if any(m['exact_pair_coverage'] for m in members):continue
        selected=sorted(members,key=lambda m:(not m['critical_in_current_DAG'],m['group']))[0]
        pending.append(dict(signature=sig,selected_group=selected['group'],
            eligible_structural_members=[m['group'] for m in members],
            phases=selected['phases'],phase_count=selected['phase_count'],
            regions=selected['regions'],paired_runs=2*len(selected['regions']),
            critical=any(m['critical_in_current_DAG'] for m in members),
            expected_output_rows_both_modes=2*selected['expected_output_rows'],
            expected_W_VMW_VMS_assertions=6*selected['expected_output_rows'],
            input_bytes_per_physical_die_node=selected['input_bytes_per_die_node'],
            archive_supported_K_MAX=6144,archive_supported_PHASE_MAX=8,
            frontend_compiles=0,archive_compiles=0,
            owner='Epicurus sole retained observer',
            source_selection='Existing node_groups and node_image; select this exact group rather than hardcoded L20. Reuse SAME final2 archive and caller; no new engine/archive build.',
            qualification='New tensor/input/rank/program identity never inherits exactness from a structural class.',
            phase_tag_wrap=selected['phase_count']>4,
            admission_budget_cycles=None))
    pending.sort(key=lambda r:(not r['critical'],r['selected_group']))
    family_budget=defaultdict(lambda:dict(classes=0,paired_runs=0,groups=[],output_rows_both_modes=0,
                                        W_VMW_VMS_assertions=0))
    for p in pending:
        family=p['selected_group'].split('.',1)[1].rsplit('.st',1)[0]
        v=family_budget[family];v['classes']+=1;v['paired_runs']+=p['paired_runs'];v['groups'].append(p['selected_group'])
        v['output_rows_both_modes']+=p['expected_output_rows_both_modes']
        v['W_VMW_VMS_assertions']+=p['expected_W_VMW_VMS_assertions']

    # All 40 canonical layers, every expert alternative. This inventory is not
    # the seven retained golden programs and must not be silently collapsed by
    # field_rep() or by a representative matrix's dimensions alone.
    canonical_classes=defaultdict(lambda:dict(count=0,layers=set(),stages=set(),examples=[]))
    selected_matrix_owners=[]
    bylayer=defaultdict(Counter);canonical_aliases=Counter();canonical_rows=0
    with gzip.open(CAN/'matrix_map.jsonl.gz','rt') as f:
        for line in f:
            r=json.loads(line);L=r['layer']
            if not isinstance(L,int) or not 0<=L<40:continue
            canonical_rows+=1;a=alias_class(r['alias']);nodes=sorted(aliases.get(a,()))
            shape=dict(alias_class=a,format=r['format'],K=r['K'],rows=r['rows'],
                segments=r['segments'],rank_slices=r['rank_slices'],
                read=r['t_read_words_max'],issue=r['issue_cycles_LAT8_condition'],conversion=r['conversion'])
            h=digest(shape);v=canonical_classes[h]
            v['shape']=shape;v['count']+=1;v['layers'].add(L);v['stages'].add(r['stage'])
            if len(v['examples'])<2:v['examples'].append(dict(tensor=r['tensor'],stage=r['stage'],alias=r['alias']))
            v['retained_program_nodes']=nodes
            bylayer[L][a]+=1;canonical_aliases[a]+=1
            if r['expert'] is None or r['expert'] in gold[L]['experts']:
                selected_matrix_owners.append(dict(layer=L,tensor=r['tensor'],alias=r['alias'],
                    stage=r['stage'],expert=r['expert'],format=r['format'],K=r['K'],rows=r['rows'],
                    segments=r['segments'],rank_slices=r['rank_slices'],structural_class=h,
                    ordered_physical_plan_hash=digest(r['plans']),retained_program_nodes=nodes))
    canonical=[]
    for h,v in canonical_classes.items():
        v['layers']=sorted(v['layers']);v['stages']=sorted(v['stages'])
        canonical.append(dict(signature=h,**v))
    canonical.sort(key=lambda r:(r['shape']['alias_class'],r['signature']))

    su=D.load(OUT/'inputs/SU_physical_admission.json')
    face=su['legacy_slot_contract']['VM_faces_bits']
    norm=next(r for r in su['norm'] if r['variant']=='hc')
    rejection=dict(norm=dict(verdict='REJECT_SELECTED_NATIVE_CORRIDOR',
        input_bits_per_candidate_edge=norm['cost']['input_bits_per_cycle'],native_face_bits=face,
        required_parallel_width_ratio=norm['cost']['input_bits_per_cycle']/face,
        candidate_hz=1200000000,native_face_hz=900000000,
        positive_composed_gain=None,admission=False),
        swiglu=dict(verdict='REJECT_SELECTED_NATIVE_CORRIDOR_AND_TIMING',
        input_bits_per_candidate_edge=su['swiglu']['input_bits_per_cycle'],native_face_bits=face,
        required_parallel_width_ratio=su['swiglu']['input_bits_per_cycle']/face,
        SS_ps=su['swiglu']['prelayout_lane_screen']['ss_setup_wns_ps'],
        FF_ps=su['swiglu']['prelayout_lane_screen']['ff_hold_wns_ps'],positive_composed_gain=None,admission=False),
        disposition='Selected configurations cannot borrow serial native corridors. Functional records retained; no infinite HOLD or silent larger ports. Baseline SU latency retained, no rescue configuration selected.')
    src=[OUT/'inputs/retained_plan.json.gz',OUT/'inputs/SU_physical_admission.json',
         OUT/'inputs/all40_golden_json.json.gz',
         CAN/'matrix_map.jsonl.gz',CAN/'stage_map.json',D.A.RECOVERY/'paired_field_gate/model.json',
         D.OUT/'model.json',D.ROOT/'tools/dsrom_recovery_coverage_manifest.py',
         D.ROOT/'results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz',
         D.ROOT/'results/uarch/dsrom_native_port_su_pair_20261005/model.json',
         D.ROOT/'results/uarch/ds_recovery_cost_delta_20261005/inputs/physcost_layer.json',
         D.ROOT/'tools/dsrom_s81_fulldie.py']
    return dict(schema='opentallas.dsrom-recovery.coverage-manifest.v1',
        inputs={str(p.relative_to(D.ROOT)):D.sha(p) for p in src},
        exact_paired_groups=sorted(paired['groups']),retained_program_layers=plan['layers'],
        retained_phase_count=len(plan['phases']),retained_group_count=len(grouped),phase_identity_mapping=identities,
        minimum_additional_retained_structural_classes=pending,family_budgets=dict(family_budget),
        additional_pairs=sum(p['paired_runs'] for p in pending),
        canonical_matrix_count=canonical_rows,canonical_layers=sorted(bylayer),
        canonical_matrix_classes=canonical,canonical_by_layer={L:dict(v) for L,v in bylayer.items()},
        actual_selected_matrix_owners=selected_matrix_owners,
        actual_golden_program_inputs=[dict(layer=r['layer'],source_json_path=r['path'],
            json_sha256=hashlib.sha256(r['json_bytes'].encode()).hexdigest(),
            selected_experts_in_record_order=gold[r['layer']]['experts'],
            input_sha256=gold[r['layer']]['input_sha256'],output_sha256=gold[r['layer']]['output_sha256'],
            trace_sha256=gold[r['layer']]['trace_sha256'],npz_path=r['npz_path'],
            npz_present=r['npz_present'],npz_bytes=r['npz_size'],
            accepted_runtime_journal_qualified=False) for r in golden_sources],
        canonical_aliases_uncovered_by_retained_program=[a for a in canonical_aliases if a not in aliases],
        coverage_limit='Class equality selects observer work only. All40 actual golden selections are now bound to canonical matrix owners; each new phase/rank still requires exact program binding. Thirty-three unretained layer programs cannot inherit measured gain via field_rep().',
        next_exact_binding=dict(owner='Arendt source schedules; Epicurus sole observer; Maxwell composition',
            action='Use canonical tensor/stage map and existing retained golden weight-op/input metadata to emit phase lists for the 33 missing layers; select actual six EIDs in program order, no new inference or payload duplication. Compare their region signatures to this manifest before adding any run.',
            all_layer_selected_EID_golden_records_available=True,
            actual_full40_native_accepted_journal_available=False,
            missing_layers=sorted(set(range(40))-set(plan['layers'])),
            unknown_new_classes='Must derive from actual missing program phase lists, not all-384 capacity reservation or representative-layer extrapolation',
            new_archives=0,new_frontend_builds=0),
        active_SU_selection=rejection,
        native_port_hc_pair=hc_pair_census(),
        issuer_slot_proposal=dict(name='sp_capture/sp_pq_issuer',instances_per_field_die=1,
            parent_model='results/uarch/ds_recovery_cost_delta_20261005/inputs/physcost_layer.json',
            parent_geometry_source='tools/dsrom_s81_fulldie.py::geometry/sp_capture slab',
            parent_capture_origin_um=[15182.64,13471.92],
            requested_subbox_um=[15186.96,13476.24,15251.76,13484.88],
            reservation_um2=559.872,incremental_reservation_mm2_per_die=.000559872,
            raw_FF=47,raw_FF_body_floor_um2=47*.2916,stream_clock_target_hz=1200000000,
            added_cycles=0,accepted_II=1,additional_ROM_reads=0,
            ports=dict(active_descriptor_capture=33,registered_ROM_address=14,existing_stream_word=48),
            other_cell_terms='up to99mux2+14bit base add+16bit increment/equality+protection/enable/clock/reset/localwire',
            accounting='Separate new issuer debit, one per die not128 per region. Proposed suballocation of named capture/controller home, not claimed spare cells or routing-channel credit.',
            fitted=False,existing_capture_cell_overlap_checked=False,loaded_SS_FF_qualified=False,
            required_next='Epicurus use named stream-side issuer home; detailed cells must reconcile with capture/control owner before physical adoption. No boundary/clock change or blanket waiting for pointer.'),
        active_composition=dict(baseline_SU_latency_retained=True,
            bounded_field_serial_AR_us=paired['serialized_projection']['AR_us'],
            bounded_field_overlap_AR_us=paired['overlapped_projection']['AR_us'],
            matched_L20_only_saved_us=paired['matched_L20_AR_saved_us'],
            combined_norm_SwiGLU_gain_admitted=None,field_adoption=False,physical_build_admitted=False),
        observer_budget_policy='First exact manifest; no launch here. Epicurus reuses existing observer/archive; report all source acceptance/GO/end/W/VMW/VMS/idle events and identical bytes/order. Single-phase groups have no scheduling-overlap opportunity; no paired gain assigned.')


if __name__=='__main__':
    d=build();(OUT/'manifest.json').write_text(json.dumps(d,indent=1,sort_keys=True)+'\n')
    print(json.dumps({k:d[k] for k in ('retained_phase_count','retained_group_count','additional_pairs','family_budgets','canonical_matrix_count')}))
