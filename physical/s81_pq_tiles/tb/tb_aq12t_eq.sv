`timescale 1ns/1ps
// Lockstep equivalence: T_AQ tile ot_dsrom_aq12t (SRAM-ring x wait line) vs the routed quantiser ot_dsrom_aq12m, same
// stimulus, every cycle: vo and fault always; q / e / y on every vo.  Stimulus mixes random FP32, small / subnormal /
// zero lanes, Inf/NaN lanes (fault path), equal-magnitude ties and a wide exponent spread; valid ~ random with bursts.
// +NCYC=<n> (default 40000), +SEED=<s>.  Prints AQ12T_EQ PASS / AQ12T_EQ FAIL.
module tb_aq12t_eq;
    reg clk = 0, rst_n = 0, v = 0;
    reg [1023:0] x;
    always #0.5 clk = ~clk;
    wire vo_a, vo_b, f_a, f_b;
    wire [255:0] q_a, q_b;
    wire signed [9:0] e_a, e_b;
    wire [511:0] y_a, y_b;
    ot_dsrom_aq12m u_ref (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo_a), .q(q_a), .e(e_a), .y(y_a), .fault(f_a));
    ot_dsrom_aq12t u_dut (.clk(clk), .rst_n(rst_n), .v(v), .x(x), .vo(vo_b), .q(q_b), .e(e_b), .y(y_b), .fault(f_b));
    integer seed, ncyc, cyc, nv, nerr, i, mode;
    reg [31:0] w;
    function [31:0] lane(input integer m);
        reg [31:0] r;
        begin
            r = $random(seed);
            case (m)
                0: lane = r;                                                // any pattern (incl. Inf/NaN, rare)
                1: lane = {r[31], 8'd127 + r[10:8] - 8'd3, r[22:0]};        // near 1.0
                2: lane = {r[31], 8'd0, (r[5]) ? r[22:0] : 23'd0};          // zero / subnormal
                3: lane = {r[31], 8'd100 + r[29:24], r[22:0]};              // mid spread
                4: lane = {r[31], 8'd1 + r[30:24], r[22:0]};                // wide spread, finite
                default: lane = {r[31], 8'd120, 23'd0};                     // ties
            endcase
        end
    endfunction
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261011;
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 40000;
        nv = 0; nerr = 0; x = 0;
        repeat (5) @(posedge clk);
        rst_n = 1;
        repeat (8) @(posedge clk);                       // the tile reset relay (sync 2 + tree 1) releases first
        for (cyc = 0; cyc < ncyc + 40; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc < ncyc) begin
                v = ((cyc / 64) % 3 == 0) ? 1'b1 : ($random(seed) & 1);
                mode = ($random(seed) & 32'h7fffffff) % 6;
                for (i = 0; i < 32; i = i + 1) begin
                    w = lane((mode == 0 && (($random(seed) & 255) != 0)) ? 4 : (($random(seed) & 7) == 0) ? 2 : mode);
                    x[32*i +: 32] = w;
                end
            end else begin v = 0; x = {32{$random(seed)}}; end
            @(posedge clk); #0.1;
            if (vo_a !== vo_b || f_a !== f_b) begin
                nerr = nerr + 1; if (nerr < 5) $display("MISMATCH vo/fault cyc %0d: %b%b vs %b%b", cyc, vo_a, f_a, vo_b, f_b);
            end else if (vo_a === 1'b1) begin
                nv = nv + 1;
                if (q_a !== q_b || e_a !== e_b || y_a !== y_b) begin
                    nerr = nerr + 1; if (nerr < 5) $display("MISMATCH data cyc %0d", cyc);
                end
            end
        end
        if (nerr == 0 && nv > ncyc / 3) $display("AQ12T_EQ PASS valid_outputs=%0d cycles=%0d", nv, ncyc);
        else $display("AQ12T_EQ FAIL errors=%0d valid_outputs=%0d", nerr, nv);
        $finish;
    end
endmodule
