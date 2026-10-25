`timescale 1ns/1ps
// S81/IDXNET (2026-10-25, S81 DECISIONS 1 + 2): bench of the new lep index-network ends, production opt-ins RX_SRAM 1 /
// IN_PIPE 1 / NATIVE32 1, every link through the hardened lane tiles dsfd_coll_lane_w (LCR 1) + the behavioural PMA
// ot_pdie_ucie (lane 1 of a pair skewed), as tb_s81sl_lep_idx (H4).  Seven dies:
//   T1  D0 <-> D1 ot_s81sl_lep_mu_h_tp (s_7N), pair A <-> pair A (topk_final step 1, the d+2 swap): tp_i beats (lane 2)
//       -> the peer's tp_o, both ways, bit-exact, in order; ring beats both ways intact.
//   T2  D2 ot_s81sl_lep_mu_a_tpt (s_7S) -> D3 ot_s81sl_lep_mu_a_tpr (s_0S), pair A <-> pair A (step 2): D2 tp_i -> D3 tp_o.
//   Q   D4 -> D5 -> D6 -> D4 ot_s81sl_lep_mu_ab_idxq (s_0N), pair A of Dk = stage NEXT -> pair B of Dk+1 (as the rack):
//       Q1 D4 (root) qc: frames {type-10 header with relay count RL = 1, len words} sent 2-beat at 1 word / 4 cycles
//          -> D5 ql = every word exact (RL 1 as sent), D5 relays it -> D6 ql = every word with RL 0 in the header, D6
//          does not relay -> nothing on D4 ql; a second frame with RL 0 reaches D5 ql only.
//       Q2 D4 tm beats (the s_0S TP RX lane) -> D4 ca exactly 3 edges later; D6 tl tree beats (lane 2, pair A -> D4
//          pair B) -> D4 ca too (H4 path) in other cycles; D4 cb / every other ca / cb idle.
//   Main phase: no fault anywhere.  Fault phase: F1 D0 tp beat with lane 3 -> D0 (TX) + D1 (RX lane) fault; F2 D2 tp beat
//   with lane 0 -> D2 + D3 fault; F3 D4 root frame whose header is not type 10 (RL 0) -> D5 fault, D6 clean (Q framer); F4 D4 qc beat 1 without beat 0
//   -> D4 fault; F5 tm beat in the same ca cycle as a tree beat -> D4 fault is NOT tested (link-timing dependent).
// Mutants (must FAIL): OT_S81SL_LEP_MUT_IDXDMX (TP RX never reaches tp_o), OT_S81SL_LEP_MUT_QBEAT (qc halves swapped),
//   OT_S81SL_LEP_MUT_QRL (relay count not decremented: D6 relays on to D4), OT_S81SL_LEP_MUT_TPMRG (tm not merged).
// Gate runs: seeds 1 / 5, RSLOT 3 and TSLOT 3 (ring frame in the cycle right after a Q / tree frame on the same pair).
// Verdict "PASS lep_idxnet ..." / "FAIL lep_idxnet ...".
module tb_s81sl_lep_idxnet #(parameter integer N = 96, parameter integer SEED = 1, parameter integer WAIT = 6000,
    parameter integer RSLOT = 0,    // Q1 slot of the root's ring beat: 0 (ring frame c, Q frame c + 2) or 3 (ring frame c + 3, the cycle after)
    parameter integer TSLOT = 0);   // 3: a D6 ring beat in slot 3 of Q2 (its ring frame the cycle after each tree frame, same pair)
    localparam integer ND = 7;
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg [1103:0] ro [0:ND-1]; wire [1103:0] ri [0:ND-1];
    reg [275:0] tpi [0:3]; wire [275:0] tpo [0:3];
    reg [275:0] tl [4:6]; reg [275:0] tm [4:6]; reg [257:0] qc [4:6];
    wire [275:0] ca [4:6]; wire [275:0] cb [4:6]; wire [512:0] ql [4:6];
    wire [ND-1:0] f;
    wire [4*ND-1:0] lv, lr, iv, ir, rxv; wire [4*553*ND-1:0] ld, id; wire [12*ND-1:0] fl;
    wire [4*512*ND-1:0] tx, rx; wire [8*ND-1:0] st;
    integer q0;
    initial for (q0 = 0; q0 < ND; q0 = q0 + 1) ro[q0] = 0;
    initial begin for (q0 = 0; q0 < 4; q0 = q0 + 1) tpi[q0] = 0; for (q0 = 4; q0 < 7; q0 = q0 + 1) begin tl[q0] = 0; tm[q0] = 0; qc[q0] = 0; end end
`define LN(X, L) .lo``L``_v(lv[4*X+L]), .lo``L``_r(lr[4*X+L]), .lo``L``_d(ld[553*(4*X+L) +: 553]), \
                 .li``L``_v(iv[4*X+L]), .li``L``_r(ir[4*X+L]), .li``L``_d(id[553*(4*X+L) +: 553])
`define COM(X) .clk(clk), .rst_n(rst_n), .ro(ro[X]), .ri(ri[X]), `LN(X, 0), `LN(X, 1), .rxv(rxv[4*X +: 2]), .sl_f(1'b0), \
               .l0_f(fl[12*X +: 3]), .l1_f(fl[12*X+3 +: 3]), .mu_c(34'd0), .mu_rt(), .ml_wv(), .ml_wd(), .ml_rv(1'b0), \
               .ml_rd(1104'd0), .ml_f(1'b0), .fault(f[X])
`define PRM #(.SRAM(1), .RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1))
    ot_s81sl_lep_mu_h_tp `PRM u_d0 (`COM(0), .l0_st(2'b00), .l1_st(2'b00), .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .tp_i(tpi[0]), .tp_o(tpo[0]));
    ot_s81sl_lep_mu_h_tp `PRM u_d1 (`COM(1), .l0_st(2'b00), .l1_st(2'b00), .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .tp_i(tpi[1]), .tp_o(tpo[1]));
    ot_s81sl_lep_mu_a_tpt `PRM u_d2 (`COM(2), .tp_i(tpi[2]));
    ot_s81sl_lep_mu_a_tpr `PRM u_d3 (`COM(3), .tp_o(tpo[3]));
    assign tpo[1 + 1] = 276'd0;
    genvar g;
    generate for (g = 4; g < 7; g = g + 1) begin : g_q
        ot_s81sl_lep_mu_ab_idxq `PRM u (`COM(g), `LN(g, 2), `LN(g, 3), .rxvb(rxv[4*g+2 +: 2]), .l2_f(fl[12*g+6 +: 3]),
            .l3_f(fl[12*g+9 +: 3]), .tl(tl[g]), .ca(ca[g]), .cb(cb[g]), .tm(tm[g]), .qc(qc[g]), .ql(ql[g]));
    end endgenerate
    // lane tiles: every die x 4 lanes (lanes 2/3 of D0..D3 idle: no link)
    generate for (g = 0; g < 4 * ND; g = g + 1) begin : g_lt
        if (g % 4 < 2 || g >= 16) begin : g_t
            dsfd_coll_lane_w #(.LCR(1)) u (.ck(clk), .rs(rst_n), .chb(1'b0), .rx({st[2*g], st[2*g+1], rx[512*g +: 512], rxv[g]}),
                .tx(tx[512*g +: 512]), .tf(), .lo_v(lv[g]), .lo_r(lr[g]), .lo_d(ld[553*g +: 553]),
                .li_v(iv[g]), .li_r(ir[g]), .li_d(id[553*g +: 553]), .flt(fl[3*g +: 3]));
        end else begin : g_n
            assign lr[g] = 1'b0; assign iv[g] = 1'b0; assign id[553*g +: 553] = '0; assign fl[3*g +: 3] = 3'd0; assign rxv[g] = 1'b0;
        end
    end endgenerate
    // links: die-lane a <-> die-lane b (global lane index 4*die + lane)
    localparam integer NLK = 10;
    localparam [NLK*16-1:0] LKS = {
        8'(4*4+0), 8'(4*5+2),  8'(4*4+1), 8'(4*5+3),     // D4 A -> D5 B
        8'(4*5+0), 8'(4*6+2),  8'(4*5+1), 8'(4*6+3),     // D5 A -> D6 B
        8'(4*6+0), 8'(4*4+2),  8'(4*6+1), 8'(4*4+3),     // D6 A -> D4 B
        8'(4*0+0), 8'(4*1+0),  8'(4*0+1), 8'(4*1+1),     // D0 A <-> D1 A
        8'(4*2+0), 8'(4*3+0),  8'(4*2+1), 8'(4*3+1)};    // D2 A <-> D3 A
    generate for (g = 0; g < NLK; g = g + 1) begin : g_lk
        localparam integer a = LKS[16*g+8 +: 8], b = LKS[16*g +: 8];
        wire [512:0] pa, pb; wire ta, tb;
        ot_pdie_ucie #(.PMA_LAT(a % 2 == 0 ? 2 : 9)) u_a (.clk(clk), .rst(rst_n), .tx(tx[512*a +: 512]), .rx(rx[512*a +: 512]),
            .st(st[2*a +: 2]), .pma_tx(pa), .pma_tck(ta), .pma_rx(pb), .pma_rck(tb));
        ot_pdie_ucie #(.PMA_LAT(a % 2 == 0 ? 2 : 9)) u_b (.clk(clk), .rst(rst_n), .tx(tx[512*b +: 512]), .rx(rx[512*b +: 512]),
            .st(st[2*b +: 2]), .pma_tx(pb), .pma_tck(tb), .pma_rx(pa), .pma_rck(ta));
    end endgenerate
    generate for (g = 0; g < 4 * ND; g = g + 1) begin : g_ust
        if (!(g % 4 < 2 || g >= 16)) begin : g_z assign st[2*g +: 2] = 2'b00; assign tx[512*g +: 512] = '0; end
    end endgenerate

    // ------------------------------------------------------------------ scoreboards (queues of expected beats)
    reg [1103:0] er [0:ND-1][$];                 // ring beats expected at ri[d]
    reg [275:0] etp [0:3][$];                    // tp_o
    reg [275:0] eca [$];                         // D4 ca
    reg [512:0] eql [4:6][$];                    // ql
    integer bad = 0, stray = 0, i, d;
    integer ntp [0:3]; integer nql [4:6]; integer nca = 0;
    reg chk_lat = 1; reg [275:0] tm_pipe [0:2]; integer tmlat_bad = 0;
    initial begin for (i = 0; i < 4; i = i + 1) ntp[i] = 0; for (i = 4; i < 7; i = i + 1) nql[i] = 0; end
    always @(posedge clk) if (rst_n) begin
        for (d = 0; d < ND; d = d + 1) if (ri[d][0]) begin
            if (er[d].size() == 0 || ri[d] !== er[d][0]) begin bad++; if (bad < 10) $display("MISMATCH D%0d.ri cyc %0d got %h exp %h q %0d", d, cyc, ri[d][63:0], er[d].size() ? er[d][0][63:0] : 64'd0, er[d].size()); end
            if (er[d].size()) void'(er[d].pop_front());
        end
        for (d = 0; d < 4; d = d + 1) if (d != 2 && tpo[d][0]) begin
            if (etp[d].size() == 0 || tpo[d] !== etp[d][0]) begin bad++;
                if (bad < 10) $display("MISMATCH D%0d.tp_o cyc %0d got %h", d, cyc, tpo[d][63:0]); end
            if (etp[d].size()) void'(etp[d].pop_front()); ntp[d]++;
        end
        if (ca[4][0]) begin
            if (eca.size() == 0 || ca[4] !== eca[0]) begin bad++; if (bad < 10) $display("MISMATCH D4.ca cyc %0d got %h", cyc, ca[4][63:0]); end
            if (eca.size()) void'(eca.pop_front()); nca++;
        end
        for (d = 4; d < 7; d = d + 1) if (ql[d][0]) begin
            if (eql[d].size() == 0 || ql[d] !== eql[d][0]) begin bad++;
                if (bad < 10) $display("MISMATCH D%0d.ql cyc %0d got %h", d, cyc, ql[d][16:0]); end
            if (eql[d].size()) void'(eql[d].pop_front()); nql[d]++;
        end
        if (cb[4] !== 0 || ca[5] !== 0 || cb[5] !== 0 || ca[6] !== 0 || cb[6] !== 0) begin stray++;
            if (stray < 4) $display("STRAY ca/cb beat cyc %0d", cyc); end
        // tm -> ca latency: a tm beat driven before edge e appears on ca after edge e + 2 (3 edges)
        if (tm_pipe[2][0] && ca[4] !== tm_pipe[2]) begin tmlat_bad++; if (tmlat_bad < 4) $display("TM LATENCY cyc %0d", cyc); end
    end
    always @(posedge clk) begin tm_pipe[2] <= tm_pipe[1]; tm_pipe[1] <= tm_pipe[0]; tm_pipe[0] <= tm[4]; end
    integer seed = SEED, k, t0, w, nw, fr;
    function automatic [275:0] vbeat(input integer lane);
        reg [275:0] b; integer j;
        begin for (j = 0; j < 276; j = j + 32) b[j +: 32] = $random(seed); b[0] = 1'b1; b[3:1] = 3'd4; b[5:4] = lane[1:0]; vbeat = b; end
    endfunction
    function automatic [1103:0] rbeat(input integer dummy);
        reg [1103:0] b; integer j;
        begin for (j = 0; j < 1104; j = j + 32) b[j +: 32] = $random(seed); b[0] = 1'b1; b[3:1] = 3'd2; b[1045 +: 33] = 33'd0; rbeat = b; end
    endfunction
    function automatic [511:0] rword(input integer dummy);
        reg [511:0] b; integer j; begin for (j = 0; j < 512; j = j + 32) b[j +: 32] = $random(seed); rword = b; end
    endfunction
    function automatic [511:0] qhdr(input [3:0] ty, input [11:0] len, input [3:0] rl);
        reg [511:0] h; begin h = rword(0); h[511:508] = ty; h[491:480] = len; h[7:4] = rl; qhdr = h; end
    endfunction
    reg [511:0] fw [0:15]; reg ok_main;
    task automatic clr; begin for (k = 0; k < 4; k = k + 1) tpi[k] = 0; for (k = 4; k < 7; k = k + 1) begin tl[k] = 0; tm[k] = 0; qc[k] = 0; end
        for (k = 0; k < ND; k = k + 1) ro[k] = 0; end endtask
    // one root frame on D4 qc: header (type ty, len n-1, relay rl) + n-1 words, word every 4 cycles (beat 0 slot 0,
    // beat 1 slot 1) with a D4 ring beat in slot RSLOT (ring frame c + RSLOT, Q frame c + 2); expected ql per the relay count
    task automatic qframe(input integer n, input [3:0] ty, input [3:0] rl, input bit expect_q);
        integer j; reg [511:0] x5;
        begin
            fw[0] = qhdr(ty, 12'(n - 1), rl);
            for (j = 1; j < n; j = j + 1) fw[j] = rword(0);
            for (j = 0; j < n; j = j + 1) begin
                @(negedge clk); clr; qc[4] = {fw[j][255:0], 1'b0, 1'b1}; if (RSLOT == 0) begin ro[4] = rbeat(0); er[5].push_back(ro[4]); end
                @(negedge clk); clr; qc[4] = {fw[j][511:256], 1'b1, 1'b1};
                @(negedge clk); clr;
                @(negedge clk); clr; if (RSLOT == 3) begin ro[4] = rbeat(0); er[5].push_back(ro[4]); end
                if (expect_q) begin
                    eql[5].push_back({fw[j], 1'b1});
                    x5 = fw[j]; if (j == 0) x5[7:4] = rl - 4'd1;
                    if (rl != 0) eql[6].push_back({x5, 1'b1});
                end
            end
            @(negedge clk); clr;                       // RSLOT 3 drives ro on the last negedge: never hold it into the idle
        end
    endtask
    initial begin
        repeat (20) @(posedge clk); rst_n = 1;
        repeat (300) @(posedge clk);
        // ---- T1 / T2: 4-cycle calendar, slot 0 ring beats (D0 <-> D1, D2 -> D3, D3 -> D2), slot 1 tp beats lane 2
        for (i = 0; i < 4 * N; i = i + 1) begin
            @(negedge clk); clr;
            if (i % 4 == 0) begin
                ro[0] = rbeat(0); er[1].push_back(ro[0]); ro[1] = rbeat(0); er[0].push_back(ro[1]);
                ro[2] = rbeat(0); er[3].push_back(ro[2]); ro[3] = rbeat(0); er[2].push_back(ro[3]);
            end
            if (i % 4 == 1) begin
                tpi[0] = vbeat(2); etp[1].push_back(tpi[0]); tpi[1] = vbeat(2); etp[0].push_back(tpi[1]);
                tpi[2] = vbeat(2); etp[3].push_back(tpi[2]);
            end
        end
        @(negedge clk); clr;
        // ---- Q1: three frames RL 1 (D5 + D6), one frame RL 0 (D5 only)
        for (fr = 0; fr < 3; fr = fr + 1) begin qframe(5 + 3 * fr, 4'd10, 4'd1, 1); repeat (6) @(negedge clk); end
        qframe(4, 4'd10, 4'd0, 1);
        repeat (40) @(negedge clk);
        // ---- Q2: tm beats into D4 ca, then D6 tree beats (lane 2 -> pair A -> D4 pair B -> ca), different cycles
        for (i = 0; i < 2 * N; i = i + 1) begin
            @(negedge clk); clr;
            if (i % 4 == 1 && i < N) begin tm[4] = vbeat(2); eca.push_back(tm[4]); end
        end
        @(negedge clk); clr; repeat (20) @(negedge clk);
        for (i = 0; i < 2 * N; i = i + 1) begin
            @(negedge clk); clr;
            if (i % 4 == 1) begin tl[6] = vbeat(2); eca.push_back(tl[6]); end
            if (TSLOT == 3 && i % 4 == 3) begin ro[6] = rbeat(0); er[4].push_back(ro[6]); end
        end
        @(negedge clk); clr;
        t0 = cyc; k = 0;
        while (cyc < t0 + WAIT && !(eca.size() == 0 && eql[4].size() == 0 && eql[5].size() == 0 && eql[6].size() == 0
               && etp[0].size() == 0 && etp[1].size() == 0 && etp[3].size() == 0 && er[0].size() == 0 && er[1].size() == 0
               && er[2].size() == 0 && er[3].size() == 0 && er[4].size() == 0 && er[5].size() == 0)) @(posedge clk);
        // (er[0..3], er[5] all drained is part of ok_main)
        repeat (60) @(posedge clk);
        ok_main = bad == 0 && stray == 0 && tmlat_bad == 0 && f == 0 && eca.size() == 0 && eql[5].size() == 0 &&
                  eql[6].size() == 0 && nql[4] == 0 && etp[0].size() == 0 && etp[1].size() == 0 && etp[3].size() == 0 &&
                  er[0].size() == 0 && er[1].size() == 0 && er[2].size() == 0 && er[3].size() == 0 && er[4].size() == 0 && er[5].size() == 0;
        $display("main: tp D1 %0d D0 %0d D3 %0d; ql D5 %0d D6 %0d D4 %0d; D4.ca %0d; bad %0d stray %0d tmlat %0d fault %b left ca %0d ql5 %0d ql6 %0d",
            ntp[1], ntp[0], ntp[3], nql[5], nql[6], nql[4], nca, bad, stray, tmlat_bad, f, eca.size(), eql[5].size(), eql[6].size());
        // ---- fault phase
        @(negedge clk); clr; tpi[0] = vbeat(3);                              // F1
        @(negedge clk); clr; tpi[2] = vbeat(0);                              // F2
        @(negedge clk); clr; repeat (8) @(negedge clk);
        qframe(3, 4'd9, 4'd0, 0);                                            // F3 (RL 0: no relay; D5 ql words not checked)
        @(negedge clk); clr; qc[4] = {256'd5, 1'b1, 1'b1};                   // F4
        @(negedge clk); clr;
        repeat (400) @(posedge clk);
        if (ok_main && f == 7'b0111111)
            $display("PASS lep_idxnet seed %0d: tp D0<->D1 %0d/%0d, D2->D3 %0d, Q root->D5 %0d words, relay->D6 %0d, D4 ql 0, D4.ca %0d (tm 3 edges + tree), F1-F4 faults raised",
                SEED, ntp[1], ntp[0], ntp[3], nql[5], nql[6], nca);
        else
            $display("FAIL lep_idxnet seed %0d: main ok %b, faults %b (want 0111111: D0..D5, not D6)", SEED, ok_main, f);
        $finish;
    end
    initial begin #400000; $display("FAIL lep_idxnet timeout"); $finish; end
endmodule
