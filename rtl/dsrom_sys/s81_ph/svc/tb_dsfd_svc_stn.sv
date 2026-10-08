`timescale 1ns/1ps
// tb_dsfd_svc_stn (CLAUDE S81-PH svc): transaction-level gate of a chain of NS link stations: random q words (valid
// duty 60%) hub -> quadrant; od / a0 frames quadrant -> hub with random source valid and random sink ready.
// Scoreboards: every word exactly once, in order, bit-exact, on every lane; prints TB_SVC_STN PASS / FAIL.
module tb_dsfd_svc_stn;
    parameter integer NS = 15, N = 3000;
    reg ck = 0, rst = 0;
    always #0.4165 ck = ~ck;
    wire [514:0] q [0:NS];
    wire [NS:0] odv, odr, a0v, a0r;
    wire [511:0] odd [0:NS], a0d [0:NS];
    reg [514:0] q_src = 0;
    assign q[NS] = q_src;                       // the hub drives the E end (index NS), the quadrant sits at index 0
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_s
        dsfd_svc_stn u (.ck(ck), .rst(rst), .q_e(q[s+1]), .q_w(q[s]),
            .od_wv(odv[s]), .od_wd(odd[s]), .od_wr(odr[s]), .od_ev(odv[s+1]), .od_ed(odd[s+1]), .od_er(odr[s+1]),
            .a0_wv(a0v[s]), .a0_wd(a0d[s]), .a0_wr(a0r[s]), .a0_ev(a0v[s+1]), .a0_ed(a0d[s+1]), .a0_er(a0r[s+1]));
    end endgenerate
    reg sv_od = 0, sv_a0 = 0, rr_od = 0, rr_a0 = 0;
    reg [511:0] sd_od = 0, sd_a0 = 0;
    assign odv[0] = sv_od; assign odd[0] = sd_od; assign a0v[0] = sv_a0; assign a0d[0] = sd_a0;
    assign odr[NS] = rr_od; assign a0r[NS] = rr_a0;
    reg [514:0] eq [0:N-1]; reg [511:0] eo [0:N-1], ea [0:N-1];
    integer nq = 0, no = 0, na = 0, cq = 0, co = 0, ca = 0, err = 0, i, seed, cyc = 0;
    function [511:0] rw(input integer d); integer k; begin for (k = 0; k < 512; k = k + 32) rw[k +: 32] = $urandom; end endfunction
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        void'($urandom(seed));
        repeat (4) @(posedge ck); rst = 1; repeat (4) @(posedge ck);
        while ((cq < N || co < N || ca < N) && cyc < 40 * N) begin
            @(negedge ck); cyc = cyc + 1;
            // sources: hold the word while not accepted (valid/ready), q valid-only
            if (sv_od && odr[0]) begin sv_od = 0; end
            if (sv_a0 && a0r[0]) begin sv_a0 = 0; end
            q_src = 0;
            if (nq < N && ($urandom % 100) < 60) begin q_src = {rw(0), 3'b0}; q_src[0] = 1; eq[nq] = q_src; nq = nq + 1; end
            if (!sv_od && no < N && ($urandom % 100) < 70) begin sd_od = rw(0); sv_od = 1; eo[no] = sd_od; no = no + 1; end
            if (!sv_a0 && na < N && ($urandom % 100) < 50) begin sd_a0 = rw(0); sv_a0 = 1; ea[na] = sd_a0; na = na + 1; end
            rr_od = ($urandom % 100) < 60;
            rr_a0 = ($urandom % 100) < 40;
        end
        $display("q %0d/%0d od %0d/%0d a0 %0d/%0d errors %0d cycles %0d", cq, N, co, N, ca, N, err, cyc);
        $display("TB_SVC_STN %s", (err == 0 && cq == N && co == N && ca == N) ? "PASS" : "FAIL");
        $finish;
    end
    always @(posedge ck) if (rst) begin
        if (q[0][0]) begin if (cq >= N || q[0] !== eq[cq]) err = err + 1; cq = cq + 1; end
        if (odv[NS] && odr[NS]) begin if (co >= N || odd[NS] !== eo[co]) err = err + 1; co = co + 1; end
        if (a0v[NS] && a0r[NS]) begin if (ca >= N || a0d[NS] !== ea[ca]) err = err + 1; ca = ca + 1; end
    end
endmodule
