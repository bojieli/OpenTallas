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
 // Source-role guard factoring: each is the same scalar three-input AND.
 // Kept pair/guard cells prevent cross-chunk ABC sharing; no new state/edge.
 wire rp_ab,rp_ac,rp_bc;
 qfd_dv_s8_rp_and2 #(.ID(0)) u_ab(.a(rp_arm),.b(dd_q[519]),.y(rp_ab));
 qfd_dv_s8_rp_and2 #(.ID(1)) u_ac(.a(rp_arm),.b(dd_q[518]),.y(rp_ac));
 qfd_dv_s8_rp_and2 #(.ID(2)) u_bc(.a(dd_q[519]),.b(dd_q[518]),.y(rp_bc));
 wire [68:0] rp_guard;
 generate for(genvar g=0;g<69;g=g+1)begin:g_guard
   if(g%3==0)begin:g_ab
     qfd_dv_s8_rp_and2 #(.ID(100+g)) u_g(.a(rp_ab),.b(dd_q[518]),.y(rp_guard[g]));
   end else if(g%3==1)begin:g_ac
     qfd_dv_s8_rp_and2 #(.ID(100+g)) u_g(.a(rp_ac),.b(dd_q[519]),.y(rp_guard[g]));
   end else begin:g_bc
     qfd_dv_s8_rp_and2 #(.ID(100+g)) u_g(.a(rp_bc),.b(rp_arm),.y(rp_guard[g]));
   end
 end endgenerate
 wire rp_w=rp_guard[64];
 wire rp_bk=rp_k[0];
 wire rp_bad=(c_rpa && rp_arm) || (rp_w && dd_q[514:512]!=rp_k) || (rp_w && tw_we);
 always @(posedge ck or negedge rst)
  if(!rst)begin rp_arm<=0;rp_base<=0;rp_k<=0;end
  else if(c_rpa)begin rp_arm<=1;rp_base<=cmd_q[15:6];rp_k<=0;end
  else if(rp_w)begin rp_k<=rp_k+3'd1;if(rp_k==7)rp_arm<=0;end
 assign vtw_we=tw_we || rp_w;
 wire [23:0] rp_addr={12'd0,1'b1,rp_bk,rp_base+{8'd0,rp_k[2:1]}};
 wire [1023:0] rp_data={dd_q[511:0],dd_q[511:0]};
 generate for(genvar g=0;g<64;g=g+1)begin:g_data_mux
   qfd_dv_s8_rp_mux #(.W(16),.ID(g)) u_m(.s(rp_guard[g]),
     .a(rp_data[g*16+:16]),.b(tw_data[g*16+:16]),.y(vtw_data[g*16+:16]));
 end
 for(genvar g=0;g<3;g=g+1)begin:g_addr_mux
   qfd_dv_s8_rp_mux #(.W(8),.ID(80+g)) u_m(.s(rp_guard[65+g]),
     .a(rp_addr[g*8+:8]),.b(tw_addr[g*8+:8]),.y(vtw_addr[g*8+:8]));
 end endgenerate
 qfd_dv_s8_rp_mux #(.W(2),.ID(90)) u_kind(.s(rp_guard[68]),
   .a(2'd1),.b(tw_kind),.y(vtw_kind));
 assign ctl_cmd={cmd_q[115:1],cmd_q[0] && !c_rpa};
 assign ctl_chd={chd_q[1037:520],chd_q[519] && !rp_w,chd_q[518:0]};
 assign fault=rp_bad;
endmodule

// Real combinational cells; no blackbox, clock, constraint or reset exceptions.
(* keep_hierarchy="yes" *) module qfd_dv_s8_rp_and2 #(parameter integer ID=0)(input wire a,b,output wire y);
 assign y=a & b;
endmodule
(* keep_hierarchy="yes" *) module qfd_dv_s8_rp_mux #(parameter integer W=16,ID=0)(input wire s,input wire[W-1:0]a,b,output wire[W-1:0]y);
 // Retain Verilog ternary's four-state bit merge when s is X/Z.
 assign y=s ? a : b;
endmodule
