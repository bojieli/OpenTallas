`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT-L1 (2026-10-17): dsdv_gunit_l1f -- router select FRONT leaf of dsdv_gunit (hardened once, 4 instances
// beside the stack leaf L1; instance q owns lanes 16 q .. 16 q + 15 of every 64-lane select beat, i.e. score index
// i = 64 b + 16 q + k, b = 0..6, k = 0..15).  The leaf does not know q: everything q-specific arrives on its own wires
// (the stack's per-front SC word enables / lane counts / bias-row enables, the collector's per-front gather hits), and
// its records carry the LOCAL index {b, k} (the collector inserts q).
//   SC store   112 x binary32 unbiased scores (written from the stack's registered SC beats; word j of a beat with row r
//              is index 7 r + j, written iff the stack's enable for this front says so);
//   bias       2 x ot_sram_1r1w_128x256_m1_r2c2 (macro m = lanes 8 m .. 8 m + 7; address {set, b}; bias row
//              r = 8 b + 2 q + m), read one beat ahead (the stack's prefetch address), captured in s_bias;
//   select     per beat: 16 x add(score, bias) (ot_hdc_qadd_lat LAT 4, the golden's RNE add), key register, 2 x bitonic
//              sort8 at two compare-exchanges per stage (3 stages), merge8 (2 stages) -> this front's top 6 of the beat;
//   gather     on the collector's request: the unbiased scores of the chosen experts held here (zero elsewhere), for
//              the routing weights (one row instead of the old 28-row score stream).
// Timing (edges): stack control / SC in-flops E, s_val / s_bias E+1, adders E+6, key E+7, sort E+10, merge (output
// register, also the gather output) E+12.  Fixed: no handshakes.  Every input lands in a flop, every output leaves one.
// MUT (bench only): 1 = bias not added.
// S81U-GUNIT-L1b (10-17): (a) rst_n drives only ot_rst_relay (4 kept region copies; the adders' reset was 660 raw
// port loads); (b) the bias add is ot_hdc_qadd_lat LAT 5 (f12 l5x: decode + differences | compare, alignments,
// swap | ...): the LAT-4 unit's first stage measured 207 ps over 0.833 ns behind the operand registers (gate TT,
// placement RC) -> +1 edge on the select (adders E+6, key E+7, sort E+10, merge E+12); (c) the merge is one compare
// deep a stage (dsdv_sel_fold_cx / dsdv_sel_cx8_2); (d) the gather request arrives one edge earlier (the collector
// sends it beside its ids) and lands in a registered one-hot hit decode (6 x 112) before the store read: the reply
// leaves on the same edge as before (the store read was a 112:1 select behind one 1,800-load address flop, -47 ps).
// DRIVE-S81-GUNIT N32 (10-20, native census: no mapped driver > 32 loads; same function, same edges, same ports):
// (a) reset: valid / enable bits only, 13 kept relay regions (<= 28 loads each); (b) the bias add is the ve-local
// NATIVE-32 adder ot_s81sl_ve_qadd (LAT 4, bit-exact f12, valid-only reset) behind one operand register with kept
// twin copies (a / a2, b / b2) = LAT 5 as before; (c) SC store write decode per entry and half word in kept
// dsdv_l1f_wdec instances fed by 9 kept copies of the write enables / rows (8 entry groups + the beat-0 forward) and 4
// kept copies of the SC data (input flops at the pins); (d) the beat read select from 19 kept copies of the beat
// number flop (each one slice of the 512 read bits); (e) gather hit decode from 4 kept copies of the request flops;
// (f) the key from both adder output copies (y bits 0..15, y2 bits 16..31), the lane valid twice; (g) sort / merge
// from dsdv_gunit_sel_n32 (4 kept compare copies, one per record bit slice); (h) the reply select from 9 kept copies.
// -----------------------------------------------------------------------------------------------------------------------
// one SC entry's write decode, half word H (kept: the two halves and the forward copy are separate cells)
(* keep_hierarchy *)
module dsdv_l1f_wdec #(
    parameter integer I = 0,
    parameter integer H = 0
) (
    input  wire [13:0]  wq,
    input  wire [3:0]   am, input wire [3:0] bm,
    input  wire [223:0] ad,  input wire [223:0] bd,
    output reg          wh,
    output reg  [15:0]  wd
);
    integer k;
    always @(*) begin
        wh = 1'b0; wd = 16'd0;
        for (k = 0; k < 4; k = k + 1) begin
            if (wq[(64 * (I / 16) + 16 * k + (I % 16)) % 7] && am[k]) begin
                wh = 1'b1; wd = wd | ad[32 * ((64 * (I / 16) + 16 * k + (I % 16)) % 7) + 16 * H +: 16];
            end
            if (wq[7 + (64 * (I / 16) + 16 * k + (I % 16)) % 7] && bm[k]) begin
                wh = 1'b1; wd = wd | bd[32 * ((64 * (I / 16) + 16 * k + (I % 16)) % 7) + 16 * H +: 16];
            end
        end
    end
endmodule

module dsdv_gunit_l1f #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // W face (stack L1)
    input  wire [5:0]    sa_r, input wire [223:0] sa_d, input wire [5:0] sb_r, input wire [223:0] sb_d,
    input  wire [13:0]   we,                 // [6:0] beat a words, [13:7] beat b words that belong to this front
    input  wire          c_go, input wire c_fw, input wire c_l, input wire [2:0] c_bn, input wire [4:0] c_lvn,
    input  wire          re, input wire [3:0] ra,                         // bias read {set, beat}, one beat ahead
    input  wire [1:0]    bw_e, input wire [3:0] bw_a, input wire [255:0] bw_d, // bias row write {set, b}, macro enables
    // E face (collector L1c)
    input  wire          g_go, input wire [5:0] g_hit, input wire [41:0] g_a,  // gather: local {b, k} of each chosen id
    output reg           o_v, output reg o_f, output reg o_l, output reg o_g, output reg [245:0] o_d,
    output reg           o_flt
);
    localparam integer EW = 41, LW = 8 * EW, NL = 16, LA = 5, NS = 7 * NL;
    localparam integer NW = 9, ND = 4, NB = 19, NG = 4, NQ = 9, NR = 13;
    integer i, j, k, c;
    genvar g, l, h;
    // ---------------------------------------------------------------- reset relay: NR kept regions (valid bits only)
    // [0..4] wq copies, [5] control valids, [6..9] adders (4 lanes each), [10] adder flags + key, [11] sorts, [12] out
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- input flops (kept copies at the pins)
    (* keep *) reg [13:0]  wqc [0:NW-1];
    (* keep *) reg [223:0] adc [0:ND-1];
    (* keep *) reg [223:0] bdc [0:ND-1];
    (* keep *) reg [2:0]   cbc [0:NB-1];
    (* keep *) reg [1:0]   cfwc;
    (* keep *) reg [5:0]   ghc [0:NG-1];
    (* keep *) reg [41:0]  gac [0:NG-1];
    reg cgo, cl, rdq, gq; reg [4:0] clv; reg [3:0] rad; reg [1:0] bwe; reg [3:0] bwa; reg [255:0] bwd;
    generate
        for (g = 0; g < NW; g = g + 1) begin : g_wq
            always @(posedge clk or negedge rq[g / 2])
                if (!rq[g / 2]) wqc[g] <= 14'd0; else wqc[g] <= we;
        end
        for (g = 0; g < ND; g = g + 1) begin : g_dq
            always @(posedge clk) begin adc[g] <= sa_d; bdc[g] <= sb_d; end
        end
        for (g = 0; g < NB; g = g + 1) begin : g_bq
            always @(posedge clk) cbc[g] <= c_bn;
        end
        for (g = 0; g < NG; g = g + 1) begin : g_gq
            always @(posedge clk) begin ghc[g] <= g_hit; gac[g] <= g_a; end
        end
    endgenerate
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) begin cgo <= 1'b0; rdq <= 1'b0; bwe <= 2'b00; gq <= 1'b0; end
        else begin cgo <= c_go; rdq <= re; bwe <= bw_e; gq <= g_go; end
    always @(posedge clk) begin
        cfwc <= {2{c_fw}}; cl <= c_l; clv <= c_lvn; rad <= ra; bwa <= bw_a; bwd <= bw_d;
    end
    // ---------------------------------------------------------------- SC store: entry (b, k) = index 64 b + 16 q' + k
    // Decode once before the original input edge, then keep independent final
    // row-match flops per half-entry consumer. No binary row fanout remains
    // after the flop; each final row-match output serves at most 16 data gates
    // plus the write-enable reduction. A predecode output serves at most 28
    // flops (7 global words x 2 halves, doubled for beat-zero forwarding).
    (* keep *) wire [7:0] ahi, alo, bhi, blo;
    (* keep *) wire [63:0] adec, bdec;
    generate for (g = 0; g < 8; g = g + 1) begin : g_pre
        assign ahi[g] = sa_r[5:3] == 3'(g);
        assign alo[g] = sa_r[2:0] == 3'(g);
        assign bhi[g] = sb_r[5:3] == 3'(g);
        assign blo[g] = sb_r[2:0] == 3'(g);
    end
    for (g = 0; g < 64; g = g + 1) begin : g_row_decode
        assign adec[g] = ahi[g / 8] && alo[g % 8];
        assign bdec[g] = bhi[g / 8] && blo[g % 8];
    end endgenerate
    reg  [NS*32-1:0] sc;
    wire [2*NS-1:0]  wh;                       // [2 i + h]
    wire [NS*32-1:0] wdv;
    wire [2*NL-1:0]  whf;
    wire [NL*32-1:0] wdf;
    generate
        for (g = 0; g < NS; g = g + 1) begin : g_e
            for (h = 0; h < 2; h = h + 1) begin : g_h
                (* keep *) reg [3:0] am, bm;
                for (genvar t = 0; t < 4; t = t + 1) begin : g_match
                    localparam integer ROW = (64 * (g / 16) + 16 * t + g % 16) / 7;
                    always @(posedge clk) begin am[t] <= adec[ROW]; bm[t] <= bdec[ROW]; end
                end
                dsdv_l1f_wdec #(.I(g), .H(h)) u_w (.wq(wqc[g / 14]), .am(am), .bm(bm),
                    .ad(adc[g / 28]), .bd(bdc[g / 28]), .wh(wh[2 * g + h]), .wd(wdv[32 * g + 16 * h +: 16]));
                always @(posedge clk) if (wh[2 * g + h]) sc[32 * g + 16 * h +: 16] <= wdv[32 * g + 16 * h +: 16];
                if (g < NL) begin : g_f
                    (* keep *) reg [3:0] amf, bmf;
                    for (genvar t = 0; t < 4; t = t + 1) begin : g_match
                        localparam integer ROW = (64 * (g / 16) + 16 * t + g % 16) / 7;
                        always @(posedge clk) begin amf[t] <= adec[ROW]; bmf[t] <= bdec[ROW]; end
                    end
                    dsdv_l1f_wdec #(.I(g), .H(h)) u_f (.wq(wqc[NW - 1]), .am(amf), .bm(bmf),
                        .ad(adc[ND - 1]), .bd(bdc[ND - 1]), .wh(whf[2 * g + h]), .wd(wdf[32 * g + 16 * h +: 16]));
                end
            end
        end
    endgenerate
    // beat cbn of the store, lane k: read bit n = 32 k + b selected by beat-number copy n / 27
    reg [NL*32-1:0] rdb;
    always @(*) begin
        rdb = {NL*32{1'b0}};
        for (i = 0; i < NL * 32; i = i + 1)
            for (j = 0; j < 7; j = j + 1)
                if (cbc[i / 27] == j[2:0]) rdb[i] = rdb[i] | sc[32 * NL * j + i];
    end
    // ---------------------------------------------------------------- bias macros (read one beat ahead)
    wire [511:0] rd;
    genvar m;
    generate
        for (m = 0; m < 2; m = m + 1) begin : g_m
            ot_sram_1r1w_128x256_m1_r2c2 u_b (.clk(clk), .r_ce_in(rdq), .r_addr_in({3'b000, rad}), .rd_out(rd[256 * m +: 256]),
                .w_ce_in(bwe[m]), .w_addr_in({3'b000, bwa}), .wd_in(bwd), .w_mask_in({256{1'b1}}),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    endgenerate
    // ---------------------------------------------------------------- operands (beat 0 forwards this cycle's writes)
    reg s_v, s_f, s_l; reg [2:0] s_bn; reg [NL-1:0] s_lv; reg [NL*32-1:0] s_val, s_bias;
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) s_v <= 1'b0; else s_v <= cgo;
    always @(posedge clk) begin
        s_f <= cfwc[0]; s_l <= cl; s_bn <= cbc[0];
        for (k = 0; k < NL; k = k + 1) begin
            s_lv[k] <= k < clv;
            for (j = 0; j < 2; j = j + 1)
                s_val[32 * k + 16 * j +: 16] <= (cfwc[j] && whf[2 * k + j]) ? wdf[32 * k + 16 * j +: 16]
                                                                             : rdb[32 * k + 16 * j +: 16];
            s_bias[32 * k +: 32] <= (MUT == 1) ? 32'd0 : rd[32 * k +: 32];
        end
    end
    // ---------------------------------------------------------------- 16 adds: operand register + LAT-4 ve adder = 5
    wire [NL*32-1:0] y, y2; wire [NL-1:0] yf;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_add
            reg pv;
            (* keep *) reg [31:0] pa, pa2, pb, pb2;
            always @(posedge clk or negedge rq[6 + l / 4])
                if (!rq[6 + l / 4]) pv <= 1'b0; else pv <= s_v && s_lv[l];
            always @(posedge clk) begin
                pa <= s_val[32 * l +: 32]; pa2 <= s_val[32 * l +: 32];
                pb <= s_bias[32 * l +: 32]; pb2 <= s_bias[32 * l +: 32];
            end
            wire vo;
            ot_s81sl_ve_qadd #(.LAT(4)) u (.clk(clk), .rst_n(rq[6 + l / 4]), .v(pv), .a(pa), .a2(pa2), .b(pb), .b2(pb2),
                                           .y(y[32 * l +: 32]), .y2(y2[32 * l +: 32]), .vo(vo), .fault(yf[l]));
        end
    endgenerate
    reg [LA*3-1:0] dv; reg [LA*(NL+3+2)-1:0] dd; (* keep *) reg [LA*NL-1:0] dl2;
    always @(posedge clk or negedge rq[10])
        if (!rq[10]) dv <= {LA*3{1'b0}}; else dv <= {dv[3*(LA-1)-1:0], s_l, s_f, s_v};
    always @(posedge clk) begin dd <= {dd[(NL+5)*(LA-1)-1:0], s_bn, s_lv, 2'b00}; dl2 <= {dl2[NL*(LA-1)-1:0], s_lv}; end
    wire [2:0] a_fl = dv[3*(LA-1) +: 3];
    wire [NL+4:0] a_dd = dd[(NL+5)*(LA-1) +: NL+5];
    wire [2:0] a_bn = a_dd[NL+4:NL+2]; wire [NL-1:0] a_lv = a_dd[NL+1:2];
    wire [NL-1:0] a_lv2 = dl2[NL*(LA-1) +: NL];
    // ---------------------------------------------------------------- key register (ot_hdc_select's key map)
    reg [NL*EW-1:0] kd; reg [2:0] kf;
    always @(posedge clk or negedge rq[10]) if (!rq[10]) kf <= 3'd0; else kf <= a_fl;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_key
            wire [31:0] v    = y[32 * l +: 32];        // key bits 0..15
            wire [31:0] v2   = y2[32 * l +: 32];       // key bits 16..31, ninf
            wire        zlo  = (v[30:0] == 31'd0);
            wire        zhi  = (v2[30:0] == 31'd0);
            wire [15:0] klo  = zlo ? 16'h0000 : v[31] ? ~v[15:0] : v[15:0];
            wire [15:0] khi  = zhi ? 16'h8000 : v2[31] ? ~v2[31:16] : {1'b1, v2[30:16]};
            wire        ninf = (v2 == 32'hFF80_0000);
            wire [3:0]  lk   = l;
            wire [EW-1:0] rec = {1'b1, khi, klo, ~{a_bn, lk}, ninf};
            always @(posedge clk) begin
                kd[EW * l +: 20]      <= a_lv[l]  ? rec[19:0]  : 20'd0;
                kd[EW * l + 20 +: 21] <= a_lv2[l] ? rec[40:20] : 21'd0;
            end
        end
    endgenerate
    // ---------------------------------------------------------------- 2 x sort8 (2 exchanges / stage), merge8
    wire [LW-1:0] s0, s1; wire [2:0] sf0, sf1;
    dsdv_seln_sort8 #(.EW(EW), .FW(3)) u_s0 (.clk(clk), .rst_n(rq[11]), .fi(kf), .d(kd[0 +: LW]), .fo(sf0), .q(s0));
    dsdv_seln_sort8 #(.EW(EW), .FW(3)) u_s1 (.clk(clk), .rst_n(rq[11]), .fi(kf), .d(kd[LW +: LW]), .fo(sf1), .q(s1));
    wire [LW-1:0] c1, c3;
    dsdv_seln_fold_cx #(.EW(EW)) u_m0 (.a(s0), .b(s1), .q(c1));
    reg [LW-1:0] m1; reg [2:0] mf;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) mf <= 3'd0; else mf <= sf0;
    always @(posedge clk) m1 <= c1;
    dsdv_seln_cx8_2 #(.EW(EW), .J1(2), .KB1(8), .J2(1), .KB2(8)) u_m1 (.d(m1), .q(c3));
    // gather: registered one-hot hit decode (request one edge early) from NG request copies (28 entries each)
    reg [6*NS-1:0] hs;
    (* keep *) reg [NQ-1:0] gq2;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) gq2 <= {NQ{1'b0}}; else gq2 <= {NQ{gq}};
    always @(posedge clk)
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                hs[NS * j + i] <= ghc[i / 28][j] && {gac[i / 28][7 * j + 4 +: 3], gac[i / 28][7 * j +: 4]} == 7'(i);
    reg [191:0] gd;
    always @(*) begin
        gd = 192'd0;
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                if (hs[NS * j + i]) gd[32 * j +: 32] = gd[32 * j +: 32] | sc[32 * i +: 32];
    end
    always @(posedge clk or negedge rq[12])
        if (!rq[12]) begin o_v <= 1'b0; o_f <= 1'b0; o_l <= 1'b0; o_g <= 1'b0; o_flt <= 1'b0; end
        else begin
            o_v <= mf[0]; o_f <= mf[1]; o_l <= mf[2]; o_g <= gq2[NQ - 1];
            if (|yf || (gq2[NQ - 1] && mf[0])) o_flt <= 1'b1;   // adder fault / a gather on a live select
        end
    wire [245:0] onext = {54'd0, gd};
    always @(posedge clk)
        for (i = 0; i < 246; i = i + 1) o_d[i] <= gq2[i / 28] ? onext[i] : c3[i];
endmodule
