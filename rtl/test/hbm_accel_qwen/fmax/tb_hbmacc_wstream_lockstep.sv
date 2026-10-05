`timescale 1ps/1fs
// Lockstep: ot_hbmacc_qwen_wstream (as measured in HA8) against its 1.2 GHz successor ot_hbmacc_qwen_wstream_f12 on
// the same stream: an engine model consumes complete words with random stalls (window-room blocking is exercised by
// long stalls), Gray coded through the real 2-flop crossing.  Every cycle a_gray, fault and st_words must match, and
// the four counting statistics must equal the original's one cycle earlier (the successor registers them).  +seed=<n> +cycles=<n> +words=<n>
module tb_hbmacc_wstream_lockstep;
    parameter integer NSTK = 4;
    localparam integer CW = 32;
    reg clk = 0, rst_n = 0;
    always #512 clk = ~clk;                       // the HBM controller clock, 1.024 ns
    reg go = 0;
    reg [CW-1:0] cfg_words, c_bin, c_gray;
    wire [CW-1:0] ag0, ag1, cy0, cy1, rd0, rd1, rb0, rb1, dg0, dg1, w0, w1;
    wire f0, f1;
    ot_hbmacc_qwen_wstream #(.ENABLE(1), .NSTK(NSTK), .REF_MODE(1), .WINW(160), .SPW(24), .CRED(32)) u0 (
        .clk(clk), .rst_n(rst_n), .go(go), .cfg_words(cfg_words), .c_gray(c_gray), .a_gray(ag0), .fault(f0),
        .st_cycles(cy0), .st_rd(rd0), .st_room_block(rb0), .st_desc_gap(dg0), .st_words(w0));
    ot_hbmacc_qwen_wstream_f12 #(.ENABLE(1), .NSTK(NSTK), .REF_MODE(1), .WINW(160), .SPW(24), .CRED(32)) u1 (
        .clk(clk), .rst_n(rst_n), .go(go), .cfg_words(cfg_words), .c_gray(c_gray), .a_gray(ag1), .fault(f1),
        .st_cycles(cy1), .st_rd(rd1), .st_room_block(rb1), .st_desc_gap(dg1), .st_words(w1));
    function automatic [CW-1:0] g2b(input [CW-1:0] g);
        integer i; begin g2b[CW-1] = g[CW-1]; for (i = CW - 2; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i]; end
    endfunction
    reg [CW-1:0] cy0d, rd0d, rb0d, dg0d;
    always @(posedge clk) begin cy0d <= cy0; rd0d <= rd0; rb0d <= rb0; dg0d <= dg0; end
    integer seed, seed0, cycles, words, c, errs, stall;
    // xorshift32 (simulator-independent; Verilator's $random(seed) ignores the seed variable)
    reg [31:0] rs;
    function automatic integer rnd(input integer dummy);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); rnd = rs; end
    endfunction
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        seed0 = seed;
        rs = 32'h9e3779b9 ^ seed; if (rs == 0) rs = 1;
        if (!$value$plusargs("cycles=%d", cycles)) cycles = 60000;
        if (!$value$plusargs("words=%d", words)) words = 1500;
        cfg_words = words; c_bin = 0; c_gray = 0; errs = 0; stall = 0;
        repeat (4) @(posedge clk);
        #100 rst_n = 1;
        repeat (3) @(posedge clk);
        #100 go = 1;
        for (c = 0; c < cycles; c = c + 1) begin
            @(negedge clk);
            if (ag0 !== ag1 || f0 !== f1 || cy0d !== cy1 || rd0d !== rd1 || rb0d !== rb1 || dg0d !== dg1 || w0 !== w1) begin
                errs = errs + 1;
                if (errs < 10) $display("MISMATCH c=%0d a %h/%h f %b/%b cyc %0d/%0d rd %0d/%0d room %0d/%0d gap %0d/%0d words %0d/%0d",
                    c, ag0, ag1, f0, f1, cy0d, cy1, rd0d, rd1, rb0d, rb1, dg0d, dg1, w0, w1);
            end
            // engine: consume available words, with random stalls (some long, so the window fills)
            if (stall > 0) stall = stall - 1;
            else if (rnd(0) % 3000 == 0) stall = 2000 + (rnd(0) & 8191);
            else if (c_bin < g2b(ag0) && (rnd(0) % 4 != 0)) c_bin = c_bin + 1;
            c_gray = c_bin ^ (c_bin >> 1);
        end
        $display("RESULT wstream_lockstep NSTK=%0d seed=%0d cycles=%0d words=%0d complete=%0d rd=%0d room_block=%0d desc_gap=%0d mismatches=%0d",
                 NSTK, seed0, cycles, words, w0, rd0, rb0, dg0, errs);
        $finish;
    end
endmodule
