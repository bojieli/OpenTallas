#!/usr/bin/env python3
"""Finite future adapter specification; original producer has no such ports."""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
PRODUCER='rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv'
GAP_COMMIT='9d42d5da8a4f5cf36d4e04668c6894eb9d9f37b4'
GAP='results/uarch/w17_window_qdq8_producer_freeze_cancel_gap_20261002/model.json'

@dataclass
class Adapter:
    """One operation, 16 QE outputs, at most one accepted WINDOW block.

    Fault is sampled before NEW admissions at an edge. Earlier accepted
    transfers remain owned. No arithmetic/payload/provider is invented here.
    """
    generation: int
    issued: bool=False
    remaining: int=0
    resident: int=0
    discarded: int=0
    delivered: int=0
    frozen: bool=False
    cancel_ack: bool=False
    qe_tail_done: bool=False
    intents: dict=field(default_factory=dict)
    accepted_window_block: int | None=None

    def qe_accept(self):
        if self.frozen or self.issued:raise ValueError('QE admission forbidden')
        self.issued=True;self.remaining=16

    def capture(self, generation):
        if generation!=self.generation or not self.issued or self.remaining==0:
            raise ValueError('stale or duplicate QE output; provenance uncertified')
        self.remaining-=1
        if self.frozen:self.discarded+=1
        else:self.resident+=1

    def window_accept(self, block):
        if self.frozen or self.resident!=16 or self.accepted_window_block is not None:
            raise ValueError('new block forbidden or owner busy')
        if block!=self.delivered or block>=16:raise ValueError('block sequence')
        self.accepted_window_block=block
        for kind in ('WC','WS'):self.intents[(self.generation,block,kind)]='accepted'
        self.delivered+=1

    def issue_write(self, identity):
        if self.intents.get(identity)!='accepted':raise ValueError('unowned write issue')
        self.intents[identity]='issued'

    def ack_write(self, identity):
        if self.intents.get(identity)!='issued':raise ValueError('ACK without issue')
        self.intents[identity]='acked'

    def complete_block(self):
        b=self.accepted_window_block
        if b is None or any(self.intents[(self.generation,b,k)]!='acked' for k in ('WC','WS')):
            raise ValueError('WC/WS accepted intent must drain')
        self.accepted_window_block=None

    def fault(self):self.frozen=True

    def qe_idle_receipt(self):
        if self.remaining:raise ValueError('QE suffix still owned')
        self.qe_tail_done=True

    def cancel_local(self):
        if not self.frozen or not self.qe_tail_done or self.remaining:
            raise ValueError('local cancel before fixed-latency suffix closure')
        if self.cancel_ack:raise ValueError('duplicate cancel')
        # Cancels only producer-resident content; accepted WINDOW intent stays.
        self.resident=0;self.cancel_ack=True

    def restart(self, *, read_empty, selected_write_empty, delivery_fence, visibility_fence, provenance):
        if not (self.frozen and self.cancel_ack and self.qe_tail_done and
                self.accepted_window_block is None and
                all(v=='acked' for v in self.intents.values()) and read_empty and
                selected_write_empty and delivery_fence and visibility_fence and provenance):
            raise ValueError('restart forbidden until selected-owner quiescence')
        return self.generation+1


def record():
    read=lambda c,p:subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
    producer=read(SOURCE,PRODUCER);gap=read(GAP_COMMIT,GAP);g=json.loads(gap)
    assert hashlib.sha256(producer).hexdigest()==g['source_sha256']
    witnesses=[]
    # Every FILL boundary, FULL boundary and no-QE suffix case.
    for prefix in range(17):
        a=Adapter(1);a.qe_accept()
        for _ in range(prefix):a.capture(1)
        a.fault()
        for _ in range(16-prefix):a.capture(1)
        a.qe_idle_receipt();a.cancel_local()
        assert a.restart(read_empty=True,selected_write_empty=True,delivery_fence=True,visibility_fence=True,provenance=True)==2
        witnesses.append({'fault_after_captures':prefix,'fixed_QE_suffix_discarded':a.discarded,'resident_cancelled':prefix})
    return {'schema':'opentallas.selected_producer.cancel_adapter.v1','status':'MODEL_ONLY_UNIMPLEMENTED_NO_GO_NO_RTL',
      'source_commit':SOURCE,'producer_path':PRODUCER,'producer_sha256':hashlib.sha256(producer).hexdigest(),
      'gap_commit':GAP_COMMIT,'gap_sha256':hashlib.sha256(gap).hexdigest(),'WIN_STACK':2,
      'finite_contract':{'QE_operations':1,'outputs_per_QE':16,'WINDOW_accepted_blocks_at_once':1,'accepted_write_intents_per_block':2,'fault_edge':'freeze new cap/issue/blk/descriptor admissions; already accepted transfer remains owned','fixed_QE_suffix':'sink/drop every already-issued output without backpressure, preserve fault; wait source-bound QE idle after last output','local_cancel':'new explicit producer metadata clear-to-EMPTY only after suffix closure; not rst_n and no payload zeroing','write_drain':'retain accepted block WC then WS even after fault; never cancel downstream accepted intent','restart':'producer cancel_ack + QE suffix idle + WINDOW empty + selected mux/KARB/backend ownership zero + certified delivery and visibility fences + valid provenance','closed_identity_assumption':'One closed QE operation; observation generation is not on wire. Real QE has no per-output generation; restart only after complete old suffix. Hostile same-wire output cannot be detected without provider identity.'},
      'source_bound_timing':g['bounded_QE_lifetime'],
      'candidate_interface':{'inputs':['freeze','cancel_request','QE_suffix_closed','selected_owner_quiescent','certified_fence'], 'outputs':['local_cancel_ack','producer_frozen'], 'replicas':1,'additional_control_bits_estimate':19,'bits_detail':'5 suffix count +5 delivered count +5 discarded count +2 state +freeze1 +cancel_ack1; diagnostics may remain model-only','healthy_added_stages':0,'healthy_guard_cycles':0,'area_dff_estimate_um2':19*0.2916,'route_control_bits_proxy':7,'payload_bits_added':0,'clock_reset':'actual producer clk/rst_n streaming domain; new local cancel must not reset mux/backend or another owner','latency':'<=16 remaining capture outputs + source QE idle tail + local cancel acknowledgement; accepted WR/read/fence latency requires bounded external service fairness, no numerical PHY drain bound assigned','slot_and_enable_gate_area':'UNPRICED; model count only, no floorplan/SSFF/adoption'},
      'boundary_witnesses':witnesses,'remaining_gaps':['Actual producer cancel/freeze ports and QE suffix adapter absent.','Bounded external delivery/visibility fence provider absent; projected idx deadline not PHY.','Asynchronous/global reset during ownership forbidden; no reset erases accepted downstream intents.','Payload and arithmetic unchanged; no new provider or hardware implementation.']}

if __name__=='__main__':print(json.dumps(record(),indent=2))
