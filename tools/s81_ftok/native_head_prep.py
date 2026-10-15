#!/usr/bin/env python3
"""Run HC_PRE + final RMSNorm in the actual S81 HC hierarchy.

Inputs are hardware handoff files: --hout (641 hop flits), --pre (four
binary32 words), --gain (5120 binary32 ROM words), and --eps (hex binary32).
Golden computes only expected results. The DUT reads h/pre/gain, never golden xf.
Output xf.mem contains 5120 scalar-order BF16 words produced by the DUT.
This component gate models its VM pin boundary; it is NOT full-chip qualification.
The command slots are compile-time reservations, with no credits/ready scheduling.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/s81_suhc'), str(ROOT/'tools/s81_ftok')]
os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import hc_gate as HG
import chain_glue as CG
TB = 'rtl/dsrom_sys/s81_native_head_connect/test/tb_s81_head_prep.sv'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_f32(p, count):
    words = [int(x, 16) for x in Path(p).read_text().split()]
    if len(words) != count or any(x > 0xffffffff for x in words):
        raise ValueError(f'{p}: expected {count} binary32 words')
    return np.array(words, np.uint32).view(np.float32)


def prep(a):
    w = Path(a.work); w.mkdir(parents=True, exist_ok=True)
    h = CG.rows_to_h(a.hout)
    pre = read_f32(a.pre, 4); gain = read_f32(a.gain, HG.D)
    eps = np.array([int(a.eps,16)], np.uint32).view(np.float32)[0]
    if not np.isfinite(pre).all() or not np.isfinite(gain).all() or not np.isfinite(eps) or eps <= 0:
        raise ValueError('non-finite operand or invalid epsilon')
    r = HG.Run(256)
    for q, row in enumerate(r.h_rows(h)):
        r.vm[HG.H_BASE+q] = row
    for q in range(HG.GROWS):
        r.vm[HG.G_BASE+q] = HG.pack(HG.u32(gain[16*q:16*q+16]),32)
    r.vm[HG.C_BASE] = 0             # NORM never consumes comb or post.
    r.vm[HG.C_BASE+1] = HG.pack(list(HG.u32(pre))+[0]*4+[int(HG.u32([eps])[0])],32)
    r.job(HG.K_GAIN,0,HG.G_BASE)
    r.job(HG.K_HLOAD,0,HG.H_BASE)
    r.job(HG.K_COEF,0,HG.C_BASE)
    r.job(HG.K_NORM,0,HG.O_BASE,quant=0,yout=1)
    expected = HG.g_norm(h,pre,gain,eps)
    r.norm_rows(HG.O_BASE,expected,quant=0,yout=1)
    # Conservative reserved component slots. These are not an accepted token price.
    slots = [64,512,1536,1792]
    meta = dict(kind='s81_hardware_head_prep_component', full_native_token=False,
                modeled_boundary='VM pins only; integrate real VM and native producer before token qualification',
                schedule_kind='fixed compiler slots; completion never gates issue',
                issue_cycles=slots, performance_qualified=False,
                inputs={name:dict(path=str(Path(p).resolve()),sha256=sha(p)) for name,p in
                        [('hout',a.hout),('pre',a.pre),('gain',a.gain)]}, eps=a.eps)
    r.write(w,meta)
    (w/'issue.mem').write_text(''.join(f'{x:08x}\n' for x in slots))
    # Readmemh requires at least one word even when there is no collective input.
    (w/'y.mem').write_text('0\n')
    np.save(w/'expected.npy',expected)
    print('S81_HEAD_PREP prepared: actual operands -> HC_PRE+RMSNorm, 4 static commands')


def run(a):
    w=Path(a.work).resolve(); meta=json.loads((w/'meta.json').read_text())
    if meta['schedule_kind'] != 'fixed compiler slots; completion never gates issue':
        raise ValueError('unsupported schedule')
    obj=(Path(a.build_work).resolve() if a.build_work else w)/f'obj_m{a.mut}'; obj.mkdir(exist_ok=True)
    exe=obj/'Vtb_s81_head_prep'
    sources=[ROOT/s for s in HG.FP['rtl']+HG.RTL+[TB,'tools/s81_ftok/head_prep.vlt']]
    # Immutable source manifest is checked before reusing a binary.
    manifest={str(p.relative_to(ROOT)):sha(p) for p in sources}
    manifest['mut']=a.mut
    mf=obj/'sources.json'
    if exe.exists() and (not mf.exists() or json.loads(mf.read_text()) != manifest):
        raise ValueError('source changed: use a fresh work/build directory')
    if not exe.exists():
        cmd=[HG.VERILATOR,'--binary','--timing','--hierarchical','--hierarchical-threads',str(a.hier_workers),'-O2','-Wno-fatal','-Wno-WIDTH',
             '--top-module','tb_s81_head_prep','-Mdir',str(obj),'-j','16',
             '--unroll-count','4','-fno-dfg','-GNG=256',f'-GMUT={a.mut}',
             '-GHIER=1','-GHALF=1','-GCSPLIT=1','-GTAIL_SPLIT=2',
             '-GCNL_PIN=1','-GCHAIN_STEP=6','-GLANE_SPECIALIZE=1',
             *map(str,sources),'-CFLAGS','-O1']
        p=subprocess.run(cmd,capture_output=True,text=True)
        (obj/'build.log').write_text(' '.join(cmd)+'\n'+p.stdout+p.stderr)
        if p.returncode: raise RuntimeError(f'build failed: {obj}/build.log')
        mf.write_text(json.dumps(manifest,indent=2)+'\n')
    p=subprocess.run([str(exe)],cwd=w,capture_output=True,text=True)
    (w/f'run_m{a.mut}.log').write_text(p.stdout+p.stderr)
    good=p.returncode==0 and 'HCG PASS' in p.stdout
    if a.mut:
        m=HG.HCG.search(p.stdout)
        if good or 'HCG FAIL' not in p.stdout or not m:
            raise RuntimeError('mutant did not produce an observed FAIL')
        jobs,done,errs,rows,fault,code,cyc,bad_tag=map(int,m.groups())
        if jobs!=4 or done!=4 or errs==0 or fault or bad_tag:
            raise RuntimeError('mutant failed for an unexpected reason')
        print('S81_HEAD_PREP mutant detected'); return
    if not good: raise RuntimeError('head prep failed: '+p.stdout[-2000:])
    got=[int(x,16) for x in (w/'got.mem').read_text().split()]
    words=np.array([(row>>(16*l))&65535 for row in got for l in range(32)],np.uint16)
    if len(words)!=HG.D: raise ValueError('output dimension')
    xf=(words.astype(np.uint32)<<16).view(np.float32)
    if not CG.same(xf,np.load(w/'expected.npy')): raise ValueError('RTL output mismatch')
    (w/'xf.mem').write_text(''.join(f'{x:04x}\n' for x in words))
    np.save(w/'xf.npy',xf)
    provenance=dict(meta, rtl_sources=manifest, actual_output_sha256=sha(w/'xf.mem'),
                    actual_output_producer='dsfd_sp_hc HIER=1 HALF=1 CSPLIT=1 TAIL_SPLIT=2 K_NORM YOUT',
                    arithmetic='RTL only; no DPI',gate='PASS')
    (w/'xf.provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('S81_HEAD_PREP PASS RTL HC_PRE+RMSNorm -> xf.mem (5120 BF16, VM boundary component only)')


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='step',required=True)
    q=sub.add_parser('prep'); q.add_argument('--work',required=True)
    for name in ('hout','pre','gain'): q.add_argument('--'+name,required=True)
    q.add_argument('--eps',default='358637bd')
    q=sub.add_parser('run');q.add_argument('--work',required=True);q.add_argument('--hier-workers',type=int,choices=range(1,5),default=1,help='bound concurrent native module compilers by memory');q.add_argument('--build-work',help='reuse source-checked build directory across hardware handoffs');q.add_argument('--mut',type=int,choices=[0,3],default=0)
    a=p.parse_args(); return dict(prep=prep,run=run)[a.step](a)
if __name__=='__main__': main()
