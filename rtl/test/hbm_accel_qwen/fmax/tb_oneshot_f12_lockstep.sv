`timescale 1ns/1ps
// Lockstep exactness bench: the original package ot_rom_oneshot_allreduce (pinned dies) against
// ot_rom_oneshot_allreduce_f12 (successor dies) under the SAME stimulus: per die a schedule of collectives
// (random all-reduce lengths 1..256 and all-gathers), random fp32 lanes incl. zeros, subnormals and rare
// non-finite / huge values, the same per-cycle producer stall pattern.  Each side runs its own handshakes.
// Checked: every die's output stream (data, last, rank, err) identical word for word, and the final fault /
// fault_code identical.  SERIAL = 1: a die starts collective k+1 only after it received collective k's
// result (the TP sequencer's behaviour); the per-collective latency (die 0: first push -> last result) of
// both sides is summed, and the delta is printed.
module tb_oneshot_f12_lockstep;
    parameter integer N = 2, DEPTH = 16, LAT = 11, BPC = 3600, FIFO_IMPL = 1, ADD_IMPL = 1;
    parameter integer NCOLL = 200, SERIAL = 1, SEED = 1, STALL_PCT = 10, MAXNW = 256, SPECIAL = 1;
    localparam integer LANES = 16, TAGW = 32, FW = 512, RB = (N > 1) ? $clog2(N) : 1;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;

    integer cnw [0:NCOLL-1];
    reg     cmode [0:NCOLL-1];
    integer cbase [0:NCOLL];          // expected output words per die before collective k
    integer k, i;
    integer seed;

    function automatic [31:0] mix(input [31:0] x);
        reg [31:0] h;
        begin
            h = x ^ 32'h9e3779b9;
            h = h ^ (h >> 16); h = h * 32'h85ebca6b;
            h = h ^ (h >> 13); h = h * 32'hc2b2ae35;
            h = h ^ (h >> 16);
            mix = h;
        end
    endfunction
    function automatic [31:0] lane_val(input integer d, input integer kk, input integer j, input integer l);
        reg [31:0] h, h2;
        reg [7:0] e;
        begin
            h = mix(SEED * 7919 + d * 1000003 + kk * 4099 + j * 67 + l);
            h2 = mix(h + 32'h1234567);
            e = 8'd100 + (h2[7:0] % 8'd50);
            if (SPECIAL && h2[19:8] == 12'd4000) e = 8'hff;                 // non-finite (fail closed)
            else if (SPECIAL && h2[19:8] == 12'd4001) e = 8'hfe;            // huge: may overflow
            else if (h2[19:8] < 12'd40) e = 8'd0;                       // zero / subnormal
            if (h2[19:8] < 12'd20) lane_val = {h[31], 31'd0};           // signed zero
            else lane_val = {h[31], e, h[22:0]};
        end
    endfunction
    function automatic [FW-1:0] word(input integer d, input integer kk, input integer j);
        integer l;
        begin
            for (l = 0; l < LANES; l = l + 1) word[32*l +: 32] = lane_val(d, kk, j, l);
        end
    endfunction

    // -- the two packages --------------------------------------------------------------------
    reg  [N-1:0]      iv [0:1];
    wire [N-1:0]      ir [0:1];
    reg  [N*FW-1:0]   idat [0:1];
    reg  [N-1:0]      ilast [0:1], imode [0:1];
    reg  [N*TAGW-1:0] itag [0:1];
    wire [N-1:0]      ov [0:1], ol [0:1], oe [0:1], flt [0:1];
    wire [N*FW-1:0]   od [0:1];
    wire [N*RB-1:0]   ork [0:1];
    wire [N*3-1:0]    fc [0:1];
    wire [31:0]       ls0, ls1;
    ot_rom_oneshot_allreduce #(.N(N), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH), .LAT(LAT), .BPC_NUM(BPC)) u_ref (
        .clk(clk), .rst_n(rst_n), .in_valid(iv[0]), .in_ready(ir[0]), .in_data(idat[0]), .in_last(ilast[0]),
        .in_mode(imode[0]), .in_tag(itag[0]), .out_valid(ov[0]), .out_data(od[0]), .out_last(ol[0]),
        .out_rank(ork[0]), .out_err(oe[0]), .fault(flt[0]), .fault_code(fc[0]), .link_stalls(ls0));
    ot_rom_oneshot_allreduce_f12 #(.N(N), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH), .LAT(LAT), .BPC_NUM(BPC),
        .FIFO_IMPL(FIFO_IMPL), .ADD_IMPL(ADD_IMPL)) u_new (
        .clk(clk), .rst_n(rst_n), .in_valid(iv[1]), .in_ready(ir[1]), .in_data(idat[1]), .in_last(ilast[1]),
        .in_mode(imode[1]), .in_tag(itag[1]), .out_valid(ov[1]), .out_data(od[1]), .out_last(ol[1]),
        .out_rank(ork[1]), .out_err(oe[1]), .fault(flt[1]), .fault_code(fc[1]), .link_stalls(ls1));

    // -- drivers --------------------------------------------------------------------------------
    integer ck [0:1][0:N-1];          // current collective
    integer cj [0:1][0:N-1];          // next word of it
    integer oc [0:1][0:N-1];          // outputs received
    integer t_first [0:1][0:NCOLL-1];
    integer t_last  [0:1][0:NCOLL-1];
    integer cyc = 0;
    reg [N-1:0] stall;
    integer s, d;
    // output comparison queues
    localparam integer QD = 8192;
    reg [FW+RB+1:0] q [0:1][0:N-1][0:QD-1];
    integer qw [0:1][0:N-1];
    integer qr [0:N-1];
    integer mism = 0, compared = 0;

    task automatic drive(input integer sd);
        integer dd, kk, jj;
        begin
            for (dd = 0; dd < N; dd = dd + 1) begin
                kk = ck[sd][dd]; jj = cj[sd][dd];
                iv[sd][dd] = 1'b0;
                idat[sd][dd*FW +: FW] = 0; ilast[sd][dd] = 0; imode[sd][dd] = 0; itag[sd][dd*TAGW +: TAGW] = 0;
                if (kk < NCOLL && !stall[dd] && (!SERIAL || oc[sd][dd] >= cbase[kk])) begin
                    iv[sd][dd] = 1'b1;
                    idat[sd][dd*FW +: FW] = word(dd, kk, jj);
                    ilast[sd][dd] = (jj == cnw[kk] - 1);
                    imode[sd][dd] = cmode[kk];
                    itag[sd][dd*TAGW +: TAGW] = kk;
                end
            end
        end
    endtask

    initial begin
        seed = SEED;
        cbase[0] = 0;
        for (k = 0; k < NCOLL; k = k + 1) begin
            i = mix(SEED * 31 + k);
            cmode[k] = (i[3:0] < 4'd3);
            if (cmode[k]) cnw[k] = 1;
            else if (i[7:4] < 4'd4) cnw[k] = MAXNW;
            else cnw[k] = 1 + (i[23:8] % MAXNW);
            cbase[k+1] = cbase[k] + (cmode[k] ? N : cnw[k]);
        end
        for (s = 0; s < 2; s = s + 1) begin
            iv[s] = 0; idat[s] = 0; ilast[s] = 0; imode[s] = 0; itag[s] = 0;
            for (d = 0; d < N; d = d + 1) begin ck[s][d] = 0; cj[s][d] = 0; oc[s][d] = 0; qw[s][d] = 0; end
        end
        for (d = 0; d < N; d = d + 1) qr[d] = 0;
        for (k = 0; k < NCOLL; k = k + 1) begin t_first[0][k] = -1; t_first[1][k] = -1; t_last[0][k] = -1; t_last[1][k] = -1; end
        stall = 0;
        i = 0;
        for (k = 0; k < 20000; k = k + 1) if (lane_val(k % N, k / 4096, k % 256, k % 16) == 32'h7f800000 ||
                                             lane_val(k % N, k / 4096, k % 256, k % 16) [30:23] == 8'hff) i = i + 1;
        $display("STIM non-finite lanes in a 20000-sample = %0d", i);
        repeat (4) @(posedge clk);
        rst_n = 1;
    end

    // stimulus is applied on the falling edge; handshakes / outputs sampled at the rising edge
    always @(negedge clk) if (rst_n) begin
        for (d = 0; d < N; d = d + 1) stall[d] = (($random(seed) & 32'h7fffffff) % 100) < STALL_PCT;
        drive(0); drive(1);
    end
    integer kk2, jj2, done_all;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        for (s = 0; s < 2; s = s + 1) for (d = 0; d < N; d = d + 1) begin
            if (iv[s][d] && ir[s][d]) begin
                kk2 = ck[s][d];
                if (d == 0 && cj[s][d] == 0) t_first[s][kk2] = cyc;
                if (cj[s][d] == cnw[kk2] - 1) begin ck[s][d] = kk2 + 1; cj[s][d] = 0; end
                else cj[s][d] = cj[s][d] + 1;
            end
            if (ov[s][d]) begin
                q[s][d][qw[s][d] % QD] = {oe[s][d], ol[s][d], ork[s][d*RB +: RB], od[s][d*FW +: FW]};
                qw[s][d] = qw[s][d] + 1;
                oc[s][d] = oc[s][d] + 1;
                if (d == 0) begin
                    for (k = 0; k < NCOLL; k = k + 1) if (cbase[k+1] == oc[s][d]) t_last[s][k] = cyc;
                end
            end
        end
        for (d = 0; d < N; d = d + 1) begin
            while (qr[d] < qw[0][d] && qr[d] < qw[1][d]) begin
                if (q[0][d][qr[d] % QD] !== q[1][d][qr[d] % QD]) begin
                    if (mism < 10) $display("MISMATCH die %0d word %0d: ref %h new %h", d, qr[d],
                                             q[0][d][qr[d] % QD], q[1][d][qr[d] % QD]);
                    mism = mism + 1;
                end
                compared = compared + 1;
                qr[d] = qr[d] + 1;
            end
            if (qw[0][d] - qr[d] > QD - 4 || qw[1][d] - qr[d] > QD - 4) begin $display("FAIL queue overflow"); $finish; end
        end
    end

    integer lat0, lat1, dlat_min, dlat_max, dl, nar, nga, dsum_ar, dsum_ga, dfirst;
    initial begin
        wait (rst_n);
        done_all = 0;
        while (!done_all) begin
            @(posedge clk);
            done_all = 1;
            for (d = 0; d < N; d = d + 1)
                if (oc[0][d] < cbase[NCOLL] || oc[1][d] < cbase[NCOLL]) done_all = 0;
            if (cyc > 50000000) begin $display("FAIL timeout"); $finish; end
        end
        repeat (20) @(posedge clk);
        lat0 = 0; lat1 = 0; dlat_min = 1 << 30; dlat_max = -(1 << 30); nar = 0; nga = 0; dsum_ar = 0; dsum_ga = 0;
        for (k = 0; k < NCOLL; k = k + 1) begin
            dl = (t_last[1][k] - t_first[1][k]) - (t_last[0][k] - t_first[0][k]);
            lat0 = lat0 + t_last[0][k] - t_first[0][k];
            lat1 = lat1 + t_last[1][k] - t_first[1][k];
            if (dl < dlat_min) dlat_min = dl;
            if (dl > dlat_max) dlat_max = dl;
            if (cmode[k]) begin nga = nga + 1; dsum_ga = dsum_ga + dl; end else begin nar = nar + 1; dsum_ar = dsum_ar + dl; end
        end
        for (d = 0; d < N; d = d + 1) if (qw[0][d] != qw[1][d]) mism = mism + 1;
        if (flt[0] !== flt[1] || fc[0] !== fc[1]) begin $display("FAULT MISMATCH ref %b/%b new %b/%b", flt[0], fc[0], flt[1], fc[1]); mism = mism + 1; end
        $display("RESULT N=%0d DEPTH=%0d LAT=%0d BPC=%0d FIFO_IMPL=%0d ADD_IMPL=%0d SERIAL=%0d SEED=%0d colls=%0d (ar %0d, gather %0d) words_compared=%0d mismatches=%0d fault=%b/%b code=%b/%b cycles_ref=%0d cycles_new=%0d",
                 N, DEPTH, LAT, BPC, FIFO_IMPL, ADD_IMPL, SERIAL, SEED, NCOLL, nar, nga, compared, mism, flt[0], flt[1], fc[0], fc[1],
                 t_last[0][NCOLL-1], t_last[1][NCOLL-1]);
        $display("LATENCY sum_ref=%0d sum_new=%0d delta_per_collective min=%0d max=%0d ar_avg_x100=%0d gather_avg_x100=%0d",
                 lat0, lat1, dlat_min, dlat_max, nar ? dsum_ar * 100 / nar : 0, nga ? dsum_ga * 100 / nga : 0);
        $finish;
    end
endmodule
