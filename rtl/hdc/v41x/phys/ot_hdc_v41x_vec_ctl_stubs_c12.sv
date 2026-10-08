`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM SU c12 (claude hbm-su-attn, 2026-10-05): copy of the hbm-fmax-su controller stubs
// (claude/hbm-fmax-su-20261004 rtl/hdc/v41x/phys/ot_hdc_v41x_vec_ctl_stubs.sv) accepting the c12 parameters, plus the
// controller vehicle top ot_su12_ctl64 (rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv at N 64 / M 16, BCAST 7 / RET 8, MLAT 6 /
// ALAT 6, OPR 1, DDIV 21, SIDEX 4, CAPR 1, FSQ 1, RPAD 1 / RSL 2 / RTAP 1 / ROUT 1).
// PHYSICAL VEHICLE ONLY (hbm-fmax-su 2026-10-04): register stubs for the stream unit's lanes, side pipe and reducer,
// so ot_hdc_v41x_vec's CONTROLLER (issue, checkpoints, chaining credits, control pipe, insertion lines, broadcast
// tree, return stages, published state) is hardened on its own.  The lane / side / reducer are hardened separately
// (their own routes); here each is replaced by a module of the same name and ports that REGISTERS every input bit
// (the controller's paths end at the first register they would reach, the lane's leaf / the unit's input
// register) and drives every output from registers (each output bit the XOR of a few input registers, so no input
// register is optimised away).  Never in a functional source list.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_ctl_stub_fold #(parameter integer WI = 8, parameter integer WO = 4) (
    input  wire clk, input wire [WI-1:0] d, output reg [WO-1:0] q
);
    reg [WI-1:0] r;
    always @(posedge clk) r <= d;
    localparam integer F = (WI + WO - 1) / WO;
    integer o, j;
    reg [WO-1:0] f;
    always @(*) begin
        for (o = 0; o < WO; o = o + 1) begin
            f[o] = 1'b0;
            for (j = 0; j < F; j = j + 1) if (o * F + j < WI) f[o] = f[o] ^ r[o * F + j];
        end
    end
    always @(posedge clk) q <= f;
endmodule

module ot_hdc_v41x_vec_lane #(
    parameter integer AW = 24, parameter integer CW = 24, parameter integer LN = 3, parameter integer KIND = 0,
    parameter integer KVT_SH = 9, parameter integer LEAF = 0, parameter integer MLAT = 3, parameter integer ALAT = 3,
    parameter integer OPR = 0, parameter integer DDIV = 19, parameter integer SIDEX = 0, parameter integer CAPR = 0,
    parameter integer GSH = 0, parameter integer KIMM = 0, parameter integer DENR = 0, parameter integer DRING = 0
) (
    input  wire clk, input wire rst_n, input wire [10:0] lane_id,
    input  wire ld, input wire ld_bank, input wire [5*LN*AW-1:0] ld_c,
    input  wire emit, input wire bank, input wire [CW-1:0] o_v, i_v, no, ni, input wire [3:0] ls, input wire [3:0] lvw,
    input  wire [5*AW-1:0] vb, input wire [AW-1:0] krow, input wire [AW-1:0] obase, input wire [AW-1:0] aibase,
    input  wire [1:0] aind, input wire [4:0] gsh, input wire cpair, input wire [1:0] dst, input wire [7:0] srcs,
    output wire vi_re, output wire [AW-1:0] vi_addr, input wire [31:0] vi_q,
    output wire [4*AW-1:0] rd_addr, output wire [3:0] rd_re, output wire [7:0] rd_src, input wire [4*32-1:0] rd_q,
    input  wire [7:0] cx_srcs, input wire cx_arnd, cx_arelu, cx_amin, cx_cclip, input wire [31:0] cx_imm3,
    input  wire [2:0] cp_m1, input wire [31:0] cp_imm1, input wire [2:0] cm_m1, input wire [1:0] cm_m2,
    input  wire [2:0] cm_qm, input wire [31:0] cm_imm1, input wire [2:0] ca_ad, input wire [31:0] ca_imm2,
    input  wire [2:0] ci_sfu, input wire [2:0] cs_sfu, input wire [2:0] cs_e1, input wire [31:0] cs_imm2,
    input  wire [1:0] ce_e2, input wire [31:0] ce_imm1, input wire co_rnd, input wire [1:0] co_dst,
    output wire side_v, output wire [31:0] side_x, input wire [31:0] side_y,
    output wire vm_we, output wire [AW-1:0] vm_waddr, output wire [31:0] vm_wdata,
    output wire kv_we, output wire [AW-1:0] kv_waddr, output wire [31:0] kv_wdata,
    output wire ro_v, output wire [31:0] ro_x, output wire fault, output wire coll
);
    localparam integer WI = 11 + 2 + 5*LN*AW + 2 + 4*CW + 8 + 5*AW + 3*AW + 2 + 5 + 1 + 2 + 8 + 32 + 128 + 8 + 4 + 32
                          + 3 + 32 + 3 + 2 + 3 + 32 + 3 + 32 + 3 + 3 + 3 + 32 + 2 + 32 + 1 + 2 + 32;
    localparam integer WO = 1 + AW + 4*AW + 4 + 8 + 1 + 32 + 1 + AW + 32 + 1 + AW + 32 + 1 + 32 + 1 + 1;
    wire [WO-1:0] q;
    ot_hdc_v41x_ctl_stub_fold #(.WI(WI), .WO(WO)) u (.clk(clk), .d({lane_id, ld, ld_bank, ld_c, emit, bank, o_v, i_v, no, ni,
        ls, lvw, vb, krow, obase, aibase, aind, gsh, cpair, dst, srcs, vi_q, rd_q, cx_srcs, cx_arnd, cx_arelu, cx_amin,
        cx_cclip, cx_imm3, cp_m1, cp_imm1, cm_m1, cm_m2, cm_qm, cm_imm1, ca_ad, ca_imm2, ci_sfu, cs_sfu, cs_e1, cs_imm2,
        ce_e2, ce_imm1, co_rnd, co_dst, side_y}), .q(q));
    assign {vi_re, vi_addr, rd_addr, rd_re, rd_src, side_v, side_x, vm_we, vm_waddr, vm_wdata, kv_we, kv_waddr, kv_wdata,
            ro_v, ro_x, fault, coll} = q;
endmodule

module ot_hdc_v41x_vec_side #(parameter integer MLAT = 3, parameter integer ALAT = 3, parameter integer DDIV = 19,
                              parameter integer SIDEX = 0, parameter integer FSQ = 0) (
    input wire clk, input wire rst_n, input wire v, input wire [2:0] fn, input wire [31:0] x, input wire [2:0] fn_out,
    output wire [31:0] y, output wire fault
);
    ot_hdc_v41x_ctl_stub_fold #(.WI(39), .WO(33)) u (.clk(clk), .d({v, fn, x, fn_out}), .q({y, fault}));
endmodule

module ot_hdc_v41x_vec_red #(
    parameter integer N = 64, parameter integer LV = 6, parameter integer AW = 24, parameter integer MW = 64,
    parameter integer MLAT = 3, parameter integer ALAT = 3, parameter integer RPAD = 0, parameter integer RSL = 0,
    parameter integer RTAP = 0, parameter integer ROUT = 0, parameter integer SL = 64,
    parameter integer ROPI = 0, parameter integer RKC = 0, parameter integer RHALF = 0
) (
    input  wire clk, input wire rst_n, input wire v_in, input wire [N*32-1:0] x_in, input wire [N-1:0] live_in,
    input  wire mx_in, input wire sq_in, input wire [3:0] lt_in, input wire span_in, input wire [2:0] l_in,
    input  wire last_in, input wire [7:0] nres_in, input wire rnd_in, input wire [AW-1:0] rbase_in,
    input  wire [4:0] rsh_in, input wire [MW-1:0] meta_in,
    output wire [N/8-1:0] o_we, output wire [N/8*AW-1:0] o_addr, output wire [N/8*32-1:0] o_data,
    output wire [MW-1:0] o_meta, output wire o_ev, output wire busy, output wire fault
);
    localparam integer WI = 1 + N*32 + N + 1 + 1 + 4 + 1 + 3 + 1 + 8 + 1 + AW + 5 + MW;
    localparam integer WO = N/8 + N/8*AW + N/8*32 + MW + 3;
    ot_hdc_v41x_ctl_stub_fold #(.WI(WI), .WO(WO)) u (.clk(clk), .d({v_in, x_in, live_in, mx_in, sq_in, lt_in, span_in,
        l_in, last_in, nres_in, rnd_in, rbase_in, rsh_in, meta_in}), .q({o_we, o_addr, o_data, o_meta, o_ev, busy, fault}));
endmodule

// the c12 controller vehicle
module ot_su12_ctl64 #(parameter integer N = 64, parameter integer M = 16, parameter integer AW = 24, parameter integer NW = 16) (
    input  wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input  wire [NW-1:0] i_nout, i_nin, input wire [1:0] i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0] i_abase, i_aso, i_asi, i_aibase, input wire [1:0] i_aind, input wire [AW-1:0] i_bbase, i_bso, i_bsi,
    input  wire i_bhalf, input wire [AW-1:0] i_cbase, i_cso, i_csi, input wire i_cpair, input wire [AW-1:0] i_dbase, i_dso, i_dsi,
    input  wire i_arnd, i_arelu, i_amin, i_cclip, input wire [2:0] i_m1, input wire [1:0] i_m2,
    input  wire [2:0] i_qm, i_ad, i_sfu, i_e1, input wire [1:0] i_e2, input wire i_rnd, input wire [1:0] i_dst,
    input  wire [AW-1:0] i_obase, i_oso, i_osi, i_orow, input wire [1:0] i_red,
    input  wire i_redsq, i_redwhole, i_redtree, i_redrnd, input wire [AW-1:0] i_rbase, i_rso,
    input  wire [31:0] i_imm1, i_imm2, i_imm3,
    input  wire [1:0] i_ch_src, input wire [7:0] i_ch_seq, input wire [15:0] i_ch_lead, i_ch_mul,
    input  wire [7:0] x_seq, x_dseq, input wire [15:0] x_cnt,
    output wire [7:0] cr_seq, cr_dseq, cr_rseq, output wire [15:0] cr_cnt,
    output wire [N-1:0] vi_re, output wire [N*AW-1:0] vi_addr, input wire [N*32-1:0] vi_q,
    output wire [4*N*AW-1:0] rd_addr, output wire [4*N-1:0] rd_re, output wire [8*N-1:0] rd_src, input wire [4*N*32-1:0] rd_q,
    output wire [N-1:0] vm_we, output wire [N*AW-1:0] vm_waddr, output wire [N*32-1:0] vm_wdata,
    output wire [N-1:0] kv_we, output wire [N*AW-1:0] kv_waddr, output wire [N*32-1:0] kv_wdata,
    output wire [N/8-1:0] res_we, output wire [N/8*AW-1:0] res_addr, output wire [N/8*32-1:0] res_data,
    output wire fault, order_fault, output wire [15:0] emitted, output wire retire_o,
    output wire dbg_emit, output wire [7:0] dbg_eseq, output wire dbg_ret, output wire [7:0] dbg_rseq,
    output wire dbg_res, output wire [7:0] dbg_sseq
);
    ot_hdc_v41x_vec #(.N(N), .M(M), .AW(AW), .NW(NW), .BCAST_STAGES(7), .RET_STAGES(8), .MLAT(6), .ALAT(6), .OPR(1),
                      .DDIV(21), .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(64), .CTL12(1)) u (.*);
endmodule

// the same controller on a smaller lane width (a pin-limited die cannot hold the N = 64 lane buses): the control
// pipe, the set-up and the vector loop are lane-width independent, so this is the same logic on a smaller die
module ot_su12_ctl16 #(parameter integer N = 16, parameter integer M = 8, parameter integer AW = 24, parameter integer NW = 16) (
    input  wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input  wire [NW-1:0] i_nout, i_nin, input wire [1:0] i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0] i_abase, i_aso, i_asi, i_aibase, input wire [1:0] i_aind, input wire [AW-1:0] i_bbase, i_bso, i_bsi,
    input  wire i_bhalf, input wire [AW-1:0] i_cbase, i_cso, i_csi, input wire i_cpair, input wire [AW-1:0] i_dbase, i_dso, i_dsi,
    input  wire i_arnd, i_arelu, i_amin, i_cclip, input wire [2:0] i_m1, input wire [1:0] i_m2,
    input  wire [2:0] i_qm, i_ad, i_sfu, i_e1, input wire [1:0] i_e2, input wire i_rnd, input wire [1:0] i_dst,
    input  wire [AW-1:0] i_obase, i_oso, i_osi, i_orow, input wire [1:0] i_red,
    input  wire i_redsq, i_redwhole, i_redtree, i_redrnd, input wire [AW-1:0] i_rbase, i_rso,
    input  wire [31:0] i_imm1, i_imm2, i_imm3,
    input  wire [1:0] i_ch_src, input wire [7:0] i_ch_seq, input wire [15:0] i_ch_lead, i_ch_mul,
    input  wire [7:0] x_seq, x_dseq, input wire [15:0] x_cnt,
    output wire [7:0] cr_seq, cr_dseq, cr_rseq, output wire [15:0] cr_cnt,
    output wire [N-1:0] vi_re, output wire [N*AW-1:0] vi_addr, input wire [N*32-1:0] vi_q,
    output wire [4*N*AW-1:0] rd_addr, output wire [4*N-1:0] rd_re, output wire [8*N-1:0] rd_src, input wire [4*N*32-1:0] rd_q,
    output wire [N-1:0] vm_we, output wire [N*AW-1:0] vm_waddr, output wire [N*32-1:0] vm_wdata,
    output wire [N-1:0] kv_we, output wire [N*AW-1:0] kv_waddr, output wire [N*32-1:0] kv_wdata,
    output wire [N/8-1:0] res_we, output wire [N/8*AW-1:0] res_addr, output wire [N/8*32-1:0] res_data,
    output wire fault, order_fault, output wire [15:0] emitted, output wire retire_o,
    output wire dbg_emit, output wire [7:0] dbg_eseq, output wire dbg_ret, output wire [7:0] dbg_rseq,
    output wire dbg_res, output wire [7:0] dbg_sseq
);
    ot_hdc_v41x_vec #(.N(N), .M(M), .AW(AW), .NW(NW), .BCAST_STAGES(7), .RET_STAGES(8), .MLAT(6), .ALAT(6), .OPR(1),
                      .DDIV(21), .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(64),
                      .CTL12(1)) u (.*);
endmodule

// the same vehicle with the CTL12 = 2 controller (replicated loop control, sliced set-up products, kept-prefix
// loop adds; +4 set-up cycles)
module ot_su12_ctl16c #(parameter integer N = 16, parameter integer M = 8, parameter integer AW = 24, parameter integer NW = 16) (
    input  wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input  wire [NW-1:0] i_nout, i_nin, input wire [1:0] i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0] i_abase, i_aso, i_asi, i_aibase, input wire [1:0] i_aind, input wire [AW-1:0] i_bbase, i_bso, i_bsi,
    input  wire i_bhalf, input wire [AW-1:0] i_cbase, i_cso, i_csi, input wire i_cpair, input wire [AW-1:0] i_dbase, i_dso, i_dsi,
    input  wire i_arnd, i_arelu, i_amin, i_cclip, input wire [2:0] i_m1, input wire [1:0] i_m2,
    input  wire [2:0] i_qm, i_ad, i_sfu, i_e1, input wire [1:0] i_e2, input wire i_rnd, input wire [1:0] i_dst,
    input  wire [AW-1:0] i_obase, i_oso, i_osi, i_orow, input wire [1:0] i_red,
    input  wire i_redsq, i_redwhole, i_redtree, i_redrnd, input wire [AW-1:0] i_rbase, i_rso,
    input  wire [31:0] i_imm1, i_imm2, i_imm3,
    input  wire [1:0] i_ch_src, input wire [7:0] i_ch_seq, input wire [15:0] i_ch_lead, i_ch_mul,
    input  wire [7:0] x_seq, x_dseq, input wire [15:0] x_cnt,
    output wire [7:0] cr_seq, cr_dseq, cr_rseq, output wire [15:0] cr_cnt,
    output wire [N-1:0] vi_re, output wire [N*AW-1:0] vi_addr, input wire [N*32-1:0] vi_q,
    output wire [4*N*AW-1:0] rd_addr, output wire [4*N-1:0] rd_re, output wire [8*N-1:0] rd_src, input wire [4*N*32-1:0] rd_q,
    output wire [N-1:0] vm_we, output wire [N*AW-1:0] vm_waddr, output wire [N*32-1:0] vm_wdata,
    output wire [N-1:0] kv_we, output wire [N*AW-1:0] kv_waddr, output wire [N*32-1:0] kv_wdata,
    output wire [N/8-1:0] res_we, output wire [N/8*AW-1:0] res_addr, output wire [N/8*32-1:0] res_data,
    output wire fault, order_fault, output wire [15:0] emitted, output wire retire_o,
    output wire dbg_emit, output wire [7:0] dbg_eseq, output wire dbg_ret, output wire [7:0] dbg_rseq,
    output wire dbg_res, output wire [7:0] dbg_sseq
);
    ot_hdc_v41x_vec #(.N(N), .M(M), .AW(AW), .NW(NW), .BCAST_STAGES(7), .RET_STAGES(8), .MLAT(6), .ALAT(6), .OPR(1),
                      .DDIV(21), .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(64),
                      .CTL12(2)) u (.*);
endmodule

`ifndef OT_SU_RHPAR
`define OT_SU_RHPAR 0
`endif
// ot_su12_ctl16c with the HALF-RATE reducer issue rule (RHALF 1: reduction beats retire only in ph = 1 cycles, one
// per two cycles; reducer depths doubled + pin stages).  Pairs with ot_hdc_v41x_vred_{slice64,top1024}_c12h.
module ot_su12_ctl16h #(parameter integer N = 16, parameter integer M = 8, parameter integer AW = 24, parameter integer NW = 16) (
    input  wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input  wire [NW-1:0] i_nout, i_nin, input wire [1:0] i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0] i_abase, i_aso, i_asi, i_aibase, input wire [1:0] i_aind, input wire [AW-1:0] i_bbase, i_bso, i_bsi,
    input  wire i_bhalf, input wire [AW-1:0] i_cbase, i_cso, i_csi, input wire i_cpair, input wire [AW-1:0] i_dbase, i_dso, i_dsi,
    input  wire i_arnd, i_arelu, i_amin, i_cclip, input wire [2:0] i_m1, input wire [1:0] i_m2,
    input  wire [2:0] i_qm, i_ad, i_sfu, i_e1, input wire [1:0] i_e2, input wire i_rnd, input wire [1:0] i_dst,
    input  wire [AW-1:0] i_obase, i_oso, i_osi, i_orow, input wire [1:0] i_red,
    input  wire i_redsq, i_redwhole, i_redtree, i_redrnd, input wire [AW-1:0] i_rbase, i_rso,
    input  wire [31:0] i_imm1, i_imm2, i_imm3,
    input  wire [1:0] i_ch_src, input wire [7:0] i_ch_seq, input wire [15:0] i_ch_lead, i_ch_mul,
    input  wire [7:0] x_seq, x_dseq, input wire [15:0] x_cnt,
    output wire [7:0] cr_seq, cr_dseq, cr_rseq, output wire [15:0] cr_cnt,
    output wire [N-1:0] vi_re, output wire [N*AW-1:0] vi_addr, input wire [N*32-1:0] vi_q,
    output wire [4*N*AW-1:0] rd_addr, output wire [4*N-1:0] rd_re, output wire [8*N-1:0] rd_src, input wire [4*N*32-1:0] rd_q,
    output wire [N-1:0] vm_we, output wire [N*AW-1:0] vm_waddr, output wire [N*32-1:0] vm_wdata,
    output wire [N-1:0] kv_we, output wire [N*AW-1:0] kv_waddr, output wire [N*32-1:0] kv_wdata,
    output wire [N/8-1:0] res_we, output wire [N/8*AW-1:0] res_addr, output wire [N/8*32-1:0] res_data,
    output wire fault, order_fault, output wire [15:0] emitted, output wire retire_o,
    output wire dbg_emit, output wire [7:0] dbg_eseq, output wire dbg_ret, output wire [7:0] dbg_rseq,
    output wire dbg_res, output wire [7:0] dbg_sseq
);
    ot_hdc_v41x_vec #(.N(N), .M(M), .AW(AW), .NW(NW), .BCAST_STAGES(7), .RET_STAGES(8), .MLAT(6), .ALAT(6), .OPR(1),
                      .DDIV(21), .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(64),
                      .CTL12(2), .RHALF(1), .RHPAR(`OT_SU_RHPAR)) u (.*);
endmodule
