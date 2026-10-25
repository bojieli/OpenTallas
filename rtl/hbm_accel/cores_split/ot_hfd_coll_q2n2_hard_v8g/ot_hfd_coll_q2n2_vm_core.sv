// GENERATED (PATH-HBM/NE2 2026-10-25) from ot_hfd_coll_q3_vm_core.sv (build_split_tops coll_q3_vm, main a63baaa9a0): same members
// u_vmasm = ot_hgi_coll_vmasm_sliced_v7, u_writer = ot_hgi_coll_static_vmwrite_roots_v6_physical, minus the TKM write port:
// ot_hfd_coll_q2_hard_v8g_s #(NLINK 2) drives the writer tkw_v/tkw_d with constant 0 (no TKM in NE_hub), so the constant
// is folded INSIDE this core (no tied partition pins) and the clk_tkw domain runs on the clk_meta tap. NE_hub vm piece.
// Functional split-piece type coll_q3_vm: master ot_hfd_coll_q3_hard_v8x_s; replicas 1 (ot_hfd_coll_q3_hard_v8x_s__vm).
// Members (roles): u_vmasm = ot_hgi_coll_vmasm_sliced_v7  (as-built ot_hgi_coll_vmasm_sliced_v7 at u_body.u_vmasm); u_writer = ot_hgi_coll_static_vmwrite_roots_v6_physical  (as-built ot_hgi_coll_static_vmwrite_roots_v6_physical at u_body.u_writer)
// Source wiring: rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q3_hard_v8x_s.sv #(NLINK 3, TP 192, AR_ITER 1, ROWS 256, VM_RT 81) u_body.u_vmasm (VM read assembly, vm_rr face) + u_body.u_writer (VM write roots, vm_kq face): body_core <= ~260k
// Wired bit-exactly as the as-built master netlist (split_conn.py); straps = replica constants tied at the parent.
`timescale 1ns/1ps
`default_nettype none
module ot_hfd_coll_q2n2_vm_core (
    input wire [15:0] vmasm_clk,
    input wire [23:0] vmasm_sel,
    input wire [2047:0] vmasm_rd_il,
    input wire writer_clk_rgx_data0,
    input wire writer_clk_rgx_data1,
    input wire writer_clk_rgx_data2,
    input wire writer_clk_rgx_data3,
    input wire writer_clk_rgx_ctrl,
    input wire writer_clk_meta,
    input wire writer_clk_body,
    input wire writer_clk_bank0,
    input wire writer_clk_bank1,
    input wire writer_clk_bank2,
    input wire writer_clk_bank3,
    input wire writer_clk_bank4,
    input wire writer_clk_bank5,
    input wire writer_clk_bank6,
    input wire writer_clk_bank7,
    input wire writer_rst_n,
    input wire [1:0] writer_sid,
    input wire [3:0] writer_rgx_v,
    input wire [159:0] writer_rgx_addr,
    input wire [511:0] writer_rgx_data0,
    input wire [511:0] writer_rgx_data1,
    input wire [511:0] writer_rgx_data2,
    input wire [511:0] writer_rgx_data3,
    input wire writer_rgx_vm,
    input wire [4:0] writer_ingress_slot,
    input wire [7:0] writer_slot_valid,
    input wire [31:0] writer_slot_owner,
    output wire [2047:0] vmasm_as_il,
    output wire [280:0] writer_kq0,
    output wire [280:0] writer_kq1,
    output wire [280:0] writer_kq2,
    output wire [280:0] writer_kq3,
    output wire [280:0] writer_kq4,
    output wire [280:0] writer_kq5,
    output wire [280:0] writer_kq6,
    output wire [280:0] writer_kq7,
    output wire writer_fault
);
    wire [15:0] u_vmasm__clk;
    wire [23:0] u_vmasm__sel;
    wire [2047:0] u_vmasm__rd_il;
    wire [2047:0] u_vmasm__as_il;
    ot_hgi_coll_vmasm_sliced_v7 u_vmasm (
        .clk(u_vmasm__clk),
        .sel(u_vmasm__sel),
        .rd_il(u_vmasm__rd_il),
        .as_il(u_vmasm__as_il));
    wire u_writer__clk_rgx_data0;
    wire u_writer__clk_rgx_data1;
    wire u_writer__clk_rgx_data2;
    wire u_writer__clk_rgx_data3;
    wire u_writer__clk_rgx_ctrl;
    wire u_writer__clk_tkw;
    wire u_writer__clk_meta;
    wire u_writer__clk_body;
    wire u_writer__clk_bank0;
    wire u_writer__clk_bank1;
    wire u_writer__clk_bank2;
    wire u_writer__clk_bank3;
    wire u_writer__clk_bank4;
    wire u_writer__clk_bank5;
    wire u_writer__clk_bank6;
    wire u_writer__clk_bank7;
    wire u_writer__rst_n;
    wire [1:0] u_writer__sid;
    wire [3:0] u_writer__rgx_v;
    wire [159:0] u_writer__rgx_addr;
    wire [511:0] u_writer__rgx_data0;
    wire [511:0] u_writer__rgx_data1;
    wire [511:0] u_writer__rgx_data2;
    wire [511:0] u_writer__rgx_data3;
    wire u_writer__rgx_vm;
    wire u_writer__tkw_v;
    wire [567:0] u_writer__tkw_d;
    wire [4:0] u_writer__ingress_slot;
    wire [7:0] u_writer__slot_valid;
    wire [31:0] u_writer__slot_owner;
    wire [280:0] u_writer__kq0;
    wire [280:0] u_writer__kq1;
    wire [280:0] u_writer__kq2;
    wire [280:0] u_writer__kq3;
    wire [280:0] u_writer__kq4;
    wire [280:0] u_writer__kq5;
    wire [280:0] u_writer__kq6;
    wire [280:0] u_writer__kq7;
    wire [4:0] u_writer__launch_done;
    wire u_writer__fault;
    ot_hgi_coll_static_vmwrite_roots_v6_physical u_writer (
        .clk_rgx_data0(u_writer__clk_rgx_data0),
        .clk_rgx_data1(u_writer__clk_rgx_data1),
        .clk_rgx_data2(u_writer__clk_rgx_data2),
        .clk_rgx_data3(u_writer__clk_rgx_data3),
        .clk_rgx_ctrl(u_writer__clk_rgx_ctrl),
        .clk_tkw(u_writer__clk_tkw),
        .clk_meta(u_writer__clk_meta),
        .clk_body(u_writer__clk_body),
        .clk_bank0(u_writer__clk_bank0),
        .clk_bank1(u_writer__clk_bank1),
        .clk_bank2(u_writer__clk_bank2),
        .clk_bank3(u_writer__clk_bank3),
        .clk_bank4(u_writer__clk_bank4),
        .clk_bank5(u_writer__clk_bank5),
        .clk_bank6(u_writer__clk_bank6),
        .clk_bank7(u_writer__clk_bank7),
        .rst_n(u_writer__rst_n),
        .sid(u_writer__sid),
        .rgx_v(u_writer__rgx_v),
        .rgx_addr(u_writer__rgx_addr),
        .rgx_data0(u_writer__rgx_data0),
        .rgx_data1(u_writer__rgx_data1),
        .rgx_data2(u_writer__rgx_data2),
        .rgx_data3(u_writer__rgx_data3),
        .rgx_vm(u_writer__rgx_vm),
        .tkw_v(u_writer__tkw_v),
        .tkw_d(u_writer__tkw_d),
        .ingress_slot(u_writer__ingress_slot),
        .slot_valid(u_writer__slot_valid),
        .slot_owner(u_writer__slot_owner),
        .kq0(u_writer__kq0),
        .kq1(u_writer__kq1),
        .kq2(u_writer__kq2),
        .kq3(u_writer__kq3),
        .kq4(u_writer__kq4),
        .kq5(u_writer__kq5),
        .kq6(u_writer__kq6),
        .kq7(u_writer__kq7),
        .launch_done(u_writer__launch_done),
        .fault(u_writer__fault));
    assign u_vmasm__clk[15:0] = vmasm_clk[15:0];
    assign u_vmasm__sel[23:0] = vmasm_sel[23:0];
    assign u_vmasm__rd_il[2047:0] = vmasm_rd_il[2047:0];
    assign vmasm_as_il[2047:0] = u_vmasm__as_il[2047:0];
    assign u_writer__clk_rgx_data0 = writer_clk_rgx_data0;
    assign u_writer__clk_rgx_data1 = writer_clk_rgx_data1;
    assign u_writer__clk_rgx_data2 = writer_clk_rgx_data2;
    assign u_writer__clk_rgx_data3 = writer_clk_rgx_data3;
    assign u_writer__clk_rgx_ctrl = writer_clk_rgx_ctrl;
    assign u_writer__clk_tkw = writer_clk_meta;   // NE: no TKM write port; tkw domain on the meta tap
    assign u_writer__clk_meta = writer_clk_meta;
    assign u_writer__clk_body = writer_clk_body;
    assign u_writer__clk_bank0 = writer_clk_bank0;
    assign u_writer__clk_bank1 = writer_clk_bank1;
    assign u_writer__clk_bank2 = writer_clk_bank2;
    assign u_writer__clk_bank3 = writer_clk_bank3;
    assign u_writer__clk_bank4 = writer_clk_bank4;
    assign u_writer__clk_bank5 = writer_clk_bank5;
    assign u_writer__clk_bank6 = writer_clk_bank6;
    assign u_writer__clk_bank7 = writer_clk_bank7;
    assign u_writer__rst_n = writer_rst_n;
    assign u_writer__sid[1:0] = writer_sid[1:0];
    assign u_writer__rgx_v[3:0] = writer_rgx_v[3:0];
    assign u_writer__rgx_addr[159:0] = writer_rgx_addr[159:0];
    assign u_writer__rgx_data0[511:0] = writer_rgx_data0[511:0];
    assign u_writer__rgx_data1[511:0] = writer_rgx_data1[511:0];
    assign u_writer__rgx_data2[511:0] = writer_rgx_data2[511:0];
    assign u_writer__rgx_data3[511:0] = writer_rgx_data3[511:0];
    assign u_writer__rgx_vm = writer_rgx_vm;
    assign u_writer__tkw_v = 1'b0;   // NE (q2n2) has no TKM: as ot_hfd_coll_q2_hard_v8g_s n<3 (tk_w_* = 0), folded inside the core
    assign u_writer__tkw_d[567:0] = 568'd0;
    assign u_writer__ingress_slot[4:0] = writer_ingress_slot[4:0];
    assign u_writer__slot_valid[7:0] = writer_slot_valid[7:0];
    assign u_writer__slot_owner[31:0] = writer_slot_owner[31:0];
    assign writer_kq0[280:0] = u_writer__kq0[280:0];
    assign writer_kq1[280:0] = u_writer__kq1[280:0];
    assign writer_kq2[280:0] = u_writer__kq2[280:0];
    assign writer_kq3[280:0] = u_writer__kq3[280:0];
    assign writer_kq4[280:0] = u_writer__kq4[280:0];
    assign writer_kq5[280:0] = u_writer__kq5[280:0];
    assign writer_kq6[280:0] = u_writer__kq6[280:0];
    assign writer_kq7[280:0] = u_writer__kq7[280:0];
    assign writer_fault = u_writer__fault;
endmodule
`default_nettype wire
