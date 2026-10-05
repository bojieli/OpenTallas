`timescale 1ns/1ps
// Lockstep: the generated Qwen core, original (ot_hdc_core_vector_weight.sv) against the 1.2 GHz successor
// (ot_hdc_core_vector_weight_f12.sv, DEC_FAST and ME_ISSUE_RE as given), each in the physical context wrapper (stream
// gating OPT GREF / GOPT, deterministic registered-boundary unit stubs).  Random 1024-bit program words (END with
// probability 1/8 so tokens finish and restart), random token / position per start, a random segment table written
// with each start, and a monotone window count.  With ME_ISSUE_RE = 0 and GREF == GOPT % 2 (OPT 1 is zero-cycle)
// every output and both stubs' captured fields must match on every cycle.  Sources from gen_core_lockstep.py.
module tb_qwen_core_f12_lockstep;
    parameter integer MEIR = 0, DECF = 1, GOPT = 1, GREF = 0, NSEG = 8;
    localparam integer G = 6144, NW = 18, SW = 64, CW = 32;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg start = 0;
    reg [NW-1:0] token = 0, pos = 0;
    reg [NSEG*24-1:0] sb, sl; reg [NSEG*CW-1:0] ss; reg [NSEG*2-1:0] sk;
    reg [CW-1:0] a_bin = 0, a_gray = 0;
    reg [1023:0] rom [0:4095];
    reg [1023:0] q0, q1;
    wire d0, d1, f0, f1, pr0, pr1, ce0, ce1, wr0, wr1, ov0, ov1, mx0, mx1, hf0, hf1;
    wire [NW-1:0] nt0, nt1; wire [31:0] nv0, nv1, cy0, cy1; wire [11:0] pa0, pa1;
    wire [(G>>7)-1:0] mw0, mw1; wire [SW-1:0] sw0, sw1, kw0, kw1; wire [CW-1:0] wc0, wc1;
    ot_qwen_hbmacc_core_ctx_ref #(.GATE_OPT(GREF)) u0 (.clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(d0), .next_token(nt0), .next_val(nv0), .cycles(cy0), .fault(f0), .prog_re(pr0), .prog_addr(pa0), .prog_q(q0),
        .fab_fault(1'b0), .me_clk_en(ce0), .wrom_re(wr0), .me_ov(ov0), .vw_me_we(mw0), .vw_mx_we(mx0), .vw_su_we(sw0),
        .kv_we(kw0), .seg_base(sb), .seg_len(sl), .seg_sidx(ss), .seg_kind(sk), .w_a_gray(a_gray), .w_c_gray(wc0), .hbm_fault(hf0));
    ot_qwen_hbmacc_core_ctx_f12 #(.GATE_OPT(GOPT), .ME_ISSUE_RE(MEIR), .DEC_FAST(DECF)) u1 (.clk(clk), .rst_n(rst_n),
        .start(start), .token(token), .pos(pos),
        .done(d1), .next_token(nt1), .next_val(nv1), .cycles(cy1), .fault(f1), .prog_re(pr1), .prog_addr(pa1), .prog_q(q1),
        .fab_fault(1'b0), .me_clk_en(ce1), .wrom_re(wr1), .me_ov(ov1), .vw_me_we(mw1), .vw_mx_we(mx1), .vw_su_we(sw1),
        .kv_we(kw1), .seg_base(sb), .seg_len(sl), .seg_sidx(ss), .seg_kind(sk), .w_a_gray(a_gray), .w_c_gray(wc1), .hbm_fault(hf1));
    always @(posedge clk) begin q0 <= rom[pa0]; q1 <= rom[pa1]; end
    reg [31:0] rs;
    function automatic [31:0] rnd(input integer dummy);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); rnd = rs; end
    endfunction
    integer seed, cycles, c, i, w, errs, tokens, idle_n, wbits;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles = 200000;
        rs = 32'h9e3779b9 ^ seed; if (rs == 0) rs = 1;
        for (i = 0; i < 4096; i = i + 1) begin
            for (w = 0; w < 32; w = w + 1) rom[i][32*w +: 32] = rnd(0);
            // unit field (bits [1:0] by tools/hdc_isa.py O_UNIT = 0): END 1/8, else ME or SU
            rom[i][1:0] = (rnd(0) % 8 == 0) ? 2'd0 : (rnd(0) % 2 ? 2'd1 : 2'd2);
            // keep the program live: barriers 1/16, chases 1/32 (their counts small), KV-sourced matrix ops 1/16,
            // DYN_TTILES (decode 6) 1/4 of the tile counts with a valid or invalid split
            rom[i][2] = (rnd(0) % 16 == 0);
            rom[i][3] = (rnd(0) % 32 == 0);
            if (rom[i][3]) rom[i][19:4] = rnd(0) & 16'h3;    // CHASE_N small when chasing
            rom[i][71] = (rnd(0) % 16 == 0);
            if (rnd(0) % 4 == 0) rom[i][233:231] = 3'd6;
        end
        for (i = 0; i < NSEG*24; i = i + 1) begin sb[i] = rnd(0); sl[i] = rnd(0); end
        for (i = 0; i < NSEG*CW; i = i + 1) ss[i] = rnd(0);
        for (i = 0; i < NSEG*2; i = i + 1) sk[i] = rnd(0);
        errs = 0; tokens = 0; idle_n = 0;
        repeat (4) @(posedge clk); #0.1 rst_n = 1;
        for (c = 0; c < cycles; c = c + 1) begin
            @(negedge clk);
            if ({d0, nt0, nv0, cy0, f0, pr0, pa0, ce0, wr0, ov0, mw0, mx0, sw0, kw0, wc0, hf0} !==
                {d1, nt1, nv1, cy1, f1, pr1, pa1, ce1, wr1, ov1, mw1, mx1, sw1, kw1, wc1, hf1} ||
                u0.core.u_me.f !== u1.core.u_me.f || u0.core.g_vsu.u_su.f !== u1.core.g_vsu.u_su.f) begin
                errs = errs + 1;
                if (errs < 10) $display("MISMATCH c=%0d done %b/%b pa %0d/%0d ce %b/%b me.f %0d su.f %0d", c, d0, d1, pa0, pa1, ce0, ce1,
                    u0.core.u_me.f !== u1.core.u_me.f, u0.core.g_vsu.u_su.f !== u1.core.g_vsu.u_su.f);
            end
            start = 0;
            if (u0.core.st == 2'd0) begin
                idle_n = idle_n + 1;
                if (idle_n > 3 && rnd(0) % 4 == 0) begin
                    start = 1; tokens = tokens + 1; idle_n = 0;
                    token = rnd(0); pos = rnd(0) & 18'h3ffff;
                end
            end else idle_n = 0;
            if (rnd(0) % 3 == 0) a_bin = a_bin + (rnd(0) & 3);
            a_gray = a_bin ^ (a_bin >> 1);
        end
        $display("RESULT core_lockstep MEIR=%0d DECF=%0d GOPT=%0d seed=%0d cycles=%0d tokens=%0d mismatches=%0d", MEIR, DECF, GOPT, seed, cycles, tokens, errs);
        $finish;
    end
endmodule
