`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MBIST test collar for one compiled SRAM macro (tools/mem_compiler/sram_gen.py).
//
// * Functional path: a pure combinational pass-through while t_en is low --
//   no register, no added cycle.  f_r_* is the read request, f_w_* the write
//   request.  PORTS = 0 (1RW macro): ce = f_r_ce | f_w_ce, we = f_w_ce, and the
//   address is the write address when writing (the functional user must not
//   read and write a 1RW macro in the same cycle).  PORTS = 1 (1R1W macro):
//   the read and write ports map straight through.
// * Test path (t_en high, driven by ot_mbist_ctrl): one operation per cycle,
//   t_req/t_we/t_addr/t_pol/t_bg.  The collar builds the data from the
//   background t_bg computed on the PHYSICAL array (data bit b of address a
//   with column select s = a % MUX lies in physical row a / MUX and physical
//   column b * MUX + s):
//       0 solid          0
//       1 checkerboard   (row ^ column) & 1
//       2 row stripe     row & 1
//       3 column stripe  column & 1
//   XOR t_pol.  A read is compared one cycle after it is issued (when rd_out
//   is valid) and the result registered: c_fail / c_failvec (failing data
//   bits, zero-padded to DMAX) / c_row (physical row, zero-padded to RMAX) are
//   valid two cycles after the issuing t_req.
// * Repair register: rr_en[NSR], rr_addr[NSR*RA], cr_en[NSC], cr_sel[NSC*CB],
//   exactly the macro's repair pins.  Loaded in parallel from the BIRA
//   broadcast (rep_load), cleared by rep_clear, and shifted as a scan chain
//   (rep_shift_en, rep_si -> rep_so; LSB of {cr_sel, cr_en, rr_addr, rr_en}
//   first) for fuse read-out after test and fuse load at boot.  rep_q shows
//   the whole register.
// ---------------------------------------------------------------------------
// Lint waiver: the test and repair buses are sized for the widest macro on the
// shared controller; each collar reads only its own slice (UNUSED on the rest).
// verilator lint_off UNUSED
module ot_mbist_sram_collar #(
    parameter integer PORTS = 0,          // 0: 1RW macro, 1: 1R1W macro
    parameter integer WORDS = 256,
    parameter integer DW    = 64,
    parameter integer MUX   = 4,
    parameter integer NSR   = 2,          // spare rows of the macro (0 allowed)
    parameter integer NSC   = 2,          // spare IO columns of the macro (0 allowed)
    parameter integer AMAX  = 16,         // test-bus address width
    parameter integer DMAX  = 128,        // test-bus fail-vector width (>= DW)
    parameter integer RMAX  = 16,         // test-bus row width (>= RA)
    parameter integer CMAX  = 8,          // BIRA column-index width (>= CB)
    parameter integer NSRB  = 2,          // BIRA broadcast spare rows (>= NSR)
    parameter integer NSCB  = 2,          // BIRA broadcast spare columns (>= NSC)
    parameter integer AW    = (WORDS <= 2) ? 1 : $clog2(WORDS),
    parameter integer ROWS  = WORDS / MUX,
    parameter integer RA    = (ROWS <= 2) ? 1 : $clog2(ROWS),
    parameter integer CB    = (DW <= 2) ? 1 : $clog2(DW),
    parameter integer LS    = (MUX <= 1) ? 0 : $clog2(MUX),
    parameter integer NSR1  = (NSR > 0) ? NSR : 1,
    parameter integer NSC1  = (NSC > 0) ? NSC : 1,
    parameter integer REPW  = NSR + NSR * RA + NSC + NSC * CB,
    parameter integer REPW1 = (REPW > 0) ? REPW : 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // functional side
    input  wire                 f_r_ce,
    input  wire [AW-1:0]        f_r_addr,
    output wire [DW-1:0]        f_rd,
    input  wire                 f_w_ce,
    input  wire [AW-1:0]        f_w_addr,
    input  wire [DW-1:0]        f_wd,
    input  wire [DW-1:0]        f_wmask,
    // macro side (1RW uses m_ce/m_we/m_addr; 1R1W uses m_r_* / m_w_*)
    output wire                 m_ce,
    output wire                 m_we,
    output wire [AW-1:0]        m_addr,
    output wire                 m_r_ce,
    output wire [AW-1:0]        m_r_addr,
    output wire                 m_w_ce,
    output wire [AW-1:0]        m_w_addr,
    output wire [DW-1:0]        m_wd,
    output wire [DW-1:0]        m_wmask,
    input  wire [DW-1:0]        m_rd,
    output wire [NSR1-1:0]      m_rr_en,
    output wire [NSR1*RA-1:0]   m_rr_addr,
    output wire [NSC1-1:0]      m_cr_en,
    output wire [NSC1*CB-1:0]   m_cr_sel,
    // test bus from the controller
    input  wire                 t_en,
    input  wire                 t_req,
    input  wire                 t_we,
    input  wire [AMAX-1:0]      t_addr,
    input  wire                 t_pol,
    input  wire [1:0]           t_bg,
    output reg                  c_fail,
    output reg  [DMAX-1:0]      c_failvec,
    output reg  [RMAX-1:0]      c_row,
    // repair register
    input  wire                 rep_clear,
    input  wire                 rep_load,
    input  wire [NSRB-1:0]      rep_rr_en,
    input  wire [NSRB*RMAX-1:0] rep_rr_addr,
    input  wire [NSCB-1:0]      rep_cr_en,
    input  wire [NSCB*CMAX-1:0] rep_cr_sel,
    input  wire                 rep_shift_en,
    input  wire                 rep_si,
    output wire                 rep_so,
    output wire [REPW1-1:0]     rep_q
);
    // ---- background pattern for one address --------------------------------
    function automatic [DW-1:0] pattern(input [AMAX-1:0] a, input pol, input [1:0] bg);
        integer b;
        reg [AMAX-1:0] row;
        reg rp, cp;
        begin
            row = a >> LS;
            rp = row[0];
            for (b = 0; b < DW; b = b + 1) begin
                // physical column b*MUX + s: its parity is s[0] for MUX >= 2, else b[0]
                if (MUX >= 2) cp = a[0];
                else cp = b[0];
                case (bg)
                    2'd0: pattern[b] = pol;
                    2'd1: pattern[b] = pol ^ rp ^ cp;
                    2'd2: pattern[b] = pol ^ rp;
                    default: pattern[b] = pol ^ cp;
                endcase
            end
        end
    endfunction

    wire [DW-1:0] t_data = pattern(t_addr, t_pol, t_bg);
    wire [AW-1:0] t_a = t_addr[AW-1:0];
    wire t_rd = t_en & t_req & ~t_we;
    wire t_wr = t_en & t_req & t_we;

    generate
        if (PORTS == 0) begin : g_1rw
            assign m_ce   = t_en ? t_req : (f_r_ce | f_w_ce);
            assign m_we   = t_en ? t_we  : f_w_ce;
            assign m_addr = t_en ? t_a   : (f_w_ce ? f_w_addr : f_r_addr);
            assign m_r_ce = 1'b0; assign m_r_addr = {AW{1'b0}};
            assign m_w_ce = 1'b0; assign m_w_addr = {AW{1'b0}};
        end else begin : g_1r1w
            assign m_r_ce   = t_en ? t_rd : f_r_ce;
            assign m_r_addr = t_en ? t_a  : f_r_addr;
            assign m_w_ce   = t_en ? t_wr : f_w_ce;
            assign m_w_addr = t_en ? t_a  : f_w_addr;
            assign m_ce = 1'b0; assign m_we = 1'b0; assign m_addr = {AW{1'b0}};
        end
    endgenerate
    assign m_wd    = t_en ? t_data : f_wd;
    assign m_wmask = t_en ? {DW{1'b1}} : f_wmask;
    assign f_rd    = m_rd;

    // ---- compare one cycle after the read -----------------------------------
    reg          cmp_v;
    reg [DW-1:0] cmp_exp;
    reg [RA-1:0] cmp_row;
    wire [DW-1:0] diff = m_rd ^ cmp_exp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cmp_v <= 1'b0; cmp_exp <= {DW{1'b0}}; cmp_row <= {RA{1'b0}};
            c_fail <= 1'b0; c_failvec <= {DMAX{1'b0}}; c_row <= {RMAX{1'b0}};
        end else begin
            cmp_v <= t_rd;
            if (t_rd) begin
                cmp_exp <= t_data;
                cmp_row <= t_addr[RA+LS-1:LS];
            end
            c_fail <= cmp_v && (diff != {DW{1'b0}});
            c_failvec <= {DMAX{1'b0}};
            c_failvec[DW-1:0] <= cmp_v ? diff : {DW{1'b0}};
            c_row <= {RMAX{1'b0}};
            c_row[RA-1:0] <= cmp_row;
        end
    end

    // ---- repair register ----------------------------------------------------
    generate
        if (REPW > 0) begin : g_rep
            reg [REPW-1:0] rep;
            wire [REPW-1:0] load_word;
            genvar k;
            for (k = 0; k < NSR; k = k + 1) begin : g_r
                assign load_word[k] = rep_rr_en[k];
                assign load_word[NSR + k*RA +: RA] = rep_rr_addr[k*RMAX +: RA];
            end
            for (k = 0; k < NSC; k = k + 1) begin : g_c
                assign load_word[NSR + NSR*RA + k] = rep_cr_en[k];
                assign load_word[NSR + NSR*RA + NSC + k*CB +: CB] = rep_cr_sel[k*CMAX +: CB];
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) rep <= {REPW{1'b0}};
                else if (rep_clear) rep <= {REPW{1'b0}};
                else if (rep_load) rep <= load_word;
                else if (rep_shift_en) rep <= {rep_si, rep[REPW-1:1]};
            end
            assign rep_so = rep[0];
            assign rep_q = rep;
            if (NSR > 0) begin : g_ro
                assign m_rr_en = rep[NSR-1:0];
                assign m_rr_addr = rep[NSR +: NSR*RA];
            end else begin : g_rn
                assign m_rr_en = 1'b0;
                assign m_rr_addr = {RA{1'b0}};
            end
            if (NSC > 0) begin : g_co
                assign m_cr_en = rep[NSR + NSR*RA +: NSC];
                assign m_cr_sel = rep[NSR + NSR*RA + NSC +: NSC*CB];
            end else begin : g_cn
                assign m_cr_en = 1'b0;
                assign m_cr_sel = {CB{1'b0}};
            end
        end else begin : g_norep
            assign rep_so = rep_si;
            assign rep_q = 1'b0;
            assign m_rr_en = 1'b0; assign m_rr_addr = {RA{1'b0}};
            assign m_cr_en = 1'b0; assign m_cr_sel = {CB{1'b0}};
        end
    endgenerate
endmodule
// verilator lint_on UNUSED
