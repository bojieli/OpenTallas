#!/bin/bash
# Exact old-node composition versus the compact PAD62 node, including pulses and long low/high runs.
set -u
MODE=${1:?mode}; O=${2:?out}
cd "$(dirname "$0")/../.." || exit 2
mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
cp physical/qwen_rst_rep/qfd_rst_rep_p62.sv "$O/dut.sv"
case "$MODE" in
 pass) ;;
 mut) sed -i 's/.PAD(62)/.PAD(62), .MUT(1)/' "$O/dut.sv" ;;
 lat) sed -i 's/.PAD(62)/.PAD(61)/' "$O/dut.sv" ;;
 *) exit 2 ;;
esac
cat > "$O/tb.sv" <<'SV'
`timescale 1ns/1ps
module tb;
 reg clk=0; always #5 clk=~clk;
 reg d=1; wire q0,q1; wire [8:0] refwire;
 assign refwire[0]=d;
 genvar g;
 generate for(g=0;g<6;g=g+1) begin:R8
  qfd_rst_rep_p8 r(.clk(clk),.d(refwire[g]),.q0(refwire[g+1]),.q1());
 end for(g=6;g<8;g=g+1) begin:R0
  qfd_rst_rep r(.clk(clk),.d(refwire[g]),.q0(refwire[g+1]),.q1());
 end endgenerate
 qfd_rst_rep_p62 dut(.clk(clk),.d(d),.q0(q0),.q1(q1));
 reg [127:0] hist=0;
 integer e=0,err=0,checks=0,run=0,seed=32'h62c0;
 always @(posedge clk) begin
  if(e>65) begin
   checks=checks+1;
   if(q0!==hist[63] || q1!==hist[63] || q0!==refwire[8]) begin
    err=err+1;
    if(err<5)$display("RST64_MISMATCH edge%0d q0%0b q1%0b old%0b expected%0b",e,q0,q1,refwire[8],hist[63]);
   end
  end
  hist<={hist[126:0],d};e=e+1;
  if(run==0) begin
   run=1+((($random(seed)&7)==0)?(($random(seed)&32'h7fff)%193):0);
   d<=$random(seed);
  end else run=run-1;
  if(e==20000) begin
   if(err==0)$display("RST64_PASS checks%0d exact64edges old6p8+2p0 q0/q1 assert/deassert",checks);
   else $display("RST64_FAIL errors%0d checks%0d",err,checks);
   $finish;
  end
 end
endmodule
SV
verilator --binary --timing --build-jobs 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb -Mdir "$O/obj" "$O/tb.sv" "$O/dut.sv" physical/qwen_rst_rep/qfd_rst_rep_masters.sv rtl/qwen_sys/reset_tree_20261013/ot_qwen_rst_rep.sv > "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; exit 2; }
"$O/obj/Vtb" | tee "$O/run.log"
grep -q RST64_PASS "$O/run.log"
