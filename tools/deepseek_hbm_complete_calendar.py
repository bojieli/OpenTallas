#!/usr/bin/env python3
"""Source-bound per-op GPU calendar demand: candidate arithmetic, fail-closed services.

Ram composes the token graph. This exporter does not replace that graph or invent
bank/quad locality, controller timings, or missing SFU hardware implementations.
"""
import argparse
from collections import Counter
import hashlib
import json
import subprocess
from pathlib import Path
import deepseek_hbm_complete_program as P
import deepseek_hbm_complete_isa as I
import deepseek_hbm_complete_index as X
import deepseek_hbm_complete_canonical as Canon
import w19_gpu_compare_lowering as L
import w19_gpu_norm_calendar as N
import w19_gpu_attention_finish as A


LAT={'LOAD':2,'STORE':3,'SHFL':7,'FADD':9,'FMUL':9,'FCMP_GT':9,'FCMP_LT':9,'IADD':9,'ISUB':9}

def live(p,after=None):
    current=set() if after is None else set(after);peak=len(current)
    for i in reversed(p):
        src=set(x for x in i['src'] if isinstance(x,str) and not x.startswith('@')) if i['op']!='LOAD' else set()
        if i['op'].startswith('B'):
            yes,yp=live(i['yes'],current);no,np=live(i['no'],current);current=yes|no|src;peak=max(peak,yp,np,len(current))
        else:
            dst=i.get('dst') if i['op'] not in ['STORE','STORE32','STORE16'] else None
            peak=max(peak,len(current|({dst} if dst else set())))
            current.discard(dst);current|=src;peak=max(peak,len(current))
    return current,peak


def profile(p):
    counts=Counter();unbound=Counter();cycles=0;reads=writes=shared=0
    def walk(items):
        nonlocal cycles,reads,writes,shared
        for i in items:
            counts[i['op']]+=1
            if i['op'] not in LAT:unbound[i['op']]+=1
            cycles+=LAT.get(i['op'],9);reads+=len(i['src'])*1024
            if i['op']=='LOAD' or i['op'].startswith('STORE'):shared+=1
            if i['op'].startswith('B'):walk(i['yes']);walk(i['no'])
            elif i.get('dst') and not i['op'].startswith('STORE'):writes+=1024
    walk(p);_,peak=live(p)
    return {'warp_instruction_upper_all_divergent_arms':dict(counts),'proxy_cycles_assuming_UNBOUND_opcodes_9':cycles,'serial_dependency_cycles_upper_candidate':None if unbound else cycles,'unbound_opcode_counts':dict(unbound),
            'RF_read_bits_including_immediates':reads,'RF_write_bits':writes,'shared_issue_cycles_upper':shared,
            'peak_live_value_regs_upper':peak,'address_loop_regs':8,'RF32_fit':peak+8<=32,
            'branch_reconvergence_cycles':None,'SFU_INT_physical_qualified':False}


def build():
    g=P.compile_program();recipes={}
    for kind in ['FADD','FMUL','DIV','NEG','BF16','EXP','RSQRT','MAX','MIN']:
        recipes[kind]={'program':I.recipe(kind),'one_warp_candidate':Canon.events(I.recipe(kind),32)}
    for routed in [False,True]:
        p=I.swiglu_program(routed);recipes['SWIGLU_ROUTED' if routed else 'SWIGLU_SHARED']={'program':p,'one_warp_candidate':Canon.events(p,24)}
    for name,p in [('NORM_PRE',N.vector_program('pre')),('NORM_POST',N.vector_program('post')),('NORM_SCALAR',N.scalar_norm_program()),('NORM_SCALE',N.scale_program())]:
        recipes[name]={'program':p,'one_warp_candidate':Canon.events(p,1 if name=='NORM_SCALAR' else 32)}
    for rows in [128,640]:
        a=A.profile(rows)
        for name,p in a['recipes'].items():
            lp=L.lower(p);recipes[f'ATTN_{rows}_{name}']={'program':lp,'one_warp_candidate':Canon.events(lp,a['calendars'][name]['active_lanes'])}
    idx={'INDEX_QDQ_REPRESENTATION':X.decode_program(),'INDEX32_BLOCK_ROUND':X.K.program(),'INDEX32HEAD_TREE':X.reduce_program()}
    for name,p in idx.items():recipes[name]={'program':p,'one_warp_candidate':profile(p)}
    operations=[];missing=Counter()
    for i in g['instructions']:
        o=i['op'];fn=i['function'];phases=[];gaps=[]
        if fn=='swiglu':
            routed=o['slot']<6;name='SWIGLU_ROUTED' if routed else 'SWIGLU_SHARED'
            phases=[{'recipe':name,'warps_per_rank':1,'active_lanes':24,'finite_outer_iterations':1,'elements_per_rank':24}]
        elif fn in ['hc_pre_norm','hc_post','final_norm']:
            # Existing source-bound full-shape20SM normative decomposition;
            # actual complete-executor primitive roundtrip counts are separate.
            phases=[{'recipe_source':'tools/w19_gpu_norm_calendar.py','kind':fn,'full_shape':5120 if fn!='hc_post' else 20480,
                     'warp_lanes':32,'recipes':['NORM_POST'] if fn=='hc_post' else ['NORM_PRE','NORM_SCALAR','NORM_SCALE'],'norm_chunk8_count':640 if fn!='hc_post' else None,'norm_outer_warp_iterations':20 if fn!='hc_post' else None}]
            gaps+=['complete_executor_roundtrip_vs_lane_local_norm_calendar_binding','crossSM tree/broadcast word addresses and finite fabric']
        elif fn=='attend':
            rows=640 if o['yarn'] else 128
            phases=[{'rows':rows,'recipes':[f'ATTN_{rows}_{k}' for k in A.profile(rows)['recipes']],
                      'dot_source':'tools/w19_gpu_attention_dots.py','head_ranks':64}]
            gaps+=['actualSM word/bank addresses and phase matching','table delivery, finite collective and HBM/CDC event cycles']
        elif fn=='index_scores':
            n=o['n'];rank_rows=[(n//768)*8+min(8,max(0,n%768-r*8)) for r in range(96)]
            phases=[{'head_lanes_per_key_warp':32,'dimensions':128,'blocks32':4,'rows_per_rank':rank_rows,
                     'finite_outer_iterations_per_rank':[(v+1023)//1024 for v in rank_rows],
                     'global_ids':'(i//8)%96 owner; no modulo capacity alias','recipes':list(idx),'four_block_combination':'8 FADD from+0 incl4paddedzero, BF16; MAXpositivezero;weightFMUL/BF16;head32 chunk8+tree/BF16'}]
            gaps+=['packed68B producer/decoder and BF16/F64 storage bridge','query/key transpose and all sharedbank maps',
                    'mixed-lane reconvergence and crossquad/NoC','fullshape scratch refill/liveness before capacity admission']
        else:
            gaps.append('complete ordinaryGPU instruction expansion for '+fn)
        # No token rate/physical launch passes with these unresolved interfaces.
        gaps+=['production finite HBM request/return/writevisible/consumerdone/reverseCDC','quad placement/locality and combined750B/fastcycle service','contextual SS/FF ordinaryINT/SFU/ALU/RF qualification']
        missing.update(gaps)
        operations.append({'pc':i['pc'],'layer':i['layer'],'source_op_id':i['source_op_id'],'function':fn,
          'participants':o.get('ranks','row_partition96' if o['kind']=='mv' else 'all'),
          'matrix_shape':[o['n'],o['k']] if o['kind']=='mv' else None,
          'dependencies':[] if i['pc']==0 else [i['pc']-1],'issue_policy':'serial reference graph; no overlap credit',
          'ordinary_recipe_phases':phases,'RF_read_ports':2,'RF_write_ports':1,'shared_capacity_bytes':65536,
          'shared_bytes_per_serial_0p9GHz_cycle':128,'shared_bytes_per_fast_1p2GHz_cycle':96,
          'shared_word_bank_map':None,'RF_write_calendar_binding':None,'quad_placement':None,
          'callbacks':{'issue':'software execute_instruction enter','RFready':None,'resultvisible':'software handler return only',
                      'memaccept':'PersistentMemory.submit','writevisible':'software actual_backend_event only; no DRAM credit',
                      'consumerdone':'PersistentMemory.consume','creditreturn':'software consume only; physical reverseCDC unbound'},
          'qualified_cycles':None,'missing_costs':gaps,'physical_calendar_admission':'FAIL_CLOSED'})
    evidence='results/rtl/deepseek_hbm_complete_20261001/checkpoint-full-40-head-r1.json'
    actual=json.loads((P.ROOT/evidence).read_text())
    if actual['verdict']!='PASS' or len(actual['operator_receipts'])!=len(operations) or actual['perlayer_reference_injection']:
        raise ValueError('authoritative fullsoftware callbacks missing/invalid')
    verified={}
    for path,want in actual['source_pins'].items():
        got=hashlib.sha256(subprocess.check_output(['git','show',actual['source_commit']+':'+path],cwd=P.ROOT)).hexdigest()
        if got!=want:raise ValueError('historical execution sourceblob drift '+path)
        verified[path]=got
    for operation,receipt in zip(operations,actual['operator_receipts']):
        if operation['pc']!=receipt['pc'] or operation['function']!=receipt['function'] or not receipt['completed']:
            raise ValueError('callback source instruction mismatch')
        operation['actual_software_callbacks']={'completed':True,'CPU_wall_s':receipt['CPU_wall_s'],
             'numerical_backend_at_execution':receipt['numerical_backend'],'RF_shared_physical_timeline':None}
    actual_callbacks={'source_commit':actual['source_commit'],'execution_evidence':evidence,'execution_evidence_sha256':P.digest(evidence),
       'historical_source_blobs_verified':verified,'memory':actual['memory'],'memory_trace_is_complete':False,
       'collective_events':actual['collective_events'],'full_software_gate':'PASS','head':actual['head'],
       'does_not_qualify_prospective_new_lowering':True,'physical_RF_or_shared_timeline_bound':False}
    paths=['tools/deepseek_hbm_complete_calendar.py','tools/deepseek_hbm_complete_canonical.py','tools/deepseek_hbm_complete_index.py','tools/deepseek_hbm_complete_isa.py']
    return {'schema':'opentallas.deepseek.hbm.complete-calendar-demand.v1','source_pins':{**g['source_pins'],**{p:P.digest(p) for p in paths}},
      'instructions':[{'id':o['pc'],'dependencies':o['dependencies'],'layer':o['layer'],'function':o['function']} for o in operations],
      'serial_DAG_authority':'066 source execute(program) instruction loop; execute_instruction actual memory+fabric fence before nextpc',
      'actual_software_callbacks':actual_callbacks,'operations':operations,'recipes':recipes,'missing_class_counts':dict(missing),'whole_program_op_count':len(operations),
      'model_authority':'Ram whole-token dependency/service graph; Boyle contextual floorplan/calendar validation',
      'full_program_arithmetic_lowering_complete':False,'whole_program_physical_admission':'FAIL_CLOSED',
      'hardware_build_authorized_by_this_record':False,'full_token_rate':None}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise SystemExit('refuse evidence overwrite')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),separators=(',',':'))+'\n')
