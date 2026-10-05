`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_elem_mbist_top: memory BIST vehicle for the DeepSeek-V4.1 ROM S81 die (default-off successor).
//
// One shared ot_mbist_ctrl tests, one macro at a time:
//   * the four ot_rom_4096x274_m8 weight-ROM macros of one q pair element (NB 2 x ping-pong), through the
//     ROM collars of the generated successor ot_v41_rom_elem_qp_mb_w10: a full address sweep folded into a
//     CRC-32 per macro (tools/mem_compiler/ecc.py signature) compared with the personalisation's expected
//     signature (mb_exp: fuse / CSR word per macro);
//   * NKV KV staging banks (ot_sram_1r1w_256x256_m2_r2c2, the attention staging / compressed-KV fetch macro
//     of the S81 layer die) through ot_mbist_sram_collar: March C- with BIRA and spare-row / spare-column
//     repair; the repair registers form one scan chain (rep_scan_*) for fuse read-out and boot load.
// The q element's ports are those of ot_v41_rom_elem_q_qp_w10 (same tie-offs), so with bist_start never
// asserted the element is cycle- and bit-identical to the pinned element (the collars are pass-throughs and
// the ICG enable is ORed with a constant 0).  While the BIST runs (bist_busy) the element ICG is held open.
// The KV banks' functional port is the registered boundary of ot_chip_v41x_attn_sram_bank_phy.
// ---------------------------------------------------------------------------
module ot_v41_elem_mbist_top #(
    parameter integer NB = 2,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 1,
    parameter integer PP = 1,
    parameter integer QTIMING_FIX = 1,
    parameter integer QPIPE = 1,
    parameter integer QP_XS = 1,
    parameter integer QP_CAP = 0,
    parameter integer QP_P1 = 1,
    parameter integer QP_CSAM = 10,
    parameter integer NKV = 2,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    // q element (ot_v41_rom_elem_q_qp_w10 ports)
    input  wire         cfg_v,
    input  wire [4:0]   cfg_a,
    input  wire [47:0]  cfg_d,
    input  wire         go,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    output wire [NB-1:0]    pv,
    output wire [32*NB-1:0] pval,
    output wire [16*NB-1:0] prow,
    output wire [5*NB-1:0]  pseg,
    output wire [5*NB-1:0]  pnseg,
    output wire [NB-1:0]    perr,
    output wire [3*NB-1:0]  ppos,
    output wire         busy,
    output wire         fault,
    // KV staging banks (functional)
    input  wire [NKV-1:0]     kv_we,
    input  wire [NKV*8-1:0]   kv_waddr,
    input  wire [NKV*256-1:0] kv_wdata,
    input  wire [NKV*8-1:0]   kv_raddr,
    output reg  [NKV*256-1:0] kv_rd,
    // memory BIST (TAP / CSR side)
    input  wire               bist_rst_n,
    input  wire               bist_start,
    output wire               bist_busy,
    output wire               bist_done,
    output wire               bist_pass,
    output wire [2*NKV-1:0]   bist_sram_status,
    output wire [2*2*NB-1:0]  bist_rom_status,
    input  wire [64*NB-1:0]   rom_exp_sig,
    output wire [64*NB-1:0]   rom_sig,
    input  wire               rep_scan_en,
    input  wire               rep_scan_in,
    output wire               rep_scan_out
);
    localparam integer NR = 2 * NB;
    localparam integer AMAX = 12, DMAX = 256, RMAX = 7, CMAX = 8;

    wire [NKV-1:0] t_sel, rep_clear, rep_load, c_fail;
    wire [NKV*DMAX-1:0] c_failvec;
    wire [NKV*RMAX-1:0] c_row;
    wire t_req, t_we, t_pol;
    wire [1:0] t_bg;
    wire [AMAX-1:0] t_addr, rom_addr;
    wire [1:0] rr_en, cr_en;
    wire [2*RMAX-1:0] rr_addr;
    wire [2*CMAX-1:0] cr_sel;
    wire rom_clear, rom_req;
    wire [NR-1:0] rom_sel, rom_match;

    ot_mbist_ctrl #(.N_SRAM(NKV), .N_ROM(NR), .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                    .NSR(2), .NSC(2), .E(6),
                    .SRAM_WORDS({NKV{32'd256}}), .ROM_WORDS({NR{32'd4096}})) u_bist (
        .clk(clk), .rst_n(bist_rst_n), .start(bist_start), .hold(1'b0),
        .busy(bist_busy), .done(bist_done), .pass(bist_pass),
        .cfg_we(1'b0), .cfg_addr(4'd0), .cfg_wdata(16'd0), .cfg_rdata(),
        .sram_status(bist_sram_status), .rom_status(bist_rom_status),
        .t_sel(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c_fail), .c_failvec(c_failvec), .c_row(c_row),
        .rep_clear(rep_clear), .rep_load(rep_load), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
        .rom_sel(rom_sel), .rom_clear(rom_clear), .rom_req(rom_req), .rom_addr(rom_addr),
        .rom_match(rom_match),
        .dbg_bira_events(), .dbg_bira_must_cols(), .dbg_bira_overflow());

    // ---- q pair element: ROM collars inside the successor --------------------------------------------
    ot_v41_rom_elem_qp_mb_w10 #(.QTIMING_FIX(QTIMING_FIX), .QPIPE(QPIPE), .QP_XS(QP_XS), .QP_CAP(QP_CAP),
        .QP_P1(QP_P1), .QP_CSAM(QP_CSAM), .BF16(0), .NB(NB), .MTP(MTP), .EARLY(EARLY), .FAST(FAST), .PP(PP),
        .INSTANCE(INSTANCE)) u_e (
        .mb_on(bist_busy), .mb_sel(rom_sel), .mb_clear(rom_clear), .mb_req(rom_req), .mb_addr(rom_addr[11:0]),
        .mb_exp(rom_exp_sig), .mb_match(rom_match), .mb_sig(rom_sig), .mb_rst_n(bist_rst_n),
        .clk(clk), .rst_n_pin(rst_n), .cfg_v_pin(cfg_v), .cfg_a_pin(cfg_a), .cfg_d_pin(cfg_d), .go_pin(go), .go_bf_pin(1'b0),
        .xs_v_pin(xs_v), .xs_p_pin(xs_p), .xs_b_pin(xs_b), .xs_sv_pin(xs_sv), .xs_q0_pin(xs_q0), .xs_e0_pin(xs_e0), .xs_q1_pin(xs_q1),
        .xs_e1_pin(xs_e1), .xs_pos_pin(xs_pos), .xb_pos_pin(3'd0), .ppos(ppos), .xb_v_pin(1'b0), .xb_b_pin(3'd0), .xb_sv_pin(4'd0),
        .xb_u_pin(32'd0), .xb_d_pin(1024'd0),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr), .busy(busy), .fault(fault));

    // ---- KV staging banks ------------------------------------------------------------------------------
    wire [NKV:0] scan;
    assign scan[0] = rep_scan_in;
    assign rep_scan_out = scan[NKV];
    genvar k;
    generate for (k = 0; k < NKV; k = k + 1) begin : g_kv
        reg we_q;
        reg [7:0] wa_q, ra_q;
        reg [255:0] wd_q;
        wire [255:0] rd_f;
        always @(posedge clk) begin
            we_q <= kv_we[k]; wa_q <= kv_waddr[8*k +: 8]; wd_q <= kv_wdata[256*k +: 256]; ra_q <= kv_raddr[8*k +: 8];
            kv_rd[256*k +: 256] <= rd_f;
        end
        wire m_r_ce, m_w_ce;
        wire [7:0] m_r_addr, m_w_addr;
        wire [255:0] m_wd, m_wmask, m_rd;
        wire [1:0] m_rr_en, m_cr_en;
        wire [13:0] m_rr_addr;
        wire [15:0] m_cr_sel;
        ot_mbist_sram_collar #(.PORTS(1), .WORDS(256), .DW(256), .MUX(2), .NSR(2), .NSC(2),
                               .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX), .NSRB(2), .NSCB(2)) u_col (
            .clk(clk), .rst_n(bist_rst_n),
            .f_r_ce(1'b1), .f_r_addr(ra_q), .f_rd(rd_f),
            .f_w_ce(we_q), .f_w_addr(wa_q), .f_wd(wd_q), .f_wmask({256{1'b1}}),
            .m_ce(), .m_we(), .m_addr(), .m_r_ce(m_r_ce), .m_r_addr(m_r_addr),
            .m_w_ce(m_w_ce), .m_w_addr(m_w_addr), .m_wd(m_wd), .m_wmask(m_wmask), .m_rd(m_rd),
            .m_rr_en(m_rr_en), .m_rr_addr(m_rr_addr), .m_cr_en(m_cr_en), .m_cr_sel(m_cr_sel),
            .t_en(t_sel[k]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
            .c_fail(c_fail[k]), .c_failvec(c_failvec[k*DMAX +: DMAX]), .c_row(c_row[k*RMAX +: RMAX]),
            .rep_clear(rep_clear[k]), .rep_load(rep_load[k]), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
            .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
            .rep_shift_en(rep_scan_en), .rep_si(scan[k]), .rep_so(scan[k + 1]), .rep_q());
        ot_sram_1r1w_256x256_m2_r2c2 u_mem (
            .clk(clk), .r_ce_in(m_r_ce), .r_addr_in(m_r_addr), .rd_out(m_rd),
            .w_ce_in(m_w_ce), .w_addr_in(m_w_addr), .wd_in(m_wd), .w_mask_in(m_wmask),
            .rr_en(m_rr_en), .rr_addr(m_rr_addr), .cr_en(m_cr_en), .cr_sel(m_cr_sel));
    end endgenerate
endmodule
