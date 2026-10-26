`timescale 1ns/1ps
// Fixed 24-row token calendar. One actual hash-row ID per edge; no ready/credits.
// Outputs one registered HBM request descriptor per input slot. HBM return service
// and native ROW_GATHER are separate interfaces and must reserve their own slots.
module ot_hbm_engram_home_dispatch #(
    parameter integer MUTANT_RANK = 0
)(
    input wire clk, rst_n,
    input wire start,
    input wire layer_index,
    input wire row_valid,
    input wire [28:0] row_id,
    output reg request_valid,
    output reg [6:0] request_rank,
    output reg [36:0] request_address,
    output reg [25:0] request_local_row,
    output reg [4:0] request_staging_slot,
    output reg [19:0] gather_slot_id,
    output reg [4:0] request_list_index,
    output reg done,
    output reg fault
);
    reg active, li;
    reg [4:0] index;
    reg [4:0] count [0:7];
    wire [28:0] nrows = li ? 29'd384016682 : 29'd384006168;
    wire [25:0] rph = li ? 26'd48002086 : 26'd48000771;
    reg [2:0] home;
    reg [28:0] first;
    reg [25:0] local_row;
    reg [6:0] rank;
    reg [19:0] slot_id;
    integer h;
    always @* begin
        home = 0;
        // Constant bounds: no large divider or dynamic address table.
        for (integer k = 1; k < 8; k = k + 1)
            if (row_id >= (k * rph)) home = k;
        first = home * rph;
        local_row = row_id - first;
        rank = (li ? 7'd8 : 7'd0) + home + MUTANT_RANK;
        slot_id = (count[home] / 8) * 768 + rank * 8 + count[home] % 8;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 0; li <= 0; index <= 0; request_valid <= 0;
            done <= 0; fault <= 0;
            for (h = 0; h < 8; h = h + 1) count[h] <= 0;
            request_rank <= 0; request_address <= 0; request_local_row <= 0;
            request_staging_slot <= 0; gather_slot_id <= 0; request_list_index <= 0;
        end else begin
            request_valid <= 0; done <= 0;
            if (start) begin
                if (active || row_valid) fault <= 1;
                active <= 1; li <= layer_index; index <= 0;
                for (h = 0; h < 8; h = h + 1) count[h] <= 0;
            end else if (active) begin
                // Missing/invalid slot faults rather than extending the calendar.
                if (!row_valid || row_id >= nrows) fault <= 1;
                if (row_valid && row_id < nrows) begin
                    request_valid <= 1;
                    request_rank <= rank;
                    request_local_row <= local_row;
                    request_address <= 37'd103079215104 + (37'(local_row) * 37'd288);
                    request_staging_slot <= count[home];
                    gather_slot_id <= slot_id;
                    request_list_index <= index;
                    count[home] <= count[home] + 1'b1;
                end
                if (index == 23) begin active <= 0; done <= 1; end
                else index <= index + 1'b1;
            end else if (row_valid) fault <= 1;
        end
    end
endmodule
