#!/usr/bin/env python3
"""Compare legal whole-K packed and spread phases on the same minimum field RTL.
Uses the two-pair/one-region generic W17/W10 numerical vehicle, not physical signoff.
"""
import argparse,json,re,subprocess
from pathlib import Path
import numpy as np
import dsrom_mtp_p2 as P
import dsrom_1m_field as FD
import v41_die_images_w17w10 as I
import rtl_v41_rom_array as A
import hdc_golden_v41 as G


def run(snapshot,work,exe,kind):
    G.set_arith('chunk8');ck=A.Ckpt(snapshot);mats=[]
    k=2304 if kind=='w2_packed' else 5120
    for i,op in enumerate(['w2'] if kind=='w2_packed' else ['w1','w3']):
        m=A.Mat(ck,f'mtp.0.ffn.experts.0.{op}','fp4',1280 if op=='w2' else 576,k)
        m=FD.take(m,[0,1,256,257,512,513] if op=='w2' else [0,1])
        m.s81_segments=[[0,k]]
        m.s81_place=[(j,0,i if kind=='gu_spread' else 0) for j in range(m.rows//2)]
        mats.append(m)
    fld=I.Field(2,1,0,pp=True,fast=True);meta=I.add_phase(fld,mats,(False,False),0)
    img=work/kind/'img';img.mkdir(parents=True,exist_ok=True);I.write_field(fld,img,2)
    x=FD.rand_x('p2-worst-gu' if k==5120 else 'p2-worst-w2',k,False)
    vm=np.zeros(1<<16,dtype=np.uint32);vm[:k]=x
    (img/'vm.hex').write_text(''.join(f'{int(v):08x}\n' for v in vm))
    ops=img.parent/'ops.txt';ops.write_text(f'0 0 0 {k} 32768 {meta["nrows"]}\n')
    p=subprocess.run([str(exe),str(img),str(ops)],capture_output=True,text=True)
    log=img.parent/'sim.log';log.write_text(p.stdout+p.stderr)
    writes={int(t[2]):int(t[3],16) for l in p.stdout.splitlines() if (t:=l.split()) and t[0]=='W'}
    expected={32768+i:b<<16 for i,(f,b) in I.golden_phase(mats,G.from_bits(x).astype(G.F)).items()}
    cycles={kk:int(v) for kk,v in re.findall(r'(\w+)=(-?\d+)',next(l for l in p.stdout.splitlines() if l.startswith('OP ')))}
    return dict(case=kind,pass_=p.returncode==0 and writes==expected and p.stdout.strip().splitlines()[-1].startswith('PASS'),
                full_K=k,rows=len(expected),metadata=meta,cycles=cycles,sim_log_sha256=P.digest(log),
                checkpoint_header_sha256=ck.pins)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,default=P.D.SNAP_DEFAULT)
    p.add_argument('--work',type=Path,required=True);p.add_argument('--exe',type=Path,required=True)
    p.add_argument('--record',type=Path,required=True);a=p.parse_args()
    r=[run(a.snapshot,a.work,a.exe,k) for k in ['gu_packed','gu_spread','w2_packed']]
    out=dict(verdict='PASS' if all(x['pass_'] for x in r) else 'FAIL',cases=r,
             gu_packing_cycle_delta=r[0]['cycles']['phase_cycles']-r[1]['cycles']['phase_cycles'],
             clock_GHz=1.2,source_sha256=P.digest(__file__),executable_sha256=P.digest(a.exe),
             rtl_source_sha256={str(x.relative_to(P.ROOT)):P.digest(x) for x in FD.RTL+FD.DIE+FD.ROMS},
             physical_qualified=False,production_qelement_qualified=False)
    if a.record.exists():raise FileExistsError(a.record)
    a.record.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out,indent=1))
    if out['verdict']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
