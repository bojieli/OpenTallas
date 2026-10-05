#!/usr/bin/env python3
"""Decoupled cross-layer KV service lease (streaming-only candidate), model only.

Committed copy of the reviewed /tmp/claude-review-20261003/prefetch/work/decoupled.py
(sha256 3c776a52..., pinned in results/uarch/qwen_rom_calibrated_calendar_20261003).
The per-cohort logic is a copy of
tools/uarch_model_qwen_kv_credit_allocator.py:credit_layer_calendar, but one event
loop runs all 36 layers. Layer L+1 descriptor heads become eligible when (a) every
layer-L head has issued its last request (handoff='last_issue') or every layer-L
grant has retired (handoff='all_grants', the control that reproduces the per-layer
lease), and (b) tile window (L+1)%2 has been released by compute_done(L-1).
Only the parameterisation changed: rest/extra compute and the service object are
arguments instead of an environment variable and a fixed PCService. Capacity and
latency literals are left at the 16-credit predecessor values so that callers
(tools/uarch_model_qwen_rom_calibrated_calendar.py) rewrite them by asserted
source anchors, exactly as tools/uarch_model_qwen_kv_credit17.py does.
"""
from collections import Counter
from fractions import Fraction
import heapq
import math
import uarch_model_qwen_kv_credit_allocator as A
S=A.S
from uarch_model_qwen_kv_bank_groups import cohort_words,pc_of

def run(handoff,rest_ps,extra_ps,service):
    if handoff not in ('last_issue','all_grants'):raise ValueError('handoff')
    PREFIX=Fraction(451*2500,3);NL=36
    prefix={0:PREFIX};compute={};fill_end={};begin={0:Fraction(0)};outstanding=Counter();issued_all={}
    lastissue={};allgrant=Counter();issue_at={};hold=[]
    layer=0;cursors=[A.GroupCursor(0,g) for g in range(8)]
    credit=[16]*8;globalcredit=128;events=[];fill=[Fraction(0)]*7;clock=Fraction(0);request=Fraction(0);index=0;rr=0
    pending=Counter();writing=Counter();perpool=Counter();peak_pool=0;peak_live=0;peak_pending=0;peak_writing=0
    occupied=[[set() for _ in range(8)] for _ in range(4)];latest=Fraction(0)
    link=Fraction(39*2500,3);period=Fraction(2500,3);layer_fill=Counter();overlap_cohorts=0
    def owned(st,g,ready):
        edge=math.ceil(ready/1000);used=occupied[st][g]
        while edge in used:edge+=1
        used.add(edge);return Fraction((edge+1)*1000)
    def reservations(head):
        kind,base,n=head;counts=Counter()
        for st in range(4):
            count=n-4 if kind=='V' and st==3 and base%8192==8176 else n
            if kind=='VW' and st!=3:count=0
            for beat in range(count):counts[st,pc_of(base+beat)]+=1
        return counts
    def available(head):
        iswrite=head[0] in ('KW','VW')
        return all(pending[key]+n<=64 and (not iswrite or writing[key]+n<=4) for key,n in reservations(head).items())
    def needs_prefix(head):return head[0] in ('KW','VW') or (head[0]=='V' and head[1]%8192==8176)
    def release(g):
        h=cursors[g].head
        if needs_prefix(h):
            if layer not in prefix:return None
            return max(request,prefix[layer]) if h[0] in ('KW','VW') else max(request,begin[layer])
        return max(request,begin[layer])
    def settle():
        # close layers whose fills are all visible and whose requests are all issued
        for L in sorted(issued_all):
            if L in compute or outstanding[L]:continue
            fe=layer_fill[L];fill_end[L]=fe
            compute[L]=max(fe,prefix[L])+rest_ps
            if L+1<NL:prefix[L+1]=compute[L]+PREFIX
    while True:
        while events and events[0][0]<=clock:
            at,typ,ci,data=heapq.heappop(events)
            L,g,words,identities=data
            if typ==0:
                visible=at
                for tile,row in sorted(words):
                    lane=tile%7;fill[lane]=max(fill[lane],at+4*period)+period
                    visible=max(visible,fill[lane]+period)
                if words:layer_fill[L]=max(layer_fill[L],visible)  # == max(fill)+period over layer (fill words only, as baseline fill_end_ps)
                retired=visible
                for st,pc,sector,iswrite in identities:retired=max(retired,owned(st,g,visible+link))
                heapq.heappush(events,(retired,1,ci,data));outstanding[L]-=1;settle()
            else:
                credit[g]+=1;globalcredit+=1;hold.append(at-issue_at.pop(ci))
                for st,pc,sector,iswrite in identities:
                    pending[st,pc]-=1
                    if iswrite:writing[st,pc]-=1
                for tile,row in words:perpool[g,tile%7]-=1
                latest=max(latest,at);allgrant[L]=max(allgrant[L],at)
        # lease handoff
        if all(c.head is None for c in cursors) and layer not in issued_all:
            issued_all[layer]=clock;settle()
        if layer in issued_all and layer+1<NL:
            nxt=layer+1
            win_ok=(nxt-2<0) or (nxt-2 in compute)
            if handoff=='all_grants':gate=(not events)
            else:gate=True
            if win_ok and gate:
                b=max(clock,compute[nxt-2] if nxt-2>=0 else 0)
                if b<=clock:
                    layer=nxt;begin[layer]=b;rr=0;cursors=[A.GroupCursor(layer,g) for g in range(8)];continue  # rr reset per layer as baseline
        if layer==NL-1 and layer in issued_all and not events:break
        active=[g for g,c in enumerate(cursors) if c.head is not None]
        eligible=[]
        for g in active:
            if credit[g] and globalcredit and available(cursors[g].head):
                r=release(g)
                if r is not None and r<=clock:eligible.append(g)
        if eligible:
            g=A.select_group(eligible,rr);kind,base,n=cursors[g].head;rr=(g+1)%8
            clock=Fraction(math.ceil(clock/1000)*1000);request=clock+1000
            words,_=cohort_words(layer,base,n) if kind in ('K','V') else (set(),[])
            if any(v>5 for v in Counter(t%7 for t,r in words).values()):raise ValueError('5 words')
            for key,ns in reservations(cursors[g].head).items():
                pending[key]+=ns;peak_pending=max(peak_pending,pending[key])
                if kind in ('KW','VW'):writing[key]+=ns;peak_writing=max(peak_writing,writing[key])
            credit[g]-=1;globalcredit-=1;peak_live=max(peak_live,128-globalcredit)
            if any(k not in compute and k<layer for k in range(layer)):overlap_cohorts+=1
            for tile,row in words:perpool[g,tile%7]+=1;peak_pool=max(peak_pool,perpool[g,tile%7])
            if peak_pool>80:raise ValueError('80 slots')
            ready=clock;identities=[]
            for st in range(4):
                count=n-4 if kind=='V' and st==3 and base%8192==8176 else n
                if kind=='VW' and st!=3:count=0
                for beat in range(count):
                    sector=base+beat;pc=pc_of(sector)
                    col=service.column(layer,st,sector,kind in ('KW','VW'),clock+3000+link+10000)
                    ready=max(ready,owned(st,g,col+25000+3000+12000+link));identities.append((st,pc,sector,kind in ('KW','VW')))
            if kind=='V' and base%8192==8176:ready=max(ready,prefix[layer])
            issue_at[index]=clock;heapq.heappush(events,(ready,0,index,(layer,g,words,identities)));index+=1;outstanding[layer]+=1;cursors[g].advance()
            continue
        choices=[events[0][0]] if events else []
        rel=[release(g) for g in active if credit[g] and globalcredit and available(cursors[g].head)]
        rel=[r for r in rel if r is not None]
        if rel:choices.append(min(rel))
        if layer in issued_all and layer+1<NL and (layer-1) in compute:choices.append(max(clock,compute[layer-1]))
        if not choices:raise ValueError('deadlock at layer %d'%layer)
        nc=max(clock,min(choices))
        if nc==clock and not (events and events[0][0]<=clock):
            # only possible via window path; advance one edge
            nc=clock+1000
        clock=nc
    settle()
    if any(pending.values()) or any(writing.values()) or globalcredit!=128:raise ValueError('debts')
    total=(max(latest,compute[NL-1])+extra_ps)/10**12
    rows=[dict(layer=L,begin_ps=float(begin[L]),last_issue_ps=float(issued_all[L]),prefix_ready_ps=float(prefix[L]),
        fill_ready_ps=float(fill_end[L]),all_grants_ps=float(allgrant[L]),compute_done_ps=float(compute[L])) for L in range(NL)]
    return dict(total_s=float(total),total_exact_ps=str(max(latest,compute[NL-1])+extra_ps),rows=rows,cohorts=index,
        peak_live_cohorts=peak_live,peak_pending_entries_per_PC=peak_pending,peak_write_slots_per_PC=peak_writing,
        peak_words_per_group_lane_pool=peak_pool,cross_layer_overlapped_issues=overlap_cohorts,
        command_counts=dict(service.count),max_refresh_lateness_edges=service.max_refresh_lateness,
        rest_ps=float(rest_ps),extra_ps=float(extra_ps),mean_credit_hold_ps=float(sum(hold)/len(hold)),
        p50_credit_hold_ps=float(sorted(hold)[len(hold)//2]),p90_credit_hold_ps=float(sorted(hold)[9*len(hold)//10]))
