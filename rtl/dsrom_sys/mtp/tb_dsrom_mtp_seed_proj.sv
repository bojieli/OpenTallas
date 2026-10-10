`timescale 1ns/1ps
// Exact gate of ot_dsrom_mtp_seed_proj against the released mtp.0.main_proj golden (tools/dsrom_mtp_seed_proj.py
// writes the fixture: x.hex 15360 BF16-in-FP32 words, gold.hex 2 RP FP32 roots, goldbf.hex 2 RP BF16).
// Two tokens back to back (same activation): every row of both must match bit for bit, no fault.
module tb_dsrom_mtp_seed_proj #(parameter integer RP = 8, parameter integer MUT_JOIN = 0, parameter integer TOKENS = 2);
    reg clk = 0; always #0.416667 clk = ~clk;
    reg rst_n = 0, x_v = 0; reg [511:0] xa = 0, xb = 0;
    wire x_rdy, y_v, done, busy; wire [15:0] y_row, y_bf; wire [31:0] y_root; wire [3:0] fault;
    ot_dsrom_mtp_seed_proj #(.RP(RP), .MUT_JOIN(MUT_JOIN)) dut (.clk(clk), .rst_n(rst_n), .in_x_v(x_v),
        .in_xa_bf16(xa), .in_xb_bf16(xb), .out_x_rdy(x_rdy), .out_y_v(y_v), .out_y_row(y_row), .out_y_bf16(y_bf),
        .out_y_root(y_root), .out_done(done), .out_busy(busy), .out_fault(fault));
    reg [31:0] x [0:15359]; reg [31:0] gold [0:2*RP-1]; reg [15:0] goldbf [0:2*RP-1];
    integer seen [0:2*RP-1];
    integer cyc = 0, ny = 0, nbad = 0, tok = 0, t_first_x = 0, t_last_y = 0, t_done = 0, t_tok0 = 0, t_xend = 0, i, j;
    string dir;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n && fault != 0) begin $display("SEED_PROJ FAULT %b cyc %0d", fault, cyc); $fatal(1, "fault"); end
        if (y_v) begin
            if (y_row >= 2 * RP) $fatal(1, "row out of range %0d", y_row);
            if (y_root !== gold[y_row] || y_bf !== goldbf[y_row]) begin
                $display("SEED_PROJ MISMATCH token %0d row %0d got %h/%h want %h/%h", tok, y_row, y_root, y_bf,
                         gold[y_row], goldbf[y_row]);
                nbad <= nbad + 1;
            end
            seen[y_row] = seen[y_row] + 1; ny <= ny + 1; t_last_y <= cyc;
        end
    end
    initial begin
        if (!$value$plusargs("DATA=%s", dir)) $fatal(1, "+DATA");
        $readmemh({dir, "/x.hex"}, x); $readmemh({dir, "/gold.hex"}, gold); $readmemh({dir, "/goldbf.hex"}, goldbf);
        for (i = 0; i < 2 * RP; i = i + 1) seen[i] = 0;
        repeat (8) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        for (tok = 0; tok < TOKENS; tok = tok + 1) begin
            wait (x_rdy); @(negedge clk);
            t_tok0 = cyc; if (tok == 0) t_first_x = cyc;
            for (i = 0; i < 240; i = i + 1) begin
                x_v = 1;
                for (j = 0; j < 32; j = j + 1) begin
                    xa[16 * j +: 16] = x[i * 64 + j][31:16]; xb[16 * j +: 16] = x[i * 64 + 32 + j][31:16];
                end
                @(negedge clk);
            end
            x_v = 0; t_xend = cyc;
            wait (done); t_done = cyc; @(negedge clk);
            $display("SEED_PROJ TOKEN %0d rows=%0d first_x_to_done=%0d last_x_to_done=%0d", tok, 2 * RP, t_done - t_tok0,
                     t_done - t_xend);
        end
        repeat (16) @(negedge clk);
        for (i = 0; i < 2 * RP; i = i + 1) if (seen[i] != TOKENS) $fatal(1, "row %0d seen %0d times", i, seen[i]);
        if (nbad != 0) $fatal(1, "SEED_PROJ FAIL %0d mismatching rows", nbad);
        $display("SEED_PROJ PASS K=15360 RP=%0d rows=%0d tokens=%0d first_x_to_last_y=%0d", RP, 2 * RP, TOKENS,
                 t_last_y - t_first_x);
        $finish;
    end
    initial begin #2000000; $fatal(1, "timeout"); end
endmodule
