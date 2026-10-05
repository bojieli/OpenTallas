"""Reachability of ddc stop/wait receipts; source CDC inventory, no hardware admission."""
import copy
import hashlib
import json
import subprocess
from collections import deque
from pathlib import Path
from engram_epoch32_ack_receipts import ReceiptHop
from engram_epoch32_fragment_contract import tag,response_encode

def signature(h):
    return (h.sender,h.rxphase,h.peer_ack,h.first is not None,h.word is not None,
            tuple((t,level,receipt is h._consume_receipt,receipt is h._request_clear_receipt)
                  for t,level,receipt in h._events),
            h._consume_receipt is not None,h._request_clear_receipt is not None)

def run():
    t=tag(7,0,0,0,3);f0,f1=response_encode(123,t)
    initial=ReceiptHop(t);pending=deque([(initial,[])])
    seen={signature(initial)};edges=[];maximum=0;witness=None
    while pending:
        h,trace=pending.popleft()
        assert len(h._events)<=1
        maximum=max(maximum,len(h._events))
        if len(h._events)==1 and witness is None:witness=trace
        actions=[('start',lambda x:x.start(0,True,True)),
                 ('fragment0',lambda x:x.fragment(f0)),('fragment1',lambda x:x.fragment(f1)),
                 ('consume',lambda x:x.consume()),('observe_ack',lambda x:x.observe_ack()),
                 ('peer_observe_clear',lambda x:x.peer_observe_request()),
                 ('reset_assumed_drained',lambda x:x.reset(True))]
        for name,action in actions:
            new=copy.deepcopy(h)
            try:action(new)
            except ValueError:continue
            assert len(new._events)<=1
            before=signature(h);after=signature(new)
            edges.append(dict(action=name,before=list(before[:5]),after=list(after[:5]),
                              occupancy_before=len(h._events),occupancy_after=len(new._events)))
            if after not in seen:seen.add(after);pending.append((new,trace+[name]))
    assert maximum==1
    sourcepin='1fa3b30f088eea87a801605ba22a276835214b5e'
    sourcepath='rtl/lib/ot_cdc_mailbox.sv'
    raw=subprocess.check_output(['git','show',sourcepin+':'+sourcepath])
    out=dict(schema='opentallas.engram.ACK-reference-occupancy-and-source-CDC.v1',
        reference_pin='ddc93f3789ef2b3b7d1313a5512797334a3a3f3f',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reachable_signature_count=len(seen),valid_transition_count=len(edges),maximum_pending_receipts=maximum,
        occupancy_one_witness=witness,transitions=edges,
        proof=['Only consume and peer_observe_request append.',
               'Consume moves FULL to DRAIN so cannot append twice; ACK1 is the sole pending event.',
               'observe_ack pops ACK1 atomically before the modeled REQclear event can be delivered.',
               'peer_observe_request requires that clear event and consumed receiver, then clears peerACK and RXphase, excluding duplicate ACK0 append.',
               'observe_ack pops ACK0 before sender IDLE permits next start; reset rejects a nonempty queue.',
               'Thus occupancy <=1 is inductive in the sequential reference transition system, including idle delays and reuse. Atomicity here is a software contract, not an asynchronous hardware proof.'],
        correction=dict(prior_101FF_label='Incorrectly called a lower bound in ddc evidence; retain original immutable record.',
            corrected_label='Conditional chosen depth-two reservation, NOT architecture minimum.',
            prior_power_ref='e851c57ae',power_scope='Refusal applies to the conditional depth-two reservation; it establishes no minimal-architecture infeasibility.',
            minimum_actual_extra_FF=None,tag_deduplication_credit=False,
            reason='Locked tag48 may bind level ACKs only with actual immutable endpoint context, ordered four-phase wire, reset and drain proof. Python object receipts are not extra hardware cells or free hardware comparators.'),
        actual_source=dict(commit=sourcepin,path=sourcepath,sha256=hashlib.sha256(raw).hexdigest(),
            instantiated_Engram_binding=None,
            FF_recipe='payload_hold WIDTH + payload_capture WIDTH + response_hold RESPONSE_W + src_response RESPONSE_W +15 scalar FF',
            scalar_source8=['request_level','source_waiting','source_online','ack_sync1','ack_sync2','dst_online_sync1','dst_online_sync2','src_done'],
            scalar_destination7=['acknowledge_level','destination_valid','destination_online','request_sync1','request_sync2','src_online_sync1','src_online_sync2'],
            generic_75request_48response_FF=261,
            duplication_credit=None,
            ordered_event_binding='Destination ready captures response and raises held ACK1; source synchronizes ACK1 and captures held response while clearing REQ; destination synchronizes REQ0 before lowering ACK; source_ready requires synchronized ACK0. src_done at ACK1 is NOT reusable credit.',
            reset_limitation='Destination reset may replay an outstanding request. Exactly-once irreversible row consumption needs shared reset or idempotence/retirement protocol; absent for Engram.',
            timing_aligned_settled_equal_clock=dict(src_accept=0,request_sync1=1,request_sync2=2,destination_capture=3,destination_consume_ACK1=4,ack_sync1=5,ack_sync2=6,src_done_REQ0=7,request_sync1_zero=8,request_sync2_zero=9,destination_ACK0=10,ack_sync1_zero=11,ack_sync2_zero_ready=12,next_src_accept=13),
            timing_scope='Illustrative exact nonblocking-register edge calendar with settled online state and immediately ready destination. Clock phase/ratio, CDC uncertainty, setup/hold/route and Engram placement remain unbound; no latency admission.'),
        required_actual_inventory=['Source-owned final word/row consumer acceptance publication and locked word27,row29,shard,imageSHA,E32 context.',
            'Every per-hop ACK/REQ synchronizer/capture/holding register, online/reset state, feedback enable, comparator and serializer gate with actual instantiation.',
            'Ordered transport return-to-zero and finite reset/replay protection; all-hop backend/queue/consumer drain certificate.',
            'Full source register calendar, CDC phase bounds, routed control/return bandwidth and CTS/data costs.'],
        actual_capture_CDC_extra_FF=None,all_hop_drain_provider=None,L1_generated_source=None,
        checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False)
    path=Path('results/quality/w16_engram_rom_constructive_home_20261001/ACK_capture_occupancy_and_CDC.json')
    assert not path.exists();path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(states=len(seen),edges=len(edges),maximum=maximum,sha256=hashlib.sha256(path.read_bytes()).hexdigest())))

if __name__=='__main__':run()
