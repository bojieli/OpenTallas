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
// ---------------------------------------------------------------------------------------------------------------------
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
    localparam integer EW = 41, LW = 8 * EW, NL = 16, LA = 5;
    integer i, j, k;
    wire [3:0] rq;                            // relayed resets: [0] input flops / operands, [1] adders, [2] key / sorts, [3] out
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- input flops
    reg [5:0] ar, br; reg [223:0] ad, bd; reg [13:0] wq;
    reg cgo, cfw, cl, rdq, gq; reg [2:0] cbn; reg [4:0] clv; reg [3:0] rad; reg [1:0] bwe; reg [3:0] bwa; reg [255:0] bwd;
    reg [5:0] ghit; reg [41:0] ga;
    always @(posedge clk or negedge rq[0])
        if (!rq[0]) begin wq <= 14'd0; cgo <= 1'b0; rdq <= 1'b0; bwe <= 2'b00; gq <= 1'b0; end
        else begin wq <= we; cgo <= c_go; rdq <= re; bwe <= bw_e; gq <= g_go; end
    always @(posedge clk) begin
        ar <= sa_r; ad <= sa_d; br <= sb_r; bd <= sb_d; cfw <= c_fw; cl <= c_l; cbn <= c_bn; clv <= c_lvn;
        rad <= ra; bwa <= bw_a; bwd <= bw_d; ghit <= g_hit; ga <= g_a;
    end
    // ---------------------------------------------------------------- SC store: entry (b, k) = index 64 b + 16 q' + k
    // for the unknown q' = 0..3; candidate (q', beat) hits iff that beat's row is (64 b + 16 q' + k) / 7 and its word
    // (64 b + 16 q' + k) % 7 is enabled for this front (at most one candidate can: the rows differ).
    localparam integer NS = 7 * NL;
    reg  [NS*32-1:0] sc;                       // entry e = NL b + k at [32 e +: 32]
    reg  [NS-1:0]    wh;                       // this cycle's write hits (also the beat-0 forward)
    reg  [NS*32-1:0] wdv;
    always @(*) begin
        wh = {NS{1'b0}}; wdv = {NS*32{1'b0}};
        for (i = 0; i < NS; i = i + 1)
            for (k = 0; k < 4; k = k + 1)
                for (j = 0; j < 7; j = j + 1)
                    if ((64 * (i / NL) + 16 * k + (i % NL)) % 7 == j) begin
                        if (wq[j] && ar == 6'((64 * (i / NL) + 16 * k + (i % NL)) / 7)) begin
                            wh[i] = 1'b1; wdv[32 * i +: 32] = wdv[32 * i +: 32] | ad[32 * j +: 32];
                        end
                        if (wq[7 + j] && br == 6'((64 * (i / NL) + 16 * k + (i % NL)) / 7)) begin
                            wh[i] = 1'b1; wdv[32 * i +: 32] = wdv[32 * i +: 32] | bd[32 * j +: 32];
                        end
                    end
    end
    always @(posedge clk) for (i = 0; i < NS; i = i + 1) if (wh[i]) sc[32 * i +: 32] <= wdv[32 * i +: 32];
    // beat cbn of the store, lane k (one-hot AND-OR over the 7 beats)
    reg [NL*32-1:0] rdb;
    always @(*) begin
        rdb = {NL*32{1'b0}};
        for (k = 0; k < NL; k = k + 1)
            for (j = 0; j < 7; j = j + 1)
                if (cbn == j[2:0]) rdb[32 * k +: 32] = rdb[32 * k +: 32] | sc[32 * (NL * j + k) +: 32];
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
    always @(posedge clk or negedge rq[0])
        if (!rq[0]) s_v <= 1'b0; else s_v <= cgo;
    always @(posedge clk) begin
        s_f <= cfw; s_l <= cl; s_bn <= cbn;
        for (k = 0; k < NL; k = k + 1) begin
            s_lv[k] <= k < clv;
            s_val[32 * k +: 32] <= (cfw && wh[k]) ? wdv[32 * k +: 32] : rdb[32 * k +: 32];
            s_bias[32 * k +: 32] <= (MUT == 1) ? 32'd0 : rd[32 * k +: 32];
        end
    end
    // ---------------------------------------------------------------- 16 adds (LAT 5) + the flags / lane valids beside
    wire [NL*32-1:0] y; wire [NL-1:0] yf;
    genvar l;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_add
            ot_hdc_qadd_lat #(.KEEP(1), .LAT(LA)) u (clk, rq[1], s_v && s_lv[l], s_val[32 * l +: 32], s_bias[32 * l +: 32],
                                                     y[32 * l +: 32], yf[l]);
        end
    endgenerate
    reg [LA*3-1:0] dv; reg [LA*(NL+3+2)-1:0] dd;
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) dv <= {LA*3{1'b0}}; else dv <= {dv[3*(LA-1)-1:0], s_l, s_f, s_v};
    always @(posedge clk) dd <= {dd[(NL+5)*(LA-1)-1:0], s_bn, s_lv, 2'b00};
    wire [2:0] a_fl = dv[3*(LA-1) +: 3];                      // {l, f, v} of the adder outputs
    wire [NL+4:0] a_dd = dd[(NL+5)*(LA-1) +: NL+5];
    wire [2:0] a_bn = a_dd[NL+4:NL+2]; wire [NL-1:0] a_lv = a_dd[NL+1:2];
    // ---------------------------------------------------------------- key register (ot_hdc_select's key map)
    reg [NL*EW-1:0] kd; reg [2:0] kf;
    always @(posedge clk or negedge rq[2]) if (!rq[2]) kf <= 3'd0; else kf <= a_fl;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_key
            wire [31:0] v    = y[32 * l +: 32];
            wire        zero = (v[30:0] == 31'd0);
            wire [31:0] key  = zero ? 32'h8000_0000 : v[31] ? ~v : {1'b1, v[30:0]};
            wire        ninf = (v == 32'hFF80_0000);
            wire [3:0]  lk   = l;
            always @(posedge clk) kd[EW * l +: EW] <= a_lv[l] ? {1'b1, key, ~{a_bn, lk}, ninf} : {EW{1'b0}};
        end
    endgenerate
    // ---------------------------------------------------------------- 2 x sort8 (2 exchanges / stage), merge8
    wire [LW-1:0] s0, s1; wire [2:0] sf0, sf1;
    dsdv_sel_sort8 #(.EW(EW), .CPS(2), .FW(3), .MUT(MUT)) u_s0 (.clk(clk), .rst_n(rq[2]), .fi(kf), .d(kd[0 +: LW]), .fo(sf0), .q(s0), .fn(), .qn());
    dsdv_sel_sort8 #(.EW(EW), .CPS(2), .FW(3), .MUT(MUT)) u_s1 (.clk(clk), .rst_n(rq[2]), .fi(kf), .d(kd[LW +: LW]), .fo(sf1), .q(s1), .fn(), .qn());
    // merge8 inline (one compare deep a stage): its second register is the output register, shared with the gather reply
    wire [LW-1:0] c1, c3;
    dsdv_sel_fold_cx #(.EW(EW)) u_m0 (.a(s0), .b(s1), .q(c1));
    reg [LW-1:0] m1; reg [2:0] mf;
    always @(posedge clk or negedge rq[3]) if (!rq[3]) mf <= 3'd0; else mf <= sf0;
    always @(posedge clk) m1 <= c1;
    dsdv_sel_cx8_2 #(.EW(EW), .J1(2), .KB1(8), .J2(1), .KB2(8)) u_m1 (.d(m1), .q(c3));
    // gather: registered one-hot hit decode (request one edge early), then the scores of the chosen experts held here
    // (local {b, k}), zero where not hit
    reg [6*NS-1:0] hs; reg gq2;
    always @(posedge clk or negedge rq[3]) if (!rq[3]) gq2 <= 1'b0; else gq2 <= gq;
    always @(posedge clk)
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                hs[NS * j + i] <= ghit[j] && {ga[7 * j + 4 +: 3], ga[7 * j +: 4]} == 7'(NL * (i / NL) + (i % NL));
    reg [191:0] gd;
    always @(*) begin
        gd = 192'd0;
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                if (hs[NS * j + i]) gd[32 * j +: 32] = gd[32 * j +: 32] | sc[32 * i +: 32];
    end
    always @(posedge clk or negedge rq[3])
        if (!rq[3]) begin o_v <= 1'b0; o_f <= 1'b0; o_l <= 1'b0; o_g <= 1'b0; o_flt <= 1'b0; end
        else begin
            o_v <= mf[0]; o_f <= mf[1]; o_l <= mf[2]; o_g <= gq2;
            if (|yf || (gq2 && mf[0])) o_flt <= 1'b1;           // adder fault / a gather on a live select
        end
    always @(posedge clk) o_d <= gq2 ? {54'd0, gd} : c3[6 * EW - 1:0];
endmodule
