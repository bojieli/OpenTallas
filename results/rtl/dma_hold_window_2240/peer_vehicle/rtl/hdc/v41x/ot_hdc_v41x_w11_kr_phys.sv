`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 OPERATOR FUSION: the N = 1,024 stream unit's lane WITH its lane register file (KR_DEPTH 32-bit
// entries; tools/w11_su_fuse.py; ot_hdc_v41x_vec_lane KR_DEPTH of ot_hdc_v41x_vec_lane_kr.sv, the fusion build of the
// lane: route it with that file in place of ot_hdc_v41x_vec_lane.sv), as fixed-parameter hardening tops beside
// ot_hdc_v41x_w11_phys.sv's lane1024r: the same broadcast-tree stage register in front of the lane, plus the
// four KR control inputs (read streams and entry at the capture, write flag and entry at OUT) in it.
//   ot_hdc_v41x_vec_light1024rk  KIND 0 (light) lane, KR_DEPTH 32
//   ot_hdc_v41x_vec_sfu1024rk    KIND 1 (SFU) lane, KR_DEPTH 32
// ---------------------------------------------------------------------------
// ot_hdc_v41x_vec_lane1024rk: one lane of the N = 1,024 unit (LN = 10, LEAF = 1) driven from a register that stands
// for the broadcast tree's stage BCAST_STAGES - 1 (the lane's own leaf register is the last stage).  At spec width the controller's per-vector fields and
// per-stage control reach 1,024 lanes over ~6 mm, so every lane (or lane group) takes them from a local
// register of the broadcast tree; the element is hardened with that register (KIND 0 light, 1 SFU).
module ot_hdc_v41x_vec_lane1024rk #(
    parameter integer KIND = 0,
    parameter integer LANE = 37,
    parameter integer MLAT = 3,         // multiplier latency (W11 serial domain: 5)
    parameter integer ALAT = 3,         // FP add latency (W11 serial domain: 4)
    parameter integer KR_DEPTH = 32     // operator fusion: lane register entries
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
    input  wire [3:0] ck_r, input wire [5:0] ck_ri, input wire co_krw, input wire [5:0] co_kwi,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll
);
    localparam integer BW = 1 + 1 + 1200 + 1 + 1 + 4 * 24 + 4 + 4 + 120 + 3 * 24 + 2 + 5 + 1 + 2 + 8
                          + 4 + 32 + 3 + 32 + 3 + 2 + 3 + 32 + 3 + 32 + 3 + 3 + 3 + 32 + 2 + 32 + 1 + 2 + 17;
    wire [BW-1:0] b_in = {ld, ld_bank, ld_c, emit, bank, o_v, i_v, no, ni, ls, lvw, vb, krow, obase, aibase, aind, gsh,
                          cpair, dst, srcs, cx_arnd, cx_arelu, cx_amin, cx_cclip, cx_imm3, cp_m1, cp_imm1, cm_m1,
                          cm_m2, cm_qm, cm_imm1, ca_ad, ca_imm2, ci_sfu, cs_sfu, cs_e1, cs_imm2, ce_e2, ce_imm1,
                          co_rnd, co_dst, ck_r, ck_ri, co_krw, co_kwi};
    reg  [BW-1:0] b_q;
    always @(posedge clk) b_q <= b_in;
    wire r_ld, r_ld_bank, r_emit, r_bank, r_cpair, r_arnd, r_arelu, r_amin, r_cclip, r_rnd;
    wire [1199:0] r_ld_c; wire [23:0] r_o_v, r_i_v, r_no, r_ni, r_krow, r_obase, r_aibase; wire [3:0] r_ls, r_lvw;
    wire [119:0] r_vb; wire [1:0] r_aind, r_dst, r_m2, r_e2, r_odst; wire [4:0] r_gsh; wire [7:0] r_srcs;
    wire [31:0] r_imm3, r_pimm1, r_mimm1, r_aimm2, r_simm2, r_eimm1;
    wire [2:0] r_pm1, r_mm1, r_qm, r_ad, r_isfu, r_ssfu, r_e1;
    wire [3:0] r_ckr; wire [5:0] r_ckri, r_kwi; wire r_krw;
    assign {r_ld, r_ld_bank, r_ld_c, r_emit, r_bank, r_o_v, r_i_v, r_no, r_ni, r_ls, r_lvw, r_vb, r_krow, r_obase,
            r_aibase, r_aind, r_gsh, r_cpair, r_dst, r_srcs, r_arnd, r_arelu, r_amin, r_cclip, r_imm3, r_pm1, r_pimm1,
            r_mm1, r_m2, r_qm, r_mimm1, r_ad, r_aimm2, r_isfu, r_ssfu, r_e1, r_simm2, r_e2, r_eimm1, r_rnd,
            r_odst, r_ckr, r_ckri, r_krw, r_kwi} = b_q;
    // the lane with LEAF = 1: its own register is the broadcast tree's last stage (claude/w11-su d734e304);
    // b_q above stands for the tree's stage BCAST_STAGES - 1
    ot_hdc_v41x_vec_lane #(.AW(24), .LN(10), .KIND(KIND), .LEAF(1), .MLAT(MLAT), .ALAT(ALAT), .KR_DEPTH(KR_DEPTH)) u (
        .clk(clk), .rst_n(rst_n), .lane_id(LANE[10:0]), .ld(r_ld), .ld_bank(r_ld_bank), .ld_c(r_ld_c), .emit(r_emit),
        .bank(r_bank), .o_v(r_o_v), .i_v(r_i_v), .no(r_no), .ni(r_ni), .ls(r_ls), .lvw(r_lvw), .vb(r_vb),
        .krow(r_krow), .obase(r_obase), .aibase(r_aibase), .aind(r_aind), .gsh(r_gsh), .cpair(r_cpair), .dst(r_dst),
        .srcs(r_srcs), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .cx_srcs(8'd0), .cx_arnd(r_arnd), .cx_arelu(r_arelu), .cx_amin(r_amin),
        .cx_cclip(r_cclip), .cx_imm3(r_imm3), .cp_m1(r_pm1), .cp_imm1(r_pimm1), .cm_m1(r_mm1), .cm_m2(r_m2),
        .cm_qm(r_qm), .cm_imm1(r_mimm1), .ca_ad(r_ad), .ca_imm2(r_aimm2), .ci_sfu(r_isfu), .cs_sfu(r_ssfu),
        .cs_e1(r_e1), .cs_imm2(r_simm2), .ce_e2(r_e2), .ce_imm1(r_eimm1), .co_rnd(r_rnd), .co_dst(r_odst),
        .ck_r(r_ckr), .ck_ri(r_ckri), .co_krw(r_krw), .co_kwi(r_kwi),
        .side_v(), .side_x(), .side_y(32'd0),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll));
endmodule

module ot_hdc_v41x_vec_light1024rk #(
    parameter integer MLAT = 3,
    parameter integer ALAT = 3,
    parameter integer KR_DEPTH = 32
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
    input  wire [3:0] ck_r, input wire [5:0] ck_ri, input wire co_krw, input wire [5:0] co_kwi,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll
);
    ot_hdc_v41x_vec_lane1024rk #(.KIND(0), .LANE(37), .MLAT(MLAT), .ALAT(ALAT), .KR_DEPTH(KR_DEPTH)) u (.*);
endmodule

module ot_hdc_v41x_vec_sfu1024rk #(
    parameter integer MLAT = 3,
    parameter integer ALAT = 3,
    parameter integer KR_DEPTH = 32
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
    input  wire [3:0] ck_r, input wire [5:0] ck_ri, input wire co_krw, input wire [5:0] co_kwi,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata, output wire kv_we,
    output wire [23:0] kv_waddr, output wire [31:0] kv_wdata, output wire ro_v, output wire [31:0] ro_x,
    output wire fault, output wire coll
);
    ot_hdc_v41x_vec_lane1024rk #(.KIND(1), .LANE(37), .MLAT(MLAT), .ALAT(ALAT), .KR_DEPTH(KR_DEPTH)) u (.*);
endmodule

