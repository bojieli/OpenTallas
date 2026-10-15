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
// TP8 (qwen-tp8/par-tt, results/arch/qwen_tp8_1012): NBP = 3 -> 3 bands (GT 3,072), LG 12, splits 7..12; the reference
// stays the GT 6,144 lane (a group g < 3072 >> s only reads bands 0..2's positions, so the same lane is the golden).
// MUT = 3: the upper's band-index mutant (band words in reverse band order; MUT 2 is a no-op at NB 3) -> FAIL.
// NBP = 6 (default) is the unchanged TP4 bench (same LG 13, same stimulus).
// qwen-tp8/spine 2026-10-12: at NB 3 the upper holds level 11 only (LG - 11 levels; level 12 = LG is the port's hold),
// so the bands' ty is 8 edges earlier (LAT_B 38 + 2 LNK); the GT-6,144 lane's level-12 hold is a copy for every
// in-range group (3072 >> s, s <= 11), so the same lane stays the golden.  MUT = 4: the pre-fix 2-level upper -> FAIL at NB 3
// (a no-op at NB 6).
module tb_qfd_band_lanes;
    parameter integer NL = 4, LNK = 0, MUT = 0, NOPS = 3000, SEED = 1;
    parameter integer RDMEM = 0, BANR = 0;   // el1011-q-seq: DUT delay lines in SRAM (2 = one-edge-short mutant) / valid-only adder resets
    parameter integer NBP = 6;               // bands: 6 (TP4, GT 6,144) or 3 (TP8, GT 3,072)
    parameter integer BL = 0;                // el1013-qwen-small-masters r3b: 1 = each band is the slot composition qfd_sp_band_lanes (16 x qfd_bl_lane); 2 = its lnk strap wrong
    parameter integer CDLY = 2;              // CL=1: leaf c-tap delay of the cluster (1 = the hardened leaf, selects one edge late)
    parameter integer RPIN = 0, RSTX = 0;   // q14 r11: CL=2 leaf reset pin register; RSTX = extra idle edges after reset release (die schedule)
    parameter integer CL = 0;                // el1013-qwen-small-masters: 1 = the tree top is the die CLUSTER cell qfd_tt_up4 (NL 16, NBP 3, LNK 1:
                                             // its two pin stages ARE the one link relay stage; no u_l1..u_l4 delay on its links, sel undelayed)
    localparam integer NB = NBP, LG = $clog2(NB * 1024), LAT_L = 41, LAT_B = ((BL != 0) ? 4 : 0) + 46 + 2 * LNK - 8 * (13 - LG);   // qwen-tp8/spine: the upper has LG-11 levels
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
    reg [LG:0] upper_sel0,upper_sel1,upper_tv0,upper_tv1;
    always @(posedge clk) begin
        upper_sel0<=sel[LG:0];upper_sel1<=upper_sel0;
        upper_tv0<=rst_n ? tv[LG:0] : 0;upper_tv1<=rst_n ? upper_tv0 : 0;
    end
    wire [LG:0] upper_sel=(BL!=0) ? upper_sel1 : sel[LG:0];
    wire [LG:0] upper_tv=(BL!=0) ? upper_tv1 : tv[LG:0];
    // ---- DUT: 6 band blocks + upper, LNK relays on each link ---------------------------------------------------------
    wire [NB*NL*32-1:0] pw, pw_r;
    wire [NB-1:0] pv, pv_r, bf, bf_r;
    wire [8*NL*32-1:0] ty [0:NB-1];
    wire [3*NL*32-1:0] tt, tt_r;
    wire tu, tvv, tu_r, tv_r2, uf;
    generate for (b = 0; b < NB; b = b + 1) begin : g_band
        if (BL == 0) begin : g_flatb
            ot_qfd_band_lanes #(.NL(NL), .LNK(LNK), .MUT((MUT == 1 || MUT == 4) ? MUT : 0), .RDMEM(RDMEM), .BANR(BANR), .LG(LG)) u_b (
                .clk(clk), .rst_n(rst_n), .b0(b == 0), .tw(din[b*8*NL*32 +: 8*NL*32]), .sel_e(sel[LG:0]), .tv_e(tv[LG:0]),
                .tt_ty(b == 0 ? tt_r : {3*NL*32{1'b0}}), .tt_use(b == 0 ? tu_r : 1'b0), .tt_v(b == 0 ? tv_r2 : 1'b0),
                .pw(pw[b*NL*32 +: NL*32]), .pw_v(pv[b]), .ty(ty[b]), .fault(bf[b]));
        end else begin : g_slotb
            // el1013-qwen-small-masters r3b: the band is the die slot composition qfd_sp_band_lanes (16 hardened one-lane
            // leaves qfd_bl_lane, wires only), driven through its contract bundles; the link relay count is its strap
            // (BL = 2: strap one stage short of the bench's relays -> must FAIL)
            wire [512:0] spw;
            initial if (NL != 16 || NB != 3) begin $display("FAIL qfd_band_lanes BL needs NL 16, NBP 3"); $fatal(1); end
            qfd_sp_band_lanes u_b (.ck(clk), .ck_l0(clk), .ck_l1(clk), .ck_l2(clk), .ck_l3(clk), .ck_l4(clk), .ck_l5(clk), .ck_l6(clk), .ck_l7(clk), .ck_l8(clk), .ck_l9(clk), .ck_l10(clk), .ck_l11(clk), .ck_l12(clk), .ck_l13(clk), .ck_l14(clk), .ck_l15(clk), .rst_n(rst_n), .b0(b == 0), .lnk(6'(BL == 2 ? LNK + 1 : LNK)), .tw(din[b*8*NL*32 +: 8*NL*32]),
                .c({tv[LG:0], sel[LG:0]}), .tt(b == 0 ? {tv_r2, tu_r, tt_r} : 1538'd0), .pw(spw), .ty(ty[b]), .f(bf[b]));
            assign pw[b*NL*32 +: NL*32] = spw[511:0];
            assign pv[b] = spw[512];
        end
    end endgenerate
    generate if (CL == 0) begin : g_flat
        ot_hdc_delay #(.W(NB*NL*32), .D(LNK)) u_l1 (.clk(clk), .rst_n(rst_n), .d(pw), .q(pw_r));
        ot_hdc_delay #(.W(2*NB), .D(LNK), .RESET(1)) u_l2 (.clk(clk), .rst_n(rst_n), .d({pv, bf}), .q({pv_r, bf_r}));
        ot_hdc_delay #(.W(3*NL*32), .D(LNK)) u_l3 (.clk(clk), .rst_n(rst_n), .d(tt), .q(tt_r));
        ot_hdc_delay #(.W(2), .D(LNK), .RESET(1)) u_l4 (.clk(clk), .rst_n(rst_n), .d({tu, tvv}), .q({tu_r, tv_r2}));
        ot_qfd_band_upper #(.NL(NL), .NB(NB), .LNK(LNK), .MUT((MUT == 2 || MUT == 3 || MUT == 4) ? MUT : 0), .LG(LG)) u_up (
            .clk(clk), .rst_n(rst_n), .pw(pw_r), .pw_v(pv_r), .lf(bf_r), .sel_e(upper_sel), .tv_e(upper_tv),
            .tt_ty(tt), .tt_use(tu), .tt_v(tvv), .fault(uf));
    end else if (CL == 2) begin : g_w
        // the slot without a parent: 4 leaves through the wires-only wrapper qfd_tt_up4_w, the die's fan-out of the
        // selects / valids / faults and its OR of the leaf faults done here; link relays exactly as the flat build
        initial if (NL != 16 || NB != 3) begin $display("FAIL qfd_band_lanes CL=2 needs NL 16, NBP 3"); $fatal(1); end
        ot_hdc_delay #(.W(NB*NL*32), .D(LNK)) u_l1 (.clk(clk), .rst_n(rst_n), .d(pw), .q(pw_r));
        ot_hdc_delay #(.W(2*NB), .D(LNK), .RESET(1)) u_l2 (.clk(clk), .rst_n(rst_n), .d({pv, bf}), .q({pv_r, bf_r}));
        ot_hdc_delay #(.W(3*NL*32), .D(LNK)) u_l3 (.clk(clk), .rst_n(rst_n), .d(tt), .q(tt_r));
        ot_hdc_delay #(.W(2), .D(LNK), .RESET(1)) u_l4 (.clk(clk), .rst_n(rst_n), .d({tu, tvv}), .q({tu_r, tv_r2}));
        wire [4*384-1:0] wpw, wty;
        wire [3:0] wtu, wtv, wfl;
        genvar wl, wb, wj;
        for (wl = 0; wl < 4; wl = wl + 1) begin : g_s
            for (wb = 0; wb < 3; wb = wb + 1) begin : g_b
                for (wj = 0; wj < 4; wj = wj + 1) begin : g_j
                    assign wpw[384*wl + 32*(wb*4 + wj) +: 32] = pw_r[512*wb + 32*(4*wl + wj) +: 32];
                    assign tt[32*(wb*16 + 4*wl + wj) +: 32] = wty[384*wl + 32*(wb*4 + wj) +: 32];
                end
            end
        end
        // CDLY 1 = the HARDENED leaf (LNK 0, DLY 1: tb LNK must be 0): the die's control tile delivers the selects one
        // edge later (its output station), modelled by one flop on sel / tv.  CDLY 2: the leaf at the bench's own timing.
        reg [2*(LG+1)-1:0] wsel_st;
        always @(posedge clk or negedge rst_n) if (!rst_n) wsel_st <= {2*(LG+1){1'b0}}; else wsel_st <= {tv[LG:0], sel[LG:0]};
        wire [2*(LG+1)-1:0] wsel = (CDLY == 1) ? wsel_st : {tv[LG:0], sel[LG:0]};
        initial if (CDLY == 1 && LNK != 0) begin $display("FAIL qfd_band_lanes CL=2 CDLY=1 is the hard leaf: LNK 0"); $fatal(1); end
        qfd_tt_up4_w #(.DLY(CDLY == 1 ? 1 : 2 + LNK), .LNK(LNK), .LMUT((MUT == 2 || MUT == 3) ? MUT : 0), .RPIN(RPIN)) u_up (
            .ck({4{clk}}), .rst_n({4{rst_n}}), .pw_l(wpw), .pv_l({4{pv_r}}), .lf_l({4{bf_r}}),
            .sel_l({4{wsel}}), .ty_l(wty), .tu_l(wtu), .tv_l(wtv), .flt_l(wfl));
        assign tu = wtu[0]; assign tvv = wtv[0]; assign uf = |wfl;
    end else begin : g_cl
        // the cluster through its own die bundles; packing as documented in rtl/physical/ot_qwen_tt_up4_cluster.sv
        wire [1537:0] cty;
        initial if (NL != 16 || NB != 3 || LNK != 1) begin $display("FAIL qfd_band_lanes CL=1 needs NL 16, NBP 3, LNK 1"); $fatal(1); end
        // CDLY = the cluster leaves' c-tap delay.  2: the selects reach the cluster with the band words (this bench's
        // own timing).  1 = the HARDENED leaf (kit qfd_tt_up4_leaf, die lead's cell definition): the die's control tile
        // delivers the selects one edge later (its output station), modelled here by one flop on sel / tv.
        reg [2*(LG+1)-1:0] sel_st;
        always @(posedge clk or negedge rst_n) if (!rst_n) sel_st <= {2*(LG+1){1'b0}}; else sel_st <= {tv[LG:0], sel[LG:0]};
        wire [2*(LG+1)-1:0] sel_c = (CDLY == 1) ? sel_st : {tv[LG:0], sel[LG:0]};
        initial if (CDLY != 1 && CDLY != 2) begin $display("FAIL qfd_band_lanes CDLY must be 1 or 2"); $fatal(1); end
        qfd_tt_up4 #(.NB(NB), .LG(LG), .DLY(CDLY), .LMUT((MUT == 2 || MUT == 3) ? MUT : 0)) u_up (
            .ck(clk), .rst_n(rst_n), .pw0({pv[0], pw[0*512 +: 512]}), .pw1({pv[1], pw[1*512 +: 512]}), .pw2({pv[2], pw[2*512 +: 512]}),
            .lf0(bf[0]), .lf1(bf[1]), .lf2(bf[2]), .sel(sel_c), .ty(cty), .flt(uf));
        assign tt_r = cty[1535:0];
        assign tu_r = cty[1536];
        assign tv_r2 = cty[1537];
        assign pw_r = pw; assign pv_r = pv; assign bf_r = bf; assign tt = cty[1535:0]; assign tu = cty[1536]; assign tvv = cty[1537];
    end endgenerate
    // q14 r11: CL=2 leaf reset pin register: the leaf's internal reset releases exactly one edge after rst_n (RPIN 1).
    // RPIN 2 (bench mutant: register bypassed) releases on the rst_n edge itself and FAILS here.  The tree-top levels
    // see their first op >= 24 edges after release, so the +1 edge is otherwise invisible to the data check.
    generate if (CL == 2 && RPIN != 0) begin : g_rchk
        integer re = 0;
        always @(posedge clk) if (rst_n) begin
            re = re + 1;
            if (re == 1 && g_w.u_up.g_leaf[0].u_leaf.rs !== 1'b0) begin $display("FAIL qfd_band_lanes leaf reset released on the rst_n edge (no pin register)"); $fatal(1); end
            if (re == 2 && g_w.u_up.g_leaf[0].u_leaf.rs !== 1'b1) begin $display("FAIL qfd_band_lanes leaf reset not released one edge after rst_n"); $fatal(1); end
        end
    end endgenerate
    // ---- op history: cycle n's op (valid, split) -----------------------------------------------------------------------
    localparam integer HN = 1 << 14;
    reg        hv [0:HN-1];
    reg [3:0]  hs [0:HN-1];
    reg [48*NL*32-1:0] yh [0:127];   // the lane's y by cycle (mod 128)
    reg [8*NL*32-1:0] tyh [0:NB-1][0:127];   // the bands' ty by cycle (mod 128): at NB 3 the bands lead the LG-13 lane (LAT_B < LAT_L)
    localparam integer LAT_C = (LAT_B > LAT_L) ? LAT_B : LAT_L;   // check op n-LAT_C once both its band and lane words exist
    integer n = 0, i, k, g, s, ops = 0, checks = 0, groups = 0, errors = 0, seed = SEED;
    initial begin seed = SEED; $display("SEED=%0d", seed); end  // runtime seed: Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
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
        repeat (RSTX) @(negedge clk);
        while (n < NOPS + 200) begin
            // ---- check outputs (negedge n: op n-LAT_C; its ty at +LAT_B, the lane's y at +41) ---------------------------
            yh[n % 128] = ry;
            for (i = 0; i < NB; i = i + 1) tyh[i][n % 128] = ty[i];
            if (n >= LAT_C && hv[(n - LAT_C) % HN]) begin
                s = hs[(n - LAT_C) % HN];
                for (g = 0; g < ((NB * 1024) >> s); g = g + 1) begin
                    for (k = 0; k < NL; k = k + 1) begin
                        if (tyh[band_of(s, g)][(n - LAT_C + LAT_B) % 128][32*(slot_of(s, g)*NL + k) +: 32] !== yh[(n - LAT_C + LAT_L) % 128][32*(g*NL + k) +: 32]) begin
                            if (errors < 5) $display("MISMATCH op@%0d split %0d group %0d lane %0d: band %h lane %h", n - LAT_C, s, g, k,
                                tyh[band_of(s, g)][(n - LAT_C + LAT_B) % 128][32*(slot_of(s, g)*NL + k) +: 32], yh[(n - LAT_C + LAT_L) % 128][32*(g*NL + k) +: 32]);
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
            csplit = 7 + ({$random(seed)} % (LG - 6));
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
        if (errors != 0) begin $display("FAIL qfd_band_lanes %0d mismatching words of %0d (ops %0d, NL %0d, NB %0d, LNK %0d, MUT %0d)",
            errors, checks, ops, NL, NB, LNK, MUT); $fatal(1); end
        $display("PASS qfd_band_lanes ops=%0d groups=%0d words=%0d NL=%0d NB=%0d LG=%0d LNK=%0d latency=+%0d faults(finite 0/0, NaN 1/1)",
            ops, groups, checks, NL, NB, LG, LNK, LAT_B - LAT_L);
        $finish;
    end
endmodule
