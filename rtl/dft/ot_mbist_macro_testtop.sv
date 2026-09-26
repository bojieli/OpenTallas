`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Place-and-route test top for the ASAP7 compiled memory macros with their
// self-test: one 1RW SRAM hard macro (ot_sram_1rw_256x64_m4_r2c2, 2 spare rows
// and 2 spare IO columns) behind an ot_mbist_sram_collar, one via-programmed
// ROM hard macro (ot_rom_1024x72_m8) behind an ot_mbist_rom_collar with the
// (72,64) SECDED decoder on its read path, and ONE shared ot_mbist_ctrl (March
// C-, BIRA, ROM signature).  The functional ports are brought out so nothing
// is optimised away; in synthesis the two macros are blackboxes resolved from
// their compiler liberty and placed as hard macros from their LEF
// (tools/run_abi3_physical.py --macro-view).
// ---------------------------------------------------------------------------
module ot_mbist_macro_testtop (
    input  wire         clk,
    input  wire         rst_n,
    // SRAM functional port (1RW)
    input  wire         s_ce,
    input  wire         s_we,
    input  wire [7:0]   s_addr,
    input  wire [63:0]  s_wd,
    input  wire [63:0]  s_wmask,
    output wire [63:0]  s_rd,
    // ROM functional port, SECDED-corrected
    input  wire         r_ce,
    input  wire [9:0]   r_addr,
    output wire [63:0]  r_data,
    output wire         r_corrected,
    output wire         r_uncorrectable,
    // BIST
    input  wire         bist_start,
    output wire         bist_busy,
    output wire         bist_done,
    output wire         bist_pass,
    output wire [1:0]   bist_sram_status,
    output wire [1:0]   bist_rom_status,
    input  wire [31:0]  rom_exp_sig,
    input  wire         cfg_we,
    input  wire [3:0]   cfg_addr,
    input  wire [15:0]  cfg_wdata,
    output wire [15:0]  cfg_rdata,
    // repair register scan chain (fuse read-out / boot load)
    input  wire         rep_scan_en,
    input  wire         rep_scan_in,
    output wire         rep_scan_out
);
    localparam integer AMAX = 10, DMAX = 64, RMAX = 6, CMAX = 6;

    wire t_sel, t_req, t_we, t_pol, c_fail, rep_clear, rep_load;
    wire [1:0] t_bg;
    wire [AMAX-1:0] t_addr, rom_addr;
    wire [DMAX-1:0] c_failvec;
    wire [RMAX-1:0] c_row;
    wire [1:0] rr_en, cr_en;
    wire [2*RMAX-1:0] rr_addr;
    wire [2*CMAX-1:0] cr_sel;
    wire rom_sel, rom_clear, rom_req, rom_match;

    ot_mbist_ctrl #(.N_SRAM(1), .N_ROM(1), .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX),
                    .NSR(2), .NSC(2), .E(6), .SRAM_WORDS(32'd256), .ROM_WORDS(32'd1024)) u_ctrl (
        .clk(clk), .rst_n(rst_n), .start(bist_start), .hold(1'b0),
        .busy(bist_busy), .done(bist_done), .pass(bist_pass),
        .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_wdata(cfg_wdata), .cfg_rdata(cfg_rdata),
        .sram_status(bist_sram_status), .rom_status(bist_rom_status),
        .t_sel(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c_fail), .c_failvec(c_failvec), .c_row(c_row),
        .rep_clear(rep_clear), .rep_load(rep_load), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
        .rom_sel(rom_sel), .rom_clear(rom_clear), .rom_req(rom_req), .rom_addr(rom_addr),
        .rom_match(rom_match),
        .dbg_bira_events(), .dbg_bira_must_cols(), .dbg_bira_overflow());

    // ---- SRAM hard macro behind its collar ----
    wire m_ce, m_we;
    wire [7:0] m_addr;
    wire [63:0] m_wd, m_wmask, m_rd;
    wire [1:0] m_rr_en, m_cr_en;
    wire [11:0] m_rr_addr, m_cr_sel;
    ot_mbist_sram_collar #(.PORTS(0), .WORDS(256), .DW(64), .MUX(4), .NSR(2), .NSC(2),
                           .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX), .NSRB(2), .NSCB(2)) u_scol (
        .clk(clk), .rst_n(rst_n),
        .f_r_ce(s_ce), .f_r_addr(s_addr), .f_rd(s_rd), .f_w_ce(s_we), .f_w_addr(s_addr), .f_wd(s_wd),
        .f_wmask(s_wmask),
        .m_ce(m_ce), .m_we(m_we), .m_addr(m_addr), .m_r_ce(), .m_r_addr(), .m_w_ce(), .m_w_addr(),
        .m_wd(m_wd), .m_wmask(m_wmask), .m_rd(m_rd),
        .m_rr_en(m_rr_en), .m_rr_addr(m_rr_addr), .m_cr_en(m_cr_en), .m_cr_sel(m_cr_sel),
        .t_en(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c_fail), .c_failvec(c_failvec), .c_row(c_row),
        .rep_clear(rep_clear), .rep_load(rep_load), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
        .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
        .rep_shift_en(rep_scan_en), .rep_si(rep_scan_in), .rep_so(rep_scan_out), .rep_q());
    ot_sram_1rw_256x64_m4_r2c2 u_sram (
        .clk(clk), .ce_in(m_ce), .we_in(m_we), .addr_in(m_addr), .wd_in(m_wd), .w_mask_in(m_wmask),
        .rd_out(m_rd), .rr_en(m_rr_en), .rr_addr(m_rr_addr), .cr_en(m_cr_en), .cr_sel(m_cr_sel));

    // ---- ROM hard macro behind its collar, SECDED on the read path ----
    wire rm_ce;
    wire [9:0] rm_addr;
    wire [71:0] rm_rd, r_cw;
    ot_mbist_rom_collar #(.WORDS(1024), .DW(72), .AMAX(AMAX)) u_rcol (
        .clk(clk), .rst_n(rst_n), .f_ce(r_ce), .f_addr(r_addr), .f_rd(r_cw),
        .m_ce(rm_ce), .m_addr(rm_addr), .m_rd(rm_rd),
        .t_en(rom_sel), .t_clear(rom_clear), .t_req(rom_req), .t_addr(rom_addr),
        .exp_sig(rom_exp_sig), .sig(), .sig_match(rom_match), .sig_busy());
    ot_rom_1024x72_m8 u_rom (.clk(clk), .ce_in(rm_ce), .addr_in(rm_addr), .rd_out(rm_rd));
    ot_rom_secded_dec #(.K(64)) u_dec (.cw(r_cw), .data(r_data), .corrected(r_corrected),
                                       .uncorrectable(r_uncorrectable));
endmodule
