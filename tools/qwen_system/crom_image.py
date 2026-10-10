#!/usr/bin/env python3
"""Qwen3-8B ROM die constant ROM (stream qwen-system, 2026-10-08): banking contract, image and bench vectors.

The full-shape stage program (tools/hdc_qwen_fullshape_program_w12.py, TP4, SU_WIDTH 64) reads its constants from a
layer-local stage image of 541,953 x 64 b (tools/hdc_qwen_layer0_rom_w12.constant_words; the head stage reads the
final norm, tools/qwen_o4_fulltoken_binding_w12.write_final_norm).  The C++ runtime swapped that image per stage.  On
the die one constant ROM serves all 37 stages; the stage (layer) index arrives beside the address and the ROM maps
the layer-local address onto one shared store:

  region   layer-local words           content                     store
  ZERO     [0, 4096) [5376, 9472)       folded in/post norm (0)     none (reads return 0)
  QK       [4096, 5376)                 q/k norm tiles, layer L     narrow (32 b / lane), rows L*148 + [0, 20)
  QSCALE   9472                         (0, 1/sqrt(128))            hardwired
  ROPE     [9473, 533761)               cos/sin, 8,192 positions    wide (64 b / lane), rows [0, 8192)
  OSC      [533761, 537857)             o true row scales, layer L  narrow, rows L*148 + 20 + [0, 64)
  DSC      [537857, 541953)             down true row scales        narrow, rows L*148 + 84 + [0, 64)
  FNORM    head stage (L = 36) [0,4096) final norm                  narrow, rows 5328 + [0, 64)

Banking contract (checked here over every constant-ROM read of the stage programs at every position class): lane l
of an SU vector reads layer-local word rb + 64 r + l of one region (rb the region base), so every lane of a vector
reads the same store row r and lane l's word always lives in lane l's column: no crossbar, one row address per macro
column group.  ZERO / QSCALE reads (the qscale op broadcasts one word to all lanes) need no store.

Usage:
  crom_image.py contract --out DIR                    contract check over the stage + head programs (no checkpoint)
  crom_image.py build --snapshot SNAP --out DIR       image, macro via maps, bench vectors, golden cross-check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault('QWEN_O4_TP', '4')
os.environ.setdefault('HDC_SU_WIDTH', '64')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'mem_compiler'))

import numpy as np  # noqa: E402

import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_isa_w12 as QI  # noqa: E402
import hdc_qwen_fullshape_program_w12 as FP  # noqa: E402

SW = 64
H, HD, TMAX = 4096, 128, FP.TMAX
NH, KV = 32 // FP.TP, 8 // FP.TP
QKN = (NH + KV) * HD                      # 1,280 at TP4
QK0 = H
POST0 = H + QKN
QSCALE = 2 * H + QKN                      # 9,472
ROPE0 = QSCALE + 1                        # 9,473
ROPE_N = TMAX * HD // 2                   # 524,288
OSC0 = ROPE0 + ROPE_N                     # 533,761
DSC0 = OSC0 + H                           # 537,857
END = DSC0 + H                            # 541,953
NLAYER = 36
HEAD = 36                                 # stage index of the lm_head stage
QK_ROWS, SC_ROWS = QKN // SW, H // SW     # 20, 64
LROWS = QK_ROWS + 2 * SC_ROWS             # 148 narrow rows a layer
FN_ROW0 = NLAYER * LROWS                  # 5,328
NARROW_ROWS = FN_ROW0 + H // SW           # 5,392
WIDE_ROWS = ROPE_N // SW                  # 8,192
QSCALE_WORD = (int(G.bits(np.float32(1 / np.sqrt(HD)))) << 32)
MACRO = 'ot_rom_4096x266_m8'
MDEPTH, MBITS = 4096, 266
WIDE_LPM, NARROW_LPM = 4, 8               # lanes a macro column: 4 x 64 b, 8 x 32 b (256 of 266 bits)
WIDE_COLS, NARROW_COLS = SW // WIDE_LPM, SW // NARROW_LPM
WIDE_DEPTH, NARROW_DEPTH = -(-WIDE_ROWS // MDEPTH), -(-NARROW_ROWS // MDEPTH)
assert END == 541953 and (WIDE_DEPTH, NARROW_DEPTH) == (2, 2)


def region(layer, a):
    """(kind, store row or None, region base) of layer-local word a at stage `layer` (None kind: out of range)."""
    if layer == HEAD:
        return ('FNORM', FN_ROW0 + a // SW, 0) if a < H else (None, None, None)
    if a < QK0 or POST0 <= a < QSCALE:
        return 'ZERO', None, None
    if a < POST0:
        return 'QK', layer * LROWS + (a - QK0) // SW, QK0
    if a == QSCALE:
        return 'QSCALE', None, None
    if a < OSC0:
        return 'ROPE', (a - ROPE0) // SW, ROPE0
    if a < DSC0:
        return 'OSC', layer * LROWS + QK_ROWS + (a - OSC0) // SW, OSC0
    if a < END:
        return 'DSC', layer * LROWS + QK_ROWS + SC_ROWS + (a - DSC0) // SW, DSC0
    return None, None, None


# ------------------------------------------------------------------------------------------------ programs
def stage_programs():
    """Decoded instruction lists of the TP4 layer stage (die 0; identical constant addressing on every die) and the
    head stage (final norm at constant base 0)."""
    layer = FP.profile(0, post_scale_bases=(OSC0, DSC0))
    prog = [QI.decode_instruction(int(w, 16)) for w in layer['program_hex']]
    from hdc_qwen_fullshape_placement_w12 import matrix
    row = matrix(0, 'lm_head', 151936 // FP.TP, 4096)     # the binding's head geometry (qwen_o4_fulltoken_binding_w12)
    row['scale_base'] = 0
    head = FP.profile_lm_head(0, row, 0)
    hprog = [QI.decode_instruction(int(w, 16)) for w in head['program_hex']]
    return {'layer': prog, 'head': hprog}


def crom_reads(f, pos):
    """Per vector: list of (lane, address) of an SU instruction's constant-ROM operand reads (b and/or c)."""
    if f['unit'] != I.UNIT_SU:
        return []
    lay = type('L', (), dict(H=H, half=HD // 2, HD=HD))()
    dyn = P.dyn_values(lay, 0, pos)
    out = []
    n_out = f['su_nout'] + dyn[f['su_d_nout']] if 'su_d_nout' in f else f['su_nout']
    n_in = f['su_nin'] + dyn[f['su_d_nin']]
    for s, src in (('b', 'b_src'), ('c', 'c_src')):
        if not f[src]:
            continue
        base = f[f'{s}_base'] + dyn[f[f'{s}_d']]
        for o in range(n_out):
            for v in range(-(-n_in // SW)):
                vec = []
                for lane in range(SW):
                    i = v * SW + lane
                    if i < n_in:
                        vec.append((lane, base + o * f[f'{s}_so'] + i * f[f'{s}_si']))
                out.append((s, vec))
    return out


POSITIONS = (0, 1, 63, 64, 255, 256, 4095, 4096, 8190, 8191)


def check_contract(progs):
    """Every constant read of both stage programs at every position class obeys the banking contract."""
    stats = {}
    bad = []
    for stage, prog in progs.items():
        layers = (0, 17, 35) if stage == 'layer' else (HEAD,)
        for pos in POSITIONS:
            for idx, f in enumerate(prog):
                for s, vec in crom_reads(f, pos):
                    for layer in layers:
                        kinds, rows = set(), set()
                        for lane, a in vec:
                            kind, row, rb = region(layer, a)
                            kinds.add(kind)
                            if kind is None:
                                bad.append((stage, pos, idx, s, lane, a, 'out of range'))
                            elif row is not None:
                                rows.add(row)
                                if (a - rb) % SW != lane:
                                    bad.append((stage, pos, idx, s, lane, a, 'lane misaligned'))
                        if len(kinds) != 1 or len(rows) > 1:
                            bad.append((stage, pos, idx, s, sorted(map(str, kinds)), sorted(rows), 'vector spans rows'))
                        k = f'{stage}:{"/".join(sorted(map(str, kinds)))}'
                        stats[k] = stats.get(k, 0) + 1
    return dict(pass_=not bad, violations=bad[:20], n_violations=len(bad), vector_reads_by_stage_region=stats,
                positions=POSITIONS)


# ------------------------------------------------------------------------------------------------ golden
def golden_constants(snapshot, layers=range(NLAYER)):
    """Per layer: qk norm tile (1,280 FP32), o and down true row scales (4,096 BF16 bits each); final norm (FP32 bits).
    The o / down scales are the deployed W8 full-row scales (hdc_qwen_int8_image_w12.quantize_full_rows_then_partition,
    the source of the passing P8191 stage images)."""
    import torch
    from safetensors import safe_open
    from hdc_qwen_int8_image_w12 import quantize_full_rows_then_partition
    torch.set_num_threads(int(os.environ.get('CROM_THREADS', '2')))
    snapshot = Path(snapshot)
    index = json.loads((snapshot / 'model.safetensors.index.json').read_text())['weight_map']

    def t(name):
        with safe_open(str(snapshot / index[name]), framework='pt', device='cpu') as sf:
            return sf.get_tensor(name)
    out = {}
    for L in layers:
        p = f'model.layers.{L}.'
        qn, kn = t(p + 'self_attn.q_norm.weight').float().numpy(), t(p + 'self_attn.k_norm.weight').float().numpy()
        qk = np.concatenate((np.tile(qn, NH), np.tile(kn, KV))).astype(np.float32)
        sc = {}
        for short, name in (('o', 'self_attn.o_proj.weight'), ('down', 'mlp.down_proj.weight')):
            _, s = quantize_full_rows_then_partition(t(p + name), die=0, axis='columns', tp=FP.TP)
            sc[short] = s.view(torch.int16).numpy().view(np.uint16).reshape(-1)
        out[L] = dict(qk=qk, o=sc['o'], down=sc['down'])
        print(f'layer {L}: constants', flush=True)
    fn = t('model.norm.weight').float().numpy().astype(np.float32)
    return out, fn


def stage_word(gold, fnorm, layer, a):
    """The stage image's word (the C++ runtime's crom[a]) -- constant_words / write_final_norm semantics."""
    if layer == HEAD:
        return int(fnorm[a].view(np.uint32)) if a < H else None
    kind, _, _ = region(layer, a)
    g = gold[layer]
    if kind == 'ZERO':
        return 0
    if kind == 'QK':
        return int(g['qk'][a - QK0].view(np.uint32))
    if kind == 'QSCALE':
        return QSCALE_WORD
    if kind == 'ROPE':
        p, d = divmod(a - ROPE0, HD // 2)
        cos, sin, _ = rope_row(p)
        return (int(G.bits(sin[d])) << 32) | int(G.bits(cos[d]))
    if kind == 'OSC':
        return int(g['o'][a - OSC0]) << 16
    if kind == 'DSC':
        return int(g['down'][a - DSC0]) << 16
    return None


_ROPE = {}


def rope_row(p):
    if p not in _ROPE:
        _ROPE[p] = G.rope_tables(p, HD, 1_000_000)
    return _ROPE[p]


def cross_check(snapshot, gold, fnorm, layers):
    """Our stage words == hdc_qwen_layer0_rom_w12.constant_words (the tool that emitted the passing P8191 stage images)
    for the given layers, every word; and the head word list == write_final_norm's."""
    import hdc_qwen_layer0_rom_w12 as L0
    res = {}
    for L in layers:
        lay = FP.LayerZero(None, 0, [dict(base=0, rows=1, k_per_split=1, rounds=1, split=1)] * 4)
        data, bases = L0.constant_words(Path(snapshot), gold[L]['o'], gold[L]['down'], lay, L)
        assert tuple(bases) == (OSC0, DSC0) and len(data) == END, (bases, len(data))
        ref = np.array([(int(G.bits(hi)) << 32) | int(G.bits(lo)) for lo, hi in data], dtype=np.uint64)
        ours = np.array([stage_word(gold, fnorm, L, a) for a in range(END)], dtype=np.uint64)
        res[L] = dict(words=END, mismatches=int((ref != ours).sum()),
                      sha256=hashlib.sha256(ref.tobytes()).hexdigest())
        print(f'cross-check layer {L}: {res[L]["mismatches"]} mismatches of {END}', flush=True)
    return res


# ------------------------------------------------------------------------------------------------ store + macros
def store(gold, fnorm):
    """wide[row][lane] (64 b) and narrow[row][lane] (32 b) of the shared store."""
    wide = np.zeros((WIDE_ROWS, SW), dtype=np.uint64)
    for p in range(TMAX):
        cos, sin, _ = rope_row(p)
        w = (G.bits(sin).astype(np.uint64) << np.uint64(32)) | G.bits(cos).astype(np.uint64)
        wide[p] = w                          # row p = position p: 64 (cos, sin) pairs = lanes 0..63
    narrow = np.zeros((NARROW_ROWS, SW), dtype=np.uint32)
    for L in range(NLAYER):
        g = gold[L]
        r0 = L * LROWS
        narrow[r0:r0 + QK_ROWS] = g['qk'].view(np.uint32).reshape(QK_ROWS, SW)
        narrow[r0 + QK_ROWS:r0 + QK_ROWS + SC_ROWS] = (g['o'].astype(np.uint32) << 16).reshape(SC_ROWS, SW)
        narrow[r0 + QK_ROWS + SC_ROWS:r0 + LROWS] = (g['down'].astype(np.uint32) << 16).reshape(SC_ROWS, SW)
    narrow[FN_ROW0:] = fnorm.view(np.uint32).reshape(-1, SW)
    return wide, narrow


def macro_words(wide, narrow):
    """{instance: [word]} for the 48 ot_rom_4096x266_m8 macros (wide c<col>_d<depth>, narrow likewise)."""
    out = {}
    for c in range(WIDE_COLS):
        for d in range(WIDE_DEPTH):
            rows = wide[d * MDEPTH:(d + 1) * MDEPTH, c * WIDE_LPM:(c + 1) * WIDE_LPM]
            out[f'crom_w_c{c}_d{d}'] = [sum(int(x) << (64 * k) for k, x in enumerate(r)) for r in rows]
    for c in range(NARROW_COLS):
        for d in range(NARROW_DEPTH):
            rows = narrow[d * MDEPTH:(d + 1) * MDEPTH, c * NARROW_LPM:(c + 1) * NARROW_LPM]
            out[f'crom_n_c{c}_d{d}'] = [sum(int(x) << (32 * k) for k, x in enumerate(r)) for r in rows]
    return out


# ------------------------------------------------------------------------------------------------ bench vectors
def vectors(gold, fnorm, progs, seed=1):
    """(layer, [(re, addr) x 64], [expected x 64]) per vector.  Coverage: every stored word (wide rows once,
    narrow rows of every layer / the head), ZERO and QSCALE words, and the program's own read vectors at every
    position class; random lane-enable masks (a disabled lane's expected is 'hold' = None)."""
    rng = np.random.default_rng(seed)
    out = []

    def vec(layer, addrs, mask=None):
        ent = []
        exp = []
        for lane in range(SW):
            a = addrs[lane]
            on = a is not None and (mask is None or mask[lane])
            ent.append((int(on), a if on else 0))
            exp.append(stage_word(gold, fnorm, layer, a) if on else None)
        out.append((layer, ent, exp))

    for r in range(WIDE_ROWS):                               # every RoPE row (layer varies: shared store)
        vec(int(rng.integers(0, NLAYER)), [ROPE0 + r * SW + l for l in range(SW)])
    for L in range(NLAYER):
        for b0, n in ((QK0, QKN), (OSC0, H), (DSC0, H)):
            for r in range(n // SW):
                m = rng.random(SW) < 0.9 if rng.random() < 0.3 else None
                vec(L, [b0 + r * SW + l for l in range(SW)], m)
        vec(L, [QSCALE] * SW)                                 # broadcast
        vec(L, [int(rng.integers(0, QK0)) for _ in range(SW)])          # ZERO (any lane, any word)
        vec(L, [int(rng.integers(POST0, QSCALE)) for _ in range(SW)])
    for r in range(H // SW):
        vec(HEAD, [r * SW + l for l in range(SW)])
    for stage, prog in progs.items():                        # the programs' own vectors
        for pos in (0, 8191, int(rng.integers(1, 8191))):
            layers = (int(rng.integers(0, NLAYER)),) if stage == 'layer' else (HEAD,)
            for f in prog:
                for s, v in crom_reads(f, pos):
                    for L in layers:
                        addrs = [None] * SW
                        for lane, a in v:
                            addrs[lane] = a
                        vec(L, addrs)
    return out


def write_vectors(path, vecs):
    """One line a vector: layer(2 hex) re(16 hex) addr(64 x 6 hex) exp(64 x 16 hex; a lane with re = 0 is not checked)."""
    with open(path, 'w') as fh:
        for layer, ent, exp in vecs:
            re = sum(on << l for l, (on, _) in enumerate(ent))
            fh.write(f'{layer:02x} {re:016x} ' + ''.join(f'{a:06x}' for _, a in reversed(ent)) + ' '
                     + ''.join(f'{0 if e is None else e:016x}' for e in reversed(exp)) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('mode', choices=['contract', 'build'])
    ap.add_argument('--snapshot', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--cross-layers', default='0,35')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    progs = stage_programs()
    con = check_contract(progs)
    rec = dict(schema='opentallas.qwen_crom.v1', tp=FP.TP, su_width=I.SU_WIDTH, tmax=TMAX,
               layout=dict(QK0=QK0, POST0=POST0, QSCALE=QSCALE, ROPE0=ROPE0, OSC0=OSC0, DSC0=DSC0, END=END,
                           LROWS=LROWS, FN_ROW0=FN_ROW0, NARROW_ROWS=NARROW_ROWS, WIDE_ROWS=WIDE_ROWS,
                           macro=MACRO, wide=[WIDE_COLS, WIDE_DEPTH, WIDE_LPM], narrow=[NARROW_COLS, NARROW_DEPTH,
                                                                                         NARROW_LPM],
                           macros=WIDE_COLS * WIDE_DEPTH + NARROW_COLS * NARROW_DEPTH),
               program_instructions={k: len(v) for k, v in progs.items()},
               contract={k.rstrip('_'): v for k, v in con.items()})
    if not con['pass_']:
        (a.out / 'crom_contract.json').write_text(json.dumps(rec, indent=1, default=str))
        raise SystemExit(f'banking contract FAILS: {con["violations"][:3]}')
    if a.mode == 'contract':
        (a.out / 'crom_contract.json').write_text(json.dumps(rec, indent=1, default=str))
        print(json.dumps(rec['contract'], default=str)[:2000])
        return
    import rom_gen as RG
    gold, fnorm = golden_constants(a.snapshot)
    cl = [int(x) for x in a.cross_layers.split(',') if x]
    rec['cross_check'] = cross_check(a.snapshot, gold, fnorm, cl)
    if any(v['mismatches'] for v in rec['cross_check'].values()):
        raise SystemExit('stage image cross-check FAILED')
    wide, narrow = store(gold, fnorm)
    spec = RG.spec_from_sheet(ROOT / 'physical/asap7_memory_macros' / MACRO / f'{MACRO}.json')
    mw = macro_words(wide, narrow)
    recs = [RG.personalise_instance(spec, words, inst, a.out / 'viamap') for inst, words in sorted(mw.items())]
    rec['macros'] = {r['instance']: dict(viamap_sha256=r['viamap_sha256'], crc32=r['signature_crc32'])
                     for r in recs}
    rec['die_signature'] = RG.die_signature(recs)
    vecs = vectors(gold, fnorm, progs)
    write_vectors(a.out / 'crom_vectors.hex', vecs)
    rec['vectors'] = dict(n=len(vecs), lane_reads=sum(sum(on for on, _ in e) for _, e, _ in vecs),
                          sha256=hashlib.sha256((a.out / 'crom_vectors.hex').read_bytes()).hexdigest())
    rec['golden_sha256'] = dict(wide=hashlib.sha256(wide.tobytes()).hexdigest(),
                                narrow=hashlib.sha256(narrow.tobytes()).hexdigest())
    (a.out / 'crom_build.json').write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({k: v for k, v in rec.items() if k != 'macros'}, default=str)[:3000])


if __name__ == '__main__':
    main()
