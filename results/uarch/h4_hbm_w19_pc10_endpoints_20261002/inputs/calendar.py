#!/usr/bin/env python3
"""Full H3 finite SOFTWARE calendar; explicit provisional cycles, never an RTL oracle.

An interval with repeats is a lossless run-length schedule: repeat i owns the
listed credits on [start+i*stride,start+(i+1)*stride). Conservative batches
retain their ports through retirement. No traffic, admission, or ACK is free.
"""
import argparse
import ast
import math
import re
from collections import Counter, defaultdict
import gzip
import hashlib
import heapq
import json
import sys
import subprocess
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/h3_complete_native_calendar_20261002'
LOWERING = 'results/uarch/h3_versioned_lowering_20261002'
DISTRIBUTED = 'results/uarch/h3_distributed_norm_endpoint_20261002'
PINS = [f'{folder}/{target}.json.gz' for folder in (LOWERING, DISTRIBUTED)
        for target in ('Qwen', 'DeepSeek')] + [
    DISTRIBUTED + '/model.json', LOWERING + '/manifest.json',
    'results/uarch/qwen_hbm_connected_20261001/common_HBM_backend_provider_binding_r2.json',
    'results/uarch/qwen_hbm_resource_schedule_20261002/required_phase_provider_r7.json',
    'results/uarch/qwen_hbm_downstream_contract_20261002/provider_ports_r8.json',
    'rtl/gpu/ot_gpu_rf_service.sv', 'rtl/gpu/ot_gpu_full_sm_service.sv',
    'tools/deepseek_hbm_complete_memory.py',
    'tools/qwen_hbm_complete_service_provider.py',
    'tools/deepseek_hbm_complete_packed_index_provider.py',
    'tools/h3_complete_native_calendar.py']


def positive(n, label):
    if type(n) is not int or n < 1:
        raise ValueError('positive explicit integer required: ' + label)
    return n


def ceil(n, d):
    return (n + d - 1) // d


def read_json(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as f:
            return json.load(f)
    return json.loads(Path(path).read_text())


PORTABLE_INPUTS = None


def portable_calendar_blob(path, commit, archive):
    """Strict hash-addressed input lookup; never probes historical Git refs."""
    relative=Path(path)
    if relative.is_absolute():relative=relative.relative_to(ROOT)
    if '..' in relative.parts:raise ValueError('portable input path escape')
    index=read_json(Path(archive)/'index.json')
    rows=[r for r in index['inputs'] if r['path']==relative.as_posix() and
        (r['commit'].startswith(commit) or commit.startswith(r['commit']))]
    if len(rows)!=1:raise ValueError('missing or ambiguous portable calendar source pin '+commit+':'+str(relative))
    row=rows[0]
    if row['storage']=='canonical_tracked_path':
        local=ROOT/row['path']
        if not local.is_file():raise ValueError('canonical committed archive required: '+row['path'])
        raw=local.read_bytes()
    elif row['storage']=='hash_blob_gzip':
        raw=gzip.decompress((Path(archive)/'blobs'/(row['sha256']+'.gz')).read_bytes())
    else:raise ValueError('unknown portable storage kind')
    if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('portable source byte hash mismatch '+row['path'])
    return raw


def pinned_calendar_blob(path, commit):
    if PORTABLE_INPUTS is not None:return portable_calendar_blob(path,commit,PORTABLE_INPUTS)
    return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)


def export_calendar_portable_inputs(output):
    """Archive exact existing input pins; models and historical verdicts immutable."""
    output=Path(output)
    if output.exists():raise ValueError('fresh portable input closure required')
    roots=[('a67150839',OUT+'/provider_v1_mtp_join_r4/final_physical/manifest.json'),
        ('2e76d4f96',OUT+'/ds_r33_calendar_adapter_r1/provider_final/manifest.json'),
        ('4e8f517fc',OUT+'/ds_r33_once_reprice_r1/model/manifest.json')]
    requested={}
    for commit,path in roots:
        manifest_raw=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
        requested[(commit,path)]=hashlib.sha256(manifest_raw).hexdigest()
        manifest=json.loads(manifest_raw)
        for source,record in manifest['source_pins'].items():
            requested[(record.get('commit',commit),source)]=record['sha256']
    physical=json.loads(pinned_calendar_blob('results/uarch/h4_v1_g0_model_20261002/physical_join_r1/final/model.json','620c078de78cc55ddb5562b1d5d7171d8ef944ca'))
    for record in physical['source_pins']:
        requested[(record['commit'],record['path'])]=record['sha256']
    # Source/binary receipts have an explicit literal TP96 producer closure.
    folder=ROOT/OUT/'tp96_literal_collective_join_r1/inputs'
    record=read_json(folder/'normal_record.json');binary=read_json(folder/'binary_sources.json');preflight=read_json(folder/'preflight.json')
    for path,sha in {**record['source_sha256'],**binary['pins'],**preflight['source_sha256']}.items():
        requested[(record['source_commit'],path)]=sha
    path='results/uarch/h3_versioned_lowering_20261002/DeepSeek.json.gz';commit='781046c9775880183bd7f45a06ab101e98c66cac'
    requested[(commit,path)]=hashlib.sha256(subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)).hexdigest()
    # The producer originals needed by the later source adapter remain archived,
    # even if two manifests refer to one identical blob under different commits.
    for path in ('tools/ds_hbm_group_provider_r34.py','results/uarch/ds_hbm_source_inputs_views_r34_20261002/prepared_join.json'):
        raw=pinned_calendar_blob(path,'0b4ab421b');requested[('0b4ab421b',path)]=hashlib.sha256(raw).hexdigest()
    rows=[];blobs={}
    canonical='results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
    for (commit,path),want in sorted(requested.items()):
        raw=pinned_calendar_blob(path,commit)
        if hashlib.sha256(raw).hexdigest()!=want:raise ValueError('input pin archive export mismatch '+path)
        storage='canonical_tracked_path' if path==canonical else 'hash_blob_gzip'
        if len(raw)>1048576 and storage!='canonical_tracked_path':
            # Reuse immutable bulk already tracked by an intake prerequisite.
            for ref in ('HEAD','main'):
                found=subprocess.run(['git','show',ref+':'+path],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
                if found.returncode==0 and hashlib.sha256(found.stdout).hexdigest()==want:
                    storage='canonical_tracked_path';break
        if storage=='hash_blob_gzip':blobs[want]=gzip.compress(raw,mtime=0)
        rows.append(dict(commit=commit,path=path,sha256=want,bytes=len(raw),storage=storage))
    output.mkdir(parents=True);(output/'blobs').mkdir()
    for sha,raw in blobs.items():(output/'blobs'/(sha+'.gz')).write_bytes(raw)
    index=dict(schema='H4_CALENDAR_PORTABLE_EXACT_INPUT_CLOSURE_V1',inputs=rows,
        roots=[dict(commit=c,path=p) for c,p in roots],unique_archived_blobs=len(blobs),
        archived_bytes=sum(map(len,blobs.values())),canonical_native_duplicated=False,
        historical_models_altered=False,hardware_admitted=False)
    (output/'index.json').write_text(json.dumps(index,sort_keys=True,indent=2)+'\n')
    return index


def source_bytes(path, commit=None):
    """Read an immutable canonical blob without duplicating a producer artifact."""
    path=Path(path)
    if commit is None:return path.read_bytes()
    if not re.fullmatch('[0-9a-f]{7,40}',commit):raise ValueError('immutable source commit required')
    relative=path.relative_to(ROOT) if path.is_absolute() else path
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('source blob path escape')
    if PORTABLE_INPUTS is not None:return portable_calendar_blob(relative,commit,PORTABLE_INPUTS)
    raw=pinned_calendar_blob(relative.as_posix(),commit)
    local=ROOT/relative
    if local.exists() and local.read_bytes()!=raw:raise ValueError('canonical source bytes differ from pinned commit')
    return raw


def load_ds_forward_builders():
    """Compile pinned builder definitions only; no runtime numerical/provider run."""
    import numpy as np
    base=ROOT/OUT/'final_ds_bed325f89';pins=read_json(base/'producer_pins.json')['files']
    path=base/'h3_deepseek_complete_native.py.source';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pins[path.name]['sha256']:raise ValueError('DS builder source pin mismatch')
    N=types.ModuleType('source_pinned_DS_builder');N.__dict__.update(np=np,Counter=Counter,math=math)
    tree=ast.parse(raw);body=[n for n in tree.body if isinstance(n,ast.FunctionDef) or isinstance(n,ast.ClassDef) and n.name=='Builder'
        or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('NATIVE','FAMILIES') for t in n.targets)]
    exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),N.__dict__)
    N.Builder.topk=N.native_topk
    path=ROOT/OUT/'bounded_provider_milestone/ds/h3_deepseek_streaming_linear.py.source';raw=path.read_bytes()
    files=read_json(path.parent/'files_sha256.json');key='tools/h3_deepseek_streaming_linear.py'
    if hashlib.sha256(raw).hexdigest()!=files[key]:raise ValueError('DS forward builder source pin mismatch')
    S=types.ModuleType('source_pinned_DS_forward_builder');S.__dict__.update(N=N,np=np,Counter=Counter,math=math)
    tree=ast.parse(raw);body=[n for n in tree.body if isinstance(n,ast.FunctionDef) or isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id in ('K_BLOCK','ROW_TILE') for t in n.targets)]
    exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),S.__dict__)
    return N,S


def compile_ds_forward_leaf_catalog(dispatch, native_program, N, S):
    """Actual retained forward builder leaves and source-derived loop counts.

    Catalogs code, not exporter opcode strings. Index row/ rank constants are
    parameterized source builder arguments; their hardware dispatch stays open.
    Source whole-array SSA remains catalogued for staged families.
    """
    leaves={};templates={};paths=Counter()
    def leaf(program,builder,args):
        raw=json.dumps(program,sort_keys=True,separators=(',',':')).encode();key=hashlib.sha256(raw).hexdigest()
        if key not in leaves:
            counts=Counter();batches=Counter()
            for node in program['code']:
                n=max(1,math.prod(node['shape']));counts[node['op']]+=n;batches[node['op']]+=ceil(n,128)
            leaves[key]={('program_ref' if builder=='retained_original_template' else 'program'):
                ('results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz#/templates/'+args[0] if builder=='retained_original_template' else program),
                'code_sha256':hashlib.sha256(json.dumps(program['code'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                'native_scalars':dict(counts),'native_batches128':dict(batches),
                'source_builder':builder,'source_builder_args':args,
                'hardware_command_binding':False}
        return key
    for tid,t in dispatch['templates'].items():
        source=native_program['templates'][tid];plan=t['plan'];path=t['execution_path'];calls=[]
        sh=source['shape_parameters'];family=source['family']
        if t['family']!=family:raise ValueError('forward leaf family source mismatch')
        if path in ('forward_streaming_Q8_matvec','forward_streaming_float_matvec'):
            if plan['rows']!=sh.get('rows',4) or plan['fullK']!=sh.get('k',32):raise ValueError('forward leaf matrix shape source mismatch')
        if path=='forward_streaming_Q8_matvec' and plan['weight_format']!=source['source_attributes'].get('fmt','fp8'):
            raise ValueError('forward leaf matrix format source mismatch')
        if path=='forward_streaming_float_matvec' and plan['round_output_BF16']!=(family=='linear_bf16'):
            raise ValueError('forward leaf rounding source mismatch')
        def add(program,builder,args,reps,phase,parameters=None):
            if reps:
                calls.append({'leaf':leaf(program,builder,args),'repetitions':positive(reps,'source forward leaf repetitions'),
                    'source_phase':phase,'dynamic_source_parameters':parameters or {}})
        if path=='forward_streaming_Q8_matvec':
            rows=plan['rows'];blocks=plan['blocks'];chunks=plan['chunks8'];padded=plan['tree_padded_chunks'];fmt=plan['weight_format']
            add(S.quant_program(),'quant_program',[],blocks,'quantize_once_per_Kblock')
            for nr,reps in [(128,rows//128),(rows%128,int(rows%128>0))]:
                if not reps:continue
                add(S.block_program(nr,fmt),'block_program',[nr,fmt],blocks*reps,'source_row_tile_then_Kblock_dot')
                add(S.add_program(nr),'add_program',[nr],(chunks*8+padded-1)*reps,'sequential_chunk8_then_adjacent_carry_tree')
                add(S.pack_program(nr),'pack_program',[nr],reps,'BF16_final_once_per_row_tile')
        elif path=='forward_streaming_float_matvec':
            rows=plan['rows'];chunks=ceil(plan['fullK'],8);padded=plan['padded_tree_chunks']
            add(S.pack_program(8),'pack_program',[8],chunks,'BF16_input_chunk8_once')
            for nr,reps in [(128,rows//128),(rows%128,int(rows%128>0))]:
                if not reps:continue
                add(S.float_block_program(nr),'float_block_program',[nr],chunks*reps,'source_row_tile_then_Kchunk8_dot')
                add(S.add_program(nr),'add_program',[nr],(padded-1)*reps,'source_padded_adjacent_carry_tree')
                if plan['round_output_BF16']:add(S.pack_program(nr),'pack_program',[nr],reps,'BF16_final_once')
        elif path=='forward_streaming_index_rows':
            h=plan['heads'];w=plan['fullK'];rows=plan['rows']
            add(S.query_program(h,w),'query_program',[h,w],1,'query_decode_once')
            add(S.index_program(h,w,1,0,0),'index_program',[h,w,1,0,0],rows,'source_independent_key_rows',
                {'first':{'minimum':0,'maximum_exclusive':rows,'source_loop':'for first in range(rows)'},
                 'rank':{'minimum':0,'maximum_exclusive':96,'source_binding':'actual call rank'}})
        elif path=='forward_streaming_gather_columns':
            n=plan['elements'];ranks=plan['ranks']
            for width,reps in [(128,n//128),(n%128,int(n%128>0))]:
                if reps:add(N.recipe('all_gather',{'n':width,'ranks':ranks},{}),'recipe_all_gather',[width,ranks],reps,'source_column_tiles_rank_order')
        elif path=='source_order_live_range_stages':
            add(source,'retained_original_template',[tid],1,'source_order_live_range_stages')
        else:raise ValueError('unsupported forward source path '+path)
        counts=Counter();batches=Counter()
        for call in calls:
            record=leaves[call['leaf']]
            counts.update({op:n*call['repetitions'] for op,n in record['native_scalars'].items()})
            batches.update({op:n*call['repetitions'] for op,n in record['native_batches128'].items()})
        if dict(counts)!=t['executed_primitive_scalar_projection']:raise ValueError('forward leaf instruction/repetition source count mismatch '+tid)
        templates[tid]={'execution_path':path,'calls':calls,'native_scalars':dict(counts),'native_batches128':dict(batches),
            'source_loop_plan':plan,'ordered_dynamic_loop_trace_executed':False,'shared64_movements':None}
        paths[path]+=1
    pcs=[];totals=Counter();batch_totals=Counter()
    for op in dispatch['PC_dispatch']:
        original=native_program['instructions'][op['pc']]
        expected=[]
        for rb in original['rank_bindings']:
            if rb.get('empty_owned_extent'):continue
            ids=[b['template'] for b in rb['buffer_programs']] if rb.get('buffer_programs') else [rb['template']]
            expected.extend((rb['rank'],tid) for tid in ids)
        if op['family']!=original['family'] or op['dependencies']!=original['dependencies'] or [(c['rank'],c['template']) for c in op['calls']]!=expected:
            raise ValueError('forward leaf actual PC/rank/template source mismatch')
        counts=Counter();batches=Counter();bindings=[]
        for call in op['calls']:
            t=templates[call['template']];counts.update(t['native_scalars']);batches.update(t['native_batches128'])
            bindings.append({'rank':call['rank'],'template':call['template'],'SM_partition':call['SM_partition'],
                'leaf_call_refs':list(range(len(t['calls'])))})
        if dict(counts)!=op['projected_executed_primitive_scalars']:raise ValueError('all-PC forward leaf source count mismatch')
        pcs.append({'pc':op['pc'],'family':op['family'],'dependencies':op['dependencies'],'bindings':bindings,
            'native_scalars':dict(counts),'native_batches128':dict(batches),'shared64_movements':None})
        totals.update(counts);batch_totals.update(batches)
    return {'schema':'H4_DS_SOURCE_RESOLVED_FORWARD_LEAF_CATALOG_V1','PCs':len(pcs),'families':len({r['family'] for r in pcs}),
        'leaves':leaves,'templates':templates,'PC_bindings':pcs,'execution_paths':dict(paths),
        'native_scalars':dict(totals),'native_batches128':dict(batch_totals),
        'cost_scope':'actual source128-lane batch obligation counts; positive provisional service inputs required; no RTL rate/clock conversion',
        'source_program_sha256':dispatch['source_program_sha256'],'actual_shared64_movements':None,
        'hardware_full_native_claim':False,'numerical_or_provider_execution':False}


def join_c0_source_lowering(lowering, qwen, native, catalog, qwen_aliases, *, qwen_sha256):
    """Validate reviewed static control records against actual native sources.

    This joins identities and continuations; dynamic movement/leases stay open.
    """
    def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if lowering.get('schema')!='H4_C0_FULL_PC_STATIC_DISPATCH_LOWERING_V1':raise ValueError('C0 static lowering schema mismatch')
    if lowering.get('RTL_admission') or lowering.get('complete_dynamic_numeric_execution'):raise ValueError('C0 static source cannot qualify dynamic execution')
    index={}
    for row in lowering['dispatch']:
        key=(row['model'],row['source_PC'])
        if key in index:raise ValueError('C0 duplicate PC')
        index[key]=row
    expected=set();totals={};qcommands=Counter()
    for model,ops in [('Qwen',qwen['operations']),('DeepSeek',native['instructions'])]:
        for op in ops:
            key=(model,op['pc']);expected.add(key)
            if key not in index:raise ValueError('C0 missing PC')
            row=index[key];sha=qwen_sha256 if model=='Qwen' else catalog['source_program_sha256']
            versions=lambda side:op[side] if model=='Qwen' else [v['version'] for v in op[side]]
            if (row['program_sha256']!=sha or row['family']!=op.get('opcode',op.get('family')) or
                row['dependency_completed_PC_ids']!=op['dependencies'] or row['source_version_refs']!=versions('reads') or
                row['destination_version_refs']!=versions('writes')):raise ValueError('C0 PC source identity/version/dependency mismatch')
            if row['family_hardware_admitted'] or row['source_numeric_payload_executed']:raise ValueError('C0 static PC qualification mismatch')
            if row['state_transition_order']!=['accepted','complete','mirrored_visible_ACK','consumer_accept','reverse_grant','retire']:
                raise ValueError('C0 ACK/lease transition mismatch')
            if model=='Qwen':
                export=op['calendar_export']['physical_primitives'];kernels=export['kernel_invocations'];bound={};count=Counter()
                for binding in row['ordered_leaf_bindings']:
                    k=binding['kernel']
                    if k in bound or k not in kernels:raise ValueError('C0 Qwen kernel binding mismatch')
                    code=qwen['microcode'][k];sequence=[]
                    for step in code:
                        name=step['op'];sequence.extend(['BITCAST_U','XOR','BITCAST_F'] if name=='NEG' else ['COPY'] if name=='MOV' else [qwen_aliases.get(name,name)])
                    if binding['invocations']!=kernels[k] or binding['ordered_lowered_leaf_opcodes']!=sequence or binding['source_order_sha256']!=digest(code):
                        raise ValueError('C0 Qwen retained instruction sequence mismatch')
                    bound[k]=binding;count.update({name:n*kernels[k] for name,n in Counter(sequence).items()})
                if set(bound)!=set(kernels) or dict(count)!=export['native_primitive_commands'] or dict(count)!=row['native_command_counts']:
                    raise ValueError('C0 Qwen primitive repetition mismatch')
                qcommands.update(count)
            else:
                calls=[]
                for rb in op['rank_bindings']:
                    ids=sorted(({rb['template']} if 'template' in rb else set())|{b['template'] for b in rb.get('buffer_programs',[])})
                    calls.append({'rank':rb['rank'],'template_refs':ids,'buffer_programs':rb.get('buffer_programs',[]),
                        'row_interval':rb.get('row_interval'),'empty_owned_extent':rb.get('empty_owned_extent',False),'SM_partition':rb.get('SM_partition')})
                if row['rank_template_calls']!=calls:raise ValueError('C0 DS rank/template interval mismatch')
        totals[model]={'PCs':len(ops),'families':len({o.get('opcode',o.get('family')) for o in ops})}
    if set(index)!=expected:raise ValueError('C0 extra PC')
    if set(lowering['DS_template_catalog'])!=set(catalog['templates']):raise ValueError('C0 template coverage mismatch')
    for tid,t in catalog['templates'].items():
        code=native['templates'][tid]['code'];record=lowering['DS_template_catalog'][tid]
        if (record['ordered_source_code_sha256']!=digest(code) or record['ordered_steps']!=len(code) or
            record['opcode_records']!=dict(Counter(n['op'] for n in code)) or record['bounded_emitter']!=t['execution_path']):
            raise ValueError('C0 retained DS code/continuation source mismatch')
    return {'schema':'H4_C0_SOURCE_FORWARD_CONTINUATION_JOIN_V1','status':'PASS_STATIC_SOURCE_AND_FORWARD_LEAF_JOIN',
        'programs':totals,'DS_templates':len(catalog['templates']),'DS_forward_leaves':len(catalog['leaves']),
        'Qwen_native_command_counts':dict(qcommands),'DS_source128lane_batches':catalog['native_batches128'],
        'ordered_dynamic_movement_executed':False,'shared64_movements':None,'hardware_full_native_claim':False,
        'remaining_gate':'actual ordered bounded continuation operand spans, concrete provider/home generation, finite leases and mirrored ACK receipts',
        'C0_state_transition_order':['accepted','complete','mirrored_visible_ACK','consumer_accept','reverse_grant','retire']}


def compile_ds_forward_parent_interface(catalog, native, residence):
    """Actual parent versions/providers/home references, never fabricated leases."""
    pcs=[];versions=set()
    for row in catalog['PC_bindings']:
        bindings=[b for b in row['bindings'] if catalog['templates'][b['template']]['execution_path'].startswith('forward_')]
        if not bindings:continue
        op=native['instructions'][row['pc']];provider_bindings={}
        for tid in sorted({b['template'] for b in bindings}):
            if tid not in op['provider_bindings']:raise ValueError('forward parent provider declaration missing')
            provider_bindings[tid]=op['provider_bindings'][tid]
            for provider in provider_bindings[tid].values():
                if provider.get('version'):versions.add(provider['version'])
                versions.update(provider.get('additional_versions',[]))
        declared=[v['version'] for side in ('reads','writes') for v in op[side]];versions.update(declared)
        pcs.append({'pc':row['pc'],'family':row['family'],'dependencies':row['dependencies'],
            'reads':op['reads'],'writes':op['writes'],'actual_rank_template_calls':bindings,
            'parent_provider_bindings':provider_bindings,
            'provider_refill_writeback_ACK_reverse':'UNKNOWN_NO_DYNAMIC_PARENT_PROVIDER_RECEIPT'})
    homes=defaultdict(list)
    for index,home in enumerate(residence['homes']):
        if home['version'] in versions:homes[home['version']].append(index)
    return {'schema':'H4_DS_FORWARD_ACTUAL_PARENT_PROVIDER_HOME_INTERFACE_V1','PC_bindings':pcs,
        'source_program_sha256':catalog['source_program_sha256'],'residence_archive':native['residence_archive'],
        'version_home_refs':dict(homes),'missing_version_home_refs':sorted(versions-set(homes)),
        'home_ref_encoding':'canonical residence archive /homes/<index>; retain rank_group, SM, concrete home and birth/retire',
        'native_leaf_reference_fields':['parent_template','call_index','invocation_index','template','code_index','opcode','attrs',
            'result_shape','operand','value','logical_byte_offset','payload_bytes','source_parameters for dynamic index'],
        'provider_receipt_required':['PC/version/rank/SM/generation','parent LOAD provider declaration','source tile/window view',
            'concrete provider/home identity','accepted finite refill/writeback credit','visible two-mirror ACK',
            'consumer capture','matched reverse grant','source last use'],
        'fixture_observer_scope':'CPU fixture observation cannot close a parent provider movement or hardware gate',
        'physical_admission':False,'hardware_full_native_claim':False}


def resolve_ds_forward_parent_home(interface, residence, *, pc, version, rank, SM):
    rows=[r for r in interface['PC_bindings'] if r['pc']==pc]
    if len(rows)!=1:raise ValueError('actual forward parent PC required')
    row=rows[0]
    if not any(b['rank']==rank for b in row['actual_rank_template_calls']):raise ValueError('actual forward parent rank missing')
    allowed={v['version'] for side in ('reads','writes') for v in row[side]}
    for group in row['parent_provider_bindings'].values():
        for provider in group.values():
            if provider.get('version'):allowed.add(provider['version'])
            allowed.update(provider.get('additional_versions',[]))
    if version not in allowed:raise ValueError('actual forward parent version missing')
    if type(SM)!=int or not 0<=SM<32:raise ValueError('actual forward SM extent')
    matches=[]
    for index in interface['version_home_refs'].get(version,[]):
        home=residence['homes'][index]
        if home['version']!=version:raise ValueError('canonical parent home version mismatch')
        if home['SM']==SM and rank in home.get('rank_group',[home.get('rank',0)]):
            retirement=home.get('retire_pc')
            if home['birth_pc']<=pc and (retirement is None or pc<=retirement):matches.append((index,home))
    if len(matches)!=1:raise ValueError('UNKNOWN actual parent physical home absent or ambiguous for PC/version/rank/SM')
    return matches[0]


def load_v1_cost_api(commit):
    """Import analytical cost/lease functions only from the immutable producer."""
    raw=source_bytes('tools/h4_v1_g0_model.py',commit)
    names={'positive','contract','latency_key','command_cost','reconcile_cost'}
    tree=ast.parse(raw);body=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:body.append(node)
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('DEFAULT','V1','ALIASES') for t in node.targets):body.append(node)
    ns={'math':math};exec(compile(ast.Module(body=body,type_ignores=[]),'pinned_V1_cost_API','exec'),ns)
    return types.SimpleNamespace(**{name:ns[name] for name in names})


def bind_kepler_state_directory(native, directory, producer_source, native_sha256):
    """Replay the actual finite state allocator; no permanent native copy."""
    names={'output_spec','compile_directory'};tree=ast.parse(producer_source);body=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:body.append(node)
        elif isinstance(node,ast.Assign):body.append(node)
    ns={'math':math};exec(compile(ast.Module(body=body,type_ignores=[]),'pinned_Kepler_state_allocator','exec'),ns)
    expected=json.loads(json.dumps(ns['compile_directory'](native,native_sha256)))
    if directory!=expected:raise ValueError('Kepler state directory differs from retained source allocator')
    by_rank=defaultdict(list)
    for row in directory['rows']:by_rank[row['rank']].append(row)
    for rows in by_rank.values():
        rows.sort(key=lambda row:row['base'])
        for a,b in zip(rows,rows[1:]):
            if a['base']+a['reservation_bytes']>b['base']:raise ValueError('Kepler live state fragment alias')
    keys=[]
    for row in directory['rows']:
        if 'index_keys.L' not in row['version']:continue
        consumers=[]
        for op in native['instructions']:
            for tid,providers in op['provider_bindings'].items():
                for field,binding in providers.items():
                    if binding.get('version')!=row['version']:continue
                    spec=native['templates'][tid]['providers'][field]
                    consumers.append({'pc':op['pc'],'template':tid,'field':field,'shape':spec['shape'],
                        'dtype':spec['dtype'],'requested_bytes':max(1,math.prod(spec['shape']))*{'F32':4,'U32':4,'I64':8}[spec['dtype']],
                        'view_contract':binding['native_address_view'],
                        'status':'UNKNOWN_RETAINED_HISTORY_APPEND_OR_CODE_SCALE_VIEW_REQUIRED'})
        keys.append({'produced_fragment':row,'source_consumer_views':consumers,
            'produced_fragment_address_bound':True,'produced_fragment_visible_receipt':None,
            'complete_index_history_home_bound':False})
    return {'schema':'H4_DS_SOURCE_RESOLVED_KEPLER_STATE_HOME_JOIN_V1',
        'source_native_sha256':native_sha256,'state_fragment_homes':len(directory['rows']),
        'missing_write_versions_bound':len({(r['PC'],r['version']) for r in directory['rows']}),
        'extent':directory['extent'],'index_key_bindings':keys,
        'full_history_substitution_admitted':False,'hardware_full_native_claim':False,
        'status':'PASS_EXACT_PRODUCED_FRAGMENT_HOMES_HISTORY_VIEWS_UNKNOWN'}


def reconcile_v1_ordered_phases(program, template, record, api):
    """Replace exactly one native term and reconcile serialized RF once.

    An explicit source-scoped RF ledger is mandatory; absent is not zero.
    C0 and provider/RMW phases are retained byte-data identical. This is an
    analytical reservation, not evidence that H1 implements a V1 owner lock.
    """
    specs=native_value_specs(program,template);ref=record['native_instruction_ref']
    role,value,_,offset,payload=resolve_ds_movement_reference(program,template,ref,specs)
    if role[1]!='dst':raise ValueError('V1 destination source reference required')
    node=program['templates'][template]['code'][role[0]];elements=payload//specs[value]['width']
    input_bits=[specs[s]['width']*8 for s in node['src']]
    cost=api.command_cost(node['op'],input_bits,specs[value]['width']*8,elements=elements)
    identity=record['owner']
    if (set(identity)!={'PC','rank','SM','tag','generation'} or type(identity['PC'])!=int or identity['PC']<0 or
        any(type(identity[k])!=int or not 0<=identity[k]<limit for k,limit in
            [('rank',96),('SM',32),('tag',1<<64),('generation',1<<64)])):
        raise ValueError('V1 finite owner identity required')
    ledger=record.get('RF_ledger')
    if ledger is None:raise ValueError('UNKNOWN source-scoped existing RF ledger required')
    phases=record['baseline_phases'];native=[p for p in phases if p['kind']=='native']
    if len(native)!=1 or native[0]['opcode']!=node['op']:raise ValueError('V1 replaces exactly one matching native phase')
    if record.get('native_replacement_applied'):raise ValueError('V1 native replacement already applied')
    if native[0]['ticks']!=ledger['native_ticks_per_command']:raise ValueError('V1 native baseline ledger mismatch')
    for phase in phases:positive(phase['ticks'],'retained phase ticks')
    reads=sum(p.get('transactions',0) for p in phases if p['kind']=='RF_read_pair')
    writes=sum(p.get('transactions',0) for p in phases if p['kind']=='RF_write_vector_ACK')
    if (reads,writes)!=(ledger['RF_read_pair_transactions'],ledger['RF_write_vectors']):
        raise ValueError('V1 RF ledger does not resolve baseline phases')
    if ledger['I64_RMW_already_charged'] and not any(p['kind']=='provider_RMW' for p in phases):
        raise ValueError('V1 claimed existing I64 RMW has no baseline phase')
    kinds=[p['kind'] for p in phases];ni=kinds.index('native')
    if any(p['kind']=='RF_read_pair' for p in phases[ni+1:]) or any(p['kind']=='RF_write_vector_ACK' for p in phases[:ni]):
        raise ValueError('V1 serialized operand/ACK phase order')
    if not any(p['kind']=='C0_accept' for p in phases[:ni]) or not any(p['kind']=='C0_reverse_retire' for p in phases[ni+1:]):
        raise ValueError('V1 retains C0 owner accept/reverse phases')
    delta=api.reconcile_cost(cost,ledger);new=[]
    for phase in phases:
        if phase['kind']!='native':new.append(dict(phase));continue
        for i in range(delta['additional_RF_read_pairs']):
            new.append({'kind':'RF_read_pair','transactions':1,'ticks':cost['components']['RF_read']//cost['RF_read_pair_transactions'],'owner':identity,
                'provisional':True,'source':'V1 read_accept/capture/return; single owner credit'})
        new.append(dict(phase,ticks=delta['native_only_replacement_ticks'],replacement='V1_native_only_once'))
        for i in range(delta['additional_RF_write_vectors']):
            new.append({'kind':'RF_write_vector_ACK','transactions':1,'ticks':cost['components']['RF_write_visible']//cost['RF_write_vectors'],'owner':identity,
                'provisional':True,'source':'V1 write_accept/both_mirror_ACK; release after ACK'})
    if [p for p in new if p['kind'].startswith('C0_')]!=[p for p in phases if p['kind'].startswith('C0_')]:
        raise ValueError('V1 changed retained C0 charge')
    return {'schema':'H4_V1_ORDERED_PHASE_NATIVE_REPLACEMENT_V1','owner':identity,
        'native_instruction_ref':ref,'native_replacement_applied':True,'ordered_phases':new,
        'software_ticks_before':sum(p['ticks'] for p in phases),'software_ticks_after':sum(p['ticks'] for p in new),
        'reconciliation':delta,'serialized_RF_cost':cost,'hardware_admitted':False,
        'C0_atomic_owner_lock_in_actual_H1':'UNKNOWN','clock_or_ns_conversion':None}


def compose_v1_native_component_successor(ds, qwen_fixture, qwen, model):
    """All-PC analytical native-only replacement; unknown RF debit stays unknown.

    Retains DS's conservative scalar service unit and Qwen's exported command
    unit. No conversion of scalar service bounds to achieved SIMD throughput.
    Whole serialized V1 cost must never be added on top of RF/C0/provider terms.
    """
    if ds.get('V1_native_replacement_applied') or qwen_fixture.get('V1_native_replacement_applied'):
        raise ValueError('V1 native component already replaced')
    profiles=model['typed_cost_bounds']
    def demand(counts, baseline):
        selected={op:n for op,n in counts.items() if op in profiles};removed=added=reads=writes=0
        for op,n in selected.items():
            if type(n)!=int or n<0:raise ValueError('V1 source command count')
            p=profiles[op]['upper'];positive(p['native_only_replacement_ticks'],'V1 native replacement')
            removed+=n*baseline;added+=n*p['native_only_replacement_ticks']
            reads+=n*p['RF_read_pair_transactions'];writes+=n*p['RF_write_vectors']
        return {'native_old_ticks':removed,'native_new_ticks':added,'native_delta_ticks':added-removed,
            'RF_required_read_pairs_upper':reads,'RF_required_write_vectors_upper':writes,
            'RF_additional_cost_after_existing_ledger':None,'C0_additional_ticks':0,'I64_RMW_additional_ticks':0}
    tick=0;rows=[];base=ds['retained_baseline_provisional_costs']['primitive_scalar'];positive(base,'DS native baseline')
    for pc in ds['PC_intervals']:
        groups=defaultdict(list);records={};durations=[]
        for rank in pc['ranks']:
            d=demand(rank['native_scalar_command_upper_by_opcode'],base)
            if d['native_old_ticks']>rank['baseline_provider_and_native_ticks_charged_once']:raise ValueError('DS native removal exceeds charged baseline')
            d.update(C0_retained_ticks=rank['C0_ticks'],shared_retained_ticks=rank['shared_known_ticks'],
                provider_nonV1_retained_ticks=rank['baseline_provider_and_native_ticks_charged_once']-d['native_old_ticks'])
            duration=rank['end']-rank['start']+d['native_delta_ticks']
            if duration<0:raise ValueError('negative DS successor interval')
            key=json.dumps(d,sort_keys=True,separators=(',',':'));groups[key].append(rank['rank']);records[key]=d;durations.append(duration)
        end=tick+max(durations)+pc['additional_atomic_admission_ticks']
        rows.append({'pc':pc['pc'],'family':pc['family'],'dependencies':pc['dependencies'],'start':tick,'end':end,
            'rank_groups':[dict(records[k],ranks=ranks) for k,ranks in groups.items()],
            'atomic_collective_participants':pc['atomic_collective_participants'],
            'actual_RF_reconciliation_complete':False});tick=end
    qrows=[];shift=0
    for old in qwen_fixture['ordered_PC_intervals']:
        d=demand(old['native_commands'],32)
        if sum(old['native_commands'].values())!=old['cost_units']['native_batch']:raise ValueError('Qwen fixture native source count mismatch')
        row=dict(pc=old['pc'],position=old['position'],family=old['opcode'],start=old['start']+shift,
            end=old['end']+shift+d['native_delta_ticks'],C0_retained_ticks=old['C0_service_ticks'],
            provider_retained_ticks=old['provider_service_ticks'],**d)
        qrows.append(row);shift+=d['native_delta_ticks']
    qfull=[]
    for op in qwen['operations']:
        counts=op['calendar_export']['physical_primitives']['native_primitive_commands']
        qfull.append({'pc':op['pc'],'family':op['opcode'],'dependencies':op['dependencies'],
            'source_native_command_counts':counts,**demand(counts,32),
            'C0_existing_charge_unchanged':True,'complete_provider_RF_calendar':None})
    return {'schema':'H4_V1_BOTH_PROGRAM_NATIVE_COMPONENT_SUCCESSOR_V1','V1_native_replacement_applied':True,
        'DeepSeek':{'PCs':len(rows),'families':len({r['family'] for r in rows}),'PC_intervals':rows,
            'known_native_only_successor_software_ticks':tick,'baseline_known_service_software_ticks':ds['known_service_software_ticks'],
            'count_scope':'retained scalar-command conservative upper per rank; no128lane speedup claimed',
            'unknown_shared_template_calls':ds['unknown_shared_template_calls']},
        'Qwen_fixture':{'PC_intervals':qrows,'baseline_software_ticks':qwen_fixture['software_ticks'],
            'native_only_successor_software_ticks':qwen_fixture['software_ticks']+shift,'scope':'two reduced36layer CPU fixtures'},
        'Qwen_full_program':{'PCs':len(qfull),'families':len({r['family'] for r in qfull}),'PC_native_component_demands':qfull,
            'complete_service_software_ticks':None},
        'RF_join':'UNKNOWN until source-scoped existing pair/read/write/ACK ledger; no zero debit assumed',
        'C0_and_provider_costs_retained_once':True,'additional_RMW_codec_or_r22_cost':0,
        'area':model['area'],'routing':model['routing'],'resource_contract':model['resource_contract'],
        'measured_opcode_costs':None,'complete_iteration_service_software_ticks':None,
        'hardware_admitted':False,'clock_or_ns_conversion':None}


def compile_ds_r34_group_source(original, source, witness):
    """Execute only the pinned metadata lowerer; resolve every corrected code node."""
    import copy
    functions=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ('canonical','lower_template','lower_native')]
    if len(functions)!=3:raise ValueError('exact r34 metadata lowerer closure required')
    ns=dict(copy=copy,math=math,Counter=Counter,json=json,hashlib=hashlib)
    exec(compile(ast.Module(body=functions,type_ignores=[]),'source-pinned-r34-group-lowerer','exec'),ns)
    digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    rows=[];templates={};seen=set()
    for row in witness:
        pc=row['PC']
        if pc in seen:raise ValueError('duplicate r34 PC')
        seen.add(pc);op=original['instructions'][pc];old=row['old_template']
        if op['family']!='all_reduce' or (op['source_op']['groups'],op['source_op']['per_group'],op['source_op']['elems'])!=(8,8,8192):
            raise ValueError('actual source eight independent groups required')
        if any(b.get('template')!=old for b in op['rank_bindings']):raise ValueError('old actual rank/template binding required')
        before=original['templates'][old];after=ns['lower_template'](before)
        if digest(after)!=row['new_template']:raise ValueError('source-derived r34 template hash mismatch')
        # Resolve shape changes against every original instruction and preserve
        # operation, operand, attributes and rounding/tree order byte-data.
        for a,b in zip(before['code'],after['code']):
            if any(a[k]!=b[k] for k in a if k!='shape'):raise ValueError('r34 changed arithmetic or operand order')
        def counts(program):
            scalars=Counter();batches=Counter()
            for n in program['code']:
                size=max(1,math.prod(n['shape']));scalars[n['op']]+=size;batches[n['op']]+=ceil(size,128)
            return dict(scalars),dict(batches)
        old_count,old_batch=counts(before);new_count,new_batch=counts(after)
        templates[row['new_template']]=after
        owned,_=ns['lower_native']({'templates':{old:before},'instructions':[op]})
        corrected_op=owned['instructions'][0]
        if any(b.get('template')!=row['new_template'] for b in corrected_op['rank_bindings']):
            raise ValueError('source-derived r34 rank/template remap mismatch')
        rows.append(dict(pc=pc,dependencies=op['dependencies'],old_template=old,new_template=row['new_template'],
            ranks=[b['rank'] for b in op['rank_bindings'] if not b.get('empty_owned_extent')],
            original_provider_bindings=op['provider_bindings'],provider_bindings=corrected_op['provider_bindings'],
            actual_rank_template_bindings=corrected_op['rank_bindings'],reads=op['reads'],writes=op['writes'],
            old_native_scalars=old_count,new_native_scalars=new_count,old_batches128=old_batch,new_batches128=new_batch,
            input_words=65536,output_words=8192,materialized_workspace_bytes=after['resources']['materialized_tensor_workspace_bytes'],
            hardware_addressed_shared_journal=None))
    expected={o['pc'] for o in original['instructions'] if o['family']=='all_reduce'}
    if seen!=expected:raise ValueError('all actual all-reduce PCs required')
    return dict(schema='H4_R34_RESOLVED_EIGHT_GROUP_SOURCE_INVENTORY_V1',PCs=len(original['instructions']),
        corrected_PC_bindings=rows,native_templates=templates,source_provider_code_sha256=hashlib.sha256(source).hexdigest(),
        group_order='contributor j, group g, word; source rank=8*g+j',tree_order='((0+1)+(2+3))+((4+5)+(6+7)) separately per group',
        numerical_or_provider_execution=False,hardware_admitted=False)


def reprice_ds_r34_groups(previous, inventory, v1_model, scalar_ticks, c0_ticks):
    """Replace source-dependent native and C0 obligations once; no RF/provider add."""
    import copy
    positive(scalar_ticks,'retained primitive scalar ticks');positive(c0_ticks,'retained C0 command ticks')
    if previous.get('r34_reprice_applied'):raise ValueError('r34 replacement already applied')
    if not previous.get('r33_reprice_applied'):raise ValueError('current once-only r33 baseline required')
    changes={r['pc']:r for r in inventory['corrected_PC_bindings']};out=copy.deepcopy(previous)
    profiles=v1_model['typed_cost_bounds'];cursor=0;added=0;calls=0;proof=[]
    for row in out['DeepSeek']['PC_intervals']:
        duration=row['end']-row['start'];delta=0
        if row['pc'] in changes:
            source=changes[row['pc']]
            if row['family']!='all_reduce' or row['dependencies']!=source['dependencies']:raise ValueError('r34 source PC dependency mismatch')
            ranks=[r for group in row['rank_groups'] for r in group['ranks']]
            if len(set(ranks))!=len(ranks) or set(ranks)!=set(source['ranks']):raise ValueError('r34 actual rank coverage mismatch')
            def price(counts):
                return sum(n*(profiles[op]['upper']['native_only_replacement_ticks'] if op in profiles else scalar_ticks) for op,n in counts.items())
            native_delta=price(source['new_native_scalars'])-price(source['old_native_scalars'])
            c0_old=sum(source['old_batches128'].values())*c0_ticks
            c0_new=sum(source['new_batches128'].values())*c0_ticks
            delta=native_delta+c0_new-c0_old
            for group in row['rank_groups']:
                if group['C0_retained_ticks']!=c0_old:raise ValueError('existing C0 source ledger mismatch')
                if profiles:
                    old_v1=sum(n*profiles[op]['upper']['native_only_replacement_ticks'] for op,n in source['old_native_scalars'].items() if op in profiles)
                    old_removed=sum(n*scalar_ticks for op,n in source['old_native_scalars'].items() if op in profiles)
                    if (group.get('native_new_ticks'),group.get('native_old_ticks'))!=(old_v1,old_removed):
                        raise ValueError('existing V1 source profile ledger mismatch')
                group['r34_native_only_delta_ticks']=native_delta
                group['r34_C0_once_replacement_delta_ticks']=c0_new-c0_old
                group['r34_actual_shared_movement']=None
                group['r34_additional_RF_debit']=None
                group['r34_additional_provider_transfer_cost']=None
            proof.append(dict(pc=row['pc'],ranks=len(ranks),native_only_delta_ticks=native_delta,
                C0_old_ticks=c0_old,C0_new_ticks=c0_new,critical_rank_delta_ticks=delta,
                input_byte_increase_per_call=(65536-8192)*4,output_byte_increase_per_call=(8192-1024)*4,
                source_input_fragment_ranks=list(range(64)),actual_shared64_transactions=None,
                prior_single_group_shared_reservation_retained_as_partial=True))
            calls+=len(ranks)
        row['start']=cursor;row['end']=cursor+duration+delta
        if row['end']<=row['start']:raise ValueError('nonpositive r34 successor interval')
        cursor=row['end'];added+=delta
    if cursor!=previous['DeepSeek']['known_native_only_successor_software_ticks']+added:raise ValueError('r34 interval sum mismatch')
    if len(proof)!=len(changes):raise ValueError('r34 complete PC ledger coverage required')
    out['r34_reprice_applied']=True;out['DeepSeek']['known_native_only_successor_software_ticks']=cursor
    out['DeepSeek']['unknown_shared_template_calls']+=calls
    return out,dict(schema='H4_R34_ONCE_NATIVE_C0_GROUP_REPRICE_V1',PCs=out['DeepSeek']['PCs'],
        changed_PCs=len(proof),changed_rank_calls=calls,critical_rank_software_tick_delta=added,
        known_partial_software_ticks=cursor,shared_unknown_calls=out['DeepSeek']['unknown_shared_template_calls'],
        records=proof,RF_mirror_cost_recharged=False,I64_RMW_recharged=False,provider_cost_recharged=False,
        C0_replacement_count=1,native_replacement_count=1,full_service_software_ticks=None,
        physical_endpoint_latencies=None,hardware_admitted=False,clock_or_ns_conversion=None)


def compose_ds_r33_once_reprice(adapter, catalog, overlay, provider, parent, parent_catalog, previous, scalar_ticks):
    """Reprice only resolved LOAD scalar obligations; retain every other ledger.

    This is the known analytical subledger, not a complete physical calendar.
    In particular removing source LOAD issue obligations cannot remove the old
    conservative provider/shared reservation or supply absent runtime receipts.
    """
    import copy
    positive(scalar_ticks, 'retained scalar LOAD cost')
    if previous.get('r33_reprice_applied'):raise ValueError('r33 cost already replaced once')
    digest=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    ctx=adapter['source_context']
    if (parent.get('schema')!='H4_C0_R33_SOURCE_ADAPTER_V1' or parent.get('hardware_qualified') or
        parent['inputs']['native']!=ctx['native_sha256'] or
        parent['source_catalog_sha256']!=digest(parent_catalog) or
        parent_catalog['source_program_sha256']!=ctx['native_sha256'] or
        provider['source_context']!=ctx):raise ValueError('current parent source/catalog identity required')
    changes={row['pc']:row for row in adapter['changed_window_PCs']}
    delta={k:v for k,v in adapter['primitive_scalar_delta'].items() if v}
    if parent['actual_scalar_count_delta']!=delta:raise ValueError('parent scalar source delta mismatch')
    if len(parent_catalog['PC_bindings'])!=len(catalog['PC_bindings']):raise ValueError('parent all-PC coverage mismatch')
    for current,other in zip(catalog['PC_bindings'],parent_catalog['PC_bindings']):
        for key in ('pc','family','dependencies','bindings','native_scalars','native_batches128'):
            if current[key]!=other[key]:raise ValueError('current parent all-PC source count/binding mismatch')
    if previous['DeepSeek']['PCs']!=len(catalog['PC_bindings']):raise ValueError('baseline all-PC coverage mismatch')
    out=copy.deepcopy(previous);cursor=0;total_delta=0;witnesses=[]
    for row,source in zip(out['DeepSeek']['PC_intervals'],catalog['PC_bindings']):
        if (row['pc'],row['family'],row['dependencies'])!=(source['pc'],source['family'],source['dependencies']):
            raise ValueError('baseline PC/dependency mismatch')
        duration=row['end']-row['start'];correction=0
        if row['pc'] in changes:
            change=changes[row['pc']];calls=source['bindings'];ranks=[c['rank'] for c in calls]
            if len(set(ranks))!=len(ranks) or change['source_calls']!=len(ranks):raise ValueError('one window call per rank required')
            if change['LOAD_scalar_delta']!=-512*len(ranks):raise ValueError('actual per-rank LOAD source delta required')
            grouped=[r for g in row['rank_groups'] for r in g['ranks']]
            if len(grouped)!=len(set(grouped)) or set(grouped)!=set(ranks):raise ValueError('exact baseline rank coverage required')
            for group in row['rank_groups']:
                if group['provider_nonV1_retained_ticks']<512*scalar_ticks:raise ValueError('source LOAD subtraction exceeds retained nonV1 ledger')
                # Preserve original provider/RF/V1/C0 fields for independent audit.
                group['source_LOAD_native_scalar_correction_ticks']=-512*scalar_ticks
            correction=-512*scalar_ticks
            for call in calls:
                tid=call['template'];code=overlay['native_templates'][tid]['code']
                loads=[(i,n) for i,n in enumerate(code) if n['op']=='LOAD' and n['attrs'].get('name')=='window']
                if len(loads)!=1 or loads[0][1]['shape']!=[127,512]:raise ValueError('resolved127-row source LOAD required')
                leaf=parent_catalog['templates'][tid]['calls'][0]['leaf']
                if parent_catalog['leaves'][leaf]['code_sha256']!=digest(code):raise ValueError('parent native code digest mismatch')
            witnesses.append(dict(pc=row['pc'],rank_calls=len(ranks),native_LOAD_scalar_delta=change['LOAD_scalar_delta'],
                critical_rank_software_tick_delta=correction,all_rank_scalar_obligation_tick_delta=correction*len(ranks)))
        row['start']=cursor;row['end']=cursor+duration+correction
        if row['end']<=row['start']:raise ValueError('nonpositive successor interval')
        cursor=row['end'];total_delta+=correction
    baseline=previous['DeepSeek']['known_native_only_successor_software_ticks']
    if cursor!=baseline+total_delta:raise ValueError('once reprice interval reconciliation failed')
    out['r33_reprice_applied']=True
    out['DeepSeek']['known_native_only_successor_software_ticks']=cursor
    out['DeepSeek']['source_program_sha256']=ctx['native_sha256']
    out['current_parent_catalog_sha256']=digest(parent_catalog)
    out['r33_reprice_scope']='Only32-tick provisional native LOAD scalar obligations; conservative provider/shared reservations retained'
    receipt=dict(schema='H4_R33_DEWEY_ONCE_REPRICE_V1',native_sha256=ctx['native_sha256'],
        dispatch_sha256=parent['inputs']['dispatch'],catalog_sha256=digest(parent_catalog),
        actual_scalar_count_delta=delta,RF_highword_RMW_recharged=False,C0_control_recharged=False,reprice_count=1,
        baseline_known_subledger_software_ticks=baseline,current_known_subledger_software_ticks=cursor,
        critical_path_software_tick_delta=total_delta,provisional_LOAD_scalar_ticks=scalar_ticks,
        actual_shared_movement_repriced=False,provider_reservations_retained=True,
        complete_service_software_ticks=None,hardware_qualified=False,clock_or_ns_conversion=None,
        changed_PC_witnesses=witnesses)
    return out,receipt


def reserve_ds_r33_initial_loads(adapter, catalog, overlay, provider, costs):
    """Construct source-resolved finite initial-window LOAD boundary reservations.

    Per-fragment phases are ordered and positive, compressed without overlap.
    They reserve a compiler mapping, not installed RF connections or execution.
    Arithmetic and output commit are deliberately outside this boundary ledger.
    """
    names={'owner_accept','HBM32_read_return','scratch64_write_ACK','scratch64_read_return',
        'RF512_both_mirror_ACK','consumer_capture','validated_reverse'}
    if set(costs)!=names:raise ValueError('explicit complete boundary phase costs required')
    for name,value in costs.items():positive(value,name)
    ctx=adapter['source_context']
    if provider['source_context']!=ctx:raise ValueError('current window provider source context required')
    phase_units=[('owner_accept',1),('HBM32_read_return',16),('scratch64_write_ACK',8),
        ('scratch64_read_return',8),('RF512_both_mirror_ACK',1),('consumer_capture',1),('validated_reverse',1)]
    phases=[];stride=0
    for name,units in phase_units:
        phases.append(dict(phase=name,units=units,start_offset=stride,end_offset=stride+units*costs[name],
            provisional_ticks_per_unit=costs[name]))
        stride+=units*costs[name]
    # One global fragment reservation; all32 SM resources are conservatively
    # held by the enclosing batch. Source block256%32 maps each actual fragment.
    capacities={'global.provider_fragment':1}
    for rank in sorted({b['rank'] for b in provider['bindings']}):
        capacities[f'r{rank}.provider_credit']=1
        for sm in range(32):
            for name in ('scratch_fragment512','RF_mirror0','RF_mirror1'):
                capacities[f'r{rank}.s{sm}.{name}']=1
    cal=Calendar(capacities);last=[];bound=[];totals=Counter();seen=set()
    pc_index={r['pc']:r for r in catalog['PC_bindings']}
    resolved_templates=set()
    for item in sorted(provider['bindings'],key=lambda b:(b['pc'],b['rank'])):
        pc,rank,tid=item['pc'],item['rank'],item['current_template'];key=(pc,rank)
        if key in seen:raise ValueError('duplicate window call')
        seen.add(key);source=pc_index[pc]
        matches=[b for b in source['bindings'] if b['rank']==rank and b['template']==tid]
        if len(matches)!=1:raise ValueError('actual current parent rank/template binding required')
        home=item['input'];size=127*512*4;base=home['base']
        actual_homes=[h for row in adapter['changed_window_PCs'] if row['pc']==pc for h in row['window_homes'] if h['rank']==rank]
        if actual_homes!=[home]:raise ValueError('immutable initial provider home mismatch')
        if home['bytes']!=size or base%512 or home['rank']!=rank or home['generation']!=1:
            raise ValueError('exact aligned127-row initial home/generation required')
        if base<33554432 or base+size>67108864:raise ValueError('finite32MiB initial window extent exhausted')
        code=overlay['native_templates'][tid]['code']
        found=[(i,n) for i,n in enumerate(code) if n['op']=='LOAD' and n['attrs'].get('name')=='window']
        if len(found)!=1:raise ValueError('actual source LOAD missing')
        i,node=found[0]
        ref=dict(source_context=ctx,pc=pc,rank=rank,parent_template=tid,call_index=0,invocation_index=0,
            template=tid,code_index=i,opcode='LOAD',attrs=node['attrs'],result_shape=node['shape'],
            operand='dst',value=node['dst'],logical_byte_offset=0,payload_bytes=size)
        # Code/source digest and scalar span are invariant across calls of this
        # immutable template. Resolve once; check every PC/rank/home above.
        if tid not in resolved_templates:
            resolve_ds_r33_window_reference(adapter,catalog,overlay,ref)
            resolved_templates.add(tid)
        resources={'global.provider_fragment':1,f'r{rank}.provider_credit':1}
        for sm in range(32):
            for name in ('scratch_fragment512','RF_mirror0','RF_mirror1'):resources[f'r{rank}.s{sm}.{name}']=1
        repeats=size//512
        event=cal.add(f'PC{pc}.r{rank}.initial_window_LOAD',last,stride*repeats,resources,
            repeats=repeats,stride=stride,source_ref=ref,home_ref=home['home_ref'],version=home['version'],
            source_byte_base=base,payload_bytes=512,fragment_byte_stride=512,
            SM_formula='floor(fragment_index/2)%32; source block256%32; conservative compiler mapping',
            scratch_reserved_bytes_per_SM=512,RF_reserved_vectors_per_SM=1,RF_write_mirror_mask=3,
            phases_ref='initial_window_LOAD512',lease_release_phase='validated_reverse')
        last=[event];bound.append(dict(pc=pc,rank=rank,event=event,actual_provider_receipt=None,
            output_generation_lease=item['output_generation_or_lease'],output_commit_calendar=None))
        for phase,units in phase_units:totals[phase]+=units*repeats
    if len(seen)!=provider['rank_window_pairs']:raise ValueError('complete window call coverage required')
    proof=verify_calendar(cal.events,capacities)
    return dict(schema='H4_R33_INITIAL_LOAD_FINITE_BOUNDARY_RESERVATION_V1',
        status='PROVISIONAL_SOURCE_BOUND_INPUT_RESERVATION_ONLY',source_context=ctx,
        phase_templates={'initial_window_LOAD512':phases},explicit_provisional_costs=costs,
        events=cal.events,capacities=capacities,proof=proof,bindings=bound,phase_unit_totals=dict(totals),
        boundary_serial_reservation_software_ticks=max(cal.ends.values(),default=0),
        shared_transaction_bytes=64,RF_logical_vector_bytes=512,RF_physical_mirrors=2,
        scratch_reuse_after_matching_reverse=True,all_PC_runtime_calendar=None,
        added_to_existing_cost_ledger=False,installed_physical_RF_map=None,
        actual_payload_or_provider_execution=False,actual_output_commit_or_visibility=None,
        full_service_software_ticks=None,hardware_admitted=False,clock_or_ns_conversion=None)


def derive_ds_r33_source_pair(native, dispatch, contract_source, prepare_source, position):
    """Execute only the producer's metadata lowering and dispatch count adapter."""
    import copy
    ns={'copy':copy,'hashlib':hashlib,'json':json}
    nodes=[n for n in ast.parse(contract_source).body if isinstance(n,ast.FunctionDef)]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned_r33_window_contract','exec'),ns)
    lowered,witness=ns['lower_full_native'](native,position,'pretrimmed127')
    raw=gzip.compress(ns['canonical'](lowered),mtime=0)
    main=next(n for n in ast.parse(prepare_source).body if isinstance(n,ast.FunctionDef) and n.name=='main')
    start=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='joined' for t in n.targets))
    selected=main.body[start:start+3]
    if not isinstance(selected[-1],ast.For):raise ValueError('r33 producer dispatch adapter source changed')
    env={'copy':copy,'Counter':Counter,'math':math,'hashlib':hashlib,
        'dispatch':dispatch,'lowered':lowered,'witness':witness,'raw':raw}
    exec(compile(ast.Module(body=selected,type_ignores=[]),'pinned_r33_dispatch_adapter','exec'),env)
    return lowered,env['joined'],witness,raw,gzip.compress(ns['canonical'](env['joined']),mtime=0)


def adapt_ds_r33_calendar(original, old_dispatch, current, current_dispatch, witness, catalog, initial_homes):
    """Current source/count identities, explicitly separate from old cost fit.

    No 128-row physical reservation is removed and no new movement is certified.
    Exported template overlay makes new leaf references locally resolvable.
    """
    import copy
    canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode()
    if catalog['source_program_sha256']!=old_dispatch['source_program_sha256']:
        raise ValueError('r33 baseline catalog/native source mismatch')
    digest=hashlib.sha256(gzip.compress(canonical(current),mtime=0)).hexdigest()
    if current_dispatch['source_program_sha256']!=digest:raise ValueError('r33 current dispatch/native source mismatch')
    if len(original['instructions'])!=len(current['instructions']) or len(current_dispatch['PC_dispatch'])!=len(current['instructions']):
        raise ValueError('r33 complete PC source coverage')
    remap={};by_pc=defaultdict(list)
    for row in witness:remap[row['old_template']]=row['new_template'];by_pc[row['PC']].append(row)
    expected_pcs={o['pc'] for o in original['instructions'] if o['family']=='q_norm_kv_row'}
    if set(by_pc)!=expected_pcs:raise ValueError('r33 window witness PC coverage')
    updated=copy.deepcopy(catalog);overlay={'native_templates':{},'instruction_patches':{},'dispatch_templates':{},'dispatch_PC_patches':{}}
    changed=[];total_delta=Counter();batch_delta=Counter();old_new_leaves={}
    for old,new in remap.items():
        before=original['templates'][old];after=current['templates'][new]
        if hashlib.sha256(canonical(after)).hexdigest()!=new:raise ValueError('r33 new template source identity')
        normalized=copy.deepcopy(after)
        loads=[i for i,n in enumerate(before['code']) if n['op']=='LOAD' and n['attrs'].get('name')=='window']
        if len(loads)!=1:raise ValueError('r33 actual window LOAD source')
        index=loads[0];load=before['code'][index]
        slices=[i for i,n in enumerate(before['code']) if n['op']=='SLICE' and n['src']==[load['dst']]]
        if len(slices)!=1 or before['code'][slices[0]]['attrs']['start']!=1:raise ValueError('r33 actual window drop source')
        sl=slices[0]
        if after['code'][index]['shape']!=[127,512] or after['code'][sl]['attrs']['start']!=0:
            raise ValueError('r33 requires explicit127 LOAD/drop0 source')
        normalized['code'][index]['shape']=load['shape']
        normalized['code'][sl]['attrs']['start']=1
        normalized['providers']['window']['shape']=before['providers']['window']['shape']
        normalized['shape_parameters']['window']=before['shape_parameters']['window']
        if normalized!=before:raise ValueError('r33 changes arithmetic or unrelated native semantics')
        counts=Counter();batches=Counter()
        for n in after['code']:
            elements=max(1,math.prod(n['shape']));counts[n['op']]+=elements;batches[n['op']]+=ceil(elements,128)
        delta={k:counts[k]-catalog['templates'][old]['native_scalars'].get(k,0) for k in counts}
        if {k:v for k,v in delta.items() if v}!= {'LOAD':-512}:raise ValueError('r33 source movement count delta')
        if current_dispatch['templates'][new]['executed_primitive_scalar_projection']!=dict(counts):
            raise ValueError('r33 dispatch template counts do not resolve source')
        leaf=hashlib.sha256(canonical(after)).hexdigest();oldleaf=catalog['templates'][old]['calls'][0]['leaf'];old_new_leaves[oldleaf]=leaf
        updated['leaves'][leaf]={'program_ref':'r33_source_overlay.json.gz#/native_templates/'+new,
            'code_sha256':hashlib.sha256(canonical(after['code'])).hexdigest(),'native_scalars':dict(counts),
            'native_batches128':dict(batches),'source_builder':'retained_r33_window_template','source_builder_args':[new],
            'hardware_command_binding':False}
        t=copy.deepcopy(catalog['templates'][old]);t['calls'][0]['leaf']=leaf
        t['retained_128row_capacity_plan']=t.pop('source_loop_plan')
        t.update(native_scalars=dict(counts),native_batches128=dict(batches),
            source_loop_plan={'primitive_scalars':sum(counts.values()),'scalar_evaluations_by_opcode':dict(counts),
                '128lane_batches':sum(batches.values()),'matching_physical_service_cost':None,'fits':None},
            actual_shared_movement_source_context=None)
        updated['templates'][new]=t
        overlay['native_templates'][new]=after;overlay['dispatch_templates'][new]=current_dispatch['templates'][new]
    for pc,(before,after,oldrow,row) in enumerate(zip(original['instructions'],current['instructions'],old_dispatch['PC_dispatch'],current_dispatch['PC_dispatch'])):
        if before['pc']!=pc or after['pc']!=pc or row['pc']!=pc:raise ValueError('r33 source PC order')
        if pc not in by_pc:
            if before!=after or oldrow!=row:raise ValueError('r33 nonwindow PC changed')
            continue
        if before['family']!=after['family'] or before['reads']!=after['reads'] or before['writes']!=after['writes'] or before['dependencies']!=after['dependencies']:
            raise ValueError('r33 version/dependency identity changed')
        expected_op=copy.deepcopy(before)
        for joined in by_pc[pc]:
            old,new=joined['old_template'],joined['new_template']
            bindings=expected_op['provider_bindings'].pop(old)
            window=after['provider_bindings'][new]['window'];position=window.get('window_position')
            if (bindings['window']['version']!=joined['input_version'] or window['version']!=joined['input_version'] or
                type(position)!=int or position<127):raise ValueError('r33 window source version/position')
            if any(b.get('position',position)!=position for b in bindings.values()):raise ValueError('r33 source position changed')
            bindings['window'].update(view='explicit pretrimmed127 old window, [127, 512]',
                window_representation='pretrimmed127',window_position=position)
            expected_op['provider_bindings'][new]=bindings
            for binding in expected_op['rank_bindings']:
                if binding.get('template')==old:binding['template']=new
        if after!=expected_op:raise ValueError('r33 unrelated provider/rank instruction mutation')
        expected=[dict(c,template=remap.get(c['template'],c['template'])) for c in oldrow['calls']]
        if row['calls']!=expected or row['rank_bindings']!=after['rank_bindings'] or row['provider_bindings']!=after['provider_bindings']:
            raise ValueError('r33 current PC mixes old template/provider calls')
        entry=updated['PC_bindings'][pc];scalars=Counter();batch=Counter()
        for call in row['calls']:
            t=updated['templates'][call['template']];scalars.update(t['native_scalars']);batch.update(t['native_batches128'])
        if dict(scalars)!=row['projected_executed_primitive_scalars']:raise ValueError('r33 perPC dispatch source counts')
        for k in set(scalars)|set(entry['native_scalars']):total_delta[k]+=scalars[k]-entry['native_scalars'].get(k,0)
        for k in set(batch)|set(entry['native_batches128']):batch_delta[k]+=batch[k]-entry['native_batches128'].get(k,0)
        entry.update(native_scalars=dict(scalars),native_batches128=dict(batch))
        for binding in entry['bindings']:binding['template']=remap.get(binding['template'],binding['template'])
        homes=[(i,h) for i,h in enumerate(initial_homes['rows']) if h['PC_first_consumer']==pc]
        if len(homes)!=len(row['calls']) or {h['rank'] for _,h in homes}!={c['rank'] for c in row['calls']}:
            raise ValueError('r33 initial window homes/consumer ranks mismatch')
        versions={w['input_version'] for w in by_pc[pc]}
        if any(h['shape']!=[127,512] or h['bytes']!=127*2048 or h['generation']!=1 or h['version'] not in versions or not h['source_payload_required'] for _,h in homes):
            raise ValueError('r33 current concrete window home span/generation')
        changed.append({'pc':pc,'source_calls':len(row['calls']),'template_joins':by_pc[pc],
            'LOAD_scalar_delta':-512*len(row['calls']),'LOAD_batches128_delta':-4*len(row['calls']),
            'window_homes':[{'rank':h['rank'],'base':h['base'],'bytes':h['bytes'],'generation':h['generation'],
                'version':h['version'],'home_ref':'results/uarch/ds_hbm_window_retirement_r33_20261002/initial_window_homes.json.gz#/rows/'+str(i)} for i,h in homes],
            'physical_cost_source':'original128row reservation retained','matching_physical_movement_cost':None})
        overlay['instruction_patches'][str(pc)]=after;overlay['dispatch_PC_patches'][str(pc)]=row
    for k,v in total_delta.items():updated['native_scalars'][k]+=v
    for k,v in batch_delta.items():updated['native_batches128'][k]+=v
    updated.update(source_program_sha256=digest,source_dispatch_sha256=hashlib.sha256(canonical(current_dispatch)).hexdigest(),
        retained_cost_source_program_sha256=old_dispatch['source_program_sha256'],
        source_context_requires_explicit_adapter=True,actual_shared64_movements=None)
    context={'native_sha256':digest,'dispatch_content_sha256':updated['source_dispatch_sha256'],
        'catalog_content_sha256':hashlib.sha256(canonical(updated)).hexdigest()}
    return {'schema':'H4_DS_R33_SOURCE_COUNT_CALENDAR_ADAPTER_V1','source_context':context,'PCs':len(current['instructions']),
        'changed_window_PCs':changed,'primitive_scalar_delta':dict(total_delta),'native_batches128_delta':dict(batch_delta),
        'original128row_cost_reservations_retained':True,'physical_cost_replacement_applied':False,
        'matching_current_movement_bridge':None,'hardware_admitted':False},updated,overlay


def require_ds_calendar_source_context(adapter, native_sha256, dispatch_content_sha256, catalog_content_sha256):
    if adapter['source_context']!={'native_sha256':native_sha256,'dispatch_content_sha256':dispatch_content_sha256,
        'catalog_content_sha256':catalog_content_sha256}:raise ValueError('mixed native/dispatch/catalog source context')


def resolve_ds_r33_window_reference(adapter, catalog, overlay, ref):
    """Explicit importer ABI for current staged references, not original DPATH."""
    if ref.get('source_context')!=adapter['source_context']:raise ValueError('mixed r33 movement source context')
    digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require_ds_calendar_source_context(adapter,catalog['source_program_sha256'],catalog['source_dispatch_sha256'],digest(catalog))
    tid=ref.get('parent_template');pc=ref.get('pc');rank=ref.get('rank')
    if tid not in overlay['native_templates'] or type(pc)!=int or not 0<=pc<len(catalog['PC_bindings']):
        raise ValueError('r33 actual window template/PC reference required')
    if not any(b['rank']==rank and b['template']==tid for b in catalog['PC_bindings'][pc]['bindings']):
        raise ValueError('r33 movement rank/template not owned by source PC')
    calls=catalog['templates'][tid]['calls'];ci=ref.get('call_index');iteration=ref.get('invocation_index')
    if type(ci)!=int or not 0<=ci<len(calls) or type(iteration)!=int or not 0<=iteration<calls[ci]['repetitions']:
        raise ValueError('r33 staged leaf invocation reference')
    key=calls[ci]['leaf'];program=overlay['native_templates'][tid]
    if ref.get('template')!=key or digest(program)!=key or digest(program['code'])!=catalog['leaves'][key]['code_sha256']:
        raise ValueError('r33 retained template/leaf source identity')
    return resolve_ds_movement_reference({'templates':{key:program}},key,ref)


def bind_ds_r33_window_provider_homes(adapter, produced, initial):
    """Explicit old-output/new-read home join; no payload, lease or ACK invented."""
    rank_extents=defaultdict(list)
    for rows in (produced['rows'],initial['rows']):
        for home in rows:
            rank_extents[home['rank']].append((home['base'],home['base']+home['reservation_bytes']))
    for rank,extents in rank_extents.items():
        for start,end in sorted(extents):
            if start<33554432 or end>67108864:raise ValueError('r33 finite32MiB state extent')
        for (_,end),(start,_) in zip(sorted(extents),sorted(extents)[1:]):
            if end>start:raise ValueError('r33 initial/produced state home alias')
    index={(h['PC'],h['version'],h['rank']):(i,h) for i,h in enumerate(produced['rows'])}
    if len(index)!=len(produced['rows']):raise ValueError('r33 duplicate output home identity')
    rows=[]
    for changed in adapter['changed_window_PCs']:
        for home in changed['window_homes']:
            joins=[j for j in changed['template_joins'] if j['input_version']==home['version']]
            if len(joins)!=1:raise ValueError('r33 window input version source join')
            j=joins[0];key=(changed['pc'],j['output_version'],home['rank'])
            if key not in index:raise ValueError('r33 actual produced window home missing')
            i,out=index[key]
            if out['source_template']!=j['old_template'] or out['shape']!=[128,512] or out['bytes']!=128*2048 or out['dtype']!='F32':
                raise ValueError('r33 output source shape/typed home mismatch')
            rows.append({'pc':changed['pc'],'rank':home['rank'],'current_template':j['new_template'],
                'input':home,'output':{'version':out['version'],'base':out['base'],'bytes':out['bytes'],
                    'home_ref':'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/finite_state_homes.json#/rows/'+str(i)},
                'output_shape_source_equivalence_proved':True,'initial_generation':1,
                'output_generation_or_lease':None,'actual_refill_visible_ACK_reverse_receipt':None})
    return {'schema':'H4_DS_R33_CONCRETE_WINDOW_PROVIDER_SOURCE_JOIN_V1','source_context':adapter['source_context'],
        'rank_window_pairs':len(rows),'bindings':rows,'extent_bytes_per_rank':33554432,'AW':27,
        'hardware_address_translation':None,'source_payloads_supplied':False,'hardware_admitted':False}


def reconcile_tp96_literal_collectives(record, preflight, fixture, log, operations, costs):
    """Join literal transport receipts, retaining source and clock distinctions.

    The constructive repeated-word calendar is a provisional endpoint-only
    reservation. Arithmetic, codecs, source refill and physical clocks remain
    separately owned; no conversion or summation with native software ticks.
    """
    required={'admit','reduce_word_route','gather_word_route','consumer_record','visible_ACK','reverse'}
    if set(costs)!=required:raise ValueError('explicit TP96 endpoint cycle table required')
    for k,v in costs.items():positive(v,k)
    normal=record['cases']['normal']
    if (record['schema']!='w15_tp96_exact_v1' or not normal['passed'] or normal['rc']!=0 or
        normal['parameters']!={'STALL':0,'BAD_ORDER':0,'BAD_TAG':0} or normal['endpoints']!=96):
        raise ValueError('TP96 normal receipt scope')
    if hashlib.sha256(log.encode()).hexdigest()!=normal['log_sha256']:
        raise ValueError('TP96 normal log pin mismatch')
    pattern=r'OP op=(\d+) die=(\d+) mode=(\d+) words=(\d+) issue=(-?\d+) first_tx=(-?\d+) last_tx=(-?\d+) first_vm=(-?\d+) last_vm=(-?\d+) done=(-?\d+) writes=(\d+) expect=(\d+)'
    rows=[tuple(map(int,m)) for m in re.findall(pattern,log)]
    if len(rows)!=288 or {(r[0],r[1]) for r in rows}!={(o,r) for o in range(3) for r in range(96)}:
        raise ValueError('TP96 actual endpoint rows incomplete')
    credits=[tuple(map(int,m)) for m in re.findall(r'CREDIT die=(\d+) waiting=(\d+) consumer_stall=(\d+) landing_peak=(\d+) accepted=(\d+)',log)]
    if len(credits)!=96 or {r[0] for r in credits}!=set(range(96)) or any(r[3]>128 or r[4]!=7136 for r in credits):
        raise ValueError('TP96 finite landing/consumer records')
    if 'W15DONE' not in log or 'faults=0' not in log or any(x in log for x in ['%Error','%Fatal','W15TIMEOUT']):
        raise ValueError('TP96 normal round did not retire')
    comparisons=[]
    for index,desc in enumerate(fixture['ops']):
        prior=next(p for p in preflight['cases'] if p['name']==desc['name'])
        observed=[r for r in rows if r[0]==index];copies=96 if desc['mode'] else 1
        if any(r[2]!=desc['mode'] or r[3]!=desc['words'] or r[10]!=r[11] or r[11]!=desc['words']*copies for r in observed):
            raise ValueError('TP96 literal descriptor/endpoint span mismatch')
        cycles=max(r[9]-r[4] for r in observed)
        if cycles!=normal['cycles'][desc['name']]:raise ValueError('TP96 cycle extraction mismatch')
        bound=prior['composed_serial_cycles_upper_bound']
        comparisons.append({'name':desc['name'],'words_per_rank':desc['words'],'payload_bytes_per_rank':desc['bytes'],
            'physical_bytes_per_rank':desc['words']*64,'normal_cycles':cycles,'prior_preflight_cycles':bound,
            'bound_verdict':'FAIL_NORMAL_EXCEEDS_PREFLIGHT' if cycles>bound else 'NORMAL_WITHIN_PREFLIGHT_NOT_STALL_PROOF',
            'normal_minus_preflight_cycles':cycles-bound,'consumer_floor_cycles':desc['words']*copies})
    if [o['pc'] for o in operations]!=list(range(len(operations))):raise ValueError('source PC coverage/order')
    cursor=0;calendar=[];bindings=[]
    for op in operations:
        pc=op['pc'];family=op['opcode']
        if any(d>=pc or d<0 for d in op['dependencies']):raise ValueError('TP96 source dependency/deadlock')
        if family not in ('all_reduce','all_gather','topk_merge','kv_gather'):
            calendar.append({'pc':pc,'native_dependency_refs':op['dependencies'],'endpoint_reservation':None,
                'native_provider_cost_owner':'existing native/V1 calendar; unchanged'})
            continue
        source=op['source']['op'];payload=positive(source['bytes'],'source collective payload')
        if op['participants']!=list(range(96)) or source['kind']!=family:raise ValueError('TP96 source participant binding')
        reduce=family=='all_reduce';copies=1 if reduce else 96
        # Gather payload is global; round up each rank to whole literal64B words.
        per_rank=payload if reduce else ceil(payload,96);words=ceil(per_rank,64)
        phases=[{'phase':'atomic_all_endpoint_admit','cycles':costs['admit']},
            {'phase':'literal64B_route','cycles':costs['reduce_word_route' if reduce else 'gather_word_route']},
            {'phase':'all_endpoint_consume','cycles':copies*costs['consumer_record']},
            {'phase':'visible_ACK','cycles':costs['visible_ACK']},
            {'phase':'reverse_and_release','cycles':costs['reverse']}]
        duration=words*sum(p['cycles'] for p in phases);end=cursor+duration
        demand={'pc':pc,'family':family,'source_op':source,'payload_bytes_global':payload,
            'payload_bytes_per_rank_upper':per_rank,'literal_words_per_rank':words,'physical_bytes_per_rank':words*64,
            'consumer_records_per_endpoint':words*copies,'consumer_floor_cycles':words*copies,
            'word_phase_order':phases,'word_repetitions':words,'start_endpoint_cycles':cursor,'end_endpoint_cycles':end,
            'global_collective_credit':1,'rank_service_credit_each':1,'landing_records_reserved_each':copies,
            'landing_capacity_each':128,'endpoint_count':96,'release_before_next_word':True,
            'source_versions':{'reads':op['reads'],'writes':op['writes']},
            'provider_home_binding':'canonical native instruction /instructions/'+str(pc)+' read/write home_indices; payload ports/ACK still UNKNOWN',
            'parent_refill_ACK_reverse_cost':None,
            'native_arithmetic_codec_cost_owner':'existing native calendar; no replacement or extra charge',
            'production_endpoint_cycles':None,'measured_full_PC_cycles':None,'provisional':True}
        if source.get('tag')=='expert_intermediate_gather':
            demand['normal_fixture_shape_match']=per_rank==288
            demand['fixture_gap']='normal fixture six slots/288B/five words; actual source seven slots/336B/six words' if per_rank==336 else 'source shape requires independent binding'
        if family=='topk_merge':demand['transport_gap']='raw gather only; selection and source I64/value wire codec not qualified by opaque fixture'
        if family=='kv_gather':demand['transport_gap']='conservative all96 raw gather demand; actual heads-only ownership/refill mapping UNKNOWN'
        bindings.append(demand);calendar.append({'pc':pc,'native_dependency_refs':op['dependencies'],'endpoint_reservation':len(bindings)-1})
        cursor=end
    return {'schema':'H4_TP96_LITERAL_COLLECTIVE_FULL_PC_COMPONENT_V1','PCs':len(operations),
        'collective_PCs':len(bindings),'case_reconciliation':comparisons,'ordered_PC_join':calendar,
        'endpoint_reservations':bindings,'endpoint_only_provisional_cycles':cursor,'explicit_endpoint_costs':costs,
        'finite_resource_proof':{'rank_count':96,'landing_capacity_each':128,'maximum_word_reservation_each':96,
            'global_collective_capacity':1,'atomic_all_endpoint_admission':True,'word_release_after_all_consumers':True,
            'no_overlap_assumed':True,'proof_scope':'constructive repeated-word software reservations; production runtime UNKNOWN'},
        'normal_scope':'actual96 endpoint functional rounds and harness credit admission only',
        'stalled_case_status':'NOT_JOINED_PENDING_INDEPENDENT_RECEIPT','serial_test_clock_ns':1.111111,
        'prior_preflight_serial_clock_ns':preflight['clocks']['serial_ns'],
        'native_software_ticks_changed':False,'physical_timings_changed':False,'headline_delta':None,
        'complete_program_latency':None,'hardware_admitted':False}


def join_v1_physical_capacity(model):
    """Retain the reviewed slot failure and finite owner contract, without credit.

    Exact rank/SM identities are checked independently of analytical geometry.
    This does not price absent operand routes or install an H1 owner gateway.
    """
    if model['schema']!='opentallas.H4.V1.physical-join.v1' or model['hardware_admitted'] or model['RTL_allowed']:
        raise ValueError('V1 physical model scope changed')
    rf=model['RF_contract']
    expected={'command_credit':1,'RF_transaction_credit':1,'read_vectors_per_accept':2,
        'write_vectors_per_accept':1,'physical_write_mirrors':2,'RF_vector_count':512,
        'response_payload_B':1024,'write_mirror_payload_B':1024}
    if any(rf.get(k)!=v for k,v in expected.items()):raise ValueError('V1 finite RF mirror/credit contract')
    joined={}
    for name,ranks in [('Qwen',2),('DeepSeek',96)]:
        m=model['models'][name];mapping=m['rank_to_die_SM']
        identities=[(r['rank'],r['SM']) for r in mapping]
        if len(mapping)!=ranks*32 or set(identities)!={(r,s) for r in range(ranks) for s in range(32)}:
            raise ValueError('V1 finite rank/SM map incomplete or duplicate')
        if any(r['die']!=r['rank'] or r['instance']!='die%d/sm%d'%(r['rank'],r['SM']) for r in mapping):
            raise ValueError('V1 physical instance identity')
        if m['calendar']['RF_read_II']!=3 or m['calendar']['RF_write_II']!=2:
            raise ValueError('V1 source RF serialized service phases')
        joined[name]={'replicas':len(mapping),'rank_SM_mapping_sha256':hashlib.sha256(
            json.dumps(mapping,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'slot':m['slot'],'routing':m['routing'],'calendar':m['calendar'],
            'G0_verdict':m['G0_verdict'],'opcode_hardware_coverage':m['opcode_hardware_coverage']}
    return {'schema':'H4_CALENDAR_V1_PHYSICAL_CAPACITY_JOIN_V1','models':joined,'RF_contract':rf,
        'source_pins':model['source_pins'],'blockers':model['blockers'],
        'additional_C0_or_RF_cost_applied':False,'dynamic_RF_ledger':None,
        'hardware_admitted':False,'clock_or_ns_conversion':None}


def validate_kepler_state_publication(receipt, binding):
    """Consume actual r30 terminal receipts without treating them as full journals."""
    identity=receipt['identity'];expected={'PC':binding['PC'],'version':binding['version'],'rank':binding['rank']}
    if any(identity.get(k)!=v for k,v in expected.items()):raise ValueError('Kepler parent publication source identity mismatch')
    if type(identity.get('generation'))!=int or not 0<identity['generation']<1<<64:raise ValueError('Kepler publication generation')
    if receipt.get('pending_obligations')!=0:raise ValueError('Kepler publication has outstanding debt')
    if not re.fullmatch('[0-9a-f]{64}',receipt.get('payload_sha256',{}).get('data','')):raise ValueError('Kepler publication payload pin')
    events=receipt['events']
    if [e['event'] for e in events]!=['software_backing_visible','consumer_accept','validated_reverse_grant']:
        raise ValueError('Kepler publication actual visibility/consume/reverse order')
    last_sequence=-1;last_tick=-1;owner=None
    for event in events:
        if event['identity']!=identity or type(event['sequence'])!=int or event['sequence']<=last_sequence or event['source_tick']<last_tick:
            raise ValueError('Kepler publication owner or event order')
        fragment=event['source_fragment_identity']
        if (type(event['source_tag'])!=int or not 0<=event['source_tag']<4 or
            type(event['source_tag_generation'])!=int or not 0<=event['source_tag_generation']<1<<64):
            raise ValueError('Kepler finite tag/generation extent')
        if any(fragment.get(k)!=v for k,v in {'target':'DeepSeek','rank':binding['rank'],'pc':binding['PC'],'epoch':identity['generation'],
            'sector':(binding['base']+binding['bytes']-1)//32}.items()):raise ValueError('Kepler terminal sector/source mismatch')
        token=(fragment,event['source_tag'],event['source_tag_generation'])
        if owner is not None and token!=owner:raise ValueError('Kepler reverse tag/generation mismatch')
        owner=token;last_sequence=event['sequence'];last_tick=event['source_tick']
    return {'status':'PASS_SOURCE_BOUND_TERMINAL_PUBLICATION','binding':binding,'receipt':receipt,
        'whole_fragment_sector_journal_bound':False,'RF_phase_cost_debit':None,
        'parent_forward_refill_ACK_reverse_complete':False,'hardware_admitted':False}


def audit_ds_mtp_source_contract(native, acceptance, isa_source, golden_source, uarch_source):
    """Source/causal audit composed with provider/V1 gates, not an MTP executor."""
    tree=ast.parse(isa_source);run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_mtp')
    text=ast.get_source_segment(isa_source,run)
    if not all(s in text for s in ('compile_layer','compile_head','tokens[1:]','pos0 + j','hists[j]')):
        raise ValueError('MTP verify source contract changed; audit required')
    draft=next(n for n in ast.parse(golden_source).body if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='DRAFTS' for t in n.targets))
    drafts=ast.literal_eval(draft.value)
    if len(drafts)!=5:raise ValueError('six-position MTP reference contract required')
    hbm=next(n.value for n in ast.parse(uarch_source).body if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='HBM_W19' for t in n.targets))
    if not isinstance(hbm,ast.Call) or not isinstance(hbm.func,ast.Name) or hbm.func.id!='dict':raise ValueError('HBM_W19 source model contract')
    fields={k.arg:ast.literal_eval(k.value) for k in hbm.keywords if k.arg in ('ar_us','mtp_pass_us','drafter_us')}
    cohorts={name:acceptance['results'][group]['walk']['tau'] for name,group in [('overall','overall')]}
    cohorts['chat']=acceptance['results']['per_class']['chat']['walk']['tau']
    cohorts['reasoning']=acceptance['results']['per_class']['reasoning']['walk']['tau']
    return {'schema':'H4_DS_MTP_CAUSAL_PROVIDER_NATIVE_SOURCE_AUDIT_V1','status':'MTP_NATIVE_ITERATION_CONTRACT_INCOMPLETE',
        'AR_native_program':{'PCs':len(native['instructions']),'family_count':len(native['coverage']['families']) if isinstance(native['coverage']['families'],dict) else native['coverage']['families'],
            'scope':'single-reference-position native program; no MTP accepted-token credit'},
        'source_verify_program':{'path':'tools/w19_hbm_tp96_isa.py:run_mtp','positions':6,
            'order':'layer-major; j=0..5, pos=pos0+j, history=hist0+tokens[1:1+j]',
            'ownership':'distinct PR[j] rank buffers; causal shared State compressed/index stores and per-rank window appends',
            'head':'compile_head per position, source greedy target prefix acceptance',
            'actual_primitive_microprograms_and_version_home_calendar':None,
            'scope':'ISA/source execution uses high-level numerical families; does not replace H3 primitive recipes'},
        'reference_drafts':{'fixed_token_ids':drafts,'actual_drafter_executed_by_reference':False,
            'native_draft_program_and_provider_versions':None},
        'causal_KV_successor_contract':{
            'identity':['iteration','position_j','logical_position','version','rank','SM','generation'],
            'visibility':'position j may read retained committed history plus earlier verified-position state; later positions never visible',
            'states':['window rows','compressed KV rows','index-key/code/scale rows','compressor open slots','State.n row counts','token history','draft hidden/cache state'],
            'accepted_commit':'publish processed anchor and accepted draft-input KV/index/window versions after visible ACKs; emit accepted drafts plus target bonus',
            'bonus_token':'next pending input; no fabricated KV for the unprocessed bonus',
            'rejected_suffix':'restore all speculative state counters/views and reclaim suffix leases only after consumer/return/reverse debt drains',
            'implemented_native_commit_or_rollback_program':None},
        'acceptance':{'overall_walk_tau':cohorts['overall'],'pooled_prompts':acceptance['results']['overall']['prompts'],
            'chat_walk_tau':cohorts['chat'],'reasoning_walk_tau':cohorts['reasoning'],
            'headline_rounded_assumption':acceptance['headline']['tau'],
            'bonus_included':True,'scope':'36-prompt pooled short-context own greedy continuations; not reasoning-only',
            'arithmetic_transfer_to_exact_chunk8_1M':'UNPROVEN; different GEMM summation order and own short-context continuations',
            'caveats':acceptance['caveats'],'budget_record_owner':'parent additive cohort/iteration budget record',
            'headline_requirement':'primary third-party V4.1 gamma5 agentic per-request committed-token/verify receipts with matching costs',
            'headline_agentic_median_rate':None,'local_chat_role':'sensitivity only; not the DS headline',
            'local_pooled_role':'sensitivity/acceptance experiment only; not third-party agentic median'},
        'modeled_reference_us':{'AR_baseline':fields['ar_us'],'six_position_verify':fields['mtp_pass_us'],
            'draft':fields['drafter_us'],'qualification':'modeled historical contributions; not calibrated complete native iteration'},
        'missing_complete_iteration_costs':{k:None for k in ['source_native_draft','six_position_native_verify_and_cross_position_provider_movement',
            'accepted_prefix_and_bonus_commit','rejected_suffix_rollback_and_lease_drain','acceptance_control_and_target_compare',
            'causal_index_KV_append_refill_and_code_scale_visibility','clock_domain_CDC_and_calibrated_endpoint_stalls']},
        'software_ticks_to_us_conversion':None,'full_iteration_calibrated_us':None,'accepted_token_rate_qualified':False,
        'composition':'must close the same provider/home/ACK/reverse and V1/C0 gates; AR full run is a separate gate'}


def agentic_request_rate_summary(receipts):
    """Median request rates, with full matching iteration costs and gamma5 proof."""
    import statistics
    if not receipts:return {'status':'PENDING_PRIMARY_AGENTIC_RECEIPTS','median_request_tokens_s':None,
        'pooled_tokens_per_verify':None,'pooled_tokens_s':None,'qualified_headline':False}
    rates=[];tokens=cycles=cost=0;ids=set()
    for row in receipts:
        if row['request_id'] in ids:raise ValueError('duplicate third-party request')
        ids.add(row['request_id'])
        if row.get('workload_class')!='agentic' or row.get('gamma')!=5 or row.get('model')!='DeepSeek-V4.1-Flash':
            raise ValueError('actual V4.1 gamma5 agentic request required')
        if row.get('acceptance_mode')!='actual' or row.get('includes_committed_bonus') is not True:
            raise ValueError('actual committed-token counters required; synthetic acceptance rejected')
        if not re.fullmatch('[0-9a-f]{64}',row.get('source_receipt_sha256','')):raise ValueError('primary request receipt pin required')
        n=positive(row['committed_tokens'],'request committed tokens');v=positive(row['verify_iterations'],'request verify iterations')
        costs=row['complete_iteration_costs_us']
        if len(costs)!=v or any(type(c) not in (int,float) or not math.isfinite(c) or c<=0 for c in costs):
            raise ValueError('matching complete per-iteration costs required')
        if n>6*v:raise ValueError('gamma5 committed-token count extent')
        duration=sum(costs);rates.append(n*1e6/duration);tokens+=n;cycles+=v;cost+=duration
    return {'status':'PASS_REQUEST_RATE_AGGREGATION_SOURCE_TRANSFER_GATE_SEPARATE','requests':len(rates),
        'median_request_tokens_s':statistics.median(rates),'per_request_tokens_s':rates,
        'pooled_tokens_per_verify':tokens/cycles,'pooled_tokens_s':tokens*1e6/cost,
        'qualified_headline':False,'transfer_to_exact_1M_native_contract':None}


def resolve_ds_forward_leaf_reference(catalog, N, S, ref, *, expected_rank):
    """Existing importer hook: resolve actual source leaf/iteration, not strings."""
    if not isinstance(ref,dict):raise ValueError('structured source forward leaf reference required')
    tid=ref.get('parent_template');ci=ref.get('call_index');iteration=ref.get('invocation_index')
    if tid not in catalog['templates']:raise ValueError('forward parent template unknown')
    calls=catalog['templates'][tid]['calls']
    if type(ci)!=int or not 0<=ci<len(calls):raise ValueError('forward leaf call index out of range')
    call=calls[ci];key=call['leaf']
    if ref.get('template')!=key:raise ValueError('forward leaf id does not match source call')
    if type(iteration)!=int or not 0<=iteration<call['repetitions']:raise ValueError('forward invocation out of range')
    record=catalog['leaves'][key]
    if 'program' not in record:raise ValueError('staged source uses retained native template resolver')
    program=record['program']
    if hashlib.sha256(json.dumps(program['code'],sort_keys=True,separators=(',',':')).encode()).hexdigest()!=record['code_sha256']:
        raise ValueError('forward leaf retained source code hash mismatch')
    if call['dynamic_source_parameters']:
        parameters=ref.get('source_parameters',{})
        if record['source_builder']!='index_program' or parameters!={'first':iteration,'rank':expected_rank} or not 0<=expected_rank<96:
            raise ValueError('forward dynamic row/rank source binding mismatch')
        h,w,n,_,_=record['source_builder_args'];program=S.index_program(h,w,n,iteration,expected_rank)
    elif ref.get('source_parameters',{}):raise ValueError('unexpected forward dynamic source parameters')
    return resolve_ds_movement_reference({'templates':{key:program}},key,ref)


def native_value_specs(program, template_id):
    widths={};specs={}
    for definition,i in enumerate(program['templates'][template_id]['code']):
        op=i['op']
        if op in ('LOAD','CONST'):w=8 if i['attrs']['dtype']=='I64' else 4
        elif op=='F2I':w=8
        elif op in ('I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_U','BITCAST_F') or op.startswith('FCMP'):w=4
        else:w=max((widths[v] for v in i['src']),default=8 if op=='IOTA' else 4)
        widths[i['dst']]=w;specs[i['dst']]={'bytes':max(1,math.prod(i['shape']))*w,'width':w,'definition':definition}
    return specs


def compile_g0_source_interface(qwen, ds_catalog):
    """Both-program source instruction demand for Popper G0; no hardware credit."""
    caps=read_json(ROOT/OUT/'h4_actual_config_e844/inputs/primitive_capabilities.json')
    opcodes={r['opcode'] for r in caps if r['implementation_requirement']=='V1'}
    qrows=[];qtotals=Counter();dstotals=Counter();drows=[]
    for op in qwen['operations']:
        counts={k:v for k,v in op['calendar_export']['physical_primitives']['native_primitive_commands'].items() if k in opcodes}
        qtotals.update(counts);qrows.append({'pc':op['pc'],'family':op['opcode'],'G0_native_commands':counts,
            'source_kernel_invocations':op['calendar_export']['physical_primitives']['kernel_invocations']})
    for op in ds_catalog['PC_bindings']:
        counts={k:v for k,v in op['native_batches128'].items() if k in opcodes}
        dstotals.update(counts);drows.append({'pc':op['pc'],'family':op['family'],'G0_native_batches128':counts,
            'actual_rank_template_leaf_refs':op['bindings']})
    records=[]
    for tid,t in ds_catalog['templates'].items():
        if t['execution_path']=='source_order_live_range_stages':continue
        for j,call in enumerate(t['calls']):
            leaf=ds_catalog['leaves'][call['leaf']];program=leaf['program'];specs=native_value_specs({'templates':{'leaf':program}},'leaf')
            for i,node in enumerate(program['code']):
                if node['op'] not in opcodes:continue
                n=max(1,math.prod(node['shape']));width=specs[node['dst']]['width']
                records.append({'template':tid,'leaf':call['leaf'],'call_index':j,'code_index':i,
                    'opcode':node['op'],'attrs':node['attrs'],'shape':node['shape'],'src':node['src'],'dst':node['dst'],
                    'invocation_repetitions':call['repetitions'],'native_batches128_per_invocation':ceil(n,128),
                    'output_word_bits':width*8,'output_RF_vectors_per128batch':ceil(min(128,n)*width,512),
                    'source_typed_bytes':{s:specs[s]['bytes'] for s in node['src']},
                    'source_RF_whole_operand_vector_upper':sum(ceil(specs[s]['bytes'],512) for s in node['src']),
                    'dynamic_source_parameters':call['dynamic_source_parameters'],
                    'operand_window_movement_binding':'UNKNOWN unless actual bounded continuation/provider route resolves'})
    return {'schema':'H4_G0_BOTH_PROGRAM_SOURCE_PORT_COST_INTERFACE_V1','owner':'Popper V1/G0; C0 Sagan; finite composition Dewey',
        'Qwen':{'PCs':len(qrows),'families':len({r['family'] for r in qrows}),'native_commands':dict(qtotals),'PC_bindings':qrows},
        'DeepSeek':{'PCs':len(drows),'families':len({r['family'] for r in drows}),'native_batches128':dict(dstotals),'PC_bindings':drows},
        'DS_forward_instruction_records':records,
        'opcode_cost_contract':{op:{'provisional_service_ticks_per128batch':32,'measured_cycles':None,
            'exact_source_semantics_gate':'attrs, dtype, shifts/overflow, signedness, predicates, converts and I64 paired words; no FP arithmetic substitution',
            'routing_area_qualification':None,'area_um2_per_replica':None} for op in sorted(opcodes)},
        'RF_port_contract':{'read_ports':2,'logical_write_ports':1,'port_bits':4096,'mirrored_physical_write_copies':2,
            'transaction_credit':1,'release':'two-mirror visible_ACK','workspace_vectors':32,'logical_vectors':512,
            'I64':'two32-bit words; up to two4096-bit result transactions per128lane batch; paired-word execution and carry/predicate gate required'},
        'replicas':{'Qwen_ranks':2,'DeepSeek_ranks':96,'SMs_per_rank':32},
        'C0_interface':'h4_actual_config_e844/C0_Sagan_interface.json',
        'routing':'actual operand/result/control bit demand, mux/demux/fanout and channel/slot fit required before RTL; UNKNOWN measured fit',
        'cost_integration':'replace retained native term exactly once with opcode table only after source-exact interface gate; no add-on double charge',
        'hardware_full_native_claim':False,'numerical_execution':False}


def resolve_ds_movement_reference(program, template_id, ref, specs=None):
    """Resolve an exact retained SSA instruction and its typed operand."""
    if not isinstance(ref,dict) or ref.get('template')!=template_id:
        raise ValueError('structured retained native instruction reference required')
    index=ref.get('code_index');code=program['templates'][template_id]['code']
    if type(index)!=int or not 0<=index<len(code):raise ValueError('native instruction index out of range')
    node=code[index]
    specs=specs if specs is not None else native_value_specs(program,template_id)
    if ref.get('opcode')!=node['op'] or ref.get('attrs')!=node['attrs'] or ref.get('result_shape')!=node['shape']:
        raise ValueError('native instruction opcode attrs shape mismatch')
    operand=ref.get('operand')
    if operand=='dst':symbol=node['dst'];definition=index
    elif isinstance(operand,str) and re.fullmatch('src:[0-9]+',operand):
        j=int(operand[4:])
        if j>=len(node['src']):raise ValueError('native operand index out of range')
        symbol=node['src'][j];definition=specs.get(symbol,{}).get('definition')
        if definition is None or definition>=index:raise ValueError('native source definition missing')
    else:raise ValueError('native operand role required')
    if ref.get('value')!=symbol:raise ValueError('native operand value mismatch')
    size=specs[symbol]['bytes'];width=specs[symbol]['width']
    offset=ref.get('logical_byte_offset');payload=ref.get('payload_bytes')
    if type(offset)!=int or type(payload)!=int or offset<0 or payload<=0 or offset%width or payload%width or offset+payload>size:
        raise ValueError('native operand typed span out of range')
    return (index,operand),symbol,size,offset,payload


def verify_ds_operand_journal(program, template, reference, binding, events, *, translation=None):
    """Resolve one actual bounded operand call and all its sector/reverse debt.

    Sagan owns capture/continuation. This validates its received source span and
    Kepler's backing-address namespace; it does not generate movement receipts.
    A translated address is software mapping evidence, never an installed port.
    """
    _,symbol,size,offset,length=resolve_ds_movement_reference(program,template,reference)
    if length>512:raise ValueError('explicit bounded512B operand tile required')
    required={'PC','rank','SM','generation','lease','version','native_SSA_value',
        'logical_base','allocation_bytes','operand_base_offset','shared_tile_offset','shared_capacity_bytes'}
    if not required<=binding.keys():raise ValueError('concrete owner/allocation/lease binding required')
    if binding['native_SSA_value']!=symbol or not binding['version'] or not binding['lease']:
        raise ValueError('source SSA/version/lease identity mismatch')
    for k in ('PC','rank','SM','generation','logical_base','allocation_bytes','operand_base_offset','shared_tile_offset','shared_capacity_bytes'):
        if type(binding[k]) is not int or binding[k]<0:raise ValueError('integer owner/address/capacity required')
    if not 0<=binding['rank']<96 or not 0<=binding['SM']<32 or binding['generation']<1:
        raise ValueError('finite32SM/rank/generation identity')
    if 'instructions' in program:
        operations=[o for o in program['instructions'] if o['pc']==binding['PC']]
        if len(operations)!=1 or not any(r.get('rank')==binding['rank'] and r.get('template')==template for r in operations[0]['rank_bindings']):
            raise ValueError('actual source PC/rank/template binding mismatch')
    if binding.get('lease_state')!='active':raise ValueError('active source operand lease required')
    if binding['shared_capacity_bytes']!=65536 or binding['shared_tile_offset']+length>65536:
        raise ValueError('physical64KiB shared tile extent exceeded')
    # Home describes this explicitly tiled operand window, not a whole array.
    window_start=binding['operand_base_offset'];relative=offset-window_start
    if relative<0 or relative+length>binding['allocation_bytes']:
        raise ValueError('source operand tile outside concrete allocation window')
    address=binding['logical_base']+relative
    if address%32:raise ValueError('actual software sector alignment required')
    capacity=positive(binding.get('provider_tag_capacity'),'provider_tag_capacity')
    expected=set(range(address//32,(address+length+31)//32))
    direction='write' if reference['operand']=='dst' else 'read'
    transactions={};live={};tag_generations={};covered=set();last_tick=-1;peak=0;phase_counts=Counter();digest=hashlib.sha256()
    for ordinal,e in enumerate(events):
        digest.update(json.dumps(e,sort_keys=True,separators=(',',':')).encode()+b'\n')
        identity=e.get('identity',{});name=e.get('event');tick=e.get('tick')
        if e.get('hardware') is not False or type(tick) is not int or tick<last_tick:
            raise ValueError('ordered software journal tick/scope required')
        last_tick=tick
        if (identity.get('target'),identity.get('rank'),identity.get('pc'),identity.get('epoch'))!=('DeepSeek',binding['rank'],binding['PC'],binding['generation']):
            raise ValueError('sector journal owner/generation differs from source lease')
        sector=identity.get('sector');tag=e.get('tag');generation=e.get('generation')
        if sector not in expected or type(tag)is not int or not 0<=tag<capacity or type(generation)is not int or generation<1:
            raise ValueError('accepted sector/span/tag identity required')
        key=(json.dumps(identity,sort_keys=True),tag,generation)
        if name=='request_accept':
            if key in transactions or tag in live:raise ValueError('live tag reused before matching reverse')
            if generation<=tag_generations.get(tag,0):raise ValueError('recycled tag generation did not advance')
            tag_generations[tag]=generation
            transactions[key]=dict(phase=1,sector=sector,first_tick=tick);live[tag]=key;peak=max(peak,len(live))
        else:
            if key not in transactions or live.get(tag)!=key:raise ValueError('event without matching live acceptance')
            row=transactions[key];phase=row['phase']
            if name in ('write_residence_reserved','software_owned_issue','software_service_phases_reserved'):
                if phase!=1:raise ValueError('issue/reservation after returned backing')
            elif name in ('software_backing_visible','software_read_capture'):
                if phase!=1 or name!=('software_backing_visible' if direction=='write' else 'software_read_capture'):
                    raise ValueError('backing visibility/capture direction or order')
                row['phase']=2
            elif name in ('consumer_accept','reverse_credit_accept','validated_reverse_grant'):
                sequence=('consumer_accept','reverse_credit_accept','validated_reverse_grant')
                if phase not in (2,3,4) or name!=sequence[phase-2]:raise ValueError('premature/stale consumer/reverse grant')
                row['phase']+=1
                if name=='validated_reverse_grant':
                    if sector in covered:raise ValueError('duplicate completed sector in operand call')
                    covered.add(sector);del live[tag]
            else:raise ValueError('failed/unknown movement journal event: '+str(name))
        phase_counts[name]+=1
    if live or not transactions or covered!=expected:raise ValueError('partial operand span or reverse debt retained')
    if peak>capacity:
        raise ValueError('finite provider tag capacity exceeded or absent')
    mapped=None
    if translation is not None:
        if any(translation.get(k)!=binding[k] for k in ('rank','SM','generation','version','lease')):
            raise ValueError('physical translation owner/version/lease mismatch')
        for k in ('logical_base','physical_base','bytes','AW'):
            if type(translation.get(k))is not int or translation[k]<0:raise ValueError('explicit physical mapping required')
        if not 1<=translation['AW']<=64:raise ValueError('physical address width')
        start=translation['logical_base'];end=start+translation['bytes']
        if address<start or address+length>end:raise ValueError('physical translation does not cover source span')
        mapped=translation['physical_base']+address-start
        if mapped+length>1<<translation['AW']:raise ValueError('physical translated extent exceeds AW')
    return dict(schema='H4_DS_ACTUAL_OPERAND_JOURNAL_ADMISSION_V1',source_reference=reference,
        source_SSA_bytes=size,owner={k:binding[k] for k in ('PC','rank','SM','generation','version','lease')},
        logical_byte_address=address,physical_byte_address=mapped,physical_translation_bound=translation is not None,
        payload_bytes=length,sector32_transactions=len(transactions),scratch64_transactions=(binding['shared_tile_offset']%64+length+63)//64,
        phase_counts=dict(phase_counts),peak_live_provider_tags=peak,matching_reverse_drained=True,
        journal_sha256=digest.hexdigest(),additional_provider_RF_C0_I64_charge=0,
        cost_replacement=None,actual_lease_acquisition_and_release_journal=None,
        installed_home_directory_source_pin=None,whole_program_movement_complete=False,hardware_admitted=False)


def load_group_native_primitive_factory(sources):
    """Only exact retained generic VM instructions, no arithmetic callback."""
    import numpy as np
    expected={'bounded_native':'282e57ab97f2dcdd0205b6f4e11ec189b669e3cc48548fab5f6d3c373d63c32b',
              'arithmetic_helpers':'9a231227d3d605cd34aec0629300bf24ff561b14d0b65364a696f9c5be4a6c76'}
    if set(sources)!=set(expected):raise ValueError('exact generic primitive source closure required')
    for name,digest in expected.items():
        if not isinstance(sources[name],bytes) or hashlib.sha256(sources[name]).hexdigest()!=digest:
            raise ValueError('generic primitive source pin mismatch: '+name)
    tree=ast.parse(sources['bounded_native']);nodes=[]
    nodes.extend(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='COMMON_NATIVE' for x in n.targets))
    nodes.append(next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativePrimitiveVM'))
    nodes.append(next(n for n in ast.parse(sources['arithmetic_helpers']).body if isinstance(n,ast.FunctionDef) and n.name=='poszero'))
    ns=dict(np=np,F=np.float32,Counter=Counter)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned-source-generic-group-primitive-VM','exec'),ns)
    return ns['NativePrimitiveVM']


def execute_ds_group128_tiles(plan, PC, rank, generation, source, shared_factory, primitive_sources, output, *, movement_observer=None):
    """Execute all64 current-source tiles with actual journalled shared calls.

    Source/output hooks move bytes and leases only; arithmetic is the retained
    generic primitive VM. Failure retains the owner's leases and journal debt.
    This is an executable kernel join, not a full-program execution receipt.
    """
    import numpy as np
    if type(generation)is not int or generation<1:raise ValueError('positive source generation required')
    primitive_factory=load_group_native_primitive_factory(primitive_sources)
    parent=plan.parents[PC];tid=parent['new_template'];program=plan.templates[tid]
    if hashlib.sha256(json.dumps(program,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=tid:
        raise ValueError('actual retained group template identity mismatch')
    if (plan.inventory['source_native_sha256'],plan.inventory['source_dispatch_sha256'])!=('c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264','bcf7d800aa64aeff92b8a1954cab328911c400025179d6a9ab9f211a934c253c'):
        raise ValueError('current native/dispatch source identity required')
    uses=Counter(v for node in program['code'] for v in node['src']);uses.update(program['outputs'].values())
    scalar_counts=Counter();step_counts=Counter();movement_counts=Counter();proof_hash=hashlib.sha256();output_hash=hashlib.sha256();peak_RF=0
    published=[];constants={};sector_ticks=0;provider_parameters=None;constant_vm=primitive_factory()
    for node in program['code']:
        if node['op']=='CONST':
            constants[node['dst']]=constant_vm.primitive('CONST',[],attrs=node['attrs'],shape=())
            scalar_counts['CONST']+=1;step_counts['CONST']+=1
    for group in range(8):
        for first in range(0,1024,128):
            tile=plan.tile(PC,rank,group,first)
            expected_output=group*1024+first
            if (tile['source_PC'],tile['destination_rank'],tile['parent_template'],tile['output_flat_word_first'],tile['SM'],tile['destination_version'])!=(PC,rank,tid,expected_output,expected_output//256%32,parent['writes'][0]['version']):
                raise ValueError('source tile output/owner mapping mismatch')
            expected_version=parent['provider_bindings'][tid]['parts']['version']
            if len(tile['source_spans'])!=8:raise ValueError('all eight source contributor spans required')
            for j,span in enumerate(tile['source_spans']):
                if (span['contributor'],span['source_rank'],span['source_version'],span['local_word_first'],span['LOAD_flat_word_first'],span['words'],span['bytes'])!=(j,8*group+j,expected_version,first,(j*8+group)*1024+first,128,512):
                    raise ValueError('source contributor LOAD span mapping mismatch')
            owner=dict(PC=PC,rank=rank,SM=tile['SM'],generation=generation,tile=tile['tile_ordinal'],template=tid)
            memory=shared_factory(owner)
            extent=memory.extent
            if extent.get('bytes')!=65536 or extent.get('rank')!=rank or extent.get('SM')!=tile['SM'] or extent.get('base',-1)<0:
                raise ValueError('actual finite64KiB owner shared allocation required')
            parameters=dict(phase_costs=dict(memory.p.costs),read_ticks=memory.p.read_ticks,write_ticks=memory.p.write_ticks,tag_capacity=memory.p.tags)
            if provider_parameters is not None and parameters!=provider_parameters:raise ValueError('mixed provider cost/capacity inputs require explicit model join')
            provider_parameters=parameters
            leases=[];vectors=[]
            def transfer(index,operand,value,logical_offset,shared_offset,*,raw=None):
                nonlocal sector_ticks
                node=program['code'][index]
                reference=dict(template=tid,code_index=index,opcode=node['op'],attrs=node['attrs'],result_shape=node['shape'],
                    operand=operand,value=value,logical_byte_offset=logical_offset,payload_bytes=512)
                start=len(memory.p.events)
                returned=memory.transact(shared_offset,write=raw is not None,payload=raw,length=512)
                stop=len(memory.p.events)
                if stop<=start:raise ValueError('actual provider returned no journal events')
                sector_ticks+=memory.p.events[stop-1]['tick']-memory.p.events[start]['tick']
                if memory.p.live or memory.p.queue or memory.p.calendar or memory.p.resident:raise ValueError('actual shared reverse debt not drained')
                binding=dict(PC=PC,rank=rank,SM=tile['SM'],generation=generation,version=value,lease='tile:'+str(tile['tile_ordinal']),
                    lease_state='active',native_SSA_value=value,logical_base=extent['base']+shared_offset,allocation_bytes=512,
                    operand_base_offset=logical_offset,shared_tile_offset=shared_offset,shared_capacity_bytes=65536,provider_tag_capacity=memory.p.tags)
                proof=verify_ds_operand_journal({'templates':{tid:program},'instructions':[dict(pc=PC,rank_bindings=parent['actual_rank_template_bindings'])]},
                    tid,reference,binding,memory.p.events[start:stop])
                if movement_observer is not None:
                    movement_observer(dict(owner=owner,source_reference=reference,binding=binding,journal_id=memory.p.events.id,journal_start=start,journal_end=stop,proof=proof))
                proof_hash.update(json.dumps(proof,sort_keys=True,separators=(',',':')).encode())
                movement_counts['sector32']+=proof['sector32_transactions'];movement_counts['scratch64']+=proof['scratch64_transactions']
                movement_counts['write512' if raw is not None else 'read512']+=1
                if raw is None and len(returned)!=512:raise ValueError('actual shared returned tile length')
                return returned
            for span in tile['source_spans']:
                record=source.acquire(span,owner)
                expected=dict(version=span['source_version'],rank=span['source_rank'],generation=generation,first=first,words=128)
                if any(record.get(k)!=v for k,v in expected.items()) or record.get('state')!='visible' or not record.get('lease'):
                    raise ValueError('actual source span/version/generation/lease mismatch')
                raw=record.get('data')
                if not isinstance(raw,bytes) or len(raw)!=512:raise ValueError('actual source512B F32 bytes required')
                if record.get('payload_sha256')!=hashlib.sha256(raw).hexdigest():raise ValueError('actual source span payload changed')
                leases.append(record);j=span['contributor'];offset=j*512;logical=span['LOAD_flat_word_first']*4
                transfer(0,'dst',program['code'][0]['dst'],logical,offset,raw=raw)
                raw=transfer(1+2*j,'src:0',program['code'][0]['dst'],logical,offset)
                vectors.append(np.frombuffer(raw,dtype=np.float32).copy())
            values={};remaining=uses.copy();vm=primitive_factory()
            for index,node in enumerate(program['code']):
                op=node['op'];args=[values[v] for v in node['src']]
                if op=='LOAD':value=vectors
                elif op=='CONST':value=constants[node['dst']]
                elif op=='SLICE':
                    attrs=node['attrs']
                    if attrs['axis']!=0 or attrs['step']!=1 or attrs['stop']!=attrs['start']+1:raise ValueError('original contributor SLICE source required')
                    value=args[0][attrs['start']].reshape(1,128)
                else:
                    shape=() if node['shape']==[] else (128,)
                    value=vm.primitive(op,args,attrs=node['attrs'],shape=shape)
                values[node['dst']]=value
                words=1024 if op=='LOAD' else max(1,int(np.size(value)))
                if op!='CONST':
                    scalar_counts[op]+=words;step_counts[op]+=8 if op=='LOAD' else 1
                peak_RF=max(peak_RF,sum(8 if isinstance(v,list) else max(1,(v.nbytes+511)//512) for v in values.values()))
                if peak_RF>32:raise ValueError('actual tile RF32 live capacity exceeded')
                for v in node['src']:
                    remaining[v]-=1
                    if not remaining[v]:del values[v]
            if vm.fault:raise ValueError('primitive numerical fault prevents output publication')
            raw=values[program['outputs']['out']].tobytes();logical=tile['output_flat_word_first']*4;final=len(program['code'])-1
            transfer(final,'dst',program['code'][final]['dst'],logical,8192,raw=raw)
            raw=transfer(final,'src:0',program['code'][final]['src'][0],logical,8192)
            receipt=output.write_span(tile,owner,raw)
            if (receipt.get('version'),receipt.get('rank'),receipt.get('generation'),receipt.get('first'),receipt.get('bytes'))!=(tile['destination_version'],rank,generation,tile['output_flat_word_first'],512):
                raise ValueError('actual output span/version/owner mismatch')
            if receipt.get('payload_sha256')!=hashlib.sha256(raw).hexdigest() or receipt.get('pending_obligations')!=0:
                raise ValueError('output receipt changed payload or retained reverse debt')
            # Full RF mirrored/physical visibility stays UNKNOWN; this hook must
            # supply its own complete parent provider journal for that join.
            published.append(receipt);output_hash.update(raw)
            for record in leases:source.release(record,owner)
    return dict(schema='H4_DS_EXECUTED_GROUP128_JOURNAL_KERNEL_V1',PC=PC,rank=rank,generation=generation,
        source_native_sha256=plan.inventory['source_native_sha256'],source_dispatch_sha256=plan.inventory['source_dispatch_sha256'],
        tiles_executed=64,source_spans=512,output_spans=64,shared_capacity_per_SM=65536,reserved_shared_bytes=8704,
        peak_RF_vectors=peak_RF,executed_primitive_scalars=dict(scalar_counts),executed_steps=dict(step_counts),
        actual_shared_movements=dict(movement_counts),actual_movement_proof_chain_sha256=proof_hash.hexdigest(),output_sha256=output_hash.hexdigest(),
        output_span_receipts=published,explicit_provisional_sector_parameters=provider_parameters,
        actual_serial_sector_service_software_ticks=sector_ticks,scratch64_endpoint_cost=None,
        primitive_endpoint_costs=None,actual_RF_mirror_journal=None,physical_address_translation=None,
        native_C0_provider_RF_I64_cost_added=0,full_program_executed=False,production_unknown_shared_calls=193316,
        whole_token_latency=None,hardware_admitted=False)


def bind_executed_group_shared64(control, program, inventory_call, existing_interval_id, external_bounds, *, journal_reader=None):
    """Export actual executed source spans into the selected-interval ABI.

    Positive bounds are explicit provisional model inputs, not the software
    sector timestamps converted into hardware edges. Existing charges stay put.
    """
    required={'backend_bound_edges','consumer_bound_edges','reverse_bound_edges'}
    if set(external_bounds)!=required:raise ValueError('complete explicit external wait bounds required')
    for name,value in external_bounds.items():positive(value,name)
    if not existing_interval_id:raise ValueError('retained interval identity required')
    if (inventory_call['PC'],inventory_call['rank'])!=(control['PC'],control['rank']):raise ValueError('selected call differs from executed source owner')
    template=inventory_call['template']
    if hashlib.sha256(json.dumps(program['templates'][template],sort_keys=True,separators=(',',':')).encode()).hexdigest()!=template:
        raise ValueError('retained selected template source identity mismatch')
    journals={r['journal_id']:r['events'] for r in control.get('control_disk_journal_events',[])};commands=[]
    movement_calls=control.get('actual_movement_calls',control.get('control_movement_calls'))
    if not isinstance(movement_calls,list) or not movement_calls:raise ValueError('executed movement journal calls required')
    if not journals and not callable(journal_reader):raise ValueError('actual archived journal reader required')
    chain=hashlib.sha256()
    for call in movement_calls:
        ref=call['source_reference'];binding=call['binding'];owner=call['owner']
        if ref['template']!=inventory_call['template'] or (owner['PC'],owner['rank'],owner['generation'])!=(control['PC'],control['rank'],control['generation']):
            raise ValueError('executed source template/generation differs from selected call')
        proof=call['proof']
        events=(journal_reader(call['journal_id'],call['journal_start'],call['journal_end']) if journal_reader is not None else journals[call['journal_id']][call['journal_start']:call['journal_end']])
        actual=verify_ds_operand_journal(program,ref['template'],ref,binding,events)
        if actual!=proof or proof['sector32_transactions']!=16 or not proof['matching_reverse_drained']:
            raise ValueError('actual executed source journal span changed')
        chain.update(json.dumps(proof,sort_keys=True,separators=(',',':')).encode())
        for beat in range(8):
            commands.append(dict(kind='shared_write64' if ref['operand']=='dst' else 'shared_read64',
                die=owner['rank'],SM=owner['SM'],generation=owner['generation'],lease=binding['lease'],
                provider_reference='journal:'+str(call['journal_id'])+':'+str(call['journal_start'])+':'+proof['journal_sha256'],
                existing_interval_id=existing_interval_id,group=beat,scratch_byte_address=binding['shared_tile_offset']+beat*64,
                source_operand=dict(code_index=ref['code_index'],operand=ref['operand'],typed_offset=ref['logical_byte_offset']+beat*64,typed_bytes=64),
                actual_journal_span=[call['journal_id'],call['journal_start'],call['journal_end']],
                native_group=owner['tile']//8,**external_bounds))
    if chain.hexdigest()!=control['actual_movement_proof_chain_sha256'] or len(commands)!=control['actual_shared_movements']['scratch64']:
        raise ValueError('complete executed shared movement proof/count mismatch')
    return dict(source_native_sha256=control['source_native_sha256'],source_dispatch_sha256=control['source_dispatch_sha256'],
        calls={inventory_call['call_id']:dict(template=inventory_call['template'],commands=commands)},
        origin='executed64-tile directed software kernel; source/output provider controls, not a released-checkpoint token',
        cost_bound_scope='explicit provisional endpoint-model edges; measured endpoint costs UNKNOWN',
        existing_RF_I64_RMW_C0_provider_charges_added=0,production_calls_closed=0,whole_program_executed=False,hardware_admitted=False)


def project_pc0_provider_journal(packet, phase_schema, calibration):
    """Source-phase event bounds and measured host projections, never admission.

    Original byte totals do not resolve every instruction's sector padding.
    Preserve the producer upper transaction bound and price its ambiguous
    padding as writes for a conservative event upper bound.
    """
    if packet['PC']!=0 or packet['rank_calls']!=96 or packet['sector32_bytes']!=32:
        raise ValueError('actual PC0/96rank/sector32 packet required')
    common=['request_accept','software_owned_issue','software_service_phases_reserved',
            'consumer_accept','reverse_credit_accept','validated_reverse_grant']
    if sorted(phase_schema['read'])!=sorted(common+['software_read_capture']) or sorted(phase_schema['write'])!=sorted(common+['write_residence_reserved','software_backing_visible']):
        raise ValueError('actual provider read/write phase schema mismatch')
    read=(positive(packet['original_staged_read_bytes_per_rank'],'read bytes')+31)//32
    write=(positive(packet['original_staged_write_bytes_per_rank'],'write bytes')+31)//32
    upper=positive(packet['sector_transactions_upper_per_rank'],'producer transaction upper')
    if upper<read+write:raise ValueError('producer sector upper below byte floor')
    padding=upper-read-write;ranks=96
    lower_events=read*len(phase_schema['read'])+write*len(phase_schema['write'])
    upper_events=lower_events+padding*max(map(len,phase_schema.values()))
    events=positive(calibration['total_events'],'measured calibration events')
    seconds=calibration['wall_seconds']
    if not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<=0:raise ValueError('positive measured host runtime required')
    footprint=positive(calibration['journal_sqlite_bytes'],'measured SQLite bytes')
    reserved=positive(calibration['actual_journal_reserved_bytes'],'measured reservation')
    if reserved<footprint:raise ValueError('actual conservative reservation below disk bytes')
    total=upper_events*ranks
    return dict(schema='H4_PC0_96RANK_PHASE_JOURNAL_PROJECTION_V1',PC=0,ranks=ranks,
        sector_transactions_upper_per_rank=upper,sector_transactions_upper_all_ranks=upper*ranks,
        read_sector_byte_floor_per_rank=read,write_sector_byte_floor_per_rank=write,
        unresolved_instruction_padding_sectors_per_rank=padding,
        provider_events_byte_floor_per_rank=lower_events,provider_events_upper_per_rank=upper_events,
        provider_events_upper_all_ranks=total,read_phase_events=phase_schema['read'],write_phase_events=phase_schema['write'],
        projected_sqlite_bytes=math.ceil(total*footprint/events),
        projected_conservative_journal_reservation_bytes=math.ceil(total*reserved/events),
        projected_serial_host_seconds=total*seconds/events,
        projection_scope='measured rank0 publication event density/runtime extrapolated; native arithmetic/checkpoint IO, cache contention and metadata growth additional UNKNOWN',
        exact_full_PC0_event_count=None,physical_disk_guaranteed=False,production_96rank_prefix_completed=False,
        calibration_is_qualification=False,arbitrary_caps_injected=False,
        native_group_staging_bytes=packet['group_staging_bytes_retained'],whole_prefix_latency=None,hardware_admitted=False)


def execute_ds_provider_group128(continuation, PC, rank, *, generation, identity, source_store_view,
                                 shared_factory, primitive_sources, movement_observer=None):
    """Join df6 actual source backing/publication to journalled64KiB shared.

    The original global source-version lease remains live until all64 tiles and
    actual mirrored writer/readback reverse completion. No full LOAD view is
    materialized. This path is also callable by the complete source driver.
    """
    import numpy as np
    origin=Path(continuation.run.__func__.__code__.co_filename)
    if not origin.is_file() or hashlib.sha256(origin.read_bytes()).hexdigest()!='1fbcc6ba439d1b1bc8798aa300d9c5f65c116e638a04d0b66b65b9aede5ae96b':
        raise ValueError('exact df6 provider continuation source required')
    provider=continuation.provider;plan=continuation.plan
    if continuation.failed or (PC,rank,generation) in continuation.completed:raise ValueError('failed or completed provider continuation; no retry')
    if generation!=provider.generation:raise ValueError('provider generation mismatch')
    continuation.bridge._check();parent=plan.parents[PC];writer=parent['writes'][0]
    if (identity.get('PC'),identity.get('rank'),identity.get('generation'),identity.get('version'))!=(PC,rank,generation,writer['version']) or source_store_view!=writer['native_result_binding']:
        raise ValueError('exact source writer identity/result binding required')
    if not identity.get('home_indices') or provider._leased(writer['version']) or any(k[:3]==(PC,rank,generation) for k in provider.views):
        raise ValueError('concrete unleased writer and unique live operation required')
    source_version=parent['provider_bindings'][parent['new_template']]['parts']['version']
    lease={'parts':dict(version=source_version,leased_versions=[source_version],source_ranks=list(range(64)),provenance_certified=False,data=None)}
    provider.views[PC,rank,generation,id(lease)]=lease
    source_receipts=[];publication=None;result_journal=None;released=0;pending_tiles=set();output=np.empty(8192,np.float32)
    class Source:
        def acquire(self,span,owner):
            if not provider._leased(source_version):raise ValueError('actual global source lease lost')
            loc=provider.locations.get((source_version,span['source_rank']))
            if loc is None or list(loc['shape'])!=[1024] or np.dtype(loc['dtype'])!=np.dtype('float32'):
                raise ValueError('actual retained1024 F32 source backing required')
            first=span['local_word_first'];words,loc,receipt=continuation.bridge._read_words(source_version,span['source_rank'],np.arange(first,first+128))
            tile=plan.tile(PC,rank,owner['tile']//8,(owner['tile']%8)*128)
            receipt=dict(receipt);receipt['source_operand_proof']=continuation.receive(tile,span,loc,receipt,f'group:{PC}:{rank}:{generation}:{source_version}')
            source_receipts.append(receipt);raw=words.tobytes()
            return dict(version=source_version,rank=span['source_rank'],generation=generation,first=first,words=128,
                lease=(owner['tile'],span['source_rank']),state='visible',data=raw,payload_sha256=hashlib.sha256(raw).hexdigest())
        def release(self,record,owner):
            nonlocal released
            # Logical tile consumption can finish early; the parent version
            # lease must NOT release before the final real writer ACK/reverse.
            released+=1
            if released==512:
                if publication is None or len(pending_tiles)!=64:raise ValueError('source release before complete publication')
                provider.release_views(PC,rank,generation,lease)
    class Output:
        def write_span(self,tile,owner,raw):
            nonlocal publication,result_journal
            ordinal=tile['tile_ordinal'];first=tile['output_flat_word_first']
            if ordinal in pending_tiles or ordinal!=len(pending_tiles):raise ValueError('output tile duplicate/out of source order')
            output[first:first+128]=np.frombuffer(raw,np.float32);pending_tiles.add(ordinal)
            if len(pending_tiles)==64:
                engine=provider.rf.get(rank);start=len(engine.events) if engine is not None else 0
                publication=provider.publish(identity,{'data':output},source_store_view)
                engine=provider.rf[rank];end=len(engine.events)
                prove=continuation.run.__func__.__globals__['prove_sector_span']
                transactions=prove(engine.events[start:end],model='DeepSeek',rank=rank,PC=PC,generation=generation)
                if not any(t['direction']=='write' for t in transactions) or any((engine.live,engine.queue,engine.calendar,engine.resident)):
                    raise ValueError('actual writer/readback reverse debt retained')
                if publication.get('identity')!=identity or publication.get('pending_obligations')!=0 or publication['payload_sha256']['data']!=hashlib.sha256(output.tobytes()).hexdigest():
                    raise ValueError('actual provider publication owner/payload/debt mismatch')
                if [e['event'] for e in publication['events']]!=['software_backing_visible','consumer_accept','validated_reverse_grant']:
                    raise ValueError('actual provider publication visibility/consumer/reverse order')
                written={t['identity']['sector'] for t in transactions if t['direction']=='write'};required=set()
                for i in identity['home_indices']:
                    home=provider.homes[i]
                    if home['version']!=writer['version'] or rank not in home['rank_group'] or home['home']['class']!='RF':raise ValueError('actual mirrored writer home identity')
                    for copy in range(2):
                        base=(home['SM']*2+copy)*262144+home['home']['slot_first']*512
                        required.update(range(base//32,(base+home['word_count']*4+31)//32))
                if not required or not required<=written:raise ValueError('actual both-mirror backing visibility/reverse incomplete')
                result_journal=dict(journal_id=engine.events.id,start=start,end=end,sector_transactions=len(transactions),
                    actual_RF_mirrors=2,required_write_sectors=len(required),all_required_mirror_sectors_reverse_drained=True)
            return dict(version=writer['version'],rank=rank,generation=generation,first=first,bytes=512,
                payload_sha256=hashlib.sha256(raw).hexdigest(),pending_obligations=0,
                state='actual_published' if publication is not None else 'unpublished_charged_staging')
    try:
        result=execute_ds_group128_tiles(plan,PC,rank,generation,Source(),shared_factory,primitive_sources,Output(),movement_observer=movement_observer)
        if provider._leased(source_version) or released!=512 or publication is None:raise ValueError('actual group global view not retired')
        continuation.completed.add((PC,rank,generation))
        result.update(actual_source_receipts=source_receipts,actual_publication=publication,actual_result_journal=result_journal,
            source_global_view_released=True,source_version_retired=False,
            unpublished_output_staging_bytes=32768,total_operand_and_staging_bound_bytes=41472,
            actual_RF_mirror_journal=result_journal,actual_provider_writer=True,production_payload_provenance='caller-retained producer backing; qualification belongs to full driver/input receipts',
            production_calls_closed=0)
        return result
    except Exception:
        continuation.failed=True
        raise


def execute_ds_driver_with_group128(driver, continuation, *, shared_factory, primitive_sources, observer=None):
    """Full source-PC dispatch with current group continuation; opt-in only.

    All other families execute the existing driver run_buffer/kernel machinery.
    A missing binding faults with completed-PC and live provider evidence intact;
    this does not skip arithmetic or turn an absent producer into a successful PC.
    """
    source=Path(driver.run_buffer.__func__.__code__.co_filename)
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!='3cbfc171ab3ff28439637a4ac4e3adb7bd332d87e015e03a7dabfc2d0d1443e0':
        raise ValueError('exact retained full native driver required; no family callback')
    if continuation.provider is not driver.provider:raise ValueError('driver/continuation actual provider differs')
    if len(driver.native['instructions'])!=2213 or driver.native is not continuation.provider.native or driver.generation!=continuation.provider.generation:
        raise ValueError('complete current2213PC/provider native object and generation required')
    if driver.retired:raise ValueError('fresh full driver required; no replay over live partial state')
    calls=[]
    for op in driver.native['instructions']:
        if not set(op['dependencies'])<=driver.retired:raise ValueError('source dependency not retired')
        views=None
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            rank=owned['rank']
            if op['family']=='all_reduce':
                write=op['writes'][0]
                indices=[i for i in write['home_indices'] if rank in driver.homes[i]['rank_group']]
                identity=dict(PC=op['pc'],version=write['version'],rank=rank,generation=driver.generation,home_indices=indices)
                record=execute_ds_provider_group128(continuation,op['pc'],rank,generation=driver.generation,identity=identity,
                    source_store_view=write['native_result_binding'],shared_factory=shared_factory,primitive_sources=primitive_sources,movement_observer=observer)
                if observer is not None:observer(dict(event='actual_group_call_completed',PC=op['pc'],rank=rank,record=record))
                calls.append(dict(PC=op['pc'],rank=rank,output_sha256=record['output_sha256']))
            else:
                views=driver.provider.read_views(op,owned,driver.generation)
                if owned.get('buffer_programs'):
                    if set(views)!={b['write_version'] for b in owned['buffer_programs']}:raise ValueError('exact independent collective buffer view set')
                    for buffer in owned['buffer_programs']:
                        bindings={name:dict(value) for name,value in op['provider_bindings'][buffer['template']].items()}
                        for name,required in bindings.items():
                            if name=='parts':required.update(version=buffer['read_version'],additional_versions=[buffer['read_version']])
                            elif required['kind']=='explicit_auxiliary_provider':required['identity_from_versions']=[buffer['read_version']]
                        driver.run_buffer(op,owned,buffer['template'],bindings,views[buffer['write_version']],[w for w in op['writes'] if w['version']==buffer['write_version']])
                else:driver.run_buffer(op,owned,owned['template'],op['provider_bindings'][owned['template']],views,op['writes'])
        retired=driver.provider.retire_operation(op['pc'],driver.generation)
        if retired!=dict(PC=op['pc'],generation=driver.generation,pending_obligations=0,source_consumers_released=True):raise ValueError('actual source operation retirement debt')
        driver.retired.add(op['pc'])
        for read in op['reads']:
            if driver.last_use[read['version']]==op['pc']:driver.provider.release_version(read['version'],driver.generation)
    drained=driver.provider.drain(driver.generation)
    if drained!=dict(generation=driver.generation,pending_obligations=0,live_consumers=0):raise ValueError('full driver terminal debt')
    return dict(schema='H4_DS_FULL_DRIVER_GROUP128_DISPATCH_V1',PCs_retired=len(driver.retired),actual_group_calls=calls,
        status='FULL_NATIVE_DRIVER_SOFTWARE_COMPLETED',full_program_executed=True,group_movement_observer_present=observer is not None,hardware_admitted=False,whole_token_latency=None)


def reprice_h4_intervals(execution, *, costs=None):
    """Recompose retained execution, without arithmetic/provider rerun or r22.

    Producer128B shared transfers each require two actual64B transactions.
    C0 is an explicit provisional software service demand, never an RTL bridge.
    """
    costs = dict(costs or {'scratch64_transaction':8, 'C0_fetch':2,
        'C0_decode':2, 'C0_home_scoreboard':12, 'C0_accept':2,
        'C0_complete':2, 'C0_reverse_retire':2})
    required = {'scratch64_transaction','C0_fetch','C0_decode','C0_home_scoreboard',
                'C0_accept','C0_complete','C0_reverse_retire'}
    if set(costs) != required: raise ValueError('complete H4 cost table required')
    for key,value in costs.items(): positive(value,key)
    old_costs = execution['explicit_provisional_latency']
    rows=[]; shift=0; total_shared=total_commands=0
    for row in execution['ordered_PC_intervals']:
        units=row['cost_units']; commands=units['native_batch']
        if type(commands) is not int or commands<0: raise ValueError('native command repetitions')
        old_shared=units['shared_beat128']; shared64=2*old_shared
        if type(old_shared) is not int or old_shared<0: raise ValueError('shared repetitions')
        before=row['provider_service_ticks']+sum(units[k]*old_costs[k] for k in old_costs)
        if row['end']-row['start'] != before: raise ValueError('retained interval cost mismatch')
        if not row['all_provider_grants_before_PC_retire']: raise ValueError('unretired provider ownership')
        extra_shared=shared64*costs['scratch64_transaction']-old_shared*old_costs['shared_beat128']
        dispatch=commands*sum(v for k,v in costs.items() if k!='scratch64_transaction')
        changed=dict(row);changed.update(start=row['start']+shift,
            end=row['end']+shift+extra_shared+dispatch,
            scratch64_transactions=shared64, C0_command_repetitions=commands,
            C0_service_ticks=dispatch, scratch_reprice_delta=extra_shared,
            RF_service_credit='existing serialized provider/ACK charge retained once',
            native_RTL_bridge=False)
        rows.append(changed);shift+=extra_shared+dispatch
        total_shared+=shared64;total_commands+=commands
    return {'schema':'H4_REPRICED_RETAINED_SOFTWARE_INTERVALS_V1',
        'ordered_PC_intervals':rows, 'software_ticks':execution['ordered_PC_ticks']+shift,
        'baseline_software_ticks':execution['ordered_PC_ticks'], 'delta_software_ticks':shift,
        'scratch64_transactions':total_shared,'C0_commands':total_commands,
        'explicit_provisional_costs':costs,'hardware_clock_admission':False,
        'arithmetic_or_provider_rerun':False,'r22_augmentation_applied':False,
        'qualification':'CPU/native execution retained as software evidence only; all51 H1 family bridges absent',
        'traffic_scope':'existing reduced36layer fixtures; not fullshape checkpoint execution'}


class C0VersionScoreboard:
    """Finite software C0 ABI control; Sagan owns its actual command bridge.

    Immutable identity includes rank/SM/version/generation. Complete, visible,
    consumer accept, reverse grant and retirement are distinct transitions.
    One RF transaction credit stays held from accept through mirrored ACK.
    """
    def __init__(self, entries=512):
        self.capacity=positive(entries,'scoreboard entries');self.live={};self.commands={}
        self.last_generation={};self.RF_owner={}

    def publish(self, identity, home, *, visible=True, future_readers=()):
        if len(identity)!=4: raise ValueError('rank SM version generation identity')
        rank,sm,version,generation=identity
        if type(rank)!=int or rank<0 or type(sm)!=int or not 0<=sm<32 or not version:
            raise ValueError('rank SM version identity')
        positive(generation,'version generation')
        if len(home)!=3 or home[0] not in ('RF','scratch','HBM'):
            raise ValueError('concrete storage base extent required')
        kind,base,size=home;positive(size,'home bytes')
        if type(base)!=int or base<0: raise ValueError('concrete home base required')
        cap={'RF':262144,'scratch':65536,'HBM':1<<27}[kind]
        if base+size>cap: raise ValueError('home physical extent')
        if len(self.live)>=self.capacity: raise ValueError('finite scoreboard exhausted')
        if identity in self.live: raise ValueError('duplicate version identity')
        key=(rank,None if kind=='HBM' else sm,kind,base)
        if generation<=self.last_generation.get(key,0): raise ValueError('stale home generation')
        for ident,e in self.live.items():
            k,b,n=e['home']
            same_scope=ident[0]==rank and (kind=='HBM' or ident[1]==sm)
            if same_scope and k==kind and base<b+n and b<base+size:
                raise ValueError('premature write reuse live home alias')
        self.live[identity]={'home':home,'visible':visible,'readers':set(),
                             'future_readers':set(future_readers),'producer':None}
        self.last_generation[key]=generation

    def accept(self, command, sources, destination):
        if command in self.commands: raise ValueError('duplicate command')
        identities=list(sources)+[destination]
        if any(i not in self.live for i in identities): raise ValueError('unbound version/home')
        owner=destination[:2]
        if any(i[:2]!=owner for i in identities): raise ValueError('cross SM requires priced provider route')
        if owner in self.RF_owner: raise ValueError('RF transaction credit exhausted through ACK')
        if any(not self.live[i]['visible'] for i in sources): raise ValueError('premature read visibility')
        if self.live[destination]['visible'] or self.live[destination]['producer'] is not None:
            raise ValueError('destination already produced')
        self.RF_owner[owner]=command;self.live[destination]['producer']=command
        for i in sources:self.live[i]['readers'].add(command)
        self.commands[command]={'sources':list(sources),'destination':destination,'phase':'accepted'}

    def transition(self, command, phase):
        c=self.commands[command];expected={'accepted':'complete','complete':'mirrored_visible_ACK',
            'mirrored_visible_ACK':'consumer_accept','consumer_accept':'reverse_grant','reverse_grant':'retire'}
        if expected.get(c['phase'])!=phase: raise ValueError('C0 transition order')
        c['phase']=phase
        if phase=='mirrored_visible_ACK':
            self.live[c['destination']]['visible']=True;del self.RF_owner[c['destination'][:2]]
        if phase=='retire':
            for i in set(c['sources']):
                self.live[i]['readers'].remove(command);self.live[i]['future_readers'].discard(command)
            self.live[c['destination']]['producer']=None;del self.commands[command]

    def release(self, identity):
        e=self.live[identity]
        if e['readers'] or e['future_readers'] or e['producer'] is not None:
            raise ValueError('retained lease before reverse retirement or declared future consumer')
        del self.live[identity]


def reprice_h4_native_stages(calendar, program, costs):
    """Add ordered C0 service to the proved native trace, with no new payload run."""
    original_proof=verify_ssa_finite_sm_services(calendar,program)
    keys=['C0_fetch','C0_decode','C0_home_scoreboard','C0_accept','C0_complete','C0_reverse_retire']
    dispatch=[(k,positive(costs[k],k)) for k in keys]
    rows=[];now=0;delta=0
    for old in calendar['stages']:
        phases=[];cursor=0
        for key,value in dispatch[:4]:
            phases.append({'phase':key,'units':1,'start':cursor,'end':cursor+value,
                           'provisional_service_ticks':value})
            cursor+=value
        prefix=cursor
        for phase in old['phases']:
            if phase is old['phases'][-1]:
                for key,value in dispatch[4:]:
                    phases.append({'phase':key,'units':1,'start':phase['start']+cursor,
                        'end':phase['start']+cursor+value,'provisional_service_ticks':value})
                    cursor+=value
            p=dict(phase);p['start']+=cursor;p['end']+=cursor;phases.append(p)
        stride=old['batch_stride']+cursor
        row=dict(old);row.update(start=now,end=now+stride*old['repetitions'],batch_stride=stride,
            phases=phases,C0_command_repetitions=old['repetitions'],native_RTL_bridge=False,
            C0_RF_credit_scope='accept through existing two-mirror visible ACK; conservative batch ownership retained',
            C0_issue_prefix_ticks=prefix)
        now=row['end'];rows.append(row);delta+=cursor*old['repetitions']
    if now!=calendar['software_ticks']+delta:raise ValueError('C0 ordered stage composition')
    return {'schema':'H4_C0_REPRICED_ORDERED_DS_STAGE_SERVICES_V1','stages':rows,
        'software_ticks':now,'baseline_software_ticks':calendar['software_ticks'],
        'C0_added_software_ticks':delta,'C0_commands':sum(r['repetitions'] for r in rows),
        'baseline_native_port_and_lifetime_proof':original_proof,'workspace':calendar['workspace'],
        'workspace_peak_bytes':calendar['workspace_peak_bytes'],
        'constrained_extent_successor_demand':calendar['constrained_extent_successor_demand'],
        'scope':'PC127 rank0 native source-ordered conservative services only; no all2213 payload run',
        'scratch64_transaction_count':None,
        'scratch_count_unknown_reason':'DS relative32MiB workspace is not H1 local64KiB scratch; actual shared movement bridge not bound',
        'payload_executed':False,'hardware_clock_admission':False,
        'physical_workspace_admission':False,'r22_augmentation_applied':False}


def compose_h4_uarch(model_source, parameters, inventory):
    """Source-pinned unified model algorithms with actual H1 configurations.

    Pure unit-sum model excludes opportunistic physical record substitution.
    No executable opcode implementation is inferred from modeled area/rate.
    """
    names={'sm_area','sm_op_cycles','mma_drain_cycles'}
    parsed=ast.parse(model_source);selected=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in selected}!=names: raise ValueError('unified model functions missing')
    namespace=dict(parameters,math=math,gpu_hardened_columns=lambda:{})
    exec(compile(ast.Module(body=selected,type_ignores=[]),'pinned_unified_model','exec'),namespace)
    result={}
    for target,key,ranks in [('Qwen','qwen',2),('DeepSeek','v41',96)]:
        old=dict(inventory['unified_model']['SM_ELEM'][key]);actual=dict(old)
        config=inventory['bindings']['Qwen_matrix' if key=='qwen' else 'DS_matrix']['config']
        actual['stack_levels']=config['LEV'];actual['group_slot']=False
        area=namespace['sm_area'](actual,64);rf_macros=4*16*2
        rf_area=rf_macros*parameters['SRAM_128X256_UM2']*parameters['GPU_MACRO_PACK']/1e6
        # ASSUMED finite C0 implementation:512 entries of200 bits and512bit command.
        control_bits=512*200+512; mux_bits=512*31
        control_area=(control_bits*parameters['DFF_UM2']+mux_bits*.2)/parameters['GPU_LOGIC_UTIL']/1e6
        per_sm=area['total_mm2']+rf_area+control_area
        result[target]={'actual_H1_config':config,'previous_model_element':old,'reconciled_model_element':actual,
            'ranks':ranks,'SMs_per_rank':32,'total_SM_replicas':ranks*32,
            'clock_policy':{'streaming_target_Hz':1200000000,'serial_chain_target_Hz':900000000,
                'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'SS_FF_qualification':False,
                'software_tick_to_hardware_clock_conversion':None},
            'RF':{'logical_bytes_per_SM':262144,'physical_mirrored_bytes_per_SM':524288,
                'logical_bytes_per_rank':8388608,'physical_bytes_per_rank':16777216,
                'logical_vectors':512,'workspace_reserved_vectors':32,'retained_source_vectors':480,
                'read_ports':2,'write_ports':1,'physical_write_copies':2,
                'transaction_credit':1,'credit_held_until':'mirrored_visible_ACK',
                'macros_per_SM':rf_macros,'footprint_mm2_per_SM':rf_area},
            'ports_bytes_per_accepted_transaction':{'RF_read_A':512,'RF_read_B':512,
                'RF_write_A':512,'RF_write_B':512,'scratch':64,'matrix_ingest':128},
            'boundary_bits_per_transaction':{'RF_operands':8192,'RF_mirrored_write':8192,
                'scratch':512,'matrix_ingest':1024,'C0_command':512},
            'port_peak_Bpc_is_not_achieved_rate':True,
            'finite_credits_per_SM':{'C0_command':1,'RF_transaction':1,'scratch_transaction':1,
                'scoreboard_entries':512,'provider_tag':1,'reverse_grant':1},
            'compute':{'matrix_macs_per_issue_clk':2048 if key=='qwen' else 512,
                'mode_rates_macs_per_issue_clk':{'INT8':2048} if key=='qwen' else {'BF16':512,'FP8':1024,'FP4':2048},
                'mode_rate_basis':'lane/column analytical peak, mutually exclusive formats; H1 DS exercises BF16 only',
                'unified_area_helper_sum_of_mode_lanes_not_an_issue_rate':area['macs_per_clk'],
                'native_hardware_bound_families':0,
                'actual_H1_opcode_exercised':['FADD'],'general_native_issue_rate':'UNKNOWN_POSITIVE_PROVISIONAL_REQUIRED',
                'communication_intensity_H1_macs_per_ingest_byte':(2048 if key=='qwen' else 512)/128},
            'area':{'matrix_and_SIMT_unit_sum':area,'RF_added_mm2_per_SM':rf_area,
                'C0_ASSUMED_mm2_per_SM':control_area,'modeled_lower_mm2_per_SM':per_sm,
                'modeled_lower_mm2_per_rank':32*per_sm,
                'excluded':'unimplemented generic SFU/reduction/movement/collective units; measured slot-fit UNKNOWN'},
            'routing':{'local_payload_tracks_lower':8192+8192+512+1024+512,
                'replicas':32,'command_mux_2to1_bit_equivalents':mux_bits,'command_demux_destinations':32,
                'broadcast_fanout':32,'channel_capacity_tracks':None,'slot_fit':None,
                'admission':'BLOCKED until actual floorplan channel/escape and complete endpoint areas'},
            'formula_drain_cycles_before':namespace['mma_drain_cycles'](old),
            'formula_drain_cycles_actual_config':namespace['mma_drain_cycles'](actual),
            'matvec_issue_comparison':[{'rows_per_rank':rows,'K':5120,'format':'fp8',
                'previous_group_slot_cycles':namespace['sm_op_cycles'](rows,5120,'fp8',1,True),
                'actual_row_slot_cycles':namespace['sm_op_cycles'](rows,5120,'fp8',1,False)}
                for rows in (32,64,256)] if key=='v41' else [],
            'hardware_admission':False}
    return {'schema':'H4_SOURCE_PINNED_ACTUAL_CONFIG_UNIFIED_COMPOSITION_V1','designs':result,
        'status':'MODELED_SOFTWARE_SERVICE_DEMAND_HARDWARE_UNQUALIFIED',
        'area_basis':'unified sm_area pure unit-sum; RF macro footprints + explicitly assumed C0 DFF/mux; lower bound',
        'measured_costs':'UNKNOWN; positive provisional calendar separate',
        'C0_bridge_owner':'Sagan','composed_model_owner':'Dewey'}


def verify_portable_producer(path, native):
    """Validate archived producer bytes without consulting another checkout."""
    pin_path = path.parent / 'producer_pins.json'
    if not pin_path.exists():
        return {}
    pins = read_json(pin_path)
    if pins.get('schema') != 'H3_PORTABLE_PRODUCER_PINS_V1':
        return {}  # Retained historical snapshot receipt, not this closure ABI.
    sources = {}; producer = {}
    for relative, pin in pins['files'].items():
        archived = (path.parent / relative).resolve()
        if not archived.is_relative_to(path.parent.resolve()):
            raise ValueError('producer archive path escape')
        raw = archived.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
        if digest != pin['sha256']:
            raise ValueError('portable producer source pin mismatch: ' + relative)
        sources[str(archived)] = digest; producer[pin['path']] = digest
    if str(path.resolve()) not in sources:
        raise ValueError('portable producer lacks native input pin')
    for name, digest in native.get('source_sha256', {}).items():
        if producer.get(name) != digest:
            raise ValueError('portable producer source closure incomplete: ' + name)
    return sources


def split_i64_words(value):
    """Software R20 codec: preserve signed source bits in two LE words."""
    import numpy as np
    bits = np.asarray(value, dtype=np.int64).view(np.uint64)
    return (bits & np.uint64(0xffffffff)).astype('<u4'), (bits >> np.uint64(32)).astype('<u4')


def join_i64_words(low, high, low_identity, high_identity):
    import numpy as np
    if low_identity != high_identity or not low_identity:
        raise ValueError('I64 codec owner/definition/iteration mismatch')
    low = np.asarray(low, dtype='<u4'); high = np.asarray(high, dtype='<u4')
    if low.shape != high.shape:
        raise ValueError('I64 codec missing highword extent')
    return (low.astype(np.uint64) | (high.astype(np.uint64) << np.uint64(32))).view(np.int64)


def load_workspace_provider(path, native_sha256):
    join = read_json(path)
    if join['source_native_sha256'] != native_sha256:
        raise ValueError('workspace final native source mismatch')
    homes_path = path.parent / 'temporary_provider_homes.json.gz'
    if hashlib.sha256(homes_path.read_bytes()).hexdigest() != join['temporary_provider_homes_sha256']:
        raise ValueError('workspace home pin mismatch')
    homes = read_json(homes_path); index = {}
    for home in homes:
        key = home['pc'], home['rank'], home['symbol']
        if key in index:
            raise ValueError('duplicate workspace home')
        index[key] = home
    return {'join': join, 'homes': index, 'input_path': str(path),
            'sources': verify_portable_producer(path, {})}


def load_pinned_module(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('executable provider source pin mismatch')
    name = 'h3_provider_' + digest[:16]
    module = types.ModuleType(name); module.__file__ = str(path)
    sys.modules[name] = module
    old = list(sys.path)
    try:
        sys.path.insert(0, str(ROOT / 'tools'))
        exec(compile(raw, str(path), 'exec'), module.__dict__)
    finally:
        sys.path[:] = old
    if hasattr(module, 'ROOT'):
        module.ROOT = ROOT
    return module


def audit_bounded_export(native, graph):
    """Count/binding audit of executable tile IR, not a fabricated macro trace."""
    if native['schema'] != 'opentallas.H3.qwen-bounded-tiled-native.v1':
        raise ValueError('bounded native schema required')
    if native['feasibility']['temporary_HBM_bytes'] != 0:
        raise ValueError('bounded native unexpectedly materializes HBM temporaries')
    provider=native['provider_binding']
    homes,reuse,releases,provider_ops=bind_provider_homes(provider,graph,{})
    check_homes(homes,graph)
    references={h['provider_ref']:h for h in provider['version_homes']}
    for operand in native['operands']:
        for h in operand['homes']:
            if 'home' in h and (h.get('provider_ref') not in references or h!=references[h['provider_ref']]):
                raise ValueError('bounded retained concrete home mismatch')
    abi = native['tile_kernel_ABI']; rows = []; totals = Counter()
    for name, kernel in abi.items():
        observed = Counter()
        for step in kernel['steps']:
            observed.update(step['native_steps'])
            if math.prod(step['write']['shape_max']) > 128 or step['write']['RF_vectors_max'] > 32:
                raise ValueError('bounded kernel RF/tile overcapacity')
            if not step['round_point']:
                raise ValueError('bounded arithmetic contract missing')
        if dict(observed) != kernel['native_counts_per_invocation']:
            raise ValueError('bounded kernel primitive count mismatch ' + name)
    if len(native['operations']) != len(graph['operations']):
        raise ValueError('bounded PC coverage mismatch')
    for op, source in zip(native['operations'], graph['operations']):
        if any(op[k] != source[k] for k in ('pc', 'opcode', 'reads', 'writes', 'dependencies')):
            raise ValueError('bounded source PC/version/dependency mismatch')
        export = op['calendar_export']; physical = export['physical_primitives']; counts = Counter()
        for name, repetitions in physical['kernel_invocations'].items():
            positive(repetitions, 'bounded kernel repetition')
            counts.update({k: v * repetitions for k, v in abi[name]['native_counts_per_invocation'].items()})
        if dict(counts) != physical['native_primitive_commands']:
            raise ValueError('bounded all-PC primitive count mismatch')
        if export['RF_workspace_vectors'] > 32 or export['shared_reserved_bytes'] > 65536 or export['temporary_HBM_bytes'] != 0:
            raise ValueError('bounded workspace capacity exhausted')
        totals.update(counts)
        rows.append({'pc': op['pc'], 'opcode': op['opcode'], 'primitive_commands': dict(counts),
            'kernel_invocations': physical['kernel_invocations'], 'providers': op['provider_binding']})
    return {'status': 'PASS_BOUNDED_ALL_PC_SOURCE_BINDINGS_AND_PRIMITIVE_COUNTS', 'PCs': len(rows),
        'classes': len({r['opcode'] for r in rows}), 'PCs_detail': rows, 'primitive_commands': dict(totals),
        'workspace': native['feasibility'], 'fullshape_ordered_runtime_trace_executed': False,
        'retained_source_home_proof':{'status':'PASS_CONCRETE_HOME_APERTURE_LIFETIME_AND_REUSE',
            'data_homes':len(provider['version_homes']),'control_homes':len(provider['control_homes']),
            'versions':len(native['operands']),'reuse_home_count':len(reuse),
            'RF_workspace_slots':list(range(32)),'RF_source_slots':'32..511, disjoint from native workspace'},
        'fullshape_companion_scope': 'conservative service reservation, not actual ordered instruction trace',
        'physical_or_clock_admission': False}


def load_bounded_provider_sources(directory):
    """Load the committed portable closure, including compiler imports."""
    base = Path(directory); pins = read_json(base / 'producer_pins.json')['files']
    for name, pin in pins.items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('bounded producer closure pin mismatch ' + name)
    for name in ('qwen_hbm_complete_program', 'h3_versioned_lowering', 'h3_distributed_norm_endpoint'):
        path = 'sources/tools/' + name + '.py'
        sys.modules[name] = load_pinned_module(base / path, pins[path]['sha256'])
    if 'bounded_entrypoint.py.source' not in pins or 'baseline.py.source' not in pins:
        raise ValueError('separate bounded entrypoint with preserved baseline required')
    sys.modules['h3_qwen_complete_native']=load_pinned_module(base/'baseline.py.source',pins['baseline.py.source']['sha256'])
    return (load_pinned_module(base / 'bounded_entrypoint.py.source', pins['bounded_entrypoint.py.source']['sha256']),
            load_pinned_module(base / 'provider.py.source', pins['provider.py.source']['sha256']))


def audit_ds_bounded_dispatch(dispatch, *, costs=None):
    """Finite conservative service reservations, with physical inadmission.

    This is deliberately an intermediate reservation of the pinned forward
    instruction executor, not an invented opcode-sorted native timeline.
    Every rank holds its32 SM services; execution is serialized within a rank
    and across PCs, so no bandwidth/parallel speedup is assumed. All costs are
    positive estimates. Actual workspace addresses and checkpoint descriptors
    remain required for addressed whole-program execution.
    """
    if dispatch['schema']!='H3_DS_FORWARD_BOUNDED_POLYNOMIAL_DISPATCH_V2':
        raise ValueError('DS bounded forward schema required')
    if dispatch['automatic_scalar_fallback_templates']!=0: raise ValueError('DS recursive fallback rejected')
    costs=dict(costs or {'primitive_scalar':32,'fragment512_read':16*108,'fragment512_write':16*128,
        'route512':64,'admit':2,'retire':2,'visibility_fence':4,'collective_rendezvous':2})
    required={'primitive_scalar','fragment512_read','fragment512_write','route512','admit','retire',
              'visibility_fence','collective_rendezvous'}
    if set(costs)!=required: raise ValueError('complete DS cost table required')
    for key,value in costs.items(): positive(value,key)
    cap=dispatch['workspace']['rank_cap_bytes']; templates=dispatch['templates']; count=Counter(); rows=[]
    demands={}; done=set(); tick=0; successor=[]
    for key,t in templates.items():
        p=t['plan']
        if t['reference_scalar_fallback_admitted'] or not t['no_recomputed_dependency_scalars']:
            raise ValueError('DS recursive fallback rejected')
        demand=p.get('workspace_upper_bytes',p.get('typed_live_workspace_upper_bytes_per_SM',0))
        if t['execution_path'].startswith('forward_'):
            demand+=p.get('quantized_input_provider_bytes_per_rank',p.get('retained_query_bytes',0))
        if demand<=0 or demand>cap: raise ValueError('DS finite workspace exhausted '+key)
        demands[key]=demand
    for op in dispatch['PC_dispatch']:
        if op['pc']!=len(rows) or not set(op['dependencies'])<=done: raise ValueError('DS bounded dependency deadlock')
        totals=Counter(); transfers=Counter(); ranks=defaultdict(lambda:{'work':Counter(),'read':0,'write':0,'templates':[]})
        for call in op['calls']:
            rank=call['rank']; key=call['template']; t=templates[key]
            if not 0<=rank<96 or 'block256%32' not in call['SM_partition']: raise ValueError('DS concrete32SM source binding required')
            totals.update(t['executed_primitive_scalar_projection'])
            transfer=t['provider_transfer_projection']
            transfers.update({k:v for k,v in transfer.items() if type(v) is int})
            ranks[rank]['work'].update(t['executed_primitive_scalar_projection'])
            ranks[rank]['read']+=transfer['read_512B_fragments_upper']
            ranks[rank]['write']+=transfer['write_512B_fragments_upper']
            ranks[rank]['templates'].append(key)
        if dict(totals)!=op['projected_executed_primitive_scalars'] or dict(transfers)!=op['provider_transfer_projection']:
            raise ValueError('DS all-PC primitive/transport count mismatch')
        rank_rows=[]
        for rank,record in sorted(ranks.items()):
            units={'primitive_scalar':sum(record['work'].values()),'fragment512_read':record['read'],
                'fragment512_write':record['write'],'route512':record['read']+record['write'],
                'admit':len(record['templates']),'retire':len(record['templates']),
                'visibility_fence':len(record['templates']),'collective_rendezvous':int(op['family']=='all_gather')}
            duration=sum(units[k]*costs[k] for k in costs)
            rank_rows.append({'rank':rank,'start':tick,'end':tick+duration,
                'cost_units':units,'workspace_peak_upper':max(demands[k] for k in record['templates']),
                'resources':{'SM_issue_leases_each_of_32':1,'source_fragment_credit':1,'write_residence':1,
                    'RF_vectors_per_SM':32,'rank_workspace_bytes':cap},'ordered_executor_templates':record['templates']})
        if not rank_rows: raise ValueError('DS PC has no admitted services')
        end=max(r['end'] for r in rank_rows)
        rows.append({'pc':op['pc'],'family':op['family'],'start':tick,'end':end,'dependencies':op['dependencies'],
            'ranks':rank_rows,'atomic_collective_participants':sorted(ranks) if op['family']=='all_gather' else [],
            'global_collective_credit':int(op['family']=='all_gather'),'writes_visible_before_retire':True,
            'scope':'conservative finite reservation; actual instruction order remains pinned forward executor'})
        count.update(totals); tick=end; done.add(op['pc'])
    for rank in range(96):
        successor.append({'rank':rank,'requested_bytes':cap,'alignment_bytes':512,'address_bits':27,
            'maximum_base_inclusive':(1<<27)-cap,'physical_base':dispatch['workspace']['base'],
            'must_be_disjoint_from':'all retained source homes, immutable checkpoint, persistent provider and every live lease',
            'release_guard':'accepted fragment return, consumer capture, matched reverse grant, source last use',
            'status':'UNBOUND_PHYSICAL_BASE_AND_PROVIDER_LEASE'})
    return {'status':'PASS_ALL_PC_BOUNDED_FINITE_SERVICE_RESERVATION_INTERMEDIATE','PCs':len(rows),
        'families':len({r['family'] for r in rows}),'primitive_scalars':dict(count),'estimated_service_ticks':tick,
        'explicit_provisional_costs':costs,'source_program_sha256':dispatch['source_program_sha256'],
        'PC_intervals':rows,'constrained_extent_successor_demand':successor,
        'ordered_full_native_trace':False,'full_token_numerical_execution':False,
        'checkpoint_scope':'producer fragment projection excludes physical checkpoint fetch; concrete provider range/route binding is required',
        'physical_admission':False,'clock_admission':False,'automatic_scalar_fallback':False}


def compose_ds_full_program_services(dispatch, *, bridge=None, native_program=None, leaf_catalog=None, costs=None):
    """All-PC finite service composition using retained producer projections.

    One dispatch per primitive scalar is an explicit conservative command upper,
    not an invented vector speedup. Bridge64B scratch demand is additive only
    when a pinned movement trace actually binds that template; absent is UNKNOWN.
    No numerical executor/provider payload or r22 augmentation runs here.
    """
    baseline=audit_ds_bounded_dispatch(dispatch)
    costs=dict(costs or {'C0_fetch':2,'C0_decode':2,'C0_home_scoreboard':12,
        'C0_accept':2,'C0_complete':2,'C0_reverse_retire':2,'scratch64_read':8,'scratch64_write_ACK':8,
        'atomic_collective_admit':2})
    required={'C0_fetch','C0_decode','C0_home_scoreboard','C0_accept','C0_complete',
              'C0_reverse_retire','scratch64_read','scratch64_write_ACK','atomic_collective_admit'}
    if set(costs)!=required:raise ValueError('complete all-PC service cost table required')
    for key,value in costs.items():positive(value,key)
    bridge_templates={}
    if bridge is not None:
        if native_program is None:raise ValueError('retained native code required for shared bridge validation')
        if bridge.get('schema')!='H4_DS_NATIVE_SHARED_MOVEMENT_BRIDGE_V1':raise ValueError('actual shared movement bridge schema')
        if bridge.get('source_program_sha256')!=dispatch['source_program_sha256']:
            raise ValueError('shared movement program source mismatch')
        if bridge.get('source_dispatch_sha256')!=hashlib.sha256(
                json.dumps(dispatch,sort_keys=True,separators=(',',':')).encode()).hexdigest():
            raise ValueError('shared movement dispatch content mismatch')
        if bridge.get('scratch_beat_bytes')!=64 or bridge.get('scratch_capacity_bytes')!=65536:
            raise ValueError('actual scratch64B/64KiB ABI required')
        if not re.fullmatch('[0-9a-f]{64}',bridge.get('bridge_source_sha256','')):
            raise ValueError('bridge producer source pin required')
        bridge_templates=bridge['templates']
        if not set(bridge_templates)<=set(dispatch['templates']):raise ValueError('unknown bridge native template')
    summaries={}
    for key,t in dispatch['templates'].items():
        r=bridge_templates.get(key)
        if r is None:
            summaries[key]={'status':'UNKNOWN_UNBOUND_SHARED_MOVEMENT','read64':None,'write64':None}
            continue
        if t['execution_path']!='source_order_live_range_stages':
            summaries[key]={'status':'UNKNOWN_FORWARD_LEAF_CONTINUATION_NOT_RESOLVED',
                'read64':None,'write64':None}
            continue
        if key not in native_program['templates']:raise ValueError('bridge retained template missing')
        code=native_program['templates'][key]['code']
        specs=native_value_specs(native_program,key)
        native_counts=Counter()
        for node in code:native_counts[node['op']]+=max(1,math.prod(node['shape']))
        if dict(native_counts)!=t['executed_primitive_scalar_projection']:
            raise ValueError('retained instruction projection mismatch')
        if r.get('execution_path')!=t['execution_path'] or r.get('native_primitive_scalars')!=t['executed_primitive_scalar_projection']:
            raise ValueError('bridge native instruction count/path mismatch')
        movements=r.get('ordered_movements');reads=writes=0;leases={};last_step=-1;covered=defaultdict(list)
        if not isinstance(movements,list):raise ValueError('ordered shared movement commands required')
        for m in movements:
            step=m['source_step'];kind=m['event'];identity=m['lease']
            if type(step)!=int or step<last_step or step<0:raise ValueError('shared source step order')
            last_step=step
            if kind=='acquire':
                base=m['base'];size=m['bytes']
                if identity in leases or type(base)!=int or type(size)!=int or base<0 or size<=0 or base%64 or size%64 or base+size>65536:
                    raise ValueError('finite shared concrete lease extent')
                if any(base<e['base']+e['bytes'] and e['base']<base+size for e in leases.values()):raise ValueError('shared live alias')
                value=m.get('value');offset=m.get('logical_byte_offset');payload=m.get('payload_bytes')
                if value not in specs or type(offset)!=int or type(payload)!=int or offset<0 or offset%64 or payload<=0 or offset+payload>specs[value]['bytes'] or size!=ceil(payload,64)*64:
                    raise ValueError('shared lease does not resolve retained value span')
                leases[identity]={'base':base,'bytes':size,'value':value,'offset':offset,'payload':payload,'written':[]}
            elif kind=='release_after_ACK_reverse':
                if identity not in leases:raise ValueError('unmatched shared retirement')
                del leases[identity]
            elif kind in ('read64','write64_ACK'):
                if identity not in leases:raise ValueError('shared movement missing live lease')
                count=positive(m['repetitions'],'actual shared instruction repetitions')
                lease=leases[identity];base,size=lease['base'],lease['bytes'];address=m['byte_address'];span=m['span_bytes']
                if type(address)!=int or type(span)!=int or address%64 or span<=0 or span%64 or address<base or address+span>base+size:
                    raise ValueError('shared instruction address extent')
                role,symbol,typed_bytes,offset,payload=resolve_ds_movement_reference(native_program,key,m.get('native_instruction_ref'),specs)
                if role[0]!=step or (kind=='read64')!=(role[1]!='dst'):
                    raise ValueError('native movement step/read-write role mismatch')
                if span!=ceil(payload,64)*64 or count!=1:
                    raise ValueError('native movement span/repetitions not resolved from source')
                if symbol!=lease['value'] or offset<lease['offset'] or offset+payload>lease['offset']+lease['payload'] or address!=base+offset-lease['offset']:
                    raise ValueError('shared movement does not match actual value/home slice')
                if kind=='read64' and not any(a<=offset and offset+payload<=b for a,b in lease['written']):
                    raise ValueError('shared read before source write visibility')
                if kind=='write64_ACK':lease['written'].append((offset,offset+payload))
                covered[role].append((offset,offset+payload))
                if kind=='read64':reads+=count*span//64
                else:writes+=count*span//64
            else:raise ValueError('unknown shared bridge movement event')
        if leases:raise ValueError('shared lease retained past template retirement')
        # RF alternatives must resolve the same complete operand obligations.
        # No exported proof string can suppress missing reads/writes.
        routes=r.get('RF_operand_routes',[])
        rf_homes=r.get('RF_value_homes',{});last={}
        for i,node in enumerate(code):
            for symbol in node['src']:last[symbol]=i
        for symbol in native_program['templates'][key]['outputs'].values():last[symbol]=len(code)
        for symbol,home in rf_homes.items():
            if symbol not in specs:raise ValueError('RF home unknown source value')
            slot=home.get('slot_first');vectors=home.get('vectors')
            if type(slot)!=int or type(vectors)!=int or slot<0 or slot+vectors>32 or vectors!=ceil(specs[symbol]['bytes'],512):
                raise ValueError('RF source value home capacity')
        for a,ha in rf_homes.items():
            for b,hb in rf_homes.items():
                if a>=b:continue
                simultaneous=specs[a]['definition']<=last.get(b,specs[b]['definition']) and specs[b]['definition']<=last.get(a,specs[a]['definition'])
                if simultaneous and ha['slot_first']<hb['slot_first']+hb['vectors'] and hb['slot_first']<ha['slot_first']+ha['vectors']:
                    raise ValueError('RF live source value home alias')
        for route in routes:
            role,symbol,size,offset,payload=resolve_ds_movement_reference(native_program,key,route.get('native_instruction_ref'),specs)
            slot=route.get('slot_first');vectors=route.get('vectors')
            if type(slot)!=int or type(vectors)!=int or slot<0 or vectors<1 or slot+vectors>32 or vectors!=ceil(payload,512):
                raise ValueError('finite source-resolved RF operand route')
            if route.get('visibility_guard')!='two-mirror visible_ACK':raise ValueError('RF route missing mirrored ACK')
            if rf_homes.get(symbol)!={'slot_first':slot,'vectors':vectors} or offset!=0 or payload!=size:
                raise ValueError('RF route does not match source value home')
            covered[role].append((offset,offset+payload))
        for i,node in enumerate(code):
            for operand in ['dst']+['src:'+str(j) for j in range(len(node['src']))]:
                spans=sorted(covered[(i,operand)]);cursor=0
                for start,end in spans:
                    if start!=cursor:raise ValueError('incomplete or duplicate native movement operand coverage')
                    cursor=end
                symbol=node['dst'] if operand=='dst' else node['src'][int(operand[4:])];size=specs[symbol]['bytes']
                if cursor!=size:raise ValueError('incomplete native movement operand coverage')
        summaries[key]={'status':'BOUND_SOFTWARE_MOVEMENT_TRACE','read64':reads,'write64':writes,
                        'bridge_source_sha256':bridge['bridge_source_sha256'],
                        'actual_source_instruction_operand_coverage':True}
    rows=[];tick=0;commands=shared_reads=shared_writes=0;unknown_calls=0;count=Counter()
    dispatch_cost=sum(v for k,v in costs.items() if k.startswith('C0_'))
    for op,old in zip(dispatch['PC_dispatch'],baseline['PC_intervals']):
        by_rank=defaultdict(lambda:{'native':Counter(),'batches':Counter(),'read64':0,'write64':0,'unknown':[],'templates':[]})
        for call in op['calls']:
            key=call['template'];r=by_rank[call['rank']];r['native'].update(dispatch['templates'][key]['executed_primitive_scalar_projection'])
            if leaf_catalog is not None:
                entry=leaf_catalog['templates'][key]
                if entry['native_scalars']!=dispatch['templates'][key]['executed_primitive_scalar_projection']:
                    raise ValueError('C0 forward leaf native source mismatch')
                r['batches'].update(entry['native_batches128'])
            r['templates'].append(key);s=summaries[key]
            if s['read64'] is None:r['unknown'].append(key);unknown_calls+=1
            else:r['read64']+=s['read64'];r['write64']+=s['write64'];shared_reads+=s['read64'];shared_writes+=s['write64']
        rank_rows=[]
        for old_rank in old['ranks']:
            rank=old_rank['rank'];r=by_rank[rank]
            n=sum(r['batches'].values()) if leaf_catalog is not None else sum(r['native'].values())
            commands+=n;count.update(r['native'])
            c0=n*dispatch_cost;shared=r['read64']*costs['scratch64_read']+r['write64']*costs['scratch64_write_ACK']
            duration=old_rank['end']-old_rank['start']+c0+shared
            rank_rows.append({'rank':rank,'start':tick,'end':tick+duration,
                'native_scalar_command_upper_by_opcode':dict(r['native']),'C0_command_upper':n,
                **({'C0_source_leaf_batches128_by_opcode':dict(r['batches'])} if leaf_catalog is not None else {}),
                'C0_ticks':c0,'shared_known_ticks':shared,
                'scratch64_reads':None if r['unknown'] else r['read64'],
                'scratch64_writes_ACK':None if r['unknown'] else r['write64'],
                'bound_shared_read64_subtotal':r['read64'],'bound_shared_write64_subtotal':r['write64'],
                'unknown_shared_templates':r['unknown'],'baseline_provider_and_native_ticks_charged_once':old_rank['end']-old_rank['start'],
                'workspace_peak_upper':old_rank['workspace_peak_upper'],'resources':old_rank['resources'],
                'C0_and_scratch_transaction_credits_per_SM':1,'scoreboard_entries_per_SM':512,
                'RF_credit_held_until':'two-mirror visible_ACK','ordered_executor_templates':r['templates']})
        collective=op['family'] in ('all_gather','all_reduce','topk_merge')
        # all_gather's existing provisional admission is already in baseline.
        collective_delta=costs['atomic_collective_admit'] if collective and op['family']!='all_gather' else 0
        end=max(r['end'] for r in rank_rows)+collective_delta
        rows.append({'pc':op['pc'],'family':op['family'],'start':tick,'end':end,'ranks':rank_rows,
            'dependencies':op['dependencies'],'atomic_collective_participants':sorted(by_rank) if collective else [],
            'global_collective_credit':int(collective),'additional_atomic_admission_ticks':collective_delta,
            'actual_collective_payload_route_ticks':None if collective else 'not a collective PC',
            'shared_scope_complete':not any(r['unknown_shared_templates'] for r in rank_rows)})
        tick=end
    return {'schema':'H4_DS_ALL_PC_FINITE_KNOWN_SERVICE_COMPOSITION_V1','PCs':len(rows),
        'families':baseline['families'],'PC_intervals':rows,'source_program_sha256':dispatch['source_program_sha256'],
        'native_scalar_commands_upper_by_opcode':dict(count),'C0_scalar_command_upper':sum(count.values()),
        **({'C0_source128lane_commands':commands} if leaf_catalog is not None else {}),
        'known_service_software_ticks':tick,'complete_service_software_ticks':None,
        'scratch64_read_transactions':None if unknown_calls else shared_reads,
        'scratch64_write_ACK_transactions':None if unknown_calls else shared_writes,
        'bound_scratch64_read_subtotal':shared_reads,'bound_scratch64_write_ACK_subtotal':shared_writes,
        'unknown_shared_template_calls':unknown_calls,'template_shared_bindings':summaries,
        'constrained_extent_successor_demand':baseline['constrained_extent_successor_demand'],
        'explicit_provisional_costs':costs,'retained_baseline_provisional_costs':baseline['explicit_provisional_costs'],
        'status':'PARTIAL_KNOWN_SERVICE_COST_WITH_EXPLICIT_SHARED_UNKNOWNS' if unknown_calls else 'PASS_ALL_PC_NATIVE_AND_SHARED_COST_JOIN_WITH_CHECKPOINT_GAP',
        'native_command_count_scope':'source-resolved forward/original128lane batches with actual source loop repetitions; hardware command bridge still required' if leaf_catalog is not None else
            'one command per scalar is conservative upper; actual vector/loop bridge needed',
        'checkpoint_traffic_cost':'UNKNOWN_NOT_INCLUDED_IN_KNOWN_SUBTOTAL',
        'ordered_full_native_trace':False,'arithmetic_or_provider_rerun':False,'r22_augmentation_applied':False,
        'hardware_full_native_claim':False,'clock_admission':False,'physical_admission':False}


def compile_ssa_finite_sm_services(program, *, rank, provider_bindings, workspace=None, costs=None):
    """Ordered native stage issue templates and bounded last-use allocation.

    Input is actual source SSA, never a macro callback or opcode histogram.
    Blocks are lossless128-lane repetitions. Source block256%32 selects the
    issuing SM; all services serialize, with no assumed32SM speedup. Operand
    transport deliberately reloads a whole source before each result batch,
    a positive conservative bound until actual indexed provider traffic exists.
    This compiler does not execute payloads or supply RTL implementations.
    """
    if type(rank) is not int or not 0<=rank<96: raise ValueError('DS rank extent')
    if set(provider_bindings)!=set(program['providers']): raise ValueError('exact native provider LOAD bindings required')
    cap=33554432; workspace=dict(workspace or {'AW':27,'base':None,'bytes':cap,'occupied_extents':[]})
    if workspace.get('AW')!=27 or workspace.get('bytes')!=cap: raise ValueError('AW27/32MiB provider workspace required')
    base=workspace.get('base')
    if base is not None:
        if type(base) is not int or base<0 or base%512 or base+cap>1<<27: raise ValueError('workspace aperture/alignment')
        if 'occupied_extents' not in workspace: raise ValueError('actual occupied provider extents required')
        for e in workspace['occupied_extents']:
            if type(e['base']) is not int or type(e['bytes']) is not int or e['base']<0 or e['bytes']<=0 or e['base']+e['bytes']>1<<27:
                raise ValueError('occupied provider extent aperture')
            if base<e['base']+e['bytes'] and e['base']<base+cap: raise ValueError('workspace/provider live alias')
    costs=dict(costs or {'native_batch':32,'RF_read_vector':3,'RF_mirrored_write_ACK':3,
        'HBM_sector_read':108,'HBM_sector_write':128,'RMW_merge':32,'route_fragment512':64,'admit':2,'consume':2,'retire':2})
    if set(costs)!={'native_batch','RF_read_vector','RF_mirrored_write_ACK','HBM_sector_read',
                   'HBM_sector_write','RMW_merge','route_fragment512','admit','consume','retire'}:
        raise ValueError('complete explicit SM/provider costs required')
    for key,value in costs.items():positive(value,key)
    code=program['code']; last={}; width={}; sizes={}; live={}; free=[(0,cap)]; stages=[]; released=[]
    tick=0; peak=0; generations=Counter(); counts=Counter(); batches=Counter()
    for index,node in enumerate(code):
        for ref in node['src']:last[ref]=index
    for ref in program['outputs'].values():last[ref]=len(code)
    def release(name,index):
        h=live.pop(name);free.append((h['offset'],h['reserved_bytes']));free.sort();merged=[]
        for address,size in free:
            if merged and merged[-1][0]+merged[-1][1]==address:merged[-1]=(merged[-1][0],merged[-1][1]+size)
            else:merged.append((address,size))
        free[:]=merged
        released.append({'symbol':name,'after_stage':index,'after_tick':tick,'generation':h['generation'],
                         'guard':'last source use and every accepted write/consumer/reverse grant retired'})
    for index,node in enumerate(code):
        for name in list(live):
            if last.get(name,-1)<index:release(name,index-1)
        op=node['op'];dst=node['dst'];args=node['src'];attrs=node.get('attrs',{})
        if dst in sizes or any(ref not in live for ref in args):raise ValueError('native SSA alias or premature source reuse')
        if any(type(d) is not int or d<0 for d in node['shape']):raise ValueError('native result shape extent')
        n=max(1,math.prod(node['shape']))
        w=(8 if attrs.get('dtype')=='I64' else 4) if op in ('LOAD','CONST') else 8 if op in ('F2I','IOTA') else (
            4 if op in ('I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_U','BITCAST_F') or op.startswith('FCMP')
            else max((width[r] for r in args),default=4))
        length=max(512,ceil(n*w,512)*512)
        chosen=next((j for j,(_,size) in enumerate(free) if size>=length),None)
        if chosen is None:
            return {'status':'CONSTRAINED_NATIVE_WORKSPACE_SUCCESSOR_REQUIRED','failed_stage':index,'opcode':op,
                'requested_definition_bytes':length,'live_definitions':live,'live_bytes':sum(h['reserved_bytes'] for h in live.values()),
                'largest_free_span_bytes':max((size for _,size in free),default=0),'workspace_bytes':cap,
                'source_order_stages_completed':len(stages),'stages':stages,'hardware_or_clock_admission':False,
                'successor':'refine this exact stage/shape under source rounding and last-use order; do not wrap addresses or stop other templates'}
        address,room=free[chosen];free[chosen:chosen+1]=[(address+length,room-length)] if room>length else []
        generations[address]+=1
        home={'offset':address,'base':None if base is None else base+address,'reserved_bytes':length,
              'typed_bytes':n*w,'generation':generations[address],'release_after_stage':last.get(dst,index)}
        source_homes={ref:dict(live[ref]) for ref in args}
        live[dst]=home;width[dst]=w;sizes[dst]=n*w;peak=max(peak,sum(h['reserved_bytes'] for h in live.values()))
        repeats=ceil(n,128);frame_vectors=3+sum(ceil(min(128,n)*width[r],512) for r in args)+ceil(min(128,n)*w,512)
        if frame_vectors>32:raise ValueError('finite RF32 primitive frame exhausted')
        reads=sum(ceil(sizes[r],512) for r in args)
        external=None
        if op=='LOAD':
            name=attrs['name'];external=provider_bindings.get(name)
            if external is None or not external.get('kind'):raise ValueError('missing actual source provider reference')
            if external['kind']=='versioned_operand' and not external.get('version'):
                raise ValueError('versioned provider source identity required')
            spec=program['providers'][name]
            if spec['shape']!=node['shape'] or spec['dtype']!=attrs['dtype']:
                raise ValueError('exact native provider shape/dtype required')
            reads+=ceil(n*w,512)
        phases=[{'phase':'admit','units':1,'cost':'admit'},
            {'phase':'provider_read_capture_and_reverse_grant','units':reads*16,'cost':'HBM_sector_read'},
            {'phase':'provider_route','units':reads,'cost':'route_fragment512'},
            {'phase':'RF_operand_reads_2R','units':sum(ceil(min(128,n)*width[r],512) for r in args),'cost':'RF_read_vector'},
            {'phase':'consume','units':1,'cost':'consume'},
            {'phase':'native_issue','units':1,'cost':'native_batch'},
            {'phase':'RF_two_mirror_visible_ACK','units':ceil(min(128,n)*w,512),'cost':'RF_mirrored_write_ACK'},
            {'phase':'possible_partial_destination_sector_read','units':1,'cost':'HBM_sector_read'},
            {'phase':'possible_partial_destination_RMW_merge','units':1,'cost':'RMW_merge'},
            {'phase':'workspace_commit_visible_and_reverse_grant','units':ceil(min(128,n)*w,32),'cost':'HBM_sector_write'},
            {'phase':'retire','units':1,'cost':'retire'}]
        cursor=0
        for phase in phases:
            phase['start']=cursor;cursor+=phase['units']*costs[phase['cost']];phase['end']=cursor
        stages.append({'stage':index,'op':op,'src':list(args),'dst':dst,'shape':node['shape'],'attrs':attrs,
            'scalar_elements':n,'semantic_bits':w*8,'source_homes':source_homes,'destination_home':dict(home),
            'external_provider_binding':external,'start':tick,'end':tick+cursor*repeats,
            'repetitions':repeats,'batch_stride':cursor,'last_batch_lanes':n-(repeats-1)*128,
            'phases':phases,'SM_recipe':'((batch_index*128)//256)%32','RF_frame_vectors_upper':frame_vectors,
            'resources_per_batch':{'RF_read_ports':2,'RF_write_ports':1,'RF_mirrors':2,'provider_tag':1,
                'request_queue':1,'write_residence':1,'rank_route_credit':1,'SM_issue_credit':1},
            'native_implementation_binding':'UNKNOWN_PENDING_H4_OWNER; software estimate only',
            'rounding_and_movement_contract':{'op':op,'attrs':attrs,'source_stage_order':index},'payload_executed':False})
        counts[op]+=n;batches[op]+=repeats;tick+=cursor*repeats
    outputs={name:dict(live[ref],symbol=ref) for name,ref in program['outputs'].items()}
    for name in list(live):release(name,len(code))
    return {'status':'PASS_ORDERED_NATIVE_STAGE_FINITE_SM_SOFTWARE_RESERVATION','rank':rank,'stages':stages,
        'primitive_scalars':dict(counts),'primitive_batches128':dict(batches),'outputs':outputs,'release_events':released,
        'workspace_peak_bytes':peak,'workspace':workspace,'RF_vectors_per_SM':32,'SMs':32,'software_ticks':tick,
        'explicit_provisional_costs':costs,'hardware_cost_calibration':'UNKNOWN_NO_CPU_PRIMITIVE_AS_RTL_CREDIT',
        'concrete_software_address_binding':base is not None,'physical_workspace_admission':False,
        'hardware_or_clock_admission':False,'payload_executed':False,
        'RMW_scope':'one possible partial sector read+merge conservatively charged per batch; contiguous I64, no second r22 sidecar charge',
        'transport_scope':'whole operand reload per result128batch conservative upper; exact indexed traffic remains provider-bound',
        'constrained_extent_successor_demand':[] if base is not None else [{'rank':rank,'bytes':cap,'alignment':512,
            'AW':27,'maximum_base':(1<<27)-cap,'base':None,'release_guard':'source last use + actual backing/consumer/reverse grant drain'}]}


def verify_ssa_finite_sm_services(calendar, program):
    if len(calendar['stages'])!=len(program['code']):raise ValueError('native stage coverage incomplete')
    if calendar['hardware_or_clock_admission'] or calendar['hardware_cost_calibration']!='UNKNOWN_NO_CPU_PRIMITIVE_AS_RTL_CREDIT':
        raise ValueError('CPU/software primitive cannot qualify RTL cost')
    definitions={};groups=defaultdict(list);counts=Counter();batches=Counter();tick=0;last={};width={};sizes={};generations=Counter()
    for index,node in enumerate(program['code']):
        for ref in node['src']:last[ref]=index
    for ref in program['outputs'].values():last[ref]=len(program['code'])
    for index,(stage,node) in enumerate(zip(calendar['stages'],program['code'])):
        if any(stage[k]!=node[k] for k in ('op','src','dst','shape','attrs') if k in node):
            raise ValueError('native instruction/source mismatch')
        n=max(1,math.prod(node['shape']));repeats=ceil(n,128);cursor=0
        op=node['op'];at=node.get('attrs',{});args=node['src']
        w=(8 if at.get('dtype')=='I64' else 4) if op in ('LOAD','CONST') else 8 if op in ('F2I','IOTA') else (
            4 if op in ('I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_U','BITCAST_F') or op.startswith('FCMP')
            else max((width[r] for r in args),default=4))
        reads=sum(ceil(sizes[r],512) for r in args)+(ceil(n*w,512) if op=='LOAD' else 0)
        expected_units=[1,reads*16,reads,sum(ceil(min(128,n)*width[r],512) for r in args),1,1,
                        ceil(min(128,n)*w,512),1,1,ceil(min(128,n)*w,32),1]
        expected_phases=['admit','provider_read_capture_and_reverse_grant','provider_route','RF_operand_reads_2R',
            'consume','native_issue','RF_two_mirror_visible_ACK','possible_partial_destination_sector_read',
            'possible_partial_destination_RMW_merge','workspace_commit_visible_and_reverse_grant','retire']
        if [p['units'] for p in stage['phases']]!=expected_units or [p['phase'] for p in stage['phases']]!=expected_phases:
            raise ValueError('native provider read/write/native repetition obligations mismatch')
        expected_costs=['admit','HBM_sector_read','route_fragment512','RF_read_vector','consume','native_batch',
            'RF_mirrored_write_ACK','HBM_sector_read','RMW_merge','HBM_sector_write','retire']
        if [p['cost'] for p in stage['phases']]!=expected_costs:raise ValueError('native service cost reference mismatch')
        if stage['start']!=tick or stage['stage']!=index or stage['repetitions']!=repeats or stage['scalar_elements']!=n:
            raise ValueError('native issue/repetition/source order mismatch')
        for ref in node['src']:
            if ref not in definitions or stage['source_homes'][ref]!=definitions[ref] or last[ref]<index:
                raise ValueError('native source lease/generation mismatch')
        for phase in stage['phases']:
            cost=positive(calendar['explicit_provisional_costs'][phase['cost']],phase['cost'])
            if type(phase['units']) is not int or phase['units']<0 or phase['start']!=cursor:
                raise ValueError('native service phase order/capacity')
            cursor+=phase['units']*cost
            if phase['end']!=cursor:raise ValueError('native service phase cost mismatch')
        if stage['batch_stride']!=cursor or stage['end']!=tick+cursor*repeats:
            raise ValueError('native repeated interval cost mismatch')
        if stage['RF_frame_vectors_upper']>32 or stage['resources_per_batch']!=dict(RF_read_ports=2,RF_write_ports=1,
            RF_mirrors=2,provider_tag=1,request_queue=1,write_residence=1,rank_route_credit=1,SM_issue_credit=1):
            raise ValueError('finite SM/provider capacity mismatch')
        home=stage['destination_home'];address=home['offset'];size=home['reserved_bytes']
        generations[address]+=1
        if home['generation']!=generations[address]:raise ValueError('native write reuse generation mismatch')
        if stage['semantic_bits']!=w*8 or home['typed_bytes']!=n*w:
            raise ValueError('native semantic word width/storage mismatch')
        if address<0 or address%512 or size%512 or size<=0 or address+size>calendar['workspace']['bytes']:
            raise ValueError('native workspace extent overrun')
        if home['release_after_stage']!=last.get(node['dst'],index):raise ValueError('premature source write reuse')
        for birth,retire,lo,hi in groups['workspace']:
            if retire>=index and address<hi and lo<address+size:raise ValueError('native live workspace alias')
        groups['workspace'].append((index,home['release_after_stage'],address,address+size))
        definitions[node['dst']]=home;width[node['dst']]=w;sizes[node['dst']]=n*w
        tick=stage['end'];counts[node['op']]+=n;batches[node['op']]+=repeats
    if dict(counts)!=calendar['primitive_scalars'] or dict(batches)!=calendar['primitive_batches128'] or tick!=calendar['software_ticks']:
        raise ValueError('native stage primitive count/total cost mismatch')
    return {'status':'PASS_ORDERED_SOURCE_STAGE_PORT_CREDIT_LIFETIME_AND_COST_PROOF','source_stages':len(calendar['stages']),
        'primitive_batches128':sum(batches.values()),'native_RTL_cost_credit':False,'physical_workspace_admission':False,
        'payload_executed':False,'transport_scope':calendar['transport_scope']}


class AddressedTileByteBackend:
    """Immutable byte requests use R21 real finite ownership and backing.

    Padding is explicitly loader initialized but never a valid logical byte
    range. No response ACK is invented: each ticket drains its reverse grant.
    """
    def __init__(self, K, native):
        self.K = K; self.pc = 0; self.serial = 0; self.loaded = set()
        self.epoch = 0
        self.extents = {e['provider_ref']: dict(e, rank=a['rank'])
            for a in native['provider_binding']['allocation'] for e in a['extents']}
        extents = defaultdict(list)
        for e in self.extents.values():
            extents['Qwen', e['rank']].append({'base': e['base'], 'bytes': ceil(e['bytes'], 32) * 32})
        for rank in range(2):
            for sm in range(32):
                for mirror in range(2):
                    extents[f'Qwen_RF_SM{sm}_copy{mirror}', rank].append({'base': 0, 'bytes': 512*512})
        self.events = Counter(); self.digest = hashlib.sha256()
        owner = self
        class Journal(K.SectorProvider):
            def log(self, event, ticket, **kw):
                super().log(event, ticket, **kw)
                record = self.events.pop(); owner.events[event] += 1
                owner.digest.update(encode(record) + b'\n')
        self.provider = Journal(dict(extents), tags=1, queue=1, write_residence=1)

    def transaction(self, target, rank, sector, payload=None):
        self.serial += 1
        identity = self.K.Identity(target, rank, self.epoch, self.pc, self.serial, sector)
        p = self.provider
        # Explicit RF service estimate, distinct from HBM64/80. All request,
        # owner lookup, CDC and reverse phases remain positive and recorded.
        read, write = (3, 3) if target.startswith('Qwen_RF_') else (64, 80)
        p.read_ticks, p.write_ticks = read, write
        p.costs['read_service'], p.costs['write_service'] = read, write
        t = p.submit(identity, payload is not None, payload or b'')
        value = p.wait(t); p.finish(t)
        return value

    def write_changes(self, target, rank, changes):
        parts = defaultdict(dict)
        for address, byte in changes.items(): parts[address//32][address%32] = int(byte)
        for sector, updates in sorted(parts.items()):
            if len(updates) == 32: data = bytearray(updates[i] for i in range(32))
            else:
                if (target, rank, sector) not in self.provider.backing:
                    self.provider.seed(target, rank, sector*32, bytes(32))
                data = bytearray(self.transaction(target, rank, sector))
                for offset, byte in updates.items(): data[offset] = byte
            self.transaction(target, rank, sector, bytes(data))

    def read_addresses(self, target, rank, addresses):
        captures = {}
        for sector in sorted({int(a)//32 for a in addresses}):
            captures[sector] = self.transaction(target, rank, sector)
        return bytes(captures[int(a)//32][int(a)%32] for a in addresses)

    def seed(self, ref, offset, payload):
        e = self.extents[ref]; address = e['base'] + offset
        if offset < 0 or offset + len(payload) > e['bytes']:
            raise ValueError('immutable loader logical extent')
        # Initialize only touched sector padding; retain an independent logical
        # loaded-byte set so missing checkpoint bytes never turn into zeros.
        for sector in range(address // 32, (address + len(payload) + 31) // 32):
            if ('Qwen', e['rank'], sector) not in self.provider.backing:
                self.provider.seed('Qwen', e['rank'], sector * 32, bytes(32))
        self.provider.seed('Qwen', e['rank'], address, payload)
        self.loaded.update((e['rank'], address + i) for i in range(len(payload)))

    def read_tile_bytes(self, request):
        e = self.extents.get(request.get('provider_ref'))
        if e is None or request.get('lease_state') != 'visible' or request.get('lease') != f'PC{self.pc}.{e["provider_ref"]}':
            raise ValueError('immutable provider lease/ref mismatch')
        payloads = []; captures = {}
        for r in request['byte_ranges']:
            address, size = r['address'], r['bytes']
            if size <= 0 or not e['base'] <= address or address + size > e['base'] + e['bytes']:
                raise ValueError('immutable request logical extent')
            if any((e['rank'], address + i) not in self.loaded for i in range(size)):
                raise ValueError('immutable checkpoint bytes missing')
            for sector in range(address // 32, (address + size + 31) // 32):
                if sector not in captures:
                    captures[sector] = self.transaction('Qwen', e['rank'], sector)
            payloads.append(bytes(captures[(address+i)//32][(address+i)%32] for i in range(size)))
        return {'provider_ref': request['provider_ref'], 'lease': request['lease'], 'state': 'visible',
                'reverse_grant_ACK': not self.provider.live, 'payloads': payloads}

    def proof(self):
        return {'events': dict(self.events), 'journal_sha256': self.digest.hexdigest(),
                'provisional_ticks': self.provider.now, 'all_owners_drained': not self.provider.live,
                'loader_bytes': len(self.loaded), 'hardware_or_clock_admission': False}


def seed_bounded_fixture(N, backend, native, positions):
    """Explicit small raw immutable image loader; excluded from execution costs."""
    import numpy as np
    p = native['source_program']; c = p['config']; raw = N.TileFixtureWeights(p)
    def put(rank, name, offset, data): backend.seed(f'Qwen.rank{rank}.extent.{name}', offset, data)
    for key, d in p['weight_descriptors'].items():
        prefix = 'head' if d['layer'] is None else f'L{d["layer"]}.{d["name"]}'
        for start in range(0, d['rows'], 128):
            n = min(128, d['rows'] - start)
            for col in range(0, d['K'], 32):
                k = min(32, d['K'] - col); codes = raw.matrix_tile(key, start, n, col, k)
                for row in range(n): put(d['die'], prefix+'.codes', (start+row)*d['K']+col, codes[row].tobytes())
            put(d['die'], prefix+'.scales', 2*start,
                (raw.scale_tile(key, start, n).view(np.uint32)>>16).astype('<u2').tobytes())
    h = c['hidden_size']; hd = c['head_dim']
    for rank in range(2):
        for token in range(c['vocab_size']):
            for start in range(0, h, 128):
                codes, scale = raw.embedding_tile(token, start, min(128, h-start))
                put(rank, 'embedding', token*h+start, codes.tobytes())
            put(rank, 'embedding', c['vocab_size']*h+2*token,
                np.array([int(scale.view(np.uint32))>>16], '<u2').tobytes())
        for layer in range(c['num_hidden_layers']):
            put(rank, f'L{layer}.qk_norm', 0, np.full(2*hd, 0x3f80, '<u2').tobytes())
        put(rank, 'final_norm', 0, np.full(h, 0x3f80, '<u2').tobytes())
        for position in positions:
            for start in range(0, hd//2, 128):
                n = min(128, hd//2-start)
                co, si = raw.rope_tile(position, c['rope_theta'], start, n)
                put(rank, 'rope_table', 4*(position*hd+start), co.astype('<f4').tobytes())
                put(rank, 'rope_table', 4*(position*hd+hd//2+start), si.astype('<f4').tobytes())


def execute_bounded_provider_program(N, K, native, backend, *, positions, sidecars=None, observer=None,
                                     latency=None):
    """All-PC tiled execution with R21 addressed microVM arithmetic/transport.

    N and K must be source-pinned producer modules. Immutable bytes come only
    from the caller backend. A finite16KiB RF shadow holds primitive operands;
    optional R20 sidecars use their real low/high addresses, not new extents.
    The shadow and event journals are software models, not physical RF hardware.
    No materialized fullshape calendar or r22 cost augmentation executes here.
    """
    import numpy as np
    latency = dict(latency or {'native_batch':32, 'scratch64_transaction':8, 'NoC_page512':64,
                               'PC_admit':2, 'PC_retire':2, 'visibility_fence':4, 'collective_rendezvous':2})
    required = {'native_batch','scratch64_transaction','NoC_page512','PC_admit','PC_retire','visibility_fence','collective_rendezvous'}
    if set(latency)!=required: raise ValueError('complete explicit latency table required')
    for key,value in latency.items(): positive(value,key)
    if not hasattr(backend, 'read_tile_bytes'):
        raise ValueError('actual raw provider byte backend required')
    sidecars = sidecars or []
    bypc = defaultdict(list)
    for h in sidecars:
        if h.get('semantic_bits') == 64 and h['class_'] == 'HBM_native_workspace':
            bypc[h['pc']].append(h)
    frame_extents = {('Qwen_RF_shadow', 0): [{'base': 0, 'bytes': 16384}]}
    for homes in bypc.values():
        for h in homes:
            es = frame_extents.setdefault(('Qwen', h['rank']), [])
            for base, size in [(h['base'], h['reserved_bytes']), (h['highword_base'], h['highword_reserved_bytes'])]:
                e = {'base': base, 'bytes': size}
                if e not in es: es.append(e)
    # Different PCs reuse arenas: union their address ranges before provider
    # construction. Per-definition ownership still uses immutable generations.
    for key, es in frame_extents.items():
        merged = []
        for e in sorted(es, key=lambda e: e['base']):
            end = e['base'] + e['bytes']
            if merged and e['base'] <= merged[-1]['base'] + merged[-1]['bytes']:
                merged[-1]['bytes'] = max(end, merged[-1]['base'] + merged[-1]['bytes']) - merged[-1]['base']
            else: merged.append(dict(e))
        frame_extents[key] = merged
    journal_counts = Counter(); journal_hash = hashlib.sha256()
    class JournalProvider(K.SectorProvider):
        def log(self, event, ticket, **kw):
            super().log(event, ticket, **kw)
            record = self.events.pop(); journal_counts[event] += 1
            journal_hash.update(encode(record) + b'\n')
    provider = JournalProvider(frame_extents, tags=1, queue=1, write_residence=1)
    frame = K.Storage(provider, 'Qwen_RF_shadow', 0, 0, 16384)
    codec = {rank: K.Storage(provider, 'Qwen', rank, es[0]['base'], es[0]['bytes'])
             for (target, rank), es in frame_extents.items() if target == 'Qwen'}
    pc = [-1]; physical_batches = Counter(); primitive_journal = hashlib.sha256(); step_number = [0]
    pc_rows = []; tick = [0]; position_now = [0]
    sidecar_uses = Counter()
    class Router:
        def __init__(self): self.provider = provider; self.tile = 128; self._epoch = 0; self._pc = 0
        @property
        def epoch(self): return self._epoch
        @epoch.setter
        def epoch(self, value):
            self._epoch = value; frame.epoch = value
            for s in codec.values(): s.epoch = value
        @property
        def pc(self): return self._pc
        @pc.setter
        def pc(self, value):
            self._pc = value; frame.pc = value
            for s in codec.values(): s.pc = value
        def read(self, t, indexes): return (frame if t.target == frame.target else codec[t.rank]).read(t, indexes)
        def write(self, t, start, data): return (frame if t.target == frame.target else codec[t.rank]).write(t, start, data)
        def allocate(self, shape, dtype):
            if dtype == 'I64' and available:
                h = available.pop(0); sidecar_uses[pc[0]] += 1
                return K.tensor_from_native_binding(h, shape)
            return frame.allocate(shape, dtype)
        def free(self, t):
            if t.target == frame.target: frame.free(t)
    router = Router(); available = []
    class AddressedVM(N.NativePrimitiveVM):
        def primitive(self, op, args, attrs=None, shape=None):
            at = dict(attrs or {}); values = [np.asarray(v) for v in args]
            if any(v.size > 128 for v in values): raise ValueError('native operand needs outer tile')
            if at.get('dtype') in ('U32', 'I64'):
                values = [v.astype(np.uint32 if at['dtype'] == 'U32' else np.int64) for v in values]
            if op == 'COPY': operation = 'PACKET_COMMIT'
            else: operation = op
            if operation not in K.MicroVM.SUPPORTED:
                raise ValueError('provider microVM unsupported primitive ' + op)
            if shape is None: shape = list(np.broadcast_shapes(*(v.shape for v in values))) if values else []
            if math.prod(shape) > 128: raise ValueError('native result needs outer tile')
            if provider.live or frame.allocations: raise ValueError('primitive frame reused before reverse grant')
            available[:] = sorted(bypc.get(pc[0], []), key=lambda h: (h['rank'], h['symbol']))
            router.pc = pc[0]; router.epoch += 1; inputs = {}; code = []
            for j, value in enumerate(values):
                dtype = ('F32' if value.dtype.kind == 'f' else 'I8' if value.dtype == np.int8 else
                         'U8' if value.dtype == np.uint8 else 'I64' if value.dtype == np.int64 else 'U32')
                t = router.allocate(tuple(value.shape), dtype); router.write(t, 0, value.reshape(-1))
                inputs[str(j)] = t
                code.append({'op': 'LOAD', 'dst': 'a' + str(j), 'src': [], 'shape': list(value.shape),
                             'attrs': {'name': str(j), 'dtype': dtype}})
            code.append({'op': operation, 'dst': 'out', 'src': ['a' + str(j) for j in range(len(values))],
                         'shape': list(shape), 'attrs': at})
            vm = K.MicroVM(router)
            result_tensor = vm.run({'code': code, 'outputs': {'out': 'out'}, 'source_pc': pc[0]}, inputs)['out']
            result = router.read(result_tensor, np.arange(result_tensor.count)).reshape(shape)
            for entry in vm.journal:
                physical_batches[entry['op']] += 1; primitive_journal.update(encode(entry) + b'\n')
                if entry['staging_payload_bytes'] > 1536: raise ValueError('provider staging capacity exhausted')
            for t in list(inputs.values()) + list(vm.registers.values()): router.free(t)
            if provider.live or provider.queue or provider.resident or frame.allocations:
                raise ValueError('primitive ownership not drained')
            self.counts[op] += 1; self.word_counts[op] += result.size
            self.fault |= vm.fault; step_number[0] += 1
            self.peak_vectors = max(self.peak_vectors, ceil(frame.peak_live_bytes, 512))
            return result
    class TransportWords(N.TileWords):
        def location(self, key, mirror=0):
            kind, rank, sm, page = key
            return (f'Qwen_RF_SM{sm}_copy{mirror}', rank, page*512) if kind == 'RF' else ('Qwen', rank, page)
        def write(self, version, start, values):
            super().write(version, start, values)
            touched = {self.key(version,start+i,rank)[0]
                for rank in {h['rank'] for h in self.values[version]['homes']} for i in range(np.size(values))}
            for key in sorted(touched):
                for mirror, data in enumerate(self.pages[key]):
                    target, rank, base = self.location(key, mirror)
                    raw = data.astype('<u4').tobytes()
                    backend.write_changes(target, rank, {base+i:b for i,b in enumerate(raw)})
        def read_indices(self, version, indices):
            if version not in self.published: raise ValueError('unpublished source')
            ids = np.asarray(indices,np.int64).reshape(-1)
            shape, kind = self.shapes[version]; total = 2 if kind == 'winner' else math.prod(shape)
            if len(ids)>128 or np.any(ids<0) or np.any(ids>=total): raise ValueError('source read aperture')
            result = np.empty(len(ids),np.uint32); rank = self.rank(version)
            for i, word in enumerate(ids):
                key,lane = self.key(version,int(word),rank)
                if self.owners.get(key)!=version or key not in self.pages: raise ValueError('source provider lease identity')
                if self.cache is None or self.cache[0]!=key:
                    copies = []
                    for mirror in range(len(self.pages[key])):
                        target,r,base = self.location(key,mirror)
                        copies.append(np.frombuffer(backend.read_addresses(target,r,range(base,base+512)), '<u4').copy())
                    if len(copies)==2 and not np.array_equal(*copies): raise ValueError('RF mirror disagreement')
                    self.cache = (key,copies[0])
                    self.counters['RF_read' if key[0]=='RF' else 'HBM_read_sectors32'] += 1 if key[0]=='RF' else 16
                    self.counters['source_read_payload_bits'] += 4096
                    if (key[1],key[2])!=(self.worker_rank,self.worker_SM): self.counters['NoC_source_read_bits'] += 4096
                result[i] = self.cache[1][lane]
            self.counters['source_word_reads'] += len(ids)
            return result if kind in ('U32','winner') else result.view(np.float32)
    class TransportKV(N.BoundKVStorage):
        def state_write(self, rank, offset, data):
            super().state_write(rank,offset,data)
            base = self.state[rank]['base']+offset
            backend.write_changes('Qwen',rank,{base+i:b for i,b in enumerate(data)})
        def state_read(self, rank, offset, count):
            e=self.state[rank]
            if offset<0 or offset+count>e['bytes']: raise ValueError('KV state byte aperture')
            # State has an explicit cold zero initialization, unlike checkpoint bytes.
            self.counters['state_read_sectors32'] += len(set((e['base']+offset+i)//32 for i in range(count)))
            return backend.read_addresses('Qwen',rank,range(e['base']+offset,e['base']+offset+count))
        def commit(self, tag):
            state=self.pending[int(tag)]; rank=state['key'][1]
            backend.write_changes('Qwen',rank,state['payload'])
            return super().commit(tag) # publication follows all actual backing grants
        def read(self, lease, addresses):
            super().read(lease,addresses) # validate source producer generation and two-reader lease
            rank=self.leases[int(lease)]['key'][1]
            raw=backend.read_addresses('Qwen',rank,np.asarray(addresses).reshape(-1))
            return np.frombuffer(raw,np.uint8).copy().reshape(np.shape(addresses))
    for e in backend.extents.values():
        if e['name']=='KV_provider_state':
            backend.provider.seed('Qwen',e['rank'],e['base'],bytes(ceil(e['bytes'],32)*32))
    machine = N.TiledMachine(native, N.HBMByteTileProvider(backend)); machine.vm = AddressedVM()
    machine.store = TransportWords(native); machine.memory = TransportKV(native['source_program'])
    original_execute = machine.execute
    def execute(op):
        pc[0] = op['pc']; backend.pc = op['pc']
        before = Counter(machine.vm.counts); batches = Counter(physical_batches)
        begin_provider = provider.now + backend.provider.now
        before_transfer = Counter(machine.store.counters); before_tiles = Counter(machine.counters)
        original_execute(op)
        counts = Counter(machine.vm.counts)-before
        source = native['source_program']['instructions'][op['pc']]
        expected = N.physical_tile_export(source,native['source_program'],position_now[0])['native_primitive_commands']
        if dict(counts)!=expected: raise ValueError('executed PC native primitive count mismatch '+str(op['pc']))
        transfers = Counter(machine.store.counters)-before_transfer; tiles = Counter(machine.counters)-before_tiles
        cost_units = {'native_batch':sum((Counter(physical_batches)-batches).values()),
            'scratch64_transaction':2*(tiles['shared_read_beats128']+tiles['shared_write_beats128']),
            'NoC_page512':(transfers['NoC_source_read_bits']+transfers['NoC_source_write_bits'])//4096,
            'PC_admit':1,'PC_retire':1,'visibility_fence':int(op['opcode']=='KV_FENCE'),
            'collective_rendezvous':int(op['opcode'] in ('ALL_REDUCE','ARGMAX_REDUCE'))}
        extra = sum(latency[k]*v for k,v in cost_units.items())
        elapsed = provider.now + backend.provider.now - begin_provider + extra
        if provider.live or backend.provider.live: raise ValueError('PC retires with retained provider ownership')
        start = begin_provider+tick[0]
        pc_rows.append({'pc':op['pc'],'position':position_now[0],'opcode':op['opcode'],'start':start,
            'end':start+elapsed,'dependencies':op['dependencies'],'native_commands':dict(counts),
            'provider_service_ticks':provider.now+backend.provider.now-begin_provider,
            'cost_units':cost_units,'reads':op['reads'],'writes':op['writes'],
            'all_provider_grants_before_PC_retire':True,'temporary_HBM_bytes':0})
        tick[0] += extra
    machine.execute = execute
    results = []; observer_ticks = [0]
    def observe(op, store):
        before = backend.provider.now+provider.now
        if observer: observer(op,store)
        observer_ticks[0] += backend.provider.now+provider.now-before
    for token, position in positions:
        backend.pc=0; position_now[0]=position
        backend.epoch = position
        results.append(machine.run(token, position, observe if observer else None))
        # Per-PC intervals price only their own transport; cold initialized
        # input publication is reported separately by the total provider ledger.
    result = {'status': 'PASS_ALL_PC_BOUNDED_PROVIDER_MICROVM_EXECUTION', 'executions': results,
        'provider_events': dict(journal_counts), 'provider_journal_sha256': journal_hash.hexdigest(),
        'primitive_journal_sha256': primitive_journal.hexdigest(), 'provider_native_batches': dict(physical_batches),
        'primitive_calls': step_number[0], 'RF_shadow_peak_bytes': frame.peak_live_bytes,
        'R20_sidecar_PC_uses': dict(sidecar_uses), 'all_provider_owners_drained': not provider.live,
        'codec_leases_drained': all(not s.codec_leases and not s.codec_locks for s in codec.values()),
        'provider_ticks': provider.now, 'cost_scope': 'positive provisional provider ticks, separate from existing calendar',
        'source_transport': backend.proof(),
        'native_service_ticks': sum(physical_batches.values())*latency['native_batch'],
        'explicit_provisional_latency':latency,'ordered_PC_intervals':pc_rows,
        'ordered_PC_ticks':tick[0]+provider.now+backend.provider.now,
        'post_commit_test_observer_service_ticks':observer_ticks[0],
        'initial_source_publication_ticks':provider.now+backend.provider.now-sum(r['provider_service_ticks'] for r in pc_rows)-observer_ticks[0],
        'calibration':'UNKNOWN_UNCALIBRATED; all software service estimates explicit and positive',
        'r22_augmentation_applied': False, 'existing_calendar_cost_mutated': False,
        'provider_sector_admission_ticks': 2, 'parent_sector_cost_admission_separately_accounted': True,
        'physical_or_clock_admission': False,
        'sidecar_scope': 'Optional addressed R20 staging experiment; not the zero-temporary-HBM bounded layout' if sidecars else
                         'I64 occupies two32bit words in finite RF shadow; zero additional temporary HBM'}
    result['interval_proof']=verify_bounded_provider_execution(result,native)
    return result


def verify_bounded_provider_execution(result, native):
    rows=result['ordered_PC_intervals'];n=len(native['operations']);done=set();previous=0;position=None
    if len(rows)!=n*len(result['executions']): raise ValueError('bounded executable PC coverage incomplete')
    latency=result['explicit_provisional_latency']
    for key,value in latency.items():positive(value,key)
    for index,row in enumerate(rows):
        if row['position']!=position: done=set();position=row['position']
        op=native['operations'][index%n]
        if row['pc']!=op['pc'] or row['dependencies']!=op['dependencies'] or not set(row['dependencies'])<=done:
            raise ValueError('bounded executable dependency deadlock')
        if row['reads']!=op['reads'] or row['writes']!=op['writes']:raise ValueError('bounded operand version alias')
        duration=row['provider_service_ticks']+sum(latency[k]*v for k,v in row['cost_units'].items())
        if row['start']<previous or row['end']-row['start']!=duration or duration<=0:
            raise ValueError('bounded executable interval overlap/cost mismatch')
        if not row['all_provider_grants_before_PC_retire'] or row['temporary_HBM_bytes']!=0:
            raise ValueError('bounded premature write reuse')
        done.add(row['pc']);previous=row['end']
    for events in (result['provider_events'],result['source_transport']['events']):
        if events['request_accept']!=events['validated_reverse_grant'] or events.get('reverse_quarantine',0):
            raise ValueError('bounded provider credit not drained')
    if not result['all_provider_owners_drained'] or not result['source_transport']['all_owners_drained']:
        raise ValueError('bounded retained provider ownership')
    if result['RF_shadow_peak_bytes']>16384 or any(e['RF_workspace_peak_vectors']>32 or e['shared_tile_peak_bytes']>17408 for e in result['executions']):
        raise ValueError('bounded finite capacity exhausted')
    return {'status':'PASS_ORDERED_PC_DEPENDENCY_COST_AND_FINITE_PROVIDER_PROOF',
        'PC_intervals':len(rows),'source_and_scratch_tags_each':1,'queues_each':1,'write_residence_each':1,
        'physical_or_clock_admission':False}


def execute_primitive_vm(target, program, payloads, *, snapshot, source_sha256,
                         scratch_bytes, instruction_limit, weights=None, storage=None, div=None):
    """Execute producer instructions, with explicit finite software admission.

    DS accepts an SSA template; Qwen accepts a recipe and an expression environment.
    Payloads are caller-supplied arrays, never an opcode/golden callback. This is
    a primitive numerical adapter, not a complete DS provider orchestrator.
    Scratch bounds cover resident tensor values; NumPy process/transient memory
    and hardware residence remain separate gates. No numerical runtime is used
    as a calendar latency. DIV requires an explicit primitive provider.
    """
    import numpy as np
    positive(scratch_bytes, 'VM scratch bytes')
    positive(instruction_limit, 'VM instruction limit')
    raw = Path(snapshot).read_bytes()
    if hashlib.sha256(raw).hexdigest() != source_sha256:
        raise ValueError('primitive VM source pin mismatch')
    tree = ast.parse(raw)
    namespace = {'np': np, '__name__': 'h3_pinned_primitive_vm', '__file__': str(snapshot)}
    if target == 'DeepSeek':
        # Only the producer's primitive machine is loaded; no compiler/module
        # side effects or high-level source operator dispatch can execute.
        machine = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Machine')
        exec(compile(ast.Module(body=[machine], type_ignores=[]), str(snapshot), 'exec'), namespace)
        code = program['code']
        if len(code) > instruction_limit:
            raise ValueError('finite VM instruction capacity exhausted')
        live = {}; last = {}; peak = 0
        for pc, ins in enumerate(code):
            for name in ins['src']: last[name] = pc
        for name in program['outputs'].values(): last[name] = len(code)
        for pc, ins in enumerate(code):
            if ins['dst'] in live or any(name not in live for name in ins['src']):
                raise ValueError('VM SSA alias or premature version consumption')
            # Eight bytes accommodates every producer scalar type, including
            # integer addressing, before any payload execution/allocation.
            live[ins['dst']] = math.prod(ins['shape']) * 8
            peak = max(peak, sum(live.values()))
            if peak > scratch_bytes:
                raise ValueError('finite VM scratch capacity exhausted')
            live = {name: size for name, size in live.items() if last.get(name, -1) > pc}
        vm = namespace['Machine'](program, payloads, div=div)
        outputs = vm.run()
        return {'outputs': outputs, 'events': vm.events, 'fault': vm.fault,
                'resident_tensor_bound_bytes': peak, 'source_sha256': source_sha256}
    if target != 'Qwen':
        raise ValueError('unsupported primitive VM target')
    # Qwen's module defines primitive helpers and its addressed storage class;
    # its __main__ compile/run path is never executed here.
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(ROOT / 'tools'))
        exec(compile(tree, str(snapshot), 'exec'), namespace)
    finally:
        sys.path[:] = old_path
    base = namespace['Machine']
    class BoundedMachine(base):
        def nodes(self, nodes, env, operation):
            for node in nodes:
                self.executed += 1
                if self.executed > instruction_limit:
                    raise ValueError('finite VM instruction capacity exhausted')
                if node['op'] == 'FOR':
                    start, stop, step = (int(self.value(node[k], env)) for k in ('start', 'stop', 'step'))
                    if start < 0 or stop < 0 or step <= 0:
                        raise ValueError('loop aperture')
                    if len(range(start, stop, step)) > instruction_limit - self.executed:
                        raise ValueError('finite VM loop capacity exhausted')
                    for index in range(start, stop, step):
                        env[node['var']] = index
                        self.nodes(node['body'], env, operation)
                else:
                    super().nodes([node], env, operation)
                size = sum(value.nbytes for value in env.values() if isinstance(value, np.ndarray))
                self.peak = max(self.peak, size)
                if size > scratch_bytes:
                    raise ValueError('finite VM scratch capacity exhausted')
    vm = BoundedMachine.__new__(BoundedMachine)
    vm.weights = weights; vm.storage = storage
    vm.lease_by_version = {}; vm.expression_cache = {}; vm.primitive_counts = Counter()
    vm.executed = 0; vm.peak = 0
    env = dict(payloads)
    if sum(v.nbytes for v in env.values() if isinstance(v, np.ndarray)) > scratch_bytes:
        raise ValueError('finite VM scratch capacity exhausted')
    # Loads/publication require explicit provider objects. Missing bindings
    # fail before instruction dispatch rather than silently installing fixtures.
    def check(nodes):
        for node in nodes:
            if node['op'] == 'FOR': check(node['body'])
            elif node['op'].startswith('LOAD_') and weights is None:
                raise ValueError('unbound native weight provider')
            elif node['op'] in {'BEGIN_WRITE', 'WRITE_BYTES', 'COMMIT_PUBLISH', 'ACQUIRE', 'READ_BYTES', 'CONSUMER_DONE'} and storage is None:
                raise ValueError('unbound native storage provider')
    check(program['recipe'])
    vm.nodes(program['recipe'], env, program)
    return {'outputs': {name: env[name] for name in program['outputs']},
            'primitive_counts': dict(vm.primitive_counts), 'executed_instructions': vm.executed,
            'resident_tensor_bound_bytes': vm.peak, 'source_sha256': source_sha256}


class Calendar:
    """Deterministic earliest-ready DAG scheduler, atomic all-resource admission.

    Slots are concrete finite credit identities. Each reservation holds them
    through final consumption/reverse-credit. Atomic admission removes circular
    hold-and-wait; DAG cycles and impossible requests are rejected, not timed out.
    """
    def __init__(self, capacities):
        self.capacities = {k: positive(v, k) for k, v in capacities.items()}
        self.slots = {k: [0] * v for k, v in self.capacities.items()}
        self.events = []
        self.ends = {}

    def add(self, name, deps, duration, resources, *, ready=0, **attrs):
        if name in self.ends:
            raise ValueError('duplicate event identity ' + name)
        positive(duration, name)
        if type(ready) is not int or ready < 0:
            raise ValueError('invalid ready cycle')
        if len(deps) != len(set(deps)) or any(d not in self.ends for d in deps):
            raise ValueError('unresolved dependency/deadlock ' + name)
        start = max([ready] + [self.ends[d] for d in deps])
        selected = {}
        for key, count in sorted(resources.items()):
            positive(count, key)
            if key not in self.slots or count > self.capacities[key]:
                raise ValueError('finite capacity exhausted: ' + key)
            choices = sorted(range(len(self.slots[key])), key=lambda i: (self.slots[key][i], i))[:count]
            selected[key] = choices
            start = max(start, *(self.slots[key][i] for i in choices))
        end = start + duration
        for key, slots in selected.items():
            for slot in slots:
                self.slots[key][slot] = end
        event = dict(id=name, deps=list(deps), start=start, end=end,
                     resources=selected, **attrs)
        self.events.append(event)
        self.ends[name] = end
        return name

    def dag(self, tasks):
        tasks = list(tasks)
        byid = {t['id']: t for t in tasks}
        if len(byid) != len(tasks):
            raise ValueError('duplicate task')
        indegree = {}; successors = defaultdict(list)
        for t in tasks:
            if len(t['deps']) != len(set(t['deps'])):
                raise ValueError('duplicate dependency')
            indegree[t['id']] = len(t['deps'])
            for dep in t['deps']:
                if dep not in byid:
                    raise ValueError('unknown dependency')
                successors[dep].append(t['id'])
        queue = [k for k, v in indegree.items() if not v]
        heapq.heapify(queue)
        while queue:
            key = heapq.heappop(queue); t = byid[key]
            self.add(key, t['deps'], t['duration'], t['resources'])
            for nxt in successors[key]:
                indegree[nxt] -= 1
                if not indegree[nxt]:
                    heapq.heappush(queue, nxt)
        if len(self.ends) != len(tasks):
            raise ValueError('dependency cycle/deadlock')
        return self.events


def verify_calendar(events, capacities):
    """Independent interval/credit and dependency proof; handles parallel events."""
    seen = {}; owners = defaultdict(list)
    for e in events:
        if e['id'] in seen or type(e['start']) is not int or e['start'] < 0 or e['end'] <= e['start']:
            raise ValueError('event identity/time')
        for dep in e['deps']:
            if dep not in seen or seen[dep]['end'] > e['start']:
                raise ValueError('premature consume/dependency')
        for key, slots in e['resources'].items():
            if key not in capacities or len(slots) != len(set(slots)):
                raise ValueError('unknown/duplicate resource')
            for slot in slots:
                if type(slot) is not int or not 0 <= slot < capacities[key]:
                    raise ValueError('finite capacity exhausted')
                owners[key, slot].append((e['start'], e['end'], e['id']))
        if 'repeats' in e:
            if positive(e['repeats'], 'repeats') * positive(e['stride'], 'stride') != e['end'] - e['start']:
                raise ValueError('batch interval inconsistent')
        if 'native_program' in e:
            verify_native_program(e['native_program'])
            if e['end'] - e['start'] != e['native_program']['duration']:
                raise ValueError('native enclosing reservation mismatch')
        seen[e['id']] = e
    for intervals in owners.values():
        ordered = sorted(intervals)
        if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('overlapping credit/port ownership')
    return {'events': len(events), 'resource_slots_used': len(owners),
            'dependency_edges': sum(len(e['deps']) for e in events),
            'status': 'PASS_FINITE_INTERVAL_PROOF'}


def verify_native_program(program):
    """Replay compressed primitive timing and finite scratch, independently."""
    def walk(nodes):
        offset = 0; counts = Counter()
        for node in nodes:
            if node['offset'] != offset:
                raise ValueError('native primitive ordering/offset')
            if node['kind'] == 'primitive':
                for name, value in node['stage_cycles'].items():
                    positive(value, name)
                if node['duration'] != sum(node['stage_cycles'].values()):
                    raise ValueError('native stage composition')
                credit = node['storage_credit']
                if credit['sector_credit'] != 1 or credit['read_ports'] > 2 or credit['write_ports'] != 1:
                    raise ValueError('native primitive finite capacity')
                if not node['rounding'] or not node['source_instruction'].get('op'):
                    raise ValueError('native arithmetic provenance')
                counts[node['op']] += node['batches128']
            elif node['kind'] == 'loop':
                if node['count'] < 0:
                    raise ValueError('negative loop trip count')
                duration, body_counts = walk(node['body'])
                expected = duration * node['count'] + node.get('control_cycles', node.get('explicit_empty_loop_control_cycles', 0))
                if node['duration'] != expected:
                    raise ValueError('native loop repetition/stride')
                counts.update({op: n * node['count'] for op, n in body_counts.items()})
            else:
                raise ValueError('native calendar node kind')
            positive(node['duration'], 'native duration'); offset += node['duration']
        return offset, counts
    duration, counts = walk(program['primitive_tree'])
    duration += program.get('empty_owned_extent_control_cycles', 0)
    if duration != program['duration']:
        raise ValueError('native recipe duration')
    live = []
    for home in program['scratch_homes'].values():
        lo = home['byte_offset']; size = home['buffer_bytes'] * home['buffers']
        if lo < 0 or lo % 512 or size % 512 or lo + size > program['finite_scratch_bytes']:
            raise ValueError('native scratch capacity')
        live.append((lo, lo + size))
    live.sort()
    if any(a[1] > b[0] for a, b in zip(live, live[1:])):
        raise ValueError('native scratch alias')
    return dict(counts)


def cycle_table(graphs, layouts):
    endpoints = {'admit', 'RF_read', 'RF_write_ACK', 'consume', 'retire',
                 'visibility_fence', 'HBM_read_sector', 'HBM_write_sector',
                 'forward_CDC', 'reverse_CDC', 'collective_sector', 'PACK_BF16',
                 'root_delivery', 'scalar_broadcast', 'matrix_stage', 'matrix_weight_sector',
                 'norm_collector_tail', 'norm_output_scale', 'external_stage', 'native:STAGE_OPERAND', 'owner_lookup', 'owner_held_accept', 'validated_reverse_grant'}
    for g in graphs.values():
        for o in g['operations']:
            endpoints.add('operator:' + o['opcode'])
            endpoints.update('provider:' + p for p in o['missing_native_endpoints'])
    for layout in layouts.values():
        for template in layout['selected_command_bindings']['command_templates'].values():
            endpoints.update('native:' + c['op'] for c in template)
    # These are deliberately explicit SOFTWARE estimates in abstract scheduler ticks.
    # Users may replace every value with calibrated endpoint inputs via --cycles.
    estimates = {'admit': 2, 'RF_read': 3, 'RF_write_ACK': 3, 'consume': 2,
                 'retire': 2, 'visibility_fence': 4, 'HBM_read_sector': 64,
                 'HBM_write_sector': 80, 'forward_CDC': 4, 'reverse_CDC': 4,
                 'collective_sector': 32, 'PACK_BF16': 8, 'root_delivery': 12,
                 'scalar_broadcast': 12, 'matrix_stage': 8, 'matrix_weight_sector': 64,
                 'owner_lookup': 12, 'owner_held_accept': 1, 'validated_reverse_grant': 4,
                 'norm_collector_tail': 512, 'norm_output_scale': 32, 'external_stage': 16}
    return {'schema': 'H3_EXPLICIT_ENDPOINT_CYCLES_V1', 'unit': 'abstract_software_tick',
            'calibration': 'PROVISIONAL_UNCALIBRATED', 'hardware_clock_claim': False,
            'values': {key: estimates.get(key, 32) for key in sorted(endpoints)},
            'basis': 'Explicit conservative software service estimates; provider/operator cost per 128-word tile; memory/collective per sector32; native per command; no CPU numerical oracle.'}


def validate_cycles(table, required):
    if table.get('unit') != 'abstract_software_tick' or table.get('hardware_clock_claim') is not False:
        raise ValueError('software cycle unit/clock scope')
    if table.get('calibration') not in ('PROVISIONAL_UNCALIBRATED', 'MEASURED_ENDPOINT_INPUTS'):
        raise ValueError('latency provenance missing')
    if table['calibration'] == 'MEASURED_ENDPOINT_INPUTS' and not table.get('measurement_pins'):
        raise ValueError('measured inputs require separate source pins')
    for key in required:
        positive(table.get('values', {}).get(key), key)


def version_homes(graph, layout, ranks):
    """Expand real rank groups; add finite persistent object/opaque homes explicitly."""
    homes = defaultdict(list)
    for h in layout['homes']:
        for rank in h['rank_group']:
            homes[h['version'], rank].append({k: v for k, v in h.items() if k != 'rank_group'})
    for v in graph['operands']:
        for rank in range(ranks):
            n = v['elements_per_rank'][rank]
            if not n or homes[v['id'], rank]:
                continue
            if v['bits_per_element'] == 0:
                home = {'class': 'publication', 'object': v['id'], 'bytes': 1}
            elif v['name'].startswith(('window.', 'compressed.', 'index_keys.', 'selected.')):
                home = {'class': 'persistent', 'object': v['name'],
                        'bytes': ceil(n * v['bits_per_element'], 8), 'byte_offset': 0}
            else:
                raise ValueError('unmapped version ' + v['id'])
            homes[v['id'], rank].append({'version': v['id'], 'name': v['name'], 'SM': 0,
                'birth_pc': v['birth_pc'], 'retire_pc': v['retire_pc'], 'home': home})
    return homes


def bind_provider_homes(provider, graph, fallback):
    if provider.get('schema') != 'opentallas.Qwen.provider-binding.v1':
        raise ValueError('provider binding schema')
    coverage = provider['coverage']
    if coverage['PCs'] != len(graph['operations']) or coverage['versions'] != len(graph['operands']) or coverage['unbound_versions']:
        raise ValueError('provider coverage')
    homes = defaultdict(list); refs = {}; release_at = defaultdict(list)
    versions = {v['id']: v for v in graph['operands']}
    for h in provider['version_homes']:
        if h['version'] not in versions or h['provider_ref'] in refs:
            raise ValueError('provider home/version identity')
        if h['birth_pc'] != versions[h['version']]['birth_pc'] or h['retire_pc'] != versions[h['version']]['retire_pc']:
            raise ValueError('provider lifetime mismatch')
        record = dict(h); record['name'] = versions[h['version']]['name']
        homes[h['version'], h['rank']].append(record); refs[h['provider_ref']] = h
        release_at[h['retire_pc']].append(h)
    for h in provider['control_homes']:
        if h['version'] not in versions or h['provider_ref'] in refs:
            raise ValueError('control provider identity')
        record = {'version': h['version'], 'name': versions[h['version']]['name'],
            'SM': 0, 'home': {'class': 'publication', 'object': h['version'], 'bytes': 1,
                'provider_extent': h['state_extent']}, 'provider_ref': h['provider_ref']}
        homes[h['version'], h['rank']].append(record); refs[h['provider_ref']] = h
    for key, entries in fallback.items():
        if entries and not homes[key]:
            raise ValueError('unbound provider version/rank')
    reuse = defaultdict(list); release_refs = {h['release_event']: h for h in provider['version_homes']}
    for edge in provider['reuse_dependencies']:
        if edge['new_home'] not in refs or edge['wait_release'] not in release_refs:
            raise ValueError('provider reuse dependency identity')
        new, old = refs[edge['new_home']], release_refs[edge['wait_release']]
        if old['retire_pc'] >= new['birth_pc']:
            raise ValueError('provider premature reuse')
        reuse[edge['new_home']].append(edge['wait_release'])
    operations = {}
    for p, op in zip(provider['operations'], graph['operations']):
        if p['pc'] != op['pc'] or p['opcode'] != op['opcode'] or p['source_dependencies'] != op['dependencies']:
            raise ValueError('provider PC/dependency mismatch')
        if set(p['inputs']) != set(op['reads']) or set(p['outputs']) != set(op['writes']):
            raise ValueError('provider PC operand mismatch')
        if any(ref not in refs for group in (p['inputs'], p['outputs']) for ids in group.values() for ref in ids):
            raise ValueError('unknown concrete provider reference')
        operations[p['pc']] = p
    if len(operations) != len(graph['operations']):
        raise ValueError('provider operation coverage')
    return homes, reuse, release_at, operations


def check_homes(homes, graph):
    values = {v['id']: v for v in graph['operands']}
    groups = defaultdict(list); persistent = defaultdict(list)
    for (vid, rank), entries in homes.items():
        if vid not in values:
            raise ValueError('unknown version home')
        for h in entries:
            p = h['home']; cls = p['class']
            if cls not in ('RF', 'spill', 'persistent', 'publication'):
                raise ValueError('home class')
            if cls == 'RF':
                lo, size = p['slot_first'], positive(p['vectors'], 'vectors')
                if lo < 32 or lo + size > 512:
                    raise ValueError('RF aperture/workspace capacity')
            elif cls == 'spill':
                lo, size = p['byte_offset'], positive(p['bytes'], 'spill bytes')
                if lo < 0 or lo % 512 or size % 512:
                    raise ValueError('spill alignment')
            elif cls == 'persistent':
                persistent[rank, p['object']].append((values[vid]['birth_pc'], values[vid]['retire_pc'], vid))
                continue
            else:
                continue
            groups[rank, h['SM'], cls].append((values[vid]['birth_pc'], values[vid]['retire_pc'], lo, lo + size, vid))
    for entries in groups.values():
        live = []
        for birth, retire, lo, hi, vid in sorted(entries):
            live = [x for x in live if x[0] >= birth]
            if any(lo < x[2] and x[1] < hi for x in live):
                raise ValueError('live home alias/premature write reuse ' + vid)
            live.append((retire, lo, hi, vid))
    for entries in persistent.values():
        ordered = sorted(entries)
        if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('persistent generation reused with future readers')
    return True


def extent_demands(layout):
    demands = []
    for binding in layout['spill_resident_bindings']:
        if not binding.get('fits', True):
            extent = binding['source_extent']; required = binding['required_bytes']
            demands.append({'rank_group': binding['rank_group'], 'class': 'activation_spill',
                'source_extent': extent, 'required_bytes': required,
                'additional_bytes': required - extent['bytes'], 'alignment_bytes': 512,
                'AW': binding['provider_ABI']['AW'],
                'status': 'CONSTRAINED_SUCCESSOR_EXTENT_REQUIRED',
                'constraints': ['nonalias with all checkpoint/KV/source extents',
                    'fulladdress end <= 2**AW', 'one distinct arena per rank; explicit SM subranges',
                    'all readers retired and reverse credit returned before address reuse'],
                'calendar_binding': 'logical successor arena; NOT an allocated source address'})
    return demands


class Shape:
    """Shape-only expressions. Never stores or evaluates numerical tensor data."""
    def __init__(self, shape=()):
        self.shape = tuple(int(n) for n in shape)
        if any(n < 0 for n in self.shape):
            raise ValueError('negative tensor extent')
    def __getitem__(self, key):
        keys = key if isinstance(key, tuple) else (key,)
        if Ellipsis in keys:
            missing = len(self.shape) - sum(k is not None and k is not Ellipsis for k in keys)
            keys = tuple(x for k in keys for x in ([slice(None)] * missing if k is Ellipsis else [k]))
        out = []; axis = 0
        for item in keys:
            if item is None:
                out.append(1); continue
            n = self.shape[axis]; axis += 1
            if isinstance(item, slice):
                out.append(len(range(*item.indices(n))))
            elif isinstance(item, Shape):
                out.extend(item.shape)
            elif not -n <= int(item) < n:
                raise ValueError('shape index aperture')
        return Shape(out + list(self.shape[axis:]))
    def binary(self, other):
        return Shape(broadcast(self.shape, other.shape if isinstance(other, Shape) else ()))
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = binary
    __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = __mod__ = __rmod__ = binary


def broadcast(*shapes):
    result = []
    for axis in range(1, max(map(len, shapes), default=0) + 1):
        sizes = {s[-axis] for s in shapes if len(s) >= axis} - {1}
        if len(sizes) > 1:
            raise ValueError('incompatible broadcast extents')
        result.append(next(iter(sizes), 1))
    return tuple(reversed(result))


def shape_reshape(value, shape):
    shape = list(shape); size = math.prod(value.shape)
    if shape.count(-1) > 1:
        raise ValueError('reshape inferred dimension')
    if -1 in shape:
        known = math.prod(n for n in shape if n != -1)
        if not known or size % known:
            raise ValueError('reshape extent')
        shape[shape.index(-1)] = size // known
    if math.prod(shape) != size:
        raise ValueError('reshape element count')
    return Shape(shape)


def shape_concat(values, axis=0):
    shapes = [as_shape(v).shape for v in values]; out = list(shapes[0]); axis %= len(out)
    for shape in shapes[1:]:
        if len(shape) != len(out) or any(a != b for i, (a, b) in enumerate(zip(out, shape)) if i != axis):
            raise ValueError('concat extent')
        out[axis] += shape[axis]
    return Shape(out)


def as_shape(value):
    if isinstance(value, Shape):
        return value
    if isinstance(value, (tuple, list)):
        return Shape((len(value),))
    return Shape()


def shape_expression(expr, env):
    expr = re.sub(r'np\.float64\(([-+0-9.eE]+)\)', r'\1', str(expr))
    tree = ast.parse(expr, mode='eval')
    allowed = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.Tuple, ast.List,
        ast.Subscript, ast.Slice, ast.Attribute, ast.Call, ast.BinOp, ast.UnaryOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError('non-shape expression ' + expr)
        if isinstance(node, ast.Attribute) and node.attr != 'shape':
            raise ValueError('shape expression attribute')
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in
                ('reshape', 'transpose', 'concat', 'zeros', 'arange', 'f32', 'int', 'min', 'max', 'pow2ceil', 'log2ceil', 'bitlength')):
            raise ValueError('non-shape call: ' + expr)
    helpers = {'reshape': shape_reshape,
        'transpose': lambda v: Shape(tuple(reversed(v.shape))), 'concat': shape_concat,
        'zeros': lambda s: Shape(s), 'arange': lambda n: Shape((n,)),
        'f32': lambda n: Shape(), 'int': lambda n: n if isinstance(n, int) else Shape(),
        'min': min, 'max': max, 'pow2ceil': lambda n: 1 << (max(1,int(n))-1).bit_length(),
        'log2ceil': lambda n: (max(1,int(n))-1).bit_length(), 'bitlength': lambda n: int(n).bit_length()}
    return eval(compile(tree, '<shape-only-native-index>', 'eval'), {'__builtins__': {}, **helpers}, env)


def normalize_bundle(data):
    if data.get('schema') == 'opentallas.H3.qwen-complete-native-software.v1':
        return {**data, 'target': 'Qwen'}
    if data.get('schema') == 'H3_DEEPSEEK_COMPLETE_NATIVE_V1':
        operations = []; sequences = {}
        for op in data['instructions']:
            groups = defaultdict(list)
            for binding in op['rank_bindings']:
                if not binding.get('empty_owned_extent'):
                    # Final DS exports one actual recipe per gathered buffer.
                    # The primary recipe is an extent preview, not an additional
                    # executable buffer when explicit buffer_programs are present.
                    keys = tuple(b['template'] for b in binding.get('buffer_programs', [])) or (binding['template'],)
                    groups[keys].append(binding['rank'])
            programs = []
            for keys, ranks in groups.items():
                if keys not in sequences:
                    code = []; counts = Counter(); outputs = {}
                    for index, key in enumerate(keys):
                        template = data['templates'][key]
                        prefix = f'buffer{index}_' if len(keys) > 1 else ''
                        for instruction in template['code']:
                            code.append({**instruction, 'dst': prefix + instruction['dst'],
                                'src': [prefix + v for v in instruction['src']]})
                        outputs.update({prefix + name: prefix + symbol for name, symbol in template['outputs'].items()})
                        counts.update(template['resources'].get('instruction_batches128_by_opcode', {}))
                    sequences[keys] = {'instructions': code, 'outputs': outputs,
                        'expected_primitive_batches': dict(counts),
                        'source_template': hashlib.sha256(encode(keys)).hexdigest()}
                programs.append({**sequences[keys], 'rank_group': ranks,
                    'source_templates': list(keys),
                    'providers': {key: op['provider_bindings'][key] for key in keys},
                    'resources': {key: data['templates'][key]['resources'] for key in keys}})
            operations.append({**op, 'opcode': op['family'], 'programs': programs,
                'reads': [v['version'] for v in op['reads']], 'writes': [v['version'] for v in op['writes']]})
        return {**data, 'target': 'DeepSeek', 'operations': operations}
    return data


def bundle_primitives(data):
    if data.get('schema') == 'H3_ORDERED_NATIVE_LOWERING_V1':
        return {step['op'] for op in data['operations'] for step in op['steps']}
    result = set()
    def walk(nodes):
        for node in nodes:
            result.add(node['op'])
            walk(node.get('body', [])); walk(node.get('exact_template', []))
    for op in data['operations']:
        if 'recipe' in op:
            walk(op['recipe'])
        else:
            for program in op.get('programs', []):
                walk(program['instructions'])
    return result


def validate_bundle(native, graph):
    if len(native['operations']) != len(graph['operations']):
        raise ValueError('native bundle PC coverage')
    for plan, op in zip(native['operations'], graph['operations']):
        if plan['pc'] != op['pc'] or plan.get('opcode', plan.get('family')) != op['opcode']:
            raise ValueError('native bundle PC identity')
        if plan['reads'] != op['reads'] or plan['writes'] != op['writes']:
            raise ValueError('native bundle version mismatch')
        if 'recipe' not in plan and 'programs' not in plan:
            raise ValueError('native bundle instructions missing')


def bind_recipe(native, plan, macro, rank, table, workspace=None):
    """Instruction-dependent ordered nested calendar; loops remain lossless RLE.

    Every primitive serially consumes at most two RF read ports, one write port,
    one finite sector credit and one of 32 lane engines. Source temporaries use
    a finite double-buffered logical scratch arena, sized by this binding. It is
    a constrained successor allocation if the existing scratch extent is short.
    """
    costs = table['values']; env = {}; buffers = {}; stats = Counter(); serial = [0]
    source = native.get('source_program', {})
    version_shapes = {v['version']: v['shape'] for v in native.get('operands', []) if 'version' in v and 'shape' in v}
    version_names = {v['version']: v.get('name', '') for v in native.get('operands', []) if 'version' in v}
    context = source.get('context_capacity', 8192)
    env['position'] = context - 1
    for i, vid in enumerate(macro['reads']):
        shape = version_shapes.get(vid)
        if shape is not None:
            env[f'input{i}'] = Shape([context if n == 'position+1' else n for n in shape])
            if version_names.get(vid) == 'position':
                env[f'input{i}'] = context - 1
            if macro['opcode'] == 'ARGMAX_REDUCE':
                env[f'input{i}'] = Shape((2,))
    exported_allocations = plan.get('temporary_storage', {}).get('allocations')
    workspace_homes = ({symbol: workspace['homes'][plan['pc'], rank, symbol]
                        for symbol in exported_allocations} if workspace and exported_allocations else {})
    highword_symbols = {symbol for symbol, home in workspace_homes.items() if home.get('semantic_bits') == 64}
    element_bytes = 4 if exported_allocations else 8
    def register(name, shape):
        if name:
            name = name.split('[')[0]
            size = max(element_bytes, element_bytes * math.prod(shape))
            buffers[name] = max(buffers.get(name, 0), ceil(size, 512) * 512)
    for key, val in env.items():
        if isinstance(val, Shape):
            register(key, val.shape)
    def primitive(node, local_env, path):
        op = node['op']; src = node.get('src', []); dst = node.get('dst')
        rounding = node.get('round_point', node.get('rounding'))
        if not rounding:
            rounding = 'FP32_RNE_then_positive_zero' if op in ('FADD', 'FMUL') else 'explicit native instruction contract'
        if any(k in node for k in ('callback', 'handler', 'golden_callback')):
            raise ValueError('native callback forbidden')
        args = [shape_expression(x, local_env) for x in src]
        if 'shape' in node:
            result = Shape(node['shape'])
        elif op == 'LOAD_WEIGHT':
            d = source['weight_descriptors'][node['key']]; result = Shape((d['rows'], d['K']))
        elif op == 'LOAD_EMBED_CODES':
            result = Shape((source['config']['hidden_size'],))
        elif op == 'LOAD_EMBED_SCALE':
            result = Shape()
        elif op == 'LOAD_GAMMA':
            result = Shape((source['config']['head_dim'] if node.get('kind') != 'final' else source['config']['hidden_size'],))
        elif op in ('LOAD_ROPE_COS', 'LOAD_ROPE_SIN'):
            result = Shape((source['config']['head_dim'] // 2,))
        elif op == 'LOAD_SCALE':
            d = source['weight_descriptors'][node['key']]; result = Shape((d['rows'],))
        elif op == 'READ_BYTES':
            result = as_shape(args[-1])
        elif op in ('BEGIN_WRITE', 'ACQUIRE', 'BIND_LEASE', 'COMMIT_PUBLISH', 'CONSUMER_DONE'):
            result = Shape()
        else:
            result = Shape(broadcast(*(as_shape(a).shape for a in args))) if args else Shape()
        if op == 'MOV' and args:
            result = as_shape(args[0])
        name = dst.split('[')[0] if dst else None
        if name:
            if '[' in dst:
                # Destination scatter is a costed materialization under its full lease.
                if name not in local_env:
                    raise ValueError('scatter destination uninitialized')
                register(name, as_shape(local_env[name]).shape)
            else:
                if op != 'STAGE_OPERAND' or not isinstance(local_env.get(name), int):
                    local_env[name] = result
                register(name, result.shape)
        batches = max(1, ceil(math.prod(result.shape), 128))
        read_batches = sum(max(1, ceil(math.prod(as_shape(a).shape) * element_bytes, 512)) for a in args)
        write_batches = max(1, ceil(math.prod(result.shape) * element_bytes, 512)) if dst else 1
        # A source recipe may have three-input SELECT or CONCAT. Decompose RF
        # operand reads into serial pairs, retaining values in the finite arena.
        operand_pairs = max(1, ceil(len(args), 2))
        stages = {'admit': costs['admit'], 'RF_read': costs['RF_read'] * max(read_batches, operand_pairs),
            'execute': costs['native:' + op] * batches,
            'RF_write_ACK': costs['RF_write_ACK'] * write_batches,
            'consume': costs['consume'], 'retire': costs['retire']}
        # All temporaries are explicitly scratch-backed. No invisible limitless RF.
        sectors = 16 * (read_batches + write_batches)
        ownership = 2 * (costs['owner_lookup'] + costs['owner_held_accept'])
        read_sectors, write_sectors = 16 * read_batches, 16 * write_batches
        stages['scratch_read'] = max(1, read_sectors) * (costs['HBM_read_sector'] + ownership +
            costs['forward_CDC'] + costs['consume'] + costs['reverse_CDC'] + costs['validated_reverse_grant'] + costs['retire'])
        stages['scratch_write'] = write_sectors * (costs['HBM_write_sector'] + ownership +
            costs['visibility_fence'] + costs['forward_CDC'] + costs['consume'] + costs['reverse_CDC'] +
            costs['validated_reverse_grant'] + costs['retire'])
        high_reads = []
        for text, arg in zip(src, args):
            names = {n.id for n in ast.walk(ast.parse(text, mode='eval')) if isinstance(n, ast.Name)}
            touched = sorted(names & highword_symbols)
            if touched:
                high_reads.append({'symbols': touched, 'sectors32': max(1, ceil(math.prod(as_shape(arg).shape) * 4, 32))})
        high_write = max(1, ceil(math.prod(result.shape) * 4, 32)) if name in highword_symbols else 0
        if high_reads:
            stages['I64_highword_read'] = sum(r['sectors32'] for r in high_reads) * costs['I64_highword_read_sector']
            stages['I64_join'] = costs['I64_split_join'] * sum(max(1, ceil(r['sectors32'], 16)) for r in high_reads)
        if high_write:
            stages['I64_split'] = costs['I64_split_join'] * max(1, ceil(high_write, 16))
            # Conservative sector RMW for every upper-word write, including
            # partial words/scatters. Adjacent packed owners are never clobbered.
            stages['I64_RMW_read'] = high_write * costs['I64_highword_read_sector']
            stages['I64_RMW_merge'] = costs['I64_RMW_merge'] * max(1, ceil(high_write, 16))
            stages['I64_highword_write_visible'] = high_write * costs['I64_highword_write_sector']
        if op.startswith('LOAD') or op in ('WRITE_BYTES', 'READ_BYTES', 'PACKET_COMMIT'):
            stages['provider_visibility'] = max(1, ceil(math.prod(result.shape) * element_bytes, 32)) * (
                costs['HBM_write_sector' if op in ('WRITE_BYTES', 'PACKET_COMMIT') else 'HBM_read_sector'] +
                costs['visibility_fence'] + ownership + costs['validated_reverse_grant'])
        index = serial[0]; serial[0] += 1; stats[op] += batches
        return {'kind': 'primitive', 'index': index, 'op': op, 'source_instruction': node,
            'rounding': rounding, 'shape': list(result.shape), 'batches128': batches, 'scratch_element_bytes': element_bytes,
            'RF_read_batches': read_batches, 'RF_write_batches': write_batches,
            'operand_pair_reads': operand_pairs, 'storage_sectors32': sectors, 'scratch_read_sectors32': read_sectors, 'scratch_write_sectors32': write_sectors,
            'owner_lookup_edges_per_sector': 2 * costs['owner_lookup'],
            'owner_accept_edges_per_sector': 2 * costs['owner_held_accept'],
            'validated_reverse_grant_cycles': costs['validated_reverse_grant'],
            'stage_cycles': stages, 'duration': sum(stages.values()),
            'version_identity': ['event.target', 'event.pc', 'event.rank', path, index, 'loop_iteration_tuple'],
            'read_symbols': src, 'write_symbol': dst,
            'I64_highword_reads': high_reads, 'I64_highword_write_sectors32': high_write,
            'I64_conservative_RMW_sectors32': high_write,
            'storage_credit': {'sector_credit': 1, 'read_ports': 2, 'write_ports': 1,
                               'lanes': 128, 'double_buffer_versions': 2}}
    def walk(nodes, local_env, path=()):
        out = []; offset = 0
        for i, node in enumerate(nodes):
            if node['op'] in ('FOR', 'SUM_TEMPLATE'):
                if node['op'] == 'FOR':
                    start = shape_expression(node['start'], local_env); stop = shape_expression(node['stop'], local_env)
                    step = shape_expression(node['step'], local_env); count = len(range(start, stop, step))
                    local_env[node['var']] = start; body = node['body']
                else:
                    start = 0; step = 1; count = 1; body = node['exact_template']
                if count == 0:
                    record = {'kind': 'loop', 'count': 0, 'body': [], 'duration': costs['admit'],
                              'explicit_empty_loop_control_cycles': costs['admit']}
                else:
                    groups = [(start, count)]
                    if node['op'] == 'FOR' and node['var'] == 'tree_level':
                        groups = [(index, 1) for index in range(start, stop, step)]
                    elif node['op'] == 'FOR' and node['var'] == 'g' and count > 1:
                        groups = [(start, count - 1), (start + step * (count - 1), 1)]
                    elif node['op'] == 'FOR' and node['var'] == 's':
                        knode = next((n for n in body if n['op'] == 'FOR' and n['var'] == 'k'), None)
                        if knode:
                            groups = []; last_trip = None
                            for index in range(start, stop, step):
                                local_env[node['var']] = index
                                bounds = [shape_expression(knode[k], local_env) for k in ('start', 'stop', 'step')]
                                trip = len(range(*bounds))
                                if trip != last_trip:
                                    groups.append([index, 1]); last_trip = trip
                                else:
                                    groups[-1][1] += 1
                    segments = []; total = 0
                    for index, repeat in groups:
                        if node['op'] == 'FOR':
                            local_env[node['var']] = index
                        children, duration = walk(body, local_env, path + (i, index))
                        segment = {'kind': 'loop', 'count': repeat, 'iteration_start': index,
                            'iteration_step': step, 'iteration_stride': duration, 'body': children,
                            'duration': duration * repeat + costs['admit'], 'control_cycles': costs['admit'],
                            'offset': total, 'ordering': 'iteration-major exact body order'}
                        segments.append(segment); total += segment['duration']
                    record = {'kind': 'loop', 'count': 1, 'body': segments, 'duration': total + costs['admit'],
                        'control_cycles': costs['admit'], 'source_loop_count': count,
                        'ordering': 'contiguous source iteration groups; shrinking trees and tail extents explicit'}
                    if node['op'] == 'FOR':
                        local_env[node['var']] = start + step * (count - 1)
            else:
                record = primitive(node, local_env, path + (i,))
            record['offset'] = offset; offset += record['duration']; out.append(record)
        return out, offset
    if 'recipe' in plan:
        nodes = plan['recipe']
    else:
        programs = plan['programs']; program = next((p for p in programs if rank in p['rank_group']), None)
        if program is None:
            return {'schema': 'H3_ORDERED_PRIMITIVE_CALENDAR_V1', 'duration': costs['admit'],
                'primitive_tree': [], 'finite_scratch_bytes': 0, 'scratch_homes': {},
                'empty_owned_extent_control_cycles': costs['admit'], 'no_tensor_value_evaluation': True}
        nodes = program['instructions']
        definitions = set()
        for node in nodes:
            if any(v not in definitions for v in node['src']):
                raise ValueError('Peirce SSA premature consume')
            if node['dst'] in definitions:
                raise ValueError('Peirce SSA duplicate write')
            definitions.add(node['dst'])
        for node in nodes:
            # DS instructions use SSA symbol references, not expression callbacks.
            if node['op'] == 'LOAD':
                env[node['dst']] = Shape(node['shape'])
    prefix = [{'op': 'STAGE_OPERAND', 'dst': name, 'src': [name],
        'round_point': 'bit-exact source version movement; no arithmetic',
        'version': macro['reads'][int(name[5:])], 'source': 'macro RF/persistent read landing'}
        for name in list(env) if name.startswith('input') and name[5:].isdigit()]
    tree, duration = walk(prefix + nodes, env)
    arena = {}; cursor = 0; producer_homes = {}
    if exported_allocations:
        for name, allocation in exported_allocations.items():
            home = allocation['home']; producer_homes[name] = allocation
            if home['class_'] == 'spill':
                size = ceil(allocation['bytes'], 512) * 512
                arena[name] = {'byte_offset': home['byte_offset'], 'buffer_bytes': size, 'buffers': 1,
                    'base_by_rank': home['base_by_rank'], 'version': allocation['version'],
                    'lease': allocation['lease'], 'release_after': allocation['release_after']}
                cursor = max(cursor, home['byte_offset'] + size)
            elif home['class_'] == 'RF':
                if any(not 3 <= slot < 32 for slot in home['vector_slots']):
                    raise ValueError('producer native workspace RF aperture')
            else:
                raise ValueError('producer native temporary home class')
        if cursor != plan['temporary_storage']['spill_bytes']:
            raise ValueError('producer native scratch extent mismatch')
    else:
        for name, size in sorted(buffers.items()):
            arena[name] = {'byte_offset': cursor, 'buffer_bytes': size, 'buffers': 2,
                           'version_buffer': 'iteration-local producer parity; read old parity before mirrored ACK switch'}
            cursor += 2 * size
    result = {'schema': 'H3_ORDERED_PRIMITIVE_CALENDAR_V1', 'duration': duration,
        'primitive_tree': tree, 'finite_scratch_bytes': cursor, 'scratch_homes': arena,
        'producer_temporary_homes': producer_homes,
        'workspace_provider_homes': workspace_homes,
        'producer_counts_full_context': plan.get('calendar_counts_full_context'),
        'producer_native_finite_export': plan.get('calendar_export', {}).get('schema'),
        'source_arithmetic': macro['golden_contract'], 'source_recipe_sha256': hashlib.sha256(encode(nodes)).hexdigest(),
        'provider_refs': native.get('provider_requirements', 'Peirce LOAD/provider program descriptors'),
        'storage_scope': 'finite logical successor arena per rank; does not alias source scratch',
        'scratch_layout': ('producer finite RF/refill/spill allocations consumed exactly; no independently sized double buffers' if exported_allocations else
            '8 bytes per logical element: F32/U32 lowword plus padded highword; I64 retains both32bit words; two RF staging vectors per128 logical values'),
        'no_tensor_value_evaluation': True}
    if 'programs' in plan and program.get('expected_primitive_batches'):
        expected = program['expected_primitive_batches']
        observed = verify_native_program(result)
        if observed != expected:
            raise ValueError('DS producer primitive count mismatch at PC' + str(plan['pc']))
        result['producer_vector_count_gate'] = 'PASS_EXACT_EXPORTED_NATIVE_COUNTS'
        result['producer_expected_primitive_batches'] = expected
        result['producer_source_templates'] = program['source_templates']
    if plan.get('calendar_counts_full_context'):
        expected = {op: counts['native_vector_beats'] for op, counts in
                    plan['calendar_counts_full_context']['by_primitive'].items()}
        observed = verify_native_program(result)
        if any(observed.get(op, 0) != count for op, count in expected.items()):
            raise ValueError('producer native vector count mismatch at PC' + str(plan['pc']))
        result['producer_vector_count_gate'] = 'PASS_EXACT_EXPORTED_NATIVE_COUNTS'
    return result



def validate_native_lowering(native, graph, homes, ranks):
    """Worker interchange: every PC and concrete ordered two-source native steps.

    Each step has rank, SM, op, repeats, reads=[{version,slot}],
    writes=[{version,slot}], rounding, provider_refs, and source_arithmetic.
    Macro inputs initialize their concrete slots. Constants need explicit
    provider descriptors, which create costed staging steps. Local versions may
    reuse a slot only after their last listed read. No callback is executable.
    """
    if native.get('schema') != 'H3_ORDERED_NATIVE_LOWERING_V1':
        raise ValueError('native lowering schema')
    operations = native.get('operations', [])
    if len(operations) != len(graph['operations']):
        raise ValueError('native lowering must cover every PC')
    plans = {}
    for plan, macro in zip(operations, graph['operations']):
        if plan.get('pc') != macro['pc'] or plan.get('opcode') != macro['opcode']:
            raise ValueError('native PC identity/order')
        if plan.get('operand_versions') != {'reads': macro['reads'], 'writes': macro['writes']}:
            raise ValueError('native operand version mismatch')
        if not plan.get('source_arithmetic') or not plan.get('rounding') or not plan.get('provider_refs'):
            raise ValueError('native arithmetic/provider contract missing')
        steps = plan.get('steps', [])
        if not steps:
            raise ValueError('native steps missing')
        state = {}; last = {}; definitions = set()
        for i, step in enumerate(steps):
            for ref in step.get('reads', []):
                last[step['rank'], step['SM'], ref['version']] = i
        for rank in macro['participants']:
            for vid in macro['reads']:
                for h in homes[vid, rank]:
                    if h['home']['class'] == 'RF':
                        p = h['home']
                        for slot in range(p['slot_first'], p['slot_first'] + p['vectors']):
                            state[rank, h['SM'], slot] = vid
        for i, step in enumerate(steps):
            rank, sm = step['rank'], step['SM']
            if rank not in macro['participants'] or not 0 <= sm < 32:
                raise ValueError('native step owner')
            if not step.get('op') or any(k in step for k in ('callback', 'golden', 'handler')):
                raise ValueError('native callback/opcode forbidden')
            positive(step['repeats'], 'native repeats')
            if not step.get('rounding') or not step.get('provider_refs') or not step.get('source_arithmetic'):
                raise ValueError('native step provenance')
            if len(step['reads']) > 2 or len(step['writes']) > 1:
                raise ValueError('native two-source port capacity')
            for ref in step['reads'] + step['writes']:
                if type(ref['slot']) is not int or not 0 <= ref['slot'] < 512:
                    raise ValueError('native slot aperture')
            for ref in step['reads']:
                key = rank, sm, ref['slot']
                if state.get(key) != ref['version']:
                    raise ValueError('native stale/unpublished input')
            for ref in step['writes']:
                key = rank, sm, ref['slot']; old = state.get(key)
                if old is not None and last.get((rank, sm, old), -1) > i:
                    raise ValueError('native premature write reuse')
                ident = rank, sm, ref['version']
                if ident in definitions:
                    raise ValueError('native duplicate version')
                definitions.add(ident); state[key] = ref['version']
        plans[plan['pc']] = plan
    return plans


def bind_workspace_intervals(workspace, events, pcs, native_plans):
    """Bind R20 addresses to actual admission/retirement fence intervals.

    An entire PC holds the finite workspace lease. All native primitive traffic,
    including upper-word transactions, occurs inside the ordered nested program.
    No source mismatch, review arena, or physical ACK is silently adopted.
    """
    byid = {e['id']: e for e in events}
    allocations = {r['rank']: r for r in workspace['join']['rank_allocation']}
    intervals = []; rank_leases = defaultdict(list); seen = set()
    for pc in pcs:
        plan = native_plans[pc['pc']]
        for rank in pc['participants']:
            start = byid[pc['admit']]['start']; end = byid[pc['retire']]['end']
            rank_leases[rank].append((start, end, pc['pc']))
            regions = []; slots = []
            for symbol, allocation in plan['temporary_storage']['allocations'].items():
                key = pc['pc'], rank, symbol; seen.add(key)
                home = workspace['homes'][key]; source = allocation['home']
                if (home['version'] != allocation['version'] or home['lease'] != allocation['lease'] or
                        home['bytes'] != allocation['bytes'] or home['release_after'] != f"PC{pc['pc']}.retire"):
                    raise ValueError('workspace version/lease/retire binding mismatch')
                if home['class_'] == 'RF_workspace':
                    if source['class_'] != 'RF' or home['slots'] != source['vector_slots']:
                        raise ValueError('workspace RF source mismatch')
                    slots.extend(home['slots'])
                else:
                    expected = source['base_by_rank'][str(rank)] + source['byte_offset']
                    if source['class_'] != 'spill' or home['base'] != expected:
                        raise ValueError('workspace physical base source mismatch')
                    regions.append((home['base'], home['end_exclusive']))
                    extent = next(e for e in allocations[rank]['extents'] if e['name'] == 'native_workspace')
                    if not extent['base'] <= home['base'] < home['end_exclusive'] <= extent['base'] + extent['bytes']:
                        raise ValueError('workspace finite extent exhausted')
                if home.get('semantic_bits') == 64:
                    extent = next(e for e in allocations[rank]['extents'] if e['name'] == 'native_I64_highword_codec_sidecar')
                    lo = home['highword_base']; hi = lo + home['highword_reserved_bytes']
                    if not extent['base'] <= lo < hi <= extent['base'] + extent['bytes']:
                        raise ValueError('workspace I64 sidecar extent exhausted')
                    regions.append((lo, hi))
                intervals.append({'pc': pc['pc'], 'rank': rank, 'symbol': symbol,
                    'home': home, 'start': start, 'end': end, 'admit_event': pc['admit'],
                    'retire_event': pc['retire'], 'release_guard': home['release_guard'],
                    'I64_software_codec_implemented': home.get('semantic_bits') == 64,
                    'physical_codec_admitted': False,
                    'iteration_identity': ['session64', 'PC', 'rank', 'symbol', 'definition', 'loop_iteration_tuple'],
                    'write_visibility': 'priced provisional causal fence; actual physical event is unqualified'})
            regions.sort()
            if any(a[1] > b[0] for a, b in zip(regions, regions[1:])) or len(slots) != len(set(slots)):
                raise ValueError('workspace alias within live PC lease')
    if seen != set(workspace['homes']):
        raise ValueError('workspace provider coverage mismatch')
    for leases in rank_leases.values():
        leases.sort()
        if any(a[1] > b[0] for a, b in zip(leases, leases[1:])):
            raise ValueError('premature workspace lease reuse')
    return intervals, {'status': 'PASS_CONCRETE_SOFTWARE_WORKSPACE_INTERVALS',
        'temporary_home_count': len(intervals), 'rank_PC_leases': sum(map(len, rank_leases.values())),
        'final_native_source_match': True,
        'older_calendar_source_mismatch_preserved': not workspace['join']['final_native_calendar_source_match'],
        'review_candidate_arena_adopted': False, 'physical_or_clock_admission': False,
        'I64_software_codec': 'LE lower/upper32; equal owner/definition/iteration; two visible writes before publication',
        'I64_physical_codec_implemented': False}


def compile_target(target, graph, layout, table, native=None, providers=None, workspace=None):
    ranks = 2 if target == 'Qwen' else 96
    homes = version_homes(graph, layout, ranks); check_homes(homes, graph)
    values = {v['id']: v for v in graph['operands']}
    reuse = defaultdict(list); release_at = defaultdict(list); provider_ops = {}
    if providers:
        homes, reuse, release_at, provider_ops = bind_provider_homes(providers, graph, homes)
        check_homes(homes, graph)
    bundled = native and native.get('schema') != 'H3_ORDERED_NATIVE_LOWERING_V1'
    native_plans = ({o['pc']: o for o in native['operations']} if bundled else
                    validate_native_lowering(native, graph, homes, ranks) if native else {})
    if bundled:
        validate_bundle(native, graph)
    selected = {b['pc']: b for b in layout['selected_command_bindings']['bindings']}
    caps = {'global.collective': 1}
    for r in range(ranks):
        caps.update({f'r{r}.{k}': n for k, n in [('issue', 1), ('collective', 1), ('HBM', 1),
            ('sector_credit', 4), ('ACK_capture', 4), ('forward_CDC', 4), ('reverse_CDC', 4),
            ('RMW_lock', 4), ('opcode_context', 4), ('owner_lookup', 1), ('owner_context', 4)]})
        for sm in range(32):
            caps.update({f'r{r}.s{sm}.{k}': n for k, n in [('RF', 1), ('read_port', 2),
                ('write_port', 1), ('execute', 1), ('packing_queue', 2), ('root_FIFO', 2),
                ('shared_workspace', 1)]})
    scratch_peaks = Counter(); primitive_counts = Counter(); programs = {}; recipe_cache = {}
    cal = Calendar(caps); cost = table['values']; pcs = []; visible = {}; last_reader = {}; terminal = {}; last_pc = None
    persistent_owner = {}

    def stage(name, deps, endpoint, resources, units=1, **attrs):
        units = positive(units, name + '.units')
        return cal.add(name, list(dict.fromkeys(deps)), cost[endpoint] * units, resources,
                       endpoint=endpoint, repeats=units, stride=cost[endpoint], **attrs)

    def transfer(name, deps, h, rank, write):
        p = h['home']; sm = h['SM']; rr = f'r{rank}'; ss = rr + f'.s{sm}'
        if write and providers:
            deps = list(deps) + reuse.get(h.get('provider_ref'), [])
            if any(d not in cal.ends for d in deps):
                raise ValueError('provider home reuse before release')
        if p['class'] == 'RF':
            resources = {ss + '.RF': 1, ss + ('.write_port' if write else '.read_port'): 1}
            endpoint = 'RF_write_ACK' if write else 'RF_read'; units = p['vectors']
        elif p['class'] in ('spill', 'persistent'):
            resources = {rr + '.HBM': 1, rr + '.sector_credit': 1, rr + '.forward_CDC': 1,
                         rr + '.ACK_capture': 1, rr + '.RMW_lock': 1, rr + '.reverse_CDC': 1,
                         rr + '.owner_lookup': 1, rr + '.owner_context': 1}
            endpoint = 'HBM_write_sector' if write else 'HBM_read_sector'; units = ceil(p['bytes'], 32)
        else:
            resources = {rr + '.opcode_context': 1}; endpoint = 'consume'; units = 1
        event = stage(name, deps, endpoint, resources, units, version=h['version'], rank=rank,
                      SM=sm, home=p, provider_ref=h.get('provider_ref'),
                      request_identity={'version': h['version'], 'rank': rank, 'SM': sm, 'serial': name,
                          'repeat_sector_ordinal': 'repeat_index', 'epoch': 'token_session',
                          'quarantine': 'compound consumer+reverse+validated grant retirement'},
                      direction='write' if write else 'read')
        # HBM transport slots above stay owned across the full compound sequence.
        # Repeat stride explicitly includes backing visibility, consumer completion
        # and reverse CDC. It never purports to be an actual DUT completion event.
        if p['class'] in ('spill', 'persistent'):
            e = cal.events[-1]
            owner_cycles = 2 * (cost['owner_lookup'] + cost['owner_held_accept'])
            extra = owner_cycles + sum(cost[k] for k in ('forward_CDC', 'consume', 'reverse_CDC', 'validated_reverse_grant', 'retire'))
            if write:
                extra += cost['visibility_fence']
            e['stride'] += extra; e['end'] += extra * units
            e['phases_per_repeat'] = {'service': cost[endpoint], 'forward_CDC': cost['forward_CDC'],
                'consume': cost['consume'], 'reverse_CDC': cost['reverse_CDC'], 'retire': cost['retire'],
                'owner_lookup': 2 * cost['owner_lookup'], 'owner_held_accept': 2 * cost['owner_held_accept'],
                'validated_reverse_grant': cost['validated_reverse_grant']}
            if write:
                e['phases_per_repeat']['backing_visibility_fence'] = cost['visibility_fence']
            cal.ends[event] = e['end']
            for key, slots in e['resources'].items():
                for slot in slots:
                    cal.slots[key][slot] = e['end']
        return event

    # External values are scheduled provider inputs, never magically visible.
    for v in graph['operands']:
        if not v['external_source']:
            continue
        for rank in range(ranks):
            entries = homes[v['id'], rank]
            if not entries:
                continue
            prev = stage(f'input.{v["id"]}.r{rank}', [], 'external_stage', {f'r{rank}.issue': 1}, version=v['id'])
            ends = [transfer(f'{prev}.h{i}', [prev], h, rank, True) for i, h in enumerate(entries)]
            visible[v['id'], rank] = stage(prev + '.visible', ends, 'visibility_fence', {f'r{rank}.issue': 1})
            for h in entries:
                if h['home']['class'] == 'persistent':
                    persistent_owner[rank, h['home']['object']] = visible[v['id'], rank]

    # Source ordering is retained: macro dependencies include previous-PC retire.
    # Independent SM chains inside each macro overlap only on disjoint resources.
    for op in graph['operations']:
        pc = op['pc']; prefix = f'pc{pc}'; participants = op['participants']
        if not participants or len(participants) != len(set(participants)) or any(r not in range(ranks) for r in participants):
            raise ValueError('participant/rendezvous identity')
        deps = []
        for dep in op['dependencies']:
            if dep not in terminal:
                raise ValueError('PC dependency deadlock')
            deps.append(terminal[dep])
        if last_pc:
            deps.append(last_pc)
        admitted = stage(prefix + '.admit', deps, 'admit', {f'r{r}.issue': 1 for r in participants}, pc=pc)
        reads = []; read_by_rank = defaultdict(list)
        for vid in op['reads']:
            if vid not in values:
                raise ValueError('unknown read version')
            for rank in participants:
                for i, h in enumerate(homes[vid, rank]):
                    if (vid, rank) not in visible:
                        raise ValueError('unpublished/premature read ' + vid)
                    e = transfer(f'{prefix}.read.{vid}.r{rank}.h{i}', [admitted, visible[vid, rank]], h, rank, False)
                    reads.append(e); read_by_rank[rank].append(e); last_reader[vid, rank] = e
        collective = op['opcode'] in ('ALL_REDUCE', 'ARGMAX_REDUCE', 'all_gather', 'all_reduce', 'topk_merge', 'kv_gather')
        executions = []; collective_ready = admitted
        if collective and pc in native_plans:
            resources = {'global.collective': 1, **{f'r{r}.collective': 1 for r in participants}}
            collective_ready = stage(prefix + '.collective_admit', reads + [admitted], 'collective_sector',
                resources, max(1, ceil(sum(ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                    for v in op['reads'] for r in participants), 32)),
                atomic_rendezvous=True, participants=participants, phase='ordered source delivery before native consumption',
                golden_contract=op['golden_contract'])
        if pc in native_plans and bundled:
            for rank in participants:
                plan = native_plans[pc]
                if 'programs' in plan:
                    template = next((p for p in plan['programs'] if rank in p['rank_group']), None)
                    cache_key = template['source_template'] if template else 'empty_extent'
                else:
                    cache_key = f'Qwen.pc{pc}' + (f'.rank{rank}' if workspace else '')
                if cache_key not in recipe_cache:
                    recipe = bind_recipe(native, plan, op, rank, table, workspace)
                    counts = verify_native_program(recipe)
                    key = hashlib.sha256(cache_key.encode()).hexdigest()[:24]
                    programs[key] = recipe
                    recipe_cache[cache_key] = key, counts
                key, counts = recipe_cache[cache_key]; recipe = programs[key]
                primitive_counts.update(counts)
                scratch_peaks[rank] = max(scratch_peaks[rank], recipe['finite_scratch_bytes'])
                rr = f'r{rank}'
                resources = {rr + '.HBM': 1, rr + '.sector_credit': 1, rr + '.ACK_capture': 1,
                    rr + '.forward_CDC': 1, rr + '.reverse_CDC': 1, rr + '.opcode_context': 1,
                    rr + '.owner_lookup': 1, rr + '.owner_context': 1}
                for sm in range(32):
                    resources.update({rr + f'.s{sm}.RF': 1, rr + f'.s{sm}.execute': 1,
                        rr + f'.s{sm}.read_port': 2, rr + f'.s{sm}.write_port': 1,
                        rr + f'.s{sm}.shared_workspace': 1})
                executions.append(cal.add(f'{prefix}.r{rank}.native_recipe',
                    list(dict.fromkeys(read_by_rank[rank] + [collective_ready])), recipe['duration'], resources,
                    native_program_ref=key, native_source_PC=pc, pc=pc, rank=rank,
                    operand_versions={'reads': op['reads'], 'writes': op['writes']},
                    concrete_provider_operation=provider_ops.get(pc),
                    native_provider_bindings_ref=str(pc) if target == 'DeepSeek' else None,
                    policy='exclusive finite rank lease; ordered primitive calendar below; no internal ideal overlap'))
        elif pc in native_plans:
            plan = native_plans[pc]; chains = {}
            for index, step in enumerate(plan['steps']):
                rank, sm = step['rank'], step['SM']; ss = f'r{rank}.s{sm}'
                previous = [chains[rank, sm]] if (rank, sm) in chains else read_by_rank[rank] + [collective_ready]
                stem = f'{prefix}.native{index}'
                issued = stage(stem + '.issue', previous, 'admit', {ss + '.execute': 1}, native_step=step)
                read = stage(stem + '.consume', [issued], 'RF_read', {ss + '.RF': 1, ss + '.read_port': max(1, len(step['reads']))}, step['repeats'])
                execute = stage(stem + '.execute', [read], 'native:' + step['op'], {ss + '.execute': 1}, step['repeats'])
                write = stage(stem + '.commit', [execute], 'RF_write_ACK', {ss + '.RF': 1, ss + '.write_port': 1}, step['repeats'])
                chains[rank, sm] = stage(stem + '.retire', [write], 'retire', {ss + '.execute': 1})
            executions.extend(chains.values())
        elif pc in selected:
            b = selected[pc]; templates = layout['selected_command_bindings']['command_templates']; roots = defaultdict(list)
            for binding in b['participant_commands']:
                for rank in binding['rank_group']:
                    if rank not in participants:
                        raise ValueError('native participant outside macro')
                    sm = binding['SM']; ss = f'r{rank}.s{sm}'; previous = list(read_by_rank[rank]) + [admitted]
                    previous = [stage(f'{prefix}.r{rank}.s{sm}.constants', previous, 'external_stage',
                        {ss + '.RF': 1, ss + '.write_port': 1},
                        max(1, len(binding['coefficient_constant_provider_preconditions'])),
                        provider_preconditions=binding['coefficient_constant_provider_preconditions'])]
                    template = templates[binding['command_template']]
                    for command in template:
                        ci = command['command_index']; stem = f'{prefix}.r{rank}.s{sm}.cmd{ci}'
                        issued = stage(stem + '.issue', previous, 'admit', {ss + '.execute': 1}, command=command)
                        consumed = stage(stem + '.consume', [issued], 'RF_read', {ss + '.RF': 1, ss + '.read_port': 2})
                        ran = stage(stem + '.execute', [consumed], 'native:' + command['op'], {ss + '.execute': 1})
                        committed = stage(stem + '.commit', [ran], 'RF_write_ACK', {ss + '.RF': 1, ss + '.write_port': 1})
                        previous = [stage(stem + '.retire', [committed], 'retire', {ss + '.execute': 1})]
                    roots[rank].append(stage(f'{prefix}.r{rank}.s{sm}.root', previous, 'root_delivery',
                        {ss + '.root_FIFO': 1, f'r{rank}.s0.RF': 1, f'r{rank}.s0.write_port': 1},
                        source_RF_slot=binding['root_RF_slot'], root_version=binding['root_version'],
                        collector_lane=sm, closed_delivery_fence=True))
            for rank in participants:
                if not roots[rank]:
                    raise ValueError('missing root participant')
                tail = stage(f'{prefix}.r{rank}.collector', roots[rank], 'norm_collector_tail',
                    {f'r{rank}.s0.RF': 1, f'r{rank}.s0.execute': 1},
                    golden_contract=op['golden_contract'], root_order=sorted(x['SM'] for x in b['participant_commands'] if rank in x['rank_group']))
                for sm in sorted({h['SM'] for vid in op['writes'] for h in homes[vid, rank]}):
                    delivered = stage(f'{prefix}.r{rank}.s{sm}.scalar', [tail], 'scalar_broadcast',
                        {f'r{rank}.s{sm}.root_FIFO': 1, f'r{rank}.s{sm}.RF': 1})
                    executions.append(stage(f'{prefix}.r{rank}.s{sm}.scale', [delivered], 'norm_output_scale',
                        {f'r{rank}.s{sm}.execute': 1}))
        elif collective:
            resources = {'global.collective': 1}
            resources.update({f'r{r}.collective': 1 for r in participants})
            bytes_ = sum(ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                         for v in op['reads'] for r in participants)
            executions.append(stage(prefix + '.rendezvous', reads + [admitted], 'collective_sector',
                resources, max(1, ceil(bytes_, 32)), participants=participants,
                atomic_rendezvous=True, golden_contract=op['golden_contract'],
                ordered_source_ranks=participants, payload_bytes=bytes_))
        else:
            for rank in participants:
                previous = list(read_by_rank[rank]) + [admitted]
                units = max(1, ceil(max(sum(values[v]['elements_per_rank'][rank] for v in op['reads']),
                                       sum(values[v]['elements_per_rank'][rank] for v in op['writes'])), 128))
                for index, endpoint in enumerate(op['missing_native_endpoints']):
                    is_memory = any(s in endpoint.lower() for s in ('hbm', 'provider', 'packed', 'fetch', 'visible'))
                    resources = {f'r{rank}.opcode_context': 1,
                                 f'r{rank}.HBM' if is_memory else f'r{rank}.s0.execute': 1}
                    previous = [stage(f'{prefix}.r{rank}.provider{index}', previous, 'provider:' + endpoint,
                        resources, units, golden_contract=op['golden_contract'],
                        source_binding=op.get('external_bindings', op['source']))]
                executions.append(stage(f'{prefix}.r{rank}.execute', previous, 'operator:' + op['opcode'],
                    {f'r{rank}.s0.execute': 1, f'r{rank}.opcode_context': 1}, units,
                    source_operation=op['source'], golden_contract=op['golden_contract'],
                    implementation='parameterized software endpoint; numerical execution separate'))
        if collective and pc in native_plans:
            resources = {'global.collective': 1, **{f'r{r}.collective': 1 for r in participants}}
            executions = [stage(prefix + '.rendezvous', executions + reads + [admitted],
                'collective_sector', resources, max(1, ceil(sum(
                    ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                    for v in op['reads'] for r in participants), 32)),
                atomic_rendezvous=True, participants=participants, golden_contract=op['golden_contract'])]
        consumed = stage(prefix + '.consume', executions + reads + [admitted], 'consume',
                         {f'r{r}.issue': 1 for r in participants}, pc=pc)
        commits = []
        for vid in op['writes']:
            if vid not in values or values[vid]['birth_pc'] != pc:
                raise ValueError('wrong write version producer')
            for rank in range(ranks):
                entries = homes[vid, rank]
                destination_admit = consumed
                if entries and rank not in participants:
                    destination_admit = stage(f'{prefix}.delivery.r{rank}.{vid}', [consumed], 'admit', {f'r{rank}.issue': 1},
                        source_ranks=participants, destination_rank=rank)
                for i, h in enumerate(entries):
                    p = h['home']; extra = []
                    if p['class'] == 'persistent' and (rank, p['object']) in persistent_owner:
                        extra.append(persistent_owner[rank, p['object']])
                    # RF/spill reuse obeys inclusive static lifetime check and previous
                    # macro retirement; old consumer and reverse credits have drained.
                    event = transfer(f'{prefix}.write.{vid}.r{rank}.h{i}', [destination_admit] + extra, h, rank, True)
                    commits.append(event)
                if entries:
                    fence = stage(f'{prefix}.visible.{vid}.r{rank}', commits[-len(entries):],
                        'visibility_fence', {f'r{rank}.issue': 1}, version=vid, rank=rank)
                    visible[vid, rank] = fence; commits.append(fence)
                    for h in entries:
                        if h['home']['class'] == 'persistent':
                            persistent_owner[rank, h['home']['object']] = fence
        last_pc = stage(prefix + '.retire', commits + [consumed], 'retire',
                        {f'r{r}.issue': 1 for r in participants}, pc=pc)
        terminal[pc] = last_pc
        for h in release_at.get(pc, []):
            stage(h['release_event'], [last_pc, visible[h['version'], h['rank']]], 'validated_reverse_grant',
                {f'r{h["rank"]}.issue': 1}, provider_ref=h['provider_ref'],
                requires=h['release_requires'], source_consumers=h['consumers'])
        pcs.append({'pc': pc, 'opcode': op['opcode'], 'participants': participants,
                    'admit': admitted, 'consume': consumed, 'commit_fences':
                    [e for e in commits if '.visible.' in e], 'retire': last_pc,
                    'read_versions': op['reads'], 'write_versions': op['writes'],
                    'native_commands': pc in selected or pc in native_plans, 'atomic_collective': collective})
    proof = verify_calendar(cal.events, caps)
    for e in cal.events:
        if 'native_program_ref' in e and e['end'] - e['start'] != programs[e['native_program_ref']]['duration']:
            raise ValueError('native enclosing reservation duration')
    demands = [] if providers else extent_demands(layout)
    workspace_layout = {p['rank']: p for p in (native or {}).get('storage', {}).get('software_provider_layout', [])}
    for rank, size in sorted(scratch_peaks.items()):
        if size:
            demands.append({'rank_group': [rank], 'class': 'native_temporary_scratch',
                'required_bytes': size, 'alignment_bytes': 512, 'additional_bytes': size,
                'required_minimum_AW': max(1, (size - 1).bit_length()),
                'source_provider_AW': 34 if target == 'Qwen' else 27,
                'source_provider_address_width_fits': size <= 2**(34 if target == 'Qwen' else 27),
                'status': 'CONSTRAINED_SUCCESSOR_EXTENT_REQUIRED',
                'constraints': ['distinct from all version spill, checkpoint and persistent extents',
                    'capacity >= maximum bound recipe arena; no modulo alias',
                    'producer allocation leases retire before workspace reuse; conservative fallback buffers drain before reuse'],
                'calendar_binding': ('producer concrete software base and lease; physical residence unqualified' if rank in workspace_layout else
                                     'finite logical arena; resident physical base needs provider binding'),
                'producer_workspace_layout': workspace_layout.get(rank),
                'bounded_tiled_allocation': False,
                'admission_scope': 'outside retained source spill extent; software workspace reservation only'})
    persistent_caps = {}
    for (vid, rank), entries in homes.items():
        for h in entries:
            if h['home']['class'] == 'persistent':
                key = f'r{rank}:' + h['home']['object']
                persistent_caps[key] = max(persistent_caps.get(key, 0), h['home']['bytes'])
    workspace_intervals = []; workspace_proof = None
    if workspace:
        workspace_intervals, workspace_proof = bind_workspace_intervals(workspace, cal.events, pcs, native_plans)
    return {'schema': 'H3_COMPLETE_NATIVE_SOFTWARE_CALENDAR_V1', 'target': target,
        'status': ('PASS_COMPLETE_NATIVE_SOFTWARE_CALENDAR' if len(native_plans) == len(pcs) else
                   'PASS_MACRO_RESERVATION_INTERMEDIATE'), 'PC_count': len(pcs), 'PCs': pcs,
        'native_lowering_PC_count': len(native_plans),
        'native_operator_lowering_complete': len(native_plans) == len(pcs),
        'ordinary_native_lowering_gap_PCs': [p['pc'] for p in pcs if p['pc'] not in native_plans and not p['native_commands']],
        'events': cal.events, 'resources': caps, 'proof': proof,
        'native_primitive_batch_counts': dict(sorted(primitive_counts.items())),
        'native_programs': programs,
        'native_provider_bindings_by_PC': {str(pc): plan['provider_bindings'] for pc, plan in native_plans.items()
                                           if 'provider_bindings' in plan},
        'native_primitive_count_gate': ('PASS_ALL_PC_EXPORTED_COUNTS' if native_plans and
            all(p.get('producer_vector_count_gate') == 'PASS_EXACT_EXPORTED_NATIVE_COUNTS'
                for p in programs.values() if p['primitive_tree']) else 'NOT_ALL_EXPORTED_COUNT_CHECKS_AVAILABLE'),
        'workspace_provider_intervals': workspace_intervals, 'workspace_provider_proof': workspace_proof,
        'version_home_archive': ('Qwen_provider_binding.json.gz' if providers else DISTRIBUTED + '/' + target + '.json.gz'),
        'provider_binding_coverage': providers['coverage'] if providers else None,
        'provider_resource_contract': providers['resource_contract'] if providers else None,
        'cycles': cal.ends[last_pc], 'cycle_unit': table['unit'],
        'latency_calibration': table['calibration'], 'hardware_clock_claim': False,
        'physical_base_and_lease_bindings_complete': False,
        'software_schedule_coverage_scope': 'all source PCs and actual instruction expansions; physical bases/leases remain separate admission',
        'RTL_or_physical_admission': False, 'CPU_numerical_oracle_cycles': False,
        'source_backed_extent_admission': not bool(demands), 'constrained_extent_successors': demands,
        'home_binding': 'actual provider lookup when supplied; otherwise exact distributed RF/spill homes; persistent finite logical objects, physical bases separate gate',
        'persistent_object_capacities': persistent_caps,
        'provisional_endpoint_scope': 'All macro providers and ordinary operators have explicit tile service reservations. Selected native templates expand command-by-command. Generic endpoints are parameterized software providers, not hardware implementation claims.'}


def load_inputs():
    manifest = read_json(ROOT / LOWERING / 'manifest.json')
    for path, digest in manifest['outputs'].items():
        if hashlib.sha256((ROOT / LOWERING / path).read_bytes()).hexdigest() != digest:
            raise ValueError('lowering input pin mismatch: ' + path)
    graphs = {t: read_json(ROOT / LOWERING / (t + '.json.gz')) for t in ('Qwen', 'DeepSeek')}
    layouts = {t: read_json(ROOT / DISTRIBUTED / (t + '.json.gz')) for t in graphs}
    return graphs, layouts


def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def run_bounded_provider_join(directory, out, *, layers=36, verify=False):
    """Portable executable milestone; no old large-calendar regeneration."""
    import numpy as np
    base=Path(directory); out=Path(out); N,K=load_bounded_provider_sources(base)
    original=read_json(base/'Qwen_tiled.json.gz')
    graph=read_json(base/'sources/results/uarch/h3_versioned_lowering_20261002/Qwen.json.gz')
    full=audit_bounded_export(original,graph)
    ds=read_json(base/'ds/forward_dispatch_milestone.json.gz'); dsproof=audit_ds_bounded_dispatch(ds)
    dsprogram=ROOT/OUT/'final_ds_bed325f89/program_final.json.gz'
    if hashlib.sha256(dsprogram.read_bytes()).hexdigest()!=ds['source_program_sha256']:
        raise ValueError('DS bounded source program pin mismatch')
    config=dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
        intermediate_size=16,vocab_size=16,num_hidden_layers=layers,rms_norm_eps=1e-6,rope_theta=1000000)
    native=N.compile_tiled(N.compile_program(config,context=32,groups=16)); positions=[(3,0),(5,1)]
    def bits(value):
        if isinstance(value,dict): return {k:bits(v) for k,v in value.items()}
        if isinstance(value,tuple): return [bits(v) for v in value]
        a=np.asarray(value)
        return {'shape':list(a.shape),'dtype':a.dtype.str,'bits':a.tobytes().hex()}
    expected=N.TiledMachine(native); references={}; reference_results=[]; pos=[0]
    def record(op,store):
        references[pos[0],op['pc']]={v:bits(store.debug_snapshot(v)) for v in op['writes']}
    for token,position in positions:
        pos[0]=position; reference_results.append(expected.run(token,position,record))
    backend=AddressedTileByteBackend(K,native);seed_bounded_fixture(N,backend,native,[p for _,p in positions])
    snapshots=[]; seen=[0]
    def compare(op,store):
        position=positions[seen[0]//len(native['operations'])][1]
        observed={v:bits(store.debug_snapshot(v)) for v in op['writes']}
        if observed!=references[position,op['pc']]: raise ValueError('post-commit output bits mismatch PC'+str(op['pc']))
        snapshots.append({'pc':op['pc'],'position':position,'sha256':hashlib.sha256(encode(observed)).hexdigest()})
        seen[0]+=1
    execution=execute_bounded_provider_program(N,K,native,backend,positions=positions,observer=compare)
    if [e['next_token'] for e in execution['executions']]!=[e['next_token'] for e in reference_results]:
        raise ValueError('bounded provider token mismatch')
    execution['post_commit_all_output_bits']='PASS_EXACT_PINNED_NATIVE_EXECUTOR_REFERENCE'
    execution['post_commit_output_snapshots']=snapshots
    execution['reference_scope']='test-only native primitive executor, no golden callback or numerical CPU time in costs'
    old=ROOT/OUT/'workspace_r20_33b741b4e/calendar_r1/manifest.json'
    oldmanifest=read_json(old)
    existing={'manifest_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
        'I64_highword_read_sector':oldmanifest['endpoint_cycles']['values']['I64_highword_read_sector'],
        'I64_highword_write_sector':oldmanifest['endpoint_cycles']['values']['I64_highword_write_sector'],
        'I64_split_join':oldmanifest['endpoint_cycles']['values']['I64_split_join'],
        'I64_RMW_merge':oldmanifest['endpoint_cycles']['values']['I64_RMW_merge'],
        'r22_augmentation_applied':False,'existing_calendar_mutated':False,
        'bounded_Qwen_additional_temporary_HBM_bytes':0,
        'old_2801511424_byte_workspace_scope':'retained baseline only; not inherited by bounded export',
        'R21_read_sector_ticks':108,'R21_write_sector_ticks':128,
        'difference_to_parent_sector_cost':'2 admission ticks, explicit in R21 service; no additive second codec charge',
        'R20_intervals':'retained baseline allocation proof; bounded RF I64 uses two32bit words, optional realPC14 codec tested separately',
        'source_interval_join':'same actual graph versions and PC dependencies; old macro times do not qualify the new instruction counts'}
    outputs={'Qwen_all_PC_bindings.json.gz':full,'Qwen_provider_execution.json.gz':execution,
             'DS_bounded_reservation.json.gz':dsproof,'cost_reconciliation.json':existing}
    if not verify: out.mkdir(parents=True,exist_ok=False)
    hashes={}
    for name,value in outputs.items():
        raw=encode(value); data=gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw+b'\n'
        path=out/name
        if verify:
            if path.read_bytes()!=data: raise ValueError('bounded join replay mismatch '+name)
        else: path.write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest()
    pins=read_json(base/'producer_pins.json')['files']
    manifest={'schema':'H3_BOUNDED_PROVIDER_JOIN_MILESTONE_V1','source_pins':pins,
        'consumer_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'output_sha256':hashes,'Qwen_fullshape_PCs':full['PCs'],'Qwen_families':full['classes'],
        'Qwen_executed_fixture_PCs_per_token':len(native['operations']),'Qwen_fixture_layers':layers,
        'Qwen_executed_tokens':len(positions),'Qwen_fixture_next_tokens':[e['next_token'] for e in execution['executions']],
        'DS_bounded_PCs':dsproof['PCs'],'DS_families':dsproof['families'],
        'DS_scope':dsproof['status'],'full_token_checkpoint_quality':False,'hardware_clock_admission':False,
        'existing_cost_reconciliation':existing,
        'remaining_gaps':['DS rank workspace physical bases/leases and checkpoint routes unbound',
            'DS ordered wholeprogram addressed microVM execution pending; bounded dispatch service reservation intermediate',
            'Qwen fullshape checkpoint token execution not demonstrated by reduced36layer raw fixtures',
            'Measured RF/HBM/NoC/shared/native/collective costs separate calibration gate',
            'KeplerR21 lacks IOTA; DS complete generic addressed microVM requires bounded IOTA binding'],
        'replay':f'python tools/h3_complete_native_calendar.py --bounded-provider-join {directory} --bounded-layers {layers} --out {out} --verify'}
    path=out/'manifest.json'; raw=encode(manifest)+b'\n'
    if verify:
        if path.read_bytes()!=raw: raise ValueError('bounded join manifest replay mismatch')
    else: path.write_bytes(raw)
    print(json.dumps({k:manifest[k] for k in ('Qwen_fullshape_PCs','Qwen_executed_fixture_PCs_per_token',
        'Qwen_fixture_next_tokens','DS_bounded_PCs','DS_families','hardware_clock_admission')}))
    print('PASS_BOUNDED_SOURCE_PINNED_PROVIDER_JOIN_REPLAY' if verify else 'PASS_BOUNDED_PROVIDER_JOIN_MILESTONE')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / OUT)
    ap.add_argument('--cycles', type=Path)
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--native-lowering', type=Path, action='append', default=[])
    ap.add_argument('--qwen-providers', type=Path)
    ap.add_argument('--qwen-workspace', type=Path)
    ap.add_argument('--target', choices=('Qwen', 'DeepSeek'), action='append')
    ap.add_argument('--bounded-provider-join', type=Path)
    ap.add_argument('--bounded-layers', type=int, default=36)
    ap.add_argument('--ds-native-stage-calendar', type=Path)
    ap.add_argument('--ds-stage-bindings', type=Path)
    ap.add_argument('--ds-stage-workspace', type=Path)
    ap.add_argument('--ds-stage-rank', type=int, default=0)
    ap.add_argument('--h4-cost-join', type=Path)
    ap.add_argument('--ds-full-program-cost',type=Path)
    ap.add_argument('--ds-full-native-source',type=Path)
    ap.add_argument('--ds-shared-bridge',type=Path)
    ap.add_argument('--ds-shared-bridge-source',type=Path)
    ap.add_argument('--ds-shared-bridge-commit')
    ap.add_argument('--ds-native-source-commit')
    ap.add_argument('--ds-forward-leaves',action='store_true')
    ap.add_argument('--provider-v1-join',action='store_true')
    ap.add_argument('--ds-r33-calendar-source-join',action='store_true')
    ap.add_argument('--ds-r33-once-reprice',action='store_true')
    ap.add_argument('--portable-inputs',type=Path)
    ap.add_argument('--ds-r34-group-reprice',action='store_true')
    ap.add_argument('--r34-source-commit',default='0b4ab421b')
    ap.add_argument('--r33-cost-baseline',type=Path)
    ap.add_argument('--export-portable-inputs',action='store_true')
    ap.add_argument('--r33-parent-commit',default='ce132ffea40cf31f1af9d8c7af696d5e57125213')
    ap.add_argument('--r33-boundary-cycles',type=Path)
    ap.add_argument('--r33-source-commit',default='433ccff91c9ed6f0e61761bdbffa11f4878d6339')
    ap.add_argument('--tp96-collective-inputs',type=Path)
    ap.add_argument('--tp96-endpoint-cycles',type=Path)
    ap.add_argument('--v1-source-commit',default='f7fa8e290d419f6de3356385c0b55ded768c2090')
    ap.add_argument('--v1-physical-source-commit',default='620c078de78cc55ddb5562b1d5d7171d8ef944ca')
    ap.add_argument('--kepler-source-commit',default='f240f42fbeb67e402e922b4a4aae30b8a8873ce1')
    ap.add_argument('--mtp-source-commit',default='5b71cd17cebe109a1dab6141aa2812bd6f02b2a8')
    ap.add_argument('--parent-state-receipts',type=Path)
    ap.add_argument('--c0-source-commit')
    args = ap.parse_args()
    global PORTABLE_INPUTS
    PORTABLE_INPUTS=args.portable_inputs
    if args.export_portable_inputs:
        index=export_calendar_portable_inputs(args.out)
        print(json.dumps({k:v for k,v in index.items() if k!='inputs'},sort_keys=True));return
    if args.ds_r34_group_reprice:
        if args.r33_cost_baseline is None:raise ValueError('current r33 once-repriced baseline required')
        pins={}
        def blob(path,commit):
            raw=pinned_calendar_blob(path,commit);pins[path]=dict(commit=commit,sha256=hashlib.sha256(raw).hexdigest());return raw
        raw=blob('results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz','91e3b8cc2791fa3fe1322df3d72b3f76dbd184f6')
        original=json.loads(gzip.decompress(raw))
        # Eight-group correction is independent of the40 r33 window changes;
        # retain the current r33 interval ledger and require exact producer input.
        record=json.loads(blob('results/uarch/ds_hbm_source_inputs_views_r34_20261002/prepared_join.json',args.r34_source_commit))
        baseline_manifest=read_json(args.r33_cost_baseline/'manifest.json')
        receipt=read_json(args.r33_cost_baseline/'once_reprice_receipt.json')
        if (record['native_input_sha256']!=receipt['native_sha256'] or
            record['dispatch_input_sha256']!=receipt['dispatch_sha256']):raise ValueError('r34 producer/current r33 source mismatch')
        previous=read_json(args.r33_cost_baseline/'all_PC_native_component_successor.json.gz')
        expected=baseline_manifest['output_sha256']['all_PC_native_component_successor.json.gz']
        immutable_baseline=json.loads(blob(OUT+'/ds_r33_once_reprice_r1/model/manifest.json','4e8f517fc'))
        if expected!=immutable_baseline['output_sha256']['all_PC_native_component_successor.json.gz']:
            raise ValueError('r34 requires exact reviewed r33 baseline cost pin')
        if hashlib.sha256((args.r33_cost_baseline/'all_PC_native_component_successor.json.gz').read_bytes()).hexdigest()!=expected:
            raise ValueError('current r33 cost baseline bytes mismatch')
        inventory=compile_ds_r34_group_source(original,blob('tools/ds_hbm_group_provider_r34.py',args.r34_source_commit),record['group_PCs'])
        model=json.loads(blob('results/uarch/h4_v1_g0_model_20261002/intake/run/model.json','f7fa8e290d419f6de3356385c0b55ded768c2090'))
        scalar=32;c0=22
        successor,summary=reprice_ds_r34_groups(previous,inventory,model,scalar,c0)
        successor['DeepSeek']['source_program_sha256']=record['native_output_sha256']
        successor['current_r34_dispatch_sha256']=record['dispatch_output_sha256']
        successor['current_r34_C0_source_catalog_binding']=None
        inventory.update(source_native_sha256=record['native_output_sha256'],source_dispatch_sha256=record['dispatch_output_sha256'])
        summary.update(source_native_sha256=record['native_output_sha256'],source_dispatch_sha256=record['dispatch_output_sha256'],
            status='PASS_SOURCE_RESOLVED_GROUP_COST_REPLACEMENT_ACTUAL_MOVEMENT_UNKNOWN',
            materialized_native_workspace_bytes_per_call=record['materialized_group_workspace_bytes_conservative'],
            software_scratch_capacity_per_rank=record['software_scratch_capacity_per_rank'],
            physical_shared_scratch_bytes_per_SM=65536,bounded_group_operand_span_schedule=None,
            actual_parent_movement_journals=None,source_initial_windows_provenance='seeded reference state, not decoded prefix',
            literal_TP96_64B_geometry_replaced=False,wide_product_rate=None)
        artifacts={'summary.json':summary,'source_inventory.json.gz':inventory,'all_PC_native_component_successor.json.gz':successor}
        raws={n:((gzip.compress((json.dumps(v,sort_keys=True,indent=2)+'\n').encode(),mtime=0)) if n.endswith('.gz')
            else (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()) for n,v in artifacts.items()}
        manifest=dict(schema='H4_R34_SOURCE_COST_SUCCESSOR_MANIFEST_V1',source_pins=pins,
            r33_baseline_component_sha256=expected,r33_baseline_receipt_sha256=hashlib.sha256((args.r33_cost_baseline/'once_reprice_receipt.json').read_bytes()).hexdigest(),
            explicit_provisional_costs=dict(native_nonV1_scalar=scalar,C0_command=c0,V1='retained upper typed profiles'),
            tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            output_sha256={n:hashlib.sha256(v).hexdigest() for n,v in raws.items()},
            full_program_dynamic_movement=False,hardware_admitted=False)
        raws['manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
        if not args.verify:args.out.mkdir(parents=True,exist_ok=False)
        for name,raw in raws.items():
            if args.verify:
                if (args.out/name).read_bytes()!=raw:raise ValueError('r34 source-cost replay mismatch '+name)
            else:(args.out/name).write_bytes(raw)
        print(json.dumps({k:v for k,v in summary.items() if k!='records'},sort_keys=True));print('PASS_R34_GROUP_REPLAY' if args.verify else 'PASS_R34_GROUP_REPRICE');return
    if args.ds_r33_once_reprice:
        if args.r33_boundary_cycles is None:raise ValueError('explicit provisional boundary cycle table required')
        pins={}
        def pinned_record(path,commit):
            raw=pinned_calendar_blob(path,commit)
            pins[path]=dict(commit=commit,sha256=hashlib.sha256(raw).hexdigest())
            return json.loads(gzip.decompress(raw) if path.endswith('.gz') else raw)
        base=OUT+'/ds_r33_calendar_adapter_r1/provider_final/'
        records={n:pinned_record(base+n,'2e76d4f96') for n in (
            'source_count_adapter.json.gz','r33_current_catalog.json.gz','r33_source_overlay.json.gz','r33_window_provider_join.json.gz')}
        parent_base='results/uarch/h4_c0_r33_source_adapter_20261002/r1/model/'
        parent=pinned_record(parent_base+'source_adapter.json',args.r33_parent_commit)
        parent_catalog=pinned_record(parent_base+'source_catalog.json.gz',args.r33_parent_commit)
        old=pinned_record(OUT+'/provider_v1_mtp_join_r4/final_physical/V1_native_component_successor.json.gz','a67150839')
        scalar=pinned_record(OUT+'/ds_forward_leaf_join_r3/review/summary.json','781046c9')['retained_baseline_provisional_costs']['primitive_scalar']
        a,cat,o,provider=[records[n] for n in ('source_count_adapter.json.gz','r33_current_catalog.json.gz','r33_source_overlay.json.gz','r33_window_provider_join.json.gz')]
        successor,receipt=compose_ds_r33_once_reprice(a,cat,o,provider,parent,parent_catalog,old,scalar)
        boundary=reserve_ds_r33_initial_loads(a,cat,o,provider,read_json(args.r33_boundary_cycles))
        reset=pinned_record('results/uarch/native_software_parent_intake_20261002/Qwen_reset_source_parent_review.json',args.r33_parent_commit)
        summary=dict(schema='H4_R33_ONCE_ONLY_CALENDAR_AND_INPUT_RESERVATION_V1',DS_PCs=2213,Qwen_PCs=1737,
            changed_PCs=len(receipt['changed_PC_witnesses']),window_rank_calls=len(boundary['bindings']),
            current_known_subledger_software_ticks=receipt['current_known_subledger_software_ticks'],
            critical_path_software_tick_delta=receipt['critical_path_software_tick_delta'],
            shared_unknown_calls=successor['DeepSeek']['unknown_shared_template_calls'],
            boundary_phase_unit_totals=boundary['phase_unit_totals'],
            boundary_costs_added_to_known_subledger=False,C0_V1_I64_and_mirrors_recharged=False,
            current_C0_catalog_sha256=receipt['catalog_sha256'],complete_service_software_ticks=None,
            reset_context=dict(model='Qwen_ROM',source_tile_reset_bits=reset['complete_tile_async_reset_bits'],
                source_tile_clock_bits=reset['complete_tile_clock_bits'],HBM_runtime_cost_added=False,
                physical_reset_or_CTS_proven=reset['root_protocol_physically_proven']),
            hardware_admitted=False,status='PASS_ONCE_ONLY_SOURCE_COST_REPRICE_FINITE_INPUT_RESERVATION_PARTIAL')
        artifacts={'summary.json':summary,'once_reprice_receipt.json':receipt,
            'all_PC_native_component_successor.json.gz':successor,'initial_LOAD_boundary_reservations.json.gz':boundary}
        raw_records={n:((gzip.compress((json.dumps(v,sort_keys=True,indent=2)+'\n').encode(),mtime=0)) if n.endswith('.gz')
            else (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()) for n,v in artifacts.items()}
        manifest=dict(schema='H4_R33_ONCE_ONLY_CALENDAR_MANIFEST_V1',source_pins=pins,
            tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            cycle_input_sha256=hashlib.sha256(args.r33_boundary_cycles.read_bytes()).hexdigest(),
            output_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in raw_records.items()},
            source_bulk_duplicated=False,hardware_admitted=False)
        raw_records['manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
        if not args.verify:args.out.mkdir(parents=True,exist_ok=False)
        for name,raw in raw_records.items():
            if args.verify:
                if (args.out/name).read_bytes()!=raw:raise ValueError('once reprice replay mismatch '+name)
            else:(args.out/name).write_bytes(raw)
        print(json.dumps(summary,sort_keys=True));print('PASS_R33_ONCE_REPRICE_REPLAY' if args.verify else 'PASS_R33_ONCE_REPRICE')
        return
    if args.ds_r33_calendar_source_join:
        pins={}
        def pinned(path,commit=args.r33_source_commit):
            raw=pinned_calendar_blob(path,commit)
            pins[path]={'commit':commit,'sha256':hashlib.sha256(raw).hexdigest()};return raw
        def decoded(path,commit=args.r33_source_commit):
            raw=pinned(path,commit);return json.loads(gzip.decompress(raw) if path.endswith('.gz') else raw)
        folder='results/uarch/ds_hbm_window_retirement_r33_20261002/'
        bridge=decoded(folder+'bridge.json');native_raw=pinned('results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz')
        dispatch_raw=pinned('results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz')
        if hashlib.sha256(native_raw).hexdigest()!=bridge['original_native_sha256'] or hashlib.sha256(dispatch_raw).hexdigest()!=bridge['original_dispatch_sha256']:
            raise ValueError('r33 original native/dispatch producer source pins')
        original=json.loads(gzip.decompress(native_raw));dispatch=json.loads(gzip.decompress(dispatch_raw))
        contract=pinned('tools/ds_hbm_window_contract_r33.py');prepare=pinned('tools/ds_hbm_window_rope_prepare_r33.py')
        current,current_dispatch,witness,current_raw,current_dispatch_raw=derive_ds_r33_source_pair(original,dispatch,contract,prepare,bridge['position'])
        if (hashlib.sha256(current_raw).hexdigest()!=bridge['lowered_native_sha256'] or
            hashlib.sha256(current_dispatch_raw).hexdigest()!=bridge['lowered_dispatch_sha256'] or witness!=bridge['window_template_joins']):
            raise ValueError('r33 actual producer native/dispatch/witness regeneration mismatch')
        catalog=decoded(OUT+'/ds_forward_leaf_join_r3/review/forward_leaf_catalog.json.gz','781046c9775880183bd7f45a06ab101e98c66cac')
        homes=decoded(folder+'initial_window_homes.json.gz');produced=decoded('results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/finite_state_homes.json')
        import copy
        env={'copy':copy,'hashlib':hashlib,'json':json}
        exec(compile(ast.Module(body=[n for n in ast.parse(contract).body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'pinned_r33_initial_home_allocator','exec'),env)
        expected=env['initial_home_directory'](original,produced,bridge['position'],bridge['representation'])
        if json.loads(json.dumps(expected))!=homes:raise ValueError('r33 initial home allocator replay mismatch')
        adapter,current_catalog,overlay=adapt_ds_r33_calendar(original,dispatch,current,current_dispatch,witness,catalog,homes)
        window_provider=bind_ds_r33_window_provider_homes(adapter,produced,homes)
        g0=decoded(OUT+'/ds_forward_leaf_join_r3/review/G0_both_program_interface.json.gz','781046c9775880183bd7f45a06ab101e98c66cac')
        for row,current_pc in zip(g0['DeepSeek']['PC_bindings'],current_catalog['PC_bindings']):
            if row['pc']!=current_pc['pc'] or any(current_pc['native_batches128'][k]!=v for k,v in row['G0_native_batches128'].items()):
                raise ValueError('r33 unexpectedly changes source V1/G0 arithmetic demand')
            row['actual_rank_template_leaf_refs']=current_pc['bindings']
        g0['r33_source_context']=adapter['source_context'];g0['current_r33_C0_static_template_binding']=None
        g0['original_V1_cost_reservation_retained']=True
        rope=decoded(folder+'source_owned_rope_bindings.json.gz')
        expected_refs={str(o['pc'])+'/'+key+'/'+name for o in current['instructions'] for key,bs in o['provider_bindings'].items()
            for name,b in bs.items() if b['kind']=='explicit_auxiliary_provider' and name in ('rope_cos','rope_sin')}
        if set(rope)!=expected_refs:raise ValueError('r33 RoPE references mix source template contexts')
        for ref,binding in rope.items():
            pc,key,name=ref.split('/');actual=current['instructions'][int(pc)]['provider_bindings'][key][name]
            spec=current['templates'][key]['providers'][name]
            if binding['source_binding']!=actual or binding['shape']!=spec['shape'] or binding['dtype']!=spec['dtype']:
                raise ValueError('r33 actual coefficient provider/template binding')
            path=folder+'rope_images/'+Path(binding['path']).name
            image=pinned(path) if path not in pins else pinned_calendar_blob(path,args.r33_source_commit)
            if hashlib.sha256(image).hexdigest()!=binding['sha256']:raise ValueError('r33 immutable coefficient image pin')
        adapter['source_owned_RoPE_bindings']=len(rope)
        prior=decoded(OUT+'/provider_v1_mtp_join_r4/final_physical/summary.json','a67150839')
        adapter['retained_128row_cost_summary']=prior
        adapter['full_program_cost_reprice']=None;adapter['Sagan_original_DPATH_catalog_admitted_for_r33']=False
        context=adapter['source_context']
        require_ds_calendar_source_context(adapter,hashlib.sha256(current_raw).hexdigest(),
            hashlib.sha256(json.dumps(current_dispatch,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            hashlib.sha256(json.dumps(current_catalog,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        manifest={'schema':'H4_DS_R33_CALENDAR_SOURCE_MANIFEST_V1','source_pins':pins,
            'calendar_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'current_source_context':context,'current_native_gzip_sha256':bridge['lowered_native_sha256'],
            'current_dispatch_gzip_sha256':bridge['lowered_dispatch_sha256'],
            'derived_bulk_artifacts_stored':False,'old_cost_fit_retained':True,'hardware_admitted':False}
        summary={k:v for k,v in adapter.items() if k!='changed_window_PCs'}
        summary.update(changed_window_PCs=len(adapter['changed_window_PCs']),changed_source_calls=sum(r['source_calls'] for r in adapter['changed_window_PCs']))
        artifacts={'manifest.json':manifest,'summary.json':summary,'source_count_adapter.json.gz':adapter,
            'r33_current_catalog.json.gz':current_catalog,'r33_source_overlay.json.gz':overlay,
            'r33_window_provider_join.json.gz':window_provider,'r33_current_G0_interface.json.gz':g0}
        if not args.verify:args.out.mkdir(parents=True,exist_ok=False)
        for name,item in artifacts.items():
            raw=(json.dumps(item,sort_keys=True,indent=2)+'\n').encode();raw=gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw
            if args.verify:
                if (args.out/name).read_bytes()!=raw:raise ValueError('r33 source adapter replay mismatch '+name)
            else:(args.out/name).write_bytes(raw)
        print(json.dumps(summary,sort_keys=True));print('PASS_R33_CALENDAR_SOURCE_REPLAY' if args.verify else 'PASS_R33_CALENDAR_SOURCE_ADAPTER')
        return
    if args.tp96_collective_inputs:
        folder=args.tp96_collective_inputs
        if args.tp96_endpoint_cycles is None:raise ValueError('explicit provisional TP96 endpoint cycle inputs required')
        blobs={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
        record=json.loads(blobs['normal_record.json']);preflight=json.loads(blobs['preflight.json'])
        fixture=json.loads(blobs['fixture_manifest.json']);binary=json.loads(blobs['binary_sources.json'])
        if hashlib.sha256(blobs['preflight.json']).hexdigest()!=record['preflight_sha256']:
            raise ValueError('TP96 preflight bytes pin mismatch')
        if binary['compiled_at_source']!=record['source_commit'] or binary['binary_sha256']!=record['cases']['normal']['binary_sha256']:
            raise ValueError('TP96 source/binary receipt identity')
        for path,digest in {**preflight['source_sha256'],**record['source_sha256'],**binary['pins']}.items():
            retained=pinned_calendar_blob(path,record['source_commit'])
            if hashlib.sha256(retained).hexdigest()!=digest:
                raise ValueError('TP96 retained producer source mismatch '+path)
        costs=read_json(args.tp96_endpoint_cycles)
        versioned_path='results/uarch/h3_versioned_lowering_20261002/DeepSeek.json.gz'
        versioned_raw=source_bytes(versioned_path,'781046c9775880183bd7f45a06ab101e98c66cac')
        versioned=json.loads(gzip.decompress(versioned_raw))
        joined=reconcile_tp96_literal_collectives(record,preflight,fixture,blobs['normal.log'].decode(),versioned['operations'],costs['cycles'])
        native_path='results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
        native_raw=source_bytes(native_path,'91e3b8cc2791fa3fe1322df3d72b3f76dbd184f6')
        native=json.loads(gzip.decompress(native_raw))
        for op,actual in zip(versioned['operations'],native['instructions']):
            if op['pc']!=actual['pc'] or op['opcode']!=actual['family'] or op['reads']!=[r['version'] for r in actual['reads']] or op['writes']!=[r['version'] for r in actual['writes']]:
                raise ValueError('TP96 native/versioned source PC identity mismatch')
        legacy=json.loads(blobs['legacy_w15_hbm_nvls.json']);prod=legacy['configs']['hbm_p48_ss_prod']
        joined['legacy_product_slot_geometry']={'record_bytes':prod['record_bytes'],'slot_bytes':prod['slot_bytes'],
            'clock_hz':prod['clock_hz'],'fit':prod['fit'],'reading_guide':legacy['reading_guide']['product_bytes'],
            'index64B_consumer_floor_cycles':64*96,
            'index_product_slot_count':ceil(4096,prod['slot_bytes']),
            'index_product_fit_cycles':prod['fit']['all_gather']['fixed_cycles']+prod['fit']['all_gather']['cycles_per_word']*ceil(4096,prod['slot_bytes']),
            'literal_geometry_equivalent':False,'implementable_wideport_and_credits':None,'headline_delta':None}
        prior_path=OUT+'/provider_v1_mtp_join_r4/final_physical/summary.json'
        prior_raw=source_bytes(prior_path,'a67150839')
        joined['retained_native_provider_calendar']={'source_commit':'a67150839','summary_path':prior_path,
            'summary_sha256':hashlib.sha256(prior_raw).hexdigest(),'summary':json.loads(prior_raw),
            'native_V1_replacement_applied_again':False,'I64_RMW_added_again':False,
            'shared64_or_RF_mirror_cost_changed':False,'endpoint_cycles_added_to_native_ticks':False}
        manifest={'schema':'H4_TP96_LITERAL_SOURCE_MANIFEST_V1','producer_commit':record['source_commit'],
            'snapshots_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()},
            'cycle_input_sha256':hashlib.sha256(args.tp96_endpoint_cycles.read_bytes()).hexdigest(),
            'calendar_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'canonical_native_source':{'path':native_path,'commit':'91e3b8cc2791fa3fe1322df3d72b3f76dbd184f6','sha256':hashlib.sha256(native_raw).hexdigest()},
            'canonical_versioned_source':{'path':versioned_path,'commit':'781046c9775880183bd7f45a06ab101e98c66cac','sha256':hashlib.sha256(versioned_raw).hexdigest()},
            'producer_source_sha256':record['source_sha256'],'fixture_images_validation_owner':'parent independent normal receipt archive; no fixture regeneration',
            'physical_timings_changed':False,'headline_delta':None}
        summary={k:v for k,v in joined.items() if k not in ('ordered_PC_join','endpoint_reservations')}
        artifacts={'manifest.json':manifest,'summary.json':summary,'full_PC_collective_component.json.gz':joined}
        if not args.verify:args.out.mkdir(parents=True,exist_ok=False)
        for name,item in artifacts.items():
            raw=(json.dumps(item,sort_keys=True,indent=2)+'\n').encode();raw=gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw
            if args.verify:
                if (args.out/name).read_bytes()!=raw:raise ValueError('TP96 source replay mismatch '+name)
            else:(args.out/name).write_bytes(raw)
        print(json.dumps({'PCs':joined['PCs'],'collective_PCs':joined['collective_PCs'],'case_reconciliation':joined['case_reconciliation']},sort_keys=True))
        print('PASS_TP96_LITERAL_SOURCE_REPLAY' if args.verify else 'PASS_TP96_LITERAL_COMPONENT_COMPOSITION')
        return
    if args.provider_v1_join:
        pins={}
        def blob(path,commit=None):
            raw=source_bytes(path,commit);pins[path]={'commit':commit,'sha256':hashlib.sha256(raw).hexdigest()};return raw
        def value(path,commit=None):
            raw=blob(path,commit);return json.loads(gzip.decompress(raw) if path.endswith('.gz') else raw)
        native_raw=blob('results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz','91e3b8cc2791fa3fe1322df3d72b3f76dbd184f6')
        native=json.loads(gzip.decompress(native_raw));native_sha=hashlib.sha256(native_raw).hexdigest()
        folder=OUT+'/ds_forward_leaf_join_r3/review/'
        ds=value(folder+'full_program_costs.json.gz','781046c9775880183bd7f45a06ab101e98c66cac')
        qfix=value(OUT+'/h4_actual_config_e844/run_r3/repriced_intervals.json.gz','6e28f1a8b48ea0182aed59a09d65540a1b0b96b3')
        qwen=value(OUT+'/bounded_provider_milestone/Qwen_tiled.json.gz','781046c9775880183bd7f45a06ab101e98c66cac')
        model=value('results/uarch/h4_v1_g0_model_20261002/intake/run/model.json',args.v1_source_commit)
        blob('tools/h4_v1_g0_model.py',args.v1_source_commit);api=load_v1_cost_api(args.v1_source_commit)
        for op,bounds in model['typed_cost_bounds'].items():
            for key,cost in bounds.items():
                if api.command_cost(op,cost['input_bits'],cost['output_bits'],elements=cost['elements'],lanes=cost['lanes'])!=cost:
                    raise ValueError('V1 model command phases/source cost replay mismatch')
        successor=compose_v1_native_component_successor(ds,qfix,qwen,model)
        physical=value('results/uarch/h4_v1_g0_model_20261002/physical_join_r1/final/model.json',args.v1_physical_source_commit)
        blob('tools/h4_v1_physical_join.py',args.v1_physical_source_commit)
        for pin in physical['source_pins']:
            if hashlib.sha256(blob(pin['path'],pin['commit'])).hexdigest()!=pin['sha256']:
                raise ValueError('V1 physical input source pin mismatch')
        physical_join=join_v1_physical_capacity(physical)
        directory=value('results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/finite_state_homes.json',args.kepler_source_commit)
        source=blob('tools/ds_hbm_finite_state_homes_r30.py',args.kepler_source_commit)
        homes=bind_kepler_state_directory(native,directory,source,native_sha)
        terminal=[]
        if args.parent_state_receipts:
            supplied=read_json(args.parent_state_receipts);pins[str(args.parent_state_receipts)]={'sha256':hashlib.sha256(args.parent_state_receipts.read_bytes()).hexdigest()}
            for receipt in supplied['receipts']:
                identity=receipt['identity'];bindings=[r for r in directory['rows'] if all(identity[k]==r[k] for k in ('PC','version','rank'))]
                if len(bindings)!=1:raise ValueError('parent receipt state directory identity missing')
                terminal.append(validate_kepler_state_publication(receipt,bindings[0]))
        receipt_scope={'schema':'H4_KEPLER_PARENT_PUBLICATION_RECEIPT_JOIN_V1','source_bound_terminal_receipts':terminal,
            'actual_parent_receipts_supplied':bool(args.parent_state_receipts),'full_parent_movement_cost_closed':False,
            'full_fragment_sector_journals':None,'refill_writeback_ACK_reverse_cost':None,'hardware_admitted':False}
        acceptance=value('results/speculative/v41_flash_dspark_onpolicy_greedy.json',args.mtp_source_commit)
        isa=blob('tools/w19_hbm_tp96_isa.py',args.mtp_source_commit).decode()
        golden=blob('tools/w19_v41_mtp_golden.py',args.mtp_source_commit).decode()
        uarch=blob('tools/uarch_model.py',args.mtp_source_commit).decode()
        blob('tools/build_dspark_draft_graph.py',args.mtp_source_commit)
        mtp=audit_ds_mtp_source_contract(native,acceptance,isa,golden,uarch)
        mtp['primary_agentic_request_rate']=agentic_request_rate_summary([])
        pins['tools/h3_complete_native_calendar.py']={'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        summary={'schema':'H4_PROVIDER_V1_MTP_COMPOSED_JOIN_V1','status':'PASS_COMPONENT_JOIN_PARENT_MOVEMENT_AND_MTP_GATES_OPEN',
            'DS_PCs':successor['DeepSeek']['PCs'],'Qwen_PCs':successor['Qwen_full_program']['PCs'],
            'DS_native_only_successor_software_ticks':successor['DeepSeek']['known_native_only_successor_software_ticks'],
            'Qwen_reduced_fixture_native_only_successor_software_ticks':successor['Qwen_fixture']['native_only_successor_software_ticks'],
            'C0_provider_and_shared_charges_retained':True,'RF_additional_debit':None,'new_r22_charge':0,
            'index_key_produced_fragment_bindings':len(homes['index_key_bindings']),'index_key_full_history_binding':None,
            'shared_unknown_calls':ds['unknown_shared_template_calls'],'native_state_homes':homes['state_fragment_homes'],
            'complete_MTP_iteration_calibrated_us':None,'headline_agentic_median_rate':None,'hardware_admitted':False}
        artifacts={'manifest.json':{'schema':'H4_PROVIDER_V1_MTP_SOURCE_MANIFEST_V1','source_pins':pins,'hardware_admitted':False},
            'summary.json':summary,'V1_native_component_successor.json.gz':successor,'Kepler_state_home_join.json.gz':homes,
            'parent_receipt_join.json':receipt_scope,'MTP_source_contract_audit.json':mtp,
            'V1_physical_capacity_join.json':physical_join}
        if not args.verify:args.out.mkdir(parents=True,exist_ok=False)
        for name,item in artifacts.items():
            raw=(json.dumps(item,sort_keys=True,indent=2)+'\n').encode();raw=gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw
            if args.verify:
                if (args.out/name).read_bytes()!=raw:raise ValueError('provider/V1/MTP source replay mismatch '+name)
            else:(args.out/name).write_bytes(raw)
        print(json.dumps(summary,sort_keys=True));print('PASS_PROVIDER_V1_MTP_SOURCE_REPLAY' if args.verify else 'PASS_PROVIDER_V1_MTP_COMPOSITION')
        return
    if args.ds_full_program_cost:
        dispatch=read_json(args.ds_full_program_cost)
        if args.ds_full_native_source is None:raise ValueError('actual source native artifact required')
        native_raw=source_bytes(args.ds_full_native_source,args.ds_native_source_commit)
        digest=hashlib.sha256(native_raw).hexdigest()
        if digest!=dispatch['source_program_sha256']:raise ValueError('full native source pin mismatch')
        bridge_raw=source_bytes(args.ds_shared_bridge,args.ds_shared_bridge_commit) if args.ds_shared_bridge else None
        bridge=json.loads(gzip.decompress(bridge_raw) if str(args.ds_shared_bridge).endswith('.gz') else bridge_raw) if bridge_raw is not None else None
        bridge_source_raw=None
        if bridge is not None:
            if args.ds_shared_bridge_source is None:raise ValueError('bridge producer source bytes required')
            bridge_source_raw=source_bytes(args.ds_shared_bridge_source,args.ds_shared_bridge_commit)
            if hashlib.sha256(bridge_source_raw).hexdigest()!=bridge.get('bridge_source_sha256'):
                raise ValueError('bridge producer source bytes pin mismatch')
        native_program=json.loads(gzip.decompress(native_raw)) if bridge is not None or args.ds_forward_leaves else None
        catalog=None;c0join=None;c0pins={};parent_interface=None;residence_path=None;residence_raw=None
        if args.c0_source_commit and not args.ds_forward_leaves:raise ValueError('C0 join requires source forward leaves')
        if args.ds_forward_leaves:
            N,S=load_ds_forward_builders();catalog=compile_ds_forward_leaf_catalog(dispatch,native_program,N,S)
            residence_path=Path(native_program['residence_archive']);residence_raw=source_bytes(residence_path,args.ds_native_source_commit)
            parent_interface=compile_ds_forward_parent_interface(catalog,native_program,json.loads(gzip.decompress(residence_raw)))
        if args.c0_source_commit:
            path=Path('results/uarch/h4_c0_bridge_model_20261002/dispatch_lowering.json.gz')
            raw=source_bytes(path,args.c0_source_commit);c0pins[str(path)]=hashlib.sha256(raw).hexdigest()
            lowering=json.loads(gzip.decompress(raw))
            path=Path('tools/h3_qwen_bounded_native.py');raw=source_bytes(path,args.c0_source_commit)
            c0pins[str(path)]=hashlib.sha256(raw).hexdigest()
            aliases=next(ast.literal_eval(n.value) for n in ast.parse(raw).body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='QWEN_ALIASES' for t in n.targets))
            qpath=ROOT/OUT/'bounded_provider_milestone/Qwen_tiled.json.gz'
            c0join=join_c0_source_lowering(lowering,read_json(qpath),native_program,catalog,aliases,
                qwen_sha256=hashlib.sha256(qpath.read_bytes()).hexdigest())
        result=compose_ds_full_program_services(dispatch,bridge=bridge,native_program=native_program,leaf_catalog=catalog)
        inputs=[args.ds_full_program_cost,args.ds_full_native_source,Path(__file__)]
        if args.ds_shared_bridge:inputs.extend([args.ds_shared_bridge,args.ds_shared_bridge_source])
        if residence_path is not None:inputs.append(residence_path)
        if args.ds_forward_leaves:inputs.extend([ROOT/OUT/'final_ds_bed325f89/h3_deepseek_complete_native.py.source',
            ROOT/OUT/'bounded_provider_milestone/ds/h3_deepseek_streaming_linear.py.source',
            ROOT/OUT/'bounded_provider_milestone/Qwen_tiled.json.gz',
            ROOT/OUT/'final_ds_bed325f89/producer_pins.json',ROOT/OUT/'bounded_provider_milestone/ds/files_sha256.json',
            ROOT/OUT/'h4_actual_config_e844/inputs/primitive_capabilities.json'])
        manifest={'schema':'H4_DS_FULL_PROGRAM_COST_MANIFEST_V1','PCs':result['PCs'],'families':result['families'],
            'source_sha256':{str(p.relative_to(ROOT)) if p.is_absolute() and p.is_relative_to(ROOT) else str(p):
                hashlib.sha256(native_raw if p==args.ds_full_native_source else bridge_raw if p==args.ds_shared_bridge else
                    bridge_source_raw if p==args.ds_shared_bridge_source else residence_raw if p==residence_path else p.read_bytes()).hexdigest() for p in inputs},
            'native_source_commit':args.ds_native_source_commit,
            'status':result['status'],'unknown_shared_template_calls':result['unknown_shared_template_calls'],
            'complete_service_software_ticks':None,'hardware_full_native_claim':False,
            'scope':('all-PC source-resolved instruction/128lane obligations, retained provider costs, actual shared movement UNKNOWN; no arithmetic/provider replay' if catalog is not None else
                'all-PC instruction-dependent scalar upper, retained provider projections and optional actual shared bridge; no arithmetic/provider replay')}
        if args.ds_shared_bridge_commit:manifest['shared_bridge_source_commit']=args.ds_shared_bridge_commit
        if args.c0_source_commit:manifest.update(C0_source_commit=args.c0_source_commit,C0_source_sha256=c0pins)
        summary={k:v for k,v in result.items() if k not in ('PC_intervals','template_shared_bindings','constrained_extent_successor_demand')}
        summary['unbound_physical_workspace_ranks']=len(result['constrained_extent_successor_demand'])
        artifacts={'manifest.json':manifest,'summary.json':summary,'full_program_costs.json.gz':result}
        if parent_interface is not None:artifacts['forward_parent_provider_interface.json.gz']=parent_interface
        if c0join is not None:artifacts['C0_forward_source_join.json']=c0join
        if catalog is not None:
            qwen=read_json(ROOT/OUT/'bounded_provider_milestone/Qwen_tiled.json.gz')
            g0=compile_g0_source_interface(qwen,catalog)
            if c0join is not None:g0.update(C0_source_commit=args.c0_source_commit,C0_source_sha256=c0pins,
                C0_interface='results/uarch/h4_c0_bridge_model_20261002/dispatch_lowering.json.gz; verified by C0_forward_source_join.json')
            artifacts.update({'forward_leaf_catalog.json.gz':catalog,'G0_both_program_interface.json.gz':g0})
        if args.verify:
            for name,value in artifacts.items():
                raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
                expected=gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw
                if (args.out/name).read_bytes()!=expected:raise ValueError('DS full cost byte-exact replay mismatch: '+name)
        else:
            args.out.mkdir(parents=True,exist_ok=False)
            for name,value in artifacts.items():
                raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
                (args.out/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
        print(json.dumps({'PCs':result['PCs'],'families':result['families'],'status':result['status'],
            'known_service_software_ticks':result['known_service_software_ticks'],
            'unknown_shared_template_calls':result['unknown_shared_template_calls'],'hardware_full_native_claim':False}))
        print('PASS_DS_FULL_SOURCE_PINNED_COST_REPLAY' if args.verify else 'PASS_DS_FULL_KNOWN_SERVICE_COMPOSITION')
        return
    if args.h4_cost_join:
        folder=args.h4_cost_join
        pins=read_json(folder/'inputs.json')
        for name,digest in pins['sha256'].items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('H4 source pin mismatch: '+name)
        model=compose_h4_uarch((folder/'uarch_model.py.source').read_text(),
            read_json(folder/'uarch_parameters.json'),read_json(folder/'hardware_inventory.json'))
        execution=read_json(folder/'Qwen_provider_execution.json.gz')
        repriced=reprice_h4_intervals(execution)
        ds=reprice_h4_native_stages(read_json(folder/'DS_PC127_calendar.json.gz'),
            read_json(folder/'DS_PC127_template.json.gz'),repriced['explicit_provisional_costs'])
        summary={'schema':'H4_FINITE_MODEL_COST_JOIN_V1','source_sha256':pins['sha256'],
            'consumer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'Qwen_fixture_PC_intervals':len(repriced['ordered_PC_intervals']),
            'Qwen_software_ticks_before':repriced['baseline_software_ticks'],
            'Qwen_software_ticks_after':repriced['software_ticks'],
            'scratch64_transactions':repriced['scratch64_transactions'],
            'C0_command_repetitions':repriced['C0_commands'],
            'DS_PC127_C0_commands':ds['C0_commands'],'DS_PC127_added_software_ticks':ds['C0_added_software_ticks'],
            'DS_PC127_source_stages':len(ds['stages']),
            'H1_bridge_family_coverage':read_json(folder/'family_coverage.json'),
            'hardware_clock_admission':False,'no_provider_or_arithmetic_repeat':True,
            'RF_ACK_service_charged_once':True,'r22_augmentation_applied':False}
        artifacts={'model.json':model,'summary.json':summary,'repriced_intervals.json.gz':repriced,
                   'DS_PC127_repriced_stages.json.gz':ds}
        if args.verify:
            for name,value in artifacts.items():
                if read_json(args.out/name)!=value:raise ValueError('H4 cost replay mismatch: '+name)
        else:
            args.out.mkdir(parents=True,exist_ok=False)
            for name,value in artifacts.items():
                raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
                (args.out/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
        print(json.dumps(summary,sort_keys=True))
        print('PASS_H4_SOURCE_PINNED_COST_REPLAY' if args.verify else 'PASS_H4_FINITE_MODEL_COST_JOIN')
        return
    if args.ds_native_stage_calendar:
        if args.ds_stage_bindings is None:raise ValueError('native source provider bindings required')
        program=read_json(args.ds_native_stage_calendar);bindings=read_json(args.ds_stage_bindings)
        workspace=read_json(args.ds_stage_workspace) if args.ds_stage_workspace else None
        result=compile_ssa_finite_sm_services(program,rank=args.ds_stage_rank,provider_bindings=bindings,workspace=workspace)
        proof=verify_ssa_finite_sm_services(result,program) if result['status'].startswith('PASS') else {'status':result['status']}
        manifest={'schema':'H3_ORDERED_NATIVE_SM_STAGE_CALENDAR_V1',
            'source_sha256':{str(p.relative_to(ROOT)) if p.is_absolute() and p.is_relative_to(ROOT) else str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [args.ds_native_stage_calendar,args.ds_stage_bindings,Path(__file__)]},
            'status':result['status'],'proof':proof,'CPU_primitive_as_RTL_credit':False,'hardware_clock_admission':False,
            'scope':'ordered native stage/relative workspace/finite issue template; no payload or hardware execution'}
        if args.ds_stage_workspace:
            path=args.ds_stage_workspace
            name=str(path.relative_to(ROOT)) if path.is_absolute() and path.is_relative_to(ROOT) else str(path)
            manifest['source_sha256'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
        raw=gzip.compress(encode(result),mtime=0);manifest['calendar_sha256']=hashlib.sha256(raw).hexdigest()
        if args.verify:
            if (args.out/'native_stage_calendar.json.gz').read_bytes()!=raw or read_json(args.out/'manifest.json')!=manifest or read_json(args.out/'proof.json')!=proof:
                raise ValueError('native stage/source-pin calendar replay mismatch')
        else:
            args.out.mkdir(parents=True,exist_ok=False)
            (args.out/'native_stage_calendar.json.gz').write_bytes(raw)
            (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
            (args.out/'proof.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'status':'PASS_SOURCE_PINNED_NATIVE_SM_STAGE_REPLAY' if args.verify else result['status'],
                          'proof':proof,'hardware_clock_admission':False}))
        return
    if args.bounded_provider_join:
        return run_bounded_provider_join(args.bounded_provider_join,args.out,layers=args.bounded_layers,verify=args.verify)
    providers = read_json(args.qwen_providers) if args.qwen_providers else None
    native = {}
    producer_sources = {}
    native_hashes = {}
    for path in args.native_lowering:
        original = read_json(path)
        producer_sources.update(verify_portable_producer(path, original))
        data = normalize_bundle(original)
        if data['target'] in native:
            raise ValueError('duplicate target lowering')
        native[data['target']] = data
        native_hashes[data['target']] = hashlib.sha256(path.read_bytes()).hexdigest()
    workspace = load_workspace_provider(args.qwen_workspace, native_hashes['Qwen']) if args.qwen_workspace else None
    graphs, layouts = load_inputs(); default = cycle_table(graphs, layouts)
    table = read_json(args.cycles) if args.cycles else default
    required = set(default['values'])
    if workspace:
        provider_cost = workspace['join']['service_cost']
        for key, source in [('I64_highword_read_sector', 'highword_sidecar_extra_full_sector_read_ticks'),
                            ('I64_highword_write_sector', 'highword_sidecar_extra_full_sector_write_ticks'),
                            ('I64_split_join', 'codec_split_join_ticks_per128word_tile')]:
            if not args.cycles:
                table['values'][key] = positive(provider_cost[source], key)
            required.add(key)
        if not args.cycles:
            table['values']['I64_RMW_merge'] = 32
        required.add('I64_RMW_merge')
        table['workspace_cost_scope'] = 'R20 positive provisional inputs, unmeasured; sidecar sectors and split/join priced explicitly'
    for data in native.values():
        for primitive in bundle_primitives(data):
            key = 'native:' + primitive
            if not args.cycles:
                table['values'][key] = 32
            required.add(key)
    validate_cycles(table, required)
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PINS}
    sources.update(producer_sources)
    if workspace:
        sources.update(workspace['sources'])
        sources[str(args.qwen_workspace.resolve())] = hashlib.sha256(args.qwen_workspace.read_bytes()).hexdigest()
    if args.qwen_providers:
        sources[str(args.qwen_providers.resolve())] = hashlib.sha256(args.qwen_providers.read_bytes()).hexdigest()
    for path in args.native_lowering:
        sources[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in args.native_lowering:
        for snapshot in sorted(path.parent.glob('*.source')):
            sources[str(snapshot.resolve())] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        for name in ('h3_exact_scalar_contract.py', 'compile_deepseek_snapshot.py', 'producer_pins.json'):
            snapshot = path.parent / name
            if snapshot.exists():
                sources[str(snapshot.resolve())] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    if args.cycles:
        sources[str(args.cycles.resolve())] = hashlib.sha256(args.cycles.read_bytes()).hexdigest()
    if not args.verify:
        args.out.mkdir(parents=True, exist_ok=False)
    digests = {}; summaries = {}
    targets = args.target or list(graphs)
    if len(targets) != len(set(targets)):
        raise ValueError('duplicate target')
    for target in targets:
        result = compile_target(target, graphs[target], layouts[target], table, native.get(target), providers if target == 'Qwen' else None,
                                workspace if target == 'Qwen' else None)
        raw = encode(result); path = args.out / (target + '.json.gz')
        if args.verify:
            if gzip.decompress(path.read_bytes()) != raw:
                raise ValueError('calendar replay mismatch ' + target)
        else:
            path.write_bytes(gzip.compress(raw, mtime=0))
        digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        summaries[target] = {k: result[k] for k in ('status', 'PC_count', 'proof', 'cycles',
            'source_backed_extent_admission', 'constrained_extent_successors',
            'native_lowering_PC_count', 'native_operator_lowering_complete', 'native_primitive_count_gate',
            'workspace_provider_proof')}
    sources = {str(Path(k).relative_to(ROOT)) if Path(k).is_absolute() and Path(k).is_relative_to(ROOT) else k: v
               for k, v in sources.items()}
    manifest = {'schema': 'H3_COMPLETE_CALENDAR_REPLAY_V1', 'source_sha256': sources,
        'output_sha256': digests, 'endpoint_cycles': table, 'targets': summaries,
        'calibration_gate': 'Separate measured provider composition and numerical operator gates required; software ticks do not transfer to hardware clocks.',
        'replay': 'python tools/h3_complete_native_calendar.py --verify --out ' + str(args.out) +
            ''.join(' --native-lowering ' + str(p) for p in args.native_lowering) +
            (' --cycles ' + str(args.cycles) if args.cycles else '') +
            (' --qwen-providers ' + str(args.qwen_providers) if args.qwen_providers else '') +
            (' --qwen-workspace ' + str(args.qwen_workspace) if args.qwen_workspace else '') +
            ''.join(' --target ' + t for t in (args.target or []))}
    path = args.out / 'manifest.json'
    if args.verify:
        if read_json(path) != manifest:
            raise ValueError('source-pin manifest replay mismatch')
        print('PASS_SOURCE_PINNED_COMPLETE_CALENDAR_REPLAY')
    else:
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
