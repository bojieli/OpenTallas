"""Finite downstream lease checker, independent of physical fragment encoding.

Events carry full model identity. This does not prove that any current wire
contains that identity or that a bounded physical provider supplies events.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path

class WordLease:
    def __init__(self, tag, epoch):
        if not 0 <= tag < 1 << 24 or not 0 <= epoch < 1 << 32:
            raise ValueError('identity aperture')
        self.tag,self.epoch=tag,epoch
        self.fragments={};self.stored=False;self.consumed=False;self.acked=False;self.released=False

    def fragment(self,tag,epoch,phase,data):
        if (tag,epoch)!=(self.tag,self.epoch) or self.released:
            raise ValueError('stale fragment identity')
        if phase not in (0,1) or phase in self.fragments or self.stored:
            raise ValueError('duplicate or invalid fragment')
        bits=224 if phase==0 else 40
        if not 0 <= data < 1 << bits:raise ValueError('fragment aperture')
        # One landing word, ordered two-fragment baseline. No reorder seat.
        if phase==1 and 0 not in self.fragments:raise ValueError('second before first')
        self.fragments[phase]=data

    def store(self):
        if self.stored or set(self.fragments)!={0,1}:raise ValueError('partial/duplicate store')
        self.stored=True
        return self.fragments[0] | (self.fragments[1] << 224)

    def consumer_accept(self):
        if not self.stored or self.consumed:raise ValueError('unstored/duplicate consumer acceptance')
        self.consumed=True

    def stored_ack(self,tag,epoch):
        if (tag,epoch)!=(self.tag,self.epoch) or not self.consumed or self.acked:
            raise ValueError('early/stale/duplicate stored ACK')
        self.acked=True

    def return_credit(self):
        if not self.acked or self.released:raise ValueError('early/duplicate credit')
        self.released=True

class RowLease:
    def __init__(self,epoch,tag_start):
        if tag_start+8 > 1 << 24:raise ValueError('tag wrap requires admitted global drain')
        self.words=[WordLease(tag_start+i,epoch) for i in range(8)]
        self.consumer_done=False;self.reverse_row_ack=False;self.released=False

    def row_consumer_done(self):
        if not all(w.released for w in self.words) or self.consumer_done:
            raise ValueError('missing word credits or duplicate row consumer')
        self.consumer_done=True

    def return_row_ack(self):
        if not self.consumer_done or self.reverse_row_ack:raise ValueError('early/duplicate row ACK')
        self.reverse_row_ack=True

    def release(self):
        if not self.reverse_row_ack or self.released:raise ValueError('early/duplicate row lease release')
        self.released=True

def build():
    sources={}
    for name,commit,path in [
        ('repacked_join','8af4e26af','results/quality/w16_w17_crom_finite_prefetch_20261001/repacked_constraint_join.json'),
        ('event_contract','c8ea5395d','results/quality/w16_engram_rom_constructive_home_20261001/repacked_192_enable_mask_contract.json')]:
        data=subprocess.check_output(['git','show',commit+':'+path])
        sources[name]=dict(commit=commit,path=path,sha256=hashlib.sha256(data).hexdigest())
    return dict(schema='opentallas.w17.Engram-fragment-credit-checker.v1',source_pins=sources,
        finite_seats=dict(assembly_words_per_endpoint=1,fragments_per_word=2,words_per_row=8),
        acceptance_order=['first fragment accepted','second matching fragment accepted',
            'complete264bit word stored','consumer accepts complete word','matching stored-word ACK',
            'reverse word credit','all8 word credits and final row consumer','reverse row ACK','row lease release'],
        preserved_unsafe_rule='READY or second-fragment capture as consumer credit is rejected.',
        model_identity_bits=dict(tag=24,epoch=32),
        identity_scope='Full model identity only; physical epoch/setup transport, all endpoints, allocator/no-wrap and reset drain require binding.',
        fragment_encoding_owner='Avicenna; checker does not encode wire words or price codec hardware.',
        physical_events_bound=False,physical_deadline=None,
        all_endpoint_state_clock_power_bound=False,physical_admission=False,
        full_token_latency=None,headline_rate=None,jobs_launched=0,checkpoint_reads=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
