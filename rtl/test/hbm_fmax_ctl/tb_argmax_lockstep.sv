`timescale 1ns/1ps
// Lockstep bench: ot_dshbm_argmax FAST = 0 (as built) vs FAST = 1 on one random stream of rows (random lengths
// and short last beats, biased / unbiased rows, ties, +-0, NaN, Inf and overflowing biases, gaps and back-to-back
// rows).  The successor's outputs must equal the original's delayed by one cycle, every cycle.
module tb_argmax_lockstep;
    parameter integer LP = 8, IW = 17, NROW = 3000, SEED = 1, F1 = 1;   // F1: FAST of the second instance (0: delay 0)
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg in_v = 0, in_last = 0, in_bias_en = 0; reg [LP-1:0] in_mask = 0; reg [LP*32-1:0] in_vals = 0, in_bias = 0;
    wire v0, v1, n0, n1, f0, f1; wire [IW-1:0] i0, i1;
    ot_dshbm_argmax #(.LP(LP), .IW(IW), .FLAT(7), .FAST(0)) d0 (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_last(in_last),
        .in_bias_en(in_bias_en), .in_mask(in_mask), .in_vals(in_vals), .in_bias(in_bias), .out_v(v0), .out_idx(i0),
        .out_nan(n0), .fault(f0));
    ot_dshbm_argmax #(.LP(LP), .IW(IW), .FLAT(7), .FAST(F1)) d1 (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_last(in_last),
        .in_bias_en(in_bias_en), .in_mask(in_mask), .in_vals(in_vals), .in_bias(in_bias), .out_v(v1), .out_idx(i1),
        .out_nan(n1), .fault(f1));
    reg [IW+2:0] h = 0;
    integer bad = 0, rows = 0, faults = 0, cyc = 0, seed, r, b, k, len, md;
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (F1 == 0) h = {v0, n0, f0, i0};
        if (cyc > 2 && ({h[IW+2], h[IW+1], h[IW], (h[IW+2] ? h[IW-1:0] : {IW{1'b0}})} !== {v1, n1, f1, (v1 ? i1 : {IW{1'b0}})})) begin
            bad = bad + 1; if (bad < 8) $display("MISMATCH cyc %0d want %h got v%b n%b f%b i%0d", cyc, h, v1, n1, f1, i1);
        end
        h = {v0, n0, f0, i0};
        if (v0) rows = rows + 1;
        if (f0) faults = faults + 1;
    end
    function [31:0] rv(input integer m);
        reg [31:0] x;
        begin
            x = $random(seed);
            case (m)
                0: rv = x;                                                  // anything incl. NaN / Inf
                1: rv = {x[31], 8'd127 + x[1:0], x[22:21], 21'd0};          // ties
                2: rv = (x[2:0] == 0) ? 32'h8000_0000 : (x[2:0] == 1) ? 32'h0 : (x[2:0] == 2) ? 32'h7f80_0001 : {x[31], 8'd126, 23'd5};
                default: rv = {x[31], 8'd250 + x[2:0], x[22:0]};            // near overflow (biased: Inf faults)
            endcase
        end
    endfunction
    initial begin
        seed = SEED;
        repeat (3) @(posedge clk); rst_n = 1;
        @(negedge clk);
        for (r = 0; r < NROW; r = r + 1) begin
            md = $unsigned($random(seed)) % 4; len = 1 + $unsigned($random(seed)) % 60;
            in_bias_en = $random(seed);
            for (b = 0; b < len; b = b + LP) begin
                in_v = 1; in_last = (b + LP >= len);
                for (k = 0; k < LP; k = k + 1) begin
                    in_mask[k] = (b + k < len);
                    in_vals[32*k +: 32] = rv(md); in_bias[32*k +: 32] = rv(md);
                end
                @(negedge clk);
                if (($random(seed) & 7) == 0 && !in_last) begin in_v = 0; @(negedge clk); end
            end
            in_v = 0; in_last = 0;
            if ($random(seed) & 1) repeat ($unsigned($random(seed)) % 4) @(negedge clk);
        end
        repeat (40) @(negedge clk);
        $display("LOCKSTEP argmax rows=%0d results=%0d faults=%0d mismatches=%0d", NROW, rows, faults, bad);
        $finish;
    end
endmodule
