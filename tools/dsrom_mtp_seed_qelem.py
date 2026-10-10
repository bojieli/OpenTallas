#!/usr/bin/env python3
"""Remote-only full-K seed: two released rows, native QX pair and actual activation quantisers.
The current field descriptor's 13-bit K cannot encode15360: this bench drives the native element ABI.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
import numpy as np
import dsrom_1m_field as F
import v41_die_images_w17w10 as I
import rtl_v41_rom_array as A
import hdc_golden_v41 as G
ROOT=Path(__file__).resolve().parents[1]
TB=r'''
`timescale 1ns/1ps
module tb_mtp_seed;
 reg clk=0; always #0.416667 clk=~clk;
 reg rst_n=0,cfg_v=0,go=0,xs_v=0;reg[4:0]cfg_a=0;reg[47:0]cfg_d=0;
 reg[7:0]xs_p=0;reg[2:0]xs_b=0;reg[1:0]xs_sv=0;reg[255:0]xs_q0=0,xs_q1=0;reg[9:0]xs_e0=0,xs_e1=0;
 wire[1:0]pv,perr;wire[63:0]pval;wire[31:0]prow;wire[9:0]pseg,pnseg;wire[5:0]ppos;wire busy,fault;
 ot_v41_rom_elem_q_qx_w10 #(.NB(2),.MTP(1),.EARLY(1),.FAST(1),.PP(1),.QTIMING_FIX(1),.QPIPE(1),.QP_XS(1),.QP_CAP(0),.QP_P1(1),.QP_CSAM(10),.QZ(1),.QZ_NS(8),.QZ_NE(4),.QY(1),.QX(QXV),.INSTANCE("seed")) dut
 (.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_a(cfg_a),.cfg_d(cfg_d),.go(go),.xs_v(xs_v),.xs_p(xs_p),.xs_b(xs_b),.xs_sv(xs_sv),.xs_q0(xs_q0),.xs_e0(xs_e0),.xs_q1(xs_q1),.xs_e1(xs_e1),.xs_pos(3'd0),.pv(pv),.pval(pval),.prow(prow),.pseg(pseg),.pnseg(pnseg),.perr(perr),.ppos(ppos),.busy(busy),.fault(fault));
 reg av=0;reg[2047:0]ax=0;wire[1:0]aqv,aqf;wire[511:0]aq;wire[19:0]ae;
 for(genvar j=0;j<2;j++)begin:qg
 wire[511:0]unused_y;
 ot_hdc_actquant quant(.clk(clk),.rst_n(rst_n),.v(av),.fp4(1'b0),.x(ax[j*1024+:1024]),.vo(aqv[j]),.q(aq[j*256+:256]),.e(ae[j*10+:10]),.y(unused_y),.fault(aqf[j]));end
 reg[31:0]x[0:15359],gold[0:1];reg[255:0]qgold[0:479],qb[0:479];reg[9:0]egold[0:479],eb[0:479];reg[47:0]cfg[0:24],stream[0:NBTS-1];
 integer cyc=0,nq=0,ny=0,go_cycle=0,quant_start=0,quant_end=0,first=0,last=0;string dir;
 always @(posedge clk)begin
 cyc<=cyc+1;
 if(rst_n && (&aqv))begin
 for(integer j=0;j<2;j++)begin
 if(aqf[j] || aq[j*256+:256]!==qgold[nq+j] || ae[j*10+:10]!==egold[nq+j])$fatal(1,"activation quant mismatch %0d",nq+j);
 qb[nq+j]<=aq[j*256+:256];eb[nq+j]<=ae[j*10+:10];end
 nq<=nq+2;quant_end<=cyc;end
 for(integer j=0;j<2;j++)if(pv[j])begin
 if(perr[j] || prow[j*16+:16]!=j || pseg[j*5+:5]!=0 || pnseg[j*5+:5]!=1 || pval[j*32+:32]!==gold[j])$fatal(1,"seed row %0d got %h want %h",j,pval[j*32+:32],gold[j]);
 if(ny==0)first<=cyc;last<=cyc;end
 if(|pv)ny<=ny+pv[0]+pv[1];
 if(rst_n && fault)$fatal(1,"element fault");end
 initial begin
 if(!$value$plusargs("DATA=%s",dir))$fatal;
 $readmemh({dir,"/x.hex"},x);$readmemh({dir,"/gold.hex"},gold);$readmemh({dir,"/q.hex"},qgold);$readmemh({dir,"/e.hex"},egold);$readmemh({dir,"/cfg.hex"},cfg);$readmemh({dir,"/stream.hex"},stream);
 repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);quant_start=cyc;
 for(integer k=0;k<240;k++)begin av=1;for(integer j=0;j<64;j++)ax[j*32+:32]=x[k*64+j];@(negedge clk);end av=0;wait(nq==480);@(negedge clk);
 for(integer k=0;k<25;k++)begin cfg_v=1;cfg_a=k;cfg_d=cfg[k];@(negedge clk);end cfg_v=0;repeat(6)@(negedge clk);go=1;go_cycle=cyc;@(negedge clk);go=0;repeat(4)@(negedge clk);
 for(integer k=0;k<NBTS;k++)begin
 xs_v=stream[k][0];xs_p=stream[k][8:1];xs_b=stream[k][11:9];xs_sv=stream[k][13:12];
 if(xs_v)begin xs_q0=qb[xs_p*16+xs_b];xs_e0=eb[xs_p*16+xs_b];xs_q1=qb[xs_p*16+8+xs_b];xs_e1=eb[xs_p*16+8+xs_b];end
 @(negedge clk);end xs_v=0;
 repeat(512)@(negedge clk);if(ny!=2)$fatal(1,"missing/duplicate rows %0d",ny);
 $display("MTP_SEED PASS K=15360 rows=2 quant_cycles=%0d first_cycles=%0d last_cycles=%0d",quant_end-quant_start+1,first-go_cycle,last-go_cycle);$finish;end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--ref',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--qx',type=int,default=9);p.add_argument('--jobs',type=int,default=12);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
 a.work.mkdir(parents=True,exist_ok=True);G.set_arith('chunk8');ck=A.Ckpt(a.snapshot);m=A.Mat(ck,'mtp.0.main_proj','fp8',2,15360);m.s81_segments=[[0,15360]];m.s81_place=[(0,0,0)]
 hs=[np.load(a.ref/f'ctx1048576_L{l}.npz')['h_in'] for l in (37,38,39)]
 def mean(h):
  assert h.shape[0]==4 and h.shape[-1]==5120,h.shape
  return G.to_bf16(G.mul(G.seqsum([h[j] for j in range(4)]),G.F(.25)))
 x=np.concatenate([mean(h) for h in hs]);assert x.shape==(15360,),x.shape
 fld=I.Field(1,1,0,pp=True,fast=True);ph=I.add_phase(fld,[m],(True,False),0)
 for mb in range(2):
  name='seed'+('b' if mb else '')
  for parity in (0,1):
   t=a.work/f'{name}_{parity}.viamap.hex';A.viamap({k//2:v for k,v in fld.words[mb].items() if k%2==parity},t);t.write_text(''.join(t.read_text().splitlines(keepends=True)[:512]))
 def hexfile(n,vs,w):(a.work/n).write_text(''.join(f'{int(v):0{w}x}\n' for v in vs))
 acc,_,xq,xe=A.golden_rows(m,x);codes=A.x_codes(xq)
 hexfile('x.hex',G.bits(x),8);hexfile('gold.hex',acc,8);hexfile('cfg.hex',fld.cfg[0][0],12);hexfile('stream.hex',fld.stream,12)
 hexfile('q.hex',[int.from_bytes(codes[k:k+32].tobytes(),'little') for k in range(0,15360,32)],64);hexfile('e.hex',xe.astype(int)&1023,3)
 tb=a.work/'tb.sv';tb.write_text(TB.replace('QXV',str(a.qx)).replace('NBTS',str(ph['nbeat'])))
 meta=dict(K=15360,rows=2,activation_blocks=480,quantisers=2,activation_port_bytes_per_cycle=256,weight_words_per_macro=480,units=30,subblocks=4,phase=ph,qx=a.qx,field_descriptor_K_limit=8191,whole_field_qualified=False,MACs_per_issue_cycle=64,issued_weight_bytes_per_cycle=64,weight_boundary_bits_per_cycle=548,activation_boundary_bits_per_cycle=2048,rom_carrier_bits=274,weight_payload_bits=256,UE8M0_bits=8,unused_carrier_bits=10,source_headers=ck.pins,input_sha256=hashlib.sha256(G.bits(x).tobytes()).hexdigest())
 (a.work/'plan.json').write_text(json.dumps(meta,indent=1)+'\n')
 if a.prepare_only:return
 sources=list(dict.fromkeys(F.RTL+F.QRTL+F.ROMS))
 cmd=[os.environ.get('OT_VERILATOR',F.VERILATOR),'--binary','--timing','-Wno-fatal','--top-module','tb_mtp_seed','--Mdir',str(a.work/'obj'),'-j',str(a.jobs),str(tb)]+list(map(str,sources))
 run=subprocess.run(cmd,text=True,capture_output=True);(a.work/'build.log').write_text(run.stdout+run.stderr)
 if run.returncode:raise RuntimeError('seed build failed')
 run=subprocess.run([str(a.work/'obj/Vtb_mtp_seed'),f'+DATA={a.work}',f'+OT_ROM_DIR={a.work}'],text=True,capture_output=True);(a.work/'sim.log').write_text(run.stdout+run.stderr);print(run.stdout)
 if run.returncode or 'MTP_SEED PASS' not in run.stdout:raise RuntimeError('seed exact gate failed')
if __name__=='__main__':main()
