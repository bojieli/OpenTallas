`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE (stream 0cm, 2026-10-17): ot_s81sl_xs = the slice x streamer (1 per slice, centre leaf, own clock root).
//
// In the DV S81 die there is no central PQ: every slice streams the FULL x vector to its own 8 frames' x chains, in the
// production stream-ROM order, as the dsfd_pq_lx STATIC_X2 frame word {x2 536 | cc 15 | x1 266 | x0 283 | v} (1,101 b).
//
//   ring all-gather beats -> [pin flops] -> x buffer (24 SRAM macros, one write port per source)
//   issuer word is_d      -> [pin flop] -> fixed per-slice delay (ring-arrival offset) -> calendar ROM reader (2 ROMs),
//                                          GO / phase -> phase ROM 0, stream ROMs (4)
//   ot_s81sl_xs_ctl (the production static PQ stream path, pruned of VM/AQ/return counting) -> stream head + bc_hr
//   x buffer reads on the production QB / IX edges -> f_bus (the production 1,634-b broadcast) -> dsfd_pq_lx (verbatim,
//   DSFD_PQ_STATIC_X2) -> output relay register -> xw_d
//
// Static schedule.  No ready, no credit, no arbitration.  Every issue time is the calendar's, shifted by the slice's
// ring-arrival offset (config, loaded through is_d; the ROM images are identical in all 16 slices).  A buffer read of a
// beat that has not arrived, a second arrival of one beat, two sources writing one beat, a BF read bank conflict and every
// calendar-contract violation set the sticky fault; none of them moves an event.
//
// ---- is_d[159:0] (issuer word; the slice xr fans it out; is_v qualifies it) ------------------------------------------
//   [92:0]    f_iss, dsfd_sp_pq_n order {f_fault, fmt 2, ops 19, obase 19, xps 19, xbase 19, np 3, ph 10, go}.
//             fmt/ops/obase/xps/xbase configure the return write-back (ot_s81sl_cap): not used here.
//   [93]      calendar prime          [94] calendar stage start
//   [106:95]  calendar base (12)      [119:107] calendar length (13)
//   [120]     gather window open: [121] family (0 q, 1 BF16), [122] buffer parity.  Clears that (family, parity)'s
//             arrival table and directs the family's following arrivals to that parity.
//   [123]     load the ring-arrival offset [131:124] (applied at the pin, NOT delayed; only with the delay line empty)
//   [159:132] reserved, must be 0
// Every field except the offset load passes the fixed delay line: it acts OFF + 2 edges after the is_d pin edge.
//
// ---- gathered beats (up to three a cycle; each beat index arrives exactly once) --------------------------------------
//   source k = 0 own leaf, 1 from W, 2 from E: g_v[k], g_fam[k] (0 q, 1 BF16), g_idx[7k +: 7] (global beat, 64 elements),
//   g_d[1024k +: 1024]: q family {e1 10, q1 256, e0 10, q0 256} in [531:0] (blocks 2 idx, 2 idx + 1); BF16 family
//   element 64 idx + l at [16 l +: 16].
//
// ---- x buffer: 3 sources x 8 ot_sram_1r1w_128x256_m1_r2c2 (one write port per source; nothing is arbitrated) --------
//   Macro m of every source bank holds, for buffer parity p (row bit 6):
//     BF16 rows {p, u} (u < 40, 128-element unit): lanes L = 0..15 of the skewed column b = (m - u) mod 8, i.e.
//          elements 128 u + 8 L + b at [16 L +: 16]; beat 2u fills lanes 0..7 (low half), beat 2u+1 lanes 8..15.
//          One beat writes all 8 macros once (masked half rows).  A BF stream word reads unit u_k of group k from
//          macro (b + u_k) mod 8: four groups read four different macros when their units differ mod 8 (true for
//          every BF word of all 72 production stage images; a violation is a fault -- compiler rule).
//     q rows {p, 40 + 2 (beat >> 3) + beat[1]}: macro {beat[2], h, beat[0]} holds block 2 beat + h (256 b of FP8).
//          One beat writes 2 macros; q0 (beat[2] = 0) and q1 (beat[2] = 1) always read two different macros.
//   Block exponents: one flop array [2 x 192] x 10 (three write ports, two read ports, indexed by the production QB
//   index par * 192 + block).  Arrival tables (valid + source per family, parity, beat): flops.
//   Reads occur on the production QB / IX edges (stream head + 1: index registers; + 2: macro read; + 3: output
//   register), so the x fields join bc_hr exactly where the production QB / IX outputs join it.
// ---- latency (measured, tools/s81_slice/xs_bench.sh) ------------------------------------------------------------------
//   frame word = production lane word + OFF - 4 (issuer pin / delay / output edges +3, no die QB-align and bc relay
//   stages -8, output relay +1).  A gathered beat may arrive at the pins on the edge its first stream head loads; its
//   first frame word leaves xw_d 5 edges after the beat's pin edge (pin, SRAM write, read, output register, lx, relay).
// ---- physical structure -----------------------------------------------------------------------------------------------
//   Kept (ot_v41_kreg) copies of every wide select: the BF write rotation per macro and half, the q / BF read-mux selects
//   per 32 / 64-b slice; 8 reset-relay regions.  Floorplan: tools/ref_tile/specs_s81slice/s81sl_xs.json.
// ---------------------------------------------------------------------------------------------------------------------
// ROM image names (INSTANCE, read from +OT_ROM_DIR) exist only in simulation; the hard macro has no parameters.
`ifdef SYNTHESIS
`define OT_S81SL_XS_ROM(n) ot_rom_4096x72_m8
`else
`define OT_S81SL_XS_ROM(n) ot_rom_4096x72_m8 #(.INSTANCE(n))
`endif
module ot_s81sl_xs #(
    // RD2 = 1 (S81-XG structural successor 10-19): the 24-macro read crossbar becomes two registered stages -- a bank-local
    // 8:1 macro select registered beside each source bank column (kept per-bank select copies), then a 3:1 bank select.
    // Long read wires drop from 24 x 1,536 b to 3 x 1,536 b (gate2 GRT stalled 4 h in congestion).  The frame word leaves
    // one edge later (bench --xs-out 2); RD2 = 0 is the original.
    parameter integer RD2 = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [2:0]    g_v,
    input  wire [2:0]    g_fam,
    input  wire [20:0]   g_idx,
    input  wire [3071:0] g_d,
    input  wire          is_v,
    input  wire [159:0]  is_d,
    output wire          xw_v,
    output wire [1100:0] xw_d,
    output reg           fault
);
`ifndef DSFD_PQ_STATIC_X2
    DSFD_PQ_STATIC_X2_required_for_the_dsfd_pq_lx_static_frame_word u_missing_define ();
`endif
    // reset relay: one region per <= ~256 reset loads (issue / gates / fault + lane / 4 arrival tables / write state)
    wire [7:0] rsv;
    ot_rst_relay #(.REGIONS(8), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_i = rsv[0], rs_g = rsv[1], rs_f = rsv[2], rs_w = rsv[7];
    wire [3:0] rs_t = rsv[6:3];

    // ================================================================== pin flops
    reg [2:0] gv_q; reg [2:0] gf_q; reg [20:0] gi_q; reg [3071:0] gd_q;
    reg isv_q; reg [159:0] isd_q;
    always @(posedge clk or negedge rs_g) if (!rs_g) gv_q <= 3'd0; else gv_q <= g_v;
    always @(posedge clk or negedge rs_i) if (!rs_i) isv_q <= 1'b0; else isv_q <= is_v;
    always @(posedge clk) begin gf_q <= g_fam; gi_q <= g_idx; gd_q <= g_d; isd_q <= is_d; end

    // ================================================================== issuer: fixed per-slice delay line
    // payload {gw_par, gw_fam, gw_v, length 13, base 12, start, prime, f_fault, np 3, ph 10, go} = 45 b
    localparam integer PW = 45, ND = 8;
    wire [PW-1:0] is_pay = {isd_q[122:93], isd_q[92], isd_q[13:0]};
    reg [7:0]  off;
    reg [15:0] cyc;
    reg [PW-1:0] dq_p [0:ND-1];
    reg [15:0] dq_t [0:ND-1];
    reg [2:0]  dq_w, dq_r;
    reg [3:0]  dq_n;
    wire       dq_pop = dq_n != 0 && dq_t[dq_r] == cyc;
    // delayed issuer outputs: pulses (go, prime, start, gw_v) for one edge; fields held until the next word
    reg        o_go, o_prime, o_start, o_gw, o_gw_fam, o_gw_par, o_ff;
    reg [9:0]  o_ph; reg [2:0] o_np; reg [11:0] o_base; reg [12:0] o_len;
    reg        is_fault;
`ifdef OT_S81SL_XS_MUT_OFF
    wire [15:0] due = cyc + 16'(off) + 16'(off == 8'd0);   // mutant: the offset delay one edge short
`else
    wire [15:0] due = cyc + 16'(off) + 16'd1;
`endif
    integer kq;
    always @(posedge clk) if (isv_q) dq_p[dq_w] <= is_pay;
    always @(posedge clk) if (isv_q) dq_t[dq_w] <= due;
    always @(posedge clk or negedge rs_i) begin
        if (!rs_i) begin
            off <= 8'd0; cyc <= 16'd0; dq_w <= 3'd0; dq_r <= 3'd0; dq_n <= 4'd0; is_fault <= 1'b0;
            o_go <= 1'b0; o_prime <= 1'b0; o_start <= 1'b0; o_gw <= 1'b0; o_ff <= 1'b0;
            o_gw_fam <= 1'b0; o_gw_par <= 1'b0; o_ph <= 10'd0; o_np <= 3'd0; o_base <= 12'd0; o_len <= 13'd0;
        end else begin
            cyc <= cyc + 16'd1;
            if (isv_q && isd_q[123]) begin
                off <= isd_q[131:124];
                if (dq_n != 0) is_fault <= 1'b1;                             // offset change with words in flight
            end
            if (isv_q && (|isd_q[159:132])) is_fault <= 1'b1;
            if (isv_q && dq_n == 4'(ND) && !dq_pop) is_fault <= 1'b1;       // delay line overrun
            if (isv_q) dq_w <= dq_w + 3'd1;
            if (dq_pop) dq_r <= dq_r + 3'd1;
            dq_n <= dq_n + 4'(isv_q) - 4'(dq_pop);
            o_go <= dq_pop && dq_p[dq_r][0];
            o_prime <= dq_pop && dq_p[dq_r][15];
            o_start <= dq_pop && dq_p[dq_r][16];
            o_gw <= dq_pop && dq_p[dq_r][42];
            // each held field changes only with the word that carries it (GO holds ph / np for the phase-ROM read)
            if (dq_pop && dq_p[dq_r][0]) begin o_ph <= dq_p[dq_r][10:1]; o_np <= dq_p[dq_r][13:11]; end
            if (dq_pop) o_ff <= dq_p[dq_r][14];
            if (dq_pop && (dq_p[dq_r][15] || dq_p[dq_r][16])) begin o_base <= dq_p[dq_r][28:17]; o_len <= dq_p[dq_r][41:29]; end
            if (dq_pop && dq_p[dq_r][42]) begin o_gw_fam <= dq_p[dq_r][43]; o_gw_par <= dq_p[dq_r][44]; end
        end
    end

    // ================================================================== ROMs (images identical in every slice)
    // the production paired calendar ROM (ot_s81_pq_calendar_rom's content, flattened here: its `parameter string`
    // image names do not parse in the synthesis front end): two ot_rom_4096x72_m8 + ot_s81_pq_calendar_reader (PINREG)
    wire [74:0] cal_action;
    wire cal_active, cal_primed, cal_fault;
    wire [11:0] cal_a; wire [71:0] cal_ra, cal_rt;
    `OT_S81SL_XS_ROM("pq_calendar_action") u_cal_action (.clk(clk), .ce_in(1'b1), .addr_in(cal_a), .rd_out(cal_ra));
    `OT_S81SL_XS_ROM("pq_calendar_time") u_cal_time (.clk(clk), .ce_in(1'b1), .addr_in(cal_a), .rd_out(cal_rt));
    ot_s81_pq_calendar_reader #(.ACTION_BITS(75), .PINREG(1)) u_cal_reader (
        .ck(clk), .rst_n(rst_n), .prime(o_prime), .stage_start(o_start), .base(o_base), .length(o_len),
        .rom_addr(cal_a), .rom_action(cal_ra), .rom_time(cal_rt),
        .action(cal_action), .active(cal_active), .primed(cal_primed), .fault(cal_fault));
    wire cal_v = cal_primed || cal_active || (|cal_action);
    wire [71:0] ph_rd;
    `OT_S81SL_XS_ROM("pq_phase0") u_phase0 (.clk(clk), .ce_in(1'b1), .addr_in({1'b0, o_ph, 1'b0}),
        .rd_out(ph_rd));
    wire [11:0] sa_a; wire [3:0] sa_ce; wire [71:0] st_rd [0:3]; wire [47:0] st_sq;
    ot_s81_pq_stream_rom4_sel u_rom4 (.clk(clk), .sa(cal_action[53:40]), .a(sa_a), .ce(sa_ce),
        .rd0(st_rd[0][47:0]), .rd1(st_rd[1][47:0]), .rd2(st_rd[2][47:0]), .rd3(st_rd[3][47:0]), .sq(st_sq));
    `OT_S81SL_XS_ROM("pq_stream0") u_stream0 (.clk(clk), .ce_in(sa_ce[0]), .addr_in(sa_a), .rd_out(st_rd[0]));
    `OT_S81SL_XS_ROM("pq_stream1") u_stream1 (.clk(clk), .ce_in(sa_ce[1]), .addr_in(sa_a), .rd_out(st_rd[1]));
    `OT_S81SL_XS_ROM("pq_stream2") u_stream2 (.clk(clk), .ce_in(sa_ce[2]), .addr_in(sa_a), .rd_out(st_rd[2]));
    `OT_S81SL_XS_ROM("pq_stream3") u_stream3 (.clk(clk), .ce_in(sa_ce[3]), .addr_in(sa_a), .rd_out(st_rd[3]));

    // ================================================================== production stream path
    wire q_consume, b_consume, ctl_fault;
    wire [47:0] hw; wire [35:0] h_hi; wire [15:0] h_b0, h_b1; wire [609:0] bc_hr;
    ot_s81sl_xs_ctl u_ctl (.clk(clk), .rst_n(rst_n), .calendar_v(cal_v), .calendar_action(cal_action), .go(o_go),
        .i_ph(o_ph), .i_np(o_np), .rom_gobf(ph_rd[0]), .rom_sq(st_sq), .q_consume(q_consume), .b_consume(b_consume),
        .hw_o(hw), .h_hi_o(h_hi), .h_b0_o(h_b0), .h_b1_o(h_b1), .bc_hr_o(bc_hr), .fault(ctl_fault));

    // ================================================================== x buffer
    // ---- write side (pin flops -> macro pins: written on the edge after the pin edge) ----
    reg wpar_q, wpar_b;                       // buffer parity each family writes
    reg [95:0] tq_v [0:1]; reg [1:0] tq_s [0:1][0:95];
    reg [79:0] tb_v [0:1]; reg [1:0] tb_s [0:1][0:79];
    reg [9:0]  ex [0:383];                    // block exponents, production QB index
    reg        wr_fault;
    wire [6:0] gi [0:2];
    genvar gs, gm;
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_src
        assign gi[gs] = gi_q[7*gs +: 7];
    end endgenerate
    // per source / macro write port
    wire [255:0] mw_d [0:2][0:7];
    wire [255:0] mw_m [0:2][0:7];
    wire [6:0]   mw_a [0:2][0:7];
    wire         mw_e [0:2][0:7];
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_w
        wire       v = gv_q[gs], f = gf_q[gs];
        wire [6:0] g = gi[gs];
        wire [1023:0] d = gd_q[1024*gs +: 1024];
        // BF16 columns: col[b] lane j = element 8 j + b of the beat
        wire [127:0] col [0:7];
        for (gm = 0; gm < 8; gm = gm + 1) begin : g_col
            genvar j;
            for (j = 0; j < 8; j = j + 1) begin : g_j
                assign col[gm][16*j +: 16] = d[16*(8*j + gm) +: 16];
            end
        end
        wire [5:0] u = g[6:1];
        wire [5:0] qrow = 6'd40 + {1'b0, g[6:3], g[1]};
        for (gm = 0; gm < 8; gm = gm + 1) begin : g_m
            localparam [2:0] M = gm;                       // q macro {c, h, z}
            // BF macro m holds column (m - u) mod 8 of unit u.  The rotation select is a kept per-macro, per-half copy
            // of the unit's low bits, captured from the g_idx pins on the same edge as gi_q (no merge, <= ~256 loads)
            wire [2:0] ur0, ur1;
            ot_v41_kreg #(.W(3)) u_ur0 (.clk(clk), .arst_n(1'b1), .d(g_idx[7*gs + 1 +: 3]), .q(ur0));
            ot_v41_kreg #(.W(3)) u_ur1 (.clk(clk), .arst_n(1'b1), .d(g_idx[7*gs + 1 +: 3]), .q(ur1));
            wire [2:0] bsel0 = M - ur0, bsel1 = M - ur1;
            wire [127:0] cb = {col[bsel1][127:64], col[bsel0][63:0]};
            wire qh = M[1];
            assign mw_e[gs][gm] = v && (f || (g[2] == M[2] && g[0] == M[0]));
            assign mw_a[gs][gm] = f ? {wpar_b, u} : {wpar_q, qrow};
            assign mw_d[gs][gm] = f ? {cb, cb} : (qh ? {d[521:266]} : d[255:0]);
            assign mw_m[gs][gm] = f ? (g[0] ? {{128{1'b1}}, 128'd0} : {128'd0, {128{1'b1}}}) : {256{1'b1}};
        end
    end endgenerate

    // ---- read side ----
    // stage 1 (stream head + 1): decoded read indices
    wire q_par0 = h_b0 >= 16'd192, q_par1 = h_b1 >= 16'd192;
    wire [7:0] q_blk0 = 8'(h_b0 - (q_par0 ? 16'd192 : 16'd0)), q_blk1 = 8'(h_b1 - (q_par1 ? 16'd192 : 16'd0));
    reg  [1:0] r1_qg;                          // gates & q_consume
    reg        r1_qpar;
    reg  [6:0] r1_qbeat0, r1_qbeat1;
    reg  [6:0] r1_qrow;
    reg  [2:0] r1_qm0, r1_qm1;
    reg  [8:0] r1_ei0, r1_ei1;
    reg        r1_qbad;
    reg  [3:0] r1_bg;                          // BF gates & b_consume
    reg  [3:0] r1_bpar;
    reg  [5:0] r1_bu [0:3];
    reg  [2:0] r1_bm [0:3];
    reg        r1_bbad;
    integer k, k2;
    always @(posedge clk or negedge rs_g) begin
        if (!rs_g) begin r1_qg <= 2'd0; r1_bg <= 4'd0; end
        else begin
            r1_qg <= hw[13:12] & {2{q_consume}};
            for (k = 0; k < 4; k = k + 1) r1_bg[k] <= hw[4+k] && b_consume;
        end
    end
    always @(posedge clk) begin
        r1_qpar <= q_par0;
        r1_qbeat0 <= q_blk0[7:1]; r1_qbeat1 <= q_blk1[7:1];
        r1_qrow <= {q_par0, 6'd40 + {1'b0, q_blk0[7:4], q_blk0[2]}};
        r1_qm0 <= {1'b0, q_blk0[0], q_blk0[1]};
        r1_qm1 <= {1'b1, q_blk1[0], q_blk1[1]};
        r1_ei0 <= 9'(h_b0); r1_ei1 <= 9'(h_b1);
        r1_qbad <= (q_consume && hw[12] && h_b0 >= 16'd384) || (q_consume && hw[13] && h_b1 >= 16'd384) ||
                   (q_consume && hw[12] && hw[13] && q_par0 != q_par1);
        r1_bbad <= 1'b0;
        for (k = 0; k < 4; k = k + 1) begin
            r1_bpar[k] <= h_hi[9*k +: 9] >= 9'd48;
            r1_bu[k] <= 6'(h_hi[9*k +: 9] - (h_hi[9*k +: 9] >= 9'd48 ? 9'd48 : 9'd0));
            r1_bm[k] <= 3'(hw[3:1] + 3'(h_hi[9*k +: 9] - (h_hi[9*k +: 9] >= 9'd48 ? 9'd48 : 9'd0)));
            if (b_consume && hw[4+k] && (h_hi[9*k +: 9] >= 9'd96 ||
                (h_hi[9*k +: 9] >= 9'd48 ? h_hi[9*k +: 9] - 9'd48 : h_hi[9*k +: 9]) >= 9'd40)) r1_bbad <= 1'b1;
        end
    end
    // macro read ports (sampled at stage 2 = stream head + 2)
    wire [6:0] mr_a [0:7];
    wire       mr_e [0:7];
    generate for (gm = 0; gm < 8; gm = gm + 1) begin : g_r
        wire [3:0] hit;
        genvar kk;
        for (kk = 0; kk < 4; kk = kk + 1) begin : g_h
            assign hit[kk] = r1_bg[kk] && r1_bm[kk] == 3'(gm);
        end
        wire [6:0] brow = hit[0] ? {r1_bpar[0], r1_bu[0]} : hit[1] ? {r1_bpar[1], r1_bu[1]} :
                          hit[2] ? {r1_bpar[2], r1_bu[2]} : {r1_bpar[3], r1_bu[3]};
        wire qhit = (r1_qg[0] && r1_qm0 == 3'(gm)) || (r1_qg[1] && r1_qm1 == 3'(gm));
        assign mr_e[gm] = qhit || (|hit);
        assign mr_a[gm] = (|hit) ? brow : r1_qrow;
    end endgenerate
    // the macros
    wire [255:0] mrd [0:2][0:7];
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_bank
        for (gm = 0; gm < 8; gm = gm + 1) begin : g_mac
            ot_sram_1r1w_128x256_m1_r2c2 u_mem (
                .clk(clk), .r_ce_in(mr_e[gm]), .r_addr_in(mr_a[gm]), .rd_out(mrd[gs][gm]),
                .w_ce_in(mw_e[gs][gm]), .w_addr_in(mw_a[gs][gm]), .wd_in(mw_d[gs][gm]), .w_mask_in(mw_m[gs][gm]),
                .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
    end endgenerate
    // stage 2: arrival-table lookups, exponents, selection state
    reg  [1:0] r2_qg; reg [9:0] r2_e0, r2_e1;
    reg  [3:0] r2_bg;
    reg        rd_fault;
    wire [1:0] q_s0 = tq_s[r1_qpar][r1_qbeat0], q_s1 = tq_s[r1_qpar][r1_qbeat1];
    wire       q_v0 = tq_v[r1_qpar][r1_qbeat0], q_v1 = tq_v[r1_qpar][r1_qbeat1];
    reg  [3:0] b_vlo, b_vhi; reg [1:0] b_slo [0:3]; reg [1:0] b_shi [0:3]; reg b_conf;
    always @* begin
        b_conf = 1'b0;
        for (k = 0; k < 4; k = k + 1) begin
            b_vlo[k] = tb_v[r1_bpar[k]][{r1_bu[k], 1'b0}]; b_slo[k] = tb_s[r1_bpar[k]][{r1_bu[k], 1'b0}];
            b_vhi[k] = tb_v[r1_bpar[k]][{r1_bu[k], 1'b1}]; b_shi[k] = tb_s[r1_bpar[k]][{r1_bu[k], 1'b1}];
            for (k2 = 0; k2 < k; k2 = k2 + 1)
                if (r1_bg[k] && r1_bg[k2] && r1_bm[k] == r1_bm[k2]) b_conf = 1'b1;
        end
    end
    always @(posedge clk or negedge rs_g) begin
        if (!rs_g) begin r2_qg <= 2'd0; r2_bg <= 4'd0; end
        else begin r2_qg <= r1_qg; r2_bg <= r1_bg; end
    end
`ifdef OT_S81SL_XS_MUT_BANK
    wire [1:0] q_s0m = q_s0 == 2'd2 ? 2'd0 : q_s0 + 2'd1;  // mutant: q0 read from the wrong source bank
`else
    wire [1:0] q_s0m = q_s0;
`endif
    always @(posedge clk) begin r2_e0 <= ex[r1_ei0]; r2_e1 <= ex[r1_ei1]; end
    // read-mux selects {gate, source, macro}: kept copies, one per 32-b q slice / 64-b BF slice (<= ~256 loads each)
    wire [5:0] qsel0 [0:7], qsel1 [0:7], bsel [0:3][0:3];
    generate for (gm = 0; gm < 8; gm = gm + 1) begin : g_qsel
        ot_v41_kreg #(.W(6), .AR(1)) u_q0 (.clk(clk), .arst_n(rs_g), .d({r1_qg[0], q_s0m, r1_qm0}), .q(qsel0[gm]));
        ot_v41_kreg #(.W(6), .AR(1)) u_q1 (.clk(clk), .arst_n(rs_g), .d({r1_qg[1], q_s1, r1_qm1}), .q(qsel1[gm]));
    end
    for (gs = 0; gs < 4; gs = gs + 1) begin : g_bsel
        for (gm = 0; gm < 4; gm = gm + 1) begin : g_sl
            ot_v41_kreg #(.W(6), .AR(1)) u_b (.clk(clk), .arst_n(rs_g),
                .d({r1_bg[gs], gm < 2 ? b_slo[gs] : b_shi[gs], r1_bm[gs]}), .q(bsel[gs][gm]));
        end
    end endgenerate
    always @(posedge clk or negedge rs_f) begin
        if (!rs_f) rd_fault <= 1'b0;
        else begin
            if ((r1_qg[0] && !q_v0) || (r1_qg[1] && !q_v1) || r1_qbad || r1_bbad || b_conf) rd_fault <= 1'b1;
            for (k = 0; k < 4; k = k + 1) if (r1_bg[k] && (!b_vlo[k] || !b_vhi[k])) rd_fault <= 1'b1;
        end
    end
    // stage 3: output registers (zero unless consumed and gated, as the production QB / IX outputs)
    reg [255:0] hq0, hq1; reg [9:0] he0, he1; reg [1023:0] bt_d;
    reg [609:0] bc_hr_x;                      // bc_hr aligned with the x fields (RD2: one more edge)
    integer j;
    generate if (RD2 == 0) begin : g_rd1
        always @(posedge clk) begin
            for (j = 0; j < 8; j = j + 1) begin
                hq0[32*j +: 32] <= qsel0[j][5] ? mrd[qsel0[j][4:3]][qsel0[j][2:0]][32*j +: 32] : 32'd0;
                hq1[32*j +: 32] <= qsel1[j][5] ? mrd[qsel1[j][4:3]][qsel1[j][2:0]][32*j +: 32] : 32'd0;
            end
            he0 <= r2_qg[0] ? r2_e0 : 10'd0;
            he1 <= r2_qg[1] ? r2_e1 : 10'd0;
            for (k = 0; k < 4; k = k + 1)
                for (j = 0; j < 4; j = j + 1)
                    bt_d[256*k + 64*j +: 64] <= bsel[k][j][5] ? mrd[bsel[k][j][4:3]][bsel[k][j][2:0]][64*j +: 64] : 64'd0;
        end
        always @(*) bc_hr_x = bc_hr;
    end else begin : g_rd2
        // stage 3a, per source bank column: 8:1 macro select from kept per-bank copies of the macro fields (each copy
        // drives one bank's 32-b / 64-b slice muxes); stage 3b: gate + 3:1 bank select from kept copies of {gate, bank}.
        reg [255:0] qa0 [0:2], qa1 [0:2]; reg [1023:0] ba [0:2];
        wire [2:0] gq0 [0:7], gq1 [0:7]; wire [2:0] gb [0:3][0:3];
        for (gs = 0; gs < 3; gs = gs + 1) begin : g_bk
            wire [2:0] mq0 [0:7], mq1 [0:7]; wire [2:0] mb [0:3][0:3];
            for (gm = 0; gm < 8; gm = gm + 1) begin : g_q
                ot_v41_kreg #(.W(3)) u_m0 (.clk(clk), .arst_n(1'b1), .d(r1_qm0), .q(mq0[gm]));
                ot_v41_kreg #(.W(3)) u_m1 (.clk(clk), .arst_n(1'b1), .d(r1_qm1), .q(mq1[gm]));
                always @(posedge clk) begin
                    qa0[gs][32*gm +: 32] <= mrd[gs][mq0[gm]][32*gm +: 32];
                    qa1[gs][32*gm +: 32] <= mrd[gs][mq1[gm]][32*gm +: 32];
                end
            end
            for (gm = 0; gm < 16; gm = gm + 1) begin : g_b
                ot_v41_kreg #(.W(3)) u_m (.clk(clk), .arst_n(1'b1), .d(r1_bm[gm / 4]), .q(mb[gm / 4][gm % 4]));
                always @(posedge clk) ba[gs][256*(gm / 4) + 64*(gm % 4) +: 64] <= mrd[gs][mb[gm / 4][gm % 4]][64*(gm % 4) +: 64];
            end
        end
        // {gate, bank} copies, one edge after qsel / bsel (whose macro fields the per-bank copies replace)
        for (gm = 0; gm < 8; gm = gm + 1) begin : g_gq
            ot_v41_kreg #(.W(3), .AR(1)) u_g0 (.clk(clk), .arst_n(rs_g), .d(qsel0[gm][5:3]), .q(gq0[gm]));
            ot_v41_kreg #(.W(3), .AR(1)) u_g1 (.clk(clk), .arst_n(rs_g), .d(qsel1[gm][5:3]), .q(gq1[gm]));
        end
        for (gm = 0; gm < 16; gm = gm + 1) begin : g_gb
            ot_v41_kreg #(.W(3), .AR(1)) u_g (.clk(clk), .arst_n(rs_g), .d(bsel[gm / 4][gm % 4][5:3]), .q(gb[gm / 4][gm % 4]));
        end
        reg [9:0] he0a, he1a; reg [609:0] bc_hr_d;
        always @(posedge clk) begin
            for (j = 0; j < 8; j = j + 1) begin
                hq0[32*j +: 32] <= gq0[j][2] ? qa0[gq0[j][1:0]][32*j +: 32] : 32'd0;
                hq1[32*j +: 32] <= gq1[j][2] ? qa1[gq1[j][1:0]][32*j +: 32] : 32'd0;
            end
            he0a <= r2_qg[0] ? r2_e0 : 10'd0; he0 <= he0a;
            he1a <= r2_qg[1] ? r2_e1 : 10'd0; he1 <= he1a;
            for (k = 0; k < 16; k = k + 1)
                bt_d[256*(k / 4) + 64*(k % 4) +: 64] <= gb[k / 4][k % 4][2] ? ba[gb[k / 4][k % 4][1:0]][256*(k / 4) + 64*(k % 4) +: 64] : 64'd0;
            bc_hr_d <= bc_hr;
        end
        always @(*) bc_hr_x = bc_hr_d;
    end endgenerate

    // ---- write-side state: arrival tables, exponents, parity windows, write faults ----
    integer s, b;
    always @(posedge clk or negedge rs_w) begin
        if (!rs_w) begin wpar_q <= 1'b0; wpar_b <= 1'b0; wr_fault <= 1'b0; end
        else begin
            if (o_gw) begin if (o_gw_fam) wpar_b <= o_gw_par; else wpar_q <= o_gw_par; end
            for (s = 0; s < 3; s = s + 1) if (gv_q[s]) begin
                if (gf_q[s] ? (gi[s] >= 7'd80 || tb_v[wpar_b][gi[s]]) : (gi[s] >= 7'd96 || tq_v[wpar_q][gi[s]]))
                    wr_fault <= 1'b1;
                for (b = 0; b < s; b = b + 1)
                    if (gv_q[b] && gf_q[b] == gf_q[s] && gi[b] == gi[s]) wr_fault <= 1'b1;
            end
        end
    end
    // arrival tables: valid (one reset region per family / parity) + source
    genvar gp;
    generate for (gp = 0; gp < 2; gp = gp + 1) begin : g_tv
        always @(posedge clk or negedge rs_t[gp]) begin
            if (!rs_t[gp]) tq_v[gp] <= '0;
            else begin
                if (o_gw && !o_gw_fam && o_gw_par == gp[0]) tq_v[gp] <= '0;
                for (s = 0; s < 3; s = s + 1)
                    if (gv_q[s] && !gf_q[s] && wpar_q == gp[0] && gi[s] < 7'd96 && !tq_v[gp][gi[s]]) tq_v[gp][gi[s]] <= 1'b1;
            end
        end
        always @(posedge clk or negedge rs_t[2 + gp]) begin
            if (!rs_t[2 + gp]) tb_v[gp] <= '0;
            else begin
                if (o_gw && o_gw_fam && o_gw_par == gp[0]) tb_v[gp] <= '0;
                for (s = 0; s < 3; s = s + 1)
                    if (gv_q[s] && gf_q[s] && wpar_b == gp[0] && gi[s] < 7'd80 && !tb_v[gp][gi[s]]) tb_v[gp][gi[s]] <= 1'b1;
            end
        end
    end endgenerate
    always @(posedge clk)
        for (s = 0; s < 3; s = s + 1) if (gv_q[s]) begin
            if (gf_q[s]) begin if (gi[s] < 7'd80 && !tb_v[wpar_b][gi[s]]) tb_s[wpar_b][gi[s]] <= 2'(s); end
            else if (gi[s] < 7'd96 && !tq_v[wpar_q][gi[s]]) tq_s[wpar_q][gi[s]] <= 2'(s);
        end
    always @(posedge clk)
        for (s = 0; s < 3; s = s + 1)
            if (gv_q[s] && !gf_q[s] && gi[s] < 7'd96) begin
                ex[(wpar_q ? 9'd192 : 9'd0) + {1'b0, gi[s], 1'b0}] <= gd_q[1024*s + 256 +: 10];
                ex[(wpar_q ? 9'd192 : 9'd0) + {1'b0, gi[s], 1'b1}] <= gd_q[1024*s + 522 +: 10];
            end

    // ================================================================== frame word: the production f_bus -> dsfd_pq_lx
    wire [1633:0] f_bus;
`ifdef OT_S81SL_XS_MUT_QSWAP
    assign f_bus = {bc_hr_x[609:578], hq1, he0, hq0, he1, bc_hr_x[45:0], bt_d};   // mutant: q0 / q1 swapped
`else
    assign f_bus = {bc_hr_x[609:578], hq0, he0, hq1, he1, bc_hr_x[45:0], bt_d};
`endif
    wire lx_fault;
    wire [1100:0] xe_unused;
    // xws / xes are the legacy ready/overrun status inputs: with DSFD_PQ_STATIC_X2 they have no effect on data,
    // validity, faults or progress (dsfd_sp_pq_n header); the slice has no start-block status to give them.
    wire [1100:0] xw_l;
    dsfd_pq_lx u_lane (.ck(clk), .rst(rs_f), .f_bus(f_bus), .f_fault(o_ff), .xws(3'b000), .xes(3'b000),
        .xw(xw_l), .xe(xe_unused), .f_fault_c(lx_fault));
    // output relay: the frame-word pin flops spread over a full face while the lane register stays at the band
    reg [1100:0] xw_q;
    always @(posedge clk) xw_q <= xw_l;
    assign xw_d = xw_q;
    assign xw_v = xw_q[0];

    // ================================================================== sticky fault (registered output)
    always @(posedge clk or negedge rs_f)
        if (!rs_f) fault <= 1'b0;
        else if (is_fault || cal_fault || ctl_fault || wr_fault || rd_fault || lx_fault) fault <= 1'b1;
endmodule
`undef OT_S81SL_XS_ROM
