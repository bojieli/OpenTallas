#!/usr/bin/env python3
"""Four-stack source-addressed causal provider MODEL experiment, no RTL.
All consumer inputs in built-in scenario explicitly synthetic. Never claims
source callbacks or actual connected hardware. Existing r10 remains immutable.
"""
import argparse, contextlib, hashlib, importlib.util, json
from pathlib import Path
from fractions import Fraction as F
from qwen_hbm_interface_geometry_r11 import checked_local, qwen_geometry, TagOwners
from qwen_hbm_downstream_contract_r8 import fixture
from qwen_hbm_controller_calendar_r2 import BankCalendar, bankmap, audit_bank_events, edge
from qwen_hbm_controller_events_r1 import ROOT, source_timing

R10=ROOT/'tools/qwen_hbm_shoreline_remedy_r10.py'
spec=importlib.util.spec_from_file_location('native_r13_pinned_r10',R10)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.PHY=F(1000) # private loaded module; original imported r10 untouched
CORE=F(1000);FAST=F(2500,3);SERIAL=F(10000,9)

class NativeProvider(base.Provider):
    def __init__(self,rows):
        super().__init__(rows)
        self.channels=[]
        for s in range(4):
            self.channels.append(dict(cal=BankCalendar(source_timing(),CORE),pc_busy=[F(0)]*32,
              pending_commands=[[] for _ in range(32)],refresh_next=[F(source_timing()['REFI_PS'])+F(source_timing()['REFI_PS']*p,32) for p in range(32)]))
        self.selected=0;self.channel_backing={};self.route_edges=qwen_geometry()['new_oneway_route_FAST_edges']
        self.tags=[TagOwners() for _ in range(4)];self.read_tags={}
        self.bind(0)
    def bind(self,s):
        self.selected=s
        for k,v in self.channels[s].items():setattr(self,k,v)
    @contextlib.contextmanager
    def channel(self,s):
        old=self.selected;self.bind(s)
        try:yield
        finally:self.bind(old)
    def reserve(self,i,producer,transport):
        checked_local(self.rows[i]['sector'],1)
        ok=super().reserve(i,producer,transport)
        if ok:self.live[i]['stack']=self.rows[i]['stack']
        return ok
    def advance(self,now):
        now=F(now)
        if now<self.now:raise ValueError('causal time')
        self.now=now
        for s,c in enumerate(self.channels):
            for pc in range(32):c['pending_commands'][pc]=[x for x in c['pending_commands'][pc] if x>now]
            with self.channel(s):super().current_refresh()
        for i,x in self.live.items():
            if x['phase']=='WR_emitted' and now>=x['visible_due']:
                x['phase']='WR_visible'
                key=(x['stack'],x['sector']);self.channel_backing[key]=(i,x['producer'],x['transport'])
                self.record('backing_visible',i,stack=x['stack'],sector=x['sector'])
    def RMW_read(self,i,identity):
        s=self.rows[i]['stack'];a=identity[0]
        with self.channel(s):
            tag=self.tags[s].accept(a,1,i,identity[1],identity[2])
            if tag is None:return False
            due=super().RMW_read(i,identity)
            if due is False:
                # No command accepted; explicit rollback is allocation abort.
                self.tags[s].live[tag]['seen'].add(0);self.tags[s].reclaim(tag);return False
            self.live[i]['RMW_ready']+=12*CORE+3*FAST
            self.read_tags['RMW',i]=(s,tag)
            return self.live[i]['RMW_ready']
    def capture_owned_read(self,kind,i,identity):
        s,tag=self.read_tags[kind,i]
        x=self.live[i] if kind=='RMW' else self.readers[i]
        due=x['RMW_ready'] if kind=='RMW' else x['ready']
        if tuple(identity)!=(x['sector'],x['producer'],x['transport']) or self.now<due:
            raise ValueError('early or wrong accepted identity return')
        del self.read_tags[kind,i]
        a=identity[0];self.tags[s].capture(tag,bankmap(a)['pc'],0,'SYNTHETIC_METADATA_NO_PAYLOAD')
        self.tags[s].reclaim(tag)
        self.record('physical_owned_return_MODEL_INPUT',i,stack=s,sector=a)
    def RMW_result_commit(self,i,identity):
        x=self.owner(i,identity)
        if self.now<x['RMW_ready']:raise ValueError('early native PHY result')
        if ('RMW',i) in self.read_tags:raise ValueError('actual owned return capture required')
        return super().RMW_result_commit(i,identity)
    def WR_column(self,i,identity):
        with self.channel(self.rows[i]['stack']):return super().WR_column(i,identity)
    def RAW_read_ready(self,sector):
        return not any(x['stack']==self.selected and x['sector']==sector and x['phase'] in
          ['RMW_wait','RMW_result_wait','RMW_retire_wait','WR_ready','WR_emitted'] for x in self.live.values())
    def reader_accept(self,i,sector,producer,transport):
        checked_local(sector,1);s=self.read_rows[i]['stack']
        with self.channel(s):
            tag=self.tags[s].accept(sector,1,i,producer,transport)
            if tag is None:return False
            ok=super().reader_accept(i,sector,producer,transport)
            if not ok:
                self.tags[s].live[tag]['seen'].add(0);self.tags[s].reclaim(tag);return False
            self.readers[i]['stack']=s;self.readers[i]['ready']+=12*CORE+3*FAST
            self.read_tags['reader',i]=(s,tag);return True
    def reader_result(self,i,identity):
        if ('reader',i) in self.read_tags:raise ValueError('owned reader return capture required')
        return super().reader_result(i,identity)

def scenario():
    """Explicit synthetic endpoints; exact actual metadata, no source issuance guess.
    Serialized host-driven stimulus is conservative and gives no token-rate credit.
    """
    f=fixture();rows=f['sector_rows'];p=NativeProvider(rows);assert p.reserve(0,7,8);p.opcode_issue(10,0,1,7,8)
    for i,r in enumerate(rows):
        if i:assert p.reserve(i,7,8)
        owner=(r['sector'],7,8)
        if r['partial']:
            due=p.RMW_read(i,owner);assert due is not False;p.advance(due)
            p.capture_owned_read('RMW',i,owner);p.RMW_result_commit(i,owner);p.RMW_owned_retire(i,owner)
        due=p.WR_column(i,owner);assert due is not False
        with p.channel(r['stack']):assert not p.RAW_read_ready(r['sector'])
        p.advance(due);assert p.channel_backing[r['stack'],r['sector']]==(i,7,8)
        p.ACK_capture(i,owner);p.advance(p.live[i]['ACK_landing']);p.sector_store(i,owner)
        p.advance(p.live[i]['store_due']+SERIAL);p.sector_retire(i,owner)
        p.advance(p.live[i]['reverse_due']);p.reverse_credit(i,owner)
    p.advance(edge(p.now,SERIAL));p.opcode_complete(10,0,1);p.advance(p.now+SERIAL);p.IRS_retire(10,0,1)
    p.opcode_issue(11,1,2,7,8);p.opcode_complete(11,1,2);p.advance(p.now+SERIAL);p.IRS_retire(11,1,2)
    p.acquire(7,8,dict(position=0,producer=7,transport=8,sector_retire_quorum=272,scope='SYNTHETIC_EXPLICIT_INPUT'))
    p.opcode_issue(12,2,3,7,8)
    for i,r in enumerate(f['KV_prefix_read_rows']):
        owner=(r['sector'],7,8);assert p.reader_accept(i,*owner)
        p.advance(p.readers[i]['ready']);p.capture_owned_read('reader',i,owner);p.reader_result(i,owner);p.reader_retire(i,owner)
        p.advance(p.readers[i]['reverse_due']);p.reader_reverse_credit(i,owner)
    p.advance(edge(p.now,SERIAL));p.opcode_complete(12,2,3);p.advance(p.now+SERIAL);p.IRS_retire(12,2,3)
    for instruction in (13,14,15):
        p.opcode_issue(instruction,instruction-10,instruction,7,8);p.opcode_result_commit(instruction,7,8)
        p.opcode_complete(instruction,instruction-10,instruction);p.advance(p.now+SERIAL);p.IRS_retire(instruction,instruction-10,instruction)
    p.release(7,8);p.writer_context_release()
    events=[]
    for s,c in enumerate(p.channels):
        audit_bank_events(c['cal'].events,source_timing())
        for e in c['cal'].events:events.append(dict(stack=s,**{k:str(v) if isinstance(v,F) else v for k,v in e.items()}))
    assert len(p.completed)==272 and len(p.reader_done)==288 and not p.read_tags
    return dict(scope='SYNTHETIC_EXPLICIT_ENDPOINT_MODEL_ONLY_ACTUAL_ADDRESSES_NO_PAYLOAD',
      source_R10_sha256=hashlib.sha256(R10.read_bytes()).hexdigest(),physical_provider_runtime_ready=False,
      writer_sector_completions=len(p.completed),reader_completions=len(p.reader_done),RMW_reads=256,
      stacks=4,PCs_per_stack=32,PHY_core_ps=1000,controller_FAST_ps=str(FAST),
      serialized_stimulus_end_ps=str(p.now),per_user_latency_credit=False,mixed_weight_service_credit=False,
      journal=p.log,bank_events=events,peak=dict(p.peak),source_completion_events=0,
      actual_runtime_blockers=['No actual source addressed sector-store retirement or RMW owned result-retirement endpoint.',
        'No actual held WRvisible and reader lease acquisition/release endpoints.',
        'Actual mixed weight accepted phase/order/time provider absent; no weight issue guessed from ranges.',
        'Native LEN6/BEAT5 PHY and1GHz CDC implementation/SSFF admission absent.'],
      experiment_resources=dict(threads=1,memory_GiB=2,swap_GiB=0,wall_seconds=120,fullprogram=False,RTL=False))

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    x=scenario();args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(x,f,sort_keys=True,indent=2);f.write('\n')
