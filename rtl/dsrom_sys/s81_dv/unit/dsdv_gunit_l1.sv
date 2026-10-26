`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l1 -- G-unit leaf L1 (5th of 6 in the stack, below the stop L2): the router's
// stack leaf.  S81U-GUNIT-L1 (10-17): the score store, bias table and top-6 select moved to FIVE E-side leaves -- four select fronts dsdv_gunit_l1f (lanes 16 q .. 16 q + 15 of every 64-lane beat: SC store
// slice, bias in 2 SRAM macros, 16 bias adds, sort / merge at two compare-exchanges a stage) and the collector
// dsdv_gunit_l1c (merges over the fronts and the beats, ascending-index order, gather of the chosen scores).  This leaf
// keeps: the rung feedthrough, SC beat checks and the window / job sequencer, the per-front control, the bias-row
// writes, the ids CTL row (formed from the collector's ids, zero when idle), the routing-weight operands to L3 and the
// merge of L3's weight rows into the router CTL toward L2.
//
// Per layer-token (tools/hdc_golden_v41.Model.moe, every rounding the golden's):
//     ids = sorted(topk_lowest_index(add(scores, bias), K))      (fronts + collector)
//     w_j = mul(div(scores[ids[j]], add(seqsum(scores[ids]), 1e-20)), route_scale)   (L3 ot_s81_su_rw, unchanged)
// L3's operand rows are now the ids row with the ids renumbered 0..5 (same order) and ONE score row holding the six
// gathered unbiased scores at words 0..5: ot_s81_su_rw reads exactly scores[ids[j]] in the ids order, so the weights
// are bit-identical to the old 28-row score stream's, and ~27 cycles earlier.
// SC beats (kind 5) arrive from L2's vstop deliver flops (dl_*, unfiltered; kind decoded behind this leaf's input flop):
// score row r = [49:40] (r < 64), scores j = 0..6 = [52 + 32 j +: 32], index 7 r + j (indices >= ne ignored), each
// row once, ceil(ne / 7) beats in any order and either direction (two in one cycle are fine).
// cw (relayed by L2): cw_a[9] = 0 table write, set s = cw_a[8]: rows 0..55 = bias words 8 r .. 8 r + 7 (-> front
// (r % 8) / 2, macro r % 2, address {s, r / 8}), row 62 word 6 = route_scale; cw_a[9:8] = 2'b10, cw_a[0] = 0 ROUTER JOB
// {set [40], ne [39:31], row [30:21], lmask [20:16], smask [15:0]}, armed before the window's first SC beat.
// Latency: the select starts ON the edge after the last SC beat lands here (beat 0 forwards the arriving words in the
// fronts); the fronts' bias macros are read one beat ahead (beat 0's address {set, 0} is held while a window fills, so
// the SRAM read adds no edge).  Fixed: no handshakes, no ready / credit.
// Output ct (router CTL rows, target 5; zero when idle): ids row `row` (mask 0011) on the edge after the collector's
// ids, later L3's two weight rows (relayed: input flop -> this output flop).  Both on one edge is a sticky fault.
// fault (sticky): duplicate SC row, row >= 64, an SC beat with no armed job or while the select runs, a job write
// while one is armed, the collector's fault (fewer than K, a front's adder fault), L3's fault, a CTL collision.
// Every input lands in a flop; every output leaves a flop (the ids row: the collector's zero-idle ids into ct_b).
// S81U-GUNIT-L1b (10-17, NATIVE-2 pin rules): rst_n drives only ot_rst_relay (4 kept region copies); the job /
// window / route_scale registers left the reset block (the raw port was their load enable: in->reg -167 ps at the
// gate); the collector's i_v / i_ids land in pin flops (they fed the N-face ct_b output flop and the sequencer
// straight from the E pins): +1 edge on the ids row (and the weights' start).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l1 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // N face (L2)
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins): dl_a / dl_b packed {dl[275:52], dl[49:40], dl[3:1]} (bits 0, 4..39, 50, 51 are
    // not read), cw_a packed {cw_a[9:8], cw_a[5:0]} (cw_a[7:6] not read), ct_b / w_b = the packed CTL row (ctlpk), rw_x
    // [191:0] (rw_x[511:192] were 0).  Unpacked into the same internal registers: function and edges unchanged.
    input  wire          dl_av, input wire [236:0] dl_a, input wire dl_bv, input wire [236:0] dl_b,
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output reg           ct_v, output reg [169:0] ct_b, output reg fault,
    // S face (L3)
    output wire [275:0]  rs_o,  input wire [275:0] rs_i,
    output reg           rw_st, output reg rw_v, output reg rw_l, output reg [191:0] rw_x,
    output reg  [31:0]   rw_scale, output reg [9:0] rw_row, output reg [4:0] rw_lm, output reg [15:0] rw_sm,
    output reg  [3:0]    sid_o,
    input  wire          w_v, input wire [169:0] w_b, input wire f3,
    // E face: the four fronts (shared buses + per-front q-packed enables)
    output reg  [5:0]    sa_r, output reg [223:0] sa_d, output reg [5:0] sb_r, output reg [223:0] sb_d,
    output reg  [55:0]   we, output reg c_go, output reg c_fw, output reg c_l, output reg [2:0] c_bn,
    output reg  [19:0]   c_lvn, output reg re, output reg [3:0] ra,
    output reg  [7:0]    bw_e, output reg [3:0] bw_a, output reg [255:0] bw_d,
    // E face: the collector
    input  wire          i_v, input wire [53:0] i_ids, input wire gs_v, input wire [191:0] gs_d, input wire fc
);
    localparam integer V = 276, K = 6, NSET = 2, NE = 448, IW = 9, SB = 1;
    integer i, j, q, i2;
    wire [3:0] rq;                            // relayed resets: [0] rung dn, [1] rung up, [2] N / E input flops, [3] sequencer
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- rung feedthrough (L2 <-> L3)
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rq[0]), .d(rn_i), .q(rs_o));
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rq[1]), .d(rs_i), .q(rn_o));
    // ---------------------------------------------------------------- input flops
    reg dav, dbv, wv, wv3, f3_q, fc_q, gv, iv; reg [V-1:0] ab, bb, wb3; reg [9:0] wa; reg [255:0] wd; reg [3:0] sid_c;
    reg [191:0] gd; reg [53:0] ids;
    always @(posedge clk or negedge rq[2])
        if (!rq[2]) begin dav <= 1'b0; dbv <= 1'b0; wv <= 1'b0; wv3 <= 1'b0; f3_q <= 1'b0; fc_q <= 1'b0; gv <= 1'b0; iv <= 1'b0; end
        else begin dav <= dl_av; dbv <= dl_bv; wv <= cw_v; wv3 <= w_v; f3_q <= f3; fc_q <= fc; gv <= gs_v; iv <= i_v; end
    always @(posedge clk) begin
`ifdef OT_RTLC_MUT_L1   // RTLC bench mutant: dl_a unpack: the ra field (bits 40..45) lands one bit low
        ab <= {dl_a[236:13], 3'd0, dl_a[12:3], 35'd0, dl_a[2:0], 1'b0}; bb <= {dl_b[236:13], 2'd0, dl_b[12:3], 36'd0, dl_b[2:0], 1'b0};
`else
        ab <= {dl_a[236:13], 2'd0, dl_a[12:3], 36'd0, dl_a[2:0], 1'b0}; bb <= {dl_b[236:13], 2'd0, dl_b[12:3], 36'd0, dl_b[2:0], 1'b0};
`endif
        wa <= {cw_a[7:6], 2'd0, cw_a[5:0]}; wd <= cw_d; sid_c <= sid_i; wb3 <= ctlup(w_b); sid_o <= sid_c; gd <= gs_d; ids <= i_ids;
    end
    wire av = dav && ab[3:1] == 3'd5, bv = dbv && bb[3:1] == 3'd5;
    wire [SB-1:0] wset = wa[8 +: SB];
    // ---------------------------------------------------------------- route_scale table; bias rows -> the fronts' macros
    reg [31:0] rscale [0:NSET-1];
    wire bias_w = wv && !wa[9] && wa[5:0] < 6'd56;
    always @(posedge clk) if (wv && !wa[9] && wa[5:0] == 6'd62) rscale[wset] <= wd[32 * 6 +: 32];
    always @(posedge clk or negedge rq[2])
        if (!rq[2]) bw_e <= 8'd0; else bw_e <= bias_w ? (8'd1 << wa[2:0]) : 8'd0;
    always @(posedge clk) begin bw_a <= {wset, wa[5:3]}; bw_d <= wd; end
    // ---------------------------------------------------------------- router job (armed -> taken by the SC window)
    reg jv; reg [SB-1:0] jset; reg [8:0] jne; reg [9:0] jrow; reg [4:0] jlm; reg [15:0] jsm;
    reg [SB-1:0] cset; reg [8:0] ne; reg [9:0] row; reg [4:0] lmask; reg [15:0] smask; reg [6:0] nsc;
    wire job_w = wv && wa[9:8] == 2'b10 && !wa[0];
    reg [63:0] seen; reg [6:0] nseen;
    wire [5:0] ra_a = ab[45:40], ra_b = bb[45:40];
    // ---------------------------------------------------------------- sequencer (fixed cycle counts, no handshakes)
    localparam [1:0] S_IN = 2'd0, S_SEL = 2'd1, S_IDS = 2'd2, S_GW = 2'd3;
    reg [1:0] st; reg [2:0] n; reg [3:0] nbs;
    wire take = st == S_IN && (av || bv) && nseen == 7'd0;      // the first SC beat of a window takes the armed job
    wire last = st == S_IN && (av || bv) && nseen + av + bv == (take ? 7'((jne + 9'd6) / 9'd7) : nsc);
    wire [8:0] ne_x = take ? jne : ne;
    wire [3:0] nbs_c = 4'((ne_x + 9'd63) >> 6);
    // set of the bias read: the armed job's until its window starts (a job written this cycle bypasses), then cset
    wire [SB-1:0] set_x = (nseen == 7'd0) ? (job_w ? wd[40 +: SB] : jset) : cset;
    wire [SB-1:0] set_t = take ? jset : cset;
    // select beat issued this edge: beat 0 on `last` (S_IN), beats 1 .. nbs-1 in S_SEL
    wire        go_n = last || st == S_SEL;
    wire [2:0]  bn_n = (st == S_SEL) ? n : 3'd0;
    wire [3:0]  nb_n = last ? nbs_c : nbs;
    wire [8:0]  ne_n = last ? ne_x : ne;
    // S81-KITS-RTLC 10-24 (raw face_guard, 0 edges): the held pin registers fault (sticky) and rw_scale have kept internal
    // twins that hold; each pin flop loads twin-next, never its own Q.
    (* keep = "true" *) reg fault_k; (* keep = "true" *) reg [31:0] rws_k; reg fs;
    always @(posedge clk) rw_scale <= (st == S_IN && take) ? rscale[jset] : rws_k;
    always @(posedge clk or negedge rq[3])
        if (!rq[3]) begin
            fs = 1'b0; fault_k <= 1'b0;
            st <= S_IN; seen <= 64'd0; nseen <= 7'd0; fault <= 1'b0; jv <= 1'b0; c_go <= 1'b0; we <= 56'd0; re <= 1'b0;
            rw_st <= 1'b0; rw_v <= 1'b0; ct_v <= 1'b0;
        end else begin
            fs = 1'b0;
            rw_st <= 1'b0; rw_v <= 1'b0;
            if (fc_q || f3_q || (iv && wv3)) fs = 1'b1;
            if (av && (ab[49:46] != 4'd0 || seen[ra_a])) fs = 1'b1;
            if (bv && (bb[49:46] != 4'd0 || seen[ra_b] || (av && ra_a == ra_b))) fs = 1'b1;
            if ((av || bv) && st != S_IN) fs = 1'b1;
            if (job_w) begin
                if (jv && !take) fs = 1'b1;
                jv <= 1'b1;
            end
            // SC word enables per front: word j of a beat with row r is index 7 r + j, front (7 r + j)[5:4]
            for (i = 0; i < 4; i = i + 1)
                for (j = 0; j < 7; j = j + 1) begin
                    we[14 * i + j]     <= av && 9'((7 * ra_a + j) >> 4) % 4 == i;
                    we[14 * i + 7 + j] <= bv && 9'((7 * ra_b + j) >> 4) % 4 == i;
                end
            c_go <= go_n; re <= 1'b1;
            ct_v <= iv || wv3;
            case (st)
                S_IN: begin
                    if (take) begin
                        if (!jv) fs = 1'b1;
                        jv <= job_w;
                    end
                    seen <= seen | (av ? 64'd1 << ra_a : 64'd0) | (bv ? 64'd1 << ra_b : 64'd0);
                    nseen <= nseen + av + bv;
                    if (last) st <= (nbs_c == 4'd1) ? S_IDS : S_SEL;
                end
                S_SEL: if ({1'b0, n} + 4'd1 == nbs) st <= S_IDS;      // beats 1 .. ceil(ne / 64) - 1, one a cycle
                S_IDS: if (iv) begin rw_st <= 1'b1; st <= S_GW; end
                S_GW: begin                                   // ids row (renumbered) next edge, the gathered row on arrival
                    if (n == 3'd0) rw_v <= 1'b1;
                    if (gv) begin rw_v <= 1'b1; st <= S_IN; seen <= 64'd0; nseen <= 7'd0; end
                end
                default: st <= S_IN;
            endcase
            fault_k <= fault_k | fs; fault <= fault_k | fs;
        end
    // the job / window registers (no reset: loaded only on a job write / the window's first beat / the sequencer steps)
    always @(posedge clk) begin
        if (job_w) begin jset <= wd[40 +: SB]; jsm <= wd[15:0]; jlm <= wd[20:16]; jrow <= wd[30:21]; jne <= wd[39:31]; end
        case (st)
            S_IN: begin
                if (take) begin
                    cset <= jset; ne <= jne; row <= jrow; lmask <= jlm; smask <= jsm;
                    nsc <= 7'((jne + 9'd6) / 9'd7); rws_k <= rscale[jset];
                end
                if (last) begin n <= 3'd1; nbs <= nbs_c; end
            end
            S_SEL: n <= n + 3'd1;
            S_IDS: if (iv) n <= 3'd0;
            S_GW:  if (n == 3'd0) n <= 3'd1;
            default: ;
        endcase
    end
    // per-front control of the beat issued this edge
    always @(posedge clk) begin
        sa_r <= ra_a; sa_d <= ab[52 +: 224]; sb_r <= ra_b; sb_d <= bb[52 +: 224];
        c_fw <= last; c_bn <= bn_n; c_l <= go_n && ({1'b0, bn_n} + 4'd1 == nb_n);
        for (q = 0; q < 4; q = q + 1) begin : lv
            integer rem;
            rem = ne_n - 64 * bn_n - 16 * q;
            c_lvn[5 * q +: 5] <= (rem <= 0) ? 5'd0 : (rem >= 16) ? 5'd16 : 5'(rem);
        end
        // bias read address one beat ahead: beat 0 of the coming window while it fills, beat 1 on `last`, n + 1 in S_SEL
        ra <= (st == S_SEL) ? {cset, n + 3'd1} : last ? {set_t, 3'd1} : {set_x, 3'd0};
        rw_row <= row; rw_lm <= lmask; rw_sm <= smask;
        rw_l <= gv;
        rw_x <= 192'd0;
        if (gv) rw_x[191:0] <= gd;
        else for (i2 = 0; i2 < K; i2 = i2 + 1) rw_x[32 * i2 +: IW] <= i2[IW-1:0];
    end
    // ---------------------------------------------------------------- router CTL out (ids row here, weights from L3)
    function automatic [V-1:0] ctl(input [9:0] a, input [3:0] m, input [127:0] d, input [15:0] sm, input [4:0] lm,
                                   input [3:0] s);
        reg [185:0] p;
        begin
            p = 186'd0; p[15:0] = sm; p[20:16] = 5'd5; p[25:21] = lm;
            p[26 +: 10] = a; p[36 +: 4] = m; p[40 +: 128] = d;
            ctl = {V{1'b0}}; ctl[0] = 1'b1; ctl[12:9] = s; ctl[21 +: 186] = p;
        end
    endfunction
    // CTL row bus packed (S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins)): a CTL row word has 106 bits that are constant 0 on every
    // producer (bits 1..8, 13..20, 38, 40, 41 and 189..275 of ctl(): the 5'd5 kind field's zeros, the free header bits and
    // the tail above the 128-bit data); the seam carries the other 170 = {w[188:42], w[39], w[37:21], w[12:9], w[0]}.
    function automatic [169:0] ctlpk(input [275:0] w); ctlpk = {w[188:42], w[39], w[37:21], w[12:9], w[0]}; endfunction
    function automatic [275:0] ctlup(input [169:0] p);
        ctlup = {87'd0, p[169:23], 2'd0, p[22], 1'b0, p[21:5], 8'd0, p[4:1], 8'd0, p[0]};
    endfunction
    // the collector's ids are zero when idle: header gated by its valid, ids OR'd in (both from this leaf's pin flops)
    wire [31:0] pk0 = {5'd0, ids[IW * 2 +: IW], ids[IW * 1 +: IW], ids[IW * 0 +: IW]};
    wire [31:0] pk1 = {5'd0, ids[IW * 5 +: IW], ids[IW * 4 +: IW], ids[IW * 3 +: IW]};
    reg [V-1:0] idb;
    always @(*) begin idb = {V{1'b0}}; idb[61 +: 64] = {pk1, pk0}; end
    always @(posedge clk)
        ct_b <= ctlpk((iv ? ctl(row, 4'h3, 128'd0, smask, lmask, sid_c) : {V{1'b0}}) | idb | (wv3 ? wb3 : {V{1'b0}}));
endmodule
