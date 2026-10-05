#!/usr/bin/env python3
"""One source-hash partitioned credit allocator for the retained8/4/7 candidate.
Address/calendar model only. Eight heads, no stored full-layer descriptor journal.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import heapq
import json
import math
from pathlib import Path
import uarch_model_qwen_kv_successor as S
from uarch_model_qwen_kv_bank_groups import burst_group,cohort_words,pc_of
from uarch_model_qwen_parent_context import tree_count
ROOT=S.ROOT

class GroupCursor:
    """Invert source PC hash within aligned eight-cohort slabs.

    For aligned16-sector base, group=(m^(m>>5)^(m>>10))&7,
    m=base>>4. High terms are constant in an aligned8-block slab.
    Four extents are source K/V reads and closing K/V writes per head.
    Store one current descriptor and extent/slab state, never2048 records.
    """
    def __init__(self,layer,group):
        if not 0<=layer<36 or not 0<=group<8:raise ValueError('layer/group')
        self.group=group;self.extents=[]
        for head in range(2):
            k=(layer*2+head)*8192;v=k+589824
            self.extents.extend([('K',k,8160),('V',v,8192),('KW',k+8176,16),('VW',v+8188,4)])
        self.extent=0;self.slab=None;self.head=None;self.write_tail=None;self.advance()
    def advance(self):
        self.head=None
        if self.write_tail is not None:
            kind,base,stop=self.write_tail
            self.head=(kind,base,1)
            self.write_tail=(kind,base+1,stop) if base+1<stop else None
            return
        while self.extent<len(self.extents):
            kind,start,length=self.extents[self.extent];end=start+length
            slab=(start>>7) if self.slab is None else self.slab
            m0=slab*8;m=m0|(self.group^((m0>>5)&7)^((m0>>10)&7))
            base=max(m*16,start);stop=min(m*16+16,end)
            self.slab=slab+1
            if base<stop:
                if burst_group(base,stop-base)!=self.group:raise ValueError('hash inversion')
                if kind in ('KW','VW'):
                    self.head=(kind,base,1)
                    self.write_tail=(kind,base+1,stop) if base+1<stop else None
                else:self.head=(kind,base,stop-base)
                return
            if m*16>=end or (slab+1)*128>=end:
                self.extent+=1;self.slab=None

def select_group(eligible,rr):
    if not 0<=rr<8 or any(not 0<=g<8 for g in eligible):raise ValueError('arbiter group')
    return min(eligible,key=lambda g:(g-rr)%8) if eligible else None

def credit_layer_calendar(layer,begin,prefix,service):
    """One finite ready-cohort scheduler over8x7x80 quarter-write pools.

   128live cohorts,16/group;eachcohort<=5words/lane, hence80/group/lane.
    Process return-ready events before selecting lane writes; another ready
    group can fill a lane while a PC waits. No FIFO HOL across future-ready
    cohorts, no extra owner/bank/command replication. All7outputs have their
    own8group-bank read selection; explicit cells and4stages priced.
    """
    cursors=[GroupCursor(layer,g) for g in range(8)]
    credit=[16]*8;globalcredit=128;events=[];fill=[begin]*7;clock=begin;request=begin;index=0;rr=0
    bypasses=0;max_active_heads=0;group_issues=Counter();pending=Counter();writing=Counter();peak_pending=0;peak_writing=0
    occupied=[[set() for _ in range(8)] for _ in range(4)];latest=begin;digest=hashlib.sha256()
    commandcount=[0]*4;ownedcount=[0]*4;peak_live=0;perpool=Counter();peak_pool=0
    link=Fraction(39*2500,3);period=Fraction(2500,3)
    def owned(st,g,ready):
        edge=math.ceil(ready/1000);used=occupied[st][g]
        while edge in used:edge+=1
        used.add(edge);ownedcount[st]+=1;return Fraction((edge+1)*1000)
    def reservations(head):
        kind,base,n=head;counts=Counter()
        for st in range(4):
            count=n-4 if kind=='V' and st==3 and base%8192==8176 else n
            if kind=='VW' and st!=3:count=0
            for beat in range(count):counts[st,pc_of(base+beat)]+=1
        return counts
    def available(head):
        iswrite=head[0] in ('KW','VW')
        return all(pending[key]+n<=64 and (not iswrite or writing[key]+n<=4)
                   for key,n in reservations(head).items())
    while any(c.head is not None for c in cursors) or events:
        while events and events[0][0]<=clock:
            at,typ,ci,data=heapq.heappop(events)
            if typ==0:
                g,words,identities=data;visible=at
                for tile,row in sorted(words):
                    lane=tile%7;fill[lane]=max(fill[lane],at+4*period)+period
                    visible=max(visible,fill[lane]+period)
                retired=visible
                for st,pc,sector,iswrite in identities:retired=max(retired,owned(st,g,visible+link))
                heapq.heappush(events,(retired,1,ci,(g,words,identities)))
                digest.update(f'{ci}:{at}:{visible}:{retired};'.encode())
            else:
                g,words,identities=data;credit[g]+=1;globalcredit+=1
                for st,pc,sector,iswrite in identities:
                    pending[st,pc]-=1
                    if iswrite:writing[st,pc]-=1
                for tile,row in words:perpool[g,tile%7]-=1
                latest=max(latest,at)
        if not any(c.head is not None for c in cursors) and not events:break
        active=[g for g,c in enumerate(cursors) if c.head is not None]
        max_active_heads=max(max_active_heads,len(active))
        eligible=[g for g in active if credit[g] and globalcredit and available(cursors[g].head) and
                  max(request,prefix if cursors[g].head[0] in ('KW','VW') else begin)<=clock]
        if eligible:
            g=select_group(eligible,rr)
            kind,base,n=cursors[g].head
            if active and g!=min(active,key=lambda x:cursors[x].head[1]):bypasses+=1
            rr=(g+1)%8;group_issues[g]+=1
            clock=Fraction(math.ceil(clock/1000)*1000);request=clock+1000
            words,_=cohort_words(layer,base,n) if kind in ('K','V') else (set(),[])
            by_lane=Counter(t%7 for t,r in words)
            if any(n>5 for n in by_lane.values()):raise ValueError('fivewords/cohort/lane source bound')
            for key,nslots in reservations(cursors[g].head).items():
                pending[key]+=nslots;peak_pending=max(peak_pending,pending[key])
                if kind in ('KW','VW'):
                    writing[key]+=nslots;peak_writing=max(peak_writing,writing[key])
            credit[g]-=1;globalcredit-=1;peak_live=max(peak_live,128-globalcredit)
            for tile,row in words:
                perpool[g,tile%7]+=1;peak_pool=max(peak_pool,perpool[g,tile%7])
            if peak_pool>80:raise ValueError('80 actual slots/group/lane')
            ready=clock;identities=[]
            for st in range(4):
                count=n-4 if kind=='V' and st==3 and base%8192==8176 else n
                if kind=='VW' and st!=3:count=0
                for beat in range(count):
                    sector=base+beat;pc=pc_of(sector)
                    col=service.column(layer,st,sector,kind in ('KW','VW'),clock+3000+link+10000)
                    commandcount[st]+=1
                    ready=max(ready,owned(st,g,col+25000+3000+12000+link));identities.append((st,pc,sector,kind in ('KW','VW')))
            if kind=='V' and base%8192==8176:ready=max(ready,prefix)
            heapq.heappush(events,(ready,0,index,(g,words,identities)));index+=1;cursors[g].advance()
            continue
        releases=[max(request,prefix if cursors[g].head[0] in ('KW','VW') else begin)
                  for g in active if credit[g] and globalcredit and available(cursors[g].head)]
        next_request=min(releases) if releases else None
        choices=[events[0][0]] if events else []
        if next_request is not None:choices.append(next_request)
        if not choices:raise ValueError('finite credit deadlock')
        clock=max(clock,min(choices))
    if any(pending.values()) or any(writing.values()) or globalcredit!=128 or credit!=[16]*8:
        raise ValueError('pending/write/group/global debts not fully retired')
    return dict(end_ps=latest,fill_end_ps=max(fill)+period,cohorts=index,
        reservation_sha256=digest.hexdigest(),credit_aware_bypasses=bypasses,
        maximum_descriptor_heads=max_active_heads,group_issues=dict(sorted(group_issues.items())),allocator_registered_edges=3,command_count_per_stack=commandcount,
        owned_data_and_grant_count_per_stack=ownedcount,peak_live_cohorts=peak_live,
        peak_pending_entries_per_PC=peak_pending,peak_write_slots_per_PC=peak_writing,
        peak_words_per_group_lane_pool=peak_pool,assembly_group_lane_pools=56,assembly_slots_per_pool=80,
        global_assembly_slots=4480,all_reverse_grants_reserved=True,physical_or_payload_qualification=False)


def build():
    # Same integer configuration, deadlines, banks and double-debit rules.
    # Substitute only the finite request selection, then price its added cones.
    original=S.ready_layer_calendar
    try:
        S.ready_layer_calendar=credit_layer_calendar
        out=S.build()
    finally:S.ready_layer_calendar=original
    predecessor=ROOT/'results/uarch/qwen_rom_kv_successor_20261002/model-r7.json'
    old=json.loads(predecessor.read_text())
    cells=json.loads((ROOT/'results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json').read_text())['cells']
    ff=cells['ASR_area_um2']+cells['INV_area_um2'];a=cells['AND3_area_um2'];inv=cells['INV_area_um2'];buf=cells['BUF_area_um2']
    # Existing455-bit pergroup ingress holds/address counters charged byfd406.
    # Only new epoch/extent/release descriptors and registered8-way arbiter.
    counts=dict(descriptor_epoch_extent_release=4*8*(192+32+3+26+64+1),
        request_selection_three_registers=4*3*(455+192+3+32),
        round_robin_and_inflight_group_reservations=4*(3+8*3),
        matched_stack_accept_holds=4*(192+8+1))
    reps=dict(descriptor_epoch_extent_release=32,request_selection_three_registers=4,
        round_robin_and_inflight_group_reservations=4,matched_stack_accept_holds=4)
    collector=sum(2*reps[k]*tree_count(n//reps[k],8)['nodes'] for k,n in counts.items())
    muxbits=4*7*(455+192+32+3);eligbits=4*8*(5+64+32);hashxorbits=4*8*6
    delta=(sum(counts.values())*ff+collector*buf+muxbits*(3*a+2*inv)+(eligbits+hashxorbits)*(3*a+5*inv))/1e6
    out['schema']='qrom-eight-source-hash-cursors-credit-arbiter.v1'
    out['dimensioning']['mandatory_first_payload_ps']+=3000
    out['dimensioning']['mandatory_layer_visibility_start_ps']+=3000
    out['dimensioning']['source_cold_lease_six_fill_lower_s']+=36*3000/10**12
    out['dimensioning']['credit_arbiter_three_registered_edges_priced']=True

    out['predecessor_successor_sha256']=hashlib.sha256(predecessor.read_bytes()).hexdigest()
    out['request_allocator']=dict(source_equation='pc=((sector>>2)^(sector>>7)^(sector>>12))&31; group=pc//4',
        inverse='m=aligned16-sector base>>4; for slab m0=8*slab, m=m0|(group^((m0>>5)&7)^((m0>>10)&7))',
        descriptor_heads=8,full_layer_descriptor_RAM_entries=0,per_group_order_preserved=True,
        pending_service_and_reverse_credits_unchanged=True,registered_selection_edges=3,accept_II_edges=1,
        fairness='Rotating pointer advances only on accepted matched cohort. A continuously eligible head is selected within8 accepted cohorts; no wall-time bound while credits or producer release are withheld.',
        final_accept_contract='Reserve all4 stack tags/16-group credits atomically; retain immutable source epoch and descriptor; reject stale epoch or missing stack before any commit. Actual joint-update RTL and producer receipt remain unqualified.',
        existing_ingress_holds_charged_once=True,source_provider_connected=False,
        heterogeneous_write_request_LEN=1,write_cohort_heads_per_layer=40,read_cohort_heads_per_layer=2044,
        actual_source_write_ACK_and_protection_bound=False)
    out['cells']['credit_allocator_added_FF']=counts
    out['cells']['credit_allocator_replica_counts']=reps
    out['cells']['credit_allocator_collector_buffers']=collector
    out['cells']['credit_allocator_mux_bits']=muxbits
    out['cells']['credit_allocator_eligibility_comparison_bits']=eligbits
    out['cells']['source_hash_inverse_XOR_bits']=hashxorbits
    out['cells']['credit_allocator_delta_mm2']=delta
    out['cells']['total_known_service_mm2']+=delta
    out['physical']['conditional_remaining_mm2']-=delta
    out['physical']['matched_accept_local_control_bits']=4*(192+8+1)
    out['physical']['global_boundary_bits']+=4*(192+8+1)
    out['physical']['matched_accept_control_route_proven']=False
    out['calendar']['predecessor_conditional_s']=old['calendar']['composed_conditional_s']
    out['calendar']['conditional_reduction_s']=old['calendar']['composed_conditional_s']-out['calendar']['composed_conditional_s']
    out['calendar']['scope']='One8/4/7 source-hash partitioned credit-aware allocator; all36 sequential layers, full1536 destinations and native deadlines. Conditional address-only calendar; actual producer release, protected atomic accept, pending capacity, strict refresh, PHY and physical slots remain open.'
    out['implementation_sha256']['tools/uarch_model_qwen_kv_credit_allocator.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out['admission']['blockers'].append('Protected matched4-stack atomic accept/epoch and request-arbiter SSFF/CDC/route receipt')
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);args=ap.parse_args()
    with args.result.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')
