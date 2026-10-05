`timescale 1ns/1ps
// SIMULATION ONLY.  ot_qwen_rom_rt_die_w12_vp: ot_qwen_rom_rt_die_w12 for the
// speculative verify step -- the core emitted with VPOS (tools/qwen_rom_verify_core_emit_w12.py)
// and the sequencer successor ot_qwen_tp_seq_w12_vp (ENABLE_ARP), its vector-memory
// word port widened to VWA bits and its per-position argmax records exported.
// With VPOS = 0 and ENABLE_ARP = 0 it is ot_qwen_rom_rt_die_w12.
// One Qwen3-8B O4 ROM die for the W12 runtime composition:
// the TP sequencer (ot_qwen_tp_seq_w12) and ot_qwen_rom_core (tools/qwen_rom_rt_core_emit.py:
// the production core with the vector stream unit and its matrix engine built
// as the W12 array spine).  The tile fabric -- G/4 ot_qwen_rom_tile_logic_w12
// elements and the upper tree nodes, with their wire stages -- is composed by
// the host (qwen_rom_rt.cpp) from one compiled tile model, and every memory
// (program, descriptors, code ROM banks, scales, constants, VM, KV) is served
// by the host with registered-response semantics.  Reset/start stimulus is the
// layer-0 bench's (rtl/test/tb_hdc_qwen_layer0_tp2.sv), as in the W6 die.
module ot_qwen_rom_rt_die_w12_vp #(
    parameter integer VPOS = 0,
    parameter integer ENABLE_ARP = 0,
    parameter integer VWA = 12,
    parameter integer G = 5120,
    parameter integer NW = 18,
    parameter integer SNW = 18,
    parameter integer QWEN_FULLSHAPE = 1,
    parameter integer ME_IDLE_GATE = 1,
    parameter integer SW = 1024,
    parameter integer LV = 3,
    parameter integer SMIN = 7,
    parameter integer SMAX = 10,
    parameter integer TCUT = 7,
    parameter integer BD = 1,
    parameter integer XVM = 0,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer MEM_EXTRA = 0,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer MUL_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer ENABLE_AR256 = 0,
    parameter integer D = 2
) (
    input  wire              clk,
    output reg               rt_rst_n,
    output reg  [31:0]       cyc,
    output reg               start,
    input  wire [SNW-1:0]    tp_token,
    input  wire [SNW-1:0]    tp_pos,
    input  wire              h_start,
    output wire              me_clk_en,
    output wire              s_done,
    output wire              s_fault,
    output wire              core_fault,
    output wire [SNW-1:0]    seq_ntok,
    output wire [8*SNW-1:0]  seq_tok_vec,
    output wire [8*32-1:0]   seq_val_vec,
    output wire [3:0]        seq_n_tok,
    output wire [31:0]       seq_nval,
    output wire [31:0]       core_cycles,
    output wire              c_valid,
    input  wire              c_ready,
    output wire [511:0]      c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [31:0]       c_tag,
    input  wire              r_valid,
    input  wire [511:0]      r_data,
    input  wire              r_last,
    input  wire [((D > 2) ? 2 : 1)-1:0] r_rank,
    input  wire              r_err,
    output wire [11:0]       prog_base,
    output wire              prog_re,
    output wire [11:0]       prog_addr,
    input  wire [1023:0]     prog_q,
    output wire              desc_re,
    output wire [5:0]        desc_addr,
    input  wire [63:0]       desc_q,
    output wire              s_vre,
    output wire [VWA-1:0]    s_vraddr,
    input  wire [511:0]      s_vrq,
    output wire              s_vwe,
    output wire [VWA-1:0]    s_vwaddr,
    output wire [511:0]      s_vwdata,
    // core memories
    output wire              wrom_re,         // the stream unit's weight-ROM read (must never assert)
    output wire              int8_wrom_re,
    output wire [23:0]       int8_wrom_addr,
    output wire              scale_re,
    output wire [(G >> SMIN)-1:0]      scale_gre,
    output wire [(G >> SMIN)*24-1:0]   scale_addr,
    input  wire [(G >> SMIN)*16*16-1:0] scale_q,
    output wire [SW-1:0]     crom_re,
    output wire [SW*24-1:0]  crom_addr,
    input  wire [SW*64-1:0]  crom_q,
    output wire              kv_re,
    output wire [SW-1:0]     kv_we,
    output wire [SW*24-1:0]  kv_waddr,
    output wire [SW*32-1:0]  kv_wdata,
    output wire [SW-1:0]     va_re, vb_re, vc_re,
    output wire [SW*24-1:0]  va_addr, vb_addr, vc_addr,
    input  wire [SW*32-1:0]  va_q, vb_q, vc_q,
    output wire [SW-1:0]     vw_su_we,
    output wire [SW*24-1:0]  vw_su_addr,
    output wire [SW*32-1:0]  vw_su_data,
    output wire              vw_rd_we,
    output wire [23:0]       vw_rd_addr,
    output wire [31:0]       vw_rd_data,
    output wire              vw_mx_we,
    output wire [23:0]       vw_mx_addr,
    output wire [15:0]       vw_mx_mask,
    output wire [511:0]      vw_mx_data,
    output wire [(G >> SMIN)-1:0]      vw_me_we,
    output wire [(G >> SMIN)*24-1:0]   vw_me_addr,
    output wire [(G >> SMIN)*16-1:0]   vw_me_mask,
    output wire [(G >> SMIN)*16*32-1:0] vw_me_data,
    output wire              me_ov,
    // array spine: x chunk port and tile fabric
    output wire [(1<<SMAX)-1:0]    vx_re,
    output wire [(1<<SMAX)*24-1:0] vx_addr,
    input  wire [(1<<SMAX)*32-1:0] vx_q,
    output wire              tgo,
    output wire [3*NW+13*24+13-1:0] tb,
    output wire [(1<<SMAX)*32-1:0] xl_d,
    input  wire [(G >> TCUT)*16*32-1:0] t_lvl,
    input  wire              fab_fault
);
    localparam integer W=16, AW=24, PAW=12, DAW=6, FW=512;
    initial begin rt_rst_n = 0; start = 0; cyc = 0; end
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (cyc==5) rt_rst_n <= 1;
        if (cyc==7) start <= 1;
        if (cyc==8) start <= 0;
    end
    wire rst_n = rt_rst_n;
    wire core_start, core_done;
    wire [SNW-1:0] core_tok, core_pos, core_ntok;
    wire [31:0] core_nval;
    wire coll_busy;
    wire [NW-1:0] core_ntok_c;
    assign core_ntok = core_ntok_c;
    // the DYN model constants of Qwen3-8B (hidden 4,096, half head 64, head 128): the parent
    // ot_qwen_rom_rt_die_w12 leaves the core's defaults (128/8/16), which are correct only at position 0
    ot_qwen_rom_core #(.W(W),.G(G),.AW(AW),.NW(NW),.PAW(PAW),.HID(4096),.HALF(64),.HD(128),
        .SU_VEC(1),.SW(SW),.LV(LV),.KV_FP8(1),
        .INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.INT8_EMBED(0),.QWEN_FULLSHAPE(QWEN_FULLSHAPE),
        .ME_STALL(0),.ME_IDLE_GATE(ME_IDLE_GATE),
        .SMIN(SMIN),.SMAX(SMAX),.TCUT(TCUT),.BD(BD),.XVM(XVM),.NWS(NWS),.TWS(TWS),.ORD(ORD),.SCALE_LOCAL(SCALE_LOCAL),.MEM_EXTRA(MEM_EXTRA),
        .ACC_LAT(ACC_LAT),.TREE_LAT(TREE_LAT),.MUL_LAT(MUL_LAT),
        .FAST_ISSUE(FAST_ISSUE),.KV_PREP(KV_PREP),.VPOS(VPOS)) core (
        .clk(clk),.rst_n(rst_n),.start(core_start),.token(core_tok[NW-1:0]),.pos(core_pos[NW-1:0]),
        .done(core_done),.next_token(core_ntok_c),.next_val(core_nval),
        .cycles(core_cycles),.fault(core_fault),
        .prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),
        .wrom_re(wrom_re),.wrom_addr(),.wrom_q({(G*W*16){1'b0}}),
        .int8_wrom_re(int8_wrom_re),.int8_wrom_addr(int8_wrom_addr),
        .scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr),.scale_q(scale_q),
        .embed_code_re(),.embed_code_addr(),.embed_code_q(512'd0),
        .embed_scale_re(),.embed_scale_addr(),.embed_scale_q(16'd0),
        .crom_re(crom_re),.crom_addr(crom_addr),.crom_q(crom_q),
        .kv_re(kv_re),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_write_drained(1'b1),.kv_write_flush(),
        .va_re(va_re),.va_addr(va_addr),.va_q(va_q),
        .vb_re(vb_re),.vb_addr(vb_addr),.vb_q(vb_q),
        .vc_re(vc_re),.vc_addr(vc_addr),.vc_q(vc_q),
        .vw_me_we(vw_me_we),.vw_me_addr(vw_me_addr),.vw_me_mask(vw_me_mask),.vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we),.vw_su_addr(vw_su_addr),.vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we),.vw_rd_addr(vw_rd_addr),.vw_rd_data(vw_rd_data),
        .vw_mx_we(vw_mx_we),.vw_mx_addr(vw_mx_addr),.vw_mx_mask(vw_mx_mask),.vw_mx_data(vw_mx_data),
        .me_ov(me_ov),
        .kvd_v(),.kvd_wbase(),.kvd_ts(),.kvd_ks(),.kvd_js(),.kvd_wcs(),.kvd_split(),.kvd_jsh(),
        .kvd_tiles(),.kvd_k(),.kvd_nout(),.kvd_kindk(),.kvd_pos(),.kv_ok(1'b1),
        .wrom_su(),.wd_v(),.wd_wbase(),.wd_sbase(),.wd_tiles(),.wd_k(),.wd_nout(),
        .vx_re(vx_re),.vx_addr(vx_addr),.vx_q(vx_q),
        .tgo(tgo),.tb(tb),.xl_d(xl_d),.t_lvl(t_lvl),.fab_fault(fab_fault),
        .w_ok(1'b1),.emb_ok(1'b1),.me_mem_ok(1'b1),.me_clk_en(me_clk_en));
    ot_qwen_tp_seq_w12_vp #(.N(D),.NW(SNW),.PAW(PAW),.VWA(VWA),.DAW(DAW),.FW(FW),.TAGW(32),
                    .QWEN_FULLSHAPE(QWEN_FULLSHAPE), .ENABLE_AR256(ENABLE_AR256),
                    .ENABLE_ARP(ENABLE_ARP), .NTOK(8)) seq (
        .clk(clk),.rst_n(rst_n),.start(start | h_start),.token(tp_token),.pos(tp_pos),
        .done(s_done),.next_token(seq_ntok),.next_val(seq_nval),
        .fault(s_fault),.coll_busy(coll_busy),
        .tok_vec(seq_tok_vec),.val_vec(seq_val_vec),.n_tok(seq_n_tok),
        .core_start(core_start),.core_token(core_tok),.core_pos(core_pos),
        .core_done(core_done),.core_next_token(core_ntok),.core_next_val(core_nval),
        .core_fault(core_fault),.prog_base(prog_base),
        .desc_re(desc_re),.desc_addr(desc_addr),.desc_q(desc_q),
        .vm_re(s_vre),.vm_raddr(s_vraddr),.vm_rq(s_vrq),
        .vm_we(s_vwe),.vm_waddr(s_vwaddr),.vm_wdata(s_vwdata),
        .c_valid(c_valid),.c_ready(c_ready),.c_data(c_data),
        .c_last(c_last),.c_mode(c_mode),.c_tag(c_tag),
        .r_valid(r_valid),.r_data(r_data),.r_last(r_last),
        .r_rank(r_rank),.r_err(r_err));
endmodule
