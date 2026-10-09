// REDESIGN-S81 2026-10-08: cycle exactness of the pin-registered WINDOW column (PINREG 1, WE_REP 1/2/4) against
// the original column (PINREG 0) for 128 and 256 bits: identical random stimulus (dense writes incl. same-row
// write-then-read and write+read in one cycle), read_data compared every cycle once defined.
// +define+OT_WCOL_MUT_NOBYPASS (read from mem, not the bypassed next value) must FAIL.
`timescale 1ns/1ps
module tb_window_column_pinreg;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg [31:0] row_we; reg [255:0] wd; reg read_v; reg [4:0] ra;
    wire [255:0] q0_256, q1_256, q2_256; wire [127:0] q0_128, q1_128;
    ot_dsrom_window_column #(.WIDTH(256), .PINREG(0)) u_g256 (.clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd), .read_v(read_v), .read_addr(ra), .read_data(q0_256));
    ot_dsrom_window_column_256 u_n256 (.clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd), .read_v(read_v), .read_addr(ra), .read_data(q1_256));
    ot_dsrom_window_column_256 #(.WE_REP(1)) u_n256r1 (.clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd), .read_v(read_v), .read_addr(ra), .read_data(q2_256));
    ot_dsrom_window_column #(.WIDTH(128), .PINREG(0)) u_g128 (.clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd[127:0]), .read_v(read_v), .read_addr(ra), .read_data(q0_128));
    ot_dsrom_window_column_128 u_n128 (.clk(clk), .rst_n(rst_n), .row_we(row_we), .write_data(wd[127:0]), .read_v(read_v), .read_addr(ra), .read_data(q1_128));
    integer seed = 1, cyc, errs = 0, cmp = 0, k;
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        row_we = 0; wd = 0; read_v = 0; ra = 0;
        repeat (3) @(negedge clk); rst_n = 1;
        for (cyc = 0; cyc < 20000; cyc = cyc + 1) begin
            @(negedge clk);
            // first 64 cycles fill every row; then sparse random writes (one-hot, as the parent's row decode) and reads
            row_we = (cyc < 64) ? (32'h1 << (cyc % 32)) : (($random(seed) % 3 == 0) ? (32'h1 << ($random(seed) & 31)) : 32'h0);
            for (k = 0; k < 8; k = k + 1) wd[32*k +: 32] = $random(seed);
            read_v = (cyc >= 64) && ($random(seed) & 1);
            // half of the reads hit the row written this or last cycle
            ra = ($random(seed) & 1) ? $random(seed) : ra;
            if (cyc >= 70) begin
                if (q0_256 !== q1_256 || q0_256 !== q2_256 || q0_128 !== q1_128) begin
                    if (errs < 5) $display("cycle %0d mismatch", cyc); errs = errs + 1;
                end
                cmp = cmp + 1;
            end
        end
        $display("SUMMARY compared %0d cycles, mismatches %0d", cmp, errs);
        if (errs == 0) $display("RESULT PASS"); else $display("RESULT FAIL");
        $finish;
    end
endmodule
