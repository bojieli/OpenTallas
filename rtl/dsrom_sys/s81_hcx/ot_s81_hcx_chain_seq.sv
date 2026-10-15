`timescale 1ns/1ps
`default_nettype none
// Port-9 HC coefficient chain command face (S81 die 0): ONE compiled command runs the whole chain
//   projection (dsfd_sp_hcx_projection, this rank's 6 rows) -> TP4 raw gather (collective) -> ot_s81_hcx_gatherpack
//   (24 FP32 -> 2 raw VM rows) -> ot_s81_hcx_post_gain_native post mode (pre/post/Sinkhorn -> comb row + pre/post/eps row).
// Every start and the completion pin are fixed stream (ck) ages after the sampled command: G_OFF gatherpack start,
// POST_TOG post start (toggle into the serial post clock, fixed 4:3 phase from reset), DONE_OFF c_done. Observed events
// (projection c_done/tag, gatherpack done, post done) are CHECKED at their compiled ages and fault; they never move a
// start or the done pin. No ready, credit or wait. Offsets come from the measured chain (tb_s81_hcx_chain); the
// compiler issues the command at a projection-controller phase-2 edge and samples done at issue+1+DONE_OFF.
// Command arg24 (cmd[30:7]) is the projection's {0,layer6,h_base14,ffn}; raw/coef rows are compiler-fixed VM rows:
// raw RAW_BASE (16-aligned, 2 rows), coefficients COEF_BASE + COEF_STRIDE*ffn (comb row, pre/post/eps row).
module ot_s81_hcx_chain_seq #(
 parameter integer PROJ_DONE=1,G_OFF=1,GP_DONE=24,POST_TOG=1,POST_SEEN=1,DONE_OFF=2,
 parameter[13:0]RAW_BASE=14'd2624,COEF_BASE=14'd2560,COEF_STRIDE=14'd2
)(
 input wire ck,rst_n,skv,srst_n,
 input wire[84:0]c_cmd,
 output reg[8:0]c_done,
 output reg[1:0]c_st,
 output wire[84:0]p_cmd,
 input wire[8:0]p_done,
 input wire[1:0]p_st,
 output reg g_start,
 output wire[13:0]g_raw_base,
 input wire g_done,g_fault,
 output reg s_start,
 output reg s_ffn,
 output reg[5:0]s_layer,
 output wire[13:0]s_raw_base,
 output reg[13:0]s_coef_base,
 input wire s_done,s_fault
);
 assign p_cmd=c_cmd;assign g_raw_base=RAW_BASE;assign s_raw_base=RAW_BASE;
 reg busy,cfault,ptog,dsync1,dsync2,dseen,fsync1,fsync2;
 reg[15:0]age;reg[7:0]tag;reg ffn_q;reg[5:0]layer_q;
 // serial side: start toggle in, done toggle out
 reg tsync1,tsync2,tseen,dtog,sfault;
 always @(posedge skv or negedge srst_n)begin
  if(!srst_n)begin tsync1<=0;tsync2<=0;tseen<=0;dtog<=0;s_start<=0;sfault<=0;s_ffn<=0;s_layer<=0;s_coef_base<=0;end
  else begin
   tsync1<=ptog;tsync2<=tsync1;s_start<=0;
   if(tsync2!=tseen)begin tseen<=tsync2;s_start<=1;s_ffn<=ffn_q;s_layer<=layer_q;s_coef_base<=COEF_BASE+(ffn_q?COEF_STRIDE:14'd0);end
   if(s_done)dtog<=!dtog;
   if(s_fault)sfault<=1;
  end
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin busy<=0;cfault<=0;ptog<=0;dsync1<=0;dsync2<=0;dseen<=0;fsync1<=0;fsync2<=0;age<=0;tag<=0;
   c_done<=0;c_st<=0;g_start<=0;ffn_q<=0;layer_q<=0;end
  else begin
   c_done[8]<=0;g_start<=0;c_st<={1'b1,cfault|fsync2|p_st[0]};
   dsync1<=dtog;dsync2<=dsync1;fsync1<=sfault;fsync2<=fsync1;
   if(c_cmd[84])begin
    if(busy)cfault<=1;
    busy<=1;age<=0;tag<={c_cmd[83],c_cmd[6:0]};ffn_q<=c_cmd[7];layer_q<=c_cmd[27:22];
   end else if(busy)begin
    age<=age+1'b1;
    if(age+1'b1==16'(G_OFF))g_start<=1;
    if(age+1'b1==16'(POST_TOG))ptog<=!ptog;
    if(age+1'b1==16'(DONE_OFF))begin c_done<={1'b1,tag};busy<=0;end
   end
   // checks only: compiled ages of the observed events
   if(p_done[8]&&(!busy||age+1'b1!=16'(PROJ_DONE)||p_done[7:0]!=tag))cfault<=1;
   if(busy&&age+1'b1==16'(PROJ_DONE)&&!p_done[8])cfault<=1;
   if(g_done&&(!busy||age+1'b1!=16'(G_OFF+GP_DONE)))cfault<=1;
   if(g_fault)cfault<=1;
   if(dsync2!=dseen)begin dseen<=dsync2;if(!busy||age+1'b1!=16'(POST_SEEN))cfault<=1;end
  end
 end
endmodule
`default_nettype wire
