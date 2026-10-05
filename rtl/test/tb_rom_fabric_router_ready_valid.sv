`timescale 1ns/1ps
// Saturate the router input while a ready/valid sender holds its head flit.
// Count accepted flits at both interfaces to check order and conservation.
module tb_rom_fabric_router_ready_valid;
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    integer cycle = 0, sent = 0, received = 0, stalled = 0;
    wire [1:0] in_valid = {1'b0, (sent < 6)};
    wire [1:0] in_ready, in_credit;
    wire [63:0] data0 = {48'd0, sent[7:0], 8'd0};
    wire [127:0] in_data = {64'd0, data0};
    wire [1:0] in_last = {1'b0, (sent == 5)};
    wire [1:0] out_valid, out_last;
    wire [1:0] out_ready = {1'b1, (cycle >= 15)};
    wire [127:0] out_data;
    wire [31:0] drops;
    wire overflow;

    ot_rom_fabric_router #(.NP(2), .FW(64), .BUF(2), .DESTS(2),
                           .INPUT_READY_VALID(1), .ROUTE_INIT(4'b0001)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
        .in_credit(in_credit), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data),
        .out_last(out_last), .cfg_we(1'b0), .cfg_dest(8'd0), .cfg_mask(2'b00),
        .drops(drops), .overflow(overflow));

    always @(posedge clk) begin
        cycle <= cycle + 1;
        if (cycle == 2) rst_n <= 1'b1;
        if (rst_n) begin
            if (in_valid[0] && in_ready[0]) sent <= sent + 1;
            if (in_valid[0] && !in_ready[0]) stalled <= stalled + 1;
            if (out_valid[0] && out_ready[0]) begin
                if (received >= 6 || out_data[15:8] !== received[7:0] ||
                    out_last[0] !== (received == 5))
                    $fatal(1, "flit order/data/last mismatch at receive %0d", received);
                received <= received + 1;
            end
            if (out_valid[1]) $fatal(1, "unexpected output port 1 flit");
            if (overflow || drops != 0) $fatal(1, "overflow=%0d drops=%0d", overflow, drops);
            if (sent == 6 && received == 6) begin
                if (stalled == 0) $fatal(1, "input never saturated");
                $display("ROUTER_READY_VALID sent=%0d received=%0d stalled=%0d overflow=%0d drops=%0d",
                         sent, received, stalled, overflow, drops);
                $display("PASS");
                $finish;
            end
            if (cycle > 100) $fatal(1, "timeout sent=%0d received=%0d", sent, received);
        end
    end
endmodule
