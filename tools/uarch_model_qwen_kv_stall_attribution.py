#!/usr/bin/env python3
"""Nonperturbing attribution and lower bounds for frozen02e9 topology. No sweep."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import inspect
import json
import math
from pathlib import Path
import uarch_model_qwen_kv_credit_allocator as A
from uarch_model_qwen_kv_successor import PCService
ROOT=A.ROOT

class TracedPC(PCService):
    def __init__(self):
        super().__init__();self.parts=Counter();self.layer_parts=Counter();self.cursor=0
        self.cause='command_deadline';self.last_parts={};self.worst=None;self.layer_ops=Counter()
    def mark(self,value,reason):
        if value<self.cursor:raise ValueError('trace clock regression')
        self.parts[reason]+=value-self.cursor;self.cursor=value
    def command(self,st,pc,op,earliest,sector):
        self.mark(max(self.cursor,earliest),self.cause)
        previous=self.last_event.get((st,pc),-5)
        self.mark(max(self.cursor,previous),'older_PC_reserved_work')
        edge=max(earliest,previous+5)
        self.mark(edge,'PC_command_feedback_II5')
        answer=super().command(st,pc,op,earliest,sector)
        self.mark(answer,'shared_column_command_path_occupied')
        self.layer_ops[op]+=1
        return answer
    def finish(self,start,layer,st,pc,sector,col):
        if sum(self.parts.values())!=col-start:raise ValueError('column exclusive accounting')
        self.last_parts=dict(self.parts);self.layer_parts.update(self.parts)
        sample=dict(layer=layer,stack=st,PC=pc,sector=sector,column_edge=col,
                    arrival_edge=start,elapsed_edges=col-start,parts_edges=dict(self.parts))
        if self.worst is None or sample['elapsed_edges']>self.worst['elapsed_edges']:self.worst=sample

# Instrument exactly the pinned implementation text. No rewritten scheduling
# expressions or parameter changes; original digests must replay identically.
col=inspect.getsource(PCService.column)
col='\n'.join(line[4:] for line in col.splitlines())+'\n'
col=col.replace('now=math.ceil(arrival_ps/1000);cold=(layer,st,pc)',
    'now=math.ceil(arrival_ps/1000);start=now;self.cursor=now;self.parts=Counter();cold=(layer,st,pc)')
col=col.replace('self.cold.add(cold)','self.cold.add(cold);self.mark(now,"cold_lookahead21")')
col=col.replace('now=max(now,self.last_event.get((st,pc),-5)+5)',
    'now=max(now,self.last_event.get((st,pc),-5));self.mark(now,"older_PC_reserved_work");now=max(now,self.last_event.get((st,pc),-5)+5);self.mark(now,"PC_command_feedback_II5")')
col=col.replace('now=max(now,self.last_event.get((st,pc),-1)+1)',
    'now=max(now,self.last_event.get((st,pc),-1)+1);self.mark(now,"PC_command_feedback_II5")')
col=col.replace("pre=self.command(st,pc,'PREALL'", "self.cause='refresh_PREALL_bank_deadline';pre=self.command(st,pc,'PREALL'")
col=col.replace('now=pre+17','now=pre+17;self.mark(now,"refresh_PREALL17")')
col=col.replace("ref=self.command(st,pc,'REF'", "self.cause='refresh_entry_deadline';ref=self.command(st,pc,'REF'")
col=col.replace('now=ref+1','now=ref+1;self.mark(now,"refresh_command1")')
col=col.replace("now=max(now,s['refblock'])", "now=max(now,s['refblock']);self.mark(now,'refresh_busy350')")
col=col.replace("pre=self.command(st,pc,'PRE'", "self.cause='row_change_PRE_deadline';pre=self.command(st,pc,'PRE'")
col=col.replace('now=pre+1\n','now=pre+1;self.mark(now,"row_PRE_command1")\n')
col=col.replace("act=self.command(st,pc,'ACT'", "self.cause='bank_ACT_source_deadline';act=self.command(st,pc,'ACT'")
col=col.replace('now=act+1','now=act+1;self.mark(now,"bank_ACT_command1")')
col=col.replace("col=self.command(st,pc,'WR'", "self.mark(col,'source_RD_WR_bank_turnaround');self.cause='column_accept';col=self.command(st,pc,'WR'")
col=col.replace('return Fraction(col*1000)','self.finish(start,layer,st,pc,sector,col);return Fraction(col*1000)')
ns=dict(A.__dict__);exec(col,ns);TracedPC.column=ns['column']

class Diagnostic:
    def __init__(self):
        self.wait=Counter();self.patterns=Counter();self.owner_collisions=0
        self.join=Counter();self.group_lease=Counter();self.global_lease=0;self.worst_join=None;self.critical_drain=None;self.first_data={}
    def allocator_wait(self,clock,end,active,cursors,credit,globalcredit,pending,writing,request,prefix,begin):
        if end<clock:raise ValueError('allocator regression')
        duration=end-clock;reasons=set()
        if not active:reasons.add('final_drain_no_unissued_heads')
        for g in active:
            kind,base,n=cursors[g].head
            if not globalcredit:reasons.add('global_cohort_credit')
            if not credit[g]:reasons.add('group16_credit')
            counts=Counter()
            for st in range(4):
                count=n-4 if kind=='V' and st==3 and base%8192==8176 else n
                if kind=='VW' and st!=3:count=0
                for b in range(count):counts[st,A.pc_of(base+b)]+=1
            if any(pending[k]+v>64 for k,v in counts.items()):reasons.add('PC64_pending_credit')
            if kind in ('KW','VW') and any(writing[k]+v>4 for k,v in counts.items()):reasons.add('PC4_write_credit')
            if kind in ('KW','VW') and prefix>clock:reasons.add('producer_prefix_release')
            if request>clock:reasons.add('request_allocator_II1')
        signature='+'.join(sorted(reasons)) or 'event_dispatch'
        self.patterns[signature]+=duration
        # Exclusive wall-clock partition. Mixed reasons remain mixed; do not
        # pretend independent resource waits or request waits are additive.
        self.wait[signature]+=duration
    def cohort(self,ci,at,visible,retired,allocated,g,first,critical,words):
        hold=retired-first;join=at-first
        self.group_lease[g]+=retired-allocated;self.global_lease+=retired-allocated
        self.join['sum_cohort_all_member_wait_ps']+=join
        self.join['sum_cohort_visibility_then_reverse_hold_ps']+=retired-at
        sample=dict(cohort=ci,group=g,allocated_ps=float(allocated),first_data_ps=float(first),last_member_ready_ps=float(at),
            all_words_visible_ps=float(visible),all_grants_ps=float(retired),
            full_lease_after_first_data_ps=float(hold),all_member_barrier_ps=float(join),critical_member=critical,
            words=len(words))
        if self.worst_join is None or hold>self.worst_join['full_lease_after_first_data_ps']:self.worst_join=sample
        if self.critical_drain is None or retired>self.critical_drain['all_grants_ps']:self.critical_drain=sample

cal=inspect.getsource(A.credit_layer_calendar).replace('def credit_layer_calendar(', 'def traced_calendar(')
cal=cal.replace('    cursors=', '    diag=Diagnostic();samples={}\n    cursors=',1)
cal=cal.replace('edge=math.ceil(ready/1000);used=occupied[st][g]',
    'edge=math.ceil(ready/1000);first_edge=edge;used=occupied[st][g]')
cal=cal.replace('used.add(edge);ownedcount[st]+=1;',
    'diag.owner_collisions+=edge-first_edge;used.add(edge);ownedcount[st]+=1;')
cal=cal.replace("digest.update(f'{ci}:{at}:{visible}:{retired};'.encode())", "digest.update(f'{ci}:{at}:{visible}:{retired};'.encode());diag.cohort(ci,at,visible,retired,*samples[ci],words)")
cal=cal.replace('ready=clock;identities=[]','ready=clock;identities=[];first_data=None;critical=None')
old="ready=max(ready,owned(st,g,col+25000+3000+12000+link));identities.append"
new="""member=owned(st,g,col+25000+3000+12000+link)
                    first_data=member if first_data is None else min(first_data,member)
                    if member>ready:
                        critical=dict(stack=st,PC=pc,sector=sector,column_ps=float(col),column_wait_parts_edges=service.last_parts)
                    ready=max(ready,member);identities.append"""
# Original inner indentation is16 spaces; continuation lines inserted at20
# then lowered to match the literal loop body.
# Preserve the original20-space beat-loop indentation.
if old not in cal:raise ValueError('pinned owned return anchor')
cal=cal.replace(old,new)
cal=cal.replace('heapq.heappush(events,(ready,0,index,', 'samples[index]=(clock,g,first_data,critical);heapq.heappush(events,(ready,0,index,')
cal=cal.replace('clock=max(clock,min(choices))',
    'end=max(clock,min(choices));diag.allocator_wait(clock,end,active,cursors,credit,globalcredit,pending,writing,request,prefix,begin);clock=end')
cal=cal.replace('    return dict(end_ps=', '''    diagresult=dict(allocator_exclusive_wait_ps={k:float(v) for k,v in sorted(diag.wait.items())},
        owner_DATA_GRANT_collision_edges=diag.owner_collisions,
        measured_group_lease_work_ps={str(k):float(v) for k,v in diag.group_lease.items()},
        fixed_lease_group16_span_lower_ps=float(max(diag.group_lease.values())/16),
        fixed_lease_global128_span_lower_ps=float(diag.global_lease/128),
        cohort_overlap_counters_ps={k:float(v) for k,v in diag.join.items()},
        worst_cohort_lease=diag.worst_join,critical_final_grant_cohort=diag.critical_drain,
        PC_overlapping_wait_edges=dict(service.layer_parts),PC_command_counts=dict(service.layer_ops),
        worst_PC_column=service.worst,
        owner_group_slots_per_stack=[[len(s) for s in groups] for groups in occupied])
    return dict(diagnostic=diagresult,end_ps=''')
ns=dict(A.__dict__);ns.update(Diagnostic=Diagnostic);exec(cal,ns);traced_calendar=ns['traced_calendar']

def lower_bounds(frozen):
    # Demand-only port bounds: command counts with calendar-generated refresh
    # are a witness constraint, not a universal source minimum. Keep separate.
    rows=frozen['rows'];fill=A.S.fill_destinations()
    fill_counts=[sum(n for tile,n in enumerate(fill) if tile%7==lane) for lane in range(7)]
    owned=[r['diagnostic']['owner_group_slots_per_stack'] for r in rows]
    owner_layer=[max(max(st) for st in row) for row in owned]
    commands=frozen['controller']['commands_per_shared_path']
    column_witness=max(max(st) for st in commands)/1e9
    return dict(fill_demand_port_s=max(fill_counts)*36/1.2e9,
        owner_DATA_plus_GRANT_port_s=sum(owner_layer)/1e9,
        column_payload_only_port_s=32736*36/4/1e9,
        column_with_observed_maintenance_witness_s=column_witness,
        maintenance_scope='Observed source-native command counts depend on this finite ordering and refresh placement; not a universal lower bound for another ordering.',
        PC_feedback_payload_only_port_s=32736*36*5/32/1e9,
        refresh_source_interval_edges=3900,refresh_busy_edges=350,
        owner_counts_include_two_receipts_not_two_payload_transfers=True,
        bounds_overlap_not_sum=True,PHY_wait_assumed=0,actual_PHY_qualified=False,
        scope='Same8/4/7 topology and conditional cold demand. Physical/producer qualification is separate. Strict refresh still unqualified.')

def build(journal=None):
    path=ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json'
    old=json.loads(path.read_text());prev=json.loads(A.S.PREV.read_text())
    rest=(Fraction(3338-451)+Fraction(str(prev['calendar']['layer_allreduce_priced_stream_equivalent_cycles'])))*Fraction(2500,3)
    extra=Fraction(str(prev['calendar']['whole_token_extra_compute_and_exchange_s']))*10**12
    t=Fraction(0);compute=Fraction(0);windows=[Fraction(0)]*2;service=TracedPC();rows=[]
    for layer in range(36):
        begin=max(t,windows[layer%2]);prefix=compute+Fraction(451*2500,3)
        service.layer_parts=Counter();service.layer_ops=Counter();service.worst=None
        row=traced_calendar(layer,begin,prefix,service);t=row.pop('end_ps');ready=row.pop('fill_end_ps')
        compute=max(ready,prefix)+rest;windows[layer%2]=max(t,compute)
        expected=old['calendar']['rows'][layer]
        for key in row:
            if key!='diagnostic' and json.loads(json.dumps(row[key]))!=expected[key]:raise ValueError('calendar perturbation '+str(layer)+':'+key)
        if float(t)!=expected['all_grants_ps'] or float(ready)!=expected['fill_ready_ps']:raise ValueError('boundary perturbation')
        rows.append(dict(layer=layer,begin_ps=float(begin),fill_ready_ps=float(ready),all_grants_ps=float(t),**row))
        if journal is not None:
            journal.write(json.dumps(rows[-1])+chr(10));journal.flush()
    if float((max(t,compute)+extra)/10**12)!=old['calendar']['composed_conditional_s']:raise ValueError('composition perturbation')
    out=dict(schema='qrom-frozen-stall-attribution.v1',predecessor_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        source_sha256=old['source_sha256'],rows=rows,controller=dict(command_counts=dict(service.count),commands_per_shared_path=[[len(v) for v in paths] for paths in service.bus]),
        composed_conditional_s=old['calendar']['composed_conditional_s'],nonperturbing_exact_calendar=True,
        adopted_rate=None,hardware=False,production=False,
        attribution_scope='Allocator signatures partition time within layers. PC/cohort/port counters overlap and cannot be summed into token latency. Critical final-grant member is sampled, not a full end-to-end max-plus DAG.',
        implementation_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('tools/uarch_model_qwen_kv_credit_allocator.py','tools/uarch_model_qwen_kv_successor.py','tools/uarch_model_qwen_kv_stall_attribution.py')})
    out['lower_bounds']=lower_bounds(out)
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);ap.add_argument('--journal',type=Path);args=ap.parse_args()
    if args.journal is None:
        with args.result.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')
    else:
        with args.journal.open('x') as journal,args.result.open('x') as f:
            json.dump(build(journal),f,indent=2);f.write('\n')
