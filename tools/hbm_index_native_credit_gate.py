#!/usr/bin/env python3
"""Small remote query4credit and TU15slot parser exact/identity negative gates."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
QUERY='''`timescale 1ns/1ps
module tb;
reg clk=0;always #0.416 clk=~clk;
reg por_n=0,retained=0,bv=0,qbr=0;reg[72:0]frame=73'h123456;
reg[4:0]head;reg[1:0]bn;reg[1023:0]data;reg[15:0]weight;
wire br,drained,fault;wire[1047:0]qb;
integer sent,got,outstanding,cyc=0,i,round;reg mutant,mut_qb,injected=0;
ot_hbm_native_index_query_credit #(.ENABLE(1))dut(.clk(clk),.por_n(por_n),
.owner_valid(1'b1),.owner_fault(1'b0),.retained(retained),.owner_frame(73'h123456),
.block_frame(frame),.owner_rank(7'd17),.block_rank(7'd17),.block_v(bv),.block_r(br),
.block_head(head),.block_number(bn),.block_data(data),.head_weight(weight),.qbr(qbr),
.qb(qb),.drained(drained),.fault(fault));
initial begin
mutant=$test$plusargs("MUT_OWNER");mut_qb=$test$plusargs("MUT_QB");repeat(4)@(negedge clk);por_n=1;
for(round=0;round<2;round=round+1)begin
sent=0;got=0;outstanding=0;@(negedge clk);retained=1;
while((got<128||outstanding!=0)&&cyc<4000)begin
@(negedge clk);if(mut_qb&&sent==1&&!injected)begin dut.qb_hold[15]=!dut.qb_hold[15];injected=1;end
cyc=cyc+1;bv=sent<128;head=sent/4;bn=sent%4;weight=sent+31;
for(i=0;i<32;i=i+1)data[32*i+:32]=sent*100+i;
qbr=outstanding!=0&&cyc%7==0;
frame=(mutant&&sent==13)?73'h123457:73'h123456;
@(posedge clk);
if(bv&&br)sent=sent+1;
if(qb[0])begin
if(qb[5:1]!==5'(got/4)||qb[7:6]!==2'(got%4)||qb[1047:1032]!==16'(got+31))$fatal(1,"ORDER");
for(i=0;i<32;i=i+1)if(qb[8+32*i+:32]!==32'(got*100+i))$fatal(1,"DATA");
got=got+1;outstanding=outstanding+1;end
if(qbr)outstanding=outstanding-1;
if(fault)$fatal(1,"OWNER_REJECTED");
end
@(negedge clk);bv=0;qbr=0;repeat(3)@(negedge clk);
if(sent!=128||got!=128||!drained)$fatal(1,"PROTOCOL");
retained=0;repeat(3)@(negedge clk);
end
$display("QUERY_DONE blocks=256 cycles=%0d",cyc);$finish;
end
endmodule
'''
PARSE='''`timescale 1ns/1ps
module tb;
reg clk=0;always #0.416 clk=~clk;
reg por_n=0,fv=0,tr=0;reg[544:0]flit=0;
wire fr,tv,last,drained,fault;wire[33:0]tuple;wire[7:0]src;wire[15:0]idx;wire[3:0]slot;wire[72:0]owner;
integer sent=0,got=0,cyc=0,j;reg mutant,mut_payload,injected=0;
ot_hbm_native_candidate_parse #(.ENABLE(1))dut(.clk(clk),.por_n(por_n),
.owner_valid(1'b1),.owner_fault(1'b0),.owner_frame(73'h123456),.expected_kind(1'b1),.expected_dst(8'd9),
.flit_v(fv),.flit_r(fr),.flit(flit),.flit_owner(73'h123456),.tuple_v(tv),.tuple_r(tr),.tuple(tuple),
.tuple_src(src),.tuple_index(idx),.tuple_slot(slot),.quarter_last(last),.tuple_owner(owner),.drained(drained),.fault(fault));
initial begin
mutant=$test$plusargs("MUT_RESERVED");mut_payload=$test$plusargs("MUT_PAYLOAD");repeat(4)@(negedge clk);por_n=1;
while(got<60&&cyc<1000)begin
@(negedge clk);if(mut_payload&&sent==1&&!injected)begin dut.held[20]=!dut.held[20];injected=1;end
cyc=cyc+1;fv=sent<4;tr=cyc%5!=0;flit=0;
for(j=0;j<15;j=j+1)flit[34*j+:34]=sent*100+j;
flit[511]=1;flit[527:512]=sent<<14;flit[535:528]=73;flit[543:536]=9;flit[544]=1;
if(mutant)flit[510]=1;
@(posedge clk);
if(fv&&fr)sent=sent+1;
if(tv&&tr)begin
if(tuple!==34'((got/15)*100+got%15)||slot!==4'(got%15)||src!=73||idx!==16'((got/15)<<14)||last!==(got%15==14)||owner!==73'h123456)$fatal(1,"PARSE_MISMATCH");
got=got+1;end
if(fault)$fatal(1,"RESERVED_REJECTED");
end
@(negedge clk);fv=0;repeat(3)@(negedge clk);
if(got!=60||sent!=4||!drained)$fatal(1,"PROTOCOL");
$display("PARSE_DONE tuples=60 cycles=%0d",cyc);$finish;
end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=True);records=[]
 for name,text,rtl,mutant,diagnostic in [('query',QUERY,'ot_hbm_native_index_query_credit','MUT_OWNER','OWNER_REJECTED'),('parse',PARSE,'ot_hbm_native_candidate_parse','MUT_RESERVED','RESERVED_REJECTED')]:
  d=w/name;d.mkdir(exist_ok=True);tb=d/'tb.sv';tb.write_text(text);src=ROOT/'rtl/hbm_accel/index'/f'{rtl}.sv'
  with(d/'build.log').open('w')as f:r=subprocess.run(['verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','tb','--Mdir',str(d/'obj'),str(src),str(tb)],stdout=f,stderr=subprocess.STDOUT)
  (d/'build.exit').write_text(str(r.returncode)+'\n')
  if r.returncode:return r.returncode
  tests=[('base',[]),(mutant,['+'+mutant])]
  if name=='parse':tests.append(('MUT_PAYLOAD',['+MUT_PAYLOAD']))
  if name=='query':tests.append(('MUT_QB',['+MUT_QB']))
  for test,extra in tests:
   r=subprocess.run([str(d/'obj/Vtb'),*extra],capture_output=True,text=True);(d/(test+'.log')).write_text(r.stdout+r.stderr)
   ok=r.returncode==0 and '_DONE' in r.stdout if not extra else r.returncode!=0 and diagnostic in r.stdout
   records.append(dict(component=name,test=test,exit=r.returncode,pass_gate=ok,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
 record=dict(verdict='PASS'if all(x['pass_gate']for x in records)else'FAIL',runs=records,scope='query128blocks twoframes cold4credits delayedreturns; actual15slot TU parser backpressure/negative reservedbit; no physical credit')
 (w/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(record['verdict']);return 0 if record['verdict']=='PASS'else 1
if __name__=='__main__':raise SystemExit(main())
