`timescale 1ns/1ps
// PATH-S81/HCORE 10-25: exact cycle-by-cycle miter of the f12 binary32 adders with the replicated swap select
// (-DOT_F12_SWAP_REP) against the unchanged reference text (modules renamed *_ref).  Three cut variants: l4
// cuts 0 and 6 open: 6'b101010), l5x (7'b1101010: cut 6 closed, cut 0 open), l5 (6'b101011: cut 0 closed, g_swq path).
// Every cycle compares y, err, valid_out of all three pairs; no masking.  Operands are biased so the equal-exponent-field
// branch of the swap select (f_eq, fraction compare decides) and every alignment distance are exercised.
module tb;
    reg clk = 0, rst_n = 0, vin = 0;
    reg [31:0] a = 0, b = 0;
    wire [31:0] y4, y4r, y5x, y5xr, y5, y5r;
    wire [1:0]  e4, e4r, e5x, e5xr, e5, e5r;
    wire        v4, v4r, v5x, v5xr, v5, v5r;
    ot_hdc_fp32_add_f12_l4      d4  (.clk(clk), .rst_n(rst_n), .valid_in(vin), .a(a), .b(b), .y(y4),  .err(e4),  .valid_out(v4));
    ot_hdc_fp32_add_f12_l4_ref  r4  (.clk(clk), .rst_n(rst_n), .valid_in(vin), .a(a), .b(b), .y(y4r), .err(e4r), .valid_out(v4r));
    ot_hdc_fp32_add_f12_l5x     d5x (.clk(clk), .rst_n(rst_n), .valid_in(vin), .a(a), .b(b), .y(y5x),  .err(e5x),  .valid_out(v5x));
    ot_hdc_fp32_add_f12_l5x_ref r5x (.clk(clk), .rst_n(rst_n), .valid_in(vin), .a(a), .b(b), .y(y5xr), .err(e5xr), .valid_out(v5xr));
    ot_hdc_fp32_add_f12_l5      d5  (.clk(clk), .rst_n(rst_n), .valid_in(vin), .a(a), .b(b), .y(y5),  .err(e5),  .valid_out(v5));
    ot_hdc_fp32_add_f12_l5_ref  r5  (.clk(clk), .rst_n(rst_n), .valid_in(vin), .a(a), .b(b), .y(y5r), .err(e5r), .valid_out(v5r));
    reg [63:0] st;
    function automatic [63:0] xs(input [63:0] x);
        reg [63:0] t; begin t = x ^ (x << 13); t = t ^ (t >> 7); xs = t ^ (t << 17); end
    endfunction
    integer cyc = 0, ncyc = 2000000, seed = 1, mis = 0, n_eq = 0, n_eqsw = 0, n_val = 0, n_dist = 0;
    reg [7:0] fa, fb;
    reg [3:0] mode;
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("cycles=%d", ncyc)) ncyc = 2000000;
        st = 64'h9e3779b97f4a7c15 ^ {32'd0, seed[31:0]} ^ ({32'd0, seed[31:0]} << 40);
    end
    always #1 clk = ~clk;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1;
        st = xs(st);
        mode = st[3:0];
        vin <= st[4] | st[5];
        a <= st[63:32];
        b <= st[31:0];
        st = xs(st);
        case (mode)
            4'd0, 4'd1, 4'd2, 4'd3, 4'd4: begin            // equal exponent field (f_eq): fraction compare decides the swap
                fa = 8'd1 + st[6:0] + {1'b0, st[7], 6'd0}; a[30:23] <= fa; b[30:23] <= fa;
                if (st[8]) b[22:16] <= a[22:16];          // long common fraction prefix: deep compare
            end
            4'd5, 4'd6, 4'd7, 4'd8: begin                   // exponent distance 0..31 either way
                fa = 8'd40 + st[6:0]; fb = st[9] ? fa + {3'd0, st[14:10]} : fa - {3'd0, st[14:10]};
                a[30:23] <= fa; b[30:23] <= fb;
            end
            4'd9: begin a[30:23] <= 8'd0; b[30:23] <= st[10] ? 8'd0 : 8'd1; end           // subnormals
            4'd10: begin if (st[11]) a[30:0] <= 31'd0; else b[30:0] <= 31'd0; end           // zeros
            4'd11: begin if (st[12]) a[30:23] <= 8'hff; else b[30:23] <= 8'hfe; end         // non-finite / overflow
            4'd12: begin a[30:23] <= 8'hfe; b[30:23] <= 8'hfe; b[31] <= a[31]; end          // overflow on add
            4'd13: begin b <= {~a[31], a[30:0]}; end                                        // exact cancellation
            default: ;
        endcase
        if (vin && a[30:23] == b[30:23]) begin n_eq <= n_eq + 1; if (a[22:0] != b[22:0]) n_eqsw <= n_eqsw + 1; end
        if (vin && a[30:23] != b[30:23]) n_dist <= n_dist + 1;
        if (v4) n_val <= n_val + 1;
        if ({y4, e4, v4} !== {y4r, e4r, v4r} || {y5x, e5x, v5x} !== {y5xr, e5xr, v5xr} || {y5, e5, v5} !== {y5r, e5r, v5r}) begin
            if (mis < 5) $display("MISMATCH cyc=%0d l4 %h/%h %0d/%0d  l5x %h/%h  l5 %h/%h", cyc, y4, y4r, e4, e4r, y5x, y5xr, y5, y5r);
            mis <= mis + 1;
        end
        if (cyc == ncyc) begin
            $display("F12_SWR_MITER %s seed=%0d cycles=%0d mismatches=%0d valid_out=%0d feq_in=%0d feq_fracdiff_in=%0d dist_in=%0d",
                     (mis == 0 && n_val > ncyc / 4 && n_eqsw > ncyc / 8) ? "PASS" : "FAIL", seed, ncyc, mis, n_val, n_eq, n_eqsw, n_dist);
            $finish;
        end
    end
endmodule
