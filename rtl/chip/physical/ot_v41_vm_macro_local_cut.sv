`timescale 1ns/1ps
// One actual 128-bit column of ot_v41_vm_bank4_macro_pipe, isolated for
// SRAM-pin/first-flop physical characterization. The command, local-write,
// macro and read-capture edges match that module; no service stage is added.
module ot_v41_vm_macro_local_cut #(
    parameter integer GROUP=0
) (
    input wire clk,
    input wire rst_n,
    input wire rd_v,
    input wire [3:0] rd_group,
    input wire [8:0] rd_row,
    input wire wr_v,
    input wire [3:0] wr_group,
    input wire [8:0] wr_row,
    input wire [127:0] wr_data,
    input wire [127:0] wr_mask,
    output reg [127:0] rd_capture,
    output reg rd_capture_v
);
    reg rd_v_q,wr_v_q;
    reg [3:0] rd_group_q,wr_group_q;
    reg [8:0] rd_row_q,wr_row_q;
    reg [127:0] wr_data_q,wr_mask_q;
    reg wr_local_en_q;
    reg [8:0] wr_local_row_q;
    reg [127:0] wr_local_data_q,wr_local_mask_q;
    reg rd_mem_v_q;
    wire [127:0] macro_q;
    wire rd_hit = rd_v_q && rd_group_q == GROUP;
    wire wr_hit = wr_v_q && wr_group_q == GROUP;

    always @(posedge clk) begin
        if (!rst_n) begin
            rd_v_q<=0; wr_v_q<=0;
            rd_group_q<=0; wr_group_q<=0;
            rd_row_q<=0; wr_row_q<=0;
            wr_data_q<=0; wr_mask_q<=0;
            wr_local_en_q<=0; wr_local_row_q<=0;
            wr_local_data_q<=0; wr_local_mask_q<=0;
            rd_mem_v_q<=0; rd_capture_v<=0;
        end else begin
            rd_v_q<=rd_v; wr_v_q<=wr_v;
            rd_group_q<=rd_group; wr_group_q<=wr_group;
            rd_row_q<=rd_row; wr_row_q<=wr_row;
            wr_data_q<=wr_data; wr_mask_q<=wr_mask;
            wr_local_en_q<=wr_hit;
            if (wr_hit) begin
                wr_local_row_q<=wr_row_q;
                wr_local_data_q<=wr_data_q;
                wr_local_mask_q<=wr_mask_q;
            end
            rd_mem_v_q<=rd_hit;
            rd_capture_v<=rd_mem_v_q;
        end
        rd_capture<=macro_q;
    end

    ot_sram_1r1w_512x128_m4_r2c2 u_sram (
        .clk(clk),.r_ce_in(rd_hit),.r_addr_in(rd_row_q),.rd_out(macro_q),
        .w_ce_in(wr_local_en_q),.w_addr_in(wr_local_row_q),
        .wd_in(wr_local_data_q),.w_mask_in(wr_local_mask_q),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0)
    );
endmodule
