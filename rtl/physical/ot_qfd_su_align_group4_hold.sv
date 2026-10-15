`timescale 1ns/1ps
// Exact alignment FF/mux logic; added real combinational hold padding only.
module ot_qfd_su_align_group4_hold #(
    parameter integer ML=15, VL=7, MC=4
) (
    input wire clk, rst_n,
    input wire [383:0] vm_q,
    input wire [255:0] crom_q,
    input wire [127:0] emb_q,
    input wire [3:0] emb_sel,
    input wire [11:0] vm_mask,
    output wire [383:0] vm_eff,
    output wire [255:0] crom_m,
    output wire [127:0] emb_m,
    output wire [3:0] emb_sel_m
);
    wire [383:0] vm_new;
    wire [11:0] mask_m;
    reg [383:0] vm_hold;
    ot_qfd_su_delay_hold #(.W(384),.D(ML-VL)) u_vm (.clk(clk),.rst_n(rst_n),.d(vm_q),.q(vm_new));
    ot_qfd_su_delay_hold #(.W(256),.D(ML-MC)) u_cr (.clk(clk),.rst_n(rst_n),.d(crom_q),.q(crom_m));
    ot_qfd_su_delay_hold #(.W(132),.D(ML)) u_em (.clk(clk),.rst_n(rst_n),.d({emb_sel,emb_q}),.q({emb_sel_m,emb_m}));
    ot_qfd_su_delay_hold #(.W(12),.D(ML),.RESET(1)) u_mk (.clk(clk),.rst_n(rst_n),.d(vm_mask),.q(mask_m));
    genvar j;
    generate for(j=0;j<12;j=j+1) begin:g_hold
        assign vm_eff[j*32+:32]=mask_m[j]?vm_new[j*32+:32]:vm_hold[j*32+:32];
    end endgenerate
    always @(posedge clk) vm_hold<=vm_eff;
endmodule
