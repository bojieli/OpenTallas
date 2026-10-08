`timescale 1ns/1ps
// qwen-lane-band 2026-10-08: the 6 per-band lane blocks (ot_qfd_band_lanes) + the tree top's upper levels
// (ot_qfd_band_upper), reassembled with LNK relay stages on every band <-> tree-top link, against NL copies of the
// existing lane (ot_qwen_spine_lane, TREE_LAT 7) fed the same words and the same split-derived per-level select /
// valid (ot_qwen_spine_lane_credit's generation: tv[lv] = v && split >= lv at D = 8(lv-8), sel[lv] = split >= lv at
// D + 7).  Ops: random FP32 words (mixed exponents, so a reordered sum rounds differently), random split 7..13, random
// valid gaps, plus back-to-back runs.  Check, for every valid op and every in-range result group g < 6144 >> split:
// the band-local slot holding g (ot_qfd_band_lanes header) == the lane's y[g], bit-exact, 5 + 2 LNK edges later.
// Faults: phase 1 finite words -> both sides stay 0; phase 2 a NaN in a split-12 op -> both sides raise.
// MUT = 1 / 2: the band / upper negative mutants (wrong combine order) -> FAIL.
module tb_qfd_band_lanes;
    parameter integer NL = 4, LNK = 0, MUT = 0, NOPS = 3000, SEED = 1;
    localparam integer NB = 6, LAT_L = 41, LAT_B = 46 + 2 * LNK;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    // ---- stimulus -----------------------------------------------------------------------------------------------
    reg [48*NL*32-1:0] din;          // (position p, lane l) at [32*(p*NL + l)]
    reg [13:0] sel, tv;
    // ---- reference: NL lanes -----------------------------------------------------------------------------------------
    wire [48*NL*32-1:0] ry;
    wire [NL-1:0] rf;
    genvar l, p, b;
    generate for (l = 0; l < NL; l = l + 1) begin : g_ref
        wire [48*32-1:0] ti, yo;
        for (p = 0; p < 48; p = p + 1) begin : g_p
            assign ti[32*p +: 32] = din[32*(p*NL + l) +: 32];
            assign ry[32*(p*NL + l) +: 32] = yo[32*p +: 32];
        end
        ot_qwen_spine_lane #(.TREE_LAT(7), .OSTN(0)) u_lane (clk, rst_n, ti, sel, tv, yo, rf[l]);
    end endgenerate
    // ---- DUT: 6 band blocks + upper, LNK relays on each link ---------------------------------------------------------
    wire [NB*NL*32-1:0] pw, pw_r;
    wire [NB-1:0] pv, pv_r, bf, bf_r;
    wire [8*NL*32-1:0] ty [0:NB-1];
    wire [3*NL*32-1:0] tt, tt_r;
    wire tu, tvv, tu_r, tv_r2, uf;
    generate for (b = 0; b < NB; b = b + 1) begin : g_band
        ot_qfd_band_lanes #(.NL(NL), .LNK(LNK), .MUT(MUT == 1 ? 1 : 0)) u_b (
            .clk(clk), .rst_n(rst_n), .b0(b == 0), .tw(din[b*8*NL*32 +: 8*NL*32]), .sel_e(sel), .tv_e(tv),
            .tt_ty(b == 0 ? tt_r : {3*NL*32{1'b0}}), .tt_use(b == 0 ? tu_r : 1'b0), .tt_v(b == 0 ? tv_r2 : 1'b0),
            .pw(pw[b*NL*32 +: NL*32]), .pw_v(pv[b]), .ty(ty[b]), .fault(bf[b]));
    end endgenerate
    ot_hdc_delay #(.W(NB*NL*32), .D(LNK)) u_l1 (.clk(clk), .rst_n(rst_n), .d(pw), .q(pw_r));
    ot_hdc_delay #(.W(2*NB), .D(LNK), .RESET(1)) u_l2 (.clk(clk), .rst_n(rst_n), .d({pv, bf}), .q({pv_r, bf_r}));
    ot_hdc_delay #(.W(3*NL*32), .D(LNK)) u_l3 (.clk(clk), .rst_n(rst_n), .d(tt), .q(tt_r));
    ot_hdc_delay #(.W(2), .D(LNK), .RESET(1)) u_l4 (.clk(clk), .rst_n(rst_n), .d({tu, tvv}), .q({tu_r, tv_r2}));
    ot_qfd_band_upper #(.NL(NL), .NB(NB), .LNK(LNK), .MUT(MUT == 2 ? 2 : 0)) u_up (
        .clk(clk), .rst_n(rst_n), .pw(pw_r), .pw_v(pv_r), .lf(bf_r), .sel_e(sel), .tv_e(tv),
        .tt_ty(tt), .tt_use(tu), .tt_v(tvv), .fault(uf));
    // ---- op history: cycle n's op (valid, split) -----------------------------------------------------------------------
    localparam integer HN = 1 << 14;
    reg        hv [0:HN-1];
    reg [3:0]  hs [0:HN-1];
    reg [48*NL*32-1:0] yh [0:127];   // the lane's y by cycle (mod 128)
    integer n = 0, i, k, g, s, ops = 0, checks = 0, groups = 0, errors = 0, seed = SEED;
    integer lv, d;
    reg rstick = 0, dstick = 0;
    function automatic [31:0] rfp(input integer dummy);
        reg [31:0] r;
        begin r = $random(seed); rfp = {r[31], 8'd112 + {3'd0, r[27:23]}, r[22:0]}; end   // exponents 112..143
    endfunction
    function automatic integer band_of(input integer s_, input integer g_);   // the band-local slot of group g
        if (s_ <= 10) band_of = g_ >> (10 - s_); else band_of = 0;
    endfunction
    function automatic integer slot_of(input integer s_, input integer g_);
        if (s_ <= 10) slot_of = g_ & ((1 << (10 - s_)) - 1); else slot_of = g_;
    endfunction
    integer phase = 1, nan_at = -1;
    reg [3:0] csplit; reg cv;
    initial begin
        din = 0; sel = 0; tv = 0;
        for (i = 0; i < HN; i = i + 1) begin hv[i] = 0; hs[i] = 7; end
        repeat (3) @(posedge clk);
        @(negedge clk); rst_n = 1;
        while (n < NOPS + 200) begin
            // ---- check outputs (negedge n: the lane's y is op n-41, the bands' ty op n-LAT_B) ---------------------------
            yh[n % 128] = ry;
            if (n >= LAT_B && hv[(n - LAT_B) % HN]) begin
                s = hs[(n - LAT_B) % HN];
                for (g = 0; g < (6144 >> s); g = g + 1) begin
                    for (k = 0; k < NL; k = k + 1) begin
                        if (ty[band_of(s, g)][32*(slot_of(s, g)*NL + k) +: 32] !== yh[(n - LAT_B + LAT_L) % 128][32*(g*NL + k) +: 32]) begin
                            if (errors < 5) $display("MISMATCH op@%0d split %0d group %0d lane %0d: band %h lane %h", n - LAT_B, s, g, k,
                                ty[band_of(s, g)][32*(slot_of(s, g)*NL + k) +: 32], yh[(n - LAT_B + LAT_L) % 128][32*(g*NL + k) +: 32]);
                            errors = errors + 1;
                        end
                        checks = checks + 1;
                    end
                    groups = groups + 1;
                end
            end
            rstick = rstick | (|rf); dstick = dstick | uf;
            // ---- phase 1 end: drained, both fault-free ------------------------------------------------------------------
            if (n == NOPS / 2 + 120) begin
                if (rstick || dstick) begin $display("FAIL qfd_band_lanes finite-phase fault ref %0d dut %0d", rstick, dstick); $fatal(1); end
                phase = 2;
            end
            // ---- drive op n ---------------------------------------------------------------------------------------------
            cv = (n < NOPS / 2 || (n >= NOPS / 2 + 130 && n < NOPS)) && ((n % 97) < 60 ? 1'b1 : ($random(seed) & 1));
            csplit = 7 + ({$random(seed)} % 7);
            if (phase == 2 && nan_at < 0 && cv) begin csplit = 12; nan_at = n; end
            hv[n % HN] = cv; hs[n % HN] = csplit;
            for (i = 0; i < 48 * NL; i = i + 1) din[32*i +: 32] = rfp(0);
            if (nan_at == n) din[31:0] = 32'h7FC00001;
            if (cv) ops = ops + 1;
            sel = 0; tv = 0;
            for (lv = 8; lv <= 12; lv = lv + 1) begin
                d = 8 * (lv - 8);
                if (n - d >= 0) tv[lv] = hv[(n - d) % HN] && (hs[(n - d) % HN] >= lv);
                if (n - d - 7 >= 0) sel[lv] = hs[(n - d - 7) % HN] >= lv;
            end
            @(posedge clk); @(negedge clk);
            n = n + 1;
        end
        if (!(rstick && dstick)) begin $display("FAIL qfd_band_lanes NaN phase: ref fault %0d dut fault %0d", rstick, dstick); $fatal(1); end
        if (errors != 0) begin $display("FAIL qfd_band_lanes %0d mismatching words of %0d (ops %0d, NL %0d, LNK %0d, MUT %0d)",
            errors, checks, ops, NL, LNK, MUT); $fatal(1); end
        $display("PASS qfd_band_lanes ops=%0d groups=%0d words=%0d NL=%0d LNK=%0d latency=+%0d faults(finite 0/0, NaN 1/1)",
            ops, groups, checks, NL, LNK, LAT_B - LAT_L);
        $finish;
    end
endmodule
