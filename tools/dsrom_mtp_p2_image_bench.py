#!/usr/bin/env python3
"""Load the generated complete pair0 image and its first legal PP config into RTL."""
import argparse,json,re,subprocess
from pathlib import Path
import numpy as np
import dsrom_mtp_p2 as P
import dsrom_1m_field as FD
import v41_die_images_w17w10 as I
import rtl_v41_rom_array as A
import hdc_golden_v41 as G


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,default=P.D.SNAP_DEFAULT)
    p.add_argument('--image',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--exe',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--record',type=Path,required=True);a=p.parse_args()
    proof=json.loads(a.config.read_text());first=proof['configs'][0]
    assert (proof['side'],proof['rank'],proof['pair'])==('A',0,0)
    assert (first['stage'],first['expert'],first['subphase'])==(0,0,0)
    G.set_arith('chunk8');ck=A.Ckpt(a.snapshot);mats=[]
    for op in ['w1','w3']:
        m=FD.take(A.Mat(ck,f'mtp.0.ffn.experts.0.{op}','fp4',576,5120),[0,1])
        m.s81_segments=[[0,5120]];m.s81_place=[(0,0,0)];mats.append(m)
    fld=I.Field(2,1,0,pp=True,fast=True);meta=I.add_phase(fld,mats,(False,False),0)
    data=np.frombuffer(a.image.read_bytes(),dtype=np.uint8).reshape(8192,2,34)
    fld.words[:2]=[{j:int.from_bytes(data[j,mb].tobytes(),'little') for j in range(8192)} for mb in range(2)]
    fld.cfg[0][0]=first['cfg']
    img=a.work/'img';I.write_field(fld,img,2)
    x=FD.rand_x('p2-worst-gu',5120,False);vm=np.zeros(1<<16,dtype=np.uint32);vm[:5120]=x
    (img/'vm.hex').write_text(''.join(f'{int(v):08x}\n' for v in vm))
    ops=a.work/'ops.txt';ops.write_text('0 0 0 5120 32768 4\n')
    run=subprocess.run([str(a.exe),str(img),str(ops)],capture_output=True,text=True)
    log=a.work/'sim.log';log.write_text(run.stdout+run.stderr)
    writes={int(t[2]):int(t[3],16) for l in run.stdout.splitlines() if (t:=l.split()) and t[0]=='W'}
    gold=I.golden_phase(mats,G.from_bits(x).astype(G.F))
    expect={32768+(i if i<2 else i+574):b<<16 for i,(f,b) in gold.items()}
    result=dict(verdict='PASS' if run.returncode==0 and writes==expect and run.stdout.strip().splitlines()[-1].startswith('PASS') else 'FAIL',
                generated_complete_pair_image_sha256=P.digest(a.image),config_sha256=P.digest(a.config),
                source_sha256=P.digest(__file__),executable_sha256=P.digest(a.exe),
                golden_words=expect,rtl_words=writes,sim_log_sha256=P.digest(log),
                cycles={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',next(l for l in run.stdout.splitlines() if l.startswith('OP ')))},
                qualified_scope='generated A/rank0/pair0 image, first GU subphase, fullK5120',
                physical_qualified=False,production_qelement_qualified=False)
    if a.record.exists():raise FileExistsError(a.record)
    a.record.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1))
    if result['verdict']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
