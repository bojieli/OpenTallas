#!/usr/bin/env python3
"""Real token-0 embedding -> QKV operands -> existing GPU SM HBM/SRAM RTL.

prepare emits bounded complete-K SM windows; run compiles the existing SM
bench once and reuses it. This is a producer/component gate, never a token
verdict. Norm and post-QKV scalar are host golden operations. No RTL changes.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open

import hdc_golden as G
import qwen3_deployment_quality as Q
import rtl_gpu_sm_exact as S
from hdc_qwen_layer0_rom_w12 import pinned_snapshot
from hdc_qwen_int8_image_w12 import quantize_full_rows_then_partition
from w19_qwen_hbm_preflight_w12 import ROOT, sha, sm_snapshot


def save_json(path, record):
    with Path(path).open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')


def row_segments(die, sm):
    """Contiguous equal QKV ownership, including windows crossing projections."""
    if die not in (0, 1) or not 0 <= sm < 32:
        raise ValueError('TP die or SM index out of range')
    a, b = sm * 96, (sm + 1) * 96
    result = []
    for kind, lo, hi, n in [('q', 0, 2048, 2048), ('k', 2048, 2560, 512),
                            ('v', 2560, 3072, 512)]:
        l, h = max(a, lo), min(b, hi)
        if l < h:
            result.append((kind, die*n+l-lo, die*n+h-lo))
    return result


def prepare(args):
    torch.set_num_threads(1)
    if G.SU_WIDTH == 1:
        raise ValueError('Qwen R-ARITH chunk8 golden required')
    lock = pinned_snapshot(args.snapshot)
    config = json.loads((args.snapshot/'config.json').read_text())
    index = json.loads((args.snapshot/'model.safetensors.index.json').read_text())['weight_map']
    def tensor(name, lo=None, hi=None):
        with safe_open(str(args.snapshot/index[name]), framework='pt', device='cpu') as sf:
            return sf.get_tensor(name) if lo is None else sf.get_slice(name)[lo:hi]
    args.bundle.mkdir(parents=True, exist_ok=False)
    embedding = tensor('model.embed_tokens.weight', args.token, args.token+1)
    codes, scales, _ = Q.quantize_w8(embedding)
    x = G.mul(codes[0].numpy().astype(np.float32), scales.float().numpy()[0, 0])
    norm = tensor('model.layers.0.input_layernorm.weight')
    rstd = G.rstd(x, config['rms_norm_eps'])
    # Independent deployed torch contract check for the producer's reduction.
    ref_rstd = Q.rstd_g(torch.from_numpy(x)[None], config['rms_norm_eps']).numpy()[0]
    if int(G.bits(rstd)) != int(G.bits(ref_rstd)):
        raise ValueError('embedding norm producer disagrees with deployed contract')
    cases = []
    for die in (0, 1):
        for sm in args.sm:
            qparts, sparts, sources = [], [], []
            for kind, lo, hi in row_segments(die, sm):
                key = f'model.layers.0.self_attn.{kind}_proj.weight'
                w = tensor(key, lo, hi)
                q, sc = quantize_full_rows_then_partition(w, die=0, axis='columns', tp=1, norm=norm)
                qparts.append(q.numpy())
                sparts.append(sc.float().numpy().reshape(-1))
                sources.append(dict(tensor=key, rows=[lo, hi],
                                    bf16_sha256=__import__('hashlib').sha256(w.view(torch.int16).numpy().tobytes()).hexdigest()))
            q, scale = np.concatenate(qparts), np.concatenate(sparts)
            raw = G.matvec(q.astype(np.float32), x, 256)
            y = G.mul(raw, scale)
            # Same full-shape golden split as TP2 QKV, not recomputed for 96 rows.
            ref = Q.int8_mv_t(torch.from_numpy(x)[None], torch.from_numpy(q.T.copy()),
                              torch.from_numpy(scale)[None], 256).numpy()[0]
            if not np.array_equal(G.bits(y), G.bits(ref)):
                raise ValueError('QKV golden disagrees with deployed W8 arithmetic')
            path = args.bundle/f'd{die}_sm{sm}.npz'
            np.savez(path, codes=q, scale=scale, x=x, expected=G.bits(y),
                     post_norm_expected=G.bits(G.mul(y, rstd)), rstd=G.bits(rstd))
            cases.append(dict(file=path.name, sha256=sha(path), die=die, sm=sm,
                              qkv_rows=[sm*96, (sm+1)*96], sources=sources))
    save_json(args.bundle/'manifest.json', dict(
        schema='opentallas.w19-qwen-hbm-checkpoint-operands.v1',
        status='real_checkpoint_producer_exact', token=args.token, position=0,
        layer=0, checkpoint_revision=lock['revision'],
        checkpoint_lock_sha256=sha(ROOT/'compiler/models/qwen3-8b/checkpoint_source.json'),
        embedding_bf16_sha256=__import__('hashlib').sha256(embedding.view(torch.int16).numpy().tobytes()).hexdigest(),
        norm_bf16_sha256=__import__('hashlib').sha256(norm.view(torch.int16).numpy().tobytes()).hexdigest(),
        rstd_bits=f'{int(G.bits(rstd)):08x}', split=256, cases=cases,
        arithmetic='Existing W8 folded-weight TP2 contract, input BF16, FP32 tree then BF16 row scale then separate rstd multiply',
        source_sha256={p: sha(ROOT/p) for p in ('tools/w19_qwen_hbm_checkpoint.py',
            'tools/hdc_golden.py', 'tools/qwen3_deployment_quality.py', 'tools/hdc_qwen_int8_image_w12.py')},
        claim_boundary='Golden producer operands; no RTL norm, embedding, or complete token.'))


def pack(directory, q, scale, x, cols):
    rows, k = q.shape
    if (rows, k) != (96, 4096):
        raise ValueError('expected complete model-composed QKV SM window')
    c, gn, depth, lanes = 16, 2, 96, 128
    lines = []
    for r, g, t in S.issue_order(rows, gn, c, False):
        indices = (g*lanes+np.arange(lanes))*c+t
        lines.append(S.hexw(q[r, indices], 1024, 8))
    xb = S.bf16_bits(x)
    xwords = []
    for a in range(depth):
        g, t = divmod(a, c)
        vals = xb[(g*lanes+np.arange(lanes))*c+t] if g < gn else np.zeros(lanes, dtype=np.uint32)
        xwords.append(S.hexw(np.tile(vals, cols), lanes*cols*16, 16))
    (directory/'lines.hex').write_text('\n'.join(lines)+'\n')
    (directory/'x.hex').write_text('\n'.join(xwords)+'\n')
    (directory/'scale.hex').write_text('\n'.join(f'{int(v):04x}' for v in S.bf16_bits(scale))+'\n')
    (directory/'cfg.hex').write_text('\n'.join(f'{v:08x}' for v in (rows,c,gn,1,len(lines),0,0,0))+'\n')
    return len(lines)


def verify(res, meta, expected, cols, nlines):
    mismatches = sum(1 for r in range(len(expected)) for col in range(cols)
                     if r not in res or (int(res[r],16) >> (32*col)) & 0xffffffff != int(expected[r]))
    exact = (mismatches == 0 and set(res) == set(range(len(expected)))
             and not meta.get('timeout') and meta.get('fault') == 0
             and meta.get('consumed') == nlines and meta.get('released') == 1)
    return mismatches, exact


def run(args):
    model = json.loads(args.preflight.read_text())
    if model['operation']['tested_cols'] != args.cols:
        raise ValueError('column count differs from committed preflight')
    for path, digest in model['source_sha256'].items():
        if sha(ROOT/path) != digest:
            raise ValueError(f'preflight source drift: {path}')
    manifest = json.loads((args.bundle/'manifest.json').read_text())
    for path, digest in manifest['source_sha256'].items():
        if sha(ROOT/path) != digest:
            raise ValueError(f'producer source drift: {path}')
    for case in manifest['cases']:
        if sha(args.bundle/case['file']) != case['sha256']:
            raise ValueError('operand bundle drift')
    args.work.mkdir(parents=True, exist_ok=False)
    build = args.work/'build'
    build.mkdir()
    sources = S.SMQ_SRC
    snapshot = model.get('sm_snapshot')
    if snapshot:
        if sm_snapshot(snapshot['commit']) != snapshot:
            raise ValueError('W13 snapshot/equivalence pins drifted')
        sources = []
        for path,digest in snapshot['source_sha256'].items():
            data = subprocess.check_output(['git','show',snapshot['commit']+':'+path],cwd=ROOT)
            dst = args.work/'sm_snapshot'/path
            dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(data)
            if sha(dst) != digest:
                raise ValueError('exported W13 snapshot drift')
            sources.append(str(dst))
    params = dict(SUB=4,LS=32,NC=args.cols,XDEPTH=96,RMAX=256,LEV=5,
                  NXM=max(1,args.cols),LAT=550,JIT=55)
    exe = S.compile_tb(sources,'tb_gpu_sm_q',params,build)
    cases = []
    for case in manifest['cases']:
        d = args.work/Path(case['file']).stem
        d.mkdir()
        with np.load(args.bundle/case['file'], allow_pickle=False) as data:
            nlines = pack(d, data['codes'], data['scale'], data['x'], args.cols)
            res, meta = S.run_sim(exe,d,0)
            mism, exact = verify(res,meta,data['expected'],args.cols,nlines)
            # Host epilogue only; preserves separate rounding after row scale.
            post_mism = 0
            for r, h in res.items():
                for col in range(args.cols):
                    y = G.from_bits(np.uint32((int(h,16) >> (32*col)) & 0xffffffff))
                    post_mism += int(int(G.bits(G.mul(y,G.from_bits(data['rstd'])))) != int(data['post_norm_expected'][r]))
            cases.append(dict(case, exact=exact and post_mism == 0,
                              mismatches=mism, host_epilogue_mismatches=post_mism,
                              rows=96,K=4096,split=256,cols=args.cols,weight_lines=nlines,
                              rtl=meta, output_sha256=sha(d/'out.txt')))
    record = dict(schema='opentallas.w19-qwen-hbm-checkpoint-rtl.v1',
                  status='pass' if all(c['exact'] for c in cases) else 'fail',
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  preflight_sha256=sha(args.preflight), operand_manifest=manifest,
                  cases=cases, testbench_params=params,
                  sm_snapshot=snapshot,
                  source_sha256={p:sha(ROOT/p) for p in S.SMQ_SRC+['tools/w19_qwen_hbm_checkpoint.py']},
                  timing='Behavioral loaded HBM latency 550+0..55 cycles; bench clock units are cycles, not SS frequency evidence',
                  model_feedback=dict(measured_component_cycles=[c['rtl'] for c in cases],
                                      full_token_cycles=None, adoption=False),
                  remaining_full_token_exit=model['remaining_full_token_exit'],
                  claim_boundary='Real checkpoint embedding producer, complete-K QKV windows through existing GPU SM bulk-copy/SRAM/MMA/row-scale RTL. AR NC1 specialization if cols=1; physical NC16 validation pending. Embedding, norm, rstd epilogue and barrier release are host/bench, not connected RTL. No full layer/token or performance/signoff claim.')
    save_json(args.out,record)
    if record['status'] != 'pass':
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command',required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--token',type=int,default=0)
    p.add_argument('--sm',type=int,nargs='+',default=[21,26])
    p = sub.add_parser('run')
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--preflight',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--cols',type=int,choices=[1,16],default=1)
    args = ap.parse_args()
    (prepare if args.command == 'prepare' else run)(args)


if __name__ == '__main__':
    main()
