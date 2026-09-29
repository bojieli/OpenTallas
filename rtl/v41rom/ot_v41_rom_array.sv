`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_rom_array: N replicated ot_v41_rom_elem with the registered x broadcast and the ordered adding
// return tree (W10, docs/MICROARCH_MODEL.md build item 1).
//
//   x stream beat -> BST registered broadcast stages -> every element
//   element partials -> log2(N) levels of ot_v41_ret_node (golden-sibling FP32 adds, else forward),
//                       each followed by RST register stages -> ot_v41_ret_root -> finished rows
// Element e's ROM instance is named "e<e>" (behavioural model: +OT_ROM_DIR=<dir> loads
// <dir>/e<e>.viamap.hex).  N must be a power of two.
// ---------------------------------------------------------------------------
module ot_v41_rom_array #(
    parameter integer N = 8,
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer BST = 2,
    parameter integer RST = 1,
    parameter integer LV = 5,
    parameter integer RD = 16,         // return-node FIFO depth
    parameter integer ROOTD = 16,      // root combiner: pending partials and input queue (bench harness sizing)
    parameter integer BF16 = 0,
    parameter integer NB = 1,         // 2: elements are W1 macro pairs sharing one front end (N counts macros)
    parameter integer MTP = 0,        // 1: position-outer MTP (up to 6 positions)
    parameter integer EARLY = 0,      // 1: segment-tree early exit (fill cut)
    parameter integer BYPASS = 0      // 1: return-node forward bypass (fill cut)
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         cfg_v,
    input  wire [7:0]   cfg_e,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         go_bf,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    input  wire [2:0]   xb_pos,
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
    output wire         r_v,
    output wire [15:0]  r_row,
    output wire [2:0]   r_pos,
    output wire [31:0]  r_fp32,
    output wire [15:0]  r_bf16,
    output wire         r_e,
    output wire         busy,
    output wire         fault
);
    localparam integer L = $clog2(N);
    localparam integer XBW = 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10;
    // registered broadcast
    wire [XBW-1:0] xb_in = {xs_v, xs_p, xs_b, xs_sv, xs_q0, xs_e0, xs_q1, xs_e1};
    wire [5:0] pos_d;
    ot_hdc_delay #(.W(6), .D(BST)) u_pos (.clk(clk), .rst_n(rst_n), .d({xs_pos, xb_pos}), .q(pos_d));
    wire [XBW-1:0] xb;
    ot_hdc_delay #(.W(XBW), .D(BST)) u_xb (.clk(clk), .rst_n(rst_n), .d(xb_in), .q(xb));
    // BF16 x broadcast (1,024-bit slices + tags), same register stages
    localparam integer BBW = 3 + 4 + 32 + 1024;
    wire [BBW-1:0] bb;
    ot_hdc_delay #(.W(BBW), .D(BST)) u_bb (.clk(clk), .rst_n(rst_n), .d({xb_b, xb_sv, xb_u, xb_d}), .q(bb));
    wire [BST:0] bv_d;
    assign bv_d[0] = xb_v;
    wire [BST:0] gb_d;
    assign gb_d[0] = go_bf;
    wire [BST:0] go_d;
    assign go_d[0] = go;
    genvar g, l;
    generate for (g = 0; g < BST; g = g + 1) begin : g_go
        reg r;
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= go_d[g];
        assign go_d[g+1] = r;
    end endgenerate
    generate for (g = 0; g < BST; g = g + 1) begin : g_bv
        reg r, f;
        always @(posedge clk or negedge rst_n) if (!rst_n) begin r <= 1'b0; f <= 1'b0; end
                                               else begin r <= bv_d[g]; f <= gb_d[g]; end
        assign bv_d[g+1] = r;
        assign gb_d[g+1] = f;
    end endgenerate
    // x valid must reset: carry it on its own reset line
    wire [BST:0] xv_d;
    assign xv_d[0] = xs_v;
    generate for (g = 0; g < BST; g = g + 1) begin : g_xv
        reg r;
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= xv_d[g];
        assign xv_d[g+1] = r;
    end endgenerate

    // node streams: level 0 = elements
    wire        nv [0:L][0:N-1];
    wire [31:0] nt [0:L][0:N-1];
    wire [31:0] nd [0:L][0:N-1];
    wire        ne [0:L][0:N-1];
    wire [N/NB-1:0] e_busy, e_fault;
    wire [N-1:0] n_fault [0:L];
    wire [N-1:0] e_busy_m, e_fault_m;
    generate for (g = 0; g < N / NB; g = g + 1) begin : g_el
        wire [NB-1:0] pv, perr;
        wire [32*NB-1:0] pval;
        wire [16*NB-1:0] prow;
        wire [5*NB-1:0] pseg, pnseg;
        wire [3*NB-1:0] ppos;
        ot_v41_rom_elem #(.NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NB(NB), .MTP(MTP), .EARLY(EARLY),
                          .INSTANCE($sformatf("e%0d", g))) u_e (
            .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v && cfg_e == g), .cfg_a(cfg_a), .cfg_d(cfg_d),
            .go(go_d[BST]), .go_bf(gb_d[BST]), .xb_v(bv_d[BST]), .xb_b(bb[BBW-1 -: 3]), .xb_sv(bb[BBW-4 -: 4]),
            .xb_u(bb[1055:1024]), .xb_d(bb[1023:0]), .xs_v(xv_d[BST]), .xs_p(xb[XBW-2 -: 8]), .xs_b(xb[XBW-10 -: 3]),
            .xs_sv(xb[XBW-13 -: 2]), .xs_q0(xb[XBW-15 -: 256]), .xs_e0(xb[XBW-271 -: 10]),
            .xs_q1(xb[XBW-281 -: 256]), .xs_e1(xb[9:0]), .xs_pos(pos_d[5:3]), .xb_pos(pos_d[2:0]), .ppos(ppos),
            .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr),
            .busy(e_busy_m[g]), .fault(e_fault_m[g]));
        genvar m;
        for (m = 0; m < NB; m = m + 1) begin : g_m
            assign nv[0][NB*g+m] = pv[m];
            assign nt[0][NB*g+m] = {ppos[3*m +: 3], prow[16*m +: 16], pseg[5*m +: 5], 3'd0, pnseg[5*m +: 5]};
            assign nd[0][NB*g+m] = pval[32*m +: 32];
            assign ne[0][NB*g+m] = perr[m];
        end
    end endgenerate
    assign e_busy = e_busy_m[N/NB-1:0];
    assign e_fault = e_fault_m[N/NB-1:0];
    generate for (l = 0; l < L; l = l + 1) begin : g_lv
        for (g = 0; g < (N >> (l + 1)); g = g + 1) begin : g_n
            wire ov, oe, of;
            wire [31:0] ot;
            wire [31:0] od;
            ot_v41_ret_node #(.D(RD), .BYPASS(BYPASS)) u_n (.clk(clk), .rst_n(rst_n),
                .a_v(nv[l][2*g]), .a_t(nt[l][2*g]), .a_d(nd[l][2*g]), .a_e(ne[l][2*g]),
                .b_v(nv[l][2*g+1]), .b_t(nt[l][2*g+1]), .b_d(nd[l][2*g+1]), .b_e(ne[l][2*g+1]),
                .o_v(ov), .o_t(ot), .o_d(od), .o_e(oe), .fault(of));
            // RST register stages of return wire
            wire [64:0] rq;
            ot_hdc_delay #(.W(65), .D(RST)) u_rd (.clk(clk), .rst_n(rst_n), .d({ot, od, oe}), .q(rq));
            wire [RST:0] rv;
            assign rv[0] = ov;
            genvar r;
            for (r = 0; r < RST; r = r + 1) begin : g_rv
                reg q;
                always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= rv[r];
                assign rv[r+1] = q;
            end
            assign nv[l+1][g] = rv[RST];
            assign nt[l+1][g] = rq[64:33];
            assign nd[l+1][g] = rq[32:1];
            assign ne[l+1][g] = rq[0];
            assign n_fault[l][g] = of;
        end
    end endgenerate
    wire rf;
    ot_v41_ret_root #(.D(ROOTD), .QD(ROOTD)) u_root (.clk(clk), .rst_n(rst_n), .i_v(nv[L][0]), .i_t(nt[L][0]), .i_d(nd[L][0]),
        .i_e(ne[L][0]), .r_v(r_v), .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e), .fault(rf));
    reg nf;
    integer k, m;
    always @* begin
        nf = 1'b0;
        for (k = 0; k < L; k = k + 1)
            for (m = 0; m < (N >> (k + 1)); m = m + 1) nf = nf | n_fault[k][m];
    end
    assign fault = (|e_fault) | nf | rf;
    assign busy = |e_busy;
endmodule
