`timescale 1ns/1ps
module tb; reg clk=0; always #5 clk=~clk; integer checks=0,bad=0,mutant_bad=0;
reg [0:0] rst_n=0;
reg [1:0] sid=0;
reg [0:0] dir=0;
reg [0:0] tx_enable=0;
reg [2:0] tx_source=0;
reg [2223:0] l_in=0;
reg [289:0] pi=0;
reg [2207:0] eg=0;
reg [7:0] xq_done=0;
reg [265:0] ri=0;
reg [2:0] wki=0;
reg [0:0] ack_i=0;
wire [2223:0] gold_l_out;
wire [2207:0] gold_xq;
wire [287:0] gold_rce;
wire [2:0] gold_wko;
wire [263:0] gold_cco;
wire [0:0] gold_ack_o;
wire [0:0] gold_mirror_busy;
wire [0:0] gold_fault;
wire [2223:0] dut_l_out;
wire [2207:0] dut_xq;
wire [287:0] dut_rce;
wire [2:0] dut_wko;
wire [263:0] dut_cco;
wire [0:0] dut_ack_o;
wire [0:0] dut_mirror_busy;
wire [0:0] dut_fault;
wire [2223:0] mut_l_out;
wire [2207:0] mut_xq;
wire [287:0] mut_rce;
wire [2:0] mut_wko;
wire [263:0] mut_cco;
wire [0:0] mut_ack_o;
wire [0:0] mut_mirror_busy;
wire [0:0] mut_fault;
ot_vms_rstop_static_reference u_gold (.clk(clk),.rst_n(rst_n),.sid(sid),.dir(dir),.tx_enable(tx_enable),.tx_source(tx_source),.l_in(l_in),.pi(pi),.eg(eg),.xq_done(xq_done),.ri(ri),.wki(wki),.ack_i(ack_i),.l_out(gold_l_out),.xq(gold_xq),.rce(gold_rce),.wko(gold_wko),.cco(gold_cco),.ack_o(gold_ack_o),.mirror_busy(gold_mirror_busy),.fault(gold_fault));
ot_vms_rstop_static #(.LOCAL_CTRL_REPLICAS(1)) u_dut (.clk(clk),.rst_n(rst_n),.sid(sid),.dir(dir),.tx_enable(tx_enable),.tx_source(tx_source),.l_in(l_in),.pi(pi),.eg(eg),.xq_done(xq_done),.ri(ri),.wki(wki),.ack_i(ack_i),.l_out(dut_l_out),.xq(dut_xq),.rce(dut_rce),.wko(dut_wko),.cco(dut_cco),.ack_o(dut_ack_o),.mirror_busy(dut_mirror_busy),.fault(dut_fault));
ot_vms_rstop_static_mut #(.LOCAL_CTRL_REPLICAS(1)) u_mut (.clk(clk),.rst_n(rst_n),.sid(sid),.dir(dir),.tx_enable(tx_enable),.tx_source(tx_source),.l_in(l_in),.pi(pi),.eg(eg),.xq_done(xq_done),.ri(ri),.wki(wki),.ack_i(ack_i),.l_out(mut_l_out),.xq(mut_xq),.rce(mut_rce),.wko(mut_wko),.cco(mut_cco),.ack_o(mut_ack_o),.mirror_busy(mut_mirror_busy),.fault(mut_fault));
initial begin
repeat(3) @(negedge clk); rst_n=1;
for(integer c=0;c<5000;c=c+1) begin
@(negedge clk);
sid=$random;
dir=$random;
tx_enable=$random;
tx_source=$random;
for(integer k=0;k<2224;k=k+32) l_in[k+:32]=$random;
for(integer k=0;k<290;k=k+32) pi[k+:32]=$random;
for(integer k=0;k<2208;k=k+32) eg[k+:32]=$random;
xq_done=$random;
for(integer k=0;k<266;k=k+32) ri[k+:32]=$random;
wki=$random;
ack_i=$random;
tx_source=c%8; rst_n=(c%127!=0);
@(posedge clk); #1; checks=checks+1;
if({gold_l_out,gold_xq,gold_rce,gold_wko,gold_cco,gold_ack_o,gold_mirror_busy,gold_fault} !== {dut_l_out,dut_xq,dut_rce,dut_wko,dut_cco,dut_ack_o,dut_mirror_busy,dut_fault}) begin bad=bad+1; if(bad<4) $display("MISMATCH %0d",c); end
if({gold_l_out,gold_xq,gold_rce,gold_wko,gold_cco,gold_ack_o,gold_mirror_busy,gold_fault} !== {mut_l_out,mut_xq,mut_rce,mut_wko,mut_cco,mut_ack_o,mut_mirror_busy,mut_fault}) mutant_bad=mutant_bad+1;
end
$display("GLUE039_RING checks=%0d mismatches=%0d mutant=%0d",checks,bad,mutant_bad);
if(bad || !mutant_bad) $fatal(1,"ring locality failed"); $finish; end endmodule
