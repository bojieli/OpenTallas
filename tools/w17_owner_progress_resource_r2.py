#!/usr/bin/env python3
"""Additive measured resource audit and existing-source 32-write calendar. No build."""
import hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROFILE=Path('/tmp/opentallas-core-retained-binary-full27-campaign-20261002-r2/physical_QE_gate/frontend_profile.json')
TRANSFER=PROFILE.parent.parent/'baseline/binary_transfer.json'
OWNER=Path('/home/ubuntu/w17-window-epoch-candidate')
PRED=OWNER/'results/uarch/w17_window_epoch9_producer_prediction_20261001_attempt3/prediction.json'
JOURNAL=PRED.parent/'L0_no_retain_events.jsonl'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def selected_files(command):return [Path(x) for x in command if x.endswith(('.sv','.v','.svh'))]
def cone(files):
    modules={};source_bytes=0
    for p in files:
        text=p.read_text();source_bytes+=p.stat().st_size
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
        for name,body in re.findall(r'\bmodule\s+(\w+)\b(.*?)\bendmodule\b',text,re.S):modules[name]=body
    graph={name:[dep for dep in modules if re.search(r'\b'+re.escape(dep)+r'\s*(?:#\s*\(|\w+\s*\()',body)] for name,body in modules.items()}
    todo=['tb'];seen=set()
    while todo:
        name=todo.pop()
        if name in seen:continue
        seen.add(name);todo.extend(graph.get(name,[]))
    return {'compile_input_files':len(files),'compile_input_bytes':source_bytes,'defined_unique_modules':len(modules),'syntactically_reachable_unique_modules':len(seen),'reachable_names':sorted(seen),'count_scope':'Static source-name dependency closure, BOTH generate arms included. Not elaborated replica/AST counts or linear compile-time/size prediction.'}
def find_key(x,key):
    if isinstance(x,dict):
        if key in x:return x[key]
        for v in x.values():
            z=find_key(v,key)
            if z is not None:return z
    elif isinstance(x,list):
        for v in x:
            z=find_key(v,key)
            if z is not None:return z
    return None
def validate_writer(events):
    intents=[e for e in events if e['kind']=='request'];acks=[e for e in events if e['kind']=='write_ack'];columns=[e for e in events if e['kind']=='column']
    if not len(intents)==len(acks)==len(columns)==32:raise ValueError('wrong writer geometry')
    for i,(req,ack,col) in enumerate(zip(intents,acks,columns)):
        sec=i//2 if i%2==0 else 16
        if not (req['address']==262144+127*17+sec and req['tag']==65536|sec and req['strobe']==(4294967295 if i%2==0 else 1<<(i//2))):raise ValueError('writer owner/address/mask contract')
        if not (ack['address']==col['address']==req['address'] and ack['tag']==col['tag']==req['tag'] and ack['cycle']==col['cycle']+1 and req['cycle']<=col['cycle']):raise ValueError('writer ACK accepted intent/column edge contract')
def build():
    profile=json.loads(PROFILE.read_text());transfer=json.loads(TRANSFER.read_text())
    failed=json.loads((ROOT/'results/rtl/w17_owner_progress_watchdog_20261002/attempt2_resource_FAIL/active_stage.json').read_text())
    old_files=selected_files(failed['command'])
    old_files=[ROOT/'rtl/test/w17_owner_progress_watchdog'/str(p).split('/rtl/test/w17_owner_progress_watchdog/',1)[1] for p in old_files]
    # Backend writer helper is reused without altering old generator or any RTL.
    sys.path.insert(0,str(OWNER/'tools'))
    spec=importlib.util.spec_from_file_location('existing_writer',OWNER/'tools/w17_window_epoch9_producer_prediction.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    pred=json.loads(PRED.read_text())
    if sha(OWNER/'tools/w17_window_epoch9_producer_prediction.py')!=pred['generator_sha256']:raise ValueError('writer generator pin changed')
    summary,events=mod.replay(pred['params'],128,0)
    stored=[json.loads(x) for x in JOURNAL.read_text().splitlines()]
    if events!=stored:raise ValueError('existing writer events mismatch; no fit')
    final_ack=summary['last_write_ack']
    write_events=[e for e in events if e['kind'] in ('block','write_ack','logical_publish','write_visible') or (e['kind'] in ('request','column') and e.get('we'))]
    validate_writer(write_events)
    basecone=cone(selected_files(profile['step']['command']));ownercone=cone(old_files)
    result={'status':'ADDITIVE_RESOURCE_PROPOSAL_R2_NOT_GO_NO_LAUNCH','prior_proposal_commit':'3e90da3c1ebd16b052e40f02615a2991bdd95752','old180second_and256MiB_aggregate_proposal':'WITHDRAWN_AS_UNJUSTIFIED; original proposal and resourceFAIL unchanged','source_commit':pred['source_commit'],'profile_pins':{str(p):sha(p) for p in (PROFILE,TRANSFER,PRED,JOURNAL,OWNER/'tools/w17_window_epoch9_producer_prediction.py',OWNER/'tools/w17_window_epoch9_timing_model.py')},'source_pins':pred['source_sha256'],
      'measured_profile':{'frontend_wall_seconds':profile['step']['wall_seconds'],'generated_bytes':profile['generated_bytes'],'generated_files':len(profile['files']),'baseline_CXX_seconds':find_key(transfer,'compiled_CXX_wall_seconds'),'baseline_cumulative_peak_bytes':find_key(transfer,'observed_cumulative_peak_bytes'),'parent_reported_other_CXX_seconds':362.172,'parent_other_CXX_receipt_not_yet_pinned':True,'frontend_options':profile['step']['command'][:profile['step']['command'].index('--Mdir')]},
      'cone_comparison':{'measured_fullcore':basecone,'owner_progress_actual_SU_WINDOW':ownercone,'shape_preserved':'SUN256 SUM64 and every SU helper unchanged; no full core/QE/ME instantiated by owner fixture. Source closure counts alone do not prove faster or smaller.','compile_options_changed':False,'owner_options':failed['command'][:failed['command'].index('--Mdir')]},
      'new_bounded_budget_proposal':{'memory_GiB':12,'CPU_workers':2,'affinity':[30,31],'swap_max':0,'shared_compile_seconds':750,'runtime_cases':5,'runtime_seconds_each':20,'reserve_seconds':50,'whole_seconds':900,'generated_aggregate_bytes':2*2**30,'per_file_bytes':256*2**20,'basis':'750s exceeds measured99.381 frontend +389.972 baselineCXX sum489.353 by~53%;2GiB aggregate is3.04x measured706497643-byte generated baseline. This is a resource margin proposal, not architecture gain or guaranteed success. Object/archive/log growth charged to same2GiB cap.','auto_retry':False,'fallback':False,'fresh_GO_required':True,'scope':'One compile plus bounded HEALTHY/HOLD_REQ/HOLD_RSP/OVERALL/WRITER cases; no wholeL0'},
      'writer_calendar':{'status':'EXISTING_SOURCE_WRITE_PREFIX_REPLAY_IDENTICAL_REUSED','source_hook':'Actual WINDOW WC/WC_DONE/WS/WS_DONE; credit/epoch change affects FR only. Writer prefix binds original unchanged source; no across-token retention claim.','fixture_inputs':{'synthetic_capture_first_cycle':300,'capture_vectors':16,'capture_full_cycle':315,'drain_issue_cycle':317,'source_first_block_cycle':317,'own_slot':127,'base_sector':262144,'clock_model_ps':1000,'NPC':32,'REFPB':3,'TAGW':17,'MEM_MODE':0,'MEM_WORDS':264320,'writer_hbm_payload_checkpoint':False,'reset_and_backend_state':'Same reset-origin cold no-competitor WriteBackend as immutable producer prediction; this is independent WRITER case, not a changed read-baseline start.'},'block_accepts':16,'write_accepts':32,'qualified_ACKs':32,'final_ACK_pre_NBA_cycle':final_ack,'logical_row_valid_after_NBA_same_edge':final_ack,'final_WRcolumn_ps':summary['last_WRcolumn_ps'],'projected_final_visibility_ps':summary['final_scale_visible_ps'],'physical_visibility_qualification':False,'max_source_write_credit':1,'events':write_events,'calendar_provenance':'Prior original FAIL and additive ACT/publication correction remain separate; no old prediction/runtime overwritten. Event timing reused; per-PC ACT omitted from this writer-only summary until corrected helper bound.','future_negative_controls':['unaccepted ACK','duplicate ACK','wrong owner ACK','early WC/WS ACK','masked scale corruption','out-of-aperture address/no alias','static ready counted as progress']},
      'remaining_before_GO':['Pin additive fixture actual four admission bits and qualified request/reply/writer ledgers; existing historicalprimecase0ACK is not positiveACK qualification.','Freeze WRITER case to this exact32intent source-controlled calendar; direct synthetic block stimulus allowed only with actual u_blocks drain/source writes, no synthetic ACKs.','Bind exact source/compiler/options/output-size/time/memory plan to fresh parentGO; preflight fresh fleet headroom and reservations.','No fullL0 or native publicbenchmark restart; actualoriginal callbacks unavailable, causal diagnosis remains unresolved.'],'admission':False,'physical_visibility':False,'new_builds':0}
    return result
if __name__=='__main__':print(json.dumps(build(),indent=2))
