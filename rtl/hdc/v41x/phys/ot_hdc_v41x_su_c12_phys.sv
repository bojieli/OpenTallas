`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): PHYSICAL VEHICLES of the c12 stream unit's hardened
// elements (fixed-parameter tops, so a route needs no -chparam), built from rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv,
// ot_hdc_v41x_vec_side_c12.sv, ot_hdc_v41x_sfu_c12.sv and rtl/hdc/ot_hdc_fastfp_lat_c12.sv at MLAT 6 / ALAT 6,
// OPR 1, DDIV 21, SIDEX 4, CAPR 1, FSQ 1.  As rtl/hdc/v41x/ot_hdc_v41x_w11_phys.sv's ot_hdc_v41x_vec_lane1024r, a lane is
// driven from one register (b_q) that stands for the broadcast tree's stage BCAST_STAGES - 1; the lane's own leaf
// register is the tree's last stage.
//   ot_su12_light  KIND 0 (lanes M .. N-1)      ot_su12_sfu  KIND 1 (lanes 1 .. M-1)
//   ot_su12_full   KIND 2 (lane 0, with the side pipe's ports)    ot_su12_side  the scalar side pipe
// Every output of the lane vehicles and of the side pipe leaves a register (rd_* / side_* / coll registered in the
// c12 lane, y / fault in the c12 side) and every input enters a register (b_q, the memory-word register (CAPR),
// the gather-word register (OPR), lane 0's side_y register (SIDEX 4), the side pipe's input registers), so the
// routes false-path the block's IO (--false-path-io), checked on the routed netlist (outcheck / incheck).
// ---------------------------------------------------------------------------
module ot_su12_lane #(
    parameter integer KIND = 0,
    parameter integer LANE = 37,
    parameter integer MLAT = 6,         // multiplier latency (W11 serial domain: 5)
    parameter integer ALAT = 6,         // FP add latency (W11 serial domain: 4)
    parameter integer OPR = 1,
    parameter integer DDIV = 21,
    parameter integer SIDEX = 4,
    parameter integer CAPR = 1,
    parameter integer GSH = 0,          // CLAUDE HBM-ABSTRACTS hub lane margin (default off): gather shift register
    parameter integer KIMM = 0,         // ... and imm3 in order-key form (rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv)
    parameter integer DENR = 0,         // views agent SFU lane fail-fast (default off): sigmoid den operand register
    parameter integer RSTPIPE = 0,
    parameter integer DRING = 0         // ... and the SFU delay lines as ring buffers
) (
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
    localparam integer BW = 1 + 1 + 1200 + 1 + 1 + 4 * 24 + 4 + 4 + 120 + 3 * 24 + 2 + 5 + 1 + 2 + 8
                          + 4 + 32 + 3 + 32 + 3 + 2 + 3 + 32 + 3 + 32 + 3 + 3 + 3 + 32 + 2 + 32 + 1 + 2;
    wire [BW-1:0] b_in = {ld, ld_bank, ld_c, emit, bank, o_v, i_v, no, ni, ls, lvw, vb, krow, obase, aibase, aind, gsh,
                          cpair, dst, srcs, cx_arnd, cx_arelu, cx_amin, cx_cclip, cx_imm3, cp_m1, cp_imm1, cm_m1,
                          cm_m2, cm_qm, cm_imm1, ca_ad, ca_imm2, ci_sfu, cs_sfu, cs_e1, cs_imm2, ce_e2, ce_imm1,
                          co_rnd, co_dst};
    reg  [BW-1:0] b_q;
    always @(posedge clk) b_q <= b_in;
    wire r_ld, r_ld_bank, r_emit, r_bank, r_cpair, r_arnd, r_arelu, r_amin, r_cclip, r_rnd;
    wire [1199:0] r_ld_c; wire [23:0] r_o_v, r_i_v, r_no, r_ni, r_krow, r_obase, r_aibase; wire [3:0] r_ls, r_lvw;
    wire [119:0] r_vb; wire [1:0] r_aind, r_dst, r_m2, r_e2, r_odst; wire [4:0] r_gsh; wire [7:0] r_srcs;
    wire [31:0] r_imm3, r_pimm1, r_mimm1, r_aimm2, r_simm2, r_eimm1;
    wire [2:0] r_pm1, r_mm1, r_qm, r_ad, r_isfu, r_ssfu, r_e1;
    assign {r_ld, r_ld_bank, r_ld_c, r_emit, r_bank, r_o_v, r_i_v, r_no, r_ni, r_ls, r_lvw, r_vb, r_krow, r_obase,
            r_aibase, r_aind, r_gsh, r_cpair, r_dst, r_srcs, r_arnd, r_arelu, r_amin, r_cclip, r_imm3, r_pm1, r_pimm1,
            r_mm1, r_m2, r_qm, r_mimm1, r_ad, r_aimm2, r_isfu, r_ssfu, r_e1, r_simm2, r_e2, r_eimm1, r_rnd,
            r_odst} = b_q;
    // the lane with LEAF = 1: its own register is the broadcast tree's last stage (claude/w11-su d734e304);
    // b_q above stands for the tree's stage BCAST_STAGES - 1
    ot_hdc_v41x_vec_lane #(.AW(24), .LN(10), .KIND(KIND), .LEAF(1), .MLAT(MLAT), .ALAT(ALAT), .OPR(OPR),
                           .DDIV(DDIV), .SIDEX(SIDEX), .CAPR(CAPR), .GSH(GSH), .KIMM(KIMM), .DENR(DENR), .DRING(DRING), .RSTPIPE(RSTPIPE)) u (
        .clk(clk), .rst_n(rst_n), .lane_id(LANE[10:0]), .ld(r_ld), .ld_bank(r_ld_bank), .ld_c(r_ld_c), .emit(r_emit),
        .bank(r_bank), .o_v(r_o_v), .i_v(r_i_v), .no(r_no), .ni(r_ni), .ls(r_ls), .lvw(r_lvw), .vb(r_vb),
        .krow(r_krow), .obase(r_obase), .aibase(r_aibase), .aind(r_aind), .gsh(r_gsh), .cpair(r_cpair), .dst(r_dst),
        .srcs(r_srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_srcs(8'd0), .cx_arnd(r_arnd), .cx_arelu(r_arelu), .cx_amin(r_amin),
        .cx_cclip(r_cclip), .cx_imm3(r_imm3), .cp_m1(r_pm1), .cp_imm1(r_pimm1), .cm_m1(r_mm1), .cm_m2(r_m2),
        .cm_qm(r_qm), .cm_imm1(r_mimm1), .ca_ad(r_ad), .ca_imm2(r_aimm2), .ci_sfu(r_isfu), .cs_sfu(r_ssfu),
        .cs_e1(r_e1), .cs_imm2(r_simm2), .ce_e2(r_e2), .ce_imm1(r_eimm1), .co_rnd(r_rnd), .co_dst(r_odst),
        .side_v(side_v), .side_x(side_x), .side_y(side_y),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll));
endmodule

module ot_su12_light #(parameter integer GSH = 0, parameter integer KIMM = 0) (
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
    ot_su12_lane #(.KIND(0), .LANE(37), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21), .SIDEX(4), .CAPR(1), .GSH(GSH), .KIMM(KIMM)) u (.clk(clk), .rst_n(rst_n),
        .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni),
        .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair),
        .dst(dst), .srcs(srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip),
        .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm),
        .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1),
        .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst), .vm_we(vm_we),
        .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll), .side_v(), .side_x(), .side_y(32'd0));
endmodule

module ot_su12_sfu #(parameter integer GSH = 0, parameter integer KIMM = 0, parameter integer DENR = 0, parameter integer DRING = 0, parameter integer RSTPIPE = 0) (
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
    ot_su12_lane #(.KIND(1), .LANE(5), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21), .SIDEX(4), .CAPR(1), .GSH(GSH), .KIMM(KIMM), .DENR(DENR), .DRING(DRING), .RSTPIPE(RSTPIPE)) u (.clk(clk), .rst_n(rst_n),
        .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni),
        .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair),
        .dst(dst), .srcs(srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip),
        .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm),
        .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1),
        .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst), .vm_we(vm_we),
        .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll), .side_v(), .side_x(), .side_y(32'd0));
endmodule

module ot_su12_full (
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
    ot_su12_lane #(.KIND(2), .LANE(0), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21), .SIDEX(4), .CAPR(1), .GSH(0), .KIMM(0)) u (.clk(clk), .rst_n(rst_n),
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

// ot_su12_full with DDIV 31 (Claude:hbm-su 2026-10-07, aggressive su_full variant): both dividers (M1 and the softplus
// gate) are rtl/hdc/v41/ot_hdc_fdiv (one quotient bit a stage, DEPTH 31) instead of the kit ot_dsrom_fdiv_f12 (DEPTH 21,
// worst class of full_u30_h25: r_rem stage +4.77 at 833).  +10 cycles on every divide (M1 DIVB/DIVIMM, SIGM/SILU,
// softplus, EGATE); the controller / side run at DDIV 31 with it.
module ot_su12_full31 (
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
    ot_su12_lane #(.KIND(2), .LANE(0), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(31), .SIDEX(4), .CAPR(1)) u (.clk(clk), .rst_n(rst_n),
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

// the scalar side pipe: v / fn / x from lane 0's registers (fn: the controller's S-in code), y to lane 0's S output
module ot_su12_side (input wire clk, rst_n, v, input wire [2:0] fn, input wire [31:0] x, input wire [2:0] fn_out,
                     output wire [31:0] y, output wire fault);
    ot_hdc_v41x_vec_side #(.MLAT(6), .ALAT(6), .DDIV(21), .SIDEX(4), .FSQ(1)) u (.*);
endmodule
