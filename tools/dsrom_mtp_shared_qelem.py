#!/usr/bin/env python3
"""Remote-only shared W2 minimum: released weights, explicitly scoped GU sample."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
import numpy as np
import dsrom_mtp_seed_qs5f as S
from dsrom_mtp_seed_qs5f import B,F,I,A,G
from dsrom_mtp_shared_qelem_model import model

def bench(raw_negative=False):
    s=B.TB.replace('0:15359','0:2303').replace('0:479','0:71')
    s=s.replace('k<240','k<36').replace('nq==480','nq==72')
    s=s.replace('wire busy,fault;', 'wire busy,fault,walking,bank_free,sh_free;')
    s=s.replace(".go_tag(2'd0),", ".go_tag(2'd0),.walking(walking),.bank_free(bank_free),.sh_free(sh_free),")
    s=s.replace('end cfg_v=0;repeat(6)@(negedge clk);go=1;', 'end cfg_v=0;repeat(6)@(negedge clk);wait(sh_free && !walking);repeat(6)@(negedge clk);go=1;')
    extra=r'''
 reg[31:0]rounded_gold[0:1];wire[1:0]rv,re,rf;wire[63:0]raw_return;wire[31:0]bf_return;
 integer nr=0,issued=0,round_last=0;
 for(genvar j=0;j<2;j++)begin:ret
 wire[15:0]row;wire[2:0]pos;
 ot_v41_ret_root #(.D(16),.QD(16)) root(.clk(clk),.rst_n(rst_n),.i_v(pv[j]),
 .i_t({3'd0,prow[j*16+:16],5'd0,3'd0,5'd1}),.i_d(pval[j*32+:32]),.i_e(perr[j]),
 .r_v(rv[j]),.r_row(row),.r_pos(pos),.r_fp32(raw_return[j*32+:32]),
 .r_bf16(bf_return[j*16+:16]),.r_e(re[j]),.fault(rf[j]));
 end
 always @(posedge clk)if(rst_n)begin
 if(dut.u_e.issue)issued<=issued+1;
 for(integer j=0;j<2;j++)if(rv[j])begin
 if(re[j] || rf[j] || {bf_return[j*16+:16],16'd0}!==rounded_gold[j])
 $fatal(1,"shared rounded contribution mismatch row%0d",j);
 round_last<=cyc;end
 if(|rv)nr<=nr+rv[0]+rv[1];end
'''
    if raw_negative:
        extra=extra.replace("{bf_return[j*16+:16],16'd0}!==rounded_gold[j]", "raw_return[j*32+:32]!==rounded_gold[j]")
    s=s.replace('integer cyc=0,',extra+'\n integer cyc=0,')
    s=s.replace('$readmemh({dir,"/x.hex"},x);','$readmemh({dir,"/rounded.hex"},rounded_gold);$readmemh({dir,"/x.hex"},x);')
    s=s.replace('if(ny!=2)', 'if(nr!=2 || issued!=72)$fatal(1,"round/read count nr=%0d issued=%0d",nr,issued);if(ny!=2)')
    s=s.replace('$display("MTP_SEED PASS K=15360 rows=2 quant_cycles=%0d first_cycles=%0d last_cycles=%0d",quant_end-quant_start+1,first-go_cycle,last-go_cycle);', '$display("MTP_SHARED_Q PASS K=2304 rows=2 issues=%0d rowbank_reads=%0d MACs=%0d weight_bytes=%0d quant_cycles=%0d first_cycles=%0d last_cycles=%0d round_last_cycles=%0d complete_cycles=%0d",issued,2*issued,64*issued,64*issued,quant_end-quant_start+1,first-go_cycle,last-go_cycle,round_last-go_cycle,round_last-quant_start+1);')
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--sample',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--jobs',type=int,default=12);p.add_argument('--raw-negative',action='store_true');a=p.parse_args()
    a.work.mkdir(parents=True,exist_ok=True);G.set_arith('chunk8');ck=A.Ckpt(a.snapshot)
    sample=np.load(a.sample)['h_in'][0];assert sample.shape==(5120,)
    sample=G.to_bf16(sample);config=json.loads(a.config.read_text());limit=G.F(config.get('text_config',config)['swiglu_limit'])
    prefix='mtp.0.ffn.shared_experts.'
    w1=A.Mat(ck,prefix+'w1','fp8',2304,5120);w3=A.Mat(ck,prefix+'w3','fp8',2304,5120)
    g=G.linear_q(w1.w,sample);u=G.linear_q(w3.w,sample)
    x=G.to_bf16(G.mul(G.silu(np.minimum(g,limit).astype(G.F)),np.clip(u,-limit,limit).astype(G.F)))
    m=A.Mat(ck,prefix+'w2','fp8',2,2304);m.s81_segments=[[0,2304]];m.s81_place=[(0,0,0)]
    acc,bf,xq,xe=A.golden_rows(m,x);assert np.any(acc != (bf << 16)), 'raw-root negative must distinguish rounding'
    fld=I.Field(1,1,0,pp=True,fast=True);ph=I.add_phase(fld,[m],(False,False),0)
    for mb in range(2):
        for parity in (0,1):
            f=a.work/f'seed{"b" if mb else ""}_{parity}.viamap.hex';A.viamap({k//2:v for k,v in fld.words[mb].items() if k%2==parity},f);f.write_text(''.join(f.read_text().splitlines(keepends=True)[:512]))
    def hx(n,vs,w):(a.work/n).write_text(''.join(f'{int(v):0{w}x}\n' for v in vs))
    codes=A.x_codes(xq);hx('x.hex',G.bits(x),8);hx('gold.hex',acc,8);hx('rounded.hex',bf<<16,8);hx('cfg.hex',fld.cfg[0][0],12);hx('stream.hex',fld.stream,12);hx('q.hex',[int.from_bytes(codes[k:k+32].tobytes(),'little') for k in range(0,2304,32)],64);hx('e.hex',xe.astype(int)&1023,3)
    meta=model();meta.update(phase=ph,source_headers=ck.pins,config_sha256=hashlib.sha256(a.config.read_bytes()).hexdigest(),sample_sha256=hashlib.sha256(a.sample.read_bytes()).hexdigest(),GU_sha256=hashlib.sha256(G.bits(x).tobytes()).hexdigest(),raw_roots=acc.tolist(),rounded_widened_roots=(bf<<16).tolist(),swiglu_limit=float(limit))
    (a.work/'plan.json').write_text(json.dumps(meta,indent=2)+'\n')
    tb=a.work/'tb.sv';tb.write_text(bench(a.raw_negative).replace('QXV','10').replace('NBTS',str(ph['nbeat'])))
    sources=list(dict.fromkeys(F.RTL+F.QRTL+F.ROMS));run=subprocess.run([os.environ.get('OT_VERILATOR',F.VERILATOR),'--binary','--timing','-Wno-fatal','--top-module','tb_mtp_seed','--Mdir',str(a.work/'obj'),'-j',str(a.jobs),str(tb)]+list(map(str,sources)),text=True,capture_output=True);(a.work/'build.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('build failed')
    run=subprocess.run([str(a.work/'obj/Vtb_mtp_seed'),f'+DATA={a.work}',f'+OT_ROM_DIR={a.work}'],text=True,capture_output=True);(a.work/'sim.log').write_text(run.stdout+run.stderr);print(run.stdout)
    if a.raw_negative:
        if run.returncode and 'shared rounded contribution mismatch' in run.stdout:print('SHARED_RAW_ROOT FAIL_AS_REQUIRED');return
        raise RuntimeError('missing-rounding mutant escaped')
    if run.returncode or 'MTP_SHARED_Q PASS' not in run.stdout:raise RuntimeError('shared native gate failed')
if __name__=='__main__':main()
