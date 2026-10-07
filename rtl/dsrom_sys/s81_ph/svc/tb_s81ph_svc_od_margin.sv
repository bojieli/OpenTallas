`timescale 1ns/1ps
// tb_s81ph_svc_io (CLAUDE S81-PH): transaction-level exact bench of the scan-service IO hub.  Random frame streams on
// every quadrant source (header len 0..LM, random valid gaps), random q words; scoreboard per source.  Checks: every
// q word reaches every quadrant in order; od / ad[a0] carry every source frame exactly once, contiguous (atomic), each
// source's frames in order; a1 / xd every word in order; nothing extra; all drained at the end.  +SEED, +N (frames
// per source).  Mutants: S81PH_SVC_MUT_NOATOM (re-arbitrate every word), S81PH_SVC_MUT_SKID (skid loses a word).
module tb_s81ph_svc_od_margin #(parameter integer MARGIN=1);
    localparam integer NQ = 4, LM = 40;
    reg ck = 0, rst = 0;
    always #0.4166 ck = ~ck;
    reg [514:0] q; wire [513:0] od, xd; wire [1025:0] ad; wire fault; wire [515*NQ-1:0] q_q;
    reg [NQ-1:0] od_v, a0_v; reg [512*NQ-1:0] od_d, a0_d; wire [NQ-1:0] od_r, a0_r;
    reg a1_v, x_v; reg [511:0] a1_d, x_d; wire a1_r, x_r;
`ifdef SVCIO_TILED
    ot_s81ph_svc_io_t #(.OD_MARGIN(MARGIN)) dut (
`else
    ot_s81ph_svc_io #(.NQ(NQ)) dut (
`endif.ck(ck), .rst(rst), .q(q), .od(od), .xd(xd), .ad(ad), .fault(fault), .q_q(q_q),
        .od_v(od_v), .od_d(od_d), .od_r(od_r), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r),
        .x_v(x_v), .x_d(x_d), .x_r(x_r));
    integer seed, NF, errs = 0, cyc = 0;
    // generated source words: word = {src 4, kind 4, seq 32, payload rest}; header carries len at [491:480]
    function [511:0] mkw(input integer kind, input integer src, input integer fr, input integer w, input integer len, input integer rnd);
        reg [511:0] x; begin
            x = {16{rnd[31:0] ^ (fr * 7919 + w * 104729 + src * 31 + kind)}};
            x[511:508] = (w == 0) ? 4'd3 : x[511:508];
            if (w == 0) x[491:480] = len[11:0];
            x[479:448] = {kind[7:0], src[7:0], fr[15:0]}; x[447:432] = w[15:0];
            mkw = x;
        end
    endfunction
    // per source state
    integer fr_od [0:NQ-1], w_od [0:NQ-1], len_od [0:NQ-1];
    integer fr_a0 [0:NQ-1], w_a0 [0:NQ-1], len_a0 [0:NQ-1];
    integer n_a1, n_x;
    // expected queues (simple arrays)
    reg [511:0] eq_od [0:NQ-1][0:65535]; integer eh_od [0:NQ-1], et_od [0:NQ-1];
    reg [511:0] eq_a0 [0:NQ-1][0:65535]; integer eh_a0 [0:NQ-1], et_a0 [0:NQ-1];
    reg [511:0] eq_a1 [0:65535]; integer eh_a1 = 0, et_a1 = 0;
    reg [511:0] eq_x [0:65535]; integer eh_x = 0, et_x = 0;
    reg [514:0] qh [0:65535]; integer qn = 0; integer qc [0:NQ-1];
    integer i, k, r;
    // output frame tracking
    integer cur_od, rem_od, cur_a0, rem_a0;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("N=%d", NF)) NF = 200;
        r = $random(seed);
        for (i = 0; i < NQ; i = i + 1) begin
            fr_od[i] = 0; w_od[i] = 0; len_od[i] = $urandom(seed + i) % (LM + 1);
            fr_a0[i] = 0; w_a0[i] = 0; len_a0[i] = $urandom(seed + 9 + i) % (LM + 1);
            eh_od[i] = 0; et_od[i] = 0; eh_a0[i] = 0; et_a0[i] = 0; qc[i] = 0;
        end
        n_a1 = 0; n_x = 0; cur_od = -1; rem_od = 0; cur_a0 = -1; rem_a0 = 0;
        od_v = 0; a0_v = 0; a1_v = 0; x_v = 0; q = 0;
        repeat (5) @(posedge ck); rst = 1; repeat (5) @(posedge ck);
    end
    // handshakes sampled at posedge (before the DUT updates), bookkeeping + new drive at negedge
    reg [NQ-1:0] acc_od, acc_a0; reg acc_a1, acc_x;
    always @(posedge ck) begin acc_od <= od_v & od_r; acc_a0 <= a0_v & a0_r; acc_a1 <= a1_v & a1_r; acc_x <= x_v & x_r; end
    always @(negedge ck) if (rst) begin
        cyc = cyc + 1;
        for (i = 0; i < NQ; i = i + 1) begin
            if (acc_od[i]) begin eq_od[i][et_od[i]] = od_d[512*i +: 512]; et_od[i] = et_od[i] + 1;
                if (w_od[i] == len_od[i]) begin fr_od[i] = fr_od[i] + 1; w_od[i] = 0; len_od[i] = $urandom % (LM + 1); end
                else w_od[i] = w_od[i] + 1; od_v[i] = 1'b0; end
            if (!od_v[i] && fr_od[i] < NF && ($urandom % 4) != 0) begin od_v[i] = 1'b1; od_d[512*i +: 512] = mkw(1, i, fr_od[i], w_od[i], len_od[i], $urandom); end
            if (acc_a0[i]) begin eq_a0[i][et_a0[i]] = a0_d[512*i +: 512]; et_a0[i] = et_a0[i] + 1;
                if (w_a0[i] == len_a0[i]) begin fr_a0[i] = fr_a0[i] + 1; w_a0[i] = 0; len_a0[i] = $urandom % (LM + 1); end
                else w_a0[i] = w_a0[i] + 1; a0_v[i] = 1'b0; end
            if (!a0_v[i] && fr_a0[i] < NF && ($urandom % 3) != 0) begin a0_v[i] = 1'b1; a0_d[512*i +: 512] = mkw(2, i, fr_a0[i], w_a0[i], len_a0[i], $urandom); end
        end
        if (acc_a1) begin eq_a1[et_a1] = a1_d; et_a1 = et_a1 + 1; n_a1 = n_a1 + 1; a1_v = 0; end
        if (!a1_v && n_a1 < NF * 4 && ($urandom % 2)) begin a1_v = 1; a1_d = mkw(3, 0, n_a1, 1, 0, $urandom); end
        if (acc_x) begin eq_x[et_x] = x_d; et_x = et_x + 1; n_x = n_x + 1; x_v = 0; end
        if (!x_v && n_x < NF * 4 && ($urandom % 2)) begin x_v = 1; x_d = mkw(4, 0, n_x, 1, 0, $urandom); end
        // q: random word every cycle while generating
        if (qn < NF * 8) begin q = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                                     $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            qh[qn] = q; qn = qn + 1; end
    end
    // q check: quadrant g sees q words in order at a fixed latency of 3 cycles
    reg [514:0] qd1, qd2, qd3; integer qi1, qi2, qi3;
    initial begin qi1 = -1; qi2 = -1; qi3 = -1; end
    always @(posedge ck) if (rst) begin
        // the word driven in cycle t is registered by q_p at t+1, q_rep t+2, q_q t+3
        if (qi3 >= 0) for (k = 0; k < NQ; k = k + 1) if (q_q[515*k +: 515] !== qh[qi3]) begin
            if (errs < 10) $display("MISMATCH q quadrant %0d word %0d", k, qi3); errs = errs + 1; end
        qi3 = qi2; qi2 = qi1; qi1 = (qn > 0 && rst) ? qn - 1 : -1;
    end
    // output checks
    integer s; reg [511:0] w;
    always @(posedge ck) if (rst) begin
        if (od[1]) begin
            w = od[513:2]; s = w[471:464];
            if (cur_od >= 0 && s != cur_od) begin if (errs < 10) $display("ATOMICITY od: src %0d inside a frame of %0d", s, cur_od); errs = errs + 1; end
            if (eh_od[s] >= et_od[s] || eq_od[s][eh_od[s]] !== w) begin if (errs < 10) $display("MISMATCH od src %0d word %0d (have %0d) got %h exp %h", s, eh_od[s], et_od[s], w[479:432], eq_od[s][eh_od[s]][479:432]); errs = errs + 1; end
            eh_od[s] = eh_od[s] + 1;
            if (cur_od < 0) begin cur_od = s; rem_od = w[491:480]; end else rem_od = rem_od - 1;
            if (rem_od == 0) cur_od = -1;
        end
        if (ad[0]) begin
            w = ad[512:1]; s = w[471:464];
            if (cur_a0 >= 0 && s != cur_a0) begin if (errs < 10) $display("ATOMICITY a0: src %0d inside a frame of %0d", s, cur_a0); errs = errs + 1; end
            if (eh_a0[s] >= et_a0[s] || eq_a0[s][eh_a0[s]] !== w) begin if (errs < 10) $display("MISMATCH a0 src %0d word %0d", s, eh_a0[s]); errs = errs + 1; end
            eh_a0[s] = eh_a0[s] + 1;
            if (cur_a0 < 0) begin cur_a0 = s; rem_a0 = w[491:480]; end else rem_a0 = rem_a0 - 1;
            if (rem_a0 == 0) cur_a0 = -1;
        end
        if (ad[513]) begin if (eq_a1[eh_a1] !== ad[1025:514] || eh_a1 >= et_a1) begin if (errs < 10) $display("MISMATCH a1 %0d", eh_a1); errs = errs + 1; end eh_a1 = eh_a1 + 1; end
        if (xd[1]) begin if (eq_x[eh_x] !== xd[513:2] || eh_x >= et_x) begin if (errs < 10) $display("MISMATCH x %0d", eh_x); errs = errs + 1; end eh_x = eh_x + 1; end
    end
    // end: all sources done and drained
    integer done, tot;
    always @(posedge ck) if (rst) begin
        done = (n_a1 >= NF * 4) && (n_x >= NF * 4) && (eh_a1 == et_a1) && (eh_x == et_x);
        tot = 0;
        for (k = 0; k < NQ; k = k + 1) begin
            done = done && fr_od[k] >= NF && fr_a0[k] >= NF && eh_od[k] == et_od[k] && eh_a0[k] == et_a0[k];
            tot = tot + et_od[k] + et_a0[k];
        end
        if (done || cyc > 2000000) begin
            if (!done) begin $display("TIMEOUT"); errs = errs + 1; end
            if (fault) begin $display("unexpected fault"); errs = errs + 1; end
            $display("SUMMARY seed=%0d frames/src=%0d words=%0d cycles=%0d errors=%0d", seed, NF, tot + et_a1 + et_x, cyc, errs);
            $display("RESULT %s", errs == 0 ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
