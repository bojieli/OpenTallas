`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-SLICE / xs (2026-10-17): ot_s81sl_xs_ctl = the production static PQ stream controller, pruned to its stream path.
//
// Source: rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_state_phw10.sv (pin-capture layer) over ot_s81_pq_ctl_static_native.sv,
// resolved for the canonical produced profile (OT_PQ_CTL_STATIC + OT_PQ_CTL_STATE_PINS + OT_PQ_CTL_INCAP +
// OT_PQ_AQ_PIN_LAUNCH + OT_PQ_CTL_CALCAP).  Every kept statement is the production text (the same registers, the same
// edges), so the broadcast word bc_hr_o and the stream head (hw / h_b0 / h_b1 / h_hi / q_consume / b_consume) are the
// production values on the production edges.  The lockstep bench (tools/s81_slice/xs_bench.py) compares the composed
// frame words against the unmodified production core bit for bit.
//
// DROPPED (they do not exist in a DV slice, or are not part of the stream):
//   VM load      x_re, x_addr, x_rv (+ its INCAP capture): x arrives by the ring all-gather into the xs x buffer.
//   act-quant    aq_vin, aqf, aqi_o (+ the AQL-2 metadata delays): the owning slice's vq quantises before the ring.
//   BF write     ba_v_o, ba_wv_o, ba_blk_o: the BF16 family arrives rounded (vq) and is written by the xs buffer.
//   returns      ga_i, q2f_i, mdr_o and the per-tag return configuration (s_xb/s_ob/s_xps/s_ops/s_fm/s_rs, iss_tag,
//                g_md/g_mdr*), the row-count chain (gb/gp/rc/rows_seen, s_tq/s_tm/s_tot) and its retire check: the
//                128-region return counting.  In the slice the capture root (ot_s81sl_cap) owns the returns.
//                Retirement itself is kept: a calendar retire still frees its tag slot on the fixed edge.
//   status       ready, idle, phase_cycles, ev_go/ev_end/ev_tag, stream_end_v/tag: issuer status (t_iss) telemetry;
//                no slice consumer (the xr ctl tree carries no PQ status).
//   phase word 1 rom_pq1 (s_rs = rsplit): return configuration only.  The xs holds phase ROM 0 alone.
//   phase word 0 bits [63:1] (K, nbeat, sbase, rows, fmt): only s_pw[0] (gobf) reaches the stream; the rest fed the
//                count chain / return configuration.  Only bit 0 enters this leaf.
//   faults       the INCAP fault-cause inputs of VM/AQ/returns and the retire count check; every R-independent
//                calendar-contract diagnosis is kept (reserved action bits, multiple retire, GO without calendar,
//                GO on a live tag, cfg / launch on a slot that is not loaded).
// The pruned leaf has no tied functional input: every input port is used.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xs_ctl (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          calendar_v,
    input  wire [74:0]   calendar_action,
    input  wire          go,
    input  wire [9:0]    i_ph,
    input  wire [2:0]    i_np,
    input  wire          rom_gobf,          // phase ROM 0 rd_out[0] (s_pw[0])
    input  wire [47:0]   rom_sq,            // stream ROM word (two-cycle ROM: the macro + ot_s81_pq_stream_rom4_sel)
    output wire          q_consume,
    output wire          b_consume,
    output wire [47:0]   hw_o,
    output wire [35:0]   h_hi_o,
    output wire [15:0]   h_b0_o,
    output wire [15:0]   h_b1_o,
    output wire [609:0]  bc_hr_o,
    output reg           fault
);
    localparam integer PHW = 10, SAW = 14, KMAX = 6144, NBLK = 192, BW = 1634;
    // ------------------------------------------------------------------ ot_s81_pq_ctl_state_phw10 (CALCAP) pin layer
    wire state_rst_n;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_pin_reset
        (.clk(clk), .rst_n_in(rst_n), .rst_n(state_rst_n));
    reg cv_q, go_q; reg [74:0] ca_q; reg [9:0] iph_q; reg [2:0] inp_q;
    always @(posedge clk) begin
        cv_q <= calendar_v; ca_q <= calendar_action; iph_q <= i_ph; inp_q <= i_np; go_q <= go;
    end
    // ------------------------------------------------------------------ ot_s81_pq_ctl_static_native (INCAP + CALCAP)
    // reset relay: production REGIONS 4 (main / AQ metadata / count tree / bc+accept); AQ metadata and count regions
    // are dropped with their logic.
    // S81-XG3 (10-19): a third region for the p1 / bt broadcast-header pipeline (gate xgr: rst_c drove 585 loads);
    // all regions release on the same edge, so the function is unchanged.
    wire [2:0] rst_cv;
    ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr
        (.clk(clk), .rst_n_in(state_rst_n), .rst_n(rst_cv));
    wire rst_c = rst_cv[0], rst_bc = rst_cv[1], rst_p = rst_cv[2];
    reg [1:0] act_hi_q;
    always @(posedge clk) act_hi_q <= {2{cv_q}} & ca_q[74:73];
    wire [74:0] action = cv_q ? ca_q : 75'd0;
    wire [1:0]  accept_tag = action[1:0];
    wire [1:0]  config_tag = action[64:63], launch_tag = action[67:66];
    reg sv [0:3], sr [0:3], si [0:3];
    reg [PHW-1:0] s_ph [0:3];
    reg [2:0]     s_np [0:3];
    reg           s_pw0 [0:3];             // s_pw[tag][0] (gobf)
    reg           a_v, a_v2;
    reg [1:0]     a_tag, a_tag2;
    reg [PHW-1:0] a_ph;
    reg [2:0]     a_np;
    wire [3:0]    a_oh_d = go_q ? (4'b0001 << accept_tag) : 4'b0000;
    wire [3:0]    a_oh;
    ot_v41_kreg #(.W(4), .AR(1)) u_aoh1 (.clk(clk), .arst_n(rst_bc), .d(a_oh_d), .q(a_oh));
    always @(posedge clk) a_np <= inp_q;
    integer ka;
    always @(posedge clk)
        for (ka = 0; ka < 4; ka = ka + 1)
            if (a_oh[ka]) begin s_ph[ka] <= a_ph; s_np[ka] <= a_np; end
    // CALCAP c4: the phase-ROM response at the leaf pins; the tagged store one edge later
    reg phase0_pin;
    reg phase_pin_valid;
    reg [1:0] phase_pin_tag;
    always @(posedge clk) begin
        phase0_pin <= rom_gobf;
        phase_pin_tag <= a_tag2;
    end
    always @(posedge clk or negedge rst_c)
        if (!rst_c) phase_pin_valid <= 1'b0;
        else phase_pin_valid <= a_v2;
    wire phase_store_valid = phase_pin_valid;
    wire [1:0] phase_store_tag = phase_pin_tag;

    // R0: registered ROM address + the word's attributes; RA: the macro's own pipeline register; R1: the ROM word
    reg           r0_v, r0_lp, r0_lo, r0_fam;
    reg [1:0]     r0_tag;
    reg [2:0]     r0_pos;
    reg [SAW-1:0] r0_a;
    reg           ra_v, ra_lp, ra_lo, ra_fam;
    reg [1:0]     ra_tag;
    reg [2:0]     ra_pos;
    wire [47:0] st_q = rom_sq;
    reg           r1_v, r1_lp, r1_lo, r1_fam;
    reg [1:0]     r1_tag;
    reg [2:0]     r1_pos;
    reg [47:0]    r1_w;
    always @(posedge clk) r1_w <= st_q;     // CALCAP c4 direct ROM capture
    // R2: derived fields
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
    wire [9:0]  r1_nq;
    ot_v41_inc #(.W(10)) u_nq (.a({r1_u[5:0], r1_sv[1], r1_b}), .inc(1'b1), .y(r1_nq), .co());
    wire [15:0] r1_blk0 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b0, r1_b};
    wire [15:0] r1_blk1 = (r1_spar ? 16'(NBLK) : 16'd0) + {5'd0, r1_u, 1'b1, r1_b};
    reg           r2_v, r2_lp, r2_lo, r2_fam, r2_spar;
    reg [1:0]     r2_tag;
    reg [2:0]     r2_pos;
    reg [47:0]    r2_w;
    reg [9:0]     r2_nq;
    reg [7:0]     r2_m01, r2_m23;
    reg [15:0]    r2_b0, r2_b1;
    reg [35:0]    r2_hi;
    reg           r3_v, r3_lp, r3_lo, r3_fam, r3_spar;
    reg [1:0]     r3_tag;
    reg [2:0]     r3_pos;
    reg [47:0]    r3_w;
    reg [9:0]     r3_nq;
    reg [7:0]     r3_umax;
    reg [15:0]    r3_b0, r3_b1;
    reg [35:0]    r3_hi;
    wire [7:0]    r3_nb;
    ot_v41_inc #(.W(8)) u_nb (.a(r3_umax), .inc(1'b1), .y(r3_nb), .co());
    // an entry: {w 48, need 15, spar, lp, lo, fam, tag 2, pos 3, b0 16, b1 16, hi 36}
    localparam integer EW = 48 + 15 + 4 + 2 + 3 + 16 + 16 + 36;
    wire [EW-1:0] r3_e = {r3_w, r3_fam ? {r3_nb, 7'd0} : {r3_nq, 5'd0}, r3_spar, r3_lp, r3_lo, r3_fam, r3_tag, r3_pos,
                          r3_b0, r3_b1, r3_hi};
    reg [EW-1:0] he; reg hv;
    wire [47:0] hw = he[EW-1 -: 48];
    wire        h_fam = he[EW-67];
    wire [2:0]  h_pos = he[EW-70 -: 3];
    // CALCAP: q/b_consume launch from their own flops, loaded from r3 on the edge that loads he/hv
    reg qc_q, bc_q;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) begin qc_q <= 1'b0; bc_q <= 1'b0; end
        else begin qc_q <= r3_v && r3_e[EW-48] && !r3_e[EW-67]; bc_q <= r3_v && r3_e[EW-48] && r3_e[EW-67]; end
    assign q_consume = qc_q; assign b_consume = bc_q;
    assign hw_o = hw; assign h_hi_o = he[35:0]; assign h_b0_o = he[EW-73 -: 16]; assign h_b1_o = he[EW-89 -: 16];
    reg         p1_xs_v, p1_xb_v, p1_go, p1_gobf, p1_cfg;
    reg [7:0]   p1_p;
    reg [2:0]   p1_b, p1_pos, p1_np;
    reg [1:0]   p1_sv, p1_tag;
    reg [3:0]   p1_bsv;
    reg [31:0]  p1_u;
    reg [PHW-1:0] p1_ph;
    reg         bt_xs_v, bt_xb_v;
    reg [7:0]   bt_p;
    reg [2:0]   bt_b;
    reg [1:0]   bt_sv;
    wire [255:0] bt_q0 = '0, bt_q1 = '0;  // the x data fields are spliced in by the parent (xs buffer)
    wire [9:0]   bt_e0 = '0, bt_e1 = '0;
    reg [3:0]   bt_bsv;
    reg [31:0]  bt_u;
    reg         bt_go, bt_gobf, bt_cfg;
    reg [1:0]   bt_tag;
    reg [2:0]   bt_np, bt_pos;
    reg [PHW-1:0] bt_ph;
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
    always @(posedge clk or negedge rst_bc)
        if (!rst_bc) bc_hc <= '0; else bc_hc <= {bc_h[BW-1025 -: BRT], bc_h[39]};
    reg  [BW-1025:0] bc_hr;
    always @* begin bc_hr = bc_hd; bc_hr[BW-1025 -: BRT] = bc_hc[BRT:1]; bc_hr[39] = bc_hc[0]; end
    assign bc_hr_o = bc_hr;

    // INCAP calendar-contract diagnosis, one edge after the event (never gates an event)
    reg [74:0] dg_act; reg dg_go, dg_calv; reg [3:0] dg_sv, dg_sr, dg_si;
    wire [1:0] dg_cfg = dg_act[64:63];
    integer kd, ks;
    always @(posedge clk) begin
        dg_act <= cv_q ? ca_q : 75'd0; dg_go <= go_q; dg_calv <= cv_q;
        for (kd = 0; kd < 4; kd = kd + 1) begin dg_sv[kd] <= sv[kd]; dg_sr[kd] <= sr[kd]; dg_si[kd] <= si[kd]; end
    end
    always @(posedge clk or negedge rst_c) begin
        if (!rst_c) begin
            fault <= 0;
            a_v <= 0; a_v2 <= 0; a_tag <= 0; a_tag2 <= 0; a_ph <= 0;
            r0_v <= 0; ra_v <= 0; r1_v <= 0; r2_v <= 0; r3_v <= 0; hv <= 0;
            for (ks = 0; ks < 4; ks = ks + 1) begin sv[ks] <= 0; sr[ks] <= 0; si[ks] <= 0; end
        end else begin
            if (|act_hi_q) fault <= 1;
            if ((dg_act[71:68] & (dg_act[71:68] - 4'd1)) != 0) fault <= 1;
            if (dg_go && dg_sv[dg_act[1:0]]) fault <= 1;
            if (dg_go && !dg_calv) fault <= 1;
            if (dg_act[62] && (!dg_sv[dg_cfg] || !dg_sr[dg_cfg])) fault <= 1;
            if (dg_act[65] && (!dg_sv[dg_act[67:66]] || !dg_sr[dg_act[67:66]] || !dg_si[dg_act[67:66]])) fault <= 1;
            a_v <= go_q; a_tag <= accept_tag; a_v2 <= a_v; a_tag2 <= a_tag;
            if (go_q) begin sv[accept_tag] <= 1; sr[accept_tag] <= 0; si[accept_tag] <= 0; a_ph <= iph_q; end
            if (phase_store_valid) begin s_pw0[phase_store_tag] <= phase0_pin; sr[phase_store_tag] <= 1; end
            for (ks = 0; ks < 4; ks = ks + 1)
                if (action[68 + ks]) begin sv[ks] <= 0; sr[ks] <= 0; si[ks] <= 0; end
            if (action[62]) si[config_tag] <= 1;
            r0_v <= action[39]; r0_a <= action[53:40]; r0_tag <= action[55:54]; r0_pos <= action[58:56];
            r0_fam <= action[59]; r0_lp <= action[60]; r0_lo <= action[61];
            ra_v <= r0_v; ra_tag <= r0_tag; ra_pos <= r0_pos; ra_fam <= r0_fam; ra_lp <= r0_lp; ra_lo <= r0_lo;
            r1_v <= ra_v;
            r1_tag <= ra_tag; r1_pos <= ra_pos; r1_fam <= ra_fam; r1_lp <= ra_lp; r1_lo <= ra_lo;
            r2_v <= r1_v; r2_w <= r1_w; r2_tag <= r1_tag; r2_pos <= r1_pos; r2_fam <= r1_fam; r2_lp <= r1_lp; r2_lo <= r1_lo;
            r2_spar <= r1_spar; r2_nq <= r1_nq; r2_m01 <= r1_m01; r2_m23 <= r1_m23; r2_b0 <= r1_blk0; r2_b1 <= r1_blk1;
            for (kd = 0; kd < 4; kd = kd + 1) r2_hi[9*kd +: 9] <= (r1_spar ? 9'(KMAX/128) : 9'd0) + {1'b0, r1_w[8+8*kd +: 8]};
            r3_v <= r2_v; r3_w <= r2_w; r3_tag <= r2_tag; r3_pos <= r2_pos; r3_fam <= r2_fam; r3_lp <= r2_lp; r3_lo <= r2_lo;
            r3_spar <= r2_spar; r3_nq <= r2_nq; r3_umax <= r2_m23 > r2_m01 ? r2_m23 : r2_m01;
            r3_b0 <= r2_b0; r3_b1 <= r2_b1; r3_hi <= r2_hi;
            he <= r3_e; hv <= r3_v;
        end
    end
    // p1 / bt broadcast-header pipeline (own reset region rst_p; same next-state functions as before the split)
    always @(posedge clk or negedge rst_p) begin
        if (!rst_p) begin
            p1_xs_v <= 0; p1_xb_v <= 0; p1_go <= 0; p1_gobf <= 0; p1_cfg <= 0; p1_tag <= 0; p1_ph <= 0; p1_np <= 0;
            bt_xs_v <= 0; bt_xb_v <= 0; bt_go <= 0; bt_gobf <= 0; bt_cfg <= 0; bt_tag <= 0; bt_ph <= 0; bt_np <= 0;
        end else begin
            p1_cfg <= action[62]; p1_go <= action[65];
            if (action[62]) begin p1_ph <= s_ph[config_tag]; p1_np <= s_np[config_tag]; end
            if (action[65]) begin p1_gobf <= s_pw0[launch_tag]; p1_tag <= launch_tag; end
            p1_xs_v <= hv && hw[0] && !h_fam; p1_xb_v <= hv && hw[0] && h_fam;
            bt_xs_v <= p1_xs_v; bt_xb_v <= p1_xb_v;
            bt_go <= p1_go; bt_gobf <= p1_gobf; bt_cfg <= p1_cfg; bt_tag <= p1_tag; bt_ph <= p1_ph; bt_np <= p1_np;
        end
    end
endmodule
