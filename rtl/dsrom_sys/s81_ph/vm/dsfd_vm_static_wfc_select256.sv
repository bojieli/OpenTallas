`timescale 1ns/1ps
`default_nettype none
// Wires-only opt-in parent; original closed leaf source remains byte-identical.
module dsfd_vm_static_wfc_select256 #(parameter integer RLAT = 13, parameter integer RESPONSE_PAD = 0, parameter integer RETURN256 = 0) (
    input wire ck_control_s, ck_control_t,
    input wire ck_fault_s, ck_fault_t, rst_fault_s, rss_fault_t,
    input wire [(RETURN256?3:1)-1:0] ck_return_t,rss_return_t,
    input wire ck_fault_x34_s,ck_fault_x34_t,ck_fault_x43_t,ck_fault_x43_s,
    input wire rst_fault_x34_s,rss_fault_x34_t,rss_fault_x43_t,rst_fault_x43_s,
    input wire ck_x34_s, ck_x34_t, ck_x43_s, ck_x43_t,
    input wire rst_control_s, rss_control_t,
    input wire rst_x34_s, rss_x34_t, rst_x43_s, rss_x43_t,
    input  wire [559:0]  f_wfc,
    output wire [1028:0] t_wfc,
    // stream side to / from dsfd_vm_static_core
    output wire          w_v, output wire [13:0] w_row, output wire [511:0] w_d,
    output wire [3:0]    a_v, output wire [55:0] a_row,         // aux ports 8..11
    input  wire [3:0]    e_v, input wire [2047:0] e_d,          // aux ports 8..11 returns (core output registers)
    input  wire          vm_fault,                              // stream level
    output wire          fault                                  // core summary from u_fault; diagnostic delay only
);
    // Wires only: x34, request/return control leaf, fault bridge and x43.
    wire xv; wire [559:0] xd; wire x34f; wire ov; wire [1025:0] od; wire x43f; wire sv; wire [1025:0] sd; wire g_q, e_q; wire native_core_fault;
    // Every epoch bank carries a payload. Its write/read operation-valid bits
    // remain in xd[0]/xd[528] and gate the decoded requests after capture.
    // Always-valid transport removes a serial parent OR without changing any
    // operation, error, clock, or cycle (frozen prior wrapper comparison proves it).
    ot_s81_vm_x34 #(.W(560)) u_xi (.s_ck(ck_x34_s), .s_rst_n(rst_x34_s), .s_v(1'b1), .s_d(f_wfc),
        .t_ck(ck_x34_t), .t_rst_n(rss_x34_t), .o_v(xv), .o_d(xd), .fault(x34f));
    wire [1:0] return_valid;wire[3:0] return_lane;wire return_fault;
    dsfd_vm_wfc_request #(.RLAT(RLAT)) u_req (
      .ck(ck_control_t),.rn(rss_control_t),.xv(xv),.xd(xd),.x34f(x34f),.vm_fault(vm_fault),
      .w_v(w_v),.w_row(w_row),.w_d(w_d),.a_v(a_v),.a_row(a_row),
      .return_valid(return_valid),.return_lane(return_lane),.fault(native_core_fault));
    generate if (RETURN256) begin : split_return
      dsfd_vm_wfc_return_split256 #(.RESPONSE_PAD(RESPONSE_PAD)) u_ret (
        .ck(ck_return_t),.rn(rss_return_t),.return_valid(return_valid),.return_lane(return_lane),
        .e_v(e_v),.e_d(e_d),.s_v(sv),.s_d(sd),.r_bad(return_fault));
    end else begin : legacy_return
    dsfd_vm_wfc_return #(.RESPONSE_PAD(RESPONSE_PAD)) u_ret (
      .ck(ck_return_t),.rn(rss_return_t),.return_valid(return_valid),.return_lane(return_lane),
      .e_v(e_v),.e_d(e_d),.s_v(sv),.s_d(sd),.r_bad(return_fault));
    end endgenerate
    dsfd_vm_wfc_fault_bridge u_fault (.ck_t(ck_fault_t), .ck_s(ck_fault_s),
      .rst_t(rss_fault_t), .rst_s(rst_fault_s),
      .ck_x34_s(ck_fault_x34_s),.ck_x34_t(ck_fault_x34_t),.ck_x43_t(ck_fault_x43_t),.ck_x43_s(ck_fault_x43_s),
      .rst_x34_s(rst_fault_x34_s),.rss_x34_t(rss_fault_x34_t),.rss_x43_t(rss_fault_x43_t),.rst_x43_s(rst_fault_x43_s), .core_fault(native_core_fault),.core_fault_b(return_fault),.serial_fault(x43f),
      .core_summary(fault),.g_q(g_q),.e_q(e_q));
    ot_s81_vm_x43 #(.W(1026)) u_xo (.t_ck(ck_x43_t), .t_rst_n(rss_x43_t), .s_v(sv), .s_d(sd),
        .s_ck(ck_x43_s), .s_rst_n(rst_x43_s), .o_v(ov), .o_d(od), .fault(x43f));
    assign t_wfc = {e_q, od, g_q, g_q};
endmodule
`default_nettype wire
