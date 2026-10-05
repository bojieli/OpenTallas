"""Replay actual descriptor assertion and RTL bit decode; no RTL changes."""
import ast
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIN = 'cc8a2a77bdfc1c69aeda2d0a678d66f5df5a8cd9'
PACKER = 'tools/v41_die_images_w17w10.py'
SPINE = 'rtl/v41die/ot_v41_spine_w17w10.sv'
PAIR = 'rtl/v41die/ot_v41_pair_w17w10.sv'
CANDIDATE = 'results/quality/w16_w17_integer_residency_20261001/candidate.json.gz'

def blob(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)

def replay():
    source = blob(PIN, PACKER)
    fn = next(x for x in ast.parse(source).body if isinstance(x, ast.FunctionDef) and x.name == 'phase_words')
    namespace = {}
    # Compile the unchanged actual function, without importing numpy or image
    # generators. The optimized variant is a negative-control counterexample.
    module = ast.Module(body=[fn], type_ignores=[])
    exec(compile(module, PACKER, 'exec'), namespace)
    unchecked = {}
    exec(compile(module, PACKER, 'exec', optimize=1), unchecked)
    packed_candidate = blob('0fb58ac09', CANDIDATE)
    candidate = json.loads(gzip.decompress(packed_candidate))
    family_order = ('w1', 'w3', 'w2')
    counts = {f: candidate['templates'][f]['stream_issue_cycles'] for f in family_order}
    stage = max(candidate['stages'], key=lambda s: s['experts'])
    phases = []
    base = 0
    first_failure = None
    for slot in range(stage['experts']):
        for family in family_order:
            # Counts and K are actual candidate quantities; nrows1280 is a legal
            # illustrative even value, not an emitted new phase image.
            ph = dict(bf=False, K=candidate['templates'][family]['K'],
                      nbeat=counts[family], sbase=base, nrows=1280,
                      fmt_fp32=[False, False], rsplit=0)
            try:
                word, _ = namespace['phase_words'](ph)
                assert ((word >> 30) & 65535) == base
                assert ((word >> 46) & 65535) == ph['nrows']
                status = 'accepted_without_truncation'
            except AssertionError:
                status = 'actual_packer_rejected'
                if first_failure is None:
                    bad, _ = unchecked['phase_words'](ph)
                    first_failure = dict(expert_slot_zero_based=slot, family=family,
                                         phase_zero_based=len(phases), intended_sbase=base,
                                         assertion_rejected=True,
                                         assertions_disabled_sbase=(bad >> 30) & 65535,
                                         illustrative_intended_nrows=1280,
                                         assertions_disabled_nrows=(bad >> 46) & 65535)
            phases.append((slot, family, base, status))
            base += counts[family]
    assert first_failure['expert_slot_zero_based'] == 292
    assert first_failure['family'] == 'w2'
    assert first_failure['intended_sbase'] == 65568
    assert first_failure['assertions_disabled_sbase'] == 32
    assert first_failure['assertions_disabled_nrows'] == 1281
    assert base == 76384 and len(phases) == 1023
    for boundary in (0, 65535):
        ph = dict(bf=False, K=2304, nbeat=64, sbase=boundary, nrows=1280,
                  fmt_fp32=[False, False], rsplit=0)
        word, _ = namespace['phase_words'](ph)
        assert (word >> 30) & 65535 == boundary
    rtl = blob(PIN, SPINE)
    pair = blob(PIN, PAIR)
    assert b'wire [15:0] sbase = pw[45:30];' in rtl
    assert b'parameter integer PHW = 6' in rtl and b'parameter integer PHW = 6' in pair
    pins = {path: dict(commit=commit, sha256=hashlib.sha256(data).hexdigest())
            for commit, path, data in ((PIN, PACKER, source), (PIN, SPINE, rtl),
                                       (PIN, PAIR, pair), ('0fb58ac09', CANDIDATE, packed_candidate))}
    return dict(schema='opentallas.parent.rom-descriptor-width-counterexample.v1',
                source_pins=pins, maximum_experts=stage['experts'], phase_entries=len(phases),
                PHW_current=6, phase_entry_capacity=64, phase_bits_required=10,
                per_family_stream_words=counts, total_stream_words=base,
                stream_address_bits_required=17, descriptor_sbase_bits_current=16,
                first_failure=first_failure,
                rejected_phase_count=sum(p[3] == 'actual_packer_rejected' for p in phases),
                verdict='CONFIRMED_EXISTING_DESCRIPTOR_CANNOT_ENCODE_CANDIDATE',
                explanation='PHW widening alone is insufficient. Actual packer rejects overflow; disabling assertions aliases the base and corrupts the adjacent nrows field.',
                exclusions=['full matrix assignment', 'compact descriptor hardware/service',
                            'physical fit', 'connected token execution'],
                physical_admission=False, engine_RTL_build_ready=False, adopt=False)

if __name__ == '__main__':
    print(json.dumps(replay(), indent=2))
