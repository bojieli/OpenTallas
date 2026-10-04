`timescale 1ns/1ps
// DS-ROM 1M head: the S81 native ordered-root terminal (rtl/test/s81_native_head_terminal/native_head_terminal.sv,
// unchanged) on one rank's full 32,320 rows at the highest rate it admits (in_valid held, logit_ready held).
// tools/dsrom_1m_head.py writes +DIR=<dir>/roots.hex: one line a row, {root4096[31:0], root1024[31:0]} in row
// order.  Prints "L <row> <logit>" per accepted logit and
// "T <first_in> <last_in> <last_logit> <done> <best_row> <best_bits> <fault> <token_valid>" (absolute cycles).
module tb_dsrom_1m_head_terminal;
    localparam integer ROWS = 32320;
    reg clk = 0;
    always #0.5 clk = ~clk;
    reg rst_n = 0, start = 0, cancel = 0, in_valid = 0, logit_ready = 1, done_ready = 0;
    reg [1:0] rank = 2'd0;
    reg [46:0] start_owner = 47'h1234, in_owner = 47'h1234;
    reg [16:0] in_row = 0;
    reg [31:0] root4096 = 0, root1024 = 0;
    wire ready, in_ready, logit_valid, logit_poison, done_valid, token_valid, fault;
    wire [46:0] logit_owner, done_owner;
    wire [16:0] logit_row, best_row;
    wire [31:0] logit_bits, best_bits;
    s81_native_head_terminal #(.OPT_NATIVE_HEAD(1), .ROWS(ROWS)) dut(.*);
    reg [63:0] roots [0:ROWS-1];
    reg [8*1024-1:0] dir;
    reg f = 0;
    integer acyc = 0, n = 0, t_first = -1, t_last_in = -1, t_last_logit = -1, t_done = -1;
    always @(posedge clk) acyc <= acyc + 1;
    always @(posedge clk) begin
        if (logit_valid && logit_ready) begin
            $display("L %0d %08h", logit_row, logit_bits);
            t_last_logit = acyc;
        end
        if (in_valid && in_ready) begin
            if (t_first < 0) t_first = acyc;
            t_last_in = acyc;
        end
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        $readmemh({dir, "/roots.hex"}, roots);
        repeat (3) @(negedge clk);
        rst_n = 1;
        @(negedge clk); start = 1;
        @(negedge clk); start = 0;
        while (n < ROWS) begin
            @(negedge clk);
            in_valid = 1; in_row = n[16:0]; {root4096, root1024} = roots[n];
            #0.25 f = in_ready;           // in_ready before the edge that fires
            @(posedge clk);
            if (f) n = n + 1;
        end
        @(negedge clk);
        in_valid = 0;
        while (!done_valid) @(posedge clk);
        t_done = acyc;
        #0.1;
        $display("T %0d %0d %0d %0d %0d %08h %0d %0d", t_first, t_last_in, t_last_logit, t_done, best_row, best_bits,
                 fault, token_valid);
        @(negedge clk); done_ready = 1; @(negedge clk); done_ready = 0;
        $finish;
    end
endmodule
