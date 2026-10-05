#!/usr/bin/env python3
"""Pinned nested-dot/phase successor delta. Reads source/graphs/LEFs, no payloads.

--output DIR creates summary.json and deterministic events.json.gz; --check DIR
reproduces both. Original TC prerequisite evidence is never changed.
"""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE='e72abea5ae169d3167dddc89543013f0e6bb3a7a'
PHASE_REV='024bf9f8f6e2201a51144969b5c17bf7a82aa64a'
RF_REV='7c46371addc154ba6d6d89411cbe2a50f2fd3f08'
OLD='5413f0757b7e625693df2658481fcc218bbdefca'
PREFIX='results/rtl/deepseek_hbm_complete_20261001/'
PHASE_PATH=PREFIX+'index-source-service-phases-r2.json.gz'
RF_PATH='results/physical_abi3/asap7/gpu/w13_index_f32_consumer_ports_20261001/allphase_resource_join_r2.json'
TC_OPCODE='MMA_BF16_CHUNK8_TC16'


def tc_delta(opcode):
    # BF16 casts and scalar product/add instructions are NOT Tensor Core calls.
    if opcode==TC_OPCODE:return 1
    if opcode in {'FMUL','FADD','BF16','BF16_WIDEN','IMUL','F2I','dots_q4','SIMD_QK','SIMD_PV'}:return 0
    raise ValueError('unmapped dot/opcode: '+opcode)


def owned_count(n,rank):
    blocks=math.ceil(n/8);owned=max(0,(blocks-rank+95)//96);count=owned*8
    if owned and (blocks-1)%96==rank:count-=blocks*8-n
    return count


def selected_grid(text,which):
    tree=ast.parse(text);names={'_snap','_rows','grid_sm_'+which}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if len(nodes)!=3:raise ValueError('grid source contract changed')
    env={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned_grid_source','exec'),env)
    return env['grid_sm_'+which]()


def lef_info(text):
    m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text)
    if not m:raise ValueError('missing LEF size')
    w,h=map(float,m.groups());pins=[]
    for name,body in re.findall(r'\bPIN\s+(\S+)\s+(.*?)\n\s*END\s+\1(?:\s|$)',text,re.S):
        direction=re.search(r'DIRECTION\s+(\w+)',body)
        for layer,x0,y0,x1,y1 in re.findall(r'LAYER\s+(\w+)\s*;\s*RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',body):
            x,y=(float(x0)+float(x1))/2,(float(y0)+float(y1))/2
            edge=min({'W':x,'E':w-x,'S':y,'N':h-y},key=lambda e:{'W':x,'E':w-x,'S':y,'N':h-y}[e])
            pins.append({'pin':name,'direction':direction.group(1) if direction else 'unspecified','layer':layer,'edge':edge})
    return {'size_um':[w,h],'pin_rectangle_counts_by_edge_layer':dict(Counter(p['edge']+'/'+p['layer'] for p in pins)),
            'OBS_layers':sorted(set(re.findall(r'\bLAYER\s+(\w+)\s*;',text.split('  OBS',1)[-1]))) if '  OBS' in text else [],
            'pin_rectangles':len(pins)}


def build():
    pins=[];cache={}
    def raw(rev,path):
        key=(rev,path)
        if key not in cache:
            b=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
            pins.append({'git':rev,'path':path,'sha256':hashlib.sha256(b).hexdigest()});cache[key]=b
        return cache[key]
    def record(rev,path):return json.loads(raw(rev,path))
    proof=record(PHASE_REV,PREFIX+'index-source-service-plan-proof-r2.json')
    packed=raw(PHASE_REV,PHASE_PATH)
    if hashlib.sha256(packed).hexdigest()!=proof['artifacts'][Path(PHASE_PATH).name]['sha256']:raise ValueError('phase pin mismatch')
    for p,sha in proof['source_pins'].items():
        if hashlib.sha256(raw(proof['source_commit'],p)).hexdigest()!=sha:raise ValueError('phase source mismatch '+p)
    trace=json.loads(gzip.decompress(packed));rf=record(RF_REV,RF_PATH)
    if rf['phase_manifest_sha256']!=hashlib.sha256(packed).hexdigest():raise ValueError('RF phase identity mismatch')
    old=record(OLD,'results/uarch/hbm_tc_column_failure_prerequisite_20261001/model.json')
    graph=record(BASE,'results/rtl/w19_hbm_tp96_program_oreduce.json')
    calendar=record(BASE,PREFIX+'whole-program-calendar-r2.json')
    config=record(BASE,'compiler/models/deepseek-v4.1-flash/inference_config.json')
    paths=['tools/deepseek_hbm_complete_program.py','tools/deepseek_hbm_complete_executor.py','tools/deepseek_hbm_complete_isa.py',
        'tools/deepseek_hbm_complete_canonical.py','tools/w19_hbm_tp96_isa.py','tools/hdc_golden_v41.py',
        'tools/w19_gpu_attention_dots.py','tools/w19_gpu_simd_contract.py','tools/w19_attention_opcode_proof.py',
        'tools/w13_index_resource_calendar.py','tools/w13_index_allphase_resources.py','tools/deepseek_hbm_complete_index_token_demand.py',
        'rtl/gpu/ot_gpu_sm_v.sv','rtl/gpu/ot_gpu_stack.sv','rtl/gpu/ot_gpu_issue.sv','tools/uarch_model.py']
    for p in paths:raw(BASE,p)
    canonical=ast.parse(raw(BASE,'tools/deepseek_hbm_complete_canonical.py'))
    known=next(ast.literal_eval(n.value) for n in canonical.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='KNOWN' for t in n.targets))
    import w19_gpu_attention_dots as attention
    for path in ['tools/w19_gpu_attention_dots.py','tools/w19_gpu_simd_contract.py']:
        if (ROOT/path).read_bytes()!=raw(BASE,path):raise ValueError('local calendar source differs from pin')
    attention_profiles={str(rows):attention.profile(rows) for rows in [128,640]}
    contracts={}
    opcodes=sorted({e['opcode'] for p in trace['phases'] for e in p['events']})
    for op in opcodes:
        contracts[op]={'TC_successor_delta_cycles':tc_delta(op) if op in ('FMUL','FADD','IMUL','F2I') else 0,
            'service':'ordinary_SIMD_RF_shared','RF_read_latency_candidate':2,
            'physical_II_provider':'W13_OPCODE_'+op+'_II_CONTEXTUAL_SSFF',
            'physical_core_latency_provider':'W13_OPCODE_'+op+'_CORE_LATENCY_CONTEXTUAL_SSFF',
            'candidate_core_latency_cycles':7 if op in ('FADD','FMUL','IADD','ISUB','FCMP_GT','FCMP_LT') else 5 if op=='SHFL' else 'UNBOUND_CORE_'+op,
            'candidate_issue_rule':'one instruction per partition per cycle in canonical event model; arbitration/physicalII still requires provider',
            'candidate_latency_source':'Canonical KNOWN' if op in known else 'No bound cost in pinned canonical source; no default9 substitution',
            'candidate_RF_inclusive_latency_cycles':known[op] if op in known else 'UNBOUND_OPCODE_'+op}
    eventrows=[];phases=[]
    for phase_index,ph in enumerate(trace['phases']):
        cost=rf['phases'][phase_index]
        if cost['phase']!=ph['kernel']:raise ValueError('phase order mismatch')
        counter=Counter();read=write=0;ids=[]
        for e in ph['events']:
            if 'TC' in e['opcode'] or 'MMA' in e['opcode']:raise ValueError('unpriced TC found in index trace')
            warps=[a['warp'] for a in e['active_lanes'] if a['lanes']]
            counter[e['opcode']]+=len(warps)
            rb=32*len(e.get('operand_register_bindings',[]));wb=32*len(e.get('result_register_bindings',[]))
            read+=rb;write+=wb;ids.append(e['id'])
            eventrows.append({'source_event':e['id'],'phase':ph['kernel'],'branch':'finite' if phase_index<14 else 'exceptional',
                'recipe_pc_path':e['recipe_pc_path'],'opcode':e['opcode'],'executed_warp_issues':len(warps),
                'RF_read_bits':rb,'RF_logical_write_bits':wb,'RF_physical_write_bits':2*wb,
                'TC_successor_delta_cycles':0,'service_contract_ref':e['opcode']})
        if dict(counter)!=cost['demand']['executed_warp_issues_by_opcode']:raise ValueError('opcode event demand mismatch')
        if read!=sum(cost['demand']['active_RF_read_bits_by_opcode'].values()) or write!=sum(cost['demand']['active_RF_logical_write_bits_by_opcode'].values()):raise ValueError('RF demand mismatch')
        # Scope/query/key mapping follows the actual executed source, not a generic dot.
        scope='query_once_per_SM_per_index_call' if phase_index in (0,1,2,5,6,7,8) else 'per_local2_branch_invocation'
        phases.append({'phase':ph['kernel'],'branch':cost['branch_scenario'],'call_scope':scope,
            'source_event_count':len(ids),'source_events_digest':hashlib.sha256('\n'.join(ids).encode()).hexdigest(),
            'source_shape':ph['shape'],'opcode_warp_issues':dict(counter),'RF_read_bits':read,'RF_logical_write_bits':write,
            'RF_physical_two_copy_write_bits':2*write,'shared_warp_instructions':sum(cost['demand']['shared_warp_instructions_by_opcode'].values()),
            'no_broadcast_shared_bank_service_cycles':cost['no_broadcast_shared_bank_service_cycles'],
            'source_STORE_bindings_checked':cost['crossphase_source_STORE_bindings_checked'],
            'TC_successor_delta_cycles':0,'calendar_provider_requirements':cost['calendar_blockers']})
    flat=[(l['layer'],o) for l in graph['layers'] for o in l['ops']]
    indexnodes=[];nested=[];explicit=[];simd_nested=[]
    for pc,(layer,o) in enumerate(flat):
        c=calendar['operations'][pc]
        if (c['pc'],c['layer'],c['source_op_id'])!=(pc,layer,o['id']):raise ValueError('complete graph/calendar mismatch')
        if o.get('fn')=='index_scores':
            ranks=[]
            for rank in range(96):
                n=owned_count(o['n'],rank);full,tail=divmod(n,64)
                ranks.append({'rank':rank,'keys':n,'full64_tiles':full,'tail_keys':tail,
                    'source_executor_1024_batches':math.ceil(n/1024),
                    'query_template_calls_per_SM':1 if n else 0,
                    'local2_calls_by_SM':[full+int(2*s<tail) for s in range(32)],
                    'branch_templates':'finite phases0..13 with query_once scope, or exceptional phases14..49 selected by actual decoded bits; do not sum alternatives'})
            if [r['keys'] for r in ranks]!=c['ordinary_recipe_phases'][0]['rows_per_rank']:raise ValueError('index ownership mismatch')
            indexnodes.append({'pc':pc,'layer':layer,'source_op_id':o['id'],'KV_source_layer':o['src'],
                'global_keys':o['n'],'ranks':ranks,'phase_template_refs':[p['phase'] for p in phases],
                'TC_successor_delta_cycles':0,'actual_source_call':'Executor.f_index_scores -> IX.scores / finite fused or exceptional service proposal',
                'complete_service_join':'Per-call key mask/route must select actual executed template path. The r2 diverse2key trace proves bounded counts, not production branch frequencies.'})
        if o.get('fn')=='compressor':
            if not o['closes']:continue
            n=config['index_n_heads']*config['index_head_dim'];k=config['head_dim']
            chunks=math.ceil(k/8);groups=math.ceil(chunks/64);stack=math.ceil(math.log2(groups))
            old_col=42;parent_drain=old_col+14+7*stack+1+1+2
            rows_sm=math.ceil(n/32);issues=math.ceil(rows_sm*groups/8)*64
            nested.append({'event_id':f'pc{pc}.compressor.indexer_wk','pc':pc,'layer':layer,'source_op_id':o['id'],
                'call_count':1,'participants':o['ranks'],'source_call':'f_compressor -> V.linear_bf16 -> mv -> matvec_c',
                'weight':f'layers.{layer}.attn.indexer.wk.weight','matrix_shape':[n,k],
                'current_compiler_unit':o['unit'],'current_lowering':'reference macro gap with typed scalar recipes; no TC dispatch implemented',
                'successor_proposal_opcode':TC_OPCODE,'candidate_TC_delta_cycles':tc_delta(TC_OPCODE),
                'mapping_requires':'owner compiler opt-in TC BF16 projection binding; source BF16 conversion after FP32 row result; k_norm/RoPE/QDQ stay subsequent separate phases',
                'per_SM_rows':rows_sm,'chunk_len':8,'groups':groups,'slot_count':8,'TC_input_II_cycles':1,
                'weight_issue_cycles_per_SM':issues,'weight_bytes_per_rank':n*k*2,
                'old_column_latency_cycles':old_col,'new_column_latency_cycles':old_col+1,
                'parent_SM_drain_from_last_issue_cycles_structural':parent_drain,
                'new_parent_SM_drain_cycles_structural':parent_drain+1,
                'issue_plus_drain_cycles_structural':issues+parent_drain,
                'new_issue_plus_drain_cycles_structural':issues+parent_drain+1,
                'dependency_before':[f'pc{pc}.compressor.latent_BF16_visible',f'pc{pc}.WK_weights_visible'],
                'dependency_after':[f'pc{pc}.k_norm',f'pc{pc}.index_RoPE',f'pc{pc}.QDQ_FP4',f'pc{pc}.paired_append_WRvisible'],
                'cycle_basis':'Archived TC16 input42 + SUB4 combine14 + G-dependent stack7*ceil(log2G) + stack retirement1 + SM output1 + SM ingress2. Source structure, not measured physical closure.'})
        participants=list(range(96)) if o.get('ranks')=='all' else o.get('ranks',[])
        if o.get('fn')=='attend':
            rows=640 if o['yarn'] else 128
            for family in ('QK','PV'):
                simd_nested.append({'event_id':f'pc{pc}.attention.{family}','pc':pc,'layer':layer,'source_op_id':o['id'],
                    'family':family,'semantic_dot_calls_per_participant':1,'participants':participants,
                    'output_dot_count_per_participant':rows if family=='QK' else 512,
                    'dot_K':512 if family=='QK' else rows,'source_mapping':'ordinary SIMD FMUL+FADD+SHFL_PAIR',
                    'phase_profile_ref':str(rows)+'/'+family,'TC_successor_delta_cycles':0})
        if o.get('fn')=='hc_mixes':
            simd_nested.append({'event_id':f'pc{pc}.hc_mix_projection','pc':pc,'layer':layer,'source_op_id':o['id'],
                'semantic_matvec_calls_per_participant':1,'participants':participants,'matrix_shape':[24,20480],
                'source_mapping':'FP32 coefficient x BF16 residual via SIMD chunk_program; serial7core+RF2',
                'TC_successor_delta_cycles':0})
        if o.get('fn')=='engram_mix':
            simd_nested.append({'event_id':f'pc{pc}.engram_norm_similarity','pc':pc,'layer':layer,'source_op_id':o['id'],
                'participants':participants,'reduce_calls_per_participant':3*config['hc_mult'],
                'head_iterations':config['hc_mult'],'dot_K':config['dim'],
                'source_mapping':'2 norm plus1 similarity reduce_sum_c per HC head; FP32 coefficient products',
                'TC_successor_delta_cycles':0})
        if o['kind']=='mv' and o['fmt']=='bf16':
            explicit.append({'event_id':f'pc{pc}.matrix','pc':pc,'layer':layer,'source_op_id':o['id'],'source_fn':o['fn'],
                'candidate_opcode':TC_OPCODE,'candidate_TC_delta_cycles':1,'matrix_shape':[o['n'],o['k']],
                'groups':math.ceil(math.ceil(o['k']/8)/64),
                'shape_specific_parent_drain_cycles_structural':60+7*math.ceil(math.log2(math.ceil(math.ceil(o['k']/8)/64))),
                'shape_specific_new_parent_drain_cycles_structural':61+7*math.ceil(math.log2(math.ceil(math.ceil(o['k']/8)/64))),
                'TC_input_II_cycles':1,'active_ranks':[i for i,(a,b) in enumerate(o['rows']) if b>a]})
    if len(indexnodes)!=8 or len(nested)!=4 or len(explicit)!=93:raise ValueError('dot graph scope changed')
    historical=record(BASE,'results/rtl/gpu_sm_exact.json')
    measurements=[{'case':c['case'],'K':c['K'],'groups':c['groups'],'issue':c['issue'],'drain_cycles':c['rtl']['drain_last_line_to_last_result']} for c in historical['cases'] if c['fmt']=='v41_bf16']
    geometries={}
    gridtext=raw(BASE,'tools/chip_assembly/floorplans.py').decode()
    tc_path='results/physical_abi3/asap7/gpu/w13_tc_col_terminal_20261001T2112Z/records/results/physical_abi3/asap7/chip/abstracts/ot_gpu_tc_col/ot_gpu_tc_col.lef'
    lefs={name:lef_info(raw(BASE,path).decode()) for name,path in {
        'q_tc':tc_path,'v_tc':'results/physical_abi3/asap7/chip/abstracts/ot_gpu_tc16/ot_gpu_tc16.lef',
        'v_bd':'results/physical_abi3/asap7/chip/abstracts/ot_gpu_bd_col/ot_gpu_bd_col.lef'}.items()}
    for design,which in [('qwen','q'),('v41','v')]:
        layout=selected_grid(gridtext,which);cells=[]
        for name,x,y in layout:
            kind='q_tc' if which=='q' and 'u_tc' in name else 'v_tc' if 'u_tc' in name else 'v_bd' if 'u_bd' in name else ''
            if kind:cells.append({'instance':name,'x':x,'y':y,'w':lefs[kind]['size_um'][0],'h':lefs[kind]['size_um'][1],'master':kind})
        gaps=[];overlaps=[]
        for i,a in enumerate(cells):
            for b in cells[i+1:]:
                dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x']);dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
                if dx>0 and dy>0:overlaps.append({'a':a['instance'],'b':b['instance'],'overlap_um':[round(dx,3),round(dy,3)]})
            same=[b for b in cells if b['x']>a['x'] and b['y']==a['y']]
            if same:
                b=min(same,key=lambda b:b['x']);gaps.append(round(b['x']-a['x']-a['w'],3))
        fp=record(BASE,f'results/floorplan/hbm_gpu/{"qwen" if which=="q" else "v41"}_hbm_die.json')
        deftext=raw(BASE,f'results/floorplan/hbm_gpu/{"qwen" if which=="q" else "v41"}_hbm_die_macros.def').decode()
        if hashlib.sha256(deftext.encode()).hexdigest()!=fp['def_sha256']:raise ValueError('retained DEF identity')
        placed=[(int(i),int(x)/1000,int(y)/1000) for i,x,y in re.findall(r'- sm(\d+) \S+ \+ FIXED \( (\d+) (\d+) \)',deftext)]
        horiz=[round(b[1]-a[1]-fp['sm_tile']['w'],3) for a,b in zip(placed,placed[1:]) if a[2]==b[2]]
        vert=sorted(set(round(b[2]-a[2]-fp['sm_tile']['h'],3) for a in placed for b in placed if a[1]==b[1] and 0<b[2]-a[2]<2*fp['sm_tile']['h']))
        geometries[design]={'LEFs':{k:v for k,v in lefs.items() if k.startswith(which)},'source_grid_cells':cells,
            'raw_horizontal_column_gaps_um':sorted(set(gaps)),'grid_LEF_overlap_pairs':overlaps,
            'macro_halo_um_each_side':6,'Qwen_halo_free_gap_um':min(gaps)-12 if which=='q' else 'INVALID_OVERLAPPING_GRID',
            'retained_die_DEF_horizontal_SM_gaps_um':sorted(set(horiz)),'retained_die_DEF_vertical_SM_gaps_um':vert,
            'die_channel_model':fp['channels_um'],'die_floorplan_claim_boundary':fp['claim_boundary'],
            'local_channel_verdict':'Qwen source coordinates give raw gap only, no layer occupancy/PDN capacity' if which=='q' else 'FAIL_GRID_LEF_DIMENSION_CONFLICT',
            'required_provider':'W13_CONTEXT_TC_LANE_AND_SM_CHANNEL_GEOMETRY'}
    distributed=record(BASE,'results/physical_abi3/asap7/gpu/w13_distributed_geometry_correction_20261001/candidate_v2.json')
    providers=[{'id':'W13_CONTEXT_TC_LANE_AND_SM_CHANNEL_GEOMETRY','owner':'W13 physical/floorplan owner',
        'needed':['source-matched placement DEF with TC master SHA, orientation and x/y for all32/64 columns',
            'lane predecode-stage register placement boxes and boundary-to-lane control routes',
            'track grid origin/pitch/direction for each permitted layer and channel rectangle endpoints',
            'LEF OBS + parent PDN/via/halo/blockage occupancy and remaining tracks per direction',
            'source-matched TC16 master dimensions; resolve164grid versus180LEF and104bdgrid versus150LEF before capacity arithmetic'],
        'retained_evidence_limit':'Macro LEFs give pin access/OBS; die DEF places only SM envelopes. No placed TC lanes/new cut or routed whole SM capacity exists in retained records.'},
        {'id':'W13_INDEX_OPCODE_SERVICE_CONTRACTS','owner':'ordinary GPU/SIMD/RF provider with Boyle event join',
         'needed':['per-opcode core_latency and II for the22 executed index opcodes, source-qualified clock domain',
             'per-partition issue and RF2R1W readiness/write arbitration preserving lane SSA/result IDs',
             'all128query-guard warps split into4resident32 waves with launch/fence/loop and RF drain',
             'shared bank maps including scaleSTORE bridges, protected authority/read leases, provider ACK/CDC/creditreturn',
             'production per-call finite/exceptional branch masks; bounded synthetic2key opcode counts cannot be token frequencies'],
         'costs_already_bound':'50 phases /20492 executed source events; per-opcode warp demand, exact RF bits, shared service floors, no free repeated-address multicast'}]
    summary={'schema':'opentallas.hbm-tc-nested-dot-delta.v1','pins':pins,
        'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'failed_TC_verdict_unchanged':old['failure_unchanged'],
        'index_phase_join':{'artifact_git':PHASE_REV,'phase_source_git':proof['source_commit'],'RF_evidence_git':RF_REV,
            'source_events':len(eventrows),'phases':phases,'node_bindings':indexnodes,'service_contracts':contracts,
            'TC_successor_delta_cycles':0,'finite_and_exceptional_summed':False,
            'trace_scope':trace['fixture'],'provider_events_actual':trace['provider_events_actual'],
            'RF_source_contract':rf['phases'][0]['source_RF_contract'],'branch_resource_totals':rf['separate_branch_resource_totals'],
            'source_warp_guard_calls':'phase0 kernel once per SM,4resident waves; additional1536address_warp_ops/source trace queryguard contract, no zero-time launch'},
        'nested_compressor_projection_events':nested,'explicit_BF16_matrix_events':explicit,
        'ordinary_SIMD_nested_events':simd_nested,'attention_shape_service_profiles':attention_profiles,
        'other_nested_dots':{'attention_QK_PV':{'graph_calls':sum(o.get('fn')=='attend' for _,o in flat),'source_mapping':'dot_program(16/32) FMUL+FADD+SHFL_PAIR via schedule_warps; serial0.9GHz','candidate_issue_per_partition_per_cycle':1,'partitions':4,'shared_issue_per_SM_cycle':1,'FMUL_FADD_RF_inclusive_latency_cycles':9,'TC_successor_delta_cycles':0,'TC_retargeting':'Not selected: requires separate exactly matched golden-order/operand-domain mapping and per-shape calendar'},
            'HC_mix_projection':{'graph_calls':sum(o.get('fn')=='hc_mixes' for _,o in flat),'source_mapping':'hc_compute/chunk_program on ordinary SIMD; FP32 coefficients and BF16 residual','TC_successor_delta_cycles':0,'reason':'BF16 activations alone do not make coefficients BF16'},
            'Engram_similarity_and_norm_dots':{'graph_calls':sum(o.get('fn')=='engram_mix' for _,o in flat),'source_mapping':'FP32 multiplies/reduce_sum_c; serial ordinary SIMD','TC_successor_delta_cycles':0},
            'BF16_cast_opcode':{'source_mapping':'U32 RNE bit recipe in complete ISA; no multiply/accumulate','TC_successor_delta_cycles':0}},
        'composition_delta':{'previous_explicit_BF16_matrix_node_count':93,'added_nested_projection_node_count':4,
            'index_affected_TC_nodes':0,'attention_affected_TC_nodes':0,'proposal_TC_total_nodes':97,
            'added_serial_graph_projection_delta_stream_cycles':4,'added_serial_graph_projection_delta_ps':4*833,
            'retargeting_current_reference_gap_required':True,
            'parent_rule':'Add4 WK successor events on owner ranks63/31 to existing93 BF16 TC candidate events. Each adds1cycle to its own result/otag/ov, then k_norm and actual publication depend on it. Do not multiply delta by4096 rows/32SM/8cols or charge scalarFMUL/FADD.',
            'whole_token_service_status':'TC incremental exposure now bound per nested call; complete event-service timing requires named providers, no universal drain/max clock assumption'},
        'historical_measured_BF16_SM_cases':{'cases':measurements,'source_hashes':historical['source_sha256'],
            'transfer':'Historical standalone functional SM measurements differ from failed source/context.67/74/95 are shape-dependent evidence, not a common95cycle successor latency.'},
        'directional_geometry':geometries,
        'distributed_retained_alternative':{'scope':'capacity envelope, not TC lane/SM placement','rows':[{'model':r['model'],'vertical':r['vertical'],'horizontal':r['horizontal'],'map_scope':r['map_scope']} for r in distributed['rows']]},
        'exact_missing_providers':providers,
        'no_admission':{'checkpoint_payload_reads':0,'RTL_edits':0,'original_edits':0,'hardware_builds':0,'PnR':0,'main_writes':0,'adoption':False,'constraints_changed':False,'live_job_changes':0}}
    return summary,{'schema':'opentallas.hbm-tc-composed-phase-event-delta.v1','index_phase_events':eventrows,
        'nested_TC_candidate_events':nested,'explicit_TC_candidate_events':explicit,'ordinary_SIMD_nested_events':simd_nested,
        'index_graph_node_phase_replication':indexnodes}


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output',type=Path);g.add_argument('--check',type=Path);a=p.parse_args()
    summary,events=build();packed=gzip.compress((json.dumps(events,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
    summary['event_artifact_sha256']=hashlib.sha256(packed).hexdigest()
    text=json.dumps(summary,indent=2,sort_keys=True)+'\n';dest=a.output or a.check
    if a.check:
        if (dest/'summary.json').read_text()!=text or (dest/'events.json.gz').read_bytes()!=packed:raise SystemExit('FAIL reproduction')
        print('PASS pinned50phase/20492event RF join, nested TC mappings, shape-specific latency and directional geometry reproduce')
    else:
        if dest.exists():raise SystemExit('refuse overwrite evidence')
        dest.mkdir(parents=True);(dest/'summary.json').write_text(text);(dest/'events.json.gz').write_bytes(packed)
        print('Wrote nested event delta; hardware admission stays closed')

if __name__=='__main__':main()
