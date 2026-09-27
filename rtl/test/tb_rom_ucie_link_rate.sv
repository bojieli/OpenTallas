`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Rate regression of ot_rom_ucie_link (rtl/rom/ot_rom_oneshot_allreduce.sv).
//
// A saturating sender offers a record every cycle for CYCLES cycles.  The link
// must accept records at its byte rate, BPC_NUM / BPC_DEN bytes per cycle for
// FLIT_BYTES per record, INCLUDING a fractional cycles-per-record: 512-byte
// records at 157.58 B/cycle (the V4.1 T1 board link) are 3.249 cycles each, and
// a bucket that dropped the remainder would run them at 4.  Every accepted
// record must leave the far end exactly LAT cycles later, in order, and a
// credit must cross in LAT cycles too.  Prints one RATE line; the test
// (tests/test_rom_ucie_link_rate.py) checks the counts.
// ---------------------------------------------------------------------------
module tb_rom_ucie_link_rate #(
    parameter integer LAT        = 142,
    parameter integer FLIT_BYTES = 512,
    parameter integer BPC_NUM    = 15758,
    parameter integer BPC_DEN    = 100,
    parameter integer CYCLES     = 20000
);
    localparam integer PW = 32;
    reg clk = 1'b0;
    always #1 clk = ~clk;
    reg rst_n = 1'b0;
    integer cyc = 0, sent = 0, recv = 0, bad = 0, first_send = -1, first_recv = -1, cr_sent = -1, cr_seen = -1;
    wire in_ready, out_valid, cr_out;
    wire [PW-1:0] out_rec;
    reg  in_valid = 1'b0;
    reg  cr_in = 1'b0;
    ot_rom_ucie_link #(.PW(PW), .LAT(LAT), .FLIT_BYTES(FLIT_BYTES), .BPC_NUM(BPC_NUM), .BPC_DEN(BPC_DEN)) u_link (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_rec(sent), .in_ready(in_ready),
        .out_valid(out_valid), .out_rec(out_rec), .cr_in(cr_in), .cr_out(cr_out));
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if (in_valid && in_ready) begin
            if (first_send < 0) first_send <= cyc;
            sent <= sent + 1;
        end
        if (out_valid) begin
            if (first_recv < 0) first_recv <= cyc;
            if (out_rec !== recv) bad <= bad + 1;
            recv <= recv + 1;
        end
        cr_in <= (cyc == 100);
        if (cr_in && cr_sent < 0) cr_sent <= cyc;
        if (cr_out && cr_seen < 0) cr_seen <= cyc;
    end
    initial begin
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        @(negedge clk);
        in_valid = 1'b1;
        repeat (CYCLES) @(posedge clk);
        @(negedge clk);
        in_valid = 1'b0;
        repeat (LAT + 4) @(posedge clk);
        $display("RATE cycles=%0d sent=%0d recv=%0d bad=%0d lat=%0d cr_lat=%0d", CYCLES, sent, recv, bad,
                 first_recv - first_send, cr_seen - cr_sent);
        $finish;
    end
endmodule
