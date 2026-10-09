#!/usr/bin/env python3
"""Remote minimum exact native TU formatter vehicle with finite8packet credits."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);a=ap.parse_args()
 w=a.work.resolve();w.mkdir(parents=True,exist_ok=True)
 packets=[];flits=[];rank=73;dst=9;kind=1
 for q,n in enumerate([2,16,342,1366]):
  tuples=[]
  for i in range(n):
   lv=int(i%11!=3);score=(i*193+q*7)&65535;bid=q*2048+i
   tuples.append((bid<<17)|(score<<1)|lv)
  for i in range(0,n,2):
   x,y=tuples[i:i+2];last=i+2==n
   co=1|((last and q==3)<<1)|(q<<2)|((x&1)<<4)|((y&1)<<5)|(((x>>1)&65535)<<6)|(((y>>1)&65535)<<22)|((x>>17)<<38)|((y>>17)<<55)
   packets.append(co|(int(last)<<72))
  for b,i in enumerate(range(0,n,15)):
   group=tuples[i:i+15];payload=sum(t<<(34*j) for j,t in enumerate(group))
   payload|=int(i+15>=n)<<511
   flits.append(payload|(((q<<14)|b)<<512)|(rank<<528)|(dst<<536)|(kind<<544))
 for name,values in [('packets',packets),('flits',flits)]:
  (w/(name+'.mem')).write_text(''.join(f'{v:x}\n' for v in values))
 tb=w/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
reg clk=0;always #0.416 clk=~clk;
reg por_n=0,retained=0;reg[71:0]co=0;reg qlast=0;wire coc,v,drained,fault;
reg ready=0;wire[544:0]tu;wire[72:0]owner;
reg[72:0]pk[0:NP-1];reg[544:0]gold[0:NF-1];
integer sent=0,got=0,credits=8,cyc=0,errors=0;reg mutant;
ot_hbm_native_candidate_format #(.ENABLE(1))dut(.clk(clk),.por_n(por_n),
.owner_valid(1'b1),.owner_fault(1'b0),.retained(retained),.owner_frame(73'h123456789abcdef),
.owner_rank(7'd73),.tu_kind(1'b1),.tu_dst(8'd9),.co(co),.co_quarter_last(qlast),.coc(coc),
.tu_v(v),.tu_r(ready),.tu(tu),.tu_owner(owner),.drained(drained),.fault(fault));
initial begin
$readmemh("packets.mem",pk);$readmemh("flits.mem",gold);mutant=$test$plusargs("MUT_ID");
repeat(4)@(negedge clk);por_n=1;repeat(2)@(negedge clk);retained=1;
while(got<NF && cyc<NP*40+100)begin
@(negedge clk);cyc=cyc+1;ready=(cyc%10==0);co=0;qlast=0;
if(sent<NP&&credits>0&&cyc%3!=0)begin
co=pk[sent][71:0];qlast=pk[sent][72];if(mutant&&sent==30)co[38]=!co[38];
sent=sent+1;credits=credits-1;end
@(posedge clk);
if(coc)credits=credits+1;
if(v&&ready)begin
if(tu!==gold[got]||owner!==73'h123456789abcdef)begin errors=errors+1;$display("MISMATCH flit=%0d",got);end
got=got+1;end
if(fault)$fatal(1,"FAULT");
end
@(negedge clk);co=0;qlast=0;repeat(5)@(negedge clk);
if(got!=NF||sent!=NP||!drained||credits!=8)$fatal(1,"PROTOCOL sent=%0d got=%0d credits=%0d",sent,got,credits);
$display("FORMAT_DONE packets=%0d flits=%0d cycles=%0d errors=%0d",sent,got,cyc,errors);
if(errors)$fatal(1,"EXACT_MISMATCH");$finish;
end
endmodule
'''.replace('NP',str(len(packets))).replace('NF',str(len(flits))))
 src=ROOT/'rtl/hbm_accel/index/ot_hbm_native_candidate_format.sv'
 cmd=['verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','tb','--Mdir',str(w/'obj'),str(src),str(tb)]
 with (w/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 (w/'build.exit').write_text(str(r.returncode)+'\n')
 if r.returncode:return r.returncode
 runs=[]
 for name,extra in [('base',[]),('MUT_ID',['+MUT_ID'])]:
  r=subprocess.run([str(w/'obj/Vtb'),*extra],cwd=w,capture_output=True,text=True)
  (w/(name+'.log')).write_text(r.stdout+r.stderr)
  ok=(r.returncode==0 and 'errors=0' in r.stdout) if not extra else (r.returncode!=0 and 'EXACT_MISMATCH' in r.stdout and 'FORMAT_DONE' in r.stdout)
  runs.append(dict(name=name,exit=r.returncode,pass_gate=ok))
 record=dict(verdict='PASS' if all(r['pass_gate'] for r in runs)else 'FAIL',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),packets=len(packets),flits=len(flits),runs=runs,scope='lossless literal slots, quarter partial, actual33bit header, finite8credits,90percent TU stalls; no physical credit')
 (w/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(record['verdict'])
 return 0 if record['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
