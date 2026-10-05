#!/usr/bin/env python3
"""Full source-pinned per-family bounded native schedule, all2213 PCs.

Regular operators use polynomial forward streams. Other families execute the
original SSA stages once with live-range arena reuse. Scalar demand evaluation
is a separate reference, never a performance admission or automatic fallback.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import h3_deepseek_streaming_linear as S
import h3_deepseek_staged_native as V
import h3_deepseek_bounded_tiles as REF
ROOT=Path(__file__).resolve().parents[1]
SOURCE=REF.PROGRAM


def transfer_projection(t):
    """Closed forward algorithm's <=512B fragment counts, not PHY costs."""
    f=t['family'];sh=t['shape_parameters'];ceil=lambda n:(n+511)//512
    rows=sh.get('rows',4);k=sh.get('k',32);tiles=(rows+127)//128
    if f=='linear_q':
        b=k//32;reads=b+tiles*b+2*rows*b;writes=b+tiles
    elif f in ('mv','linear_bf16','wo_a_part'):
        b=(k+7)//8;reads=b+tiles*b+rows*b;writes=b+tiles
    elif f=='all_gather':
        tiles=(sh.get('n',128)+127)//128;reads=2*sh.get('ranks',96)*tiles;writes=tiles
    elif f=='index_scores':
        h=sh.get('heads',4);w=sh.get('width',32)
        reads=ceil(h*w*4)+ceil(h*w//32*8)+ceil(h*w//2*4)+ceil(h*4)
        retained=ceil(h*w*8)+ceil(h*w//32*8)
        reads+=retained+rows*(ceil(w*4)+ceil(w//2*4)+ceil(w//32*8));writes=retained+rows
    else:
        sizes={};reads=0;writes=0
        for i in t['code']:
            # Eight bytes is a conservative width bound for every native dtype.
            # Report upper, not exact: F32/U32 are four bytes in the executor.
            for v in i['src']:reads+=ceil(sizes[v])
            sizes[i['dst']]=max(1,math.prod(i['shape']))*8;writes+=ceil(sizes[i['dst']])
        reads+=sum(ceil(sizes[v]) for v in t['outputs'].values())
    return {'read_512B_fragments_upper':reads,'write_512B_fragments_upper':writes,
            'accepted_commands_upper':reads+writes,'accepted_bytes_upper':512*(reads+writes),
            'memo_32B_commands':0,'continuation_128B_commands':0,
            'scope':'forward selected logical provider; excludes checkpoint fetch/route/physical costs; staged dtype width conservative8B',
            'physical_visibility_qualified':False}


def profile(t):
    f=t['family'];sh=t['shape_parameters'];attrs=t['source_attributes']
    if f=='linear_q':p=S.model(sh.get('rows',4),sh.get('k',32),attrs.get('fmt','fp8'));path='forward_streaming_Q8_matvec'
    elif f in ('mv','linear_bf16','wo_a_part'):p=S.float_model(sh.get('rows',4),sh.get('k',32),f=='linear_bf16');path='forward_streaming_float_matvec'
    elif f=='index_scores':p=S.index_model(sh.get('rows',4),sh.get('heads',4),sh.get('width',32));path='forward_streaming_index_rows'
    elif f=='all_gather':p=S.gather_model(sh.get('ranks',96),sh.get('n',128));path='forward_streaming_gather_columns'
    else:
        p=V.plan(t);path='source_order_live_range_stages'
        if not p['fits']:raise ValueError('explicit family refinement required, never automatic scalar fallback '+f)
    counts=p.get('opcode_scalar_evaluations',p.get('scalar_evaluations_by_opcode'))
    baseline=Counter()
    for i in t['code']:baseline[i['op']]+=max(1,math.prod(i['shape']))
    reference=REF.template_plan(t)
    return {'family':f,'execution_path':path,'plan':p,'executed_primitive_scalar_projection':counts,
            'provider_transfer_projection':transfer_projection(t),
            'baseline_once_scalar_evaluations':dict(baseline),'baseline_once_total':sum(baseline.values()),'forward_total':sum(counts.values()),
            'forward_to_baseline_work_ratio':{'numerator':sum(counts.values()),'denominator':sum(baseline.values())},
            'reference_only_cacheless_upper':reference['source_order_validation_evaluation_upper_bound']+sum(o['elements']*o['dependency_evaluation_upper_bound_per_element'] for o in reference['outputs'].values()),
            'reference_scalar_fallback_admitted':False,'no_recomputed_dependency_scalars':True,
            'unknown_port_route_latency_is_not_zero':True,'no_loss_vs_intended_tile_array_qualified':False}


def compile_full(source):
    templates={key:profile(t) for key,t in source['templates'].items()};pcs=[]
    for op in source['instructions']:
        counts=Counter();baseline=Counter();calls=[];transfers=Counter()
        for rank in op['rank_bindings']:
            if rank.get('empty_owned_extent'):continue
            identifiers=[b['template'] for b in rank['buffer_programs']] if rank['buffer_programs'] else [rank['template']]
            for key in identifiers:
                counts.update(templates[key]['executed_primitive_scalar_projection']);baseline.update(templates[key]['baseline_once_scalar_evaluations'])
                transfers.update({k:v for k,v in templates[key]['provider_transfer_projection'].items() if type(v) is int})
                calls.append({'rank':rank['rank'],'template':key,'SM_partition':rank['SM_partition'],'row_interval':rank.get('row_interval')})
        pcs.append({'pc':op['pc'],'family':op['family'],'calls':calls,'rank_bindings':op['rank_bindings'],'reads':op['reads'],'writes':op['writes'],'provider_bindings':op['provider_bindings'],
            'dependencies':op['dependencies'],'projected_executed_primitive_scalars':dict(counts),'baseline_once_scalars':dict(baseline),'recomputed_dependency_scalars':0,
            'provider_transfer_projection':dict(transfers),
            'unmeasured_provider_frame_routes_require_positive_costs':True,'hardware_admitted':False})
    paths=['tools/h3_deepseek_bounded_compile.py','tools/h3_deepseek_streaming_linear.py','tools/h3_deepseek_staged_native.py','tools/h3_deepseek_bounded_tiles.py','tools/h3_native_microop_adapter.py']
    return {'schema':'H3_DS_FORWARD_BOUNDED_POLYNOMIAL_DISPATCH_V2','coverage':source['coverage'],'source_program':SOURCE,'source_program_sha256':hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(),
        'templates':templates,'PC_dispatch':pcs,'automatic_scalar_fallback_templates':0,
        'workspace':{'rank_cap_bytes':33554432,'provider_AW':27,'base':None,'allocation_requires':'aligned disjoint actual provider range; prohibit wrap or HBM/spill/free-capacity fiction','live_range_release':'matching accepted fragment returns+reverse consumes, then source last use, then reuse','physical_provider_certified':False},
        '32SM_binding':'source block256 modulo32 and complete chunk8 subtrees retained; scalar collectors SM0. CPU interpreter wall time is not a GPU serialization/performance claim.',
        'fusion_scope':'exact original rounding; streaming matrix Kblocks, index independent rows, gather columns. Stage roundtrips priced rather than ideal fused routing.',
        'cost_status':'polynomial work/transfer obligations, NOT latency feasibility. Maxwell/Dewey must compose actual finite services+routes+critical path and no-loss gate.',
        'hardware_admitted':False,'latency_admitted':False,'physical_visibility_qualified':False,'RTL_builds':0,
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--verify',action='store_true');a=ap.parse_args()
    source=json.loads(gzip.decompress((ROOT/SOURCE).read_bytes()));p=compile_full(source);raw=json.dumps(p,sort_keys=True,separators=(',',':')).encode()
    if a.verify:
        if gzip.decompress(a.out.read_bytes())!=raw:raise SystemExit('source-bound bounded schedule mismatch')
    else:
        if a.out.exists():raise SystemExit('refuse overwrite evidence')
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(gzip.compress(raw,mtime=0))
    print(json.dumps({'status':'PASS_FULL_PC_POLYNOMIAL_SOFTWARE_SCHEDULE','PCs':len(p['PC_dispatch']),'families':len(p['coverage']['families']),'templates':len(p['templates']),'fallback':0,'workspace_rank_bytes':33554432,'provider_AW':27,'paths':dict(Counter(t['execution_path'] for t in p['templates'].values())),'latency_admitted':False}))
if __name__=='__main__':main()
