#!/usr/bin/env python3
"""Qualified W13 source composition for the Qwen checkpoint SM gate.

Only the existing bulk-copy/SRAM/MMA/row-scale path is connected RTL.
Embedding, norm, rstd epilogue and release remain host/bench. No full token.
Pinned originals are unchanged; failed records are never overwritten.
"""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
from w19_qwen_hbm_checkpoint import ROOT, sha, sm_snapshot, save_json, pack, verify, G, S, prepare

def run(args):
    if args.out.exists() or args.work.exists():
        raise ValueError('Refusing to overwrite an existing result or work directory')
    host_paths = ['tools/w19_qwen_hbm_checkpoint_w13.py', 'tools/w19_qwen_hbm_checkpoint.py',
                  'tools/w19_qwen_hbm_preflight_w12.py', 'tools/rtl_gpu_sm_exact.py',
                  'tools/hdc_golden.py', 'tools/qwen3_deployment_quality.py']
    host_pins = {p: sha(ROOT/p) for p in host_paths}
    model = json.loads(args.preflight.read_text())
    if not model.get('sm_snapshot'):
        raise ValueError('Qualified W13 snapshot and prefix equivalence proof required')
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
    if not manifest['cases']:
        raise ValueError('Empty operand bundle cannot establish exactness')
    if manifest['split'] != 256 or manifest['checkpoint_revision'] != json.loads((ROOT/'compiler/models/qwen3-8b/checkpoint_source.json').read_text())['revision']:
        raise ValueError('Operand arithmetic or checkpoint revision mismatch')
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
    stable = host_pins == {p:sha(ROOT/p) for p in host_paths}
    record = dict(schema='opentallas.w19-qwen-hbm-checkpoint-w13-rtl.v1',
                  status='pass' if stable and all(c['exact'] for c in cases) else 'fail',
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  preflight_sha256=sha(args.preflight), operand_manifest=manifest,
                  cases=cases, testbench_params=params,
                  sm_snapshot=snapshot,
                  source_sha256=host_pins, source_stable=stable,
                  compiled_source_sha256=snapshot['source_sha256'],
                  compiled_source_commit=snapshot['commit'],
                  source_composition='Current pinned host producer/packing and immutable qualified W13 SM RTL; current main SMQ_SRC is not executed',
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
