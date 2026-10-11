`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_hier (s81-suhc-hier-1011, 2026-10-11): the S81 HC engine as a HIERARCHICAL slab, a drop-in for
// ot_s81_hc_core (same ports, same job contract, bit-exact): the root (ot_s81_hc_hroot: job intake, VM slots, the
// norm's scalar tail) and KT identical hardened row-group tiles (ot_s81_hc_tile, G = NG / KT groups each) in a column
// along the slab.  Between neighbours every bus crosses RS relay register stages (relay stations: one tile pitch per
// RS + 1 registers, the tile's own pin flop the last): the forward bus (root commands + VM response rows) runs root ->
// tile 0 -> .. -> tile KT-1, each tile's y slice runs beside it, and the return packet bus runs tile KT-1 -> .. -> tile
// 0 -> root.  The reset is relayed tile to tile (two flops a tile).  No signal spans more than one tile pitch.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_hier #(
    parameter integer NG = 256, D = 5120, S_RD = 2, S_WR = 8, LVM = 10, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer OQ = 512, MUT = 0, KT = 8, RS = 1
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   e_cmd_v,
    input  wire [83:0]            e_cmd_d,
    output wire                   e_cmd_ready,
    output wire                   e_done_v,
    output wire [7:0]             e_done_tag,
    input  wire                   y_v,
    output wire                   y_rdy,
    input  wire [NG*32-1:0]       y_d,
    output wire [S_RD-1:0]        rq_v,
    output wire [S_RD*14-1:0]     rq_row,
    input  wire [S_RD-1:0]        rs_v,
    input  wire [S_RD*512-1:0]    rs_d,
    output wire [S_WR-1:0]        wq_v,
    output wire [S_WR*14-1:0]     wq_row,
    output wire [S_WR*16-1:0]     wq_mask,
    output wire [S_WR*512-1:0]    wq_d,
    output wire                   busy,
    output wire                   fault,
    output wire [3:0]             fault_code,
    output wire [31:0]            st_jobs
);
    localparam integer G = NG / KT;
    localparam integer O_RD = 5 + S_RD * 16, O_PB = O_RD + S_RD * 512, FDW = O_PB + 12 + 6 + 8 + 32 + 1;
    localparam integer RDW = 2 * S_WR + 8 * S_WR + 16 * S_WR + 512 * S_WR + 8 + KT * 128;
    localparam integer FVW = S_RD + 5, RVW = S_WR + 4;
    wire [FVW-1:0]   r_fv;
    wire [FDW-1:0]   r_fd;
    wire [NG*32-1:0] r_y;
    wire [RVW-1:0]   r_rv;
    wire [RDW-1:0]   r_rd;
    ot_s81_hc_hroot #(.NG(NG), .D(D), .KT(KT), .S_RD(S_RD), .S_WR(S_WR), .ML(ML), .AL(AL), .MUT(MUT)) u_root (
        .clk(clk), .rst_n(rst_n), .e_cmd_v(e_cmd_v), .e_cmd_d(e_cmd_d), .e_cmd_ready(e_cmd_ready), .e_done_v(e_done_v),
        .e_done_tag(e_done_tag), .y_v(y_v), .y_rdy(y_rdy), .y_d(y_d), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v),
        .rs_d(rs_d), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(busy), .fault(fault),
        .fault_code(fault_code), .st_jobs(st_jobs), .fv(r_fv), .fd(r_fd), .yo(r_y), .rv_in(r_rv), .rd_in(r_rd));

    wire [FVW-1:0] t_fvo [0:KT-1];
    wire [FDW-1:0] t_fdo [0:KT-1];
    wire [RVW-1:0] t_rvo [0:KT-1];
    wire [RDW-1:0] t_rdo [0:KT-1];
    wire           t_rso [0:KT-1];
    localparam integer SEG = (G < 32) ? G : 32, NU = 4 * G / SEG;
    wire [NU*32-1:0] t_pmn [0:KT-1];
    wire [NU*32-1:0] t_pms [0:KT-1];
    genvar t;
    generate for (t = 0; t < KT; t = t + 1) begin : g_t
        wire [FVW-1:0] fv_src = (t == 0) ? r_fv : t_fvo[t > 0 ? t - 1 : 0];
        wire [FDW-1:0] fd_src = (t == 0) ? r_fd : t_fdo[t > 0 ? t - 1 : 0];
        wire [RVW-1:0] rv_src = (t == KT - 1) ? {RVW{1'b0}} : t_rvo[t < KT - 1 ? t + 1 : 0];
        wire [RDW-1:0] rd_src = (t == KT - 1) ? {RDW{1'b0}} : t_rdo[t < KT - 1 ? t + 1 : 0];
        wire [FVW-1:0] fv_in;
        wire [FDW-1:0] fd_in;
        wire [RVW-1:0] rv_in;
        wire [RDW-1:0] rd_in;
        wire [G*32-1:0] y_in;
        // relay stations: valids on reset flops (the regional reset of the previous tile), data on plain flops
        wire rg = (t == 0) ? rst_n : t_rso[t > 0 ? t - 1 : 0];
        ot_hdc_delay #(.W(FVW), .D(RS), .RESET(1)) u_rfv (.clk(clk), .rst_n(rg), .d(fv_src), .q(fv_in));
        ot_hdc_delay #(.W(FDW), .D(RS)) u_rfd (.clk(clk), .rst_n(rst_n), .d(fd_src), .q(fd_in));
        ot_hdc_delay #(.W(RVW), .D(RS), .RESET(1)) u_rrv (.clk(clk), .rst_n(rg), .d(rv_src), .q(rv_in));
        ot_hdc_delay #(.W(RDW), .D(RS)) u_rrd (.clk(clk), .rst_n(rst_n), .d(rd_src), .q(rd_in));
        // the tile's y slice beside the forward bus: (t+1)(RS+1) - 1 stages from the root's y register
        ot_hdc_delay #(.W(G * 32), .D((t + 1) * RS + t)) u_ry (.clk(clk), .rst_n(rst_n), .d(r_y[G * 32 * t +: G * 32]), .q(y_in));
        // G = 16 quant-maximum exchange with the neighbours (relayed like every seam)
        wire [NU*32-1:0] pm_n, pm_s;
        ot_hdc_delay #(.W(NU * 32), .D(RS)) u_rpn (.clk(clk), .rst_n(rst_n), .d((t == 0) ? {NU*32{1'b0}} : t_pms[t > 0 ? t - 1 : 0]), .q(pm_n));
        ot_hdc_delay #(.W(NU * 32), .D(RS)) u_rps (.clk(clk), .rst_n(rst_n), .d((t == KT - 1) ? {NU*32{1'b0}} : t_pmn[t < KT - 1 ? t + 1 : 0]), .q(pm_s));
        ot_s81_hc_tile #(.NG(NG), .D(D), .KT(KT), .S_RD(S_RD), .S_WR(S_WR), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL), .RS(RS)) u_tile (
            .clk(clk), .rst_in((t == 0) ? rst_n : t_rso[t > 0 ? t - 1 : 0]), .rst_out(t_rso[t]), .tid(t),
            .fv_in(fv_in), .fd_in(fd_in), .fv_out(t_fvo[t]), .fd_out(t_fdo[t]), .y_in(y_in),
            .rv_in(rv_in), .rd_in(rd_in), .rv_out(t_rvo[t]), .rd_out(t_rdo[t]),
            .pm_out_n(t_pmn[t]), .pm_out_s(t_pms[t]), .pm_in_n(pm_n), .pm_in_s(pm_s));
    end endgenerate
    ot_hdc_delay #(.W(RVW), .D(RS), .RESET(1)) u_rrv0 (.clk(clk), .rst_n(rst_n), .d(t_rvo[0]), .q(r_rv));
    ot_hdc_delay #(.W(RDW), .D(RS)) u_rrd0 (.clk(clk), .rst_n(rst_n), .d(t_rdo[0]), .q(r_rd));
endmodule
