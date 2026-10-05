#!/usr/bin/env python3
"""Pure causal finite model: exact addresses, supported service, fail-closed phases.

No existing-source timestamp is transferred into a repaired provider verdict.
External engine retirement/lease timestamps are absent: retained credits never
release on an invented timer. Prefix critical paths and blocked resources are
computed, not a full token latency or RTL admission.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import argparse,hashlib,json,math,re
from pathlib import Path
from qwen_hbm_controller_events_r1 import ROOT,REV,MACRO,Beat,pinned,source_timing,queue_port_schedule
from qwen_hbm_controller_calendar_r2 import BankCalendar,bankmap,edge,audit_bank_events,kv_rows,PROGRAM,BASE
from qwen_hbm_provider_prep_r3 import read_journal
from qwen_hbm_visible_provider_prep_r6 import VisibleProvider

PIN='4d62907d1f92df00607e63f10bd278cd0d4474fd'
OBS='results/rtl/qwen_hbm_provider_observation_r5_20261002'
FAST=F(2500,3);SLOW=F(10000,9)

def cross(now,period):return (F(now)//period+3)*period

class Model:
    def __init__(self,requests,read_hold_until=0,front_capacity=4):
        self.front_capacity=front_capacity;self.live_front=set();self.values={}
        self.t=source_timing();self.tc=F(self.t['CLK_PS']);self.bank=BankCalendar(self.t,self.tc)
        self.writer=VisibleProvider(self.t);self.jobs=deepcopy(requests);self.ingress=None
        self.skip=[0]*32;self.command_seen=set();self.q=[[] for _ in range(32)];self.phase=[None]*32;self.ready=[F(0)]*32
        self.returns=[[] for _ in range(32)];self.reserved=[0]*32;self.rr=0
        self.log=[];self.now=F(0);self.read_hold_until=F(read_hold_until)
        self.rmw_done={};self.merge_done={};self.merge_free=F(0);self.store_free=F(0)
        self.inflight={};self.stored={};self.held_read=None;self.peaks=Counter();self.stalls=Counter()
        self.visible_ack_next=F(0);self.read_arb_next=F(0)
    def emit(self,event,now,b=None,**fields):
        row=dict(event=event,ps=F(now),**fields)
        if b:row.update(tag=b.tag,beat=b.beat,sector=b.addr,producer_epoch=b.producer_epoch,transport_epoch=b.transport_epoch)
        self.log.append(row)
    def refresh(self,p,now):
        if self.phase[p] and self.phase[p]['stage']=='command':return False
        if self.bank.next_ref[p]>now:return False
        # Current-time autonomous service, including completely idle PCs.
        banks=self.bank.b[p];opened=[b for b in banks if b.open]
        start=max(now,self.bank.last_col[p]+self.t['BURST_PS'])
        if opened:
            pre=edge(max([start]+[b.preok for b in opened]),self.tc)
            self.bank.log('PREall',pre,p);start=pre+self.t['RP_PS']
        ref=edge(start,self.tc);self.bank.log('REF',ref,p)
        for b in banks:b.open=False;b.actok=max(b.actok,ref+self.t['RFC_PS'])
        self.bank.last_ref[p]=ref
        self.bank.next_ref[p]+=self.t['REFI_PS']
        end=ref+self.t['RFC_PS'];self.ready[p]=max(self.ready[p],edge(end,self.tc))
        if self.phase[p]:
            # Refresh invalidates the bank estimate: restart the frozen scan.
            self.phase[p]=None;self.stalls['refresh_scan_restart']+=1
        self.emit('current_refresh',now,pc=p,REF_ps=ref,ready_ps=end)
        return True
    def choose(self,p,now):
        a=self.q[p];n=min(16,len(a));selected=0;
        if self.skip[p]>=16:return 0
        best=self.bank.estimate(a[0],now)
        for i in range(1,n):
            b=a[i]
            if any(x.addr==b.addr and (x.write or b.write) for x in a[:i]):continue
            estimate=self.bank.estimate(b,now)
            if estimate<best:best=estimate;selected=i
        return selected
    def step(self,now):
        self.now=F(now);now=self.now;self.writer.advance(now)
        # Downstream: ACK capture records and FIFO capacity are held through
        # consumer retirement/reversecredit. No timer can release these slots.
        offered=self.writer.offer(now)
        if offered and now>=self.visible_ack_next and len(self.inflight)<4:
            b=offered.request
            ack=self.writer.capture(now,True);self.visible_ack_next=now+self.tc
            # Two-level WR4 arbiter + registered held output; source-shaped
            # three-destination-edge FIFO; floorplan conservative36fast route.
            registered=edge(now+3*self.tc,FAST)
            routed=registered+36*FAST
            delivered=cross(routed,SLOW)
            stored=edge(max(delivered,self.store_free),SLOW)+SLOW
            self.store_free=stored
            self.inflight[b.tag]=dict(request=b,stored_ps=stored)
            self.emit('held_visible_ACK_capture',now,b,registered_ps=registered,route_ready_ps=routed,forward_CDC_ps=delivered,scoreboard_visible_ps=stored)
        for tag,item in self.inflight.items():
            if tag not in self.stored and item['stored_ps']<=now:
                self.stored[tag]=item['stored_ps'];self.writer.downstream(item['request'],'forward_CDC');self.writer.downstream(item['request'],'completion_store')
                self.emit('scoreboard_store_visible',item['stored_ps'],item['request'],next_required='actual_sector_consumer_retire')
        # One locked stack RD arbiter, five binary mux levels and registered
        # held output. Source response-tail is not a replacement for that cost.
        if self.held_read and now>=self.held_read[2] and now>=self.read_hold_until:
            p,b,ready=self.held_read;self.returns[p].pop(0);self.reserved[p]-=1
            self.emit('read_take',now,b,pc=p)
            if b.tag<4:
                # Real addressed partial RMW stage: source candidate3x9serial
                # XOR/AND/XOR cost, one shared serial port, plus floorplan hop.
                landed=cross(now+36*FAST,SLOW)
                merged=edge(max(landed,self.merge_free),SLOW)+27*SLOW
                self.merge_free=merged;self.merge_done[b.tag]=merged
                self.emit('RMW_merge_bound',now,b,landing_ps=landed,merge_done_ps=merged)
            self.held_read=None;self.read_arb_next=now+self.tc
        if self.held_read is None and now>=self.read_arb_next:
            for offset in range(32):
                p=(self.rr+offset)%32
                if self.returns[p] and self.returns[p][0][1]<=now:
                    b,due=self.returns[p][0];self.held_read=(p,b,now+6*self.tc);self.rr=(p+1)%32
                    self.emit('read_arbiter_lock',now,b,pc=p,held_ready_ps=now+6*self.tc);break
        for p in range(32):
            self.refresh(p,now)
            state=self.phase[p]
            if state and state['end']<=now:
                b=state['request']
                if state['stage']=='scan':
                    if b.write:
                        if not self.writer.reserve(b,now):self.stalls['WR_reservation_full_or_WAW']+=1;continue
                    else:
                        if self.reserved[p]>=32:self.stalls['RQD32']+=1;continue
                        if self.writer.read(b.addr,now) is None:self.stalls['RAW_visibility']+=1;continue
                        self.reserved[p]+=1
                    # Future command reservations are emitted at their dated
                    # explicit service edges, not claimed at planning time.
                    # Autonomous refresh owns next_ref; disable demand refresh
                    # only inside this one exclusive PC command chain.
                    refresh_due=self.bank.next_ref[p];self.bank.next_ref[p]=F(10**30)
                    start_index=len(self.bank.events);column=self.bank.plan(b,now)
                    self.bank.next_ref[p]=refresh_due
                    events=self.bank.events[start_index:]
                    assert all(e['ps']>=now for e in events)
                    self.phase[p]=dict(stage='command',end=column,request=b,events=events)
                    self.emit('capacity_reserved_before_commands',now,b,pc=p,column_ps=column)
                else:
                    assert self.q[p][0]==b
                    if b.write:self.writer.column(b,now)
                    else:
                        due=now+self.t['CL_PS']+self.t['BURST_PS']+self.t['RSP_PS'];self.returns[p].append((b,due));self.values[b.tag,b.beat]=self.writer.read(b.addr,now)
                    self.q[p].pop(0);self.ready[p]=now+self.tc;self.phase[p]=None
                    self.emit('column_head_pop',now,b,pc=p)
            if self.phase[p] is None and self.q[p] and now>=self.ready[p]:
                selected=self.choose(p,now);self.skip[p]=self.skip[p]+1 if selected else 0;b=self.q[p].pop(selected);self.q[p].insert(0,b)
                cycles=len(queue_port_schedule(selected))
                self.phase[p]=dict(stage='scan',end=now+cycles*self.tc,request=b)
                self.emit('PC_frozen_scan',now,b,pc=p,selected=selected,edges=cycles,end_ps=now+cycles*self.tc)
        # One shared ingress/beat expansion port/stack. Each macro has one
        # write port; a frozen PC rejects expansion, holding the whole ingress.
        if self.ingress is None and self.jobs and len(self.live_front)>=self.front_capacity:self.stalls['front_maps_held_without_consumer_retire']+=1
        if self.ingress is None and self.jobs and len(self.live_front)<self.front_capacity:
            for i,j in enumerate(self.jobs):
                if F(j['release_ps'])>now:continue
                if j['write'] and j.get('RMW_tag') is not None:
                    prior=j['RMW_tag']
                    if prior not in self.merge_done or self.merge_done[prior]>now:continue
                self.ingress=self.jobs.pop(i);self.live_front.add(j['tag']);self.ingress['cursor']=0;self.ingress['accept_ps']=now
                self.emit('request_accept',now,tag=j['tag'],sector=j['addr'],length=j['length'],write=j['write']);break
        if self.ingress:
            j=self.ingress;cursor=j['cursor'];b=Beat(j['addr']+cursor,j['tag'],2**48+1,1,cursor,j['write'],j.get('data',0),int(j['accept_ps']));p=bankmap(b.addr)['pc']
            if self.phase[p] is not None:self.stalls['ingress_PC_frozen']+=1
            elif len(self.q[p])>=64:self.stalls['QD64']+=1
            else:
                empty=not self.q[p];self.q[p].append(b);self.emit('beat_enqueue',now,b,pc=p)
                if empty:self.ready[p]=max(self.ready[p],now+2*self.tc)
                j['cursor']+=1
                if j['cursor']==j['length']:self.ingress=None
        for i,command in enumerate(self.bank.events):
            if i not in self.command_seen and command['ps']==now:
                self.command_seen.add(i);self.emit('command_service_edge',now,pc=command['pc'],bank=command['bank'],command=command['kind'],sector=command['sector'])
        self.peaks['front_maps']=max(self.peaks['front_maps'],len(self.live_front))
        self.peaks['Q']=max(self.peaks['Q'],max(map(len,self.q)))
        self.peaks['RD_reserved']=max(self.peaks['RD_reserved'],max(self.reserved))
        self.peaks['WR_resident']=max(self.peaks['WR_resident'],len(self.writer.slots))
        self.peaks['ACK_downstream']=max(self.peaks['ACK_downstream'],len(self.inflight))
    def run(self,limit=6000000):
        for now in range(0,limit+1,self.t['CLK_PS']):self.step(now)
        emitted=[e for e in self.bank.events if e['ps']<=limit]
        assert len(self.command_seen)==len(emitted),'every planned in-bound command serviced at its actual model edge'
        timing=audit_bank_events(emitted,self.t)
        commands=Counter((e['pc'],e['ps']) for e in self.bank.events)
        assert max(commands.values())<=1,'one conventional command/PC/edge'
        assert max(self.reserved)<=32 and len(self.writer.slots)<=4
        return dict(status='FINITE_PREFIX_BLOCKED_ON_ACTUAL_CONSUMER_RETIREMENT' if self.live_front else 'FINITE_READ_PREFIX_MODEL_ONLY',front_capacity=self.front_capacity,live_front_maps=len(self.live_front),read_values=[dict(tag=k[0],beat=k[1],data=str(v)) for k,v in sorted(self.values.items())],limit_ps=limit,peaks=dict(self.peaks),stalls=dict(self.stalls),timing=timing,remaining_jobs=len(self.jobs),queued_beats=sum(map(len,self.q)),retained_WR_slots=len(self.writer.slots),stored_WRs=len(self.stored),known_prefix_critical_path_ps=max(list(self.stored.values())+list(self.merge_done.values())+[e['ps'] for e in self.log if e['event']=='read_take'],default=0),publication='max(all272 reversecredit completions); unsupported actual_consumer_retire/lease phases prevent publication',journal=self.log,commands=emitted,command_reservations_beyond_bound=[e for e in self.bank.events if e['ps']>limit])


def requests(case):
    events=read_journal(ROOT/OBS/f'case{case}.tsv')
    return [dict(tag=e['tag'],addr=e['sector'],length=e['beat'],write=e['kind']=='ACCEPT_WR',release_ps=e['observe_ps'],data=sum((0x71000000+e['tag'])<<(32*i) for i in range(8)) if e['kind']=='ACCEPT_WR' else 0,RMW_tag=e['tag']-4 if case==0 and e['kind']=='ACCEPT_WR' else None) for e in events if e['kind'].startswith('ACCEPT_')]


def physical_costs():
    fp=json.loads(pinned(ROOT,PIN,'results/floorplan/hbm_gpu/qwen_hbm_die.json'))
    raw=pinned(ROOT,REV,MACRO+'.lef').decode();spec=json.loads(pinned(ROOT,REV,MACRO+'.json'))
    w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',raw).groups())
    halos=(4.32,2.16);px=w+2*halos[0];py=h+2*halos[1]
    band=next(x for x in fp['regions'] if x['name']=='svc_south');rows=math.floor(band['h']/py)
    # Equal halves of one existing real service band, each owns two64 queues.
    slot_w=band['w']/2;cols=math.ceil(64/rows)
    packed=cols*px*rows*py;slot_area=slot_w*band['h']
    lower_OBS=re.findall(r'LAYER (M\d+) ;\s*RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',raw.split('  OBS')[1])
    model=json.loads(pinned(ROOT,PIN,'results/uarch/qwen_hbm_visible_provider_prep_20261002/model_r6.json'))
    # Tree32+tree4 pipeline costs, placed before shared corridors; no 32-PC
    # raw fanout escapes the shoreline. Complete context/logic slot not proven.
    nodes_read=31*471;nodes_WR=3*216;tree_bits=8*(nodes_read+nodes_WR)
    tree_proxy=tree_bits*.2916/.5/1e6;tree_mux=tree_bits*.2/.5/1e6
    bank_timer_bits=8*32*(32*(1+64+3*64)+(17*64+3))
    bank_timer_proxy=bank_timer_bits*.2916/.5/1e6
    common=json.loads(pinned(ROOT,PIN,'results/rtl/qwen_hbm_complete_20261001/common36_drain_model_r2.json'))
    common_proxy=common['candidate_additional_state']['conservative_additive_area_mm2']
    per_stack_control=(model['subset_area']['queue_and_r1_r6_control_proxy_mm2']-model['subset_area']['queue_macro_mm2'])/8+bank_timer_proxy/8+common_proxy/8
    shared_bits=471+216+409+64 # RD,WRvisible, epoch-bearing request+drain
    return dict(macro_width_um=w,macro_height_um=h,macro_signal_pins=spec['area']['outline']['signal_pins'],halo_um=halos,OBS=lower_OBS,
        macros_per_stack=64,rows=rows,columns=cols,queue_rectangle_um=[cols*px,rows*py],queue_reserved_area_mm2=packed/1e6,service_slot_um=[slot_w,band['h']],service_slot_area_mm2=slot_area/1e6,
        control_plus_tree_proxy_mm2=per_stack_control+(tree_proxy+tree_mux)/8,priced_subset_total_mm2_per_stack=packed/1e6+per_stack_control+(tree_proxy+tree_mux)/8,
        queue_rectangle_fits=cols*px<=slot_w and rows*py<=band['h'],service_band_unclaimed_remaining_mm2_per_stack=slot_area/1e6-packed/1e6-per_stack_control-(tree_proxy+tree_mux)/8,
        source_bank_timer_FF_bits=bank_timer_bits,source_bank_timer_FF_proxy_mm2=bank_timer_proxy,common36_r2_additive_proxy_mm2=common_proxy,command_tree_added_FF_bits=tree_bits,tree_FF_proxy_mm2=tree_proxy,tree_mux_proxy_mm2=tree_mux,
        read_arbiter_latency_edges=6,WR_arbiter_latency_edges=3,raw_PC_read_bus_bits=32*471,
        raw_PC_read_bus_fits_vertical_channel=32*471<=fp['channels_um']['v_wires'],locked_shared_bus_bits=shared_bits,all_four_stack_trunk_bits=4*shared_bits,all_four_stack_trunk_fits=False,vertical_channel_tracks=fp['channels_um']['v_wires'],shared_bus_fits_vertical_estimate=shared_bits<=fp['channels_um']['v_wires'],
        raw_local_macro_escape_tracks_estimate=2*halos[0]*fp['channels_um']['tracks_per_um_v'],macro_pin_half_edges=spec['area']['outline']['pins_per_edge'],escape_status='FAIL_ALL_PIN_DIRECT_CORRIDOR; upper-layer over-macro routing/local mux/tied mask pins must be explicitly lowered',
        OBS_scope='M1..M4 obstructed by source LEF; M5..M9 upper routing not obstructed in abstract, but no detailed via/PDN/pin escape proof.',
        slot_fit_status='PRICED_QUEUE_TREE_SUBSET_FITS_AREA_ONLY; Bank timer FF and common36r2 delta priced; timer comparator/mux logic, inherited common36 base/RF, pin escape, PHY controller occupancy still unbound',
        physical_qualification=False)


def compose():
    cases=[];direct=[]
    for c in range(3):
        model=Model(requests(c),4100000 if c==1 else 0);r=model.run();r['case']=c;r['scope']='Strict Common36 four mappings/die; no release on read take or ACK store';cases.append(r)
        backend=Model(requests(c),4100000 if c==1 else 0,64);b=backend.run();b['case']=c;b['scope']='Direct finite source-bench64tag-ledger port contract only; no Common36/engine retirement admission';direct.append(b)
    graph=json.loads(pinned(ROOT,BASE,PROGRAM));rows=kv_rows(graph,graph['instructions'][10],1)
    binding=dict(actual_program_instructions=len(graph['instructions']),writer=10,fence=11,KV_read=12,position=1,writer_sectors=len(rows),sectors_by_stack=dict(Counter(r['stack'] for r in rows)),actual_addresses_SHA=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),executed_subset='Pinned r5 case0 four exact KV sectors and128 next-matrix weight sectors; case1/case2 source-contract fixtures.',phase_scope='Recorded acceptance times are release lower bounds, not repaired acceptance; RMW27serial and route/CDC costs are source-shaped candidates, not actual engine measurements.')
    return dict(schema='Qwen_causal_finite_resource_schedule_r7',status='EXECUTED_SUPPORTED_PREFIX_WITH_EXACT_MISSING_PHASE_FAILURE',source_pin=PIN,observed_pin='952dc10e76d5b1eb7df2cbb7ad711fbf80630b05',cases=cases,direct_source_bench_diagnostics=direct,program_binding=binding,physical=physical_costs(),clocks=dict(controller_ps=1000,hub_FAST_ps=str(FAST),serial_ps=str(SLOW),scope='Independent explicit source-model domains, no universal or signoff clock'),
        downstream_costs=dict(RMW_serial_edges=27,ACK_arbiter_register_controller_edges=3,read_arbiter_register_controller_edges=6,floorplan_NoC_FAST_edges_oneway=36,forward_CDC_destination_edges=3,scoreboard_store_serial_edges=1,reverse_CDC_destination_edges=3,
        sector_consumer_retirement='REQUIRED_INPUT: existing Common36.consumer_result_retire result_visible_ps/dut_retire_ps, no controller producer hook or measured service.',SCORES_PV_lease='REQUIRED_INPUT: actual KVread acquisition, both consumer result/retire records, persistent lease-release and writer context release.',no_zero_cost_phase=True),
        critical_path='Prefix = max actual scheduled dependency/resource arrival, with explicit scan/command/tail/arbiter/NoC/CDC/store costs. Full publication/reader critical path = max all272 completed reversecredits plus exact acquired/retired lease DAG; not evaluable without mandatory provider inputs.',
        no_callback_failure=dict(stage='four_front_mappings_held_until_actual_RMW_read_or_sector_consumer_retire; directACK diagnostics stop after completion_store',retained_reservations=True,reversecredit_events=0,actual_publication_events=0,KVread_lease_events=0,provider_experiment_required='Journal actual finite result visibility/sector retirement/lease endpoints, or review and price a new supported consumer microarchitecture; do not free reservations from ACK-store alone.'),
        hardware_RTL_admission=False,provider_PASS=False,hardware_rate_credit=0,fullprogram_execution=False)

def encode(o):return str(o) if isinstance(o,F) else o
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with a.output.open('x') as f:json.dump(compose(),f,indent=2,sort_keys=True,default=encode);f.write('\n')
