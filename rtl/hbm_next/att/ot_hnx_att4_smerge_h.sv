`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_att4_smerge_h: ONE WORD-HALF of the shared NL-lane PV merge (ot_hnx_att4_smerge, PUBLISH = 1) for the cluster
// leaves of HNEXT.ATT4 (claude/hnx-att4-leaf-1020).  The _nf one-tile gate (hnx_rp3a3_spvm_safe_nf, 10-19) failed on
// one 18.5k-sink root (pin-flop spread TT 127 / FF 114 ps) and a GRT that the 4 h GATE_STALL watchdog killed (rc 137)
// while 18 abutted 512-bit macro buses converged on one std area.  The merge's control (decode, entries, return ring,
// turn, publication FSM) never reads a data value, and the datapath is word-sliced: adder g reads / writes only word g
// of every ring head, event word and its own result.  So the datapath splits by word half with NO data crossing:
// HALF h holds words 8h .. 8h+7 = the 256-bit half macro of every (lane, level) ring (9 SRAMs at NL 3), adders 8h..8h+7,
// their kept one-hot operand selects, head-write muxes and a 256-bit publication buffer.  Each half carries an
// IDENTICAL replica of the control (same inputs, same reset edge => same state every cycle; the cluster lockstep bench
// proves it against the flat spvm), so the leaves exchange only their registered input feed-throughs, the publication
// word and the sticky fault -- no command seam, no added recurrence latency (ring turn 8 = ALAT 7 + head, unchanged).
// PH0 = reset value of the free-running residue ph: the leaves land the reset one stage deeper than the data (2-stage
// reset landing + kept split stage), so ph starts at PH0 = 1 to keep the residue of every input edge unchanged.
// Publication: pub_data = this half's word pub_word[2:0] (the leaf picks the half by pub_word[3]); all other publication
// outputs are identical in both halves.  Mutants as ot_hnx_att4_smerge (MUT 1..6); pv_* outputs are not built (the
// production leaf publishes, PUBLISH = 1).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att4_smerge_h #(
    parameter integer NL      = 3,      // query lanes = P (P3 default, owner 10-19; generic 1..4)
    parameter integer L       = 16,
    parameter integer TAGW    = 16,
    parameter integer ALAT    = 7,
    parameter integer LV      = 3,
    parameter integer MUT     = 0,
    parameter integer WHP     = 256,    // half width (fixed: L 16 / 2 x 32)
    parameter integer HALF    = 0,      // word half: 0 = words 0..7, 1 = words 8..15
    parameter integer PH0     = 0       // residue counter reset value (see header)
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
    localparam integer W  = WHP;                         // this half's datapath width (8 words)
    localparam integer LH = L / 2;                       // adders in this half
    localparam integer NE = 8 * NL;
    localparam integer NW = NL * LV;                      // ring head words
    localparam [1:0] IDLE = 2'd0, RIP = 2'd1, FL = 2'd2;
    localparam [2:0] TOP = 3'(LV - 1);

    // ---------------- reset landing: kept control copies (the adders take their own copy in g_madd) ----------------
    localparam integer RST_COPIES = `ifdef OT_HNX_ATT_SAFE_RESET 16 `else 1 `endif;
    // Identical kept vectors at the EXISTING reset edge; synthesis proves identity and distributes at most32loads.
    (* keep = "true", ot_rst_split = 1 *) reg [RST_COPIES-1:0] rst_cv, rst_ev;
    wire rst_c = rst_cv[0];
    wire rst_e = rst_ev[0];
    always @(posedge clk) begin rst_cv <= {RST_COPIES{rst_n}}; rst_ev <= {RST_COPIES{rst_n}}; end

    // ---------------- input registers (STEP 4: +2 edges, uniform) -------------------------------------------------------
    // Stage 1 = LANDING registers: the decode reads ev / tag only from ev_q / tag_q, which the placer puts beside the
    // decode (their D is the tile pin register across the outline, a wire-only cycle), so no pin wire sits in front of
    // the decode logic.  The data / publication inputs take the same stage (sum_l, *_l) so every input is delayed
    // uniformly: it only rotates which residue a slot owns (as the pin registers do); stage 2 (sum_q, ps_q, ...) is the
    // step-3 input register the head stage reads one cycle after the decode.
    reg [NL-1:0]      ev_q;
    reg [NL*TAGW-1:0] tag_q;
    reg [NL*W-1:0]    sum_l, sum_q;
    reg               ps_l, ps_q;
    reg [1:0]         pl_l, pl_q;
    reg [2:0]         pslot_l, pslot_q;
    always @(posedge clk or negedge rst_c)
        if (!rst_c) begin ev_q <= {NL{1'b0}}; ps_l <= 1'b0; ps_q <= 1'b0; end
        else begin ev_q <= ev; ps_l <= pub_start; ps_q <= ps_l; end
    always @(posedge clk) begin
        tag_q <= tag_d; sum_l <= sum; sum_q <= sum_l;
        pl_l <= pub_lane; pl_q <= pl_l; pslot_l <= pub_slot; pslot_q <= pslot_l;
    end

    reg [2:0] ph;                                        // residue whose entries are at the ring heads (head stage)
    always @(posedge clk or negedge rst_c) if (!rst_c) ph <= 3'(PH0); else ph <= ph + 3'd1;
    wire [2:0] phn = ph + 3'd1;                          // residue decoded this cycle (its head turn is the next cycle)

    // ---------------- per-entry control (indexed {lane, residue}) ----------------
    reg [1:0]      e_md  [0:NE-1];
    reg [2:0]      e_rk  [0:NE-1];
    reg [2:0]      e_rj  [0:NE-1];
    reg            e_fin [0:NE-1];
    reg            e_ff  [0:NE-1];
    reg [LV-1:0]   e_fb  [0:NE-1];
    reg [LV:0]     e_n   [0:NE-1];
    reg [TAGW-1:0] e_tag [0:NE-1];
    reg [NE-1:0]   node_valid;

    // ---------------- stationary return metadata ring (issue now -> same ph in eight edges) ----------------
    reg [ALAT:0]   rp_v;
    reg [1:0]      rp_l   [0:ALAT];
    reg [2:0]      rp_t   [0:ALAT];
    reg            rp_f   [0:ALAT];
    reg [TAGW-1:0] rp_tag [0:ALAT];
    wire           ret_v = rp_v[ph];
    wire [1:0]     ret_l = rp_l[ph];
    wire [2:0]     ret_t = rp_t[ph];
    wire           nret_v = rp_v[phn];                // the result that returns at the NEXT head turn
    wire [1:0]     nret_l = rp_l[phn];
    wire [2:0]     nret_t = rp_t[phn];
    wire [W-1:0]   my;

    // ---------------- stationary SRAM rings: read ph+1, write ph; no shifting storage ----------------
    wire [NW*W-1:0] hw;                                  // head words
    wire [NW*W-1:0] hn;                                  // head next (into stage 7)
    genvar gl, gq;
    generate for (gl = 0; gl < NL; gl = gl + 1) begin : g_lane
        for (gq = 0; gq < LV; gq = gq + 1) begin : g_lv
            // Each bank needs one read and write per edge; independent banks preserve simultaneous lane events.
            // Registered SRAM output is the next head. Distinct read/write addresses avoid collision semantics.
            // MUT 6 reads one residue early: a storage-specific negative control.
            hnx_sram_1r1w_128x256_r43 u_ring (
                .clk(clk), .r_ce_in(1'b1), .r_addr_in({4'b0, (MUT == 6 ? ph : phn)}),
                .rd_out(hw[(gl*LV+gq)*W +: W]),
                .w_ce_in(1'b1), .w_addr_in({4'b0, ph}), .wd_in(hn[(gl*LV+gq)*W +: W]),
                .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
        end
    end endgenerate

    function automatic [2:0] tones(input [LV:0] c);      // trailing ones
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

    // ================= DECODE STAGE (cycle before the head turn of residue phn): raw inputs, entries (l, phn) =========
    reg [2:0]      ew   [0:NL-1];                        // level the event writes
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
    reg            iss;
    reg [LV-1:0]   rem0, rem1;
    reg [2:0]      k0, k1;
    reg            lastr, pone, first, lastc;
    reg [4:0]      ix;
    // one-hot selects of the head cycle: operand A / B = ring head word m | returning result | lane l's event word
    reg [NW-1:0]   da_hw, db_hw, dw_ev, dw_rt;
    reg            da_my, db_my;
    reg [NL-1:0]   da_ev, db_ev;
    reg [NL-1:0]   d_flt, d_nvc;
    integer l, q, m;
    always @(*) begin
        for (l = 0; l < NL; l = l + 1) begin
            ix = {l[1:0], phn};
            first = tag_q[l*TAGW + TAGW-2]; lastc = tag_q[l*TAGW + TAGW-3];
            cc[l] = first ? {(LV+1){1'b0}} : e_n[ix];
            ew[l] = cc[l][0] ? tones(cc[l]) : 3'd0;
            if (ev_q[l]) begin
                d_n[l] = cc[l] + 1'b1; d_tag[l] = tag_q[l*TAGW +: TAGW];
                d_rk[l] = 3'd0; d_rj[l] = ew[l]; d_fin[l] = lastc; d_ff[l] = 1'b1;
                d_fb[l] = d_n[l][LV-1:0];
                d_md[l] = cc[l][0] ? RIP : (lastc ? FL : IDLE);
            end else begin
                d_n[l] = e_n[ix]; d_tag[l] = e_tag[ix]; d_rk[l] = e_rk[ix]; d_rj[l] = e_rj[ix];
                d_fin[l] = e_fin[ix]; d_ff[l] = e_ff[ix]; d_fb[l] = e_fb[ix]; d_md[l] = e_md[ix];
            end
            // collisions of an arriving event (sticky fault at the head turn)
            d_flt[l] = ev_q[l] && ((e_md[ix] != IDLE) || (nret_v && nret_l == l[1:0] && nret_t == ew[l]) ||
                                 (cc[l] >= (1 << (LV - 1))));
            d_nvc[l] = ev_q[l] && first;
            cand[l] = (d_md[l] != IDLE);
            // step
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
        // the turn: the returning chain keeps it, else the lowest lane with a step
        iss = |cand;
        sel = 2'd0;
        for (l = NL - 1; l >= 0; l = l - 1) if (cand[l]) sel = l[1:0];
        if (nret_v && cand[nret_l]) sel = nret_l;
        // operand selects with the step-2 priority: event word > returning result > ring head word; B = +0 if s_bz
        da_hw = {NW{1'b0}}; db_hw = {NW{1'b0}}; da_my = 1'b0; db_my = 1'b0; da_ev = {NL{1'b0}}; db_ev = {NL{1'b0}};
        if (ev_q[sel] && ew[sel] == s_a[sel]) da_ev[sel] = 1'b1;
        else if (nret_v && nret_l == sel && nret_t == s_a[sel]) da_my = 1'b1;
        else for (m = 0; m < NW; m = m + 1) if (m == sel * LV + s_a[sel]) da_hw[m] = 1'b1;
        if (s_bz[sel]) begin end
        else if (MUT != 1 && ev_q[sel] && ew[sel] == s_b[sel]) db_ev[sel] = 1'b1;
        else if (nret_v && nret_l == sel && nret_t == s_b[sel]) db_my = 1'b1;
        else for (m = 0; m < NW; m = m + 1) if (m == sel * LV + s_b[sel]) db_hw[m] = 1'b1;
        // head writes: the event's word, else the returning result's word, else the head word circulates
        for (l = 0; l < NL; l = l + 1)
            for (q = 0; q < LV; q = q + 1) begin
                dw_ev[l*LV+q] = ev_q[l] && ew[l] == q[2:0];
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
    reg            x_iss, x_sf;
    reg [1:0]      x_sel;
    reg [2:0]      x_st;
    reg [TAGW-1:0] x_stag;
    reg [NL-1:0]   x_flt, x_nvc;
    integer l3;
    always @(posedge clk or negedge rst_e)
        if (!rst_e) begin
            x_iss <= 1'b0; x_flt <= {NL{1'b0}}; x_nvc <= {NL{1'b0}};
            for (l3 = 0; l3 < NL; l3 = l3 + 1) x_md[l3] <= IDLE;
        end else begin
            x_iss <= iss; x_flt <= d_flt; x_nvc <= d_nvc;
            for (l3 = 0; l3 < NL; l3 = l3 + 1) x_md[l3] <= (iss && sel == l3[1:0]) ? p_md[l3] : d_md[l3];
        end
    always @(posedge clk) begin
        x_sel <= sel; x_st <= s_t[sel]; x_sf <= s_fin[sel]; x_stag <= d_tag[sel];
        for (l3 = 0; l3 < NL; l3 = l3 + 1) begin
            x_n[l3] <= d_n[l3]; x_rj[l3] <= d_rj[l3]; x_fin[l3] <= d_fin[l3]; x_tag[l3] <= d_tag[l3];
            if (iss && sel == l3[1:0]) begin x_rk[l3] <= p_rk[l3]; x_fb[l3] <= p_fb[l3]; x_ff[l3] <= p_ff[l3]; end
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
        (* keep *) reg [NW-1:0] ka_hw, kb_hw, kw_ev, kw_rt;
        (* keep *) reg          ka_my, kb_my;
        (* keep *) reg [NL-1:0] ka_ev, kb_ev;
        (* keep = "true", ot_rst_split = 1 *) reg [RST_COPIES-1:0] rst_mv;
        wire rst_m = rst_mv[0];
        always @(posedge clk) begin
            ka_hw <= da_hw; kb_hw <= db_hw; kw_ev <= dw_ev; kw_rt <= dw_rt;
            ka_my <= da_my; kb_my <= db_my; ka_ev <= da_ev; kb_ev <= db_ev; rst_mv <= {RST_COPIES{rst_n}};
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
            assign hn[gw*W + 32*ga +: 32] = kw_ev[gw] ? sum_q[(gw/LV)*W + 32*ga +: 32] :
                                            kw_rt[gw] ? my[32*ga +: 32] : hw[gw*W + 32*ga +: 32];
        end
        ot_gpu_fadd #(.LAT(ALAT)) u_m (.clk(clk), .rst_n(rst_m), .v(ov), .a(oa[32*ga +: 32]), .b(ob[32*ga +: 32]),
                                       .y(my[32*ga +: 32]), .fault(mf[ga]));
    end endgenerate

    // ---------------- state update (entries (l, ph)), return, faults ----------------
    integer k, l2;
    reg [4:0] ix2, ix3;
    reg m_fault;
    always @(posedge clk or negedge rst_e) begin
        if (!rst_e) begin
            rp_v <= {(ALAT+1){1'b0}}; m_fault <= 1'b0; node_valid <= {NE{1'b0}};
            for (k = 0; k < NE; k = k + 1) begin
                e_md[k] <= IDLE; e_rk[k] <= 3'd0; e_rj[k] <= 3'd0; e_fin[k] <= 1'b0; e_ff[k] <= 1'b0;
                e_fb[k] <= {LV{1'b0}}; e_n[k] <= {(LV+1){1'b0}};
            end
        end else begin
            rp_v[ph] <= x_iss;
            if (ret_v && rp_f[ph]) node_valid[{ret_l, ph}] <= 1'b1;
            if ((|mf) || (|x_flt)) m_fault <= 1'b1;
            for (l2 = 0; l2 < NL; l2 = l2 + 1) begin
                ix2 = {l2[1:0], ph};
                if (x_nvc[l2]) node_valid[ix2] <= 1'b0;
                e_n[ix2] <= x_n[l2]; e_rj[ix2] <= x_rj[l2]; e_fin[ix2] <= x_fin[l2];
                e_md[ix2] <= x_md[l2]; e_rk[ix2] <= x_rk[l2]; e_fb[ix2] <= x_fb[l2]; e_ff[ix2] <= x_ff[l2];
            end
        end
    end
    always @(posedge clk) begin
        for (l2 = 0; l2 < NL; l2 = l2 + 1) begin ix3 = {l2[1:0], ph}; e_tag[ix3] <= x_tag[l2]; end
        rp_l[ph] <= x_sel; rp_t[ph] <= x_st; rp_f[ph] <= x_sf; rp_tag[ph] <= x_stag;
    end

    // ---------------- publication (PUBLISH = 1): node = level LV-1 of entry (pl_q, ph), request through the input reg ----
    reg pub_fault;
    generate if (1) begin : g_pub
        reg [W-1:0] pr_q, pub_buffer;
        reg pub_d0, pub_d1, pub_active;
        reg [2:0] slot0, slot1;
        reg [1:0] lane0, lane1;
        reg [TAGW-1:0] tag0, tag1;
        reg [3:0] word_next;
        reg [4:0] pix;
        wire [1:0] rl = (MUT == 5) ? (pl_q ^ 2'd1) : pl_q;
        integer pl;
        always @(posedge clk)
            for (pl = 0; pl < NL; pl = pl + 1) if (rl == pl[1:0]) pr_q <= hw[(pl*LV + LV-1)*W +: W];
        always @(posedge clk or negedge rst_c)
            if (!rst_c) begin
                pub_d0 <= 1'b0; pub_d1 <= 1'b0; pub_active <= 1'b0; pub_fault <= 1'b0; pub_v <= 1'b0; word_next <= 4'd0;
            end else begin
                pub_d0 <= ps_q; pub_d1 <= pub_d0;
                pub_v <= pub_d1 || pub_active;
                if (ps_q) begin
                    pix = {pl_q, ph};
                    slot0 <= pslot_q; lane0 <= pl_q; tag0 <= e_tag[pix];
                    if (!node_valid[pix] || e_tag[pix][2:0] != pslot_q || (ret_v && ret_l == pl_q && ret_t == TOP) ||
                        pub_d0 || pub_d1 || (pub_active && word_next != 4'd14) || pl_q >= NL)
                        pub_fault <= 1'b1;
                end
                if (pub_d0) begin pub_buffer <= pr_q; slot1 <= slot0; lane1 <= lane0; tag1 <= tag0; end
                if (pub_d1) begin
                    pub_data <= pub_buffer[31:0]; pub_word <= 4'd0; pub_out_slot <= slot1; pub_out_lane <= lane1;
                    pub_tag <= tag1; word_next <= 4'd1; pub_active <= 1'b1;
                end else if (pub_active) begin
                    pub_data <= pub_buffer[32*word_next[2:0] +: 32]; pub_word <= word_next;
                    if (word_next == 4'd15) begin pub_active <= 1'b0; word_next <= 4'd0; end
                    else word_next <= word_next + 4'd1;
                end
            end
    end endgenerate
    assign fault = m_fault | pub_fault;
endmodule
`default_nettype wire
