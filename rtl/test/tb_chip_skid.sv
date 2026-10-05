`timescale 1ns/1ps
// ot_chip_skid: every beat passes once, in order, under random source gaps and
// sink stalls; with both sides always ready it moves one beat per cycle.
// Plusargs: +STALL=<sink stall %> +GAP=<source gap %>.  Prints PASS/FAIL.
module tb_chip_skid;
    localparam integer W = 16, N = 3000;
    reg clk = 1'b0, rst_n = 1'b0;
    always #0.5 clk = ~clk;
    reg in_valid = 1'b0, out_ready = 1'b1;
    reg [W-1:0] in_data = 0;
    wire in_ready, out_valid;
    wire [W-1:0] out_data;
    ot_chip_skid #(.W(W)) dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
        .in_data(in_data), .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data));
    integer stall = 0, gap = 0, sent = 0, got = 0, bad = 0, cyc = 0, first = -1, last = 0;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if (in_valid && in_ready) sent <= sent + 1;
        if (out_valid && out_ready) begin
            if (out_data !== got[W-1:0]) bad <= bad + 1;
            if (first < 0) first <= cyc;
            got <= got + 1; last <= cyc;
        end
        out_ready <= ($unsigned($random) % 100) >= stall;
    end
    // the source holds a beat until it is taken
    always @(posedge clk) if (rst_n) begin
        if (!in_valid || in_ready) begin
            if (in_valid && in_ready) in_data <= in_data + 1'b1;
            in_valid <= (sent + (in_valid && in_ready) < N) && (($unsigned($random) % 100) >= gap);
        end
    end
    initial begin
        if (!$value$plusargs("STALL=%d", stall)) stall = 0;
        if (!$value$plusargs("GAP=%d", gap)) gap = 0;
        repeat (3) @(posedge clk);
        @(negedge clk) rst_n = 1'b1;
        wait (got == N || cyc > 50 * N);
        @(posedge clk);
        if (got != N || bad != 0) $display("FAIL got=%0d bad=%0d", got, bad);
        else if (stall == 0 && gap == 0 && last - first + 1 != N) $display("FAIL rate %0d", last - first + 1);
        else $display("PASS %0d %0d", got, last - first + 1);
        $finish;
    end
endmodule
