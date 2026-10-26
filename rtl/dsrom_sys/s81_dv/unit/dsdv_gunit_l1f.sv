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
// GUNIT2 (10-20): the 10-20 N32 gates (214042) refused native census (488 drivers > 32, max 276).  Two synthesis
// facts undid the kept copies: (1) the copies were UNPACKED ARRAYS (reg [13:0] wqc [0:8], ...): yosys makes them
// memories, ot_keep_regs.tcl never sees a keep wire, and opt_merge folded every copy into one flop (wqc 276, cbc 60);
// (2) the kept modules were PARAMETERISED (dsdv_l1f_wdec #(I, H), dsdv_seln_gt #(W)): $paramod names miss
// SYNTH_KEEP_MODULES, so they were flattened and their identical logic merged across copies (compare 72, wdec 40, the
// shared row decode 238).  Fix, same function / ports / edges: every copy is a PACKED keep vector; every kept module
// is unparameterised and on the kit keep list.  The census counts the leaf pins a driver reaches THROUGH the
// hierarchy and through buffers / inverters, so each kept module is a fan-out fence: dsdv_l1f_wdec8 (one entry half;
// its 8 candidate terms arrive pre-selected by wiring and are ANDed in a kept dsdv_l1f_term8, so a row one-hot / wq
// bit reaches one gate per term; the write enable leaves as two dsdv_l1f_or8 copies, one per byte), kept decoders
// dsdv_l1f_dec64 (row -> one-hot, per row copy) and dsdv_l1f_dec7 (beat -> one-hot, 32 beat copies of 16 read bits),
// the forward byte select dsdv_l1f_mux8, and the select network of dsdv_gunit_sel_n32.sv (kept 4-bit compare trees,
// S = 8 compare copies, kept 1-bit record muxes, every record register -- key, sort stages, merge -- kept twice).  The
// forward path has its own SC data copy (ND 5); 18 reply-select copies (<= 14 bits each); 4 cfw copies.
// the 8 term enables of one entry half (kept: the row one-hot / wq copies reach one gate per term)
(* keep_hierarchy *)
module dsdv_l1f_term8 (input wire [7:0] en, input wire [7:0] hit, output wire [7:0] p);
    assign p = en & hit;
endmodule

// byte select (kept: the forward select reaches these 8 muxes only)
(* keep_hierarchy *)
module dsdv_l1f_mux8 (input wire s, input wire [7:0] a, input wire [7:0] b, output wire [7:0] y);
    assign y = s ? a : b;
endmodule

// 8-input OR (kept, so the two write-enable copies of one entry half stay two drivers)
(* keep_hierarchy *)
module dsdv_l1f_or8 (input wire [7:0] a, output wire y);
    assign y = |a;
endmodule

// one SC entry half's write decode: term t (a beat: 2 k, b beat: 2 k + 1) writes d[16 t +: 16] iff en[t] && hit[t];
// the write enable leaves twice (wh[0] for bits 0..7, wh[1] for bits 8..15: one 16-bit enable measured 40 loads)
(* keep_hierarchy *)
module dsdv_l1f_wdec8 (
    input  wire [7:0]   en,
    input  wire [7:0]   hit,
    input  wire [127:0] d,
    output wire [1:0]   wh,
    output reg  [15:0]  wd
);
    wire [7:0] p;
    (* keep = 1 *) dsdv_l1f_term8 u_p (.en(en), .hit(hit), .p(p));   // en / hit reach one AND each (not the 16 data bits)
    integer t;
    always @(*) begin
        wd = 16'd0;
        for (t = 0; t < 8; t = t + 1)
            if (p[t]) wd = wd | d[16 * t +: 16];
    end
    (* keep = 1 *) dsdv_l1f_or8 u_o0 (.a(p), .y(wh[0]));
    (* keep = 1 *) dsdv_l1f_or8 u_o1 (.a(p), .y(wh[1]));
endmodule

// row copy -> one-hot (64)
(* keep_hierarchy *)
module dsdv_l1f_dec64 (input wire [5:0] a, output wire [63:0] y);
    genvar j;
    generate for (j = 0; j < 64; j = j + 1) begin : g_j assign y[j] = (a == j); end endgenerate
endmodule

// beat-number copy -> one-hot (beats 0..6; 7 selects nothing)
(* keep_hierarchy *)
module dsdv_l1f_dec7 (input wire [2:0] a, output wire [6:0] y);
    genvar j;
    generate for (j = 0; j < 7; j = j + 1) begin : g_j assign y[j] = (a == j); end endgenerate
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
    output reg           o_v, output reg o_f, output reg o_l, output reg o_g, output wire [244:0] o_d,   // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins): o_d packed {d[245:206], d[204:0]} (d[205] is read by no collector)
    output reg           o_flt
);
    reg [245:0] o_df;   // RTLC: o_df[205] is never written and has no pin
`ifdef OT_RTLC_MUT_L1F   // RTLC bench mutant: o_d packs d[245:1] (drops d[0], keeps d[205])
    assign o_d = o_df[245:1];
`else
    assign o_d = {o_df[245:206], o_df[204:0]};
`endif
    localparam integer EW = 41, LW = 8 * EW, NL = 16, LA = 5, NS = 7 * NL;
`ifdef OT_S81_GUNIT_FWDOWN
    // Eight store groups plus sixteen same-edge forward row/enable owners.
    // Four payload owners each serve four forward lanes; no new data edge.
    localparam integer NW = 24, ND = 8, NB = 32, NG = 4, NQ = 18, NR = 21;
`else
    localparam integer NW = 9, ND = 5, NB = 32, NG = 4, NQ = 18, NR = 13;
`endif
    integer i, j, k, c;
    genvar g, l, h, t;
    // ---------------------------------------------------------------- reset relay: NR kept regions (valid bits only)
    // [0..4] wq copies, [5] control valids, [6..9] adders (4 lanes each), [10] adder flags + key, [11] sorts, [12] out
    wire [NR-1:0] rq;
    ot_rst_relay #(.REGIONS(NR)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- input flops (kept copies at the pins)
    // PACKED keep vectors (an unpacked array becomes a yosys memory and its copies fold, GUNIT2)
    (* keep *) reg [NW*14-1:0]  wqc;
    (* keep *) reg [NW*6-1:0]   arc, brc;
    (* keep *) reg [ND*224-1:0] adc, bdc;
    (* keep *) reg [NB*3-1:0]   cbc;
    (* keep *) reg [3:0]        cfwc;
    (* keep *) reg [NG*6-1:0]   ghc;
    (* keep *) reg [NG*42-1:0]  gac;
    reg cgo, cl, rdq, gq; reg [4:0] clv; reg [3:0] rad; reg [1:0] bwe; reg [3:0] bwa; reg [255:0] bwd;
    generate
        for (g = 0; g < NW; g = g + 1) begin : g_wq
`ifdef OT_S81_GUNIT_FWDOWN
            localparam integer WR_REGION=(g<8)?g/2:13+(g-8)/2;
`else
            localparam integer WR_REGION=g/2;
`endif
            always @(posedge clk or negedge rq[WR_REGION])
                if (!rq[WR_REGION]) wqc[14 * g +: 14] <= 14'd0; else wqc[14 * g +: 14] <= we;
            always @(posedge clk) begin arc[6 * g +: 6] <= sa_r; brc[6 * g +: 6] <= sb_r; end
        end
        for (g = 0; g < ND; g = g + 1) begin : g_dq
            always @(posedge clk) begin adc[224 * g +: 224] <= sa_d; bdc[224 * g +: 224] <= sb_d; end
        end
        for (g = 0; g < NB; g = g + 1) begin : g_bq
            always @(posedge clk) cbc[3 * g +: 3] <= c_bn;
        end
        for (g = 0; g < NG; g = g + 1) begin : g_gq
            always @(posedge clk) begin ghc[6 * g +: 6] <= g_hit; gac[42 * g +: 42] <= g_a; end
        end
    endgenerate
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) begin cgo <= 1'b0; rdq <= 1'b0; bwe <= 2'b00; gq <= 1'b0; end
        else begin cgo <= c_go; rdq <= re; bwe <= bw_e; gq <= g_go; end
    always @(posedge clk) begin
        cfwc <= {4{c_fw}}; cl <= c_l; clv <= c_lvn; rad <= ra; bwa <= bw_a; bwd <= bw_d;
    end
    // ---------------------------------------------------------------- SC store: entry (b, k) = index 64 b + 16 q' + k
    // write decode: entry i in group i / 14 (wq / row copies), data copy i / 28; forward (i < 16): copy NW-1 / ND-1.
    // Entry (b, k) half h has 8 candidate terms: front q' = 0..3 of beat a (term 2 q') and beat b (2 q' + 1), global
    // index IX = 64 b + 16 q' + k = word IX % 7 of row IX / 7; the selection is wiring into the kept dsdv_l1f_wdec8.
    wire [NW*64-1:0] aoh, boh;
    generate
        for (g = 0; g < NW; g = g + 1) begin : g_dec
            (* keep = 1 *) dsdv_l1f_dec64 u_da (.a(arc[6 * g +: 6]), .y(aoh[64 * g +: 64]));
            (* keep = 1 *) dsdv_l1f_dec64 u_db (.a(brc[6 * g +: 6]), .y(boh[64 * g +: 64]));
        end
    endgenerate
    reg  [NS*32-1:0] sc;
    wire [4*NS-1:0]  wh;                       // [4 i + 2 h + byte]
    wire [NS*32-1:0] wdv;
    wire [4*NL-1:0]  whf;
    wire [NL*32-1:0] wdf;
    generate
        for (g = 0; g < NS; g = g + 1) begin : g_e
            for (h = 0; h < 2; h = h + 1) begin : g_h
                wire [7:0] en, hit, enf, hitf; wire [127:0] dd, ddf;
                for (t = 0; t < 4; t = t + 1) begin : g_t
                    localparam integer IX = 64 * (g / 16) + 16 * t + (g % 16), WJ = IX % 7, RJ = IX / 7;
                    localparam integer CW = g / 14, CD = g / 28;
`ifdef OT_S81_GUNIT_FWDOWN
                    localparam integer FW=8+((g<NL)?g:0), FD=4+((g<NL)?g/4:0);
`else
                    localparam integer FW=NW-1, FD=ND-1;
`endif
                    assign en[2 * t]      = wqc[14 * CW + WJ];      assign en[2 * t + 1]  = wqc[14 * CW + 7 + WJ];
                    assign hit[2 * t]     = aoh[64 * CW + RJ];      assign hit[2 * t + 1] = boh[64 * CW + RJ];
                    assign dd[32 * t +: 16]      = adc[224 * CD + 32 * WJ + 16 * h +: 16];
                    assign dd[32 * t + 16 +: 16] = bdc[224 * CD + 32 * WJ + 16 * h +: 16];
                    assign enf[2 * t]     = wqc[14 * FW + WJ];      assign enf[2 * t + 1] = wqc[14 * FW + 7 + WJ];
                    assign hitf[2 * t]    = aoh[64 * FW + RJ];      assign hitf[2 * t + 1] = boh[64 * FW + RJ];
                    assign ddf[32 * t +: 16]      = adc[224 * FD + 32 * WJ + 16 * h +: 16];
                    assign ddf[32 * t + 16 +: 16] = bdc[224 * FD + 32 * WJ + 16 * h +: 16];
                end
                (* keep = 1 *) dsdv_l1f_wdec8 u_w (.en(en), .hit(hit), .d(dd), .wh(wh[4 * g + 2 * h +: 2]), .wd(wdv[32 * g + 16 * h +: 16]));
                always @(posedge clk) begin
                    if (wh[4 * g + 2 * h])     sc[32 * g + 16 * h +: 8]     <= wdv[32 * g + 16 * h +: 8];
                    if (wh[4 * g + 2 * h + 1]) sc[32 * g + 16 * h + 8 +: 8] <= wdv[32 * g + 16 * h + 8 +: 8];
                end
                if (g < NL) begin : g_f
                    (* keep = 1 *) dsdv_l1f_wdec8 u_f (.en(enf), .hit(hitf), .d(ddf), .wh(whf[4 * g + 2 * h +: 2]),
                                                       .wd(wdf[32 * g + 16 * h +: 16]));
                end
            end
        end
    endgenerate
    // beat cbn of the store, lane k: read bit n = 32 k + b selected by one-hot beat copy n / 16 (16 AND-OR loads)
    wire [NB*7-1:0] cbh;
    generate
        for (g = 0; g < NB; g = g + 1) begin : g_bd
            (* keep = 1 *) dsdv_l1f_dec7 u_d (.a(cbc[3 * g +: 3]), .y(cbh[7 * g +: 7]));
        end
    endgenerate
    reg [NL*32-1:0] rdb;
    always @(*) begin
        rdb = {NL*32{1'b0}};
        for (i = 0; i < NL * 32; i = i + 1)
            for (j = 0; j < 7; j = j + 1)
                if (cbh[7 * (i / 16) + j]) rdb[i] = rdb[i] | sc[32 * NL * j + i];
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
    wire [NL*32-1:0] svn;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_fw
            for (h = 0; h < 4; h = h + 1) begin : g_y
                (* keep = 1 *) dsdv_l1f_mux8 u_m (.s(cfwc[2 * (h / 2) + l / 8] && whf[4 * l + h]), .a(wdf[32 * l + 8 * h +: 8]),
                                                  .b(rdb[32 * l + 8 * h +: 8]), .y(svn[32 * l + 8 * h +: 8]));
            end
        end
    endgenerate
    reg s_v, s_f, s_l; reg [2:0] s_bn; reg [NL-1:0] s_lv; reg [NL*32-1:0] s_val, s_bias;
    always @(posedge clk or negedge rq[5])
        if (!rq[5]) s_v <= 1'b0; else s_v <= cgo;
    always @(posedge clk) begin
        s_f <= cfwc[0]; s_l <= cl; s_bn <= cbc[2:0];
        for (k = 0; k < NL; k = k + 1) begin
            s_lv[k] <= k < clv;
            for (j = 0; j < 4; j = j + 1)                 // byte j of lane k (half j / 2): kept byte mux below
                s_val[32 * k + 8 * j +: 8] <= svn[32 * k + 8 * j +: 8];
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
    (* keep *) reg [NL*EW-1:0] kda, kdb;   // copies A (select compares) / B (candidate compares, data), GUNIT2
    reg [2:0] kf;
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
            wire [EW-1:0] mrec = {a_lv2[l] ? rec[40:20] : 21'd0, a_lv[l] ? rec[19:0] : 20'd0};
            always @(posedge clk) begin kda[EW * l +: EW] <= mrec; kdb[EW * l +: EW] <= mrec; end
        end
    endgenerate
    // ---------------------------------------------------------------- 2 x sort8 (2 exchanges / stage), merge8
    wire [LW-1:0] s0a, s0b, s1a, s1b; wire [2:0] sf0, sf1;
    dsdv_seln_sort8 #(.EW(EW), .FW(3)) u_s0 (.clk(clk), .rst_n(rq[11]), .fi(kf), .da(kda[0 +: LW]), .db(kdb[0 +: LW]),
                                            .fo(sf0), .qa(s0a), .qb(s0b));
    dsdv_seln_sort8 #(.EW(EW), .FW(3)) u_s1 (.clk(clk), .rst_n(rq[11]), .fi(kf), .da(kda[LW +: LW]), .db(kdb[LW +: LW]),
                                            .fo(sf1), .qa(s1a), .qb(s1b));
    wire [LW-1:0] c1, c3;
    dsdv_seln_fold_cx #(.EW(EW)) u_m0 (.aa(s0a), .ab(s0b), .ba(s1a), .bb(s1b), .q(c1));
    (* keep *) reg [LW-1:0] m1a, m1b; reg [2:0] mf;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) mf <= 3'd0; else mf <= sf0;
    always @(posedge clk) begin m1a <= c1; m1b <= c1; end
    dsdv_seln_cx8_2 #(.EW(EW), .J1(2), .KB1(8), .J2(1), .KB2(8)) u_m1 (.da(m1a), .db(m1b), .q(c3));
    // gather: registered one-hot hit decode (request one edge early) from NG request copies (28 entries each); NQ reply
    // select copies (14 output bits each)
    reg [6*NS-1:0] hs;
    (* keep *) reg [NQ-1:0] gq2;
    always @(posedge clk or negedge rq[12]) if (!rq[12]) gq2 <= {NQ{1'b0}}; else gq2 <= {NQ{gq}};
    always @(posedge clk)
        for (j = 0; j < 6; j = j + 1)
            for (i = 0; i < NS; i = i + 1)
                hs[NS * j + i] <= ghc[6 * (i / 28) + j] && {gac[42 * (i / 28) + 7 * j + 4 +: 3], gac[42 * (i / 28) + 7 * j +: 4]} == 7'(i);
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
        for (i = 0; i < 246; i = i + 1) if (i != 205) o_df[i] <= gq2[i / 14] ? onext[i] : c3[i];
endmodule
