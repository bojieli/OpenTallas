`timescale 1ns/1ps
`default_nettype none
// HC ring bank tiles, REGIONAL-CLOCK successor (HBM-HCBANK6 10-20, H.STA.BLK.17).  Same function, same edges, same
// pins as ot_hbm_hc_bankq*_static (ot_hbm_hc_bankq_static.sv + ot_hbm_hc_bank_static.sv + the LG=8 path of
// ot_hdc_v41x_hcp_stage) PLUS clock entry ports, so the tile is a hybrid_entries cluster instead of one balanced spine:
//   clk            glue CTS root: face/pin mass (beat landing, CPI chain pin flops, write pin flops, reset relays)
//   clk_c          glue CTS root (rc3 tops; = clk in the rc tops): stage control + raw SRAM read capture (wdat/xdat)
//   clk_o          glue CTS root (rc3 tops; = clk in the rc tops): CPO chain pin flops at the out face
//   ck_l[g]        hard lane leaf g (ot_hdc_v41x_hcp_lanes) clock pin -- its own entry, the die delivers phi - R_g
//   ck_w[g]/ck_x[h] raw SRAM clock pins (weight macro g, x macro h) -- direct raw-Liberty entries
// Why (cb_s1 --cts gate 10-19, GATE_STALL in post-GRT hold repair): ONE clk spine of 15,636 buffers over 10,737 sinks
// (8 leaf pins, 12 SRAM pins, 10.7 k glue flops) gave TT insertion 975..1271 ps (spread 296 ps across the glue/leaf/SRAM
// boundary); hold repair then padded ~1.2 k boundary endpoints and stalled.  With entries each leaf / SRAM is compensated
// to the common phase by the die (neighbour-matched boundary) and the glue roots stay small.
// FAN32 (native32 census, mandatory 042aa171b): base census of the bankq netlist = 4 drivers > 32 (beat-slot hold enables
// 3 x 512 loads, stage ss select 64).  Here: 16 KEPT copies of the beat pin flops (xb_v / xb_beat land in 16 copies, each
// copy enables 16 bits of each hold slot: <= 32 loads), and the stage lane-enable sources lvs/sss come from 4 KEPT copies
// of cv[ML] / nv / ss taken one tap earlier (cd[ML-1] -> copy == cd[ML], same edge).  0 added edges anywhere.
// MUT (bench): 1 = weight write slice rotated by one group (as ot_hbm_hc_bank_static MUT 1); 2 = landing copy 5 writes
// the next hold slot (proves the kept copies are the ones that land the beats).
// HBM-HCBANK9 10-21 WROW 1: the write-data register wd_q (one 1,024-b mass feeding all 12 SRAMs, e2_rl clk_a spread 283.5 ps
// TT over 2,817 sinks) is replaced by one KEPT 256-b copy per SRAM, loaded from asm_q on the same edge and clocked by its
// SRAM row's root clk_d[r] (weight SRAMs 2r / 2r+1, x SRAM r); the kit anchors each copy beside its SRAM's wd_in pins.
// Same data, same edge (0 added); WROW 0 = unchanged (clk_d unused).
module ot_hbm_hc_bankrc_core #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0,
    parameter integer WROW = 0)(
    input  wire          clk, clk_c, clk_o,
    // HBM-HCBANK9 10-20: clk_a = write mass (beat assembler hold / asm_q, lb_q, write data wd_q) off the in-face pin root
    // clk (the _rl / _rm cb tops; every older top ties it to clk).
    input  wire          clk_a,
    // HBM-HC7-BANK 10-20: per-lane-row glue roots (row r = lane leaves 2r / 2r+1, weight SRAMs 2r / 2r+1, x SRAM r):
    // clk_ri[r] CPI sum flops of row r, clk_rc[r] SRAM read capture (wdat / xdat) + lane enables (lvs / sss) of row r,
    // clk_q[r] CPO sum flops of row r.  The rc / rc3 tops tie them to clk / clk_c / clk_o (unchanged).
    // HBM-HCBANK9 10-20: clk_rc split into clk_rw[r] (weight SRAM pair 2r / 2r+1 read capture wd), clk_rx[r] (x SRAM r read
    // capture xd) and clk_re[r] (lane enables lv / sv of leaves 2r / 2r+1); older tops pass their clk_rc net to all three.
    input  wire [3:0]    clk_ri, clk_rw, clk_rx, clk_re, clk_q,
    input  wire [3:0]    clk_d,
    input  wire [7:0]    ck_l, ck_w,
    input  wire [3:0]    ck_x,
    input  wire          rst_n, first,
    input  wire          d_v, d_ss, input wire [6:0] d_nv, input wire [9:0] d_wa, d_xa,
    output wire          o_v, o_ss, output wire [6:0] o_nv, output wire [9:0] o_wa, o_xa,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out,
    input  wire          f_in, output wire f_out,
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d,
    input  wire          wv, xv, j, input wire [9:0] wa,
    output reg           wfault
);
    // ---------------- clk: reset relays (identical to bankq core u_rst + bank RST_RELAY 1 u_rst)
    wire [0:0] rc;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rc));
    wire [1:0] rr;
    ot_rst_relay #(.REGIONS(2)) u_rst_b (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn_st = rr[0], rn_w = rr[1];
    // ---------------- clk: beat landing (= ot_hbm_hc_xw_rx_static data path, this bank's slice), FAN32 copies
    (* keep = "true" *) reg [15:0] vq_c;
    (* keep = "true" *) reg [31:0] bq_c;
    reg [255:0] d_q; reg [767:0] hold; reg [1023:0] asm_q;
    always @(posedge clk or negedge rc[0]) if (!rc[0]) vq_c <= 16'd0; else vq_c <= {16{xb_v}};
    always @(posedge clk) begin bq_c <= {16{xb_beat}}; d_q <= xb_d; end
    always @(posedge clk_a) begin
        for (integer k = 0; k < 16; k = k + 1)
            for (integer b = 0; b < 3; b = b + 1)
                if (vq_c[k] && bq_c[2*k +: 2] == ((MUT == 2 && k == 5) ? 2'((b + 1) % 3) : 2'(b)))
                    hold[b*256 + 16*k +: 16] <= d_q[16*k +: 16];
        asm_q <= {d_q, hold};
    end
    reg lb_q, xv_c;
    always @(posedge clk_a) begin
        lb_q <= 1'b0;
        for (integer m = 0; m < 32; m = m + 1) if (|asm_q[m*32 +: 16]) lb_q <= 1'b1;
    end
    always @(posedge clk or negedge rc[0])
        if (!rc[0]) begin xv_c <= 1'b0; wfault <= 1'b0; end
        else begin xv_c <= xv; if (xv_c && lb_q) wfault <= 1'b1; end
    // ---------------- chain pin registers: CPI on clk (in face), CPO on clk_o (out face)
    wire c_v, c_ss, c_f; wire [6:0] c_nv; wire [9:0] c_wa, c_xa; wire [2047:0] c_s;
    wire q_v, q_ss, q_f; wire [6:0] q_nv; wire [9:0] q_wa, q_xa; wire [2047:0] q_s;
    if (CPI != 0) begin : g_cpi
        reg v_r, f_r, ss_r; reg [6:0] nv_r; reg [9:0] wa_r, xa_r; wire [2047:0] s_r;
        // f_in (pin at the far end of the in face, beside lane row 3) lands on row 3's root
        always @(posedge clk or negedge rc[0]) if (!rc[0]) v_r <= 1'b0; else v_r <= d_v;
        always @(posedge clk_ri[3] or negedge rc[0]) if (!rc[0]) f_r <= 1'b0; else f_r <= f_in;
        always @(posedge clk) begin ss_r <= d_ss; nv_r <= d_nv; wa_r <= d_wa; xa_r <= d_xa; end
        for (genvar gi = 0; gi < 8; gi = gi + 1) begin : g_si
            reg [255:0] q;
            always @(posedge clk_ri[gi/2]) q <= sum_in[gi*256 +: 256];
            assign s_r[gi*256 +: 256] = q;
        end
        assign {c_v, c_ss, c_nv, c_wa, c_xa, c_s, c_f} = {v_r, ss_r, nv_r, wa_r, xa_r, s_r, f_r};
    end else begin : g_ncpi
        assign {c_v, c_ss, c_nv, c_wa, c_xa, c_s, c_f} = {d_v, d_ss, d_nv, d_wa, d_xa, sum_in, f_in};
    end
    if (CPO != 0) begin : g_cpo
        reg v_r, f_r, ss_r; reg [6:0] nv_r; reg [9:0] wa_r, xa_r; wire [2047:0] s_r;
        // f_out (pin at the far end of the out face, beside lane row 3's CPO slice) on row 3's CPO root
        always @(posedge clk_o or negedge rc[0]) if (!rc[0]) v_r <= 1'b0; else v_r <= q_v;
        always @(posedge clk_q[3] or negedge rc[0]) if (!rc[0]) f_r <= 1'b0; else f_r <= q_f;
        always @(posedge clk_o) begin ss_r <= q_ss; nv_r <= q_nv; wa_r <= q_wa; xa_r <= q_xa; end
        for (genvar go = 0; go < 8; go = go + 1) begin : g_so
            reg [255:0] q;
            always @(posedge clk_q[go/2]) q <= q_s[go*256 +: 256];
            assign s_r[go*256 +: 256] = q;
        end
        assign {o_v, o_ss, o_nv, o_wa, o_xa, sum_out, f_out} = {v_r, ss_r, nv_r, wa_r, xa_r, s_r, f_r};
    end else begin : g_ncpo
        assign {o_v, o_ss, o_nv, o_wa, o_xa, sum_out, f_out} = {q_v, q_ss, q_nv, q_wa, q_xa, q_s, q_f};
    end
    // ---------------- clk: write pin registers (ot_hbm_hc_bank_static)
    reg wv_q, xv_q, j_q; reg [9:0] wa_q; reg [1023:0] wd_q;
    always @(posedge clk or negedge rn_w) if (!rn_w) begin wv_q <= 1'b0; xv_q <= 1'b0; end else begin wv_q <= wv; xv_q <= xv; end
    always @(posedge clk) begin j_q <= j; wa_q <= wa; end
    always @(posedge clk_a) wd_q <= asm_q;
    wire [1023:0] wsrc = (WROW != 0) ? asm_q : wd_q;     // WROW 1: per-SRAM copies load asm_q (wd_q then unused)
    // ---------------- clk_c: stage control (ot_hdc_v41x_hcp_stage W 64, AW 10, ML 2, LA 7, SOR 1, LG 8)
    localparam integer ML = 2, NC = 8, DW = 29, OT = 8;      // NC = max(1 + ML, LA + SOR); out tap LA + SOR
    reg [NC:0] cv; reg [DW-2:0] cd [0:NC];
    reg fin_q, f_o, w_re, x_re; reg [9:0] w_addr, x_addr;
    wire [7:0] lfg; wire lf_any = |lfg;
    always @(posedge clk_c or negedge rn_st) begin
        if (!rn_st) begin cv <= '0; w_re <= 1'b0; x_re <= 1'b0; fin_q <= 1'b0; f_o <= 1'b0; end
        else begin
            cv <= {cv[NC-1:0], c_v};
            w_re <= cv[0] && !cd[0][DW-2];
            x_re <= cv[0];
            fin_q <= c_f;
            f_o <= fin_q || lf_any;
        end
    end
    always @(posedge clk_c) begin
        cd[0] <= {c_ss, c_nv, c_wa, c_xa};
        for (integer t = 1; t <= NC; t = t + 1) cd[t] <= cd[t-1];
        w_addr <= cd[0][19:10];
        x_addr <= cd[0][9:0];
    end
    assign q_v = cv[OT]; assign {q_ss, q_nv, q_wa, q_xa} = cd[OT]; assign q_f = f_o;
    // lane enables (task at local ML) from 4 kept copies of cv[ML] / nv / ss, each loaded from tap ML - 1
    (* keep = "true" *) reg [3:0] cvc;
    (* keep = "true" *) reg [27:0] nvc;
    (* keep = "true" *) reg [3:0] ssc;
    always @(posedge clk_c or negedge rn_st) if (!rn_st) cvc <= 4'd0; else cvc <= {4{cv[ML-1]}};
    always @(posedge clk_c) begin nvc <= {4{cd[ML-1][DW-3 -: 7]}}; ssc <= {4{cd[ML-1][DW-2]}}; end
    wire [63:0] lvs, sss;
    for (genvar rl = 0; rl < 4; rl = rl + 1) begin : g_le            // lanes 16 rl .. 16 rl + 15 = leaves 2 rl / 2 rl + 1
        (* keep = "true" *) reg [15:0] lv, sv;
        always @(posedge clk_re[rl]) for (integer l = 0; l < 16; l = l + 1) begin
            lv[l] <= cvc[rl] && (7'(16 * rl + l) < nvc[rl*7 +: 7]);
            sv[l] <= ssc[rl];
        end
        assign lvs[16*rl +: 16] = lv; assign sss[16*rl +: 16] = sv;
    end
    reg ov_r;
    always @(posedge clk_c or negedge rn_st) if (!rn_st) ov_r <= 1'b0; else ov_r <= cv[1 + ML];
    // ---------------- macros: weight (ck_w), x (ck_x); raw capture on clk_c (ML = 2)
    wire [2047:0] wq; wire [1023:0] xq;
    wire [2047:0] wdat; wire [1023:0] xdat;
    genvar g, h, i;
    generate for (g = 0; g < 8; g = g + 1) begin : g_w
        localparam integer GS = (MUT == 1) ? ((g + 1) % 8) : g;
        wire we = wv_q && (j_q == 1'(GS / 4));
        wire [255:0] d;
        wire [255:0] ds;
        for (i = 0; i < 8; i = i + 1) begin : g_l
            assign ds[32*i +: 32] = wsrc[(8*(GS % 4) + i)*32 +: 32];
        end
        if (WROW != 0) begin : g_wr
            (* keep = "true" *) reg [255:0] wr;
            always @(posedge clk_d[g/2]) wr <= ds;
            assign d = wr;
        end else begin : g_nwr
            assign d = ds;
        end
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(ck_w[g]), .r_ce_in(w_re), .r_addr_in(w_addr), .rd_out(wq[g*256 +: 256]),
            .w_ce_in(we), .w_addr_in(wa_q), .wd_in(d), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(18'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
    end
    for (h = 0; h < 4; h = h + 1) begin : g_x
        wire we = xv_q && (j_q == 1'(h / 2));
        wire [255:0] d;
        wire [255:0] ds;
        for (i = 0; i < 16; i = i + 1) begin : g_l
            assign ds[16*i +: 16] = wsrc[(16*(h % 2) + i)*32 + 16 +: 16];
        end
        if (WROW != 0) begin : g_wr
            (* keep = "true" *) reg [255:0] wr;
            always @(posedge clk_d[h]) wr <= ds;
            assign d = wr;
        end else begin : g_nwr
            assign d = ds;
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck_x[h]), .r_ce_in(x_re), .r_addr_in(x_addr[6:0]), .rd_out(xq[h*256 +: 256]),
            .w_ce_in(we), .w_addr_in(wa_q[6:0]), .wd_in(d), .w_mask_in({256{1'b1}}), .rr_en(2'b00), .rr_addr(14'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    for (genvar rq = 0; rq < 4; rq = rq + 1) begin : g_cap         // row rq: weight SRAMs 2 rq / 2 rq + 1, x SRAM rq
        reg [511:0] wd; reg [255:0] xd;
        always @(posedge clk_rw[rq]) wd <= wq[rq*512 +: 512];
        always @(posedge clk_rx[rq]) xd <= xq[rq*256 +: 256];
        assign wdat[rq*512 +: 512] = wd; assign xdat[rq*256 +: 256] = xd;
    end
    // ---------------- hard lane leaves (own entries), instantiated without overrides
    for (genvar gg = 0; gg < 8; gg = gg + 1) begin : g_grp
        ot_hdc_v41x_hcp_lanes u_lg (.clk(ck_l[gg]), .rst_n(rn_st), .fst(first), .gov_i(ov_r), .lv_i(lvs[gg*8 +: 8]),
            .ss_i(sss[gg*8 +: 8]), .w_i(wdat[gg*256 +: 256]), .x_i(xdat[gg*128 +: 128]),
            .s_i(c_s[gg*256 +: 256]), .y(q_s[gg*256 +: 256]), .lf(lfg[gg]));
    end
endmodule

`define OT_HCB_RC_CHAIN \
    input  wire          d_v, d_ss, input wire [6:0] d_nv, input wire [9:0] d_wa, d_xa, \
    output wire          o_v, o_ss, output wire [6:0] o_nv, output wire [9:0] o_wa, o_xa, \
    input  wire          xb_v, input wire [1:0] xb_beat, input wire [255:0] xb_d, \
    input  wire          wv, xv, j, input wire [9:0] wa, \
    output wire          wfault
`define OT_HCB_RC_CONN \
    .ck_l(ck_l), .ck_w(ck_w), .ck_x(ck_x), .rst_n(rst_n), \
    .d_v(d_v), .d_ss(d_ss), .d_nv(d_nv), .d_wa(d_wa), .d_xa(d_xa), .o_v(o_v), .o_ss(o_ss), .o_nv(o_nv), \
    .o_wa(o_wa), .o_xa(o_xa), .xb_v(xb_v), .xb_beat(xb_beat), .xb_d(xb_d), .wv(wv), .xv(xv), .j(j), .wa(wa), .wfault(wfault)

// plain ring bank (positions 1, 3, 4, 5, 7): one glue root clk (+ 8 leaf + 12 SRAM entries)
module ot_hbm_hc_bankq_rc_static #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0)(
    input  wire clk, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (.clk(clk), .clk_c(clk), .clk_o(clk), .clk_ri({4{clk}}), .clk_a(clk), .clk_rw({4{clk}}), .clk_rx({4{clk}}), .clk_re({4{clk}}), .clk_q({4{clk}}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
// plain ring bank, three regional glue roots: clk (in face), clk_c (stage + SRAM capture), clk_o (out face)
module ot_hbm_hc_bankq_rc3_static #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0)(
    input  wire clk, clk_c, clk_o, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (.clk(clk), .clk_c(clk_c), .clk_o(clk_o), .clk_ri({4{clk}}), .clk_a(clk), .clk_rw({4{clk_c}}), .clk_rx({4{clk_c}}), .clk_re({4{clk_c}}),
        .clk_q({4{clk_o}}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule

// first ring bank (b0): chain start + bank 7's chain-exit relay (DRLY registers on clk)
`define OT_HCB_RC0_BODY \
    initial if (DRLY < 1) $fatal(1, "DRLY >= 1 (the chain exit is registered here)"); \
    reg [2048:0] sr [0:DRLY-1]; \
    always @(posedge clk) begin \
        sr[0] <= s_i; \
        for (integer i = 1; i < DRLY; i = i + 1) sr[i] <= sr[i-1]; \
    end \
    assign s_o = sr[DRLY-1];
module ot_hbm_hc_bankq0_rc_static #(parameter integer MUT = 0, parameter integer DRLY = 1, parameter integer CPO = 0)(
    input  wire clk, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    output wire [2047:0] sum_out, output wire f_out, input wire [2048:0] s_i, output wire [2048:0] s_o
);
    `OT_HCB_RC0_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPO(CPO)) u_c (.clk(clk), .clk_c(clk), .clk_o(clk), .clk_ri({4{clk}}), .clk_a(clk), .clk_rw({4{clk}}), .clk_rx({4{clk}}), .clk_re({4{clk}}), .clk_q({4{clk}}), .first(1'b1),
        `OT_HCB_RC_CONN, .sum_in(2048'd0), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq0_rc3_static #(parameter integer MUT = 0, parameter integer DRLY = 1, parameter integer CPO = 0)(
    input  wire clk, clk_c, clk_o, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    output wire [2047:0] sum_out, output wire f_out, input wire [2048:0] s_i, output wire [2048:0] s_o
);
    `OT_HCB_RC0_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPO(CPO)) u_c (.clk(clk), .clk_c(clk_c), .clk_o(clk_o), .clk_ri({4{clk}}), .clk_a(clk), .clk_rw({4{clk_c}}), .clk_rx({4{clk_c}}), .clk_re({4{clk_c}}),
        .clk_q({4{clk_o}}), .first(1'b1),
        `OT_HCB_RC_CONN, .sum_in(2048'd0), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out));
endmodule

// edge bank N/S (positions 2, 6) + registered feed of its two ring-corner neighbours (feed regs on clk)
`define OT_HCB_RCFT_PORTS \
    input  wire          fa_xb_v, input wire [1:0] fa_xb_beat, input wire [255:0] fa_xb_d, \
    input  wire          fa_wv, fa_xv, fa_j, input wire [9:0] fa_wa, \
    output reg           fa_xb_v_o, output reg [1:0] fa_xb_beat_o, output reg [255:0] fa_xb_d_o, \
    output reg           fa_wv_o, fa_xv_o, fa_j_o, output reg [9:0] fa_wa_o, \
    input  wire          fb_xb_v, input wire [1:0] fb_xb_beat, input wire [255:0] fb_xb_d, \
    input  wire          fb_wv, fb_xv, fb_j, input wire [9:0] fb_wa, \
    output reg           fb_xb_v_o, output reg [1:0] fb_xb_beat_o, output reg [255:0] fb_xb_d_o, \
    output reg           fb_wv_o, fb_xv_o, fb_j_o, output reg [9:0] fb_wa_o, \
    input  wire          fa_rst_n, fb_rst_n, output wire fa_rst_n_o, fb_rst_n_o, \
    input  wire          fa_wfault, fb_wfault, output reg fa_wfault_o, fb_wfault_o
`define OT_HCB_RCFT_BODY \
    assign fa_rst_n_o = fa_rst_n; assign fb_rst_n_o = fb_rst_n; \
    wire [1:0] rf; \
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rf)); \
    always @(posedge clk or negedge rf[0]) \
        if (!rf[0]) begin fa_xb_v_o <= 1'b0; fa_wv_o <= 1'b0; fa_xv_o <= 1'b0; fa_wfault_o <= 1'b0; end \
        else begin fa_xb_v_o <= fa_xb_v; fa_wv_o <= fa_wv; fa_xv_o <= fa_xv; fa_wfault_o <= fa_wfault; end \
    always @(posedge clk or negedge rf[1]) \
        if (!rf[1]) begin fb_xb_v_o <= 1'b0; fb_wv_o <= 1'b0; fb_xv_o <= 1'b0; fb_wfault_o <= 1'b0; end \
        else begin fb_xb_v_o <= fb_xb_v; fb_wv_o <= fb_wv; fb_xv_o <= fb_xv; fb_wfault_o <= fb_wfault; end \
    always @(posedge clk) begin \
        fa_xb_beat_o <= fa_xb_beat; fa_xb_d_o <= fa_xb_d; fa_j_o <= fa_j; fa_wa_o <= fa_wa; \
        fb_xb_beat_o <= fb_xb_beat; fb_xb_d_o <= fb_xb_d; fb_j_o <= fb_j; fb_wa_o <= fb_wa; \
    end
module ot_hbm_hc_bankq_ft_rc_static #(parameter integer MUT = 0)(
    input  wire clk, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_RCFT_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT)) u_c (.clk(clk), .clk_c(clk), .clk_o(clk), .clk_ri({4{clk}}), .clk_a(clk), .clk_rw({4{clk}}), .clk_rx({4{clk}}), .clk_re({4{clk}}), .clk_q({4{clk}}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq_ft_rc3_static #(parameter integer MUT = 0)(
    input  wire clk, clk_c, clk_o, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_RCFT_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT)) u_c (.clk(clk), .clk_c(clk_c), .clk_o(clk_o), .clk_ri({4{clk}}), .clk_a(clk), .clk_rw({4{clk_c}}), .clk_rx({4{clk_c}}), .clk_re({4{clk_c}}),
        .clk_q({4{clk_o}}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
// ================= HBM-HC7-BANK 10-20: lane-row regional glue roots (successor of the rc3 tops) =================
// rc3 --cts gates FAILED at CTS (0dq rule): glue root clk pin-flop spread 354.9 ps (cb, 2,398 boundary of 5,221 sinks,
// avg sink wire 1,301 um) and 674.3 ps (b0, 4,418 of 7,241 incl. the 2 x 2,049 exit-relay flops).  Placement evidence
// (cb_rc3 3_place.odb): the CPI sum flops sit beside their own lane leaves (x 350..632) and the SRAM capture / lane
// enables beside their row, so every 2,048-bit group is row-local; one root per face spanned the whole 777 x 734 tile
// around 12 SRAMs.  Here every glue root covers ONE compact region:
//   clk         in-face landing / write port / reset relays / CPI scalars (W-S corner, x <= ~380, y <= ~350)
//   clk_c       stage control (cv / cd / addresses / lane-enable copies)
//   clk_o       CPO scalars (out-face control pins, x 130..140)
//   clk_r<r>    row r: CPI sums of leaves 2r / 2r+1 + SRAM read capture + lane enables (one lane-row strip)
//   clk_q<r>    row r: CPO sums of leaves 2r / 2r+1 (between the row and the out face)
//   b0 only: clk_s0 = exit-relay stage 0 (s_i face), clk_s1 = exit-relay stages >= 1 (s_o face)
// _rr tops: 4 row roots each; _rh tops (parallel fallback): 2 half-tile roots each (rows 0-1, rows 2-3).
// Same function, same edges (0 added), only clock-net partition; cross-root paths are same-source in-tile (< 1 mm) STA.
`define OT_HCB_RR_ROOTS input wire clk, clk_c, clk_o, clk_r0, clk_r1, clk_r2, clk_r3, clk_q0, clk_q1, clk_q2, clk_q3,
`define OT_HCB_RH_ROOTS input wire clk, clk_c, clk_o, clk_r0, clk_r1, clk_q0, clk_q1,
`define OT_HCB_RR_V .clk(clk), .clk_c(clk_c), .clk_o(clk_o), .clk_ri({clk_r3, clk_r2, clk_r1, clk_r0}), \
    .clk_a(clk), .clk_rw({clk_r3, clk_r2, clk_r1, clk_r0}), .clk_rx({clk_r3, clk_r2, clk_r1, clk_r0}), .clk_re({clk_r3, clk_r2, clk_r1, clk_r0}), .clk_q({clk_q3, clk_q2, clk_q1, clk_q0})
`define OT_HCB_RH_V .clk(clk), .clk_c(clk_c), .clk_o(clk_o), .clk_ri({clk_r1, clk_r1, clk_r0, clk_r0}), \
    .clk_a(clk), .clk_rw({clk_r1, clk_r1, clk_r0, clk_r0}), .clk_rx({clk_r1, clk_r1, clk_r0, clk_r0}), .clk_re({clk_r1, clk_r1, clk_r0, clk_r0}), .clk_q({clk_q1, clk_q1, clk_q0, clk_q0})
module ot_hbm_hc_bankq_rr_static #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0)(
    `OT_HCB_RR_ROOTS input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (`OT_HCB_RR_V, .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq_rh_static #(parameter integer MUT = 0, parameter integer CPI = 0, parameter integer CPO = 0)(
    `OT_HCB_RH_ROOTS input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (`OT_HCB_RH_V, .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
// b0 exit relay on its own face roots: stage 0 (lands s_i) on clk_s0, stages >= 1 (drive s_o) on clk_s1
`define OT_HCB_RR0_BODY \
    initial if (DRLY < 2) $fatal(1, "DRLY >= 2 (stage 0 at the s_i face, last stage at the s_o face)"); \
    reg [2048:0] sr [0:DRLY-1]; \
    always @(posedge clk_s0) sr[0] <= s_i; \
    always @(posedge clk_s1) for (integer i = 1; i < DRLY; i = i + 1) sr[i] <= sr[i-1]; \
    assign s_o = sr[DRLY-1];
module ot_hbm_hc_bankq0_rr_static #(parameter integer MUT = 0, parameter integer DRLY = 2, parameter integer CPO = 0)(
    `OT_HCB_RR_ROOTS input wire clk_s0, clk_s1, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    output wire [2047:0] sum_out, output wire f_out, input wire [2048:0] s_i, output wire [2048:0] s_o
);
    `OT_HCB_RR0_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPO(CPO)) u_c (`OT_HCB_RR_V, .first(1'b1),
        `OT_HCB_RC_CONN, .sum_in(2048'd0), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq0_rh_static #(parameter integer MUT = 0, parameter integer DRLY = 2, parameter integer CPO = 0)(
    `OT_HCB_RH_ROOTS input wire clk_s0, clk_s1, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    output wire [2047:0] sum_out, output wire f_out, input wire [2048:0] s_i, output wire [2048:0] s_o
);
    `OT_HCB_RR0_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPO(CPO)) u_c (`OT_HCB_RH_V, .first(1'b1),
        `OT_HCB_RC_CONN, .sum_in(2048'd0), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out));
endmodule
// edge bank (bench completeness): feed registers stay on clk
module ot_hbm_hc_bankq_ft_rr_static #(parameter integer MUT = 0)(
    `OT_HCB_RR_ROOTS input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_RCFT_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT)) u_c (`OT_HCB_RR_V, .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq_ft_rh_static #(parameter integer MUT = 0)(
    `OT_HCB_RH_ROOTS input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_RCFT_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT)) u_c (`OT_HCB_RH_V, .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
// ================= HBM-HCBANK9 10-20: one root per compact register mass (successor of the _rr / _rp tops) =================
// _rr / _rp --cts gates FAILED (b0_rp clk_r0 150.2 ps TT internal-only over 800 sinks; cb_rw clk boundary 136.5 ps TT).
// 3_place.odb evidence: b0 clk_r0 = weight capture wd (512, beside the SRAM pair) + x capture xd (256, 190 um W of the x
// SRAM) + lane enables (32, beside the leaves, 200-390 um away) -> three separated clusters on one tree; clk_q0 (CPO sums,
// unanchored) spread along the 550 um leaf -> out-face path; cb_rw clk = W-face pin flops + 2.8 k write-mass flops 300-770 um
// E of them.  Here each glue root is ONE register mass, and the kit anchors that mass beside the pins it serves
// (io_flop_at_pins macro_out_pins rd_out / y, macro_pins lv_i / ss_i, in-face port flops):
//   clk        in-face pin flops (beat landing d_q / copies, write scalars, CPI scalars), reset relays
//   clk_a      write mass: hold / asm_q / lb_q / wd_q (cb tops; b0_rm keeps it on clk, b0's in face is beside the SRAMs)
//   clk_c      stage control (unchanged)            clk_o   CPO scalars (unchanged)
//   clk_w<r>   wd capture of weight SRAMs 2r / 2r+1 (beside their rd_out)    clk_x<r>  xd capture of x SRAM r (beside rd_out)
//   clk_r<r>   (_rm) = clk_w<r> + clk_x<r> on one root per SRAM row
//   clk_e<r>   lane enables lv / sv of leaves 2r / 2r+1 (beside the leaf lv_i / ss_i pins)
//   clk_i<r>   CPI sums of leaves 2r / 2r+1 (cb: anchored at the in face)   clk_q<r>  CPO sums of leaves 2r / 2r+1 (beside y)
// Same function, same edges (0 added): only the clock-net partition changes.  Cross-root paths stay same-source in-tile
// entries (the die forest delivers every entry at phi - R) and are STA-timed, exactly as the _rr crossings.
`define OT_HCB_RL_ROOTS input wire clk, clk_c, clk_o, clk_w0, clk_w1, clk_w2, clk_w3, clk_x0, clk_x1, clk_x2, clk_x3, \
    clk_e0, clk_e1, clk_e2, clk_e3, clk_q0, clk_q1, clk_q2, clk_q3,
`define OT_HCB_RM_ROOTS input wire clk, clk_c, clk_o, clk_r0, clk_r1, clk_r2, clk_r3, \
    clk_e0, clk_e1, clk_e2, clk_e3, clk_q0, clk_q1, clk_q2, clk_q3,
`define OT_HCB_CPI_ROOTS input wire clk_i0, clk_i1, clk_i2, clk_i3,
`define OT_HCB_RL_V .clk(clk), .clk_c(clk_c), .clk_o(clk_o), .clk_rw({clk_w3, clk_w2, clk_w1, clk_w0}), \
    .clk_rx({clk_x3, clk_x2, clk_x1, clk_x0}), .clk_re({clk_e3, clk_e2, clk_e1, clk_e0}), .clk_q({clk_q3, clk_q2, clk_q1, clk_q0})
`define OT_HCB_RM_V .clk(clk), .clk_c(clk_c), .clk_o(clk_o), .clk_rw({clk_r3, clk_r2, clk_r1, clk_r0}), \
    .clk_rx({clk_r3, clk_r2, clk_r1, clk_r0}), .clk_re({clk_e3, clk_e2, clk_e1, clk_e0}), .clk_q({clk_q3, clk_q2, clk_q1, clk_q0})
module ot_hbm_hc_bankq_rl_static #(parameter integer MUT = 0, parameter integer CPI = 1, parameter integer CPO = 1)(
    `OT_HCB_RL_ROOTS input wire clk_a, `OT_HCB_CPI_ROOTS input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    initial if (CPI == 0 || CPO == 0) $fatal(1, "_rl bank: CPI = CPO = 1 (its clk_i / clk_q roots clock the chain pin registers)");
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (`OT_HCB_RL_V, .clk_a(clk_a),
        .clk_ri({clk_i3, clk_i2, clk_i1, clk_i0}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq_rm_static #(parameter integer MUT = 0, parameter integer CPI = 1, parameter integer CPO = 1)(
    `OT_HCB_RM_ROOTS input wire clk_a, `OT_HCB_CPI_ROOTS input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    initial if (CPI == 0 || CPO == 0) $fatal(1, "_rm bank: CPI = CPO = 1 (its clk_i / clk_q roots clock the chain pin registers)");
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO)) u_c (`OT_HCB_RM_V, .clk_a(clk_a),
        .clk_ri({clk_i3, clk_i2, clk_i1, clk_i0}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
// b0: no CPI (chain start); _rl splits the write mass to clk_a, _rm keeps it on clk (b0_rp clk boundary 43.9 ps PASS)
module ot_hbm_hc_bankq0_rl_static #(parameter integer MUT = 0, parameter integer DRLY = 2, parameter integer CPO = 1)(
    `OT_HCB_RL_ROOTS input wire clk_a, clk_s0, clk_s1, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    output wire [2047:0] sum_out, output wire f_out, input wire [2048:0] s_i, output wire [2048:0] s_o
);
    initial if (CPO == 0) $fatal(1, "_rl b0: CPO = 1 (its clk_q roots clock the chain pin registers)");
    `OT_HCB_RR0_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPO(CPO)) u_c (`OT_HCB_RL_V, .clk_a(clk_a), .clk_ri({4{clk}}), .first(1'b1),
        `OT_HCB_RC_CONN, .sum_in(2048'd0), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq0_rm_static #(parameter integer MUT = 0, parameter integer DRLY = 2, parameter integer CPO = 1)(
    `OT_HCB_RM_ROOTS input wire clk_s0, clk_s1, input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    output wire [2047:0] sum_out, output wire f_out, input wire [2048:0] s_i, output wire [2048:0] s_o
);
    initial if (CPO == 0) $fatal(1, "_rm b0: CPO = 1 (its clk_q roots clock the chain pin registers)");
    `OT_HCB_RR0_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPO(CPO)) u_c (`OT_HCB_RM_V, .clk_a(clk), .clk_ri({4{clk}}), .first(1'b1),
        `OT_HCB_RC_CONN, .sum_in(2048'd0), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out));
endmodule
// edge bank N/S (e2, positions 2 / 6): no chain pin registers (CPI = CPO = 0), feed registers on clk -> no clk_i / clk_q /
// clk_o sinks; _rl = clk, clk_a, clk_c + per-SRAM capture / lane-enable roots, _rm = capture on one root per SRAM row.
module ot_hbm_hc_bankq_ft_rl_static #(parameter integer MUT = 0)(
    input wire clk, clk_a, clk_c, clk_w0, clk_w1, clk_w2, clk_w3, clk_x0, clk_x1, clk_x2, clk_x3, clk_e0, clk_e1, clk_e2, clk_e3,
    input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_RCFT_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT)) u_c (.clk(clk), .clk_c(clk_c), .clk_o(clk), .clk_a(clk_a), .clk_ri({4{clk}}),
        .clk_rw({clk_w3, clk_w2, clk_w1, clk_w0}), .clk_rx({clk_x3, clk_x2, clk_x1, clk_x0}),
        .clk_re({clk_e3, clk_e2, clk_e1, clk_e0}), .clk_q({4{clk}}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq_ft_rm_static #(parameter integer MUT = 0)(
    input wire clk, clk_a, clk_c, clk_r0, clk_r1, clk_r2, clk_r3, clk_e0, clk_e1, clk_e2, clk_e3,
    input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_RCFT_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT)) u_c (.clk(clk), .clk_c(clk_c), .clk_o(clk), .clk_a(clk_a), .clk_ri({4{clk}}),
        .clk_rw({clk_r3, clk_r2, clk_r1, clk_r0}), .clk_rx({clk_r3, clk_r2, clk_r1, clk_r0}),
        .clk_re({clk_e3, clk_e2, clk_e1, clk_e0}), .clk_q({4{clk}}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
// ================= HBM-HCBANK9 10-21: _rw2 / _rw3 = _rl + per-SRAM write-data copies on per-row roots clk_d0..3 (WROW 1) ======
// e2_rl --cts gate: clk_a (hold / asm_q / lb_q / wd_q, 2,817 sinks) spread 283.5 ps TT.  The 1,024-b wd_q that fed all 12
// SRAMs becomes 12 kept 256-b copies beside their SRAM's wd_in (clk_d<r> per SRAM row).  _rw2: hold / asm_q / lb_q stay on
// clk_a (cb, e2); _rw3: on clk (cb, e2: in-face root, boundary-scoped); b0_rw2: on clk (b0's in face is beside the SRAMs).
`define OT_HCB_RW_CK input wire clk_d0, clk_d1, clk_d2, clk_d3,
`define OT_HCB_RW_V .clk_d({clk_d3, clk_d2, clk_d1, clk_d0})
module ot_hbm_hc_bankq_rw2_static #(parameter integer MUT = 0, parameter integer CPI = 1, parameter integer CPO = 1)(
    `OT_HCB_RL_ROOTS input wire clk_a, `OT_HCB_CPI_ROOTS `OT_HCB_RW_CK input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    initial if (CPI == 0 || CPO == 0) $fatal(1, "_rw2 bank: CPI = CPO = 1");
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO), .WROW(1)) u_c (`OT_HCB_RL_V, .clk_a(clk_a), `OT_HCB_RW_V,
        .clk_ri({clk_i3, clk_i2, clk_i1, clk_i0}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq_rw3_static #(parameter integer MUT = 0, parameter integer CPI = 1, parameter integer CPO = 1)(
    `OT_HCB_RL_ROOTS `OT_HCB_CPI_ROOTS `OT_HCB_RW_CK input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out
);
    initial if (CPI == 0 || CPO == 0) $fatal(1, "_rw3 bank: CPI = CPO = 1");
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPI(CPI), .CPO(CPO), .WROW(1)) u_c (`OT_HCB_RL_V, .clk_a(clk), `OT_HCB_RW_V,
        .clk_ri({clk_i3, clk_i2, clk_i1, clk_i0}), .first(1'b0),
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
endmodule
module ot_hbm_hc_bankq0_rw2_static #(parameter integer MUT = 0, parameter integer DRLY = 2, parameter integer CPO = 1)(
    `OT_HCB_RL_ROOTS input wire clk_s0, clk_s1, `OT_HCB_RW_CK input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    output wire [2047:0] sum_out, output wire f_out, input wire [2048:0] s_i, output wire [2048:0] s_o
);
    initial if (CPO == 0) $fatal(1, "_rw2 b0: CPO = 1");
    `OT_HCB_RR0_BODY
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .CPO(CPO), .WROW(1)) u_c (`OT_HCB_RL_V, .clk_a(clk), `OT_HCB_RW_V, .clk_ri({4{clk}}), .first(1'b1),
        `OT_HCB_RC_CONN, .sum_in(2048'd0), .sum_out(sum_out), .f_in(1'b0), .f_out(f_out));
endmodule
`define OT_HCB_FTRW_BODY(CKA) \
    `OT_HCB_RCFT_BODY \
    ot_hbm_hc_bankrc_core #(.MUT(MUT), .WROW(1)) u_c (.clk(clk), .clk_c(clk_c), .clk_o(clk), .clk_a(CKA), .clk_ri({4{clk}}), \
        .clk_rw({clk_w3, clk_w2, clk_w1, clk_w0}), .clk_rx({clk_x3, clk_x2, clk_x1, clk_x0}), \
        .clk_re({clk_e3, clk_e2, clk_e1, clk_e0}), .clk_q({4{clk}}), `OT_HCB_RW_V, .first(1'b0), \
        `OT_HCB_RC_CONN, .sum_in(sum_in), .sum_out(sum_out), .f_in(f_in), .f_out(f_out));
module ot_hbm_hc_bankq_ft_rw2_static #(parameter integer MUT = 0)(
    input wire clk, clk_a, clk_c, clk_w0, clk_w1, clk_w2, clk_w3, clk_x0, clk_x1, clk_x2, clk_x3, clk_e0, clk_e1, clk_e2, clk_e3,
    `OT_HCB_RW_CK input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_FTRW_BODY(clk_a)
endmodule
module ot_hbm_hc_bankq_ft_rw3_static #(parameter integer MUT = 0)(
    input wire clk, clk_c, clk_w0, clk_w1, clk_w2, clk_w3, clk_x0, clk_x1, clk_x2, clk_x3, clk_e0, clk_e1, clk_e2, clk_e3,
    `OT_HCB_RW_CK input wire [7:0] ck_l, ck_w, input wire [3:0] ck_x, input wire rst_n,
    `OT_HCB_RC_CHAIN,
    input  wire [2047:0] sum_in, output wire [2047:0] sum_out, input wire f_in, output wire f_out,
    `OT_HCB_RCFT_PORTS
);
    `OT_HCB_FTRW_BODY(clk)
endmodule
`undef OT_HCB_FTRW_BODY
`undef OT_HCB_RW_CK
`undef OT_HCB_RW_V
`undef OT_HCB_RL_ROOTS
`undef OT_HCB_RM_ROOTS
`undef OT_HCB_CPI_ROOTS
`undef OT_HCB_RL_V
`undef OT_HCB_RM_V
`undef OT_HCB_RR_ROOTS
`undef OT_HCB_RH_ROOTS
`undef OT_HCB_RR_V
`undef OT_HCB_RH_V
`undef OT_HCB_RR0_BODY
`undef OT_HCB_RC_CHAIN
`undef OT_HCB_RC_CONN
`undef OT_HCB_RC0_BODY
`undef OT_HCB_RCFT_PORTS
`undef OT_HCB_RCFT_BODY
`default_nettype wire
