`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// MU-S81/HOST (2026-10-18, MU.S81.BUF host part (a)): dsdv_mu_hslot -- the S81 host plane's static outstanding-token
// slot table, a NEW small leaf beside dsdv_seq_host's L0 (dsdv_sh_lk), and dsdv_seq_host_mu, the unit wrapper that
// instantiates it.  No existing file changes: dsdv_seq_host.sv and every leaf in it (sh_lk, sh_sq, sh_vc CLOSED, sh_ft)
// and dsfd_host_native / dsfd_host_sd (CLOSED) are untouched, byte-identical.
//
// Multi-user = STATIC shift calendar (owner MU.DECIDE option A): user k runs the single-user schedule shifted by k slots
// of S cycles (S = 20,753 AR / 47 users, or the MTP slot / 10 users).  The host plane takes one start {user, tok, pos}
// a slot on f_ks and returns each start's next token on t_kd a FIXED RL edges later (RL = the compiled start -> KIT
// latency of the position, the same for every user, because each user's schedule is the same schedule shifted).
// Today t_kd = {done, tok 21, 32'b0} carries no user: one start / one return a step (single user).  This leaf:
//   * taps the start pin f_ks (it captures the same pin the unit's sh_lk pin flop captures, on the same edge) and keeps
//     a slot table of NSLOT entries {user 10, pos 21, due}: slot index = the calendar slot of the start, from a slot
//     timer (period S, armed by the first start; a start must fall on a slot boundary, phase 0);
//   * emits t_ku = {v, user 10, pos 21} of the start whose return is due, on EXACTLY the edge the unit drives that
//     return's t_kd done (it knows the due edge in advance: static schedule), so the wrapper's t_kd =
//     {done, tok 21, user 10, pos 21, 1'b0} -- the 32 spare zero bits -- with NO added latency on any user's start or
//     return path (user 0 / every user cycle-identical to single-user);
//   * checks one edge later that the unit's t_kd done really arrived on that edge (a missing, early, late or extra
//     return is a fault).  The next-token return message on the host lane (133.5 cycles a return, off the critical
//     path) carries {tok, user, pos}; the host PHY lane block is the only elastic face.
// No queue with ready, no credit, no stall: a start into an occupied slot (two users in one slot = compiler error) is a
// sticky fault and is NOT recorded; nothing is rescheduled.
// Faults t_mf (sticky): [0] slot collision (start into an occupied slot), [1] off-calendar start (not at slot phase 0)
// or the user already outstanding, [2] return mismatch (t_kd done without an announced return or vice versa), [3] config
// (f_mc while armed / outstanding, no gap or a gap < nw, RL <= nw at the first start, more than NSLOT gaps, or RL - 1 >=
// the calendar period (HSLOT2); nw = the slot entries in use, NSLOT for one gap word, else the gap count -- MU-S81-2/SEQ).
// Boot config f_mc = {v, sel, d 24} (host lane block CSR, boot only): sel 0 = slot gap (cycles; one word = uniform period
// S, n words = the gap table g[0..n-1] of a non-uniform calendar, MU-S81-2/SEQ), sel 1 = RL (edges
// from the f_ks capture edge to the t_kd pin edge).  Return order = start order (same RL for every start): HSLOT2 walks
// the gap table a second time RL - 1 edges behind (return slot timer), see the module body.
// Timing: f_ks / f_kd / f_mc land in pin flops; t_ku / t_mf leave flops.  Single clock ck (stream), ot_rst_relay.
// Area (NSLOT 47, HSLOT2): 47 x {user 10, pos 21, gap 24} flops + 47 10-b user compares + ~400 control / pointer /
// kept-copy flops ~ 3.0k flops.
// NSLOT = 1 (default of dsdv_seq_host_mu): the leaf is not instantiated, t_kd / every pin = dsdv_seq_host exactly.
// MUT (bench negative controls): 1 user field dropped from t_ku (user 0 on every return), 2 slot-collision check
// dropped (the occupied entry is overwritten, no fault), 5 gap table index stuck at 0 (uniform g[0] slots).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_mu_hslot #(parameter integer NSLOT = 47, parameter integer MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [52:0]   f_ks,            // tap of the unit start pin {start, user 10, tok 21, pos 21}
    input  wire [53:0]   f_kd,            // tap of the unit t_kd {done, tok 21, 32'b0}
    input  wire [25:0]   f_mc,            // boot config {v, sel, d 24}
    output reg  [31:0]   t_ku,            // {v, user 10, pos 21}: same edge as the unit's t_kd done
    output reg  [3:0]    t_mf             // sticky faults
);
    // MU-S81-2/HSLOT2 (10-19, safe-design checklist): structural re-design of the table, same pins / boot words /
    // t_ku edge / faults.  (a) No per-entry due field and no return pointer: return order = start order and RL is the
    // same for every start, so the returns follow a SECOND walk of the same slot gap table started RL - 1 edges after
    // the arming start (return timer); return slot k's boundary is exactly start slot k's boundary + RL - 1, i.e. every
    // recorded start's due edge.  The 47 x 32 b due table, the 32 b edge counter, the 47:1 x 32 b compare and the
    // sweep pointer rp (3,007 loads) are gone.  Needs RL - 1 < the calendar period (an AR user's next start waits for
    // its return, so this always holds on a valid calendar; RL - 1 >= period raises t_mf[3] on the slot-0 wrap edge).
    // (b) Every pointer is a registered ONE-HOT vector (start slot sl, return slot rn, gap read gx / rgx, gap write
    // gw): each pointer bit enables only its own entry (<= 32 loads), reads are AND-OR trees into REGISTERS (ng / rng
    // gap prefetch, rq = the entry of the next return boundary, loaded every edge: a write lands >= 2 edges before its
    // return because RL > nw >= 2).  (c) The start payload {user, pos} and the gap word land in KEPT pin-flop copies,
    // one per <= 16 entries (payload) / <= 24 entries (gap), so no register drives more than ~32 loads.
    // Historical HSLOT2 tables (before the SRAM change; written only at a start / at boot, read only through the registered one-hot reads above): user
    // 47 x 10 b (also the outstanding-user compare), pos 47 x 21 b, gap 47 x 24 b = 2.6 kb (was 4.1 kb + a 32 b timer).
    // Schedule: zero added cycles on any pin path; t_ku leaves its flop on the same edge as before.
    localparam integer SI = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    localparam integer SJ = SI + 1;
    localparam integer NG = (NSLOT + 15) / 16;           // payload copies (<= 16 entries each)
    localparam integer NC = (NSLOT + 23) / 24;           // gap word copies (<= 24 entries each)
    localparam [NSLOT-1:0] ONE = {{(NSLOT-1){1'b0}}, 1'b1};
    localparam [NSLOT-1:0] LAST = {1'b1, {(NSLOT-1){1'b0}}};
`ifndef SYNTHESIS
    initial if (NSLOT < 2 || NSLOT > 512) $fatal(1, "dsdv_mu_hslot: NSLOT must be 2..512 (NSLOT 1 = leaf absent)");
`endif
    // three reset regions (<= ~250 flops each): rn_ = control scalars + pin gating, rs_ = start-side one-hot vectors,
    // rt_ = return side (timer, return pointers, valid bits, t_ku)
    wire [2:0] rr; ot_rst_relay #(.REGIONS(3)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    wire rn_ = rr[0], rs_ = rr[1], rt_ = rr[2];
    // ---- pin flops (valid bits held low by the relayed reset, payload not); payload / gap word in kept copies
    reg st_q, kd_q, mv_q, ms_q;
    (* keep *) reg [31*NG-1:0] kp_q;                     // NG x {user 10, pos 21}
    (* keep *) reg [24*NC-1:0] md_q;                     // NC x gap / RL word
    always @(posedge ck) begin
        ms_q <= f_mc[24]; kp_q <= {NG{f_ks[51:42], f_ks[20:0]}}; md_q <= {NC{f_mc[23:0]}};
    end
    always @(posedge ck or negedge rn_)                 // valid bits: reset-held low
        if (!rn_) begin st_q <= 1'b0; kd_q <= 1'b0; mv_q <= 1'b0; end
        else begin st_q <= f_ks[52]; kd_q <= f_kd[53]; mv_q <= f_mc[25]; end
    wire [23:0] md = md_q[23:0];
    // ---- state
    reg [23:0] cs, crl; reg armed; reg [23:0] ph, cg, ng; reg kv_d;
    reg [NSLOT-1:0] sl, gx, gw, gwo, lwo; reg [SI-1:0] slb, rnb; reg [SJ-1:0] gn; reg [SI-1:0] lw;
    reg rpend, rarmed; reg [23:0] rc, rph, rcg, rng; reg [NSLOT-1:0] rn, rgx;
    reg [NSLOT-1:0] vld; reg [10*NSLOT-1:0] eu; reg [24*NSLOT-1:0] gt;   // gt holds gap - 1
    reg rq_v; reg [30:0] rq;
    function automatic [NSLOT-1:0] onx(input [NSLOT-1:0] p, input [NSLOT-1:0] last);   // one-hot next, wrap at last
        onx = (|(p & last)) ? ONE : {p[NSLOT-2:0], 1'b0};
    endfunction
    // ---- start side: the start's calendar slot is sl (slot 0 before arming)
    wire on_cal = !armed || ph == 24'd0;
    wire col = |(vld & sl);
    reg udup; reg [23:0] ngd, rngd; reg [30:0] rqd; integer i;
    always @* begin
        udup = 1'b0; ngd = 24'd0; rngd = 24'd0; rqd = 31'd0;
        for (i = 0; i < NSLOT; i = i + 1) begin
            if (vld[i] && eu[10*i +: 10] == kp_q[31*(i/16) + 21 +: 10]) udup = 1'b1;
            ngd  = ngd  | ({24{gx[i]}}  & gt[24*i +: 24]);
            rngd = rngd | ({24{rgx[i]}} & gt[24*i +: 24]);
            rqd  = rqd  | ({31{rn[i]}}  & {eu[10*i +: 10], 21'd0});
        end
    end
    wire [23:0] nw = {{(23-SI){1'b0}}, lw} + 24'd1;     // slot entries in use
    wire cfg_bad = gn == {SJ{1'b0}} || cs < nw || crl <= nw;
    wire m2c = MUT == 2 && col;                          // MUT 2: the collision (and the dup it implies) goes unchecked
    wire rec = st_q && on_cal && ((!col && !udup) || m2c) && !(!armed && cfg_bad);    // the start is recorded
    wire arm = st_q && !armed && !cfg_bad;
    wire gwr = mv_q && !ms_q && !armed && !(|vld) && gn != SJ'(NSLOT);              // boot gap word write
    wire [NSLOT-1:0] gxn  = (MUT == 5 || |(gx & gwo))  ? ONE : {gx[NSLOT-2:0], 1'b0};  // MUT 5: gap index stuck at 0
    wire [NSLOT-1:0] rgxn = (MUT == 5 || |(rgx & gwo)) ? ONE : {rgx[NSLOT-2:0], 1'b0};
    // ---- return side: boundary of return slot rn (rarm = slot 0's, RL - 1 edges after the arming start)
    wire rarm = rpend && rc == 24'd1;
    wire rb = rarm || (rarmed && rph == 24'd0);
    wire ret = rb && rq_v;
    always @(posedge ck) begin                          // registered reads (data, no reset)
        ng <= ngd; rng <= rngd; rq <= rqd; rq_v <= |(vld & rn);
    end
    // Position payload is the sole dense return-only table.  A registered SRAM read replaces its
    // registered one-hot read exactly; user IDs remain parallel for duplicate detection.  WREG
    // forwards the write from the preceding edge; RL > nw leaves the normal write ample slack.
    // Binary shadows track the one-hot slot walks, so no combinational pointer encoder feeds SRAM.
    wire [20:0] posq;
    ot_s81ph_mem1r1w #(.W(21), .DEPTH(NSLOT), .SRAM(1), .WREG(1)) u_pos (
        .clk(ck), .rst_n(rn_), .we(rec), .wa(slb), .wd(kp_q[20:0]),
        .re(1'b1), .ra(rnb), .q(posq));
    genvar k;
    generate for (k = 0; k < NSLOT; k = k + 1) begin : g_e
        always @(posedge ck) begin                      // entry payload: written at its start / boot word only
            if (rec && sl[k]) begin eu[10*k +: 10] <= kp_q[31*(k/16) + 21 +: 10]; end
            if (gwr && gw[k]) gt[24*k +: 24] <= md_q[24*(k/24) +: 24] - 24'd1;
        end
    end endgenerate
    wire sadv = armed && ph == cg;                       // start slot timer: gap end
    // ---- region rn_: control scalars and faults
    always @(posedge ck or negedge rn_)
        if (!rn_) begin
            armed <= 1'b0; ph <= 24'd0; cg <= 24'd0; gn <= {SJ{1'b0}}; lw <= SI'(NSLOT - 1); cs <= 24'd0; crl <= 24'd0;
            kv_d <= 1'b0; t_mf <= 4'd0;
        end else begin
            // boot config
            if (mv_q) begin
                if (armed || |vld) t_mf[3] <= 1'b1;
                else if (ms_q) crl <= md;
                else if (gn == SJ'(NSLOT)) t_mf[3] <= 1'b1;                          // more gaps than slots
                else begin
                    gn <= gn + 1'b1;
                    if (gn == {SJ{1'b0}} || md < cs) cs <= md;
                    lw <= (gn == {SJ{1'b0}}) ? SI'(NSLOT - 1) : gn[SI-1:0];        // nw = n for n >= 2
                end
            end
            // start slot timer: phase of the current edge, slot advanced at the gap end
            if (armed) begin
                if (sadv) begin ph <= 24'd0; cg <= ng; end else ph <= ph + 24'd1;
                if (ph == 24'd0 && sl[0] && !rarmed) t_mf[3] <= 1'b1;                // RL - 1 >= calendar period
            end
            if (st_q) begin
                if (!armed && cfg_bad) t_mf[3] <= 1'b1;
                if (col && MUT != 2) t_mf[0] <= 1'b1;                            // (a slot collision is also a user dup)
                else if (!on_cal || (udup && !m2c)) t_mf[1] <= 1'b1;
            end
            if (arm) begin armed <= 1'b1; ph <= 24'd1; cg <= ng; end
            // the unit's done must land on exactly the edge t_ku announced
            kv_d <= t_ku[31];
            if (kd_q != kv_d) t_mf[2] <= 1'b1;
        end
    // ---- region rs_: start-side one-hot vectors
    always @(posedge ck or negedge rs_)
        if (!rs_) begin
            slb <= SI'(0); sl <= ONE; gx <= ONE; gw <= ONE; gwo <= ONE; lwo <= LAST;
        end else begin
            if (gwr) begin gw <= {gw[NSLOT-2:0], 1'b0}; gwo <= gw; lwo <= (gn == {SJ{1'b0}}) ? LAST : gw; end
            if (sadv) begin slb <= slb == lw ? SI'(0) : slb + 1'b1; sl <= onx(sl, lwo); gx <= gxn; end
            if (arm) gx <= gxn;
        end
    // ---- region rt_: return slot timer (the same gap walk, RL - 1 edges behind), valid bits, t_ku
    always @(posedge ck or negedge rt_)
        if (!rt_) begin
            rpend <= 1'b0; rarmed <= 1'b0; rc <= 24'd0; rph <= 24'd0; rcg <= 24'd0; rn <= ONE; rgx <= ONE;
            rnb <= SI'(0); vld <= {NSLOT{1'b0}}; t_ku <= 32'd0;
        end else begin
            if (arm) begin rpend <= 1'b1; rc <= crl - 24'd1; end
            if (rpend) begin
                rc <= rc - 24'd1;
                if (rc == 24'd1) begin rpend <= 1'b0; rarmed <= 1'b1; rph <= 24'd1; rcg <= rng; rgx <= rgxn; end
            end
            if (rarmed) begin
                if (rph == rcg) begin rph <= 24'd0; rcg <= rng; rgx <= rgxn; end else rph <= rph + 24'd1;
            end
            // return of the start recorded in slot rn, on its due edge (rq = that entry, read the edge before)
            t_ku <= 32'd0;
            if (rb) begin rn <= onx(rn, lwo); rnb <= rnb == lw ? SI'(0) : rnb + 1'b1; end
            if (ret) t_ku <= {1'b1, (MUT == 1) ? 10'd0 : rq[30:21], posq};
            vld <= (vld & ~(ret ? rn : {NSLOT{1'b0}})) | (rec ? sl : {NSLOT{1'b0}});
        end
endmodule

// ---------------------------------------------------------------- the unit with the multi-user host slot table
// NSLOT 1 (default): dsdv_seq_host exactly (t_ku / t_mf tied 0, f_mc unused).  NSLOT > 1: t_kd's 32 spare zero bits
// carry {user, pos, 0} of the returning start; t_mf goes to the die status fold beside t_host.
module dsdv_seq_host_mu #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0,
                          parameter integer NSLOT = 1, parameter integer MU_MUT = 0,
                          parameter integer SELR = 0) (            // S81/H23: SEL relay in L0 (dsdv_sh_selr)
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    input  wire [25:0]   f_mc,   output wire [3:0]  t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d
);
    wire [53:0] kd;
    dsdv_seq_host #(.V(V), .STAGE(STAGE), .MUT(MUT), .SELR(SELR)) u_u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks),
        .t_kd(kd), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w),
        .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    generate if (NSLOT > 1) begin : g_mu
        wire [31:0] ku;
        dsdv_mu_hslot #(.NSLOT(NSLOT), .MUT(MU_MUT)) u_hs (.ck(ck), .rst_n(rst_n), .f_ks(f_ks), .f_kd(kd), .f_mc(f_mc),
            .t_ku(ku), .t_mf(t_mf));
        assign t_kd = {kd[53:32], ku[30:0], 1'b0};      // kd[31:0] = 0 by the unit's contract (sh_sq kd_o)
    end else begin : g_su
        assign t_kd = kd; assign t_mf = 4'd0;
    end endgenerate
endmodule
