#!/usr/bin/env python3
"""Enroll released L20 expert41/65 G/U rows into one reusable SIMT kernel.

Software/image preparation only. Expected payloads are separate comparators,
never installed producer inputs. No RTL launch, producer export or parent claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/gpu_sys'))
import isa
import machine as MC
import hdc_golden as G
import hdc_golden_v41 as V
from dshbm_expert_workgroup import steer

EXPERTS = (41, 65)
CODE_BASE, EXP_BASE, OUT_BASE, WEIGHT_BASE = 0x1000, 0x8000, 0x30000, 0x100000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def words(path):
    return [int(v, 16) for v in Path(path).read_text().split()]


def writehex(path, values, width):
    Path(path).write_text(''.join(f'{int(v):0{width}x}\n' for v in values))


def simt_weight_image(packed, scales):
    """Existing SIMT TCBMMA lockstep order, 288 bytes / nine sectors per line."""
    codes = np.empty((12, 5120), dtype=np.uint8)
    codes[:, 0::2], codes[:, 1::2] = packed & 15, packed >> 4
    exponents = scales.astype(np.int16) - 127
    image = np.zeros((288, 288), dtype=np.uint8)
    for index, (row, group, t) in enumerate(MC.bd_issue(12, 3, 8)):
        e = np.zeros(8, dtype='<i2')
        for lane in range(8):
            block = (int(group) * 8 + lane) * 8 + int(t)
            if block < 160:
                image[index, lane * 32:(lane + 1) * 32] = codes[row, block * 32:(block + 1) * 32]
                e[lane] = exponents[row, block]
        image[index, 256:272] = e.view(np.uint8)
    return image.reshape(-1), codes, exponents


def kernel():
    ins = []
    def emit(op, d=0, a=0, b=0, imm=0):
        ins.append(isa.enc(op, d, a, b, imm))
    for address in range(24):
        emit('UMOVI', 6, imm=CODE_BASE + 1024 * address)
        emit('LDG', 0, 6, 127)
        emit('LDG', 1, 6, 127, 512)
        emit('UMOVI', 7, imm=EXP_BASE + 32 * address)
        emit('LDG', 2, 7, 7)
        emit('TCXB', 0, 0, 1, address)
        emit('TCXE', 0, 2, 0, address)
    emit('UMOVI', 4, imm=WEIGHT_BASE)
    emit('UMOVI', 5, imm=0)  # actual TC result shared-memory base
    emit('TCBMMA', 4, 5, 3, 12 | (1 << 12) | (8 << 16))
    emit('TCWAIT')
    emit('LDS', 3, 5, 11)
    conversion_pc = len(ins)
    emit('CVTBF16', 4, 3)
    emit('UMOVI', 8, imm=OUT_BASE)
    emit('STG', 4, 8, 11)
    emit('MEMBAR')
    emit('EXIT')
    return ins, conversion_pc


def prepare(gu, inputs, retained, weight_rows, out):
    record = json.loads((gu / 'record.json').read_text())
    if (record['status'] != 'PASS_ACTUAL_SOURCE_ROUTED_GU_ALL_ROWS'
            or record['layer'] != 20 or record['position'] != 1048575):
        raise ValueError('original exact L20 released GU record required')
    source_pins = {'GU_record': sha(gu / 'record.json')}
    for field, name in [('activation_u32', 'ffn_norm.u32'), ('router_ids_u32', 'expert_ids.u32')]:
        source_pins[name] = sha(inputs / name)
        if source_pins[name] != record[field]['sha256']:
            raise ValueError('original actual capture changed: ' + name)
    x = G.from_bits(np.fromfile(inputs / 'ffn_norm.u32', dtype='<u4'))
    ids = tuple(map(int, np.fromfile(inputs / 'expert_ids.u32', dtype='<u4')))
    if x.shape != (5120,) or not np.isfinite(x).all() or ids != tuple(record['router_ids']) or ids[:2] != EXPERTS:
        raise ValueError('require actual K5120 activation and original routed expert order')
    provenance = json.loads((inputs / 'source.json').read_text())
    released = json.loads((weight_rows / 'source.json').read_text())
    if (released != json.loads((inputs / 'weight_rows.json').read_text())
            or released['layer'] != 20 or released['expert_ids'] != list(ids)
            or Path(released['checkpoint']).name != provenance['checkpoint_revision']
            or provenance['arith'] != 'chunk8' or provenance['position'] != record['position']):
        raise ValueError('released checkpoint/capture provenance mismatch')
    for name, pin in provenance['producer_golden'].items():
        if sha(ROOT / name) != pin['sha256']:
            raise ValueError('original golden source changed: ' + name)
    source_pins['capture_provenance'] = sha(inputs / 'source.json')
    source_pins['released_weight_manifest'] = sha(weight_rows / 'source.json')
    arrays = {}
    for t in released['tensors']:
        if t['expert'] not in EXPERTS:
            continue
        path = weight_rows / t['file']
        shape = [2304, 2560 if t['kind'] == 'packed' else 160]
        if t['shape'] != shape or path.stat().st_size != t['bytes'] or sha(path) != t['sha256']:
            raise ValueError('released checkpoint tensor changed: ' + str(path))
        arrays[t['expert'], t['matrix'], t['kind']] = np.memmap(path, dtype=np.uint8, mode='r', shape=tuple(shape))
        source_pins[str(path)] = t['sha256']
    if set(arrays) != {(e, m, k) for e in EXPERTS for m in ('w1', 'w3') for k in ('packed', 'scale')}:
        raise ValueError('all four released G/U matrices required')
    V.set_arith('chunk8')
    xq, xe = V.quant_fp8(x)
    # Existing E4M3 encoder; zero inactive chunks, signed ten-bit exponents.
    code_beats = np.zeros((24, 8, 32), dtype='<u4')
    exponent_beats = np.zeros((24, 8), dtype='<u4')
    for a in range(24):
        group, t = divmod(a, 8)
        for lane in range(8):
            block = (group * 8 + lane) * 8 + t
            if block < 160:
                code_beats[a, lane] = isa.e4m3_encode(G.bits(xq[block * 32:(block + 1) * 32]))
                exponent_beats[a, lane] = int(xe[block]) & 0x3ff
    cases = {(c['die'], c['sm']): c for c in record['cases']}
    if len(cases) != len(record['cases']):
        raise ValueError('duplicate original source descriptor')
    out.mkdir(parents=True, exist_ok=False)
    code_beats.tofile(out / 'activation_codes.u32')
    exponent_beats.tofile(out / 'activation_exponents.u32')
    ins, cvt_pc = kernel()
    writehex(out / 'kernel.hex', ins, 16)
    seen = {(e, m): set() for e in EXPERTS for m in ('w1', 'w3')}
    expected = {key: np.zeros(2304, dtype='<u4') for key in seen}
    descriptors = []
    vm = MC.Machine(nd=1, nsm=1, nl=128, mem_bytes=WEIGHT_BASE + 288 * 288, L=16)
    mem = vm.dies[0].mem
    mem[CODE_BASE:CODE_BASE + code_beats.nbytes] = code_beats.view(np.uint8).reshape(-1)
    mem[EXP_BASE:EXP_BASE + exponent_beats.nbytes] = exponent_beats.view(np.uint8).reshape(-1)
    for die in range(96):
        for d in steer(ids, die):
            if d.expert not in EXPERTS:
                continue
            c = cases[die, d.sm]
            if (not c['exact'] or c['mismatches'] or c['exit'] or c['expert'] != d.expert
                    or c['matrix'] != d.matrix or c['rows'] != [d.row_start, d.row_stop]):
                raise ValueError('original descriptor identity/verdict changed')
            source = gu / f'die{die:02}_sm{d.sm:02}'
            packed, scales = [arrays[d.expert, d.matrix, kind][d.row_start:d.row_stop].copy()
                              for kind in ('packed', 'scale')]
            for field, data in [('packed', packed), ('scale', scales)]:
                if hashlib.sha256(data.tobytes()).hexdigest() != c[field + '_sha256']:
                    raise ValueError('released checkpoint row digest mismatch: ' + field)
            image, codes, e = simt_weight_image(packed, scales)
            q = V.E2M1_VALUES[codes & 7] * np.where(codes & 8, -1., 1.)
            golden = G.bits(V.linear_q(V.Q8(q, e.astype(np.int64)), x))
            if not np.isfinite(G.from_bits(golden)).all() or np.any(golden & 0xffff):
                raise ValueError('golden finite/BF16 contract')
            # Execute the newly enrolled software kernel with real input memory.
            mem[WEIGHT_BASE:] = image
            mem[OUT_BASE:OUT_BASE + 48] = 0xa5
            vm.launch({(0, 0): ins}, token=0, pos=record['position'])
            actual = mem[OUT_BASE:OUT_BASE + 48].copy().view('<u4')
            if not np.array_equal(actual, golden):
                raise ValueError(f'enrolled SIMT image differs from golden: die{die} sm{d.sm}')
            key = d.expert, d.matrix
            rows = set(range(d.row_start, d.row_stop))
            if seen[key] & rows:
                raise ValueError('duplicate consumer rows')
            seen[key] |= rows
            expected[key][d.row_start:d.row_stop] = golden
            folder = out / f'die{die:02}_sm{d.sm:02}'
            folder.mkdir()
            image.tofile(folder / 'weights.bin')
            writehex(folder / 'expected_bf16.hex', golden, 8)
            descriptors.append(dict(die=die, source_sm=d.sm, expert=d.expert,
                matrix=d.matrix, row_start=d.row_start, row_stop=d.row_stop,
                w2_op=EXPERTS.index(d.expert), native_op=0,
                conversion_pc=cvt_pc, conversion_source_register=3,
                conversion_destination_register=4, valid_lanes=12,
                weight_image=str(folder.relative_to(out) / 'weights.bin'),
                weight_sha256=sha(folder / 'weights.bin'),
                released_packed_sha256=c['packed_sha256'], released_scale_sha256=c['scale_sha256'],
                original_actual_result_sha256=sha(source / 'out.txt')))
    if len(descriptors) != 768 or any(v != set(range(2304)) for v in seen.values()):
        raise ValueError('full four-vector row enrollment required')
    for (expert, matrix), values in expected.items():
        name = 'g.mem' if matrix == 'w1' else 'u.mem'
        original = retained / f'expert{expert}' / name
        if words(original) != list(map(int, values)):
            raise ValueError('new released-row golden differs from retained actual GU boundary')
        source_pins[str(original)] = sha(original)
        writehex(out / f'expert{expert}_{matrix}_expected_bf16.hex', values, 8)
    manifest = dict(scope='software/full released row images and comparator-only BF16; not live GU RTL',
        status='PASS_SOFTWARE_IMAGE_ENROLLMENT', layer=20, source_position=record['position'],
        experts=list(EXPERTS), rows_per_matrix=2304, total_GU_rows=9216,
        descriptor_count=len(descriptors), kernel_words=len(ins), conversion_pc=cvt_pc,
        image_memory=dict(codes=CODE_BASE, exponents=EXP_BASE, weights=WEIGHT_BASE, output=OUT_BASE),
        memory_note='private component fixture addresses; no parent physical allocation claim',
        producer_parameters=dict(NL=128, HAS_BD=1, BD_XDEPTH=64, TC_RMAX=1024),
        checkpoint_revision=provenance['checkpoint_revision'],
        checkpoint_binding='full released tensor hashes match original manifest; every row slice matches original GU source digests',
        rounding='existing CVTBF16 after TCWAIT/LDS; golden linear_q chunk8 with final RNE BF16',
        expected_payload_installed_as_input=False, live_export_present=False,
        transaction_note='caller must bind actual token/position/owner; software token0 is not runtime authority',
        source_sha256=source_pins, descriptors=descriptors)
    (out / 'enrollment.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('PASS_SOFTWARE_IMAGE_ENROLLMENT descriptors=768 GUrows=9216 experts=41,65', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('gu', 'inputs', 'retained', 'weight-rows', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    prepare(a.gu, a.inputs, a.retained, a.weight_rows, a.out)
