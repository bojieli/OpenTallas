#!/usr/bin/env python3
"""Finite burst admission and source-pinned HC22 transport scope checks, not RTL."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import types
import w19_burst_ingress as M

ROOT=Path(__file__).resolve().parents[1]
PROVIDER_COMMIT='49c9c190ab10e5e196d27393d572e311f093998b'
PROVIDER='tools/w16_gpu_hc_dot_schedule.py'
INPUT='results/uarch/w16_gpu_hc_dot_schedule_20261001/inputs_r1.json'
COST='results/uarch/w16_gpu_hc_dot_schedule_20261001/cost_r1.json'
BANK_COMMIT='0833a6613d0f0568dd28cb68fb1550b0d1b7c137'
BANK='tools/w19_landing_banks.py'


def blob(commit,path):
    return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)


def historical_bank():
    source=blob(BANK_COMMIT,BANK)
    module=types.ModuleType('pinned_w19_bank_0833')
    module.__file__=str(ROOT/BANK)
    exec(compile(source,module.__file__,'exec'),module.__dict__)
    return module


class Admission(M.Burst):
    """Only ports prepared requests retained. Grants update queues atomically."""
    def __init__(self,ports=1,**kwargs):
        if ports not in (1,2):raise ValueError('one real or two proposed ports')
        super().__init__(**kwargs);self.ports=ports

    def prepare(self,*args,**kwargs):
        if sum(not r['issued'] for r in self.pending.values())==self.ports:return None
        return super().prepare(*args,**kwargs)

    def admit(self,tags,rooms,controller_ready=True):
        if len(tags)>self.ports or len(set(tags))!=len(tags):raise ValueError('invalid port candidates')
        if any(t not in self.pending or self.pending[t]['issued'] for t in tags):raise ValueError('unprepared/duplicate request')
        if not controller_ready:return []
        requests=[(self.pending[t]['addr'],self.pending[t]['length']) for t in tags]
        parity={self.pending[t]['group']&1 for t in tags}
        if len(tags)==2 and (len(parity)!=2 or not M.joint_ready(requests,rooms)):
            # Oldest-first isolated grant; do not independently consume stale
            #room on both ports. Same metadata parity is serialized.
            tags=tags[:1]
            requests=requests[:1]
        if not M.joint_ready(requests,rooms):return []
        for t in tags:self.pending[t]['issued']=True
        return tags


def bank_tail(stall_cycles=0):
    B=historical_bank();m=B.Landing();m.allocate(0,0)
    for beat in range(4):m.step({0:(0,beat,bytes([beat])*32)},ready=set())
    last_response_cycle=3
    m.step(ready=set());last_write_cycle=4
    assert m.lines[0]['mask']==15
    release=last_write_cycle+3+stall_cycles
    while m.cycle<release:m.step(ready=set())
    m.step(ready={0})
    assert len(m.delivered)==1
    delivery=m.delivered[0]['cycle']
    return dict(last_controller_response_accept_cycle=last_response_cycle,
        last_bank_write_cycle=last_write_cycle,delivery_cycle=delivery,
        tail_after_bank_write_cycles=delivery-last_write_cycle,
        tail_after_response_accept_cycles=delivery-last_response_cycle,
        finite_destination_hold_cycles=stall_cycles,
        tail_serial_cycles_ceil=math.ceil(Fraction((delivery-last_write_cycle)*3,4)),
        scope='Pinned0833 cycle oracle with one PC delivering one sector/cycle; no physical/loaded-HBM evidence')


def same_SM_trace():
    m=M.Burst(groups=8,credits=Counter({0:32}))
    tags=[]
    for group in range(8):
        tag=m.prepare(16*group,[0]*4,128);m.grant(tag,[64]*32);tags.append(tag)
    for phase in (3,1,2,0):
        responses={}
        for group,tag in enumerate(tags):
            for line in range(4):
                beat=4*line+phase;pc=M.pc_of(16*group+beat)
                assert pc not in responses
                responses[pc]=(tag,beat,bytes([16*group+beat])*32,0)
        m.step(responses)
    last_write_cycle=None
    for _ in range(100):
        before=m.landing.writes;cycle=m.landing.cycle;m.step()
        if m.landing.writes>before:last_write_cycle=cycle
    assert not m.pending and len(m.ring_lines)==32
    end=max(e['cycle'] for e in m.landing.delivered)
    data=b''.join(e['data'] for e in sorted(m.landing.delivered,key=lambda e:e['tag']))
    assert data==b''.join(bytes([i])*32 for i in range(128))
    return dict(bursts=8,sectors=128,delivered_lines=32,last_response_accept_cycle=3,
        last_bank_write_cycle=last_write_cycle,last_delivery_cycle=end,
        tail_after_last_bank_write=end-last_write_cycle,
        tail_after_last_response_accept=end-3,
        exact_bytes_sha256=hashlib.sha256(data).hexdigest(),
        scope='Actual32PC map into bank model; oneSM destination contention, no arbitrary external stall. Preissued/setup8cycles and HBM wait excluded.')


def admission_traces():
    rooms=[64]*32
    for pc in range(4):rooms[pc]=4
    shared=Counter({0:8});m=Admission(ports=2,groups=4,credits=shared)
    a=m.prepare(0,[0]*4,16);b=m.prepare(0,[0]*4,16)
    granted=m.admit([a,b],rooms)
    assert granted==[a] and not m.pending[b]['issued']
    high=Admission(ports=2,groups=4,credits=Counter({0:8}))
    c=high.prepare(0,[0]*4,32);d=high.prepare(16,[0]*4,32)
    assert high.admit([c,d],[64]*32)==[c,d]
    blocked=Admission(ports=1,credits=Counter({0:0}))
    attempts=1024
    for _ in range(attempts):assert blocked.prepare(0,[0],4) is None
    blocked.credits[0]=1;tag=blocked.prepare(0,[0],4);assert tag is not None
    return dict(overlapping_PC_requests=dict(prepared=2,simultaneously_granted=1,held_second=True),
        disjoint_PC_complementary_banks=dict(prepared=2,simultaneously_granted=2),
        finite_credit_counterexample=dict(fabric_admission_attempts_without_credit=attempts,
            equivalent_serial_cycles=math.ceil(Fraction(attempts*3,4)),eventually_credit_returned=True,
            assumption='No destination credit deadline is supplied. Counterexample disproves a bound from finiteness alone; it does not contradict a separately imposed450-cycle deadline.'),
        candidate_storage='One/two held requests use the previously priced50bit request holder per port; no new storage claimed free.',
        actual_two_port_hardware=False)


def build():
    p=json.loads(blob(PROVIDER_COMMIT,INPUT));cost=json.loads(blob(PROVIDER_COMMIT,COST))
    if (p['bounded_credit_wait_cycles'],p['loaded_HBM_ns'],p['landing_after_last_sector_cycles'])!=(450,500,3):
        raise ValueError('provider transport assumptions changed')
    if cost['Euler_input']['commit']!=BANK_COMMIT or cost['expanded_graph_input']['commit']!='0095fc4bc016ff1571e8316e836d5e522fc029e8':
        raise ValueError('provider bank/graph input changed')
    base=bank_tail();stalled=bank_tail(1024);admission=admission_traces()
    assert base['tail_after_bank_write_cycles']==3
    assert stalled['tail_serial_cycles_ceil']>450
    return dict(schema='opentallas.w19.HC22_transport_scope_and_burst_admission.v1',
        parent_provider_ack=dict(commit=PROVIDER_COMMIT,graph_commit=cost['expanded_graph_input']['commit'],
            bank_commit=BANK_COMMIT,measured=False,ready_to_build=False),
        historical_pins={path:dict(commit=commit,sha256=hashlib.sha256(blob(commit,path)).hexdigest()) for commit,path in
            [(PROVIDER_COMMIT,PROVIDER),(PROVIDER_COMMIT,INPUT),(PROVIDER_COMMIT,COST),(BANK_COMMIT,BANK)]},
        current_pins={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in
            ['tools/w19_burst_ingress.py','tools/w19_landing_banks.py','tools/w19_burst_admission.py',M.CTRL]},
        verdict=dict(credit_450='REJECT_AS_VALIDATED_UPPER_BOUND; retain only explicit isolated scenario assumption until destination/source progress deadlines and admission proof are supplied',
            bank_3='CONFIRM conditional3cycles after final bank write with delivery eligibility; reject as unconditional tail after controller response',
            HBM_500ns='ASSUMED_LOADED_LATENCY; not measured service or upper bound',
            provider='CONDITIONAL_HC22_MODEL_ONLY; no measured guarantee, no bound validation and no full-token/hardware credit'),
        pinned_bank_no_stall=base,pinned_bank_finite_stall_counterexample=stalled,
        actual32PC_single_destination=same_SM_trace(),burst_admission=admission,
        ceilings=dict(current_HC_one_line_controller_bytes_s=128*1200000000,
            proposed_existing_wire_full_burst_bytes_s=512*1200000000,
            proposed_two_port_bytes_s=1024*1200000000,actual_one_TB_credit=False),
        required_owner_contract=['Initial all-controller and endpoint drain/phase ownership',
            'Finite landing and immutable context reservation for every burst member',
            'Authoritative shared SM ring credits; consumer deadline, rawbuffer ready and CDC visibility deadline',
            'PC room and refresh/source-service bounds including joint multiport queue enqueue',
            'Bank arbitration/completion FIFO and rank destination contention bound',
            'HC raw/scatter/final-write completion fences and all32SM barriers'],
        allocation_or_model_generator_changed=False,historical_r1_changed=False,
        source_graph_pin_changed=False,enabled_default=False,new_RTL=False,new_PnR=False,
        ready_to_build=False,hardware_adopted=False,full_token_cycles=None)


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--out',type=Path);g.add_argument('--check',type=Path);a=p.parse_args();r=build()
    if a.check:
        if json.loads(a.check.read_text())!=r:raise ValueError('scope/admission receipt changed')
    else:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print('PASS finite trace scope;450-cycle guarantee REJECTED,3-cycle bank tail CONDITIONAL; no hardware credit')

if __name__=='__main__':main()
