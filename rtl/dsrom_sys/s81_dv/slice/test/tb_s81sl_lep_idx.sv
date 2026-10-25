`timescale 1ns/1ps
// S81/H4 (2026-10-24, COORD H4 ruling option A): bench of the index rank-tree frames of the s_0N lep
// (ot_s81sl_lep_mu_ab_idx = ot_s81sl_lep_mu_ab + IDX_EN 1, production opt-ins RX_SRAM 1 / IN_PIPE 1 / NATIVE32 1).
// Two stage dies, both s_0N ends, on the two stage circuits as the rack wires them (RELEASE_RACK S81 links: pair A =
// stage NEXT, pair B = stage PREV): D0 pair A (lanes 0/1) <-> D1 pair B (lanes 2/3) and D0 pair B <-> D1 pair A, each
// through the hardened lane tiles dsfd_coll_lane_w (LCR 1) and the behavioural PMA ot_pdie_ucie (lane 1 skewed).
// Static calendar (main phase): every 4 cycles slot 0 = an untagged XB ring beat on ro, slot 1 = a tree beat on tl (tl
//   takes one edge more than ro to the frame -- a pin flop, then the face stage -- so its frame goes out in frame slot 2,
//   two cycles from the ring frames: the receiver releases pair A and pair B from one head, and the compiler keeps the
//   two pairs' arrivals in different cycles);
//   D0 tl beats carry lane 2 (child slot A of the parent D1) -> must arrive on D1 ca;  D1 tl beats carry lane 3 -> must
//   arrive on D0 cb.  Rate 0.5 frames/cycle < the 0.764 lane cap.
// Checks: every tree beat bit-exact and in order on the right port (D1 ca / D0 cb), nothing ever on D1 cb / D0 ca, every
//   ring beat bit-exact and in order on the peer's ri (tree frames never reach ri), no fault in the main phase; then
//   F1 a tree beat on a ring-beat cycle -> D0 fault, F2 a tree beat with lane 0 -> D1 fault.
// Mutants (must FAIL): +define+OT_S81SL_LEP_MUT_IDXPAIR (TX pair select inverted), +define+OT_S81SL_LEP_MUT_IDXDMX (RX
//   demux swapped).  Verdict: "PASS lep_idx ..." / "FAIL lep_idx ...".
module tb_s81sl_lep_idx #(parameter integer N = 160, parameter integer SEED = 1, parameter integer WAIT = 6000);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [1103:0] ro0 = 0, ro1 = 0; reg [275:0] tl0 = 0, tl1 = 0;
    wire [1103:0] ri0, ri1; wire [275:0] ca0, cb0, ca1, cb1; wire f0, f1;
    // lane-side nets per die: index l = 0..3 (pair A = 0/1, pair B = 2/3)
    wire [3:0] lv0, lr0, iv0, ir0, lv1, lr1, iv1, ir1, rxv0, rxv1;
    wire [4*553-1:0] ld0, id0, ld1, id1; wire [11:0] fl0, fl1;
    wire [4*512-1:0] tx0, rx0, tx1, rx1; wire [7:0] st0, st1;
    `define TB_LEP(X) \
    ot_s81sl_lep_mu_ab_idx #(.SRAM(1), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u_d``X (.clk(clk), .rst_n(rst_n), .ro(ro``X), .ri(ri``X), \
        .lo0_v(lv``X[0]), .lo0_r(lr``X[0]), .lo0_d(ld``X[0 +: 553]), .lo1_v(lv``X[1]), .lo1_r(lr``X[1]), .lo1_d(ld``X[553 +: 553]), \
        .li0_v(iv``X[0]), .li0_r(ir``X[0]), .li0_d(id``X[0 +: 553]), .li1_v(iv``X[1]), .li1_r(ir``X[1]), .li1_d(id``X[553 +: 553]), \
        .rxv(rxv``X[1:0]), .sl_f(1'b0), .l0_f(fl``X[2:0]), .l1_f(fl``X[5:3]), \
        .mu_c(34'd0), .mu_rt(), .ml_wv(), .ml_wd(), .ml_rv(1'b0), .ml_rd(1104'd0), .ml_f(1'b0), \
        .lo2_v(lv``X[2]), .lo2_r(lr``X[2]), .lo2_d(ld``X[1106 +: 553]), .lo3_v(lv``X[3]), .lo3_r(lr``X[3]), .lo3_d(ld``X[1659 +: 553]), \
        .li2_v(iv``X[2]), .li2_r(ir``X[2]), .li2_d(id``X[1106 +: 553]), .li3_v(iv``X[3]), .li3_r(ir``X[3]), .li3_d(id``X[1659 +: 553]), \
        .rxvb(rxv``X[3:2]), .l2_f(fl``X[8:6]), .l3_f(fl``X[11:9]), .fault(f``X), .tl(tl``X), .ca(ca``X), .cb(cb``X));
    `TB_LEP(0)
    `TB_LEP(1)
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_ln
        dsfd_coll_lane_w #(.LCR(1)) u_l0 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({st0[2*g], st0[2*g+1], rx0[512*g +: 512], rxv0[g]}),
            .tx(tx0[512*g +: 512]), .tf(), .lo_v(lv0[g]), .lo_r(lr0[g]), .lo_d(ld0[553*g +: 553]),
            .li_v(iv0[g]), .li_r(ir0[g]), .li_d(id0[553*g +: 553]), .flt(fl0[3*g +: 3]));
        dsfd_coll_lane_w #(.LCR(1)) u_l1 (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({st1[2*g], st1[2*g+1], rx1[512*g +: 512], rxv1[g]}),
            .tx(tx1[512*g +: 512]), .tf(), .lo_v(lv1[g]), .lo_r(lr1[g]), .lo_d(ld1[553*g +: 553]),
            .li_v(iv1[g]), .li_r(ir1[g]), .li_d(id1[553*g +: 553]), .flt(fl1[3*g +: 3]));
        // D0 lane g <-> D1 lane g ^ 2 (pair A <-> pair B), lane 1 of each pair skewed
        localparam integer h = g ^ 2;
        wire [512:0] pa, pb; wire ta, tb;
        ot_pdie_ucie #(.PMA_LAT(g % 2 == 0 ? 2 : 9)) u_u0 (.clk(clk), .rst(rst_n), .tx(tx0[512*g +: 512]), .rx(rx0[512*g +: 512]),
            .st(st0[2*g +: 2]), .pma_tx(pa), .pma_tck(ta), .pma_rx(pb), .pma_rck(tb));
        ot_pdie_ucie #(.PMA_LAT(g % 2 == 0 ? 2 : 9)) u_u1 (.clk(clk), .rst(rst_n), .tx(tx1[512*h +: 512]), .rx(rx1[512*h +: 512]),
            .st(st1[2*h +: 2]), .pma_tx(pb), .pma_tck(tb), .pma_rx(pa), .pma_rck(ta));
    end endgenerate

    // ------------------------------------------------------------------ scoreboards
    reg [275:0] e1a [0:N+3]; reg [275:0] e0b [0:N+3]; reg [1103:0] e1r [0:N+3]; reg [1103:0] e0r [0:N+3];
    integer n1a = 0, n0b = 0, n1r = 0, n0r = 0, g1a = 0, g0b = 0, g1r = 0, g0r = 0, bad = 0, stray = 0;
    always @(posedge clk) if (rst_n) begin
        if (ca1[0]) begin
            if (g1a >= n1a || ca1 !== e1a[g1a]) begin bad = bad + 1;
                if (bad < 8) $display("MISMATCH D1.ca %0d cyc %0d got %h", g1a, cyc, ca1[63:0]); end
            g1a = g1a + 1;
        end
        if (cb0[0]) begin
            if (g0b >= n0b || cb0 !== e0b[g0b]) begin bad = bad + 1;
                if (bad < 8) $display("MISMATCH D0.cb %0d cyc %0d got %h", g0b, cyc, cb0[63:0]); end
            g0b = g0b + 1;
        end
        if (ca0 !== 276'd0 || cb1 !== 276'd0) begin stray = stray + 1;
            if (stray < 4) $display("STRAY tree beat cyc %0d: D0.ca %h D1.cb %h", cyc, ca0[63:0], cb1[63:0]); end
        if (ri1[0]) begin
            if (g1r >= n1r || ri1 !== e1r[g1r]) begin bad = bad + 1;
                if (bad < 8) $display("MISMATCH D1.ri %0d cyc %0d got %h", g1r, cyc, ri1[63:0]); end
            g1r = g1r + 1;
        end
        if (ri0[0]) begin
            if (g0r >= n0r || ri0 !== e0r[g0r]) begin bad = bad + 1;
                if (bad < 8) $display("MISMATCH D0.ri %0d cyc %0d got %h", g0r, cyc, ri0[63:0]); end
            g0r = g0r + 1;
        end
    end

    integer seed = SEED, i, k, t0;
    function automatic [275:0] vbeat(input integer lane);
        reg [275:0] b; integer j;
        begin
            for (j = 0; j < 276; j = j + 32) b[j +: 32] = $random(seed);
            b[0] = 1'b1; b[3:1] = 3'd4; b[5:4] = lane[1:0];
            vbeat = b;
        end
    endfunction
    function automatic [1103:0] rbeat(input integer dummy);
        reg [1103:0] b; integer j;
        begin
            for (j = 0; j < 1104; j = j + 32) b[j +: 32] = $random(seed);
            b[0] = 1'b1; b[3:1] = 3'd2;              // untagged XB ring beat
            b[1045 +: 33] = 33'd0;                    // tag fields 0 (no TX window open)
            rbeat = b;
        end
    endfunction
    reg ok_main;
    initial begin
        repeat (20) @(posedge clk);
        rst_n = 1;
        repeat (300) @(posedge clk);                  // lanes trained (PMA live) before traffic
        for (i = 0; i < 4 * N; i = i + 1) begin
            @(negedge clk);
            ro0 = 0; ro1 = 0; tl0 = 0; tl1 = 0;
            k = i / 4;
            if (i % 4 == 0) begin
                ro0 = rbeat(0); e1r[n1r] = ro0; n1r = n1r + 1;
                ro1 = rbeat(0); e0r[n0r] = ro1; n0r = n0r + 1;
            end
            if (i % 4 == 1) begin
                tl0 = vbeat(2); e1a[n1a] = tl0; n1a = n1a + 1;
                tl1 = vbeat(3); e0b[n0b] = tl1; n0b = n0b + 1;
            end
        end
        @(negedge clk); ro0 = 0; ro1 = 0; tl0 = 0; tl1 = 0;
        t0 = cyc;
        while ((g1a < n1a || g0b < n0b || g1r < n1r || g0r < n0r) && cyc < t0 + WAIT) @(posedge clk);
        repeat (50) @(posedge clk);
        ok_main = (bad == 0 && stray == 0 && g1a == n1a && g0b == n0b && g1r == n1r && g0r == n0r && !f0 && !f1);
        $display("main: D1.ca %0d/%0d D0.cb %0d/%0d D1.ri %0d/%0d D0.ri %0d/%0d bad %0d stray %0d fault %b%b", g1a, n1a, g0b, n0b,
            g1r, n1r, g0r, n0r, bad, stray, f0, f1);
        // F1: tree beat and ring beat reaching the D0 frame stage in the same cycle (tl one cycle before ro: static-slot
        // violation) -> D0 fault
        @(negedge clk); tl0 = vbeat(2);
        @(negedge clk); tl0 = 0; ro0 = rbeat(0); e1r[n1r] = ro0; n1r = n1r + 1;
        @(negedge clk); ro0 = 0;
        // F2: a tree beat with lane 0 at D1 -> D1 fault
        repeat (8) @(negedge clk); tl1 = vbeat(0);
        @(negedge clk); tl1 = 0;
        repeat (400) @(posedge clk);
        // fault phase: the F1 ring beat still reaches D1 bit-exact (ring wins the slot); the F2 lane-0 beat may surface
        if (ok_main && f0 && f1 && bad == 0 && g1r == n1r)
            $display("PASS lep_idx seed %0d: %0d tree beats each way bit-exact (D0 lane2 -> D1.ca, D1 lane3 -> D0.cb), %0d+%0d ring beats intact, F1/F2 faults raised",
                SEED, n1a, n1r - 1, n0r);
        else
            $display("FAIL lep_idx seed %0d: main ok %b, F1 fault %b, F2 fault %b, bad %0d, D1.ri %0d/%0d", SEED, ok_main, f0, f1,
                bad, g1r, n1r);
        $finish;
    end
    initial begin #200000; $display("FAIL lep_idx timeout"); $finish; end
endmodule
