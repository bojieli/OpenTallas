`timescale 1ns/1ps
// =====================================================================================================================
// QW-VM8SPLIT 10-20 (COORD 09:45 DECISION): the slice2 VM (qfd_dv_s5_vm8) SPLIT into hardened SINGLE-ROOT leaves.
// Why: one CTS root over ~700 x 648 um / 15k sinks cannot meet the in-region 80 ps pin-flop spread (vm8b TT 100.3 /
// FF 88.3, vm8c 149 / 131); vm8h (three related roots, direct reg->reg crossings, 18 raw SRAM clock entries) is ruled
// out by the owner 10-20 clock rule (every region crossing lands in a mesochronous fixed-latency ring).
// Partition = the vm8 dataflow cut where NO signal crosses between leaves (zero internal crossings, so the split adds
// no ring of its own): each leaf owns its macros, its pin registers, its reset landing and its own sticky fault.
//   qfd_dv_s8x_vmr  x3  VM replica (a | b | c): 2 macros 1024x256 (banks 0/1) + a FULL copy of the vm7 write merge
//                       (the write decode is replicated per replica instead of crossing into the replica)
//   qfd_dv_s8x_crom x1  CROM 2 banks x {lo, hi} (4 macros 1024x256) + table-write landing + the table-write fault
//   qfd_dv_s8x_su   x1  BTAB SU copy (4 x 128x256) + PROG 2 banks x {lo, hi} (4 x 256x256)  [= btab + prog]
//   fallback partition (kit pair btab / prog): qfd_dv_s8x_btab + qfd_dv_s8x_prog as two leaves instead of su.
// Every leaf is edge-for-edge the vm8 logic it holds (same pin registers, same kept copies, same stages): the leaf
// composition qfd_dv_s5_vm8x is cycle-identical to qfd_dv_s5_vm8s on every output; fault = OR of the five leaf sticky
// faults (sticky OR distributes: OR_i(f_i | t_i) = (OR f) | (OR t)), which the slice2 consumer ORs after its landing.
// PRICE vs vm8 (static schedule): 0 edges inside the VM (prices = vm8b: reads 2 -> 4, VM write -> read 1 -> 3,
// tw +2, fault +1).  The ring rule's landing latency at the slice2 crossings is the PARENT's (lanes/QW-VM8SPLIT.md).
// Area: +2 decode copies (~2 x 2.1k FF) vs vm8.
// =====================================================================================================================

(* keep_hierarchy = "yes" *) module qfd_dv_s8x_kff #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck) q <= d;
endmodule

// ===================================================================================================== VM replica leaf
module qfd_dv_s8x_vmr #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    // read port (W face)
    input  wire [7:0]      re,
    input  wire [8*24-1:0] addr,
    output reg  [8*32-1:0] q,
    // VM writes (S face)
    input  wire [7:0]      vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire            w16_we,
    input  wire [23:0]     w16_addr,
    input  wire [511:0]    w16_data,
    input  wire            w1_we,
    input  wire [23:0]     w1_addr,
    input  wire [31:0]     w1_data,
    output reg             fault
);
    integer l, b, s, k, lc;   // lc: clocked-block loop only (no shared loop variable between processes)
    genvar gl, gb, gs, gk, bk;
    reg rl0, rl1;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    // ---------------------------------------------------------------- input pin registers
    reg [7:0] pa_re; reg [8*24-1:0] pa_addr;
    always @(posedge ck) begin pa_re <= re; pa_addr <= addr; end
    reg [8*24-1:0] pvm_waddr; reg [8*32-1:0] pvm_wdata;
    reg pw16_we, pw1_we; reg [23:0] pw16_addr, pw1_addr; reg [511:0] pw16_data; reg [31:0] pw1_data;
    always @(posedge ck) begin
        pvm_waddr <= vm_waddr; pvm_wdata <= vm_wdata;
        pw16_we <= w16_we; pw16_addr <= w16_addr; pw16_data <= w16_data;
        pw1_we <= w1_we; pw1_addr <= w1_addr; pw1_data <= w1_data;
    end
    // ---------------------------------------------------------------- VM write decode (vm8 copy; kept window copies)
    wire [9:0] pwin [0:5];
    wire [5:0] su_any_k;
    generate for (gk = 0; gk < 6; gk = gk + 1) begin : g_pwin
        qfd_dv_s8x_kff #(.W(10), .ID(8000 + gk)) u (.ck(ck), .d({vm_we, vm_waddr[23:22]}), .q(pwin[gk]));
        assign su_any_k[gk] = (|pwin[gk][9:2]) && pwin[gk][1:0] == 2'b00;
    end endgenerate
    wire su_any_r = su_any_k[4];
    wire [7:0] su_we_r, su_we_c;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_swe
        assign su_we_r[gl] = su_any_k[gl / 2] && pwin[gl / 2][2 + gl];
        assign su_we_c[gl] = su_any_k[5] && pwin[5][2 + gl];
    end endgenerate
    wire su_bank_r = pvm_waddr[3];
    wire w1_bank_r = pw1_addr[3];
    reg [7:0] off_oh [0:7];
    reg [7:0] hitS [0:7], winS [0:7];
    reg [7:0] anyS;
    reg [7:0] gw1_r [0:1], gmx_r [0:1];
    wire [1:0] sub_r;
    assign sub_r[0] = !pw16_we && su_any_r && !su_bank_r;
    assign sub_r[1] = !pw16_we && su_any_r && su_bank_r;
    wire [1:0] w1b_r;
    assign w1b_r[0] = !pw16_we && pw1_we && !w1_bank_r && !(su_any_r && !su_bank_r);
    assign w1b_r[1] = !pw16_we && pw1_we && w1_bank_r && !(su_any_r && su_bank_r);
    always @(*) begin
        for (l = 0; l < 8; l = l + 1) off_oh[l] = 8'd1 << pvm_waddr[24*l +: 3];
        for (s = 0; s < 8; s = s + 1) begin
            for (l = 0; l < 8; l = l + 1) hitS[s][l] = su_we_r[l] && off_oh[l][s];
            anyS[s] = |hitS[s];
            for (l = 0; l < 8; l = l + 1) begin
                winS[s][l] = hitS[s][l];
`ifdef OT_S8_MUT_WPRI
                for (k = 0; k < l; k = k + 1) if (hitS[s][k]) winS[s][l] = 1'b0;   // bench mutant: EARLIER lane wins
`else
                for (k = l + 1; k < 8; k = k + 1) if (hitS[s][k]) winS[s][l] = 1'b0;
`endif
            end
        end
        for (b = 0; b < 2; b = b + 1)
            for (s = 0; s < 8; s = s + 1) begin
                gw1_r[b][s] = w1b_r[b] && pw1_addr[2:0] == s[2:0];
                gmx_r[b][s] = (sub_r[b] && anyS[s]) || gw1_r[b][s];
            end
    end
    wire [1:0] ssu_r = {su_any_r && su_bank_r, su_any_r && !su_bank_r};
    wire [1:0] sw1_r = {pw1_we && w1_bank_r, pw1_we && !w1_bank_r};
    reg w_coll_r, w_bad_r;
    always @(*) begin
        w_coll_r = 1'b0; w_bad_r = 1'b0;
        if (pw1_we && pw1_addr[23:14] != 10'd0) w_bad_r = 1'b1;
        if (su_any_k[5]) begin
            for (l = 0; l < 8; l = l + 1)
                if (su_we_c[l] && (pvm_waddr[24*l+3 +: 21] != pvm_waddr[3 +: 21] || !su_we_c[0])) w_bad_r = 1'b1;
            if (pvm_waddr[23:14] != 10'd0) w_bad_r = 1'b1;
            if (pw1_we && w1_bank_r == su_bank_r) w_coll_r = 1'b1;
        end
        if (pw16_we) begin
            if (pw16_addr[3:0] != 4'd0 || pw16_addr[23:14] != 10'd0) w_bad_r = 1'b1;
            if (pw1_we || su_any_r) w_coll_r = 1'b1;
        end
    end
    reg  [255:0] l_sud;
    reg  [511:0] l_w16d;
    reg  [31:0]  l_w1d;
    reg  [9:0]   l_r16, l_rsu, l_rw1;
    reg          l_wbad, l_wbad2, l_wbad3;
    always @(posedge ck) begin
        l_sud <= pvm_wdata; l_w16d <= pw16_data; l_w1d <= pw1_data;
        l_r16 <= pw16_addr[13:4]; l_rsu <= pvm_waddr[13:4]; l_rw1 <= pw1_addr[13:4];
        l_wbad <= w_bad_r || w_coll_r; l_wbad2 <= l_wbad; l_wbad3 <= l_wbad2;
    end
    wire [1:0] l_r16w, l_m16, l_ssu, l_sw1;
    qfd_dv_s8x_kff #(.W(2), .ID(900)) u_r16 (.ck(ck), .d({2{pw16_we}}), .q(l_r16w));
    qfd_dv_s8x_kff #(.W(2), .ID(901)) u_ssu (.ck(ck), .d(ssu_r), .q(l_ssu));
    qfd_dv_s8x_kff #(.W(2), .ID(902)) u_sw1 (.ck(ck), .d(sw1_r), .q(l_sw1));
    qfd_dv_s8x_kff #(.W(2), .ID(903)) u_m16 (.ck(ck), .d({2{pw16_we}}), .q(l_m16));
    wire [1:0] l_we = l_r16w | l_ssu | l_sw1;
    wire [9:0] l_row [0:1];
    assign l_row[0] = l_r16w[0] ? l_r16 : l_ssu[0] ? l_rsu : l_rw1;
    assign l_row[1] = l_r16w[1] ? l_r16 : l_ssu[1] ? l_rsu : l_rw1;
    wire [255:0] dS;
    generate for (gs = 0; gs < 8; gs = gs + 1) begin : g_ws
        wire [7:0] lw;
        qfd_dv_s8x_kff #(.W(8), .ID(1000 + gs)) u_win (.ck(ck), .d(winS[gs]), .q(lw));
        reg [31:0] e;
        always @(*) begin
            e = 32'd0;
            for (l = 0; l < 8; l = l + 1) e = e | ({32{lw[l]}} & l_sud[32*l +: 32]);
        end
        assign dS[32*gs +: 32] = e;
    end endgenerate
    wire [255:0] wb_d [0:1];
    wire [7:0]   wb_ms [0:1];
    generate for (gb = 0; gb < 2; gb = gb + 1) begin : g_wb
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_s
            wire l16, lsu, lw1, lmx;
            qfd_dv_s8x_kff #(.W(1), .ID(1100 + 16*gb + gs)) u_16 (.ck(ck), .d(pw16_we), .q(l16));
            qfd_dv_s8x_kff #(.W(1), .ID(1150 + 16*gb + gs)) u_su (.ck(ck), .d(sub_r[gb]), .q(lsu));
            qfd_dv_s8x_kff #(.W(1), .ID(1200 + 16*gb + gs)) u_w1 (.ck(ck), .d(gw1_r[gb][gs]), .q(lw1));
            qfd_dv_s8x_kff #(.W(1), .ID(1300 + 16*gb + gs)) u_m (.ck(ck), .d(gmx_r[gb][gs]), .q(lmx));
            assign wb_d[gb][32*gs +: 32] = ({32{l16}} & l_w16d[256*gb + 32*gs +: 32]) | ({32{lsu}} & dS[32*gs +: 32]) |
                                           ({32{lw1}} & l_w1d);
            assign wb_ms[gb][gs] = l_m16[gb] | lmx;
        end
    end endgenerate
    // ---------------------------------------------------------------- registered write stage per bank (at the macros)
    wire [255:0] mwd [0:1];
    wire [9:0]   mrow [0:1];
    wire         mwe [0:1];
    wire [7:0]   mms [0:1];
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_mw
        qfd_dv_s8x_kff #(.W(256), .ID(6000 + bk)) u_d (.ck(ck), .d(wb_d[bk]), .q(mwd[bk]));
        qfd_dv_s8x_kff #(.W(10), .ID(6100 + bk)) u_r (.ck(ck), .d(l_row[bk]), .q(mrow[bk]));
        qfd_dv_s8x_kff #(.W(1), .ID(6200 + bk)) u_e (.ck(ck), .d(l_we[bk]), .q(mwe[bk]));
        qfd_dv_s8x_kff #(.W(8), .ID(6300 + bk)) u_m (.ck(ck), .d(wb_ms[bk]), .q(mms[bk]));
    end endgenerate
    // ---------------------------------------------------------------- reads: 2 banks
    wire [511:0] vm_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_bank
        wire coll = mwe[bk] && mrow[bk] == pa_addr[4 +: 10];
`ifdef OT_S8_MUT_COLL
        wire coll_u = 1'b0;                     // bench mutant: read of the row being written NOT suppressed
`else
        wire coll_u = coll;
`endif
        wire [255:0] wm;
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_m assign wm[32*gs +: 32] = {32{mms[bk][gs]}}; end
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck),
            .r_ce_in(pa_re[0] && pa_addr[3] == bk[0] && !coll_u),
            .r_addr_in(pa_addr[4 +: 10]),
            .rd_out(vm_rd[bk*256 +: 256]),
            .w_ce_in(mwe[bk]), .w_addr_in(mrow[bk]), .wd_in(mwd[bk]), .w_mask_in(wm),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg s1_bank; reg [23:0] s1_off; reg [511:0] cap;
    always @(posedge ck) begin
        s1_bank <= pa_addr[3];
        for (lc = 0; lc < 8; lc = lc + 1) s1_off[3*lc +: 3] <= pa_addr[24*lc +: 3];
        cap <= vm_rd;
    end
    wire [255:0] wsel;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_bk
        wire bq;
        qfd_dv_s8x_kff #(.W(1), .ID(2000 + gk)) u (.ck(ck), .d(s1_bank), .q(bq));
        assign wsel[16*gk +: 16] = bq ? cap[256 + 16*gk +: 16] : cap[16*gk +: 16];
    end endgenerate
    wire [8*32-1:0] q_n;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_l
        wire [7:0] dec = 8'd1 << s1_off[3*gl +: 3];
        wire [7:0] oh0, oh1;
        qfd_dv_s8x_kff #(.W(8), .ID(2100 + 2*gl)) u0 (.ck(ck), .d(dec), .q(oh0));
        qfd_dv_s8x_kff #(.W(8), .ID(2101 + 2*gl)) u1 (.ck(ck), .d(dec), .q(oh1));
        reg [31:0] e;
        always @(*) begin
            e = 32'd0;
            for (s = 0; s < 8; s = s + 1)
                e = e | {({16{oh1[s]}} & wsel[32*s + 16 +: 16]), ({16{oh0[s]}} & wsel[32*s +: 16])};
        end
        assign q_n[32*gl +: 32] = e;
    end endgenerate
    always @(posedge ck) q <= q_n;
    // ---------------------------------------------------------------- faults (read range of this replica, write checks)
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
    reg rd_bad_q;
    always @(posedge ck) rd_bad_q <= bad_vec(pa_re, pa_addr);
    always @(posedge ck or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | rd_bad_q | l_wbad3;
endmodule

// ===================================================================================================== CROM leaf
module qfd_dv_s8x_crom #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [7:0]      cr_re,
    input  wire [8*24-1:0] cr_addr,
    output reg  [8*64-1:0] cr_q,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [23:0]     tw_addr,
    input  wire [1023:0]   tw_data,
    output reg             fault
);
    integer l, b, s, lc;
    genvar gl, gk, bk;
    reg rl0, rl1;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    reg [7:0] pcr_re; reg [8*24-1:0] pcr_addr;
    always @(posedge ck) begin pcr_re <= cr_re; pcr_addr <= cr_addr; end
    reg ptw_we; reg [1:0] ptw_kind; reg [23:0] ptw_addr; reg [1023:0] ptw_data;
    always @(posedge ck) begin ptw_we <= tw_we; ptw_kind <= tw_kind; ptw_addr <= tw_addr; ptw_data <= tw_data; end
    // table-write group landing (+1, kept copy beside the CROM macros)
    wire [1023:0] twc_d; wire [9:0] twc_a; wire twc_crw;
    qfd_dv_s8x_kff #(.W(1024), .ID(7000)) u_twcd (.ck(ck), .d(ptw_data), .q(twc_d));
    qfd_dv_s8x_kff #(.W(10), .ID(7001)) u_twca (.ck(ck), .d(ptw_addr[9:0]), .q(twc_a));
    qfd_dv_s8x_kff #(.W(1), .ID(7002)) u_twcw (.ck(ck), .d(ptw_we && ptw_kind == 2'd1), .q(twc_crw));
    wire [4*256-1:0] cr_rd;
    reg  [255:0] cw_lo [0:1], cw_hi [0:1];
    always @(*) begin
        for (b = 0; b < 2; b = b + 1)
            for (l = 0; l < 8; l = l + 1) begin
                cw_lo[b][32*l +: 32] = twc_d[64*(8*b+l) +: 32];
                cw_hi[b][32*l +: 32] = twc_d[64*(8*b+l) + 32 +: 32];
            end
    end
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_crom
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(pcr_re[0] && pcr_addr[3] == bk[0]), .r_addr_in(pcr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk)*256 +: 256]), .w_ce_in(twc_crw), .w_addr_in(twc_a), .wd_in(cw_lo[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(pcr_re[0] && pcr_addr[3] == bk[0]), .r_addr_in(pcr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk+1)*256 +: 256]), .w_ce_in(twc_crw), .w_addr_in(twc_a), .wd_in(cw_hi[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    wire [1:0] c1_bank;
    qfd_dv_s8x_kff #(.W(2), .ID(3300)) u_c1 (.ck(ck), .d({2{pcr_addr[3]}}), .q(c1_bank));
    reg [23:0] c1_off; reg [1023:0] ccap;
    always @(posedge ck) begin
        for (lc = 0; lc < 8; lc = lc + 1) c1_off[3*lc +: 3] <= pcr_addr[24*lc +: 3];
        ccap <= cr_rd;
    end
    wire [255:0] clo, chi;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_cbk
        wire bq_lo, bq_hi;
        qfd_dv_s8x_kff #(.W(1), .ID(3000 + gk)) u_lo (.ck(ck), .d(c1_bank[0]), .q(bq_lo));
        qfd_dv_s8x_kff #(.W(1), .ID(3100 + gk)) u_hi (.ck(ck), .d(c1_bank[1]), .q(bq_hi));
        assign clo[16*gk +: 16] = bq_lo ? ccap[256*2 + 16*gk +: 16] : ccap[256*0 + 16*gk +: 16];
        assign chi[16*gk +: 16] = bq_hi ? ccap[256*3 + 16*gk +: 16] : ccap[256*1 + 16*gk +: 16];
    end endgenerate
    wire [8*64-1:0] cr_n;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_cext
        wire [7:0] dec = 8'd1 << c1_off[3*gl +: 3];
        wire [7:0] oh [0:3];
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_c
            qfd_dv_s8x_kff #(.W(8), .ID(3200 + 4*gl + gk)) u (.ck(ck), .d(dec), .q(oh[gk]));
        end
        reg [31:0] lo_e, hi_e;
        always @(*) begin
            lo_e = 32'd0; hi_e = 32'd0;
            for (s = 0; s < 8; s = s + 1) begin
                lo_e = lo_e | {({16{oh[1][s]}} & clo[32*s + 16 +: 16]), ({16{oh[0][s]}} & clo[32*s +: 16])};
                hi_e = hi_e | {({16{oh[3][s]}} & chi[32*s + 16 +: 16]), ({16{oh[2][s]}} & chi[32*s +: 16])};
            end
        end
        assign cr_n[64*gl +: 64] = (MUT == 4) ? {lo_e, hi_e} : {hi_e, lo_e};
    end endgenerate
    always @(posedge ck) cr_q <= cr_n;
    // faults: CROM read range + every table-write check (kind / address range)
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
        tw_bad_q <= ptw_we && ((ptw_kind == 2'd0) || (ptw_kind == 2'd1 && ptw_addr[23:10] != 0) ||
                               (ptw_kind == 2'd2 && (ptw_addr[1:0] != 0 || ptw_addr[23:9] != 0)) ||
                               (ptw_kind == 2'd3 && ptw_addr[23:8] != 0));
        tw_bad_q2 <= tw_bad_q;
    end
    always @(posedge ck or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | rd_bad_q | tw_bad_q2;
endmodule

// ===================================================================================================== CROM half leaf
// (r2 fallback for qfd_dv_s8x_crom, whose 475 um S face put the 1,024 tw pin registers 237 um from the clock pin:
// gate TT pin-flop spread 140.7 ps).  CROM split by WORD HALF (lo | hi), not by bank: each half = banks 0/1 of that
// half (2 x 1024x256, the vmr shape) + its own bank select + its 16-bit-half extraction, so nothing crosses between the
// halves.  ONE leaf type instantiated twice; the composition gathers each half's table bits (tw_d) and orders the answer
// {hi, lo} per lane.  Both halves carry the full table-write / CROM-read range fault (identical terms, OR'd).
module qfd_dv_s8x_crh (
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
    wire [511:0] cr_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_crb
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck), .r_ce_in(pcr_re[0] && pcr_addr[3] == bk[0]), .r_addr_in(pcr_addr[4 +: 10]),
            .rd_out(cr_rd[bk*256 +: 256]), .w_ce_in(twc_crw), .w_addr_in(twc_a), .wd_in(twc_d[256*bk +: 256]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    wire c1_bank;
    qfd_dv_s8x_kff #(.W(1), .ID(3400)) u_c1 (.ck(ck), .d(pcr_addr[3]), .q(c1_bank));
    reg [23:0] c1_off; reg [511:0] ccap;
    always @(posedge ck) begin
        for (lc = 0; lc < 8; lc = lc + 1) c1_off[3*lc +: 3] <= pcr_addr[24*lc +: 3];
        ccap <= cr_rd;
    end
    wire [255:0] c;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_cbk
        wire bq;
        qfd_dv_s8x_kff #(.W(1), .ID(3500 + gk)) u (.ck(ck), .d(c1_bank), .q(bq));
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
        tw_bad_q <= ptw_we && ((ptw_kind == 2'd0) || (ptw_kind == 2'd1 && ptw_addr[23:10] != 0) ||
                               (ptw_kind == 2'd2 && (ptw_addr[1:0] != 0 || ptw_addr[23:9] != 0)) ||
                               (ptw_kind == 2'd3 && ptw_addr[23:8] != 0));
        tw_bad_q2 <= tw_bad_q;
    end
    always @(posedge ck or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | rd_bad_q | tw_bad_q2;
endmodule

// ===================================================================================================== BTAB leaf
// (fallback partition leaf; also half of qfd_dv_s8x_su).  Table writes of kind 2 only.
// MIF (PATH-QC-SRAMIF 2026-10-25, GEOM-REVIEW F6 on btab_s6): MIF=0 = the vm8 leaf (one shared register set drives all
// 4 SRAMs through 2-4 decode levels, 66-302 um).  MIF=1 = per-SRAM macro-interface registers: every SRAM gets its own
// read-address / read-enable / write-address / write-enable / write-data landing register, the bank decode is done
// BEFORE these registers, so each one drives its macro pin directly (anchored <= 20 um, physical/common_flow/
// macro_pin_flops.tcl).  The read gets the landing stage (+1 cycle), and the write path keeps the same extra cycle
// (u_twp* becomes the shared relay stage in front of the per-SRAM landings) so that MIF=1 is exactly MIF=0 delayed by one
// cycle on bs_q (bs_q(t+1) = bs_q_MIF0(t); write/read ordering unchanged); fault is unchanged (0 cycles).
// PRICE vs MIF=0: BTAB read +1, table write +1.  The parent must schedule the +1 (static schedule).
module qfd_dv_s8x_btab #(parameter integer MIF = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire            bs_re,
    input  wire [23:0]     bs_addr,
    output reg  [255:0]    bs_q,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [8:2]      tw_addr,
    input  wire [1023:0]   tw_data,
    output reg             fault
);
    genvar gk, bk;
    reg rl0, rl1;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    reg pbs_re; reg [23:0] pbs_addr;
    always @(posedge ck) begin pbs_re <= bs_re; pbs_addr <= bs_addr; end
    reg ptw_we; reg [1:0] ptw_kind; reg [8:2] ptw_addr; reg [1023:0] ptw_data;
    always @(posedge ck) begin ptw_we <= tw_we; ptw_kind <= tw_kind; ptw_addr <= tw_addr; ptw_data <= tw_data; end
    wire ptw_w = ptw_we && ptw_kind == 2'd2;
    wire [1023:0] twp_d; wire [8:2] twp_a; wire twp_w;
    qfd_dv_s8x_kff #(.W(1024), .ID(7100)) u_twpd (.ck(ck), .d(ptw_data), .q(twp_d));
    qfd_dv_s8x_kff #(.W(7), .ID(7101)) u_twpa (.ck(ck), .d(ptw_addr), .q(twp_a));
    qfd_dv_s8x_kff #(.W(1), .ID(7102)) u_twpw (.ck(ck), .d(ptw_w), .q(twp_w));
    wire [8:0] bs_word = pbs_addr[8:0];
    wire [4*256-1:0] bt_rd;
    wire [1:0] cap_bank;   // bank of the read the SRAMs latch this edge
    generate if (MIF == 0) begin : g_cb0
        assign cap_bank = bs_word[1:0];
    end else begin : g_cb1
        qfd_dv_s8x_kff #(.W(2), .ID(7149)) u_rbk (.ck(ck), .d(bs_word[1:0]), .q(cap_bank));
    end endgenerate
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        wire m_rce, m_we; wire [8:2] m_ra, m_wa; wire [255:0] m_wd;
        if (MIF == 0) begin : g_d
            assign m_rce = pbs_re && bs_word[1:0] == bk[1:0]; assign m_ra = bs_word[8:2];
            assign m_we = twp_w; assign m_wa = twp_a; assign m_wd = twp_d[256*bk +: 256];
        end else begin : g_r
            // per-SRAM landing registers (distinct IDs: distinct kept modules, never merged), decode in front
            qfd_dv_s8x_kff #(.W(1), .ID(7150 + bk)) u_rce (.ck(ck), .d(pbs_re && bs_word[1:0] == bk[1:0]), .q(m_rce));
            qfd_dv_s8x_kff #(.W(7), .ID(7160 + bk)) u_ra (.ck(ck), .d(bs_word[8:2]), .q(m_ra));
            qfd_dv_s8x_kff #(.W(1), .ID(7170 + bk)) u_we (.ck(ck), .d(twp_w), .q(m_we));
            qfd_dv_s8x_kff #(.W(7), .ID(7180 + bk)) u_wa (.ck(ck), .d(twp_a), .q(m_wa));
            qfd_dv_s8x_kff #(.W(256), .ID(7190 + bk)) u_wd (.ck(ck), .d(twp_d[256*bk +: 256]), .q(m_wd));
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(m_rce), .r_addr_in(m_ra),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(m_we), .w_addr_in(m_wa),
            .wd_in(m_wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg [1:0] s1b_bank; reg [1023:0] btcap;
    always @(posedge ck) begin s1b_bank <= cap_bank; btcap <= bt_rd; end
    wire [3:0] bdec = 4'd1 << s1b_bank;
    wire [255:0] bs_n;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_bsel
        wire [3:0] boh;
        qfd_dv_s8x_kff #(.W(4), .ID(4000 + gk)) u (.ck(ck), .d(bdec), .q(boh));
        assign bs_n[16*gk +: 16] = ({16{boh[0]}} & btcap[256*0 + 16*gk +: 16]) | ({16{boh[1]}} & btcap[256*1 + 16*gk +: 16]) |
                                   ({16{boh[2]}} & btcap[256*2 + 16*gk +: 16]) | ({16{boh[3]}} & btcap[256*3 + 16*gk +: 16]);
    end endgenerate
    always @(posedge ck) bs_q <= bs_n;
    reg bs_bad_q;
    always @(posedge ck) bs_bad_q <= pbs_re && pbs_addr[23:9] != 0;
    always @(posedge ck or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | bs_bad_q;
endmodule

// ===================================================================================================== PROG leaf
// (fallback partition leaf; also half of qfd_dv_s8x_su).  Table writes of kind 3 only; data bank 0 = tw_data[456:0],
// bank 1 = tw_data[968:512] (the only table bits PROG stores).
// MIF (PATH-QC-SRAMIF 2026-10-25, GEOM-REVIEW F6 on prog_s6): as qfd_dv_s8x_btab.  MIF=1 = per-SRAM read-address /
// read-enable / write-address / write-enable / write-data landing registers with the bank decode in front; MIF=1 is
// exactly MIF=0 delayed by one cycle on p_q (read +1, table write +1, write/read ordering unchanged).
module qfd_dv_s8x_prog #(parameter integer MIF = 0) (
    input  wire            ck,
    input  wire            p_re,
    input  wire [8:0]      p_idx,
    output reg  [456:0]    p_q,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [7:0]      tw_addr,
    input  wire [456:0]    tw_d0,
    input  wire [456:0]    tw_d1
);
    genvar gk, bk;
    reg pp_re; reg [8:0] pp_idx;
    always @(posedge ck) begin pp_re <= p_re; pp_idx <= p_idx; end
    reg ptw_we; reg [1:0] ptw_kind; reg [7:0] ptw_addr; reg [456:0] ptw_d0, ptw_d1;
    always @(posedge ck) begin ptw_we <= tw_we; ptw_kind <= tw_kind; ptw_addr <= tw_addr; ptw_d0 <= tw_d0; ptw_d1 <= tw_d1; end
    wire ptw_w = ptw_we && ptw_kind == 2'd3;
    wire [456:0] twp_d0, twp_d1; wire [7:0] twp_a; wire twp_w;
    qfd_dv_s8x_kff #(.W(457), .ID(7200)) u_twd0 (.ck(ck), .d(ptw_d0), .q(twp_d0));
    qfd_dv_s8x_kff #(.W(457), .ID(7201)) u_twd1 (.ck(ck), .d(ptw_d1), .q(twp_d1));
    qfd_dv_s8x_kff #(.W(8), .ID(7202)) u_twpa (.ck(ck), .d(ptw_addr), .q(twp_a));
    qfd_dv_s8x_kff #(.W(1), .ID(7203)) u_twpw (.ck(ck), .d(ptw_w), .q(twp_w));
    wire [456:0] twd [0:1];
    assign twd[0] = twp_d0; assign twd[1] = twp_d1;
    wire [4*256-1:0] p_rd;
    wire cap_bank;   // bank of the read the SRAMs latch this edge
    generate if (MIF == 0) begin : g_cb0
        assign cap_bank = pp_idx[0];
    end else begin : g_cb1
        qfd_dv_s8x_kff #(.W(1), .ID(7249)) u_rbk (.ck(ck), .d(pp_idx[0]), .q(cap_bank));
    end endgenerate
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_prog
        wire lo_rce, hi_rce, lo_we, hi_we; wire [7:0] lo_ra, hi_ra, lo_wa, hi_wa; wire [255:0] lo_wd; wire [200:0] hi_wd;
        if (MIF == 0) begin : g_d
            assign lo_rce = pp_re && pp_idx[0] == bk[0]; assign hi_rce = lo_rce;
            assign lo_ra = pp_idx[8:1]; assign hi_ra = pp_idx[8:1];
            assign lo_we = twp_w; assign hi_we = twp_w; assign lo_wa = twp_a; assign hi_wa = twp_a;
            assign lo_wd = twd[bk][255:0]; assign hi_wd = twd[bk][456:256];
        end else begin : g_r
            // per-SRAM landing registers (distinct IDs: distinct kept modules, never merged), decode in front
            qfd_dv_s8x_kff #(.W(1), .ID(7250 + 2*bk)) u_lo_rce (.ck(ck), .d(pp_re && pp_idx[0] == bk[0]), .q(lo_rce));
            qfd_dv_s8x_kff #(.W(1), .ID(7251 + 2*bk)) u_hi_rce (.ck(ck), .d(pp_re && pp_idx[0] == bk[0]), .q(hi_rce));
            qfd_dv_s8x_kff #(.W(8), .ID(7260 + 2*bk)) u_lo_ra (.ck(ck), .d(pp_idx[8:1]), .q(lo_ra));
            qfd_dv_s8x_kff #(.W(8), .ID(7261 + 2*bk)) u_hi_ra (.ck(ck), .d(pp_idx[8:1]), .q(hi_ra));
            qfd_dv_s8x_kff #(.W(1), .ID(7270 + 2*bk)) u_lo_we (.ck(ck), .d(twp_w), .q(lo_we));
            qfd_dv_s8x_kff #(.W(1), .ID(7271 + 2*bk)) u_hi_we (.ck(ck), .d(twp_w), .q(hi_we));
            qfd_dv_s8x_kff #(.W(8), .ID(7280 + 2*bk)) u_lo_wa (.ck(ck), .d(twp_a), .q(lo_wa));
            qfd_dv_s8x_kff #(.W(8), .ID(7281 + 2*bk)) u_hi_wa (.ck(ck), .d(twp_a), .q(hi_wa));
            qfd_dv_s8x_kff #(.W(256), .ID(7290 + 2*bk)) u_lo_wd (.ck(ck), .d(twd[bk][255:0]), .q(lo_wd));
            qfd_dv_s8x_kff #(.W(201), .ID(7291 + 2*bk)) u_hi_wd (.ck(ck), .d(twd[bk][456:256]), .q(hi_wd));
        end
        ot_sram_1r1w_256x256_m2_r2c2 u_lo (.clk(ck), .r_ce_in(lo_rce), .r_addr_in(lo_ra),
            .rd_out(p_rd[(2*bk)*256 +: 256]), .w_ce_in(lo_we), .w_addr_in(lo_wa),
            .wd_in(lo_wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_256x256_m2_r2c2 u_hi (.clk(ck), .r_ce_in(hi_rce), .r_addr_in(hi_ra),
            .rd_out(p_rd[(2*bk+1)*256 +: 256]), .w_ce_in(hi_we), .w_addr_in(hi_wa),
            .wd_in({55'd0, hi_wd}), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    wire [3:0] p1_bank;
    qfd_dv_s8x_kff #(.W(4), .ID(5100)) u_p1 (.ck(ck), .d({4{cap_bank}}), .q(p1_bank));
    reg [1023:0] pcap;
    always @(posedge ck) pcap <= p_rd;
    wire [511:0] pw2;
    generate for (gk = 0; gk < 64; gk = gk + 1) begin : g_psel
        wire pq;
        qfd_dv_s8x_kff #(.W(1), .ID(5000 + gk)) u (.ck(ck), .d(p1_bank[gk / 16]), .q(pq));
        assign pw2[8*gk +: 8] = pq ? pcap[512 + 8*gk +: 8] : pcap[8*gk +: 8];
    end endgenerate
    always @(posedge ck) p_q <= {pw2[256 +: 201], pw2[255:0]};
endmodule

// ===================================================================================================== SU leaf (btab + prog)
module qfd_dv_s8x_su (
    input  wire            ck,
    input  wire            rst_n,
    input  wire            bs_re,
    input  wire [23:0]     bs_addr,
    output wire [255:0]    bs_q,
    input  wire            p_re,
    input  wire [8:0]      p_idx,
    output wire [456:0]    p_q,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [8:0]      tw_addr,
    input  wire [1023:0]   tw_data,
    output wire            fault
);
    qfd_dv_s8x_btab u_bt (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(bs_q),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault(fault));
    qfd_dv_s8x_prog u_pg (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(p_q),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
endmodule

// ===================================================================================================== compositions
// SPLIT = 0: r1 partition (3 x vmr + crom + su);  SPLIT = 1: 3 x vmr + crom + btab + prog;
// SPLIT = 2: 3 x vmr + 2 x crh (CROM lo / hi halves) + btab + prog (r2: no leaf wider than 259.2 um on its dense face).
// Bench / equivalence vehicle only (one clock): in slice2 every leaf is its own region and every crossing to its
// neighbours lands in a mesochronous ring in the parent.
module qfd_dv_s5_vm8x #(parameter integer MUT = 0, parameter integer SPLIT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [7:0]      a_re, b_re, c_re,
    input  wire [8*24-1:0] a_addr, b_addr, c_addr,
    output wire [8*32-1:0] a_q, b_q, c_q,
    input  wire [7:0]      cr_re,
    input  wire [8*24-1:0] cr_addr,
    output wire [8*64-1:0] cr_q,
    input  wire            bs_re,
    input  wire [23:0]     bs_addr,
    output wire [255:0]    bs_q,
    input  wire            p_re,
    input  wire [8:0]      p_idx,
    output wire [456:0]    p_q,
    input  wire [7:0]      vm_we,
    input  wire [8*24-1:0] vm_waddr,
    input  wire [8*32-1:0] vm_wdata,
    input  wire            w16_we,
    input  wire [23:0]     w16_addr,
    input  wire [511:0]    w16_data,
    input  wire            w1_we,
    input  wire [23:0]     w1_addr,
    input  wire [31:0]     w1_data,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [23:0]     tw_addr,
    input  wire [1023:0]   tw_data,
    output wire            fault
);
    wire [255:0] qa, qb, qc;
    wire fa, fb, fc, fcr, fsu;
    qfd_dv_s8x_vmr #(.MUT(MUT)) u_va (.ck(ck), .rst_n(rst_n), .re(a_re), .addr(a_addr), .q(qa),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fa));
    qfd_dv_s8x_vmr #(.MUT(MUT)) u_vb (.ck(ck), .rst_n(rst_n), .re(b_re), .addr(b_addr), .q(qb),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fb));
    qfd_dv_s8x_vmr #(.MUT(MUT)) u_vc (.ck(ck), .rst_n(rst_n), .re(c_re), .addr(c_addr), .q(qc),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data),
        .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fc));
`ifdef OT_S8_MUT_BSEL
    localparam integer BMUT = 1;               // bench mutant: operand b answered from replica c
`else
    localparam integer BMUT = 0;
`endif
    // operand b is answered from replica c for MUT 5 / BMUT: the vm8 mutant moved to the composition (replica b would
    // still be read; its row read is the same, so the mutant answers c's operand rows for b's request -> FAIL expected)
    assign a_q = qa;
    assign b_q = (MUT == 5 || BMUT == 1) ? qc : qb;
    assign c_q = qc;
    generate if (SPLIT < 2) begin : g_crom
        qfd_dv_s8x_crom #(.MUT(MUT)) u_cr (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(cr_q),
            .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(fcr));
    end else begin : g_crh
        wire [511:0] dlo, dhi; wire [255:0] qlo, qhi; wire flo, fhi;
        genvar gi;
        for (gi = 0; gi < 16; gi = gi + 1) begin : g_d
            assign dlo[32*gi +: 32] = tw_data[64*gi +: 32];
            assign dhi[32*gi +: 32] = tw_data[64*gi + 32 +: 32];
        end
        qfd_dv_s8x_crh u_lo (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(qlo),
            .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(dlo), .fault(flo));
        qfd_dv_s8x_crh u_hi (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(qhi),
            .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(dhi), .fault(fhi));
        for (gi = 0; gi < 8; gi = gi + 1) begin : g_q
            assign cr_q[64*gi +: 64] = (MUT == 4) ? {qlo[32*gi +: 32], qhi[32*gi +: 32]} : {qhi[32*gi +: 32], qlo[32*gi +: 32]};
        end
        assign fcr = flo | fhi;
    end endgenerate
    generate if (SPLIT == 0) begin : g_su
        qfd_dv_s8x_su u_su (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(bs_q), .p_re(p_re), .p_idx(p_idx),
            .p_q(p_q), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:0]), .tw_data(tw_data), .fault(fsu));
    end else begin : g_bp
        qfd_dv_s8x_btab u_bt (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(bs_q),
            .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault(fsu));
        qfd_dv_s8x_prog u_pg (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(p_q),
            .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
    end endgenerate
    assign fault = fa | fb | fc | fcr | fsu;
endmodule
