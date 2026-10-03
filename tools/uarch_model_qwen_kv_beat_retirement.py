#!/usr/bin/env python3
"""One causal per-word visibility/per-beat grant policy, unchanged8/4/7 ports.
No capacity sweep or hardware. Actual producer policy/physical admission open.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import gzip
import heapq
import json
import math
from pathlib import Path
import uarch_model_qwen_kv_credit_allocator as A
from uarch_model_qwen_parent_context import tree_count
ROOT=A.ROOT
OUT=ROOT/'results/uarch/qwen_rom_kv_beat_retirement_20261003'
P=2500 # one stream edge in thirds of a ps
LINK=39*P

def fragments(layer,stack,sector):
    result=[]
    for off in (0,16):
        a=(sector//4*4+stack)*128+sector%4*32+off
        if a<75497472:
            word=a//16;dim=word%128;t=word//128%512;head=word//65536%2
            owner=word//131072;tile=t%48*32+dim//4;row=t//48*2+head;quarter=dim%4
        else:
            a-=75497472;dim=a%128;position=a//128%8192;head=a//1048576%2
            owner=a//2097152;tile=dim//16*128+position%512//4;row=22+position//512*2+head;quarter=position%4
        if owner!=layer:raise ValueError('source home/layer')
        result.append(((tile,row),quarter))
    return result

class Retirement:
    """Functional identity/visibility quarantine, not a payload provider.
    Invalid events never mutate; tagged generations cross CDC with payload.
    Captured mutable storage can release before tag/word lifetime completes.
    """
    def __init__(self):self.live={};self.words={};self.pending=0
    def allocate(self,tag,epoch,beat_words):
        if tag in self.live:raise ValueError('live/quarantined tag')
        self.live[tag]={'epoch':epoch,'deps':dict(beat_words),'captured':set(),'granted':set()};self.pending+=len(beat_words)
    def capture(self,tag,epoch,beat):
        t=self.live.get(tag)
        if t is None or epoch!=t['epoch'] or beat not in t['deps'] or beat in t['captured']:raise ValueError('identity/epoch/duplicate capture')
        t['captured'].add(beat);self.pending-=1
    def visible(self,word,epoch):self.words[word]=epoch
    def grant(self,tag,epoch,beat):
        t=self.live.get(tag)
        if t is None or epoch!=t['epoch'] or beat not in t['captured'] or beat in t['granted']:raise ValueError('identity/epoch/duplicate grant')
        if any(self.words.get(w)!=epoch for w in t['deps'][beat]):raise ValueError('uncaptured dependent word visibility')
        t['granted'].add(beat)
    def release(self,tag,epoch,readers_drained):
        t=self.live.get(tag)
        if t is None or epoch!=t['epoch'] or readers_drained is not True or t['granted']!=set(t['deps']):raise ValueError('tag quarantine/drain')
        del self.live[tag]

def calendar(layer,begin_ps,prefix_ps,service,causal_journal=None):
    begin=int(F(begin_ps)*3);prefix=int(F(prefix_ps)*3)
    cursors=[A.GroupCursor(layer,g) for g in range(8)]
    credit=[16]*8;globalcredit=128;pending=Counter();writing=Counter();pools=Counter()
    headers={};events=[];eventid=0;clock=begin;request=begin;rr=0;index=0;latest=begin
    fill=[begin]*7;occupied=[[set() for _ in range(8)] for _ in range(4)]
    commandcount=[0]*4;ownedcount=[0]*4;peakpending=peakwrite=peaklive=peakpool=0
    lease=Counter();rawlease=0;extra_ack_wait=0;barrier_saved=0;digest=hashlib.sha256()
    total_words=total_fragments=forwarded=0
    def put(at,kind,data):
        nonlocal eventid
        heapq.heappush(events,(at,eventid,kind,data));eventid+=1
    def owned(st,g,ready):
        edge=(ready+2999)//3000;used=occupied[st][g]
        while edge in used:edge+=1
        used.add(edge);ownedcount[st]+=1
        return (edge+1)*3000
    def counts(head):
        kind,base,n=head;answer=Counter()
        for st in range(4):
            count=n-4 if kind=='V' and st==3 and base%8192==8176 else n
            if kind=='VW' and st!=3:count=0
            for b in range(count):answer[st,A.pc_of(base+b)]+=1
        return answer
    def available(head):
        return all(pending[k]+v<=64 and (head[0] not in ('KW','VW') or writing[k]+v<=4) for k,v in counts(head).items())
    def schedule_grant(ci,key):
        h=headers[ci];r=h['beats'][key]
        if r['scheduled'] or r['copied'] is None:return
        if any(w not in h['visible'] for w,q in r['pieces']):return
        vis=max([r['copied']]+[h['visible'][w] for w,q in r['pieces']])
        r['scheduled']=True
        # Immutable beat identity reconstructed from live burst context.
        # DATA/GRANT share exactly the original one service port/group/stack.
        end=owned(key[0],h['g'],vis+LINK+6000)
        put(end,'grant',(ci,key,vis));r['grant']=end
    while any(c.head is not None for c in cursors) or events:
        while events and events[0][0]<=clock:
            at,_,typ,data=heapq.heappop(events)
            ci=data[0];h=headers[ci];g=h['g']
            if typ=='copy':
                _,key=data;r=h['beats'][key]
                if r['copied'] is not None:raise ValueError('duplicate inflight beat')
                r['copied']=at
                if not r['forward']:
                    pending[key[0],r['pc']]-=1;rawlease+=at-h['allocated']
                for w,q in r['pieces']:
                    if h['masks'][w]&(1<<q):raise ValueError('duplicate quarter')
                    h['masks'][w]|=1<<q
                    if h['masks'][w]==15:
                        lane=w[0]%7
                        fill[lane]=max(fill[lane],at+5*P)+P
                        vis=fill[lane]+P;h['visible'][w]=vis
                        put(vis,'word',(ci,w))
                        for bk in h['word_beats'][w]:schedule_grant(ci,bk)
                schedule_grant(ci,key)
            elif typ=='word':
                _,w=data;pools[g,w[0]%7]-=1
            elif typ=='grant':
                _,key,vis=data;r=h['beats'][key]
                if r['forward'] or r['granted']:raise ValueError('grant ownership')
                r['granted']=True;h['remaining']-=1
                extra_ack_wait+=at-vis-LINK-6000
                if r['write']:writing[key[0],r['pc']]-=1
                digest.update(f'{ci}:{key}:{r["copied"]}:{vis}:{at};'.encode())
                if h['remaining']==0:
                    if not all(r['forward'] or r['granted'] for r in h['beats'].values()):raise ValueError('lost beat')
                    credit[g]+=1;globalcredit+=1;latest=max(latest,at)
                    lease[g]+=at-h['allocated']
                    # Witness difference from holding early raw copies until finalgrant.
                    barrier_saved+=sum(at-r['copied'] for r in h['beats'].values() if not r['forward'])
                    if causal_journal:
                        recipe=[[list(bk),r['pc'],r['copied'],r.get('grant'),[[list(w),q] for w,q in r['pieces']]] for bk,r in sorted(h['beats'].items())]
                        causal_journal.write(json.dumps(dict(layer=layer,cohort=ci,group=g,kind=h['kind'],base=h['base'],length=h['n'],allocated_third_ps=h['allocated'],retired_third_ps=at,
                            exact_dependencies_and_events_sha256=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest(),
                            members=len(recipe),words=len(h['masks']),all_quarter_masks_complete=all(m==15 for m in h['masks'].values()),
                            all_grants_consumed=True,copy_readers_drained_at_visible=True,actual_production_journal=False))+'\n')
                    del headers[ci]
            else:raise ValueError('event type')
        active=[g for g,c in enumerate(cursors) if c.head is not None]
        eligible=[g for g in active if credit[g] and globalcredit and available(cursors[g].head) and max(request,prefix if cursors[g].head[0] in ('KW','VW') else begin)<=clock]
        if eligible:
            g=A.select_group(eligible,rr);rr=(g+1)%8;kind,base,n=cursors[g].head;write=kind in ('KW','VW')
            clock=(clock+2999)//3000*3000;request=clock+3000
            words,_=A.cohort_words(layer,base,n) if not write else (set(),[])
            by_lane=Counter(w[0]%7 for w in words)
            if any(v>5 for v in by_lane.values()):raise ValueError('source five words')
            for k,v in counts(cursors[g].head).items():
                pending[k]+=v;peakpending=max(peakpending,pending[k])
                if write:writing[k]+=v;peakwrite=max(peakwrite,writing[k])
            credit[g]-=1;globalcredit-=1;peaklive=max(peaklive,128-globalcredit)
            for w in words:pools[g,w[0]%7]+=1;peakpool=max(peakpool,pools[g,w[0]%7])
            if peakpool>80:raise ValueError('finite80 words')
            h={'kind':kind,'base':base,'n':n,'g':g,'allocated':clock,'masks':dict.fromkeys(words,0),'visible':{},'word_beats':{w:[] for w in words},'beats':{},'remaining':0};headers[index]=h
            total_words+=len(words)
            for st in range(4):
                if kind=='VW' and st!=3:continue
                for b in range(n):
                    sector=base+b;pc=A.pc_of(sector);key=st,b
                    fwd=kind=='V' and st==3 and base%8192==8176 and b>=n-4
                    pieces=fragments(layer,st,sector) if not write else []
                    r=dict(pc=pc,write=write,forward=fwd,pieces=pieces,copied=None,scheduled=fwd,granted=False);h['beats'][key]=r
                    for w,q in pieces:h['word_beats'][w].append(key)
                    total_fragments+=len(pieces)
                    if fwd:
                        forwarded+=1;copy=(max(prefix,clock)+P-1)//P*P+P
                    else:
                        h['remaining']+=1
                        col=int(service.column(layer,st,sector,write,F(clock+9000+LINK+30000,3))*3);commandcount[st]+=1
                        # Retain provider25, raw3, validation2, owner12, response39.
                        # Existing32flight ring reserves a DATA departure before
                        #context read, at most12 flight entries; unused DATA
                        #slots are never overwritten by subsequently ready grants.
                        tx=owned(st,g,col+(25+3+2+12)*3000)
                        copy=(tx+LINK+P-1)//P*P+P
                    put(copy,'copy',(index,key))
            if sum(len(v) for v in h['word_beats'].values())!=4*len(words):raise ValueError('four actual quarters/word')
            index+=1;cursors[g].advance();continue
        if not events and not active:break
        release=[max(request,prefix if cursors[g].head[0] in ('KW','VW') else begin) for g in active if credit[g] and globalcredit and available(cursors[g].head)]
        choices=([events[0][0]] if events else [])+release
        if not choices:raise ValueError('finite lifecycle deadlock')
        clock=max(clock,min(choices))
    if headers or any(pending.values()) or any(writing.values()) or any(pools.values()) or globalcredit!=128:raise ValueError('undrained state')
    return dict(end_ps=F(latest,3),fill_end_ps=F(max(fill)+P,3),cohorts=index,command_count_per_stack=commandcount,
        owned_DATA_GRANT_count_per_stack=ownedcount,reservation_sha256=digest.hexdigest(),peak_live_cohorts=peaklive,
        peak_pending_per_PC=peakpending,peak_write_per_PC=peakwrite,peak_words_per_pool=peakpool,
        filled_words=total_words,captured_quarters=total_fragments,source_forwarded_32B_beats=forwarded,
        group_lease_work_ps={str(k):float(F(v,3)) for k,v in lease.items()},raw_lease_work_ps=float(F(rawlease,3)),
        removed_raw_wait_to_final_grant_ps=float(F(barrier_saved,3)),queued_reverse_wait_ps=float(F(extra_ack_wait,3)),
        all_tags_and_epochs_drained=True,actual_producer_bound=False)

def price(old):
    cell=json.loads((ROOT/'results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json').read_text())['cells']
    ff=cell['ASR_area_um2']+cell['INV_area_um2'];a=cell['AND3_area_um2'];inv=cell['INV_area_um2'];buf=cell['BUF_area_um2']
    families={
        'beat_dependency_capture_grant_mask':(128,64*(2*7+2+3+1+1+1)),
        'word_quarter_owner_visibility_generation':(56,80*(4+4*(7+2+4)+32+2-36)),
        'two_quarter_deposit_pipeline_per_stack_group':(32,2*(128+16+7+32+4)),
        'grant_dispatch_two_registered_levels':(32,(16+8)*(7+4+64+1)),
        'return_identity_two_validators':(128,151+64+34+21+8),
        'reverse_identity_two_validators':(32,404+192+12+5+34+64+32+16+9),
        'joint_live_tags_epoch_PC_hazards':(4,2*(12+32+3+8)+192+32+16)}
    FF={k:r*n for k,(r,n) in families.items()};collectors=sum(2*r*tree_count(n,8)['nodes'] for r,n in families.values())
    mux={'second_quarter_write_selector':56*80*(128+16),
         'perbeat_two_word_reference_selection':32*15*(14+7+32),
         'perword_four_beat_ref_selection':56*80*3*(7+2+4),
         'grant16cohort16beat_selection':32*(15+15)*(192+12+5+34+64+32+16)}
    eq={'deposit_duplicate':56*80*4,'perbeat_immutable_reverse':32*(192+12+5+34+64+32+16),'selected_return_identity':128*151,'namespace_atomic_epoch':4*(192+32+12)}
    cmpbits=128*(64+34)+32*(64+6)+4*(6+12)
    ampere=json.loads((OUT/'inputs/Ampere-peer-contract-r1.json').read_text())['gross_control_price']
    delta=(sum(FF.values())*ff+sum(mux.values())*(3*a+2*inv)+sum(eq.values())*(3*a+5*inv)+cmpbits*(5*a+5*inv)+collectors*buf)/1e6+ampere['known_mm2']
    return dict(Ampere_gross_control=ampere,Ampere_ready_controls_charged_once=True,FF=FF,replicas={k:r for k,(r,n) in families.items()},mux_bits=mux,equality_bits=eq,unsigned_compare_bits=cmpbits,collectors=collectors+ampere['collector_buffers'],
        incremental_known_mm2=delta,total_known_service_mm2=old['cells']['total_known_service_mm2']+delta,
        conditional_remaining_mm2=old['physical']['conditional_remaining_mm2']-delta,
        existing_macros_or_fill_root_recharged=False,mutable_storage_protection_area_mm2=None,
        loaded_route_CTS_reset_CDC_hold_PG_area_mm2=None,
        quarter_deposit_scope='Two16B fragments per accepted32B beat, perstack/group, disjoint quarter masks in existing FF assembly. Second selector and pipeline priced; not an unpriced dualport macro.',
        state_protection_scope='Identity/epoch/address/duplicate checks gross charged. Actual mutable storage fault protection realization remains unbound; no ROM ECC added.')

def bounds(rows,old):
    trace=json.loads((ROOT/'results/uarch/qwen_rom_kv_stall_attribution_20261002/model-r3.json').read_text())
    port=trace['lower_bounds'];extra=F(3164*2500,3)/10**12
    # Universal optimistic per-beat causal quarantine afterallocation:
    # arb3+REQ39stream+REQ10+provider25+raw3+validate2+lookup12+
    # DATA1+response39stream+capture1stream+select4stream+fill1stream+
    # visibility1stream+reverse39stream+validate2+GRANT1. Relax bank/cold
    #queueing, throughput arbitration and absent productionrelease.
    minhold=F((3+10+25+3+2+12+1+2+1)*3000+(3*39+1+5+1+1)*P,3)/10**12
    oldwork=sum(max(r['diagnostic']['measured_group_lease_work_ps'].values()) for r in trace['rows'])/1e12
    newwork=sum(max(r['group_lease_work_ps'].values()) for r in rows)/1e12
    globalwork=sum(sum(r['group_lease_work_ps'].values()) for r in rows)/1e12
    causalwork=sum(max(r['group_issues'].values()) for r in old['calendar']['rows'])*float(minhold)
    targets={}
    for rate in (3000,6222,8460):
        budget=F(1,rate)-extra
        targets[str(rate)]=dict(period_us=1e6/rate,causal_group_credit_lower=math.ceil(causalwork/float(budget)),
            recorded_old_lifetime_group_credit_necessary=math.ceil(oldwork/float(budget)),
            observed_alternative_lifetime_group_credit_necessary=math.ceil(newwork/float(budget)),
            observed_alternative_lifetime_global_credit_necessary=math.ceil(globalwork/float(budget)),
            credit_only_can_overcome_port_floor=max(port['fill_demand_port_s'],port['owner_DATA_plus_GRANT_port_s'],port['column_payload_only_port_s'])<=float(budget),
            fill_lane_necessary=math.ceil(port['fill_demand_port_s']*7/float(budget)),
            return_group_necessary=math.ceil(port['owner_DATA_plus_GRANT_port_s']*8/float(budget)),
            column_path_necessary=math.ceil(port['column_payload_only_port_s']*4/float(budget)),
            port_replica_scope='Necessary equivalent capacity bounds only, not selected replicas, legal channels or sustainable PHY.',
            sustained_payload_GBps_per_stack_necessary=32736*32*36/float(budget)/1e9)
    return dict(source_port_lower_bounds=port,optimistic_perbeat_causal_quarantine_s=float(minhold),targets=targets,
        credit_scope='Causal group bound relaxes cold/bank/refresh/serialization/fanout. Recorded old and observed alternative lease-area bounds assume their lifetimes and are not universal sizing prescriptions. No capacity sweep.',
        historical_rate_reconciliation='6222/8460 historical8K rows did not qualify this source151MB/token cold delivery. More credits or faster root compute cannot remove current transport port/traffic floor. Actual selected resident/reuse policy may avoid transfers, but requires source-owned producer state/visibility and observed release journal; no speculative subtraction.')

def build(journal=None,causal_journal=None):
    path=ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json';old=json.loads(path.read_text())
    for p,h in old['source_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('source pin '+p)
    rest=F(3338-451)*F(2500,3)+F(18176,100)*F(2500,3);extra=F(3164*2500,3)
    t=compute=F(0);windows=[F(0)]*2;service=A.S.PCService();rows=[]
    for layer in range(36):
        begin=max(t,windows[layer%2]);prefix=compute+F(451*2500,3)
        row=calendar(layer,begin,prefix,service,causal_journal);t=row.pop('end_ps');ready=row.pop('fill_end_ps');compute=max(prefix,ready)+rest;windows[layer%2]=max(t,compute)
        row=dict(layer=layer,begin_ps=float(begin),prefix_ps=float(prefix),fill_ready_ps=float(ready),all_grants_ps=float(t),compute_done_ps=float(compute),**row);rows.append(row)
        if journal:
            with journal.open('a') as f:f.write(json.dumps(row)+'\n')
    total=float((max(t,compute)+extra)/10**12);gain=old['calendar']['composed_conditional_s']/total-1
    pricing=price(old)
    return dict(schema='qrom-one-source-causal-beat-retirement.v1',source_sha256=old['source_sha256'],predecessor_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        rejected17_sha256=hashlib.sha256((ROOT/'results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json').read_bytes()).hexdigest(),
        configuration=dict(returns_per_stack=8,columns_per_stack=4,global_fills=7,group_credits=16,global_credits=128,pending_per_PC=64,words_per_pool=80,assembly_pools=56,context_banks_per_stack=32,context_depth128=True,flight_output_per_group=32,lookup_edges=12,provider_edges=25,raw_capture_edges=3,word_predicate_edges=1,selection_edges=4,return_validation_edges=2,reverse_validation_edges=2,service_Hz=1e9,stream_Hz=1.2e9,serial_Hz=.9e9),
        calendar=dict(rows=rows,full36=True,total_conditional_s=total,predecessor_conditional_s=old['calendar']['composed_conditional_s'],gain_fraction=gain,meets3k=total<=1/3000,clears1percent=gain>=.01,production_qualified=False,actual_rate=None,
            scope='Ampere0fba48658 ONE ready-word/perbeat ACK policy, retained source8191 tail/Vforward and cold-perlayer lease. No full-cohort word barrier. Raw releases on captured downstream copy; words release only after visibility; cohort/tag quarantine until all matching grants/readers drain. Source producer journal remains unbound.'),
        cells=pricing,bounds=bounds(rows,old),controller=dict(command_counts=dict(service.count),command_sha256=service.digest.hexdigest(),max_lazy_refresh_lateness_edges=service.max_refresh_lateness,strict_refresh_qualified=False),
        unified_debits=dict(existing_KV_HBM_replaced_once=True,baseline_layer_cycles=3338,prefix_cycles=451,AR_stream_cycles=181.76,nonlayer_cycles=3164,conditional_bytes_per_token=32736*32*4*36,compulsory_refill_assumed=False,compute_doublecharged=False),
        route=dict(fill_control_bits=7973,source_capacity_tracks=1360,deficit_tracks=6613,additional_local_quarter_bundle_bits=128+16+7+32+4,extra_collector_wire_um=pricing['collectors']*32,named_channels_allocated=False,loaded_area_mm2=None,SSFF_CDC_closed=False),
        admission=dict(model_only=True,hardware=False,adopted=False,actual_PHY_Bps=None,production_journal_bound=False,source379bit_and128capture_owned=False,mutable_protection_bound=False,
            blockers=['Finite target/gain result as recorded','Production state/release/reuse journal from Euclid liveL0','Ampere named legal channels/PHY/clock/CDC/hold','Mutable protection/Maxwell baseline debit and service slot','Strict refresh remains unqualified']),
        peer_input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'inputs').iterdir()},implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);ap.add_argument('--journal',type=Path);ap.add_argument('--causal-journal',type=Path);a=ap.parse_args()
    if a.journal:a.journal.open('x').close()
    with a.result.open('x') as f:
        if a.causal_journal:
            if a.causal_journal.exists():raise ValueError('preserve causal journal')
            with gzip.open(a.causal_journal,'wt') as cj:result=build(a.journal,cj)
        else:result=build(a.journal)
        json.dump(result,f,indent=2);f.write('\n')
