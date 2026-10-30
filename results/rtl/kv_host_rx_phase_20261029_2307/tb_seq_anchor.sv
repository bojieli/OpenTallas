`timescale 1ns/1ps
module tb_seq_anchor;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0,ep=0,btx=0,brx=0;reg[31:0]bd=0;reg[4:0]fw=0;
always @(posedge ck) fw<={fw,ep};
wire kcs,ccs; wire kf,cf; integer cyc=0,kcy=-1,ccy=-1;
always @(posedge ck)begin
 cyc<=cyc+1;
 if(kcs&&kcy<0)begin kcy=cyc;$display("ANCHOR K cal %0d",cyc);end
 if(ccs&&ccy<0)begin ccy=cyc;$display("ANCHOR C cal %0d",cyc);end
end
qkd_d2d_cal_seq_pin_bc4 #(.VIAMAP("/srv/opentallas-scratch2/claude/tok-kv-4-1029/dcal_h153/kv_dcal_r0_c0.viamap.hex"),.EP_SKEW(3)) k(
 .ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(ep),.halt(1'b0),.bcfg_tx_we(btx),.bcfg_rx_we(brx),.bcfg_addr(6'd32),.bcfg_data(bd),
 .cfg_tx_we(),.cfg_rx_we(),.cfg_addr(),.cfg_data(),.cal_start(kcs),.cal_seg(),.cal_ready(),.running(),.layer(),.adm_done(),.tok_start(),.fault(kf));
ot_qwen_d2d_cal_seq #(.ADM(1),.AUTO(1),.ADM_OFS(72),.ADM_LEN(1253),.FIRST_OFS(1329),.PERIOD(293376),.TX_SEG2(10),.RX_SEG2(11),.EP_SKEW(0)) c(
 .ck(ck),.rst_n(rst_n),.reload(1'b0),.tok_go(1'b0),.epoch_go(fw[4]),.halt(1'b0),
 .cfg_tx_we(),.cfg_rx_we(),.cfg_addr(),.cfg_data(),.cal_start(ccs),.cal_seg(),.cal_ready(),.running(),.layer(),.adm_done(),.tok_start(),.fault(cf));
initial begin
 repeat(5) @(negedge ck);rst_n=1;
 repeat(100) @(negedge ck);
 btx=1;bd=10;@(negedge ck);btx=0;brx=1;bd=11;@(negedge ck);brx=0;
 repeat(20) @(negedge ck);ep=1;@(negedge ck);ep=0;
 repeat(120) @(negedge ck);
 if(kcy<0||ccy<0||kf||cf) $fatal(1,"anchor missing/fault K%0d C%0d f%b%b",kcy,ccy,kf,cf);
 $display("ANCHOR_DELTA CminusK %0d K%0d C%0d",ccy-kcy,kcy,ccy);$finish;
end
endmodule
