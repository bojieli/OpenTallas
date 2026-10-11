`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_hc (stream s81-suhc-1011, 2026-10-11): die master of the S81 HC slab.  The dsfd_sp_ctrl engine adapter
// (ot_s81_engine_adapter QD 8, engine port hc = 2) sits at the slab boundary (physical/s81_ctrl/ADAPTER_CONTRACT_1011
// .json): the die nets c_cmd_v / c_cmd_d (85 b) and c_done_v / c_done_tag (9 b) are the controller-clock pulses;
// the engine (ot_s81_hc_core) runs on the slab clock sk.  `inp` is the die dependency net (s81-ctl): the operands of
// the head descriptor are present (VM rows written by their producer); the y operand of a POST is flow-controlled on
// its own bus (y_v / y_rdy).  Every die input lands in a pin flop and every output leaves a flop (VM, y, status);
// the command / done pulses are flopped inside the adapter's CDC FIFOs.
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_hc #(
    parameter integer NG = 256, D = 5120, S_RD = 2, S_WR = 8, LVM = 10, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer OQ = 512, MUT = 0, AMUT = 0,
    parameter integer HIER = 0,                          // 0: flat engine ot_s81_hc_core; 1: hierarchical slab = root
    parameter integer NCOL = 3, GS = 8, S_RT = 4         //    tile ot_s81_hc_rtile + NCOL chains of ot_s81_hc_ctile
) (
    input  wire                cck, crs,                 // controller clock / reset (dsfd_sp_ctrl domain)
    input  wire                sk, srs,                  // slab clock / reset
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output wire                c_done_v,
    output wire [7:0]          c_done_tag,
    input  wire                inp,
    input  wire                y_v,
    output wire                y_rdy,
    input  wire [NG*32-1:0]    y_d,
    output wire [S_RD-1:0]     rq_v,
    output wire [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire [S_WR-1:0]     wq_v,
    output wire [S_WR*14-1:0]  wq_row,
    output wire [S_WR*16-1:0]  wq_mask,
    output wire [S_WR*512-1:0] wq_d,
    output wire                flt,
    output wire                online,
    output wire [3:0]          fcode
);
    wire e_v, e_r;
    wire [83:0] e_d;
    generate if (HIER) begin : g_hier
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer FDW = 5 + S_RD * 16 + 12 + 6 + 8 + 32 + 1 + FDD;
    localparam integer RDW = S_RT + 8 * S_RT + 16 * S_RT + 8 + 512 * S_RT;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    wire [NCOL-1:0]     ch_rst;
    wire [NCOL*FVW-1:0] ch_fv;
    wire [NCOL*FDW-1:0] ch_fd;
    wire [NCOL*RVW-1:0] ch_rv;
    wire [NCOL*RDW-1:0] ch_rd;
    ot_s81_hc_rtile #(.NG(NG), .D(D), .S_RD(S_RD), .S_WR(S_WR), .LVM(LVM), .ML(ML), .AL(AL), .MUT(MUT), .AMUT(AMUT),
                      .NCOL(NCOL), .GS(GS), .S_RT(S_RT)) u_rt (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .y_v(y_v), .y_rdy(y_rdy), .y_d(y_d), .rq_v(rq_v), .rq_row(rq_row),
        .rs_v(rs_v), .rs_d(rs_d), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .flt(flt),
        .online(online), .fcode(fcode), .ch_rst(ch_rst), .ch_fv(ch_fv), .ch_fd(ch_fd), .ch_rv(ch_rv), .ch_rd(ch_rd));
    genvar c, p;
    for (c = 0; c < NCOL; c = c + 1) begin : g_c
        localparam integer LC = (NS - c * NP >= NP) ? NP : (NS - c * NP > 0) ? NS - c * NP : 0;
        if (LC > 0) begin : g_live
            wire [FVW-1:0] fvo [0:LC-1];
            wire [FDW-1:0] fdo [0:LC-1];
            wire [RVW-1:0] rvo [0:LC-1];
            wire [RDW-1:0] rdo [0:LC-1];
            wire           rso [0:LC-1];
            for (p = 0; p < LC; p = p + 1) begin : g_p
                localparam [7:0] TID = c * NP + p;
                ot_s81_hc_ctile #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .WIN(WIN), .WOUT(WOUT),
                                  .ML(ML), .AL(AL)) u_t (
                    .clk(sk), .rst_in(p == 0 ? ch_rst[c] : rso[p > 0 ? p - 1 : 0]), .rst_out(rso[p]), .tid(TID),
                    .last(p == LC - 1),
                    .fv_in(p == 0 ? ch_fv[c * FVW +: FVW] : fvo[p > 0 ? p - 1 : 0]),
                    .fd_in(p == 0 ? ch_fd[c * FDW +: FDW] : fdo[p > 0 ? p - 1 : 0]),
                    .fv_out(fvo[p]), .fd_out(fdo[p]),
                    .rv_in(p == LC - 1 ? {RVW{1'b0}} : rvo[p < LC - 1 ? p + 1 : 0]),
                    .rd_in(p == LC - 1 ? {RDW{1'b0}} : rdo[p < LC - 1 ? p + 1 : 0]),
                    .rv_out(rvo[p]), .rd_out(rdo[p]));
            end
            assign ch_rv[c * RVW +: RVW] = rvo[0];
            assign ch_rd[c * RDW +: RDW] = rdo[0];
        end else begin : g_none
            assign ch_rv[c * RVW +: RVW] = 0;
            assign ch_rd[c * RDW +: RDW] = 0;
        end
    end
`ifndef SYNTHESIS
    // bench observability (tb job start cycles)
    assign e_v = u_rt.e_v; assign e_r = u_rt.e_r; assign e_d = u_rt.e_d;
`endif
    end else begin : g_flat
    wire d_v, a_flt, c_flt;
    wire [7:0]  d_t;
    reg inp_q;
    always @(posedge sk or negedge srs) if (!srs) inp_q <= 1'b0; else inp_q <= inp;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v), .c_done_tag(c_done_tag),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    wire [31:0] jobs;
    wire        bsy;
    // pin flops: VM responses (fixed latency + 1, the core counts responses), y through a registered-ready skid
    reg  [S_RD-1:0]     rs_v_q;
    reg  [S_RD*512-1:0] rs_d_q;
    always @(posedge sk) rs_d_q <= rs_d;
    always @(posedge sk or negedge srs) if (!srs) rs_v_q <= 0; else rs_v_q <= rs_v;
    wire yq_v, yq_r, y_ov, y_un;
    wire [NG*32-1:0] yq_d;
    ot_skid_buffer #(.WIDTH(NG*32), .DEPTH(2)) u_ysk (.clk(sk), .rst_n(srs), .in_valid(y_v), .in_ready(y_rdy),
        .in_data(y_d), .out_valid(yq_v), .out_ready(yq_r), .out_data(yq_d), .overflow(y_ov), .underflow(y_un));
    ot_s81_hc_core #(.NG(NG), .D(D), .S_RD(S_RD), .S_WR(S_WR), .LVM(LVM), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL),
                     .OQ(OQ), .MUT(MUT)) u_core (
        .clk(sk), .rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_done_v(d_v), .e_done_tag(d_t),
        .y_v(yq_v), .y_rdy(yq_r), .y_d(yq_d), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v_q), .rs_d(rs_d_q),
        .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d), .busy(bsy), .fault(c_flt), .fault_code(fcode),
        .st_jobs(jobs));
    assign flt = a_flt | c_flt | y_ov | y_un;
    end endgenerate
endmodule
