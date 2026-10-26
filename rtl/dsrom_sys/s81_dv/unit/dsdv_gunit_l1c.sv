`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT-L1 (2026-10-17): dsdv_gunit_l1c -- router select COLLECTOR leaf of dsdv_gunit (E of the four fronts
// dsdv_gunit_l1f): per beat the four fronts' top-6 lists -> one top-8 list (two merge levels, the front number q
// inserted into each record's index: global index = {b, q, k}), a running top-8 over the beats (two interleaved
// accumulators on one 2-stage merge8: acc_t = top8(list_t U acc_{t-2}), beats back to back), the final merge of the two
// accumulators, the first K = 6 sorted by ascending index (sort8 on {valid, ~index, ninf}, three exchanges a stage),
// then:
//   ids out  -> the stack leaf L1 (zero when idle: forms the ids CTL row there);
//   gather   -> per-front hit bits + local {b, k} of each id -> the fronts reply with the unbiased scores -> OR -> the
//              one-row score operand of the routing weights (stack -> L3).
// Exact by construction: every merge keeps the exact top 8 of its inputs under the golden's total order (records with
// unique indices), so the result is tools/hdc_golden_v41 `sorted(topk_lowest_index(scores + bias, 6))`.
// Timing (edges): front lists land E, level-1 merges E+2, level-2 E+4, accumulator E+6 (+ beats), final merge E+8,
// order sort (output register) E+10 after the last beat's list lands.  Every input lands in a flop; every output
// leaves one.  fault (sticky): a front fault, fewer than K selected.  MUT 10 (bench only): the order sort drops its last
// compare-exchange (a 3-exchange stage).
// S81U-GUNIT-L1b (10-17, NATIVE-2 pin rules, 0 data edges): rst_n drives only ot_rst_relay (2 kept region copies);
// i_v / i_ids leave pin-only output flops (twins of the order sort's last register, formed from its next value); the
// gather request g_go / g_hit / g_a leaves on the SAME edge as i_v (was one edge later) -- the fronts spend that edge
// decoding it (dsdv_gunit_l1f), so the gather reply lands on the same edge as before.  The accumulator's "fresh" select
// is a flop of its own and an empty (fresh / single) operand clears only the VALID bits of the fed-back list (invalid
// records order below every valid one, so every valid record lands where the zeroed list put it: same outputs).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l1c #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // W face (fronts q = 0..3, packed by q)
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins): the collector reads f_v / f_f / f_l / f_g of front 0 only (fronts 1..3 leave
    // those outputs open: one shared L1f master) and no f_d bit 205 of any front (L1f o_d is packed, 245 bits per front)
    input  wire [0:0]    f_v, input wire [0:0] f_f, input wire [0:0] f_l, input wire [0:0] f_g,
    input  wire [4*245-1:0] f_d, input wire [3:0] f_flt,
    output reg           g_go, output reg [23:0] g_hit, output reg [41:0] g_a,
    // stack L1
    output reg           i_v, output reg [53:0] i_ids,
    output reg           s_v, output reg [191:0] s_d,
    output reg           fault
);
    localparam integer FE = 41, EW = 43, LW = 8 * EW, K = 6, XW = 11;
    integer i, j;
    wire [1:0] rq;                            // relayed resets: rq[0] the W half (inputs, merges), rq[1] the rest
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    // ---------------------------------------------------------------- input flops
    reg [3:0] fv, ff, fl, fg, ft; reg [4*246-1:0] fd;
    always @(posedge clk or negedge rq[0])
        if (!rq[0]) begin fv <= 4'd0; fg <= 4'd0; ft <= 4'd0; end else begin fv <= {3'd0, f_v}; fg <= {3'd0, f_g}; ft <= f_flt; end
    always @(posedge clk) begin
        ff <= {3'd0, f_f}; fl <= {3'd0, f_l};
`ifdef OT_RTLC_MUT_L1C   // RTLC bench mutant: front words unpacked from the wrong 245-bit slot (fronts rotated)
        for (i = 0; i < 4; i = i + 1) fd[246 * i +: 246] <= {f_d[245 * ((i + 1) % 4) + 205 +: 40], 1'b0, f_d[245 * ((i + 1) % 4) +: 205]};
`else
        for (i = 0; i < 4; i = i + 1) fd[246 * i +: 246] <= {f_d[245 * i + 205 +: 40], 1'b0, f_d[245 * i +: 205]};
`endif
    end
    // records: front record {v, key[32], ~{b[3], k[4]}, ninf} -> {v, key, ~b, ~q, ~k, ninf}; slots 6, 7 empty
    reg [4*LW-1:0] L;
    always @(*) begin
        L = {4*LW{1'b0}};
        for (i = 0; i < 4; i = i + 1)
            for (j = 0; j < K; j = j + 1) begin : rec
                reg [FE-1:0] e; reg [1:0] qq;
                e = fd[246 * i + FE * j +: FE]; qq = i[1:0];
                L[LW * i + EW * j +: EW] = {e[40:5], ~qq, e[4:0]};
            end
    end
    // ---------------------------------------------------------------- per-beat merges (flags {l, f, v} of front 0)
    wire [2:0] fl0 = {fl[0], ff[0], fv[0]};
    wire [LW-1:0] m01, m23, mb; wire [2:0] g01, g23, gb, gbn;
    dsdv_sel_merge8 #(.EW(EW), .FW(3)) u_m01 (.clk(clk), .rst_n(rq[0]), .fi(fl0), .a(L[0 +: LW]), .b(L[LW +: LW]), .fo(g01), .q(m01), .fp());
    dsdv_sel_merge8 #(.EW(EW), .FW(3)) u_m23 (.clk(clk), .rst_n(rq[0]), .fi(fl0), .a(L[2*LW +: LW]), .b(L[3*LW +: LW]), .fo(g23), .q(m23), .fp());
    dsdv_sel_merge8 #(.EW(EW), .FW(3)) u_mb (.clk(clk), .rst_n(rq[0]), .fi(g01), .a(m01), .b(m23), .fo(gb), .q(mb), .fp(gbn));
    // ---------------------------------------------------------------- running top 8: two interleaved accumulators
    // beat t enters with acc_{t-2} (the merge's own output this cycle); beats 0 and 1 of a segment enter with empty.
    wire [LW-1:0] acc; wire [3:0] ga_f;       // {single, l, f, v} at the accumulator output
    // fresh = gb[1] || (gb[0] && gb[1] one cycle ago), registered one cycle ahead from u_mb's next flags
    reg  fresh;
    always @(posedge clk or negedge rq[1]) if (!rq[1]) fresh <= 1'b0; else fresh <= gbn[1] || (gb[0] && gb[1]);
    // an empty operand: the fed-back list with its valid bits cleared (all invalid -> below every valid record)
    function automatic [LW-1:0] novalid(input [LW-1:0] x, input z);
        integer e;
        begin novalid = x; for (e = 0; e < 8; e = e + 1) novalid[EW * e + EW - 1] = x[EW * e + EW - 1] && !z; end
    endfunction
    dsdv_sel_merge8 #(.EW(EW), .FW(4)) u_acc (.clk(clk), .rst_n(rq[1]), .fi({gb[1] && gb[2], gb}), .a(mb),
        .b(novalid(acc, fresh)), .fo(ga_f), .q(acc), .fp());
    reg [LW-1:0] hold;                        // acc_{t-1}
    always @(posedge clk) hold <= acc;
    // ---------------------------------------------------------------- final merge of the two accumulators
    wire [LW-1:0] fin; wire [0:0] gfv;
    dsdv_sel_merge8 #(.EW(EW), .FW(1)) u_fin (.clk(clk), .rst_n(rq[1]), .fi(ga_f[0] && ga_f[2]), .a(acc),
        .b(novalid(hold, ga_f[3])), .fo(gfv), .q(fin), .fp());
    // ---------------------------------------------------------------- first K, ascending index (output register zeroed when idle)
    wire [8*XW-1:0] xd, xq, xn; wire xv, xnv;
    genvar l;
    generate
        for (l = 0; l < 8; l = l + 1) begin : g_x
            wire [EW-1:0] e = fin[EW * l +: EW];
            assign xd[XW * l +: XW] = (l < K && e[EW-1]) ? {1'b1, e[9:1], e[0]} : {XW{1'b0}};
        end
    endgenerate
    dsdv_sel_sort8 #(.EW(XW), .CPS(3), .FW(1), .ZQ(1), .MUT(MUT)) u_ord (.clk(clk), .rst_n(rq[1]), .fi(gfv), .d(xd), .fo(xv), .q(xq),
        .fn(xnv), .qn(xn));
    // the ids of the order sort's next register (zero when idle), for the pin-only output flops and the gather request
    wire [53:0] idn;
    generate
        for (l = 0; l < K; l = l + 1) begin : g_o
            assign idn[9 * l +: 9] = ~xn[XW * l + 1 +: 9] & {9{xn[XW * l + XW - 1] && xnv}};
        end
    endgenerate
    wire allk = &{xq[XW*5+XW-1], xq[XW*4+XW-1], xq[XW*3+XW-1], xq[XW*2+XW-1], xq[XW*1+XW-1], xq[XW-1]};
    // ---------------------------------------------------------------- gather request / reply
    // S81-KITS-RTLB 10-24 (owner: register every pin, in RTL): (1) fault leaves a pin-only flop loaded with
    // the kept sticky state's next value (fault == flt_s every cycle); (2) the fault check reads its own kept twin xv_k of
    // the order sort's fo (= xnv one edge later, same reset), so synthesis no longer folds fo into the g_go pin flop
    // (g_go fed the fault logic: face_guard 'shared').  0 cycles.
    (* keep *) reg flt_s; (* keep *) reg xv_k;
    wire flt_n = flt_s | (|ft) | (xv_k && !allk);
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin i_v <= 1'b0; g_go <= 1'b0; g_hit <= 24'd0; s_v <= 1'b0; fault <= 1'b0; flt_s <= 1'b0; xv_k <= 1'b0; end
        else begin
            i_v <= xnv; g_go <= xnv; xv_k <= xnv;
            for (i = 0; i < 4; i = i + 1)
                for (j = 0; j < K; j = j + 1) g_hit[6 * i + j] <= xnv && idn[9 * j + 4 +: 2] == i[1:0];
            s_v <= fg[0];
            flt_s <= flt_n;
`ifdef OT_RTLB_PINFLOP_MUT
            fault <= |ft;                                  // mutant: pin flop not sticky, check dropped
`else
            fault <= flt_n;
`endif
        end
    always @(posedge clk) begin
        i_ids <= idn;
        for (j = 0; j < K; j = j + 1) g_a[7 * j +: 7] <= {idn[9 * j + 6 +: 3], idn[9 * j +: 4]};
        s_d <= fd[0 +: 192] | fd[246 +: 192] | fd[492 +: 192] | fd[738 +: 192];
    end
endmodule
