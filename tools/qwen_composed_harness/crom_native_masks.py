#!/usr/bin/env python3
"""Released-image masks for the native TP8 constant ROM (48 x ot_rom_4096x266_m8, ot_qfd_crom TP=8).

Q-FUNC step 1 of replacing the whole-token harness's C++ ROM arrays (RomVmAdapter::constants) by real mapped
memory: the masks are built from EXACTLY the per-stage crom.hex images the PASSing whole-token runs consumed
(36 decoder stages + the head stage's final-norm image), never from a re-derivation of the checkpoint.

Every word of every stage image is accounted for, fail-closed:
  ZERO   [0,QK0) [POST0,QSCALE)  must be 0 (folded norms)          -> no store
  QK     [QK0,POST0)             narrow, row L*138 + (a-QK0)/64     high 32 bits must be 0
  QSCALE QSCALE                  must equal the hardwired word      -> no store
  ROPE   [ROPE0,OSC0)            wide,   row (a-ROPE0)/64           must be identical in all 36 stages
  OSC    [OSC0,DSC0)             narrow, row L*138 + 10 + (a-OSC0)/64
  DSC    [DSC0,END)              narrow, row L*138 + 74 + (a-DSC0)/64
  HEAD stage [0,4096)            narrow, row 4968 + a/64; every other head word must be 0
Store layout and bit order are the macro's (8-way bitline mux), as tools/qwen_native_memory/make_crom_fixture.py.

Also emits the exhaustive read-test vectors for tb_crom_released_tp8.sv: one test per stored row per stage plus
QSCALE and ZERO probes per stage. Expected words come from the stage images (comparison only).
"""
import argparse
import hashlib
import json
from pathlib import Path

QK0, POST0, QSCALE, ROPE0, OSC0, DSC0, END = 4096, 4736, 8832, 8833, 533121, 537217, 541313
LROWS, QKR, FN0, HEAD, HEAD_N = 138, 10, 36 * 138, 36, 4096
QSCALE_WORD = 0x3db504f300000000
NARROW_ROWS, WIDE_ROWS = 8192, 8192


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_image(path, n):
    words, addr = [0] * n, 0
    with open(path) as f:
        for line in f:
            line = line.split('//')[0]
            for tok in line.split():
                if tok[0] == '@':
                    addr = int(tok[1:], 16)
                    continue
                if addr >= n:
                    raise SystemExit(f'FAIL image word beyond {n}: {path}')
                words[addr] = int(tok, 16)
                addr += 1
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', type=Path, required=True, help='banks/images (layer<L>/die<r>/crom.hex)')
    ap.add_argument('--head-crom', type=Path, required=True, help='head final-norm crom.hex used by the head stage')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    narrow = [[None] * 64 for _ in range(NARROW_ROWS)]
    wide = [[None] * 64 for _ in range(WIDE_ROWS)]
    inputs, tests, rope_ref = {}, [], None

    def put(store, row, lane, value, what):
        old = store[row][lane]
        if old is not None and old != value:
            raise SystemExit(f'FAIL store conflict {what} row {row} lane {lane}')
        store[row][lane] = value

    for L in range(36):
        dies = [a.images / f'layer{L}' / f'die{r}' / 'crom.hex' for r in range(8)]
        hs = {str(p): sha(p) for p in dies}
        if len(set(hs.values())) != 1:
            raise SystemExit(f'FAIL layer{L}: rank crom images differ (one shared ROM cannot serve them)')
        inputs.update(hs)
        w = read_image(dies[0], END)
        for x in range(0, QK0):
            if w[x]:
                raise SystemExit(f'FAIL layer{L} ZERO word {x} = {w[x]:x}')
        for x in range(POST0, QSCALE):
            if w[x]:
                raise SystemExit(f'FAIL layer{L} ZERO word {x} = {w[x]:x}')
        if w[QSCALE] != QSCALE_WORD:
            raise SystemExit(f'FAIL layer{L} QSCALE {w[QSCALE]:x}')
        rope = w[ROPE0:OSC0]
        if rope_ref is None:
            rope_ref = rope
        elif rope != rope_ref:
            raise SystemExit(f'FAIL layer{L} ROPE differs from layer0 (shared store impossible)')
        for base, end, row0 in ((QK0, POST0, L * LROWS), (OSC0, DSC0, L * LROWS + QKR), (DSC0, END, L * LROWS + QKR + 64)):
            for x in range(base, end):
                if w[x] >> 32:
                    raise SystemExit(f'FAIL layer{L} narrow word {x} has high bits {w[x]:x}')
                put(narrow, row0 + (x - base) // 64, (x - base) % 64, w[x], f'layer{L}@{x}')
            for r in range((end - base) // 64):
                tests.append((L, base + 64 * r, 0, [w[base + 64 * r + l] for l in range(64)]))
        if L == 0:
            for x in range(ROPE0, OSC0):
                put(wide, (x - ROPE0) // 64, (x - ROPE0) % 64, w[x], f'rope@{x}')
        for r in range(L, WIDE_ROWS, 36):   # every wide row once, rotated over the stages (stage-independent store)
            tests.append((L, ROPE0 + 64 * r, 0, [w[ROPE0 + 64 * r + l] for l in range(64)]))
        tests.append((L, QSCALE, 1, [QSCALE_WORD] * 64))
        tests.append((L, 0, 0, [0] * 64))
        tests.append((L, POST0, 0, [0] * 64))
        print(f'stage {L} ok', flush=True)
    inputs[str(a.head_crom)] = sha(a.head_crom)
    h = read_image(a.head_crom, END)
    for x in range(HEAD_N, END):
        if h[x]:
            raise SystemExit(f'FAIL head word {x} outside final norm = {h[x]:x}')
    for x in range(HEAD_N):
        if h[x] >> 32:
            raise SystemExit(f'FAIL head word {x} has high bits')
        put(narrow, FN0 + x // 64, x % 64, h[x], f'head@{x}')
    for r in range(HEAD_N // 64):
        tests.append((HEAD, 64 * r, 0, [h[64 * r + l] for l in range(64)]))

    outputs = {}
    for kind, store, cols, lanes, width in (('n', narrow, 8, 8, 32), ('w', wide, 16, 4, 64)):
        for c in range(cols):
            for d in range(2):
                phys = [0] * 512
                for local in range(4096):
                    vals = store[d * 4096 + local][c * lanes:(c + 1) * lanes]
                    if all(v is None for v in vals):
                        continue
                    word = sum((v or 0) << (width * k) for k, v in enumerate(vals))
                    for bit in range(lanes * width):
                        if (word >> bit) & 1:
                            phys[local // 8] |= 1 << (bit * 8 + local % 8)
                p = a.out / f'crom_{kind}_c{c}_d{d}.viamap.hex'
                p.write_text(''.join(f'{x:0532x}\n' for x in phys))
                outputs[p.name] = sha(p)
    with open(a.out / 'tests_hdr.hex', 'w') as fh, open(a.out / 'tests_exp.hex', 'w') as fe:
        for st, base, bc, exp in tests:
            fh.write(f'{(st << 32) | (bc << 31) | base:016x}\n')
            fe.write(''.join(f'{v:016x}\n' for v in exp))
    used_n = sum(1 for r in narrow if any(v is not None for v in r))
    used_w = sum(1 for r in wide if any(v is not None for v in r))
    man = {'schema': 'opentallas.qwen-crom-released-masks.v1', 'tests': len(tests),
           'narrow_rows_stored': used_n, 'wide_rows_stored': used_w,
           'inputs_sha256': inputs, 'masks_sha256': outputs,
           'tests_sha256': {n: sha(a.out / n) for n in ('tests_hdr.hex', 'tests_exp.hex')},
           'exporter_sha256': sha(__file__)}
    (a.out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'PASS masks 48 tests {len(tests)} narrow_rows {used_n} wide_rows {used_w}')


if __name__ == '__main__':
    main()
