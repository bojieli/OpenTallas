#!/usr/bin/env python3
"""Emit the actual window projection block against the original counter contract."""
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
s=(Path(__file__).resolve().parents[2]/"rtl/dsrom_sys/s81_head/ot_s81hd_ctl_hsf0_static.sv").read_text()
s=s.split("begin : g_window_pre",1)[1].split("assign window_open",1)[0].replace("rr[1]","rn")
assert "window_nz_q <= wcnt != 7'd1;" in s
v="module projected(input ck,rn,o3,sel_fx,input[6:0]wcnt,output observed);\n"+s+"\nassign observed=window_nz_q;endmodule\n"
tb="""module tb;
reg ck=0;always #5 ck=~ck;
reg rn=0,o3=0,sel_fx=0;reg[6:0]wcnt=0;wire observed;
projected dut(ck,rn,o3,sel_fx,wcnt,observed);
// Original production wcnt transition contract, including load priority.
always @(posedge ck or negedge rn)
 if(!rn)wcnt<=0;
 else if(o3)wcnt<=80;
 else if(sel_fx&&wcnt!=0)wcnt<=wcnt-1'b1;
integer c,phase,checks=0,empty=0,full=0,loads=0,resets=0;
reg[31:0]rng=32'h17291;
initial begin
 for(c=0;c<10000;c=c+1)begin
  @(negedge ck);
  phase=c%500;
  rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
  rn=(phase>1&&phase!=250&&phase!=251);
  o3=(phase==3||phase==200||phase==253)||(phase>350&&rng[8:0]==0);
  sel_fx=(phase>=4&&phase<120)||(phase>=254&&phase<350)||(phase>350&&|rng[1:0]);
  if(phase==4||phase==254)o3=1; // simultaneous load and decrement: load wins.
  if(!rn)resets=resets+1;if(o3)loads=loads+1;
  @(posedge ck);#1;checks=checks+1;
  if(observed!==(wcnt!=0))$fatal(1,"WINDOW_COUNTER_MISMATCH cycle=%0d count=%0d observed=%b",c,wcnt,observed);
  if(wcnt==0)empty=empty+1;if(wcnt==80)full=full+1;
 end
 if(empty<100||full<100||loads<50||resets<20)$fatal(1,"coverage missing");
 $display("WINDOW_COUNTER_PASS checks=%0d empty=%0d full=%0d load_priority=%0d reset=%0d",checks,empty,full,loads,resets);$finish;
end
endmodule
"""
a.out.mkdir(parents=True,exist_ok=False)
(a.out/"positive.v").write_text(v)
(a.out/"mutant.v").write_text(v.replace("wcnt != 7'd1;","wcnt != 7'd2;",1))
(a.out/"tb.sv").write_text(tb)
(a.out/"run.sh").write_text("""#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for k in positive mutant; do
 iverilog -g2012 -s tb -o sim_$k "$k.v" tb.sv >build_$k.log 2>&1
 if vvp sim_$k >run_$k.log 2>&1; then
  [ "$k" = positive ] || { echo MUTANT_SURVIVED;exit 1; }
  grep -q WINDOW_COUNTER_PASS run_$k.log
 else
  [ "$k" = mutant ] || { cat run_$k.log;exit 1; }
  grep -q WINDOW_COUNTER_MISMATCH run_$k.log
 fi
 tail -2 run_$k.log
done
""")
print(a.out)
