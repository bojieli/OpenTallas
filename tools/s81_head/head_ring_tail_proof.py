#!/usr/bin/env python3
"""Emit bounded arbitrary-tail write/read ring lockstep and mechanism mutants."""
from pathlib import Path
import argparse,re
a=argparse.ArgumentParser();a.add_argument('--baseline',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args()
r=p.out;r.mkdir(parents=True,exist_ok=False)
src=Path(__file__).resolve().parents[2]/'rtl/common'
old=p.baseline.read_text()
oldring=re.search(r'module ot_meso_ring_ca\b.*?endmodule',old,re.S).group(0).replace('module ot_meso_ring_ca','module old_ring',1)
(r/'old_ring.sv').write_text(oldring)
new=(src/'ot_dp_clk_landing_ca.sv').read_text();(r/'new.sv').write_text(new)
(r/'fifo.sv').write_bytes((src/'ot_meso_fifo.sv').read_bytes())
badw=new.replace('if (wen[wi * WNC + wc])','if (wen[wi * WNC + wc] && (!WRITE_TAIL || !(wi == 0 && wc == WNC-1)))')
badr=new.replace('.place(RP0[AW-1:0]), .sd(sd_c)',".place(RP0[AW-1:0] + AW'(READ_CHUNK > 0)), .sd(sd_c)")
assert badw!=new and badr!=new
(r/'mut_write.sv').write_text(badw);(r/'mut_read.sv').write_text(badr)
tb=r"""module one #(parameter W=515,WR=1,TAIL=1,RCH=32,PH=2,CONSTTAIL=0)(output reg done=0);
reg tc=0,rc=0;always #5 tc=~tc;
initial begin #(PH);forever #5 rc=~rc;end
reg tr=0,rr=0;reg[5:0]ks=2;reg[W-1:0]d=0;
wire[W-1:0]a,b;wire av,bv,al,bl,ag,bg,ah,bh;integer n=0,j,cnt=0;reg[31:0]rng=32'h12345678+W+PH+WR;
old_ring #(.W(W),.WREG(WR),.WRITE_CHUNK(8)) gold(.tclk(tc),.wen_clk(tc),.t_rst_n(tr),.t_d(d),.rclk(rc),.r_rst_n(rr),.k_s(ks),.r_d(a),.r_v(av),.r_lap_ok(al),.r_glo_ok(ag),.r_ghi_ok(ah));
ot_meso_ring_ca #(.W(W),.WREG(WR),.WRITE_CHUNK(8),.WRITE_TAIL(TAIL),.READ_CHUNK(RCH)) dut(.tclk(tc),.wen_clk(tc),.t_rst_n(tr),.t_d(d),.rclk(rc),.r_rst_n(rr),.k_s(ks),.r_d(b),.r_v(bv),.r_lap_ok(bl),.r_glo_ok(bg),.r_ghi_ok(bh));
initial begin
 for(n=0;n<4000;n=n+1)begin
  @(negedge tc);
  tr=(n%257)>8;rr=(n%257)>15;
  if(!tr)ks=6'(2+(n/257)%3);
  for(j=0;j<W;j=j+1)begin
   rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);d[j]=rng[0];
  end
  if(CONSTTAIL) for(j=0;j<3 && j<W;j=j+1) d[W-1-j]=0;
 end
 done=1;
 $display("CASE PASS W=%0d WR=%0d TAIL=%0d RCH=%0d PH=%0d CONST=%0d checks=%0d",W,WR,TAIL,RCH,PH,CONSTTAIL,cnt);
end
always @(posedge rc)begin
 #1;
 if(n>64 && !done)begin
  if({a,av,al,ag,ah}!=={b,bv,bl,bg,bh})$fatal(1,"tail lockstep W=%0d WR=%0d TAIL=%0d RCH=%0d PH=%0d n=%0d",W,WR,TAIL,RCH,PH,n);
  cnt=cnt+1;
 end
end
endmodule
module tb;
wire[23:0]done;
"""
widths=[1,31,32,33,64,65,515,517]
for i,w in enumerate(widths):
 for k,(wr,tail,rch,ph,const) in enumerate([(0,0,0,0,0),(1,1,32,2,0),(1,1,32,4,1)]):
  idx=i*3+k;tb+=f'one #(.W({w}),.WR({wr}),.TAIL({tail}),.RCH({rch}),.PH({ph}),.CONSTTAIL({const})) c{idx}(done[{idx}]);\n'
tb+='initial begin wait(&done);$display("PASS tail chunk default-off, writer-tail/read32, all24 cases");$finish;end\ninitial begin #1000000;$fatal(1,"watchdog");end\nendmodule\n'
(r/'tb.sv').write_text(tb)
(r/'run.sh').write_text("""#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for mode in positive write read;do
 src=new.sv;[ "$mode" = positive ] || src=mut_$mode.sv
 iverilog -g2012 -s tb -o sim_$mode old_ring.sv "$src" fifo.sv tb.sv > build_$mode.log 2>&1
 if vvp sim_$mode > run_$mode.log 2>&1;then
  test "$mode" = positive || { echo "MUTANT SURVIVED $mode";exit 1; }
  grep -q 'PASS tail chunk' run_$mode.log
 else
  test "$mode" != positive || { cat run_$mode.log;exit 1; }
  grep -q 'FATAL:' run_$mode.log
 fi
 tail -3 run_$mode.log
done
""")
print(r)
