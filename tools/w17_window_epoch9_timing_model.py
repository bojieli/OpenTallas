#!/usr/bin/env python3
"""Pinned read-only WINDOW/idx_hbm cycle transcription. Predict before RTL measurement."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
IDX='rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'
BENCH='/tmp/opentallas-window-connected-baseline-20261001/rtl/test/w17_window_connected_baseline/tb.sv'

def sha(b): return hashlib.sha256(b).hexdigest()
def pc(a): return ((a>>2)^(a>>7)^(a>>12))&31
def bank(a): return ((((a>>12)^((a>>15)>>2))&7)<<2)|((a^(a>>15))&3)

class Backend:
    def __init__(self, params):
        self.t=params
        self.s=[]
        self.offers=[False]*32
        self.qfree=[0]*32
        for p in range(32):
            self.s.append(dict(q=[],r=[],head=None,skip=0,open=[False]*32,row=[0]*32,
                act=[0]*32,actok=[0]*32,preok=[0]*32,lastact=-1000000,
                actbg=[-1000000]*4,faw=[-1000000]*4,col=-1000000,colbg=[-1000000]*4,
                nref=params['REFI_PS']//32+params['REFI_PS']*p//1024,
                refdone=set(),reads=0,acts=0,refs=0,hits=0,conflicts=0,
                qmax=0,rmax=0,bypasses=0,held=0))
    def estimate(self,s,d,now):
        t=self.t;a=d['address'];arr=d['arr'];bk=bank(a);bg=bk&3
        if s['open'][bk] and s['row'][bk]==a>>15: act=s['act'][bk]
        else:
            act=max(arr+t['REQ_PS'],s['preok'][bk])+t['RP_PS'] if s['open'][bk] else arr+t['REQ_PS']
            act=max(act,s['actok'][bk],s['lastact']+t['RRDS_PS'],s['actbg'][bg]+t['RRDL_PS'],s['faw'][0]+t['FAW_PS'])
        return max(arr+t['REQ_PS'],now,act+t['RCDRD_PS'],s['col']+t['BURST_PS'],s['colbg'][bg]+t['TCCDL_PS'])
    def schedule(self,s,d,now):
        t=self.t;a=d['address'];bk=bank(a);bg=bk&3;tmin=d['arr']+t['REQ_PS']
        while s['nref']<=max(tmin,s['col']):
            counts=Counter(bank(x['address']) for x in s['q']);counts[bk]+=t['QD']+1
            chosen=min((b for b in range(32) if b not in s['refdone']),key=lambda b:(counts[b],-s['act'][b],b))
            s['refdone'].add(chosen)
            if len(s['refdone'])==32:s['refdone'].clear()
            tr=s['nref']
            if s['open'][chosen]:tr=max(tr,s['preok'][chosen])+t['RP_PS']
            s['open'][chosen]=False;s['actok'][chosen]=max(s['actok'][chosen],tr+t['RFCPB_PS'])
            s['nref']+=t['REFI_PS']//32;s['refs']+=1
        if s['open'][bk] and s['row'][bk]==a>>15:
            s['hits']+=1;act=s['act'][bk]
        else:
            if s['open'][bk]:s['conflicts']+=1;act=max(tmin,s['preok'][bk])+t['RP_PS']
            else:act=tmin
            act=max(act,s['actok'][bk],s['lastact']+t['RRDS_PS'],s['actbg'][bg]+t['RRDL_PS'],s['faw'][0]+t['FAW_PS'])
            s['faw']=s['faw'][1:]+[act];s['lastact']=act;s['actbg'][bg]=act
            s['open'][bk]=True;s['row'][bk]=a>>15;s['act'][bk]=act
            s['actok'][bk]=act+t['RAS_PS']+t['RP_PS'];s['preok'][bk]=act+t['RAS_PS'];s['acts']+=1
        col=max(tmin,now,act+t['RCDRD_PS'],s['col']+t['BURST_PS'],s['colbg'][bg]+t['TCCDL_PS'])
        s['col']=col;s['colbg'][bg]=col;s['preok'][bk]=max(s['preok'][bk],col+t['RTP_PS'])
        return col
    def edge(self,c,request,selected):
        t=self.t;now=c*t['CLK_PS']
        if selected is not None:self.s[selected]['r'].pop(0)
        for p in range(32):
            s=self.s[p]
            if self.offers[p] and selected!=p:s['held']+=1
        if request is not None:
            p=pc(request['address']);s=self.s[p];assert self.qfree[p]>=1
            s['q'].append(dict(request,arr=now));s['qmax']=max(s['qmax'],len(s['q']))
        for p,s in enumerate(self.s):
            for _ in range(4):
                if not s['q'] or len(s['r'])>=t['RQD']:continue
                if s['head'] is None:
                    sel=0;best=self.estimate(s,s['q'][0],now)
                    if s['skip']<t['MAXSKIP']:
                        for i in range(1,min(t['RW'],len(s['q']))):
                            est=self.estimate(s,s['q'][i],now)
                            if est<best:best=est;sel=i
                    if sel:s['q'].insert(0,s['q'].pop(sel));s['skip']+=1;s['bypasses']+=1
                    else:s['skip']=0
                    s['head']=self.schedule(s,s['q'][0],now)
                if s['head']<=now:
                    d=s['q'].pop(0);due=s['head']+t['CL_PS']+t['BURST_PS']+t['RSP_PS']
                    s['r'].append(dict(d,due=due));s['reads']+=1;s['head']=None;s['rmax']=max(s['rmax'],len(s['r']))
            self.offers[p]=bool(s['r'] and s['r'][0]['due']<=(c+1)*t['CLK_PS'])
            self.qfree[p]=t['QD']-len(s['q'])

def replay(credits,start,params):
    b=Backend(params);events=[];row=0;epoch=0;issued=received=pending=nxt=0
    state='IDLE';pf_edge=start+1;maxpending=0;stalls=0;lastreply=None;reqs=reps=0
    scale_edges=[]
    for c in range(200001):
        selected=next((p for p,v in enumerate(b.offers) if v),None)
        reply=b.s[selected]['r'][0] if selected is not None else None
        request=None
        if state=='FR' or (state=='PIPE' and pending<credits and (nxt<16 or (nxt==16 and received&65535==65535))):
            sec=nxt;address=262144+row*17+sec
            tag=(epoch<<5)|sec if credits>1 else sec
            if b.qfree[pc(address)]>=1:
                request=dict(address=address,tag=65536|tag,row=row,sector=sec,epoch=epoch)
                events.append(dict(kind='request',cycle=c,pc=pc(address),**request));reqs+=1
            else:stalls+=1
        # All source updates use the pre-edge state/masks, matching nonblocking RTL.
        if c==pf_edge:
            assert state=='IDLE' and pending==0 and not any(s['q'] or s['r'] for s in b.s)
            epoch=(epoch+1)&511 if credits>1 else epoch
            issued=received=pending=nxt=0;state='PIPE' if credits>1 else 'FR'
        elif request:
            issued|=1<<nxt;nxt+=1;pending+=1
            if credits==1:state='WAIT'
        if reply is not None:
            sec=reply['sector']
            assert reply['row']==row and reply['epoch']==epoch and issued>>sec&1 and not(received>>sec&1)
            assert state in ('PIPE','WAIT') and (sec!=16 or received&65535==65535)
            received|=1<<sec;pending-=1;reps+=1;lastreply=c
            events.append(dict(kind='reply',cycle=c,pc=selected,**{k:reply[k] for k in ('address','tag','row','sector','epoch')}))
            if sec==16:
                assert pending==0 and received==131071
                scale_edges.append(c);state='IDLE';row+=1;pf_edge=c+2
            elif credits==1:state='FR'
        b.edge(c,request,selected)
        assert sum(len(s['q'])+len(s['r']) for s in b.s)==pending
        maxpending=max(maxpending,pending)
        assert pending<=credits
        if row==128:break
    assert row==128 and reqs==reps==2176
    # Final scale edge B: stage asserted post B+1, sampled pre B+2; stream_go next negedge.
    # Merge accepts B+3; stage4 is two-register response, so 32 beats consume four cycles each.
    # Last merge done samples at B+132; schedule done is sampled by bench B+133.
    metrics=dict(start=start,staged=lastreply+2,done=lastreply+133,refill=lastreply-start+1,
                 reads=reqs,replies=reps,beats=32,max_inflight=maxpending)
    perpc=[dict(pc=p,reads=s['reads'],q=len(s['q']),r=len(s['r']),refreshes=s['refs'],activations=s['acts'],
                hits=s['hits'],conflicts=s['conflicts'],qmax=s['qmax'],rmax=s['rmax'],bypasses=s['bypasses'],held=s['held']) for p,s in enumerate(b.s)]
    assert all(s['reads']==68 and s['q']==s['r']==0 for s in perpc)
    return dict(credits=credits,metrics=metrics,last_scale_response=lastreply,request_stalls=stalls,
                per_PC=perpc,scale_response_cycles=scale_edges),events

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);args=ap.parse_args()
    raw=subprocess.check_output(['git','show',PIN+':'+IDX],cwd=ROOT);assert (ROOT/IDX).read_bytes()==raw
    names=['QD','RQD','RW','MAXSKIP','CLK_PS','BURST_PS','TCCDL_PS','CL_PS','RCDRD_PS','RP_PS','RAS_PS','RTP_PS','RRDS_PS','RRDL_PS','FAW_PS','REQ_PS','RSP_PS','REFI_PS','RFCPB_PS']
    params={n:int(re.search(r'parameter (?:integer|longint)\s+'+n+r'\s*=\s*(\d+)',raw.decode())[1]) for n in names}
    baseline_dir=ROOT/'results/uarch/w17_window_epoch9_baseline_comparison_20261001'
    baseline=json.loads((baseline_dir/'baseline_record.json').read_bytes());log=(baseline_dir/'baseline_runtime.log').read_text()
    out=(ROOT/args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();arms={}
    for credits in (1,8):
        arm,events=replay(credits,12300,params);arms[str(credits)]=arm
        (out/f'credit{credits}_events.jsonl').write_text(''.join(json.dumps(e,separators=(',',':'))+'\n' for e in events))
    measured=baseline['metrics'];mismatches={k:dict(predicted=arms['1']['metrics'][k],measured=v) for k,v in measured.items() if arms['1']['metrics'][k]!=v}
    drains={int(p):(int(r),int(a)) for p,r,a in re.findall(r'PC_DRAIN pc=(\d+) reads=68 q=0 r=0 refreshes=(\d+) activations=(\d+)',log)}
    for p in arms['1']['per_PC']:
        if (p['refreshes'],p['activations'])!=drains[p['pc']]:mismatches['pc'+str(p['pc'])]=dict(predicted=[p['refreshes'],p['activations']],measured=drains[p['pc']])
    r=dict(schema='opentallas.window_epoch9.connected_timing_prediction.v1',source_commit=PIN,idx_sha256=sha(raw),model_sha256=sha(Path(__file__).read_bytes()),params=params,
        reset_start='Backend reset cyc0 at clock0.5ns; rst_n rises1.1ns; first enabled edge1.5ns is cyc0. Source start sampled cyc12300. Same parent fixture.',
        edge_contract=dict(first_prefetch=12301,first_request=12302,
            final_response='B',refill='B-start+1',stage_asserted_after_edge='B+1',bench_staged_sample='B+2',bench_done_sample='B+133',
            prior_failure='Prior record identified ONE_CYCLE_EDGE_CONVENTION_MISMATCH; model_r2 incorrectly labeled post-NBA stage assertion as pre-edge bench sample. Failure preserved; corrected from RTL FSM/NBA semantics, not fit.'),
        backend_contract='All finite QD64/RQD32 queues, 4 issue iterations per PC, RW16/MAXSKIP16 FR-FCFS, REFPB3 queue counts and MRU ties, registered offers, lowest-PC KARB consume. Read-only/no competitors/writes/SHARE. Exact owner100 and9-bit source epochs1..128.',
        arms=arms,baseline_mismatches=mismatches,
        verdict='READY_PREDICTION_BEFORE_CANDIDATE_MEASUREMENT' if not mismatches else 'FAIL_BASELINE_MODEL_MISMATCH_PRESERVED',
        model_wall_seconds=time.monotonic()-started,
        event_sha256={f'credit{c}':sha((out/f'credit{c}_events.jsonl').read_bytes()) for c in (1,8)},
        candidate_measurement=None,
        preflight=dict(workers_max=2,address_space_bytes=4*1024**3,total_wall_cap_seconds=180,
            backend_payload_bytes=264320*32,source_declared_bits=606718,backend_queue_bound_beats=32*(64+32),
            prior_baseline_compilation_seconds=baseline['compile']['elapsed_seconds'],prior_baseline_runtime_allocated_MB=15),
        limits=['Behavioral CLK_PS1000 only; no physicalclock','Historical prime API generated nonpoison sectors; no actual producer/fulltoken/checkpoint proof','One cold event origin; no40layer/warmtoken transfer','Healthy epoch contract only; external fault recovery needs quiescence/nonreplay','No constant-L fit/divideby8; source admission changes refresh/FR-FCFS state'])
    (out/'prediction.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(verdict=r['verdict'],mismatches=mismatches,arms={k:v['metrics'] for k,v in arms.items()},seconds=r['model_wall_seconds']),indent=2))
    return bool(mismatches)
if __name__=='__main__':raise SystemExit(main())
