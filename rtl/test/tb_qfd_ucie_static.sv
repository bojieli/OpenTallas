`timescale 1ns/1ps
// Actual UCIe P/R parent with nonoverlapping compiler slots: one logical
// record per physical endpoint per edge. No parallel bandwidth is invented.
module tb_qfd_ucie_static;
 parameter MUT=0,N=512;
 localparam PHASE=N+16,LAT=MUT==4?15:14;
 reg clk=0,rst_n=0,epoch_begin=0;
 integer cyc=0,checks=0,bad=0,aborts=0;
 function [545:0] pw(input integer ep,input integer index);
 integer k;begin for(k=0;k<546;k=k+1)pw[k]=((ep*29+index*17+k*13)^(index>>(k%13)))&1;end endfunction
 function [513:0] rw(input integer ep,input integer index);
 integer k;begin for(k=0;k<514;k=k+1)rw[k]=((ep*83+index*37+k*7)^(index>>(k%13)))&1;end endfunction
 reg p_wr=0,p_rd=0,p_ev=0;
 reg [5:0] p_ws=0,p_rs=0,p_es=0;
 wire a_p_tv,b_p_tv,a_p_rv,b_p_rv,a_p_abort,b_p_abort;
 wire [596:0] a_p_tf,b_p_tf;
 wire [545:0] a_p_word,b_p_word;
 wire [7:0] a_p_cause,b_p_cause;
 reg [LAT-1:0] a_p_vp=0,b_p_vp=0;
 reg [LAT*597-1:0] a_p_fp=0,b_p_fp=0;
 always @(posedge clk)begin
 if(!rst_n)begin a_p_vp<=0;b_p_vp<=0;a_p_fp<=0;b_p_fp<=0;end
 else begin
 a_p_vp<={a_p_vp,a_p_tv};b_p_vp<={b_p_vp,b_p_tv};
 a_p_fp<={a_p_fp,a_p_tf ^ ((MUT==1 && a_p_tv)?597'b1:597'b0)};
 b_p_fp<={b_p_fp,b_p_tf};
 end end
 reg r_wr=0,r_rd=0,r_ev=0;
 reg [5:0] r_ws=0,r_rs=0,r_es=0;
 wire a_r_tv,b_r_tv,a_r_rv,b_r_rv,a_r_abort,b_r_abort;
 wire [564:0] a_r_tf,b_r_tf;
 wire [513:0] a_r_word,b_r_word;
 wire [7:0] a_r_cause,b_r_cause;
 reg [LAT-1:0] a_r_vp=0,b_r_vp=0;
 reg [LAT*565-1:0] a_r_fp=0,b_r_fp=0;
 always @(posedge clk)begin
 if(!rst_n)begin a_r_vp<=0;b_r_vp<=0;a_r_fp<=0;b_r_fp<=0;end
 else begin
 a_r_vp<={a_r_vp,a_r_tv};b_r_vp<={b_r_vp,b_r_tv};
 a_r_fp<={a_r_fp,a_r_tf ^ ((MUT==1 && a_r_tv)?565'b1:565'b0)};
 b_r_fp<={b_r_fp,b_r_tf};
 end end
 qfd_io_ucie_static #(.MUT(MUT==3?3:0)) a (.rst_n(rst_n),
.epoch_begin(epoch_begin),
.epoch(8'h3a),
.p_ck(clk),
.p_ckb0(clk),
.p_ckb1(clk),
.p_ckb2(clk),
.p_ckb3(clk),
.p_wr_v(p_wr),
.p_wr_observed_v(p_wr && !(MUT==5 && cyc==8+64+7)),
.p_wr_slot(p_ws),
.p_wr_word(pw(0,(MUT==5 && cyc==8+64+7)?7:cyc-8)),
.p_rd_v(p_rd),
.p_rd_slot(p_rs),
.p_rx_expect_v(p_ev),
.p_rx_expect_slot(p_es),
.p_phy_up(1'b1),
.p_phy_tx_v(a_p_tv),
.p_phy_tx(a_p_tf),
.p_phy_rx_v(b_p_vp[LAT-1]),
.p_phy_rx(b_p_fp[LAT*597-1-:597]),
.p_rx_v(a_p_rv),
.p_rx_word(a_p_word),
.p_epoch_abort(a_p_abort),
.p_fault_cause(a_p_cause),
.r_ck(clk),
.r_ckb0(clk),
.r_ckb1(clk),
.r_ckb2(clk),
.r_ckb3(clk),
.r_wr_v(r_wr),
.r_wr_observed_v(r_wr && !(MUT==5 && cyc==8+PHASE+64+7)),
.r_wr_slot(r_ws),
.r_wr_word(rw(0,(MUT==5 && cyc==8+PHASE+64+7)?7:cyc-8-PHASE)),
.r_rd_v(r_rd),
.r_rd_slot(r_rs),
.r_rx_expect_v(r_ev),
.r_rx_expect_slot(r_es),
.r_phy_up(1'b1),
.r_phy_tx_v(a_r_tv),
.r_phy_tx(a_r_tf),
.r_phy_rx_v(b_r_vp[LAT-1]),
.r_phy_rx(b_r_fp[LAT*565-1-:565]),
.r_rx_v(a_r_rv),
.r_rx_word(a_r_word),
.r_epoch_abort(a_r_abort),
.r_fault_cause(a_r_cause));
 qfd_io_ucie_static #(.MUT(0)) b (.rst_n(rst_n),
.epoch_begin(epoch_begin),
.epoch(8'h3a),
.p_ck(clk),
.p_ckb0(clk),
.p_ckb1(clk),
.p_ckb2(clk),
.p_ckb3(clk),
.p_wr_v(p_wr),
.p_wr_observed_v(p_wr),
.p_wr_slot(p_ws),
.p_wr_word(pw(1,cyc-8-0)),
.p_rd_v(p_rd),
.p_rd_slot(p_rs),
.p_rx_expect_v(p_ev),
.p_rx_expect_slot(p_es),
.p_phy_up(1'b1),
.p_phy_tx_v(b_p_tv),
.p_phy_tx(b_p_tf),
.p_phy_rx_v(a_p_vp[LAT-1]),
.p_phy_rx(a_p_fp[LAT*597-1-:597]),
.p_rx_v(b_p_rv),
.p_rx_word(b_p_word),
.p_epoch_abort(b_p_abort),
.p_fault_cause(b_p_cause),
.r_ck(clk),
.r_ckb0(clk),
.r_ckb1(clk),
.r_ckb2(clk),
.r_ckb3(clk),
.r_wr_v(r_wr),
.r_wr_observed_v(r_wr),
.r_wr_slot(r_ws),
.r_wr_word(rw(1,cyc-8-PHASE)),
.r_rd_v(r_rd),
.r_rd_slot(r_rs),
.r_rx_expect_v(r_ev),
.r_rx_expect_slot(r_es),
.r_phy_up(1'b1),
.r_phy_tx_v(b_r_tv),
.r_phy_tx(b_r_tf),
.r_phy_rx_v(a_r_vp[LAT-1]),
.r_phy_rx(a_r_fp[LAT*565-1-:565]),
.r_rx_v(b_r_rv),
.r_rx_word(b_r_word),
.r_epoch_abort(b_r_abort),
.r_fault_cause(b_r_cause));
initial begin
 for(cyc=0;cyc<PHASE+32+3+14+2+N+20;cyc=cyc+1) begin
 rst_n=cyc>=4;epoch_begin=cyc==6;
 p_wr=cyc>=8 && cyc<8+N;p_ws=6'(cyc-8);
 p_rd=cyc>=32 && cyc<32+N;p_rs=6'(cyc-32);
 p_ev=cyc>=50 && cyc<50+N;p_es=6'(cyc-50);
 r_wr=cyc>=8+PHASE && cyc<8+PHASE+N;r_ws=6'(cyc-8-PHASE);
 r_rd=cyc>=32+PHASE && cyc<32+PHASE+N;r_rs=6'(cyc-32-PHASE);
 r_ev=cyc>=50+PHASE && cyc<50+PHASE+N;r_es=6'(cyc-50-PHASE);
 #5;clk=1;#1;
 if(rst_n)begin
 if(a_p_abort || a_r_abort || b_p_abort || b_r_abort)aborts=aborts+1;
 if(MUT==0 && ({a_p_abort,a_r_abort,b_p_abort,b_r_abort}!==4'b0 ||
 {a_p_cause,a_r_cause,b_p_cause,b_r_cause}!==32'b0))bad=bad+1;
 if(MUT==0 && (a_p_tv && a_r_tv || b_p_tv && b_r_tv))bad=bad+1;
 if(cyc>=51 && cyc<51+N)begin checks=checks+2;
 if(a_p_rv!==1'b1 || a_p_word!==pw(1,cyc-51))bad=bad+1;
 if(b_p_rv!==1'b1 || b_p_word!==pw(0,cyc-51))bad=bad+1;end
 else if(MUT==0 && (a_p_rv!==1'b0 || b_p_rv!==1'b0))bad=bad+1;
 if(cyc>=51+PHASE && cyc<51+PHASE+N)begin checks=checks+2;
 if(a_r_rv!==1'b1 || a_r_word!==rw(1,cyc-51-PHASE))bad=bad+1;
 if(b_r_rv!==1'b1 || b_r_word!==rw(0,cyc-51-PHASE))bad=bad+1;end
 else if(MUT==0 && (a_r_rv!==1'b0 || b_r_rv!==1'b0))bad=bad+1;
 end
 #4;clk=0;
 end
 if(MUT==5 && (a_p_cause!==8'h80 || a_r_cause!==8'h80)) $display("WRONG_MISSING_PRODUCER_CAUSE P%h R%h expected80",a_p_cause,a_r_cause);
 if(bad==0 && aborts==0)$display("STATIC_UCIE_PASS checks%0d words_per_channel512 TX3 RX1 PHY14 zero_simultaneous_subchannel_slots",checks);
 else $display("STATIC_UCIE_FAIL checks%0d errors%0d abort_cycles%0d causesA%h/%h causesB%h/%h MUT%0d",checks,bad,aborts,a_p_cause,a_r_cause,b_p_cause,b_r_cause,MUT);
 $finish;
 end
endmodule
