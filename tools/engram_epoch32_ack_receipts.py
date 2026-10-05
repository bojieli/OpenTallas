"""Opt-in integer ACK receipt reference; not a wire/CDC provider."""
import hashlib
import json
import subprocess
from pathlib import Path
from engram_epoch32_fragment_contract import Hop, tag, response_encode, reject

class ReceiptHop(Hop):
    def __init__(self, t):
        super().__init__(t)
        self._events=[]
        self._consume_receipt=None
        self._request_clear_receipt=None

    def consume(self):
        word=super().consume()
        # Only the receiver's actual publication/consumption transition issues ACK1.
        self._consume_receipt=object()
        self._events.append((self.t, 1, self._consume_receipt))
        return word

    def observe_ack(self, *caller_levels):
        if caller_levels:
            raise ValueError('caller levels are not source receipts')
        if not self._events:
            raise ValueError('no captured source transition')
        identity,level,receipt=self._events[0]
        if identity!=self.t:
            raise ValueError('receipt identity mismatch')
        if level==1:
            if self.sender!=1 or receipt is not self._consume_receipt:
                raise ValueError('ACK1 lacks ordered consumed publication')
            self.sender=2
            self._request_clear_receipt=object()
        else:
            if self.sender!=2 or receipt is not self._request_clear_receipt:
                raise ValueError('ACK0 lacks source REQclear transition')
            self.sender=0
        self._events.pop(0)

    def peer_observe_request(self, *caller_levels):
        if caller_levels:
            raise ValueError('caller request levels are not source receipts')
        if self._request_clear_receipt is None or self.sender!=2:
            raise ValueError('no actual source REQclear receipt')
        if self.rxphase!=3 or not self.peer_ack:
            raise ValueError('no consumed ACK1 receiver transition')
        self.peer_ack=0
        self.rxphase=0
        self._events.append((self.t,0,self._request_clear_receipt))

    def reset(self, all_hops_drained):
        if self._events:
            raise ValueError('captured transitions not drained')
        super().reset(all_hops_drained)
        self._consume_receipt=None
        self._request_clear_receipt=None


def run():
    pin='9b5ca5767c4c03be4c587d77ad8c4ca8ff6f1f39'
    path='results/quality/w16_engram_eight_scale_binding_20261001/actual_rows.wire_beats.bin'
    raw=subprocess.check_output(['git','show',pin+':'+path])
    n=0;negative=0;digest=hashlib.sha256()
    for i in range(384):
        row,beat=divmod(i,8);layer,col=divmod(row,24)
        data=int.from_bytes(raw[33*i:33*(i+1)],'little')
        for epoch in (7,263,2**31-1,2**32-1):
            t=tag(epoch,col,layer,beat,3);h=ReceiptHop(t)
            h.start(0,True,True)
            negative+=reject(lambda:h.observe_ack(1))
            negative+=reject(lambda:h.observe_ack(0))
            negative+=reject(h.observe_ack)
            negative+=reject(h.peer_observe_request)
            f0,f1=response_encode(data,t);h.fragment(f0);h.fragment(f1)
            negative+=reject(h.observe_ack)
            word=h.consume();negative+=reject(h.consume)
            # Capture is held independently of current peer level. No current-level equality.
            assert len(h._events)==1 and h.sender==1
            captured=h._events[0]
            h._events[0]=(t^65536,captured[1],captured[2])
            negative+=reject(h.observe_ack)
            h._events[0]=(t,0,captured[2])
            negative+=reject(h.observe_ack)
            h._events[0]=captured
            h.observe_ack();assert h.sender==2
            negative+=reject(h.observe_ack)
            h.peer_observe_request();assert h.peer_ack==0 and h.sender==2
            negative+=reject(h.peer_observe_request)
            negative+=reject(lambda:h.reset(True))
            # Arbitrarily delayed delivery retains the source transition and identity.
            for _ in range(17): assert h.sender==2 and len(h._events)==1
            h.observe_ack();assert h.sender==0 and h.word==word
            negative+=reject(h.observe_ack)
            negative+=reject(h.consume)
            h.reset(True)
            digest.update(word.to_bytes(39,'little'));n+=1
    out=dict(schema='opentallas.engram.ordered-source-ACK-receipts.v1',
        status='PASS_LOCAL_REFERENCE_RECEIPTS_NOT_TRANSPORT_PROVIDER',
        failure_preserved_commit='94f21a11e6aa59ce39424ea89f61d0d6fad8a4d5',
        prior_reference_source='50ebbce7cf42821b936c11de69fb7a458273a8d7',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        fixture=dict(commit=pin,path=path,sha256=hashlib.sha256(raw).hexdigest()),
        gate=dict(words=n,negative_rejections=negative,word_sha256=digest.hexdigest(),delayed_ACK0_reference_steps=17),
        authority='Receiver consume publishes immutable ACK1 receipt; source ordered observation creates REQclear receipt; receiver accepts that transition and publishes ACK0. Observation takes no caller level. Captured identity and ordering survive delivery delay; current peer_ack equality is not used.',
        scope='Python object capabilities are reference provenance ONLY, not hardware authentication, CDC, link ordering or full endpoint context.',
        proposed_capture_storage=dict(depth=2,entry_tag_bits=48,entry_level_bits=1,queue_pointer_occupancy_bits=3,extra_FF_per_hop=101,paired_hops_per_home=24928,homes=192,extra_FF_total=101*24928*192,prior_FF_total=4361491198,new_provisional_FF_total=4361491198+101*24928*192,
            exclusions='Full word27,row29,shard,image256 endpoint comparisons; capture FIFO reset/online/CDC control, gates, CTS, route and return bandwidth remain unbound. 101 is a provisional storage lower bound, not a complete implementation inventory.'),
        full_endpoint_context_provider=None,all_hop_drain_provider=None,actual_ordered_ACK_transport_provider=None,
        start_drain_and_image_booleans='Retained legacy assumptions ONLY; no admission credit. This companion fixes ACK caller authority, not setup/drain.',
        L1_generated_source=None,checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False)
    dest=Path('results/quality/w16_engram_rom_constructive_home_20261001/epoch32_ACK_source_receipts.json')
    assert not dest.exists();dest.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out['gate']))

if __name__=='__main__':run()
