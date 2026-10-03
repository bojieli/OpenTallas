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
