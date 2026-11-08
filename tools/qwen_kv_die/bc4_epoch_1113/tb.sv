`timescale 1ns/1fs
`include "defs.svh"
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst=0,reload=0,epoch=0,halt=0,btx=0,brx=0;
reg[5:0]ba=0;reg[31:0]bd=0,boot[0:65];
wire[52:0]g,d,m,w,f;
reg epoch_q=0,halt_q=0;
always @(posedge ck)begin epoch_q<=epoch;halt_q<=halt;end
`define PORTS(V,E,H) .ck(ck),.rst_n(rst),.reload(reload),.epoch_go(E),.halt(H),.bcfg_tx_we(btx),.bcfg_rx_we(brx),.bcfg_addr(ba),.bcfg_data(bd),.cfg_tx_we(V[0]),.cfg_rx_we(V[1]),.cfg_addr(V[7:2]),.cfg_data(V[39:8]),.cal_start(V[40]),.cal_seg(V[41]),.cal_ready(V[42]),.running(V[43]),.adm_done(V[44]),.tok_start(V[45]),.fault(V[46]),.layer(V[52:47])
bc4_literal_qc_pair gold(`PORTS(g,epoch,halt));
qkd_d2d_cal_seq_pin_bc4 #(.VIAMAP("profile.viamap.hex")) dut(`PORTS(d,epoch,halt));
qkd_d2d_cal_seq_pin_bc4 #(.VIAMAP("stale.viamap.hex")) stale(`PORTS(m,epoch,halt));
qkd_d2d_cal_seq_pin_bc4 #(.VIAMAP("profile.viamap.hex"),.MUT(1)) lost_base(`PORTS(w,epoch,halt));
qkd_d2d_cal_seq_pin_bc4 #(.VIAMAP("profile.viamap.hex")) feedback(`PORTS(f,epoch_q,halt_q));
// Only the selected RF input cohort is modelled here: cfg+start all add1.
// The real all-port RF wrapper has its own native lockstep proof.
reg[41:0]rf,fb_rf;reg[5:0]rf_layer,fb_layer;
always @(posedge ck)begin fb_rf<=f[41:0];fb_layer<=f[52:47];end
always @(posedge ck)begin rf<=d[41:0];rf_layer<=d[52:47];end
integer cyc=0,stim=0,bad=0,stale_bad=0,epochs=0,starts=0,ready_at=-1;
integer first_token=-1,stale_first=-1,rf_min_gap=9999,feedback_first=-1,feedback_starts=0;
integer tb0=0,rb0=0,tbr=0,rbr=0,tbw=0,rbw=0,last_rf_base=-100,base_errors=0,rf_errors=0;
reg old_epoch=0,old_feedback_epoch=0;
always @(posedge ck)begin
 cyc=cyc+1;
 if(epoch&&!old_epoch)begin epochs=epochs+1;$display("EPOCH input_sample=%0d id=%0d",cyc,epochs);end
 old_epoch=epoch;
 if(epoch_q&&!old_feedback_epoch)$display("FEEDBACK_EPOCH input_sample=%0d",cyc);
 old_feedback_epoch=epoch_q;
 if(cyc>35)begin
  if(g!==d)begin bad=bad+1;if(bad<4)$display("MISMATCH cycle=%0d literal=%h rom=%h",cyc,g,d);end
  if(d!==m)stale_bad=stale_bad+1;
  if(d[46])$fatal(1,"native BC4 fault at%0d",cyc);
 end
 if(ready_at<0&&d[42])begin ready_at=cyc;$display("READY input_sample=%0d",cyc);end
 if(d[7:2]==32)begin
  if(d[0])begin tb0=d[39:8];$display("BASE source_sample=%0d side=TX value=%0d",cyc,tb0);end
  if(d[1])begin rb0=d[39:8];$display("BASE source_sample=%0d side=RX value=%0d",cyc,rb0);end
 end
 if(rf[7:2]==32)begin
  if(rf[0])tbr=rf[39:8];
  if(rf[1])rbr=rf[39:8];
  if(rf[0]||rf[1])last_rf_base=cyc;
 end
 if(w[7:2]==32)begin if(w[0])tbw=w[39:8];if(w[1])rbw=w[39:8];end
 if(d[40])begin
  starts=starts+1;
  $display("START source_sample=%0d epoch=%0d layer=%0d seg=%0d txbase=%0d rxbase=%0d",cyc,epochs,d[52:47],d[41],tb0,rb0);
  if(d[52:47]==63 && (tb0!=`TX_SEG2||rb0!=`RX_SEG2))bad=bad+1;
  if(d[52:47]==0)begin
   if(first_token<0)first_token=cyc;
   if(tb0!=`TX_SEG1||rb0!=`RX_SEG1)bad=bad+1;
  end
 end
 if(m[40]&&m[52:47]==0&&stale_first<0)stale_first=cyc;
 if(w[40]&&w[52:47]==0&&(tbw!=`TX_SEG1||rbw!=`RX_SEG1))base_errors=base_errors+1;
 if(rf[40])begin
  $display("RF_START input_sample=%0d epoch=%0d layer=%0d txbase=%0d rxbase=%0d last_cfg_gap=%0d",cyc,epochs,rf_layer,tbr,rbr,cyc-last_rf_base);
  if(rf_layer==0)begin
   if(tbr!=`TX_SEG1||rbr!=`RX_SEG1)rf_errors=rf_errors+1;
   if(cyc-last_rf_base<rf_min_gap)rf_min_gap=cyc-last_rf_base;
  end
 end
 if(fb_rf[40])begin
  feedback_starts=feedback_starts+1;
  $display("FEEDBACK_START receiver_sample=%0d epoch=%0d layer=%0d",cyc,epochs,fb_layer);
  if(fb_layer==0&&feedback_first<0)feedback_first=cyc;
 end
 if(cyc==6000)begin
  $display("RESULT cycles=%0d epochs=%0d starts=%0d errors=%0d stale_differences=%0d lost_base_errors=%0d rf_errors=%0d rf_min_cfg_gap=%0d first_token=%0d stale_first=%0d early_by=%0d",cyc,epochs,starts,bad,stale_bad,base_errors,rf_errors,rf_min_gap,first_token,stale_first,first_token-stale_first);
  if(bad||rf_errors||epochs!=3||starts!=6||stale_bad==0||base_errors!=3||first_token-stale_first!=170||rf_min_gap<2)$fatal(1,"BC4 epoch/profile contract");
  $display("FEEDBACK_RESULT starts=%0d first_token=%0d extra_vs_native=%0d",feedback_starts,feedback_first,feedback_first-first_token);
  if(feedback_starts!=6||feedback_first-first_token!=2)$fatal(1,"RF forwarded epoch plus control capture law");
  $display("BC4_EPOCH_PASS");$finish;
 end
end
integer k;
always @(negedge ck)begin
 stim=stim+1;rst=stim>=10;epoch=(stim>=220&&stim<223)||(stim>=2300&&stim<2303)||(stim>=4200&&stim<4203);
 halt=(stim>=2200&&stim<2205)||(stim>=4000&&stim<4005);
 reload=stim>=4020&&stim<4022;
 btx=0;brx=0;
 k=(stim>=4100)?stim-4100:stim-100;
 if(k>=0&&k<66)begin
  ba=(k<64)?6'(k/2):6'd32;bd=boot[k];btx=!(k%2);brx=k%2;
 end
end
initial $readmemh("boot.hex",boot);
endmodule
