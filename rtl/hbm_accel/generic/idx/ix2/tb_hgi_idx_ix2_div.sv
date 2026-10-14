`timescale 1ns/1ps
// Exhaustive self-check of the ix2 keep divide path (ot_hgi_idx_ix2_kp stages 1..4) against / and %:
// (each sweep holds its last 32 values one extra cycle: 32,896 checks)
// every h = id[17:5] in 0 .. 8,191 (the whole legal input range: 13 bits) x every owner residue rank[6:5] in 0 .. 3.
module tb_hgi_idx_ix2_div #(parameter integer MUT = 0);
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0; reg [6:0] rank = 0; reg [3:0] c_v = 0; reg [415:0] c_h = 0; reg [31:0] c_f = 0;
    wire [3:0] c_cr; wire ks_v; wire [10:0] ks_ord;
    ot_hgi_idx_ix2_kp #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .start(1'b0), .rank_i(rank), .c_v(c_v), .c_h(c_h), .c_f(c_f),
        .c_cr(c_cr), .ks_v(ks_v), .ks_ord(ks_ord));
    integer h, r, p, d, bad = 0, n = 0; reg [12:0] hq [0:7][0:31]; reg [1:0] rq [0:7]; integer t = 0;
    always @(posedge clk) begin
        t <= t + 1;
        for (p = 0; p < 32; p = p + 1) hq[0][p] <= c_h[p*13 +: 13];
        rq[0] <= rank[6:5];
        for (d = 1; d < 8; d = d + 1) begin rq[d] <= rq[d-1]; for (p = 0; p < 32; p = p + 1) hq[d][p] <= hq[d-1][p]; end
        if (dut.v4[0]) for (p = 0; p < 32; p = p + 1) begin : chk
            reg [12:0] hx; hx = hq[4][p]; n = n + 1;
            if (dut.m4[p] !== ((hx % 3) == rq[0] && (hx / 3) < 1368) || dut.o4[p] !== 11'((hx / 3) & 2047)) begin
                bad = bad + 1; if (bad < 5) $display("DIV MISMATCH h=%0d m=%b o=%0d", hx, dut.m4[p], dut.o4[p]);
            end
        end
    end
    initial begin
        repeat (5) @(posedge clk); rst_n = 1; repeat (5) @(posedge clk);
        for (r = 0; r < 4; r = r + 1) begin
            rank = {r[1:0], 5'd0}; repeat (10) @(posedge clk);
            for (h = 0; h < 8192; h = h + 32) begin
                for (p = 0; p < 32; p = p + 1) c_h[p*13 +: 13] = 13'(h + p);
                c_f = 32'hFFFF_FFFF; c_v = 4'hF; @(posedge clk); #0.1;
            end
            c_v = 0; repeat (10) @(posedge clk);
        end
        // (two displays: the ?: of two string literals inside $display printed FAIL at bad = 0 under Verilator 5.050)
        if (bad == 0 && n >= 32768) $display("IX2DIV checks=%0d bad=%0d PASS", n, bad);
        else $display("IX2DIV checks=%0d bad=%0d FAIL", n, bad);
        $finish;
    end
endmodule
