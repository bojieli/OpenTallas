#!/usr/bin/env python3
"""Native TP8 attention vectors and admitted-run receipts (4 query heads, one FP8 KV head).

Q transport preserves FP32; the consumer must round RNE to BF16, as decode_token_tp
matvec does. The PV split is derived from the actual TP8 group count, not inherited
from a TP4 vector suite. This gate covers attention arithmetic/control, not a full token.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import qwen_nearhbm_attn_ref as R

ROOT = Path(__file__).resolve().parents[1]


def configure(groups):
    R.NH, R.KVH, R.GQ, R.GROUPS = 4, 1, 4, groups
    R.S_SC, R.S_PV = R.G.attn_splits(R.HD, groups)
    R.RES = R.S_PV // R.STACKS
    if R.S_SC != 128 or R.RES % 8:
        raise ValueError("native HD128 profile requires score split128 and PV residues divisible by8")


def source_receipt():
    paths = [ROOT / 'tools/hdc_golden.py', ROOT / 'tools/qwen_nearhbm_attn_ref.py', Path(__file__),
             ROOT / 'rtl/test/nearhbm/tb_qwen_nearhbm_attn.cpp',
             ROOT / 'rtl/test/nearhbm/ot_qwen_nearhbm_attn_die_tb.sv']
    paths += sorted((ROOT / 'rtl/hdc/nearhbm').glob('*.sv'))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def vectors(ctx, seed, kind, outdir, groups):
    configure(groups)
    outdir.mkdir(parents=True, exist_ok=True)
    q, k, v = R.make_case(ctx, seed, 'normal' if kind == 'precision_ties' else kind)
    if kind == 'precision_ties':
        # Even/odd BF16 midpoint ties, adjacent lower FP32 ulps, signs and subnormal ties.
        bits = np.array([0x3f808000, 0x3f818000, 0x3f808001, 0x3f807fff,
                         0xbf808000, 0xbf818000, 0x00008000, 0x00018000], dtype=np.uint32)
        q = np.resize(bits, (4, 128)).view(np.float32).copy()
    gold = R.golden_die(q, k, v)
    # Denominator follows the canonical lane_sum CHUNK independent of PV split.
    maxima, denom = [], []
    for h in range(4):
        scores = R.G.mul(R.G.matvec_il(k[:, 0, :], R.G.to_bf16(q[h]), R.S_SC), R.SCALE)
        m = scores.max()
        maxima.append(R.G.bits(m))
        denom.append(R.G.bits(R.G.lane_sum(R.G.exp(R.G.add(scores, R.G.neg(m))))))
    (outdir / 'q.hex').write_text(''.join(f'{int(b):08x}\n' for b in R.G.bits(q).reshape(-1)))
    with (outdir / 'kv.hex').open('w') as f:
        for arr in (R.fp8_encode(k), R.fp8_encode(v)):
            for t in range(ctx):
                f.write(bytes(arr[t, 0, ::-1]).hex() + '\n')
    (outdir / 'gold.hex').write_text(''.join(f'{int(b):08x}\n' for b in R.G.bits(gold).reshape(-1)))
    (outdir / 'check.hex').write_text(''.join(f'{int(b):08x}\n' for b in
        np.concatenate([np.asarray(maxima), np.asarray(denom)])))
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in outdir.glob('*.hex')}
    meta = dict(schema='qwen-tp8-attention-native-v1', ctx=ctx, position=ctx-1, seed=seed, kind=kind,
                q_heads=4, kv_heads=1, hd=128, groups=groups, attn_splits=[R.S_SC, R.S_PV],
                q_transport='FP32', consumer_q='BF16 RNE', kv='FP8 E4M3', outputs=512,
                output_beats=32, input_beats=32, hashes=hashes, source_hashes=source_receipt(),
                qualification='ATTENTION_COMPONENT_ONLY')
    (outdir / 'meta.json').write_text(json.dumps(meta, indent=2)+'\n')
    print(json.dumps(meta))
    return meta


def run(binary, vecdir, out, stall, mutant, maxcyc):
    meta = json.loads((vecdir / 'meta.json').read_text())
    for name, sha in meta['hashes'].items():
        if hashlib.sha256((vecdir / name).read_bytes()).hexdigest() != sha:
            raise ValueError(f'vector hash mismatch: {name}')
    cmd = [str(binary.resolve()), str(vecdir.resolve()), '16', '750', str(maxcyc), str(stall), mutant]
    result = subprocess.run(cmd, text=True, capture_output=True)
    try:
        record = json.loads(result.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        record = None
    # A crash/timeout/invalid request is not an observed arithmetic mutant.
    positive = result.returncode == 0 and record and record.get('exact') and record.get('outputs') == 512
    negative = result.returncode == 1 and record and (record.get('data_mismatches', 0) > 0 or record.get('fault', 0) > 0)
    passed = positive if mutant == 'none' else negative
    receipt = dict(schema='qwen-tp8-attention-native-run-v1', command=cmd,
                   binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(), vectors=meta,
                   exit_code=result.returncode, record=record, stdout=result.stdout, stderr=result.stderr,
                   stalls=stall, mutant=mutant, passed=bool(passed), scope='ATTENTION_COMPONENT_ONLY')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(passed=bool(passed), mutant=mutant, record=record)))
    return bool(passed)


def counterproof(ctx, seed, kind, out):
    configure(3072)
    q, k, v = R.make_case(ctx, seed, kind)
    native = R.golden_die(q, k, v)
    R.S_PV = 512
    legacy = R.golden_die(q, k, v)
    diff = R.G.bits(native) != R.G.bits(legacy)
    record = dict(schema='qwen-tp8-pv-split-counterproof-v1', ctx=ctx, position=ctx-1,
                  seed=seed, kind=kind, groups=3072, native_splits=[128,256],
                  legacy_splits=[128,512], compared_bits_words=512,
                  differing_words=int(diff.sum()), first_different=int(np.flatnonzero(diff)[0]) if diff.any() else None,
                  native_sha256=hashlib.sha256(R.G.bits(native).tobytes()).hexdigest(),
                  legacy_sha256=hashlib.sha256(R.G.bits(legacy).tobytes()).hexdigest(),
                  operand_sha256={name:hashlib.sha256(arr.tobytes()).hexdigest()
                                  for name, arr in [('q',q),('k',k),('v',v)]},
                  source_hashes=source_receipt(), qualification='COUNTEREVIDENCE_ONLY')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record))
    return bool(diff.any())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    a = sub.add_parser('vectors')
    a.add_argument('--ctx', type=int, required=True)
    a.add_argument('--seed', type=int, default=1)
    a.add_argument('--groups', type=int, default=3072)
    a.add_argument('--kind', choices=(*R.KINDS, 'precision_ties'), default='normal')
    a.add_argument('--out', type=Path, required=True)
    b = sub.add_parser('run')
    b.add_argument('--binary', type=Path, required=True)
    b.add_argument('--vectors', type=Path, required=True)
    b.add_argument('--out', type=Path, required=True)
    b.add_argument('--stall', type=int, default=0)
    b.add_argument('--max-cycles', type=int, default=400000)
    b.add_argument('--mutant', choices=['none', 'q_order', 'context', 'context_length', 'group'], default='none')
    c = sub.add_parser('counterproof')
    c.add_argument('--ctx', type=int, default=8192)
    c.add_argument('--seed', type=int, default=1)
    c.add_argument('--kind', choices=R.KINDS, default='normal')
    c.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.command == 'counterproof':
        return 0 if counterproof(args.ctx, args.seed, args.kind, args.out) else 1
    if args.command == 'vectors':
        if not 1 <= args.ctx <= 8192:
            ap.error('context must be in 1..8192')
        vectors(args.ctx, args.seed, args.kind, args.out, args.groups)
        return 0
    return 0 if run(args.binary, args.vectors, args.out, args.stall, args.mutant, args.max_cycles) else 1


if __name__ == '__main__':
    raise SystemExit(main())
