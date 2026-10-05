`timescale 1ns/1ps
// DS-ROM 1M embedding row read: ot_dsrom_embed_row_reader on the real token's BF16 row (via map from
// tools/dsrom_1m_embed.py: embed.viamap.hex, expected words embed_exp.mem {idx, 16 x FP32}).  +BASE=<bank word>.
// Prints the start cycle, the first and last output cycles and the mismatch count.
module tb_dsrom_1m_embed;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    reg rst_n = 1'b0, start = 1'b0;
    reg [12:0] base;
    wire o_v, busy;
    wire [8:0] o_idx;
    wire [511:0] o_d;
    reg [511:0] exp_ [0:319];
    integer cyc = 0, n = 0, err = 0, t0 = -1, tf = -1, tl = -1, b = 0;
    ot_dsrom_embed_row_reader #(.WORDS(320), .VIAMAP("embed.viamap.hex"), .ENABLE(1)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .base(base), .o_v(o_v), .o_idx(o_idx), .o_d(o_d), .busy(busy));
    initial begin
        $readmemh("embed_exp.mem", exp_);
        if (!$value$plusargs("BASE=%d", b)) b = 0;
        base = b[12:0];
    end
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        start <= (cyc == 8);
        if (cyc == 8) t0 = cyc + 1;                     // start registered at the next edge
        if (o_v) begin
            if (o_d !== exp_[o_idx] || o_idx != n[8:0]) err = err + 1;
            if (tf < 0) tf = cyc;
            tl = cyc; n = n + 1;
        end
        if (cyc > 8 && !busy && n == 320) begin
            $display("EMB start=%0d first=%0d last=%0d words=%0d errors=%0d", t0, tf, tl, n, err);
            if (err == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
        if (cyc > 5000) begin $display("EMB timeout words=%0d", n); $display("FAIL"); $finish; end
    end
endmodule
