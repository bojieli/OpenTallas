`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Fixed-parameter tops for the ASAP7 characterisation of the V4.1 vector stream
// unit (results/physical_abi3/asap7/hdc/v41x/<top>/physical.json).  Each is a
// plain instance, so a route needs no -chparam.
//
//   ot_hdc_v41x_vec_tile       the unit at N = 64, M = 16: 48 light lanes, 16 SFU
//                              lanes (lane 0 with the side pipe), the controller,
//                              the control pipe and the reducer.  The die's N =
//                              1,024 / M = 256 is 16 such tiles side by side.
//   ot_hdc_v41x_vec_light64    one light lane of a 64-lane tile
//   ot_hdc_v41x_vec_sfu64      one SFU lane of a 64-lane tile
//   ot_hdc_v41x_vec_red64      the reducer of a 64-lane tile
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vec_tile #(
    parameter integer N = 64,
    parameter integer M = 16,
    parameter integer AW = 24
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [15:0]       i_nout, i_nin,
    input  wire [1:0]        i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi, i_aibase,
    input  wire [1:0]        i_aind,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_bhalf,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire              i_cpair,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire              i_arnd, i_arelu, i_amin, i_cclip,
    input  wire [2:0]        i_m1,
    input  wire [1:0]        i_m2,
    input  wire [2:0]        i_qm, i_ad, i_sfu, i_e1,
    input  wire [1:0]        i_e2,
    input  wire              i_rnd,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase, i_oso, i_osi, i_orow,
    input  wire [1:0]        i_red,
    input  wire              i_redsq, i_redwhole, i_redtree, i_redrnd,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2, i_imm3,
    input  wire [1:0]        i_ch_src,
    input  wire [7:0]        i_ch_seq,
    input  wire [15:0]       i_ch_lead,
    input  wire [15:0]       i_ch_mul,
    input  wire [7:0]        x_seq, x_dseq,
    input  wire [15:0]       x_cnt,
    output wire [7:0]        cr_seq, cr_dseq, cr_rseq,
    output wire [15:0]       cr_cnt,
    output wire [N-1:0]      vi_re,
    output wire [N*AW-1:0]   vi_addr,
    input  wire [N*32-1:0]   vi_q,
    output wire [4*N*AW-1:0] rd_addr,
    output wire [4*N-1:0]    rd_re,
    output wire [8*N-1:0]    rd_src,
    input  wire [4*N*32-1:0] rd_q,
    output wire [N-1:0]      vm_we,
    output wire [N*AW-1:0]   vm_waddr,
    output wire [N*32-1:0]   vm_wdata,
    output wire [N-1:0]      kv_we,
    output wire [N*AW-1:0]   kv_waddr,
    output wire [N*32-1:0]   kv_wdata,
    output wire [N/8-1:0]    res_we,
    output wire [N/8*AW-1:0] res_addr,
    output wire [N/8*32-1:0] res_data,
    output wire              fault,
    output wire              order_fault
);
    ot_hdc_v41x_vec #(.N(N), .M(M)) u (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_nin(i_nin), .i_asrc(i_asrc), .i_bsrc(i_bsrc), .i_csrc(i_csrc), .i_dsrc(i_dsrc),
        .i_abase(i_abase), .i_aso(i_aso), .i_asi(i_asi), .i_aibase(i_aibase), .i_aind(i_aind),
        .i_bbase(i_bbase), .i_bso(i_bso), .i_bsi(i_bsi), .i_bhalf(i_bhalf),
        .i_cbase(i_cbase), .i_cso(i_cso), .i_csi(i_csi), .i_cpair(i_cpair),
        .i_dbase(i_dbase), .i_dso(i_dso), .i_dsi(i_dsi),
        .i_arnd(i_arnd), .i_arelu(i_arelu), .i_amin(i_amin), .i_cclip(i_cclip),
        .i_m1(i_m1), .i_m2(i_m2), .i_qm(i_qm), .i_ad(i_ad), .i_sfu(i_sfu), .i_e1(i_e1), .i_e2(i_e2),
        .i_rnd(i_rnd), .i_dst(i_dst), .i_obase(i_obase), .i_oso(i_oso), .i_osi(i_osi), .i_orow(i_orow),
        .i_red(i_red), .i_redsq(i_redsq), .i_redwhole(i_redwhole), .i_redtree(i_redtree), .i_redrnd(i_redrnd),
        .i_rbase(i_rbase), .i_rso(i_rso), .i_imm1(i_imm1), .i_imm2(i_imm2), .i_imm3(i_imm3),
        .i_ch_src(i_ch_src), .i_ch_seq(i_ch_seq), .i_ch_lead(i_ch_lead), .i_ch_mul(i_ch_mul),
        .x_seq(x_seq), .x_dseq(x_dseq), .x_cnt(x_cnt),
        .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src),
        .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(fault), .order_fault(order_fault), .emitted(), .retire_o(),
        .dbg_emit(), .dbg_eseq(), .dbg_ret(), .dbg_rseq(), .dbg_res(), .dbg_sseq());
endmodule

// One lane of a 64-lane tile; KIND 0 light, 1 SFU.  Every port is the lane's own.
module ot_hdc_v41x_vec_lane64 #(
    parameter integer KIND = 0,
    parameter integer LANE = 37,
    parameter integer AW = 24,
    parameter integer LN = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              ld,
    input  wire              ld_bank,
    input  wire [5*LN*AW-1:0] ld_c,
    input  wire              emit,
    input  wire              bank,
    input  wire [23:0]       o_v, i_v, no, ni,
    input  wire [3:0]        ls, lvw,
    input  wire [5*AW-1:0]   vb,
    input  wire [AW-1:0]     krow, obase, aibase,
    input  wire [1:0]        aind,
    input  wire [4:0]        gsh,
    input  wire              cpair,
    input  wire [1:0]        dst,
    input  wire [7:0]        srcs,
    output wire              vi_re,
    output wire [AW-1:0]     vi_addr,
    input  wire [31:0]       vi_q,
    output wire [4*AW-1:0]   rd_addr,
    output wire [3:0]        rd_re,
    output wire [7:0]        rd_src,
    input  wire [4*32-1:0]   rd_q,
    input  wire              cx_arnd, cx_arelu, cx_amin, cx_cclip,
    input  wire [31:0]       cx_imm3,
    input  wire [2:0]        cp_m1,
    input  wire [31:0]       cp_imm1,
    input  wire [2:0]        cm_m1,
    input  wire [1:0]        cm_m2,
    input  wire [2:0]        cm_qm,
    input  wire [31:0]       cm_imm1,
    input  wire [2:0]        ca_ad,
    input  wire [31:0]       ca_imm2,
    input  wire [2:0]        ci_sfu, cs_sfu, cs_e1,
    input  wire [31:0]       cs_imm2,
    input  wire [1:0]        ce_e2,
    input  wire [31:0]       ce_imm1,
    input  wire              co_rnd,
    input  wire [1:0]        co_dst,
    output wire              vm_we,
    output wire [AW-1:0]     vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [AW-1:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    output wire              ro_v,
    output wire [31:0]       ro_x,
    output wire              fault,
    output wire              coll
);
    ot_hdc_v41x_vec_lane #(.AW(AW), .LN(LN), .LANE(LANE), .KIND(KIND)) u (
        .clk(clk), .rst_n(rst_n), .ld(ld), .ld_bank(ld_bank), .ld_c(ld_c), .emit(emit), .bank(bank),
        .o_v(o_v), .i_v(i_v), .no(no), .ni(ni), .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), .obase(obase),
        .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair), .dst(dst), .srcs(srcs),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src),
        .rd_q(rd_q), .cx_srcs(8'd0), .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin),
        .cx_cclip(cx_cclip), .cx_imm3(cx_imm3), .cp_m1(cp_m1), .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2),
        .cm_qm(cm_qm), .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), .ci_sfu(ci_sfu), .cs_sfu(cs_sfu),
        .cs_e1(cs_e1), .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), .co_dst(co_dst),
        .side_v(), .side_x(), .side_y(32'd0),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .ro_v(ro_v), .ro_x(ro_x), .fault(fault), .coll(coll));
endmodule

module ot_hdc_v41x_vec_light64 (
    input  wire clk, input wire rst_n, input wire ld, input wire ld_bank, input wire [719:0] ld_c,
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
    output wire fault, output wire coll
);
    ot_hdc_v41x_vec_lane64 #(.KIND(0), .LANE(37)) u (.*);
endmodule

module ot_hdc_v41x_vec_sfu64 (
    input  wire clk, input wire rst_n, input wire ld, input wire ld_bank, input wire [719:0] ld_c,
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
    output wire fault, output wire coll
);
    ot_hdc_v41x_vec_lane64 #(.KIND(1), .LANE(5)) u (.*);
endmodule

module ot_hdc_v41x_vec_red64 (
    input  wire clk, input wire rst_n, input wire v_in, input wire [2047:0] x_in, input wire [63:0] live_in,
    input  wire mx_in, sq_in, input wire [3:0] lt_in, input wire span_in, input wire [2:0] l_in,
    input  wire last_in, input wire [7:0] nres_in, input wire rnd_in, input wire [23:0] rbase_in,
    input  wire [4:0] rsh_in, input wire [8:0] meta_in,
    output wire [7:0] o_we, output wire [191:0] o_addr, output wire [255:0] o_data, output wire [8:0] o_meta,
    output wire o_ev, output wire busy, output wire fault
);
    ot_hdc_v41x_vec_red #(.N(64), .MW(9)) u (.*);
endmodule
