`timescale 1ns/1ps
// SIMULATION ONLY.  ot_qwen_hbmacc_rt_die_w12_vp: the HA8 HBM-accelerator runtime die
// (ot_qwen_hbmacc_rt_die_w12.sv, unchanged) for the DSpark VERIFY step, default-off (built only by
// tools/qwen_hbmacc_rt_verify_w12.py).  The verify changes are exactly those of
// ot_qwen_rom_rt_die_w12_vp.sv against ot_qwen_rom_rt_die_w12.sv:
//   * the core emitted with VPOS (tools/qwen_rom_verify_core_emit_w12.py: per-position DYN tables);
//   * the sequencer successor ot_qwen_tp_seq_w12_vp (ENABLE_ARP: wide all-reduce counts, per-position
//     argmax records), its vector-memory word port VWA bits wide, the argmax records exported;
// plus one stream change, MULTI-POSITION WEIGHT REUSE: the p-position verify program
// (tools/qwen_rom_verify_program_w12.py) issues every dense matvec p times back to back, so each HBM
// code word is read p times from the prefetch window while it is resident.  A window slot is released
// to the stream only on its LAST use: a per-slot use counter (3 bits, host-configured target w_nuse =
// p) advances the consumed count on the p-th read of a word.  The window must therefore hold the
// largest matvec's words plus the LAGW release lag (the driver checks it).  w_nuse = 1 is the HA8 die.
//
// Original HA8 header:
// | SIMULATION ONLY.  HA8: the Qwen3-8B HBM-ACCELERATOR runtime die (default-off: built only by the HA8 driver
// | tools/qwen_hbmacc_rt_token_w12.py).  Derived from the pinned W12 runtime die ot_qwen_rom_rt_die_w12.sv
// | (byte-identical, untouched) with three changes:
// |
// |  1. WEIGHTS AND KV FROM HBM.  The engine's INT8 code words and the KV window of positions < P are one
// |     prefetch STREAM in HBM (consumption order), fetched by ot_hbmacc_qwen_wstream (the measured r14
// |     streaming controller, HBM clock domain, a separate model the host clocks at 1.024 ns) into a window
// |     the engine drains.  The core runs with ME_STALL = 1: me_mem_ok is low while the spine presents a code
// |     word that has not completed in the window (an exact pause of the engine and its tiles), and KV_HBM = 1:
// |     kv_ok gates every KV-sourced op until the stage's KV segment has completed.  SRAM-resident segments
// |     (the lm_head, and the layers that fit the die SRAM) are never gated.  The stream's per-stage SEGMENT
// |     TABLE (code-word base, length, stream index, kind) is a host-written configuration.
// |  2. NONZERO POSITION.  The core gets the Qwen3-8B DYN constants HID 4096 / HALF 64 / HD 128 (the pinned die
// |     leaves the reduced model's defaults, which are only correct at position 0; see the REAL_MEM die).
// |  3. CYCLE ATTRIBUTION.  Every cycle is classified (priority order): HBM weight wait, HBM KV wait, matmul
// |     (engine edge on a dense op), attention (engine edge on a KV op), collective, stream unit, other
// |     (sequencer, barrier, issue), and counted.
// |
// | The window's data are the engine's code banks (served by the host exactly as in the pinned runtime); the
// | stream module times their arrival.  The consumed-word count returned to the stream lags the spine's read
// | position by LAGW words (the tiles read each word BD engine edges after the spine).
module ot_qwen_hbmacc_rt_die_w12_vp #(
    parameter integer VPOS = 1,
    parameter integer ENABLE_ARP = 1,
    parameter integer VWA = 12,
    parameter integer USE_HW_RELEASE = 0,   // 1: the release is the synthesizable rtl/hbm_accel/qwen/ot_hbmacc_win_usecount.sv
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
    parameter integer CW = 32
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
    output wire [8*SNW-1:0]  seq_tok_vec,
    output wire [8*32-1:0]   seq_val_vec,
    output wire [3:0]        seq_n_tok,
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
    input  wire              fab_fault,
    // HA8: stream configuration (host, per stage), stream status (HBM domain, Gray), statistics
    input  wire [NSEG*24-1:0] seg_base,
    input  wire [NSEG*24-1:0] seg_len,
    input  wire [NSEG*CW-1:0] seg_sidx,
    input  wire [NSEG*2-1:0]  seg_kind,         // 0 unused, 1 HBM code words, 2 SRAM-resident code words, 3 KV (HBM)
    input  wire [3:0]         w_nuse,           // VERIFY: reads of each HBM code word before its window slot is released (p)
    input  wire [CW-1:0]      w_a_gray,         // stream words complete in the window (HBM domain)
    output reg  [CW-1:0]      w_c_gray,         // stream words consumed (to the HBM domain)
    output reg                hbm_fault,
    output reg  [CW-1:0]      st_wwait, st_kvwait, st_mm, st_attn, st_coll, st_su, st_other,
    output reg  [CW-1:0]      st_last_w,        // cycle of the last code-word read
    output wire [CW-1:0]      st_nreads,        // VERIFY: HBM code-word reads (p x the stage's HBM words)
    output reg                rel_fault         // VERIFY: a code word read after its window slot was released
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
        .kvd_tiles(),.kvd_k(),.kvd_nout(),.kvd_kindk(),.kvd_pos(),.kv_ok(hb_kv_ok),
        .wrom_su(),.wd_v(),.wd_wbase(),.wd_sbase(),.wd_tiles(),.wd_k(),.wd_nout(),
        .vx_re(vx_re),.vx_addr(vx_addr),.vx_q(vx_q),
        .tgo(tgo),.tb(tb),.xl_d(xl_d),.t_lvl(t_lvl),.fab_fault(fab_fault),
        .w_ok(1'b1),.emb_ok(1'b1),.me_mem_ok(hb_me_ok),.me_clk_en(me_clk_en));
    ot_qwen_tp_seq_w12_vp #(.N(D),.NW(SNW),.PAW(PAW),.VWA(VWA),.DAW(DAW),.FW(FW),.TAGW(32),
                    .QWEN_FULLSHAPE(QWEN_FULLSHAPE), .ENABLE_AR256(ENABLE_AR256),
                    .ENABLE_ARP(ENABLE_ARP), .NTOK(8)) seq (
        .clk(clk),.rst_n(rst_n),.start(start | h_start),.token(tp_token),.pos(tp_pos),
        .done(s_done),.next_token(seq_ntok),.next_val(seq_nval),
        .tok_vec(seq_tok_vec),.val_vec(seq_val_vec),.n_tok(seq_n_tok),
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
    function automatic [CW-1:0] g2b(input [CW-1:0] g);
        integer i; begin g2b[CW-1] = g[CW-1]; for (i = CW - 2; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i]; end
    endfunction
    reg  [CW-1:0] a_s1, a_s2;                 // 2-flop synchroniser of the window's complete-word count
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_s1 <= 0; a_s2 <= 0; end else begin a_s1 <= w_a_gray; a_s2 <= a_s1; end
    wire [CW-1:0] a_bin = g2b(a_s2);
    // the spine's presented code-word read -> segment
    reg           hit, hit_res, hit_hbm;
    reg  [CW-1:0] idx;
    reg  [CW-1:0] kv_end;                     // stream index past the stage's KV segment (0: none)
    integer si;
    always @* begin
        hit = 1'b0; hit_res = 1'b0; hit_hbm = 1'b0; idx = 0; kv_end = 0;
        for (si = 0; si < NSEG; si = si + 1) begin
            if (seg_kind[si*2 +: 2] == 2'd3) kv_end = seg_sidx[si*CW +: CW] + CW'(seg_len[si*24 +: 24]);
            if ((seg_kind[si*2 +: 2] == 2'd1 || seg_kind[si*2 +: 2] == 2'd2) &&
                int8_wrom_addr >= seg_base[si*24 +: 24] && int8_wrom_addr < seg_base[si*24 +: 24] + seg_len[si*24 +: 24]) begin
                hit = 1'b1;
                hit_res = (seg_kind[si*2 +: 2] == 2'd2);
                hit_hbm = (seg_kind[si*2 +: 2] == 2'd1);
                idx = seg_sidx[si*CW +: CW] + CW'(int8_wrom_addr - seg_base[si*24 +: 24]);
            end
        end
    end
    wire w_ready = !int8_wrom_re || hit_res || (hit_hbm && idx < a_bin);
    assign hb_me_ok = !rst_n || w_ready;
    assign hb_kv_ok = (kv_end == 0) || (kv_end <= a_bin);
    // consumed words: the spine's furthest HBM word, less LAGW in flight to the tiles
    // VERIFY: a word counts as consumed on its w_nuse-th read (per-slot use counter, slot = idx mod 4,096)
    reg  [CW-1:0] cmax;
    reg  [2:0]    uses [0:4095];
    reg  [CW-1:0] n_reads;                    // HBM code-word reads (= p x HBM words of the stage)
    wire          w_read = me_clk_en && int8_wrom_re && hit_hbm;
    wire [2:0]    u_now = uses[idx[11:0]];
    wire          last_use = (4'(u_now) + 4'd1 >= w_nuse);
    integer ui;
    assign st_nreads = n_reads;
    reg  [CW-1:0] m_c_gray;                   // the zero-latency simulation model of the release
    reg           m_rel_fault;
    wire [CW-1:0] h_c_gray;                   // the synthesizable release (USE_HW_RELEASE = 1)
    wire          h_rel_fault;
    ot_hbmacc_win_usecount #(.ENABLE(USE_HW_RELEASE), .LAGW(LAGW), .CW(CW)) u_rel (
        .clk(clk), .rst_n(rst_n), .rd_v(w_read), .rd_idx(idx), .nuse(w_nuse), .c_gray(h_c_gray), .rel_fault(h_rel_fault));
    always @* begin
        w_c_gray  = (USE_HW_RELEASE != 0) ? h_c_gray : m_c_gray;
        rel_fault = (USE_HW_RELEASE != 0) ? h_rel_fault : m_rel_fault;
    end
    wire [CW-1:0] c_bin = (cmax > CW'(LAGW)) ? cmax - CW'(LAGW) : 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cmax <= 0; m_c_gray <= 0; hbm_fault <= 1'b0; n_reads <= 0; m_rel_fault <= 1'b0;
            for (ui = 0; ui < 4096; ui = ui + 1) uses[ui] <= 3'd0;
        end else begin
            if (w_read) begin
                n_reads <= n_reads + 1'b1;
                uses[idx[11:0]] <= last_use ? 3'd0 : u_now + 3'd1;
            end
            if (w_read && last_use && idx + 1 > cmax) cmax <= idx + 1;
            if (w_read && idx < c_bin) m_rel_fault <= 1'b1;
            m_c_gray <= c_bin ^ (c_bin >> 1);
            if (int8_wrom_re && !hit) hbm_fault <= 1'b1;      // a code read outside the stage's segments
        end
    // ---- HA8: cycle attribution ---------------------------------------------------------------------
    wire run_nx = (core.st == 2'd2) && core.nx_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st_wwait <= 0; st_kvwait <= 0; st_mm <= 0; st_attn <= 0; st_coll <= 0; st_su <= 0; st_other <= 0; st_last_w <= 0;
        end else begin
            if (int8_wrom_re && !w_ready) st_wwait <= st_wwait + 1;
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
