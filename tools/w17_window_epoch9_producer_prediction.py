#!/usr/bin/env python3
"""Finite write+refill+QK/PV prediction and visibility audit. No RTL execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from w17_window_epoch9_timing_model import Backend, pc, bank

ROOT=Path(__file__).resolve().parents[1]
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
IDX='rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'
BASE=262144
POS=1048575

def sha(b):return hashlib.sha256(b).hexdigest()
def pattern(a):
    n=a-BASE
    return bytes(120+i%5 if n%17==16 else 1+(n*3+i)%100 for i in range(32))

class WriteBackend(Backend):
    def __init__(self,t):
        super().__init__(t)
        self.write_offer=None;self.events=[];self.visibility={};self.write_times={}
        for s in self.s:s.update(last_rd=-1,last_wr=-1,last_wr_bg=None,writes=0)
    def estimate(self,s,d,now):
        t=self.t;a=d['address'];arr=d['arr'];bk=bank(a);bg=bk&3
        if s['open'][bk] and s['row'][bk]==a>>15:act=s['act'][bk]
        else:
            act=max(arr+t['REQ_PS'],s['preok'][bk])+t['RP_PS'] if s['open'][bk] else arr+t['REQ_PS']
            act=max(act,s['actok'][bk],s['lastact']+t['RRDS_PS'],s['actbg'][bg]+t['RRDL_PS'],s['faw'][0]+t['FAW_PS'])
        return max(arr+t['REQ_PS'],now,act+t['RCDWR_PS' if d['we'] else 'RCDRD_PS'],s['col']+t['BURST_PS'],s['colbg'][bg]+t['TCCDL_PS'])
    def schedule(self,s,d,now):
        t=self.t;a=d['address'];bk=bank(a);bg=bk&3;tmin=d['arr']+t['REQ_PS']
        from collections import Counter
        while s['nref']<=max(tmin,s['col']):
            counts=Counter(bank(x['address']) for x in s['q']);counts[bk]+=t['QD']+1
            chosen=min((b for b in range(32) if b not in s['refdone']),key=lambda b:(counts[b],-s['act'][b],b))
            s['refdone'].add(chosen)
            if len(s['refdone'])==32:s['refdone'].clear()
            tr=s['nref']
            if s['open'][chosen]:tr=max(tr,s['preok'][chosen])+t['RP_PS']
            s['open'][chosen]=False;s['actok'][chosen]=max(s['actok'][chosen],tr+t['RFCPB_PS'])
            s['nref']+=t['REFI_PS']//32;s['refs']+=1
        if s['open'][bk] and s['row'][bk]==a>>15:s['hits']+=1;act=s['act'][bk]
        else:
            if s['open'][bk]:s['conflicts']+=1;act=max(tmin,s['preok'][bk])+t['RP_PS']
            else:act=tmin
            act=max(act,s['actok'][bk],s['lastact']+t['RRDS_PS'],s['actbg'][bg]+t['RRDL_PS'],s['faw'][0]+t['FAW_PS'])
            s['faw']=s['faw'][1:]+[act];s['lastact']=act;s['actbg'][bg]=act
            s['open'][bk]=True;s['row'][bk]=a>>15;s['act'][bk]=act
            s['actok'][bk]=act+t['RAS_PS']+t['RP_PS'];s['preok'][bk]=act+t['RAS_PS']
        col=max(tmin,now,act+t['RCDWR_PS' if d['we'] else 'RCDRD_PS'],s['col']+t['BURST_PS'],s['colbg'][bg]+t['TCCDL_PS'])
        if not d['we'] and s['last_wr']>=0:
            col=max(col,s['last_wr']+t['CWL_PS']+t['BURST_PS']+t['WTRL_PS' if s['last_wr_bg']==bg else 'WTRS_PS'])
        if d['we'] and s['last_rd']>=0:col=max(col,s['last_rd']+t['RTW_PS'])
        s['col']=col;s['colbg'][bg]=col
        if d['we']:
            s['last_wr']=col;s['last_wr_bg']=bg;s['preok'][bk]=max(s['preok'][bk],col+t['CWL_PS']+t['BURST_PS']+t['WR_PS'])
        else:s['last_rd']=col;s['preok'][bk]=max(s['preok'][bk],col+t['RTP_PS'])
        return col
    def edge(self,c,request,selected):
        t=self.t;now=c*t['CLK_PS'];self.write_offer=None
        if selected is not None:self.s[selected]['r'].pop(0)
        for p,s in enumerate(self.s):
            if self.offers[p] and selected!=p:s['held']+=1
        if request:
            a=request['address'];assert BASE<=a<BASE+2176
            s=self.s[pc(a)];assert self.qfree[pc(a)]>=1
            s['q'].append(dict(request,arr=now));s['qmax']=max(s['qmax'],len(s['q']))
        for p,s in enumerate(self.s):
            for _ in range(4):
                if not s['q'] or len(s['r'])>=t['RQD']:continue
                if s['head'] is None:
                    sel=0;best=self.estimate(s,s['q'][0],now)
                    if s['skip']<t['MAXSKIP']:
                        for i in range(1,min(t['RW'],len(s['q']))):
                            # Actual write/read alias restriction inside FR-FCFS.
                            if any(x['address']==s['q'][i]['address'] and (x['we'] or s['q'][i]['we']) for x in s['q'][:i]):continue
                            est=self.estimate(s,s['q'][i],now)
                            if est<best:best=est;sel=i
                    if sel:s['q'].insert(0,s['q'].pop(sel));s['skip']+=1;s['bypasses']+=1
                    else:s['skip']=0
                    s['head']=self.schedule(s,s['q'][0],now)
                if s['head']<=now:
                    d=s['q'].pop(0);col=s['head'];s['head']=None
                    self.events.append(dict(kind='column',cycle=c,pc=p,tcol_ps=col,**{k:d[k] for k in ('address','tag','we')}))
                    if d['we']:
                        s['writes']+=1;self.write_offer=d
                        due=col+t['CWL_PS']+t['BURST_PS']
                        self.visibility[d['address']]=due
                        self.write_times.setdefault(d['address'],[]).append(col)
                        self.events.append(dict(kind='write_visible',ps=due,address=d['address'],tag=d['tag'],strobe=d['strobe']))
                    else:
                        if d['address'] in self.visibility:assert col>=self.visibility[d['address']]
                        due=col+t['CL_PS']+t['BURST_PS']+t['RSP_PS']
                        s['r'].append(dict(d,due=due));s['reads']+=1;s['rmax']=max(s['rmax'],len(s['r']))
            self.offers[p]=bool(s['r'] and s['r'][0]['due']<=(c+1)*t['CLK_PS'])
            self.qfree[p]=t['QD']-len(s['q'])


def replay(t,rows=128,retain=0):
    b=WriteBackend(t);ev=[];write_state='IDLE';block=0;producer_idx=0;producer_full=False;producer_draining=False
    row_valid=False;ack_seen=None;last_write_ack=None;writer_start=300
    source='IDLE';sch='IDLE';row=0;epoch=0;issued=received=nxt=pending=0
    op=-1;op_done=[];starts=[];stages=[];refills=[];op_last=[];life_done=[]
    desc_due=None;pf_due=None;issue_due=None;last_response=None;staged_due=None;done_due=None
    own_slot=127;first=128-rows;columns=[];retain_pending=None
    for c in range(200001):
        req=None;sel=next((p for p,v in enumerate(b.offers) if v),None);reply=b.s[sel]['r'][0] if sel is not None else None
        ack=b.write_offer
        if c==writer_start+15:producer_full=True
        if c==writer_start+17:
            assert producer_full;producer_draining=True
        if write_state=='IDLE' and producer_draining:
            block=producer_idx;producer_idx+=1
            ev.append(dict(kind='block',cycle=c,block=block))
            if producer_idx==16:producer_draining=False
            write_state='WC'
        elif write_state in ('WC','WS'):
            sec=block if write_state=='WC' else 16;addr=BASE+own_slot*17+sec
            req=dict(address=addr,tag=65536|sec,we=True,strobe=4294967295 if sec<16 else 1<<block)
            assert b.qfree[pc(addr)]>0
            write_state+='DONE'
        elif write_state in ('WCDONE','WSDONE') and ack:
            ev.append(dict(kind='write_ack',cycle=c,address=ack['address'],tag=ack['tag']))
            if write_state=='WCDONE':write_state='WS'
            else:
                write_state='IDLE'
                if block==15:
                    row_valid=True;last_write_ack=c;desc_due=c+1
                    ev.append(dict(kind='logical_publish',cycle=c))
        # Model fixture descriptor after logical publish, not artificial visibility waiting.
        if c==desc_due:
            op+=1;starts.append(c);row=first
            desc_due=None
            ev.append(dict(kind='descriptor',cycle=c,op=op,generation=op+1,user=0,rows=rows))
            if retain:
                # Actual retention adds capture + registered response dispatch edge.
                if op==1:
                    stages.append(c+2);refills.append(0);op_last.append(None)
                    issue_due=c+3;done_due=c+4*((rows+3)//4)+5
                    life_done.append(done_due);sch='RUN'
                else:pf_due=c+2;sch='SEND'
            else:pf_due=c+1;sch='SEND'
        old_source=source
        if source=='PIPE' and pending<8 and (nxt<16 or (nxt==16 and received&65535==65535)):
            addr=BASE+row*17+nxt
            if b.qfree[pc(addr)]>0:
                req=dict(address=addr,tag=65536|(epoch<<5)|nxt,we=False,strobe=0,row=row,sector=nxt,epoch=epoch,op=op)
        if c==pf_due:
            assert source=='IDLE' and write_state=='IDLE' and row_valid and pending==0
            epoch=(epoch+1)&511;issued=received=pending=nxt=0;source='PIPE';pf_due=None
        elif req and not req['we']:issued|=1<<nxt;nxt+=1;pending+=1
        if reply:
            assert old_source=='PIPE' and reply['row']==row and reply['epoch']==epoch
            sec=reply['sector'];assert issued>>sec&1 and not(received>>sec&1)
            received|=1<<sec;pending-=1
            ev.append(dict(kind='reply',cycle=c,pc=sel,**{k:reply[k] for k in ('address','tag','op')}))
            if sec==16:
                assert pending==0 and received==131071;source='IDLE';last_response=c
                if row==127:
                    op_last.append(c);stages.append(c+2);refills.append(c-starts[op]+1-retain)
                    issue_due=c+3;done_due=c+4*((rows+3)//4)+5
                    life_done.append(done_due);sch='RUN'
                else:row+=1;pf_due=c+2
        if req:
            ev.append(dict(kind='request',cycle=c,pc=pc(req['address']),**req))
        b.edge(c,req,sel)
        if op>=0:assert sum(len(s['q'])+len(s['r']) for s in b.s)==pending
        if c==done_due:
            # Merge done -> lifecycle/source drain -> sampled done. Retention arms at this edge.
            ev.append(dict(kind='lifecycle_done',cycle=c,op=op,generation=op+1))
            op_done.append(c);sch='IDLE';done_due=None
            if op==0:desc_due=c+1
            else:break
    assert len(op_done)==2 and producer_idx==16 and sum(s['writes'] for s in b.s)==32
    # Column events are from backend scheduling, never a measured RTL transcript.
    own_reads=[e for e in b.events if e['kind']=='column' and not e['we'] and (e['address']-BASE)//17==127]
    visibility=b.visibility[BASE+127*17+16]
    own_columns={str(sec):next(e for e in own_reads if e['address']==BASE+127*17+sec) for sec in (0,15,16)}
    summary=dict(rows=rows,retain=retain,write_requests=32,last_write_ack=last_write_ack,
        last_WRcolumn_ps=b.write_times[BASE+127*17+16][-1],final_scale_visible_ps=visibility,
        starts=starts,staged_samples=stages,lifecycle_done_samples=op_done,refill_counters=refills,final_epoch=epoch,
        first_own_row_READcolumns=own_columns,
        read_visibility_margin_ps={k:e['tcol_ps']-b.visibility[e['address']] for k,e in own_columns.items()},
        first_code_READ_after_final_scale_visibility_ps=own_columns['0']['tcol_ps']-visibility,
        per_PC=[dict(pc=p,reads=s['reads'],writes=s['writes'],refreshes=s['refs'],activations=s['acts'],q=len(s['q']),r=len(s['r'])) for p,s in enumerate(b.s)])
    return summary,ev+b.events


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);a=ap.parse_args()
    raw=subprocess.check_output(['git','show',PIN+':'+IDX],cwd=ROOT);assert raw==(ROOT/IDX).read_bytes()
    names=['QD','RQD','RW','MAXSKIP','CLK_PS','BURST_PS','TCCDL_PS','CL_PS','CWL_PS','RCDRD_PS','RCDWR_PS','RP_PS','RAS_PS','RTP_PS','RRDS_PS','RRDL_PS','FAW_PS','REQ_PS','RSP_PS','REFI_PS','RFCPB_PS','WR_PS','WTRS_PS','WTRL_PS','RTW_PS']
    t={n:int(re.search(r'parameter (?:integer|longint)\s+'+n+r'\s*=\s*(\d+)',raw.decode())[1]) for n in names}
    out=(ROOT/a.out).resolve();out.mkdir(parents=True,exist_ok=False);cases={};hashes={}
    for name,rows,ret in [('L0_no_retain',128,0),('L0_retain',128,1),('source_COUNT1_boundary',1,0)]:
        cases[name],events=replay(t,rows,ret)
        file=out/(name+'_events.jsonl');file.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in events));hashes[name]=sha(file.read_bytes())
    prior=json.loads((ROOT/'results/uarch/w17_window_epoch9_producer_lifecycle_20261001/model.json').read_bytes())
    timing=json.loads((ROOT/'results/uarch/w17_window_epoch9_timing_prediction_20261001_attempt1/prediction.json').read_bytes())
    pins=dict(prior['source_sha256'],**timing['source_sha256'])
    assert all(sha((ROOT/p).read_bytes())==h and sha(subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT))==h for p,h in pins.items())
    candidate={p:sha((ROOT/p).read_bytes()) for p in ('rtl/test/w17_window_epoch9_candidate/ot_chip_v41x_window_kv_prefetch.sv','rtl/test/w17_window_epoch9_candidate/ot_chip_v41x_window_attn_source.sv')}
    assert all(h==timing['candidate_added_sha256'][p] for p,h in candidate.items())
    r=dict(schema='opentallas.window_epoch9.producer_prediction.v1',source_commit=PIN,idx_sha256=sha(raw),generator_sha256=sha(Path(__file__).read_bytes()),source_sha256=pins,candidate_sha256=candidate,
        dependency_sha256={'tools/w17_window_epoch9_timing_model.py':sha((ROOT/'tools/w17_window_epoch9_timing_model.py').read_bytes())},
        prepared_fixture_sha256={p:sha((ROOT/p).read_bytes()) for p in ('rtl/test/w17_window_epoch9_producer/tb.sv','rtl/test/w17_window_epoch9_producer/transport_body.svh')},params=t,cases=cases,event_sha256=hashes,
        verdict='MODELED_PREPARED_NOT_BUILT_PENDING_PARENT_GO',
        visibility_contract=dict(lag_ps=7274,publication='row_valid proves logical ordered write acknowledgements only, not immediate physical visibility; existing consumers use it only to enter HBM refill. Packed/stage4 consumers need staged read replies; direct scalar banked reads fault.',
            earliest_prefetch_waiting_descriptor='Final WRissueI, observedackA=I+1; earliest prefetchA+1, requestA+2, READcolumn >=(A+2)*1000+REQ10000 >=last_WRcol+13000, even COUNT1.',
            minimum_first_code_margin_over_latest_scale_visibility_ps=13000-7274,
            credit8_lower_bounds_relative_last_WRcol_ps=dict(any_code=13000,last_code15=55000,scale=90000),
            lower_bound_derivation='Minimum request-to-reply34cycles from REQ10ns+CL12.5ns+BURST1.024ns+RSP10ns. Credit8 wave2 cannot start before reply0+1; code15 request>=firstgrant+42; scale waits all16 replies then oneedge. These are conservative source-derived lower bounds, not a constant fit or exact-case values.',
            per_PC_WTR_minimum_ps=dict(different_BG=11649,same_BG=13524),
            bank_dependence='Address map row127 lastcodePC15 bank10/BG2, scalePC15 bank11/BG3. WTRdifferentBG for code15 after scaleWR; sameBG for scaleREAD. Bank ACT/PRE/refresh/return congestion only postpone admission/column/reply.',
            guard_decision='No7cycle guard implemented: legal source->HBM->stage->QK/PV path already captures data after visibility. Preserve7cycle post-ack worst visibility envelope for any future immediate-visible consumer or fault/reset contract; Peirce owns recovery.',
            COUNT1='Not a legal actualL0 descriptor under L0_ONLY1 (requires128). Modeled only as stronger source-count boundary; source COUNT1 still has16code then scale barrier.'),
        stimulus_contract=dict(step_start=299,capture_edges=list(range(300,316)),producer_issue=316,
            captures='Synthetic nonpoison bytes at actual QE capture output interface, src55232+32*block; actual window_kv_blocks and window_block_guard, no QE arithmetic/payload qualification.',
            historical_rows='Prime127 historical absolute rows pos-127..pos-1; initialize their2176sector-prefix backing data; newrow slot127 starts sentinel and is written only through32actualsourcewrites.',
            descriptors='QK/PV actualresolvedfields, accept QK nextedge after logical publication without waiting7cycles; PV nextedge after lifecycle_done sample. Same user0,pos1048575, generation1then2 from actual lifecycle, no force.',
            engine='Finite engine stub becomesbusy on issue, holdsbusy through all32acceptedbeats, idle afterlastbeat. It qualifies lifecycle transport only, not engine arithmetic.',
            retention='Two modes0/1; QK completion arms only after lifecycle+source drained; PV gets newgen. No mutations between QK/PV, no across-token retention.',
            addresses='AW30, base262144,user0, MEM_WORDS264320; every admitted address explicitly bounded, no modulo alias relied on.'),
        no_RTL_run=True,no_original_live_edit=True,full_token_rate=None)
    (out/'prediction.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:{f:v[f] for f in ('last_write_ack','starts','staged_samples','lifecycle_done_samples','refill_counters','final_epoch','read_visibility_margin_ps')} for k,v in cases.items()},indent=2))
if __name__=='__main__':main()
