`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-BK bench adapter: presents a DV bk unit (dsdv_bk_sel / dsdv_bk_col) with the old slab's ports (4 lanes in,
// vd out) so the UNCHANGED slab benches (tb_s81ph_sel: transaction compare against the native ot_hdc_v41x_sel;
// tb_s81ph_col: frame / order / DONE / image scoreboard) judge it (+define+OT_DSDV_BK in those benches).
//
// The adapter is the bench's model of the compiled rung schedule around the unit (it is NOT hardware):
//   frame of 8 slots per direction.  A side = the unit's egress side (S unless +mir), B side = the other.
//   A arrivals (vi on the A side): slot 0 = the drain CTL (to the unit; canonical 10-24: consumed there, legacy: travels on to B) for the NEXT frame's window;
//            slots 1..3 = through singles (+thru: NX / CL / kind 7 / foreign CTL) else ingress; 4..7 = ingress.
//   B arrivals: slots 0..3 = through traffic (+thru: XQ / XB 4-fragment beats from slot 0, singles) else ingress;
//            slots 4..7 = ingress.
//   Egress (vo on the A side): the drain window = slots 4..7 (+thru, n 4, d 5) or 0..7 (n 8, d 1) of the next frame,
//            i.e. every A-side output slot that no forwarded B beat uses.  +oddwin: the compiler leaves the last of
//            those slots unused (n 3 / n 7: an ODD window), so a 2-beat word may not start on its last slot (S81U-BK3:
//            with even windows only, the vd capture puts every word start on an even slot and mutant 3 was unreachable).  Ingress is throttled to the drain rate (the
//            compiler's rate match; +nothrottle lifts it for the fail-closed overflow case).
//   Lane -> direction (one lane on one direction): default lanes 0..2 arrive on A, lane 3 on B; +lmap=1: lane 0 on A,
//   lanes 1..3 on B.  Each lane word is queued when the bench drives it; a word with data[499:256] == 0 and no fault
//   crosses as one single beat, every other word as part 0 + part 1 (next ingress slot of that direction).
// Checks (WRAP_ERR lines): every through beat leaves the other side unchanged and in order (exact cycle: 2 edges);
// egress beats only in their window, well formed (part 0, part 1 in turn, type/tag copy); the unit's fault pin stays 0.
// ---------------------------------------------------------------------------------------------------------------------
module tb_dsdv_bk_wrap #(
    parameter integer UNIT = 0,           // 0 dsdv_bk_sel, 1 dsdv_bk_col
    parameter integer MUT  = 0
) (
    input  wire         ck,
    input  wire         rst,              // active low
    input  wire [514:0] l0, l1, l2, l3,   // SW, SE, NW, NE
    output reg  [513:0] vd,
    output wire         vf
);
    localparam integer V = 276, LW = 7;
`ifdef OT_DSDV_BK_LP
    // PL-BK 10-18: the LANDED selector dsdv_bk_sel_x_lp (lp.py; record results/arch/landed_parent_1018/dsdv_bk_sel_x):
    // the rung relays sit in their own clock regions and land into the core region (+3 edges per direction on top of
    // the relay's +1); the whole core calendar (glue, quarters, control) moves +3 with the rung, so RL = 1 + 3
    localparam integer RL = (UNIT == 0) ? 4 : 0;
`else
    localparam integer RL = (UNIT == 0) ? 1 : 0;
`endif   // S81-TILES8/bk 10-18: dsdv_bk_sel rung relays u_rs / u_rn = +1 rung
                                                   // cycle per direction (through beats and the drain CTL alike)
    localparam [2:0] IK = 3'd4, EK = 3'd5;
    localparam [7:0] UID = 8'h5B;
    assign vf = 1'b0;
    bit thru, mir, oddw; int lmap; int wn_n, wn_d, refill;
    bit thr_on; int tok;                  // ingress throttle (the compiler's rate match to the drain windows), in words
    bit fullrate; int nfr = 0;            // +fullrate: S81U-BK's refill = the drain capacity exactly (2 / 4 words per
                                          // frame: 100% window use, so every window the frame-atomic merger leaves empty
                                          // is a permanent backlog: overflow depends on a cycle of latency).  Default
                                          // (S81U-BK2): the collector's ingress is matched to 7/8 of the drain capacity
                                          // (one word less every 8th frame); the selector reduces, its refill is unchanged
    int  side [0:3];                     // 0 = arrives on A (vi_a), 1 = on B
    initial begin
        thru = $test$plusargs("thru"); mir = $test$plusargs("mir"); oddw = $test$plusargs("oddwin");
        wn_n = (thru ? 4 : 8) - (oddw ? 1 : 0); wn_d = thru ? 5 : 1; refill = wn_n / 2;   // refill = drain capacity
        thr_on = !$test$plusargs("nothrottle"); fullrate = (UNIT == 0) || $test$plusargs("fullrate");
        if (!$value$plusargs("lmap=%d", lmap)) lmap = 0;
        for (int l = 0; l < 4; l++) side[l] = (lmap == 1) ? (l == 0 ? 0 : 1) : (l == 3 ? 1 : 0);
        tok = 64;
    end

    // ---------------- the unit
    reg  [V-1:0] vi_a, vi_b; wire [V-1:0] vo_a, vo_b, vi_s, vi_n, vo_s, vo_n; wire fault;
    assign vi_s = mir ? vi_b : vi_a; assign vi_n = mir ? vi_a : vi_b;
    assign vo_a = mir ? vo_n : vo_s; assign vo_b = mir ? vo_s : vo_n;
    generate if (UNIT == 0) begin : g_sel
`ifdef OT_DSDV_BK_LP
        dsdv_bk_sel_x_lp #(.MUT(0)) u_u (.ck_core(ck), .ck_rs(ck), .ck_rn(ck), .rst_n(rst),
`else
        dsdv_bk_sel #(.MUT(MUT)) u_u (.clk(ck), .rst_n(rst),
`endif .tap_k(8'h11), .sink_k(8'h10), .ik(IK), .ek(EK), .uid(UID),
            .eg_n(mir), .vi_s(vi_s), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .fault(fault));
    end else begin : g_col
        dsdv_bk_col #(.MUT(MUT)) u_u (.clk(ck), .rst_n(rst), .tap_k(8'h11), .sink_k(8'h10), .ik(IK), .ek(EK), .uid(UID),
            .eg_n(mir), .vi_s(vi_s), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .fault(fault));
    end endgenerate

    // ---------------- producer
    int cyc = 0;
    int rst_hi = 0, wi = 0;               // last cycle with reset low; window cursor
    always @(posedge ck) if (!rst) rst_hi <= cyc;
    typedef struct { bit [511:0] d; bit f; } lw_t;
    lw_t q [0:3][$];
    int  pend_l [0:1]; lw_t pend [0:1]; bit pend_v [0:1]; int rr [0:1];
    bit [V-1:0] fwd_a [$], fwd_b [$];    // expected forwards, per output side, by cycle (index = cycle)
    int  win_lo [$], win_hi [$];         // egress windows on vo_a, in cycles
    int  n_thru = 0, n_in = 0, n_ctl = 0, n_eg = 0, errs = 0;
    function automatic bit [V-1:0] rnd();
        bit [V-1:0] x; for (int i = 0; i < V; i += 32) x[i +: 32] = $urandom; return x;
    endfunction
    function automatic bit [V-1:0] bk_beat(int l, lw_t w, int part, bit single);
        bit [V-1:0] b;
        b = '0; b[0] = 1; b[3:1] = IK; b[5:4] = l; b[6] = part; b[7] = single;
        if (part == 0) begin b[19:8] = w.d[511:500]; b[275:20] = w.d[255:0]; end
        else begin b[8] = w.f; b[275:20] = w.d[511:256]; end
        return b;
    endfunction
    // next ingress beat of side s (or 0)
    // (tasks with an output, not functions: side effects must happen only on the taken branch)
    task automatic ingress(input int s, output bit [V-1:0] o);
        int l; lw_t w; bit done;
        o = '0; done = 0;
        if (pend_v[s]) begin pend_v[s] = 0; n_in++; o = bk_beat(pend_l[s], pend[s], 1, 0); done = 1; end
        for (int k = 0; k < 4; k++) begin
            l = (rr[s] + k) % 4;
            if (!done && side[l] == s && q[l].size() > 0 && (!thr_on || tok > 0)) begin
                tok--; done = 1;
                w = q[l].pop_front();
                rr[s] = (l + 1) % 4;
                if (w.d[499:256] == 0 && !w.f) begin n_in++; o = bk_beat(l, w, 0, 1); end
                else begin pend_v[s] = 1; pend_l[s] = l; pend[s] = w; o = bk_beat(l, w, 0, 0); end
            end
        end
    endtask
    int xq_left [0:1];
    task automatic through(input int s, input int slot, output bit [V-1:0] b);
        int r;
        b = rnd();
        if (xq_left[s] > 0) xq_left[s]--;                                // XQ / XB continuation fragment (raw)
        else begin
            r = $urandom % 6;
            if (r == 0) b = '0;
            else if ((r == 1 || r == 2) && slot == 0 && s == 1) begin b[0] = 1; b[3:1] = 1 + $urandom % 2; xq_left[s] = 3; end
            else if (r <= 2) begin b[0] = 1; b[3:1] = 3; end
            else if (r == 3) begin b[0] = 1; b[3:1] = 6; end
            else if (r == 4) begin b[0] = 1; b[3:1] = 0; b[28:21] = UID ^ 8'(1 + $urandom % 255); end   // foreign CTL
            else begin b[0] = 1; b[3:1] = 7; end
        end
    endtask

    always @(posedge ck) begin
        if (!rst) begin
            for (int l = 0; l < 4; l++) q[l].delete();
            pend_v[0] = 0; pend_v[1] = 0; xq_left[0] = 0; xq_left[1] = 0;
        end else begin
            if (l0[0]) q[0].push_back('{l0[512:1], l0[514]});
            if (l1[0]) q[1].push_back('{l1[512:1], l1[514]});
            if (l2[0]) q[2].push_back('{l2[512:1], l2[514]});
            if (l3[0]) q[3].push_back('{l3[512:1], l3[514]});
        end
    end
    // drive the rung (after the edge; the unit samples at the next edge)
    always @(posedge ck) begin
        int slot; bit [V-1:0] a, b;
        slot = cyc % 8;
        a = '0; b = '0;
        if (rst && cyc > 40 && cyc > rst_hi + 8) begin
            if (slot == 0) begin nfr++; tok = (tok + refill - ((!fullrate && nfr % 8 == 0) ? 1 : 0) > 64) ? 64 : tok + refill - ((!fullrate && nfr % 8 == 0) ? 1 : 0); end
            // A side arrivals: slot 0 = the drain CTL for the next frame's window; through singles (+thru, 1..3); ingress
            if (slot == 0) begin
                a[0] = 1; a[3:1] = 0; a[8:4] = $urandom; a[12:9] = $urandom; a[28:21] = UID; a[31:29] = 1;
                a[39:32] = 8'(wn_n); a[47:40] = 8'(wn_d);
                // window (arrival index; the unit's LW = 7: CTL vo edge + 7 + d = first window vo edge)
                win_lo.push_back(cyc + LW + wn_d); win_hi.push_back(cyc + LW + wn_d + wn_n - 1);
                n_ctl++;
            end else if (thru && slot < 4) through(0, slot, a);
            else ingress(0, a);
            // B side arrivals: through (+thru, 0..3: XQ / XB from slot 0, singles); ingress
            if (thru && slot < 4) through(1, slot, b); else ingress(1, b);
        end
        vi_a <= a; vi_b <= b;
`ifdef OT_DSDV_BK_TRACE
        if (cyc < 120 && (a[0] || b[0])) $display("WRAP_DRV cyc %0d slot %0d a %h b %h", cyc, slot, a[19:0], b[19:0]);
`endif
        // expected forwards: what arrives at cycle cyc+1 (vi visible) leaves 2 edges later
        // COORD ruling 10-24 18:55: the BK addressed-drain sink is canonical (ot_dsdv_vstop BK_DRAIN_SINK=1): the slot-0
        // drain CTL (kind 0, uid UID, op 1) is consumed by the unit's stop and NOT forwarded to B.  The retired legacy
        // expectation (transparent forwarding, records up to 10-24) is kept under +define+OT_DSDV_BK_LEGACY_FWD.
`ifdef OT_DSDV_BK_LEGACY_FWD
        fwd_b.push_back((slot == 0 || (thru && slot < 4)) ? a : '0);   // ingress beats are sunk
`else
        fwd_b.push_back((thru && slot < 4 && slot != 0) ? a : '0);     // ingress beats and the addressed drain are sunk
`endif
        fwd_a.push_back((thru && slot < 4) ? b : '0);
        cyc <= cyc + 1;
    end

    // ---------------- egress collector + checks
    bit [255:0] e_lo; bit [11:0] e_tt; bit e_half = 0;
    always @(posedge ck) begin
        vd <= {512'd0, 1'b0, 1'b1};
        if (rst && cyc > 40) begin
            // vo at this edge corresponds to arrivals driven 3 (+RL) posedges ago (driven at edge k -> visible -> vo after
            // 2 more, + RL rung relay stages; the window moves with the CTL, so window checks use the same k)
            int k; k = cyc - 3 - RL;
            if (k > rst_hi + 3 && k < fwd_a.size()) begin : g_chk
                bit [V-1:0] ea, eb; bit inwin;
                ea = fwd_a[k]; eb = fwd_b[k];
                if (vo_b !== eb) begin errs++; if (errs < 10) $display("WRAP_ERR forward B cyc %0d got %h exp %h", cyc, vo_b[15:0], eb[15:0]); end
                if (eb != 0) n_thru++;
                inwin = 0;
                while (wi < win_hi.size() && win_hi[wi] < k) wi++;
                if (wi < win_lo.size() && k >= win_lo[wi] && k <= win_hi[wi]) inwin = 1;
                if (ea != 0) begin
                    if (vo_a !== ea) begin errs++; if (errs < 10) $display("WRAP_ERR forward A cyc %0d got %h exp %h", cyc, vo_a[15:0], ea[15:0]); end
                    n_thru++;
                end else if (vo_a[0]) begin
                    if (vo_a[3:1] != EK) begin errs++; if (errs < 10) $display("WRAP_ERR stray beat on A cyc %0d %h", cyc, vo_a[15:0]); end
                    else begin
                        if (!inwin) begin errs++; if (errs < 10) $display("WRAP_ERR egress outside its window cyc %0d", cyc); end
                        if (vo_a[6] != e_half) begin errs++; if (errs < 10) $display("WRAP_ERR egress part order cyc %0d", cyc); end
                        if (!vo_a[6]) begin e_lo = vo_a[275:20]; e_tt = vo_a[19:8]; e_half = 1; end
                        else begin
                            if (vo_a[275:264] != e_tt) begin errs++; if (errs < 10) $display("WRAP_ERR egress type/tag copy cyc %0d", cyc); end
                            vd <= {vo_a[275:20], e_lo, 1'b1, 1'b1};
                            e_half = 0; n_eg++;
                        end
                    end
                end
            end
            if (fault) begin errs++; if (errs < 10) $display("WRAP_ERR unit fault pin cyc %0d", cyc); end
        end
        if (!rst) e_half = 0;
    end
    bit f_seen = 0;
`ifdef OT_DSDV_BK_COLB
    generate if (UNIT == 1) begin : g_dbg
        always @(posedge ck) if (fault && !f_seen) begin f_seen = 1;
            $display("WRAP_DBG fault cyc %0d vstop %0d vin %0d vout %0d", cyc, g_col.u_u.u_g.vs_f, g_col.u_u.u_g.vi_f, g_col.u_u.u_g.vo_f); end
    end endgenerate
`else
    generate if (UNIT == 0) begin : g_dbg0
        always @(posedge ck) if (fault && !f_seen) begin f_seen = 1;
            $display("WRAP_DBG fault cyc %0d vstop %0d vin %0d vout %0d", cyc, g_sel.u_u.u_g.vs_f, g_sel.u_u.u_g.vi_f, g_sel.u_u.u_g.vo_f); end
    end endgenerate
`endif
    final $display("WRAP_SUMMARY unit %0d thru %0d mir %0d lmap %0d: through beats %0d, ingress words %0d, drain CTL %0d, egress words %0d, errors %0d",
                   UNIT, thru, mir, lmap, n_thru, n_in, n_ctl, n_eg, errs);
endmodule
