#!/usr/bin/env python3
"""ONE8/4/7 QROM successor; finite source-native PC deadline/credit model.

No RTL, sweep, payload/state fabrication or sustained PHY qualification.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import heapq
import json
import math
from pathlib import Path
import subprocess
from uarch_model_qwen_kv_bank_groups import pc_of,burst_group,cohort_words,fill_destinations
from uarch_model_qwen_parent_context import tree_count
ROOT=Path(__file__).resolve().parents[1]
PREV=ROOT/'results/uarch/qwen_rom_kv_bank_groups_20261002/model-r4.json'

class PendingReads:
    """64 pre-reserved combined pending/raw/held credits, immutable identity.

    Source25edge read due retained. Provider tag/beat/sector/epochs validated;
    credit releases only on downstream consume. No synthetic qualification.
    """
    def __init__(self):self.pending={};self.raw={};self.used=set()
    def issue(self,key,sector,producer,transport,column):
        if key in self.used:raise ValueError('duplicate flight/returned identity')
        if len(self.used)>=64:raise ValueError('64 combined pending/raw credits')
        self.pending[key]=(sector,producer,transport,column+25);self.used.add(key)
    def returned(self,key,sector,producer,transport,edge,payload):
        if key not in self.pending:raise ValueError('unallocated or duplicate raw return')
        actual=self.pending[key]
        if (sector,producer,transport)!=actual[:3] or edge<actual[3]:raise ValueError('immutable identity/due')
        if not isinstance(payload,bytes) or len(payload)!=32:raise ValueError('actual32B payload')
        self.raw[key]=payload;del self.pending[key]
    def consume(self,key):
        if key not in self.raw:raise ValueError('no owned raw return')
        value=self.raw.pop(key);self.used.remove(key);return value

class Lookahead:
    """Actual-width whole-record16cache over64RAMslots,1R1W/edge.

    Free slots retain immutable generation/order. One read captures nextedge;
    selected holes do not trigger whole-RAM shifts. Cached candidate is usable
    only if older lookahead records are captured; alias and stale revalidation
    refusals leave state unchanged. Boundary data remain caller-owned.
    """
    def __init__(self):
        self.ram={};self.cache={};self.read=None;self.tick=0;self.sequence=0;self.skips=0
    def edge(self,enqueued=None):
        if self.read is not None:
            slot,seq,record=self.read
            if slot in self.ram and self.ram[slot][0]==seq:self.cache[slot]=(seq,record)
            self.read=None
        if enqueued is not None:
            if len(self.ram)>=64:raise ValueError('64 actual requestRAM slots')
            if not isinstance(enqueued,dict) or 'sector' not in enqueued or 'write' not in enqueued:
                raise ValueError('immutable actual whole record')
            slot=next(i for i in range(64) if i not in self.ram)
            self.ram[slot]=(self.sequence,dict(enqueued));self.sequence+=1
        oldest=sorted(self.ram,key=lambda i:self.ram[i][0])[:16]
        self.cache={i:r for i,r in self.cache.items() if i in oldest}
        for slot in oldest:
            if slot not in self.cache:
                seq,record=self.ram[slot];self.read=(slot,seq,dict(record));break
        self.tick+=1
    def select(self,legal,pending_aliases=()):
        oldest=sorted(self.ram,key=lambda i:self.ram[i][0])[:16]
        earlier=[]
        for index,slot in enumerate(oldest):
            if slot not in self.cache:break
            seq,record=self.cache[slot]
            alias=any(r['sector']==record['sector'] and (r['write'] or record['write']) for r in earlier)
            alias|=any(r['sector']==record['sector'] and (r['write'] or record['write']) for r in pending_aliases)
            if not alias and (self.skips<16 or index==0) and legal(record):return slot,seq,dict(record)
            earlier.append(record)
        return None
    def commit(self,candidate,legal,pending_aliases=()):
        if candidate is None:return None
        slot,seq,record=candidate
        if slot not in self.cache or self.cache[slot]!=(seq,record):raise ValueError('stale generation/whole record')
        actual=self.select(lambda r:r==record and legal(r),pending_aliases)
        if actual!=candidate:raise ValueError('final alias/deadline/credit revalidation')
        oldest=min(self.ram,key=lambda i:self.ram[i][0]);self.skips=0 if slot==oldest else self.skips+1
        del self.ram[slot];del self.cache[slot];return record

class PCService:
    """32 native banks/PC;4 shared command paths/stack retain ALL ops.

    Native integer deadline constraints copied by asserted source anchors.
    One candidate reserved command calendar can fill holes with another PC;
    never hold the whole global bus while a bank waits. Exact64pending credit
    bound comes from16 matched cohorts/group and4 records/PC/cohort. Warm
    lookahead refill1RAMread/edge, whole16 records,17edge initial capture.
    This is an address-only reservation, not actual provider physical service.
    """
    def __init__(self):
        self.bus=[[set() for _ in range(4)] for _ in range(4)];self.states={}
        self.count=Counter();self.digest=hashlib.sha256();self.cold=set();self.max_refresh_lateness=0
        self.last_event={}
    def state(self,st,pc):
        key=st,pc
        if key not in self.states:
            self.states[key]=dict(opened=[False]*32,rows=[0]*32,act=[0]*32,pre=[0]*32,actok=[0]*32,
                lastact=0,lastcol=0,lastrd=None,lastwr=None,wrbg=0,actbg=[0]*4,colbg=[0]*4,faw=[0]*4,
                nextref=3900+(3900*pc)//32,refblock=0)
        return self.states[key]
    def command(self,st,pc,op,earliest,sector):
        path=pc//8;used=self.bus[st][path];edge=max(earliest,self.last_event.get((st,pc),-5)+5)
        while edge in used:edge+=1
        used.add(edge);self.last_event[st,pc]=edge;self.count[op]+=1
        self.digest.update(f'{st}:{pc}:{op}:{sector}:{edge};'.encode());return edge
    def column(self,layer,st,sector,write,arrival_ps):
        pc=pc_of(sector);s=self.state(st,pc);row=sector>>15
        bank=((((sector>>12)^(row>>2))&7)<<2)|((sector^row)&3);bg=bank&3
        now=math.ceil(arrival_ps/1000);cold=(layer,st,pc)
        if cold not in self.cold:now+=21;self.cold.add(cold)
        # Four eligibility registers plus final revalidation: conservative
        #perPC commandII5, not free combinationalII1. Other PCs fill bus holes.
        now=max(now,self.last_event.get((st,pc),-5)+5)
        now=max(now,self.last_event.get((st,pc),-1)+1)
        while now>=s['nextref']:
            if any(s['opened']):
                pre=self.command(st,pc,'PREALL',max([now]+[s['pre'][b] for b in range(32) if s['opened'][b]]),sector)
                s['opened']=[False]*32
                s['actok']=[max(v,pre+17) for v in s['actok']];now=pre+17
            ref=self.command(st,pc,'REF',max(now,s['lastcol']+2,s['refblock']),sector)
            self.max_refresh_lateness=max(self.max_refresh_lateness,ref-s['nextref'])
            s['nextref']+=3900;s['refblock']=ref+350;s['actok']=[max(v,ref+350) for v in s['actok']]
            now=ref+1
        now=max(now,s['refblock'])
        if s['opened'][bank] and s['rows'][bank]!=row:
            pre=self.command(st,pc,'PRE',max(now,s['pre'][bank]),sector)
            s['opened'][bank]=False;s['actok'][bank]=max(s['actok'][bank],pre+17);now=pre+1
        if not s['opened'][bank]:
            act=self.command(st,pc,'ACT',max(now,s['actok'][bank],s['lastact']+3,s['actbg'][bg]+4,s['faw'][0]+15),sector)
            s['opened'][bank]=True;s['rows'][bank]=row;s['act'][bank]=act;s['pre'][bank]=act+29
            s['actok'][bank]=act+46;s['lastact']=act;s['actbg'][bg]=act;s['faw']=s['faw'][1:]+[act];now=act+1
        col=max(now,s['act'][bank]+(10 if write else 20),s['lastcol']+2,s['colbg'][bg]+3)
        if write and s['lastrd'] is not None:col=max(col,s['lastrd']+10)
        if not write and s['lastwr'] is not None:col=max(col,s['lastwr']+7+2+(7 if s['wrbg']==bg else 5))
        col=self.command(st,pc,'WR' if write else 'RD',col,sector)
        s['lastcol']=col;s['colbg'][bg]=col
        if write:s['lastwr']=col;s['wrbg']=bg;s['pre'][bank]=max(s['pre'][bank],col+30)
        else:s['lastrd']=col;s['pre'][bank]=max(s['pre'][bank],col+6)
        return Fraction(col*1000)

def finite_layer_calendar(layer,begin_ps,prefix_ready_ps,service):
    """Construct ONE conservative address-only finite reservation witness.

    Four matched stack members reserve <=32 central words before commands.
    Group16 burst slots and128 global cohorts are held until final reverse
    grant. Real data/state, PHY row/refresh service and CDC qualification are
    absent; fixed functional-model minimum delays are conditional lower costs.
    Full source lookup12 and39-stream-edge links are retained, never removed.
    """
    command=[[0]*4 for _ in range(4)];occupied=[[set() for _ in range(8)] for _ in range(4)]
    groups=[[begin_ps]*16 for _ in range(8)];global_slots=[begin_ps]*128
    fill=[begin_ps]*7;request=begin_ps;latest=begin_ps;digest=hashlib.sha256()
    cohorts=0;command_count=[0]*4;owned_count=[0]*4;max_words=0
    link=Fraction(39*2500,3);ns=1000
    def owned_slot(st,g,ready):
        edge=math.ceil(ready/ns);used=occupied[st][g]
        while edge in used:edge+=1
        used.add(edge);owned_count[st]+=1
        return Fraction((edge+1)*ns)
    for head in range(2):
        k=(layer*2+head)*8192;v=k+589824
        batches=[('K',k,8160),('V',v,8192),('KW',k+8176,16),('VW',v+8188,4)]
        for kind,base,length in batches:
            while length:
                n=min(length,16-base%16);g=burst_group(base,n)
                words,_=cohort_words(layer,base,n) if kind in ('K','V') else (set(),[])
                max_words=max(max_words,len(words))
                start=max(request,heapq.heappop(groups[g]),heapq.heappop(global_slots))
                if kind in ('KW','VW'):start=max(start,prefix_ready_ps)
                request=start+ns  # existing one burst allocator/stack, not4free requests
                ready=start;identities=[]
                for st in range(4):
                    actual_n=(n-4 if kind=='V' and st==3 and base%8192==8176 else n)
                    if kind=='VW' and st!=3:actual_n=0
                    for beat in range(actual_n):
                        sector=base+beat;pc=pc_of(sector);path=g//2
                        # request39stream + sourceREQ10ns; four32B column ports.
                        col=service.column(layer,st,sector,kind in ('KW','VW'),start+link+10000)
                        command[st][path]=col+ns;command_count[st]+=1
                        # Source CL12.5ns/RSP10ns minimum, earlycapture then
                        #full12edge lookup and39stream response route.
                        received=owned_slot(st,g,col+25000+3000+12000+link)
                        ready=max(ready,received);identities.append((st,pc,sector))
                if kind=='V' and base%8192==8176:ready=max(ready,prefix_ready_ps)
                for tile,row in sorted(words):
                    lane=tile%7;fill[lane]=max(fill[lane],ready+Fraction(2500,3))+Fraction(2500,3)
                visible=max([ready]+[fill[t%7]+Fraction(2500,3) for t,r in words])
                # Grant cannot be borrowed at earlier DATA acceptance: reserve
                #the actual shared467bit owner bus only after reverse traversal.
                retired=visible
                for st,pc,sector in identities:
                    retired=max(retired,owned_slot(st,g,visible+link))
                heapq.heappush(groups[g],retired);heapq.heappush(global_slots,retired)
                latest=max(latest,retired);cohorts+=1
                digest.update(json.dumps([kind,base,n,str(start),str(ready),str(visible),str(retired)],separators=(',',':')).encode())
                base+=n;length-=n
    return dict(end_ps=latest,fill_end_ps=max(fill),cohorts=cohorts,
        reservation_sha256=digest.hexdigest(),command_count_per_stack=command_count,
        owned_data_and_grant_count_per_stack=owned_count,
        max_words_per_cohort=max_words,global_cohort_limit=128,group_cohort_limit=16,
        raw_return_entries_per_PC_bound=64,global_assembly_entries_bound=4096,
        flight_output_credit_bound=32,all_reverse_grants_reserved=True,
        lookup_admission='Reserve owned DATA slot before context lookup; issue bank read12edges before slot, capture at+1 and hold immutable. At most12flight/group; stalled rawreturns retain64PC RAM/group16 burst credits. One registered assembly select and one masked-write visibility edge priced; actual CDC/fill-wire delays not closed.',
        physical_or_payload_qualification=False)

def ready_layer_calendar(layer,begin,prefix,service):
    """One finite ready-cohort scheduler over8x7x80 quarter-write pools.

   128live cohorts,16/group;eachcohort<=5words/lane, hence80/group/lane.
    Process return-ready events before selecting lane writes; another ready
    group can fill a lane while a PC waits. No FIFO HOL across future-ready
    cohorts, no extra owner/bank/command replication. All7outputs have their
    own8group-bank read selection; explicit cells and4stages priced.
    """
    batches=[]
    for head in range(2):
        k=(layer*2+head)*8192;v=k+589824
        for kind,base,length in [('K',k,8160),('V',v,8192),('KW',k+8176,16),('VW',v+8188,4)]:
            while length:
                n=min(length,16-base%16);batches.append((kind,base,n));base+=n;length-=n
    credit=[16]*8;globalcredit=128;events=[];fill=[begin]*7;clock=begin;request=begin;index=0
    occupied=[[set() for _ in range(8)] for _ in range(4)];latest=begin;digest=hashlib.sha256()
    commandcount=[0]*4;ownedcount=[0]*4;peak_live=0;perpool=Counter();peak_pool=0
    link=Fraction(39*2500,3);period=Fraction(2500,3)
    def owned(st,g,ready):
        edge=math.ceil(ready/1000);used=occupied[st][g]
        while edge in used:edge+=1
        used.add(edge);ownedcount[st]+=1;return Fraction((edge+1)*1000)
    while index<len(batches) or events:
        while events and events[0][0]<=clock:
            at,typ,ci,data=heapq.heappop(events)
            if typ==0:
                g,words,identities=data;visible=at
                for tile,row in sorted(words):
                    lane=tile%7;fill[lane]=max(fill[lane],at+4*period)+period
                    visible=max(visible,fill[lane]+period)
                retired=visible
                for st,pc,sector in identities:retired=max(retired,owned(st,g,visible+link))
                heapq.heappush(events,(retired,1,ci,(g,words)))
                digest.update(f'{ci}:{at}:{visible}:{retired};'.encode())
            else:
                g,words=data;credit[g]+=1;globalcredit+=1
                for tile,row in words:perpool[g,tile%7]-=1
                latest=max(latest,at)
        if index==len(batches) and not events:break
        if index<len(batches):
            kind,base,n=batches[index];g=burst_group(base,n)
            release=max(request,prefix if kind in ('KW','VW') else begin)
            if credit[g] and globalcredit and release<=clock:
                clock=Fraction(math.ceil(clock/1000)*1000);request=clock+1000
                words,_=cohort_words(layer,base,n) if kind in ('K','V') else (set(),[])
                by_lane=Counter(t%7 for t,r in words)
                if any(n>5 for n in by_lane.values()):raise ValueError('fivewords/cohort/lane source bound')
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
                        col=service.column(layer,st,sector,kind in ('KW','VW'),clock+link+10000)
                        commandcount[st]+=1
                        ready=max(ready,owned(st,g,col+25000+3000+12000+link));identities.append((st,pc,sector))
                if kind=='V' and base%8192==8176:ready=max(ready,prefix)
                heapq.heappush(events,(ready,0,index,(g,words,identities)));index+=1
                continue
            next_request=release if credit[g] and globalcredit else None
        else:next_request=None
        choices=[events[0][0]] if events else []
        if next_request is not None:choices.append(next_request)
        if not choices:raise ValueError('finite credit deadlock')
        clock=max(clock,min(choices))
    return dict(end_ps=latest,fill_end_ps=max(fill)+period,cohorts=len(batches),
        reservation_sha256=digest.hexdigest(),command_count_per_stack=commandcount,
        owned_data_and_grant_count_per_stack=ownedcount,peak_live_cohorts=peak_live,
        peak_words_per_group_lane_pool=peak_pool,assembly_group_lane_pools=56,assembly_slots_per_pool=80,
        global_assembly_slots=4480,all_reverse_grants_reserved=True,physical_or_payload_qualification=False)

def build():
    prev=json.loads(PREV.read_text());parent=prev['parent']
    for path,digest in prev['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('source changed: '+path)
    native=(ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv').read_text()
    for anchor in ('cyc+13+2+10','last_col+2','col_bg[bg]+3','last_act+3','act_bg[bg]+4','faw[0]+15','cyc+29+17','cyc+350','next_ref+3900','last_wr+7+2+((wr_bg==bg)?7:5)','last_rd+10'):
        if anchor not in native:raise ValueError('native deadline anchor changed: '+anchor)
    fill_counts=[sum(n for tile,n in enumerate(fill_destinations()) if tile%7==lane) for lane in range(7)]
    oldfill=Fraction(str(prev['calendar']['sum_port_reservation_s']))
    oldtotal=Fraction(str(prev['calendar']['finite_witness_if_non_layer_cost_exposed_s']))
    overhead=oldtotal-oldfill;budget=Fraction(1,3000)
    fill_perfect=Fraction(sum(fill_destinations())*36,1200000000)
    min_preserved=math.ceil(fill_perfect/(budget-overhead))
    if min_preserved!=7:raise ValueError('one successor dimension changed')
    rest_ps=(Fraction(3338-451)+Fraction(str(prev['calendar']['layer_allreduce_priced_stream_equivalent_cycles'])))*Fraction(2500,3)
    extra_ps=Fraction(str(prev['calendar']['whole_token_extra_compute_and_exchange_s']))*10**12
    mandatory_first_payload_ps=2*Fraction(39*2500,3)+10000+21000+25000+3000+12000+4*Fraction(2500,3)
    mandatory_transport_start_visibility_ps=mandatory_first_payload_ps+Fraction(2500,3)
    suffix_ps=rest_ps+extra_ps
    minimum_full_composition_fill_integer=math.ceil(fill_perfect/(budget-(36*mandatory_transport_start_visibility_ps+suffix_ps)/10**12))
    t=Fraction(0);compute=Fraction(0);windows=[Fraction(0)]*2;rows=[];service=PCService()
    for layer in range(36):
        window=layer%2;begin=max(t,windows[window]);prefix_begin=compute;prefix_end=compute+Fraction(451*2500,3)
        f=ready_layer_calendar(layer,begin,prefix_end,service);t=f.pop('end_ps');ready=f.pop('fill_end_ps')
        attention=max(ready,prefix_end);compute=attention+rest_ps;windows[window]=max(compute,t)
        rows.append(dict(layer=layer,window=window,begin_ps=float(begin),prefix_begin_ps=float(prefix_begin),prefix_ready_ps=float(prefix_end),
            fill_ready_ps=float(ready),all_grants_ps=float(t),attention_begin_ps=float(attention),compute_done_ps=float(compute),**f))
    prior_cells=prev['cells'];cell_src=json.loads((ROOT/'results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json').read_text())['cells']
    ff=cell_src['ASR_area_um2']+cell_src['INV_area_um2'];a=cell_src['AND3_area_um2'];inv=cell_src['INV_area_um2'];buf=cell_src['BUF_area_um2']
    # Added beyond8/4/6: one1048bit fill root, actual pending match/mux,
    #cache-valid/skip/sequence/refill state and registered eligibility tree.
    ff_counts=dict(fill_root=1048,pending_key_comparison_holds=128*64*17,
        lookahead_valid_skip_sequence=128*16*(1+5+32),lookahead_refill_controls=128*(6+5+1+7),
        eligibility_four_register_levels=128*(16+8+4+2)*(64+5+1),
        shared_command_final_revalidation=16*(339+32+1),
        refresh_priority_and_cache_generation=128*(32+64+1),
        request_free_slot_generation_order=128*64*(1+32+6),request_order_head_tail=128*12,
        extra_lane_partitioned_assembly_words=384*787,
        assembly_selection_metadata_pipeline=56*(80+40+20+10)*(7+64+1),
        assembly_bank_data_pipeline=56*2*787,assembly_lane_data_pipeline=7*2*787,
        gross_native_PC_bank_and_held_state=128*(8040+471+471+472+2+19+19+64))
    replicas=dict(fill_root=1,pending_key_comparison_holds=128,lookahead_valid_skip_sequence=128,
        lookahead_refill_controls=128,eligibility_four_register_levels=128,
        shared_command_final_revalidation=16,refresh_priority_and_cache_generation=128,
        request_free_slot_generation_order=128,request_order_head_tail=128,gross_native_PC_bank_and_held_state=128,
        extra_lane_partitioned_assembly_words=8,assembly_selection_metadata_pipeline=56,
        assembly_bank_data_pipeline=56,assembly_lane_data_pipeline=7)
    for name,n in ff_counts.items():
        if n%replicas[name]:raise ValueError('exact collector replica partition: '+name)
    collectors=sum(2*replicas[k]*tree_count(n//replicas[k],8)['nodes'] for k,n in ff_counts.items() if k!='extra_lane_partitioned_assembly_words')
    new_assembly_collectors=2*56*tree_count(80*787,8)['nodes']
    assembly_collector_delta=new_assembly_collectors-prior_cells['assembly_8_group_clock_reset_buffers']
    collectors+=assembly_collector_delta
    pending_mux_bits=128*63*471;cache_mux_bits=128*15*472
    # Existing predecessor already prices15-way whole-record cache selection.
    # Only15 additional bank-register selectors versus one native evaluator.
    bank_mux_bits=128*15*31*(19+3*64)
    eligibility_comparison_bits=128*(16*8+15)*64
    pending_eq_bits=128*64*17;hazard_eq_bits=128*16*15*34
    assembly_read_mux_bits=56*79*787+7*7*1048
    assembly_extra_quarter_mux_bits=384*4*(128+16)
    assembly_ready_comparison_bits=56*79*32
    selection_area=(pending_mux_bits+bank_mux_bits+assembly_read_mux_bits+assembly_extra_quarter_mux_bits)*(3*a+2*inv)+(pending_eq_bits+hazard_eq_bits+eligibility_comparison_bits+assembly_ready_comparison_bits)*(3*a+5*inv)
    old_fanout=prior_cells['fill_fanout_buffers_total'];new_fanout=sum(1048*tree_count(sum(tile%7==lane for tile in range(1536)),8)['nodes'] for lane in range(7))
    increment=(sum(ff_counts.values())*ff+collectors*buf+selection_area+(new_fanout-old_fanout)*buf)/1e6
    total=float((max(t,compute)+extra_ps)/10**12)
    columns=service.count['RD']+service.count['WR'];maintenance=sum(service.count[k] for k in ('PRE','ACT','PREALL','REF'))
    return dict(schema='qrom-one-coordinated-PC-and-seven-fill-successor.v1',parent=parent,
        status='G0_FAIL_PHYSICAL_PHY_POLICY_OPEN_CONDITIONAL_SERVICE_RECORDED',
        predecessor_sha256=hashlib.sha256(PREV.read_bytes()).hexdigest(),source_sha256=prev['source_sha256'],
        dimensioning=dict(target_s=float(budget),preserved_order_overhead_s=float(overhead),
            minimum_fill_integer_under_preserved_overhead=min_preserved,
            minimum_fill_integer_with_mandatory_cold_lease_pipeline_and_suffix=minimum_full_composition_fill_integer,
            mandatory_first_payload_ps=float(mandatory_first_payload_ps),
            mandatory_layer_visibility_start_ps=float(mandatory_transport_start_visibility_ps),
            source_cold_lease_six_fill_lower_s=float((Fraction(sum(fill_destinations())*36*2500,18)+36*mandatory_transport_start_visibility_ps+suffix_ps)/10**12),
            lower_bound_scope='Proposed cold-per-layer service-lease calendar: nextprefetch starts after previousservice drains; requestlink/REQ/coldRAMcapture+foureligibility/read25/raw3/owner12/response39/fourassemblyselectors/visible fence retained. No assumed earlycrosslayer producer/descriptor ownership. Euclid actualearlyrelease may change this policy and require rederivation; not universal architectural6lane impossibility.',
            necessary_return_groups_with_nonlayer_cost=math.ceil(2*37711872/32/(float(budget)-float(extra_ps/10**12))/1000000000),
            per_PC_II5_stack_payload_ceiling_Bps=32*32*1000000000/5,
            service_increase_mathematically_necessary_from_counts=False,successor_fill_counts_per_layer=fill_counts,
            seven_fill_port_lower_s=max(fill_counts)*36/1200000000,
            six_universal_infeasibility_proven=False,six_ideal_composition_s=prev['calendar']['total_if_non_layer_compute_exchange_exposed_s'],
            reason='ceil(total_fill_beats/(streamHz*(budget-retained_FIFO_overhead)))=7. This preserves6 predecessor known overhead; not universal proof6cannotfit with another legal ordering.',
            aggregate_command_integer_lower_including_this_maintenance=math.ceil((columns+maintenance)/4/((budget-Fraction(str(prev['calendar']['whole_token_extra_compute_and_exchange_s'])))*1000000000)),
            instruction='One8/4/7 evaluated, no sweep. Maintenance demands/count bound and actual finite reservations reported; no adopted PHY bandwidth.'),
        configuration=dict(return_groups_per_stack=8,PCs_per_group=4,column_paths_per_stack=4,global_fill_lanes=7,
            tiles=1536,tiles_per_lane=[sum(t%7==lane for t in range(1536)) for lane in range(7)],
            pending_entries_per_PC=64,lookahead_whole_records_per_PC=16,request_return_RAMs_replicated=0,
            context_RAMs_per_stack=32,context_RAMs_replicated=0,group_burst_credits=16,stack_burst_credits=128,
            global_matched_cohorts=128,central_assembly_entries=4480,assembly_group_lane_pools=56,assembly_slots_per_pool=80,flight_output_credits_per_group=32,
            lookup_latency_edges=12,context_capture_edge=1,read_provider_due_edges=25,cold_lookahead_read_capture_edges=17,
            eligibility_register_edges=4,per_PC_command_accept_II_lower_edges=5,
            raw_response_stage_and_RAM_capture_edges=3,
            request_paths_per_stack=1,source_tag_namespace_copied=False),
        controller=dict(plan='One1R1W request RAM/PC retained. Capture at most16 whole472bit records into indexed valid cache at1read/edge; holes/sequence stay immutable, oldest bypass<=16, refill at1read/edge. No per-selection wholeRAM SWAP. Register16candidate eligibility tree atfour levels, revalidate epoch/deadline/alias/credit at final339bit command accept; serial oldfreeze/scan and singlepending state are replaced, not given freeII1.',
            pending='Reserve shared64combined pending+raw+held output credits before RD. Exact tag/beat/sector/producer/transport, source25edge due; associative pending match and471bit mux priced. Stage response through one1R1W return RAM write/edge and held macro read/capture; credit releases on owned consume. Out-of-order arrivals do not alter identity; duplicates/refused early returns cannot mutate state.',
            hazards='32banks/sourcePC, sharedgroupowner/remaining_PC/live_tags and allocation/retirement unchanged. Read/write aliases in16lookahead compare against older entries and pending sectors; four finalstack command selectors must revalidate transient deadlines and cache generation. Write data slot reservation precedes WR; current4slot source write protection/ACK joins remain mandatory.',
            command_counts=dict(service.count),commands_per_shared_path=[[len(v) for v in paths] for paths in service.bus],
            reserved_same_path_collision_free=True,command_event_digest=service.digest.hexdigest(),
            max_lazy_refresh_lateness_edges=service.max_refresh_lateness,
            refresh_scope='Address-only source-native deadlines and refresh debt explicitly charged. Idle-PC refresh placement/strictdeadline/sourceeligible-cache/provider/SSFF remain admission gates; deferred debt is never sustainablePHYproof.',
            original_single_pending_read_II28_removed_only_in_candidate=True,
            native_deadlines_retained=True,actual_source_controller_replacement_instantiated=False),
        calendar=dict(rows=rows,full36_sequential=True,all1536_destinations=True,
            composed_conditional_s=total,meets_3k_in_conditional_reservation=total<=float(budget),
            margin_to_3k_s=float(budget)-total,extra_nonlayer_compute_s=float(extra_ps/10**12),
            current_V_requires_actual_prefix=True,source_policy=prev['demand'],persistent_state_erased=False,
            actual_demand_journal_bound=False,proved_overlap_s=0,adopted_rate=None,
            scope='ONE address-only fourcommand/sourcebank-deadline/eightreturn/sevenfill reservation incl maintenance and ready selection among at most128cohorts in56x80 group/lane pools. Original FIFO draft failures retained; no dimension sweep. State/payload, actualcache/revalidation phases, protection, sourceCDC/readiness and PHY sustain unqualified.'),
        cells=dict(successor_delta_FF=ff_counts,replicas=replicas,collector_buffers=collectors,
            total_56_pool_assembly_collectors=new_assembly_collectors,
            replaced_identified_8_pool_collectors=prior_cells['assembly_8_group_clock_reset_buffers'],
            assembly_collector_delta=assembly_collector_delta,
            pending_mux_bits=pending_mux_bits,retained_cache_mux_bits=cache_mux_bits,cache_mux_increment_bits=0,
            extra_bank_register_selection_bits=bank_mux_bits,eligibility_comparison_bits=eligibility_comparison_bits,
            pending_equality_bits=pending_eq_bits,
            read_write_alias_equality_bits=hazard_eq_bits,assembly_read_mux_bits=assembly_read_mux_bits,assembly_ready_comparison_bits=assembly_ready_comparison_bits,
            assembly_extra_quarter_mux_bits=assembly_extra_quarter_mux_bits,
            delta_known_mm2=increment,total_known_service_mm2=prev['slot']['known_service_mm2']+increment,
            total_fill_distribution_buffers=new_fanout,delta_fill_distribution_buffers=new_fanout-old_fanout,
            service_stream_clocks_Hz=[1000000000,1200000000],clock_reset_complete=False,
            existing64pending471bit_storage_charged_once=True,all_existing_macros_charged_once=True,
            source_native_state_gross_charge_reason='No namedMaxwell nativePCbank/held-state baseline receipt. Charge9558FF/PC plus actualcollector rather than grant baselinecredit. Existing perPC request/return/context macros,cache16 and pending64 storage remain chargedonce. Gross nativeFF source regs include bank8040,held/out/response and pointer/control reservations.',
            native_state_baseline_credit_mm2=0),
        physical=dict(named_legal_channel_owner='Ampere',uniform_corridor_widening_selected=False,
            seven_fill_bits=7*1048,shared_control_bits=637,required_fill_plus_control_tracks=7*1048+637,
            predecessor_reserved_tracks=1360,new_named_channels_allocated=False,
            additional_service_response_reverse_replicas=0,command_bits_per_stack=4*339,
            global_boundary_bits=prev['routing']['global_boundary_bits']+1048,
            required_sustained_PHY_Bps_per_stack=prev['PHY']['required_sustained_Bps_per_stack'],
            actual_sustained_PHY_Bps=None,extra_PHY_replicas_selected=0,
            parent_baseline_mm2=prev['slot']['baseline_array_mm2'],
            conditional_remaining_mm2=prev['slot']['conditional_remaining_before_new_routes_PG_unknowns_mm2']-increment,
            source_SS_macro_capture_budget_ps=prev['source_gates']['capture_FF_setup_plus_route_budget_ps'],
            SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,SSFF_proven=False),
        admission=dict(hardware=False,new_RTL=False,new_PnR=False,production_qualified=False,
            blockers=['Ampere namedlegalchannel/PHY/clock-slot allocation','Actual sustainedPHY+source64pending/cache/revalidation/strictrefresh service','Euclid actual producer/demand/policy/visibility/drain events']),
        implementation_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('tools/uarch_model_qwen_kv_successor.py','tools/uarch_model_qwen_kv_bank_groups.py')})

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);args=ap.parse_args()
    with args.result.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')
