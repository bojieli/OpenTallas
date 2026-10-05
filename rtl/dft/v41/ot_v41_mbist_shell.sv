`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_mbist_shell: the memory-BIST logic that ot_v41_elem_mbist_top adds, without the element and the
// macros, for area and 1.2 GHz timing: one ot_mbist_ctrl (2 SRAM + 4 ROM), four ROM collars (4096 x 274) and
// two SRAM collars (1r1w 256 x 256, 2 spare rows / 2 spare columns).  Macro and functional sides are ports.
// ---------------------------------------------------------------------------
module ot_v41_mbist_shell (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          bist_start,
    output wire          bist_busy,
    output wire          bist_done,
    output wire          bist_pass,
    output wire [3:0]    sram_status,
    output wire [7:0]    rom_status,
    input  wire [127:0]  rom_exp,
    output wire [127:0]  rom_sig,
    // ROM side, per macro m: functional request in, macro request out, macro word in
    input  wire [3:0]    rf_ce,
    input  wire [47:0]   rf_addr,
    output wire [3:0]    rm_ce,
    output wire [47:0]   rm_addr,
    input  wire [4*274-1:0] rm_rd,
    // SRAM side, per bank b
    input  wire [1:0]    sf_r_ce, input wire [15:0] sf_r_addr, output wire [511:0] sf_rd,
    input  wire [1:0]    sf_w_ce, input wire [15:0] sf_w_addr, input wire [511:0] sf_wd,
    output wire [1:0]    sm_r_ce, output wire [15:0] sm_r_addr, output wire [1:0] sm_w_ce, output wire [15:0] sm_w_addr,
    output wire [511:0]  sm_wd, output wire [511:0] sm_wmask, input wire [511:0] sm_rd,
    output wire [3:0]    sm_rr_en, output wire [27:0] sm_rr_addr, output wire [3:0] sm_cr_en, output wire [31:0] sm_cr_sel,
    input  wire          rep_scan_en, input wire rep_scan_in, output wire rep_scan_out
);
    localparam integer AMAX = 12, DMAX = 256, RMAX = 7, CMAX = 8;
    wire [1:0] t_sel, rep_clear, rep_load, c_fail;
    wire [2*DMAX-1:0] c_failvec;
    wire [2*RMAX-1:0] c_row;
    wire t_req, t_we, t_pol, rom_clear, rom_req;
    wire [1:0] t_bg, rr_en, cr_en;
    wire [AMAX-1:0] t_addr, rom_addr;
    wire [2*RMAX-1:0] rr_addr;
    wire [2*CMAX-1:0] cr_sel;
    wire [3:0] rom_sel, rom_match;
    ot_mbist_ctrl #(.N_SRAM(2), .N_ROM(4), .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX), .NSR(2), .NSC(2), .E(6),
                    .SRAM_WORDS({2{32'd256}}), .ROM_WORDS({4{32'd4096}})) u_bist (
        .clk(clk), .rst_n(rst_n), .start(bist_start), .hold(1'b0), .busy(bist_busy), .done(bist_done), .pass(bist_pass),
        .cfg_we(1'b0), .cfg_addr(4'd0), .cfg_wdata(16'd0), .cfg_rdata(), .sram_status(sram_status), .rom_status(rom_status),
        .t_sel(t_sel), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
        .c_fail(c_fail), .c_failvec(c_failvec), .c_row(c_row), .rep_clear(rep_clear), .rep_load(rep_load),
        .rep_rr_en(rr_en), .rep_rr_addr(rr_addr), .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
        .rom_sel(rom_sel), .rom_clear(rom_clear), .rom_req(rom_req), .rom_addr(rom_addr), .rom_match(rom_match),
        .dbg_bira_events(), .dbg_bira_must_cols(), .dbg_bira_overflow());
    genvar m;
    generate for (m = 0; m < 4; m = m + 1) begin : g_rom
        ot_mbist_rom_collar_par #(.WORDS(4096), .DW(274), .AMAX(AMAX)) u_rc (
            .clk(clk), .rst_n(rst_n), .f_ce(rf_ce[m]), .f_addr(rf_addr[12*m +: 12]), .f_rd(),
            .m_ce(rm_ce[m]), .m_addr(rm_addr[12*m +: 12]), .m_rd(rm_rd[274*m +: 274]),
            .t_en(rom_sel[m]), .t_clear(rom_clear), .t_req(rom_req), .t_addr(rom_addr), .exp_sig(rom_exp[32*m +: 32]),
            .sig(rom_sig[32*m +: 32]), .sig_match(rom_match[m]), .sig_busy());
    end endgenerate
    wire [2:0] scan;
    assign scan[0] = rep_scan_in;
    assign rep_scan_out = scan[2];
    generate for (m = 0; m < 2; m = m + 1) begin : g_kv
        ot_mbist_sram_collar #(.PORTS(1), .WORDS(256), .DW(256), .MUX(2), .NSR(2), .NSC(2),
                               .AMAX(AMAX), .DMAX(DMAX), .RMAX(RMAX), .CMAX(CMAX), .NSRB(2), .NSCB(2)) u_col (
            .clk(clk), .rst_n(rst_n),
            .f_r_ce(sf_r_ce[m]), .f_r_addr(sf_r_addr[8*m +: 8]), .f_rd(sf_rd[256*m +: 256]),
            .f_w_ce(sf_w_ce[m]), .f_w_addr(sf_w_addr[8*m +: 8]), .f_wd(sf_wd[256*m +: 256]), .f_wmask({256{1'b1}}),
            .m_ce(), .m_we(), .m_addr(), .m_r_ce(sm_r_ce[m]), .m_r_addr(sm_r_addr[8*m +: 8]),
            .m_w_ce(sm_w_ce[m]), .m_w_addr(sm_w_addr[8*m +: 8]), .m_wd(sm_wd[256*m +: 256]), .m_wmask(sm_wmask[256*m +: 256]),
            .m_rd(sm_rd[256*m +: 256]), .m_rr_en(sm_rr_en[2*m +: 2]), .m_rr_addr(sm_rr_addr[14*m +: 14]),
            .m_cr_en(sm_cr_en[2*m +: 2]), .m_cr_sel(sm_cr_sel[16*m +: 16]),
            .t_en(t_sel[m]), .t_req(t_req), .t_we(t_we), .t_addr(t_addr), .t_pol(t_pol), .t_bg(t_bg),
            .c_fail(c_fail[m]), .c_failvec(c_failvec[m*DMAX +: DMAX]), .c_row(c_row[m*RMAX +: RMAX]),
            .rep_clear(rep_clear[m]), .rep_load(rep_load[m]), .rep_rr_en(rr_en), .rep_rr_addr(rr_addr),
            .rep_cr_en(cr_en), .rep_cr_sel(cr_sel),
            .rep_shift_en(rep_scan_en), .rep_si(scan[m]), .rep_so(scan[m + 1]), .rep_q());
    end endgenerate
endmodule
