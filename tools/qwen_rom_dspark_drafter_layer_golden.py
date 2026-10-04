#!/usr/bin/env python3
"""ISA golden of ONE packed DSpark drafter layer program (default-off; checks the RTL run of it).

The drafter layer images (tools/qwen_rom_dspark_images.py on codex/qwen-rom-dspark-execution-20261003:
D<n>-d<die>/{program,segments,crom,matrix_int8,matrix_scale_bf16}.hex + drafter_layer.json; the
program from tools/qwen_rom_dspark_draft_isa.py: S slots at a frozen start, explicit norms, non-causal
over context + slots, every op behind a barrier) are run by the pinned ISA machines exactly as the
position oracle runs a target layer (tools/qwen_rom_position_oracle_w12.run_layer: per segment every
die's instructions, the all-reduce = G.fold in descriptor order), with the dense matvecs on the local
GPU (tools/qwen_rom_dspark_oracle_gpu_w12.GpuDieMachine, bit-exact to G.matvec).

Inputs are explicit and recorded: per slot an FP32 X (hex files) at the program's X bases
(qwen_rom_verify_program_w12.vm_map_p(S)), and a deterministic E4M3 KV history for the context
positions < start (seeded; the same window goes to the RTL as --kv-dir).  Outputs: per slot and die
the X after the layer (hex), the K/V block each die writes (the RTL host's kvblk format), the KV
window (u32 bin), a plan + expect for tools/qwen_rom_rt_vprm_w12.py.

  HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 \
  qwen_rom_dspark_drafter_layer_golden.py --images IMG --layer 0 --x X0,X1,X2 --out OUT [--remote-root R]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault('QWEN_O4_GROUPS', '6144')
os.environ.setdefault('QWEN_O4_TP', '4')
os.environ.setdefault('HDC_SU_WIDTH', '1024')
os.environ.setdefault('HDC_KV_FMT', 'fp8')
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

import hdc_golden as G  # noqa: E402
import hdc_qwen_fullshape_isa_w12 as QI  # noqa: E402
import qwen_rom_position_oracle_w12 as PO  # noqa: E402
import qwen_rom_verify_program_w12 as V  # noqa: E402
import qwen_rom_dspark_oracle_gpu_w12 as GO  # noqa: E402

TP = PO.TP
FILES = ('program.hex', 'segments.hex', 'crom.hex', 'matrix_int8.hex', 'matrix_scale_bf16.hex')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class DrafterImage(PO.StageImage):
    def __init__(self, directory):   # noqa: D401 -- the drafter manifest, not layer<n>_rom.json
        self.dir = Path(directory)
        m = json.loads((self.dir / 'drafter_layer.json').read_text())
        if m['tp'] != TP or m.get('norm_fold', True):
            raise ValueError('expected an explicit-norm TP4 drafter layer')
        self.manifest = {'die': m['die'], 'layer': m['layer'], 'tp': TP, 'matrix_layout': m['matrix_layout'],
                         'post_tp_scale_bases': m['post_tp_scale_bases']}
        self.meta = m
        self.image_sha = {f: sha(self.dir / f) for f in FILES}
        self.layout = {row['base']: row for row in m['matrix_layout']}
        self.program = [QI.decode_instruction(int(line, 16)) for line in (self.dir / 'program.hex').read_text().split()]
        # V.decode_descriptor: an all-reduce over S slots carries its count's high bits in [23:20] (S x 256 words);
        # QI.decode_descriptor reads only [17:10] and folded slot 0 alone (slots 1.. kept per-die partials).
        self.descriptors = [V.decode_descriptor(int(line, 16)) for line in (self.dir / 'segments.hex').read_text().split()]
        lo, hi = [], []
        for line in (self.dir / 'crom.hex').read_text().split():
            if line.startswith('@'):
                continue
            line = line.rjust(16, '0')
            hi.append(int(line[:8], 16)); lo.append(int(line[8:16], 16))
        self.crom = np.stack((G.from_bits(np.array(lo, dtype=np.uint32)), G.from_bits(np.array(hi, dtype=np.uint32))), axis=1)
        self._mat = {}


E4M3 = None


def e4m3_values():
    """All finite E4M3 values as FP32 (the tile's decode)."""
    out = []
    for c in range(256):
        s, e, m = c >> 7, (c >> 3) & 15, c & 7
        if e == 15 and m == 7:
            continue
        v = (2.0 ** (e - 7)) * (1 + m / 8) if e else (2.0 ** -6) * (m / 8)
        out.append(-v if s else v)
    return np.array(out, dtype=np.float32)


def kv_history(lay, start, seed):
    """Deterministic E4M3 window: K and V of context positions < start, zero elsewhere."""
    rng = np.random.default_rng(seed)
    vals = e4m3_values()
    kv = np.zeros(2 * lay.kv_v0, dtype=np.float32)
    kv0 = lay.kv_v0
    for h in range(2):
        for p in range(start):
            t, lane = p // 16, p % 16
            d = np.arange(128)
            kv[((h * 512 + t) * 128 + d) * 16 + lane] = rng.choice(vals, 128)
            kv[kv0 + (h * 8192 + p) * 128 + d] = rng.choice(vals, 128)
    return kv


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--images', type=Path, required=True)
    ap.add_argument('--layer', type=int, required=True)
    ap.add_argument('--x', required=True, help='comma-separated FP32 hex vectors (4,096 words), one per slot')
    ap.add_argument('--seed', type=int, default=20261004)
    ap.add_argument('--kv-window', type=Path, help='per-die context KV instead of the seeded history: L<layer>_die<d>.npy '
                    '(u32 FP32 bits of E4M3 values, 2*kv_v0 words, zero at positions >= start), e.g. a real target '
                    "layer's window (format-valid context with realistic magnitudes)")
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--remote-root', help='image/out paths as the RTL host on EPYC sees them (plan only)')
    a = ap.parse_args()
    if not (G.SU_WIDTH == 1024 and G.KV_FMT == 'fp8'):
        raise SystemExit('run in the oracle arithmetic environment')
    ims = [DrafterImage(a.images / f'D{a.layer}-d{d}') for d in range(TP)]
    if any(im.descriptors != ims[0].descriptors for im in ims):
        raise SystemExit('TP descriptor mismatch')
    xs = [np.array([int(w, 16) for w in Path(p).read_text().split() if not w.startswith('@')], dtype=np.uint32) for p in a.x.split(',')]
    S = len(xs)
    vms_map, vm_elems = V.vm_map_p(S)
    start = ims[0].meta.get('context_program_position', 48) + 1
    ms = [GO.GpuDieMachine(im) for im in ims]
    if a.kv_window:
        kvs = [G.from_bits(np.load(a.kv_window / f'L{a.layer}_die{d}.npy').astype(np.uint32)) for d in range(TP)]
        for k in kvs:
            if k.shape != (2 * ms[0].lay.kv_v0,):
                raise SystemExit('KV window has the wrong extent')
            lay = ms[0].lay
            for h in range(2):
                for p_ in range(start, 8192):
                    if np.any(k[((h * 512 + p_ // 16) * 128 + np.arange(128)) * 16 + p_ % 16]) or \
                            np.any(k[lay.kv_v0 + (h * 8192 + p_) * 128 + np.arange(128)]):
                        raise SystemExit(f'KV window holds position {p_} >= start {start}')
    else:
        kvs = [kv_history(ms[0].lay, start, a.seed)] * TP
    vms = []
    for m, kv in zip(ms, kvs):
        m.vm = np.zeros(max(vm_elems, 1 << 20), dtype=np.float32)
        m.kv = kv.copy()
        vm = m.vm.copy()
        for j, x in enumerate(xs):
            vm[vms_map[j]['X']:vms_map[j]['X'] + 4096] = G.from_bits(x)
        vms.append(vm)
    out = PO.run_layer(ims, ms, vms, 0, start)
    a.out.mkdir(parents=True, exist_ok=True)
    rec = {'schema': 'opentallas.qwen-dspark-drafter-layer-golden.v1', 'layer': a.layer, 'slots': S, 'start': start,
           'images': {f'die{d}': im.image_sha for d, im in enumerate(ims)}, 'x_inputs': {p: sha(p) for p in a.x.split(',')},
           'kv_seed': None if a.kv_window else a.seed,
           'kv_window': {f'die{d}': sha(a.kv_window / f'L{a.layer}_die{d}.npy') for d in range(TP)} if a.kv_window else None,
           'x_bases': [m['X'] for m in vms_map], 'files': {}}
    kvdir = a.out / 'kv'; kvdir.mkdir(exist_ok=True)
    for d in range(TP):
        kvs[d].view(np.uint32).astype('<u4').tofile(kvdir / f'L{a.layer}_die{d}.bin')
    for d, (m, vm) in enumerate(zip(ms, out)):
        for j in range(S):
            p = a.out / f'D{a.layer}_p{j}_die{d}_x.hex'
            p.write_text(''.join(f'{int(w):08x}\n' for w in G.bits(vm[vms_map[j]['X']:vms_map[j]['X'] + 4096])))
            rec['files'][p.name] = sha(p)
        lines = []
        for j in range(S):
            P_ = start + j
            for h in range(2):
                for dd in range(128):
                    lines.append(f'K {j} {h} {dd} {GO_e4m3(m.kv[((h * 512 + P_ // 16) * 128 + dd) * 16 + P_ % 16]):02x}')
            for h in range(2):
                for dd in range(128):
                    lines.append(f'V {j} {h} {dd} {GO_e4m3(m.kv[m.lay.kv_v0 + (h * 8192 + P_) * 128 + dd]):02x}')
        p = a.out / f'D{a.layer}_die{d}_kvblk.hex'
        p.write_text('\n'.join(lines) + '\n')
        rec['files'][p.name] = sha(p)
    # X preload (all slots) and plan / expect for the RTL host
    pre = a.out / 'x_preload.hex'
    pre.write_text(''.join(f'@{vms_map[j]["X"]:x}\n' + ''.join(f'{int(w):08x}\n' for w in xs[j]) for j in range(S)))
    R = Path(a.remote_root) if a.remote_root else a.out.parent
    rimg = R / 'images'
    rout = R / a.out.name
    plan = [f'XBASES {",".join(str(m["X"]) for m in vms_map)}',
            f'STAGE D{a.layer} {a.layer} 0 {start} {S} 0 0 {rout / "x_preload.hex"} ' + ' '.join(str(rimg / f'D{a.layer}-d{d}') for d in range(TP))]
    (a.out / 'plan').write_text('\n'.join(plan) + '\n')
    exp = {'stages': {f'D{a.layer}': {'x': {f'p{j}_die{d}': str(rout / f'D{a.layer}_p{j}_die{d}_x.hex') for j in range(S) for d in range(TP)},
                                      'kv': {f'die{d}': str(rout / f'D{a.layer}_die{d}_kvblk.hex') for d in range(TP)}}}}
    (a.out / 'expect.json').write_text(json.dumps(exp, indent=1) + '\n')
    (a.out / 'golden.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('layer', 'slots', 'start', 'x_bases')}))


def GO_e4m3(v):
    b = int(G.bits(np.float32(v)))
    s, e, m = b >> 31, (b >> 23) & 255, b & 0x7fffff
    if e == 0 and m == 0:
        return s << 7
    if 121 <= e <= 135 and m & 0xfffff == 0:
        return (s << 7) | ((e - 120) << 3) | (m >> 20)
    if e == 120 and m & 0x1fffff == 0:
        return (s << 7) | 4 | (m >> 21)
    if e == 119 and m & 0x3fffff == 0:
        return (s << 7) | 2 | (m >> 22)
    if e == 118 and m == 0:
        return (s << 7) | 1
    raise ValueError(f'not E4M3: {b:08x}')


if __name__ == '__main__':
    main()
