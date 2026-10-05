#!/usr/bin/env python3
"""One minimum joint KV bank-group/command/return/fill requirement screen.

No sweep, payload generation, source timing adoption, RTL or physical build.
Port ceilings, finite fixture gates and slot deficits are separate from actual
production demand and sustainable PHY bandwidth.
"""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import heapq
import json
import math
from pathlib import Path
import re
from uarch_model_qwen_parent_context import Pins, build as parent_model, tree_count
from uarch_model_qwen_kv_rate_risk import build as rate_risk

ROOT=Path(__file__).resolve().parents[1]

def pc_of(sector):
    if type(sector) is not int or not 0<=sector<703125000:raise ValueError('sector aperture')
    return ((sector>>2)^(sector>>7)^(sector>>12))&31

def group_of(sector):return pc_of(sector)//4

def burst_group(base,length):
    if not 1<=length<=16 or base%16+length>16:raise ValueError('one aligned16-sector block required')
    groups={group_of(base+b) for b in range(length)}
    if len(groups)!=1:raise ValueError('cross-group allocation')
    return groups.pop()

def ranges(layer,stack,user=0):
    """Source Homes/FP8 equations, selected8191 two-tail bypass/V forward.

    Each head is1MiB logical, striped128B across4stacks. K excludes its last
    two2048B tiles/head; current V row falls wholly atstack3. Closing K writes
    the last2048B tile/head. Read/write extents are not fabricated payload.
    """
    if not 0<=layer<36 or not 0<=stack<4 or not 0<=user<596:raise ValueError('finite selected home')
    prefix=user*1179648
    reads=[];writes=[]
    for head in range(2):
        k=prefix+(layer*2+head)*8192;v=k+589824
        reads.extend([(k,8160),(v,8192-(4 if stack==3 else 0))])
        writes.append((k+8176,16))
        if stack==3:writes.append((v+8188,4))
    if max(b+n for b,n in reads+writes)>703125000:raise ValueError('home exceeds provider')
    return reads,writes

def count_groups(intervals):
    groups=[0]*8;pcs=[0]*32;bursts=[0]*8
    for base,n in intervals:
        while n:
            length=min(n,16-base%16);g=burst_group(base,length);groups[g]+=length;bursts[g]+=1
            for b in range(length):pcs[pc_of(base+b)]+=1
            base+=length;n-=length
    return dict(groups=groups,PCs=pcs,bursts=bursts)

def fill_destinations():
    """Exact source tile/row64B fills; current V forwarding retains fill beat."""
    counts=[0]*1536
    for t in range(510):
        for head in range(2):
            for quad in range(32):counts[(t%48)*32+quad]+=1
    for block in range(16):
        for head in range(2):
            for dimtile in range(8):
                for quad in range(128):counts[dimtile*128+quad]+=1
    return counts

def cohort_words(layer,base,length=16):
    """Four stack-matched bursts reserve source tile/row word identities.

    V quarters cross stack boundaries; they must meet in the same destination
    assembly entry. K quarters are local pairs. One aligned cohort touches at
    most32 words, so128 cohorts need4096 global entries with no free alignment
    assumption. Payload remains caller-owned; this is address mapping only.
    """
    burst_group(base,length);words=set();by_stack=[]
    for stack in range(4):
        local=set()
        for sector in range(base,base+length):
            for offset in range(0,32,16):
                a=((sector//4)*4+stack)*128+(sector%4)*32+offset
                if a<75497472:
                    word=a//16;dim=word%128;t=(word//128)%512;head=(word//65536)%2
                    got_layer=word//131072;tile=(t%48)*32+dim//4;row=(t//48)*2+head
                else:
                    a-=75497472;dim=a%128;position=(a//128)%8192;head=(a//1048576)%2
                    got_layer=a//2097152;tile=(dim//16)*128+(position%512)//4
                    row=22+(position//512)*2+head
                if got_layer!=layer:raise ValueError('cohort owner/layer mismatch')
                local.add((tile,row))
        words.update(local);by_stack.append(local)
    if len(words)>32:raise ValueError('source assembly reservation bound')
    return words,by_stack

def finite_layer_calendar(layer,begin_ps,prefix_ready_ps):
    """Construct ONE conservative address-only finite reservation witness.

    Four matched stack members reserve <=32 central words before commands.
    Group16 burst slots and128 global cohorts are held until final reverse
    grant. Real data/state, PHY row/refresh service and CDC qualification are
    absent; fixed functional-model minimum delays are conditional lower costs.
    Full source lookup12 and39-stream-edge links are retained, never removed.
    """
    command=[[0]*4 for _ in range(4)];occupied=[[set() for _ in range(8)] for _ in range(4)]
    groups=[[begin_ps]*16 for _ in range(8)];global_slots=[begin_ps]*128
    fill=[begin_ps]*6;request=begin_ps;latest=begin_ps;digest=hashlib.sha256()
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
                        col=max(command[st][path],start+link+10000)
                        command[st][path]=col+ns;command_count[st]+=1
                        # Source CL12.5ns/RSP10ns minimum, earlycapture then
                        #full12edge lookup and39stream response route.
                        received=owned_slot(st,g,col+12500+10000+12000+link)
                        ready=max(ready,received);identities.append((st,pc,sector))
                if kind=='V' and base%8192==8176:ready=max(ready,prefix_ready_ps)
                for tile,row in sorted(words):
                    lane=tile%6;fill[lane]=max(fill[lane],ready+Fraction(2500,3))+Fraction(2500,3)
                visible=max([ready]+[fill[t%6]+Fraction(2500,3) for t,r in words])
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

class GroupLedger:
    """Finite protocol fixture:8 groups own4banks each; shared12tag namespace.

    One early bank capture atedge+1, output no earlier thanedge+12. Capture
    physically requires macroSS clk-q plus route and FF setup within one edge.
    This class cannot qualify actual SRAM timing or provide checkpoint state.
    """
    def __init__(self):
        self.tick=0;self.tags={};self.quarantine=set();self.bank={};self.flight=[]
        self.output=[[] for _ in range(8)];self.inflight=set();self.seen=set()
        self.reserved_pc=Counter();self.live_tags=0;self.grants={};self.completed_length={};self.tag_groups={}

    def allocate(self,tag,base,length):
        g=burst_group(base,length)
        if not 0<=tag<4096 or tag in self.tags or tag in self.quarantine:raise ValueError('shared live tag')
        if sum(group==g for group in self.tag_groups.values())>=16:raise ValueError('16group burst credits')
        beats={b:pc_of(base+b) for b in range(length)};needed=Counter(beats.values())
        if any(self.reserved_pc[p]+n>64 for p,n in needed.items()):raise ValueError('actual64-row return capacity')
        self.tags[tag]=dict(group=g,base=base,beats=beats,pending=set(beats),done=set(),remaining_PC=len(needed))
        self.reserved_pc.update(needed);self.live_tags+=1;self.grants[tag]=set();self.completed_length[tag]=length;self.tag_groups[tag]=g

    def grant(self,tag,beat):
        if tag not in self.grants or (tag,beat) not in self.seen or beat in self.grants[tag]:
            raise ValueError('grant without consumed matching beat or duplicate grant')
        self.grants[tag].add(beat)

    def release(self,tag,grant_consumed,readers_drained):
        if (tag not in self.quarantine or grant_consumed is not True or readers_drained is not True
            or self.grants[tag]!=set(range(self.completed_length[tag]))):
            raise ValueError('consumed grant/reader quarantine')
        self.quarantine.remove(tag);self.seen={k for k in self.seen if k[0]!=tag}
        del self.grants[tag];del self.completed_length[tag];del self.tag_groups[tag]

    def edge(self,returns=(),take=(),allocation=None):
        if len(set(take))!=len(take) or any(not 0<=g<8 for g in take):raise ValueError('one consume/group')
        # Invalid wire identities must fail before advancing any bank lease,
        #capture or retirement; a rejected packet is not an accepted clock.
        packet_keys=set();packet_groups=set()
        for record in returns:
            tag,beat=record['tag'],record['beat'];key=tag,beat
            if key in self.seen or key in self.inflight or key in packet_keys:
                raise ValueError('duplicate flight/committed beat')
            if tag not in self.tags or beat not in self.tags[tag]['pending']:raise ValueError('unallocated tag/beat')
            t=self.tags[tag];g=t['group']
            if record['pc']!=t['beats'][beat] or record['sector']!=t['base']+beat:
                raise ValueError('actual PC/sector disagrees with allocated immutable burst')
            if g in packet_groups:raise ValueError('one accepted return/group/edge')
            if not isinstance(record['data'],bytes) or len(record['data'])!=32 or not callable(record['provider']):
                raise ValueError('actual payload/context callback required')
            packet_keys.add(key);packet_groups.add(g)
        out=[]
        for g in take:
            if self.output[g]:
                r=self.output[g].pop(0);out.append(r);key=r['tag'],r['beat']
                self.inflight.remove(key);self.seen.add(key);t=self.tags[r['tag']];t['done'].add(r['beat'])
                pc_beats={beat for beat,p in t['beats'].items() if p==r['pc']}
                if pc_beats<=t['done']:t['remaining_PC']-=1
                if t['remaining_PC']==0:
                    assert t['done']==set(t['beats'])
                    del self.tags[r['tag']];self.quarantine.add(r['tag']);self.live_tags-=1
        # A shared allocation plus up to8 distinct tag completions is one
        #atomic next-live_tags computation; no overwritten nonblocking update.
        if allocation is not None:self.allocate(*allocation)
        for r in self.flight[:]:
            if self.tick==r['edge']+1:
                context=r['provider']()
                if not isinstance(context,bytes) or len(context)!=32:raise ValueError('actual256bit bank provider required')
                r['context']=context;del self.bank[r['pc']]
            if self.tick>=r['edge']+12:
                if 'context' not in r:raise ValueError('uncaptured bank output')
                self.output[r['group']].append(r);self.flight.remove(r)
        accepted=[];issued=set()
        for record in returns:
            tag,beat=record['tag'],record['beat'];key=tag,beat
            if key in self.seen or key in self.inflight:raise ValueError('duplicate flight/committed beat')
            if tag not in self.tags or beat not in self.tags[tag]['pending']:raise ValueError('unallocated tag/beat')
            t=self.tags[tag];g=t['group'];p=t['beats'][beat]
            if g in issued:raise ValueError('one accepted return/group/edge')
            issued.add(g)
            if not isinstance(record['data'],bytes) or len(record['data'])!=32 or not callable(record['provider']):
                raise ValueError('actual payload/context callback required')
            occupancy=len(self.output[g])+sum(r['group']==g for r in self.flight)
            if p not in self.bank and occupancy<32:
                r=dict(record,pc=p,group=g,edge=self.tick);self.flight.append(r);self.bank[p]=key
                self.inflight.add(key);t['pending'].remove(beat);self.reserved_pc[p]-=1;accepted.append(key)
        assert all(len(self.output[g])+sum(r['group']==g for r in self.flight)<=32 for g in range(8))
        self.tick+=1
        return accepted,out

def build(parent):
    import uarch_model as U
    p=Pins(parent);prior=parent_model(parent);risk=rate_risk(parent)
    for path,digest in prior['source_sha256'].items():
        if hashlib.sha256(p.raw(path)).hexdigest()!=digest:raise ValueError('source predecessor changed')
    pkg=p.text('rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv')
    if 'pc_of=((s>>2)^(s>>7)^(s>>12))&31;' not in pkg:raise ValueError('actual PC hash changed')
    native=p.text('rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv')
    for anchor in ("window<=5'd16;","due:cyc+13+2+10","!have_pending&&!response_staged","if(response_staged)"):
        if anchor not in native:raise ValueError('native PC gate changed: '+anchor)
    macro=p.obj('physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json')
    p.text('physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v')
    fifo_macro=p.obj('physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.json')
    phy=p.obj('physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json')
    phy_ports=p.text('physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy_bb.v')
    for anchor in ('input wire req_v,','output wire [31:0] rsp_v,','output wire [8191:0] rsp_data'):
        if anchor not in phy_ports:raise ValueError('PHY external interface changed')
    hbm=p.text('rtl/hdc/kv/ot_hdc_hbm_model.sv')
    p.text('tools/qwen_rom_persistent_kv_g0.py');p.text('tools/qwen_kv_bank_prototype.py')
    groups=math.ceil(prior['joint_service_architecture']['target_feasibility']['explicit_deficit_factor'])
    columns=risk['three_k_requirement']['shared_column_command_ports_per_stack_min']
    fills=risk['three_k_requirement']['shared_64B_fill_lanes_min']
    if (groups,columns,fills)!=(8,4,6):raise ValueError('derive one minimum configuration, no sweep')
    layer=[]
    for l in range(36):
        stacks=[]
        for st in range(4):
            r,w=ranges(l,st);stacks.append(dict(read=count_groups(r),write=count_groups(w),read_ranges=r,write_ranges=w))
        layer.append(dict(layer=l,stacks=stacks))
    read_total=sum(sum(s['read']['groups']) for l in layer for s in l['stacks'])*32
    write_total=sum(sum(s['write']['groups']) for l in layer for s in l['stacks'])*32
    if (read_total,write_total)!=(150690816,156672):raise ValueError('source policy byte debit changed')
    tile_fills=fill_destinations();fill_counts=[sum(n for t,n in enumerate(tile_fills) if t%6==g) for g in range(6)]
    if sum(fill_counts)*36!=risk['token_lower_bounds']['tail_bypass_masked_fill_beats']:raise ValueError('tile fill count changed')
    compute_cycles=risk['overlap']['analytical_current_layer_stages']['cycles']
    point=U.qwen_tp_point(4,6144,'ucie_measured',clock_hz=1200000000,me_lat_extra=55,ctx=8192,su_width=64)
    collective_cycles=2*Fraction(str(point['exchange']['per_allreduce_cycles']))
    # Owner-adopted serial-chain policy prices AR at+28% versus all-stream.
    #Other serial operators remain the explicitly conditional uniform reference.
    collective_cycles_priced=collective_cycles*Fraction(128,100)
    compute_ps=(compute_cycles+collective_cycles_priced)*Fraction(2500,3)
    prefix_ps=Fraction(451*2500,3)
    rest_ps=compute_ps-prefix_ps
    time_ps=Fraction(0);compute_done=Fraction(0);window_done=[Fraction(0),Fraction(0)]
    for row in layer:
        group_sectors=max(s['read']['groups'][g]+s['write']['groups'][g] for s in row['stacks'] for g in range(8))
        # All closing writes are conservatively included in port occupancy;
        #their actual producer release remains a separate causal dependency.
        command_pair=max(sum(s['read']['groups'][g:g+2])+sum(s['write']['groups'][g:g+2]) for s in row['stacks'] for g in range(0,8,2))
        transport=max(Fraction(2*group_sectors*1000),Fraction(command_pair*1000),Fraction(max(fill_counts)*2500,3))
        window=row['layer']%2;start=max(time_ps,window_done[window]);end=start+transport
        prefix_begin=compute_done;prefix_end=prefix_begin+prefix_ps
        cstart=max(end,prefix_end);compute_done=cstart+rest_ps;window_done[window]=compute_done;time_ps=end
        row['optimistic_reservation']=dict(window=window,prefetch_begin_ps=float(start),prefetch_end_ps=float(end),
            compute_begin_ps=float(prefix_begin),prefix_ready_ps=float(prefix_end),attention_begin_ps=float(cstart),compute_end_ps=float(compute_done),group_receipt_bound_ps=2*group_sectors*1000,
            command_pair_bound_ps=command_pair*1000,fill_bound_ps=float(Fraction(max(fill_counts)*2500,3)))
    finite_time=Fraction(0);finite_compute=Fraction(0);finite_windows=[Fraction(0),Fraction(0)]
    for row in layer:
        window=row['layer']%2;start=max(finite_time,finite_windows[window])
        prefix_begin=finite_compute;prefix_end=prefix_begin+prefix_ps
        witness=finite_layer_calendar(row['layer'],start,prefix_end)
        finite_time=witness.pop('end_ps');fill_ready=witness.pop('fill_end_ps')
        attention=max(fill_ready,prefix_end);finite_compute=attention+rest_ps
        finite_windows[window]=max(finite_compute,finite_time)
        row['finite_conditional_reservation']=dict(witness,window=window,
            begin_ps=float(start),all_reverse_grants_end_ps=float(finite_time),
            prefix_begin_ps=float(prefix_begin),prefix_ready_ps=float(prefix_end),
            fill_visible_ps=float(fill_ready),attention_begin_ps=float(attention),
            compute_end_ps=float(finite_compute))
    ff=prior['cells']['ASR_area_um2']+prior['cells']['INV_area_um2'];a=prior['cells']['AND3_area_um2'];iv=prior['cells']['INV_area_um2'];b=prior['cells']['BUF_area_um2']
    # Shared duplicate/live/CAM namespace is retained ONCE. Only tagged
    #flights/output rings, group routing/atomic controls and lease storage grow.
    delta_FF={
      'seven_additional_group_flight_and_output_rings':4*7*32*(542+467),
      'one_early_context_capture_per_actual_bank':4*32*256,
      'shared_tag_group_owner_map':4*4096*3,
      'group_local_ingress':4*7*(455+34+12+6+2),
      'expanded_burst_receipts':4*(128-16)*(192+12+6+3+16*8+4),
      'return_depth64_pointers':4*32*3,
      'native_PC_tagged_pending_reads':4*32*(64-1)*(471+1),
      'PC_frozen16_record_lookahead':4*32*16*(472-(34+1+64)),
      'command_lookahead_head_holds':4*4*339,
      'fill_root_registers_total':6*1048,
      'per_tile_per_window_row_visibility':1536*2*54,
      'stack_matched_cohort_records':128*(100+32+3+4*12+4+32+32+8),
      'write_class_and_cohort_flight_route':4*8*32*(1+7)}
    # Seven additional response/reverse links/stack; request remains a shared
    #burst control port with8 finite group ingress cursors, not8freePHY ports.
    for name,width in (('response',467),('reverse',404)):
        delta_FF[name+'_source_FIFO']=4*7*(2*width+13)
        delta_FF[name+'_FAST_FIFO_and_route']=4*7*(13+39*(2*width+4)+2*width+13)
        delta_FF[name+'_destination_pointer']=4*7*13
    assembly_write_mux_bits=8*512*4*(128+16)  # four quarter sources, disjoint masks; no free multiwrite merge
    mux_bits=assembly_write_mux_bits+4*7*32*(542+467)+4*4*7*339+6*31*1048+4*32*15*472+4*4096*8*6+1536*107
    mux_area=mux_bits*(3*a+2*iv)
    state_area=sum(delta_FF.values())*ff
    # Every named local replica has its own clock/reset tree. Do not replace
    #32 independent PC clocks or8 group roots with one aggregate free tree.
    replicas={'seven_additional_group_flight_and_output_rings':28,
        'one_early_context_capture_per_actual_bank':128,'shared_tag_group_owner_map':4,
        'group_local_ingress':28,'expanded_burst_receipts':32,'return_depth64_pointers':128,
        'native_PC_tagged_pending_reads':128,'PC_frozen16_record_lookahead':128,
        'command_lookahead_head_holds':16,'fill_root_registers_total':6,
        'per_tile_per_window_row_visibility':1536,'stack_matched_cohort_records':8,
        'write_class_and_cohort_flight_route':32}
    replicas.update({name:28 for name in delta_FF if name.startswith(('response_','reverse_'))})
    collectors_by_name={name:2*replicas[name]*tree_count(n//replicas[name],8)['nodes'] for name,n in delta_FF.items()}
    for name,n in delta_FF.items():
        if n%replicas[name]:raise ValueError('exact replicated sink partition')
    collectors=sum(collectors_by_name.values())
    domains={name:('stream' if name in ('fill_root_registers_total','per_tile_per_window_row_visibility','stack_matched_cohort_records') else 'service') for name in delta_FF}
    domains.update(response_source_FIFO='service',response_FAST_FIFO_and_route='stream',
        response_destination_pointer='stream',reverse_source_FIFO='stream',
        reverse_FAST_FIFO_and_route='stream',reverse_destination_pointer='service')
    clock_counts={domain:sum(n for name,n in delta_FF.items() if domains[name]==domain) for domain in ('service','stream')}
    collector_area=collectors*b
    response_macros=4*12  # extra48KiB/stack, actual64x512 gives4KiB/macro
    macro_area=response_macros*fifo_macro['area']['macro_area_um2']
    fanout_total=6*1048*tree_count(256,8)['nodes']
    fanout_area=fanout_total*b
    assembly_FF=4096*787
    assembly_area_increment=assembly_FF*ff/1e6-.9399877632
    assembly_collectors=2*8*tree_count(assembly_FF//8,8)['nodes']
    assembly_collector_area=assembly_collectors*b/1e6
    incremental_mm2=(state_area+mux_area+collector_area+macro_area+fanout_area)/1e6+assembly_area_increment+assembly_collector_area
    known_total_service_mm2=prior['joint_service_architecture']['area']['known_incremental_mm2']+incremental_mm2
    # Fixed modulo6 tile partition: each lane has256 real destinations.
    w=prior['wire']['grid_w_um']/64;h=prior['wire']['grid_h_um']/24
    lane_wires=[]
    for lane in range(6):
        horizontal=sum(max(t%64 for t in range(row*64,(row+1)*64) if t%6==lane)*w for row in range(24))
        lane_wires.append((23*h+horizontal)*1048)
    cut=6*1048+64+64+379+1+128+1;capacity=prior['wire']['shared_tile_cut_nominal_capacity'];width=96.768
    required_corridor_um=width*cut/capacity
    delta_width=required_corridor_um-width
    area_widening=1536*delta_width*h/1e6
    native_readII=28 # due25 + stagedresponse1 + RESERVEedge1 + SCHEDULEedge1
    native_PC_s=max(sum(row['stacks'][st]['read']['PCs'][pc] for row in layer)*native_readII/1e9 for st in range(4) for pc in range(32))
    params={k:int(v) for k,v in re.findall(r'parameter integer (\w+)\s*=\s*(\d+)',hbm)}
    compute_total=risk['token_lower_bounds']['conditional_compute_s']+float(36*(collective_cycles_priced-collective_cycles)/1200000000)
    return dict(schema='qrom-one-minimum-bank-group-service.v1',parent=p.parent,
      status='FAIL_CURRENT_NATIVE_PC_AND_SHARED_CORRIDOR_PHY_ADMISSION_OPEN',
      clocks=dict(service_candidate_Hz=1000000000,stream_target_Hz=1200000000,serial_target_Hz=900000000,
        SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,actual_source_closed=False,
        inherited12edge_lookup_retained=True,serial_AR_multiplier=1.28,
        other_serial_chain_reference_repriced=False,
        serial_scope='TwoAR/layer priced+28% per owner clock policy. Other compute reference is uniform1.2GHz, not adopted serial0.9 operator timing. Actual accepted operator journal must bind its serial-chain cost; no rate or phase credit.'),
      configuration=dict(context=8192,position=8191,TP=4,layers=36,tiles=1536,stacks_per_rank=4,
        bank_groups_per_stack=8,PCs_per_group=4,command_paths_per_stack=4,
        owned_data_grant_paths_per_stack=8,global_fill_lanes=6,fill_payload_B_per_stream_edge_per_lane=64,
        source_request_ports_per_stack=1,group_ingress_cursors=8,physical_context_RAMs_per_stack=32,
        physical_context_RAM_replication=0,group_burst_slots=16,stack_burst_slots=128,burst_max=16,
        expanded_return_entries_per_PC=64,source_actual_return_RAM_rows=64,
        matched_cohorts_per_rank=128,cohort_burst_members=4,global_assembly_slots=4096,
        owner_lookup_output_latency_edges=12,early_bank_capture_edge=1,physical_capture_admitted=False,
        single_candidate=True,parameter_sweep=False),
      partition=dict(bank_group='pc_of(sector)>>2',command_path='bank_group>>1',fill_lane='tile%6',
        aligned16_sector_burst_single_group=True,shared_tag_namespace='12physical bits perstack, shared4096live/quarantine/remaining_PC; added4096x3group ownership, validate full192identity/404reverse. Native16 upper4zero.',
        remaining_PC='AlignedLEN<=16 context set is wholly one group. Up to8 distinct tags may retire/edge; sharedlive_tags_next=live_tags+accepted_alloc-final_retire_popcount, quarantine counted independently. Never clone CAM/live/seen/remaining_PC pergroup.',
        arbitration='Four2-group command selectors; eight4-PC return/write-visible arbiters skip leased/credit-blocked banks. One request allocator can allocate a16-sector burst;8 ingress cursors expand independently.',
        assembly='Four stack-matched bursts form one cohort at same localbase/LEN/group/Owner. Source V word quarters from four stacks coalesce centrally by(window,tile,row); K local pairs retain same keyed pool. Reserve<=32 words/cohort before any member command.128cohorts require4096 global entries, same total as prior4*1024; no4096private slots perstack or free unaligned alignment. Direct global slot=(cohort_index<<5)|word_index; partition into8x512-word pools, four disjoint128bit quarter write selectors and16maskbits priced. No new4096-way CAM search or free multiwrite RAM.',
        cohort_release='Complete every required masked macro write, drain copy-reader leases and consume each member reverse/grant before cohort/tag reuse. Independent local window tile-reader leases remain until actual last attention read.',
        current_V_forward='Final partial V cohort cannot publish eight destination words until actual currentV producer supplies stack3 quarter. QKV prefix can run while historical fill proceeds; producer release/visibility/CDC is a separate causal gate, never invented early payload.',
        destinations_per_fill_lane=[256]*6,tile_fill_beats_per_layer=fill_counts,
        tile_row_visibility='Each1536tile has108 row-visible flags, clear only at leased-window reassignment and set only on masked macro write completion. Global54-row readiness cannot silently qualify partially supplied/padded tiles. Exact consumer used-row/tile masks still require Euclid journal.',
        destination_identity='One window row write port/tile. Six lanes each own disjoint256tiles; full data512/mask512/address7/valid1/tile identity retained. All24rows/64columns routed; no1536global-lane multiplication.'),
      ports=dict(MACs_per_cycle=0,arithmetic_added=False,
        context_RAMs_per_rank=128,context_read_B_per_bank_service_edge=32,context_write_B_per_bank_service_edge=32,
        PC_request_return_RAM_B_per_port_edge=64,return_RAM_depth=64,
        command_payload_B_per_stack_service_edge=128,owned_data_B_per_stack_service_edge_ceiling=256,
        owned_data_and_grant_shared_effective_B_per_stack_service_edge_ceiling=128,
        global_fill_payload_B_per_stream_edge=384,tile_read_B_per_stream_edge=64,tile_write_B_per_stream_edge=64,
        tile_ports_are_not_global_delivery_capacity=True),
      baseline_debit_join=dict(
        existing_full_read_B_per_rank_token=risk['logical_bytes']['read_rank_token'],
        replacement_offchip_read_B_per_rank_token=read_total,closing_write_B_per_rank_token=write_total,
        base_compute_reference_cycles=point['cycles'],base_compute_has_HBM_wait_cycles=False,
        source_compute_join='uarch_model.qwen_tp_point cycles=as_built+exchange+embedding; KV HBM bound is separate bounds.kv_stream, not already in compute cycles. Replace that byte/bandwidth ledger once; never add historical aggregate-HBM service and new finite service twice.',
        base_historical_HBM_Bps_per_rank=4*U.HBM_STACK_BPS,historical_BW_adopted=False,
        context_request_return_macros_retained_once=True,assembly_entries_retained_once=4096,
        prior_known_service_delta_mm2=prior['joint_service_architecture']['area']['known_incremental_mm2'],
        new_group_delta_mm2=incremental_mm2,total_known_service_delta_mm2=known_total_service_mm2,
        inherited_service_slot_refund_mm2=0,existing_PHY_rank_mm2=4*phy['footprint']['area_mm2'],
        PHY_charged_only_if_absent_from_named_baseline=True,complete_named_debit_join=False),
      demand=dict(offchip_read_B_per_rank_token=read_total,closing_write_B_per_rank_token=write_total,
        existing_KV_read_debit_replaced_once=True,incremental_full_layer_refill_B=0,
        source_policy='Conditional existing two K-tail parity tiles/currentVforward. No new compulsory refill or synthetic state. Actual producer and selected demand journal independent.',
        user_home=0,user_home_capacity_bounded=True),
      calendar=dict(scope='Source-address-counted port reservation only, optimistic buffers-ready/PHY service and uniform analytical arithmetic. Not actual production calendar.',
        rows=layer,full36_sequential=True,windows=2,persistent_HBM_erased_on_hop=False,
        staged_ideal_ports_and_uniform_layer_compute_s=float(compute_done/10**12),
        sum_port_reservation_s=float(time_ps/10**12),
        finite_port_and_sequential_compute_witness_s=float(max(finite_time,finite_compute)/10**12),
        finite_witness_if_non_layer_cost_exposed_s=float(max(finite_time,finite_compute)/10**12)+compute_total-36*float(compute_ps/10**12),
        finite_witness_scope='ONE conservative address-only FIFO cohort order, bounded128global/16group cohorts,64PC returns,32flight/output and4096global assembly; grants occupy shared bus only after visible fill and39edge reverse route. Retains12owner and39edge forward links, sourceREQ/RSP/CL minima. Does not qualify physical SRAM capture, actual PHY row/refresh/turnaround, CDC, payload or source readiness.',
        no_compute_overlap_reference_s=float(time_ps/10**12)+compute_total,
        full_token_compute_reference_s=compute_total,analytical_layer_compute_cycles=compute_cycles,
        layer_allreduce_reference_stream_cycles=float(collective_cycles),layer_allreduce_priced_stream_equivalent_cycles=float(collective_cycles_priced),
        per_layer_stages_reference=risk['overlap']['analytical_current_layer_stages']['stages'],
        whole_token_extra_compute_and_exchange_s=compute_total-36*float(compute_ps/10**12),
        total_if_non_layer_compute_exchange_exposed_s=float(compute_done/10**12)+compute_total-36*float(compute_ps/10**12),
        whole_token_extra_scope='72AR priced on36layer chain, including+28% serial AR policy. Existing non-layer/argmax/embedding costs retained separately; no automatic overlap or suffix placement. Current emitted journal locates them. Extra source launch/operand/CDC/currenttail/closingwrite delays also uncredited.',
        closing_write_release='Must follow actual producer/QKV stage and write-visible reverse fences; conservative occupancy above cannot be interpreted as precomputed producer payload.',
        proved_compute_overlap_s=0,qualified_latency_s=None,adopted_rate=None),
      PHY=dict(required_sustained_Bps_per_stack=[sum(sum(row['stacks'][st][k]['groups']) for row in layer for k in ('read','write'))*32*3000 for st in range(4)],
        actual_sustained_Bps=None,ordinary_DQ_bandwidth_adopted=False,
        source_req_single=True,source_rsp32_PC=True,
        existing_physical_footprint_rank_mm2=4*phy['footprint']['area_mm2'],
        existing_pin_count_per_stack=phy['pins']['signal_pins'],parallel_column_service_bound=False,
        boundary='Functional HBMmodel enqueues aLEN burst and schedules32PC loops; native provider exposes one339command bus. Four independent internal column paths require actual controller/PHY binding; neither single burst request nor published32PC inventory proves128GB/s sustained.',
        request_header_bits=455,command_total_bits_per_stack=4*339,owned_receipt_total_bits_per_stack=8*467,
        reverse_total_bits_per_stack=8*404,source_shim_LEN16_AW34_to31_required=True,
        source_hbm_timing_ps={k:params[k] for k in ('REQ_PS','RSP_PS','CL_PS','RCDRD_PS','RP_PS','RFC_PS','REFI_PS','TCCDL_PS')},
        finite_credit_window_ps_per_group_at_target=16*16/(max(sum(row['stacks'][st]['read']['groups'][g]+row['stacks'][st]['write']['groups'][g] for row in layer) for st in range(4) for g in range(8))*3000)*1e12,
        no_refresh_hiding_claim=True,extra_PHY_replicas_selected=0),
      source_gates=dict(native_PC_read_accept_interval_lower_edges=native_readII,native_PC_read_lower_s=native_PC_s,
        native_PC_reason='Fixed16-entry serial scan plus one rd_pending/have_pending. due=col+13+2+10=25; accepted response at25, staged write26, RESERVE27, SCHEDULE28. Four global command paths cannot bypass single pending read/PC.',
        native_PC_replacement='Finite64-tag pending read records/PC, source-bank deadline/refresh/turnaround state and captured16whole-record lookahead priced. Actual source scheduler/FF/mux timing and protection unqualified.',
        prior12edge_bank_hold_capacity_s=sum(row['stacks'][0]['read']['groups'][g] for row in layer for g in range(8))*12/(32*1e9),
        one_edge_capture_SS_macro_clk_to_q_ps=macro['timing']['ss']['clk_to_q_ps'],
        capture_FF_setup_plus_route_budget_ps=1000-60-macro['timing']['ss']['clk_to_q_ps'],
        capture_SSFF_proven=False,retained_output_lookup_latency_edges=12,
        current_source_build_admission=False),
      cells=dict(delta_FF=delta_FF,delta_clock_sink_count=sum(delta_FF.values())+response_macros,
        retained_recomposed_assembly_clock_sinks=assembly_FF,
        delta_FF_domains=domains,delta_clock_sinks_by_domain=clock_counts,
        delta_reset_sink_upper=sum(delta_FF.values()),delta_state_area_um2=state_area,
        mux_bits=mux_bits,mux_reservation_um2=mux_area,collector_buffers=collectors,collector_area_um2=collector_area,
        clock_reset_replicas=replicas,collector_buffers_by_local_replica_family=collectors_by_name,
        predicate_reduction_and_PC_selection_logic_complete=False,
        collector_leaf_segments_um=collectors*32,response_extra_64x512_macros=response_macros,
        extra_response_macro_area_mm2=macro_area/1e6,fill_fanout_buffers_total=fanout_total,
        fill_fanout_cell_reservation_mm2=fanout_area/1e6,delta_known_service_mm2=incremental_mm2,
        total_known_service_mm2=known_total_service_mm2,
        shared_CAM_duplicate_remaining_arrays_copied=False,existing384service128tail_macros_recharged=False,
        assembly_existing_entries=4096,assembly_FF_retained_once=assembly_FF,
        assembly_old_lower_bound_mm2=.9399877632,assembly_actual_cell_reservation_mm2=assembly_FF*ff/1e6,
        assembly_cell_delta_mm2=assembly_area_increment,assembly_8_group_clock_reset_buffers=assembly_collectors,
        assembly_clock_reset_reservation_mm2=assembly_collector_area,assembly_multiwrite_mux_bits=assembly_write_mux_bits,
        root_fill_register_baseline_credit=0,
        controller_protection_decoder_clock_PG_OBS_timing_complete=False),
      routing=dict(fill_wires_um_by_lane=lane_wires,total_fill_wire_um=sum(lane_wires),nominal_RC_extracted=False,
        global_boundary_bits=4*(455+4*339+8*467+8*404)+6*1048,
        shared_row_root_cut_bits=cut,source_cut_capacity=capacity,track_deficit=cut-capacity,
        cut_scope='Minimum six fill bundles plus existing control/clock/reset/x. New window invalidation and endpoint return/control routes additional; no free signal credit.',
        corridor_source_width_um=width,required_same_layer_reservation_width_um=required_corridor_um,
        additional_width_um_per_tile_slot=delta_width,added_array_area_mm2_if_uniform_widening=area_widening,
        candidate_array_w_um=64*(w+delta_width),die_width_limit_um=26000,
        existing_M6_M8_reservation_only=True,separate_routed_channels_allocated=False,
        root_stack_to_six_assembly_crossbar='32 independent grouped sources to6 destination queues; registered31-to1 selection/output and metadata held. Actual endpoint spans and controller route channels additional, never zero.',
        complete_clock_reset_PG_routes=False),
      slot=dict(baseline_array_mm2=prior['slot']['baseline_array_mm2'],other_services_budget_mm2=prior['slot']['remaining_other_services_mm2'],
        known_service_mm2=known_total_service_mm2,parent_interface_mm2=prior['cells']['known_incremental_area_mm2_per_rank'],
        useful_full36_residency_min_increment_mm2=prior['joint_service_architecture']['area']['useful_full_residency_min_increment_mm2'],
        literal_full36_residency_increment_mm2=prior['joint_service_architecture']['area']['literal_full_residency_increment_mm2'],
        known_service_is_cell_macro_reservation_not_completed_floorplan=True,
        actual_service_placement_utilization=None,
        conditional_remaining_before_new_routes_PG_unknowns_mm2=prior['baseline_debit_join']['remaining_if_all_new_debits_and_PHY_outside_baseline_mm2']-incremental_mm2,
        known_uniform_corridor_widening_overflows_other_budget=True,
        named_Maxwell_component_join=False,PHY_increment_credit=0,slot_fit=False),
      admission=dict(three_k_feasible=False,verdict='FAIL_SOURCE_NATIVE_SCHEDULER_AND_SHARED_ROUTING_SLOTS',
        finite_single_order_meets_3k=False,finite_order_failure_is_universal_lower_bound=False,
        perfect_port_bandwidth_is_not_adoption=True,fully_actual_production_trace=False,
        no_second_numerical_position=True,new_RTL=False,new_PnR=False,hardware_admitted=False),
      source_sha256=p.hashes,
      implementation_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in
        ('tools/uarch_model_qwen_parent_context.py','tools/uarch_model_qwen_kv_bank_groups.py')})

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--parent-ref',required=True);ap.add_argument('--result',type=Path,required=True)
    args=ap.parse_args()
    with args.result.open('x') as f:json.dump(build(args.parent_ref),f,indent=2);f.write('\n')
