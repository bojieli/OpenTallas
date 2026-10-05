`timescale 1ns/1ps
// SIMULATION ONLY.  1.2 GHz successor of the HA8 die ot_qwen_hbmacc_rt_die_w12.sv (HBM-accel fmax closure, 2026-10-04;
// that file stays byte-identical).  The module keeps the name ot_qwen_hbmacc_rt_die_w12 so the HA8 host binds it
// unchanged; it is compiled INSTEAD of the original only by tools/qwen_hbmacc_rt_token_w12_f12.py.  Changes, each
// behind a parameter whose 0 value is the original:
//   ME_ISSUE_RE  core successor rtl/hbm_accel/qwen/fmax/ot_hdc_core_vector_weight_f12.sv (engine issue off me_mem_ok)
//   DEC_FAST     same core successor: keep-prefix decode adders, registered DYN_TTILES, parallel chase compares
//   (GATE_OPT 2 / 3: registered window count / registered thresholds + consumed count one cycle later)
//   GATE_OPT     stream gating as ot_qwen_hbmacc_gate_f12 (OPT 0 = this die's expressions; 1 = the 1.2 GHz form)
//   TPSEQ_F12    TP sequencer ot_qwen_tp_seq_w12_f12 REG_OUT = REG_CDATA = 1 (registered collective/VM outputs)
// SIMULATION ONLY.  HA8: the Qwen3-8B HBM-ACCELERATOR runtime die (default-off: built only by the HA8 driver
// tools/qwen_hbmacc_rt_token_w12.py).  Derived from the pinned W12 runtime die ot_qwen_rom_rt_die_w12.sv
// (byte-identical, untouched) with three changes:
//
//  1. WEIGHTS AND KV FROM HBM.  The engine's INT8 code words and the KV window of positions < P are one
//     prefetch STREAM in HBM (consumption order), fetched by ot_hbmacc_qwen_wstream (the measured r14
//     streaming controller, HBM clock domain, a separate model the host clocks at 1.024 ns) into a window
//     the engine drains.  The core runs with ME_STALL = 1: me_mem_ok is low while the spine presents a code
//     word that has not completed in the window (an exact pause of the engine and its tiles), and KV_HBM = 1:
//     kv_ok gates every KV-sourced op until the stage's KV segment has completed.  SRAM-resident segments
//     (the lm_head, and the layers that fit the die SRAM) are never gated.  The stream's per-stage SEGMENT
//     TABLE (code-word base, length, stream index, kind) is a host-written configuration.
//  2. NONZERO POSITION.  The core gets the Qwen3-8B DYN constants HID 4096 / HALF 64 / HD 128 (the pinned die
//     leaves the reduced model's defaults, which are only correct at position 0; see the REAL_MEM die).
//  3. CYCLE ATTRIBUTION.  Every cycle is classified (priority order): HBM weight wait, HBM KV wait, matmul
//     (engine edge on a dense op), attention (engine edge on a KV op), collective, stream unit, other
//     (sequencer, barrier, issue), and counted.
//
// The window's data are the engine's code banks (served by the host exactly as in the pinned runtime); the
// stream module times their arrival.  The consumed-word count returned to the stream lags the spine's read
// position by LAGW words (the tiles read each word BD engine edges after the spine).
module ot_qwen_hbmacc_rt_die_w12 #(
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
    parameter integer D = 2,
    // HA8
    parameter integer NSEG = 8,
    parameter integer LAGW = 40,
    parameter integer CW = 32,
    parameter integer ME_ISSUE_RE = 1,
    parameter integer DEC_FAST = 1,
    parameter integer GATE_OPT = 1,
    parameter integer TPSEQ_F12 = 1
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
    output wire [7:0]        s_vraddr,
    input  wire [511:0]      s_vrq,
    output wire              s_vwe,
    output wire [7:0]        s_vwaddr,
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
    input  wire              fab_fault,
    // HA8: stream configuration (host, per stage), stream status (HBM domain, Gray), statistics
    input  wire [NSEG*24-1:0] seg_base,
    input  wire [NSEG*24-1:0] seg_len,
    input  wire [NSEG*CW-1:0] seg_sidx,
    input  wire [NSEG*2-1:0]  seg_kind,         // 0 unused, 1 HBM code words, 2 SRAM-resident code words, 3 KV (HBM)
    input  wire [CW-1:0]      w_a_gray,         // stream words complete in the window (HBM domain)
    output wire [CW-1:0]      w_c_gray,         // stream words consumed (to the HBM domain)
    output wire               hbm_fault,
    output reg  [CW-1:0]      st_wwait, st_kvwait, st_mm, st_attn, st_coll, st_su, st_other,
    output reg  [CW-1:0]      st_last_w         // cycle of the last code-word read
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
    wire hb_me_ok, hb_kv_ok;
    wire [NW-1:0] core_ntok_c;
    assign core_ntok = core_ntok_c;
    ot_qwen_rom_core #(.W(W),.G(G),.AW(AW),.NW(NW),.PAW(PAW),
        .SU_VEC(1),.SW(SW),.LV(LV),.KV_FP8(1),
        .INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.INT8_EMBED(0),.QWEN_FULLSHAPE(QWEN_FULLSHAPE),
        .ME_STALL(1),.ME_IDLE_GATE(ME_IDLE_GATE),.KV_HBM(1),
        .HID(4096),.HALF(64),.HD(128),
        .SMIN(SMIN),.SMAX(SMAX),.TCUT(TCUT),.BD(BD),.XVM(XVM),.NWS(NWS),.TWS(TWS),.ORD(ORD),.SCALE_LOCAL(SCALE_LOCAL),.MEM_EXTRA(MEM_EXTRA),
        .ACC_LAT(ACC_LAT),.TREE_LAT(TREE_LAT),.MUL_LAT(MUL_LAT),
        .FAST_ISSUE(FAST_ISSUE),.KV_PREP(KV_PREP),.ME_ISSUE_RE(ME_ISSUE_RE),.DEC_FAST(DEC_FAST)) core (
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
        .kvd_tiles(),.kvd_k(),.kvd_nout(),.kvd_kindk(),.kvd_pos(),.kv_ok(hb_kv_ok),
        .wrom_su(),.wd_v(),.wd_wbase(),.wd_sbase(),.wd_tiles(),.wd_k(),.wd_nout(),
        .vx_re(vx_re),.vx_addr(vx_addr),.vx_q(vx_q),
        .tgo(tgo),.tb(tb),.xl_d(xl_d),.t_lvl(t_lvl),.fab_fault(fab_fault),
        .w_ok(1'b1),.emb_ok(1'b1),.me_mem_ok(hb_me_ok),.me_clk_en(me_clk_en));
    ot_qwen_tp_seq_w12_f12 #(.REG_OUT(TPSEQ_F12),.REG_CDATA(TPSEQ_F12),.N(D),.NW(SNW),.PAW(PAW),.VWA(8),.DAW(DAW),.FW(FW),.TAGW(32),
                    .QWEN_FULLSHAPE(QWEN_FULLSHAPE), .ENABLE_AR256(ENABLE_AR256)) seq (
        .clk(clk),.rst_n(rst_n),.start(start | h_start),.token(tp_token),.pos(tp_pos),
        .done(s_done),.next_token(seq_ntok),.next_val(seq_nval),
        .fault(s_fault),.coll_busy(coll_busy),
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
    // ---- HA8: stream gating ------------------------------------------------------------------------
    wire w_ready = hb_me_ok;                  // (attribution below: a cycle the presented read is not served)
    ot_qwen_hbmacc_gate_f12 #(.OPT(GATE_OPT), .NSEG(NSEG), .LAGW(LAGW), .CW(CW), .AW(24)) gate (
        .clk(clk), .rst_n(rst_n), .int8_wrom_re(int8_wrom_re), .int8_wrom_addr(int8_wrom_addr), .me_clk_en(me_clk_en),
        .seg_base(seg_base), .seg_len(seg_len), .seg_sidx(seg_sidx), .seg_kind(seg_kind), .w_a_gray(w_a_gray),
        .me_ok(hb_me_ok), .kv_ok(hb_kv_ok), .w_c_gray(w_c_gray), .hbm_fault(hbm_fault));
    // ---- HA8: cycle attribution ---------------------------------------------------------------------
    wire run_nx = (core.st == 2'd2) && core.nx_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st_wwait <= 0; st_kvwait <= 0; st_mm <= 0; st_attn <= 0; st_coll <= 0; st_su <= 0; st_other <= 0; st_last_w <= 0;
        end else begin
            if (int8_wrom_re && !w_ready && rst_n) st_wwait <= st_wwait + 1;
            else if (run_nx && core.d_unit == 2'd1 && core.me_wsrc && !core.kv_gate) st_kvwait <= st_kvwait + 1;
            else if (me_clk_en && !core.me_idle && !core.me_wsrc) st_mm <= st_mm + 1;
            else if (me_clk_en && !core.me_idle && core.me_wsrc) st_attn <= st_attn + 1;
            else if (coll_busy) st_coll <= st_coll + 1;
            else if (!core.su_idle) st_su <= st_su + 1;
            else st_other <= st_other + 1;
            if (me_clk_en && int8_wrom_re) st_last_w <= cyc;
        end
    end
endmodule
