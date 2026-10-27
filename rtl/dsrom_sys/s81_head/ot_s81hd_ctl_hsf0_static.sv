`timescale 1ns/1ps
// Current head controller composition derived from source-pinned HSF0 controller 04718b43a5.
// Rank arithmetic, result/MTP composition and stage forwarding preserve the historical implementation.
// Issue authority is compiled START dates; physical codecs are in ot_s81hd_ctl_core.
// The current spine root already merges north/south; feeding both comparison inputs the same
// root record preserves that record exactly and retains the established two-edge pick latency.
module ot_s81hd_ctl_hsf0_static #(parameter integer SK=11, parameter integer MUT_STATIC=0, parameter integer MUT_DRAFT_EARLY=0) (
    input wire start_i, input wire adapter_fault,
    output wire job_active_o,
    input  wire              ck,
    input  wire              rst_n,
    // stage-circuit endpoint (ot_s81hd_lep, ring form)
    input  wire [1103:0]     ri,
    input  wire [31:0]       mu_rt,
    input  wire [10:0]       lw,
    input  wire              lep_f,
    output wire [1103:0]     ro,
    output wire [33:0]       mu_c,
    output wire [10:0]       mu_rc,
    output wire              ctl_f,
    // spines (bus B)
    output wire [564:0]      sn_o,
    output wire [564:0]      ss_o,
    input  wire [564:0]      sn_i,
    input  wire [564:0]      ss_i,
    // 6 TP4 mesh lanes
    output wire [5:0]        mtx_v,
    output wire [6*553-1:0]  mtx_d,
    input  wire [5:0]        mrx_v,
    input  wire [6*553-1:0]  mrx_d,
    input  wire [23:0]       mflt,
    // 2 host lanes
    output wire [1:0]        htx_v,
    output wire [2*553-1:0]  htx_d,
    input  wire [1:0]        hrx_v,
    input  wire [2*553-1:0]  hrx_d,
    input  wire [7:0]        hflt,
    // 5 draft lanes
    output wire [0:0]        dtx_v,
    output wire [553-1:0]  dtx_d,
    input  wire [0:0]        drx_v,
    input  wire [553-1:0]  drx_d,
    input  wire [3:0]       dflt,
    input wire draft_slot_free, output wire draft_valid_o, output wire [552:0] draft_frame_o
);
    localparam integer FW = 553, NW = 21, UW = 10, SW = UW + 3 * NW + 4, DW = UW + 3 + NW;
    localparam integer NSL = 8192 + 7 * SK, NEND = 5 + NSL;   // stream length (bundle contract)
    localparam integer NB = 80;                                        // XB beats a message
    localparam [2:0] K_XB = 3'd2, K_TOK = 3'd5, K_HOST = 3'd6;
    localparam [3:0] T_BEST = 4'd1, T_SEED = 4'd2, T_DHS = 4'd3, T_DHR = 4'd4, T_ROWS = 4'd5, T_CSRW = 4'd6,
                     T_HFWD = 4'd7, T_STAT = 4'd8, T_RES = 4'd9;
    // ------------------------------------------------------------------ reset (2-stage landing + leaves)
    localparam integer NRL = 24;
    wire [NRL-1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(NRL)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    integer i;
    genvar g, k;
    // ------------------------------------------------------------------ CSRs (host lane 1 CSRW)
    reg [NW-1:0] c_plen, c_glen; reg [1:0] c_rank, c_grp, c_ngrp; reg [16:0] c_rbase; reg [15:0] c_hds;
    reg [15:0] c_cper, c_coff; reg c_run;
    // ------------------------------------------------------------------ fault vector
    reg [16:0] fv;
    reg [16:0] fset;                                   // per-cycle fault events (combinational OR below)
    function [552:0] frm(input [3:0] ty, input [1:0] rk, input [1:0] gp, input [535:0] pl);
        frm = {1'b1, pl, 8'd0, gp, rk, ty};
    endfunction
    function [1:0] mod3(input [20:0] x);
        reg [5:0] s; reg [3:0] s2; reg [2:0] s3; integer j;
        begin
            s = 6'd0;
            for (j = 0; j < 10; j = j + 1) s = s + {4'd0, x[2*j +: 2]};
            s = s + {5'd0, x[20]};
            s2 = {2'd0, s[5:4]} + {2'd0, s[3:2]} + {2'd0, s[1:0]};
            s3 = {1'b0, s2[3:2]} + {1'b0, s2[1:0]};
            mod3 = (s3 >= 3'd3) ? 2'(s3 - 3'd3) : s3[1:0];
        end
    endfunction
    function isnan(input [31:0] x);
        isnan = (x[30:23] == 8'hFF) && (x[22:0] != 23'd0);
    endfunction

    // ================================================================== INGEST (ri -> x store / forward)
    reg ri_v; reg [1103:1] ri_q; reg [31:0] rt_q;                      // P1 pin flops
    always @(posedge ck) begin ri_q <= ri[1103:1]; rt_q <= mu_rt; end
    wire [2:0] rtv_c;                                                  // kept pin-flop copies of the tag valid mu_rt[31]
    ot_s81hd_kf u_rtv0 (.ck(ck), .d(mu_rt[31]), .q(rtv_c[0]));
    ot_s81hd_kf u_rtv1 (.ck(ck), .d(mu_rt[31]), .q(rtv_c[1]));
    ot_s81hd_kf u_rtv2 (.ck(ck), .d(mu_rt[31]), .q(rtv_c[2]));
    reg [20:0] upos;                                                   // position counter of untagged messages
    // effective tag {v, user, pos}: an untagged beat (single-user mode) takes {user 0, pos upos}
    reg [31:0] p1_tag;
    always @(*) begin
        p1_tag[31] = rt_q[31];
        for (i = 0; i < 21; i = i + 1) p1_tag[i] = rtv_c[i / 11] ? rt_q[i] : upos[i];
        p1_tag[30:21] = rt_q[30:21] & {10{rtv_c[2]}};
    end
    always @(posedge ck or negedge rr[0]) if (!rr[0]) ri_v <= 1'b0; else ri_v <= ri[0];
    wire       p1_xb  = ri_v && ri_q[3:1] == K_XB;
    wire [7:0] p1_gx  = ri_q[20:13];
    wire       p1_tv  = rt_q[31];
    wire       p1_own = !p1_tv || c_ngrp <= 2'd1 || (c_ngrp == 2'd2 ? (rt_q[0] == c_grp[0]) : (mod3(rt_q[20:0]) == c_grp));
    reg [6:0]  fcnt;                                                   // forwarded XB beats of the open message
    wire       p1_xw  = p1_xb && p1_own;                               // x store write
    wire p1_dft=ri_v && ri_q[3:1]==3'd7 && (ri_q[16:13]==4'd4 || ri_q[16:13]==4'd5);
    wire       p1_fw  = ri_v && !p1_xw && !p1_dft;                                // forward
    wire       p1_op  = p1_xb && !p1_own && p1_tv && fcnt == 7'd0;     // first forwarded beat of a tagged message
    // P2..P5 forward pipeline (unconditional data), P2 write port
    reg wv2, f2v, f3v, f4v, f5v, x2, x3, x4, x5, o2, o3;
    reg [6:0] wa2; reg [1023:0] wd2; reg [31:0] t2;
    reg [1103:0] f2d, f3d, f4d, f5d;
    reg [33:1] muc_d; reg muc_v;
    always @(posedge ck) begin
        wa2 <= p1_gx[6:0]; wd2 <= ri_q[1044:21]; t2 <= p1_tag;
        f2d <= {ri_q, ri_v}; f3d <= f2d; f4d <= f3d; f5d <= f4d;
    end
    always @(posedge ck or negedge rr[0])
        if (!rr[0]) begin wv2 <= 1'b0; f2v <= 1'b0; f3v <= 1'b0; f4v <= 1'b0; f5v <= 1'b0;
                          x2 <= 1'b0; x3 <= 1'b0; x4 <= 1'b0; x5 <= 1'b0; o2 <= 1'b0; o3 <= 1'b0; end
        else begin
            wv2 <= p1_xw && p1_gx < 8'd80; f2v <= p1_fw; f3v <= f2v; f4v <= f3v; f5v <= f4v;
            x2 <= p1_xb && !p1_own; x3 <= x2; x4 <= x3; x5 <= x4; o2 <= p1_op; o3 <= o2;
        end
    // tag of the window: {pos, user, land 0, ab 0} of the opening beat, issued as mu_c when it enters P4
    reg [30:0] t3o;
    always @(posedge ck) begin t3o <= {t2[20:0], t2[30:21]}; muc_d <= {t3o, 2'b00}; end
    // window / message counters
    reg [6:0] wcnt, nbeat;
    wire sel_fx;                                                       // a forwarded XB beat leaves on ro (decision stage)
    always @(posedge ck or negedge rr[1])
        if (!rr[1]) begin fcnt <= 7'd0; wcnt <= 7'd0; muc_v <= 1'b0; end
        else begin
            if (p1_xb && !p1_own) fcnt <= (fcnt == 7'(NB - 1)) ? 7'd0 : fcnt + 7'd1;
            muc_v <= o3;
            if (o3) wcnt <= 7'(NB);
            else if (sel_fx && wcnt != 7'd0) wcnt <= wcnt - 7'd1;
        end
    assign mu_c = {muc_d, muc_v};
    // x store write port (P2) and message fill
    reg busy;
    reg mt_v; reg [30:0] mt_tag;                                       // message tag {user, pos}, tag valid
    wire wa_xa = wa2 < 7'd64;
    wire [1:0] mf_c;                                                   // first beat of a message (kept copies, P2)
    wire p1_first = p1_xw && p1_gx < 8'd80 && nbeat == 7'd0 && !wv2;
    ot_s81hd_kf u_mf0 (.ck(ck), .d(p1_first), .q(mf_c[0]));
    ot_s81hd_kf u_mf1 (.ck(ck), .d(p1_first), .q(mf_c[1]));
    always @(posedge ck) begin
        if (mf_c[0]) mt_tag[15:0] <= t2[15:0];
        if (mf_c[1]) begin mt_tag[30:16] <= t2[30:16]; mt_v <= t2[31]; end
    end
    wire xrdy = nbeat == 7'(NB);
    wire start;
    wire due, deadline_miss;
    wire token_retire; reg[30:0]job_identity;
    always@(posedge ck)if(start)job_identity<=mt_tag;
    reg [15:0] c_iss_off,c_iss_per,c_merge_dl;
    wire schedule_fault;
    ot_s81hd_static_issue #(.MUT_MODE(MUT_STATIC)) u_issue(
      .ck(ck),.rn(rr[1]),.start_i(start_i),.run_i(c_run),
      .issue_offset(c_iss_off),.issue_period(c_iss_per),.merge_deadline(c_merge_dl),
      .loaded_ready(xrdy),.replay_busy(busy),.token_retire(token_retire),.merged_valid(mg4),
      .issue_o(start),.job_active_o(job_active_o),.due_o(due),.fault_o(schedule_fault));
    always @(posedge ck or negedge rr[1])
        if (!rr[1]) nbeat <= 7'd0;
        else if (start) nbeat <= 7'd0;
        else if (wv2) nbeat <= nbeat + 7'd1;
    // ================================================================== X STORE (4 x 64x512 macros)
    reg [13:0] n;
    wire go0 = busy && n == 14'd0;
    wire xv0 = busy && n >= 14'd5;
    wire [13:0] m0 = n - 14'd5;
    wire [511:0] ra0, ra1, rb0, rb1;
    ot_sram_1r1w_64x512_m1_r2c2 u_xa0 (.clk(ck), .r_ce_in(xv0), .r_addr_in(m0[7:2]), .rd_out(ra0),
        .w_ce_in(wv2 && wa_xa), .w_addr_in(wa2[5:0]), .wd_in(wd2[511:0]), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    ot_sram_1r1w_64x512_m1_r2c2 u_xa1 (.clk(ck), .r_ce_in(xv0), .r_addr_in(m0[7:2]), .rd_out(ra1),
        .w_ce_in(wv2 && wa_xa), .w_addr_in(wa2[5:0]), .wd_in(wd2[1023:512]), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    ot_sram_1r1w_64x512_m1_r2c2 u_xb0 (.clk(ck), .r_ce_in(xv0), .r_addr_in({2'b00, m0[5:2]}), .rd_out(rb0),
        .w_ce_in(wv2 && !wa_xa), .w_addr_in({2'b00, wa2[3:0]}), .wd_in(wd2[511:0]), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    ot_sram_1r1w_64x512_m1_r2c2 u_xb1 (.clk(ck), .r_ce_in(xv0), .r_addr_in({2'b00, m0[5:2]}), .rd_out(rb1),
        .w_ce_in(wv2 && !wa_xa), .w_addr_in({2'b00, wa2[3:0]}), .wd_in(wd2[1023:512]), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // ================================================================== STREAM (P0 ctl -> P1 macro -> P2 mux -> P3 pins)
    reg [30:0] tf0, tf1; reg [1:0] tfn; reg tfw, tfr;                 // tag FIFO of issued streams {user, pos}
    (* keep = "true" *) reg tfr_a, tfr_b, tfr_c;                       // read-select copies (11 / 10 / 10 bits)
    reg st1;
    always @(posedge ck or negedge rr[2])
        if (!rr[2]) begin busy <= 1'b0; n <= 14'd0; end
        else if (start) begin busy <= 1'b1; n <= 14'd0; end
        else if (busy) begin n <= n + 14'd1; if (n == 14'(NEND - 1)) busy <= 1'b0; end
    // one-hot slice selects, 8 kept copies each (one per 32 output bits)
`ifdef OT_S81HD_CTL_MUT_SLICE
    wire [3:0] sa0 = 4'b0001 << m0[1:0];                               // mutant: xa word select ignores the macro half
    wire [3:0] sa_n = {2'b00, sa0[1:0]};
`else
    wire [3:0] sa_n = 4'b0001 << m0[1:0];
`endif
    wire [3:0] sb_n = 4'b0001 << m0[1:0];
    wire [31:0] sa_c, sb_c;                                            // [4c +: 4] = copy c
    generate for (k = 0; k < 8; k = k + 1) begin : g_sc
        for (g = 0; g < 4; g = g + 1) begin : g_b
            ot_s81hd_kf u_a (.ck(ck), .d(sa_n[g]), .q(sa_c[4*k + g]));
            ot_s81hd_kf u_b (.ck(ck), .d(sb_n[g]), .q(sb_c[4*k + g]));
        end
    end endgenerate
    reg go1, xv1, go2, xv2;
    always @(posedge ck or negedge rr[2])
        if (!rr[2]) begin go1 <= 1'b0; xv1 <= 1'b0; go2 <= 1'b0; xv2 <= 1'b0; end
        else begin go1 <= go0; xv1 <= xv0; go2 <= go1; xv2 <= xv1; end
    reg [255:0] xa2, xb2;
    always @(posedge ck)
        for (i = 0; i < 256; i = i + 1) begin
            xa2[i] <= (sa_c[4*(i/32)+0] & ra0[i]) | (sa_c[4*(i/32)+1] & ra0[256+i]) |
                      (sa_c[4*(i/32)+2] & ra1[i]) | (sa_c[4*(i/32)+3] & ra1[256+i]);
            xb2[i] <= (sb_c[4*(i/32)+0] & rb0[i]) | (sb_c[4*(i/32)+1] & rb0[256+i]) |
                      (sb_c[4*(i/32)+2] & rb1[i]) | (sb_c[4*(i/32)+3] & rb1[256+i]);
        end
    // go copies (one per spine output) for the null-best fields
    wire gon, gos;
    ot_s81hd_kf u_gon (.ck(ck), .d(go1), .q(gon));
    ot_s81hd_kf u_gos (.ck(ck), .d(go1), .q(gos));
    reg ctlf_q;
    reg [564:0] sno_q, sso_q;
    always @(posedge ck) begin
        sno_q <= {ctlf_q, gon, {8{gon}}, 23'd0, {17{gon}}, go2, xv2, go2, xb2, xa2};
        sso_q <= {ctlf_q, gos, {8{gos}}, 23'd0, {17{gos}}, go2, xv2, go2, xb2, xa2};
    end
    assign sn_o = sno_q;
    assign ss_o = sso_q;
    // tag FIFO: push at start, pop at the N/S final
    wire nsf_fire;
    // the entry is written one edge after start (kept write-enable copies); mt_tag is stable until the next message
    wire [3:0] tfe;
    ot_s81hd_kf u_tfe0 (.ck(ck), .d(start && !tfw), .q(tfe[0])); ot_s81hd_kf u_tfe1 (.ck(ck), .d(start && !tfw), .q(tfe[1]));
    ot_s81hd_kf u_tfe2 (.ck(ck), .d(start && tfw), .q(tfe[2]));  ot_s81hd_kf u_tfe3 (.ck(ck), .d(start && tfw), .q(tfe[3]));
    always @(posedge ck) begin
        if (tfe[0]) tf0[15:0] <= mt_tag[15:0]; if (tfe[1]) tf0[30:16] <= mt_tag[30:16];
        if (tfe[2]) tf1[15:0] <= mt_tag[15:0]; if (tfe[3]) tf1[30:16] <= mt_tag[30:16];
    end
    always @(posedge ck or negedge rr[3])
        if (!rr[3]) begin tfn <= 2'd0; tfw <= 1'b0; tfr <= 1'b0; tfr_a <= 1'b0; tfr_b <= 1'b0; tfr_c <= 1'b0; upos <= 21'd0; st1 <= 1'b0; end
        else begin
            st1 <= start;
            if (start) tfw <= ~tfw;
            if (st1 && !mt_v) upos <= upos + 21'd1;
            if (nsf_fire && tfn != 2'd0) begin tfr <= ~tfr; tfr_a <= ~tfr_a; tfr_b <= ~tfr_b; tfr_c <= ~tfr_c; end
            tfn <= tfn + {1'b0, start && tfn != 2'd2} - {1'b0, nsf_fire && tfn != 2'd0};
        end
    wire [30:0] tf_head = {tfr_c ? tf1[30:21] : tf0[30:21], tfr_b ? tf1[20:11] : tf0[20:11], tfr_a ? tf1[10:0] : tf0[10:0]};
    // ================================================================== N/S FINAL
    reg [564:514] sni_q, ssi_q; reg nrv, srv;
    always @(posedge ck) begin sni_q <= sn_i[564:514]; ssi_q <= ss_i[564:514]; end
    always @(posedge ck or negedge rr[4]) if (!rr[4]) begin nrv <= 1'b0; srv <= 1'b0; end
                                           else begin nrv <= sn_i[514]; srv <= ss_i[514]; end
    wire [3:0] nen, sen;                                               // kept enable copies (13 / 12 / 12 / 12 bits)
    generate for (k = 0; k < 4; k = k + 1) begin : g_nse
        ot_s81hd_kf u_n (.ck(ck), .d(sn_i[514]), .q(nen[k]));
        ot_s81hd_kf u_s (.ck(ck), .d(ss_i[514]), .q(sen[k]));
    end endgenerate
    reg [48:0] nb, sb;                                                 // {bits [48:17], row [16:0]} = sni_q[563:515]
    always @(posedge ck) begin
        if (nen[0]) nb[12:0] <= sni_q[527:515];  if (nen[1]) nb[24:13] <= sni_q[539:528];
        if (nen[2]) nb[36:25] <= sni_q[551:540]; if (nen[3]) nb[48:37] <= sni_q[563:552];
        if (sen[0]) sb[12:0] <= ssi_q[527:515];  if (sen[1]) sb[24:13] <= ssi_q[539:528];
        if (sen[2]) sb[36:25] <= ssi_q[551:540]; if (sen[3]) sb[48:37] <= ssi_q[563:552];
    end
    reg nh, sh, bv1, bv;
    assign nsf_fire = nh && sh;
    always @(posedge ck or negedge rr[4])
        if (!rr[4]) begin nh <= 1'b0; sh <= 1'b0; bv1 <= 1'b0; bv <= 1'b0; end
        else begin
            nh <= (nh && !nsf_fire) || nrv; sh <= (sh && !nsf_fire) || srv; bv1 <= nsf_fire; bv <= bv1;
        end
    wire [31:0] n_bits = nb[48:17], s_bits = sb[48:17];
    // N/S pick (2 edges: one compare, kept decision copies, select); the popped tag rides a 2-stage pipeline
    wire [48:0] b_rb;
    ot_s81hd_pick u_pns (.ck(ck), .u(nb), .v(sb), .y(b_rb));
    reg [30:0] bt1, b_tag;
    always @(posedge ck) begin bt1 <= tf_head; b_tag <= bt1; end
    // own record = best + rank row base
    reg ov_p; reg [80:0] orec_d;                                       // {pos, user, bits, row, v}
    always @(posedge ck) orec_d <= {b_tag[20:0], b_tag[30:21], b_rb[48:17], b_rb[16:0] + c_rbase, 1'b1};
    always @(posedge ck or negedge rr[4]) if (!rr[4]) ov_p <= 1'b0; else ov_p <= bv;
    // ================================================================== RANK MERGE (6 mesh lanes)
    reg [5:0] mtv_q; reg [FW-1:0] mtd_q [0:5];
    wire [6*FW-1:0] mtd_q_flat;
    always @(posedge ck) for (i = 0; i < 6; i = i + 1) mtd_q[i] <= frm(T_BEST, c_rank, c_grp, {455'd0, orec_d});
    always @(posedge ck or negedge rr[5]) if (!rr[5]) mtv_q <= 6'd0; else mtv_q <= {6{ov_p}};
    generate for (k = 0; k < 6; k = k + 1) begin : g_mtx
        assign mtd_q_flat[k*FW +: FW] = mtd_q[k];
    end endgenerate
    assign mtx_v = mtv_q; assign mtx_d = mtd_q_flat;
    reg [5:0] mrv_q; reg [96:0] mrd_q [0:5];                           // only the HSF0 header + BEST payload is read
    always @(posedge ck) for (i = 0; i < 6; i = i + 1) mrd_q[i] <= mrx_d[i*FW +: 97];
    always @(posedge ck or negedge rr[5]) if (!rr[5]) mrv_q <= 6'd0; else mrv_q <= mrx_v;
    // 7 record slots: 0..5 = mesh lanes, 6 = own; 81 b each in 3 hold registers
    wire [6:0] sl_en;
    wire [7*96-1:0] sl_q;
    generate for (k = 0; k < 6; k = k + 1) begin : g_ms
        assign sl_en[k] = mrv_q[k] && mrd_q[k][3:0] == T_BEST;
        wire [95:0] dk = {15'd0, mrd_q[k][96:16]};
        for (g = 0; g < 3; g = g + 1) begin : g_h
            ot_s81hd_hreg32 u_h (.ck(ck), .en(sl_en[k]), .d(dk[32*g +: 32]), .q(sl_q[96*k + 32*g +: 32]));
        end
    end endgenerate
    assign sl_en[6] = ov_p;
    generate for (g = 0; g < 3; g = g + 1) begin : g_os
        wire [95:0] dk = {15'd0, orec_d};
        ot_s81hd_hreg32 u_h (.ck(ck), .en(ov_p), .d(dk[32*g +: 32]), .q(sl_q[96*6 + 32*g +: 32]));
    end endgenerate
    reg [6:0] sl_l, sl_v;                                              // landed enable (aligned to the hold), slot full
    wire mg_fire = &sl_v;
    reg [6:0] sl_ovw;
    always @(posedge ck or negedge rr[6])
        if (!rr[6]) begin sl_l <= 7'd0; sl_v <= 7'd0; end
        else begin sl_l <= sl_en; sl_v <= (sl_v & {7{!mg_fire}}) | sl_l; end
    always @(*) sl_ovw = sl_l & sl_v & {7{!mg_fire}};
    // record fields: slot s -> {pos [80:60], user [59:50], bits [49:18], row [17:1], v [0]}
    // merge stage 1: checks + level-1 compares (own vs pair-0 copy 0, pair-1 copy 0 vs pair-2 copy 0)
    wire [80:0] r_own = sl_q[96*6 +: 81], r_p0 = sl_q[0 +: 81], r_p0b = sl_q[96 +: 81],
                r_p1 = sl_q[192 +: 81], r_p1b = sl_q[288 +: 81], r_p2 = sl_q[384 +: 81], r_p2b = sl_q[480 +: 81];
    // 2-level registered tree (2 edges a level): (own, pair-0) and (pair-1, pair-2), then the final pick
    wire [48:0] c1a, c1b, mg_rb;
    ot_s81hd_pick u_p1a (.ck(ck), .u(r_own[49:1]), .v(r_p0[49:1]), .y(c1a));
    ot_s81hd_pick u_p1b (.ck(ck), .u(r_p1[49:1]), .v(r_p2[49:1]), .y(c1b));
    ot_s81hd_pick u_p2  (.ck(ck), .u(c1a), .v(c1b), .y(mg_rb));
    reg mg1, mg2, mg3, mg4, mchk_tag, mchk_cpy, mchk_nan; reg [30:0] mg_t;   // tag {pos, user} (slots hold until the next record)
    always @(posedge ck) begin
        mg_t <= r_own[80:50];
        mchk_tag <= (r_p0[80:50] != r_own[80:50]) || (r_p1[80:50] != r_own[80:50]) || (r_p2[80:50] != r_own[80:50]);
        mchk_cpy <= (r_p0 != r_p0b) || (r_p1 != r_p1b) || (r_p2 != r_p2b);
        mchk_nan <= isnan(r_own[49:18]) || isnan(r_p0[49:18]) || isnan(r_p1[49:18]) || isnan(r_p2[49:18]);
    end
    always @(posedge ck or negedge rr[6]) if (!rr[6]) begin mg1 <= 1'b0; mg2 <= 1'b0; mg3 <= 1'b0; mg4 <= 1'b0; end
                                           else begin mg1 <= mg_fire; mg2 <= mg1; mg3 <= mg2; mg4 <= mg3; end
    // ================================================================== RESULT -> dsfd_mtp_seq
    wire [95:0] res_h;                                                 // {pos 21, user 10, bits 32, row 17} held
    generate for (g = 0; g < 3; g = g + 1) begin : g_rh
        wire [95:0] dk = {16'd0, mg_t[30:0], mg_rb[48:0]};
        ot_s81hd_hreg32 u_h (.ck(ck), .en(mg4), .d(dk[32*g +: 32]), .q(res_h[32*g +: 32]));
    end endgenerate
    reg res_l, rpend; wire r_cr;
    always @(posedge ck or negedge rr[7])
        if (!rr[7]) begin res_l <= 1'b0; rpend <= 1'b0; end
        else begin res_l <= mg4; rpend <= (rpend && !r_cr) || res_l; end
    wire [16:0] rs_row = res_h[16:0]; wire [31:0] rs_bits = res_h[48:17];
    wire [9:0] rs_user = res_h[58:49]; wire [20:0] rs_pos = res_h[79:59];
    // c_hds is mtag {DEST, SRC}; layout of ot_dsrom_mtp_seq RESULT: TYPE [19:16] = 2, USER [39:32], POS [60:40],
    // IDX [81:61] = token, VAL [113:82] = logit, USER_HI [152:151]
    wire [511:0] rflit = {359'd0, rs_user[9:8], 37'd0, rs_bits, 4'd0, rs_row, rs_pos, rs_user[7:0], 8'd0, 4'd0, 4'd2, c_hds};
    wire f_rv, t_rg; wire [511:0] f_rd;
    ot_dsrom_mtp_ltx #(.W(512)) u_ltr (.clk(ck), .rst_n(rr[7]), .c_valid(rpend), .c_ready(r_cr), .c_data(rflit),
        .l_valid(f_rv), .l_ready(t_rg), .l_data(f_rd));
    // ================================================================== draft-lane RX (DHRES -> q, ROWS -> w)
    reg [0:0] drv_q; reg [49:0] drd_q [0:0];
    always @(posedge ck) for (i = 0; i < 1; i = i + 1) drd_q[i] <= drx_d[i*FW +: 50];
    always @(posedge ck or negedge rr[8]) if (!rr[8]) drv_q <= 1'd0; else drv_q <= drx_v;
    wire [0:0] dq_n, dw_n, dx_n;
    wire [1:0] dqc;                                                    // 2 kept copies per lane
    wire [0:0] dwc;
    reg [33:0] pq2 [0:0]; reg [9:0] pw2 [0:0];
    generate for (k = 0; k < 1; k = k + 1) begin : g_drx
        assign dq_n[k] = drv_q[k] && drd_q[k][3:0] == T_DHR;
        assign dw_n[k] = drv_q[k] && drd_q[k][3:0] == T_ROWS;
        assign dx_n[k] = drv_q[k] && !dq_n[k] && !dw_n[k];
        ot_s81hd_kf u_q0 (.ck(ck), .d(dq_n[k]), .q(dqc[2*k])); ot_s81hd_kf u_q1 (.ck(ck), .d(dq_n[k]), .q(dqc[2*k+1]));
        ot_s81hd_kf u_w0 (.ck(ck), .d(dw_n[k]), .q(dwc[k]));
    end endgenerate
    always @(posedge ck) for (i = 0; i < 1; i = i + 1) begin pq2[i] <= drd_q[i][49:16]; pw2[i] <= drd_q[i][25:16]; end
    reg [33:0] qsel; reg [9:0] wsel;
    always @(*) begin
        qsel = 34'd0; wsel = 10'd0;
        for (i = 0; i < 1; i = i + 1) begin
            qsel[16:0]  = qsel[16:0]  | ({17{dqc[2*i]}} & pq2[i][16:0]);
            qsel[33:17] = qsel[33:17] | ({17{dqc[2*i+1]}} & pq2[i][33:17]);
            wsel = wsel | ({10{dwc[i]}} & pw2[i]);
        end
    end
    wire [63:0] qw_h; wire[31:0] rows_h;
    ot_s81hd_hreg32 u_qh0 (.ck(ck), .en(|dqc), .d(qsel[31:0]), .q(qw_h[31:0]));
    ot_s81hd_hreg32 u_qh1 (.ck(ck), .en(|dqc), .d({30'd0,qsel[33:32]}), .q(qw_h[63:32]));
    ot_s81hd_hreg32 u_wh(.ck(ck),.en(|dwc),.d({22'd0,wsel}),.q(rows_h));
    wire [33:0] q_hold = qw_h[33:0]; wire [9:0] w_hold = rows_h[9:0];
    // Independent DHRES and ROWS landing holds preserve each user identity. Coincident arrivals are a schedule fault.
    reg dq_l, dw_l, dq_ready, dw_ready, qpend, wpend; wire q_cr, w_cr;
    always @(posedge ck or negedge rr[8])
        if (!rr[8]) begin dq_l <= 1'b0; dw_l <= 1'b0; dq_ready<=0;dw_ready<=0;qpend <= 1'b0; wpend <= 1'b0; end
        else begin
            dq_l <= |dq_n; dw_l <= |dw_n;
            // hreg32 has a capture+enable stage before Q. Advertise only once
            // that Q is stable; early qpend launched the previous DHRES (j0).
            dq_ready<=dq_l;dw_ready<=dw_l;
            qpend <= (qpend && !q_cr) || (MUT_DRAFT_EARLY?dq_l:dq_ready); wpend <= (wpend && !w_cr) || (MUT_DRAFT_EARLY?dw_l:dw_ready);
        end
    wire f_qv, t_qg, f_wv, t_wg; wire [DW-1:0] f_qd; wire [UW-1:0] f_wd;
    ot_dsrom_mtp_ltx #(.W(DW)) u_ltq (.clk(ck), .rst_n(rr[8]), .c_valid(qpend), .c_ready(q_cr), .c_data(q_hold),
        .l_valid(f_qv), .l_ready(t_qg), .l_data(f_qd));
    ot_dsrom_mtp_ltx #(.W(UW)) u_ltw (.clk(ck), .rst_n(rr[8]), .c_valid(wpend), .c_ready(w_cr), .c_data(w_hold),
        .l_valid(f_wv), .l_ready(t_wg), .l_data(f_wd));
    // ================================================================== dsfd_mtp_seq (closed hard child)
    wire t_tv, f_tg, t_sv, f_sg, t_hv, f_hg; wire [511:0] t_td; wire [SW-1:0] t_sd; wire [DW-1:0] t_hd;
    wire [2*NW+UW+4:0] t_acc;
    // dsfd_mtp_seq samples {glen, plen} while in reset (static configuration): it is held in reset until the host sets
    // CSR 8 run = 1 after writing plen / glen (run = 0 resets it again for the next request)
    reg seq_rn;
    always @(posedge ck or negedge rr[9]) if (!rr[9]) seq_rn <= 1'b0; else seq_rn <= c_run;
    dsfd_mtp_seq u_seq (.ck(ck), .rst(seq_rn), .f_cfg({c_glen, c_plen}),
        .f_rv(f_rv), .f_rd(f_rd), .t_rg(t_rg), .t_tv(t_tv), .t_td(t_td), .f_tg(f_tg),
        .t_sv(t_sv), .t_sd(t_sd), .f_sg(f_sg), .f_wv(f_wv), .f_wd(f_wd), .t_wg(t_wg),
        .t_hv(t_hv), .t_hd(t_hd), .f_hg(f_hg), .f_qv(f_qv), .f_qd(f_qd), .t_qg(t_qg), .t_acc(t_acc));
    // grant receivers (one grant in flight, one holding register; grant only while the holding register is empty)
    wire tk_hv, sd_hv, hs_hv; wire tk_pop, sd_pop, hs_pop;
    wire [511:0] tk_q; wire [SW-1:0] sd_q; wire [DW-1:0] hs_q;
    ot_s81hd_ctl_grx #(.W(512)) u_gt (.ck(ck), .rn(rr[10]), .l_v(t_tv), .l_d(t_td), .l_g(f_tg), .hv(tk_hv), .q(tk_q), .pop(tk_pop));
    ot_s81hd_ctl_grx #(.W(SW))  u_gs (.ck(ck), .rn(rr[10]), .l_v(t_sv), .l_d(t_sd), .l_g(f_sg), .hv(sd_hv), .q(sd_q), .pop(sd_pop));
    ot_s81hd_ctl_grx #(.W(DW))  u_gh (.ck(ck), .rn(rr[10]), .l_v(t_hv), .l_d(t_hd), .l_g(f_hg), .hv(hs_hv), .q(hs_q), .pop(hs_pop));
    // ================================================================== draft-lane TX (SEED / DHSTEP)
    reg [0:0] dtv_q; reg [FW-1:0] dtd_q [0:0];
    assign sd_pop = sd_hv && !dtv_q[0] && draft_slot_free && !f5v && !blk && !tk_pop;
    assign hs_pop = hs_hv && !sd_hv && !dtv_q[0] && draft_slot_free && !f5v && !blk && !tk_pop && !f5v && !blk && !tk_pop;
    always @(posedge ck) begin
        for (i = 0; i < 1; i = i + 1)
            dtd_q[i] <= {1'b1, 422'd0, hs_q, 3'd0, sd_q, 8'd0, c_grp, c_rank, 4'd0};
    end
    always @(posedge ck or negedge rr[11]) if (!rr[11]) dtv_q <= 1'd0; else dtv_q <= sd_pop || hs_pop;
    // the type nibble has its own flops (no select after the pin flop)
    reg [3:0] dty_q [0:0];
    always @(posedge ck) for (i = 0; i < 1; i = i + 1) dty_q[i] <= sd_pop ? T_SEED : T_DHS;
    generate for (k = 0; k < 1; k = k + 1) begin : g_dtx2
        assign dtx_d[k*FW +: FW] = {dtd_q[k][552:4], dty_q[k]};
    end endgenerate
    assign dtx_v = dtv_q;
    assign draft_valid_o=dtv_q[0]; assign draft_frame_o=dtx_d;
    // ================================================================== HOST lanes
    reg [1:0] hrv_q; reg [527:0] hrd0_q; reg [87:0] hrd1_q;
    always @(posedge ck) begin hrd0_q <= hrx_d[527:0]; hrd1_q <= hrx_d[FW +: 88]; end
    always @(posedge ck or negedge rr[12]) if (!rr[12]) hrv_q <= 2'd0; else hrv_q <= hrx_v;
    // CSR writes (host lane 1)
    wire csr_input = hrv_q[1] && hrd1_q[3:0] == T_CSRW;
    wire csr_w=csr_input&&(!start_i||hrd1_q[23:16]==7||hrd1_q[23:16]==8);
    wire [7:0] csr_a = hrd1_q[23:16];
    // decoded write enables land in kept copies (<= 16 bits each) one edge later, with the data
    reg [63:0] csr_d;
    (* keep = "true" *) reg [1:0] ce_pl, ce_gl, ce_rb, ce_hd, ce_cp, ce_co; (* keep = "true" *) reg ce_rk, ce_gp, ce_run;
    always @(posedge ck) begin
        csr_d <= hrd1_q[87:24];
        ce_pl <= {2{csr_w && csr_a == 8'd0}}; ce_gl <= {2{csr_w && csr_a == 8'd1}}; ce_rk <= csr_w && csr_a == 8'd2;
        ce_gp <= csr_w && csr_a == 8'd3; ce_rb <= {2{csr_w && csr_a == 8'd4}}; ce_hd <= {2{csr_w && csr_a == 8'd5}};
        ce_cp <= {2{csr_w && csr_a == 8'd6}}; ce_co <= {2{csr_w && csr_a == 8'd6}}; ce_run <= csr_w && csr_a == 8'd8;
    end
    always @(posedge ck or negedge rr[13])
        if (!rr[13]) c_plen <= 21'd0;
        else begin if (ce_pl[0]) c_plen[10:0] <= csr_d[10:0]; if (ce_pl[1]) c_plen[20:11] <= csr_d[20:11]; end
    always @(posedge ck or negedge rr[14])
        if (!rr[14]) c_glen <= 21'd0;
        else begin if (ce_gl[0]) c_glen[10:0] <= csr_d[10:0]; if (ce_gl[1]) c_glen[20:11] <= csr_d[20:11]; end
    always @(posedge ck or negedge rr[15])
        if (!rr[15]) begin c_rank <= 2'd0; c_grp <= 2'd0; c_ngrp <= 2'd0; c_rbase <= 17'd0; c_run <= 1'b0; end
        else begin
            if (ce_run) c_run <= csr_d[0];
            if (ce_rk) c_rank <= csr_d[1:0];
            if (ce_gp) begin c_grp <= csr_d[1:0]; c_ngrp <= csr_d[3:2]; end
            if (ce_rb[0]) c_rbase[8:0] <= csr_d[8:0]; if (ce_rb[1]) c_rbase[16:9] <= csr_d[16:9];
        end
    always @(posedge ck or negedge rr[16])
        if (!rr[16]) c_hds <= 16'd0;
        else begin if (ce_hd[0]) c_hds[7:0] <= csr_d[7:0]; if (ce_hd[1]) c_hds[15:8] <= csr_d[15:8]; end
    always @(posedge ck or negedge rr[17])
        if (!rr[17]) begin c_cper <= 16'd0; c_coff <= 16'd0; end
        else begin
            if (ce_cp[0]) c_cper[7:0] <= csr_d[7:0];   if (ce_cp[1]) c_cper[15:8] <= csr_d[15:8];
            if (ce_co[0]) c_coff[7:0] <= csr_d[23:16]; if (ce_co[1]) c_coff[15:8] <= csr_d[31:24];
        end
    always @(posedge ck or negedge rr[17])
      if(!rr[17]) begin c_iss_off<=0;c_iss_per<=0;c_merge_dl<=0;end
      else if(csr_w && !start_i) begin
        if(csr_a==9)begin c_iss_off<=hrd1_q[55:40];c_iss_per<=hrd1_q[39:24];end
        if(csr_a==10)c_merge_dl<=hrd1_q[39:24];
      end
    wire stat_req = csr_w && csr_a == 8'd7;
    // HFWD (host lane 0): one holding register (16 x hreg32); a second frame before its slot is a fault
    wire hf_en = hrv_q[0] && hrd0_q[3:0] == T_HFWD;
    wire [511:0] hf_q;
    reg [511:0] hf_p;                                                  // payload stage aligned with the enable copies
    always @(posedge ck) hf_p <= hrd0_q[527:16];
    wire [1:0] hfe;
    ot_s81hd_kf u_hfe0 (.ck(ck), .d(hf_en), .q(hfe[0])); ot_s81hd_kf u_hfe1 (.ck(ck), .d(hf_en), .q(hfe[1]));
    generate for (g = 0; g < 16; g = g + 1) begin : g_hf
        ot_s81hd_hreg32 u_h (.ck(ck), .en(hfe[g / 8]), .d(hf_p[32*g +: 32]), .q(hf_q[32*g +: 32]));
    end endgenerate
    reg hf_l0, hf_l, hf_hv; wire hf_pop;
    reg [15:0] cal;
    wire cslot = cal == c_coff;
    always @(posedge ck or negedge rr[12])
        if (!rr[12]) begin hf_l0 <= 1'b0; hf_l <= 1'b0; hf_hv <= 1'b0; cal <= 16'd0; end
        else begin
            hf_l0 <= hf_en; hf_l <= hf_l0; hf_hv <= (hf_hv && !hf_pop) || hf_l;
            cal <= (cal >= c_cper) ? 16'd0 : cal + 16'd1;
        end
    // ================================================================== RO stage (forward > token > host)
    wire blk = (wcnt != 7'd0) || o2 || o3 || p1_op;                    // window open or about to open
    reg htv0_q;
    assign tk_pop = tk_hv && !f5v && !blk && !htv0_q;
    assign token_retire=tk_pop && tk_q[60:40]==job_identity[20:0] && {tk_q[152:151],tk_q[39:32]}==job_identity[30:21];
    assign hf_pop = hf_hv && !f5v && !blk && !tk_pop && !sd_pop && !hs_pop && cslot;
    assign sel_fx = f5v && x5;
    wire [16:0] sf_c, st_c, sh_c, sd_c;
    generate for (k = 0; k < 17; k = k + 1) begin : g_rsel
        ot_s81hd_kf u_f (.ck(ck), .d(f5v), .q(sf_c[k]));
        ot_s81hd_kf u_t (.ck(ck), .d(tk_pop), .q(st_c[k]));
        ot_s81hd_kf u_h (.ck(ck), .d(hf_pop), .q(sh_c[k]));
        ot_s81hd_kf u_d (.ck(ck),.d(sd_pop||hs_pop),.q(sd_c[k]));
    end endgenerate
    reg [1103:0] f6d; reg [531:0] t6d, h6d, d6d; reg ro_v6;
    always @(posedge ck) begin
        f6d <= f5d;
        t6d <= {tk_q, 8'd0, 4'd0, 5'd1, K_TOK};
        h6d <= {hf_q, 8'd0, 4'd0, 5'd1, K_HOST};
        d6d <= {sd_pop ? {{(512-SW){1'b0}},sd_q} : ({{(512-DW){1'b0}},hs_q}<<80),4'd0,(sd_pop?T_SEED:T_DHS),4'd0,5'd1,3'd7};
    end
    always @(posedge ck or negedge rr[18]) if (!rr[18]) ro_v6 <= 1'b0; else ro_v6 <= f5v || tk_pop || hf_pop || sd_pop || hs_pop;
    reg [1103:0] ro_q;
    always @(posedge ck) begin
        ro_q[1103:533] <= f6d[1103:533];
        for (i = 1; i < 533; i = i + 1)
            ro_q[i] <= (sf_c[(i-1)/32] & f6d[i]) | (st_c[(i-1)/32] & t6d[i-1]) | (sh_c[(i-1)/32] & h6d[i-1]) | (sd_c[(i-1)/32] & d6d[i-1]);
    end
    reg ro_v;
    always @(posedge ck or negedge rr[18]) if (!rr[18]) ro_v <= 1'b0; else ro_v <= ro_v6;
    assign ro = {ro_q[1103:1], ro_v};
    // host lane 0 TX: RESULT copy of every token sent; host lane 1 TX: STATUS
    reg [FW-1:0] htd0_q, htd1_q; reg htv1_q, spend;
    wire [63:0] acc_h;
    ot_s81hd_hreg32 u_ah0 (.ck(ck), .en(t_acc[55]), .d(t_acc[31:0]), .q(acc_h[31:0]));
    ot_s81hd_hreg32 u_ah1 (.ck(ck), .en(t_acc[55]), .d({7'd0, t_acc[56:32]}), .q(acc_h[63:32]));
    reg [3:0] mfl_q [0:8];
    always @(posedge ck) begin
        for (i = 0; i < 6; i = i + 1) mfl_q[i] <= mflt[4*i +: 4];
        for (i = 0; i < 2; i = i + 1) mfl_q[6+i] <= hflt[4*i +: 4];
        for (i = 0; i < 1; i = i + 1) mfl_q[8+i] <= dflt[4*i +: 4];
    end
    reg [51:0] lflt;
    always @(*) begin lflt=0; for (i = 0; i < 9; i = i + 1) lflt[4*i +: 4] = mfl_q[i]; end
    always @(posedge ck) begin
        htd0_q <= frm(T_RES, c_rank, c_grp, {24'd0, tk_q});
        htd1_q <= frm(T_STAT, c_rank, c_grp, {390'd0, c_grp, c_rank, acc_h[56:0], lflt, 16'd0, fv});
    end
    reg [16:0] fv_l; reg acc_l;
    wire s_send = spend && !htv1_q;
    always @(posedge ck or negedge rr[19])
        if (!rr[19]) begin htv0_q <= 1'b0; htv1_q <= 1'b0; spend <= 1'b0; acc_l <= 1'b0; end
        else begin
            htv0_q <= tk_pop;
            htv1_q <= s_send;
            acc_l <= t_acc[55];
            spend <= (spend && !s_send) || stat_req || acc_l || (fv != fv_l);
        end
    always @(posedge ck or negedge rr[20]) if (!rr[20]) fv_l <= 17'd0; else fv_l <= fv;
    assign htx_v = {htv1_q, htv0_q};
    assign htx_d = {htd1_q, htd0_q};
    // ================================================================== MU landing replay (mu_rc)
    reg lw_v; reg [9:0] lw_u; reg [6:0] lcnt; reg lpend; reg [9:0] luser; reg rc_v; reg [9:0] rc_u;
    always @(posedge ck) begin lw_u <= lw[10:1]; if (lw_v && lcnt == 7'd0) luser <= lw_u; rc_u <= luser; end
    wire rc_go = lpend && !busy && nbeat == 7'd0 && !wv2;
    always @(posedge ck or negedge rr[21])
        if (!rr[21]) begin lw_v <= 1'b0; lcnt <= 7'd0; lpend <= 1'b0; rc_v <= 1'b0; end
        else begin
            lw_v <= lw[0];
            rc_v <= rc_go;
            if (rc_go) begin lpend <= 1'b0; lcnt <= 7'd0; end
            else if (lw_v) begin
                lcnt <= lcnt + 7'd1;
                if (lcnt == 7'(NB - 1)) lpend <= 1'b1;
            end
        end
    assign mu_rc = {rc_u, rc_v};
    // ================================================================== FAULTS
    reg lepf_q; reg nnan, snan, spf;
    always @(posedge ck) begin lepf_q <= lep_f; end
    always @(*) begin
        fset = 17'd0;
        fset[0]  = (wv2 && busy) || (wv2 && xrdy);                     // x store written while streaming / overfilled
        fset[1]  = p1_xw && p1_gx >= 8'd80;                            // gidx out of range
        fset[2]  = wv2 && nbeat != 7'd0 && (t2[31] != mt_v || t2[30:0] != mt_tag);   // tag changes inside a message
        fset[3]  = bv && (isnan(n_bits) || isnan(s_bits)) || (mg1 && mchk_nan);
        fset[4]  = sni_q[564] || ssi_q[564];                           // spine fault in
        fset[5]  = (nsf_fire && tfn == 2'd0) || (start && tfn == 2'd2) || (nrv && nh && !nsf_fire) || (srv && sh && !nsf_fire);
        fset[6]  = mg1 && mchk_tag;
        fset[7]  = mg1 && mchk_cpy;
        fset[8]  = |sl_ovw;
        fset[9]  = res_l && rpend && !r_cr;                            // RESULT not taken before the next one
        fset[10] = lepf_q;
        fset[11] = t_acc[56];                                          // dsfd_mtp_seq fault
        fset[12] = |lflt;
        fset[13] = hf_l && hf_hv && !hf_pop;
        fset[14] = (dq_l && qpend && !q_cr) || (dw_l && wpend && !w_cr) || (|(dq_n & (dq_n - 1'd1))) || (|(dw_n & (dw_n - 1'd1)))
                   || (|dq_n && |dw_n);
        fset[15] = (o3 && wcnt != 7'd0) || (lw_v && lpend);
        fset[16] = (csr_input&&!csr_w) || schedule_fault || adapter_fault || (|dx_n) || (hrv_q[1] && hrd1_q[3:0] != T_CSRW) || (hrv_q[0] && hrd0_q[3:0] != T_HFWD)
                   || (|(mrv_q & ~sl_en[5:0]));
    end
    always @(posedge ck or negedge rr[22]) if (!rr[22]) fv <= 17'd0; else fv <= fv | fset;
    always @(posedge ck or negedge rr[23]) if (!rr[23]) ctlf_q <= 1'b0; else ctlf_q <= |fv;
    assign ctl_f = ctlf_q;
endmodule

// grant-protocol receiver (ot_dsrom_mtp_lrx/_ltx link pair, sender = ot_dsrom_mtp_ltx inside dsfd_mtp_seq): one grant
// at a time, issued only while the holding register is empty and no grant is in flight (grant -> flit at the pins
// <= 3 edges); the flit lands in a pin stage, then ot_s81hd_hreg32 holds with kept valid copies (<= 12 loads each).  hv / q / pop = valid-only consumer.
module ot_s81hd_ctl_grx #(parameter integer W = 512) (
    input  wire         ck,
    input  wire         rn,
    input  wire         l_v,
    input  wire [W-1:0] l_d,
    output wire         l_g,
    output reg          hv,
    output wire [W-1:0] q,
    input  wire         pop
);
    localparam integer NH = (W + 31) / 32;
    localparam integer NC = (NH + 5) / 6;                              // kept valid copies, <= 6 hold words (12 loads) each
    wire [NH*32-1:0] dq, qq;
    reg [W-1:0] d_p;                                                   // pin stage of the flit, aligned with the copies
    always @(posedge ck) d_p <= l_d;
    assign dq = {{(NH*32-W){1'b0}}, d_p};
    wire [NC-1:0] vc;
    genvar h;
    generate for (h = 0; h < NC; h = h + 1) begin : g_vc
        ot_s81hd_kf u_v (.ck(ck), .d(l_v), .q(vc[h]));
    end
    for (h = 0; h < NH; h = h + 1) begin : g_h
        ot_s81hd_hreg32 u_h (.ck(ck), .en(vc[h / 6]), .d(dq[32*h +: 32]), .q(qq[32*h +: 32]));
    end endgenerate
    assign q = qq[W-1:0];
    reg g, g1, g2, g3, v0, v1;
    assign l_g = g;
    always @(posedge ck or negedge rn)
        if (!rn) begin g <= 1'b0; g1 <= 1'b0; g2 <= 1'b0; g3 <= 1'b0; v0 <= 1'b0; v1 <= 1'b0; hv <= 1'b0; end
        else begin
            g1 <= g; g2 <= g1; g3 <= g2;
            g <= !hv && !v0 && !v1 && !l_v && !g && !g1 && !g2 && !g3;
            v0 <= l_v; v1 <= v0;
            hv <= (hv && !pop) || v1;
        end
endmodule
