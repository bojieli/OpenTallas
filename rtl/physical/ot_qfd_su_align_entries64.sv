`timescale 1ns/1ps
// Source-preserving operand alignment cut for actual bv_acc response paths.
// Payload delay/hold state is deliberately unreset, as in ot_hdc_delay RESET=0.
// Read masks retain the original asynchronous reset. No latency change.
module ot_qfd_su_align_group4 #(
    parameter integer ML=15, VL=7, MC=4,
    // Q-ELEM-SUC 2026-10-16 (opt-in, default 0 = unchanged): EML extra edges on the embedding answer / select and the VM
    // read masks, for a parent whose lane requests leave EML edges earlier than its VM-face pin register
    // (qfd_sp_su64_sfu PINREG: request relays RD - 1, va pin register +1).
    parameter integer EML=0
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
    ot_hdc_delay #(.W(384),.D(ML-VL)) u_vm (.clk(clk),.rst_n(rst_n),.d(vm_q),.q(vm_new));
    ot_hdc_delay #(.W(256),.D(ML-MC)) u_cr (.clk(clk),.rst_n(rst_n),.d(crom_q),.q(crom_m));
    ot_hdc_delay #(.W(132),.D(ML+EML)) u_em (.clk(clk),.rst_n(rst_n),.d({emb_sel,emb_q}),.q({emb_sel_m,emb_m}));
    ot_hdc_delay #(.W(12),.D(ML+EML),.RESET(1)) u_mk (.clk(clk),.rst_n(rst_n),.d(vm_mask),.q(mask_m));
    genvar j;
    generate for(j=0;j<12;j=j+1) begin:g_hold
        assign vm_eff[j*32+:32]=mask_m[j]?vm_new[j*32+:32]:vm_hold[j*32+:32];
    end endgenerate
    always @(posedge clk) vm_hold<=vm_eff;
endmodule

// Sixteen separate leaf clock entries. This parent contains wires only.
// Synchronizing the clocks in a functional bench proves the partition algebra;
// physical integration still requires actual phase/RC budgets for every entry.
module ot_qfd_su_align_entries64 #(
    parameter integer ML=15, VL=7, MC=4
) (
    input wire clk_g0, clk_g1, clk_g2, clk_g3, clk_g4, clk_g5, clk_g6, clk_g7, clk_g8, clk_g9, clk_g10, clk_g11, clk_g12, clk_g13, clk_g14, clk_g15,
    input wire rst_n,
    input wire [6143:0] vm_q,
    input wire [4095:0] crom_q,
    input wire [2047:0] emb_q,
    input wire [63:0] emb_sel,
    input wire [191:0] vm_mask,
    output wire [6143:0] vm_eff,
    output wire [4095:0] crom_m,
    output wire [2047:0] emb_m,
    output wire [63:0] emb_sel_m
);
    wire [15:0] clk_group={clk_g15,clk_g14,clk_g13,clk_g12,clk_g11,clk_g10,clk_g9,clk_g8,clk_g7,clk_g6,clk_g5,clk_g4,clk_g3,clk_g2,clk_g1,clk_g0};
    genvar g,o;
    generate for(g=0;g<16;g=g+1) begin:g_group
        wire [383:0] vq,ve;
        wire [11:0] mk;
        for(o=0;o<3;o=o+1) begin:g_operand
            assign vq[o*128+:128]=vm_q[o*2048+g*128+:128];
            assign mk[o*4+:4]=vm_mask[o*64+g*4+:4];
            assign vm_eff[o*2048+g*128+:128]=ve[o*128+:128];
        end
        ot_qfd_su_align_group4 #(.ML(ML),.VL(VL),.MC(MC)) u_leaf (
            .clk(clk_group[g]),.rst_n(rst_n),.vm_q(vq),.vm_mask(mk),.vm_eff(ve),
            .crom_q(crom_q[g*256+:256]),.crom_m(crom_m[g*256+:256]),
            .emb_q(emb_q[g*128+:128]),.emb_m(emb_m[g*128+:128]),
            .emb_sel(emb_sel[g*4+:4]),.emb_sel_m(emb_sel_m[g*4+:4]));
    end endgenerate
endmodule
