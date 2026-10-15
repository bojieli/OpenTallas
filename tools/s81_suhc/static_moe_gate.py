#!/usr/bin/env python3
"""Prepare/execute full1280-word canonical-rank native MOE_SUM component."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
RTL=['rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_moe_sum_static.sv',
     'rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/ot_hdc_fastfp.sv',
     'rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv',
     'rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_sram_bank.sv','rtl/hdc/ot_sram_dline.sv',
     'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v',
     'rtl/dsrom_sys/s81_suhc/test/tb_s81_su_moe_sum_static.sv']

def prep(out):
    rng=np.random.default_rng(20261015)
    x=(rng.uniform(-2,2,size=(80,7,16))*np.exp2(rng.integers(-10,21,size=(80,7,16)))).astype(np.float32)
    x[:,:,0::4]=0;x[:,0,0::4]=np.float32(2**24);x[:,1,0::4]=1;x[:,2,0::4]=-np.float32(2**24)
    x[:,:,1::4]=0;x[:,0,1::4]=1;x[:,1,1::4]=np.float32(2**-8);x[:,2,1::4]=np.float32(2**-8)
    # Expected answers are external testbench oracles only. No result enters DUT.
    y=np.add(x[:,0,:],x[:,1,:],dtype=np.float32)
    for e in range(2,7):y=np.add(y,x[:,e,:],dtype=np.float32)
    bits=y.view(np.uint32);bits=np.where((bits&0x7fffffff)==0,np.uint32(0),bits)
    bits=(bits+np.uint32(0x7fff)+((bits>>16)&1))&np.uint32(0xffff0000)
    def pack(words):return sum(int(w)<<(32*i) for i,w in enumerate(words))
    (out/'operands.mem').write_text(''.join(f'{pack(row.reshape(-1).view(np.uint32)):0896x}\n' for row in x))
    (out/'expected.mem').write_text(''.join(f'{pack(row):0128x}\n' for row in bits))
    (out/'stimulus.json').write_text(json.dumps(dict(scope='declared external component operands; not integrated field output',
        source_nodes_L0=['L0.I'+str(i) for i in range(101,107)],rank_words=1280,rows=80,
        rounding='FP32 RNE after each of six sequential adds; only final BF16',seed=20261015),indent=2)+'\n')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['prep','run'])
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mut',type=int,default=0)
    ap.add_argument('--missing',type=int,default=0);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if a.mode=='prep':prep(out);return
    tag=f'm{a.mut}_p{a.missing}';obj=out/('obj_'+tag)
    cmd=['verilator','--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_su_moe_sum_static',
         '-Mdir',str(obj),'-j','8',f'-GMUT={a.mut}',f'-GMISSING={a.missing}',*[str(ROOT/p) for p in RTL]]
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in RTL}
    with(out/('build_'+tag+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:raise SystemExit(r.returncode)
    if pins!={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in RTL}:raise SystemExit('changed source')
    with(out/('run_'+tag+'.log')).open('w') as f:r=subprocess.run([str(obj/'Vtb_s81_su_moe_sum_static')],cwd=out,stdout=f,stderr=subprocess.STDOUT)
    (out/('receipt_'+tag+'.json')).write_text(json.dumps(dict(qualified=False,scope='actual mapped memories+six sequential native FP32 add leaves; component only',
        source_sha256=pins,returncode=r.returncode,mutant=a.mut,missing=a.missing,
        log_sha256=hashlib.sha256((out/('run_'+tag+'.log')).read_bytes()).hexdigest()),indent=2)+'\n')
    print((out/('run_'+tag+'.log')).read_text());raise SystemExit(r.returncode)
if __name__=='__main__':main()
