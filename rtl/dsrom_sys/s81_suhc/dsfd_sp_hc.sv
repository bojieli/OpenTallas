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
    parameter integer HIER = 0,                          // 0: flat engine ot_s81_hc_core; 1: hierarchical slab = pin tile
    parameter integer NCOL = 3, GS = 8, S_RT = 4         //    ot_s81_hc_cpin + combine ot_s81_hc_comb + column roots
                                                         //    ot_s81_hc_croot (chains 0 / 2) + 3 chains of ot_s81_hc_ctile
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
    // hierarchical slab layout (HIER=1)
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    localparam integer NL_ = 4 * NS, LT_ = $clog2(NL_);
    // the sum-tree node ownership (as ot_s81_hc_stree): exported subtrees of chains 0 / 2
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT_ - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL_) % NS;
            owner = 3;
            if (sz <= NS) begin
                if (L0 > 0 && s0 >= B0 && s0 + sz <= B0 + L0) owner = 0;
                else if (L1 > 0 && s0 >= B1 && s0 + sz <= B1 + L1) owner = 1;
                else if (L2 > 0 && s0 >= B2 && s0 + sz <= B2 + L2) owner = 2;
            end
        end
    endfunction
    function automatic integer expd(input integer n, input integer c);
        expd = (owner(n) == c) && (c != 3) && (n == 1 || owner(n / 2) != c);
    endfunction
    function automatic integer exidx(input integer n, input integer c);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m, c); exidx = t; end
    endfunction
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL_, c);
    endfunction
    function automatic integer imoff(input integer c);
        integer t, cc;
        begin t = 0; for (cc = 0; cc < c; cc = cc + 1) t = t + necnt(cc); imoff = t; end
    endfunction
    wire e_v, e_r;
    wire [83:0] e_d;
    generate if (HIER) begin : g_hier
    // hierarchical slab: centre pin tile + combine tile + outer column roots (chains 0 / 2) + 3 column chains
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer RDW = S_RT + 24 * S_RT + 8 + 512 * S_RT;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4, WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    wire        n_cmd_v, n_done_v, n_inp, n_flt, n_online, n_yacc, n_ypop, yacc_w, yacc_e;
    wire [83:0] n_cmd_d;
    wire [7:0]  n_done_tag;
    wire [3:0]  n_fcode;
    wire [S_RD-1:0]     n_rq_v, n_rs_v;
    wire [S_RD*14-1:0]  n_rq_row;
    wire [S_RD*512-1:0] n_rs_d;
    wire [YS1-1:0]      n_y;
    wire [YS1-1:0]      y_s1;
    if (L1 > 0) begin : g_y1
        assign y_s1 = y_d[B1 * GS * 32 +: YS1];
    end else begin : g_ny1
        assign y_s1 = 1'b0;
    end
    ot_s81_hc_cpin #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD)) u_cp (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .c_cmd_v(c_cmd_v), .c_cmd_d(c_cmd_d), .c_done_v(c_done_v),
        .c_done_tag(c_done_tag), .inp(inp), .rq_v(rq_v), .rq_row(rq_row), .rs_v(rs_v), .rs_d(rs_d), .flt(flt),
        .online(online), .fcode(fcode), .y_v(y_v), .y_rdy(y_rdy), .y_s(y_s1), .yacc_w(yacc_w), .yacc_e(yacc_e),
        .n_cmd_v(n_cmd_v), .n_cmd_d(n_cmd_d), .n_done_v(n_done_v), .n_done_tag(n_done_tag), .n_inp(n_inp),
        .n_rq_v(n_rq_v), .n_rq_row(n_rq_row), .n_rs_v(n_rs_v), .n_rs_d(n_rs_d), .n_flt(n_flt), .n_online(n_online),
        .n_fcode(n_fcode), .n_yacc(n_yacc), .n_y(n_y), .n_ypop(n_ypop));
    wire [FVW-1:0]   w_fv, e_fv;
    wire [FSW-1:0]   w_fd, e_fd;
    wire [4*WSL-1:0] w_w, e_w;
    wire [RVW-1:0]   w_rv, e_rv;
    wire [RDW-1:0]   w_rd, e_rd;
    wire             w_flt, e_flt;
    wire [NCOL-1:0]     ch_rst;
    wire [NCOL*FVW-1:0] ch_fv;
    wire [NCOL*FDW-1:0] ch_fd;
    wire [NCOL*RVW-1:0] ch_rv;
    wire [NCOL*RDW-1:0] ch_rd;
    localparam integer NE0 = (necnt(0) > 0) ? necnt(0) : 1, NE2 = (necnt(2) > 0) ? necnt(2) : 1;
    wire [NE0*32-1:0] w_ex;
    wire [NE2*32-1:0] e_ex;
    ot_s81_hc_comb #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_WR(S_WR), .S_RT(S_RT), .ML(ML), .AL(AL),
                     .MUT(MUT), .AMUT(AMUT)) u_cb (
        .cck(cck), .crs(crs), .sk(sk), .srs(srs), .n_cmd_v(n_cmd_v), .n_cmd_d(n_cmd_d), .n_done_v(n_done_v),
        .n_done_tag(n_done_tag), .n_inp(n_inp), .n_rq_v(n_rq_v), .n_rq_row(n_rq_row), .n_rs_v(n_rs_v), .n_rs_d(n_rs_d),
        .n_flt(n_flt), .n_online(n_online), .n_fcode(n_fcode), .n_yacc(n_yacc), .n_y(n_y), .n_ypop(n_ypop),
        .w_fv(w_fv), .w_fd(w_fd), .w_w(w_w), .w_rv(w_rv), .w_rd(w_rd), .w_ex(w_ex), .w_flt(w_flt),
        .e_fv(e_fv), .e_fd(e_fd), .e_w(e_w), .e_rv(e_rv), .e_rd(e_rd), .e_ex(e_ex), .e_flt(e_flt),
        .ch_rst(ch_rst[1]), .ch_fv(ch_fv[FVW +: FVW]), .ch_fd(ch_fd[FDW +: FDW]), .ch_rv(ch_rv[RVW +: RVW]),
        .ch_rd(ch_rd[RDW +: RDW]));
    ot_s81_hc_croot #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .AL(AL), .C(0)) u_rw (
        .sk(sk), .srs(srs), .y_s(y_d[B0 * GS * 32 +: L0 * GS * 32]), .wq_v(wq_v[3:0]), .wq_row(wq_row[0 +: 56]),
        .wq_mask(wq_mask[0 +: 64]), .wq_d(wq_d[0 +: 2048]), .yacc(yacc_w), .s_fv(w_fv), .s_fd(w_fd), .s_w(w_w),
        .s_rv(w_rv), .s_rd(w_rd), .s_ex(w_ex), .s_flt(w_flt), .ch_rst(ch_rst[0]), .ch_fv(ch_fv[0 +: FVW]),
        .ch_fd(ch_fd[0 +: FDW]), .ch_rv(ch_rv[0 +: RVW]), .ch_rd(ch_rd[0 +: RDW]));
    ot_s81_hc_croot #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .AL(AL), .C(2)) u_re (
        .sk(sk), .srs(srs), .y_s(y_d[B2 * GS * 32 +: L2 * GS * 32]), .wq_v(wq_v[7:4]), .wq_row(wq_row[56 +: 56]),
        .wq_mask(wq_mask[64 +: 64]), .wq_d(wq_d[2048 +: 2048]), .yacc(yacc_e), .s_fv(e_fv), .s_fd(e_fd), .s_w(e_w),
        .s_rv(e_rv), .s_rd(e_rd), .s_ex(e_ex), .s_flt(e_flt), .ch_rst(ch_rst[2]), .ch_fv(ch_fv[2 * FVW +: FVW]),
        .ch_fd(ch_fd[2 * FDW +: FDW]), .ch_rv(ch_rv[2 * RVW +: RVW]), .ch_rd(ch_rd[2 * RDW +: RDW]));
    genvar c, p;
    for (c = 0; c < NCOL; c = c + 1) begin : g_c
        localparam integer LC = (c == 0) ? L0 : (c == 1) ? L1 : L2;
        localparam integer BC = (c == 0) ? B0 : (c == 1) ? B1 : B2;
        if (LC > 0) begin : g_live
            wire [FVW-1:0] fvo [0:LC-1];
            wire [FDW-1:0] fdo [0:LC-1];
            wire [RVW-1:0] rvo [0:LC-1];
            wire [RDW-1:0] rdo [0:LC-1];
            wire           rso [0:LC-1];
            for (p = 0; p < LC; p = p + 1) begin : g_p
                localparam [7:0] TID = BC + p;
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
    assign e_v = u_cb.e_v; assign e_r = u_cb.e_r; assign e_d = u_cb.e_d;
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
