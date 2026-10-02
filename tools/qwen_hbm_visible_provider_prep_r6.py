#!/usr/bin/env python3
"""Conventional controller model preparation, never RTL/hardware admission.

Observed baseline times are evidence only. Counterfactual queue costs below
are explicit source-clock candidates, not replayed actual legal commands.
"""
import argparse
from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from qwen_hbm_controller_events_r1 import (Beat, ROOT, REV, MACRO, pinned,
    source_timing, queue_port_schedule)
from qwen_hbm_provider_prep_r3 import read_journal

OBS='952dc10e76d5b1eb7df2cbb7ad711fbf80630b05'
OBS_DIR='results/rtl/qwen_hbm_provider_observation_r5_20261002'

@dataclass(frozen=True)
class Residence:
    request: Beat
    column_ps: int | None = None
    visible_ps: int | None = None
    committed: bool = False
    phase: int = 0

class VisibleProvider:
    """Four write reservations/stack, retained through reverse credit.

    Full-address sparse backing is an oracle for external HBM, not silicon
    SRAM capacity. Explicit downstream events are experiment inputs. This
    model has no fabricated completion pulse, CDC latency or drain credit.
    """
    def __init__(self,timing,depth=4):
        if depth!=4:raise ValueError('reviewed finite depth4')
        self.t=timing;self.slots={};self.backing={};self.held=None;self.now=0
    @staticmethod
    def identity(b):return (b.tag,b.producer_epoch,b.transport_epoch,b.beat)
    def reserve(self,b,now):
        self.advance(now)
        if not b.write or not 0<=b.addr<1<<34:raise ValueError('WR/fullAW34 required')
        k=self.identity(b)
        if k in self.slots:raise ValueError('identity reuse')
        if len(self.slots)==4 or any(p.request.addr==b.addr for p in self.slots.values()):return False
        self.slots[k]=Residence(b);return True
    def column(self,b,now):
        self.advance(now);k=self.identity(b)
        if k not in self.slots:raise ValueError('reserve before column/head pop')
        p=self.slots[k]
        if p.request!=b:raise ValueError('immutable reservation identity')
        if p.column_ps is not None or now<b.accepted_ps+self.t['REQ_PS']:raise ValueError('causal single column')
        self.slots[k]=replace(p,column_ps=now,visible_ps=now+self.t['CWL_PS']+self.t['BURST_PS'])
    def advance(self,now):
        if now<self.now:raise ValueError('time reversal')
        self.now=now
        for k,p in list(self.slots.items()):
            if not p.committed and p.visible_ps is not None and p.visible_ps<=now:
                self.backing[p.request.addr]=p.request.data;self.slots[k]=replace(p,committed=True)
    def read(self,addr,now):
        self.advance(now)
        if not 0<=addr<1<<34:raise ValueError('fullAW34')
        if any(p.request.addr==addr and not p.committed for p in self.slots.values()):return None
        return self.backing.get(addr,0)
    def offer(self,now):
        self.advance(now)
        if self.held is None:
            ready=[p for p in self.slots.values() if p.committed and p.phase==0]
            if ready:self.held=min(ready,key=lambda p:(p.visible_ps,self.identity(p.request)))
        return self.held
    def capture(self,now,ready):
        p=self.offer(now)
        if p is None or not ready:return None
        self.slots[self.identity(p.request)]=replace(p,phase=1);self.held=None;return p
    def downstream(self,b,event):
        k=self.identity(b);p=self.slots[k]
        if p.request!=b:raise ValueError('immutable reservation identity')
        expected={1:'forward_CDC',2:'completion_store',3:'consumer_retire',4:'reverse_credit'}
        if expected.get(p.phase)!=event:raise ValueError('finite lifecycle order')
        if event=='reverse_credit':del self.slots[k]
        else:self.slots[k]=replace(p,phase=p.phase+1)
    def drained(self):return not self.slots and self.held is None


def derive(repo=ROOT):
    root=Path(repo)/OBS_DIR
    # No current mutable record can silently replace the committed observation.
    for name in ['case1.tsv','review_r5.json']:
        assert (root/name).read_bytes()==pinned(repo,OBS,OBS_DIR+'/'+name)
    parent_path='results/rtl/parent_actual_hbm_observation_witnesses_20261002.json'
    parent_raw=pinned(repo,'5e3b8773f07e08907c267768b7533baa2603a187',parent_path)
    parent=json.loads(parent_raw)
    for name,digest in parent['artifact_pins'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    t=source_timing(repo);q=[[] for _ in range(32)];reorders=[]
    for e in read_journal(root/'case1.tsv'):
        k=(e['tag'],e['beat']);p=e['pc']
        if e['kind']=='ENQUEUE_RD':q[p].append(k)
        if e['kind']=='REORDER':
            index=q[p].index(k);edges=len(queue_port_schedule(index))
            reorders.append(dict(tag=e['tag'],selected_index=index,queue_entries=len(q[p]),observe_ps=e['observe_ps'],source_arrival_ps=e['arrival_ps'],scan_shift_edges=edges,isolated_scan_start_ps=e['observe_ps'],isolated_reservation_ready_ps=e['observe_ps']+edges*t['CLK_PS'],scope='Isolated conventional-stage preparation from actual selected index. Loaded new scheduling requires a finite provider experiment; second observed swap is not replayed concurrently.'))
            q[p].insert(0,q[p].pop(index))
        if e['kind']=='RETURN_ENQUEUE':assert q[p].pop(0)==k
    macro=json.loads(pinned(repo,REV,MACRO+'.json'))
    base=json.loads(pinned(repo,'7bc0a87578d8a65f64e390acd1bfbfb588d0b9d1','results/uarch/qwen_hbm_controller_events_20261001/model_r1.json'))
    pcs=8*32
    # One active conventional command chain per PC; source q entry snapshot
    # already has both epochs. No free additional port into queue macros.
    command_context=dict(request_snapshot=472,phase=3,reservation_slot=2,reservation_valid=1,next_command_ps=64)
    context_width=sum(command_context.values())
    # Existing468b pending row becomes independent column/visibility/lifecycle
    # record. Keep payload/address until reverse credit, even after ACK capture.
    pending_add_fields=dict(column_ps=64,lifecycle_phase=3,beat=5)
    extra_pending=8*4*sum(pending_add_fields.values())
    completion_width=1+34+16+5+96+64
    held_bits=8*(completion_width+2)
    added=pcs*context_width+extra_pending+held_bits
    proxy=Fraction(2916,10000)/Fraction(1,2)/1000000
    model=dict(schema='Qwen_conventional_command_fulladdress_visible_provider_preparation_r6',status='MODEL_PREPARATION_NOT_CONTROLLER_RTL_ADMISSION',observed_commit=OBS,
        parent_independent_witness=dict(commit='5e3b8773f07e08907c267768b7533baa2603a187',path=parent_path,sha256=hashlib.sha256(parent_raw).hexdigest(),all_artifact_hashes_match=True),
        actual_WR_bound_comparisons=[dict(case=c['case'],tag=int(w['tag']),column_ps=w['column_ps'],backing_ps=w['backing_ps'],elapsed_ps=w['elapsed_from_column_ps'],required_minimum_ps=t['CWL_PS']+t['BURST_PS'],early_by_ps=t['CWL_PS']+t['BURST_PS']-w['elapsed_from_column_ps'],verdict='FAIL_AS_WR_VISIBLE_PROVIDER') for c in parent['cases'] for w in c['backing_store_elapsed_from_WR_column']],
        source_timing_ps=t,clock_scope='Explicit source preset1000ps candidate; no universal clock or SS/FF qualification',
        geometry=dict(NPC=32,QD=64,RQD=32,AW=34,TAGW=16,LENW=6,BEATW=5,dies=2,stacks_per_die=4,pending_WR_per_stack=4),
        inherited_queue_inventory=base['memory_macro_candidate'],
        additional_to_r1_control=dict(command_context_fields=command_context,context_width=context_width,PC_contexts=pcs,context_bits=pcs*context_width,pending_add_fields=pending_add_fields,pending_add_bits=extra_pending,held_WR_completion_width=completion_width,held_WR_completion_bits=held_bits,total_bits=added,FF_area_proxy_mm2=float(added*proxy)),
        subset_area=dict(queue_macro_count=512,queue_macro_mm2=base['memory_macro_candidate']['macro_area_total_mm2'],queue_and_r1_r6_control_proxy_mm2=base['memory_macro_candidate']['macro_plus_new_control_subset_mm2']+float(added*proxy),per_die_subset_proxy_mm2=(base['memory_macro_candidate']['macro_plus_new_control_subset_mm2']+float(added*proxy))/2,slot_fit=False,exclusions=['Inherited bank/timing control, common36, CDC queues, PHY, routing and clocktree.','FF proxy is analytical; memory abstracts do not establish physical signoff.']),
        queue_ports=dict(request_macros=256,return_macros=256,per_macro_ports='1R1W, registered read',scan_shift_edges=[18,35],PC_frozen_during_scan=True,head_advance_prefetch_edges=1,empty_enqueue_read_oldword_prefetch_edges=2,
            conventional_PC_contexts_per_stack=32,bank_timer_replicas_total=8192,pending_RAW_comparators_per_candidate=4,RAW_address_compare_bits_total=8*32*4*34,
            one_locked_read_arbiter_per_stack=dict(inputs=32,payload_bits=471,two_input_mux_nodes=31,outputs=1),one_locked_WR_visible_arbiter_per_stack=dict(inputs=4,payload_bits=completion_width,two_input_mux_nodes=3,outputs=1),
            logical_bank_command_address_bus_bits_per_PC=3+5+19,physical_command_mapping='Unbound HBM PHY channel lowering; this27-bit logical demand is not a qualified HBM pin interface.'),
        address_residence=dict(fullAW_sector_bits=34,sector_payload_bytes=32,address_span_bytes=(1<<34)*32,resident_pending_rows=32,resident_pending_payload_bytes=32*32,backing='External HBM logical sector identity; Python sparse dictionary only test oracle. Never allocate512GiB as controller SRAM or alias modulo4096.',memorymacro='Pending/control as sized FF proxy; request/return queues use pinned64x5121R1W candidate,512 total. No new macro port is assumed.'),
        event_contract=['accept snapshot immutable producer64+transport32','freeze PC18..35 scan/shift; charge head-prefetch bubbles','reserve pending WR or return capacity BEFORE any bank command/head pop','one conventional command chain/PC, emit at current explicit edge; held command under ready backpressure','autonomous current-time refresh fences PC and waits all open-bank recovery,PREall,tRP,REF,tRFC','ACT/PRE/column legality independently checked at actual emitted timestamp; no retrospective state mutation','WR column -> CWL+burst -> fulladdress backing commit -> immutable held-visible record','RAW waits for exact fulladdress commit; WAW cannot pass resident older sameaddress WR','ACKcapture -> forwardCDC -> completion_store -> consumer_retire -> reversecredit releases WRslot','drain includes contexts/reservations/heldread+WR/CDC/RMW/lease/consumer and bothdie return-zero'],
        composed_dependency_expression=dict(command_ready='max(request_accept+REQ, frozen_scan_shift_complete, capacity_reservation_ready, RAW_WAW_ready, bank_recovery, refresh_complete, command_port_ready)',column='max(command_ready, emitted_ACT+tRCD, tCCD/burst constraints, read/write turnarounds)',backing_visible='WR_column+CWL+burst',completion='max(backing_visible, held_visible_arbiter_ready, ACK_capture_capacity)',publication='max(all finite completions after forwardCDC/store/consumer_retire/reversecredit)',reader='max(publication, reader_lease_acquire, read_command_ready)',critical_path='Dependency maxima over the event DAG, never sum overlapping work floors.'),
        actual_reorder_stage_costs=reorders,known_visibility_tail_ps=t['CWL_PS']+t['BURST_PS'],
        next_finite_provider_experiment=dict(source_changes_after_model_review=['Conventional accepted-command interface and current-refresh scheduler with finite registered contexts.','FullAW34 oracle/address identity and pre-command WRreservation; delayed backing+held-visible record.','Connect held ready/valid consumer contract; never fabricate WRdone pulse.'],metadata='Same pinned actual-address subset and recorded weight addresses, synthetic marker only; retained loaded phase/provider must be measured.',journal_fields='accepted identity, scan start/end/selection, reservation slot, actual command valid/ready timestamp, bank state, fulladdress commit, held-visible valid/ready, CDC/store/retire/reversecredit/drain',admission=False),
        exact_blockers=['Actual command port service, bank-state timer widths/wrap and independent autonomous refresh implementation remain unmeasured.','ACK/CDC/RMW/lease providers require exact finite clock/phase contracts; current r5 bench has neither WRvisible nor postWR KVread stage.','Loaded queue ranking changes after18..35 hardware scan and command residence; baseline timestamps cannot be replayed as a repaired controller.','Actual1737 issue/RF/shared/NoC stage dependencies and weight phase arbitration remain unbound.','Channel capacity, total slot fit and SSsetup/FFhold remain unqualified.'],
        parent_epoch_proof='Do not duplicate; conservative64+32 retained, no epoch narrowing.',hardware_build_ready=False,provider_PASS=False,hardware_rate_credit=0,fullprogram_execution=False)
    return model

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with a.output.open('x') as f:json.dump(derive(),f,indent=2,sort_keys=True);f.write('\n')
