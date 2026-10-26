`timescale 1ns/1ps
`default_nettype none
// Unclosed source assembly matching the intended kit reset2 + core reset2.
// A future CLOSED kit replaces this WHOLE assembly: never wrap its native
// physical view with rs_l again, which would incorrectly create reset6.
module dsdv_pv_local_land_n32_source4_276(
 input wire ck_f,input wire [275:0] i,input wire ck,rs,input wire [5:0] k,
 output wire [275:0] o,output wire fault);
 (* keep = 1 *) reg [1:0] rs_l;
 always @(posedge ck) rs_l <= {rs_l[0],rs};
 dsdv_pv_local_land_n32_276 u_native(
  .ck_f(ck_f),.i(i),.ck(ck),.rs(rs_l[1]),.k(k),.o(o),.fault(fault));
endmodule
`default_nettype wire
