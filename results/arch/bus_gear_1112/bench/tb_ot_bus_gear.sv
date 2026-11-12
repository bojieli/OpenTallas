`timescale 1ns/1ps
// BUS-GEAR-1 bench: TX -> H registered stations -> RX against the unserialised reference (same bundle through one
// register + H stations + BEATS-1 pad).  Phase 1: N random words with spacing >= BEATS (random gaps), random side-band
// every cycle; every cycle checks v, d (on words) and s.  Phase 2: one word at spacing BEATS-1 -> fault_o must rise.
// Prints "RESULT PASS" / "RESULT FAIL <n>".  Mutants (MUT 1..3) must FAIL.
module tb_ot_bus_gear;
    parameter integer W = 288, BEATS = 2, H = 3, SW = 40, N = 4000, MUT = 0, SEED = 1;
    localparam integer BW = (W + BEATS - 1) / BEATS;
    localparam integer LAT = 1 + H + BEATS - 1;
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg v; reg [W-1:0] d; reg [SW-1:0] s;
    wire [BW-1:0] b; wire f, fault;
    ot_bus_gear_tx #(.W(W), .BEATS(BEATS), .MUT(MUT)) u_tx (.clk(clk), .rst_n(rst_n), .v_i(v), .d_i(d), .b_o(b), .f_o(f), .fault_o(fault));
    // side-band register at the TX face (same stage as the beats)
    reg [SW-1:0] s_tx; always @(posedge clk) s_tx <= s;
    // H stations on beats, flag and side-band
    reg [BW-1:0] bs [0:H]; reg fs [0:H]; reg [SW-1:0] ss [0:H];
    always @* begin bs[0] = b; fs[0] = f; ss[0] = s_tx; end
    genvar g;
    generate for (g = 1; g <= H; g = g + 1) begin : st
        always @(posedge clk) begin bs[g] <= bs[g-1]; fs[g] <= fs[g-1]; ss[g] <= ss[g-1]; end
    end endgenerate
    wire v_o; wire [W-1:0] d_o; wire [SW-1:0] s_o;
    ot_bus_gear_rx #(.W(W), .BEATS(BEATS), .SW(SW), .MUT(MUT)) u_rx (.clk(clk), .rst_n(rst_n), .b_i(bs[H]), .f_i(fs[H]),
        .s_i(ss[H]), .v_o(v_o), .d_o(d_o), .s_o(s_o));
    // reference delay line
    reg rv [0:LAT]; reg [W-1:0] rd [0:LAT]; reg [SW-1:0] rs [0:LAT];
    integer k;
    always @(posedge clk) begin
        rv[0] <= v; rd[0] <= d; rs[0] <= s;
        for (k = 1; k <= LAT; k = k + 1) begin rv[k] <= rv[k-1]; rd[k] <= rd[k-1]; rs[k] <= rs[k-1]; end
    end
    integer seed;
    integer err = 0, words = 0, seen = 0, cyc = 0, gap = 0, i, phase = 1;
    reg checking = 0;
    always @(negedge clk) if (checking) begin
        cyc = cyc + 1;
        if (v_o !== rv[LAT-1]) begin err = err + 1; if (err < 5) $display("v mismatch cyc %0d got %b exp %b", cyc, v_o, rv[LAT-1]); end
        if (rv[LAT-1] === 1'b1) begin
            seen = seen + 1;
            if (d_o !== rd[LAT-1]) begin err = err + 1; if (err < 5) $display("d mismatch cyc %0d", cyc); end
        end
        if (s_o !== rs[LAT-1]) begin err = err + 1; if (err < 5) $display("s mismatch cyc %0d", cyc); end
    end
    reg [W+31:0] rtmp;
    function [W-1:0] rnd_word; input integer dummy; integer j; begin
        for (j = 0; j < W; j = j + 32) rtmp[j +: 32] = $random;
        rnd_word = rtmp[W-1:0];
    end endfunction
    initial begin
        seed = SEED; k = $random(seed);
        v = 0; d = 0; s = 0;
        repeat (4) @(posedge clk);
        rst_n = 1;
        repeat (LAT + 2) @(posedge clk);
        checking = 1;
        // phase 1: legal spacing
        while (words < N) begin
            @(posedge clk); #0.1;
            s = $random;
            if (gap == 0 && ($random & 3) != 0) begin
                v = 1; d = rnd_word(0); words = words + 1;
                gap = BEATS - 1 + (($random & 7) == 0 ? ($random & 7) : 0);
            end else begin
                v = 0; d = rnd_word(0);   // non-word cycles carry garbage on the original bus
                if (gap > 0) gap = gap - 1;
            end
        end
        @(posedge clk); #0.1; v = 0;
        repeat (LAT + 4) @(posedge clk);
        checking = 0;
        if (fault !== 1'b0) begin err = err + 1; $display("fault raised on legal traffic"); end
        // phase 2: illegal spacing BEATS-1 -> fault must rise
        @(posedge clk); #0.1; v = 1; d = rnd_word(0);
        @(posedge clk); #0.1;                           // first word sampled
        repeat (BEATS - 2) begin v = 0; @(posedge clk); #0.1; end
        v = 1;                                          // second word BEATS-1 cycles after the first
        @(posedge clk); #0.1; v = 0;
        repeat (3) @(posedge clk);
        if (fault !== 1'b1) begin err = err + 1; $display("spacing violation not flagged"); end
        if (seen != words) begin err = err + 1; $display("words seen %0d of %0d", seen, words); end
        if (err == 0) $display("RESULT PASS W=%0d BEATS=%0d H=%0d words=%0d cycles=%0d LAT=%0d MUT=%0d", W, BEATS, H, words, cyc, LAT, MUT);
        else $display("RESULT FAIL %0d W=%0d BEATS=%0d H=%0d MUT=%0d", err, W, BEATS, H, MUT);
        $finish;
    end
endmodule
