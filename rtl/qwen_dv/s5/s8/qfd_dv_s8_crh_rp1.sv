`timescale 1ns/1ps
// Existing CRH1 half-write semantics recovered from c0f8097f3 qfd_dv_vm. UNCLOSED successor.
// MIF (PATH-QC-RP1-F59 2026-10-25, GEOM-REVIEW F6 amend on f58): MIF=0 = unchanged (the shared pcr_re/pcr_addr pin
// registers drive both banks' r_ce/r_addr through the bank decode, 78-91 um; w_ce from u_twcw/u_twch through 3-4 levels,
// 121/216 um).  MIF=1 = the SRAMIF recipe (qfd_dv_s8x_btab/prog/vmr MIF=1): per-bank pre-decoded macro-interface
// registers r_ce/r_addr/w_ce/w_addr/wd (distinct kff IDs -> distinct kept modules), each driving only its own SRAM's pins
// (anchored at the pin edge by physical/common_flow/macro_pin_flops.tcl).  u_twc* become the shared write relay stage,
// and the bank/lane offsets of the read go through one delayed copy (u_rs), so MIF=1 is exactly MIF=0 delayed by one
// cycle on q (read +1, table write +1, read/write order unchanged); fault unchanged (0 cycles).  MIF=1 also carries the
// f58 c1 control replica u_c1w (same D, +0 cycles) for the W1-region g_cbk consumers.
// PRICE vs MIF=0: CRH read +1, CRH table write +1.  The parent must schedule the +1 on q (static schedule).
module qfd_dv_s8_crh_rp1 #(parameter integer MIF = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [7:0]      cr_re,
    input  wire [8*24-1:0] cr_addr,
    output reg  [8*32-1:0] q,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [23:0]     tw_addr,
    input  wire [511:0]    tw_d,          // [32*(8*bank + lane) +: 32] = this half of table word lane, bank
    output reg             fault
);
    integer l, s, lc;
    genvar gl, gk, bk;
    reg rl0, rl1;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    reg [7:0] pcr_re; reg [8*24-1:0] pcr_addr;
    always @(posedge ck) begin pcr_re <= cr_re; pcr_addr <= cr_addr; end
    reg ptw_we; reg [1:0] ptw_kind; reg [23:0] ptw_addr; reg [511:0] ptw_d;
    always @(posedge ck) begin ptw_we <= tw_we; ptw_kind <= tw_kind; ptw_addr <= tw_addr; ptw_d <= tw_d; end
    wire [511:0] twc_d; wire [9:0] twc_a; wire twc_crw;
    qfd_dv_s8x_kff #(.W(512), .ID(7300)) u_twcd (.ck(ck), .d(ptw_d), .q(twc_d));
    qfd_dv_s8x_kff #(.W(10), .ID(7301)) u_twca (.ck(ck), .d(ptw_addr[9:0]), .q(twc_a));
    qfd_dv_s8x_kff #(.W(1), .ID(7302)) u_twcw (.ck(ck), .d(ptw_we && ptw_kind == 2'd1), .q(twc_crw));
    // Same capture age as twc_a/crw; bank mask is part of actual leaf logic.
    wire [1:0] twc_half;
    qfd_dv_s8x_kff #(.W(2), .ID(7303)) u_twch (.ck(ck), .d(ptw_addr[11:10]), .q(twc_half));
    wire [511:0] cr_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_crb
        wire m_rce, m_we; wire [9:0] m_ra, m_wa; wire [255:0] m_wd;
        if (MIF == 0) begin : g_d
            assign m_rce = pcr_re[0] && pcr_addr[3] == bk[0]; assign m_ra = pcr_addr[4 +: 10];
            assign m_we = twc_crw && (!twc_half[1] || twc_half[0] == bk[0]); assign m_wa = twc_a; assign m_wd = twc_d[256*bk +: 256];
        end else begin : g_r
            // per-bank landing registers, decode in front (distinct IDs: distinct kept modules, never merged)
            qfd_dv_s8x_kff #(.W(1), .ID(7310 + bk)) u_rce (.ck(ck), .d(pcr_re[0] && pcr_addr[3] == bk[0]), .q(m_rce));
            qfd_dv_s8x_kff #(.W(10), .ID(7320 + bk)) u_ra (.ck(ck), .d(pcr_addr[4 +: 10]), .q(m_ra));
            qfd_dv_s8x_kff #(.W(1), .ID(7330 + bk)) u_we (.ck(ck), .d(twc_crw && (!twc_half[1] || twc_half[0] == bk[0])), .q(m_we));
            qfd_dv_s8x_kff #(.W(10), .ID(7340 + bk)) u_wa (.ck(ck), .d(twc_a), .q(m_wa));
            qfd_dv_s8x_kff #(.W(256), .ID(7350 + bk)) u_wd (.ck(ck), .d(twc_d[256*bk +: 256]), .q(m_wd));
        end
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck), .r_ce_in(m_rce), .r_addr_in(m_ra),
            .rd_out(cr_rd[bk*256 +: 256]), .w_ce_in(m_we), .w_addr_in(m_wa), .wd_in(m_wd),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    // bank / lane offsets of the read the SRAMs latch this edge (MIF=1: one cycle later, from a delayed copy)
    wire [24:0] rsel_n;
    assign rsel_n[0] = pcr_addr[3];
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_rsel assign rsel_n[1 + 3*gl +: 3] = pcr_addr[24*gl +: 3]; end endgenerate
    wire [24:0] rsel;
    wire c1_bank, c1_bank_w;
    qfd_dv_s8x_kff #(.W(1), .ID(3400)) u_c1 (.ck(ck), .d(rsel[0]), .q(c1_bank));
    generate if (MIF == 0) begin : g_rs0
        assign rsel = rsel_n;
        assign c1_bank_w = c1_bank;
    end else begin : g_rs1
        qfd_dv_s8x_kff #(.W(25), .ID(7360)) u_rs (.ck(ck), .d(rsel_n), .q(rsel));
        // f58 c1 control replica (same D, same edge) for the W1-region consumers (mask 16'hABBF); +0 cycles
        qfd_dv_s8x_kff #(.W(1), .ID(3401)) u_c1w (.ck(ck), .d(rsel[0]), .q(c1_bank_w));
    end endgenerate
    reg [23:0] c1_off; reg [511:0] ccap;
    always @(posedge ck) begin
        c1_off <= rsel[24:1];
        ccap <= cr_rd;
    end
    wire [255:0] c;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_cbk
        wire bq;
        qfd_dv_s8x_kff #(.W(1), .ID(3500 + gk)) u (.ck(ck), .d(((16'hABBF >> gk) & 16'h1) != 16'h0 ? c1_bank_w : c1_bank), .q(bq));
        assign c[16*gk +: 16] = bq ? ccap[256 + 16*gk +: 16] : ccap[16*gk +: 16];
    end endgenerate
    wire [8*32-1:0] q_n;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_cext
        wire [7:0] dec = 8'd1 << c1_off[3*gl +: 3];
        wire [7:0] oh0, oh1;
        qfd_dv_s8x_kff #(.W(8), .ID(3600 + 2*gl)) u0 (.ck(ck), .d(dec), .q(oh0));
        qfd_dv_s8x_kff #(.W(8), .ID(3601 + 2*gl)) u1 (.ck(ck), .d(dec), .q(oh1));
        reg [31:0] e;
        always @(*) begin
            e = 32'd0;
            for (s = 0; s < 8; s = s + 1) e = e | {({16{oh1[s]}} & c[32*s + 16 +: 16]), ({16{oh0[s]}} & c[32*s +: 16])};
        end
        assign q_n[32*gl +: 32] = e;
    end endgenerate
    always @(posedge ck) q <= q_n;
    function automatic bad_vec(input [7:0] re_, input [8*24-1:0] ad);
        integer kk;
        begin
            bad_vec = 1'b0;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re_[kk] && (ad[24*kk+4 +: 20] != ad[4 +: 20])) bad_vec = 1'b1;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re_[kk] && (ad[24*kk+3] != ad[3])) bad_vec = 1'b1;
            if (re_[0] && (ad[23:14] != 10'd0)) bad_vec = 1'b1;
            if (re_ != 8'd0 && !re_[0]) bad_vec = 1'b1;
        end
    endfunction
    reg rd_bad_q, tw_bad_q, tw_bad_q2;
    always @(posedge ck) begin
        rd_bad_q <= (pcr_re != 8'd0 && (!pcr_re[0] || pcr_addr[23:14] != 10'd0)) ||
                    (pcr_re != 8'd0 && bad_vec(pcr_re, pcr_addr & {8{24'h003FFF}}));
        tw_bad_q <= ptw_we && ((ptw_kind == 2'd0) || (ptw_kind == 2'd1 && (ptw_addr[23:12] != 0 || (!ptw_addr[11] && ptw_addr[10]))) ||
                               (ptw_kind == 2'd2 && (ptw_addr[1:0] != 0 || ptw_addr[23:9] != 0)) ||
                               (ptw_kind == 2'd3 && ptw_addr[23:8] != 0));
        tw_bad_q2 <= tw_bad_q;
    end
    always @(posedge ck or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | rd_bad_q | tw_bad_q2;
endmodule
