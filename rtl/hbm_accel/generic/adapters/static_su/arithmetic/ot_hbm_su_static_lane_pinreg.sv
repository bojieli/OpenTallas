`timescale 1ns/1ps
`default_nettype none
// Pin-registered static SU lane (OWNER 2026-10-15 19:50: every new tile registers every input and output at its pin;
// the SU schedule absorbs the cycles). Every input except the clocks and reset is sampled by one register at the pin
// (clk_stage[0], the lane's command root); every output leaves through one register (fetch side on clk_stage[0],
// write / reducer side on clk_stage[7], the roots that drive them inside the lane). The wrapped lane is unchanged
// except FETCH_EXTRA_EDGES + 2 (store / gather address out +1, data in +1). Net effect at the parent (measured,
// tb_su_static_lane_leaf PINREG=1): store / RF-stream requests leave 2 edges later than before (command +1, address
// register +1) and lane writes / reducer operands 4 edges later (command +1, round trip +2, output +1):
// su_top_compile --pin-reg. Valid / fault bits are reset,
// data bits are not. The FULL lane's scalar SIDE loop (side_x -> side pipe -> side_y at S out) is a fixed-depth
// in-slice loop with no lane-side slack, so KIND 2 keeps its side pins combinational (side pipe sits beside it).
module ot_hbm_su_static_lane_pinreg #(
    parameter integer FETCH_EXTRA_EDGES = 2, AW = 24, CW = 24, LN = 3, KIND = 0, KVT_SH = 9, LEAF = 0,
    parameter integer MLAT = 3, ALAT = 3
) (
    input wire [7:0] clk_stage,
    input wire [3:0] clk_insert,
    input wire rst_n,
    input wire [10:0] lane_id,
    input wire ld, ld_bank,
    input wire [5*LN*AW-1:0] ld_c,
    input wire emit, bank,
    input wire [CW-1:0] o_v, i_v, no, ni,
    input wire [3:0] ls, lvw,
    input wire [5*AW-1:0] vb,
    input wire [AW-1:0] krow, obase, aibase,
    input wire [1:0] aind,
    input wire [4:0] gsh,
    input wire cpair,
    input wire [1:0] dst,
    input wire [7:0] srcs,
    output wire vi_re,
    output wire [AW-1:0] vi_addr,
    input wire [31:0] vi_q,
    output wire [4*AW-1:0] rd_addr,
    output wire [3:0] rd_re,
    output wire [7:0] rd_src,
    input wire [4*32-1:0] rd_q,
    input wire [7:0] cx_srcs,
    input wire cx_arnd, cx_arelu, cx_amin, cx_cclip,
    input wire [31:0] cx_imm3,
    input wire [2:0] cp_m1,
    input wire [31:0] cp_imm1,
    input wire [2:0] cm_m1,
    input wire [1:0] cm_m2,
    input wire [2:0] cm_qm,
    input wire [31:0] cm_imm1,
    input wire [2:0] ca_ad,
    input wire [31:0] ca_imm2,
    input wire [2:0] ci_sfu, cs_sfu, cs_e1,
    input wire [31:0] cs_imm2,
    input wire [1:0] ce_e2,
    input wire [31:0] ce_imm1,
    input wire co_rnd,
    input wire [1:0] co_dst,
    output wire side_v,
    output wire [31:0] side_x,
    input wire [31:0] side_y,
    output wire vm_we,
    output wire [AW-1:0] vm_waddr,
    output wire [31:0] vm_wdata,
    output wire kv_we,
    output wire [AW-1:0] kv_waddr,
    output wire [31:0] kv_wdata,
    output wire ro_v,
    output wire [31:0] ro_x,
    output wire fault,
    output wire coll
);
    /* verilator hier_block */
    wire c0 = clk_stage[0], c7 = clk_stage[7];
    // ---- input pin registers (command root): control strobes reset, data not
    localparam integer DW = 11 + 5*LN*AW + 4*CW + 8 + 5*AW + 3*AW + 2 + 5 + 1 + 2 + 8 + 32 + 128 + 8 + 4 + 32
                            + 3 + 32 + 3 + 2 + 3 + 32 + 3 + 32 + 3*3 + 32 + 2 + 32 + 1 + 2 + 32;
    wire [DW-1:0] d_in = {lane_id, ld_c, o_v, i_v, no, ni, ls, lvw, vb, krow, obase, aibase, aind, gsh, cpair, dst, srcs,
                          vi_q, rd_q, cx_srcs, cx_arnd, cx_arelu, cx_amin, cx_cclip, cx_imm3, cp_m1, cp_imm1, cm_m1,
                          cm_m2, cm_qm, cm_imm1, ca_ad, ca_imm2, ci_sfu, cs_sfu, cs_e1, cs_imm2, ce_e2, ce_imm1, co_rnd,
                          co_dst, (KIND == 2) ? 32'd0 : side_y};
    reg [DW-1:0] d_q;
    reg [3:0] s_q;                                   // ld, ld_bank, emit, bank
    always @(posedge c0) d_q <= d_in;
    always @(posedge c0 or negedge rst_n) if (!rst_n) s_q <= 4'd0; else s_q <= {ld, ld_bank, emit, bank};
    wire [10:0] q_lane_id; wire [5*LN*AW-1:0] q_ld_c; wire [CW-1:0] q_o_v, q_i_v, q_no, q_ni; wire [3:0] q_ls, q_lvw;
    wire [5*AW-1:0] q_vb; wire [AW-1:0] q_krow, q_obase, q_aibase; wire [1:0] q_aind, q_dst; wire [4:0] q_gsh;
    wire q_cpair; wire [7:0] q_srcs, q_cx_srcs; wire [31:0] q_vi_q; wire [127:0] q_rd_q;
    wire q_cx_arnd, q_cx_arelu, q_cx_amin, q_cx_cclip, q_co_rnd; wire [31:0] q_cx_imm3, q_cp_imm1, q_cm_imm1, q_ca_imm2,
    q_cs_imm2, q_ce_imm1, q_side_y; wire [2:0] q_cp_m1, q_cm_m1, q_cm_qm, q_ca_ad, q_ci_sfu, q_cs_sfu, q_cs_e1;
    wire [1:0] q_cm_m2, q_ce_e2, q_co_dst;
    assign {q_lane_id, q_ld_c, q_o_v, q_i_v, q_no, q_ni, q_ls, q_lvw, q_vb, q_krow, q_obase, q_aibase, q_aind, q_gsh,
            q_cpair, q_dst, q_srcs, q_vi_q, q_rd_q, q_cx_srcs, q_cx_arnd, q_cx_arelu, q_cx_amin, q_cx_cclip, q_cx_imm3,
            q_cp_m1, q_cp_imm1, q_cm_m1, q_cm_m2, q_cm_qm, q_cm_imm1, q_ca_ad, q_ca_imm2, q_ci_sfu, q_cs_sfu, q_cs_e1,
            q_cs_imm2, q_ce_e2, q_ce_imm1, q_co_rnd, q_co_dst, q_side_y} = d_q;
    // ---- the unchanged lane
    wire l_vi_re, l_vm_we, l_kv_we, l_ro_v, l_fault, l_coll, l_side_v;
    wire [AW-1:0] l_vi_addr, l_vm_waddr, l_kv_waddr; wire [4*AW-1:0] l_rd_addr; wire [3:0] l_rd_re; wire [7:0] l_rd_src;
    wire [31:0] l_vm_wdata, l_kv_wdata, l_ro_x, l_side_x;
    ot_hbm_su_static_lane #(.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES + 2), .AW(AW), .CW(CW), .LN(LN), .KIND(KIND),
                            .KVT_SH(KVT_SH), .LEAF(LEAF), .MLAT(MLAT), .ALAT(ALAT)) u_lane (
        .clk_stage(clk_stage), .clk_insert(clk_insert), .rst_n(rst_n), .lane_id(q_lane_id),
        .ld(s_q[3]), .ld_bank(s_q[2]), .ld_c(q_ld_c), .emit(s_q[1]), .bank(s_q[0]), .o_v(q_o_v), .i_v(q_i_v), .no(q_no),
        .ni(q_ni), .ls(q_ls), .lvw(q_lvw), .vb(q_vb), .krow(q_krow), .obase(q_obase), .aibase(q_aibase), .aind(q_aind),
        .gsh(q_gsh), .cpair(q_cpair), .dst(q_dst), .srcs(q_srcs),
        .vi_re(l_vi_re), .vi_addr(l_vi_addr), .vi_q(q_vi_q), .rd_addr(l_rd_addr), .rd_re(l_rd_re), .rd_src(l_rd_src),
        .rd_q(q_rd_q), .cx_srcs(q_cx_srcs), .cx_arnd(q_cx_arnd), .cx_arelu(q_cx_arelu), .cx_amin(q_cx_amin),
        .cx_cclip(q_cx_cclip), .cx_imm3(q_cx_imm3), .cp_m1(q_cp_m1), .cp_imm1(q_cp_imm1), .cm_m1(q_cm_m1),
        .cm_m2(q_cm_m2), .cm_qm(q_cm_qm), .cm_imm1(q_cm_imm1), .ca_ad(q_ca_ad), .ca_imm2(q_ca_imm2), .ci_sfu(q_ci_sfu),
        .cs_sfu(q_cs_sfu), .cs_e1(q_cs_e1), .cs_imm2(q_cs_imm2), .ce_e2(q_ce_e2), .ce_imm1(q_ce_imm1), .co_rnd(q_co_rnd),
        .co_dst(q_co_dst), .side_v(l_side_v), .side_x(l_side_x), .side_y((KIND == 2) ? side_y : q_side_y),
        .vm_we(l_vm_we), .vm_waddr(l_vm_waddr), .vm_wdata(l_vm_wdata), .kv_we(l_kv_we), .kv_waddr(l_kv_waddr),
        .kv_wdata(l_kv_wdata), .ro_v(l_ro_v), .ro_x(l_ro_x), .fault(l_fault), .coll(l_coll));
    // ---- output pin registers
    reg r_vi_re; reg [3:0] r_rd_re; reg [AW-1:0] r_vi_addr; reg [4*AW-1:0] r_rd_addr; reg [7:0] r_rd_src;
    always @(posedge c0 or negedge rst_n) if (!rst_n) begin r_vi_re <= 1'b0; r_rd_re <= 4'd0; end
                                          else begin r_vi_re <= l_vi_re; r_rd_re <= l_rd_re; end
    always @(posedge c0) begin r_vi_addr <= l_vi_addr; r_rd_addr <= l_rd_addr; r_rd_src <= l_rd_src; end
    reg r_vm_we, r_kv_we, r_ro_v, r_fault, r_coll; reg [AW-1:0] r_vm_waddr, r_kv_waddr; reg [31:0] r_vm_wdata, r_kv_wdata, r_ro_x;
    always @(posedge c7 or negedge rst_n) if (!rst_n) {r_vm_we, r_kv_we, r_ro_v, r_fault, r_coll} <= 5'd0;
                                          else {r_vm_we, r_kv_we, r_ro_v, r_fault, r_coll} <= {l_vm_we, l_kv_we, l_ro_v, l_fault, l_coll};
    always @(posedge c7) begin r_vm_waddr <= l_vm_waddr; r_kv_waddr <= l_kv_waddr; r_vm_wdata <= l_vm_wdata;
                               r_kv_wdata <= l_kv_wdata; r_ro_x <= l_ro_x; end
    assign {vi_re, vi_addr, rd_addr, rd_re, rd_src} = {r_vi_re, r_vi_addr, r_rd_addr, r_rd_re, r_rd_src};
    assign {vm_we, vm_waddr, vm_wdata, kv_we, kv_waddr, kv_wdata, ro_v, ro_x, fault, coll} =
           {r_vm_we, r_vm_waddr, r_vm_wdata, r_kv_we, r_kv_waddr, r_kv_wdata, r_ro_v, r_ro_x, r_fault, r_coll};
    if (KIND == 2) begin : g_side_comb
        assign side_v = l_side_v; assign side_x = l_side_x;
    end else begin : g_side_reg
        reg r_side_v; reg [31:0] r_side_x;
        always @(posedge c0 or negedge rst_n) if (!rst_n) r_side_v <= 1'b0; else r_side_v <= l_side_v;
        always @(posedge c0) r_side_x <= l_side_x;
        assign side_v = r_side_v; assign side_x = r_side_x;
    end
endmodule
`default_nettype wire
