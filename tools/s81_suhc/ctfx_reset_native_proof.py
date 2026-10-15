#!/usr/bin/env python3
"""Actual serial CTfx reset contract; ot-run only. No full-token claim."""
import argparse,pathlib,subprocess,hashlib,json,shutil
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--case',default='all',choices=['all','positive','data_invert','valid_drop','reset_bypass']);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[2];o=pathlib.Path(a.out).resolve();o.mkdir(parents=True,exist_ok=True)
sp=r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctfx_reset_native.sv';rp=r/'rtl/lib/ot_rst_relay.sv';old=r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv'
s=old.read_text();b=s.index('module ot_s81_hc_ctfx #(');e=s.index('endmodule',b)+9;(o/'reference.sv').write_text(s[b:e])
tb="""module check;
reg clk=0,rst_in=0;reg [6:0] fv_in=0;reg [1127:0] fd_in=0;
wire [6:0] fv,old_fv;wire [1127:0] fdx,old_fdx;
ot_s81_hc_ctfx_reset_native dut(.*);
ot_s81_hc_ctfx ref_dut(.clk(clk),.rst_in(rst_in),.fv_in(fv_in),.fd_in(fd_in),.fv(old_fv),.fdx(old_fdx));
reg [31:0] rng=32'h791c4a53;integer cycle,j,age;
initial begin
// Drive an actual asynchronous reset event before the first clock.
#1;rst_in=1;#1;rst_in=0;age=0;
for(cycle=0;cycle<500;cycle=cycle+1)begin
 clk=0;#1;
 if(cycle==5 || cycle==155 || cycle==305)begin rst_in=1;age=0;end
 if(cycle==150 || cycle==300)begin rst_in=0;age=0;end
 if(rst_in)age=age+1;
 for(j=0;j<1128;j=j+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);fd_in[j]=rng[0];end
 fv_in=(rst_in && age>=4)?rng[6:0]:0;
 #1;clk=1;#1;
 if(fdx!==fd_in || old_fdx!==fd_in)$fatal(1,"data edge mismatch %0d",cycle);
 if(rst_in && age>=4 && fv!==old_fv)$fatal(1,"post-init valid mismatch %0d",cycle);
 if(rst_in && age<=2 && dut.rst_local[0]!==0)$fatal(1,"early reset release %0d",cycle);
 if(rst_in && age==3 && dut.rst_local[0]!==1)$fatal(1,"late reset release %0d",cycle);
 if((!rst_in || age<=3) && fv!==0)$fatal(1,"reset quarantine violation %0d",cycle);
 // A short reset assertion wholly between clock edges must clear immediately.
 if(cycle==100)begin
  clk=0;#1;rst_in=0;#1;
  if(fv!==0)$fatal(1,"short reset did not assert asynchronously");
  rst_in=1;age=0;
 end
end
$display("PASS CTfx reset native 500 cycles 1128 bits; release3 init+2 token+0; short asynchronous reset");$finish;end
endmodule
"""
(o/'check.sv').write_text(tb);src=sp.read_text();results=[]
for v in (['positive','data_invert','valid_drop','reset_bypass'] if a.case=='all' else [a.case]):
 s=src
 if v=='data_invert':s=s.replace('fdx<=fd_in;','fdx<=~fd_in;')
 if v=='valid_drop':s=s.replace('else fv<=fv_in;',"else fv<='0;")
 if v=='reset_bypass':s=s.replace('.rst_n(rst_local)', '.rst_n()');s=s.replace(' always @(posedge clk or negedge rst_local[0])',' assign rst_local[0]=rst_in;\n always @(posedge clk or negedge rst_local[0])')
 q=o/(v+'.sv');q.write_text(s);log=o/(v+'.log');obj=o/('obj_'+v)
 with log.open('w')as f:
  x=subprocess.run([shutil.which('verilator'),'--binary','--timing','-Wno-fatal','--top-module','check','--Mdir',str(obj),'-j','4',str(o/'reference.sv'),str(q),str(rp),str(o/'check.sv')],stdout=f,stderr=subprocess.STDOUT)
  if x.returncode:raise SystemExit('compile failed '+str(log))
  x=subprocess.run([str(obj/'Vcheck')],stdout=f,stderr=subprocess.STDOUT)
 if a.case!='all' and v!='positive':
  print(log.read_text());raise SystemExit(1 if x.returncode else 0)
 good=(x.returncode==0)==(v=='positive');results.append(dict(variant=v,returncode=x.returncode,expected=good))
 if not good:raise SystemExit('unexpected verdict '+str(log))
receipt=dict(status='PASS',scope='component reset protocol: initialization release 1->3 edges, asynchronous assertion including short pulse; data/token latency unchanged; not full reset equivalence or native timing',sources={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [sp,rp,old]},results=results)
(o/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
