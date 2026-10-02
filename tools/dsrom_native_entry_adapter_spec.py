#!/usr/bin/env python3
"""Default-off source model: input proof, accepted leases, cfg/ECC fence.
No native mapping, word encoding, golden callback, RTL or hardware execution.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_native_entry_adapter_spec_20261002'


def bf16_reround_bits(bits):
    return (((bits + 0x7fff + ((bits >> 16) & 1)) >> 16) << 16) & 0xffffffff


def input_certificate(row):
    c, p = row['consumer']['instruction'], row['producer']['instruction']
    if (c.get('me_round') != 0 or p.get('rnd') != 1 or p.get('pred', 0) != 0
            or p.get('o_base') != c.get('me_xbase') or p.get('o_si') != 1
            or p.get('su_nout') != 1 or p.get('su_nin') != 5120
            or c.get('me_xks') != 1 or c.get('me_xjs', 0) != 0
            or c.get('me_xcs') != c.get('me_k') or row['intervening_XN_writers']):
        raise ValueError('phase-specific producer coverage not proved')
    if c['me_k'] * (1 << c.get('me_split', 0)) != 5120:
        raise ValueError('XN input range not fully covered')
    return dict(consumer=row['consumer']['id'], producer=row['producer']['id'],
        producer_VM_base=p['o_base'], producer_elements=5120,
        producer_word_sha256=row['producer']['template_word_sha256'],
        consumer_word_sha256=row['consumer']['template_word_sha256'],
        input_rounding_obligation='BF16 identity only, contingent on this producer version visible at all accepted reads',
        original_me_round=0, output_s_fmt=1,
        all_reduction_arithmetic_order_qualification_transferred=False,
        dedicated_head_unbound=row['consumer']['scope']=='head')


def checked_key(eid32, base, stride):
    # EID guard is BEFORE multiplication, truncation, or CAM activity.
    if not isinstance(eid32, int) or not 0 <= eid32 < 384:
        raise ValueError('invalid full unsigned32 EID; no multiply/CAM/go')
    if not 0 <= base < (1 << 30) or stride < 0:
        raise ValueError('invalid source key operands')
    wide = base + eid32 * stride
    if wide >= 1 << 30:
        raise ValueError('key overflow before30bit CAM compare')
    return wide


def cfg_delivery_fence(receipts, owner, phase, pairs):
    """Accepted decoded/captured delivery, not source c_v or elapsed27cycles."""
    seen = set()
    last = -1
    for r in receipts:
        key = (r['pair'], r['word_index'])
        if (r['owner'] != owner or r['phase'] != phase or r['pair'] not in pairs
                or not 0 <= r['word_index'] < 25 or key in seen
                or not r['capture_accepted'] or not r['ECC_good_or_corrected']
                or r['uncorrectable'] or not r['consumer_delivery_accepted']
                or r['logical_address'] != 25*phase+r['word_index']
                or not r['command_edge'] < r['capture_edge'] <= r['ECC_terminal_edge'] <= r['delivery_edge']):
            raise ValueError('poison/stale/duplicate/mismatched/unaccepted cfg return')
        seen.add(key)
        last = max(last, r['delivery_edge'])
    if seen != {(p,w) for p in pairs for w in range(25)}:
        raise ValueError('missing25word/pair delivery fence')
    return last


class EntryLease:
    """Executable model of ONE owner; no licensed native provider handshake."""
    def __init__(self, owner, indexed, base=0, stride=4096):
        self.owner, self.indexed, self.base, self.stride = owner, indexed, base, stride
        self.state='ENTRY'; self.vm_reads=0; self.vm_pending=False
        self.accepted_go=0; self.poison=False; self.arm_edge=None; self.fence_edge=None
    def vm_request(self, accepted):
        if not accepted:
            return
        if not self.indexed or self.state!='ENTRY' or self.vm_reads:
            raise ValueError('duplicate/wrong-state accepted VMread')
        self.vm_reads=1; self.vm_pending=True; self.state='VMWAIT'
    def vm_response(self, owner, eid):
        if owner != self.owner or not self.vm_pending:
            raise ValueError('stale/mismatched or unrequested VMresponse')
        self.vm_pending=False
        if self.state=='CANCEL':
            return None  # quarantine actual accepted read, no second read or CAM
        try:
            key=checked_key(eid,self.base,self.stride)
        except ValueError:
            self.poison=True;self.state='CANCEL';raise
        self.state='LOOK'; return key
    def lookup(self, hit, phase_identity_matches, predicate_ok):
        if self.state not in ('ENTRY','LOOK') or (self.indexed and self.vm_reads!=1):
            raise ValueError('lookup before actual accepted VMresponse')
        if not hit or not phase_identity_matches or not predicate_ok:
            self.poison=True;self.state='CANCEL';return False
        self.state='CFG';return True
    def fence(self, last_delivery_edge, act_visible_edge):
        if self.state!='CFG' or act_visible_edge <= last_delivery_edge:
            raise ValueError('act not visible after last accepted cfgword')
        self.fence_edge=act_visible_edge;self.state='READY'
    def arm(self, edge, reserved_ready):
        if self.state!='READY' or self.poison or edge < self.fence_edge or not reserved_ready:
            raise ValueError('no registered GO reservation')
        self.arm_edge=edge;self.state='ARMED'
    def commit(self, edge, owner, ready_held):
        if (self.state!='ARMED' or self.poison or owner!=self.owner
                or edge<=self.arm_edge or not ready_held):
            raise ValueError('registered s_go not accepted under same endpoint lease')
        self.accepted_go+=1;self.state='WAIT'
    def cancel(self):
        self.poison=True
        if self.state!='WAIT':self.state='CANCEL'
    def drain(self, matching_returns_drained, field_consumer_visible):
        if (not matching_returns_drained or self.vm_pending
                or (self.accepted_go and not field_consumer_visible)):
            raise ValueError('owner cannot release before accepted-return/consumer drain')
        self.state='RELEASED'


def build():
    pins=[]
    def read(name):
        b=(OUT/'inputs'/name).read_bytes();pins.append(dict(snapshot=name,sha256=hashlib.sha256(b).hexdigest()))
        return b
    manifest=json.loads(read('manifest.json'))
    for r in manifest:
        if hashlib.sha256(read(r['snapshot'])).hexdigest()!=r['sha256']:
            raise ValueError('source snapshot changed')
    proofs=json.loads(read('phase_producers.json'))
    certificates=[input_certificate(r) for r in proofs['proofs']]
    golden=(OUT/'inputs/golden_bits.py').read_text()
    if 'rounded = (b + 0x7FFF + ((b >> 16) & 1)) >> 16' not in golden:
        raise ValueError('golden conversion formula changed')
    assert all(bf16_reround_bits(b<<16)==b<<16 for b in range(65536))
    cfg=json.loads((OUT/'inputs/cfg_interface.json').read_bytes())
    native=(OUT/'inputs/native_adapter.sv').read_text()
    for term in ['s_fmt <= 2\'d1;', 'S_IDXW: begin key <= key + AW\'(vi_q) * stride;', 's_ph <= hit_p; st <= S_GO;']:
        if term not in native:raise ValueError('native edge semantics changed')
    return dict(schema='opentallas.dsrom.native-entry-default-off-spec.v1',
        source_pins=pins,source_manifest=manifest,program_source=proofs['source'],
        program_source_sha256=proofs['source_sha256'],
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        opt_in_parameter='MODEL_NATIVE_ENTRY_GUARD',default=False,
        producer_certificates=certificates,finite_BF16_encoding_identity_count=65536,
        includes_nonfinite_encoding_bit_identity_but_not_numerical_stability_qualification=True,
        six_compressor_input_round_obligations_conditionally_resolved=True,
        native_m_ok_and_original_words_unchanged=True,
        original_seven_native_FAIL_receipts_unchanged=True,
        reduction_order_and_full_bitexactness_admission=False,
        head_input_certificate_only=True,head_provider_argmax_and_order_still_unbound=True,
        owner_interface=['node_id','rank','stage','phase','matrix_journal_ordinal','source_key',
            'reset_generation','lease_id','producer_XN_version','producer_visibility_receipt',
            'selector_VM_address','accepted_VM_request_id','selected_unsigned32_EID'],
        owner_tag_hardware_widths_not_fabricated=True,
        VMread_contract='Exactly one accepted indexed VM request; stalls do not count as acceptance. Match response lease/generation; check all32 EID bits range0..383 BEFORE multiply/CAM; wide key overflow checked. Cancellation quarantines that actual read, never rereads.',
        native_VM_provider_accept_and_response_tags_unimplemented=True,
        cfg_ECC_interface=cfg['cfg_adapter_required_contract'],
        cfg_calendar=dict(compiled_pairs=4096,words_per_pair=25,
            macro_bits=72,payload_bits=48,SECDED7_mapping_proposal_not_qualified=True,
            request_key=['owner','pair','phase','word_index','logical_address'],
            receipt_fields=['command_edge','capture_accepted','capture_edge','ECC_good_or_corrected',
                'uncorrectable','ECC_terminal_edge','consumer_delivery_accepted','delivery_edge'],
            accepted_per_phase_word_deliveries=4096*25,
            all_padding_and_default_words_charged=True,
            act_fence='Actual word25/class-valid visibility under matching owner before ARM; source c_v/27cycles is not ACK.',
            registered_GO='ARM reserves endpoint credit at edgeE; registered s_go accepted at a later edge>=E+1 under the SAME ready-held owner. Cancellation before acceptance kills GO; after acceptance retains poison lease through result/cfg/VM drain.',
            no_fixed_physical_II_or_latency_credit=True),
        positive_calendar_terms=['XN_producer_visible','accepted_EID_VMread_response','range_and_wide_key_check',
            'matching_CAM_phase','cfg_macro_capture_ECC_delivery_all25word_fence',
            'registered_GO_accept','code_scale_ECC_field','root_consumer_visible_and_drain'],
        calendar_cost_equation='GO_accept >= max(XN_visible, selected_EID_checked, phase_key_match, cfg_all_words_act_visible) + registered_endpoint_accept_delay; completion additionally requires positive code/scale/ECC/root/consumer costs.',
        extra_area_and_route_terms=['unsigned32_range_compare','wide_key_overflow_guard','producer-version/owner lease',
            'cfg/ECC terminal fence and poison/drain bookkeeping','registered_GO credit/cancel guard'],
        area_and_finite_timing_unpriced_not_zero=True,
        full_token_or_physical_admission=False,RTL_PR_or_mapping_reemit_jobs=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=OUT/'model-r1.json');a=p.parse_args()
    b=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode()
    if a.out.exists() and a.out.read_bytes()!=b:raise ValueError('immutable record changed')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(b)
    print(hashlib.sha256(b).hexdigest())


if __name__=='__main__':main()
