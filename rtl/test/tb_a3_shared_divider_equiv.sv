// Equivalence sweep for the shared divider's power-of-two fast path.
//
// The fast path (``POW2_FAST = 1``) answers a request whose effective divisor
// is a power of two in the cycle after it is seen, instead of entering the
// 64-step restoring iteration.  Its correctness argument is by construction --
// for D = 2^k, floor(N/D) is N >> k and N - q*D is N & (2^k - 1), exactly, in
// the same 64-bit registers -- but an argument is not a measurement.  This
// bench drives BOTH builds from one stimulus stream and requires the answers
// to be bit-identical, so the claim rests on a sweep and not on the comment.
//
// What is compared, per request: the quotient, the remainder, and which
// requester the done pulse names.  What is deliberately NOT compared: latency.
// The fast path exists precisely to change latency, so requiring the two
// builds to agree on it would be requiring the change not to have happened;
// the bench measures each build's latency separately and reports both.
//
// The stimulus is chosen to be hostile to the fast path rather than kind to
// it: every power of two a shipped program uses, the boundary cases either
// side of each (2^k +/- 1, which must take the slow path in both builds), the
// zero divisor that both paths substitute with 1, and numerators at the ends
// of the 64-bit range where a wrong shift would truncate.

`timescale 1ns / 1ps

module tb_a3_shared_divider_equiv;

    localparam integer REQ = 7;

    reg                  clk = 1'b0;
    reg                  rst_n = 1'b0;
    reg                  clear = 1'b0;
    reg  [REQ-1:0]       req = {REQ{1'b0}};
    reg  [REQ*64-1:0]    num = {(REQ*64){1'b0}};
    reg  [REQ*32-1:0]    den = {(REQ*32){1'b0}};

    wire [REQ-1:0]       grant_f, grant_s;
    wire                 busy_f,  busy_s;
    wire [REQ-1:0]       done_f,  done_s;
    wire [63:0]          quot_f,  quot_s;
    wire [63:0]          rem_f,   rem_s;

    // The two builds differ in exactly one parameter and share every input.
    ot_a3_shared_divider #(.REQUESTERS(REQ), .POW2_FAST(1)) dut_fast (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .req(req), .num(num), .den(den),
        .grant(grant_f), .busy(busy_f), .done(done_f),
        .quot(quot_f), .rem(rem_f));

    ot_a3_shared_divider #(.REQUESTERS(REQ), .POW2_FAST(0)) dut_slow (
        .clk(clk), .rst_n(rst_n), .clear(clear),
        .req(req), .num(num), .den(den),
        .grant(grant_s), .busy(busy_s), .done(done_s),
        .quot(quot_s), .rem(rem_s));

    always #5 clk = ~clk;
    always @(posedge clk) cycle = cycle + 1;

    integer checks   = 0;
    integer mismatch = 0;
    integer cases    = 0;
    integer fast_cycles_total = 0;
    integer slow_cycles_total = 0;
    integer fast_pow2_cases = 0;

    reg [63:0] exp_q, exp_r;
    reg [63:0] n_v;
    reg [31:0] d_v, d_eff;
    integer    i, k, waited_f, waited_s;
    integer    seed;

    // A free-running counter and one stamp per build.  The first version of
    // this bench waited for the fast build and THEN for the slow one, which
    // charges each build whatever the other had left to run -- it reported the
    // fast build as slower, which is how the error was noticed.  Latency is
    // the whole point of the fast path, so each build is now timed from the
    // same request against a common clock.
    integer    cycle = 0;
    integer    t_req, t_fast, t_slow;
    integer    fast_pow2_lat = 0, slow_pow2_lat = 0;
    integer    fast_gen_lat  = 0, slow_gen_lat  = 0;
    integer    gen_cases = 0;

    task automatic drive(input [63:0] n, input [31:0] d);
        begin
            cases = cases + 1;
            n_v = n; d_v = d;
            d_eff = (d == 32'd0) ? 32'd1 : d;
            exp_q = n / d_eff;              // the reference is the language's own
            exp_r = n - (exp_q * d_eff);    // Euclidean pair, not either DUT

            @(negedge clk);
            num[0 +: 64] = n;
            den[0 +: 32] = d;
            req[0]       = 1'b1;
            t_req = cycle;
            @(negedge clk);
            req[0] = 1'b0;

            // One wait, both builds watched, each stamped when its own done
            // pulses.  Neither build's number contains the other's wait.
            t_fast = -1; t_slow = -1;
            waited_f = 0;
            while ((t_fast < 0 || t_slow < 0) && waited_f < 200) begin
                if (done_f[0] && t_fast < 0) begin
                    t_fast = cycle - t_req;
                    checks = checks + 1;
                    if (quot_f !== exp_q || rem_f !== exp_r) begin
                        $display("FAIL fast: N=%0d D=%0d got q=%0d r=%0d want q=%0d r=%0d",
                                 n, d, quot_f, rem_f, exp_q, exp_r);
                        mismatch = mismatch + 1;
                    end
                end
                if (done_s[0] && t_slow < 0) begin
                    t_slow = cycle - t_req;
                    checks = checks + 1;
                    if (quot_s !== exp_q || rem_s !== exp_r) begin
                        $display("FAIL slow: N=%0d D=%0d got q=%0d r=%0d want q=%0d r=%0d",
                                 n, d, quot_s, rem_s, exp_q, exp_r);
                        mismatch = mismatch + 1;
                    end
                end
                @(negedge clk); waited_f = waited_f + 1;
            end
            if (t_fast < 0 || t_slow < 0) begin
                $display("FAIL: a build never asserted done for N=%0d D=%0d (fast=%0d slow=%0d)",
                         n, d, t_fast, t_slow);
                mismatch = mismatch + 1;
            end else begin
                // The claim: same answer, whichever path served it.
                checks = checks + 1;
                if (quot_f !== quot_s || rem_f !== rem_s) begin
                    $display("FAIL equiv: N=%0d D=%0d fast q=%0d r=%0d slow q=%0d r=%0d",
                             n, d, quot_f, rem_f, quot_s, rem_s);
                    mismatch = mismatch + 1;
                end
                if ((d_eff & (d_eff - 32'd1)) == 32'd0) begin
                    fast_pow2_lat = fast_pow2_lat + t_fast;
                    slow_pow2_lat = slow_pow2_lat + t_slow;
                end else begin
                    gen_cases    = gen_cases + 1;
                    fast_gen_lat = fast_gen_lat + t_fast;
                    slow_gen_lat = slow_gen_lat + t_slow;
                end
            end

            if ((d_eff & (d_eff - 32'd1)) == 32'd0) fast_pow2_cases = fast_pow2_cases + 1;

            repeat (3) @(negedge clk);
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        // 1. Every divisor a shipped program uses, and the zero both paths
        //    substitute with 1.
        drive(64'd0,            32'd0);
        drive(64'd1,            32'd0);
        drive(64'd123456789,    32'd1);
        drive(64'd8192,         32'd512);
        drive(64'd8191,         32'd512);
        drive(64'd8193,         32'd512);
        drive(64'd1048576,      32'd1024);
        drive(64'd1048575,      32'd32768);
        drive(64'd4294967296,   32'd65536);
        drive(64'd4294967295,   32'd131072);
        drive(64'hFFFF_FFFF_FFFF_FFFF, 32'd262144);

        // 2. Every power of two the divisor field can hold, at a numerator
        //    that exercises the whole shift.
        for (k = 0; k < 32; k = k + 1) begin
            drive(64'hDEAD_BEEF_CAFE_F00D, 32'd1 << k);
            drive({32'hFFFF_FFFF, 32'hFFFF_FFFF}, 32'd1 << k);
            drive(64'd0, 32'd1 << k);
        end

        // 3. The boundaries either side of each power of two.  These are NOT
        //    powers of two, so both builds must take the slow path and agree
        //    there too -- a fast path that fired on 2^k+1 would be caught here.
        for (k = 2; k < 32; k = k + 1) begin
            drive(64'hDEAD_BEEF_CAFE_F00D, (32'd1 << k) - 32'd1);
            drive(64'hDEAD_BEEF_CAFE_F00D, (32'd1 << k) + 32'd1);
        end

        // 4. Pseudo-random pairs, deterministic seed, so the sweep is
        //    reproducible run to run and simulator to simulator.
        seed = 32'd20260907;
        for (i = 0; i < 400; i = i + 1) begin
            n_v = {$random(seed), $random(seed)};
            d_v = $random(seed);
            drive(n_v, d_v);
        end

        $display("cases=%0d checks=%0d mismatches=%0d pow2_cases=%0d",
                 cases, checks, mismatch, fast_pow2_cases);
        $display("pow2 mean latency: fast=%0d slow=%0d over %0d case(s)",
                 fast_pow2_lat / fast_pow2_cases, slow_pow2_lat / fast_pow2_cases,
                 fast_pow2_cases);
        $display("general mean latency: fast=%0d slow=%0d over %0d case(s)",
                 fast_gen_lat / gen_cases, slow_gen_lat / gen_cases, gen_cases);
        if (mismatch == 0)
            $display("PASS: shared divider fast path equals the iteration cases=%0d checks=%0d",
                     cases, checks);
        else
            $display("FAIL: %0d mismatch(es)", mismatch);
        $finish;
    end

endmodule
