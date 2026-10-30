`timescale 1ns/1ps
module tb;
reg ck=0;always #1 ck=~ck;
integer cyc=0,cmp=0,mut_diffs=0,rx_words=0,tx_words=0;
integer crx=4,ctx=4;
reg[3:0] ret_rx=0,ret_tx=0;
wire [0:0] gold_u_rx__i_cr;
wire [0:0] dut_u_rx__i_cr;
wire [0:0] mut_u_rx__i_cr;
reg [545:0] u_rx__i_d=0;
reg [0:0] u_rx__i_v=0;
reg [0:0] u_rx__o_cr=0;
wire [527:0] gold_u_rx__o_d;
wire [527:0] dut_u_rx__o_d;
wire [527:0] mut_u_rx__o_d;
wire [0:0] gold_u_rx__o_v;
wire [0:0] dut_u_rx__o_v;
wire [0:0] mut_u_rx__o_v;
wire [0:0] gold_u_rx__r_fault;
wire [0:0] dut_u_rx__r_fault;
wire [0:0] mut_u_rx__r_fault;
reg [0:0] u_rx__rrst_n=0;
wire [0:0] gold_u_rx__w_fault;
wire [0:0] dut_u_rx__w_fault;
wire [0:0] mut_u_rx__w_fault;
reg [0:0] u_rx__wrst_n=0;
wire [0:0] gold_u_tx__i_cr;
wire [0:0] dut_u_tx__i_cr;
wire [0:0] mut_u_tx__i_cr;
reg [527:0] u_tx__i_d=0;
reg [0:0] u_tx__i_v=0;
reg [0:0] u_tx__o_cr=0;
wire [545:0] gold_u_tx__o_d;
wire [527:0] dut_u_tx__o_d;
wire [527:0] mut_u_tx__o_d;
wire [0:0] gold_u_tx__o_v;
wire [0:0] dut_u_tx__o_v;
wire [0:0] mut_u_tx__o_v;
wire [0:0] gold_u_tx__r_fault;
wire [0:0] dut_u_tx__r_fault;
wire [0:0] mut_u_tx__r_fault;
reg [0:0] u_tx__rrst_n=0;
wire [0:0] gold_u_tx__w_fault;
wire [0:0] dut_u_tx__w_fault;
wire [0:0] mut_u_tx__w_fault;
reg [0:0] u_tx__wrst_n=0;
qkd_hr_cdc_pc gold(.ck(ck),
.u_rx__i_cr(gold_u_rx__i_cr),
.u_rx__i_d(u_rx__i_d),
.u_rx__i_v(u_rx__i_v),
.u_rx__o_cr(u_rx__o_cr),
.u_rx__o_d(gold_u_rx__o_d),
.u_rx__o_v(gold_u_rx__o_v),
.u_rx__r_fault(gold_u_rx__r_fault),
.u_rx__rrst_n(u_rx__rrst_n),
.u_rx__w_fault(gold_u_rx__w_fault),
.u_rx__wrst_n(u_rx__wrst_n),
.u_tx__i_cr(gold_u_tx__i_cr),
.u_tx__i_d(u_tx__i_d),
.u_tx__i_v(u_tx__i_v),
.u_tx__o_cr(u_tx__o_cr),
.u_tx__o_d(gold_u_tx__o_d),
.u_tx__o_v(gold_u_tx__o_v),
.u_tx__r_fault(gold_u_tx__r_fault),
.u_tx__rrst_n(u_tx__rrst_n),
.u_tx__w_fault(gold_u_tx__w_fault),
.u_tx__wrst_n(u_tx__wrst_n));
qkd_hr_cdc_pc_projected dut(.ck(ck),
.u_rx__i_cr(dut_u_rx__i_cr),
.u_rx__i_d(u_rx__i_d),
.u_rx__i_v(u_rx__i_v),
.u_rx__o_cr(u_rx__o_cr),
.u_rx__o_d(dut_u_rx__o_d),
.u_rx__o_v(dut_u_rx__o_v),
.u_rx__r_fault(dut_u_rx__r_fault),
.u_rx__rrst_n(u_rx__rrst_n),
.u_rx__w_fault(dut_u_rx__w_fault),
.u_rx__wrst_n(u_rx__wrst_n),
.u_tx__i_cr(dut_u_tx__i_cr),
.u_tx__i_d(u_tx__i_d),
.u_tx__i_v(u_tx__i_v),
.u_tx__o_cr(u_tx__o_cr),
.u_tx__o_d(dut_u_tx__o_d),
.u_tx__o_v(dut_u_tx__o_v),
.u_tx__r_fault(dut_u_tx__r_fault),
.u_tx__rrst_n(u_tx__rrst_n),
.u_tx__w_fault(dut_u_tx__w_fault),
.u_tx__wrst_n(u_tx__wrst_n));
qkd_hr_cdc_pc_mutant mut(.ck(ck),
.u_rx__i_cr(mut_u_rx__i_cr),
.u_rx__i_d(u_rx__i_d),
.u_rx__i_v(u_rx__i_v),
.u_rx__o_cr(u_rx__o_cr),
.u_rx__o_d(mut_u_rx__o_d),
.u_rx__o_v(mut_u_rx__o_v),
.u_rx__r_fault(mut_u_rx__r_fault),
.u_rx__rrst_n(u_rx__rrst_n),
.u_rx__w_fault(mut_u_rx__w_fault),
.u_rx__wrst_n(u_rx__wrst_n),
.u_tx__i_cr(mut_u_tx__i_cr),
.u_tx__i_d(u_tx__i_d),
.u_tx__i_v(u_tx__i_v),
.u_tx__o_cr(u_tx__o_cr),
.u_tx__o_d(mut_u_tx__o_d),
.u_tx__o_v(mut_u_tx__o_v),
.u_tx__r_fault(mut_u_tx__r_fault),
.u_tx__rrst_n(u_tx__rrst_n),
.u_tx__w_fault(mut_u_tx__w_fault),
.u_tx__wrst_n(u_tx__wrst_n));
always @(posedge ck) ret_rx <= {ret_rx[2:0],gold_u_rx__o_v};
always @(posedge ck) ret_tx <= {ret_tx[2:0],gold_u_tx__o_v};
always @(negedge ck)begin
cyc=cyc+1;
if(cyc==20)begin u_rx__rrst_n=1;u_rx__wrst_n=1;u_tx__rrst_n=1;u_tx__wrst_n=1;end
if(cyc>35)begin
cmp=cmp+1;
if(gold_u_rx__i_cr!==dut_u_rx__i_cr)$fatal(1,"projection u_rx__i_cr cyc%0d",cyc);
if(gold_u_rx__o_d!==dut_u_rx__o_d)$fatal(1,"projection u_rx__o_d cyc%0d",cyc);
if(gold_u_rx__o_v!==dut_u_rx__o_v)$fatal(1,"projection u_rx__o_v cyc%0d",cyc);
if(gold_u_rx__r_fault!==dut_u_rx__r_fault)$fatal(1,"projection u_rx__r_fault cyc%0d",cyc);
if(gold_u_rx__w_fault!==dut_u_rx__w_fault)$fatal(1,"projection u_rx__w_fault cyc%0d",cyc);
if(gold_u_tx__i_cr!==dut_u_tx__i_cr)$fatal(1,"projection u_tx__i_cr cyc%0d",cyc);
if(gold_u_tx__o_d[527:0]!==dut_u_tx__o_d)$fatal(1,"projection u_tx__o_d cyc%0d",cyc);
if(gold_u_tx__o_v!==dut_u_tx__o_v)$fatal(1,"projection u_tx__o_v cyc%0d",cyc);
if(gold_u_tx__r_fault!==dut_u_tx__r_fault)$fatal(1,"projection u_tx__r_fault cyc%0d",cyc);
if(gold_u_tx__w_fault!==dut_u_tx__w_fault)$fatal(1,"projection u_tx__w_fault cyc%0d",cyc);
if(gold_u_tx__o_v)begin tx_words=tx_words+1;if(gold_u_tx__o_d[545:528]!==18'b0)$fatal(1,"reserved nonzero cyc%0d",cyc);if(gold_u_tx__o_d[527:0]!==mut_u_tx__o_d)mut_diffs=mut_diffs+1;end
if(gold_u_rx__o_v)rx_words=rx_words+1;
if(gold_u_rx__w_fault||gold_u_rx__r_fault||gold_u_tx__w_fault||gold_u_tx__r_fault)$fatal(1,"illegal trace fault cyc%0d",cyc);
end
if(cyc>40)begin
crx=crx+gold_u_rx__i_cr;ctx=ctx+gold_u_tx__i_cr;
u_rx__i_v=(crx>0&&cyc<1500&&(cyc%5!=0));u_tx__i_v=(ctx>0&&cyc<1500&&(cyc%7!=0));
if(u_rx__i_v)crx=crx-1;if(u_tx__i_v)ctx=ctx-1;
u_rx__i_d={17{32'(cyc*137+329)}};u_tx__i_d={17{32'(cyc*181+437)}};
u_rx__o_cr=ret_rx[1];u_tx__o_cr=ret_tx[1];
end
if(cyc==1800)begin
if(rx_words<50||tx_words<50||mut_diffs<50)$fatal(1,"weak coupon rx%0d tx%0d mut%0d",rx_words,tx_words,mut_diffs);
$display("CDCPC_PROJECTION_PASS cmp=%0d rx_words=%0d tx_words=%0d reserved18_valid_zero=%0d mutant_valid_diffs=%0d added_cycles=0",cmp,rx_words,tx_words,tx_words,mut_diffs);$finish;
end
end
endmodule
