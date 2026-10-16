`timescale 1ns/1ps
`default_nettype none
// Typed W1 forms of the existing fixed-epoch RTL, for sticky diagnostic levels.
// No algorithm or schedule changes. Small diagnostic payload avoids four large
// 512/560-bit native transports inside the 345.6um VM control band.
module ot_s81_vm_fault_x34_s_w1(input wire s_ck,s_rst_n,s_v,s_d,
 output wire[1:0] b0,b1,b2,output wire[2:0] bpar,output wire s_mark);
 ot_s81_vm_x34_s #(.W(1)) u(s_ck,s_rst_n,s_v,s_d,b0,b1,b2,bpar,s_mark);
endmodule
module ot_s81_vm_fault_x34_t_w1(input wire t_ck,t_rst_n,
 input wire[1:0] b0,b1,b2,input wire[2:0] bpar,input wire s_mark,
 output wire o_v,o_d,fault);
 ot_s81_vm_x34_t #(.W(1)) u(t_ck,t_rst_n,b0,b1,b2,bpar,s_mark,o_v,o_d,fault);
endmodule
module ot_s81_vm_fault_x43_t_w1(input wire t_ck,t_rst_n,s_v,s_d,
 output wire[1:0] b0,b2,b3,output wire[2:0] bpar,output wire t_mark,ph1_bad);
 ot_s81_vm_x43_t #(.W(1)) u(t_ck,t_rst_n,s_v,s_d,b0,b2,b3,bpar,t_mark,ph1_bad);
endmodule
module ot_s81_vm_fault_x43_s_w1(input wire s_ck,s_rst_n,
 input wire[1:0] b0,b2,b3,input wire[2:0] bpar,input wire t_mark,ph1_bad,
 output wire o_v,o_d,fault);
 ot_s81_vm_x43_s #(.W(1)) u(s_ck,s_rst_n,b0,b2,b3,bpar,t_mark,ph1_bad,o_v,o_d,fault);
endmodule
`default_nettype wire
