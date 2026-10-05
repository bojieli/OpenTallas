"""Executable conservative TP96 whole-token graph with fail-closed service costs.

Compile source programme order into finite-resource phases. No numerical model,
evaluation or RTL invocation. A missing kernel, refill, credit wait or fence cost
prevents a token schedule. All ranks execute concurrently within a phase: a
provider must price its slowest participating rank and shared traffic, not sum
96 elapsed times. No overlap is assumed between source operations.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess

PIN='609af8387'
PROGRAM='results/rtl/w19_hbm_tp96_program_oreduce.json'
ISA='tools/w19_hbm_tp96_isa.py'
KERNEL_COMMIT='14c57fd85'
KERNEL='results/rtl/w19_checkpoint_production_20261001/gpu-simd-lowering-candidate-r3.json'
SM='rtl/gpu/ot_gpu_sm_v.sv'


def operation_requirements(op):
    """Independent extents/ownership; these are not physical service cycles."""
    kind=op['kind']; r={'physical_service_cycles':None,'finite_wait_cycles':None}
    if kind=='mv':
        rows=[b-a for a,b in op['rows']]
        products={'fp4':256,'fp8':128,'bf16':64}[op['fmt']]
        waves=(max(rows)+31)//32
        ideal=(op['k']+products-1)//products*waves
        r.update(active_ranks=sum(n>0 for n in rows),rank_rows=rows,
            max_products_per_rank=max(rows)*op['k'],products_all_ranks=sum(rows)*op['k'],
            accepted256_weight_refill_bytes=None,active_AR_matrix_columns=1,
            per_sm_products_per_cycle_upper_bound=products,sm_count_per_rank=32,
            independent_output_row_waves_floor=waves,
            ideal_rank_matrix_issue_floor_cycles=ideal,
            issue_floor_is_not_complete_kernel_cost=True,
            note='Conservative AR1 column, whole-row golden tree stays within one SM; rows beyond32 require waves. Ignore no inactive-column area/clock cost. Issue floor excludes row-slot/IL, tree/drain, barriers, refill and assignment skew; physical accepted256 descriptors pending.')
    elif kind in ('all_gather','all_reduce','topk_merge','kv_gather'):
        targets=64 if op.get('dest')=='heads' else 96
        r.update(compiler_payload_bytes=op['bytes'],destination_ranks=targets,
            destination_compiler_payload_bytes=op['bytes']*targets,
            physical_noc_link_bytes=None,
            note='Compiler intended payload and endpoint-copy extent, not physical link traffic. Transport datatype/codec, ownership multiplicity, topology, arbitration and self-delivery remain service bindings.')
        if kind=='all_reduce':
            r.update(groups=8,contributors_per_group=8,golden_pairwise_add_levels=3,
                input_fp32_partial_bytes_all_ranks=64*1024*4,
                final_bf16_vector_bytes=8192*2,
                final_bf16_endpoint_bytes_all_ranks=8192*2*96,
                note='Eight independent groups reduce eight1024-element head partials in golden pairwise order; BF16 only after tree, then multicast full8192 vector. Compiler bytes alone do not price this traffic.')
        elif kind=='kv_gather':
            r.update(selected_rows=op['elems']//512,owner='(global_row//8)%96',
                source_rank_distribution=None,source_rank_distribution_runtime=True,
                decoded_fp32_reference_bytes_per_head=op['elems']*4,
                compressed_rows_source=op['src'],paired_data_scale_commit_required=True)
        elif kind=='topk_merge':
            r.update(source_candidate_elements=op['elems'],selected_elements=op['k'],
                stable_order='descending score then ascending global ID',
                physical_f32_u32_bridge_qualified=False)
    elif kind=='local' and op['fn']=='index_scores':
        q,t=divmod(op['n'],8*96)
        rows=[q*8+min(8,max(0,t-r*8)) for r in range(96)]
        r.update(source_kv_layer=op['src'],rows_per_rank=rows,
            max_rows_per_rank=max(rows),bounded_1024row_loops_per_rank=[(n+1023)//1024 for n in rows],
            logical_index_key_row_bytes_candidate=68,
            max_index_key_bytes_per_rank_candidate=max(rows)*68,
            index_heads=32,head_dim=128,
            note='Actual ISA rank ownership. Candidate68B key format does not price unpack/score/head-sum/selection or shared-memory service.')
    elif kind=='local' and op['fn'] in ('q_norm_kv_row','compressor'):
        r.update(packed_RMW_sector_bytes=32,write_acceptance_is_commit=False,
            valid_count_publish_after_data_and_scale_fence=True,
            writer_ranks=op.get('ranks'),compression_group=op.get('group'),closes=op.get('closes'))
    elif kind=='expert_fetch':
        r.update(runtime_expert_ids_required=True,experts=op['experts'],
            descriptor_reservation_only=True,payload_charged_at_matrix_refill=True)
    return r


def sha(value):
    return hashlib.sha256(value).hexdigest()


def graph(program, pins):
    assert program['tp']==96 and program['variant']=='oreduce'
    nodes=[]; operations=[]; prior=None
    for layer in program['layers']:
        for op in layer['ops']:
            kind=op['kind']; fn=op.get('fn',kind)
            source_index=len(operations);operations.append(dict(op,service_extents=operation_requirements(op)))
            # Each phase needs an independently bound cost, including finite
            # waits. A ready request is not a controller write completion.
            if kind=='mv':
                phases=[('weight_descriptor','descriptor'),('weight_refill_credit_wait','hbm'),
                        ('activation_stage','staging'),('matrix_kernel','matrix'),
                        ('result_stage','staging'),('matrix_drain_barrier','barrier')]
            elif kind=='local' and fn=='hc_mixes':
                phases=[]
                for wave in range(3):
                    phases += [(f'hc_wave{wave}_read_credit_wait','hbm'),
                        (f'hc_wave{wave}_transpose_noc_credit_wait','noc'),
                        (f'hc_wave{wave}_shared_fill','staging'),
                        (f'hc_wave{wave}_projection_norm_kernel','simt'),
                        (f'hc_wave{wave}_partial_retire_barrier','barrier')]
                phases += [('hc_final_chunk_tree_kernel','simt'),('hc_norm_scalar_kernel','simt'),
                    ('hc_row_norm_collect_credit_wait','noc'),('hc_collect_barrier','barrier'),
                    ('hc_scalar_finish_kernel','simt'),('hc_scalar_publish','staging'),
                    ('hc_retire_barrier','barrier')]
            elif kind=='local' and fn in ('hc_pre_norm','final_norm'):
                phases=[('operand_read_credit_wait','hbm'),('operand_stage','staging')]
                if fn in ('hc_pre_norm','final_norm'):
                    phases += [('pre_kernel','simt'),('pre_norm_handoff_barrier','barrier')]
                phases += [('norm_local_kernel','simt'),('norm_partial_collect_credit_wait','noc'),
                    ('norm_collector_kernel','simt'),('norm_scalar_kernel','simt'),
                    ('norm_scalar_broadcast_credit_wait','noc'),('norm_scale_kernel','simt'),
                    ('result_stage','staging'),('local_drain_barrier','barrier')]
            elif kind=='local':
                phases=[('operand_read_credit_wait','hbm'),('operand_stage','staging'),
                        ('gpu_simt_kernel','simt'),('result_stage','staging')]
                if fn in ('q_norm_kv_row','compressor'):
                    phases += [('packed_state_rmw_write','hbm'),('state_write_commit_fence','fence')]
                phases += [('local_drain_barrier','barrier')]
            elif kind=='expert_fetch':
                # Actual matrix refills are separately charged at each mv.
                phases=[('router_to_descriptor','descriptor'),('descriptor_credit_reservation','credits'),
                        ('descriptor_ready_barrier','barrier')]
            elif kind in ('all_gather','all_reduce','topk_merge'):
                phases=[('collective_stage','staging'),('collective_credit_wait_and_transfer','noc')]
                if kind!='all_gather':
                    phases += [('collective_reduce_or_merge_kernel','simt')]
                phases += [('collective_delivery_barrier','barrier')]
            elif kind=='kv_gather':
                phases=[('selected_owner_read_credit_wait','hbm'),('packed_decode_stage','staging'),
                        ('selected_rows_credit_wait_and_transfer','noc'),('head_operand_stage','staging'),
                        ('selected_rows_delivery_barrier','barrier')]
            else:
                raise ValueError(f'unknown operation {kind}')
            for phase,resource in phases:
                ident=f'L{op["layer"]}.O{op["id"]}.{phase}'
                nodes.append(dict(id=ident,depends_on=[] if prior is None else [prior],
                    cost_key=f'{kind}:{fn}:{phase}',resource=resource,
                    source_operation_index=source_index,phase=phase))
                prior=ident
    record=dict(schema='opentallas.w19.composed-token-graph.v1',source_pins=pins,
        ranks=96,position=program['position'],variant=program['variant'],
        execution_policy='Conservative source-order serial phases; concurrent participating ranks inside each phase; no unproved overlap.',
        programme_operations=sum(len(l['ops']) for l in program['layers']),
        operation_counts=dict(Counter(o['kind'] for l in program['layers'] for o in l['ops'])),
        operations=operations,nodes=nodes,
        service_requirements=dict(
            hbm='Finite four-controller queues/arbitration with matrix and nonSM traffic; cost includes credit and loaded-service waits.',
            descriptor='Accepted256 images and router-produced expert IDs; binding must price actual physical payload, not checkpoint bytes.',
            staging='Finite GPU RF/shared-memory banks, port conflicts, code/scale decode, DMA scatter and liveness.',
            simt='Actual GPU FP32 SIMD/RF/shared-memory/SFU schedule; no standalone HCP substitution.',
            matrix='Actual SM matrix kernel, ownership, full-F32 HC exclusion and shared-resource budgets.',
            noc='Source bytes are logical payload only; provider prices ownership, multicast/gather multiplicity, credits and links.',
            fence='Externally visible write commit and drain, never request acceptance.',
            barrier='Finite consumer completion and workspace-reuse barriers.'))
    record['graph_sha256']=sha(json.dumps(record,sort_keys=True,separators=(',',':')).encode())
    return record


def kernel_cost_contract(g,k,sha256):
    """Bind nonzero local model costs; transport and publication remain missing.

    This is a modeled candidate schedule, not GPU RTL exactness. Serializing
    norm scalar here adds153 cycles compared with r3's overlapped local recipe.
    No complete token cost can result until all remaining providers bind.
    """
    if k['organisation']['sm_count']!=32 or k['organisation']['simt_lanes_sm']!=128:
        raise ValueError('unknown GPU kernel geometry')
    hc=k['hc']; table={}
    for w,data in enumerate(hc['waves']):
        table[f'hc_wave{w}_shared_fill']=(data['shared_refill_cycles'],'staging',25)
        table[f'hc_wave{w}_projection_norm_kernel']=(max(data['projection']['cycles'],data['norm']['cycles']),'simt',25)
    table['hc_final_chunk_tree_kernel']=(hc['final_tree_cycles_candidate'],'simt',25)
    table['hc_norm_scalar_kernel']=(hc['scalar_dependency_cycles_candidate']['norm'],'simt',1)
    scalar=hc['scalar_dependency_cycles_candidate']
    table['hc_scalar_finish_kernel']=(sum(scalar[key] for key in ('mix_scale','pre_post','comb_softmax','sinkhorn')),'simt',1)
    costs={}
    for node in g['nodes']:
        if node['phase'] not in table:continue
        cycles,resource,units=table[node['phase']]
        if node['resource']!=resource:raise ValueError('kernel resource mismatch')
        costs[node['id']]=dict(cycles=cycles,clock_hz=k['clocks']['simd_hz'],resource_units=units,
            finite_waits_included=True,exact_gpu_lowering_bound=True,
            evidence=dict(commit=KERNEL_COMMIT,path=KERNEL,sha256=sha256),
            scope='Source-bound modeled local RF/SHMEM instruction calendar only, no RTL exactness or transport qualification.')
    return dict(graph_sha256=g['graph_sha256'],scope='GPU_SIMT_FULL_TOKEN_MODEL',
        resource_capacities={'simt':32,'staging':32},node_costs=costs,
        note='Other finite capacities/providers pending. No dedicated HCP. No free transpose/CDC/NoC/fence or collector.')



def norm_cost_contract(g,k,digest):
    """Local candidate costs only; preserve transport and handoff dependencies."""
    actual=[dict(layer='head' if o['layer']==-1 else o['layer'],op=o['id'],function=o['fn']) for o in g['operations']
            if o.get('fn') in ('hc_pre_norm','hc_post','final_norm')]
    if actual!=k['source_graph_binding']:raise ValueError('norm calendar programme mismatch')
    if k['organisation']['SMs']!=32 or k['organisation']['lanes_per_SM']!=128:
        raise ValueError('norm calendar GPU organisation mismatch')
    table={'pre_kernel':('pre',20),'norm_local_kernel':('norm_local',20),
           'norm_collector_kernel':('norm_collector',1),'norm_scalar_kernel':('norm_scalar',1),
           'norm_scale_kernel':('scale',20)}
    costs={}
    for n in g['nodes']:
        op=g['operations'][n['source_operation_index']]
        phase=n['phase']
        if op.get('fn')=='hc_post' and phase=='gpu_simt_kernel':recipe,units='post',20
        elif op.get('fn') in ('hc_pre_norm','final_norm') and phase in table:recipe,units=table[phase]
        else:continue
        costs[n['id']]=dict(cycles=k['calendars'][recipe]['cycles'],clock_hz=900000000,
            resource_units=units,finite_waits_included=True,exact_gpu_lowering_bound=True,
            evidence=dict(commit='5a55e676b',path='results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json',sha256=digest),
            scope='Source-bound GPU candidate opcode/RF calendar only; transport and physical precision wrappers unqualified.')
    return costs


def elementwise_cost_contract(g,k,digest):
    actual=[dict(layer=o['layer'],op=o['id'],function='moe_sum') for o in g['operations'] if o.get('fn')=='moe_sum']
    if actual!=k['source_graph_binding']:raise ValueError('elementwise programme mismatch')
    return {n['id']:dict(cycles=k['calendar']['cycles'],clock_hz=k['clock_hz'],
        resource_units=k['active_SM_per_rank'],finite_waits_included=True,exact_gpu_lowering_bound=True,
        evidence=dict(commit='01088553b',path='results/quality/w16_w19_composed_schedule_20261001/moe_sum_calendar.json',sha256=digest),
        scope='Source-bound modeled ordered BF16-input MoE sum local calendar only; refill/staging/physical exactness pending.')
        for n in g['nodes'] if g['operations'][n['source_operation_index']].get('fn')=='moe_sum' and n['phase']=='gpu_simt_kernel'}

def schedule(g, contracts, evidence_reader=None):
    costs=contracts.get('node_costs',{})
    missing=[dict(node=n['id'],cost_key=n['cost_key'],resource=n['resource'])
             for n in g['nodes'] if n['id'] not in costs]
    base=dict(schema='opentallas.w19.composed-token-schedule.v1',graph_sha256=g['graph_sha256'],
              programme_operations=g['programme_operations'],phase_nodes=len(g['nodes']),
              hardware_adopted=False,physical_admission=False,maximum_qualified_clock_hz=None,
              connected_rate_credit=False,full_token_cycles=None,
              full_token_time_ps=None,bound_local_model_cost_nodes=len(costs))
    if not costs:
        return dict(base,status='BLOCKED_MISSING_KERNEL_OR_SERVICE_COSTS',missing_costs=missing,
                    missing_cost_keys=sorted({n['cost_key'] for n in missing}))
    if contracts.get('graph_sha256')!=g['graph_sha256']:
        raise ValueError('service contract belongs to a different graph')
    if contracts.get('scope')!='GPU_SIMT_FULL_TOKEN_MODEL':
        raise ValueError('dedicated HCP or unrelated profile is not GPU whole-token service')
    capacities=contracts.get('resource_capacities',{})
    node_ids={n['id'] for n in g['nodes']}
    if not costs.keys()<=node_ids:raise ValueError('cost contract contains unknown nodes')
    resources={n['resource'] for n in g['nodes'] if n['id'] in costs}
    if not resources<=capacities.keys():
        raise ValueError('all finite resources require declared capacities')
    slots={r:[Fraction(0)]*capacities[r] for r in resources if isinstance(capacities[r],int) and capacities[r]>0}
    if set(slots)!=resources:
        raise ValueError('resource capacity must be a positive integer')
    end={}; timeline=[]; totals=Counter(); verified={}
    if evidence_reader is None:
        def evidence_reader(commit,path):
            return subprocess.check_output(['git','show',f'{commit}:{path}'],
                cwd=Path(__file__).resolve().parents[1],stderr=subprocess.DEVNULL)
    for n in g['nodes']:
        if n['id'] not in costs:continue
        c=costs[n['id']]
        for key in ('cycles','clock_hz','resource_units'):
            if not isinstance(c.get(key),int) or c[key]<(0 if key=='cycles' else 1):
                raise ValueError(f'{n["id"]}: missing positive {key}')
        if c['cycles']==0 and c.get('zero_service_proved') is not True:
            raise ValueError(f'{n["id"]}: unproved zero-cost phase')
        if c.get('finite_waits_included') is not True or c.get('exact_gpu_lowering_bound') is not True:
            raise ValueError(f'{n["id"]}: finite waits or actual GPU lowering unbound')
        binding=c.get('evidence',{})
        if not binding.get('path') or not re.fullmatch('[0-9a-f]{64}',binding.get('sha256','')) or not re.fullmatch('[0-9a-f]{9,40}',binding.get('commit','')):
            raise ValueError(f'{n["id"]}: missing source-bound service evidence')
        key=(binding['commit'],binding['path'])
        if key not in verified:
            try:verified[key]=sha(evidence_reader(*key))
            except (OSError,subprocess.CalledProcessError) as exc:
                raise ValueError(f'{n["id"]}: service evidence unavailable') from exc
        if verified[key]!=binding['sha256']:
            raise ValueError(f'{n["id"]}: service evidence source drift')
        pool=slots[n['resource']]; demand=c['resource_units']
        if demand>len(pool):
            raise ValueError(f'{n["id"]}: resource demand exceeds finite capacity')
        if missing:continue
        available=sorted(range(len(pool)),key=pool.__getitem__)[:demand]
        begin=max([end[p] for p in n['depends_on']]+[pool[i] for i in available]+[Fraction(0)])
        duration=Fraction(c['cycles']*10**12,c['clock_hz'])
        finish=begin+duration;end[n['id']]=finish
        for i in available:pool[i]=finish
        totals[n['resource']]+=duration
        timeline.append(dict(id=n['id'],start_ps=str(begin),end_ps=str(finish),
                             cycles=c['cycles'],clock_hz=c['clock_hz'],resource=n['resource']))
    if missing:
        return dict(base,status='BLOCKED_MISSING_KERNEL_OR_SERVICE_COSTS',missing_costs=missing,
                    verified_cost_evidence={f'{rev}:{path}':digest for (rev,path),digest in verified.items()},
                    missing_cost_keys=sorted({n['cost_key'] for n in missing}))
    # Even a complete modeled graph is not connected RTL cycle evidence.
    return dict(base,status='COMPLETE_MODELED_SCHEDULE_NOT_CONNECTED_RTL',missing_costs=[],
                modeled_token_time_ps=str(max(end.values(),default=Fraction(0))),
                resource_time_ps={k:str(v) for k,v in totals.items()},timeline=timeline)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contracts',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parents[1]
    revisions={PROGRAM:PIN,ISA:PIN,SM:PIN,KERNEL:KERNEL_COMMIT}
    blobs={p:subprocess.check_output(['git','show',f'{rev}:{p}'],cwd=root) for p,rev in revisions.items()}
    g=graph(json.loads(blobs[PROGRAM]),{p:dict(commit=revisions[p],sha256=sha(b)) for p,b in blobs.items()})
    kernel_blob=blobs[KERNEL];kernel=json.loads(kernel_blob)
    verified={}
    for path,expected in kernel['source_pins'].items():
        actual=sha(subprocess.check_output(['git','show',f'{KERNEL_COMMIT}:{path}'],cwd=root))
        if actual!=expected:raise ValueError(f'kernel source pin mismatch: {path}')
        verified[path]=actual
    if kernel['source_pins'][PROGRAM]!=sha(blobs[PROGRAM]):
        raise ValueError('kernel and whole-token programme differ')
    c=kernel_cost_contract(g,kernel,sha(kernel_blob))
    norm_path='results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json'
    norm_blob=subprocess.check_output(['git','show',f'5a55e676b:{norm_path}'],cwd=root)
    norm=json.loads(norm_blob)
    for path,expected in norm['source_pins'].items():
        if sha(subprocess.check_output(['git','show',f'5a55e676b:{path}'],cwd=root))!=expected:
            raise ValueError(f'norm source pin mismatch: {path}')
    c['node_costs'].update(norm_cost_contract(g,norm,sha(norm_blob)))
    element_path='results/quality/w16_w19_composed_schedule_20261001/moe_sum_calendar.json'
    element_blob=subprocess.check_output(['git','show',f'01088553b:{element_path}'],cwd=root)
    element=json.loads(element_blob)
    for path,pin in element['source_pins'].items():
        if sha(subprocess.check_output(['git','show',f'{pin["commit"]}:{path}'],cwd=root))!=pin['sha256']:
            raise ValueError(f'elementwise source pin mismatch: {path}')
    c['node_costs'].update(elementwise_cost_contract(g,element,sha(element_blob)))
    if args.contracts:
        supplied=json.loads(args.contracts.read_text())
        if supplied.get('graph_sha256')!=g['graph_sha256'] or supplied.get('scope')!=c['scope']:
            raise ValueError('external services belong to a different graph or architecture')
        c['resource_capacities'].update(supplied.get('resource_capacities',{}))
        c['node_costs'].update(supplied.get('node_costs',{}))
    result=schedule(g,c)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'graph.json').write_text(json.dumps(g,indent=2)+'\n')
    (args.out/'schedule.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.out/'local_cost_contract.json').write_text(json.dumps(c,indent=2)+'\n')
    summary={k:v for k,v in g.items() if k not in ('nodes','operations')}
    summary['phase_nodes']=len(g['nodes'])
    summary['phase_counts']=dict(Counter(n['phase'] for n in g['nodes']))
    summary['cost_key_counts']=dict(Counter(n['cost_key'] for n in g['nodes']))
    summary['logical_collective_payload_bytes_by_kind']={kind:sum(o.get('bytes',0) for o in g['operations'] if o['kind']==kind)
        for kind in ('all_gather','all_reduce','topk_merge','kv_gather')}
    summary['payload_scope']='Source logical collective payload, not NoC transfer volume or timing; topology/multicast/ownership multiplicity pending.'
    summary['refill_scope']='1103 matrix refills require accepted256 physical descriptors and runtime expert IDs; no checkpoint-byte substitution. Expert_fetch nodes reserve descriptors; payload charged at matrix refill only.'
    summary['matrix_ideal_issue_floor_cycles_sum']=sum(o['service_extents'].get('ideal_rank_matrix_issue_floor_cycles',0) for o in g['operations'])
    summary['matrix_issue_floor_scope']='Arithmetic-only sum at one active AR column and ideal32SM whole-row waves; not complete matrix schedule, clock-qualified timing or full-token cycles.'
    summary['default_schedule_status']=result['status']
    summary['physical_admission']=False
    summary['maximum_qualified_clock_hz']=None
    summary['full_token_cycles']=None
    summary['full_token_time_ps']=None
    (args.out/'graph_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    binding=dict(schema='opentallas.w19.composed-kernel-binding.v1',graph_sha256=g['graph_sha256'],
        kernel_commit=KERNEL_COMMIT,kernel_path=KERNEL,kernel_sha256=sha(kernel_blob),
        verified_source_pins=verified,current_candidate='r3',rejected_candidates_preserved=['r1','r2'],
        source_HC_operations=sum(o.get('fn')=='hc_mixes' for o in g['operations']),
        HC_local_candidate_cycles=kernel['hc']['local_compute_cycles_candidate'],
        HC_serialized_local_cycles_per_operator=7007,
        bound_nonzero_local_cost_nodes=len(c['node_costs']),
        physical_admission=False,maximum_qualified_clock_hz=None,
        clock_hz=kernel['clocks']['simd_hz'],complete_service_provider=False,
        candidate_estimate_not_admitted_into_complete_schedule=True,
        missing_services=kernel['prerequisites'],full_token_cycles=None,connected_rate_credit=False)
    (args.out/'kernel_binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    transport_path='results/uarch/w19_transport_contract_20261001/contract_r1.json'
    write_path='results/rtl/w19_checkpoint_production_20261001/write-commit-contract-r1.json'
    physical_path='results/physical_abi3/asap7/gpu/w13_tc16_terminal_20261001T120346Z/receipt.json'
    physical_blob=subprocess.check_output(['git','show',f'a556ad457:{physical_path}'],cwd=root)
    physical=json.loads(physical_blob)
    if physical['engineering_verdict']!='FAIL' or physical['ss_setup_wns_ps']!=-31.06 or physical['ff_hold_wns_ps']!=5.22:
        raise ValueError('unexpected TC16 physical evidence')
    service_pins={physical_path:dict(commit='a556ad457',sha256=sha(physical_blob)),
        norm_path:dict(commit='5a55e676b',sha256=sha(norm_blob)),
        element_path:dict(commit='01088553b',sha256=sha(element_blob))}
    for rev,path in [('685fdce29',transport_path),('f91b15c0c',write_path)]:
        blob=subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=root)
        service_pins[path]=dict(commit=rev,sha256=sha(blob))
    from w19_finite_service_calendar import profile as finite_service_profile
    finite_profile=finite_service_profile()
    (args.out/'finite_service_profile.json').write_text(json.dumps(finite_profile,indent=2)+'\n')
    service=dict(schema='opentallas.w19.composed-service-readiness.v1',
        graph_sha256=g['graph_sha256'],source_pins=service_pins,
        finite_service_calendar=dict(tool='tools/w19_finite_service_calendar.py',
            profile_path='finite_service_profile.json',profile=finite_profile,
            complete_phase_provider=False),
        scope='Entire2213-operation graph; nonzero HC local calendar bound, transport components not substituted for complete service.',
        bound_local_model_cost_nodes=len(c['node_costs']),missing_cost_nodes=len(result.get('missing_costs',[])),
        HC_serialized_local_cycles_per_operator=7007,HC_operations=80,
        norm_compute_candidate_cycles=dict(hc_pre_norm=558,final_norm=558,hc_post=530),
        moe_sum_compute_candidate_cycles=element['calendar']['cycles'],
        moe_sum_compute_operations=40,
        norm_compute_scope='Nonzero RF/shared/opcode calendar only; collector transport, pre/norm handoff, broadcast and fences remain missing.',
        HC_read_component_floors=dict(wave_read_commands_per_controller=[384,384,192],
            wave_bytes_per_controller=[196608,196608,98304],
            ingress_cycles_one_request_per_controller_cycle=[384,384,192],
            return_cycles_32PC_times32B_peak=[192,192,96],
            note='Bandwidth/ingress lower bounds only, overlap unspecified. Not phase costs: PC ownership, banks, QD/RQD, refresh, return stalls, other clients, landing arbitration, swizzle and CDC pending.'),
        write_component_floors=dict(CWL_ps=6250,burst_ps=1024,
            earliest_visible_after_actual_WR_column_ps=7274,
            minimum_registered_ACK_fabric_cycles=1,live_transactions_per_controller=4,
            note='Actual scheduler WR timestamp/visibility event mandatory; these minima cannot replace queued service, physical visibility, CDC, consumer waits or fence.'),
        full_token_cycles=None,full_token_rate=None,physical_admission=False,
        maximum_qualified_clock_hz=None,hardware_adopted=False,
        physical_diagnostic=dict(status='SOURCE_BOUND_TERMINAL_FAIL',
            source_commit='000ba0898',SS_setup_slack_ps=-31.06,FF_hold_slack_ps=5.22,
            target_period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
            delay_derived_period_floor_ps='864.06',
            delay_derived_frequency_ceiling_hz=str(Fraction(10**14,86406)),
            note='Diagnostic ceiling only; not a qualified clock, no rate credit, no retry. Streaming1.2GHz and serial0.9GHz assumptions unchanged. Immutable terminal receipt and raw corner reports preserved in a556ad457.'),
        common_service_geometry=dict(status='OWNER_REPORTED_CORRECTION_NOT_ADMITTED',
            gather_macros=400,area_mm2='162.284',slot_fit=False,
            note='Old200-macro layout excluded. Corrected source-bound geometry/area/routes/floorplan and service calendar still required.'),
        missing_admission=['finite read controller timing/credits/backpressure and all-client arbitration',
            'landing/context bank collision ports, transpose/NoC and CDC latency',
            'actual matrix accepted256/runtime expert descriptor/refill and finite row assignment',
            'nonHC gather/KV/index/norm/SFU golden GPU instruction calendars',
            'actual WR-visible ACK interface, RMW locks, paired code/scale commit and epoch fences',
            'GPU RF/shared staging/SIMD and common service area/routes/floorplan fit',
            'connected full-token exactness/calibration and contextual SS/FF closure'])
    (args.out/'service_readiness.json').write_text(json.dumps(service,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('missing_costs','timeline')},indent=2))
    return 2 if result['status'].startswith('BLOCKED') else 0


if __name__=='__main__':
    raise SystemExit(main())
