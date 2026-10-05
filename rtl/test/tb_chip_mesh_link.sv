`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_chip_mesh_link_tx -> ot_chip_mesh_link_rx: every flit arrives once, in
// order, with its last bit; the RX FIFO never overflows; with the receiver
// always ready the link sustains one flit per cycle (CREDITS >= round trip).
// Plusargs: +STALL=<percent of cycles the receiver is not ready>.
// Prints "PASS <flits> <cycles>" or "FAIL ...".
// ---------------------------------------------------------------------------
module tb_chip_mesh_link;
    localparam integer W = 32, ST = 3, DEPTH = 12, N = 2000;
    reg clk = 1'b0, rst_n = 1'b0;
    always #0.5 clk = ~clk;

    reg          in_valid;
    wire         in_ready;
    reg  [W-1:0] in_data;
    reg          in_last;
    wire         ch_valid, ch_last, cr_ret, out_valid, out_last, overflow;
    wire [W-1:0] ch_data, out_data;
    reg          out_ready;

    ot_chip_mesh_link_tx #(.W(W), .STAGES(ST), .CREDITS(DEPTH)) u_tx (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data),
        .in_last(in_last), .ch_valid(ch_valid), .ch_data(ch_data), .ch_last(ch_last), .cr_ret(cr_ret));
    ot_chip_mesh_link_rx #(.W(W), .IN_STAGES(ST), .RET_STAGES(ST), .DEPTH(DEPTH)) u_rx (
        .clk(clk), .rst_n(rst_n), .ch_valid(ch_valid), .ch_data(ch_data), .ch_last(ch_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
        .cr_ret(cr_ret), .overflow(overflow));

    integer stall = 0, sent = 0, got = 0, cyc = 0, bad = 0, first = -1, last_cyc = 0;
    always @(posedge clk) begin
        if (rst_n) begin
            cyc <= cyc + 1;
            // sender: the next flit whenever the link can take it
            if (in_valid && in_ready) begin
                sent <= sent + 1;
            end
            // receiver
            if (out_valid && out_ready) begin
                if (out_data !== got[W-1:0] || out_last !== (got % 7 == 6)) bad <= bad + 1;
                if (first < 0) first <= cyc;
                got <= got + 1;
                last_cyc <= cyc;
            end
            out_ready <= ($unsigned($random) % 100) >= stall;
        end
    end
    always @(*) begin
        in_valid = rst_n && sent < N;
        in_data  = sent[W-1:0];
        in_last  = (sent % 7 == 6);
    end

    initial begin
        if (!$value$plusargs("STALL=%d", stall)) stall = 0;
        out_ready = 1'b1;
        repeat (4) @(posedge clk);
        @(negedge clk) rst_n = 1'b1;   // release between edges: no reset race
        wait (got == N || cyc > 40 * N);
        @(posedge clk);
        if (got != N || bad != 0 || overflow)
            $display("FAIL got=%0d bad=%0d overflow=%0d", got, bad, overflow);
        else if (stall == 0 && (last_cyc - first + 1) != N)
            $display("FAIL rate: %0d flits in %0d cycles", N, last_cyc - first + 1);
        else
            $display("PASS %0d %0d", got, last_cyc - first + 1);
        $finish;
    end
endmodule
