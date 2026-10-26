#!/usr/bin/env python3
"""Reconstruct an Engram layer's genuine attention-entry H from checkpoint inputs.

Sidecars are selected embedding codes/scales and the full TP4 wkv weights. Never
use an ops/ expected value as a producer. Fixture ops are assertion targets only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import hdc_golden_v41 as V


def _fixture(fixture, name):
    p = Path(fixture)
    spec = json.loads((p / 'files.json').read_text())[name]
    a = np.fromfile(p / name, dtype=spec['dtype']).reshape(spec['shape'])
    if spec.get('format') == 'BF16':
        return (a.reshape(-1).view(np.uint16).astype(np.uint32) << 16).view(np.float32).reshape(*spec['shape'][:-1], spec['shape'][-1] // 2)
    return a


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while b := f.read(8 << 20):
            h.update(b)
    return h.hexdigest()


def export_inputs(fixture, checkpoint, out):
    """Read only 24 selected Engram rows and this layer's full wkv projection."""
    from rtl_v41_fullshape_layer_campaign import Checkpoint
    p, out = Path(fixture), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    meta = json.loads((p / 'meta.json').read_text())
    config = json.loads((ROOT / 'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
    L = meta['layer_index']
    checkpoint = Path(checkpoint)
    ck = Checkpoint(checkpoint)
    old_tok = V.TOKENIZER
    V.TOKENIZER = checkpoint / 'tokenizer.json'
    try:
        tables = V.EngramTables(config, config['vocab_size'])
        ids = tables.hashes(meta['history'], tables.layer_ids.index(L))
    finally:
        V.TOKENIZER = old_tok
    arrays = {'ids': ids, 'rows': ck.rows(f'layers.{L}.engram.embed.weight', ids)}
    raw_sc, dt, shape = ck.raw(f'layers.{L}.engram.embed.scale')
    arrays['rows_scale'] = np.asarray(raw_sc).reshape(shape)[ids].copy()
    for short, tensor in [('wkv', 'wkv.weight'), ('wkv_scale', 'wkv.scale')]:
        raw, dt, shape = ck.raw(f'layers.{L}.engram.{tensor}')
        arrays[short] = np.asarray(raw).reshape(shape)
    files = {}
    for name, a in arrays.items():
        file = out / (name + '.bin')
        np.asarray(a).tofile(file)
        files[name] = dict(file=file.name, shape=list(a.shape), dtype=str(a.dtype), sha256=_sha(file))
    rec = dict(schema='opentallas.entry_engram_inputs.v1', layer=L, checkpoint=str(checkpoint),
               fixture_meta_sha256=_sha(p / 'meta.json'), source='checkpoint tensors and meta.history; no ops producers',
               history=meta['history'], dim=config['dim'], hc=config['hc_mult'], eps=config['norm_eps'], files=files)
    (out / 'inputs.json').write_text(json.dumps(rec, indent=1) + '\n')
    return rec


def entry_h(fixture, inputs, *, return_intermediates=False):
    """The Engram-updated BF16 H read by attention; all producers are genuine inputs."""
    p = Path(inputs)
    rec = json.loads((p / 'inputs.json').read_text())
    meta = json.loads((Path(fixture) / 'meta.json').read_text())
    if meta['layer_index'] != rec['layer'] or _sha(Path(fixture) / 'meta.json') != rec['fixture_meta_sha256']:
        raise ValueError('Engram sidecars do not match fixture')
    def arr(name):
        spec = rec['files'][name]
        return np.fromfile(p / spec['file'], dtype=spec['dtype']).reshape(spec['shape'])
    if V.ARITH != 'chunk8':
        raise ValueError('Engram entry requires chunk8 arithmetic')
    F = np.float32
    h = _fixture(fixture, 'io/h_in.bin').astype(F)
    rows = V.decode_engram_rows(arr('rows'), arr('rows_scale').astype(np.int32) - 127,
                                np.arange(len(arr('ids')))).reshape(-1)
    w = V._blocked(arr('wkv'), arr('wkv_scale').astype(np.int32) - 127, 'engram.wkv')
    kv = V.linear_q(w, rows)
    dim, hc = rec['dim'], rec['hc']
    key, value = kv[:hc * dim].reshape(hc, dim), kv[hc * dim:]
    wgt = V.mul(_fixture(fixture, 'weights/engram.q_weight.bin'), _fixture(fixture, 'weights/engram.k_weight.bin'))
    gates, out = [], []
    for j in range(hc):
        hj, kj = h[j], key[j]
        rh = V.rsqrt(V.add(V.div(V.reduce_sum_c(V.mul(hj, hj)), F(dim)), F(rec['eps'])))
        rk = V.rsqrt(V.add(V.div(V.reduce_sum_c(V.mul(kj, kj)), F(dim)), F(rec['eps'])))
        dot = V.mul(V.mul(V.reduce_sum_c(V.mul(V.mul(hj, wgt[j]), kj)), V.mul(rh, rk)), F(dim ** -0.5))
        mag = V.sqrt(np.maximum(np.abs(dot), F(1e-6)).astype(F))
        gate = V.sigmoid(np.where(dot < 0, V.neg(mag), mag).astype(F))
        gates.append(gate)
        out.append(V.add(hj, V.mul(gate, value)))
    hh = V.to_bf16(np.stack(out))
    return (hh, dict(rows=rows, kv=kv, gates=np.asarray(gates, F))) if return_intermediates else hh


def check(fixture, inputs, out):
    """Expected intermediates are used only after all arithmetic is recomputed."""
    hh, mid = entry_h(fixture, inputs, return_intermediates=True)
    pre = _fixture(fixture, 'io/pre_in.bin').astype(np.float32)
    hc_pre = V.to_bf16(V.seqsum([V.mul(pre[j], hh[j]) for j in range(len(hh))]))
    pairs = [('rows', mid['rows'], 'ops/eng.hbm_read.bin'), ('wkv', mid['kv'], 'ops/eng.wkv.bin'),
             ('gates', mid['gates'], 'ops/eng.gate.bin'), ('h', hh, 'ops/eng.add.bin'),
             ('attn_hc_pre', hc_pre, 'ops/attn.hc_pre.bin')]
    checks = {}
    for name, actual, expected in pairs:
        ref = _fixture(fixture, expected).astype(np.float32)
        checks[name] = dict(words=actual.size, mismatches=int(np.count_nonzero(actual.view(np.uint32) != ref.view(np.uint32))))
    rec = dict(schema='opentallas.entry_engram_check.v1', verdict='PASS' if all(v['mismatches'] == 0 for v in checks.values()) else 'FAIL',
               checks=checks, inputs=str(inputs), fixture=str(fixture), source='genuine checkpoint codes/scales/full wkv + fixture H/pre/q/k weights')
    Path(out).write_text(json.dumps(rec, indent=1) + '\n')
    return rec


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['export', 'check'])
    ap.add_argument('--fixture', required=True)
    ap.add_argument('--inputs', required=True)
    ap.add_argument('--checkpoint')
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.command == 'export':
        rec = export_inputs(a.fixture, a.checkpoint, a.inputs)
        print(json.dumps({k: v for k, v in rec.items() if k != 'files'}))
    else:
        rec = check(a.fixture, a.inputs, a.out)
        print(json.dumps(rec))
        raise SystemExit(rec['verdict'] != 'PASS')
