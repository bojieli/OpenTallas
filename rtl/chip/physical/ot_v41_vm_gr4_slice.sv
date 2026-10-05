`timescale 1ns/1ps
// Four-bank read reorder for one BW-bit slice of four consecutive VM words.
// Bank data is registered locally, then rotated into increasing word order.
// The bank-address issue and SRAM one-cycle read are outside this slice.
module ot_v41_vm_gr4_slice #(
    parameter integer A = 15,
    parameter integer BW = 128
) (
    input wire clk,
    input wire [1:0] first_bank,
    input wire in_v,
    input wire [4*BW-1:0] bank_data,
    output reg out_v,
    output reg [4*BW-1:0] out_data
);
    reg [4*BW-1:0] bank_q;
    reg valid_q;
    (* keep = "true" *) reg [1:0] select_q [0:3][0:BW/16-1];
    genvar l,g;
    always @(posedge clk) begin
        bank_q <= bank_data;
        valid_q <= in_v;
        out_v <= valid_q;
    end
    generate for (l=0; l<4; l=l+1) begin: g_lane
        for (g=0; g<BW/16; g=g+1) begin: g_group
            // Diversify local encoded controls so synthesis cannot collapse
            // every group onto one high-fanout select flop.
            wire [1:0] bank = select_q[l][g] ^ 2'(g);
            always @(posedge clk) begin
                select_q[l][g] <= (first_bank + 2'(l)) ^ 2'(g);
                case (bank)
                    2'd0: out_data[l*BW+g*16 +: 16] <= bank_q[0*BW+g*16 +: 16];
                    2'd1: out_data[l*BW+g*16 +: 16] <= bank_q[1*BW+g*16 +: 16];
                    2'd2: out_data[l*BW+g*16 +: 16] <= bank_q[2*BW+g*16 +: 16];
                    2'd3: out_data[l*BW+g*16 +: 16] <= bank_q[3*BW+g*16 +: 16];
                endcase
            end
        end
    end endgenerate
endmodule
