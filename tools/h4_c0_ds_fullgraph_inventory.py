"""Canonical DS fullgraph runtime/home/provider/witness inventory, not admission.

Reads metadata and independent expected-byte contracts. Executes no numerical
operator, provider initializer or checkpoint projection. Missing readiness is
explicit; source-level implementation never becomes hardware/execution credit.
"""
import argparse
import ast
from collections import Counter,defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
from h4_c0_ds_runtime_bindings import ordinary
from h3_deepseek_streaming_linear import footprint
from h3_deepseek_staged_native import plan

NATIVE='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264'
DISPATCH='bcf7d800aa64aeff92b8a1954cab328911c400025179d6a9ab9f211a934c253c'
REVIEWED_REFERENCES={'91c803a93df18e011cd7ee6c5e0a84c8fc091136718ca329e5f2928349b3f342',
 'ccc0b2003b87b530b95665b937a1fbb1f523cf42347e1f915005a573bc4f87a2',
 'e0305a2b6a93ce1cf43e9b2dee414c64b9884a754c076359abc43a83f9609157',
 '75798a7c8de7adbade6c0f6a8a3303621bb78f49276d596f23c6e807e9062b74'}
STREAM={'linear_q':'StreamingLinear','mv':'StreamingFloat','linear_bf16':'StreamingFloat',
        'wo_a_part':'StreamingFloat','all_gather':'StreamingGather','index_scores':'StreamingIndex',
        'all_reduce':'TiledContinuation'}


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def load(p):
    return json.loads(gzip.decompress(Path(p).read_bytes()) if str(p).endswith('.gz') else Path(p).read_bytes())


def opcode_set(path):
    tree=ast.parse(Path(path).read_bytes())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NATIVE' for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise ValueError('actual Machine native opcode set absent')


def route(op,name,b):
    if b['kind']=='immutable_weight_provider' and isinstance(b['logical_tensor'],list) and all(isinstance(x,str) for x in b['logical_tensor']):return 'new_ordered_checkpoint_matrix_concat'
    if b['kind']=='immutable_weight_provider':return 'accepted_route_checkpoint_weight' if isinstance(b['logical_tensor'],list) else 'locked_checkpoint_weight'
    if b['kind']=='immutable_parameter_provider':return 'locked_checkpoint_parameter'
    if b['kind']=='zero_initial_partial_destination':return 'source_declared_zero_destination'
    if b['kind']=='explicit_auxiliary_provider':
        if op['family']=='all_gather' and name=='ownership_mask':return 'source_producer_extent_gather'
        if op['family']=='kv_gather':return 'accepted_history_selection'
        if op['family']=='topk_merge' and name=='scores':return 'ordered_candidate_rank_merge'
        return 'immutable_auxiliary_image_required'
    if b['kind']!='versioned_operand':return 'UNSUPPORTED_PROVIDER_KIND'
    if ordinary(op,name,b):return 'new_typed_addressed_source_view'
    if op['family']=='all_reduce':return 'source_group_tiled_continuation'
    if op['family']=='all_gather':return 'source_producer_extent_gather'
    if op['family']=='attend':return 'source_attention_reshape_concat'
    if op['family']=='topk_merge':return 'ordered_candidate_rank_merge'
    if name=='route_weight':return 'accepted_source_route_scalar'
    if name=='expert_outputs':return 'ordered_seven_expert_sources'
    if name in ('query_codes','query_exp'):return 'addressed_query_compound_fields'
    if op['family']=='index_scores' and name in ('keys','key_codes','key_exp'):return 'paired_accepted_history_rows'
    return 'UNSUPPORTED_SOURCE_VIEW'


def references(paths,native_hash):
    rows={};pins={}
    for path in paths:
        path=Path(path);c=load(path)
        if c.get('native_program_sha256')!=native_hash or sha(path) not in REVIEWED_REFERENCES or c.get('golden_stimuli_in_executor') is True:
            raise ValueError('independent source-bound observation-only reference required')
        for source,digest in c['reference_source_sha256'].items():
            if sha(source)!=digest:raise ValueError('independent reference source changed')
        pins[str(path.resolve())]=sha(path)
        for e in c['expectations']:
            key=(e['PC'],e['version'],e['rank'],e['field'])
            if key in rows:raise ValueError('overlapping independently committed reference identities')
            p=path.parent/e['path']
            if sha(p)!=e['file_sha256']:raise ValueError('independent expected payload file changed')
            rows[key]=dict(reference=str(path.resolve()),reference_sha256=pins[str(path.resolve())],
                          **{k:e[k] for k in ('shape','dtype','generation','payload_sha256','file_sha256','path')})
    return rows,pins


def build(native_path,dispatch_path,homes_path,manifest_path,provider_root,reference_paths,out,effective_native_path=None):
    out=Path(out)
    if out.exists():raise ValueError('fresh source-pinned inventory directory required')
    if sha(native_path)!=NATIVE or sha(dispatch_path)!=DISPATCH:raise ValueError('exact corrected fullprogram/dispatch required')
    n=load(native_path);d=load(dispatch_path);home=load(homes_path);homes=home['homes'] if isinstance(home,dict) else home
    if len(n['instructions'])!=2213 or len({o['family'] for o in n['instructions']})!=30:
        raise ValueError('complete2213PC/30family canonical scope')
    if [(o['pc'],o['family']) for o in n['instructions']]!=[(o['pc'],o['family']) for o in d['PC_dispatch']]:
        raise ValueError('complete canonical dispatch identity mismatch')
    root=Path(provider_root);manifest=load(manifest_path)
    effective_pin=None
    if effective_native_path is not None:
        effective=load(effective_native_path)
        effective_content=hashlib.sha256(json.dumps(effective,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if effective_content!='9d538b80f1e8d3eada8ed4c967426bab5649339ff6fa2f0535eb393f7b15145d':
            raise ValueError('reviewed exact R41/R43 home-only native content required')
        original_homes_path=root/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/actual_DeepSeek_homes.json.gz'
        if sha(original_homes_path)!='e4751c4164368e98295f78d4270bf65992a8a7ee273a04ceffa528072f855424':
            raise ValueError('immutable original source home directory')
        original_homes=load(original_homes_path)['homes']
        if homes[:len(original_homes)]!=original_homes or len(homes)!=290730:
            raise ValueError('actual reviewed expanded directory prefix/count')
        for old,now in zip(n['instructions'],effective['instructions']):
            for a,b in zip(old['writes'],now['writes']):
                for i in b['home_indices']:
                    if not 0<=i<len(homes) or homes[i]['version']!=b['version']:
                        raise ValueError('effective allocated home version/index')
        effective_pin=dict(path=str(Path(effective_native_path).resolve()),artifact_sha256=sha(effective_native_path),
            content_sha256=effective_content,scope='reviewed source home-only expansion; initializer/runtime admission not asserted')
        n=effective

    code_root=Path(__file__).resolve().parent
    sources=[Path(__file__),code_root/'h4_c0_ds_runtime_bindings.py',code_root/'h3_deepseek_complete_native.py',
             code_root/'h3_deepseek_staged_native.py',code_root/'h3_deepseek_streaming_linear.py',code_root/'h4_c0_ds_source_views.py']
    for name in ('h3_ds_connected_provider_r37','ds_hbm_source_merge_r37','ds_hbm_attention_views_r37',
        'h3_ds_history_provider_r36','h3_ds_query_provider_r36','h3_ds_checkpoint_provider_r33',
        'ds_hbm_storage_home_binding_r41','ds_hbm_bound_engine_r43'):
        p=root/'tools'/(name+'.py')
        if p.exists():sources.append(p)
    pins={str(p.resolve()):sha(p) for p in sources}
    supported=opcode_set(code_root/'h3_deepseek_complete_native.py')
    witness,refpins=references(reference_paths,NATIVE)
    templates={};pcs=[];families=defaultdict(list);kind_counts=Counter();auxmissing=Counter();gaps=Counter()
    for tid,t in n['templates'].items():
        used=set(i['op'] for i in t['code'])
        f=footprint(t)
        staged=None if t['family'] in STREAM else plan(t)
        templates[tid]=dict(family=t['family'],opcode_set=sorted(used),unsupported_opcodes=sorted(used-supported),
            source_program_sha256=hashlib.sha256(json.dumps(t,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            CPU_native_live_and_transient_bytes=f['typed_live_bytes']+f['transient_and_output_reserve_bytes'],
            staged_workspace_upper_bytes=None if staged is None else staged['workspace_upper_bytes'],
            staged_32MiB_fits=None if staged is None else staged['fits'],
            actual_runtime_path=STREAM.get(t['family'],'StagedMachine'),
            hardware_latency_cycles=None,provider_runtime_bindings={})
    for op in n['instructions']:
        fields=[];pcgaps=[];missing=[];required=[];homegaps=[];compounds=op.get('compound_output_fields',{})
        ranks=[r for r in op['rank_bindings'] if not r.get('empty_owned_extent')]
        for tid,bs in op['provider_bindings'].items():
            specs=n['templates'][tid]['providers']
            for name,b in bs.items():
                k=route(op,name,b);kind_counts[k]+=1
                info=dict(path=k,provider_kind=b['kind'],shape=specs[name]['shape'],dtype=specs[name]['dtype'],
                    source_binding_sha256=hashlib.sha256(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest())
                fields.append(dict(template=tid,field=name,**info));templates[tid]['provider_runtime_bindings'][name]=k
                if k.startswith('UNSUPPORTED'):pcgaps.append(dict(field=name,template=tid,gap=k))
                if k=='immutable_auxiliary_image_required':
                    key=f"{op['pc']}/{tid}/{name}";record=manifest.get('view_bindings',{}).get(key)
                    if record is None:
                        missing.append(key);auxmissing[name]+=1
                    elif record.get('source_binding')!=b:
                        pcgaps.append(dict(field=name,template=tid,gap='actual_auxiliary_binding_differs'))
        for rb in ranks:
            tid=rb['template']
            if templates[tid]['unsupported_opcodes']:pcgaps.append(dict(rank=rb['rank'],gap='unsupported_native_opcode'))
            if templates[tid]['staged_32MiB_fits'] is False:pcgaps.append(dict(rank=rb['rank'],gap='staged_actual_workspace_exceeds32MiB'))
            for w in op['writes']:
                indices=[i for i in w['home_indices'] if rb['rank'] in homes[i]['rank_group']]
                if not indices or any(homes[i]['version']!=w['version'] for i in indices):
                    homegaps.append(dict(version=w['version'],rank=rb['rank']))
                for field in ['data']+compounds.get(w['native_result_binding']['result'],[]):
                    key=(op['pc'],w['version'],rb['rank'],field)
                    required.append(dict(version=w['version'],rank=rb['rank'],field=field,independent_reference_bound=key in witness))
        for g in pcgaps:gaps[g['gap']]+=1
        pcs.append(dict(PC=op['pc'],family=op['family'],scope='PC11_onward_required' if op['pc']>=11 else 'historical_prefix_owned_by_Kepler',
            dependency_PCs=op['dependencies'],source_read_versions=[r['version'] for r in op['reads']],
            active_ranks=[r['rank'] for r in ranks],rank_templates=[[r['rank'],r['template']] for r in ranks],
            buffer_continuations=[dict(rank=r['rank'],buffers=r['buffer_programs']) for r in ranks if r.get('buffer_programs')],
            output_versions=[w['version'] for w in op['writes']],compound_output_fields=compounds,
            producer_extents=[dict(version=w['version'],extent=w.get('producer_extent')) for w in op['writes']],
            collective_alias_writers=[dict(primary=b['write_version'],alias=w['version'],source_view=w['native_result_binding'])
                for b in (ranks[0].get('buffer_programs',[]) if ranks else []) for w in op['writes']
                if w['version']!=b['write_version'] and w['native_result_binding'].get('buffer')==next(x['native_result_binding'].get('buffer') for x in op['writes'] if x['version']==b['write_version'])],
            operand_bindings=fields,output_home_gaps=homegaps,actual_runtime_gaps=pcgaps,
            auxiliary_images_absent_from_current_manifest=missing,independent_witness_slots=required,
            required_nonpublication_witness='released checkpoint descriptor selection/retirement' if op['family']=='expert_fetch' else None,
            actual_execution_qualified=False,hardware_qualified=False))
        families[op['family']].append(pcs[-1])
    summary=dict(status='COMPLETE_CANONICAL_SYSTEMS_INVENTORY_NOT_EXECUTION_ADMISSION',PCs=2213,families=30,
        required_after_PC10=2202,native_sha256=NATIVE,dispatch_sha256=DISPATCH,homes_sha256=sha(homes_path),
        effective_native=effective_pin,effective_home_records=len(homes),manifest_sha256=sha(manifest_path),
        collective_alias_versions_requiring_additive_publication=sum(len(o['collective_alias_writers']) for o in pcs),
        template_count=len(templates),unsupported_native_opcodes=sorted({v for t in templates.values() for v in t['unsupported_opcodes']}),
        runtime_gap_counts=dict(gaps),absent_auxiliary_counts=dict(auxmissing),provider_route_counts=dict(kind_counts),
        missing_rank_output_homes=sum(len(o['output_home_gaps']) for o in pcs),
        independent_bound_witness_slots=sum(sum(w['independent_reference_bound'] for w in o['independent_witness_slots']) for o in pcs),
        required_published_field_witness_slots=sum(len(o['independent_witness_slots']) for o in pcs),
        family_coverage={family:dict(PCs=[o['PC'] for o in rows],count=len(rows),first_PC=rows[0]['PC'],
            required_output_slots=sum(len(o['independent_witness_slots']) for o in rows),
            bound_reference_slots=sum(sum(w['independent_reference_bound'] for w in o['independent_witness_slots']) for o in rows),
            runtime_gaps=sum(len(o['actual_runtime_gaps']) for o in rows),missing_home_slots=sum(len(o['output_home_gaps']) for o in rows)) for family,rows in sorted(families.items())},
        source_pins=pins,reference_contract_pins=refpins,zero_publication_ops_not_auto_qualified=True,
        independent_checkpoint_header_gates='not executed by this inventory; caller needs actual codec,row,K,descriptor and raw-byte receipts',
        resource_composition='Dewey owns source phase/journal/resource projection; no CPU elapsed-time or software-tick hardware credit',
        full_program_GO=False,hardware_qualified=False,full_token_qualified=False,no_new_native_jobs=True)
    out.mkdir(parents=True)
    for name,data in [('PC_bindings',pcs),('template_bindings',templates),('independent_witness_index',[dict(PC=k[0],version=k[1],rank=k[2],field=k[3],**v) for k,v in sorted(witness.items())])]:
        (out/(name+'.json.gz')).write_bytes(gzip.compress(json.dumps(data,sort_keys=True,separators=(',',':')).encode(),mtime=0))
    (out/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    artifacts={str(p):sha(p) for p in sorted(out.iterdir())}
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts=artifacts,source_pins=pins),sort_keys=True,indent=2)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('native','dispatch','homes','manifest','provider_root','out'):p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    p.add_argument('--reference',type=Path,action='append',default=[])
    p.add_argument('--effective-native',type=Path)
    a=p.parse_args();r=build(a.native,a.dispatch,a.homes,a.manifest,a.provider_root,a.reference,a.out,a.effective_native)
    print(json.dumps({k:r[k] for k in ('status','PCs','families','unsupported_native_opcodes','runtime_gap_counts','absent_auxiliary_counts','missing_rank_output_homes','independent_bound_witness_slots','required_published_field_witness_slots')},sort_keys=True))
