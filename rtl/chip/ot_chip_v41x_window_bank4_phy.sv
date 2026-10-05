`timescale 1ns/1ps
// Physical probe for one 256-bit sector slice of each of four packed-window
// banks. The real bank has 17 such slices. Four 1R1W macros read in parallel;
// one write sector is steered to a bank each clock. Local registered checksums
// retain all read-data bits without a 1024-bit top-level output bus.
module ot_chip_v41x_window_bank4_phy (
    input wire clk,
    input wire wr_v,
    input wire [1:0] wr_bank,
    input wire [4:0] wr_slot,
    input wire [255:0] wr_sector,
    input wire [4*5-1:0] rd_slots,
    output reg [4*32-1:0] rd_digest
);
    reg wr_v_q;
    reg [1:0] wr_bank_q;
    reg [4:0] wr_slot_q;
    reg [255:0] wr_sector_q;
    reg [4*5-1:0] rd_slots_q;
    wire [255:0] q [0:3];
    always @(posedge clk) begin
        wr_v_q <= wr_v;
        wr_bank_q <= wr_bank;
        wr_slot_q <= wr_slot;
        wr_sector_q <= wr_sector;
        rd_slots_q <= rd_slots;
    end
    genvar b,g;
    generate for(b=0;b<4;b=b+1) begin : g_bank
        ot_sram_1r1w_256x256_m2_r2c2 u_mem (
            .clk(clk),.r_ce_in(1'b1),.r_addr_in({3'b0,rd_slots_q[b*5 +: 5]}),
            .rd_out(q[b]),.w_ce_in(wr_v_q && wr_bank_q==2'(b)),
            .w_addr_in({3'b0,wr_slot_q}),.wd_in(wr_sector_q),
            .w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),
            .cr_en(2'b0),.cr_sel(16'b0));
        for(g=0;g<32;g=g+1) begin : g_digest
            always @(posedge clk)
                rd_digest[(b*32)+g] <= ^q[b][g*8 +: 8];
        end
    end endgenerate
endmodule
