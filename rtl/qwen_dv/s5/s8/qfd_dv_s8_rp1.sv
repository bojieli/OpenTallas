`timescale 1ns/1ps
// Existing c0f8097f3 RP1 state/write equations, split ctl adapter.
// Retains CLOSED ctl body: consume ARM/return before legacy ctl decode/write.
// Regional landing on cmd/chd/tw and suvm write inputs remains explicit in LP.
// QE3-SLICE2B 10-21: rp_w (vtw mux select, census 1052 loads) is driven per <=12-bit chunk by kept copies at the
// SAME edge: arm copies (qfd_s8k_rp_wgrp, identical next state + own identical reset sync) AND kept copies of
// chd_q[519]/[518] (USE_W_COPIES=1: landed field copies from the parent; 0: local net, unit bench only).
module qfd_dv_s8_rp1 #(parameter integer USE_W_COPIES=0, parameter integer NW=89) (
 input wire ck,rst_n,
 input wire[115:0]cmd_q,input wire[1037:0]chd_q,
 input wire tw_we,input wire[1:0]tw_kind,input wire[23:0]tw_addr,input wire[1023:0]tw_data,
 output wire[115:0]ctl_cmd,output wire[1037:0]ctl_chd,
 output wire vtw_we,output wire[1:0]vtw_kind,output wire[23:0]vtw_addr,output wire[1023:0]vtw_data,
 output wire fault,
 input wire[NW-1:0]w519_cp,w518_cp
);
 wire rst;
 qfd_dv_s5_rst2 u_rl(.ck(ck),.rst_n(rst_n),.rst(rst));
 reg[3:0]sid_q;reg sid_ok;
 wire setid=cmd_q[0] && cmd_q[3:1]==3'd7;
 always @(posedge ck or negedge rst)
  if(!rst)begin sid_q<=0;sid_ok<=0;end
  else if(setid)begin sid_q<=cmd_q[7:4];sid_ok<=1;end
 wire go=cmd_q[0] && sid_ok && (cmd_q[115:112]==sid_q || cmd_q[115:112]==4'hf) && cmd_q[3:1]!=3'd7;
 wire[519:0]dd_q=chd_q[519:0];
 reg rp_arm;reg[9:0]rp_base;reg[2:0]rp_k;
 wire c_rpa=go && cmd_q[3:1]==0 && cmd_q[5:4]==1;
 wire rp_w=rp_arm && dd_q[519] && dd_q[518];
 wire rp_bk=rp_k[0];
 wire rp_bad=(c_rpa && rp_arm) || (rp_w && dd_q[514:512]!=rp_k) || (rp_w && tw_we);
 always @(posedge ck or negedge rst)
  if(!rst)begin rp_arm<=0;rp_base<=0;rp_k<=0;end
  else if(c_rpa)begin rp_arm<=1;rp_base<=cmd_q[15:6];rp_k<=0;end
  else if(rp_w)begin rp_k<=rp_k+3'd1;if(rp_k==7)rp_arm<=0;end
 // kept chunk selects: [0..85] vtw_data 12 b each, [86..87] vtw_addr 12 b each, [88] vtw_kind+vtw_we
 wire[NW-1:0]c519=USE_W_COPIES?w519_cp:{NW{dd_q[519]}};
 wire[NW-1:0]c518=USE_W_COPIES?w518_cp:{NW{dd_q[518]}};
 wire[NW-1:0]wk;
 wire k7=rp_k==3'd7;
 generate for(genvar g=0;g<(NW+23)/24;g=g+1)begin:g_wgrp
  localparam integer GN=(NW-g*24<24)?NW-g*24:24;
  (* keep_hierarchy = "yes" *) qfd_s8k_rp_wgrp #(.N(GN)) u_g(.ck(ck),.rst_n(rst_n),.c_rpa(c_rpa),.w_m(rp_w),.k7(k7),.arm_m(rp_arm),
   .c519(c519[g*24+:GN]),.c518(c518[g*24+:GN]),.w(wk[g*24+:GN]));
 end endgenerate
 wire[23:0]rp_addr={12'd0,1'b1,rp_bk,rp_base+{8'd0,rp_k[2:1]}};
 wire[1023:0]rp_data={dd_q[511:0],dd_q[511:0]};
 generate for(genvar i=0;i<1024;i=i+1)begin:g_vd
  assign vtw_data[i]=wk[i/12] ? rp_data[i] : tw_data[i];
 end
 for(genvar i=0;i<24;i=i+1)begin:g_va
  assign vtw_addr[i]=wk[86+i/12] ? rp_addr[i] : tw_addr[i];
 end endgenerate
 assign vtw_we=tw_we || wk[88];
 assign vtw_kind=wk[88] ? 2'd1 : tw_kind;
 assign ctl_cmd={cmd_q[115:1],cmd_q[0] && !c_rpa};
 assign ctl_chd={chd_q[1037:520],chd_q[519] && !rp_w,chd_q[518:0]};
 assign fault=rp_bad;
endmodule
