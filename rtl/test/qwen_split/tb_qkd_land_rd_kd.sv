`timescale 1ns/1ps
// qwen-split/kvsys v1.2 (die lead r4, 2026-10-14): tb_qkd_land_rd with the landing strip's kn / lt delivery depths:
// KD = registered stages on kn (the KV write words), KL = on lt (layer start / T / index) between the bench and the group.
// EPOCH=1 uses rq[16] (layer parity), CHECKED in the group against the compiled layer context (static schedule, no hold):
// LEAD = the compiler's issue offset of a layer's first request after its lt (cycles at the bench = die issue points);
// LEAD < 0 selects the compiled value KL: the layer's first request reaches the group's rq pin no earlier than the edge
// its lt reaches the lt pin (measured boundary: LEAD KL PASS exact, LEAD KL - 1 trips the epoch check). EXPECT_FAULT=1 is the schedule-error case (LEAD below the compiled value): it PASSES only if the
// group's epoch check fires before any wrong response; GM=4 removes the check and must FAIL there.
// EPOCH=0 preserves the historical interface/behaviour; KL>=7 then reproduces the fault.
// el1013-qwen-kvstrips 2026-10-13: exact bench of the KV landing read path of one row engine:
// 4 x qkd_land_pc (the group's pseudo-channels, CDC landing port) + qkd_land_grp (row matcher + ot_qkvd_kv_merge E 1).
//   * CDC side (per PC): the layer region streamed in index order j = 0..1,023 as {l_v, l_sec, l_row, l_data} pushes
//     under the CDC's landing credit (LCRED 6 outstanding, l_pop returns), each PC at its own random pace; the stream
//     of a layer may start BEFORE that layer's lt (the rows must wait, not be dropped);
//   * engine side: row requests {v, g, t} in stream order under the engine's credit (DQ 32 outstanding), random gaps,
//     only positions t < T, some V rows never requested; every response is compared in order against the bench's
//     source {q3, q2, q1, q0}(layer, j) -- or, for t = T - 1 of the token whose T - 1 belongs to this group, against the
//     posted K / V row (kn), which is posted late on purpose (the fence must hold the request);
//   * layers 34, 35, 0, 1 (the wrap) over two tokens (T 8,190 then 3,000: 3,000 leaves a tail beyond T to drop);
//   * end: every streamed word was consumed (credits home), no fault.
// PASS line "PASS qkd_land_rd ..."; mutants (GM = qkd_land_grp MUT, PM = qkd_land_pc MUT) must FAIL.
module tb_qkd_land_rd_kd #(parameter integer KD = 12, KL = 12, GM = 0, PM = 0, G = 5, S = 3, EPOCH = 1, DQ = 128,
                          LEAD = -1, EXPECT_FAULT = 0);
    localparam integer LD = (LEAD < 0) ? KL : LEAD;

    reg ck = 0; always #0.416667 ck = ~ck;
    reg rst_n = 0;
    reg  [281:0] li [0:3];
    wire [3:0]   lp;
    wire [272:0] gw [0:3];
    wire [3:0]   gc;
    reg  [15+EPOCH:0] rq = 0;
    wire [1024:0] rs;
    reg  [20:0]  lt = 0;
    reg  [1046:0] kn = 0;
    wire [20:0] lt_kd; wire [1046:0] kn_kd;
    ot_hdc_delay #(.W(1047), .D(KD), .RESET(1)) u_kd (.clk(ck), .rst_n(rst_n), .d(kn), .q(kn_kd));
    ot_hdc_delay #(.W(21), .D(KL), .RESET(1)) u_kl (.clk(ck), .rst_n(rst_n), .d(lt), .q(lt_kd));
    wire [4:0]   pfo;
    wire         fo;
    assign pfo[0] = 1'b0;
    for (genvar q = 0; q < 4; q++) begin : pc
        qkd_land_pc #(.MUT(q == 2 ? PM : 0)) u (.ck(ck), .rst_n(rst_n), .lpc(5'(8 * q + G)), .li(li[q]), .lp(lp[q]), .cf(1'b0),
            .gw(gw[q]), .gc(gc[q]), .es(), .er(261'd0), .dni(298'd0), .dno(), .upi(262'd0), .upo(), .cri(32'd0), .cro(),
            .fi(pfo[q]), .fo(pfo[q+1]));
    end
    generate if (EPOCH != 0) begin : g_native
    qkd_land_grp_epoch #(.MUT(GM)) grp (.ck(ck), .rst_n(rst_n), .g(3'(G)), .s(2'(S)), .gw0(gw[0]), .gw1(gw[1]), .gw2(gw[2]),
        .gw3(gw[3]), .gc0(gc[0]), .gc1(gc[1]), .gc2(gc[2]), .gc3(gc[3]), .rq(rq), .rs(rs), .lt(lt_kd), .kn(kn_kd), .fi(pfo[4]), .fo(fo));
    end else begin : g_legacy
    qkd_land_grp #(.MUT(GM), .DQ(DQ)) grp (.ck(ck), .rst_n(rst_n), .g(3'(G)), .s(2'(S)), .gw0(gw[0]), .gw1(gw[1]), .gw2(gw[2]),
        .gw3(gw[3]), .gc0(gc[0]), .gc1(gc[1]), .gc2(gc[2]), .gc3(gc[3]), .rq(rq), .rs(rs), .lt(lt_kd), .kn(kn_kd), .fi(pfo[4]), .fo(fo));
    end endgenerate


    function automatic [255:0] src(input integer layer, input integer j, input integer q);
        integer k;
        begin for (k = 0; k < 8; k++) src[32*k +: 32] = (32'h9e3779b9 * (layer * 4096 + j * 4 + q + 1)) ^ (32'h85ebca6b * (k + 1)) ^ (j << k); end
    endfunction
    function automatic [1023:0] kept(input integer layer, input integer vg);
        integer k;
        begin for (k = 0; k < 32; k++) kept[32*k +: 32] = (32'hc2b2ae35 * (layer * 8 + vg + 3)) ^ (32'h27d4eb2f * (k + 7)); end
    endfunction
    function automatic integer t_of(input integer j);
        t_of = (((j >> 3) & 15) << 9) | (S << 7) | (((j >> 7) & 1) << 6) | ((j & 7) << 3) | G;
    endfunction
    longint cycles = 0, start_ok = 0;
    always @(posedge ck) if (rst_n) cycles <= cycles + 1;
    longint n_err = 0, n_rsp = 0, n_kept = 0, n_req = 0, n_skip = 0, n_word [0:3], n_pop [0:3];
    task automatic bad(input string what);
        if (n_err < 10) $display("MISMATCH %s", what);
        n_err++;
    endtask
    // ---- CDC side: per PC a stream of (layer, j) words ----
    int sq_l [0:3][$], sq_j [0:3][$];
    int outst [0:3];
    reg [31:0] rnd = 32'h13572468;
    always @(posedge ck) begin
        for (int q = 0; q < 4; q++) begin
            rnd = {rnd[30:0], rnd[31] ^ rnd[21] ^ rnd[1] ^ rnd[0]};
            if (lp[q]) begin outst[q]--; n_pop[q]++; end
            li[q][0] <= 1'b0;
            if (rst_n && sq_l[q].size() != 0 && outst[q] < 6 && rnd[q*3 +: 3] != 0) begin
                automatic int l = sq_l[q].pop_front(), j = sq_j[q].pop_front();
                li[q] <= {src(l, j, q), 8'(64 + l), 6'(l), 3'(j >> 7), 1'b0, 7'(j), 1'b1};
                outst[q]++; n_word[q]++;
            end
        end
    end
    // ---- engine side: requests in stream order, responses compared in order ----
    reg [1023:0] exp_q [$];
    int rq_l [$], rq_j [$];
    int eout = 0;
    always @(posedge ck) begin
        rq <= 16'd0;
        if (rs[0]) begin
            eout--; n_rsp++;
            if (exp_q.size() == 0) bad("response with no request outstanding");
            else begin
                automatic reg [1023:0] e = exp_q.pop_front();
                if (rs[1024:1] !== e) bad($sformatf("response %0d data", n_rsp));
            end
        end
        if (rst_n && rq_l.size() != 0 && eout < DQ && rnd[14:12] != 0 && cycles >= start_ok) begin
            automatic int l = rq_l.pop_front(), j = rq_j.pop_front();
            automatic int t = t_of(j);
            rq <= {1'(l & 1), 13'(t), 1'((j >> 8) & 1), 1'((j >> 9) & 1), 1'b1};
            eout++; n_req++;
        end
    end
    task automatic stream(input integer l);
        for (int q = 0; q < 4; q++) for (int j = 0; j < 1024; j++) begin sq_l[q].push_back(l); sq_j[q].push_back(j); end
    endtask
    task automatic requests(input integer l, input integer T, input bit merge);
        for (int j = 0; j < 1024; j++) begin
            automatic int t = t_of(j), v = (j >> 9) & 1, gg = (j >> 8) & 1;
            if (t >= T) continue;
            if (v == 1 && ((j * 7 + l) % 5) == 0 && t != T - 1) begin n_skip++; continue; end
            rq_l.push_back(l); rq_j.push_back(j);
            if (merge && t == T - 1) begin exp_q.push_back(kept(l, v * 2 + gg)); n_kept++; end
            else exp_q.push_back({src(l, j, 3), src(l, j, 2), src(l, j, 1), src(l, j, 0)});
        end
    endtask
    task automatic lay(input integer l, input integer T);
        @(negedge ck); lt = {6'(l), 14'(T), 1'b1}; start_ok = cycles + LD; @(negedge ck); lt[0] = 1'b0;
    endtask
    task automatic post(input integer l, input integer T);
        for (int vg = 0; vg < 4; vg++) begin
            @(negedge ck); kn = {kept(l, vg), 6'(l), 14'(T - 1), 2'(vg), 1'b1}; @(negedge ck); kn[0] = 1'b0;
            repeat (3) @(negedge ck);
        end
    endtask
    integer L [0:3] = '{34, 35, 0, 1};
    integer TT [0:3] = '{8190, 8190, 3000, 3000};
    initial begin
        for (int q = 0; q < 4; q++) begin li[q] = 0; outst[q] = 0; n_word[q] = 0; n_pop[q] = 0; end
        repeat (6) @(negedge ck); rst_n = 1; repeat (6) @(negedge ck);
        for (int i = 0; i < 4; i++) begin
            automatic bit merge = (((TT[i] - 1) & 7) == G) && ((((TT[i] - 1) >> 7) & 3) == S);
            if (i % 2 == 1) begin stream(L[i]); repeat (300) @(negedge ck); end     // the stream lands before lt
            lay(L[i], TT[i]);
            requests(L[i], TT[i], merge);
            if (i % 2 == 0) begin repeat (40) @(negedge ck); stream(L[i]); end
            if (merge) begin repeat (i == 0 ? 3000 : 20) @(negedge ck); post(L[i], TT[i]); end   // late: the fence holds
            wait (exp_q.size() == 0 && rq_l.size() == 0);
            repeat (30) @(negedge ck);
        end
        lay(2, 3000);                                   // the next layer starts: the unrequested tail is dropped
        wait (n_pop[0] == 4096 && n_pop[1] == 4096 && n_pop[2] == 4096 && n_pop[3] == 4096);
        repeat (20) @(negedge ck);
        if (fo !== 1'b0) bad("fault chain set");
        if (n_rsp != n_req || n_kept != 8 || n_skip < 100) bad("coverage floor");
        $display("LAND_COST cycles %0d epoch %0d KD %0d KL %0d LEAD %0d", cycles, EPOCH, KD, KL, LD);
        if (EXPECT_FAULT != 0) bad("schedule error not detected by the epoch check");
        if (n_err == 0)
            $display("PASS qkd_land_rd g=%0d s=%0d: %0d row responses exact in request order (%0d replaced by the posted row behind the fence), %0d V rows not requested and %0d words in all consumed, 4 layers across the wrap, tail beyond T dropped",
                     G, S, n_rsp, n_kept, n_skip, n_pop[0] + n_pop[1] + n_pop[2] + n_pop[3]);
        else $display("FAIL qkd_land_rd gm=%0d pm=%0d: %0d mismatches", GM, PM, n_err);
        $finish;
    end
    generate if (EPOCH != 0) begin : g_sched_check
        always @(posedge ck) if (EXPECT_FAULT != 0 && g_native.grp.u.epoch_fault) begin
            if (n_err == 0) $display("PASS qkd_land_rd schedule fault detected: epoch check at cycle %0d (LEAD %0d < compiled %0d), %0d responses before it all exact",
                                     cycles, LD, KL, n_rsp);
            else $display("FAIL qkd_land_rd gm=%0d pm=%0d: %0d wrong responses before the epoch check", GM, PM, n_err);
            $finish;
        end
    end endgenerate
    initial begin
        #400000;
        $display("FAIL qkd_land_rd gm=%0d pm=%0d: watchdog (responses %0d of %0d requests, pops %0d %0d %0d %0d, fault %0d, mismatches %0d)",
                 GM, PM, n_rsp, n_req, n_pop[0], n_pop[1], n_pop[2], n_pop[3], fo, n_err);
        $finish;
    end
endmodule
