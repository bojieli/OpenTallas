#!/usr/bin/env python3
"""Prepare the full-NC6 fixture, never compile or generate controller/codec RTL."""
import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/ubuntu/w2-pc-exact-completion-model-20261003')

class ProtocolError(Exception): pass

@dataclass(frozen=True)
class Identity:
    client: int
    tag: int
    generation: int
    write: bool
    def __post_init__(self):
        if not 0 <= self.client < 6 or not 0 <= self.tag < 2**32 or not 0 <= self.generation < 16:
            raise ProtocolError('identity bounds')
    @property
    def provider_tag(self): return self.client << 32 | self.tag
    @property
    def scoped39(self): return self.provider_tag << 4 | self.generation

@dataclass(frozen=True)
class Request:
    identity: Identity
    address: int
    data: int
    def __post_init__(self):
        if not 0 <= self.address < 2**34 or not 0 <= self.data < 2**256:
            raise ProtocolError('request address/data bounds')
    @property
    def wire_tuple(self):
        return (int(self.identity.write), self.address, self.identity.provider_tag,
                self.identity.generation, self.data)


def check_accepted_request(original, wire_tuple):
    """Check ALL330 bits; this never masks/truncates a received field."""
    if tuple(wire_tuple) != original.wire_tuple:
        raise ProtocolError('accepted backend full tuple differs from held caller original')


class Oracle:
    """Accepted-port oracle, independent of the implementation FSM/SECDED decoder.

    A return is matched against OLD accepted entries. No current input tag is
    substituted into a response. Slot credit ends only at client acceptance.
    Reset/wrap requires external all-copies evidence, never inferred from idle.
    """
    def __init__(self):
        self.entries = {}
        self.fault = False
        self.epoch = 0
    def cycle(self, *, issue=None, read=None, write=None, consume=()):
        if self.fault: raise ProtocolError('quarantined')
        before = dict(self.entries)
        returned = []
        accepted = dict(before)
        # issue is an ACTUAL accepted backend handshake. A simultaneous bad
        # completion cannot undo that accepted debt, though it blocks release.
        if issue is not None:
            if issue in before or sum(x.client == issue.client for x in before) >= 16:
                self.fault = True
                raise ProtocolError('duplicate identity/credit overflow')
            accepted[issue] = ('issued',None)
        try:
            for identity, payload in (() if read is None else (read,)):
                if identity.write or before.get(identity, ('missing',None))[0] != 'issued':
                    raise ProtocolError('read mismatch/duplicate/sameedge')
                returned.append((identity, payload))
            if write is not None:
                if not write.write or before.get(write, ('missing',None))[0] != 'issued':
                    raise ProtocolError('write mismatch/duplicate/sameedge')
                returned.append((write, None))
            if issue is not None:
                if issue in before: raise ProtocolError('duplicate accepted identity')
                if sum(x.client == issue.client for x in before) >= 16:
                    raise ProtocolError('credit overflow')
            for identity in consume:
                if before.get(identity, ('missing',None))[0] != 'held':
                    raise ProtocolError('consume without old held output')
        except ProtocolError:
            self.entries = accepted
            self.fault = True
            raise
        after = dict(before)
        for identity in consume: del after[identity]
        if issue is not None: after[issue] = ('issued',None)
        for identity,payload in returned: after[identity] = ('held',payload)
        self.entries = after
    def fence(self, *, provider, reverse, reset):
        if self.entries or not (provider and reverse and reset):
            self.fault=True
            raise ProtocolError('live or incomplete allcopies drain')
        self.fault=False
        self.epoch+=1



class ConnectedReceiptObserver:
    """Read-only fixture hook on EnclosingPins, registered AFTER payload hooks.

    References actual source caller offers independently of backend outputs.
    Local reset marks accepted external identities orphaned; it never disposes
    them. This observer has no clock, memory, grants, readiness or fence driver.
    Register after build() and before its first edge via add_edge_hook(observer).
    """
    def __init__(self, pins):
        self.pins = pins
        # Event-only reference tests have no driver. Live enrollment MUST use
        # the source portbook: 128 per rank, 256 total in the corrected top.
        self.instances = 128 if pins is None else pins.book['pins']['w2_rst_n']['count']
        if self.instances not in (128,256):
            raise ProtocolError('connected W2 bank inventory outside source topology')
        if pins is not None:
            for name in ('c_req_v','p_req_v','c_rsp_v','c_wr_done_v'):
                if pins.book['pins']['w2_'+name]['count'] != self.instances:
                    raise ProtocolError('connected W2 portbank counts disagree')
        self.held = {}
        self.receipts = {}
        self.orphans = set()
        self.issued = set()
        self.events = None
        self.backend_accepts = self.client_terminals = 0

    def before_edge(self):
        if self.events is not None:
            raise ProtocolError('connected observer duplicate edge')
        self.events = []
        reset = self.pins.get('w2_rst_n')
        cv = self.pins.get('w2_c_req_v')
        pv = self.pins.get('w2_p_req_v')
        rv = self.pins.get('w2_c_rsp_v')
        wv = self.pins.get('w2_c_wr_done_v')
        for pc in range(self.instances):
            if not (reset >> pc) & 1:
                self.orphans.update(k for k in self.receipts if k[0] == pc)
                # Unaccepted offers can be cancelled only at stopped/reset
                # ingress. Accepted identities and their original data survive.
                for k in list(self.held):
                    if k[0] == pc: del self.held[k]
                continue
            mask = 63 << (pc * 6)
            if not ((cv | rv | wv) & mask or (pv >> pc) & 1 or
                    any(k[0] == pc for k in self.held)):
                continue
            p = (self.pins.component('w2', pc % 128, rank=pc // 128)
                 if self.instances == 256 else self.pins.component('w2', pc))
            reqv = (cv >> (pc * 6)) & 63
            reqr = p.get('c_req_rdy') if reqv else 0
            stop = p.get('admission_stop')
            for c in range(6):
                caller = (pc, c)
                if reqv >> c & 1:
                    original = Request(Identity(c,
                        (p.get('c_req_tag') >> (c*32)) & 0xffffffff,
                        (p.get('c_req_gen') >> (c*4)) & 15,
                        bool(p.get('c_req_we') >> c & 1)),
                        (p.get('c_req_addr') >> (c*34)) & ((1<<34)-1),
                        (p.get('c_req_data') >> (c*256)) & ((1<<256)-1))
                    if caller in self.held and self.held[caller] != original:
                        raise ProtocolError('connected held caller original changed')
                    self.held.setdefault(caller, original)
                    if reqr >> c & 1:
                        self.events.append(('caller', pc, self.held[caller]))
                elif caller in self.held:
                    if not stop:
                        raise ProtocolError('connected held caller withdrawn without stop')
                    del self.held[caller]
            if (pv >> pc) & 1 and p.get('p_req_rdy'):
                self.events.append(('backend', pc, (
                    p.get('p_req_we'), p.get('p_req_addr'), p.get('p_req_tag'),
                    p.get('p_req_gen'), p.get('p_req_data'))))
            for stem, write in (('c_rsp', False), ('c_wr_done', True)):
                takes = p.get(stem+'_v') & p.get(stem+'_rdy')
                for c in range(6):
                    if takes >> c & 1:
                        identity = Identity(c,
                            (p.get(stem+'_tag') >> (c*32)) & 0xffffffff,
                            (p.get(stem+'_gen') >> (c*4)) & 15, write)
                        self.events.append(('terminal', pc, identity))

    def after_edge(self):
        if self.events is None:
            raise ProtocolError('connected observer missing before edge')
        events, self.events = self.events, None
        # Old issued identities alone can retire. Newly accepted requests
        # cannot turn a stale same-edge terminal into a valid receipt.
        old_issued = set(self.issued)
        for kind, pc, value in events:
            if kind == 'caller':
                key = (pc, value.identity)
                if key in self.receipts:
                    raise ProtocolError('connected duplicate/ABA accepted identity')
                self.receipts[key] = value
                del self.held[pc, value.identity.client]
            elif kind == 'backend':
                we, address, tag, gen, data = value
                identity = Identity(tag >> 32, tag & 0xffffffff, gen, bool(we))
                key = (pc, identity)
                if key not in self.receipts or key in self.orphans or key in self.issued:
                    raise ProtocolError('connected backend without unique live original')
                check_accepted_request(self.receipts[key], value)
                self.issued.add(key)
                self.backend_accepts += 1
            else:
                key = (pc, value)
                if key not in old_issued or key in self.orphans:
                    raise ProtocolError('connected terminal without nonorphan old receipt')
                del self.receipts[key]
                self.issued.remove(key)
                self.client_terminals += 1


def case_mapping(text):
    section=text[text.index('function automatic integer global_index'):]
    section=section[:section.index('endfunction')]
    return {int(a):int(b) for a,b in re.findall(r'(\d+):\s*global_index\s*=\s*(\d+)',section)}


def selected_primary(source_root, reset_quarantine=False):
    if reset_quarantine:
        return source_root/'rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_protected_completion_reset_quarantine.sv'
    return source_root/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_protected_completion.sv'


def selected_secondary(source_root, reset_quarantine=False):
    primary=selected_primary(source_root,reset_quarantine)
    body=primary.read_text()
    if reset_quarantine:
        if not re.search(r'\bot_w2_nc6_coded_secondary_reset_quarantine\s*#',body):
            raise ValueError('reset quarantine primary does not select matching secondary')
        return source_root/'rtl/experimental/w2_nc6_reset_quarantine_20261003/ot_w2_nc6_coded_secondary_reset_quarantine.sv'
    if re.search(r'\bot_w2_nc6_coded_secondary_acyclic\s*#',body):
        return source_root/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_coded_secondary_acyclic.sv'
    return source_root/'rtl/experimental/w2_nc6_secondary_20261003/ot_w2_nc6_coded_secondary.sv'


def inventory(source_root,reset_quarantine=False):
    paths=['tools/w2_nc6_primary_source.py',
           str(selected_primary(source_root,reset_quarantine).relative_to(source_root)),
           str(selected_secondary(source_root,reset_quarantine).relative_to(source_root)),
           'rtl/test/w2_nc6_completion_20261003/tb.sv']
    bodies={p:(source_root/p).read_text() for p in paths}
    primary=case_mapping(bodies[paths[1]])
    secondary=case_mapping(bodies[paths[2]])
    if len(primary)!=182 or len(secondary)!=37 or set(primary.values()) & set(secondary.values()) or set(primary.values())|set(secondary.values()) != set(range(219)):
        raise ValueError('physical storage mapping is not182+37 disjoint/exhaustive')
    reverse={g:dict(bank='primary',local=l) for l,g in primary.items()}
    reverse.update({g:dict(bank='secondary',local=l) for l,g in secondary.items()})
    model_text=bodies[paths[0]]
    ii=re.search(r'same_client_request_II_min=(\d+)',model_text)
    return dict(source_pins={p:hashlib.sha256((source_root/p).read_bytes()).hexdigest() for p in paths},
                words=[dict(global_word=g,**reverse[g]) for g in range(219)],
                source_same_client_II_min=int(ii.group(1)) if ii else None,
                baseline18_case_source=paths[3],
                controller_campaign=dict(singles=219*72, single_scope='ALL physical bits, all219 words',
                    doubles_sampled=219*72, double_pairs_per_word=72,
                    double_scope='adjacent cyclic physical-bit pairs (0,1)..(71,0), NOT all2556pairs/word',
                    allpair_controller_cases=219*2556, allpair_controller_run=False,
                    parent_allpair_leaf_proof='results/rtl/w2_sealed_codec_parent_20261003; reused, not rerun'),
                compiled=False, runtime_pass=False, physical_or_token_admission=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=SOURCE)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reset-quarantine',action='store_true')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    report=inventory(args.source_root,args.reset_quarantine)
    bench=ROOT/'rtl/test/w2_fullnc6_functional_20261003/tb.sv'
    report['directed_cases']=re.findall(r'pass\("([^"\n]+)"\)',bench.read_text())
    report['fixture_sha256']=hashlib.sha256(bench.read_bytes()).hexdigest()
    report['public_contract']=dict(module='ot_w2_nc6_protected_completion_reset_quarantine' if args.reset_quarantine else 'ot_w2_nc6_protected_completion',OPT_EXACT=1,PC_ID=7,
        NC=6,MAX_OUT=16,tag32=True,generation4=True,provider_tag35=True,
        provider_generation_separate4=True,address34=True,sector256=True,
        new_inputs=['reverse_fenced'],new_outputs=['repair_busy'],
        source_ready_is_required=True,write_completion_ready_is_required=True)
    report['public_contract']['OPT_RESET_QUARANTINE']=int(args.reset_quarantine)
    report['fixture_progress_bound_edges']=1024
    report['progress_bound_scope']='test progress assertion with explicit peers responsive; no process/job deadline'
    report['RTL_compile_deferred_to']='Nash/Hubble after actual source/composition admission'
    report['required_design_modules']=['ot_w2_nc6_protected_completion','ot_w2_nc6_coded_secondary',
        'ot_w2_sealed_secded72','ot_w2_nc6_correction_control']
    report['remaining_before_compile']=['Nash final primary source/composition/lint',
        'Hubble real8corrector CAP4/FIX4, actual clean/status and scrub ownership',
        'final source model normal8/8/9 and count/epoch II19 vs antecedent18 reconciliation',
        'same single clock functional fixture enrollment; no SS/FF or area/fit inferred']
    report['prospective_normal_edges']=dict(request=8,read=8,write=9,journal=4)
    report['prospective_repair_edges']=dict(capture=4,fix=4)
    report['latency_assertion_policy']='wait real readyvalid and log PORT_EVENT; never force ready or currentclean, never fit measured cycles to prospective values'
    report['synthetic_case_reset_scope']='cold case boundary explicitly discards fixture-provider copies; runtime reset stale-return is a separate refusal test, no installed allcopies/reset proof'
    report['reset_receipt_reference']=dict(
        conservation='externalaccepted = CURRENTlocaltable + acceptedjournals + identifiedresetorphans',
        local_projection='active NONquarantined receipts only',
        no_reset_equation_unchanged=True,
        local_reset_preserves_external_receipt_identity_and_debt=True,
        disposal='explicit synthetic_provider_discard_all_receipts callback at cold scope boundary only',
        terminal_requires='unique NONquarantined client/tag/gen/direction receipt',
        expected_FAIL_reference_mutants=['omit','drop','drop_debt','consume'],
        reference_mutants_run=False,updated_fixture_run=False,
        unfenced_global_reset_and_samekey_ABA='integration gap, not qualified by local stale-return refusal')

    report['mutable_fault_state_scope']='physical matrix uses cold initialized state; held-read CE and validcoded active row/query/journal tested separately; not every state x fault cross-product'
    (args.out/'preparation.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('PREPARED_ONLY:182primary+37secondary; no compile/runtime/codec rerun')

if __name__=='__main__': main()
