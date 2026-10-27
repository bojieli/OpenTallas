#!/usr/bin/env python3
"""Actual XS controller with compiled Q/B/Q calendars, before/after one Q launch edge.

Uses released layer phase/stream images. This qualifies the native controller
mechanism, not frame ROM identity, arithmetic or whole-frame retirement.
"""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/s81_dv/layer_prog'),str(ROOT/'tools/s81_static_control')]
import xs_calendar as C
from field_cfg7_image import decode_bank

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--images',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 def read(name):return decode_bank([int(v,16) for v in (a.images/name).read_text().split()])
 P=read('pq_phase0.viamap.hex');S=sum([read(f'pq_stream{k}.viamap.hex') for k in range(4)],[])
 ph=[C.phase_word(P,n) for n in range(1024) if P[2*n]]
 q=next(x['ph'] for x in ph if not x['bf']);bf=next(x['ph'] for x in ph if x['bf']);phases=[q,bf,q]
 with patch.dict(os.environ,{'OT_XS_Q_CPR':'0'}):old=C.compile_pipeline(P,S,phases,0,256,cfg_lead=52)
 with patch.dict(os.environ,{'OT_XS_Q_CPR':'1'}):new=C.compile_pipeline(P,S,phases,0,256,cfg_lead=52)
 # Independent semantic assertion: CFG, requests, addresses and retire bits never move.
 mask=(1<<65)|(3<<66);end=max(max(old['rows']),max(new['rows']))+80
 for t in range(end):
  ow=next((v&((1<<75)-1) for v in old['packed'] if v>>75==t),0);nw=next((v&((1<<75)-1) for v in new['packed'] if v>>75==t),0)
  assert (ow&~mask)==(nw&~mask)
 oldwords=[0]*end;newwords=[0]*end;go=[0]*end;iph=[0]*end;hold=0
 for v in old['packed']:oldwords[v>>75]=v&((1<<75)-1)
 for v in new['packed']:newwords[v>>75]=v&((1<<75)-1)
 accepts={x['accept']:x['phase'] for x in old['phases']}
 for t in range(end):
  if t in accepts:hold=accepts[t];go[t]=1
  iph[t]=hold
 for name,data,width in [('old',oldwords,19),('new',newwords,19),('go',go,1),('iph',iph,3),('phase',P,18),('stream',S,12)]:
  (a.out/(name+'.hex')).write_text(''.join(f'{v:0{width}x}\n' for v in data))
 tb='''`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;reg rst=0,cv=0,go=0;reg[9:0]ph=0;
reg[74:0]oa=0,na=0;wire[609:0]ob,nb;wire ofault,nfault,oq,bq,nq,nbq;wire[47:0]oh,nh;wire[35:0]ohi,nhi;wire[15:0]ob0,ob1,nb0,nb1;
reg[74:0]om[0:END-1],nm[0:END-1];reg gm[0:END-1];reg[9:0]pm[0:END-1];reg[71:0]P[0:4095];reg[47:0]S[0:16383];reg[71:0]pw=0;reg[47:0]sq=0;integer mutant=0,ng=0,ncfg=0,nstream=0;
always@(posedge clk)begin pw<=P[2*ph];sq<=S[oa[53:40]];end
`define CTL(NAME,A,B,F,Q,BQ,H,HI,B0,B1) ot_s81sl_xs_ctl NAME(.clk(clk),.rst_n(rst),.calendar_v(cv),.calendar_action(A),.go(go),.i_ph(ph),.i_np(3'd0),.rom_gobf(pw[0]),.rom_sq(sq),.q_consume(Q),.b_consume(BQ),.hw_o(H),.h_hi_o(HI),.h_b0_o(B0),.h_b1_o(B1),.bc_hr_o(B),.fault(F));
`CTL(o,oa,ob,ofault,oq,bq,oh,ohi,ob0,ob1)
`CTL(n,na,nb,nfault,nq,nbq,nh,nhi,nb0,nb1)
reg qgo=0;reg[1:0]qtag=0;
always@(posedge clk)begin qgo<=nb[595]&&!nb[594];qtag<=nb[593:592];end
reg[609:0]non_go_mask=~(610'd15<<592);
initial begin
if($value$plusargs("MUT=%d",mutant))begin end
$readmemh("OUT/old.hex",om);$readmemh("OUT/new.hex",nm);$readmemh("OUT/go.hex",gm);$readmemh("OUT/iph.hex",pm);$readmemh("OUT/phase.hex",P);$readmemh("OUT/stream.hex",S);
repeat(8)@(negedge clk);rst=1;repeat(24)@(negedge clk);
for(int t=0;t<END;t++)begin
 @(negedge clk);cv=1;oa=om[t];na=mutant?om[t]:nm[t];go=gm[t];ph=pm[t];
 @(posedge clk);#0.001;
 if(ofault||nfault)$fatal(1,"NATIVE_CONTROLLER_FAULT t%0d old%b new%b",t,ofault,nfault);
 if((ob&non_go_mask)!==(nb&non_go_mask)||{oq,bq,oh,ohi,ob0,ob1}!=={nq,nbq,nh,nhi,nb0,nb1})$fatal(1,"NATIVE_NON_GO_DIFF t%0d",t);
 if((ob[595]&&!ob[594])!==qgo)$fatal(1,"NATIVE_Q_GO_DIFF t%0d",t);
 if(ob[595]&&!ob[594] && ob[593:592]!==qtag)$fatal(1,"NATIVE_Q_TAG_DIFF t%0d",t);
 if(ob[595]&&ob[594] && (!nb[595]||!nb[594]||ob[593:592]!==nb[593:592]))$fatal(1,"NATIVE_BF_GO_DIFF t%0d",t);
 ng+=int'(ob[595]);ncfg+=int'(ob[609]);nstream+=int'(oq||bq);
end
if(ng!=3||ncfg!=3||nstream<3)$fatal(1,"NATIVE_COVERAGE go%0d cfg%0d stream%0d",ng,ncfg,nstream);
$display("GB_NATIVE_CONTROLLER PASS Q/B/Q gos%0d cfgs%0d streams%0d,833ps",ng,ncfg,nstream);$finish;
end endmodule
'''.replace('END',str(end)).replace('OUT',str(a.out.resolve()))
 (a.out/'tb.sv').write_text(tb)
 cmd=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','2','--Mdir',str(a.out/'obj'),str(ROOT/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv'),str(ROOT/'rtl/lib/ot_rst_relay.sv'),str(ROOT/'rtl/v41rom/ot_v41_kreg.sv'),str(ROOT/'rtl/common/ot_prefix.sv'),str(a.out/'tb.sv')]
 with (a.out/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 for m in (0,1):
  with (a.out/f'run{m}.log').open('w') as f:r=subprocess.run([str(a.out/'obj/Vtb'),f'+MUT={m}'],stdout=f,stderr=subprocess.STDOUT)
  log=(a.out/f'run{m}.log').read_text();assert (r.returncode==0 and 'PASS' in log) if m==0 else (r.returncode!=0 and 'NATIVE_Q_GO_DIFF' in log),log
 (a.out/'check.json').write_text(json.dumps(dict(controller_mechanism_pass=True,full_frame_qualified=False,phases=phases,period=256,mutant='oldQlaunch CAUGHT',source_images={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.images.glob('*.hex')}),indent=2)+'\n')
 print('GB_NATIVE_CONTROLLER_PASS MUTANT_CAUGHT; full_frame_qualifiedFalse')

if __name__=='__main__':main()
