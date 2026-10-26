`timescale 1ns/1ps
module tb;
  reg ck=0, rst_n=0, reload=0, epoch_go=0, halt=0, btx=0, brx=0;
  reg [5:0] ba=0;
  reg [31:0] bd=0;
  wire [52:0] gold, dut, mutant;
  qkd_d2d_cal_seq_pin_bc4 g(.ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
    .bcfg_tx_we(btx),.bcfg_rx_we(brx),.bcfg_addr(ba),.bcfg_data(bd),
    .cfg_tx_we(gold[0]),.cfg_rx_we(gold[1]),.cfg_addr(gold[7:2]),.cfg_data(gold[39:8]),
    .cal_start(gold[40]),.cal_seg(gold[41]),.cal_ready(gold[42]),.running(gold[43]),
    .adm_done(gold[44]),.tok_start(gold[45]),.fault(gold[46]),.layer(gold[52:47]));
  qkd_d2d_cal_seq_pin_rom64 #(.VIAMAP("profile.viamap.hex")) d(.ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
    .bcfg_tx_we(btx),.bcfg_rx_we(brx),.bcfg_addr(ba),.bcfg_data(bd),
    .cfg_tx_we(dut[0]),.cfg_rx_we(dut[1]),.cfg_addr(dut[7:2]),.cfg_data(dut[39:8]),
    .cal_start(dut[40]),.cal_seg(dut[41]),.cal_ready(dut[42]),.running(dut[43]),
    .adm_done(dut[44]),.tok_start(dut[45]),.fault(dut[46]),.layer(dut[52:47]));
  qkd_d2d_cal_seq_pin_rom64 #(.VIAMAP("mutant.viamap.hex")) m(.ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),
    .bcfg_tx_we(btx),.bcfg_rx_we(brx),.bcfg_addr(ba),.bcfg_data(bd),
    .cfg_tx_we(mutant[0]),.cfg_rx_we(mutant[1]),.cfg_addr(mutant[7:2]),.cfg_data(mutant[39:8]),
    .cal_start(mutant[40]),.cal_seg(mutant[41]),.cal_ready(mutant[42]),.running(mutant[43]),
    .adm_done(mutant[44]),.tok_start(mutant[45]),.fault(mutant[46]),.layer(mutant[52:47]));
  integer cyc=0, bad=0, mutant_bad=0, seed=17, starts=0, tok=0, ready_g=-1, ready_d=-1, ph;
  reg [35:0] layers_seen=0;
  always #1 ck=~ck;
  always @(negedge ck) begin
    cyc=cyc+1;
    if (cyc>8 && gold !== dut) begin
      bad=bad+1;
      if (bad<8) $display("MISMATCH cycle=%0d gold=%h dut=%h li=%0d addr=%0d rd=%h phase=%0d",cyc,gold,dut,d.profile_li,d.profile_addr,d.profile_data,d.profile_phase);
    end
    if (cyc>8 && gold !== mutant) mutant_bad=mutant_bad+1;
    if (ready_g<0 && gold[42]) ready_g=cyc;
    if (ready_d<0 && dut[42]) ready_d=cyc;
    if (gold[40]) begin
      starts=starts+1;
      if (gold[52:47]<36) layers_seen[gold[52:47]]=1;
    end
    if (gold[45]) tok=tok+1;
    if (cyc<700000) begin
      rst_n <= cyc>=3;
      epoch_go <= cyc>=120 && cyc<123;
      reload<=0; halt<=0; btx<=0; brx<=0;
      // Boot words precede epoch admission; values come from the same profile.
      if (cyc==90) begin btx<=1;ba<=32;bd<=`TX_SEG2;end
      if (cyc==92) begin brx<=1;ba<=32;bd<=`RX_SEG2;end
    end else begin
      ph=cyc%300000;
      rst_n <= !(ph<3 || (($random(seed)&262143)==0));
      reload <= (($random(seed)&2047)==0);
      halt <= (($random(seed)&16383)==0);
      epoch_go <= ((ph>60 && ph<70) || (($random(seed)&131071)==0)) ? 1 : (epoch_go && (($random(seed)&7)!=0));
      btx <= (($random(seed)&511)==0); brx <= (($random(seed)&511)==0);
      ba <= $random(seed); bd <= $random(seed);
    end
    if (cyc==1500000) begin
      $display("RESULT cycles=%0d mismatches=%0d mutant_mismatches=%0d cal_starts=%0d tokens=%0d layers=%h ready_gold=%0d ready_dut=%0d",cyc,bad,mutant_bad,starts,tok,layers_seen,ready_g,ready_d);
      if (bad || !mutant_bad || layers_seen!==36'hfffffffff || ready_g!=ready_d) $fatal(1,"ROM calendar exactness failure");
      $finish;
    end
  end
endmodule
