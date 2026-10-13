`timescale 1ns/1ps
// BENCH FIXTURE of dsfd_sp_pq: the cluster with the three ROMs as the screen's two-cycle synchronous ROM models
// (ot_v41_pqc_rom2_model, written through rw_*), i.e. the port list and timing of ot_v41_pqc_spine_screen, so the
// lockstep bench (tools/s81/sp_pq_lockstep.py) drives it and the flat v14 screen with the same pins.
module dsfd_sp_pq_screen_fix (
    input  wire clk, rst_n, go,
    input  wire [5:0] i_ph, input wire [2:0] i_np, input wire [18:0] i_xbase, i_xps, i_obase, i_ops,
    input  wire [1:0] i_fmt, input wire [2047:0] x_q, input wire x_rv,
    input  wire [15:0] r_v, input wire [255:0] r_row, input wire [47:0] r_pos, input wire [511:0] r_fp32,
    input  wire [255:0] r_bf16, input wire [15:0] r_e, input wire f_fault,
    input  wire rw_ph, rw_st, input wire [7:0] rw_a, input wire [63:0] rw_d,
    output wire o_ready, o_idle, o_x_re, output wire [18:0] o_x_addr,
    output wire [15:0] o_w_we, output wire [303:0] o_w_addr, output wire [511:0] o_w_data,
    output wire [1629:0] o_bus, output wire o_fault, o_ev
);
    wire [6:0] pa0, pa1;
    wire [7:0] sa;
    wire [63:0] pq0, pq1;
    wire [47:0] sq;
    ot_v41_pqc_rom2_model #(.AW(8), .DW(48)) u_srom (.clk(clk), .rst_n(rst_n), .we(rw_st), .wa(rw_a), .wd(rw_d[47:0]),
                                                     .ra(sa), .q(sq));
    ot_v41_pqc_rom2_model #(.AW(7), .DW(64)) u_prom0 (.clk(clk), .rst_n(rst_n), .we(rw_ph), .wa(rw_a[6:0]), .wd(rw_d),
                                                      .ra(pa0), .q(pq0));
    ot_v41_pqc_rom2_model #(.AW(7), .DW(64)) u_prom1 (.clk(clk), .rst_n(rst_n), .we(rw_ph), .wa(rw_a[6:0]), .wd(rw_d),
                                                      .ra(pa1), .q(pq1));
    dsfd_sp_pq u_dut (.clk(clk), .rst_n(rst_n), .go(go), .i_ph(i_ph), .i_np(i_np), .i_xbase(i_xbase), .i_xps(i_xps),
        .i_obase(i_obase), .i_ops(i_ops), .i_fmt(i_fmt), .f_fault(f_fault), .o_ready(o_ready), .o_idle(o_idle),
        .o_fault(o_fault), .o_ev(o_ev), .o_x_re(o_x_re), .o_x_addr(o_x_addr), .x_rv(x_rv), .x_q(x_q), .r_v(r_v),
        .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .o_w_we(o_w_we),
        .o_w_addr(o_w_addr), .o_w_data(o_w_data), .o_bus(o_bus), .rom_pa0(pa0), .rom_pa1(pa1),
        .rom_pq0(pq0), .rom_pq1(pq1), .rom_sa(sa), .rom_sq(sq));
endmodule
