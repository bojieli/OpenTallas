#!/usr/bin/env python3
"""Scenario analytical HC pre/norm/post costs; no current generator/RTL changes."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import types
import copy
import w16_gpu_hc_dot_schedule as D
import w19_gpu_norm_calendar as N
import w19_burst_ingress as B
R=D.R
ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/w16_gpu_hc_vector_costs_20261001'
INPUTS=OUT+'/inputs_r1.json'
EULER_COMMIT='eec6ba8e4da8bafd25aadbfcb9afcbeca3ba3dda'
HC_COST='results/uarch/w16_gpu_hc_dot_schedule_20261001/cost_r1.json'
BURST='results/uarch/w19_burst_ingress_20261001/contract_r2.json'
OPCODE_PROOF='results/quality/w19_norm_opcode_proof_20261001/proof.json'


def inputs():
    return dict(schema='opentallas.w16.HC_vector_inputs.v1',profile=D.assumptions(),
        packing='BF16 shared loads serialized2-bank-conflict; scalar coefficient loads serialized32 lanes, no free shared-word broadcast. STORE16 uses even then odd-lane fullword RMW, no unimplemented byte-enable credit.',
        burst_lines=4,request_ports=1,prepare_cycles=1,request_grant_cycles=1,
        service='Isolated sequential operations; fixed450cycle credit wait allowance and500ns loadedHBM are assumptions, not measured upper bounds.',measured=False)


def masked_store_program(program):
    out=[]
    for op in program:
        if op['op']!='STORE16':out.append(op);continue
        source=op['src'][0]
        for odd in (False,True):
            pred='lane%2==1' if odd else 'lane%2==0'
            out.append(N.op('LOAD','rmw_word',shared=True,source='output BF16 pair word',predicate=pred))
            if odd:
                out.extend([N.op('SHR','mask',['@UFFFF0000','@U16']),N.op('AND','keep',['rmw_word','mask']),
                    N.op('OR','merged',['keep',source])])
            else:
                out.extend([N.op('SHR','low',[source,'@U16']),N.op('AND','keep',['rmw_word','@UFFFF0000']),
                    N.op('OR','merged',['keep','low'])])
            # Ordinary full32bit word store. Selected half retained, neighbor
            # remains from latest shared word; odd read follows even retirement.
            out.append(D.W.instruction('STS_PARTIAL',src=['merged'],shared=True,predicate=pred))
    return out


def packed_bank_penalty(program,warps):
    conflict=0;detail=[]
    for op in program:
        if op['op'] not in ('LOAD','LDS_PACKED_BF16','LDS32'):continue
        source=op.get('attributes',{}).get('source','')
        if source=='output BF16 pair word':factor=1  # masked16 lanes unique words
        elif source.startswith(('pre[','comb[','post[')) or source=='published norm scalar':factor=32
        elif op['op']=='LDS32':factor=1
        else:factor=2
        extra=(factor-1)*warps
        extract=2*6*warps if factor==2 else 0  # SHIFT/MASK packed half,RF2+INT3+issue1
        if source.startswith('ordered global'):factor=1;extra=0;extract=0
        conflict+=extra+extract;detail.append(dict(source=source or op['op'],serialized_accesses=factor,
            extra_shared_issue_cycles=extra,packed_half_extract_cycles=extract,warps=warps))
    return conflict,detail


def replay(program,warps,p):
    lowered=masked_store_program(program)
    result,trace=D.replay(lowered,warps,p)
    extra,detail=packed_bank_penalty(lowered,warps)
    result.update(bank_serialization_extra_cycles=extra,bank_accesses=detail,
        conditional_cycles=result['cycles']+extra,
        shared_RMW='Even and odd active16-lane groups own disjoint words; odd word load after even write retirement. Six address instructions between shared ops guarantee intra-warp visibility at assumedLAT2; all endpoint reuse still fenced.',
        RF_writes_to_physical_words=True)
    return result,trace


def layout(post=False):
    count=1024 if post else 256
    regions=[('residual_BF16',4*count*2),('coefficients_F32',80 if post else 16)]
    regions+= [('output_BF16',count*2),('control',4096)]
    if post:regions.append(('y_BF16',count*2))
    else:regions += [('pre_BF16',count*2),('gain_BF16',count*2),('local_and_global_norm_partials',256)]
    out=[];end=0
    for name,size in regions:
        end=(end+127)//128*128;out.append(dict(name=name,base=end,bytes=size));end+=size
    R.require(end<=65536,'shared overflow')
    return dict(regions=out,end_bytes=end,shared_capacity_SM=65536,
        policy='32SM shared budgets retained,20 active owners; pre/gain/result co-live, no alias/no inactive area credit.')


def norm_leaf_program():
    # Packed pre result squared sum. One warp owns32 aligned eight-term leaves
    # perSM;640leaves =>20partials padded32 then five adjacent tree levels.
    return D.W.chunk_program(True)


def build(evidence_commit=None):
    inp=R.read(INPUTS);R.require(inp['measured'] is False,'measured flag');p=inp['profile'];D.validate(p)
    evidence_commit=evidence_commit or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    hc=R.read(HC_COST);D.check(hc)
    burst=R.read(BURST);proof=R.read(OPCODE_PROOF)
    R.require(burst==B.build(),'burst r2 no longer reproduces')
    R.require((inp['burst_lines'],inp['request_ports'],inp['prepare_cycles'])==(4,1,1),'unsupported burst ports')
    euler_blob=subprocess.check_output(['git','show',EULER_COMMIT+':tools/w19_burst_admission.py'],cwd=ROOT)
    R.require(inp['request_grant_cycles']>0,'unpriced grant')
    R.require(burst['ports_and_schedule']['one_port_prepare_contexts_per_cycle']==4,'burst allocator changed')
    R.require(proof['verdict']=='PASS' and len(proof['fixtures'])==10,'norm opcode source proof drift')
    for path,digest in proof['source_pins'].items():R.require(R.sha(path)==digest,'norm opcode proof source drift '+path)
    calendar=R.read('results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json')
    R.require(calendar==N.build(),'norm calendar drift')
    pre,pre_trace=replay(N.vector_program('pre'),8,p)
    post,post_trace=replay(N.vector_program('post'),32,p)
    scale,scale_trace=replay(N.scale_program(),8,p)
    leaf,leaf_trace=replay(norm_leaf_program(),1,p)
    root,root_trace=replay(calendar['recipes']['norm_collector'],1,p)
    scalar,scalar_trace=replay(N.scalar_norm_program(),1,p)
    fabric=lambda cycles:math.ceil(cycles*p['serial_hz']/p['fabric_hz'])
    # Charge logical framed packets on single shared NoC; no free20-way
    # reduction or scalar broadcast. .9GHz domain waiting for1.2GHz fabric.
    network=lambda byte_count:p['bounded_credit_wait_cycles']+fabric(math.ceil(byte_count/p['NoC_bytes_cycle'])+p['network_startup_cycles'])+p['CDC_cycles']
    grid=fabric(5*(2*p['network_startup_cycles']+math.ceil(32*2*16/p['NoC_bytes_cycle'])))+p['barrier_latency']
    chain=dict(pre_vector=pre['conditional_cycles'],pre_visibility=grid,
        norm_local_chunk_tree=leaf['conditional_cycles'],norm_collect_20_partial_packets=network(20*16),
        norm_root_20_to32_padded_tree=root['conditional_cycles'],norm_scalar=scalar['conditional_cycles'],
        norm_broadcast_20_packets=network(20*16),norm_visibility=grid,
        scale_vector=scale['conditional_cycles'],result_visibility=grid)
    post_chain=dict(post_vector=post['conditional_cycles'],packed_store_visibility=grid)
    def transfer(byte_count):
        lines=math.ceil(byte_count/128)
        per_controller=math.ceil(lines/4)
        R.require(per_controller<=4096,'isolated transfer cannot retain lines in finite landing')
        bursts=math.ceil(per_controller/inp['burst_lines'])+6  # conservative six inputfamily tails/controller
        per_controller+=24  # six groups reserve four slots even for shortburst
        R.require(per_controller<=4096,'burst tail slots exceed finite landing')
        lines_to_same_SM=math.ceil(math.ceil(byte_count/20)/128)
        delivery_tail_after_last_response=4+max(0,lines_to_same_SM-1)
        controller=bursts*(inp['prepare_cycles']+inp['request_grant_cycles'])+math.ceil(p['loaded_HBM_ns']*1e-9*p['fabric_hz'])+delivery_tail_after_last_response
        read=p['bounded_credit_wait_cycles']+fabric(controller)+p['CDC_cycles']
        noc=network(lines*(128+p['NoC_frame_header_bytes']))
        # Direct contiguous vectors remain row-major; no coefficienttranspose.
        # Budget .9GHz serialized endpoint write port128B across20 activeSMs.
        shared=math.ceil(byte_count/128)+20*p['barrier_latency']
        return dict(operand_read_credit_wait=read,operand_stage=noc+shared,
            line_count=lines,lines_per_controller=per_controller,bursts_per_controller=bursts,
            lines_to_same_SM=lines_to_same_SM,delivery_tail_after_last_controller_response_cycles=delivery_tail_after_last_response,
            destination_ready_assumed=True,progress_deadline_validated=False,
            allocator_contexts_per_cycle=4,request_ports=1,request_grant_cycles_assumed=inp['request_grant_cycles'],
            burst_region_policy='Read-only bursts stop at family/region endpoint. Per-family512B tail fragmentation and actual address descriptors remain unqualified; current estimate rounds aggregatepercontroller, no placement qualification.')
    # Actual source operands; conservative reader stage issues one copy perrank,
    # with20endpoint coefficient/gain copies. No25-HBM activation reload credit.
    pre_bytes=4*5120*2+20*16+5120*2
    post_bytes=4*4*5120*2+4*5120*2+20*80  # y repeated forfour output copies
    pre_transfer=transfer(pre_bytes);post_transfer=transfer(post_bytes)
    pre_phases={k:pre_transfer[k] for k in ('operand_read_credit_wait','operand_stage')}
    post_phases={k:post_transfer[k] for k in ('operand_read_credit_wait','operand_stage')}
    pre_phases.update(gpu_simt_kernel=sum(chain.values()),result_stage=network(5120*2),local_drain_barrier=grid)
    post_phases.update(gpu_simt_kernel=sum(post_chain.values()),result_stage=network(4*5120*2),local_drain_barrier=grid)
    graph_path='tools/w19_composed_schedule_r2.py'
    blob=(ROOT/graph_path).read_bytes()
    S=types.ModuleType('expanded_r2');S.__file__=str(ROOT/graph_path);exec(compile(blob,S.__file__,'exec'),S.__dict__)
    g=S.graph(R.read(D.PROGRAM),hc['expanded_graph_source_pins'])
    R.require(len(g['nodes'])==13629,'r2graph phase schema changed')
    R.require(g['graph_sha256'].startswith('ba0d17e0af'),'r2 graph source pins differ')
    # Rebind by actual source-operation andphase identity; old graph SHA is
    # NOT transplanted. Historical HCcost/records remain byte-identical.
    hc_rebound={};hc_delta=[]
    for n in g['nodes']:
        op=g['operations'][n['source_operation_index']]
        if op.get('fn')!='hc_mixes':continue
        R.require(n['id'] in hc['node_costs'] and n['phase']==hc['node_costs'][n['id']]['phase'],'HC phase/schema rebind mismatch')
        entry=copy.deepcopy(hc['node_costs'][n['id']])
        delta=0
        if n['phase'].endswith('_read_credit_wait'):
            wave=int(n['phase'].split('_')[1][4:]);chunks=hc['waves'][wave]['chunks']
            same_SM_lines=math.ceil(chunks*8*6/128)
            tail=4+same_SM_lines-1
            delta=fabric(tail-3)
            entry['cycles']+=delta
            hc_delta.append(dict(node=n['id'],same_SM_lines=same_SM_lines,response_anchor_tail_cycles=tail,added_serial_cycles=delta))
        entry.update(waits_are_scenario_allowances=True,progress_deadline_validated=False,
            evidence=dict(commit=evidence_commit,path='tools/w16_gpu_hc_vector_costs.py',sha256=R.sha('tools/w16_gpu_hc_vector_costs.py')),
            scope='Immutable HC22 rebind toactualr2 phase identities;450scenarioallowance not validated bound.4+N-1 responseanchored landingtail assumesalways-ready singleSM delivery; NoC/consumer stalls unbounded.')
        hc_rebound[n['id']]=entry
    R.require(len(hc_rebound)==1760,'not allHC phases rebound')
    costs={};counts=Counter()
    for n in g['nodes']:
        op=g['operations'][n['source_operation_index']];fn=op.get('fn')
        if fn not in ('hc_pre_norm','hc_post','final_norm'):continue
        phase=post_phases if fn=='hc_post' else dict(
            operand_read_credit_wait=pre_phases['operand_read_credit_wait'],operand_stage=pre_phases['operand_stage'],
            pre_kernel=chain['pre_vector'],pre_norm_handoff_barrier=chain['pre_visibility'],
            norm_local_kernel=chain['norm_local_chunk_tree'],norm_partial_collect_credit_wait=chain['norm_collect_20_partial_packets'],
            norm_collector_kernel=chain['norm_root_20_to32_padded_tree'],norm_scalar_kernel=chain['norm_scalar'],
            norm_scalar_broadcast_credit_wait=chain['norm_broadcast_20_packets'],norm_scale_kernel=chain['scale_vector'],
            result_stage=pre_phases['result_stage']+chain['result_visibility'],local_drain_barrier=pre_phases['local_drain_barrier']+chain['norm_visibility'])
        R.require(n['phase'] in phase,'unpriced phase')
        counts[fn]+=1
        costs[n['id']]=dict(cycles=phase[n['phase']],clock_hz=p['serial_hz'],resource_units=20 if n['resource'] in ('simt','staging') else 1,
            finite_waits_included=True,waits_are_scenario_allowances=True,progress_deadline_validated=False,exact_gpu_lowering_bound=True,target_GPU_exactness=False,
            evidence=dict(commit=evidence_commit,path='tools/w16_gpu_hc_vector_costs.py',sha256=R.sha('tools/w16_gpu_hc_vector_costs.py')),
            scope='Positive assumed isolatedHCvector calendar; no measured waits, physical or complete-token qualification.')
    R.require(counts==Counter(hc_pre_norm=960,hc_post=400,final_norm=12),'source bindings drift')
    sources=[graph_path,INPUTS,HC_COST,BURST,OPCODE_PROOF,'tools/w19_burst_ingress.py','tools/w19_norm_opcode_proof.py','tools/w16_gpu_hc_vector_costs.py','tests/test_w16_gpu_hc_vector_costs.py',
        'tools/w19_gpu_norm_calendar.py','tools/w16_gpu_hc_dot_schedule.py','tools/w19_gpu_simd_contract.py',
        'tools/w19_hbm_tp96_isa.py','tools/hdc_golden.py','tools/hdc_golden_v41.py',
        'results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json']
    result=dict(schema='opentallas.w16.HC_vector_cost_provider.v1',cost_evidence_commit=evidence_commit,
        graph_sha256=g['graph_sha256'],scope='GPU_SIMT_FULL_TOKEN_MODEL',node_costs=costs,
        resource_capacities={'hbm':4,'staging':32,'simt':32,'barrier':32,'noc':1},
        HC_rebound_scenario_costs=hc_rebound,HC_response_tail_rebind=hc_delta,
        graph_rebind=dict(previous_graph_sha256=hc['graph_sha256'],new_graph_sha256=g['graph_sha256'],phase_count=13629,
            source=graph_path,HC_phase_identities_checked=True,old_cost_receipt_changed=False,preserved_transpose_cycles=35248,
            norm_phase_count=1372,scenario_only=True,validated_bound=False),
        calendars=dict(pre=pre,post=post,scale=scale,norm_local=leaf,norm_collector=root,norm_scalar=scalar),
        pre_norm_dependency_chain=chain,post_dependency_chain=post_chain,
        shared=dict(pre=layout(),post=layout(True)),phases=dict(pre_norm=pre_phases,post=post_phases),
        transfer_assumptions=dict(pre=pre_transfer,post=post_transfer,pre_bytes=pre_bytes,post_bytes=post_bytes),
        operations=dict(hc_pre_norm=80,hc_post=80,final_norm=1),priced_phase_nodes=1372,
        conditional_vector_token_us=(81*sum(pre_phases.values())+80*sum(post_phases.values()))/900,
        Euler_credit_qualification=dict(commit=EULER_COMMIT,path='tools/w19_burst_admission.py',sha256=hashlib.sha256(euler_blob).hexdigest(),
            credit450_is_validated_upper_bound=False,progress_deadline=None,loaded500ns_is_measurement=False,
            tail_anchoring='4fabriccycles afterlastacceptedcontrollerresponse only inno-stall singleline scenario; sameSMNline tail charged4+N-1 underalways-ready. Threecycles afterbankwrite is a different anchor. No bound underdest/controller stall.',
            actual_full_token_bound=None),
        new_burst_input=dict(path=BURST,single_request_port_wire_ceiling_bytes_second=614400000000,
            selected_request_ports=1,physical_storage_bytes_rank=burst['storage']['one_port_total_bytes_per_rank'],
            source_context_allocation_lines_cycle=4,grant_cycles=inp['request_grant_cycles'],
            old_HC22_repriced=False,two_port_or_1TB_credit=False,actual_grant_latency_qualified=False),
        numerical_source_input=dict(path=OPCODE_PROOF,fixtures=10,opcode_boundaries=890,norm_tree_supplied_to_scalar_LOAD=True,
            norm640_tree_target_proof=False,packed_word_RMW_target_proof=False),
        rounding='Source four-term seqsum starts p0; separate FMUL/FADD; canonical+0 at original rounded primitives. BF16 bias/lsb bit formula. Norm uses640chunk8leaves padded1024 and20contiguous partials padded32. IEEE DIV and3Newton steps, no reciprocal/nativeSFU.',
        assumption_scope=inp,physical_qualified=False,hardware_adopted=False,ready_to_build=False,headline_rate=None,
        full_token_cycles=None,scenario_costs_only=True,validated_progress_bound=False,bound_admission='REFUSED_NO_SOURCE_DESTINATION_PROGRESS_DEADLINES',pins={path:R.sha(path) for path in sources})
    return result,dict(pre=pre_trace,post=post_trace,scale=scale_trace,norm_local=leaf_trace,norm_collector=root_trace,norm_scalar=scalar_trace),g,S


def require_progress_bound(r):
    R.require(r.get('validated_progress_bound') is True,'REFUSED_NO_SOURCE_DESTINATION_PROGRESS_DEADLINES:450is onlyscenarioallowance')


def check(r):
    for path,pin in r['pins'].items():R.require(R.sha(path)==pin,'pin drift '+path)
    raw=subprocess.check_output(['git','show',r['cost_evidence_commit']+':tools/w16_gpu_hc_vector_costs.py'],cwd=ROOT)
    R.require(hashlib.sha256(raw).hexdigest()==r['pins']['tools/w16_gpu_hc_vector_costs.py'],'committed source drift')
    fresh,_,_,_=build(r['cost_evidence_commit']);R.require(fresh==r,'cost replay drift')


def main():
    ap=argparse.ArgumentParser(description=__doc__);m=ap.add_mutually_exclusive_group(required=True)
    m.add_argument('--out',type=Path);m.add_argument('--check',type=Path);a=ap.parse_args()
    if a.check:check(json.loads(a.check.read_text()))
    else:
        r,trace,_,_=build()
        with a.out.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
        with a.out.with_suffix('.trace.json').open('x') as f:json.dump(trace,f,separators=(',',':'));f.write('\n')
    print('PASS1372analyticalHCvector phases; physical/finite measured service and full-token qualification pending')


if __name__=='__main__':main()
