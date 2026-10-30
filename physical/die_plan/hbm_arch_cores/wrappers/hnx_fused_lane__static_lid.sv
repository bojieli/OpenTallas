`timescale 1ns/1ps
`default_nettype none
// SOURCE PREP ONLY: exact R7 static-ID variant; default native mode is unchanged.
module hnx_fused_lane__static_lid (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4:0]    strap_lid,
    output wire           rq_v,
    output wire  [15:0]   rq_s,
    input  wire          rr_v,
    input  wire [255:0]  rr_d,
    output wire           wq_v,
    output wire  [15:0]   wq_s,
    output wire  [255:0]  wq_d,
    input  wire          dn_v,
    input  wire [2:0]    dn_op,
    input  wire [7:0]    dn_x,
    input  wire [127:0]  dn_d,
    input  wire          r_v,
    input  wire [31:0]   r_d,
    output wire           up_v,
    output wire           up_t,
    output wire  [9:0]    up_x,
    output wire  [255:0]  up_d,
    output wire           fin,
    output wire           flt

);
 ot_hnx_fused_lane #(.D(5120), .KX(4), .RR(10), .STATIC_LID(1)) u_native(
  .clk(clk),
  .rst_n(rst_n),
  .lid(strap_lid),
  .rq_v(rq_v),
  .rq_s(rq_s),
  .rr_v(rr_v),
  .rr_d(rr_d),
  .wq_v(wq_v),
  .wq_s(wq_s),
  .wq_d(wq_d),
  .dn_v(dn_v),
  .dn_op(dn_op),
  .dn_x(dn_x),
  .dn_d(dn_d),
  .r_v(r_v),
  .r_d(r_d),
  .up_v(up_v),
  .up_t(up_t),
  .up_x(up_x),
  .up_d(up_d),
  .fin(fin),
  .flt(flt)
 );
endmodule
`default_nettype wire
