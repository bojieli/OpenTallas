#!/usr/bin/env python3
"""One source-gated word dispatch contract after rejecting credit17.

Model only. Actual destination dependency/visibility journal and finite replay
must precede a physical delta. No group/tag/ACK early release is presumed.
"""
import json
from pathlib import Path
import uarch_model as BASELINE
import qwen_rom_kv_credit17_physical as P
R=P.R
OUT=Path('results/uarch/qwen_rom_kv_dispatch_after_rejection_20261003')


class WordDispatch:
    """Held source-owned member IDs; visibility follows accepted capture.

    This state machine validates a supplied exact dependency map. It does not
    invent that map or turn caller fixtures into production source evidence.
    """
    def __init__(self,epoch,word_members):
        if not word_members or any(not v for v in word_members.values()):raise ValueError('complete dependency map')
        self.epoch=epoch;self.requires={w:frozenset(v) for w,v in word_members.items()}
        self.captured=set();self.visible=set();self.acked=set();self.readers={w:0 for w in self.requires}
        self.identity=frozenset(m for v in self.requires.values() for m in v)

    def capture(self,epoch,member,accepted):
        if epoch!=self.epoch or member not in self.identity or member in self.captured:raise ValueError('owned identity/duplicate')
        if accepted:self.captured.add(member)

    def dispatchable(self,word):return self.requires[word]<=self.captured and word not in self.visible

    def commit(self,epoch,word,masked_write_visible):
        if epoch!=self.epoch or not self.dispatchable(word):raise ValueError('not source-ready')
        if masked_write_visible:self.visible.add(word)

    def grantable(self,member):
        words=[w for w,v in self.requires.items() if member in v]
        return member in self.captured and member not in self.acked and all(w in self.visible and self.readers[w]==0 for w in words)

    def ack(self,epoch,member,accepted_reverse):
        if epoch!=self.epoch or not self.grantable(member):raise ValueError('owned visible/drained identity')
        if accepted_reverse:self.acked.add(member)

    def cohort_retirable(self):return self.acked==self.identity and all(n==0 for n in self.readers.values())


def build():
    failed=R.obj(OUT/'inputs/peer-contract-receipt-r1.json')
    old=R.obj(OUT/'inputs/model-r3.json')
    assert failed['conditional_us']==358.6013 and failed['gain_fraction']<.01
    context=R.obj(P.OUT/'inputs/model-r7.json')['cells']
    ff=context['ASR_area_um2']+context['INV_area_um2'];gate=3*context['AND3_area_um2']+5*context['INV_area_um2']
    #Gross additional ready/visible/read-lease/epoch controls. Existing data,
    #four selection stages,128headers/64pending/80word pools retained once.
    word_controls=56*80*(32+1+1+2)
    member_controls=128*32*(1+1)
    counts=word_controls+member_controls
    compare_bits=56*80*32
    collectors=2*56*P.tree(80*36)+2*8*P.tree(16*32*2)
    known=(counts*ff+compare_bits*gate+collectors*context['BUF_area_um2'])/1e6
    return dict(schema='QROM_REJECT17_ONE_WORD_READY_DISPATCH_CONTRACT_R2',
        parent_ready_commit='78c1e4f4c',Russell_rejection_commit='61c72fb3a',
        rejected=dict(credit17=True,conditional_us=failed['conditional_us'],gain_fraction=failed['gain_fraction'],
            service_increment_mm2=old['cells']['delta_known_mm2'],
            admission='REJECTED_NO_HARDENING_BUILD',original_model_sha256=R.sha(OUT/'inputs/model-r3.json')),
        one_candidate='source-owned per-word readiness dispatch within existing16/128 credit topology',
        default_enabled=False,topology=dict(return_groups=8,column_paths=4,fill_lanes=7,
            group_credits=16,global_credits=128,pending_per_PC=64,pools=56,words_per_pool=80,
            context_RAM_replicas_added=0,PHY_replicas_added=0,lookup_edges=12),
        semantics=dict(word_ready='all required immutable source members accepted and captured',
            word_visible='actual complete masked macro write/capture accepted',
            beat_ACK='every word touched by this physical tag/beat is visible and has no reader lease; reverse credit accepted',
            tag_retire='source same-tag remaining_PC update and owned consume only',
            cohort_reuse='all member ACKs accepted and reader debt discharged',
            ready_selection_edges=4,additional_registered_predicate_edges=1,
            source_epoch_abort='stale epochs rejected; abort drains held data/ACK/reader debt before reuse'),
        justification=dict(source_write_adapter='FILL waits complete byte mask; local masked writes need no full-cohort completion signal',
            source_provider='credit_id/tag/beat/epoch checked at owned credit acceptance; physical tag and write ownership retained',
            model_barrier='frozen allocator waits max all-member readiness before any destination word dispatch',
            qualification='These anchors justify modeling per-word dispatch. Exact producer dependency map and earlier arrival times remain unobserved.'),
        gross_control_price=dict(FFs=counts,word_FFs=word_controls,member_FFs=member_controls,
            equality_bits=compare_bits,collector_buffers=collectors,known_mm2=known,
            source_sized_not_mapped=True,source_gate_and_protection_binding_complete=False,
            route_PG_hold_slew_and_clock_price_complete=False),
        source_pins={str(p.relative_to(R.ROOT)):R.sha(p.relative_to(R.ROOT)) for p in (R.ROOT/OUT/'inputs').iterdir()},
        finite_calendar_s=None,gain_fraction=None,candidate_replayed=False,
        dispatch_dependency_source_bound=False,actual_PHY_sustained_Bps=None,
        physical_delta_authorized=False,build_admission=False,
        required_Russell_replay='ONE16/128/64/80 same8/4/7 calendar; dispatch only exact-source ready words, price extra predicate edge, preserve owner DATA/GRANT contention, strict refresh and all final drains. Reject if below1percent or fails contextualSSFF.',
        required_Euclid_source='Accepted member-to-word quarter/mask dependencies, actual capture/visibility events, copy-reader leases, reverse404ACK/tag-retire and currentV prefix; no invented early payload.',
        named_baseline_physical_obligations=['7973fill/control tracks','43256boundary bits including804untyped',
            'four nativePHY pins/controller protocol and sustainable113.135616GB/s perstack',
            'complete source clock/reset/PG/hold and ACK characterization'],
        prior_cost_route_receipts='17credit physical/route records retained as rejected candidate history; not a baseline area/CTS admission',
        status='MODEL_CONTRACT_ONLY_REPLAY_AND_SOURCE_BINDING_REQUIRED')


if __name__=='__main__':
    p=R.ROOT/OUT/'model-r2.json'
    if p.exists():raise ValueError('preserve verdict')
    P.C.Q.M.write(p,build())
