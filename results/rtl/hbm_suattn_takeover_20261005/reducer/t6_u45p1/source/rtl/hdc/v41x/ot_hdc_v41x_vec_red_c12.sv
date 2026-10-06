`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM SU 1.2 GHz (claude/hbm-su-attn-close-20261005): FILE SWAP of rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv (same module
// names ot_hdc_v41x_vec_red / ot_hdc_v41x_vred_op / ot_hdc_v41x_vsq; a source list names this file OR the original,
// never both; the original is unchanged).  Same function (R-ARITH chunk8 reductions, MAX, BF16 rounding, slots,
// TIME levels) as the original, bit for bit; the contract and pipeline are documented there.
//
// The reducer is written as NS = N / SL replicated SLICES (ot_hdc_v41x_vred_slice: SL lanes of IN, SQ, padding,
// CHAIN and the tree levels inside the slice) and one TOP (ot_hdc_v41x_vred_top: the control/tag pipeline, the tree
// levels above the slices, the level taps, TIME and OUT), so each piece hardens on its own (N = 1,024 as one block
// never finished global placement).  The slices duplicate the small control lines (valid, max, square) the top also
// carries: identical registers, identical values.
//
// Optional registers (every default 0 reproduces the original cycle for cycle):
//   RPAD  the padding multiplexer's output (c_x) is registered before the CHAIN                 +1
//   RSL   every slice output (its tree levels 0 .. LS, LS = log2(SL/8)) is registered: the slice boundary  +1
//   RTAP  the level-tap selection (tap_x / tap_t / tap_v) is registered before OUT and TIME        +1
//         (with RSL = 1 the tap's level select is also formed a cycle early and registered, no added cycle)
//   ROUT  the OUT stage's inputs (packed tap and TIME result) are registered, per-slot copies              +1
//         (ROUT = 1: a slot's o_addr / o_data are exact whenever its o_we is set and o_meta whenever o_ev is;
//         unwritten slots carry 0 instead of the original's leftover TIME result)
// All four are constant offsets on every result (packed taps and spanning TIME results alike):
//   result depth after the retire = 2 + MLAT + 7 ALAT + RPAD + RSL + RTAP + ROUT + ALAT lt (+ ALAT L spanning)
// i.e. D_RED = 2 + MLAT + 7*ALAT + RPAD + RSL + RTAP + ROUT and D_RSTEP = ALAT (RSL may be 0, 1 or 2).
// RSL = 2 adds a second boundary register at the top's entry (the slice keeps one), so every port of both pieces is
// register-direct (busy then comes from one register holding the same value as the original's OR).
// The status `fault` OR is registered twice more inside each slice when RSL >= 1 (per chunk, then the slice;
// refusals are counted, not timed).
// Fanout (timing only, same function): the max flag's last register in every ot_hdc_v41x_vred_op and the padding
// selects of every lane are kept-hierarchy copies (ot_hdc_v41x_red_kreg), <= 32 multiplexer loads each.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vec_red #(
    parameter integer N  = 64,          // lanes, a power of two >= 8
    parameter integer LV = 6,           // time levels: spanning segments of up to 2^LV vectors (1..7)
    parameter integer AW = 24,
    parameter integer MW = 64,
    parameter integer MLAT = 3,
    parameter integer ALAT = 3,
    parameter integer RPAD = 0,
    parameter integer RSL = 0,
    parameter integer RTAP = 0,
    parameter integer ROUT = 0,
    parameter integer SL = 64           // lanes a slice (capped at N), a power of two >= 8
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v_in,
    input  wire [N*32-1:0] x_in,
    input  wire [N-1:0]    live_in,
    input  wire            mx_in,
    input  wire            sq_in,
    input  wire [3:0]      lt_in,
    input  wire            span_in,
    input  wire [2:0]      l_in,
    input  wire            last_in,
    input  wire [7:0]      nres_in,
    input  wire            rnd_in,
    input  wire [AW-1:0]   rbase_in,
    input  wire [4:0]      rsh_in,
    input  wire [MW-1:0]   meta_in,
    output wire [N/8-1:0]  o_we,
    output wire [N/8*AW-1:0] o_addr,
    output wire [N/8*32-1:0] o_data,
    output wire [MW-1:0]   o_meta,
    output wire            o_ev,
    output wire            busy,
    output wire            fault
);
    generate if (LV < 1 || LV > 7) begin : g_lv_out_of_range
        ot_hdc_v41x_vec_LV_must_be_1_to_7 u_trap ();
    end endgenerate
    localparam integer S = (N < SL) ? N : SL;
    localparam integer NS = N / S;
    localparam integer SW = (2 * (S / 8) - 1) * 32;      // a slice's level words
    wire [NS*SW-1:0] lv;
    wire [NS-1:0]    sf;
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_sl
        ot_hdc_v41x_vred_slice #(.SL(S), .MLAT(MLAT), .ALAT(ALAT), .RPAD(RPAD), .RSL(RSL)) u_s (.clk(clk), .rst_n(rst_n),
            .v_in(v_in), .x_in(x_in[S*32*s +: S*32]), .live_in(live_in[S*s +: S]), .mx_in(mx_in), .sq_in(sq_in),
            .lv_o(lv[SW*s +: SW]), .fault_o(sf[s]));
    end endgenerate
    ot_hdc_v41x_vred_top #(.N(N), .LV(LV), .AW(AW), .MW(MW), .MLAT(MLAT), .ALAT(ALAT), .RPAD(RPAD), .RSL(RSL),
                           .RTAP(RTAP), .ROUT(ROUT), .SL(S)) u_t (.clk(clk), .rst_n(rst_n), .v_in(v_in), .mx_in(mx_in), .lt_in(lt_in),
        .span_in(span_in), .l_in(l_in), .last_in(last_in), .nres_in(nres_in), .rnd_in(rnd_in), .rbase_in(rbase_in),
        .rsh_in(rsh_in), .meta_in(meta_in), .lv_in(lv), .sfault_in(sf), .o_we(o_we), .o_addr(o_addr), .o_data(o_data),
        .o_meta(o_meta), .o_ev(o_ev), .busy(busy), .fault(fault));
endmodule

// ---------------------------------------------------------------------------
// SLICE: lanes 0 .. SL-1 of the reducer: IN, SQ, padding, (RPAD), CHAIN, tree levels 1 .. LS, (RSL) out.
// lv_o holds level 0 (SL/8 chunk sums), then level 1 (SL/16 words), ... level LS (one word).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vred_slice #(
    parameter integer SL = 64,
    parameter integer MLAT = 3,
    parameter integer ALAT = 3,
    parameter integer RPAD = 0,
    parameter integer RSL = 0
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         v_in,
    input  wire [SL*32-1:0]             x_in,
    input  wire [SL-1:0]                live_in,
    input  wire                         mx_in,
    input  wire                         sq_in,
    output wire [(2*(SL/8)-1)*32-1:0]   lv_o,
    output wire                         fault_o
);
    localparam integer NC = SL / 8;
    localparam integer LS = $clog2(NC);
    localparam integer K = (MLAT != 3 || ALAT != 3) ? 1 : 0;
    localparam integer DCH = 7 * ALAT;
    // -- IN
    reg  [SL*32-1:0] i_x;
    reg  [SL-1:0]    i_live;
    reg              i_v, i_sq, i_mx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i_v <= 1'b0; else i_v <= v_in;
    end
    always @(posedge clk) begin
        i_x <= x_in; i_live <= live_in; i_sq <= sq_in; i_mx <= mx_in;
    end
    // -- SQ, then the padding
    wire [SL*32-1:0] xsq, xd;
    wire [SL-1:0]    fsq;
    genvar l;
    generate for (l = 0; l < SL; l = l + 1) begin : g_sq
        ot_hdc_v41x_vsq #(.MLAT(MLAT)) u_sq (.clk(clk), .rst_n(rst_n), .v(i_v && i_sq && i_live[l]), .x(i_x[32*l +: 32]),
                              .y(xsq[32*l +: 32]), .fault(fsq[l]));
    end endgenerate
    wire [SL-1:0] q_live;
    wire          q_sq, q_mx;
    ot_hdc_delay #(.W(SL*32 + SL), .D(MLAT)) u_sqd (.clk(clk), .rst_n(rst_n), .d({i_x, i_live}), .q({xd, q_live}));
    // the padding selects: the max / square flags' last stage as one kept register a lane (<= 32 loads each), so
    // synthesis cannot merge them into one flip-flop driving every lane's multiplexer
    wire q_mx1, q_sq1;
    ot_hdc_delay #(.W(2), .D(MLAT - 1)) u_sqf (.clk(clk), .rst_n(rst_n), .d({i_mx, i_sq}), .q({q_mx1, q_sq1}));
    wire [SL-1:0] k_mx, k_sq;
    generate for (l = 0; l < SL; l = l + 1) begin : g_ksel
        ot_hdc_v41x_red_kreg #(.W(2)) u_k (.clk(clk), .rst_n(rst_n), .d({q_mx1, q_sq1}), .q({k_mx[l], k_sq[l]}));
    end endgenerate
    assign q_mx = k_mx[0];
    assign q_sq = k_sq[0];
    wire [MLAT:0] vq;
    ot_hdc_vline #(.D(MLAT)) u_vq (.clk(clk), .rst_n(rst_n), .v(i_v), .vd(vq));
    wire [SL*32-1:0] p_x;
    generate for (l = 0; l < SL; l = l + 1) begin : g_pad
        assign p_x[32*l +: 32] = !q_live[l] ? (k_mx[l] ? 32'hFF800000 : 32'd0) :
                                 k_sq[l] ? xsq[32*l +: 32] : xd[32*l +: 32];
    end endgenerate
    // -- RPAD
    wire [SL*32-1:0] c_x;
    wire             c_mx, c_v;
    ot_hdc_delay #(.W(SL*32 + 1), .D(RPAD)) u_pr (.clk(clk), .rst_n(rst_n), .d({p_x, q_mx}), .q({c_x, c_mx}));
    ot_hdc_delay #(.W(1), .D(RPAD), .RESET(1)) u_pv (.clk(clk), .rst_n(rst_n), .d(vq[MLAT]), .q(c_v));
    // -- CHAIN: chunk c = lanes 8c .. 8c+7, sequential
    wire [NC*32-1:0] chunk;
    wire [NC*7-1:0]  fch;
    wire [DCH:0]     vch, mxl;
    ot_hdc_vline #(.D(DCH)) u_vch (.clk(clk), .rst_n(rst_n), .v(c_v), .vd(vch));
    ot_hdc_vline #(.D(DCH)) u_mxl (.clk(clk), .rst_n(rst_n), .v(c_v && c_mx), .vd(mxl));
    genvar c, j;
    generate for (c = 0; c < NC; c = c + 1) begin : g_chunk
        wire [32*8-1:0] acc;
        assign acc[31:0] = c_x[32*(8*c) +: 32];
        for (j = 1; j < 8; j = j + 1) begin : g_step
            wire [31:0] xj;
            ot_hdc_delay #(.W(32), .D(ALAT * (j - 1))) u_xd (.clk(clk), .rst_n(rst_n),
                .d(c_x[32*(8*c + j) +: 32]), .q(xj));
            ot_hdc_v41x_vred_op #(.K(K), .LAT(ALAT)) u_op (.clk(clk), .rst_n(rst_n), .v(vch[ALAT * (j - 1)]),
                .mx(mxl[ALAT * (j - 1)]), .a(acc[32*(j-1) +: 32]), .b(xj), .y(acc[32*j +: 32]), .fault(fch[7*c + j - 1]));
        end
        assign chunk[32*c +: 32] = acc[32*7 +: 32];
    end endgenerate
    // the tree's max flag: the item's max bit along the chain (the original's tag bit, delayed with it)
    wire t_mx0;
    ot_hdc_delay #(.W(1), .D(DCH)) u_tmx (.clk(clk), .rst_n(rst_n), .d(c_mx), .q(t_mx0));
    // -- TREE inside the slice: levels 1 .. LS
    wire [NC*32-1:0] lvl [0:LS];
    wire [LS:0]      tv, tmx;
    wire [LS:0]      tf;
    assign lvl[0] = chunk;
    assign tv[0] = vch[DCH];
    assign tmx[0] = t_mx0;
    assign tf[0] = 1'b0;
    genvar lv, p;
    generate for (lv = 1; lv <= LS; lv = lv + 1) begin : g_tree
        wire [(NC >> lv)-1:0] pf;
        wire [ALAT:0] vd;
        ot_hdc_vline #(.D(ALAT)) u_vd (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .vd(vd));
        wire md;
        ot_hdc_delay #(.W(1), .D(ALAT)) u_md (.clk(clk), .rst_n(rst_n), .d(tmx[lv-1]), .q(md));
        wire [NC*32-1:0] q;
        for (p = 0; p < (NC >> lv); p = p + 1) begin : g_pair
            ot_hdc_v41x_vred_op #(.K(K), .LAT(ALAT)) u_op (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .mx(tmx[lv-1]),
                .a(lvl[lv-1][32*(2*p) +: 32]), .b(lvl[lv-1][32*(2*p+1) +: 32]), .y(q[32*p +: 32]), .fault(pf[p]));
        end
        assign q[NC*32-1 : (NC >> lv)*32] = 0;
        assign lvl[lv] = q;
        assign tv[lv] = vd[ALAT];
        assign tmx[lv] = md;
        assign tf[lv] = |pf;
    end endgenerate
    // -- OUT of the slice: every level's words (RSL: registered)
    wire [(2*NC-1)*32-1:0] lw;
    genvar h;
    generate for (h = 0; h <= LS; h = h + 1) begin : g_lw
        assign lw[32*(2*NC - (2*NC >> h)) +: 32*(NC >> h)] = lvl[h][0 +: 32*(NC >> h)];
    end endgenerate
    localparam integer RS = (RSL > 0) ? 1 : 0;      // the slice's own boundary register (RSL = 2: one more in the top)
    ot_hdc_delay #(.W((2*NC-1)*32), .D(RS)) u_lo (.clk(clk), .rst_n(rst_n), .d(lw), .q(lv_o));
    // the status OR (refusals are counted, not timed): RSL > 0 registers it per chunk first, then once more
    wire [NC-1:0] fch_or;
    wire [NC:0] fpart = {|tf, fch_or};
    generate for (h = 0; h < NC; h = h + 1) begin : g_for
        assign fch_or[h] = (|fsq[8*h +: 8]) || (|fch[7*h +: 7]);
    end endgenerate
    wire [NC:0] fpr;
    ot_hdc_delay #(.W(NC + 1), .D(RS), .RESET(1)) u_fp (.clk(clk), .rst_n(rst_n), .d(fpart), .q(fpr));
    ot_hdc_delay #(.W(1), .D(RS), .RESET(1)) u_fo (.clk(clk), .rst_n(rst_n), .d(|fpr), .q(fault_o));
endmodule

// ---------------------------------------------------------------------------
// TOP: the item's tag / valid pipeline (IN, SQ, RPAD, CHAIN, the slice levels, RSL), the tree levels above the
// slices, the taps (RTAP), TIME and OUT -- the original's logic from the tree up, on the slices' level words.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vred_top #(
    parameter integer N  = 64,
    parameter integer LV = 6,
    parameter integer AW = 24,
    parameter integer MW = 64,
    parameter integer MLAT = 3,
    parameter integer ALAT = 3,
    parameter integer RPAD = 0,
    parameter integer RSL = 0,
    parameter integer RTAP = 0,
    parameter integer ROUT = 0,
    parameter integer SL = 64
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v_in,
    input  wire            mx_in,
    input  wire [3:0]      lt_in,
    input  wire            span_in,
    input  wire [2:0]      l_in,
    input  wire            last_in,
    input  wire [7:0]      nres_in,
    input  wire            rnd_in,
    input  wire [AW-1:0]   rbase_in,
    input  wire [4:0]      rsh_in,
    input  wire [MW-1:0]   meta_in,
    input  wire [(N/SL)*(2*(SL/8)-1)*32-1:0] lv_in,
    input  wire [N/SL-1:0] sfault_in,
    output reg  [N/8-1:0]  o_we,
    output reg  [N/8*AW-1:0] o_addr,
    output reg  [N/8*32-1:0] o_data,
    output reg  [MW-1:0]   o_meta,
    output reg             o_ev,
    output wire            busy,
    output reg             fault
);
    localparam integer NC = N / 8;
    localparam integer LC = $clog2(NC);
    localparam integer NS = N / SL;
    localparam integer SC = SL / 8;                 // chunks a slice
    localparam integer LS = $clog2(SC);             // tree levels inside a slice
    localparam integer SW = (2 * SC - 1) * 32;
    localparam integer K = (MLAT != 3 || ALAT != 3) ? 1 : 0;
    localparam integer DCH = 7 * ALAT;
    localparam integer TAG = 1 + 4 + 1 + 3 + 1 + 8 + 1 + AW + 5 + MW;
    // -- IN, SQ, RPAD, CHAIN: the tag and the valid
    reg  [TAG-1:0]  i_t;
    reg             i_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i_v <= 1'b0; else i_v <= v_in;
    end
    always @(posedge clk) i_t <= {mx_in, lt_in, span_in, l_in, last_in, nres_in, rnd_in, rbase_in, rsh_in, meta_in};
    wire [TAG-1:0] q_t, c_t, ct;
    ot_hdc_delay #(.W(TAG), .D(MLAT)) u_sqd (.clk(clk), .rst_n(rst_n), .d(i_t), .q(q_t));
    wire [MLAT:0] vq;
    ot_hdc_vline #(.D(MLAT)) u_vq (.clk(clk), .rst_n(rst_n), .v(i_v), .vd(vq));
    wire c_v;
    ot_hdc_delay #(.W(TAG), .D(RPAD)) u_pt (.clk(clk), .rst_n(rst_n), .d(q_t), .q(c_t));
    ot_hdc_delay #(.W(1), .D(RPAD), .RESET(1)) u_pv (.clk(clk), .rst_n(rst_n), .d(vq[MLAT]), .q(c_v));
    wire [DCH:0] vch;
    ot_hdc_vline #(.D(DCH)) u_vch (.clk(clk), .rst_n(rst_n), .v(c_v), .vd(vch));
    ot_hdc_delay #(.W(TAG), .D(DCH)) u_ct (.clk(clk), .rst_n(rst_n), .d(c_t), .q(ct));
    // -- the slices' levels 0 .. LS at the original timing (tv, tt), then the slice boundary (RSL)
    wire [LC:0]      tv, tb;              // valids of the levels, at this block's timing (RSL included)
    wire [TAG-1:0]   tt [0:LC];
    wire [NC*32-1:0] lvl [0:LC];
    wire [LC:0]      tf;
    wire [LS:0]      sv0;
    wire [TAG-1:0]   st0 [0:LS];
    wire [LS:0]      sb0;
    assign sv0[0] = vch[DCH];
    assign st0[0] = ct;
    assign sb0[0] = 1'b0;
    genvar lv, p, s;
    generate for (lv = 1; lv <= LS; lv = lv + 1) begin : g_slv
        wire [ALAT:0] vd;
        ot_hdc_vline #(.D(ALAT)) u_vd (.clk(clk), .rst_n(rst_n), .v(sv0[lv-1]), .vd(vd));
        ot_hdc_delay #(.W(TAG), .D(ALAT)) u_td (.clk(clk), .rst_n(rst_n), .d(st0[lv-1]), .q(st0[lv]));
        assign sv0[lv] = vd[ALAT];
        assign sb0[lv] = |vd[ALAT-1:0];
    end endgenerate
    // RSL = 2: the top registers the slices' words once more on entry (every top input register-direct)
    localparam integer RT = (RSL > 1) ? RSL - 1 : 0;
    wire [NS*SW-1:0] lv_d;
    wire [NS-1:0]    sf_d;
    ot_hdc_delay #(.W(NS*SW), .D(RT)) u_lvd (.clk(clk), .rst_n(rst_n), .d(lv_in), .q(lv_d));
    ot_hdc_delay #(.W(NS), .D(RT), .RESET(1)) u_sfd (.clk(clk), .rst_n(rst_n), .d(sfault_in), .q(sf_d));
    wire [LS:0] rsl_live, rsl_next;
    wire [LC:0]    pre_v;
    wire [TAG-1:0] pre_t [0:LC];
    generate for (lv = 0; lv <= LS; lv = lv + 1) begin : g_rsl
        if (RSL > 0) begin : g_r
            wire [RSL:0] vr;
            ot_hdc_vline #(.D(RSL)) u_v (.clk(clk), .rst_n(rst_n), .v(sv0[lv]), .vd(vr));
            wire [TAG-1:0] tp;
            ot_hdc_delay #(.W(TAG), .D(RSL - 1)) u_tp (.clk(clk), .rst_n(rst_n), .d(st0[lv]), .q(tp));
            ot_hdc_delay #(.W(TAG), .D(1)) u_t (.clk(clk), .rst_n(rst_n), .d(tp), .q(tt[lv]));
            assign tv[lv] = vr[RSL];
            assign rsl_live[lv] = |vr[RSL:1];
            assign rsl_next[lv] = |vr[RSL-1:0];
            assign pre_v[lv] = vr[RSL-1];
            assign pre_t[lv] = tp;
        end else begin : g_w0
            assign tv[lv] = sv0[lv];
            assign tt[lv] = st0[lv];
            assign rsl_live[lv] = 1'b0;
            assign rsl_next[lv] = 1'b0;
            assign pre_v[lv] = 1'b0;
            assign pre_t[lv] = {TAG{1'b0}};
        end
        assign tb[lv] = sb0[lv];
        assign tf[lv] = 1'b0;
        // level lv's words: node q is word (q mod (SC >> lv)) of slice q / (SC >> lv)
        for (p = 0; p < (NC >> lv); p = p + 1) begin : g_w
            assign lvl[lv][32*p +: 32] =
                lv_d[SW*(p / (SC >> lv)) + 32*(2*SC - (2*SC >> lv)) + 32*(p % (SC >> lv)) +: 32];
        end
        if ((NC >> lv) < NC) begin : g_z
            assign lvl[lv][NC*32-1 : (NC >> lv)*32] = 0;
        end
    end endgenerate
    // -- the tree above the slices: levels LS+1 .. LC
    generate for (lv = LS + 1; lv <= LC; lv = lv + 1) begin : g_tree
        wire [(NC >> lv)-1:0] pf;
        wire [ALAT:0] vd;
        ot_hdc_vline #(.D(ALAT)) u_vd (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .vd(vd));
        wire [TAG-1:0] td, tdp;
        ot_hdc_delay #(.W(TAG), .D(ALAT - 1)) u_tdp (.clk(clk), .rst_n(rst_n), .d(tt[lv-1]), .q(tdp));
        ot_hdc_delay #(.W(TAG), .D(1)) u_td (.clk(clk), .rst_n(rst_n), .d(tdp), .q(td));
        assign pre_v[lv] = vd[ALAT-1];
        assign pre_t[lv] = tdp;
        wire [NC*32-1:0] q;
        for (p = 0; p < (NC >> lv); p = p + 1) begin : g_pair
            ot_hdc_v41x_vred_op #(.K(K), .LAT(ALAT)) u_op (.clk(clk), .rst_n(rst_n), .v(tv[lv-1]), .mx(tt[lv-1][TAG-1]),
                .a(lvl[lv-1][32*(2*p) +: 32]), .b(lvl[lv-1][32*(2*p+1) +: 32]), .y(q[32*p +: 32]), .fault(pf[p]));
        end
        assign q[NC*32-1 : (NC >> lv)*32] = 0;
        assign lvl[lv] = q;
        assign tv[lv] = vd[ALAT];
        assign tt[lv] = td;
        assign tf[lv] = |pf;
        assign tb[lv] = |vd[ALAT-1:0];
    end endgenerate

    // -- taps: the item at level j with lt == j (RTAP: registered)
    // RSL >= 1: hit is formed a cycle early from the levels' previous stages and registered, one kept copy per
    // result word (<= 32 multiplexer loads) and one for the tag / valid (same values as the combinational hit)
    integer h, kw;
    reg  [NC*32-1:0] tap_xc;
    reg  [TAG-1:0]   tap_tc;
    reg              tap_vc;
    wire             tap_multi;
    generate if (RSL >= 1) begin : g_hitr
        reg  [LC:0] hp;
        always @(*) for (h = 0; h <= LC; h = h + 1) hp[h] = pre_v[h] && (pre_t[h][TAG-2 -: 4] == h);
        wire [LC:0] hit;
        wire [(LC+1)*NC-1:0] hw;          // level h's copy for word g at h*NC + g
        ot_hdc_v41x_red_kreg #(.W(LC + 1)) u_h (.clk(clk), .rst_n(rst_n), .d(hp), .q(hit));
        genvar g, hh;
        for (g = 0; g < NC; g = g + 1) begin : g_w
            wire [LC:0] hq;
            ot_hdc_v41x_red_kreg #(.W(LC + 1)) u_hw (.clk(clk), .rst_n(rst_n), .d(hp), .q(hq));
            for (hh = 0; hh <= LC; hh = hh + 1) begin : g_b
                assign hw[hh*NC + g] = hq[hh];
            end
        end
        always @(*) begin
            tap_vc = 1'b0; tap_xc = {NC*32{1'b0}}; tap_tc = {TAG{1'b0}};
            for (h = 0; h <= LC; h = h + 1) if (hit[h]) begin tap_vc = 1'b1; tap_tc = tt[h]; end
            for (h = 0; h <= LC; h = h + 1) for (kw = 0; kw < NC; kw = kw + 1)
                if (hw[h*NC + kw]) tap_xc[32*kw +: 32] = lvl[h][32*kw +: 32];
        end
        assign tap_multi = ($countones(hit) > 1);
    end else begin : g_hitc
        reg  [LC:0] hit;
        always @(*) for (h = 0; h <= LC; h = h + 1) hit[h] = tv[h] && (tt[h][TAG-2 -: 4] == h);
        always @(*) begin
            tap_vc = 1'b0; tap_xc = {NC*32{1'b0}}; tap_tc = {TAG{1'b0}};
            for (h = 0; h <= LC; h = h + 1) if (hit[h]) begin tap_vc = 1'b1; tap_xc = lvl[h]; tap_tc = tt[h]; end
        end
        assign tap_multi = ($countones(hit) > 1);
    end endgenerate
    wire [NC*32-1:0] tap_x;
    wire [TAG-1:0]   tap_t;
    wire             tap_v;
    ot_hdc_delay #(.W(NC*32 + TAG), .D(RTAP)) u_tap (.clk(clk), .rst_n(rst_n), .d({tap_xc, tap_tc}), .q({tap_x, tap_t}));
    ot_hdc_delay #(.W(1), .D(RTAP), .RESET(1)) u_tapv (.clk(clk), .rst_n(rst_n), .d(tap_vc), .q(tap_v));
    wire pk_v = tap_v && !tap_t[TAG-6];
    wire tm_v = tap_v && tap_t[TAG-6];

    // -- TIME (as the original)
    wire [31:0]    sv [0:LV];
    wire [LV:0]    sval;
    wire [TAG-1:0] st [0:LV];
    wire [LV:0]    sf, sb, sx, bn;          // bn: the level's registers' next-cycle liveness
    assign bn[0] = 1'b0;
    assign sv[0] = tap_x[31:0];
    assign sval[0] = tm_v;
    assign st[0] = tap_t;
    assign sf[0] = 1'b0;
    assign sb[0] = 1'b0;
    assign sx[0] = 1'b0;
    genvar t;
    generate for (t = 1; t <= LV; t = t + 1) begin : g_time
        wire [31:0]    in_x = sv[t-1];
        wire           in_v = sval[t-1] && !sx[t-1];
        wire [TAG-1:0] in_t = st[t-1];
        wire           in_last = in_t[TAG-10];
        reg  [31:0] held;
        reg         held_v;
        wire pair = in_v && held_v;
        wire pass = in_v && !held_v && in_last;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) held_v <= 1'b0;
            else if (pair) held_v <= 1'b0;
            else if (in_v && !pass) held_v <= 1'b1;
        end
        always @(posedge clk) if (in_v && !held_v && !pass) held <= in_x;
        wire [31:0] s_, pd;
        wire f;
        ot_hdc_v41x_vred_op #(.K(K), .LAT(ALAT)) u_op (.clk(clk), .rst_n(rst_n), .v(pair), .mx(in_t[TAG-1]), .a(held), .b(in_x),
                                  .y(s_), .fault(f));
        wire [TAG+1-1:0] od;
        ot_hdc_delay #(.W(TAG + 1 + 32), .D(ALAT)) u_od (.clk(clk), .rst_n(rst_n), .d({in_t, pair, in_x}), .q({od, pd}));
        wire [ALAT:0] vd;
        ot_hdc_vline #(.D(ALAT)) u_vd (.clk(clk), .rst_n(rst_n), .v(pair || pass), .vd(vd));
        assign sv[t] = od[0] ? s_ : pd;
        assign sval[t] = vd[ALAT];
        assign st[t] = od[TAG:1];
        assign sx[t] = vd[ALAT] && od[TAG:1][TAG-10] && (od[TAG:1][TAG-7 -: 3] == t);
        assign sf[t] = f;
        assign sb[t] = held_v || (|vd[ALAT-1:0]);
        assign bn[t] = (pair ? 1'b0 : (in_v && !pass) ? 1'b1 : held_v) || (|vd[ALAT-1:0]);
    end endgenerate
    wire top_bad = sval[LV] && !sx[LV];
    integer e;
    reg  [31:0]   tr_x;
    reg  [TAG-1:0] tr_t;
    reg           tr_v;
    always @(*) begin
        tr_v = 1'b0; tr_x = 32'd0; tr_t = {TAG{1'b0}};
        for (e = 1; e <= LV; e = e + 1) if (sx[e]) begin tr_v = 1'b1; tr_x = sv[e]; tr_t = st[e]; end
    end
    wire res_multi = (pk_v && tr_v) || ($countones(sx) > 1);

    // -- OUT (as the original).  ROUT = 1: the OUT stage's inputs (the packed tap and the TIME result) are
    // registered first, the per-slot fields as kept copies, one per GS slots, so neither the TIME result nor the
    // tag fans out to every slot from one register (+1 on every result)
    localparam integer GS = 4;
    localparam integer NG = (NC + GS - 1) / GS;
    localparam integer BW = 1 + TAG + 1 + 32 + TAG;          // {pk_v, tap_t, tr_v, tr_x, tr_t}
    wire [NC*32-1:0] ox;                                      // the tap words OUT reads
    wire [NG*BW-1:0] ob;                                      // per slot group: the OUT bundle
    generate if (ROUT > 0) begin : g_ro
        ot_hdc_delay #(.W(NC*32), .D(1)) u_ox (.clk(clk), .rst_n(rst_n), .d(tap_x), .q(ox));
        genvar gg;
        // the TIME result only ever writes slot 0 (o_we = tr_v && k == 0): only group 0's copy carries it, so it
        // does not fan out across the slots; the other groups' slots hold 0 in o_addr / o_data while they are
        // not written (o_we = 0; the original left the TIME result there, which no consumer reads)
        for (gg = 0; gg < NG; gg = gg + 1) begin : g_c
            ot_hdc_v41x_red_kreg #(.W(BW)) u_b (.clk(clk), .rst_n(rst_n),
                .d((gg == 0) ? {pk_v, tap_t, tr_v, tr_x, tr_t} : {pk_v, tap_t, 1'b0, 32'd0, {TAG{1'b0}}}),
                .q(ob[gg*BW +: BW]));
        end
    end else begin : g_rw
        genvar gg;
        assign ox = tap_x;
        for (gg = 0; gg < NG; gg = gg + 1) begin : g_c
            assign ob[gg*BW +: BW] = {pk_v, tap_t, tr_v, tr_x, tr_t};
        end
    end endgenerate
    // the valid flags as a reset register (bundle copy 0 carries them for the slots; this one for busy / o_ev)
    wire opk, otr;
    ot_hdc_delay #(.W(2), .D(ROUT), .RESET(1)) u_ov (.clk(clk), .rst_n(rst_n), .d({pk_v, tr_v}), .q({opk, otr}));
    wire [NC*AW-1:0] pk_addr;
    wire [NC*32-1:0] pk_bf;
    wire [NG*16-1:0] tr_hi;
    genvar ko;
    generate for (ko = 0; ko < NC; ko = ko + 1) begin : g_out
        wire unused_c;
        wire [31:0] xk = ox[32*ko +: 32];
        wire [TAG-1:0] bt = ob[(ko/GS)*BW + TAG + 33 +: TAG];
        wire [15:0] hi;
        ot_hdc_kadd #(.W(AW), .K(K)) u_ad (.a(bt[TAG-20 -: AW]), .b(ko << bt[TAG-20-AW -: 5]), .cin(1'b0),
                                           .s(pk_addr[ko*AW +: AW]), .cout(unused_c));
        ot_hdc_kinc #(.W(16), .K(K)) u_bf (.a(xk[31:16]), .inc(xk[15] & (xk[16] | (|xk[14:0]))), .y(hi));
        assign pk_bf[32*ko +: 32] = {hi, 16'd0};
    end
    for (ko = 0; ko < NG; ko = ko + 1) begin : g_trh
        wire [31:0] gx = ob[ko*BW + TAG +: 32];
        ot_hdc_kinc #(.W(16), .K(K)) u_trbf (.a(gx[31:16]), .inc(gx[15] & (gx[16] | (|gx[14:0]))), .y(tr_hi[16*ko +: 16]));
    end endgenerate
    // per slot: the OUT bundle of its group, unpacked
    wire [NC-1:0]     s_pk, s_tv;
    wire [NC*TAG-1:0] s_tt, s_rt;
    wire [NC*32-1:0]  s_rx;
    generate for (ko = 0; ko < NC; ko = ko + 1) begin : g_su
        assign {s_pk[ko], s_tt[ko*TAG +: TAG], s_tv[ko], s_rx[32*ko +: 32], s_rt[ko*TAG +: TAG]} = ob[(ko/GS)*BW +: BW];
    end endgenerate
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_we <= 0; o_ev <= 1'b0; fault <= 1'b0; end
        else begin
            for (k = 0; k < NC; k = k + 1)
                o_we[k] <= s_pk[k] ? (k < s_tt[k*TAG + TAG-11 -: 8]) : (s_tv[k] && k == 0);
            o_ev <= opk || otr;
            fault <= (|sf_d) || (|tf) || (|sf) || top_bad || tap_multi || res_multi;
        end
    end
    always @(posedge clk) begin
        for (k = 0; k < NC; k = k + 1) begin
            o_addr[k*AW +: AW] <= s_pk[k] ? pk_addr[k*AW +: AW] : s_rt[k*TAG + TAG-20 -: AW];
            o_data[32*k +: 32] <= s_pk[k] ? (s_tt[k*TAG + TAG-19] ? pk_bf[32*k +: 32] : ox[32*k +: 32])
                                          : (s_rt[k*TAG + TAG-19] ? {tr_hi[16*(k/GS) +: 16], 16'd0} : s_rx[32*k +: 32]);
        end
        o_meta <= s_pk[0] ? s_tt[MW-1:0] : s_rt[MW-1:0];
    end
    wire busy_c = i_v || (|vq) || c_v || (|vch) || (|sv0) || (|rsl_live) || (|tv) || (|tb) || tap_v || (|sval) ||
                  (|sb) || (|o_we) || ((ROUT > 0) ? (opk || otr) : 1'b0);
    // RSL >= 1: busy is one register holding the same value: every term of busy_c is (or is implied by) a register,
    // so busy(t+1) is the OR of those registers' next values, formed here from their inputs
    generate if (RSL >= 1) begin : g_bq
        wire bnext = v_in || (|vq[MLAT-1:0]) || ((RPAD > 0) ? vq[MLAT] : 1'b0) || (|vch[DCH-1:0]) || (|sb0) ||
                     (|rsl_next) || (|tb) || ((RTAP > 0) ? tap_vc : 1'b0) || (|bn) ||
                     ((ROUT > 0) ? (pk_v || tr_v || (opk ? (ob[TAG+33 + (TAG-11) -: 8] != 8'd0) : otr))
                                 : (pk_v ? (tap_t[TAG-11 -: 8] != 8'd0) : tr_v));
        reg bq;
        always @(posedge clk or negedge rst_n) if (!rst_n) bq <= 1'b0; else bq <= bnext;
        assign busy = bq;
    end else begin : g_bc
        assign busy = busy_c;
    end endgenerate
endmodule

module ot_hdc_v41x_vred_op #(
    parameter integer K = 0,
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire        mx,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    /* verilator no_inline_module */
    function automatic [31:0] okey(input [31:0] x);
        okey = x[31] ? ~x : {1'b1, x[30:0]};
    endfunction
    wire [31:0] ys, ym;
    wire mxd;
    wire ab_ge;
    ot_hdc_qadd_lat #(.KEEP(K), .LAT(LAT)) u_add (clk, rst_n, v && !mx, a, b, ys, fault);
    ot_hdc_kge #(.W(32), .K(K)) u_ge (.a(okey(a)), .b(okey(b)), .ge(ab_ge));
    ot_hdc_delay #(.W(32), .D(LAT)) u_m (.clk(clk), .rst_n(rst_n), .d(ab_ge ? a : b), .q(ym));
    // the result select's last stage in its own kept register: every op's copy stays a separate cell (the ops of
    // one CHAIN step / TREE level carry the same flag, and merged it drove hundreds of multiplexer bits)
    wire mx1;
    ot_hdc_delay #(.W(1), .D(LAT - 1)) u_mx (.clk(clk), .rst_n(rst_n), .d(mx), .q(mx1));
    ot_hdc_v41x_red_kreg #(.W(1)) u_mk (.clk(clk), .rst_n(rst_n), .d(mx1), .q(mxd));
    assign y = mxd ? ym : ys;
endmodule

// a register in its own kept hierarchy (as rtl/hdc/v41x/ot_hdc_v41x_kreg.sv, own name so this file needs no extra
// source): duplicated copies of one flag stay separate cells
(* keep_hierarchy *)
module ot_hdc_v41x_red_kreg #(parameter integer W = 1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output reg [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

module ot_hdc_v41x_vsq #(
    parameter integer MLAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        fault
);
    /* verilator no_inline_module */
    ot_hdc_qmul_lat #(MLAT) u (clk, rst_n, v, x, x, y, fault);
endmodule
