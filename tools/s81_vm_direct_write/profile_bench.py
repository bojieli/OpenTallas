#!/usr/bin/env python3
"""Actual selected profile master: full leaf ports each edge, independent golden.
Mutant flips bit0 at the actual native wrapper input, not a detached reference.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',required=True);ap.add_argument('--mutant',action='store_true');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 manifest=json.loads((R/'physical/s81_vm_direct_write_native_1015/remaining_profiles.json').read_text());p=next(p for p in manifest['profiles'] if p['tag']==a.profile)
 source=R/manifest['wrapper_source'];wrapper=source.read_text();assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['wrapper_sha256']
 if a.mutant:
  pat=r'(module '+re.escape(p['top'])+r'\b.*?endmodule)';m=re.search(pat,wrapper,re.S);assert m
  block=m[1];assert block.count('.i_data(i_data)')==1
  wrapper=wrapper[:m.start()]+block.replace('.i_data(i_data)',".i_data(i_data^1'b1)")+wrapper[m.end():]
 wp=a.out/'actual_profiles.sv';wp.write_text(wrapper)
 capture=p['bank_base'] is None;n=1 if capture else 8;b=0 if capture else p['bank_base'];top=p['top']
 defs=f'''`timescale 1ns/1ps
module tb;
localparam integer N={n},BASE={b};
reg ck=0,rst_n=0;always #5 ck=~ck;
reg [N-1:0] iv=0,iwe=0;reg[14*N-1:0] ir=0;reg[4*N-1:0] im=0;reg[128*N-1:0] id=0;reg[8*N-1:0] it=0;
wire[N-1:0] ov,owe;wire[4*N-1:0] om;wire[128*N-1:0] od;wire[8*N-1:0] ot;
integer cy,k,w,hi,bank,row,checks=0,bad=0,seed=32'h7ace1593;reg good;reg[N-1:0] xv,xwe;reg[4*N-1:0] xm;reg[128*N-1:0] xd;reg[8*N-1:0] xt;
'''
 if capture:defs+='wire[13:0] oq;reg[13:0] xq;\n'+top+' d(.ck(ck),.rst_n(rst_n),.i_v(iv),.i_we(iwe),.i_row(ir),.i_mask(im),.i_data(id),.i_tag(it),.o_v(ov),.o_we(owe),.o_row(oq),.o_mask(om),.o_data(od),.o_tag(ot));\n'
 else:defs+='wire[71:0] oq;reg[71:0] xq;wire fault;reg expect_fault=0,fault_due=0;\n'+top+' d(.ck(ck),.rst_n(rst_n),.i_v(iv),.i_we(iwe),.i_row(ir),.i_mask(im),.i_data(id),.i_tag(it),.o_v(ov),.o_we(owe),.o_addr(oq),.o_mask(om),.o_data(od),.o_tag(ot),.fault(fault));\n'
 defs+='''initial begin
 repeat(4)@(negedge ck);rst_n=1;repeat(4)@(negedge ck);
 for(cy=0;cy<8000/N;cy=cy+1)begin
  @(negedge ck);
  for(k=0;k<N;k=k+1)begin
   hi=(cy*17+k*13)%512;bank=BASE+k;row=32*hi+(bank^((hi%8)*4));
   iv[k]=cy%7!=0;iwe[k]=(cy+k)%3!=0;ir[14*k+:14]=14'(row);im[4*k+:4]=4'(cy+k);it[8*k+:8]=8'(cy+11*k);
   for(w=0;w<4;w=w+1)id[128*k+32*w+:32]=$random(seed);
  end
'''
 if capture:defs+='xv=iv;xwe=iwe;xq=ir;xm=im;xd=id;xt=it;\n'
 else:defs+='''  // Deterministic wrong-bank witness late in the normal stream, never waits.
  if(cy==995)ir[0]=!ir[0];
  for(k=0;k<N;k=k+1)begin
   row=ir[14*k+:14];bank=(row%32)^(((row/32)%8)*4);good=(bank==BASE+k);
   xv[k]=iv[k]&&good;xwe[k]=xv[k]?iwe[k]:0;xq[9*k+:9]=xv[k]?9'(row/32):0;
   xm[4*k+:4]=xv[k]?im[4*k+:4]:0;xd[128*k+:128]=xv[k]?id[128*k+:128]:0;xt[8*k+:8]=xv[k]?it[8*k+:8]:0;
   if(iv[k]&&!good)expect_fault=1;
  end
'''
 defs+='''  @(posedge ck);#1;checks=checks+N;
'''
 if capture:defs+='''  if({ov,owe,oq,om,od,ot}!=={xv,xwe,xq,xm,xd,xt})begin bad=bad+1;if(bad<4)$display("PROFILE_DATA_MISMATCH cycle%0d",cy);end
'''
 else:defs+='''  // Scatter contract (S81 VM F6 2026-10-15): o_v/o_we exact every edge; address/mask/data/tag exact for every VALID
  // record (payload is registered straight from the pins and meaningful only with o_v); sticky fault at FAULT_AGE 3,
  // i.e. exactly one edge after the record that raised it.
  if({ov,owe}!=={xv,xwe})begin bad=bad+1;if(bad<4)$display("PROFILE_VALID_MISMATCH cycle%0d",cy);end
  for(k=0;k<N;k=k+1)if(xv[k]&&{oq[9*k+:9],om[4*k+:4],od[128*k+:128],ot[8*k+:8]}!=={xq[9*k+:9],xm[4*k+:4],xd[128*k+:128],xt[8*k+:8]})begin bad=bad+1;if(bad<4)$display("PROFILE_DATA_MISMATCH cycle%0d record%0d",cy,k);end
  if(fault!==fault_due)bad=bad+1;
  fault_due=expect_fault;
'''
 defs+=''' end
 if(bad)begin $display("PROFILE_WRITE_FAIL records %0d bad %0d",checks,bad);$fatal;end
 $display("PROFILE_WRITE_PASS records %0d bad0",checks);$finish;
end
endmodule
'''
 tb=a.out/'tb.sv';tb.write_text(defs);cmd=['iverilog','-g2012','-s','tb','-o',str(a.out/'tb'),str(tb),str(wp),str(R/'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_write_capture128.sv'),str(R/'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_scatter_b8_out.sv')]
 with (a.out/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 r=subprocess.run(['vvp',str(a.out/'tb')],capture_output=True,text=True);(a.out/'run.log').write_text(r.stdout+r.stderr)
 (a.out/'binding.json').write_text(json.dumps(dict(profile=p,actual_wrapper_sha256=hashlib.sha256(wp.read_bytes()).hexdigest(),source_wrapper_sha256=manifest['wrapper_sha256'],mutant=a.mutant,command=cmd,returncode=r.returncode),indent=2)+'\n');print(r.stdout+r.stderr,end='');raise SystemExit(r.returncode)
if __name__=='__main__':main()
