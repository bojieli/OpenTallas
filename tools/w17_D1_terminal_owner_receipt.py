"""Validate actual source-bound owner snapshot and prefix journal; never token credit."""
import hashlib
import json
import re
from pathlib import Path
from tools.w17_D1_reset_qualified_runtime_verify import verify_bound_execution,verify_priming

P='tb_D1_scope_core__DOT__';D=P+'probe__DOT__dut__DOT__';C=D+'u_tile__DOT__u_core__DOT__'
W=D+'g_packed_kv__DOT__g_window_hbm_attention__DOT__u_source__DOT__'
L=D+'g_packed_kv__DOT__u_desc_life__DOT__';Q=P+'probe__DOT__g_D1_current__DOT__'


def lower_bound(first_delta_cycles):
    if type(first_delta_cycles) is not int or first_delta_cycles<34:raise ValueError('invalid accepted read/reply delta')
    minimum_due_ps=10000+12500+1024+10000
    minimum_later_cycles=(minimum_due_ps+999)//1000
    return {'kind':'SOURCE_TIMING_LOWER_BOUND_NOT_DEADLINE','assumptions':'Pinned1000ps clock, one-credit sequential FR/FR_DONE, no retained/staged row; selected original provider timing parameters',
            'minimum_request_to_due_ps':minimum_due_ps,'minimum_later_reply_cycles':minimum_later_cycles,
            'next_request_edge_cycles':1,'actual_first_reply_cycles':first_delta_cycles,
            'row0_minimum_cycles_from_first_request':first_delta_cycles+16*(minimum_later_cycles+1),
            'all128_minimum_cycles_from_first_request':first_delta_cycles+(128*17-1)*(minimum_later_cycles+1),
            'upper_bound':None,'score_completion_deadline':None,'provider_arbitration_upper_bound':None,
            'fulltoken':False,'single_case_not_universal_liveness':True}


def parse(text,receipt,plan,live):
    if receipt.get('GDB_exit')!=0 or not receipt.get('input_postchecks') or not all(receipt['input_postchecks'].values()):
        raise ValueError('execution/hash failure')
    if live.get('actual_argv')!=plan['actual_run_argv_gap']['required_argv']:raise ValueError('actual program argv mismatch')
    if receipt['log_SHA256']!=hashlib.sha256(text.encode()).hexdigest():raise ValueError('raw log hash mismatch')
    if re.findall(r'^D1_INFERIOR_EXIT code=(\d+)$',text,re.M)!=['0']:raise ValueError('inferior terminal failure')
    if text.count('\nD1_TERMINAL_OWNER_CAPTURE_BEGIN\n')!=1 or text.count('\nD1_TERMINAL_OWNER_CAPTURE_END\n')!=1:
        raise ValueError('snapshot count')
    section=text.split('D1_TERMINAL_OWNER_CAPTURE_BEGIN\n',1)[1].split('D1_TERMINAL_OWNER_CAPTURE_END',1)[0]
    matches=re.findall(r'^D1_OWNER_(\d{3}) value=(\d+)$',section,re.M)
    if len(section.strip().splitlines())!=79 or [int(i) for i,v in matches]!=list(range(79)):
        raise ValueError('owner field cardinality/order/type')
    values={}
    for (name,meta),(i,value) in zip(plan['fields'].items(),matches):
        value=int(value)
        if value>=2**(meta['bytes']*8):raise ValueError('owner storage width')
        values[name]=value
    for name in [D+'fault_r',D+'att_packed_desc_fault',D+'win_service_fault',C+'e_fault',Q+'violations']:
        if values[name]!=0:raise ValueError('actual sticky fault')
    times=[];runtime=[]
    for line in text.splitlines():
        if line.startswith(('D1_OWNER_','D1_TERMINAL_OWNER_CAPTURE_','D1_INFERIOR_EXIT')):continue
        if line.startswith(('D1_REAL_GATE ','D1_REAL_DESCRIPTOR ','D1_REAL_ACCEPT ','D1_REAL_RESPONSE ','D1_REAL_WRITER_ACK ')):
            m=re.search(r'\btime=(\d+)\b',line)
            if not m or int(m[1])%1000 or int(m[1])<1000:raise ValueError('source time quantization')
            coarse=int(m[1]);exact=coarse-500
            times.append({'marker':line.split()[0],'reported_time_ps':coarse,'posedge_sample_ps':exact})
            line=line[:m.start(1)]+str(exact)+line[m.end(1):]
        runtime.append(line)
    # Original wrapper uses $time at 1ns units; print rounds half-ns posedges upward.
    # Model retains raw journal; only the verification projection converts known posedge markers.
    runtime_text='\n'.join(runtime)
    result=verify_bound_execution(runtime_text,0,live['actual_argv'],plan['actual_run_argv_gap']['required_argv'])
    verifies=verify_priming(text)
    accept=[x for x in times if x['marker']=='D1_REAL_ACCEPT'];response=[x for x in times if x['marker']=='D1_REAL_RESPONSE']
    if len(accept)!=1 or len(response)!=1:raise ValueError('expected one qualified first-return operation')
    delta=response[0]['posedge_sample_ps']-accept[0]['posedge_sample_ps']
    if delta<0 or delta%1000:raise ValueError('accepted operation timing')
    if {key:values[Q+key] for key in ('reads','returns','writes','acks')}!={'reads':1,'returns':1,'writes':0,'acks':0}:
        raise ValueError('captured/journal ledger mismatch')
    if values[Q+'pending']!=0 or values[Q+'target_seen']!=1:raise ValueError('pending endpoint mismatch')
    if values[W+'u_window__DOT__state']!=5 or values[W+'u_window__DOT__sec']!=1:
        raise ValueError('expected source next-sector FR state')
    masks={name.split('u_window__DOT__',1)[1]:value for name,value in values.items() if 'control_mask_word' in plan['fields'][name]}
    if any(v!=(0 if name.startswith('stage_valid') else 0xffffffff) for name,v in masks.items()):
        raise ValueError('reset/primed/staged control masks inconsistent')
    return {'status':'PASS_ACTUAL_ENROLLED_FIRST_RETURN_AND_OWNER_SNAPSHOT_EXPERIMENTAL_PREFIX_ONLY',
            'validation':result,'priming':verifies,'owner_values':values,'control_masks':masks,
            'source_phase_time_mapping':times,'time_mapping_rule':'REAL_* posedge $time is rounded in 1ns units: exact sample = reported -500ps; terminal/prime $realtime/context time remains exact',
            'descriptor_accept_sample_ps':next(x['posedge_sample_ps'] for x in times if x['marker']=='D1_REAL_DESCRIPTOR'),
            'read_accept_sample_ps':accept[0]['posedge_sample_ps'],'read_reply_sample_ps':response[0]['posedge_sample_ps'],
            'actual_reply_delta_cycles':delta//1000,'stage_lower_bound':lower_bound(delta//1000),
            'original_PC24_cause':'UNOBSERVED','fulltoken':False,'RTL_fidelity':'UNPROVEN',
            'debug_fault_summary_actual':values[D+'fault_r'],'dbg_fs_direct_snapshot':'NOT_CAPTURED; source guard checked it before finish',
            'snapshot_not_history':'coll_busy0/query-valid0/score-valid0 are final-point values, not lifetime quiescence proofs',
            'DROP_KV_OK_marker':'Mixed sampled-target/post-NBA field marker; no same-phase mutation qualification claimed',
            'finite_service_upper_bound':'BOUND_MISSING','first_return_deadline':None,'I66_calendar_used':False}
