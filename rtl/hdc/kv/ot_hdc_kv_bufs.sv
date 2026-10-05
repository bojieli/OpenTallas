`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The KV streamer's on-die buffers (ot_hdc_kv_stream) built from the ASAP7
// compiled macros in physical/asap7_memory_macros (tools/mem_compiler):
//
//   window SRAM  G banks x 2^LWIN words x W*16 bits, one shared read address,
//                one write port per bank            -> G x ot_sram_1r1w_256x256_m2_r2c2
//   tail SRAM    2 banks x 2^TAW words x W*16 bits, lane (16-bit) write mask,
//                independent read address per bank  -> 2 x ot_sram_1r1w_128x256_m1_r2c2
//
// Every macro sits behind an ot_mbist_sram_collar (combinational pass-through
// while not under test) and ONE shared ot_mbist_ctrl runs March C- with BIRA
// and spare row / spare IO-column repair on all of them.  The repair registers
// form one scan chain (rep_scan_*) for fuse read-out and boot load.
//
// The ports are exactly the streamer's window and tail ports (synchronous read,
// data held while the read enable is low, read-before-write on a same-address
// collision), so the streamer and the core see the same cycles as with the
// behavioural arrays of rtl/test/tb_hdc_core_hbm.sv.
//
// tst_tl_*: the test/debug write port in front of the tail collars' functional
// side (used to preload the golden tail tiles before a token).
//
// Macro shapes are fixed: LWIN = 8, TAW = 7, W = 16 (256-bit words).
// ---------------------------------------------------------------------------
module ot_hdc_kv_bufs #(
    parameter integer G    = 4,
    parameter integer W    = 16,
    parameter integer LWIN = 8,
    parameter integer TAW  = 7,
    parameter integer N_M  = G + 2
) (
    input  wire              clk,
    input  wire              rst_n,          // BIST / collar reset
    // window SRAM
    input  wire [G-1:0]      win_we,
    input  wire [G*LWIN-1:0] win_waddr,
    input  wire [G*W*16-1:0] win_wdata,
    input  wire              win_re,
    input  wire [LWIN-1:0]   win_raddr,
    output wire [G*W*16-1:0] win_q,
    // tail SRAM
    input  wire [1:0]        tl_we,
    input  wire [2*TAW-1:0]  tl_waddr,
    input  wire [2*W-1:0]    tl_wmask,
    input  wire [2*W*16-1:0] tl_wdata,
    input  wire [1:0]        tl_re,
    input  wire [2*TAW-1:0]  tl_raddr,
    output wire [2*W*16-1:0] tl_q,
    // tail preload / debug write
    input  wire              tst_tl_en,
    input  wire [1:0]        tst_tl_we,
    input  wire [TAW-1:0]    tst_tl_addr,
    input  wire [2*W*16-1:0] tst_tl_wdata,
    // memory BIST
    input  wire              bist_start,
    output wire              bist_busy,
    output wire              bist_done,
    output wire              bist_pass,
    output wire [2*N_M-1:0]  bist_sram_status,
    input  wire              rep_scan_en,
    input  wire              rep_scan_in,
    output wire              rep_scan_out
);
    localparam integer DW = W * 16;                 // 256
    localparam integer AMAX = 8, DMAX = 256, RMAX = 7, CMAX = 8;

    // ---- shared controller ---------------------------------------------------
    wire [N_M-1:0] t_sel, rep_clear, rep_load, c_fail;
    wire [N_M*DMAX-1:0] c_failvec;
    wire [N_M*RMAX-1:0] c_row;
    wire t_req, t_we, t_pol;
    wire [1:0] t_bg;
    wire [AMAX-1:0] t_addr, rom_addr;
    wire [1:0] rr_en, cr_en;
    wire [2*RMAX-1:0] rr_addr;
    wire [2*CMAX-1:0] cr_sel;
    wire rom_clear, rom_req;
    wire [N_M:0] scan;
    assign scan[0] = rep_scan_in;
    assign rep_scan_out = scan[N_M];
    ot_mbist_ctrl #(.N_SRAM(N_M), .N_ROM(0), .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                    .NSR(2), .NSC(2), .E(6),
                    .SRAM_WORDS({{2{32'd128}}, {G{32'd256}}})) u_bist (
        .clk(clk), .rst_n(rst_n), .start(bist_start), .hold(1'b0),
        .busy(bist_busy), .done(bist_done), .pass(bist_pass),
        .cfg_we(1'b0), .cfg_addr(4'd0), .cfg_wdata(16'd0), .cfg_rdata(),
        .sram_status(bist_sram_status), .rom_status(),
        .t_sel(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c_fail), .c_failvec(c_failvec), .c_row(c_row),
        .rep_clear(rep_clear), .rep_load(rep_load), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
        .rom_sel(), .rom_clear(rom_clear), .rom_req(rom_req), .rom_addr(rom_addr),
        .rom_match(1'b0),
        .dbg_bira_events(), .dbg_bira_must_cols(), .dbg_bira_overflow());

    genvar q, b, l;
    // ---- window SRAM: macros 0 .. G-1 -----------------------------------------
    generate
        for (q = 0; q < G; q = q + 1) begin : g_win
            wire m_r_ce, m_w_ce;
            wire [7:0] m_r_addr, m_w_addr;
            wire [DW-1:0] m_wd, m_wmask, m_rd;
            wire [1:0] m_rr_en, m_cr_en;
            wire [13:0] m_rr_addr;
            wire [15:0] m_cr_sel;
            ot_mbist_sram_collar #(.PORTS(1), .WORDS(256), .DW(DW), .MUX(2), .NSR(2), .NSC(2),
                                   .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                                   .NSRB(2), .NSCB(2)) u_col (
                .clk(clk), .rst_n(rst_n),
                .f_r_ce(win_re), .f_r_addr(win_raddr), .f_rd(win_q[q*DW +: DW]),
                .f_w_ce(win_we[q]), .f_w_addr(win_waddr[q*LWIN +: LWIN]), .f_wd(win_wdata[q*DW +: DW]),
                .f_wmask({DW{1'b1}}),
                .m_ce(), .m_we(), .m_addr(), .m_r_ce(m_r_ce), .m_r_addr(m_r_addr),
                .m_w_ce(m_w_ce), .m_w_addr(m_w_addr), .m_wd(m_wd), .m_wmask(m_wmask), .m_rd(m_rd),
                .m_rr_en(m_rr_en), .m_rr_addr(m_rr_addr), .m_cr_en(m_cr_en), .m_cr_sel(m_cr_sel),
                .t_en(t_sel[q]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
                .c_fail(c_fail[q]), .c_failvec(c_failvec[q*DMAX +: DMAX]), .c_row(c_row[q*RMAX +: RMAX]),
                .rep_clear(rep_clear[q]), .rep_load(rep_load[q]), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
                .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
                .rep_shift_en(rep_scan_en), .rep_si(scan[q]), .rep_so(scan[q + 1]), .rep_q());
            ot_sram_1r1w_256x256_m2_r2c2 u_sram (
                .clk(clk), .r_ce_in(m_r_ce), .r_addr_in(m_r_addr), .rd_out(m_rd),
                .w_ce_in(m_w_ce), .w_addr_in(m_w_addr), .wd_in(m_wd), .w_mask_in(m_wmask),
                .rr_en(m_rr_en), .rr_addr(m_rr_addr), .cr_en(m_cr_en), .cr_sel(m_cr_sel));
        end

        // ---- tail SRAM: macros G, G+1 -------------------------------------------
        for (b = 0; b < 2; b = b + 1) begin : g_tl
            localparam integer MI = G + b;
            wire [DW-1:0] lane_mask;
            for (l = 0; l < W; l = l + 1) begin : g_lane
                assign lane_mask[l*16 +: 16] = {16{tl_wmask[b*W + l]}};
            end
            wire           f_w_ce = tst_tl_en ? tst_tl_we[b] : tl_we[b];
            wire [TAW-1:0] f_w_a  = tst_tl_en ? tst_tl_addr : tl_waddr[b*TAW +: TAW];
            wire [DW-1:0]  f_wd   = tst_tl_en ? tst_tl_wdata[b*DW +: DW] : tl_wdata[b*DW +: DW];
            wire [DW-1:0]  f_wm   = tst_tl_en ? {DW{1'b1}} : lane_mask;
            wire m_r_ce, m_w_ce;
            wire [6:0] m_r_addr, m_w_addr;
            wire [DW-1:0] m_wd, m_wmask, m_rd;
            wire [1:0] m_rr_en, m_cr_en;
            wire [13:0] m_rr_addr;
            wire [15:0] m_cr_sel;
            ot_mbist_sram_collar #(.PORTS(1), .WORDS(128), .DW(DW), .MUX(1), .NSR(2), .NSC(2),
                                   .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                                   .NSRB(2), .NSCB(2)) u_col (
                .clk(clk), .rst_n(rst_n),
                .f_r_ce(tl_re[b]), .f_r_addr(tl_raddr[b*TAW +: TAW]), .f_rd(tl_q[b*DW +: DW]),
                .f_w_ce(f_w_ce), .f_w_addr(f_w_a), .f_wd(f_wd), .f_wmask(f_wm),
                .m_ce(), .m_we(), .m_addr(), .m_r_ce(m_r_ce), .m_r_addr(m_r_addr),
                .m_w_ce(m_w_ce), .m_w_addr(m_w_addr), .m_wd(m_wd), .m_wmask(m_wmask), .m_rd(m_rd),
                .m_rr_en(m_rr_en), .m_rr_addr(m_rr_addr), .m_cr_en(m_cr_en), .m_cr_sel(m_cr_sel),
                .t_en(t_sel[MI]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
                .c_fail(c_fail[MI]), .c_failvec(c_failvec[MI*DMAX +: DMAX]), .c_row(c_row[MI*RMAX +: RMAX]),
                .rep_clear(rep_clear[MI]), .rep_load(rep_load[MI]), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
                .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
                .rep_shift_en(rep_scan_en), .rep_si(scan[MI]), .rep_so(scan[MI + 1]), .rep_q());
            ot_sram_1r1w_128x256_m1_r2c2 u_sram (
                .clk(clk), .r_ce_in(m_r_ce), .r_addr_in(m_r_addr), .rd_out(m_rd),
                .w_ce_in(m_w_ce), .w_addr_in(m_w_addr), .wd_in(m_wd), .w_mask_in(m_wmask),
                .rr_en(m_rr_en), .rr_addr(m_rr_addr), .cr_en(m_cr_en), .cr_sel(m_cr_sel));
        end
    endgenerate
endmodule
