"""Source-bound partial relocation; invalid image holes prohibit publication."""
import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
import hdc_isa_v41 as I

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PIN = '2a49807654c259b9d3abefecead88c97871edfc6'
LAYOUT_PATH = 'results/quality/w16_engram_initializer_20261001/frozen_closure.json'
PROGRAM_PIN = '4080bb5fd'
PROGRAM_PATH = 'results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2.json'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(pin, path):
    return subprocess.check_output(['git', 'show', pin + ':' + path], cwd=ROOT)

def authority(candidate=None):
    raw = read(LAYOUT_PIN, LAYOUT_PATH)
    expected = json.loads(raw)
    if candidate is not None and candidate != expected:
        raise ValueError('immutable layout/source/validity authority mismatch')
    return expected, sha(raw)

def require_publication(candidate):
    layout, _ = authority(candidate)
    for rank in layout['ranks']:
        if rank['complete'] is not True or rank['complete_image_sha256'] is None:
            raise ValueError('L1 slots [508800,529280) invalid; complete image unavailable')
    if layout['finite_service']['actual_routes_capture_mux_CDC_deadlines_and_power_bound'] is not True:
        raise ValueError('actual coefficient service unbound')
    return True

def build(candidate=None):
    layout, layout_sha = authority(candidate)
    isa_raw = read('d2c28c279', 'tools/hdc_isa_v41.py')
    if sha(Path(I.__file__).read_bytes()) != sha(isa_raw):
        raise ValueError('ISA codec source mismatch')
    program_raw = read(PROGRAM_PIN, PROGRAM_PATH)
    program = json.loads(program_raw)
    records = []
    off, width = I.FULL_LAYOUT['b_base']
    mask = ((1 << width) - 1) << off
    for rank in program['ranks']:
        path = PROGRAM_PATH.removesuffix('.json') + f'.rank{rank["rank"]}.templates.bin.gz'
        original = gzip.decompress(read(PROGRAM_PIN, path))
        if sha(original) != rank['encoded_template_sha256'] or len(original) != rank['encoded_instruction_count'] * 256:
            raise ValueError('rank original program SHA/extent')
        patched = bytearray(original)
        bindings = []
        offset = 0
        for stage in rank['stages']:
            for missing in stage['unbound']:
                if stage['layer'] not in (1, 14) or missing['operand'] != 'b' or missing['elements'] != 20480:
                    raise ValueError('unexpected generated operand identity')
                pc = offset + missing['instruction']
                word = int.from_bytes(original[pc*256:(pc+1)*256], 'little')
                fields = I.decode(word, full_shape=True)
                if fields['b_src'] != I.SRC_CLO or fields['m1'] != I.M1_AB or fields['m2'] != I.M2_C:
                    raise ValueError('actual generated consumer source/order')
                if any(fields[k] != value for k, value in
                       [('b_so',5120),('b_si',1),('b_half',0),('su_nin',5120),('su_nout',4),('pred',0)]):
                    raise ValueError('actual generated consumer extent/stride/half/predicate')
                base = 508800 if stage['layer'] == 1 else 529280
                valid = stage['layer'] == 14
                if valid:
                    new = (word & ~mask) | (base << off)
                    if (new ^ word) & ~mask:
                        raise AssertionError('non-base instruction bits changed')
                    patched[pc*256:(pc+1)*256] = new.to_bytes(256, 'little')
                bindings.append(dict(layer=stage['layer'], pc=pc, operand='b',
                    original_encoded_base=fields['b_base'], proposed_base=base,
                    diagnostic_encoded_base=base if valid else fields['b_base'],
                    source_valid=valid, published_base=None,
                    logical_span=[base, base+20480]))
            offset += stage['instruction_count']
        if len(bindings) != 2:
            raise ValueError('rank generated operand coverage')
        changed = [pc for pc in range(len(original)//256)
                   if original[pc*256:(pc+1)*256] != patched[pc*256:(pc+1)*256]]
        if changed != [b['pc'] for b in bindings if b['source_valid']]:
            raise AssertionError('unexpected instruction changes')
        records.append(dict(rank=rank['rank'], original_program_sha256=sha(original),
            diagnostic_partial_program_sha256=sha(patched), changed_pcs=changed,
            bindings=bindings, runnable=False, published_program_sha256=None))
    return dict(schema='w11.frozen-publication.v1', layout_commit=LAYOUT_PIN,
        layout_path=LAYOUT_PATH, layout_sha256=layout_sha,
        program_commit=PROGRAM_PIN, program_sha256=sha(program_raw),
        ISA_sha256=sha(isa_raw), ranks=records,
        unfulfilled_logical_slots_per_rank=[508800,529280],
        unfulfilled_FP32_values_per_rank=20480, unfulfilled_CROM64_bytes_per_rank=163840,
        required_address_bits=20, old_19bit_aperture_sufficient=False,
        exact_missing_physical_slots='for each a in [508800,529280): bank=(a//3)%45,row=(a//3)//45,slot=a%3',
        finite_service=layout['finite_service'], actual_service_bound=False,
        complete_image_sha256=None, image_admission=False, hardware_admission=False,
        publication_blockers=['L1 retained q/k actual payload authority absent',
                              'complete valid immutable image absent',
                              'actual physical homes/ports/CDC/service unbound'],
        checkpoint_payload_reads=0, exported_runnable_binary=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(build(), indent=2, sort_keys=True)+'\n')
