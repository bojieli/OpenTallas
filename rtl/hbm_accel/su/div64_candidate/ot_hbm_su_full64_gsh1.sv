`timescale 1ns/1ps
// Explicit diagnostic successor. Original full64 wrapper remains unchanged.
module ot_su64_full64_gsh1 (
    input  wire clk, input wire rst_n,
    input  wire ld, input wire ld_bank, input wire [1199:0] ld_c,
    input  wire emit, input wire bank, input wire [23:0] o_v, i_v, no, ni, input wire [3:0] ls, lvw,
    input  wire [119:0] vb, input wire [23:0] krow, obase, aibase, input wire [1:0] aind, input wire [4:0] gsh,
    input  wire cpair, input wire [1:0] dst, input wire [7:0] srcs,
    output wire vi_re, output wire [23:0] vi_addr, input wire [31:0] vi_q,
    output wire [95:0] rd_addr, output wire [3:0] rd_re, output wire [7:0] rd_src, input wire [127:0] rd_q,
    input  wire cx_arnd, cx_arelu, cx_amin, cx_cclip, input wire [31:0] cx_imm3, input wire [2:0] cp_m1,
    input  wire [31:0] cp_imm1, input wire [2:0] cm_m1, input wire [1:0] cm_m2, input wire [2:0] cm_qm,
    input  wire [31:0] cm_imm1, input wire [2:0] ca_ad, input wire [31:0] ca_imm2, input wire [2:0] ci_sfu,
    cs_sfu, cs_e1, input wire [31:0] cs_imm2, input wire [1:0] ce_e2, input wire [31:0] ce_imm1,
    input  wire co_rnd, input wire [1:0] co_dst,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll,
    output wire side_v, output wire [31:0] side_x, input wire [31:0] side_y
);
    ot_su64_lane #(.KIND(2), .LANE(0), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(64), .SIDEX(4), .CAPR(1), .GSH(1)) u (.clk(clk), .rst_n(rst_n),
        .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni),
        .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair),
        .dst(dst), .srcs(srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip),
        .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm),
        .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1),
        .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst), .vm_we(vm_we),
        .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll), .side_v(side_v), .side_x(side_x), .side_y(side_y));
endmodule
