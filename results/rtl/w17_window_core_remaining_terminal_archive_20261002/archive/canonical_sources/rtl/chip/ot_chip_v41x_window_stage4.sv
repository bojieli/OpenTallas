`timescale 1ns/1ps
// Four independent packed FP8 window banks.  Absolute rows 4q+b reside in
// bank b, slot q modulo 32.  Each bank has one read and one sector-write port.
// The first register captures one row per bank; the second register rotates
// bank order into chronological attention lanes.  This two-cycle path accepts
// one four-row request every cycle once rows have been staged.
module ot_chip_v41x_window_stage4 #(
    parameter integer POS_W = 21,
    parameter integer USER_W = 10,
    parameter integer MAX_CONTEXT = 1048576
) (
    input wire clk,
    input wire rst_n,
    input wire inv_v,
    input wire [POS_W-1:0] inv_row,
    input wire fill_v,
    input wire [USER_W-1:0] fill_user,
    input wire [POS_W-1:0] fill_row,
    input wire [4:0] fill_sector,
    input wire [255:0] fill_data,
    input wire fill_last,
    input wire req_v,
    output wire req_ready,
    input wire [USER_W-1:0] req_user,
    input wire [POS_W-1:0] req_first_row,
    input wire [3:0] req_mask,
    output reg rsp_v,
    output reg [USER_W-1:0] rsp_user,
    output reg [POS_W-1:0] rsp_first_row,
    output reg [3:0] rsp_mask,
    output reg [3:0] rsp_valid_mask,
    output reg [4*4224-1:0] rsp_rows,
    output reg rsp_fault
);
    localparam integer ROWB = 4224; // 512 FP8 codes and 16 E8M0 scales
    assign req_ready = 1'b1;
    wire prefix_mask = req_mask == 4'b0001 || req_mask == 4'b0011 ||
                       req_mask == 4'b0111 || req_mask == 4'b1111;
    reg v1, bad1;
    reg [USER_W-1:0] user1;
    reg [POS_W-1:0] first1;
    reg [3:0] mask1;
    wire [ROWB-1:0] bank_data [0:3];
    wire [3:0] bank_valid;
    genvar b;
    generate for (b = 0; b < 4; b = b + 1) begin : g_bank
        reg [ROWB-1:0] mem [0:31];
        reg [POS_W-1:0] tag [0:31];
        reg [USER_W-1:0] user [0:31];
        reg [31:0] valid;
        reg [ROWB-1:0] q;
        reg q_valid;
        wire [1:0] lane = 2'(b) - req_first_row[1:0];
        wire [POS_W:0] wanted = {1'b0, req_first_row} + (POS_W+1)'(lane);
        wire [4:0] raddr = wanted[6:2];
        wire [4:0] waddr = fill_row[6:2];
        wire [4:0] iaddr = inv_row[6:2];
        wire hazard = (fill_v && fill_row[6:0] == wanted[6:0]) ||
                      (inv_v && inv_row[6:0] == wanted[6:0]);
        assign bank_data[b] = q;
        assign bank_valid[b] = q_valid;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                valid <= 0; q <= 0; q_valid <= 0;
            end else begin
                if (fill_v && fill_row[1:0] == 2'(b)) begin
                    if (fill_sector == 0) valid[waddr] <= 1'b0;
                    if (fill_sector < 5'd16)
                        mem[waddr][256*fill_sector +: 256] <= fill_data;
                    else if (fill_sector == 5'd16)
                        mem[waddr][4096 +: 128] <= fill_data[127:0];
                    if (fill_last && fill_sector == 5'd16) begin
                        tag[waddr] <= fill_row;
                        user[waddr] <= fill_user;
                        valid[waddr] <= 1'b1;
                    end
                end
                if (inv_v && inv_row[1:0] == 2'(b)) valid[iaddr] <= 1'b0;
                if (req_v) begin
                    q <= mem[raddr];
                    q_valid <= wanted < (POS_W+1)'(MAX_CONTEXT) &&
                               valid[raddr] && tag[raddr] == wanted[POS_W-1:0] &&
                               user[raddr] == req_user && !hazard;
                end
            end
        end
    end endgenerate
    wire [3:0] lane_ok;
    genvar l;
    generate for (l = 0; l < 4; l = l + 1) begin : g_lane
        wire [1:0] bank = first1[1:0] + 2'(l);
        wire [6:0] slot = 7'(first1 + POS_W'(l));
        assign lane_ok[l] = mask1[l] && bank_valid[bank] &&
                            !(inv_v && inv_row[6:0] == slot);
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                rsp_rows[l*ROWB +: ROWB] <= '0;
                rsp_valid_mask[l] <= 1'b0;
            end else begin
                rsp_rows[l*ROWB +: ROWB] <= lane_ok[l] ? bank_data[bank] : '0;
                rsp_valid_mask[l] <= lane_ok[l];
            end
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            v1 <= 0; bad1 <= 0; user1 <= 0; first1 <= 0; mask1 <= 0;
            rsp_v <= 0; rsp_user <= 0; rsp_first_row <= 0;
            rsp_mask <= 0; rsp_fault <= 0;
        end else begin
            v1 <= req_v;
            if (req_v) begin
                user1 <= req_user; first1 <= req_first_row; mask1 <= req_mask;
                bad1 <= !prefix_mask ||
                    ({1'b0, req_first_row} + (POS_W+1)'(req_mask[3] ? 3 :
                      req_mask[2] ? 2 : req_mask[1] ? 1 : 0)) >=
                    (POS_W+1)'(MAX_CONTEXT);
            end
            rsp_v <= v1;
            rsp_user <= user1; rsp_first_row <= first1; rsp_mask <= mask1;
            rsp_fault <= v1 && (bad1 || ((mask1 & ~lane_ok) != 0));
        end
    end
`ifndef SYNTHESIS
    initial if (POS_W < 21 || USER_W < 10 || MAX_CONTEXT != 1048576)
        $fatal(1, "four-bank window stage parameter contract failed");
`endif
endmodule
