`timescale 1ns/1ps
// =====================================================================================================================
// QW-SUVM8 10-20: qfd_dv_s5_vm8 = the slice2 VM (18 SRAM macros: VM 3 replicas x 2 banks, CROM 2 x {lo, hi}, BTAB SU copy
// 4 banks, PROG 2 x {lo, hi}) as its OWN hardened block, split out of the doomed suvm7 / suvm7b leaf (one 9.7k-flop root,
// pin-flop spread 217 / 381 ps, reg->macro -519, in->macro -406, reg->out -429 ps at placement).
// Structure (edge-for-edge qfd_dv_s5_vm7 of claude/qw-slice6-suvm-1019 03ba379bf, re-timed; no logic change):
//   * EVERY input lands in a pin register (+1), EVERY output leaves a pin register (+1): no in->macro, no macro->out,
//     no combinational pin arc.  rst_n lands in 2 registered stages (rl0 -> rl1) and resets only the sticky fault.
//   * VM write merge (vm7 landing decode, kept per-(bank, slot) one-hot registers) is followed by a REGISTERED write
//     stage per (replica, bank): wd / row / we / per-slot mask flops beside each macro (no logic before a macro
//     write pin); the read-collision term compares two registers (pin-registered read row vs the macro-side write row).
//   * table writes tw_* land twice (pin register, then one kept copy per macro group: CROM | PROG + BTAB), so no
//     table write wire crosses the block in one cycle.
//   * three REGIONAL clock roots (related, same PLL, phase 0): ck_wr = S face (write / table pin registers + decode,
//     reset, fault), ck_rd = W face + VM / CROM macros (read pin registers, macro clocks, capture, select, answer pin
//     registers, the registered write stage, the CROM table copy), ck_su = E face + PROG / BTAB macros (SU-control
//     side requests, capture, answer pin registers, the PROG / BTAB table copy).  qfd_dv_s5_vm8s ties them (fallback).
// PRICE (static schedule; NOTICE QW-GEN / TOKSIM / slice2 parent):
//   reads  (VM a/b/c, CROM, BTAB, PROG): answer 2 -> 4 edges (+2: input pin + answer pin register)
//   VM writes (lane window 00, w16, w1): +3 vs qfd_dv_s5_suvm (+2 vs suvm7): write -> read distance 1 -> 3
//   table writes tw_*: +2 (pin + group landing): table write -> read distance unchanged (1 -> 2 vs +1 read in) = +1
//   fault: observation only (+1 vs vm7 per term, = the answer pin register)
//   bench: tb_vm8 == qfd_dv_s5_vm7 fed reads +1 / VM writes +2 / tw +2 and every output +1 (rtl/test/qwen_dv/s5/vm8).
// =====================================================================================================================

(* keep_hierarchy = "yes" *) module qfd_dv_s8_kff #(parameter integer W = 1, parameter integer ID = 0) (
    input wire ck, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge ck) q <= d;
endmodule

module qfd_dv_s5_vm8 #(parameter integer MUT = 0) (
    input  wire            ck_wr,
    input  wire            ck_rd,
    input  wire            ck_su,
    // raw SRAM clock entries (one per macro; kit qfd_dv_s5_vm8h hybrid_entries): VM 0-5 [2*rep+bank], CROM 6-9
    // [6+2*bank+hi], BTAB 10-13, PROG 14-17 [14+2*bank+hi]; tied to the root clock in vm8s and the benches
    input  wire            ckm0, ckm1, ckm2, ckm3, ckm4, ckm5, ckm6, ckm7, ckm8, ckm9, ckm10, ckm11, ckm12, ckm13, ckm14, ckm15, ckm16, ckm17,
    input  wire            rst_n,
    // ---- ck_rd (W face): lane operand reads + CROM reads
    input  wire [7:0]      a_re, b_re, c_re,
    input  wire [8*24-1:0] a_addr, b_addr, c_addr,
    output reg  [8*32-1:0] a_q, b_q, c_q,
    input  wire [7:0]      cr_re,
    input  wire [8*24-1:0] cr_addr,
    output reg  [8*64-1:0] cr_q,
    // ---- ck_su (E face): SU-control side BF16 table + program reads
    input  wire            bs_re,
    input  wire [23:0]     bs_addr,
    output reg  [255:0]    bs_q,
    input  wire            p_re,
    input  wire [8:0]      p_idx,
    output reg  [456:0]    p_q,
    // ---- ck_wr (S face): VM writes, table writes, fault
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
    output reg             fault
);
    integer l, b, s, k;
    genvar gl, gb, gs, gk, op, bk;
    wire [17:0] ckm = {ckm17, ckm16, ckm15, ckm14, ckm13, ckm12, ckm11, ckm10, ckm9, ckm8, ckm7, ckm6, ckm5, ckm4, ckm3, ckm2, ckm1, ckm0};
    // ================================================================ reset landing (ck_wr, 2 stages)
    reg rl0, rl1;
    always @(posedge ck_wr or negedge rst_n) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    // ================================================================ input pin registers
    reg [7:0]      pa_re, pb_re, pc_re, pcr_re;
    reg [8*24-1:0] pa_addr, pb_addr, pc_addr, pcr_addr;
    always @(posedge ck_rd) begin
        pa_re <= a_re; pb_re <= b_re; pc_re <= c_re; pcr_re <= cr_re;
        pa_addr <= a_addr; pb_addr <= b_addr; pc_addr <= c_addr; pcr_addr <= cr_addr;
    end
    reg pbs_re, pp_re; reg [23:0] pbs_addr; reg [8:0] pp_idx;
    always @(posedge ck_su) begin pbs_re <= bs_re; pbs_addr <= bs_addr; pp_re <= p_re; pp_idx <= p_idx; end
    reg [8*24-1:0] pvm_waddr; reg [8*32-1:0] pvm_wdata;
    reg pw16_we, pw1_we, ptw_we; reg [23:0] pw16_addr, pw1_addr, ptw_addr; reg [511:0] pw16_data; reg [31:0] pw1_data;
    reg [1:0] ptw_kind; reg [1023:0] ptw_data;
    always @(posedge ck_wr) begin
        pvm_waddr <= vm_waddr; pvm_wdata <= vm_wdata;
        pw16_we <= w16_we; pw16_addr <= w16_addr; pw16_data <= w16_data;
        pw1_we <= w1_we; pw1_addr <= w1_addr; pw1_data <= w1_data;
        ptw_we <= tw_we; ptw_kind <= tw_kind; ptw_addr <= tw_addr; ptw_data <= tw_data;
    end
    // ================================================================ VM write decode (= vm7 landing, from pin registers; ck_wr)
    // window decode from KEPT pin-register copies of {vm_we, vm_waddr[23:22]} (gate 054252 vm8b: one shared
    // vm_waddr[22] pin register drove 41 loads): copies 0-3 serve the slot hits of lane pairs, 4 the bank selects,
    // 5 the write checks
    wire [9:0] pwin [0:5];
    wire [5:0] su_any_k;
    generate for (gk = 0; gk < 6; gk = gk + 1) begin : g_pwin
        qfd_dv_s8_kff #(.W(10), .ID(8000 + gk)) u (.ck(ck_wr), .d({vm_we, vm_waddr[23:22]}), .q(pwin[gk]));
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
    always @(posedge ck_wr) begin
        l_sud <= pvm_wdata; l_w16d <= pw16_data; l_w1d <= pw1_data;
        l_r16 <= pw16_addr[13:4]; l_rsu <= pvm_waddr[13:4]; l_rw1 <= pw1_addr[13:4];
        l_wbad <= w_bad_r || w_coll_r; l_wbad2 <= l_wbad; l_wbad3 <= l_wbad2;
    end
    wire [1:0] l_r16w, l_m16, l_ssu, l_sw1;
    qfd_dv_s8_kff #(.W(2), .ID(900)) u_r16 (.ck(ck_wr), .d({2{pw16_we}}), .q(l_r16w));
    qfd_dv_s8_kff #(.W(2), .ID(901)) u_ssu (.ck(ck_wr), .d(ssu_r), .q(l_ssu));
    qfd_dv_s8_kff #(.W(2), .ID(902)) u_sw1 (.ck(ck_wr), .d(sw1_r), .q(l_sw1));
    qfd_dv_s8_kff #(.W(2), .ID(903)) u_m16 (.ck(ck_wr), .d({2{pw16_we}}), .q(l_m16));
    wire [1:0] l_we = l_r16w | l_ssu | l_sw1;
    wire [9:0] l_row [0:1];
    assign l_row[0] = l_r16w[0] ? l_r16 : l_ssu[0] ? l_rsu : l_rw1;
    assign l_row[1] = l_r16w[1] ? l_r16 : l_ssu[1] ? l_rsu : l_rw1;
    wire [255:0] dS;
    generate for (gs = 0; gs < 8; gs = gs + 1) begin : g_ws
        wire [7:0] lw;
        qfd_dv_s8_kff #(.W(8), .ID(1000 + gs)) u_win (.ck(ck_wr), .d(winS[gs]), .q(lw));
        reg [31:0] e;
        always @(*) begin
            e = 32'd0;
            for (l = 0; l < 8; l = l + 1) e = e | ({32{lw[l]}} & l_sud[32*l +: 32]);
        end
        assign dS[32*gs +: 32] = e;
    end endgenerate
    wire [255:0] wb_d [0:1];
    wire [7:0]   wb_ms [0:5];                // [2*replica + bank] per-slot mask (one bit per 32-bit slot)
    generate for (gb = 0; gb < 2; gb = gb + 1) begin : g_wb
        for (gs = 0; gs < 8; gs = gs + 1) begin : g_s
            wire l16, lsu, lw1;
            wire [2:0] lmx;
            qfd_dv_s8_kff #(.W(1), .ID(1100 + 16*gb + gs)) u_16 (.ck(ck_wr), .d(pw16_we), .q(l16));
            qfd_dv_s8_kff #(.W(1), .ID(1150 + 16*gb + gs)) u_su (.ck(ck_wr), .d(sub_r[gb]), .q(lsu));
            qfd_dv_s8_kff #(.W(1), .ID(1200 + 16*gb + gs)) u_w1 (.ck(ck_wr), .d(gw1_r[gb][gs]), .q(lw1));
            qfd_dv_s8_kff #(.W(3), .ID(1300 + 16*gb + gs)) u_m (.ck(ck_wr), .d({3{gmx_r[gb][gs]}}), .q(lmx));
            assign wb_d[gb][32*gs +: 32] = ({32{l16}} & l_w16d[256*gb + 32*gs +: 32]) | ({32{lsu}} & dS[32*gs +: 32]) |
                                           ({32{lw1}} & l_w1d);
            assign wb_ms[0 + gb][gs] = l_m16[gb] | lmx[0];
            assign wb_ms[2 + gb][gs] = l_m16[gb] | lmx[1];
            assign wb_ms[4 + gb][gs] = l_m16[gb] | lmx[2];
        end
    end endgenerate
    // ================================================================ registered write stage per (replica, bank) (ck_rd)
    wire [255:0] mwd [0:5];
    wire [9:0]   mrow [0:5];
    wire         mwe [0:5];
    wire [7:0]   mms [0:5];
    generate for (op = 0; op < 3; op = op + 1) begin : g_mw
        for (bk = 0; bk < 2; bk = bk + 1) begin : g_b
            qfd_dv_s8_kff #(.W(256), .ID(6000 + 2*op + bk)) u_d (.ck(ck_rd), .d(wb_d[bk]), .q(mwd[2*op + bk]));
            qfd_dv_s8_kff #(.W(10), .ID(6100 + 2*op + bk)) u_r (.ck(ck_rd), .d(l_row[bk]), .q(mrow[2*op + bk]));
            qfd_dv_s8_kff #(.W(1), .ID(6200 + 2*op + bk)) u_e (.ck(ck_rd), .d(l_we[bk]), .q(mwe[2*op + bk]));
            qfd_dv_s8_kff #(.W(8), .ID(6300 + 2*op + bk)) u_m (.ck(ck_rd), .d(wb_ms[2*op + bk]), .q(mms[2*op + bk]));
        end
    end endgenerate
    // ================================================================ VM reads: 3 replicas x 2 banks (ck_rd)
    wire [2:0] rq_re = {pc_re[0], pb_re[0], pa_re[0]};
    wire [24*3-1:0] rq_a0 = {pc_addr[23:0], pb_addr[23:0], pa_addr[23:0]};
    wire [3*256*2-1:0] vm_rd;
    generate for (op = 0; op < 3; op = op + 1) begin : g_rep
        for (bk = 0; bk < 2; bk = bk + 1) begin : g_bank
            wire coll = mwe[2*op + bk] && mrow[2*op + bk] == rq_a0[24*op+4 +: 10];
`ifdef OT_S8_MUT_COLL
            wire coll_u = 1'b0;                 // bench mutant: read of the row being written NOT suppressed
`else
            wire coll_u = coll;
`endif
            wire [255:0] wm;
            for (gs = 0; gs < 8; gs = gs + 1) begin : g_m assign wm[32*gs +: 32] = {32{mms[2*op + bk][gs]}}; end
            ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ckm[2*op + bk]),
                .r_ce_in(rq_re[op] && rq_a0[24*op+3] == bk[0] && !coll_u),
                .r_addr_in(rq_a0[24*op+4 +: 10]),
                .rd_out(vm_rd[(2*op+bk)*256 +: 256]),
                .w_ce_in(mwe[2*op + bk]), .w_addr_in(mrow[2*op + bk]), .wd_in(mwd[2*op + bk]), .w_mask_in(wm),
                .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        end
    end endgenerate
    reg  [2:0]    s1_bank;
    reg  [3*24-1:0] s1_off;
    reg  [3*512-1:0] cap;
    always @(posedge ck_rd) begin
        s1_bank <= {pc_addr[3], pb_addr[3], pa_addr[3]};
        for (l = 0; l < 8; l = l + 1) begin
            s1_off[3*l +: 3]      <= pa_addr[24*l +: 3];
            s1_off[24 + 3*l +: 3] <= pb_addr[24*l +: 3];
            s1_off[48 + 3*l +: 3] <= pc_addr[24*l +: 3];
        end
        cap <= vm_rd;
    end
    wire [255:0] wsel [0:2];
    generate for (op = 0; op < 3; op = op + 1) begin : g_rsel
        for (gk = 0; gk < 16; gk = gk + 1) begin : g_bk
            wire bq;
            qfd_dv_s8_kff #(.W(1), .ID(2000 + 16*op + gk)) u (.ck(ck_rd), .d(s1_bank[op]), .q(bq));
            assign wsel[op][16*gk +: 16] = bq ? cap[512*op + 256 + 16*gk +: 16] : cap[512*op + 16*gk +: 16];
        end
    end endgenerate
`ifdef OT_S8_MUT_BSEL
    localparam integer BMUT = 1;               // bench mutant: operand b answered from replica c
`else
    localparam integer BMUT = 0;
`endif
    wire [255:0] wa = wsel[0], wc = wsel[2];
    wire [255:0] wb_sel = (MUT == 5 || BMUT == 1) ? wsel[2] : wsel[1];
    wire [8*32-1:0] a_n, b_n, c_n;
    generate for (op = 0; op < 3; op = op + 1) begin : g_rext
        for (gl = 0; gl < 8; gl = gl + 1) begin : g_l
            wire [7:0] dec = 8'd1 << s1_off[24*op + 3*gl +: 3];
            wire [7:0] oh0, oh1;
            qfd_dv_s8_kff #(.W(8), .ID(2100 + 16*op + 2*gl)) u0 (.ck(ck_rd), .d(dec), .q(oh0));
            qfd_dv_s8_kff #(.W(8), .ID(2101 + 16*op + 2*gl)) u1 (.ck(ck_rd), .d(dec), .q(oh1));
            wire [255:0] wsrc = (op == 0) ? wa : (op == 1) ? wb_sel : wc;
            reg [31:0] e;
            always @(*) begin
                e = 32'd0;
                for (s = 0; s < 8; s = s + 1)
                    e = e | {({16{oh1[s]}} & wsrc[32*s + 16 +: 16]), ({16{oh0[s]}} & wsrc[32*s +: 16])};
            end
            if (op == 0) begin : g_a assign a_n[32*gl +: 32] = e; end
            else if (op == 1) begin : g_b assign b_n[32*gl +: 32] = e; end
            else begin : g_c assign c_n[32*gl +: 32] = e; end
        end
    end endgenerate
    always @(posedge ck_rd) begin a_q <= a_n; b_q <= b_n; c_q <= c_n; end
    // ================================================================ table-write group landings (+1, one kept copy per group)
    // CROM copy (ck_rd, beside the CROM macros); PROG + BTAB copy (ck_su, beside col 2)
    wire [1023:0] twc_d, twp_d;
    wire [9:0]    twc_a;
    wire [8:0]    twp_a;
    wire          twc_crw;
    wire [1:0]    twp_w;                      // {pw, bt_w}
    qfd_dv_s8_kff #(.W(1024), .ID(7000)) u_twcd (.ck(ck_rd), .d(ptw_data), .q(twc_d));
    qfd_dv_s8_kff #(.W(10), .ID(7001)) u_twca (.ck(ck_rd), .d(ptw_addr[9:0]), .q(twc_a));
    qfd_dv_s8_kff #(.W(1), .ID(7002)) u_twcw (.ck(ck_rd), .d(ptw_we && ptw_kind == 2'd1), .q(twc_crw));
    qfd_dv_s8_kff #(.W(1024), .ID(7100)) u_twpd (.ck(ck_su), .d(ptw_data), .q(twp_d));
    qfd_dv_s8_kff #(.W(9), .ID(7101)) u_twpa (.ck(ck_su), .d(ptw_addr[8:0]), .q(twp_a));
    qfd_dv_s8_kff #(.W(2), .ID(7102)) u_twpw (.ck(ck_su), .d({ptw_we && ptw_kind == 2'd3, ptw_we && ptw_kind == 2'd2}), .q(twp_w));
    // ================================================================ CROM: 2 banks x {lo, hi} (ck_rd)
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
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(ckm[6 + 2*bk]), .r_ce_in(pcr_re[0] && pcr_addr[3] == bk[0]), .r_addr_in(pcr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk)*256 +: 256]), .w_ce_in(twc_crw), .w_addr_in(twc_a), .wd_in(cw_lo[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(ckm[7 + 2*bk]), .r_ce_in(pcr_re[0] && pcr_addr[3] == bk[0]), .r_addr_in(pcr_addr[4 +: 10]),
            .rd_out(cr_rd[(2*bk+1)*256 +: 256]), .w_ce_in(twc_crw), .w_addr_in(twc_a), .wd_in(cw_hi[bk]),
            .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    wire [1:0] c1_bank;
    qfd_dv_s8_kff #(.W(2), .ID(3300)) u_c1 (.ck(ck_rd), .d({2{pcr_addr[3]}}), .q(c1_bank));
    reg [23:0] c1_off;
    reg [1023:0] ccap;
    always @(posedge ck_rd) begin
        for (l = 0; l < 8; l = l + 1) c1_off[3*l +: 3] <= pcr_addr[24*l +: 3];
        ccap <= cr_rd;
    end
    wire [255:0] clo, chi;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_cbk
        wire bq_lo, bq_hi;
        qfd_dv_s8_kff #(.W(1), .ID(3000 + gk)) u_lo (.ck(ck_rd), .d(c1_bank[0]), .q(bq_lo));
        qfd_dv_s8_kff #(.W(1), .ID(3100 + gk)) u_hi (.ck(ck_rd), .d(c1_bank[1]), .q(bq_hi));
        assign clo[16*gk +: 16] = bq_lo ? ccap[256*2 + 16*gk +: 16] : ccap[256*0 + 16*gk +: 16];
        assign chi[16*gk +: 16] = bq_hi ? ccap[256*3 + 16*gk +: 16] : ccap[256*1 + 16*gk +: 16];
    end endgenerate
    wire [8*64-1:0] cr_n;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_cext
        wire [7:0] dec = 8'd1 << c1_off[3*gl +: 3];
        wire [7:0] oh [0:3];
        for (gk = 0; gk < 4; gk = gk + 1) begin : g_c
            qfd_dv_s8_kff #(.W(8), .ID(3200 + 4*gl + gk)) u (.ck(ck_rd), .d(dec), .q(oh[gk]));
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
    always @(posedge ck_rd) cr_q <= cr_n;
    // ================================================================ BTAB (SU copy) x 4 banks x 128 x 256 (ck_su)
    wire [8:0] bs_word = pbs_addr[8:0];
    wire [4*256-1:0] bt_rd;
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ckm[10 + bk]), .r_ce_in(pbs_re && bs_word[1:0] == bk[1:0]), .r_addr_in(bs_word[8:2]),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(twp_w[0]), .w_addr_in(twp_a[8:2]),
            .wd_in(twp_d[256*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg [1:0] s1b_bank;
    reg [1023:0] btcap;
    always @(posedge ck_su) begin s1b_bank <= bs_word[1:0]; btcap <= bt_rd; end
    wire [3:0] bdec = 4'd1 << s1b_bank;
    wire [255:0] bs_n;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_bsel
        wire [3:0] boh;
        qfd_dv_s8_kff #(.W(4), .ID(4000 + gk)) u (.ck(ck_su), .d(bdec), .q(boh));
        assign bs_n[16*gk +: 16] = ({16{boh[0]}} & btcap[256*0 + 16*gk +: 16]) | ({16{boh[1]}} & btcap[256*1 + 16*gk +: 16]) |
                                   ({16{boh[2]}} & btcap[256*2 + 16*gk +: 16]) | ({16{boh[3]}} & btcap[256*3 + 16*gk +: 16]);
    end endgenerate
    always @(posedge ck_su) bs_q <= bs_n;
    // ================================================================ PROG: 2 banks x (256 + 201) x 256 (ck_su)
    wire [4*256-1:0] p_rd;
    generate for (bk = 0; bk < 2; bk = bk + 1) begin : g_prog
        ot_sram_1r1w_256x256_m2_r2c2 u_lo (.clk(ckm[14 + 2*bk]), .r_ce_in(pp_re && pp_idx[0] == bk[0]), .r_addr_in(pp_idx[8:1]),
            .rd_out(p_rd[(2*bk)*256 +: 256]), .w_ce_in(twp_w[1]), .w_addr_in(twp_a[7:0]),
            .wd_in(twp_d[512*bk +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_256x256_m2_r2c2 u_hi (.clk(ckm[15 + 2*bk]), .r_ce_in(pp_re && pp_idx[0] == bk[0]), .r_addr_in(pp_idx[8:1]),
            .rd_out(p_rd[(2*bk+1)*256 +: 256]), .w_ce_in(twp_w[1]), .w_addr_in(twp_a[7:0]),
            .wd_in({55'd0, twp_d[512*bk + 256 +: 201]}), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    wire [3:0] p1_bank;
    qfd_dv_s8_kff #(.W(4), .ID(5100)) u_p1 (.ck(ck_su), .d({4{pp_idx[0]}}), .q(p1_bank));
    reg [1023:0] pcap;
    always @(posedge ck_su) pcap <= p_rd;
    wire [511:0] pw2;
    generate for (gk = 0; gk < 64; gk = gk + 1) begin : g_psel
        wire pq;
        qfd_dv_s8_kff #(.W(1), .ID(5000 + gk)) u (.ck(ck_su), .d(p1_bank[gk / 16]), .q(pq));
        assign pw2[8*gk +: 8] = pq ? pcap[512 + 8*gk +: 8] : pcap[8*gk +: 8];
    end endgenerate
    always @(posedge ck_su) p_q <= {pw2[256 +: 201], pw2[255:0]};
    // ================================================================ faults (sticky; each term registered in its own region)
    function automatic bad_vec(input [7:0] re, input [8*24-1:0] ad);
        integer kk;
        begin
            bad_vec = 1'b0;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re[kk] && (ad[24*kk+4 +: 20] != ad[4 +: 20])) bad_vec = 1'b1;
            for (kk = 0; kk < 8; kk = kk + 1)
                if (re[kk] && (ad[24*kk+3] != ad[3])) bad_vec = 1'b1;
            if (re[0] && (ad[23:14] != 10'd0)) bad_vec = 1'b1;
            if (re != 8'd0 && !re[0]) bad_vec = 1'b1;
        end
    endfunction
    reg rd_bad_q, bs_bad_q, tw_bad_q, tw_bad_q2;
    always @(posedge ck_rd)
        rd_bad_q <= bad_vec(pa_re, pa_addr) || bad_vec(pb_re, pb_addr) || bad_vec(pc_re, pc_addr) ||
                    (pcr_re != 8'd0 && (!pcr_re[0] || pcr_addr[23:14] != 10'd0)) ||
                    (pcr_re != 8'd0 && bad_vec(pcr_re, pcr_addr & {8{24'h003FFF}}));
    always @(posedge ck_su) bs_bad_q <= pbs_re && pbs_addr[23:9] != 0;
    always @(posedge ck_wr) begin
        tw_bad_q <= ptw_we && ((ptw_kind == 2'd0) || (ptw_kind == 2'd1 && ptw_addr[23:10] != 0) ||
                               (ptw_kind == 2'd2 && (ptw_addr[1:0] != 0 || ptw_addr[23:9] != 0)) ||
                               (ptw_kind == 2'd3 && ptw_addr[23:8] != 0));
        tw_bad_q2 <= tw_bad_q;
    end
    always @(posedge ck_wr or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | rd_bad_q | bs_bad_q | tw_bad_q2 | l_wbad3;
endmodule

// single-root wrapper (parallel fallback kit qfd_dv_s5_vm8b: one centre-fed tree, same RTL)
module qfd_dv_s5_vm8s #(parameter integer MUT = 0) (
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
    qfd_dv_s5_vm8 #(.MUT(MUT)) u_vm (.ck_wr(ck), .ck_rd(ck), .ck_su(ck), .ckm0(ck), .ckm1(ck), .ckm2(ck), .ckm3(ck), .ckm4(ck), .ckm5(ck), .ckm6(ck), .ckm7(ck), .ckm8(ck), .ckm9(ck), .ckm10(ck), .ckm11(ck), .ckm12(ck), .ckm13(ck), .ckm14(ck), .ckm15(ck), .ckm16(ck), .ckm17(ck), .rst_n(rst_n),
        .a_re(a_re), .b_re(b_re), .c_re(c_re), .a_addr(a_addr), .b_addr(b_addr), .c_addr(c_addr),
        .a_q(a_q), .b_q(b_q), .c_q(c_q), .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(cr_q),
        .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(bs_q), .p_re(p_re), .p_idx(p_idx), .p_q(p_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data),
        .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_data(tw_data), .fault(fault));
endmodule
