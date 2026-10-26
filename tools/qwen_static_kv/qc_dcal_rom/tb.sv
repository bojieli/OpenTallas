`timescale 1ns/1ps
module tb;
  `include "profile_params.svh"
  reg ck=0,rst_n=0,reload=0,epoch_go=0,halt=0;
  wire [52:0] gold,dut,mutant;
  ot_qwen_d2d_cal_seq #(.NL(1),.TX_IMG(IMAGE_TX),.RX_IMG(IMAGE_RX),.TX_SEG1(SEG_TX),.RX_SEG1(SEG_RX),
    .ADM(1),.TX_SEG2(32'd16),.RX_SEG2(32'd16),.ADM_OFS(72),.ADM_LEN(1100),.AUTO(0),.EP_SKEW(0)) g (
    .ck(ck),.rst_n(rst_n),.reload(reload),.tok_go(1'b0),.epoch_go(epoch_go),.halt(halt),
    .cfg_tx_we(gold[0]),.cfg_rx_we(gold[1]),.cfg_addr(gold[7:2]),.cfg_data(gold[39:8]),
    .cal_start(gold[40]),.cal_seg(gold[41]),.cal_ready(gold[42]),.running(gold[43]),
    .adm_done(gold[44]),.tok_start(gold[45]),.fault(gold[46]),.layer(gold[52:47]));
  ot_qwen_d2d_cal_seq_image64 #(.IMAGE_VIAMAP("profile.viamap.hex"),.NL(1),.TX_SEG1(SEG_TX),.RX_SEG1(SEG_RX),
    .ADM(1),.TX_SEG2(32'd16),.RX_SEG2(32'd16),.ADM_OFS(72),.ADM_LEN(1100),.AUTO(0),.EP_SKEW(0)) d (
    .ck(ck),.rst_n(rst_n),.reload(reload),.tok_go(1'b0),.epoch_go(epoch_go),.halt(halt),
    .cfg_tx_we(dut[0]),.cfg_rx_we(dut[1]),.cfg_addr(dut[7:2]),.cfg_data(dut[39:8]),
    .cal_start(dut[40]),.cal_seg(dut[41]),.cal_ready(dut[42]),.running(dut[43]),
    .adm_done(dut[44]),.tok_start(dut[45]),.fault(dut[46]),.layer(dut[52:47]));
  ot_qwen_d2d_cal_seq_image64 #(.IMAGE_VIAMAP("mutant.viamap.hex"),.NL(1),.TX_SEG1(SEG_TX),.RX_SEG1(SEG_RX),
    .ADM(1),.TX_SEG2(32'd16),.RX_SEG2(32'd16),.ADM_OFS(72),.ADM_LEN(1100),.AUTO(0),.EP_SKEW(0)) m (
    .ck(ck),.rst_n(rst_n),.reload(reload),.tok_go(1'b0),.epoch_go(epoch_go),.halt(halt),
    .cfg_tx_we(mutant[0]),.cfg_rx_we(mutant[1]),.cfg_addr(mutant[7:2]),.cfg_data(mutant[39:8]),
    .cal_start(mutant[40]),.cal_seg(mutant[41]),.cal_ready(mutant[42]),.running(mutant[43]),
    .adm_done(mutant[44]),.tok_start(mutant[45]),.fault(mutant[46]),.layer(mutant[52:47]));
  integer cyc=0,bad=0,mutant_bad=0,seed=29,starts=0,ready_g=-1,ready_d=-1;
  reg [31:0] tx_seen=0,rx_seen=0;
  always #1 ck=~ck;
  always @(negedge ck) begin
    cyc=cyc+1;
    if (cyc>8 && gold!==dut) begin
      bad=bad+1;if(bad<8)$display("MISMATCH cycle=%0d gold=%h dut=%h ip=%0d addr=%0d image=%h",cyc,gold,dut,d.ip,d.image_addr,d.image_q);
    end
    if(cyc>8 && gold!==mutant)mutant_bad=mutant_bad+1;
    if(gold[0] && !gold[7])tx_seen[gold[6:2]]=1;
    if(gold[1] && !gold[7])rx_seen[gold[6:2]]=1;
    if(gold[40])starts=starts+1;
    if(ready_g<0&&gold[42])ready_g=cyc;
    if(ready_d<0&&dut[42])ready_d=cyc;
    if(cyc<10000) begin
      rst_n<=cyc>=3;epoch_go<=cyc>=120&&cyc<123;reload<=0;halt<=0;
    end else begin
      rst_n<=!(($random(seed)&8191)==0);
      epoch_go<=(($random(seed)&2047)==0)?1:(epoch_go&&(($random(seed)&7)!=0));
      reload<=(($random(seed)&511)==0);halt<=(($random(seed)&4095)==0);
    end
    if(cyc==1500000)begin
      $display("RESULT cycles=%0d mismatches=%0d mutant_mismatches=%0d cal_starts=%0d tx_rows=%h rx_rows=%h ready_gold=%0d ready_dut=%0d",cyc,bad,mutant_bad,starts,tx_seen,rx_seen,ready_g,ready_d);
      if(bad||!mutant_bad||tx_seen!==32'hffffffff||rx_seen!==32'hffffffff||ready_g!=ready_d)$fatal(1,"QC live image ROM exactness failure");
      $finish;
    end
  end
endmodule
