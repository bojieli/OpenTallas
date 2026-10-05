#!/usr/bin/env python3
"""Committed full-QKV RTL outputs -> full-head norm/RoPE/FP8 KV oracle fixtures.

These are host-produced numerical fixtures for the next GPU vector/KV gate.
They never constitute RTL vector, attention, or token execution evidence.
"""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
import torch
from safetensors import safe_open

import hdc_golden as G
import qwen3_deployment_quality as Q
from hdc_qwen_layer0_rom import pinned_snapshot
from w19_qwen_hbm_checkpoint import save_json
from w19_qwen_hbm_preflight import ROOT, sha


def split_projections(parts):
    if set(parts) != {0, 1} or any(np.asarray(p).shape != (3072,) for p in parts.values()):
        raise ValueError('two complete3072-row TP QKV buffers required')
    return tuple(np.concatenate([parts[d][lo:hi] for d in (0, 1)])
                 for lo, hi in ((0, 2048), (2048, 2560), (2560, 3072)))


def fp8_codes(values):
    return torch.from_numpy(np.asarray(values).copy()).to(torch.float8_e4m3fn).view(torch.uint8).numpy()


def compose(raw_bits, rstd_bits, qn, kn, eps, position, theta):
    if np.asarray(raw_bits).shape != (3072,) or qn.shape != (128,) or kn.shape != (128,):
        raise ValueError('full-shape TP QKV and128-element norm weights required')
    if G.CHUNK != 8 or G.SU_WIDTH == 1:
        raise ValueError('chunk8 vector golden required')
    post = G.mul(G.from_bits(raw_bits), G.from_bits(np.uint32(rstd_bits)))
    q, k, v = post[:2048].reshape(16, 128), post[2048:2560].reshape(4, 128), post[2560:].reshape(4, 128)
    qr, kr = np.array([G.rstd(x, eps) for x in q]), np.array([G.rstd(x, eps) for x in k])
    qnorm, knorm = G.mul(G.mul(q, qr[:, None]), qn), G.mul(G.mul(k, kr[:, None]), kn)
    cos, sin, half = G.rope_tables(position, 128, theta)
    qrope = np.array([G.rope(x, cos, sin, half) for x in qnorm])
    krope = np.array([G.rope(x, cos, sin, half) for x in knorm])
    kfp, vfp = G.to_fp8(krope), G.to_fp8(v)
    result = dict(raw_qkv_bits=raw_bits, rstd_bits=np.uint32(rstd_bits), qn_bits=G.bits(qn), kn_bits=G.bits(kn),
                  post_norm_bits=G.bits(post), q_rstd_bits=G.bits(qr), k_rstd_bits=G.bits(kr),
                  q_norm_bits=G.bits(qnorm), k_norm_bits=G.bits(knorm),
                  q_rope_bits=G.bits(qrope), k_rope_bits=G.bits(krope),
                  q_bf16_bits=(G.bits(G.to_bf16(qrope)) >> 16).astype(np.uint16),
                  k_fp8_bits=fp8_codes(kfp), v_fp8_bits=fp8_codes(vfp),
                  k_fp8_fp32_bits=G.bits(kfp), v_fp8_fp32_bits=G.bits(vfp),
                  cos_bits=G.bits(cos), sin_bits=G.bits(sin))
    # Independent deployed torch arithmetic, including its hardware FP8 cast.
    t = Q.mul(torch.from_numpy(G.from_bits(raw_bits).copy()), float(G.from_bits(np.uint32(rstd_bits))))
    tq, tk, tv = t[:2048].reshape(16, 128), t[2048:2560].reshape(4, 128), t[2560:].reshape(4, 128)
    tqr, tkr = Q.rstd_g(tq, eps), Q.rstd_g(tk, eps)
    tqn, tkn = Q.rmsnorm_g(tq, torch.from_numpy(qn), eps), Q.rmsnorm_g(tk, torch.from_numpy(kn), eps)
    tc, ts = Q.rope_tables_g([position], 128, theta, 'cpu')
    tqp, tkp = Q.rope_g(tqn, tc, ts), Q.rope_g(tkn, tc, ts)
    tkf, tvf = Q.to_fp8(tkp), Q.to_fp8(tv)
    references = dict(post_norm_bits=t, q_rstd_bits=tqr, k_rstd_bits=tkr,
                      q_norm_bits=tqn, k_norm_bits=tkn, q_rope_bits=tqp, k_rope_bits=tkp,
                      k_fp8_fp32_bits=tkf, v_fp8_fp32_bits=tvf, cos_bits=tc[0], sin_bits=ts[0])
    for name, ref in references.items():
        if not np.array_equal(result[name], G.bits(ref.numpy())):
            raise ValueError('deployed arithmetic boundary mismatch: '+name)
    if not np.array_equal(result['q_bf16_bits'], (G.bits(Q.to_bf16(tqp).numpy()) >> 16).astype(np.uint16)):
        raise ValueError('BF16 Q mismatch')
    for name, ref in [('k_fp8_bits', tkf), ('v_fp8_bits', tvf)]:
        if not np.array_equal(result[name], ref.to(torch.float8_e4m3fn).view(torch.uint8).numpy()):
            raise ValueError('FP8 byte mismatch: '+name)
    floats = (post, qr, kr, qnorm, knorm, qrope, krope, kfp, vfp)
    if any(not np.isfinite(x).all() for x in floats):
        raise ValueError('nonfinite vector/KV fixture')
    return result, dict(nonfinite=0, fp8_saturation_inputs=int(np.count_nonzero(np.abs(krope)>448)
                       + np.count_nonzero(np.abs(v)>448)), deployed_boundary_mismatches=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', type=Path, required=True)
    ap.add_argument('--bundle', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise SystemExit('run in a clean committed helper worktree')
    preflight_path = ROOT/'results/uarch/w19_qwen_hbm_vector_fixture_preflight.json'
    preflight = json.loads(preflight_path.read_text())
    for p, digest in preflight['source_sha256'].items():
        if sha(ROOT/p) != digest:
            raise ValueError('preflight source drift: '+p)
    stage = json.loads((ROOT/'results/rtl/w19_qwen_hbm_full_qkv_partitions.json').read_text())
    if stage['status'] != 'pass' or {(c['die'],c['sm']) for c in stage['cases']} != {(d,s) for d in (0,1) for s in range(32)}:
        raise ValueError('all64 exact RTL QKV partitions required')
    lock = pinned_snapshot(args.snapshot)
    if lock['revision'] != stage['operand_manifest']['checkpoint_revision']:
        raise ValueError('checkpoint revision mismatch')
    cfg = json.loads((args.snapshot/'config.json').read_text())
    index = json.loads((args.snapshot/'model.safetensors.index.json').read_text())['weight_map']
    weights, tensors = [], {}
    for name in ('q_norm', 'k_norm'):
        key = f'model.layers.0.self_attn.{name}.weight'
        with safe_open(str(args.snapshot/index[key]), framework='pt', device='cpu') as f:
            w = f.get_tensor(key)
        tensors[key] = dict(shape=list(w.shape), bf16_sha256=__import__('hashlib').sha256(w.view(torch.int16).numpy().tobytes()).hexdigest())
        weights.append(w.float().numpy())
    args.bundle.mkdir(exist_ok=False)
    torch.set_num_threads(1)
    source_commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    cases, parts = [], {}
    try:
        for die in (0,1):
            p = ROOT/f'results/rtl/w19_qwen_hbm_full_qkv_stage/d{die}_qkv_fp32.hex'
            if sha(p) != stage['stage_outputs'][p.name]:
                raise ValueError('gathered QKV drift')
            bits = np.array([int(x,16) for x in p.read_text().split()],dtype=np.uint32)
            data, checks = compose(bits,int(stage['operand_manifest']['rstd_bits'],16),*weights,
                                   cfg['rms_norm_eps'],0,cfg['rope_theta'])
            parts[die] = data['post_norm_bits']
            dst = args.bundle/f'd{die}_vector_kv.npz'
            np.savez(dst,**data)
            cases.append(dict(die=die,file=dst.name,sha256=sha(dst),checks=checks,
                              q_heads=16,kv_heads=4,head_dim=128))
        q,k,v = split_projections(parts)
        global_path=args.bundle/'global_qkv_post_norm.hex'
        global_path.write_text(''.join(f'{int(x):08x}\n' for x in np.concatenate((q,k,v))))
    except Exception as ex:
        save_json(args.out,dict(status='fail',source_commit=source_commit,error_type=type(ex).__name__,error=str(ex),cases=cases))
        raise
    save_json(args.out,dict(schema='opentallas.w19-qwen-hbm-vector-kv-fixtures.v1',status='producer_exact',
                           source_commit=source_commit,preflight_sha256=sha(preflight_path),
                           source_sha256={p:sha(ROOT/p) for p in ('tools/w19_qwen_hbm_vector_fixture.py','tools/hdc_golden.py','tools/qwen3_deployment_quality.py')},
                           checkpoint_revision=lock['revision'],tensors=tensors,cases=cases,
                           layer=0,token=0,position=0,global_qkv_post_norm_sha256=sha(global_path),
                           full_token_cycles=None,adoption=False,
                           claim_boundary='Committed64-partition real-checkpoint RTL QKV outputs feed full-head host norm/RoPE/FP8 KV fixtures, bit-exact against independent deployed arithmetic. No RTL vector/KV/attention or full-token verdict.'))


if __name__ == '__main__':
    main()
