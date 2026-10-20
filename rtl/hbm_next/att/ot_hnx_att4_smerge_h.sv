`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_att4_smerge_h: ONE WORD-HALF of the shared NL-lane PV merge (= ot_hnx_att4_smerge PUBLISH 1, bit-exact) for the
// cluster leaves of HNEXT.ATT4 (claude/hnx-att4-leaf-1020, 2026-10-20).
// WHY: the _nf one-tile gate (hnx_rp3a3_spvm_safe_nf, 10-19) failed on one 18.5k-sink root (pin-flop spread TT 127 / FF
// 114 ps) and a GRT the 4 h GATE_STALL watchdog killed (rc 137) while 18 abutted 512-bit macro buses converged.  The
// merge's control never reads a data value and the datapath is word-sliced (adder g reads / writes only word g of every
// ring head, event word and its own result), so the datapath splits by word half with NO data crossing: HALF h holds
// words 8h .. 8h+7 = the 256-bit half macro of every (lane, level) ring (9 SRAMs at NL 3), adders 8h .. 8h+7, their
// kept one-hot operand selects, head-write muxes and a 256-bit publication buffer.  Each half carries an IDENTICAL
// control replica (same inputs => same state every cycle; the cluster lockstep bench proves it vs the flat spvm).
// NATIVE FANOUT (pre-gate census, limit 32 loads a driver incl. resets; the flat core mapped 291 violations, max 1,034):
//   * residue: no shared 3-bit ph -> every consumer has its own KEPT rotating one-hot ring (per lane: entry control
//     read / tag read / control write / tag write; return ring read ph / read phn / write; node-valid write / read) and
//     two kept 3-bit SRAM address counters (read phn / write ph, 9 macro pins a bit); entry and return-ring storage is
//     read by one-hot AND-OR (no index mux trees);
//   * reset: one kept copy per consumer group (<= 32 async loads), one per adder; only the state the function needs is
//     reset (entry mode e_md, node_valid, return valid, issue / fault / publication control) -- e_n / e_rk / ... are
//     written every head turn and read only after a run's first chunk, exactly as before;
//   * publication: lane select = kept one-hot copies per 32-b word, buffer = load-then-shift register with kept load /
//     shift enables per word (no 16:1 word mux), the request's tag / node-valid are the decode's registered reads;
//   * events: ev_q kept three times (control / tag / selects+faults); head-write selects kw_* kept twice per adder;
//   * adders: ot_hdc_fp32_add_lat_fan32 SAFE_DIST 1 (the qualified LAT 7 / DRST 0 native fan-32 graph, main 520dbea3a;
//     bit-exact to ot_hdc_fp32_add_lat = ot_gpu_fadd's adder; benches unpack its cells via
//     tools/prepare_fp32_fan32_models.py).
// PH0 = reset value of the residue (the leaves land the reset one stage deeper than the data, PH0 1 keeps the residue of
// every input edge as in the flat tile; a different release only relabels residues, see ot_hnx_att4_sleaf.sv).
// Publication: pub_data = this half's local word (word index pub_word, the leaf takes the half by pub_word[3]); it is
// valid only with pub_v (the leaf holds it).  pv_* outputs are not built (the production leaf publishes).
// Mutants (bench negative controls, as ot_hnx_att4_smerge): MUT 1 = B event bypass dropped; 2 = result written into
// lane l^1's ring; 3 = ripple reads one level too high; 4 = flush first add B = +0; 5 = publication reads lane ^ 1;
// 6 = storage reads one residue early.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att4_smerge_h #(
    parameter integer NL      = 3,      // query lanes = P (P3 default; generic 1..4)
    parameter integer L       = 16,
    parameter integer TAGW    = 16,
    parameter integer ALAT    = 7,
    parameter integer LV      = 3,
    parameter integer MUT     = 0,
    parameter integer WHP     = 256,    // half width (fixed: 8 words)
    parameter integer HALF    = 0,      // word half: 0 = words 0..7, 1 = words 8..15
    parameter integer PH0     = 0       // residue reset value
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [NL-1:0]        ev,
    input  wire [NL*WHP-1:0]    sum,        // lane-major, this half's 8 words of each lane
    input  wire [NL*TAGW-1:0]   tag_d,
    input  wire                 pub_start,
    input  wire [1:0]           pub_lane,
    input  wire [2:0]           pub_slot,
    output reg                  pub_v,
    output reg  [31:0]          pub_data,
    output reg  [3:0]           pub_word,
    output reg  [2:0]           pub_out_slot,
    output reg  [1:0]           pub_out_lane,
    output reg  [TAGW-1:0]      pub_tag,
    output wire                 fault
);
    initial if (L != 16 || ALAT != 7 || LV < 1 || LV > 7 || NL < 1 || NL > 4 || TAGW < 6 || WHP != 256 || HALF < 0 ||
                HALF > 1 || PH0 < 0 || PH0 > 7)
        $fatal(1, "ot_hnx_att4_smerge_h: L 16, ALAT 7, 1 <= LV <= 7, 1 <= NL <= 4, TAGW >= 6, WHP 256, HALF 0/1, PH0 0..7");
    localparam integer W  = WHP;
    localparam integer LH = L / 2;
    localparam integer NE = 8 * NL;
    localparam integer NW = NL * LV;
    localparam [1:0] IDLE = 2'd0, RIP = 2'd1, FL = 2'd2;
    localparam [2:0] TOP = 3'(LV - 1);
    localparam [7:0] OH_PH  = 8'd1 << PH0;
    localparam [7:0] OH_PHN = 8'd1 << ((PH0 + 1) % 8);
    localparam [2:0] PH0_3 = 3'(PH0), PHN0_3 = 3'((PH0 + 1) % 8);

    // ---------------- reset: kept copies, one per consumer group (<= 32 async loads each) --------------------------------
    // 0 input / issue control   1 return valid + fault + publication control   2 node_valid
    // 3+l entry mode of lane l  3+NL+l residue rings of lane l   3+2NL return rings + SRAM address counters
    // 4+2NL node-valid rings
    localparam integer RC = 5 + 2 * NL;
    (* keep = "true" *) reg [RC-1:0] rcv;
    always @(posedge clk) rcv <= {RC{rst_n}};
    wire rst_c = rcv[0];
    wire rst_p = rcv[1];
    wire rst_v = rcv[2];
    wire rst_r = rcv[3 + 2 * NL];
    wire rst_w = rcv[4 + 2 * NL];

    // ---------------- input registers (+2 edges, uniform; as ot_hnx_att4_smerge step 4) ----------------------------------
    (* keep = "true" *) reg [NL-1:0] ev_q;               // control copy
    (* keep = "true" *) reg [NL-1:0] ev_qt;              // tag / node-valid-clear copy
    (* keep = "true" *) reg [NL-1:0] ev_qs;              // operand-select / write-select / fault copy
    reg [NL*TAGW-1:0] tag_q;
    reg [NL*W-1:0]    sum_l, sum_q;
    reg               ps_l, ps_q;
    (* keep = "true" *) reg ps_qk;                       // copy of ps_q for the 16 publication load enables
    reg [1:0]         pl_l, pl_q;
    reg [2:0]         pslot_l, pslot_q;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) begin ev_q <= {NL{1'b0}}; ev_qt <= {NL{1'b0}}; ev_qs <= {NL{1'b0}}; ps_l <= 1'b0; ps_q <= 1'b0; ps_qk <= 1'b0; end
        else begin ev_q <= ev; ev_qt <= ev; ev_qs <= ev; ps_l <= pub_start; ps_q <= ps_l; ps_qk <= ps_l; end
    always @(posedge clk) begin
        tag_q <= tag_d; sum_l <= sum; sum_q <= sum_l;
        pl_l <= pub_lane; pl_q <= pl_l; pslot_l <= pub_slot; pslot_q <= pslot_l;
    end

    // ---------------- residue: kept one-hot rings / address counters, all advance every edge ----------------------------
    // ph = residue at the ring heads (head stage), phn = ph + 1 (decoded this cycle).
    reg [7:0] rr_c [0:NL-1];                            // phn: entry control read, lane l
    reg [7:0] rr_t [0:NL-1];                            // phn: entry tag read
    reg [7:0] rw_c [0:NL-1];                            // ph : entry control write (md, n, rj)
    reg [7:0] rw_d [0:NL-1];                            // ph : entry control write (fin, rk, fb, ff)
    reg [7:0] rw_t [0:NL-1];                            // ph : entry tag write
    (* keep = "true" *) reg [7:0] rq_r, rq_n, rq_w, rv_w, rv_r;   // return ring read ph / read phn / write ph;
                                                                  // node_valid write ph / read phn
    (* keep = "true" *) reg [2:0] a_rd, a_wr;           // SRAM read address (phn) / write address (ph)
    genvar gr;
    generate for (gr = 0; gr < NL; gr = gr + 1) begin : g_rr
        (* keep = "true" *) reg [7:0] oc, ot, wc, wd, wt;
        always @(posedge clk or negedge rcv[3 + NL + gr])
            if (!rcv[3 + NL + gr]) begin oc <= OH_PHN; ot <= OH_PHN; wc <= OH_PH; wd <= OH_PH; wt <= OH_PH; end
            else begin
                oc <= {oc[6:0], oc[7]}; ot <= {ot[6:0], ot[7]}; wc <= {wc[6:0], wc[7]}; wd <= {wd[6:0], wd[7]};
                wt <= {wt[6:0], wt[7]};
            end
        always @(*) begin rr_c[gr] = oc; rr_t[gr] = ot; rw_c[gr] = wc; rw_d[gr] = wd; rw_t[gr] = wt; end
    end endgenerate
    always @(posedge clk or negedge rst_r)
        if (!rst_r) begin
            rq_r <= OH_PH; rq_n <= OH_PHN; rq_w <= OH_PH; a_rd <= PHN0_3; a_wr <= PH0_3;
        end else begin
            rq_r <= {rq_r[6:0], rq_r[7]}; rq_n <= {rq_n[6:0], rq_n[7]}; rq_w <= {rq_w[6:0], rq_w[7]};
            a_rd <= a_rd + 3'd1; a_wr <= a_wr + 3'd1;
        end
    always @(posedge clk or negedge rst_w)
        if (!rst_w) begin rv_w <= OH_PH; rv_r <= OH_PHN; end
        else begin rv_w <= {rv_w[6:0], rv_w[7]}; rv_r <= {rv_r[6:0], rv_r[7]}; end

    // ---------------- per-entry control (entry {lane, residue}) ---------------------------------------------------------
    reg [1:0]      e_md  [0:NE-1];
    reg [2:0]      e_rk  [0:NE-1];
    reg [2:0]      e_rj  [0:NE-1];
    reg            e_fin [0:NE-1];
    reg            e_ff  [0:NE-1];
    reg [LV-1:0]   e_fb  [0:NE-1];
    reg [LV:0]     e_n   [0:NE-1];
    reg [TAGW-1:0] e_tag [0:NE-1];
    reg [NE-1:0]   node_valid;

    // ---------------- return ring (issue now -> same residue in eight edges) --------------------------------------------
    reg [7:0]      rp_v;
    reg [1:0]      rp_l [0:7];
    reg [2:0]      rp_t [0:7];
    reg            rp_f [0:7];
    reg            ret_v, ret_f, nret_v;
    reg [1:0]      ret_l, nret_l;
    reg [2:0]      ret_t, nret_t;
    integer r0;
    always @(*) begin
        ret_v = 1'b0; ret_f = 1'b0; ret_l = 2'd0; ret_t = 3'd0; nret_v = 1'b0; nret_l = 2'd0; nret_t = 3'd0;
        for (r0 = 0; r0 < 8; r0 = r0 + 1) begin
            ret_v = ret_v | (rq_r[r0] & rp_v[r0]); ret_f = ret_f | (rq_r[r0] & rp_f[r0]);
            ret_l = ret_l | ({2{rq_r[r0]}} & rp_l[r0]); ret_t = ret_t | ({3{rq_r[r0]}} & rp_t[r0]);
            nret_v = nret_v | (rq_n[r0] & rp_v[r0]);
            nret_l = nret_l | ({2{rq_n[r0]}} & rp_l[r0]); nret_t = nret_t | ({3{rq_n[r0]}} & rp_t[r0]);
        end
    end
    wire [W-1:0] my;

    // ---------------- stationary SRAM rings (this half): read phn, write ph ---------------------------------------------
    wire [NW*W-1:0] hw;
    wire [NW*W-1:0] hn;
    genvar gl, gq;
    generate for (gl = 0; gl < NL; gl = gl + 1) begin : g_lane
        for (gq = 0; gq < LV; gq = gq + 1) begin : g_lv
            hnx_sram_1r1w_128x256_r43 u_ring (
                .clk(clk), .r_ce_in(1'b1), .r_addr_in({4'b0, (MUT == 6 ? a_wr : a_rd)}),
                .rd_out(hw[(gl*LV+gq)*W +: W]),
                .w_ce_in(1'b1), .w_addr_in({4'b0, a_wr}), .wd_in(hn[(gl*LV+gq)*W +: W]),
                .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
    end endgenerate

    function automatic [2:0] tones(input [LV:0] c);
        integer i; reg stop;
        begin tones = 3'd0; stop = 1'b0;
            for (i = 0; i < LV; i = i + 1) if (!stop) begin if (c[i]) tones = tones + 3'd1; else stop = 1'b1; end
        end
    endfunction
    function automatic [2:0] lowbit(input [LV-1:0] b);
        integer i; reg got;
        begin lowbit = 3'd0; got = 1'b0;
            for (i = 0; i < LV; i = i + 1) if (!got && b[i]) begin lowbit = 3'(i); got = 1'b1; end
        end
    endfunction

    // ================= DECODE STAGE (cycle before the head turn of residue phn) =======================================
    // one-hot reads of entry (l, phn)
    reg [1:0]      r_md [0:NL-1];
    reg [2:0]      r_rk [0:NL-1], r_rj [0:NL-1];
    reg            r_fin[0:NL-1], r_ff [0:NL-1];
    reg [LV-1:0]   r_fb [0:NL-1];
    reg [LV:0]     r_n  [0:NL-1];
    reg [TAGW-1:0] r_tag[0:NL-1];
    reg            r_nv [0:NL-1];
    integer l, q, m, r;
    always @(*) begin
        for (l = 0; l < NL; l = l + 1) begin
            r_md[l] = 2'd0; r_rk[l] = 3'd0; r_rj[l] = 3'd0; r_fin[l] = 1'b0; r_ff[l] = 1'b0; r_fb[l] = {LV{1'b0}};
            r_n[l] = {(LV+1){1'b0}}; r_tag[l] = {TAGW{1'b0}}; r_nv[l] = 1'b0;
            for (r = 0; r < 8; r = r + 1) begin
                r_md[l]  = r_md[l]  | ({2{rr_c[l][r]}} & e_md[l*8+r]);
                r_rk[l]  = r_rk[l]  | ({3{rr_c[l][r]}} & e_rk[l*8+r]);
                r_rj[l]  = r_rj[l]  | ({3{rr_c[l][r]}} & e_rj[l*8+r]);
                r_fin[l] = r_fin[l] | (rr_c[l][r] & e_fin[l*8+r]);
                r_ff[l]  = r_ff[l]  | (rr_c[l][r] & e_ff[l*8+r]);
                r_fb[l]  = r_fb[l]  | ({LV{rr_c[l][r]}} & e_fb[l*8+r]);
                r_n[l]   = r_n[l]   | ({(LV+1){rr_c[l][r]}} & e_n[l*8+r]);
                r_tag[l] = r_tag[l] | ({TAGW{rr_t[l][r]}} & e_tag[l*8+r]);
                r_nv[l]  = r_nv[l]  | (rv_r[r] & node_valid[l*8+r]);
            end
        end
    end
    reg [2:0]      ew   [0:NL-1];
    reg [LV:0]     cc   [0:NL-1];
    reg [1:0]      d_md [0:NL-1];
    reg [2:0]      d_rk [0:NL-1], d_rj [0:NL-1];
    reg            d_fin[0:NL-1], d_ff [0:NL-1];
    reg [LV-1:0]   d_fb [0:NL-1];
    reg [LV:0]     d_n  [0:NL-1];
    reg [TAGW-1:0] d_tag[0:NL-1];
    reg [2:0]      s_a [0:NL-1], s_b [0:NL-1], s_t [0:NL-1];
    reg            s_bz[0:NL-1], s_fin[0:NL-1];
    reg [1:0]      p_md[0:NL-1];
    reg [2:0]      p_rk[0:NL-1];
    reg [LV-1:0]   p_fb[0:NL-1];
    reg            p_ff[0:NL-1];
    reg [NL-1:0]   cand;
    reg [1:0]      sel;
    reg [NL-1:0]   so, isl;                              // one-hot turn (sel) / issuing lane
    reg [NL-1:0]   ca_ev, ca_my, cb_ev, cb_my;
    reg            iss;
    reg [LV-1:0]   rem0, rem1;
    reg [2:0]      k0, k1;
    reg            lastr, pone, first, lastc;
    reg [NW-1:0]   da_hw, db_hw, dw_ev, dw_rt;
    reg            da_my, db_my;
    reg [NL-1:0]   da_ev, db_ev;
    reg [NL-1:0]   d_flt, d_nvc;
    always @(*) begin
        for (l = 0; l < NL; l = l + 1) begin
            first = tag_q[l*TAGW + TAGW-2]; lastc = tag_q[l*TAGW + TAGW-3];
            cc[l] = first ? {(LV+1){1'b0}} : r_n[l];
            ew[l] = cc[l][0] ? tones(cc[l]) : 3'd0;
            d_tag[l] = ev_qt[l] ? tag_q[l*TAGW +: TAGW] : r_tag[l];
            if (ev_q[l]) begin
                d_n[l] = cc[l] + 1'b1;
                d_rk[l] = 3'd0; d_rj[l] = ew[l]; d_fin[l] = lastc; d_ff[l] = 1'b1;
                d_fb[l] = d_n[l][LV-1:0];
                d_md[l] = cc[l][0] ? RIP : (lastc ? FL : IDLE);
            end else begin
                d_n[l] = r_n[l]; d_rk[l] = r_rk[l]; d_rj[l] = r_rj[l];
                d_fin[l] = r_fin[l]; d_ff[l] = r_ff[l]; d_fb[l] = r_fb[l]; d_md[l] = r_md[l];
            end
            d_flt[l] = ev_qs[l] && ((r_md[l] != IDLE) || (nret_v && nret_l == l[1:0] && nret_t == ew[l]) ||
                                 (cc[l] >= (1 << (LV - 1))));
            d_nvc[l] = ev_qt[l] && first;
            cand[l] = (d_md[l] != IDLE);
            s_a[l] = 3'd0; s_b[l] = 3'd0; s_t[l] = TOP; s_bz[l] = 1'b0; s_fin[l] = 1'b0;
            p_md[l] = d_md[l]; p_rk[l] = d_rk[l]; p_fb[l] = d_fb[l]; p_ff[l] = d_ff[l];
            rem0 = {LV{1'b0}}; rem1 = {LV{1'b0}}; k0 = 3'd0; k1 = 3'd0; lastr = 1'b0; pone = 1'b0;
            if (d_md[l] == RIP) begin
                lastr = (d_rk[l] + 3'd1 == d_rj[l]);
                pone = ((d_n[l] & (d_n[l] - 1'b1)) == {(LV+1){1'b0}});
                s_a[l] = d_rk[l] + ((MUT == 3 && d_rk[l] + 3'd1 < TOP) ? 3'd1 : 3'd0);
                s_b[l] = d_rj[l];
                s_fin[l] = lastr && d_fin[l] && pone;
                s_t[l] = s_fin[l] ? TOP : d_rj[l];
                if (!lastr) p_rk[l] = d_rk[l] + 3'd1;
                else if (d_fin[l] && !pone) begin p_md[l] = FL; p_fb[l] = d_n[l][LV-1:0]; p_ff[l] = 1'b1; end
                else p_md[l] = IDLE;
            end else if (d_md[l] == FL) begin
                k0 = lowbit(d_fb[l]);
                rem0 = d_fb[l] & ~({{(LV-1){1'b0}}, 1'b1} << k0);
                k1 = lowbit(rem0);
                rem1 = rem0 & ~({{(LV-1){1'b0}}, 1'b1} << k1);
                s_t[l] = TOP;
                if (d_ff[l] && rem0 == {LV{1'b0}}) begin
                    s_a[l] = k0; s_bz[l] = 1'b1; s_fin[l] = 1'b1; p_fb[l] = {LV{1'b0}};
                end else if (d_ff[l]) begin
                    s_a[l] = k1; s_b[l] = k0; s_bz[l] = (MUT == 4); s_fin[l] = (rem1 == {LV{1'b0}}); p_fb[l] = rem1;
                end else begin
                    s_a[l] = k0; s_b[l] = TOP; s_fin[l] = (rem0 == {LV{1'b0}}); p_fb[l] = rem0;
                end
                p_ff[l] = 1'b0;
                p_md[l] = s_fin[l] ? IDLE : FL;
            end
        end
        iss = |cand;
        sel = 2'd0;
        for (l = NL - 1; l >= 0; l = l - 1) if (cand[l]) sel = l[1:0];
        if (nret_v && cand[nret_l]) sel = nret_l;
        // operand selects, per lane, gated by the one-hot turn (same priority: event word > returning result > ring head)
        da_hw = {NW{1'b0}}; db_hw = {NW{1'b0}}; da_my = 1'b0; db_my = 1'b0; da_ev = {NL{1'b0}}; db_ev = {NL{1'b0}};
        for (l = 0; l < NL; l = l + 1) begin
            so[l] = (sel == l[1:0]); isl[l] = iss && so[l];
            ca_ev[l] = ev_qs[l] && ew[l] == s_a[l];
            ca_my[l] = nret_v && nret_l == l[1:0] && nret_t == s_a[l];
            cb_ev[l] = MUT != 1 && ev_qs[l] && ew[l] == s_b[l];
            cb_my[l] = nret_v && nret_l == l[1:0] && nret_t == s_b[l];
            da_ev[l] = so[l] && ca_ev[l];
            da_my = da_my | (so[l] && !ca_ev[l] && ca_my[l]);
            db_ev[l] = so[l] && !s_bz[l] && cb_ev[l];
            db_my = db_my | (so[l] && !s_bz[l] && !cb_ev[l] && cb_my[l]);
            for (q = 0; q < LV; q = q + 1) begin
                da_hw[l*LV+q] = so[l] && !ca_ev[l] && !ca_my[l] && s_a[l] == q[2:0];
                db_hw[l*LV+q] = so[l] && !s_bz[l] && !cb_ev[l] && !cb_my[l] && s_b[l] == q[2:0];
            end
        end
        for (l = 0; l < NL; l = l + 1)
            for (q = 0; q < LV; q = q + 1) begin
                dw_ev[l*LV+q] = ev_qs[l] && ew[l] == q[2:0];
                dw_rt[l*LV+q] = !dw_ev[l*LV+q] && nret_v && (((MUT == 2) ? (nret_l ^ 2'd1) : nret_l) == l[1:0]) &&
                                nret_t == q[2:0];
            end
    end

    // ---------------- decode registers ----------------
    reg [1:0]      x_md  [0:NL-1];
    reg [2:0]      x_rk  [0:NL-1], x_rj [0:NL-1];
    reg            x_fin [0:NL-1], x_ff [0:NL-1];
    reg [LV-1:0]   x_fb  [0:NL-1];
    reg [LV:0]     x_n   [0:NL-1];
    reg [TAGW-1:0] x_tag [0:NL-1];
    reg [TAGW-1:0] x_etag[0:NL-1];                       // entry (l, ph) tag as stored (publication read)
    reg [NL-1:0]   x_nv;                                 // node_valid (l, ph) (publication read)
    reg            x_iss, x_sf;
    reg [1:0]      x_sel;
    reg [2:0]      x_st;
    reg [NL-1:0]   x_flt, x_nvc;
    integer l3;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) begin
            x_iss <= 1'b0; x_flt <= {NL{1'b0}}; x_nvc <= {NL{1'b0}};
            for (l3 = 0; l3 < NL; l3 = l3 + 1) x_md[l3] <= IDLE;
        end else begin
            x_iss <= iss; x_flt <= d_flt; x_nvc <= d_nvc;
            for (l3 = 0; l3 < NL; l3 = l3 + 1) x_md[l3] <= isl[l3] ? p_md[l3] : d_md[l3];
        end
    always @(posedge clk) begin
        x_sel <= sel;
        x_st <= 3'd0; x_sf <= 1'b0;
        for (l3 = 0; l3 < NL; l3 = l3 + 1) if (so[l3]) begin x_st <= s_t[l3]; x_sf <= s_fin[l3]; end
        for (l3 = 0; l3 < NL; l3 = l3 + 1) begin
            x_n[l3] <= d_n[l3]; x_rj[l3] <= d_rj[l3]; x_fin[l3] <= d_fin[l3]; x_tag[l3] <= d_tag[l3];
            x_etag[l3] <= r_tag[l3]; x_nv[l3] <= r_nv[l3];
            if (isl[l3]) begin x_rk[l3] <= p_rk[l3]; x_fb[l3] <= p_fb[l3]; x_ff[l3] <= p_ff[l3]; end
            else begin x_rk[l3] <= d_rk[l3]; x_fb[l3] <= d_fb[l3]; x_ff[l3] <= d_ff[l3]; end
        end
    end

    // ================= HEAD STAGE: per 32-b word g (= adder g), kept select copies, one-hot AND-OR only ==============
    reg          ov;
    reg  [W-1:0] oa, ob;
    wire [LH-1:0] mf;
    always @(posedge clk or negedge rst_c) if (!rst_c) ov <= 1'b0; else ov <= x_iss;
    genvar ga, gw;
    generate for (ga = 0; ga < LH; ga = ga + 1) begin : g_madd
        (* keep = "true" *) reg [NW-1:0] ka_hw, kb_hw, kw_ev, kw_rt, kw_ev2, kw_rt2;
        (* keep = "true" *) reg          ka_my, kb_my;
        (* keep = "true" *) reg [NL-1:0] ka_ev, kb_ev;
        (* keep = "true" *) reg          rst_m;
        always @(posedge clk) begin
            ka_hw <= da_hw; kb_hw <= db_hw; kw_ev <= dw_ev; kw_rt <= dw_rt; kw_ev2 <= dw_ev; kw_rt2 <= dw_rt;
            ka_my <= da_my; kb_my <= db_my; ka_ev <= da_ev; kb_ev <= db_ev; rst_m <= rst_n;
        end
        reg [31:0] a_w, b_w;
        integer j;
        always @(*) begin
            a_w = ka_my ? my[32*ga +: 32] : 32'd0;
            b_w = kb_my ? my[32*ga +: 32] : 32'd0;
            for (j = 0; j < NW; j = j + 1) begin
                a_w = a_w | ({32{ka_hw[j]}} & hw[j*W + 32*ga +: 32]);
                b_w = b_w | ({32{kb_hw[j]}} & hw[j*W + 32*ga +: 32]);
            end
            for (j = 0; j < NL; j = j + 1) begin
                a_w = a_w | ({32{ka_ev[j]}} & sum_q[j*W + 32*ga +: 32]);
                b_w = b_w | ({32{kb_ev[j]}} & sum_q[j*W + 32*ga +: 32]);
            end
        end
        always @(posedge clk) begin oa[32*ga +: 32] <= a_w; ob[32*ga +: 32] <= b_w; end
        for (gw = 0; gw < NW; gw = gw + 1) begin : g_hn
            assign hn[gw*W + 32*ga      +: 16] = kw_ev[gw]  ? sum_q[(gw/LV)*W + 32*ga      +: 16] :
                                                 kw_rt[gw]  ? my[32*ga      +: 16] : hw[gw*W + 32*ga      +: 16];
            assign hn[gw*W + 32*ga + 16 +: 16] = kw_ev2[gw] ? sum_q[(gw/LV)*W + 32*ga + 16 +: 16] :
                                                 kw_rt2[gw] ? my[32*ga + 16 +: 16] : hw[gw*W + 32*ga + 16 +: 16];
        end
        wire [1:0] ferr;
        wire       fvo;
        ot_hdc_fp32_add_lat_fan32 #(.LAT(ALAT), .SAFE_DIST(1)) u_m (.clk(clk), .rst_n(rst_m), .valid_in(ov),
            .a(oa[32*ga +: 32]), .b(ob[32*ga +: 32]), .y(my[32*ga +: 32]), .err(ferr), .valid_out(fvo));
        assign mf[ga] = fvo && (ferr != 2'd0);
    end endgenerate

    // ---------------- state update: entries (l, ph), return ring, node_valid, faults ------------------------------------
    integer k, l2, r2;
    reg m_fault;
    generate for (gr = 0; gr < NL; gr = gr + 1) begin : g_ent
        integer rr;
        always @(posedge clk or negedge rcv[3 + gr])
            if (!rcv[3 + gr]) begin
                for (rr = 0; rr < 8; rr = rr + 1) e_md[gr*8+rr] <= IDLE;
            end else begin
                for (rr = 0; rr < 8; rr = rr + 1) if (rw_c[gr][rr]) e_md[gr*8+rr] <= x_md[gr];
            end
        always @(posedge clk) begin
            for (rr = 0; rr < 8; rr = rr + 1) begin
                if (rw_c[gr][rr]) begin e_n[gr*8+rr] <= x_n[gr]; e_rj[gr*8+rr] <= x_rj[gr]; end
                if (rw_d[gr][rr]) begin
                    e_fin[gr*8+rr] <= x_fin[gr]; e_rk[gr*8+rr] <= x_rk[gr]; e_fb[gr*8+rr] <= x_fb[gr];
                    e_ff[gr*8+rr] <= x_ff[gr];
                end
                if (rw_t[gr][rr]) e_tag[gr*8+rr] <= x_tag[gr];
            end
        end
    end endgenerate
    always @(posedge clk or negedge rst_p)
        if (!rst_p) begin rp_v <= 8'd0; m_fault <= 1'b0; end
        else begin
            for (r2 = 0; r2 < 8; r2 = r2 + 1) if (rq_w[r2]) rp_v[r2] <= x_iss;
            if ((|mf) || (|x_flt)) m_fault <= 1'b1;
        end
    always @(posedge clk)
        for (r2 = 0; r2 < 8; r2 = r2 + 1) if (rq_w[r2]) begin rp_l[r2] <= x_sel; rp_t[r2] <= x_st; rp_f[r2] <= x_sf; end
    always @(posedge clk or negedge rst_v)
        if (!rst_v) node_valid <= {NE{1'b0}};
        else for (r2 = 0; r2 < 8; r2 = r2 + 1) if (rv_w[r2]) begin
            for (l2 = 0; l2 < NL; l2 = l2 + 1) begin
                if (ret_v && ret_f && ret_l == l2[1:0]) node_valid[l2*8+r2] <= 1'b1;
                if (x_nvc[l2]) node_valid[l2*8+r2] <= 1'b0;
            end
        end

    // ---------------- publication: node = level LV-1 of entry (pl_q, ph) ------------------------------------------------
    // pr_q: this half of the requested lane's level LV-1 head word, one-hot lane select kept per 32-b word.
    // sh: load-then-shift buffer (load at pub_d0, shift on this half's 8 output words); pub_data = sh word 0.
    reg pub_fault, pub_d0, pub_d1, pub_active;
    (* keep = "true" *) reg pub_d0t, pub_d1t;            // copies for the 16-bit tag enables
    reg [2:0] slot0, slot1;
    reg [1:0] lane0, lane1;
    reg [TAGW-1:0] tag0, tag1;
    reg [3:0] word_next;
    reg [TAGW-1:0] pr_tag;
    reg pr_nv;
    reg [W-1:0] pr_q;
    reg [W-1:0] sh;
    wire [1:0] rl_n = (MUT == 5) ? (pl_l ^ 2'd1) : pl_l;  // lane read one edge later (pl_q)
    (* keep = "true" *) reg [NL-1:0] plo_t;               // one-hot pl_q for the tag / node-valid read
    integer pl, pw;
    always @(posedge clk) for (pl = 0; pl < NL; pl = pl + 1) plo_t[pl] <= (pl_l == pl[1:0]);
    always @(*) begin
        pr_tag = {TAGW{1'b0}}; pr_nv = 1'b0;
        for (pl = 0; pl < NL; pl = pl + 1) begin
            pr_tag = pr_tag | ({TAGW{plo_t[pl]}} & x_etag[pl]); pr_nv = pr_nv | (plo_t[pl] & x_nv[pl]);
        end
    end
    // next-state of the stream (for the kept shift enables)
    wire       pd1_n = pub_d0;
    wire       act_n = pub_d1 | (pub_active & (word_next != 4'd15));
    wire [3:0] wn_n  = pub_d1 ? 4'd1 : (pub_active ? ((word_next == 4'd15) ? 4'd0 : word_next + 4'd1) : word_next);
    wire       sk_n  = pd1_n ? (HALF == 0) : (act_n && (wn_n[3] == HALF[0]));
    genvar gp;
    generate for (gp = 0; gp < 8; gp = gp + 1) begin : g_pw
        (* keep = "true" *) reg [NL-1:0] rlo;              // one-hot lane of the read, this word
        (* keep = "true" *) reg [1:0] ld, sk;              // load (= pub_d0) / shift (this half outputs a word), per 16 b
        always @(posedge clk) begin
            for (pw = 0; pw < NL; pw = pw + 1) rlo[pw] <= (rl_n == pw[1:0]);
            ld <= {2{ps_qk}}; sk <= {2{sk_n}};
        end
        reg [31:0] rw;
        integer j2;
        always @(*) begin
            rw = 32'd0;
            for (j2 = 0; j2 < NL; j2 = j2 + 1) rw = rw | ({32{rlo[j2]}} & hw[(j2*LV + LV-1)*W + 32*gp +: 32]);
        end
        always @(posedge clk) begin
            pr_q[32*gp +: 32] <= rw;
            if (ld[0]) sh[32*gp +: 16] <= pr_q[32*gp +: 16];
            else if (sk[0]) sh[32*gp +: 16] <= (gp == 7) ? 16'd0 : sh[32*(gp+1) +: 16];
            if (ld[1]) sh[32*gp + 16 +: 16] <= pr_q[32*gp + 16 +: 16];
            else if (sk[1]) sh[32*gp + 16 +: 16] <= (gp == 7) ? 16'd0 : sh[32*(gp+1) + 16 +: 16];
        end
    end endgenerate
    always @(posedge clk or negedge rst_p)
        if (!rst_p) begin
            pub_d0 <= 1'b0; pub_d1 <= 1'b0; pub_active <= 1'b0; pub_fault <= 1'b0; pub_v <= 1'b0; word_next <= 4'd0;
            pub_d0t <= 1'b0; pub_d1t <= 1'b0;
        end else begin
            pub_d0 <= ps_q; pub_d1 <= pub_d0; pub_d0t <= ps_q; pub_d1t <= pub_d0;
            pub_v <= pub_d1 || pub_active;
            if (ps_q && (!pr_nv || pr_tag[2:0] != pslot_q || (ret_v && ret_l == pl_q && ret_t == TOP) ||
                         pub_d0 || pub_d1 || (pub_active && word_next != 4'd14) || pl_q >= NL))
                pub_fault <= 1'b1;
            pub_active <= act_n; word_next <= wn_n;
        end
    always @(posedge clk) begin
        if (ps_q) begin slot0 <= pslot_q; lane0 <= pl_q; tag0 <= pr_tag; end
        if (pub_d0) begin slot1 <= slot0; lane1 <= lane0; end
        if (pub_d0t) tag1 <= tag0;
        pub_data <= sh[31:0];
        if (pub_d1t) pub_tag <= tag1;
        if (pub_d1) begin pub_word <= 4'd0; pub_out_slot <= slot1; pub_out_lane <= lane1; end
        else if (pub_active) pub_word <= word_next;
    end
    assign fault = m_fault | pub_fault;
endmodule
`default_nettype wire
