#!/usr/bin/env python3
"""Source-pinned finite producer cancellation contract; no RTL or timer fence."""
import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = '4e38326d6f361bc85e660f48c59c355e2bb95274'
SOURCES = (
    'rtl/hdc/v41/ot_hdc_v41_qe.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv',
    'rtl/hdc/v41x/ot_hdc_core_v41x.sv',
    'rtl/chip/ot_chip_v41x_window_block_guard.sv',
    'rtl/chip/ot_chip_v41x_window_kv_prefetch.sv',
    'rtl/chip/ot_chip_v41x_kv_reqmux.sv',
    'rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv',
    'rtl/chip/ot_chip_v41x_hbm_karb.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',
)
EVIDENCE = 'results/rtl/w17_window_qdq8_connected_startup_single_run_20261002'
PEIRCE = '2f208e1b8732daa57de0eb073697368464d4c0a8'
PEIRCE_PATH = 'results/uarch/w17_window_recovery_output_phase_preparation_20261002/producer_cancel_adapter_model.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class CancelLedger:
    """Proposed serial-row contract, NOT a transcription of current faulty RTL.

    QE terminal events count valid OR poison/fault outputs. Consumer ready never
    gates those events or accepted-work retirement. Provider grant/fairness is
    still required; arbitrary provider stalling has no finite time bound.
    """
    context: tuple = (0, 1, 1048575)
    qe_accepted: bool = True
    frozen: bool = False
    sticky_fault: bool = False
    blocks: int = 0
    qe_seen: set = field(default_factory=set)
    issued: set = field(default_factory=set)
    acked: set = field(default_factory=set)
    visible: set = field(default_factory=set)
    fence_requested: bool = False
    fence_seen: bool = False
    qe_idle_seen: bool = False
    delivery_fence: bool = False
    control_token: int = 0
    reads: dict = field(default_factory=dict)

    def admission(self, simultaneous_fault=False):
        return not (self.frozen or self.sticky_fault or simultaneous_fault)

    def fault(self):
        self.frozen = self.sticky_fault = True

    def qe_terminal(self, block, poison=False, consumer_ready=False):
        assert self.qe_accepted and 0 <= block < 16 and block not in self.qe_seen
        self.qe_seen.add(block)  # unconditional drain; poison is a terminal too
        if poison:
            self.fault()
        return self.admission() and consumer_ready and not poison

    def commit_block(self, simultaneous_fault=False):
        assert self.admission(simultaneous_fault) and self.blocks < 16
        assert len(self.qe_seen) == 16  # original producer FULL precedes issue
        self.blocks += 1

    def source_idle(self):
        assert not self.qe_accepted or len(self.qe_seen) == 16
        self.qe_idle_seen = True

    def local_cancel_ack(self):
        # Local metadata cancellation never changes accepted write/read sets.
        return self.frozen and self.qe_idle_seen and (not self.qe_accepted or len(self.qe_seen) == 16)

    def accept_read(self, tag, pc):
        assert self.admission() and tag >> 14 == 0b100 and 0 <= pc < 32
        assert tag & 31 <= 16
        assert tag not in self.reads and len(self.reads) < 8
        self.reads[tag] = pc

    def read_reply(self, tag, pc, poison=False, consumer_ready=False):
        assert tag >> 14 == 0b100 and self.reads.get(tag) == pc
        del self.reads[tag]  # matched fault-sink retirement, no client ready
        if poison:
            self.fault()

    def grant_write(self, intent, provider_ready=True, consumer_ready=False):
        # A previously committed block owns BOTH code and scale intents.
        # Closing admission cannot erase the second half of that obligation.
        assert provider_ready and 0 <= intent < 2 * self.blocks and intent not in self.issued
        assert intent % 2 == 0 or intent - 1 in self.acked
        self.issued.add(intent)

    def ack(self, intent, owner=0b100, context=None, consumer_ready=False):
        assert owner == 0b100 and (context is None or context == self.context)
        assert intent in self.issued and intent not in self.acked
        self.acked.add(intent)  # ACK is never visibility

    def provider_visible(self, intent, owner=0b100, context=None):
        assert owner == 0b100 and (context is None or context == self.context)
        assert intent in self.issued and intent not in self.visible
        self.visible.add(intent)  # actual causal provider event, not elapsed time

    def request_fence(self):
        assert self.frozen and not self.fence_requested
        assert self.local_cancel_ack() and not self.reads
        assert len(self.issued) == 2 * self.blocks
        assert self.issued == self.acked
        self.fence_requested = True

    def complete_fence(self, owner=0b100, context=None, control_token=0, delivery=True):
        assert self.fence_requested and not self.fence_seen
        assert owner == 0b100 and context == self.context
        assert control_token == self.control_token and delivery
        assert self.issued == self.acked == self.visible
        self.delivery_fence = True
        self.fence_seen = True

    def retired(self):
        return (self.local_cancel_ack() and self.fence_seen and self.delivery_fence and not self.reads and
                (not self.qe_accepted or len(self.qe_seen) == 16) and
                len(self.issued) == 2 * self.blocks and
                self.issued == self.acked == self.visible)


def bounded_contract_checks():
    samples = []
    # Cancel in every QE-output suffix, including no output and after all16.
    for prefix in range(17):
        ledger = CancelLedger()
        for b in range(prefix):
            ledger.qe_terminal(b, consumer_ready=True)
        ledger.fault()
        for b in range(prefix, 16):
            assert not ledger.qe_terminal(b, consumer_ready=False)
        assert not ledger.local_cancel_ack()
        ledger.source_idle()
        ledger.request_fence()
        ledger.complete_fence(context=ledger.context)
        assert ledger.retired()
        samples.append(dict(kind='QE_suffix', prefix=prefix, discarded_suffix=16-prefix))
    # Cancel after any number of block commitments, in each active-write phase.
    for blocks in range(17):
        for phase in ('unsent', 'accepted', 'acked', 'visible'):
            ledger = CancelLedger()
            for b in range(16):
                ledger.qe_terminal(b, consumer_ready=True)
            ledger.source_idle()
            for b in range(blocks):
                ledger.commit_block()
            if blocks and phase != 'unsent':
                ledger.grant_write(0)
                if phase in ('acked', 'visible'):
                    ledger.ack(0)
                if phase == 'visible':
                    ledger.provider_visible(0)
            ledger.fault()
            for intent in range(2 * blocks):
                if intent not in ledger.issued:
                    ledger.grant_write(intent, consumer_ready=False)
                if intent not in ledger.acked:
                    ledger.ack(intent, consumer_ready=False)
            ledger.request_fence()
            assert not ledger.retired()
            # Held/out-of-order visibility; no consumer ready needed.
            for intent in reversed(range(2 * blocks)):
                if intent not in ledger.visible:
                    ledger.provider_visible(intent)
            ledger.complete_fence(context=ledger.context)
            assert ledger.retired()
            samples.append(dict(kind='committed_WC_WS', blocks=blocks, phase=phase,
                                write_obligations=2*blocks))
    return samples


def generate():
    peirce_raw = subprocess.check_output(['git', 'show', PEIRCE+':'+PEIRCE_PATH], cwd=ROOT)
    peirce = json.loads(peirce_raw)
    assert peirce['source_commit'] == PIN
    pins = {}
    text = {}
    for path in SOURCES:
        raw = (ROOT / path).read_bytes()
        assert raw == subprocess.check_output(['git', 'show', PIN + ':' + path], cwd=ROOT)
        pins[path] = sha(ROOT / path)
        text[path] = raw.decode()
    producer = text[SOURCES[1]]
    assert 'assign issue_ready = state == FULL;' in producer
    assert 'assign blk_v = state == DRAIN;' in producer
    assert 'if (cap_v) begin' in producer and 'if (issue) begin' in producer
    assert 'else if (!fault)' not in producer
    assert 'input  wire              cancel' not in producer
    qe = text[SOURCES[0]]
    assert 'wire accept = go && ready;' in qe and 'kvb_fault <= aq_vo' in qe
    window = text[SOURCES[4]]
    assert 'if ((state == WC || state == WS || state == FR) && !addr_bad)' in window
    actual = json.loads((ROOT / EVIDENCE / 'record.json').read_text())
    assert peirce['producer_sha256'] == pins[SOURCES[1]]
    assert all(r['comparison']['verdict'] == 'PASS' for r in actual['results'])
    connected = json.loads((ROOT/'results/uarch/w17_window_qdq8_connected_startup_preparation_20261002/model.json').read_text())
    for path, digest in connected['candidate_sha256'].items():
        assert sha(ROOT/path) == digest
    cases = bounded_contract_checks()
    storage = dict(phase=3, sticky_fault=1, freeze_pending=1, fence_request=1,
                   fence_seen=1, qe_active=1, qe_terminal_seen=16,
                   committed_blocks=5, write_submitted=32, write_acked=32,
                   write_visible=32, expected_write_pc=5, expected_write_intent=5)
    context = dict(user=10, generation=16, absolute_row=21, local_row=21,
                   VM_source_base=30, KVT_base=30, refill_epoch=9,
                   backend_owner=3, stack=2)
    return dict(
        schema='opentallas.window.qdq8.cancel_contract.v1',
        verdict='FINITE_LOCAL_CONTRACT_COMPOSED_WITH_PEIRCE_EXTERNAL_PROVIDER_UNQUALIFIED',
        source_commit=PIN, source_sha256=pins, generator_sha256=sha(Path(__file__)),
        selected_candidate_sha256=connected['candidate_sha256'],
        branch_binding='Ninebit epoch/credit8 contract refers to isolated bench candidate namespace only. Original credit1 scalar sector tags/no epoch advance remain unchanged; original module multisector epoch width is not silently narrowed here.',
        evidence_sha256={p:sha(ROOT/p) for p in (EVIDENCE+'/record.json',
            EVIDENCE+'/retain0_runtime.log', EVIDENCE+'/retain1_runtime.log',
            'results/uarch/w17_window_qdq8_producer_freeze_cancel_gap_20261002/model.json')},
        current_source='Producer stickyfault does not gate capture/issue/blk. QE fault is delayed/pulsed, not cancellation. Core observes faults but offers producer no cancel port. WC/WS valid has no fault gate. Neither currentlive safety nor implemented cancellation is proved.',
        geometry=dict(QDQ8_values=512, blocks=16, values_per_block=32, writes_per_block=2,
                      max_write_intents=32, WINDOW_credit=8, WIN_STACK=2, NPC=32,
                      AW=30, POS_W=21, USER_W=10, descriptor_GENW=16,
                      transport_client_TAGW=16, backend_TAGW=17, epoch_bits=9),
        admission_contract=[
            'Reserve entire16-block producer capacity and immutable context before accepting mode1 QE go. One producer row/context at a time.',
            'Freeze has priority over new QEgo, capture commitment, KVT issue, newblk admission, descriptor/start/prime acceptance. Same-edge known fatal causes participate; any handshake before registered fault observation remains owned, never retroactively erased.',
            'Separate input consumption from payload commit. Already accepted QE operation completes all16 reads/results; consume good kvb_v OR kvb_fault terminal event, and drain/discard BF16 w_we side effect at boundary. Do not stall arithmetic or depend on cap_ready/consumer ready.',
            'After freeze discard uncommitted local blocks; preserve stickycause/context. A previously accepted WINDOW block retains its two WC/WS obligations, including unsent scale after code ACK. Only these ledger-owned continuations may issue after freeze; no new producer block.',
            'Do not publish row_valid, stage_valid or retention on failed context. Invalidate partial row/block validity and retained QK/PV copy; resident payload bits need no clearing.',
        ],
        retirement_contract=[
            'All16 accepted QE terminal events consumed (or no QE was accepted), no local payload admitted to new owner, all committed block WC/WS intents submitted or explicitly causally cancelled before submission.',
            'Retire writes only from matching WINDOW-owned completion. Preserve masked scale and fullcode write address/data/strobe until provider ownership transfer; neither producer EMPTY nor wr_done is physical completion.',
            'Selected-owner fence begins after final committed-intent submission and closes only from provider-derived causal visible/discard completion for exact frozen context. No elapsed timer, global idle, local reset or other-owner completion substitutes.',
            'All accepted READ replies must be consumed by owner-specific fault sink independent of consumer ready; no publishing discarded data. Eight finite credits and issued/received identity must retire exactly once. Peirce owns concrete read/write/provider mapping.',
            'Reuse generation/epoch/address/owner namespace only after localQE retirement, write/read credits zero and causal selected-owner fence. Reset does not erase provider obligations. Explicit rearm may clear stickyfault only after retired fence and fresh isolated context.',
        ],
        healthy_landmarks=dict(producer_last_block_accept_cycle=871, final_WR_ack_cycle=905,
            final_WRcolumn_ps=904000, declared_shadow_visible_ps=911274,
            declared_visible_lag_ps=7274, CLK_PS=1000,
            meaning='871<905 and904000<911274; producerEMPTY and ACK are not causalphysicalvisibility. Shadowtimer7274 is existing oracle only, not a fence event.'),
        owner_contract=dict(backend_WINDOW_owner='100 in bits16:14', CKV='101', RoPE='110',
            control_token='Independent alternating1bit cancellation/fence token; never a backendowner/tag/epoch bit. Token reuse requires old source and provider closure; same-wire ghost is a provider-assumption violation, not detectable producer generation.',
            client_epoch='00|epoch9|sector5; writessectoronly',
            write_ACK='Untagged perPC; KARB bw_out/kw_out onlydistinguish BvsK. KVmux maps K writecompletion toWINDOW because otherKowners read-only. Fence still requires retained expectedPC/context/intent, not sector tag alone.',
            key='user10,generation16,absolute/localrow21,VMsource/KVTbase30,epoch9,owner3,stack2 retained beside transport; no widening/tag alias silently introduced.',
            faultsink='Accept matching held/outoforder READ returns even clientready0. Stale/duplicate/poison/wrongowner are fault evidence; never return a new credit without matching outstanding identity.'),
        finite_bounds=dict(QE_terminal_events=16, write_obligations=32,
            simultaneous_unacked_WINDOW_writes=1, physical_visibility_pending_upper_bound=32,
            read_credits=8, consumer_ready_requirement=False,
            provider_grant_requirement=True, provider_completion_requirement=True,
            timeout_is_completion=False,
            QE_accepted_relative_calendar='reads2..17 outputs17..32 idle35; fault does not shorten sourcepipeline. Atfaultedge e fixed accepted suffix has <=16 terminal events; sourceidle alone does not retire externalwrites.',
            worst_recovery_cycles=None, reason='Finite storage/eventcount, not finite time under indefinitely stalled provider. Final visible/fence provider contract unqualified.'),
        cost=dict(existing_producer_bits=4338, added_RTL_bits_in_this_task=0,
            minimal_local_adapter_bits=peirce['candidate_interface']['additional_control_bits_estimate'],
            minimal_adapter_detail=peirce['candidate_interface']['bits_detail'],
            local_adapter_DFF_area_estimate_um2=peirce['candidate_interface']['area_dff_estimate_um2'],
            local_adapter_gate_slot_route_area='UNPRICED; count only, noSSFF/context hardware qualification.',
            proposed_local_control_fields=storage, proposed_local_control_bits=sum(storage.values()),
            proposed_retained_context_fields=context, proposed_context_bits=sum(context.values()),
            conservative_observer_metadata_bits=sum(storage.values())+sum(context.values())+1,
            observer_not_minimal_adapter='Abstract verification/owner-ledger budget includes independent1bit controltoken; do not add duplicated count/bitmap bookkeeping to minimal19bit localadapter by inference.',
            optional_8credit_read_ledger_bits=8*(17+5+4+1+1)+4,
            read_ledger_detail='8*(tag17+PC5+len4+beatseen1+valid1)+creditcount4 =228bits for singlebeat sectors, shared context held once. Peirce maps actual provider state; not free/reused without proof.',
            payload_duplication_bits=0, provider_intent_ledger='Not included: Peirce owns physicalprovider ledger. If provider does not retain payload, separate32x344bit intentFIFO bound=11008bits is required; no free completion credit.',
            boundary_bits=dict(QE_capture_codes_scale=264, QE_VMwrite_data_mask=1056,
                producer_block_payload=264, transport_write_data_strobe=288,
                fence_context=142, fence_req_ack=2, cancel_freeze_ack_fault=4),
            gate_fanout='Atleast6 logical admission sites; enable fanout covers16code/scale storagebanks. Drainvalid stays separate from payloadwriteenable. NoSS/FF timing/area proof.',
            healthy_added_cycles=0, healthy_delay_ps=None,
            cancellation_critical_cost='Remaining fixedQE suffix + alreadycommittedWC/WS provideradmission/completion + selectedownerfence. These overlap wherelegal; externalbound unresolved, not+7cycles.',
            fulltoken_rate=None),
        abstract_cases=cases, abstract_case_count=len(cases),
        coordination=dict(owner='Peirce', agent='01a0f95d-badc-74d3-bde3-f3eb28f089b8',
            adapter_commit=PEIRCE, adapter_path=PEIRCE_PATH,
            adapter_sha256=hashlib.sha256(peirce_raw).hexdigest(),
            adapter_composition='Localcancelack is frozen admission +16terminaloutputs + sourceidle + metadata EMPTY; it does not remove acceptedWCWScredits. Restart also needs ownerretire, deliveryfence, causalvisibility and provenance.',
            request_message='01a0fa42-d0fd-7a12-a209-1ae80ff598e5',
            pending='Concrete fence key/ports, cancellation and visible/discard provider event binding. Do not implement before composed review.'),
        next_gate='Peirce reconcile actual selectedowner provider sizes/sourcepins and causal delivery/visibility mapping with this composed localcontract; parent review same-edge cuts. Then optin newnamespace cancellation fixture preparation before explicit compileGO.',
        no_RTL=True, no_compile=True, no_payload_reads=True,
        physical_WR_provider_qualified=False, cancellation_implemented=False,
        live_producer_safe=False, recovery_qualified=False, fulltoken_credit=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=False)
    record = generate()
    (out/'model.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(dict(verdict=record['verdict'], cases=record['abstract_case_count'], cost=record['cost'])))
