#!/usr/bin/env python3
"""Additive conventional GPU inventory/timer/finite ownership preparation only.
No bound is a completion provider; no RTL, compile, place/route or slot credit.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib,json,math
from pathlib import Path
from qwen_hbm_controller_events_r1 import ROOT,REV,MACRO,pinned,source_timing
from qwen_hbm_controller_calendar_r2 import bankmap,weight_ranges,BASE,PROGRAM,BankCalendar,edge,audit_bank_events
from qwen_hbm_controller_events_r1 import Beat,queue_port_schedule
from qwen_hbm_downstream_contract_r8 import fixture,costs,provider_ports
PIN='0b88edc97d6d836e094492b09b0ea3c444819f7c'
FAST=F(2500,3)
DIR='results/uarch/qwen_hbm_inventory_timers_20261002'

def get(path):return pinned(ROOT,PIN,path)
def ceil_edges(ps):return math.ceil(F(ps)/FAST)
def width(n):return max(1,n.bit_length())

class Countdown:
    """Saturating elapsed-edge deadline; no retained absolute timestamp."""
    def __init__(self,maximum):self.maximum=maximum;self.left=0
    def arm(self,delay):
        if not 0<=delay<=self.maximum:raise ValueError('unproved horizon')
        self.left=max(self.left,delay)
    def edge(self):self.left=max(0,self.left-1)
    @property
    def ready(self):return self.left==0

def modular_due(now,deadline,bits,retained_age):
    half=1<<(bits-1)
    if not 0<=retained_age<half:raise ValueError('retained age violates signed half-range')
    return ((now-deadline)&((1<<bits)-1))<half

def inventory():
    fp=json.loads(get('results/floorplan/hbm_gpu/qwen_hbm_die.json'))
    generator=get('tools/hbm_gpu_floorplan.py').decode()
    inherited=get('tools/qwen_o4_floorplan.py').decode()
    assert 'SVC_DEPTH = 630.72' in generator and 'service_logic_um2=2 * 10e6' in inherited
    phy=json.loads(get('physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json'))
    bb=get('physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy_bb.v').decode()
    assert 'blackbox' in bb and '[30:0] req_addr' in bb
    rows=[dict(name='licensed PHY/controller boundary abstract',source='physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy_bb.v',replicas=8,placement='PHY strips OUTSIDE service regions',replacement_credit_mm2=0,reason='Blackbox has no internal component inventory or conventional command/WRvisible pins; AW31 LEN5 BEAT4 differs from AW34 LEN6 BEAT5.'),
          dict(name='inherited controller fabric',source='tools/qwen_o4_floorplan.py',replicas=8,placement='service bands',reservation_mm2_per_stack=10,cell_or_macro_breakdown=None,replacement_credit_mm2=0,reason='20mm2 logic/die divided by .50 utilization and4 stacks; no netlist/component replacement mapping.'),
          dict(name='per-PC arbiter and stream heads',source='tools/hbm_gpu_floorplan.py',replicas=256,placement='within inherited service reservation',replacement_credit_mm2=0,reason='Named in holds text only; no independent area or instantiated block in floorplan.'),
          dict(name='GPU SM',source='results/floorplan/hbm_gpu/qwen_hbm_die.json',replicas=64,placement='core outside service regions',replacement_credit_mm2=0,reason='Cannot borrow core RF/shared/Tensor inventory into shoreline.'),
          dict(name='L2 SRAM',source='results/floorplan/hbm_gpu/qwen_hbm_die.json',macro='ot_sram_1r1w_1024x256_m2_r2c2',replicas=512,placement='four L2 slices/die outside service regions',replacement_credit_mm2=0,reason='Existing active L2 storage, not a free request/return macro.'),
          dict(name='new request/return queues',source=MACRO+'.lef',source_commit=REV,macro='ot_sram_1r1w_64x512_m1_r2c2',replicas=512,placement='64 macros/stack inside service regions',replacement_credit_mm2=0,reason='Additional1R1W queues with serialized18..35edge swaps/headprefetch; source floorplan has no existing instance to replace.')]
    assert fp['macro_counts']=={'ot_gpu_sm_q':32,'ot_hbm3e_phy':4,'ot_sram_1r1w_1024x256_m2_r2c2':256}
    paths=['results/floorplan/hbm_gpu/qwen_hbm_die.json','tools/hbm_gpu_floorplan.py','tools/qwen_o4_floorplan.py','physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json','physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy_bb.v']
    return dict(named_components=rows,source_pins={p:dict(commit=PIN,sha256=hashlib.sha256(get(p)).hexdigest()) for p in paths},source_hash_mismatches={p:dict(recorded=v,current=hashlib.sha256(get(p)).hexdigest()) for p,v in fp['source_sha256'].items() if hashlib.sha256(get(p)).hexdigest()!=v},actual_floorplan_source_hashes_match=all(hashlib.sha256(get(p)).hexdigest()==v for p,v in fp['source_sha256'].items()),inherited_replacement_credit_mm2=0,PHY_min_period_ps=phy['timing']['ss']['min_period_ps'],PHY_clock_qualification='FAIL_ABSTRACT_1000PS_MIN_PERIOD_VS_833_1_3PS_TARGET; no clock relaxation',verdict='NO_MATCHED_COMPONENT_REMOVAL_NO_REPLACEMENT_CREDIT')

def timers():
    t=source_timing()
    # Source constraints consumed as elapsed time since REAL emitted commands.
    specs=[('bank_RCD',32,max(t['RCDRD_PS'],t['RCDWR_PS']),'b_act -> ACT-to-column remaining delay'),
           ('bank_ACTok',32,max(t['RAS_PS']+t['RP_PS'],t['RFC_PS']),'b_actok -> tRC/refresh exclusion'),
           ('bank_PREok',32,max(t['RAS_PS'],t['RTP_PS'],t['CWL_PS']+t['BURST_PS']+t['WR_PS']),'b_preok -> PRE exclusion'),
           ('RRD_global',1,t['RRDS_PS'],'last_act'),('RRD_BG',4,t['RRDL_PS'],'last_act_bg'),
           ('FAW',4,t['FAW_PS'],'four actual ACT deadlines retain order'),
           ('CCD_global',1,t['BURST_PS'],'last_col'),('CCD_BG',4,t['TCCDL_PS'],'last_col_bg'),
           ('RTW',1,t['RTW_PS'],'last_rd'),('WTR',1,t['CWL_PS']+t['BURST_PS']+max(t['WTRS_PS'],t['WTRL_PS']),'last_wr plus saved BG'),
           ('refresh',1,F(t['REFI_PS'])*63/32,'next_ref initialization stagger max PC31; recurring REFI')]
    rows=[dict(name=n,count_per_PC=count,max_ps=str(ps),max_edges=ceil_edges(ps),countdown_bits=width(ceil_edges(ps)),source_use=use) for n,count,ps,use in specs]
    per_pc=sum(r['count_per_PC']*r['countdown_bits'] for r in rows)
    # Retain bank open and address-derived19-bit row; never narrow owner/epoch.
    newbits=256*(per_pc+32*(1+19)+3)
    oldbits=256*(32*(1+64+3*64)+17*64+3)
    maxinterval=max(r['max_edges'] for r in rows)
    return dict(source_pin=REV+':rtl/hdc/kv/ot_hdc_hbm_model.sv',constraints=rows,max_retained_local_deadline_edges=maxinterval,modular_counter_bits_if_expiring=width(2*maxinterval),countdown_bits_per_PC=per_pc,bank_row_bits=19,full_AW=34,old_source_shaped_FF_bits=oldbits,candidate_local_FF_bits=newbits,conditional_FF_area_saving_mm2=(oldbits-newbits)*.2916/.5/1e6,
      proof='For each command delay d, ceil(d/T) local edges cannot emit early. Decrement every streaming edge including idle/backpressure; saturate at0, clear expired constraints. For modular representation signed comparisons require every retained delta <2^(W-1); expiration is mandatory before reuse. Initial REF deadline <=ceil((63/32)*REFI/T). Refresh countdown saturates with sticky due, never wraps/reloads on stalled consumer; command issue cannot pass pending refresh.',
      refresh_debt='One sticky due until actual REF; next interval starts only at actual REF. Deferred cadence changes nominal source calendar: required refresh policy review; never adopt slipped cadence as a JEDEC proof.',
      unbounded_fields=['q_arr age under finite queue + unbounded ready stall','r_t/held return residence after data-ready','pending WR ownership until sector retirement/reversecredit','SCORES/PV lease residence','producer64/transport32/logicaltag64/IRSserial32'],
      unbounded_policy='No width reduction. Ready deadline expires to ready bit; ownership never times out. FIFO/owner identity survives indefinitely. Arrival aging may saturate for fairness only after equivalent ordering proof; no such credit here.',
      quantization='Each local command constraint adds <one streaming edge beyond continuous delay; causal ACT/PRE/REF/RD/WR emission remains mandatory. FRFCFS35edge scan and headprefetch bubbles retained; no absolute simulation-time field transferred into CDC hardware.',
      hardware_equivalence_proven=False,applied_width_reduction=False)

class SectorStorePipe:
    """Proposed memory tracker: finite4 owners and held registered retirement.
    Caller supplies actual address-bound store visibility and reversecredit.
    Neither engine finish nor opcode IRS is inferred from elapsed edges.
    """
    def __init__(self,rows):self.rows={r['ordinal']:r for r in rows};self.live={};self.stored=[];self.held=None;self.done=set();self.peak=0
    def reserve(self,ordinal,sector,producer,transport):
        if ordinal not in self.rows or self.rows[ordinal]['sector']!=sector:raise ValueError('address owner mismatch')
        if ordinal in self.live or ordinal in self.done:raise ValueError('duplicate owner')
        if len(self.live)==4:return False
        self.live[ordinal]=(sector,producer,transport);self.peak=max(self.peak,len(self.live));return True
    def store_visible(self,ordinal,owner):
        if self.live.get(ordinal)!=tuple(owner):raise ValueError('actual visible owner mismatch')
        if ordinal in self.stored or (self.held and self.held[0]==ordinal):raise ValueError('duplicate store')
        self.stored.append(ordinal)
    def edge(self,ready):
        taken=None
        if self.held is not None and ready:
            taken=self.held;self.done.add(taken[0]);self.held=None
        if self.held is None and self.stored:
            i=self.stored.pop(0);self.held=(i,self.live[i])
        return taken
    def reverse_credit(self,ordinal,owner):
        if ordinal not in self.done or self.live.get(ordinal)!=tuple(owner):raise ValueError('actual reversecredit missing/mismatch')
        del self.live[ordinal]

class ReaderWindow:
    """Proposed four addressed reader owners; result retirement is an input.
    Full owner identity/data retained after read take; lease ACK never inferred.
    """
    def __init__(self,rows):self.rows=rows;self.live={};self.done=set();self.leased=False
    def acquire(self,actual_lease_event):
        if not actual_lease_event:raise ValueError('actual lease acquire required')
        self.leased=True
    def reserve(self,ordinal,sector,producer,transport):
        if not self.leased:raise ValueError('no reader before actual lease')
        if not 0<=ordinal<len(self.rows) or self.rows[ordinal]['sector']!=sector:raise ValueError('exact reader address')
        if ordinal in self.live or ordinal in self.done:raise ValueError('duplicate reader')
        if len(self.live)==4:return False
        self.live[ordinal]=dict(owner=(sector,producer,transport),result=None);return True
    def take(self,ordinal,owner,data):
        r=self.live[ordinal]
        if r['owner']!=tuple(owner) or r['result'] is not None:raise ValueError('immutable reader owner/result')
        r['result']=data
    def retire(self,ordinal,owner):
        r=self.live[ordinal]
        if r['owner']!=tuple(owner) or r['result'] is None:raise ValueError('actual matching visible result retirement')
        del self.live[ordinal];self.done.add(ordinal)

def graph():
    f=fixture();nodes=[]
    for r in f['sector_rows']:
        i=r['ordinal'];prev=f'accept:{i}'
        stages=['accept']+(['RMW_RD','read_arb6','forward_CDC3','RF_merge27serial','RMW_result_visible','actual_RMW_owned_retire'] if r['partial'] else [])+['WR_reserve_before_pop','scan18to35','causal_PRE_ACT_WR','CWL_burst_backing_visible','ACK_arb3','forward_route36','forward_CDC3','bit_store','sector_retire_registered','held_owned_retire','reverse_route36','reverse_CDC3','credit']
        for n,stage in enumerate(stages):
            key=f'{stage}:{i}';nodes.append(dict(id=key,ordinal=i,sector=r['sector'],stack=r['stack'],bank_identity=bankmap(r['sector']),partial=r['partial'],depends=[] if n==0 else [prev],phase=stage,completion_source='ACTUAL_INPUT_REQUIRED' if stage in ['accept','RMW_result_visible','actual_RMW_owned_retire','bit_store','held_owned_retire','credit'] else 'PROPOSED_RESOURCE_STAGE_NO_EVENT'));prev=key
    g=json.loads(pinned(ROOT,BASE,PROGRAM))
    weights=[w for w in weight_ranges(g) if w['instruction']==17]
    reads=[dict(ordinal=i,**r,depends=['publication272','prior_position0_published','actual_lease_acquire'],actual_acceptance=None,actual_result_retire=None) for i,r in enumerate(f['KV_prefix_read_rows'])]
    return dict(writer_sectors=272,RMW_sectors=256,reader_sectors=288,nodes=nodes,reader_events=reads,
      publication_dependencies=[f'credit:{i}' for i in range(272)],opcode_IRS_separate=[10,11,12,13,15],PV_dependencies=[12,14],resource_caps=dict(front_sector_owners=4,pending_WR_per_stack=4,PCs_per_stack=32,QD=64,RQD=32,sector_retire_FIFO_per_die=4,lease_FIFO_per_die=4,reader_owners=4),
      actual_input_events=[],competing_weight_metadata=weights,synthetic_event_transfer=False,critical_path='Per sector each service starts at max(predecessor visibility, resource availability, downstream reservation). Publication=max(all272 matching reversecredits, actual writer/fence retirement); reader=max(publication, prior publication, actual lease acquire). Release=max(actual SCORES/PV result/IRS retirement, held lease readiness), preserving EXP_SUM14. No total formed from serial sum of work floors.',
      blocked_without_inputs=dict(max_accepted_sector_owners=4,remaining_sector_owners=268,reader_acceptances=0,retirements=0,lease_ACKs=0),
      weight_competition='Actual1737 program matrix17 L0.o.d0 weight traffic shares PC queues/commands; acceptance phases unbound. No source-backed weight issuance before dependency16; prefetch candidate needs explicit actual release records. Retain r5 four-sectors/128-weight diagnostic only, not all272 actual schedule.')

def command_prefix():
    """Causal structural fixture on four exact addresses; zero actual credits.
    Explicit synthetic issue at edge0. No payload/real epochs or retirement.
    First missing RMW result/retirement retains all4 sector owners.
    """
    t=source_timing();cal=BankCalendar(t,FAST);rows=fixture()['sector_rows'][:4]
    q=[];pending=list(rows);phase=None;head_ready=F(0);journal=[];returns=[]
    limit_edges=512
    for cycle in range(limit_edges):
        now=cycle*FAST
        if phase and phase['stage']=='scan' and now>=phase['end']:
            b=phase['beat'];before=len(cal.events);col=cal.plan(b,now)
            assert all(e['ps']>=now for e in cal.events[before:]),'no retrospective command'
            journal.append(dict(kind='calendar_provider_start',ps=str(now),sector=b.addr))
            phase=dict(stage='column',end=col,beat=b)
        if phase and phase['stage']=='column' and now>=phase['end']:
            b=phase['beat'];q.pop(0);phase=None;head_ready=now+FAST
            ready=edge(now+t['CL_PS']+t['BURST_PS']+t['RSP_PS'],FAST)
            landed=(ready+6*FAST+36*FAST)//F(10000,9)*F(10000,9)+3*F(10000,9)
            returns.append(dict(sector=b.addr,data_ready_ps=str(ready),candidate_RF_landing_ps=str(landed),actual_RMW_result=None,actual_owned_retirement=None))
        if phase is None and q and now>=head_ready:
            b=q[0];edges=len(queue_port_schedule(0))
            phase=dict(stage='scan',end=now+edges*FAST,beat=b)
            journal.append(dict(kind='scan_freeze',ps=str(now),sector=b.addr,edges=edges))
        if pending and phase is None:
            r=pending.pop(0);empty=not q
            # Synthetic epoch marker retained by model only, never actual evidence.
            b=Beat(r['sector'],r['ordinal'],7,8,accepted_ps=now);q.append(b)
            if empty:head_ready=max(head_ready,now+2*FAST)
            journal.append(dict(kind='candidate_accept',ps=str(now),sector=b.addr,bank=bankmap(b.addr),identity_scope='SYNTHETIC_FIXTURE_EPOCH7_TRANSPORT8_NOT_ACTUAL'))
    commands=sorted(cal.events,key=lambda e:(e['ps'],e['pc']))
    audit=audit_bank_events(commands,t)
    assert len(returns)==4 and not pending and not q
    assert max(Counter((e['pc'],e['ps']) for e in commands).values())==1
    assert all(e['ps']<=limit_edges*FAST for e in commands)
    return dict(status='CAUSAL_STRUCTURAL_PREFIX_BLOCKED_ACTUAL_RMW_PROVIDER_ABSENT',scope='Explicit synthetic acceptance fixture on actual four metadata addresses; no observed timestamp/epoch or fullprogram timing transfer',controller_period_ps=str(FAST),commands=commands,modeled_service_events=[dict(**e,observe_ps=e['ps']) for e in commands],command_timing_audit=audit,queue_journal=journal,read_boundaries=returns,held_sector_owners=4,remaining_writer_sectors=268,blocked_reader_sectors=288,WR_commands=0,retirement_events=0,lease_ACKs=0,weight_commands=0,weight_reason='actual matrix17 dependency16 unavailable; no granted prefetch',refresh='512edge prefix ends before earliest REFI; bounded current-refresh countdown contract in timer record, not waived',critical_path='max(each modeled RF landing, actual result visibility, actual owned retirement); latter two absent',hardware_credit=0)

def compose():
    c=costs();tm=timers();inv=inventory()
    # This is an impossibility bound even granting removal of ALL priced bank
    # state+timer compare logic. It is not authorized replacement credit.
    physical=json.loads(get('results/uarch/qwen_hbm_resource_schedule_20261002/model_r7.json'))['physical']
    free_timer_max=(physical['source_bank_timer_FF_proxy_mm2']+c['timer_compare_mux_proxy_mm2'])/8
    reader_bits=2*(4*(338+256+3)+2*288)
    reader_area=reader_bits*.2916/.5/1e6
    original=c['total_retained_plus_additive_lower_bound_mm2_per_stack']+reader_area/8;slot=c['available_service_slot_mm2_per_stack']
    conditional=original-tm['conditional_FF_area_saving_mm2']/8
    return dict(schema='Qwen_component_inventory_bounded_timer_candidate_r9',inventory=inv,timers=tm,
      resource_area=dict(retained_r8_mm2_per_stack=c['total_retained_plus_additive_lower_bound_mm2_per_stack'],r9_reader_FF_bits=reader_bits,r9_reader_area_system_mm2=reader_area,r9_retained_plus_additive_mm2_per_stack=original,slot_mm2_per_stack=slot,conditional_countdown_FF_only_mm2_per_stack=conditional,conditional_countdown_overflow_mm2_per_stack=conditional-slot,impossible_free_all_bank_timer_and_compare_mm2_per_stack=original-free_timer_max,impossible_free_timer_overflow_mm2_per_stack=original-free_timer_max-slot,applied_replacement_credit_mm2=0,
       provider_FF_bits=c['additional_provider_FF_bits'],provider_area_system_mm2=c['additional_provider_area_proxy_mm2'],timer_decrement_zero_detect_reload_mux_cost='REQUIRED:256PC replicated countdown datapaths; row match19bits, deadline max logic, refresh due priority and scan invalidation; no decrement/mux/clock cost waived',
       inherited_occupancy=c['inherited_controller_fabric_reservation_mm2_per_stack'],via_count_per_stack=c['candidate_overmacro_M4_to_upper_data_endpoint_vias_per_stack'],via_PDN=c['via_cost_contract'],failed_corridor=c['failed_corridor'],routing_signal_escrow=.5,
       fit=False,verdict='FAIL_EVEN_FREE_ALL_PRICED_TIMER_BANK_STATE_CANNOT_CLOSE_SLOT'),
      endpoint_contract=provider_ports(),finite_graph_summary={k:v for k,v in graph().items() if k not in ['nodes','reader_events']},
      per_boundary=dict(sector_bytes=32,RD_packet_bits=471,WR_visible_bits=216,owned_retirement_bits=404,lease_bits=350,retirement_flits_320_with_header64=2,lease_flits_320_with_header64=2,read_arbiter_edges=6,WR_arbiter_edges=3,command_slots_per_PC=1,queue_freeze_edges='18..35+headprefetch1/empty2',MACs_per_cycle=0),
      exact_blockers=['Floorplan recorded uarch_model hash stale; geometry source hashes match, regenerate after inventory review','No named inherited service-fabric component/area/instance removal proof: replacement credit0','Even removing all priced bank/timer state and compare logic leaves area overflow','Address-bearing sector-store and reader lease provider endpoints absent; actual result/IRS correlation required','Countdown equivalence and refresh debt/cadence policy unreviewed; unbounded ownership remains full width','Direct corridor/pin escape fails; actual via/PDN area and clock tree/SSFF inventory absent','AW31/LEN5/BEAT4 PHY blackbox incompatible with proposed AW34/LEN6/BEAT5;1000ps abstract minimum vs833.333ps target'],
      source_bound_completion_events=0,provider_PASS=False,RTL_admission=False,physical_admission=False,hardware_rate_credit=0,compile=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',required=True,type=Path);a=p.parse_args();a.output_dir.mkdir(exist_ok=False)
    records={'model_r9.json':compose(),'finite_address_graph_r9.json':graph(),'causal_command_prefix_r9.json':command_prefix(),'timer_slot_failure_r9.json':dict(status='FAIL_PRESERVED',**compose()['resource_area'])}
    for name,value in records.items():(a.output_dir/name).write_text(json.dumps(value,indent=2,sort_keys=True,default=lambda v:str(v) if isinstance(v,F) else None)+'\n')
