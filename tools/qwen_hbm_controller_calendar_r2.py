#!/usr/bin/env python3
"""Address-bound, payload-free Qwen loaded-column prerequisite.

A conservative causal event calendar, not the original zero-time SV scheduler.
Only the recorded metadata is actual. All runnable release/ready/CDC phases
are explicitly fixture inputs. No checkpoint payload or full-program simulation.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from qwen_hbm_controller_events_r1 import (Beat, Controller, BASE, REV, SOURCE, DIR,
    ROOT, pinned, source_timing)

R1 = '7bc0a87578d8a65f64e390acd1bfbfb588d0b9d1'
PROGRAM = 'results/physical_abi3/asap7/gpu/w13_calendar_bounded_review_20261001/qwen_reproduced_program.json'

def edge(time, period):
    time, period = Fraction(time), Fraction(period)
    if period <= 0:
        raise ValueError('positive explicit period')
    return -(-time//period)*period

def crossed(time, period):
    # Same three-destination-edge candidate convention as pinned common calendar.
    return (Fraction(time)//period+3)*period

def bankmap(addr):
    if not 0 <= addr < 1 << 34:
        raise ValueError('full AW34 sector')
    row = addr >> 15
    bank = ((((addr >> 12) ^ (row >> 2)) & 7) << 2) | ((addr ^ row) & 3)
    return dict(pc=Controller.pc(addr),bank=bank,bg=bank & 3,row=row)

@dataclass
class Bank:
    open: bool = False
    row: int = 0
    act: Fraction = Fraction(0)
    actok: Fraction = Fraction(0)
    preok: Fraction = Fraction(0)

class BankCalendar:
    """32 explicit PC replicas, 32 banks each; source timing constants.

    plan commits future ACT/PRE/REF/column reservations, one scheduled head/PC.
    The source's estimate intentionally omits turnarounds/refresh; it is used
    for FRFCFS selection only. Causal plan includes them at final scheduling.
    Caller must reserve finite WR/return capacity BEFORE plan or head pop.
    """
    def __init__(self, timing, period):
        self.t = timing
        self.period = Fraction(period)
        edge(0,self.period)
        self.b = [[Bank() for _ in range(32)] for _ in range(32)]
        self.last_act = [Fraction(-1000000)]*32
        self.last_act_bg = [[Fraction(-1000000)]*4 for _ in range(32)]
        self.faw = [[Fraction(-1000000)]*4 for _ in range(32)]
        self.last_col = [Fraction(-1000000)]*32
        self.last_col_bg = [[Fraction(-1000000)]*4 for _ in range(32)]
        self.last_rd = [None]*32
        self.last_wr = [None]*32
        self.last_wr_bg = [None]*32
        self.last_ref = [None]*32
        self.next_ref = [Fraction(timing['REFI_PS'])+Fraction(timing['REFI_PS']*p,32) for p in range(32)]
        self.events = []

    def estimate(self, request, now):
        m=bankmap(request.addr);p=m['pc'];bg=m['bg'];b=self.b[p][m['bank']];t=self.t
        arrival=request.accepted_ps+t['REQ_PS']
        if b.open and b.row == m['row']:
            act=b.act
        else:
            act=max(arrival,b.preok)+t['RP_PS'] if b.open else arrival
            act=max(act,b.actok,self.last_act[p]+t['RRDS_PS'],
                    self.last_act_bg[p][bg]+t['RRDL_PS'],self.faw[p][0]+t['FAW_PS'])
        return max(arrival,now,act+t['RCDWR_PS' if request.write else 'RCDRD_PS'],
                   self.last_col[p]+t['BURST_PS'],self.last_col_bg[p][bg]+t['TCCDL_PS'])

    def log(self, kind, time, p, bank=None, request=None):
        self.events.append(dict(kind=kind,ps=Fraction(time),pc=p,bank=bank,
                                sector=request.addr if request else None,tag=request.tag if request else None,
                                producer_epoch=request.producer_epoch if request else None,
                                transport_epoch=request.transport_epoch if request else None))

    def plan(self, request, now, causal=True):
        m=bankmap(request.addr);p=m['pc'];bg=m['bg'];b=self.b[p][m['bank']];t=self.t
        arrival=Fraction(request.accepted_ps)+t['REQ_PS']
        # Source literal does NOT include now here. Causal policy does.
        horizon=max(arrival,self.last_col[p],now if causal else arrival)
        while self.next_ref[p] <= horizon:
            refresh=max(self.next_ref[p],now if causal else self.next_ref[p],self.last_col[p]+t['BURST_PS'])
            if causal and self.last_ref[p] is not None:refresh=max(refresh,self.last_ref[p]+t['RFC_PS'])
            open_banks=[x for x in self.b[p] if x.open]
            if open_banks:
                pre=edge(max([refresh]+[x.preok for x in open_banks]),self.period)
                self.log('PREall',pre,p)
                refresh=pre+t['RP_PS']
            refresh=edge(refresh,self.period)
            self.log('REF',refresh,p)
            self.last_ref[p]=refresh
            for x in self.b[p]:
                x.open=False;x.actok=max(x.actok,refresh+t['RFC_PS'])
            self.next_ref[p]+=t['REFI_PS']
        if b.open and b.row == m['row']:
            act=b.act
        else:
            earliest=max(arrival,now) if causal else arrival
            if b.open:
                pre=edge(max(earliest,b.preok),self.period)
                self.log('PRE',pre,p,m['bank'])
                earliest=pre+t['RP_PS']
            act=edge(max(earliest,b.actok,self.last_act[p]+t['RRDS_PS'],
                self.last_act_bg[p][bg]+t['RRDL_PS'],self.faw[p][0]+t['FAW_PS']),self.period)
            self.log('ACT',act,p,m['bank'],request)
            self.faw[p]=self.faw[p][1:]+[act]
            self.last_act[p]=act;self.last_act_bg[p][bg]=act
            b.open=True;b.row=m['row'];b.act=act
            b.actok=act+t['RAS_PS']+t['RP_PS'];b.preok=act+t['RAS_PS']
        column=max(arrival,now,act+t['RCDWR_PS' if request.write else 'RCDRD_PS'],
                   self.last_col[p]+t['BURST_PS'],self.last_col_bg[p][bg]+t['TCCDL_PS'])
        if not request.write and self.last_wr[p] is not None:
            column=max(column,self.last_wr[p]+t['CWL_PS']+t['BURST_PS']+
                       t['WTRL_PS' if self.last_wr_bg[p] == bg else 'WTRS_PS'])
        if request.write and self.last_rd[p] is not None:
            column=max(column,self.last_rd[p]+t['RTW_PS'])
        column=edge(column,self.period)
        self.last_col[p]=column;self.last_col_bg[p][bg]=column
        if request.write:
            self.last_wr[p]=column;self.last_wr_bg[p]=bg
            b.preok=max(b.preok,column+t['CWL_PS']+t['BURST_PS']+t['WR_PS'])
        else:
            self.last_rd[p]=column;b.preok=max(b.preok,column+t['RTP_PS'])
        self.log('WR' if request.write else 'RD',column,p,m['bank'],request)
        return column


def audit_bank_events(events, timing):
    """Independent inequalities over emitted commands; no payload access."""
    banks=[[dict(open=False,row=0,act=Fraction(0),preok=Fraction(0),actok=Fraction(0)) for _ in range(32)] for _ in range(32)]
    act=[[] for _ in range(32)];act_bg=[{} for _ in range(32)]
    col=[None]*32;col_bg=[{} for _ in range(32)];rd=[None]*32;wr=[None]*32;ref=[None]*32
    preall=[None]*32;t=timing
    for e in sorted(events,key=lambda e:e['ps']):
        now=Fraction(e['ps']);p=e['pc'];k=e['kind'];bk=e['bank']
        if k in ('PRE','PREall'):
            targets=range(32) if k=='PREall' else [bk]
            for index in targets:
                b=banks[p][index]
                if b['open']:assert now>=b['preok'], 'PRE recovery/tRAS violation'
                b['open']=False;b['actok']=max(b['actok'],now+t['RP_PS'])
            if k=='PREall':preall[p]=now
        elif k=='REF':
            assert not any(b['open'] for b in banks[p]), 'refresh with open bank'
            if preall[p] is not None:assert now>=preall[p]+t['RP_PS']
            if col[p] is not None:assert now>=col[p]+t['BURST_PS']
            if ref[p] is not None:assert now>=ref[p]+t['RFC_PS'], 'overlapping refresh'
            ref[p]=now
            for b in banks[p]:b['actok']=max(b['actok'],now+t['RFC_PS'])
        elif k=='ACT':
            m=bankmap(e['sector']);bg=m['bg'];b=banks[p][bk]
            assert m['pc']==p and m['bank']==bk
            assert not b['open'] and now>=b['actok'], 'ACT PRE/tRC/refresh block'
            if act[p]:assert now>=act[p][-1]+t['RRDS_PS']
            if bg in act_bg[p]:assert now>=act_bg[p][bg]+t['RRDL_PS']
            if len(act[p])>=4:assert now>=act[p][-4]+t['FAW_PS']
            act[p].append(now);act_bg[p][bg]=now
            b.update(open=True,row=m['row'],act=now,preok=now+t['RAS_PS'],actok=now+t['RAS_PS']+t['RP_PS'])
        elif k in ('RD','WR'):
            m=bankmap(e['sector']);bg=m['bg'];b=banks[p][bk]
            assert b['open'] and b['row']==m['row'], 'column row identity'
            assert now>=b['act']+t['RCDWR_PS' if k=='WR' else 'RCDRD_PS']
            if col[p] is not None:assert now>=col[p]+t['BURST_PS']
            if bg in col_bg[p]:assert now>=col_bg[p][bg]+t['TCCDL_PS']
            if k=='WR':
                if rd[p] is not None:assert now>=rd[p]+t['RTW_PS']
                wr[p]=(now,bg);b['preok']=max(b['preok'],now+t['CWL_PS']+t['BURST_PS']+t['WR_PS'])
            else:
                if wr[p] is not None:assert now>=wr[p][0]+t['CWL_PS']+t['BURST_PS']+t['WTRL_PS' if wr[p][1]==bg else 'WTRS_PS']
                rd[p]=now;b['preok']=max(b['preok'],now+t['RTP_PS'])
            col[p]=now;col_bg[p][bg]=now
        else:raise ValueError('unknown bank event')
    return dict(status='PASS_COMMAND_TIMING_INEQUALITIES',events=len(events),PCs=32,banks_per_PC=32)


def kv_rows(graph, writer, position):
    if writer['opcode'] != 'KV_WRITE' or not 0 <= position < graph['context_capacity']:
        raise ValueError('writer/position')
    c=graph['config'];a=writer['attributes'];hd=c['head_dim'];context=graph['context_capacity']
    ext={e['name']:e for r in graph['memory_allocation'] if r['die'] == a['die'] for e in r['extents']}
    rows=[]
    for kind in ('K','V'):
        masks={}
        for head in range(c['num_key_value_heads']//graph['TP']):
            for dim in range(hd):
                offset=(((head*(context//16)+position//16)*hd+dim)*16+position%16
                        if kind == 'K' else (head*context+position)*hd+dim)
                addr=ext[f"L{a['layer']}.{kind}"]['base']+offset
                local=addr//128//4*128+addr%128
                key=(addr//128%4,local//32)
                masks[key]=masks.get(key,0)|(1 << (local%32))
        for (stack,sector),mask in sorted(masks.items()):
            rows.append(dict(kind=kind,stack=stack,sector=sector,mask=mask,partial=mask!=0xffffffff,ordinal=len(rows)))
    return rows

def kv_read_rows(graph, writer, position):
    # All prefix bytes, then coalesce unique sectors. Exact footprint only.
    masks={}
    for pos in range(position+1):
        for r in kv_rows(graph,writer,pos):
            key=(r['kind'],r['stack'],r['sector'])
            masks[key]=masks.get(key,0)|r['mask']
    return [dict(kind=k,stack=s,sector=a,mask=m,**bankmap(a)) for (k,s,a),m in sorted(masks.items())]

def weight_ranges(graph):
    ext={(r['die'],e['name']):e for r in graph['memory_allocation'] for e in r['extents']}
    result=[]
    for op in graph['instructions']:
        if op['opcode'] != 'MATRIX':continue
        d=graph['weight_descriptors'][op['attributes']['weight']]
        name=f"L{d['layer']}.{d['name']}" if d['layer'] is not None else 'head'
        pieces=[]
        for suffix in ('codes','scales'):
            e=ext[d['die'],name+'.'+suffix]
            first=e['base']//128;last=(e['base']+e['bytes']-1)//128
            stacks=[]
            for s in range(4):
                begin=first+(s-first)%4;end=last-(last-s)%4
                stacks.append(dict(stack=s,first_local_sector=begin//4*4 if begin<=end else None,
                    line_count=(end-begin)//4+1 if begin<=end else 0,local_sector_stride=4,sectors_per_line=4))
            pieces.append(dict(extent=name+'.'+suffix,global_base_bytes=e['base'],logical_bytes=e['bytes'],stacks=stacks))
        result.append(dict(instruction=op['id'],die=d['die'],weight=d['key'],dependencies=op['dependencies'],ranges=pieces,
                           phase_provider='MISSING accepted request address/length/order/time/client/tag/epochs/cache outcome; ranges do not imply requests'))
    return result

class SharedDie:
    """Fixture: four sector credits and ACK records, one store/RMW port.

    Shared across all four stack calendars; explicitly bounded source service.
    Periods and CDC/consumer phase choices are inputs, not measured hardware.
    """
    def __init__(self):
        self.credits=set()
        self.consumer=[]
        self.store_available=Fraction(0)
        self.rmw_available=Fraction(0)
        self.last_capture=None
        self.credit_peak=0
        self.capture_peak=0

    def advance(self, now):
        for item in list(self.consumer):
            if item['release']<=now:
                owner=item['owner'];tag=item['tag']
                owner.finished.add(tag);owner.emit('reverse_credit',tag,item['release'])
                self.credits.remove(owner.info[tag]['group'])
                self.consumer.remove(item)


class LoadedStack:
    """Finite queue calendar with explicit phases; payload always zero.

    Each PC has its charged scan replica, bank state, and one scheduled head.
    One shared stack ingress and one return/ACK selection per controller edge.
    Four WR holds survive through ready acceptance; no ideal PC output fanout.
    """
    def __init__(self, timing, period, serial_period, shared=None, stack=0):
        self.shared=SharedDie() if shared is None else shared
        self.stack=stack
        self.c=Controller(timing)
        self.bank=BankCalendar(timing,period)
        self.tc=Fraction(period);self.ts=Fraction(serial_period)
        edge(0,self.ts)
        self.phase=[None]*32
        self.scan_done=[None]*32
        self.column_due=[None]*32
        self.reserved_WR={}
        self.reserved_RD={}
        self.prefetch=[Fraction(0)]*32
        self.tasks=[];self.info={};self.finished=set();self.log=[];self.event_cursor=0
        self.now=Fraction(0);self.next_id=0
        self.slot_peak=0;self.queue_peak=0;self.return_peak=0
        self.read_prefetch_waits=0;self.admission_freeze_stalls=0

    def add(self, addr, kind, ready_ps=0, predecessor=None):
        identity=self.next_id;self.next_id+=1
        b=Beat(addr,identity,2**48+1,1,write=kind=='write',data=0)
        self.tasks.append((b,kind,Fraction(ready_ps),predecessor))
        self.info[identity]=dict(kind=kind,sector=addr,pc=Controller.pc(addr),dependency=predecessor,group=(self.stack,addr) if kind in ('write','RMW_read') else None)
        return identity

    def emit(self,event,tag,now):
        identity=self.info[tag]
        self.log.append(dict(event=event,tag=tag,sector=identity['sector'],pc=identity['pc'],kind=identity['kind'],dependency=identity['dependency'],
                             producer_epoch=2**48+1,transport_epoch=1,ps=Fraction(now)))

    def step(self,now):
        self.now=now;self.c.advance(now)
        self.shared.advance(now)
        # One shared-die finite capture port, four records, one serial store.
        ack=self.c.write_offer(now)
        if ack is not None and len(self.shared.consumer)<4 and self.shared.last_capture!=now:
            tag=ack.request.tag;self.c.write_take(now,True)
            self.shared.last_capture=now
            delivered=crossed(now,self.ts)
            stored=edge(max(delivered,self.shared.store_available),self.ts)
            self.shared.store_available=stored+self.ts
            retired=stored+2*self.ts  # explicit synthetic store/result/retire chain
            release=crossed(retired,self.tc)
            self.shared.consumer.append(dict(tag=tag,release=release,owner=self))
            self.shared.capture_peak=max(self.shared.capture_peak,len(self.shared.consumer))
            for event,time in [('WR_visible_ACK_accept',now),('ACK_forward_CDC',delivered),('ACK_store',stored),('ACK_retire',retired)]:
                self.emit(event,tag,time)
        # Registered 1R1W head prefetch and shared RR arbiter (one return).
        for offset in range(32):
            p=(self.c.rr+offset)%32
            if self.c.r[p] and self.c.r[p][0].due_ps<=now:
                if self.prefetch[p]>now:
                    self.read_prefetch_waits+=1;continue
                kind=self.info[self.c.r[p][0].request.tag]['kind']
                if kind=='RMW_read' and self.shared.rmw_available>now:continue
                result=self.c.r[p].pop(0);self.c.rr=(p+1)%32
                self.prefetch[p]=now+2*self.tc
                tag=result.request.tag;self.emit('RD_accept',tag,now)
                kind=self.info[tag]['kind']
                done=crossed(now,self.ts)+(28*self.ts if kind=='RMW_read' else self.ts)
                if kind=='RMW_read':self.shared.rmw_available=done
                self.emit('RMW_merge_visible' if kind=='RMW_read' else 'read_result_visible',tag,done)
                self.info[tag]['done_ps']=done
                # merge returned to controller domain, not same-edge WR ingress
                self.info[tag]['release_ps']=crossed(done,self.tc)
                break
        # Existing selected heads: finite reservation precedes bank plan and pop.
        for p in range(32):
            if self.phase[p]=='scan' and self.scan_done[p]<=now:
                self.phase[p]='reserve'
            if self.phase[p]=='reserve':
                b=self.c.q[p][0]
                if any(x.request.addr==b.addr and not x.visible for x in self.c.pending):continue
                if b.write:
                    if len(self.c.pending)+len(self.reserved_WR)>=4:continue
                    self.reserved_WR[p]=b;self.emit('WR_capacity_reserved',b.tag,now)
                else:
                    if len(self.c.r[p])+int(p in self.reserved_RD)>=32:continue
                    self.reserved_RD[p]=b;self.emit('RD_capacity_reserved',b.tag,now)
                self.column_due[p]=self.bank.plan(b,now,causal=True)
                self.phase[p]='column'
            if self.phase[p]=='column' and self.column_due[p]<=now:
                b=self.c.q[p][0]
                assert self.c.column(p,now), 'capacity reservation lost'
                self.reserved_WR.pop(p,None);self.reserved_RD.pop(p,None)
                self.emit('WR_column' if b.write else 'RD_column',b.tag,now)
                if not b.write:
                    self.emit('RD_due',b.tag,now+self.c.timing['CL_PS']+self.c.timing['BURST_PS']+self.c.timing['RSP_PS'])
                    if len(self.c.r[p])==1:self.prefetch[p]=now+2*self.tc
                self.phase[p]=None
        # One shared stack ingress; dependency and frozen PC admission gates.
        for index,(b,kind,ready,predecessor) in enumerate(self.tasks):
            if ready>now:continue
            if predecessor is not None:
                done=self.info[predecessor].get('release_ps')
                if done is None or done>now:continue
            p=Controller.pc(b.addr)
            if self.phase[p] is not None:
                self.admission_freeze_stalls+=1;continue
            group=self.info[b.tag]['group']
            if group is not None and group not in self.shared.credits and len(self.shared.credits)>=4:continue
            if self.c.accept(b,now):
                if group is not None:
                    self.shared.credits.add(group)
                    self.shared.credit_peak=max(self.shared.credit_peak,len(self.shared.credits))
                self.emit('accept',b.tag,now);self.tasks.pop(index);break
        # Every PC has an explicitly charged sequential scan. No zero-time issue.
        for p in range(32):
            if self.phase[p] is None and self.c.q[p]:
                window=min(16,len(self.c.q[p]))
                estimates=[self.bank.estimate(b,now) for b in self.c.q[p][:window]]
                selected=self.c.reorder(p,estimates)
                # r1 RW16 budget held conservatively even for shorter snapshots.
                count=18 if selected==0 else 20+selected
                self.scan_done[p]=now+count*self.tc
                self.phase[p]='scan';self.emit('scan_start',self.c.q[p][0].tag,now)
        slots=len(self.c.pending)+len(self.reserved_WR)
        assert slots<=4
        self.slot_peak=max(self.slot_peak,slots)
        self.queue_peak=max(self.queue_peak,max(map(len,self.c.q)))
        self.return_peak=max(self.return_peak,max(map(len,self.c.r)))
        for kind,b,time in self.c.events[self.event_cursor:]:
            if kind=='WR_visible':self.emit('WR_backing_visible',b.tag,time)
        self.event_cursor=len(self.c.events)
        # Return/consumer done releases happen only at the explicitly given times.
        for tag,info in self.info.items():
            if 'release_ps' in info and info['release_ps']<=now:self.finished.add(tag)

    def run(self,limit_edges=50000):
        for tick in range(limit_edges):
            self.step(tick*self.tc)
            if not self.tasks and len(self.finished)==len(self.info) and not self.shared.consumer and self.c.drained() and not any(self.phase):
                return self.summary()
        raise ValueError('fixture finite horizon exceeded; no timeout-as-completion')

    def summary(self):
        return dict(done_ps=str(self.now),commands=len(self.info),kind_counts=dict(Counter(v['kind'] for v in self.info.values())),
            peak_pending_WR_slots=self.slot_peak,peak_PC_request_depth=self.queue_peak,peak_PC_return_depth=self.return_peak,
            freeze_stalls=self.admission_freeze_stalls,head_prefetch_waits=self.read_prefetch_waits,
            bank_event_counts=dict(Counter(e['kind'] for e in self.bank.events)),
            last_reverse_credit_ps=str(max((e['ps'] for e in self.log if e['event']=='reverse_credit'),default=0)),
            calendar_sha256=hashlib.sha256(json.dumps(self.log,default=str,sort_keys=True).encode()).hexdigest(),
            bank_calendar_sha256=hashlib.sha256(json.dumps(self.bank.events,default=str,sort_keys=True).encode()).hexdigest())


def fixture(graph,position=1,competing_weights=True,period=1000,serial_period=Fraction(10000,9)):
    writer=graph['instructions'][10]
    rows=kv_rows(graph,writer,position)
    reads=kv_read_rows(graph,writer,position)
    shared=SharedDie()
    stacks=[LoadedStack(source_timing(),period,serial_period,shared,s) for s in range(4)]
    for r in rows:
        s=stacks[r['stack']]
        old=s.add(r['sector'],'RMW_read') if r['partial'] else None
        s.add(r['sector'],'write',predecessor=old)
    # Address-exact footprint. Global publication waits all272 reverse
    # credits across the four stacks; prefetch drain is not a publication gate.
    if competing_weights:
        weight=next(w for w in weight_ranges(graph) if w['weight']=='L0.o.d0')
        for r in weight['ranges'][0]['stacks']:
            # First 16 sectors (4 lines) of a real next-matrix code extent.
            # Explicit hypothetical prefetch: opcode dependencies block actual
            # issue until after PV/NORMALIZE. This is NOT recorded traffic.
            for addr in range(r['first_local_sector'],r['first_local_sector']+16):
                stacks[r['stack']].add(addr,'weight_prefetch_fixture')
    def pump(start,writer_phase=False):
        for tick in range(start,start+50000):
            now=tick*Fraction(period)
            shared.advance(now)
            for offset in range(4):stacks[(tick+offset)%4].step(now)
            if writer_phase and all(all(tag in s.finished for tag,i in s.info.items() if i['kind']=='write') for s in stacks) and not shared.consumer and not shared.credits:
                return now
            if not writer_phase and all(not s.tasks and len(s.finished)==len(s.info) and s.c.drained() and not any(s.phase) for s in stacks) and not shared.consumer and not shared.credits:
                return now
        raise ValueError('finite fixture horizon exceeded')
    publication=pump(0,writer_phase=True)
    writer_summaries=[s.summary() for s in stacks]
    for r in reads:stacks[r['stack']].add(r['sector'],'KV_read',ready_ps=publication)
    pump(int(publication/Fraction(period))+1)
    ready=max(s.now for s in stacks)
    # Preserve actual read12 -> SCORES13 -> EXP_SUM14 -> PV15 dependencies.
    # Durations11/7/17 are declared test phases, never hardware measurements.
    scores=crossed(ready,serial_period)+11*serial_period
    exp=edge(scores,serial_period)+7*serial_period
    pv=edge(max(exp,crossed(ready,serial_period)),serial_period)+17*serial_period
    lease=max(scores,pv)
    return dict(scope='ACTUAL_METADATA_ADDRESSES_SYNTHETIC_RELEASE_READY_CDC_ATTENTION_PHASES',
        position=position,writer=10,fence=11,read=12,scores=13,pv=15,
        controller_period_ps=str(period),serial_period_ps=str(serial_period),
        NoC_phase_policy='Fixture zero forward/reverse NoC delay and deterministic ready; actual route/capture-ready/NoC provider is missing. DRAM timings are pinned, REQ/RSP assumed in source. No fixture rate is admitted.',
        phase_policy='all writer data ready0; shared four sector credits/RMW locks per die retained through reverse credit, shared four ACK records, one capture per controller edge, one serial store and one RMW serial service; CDC crossing uses explicit three destination edge candidate convention; no hardware credit',
        fixture_resources='32 explicitly charged scan/bank replicas per stack,4 retained WR slots/stack; shared four sector/RMW and four ACK/CDC records per die; one RMW read-import edge plus27 merge serial edges',
        shared_sector_credit_peak=shared.credit_peak,shared_ACK_record_peak=shared.capture_peak,
        weight_policy='16 sector prefetches/stack from actual L0.o.d0 code extent; hypothetical prefetch permission/order, absent from recorded trace' if competing_weights else 'no prefetch fixture traffic',
        writer_stacks=writer_summaries,loaded_stacks=[s.summary() for s in stacks],
        publication_max_reversecredit_ps=str(publication),KV_read_ready_max_ps=str(ready),
        synthetic_scores_done_ps=str(scores),synthetic_EXP_SUM_done_ps=str(exp),synthetic_PV_done_ps=str(pv),lease_release_max_ps=str(lease),
        lease_formula='SCORES=max(query_ready,KV_K_ready)+fixture11serial;EXP_SUM=SCORES_done+fixture7serial;PV=max(EXP_SUM_done,KV_V_ready)+fixture17serial;lease=max(SCORES_done,PV_done). Fixture sets queryready0 and conservative KV_K/Vready=all KV ready. No actual opcode cost is inferred.',
        calendar_legal=[audit_bank_events(s.bank.events,s.c.timing) for s in stacks],
        addressed_timeline=[dict(stack=s.stack,events=[dict(e,ps=str(e['ps'])) for e in sorted(s.log,key=lambda e:e['ps'])],bank_events=[dict(e,ps=str(e['ps'])) for e in sorted(s.bank.events,key=lambda e:e['ps'])]) for s in stacks],
        default_enabled=False,hardware_build_ready=False,rate_credit=0)


def compose(repo=ROOT):
    pins={}
    def get(rev,path):
        raw=pinned(repo,rev,path)
        pins[path]=dict(commit=subprocess.check_output(['git','rev-parse',rev],cwd=repo,text=True).strip(),sha256=hashlib.sha256(raw).hexdigest())
        return raw
    source=get(REV,SOURCE)
    get(R1,'tools/qwen_hbm_controller_events_r1.py')
    get(R1,'results/uarch/qwen_hbm_controller_events_20261001/model_r1.json')
    graph=json.loads(get(BASE,PROGRAM))
    trace=json.loads(gzip.decompress(get(BASE,DIR+'actual_two_token_terminal_r1/token1_execution.json.gz')))
    adapter=json.loads(get(BASE,DIR+'finite_service_adapter_r2.json'))
    get(BASE,DIR+'actual_two_token_terminal_r1/receipt.json')
    get(BASE,DIR+'actual_two_token_KV_state_r1.json')
    get(BASE,DIR+'finite_service_adapter_review_r2.json')
    get(BASE,DIR+'common36_drain_model_r2.json')
    get(BASE,'tools/common_wrack_completion_calendar.py')
    get(BASE,'tools/qwen_hbm_complete_service_provider.py')
    assert len(graph['instructions'])==len(trace['trace'])==1737
    assert [(o['id'],o['opcode'],o['dependencies']) for o in graph['instructions']]==[(o['id'],o['opcode'],o['dependencies']) for o in trace['trace']]
    for phrase in (b'while (next_ref[p] <= max2(tmin, last_col[p]))',b'tmin = arr + REQ_PS;',b'last_rd[p] + RTW_PS',b'last_wr[p] + CWL_PS + BURST_PS'):
        assert phrase in source
    writer_addresses=[]
    for demand in adapter['writer_demands']:
        rows=kv_rows(graph,graph['instructions'][demand['writer']],demand['position'])
        digest=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        assert digest==demand['sector_descriptor_sha256']
        reads=kv_read_rows(graph,graph['instructions'][demand['writer']],demand['position'])
        writer_addresses.append(dict(writer=demand['writer'],position=demand['position'],die=demand['die'],layer=demand['layer'],
            sectors=len(rows),partial_reads=sum(r['partial'] for r in rows),descriptor_sha256=digest,
            KV_read_unique_sectors=len(reads),KV_read_by_stack=[sum(r['stack']==s for r in reads) for s in range(4)],
            WR_by_PC_per_stack=[[sum(r['stack']==s and Controller.pc(r['sector'])==p for r in rows) for p in range(32)] for s in range(4)]))
    target_rows=kv_rows(graph,graph['instructions'][10],1)
    weights=weight_ranges(graph)
    fields=sorted({k for e in trace['memory_events'] for k in e})
    missing=[
        dict(provider='actual accepted-command stream',required=['die','stack','client','instruction','kind','sector34','len6','tag16','producer_epoch64','transport_epoch32','accept_ps','beat expansion order'],evidence='trace memory_events contain only '+','.join(fields)+'; r1 demands preserve footprint/hash, not accepted requests'),
        dict(provider='weight cache/coalescer/prefetch phase',required=['cache line hit/miss','SM row/tile issue order','LEN grouping','ready/backpressure','which legal prefetches are permitted','accept time versus writer/read'],evidence='290 actual MATRIX address ranges recovered; every trace cycles is null; L0.o MATRIX depends on NORMALIZE16 which depends on PV15/read12, so concurrent o reads require separately authorized prefetch'),
        dict(provider='bank ACT lookahead and refresh policy',required=['causal ACT/PRE event owner','current-time refresh catchup','controller/PHY/DRAM tCK command phase','bank state read/update ports and timer wrap'],evidence='source estimate/schedule may backdate ACT to arr+REQ; source refresh trigger omits tnow; serialized scan changes require explicit command phase provider'),
        dict(provider='finite common36 phase join',required=['four total sector/RMW credits per die','shared four ACK captures and CDC entries per die','forward/reverse CDC phases','ACK store/result/retire','lease acquire/SCORES/PV visible+retire'],evidence='synthetic fixture enforces shared four sector/ACK records per die and one RMW/store port; actual callback times, ready stalls, RF import/retirement and CDC implementation phases are absent, so fixture times cannot be actual writer latency')]
    phase_alternatives=[]
    for accept in (0,50000):
        req=Beat(target_rows[0]['sector'],1,2**48+1,1,accepted_ps=accept)
        calendar=BankCalendar(source_timing(repo),1000)
        column=calendar.plan(req,accept+18000)
        phase_alternatives.append(dict(sector=req.addr,accept_ps=accept,scan_done_ps=accept+18000,column_ps=str(column),
            legality=audit_bank_events(calendar.events,calendar.t),scope='single actual RMW-read address, synthetic legal acceptance phase'))
    return dict(schema='Qwen_controller_loaded_bank_calendar_prerequisite_r2',source_pins=pins,
        status='ADDRESS_IDENTITIES_BOUND_LEGAL_CONDITIONAL_CALENDAR_ACTUAL_PHASE_PROVIDER_MISSING',
        bank_contract=dict(NPC=32,bank_count_per_PC=32,row_shift=15,row_bits=19,AW=34,
            mapping='pc=((s>>2)^(s>>7)^(s>>12))&31;bank=((((s>>12)^(row>>2))&7)<<2)|((s^row)&3);row=s>>15',
            timings_ps=source_timing(repo),selection_estimate='exact source estimate omits refresh and turnarounds; final plan enforces them',
            legal_policy='causal ACT/PRE at or after completed scan; refresh horizon=max(arr+REQ,now,last_col); quantize commands to explicitly supplied controller edges; preserves constants and all bank timing inequalities',
            source_semantics_difference='Conservative candidate policy, not byte-exact source scheduling. Original SV remains untouched.',
            source_refresh_counterexample=dict(pc=0,arrival_ps=0,last_col_ps=-1000000,now_ps=4000000,next_ref_ps=3900000,source_loop_runs=False,causal_loop_runs=True)),
        finite_binding=dict(QD=64,RQD=32,pending_WR_per_stack=4,
            scan_full_window_edges=[18,35],scan_policy='PC enqueue frozen from scan through reserved column; clock counts retained conservatively for short windows',
            return_prefetch_edges=2,return_arbiter_per_stack_outputs_per_edge=1,WR_ACK_outputs_per_stack_edge=1,
            reservation='WR slot reserved before mutating bank calendar and before column/head pop; held through ACK acceptance; read reserves RQD before scheduling',
            MACs_per_cycle=0,hardware_extra_state='No free calendar hardware: inherited bank state,32-PC compare/ACT/refresh timer ports,WR observer and shared-die join still need hardware lowering/cost closure',
            bank_state_inventory=dict(replicas=256,banks_per_replica=32,per_bank_fields=dict(open=1,row=19,ACT_timer_proxy=64,ACT_ok_timer_proxy=64,PRE_ok_timer_proxy=64),bank_bits=256*32*212,
                read_ports_per_PC=1,read_bits_per_scan_edge=212,write_bits_per_ACT_update=212,
                refresh_bank_updates_per_PC=32,refresh_control_fanout=32,FAW_register_shift_bits_per_ACT=256,
                capacity_scope='Inherited bank state, not additional/free replacement; timer64 remains simulation proxy. Refresh32bank update needs explicit distributed FF/banked lowering; no single-port instantaneous macro update credit')),
        actual_metadata=dict(instruction_count=1737,graph_trace_id_opcode_dependency_equal=True,
            writer_demands_sha_match=len(writer_addresses),writer_addresses=writer_addresses,
            L0_position1_WR_rows=[dict(**r,bankmap=bankmap(r['sector'])) for r in target_rows],
            L0_position1_KV_read_rows=kv_read_rows(graph,graph['instructions'][10],1),
            matrix_weight_ranges=weights,recorded_memory_event_fields=fields,
            payload_read=False,fullprogram_build=False,fullprogram_simulated=False),
        conditional_fixtures=[fixture(graph,competing_weights=False),fixture(graph,competing_weights=True)],
        nonunique_phase_witness=phase_alternatives,
        phase_nonuniqueness='Same recorded RMW-read address and footprint, two legal acceptance phases -> different columns. Trace cycles/null and demand hashes cannot choose one; no payload is needed to expose missing phase.',
        exact_missing_providers=missing,source_r1_unchanged=True,default_enabled=False,
        actual_loaded_calendar_qualified=False,hardware_build_ready=False,hardware_rate_credit=0,token_cycles=None,headline_rate=None)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    record=compose()
    with args.output.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
