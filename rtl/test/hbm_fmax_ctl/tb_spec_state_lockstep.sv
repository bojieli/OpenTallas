`timescale 1ns/1ps
// Lockstep bench: ot_dshbm_spec_state (as built) vs ot_dshbm_spec_state_f on one random request / n_set / token
// write stream (every kind incl. illegal ones, positions inside and outside the rings' reach, rollback-sized and
// arbitrary n jumps, n_set edges >= 3 apart).  The successor's a_* outputs must equal the original's
// delayed by LAT cycles, every cycle; req_ready and n must be equal in the same cycle.
module tb_spec_state_lockstep;
    parameter integer NREQ = 20000, SEED = 1, LAT = 5, DRAIN = 1;
    parameter integer W = 128, PMAX = 8, WR = 136, SR = 136, TR = 16, NG = 4, NL = 40, NST = 3, NSRC = 4;
    parameter [15:0] RLOG = 16'h7272;
    parameter integer CKMAX = 262144, TW = 17, AW = 32;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg n_set = 0, tw_v = 0, req_v = 0; reg [31:0] n_val = 0, tw_pos = 0, req_pos = 0; reg [TW-1:0] tw_tok = 0;
    reg [3:0] req_kind = 0; reg [15:0] req_idx = 0;
    wire [31:0] n0, n1; wire r0, r1;
    wire v0, v1, p0, p1, l0, l1, e0, e1; wire [AW-1:0] ad0, ad1; wire [TW-1:0] t0, t1;
    ot_dshbm_spec_state #(.W(W), .PMAX(PMAX), .WR(WR), .SR(SR), .TR(TR), .NG(NG), .NL(NL), .NST(NST), .NSRC(NSRC),
        .RLOG(RLOG), .CKMAX(CKMAX), .TW(TW), .AW(AW)) d0 (.clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .n(n0),
        .tw_v(tw_v), .tw_pos(tw_pos), .tw_tok(tw_tok), .req_v(req_v), .req_ready(r0), .req_kind(req_kind),
        .req_idx(req_idx), .req_pos(req_pos), .a_v(v0), .a_addr(ad0), .a_tok(t0), .a_pad(p0), .a_last(l0), .a_err(e0));
    ot_dshbm_spec_state_f #(.W(W), .PMAX(PMAX), .WR(WR), .SR(SR), .TR(TR), .NG(NG), .NL(NL), .NST(NST), .NSRC(NSRC),
        .RLOG(RLOG), .CKMAX(CKMAX), .TW(TW), .AW(AW)) d1 (.clk(clk), .rst_n(rst_n), .n_set(n_set), .n_val(n_val), .n(n1),
        .tw_v(tw_v), .tw_pos(tw_pos), .tw_tok(tw_tok), .req_v(req_v), .req_ready(r1), .req_kind(req_kind),
        .req_idx(req_idx), .req_pos(req_pos), .a_v(v1), .a_addr(ad1), .a_tok(t1), .a_pad(p1), .a_last(l1), .a_err(e1));
    localparam integer OW = 1 + AW + TW + 3;
    wire [OW-1:0] o0 = {v0, ad0, t0, p0, l0, e0}, o1 = {v1, ad1, t1, p1, l1, e1};
    reg [OW-1:0] hist [0:LAT];
    integer last_tw = -100, resets = 0, k, cyc = 0, bad = 0, beats = 0, errs = 0, toks = 0, seed, q, last_set = -10, nreq = 0;
    always @(posedge clk) if (rst_n) begin
        for (k = LAT; k > 0; k = k - 1) hist[k] = hist[k-1];
        hist[0] = o0;
        cyc = cyc + 1;
        if (cyc > LAT && hist[LAT] !== o1) begin bad = bad + 1; if (bad < 8) $display("MISMATCH cyc %0d want %h got %h", cyc, hist[LAT], o1); end
        if (r0 !== r1 || n0 !== n1) begin bad = bad + 1; if (bad < 8) $display("MISMATCH ready/n cyc %0d", cyc); end
        if (v0) beats = beats + 1;
        if (v0 && !p0 && $isunknown(t0) == 0) toks = toks + 1;
    end
    function [31:0] rpos(input integer dummy);
        integer r;
        begin
            r = $random(seed);
            case ($unsigned(r) % 8)
                0: rpos = $unsigned($random(seed));                 // anywhere
                1: rpos = n0 + ($unsigned($random(seed)) % 4);      // tiny
                2, 3: rpos = n0 - 1 + ($signed($random(seed)) % 12);
                default: rpos = n0 + ($signed($random(seed)) % 140);
            endcase
        end
    endfunction
    initial begin
        seed = SEED;
        for (k = 0; k <= LAT; k = k + 1) hist[k] = 0;
        repeat (3) @(posedge clk); rst_n = 1;
        while (nreq < NREQ) begin
            @(negedge clk);
            n_set = 0; tw_v = 0; req_v = 0;
            if (nreq % 150 == 149 && r0) begin              // re-arm the sticky a_err: reset both, drain history
                // Scoped sticky-fault re-arm: inputs are already inactive.
                if (DRAIN) begin repeat (LAT + 1) @(negedge clk); end
                if (cyc - last_tw <= LAT + 1) $display("DIAG reset at cyc %0d, last token write cyc %0d (in flight)", cyc, last_tw);
                rst_n = 0; nreq = nreq + 1; @(negedge clk); rst_n = 1; for (k = 0; k <= LAT; k = k + 1) hist[k] = 0; cyc = 0;
                resets = resets + 1;
            end
            q = $unsigned($random(seed)) % 16;
            if (q == 0 && cyc - last_set >= 3) begin
                n_set = 1; last_set = cyc + 1;
                case ($unsigned($random(seed)) % 8)
                    0: n_val = 0;
                    1: n_val = $unsigned($random(seed)) % 2000000;
                    default: n_val = n0 + 1 + ($unsigned($random(seed)) % PMAX);
                endcase
            end
            if (q < 4) begin tw_v = 1; last_tw = cyc; tw_pos = n0 + ($unsigned($random(seed)) % PMAX) - (q == 3 ? 3 : 0); tw_tok = $random(seed); end
            if (r0 && q >= 6) begin
                req_v = 1; nreq = nreq + 1;
                req_kind = ($unsigned($random(seed)) % 20 == 0) ? $random(seed) : 1 + $unsigned($random(seed)) % 10;
                req_idx = ($unsigned($random(seed)) % 16 == 0) ? $random(seed) : $unsigned($random(seed)) % 4;
                req_pos = rpos(0);
                if (req_kind == 2 || req_kind == 4) if ($random(seed) & 1) req_pos = $unsigned($random(seed)) % 300;
                // the rl-dependent kinds index RLOG by source (< NSRC) and IK_RD walks (p+1) >> rl rows
                if (req_kind == 5 || req_kind == 6 || req_kind == 7 || req_kind == 8) req_idx = req_idx % NSRC;
                if (req_kind == 8) req_pos = $unsigned($random(seed)) % 3000;
                // window walks run from max(0, p-W+1) to p: a position >= 2^31 (n - 1 at n = 0) would walk 2^32 rows
                if ((req_kind == 2 || req_kind == 4 || req_kind == 6) && req_pos[31]) req_pos = ~req_pos;
            end
        end
        @(negedge clk); n_set = 0; tw_v = 0; req_v = 0;
        repeat (400) @(negedge clk);
        $display("LOCKSTEP spec_state requests=%0d beats=%0d token_beats=%0d cycles=%0d lat=%0d resets=%0d mismatches=%0d", NREQ, beats, toks, cyc, LAT, resets, bad);
        if (bad != 0) $fatal(1, "LOCKSTEP FAIL mismatches=%0d", bad);
        $finish;
    end
endmodule
