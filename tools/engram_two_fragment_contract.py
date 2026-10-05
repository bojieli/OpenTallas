"""Executable conditional 288word -> two256fragments contract, no RTL."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
DATA=(1<<264)-1;TAG=(1<<24)-1;LOW=(1<<224)-1
def tag(epoch,column,layer,beat,lease):
    assert 0<=epoch<256 and 0<=column<24 and layer in (0,1) and 0<=beat<8 and 0<=lease<64
    return (epoch<<16)|(column<<11)|(layer<<10)|(beat<<7)|(1<<6)|lease
def encode(payload,t):
    assert 0<=payload<=DATA and 0<=t<=TAG
    return [(payload&LOW)|(t<<224), (payload>>224)|(t<<224)|(1<<248)]
class Receiver:
    # Six control FFs: RXphase2 +ACKpending1 +ACKreturned1 +TXphase1 +creditlocked1.
    # RXphase EMPTY/HALF/FULL/DRAIN encodes publication and consumed-once.
    def __init__(self,expected):
        self.expected=expected;self.first=None;self.word=None;self.phase=0
        self.ack_pending=False;self.ack_returned=False;self.tx_phase=0;self.credit_locked=True
    @property
    def ack(self):return self.ack_pending
    @property
    def published_valid(self):return self.phase==2
    def put(self,f):
        if not self.credit_locked or self.phase not in (0,1):raise ValueError('held/retired word')
        if not 0<=f<1<<256 or f>>249:raise ValueError('frame padding')
        phase=(f>>248)&1;t=(f>>224)&TAG;payload=f&LOW
        if t!=self.expected or not ((t>>6)&1):raise ValueError('lease/tag mismatch')
        if self.phase==0:
            if phase:raise ValueError('second before first')
            self.first=payload;self.phase=1
        else:
            if not phase:raise ValueError('duplicate/out-of-order first')
            if payload>>40:raise ValueError('second payload padding')
            self.word=self.first|(payload<<224)|(t<<264);self.phase=2
        assert not self.ack_pending
    def consume(self):
        if self.phase!=2:raise ValueError('missing second or already consumed')
        self.phase=3;self.ack_pending=True
        # Keep all payload bits physically held until actual returned ACK/reset.
        return self.word
    def return_ack(self,logical_tag):
        if self.phase!=3 or not self.ack_pending or logical_tag!=self.expected:
            raise ValueError('early,duplicate,or mismatched returned ACK')
        self.ack_pending=False;self.ack_returned=True;self.credit_locked=False;self.phase=0
        # Payload remains held; only publication/lease state changes.
    def arm(self,expected):
        if self.credit_locked or self.phase!=0:raise ValueError('credit not returned')
        self.expected=expected;self.first=None;self.ack_returned=False;self.credit_locked=True
    def reset(self,expected):
        self.expected=expected;self.first=None;self.phase=0
        self.ack_pending=False;self.ack_returned=False;self.tx_phase=0;self.credit_locked=True
        # Reset/drained-reuse provider is unbound; this is software semantics only.
def must_reject(fn):
    try:fn()
    except ValueError:return True
    raise AssertionError('mutant unexpectedly accepted')

if __name__=='__main__':
    commit=subprocess.check_output(['git','rev-parse','9b5ca5767'],text=True).strip()
    path='results/quality/w16_engram_eight_scale_binding_20261001/actual_rows.wire_beats.bin'
    raw=subprocess.check_output(['git','show',commit+':'+path]);assert len(raw)==48*8*33
    masksraw=(ROOT/'repacked_192_enable_mask_contract.json').read_bytes();masks=json.loads(masksraw)
    checks=0;mutants=0;roundtrip=hashlib.sha256()
    for n in range(384):
        row,beat=divmod(n,8);layer,column=divmod(row,24)
        payload=int.from_bytes(raw[n*33:(n+1)*33],'little');t=tag(7,column,layer,beat,3)
        first,second=encode(payload,t);rx=Receiver(t);rx.put(first)
        assert rx.word is None and not rx.ack
        mutants+=must_reject(rx.consume)
        rx.put(second);assert not rx.ack
        mutants+=must_reject(lambda:rx.return_ack(t))
        got=rx.consume();assert rx.ack and not rx.published_valid and got==(payload|(t<<264))
        mutants+=must_reject(rx.consume)
        assert rx.word==got
        mutants+=must_reject(lambda:rx.put(first))
        mutants+=must_reject(lambda:rx.arm(t))
        mutants+=must_reject(lambda:rx.return_ack(t^1))
        rx.return_ack(t);assert not rx.ack and not rx.published_valid and rx.word==got
        mutants+=must_reject(rx.consume)
        mutants+=must_reject(lambda:rx.return_ack(t))
        mutants+=must_reject(lambda:rx.put(first))
        assert (got&DATA).to_bytes(33,'little')==raw[n*33:(n+1)*33]
        roundtrip.update(got.to_bytes(36,'little'));checks+=1
        for mutation in (second,first|(1<<255),first^(1<<240)):
            mutants+=must_reject(lambda mutation=mutation:Receiver(t).put(mutation))
        dup=Receiver(t);dup.put(first);mutants+=must_reject(lambda:dup.put(first))
        pad=Receiver(t);pad.put(first);mutants+=must_reject(lambda:pad.put(second|(1<<80)))
        mixed=Receiver(t);mixed.put(first);mutants+=must_reject(lambda:mixed.put(second^(1<<240)))
        reset=Receiver(t);reset.put(first);reset.reset(tag(8,column,layer,beat,3))
        mutants+=must_reject(lambda:reset.put(second))
        held=Receiver(t);held.put(first);held.put(second);mutants+=must_reject(lambda:held.put(first))
    hops=masks['path_geometry']['wire_stage_sum']+8191
    extra_per_home=318*hops
    homes=[]
    for h in masks['homes']:
        total=h['total_storage_FF_bits']+extra_per_home
        homes.append(dict(home_id=h['home_id'],actual_macros=h['actual_macros'],
            preserved_prior_FF_bits=h['total_storage_FF_bits'],new_fragment_reassembly_and_control_FF_bits=extra_per_home,
            total_storage_FF_bits=total,held_feedback_MUX2_bits=total,
            preserved_response_MUX2_bits=h['response_MUX2_bits'],request_demux_AND2_bits=h['request_demux_AND2_bits'],
            stop_wait_row_cycles_range=[8*(6*(13+p)+1) for p in h['selected_wire_path_cycles_range']]))
    out=dict(schema='opentallas.engram.two-fragment-contract.v1',
        status='PASS_SOFTWARE_PACKET_ROUNDTRIP_AND_MUTANTS_CONDITIONAL_HARDWARE_UNBOUND',
        source_retained_fixture_pin=dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest()),
        fixture_scope='384 beats from previously committed48retained first-row fixtures; not token hash coverage and no new checkpoint reads',
        repacked_enable_mask_sha256=hashlib.sha256(masksraw).hexdigest(),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        packet=dict(full_word_bits=288,payload_bits=264,tag_bits=24,fragment_bits=256,fragments=2,
            first='bits223:0 payloadlow224;247:224 duplicate tag24;248 phase0;255:249 zero',
            second='bits39:0 payloadhigh40;223:40 zero;247:224 duplicate SAMEtag24;248 phase1;255:249 zero',
            tag_recipe='epoch8,column5,layer1,beat3,valid1,lease6; tagvalid at bit6',
            response_valid='embedded in duplicated tag; no free phase/epoch wire outside256frame',
            controls='requestready1,responsefragmentready1,fullwordACK1 separately; requestvalid embedded in requesttag',
            total_cut_tracks=51+256+3,source_remaining_tracks=321,margin_tracks=11,
            earlier_309_track_option='Not claimed: explicit fullwordACK needs third reversecontrol.309requires source-proven multiplexedACK encoding.',
            actual_frame_CRC_endpoint_shared_port=None),
        lease_rule='Reserve receiver slot before first. Validate phase/order/tag/padding. First does not publish a word; second only assembles it. FullwordACK occurs only after local fullword consumer acceptance; originalword remains held meanwhile. Root rowlease held until all8word ACKs AND final external consumer ACK/generation visibility. Reset discards pending first and rejects old epoch.',
        new_state_per_response_hop_bits=318,
        new_state_recipe='288assembledword +24expectedtag +6exactcontrolFF:RXphase2(EMPTY/HALF/FULL/DRAIN) +ACKpending1 +ACKreturned1 +TXphase1 +creditlocked1. Preserve original288 response FF/mux and every original clock; no subtraction.',
        response_hop_endpoint_count_per_home=hops,homes=homes,
        aggregate_new_fragment_FF_bits=192*extra_per_home,
        aggregate_total_storage_FF_bits=sum(h['total_storage_FF_bits'] for h in homes),
        clock_rule='Every old and new FF and all1500067macros clock1.2GHz continuously. No inactive or stop credit.',
        runtime_events=dict(macro_reads_per_lookup=8,response_fragments_per_lookup_per_selected_hop=16,
            reassembly_word_accepts_per_lookup=8,fullwordACKs_per_lookup=8,
            first_payload_write_bits_per_lookup_upper=8*224,second_payload_write_bits_per_lookup_upper=8*40,
            expected_tag_bit_transitions_per_lookup_upper=24+11+1,
            duplicated_tag_wire_bit_transition_upper_including_initial=2*(24+11+1),
            fragment_phase_bit_transitions_per_lookup_upper=16,
            per_hop6control_bit_updates_upper=6*4*8,
            feedback_stall='No accepted repeatedwrite; payloadheld under backpressure. Disabled cones still see upstream raw pin transitions; Confucius owns typed event pricing.',
            startup_reset_activity=None),
        timing=dict(schedule='Conservative stop-and-wait per word, no overlap: Hrequest +1macro +4Hresponse (2fragments+assemble+localconsume) +HreverseACK =6H+1 perword,8words/row. H=13logic+actual35..36wirestages.',
            max_local_row_cycles=max(h['stop_wait_row_cycles_range'][1] for h in homes),
            max_local_row_ns=max(h['stop_wait_row_cycles_range'][1] for h in homes)/1.2,
            qualification='Conditional schedule only; hop/register/contextual SSFF and root externallease unqualified. Faster pipelined queue calendar requires separate executable proof and composed costs; old104/106cycle rows not reused.'),
        six_control_state_bits_exact=True,publication_consumption_retirement_separate=True,
        actual_tagged_ACK_wire_provider=False,ACK_API_scope='return_ack(logicaltag) tests logical lease retirement; physicalACK1bit identity/drainedreuse remains unproven.',
        supersedes_failure_pin='a21f1cdd1 duplicate consume FAIL; prior codec/old failure records retained',
        software_gate=dict(roundtrip_words=checks,fragments=checks*2,negative_mutant_rejections=mutants,
            roundtrip288word_SHA256=roundtrip.hexdigest(),held_second_before_ACK_checked=True,
            reordered_duplicate_stale_epoch_mixed_tag_padding_earlyACK_rejected=True),
        no_actual_tree_decoder_RTL_gate=True,source_provider_proven=False,L1_generated_source=None,
        checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False,headline_rate=None)
    target=ROOT/'two_fragment_contract_consumed_once.json';assert not target.exists();target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),FF=out['aggregate_total_storage_FF_bits'],hops=hops,gate=out['software_gate'],latency=out['timing'])))
