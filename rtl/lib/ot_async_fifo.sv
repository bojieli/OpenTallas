`timescale 1ns/1ps
// Dual-clock Gray-pointer FIFO.  Assertion of either interface reset flushes
// both pointer domains.  Deassertion is conditioned independently on each
// clock, followed by an online rendezvous before either interface reopens.
// DEPTH must be a power of two and at least four.  Data memory is intentionally
// not reset, because validity is carried solely by synchronized pointers.
module ot_async_fifo #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 4
) (
    input  wire             wr_clk,
    input  wire             wr_rst_n,
    input  wire             wr_valid,
    output wire             wr_ready,
    input  wire [WIDTH-1:0] wr_data,
    output reg              wr_overflow,
    input  wire             rd_clk,
    input  wire             rd_rst_n,
    output wire             rd_valid,
    input  wire             rd_ready,
    output wire [WIDTH-1:0] rd_data,
    output reg              rd_underflow
);
    initial begin
        if (DEPTH < 4 || (DEPTH & (DEPTH-1)) != 0)
            $error("ot_async_fifo DEPTH must be a power of two >= 4");
    end

    localparam integer ADDR_W = $clog2(DEPTH);
    localparam integer PTR_W = ADDR_W + 1;
    wire fifo_async_rst_n = wr_rst_n && rd_rst_n;
    wire wr_domain_rst_n;
    wire rd_domain_rst_n;
    ot_reset_sync wr_reset_conditioner (
        .clk(wr_clk), .async_rst_n(fifo_async_rst_n),
        .sync_rst_n(wr_domain_rst_n));
    ot_reset_sync rd_reset_conditioner (
        .clk(rd_clk), .async_rst_n(fifo_async_rst_n),
        .sync_rst_n(rd_domain_rst_n));

    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [PTR_W-1:0] wr_bin, wr_gray;
    reg [PTR_W-1:0] rd_bin, rd_gray;
    (* async_reg = "true" *) reg [PTR_W-1:0] rd_gray_w1, rd_gray_w2;
    (* async_reg = "true" *) reg [PTR_W-1:0] wr_gray_r1, wr_gray_r2;
    reg wr_online, rd_online;
    (* async_reg = "true" *) reg rd_online_w1, rd_online_w2;
    (* async_reg = "true" *) reg wr_online_r1, wr_online_r2;
    reg wr_full, rd_empty;
    wire wr_fire = wr_valid && wr_ready;
    wire rd_fire = rd_valid && rd_ready;
    wire [PTR_W-1:0] wr_increment = {{(PTR_W-1){1'b0}},wr_fire};
    wire [PTR_W-1:0] wr_bin_next = wr_bin + wr_increment;
    wire [PTR_W-1:0] wr_gray_next = (wr_bin_next >> 1) ^ wr_bin_next;
    wire [PTR_W-1:0] rd_increment = {{(PTR_W-1){1'b0}},rd_fire};
    wire [PTR_W-1:0] rd_bin_next = rd_bin + rd_increment;
    wire [PTR_W-1:0] rd_gray_next = (rd_bin_next >> 1) ^ rd_bin_next;
    wire wr_full_next;
    wire rd_empty_next;

    // For a binary reflected Gray pointer, full is the write pointer one lap
    // ahead of read, i.e. the synchronized read pointer with its two MSBs
    // inverted.
    assign wr_full_next = (wr_gray_next ==
                           {~rd_gray_w2[PTR_W-1:PTR_W-2],
                            rd_gray_w2[PTR_W-3:0]});
    assign rd_empty_next = (rd_gray_next == wr_gray_r2);
    assign wr_ready = wr_domain_rst_n && rd_online_w2 && !wr_full;
    assign rd_valid = rd_domain_rst_n && wr_online_r2 && !rd_empty;
    assign rd_data = mem[rd_bin[ADDR_W-1:0]];

    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n) begin
            rd_gray_w1 <= {PTR_W{1'b0}};
            rd_gray_w2 <= {PTR_W{1'b0}};
            rd_online_w1 <= 1'b0;
            rd_online_w2 <= 1'b0;
            wr_online <= 1'b0;
            wr_bin <= {PTR_W{1'b0}};
            wr_gray <= {PTR_W{1'b0}};
            wr_full <= 1'b0;
            wr_overflow <= 1'b0;
        end else begin
            wr_online <= 1'b1;
            rd_online_w1 <= rd_online;
            rd_online_w2 <= rd_online_w1;
            rd_gray_w1 <= rd_gray;
            rd_gray_w2 <= rd_gray_w1;
            // Valid may legally remain asserted while ready is low.
            if (wr_fire)
                mem[wr_bin[ADDR_W-1:0]] <= wr_data;
            wr_bin <= wr_bin_next;
            wr_gray <= wr_gray_next;
            wr_full <= wr_full_next;
        end
    end

    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n) begin
            wr_gray_r1 <= {PTR_W{1'b0}};
            wr_gray_r2 <= {PTR_W{1'b0}};
            wr_online_r1 <= 1'b0;
            wr_online_r2 <= 1'b0;
            rd_online <= 1'b0;
            rd_bin <= {PTR_W{1'b0}};
            rd_gray <= {PTR_W{1'b0}};
            rd_empty <= 1'b1;
            rd_underflow <= 1'b0;
        end else begin
            rd_online <= 1'b1;
            wr_online_r1 <= wr_online;
            wr_online_r2 <= wr_online_r1;
            wr_gray_r1 <= wr_gray;
            wr_gray_r2 <= wr_gray_r1;
            // Ready may legally remain asserted while valid is low.
            rd_bin <= rd_bin_next;
            rd_gray <= rd_gray_next;
            rd_empty <= rd_empty_next;
        end
    end

`ifndef SYNTHESIS
    // Gray pointers may only change one bit per local write/read event.
    reg [PTR_W-1:0] wr_gray_prev, rd_gray_prev;
    wire [PTR_W-1:0] wr_gray_delta = wr_gray ^ wr_gray_prev;
    wire [PTR_W-1:0] rd_gray_delta = rd_gray ^ rd_gray_prev;
    wire [PTR_W-1:0] gray_one = {{(PTR_W-1){1'b0}},1'b1};
    wire wr_gray_multi = |(wr_gray_delta & (wr_gray_delta - gray_one));
    wire rd_gray_multi = |(rd_gray_delta & (rd_gray_delta - gray_one));
    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n)
            wr_gray_prev <= {PTR_W{1'b0}};
        else begin
            if (wr_gray_multi)
                $error("ot_async_fifo write Gray pointer changed multiple bits");
            wr_gray_prev <= wr_gray;
        end
    end
    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n)
            rd_gray_prev <= {PTR_W{1'b0}};
        else begin
            if (rd_gray_multi)
                $error("ot_async_fifo read Gray pointer changed multiple bits");
            rd_gray_prev <= rd_gray;
        end
    end
`endif
endmodule
