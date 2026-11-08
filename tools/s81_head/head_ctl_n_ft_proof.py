#!/usr/bin/env python3
"""Native FT data+epoch +1 output-cycle proof, plus bounded chunk placement keys."""
from pathlib import Path
import argparse,re
p=argparse.ArgumentParser();p.add_argument('--cells',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=a.out;r.mkdir(parents=True,exist_ok=False)
(r/'cells.sv').write_text(re.search(r'module ot_dp_st\b.*?endmodule',a.cells.read_text(),re.S).group(0))
root=Path(__file__).resolve().parents[2]
s=(root/'tools/die_plan/landing_placement.tcl').read_text()
keys='\n'.join(re.search(r'proc '+n+r'\b.*?\n}',s,re.S).group(0) for n in ['cland_ffkey','cland_kbit','cland_ctl_rekey'])
keys+=r"""
proc must {v msg} {if {!$v} {error $msg}}
set n {u_cland_w3d_i/u_ring.dch[16].u_dsel/di[0]}
set k [cland_ffkey $n 0 32 513 8 32 1]
must [expr {[lindex [split $k |] 1] eq "000000512"}] read_tail_bit
must [expr {[lindex [split $k |] 2] eq "999999970"}] read_tail_protected
set legacy [cland_ffkey $n 0 32 513 8 32 0]
must [expr {$legacy eq $n}] legacy_unchanged
set moved [cland_ctl_rekey [list [list $k dummy]] u_cland_w3d_i/u_ring.s_d 3 513 0]
must [expr {[lindex $moved 0] == 0}] protected_selector_rekey
set legacy_moved [cland_ctl_rekey [list [list $legacy dummy]] u_cland_w3d_i/u_ring.s_d 3 513 0]
must [expr {[lindex $legacy_moved 0] == 1}] legacy_mutant_detected
set wn {u_cland_w3d_i/u_ring.g_wreg.sl[3].ch[64].u_wen/q}
set wk [cland_ffkey $wn 0 32 513 8 32 1]
must [expr {[lindex [split $wk |] 1] eq "000000512"}] writer_tail_bit
set wlegacy [cland_ffkey $wn 0 32 513 8 32 0]
must [expr {$wlegacy eq $wn}] legacy_writer_unchanged
puts "PASS bounded-tail placement keys + legacy key mutant"
"""
(r/'keys.tcl').write_text(keys)
tb=r"""module ft_chain #(parameter W=514,N=5,OLD=5,ISNEW=0)(input clk,input[OLD-1:0]rn,input[W-1:0]d,input ea,output[W-1:0]q,output eq);
wire[W-1:0]v[0:N];wire[N:0]e;assign v[0]=d;assign e[0]=ea;
for(genvar j=0;j<N;j++)begin:st
 localparam RI=j<OLD?j:OLD-1;
 wire[W-1:0]din;
 wire ein;
`ifdef CTLN_MUTANT_DATA
 assign din=ISNEW && j==N-1 ? v[j-1]:v[j];
`else
 assign din=v[j];
`endif
`ifdef CTLN_MUTANT_EPOCH
 assign ein=ISNEW && j==N-1 ? e[j-1]:e[j];
`else
 assign ein=e[j];
`endif
 ot_dp_st #(.W(W))u(clk,rn[RI],din,ein,v[j+1],e[j+1]);
end
assign q=v[N];assign eq=e[N];
endmodule
module one #(parameter W=514,N=5)(output reg done=0);
reg clk=0;always #5 clk=~clk;reg[N-1:0]rn=0;reg[W-1:0]d=0,salt=0;reg ea=0;
wire[W-1:0]a,b;wire ae,be;reg[W-1:0]prev;reg pe=0;
integer n=0,j,checks=0;localparam TW=W<32?W:32;
ft_chain #(.W(W),.N(N),.OLD(N))old_i(clk,rn,d,ea,a,ae);
ft_chain #(.W(W),.N(N+1),.OLD(N),.ISNEW(1))new_i(clk,rn,d,ea,b,be);
initial begin
 for(j=0;j<W;j=j+1)salt[j]=((j*17+j/3)%23)<11;
 for(n=0;n<4000;n=n+1)begin
  @(negedge clk); d={((W+31)/32){$urandom}}^salt;d[TW-1:0]=TW'(n);
  ea=(n%101)>8;
  for(j=0;j<N;j=j+1)rn[j]=(n%257)>(8+j%4);
 end
 done=1;$display("FT_PIN_EQ W=%0d stages=%0d->%0d fullword_tag_epoch checks=%0d PASS",W,N,N+1,checks);
end
always @(posedge clk)begin
 #1;
 if(n>N+5 && !done)begin
  if(b!==prev || be!==(rn[N-1]?pe:1'b0))$fatal(1,"FT added-cycle data/epoch W=%0d n=%0d",W,n);
  checks=checks+1;
 end
 prev=a;pe=ae;
end
endmodule
module tb;wire[2:0]done;
one #(.W(514),.N(5))a(done[0]);one #(.W(512),.N(5))b(done[1]);one #(.W(45),.N(1))c(done[2]);
initial begin wait(&done);$display("PASS all FT +1 output PIN including reset cancellation");$finish;end
initial begin #1000000;$fatal(1,"watchdog");end
endmodule
"""
(r/'tb.sv').write_text(tb)
(r/'run.sh').write_text("""#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tclsh keys.tcl > keys.log 2>&1
cat keys.log
for mode in positive data epoch;do
 def=;[ "$mode" = positive ] || def="-DCTLN_MUTANT_${mode^^}"
 iverilog -g2012 -s tb $def -o sim_$mode cells.sv tb.sv > build_$mode.log 2>&1
 if vvp sim_$mode > run_$mode.log 2>&1;then
  test "$mode" = positive || { echo MUTANT_SURVIVED;exit 1; }
  grep -q 'PASS all FT' run_$mode.log
 else
  test "$mode" != positive || { cat run_$mode.log;exit 1; }
  grep -q FATAL run_$mode.log
 fi
 tail -4 run_$mode.log
done
""")
print(r)
