#!/usr/bin/env python3
"""All model-specified TP2/32-SM QKV partitions; reuse one pinned SM build.

This is a full-shape QKV partition/component gate, not a connected RTL die or
token. HBM shares and release are behavioral; full QKV gather and rstd are
host operations. Successful windows can be reused after input-byte checks.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess

import numpy as np

import w19_qwen_hbm_checkpoint as C
from w19_qwen_hbm_preflight_w12 import ROOT, sha, sm_snapshot


def parse_output(path):
    res,meta={},{}
    for line in Path(path).read_text().splitlines():
        if line.startswith('#'):
            toks=line[1:].split()
            if 'TIMEOUT' in line:
                meta['timeout']=True
            for i in range(0,len(toks)-1,2):
                meta[toks[i]]=int(toks[i+1]) if toks[i+1].lstrip('-').isdigit() else toks[i+1]
        else:
            r,h=line.split()
            if int(r) in res:
                raise ValueError('duplicate row result')
            res[int(r)]=h
    return res,meta


def gather(parts):
    """Every one of 32 exact row partitions must be present on each TP die."""
    if set(parts)!={(die,sm) for die in (0,1) for sm in range(32)}:
        raise ValueError('full QKV requires two dies x 32 SMs, exactly once')
    result={}
    for die in (0,1):
        for sm in range(32):
            if np.asarray(parts[die,sm]).shape!=(96,):
                raise ValueError('QKV SM result shape changed')
        result[die]=np.concatenate([parts[die,sm] for sm in range(32)])
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--receipt',type=Path,required=True)
    ap.add_argument('--bundle',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--reuse-dir',type=Path,nargs='*',default=[])
    ap.add_argument('--jobs',type=int,default=24)
    ap.add_argument('--timeout',type=int,default=3600)
    args=ap.parse_args()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():
        raise SystemExit('Run in a clean committed helper worktree')
    receipt=json.loads(args.receipt.read_text())
    model_path=Path(receipt['preflight'])
    if sha(model_path)!=receipt['preflight_sha256']:
        raise ValueError('committed preflight drift')
    model=json.loads(model_path.read_text())
    if (model['design']['sm_count'],model['tp'])!=(32,2):
        raise ValueError('recompose for changed replica count')
    if sm_snapshot(model['sm_snapshot']['commit'])!=model['sm_snapshot']:
        raise ValueError('SM source/equivalence drift')
    for path,digest in model['source_sha256'].items():
        if sha(ROOT/path)!=digest:
            raise ValueError('preflight source drift: '+path)
    exe=Path(receipt['executable'])
    if sha(exe)!=receipt['executable_sha256'] or receipt['testbench_params']['NC']!=1:
        raise ValueError('expected pinned AR executable')
    manifest=json.loads((args.bundle/'manifest.json').read_text())
    if len(manifest['cases'])!=64 or {(c['die'],c['sm']) for c in manifest['cases']}!={(d,s) for d in (0,1) for s in range(32)}:
        raise ValueError('producer must supply all 64 model partitions')
    for path,digest in manifest['source_sha256'].items():
        if sha(ROOT/path)!=digest:
            raise ValueError('producer source drift: '+path)
    for case in manifest['cases']:
        if sha(args.bundle/case['file'])!=case['sha256']:
            raise ValueError('operand drift')
    args.work.mkdir(parents=True,exist_ok=False)
    old={}
    for root in args.reuse_dir:
        for p in [root/'verdict.json',*root.glob('*/verdict.json')]:
            if p.is_file():
                v=json.loads(p.read_text())
                if v.get('exact'):
                    old[v['file']]=p.parent
    def one(case):
        d=args.work/Path(case['file']).stem
        d.mkdir()
        try:
            with np.load(args.bundle/case['file'],allow_pickle=False) as data:
                nlines=C.pack(d,data['codes'],data['scale'],data['x'],1)
                reused=old.get(case['file'])
                if reused:
                    for name in ('lines.hex','x.hex','scale.hex','cfg.hex'):
                        if sha(d/name)!=sha(reused/name):
                            raise ValueError('cached case input drift')
                    (d/'out.txt').write_bytes((reused/'out.txt').read_bytes())
                else:
                    with (d/'sim.log').open('x') as log:
                        subprocess.run(['nice','-n','10','vvp','-n',str(exe),f'+DIR={d}','+GAP=0'],
                                       cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=args.timeout)
                res,meta=parse_output(d/'out.txt')
                mism,exact=C.verify(res,meta,data['expected'],1,nlines)
                post=sum(int(int(C.G.bits(C.G.mul(C.G.from_bits(np.uint32(int(h,16))),C.G.from_bits(data['rstd']))))
                             !=int(data['post_norm_expected'][r])) for r,h in res.items() if r<len(data['expected']))
                result=dict(case,exact=exact and post==0,mismatches=mism,host_epilogue_mismatches=post,
                            rows=96,K=4096,split=256,cols=1,weight_lines=nlines,rtl=meta,
                            reused_from=str(reused) if reused else None,output_sha256=sha(d/'out.txt'))
        except Exception as ex:
            # Failed cases remain records and do not cancel other partitions.
            result=dict(case,exact=False,error_type=type(ex).__name__,error=str(ex),
                        log_sha256=sha(d/'sim.log') if (d/'sim.log').exists() else None)
        C.save_json(d/'verdict.json',result)
        return result
    with ThreadPoolExecutor(max_workers=max(1,min(32,args.jobs))) as pool:
        cases=list(pool.map(one,manifest['cases']))
    exact=all(c['exact'] for c in cases)
    stage_outputs={}
    if exact:
        parts={}
        for case in cases:
            res,_=parse_output(args.work/Path(case['file']).stem/'out.txt')
            parts[case['die'],case['sm']]=np.array([int(res[r],16) for r in range(96)],dtype=np.uint32)
        for die,bits in gather(parts).items():
            p=args.work/f'd{die}_qkv_fp32.hex'
            p.write_text(''.join(f'{int(x):08x}\n' for x in bits))
            stage_outputs[p.name]=sha(p)
    record=dict(schema='opentallas.w19-qwen-hbm-full-qkv-partitions.v1',status='pass' if exact else 'fail',
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256={p:sha(ROOT/p) for p in ('tools/w19_qwen_hbm_qkv_stage_w12.py','tools/w19_qwen_hbm_checkpoint.py')},
                compile_receipt=receipt,sm_snapshot=model['sm_snapshot'],operand_manifest=manifest,
                replica_count=dict(tp_dies=2,sm_per_die=32,partitions_tested=len(cases),
                                   physical_cols=16,tested_active_cols=1),
                cases=cases,stage_outputs=stage_outputs,
                model_feedback=dict(max_partition_cycles=max([c.get('rtl',{}).get('cycles_start_to_done',0) for c in cases]),
                                    connected_die_stage_cycles=None,full_token_cycles=None,adoption=False),
                claim_boundary='All 64 model QKV row partitions through real-checkpoint GPU SM bulk-copy/SRAM/MMA/row-scale RTL, with host full-QKV gather and norm scalar check. Independent behavioral HBM shares and bench release; no production shared HBM/L2/NoC/barrier, physical NC16, full RTL layer or token verdict.',
                remaining_full_token_exit=model['remaining_full_token_exit'])
    C.save_json(args.out,record)
    if not exact:
        raise SystemExit(1)


if __name__=='__main__':
    main()
