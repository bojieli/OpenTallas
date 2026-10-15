#!/usr/bin/env python3
"""Native576 SW:144 SWE leaves,6 AQ engines and actual mapped operands/results."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
RTL=['rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_f12.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv', 'rtl/dsrom_sys/s81_suhc/ot_s81_su_core.sv', 'rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv', 'rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv', 'rtl/hdc/v41x/ot_hdc_v41x_spshort.sv', 'rtl/dsrom_sys/s81_suhc/dsfd_sp_su.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv', 'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv', 'rtl/hdc/v41x/ot_dsrom_su_norm.sv', 'rtl/hdc/v41x/ot_dsrom_su_swiglu.sv', 'rtl/hdc/v41x/ot_dsrom_su_f12.sv', 'rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv', 'rtl/hdc/v41x/ot_dsrom_su_softmax.sv', 'rtl/hdc/v41x/ot_dsrom_su_softmax_add.sv', 'rtl/hdc/v41x/ot_dsrom_su_softmax_add6.sv', 'rtl/hdc/v41x/ot_dsrom_su_softmax_exp6.sv', 'rtl/hdc/v41x/ot_dsrom_su_softmax_f12r.sv', 'rtl/hdc/v41x/ot_dsrom_su_softmax_m9.sv', 'rtl/hdc/v41x/ot_dsrom_su_add6.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_fastfp_lat_f12.sv', 'rtl/hdc/v41/ot_hdc_fsqrt.sv', 'rtl/hdc/v41/ot_hdc_fdiv.sv', 'rtl/hdc/v41/ot_hdc_softplus.sv', 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv', 'rtl/hdc/v41/ot_hdc_actquant.sv', 'rtl/hdc/v41x/ot_dsrom_aq12.sv', 'rtl/hdc/v41x/ot_dsrom_divc.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_hctl.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_ctl.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_norm_lg.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_tile.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_qb.sv', 'rtl/hdc/ot_sram_dline.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw.sv', 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_qn.sv', 'rtl/hdc/ot_sram_bank.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_kv.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv', 'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_cn_ik.sv', 'rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv', 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxt.sv', 'rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_su_h.sv']

def prep(out):
    from dsrom_su_swiglu import golden_swiglu,aq_lines
    rng=np.random.default_rng(20261015)
    g=rng.uniform(-15,15,576).astype(np.float32);u=rng.uniform(-14,14,576).astype(np.float32)
    weight=np.float32(0.375);lim=np.float32(10)
    a=golden_swiglu(g,u,np.repeat(weight,576),lim)
    blocks=[int(s,16) for s in aq_lines(a,False)]
    expected=[0]*28
    for b,x in enumerate(blocks):
        y=x&((1<<512)-1);q=(x>>512)&((1<<256)-1);e=(x>>768)&1023
        expected[b//2]|=q<<(256*(b%2));expected[9]|=e<<(16*b);expected[10+b]=y
    op=np.zeros((8,192),dtype=np.uint32)
    op[0,0]=8000;op[0,3]=lim.view(np.uint32);op[0,4]=2
    # Actual common RW layout: six routed weights words5..10, shared literal word11.
    op[1,5:11]=np.asarray([.125,.25,.375,.5,.625,.75],np.float32).view(np.uint32);op[1,11]=0x3f800000
    op[2:5]=g.view(np.uint32).reshape(3,192);op[5:8]=u.view(np.uint32).reshape(3,192)
    def pack(row):return sum(int(x)<<(32*i) for i,x in enumerate(row))
    (out/'sw_operands.mem').write_text(''.join(f'{pack(row):01536x}\n' for row in op))
    (out/'sw_expected.mem').write_text(''.join(f'{x:0128x}\n' for x in expected))
    (out/'stimulus.json').write_text(json.dumps(dict(scope='declared external full576 component operands, not native FIELD outputs',seed=20261015,actual_rows=72,quant_blocks=18,result_rows=28,weight_word=7,weight=float(weight)),indent=2)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prep','run','lint']);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mut',type=int,default=0);ap.add_argument('--missing',type=int,default=0);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    if a.mode=='prep':prep(out);return
    rtl=list(dict.fromkeys(RTL+['rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw576_static.sv','rtl/dsrom_sys/s81_suhc/test/tb_s81_su_sw576_static.sv']))
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in rtl}
    tag=f'm{a.mut}_p{a.missing}';obj=out/('obj_'+tag)
    cmd=['verilator','--lint-only' if a.mode=='lint' else '--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_su_sw576_static','-Mdir',str(obj),'-j','8',f'-GMUT={a.mut}',f'-GMISSING={a.missing}',*[str(ROOT/p) for p in rtl]]
    with(out/('build_'+tag+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode or a.mode=='lint':raise SystemExit(r.returncode)
    if pins!={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in rtl}:raise SystemExit('source changed')
    with(out/('run_'+tag+'.log')).open('w') as f:r=subprocess.run([str(obj/'Vtb_s81_su_sw576_static')],cwd=out,stdout=f,stderr=subprocess.STDOUT)
    (out/('receipt_'+tag+'.json')).write_text(json.dumps(dict(qualified=False,source_sha256=pins,returncode=r.returncode,mutant=a.mut,missing=a.missing),indent=2)+'\n');print((out/('run_'+tag+'.log')).read_text());raise SystemExit(r.returncode)
if __name__=='__main__':main()
