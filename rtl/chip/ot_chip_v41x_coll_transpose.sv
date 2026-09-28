`timescale 1ns/1ps
// Transpose four index-major gather ranks into rank-major VM writes.
// One accepted input beat contains ranks 0..3 for one index.  Four indices
// form a tile. On input, each rank word is stored in its destination bank
// slot, selected by VM word-address[1:0]. Each output lane is wired to one
// static bank and emits the corresponding rank-major word and address. This
// avoids a 2048-bit rotate immediately before the VM write ports. Two tiles
// permit sustained one-beat/cycle input and output; backpressure is returned
// through in_ready without dropping data.
module ot_chip_v41x_coll_transpose #(
    parameter integer WA = 19,
    parameter integer FW = 512
) (
    input  wire clk, rst_n,
    input  wire start,
    input  wire [WA-1:0] dst, n,
    output wire in_ready,
    input  wire in_valid,
    input  wire [4*FW-1:0] in_data,
    input  wire in_last,
    input  wire out_ready,
    output wire out_valid,
    output wire [3:0] out_we,
    output wire [4*WA-1:0] out_addr,
    output wire [4*FW-1:0] out_data,
    output wire out_last,
    output reg done, fault
);
    reg active, wr_sel, rd_sel;
    reg [WA-1:0] n_r, received;
    reg [WA-1:0] rank_addr [0:3];
    reg [2:0] fill [0:1];
    reg tile_ready [0:1], tile_last [0:1];
    reg [1:0] drain_rank;
    reg [FW-1:0] tile [0:1][0:3][0:3];
    reg [WA-1:0] tile_addr [0:1][0:3][0:3];
    reg [3:0] tile_mask [0:1][0:3];

    assign in_ready = active && !fault && !tile_ready[wr_sel] && received < n_r;
    wire take_in = in_valid && in_ready;
    assign out_valid = active && !fault && tile_ready[rd_sel];
    wire take_out = out_valid && out_ready;
    assign out_last = out_valid && tile_last[rd_sel] && drain_rank == 2'd3;

    genvar k, slot, rank, bank;
    // Static cell addresses avoid a dynamic 2×4×4×FW write mux. Each rank
    // address is a running counter, so the data write enable sees only two
    // address bits rather than a full-width multiply/add chain.
    generate for (slot = 0; slot < 2; slot = slot + 1) begin : g_slot
        for (rank = 0; rank < 4; rank = rank + 1) begin : g_rank
            for (bank = 0; bank < 4; bank = bank + 1) begin : g_bank
                wire wr_cell = take_in && wr_sel == 1'(slot) && rank_addr[rank][1:0] == 2'(bank);
                wire clear_cell = start || (take_out && drain_rank == 2'd3 && rd_sel == 1'(slot));
                always @(posedge clk) if (wr_cell) begin
                    tile[slot][rank][bank] <= in_data[rank*FW +: FW];
                    tile_addr[slot][rank][bank] <= rank_addr[rank];
                end
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) tile_mask[slot][rank][bank] <= 1'b0;
                    else if (clear_cell) tile_mask[slot][rank][bank] <= 1'b0;
                    else if (wr_cell) tile_mask[slot][rank][bank] <= 1'b1;
            end
        end
    end endgenerate

    generate for (k = 0; k < 4; k = k + 1) begin : g_lane
        assign out_we[k] = take_out && tile_mask[rd_sel][drain_rank][k];
        assign out_addr[k*WA +: WA] = tile_addr[rd_sel][drain_rank][k];
        assign out_data[k*FW +: FW] = tile[rd_sel][drain_rank][k];
    end endgenerate

    integer r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; wr_sel <= 1'b0; rd_sel <= 1'b0;
            n_r <= 0; received <= 0; drain_rank <= 0;
            for (r = 0; r < 4; r = r + 1) rank_addr[r] <= 0;
            fill[0] <= 0; fill[1] <= 0;
            tile_ready[0] <= 0; tile_ready[1] <= 0;
            tile_last[0] <= 0; tile_last[1] <= 0;
            done <= 0; fault <= 0;
        end else begin
            done <= 0;
            if (start) begin
                if (active || n == 0) fault <= 1;
                else begin
                    active <= 1; n_r <= n; received <= 0;
                    rank_addr[0] <= dst;
                    rank_addr[1] <= dst + n;
                    rank_addr[2] <= dst + (n << 1);
                    rank_addr[3] <= dst + (n << 1) + n;
                    wr_sel <= 0; rd_sel <= 0; drain_rank <= 0;
                    fill[0] <= 0; fill[1] <= 0;
                    tile_ready[0] <= 0; tile_ready[1] <= 0;
                    tile_last[0] <= 0; tile_last[1] <= 0;
                end
            end else if (active) begin
                if (take_in) begin
                    for (r = 0; r < 4; r = r + 1)
                        rank_addr[r] <= rank_addr[r] + 1'b1;
                    received <= received + 1'b1;
                    if (in_last != (received == n_r - 1'b1)) fault <= 1;
                    if (fill[wr_sel] == 3 || in_last) begin
                        tile_last[wr_sel] <= in_last;
                        tile_ready[wr_sel] <= 1;
                        wr_sel <= ~wr_sel;
                    end else fill[wr_sel] <= fill[wr_sel] + 1'b1;
                end
                if (take_out) begin
                    if (drain_rank == 2'd3) begin
                        tile_ready[rd_sel] <= 0;
                        fill[rd_sel] <= 0;
                        rd_sel <= ~rd_sel;
                        drain_rank <= 0;
                        if (tile_last[rd_sel]) begin active <= 0; done <= 1; end
                    end else drain_rank <= drain_rank + 1'b1;
                end
            end
        end
    end
`ifndef SYNTHESIS
    integer i, j;
    always @(posedge clk) if (rst_n && take_out) begin
        for (i = 0; i < 4; i = i + 1)
            for (j = i + 1; j < 4; j = j + 1)
                if (out_we[i] && out_we[j] &&
                    out_addr[i*WA +: 2] == out_addr[j*WA +: 2])
                    $fatal(1, "collective transpose VM bank collision");
        for (i = 0; i < 4; i = i + 1)
            if (out_we[i] && out_addr[i*WA +: 2] != 2'(i))
                $fatal(1, "collective transpose output lane is not its static VM bank");
    end
`endif
endmodule
