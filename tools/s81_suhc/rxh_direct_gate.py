#!/usr/bin/env python3
"""Source-bound production-width RX component test; no whole-chip qualification."""
import argparse, datetime, hashlib, json, os, subprocess, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
import hdc_golden_v41 as V
import su_gate as S
TB=r'''
module tb_rxh_direct;
 parameter integer XMUT=0;
 reg clk=0; always #5 clk=~clk;
 reg rst=0, st=0; reg[3:0] kind=0; reg[4:0] iv=0; reg[2559:0] idata=0;
 wire[1:0] ov,ov2,fu,fo; wire[13:0] oa[2],oa2[2]; wire[15:0] om[2]; wire[511:0] od[2],od2[2];
 ot_s81_su_rxh #(.S_RD(5),.L(4),.QL(8),.XMUT(XMUT)) dut(.clk(clk),.rst_in(rst),.dn_st_i(st),.dn_kind_i(kind),.dn_jid_i(8'd0),.dn_v_i(iv),.dn_d_i(idata),.o_v(ov[0]),.o_v2(ov2[0]),.o_a(oa[0]),.o_a2(oa2[0]),.o_m(om[0]),.o_d(od[0]),.o_d2(od2[0]),.o_fu(fu[0]),.o_fo(fo[0]));
 ot_s81_su_rxt #(.S_RD(5),.RAL(16),.QW(2)) reference(.clk(clk),.rst_in(rst),.dn_st_i(st),.dn_kind_i(kind),.dn_jid_i(8'd0),.dn_v_i(iv),.dn_d_i(idata),.o_v(ov[1]),.o_v2(ov2[1]),.o_a(oa[1]),.o_a2(oa2[1]),.o_m(om[1]),.o_d(od[1]),.o_d2(od2[1]),.o_fu(fu[1]),.o_fo(fo[1]));
 reg[511:0] inputs[0:205], expected[0:93];
 integer cyc=0,job=-1,err=0, n[2],first[2],last[2],issued=0,idx,base,count,p,q;
 always @(posedge clk) begin
  #1;cyc=cyc+1;
  for(integer d=0;d<2;d=d+1) begin
   if(ov[d]) begin
    if(n[d]==0) first[d]=cyc;
    last[d]=cyc;
    if(n[d]>=count || od[d]!==expected[base+n[d]] || om[d]!==16'hffff || oa[d] !== ((job==2)?(14'd1024+(n[d]/4)*32+28+n[d]%4):(14'd1024+n[d]))) begin
     if(err<8) $display("MISMATCH job=%0d d=%0d row=%0d cyc=%0d got=%h exp=%h addr=%0d",job,d,n[d],cyc,od[d],expected[base+n[d]],oa[d]);err=err+1;
    end
    n[d]=n[d]+1;
   end
   if(ov2[d]) begin
    last[d]=cyc;
    if(!ov[d] || n[d]>=count || od2[d]!==expected[base+n[d]] || oa2[d] !== (14'd1024+(n[d]/4)*32+28+n[d]%4)) begin
     if(err<8) $display("MISMATCH2 job=%0d d=%0d row=%0d cyc=%0d",job,d,n[d],cyc);err=err+1;
    end
    n[d]=n[d]+1;
   end
  end
 end
 task tick; begin @(negedge clk); end endtask
 task send(input integer mask,input integer startrow);begin tick();iv=mask;idata=0;for(integer s=0;s<5;s=s+1)if(mask&(1<<s)) idata[512*s+:512]=inputs[startrow+s];end endtask
 initial begin
  $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);
  count=0;base=0;for(integer d=0;d<2;d=d+1)begin n[d]=0;first[d]=-1;last[d]=-1;end
  repeat(5)tick();rst=1;repeat(10)tick();
  for(job=0;job<3;job=job+1)begin
   kind=8+job;st=1;tick();st=0;iv=0;
   count=(job==0)?6:(job==1)?24:64;base=(job==0)?0:(job==1)?6:30;
   for(integer d=0;d<2;d=d+1)begin n[d]=0;first[d]=-1;last[d]=-1;end
   idx=(job==0)?0:(job==1)?7:56;
   send((job==2)?31:1,idx);tick();iv=0;idx=idx+((job==2)?5:1);
   issued=cyc+2;
   for(p=0;p<((job==1)?2*count:count);p=p+((job==0)?1:2))begin send((job==0)?1:3,idx);idx=idx+((job==0)?1:2);end
   tick();iv=0;repeat(260)tick();
   for(integer d=0;d<2;d=d+1)begin
    $display("RXDIRECT job=%0d d=%0d rows=%0d first=%0d last=%0d issue=%0d first_latency=%0d last_latency=%0d",job,d,n[d],first[d],last[d],issued,first[d]-issued,last[d]-issued);
    if(n[d]!=count)err=err+1;
   end
   if(|fu || |fo)begin $display("FAULT fu=%b fo=%b",fu,fo);err=err+1;end
  end
  $display("RXDIRECT mut=%0d errors=%0d",XMUT,err);
  if(err) $fatal(1,"RXDIRECT FAIL");
  $display("RXDIRECT PASS");$finish;
 end
endmodule
'''
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(x):return sum(int(v)<<(32*i) for i,v in enumerate(np.asarray(x,np.float32).view(np.uint32)))
def prep(out):
 rng=np.random.default_rng(1015)
 ra=rng.uniform(-7,7,96).astype(np.float32); sc=rng.uniform(-4,4,384).astype(np.float32);bias=rng.uniform(-1,1,384).astype(np.float32)
 q=rng.uniform(-4,4,(16,512)).astype(np.float32)
 cs=np.cos(np.arange(32,dtype=np.float32)*np.float32(.09375));sn=np.sin(np.arange(32,dtype=np.float32)*np.float32(.09375))
 rr=lambda x:[row(a)for a in np.asarray(x,np.float32).reshape(-1,16)]
 inp=[1024]+rr(ra)+[1024]
 for a,b in zip(rr(sc),rr(bias)):inp += [a,b]
 inp += [1024]+rr(cs)+rr(sn)
 for h in q:inp+=rr(h[-64:])
 exp=rr(V.sqrt(V.softplus(ra)))+rr(V.add(sc,bias))+rr(V.rope_tail(q,(cs,sn))[:,-64:])
 assert len(inp)==125 and len(exp)==94,(len(inp),len(exp))
 for name,data in [('inputs',inp),('expected',exp)]: (out/(name+'.hex')).write_text(''.join(f'{r:0128x}\n'for r in data))
 (out/'tb_rxh_direct.sv').write_text(TB.replace('inputs[0:205]','inputs[0:124]'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mut',type=int,default=0);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);prep(out)
 src=list(dict.fromkeys(S.H.FP['rtl']+S.RTL+['rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxt.sv','rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv']))
 pins={s:sha(ROOT/s)for s in src};pins['tools/s81_suhc/rxh_direct_gate.py']=sha(__file__)
 for name in ['tools/hdc_golden_v41.py','tools/hdc_golden.py','tools/s81_suhc/hc_gate.py','tools/s81_suhc/su_gate.py']: pins[name]=sha(ROOT/name)
 obj=out/f'obj_m{a.mut}';cmd=[S.H.VERILATOR,'--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','--top-module','tb_rxh_direct','-Mdir',str(obj),'-j','8','--unroll-count','4','-fno-dfg',f'-GXMUT={a.mut}',*[str(ROOT/s)for s in src],str(out/'tb_rxh_direct.sv'),'-CFLAGS','-O1']
 with (out/f'build_m{a.mut}.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode: raise SystemExit(f'BUILD FAIL {r.returncode}')
 r=subprocess.run([str(obj/'Vtb_rxh_direct')],cwd=out,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/f'run_m{a.mut}.log').write_text(r.stdout);print(r.stdout,flush=True)
 assert all(sha(ROOT/s)==h for s,h in pins.items()),'source changed'
 rec=dict(schema='opentallas.s81.rxh_direct.v1',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=pins,mut=a.mut,exit=r.returncode,status='pass'if r.returncode==0 else'fail',arithmetic='actual RTL, no DPI',scope='component: rxh boundary; full 16 RA / 32 QR /16 RB lanes; 96 router acts,384 bias adds,16 heads rope',static_issue=True,output=r.stdout)
 (out/f'record_m{a.mut}.json').write_text(json.dumps(rec,indent=2)+'\n');return r.returncode
if __name__=='__main__':sys.exit(main())
