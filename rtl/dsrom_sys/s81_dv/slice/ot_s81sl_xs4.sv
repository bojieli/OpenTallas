`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-XG4XS (LEAD4-S81, 10-20): ot_s81sl_xs4 -- native-bounded successor of the slice x streamer hard leaf (the x
// streamer half of element s81sl_xg; the ring stop half is ot_s81sl_rs, S81-XG4).
//
// Function: CURRENT MAIN ot_s81sl_xs cycle for cycle, with every input landing ONE edge earlier in a capture stage
// (K = 1): every output (xw_v, xw_d, fault) equals main ot_s81sl_xs's output one edge later when both see the same
// inputs.  All internal relative timing (gather write -> buffer read, issuer -> calendar -> stream head -> frame word)
// is exactly main's.  Checked by tools/s81_slice/xs4_equiv.sh against main ot_s81sl_xs + a one-edge testbench relay
// on all outputs (production L0 / L2 programs, random traffic, in-flight reset).
// Schedule: +1 edge on the whole x streamer (gather beats and issuer words alike) -> handed to MU.S81.CAL (one
// edge on the slice x path; equal for xw_v / xw_d / fault).  Together with the rs leaf's RELAY = 1 gather edge the
// gathered beat reaches the x buffer 2 edges later than in main ot_s81sl_xg, the issuer word 1 edge later.
//
// Why: XG3's ot_s81sl_xs3 (= main ot_s81sl_xs RD2=2) failed the mandatory mapped native census (codex 3f8b2506d:
// 1,156 drivers > 32 loads, max 2,529: family bits gf_q, macro write masks mw_m 1,024 pins, merged AND/NAND selects,
// rotation / read-bank / gather selects, gi_q, dq_r, cal reader rp, wpar, ctl reset 548, bc_hr), its gate placed at
// -4.0 ns (w_mask_in / tq_s) and stalled in GRT congestion.
//
// Native-load structure (every driver <= 32 load pins by construction; the gate's mapped census checks it):
//   capture  every gather control port bit (g_v / g_fam / g_idx per source) feeds 21 kept copy flops; g_d / is_d
//            bits feed one data flop each; is_v 2 kept copies.  Level-B registers = main's pin flops, decoded.
//   write    per macro (24) a write leaf of kept registered selects: 8 x 9 one-hot data selects (8 BF rotations +
//            q mode, each copy 32 data pins), 4 + 4 mask-half copies (32 mask pins each), w_ce, w_addr, own wpar
//            replica.  Arrival-table set one-hots per source (16-entry blocks), 22 table groups of 8 entries with
//            their own parity replica / window clear; per-source exponent SRAMs (2 x ot_sram_1r1w2c_128x64_m1 per
//            source, beat bit 2 groups: block exponents 3.84 kb leave flops for SRAM).
//   issuer   8-entry delay line with registered one-hot write enables (2 copies / entry) and 5 one-hot read pointer
//            copies each with its own pop compare; 8 window-open copies.
//   read     stream head copies in the controller (4 lookup copies + 1 + BF); arrival-table lookups by registered
//            full one-hot index lines (192 q / 80 BF per copy); registered one-hot read-mux lines (12 / 24 per 32-b slice)
//            -> stage-3 AND-OR; bank one-hot copies for the 4 stream ROMs.
//   calendar native copy of ot_s81_pq_calendar_reader (PINREG): one-hot row pointers, 6 due copies (own pointer,
//            age, active), registered row write enables.
//   ctl      native copy of ot_s81sl_xs_ctl: config tag one-hot at the pin, hold-in-reset payload on regional
//            enables, bv copies for the lane word select.  Lane = dsfd_pq_lx (STATIC_X2) function with bv copies.
//   reset    port -> 2 sync flops -> 4 early (capture valids, main's release edge) / 8 -> 54 regions / 8 -> 4-stage
//            chain -> 39 controller regions; release = main's edge + 1 everywhere; payload reset-free.
// Mutants (negative controls; DUT only): OT_S81SL_XS_MUT_BANK / _OFF / _QSWAP (as main), OT_S81SL_XS4_MUT_WCOPY (one
// rotation-select copy of write leaf (1, 3) one column off), OT_S81SL_XS4_MUT_TPAR (q table group 5 parity replica
// misses the window open), OT_S81SL_XS4_MUT_EXP (q1 exponent half select swapped).
// ---------------------------------------------------------------------------------------------------------------------
`ifdef SYNTHESIS
`define OT_S81SL_XS4_ROM(n) ot_rom_4096x72_m8
`else
`define OT_S81SL_XS4_ROM(n) ot_rom_4096x72_m8 #(.INSTANCE(n))
`endif

// ===================================================================================================================== reset
// rst_n port drives 2 flops.  e: 4 early regions (release R+3 = main's ot_rst_relay edge: the capture valids, which
// stand one edge before main's pin flops); l2: 54 regions (R+4 = main + 1); k4: 39 controller regions (R+7 = main's
// ctl R+6 + 1).  Assert is clocked (2 edges, chain +4).
(* keep_hierarchy *)
module ot_s81sl_xs4_rst (
    input  wire        clk,
    input  wire        rst_n_in,
    output wire [3:0]  rst_e,
    output wire [53:0] rst_l,
    output wire [38:0] rst_k,
    output wire [23:0] rst_x    // XG5: extra controller hold-enable leaves (same release edge as rst_k)
);
    (* keep = "true", dont_touch = "true" *) reg s0, s1;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) begin s0 <= 1'b0; s1 <= 1'b0; end
        else begin s0 <= 1'b1; s1 <= s0; end
    (* keep = "true", dont_touch = "true" *) reg [3:0]  e1;
    (* keep = "true", dont_touch = "true" *) reg [7:0]  l1;
    (* keep = "true", dont_touch = "true" *) reg [53:0] l2;
    (* keep = "true", dont_touch = "true" *) reg [7:0]  c1;
    (* keep = "true", dont_touch = "true" *) reg [38:0] k1, k2, k3, k4;
    (* keep = "true", dont_touch = "true" *) reg [23:0] x1, x2, x3, x4;
    integer k;
    always @(posedge clk) begin
        e1 <= {4{s1}};
        l1 <= {8{s1}};
        for (k = 0; k < 54; k = k + 1) l2[k] <= l1[k / 7];
        c1 <= {8{s1}};
        for (k = 0; k < 39; k = k + 1) k1[k] <= c1[k / 5];
        k2 <= k1;
        k3 <= k2;
        k4 <= k3;
        for (k = 0; k < 24; k = k + 1) x1[k] <= c1[k / 3];
        x2 <= x1; x3 <= x2; x4 <= x3;
    end
    assign rst_e = e1;
    assign rst_l = l2;
    assign rst_k = k4;
    assign rst_x = x4;
endmodule

// ===================================================================================================================== XG5 kept helpers
// (listed in the kit's synth_keep_modules; non-parameterised so the keep matches the mapped name)
// arrival-table line predecode: line x = 96 p + beat (beat = k[7:1] < 96) == hi[x / 16] && lo[x % 16]
(* keep_hierarchy = 1 *) module ot_s81sl_xs4_pdec (input wire p, input wire [6:0] k, output wire [11:0] hi, output wire [15:0] lo);
    genvar j;
    generate for (j = 0; j < 12; j = j + 1) begin : g_hi
        assign hi[j] = (p == (j >= 6)) && k[6:4] == 3'(j % 6);
    end
    for (j = 0; j < 16; j = j + 1) begin : g_lo
        assign lo[j] = k[3:0] == 4'(j);
    end endgenerate
endmodule
// calendar reader due term (one instance per consumer group: same function, own gates)
(* keep_hierarchy = 1 *) module ot_s81sl_xs4_due (input wire act, input wire cnz, input wire [23:0] t, input wire [23:0] age, output wire due);
    assign due = act && cnz && t == age;
endmodule
// calendar reader fetch term (one instance per consumer group)
(* keep_hierarchy = 1 *) module ot_s81sl_xs4_fetch (input wire priming, input wire due5, input wire [12:0] fi, input wire [12:0] nrows,
                                                    output wire fetch);
    assign fetch = (priming && fi < nrows && fi < 13'd4) || (due5 && fi < nrows);
endmodule

// ===================================================================================================================== calendar
// native copy of ot_s81_pq_calendar_reader #(.ACTION_BITS(75), .PINREG(1)): same rows, same edges, same faults.
// rg[16:0] regional resets (release = main reader's rst_i + 1 edge).
module ot_s81sl_xs4_cal (
    input  wire        ck,
    input  wire [16:0] rg,
    input  wire        prime,
    input  wire        stage_start,
    input  wire [11:0] base,
    input  wire [12:0] length,
    output reg  [11:0] rom_addr,
    input  wire [71:0] rom_action,
    input  wire [71:0] rom_time,
    output wire [74:0] action,
    output wire        active,
    output reg         primed,
    output reg         fault
);
    localparam integer AB = 75, EB = 72;
    // ---- pin capture (PINREG): prime / stage_start kept copies, payload one flop
    (* keep = "true" *) reg [5:0] pq;   // XG5c: 6 copies (pok[2] base_q / pok[4] nrows / pok[5] consume_index; was 36 mapped loads)
    (* keep = "true" *) reg [6:0] sq;
    always @(posedge ck or negedge rg[0])
        if (!rg[0]) begin pq <= 6'd0; sq <= 7'd0; end
        else begin pq <= {6{prime}}; sq <= {7{stage_start}}; end
    reg [11:0] base_p; reg [12:0] len_p; reg [71:0] ra_p, rt_p;
    always @(posedge ck) begin base_p <= base; len_p <= length; ra_p <= rom_action; rt_p <= rom_time; end
    wire [143:0] rin = {rt_p, ra_p};
    // ---- shared state
    reg [12:0] nrows, fetch_index, consume_index; reg [11:0] base_q;
    reg [2:0]  fetch_valid; reg priming; reg [2:0] count; reg [1:0] wp; reg [23:0] last_ts;
    // ---- rows (4 x 99 b used: action 75, timestamp 24) with registered one-hot write enables (4 x 25-b copies)
    wire [98:0] row [0:3];
    (* keep = "true" *) reg [35:0] weq;   // [9 e + chunk]  XG5: 9 x 11-b chunks per row (was 4 x 25 b -> 48-50 mapped loads)
    genvar ge, gk;
    generate for (ge = 0; ge < 4; ge = ge + 1) begin : g_row
        reg [98:0] r;
        integer c;
        always @(posedge ck)
            for (c = 0; c < 9; c = c + 1) if (weq[9*ge + c]) r[11*c +: 11] <= rin[11*c +: 11];
        assign row[ge] = r;
    end endgenerate
    // ---- replicated due copies k = 0..5: own ts/END pointer (rpt), action pointer (rpa, k < 4), age, active
    wire [5:0] due, endm, actw;
    wire [23:0] tsm [0:5], agew [0:5];
    wire cons_last = consume_index + 13'd1 == nrows;
    wire cnz = count != 3'd0;
    wire bad = active || priming || fetch_valid != 3'd0 || len_p == 13'd0 || len_p > 13'd4096 ||
               {1'b0, base_p} + len_p > 13'd4096;
    wire [5:0] pok = pq & {6{!bad}};
    wire [74:0] act_nx;
    generate for (gk = 0; gk < 6; gk = gk + 1) begin : g_due
        (* keep = "true" *) reg [3:0] rpt;
        (* keep = "true" *) reg [3:0] rpa;   // action pointer (used by k < 4)
        (* keep = "true" *) reg [23:0] age;
        (* keep = "true" *) reg act;
        wire pk = gk < 3 ? pok[0] : pok[1];
        reg [23:0] t; reg en;
        integer e;
        always @* begin
            t = 24'd0; en = 1'b0;
            for (e = 0; e < 4; e = e + 1) if (rpt[e]) begin t = t | row[e][98:75]; en = en | row[e][EB]; end
        end
        assign tsm[gk] = t; assign endm[gk] = en; assign agew[gk] = age; assign actw[gk] = act;
        // XG5: due from a kept term instance; the action-chunk copy (k < 4) takes its own instance below
        ot_s81sl_xs4_due u_due (.act(act), .cnz(cnz), .t(t), .age(age), .due(due[gk]));
        always @(posedge ck or negedge rg[5 + gk]) begin
            if (!rg[5 + gk]) begin age <= 24'd0; act <= 1'b0; end
            else begin
                age <= act ? age + 24'd1 : (sq[gk] ? 24'd0 : age);
                act <= (due[gk] && (en || cons_last)) ? 1'b0 : (sq[gk] ? 1'b1 : act);
            end
        end
        always @(posedge ck or negedge rg[11 + gk / 3]) begin
            if (!rg[11 + gk / 3]) begin rpt <= 4'b0001; rpa <= 4'b0001; end
            else begin
                rpt <= due[gk] ? {rpt[2:0], rpt[3]} : (pk ? 4'b0001 : rpt);
                if (gk < 4) rpa <= due[gk] ? {rpa[2:0], rpa[3]} : (pk ? 4'b0001 : rpa);
            end
        end
        // action chunks (k < 4): action <= due ? rows[rp] : 0
        if (gk < 4) begin : g_ach
            localparam integer LO = 19 * gk, HI = (gk == 3) ? 74 : 19 * gk + 18;
            reg [HI-LO:0] a, am;
            integer ea;
            always @* begin
                am = '0;
                for (ea = 0; ea < 4; ea = ea + 1) if (rpa[ea]) am = am | row[ea][HI:LO];
            end
            wire due_a;
            ot_s81sl_xs4_due u_due_a (.act(act), .cnz(cnz), .t(t), .age(age), .due(due_a));
            always @(posedge ck or negedge rg[13 + gk])
                if (!rg[13 + gk]) a <= '0; else a <= due_a ? am : '0;
            assign act_nx[HI:LO] = a;
        end
    end endgenerate
    assign action = act_nx;
    assign active = actw[5];
    // ---- shared next state (copy 5 = control, copy 4 = last timestamp)
    // XG5: the shared next-state copy of due[5] (consume / count / fetch / fault) from its own kept term instance
    wire due5;
    ot_s81sl_xs4_due u_due5 (.act(actw[5]), .cnz(cnz), .t(tsm[5]), .age(agew[5]), .due(due5));
    // XG5: fetch from two kept term instances (ROM address side / index + valid side; one term mapped to 46 loads)
    // XG5c: consume_index and last_ts (2 x 12 b) take their own kept due instances (due5 mapped 37, due[4] 57 loads)
    wire due5c, due4l0, due4l1;
    ot_s81sl_xs4_due u_due5c (.act(actw[5]), .cnz(cnz), .t(tsm[5]), .age(agew[5]), .due(due5c));
    ot_s81sl_xs4_due u_due4l0 (.act(actw[4]), .cnz(cnz), .t(tsm[4]), .age(agew[4]), .due(due4l0));
    ot_s81sl_xs4_due u_due4l1 (.act(actw[4]), .cnz(cnz), .t(tsm[4]), .age(agew[4]), .due(due4l1));
    wire fetch, fetch_r;
    ot_s81sl_xs4_fetch u_fetch   (.priming(priming), .due5(due5), .fi(fetch_index), .nrows(nrows), .fetch(fetch));
    ot_s81sl_xs4_fetch u_fetch_r (.priming(priming), .due5(due5), .fi(fetch_index), .nrows(nrows), .fetch(fetch_r));
    wire push = fetch_valid[2];
    wire [1:0] wp_nx = push ? wp + 2'd1 : (pok[3] ? 2'd0 : wp);
    integer e2;
    always @(posedge ck) for (e2 = 0; e2 < 4; e2 = e2 + 1) weq[9*e2 +: 9] <= {9{fetch_valid[1] && wp_nx == 2'(e2)}};
    reg [12:0] read_a;
    always @(posedge ck or negedge rg[1]) begin
        if (!rg[1]) begin rom_addr <= 12'd0; base_q <= 12'd0; end
        else begin
            if (pok[2]) base_q <= base_p;
            if (fetch_r) begin read_a = {1'b0, base_q} + fetch_index; rom_addr <= read_a[11:0]; end
        end
    end
    always @(posedge ck or negedge rg[2]) begin
        if (!rg[2]) begin nrows <= 13'd0; fetch_index <= 13'd0; end
        else begin
            if (pok[4]) nrows <= len_p;
            if (pok[3]) fetch_index <= 13'd0;
            if (fetch) fetch_index <= fetch_index + 13'd1;
        end
    end
    always @(posedge ck or negedge rg[3]) begin
        if (!rg[3]) consume_index <= 13'd0;
        else begin
            if (pok[5]) consume_index <= 13'd0;
            if (due5c) consume_index <= consume_index + 13'd1;
        end
    end
    always @(posedge ck or negedge rg[4]) begin
        if (!rg[4]) last_ts <= 24'd0;
        else begin
            last_ts[11:0]  <= due4l0 ? tsm[4][11:0]  : (sq[6] ? 12'd0 : last_ts[11:0]);
            last_ts[23:12] <= due4l1 ? tsm[4][23:12] : (sq[6] ? 12'd0 : last_ts[23:12]);
        end
    end
    always @(posedge ck or negedge rg[0]) begin
        if (!rg[0]) begin
            primed <= 1'b0; fault <= 1'b0; priming <= 1'b0; wp <= 2'd0; count <= 3'd0; fetch_valid <= 3'd0;
        end else begin
            fetch_valid <= {fetch_valid[1:0], fetch};
            if (pq[3]) begin
                if (bad) fault <= 1'b1;
                else begin count <= 3'd0; priming <= 1'b1; primed <= 1'b0; end
            end
            wp <= wp_nx;
            if (push) begin
                if (count == 3'd4 && !due5) fault <= 1'b1;
                if (rin[143:99] != 45'd0 || rin[74:73] != 2'd0) fault <= 1'b1;
                if (priming && {10'd0, count} + 13'd1 == (nrows < 13'd4 ? nrows : 13'd4)) begin priming <= 1'b0; primed <= 1'b1; end
            end
            if (push || due5) count <= count + 3'(push) - 3'(due5);
            if (sq[5] && (!primed || active || pq[3])) fault <= 1'b1;
            if (active) begin
                if (agew[5] == 24'hffffff || count == 3'd0 || tsm[5] < agew[5]) fault <= 1'b1;
                if (due5) begin
                    if (consume_index != 13'd0 && tsm[5] <= last_ts) fault <= 1'b1;
                    if (endm[5]) begin primed <= 1'b0; if (!cons_last) fault <= 1'b1; end
                    else if (cons_last) begin primed <= 1'b0; fault <= 1'b1; end
                end
            end
        end
    end
endmodule

// ===================================================================================================================== ctl
// native copy of ot_s81sl_xs_ctl (same registers, same edges).  Differences, all value-preserving:
//   - reset: rc (reset-value flops), rh (payload that holds while main's rst_c is low = enable by region), rb (bc);
//   - action = ca_q (main gates it by cv_q; in the x streamer calendar_v == 0 implies calendar_action == 0);
//   - config tag one-hot captured beside ca_q; stream head copies for the x streamer read side; bv copies.
module ot_s81sl_xs4_ctl (
    input  wire          clk,
    input  wire [3:0]    rc,
    input  wire [31:0]   rh,
    input  wire [2:0]    rb,
    input  wire [23:0]   rx,       // XG5: second hold-enable leaves (wide payload split to <= 16 bits per enable copy)
    input  wire          calendar_v,
    input  wire [74:0]   calendar_action,
    input  wire          go,
    input  wire [9:0]    i_ph,
    input  wire [2:0]    i_np,
    input  wire          rom_gobf,
    input  wire [47:0]   rom_sq,
    // stream head copies: q k = 0..4 {h_b0 16, h_b1 16, hw[13:12]} + q_consume; BF {h_hi 36, hw[7:1]} + b_consume
    output wire [169:0]  hq_o,
    output wire [4:0]    qc_o,
    output wire [42:0]   hb_o,
    output wire          bc_o,
    output wire [609:0]  bc_hr_o,
    output wire [68:0]   bv_o,     // XG5: 69 copies (16 lane bits each; was 36 x 32 -> 64 mapped loads)
    output reg           fault
);
    localparam integer PHW = 10, SAW = 14, KMAX = 6144, NBLK = 192, BW = 1634;
    wire rst_c = rc[0];
    reg cv_q, go_q; reg [74:0] ca_q; reg [9:0] iph_q; reg [2:0] inp_q; reg [3:0] cfg_oh;
    always @(posedge clk) begin
        cv_q <= calendar_v; ca_q <= calendar_action; iph_q <= i_ph; inp_q <= i_np; go_q <= go;
        cfg_oh <= 4'b0001 << calendar_action[64:63];
    end
    reg [1:0] act_hi_q;
    always @(posedge clk) act_hi_q <= ca_q[74:73];
    wire [74:0] action = ca_q;
    wire [1:0]  accept_tag = action[1:0];
    wire [1:0]  launch_tag = action[67:66];
    reg sv [0:3], sr [0:3], si [0:3];
    reg [PHW-1:0] s_ph [0:3];
    reg [2:0]     s_np [0:3];
    reg           s_pw0 [0:3];
    reg           a_v, a_v2;
    reg [1:0]     a_tag, a_tag2;
    reg [PHW-1:0] a_ph;
    reg [2:0]     a_np;
    wire [3:0]    a_oh_d = go_q ? (4'b0001 << accept_tag) : 4'b0000;
    reg  [3:0]    a_oh;
    always @(posedge clk or negedge rb[0]) if (!rb[0]) a_oh <= 4'd0; else a_oh <= a_oh_d;
    always @(posedge clk) a_np <= inp_q;
    integer ka;
    always @(posedge clk)
        for (ka = 0; ka < 4; ka = ka + 1)
            if (a_oh[ka]) begin s_ph[ka] <= a_ph; s_np[ka] <= a_np; end
    reg phase0_pin, phase_pin_valid; reg [1:0] phase_pin_tag;
    always @(posedge clk) begin phase0_pin <= rom_gobf; phase_pin_tag <= a_tag2; end
    always @(posedge clk or negedge rc[1]) if (!rc[1]) phase_pin_valid <= 1'b0; else phase_pin_valid <= a_v2;
    reg           r0_v, r0_lp, r0_lo, r0_fam; reg [1:0] r0_tag; reg [2:0] r0_pos; reg [SAW-1:0] r0_a;
    reg           ra_v, ra_lp, ra_lo, ra_fam; reg [1:0] ra_tag; reg [2:0] ra_pos;
    reg           r1_v, r1_lp, r1_lo, r1_fam; reg [1:0] r1_tag; reg [2:0] r1_pos;
    reg [47:0]    r1_w;
    always @(posedge clk) r1_w <= rom_sq;
    wire          r1_spar = r1_tag[0] ^ r1_pos[0];
    wire [7:0]    r1_u  = r1_w[8:1];
    wire [2:0]    r1_b  = r1_w[11:9];
    wire [1:0]    r1_sv = r1_w[13:12];
    wire [7:0]    r1_g0 = r1_w[4] ? r1_w[15:8]  : 8'd0;
    wire [7:0]    r1_g1 = r1_w[5] ? r1_w[23:16] : 8'd0;
    wire [7:0]    r1_g2 = r1_w[6] ? r1_w[31:24] : 8'd0;
    wire [7:0]    r1_g3 = r1_w[7] ? r1_w[39:32] : 8'd0;
    wire [7:0]    r1_m01 = (r1_g1 > r1_g0) ? r1_g1 : r1_g0;
    wire [7:0]    r1_m23 = (r1_g3 > r1_g2) ? r1_g3 : r1_g2;
    wire [9:0]    r1_nq;
    ot_v41_inc #(.W(10)) u_nq (.a({r1_u[5:0], r1_sv[1], r1_b}), .inc(1'b1), .y(r1_nq), .co());
    wire [15:0] r1_blk0 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b0, r1_b};
    wire [15:0] r1_blk1 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b1, r1_b};
    reg           r2_v, r2_lp, r2_lo, r2_fam, r2_spar; reg [1:0] r2_tag; reg [2:0] r2_pos; reg [47:0] r2_w;
    reg [9:0]     r2_nq; reg [7:0] r2_m01, r2_m23; reg [15:0] r2_b0, r2_b1; reg [35:0] r2_hi;
    reg           r3_v, r3_lp, r3_lo, r3_fam, r3_spar; reg [1:0] r3_tag; reg [2:0] r3_pos; reg [47:0] r3_w;
    reg [9:0]     r3_nq; reg [7:0] r3_umax; reg [15:0] r3_b0, r3_b1; reg [35:0] r3_hi;
    wire [7:0]    r3_nb;
    ot_v41_inc #(.W(8)) u_nb (.a(r3_umax), .inc(1'b1), .y(r3_nb), .co());
    localparam integer EW = 48 + 15 + 4 + 2 + 3 + 16 + 16 + 36;
    wire [EW-1:0] r3_e = {r3_w, r3_fam ? {r3_nb, 7'd0} : {r3_nq, 5'd0}, r3_spar, r3_lp, r3_lo, r3_fam, r3_tag, r3_pos,
                          r3_b0, r3_b1, r3_hi};
    reg [EW-1:0] he; reg hv;
    wire [47:0] hw = he[EW-1 -: 48];
    wire        h_fam = he[EW-67];
    wire [2:0]  h_pos = he[EW-70 -: 3];
    // ---- stream head copies (x streamer read side), held in reset like he
    wire [33:0] hq_d = {r3_b0, r3_b1, r3_w[13:12]};
    wire [42:0] hb_d = {r3_hi, r3_w[7:1]};
    wire        qc_d = r3_v && r3_e[EW-48] && !r3_e[EW-67];
    wire        bc_d = r3_v && r3_e[EW-48] && r3_e[EW-67];
    genvar gq;
    generate for (gq = 0; gq < 5; gq = gq + 1) begin : g_hq
        (* keep = "true" *) reg [33:0] h;
        (* keep = "true" *) reg c;
        always @(posedge clk) begin
            if (rh[20 + 2*gq]) h[16:0] <= hq_d[16:0];
            if (rh[21 + 2*gq]) h[33:17] <= hq_d[33:17];
        end
        always @(posedge clk or negedge rc[3]) if (!rc[3]) c <= 1'b0; else c <= qc_d;
        assign hq_o[34*gq +: 34] = h;
        assign qc_o[gq] = c;
    end endgenerate
    (* keep = "true" *) reg [42:0] hb_q;
    always @(posedge clk) begin
        if (rh[30]) hb_q[10:0]  <= hb_d[10:0];
        if (rx[18]) hb_q[21:11] <= hb_d[21:11];
        if (rh[31]) hb_q[31:22] <= hb_d[31:22];
        if (rx[19]) hb_q[42:32] <= hb_d[42:32];
    end
    (* keep = "true" *) reg bc_c;
    always @(posedge clk or negedge rc[3]) if (!rc[3]) bc_c <= 1'b0; else bc_c <= bc_d;
    assign hb_o = hb_q; assign bc_o = bc_c;
    reg qc_q, bc_q;
    always @(posedge clk or negedge rc[3])
        if (!rc[3]) begin qc_q <= 1'b0; bc_q <= 1'b0; end
        else begin qc_q <= qc_d; bc_q <= bc_d; end
    reg         p1_xs_v, p1_xb_v, p1_go, p1_gobf, p1_cfg;
    reg [7:0]   p1_p; reg [2:0] p1_b, p1_pos, p1_np; reg [1:0] p1_sv, p1_tag; reg [3:0] p1_bsv; reg [31:0] p1_u;
    reg [PHW-1:0] p1_ph;
    reg         bt_xs_v, bt_xb_v;
    reg [7:0]   bt_p; reg [2:0] bt_b; reg [1:0] bt_sv;
    wire [255:0] bt_q0 = '0, bt_q1 = '0;
    wire [9:0]   bt_e0 = '0, bt_e1 = '0;
    reg [3:0]   bt_bsv; reg [31:0] bt_u;
    reg         bt_go, bt_gobf, bt_cfg; reg [1:0] bt_tag; reg [2:0] bt_np, bt_pos; reg [PHW-1:0] bt_ph;
    always @(posedge clk) begin
        p1_p <= hw[8:1]; p1_b <= h_fam ? hw[3:1] : hw[11:9];
        p1_sv <= hw[13:12]; p1_pos <= h_pos;
        p1_bsv <= hw[7:4]; p1_u <= hw[39:8];
        bt_p <= p1_p; bt_b <= p1_b; bt_sv <= p1_sv; bt_pos <= p1_pos; bt_bsv <= p1_bsv; bt_u <= p1_u;
    end
    wire [BW-1025:0] bc_h = {bt_cfg, bt_ph, bt_np, bt_go, bt_gobf, bt_tag, bt_xs_v, bt_p, bt_b, bt_sv, bt_q0, bt_e0, bt_q1,
                             bt_e1, bt_pos, bt_pos, bt_xb_v, bt_b, bt_bsv, bt_u};
    localparam integer BRT = PHW + 9;
    reg  [BW-1025:0] bc_hd;
    reg  [BRT:0]     bc_hc;
    always @(posedge clk) bc_hd <= bc_h;
    always @(posedge clk or negedge rb[0])
        if (!rb[0]) bc_hc <= '0; else bc_hc <= {bc_h[BW-1025 -: BRT], bc_h[39]};
    reg  [BW-1025:0] bc_hr;
    always @* begin bc_hr = bc_hd; bc_hr[BW-1025 -: BRT] = bc_hc[BRT:1]; bc_hr[39] = bc_hc[0]; end
    assign bc_hr_o = bc_hr;
    // bv = bc_hr[39] | bc_hr[594] (lane f_bus[1063] | f_bus[1618]): 36 registered copies beside bc_hc, from 2 + 2
    // kept copies of bt_xb_v / bt_gobf
    (* keep = "true" *) reg [3:0] btx_c, btg_c;
    always @(posedge clk or negedge rc[2])
        if (!rc[2]) begin btx_c <= 4'd0; btg_c <= 4'd0; end
        else begin btx_c <= {4{p1_xb_v}}; btg_c <= {4{p1_gobf}}; end
    (* keep = "true" *) reg [68:0] bv_c;
    integer kb;
    always @(posedge clk or negedge rb[1])
        if (!rb[1]) bv_c[17:0] <= 18'd0; else for (kb = 0; kb < 18; kb = kb + 1) bv_c[kb] <= btx_c[0] | btg_c[0];
    always @(posedge clk or negedge rx[20])
        if (!rx[20]) bv_c[34:18] <= 17'd0; else for (kb = 18; kb < 35; kb = kb + 1) bv_c[kb] <= btx_c[1] | btg_c[1];
    always @(posedge clk or negedge rb[2])
        if (!rb[2]) bv_c[52:35] <= 18'd0; else for (kb = 35; kb < 53; kb = kb + 1) bv_c[kb] <= btx_c[2] | btg_c[2];
    always @(posedge clk or negedge rx[21])
        if (!rx[21]) bv_c[68:53] <= 16'd0; else for (kb = 53; kb < 69; kb = kb + 1) bv_c[kb] <= btx_c[3] | btg_c[3];
    assign bv_o = bv_c;
    // INCAP calendar-contract diagnosis
    reg [74:0] dg_act; reg dg_go, dg_calv; reg [3:0] dg_sv, dg_sr, dg_si;
    wire [1:0] dg_cfg = dg_act[64:63];
    integer kd, ks;
    always @(posedge clk) begin
        dg_act <= ca_q; dg_go <= go_q; dg_calv <= cv_q;
        for (kd = 0; kd < 4; kd = kd + 1) begin dg_sv[kd] <= sv[kd]; dg_sr[kd] <= sr[kd]; dg_si[kd] <= si[kd]; end
    end
    // reset-value state (main: async reset by rst_c)
    always @(posedge clk or negedge rc[0]) begin
        if (!rc[0]) begin
            fault <= 0; a_v <= 0; a_v2 <= 0; a_tag <= 0; a_tag2 <= 0; a_ph <= 0;
            r0_v <= 0; ra_v <= 0; r1_v <= 0; r2_v <= 0; r3_v <= 0; hv <= 0;
        end else begin
            if (|act_hi_q) fault <= 1;
            if ((dg_act[71:68] & (dg_act[71:68] - 4'd1)) != 0) fault <= 1;
            if (dg_go && dg_sv[dg_act[1:0]]) fault <= 1;
            if (dg_go && !dg_calv) fault <= 1;
            if (dg_act[62] && (!dg_sv[dg_cfg] || !dg_sr[dg_cfg])) fault <= 1;
            if (dg_act[65] && (!dg_sv[dg_act[67:66]] || !dg_sr[dg_act[67:66]] || !dg_si[dg_act[67:66]])) fault <= 1;
            a_v <= go_q; a_tag <= accept_tag; a_v2 <= a_v; a_tag2 <= a_tag;
            if (go_q) a_ph <= iph_q;
            r0_v <= action[39]; ra_v <= r0_v; r1_v <= ra_v; r2_v <= r1_v; r3_v <= r2_v; hv <= r3_v;
        end
    end
    reg [PHW-1:0] cfg_ph; reg [2:0] cfg_np;
    always @* begin
        cfg_ph = '0; cfg_np = '0;
        for (ks = 0; ks < 4; ks = ks + 1) if (cfg_oh[ks]) begin cfg_ph = cfg_ph | s_ph[ks]; cfg_np = cfg_np | s_np[ks]; end
    end
    always @(posedge clk or negedge rc[1]) begin
        if (!rc[1]) begin
            p1_xs_v <= 0; p1_xb_v <= 0; p1_go <= 0; p1_gobf <= 0; p1_cfg <= 0; p1_tag <= 0; p1_ph <= 0; p1_np <= 0;
        end else begin
            p1_cfg <= action[62]; p1_go <= action[65];
            if (action[62]) begin p1_ph <= cfg_ph; p1_np <= cfg_np; end
            if (action[65]) begin p1_gobf <= s_pw0[launch_tag]; p1_tag <= launch_tag; end
            p1_xs_v <= hv && hw[0] && !h_fam; p1_xb_v <= hv && hw[0] && h_fam;
        end
    end
    always @(posedge clk or negedge rc[2]) begin
        if (!rc[2]) begin
            bt_xs_v <= 0; bt_xb_v <= 0; bt_go <= 0; bt_gobf <= 0; bt_cfg <= 0; bt_tag <= 0; bt_ph <= 0; bt_np <= 0;
        end else begin
            bt_xs_v <= p1_xs_v; bt_xb_v <= p1_xb_v;
            bt_go <= p1_go; bt_gobf <= p1_gobf; bt_cfg <= p1_cfg; bt_tag <= p1_tag; bt_ph <= p1_ph; bt_np <= p1_np;
        end
    end
    always @(posedge clk or negedge rc[3]) begin
        if (!rc[3]) begin
            for (ks = 0; ks < 4; ks = ks + 1) begin sv[ks] <= 0; sr[ks] <= 0; si[ks] <= 0; end
        end else begin
            if (go_q) begin sv[accept_tag] <= 1; sr[accept_tag] <= 0; si[accept_tag] <= 0; end
            if (phase_pin_valid) sr[phase_pin_tag] <= 1;
            for (ks = 0; ks < 4; ks = ks + 1)
                if (action[68 + ks]) begin sv[ks] <= 0; sr[ks] <= 0; si[ks] <= 0; end
            if (action[62]) for (ks = 0; ks < 4; ks = ks + 1) if (cfg_oh[ks]) si[ks] <= 1;
        end
    end
    // payload that holds while main's rst_c is low (main: assigned in the reset block without a reset value)
    always @(posedge clk) begin
        if (rh[0]) begin
            r0_a <= action[53:40]; r0_tag <= action[55:54]; r0_pos <= action[58:56];
            r0_fam <= action[59]; r0_lp <= action[60]; r0_lo <= action[61];
        end
        if (rh[1]) begin
            ra_tag <= r0_tag; ra_pos <= r0_pos; ra_fam <= r0_fam; ra_lp <= r0_lp; ra_lo <= r0_lo;
            r1_tag <= ra_tag; r1_pos <= ra_pos; r1_fam <= ra_fam; r1_lp <= ra_lp; r1_lo <= ra_lo;
            if (phase_pin_valid) s_pw0[phase_pin_tag] <= phase0_pin;
        end
        if (rh[2]) r2_w[11:0] <= r1_w[11:0];
        if (rx[0]) r2_w[23:12] <= r1_w[23:12];
        if (rh[3]) r2_w[35:24] <= r1_w[35:24];
        if (rx[1]) r2_w[47:36] <= r1_w[47:36];
        if (rh[4]) begin
            r2_tag <= r1_tag; r2_pos <= r1_pos; r2_fam <= r1_fam; r2_lp <= r1_lp; r2_lo <= r1_lo;
            r2_spar <= r1_spar; r2_nq <= r1_nq;
        end
        if (rh[5]) r2_m01 <= r1_m01;
        if (rx[2]) r2_m23 <= r1_m23;
        if (rh[6]) r2_b0 <= r1_blk0;
        if (rh[7]) r2_b1 <= r1_blk1;
        if (rh[8]) r2_hi[8:0]   <= (r1_spar ? 9'(KMAX/128) : 9'd0) + {1'b0, r1_w[15:8]};
        if (rx[3]) r2_hi[17:9]  <= (r1_spar ? 9'(KMAX/128) : 9'd0) + {1'b0, r1_w[23:16]};
        if (rh[9]) r2_hi[26:18] <= (r1_spar ? 9'(KMAX/128) : 9'd0) + {1'b0, r1_w[31:24]};
        if (rx[4]) r2_hi[35:27] <= (r1_spar ? 9'(KMAX/128) : 9'd0) + {1'b0, r1_w[39:32]};
        if (rh[10]) r3_w[11:0] <= r2_w[11:0];
        if (rx[5])  r3_w[23:12] <= r2_w[23:12];
        if (rh[11]) r3_w[35:24] <= r2_w[35:24];
        if (rx[6])  r3_w[47:36] <= r2_w[47:36];
        if (rh[12]) begin
            r3_tag <= r2_tag; r3_pos <= r2_pos; r3_fam <= r2_fam; r3_lp <= r2_lp; r3_lo <= r2_lo;
            r3_spar <= r2_spar; r3_nq <= r2_nq;
        end
        if (rh[13]) r3_umax <= r2_m23 > r2_m01 ? r2_m23 : r2_m01;
        if (rh[14]) r3_b0 <= r2_b0;
        if (rh[15]) r3_b1 <= r2_b1;
        if (rh[16]) r3_hi[8:0]   <= r2_hi[8:0];
        if (rx[7])  r3_hi[17:9]  <= r2_hi[17:9];
        if (rh[17]) r3_hi[26:18] <= r2_hi[26:18];
        if (rx[8])  r3_hi[35:27] <= r2_hi[35:27];
        if (rh[18]) he[EW-1 -: 12]  <= r3_e[EW-1 -: 12];
        if (rx[9])  he[EW-13 -: 12] <= r3_e[EW-13 -: 12];
        // he[EW-25:0] (116 b): rh[19] + rx[10..17], 13 b per enable copy
        if (rh[19]) he[12:0] <= r3_e[12:0];
        for (kd = 0; kd < 7; kd = kd + 1)
            if (rx[10 + kd]) he[13 + 13*kd +: 13] <= r3_e[13 + 13*kd +: 13];   // [103:13]
        if (rx[17]) he[EW-25:104] <= r3_e[EW-25:104];                           // [115:104]
    end
endmodule

// ===================================================================================================================== top
module ot_s81sl_xs4 (
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
    // ------------------------------------------------------------------ reset
    wire [3:0] rst_e; wire [53:0] rst_l; wire [38:0] rst_k; wire [23:0] rst_x;
    ot_s81sl_xs4_rst u_rst (.clk(clk), .rst_n_in(rst_n), .rst_e(rst_e), .rst_l(rst_l), .rst_k(rst_k), .rst_x(rst_x));
    // l2 region map: 0-5 issuer, 6-27 table groups, 28-29 write-leaf parity replicas, 30 faults / lane / exp,
    // 31-47 calendar, 48 window-open copies, 49-53 spare
    wire [16:0] rg_cal = rst_l[47:31];
    localparam integer NA = 21;     // capture copies per gather source

    // ================================================================== level A: capture (port bit -> <= 21 loads)
    wire       ga_v [0:2][0:NA-1];
    wire       ga_f [0:2][0:NA-1];
    wire [6:0] ga_g [0:2][0:NA-1];
    genvar gs, gc, gm, gj, ga, gb;
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_cs
        for (gc = 0; gc < NA; gc = gc + 1) begin : g_cc
            (* keep = "true" *) reg v;
            (* keep = "true" *) reg f;
            (* keep = "true" *) reg [6:0] g;
            always @(posedge clk or negedge rst_e[gs]) if (!rst_e[gs]) v <= 1'b0; else v <= g_v[gs];
            always @(posedge clk) begin f <= g_fam[gs]; g <= g_idx[7*gs +: 7]; end
            assign ga_v[gs][gc] = v; assign ga_f[gs][gc] = f; assign ga_g[gs][gc] = g;
        end
    end endgenerate
    reg [3071:0] gd_a, gd_b;
    always @(posedge clk) begin gd_a <= g_d; gd_b <= gd_a; end
    (* keep = "true" *) reg [1:0] isv_a;
    always @(posedge clk or negedge rst_e[3]) if (!rst_e[3]) isv_a <= 2'd0; else isv_a <= {2{is_v}};
    reg [44:0] ip_a; reg ow_a; reg [7:0] of_a; reg [27:0] rv_a;
    always @(posedge clk) begin
        ip_a <= {is_d[122:93], is_d[92], is_d[13:0]}; ow_a <= is_d[123]; of_a <= is_d[131:124]; rv_a <= is_d[159:132];
    end

    // ================================================================== issuer (main's fixed per-slice delay line)
    localparam integer PW = 45, ND = 8, NG = 8;
    reg [44:0] ip_b; reg ow_b; reg [7:0] of_b; reg rv_b; reg isv_b;
    always @(posedge clk) begin ip_b <= ip_a; ow_b <= ow_a; of_b <= of_a; rv_b <= |rv_a; end
    wire rs_i0 = rst_l[0], rs_i1 = rst_l[1], rs_i2 = rst_l[2], rs_i3 = rst_l[3], rs_i5 = rst_l[5];
    always @(posedge clk or negedge rs_i0) if (!rs_i0) isv_b <= 1'b0; else isv_b <= isv_a[1];
    reg [7:0]  off; reg [15:0] cyc; reg [2:0] dq_w; reg [3:0] dq_n; reg is_fault;
`ifdef OT_S81SL_XS_MUT_OFF
    wire [15:0] due = cyc + 16'(off) + 16'(off == 8'd0);
`else
    wire [15:0] due = cyc + 16'(off) + 16'd1;
`endif
    wire [2:0] dq_w_nx = dq_w + {2'd0, isv_b};
    // registered one-hot entry write enables, 2 copies per entry ({t, p} bits [30:0] / [60:31])
    wire [60:0] dqe [0:ND-1];
    wire [60:0] dq_in = {due, ip_b};
    genvar ge;
    generate for (ge = 0; ge < ND; ge = ge + 1) begin : g_dq
        (* keep = "true" *) reg [3:0] we;   // XG5: 4 copies x <= 16 b (2 x 31 b mapped to 60-62 loads)
        always @(posedge clk) we <= {4{isv_a[0] && dq_w_nx == 3'(ge)}};
        reg [60:0] w;
        always @(posedge clk) begin
            if (we[0]) w[15:0]  <= dq_in[15:0];
            if (we[1]) w[30:16] <= dq_in[30:16];
            if (we[2]) w[45:31] <= dq_in[45:31];
            if (we[3]) w[60:46] <= dq_in[60:46];
        end
        assign dqe[ge] = w;
    end endgenerate
    wire dq_nz = dq_n != 4'd0;
    // 5 read-pointer copies: one-hot rp, own time mux + pop, own payload field mux
    wire [4:0] pop; wire [44:0] pm [0:4];
    genvar gk;
    generate for (gk = 0; gk < 5; gk = gk + 1) begin : g_rp
        (* keep = "true" *) reg [7:0] rp;
        reg [15:0] t; reg [44:0] p;
        integer e;
        always @* begin
            t = 16'd0; p = 45'd0;
            for (e = 0; e < ND; e = e + 1) if (rp[e]) begin t = t | dqe[e][60:45]; p = p | dqe[e][44:0]; end
        end
        assign pop[gk] = dq_nz && t == cyc;
        assign pm[gk] = p;
        always @(posedge clk or negedge rst_l[1 + gk]) if (!rst_l[1 + gk]) rp <= 8'd1; else if (pop[gk]) rp <= {rp[6:0], rp[7]};
    end endgenerate
    reg o_go, o_prime, o_start, o_ff; reg [9:0] o_ph; reg [2:0] o_np; reg [11:0] o_base; reg [12:0] o_len;
    always @(posedge clk or negedge rs_i0) begin
        if (!rs_i0) begin
            off <= 8'd0; dq_w <= 3'd0; dq_n <= 4'd0; is_fault <= 1'b0;
            o_go <= 1'b0; o_prime <= 1'b0; o_start <= 1'b0; o_ff <= 1'b0;
        end else begin
            if (isv_b && ow_b) begin
                off <= of_b;
                if (dq_n != 0) is_fault <= 1'b1;
            end
            if (isv_b && rv_b) is_fault <= 1'b1;
            if (isv_b && dq_n == 4'(ND) && !pop[0]) is_fault <= 1'b1;
            if (isv_b) dq_w <= dq_w + 3'd1;
            dq_n <= dq_n + 4'(isv_b) - 4'(pop[0]);
            o_go <= pop[0] && pm[0][0];
            o_prime <= pop[0] && pm[0][15];
            o_start <= pop[0] && pm[0][16];
            if (pop[0]) o_ff <= pm[0][14];
        end
    end
    always @(posedge clk or negedge rs_i5) if (!rs_i5) cyc <= 16'd0; else cyc <= cyc + 16'd1;
    always @(posedge clk or negedge rs_i1)
        if (!rs_i1) begin o_ph <= 10'd0; o_np <= 3'd0; end
        else if (pop[1] && pm[1][0]) begin o_ph <= pm[1][10:1]; o_np <= pm[1][13:11]; end
    always @(posedge clk or negedge rs_i2)
        if (!rs_i2) o_base <= 12'd0; else if (pop[2] && (pm[2][15] || pm[2][16])) o_base <= pm[2][28:17];
    always @(posedge clk or negedge rs_i3)
        if (!rs_i3) o_len <= 13'd0; else if (pop[3] && (pm[3][15] || pm[3][16])) o_len <= pm[3][41:29];
    // window-open copies (gw, family, parity)
    (* keep = "true" *) reg [NG-1:0] o_gw, o_gwf, o_gwp;
    wire gw_en = pop[4] && pm[4][42];
    always @(posedge clk or negedge rst_l[48])
        if (!rst_l[48]) begin o_gw <= '0; o_gwf <= '0; o_gwp <= '0; end
        else begin
            o_gw <= {NG{gw_en}};
            if (gw_en) begin o_gwf <= {NG{pm[4][43]}}; o_gwp <= {NG{pm[4][44]}}; end
        end

    // ================================================================== ROMs
    wire [74:0] cal_action; wire cal_active, cal_primed, cal_fault;
    wire [11:0] cal_a; wire [71:0] cal_ra, cal_rt;
    `OT_S81SL_XS4_ROM("pq_calendar_action") u_cal_action (.clk(clk), .ce_in(1'b1), .addr_in(cal_a), .rd_out(cal_ra));
    `OT_S81SL_XS4_ROM("pq_calendar_time") u_cal_time (.clk(clk), .ce_in(1'b1), .addr_in(cal_a), .rd_out(cal_rt));
    ot_s81sl_xs4_cal u_cal_reader (.ck(clk), .rg(rg_cal), .prime(o_prime), .stage_start(o_start), .base(o_base),
        .length(o_len), .rom_addr(cal_a), .rom_action(cal_ra), .rom_time(cal_rt), .action(cal_action),
        .active(cal_active), .primed(cal_primed), .fault(cal_fault));
    wire cal_v = cal_primed || cal_active || (|cal_action);
    wire [71:0] ph_rd;
    `OT_S81SL_XS4_ROM("pq_phase0") u_phase0 (.clk(clk), .ce_in(1'b1), .addr_in({1'b0, o_ph, 1'b0}), .rd_out(ph_rd));
    // stream ROM bank select (ot_s81_pq_stream_rom4_sel function): address / ce from the action flops; bank one-hot
    // registered on the macro sample edge, 2 copies (24 response bits each)
    wire [13:0] sa = cal_action[53:40];
    wire [3:0]  sa_ce = 4'b0001 << sa[13:12];
    wire [71:0] st_rd [0:3];
    `OT_S81SL_XS4_ROM("pq_stream0") u_stream0 (.clk(clk), .ce_in(sa_ce[0]), .addr_in(sa[11:0]), .rd_out(st_rd[0]));
    `OT_S81SL_XS4_ROM("pq_stream1") u_stream1 (.clk(clk), .ce_in(sa_ce[1]), .addr_in(sa[11:0]), .rd_out(st_rd[1]));
    `OT_S81SL_XS4_ROM("pq_stream2") u_stream2 (.clk(clk), .ce_in(sa_ce[2]), .addr_in(sa[11:0]), .rd_out(st_rd[2]));
    `OT_S81SL_XS4_ROM("pq_stream3") u_stream3 (.clk(clk), .ce_in(sa_ce[3]), .addr_in(sa[11:0]), .rd_out(st_rd[3]));
    (* keep = "true" *) reg [3:0] bk0, bk1;
    always @(posedge clk) begin bk0 <= sa_ce; bk1 <= sa_ce; end
    reg [47:0] st_sq;
    integer kq;
    always @* begin
        st_sq = 48'd0;
        for (kq = 0; kq < 4; kq = kq + 1) begin
            if (bk0[kq]) st_sq[23:0] = st_sq[23:0] | st_rd[kq][23:0];
            if (bk1[kq]) st_sq[47:24] = st_sq[47:24] | st_rd[kq][47:24];
        end
    end

    // ================================================================== production stream path (native ctl copy)
    wire ctl_fault; wire [169:0] hq; wire [4:0] qc; wire [42:0] hb; wire bcs; wire [609:0] bc_hr; wire [68:0] bvc;
    ot_s81sl_xs4_ctl u_ctl (.clk(clk), .rc(rst_k[3:0]), .rh(rst_k[35:4]), .rb(rst_k[38:36]), .rx(rst_x), .calendar_v(cal_v),
        .calendar_action(cal_action), .go(o_go), .i_ph(o_ph), .i_np(o_np), .rom_gobf(ph_rd[0]), .rom_sq(st_sq),
        .hq_o(hq), .qc_o(qc), .hb_o(hb), .bc_o(bcs), .bc_hr_o(bc_hr), .bv_o(bvc), .fault(ctl_fault));

    // ================================================================== x buffer write side (level B -> macro pins)
    // gather source s, beat g, family f: level-B decodes from capture copy c of source s:
    //   c 0-7 write leaf of macro c, c 8-13 q set one-hots (16 beats each), c 14-18 BF set one-hots, c 19 exponent
    //   write leaf, c 20 range / duplicate faults.
    wire [255:0] mw_d [0:2][0:7], mw_m [0:2][0:7];
    wire [6:0]   mw_a [0:2][0:7];
    wire         mw_e [0:2][0:7];
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_w
        wire [1023:0] d = gd_b[1024*gs +: 1024];
        for (gm = 0; gm < 8; gm = gm + 1) begin : g_m
            localparam [2:0] M = gm;
            wire v = ga_v[gs][gm], f = ga_f[gs][gm]; wire [6:0] g = ga_g[gs][gm];
            wire gwx = o_gw[(3*gs + gm) % NG], gwf = o_gwf[(3*gs + gm) % NG], gwp = o_gwp[(3*gs + gm) % NG];
            // own buffer-parity replicas (main wpar_q / wpar_b) and their next values (the level-B address is
            // registered one edge before the macro samples it)
            (* keep = "true" *) reg wq, wb;
            wire wq_nx = (gwx && !gwf) ? gwp : wq, wb_nx = (gwx && gwf) ? gwp : wb;
            always @(posedge clk or negedge rst_l[28 + (8 * gs + gm) / 12])
                if (!rst_l[28 + (8 * gs + gm) / 12]) begin wq <= 1'b0; wb <= 1'b0; end else begin wq <= wq_nx; wb <= wb_nx; end
            reg we; reg [6:0] wa;
            always @(posedge clk) begin
                we <= v && (f || (g[2] == M[2] && g[0] == M[0]));
                wa <= f ? {wb_nx, g[6:1]} : {wq_nx, 6'd40 + {1'b0, g[6:3], g[1]}};
            end
            (* keep = "true" *) reg [3:0] mlo, mhi;
            (* keep = "true" *) reg [7:0] qm;
            always @(posedge clk) begin mlo <= {4{!f || !g[0]}}; mhi <= {4{!f || g[0]}}; qm <= {8{!f}}; end
            wire [7:0] rsel [0:7];
            for (gb = 0; gb < 8; gb = gb + 1) begin : g_r
                (* keep = "true" *) reg [7:0] r;
`ifdef OT_S81SL_XS4_MUT_WCOPY
                wire [2:0] bx = (gs == 1 && gm == 3) ? 3'(M - g[3:1] + 3'd1) : 3'(M - g[3:1]);
                always @(posedge clk) begin r <= {8{f && 3'(M - g[3:1]) == 3'(gb)}}; r[5] <= f && bx == 3'(gb); end
`else
                always @(posedge clk) r <= {8{f && 3'(M - g[3:1]) == 3'(gb)}};
`endif
                assign rsel[gb] = r;
            end
            // data: BF column b lane j = element 8 j + b of the beat (half rows; both halves carry it), q: block half
            reg [255:0] wd;
            integer k, b;
            always @* begin
                for (k = 0; k < 256; k = k + 1) begin
                    wd[k] = qm[k / 32] & (M[1] ? d[266 + k] : d[k]);
                    for (b = 0; b < 8; b = b + 1)
                        wd[k] = wd[k] | (rsel[b][k / 32] & d[16 * (8 * ((k % 128) / 16) + b) + (k % 16)]);
                end
            end
            assign mw_d[gs][gm] = wd;
            for (gj = 0; gj < 8; gj = gj + 1) begin : g_mk
                assign mw_m[gs][gm][32*gj +: 32] = {32{gj < 4 ? mlo[gj] : mhi[gj - 4]}};
            end
            assign mw_a[gs][gm] = wa; assign mw_e[gs][gm] = we;
        end
    end endgenerate
    // arrival-table set one-hots (no parity; the table groups apply theirs): q beats 0-95, BF beats 0-79
    wire [95:0] ohq [0:2]; wire [79:0] ohb [0:2];
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_oh
        for (gc = 0; gc < 6; gc = gc + 1) begin : g_q
            wire v = ga_v[gs][8 + gc], f = ga_f[gs][8 + gc]; wire [6:0] g = ga_g[gs][8 + gc];
            reg [15:0] o;
            integer i;
            always @(posedge clk) for (i = 0; i < 16; i = i + 1) o[i] <= v && !f && g == 7'(16 * gc + i);
            assign ohq[gs][16*gc +: 16] = o;
        end
        for (gc = 0; gc < 5; gc = gc + 1) begin : g_b
            wire v = ga_v[gs][14 + gc], f = ga_f[gs][14 + gc]; wire [6:0] g = ga_g[gs][14 + gc];
            reg [15:0] o;
            integer i;
            always @(posedge clk) for (i = 0; i < 16; i = i + 1) o[i] <= v && f && g == 7'(16 * gc + i);
            assign ohb[gs][16*gc +: 16] = o;
        end
    end endgenerate
    // arrival tables in 22 groups of 8 beats: valid (2 parities) + first-writer source, own parity replica and window
    // clear.  Main: clear first, then set (only if not yet valid), source written by the last setting source.
    wire [95:0] tqv [0:1]; wire [191:0] tqs [0:1]; wire [79:0] tbv [0:1]; wire [159:0] tbs [0:1];
    wire [2:0] hitq [0:11], hitb [0:9];
    generate for (gc = 0; gc < 22; gc = gc + 1) begin : g_tg
        localparam integer FB = gc >= 12 ? 1 : 0, G = gc >= 12 ? gc - 12 : gc;
        wire gwx = o_gw[gc % NG], gwf = o_gwf[gc % NG], gwp = o_gwp[gc % NG];
        (* keep = "true" *) reg wp, wpv;   // main wpar_q (FB 0) / wpar_b (FB 1): wpv for the valid sets, wp the rest
        (* keep = "true" *) reg wps;       // XG5: kept copy of wp for the s0 / s1 source writes (wp mapped to 39-50 loads)
`ifdef OT_S81SL_XS4_MUT_TPAR
        wire open_f = (gc == 5) ? 1'b0 : (gwx && gwf == FB[0]);
`else
        wire open_f = gwx && gwf == FB[0];
`endif
        reg [7:0] v0, v1; reg [15:0] s0, s1;
        wire [7:0] o0 = FB ? ohb[0][8*G +: 8] : ohq[0][8*G +: 8];
        wire [7:0] o1 = FB ? ohb[1][8*G +: 8] : ohq[1][8*G +: 8];
        wire [7:0] o2 = FB ? ohb[2][8*G +: 8] : ohq[2][8*G +: 8];
        wire [7:0] any = o0 | o1 | o2;
        wire [7:0] vc = wp ? v1 : v0;
        wire cl0 = open_f && !gwp, cl1 = open_f && gwp;
        always @(posedge clk or negedge rst_l[6 + gc]) begin
            if (!rst_l[6 + gc]) begin wp <= 1'b0; wpv <= 1'b0; wps <= 1'b0; v0 <= 8'd0; v1 <= 8'd0; end
            else begin
                if (open_f) begin wp <= gwp; wpv <= gwp; wps <= gwp; end
                v0 <= cl0 ? (any & {8{!wpv}} & ~v0) : (v0 | (any & {8{!wpv}}));
                v1 <= cl1 ? (any & {8{wpv}} & ~v1) : (v1 | (any & {8{wpv}}));
            end
        end
        integer i;
        always @(posedge clk)
            for (i = 0; i < 8; i = i + 1)
                if (!vc[i] && any[i]) begin
                    if (wps) s1[2*i +: 2] <= o2[i] ? 2'd2 : o1[i] ? 2'd1 : 2'd0;
                    else    s0[2*i +: 2] <= o2[i] ? 2'd2 : o1[i] ? 2'd1 : 2'd0;
                end
        wire [2:0] hit = {|(o2 & vc), |(o1 & vc), |(o0 & vc)};
        if (FB) begin : g_fb
            assign tbv[0][8*G +: 8] = v0; assign tbv[1][8*G +: 8] = v1;
            assign tbs[0][16*G +: 16] = s0; assign tbs[1][16*G +: 16] = s1;
            assign hitb[G] = hit;
        end else begin : g_fq
            assign tqv[0][8*G +: 8] = v0; assign tqv[1][8*G +: 8] = v1;
            assign tqs[0][16*G +: 16] = s0; assign tqs[1][16*G +: 16] = s1;
            assign hitq[G] = hit;
        end
    end endgenerate
    // exponent write leaf (copy 19): per source two SRAMs (beat bit 2), row {wpar_q, beat[6:3], beat[1:0]},
    // word {block 2 beat + 1, block 2 beat} exponents
    wire [1:0] ew [0:2]; wire [6:0] ea [0:2];
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_ew
        wire v = ga_v[gs][19], f = ga_f[gs][19]; wire [6:0] g = ga_g[gs][19];
        wire gwx = o_gw[(5 + gs) % NG], gwf = o_gwf[(5 + gs) % NG], gwp = o_gwp[(5 + gs) % NG];
        (* keep = "true" *) reg wq;
        wire wq_nx = (gwx && !gwf) ? gwp : wq;
        always @(posedge clk or negedge rst_l[30]) if (!rst_l[30]) wq <= 1'b0; else wq <= wq_nx;
        reg [1:0] e; reg [6:0] a;
        always @(posedge clk) begin
            e <= {v && !f && g < 7'd96 && g[2], v && !f && g < 7'd96 && !g[2]};
            a <= {wq_nx, g[6:3], g[1:0]};
        end
        assign ew[gs] = e; assign ea[gs] = a;
    end endgenerate
    // range / duplicate write faults (copy 20 of every source)
    reg [2:0] wrng; reg wdup;
    always @(posedge clk) begin
        wrng[0] <= ga_v[0][20] && (ga_f[0][20] ? ga_g[0][20] >= 7'd80 : ga_g[0][20] >= 7'd96);
        wrng[1] <= ga_v[1][20] && (ga_f[1][20] ? ga_g[1][20] >= 7'd80 : ga_g[1][20] >= 7'd96);
        wrng[2] <= ga_v[2][20] && (ga_f[2][20] ? ga_g[2][20] >= 7'd80 : ga_g[2][20] >= 7'd96);
        wdup <= (ga_v[0][20] && ga_v[1][20] && ga_f[0][20] == ga_f[1][20] && ga_g[0][20] == ga_g[1][20]) ||
                (ga_v[0][20] && ga_v[2][20] && ga_f[0][20] == ga_f[2][20] && ga_g[0][20] == ga_g[2][20]) ||
                (ga_v[1][20] && ga_v[2][20] && ga_f[1][20] == ga_f[2][20] && ga_g[1][20] == ga_g[2][20]);
    end
    reg [2:0] whit;
    integer kh;
    always @* begin
        whit = 3'd0;
        for (kh = 0; kh < 12; kh = kh + 1) whit = whit | hitq[kh];
        for (kh = 0; kh < 10; kh = kh + 1) whit = whit | hitb[kh];
    end
    reg wr_fault;
    always @(posedge clk or negedge rst_l[30])
        if (!rst_l[30]) wr_fault <= 1'b0; else if ((|wrng) || wdup || (|whit)) wr_fault <= 1'b1;

    // ================================================================== read side
    // ---- stage 1 (stream head + 1): q from head copies 0-3 (lookups q0 c0 / q0 c1 / q1 c0 / q1 c1), 4 (rest);
    //      BF from the BF head copy.  Lookup index = registered full one-hot line per (parity, beat).
    wire [15:0] hb0 [0:4], hb1 [0:4]; wire [1:0] hg [0:4];
    generate for (gc = 0; gc < 5; gc = gc + 1) begin : g_hqs
        assign {hb0[gc], hb1[gc], hg[gc]} = hq[34*gc +: 34];
    end endgenerate
    // q lookup copies: L = 0 q0 c0, 1 q0 c1, 2 q1 c0, 3 q1 c1 (q1 is looked up with q0's parity, as main)
    wire [191:0] qln [0:3]; wire [3:0] qms [0:3];
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_ql
        wire p0 = hb0[gc] >= 16'd192;
        wire [7:0] k0 = 8'(hb0[gc] - (p0 ? 16'd192 : 16'd0));
        wire p1 = hb1[gc] >= 16'd192;
        wire [7:0] k1 = 8'(hb1[gc] - (p1 ? 16'd192 : 16'd0));
        wire [7:0] k = gc < 2 ? k0 : k1;
        wire gate = (gc < 2 ? hg[gc][0] : hg[gc][1]) && qc[gc];
        (* keep = "true" *) reg [191:0] ln; (* keep = "true" *) reg [3:0] m;   // ln[96 parity + beat]
        // XG5: two-level predecode in a kept module (hi 12 x lo 16 one-hots): each term drives 16 / 12 line ANDs
        // (the flat 192-line decode mapped to 48-load shared products)
        wire [11:0] ohi; wire [15:0] olo;
        ot_s81sl_xs4_pdec u_pd (.p(p0), .k(k[7:1]), .hi(ohi), .lo(olo));
        integer x;
        always @(posedge clk) begin
            for (x = 0; x < 192; x = x + 1) ln[x] <= ohi[x / 16] && olo[x % 16];
            for (x = 0; x < 4; x = x + 1) m[x] <= gate && {k[0], k[1]} == 2'(x);
        end
        assign qln[gc] = ln; assign qms[gc] = m;
    end endgenerate
    // rest copy (4): read-port rows / enables, exponent rows / halves, fault gates
    wire p0r = hb0[4] >= 16'd192, p1r = hb1[4] >= 16'd192;
    wire [7:0] k0r = 8'(hb0[4] - (p0r ? 16'd192 : 16'd0)), k1r = 8'(hb1[4] - (p1r ? 16'd192 : 16'd0));
    wire g0r = hg[4][0] && qc[4], g1r = hg[4][1] && qc[4];
    reg [6:0] qrow; reg [3:0] mq0r, mq1r; reg [6:0] er0a, er1a; reg er0ce, er1ce; reg [1:0] eg0, eg1;
    reg qg0f, qg1f, qbad;
    integer x4;
    always @(posedge clk) begin
        qrow <= {p0r, 6'd40 + {1'b0, k0r[7:4], k0r[2]}};
        for (x4 = 0; x4 < 4; x4 = x4 + 1) begin
            mq0r[x4] <= g0r && {k0r[0], k0r[1]} == 2'(x4);
            mq1r[x4] <= g1r && {k1r[0], k1r[1]} == 2'(x4);
        end
        er0a <= {p0r, k0r[7:4], k0r[2:1]};
        er1a <= {p1r, k1r[7:4], k1r[2:1]};
        er0ce <= g0r; er1ce <= g1r;
        eg0 <= {g0r && k0r[0], g0r && !k0r[0]};
`ifdef OT_S81SL_XS4_MUT_EXP
        eg1 <= {g1r && !k1r[0], g1r && k1r[0]};
`else
        eg1 <= {g1r && k1r[0], g1r && !k1r[0]};
`endif
        qg0f <= g0r; qg1f <= g1r;
        qbad <= (qc[4] && hg[4][0] && hb0[4] >= 16'd384) || (qc[4] && hg[4][1] && hb1[4] >= 16'd384) ||
                (qc[4] && hg[4][0] && hg[4][1] && p0r != p1r);
    end
    // BF groups k: lookup copies c (hi: parity x bu[5:3], lo: bu[2:0]), mac one-hots (sel c0 / c1, read port)
    wire [35:0] hhi = hb[42:7]; wire [3:0] hwb = hb[6:3]; wire [2:0] hwm = hb[2:0];
    wire [79:0] bln1 [0:3][0:1]; wire [7:0] bms [0:3][0:1]; wire [7:0] bmr [0:3];
    wire [6:0] brw [0:3]; wire [3:0] bbad_k, bgf;
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_bl
        wire [8:0] h = hhi[9*gc +: 9];
        wire par = h >= 9'd48;
        wire [5:0] bu = 6'(h - (par ? 9'd48 : 9'd0));
        wire [2:0] mac = 3'(hwm + 3'(bu));
        wire gate = hwb[gc] && bcs;
        (* keep = "true" *) reg [79:0] ln0, ln1;   // [40 parity + bu]
        (* keep = "true" *) reg [7:0] ms0, ms1, mr;
        reg [6:0] rw; reg bb, gf;
        integer x;
        always @(posedge clk) begin
            for (x = 0; x < 80; x = x + 1) begin
                ln0[x] <= (par == (x >= 40)) && bu == 6'(x % 40);
                ln1[x] <= (par == (x >= 40)) && bu == 6'(x % 40);
            end
            for (x = 0; x < 8; x = x + 1) begin
                ms0[x] <= gate && mac == 3'(x); ms1[x] <= gate && mac == 3'(x); mr[x] <= gate && mac == 3'(x);
            end
            rw <= {par, bu};
            bb <= gate && (h >= 9'd96 || (par ? h - 9'd48 : h) >= 9'd40);
            gf <= gate;
        end
        assign bln1[gc][0] = ln0; assign bln1[gc][1] = ln1;
        assign bms[gc][0] = ms0; assign bms[gc][1] = ms1; assign bmr[gc] = mr;
        assign brw[gc] = rw; assign bbad_k[gc] = bb; assign bgf[gc] = gf;
    end endgenerate
    // ---- macro read ports (sampled at stage 2), shared by the three source banks
    wire [6:0] mr_a [0:7]; wire mr_e [0:7];
    generate for (gm = 0; gm < 8; gm = gm + 1) begin : g_r
        wire [3:0] hit = {bmr[3][gm], bmr[2][gm], bmr[1][gm], bmr[0][gm]};
        wire [6:0] brow = hit[0] ? brw[0] : hit[1] ? brw[1] : hit[2] ? brw[2] : brw[3];
        wire qhit = gm < 4 ? mq0r[gm % 4] : mq1r[gm % 4];
        assign mr_e[gm] = qhit || (|hit);
        assign mr_a[gm] = (|hit) ? brow : qrow;
    end endgenerate
    // the macros
    wire [255:0] mrd [0:2][0:7];
    wire [63:0]  erd [0:2][0:1];
    generate for (gs = 0; gs < 3; gs = gs + 1) begin : g_bank
        for (gm = 0; gm < 8; gm = gm + 1) begin : g_mac
            ot_sram_1r1w_128x256_m1_r2c2 u_mem (
                .clk(clk), .r_ce_in(mr_e[gm]), .r_addr_in(mr_a[gm]), .rd_out(mrd[gs][gm]),
                .w_ce_in(mw_e[gs][gm]), .w_addr_in(mw_a[gs][gm]), .wd_in(mw_d[gs][gm]), .w_mask_in(mw_m[gs][gm]),
                .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
        for (gc = 0; gc < 2; gc = gc + 1) begin : g_ex
            ot_sram_1r1w2c_128x64_m1 u_em (
                .wclk(clk), .rclk(clk), .r_ce_in(gc == 0 ? er0ce : er1ce), .r_addr_in(gc == 0 ? er0a : er1a),
                .rd_out(erd[gs][gc]), .w_ce_in(ew[gs][gc]), .w_addr_in(ea[gs]),
                .wd_in({44'd0, gd_b[1024*gs + 522 +: 10], gd_b[1024*gs + 256 +: 10]}),
                .w_mask_in({44'd0, 20'hfffff}));
        end
    end endgenerate
    // ---- stage 2: table lookups (one-hot index lines) -> registered one-hot read-mux lines
    // q lookups L: v, s
    wire qv [0:3]; wire [1:0] qs [0:3];
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_qk
        reg v; reg [1:0] s; integer x;
        always @* begin
            v = 1'b0; s = 2'd0;
            for (x = 0; x < 192; x = x + 1)
                if (qln[gc][x]) begin v = v | tqv[x / 96][x % 96]; s = s | tqs[x / 96][2 * (x % 96) +: 2]; end
        end
        assign qv[gc] = v; assign qs[gc] = s;
    end endgenerate
    // BF lookups (group k, copy c): lo entry 2 bu, hi entry 2 bu + 1
    wire bvl [0:3][0:1], bvh [0:3][0:1]; wire [1:0] bsl [0:3][0:1], bsh [0:3][0:1];
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_bk
        for (gj = 0; gj < 2; gj = gj + 1) begin : g_c
            reg vl, vh; reg [1:0] sl, sh; integer x;
            always @* begin
                vl = 1'b0; vh = 1'b0; sl = 2'd0; sh = 2'd0;
                for (x = 0; x < 80; x = x + 1)
                    if (bln1[gc][gj][x]) begin
                        vl = vl | tbv[x / 40][2 * (x % 40)];     vh = vh | tbv[x / 40][2 * (x % 40) + 1];
                        sl = sl | tbs[x / 40][4 * (x % 40) +: 2]; sh = sh | tbs[x / 40][4 * (x % 40) + 2 +: 2];
                    end
            end
            assign bvl[gc][gj] = vl; assign bvh[gc][gj] = vh; assign bsl[gc][gj] = sl; assign bsh[gc][gj] = sh;
        end
    end endgenerate
    // one-hot source decodes
`ifdef OT_S81SL_XS_MUT_BANK
    function automatic [2:0] soh_q0(input [1:0] s); soh_q0 = 3'b001 << (s == 2'd2 ? 2'd0 : s + 2'd1); endfunction
`else
    function automatic [2:0] soh_q0(input [1:0] s); soh_q0 = 3'b001 << s; endfunction
`endif
    function automatic [2:0] soh(input [1:0] s); soh = 3'b001 << s; endfunction
    wire [2:0] sq0 [0:1], sq1 [0:1], sbl [0:3][0:1], sbh [0:3][0:1];
    generate for (gc = 0; gc < 2; gc = gc + 1) begin : g_soh
        assign sq0[gc] = soh_q0(qs[gc]); assign sq1[gc] = soh(qs[2 + gc]);
        for (gj = 0; gj < 4; gj = gj + 1) begin : g_b
            assign sbl[gj][gc] = soh(bsl[gj][gc]); assign sbh[gj][gc] = soh(bsh[gj][gc]);
        end
    end endgenerate
    // registered lines: q0 / q1 slice j (32 b), source a, macro b (q0: macro b, q1: macro 4 + b)
    (* keep = "true" *) reg [95:0] ql0, ql1;   // [12 j + 4 a + b]
    (* keep = "true" *) reg [5:0]  es0, es1;   // [2 a + h]
    (* keep = "true" *) reg [767:0] bln;       // [192 k + 24 j + 8 a + m]
    integer j2, a2, b2, k2;
    always @(posedge clk) begin
        for (j2 = 0; j2 < 8; j2 = j2 + 1) for (a2 = 0; a2 < 3; a2 = a2 + 1) for (b2 = 0; b2 < 4; b2 = b2 + 1) begin
            ql0[12 * j2 + 4 * a2 + b2] <= sq0[j2 / 4][a2] && qms[j2 / 4][b2];
            ql1[12 * j2 + 4 * a2 + b2] <= sq1[j2 / 4][a2] && qms[2 + j2 / 4][b2];
        end
        for (a2 = 0; a2 < 3; a2 = a2 + 1) for (b2 = 0; b2 < 2; b2 = b2 + 1) begin
            es0[2 * a2 + b2] <= sq0[0][a2] && eg0[b2];
            es1[2 * a2 + b2] <= sq1[0][a2] && eg1[b2];
        end
        for (k2 = 0; k2 < 4; k2 = k2 + 1) for (j2 = 0; j2 < 8; j2 = j2 + 1)
            for (a2 = 0; a2 < 3; a2 = a2 + 1) for (b2 = 0; b2 < 8; b2 = b2 + 1)
                bln[192 * k2 + 24 * j2 + 8 * a2 + b2] <=
                    (j2 < 4 ? sbl[k2][(j2 / 2) % 2][a2] : sbh[k2][(j2 / 2) % 2][a2]) && bms[k2][(j2 / 2) % 2][b2];
    end
    // read faults (stage 2)
    reg rd_fault; reg conf; integer kc, kc2, mc;
    always @* begin
        conf = 1'b0;
        for (mc = 0; mc < 8; mc = mc + 1) for (kc = 0; kc < 4; kc = kc + 1) for (kc2 = 0; kc2 < kc; kc2 = kc2 + 1)
            if (bmr[kc][mc] && bmr[kc2][mc]) conf = 1'b1;
    end
    always @(posedge clk or negedge rst_l[30]) begin
        if (!rst_l[30]) rd_fault <= 1'b0;
        else begin
            if ((qg0f && !qv[0]) || (qg1f && !qv[2]) || qbad || (|bbad_k) || conf) rd_fault <= 1'b1;
            for (kc = 0; kc < 4; kc = kc + 1) if (bgf[kc] && (!bvl[kc][0] || !bvh[kc][0])) rd_fault <= 1'b1;
        end
    end
    // ---- stage 3: output registers (AND-OR of the registered lines)
    reg [255:0] hq0, hq1; reg [9:0] he0, he1; reg [1023:0] bt_d;
    integer j3, i3, a3, b3, k3; reg acc0, acc1;
    always @(posedge clk) begin
        for (j3 = 0; j3 < 8; j3 = j3 + 1) for (i3 = 0; i3 < 32; i3 = i3 + 1) begin
            acc0 = 1'b0; acc1 = 1'b0;
            for (a3 = 0; a3 < 3; a3 = a3 + 1) for (b3 = 0; b3 < 4; b3 = b3 + 1) begin
                acc0 = acc0 | (ql0[12 * j3 + 4 * a3 + b3] & mrd[a3][b3][32 * j3 + i3]);
                acc1 = acc1 | (ql1[12 * j3 + 4 * a3 + b3] & mrd[a3][4 + b3][32 * j3 + i3]);
            end
            hq0[32 * j3 + i3] <= acc0; hq1[32 * j3 + i3] <= acc1;
        end
        for (i3 = 0; i3 < 10; i3 = i3 + 1) begin
            acc0 = 1'b0; acc1 = 1'b0;
            for (a3 = 0; a3 < 3; a3 = a3 + 1) for (b3 = 0; b3 < 2; b3 = b3 + 1) begin
                acc0 = acc0 | (es0[2 * a3 + b3] & erd[a3][0][10 * b3 + i3]);
                acc1 = acc1 | (es1[2 * a3 + b3] & erd[a3][1][10 * b3 + i3]);
            end
            he0[i3] <= acc0; he1[i3] <= acc1;
        end
        for (k3 = 0; k3 < 4; k3 = k3 + 1) for (j3 = 0; j3 < 8; j3 = j3 + 1) for (i3 = 0; i3 < 32; i3 = i3 + 1) begin
            acc0 = 1'b0;
            for (a3 = 0; a3 < 3; a3 = a3 + 1) for (b3 = 0; b3 < 8; b3 = b3 + 1)
                acc0 = acc0 | (bln[192 * k3 + 24 * j3 + 8 * a3 + b3] & mrd[a3][b3][32 * j3 + i3]);
            bt_d[256 * k3 + 32 * j3 + i3] <= acc0;
        end
    end

    // ================================================================== frame word: f_bus -> lane (dsfd_pq_lx STATIC_X2)
    wire [1633:0] f_bus;
`ifdef OT_S81SL_XS_MUT_QSWAP
    assign f_bus = {bc_hr[609:578], hq1, he0, hq0, he1, bc_hr[45:0], bt_d};
`else
    assign f_bus = {bc_hr[609:578], hq0, he0, hq1, he1, bc_hr[45:0], bt_d};
`endif
    wire        l_cfg = f_bus[1633]; wire [9:0] l_ph = f_bus[1632:1623]; wire [2:0] l_np = f_bus[1622:1620];
    wire        l_go = f_bus[1619]; wire l_qv = f_bus[1615]; wire [7:0] l_p = f_bus[1614:1607];
    wire [2:0]  l_qb = f_bus[1606:1604]; wire [1:0] l_sv = f_bus[1603:1602];
    wire [255:0] l_q0 = f_bus[1601:1346]; wire [9:0] l_e0 = f_bus[1345:1336];
    wire [255:0] l_q1 = f_bus[1335:1080]; wire [9:0] l_e1 = f_bus[1079:1070]; wire [2:0] l_qp = f_bus[1069:1067];
    wire [282:0] l_x0 = {l_qv, l_sv, l_qp, l_p, l_qb, l_e0, l_q0};
    wire [265:0] l_x1 = {l_e1, l_q1};
    wire [14:0]  l_cc = {l_np, l_ph, l_cfg, l_go};
    wire [1067:0] l_xb = {f_bus[1023:0], f_bus[1055:1024], f_bus[1059:1056], f_bus[1062:1060], f_bus[1063],
                          f_bus[1066:1064], f_bus[1618]};
    wire collision = (f_bus[1063] && (l_qv || l_go || l_cfg)) || (f_bus[1618] && l_qv);
    wire [1100:0] word_b = {l_xb[535:0], l_cc, l_xb[1067:802], 17'd0, l_xb[801:536], 1'b1};   // bv = 1
    wire [1100:0] word_q = {536'd0, l_cc, l_x1, l_x0, l_qv | l_go | l_cfg};                    // bv = 0
    reg [1100:0] xw_l;
    integer kw;
    always @(posedge clk) for (kw = 0; kw < 1101; kw = kw + 1) xw_l[kw] <= bvc[kw / 16] ? word_b[kw] : word_q[kw];
    reg collision_fault, lx_fault;
    always @(posedge clk or negedge rst_l[30])
        if (!rst_l[30]) begin collision_fault <= 1'b0; lx_fault <= 1'b0; end
        else begin
            if (collision) collision_fault <= 1'b1;
            lx_fault <= o_ff | collision | collision_fault;
        end
    reg [1100:0] xw_q;
    always @(posedge clk) xw_q <= xw_l;
    assign xw_d = xw_q;
    assign xw_v = xw_q[0];

    // ================================================================== sticky fault (registered output)
    always @(posedge clk or negedge rst_l[30])
        if (!rst_l[30]) fault <= 1'b0;
        else if (is_fault || cal_fault || ctl_fault || wr_fault || rd_fault || lx_fault) fault <= 1'b1;
endmodule
`undef OT_S81SL_XS4_ROM
