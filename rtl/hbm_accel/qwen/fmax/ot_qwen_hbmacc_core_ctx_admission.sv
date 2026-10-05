`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PHYSICAL CONTEXT of the HA8 die control (fmax closure, 2026-10-04): the generated core ot_qwen_rom_core (sequencer:
// fetch FIFO, decode into NEXT, issue, argmax fold, ME clock enable / ICG, counters) exactly as the die top
// ot_qwen_hbmacc_rt_die_w12 instantiates it, with the engine-side stream gating ot_qwen_hbmacc_gate_f12 (OPT selects the
// die's original expression or the 1.2 GHz form) closing the me_mem_ok / kv_ok loop through the core, and the two
// units replaced by the registered-boundary stubs of ot_qwen_core_ctx_stubs.sv (spine on the gated engine clock).
// Route-only; the core text comes from tools/qwen_hbmacc_core_ctx_emit.py --core rtl/hbm_accel/qwen/fmax/ot_hdc_core_vector_weight_f12.sv
// (ot_qwen_rom_core with the ISA header inlined; ME_ISSUE_RE = 0 is the original core).
// ---------------------------------------------------------------------------
module ot_qwen_hbmacc_core_ctx_admission #(
    parameter integer ADMISSION_PIPE = 0,
    parameter integer GATE_OPT = 1,
    parameter integer ME_ISSUE_RE = 1,
    parameter integer DEC_FAST = 1,          // both: core successor rtl/hbm_accel/qwen/fmax/ot_hdc_core_vector_weight_f12.sv
    parameter integer G = 6144, NW = 18, SW = 64, LV = 7,
    parameter integer SMIN = 7, SMAX = 11, TCUT = 7, BD = 41, XVM = 1, NWS = 5, TWS = 38, ORD = 7, MEM_EXTRA = 1,
    parameter integer NSEG = 8, LAGW = 40, CW = 32
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               start,
    input  wire [NW-1:0]      token,
    input  wire [NW-1:0]      pos,
    output wire               done,
    output wire [NW-1:0]      next_token,
    output wire [31:0]        next_val,
    output wire [31:0]        cycles,
    output wire               fault,
    output wire               prog_re,
    output wire [11:0]        prog_addr,
    input  wire [1023:0]      prog_q,
    input  wire               fab_fault,
    output wire               me_clk_en,
    output wire               wrom_re,
    output wire               me_ov,
    output wire [(G >> SMIN)-1:0] vw_me_we,
    output wire               vw_mx_we,
    output wire [SW-1:0]      vw_su_we,
    output wire [SW-1:0]      kv_we,
    input  wire [NSEG*24-1:0] seg_base,
    input  wire [NSEG*24-1:0] seg_len,
    input  wire [NSEG*CW-1:0] seg_sidx,
    input  wire [NSEG*2-1:0]  seg_kind,
    input  wire [CW-1:0]      w_a_gray,
    output wire [CW-1:0]      w_c_gray,
    output wire               hbm_fault
);
    localparam integer W = 16, AW = 24, PAW = 12;
    // the die's reset is a register (ot_qwen_hbmacc_rt_die_w12 rt_rst_n): a synchroniser here, not a raw port
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rst_i = rs[1];
    wire hb_me_ok, hb_kv_ok, int8_wrom_re;
    wire [AW-1:0] int8_wrom_addr;
    ot_qwen_rom_core_admission #(.W(W),.G(G),.AW(AW),.NW(NW),.PAW(PAW),
        .SU_VEC(1),.SW(SW),.LV(LV),.KV_FP8(1),
        .INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.INT8_EMBED(0),.QWEN_FULLSHAPE(1),
        .ME_STALL(1),.ME_IDLE_GATE(1),.KV_HBM(1),
        .HID(4096),.HALF(64),.HD(128),
        .SMIN(SMIN),.SMAX(SMAX),.TCUT(TCUT),.BD(BD),.XVM(XVM),.NWS(NWS),.TWS(TWS),.ORD(ORD),.SCALE_LOCAL(0),.MEM_EXTRA(MEM_EXTRA),
        .ACC_LAT(5),.TREE_LAT(3),.MUL_LAT(5),.FAST_ISSUE(0),.KV_PREP(0),.ME_ISSUE_RE(ME_ISSUE_RE),.ME_ADMISSION_PIPE(ADMISSION_PIPE),.DEC_FAST(DEC_FAST)) core (
        .clk(clk),.rst_n(rst_i),.start(start),.token(token),.pos(pos),
        .done(done),.next_token(next_token),.next_val(next_val),
        .cycles(cycles),.fault(fault),
        .prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),
        .wrom_re(wrom_re),.wrom_addr(),.wrom_q({(G*W*16){1'b0}}),
        .int8_wrom_re(int8_wrom_re),.int8_wrom_addr(int8_wrom_addr),
        .scale_re(),.scale_gre(),.scale_addr(),.scale_q({((G >> SMIN)*W*16){1'b0}}),
        .embed_code_re(),.embed_code_addr(),.embed_code_q(512'd0),
        .embed_scale_re(),.embed_scale_addr(),.embed_scale_q(16'd0),
        .crom_re(),.crom_addr(),.crom_q({(SW*64){1'b0}}),
        .kv_re(),.kv_we(kv_we),.kv_waddr(),.kv_wdata(),
        .kv_write_drained(1'b1),.kv_write_flush(),
        .va_re(),.va_addr(),.va_q({(SW*32){1'b0}}),
        .vb_re(),.vb_addr(),.vb_q({(SW*32){1'b0}}),
        .vc_re(),.vc_addr(),.vc_q({(SW*32){1'b0}}),
        .vw_me_we(vw_me_we),.vw_me_addr(),.vw_me_mask(),.vw_me_data(),
        .vw_su_we(vw_su_we),.vw_su_addr(),.vw_su_data(),
        .vw_rd_we(),.vw_rd_addr(),.vw_rd_data(),
        .vw_mx_we(vw_mx_we),.vw_mx_addr(),.vw_mx_mask(),.vw_mx_data(),
        .me_ov(me_ov),
        .kvd_v(),.kvd_wbase(),.kvd_ts(),.kvd_ks(),.kvd_js(),.kvd_wcs(),.kvd_split(),.kvd_jsh(),
        .kvd_tiles(),.kvd_k(),.kvd_nout(),.kvd_kindk(),.kvd_pos(),.kv_ok(hb_kv_ok),
        .wrom_su(),.wd_v(),.wd_wbase(),.wd_sbase(),.wd_tiles(),.wd_k(),.wd_nout(),
        .vx_re(),.vx_addr(),.vx_q({((1<<SMAX)*32){1'b0}}),
        .tgo(),.tb(),.xl_d(),.t_lvl({((G >> TCUT)*W*32){1'b0}}),.fab_fault(fab_fault),
        .w_ok(1'b1),.emb_ok(1'b1),.me_mem_ok(hb_me_ok),.me_clk_en(me_clk_en));
    ot_qwen_hbmacc_gate_admission #(.ADMISSION_PIPE(ADMISSION_PIPE), .OPT(GATE_OPT), .NSEG(NSEG), .LAGW(LAGW), .CW(CW), .AW(AW)) gate (
        .clk(clk), .rst_n(rst_i), .int8_wrom_re(int8_wrom_re), .int8_wrom_addr(int8_wrom_addr), .me_clk_en(me_clk_en),
        .seg_base(seg_base), .seg_len(seg_len), .seg_sidx(seg_sidx), .seg_kind(seg_kind), .w_a_gray(w_a_gray),
        .me_ok(hb_me_ok), .kv_ok(hb_kv_ok), .w_c_gray(w_c_gray), .hbm_fault(hbm_fault));
endmodule
