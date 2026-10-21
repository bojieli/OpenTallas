`timescale 1ns/1ps
// Existing c0f8097f3 RP1 state/write equations, split ctl adapter.
// Retains CLOSED ctl body: consume ARM/return before legacy ctl decode/write.
// Regional landing on cmd/chd/tw and suvm write inputs remains explicit in LP.
module qfd_dv_s8_rp1 (
 input wire ck,rst_n,
 input wire[115:0]cmd_q,input wire[1037:0]chd_q,
 input wire tw_we,input wire[1:0]tw_kind,input wire[23:0]tw_addr,input wire[1023:0]tw_data,
 output wire[115:0]ctl_cmd,output wire[1037:0]ctl_chd,
 output wire vtw_we,output wire[1:0]vtw_kind,output wire[23:0]vtw_addr,output wire[1023:0]vtw_data,
 output wire fault
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
 assign vtw_we=tw_we || rp_w;
 assign vtw_kind=rp_w ? 2'd1 : tw_kind;
 assign vtw_addr=rp_w ? {12'd0,1'b1,rp_bk,rp_base+{8'd0,rp_k[2:1]}} : tw_addr;
 assign vtw_data=rp_w ? {dd_q[511:0],dd_q[511:0]} : tw_data;
 assign ctl_cmd={cmd_q[115:1],cmd_q[0] && !c_rpa};
 assign ctl_chd={chd_q[1037:520],chd_q[519] && !rp_w,chd_q[518:0]};
 assign fault=rp_bad;
endmodule
