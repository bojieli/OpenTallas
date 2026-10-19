#!/usr/bin/env python3
"""Private Stage1 trace extraction. Never emits a schedule or drives RTL."""
import argparse,collections,copy,hashlib,json,re
from pathlib import Path

def events(path):
    out=[]
    for line in path.read_text().splitlines():
        if not line.startswith('QWEVENT|'):continue
        t=line.split('|')
        if len(t)!=8:raise ValueError('malformed actual event: '+line)
        out.append(dict(time_ps=int(t[1]),instance=t[2],edge=int(t[3]),reset_epoch=int(t[4]),event=t[5],value=t[6],aux=t[7],clock='ck',sampling='pre-NBA posedge'))
    return out

def validate_boot(ev):
    errors=[];edges=[];by=collections.defaultdict(list)
    if not ev:return ['MISSING_ALL_EVENTS'],[]
    for e in ev:
        by[e['event']].append(e)
        if e['reset_epoch']!=1:errors.append('RESET_EPOCH_MISMATCH')
    # The original bench's common clock is a functional diagnostic assumption.
    # This checks trace coherence, never native insertion or physical phase.
    origin={}
    for e in ev:
        v=e['time_ps']-e['edge']*10000
        old=origin.setdefault(e['instance'],v)
        if old!=v:errors.append('CLOCK_EDGE_TIME_MISMATCH')
    for inp,cap,n in [('PW_CAPTURE','MACRO_PW_RECEIPT',1024),('DW_CAPTURE','MACRO_DW_RECEIPT',8)]:
        x=by[inp];y=by[cap]
        if len(x)!=n or len(y)!=n:errors.append('MISSING_'+cap)
        xi={int(e['value']):e for e in x};yi={int(e['value']):e for e in y}
        if set(xi)!=set(range(n)) or set(yi)!=set(range(n)):errors.append('ADDRESS_COVERAGE_'+cap)
        for a in sorted(set(xi)&set(yi)):
            p,q=xi[a],yi[a]
            if q['edge']-p['edge']!=2:errors.append('SOURCE_CAPTURE_RELATION_'+cap)
            edges.append(dict(source_event=inp,destination_event=cap,address=a,observed_edges=q['edge']-p['edge'],source_axis='common functional bench ck only',native_qualified=False))
    for name in ['INSTALL_BEGIN','INSTALL_AUTH','INSTALL_COMMIT']:
        if len(by[name])!=1:errors.append('MISSING_'+name)
    if all(len(by[k])==1 for k in ['INSTALL_BEGIN','INSTALL_AUTH','INSTALL_COMMIT']):
        b,a,c=(by[k][0]['edge'] for k in ['INSTALL_BEGIN','INSTALL_AUTH','INSTALL_COMMIT'])
        if not b<a<c:errors.append('INSTALL_ORDER')
    if len(by['CAL_ROM_REQUEST'])!=44 or len(by['CAL_ROM_RESPONSE'])!=44:errors.append('ROM_EVENT_COVERAGE')
    if len(by['CAL_ISSUE_CAPTURE'])!=166:errors.append('ISSUE_EVENT_COVERAGE')
    return sorted(set(errors)),edges

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--boot-only',action='store_true');a=ap.parse_args();p=a.root
    raw=p/'receipts/out2/cap1_nominal.out2';ev=events(raw);errors,edges=validate_boot(ev)
    assert not errors,errors
    tests={}
    for name,event,field,value in [('missing_read','CAL_ROM_RESPONSE',None,None),('wrong_clock','PW_CAPTURE','edge',999),('wrong_reset','MACRO_PW_RECEIPT','reset_epoch',2),('missing_address','MACRO_PW_RECEIPT',None,None)]:
        altered=copy.deepcopy(ev);i=next(i for i,e in enumerate(altered) if e['event']==event)
        if field:altered[i][field]=value
        else:altered.pop(i)
        rejected,_=validate_boot(altered);assert rejected,name;tests[name]=rejected
    equality={};negatives={}
    expected={'cap1_payload_digest_mut':'CALENDAR_RECEIVER_REJECT','cap1_clear_cap_mut':'CALENDAR_RECEIVER_CAP1_REQUIRED','cap1_auth_digest_mut':'CALENDAR_RECEIVER_REJECT','cap1_early_execution_mut':'CALENDAR_RECEIVER_REJECT','cap1_missing_final_drain_mut':'CALENDAR_RECEIVER_NOT_COMMITTED'}
    codes=dict(line.split() for line in (p/'receipts/out2/exit_codes.txt').read_text().splitlines())
    for name in ['cap1_nominal',*expected]:
        x=p/'receipts'/(name+'.log');y=p/'receipts/out2'/(name+'.trace')
        assert x.read_bytes()==y.read_bytes(),name
        equality[name]=dict(byte_equal=True,baseline_sha256=hashlib.sha256(x.read_bytes()).hexdigest())
        if name in expected:
            s=(p/'receipts/out2'/(name+'.out2')).read_text();assert int(codes[name])!=0 and expected[name] in s,name
            negatives[name]=dict(rc=int(codes[name]),actual_DUT_reject_marker=expected[name],probe_events=len(events(p/'receipts/out2'/(name+'.out2'))))
    missing=[dict(node=n,status='UNRESOLVED',actual_events=0,reason=r) for n,r in [
      ('SYSFACE_BOOT_REPLAY','Boot PW/DW stimulus is original cap1 event file; actual SYSFACE dq_prog/ROM replay producer is absent.'),
      ('CALR_TO_CTLM_HEAD','No selected CALR->head accepted command connection in this bench.'),
      ('ME_ACCEPT_AND_MEM_PIPE','One production-shaped ME part has not been connected or executed.'),
      ('XPF_TAP_WRITE_OWNER','No actual producer transaction or address/write coverage from the selected programme.'),
      ('XPF_HEAD_LEAF_QD','One actual head with its real leaves/two epochs has not been connected or executed.'),
      ('ROM_ENTRY_AT_ISSUE','Existing issue register carries command/user but no immutable source-entry address; retrospective counter inference forbidden.'),
      ('PRODUCER_TIMING','Four original ME timing mismatches remain; native KV/tile_first40 unmeasured.'),
      ('NATIVE_CLOCK_RESET_PHASE','Only common functional bench clock measured; actual regional roots/epochs/first-use remain NULL.'),
      ('SERIALIZER_ORIGINAL_BYTES','Current expected.hex be976ca5 differs from ledger1f5b521d whose original bytes remain absent.')]]
    report=dict(schema='opentallas.qwen.private-source-event-graph.stage1.v1',scope='PASSIVE BOOT FIRST LEG ONLY; not connected minimum ME/XPF vehicle',boot_observation='PASS',complete_graph_verdict='UNRESOLVED_FAIL_CLOSED',events=ev,observed_capture_edges=edges,architectural_trace_equality=equality,actual_causal_RTL_negatives=negatives,trace_checker_mutants=tests,unresolved=missing,native_phase=None,token_cycles=None,handles_or_list_size_choice=None,profile_modified=False)
    (p/'graph.json').write_text(json.dumps(report,indent=2)+'\n')
    print('BOOT_PASSIVE_OBSERVATION_PASS 1032 actual PW/DW receipts; six exact traces; five real RTL rejects; four checker mutants reject')
    print('FULL_SOURCE_GRAPH_UNRESOLVED '+','.join(x['node'] for x in missing))
    if not a.boot_only:raise SystemExit(2)
if __name__=='__main__':main()
