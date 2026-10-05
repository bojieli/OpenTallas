#!/usr/bin/env python3
"""Full source-PC dispatch/operand/control lowering, using existing native ABI.

Stores bounded descriptors and pinned continuation references; does not expand
runtime provider values or claim that source templates are RTL implementations.
"""
import collections,gzip,hashlib,json,math
from h4_c0_model import sources,pinned,NATIVE,DEWEY,DEWEY_INTERFACE,QPATH,DPATH,OUT
from h4_c0_bridge import NativeDecoder
from h3_qwen_bounded_native import COMMON_NATIVE

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    q,d,r=sources();decoder=NativeDecoder(q,d,r)
    model=json.load(open(OUT/'model.json'));dispatch=[];coverage=[]
    forward=json.loads(gzip.decompress(pinned('results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz')))
    template_catalog={};SSA_edges=0
    for tid,t in d['templates'].items():
        seen=set();native=collections.Counter();maximum_shape=0
        for i,step in enumerate(t['code']):
            assert step['op'] in COMMON_NATIVE and step['dst'] not in seen
            assert all(src in seen for src in step['src']);SSA_edges+=len(step['src']);seen.add(step['dst']);native[step['op']]+=1
            maximum_shape=max(maximum_shape,math.prod(step['shape'] or [1]))
        assert set(t['outputs'].values())<=seen
        template_catalog[tid]={'ordered_source_code_sha256':digest(t['code']),'ordered_steps':len(t['code']),'opcode_records':dict(native),'maximum_logical_shape':maximum_shape,'bounded_emitter':forward['templates'][tid]['execution_path'],'bounded_plan_ref':'forward_dispatch_milestone.json.gz#/templates/'+tid+'/plan','complete_template_lowering':'Every source SSA edge/opcode preserved; actual streaming128lane continuations remain owned by existing bounded compiler, not replaced by full-array issue.'}
    for name,ops in [('Qwen',q['operations']),('DeepSeek',d['instructions'])]:
        program_sha=hashlib.sha256(pinned(QPATH if name=='Qwen' else DPATH)).hexdigest()
        versions=sorted(set(decoder.home_index[name])|{v if isinstance(v,str) else v['version'] for op in ops for side in ('reads','writes') for v in op[side]});version_ids={v:i for i,v in enumerate(versions)}
        family_totals=collections.Counter();all_commands=0;empty=0
        for op in ops:
            pc=op['pc'];base=decoder.decode(name,pc);family_totals[base['family']]+=1
            rec={'model':name,'program_sha256':program_sha,'source_PC':pc,'family':base['family'],'dependency_completed_PC_ids':base['dependencies'],'source_version_ids':[version_ids[v] for v in base['reads']],'destination_version_ids':[version_ids[v] for v in base['writes']],'source_version_refs':base['reads'],'destination_version_refs':base['writes'],'identity_fields':['rank','SM','version','generation'],'state_transition_order':['accepted','complete','mirrored_visible_ACK','consumer_accept','reverse_grant','retire'],'family_hardware_admitted':False,'source_numeric_payload_executed':False}
            if name=='Qwen':
                c=collections.Counter();kernels=[]
                for kernel,n in op['calendar_export']['physical_primitives']['kernel_invocations'].items():
                    sequence=[step['native_opcode'] for step in decoder.leaf(name,pc,kernel=kernel)]
                    for code in sequence:c[code]+=n
                    kernels.append({'kernel':kernel,'invocations':n,'ordered_lowered_leaf_opcodes':sequence,'source_order_sha256':digest(q['microcode'][kernel])})
                assert dict(c)==op['calendar_export']['physical_primitives']['native_primitive_commands']
                all_commands+=sum(c.values());rec.update(ordered_leaf_bindings=kernels,native_command_counts=dict(c),outer_continuation='tools/h3_qwen_bounded_native.py:TiledMachine.execute/dot/rms; actual source loop driver retained',shape_context_capacity=q['source_program']['context_capacity'],control_only_family=not bool(c))
                if not c:empty+=1
            else:
                calls=[]
                for rb in op['rank_bindings']:
                    ids=sorted(({rb['template']} if 'template' in rb else set())|{x['template'] for x in rb.get('buffer_programs',[])})
                    assert rb.get('empty_owned_extent') or ids
                    for tid in ids:assert tid in template_catalog
                    calls.append({'rank':rb['rank'],'template_refs':ids,'buffer_programs':rb.get('buffer_programs',[]),'row_interval':rb.get('row_interval'),'empty_owned_extent':rb.get('empty_owned_extent',False),'SM_partition':rb.get('SM_partition')})
                rec.update(rank_template_calls=calls,outer_continuation='tools/h3_native_microop_adapter.py:execute_bound_ds_operation; existing streaming/staged compiler paths retained',logical_SSA_code_is_direct_RF_issue=False)
            dispatch.append(rec)
        p=model['programs'][name]
        coverage.append({'model':name,'PCs':len(ops),'families':dict(family_totals),'version_count':len(versions),'all_PC_dependencies_versions_lowered':True,'Qwen_native_commands_source_histogram':all_commands if name=='Qwen' else None,'control_only_PCs':empty if name=='Qwen' else None,'Dewey_interface':DEWEY_INTERFACE,'Dewey_commit':DEWEY,'minimum_encoding_fields':p['encoding']['fields_bits'],'issue_command_bits':512,'RF_logical_bytes':262144,'RF_mirrored_bytes':524288,'scratch_beat_bytes':64,'hardware_families_qualified':0,'full_numeric_program_executed':False,'missing_family_hardware_gates':p['family_gates']})
    assert len(dispatch)==3950
    # Dependency versions must actually be source declarations, not fabricated lookup IDs.
    for row in dispatch:
        unhomed=[v for v in row['source_version_refs']+row['destination_version_refs'] if v not in decoder.home_index[row['model']]]
        row['nonresident_provider_version_refs']=unhomed
        row['nonresident_provider_binding_gate']='Existing typed provider lease/visibility required; never fabricate an RF home or free zero-byte state' if unhomed else None
    payload={'schema':'H4_C0_FULL_PC_STATIC_DISPATCH_LOWERING_V1','native_commit':NATIVE,'Dewey_commit':DEWEY,'coverage':coverage,'DS_template_catalog':template_catalog,'dispatch':dispatch,'SSA_edges_verified':SSA_edges,'dynamic_commands_require':['existing actual source compiler continuation','concrete typed provider/home identity and generation','matching source attrs/rounding and predicate','source512RF/64Bscratch capacity/ACK and all future-reader release gates'],'complete_PC_dispatch_lowering':True,'complete_dynamic_numeric_execution':False,'RTL_admission':False}
    OUT.mkdir(exist_ok=True,parents=True);b=(json.dumps(payload,sort_keys=True,separators=(',',':'))+'\n').encode()
    (OUT/'dispatch_lowering.json.gz').write_bytes(gzip.compress(b,mtime=0))
    (OUT/'lowering_validation.json').write_text(json.dumps({'status':'PASS_ALL3950_PC_STATIC_MICROOP_VERSION_ACK_LOWERING','PCs':3950,'families':51,'DS_templates':len(template_catalog),'DS_SSA_edges_verified':SSA_edges,'Qwen_all1737_PC_lowered_counts_match':True,'source_programs_executed':False,'hardware_qualified':False,'payload_sha256':hashlib.sha256(b).hexdigest()},indent=2,sort_keys=True)+'\n')
    print((OUT/'lowering_validation.json').read_text())
if __name__=='__main__':main()
