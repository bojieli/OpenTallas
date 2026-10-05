#!/usr/bin/env python3
"""A kmerge-format beat through the pooled indexer read bridge and score writer."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rtl_hdc_v41x_idx_campaign as C

RTL = [ROOT / f'rtl/hdc/v41x/{n}.sv' for n in (
    'ot_hdc_v41x_idx_pool_batch', 'ot_hdc_v41x_idx_pool_finish', 'ot_hdc_v41x_idx_pcol',
    'ot_hdc_v41x_idx_hsum', 'ot_hdc_v41x_idx_arith', 'ot_hdc_v41x_wgt_tile',
    'ot_hdc_v41x_wgt_mac', 'ot_hdc_v41x_wgt_bdot', 'ot_hdc_v41x_wgt_red')] + [
    ROOT / 'rtl/hdc/ot_hdc_fastfp.sv', ROOT / 'rtl/hdc/ot_hdc_delay.sv']
TB = ROOT / 'rtl/test/tb_hdc_v41x_idx_pool_batch.sv'
HARNESS = ROOT / 'rtl/test/hdc_v41_tb_harness.cpp'
OUT = ROOT / 'results/rtl/hdc_v41x_idx_pool_batch_campaign.json'
P = re.compile(r'V41XBATCH keys=(\d+) checked=(\d+) errors=(\d+) faults=(\d+) cycles=(\d+) protocol=(\d+)')


def _line(items):
    return C.hexline(items)


def vectors(tok, work: Path, m: int):
    assert len(tok['keep']) <= 16 or len(tok['keep']) == 32
    ih, n = 32, len(tok['keep'])
    qc = np.pad(tok['qc'], ((0, 0), (0, 128-tok['qc'].shape[1])))
    qu = np.pad(tok['qu'], ((0, 0), (0, 4-tok['qu'].shape[1])))
    kc = np.pad(tok['kc'], ((0, 0), (0, 128-tok['kc'].shape[1])))
    ku = np.pad(tok['ku'], ((0, 0), (0, 4-tok['ku'].shape[1])))
    xl, wl = [], []
    for g in range(ih//m):
        for b in range(4):
            for p in range(m):
                h = g*m+p
                codes = [C.E2M1_E4M3[c & 7] | (0x80 if c & 8 else 0) for c in qc[h, 32*b:32*b+32]]
                xl.append(_line([(x, 8) for x in codes]+[(int(qu[h,b]),8)]))
    for h in range(ih):
        wl.append(_line([(int(C.G.bits(tok['w'][h]))>>16,16)]+[(int(x),8) for x in qu[h]]))
    km=['0']*64; mm=['0']*64
    base=8*(n//32)
    for q in range(4):
        qlen= n-3*base if q==3 else base
        for lane in range(qlen):
            idx=q*base+lane
            slot=q*16+lane
            km[slot]=_line([(int(x),4) for x in kc[idx]]+[(int(x),8) for x in ku[idx]])
            ref=int((ku[idx]>=253).any() or (qu>=253).any())
            mm[slot]=f'{(ref<<1)|int(tok["keep"][idx]):x}'
    em=[_line([(int(tok['exp'][i]),16),(int(tok['fault'][i]),1)]) for i in range(n)]
    em += ['0']*(64-n)
    for name,rows in [('bk.mem',km),('bx.mem',xl),('bw.mem',wl),('bm.mem',mm),('be.mem',em)]:
        (work/name).write_text('\n'.join(rows)+'\n')


def main():
    work=Path('/tmp/claude-1000/idx_pool_batch_gate');work.mkdir(parents=True,exist_ok=True)
    stamp=hashlib.sha256(b''.join(p.read_bytes() for p in RTL+[TB,HARNESS])).hexdigest()
    rng=np.random.default_rng(20260927)
    toks=[C.finish(C.rand_token(rng,32,4,n,cls)) for cls,n in (
        ('typical',32),('wide',15),('masked',16),('fault',13))]
    # A real reduced-vehicle token is padded from one 32-dim block to four;
    # zero extra blocks preserve the golden's exact FP32 accumulation.
    vehicle=C.vehicle_tokens(8)
    toks.extend((next(t for t in vehicle if t['cls']==layer and len(t['keep'])==n)
                 for layer,n in (('vehicle.L2',1),('vehicle.L20',6))))
    rows=[]
    for mp in (1,2):
        obj=work/f'obj_m{mp}';exe=obj/'Vtb_hdc_v41x_idx_pool_batch'
        if not exe.exists() or not (obj/'stamp').exists() or (obj/'stamp').read_text()!=stamp:
            subprocess.run(['verilator','--cc','--exe','--build','-O3','--x-assign','fast','--x-initial','fast',
                '-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','-Wno-DECLFILENAME','-Wno-WIDTHCONCAT',
                '--top-module','tb_hdc_v41x_idx_pool_batch',f'-GM={mp}',
                '-CFLAGS','-DVTOP=Vtb_hdc_v41x_idx_pool_batch -O1',
                '-j','8','--Mdir',str(obj),str(TB)]+[str(p) for p in RTL]+[str(HARNESS)],
                check=True,capture_output=True,text=True,timeout=1800)
            (obj/'stamp').write_text(stamp)
        for i,t in enumerate(toks):
            d=work/f'm{mp}_case{i}';d.mkdir(exist_ok=True)
            vectors(t,d,mp)
            r=subprocess.run([str(exe),f'+NKEY={len(t["keep"])}'],cwd=d,capture_output=True,text=True,timeout=600)
            m=P.search(r.stdout)
            if not m: raise RuntimeError(r.stdout[-2000:]+r.stderr[-2000:])
            v=list(map(int,m.groups()))
            row=dict(name=t['cls'],mp=mp,keys=v[0],checked=v[1],errors=v[2],
                     faults=v[3],cycles=v[4],protocol_fault=v[5])
            assert row['keys']==row['checked'] and row['errors']==0 and row['protocol_fault']==0,row
            rows.append(row)
    rec=dict(schema='opentallas-hdc-v41x-idx-pool-batch-v1',status='pass',rows=rows,
        limitation='One G4/MP1 or MP2 tile back-pressures 64-key kmerge beats; query FP8 read words and head weights are supplied by a testbench memory. Core X_IDX adapter and full-rate replication remain.',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in RTL+[TB,HARNESS,Path(__file__).resolve()]})
    OUT.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps(rows,indent=1))


if __name__=='__main__':main()
