`timescale 1ns/1ps
// Latency and integrity testbench for ot_rom_pkg_link.
//
// Sends messages of 1, 6 (one user's 10,240-byte BF16 hidden state at 1,800 B
// per flit) and 364 flits (64 users) with a free-running receiver, then the
// 364-flit message against random receiver back-pressure.  Every flit carries
// its message and sequence number, so loss, duplication or reordering is a
// scoreboard error.  Prints one CASE line per message.
module tb_rom_pkg_link;
    localparam integer FLIT_BYTES = 1800, TX = 2, CH = 60, RX = 2, CREDITS = 128;
    localparam integer W = FLIT_BYTES * 8;
    reg clk = 0, rst_n = 0;
    reg in_valid = 0, in_last = 0, out_ready = 1;
    reg [W-1:0] in_data = 0;
    wire in_ready, out_valid, out_last;
    wire [W-1:0] out_data;
    wire [31:0] credit_stalls;

    ot_rom_pkg_link #(.FLIT_BYTES(FLIT_BYTES), .TX_STAGES(TX), .CHANNEL_CYCLES(CH),
                      .RX_STAGES(RX), .CREDITS(CREDITS)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
        .in_data(in_data), .in_last(in_last), .out_valid(out_valid), .out_ready(out_ready),
        .out_data(out_data), .out_last(out_last), .credit_stalls(credit_stalls));

    always #0.5 clk = ~clk;     // 1 GHz

    integer cycle = 0;
    always @(posedge clk) cycle <= cycle + 1;

    integer errors = 0, total_errors = 0, seed = 7;
    integer rx_count, first_rx, last_rx, sent_start;
    reg backpressure = 0;

    // Receiver: scoreboard each flit as it drains.
    integer expect_msg, expect_seq;
    always @(posedge clk) begin
        if (backpressure) out_ready <= ($random(seed) & 3) != 0;
        else out_ready <= 1'b1;
    end
    always @(posedge clk) if (out_valid && out_ready) begin
        if (out_data[31:0] !== expect_msg || out_data[63:32] !== expect_seq
            || out_data[W-1:W-32] !== (expect_msg ^ expect_seq ^ 32'hA5A5_5A5A)) errors = errors + 1;
        if (rx_count == 0) first_rx = cycle;
        last_rx = cycle;
        rx_count = rx_count + 1;
        expect_seq = expect_seq + 1;
    end

    task automatic send_message(input integer msg, input integer flits, input [127:0] label);
        integer s;
        begin
            errors = 0; rx_count = 0; expect_msg = msg; expect_seq = 0;
            @(negedge clk);
            sent_start = cycle + 1;
            s = 0;
            while (s < flits) begin
                in_valid = 1;
                in_data = 0;
                in_data[31:0] = msg;
                in_data[63:32] = s;
                in_data[W-1:W-32] = msg ^ s ^ 32'hA5A5_5A5A;
                in_last = (s == flits - 1);
                @(posedge clk);
                if (in_ready) s = s + 1;
                @(negedge clk);
            end
            in_valid = 0; in_last = 0;
            while (rx_count < flits) @(posedge clk);
            @(posedge clk);
            if (rx_count != flits) errors = errors + 1;
            total_errors = total_errors + errors;
            $display("CASE label=%0s flits=%0d first_latency=%0d last_latency=%0d stalls=%0d errors=%0d",
                     label, flits, first_rx - sent_start, last_rx - sent_start, credit_stalls, errors);
            repeat (4) @(posedge clk);
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        rst_n = 1;
        repeat (2) @(posedge clk);
        send_message(1, 1, "one_flit");
        send_message(2, 6, "one_user");
        send_message(3, 364, "sixty_four_users");
        backpressure = 1;
        send_message(4, 364, "backpressure");
        backpressure = 0;
        $display("SUMMARY errors=%0d", total_errors);
        $finish;
    end
    initial begin #2000000; $display("SUMMARY errors=timeout"); $finish; end
endmodule
