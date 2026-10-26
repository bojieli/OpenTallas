`timescale 1ns/1ps
`default_nettype none
// Typed W1 forms of the existing fixed-epoch RTL, for sticky diagnostic levels.
// The x43 receiver adds one serial pin-capture edge; the epoch schedule is retained.
// Small diagnostic payload avoids four large
// 512/560-bit native transports inside the 345.6um VM control band.
module ot_s81_vm_fault_x34_s_w1(input wire s_ck,s_rst_n,s_v,s_d,
 output wire[1:0] b0,b1,b2,output wire[2:0] bpar,output wire s_mark);
`ifdef OT_VM_FAULT_X34S_MUT_BANK
 wire[1:0] unused_bank;assign b1=b0;
 ot_s81_vm_x34_s #(.W(1)) u(s_ck,s_rst_n,s_v,s_d,b0,unused_bank,b2,bpar,s_mark);
`else
 ot_s81_vm_x34_s #(.W(1)) u(s_ck,s_rst_n,s_v,s_d,b0,b1,b2,bpar,s_mark);
`endif
endmodule
module ot_s81_vm_fault_x34_t_w1(input wire t_ck,t_rst_n,
 input wire[1:0] b0,b1,b2,input wire[2:0] bpar,input wire s_mark,
 output wire o_v,o_d,fault);
`ifdef OT_VM_FAULT_X34T_MUT_BANK
 ot_s81_vm_x34_t #(.W(1)) u(t_ck,t_rst_n,b0,b2,b1,bpar,s_mark,o_v,o_d,fault);
`else
 ot_s81_vm_x34_t #(.W(1)) u(t_ck,t_rst_n,b0,b1,b2,bpar,s_mark,o_v,o_d,fault);
`endif
endmodule
module ot_s81_vm_fault_x43_t_w1(input wire t_ck,t_rst_n,s_v,s_d,
 output wire[1:0] b0,b2,b3,output wire[2:0] bpar,output wire t_mark,ph1_bad);
`ifdef OT_VM_FAULT_X43T_MUT_BANK
 wire[1:0] unused_bank;assign b3=b2;
 ot_s81_vm_x43_t #(.W(1)) u(t_ck,t_rst_n,s_v,s_d,b0,b2,unused_bank,bpar,t_mark,ph1_bad);
`else
 ot_s81_vm_x43_t #(.W(1)) u(t_ck,t_rst_n,s_v,s_d,b0,b2,b3,bpar,t_mark,ph1_bad);
`endif
endmodule
module ot_s81_vm_fault_x43_s_w1(input wire s_ck,s_rst_n,
 input wire[1:0] b0,b2,b3,input wire[2:0] bpar,input wire t_mark,ph1_bad,
 output wire o_v,o_d,fault);
// Capture each bank only at its original fixed read edge, including its parity.
// The original reader follows one serial edge later. Matched ICGs balance input
// and output clock depth, following the existing x34 NAT/BAL implementation.
 reg r1; reg [1:0] sp;
 always @(posedge s_ck) r1 <= s_rst_n;
 always @(posedge s_ck) if (!r1) sp <= 2'd0;
                         else sp <= (sp == 2'd2) ? 2'd0 : sp + 2'd1;
 // The first release edge uses reset-held sp=0; capture bank2 then bank3 then bank0.
 wire e2 = !r1 || sp == 2'd2, e3 = r1 && sp == 2'd0, e0 = r1 && sp == 2'd1;
 reg [2:0] c0,c2,c3;
 reg mk_q,ph_q;
 always @(posedge s_ck) begin mk_q <= t_mark; ph_q <= ph1_bad; end
 wire ck_b;
`ifdef SYNTHESIS
 wire g0,g2,g3;
 ICGx2_ASAP7_75t_R u_g0(.CLK(s_ck),.ENA(e0),.SE(1'b0),.GCLK(g0));
 ICGx2_ASAP7_75t_R u_g2(.CLK(s_ck),.ENA(e2),.SE(1'b0),.GCLK(g2));
 ICGx2_ASAP7_75t_R u_g3(.CLK(s_ck),.ENA(e3),.SE(1'b0),.GCLK(g3));
 ICGx2_ASAP7_75t_R u_gb(.CLK(s_ck),.ENA(r1),.SE(1'b0),.GCLK(ck_b));
 always @(posedge g0) c0 <= {bpar[0],b0};
 always @(posedge g2) c2 <= {bpar[1],b2};
 always @(posedge g3) c3 <= {bpar[2],b3};
`else
 assign ck_b=s_ck;
 always @(posedge s_ck) begin
  if(e0)c0 <= {bpar[0],b0};
  if(e2)c2 <= {bpar[1],b2};
  if(e3)c3 <= {bpar[2],b3};
 end
`endif
`ifdef OT_VM_FAULT_X43S_MUT_BANK
 ot_s81_vm_x43_s #(.W(1)) u(ck_b,r1,c0[1:0],c3[1:0],c2[1:0],{c3[2],c2[2],c0[2]},mk_q,ph_q,o_v,o_d,fault);
`else
 ot_s81_vm_x43_s #(.W(1)) u(ck_b,r1,c0[1:0],c2[1:0],c3[1:0],{c3[2],c2[2],c0[2]},mk_q,ph_q,o_v,o_d,fault);
`endif
endmodule
`default_nettype wire
