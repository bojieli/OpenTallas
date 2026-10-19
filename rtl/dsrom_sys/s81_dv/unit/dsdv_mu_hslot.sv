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
// or the user already outstanding, [2] return mismatch (t_kd done without a due entry or vice versa, or an entry past
// its due edge), [3] config (f_mc while armed / outstanding, no gap or a gap < nw, RL <= nw at the first start, or more
// than NSLOT gaps; nw = the slot entries in use, NSLOT for one gap word, else the gap count -- MU-S81-2/SEQ).
// Boot config f_mc = {v, sel, d 24} (host lane block CSR, boot only): sel 0 = slot gap (cycles; one word = uniform period
// S, n words = the gap table g[0..n-1] of a non-uniform calendar, MU-S81-2/SEQ), sel 1 = RL (edges
// from the f_ks capture edge to the t_kd pin edge).  Return order = start order (same RL for every start), so the
// return pointer rp only stops on valid entries and sweeps empty ones one an edge (needs RL > nw, checked).
// Timing: f_ks / f_kd / f_mc land in pin flops; t_ku / t_mf leave flops.  Single clock ck (stream), ot_rst_relay.
// Area (NSLOT 47): 47 x 63 b entry flops + 47 10-b user compares + ~110 control flops ~ 3.9k flops; modelled
// ~0.004 mm^2 (design study item 6: 0.001 mm^2 for the field alone).
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
    localparam integer SI = (NSLOT > 1) ? $clog2(NSLOT) : 1;
    localparam integer SJ = SI + 1;
`ifndef SYNTHESIS
    initial if (NSLOT < 2 || NSLOT > 1023) $fatal(1, "dsdv_mu_hslot: NSLOT must be 2..1023 (NSLOT 1 = leaf absent)");
`endif
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); wire rn = rr[0];
    // ---- pin flops (valid bits gated by the relayed reset, payload not)
    reg [52:0] ks_q; reg kd_q; reg [25:0] mc_q;
    always @(posedge ck) begin
        ks_q <= {rn & f_ks[52], f_ks[51:0]}; kd_q <= rn & f_kd[53]; mc_q <= {rn & f_mc[25], f_mc[24:0]};
    end
    wire st = ks_q[52]; wire [9:0] su = ks_q[51:42]; wire [20:0] sp = ks_q[20:0];
    // ---- state
    reg [23:0] cs, crl; reg [31:0] tm; reg armed; reg [23:0] ph; reg [SI-1:0] sl, rp; reg kv_d;
    // MU-S81-2/SEQ (10-19): slot gap table.  The record calendar (dv_mu_calendar --phase-q 4) has NON-uniform slots
    // (AR 46: shift_k = 4 floor(k (P/4) / 46) -> gaps 21,312 / 21,316; MTP 10 + filler: 10 x 124,524 then 58,160), so
    // one period S cannot hold it (user 3's start lands 4 edges off a uniform 21,312 grid -> t_mf[1] on the real unit).
    // Each sel-0 word APPENDS one slot gap g[k] (cycles from slot k's start edge to slot k+1's); the slot timer walks
    // g[0..n-1] cyclically (n = words written), and the slot entries wrap at nw = n (n >= 2) so the entry index IS the
    // calendar slot.  One sel-0 word (n = 1) = the former uniform period S with nw = NSLOT: the previous behaviour.
    // cs = the smallest gap.
    reg [23:0] gt [0:NSLOT-1]; reg [SI:0] gn; reg [SI-1:0] gx, lw; reg [23:0] cg, ng;
    reg [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1]; reg [31:0] ed [0:NSLOT-1];
    wire [SI-1:0] ss = armed ? sl : {SI{1'b0}};          // the start's calendar slot
    wire on_cal = !armed || ph == 24'd0;
    reg udup; integer i;
    always @* begin udup = 1'b0; for (i = 0; i < NSLOT; i = i + 1) if (vld[i] && eu[i] == su) udup = 1'b1; end
    wire col = vld[ss];
    wire [23:0] nw = {{(23-SI){1'b0}}, lw} + 24'd1;     // slot entries in use
    wire cfg_bad = gn == 0 || cs < nw || crl <= nw;
    wire m2c = MUT == 2 && col;                          // MUT 2: the collision (and the dup it implies) goes unchecked
    wire rec = st && on_cal && ((!col && !udup) || m2c) && !(!armed && cfg_bad);    // the start is recorded
    wire [31:0] rd = ed[rp];
    wire hit = vld[rp] && rd == tm;
    wire late = vld[rp] && rd != tm && rd - tm > 32'h7fffffff;                     // due edge already passed
    function automatic [SI-1:0] nxt(input [SI-1:0] p);
        nxt = (p == lw) ? {SI{1'b0}} : p + 1'b1;
    endfunction
    wire [SI-1:0] gxn = (MUT == 5 || {1'b0, gx} == gn - 1'b1) ? {SI{1'b0}} : gx + 1'b1;   // MUT 5: gap table index stuck at 0
    always @(posedge ck) ng <= gt[gx] - 24'd1;          // next slot's gap, prefetched (gx = the slot after the current one)
    always @(posedge ck) if (mc_q[25] && !mc_q[24] && !armed && !(|vld) && gn != SJ'(NSLOT)) gt[gn[SI-1:0]] <= mc_q[23:0];
    always @(posedge ck or negedge rn)
        if (!rn) begin
            tm <= 32'd0; armed <= 1'b0; ph <= 24'd0; sl <= {SI{1'b0}}; rp <= {SI{1'b0}}; vld <= {NSLOT{1'b0}};
            t_ku <= 32'd0; kv_d <= 1'b0; t_mf <= 4'd0; cs <= 24'd0; crl <= 24'd0;
            gn <= {SJ{1'b0}}; gx <= {SI{1'b0}}; lw <= SI'(NSLOT - 1); cg <= 24'd0;
        end else begin
            tm <= tm + 32'd1;
            // boot config
            if (mc_q[25]) begin
                if (armed || |vld) t_mf[3] <= 1'b1;
                else if (mc_q[24]) crl <= mc_q[23:0];
                else if (gn == SJ'(NSLOT)) t_mf[3] <= 1'b1;                          // more gaps than slots
                else begin
                    begin
                        gn <= gn + 1'b1;
                        if (gn == 0 || mc_q[23:0] < cs) cs <= mc_q[23:0];
                        lw <= (gn == 0) ? SI'(NSLOT - 1) : gn[SI-1:0];             // nw = n for n >= 2
                    end
                end
            end
            // slot timer: phase of the current edge, slot index advanced at the period wrap
            if (armed) begin
                if (ph == cg) begin ph <= 24'd0; sl <= nxt(sl); cg <= ng; gx <= gxn; end else ph <= ph + 24'd1;
            end
            // start: record in its slot, or fault (never queued, never retried)
            if (st) begin
                if (!armed) begin
                    if (cfg_bad) t_mf[3] <= 1'b1;
                    else begin armed <= 1'b1; ph <= 24'd1; cg <= ng; gx <= gxn; end     // slot 0 = g[0]
                end
                if (col && MUT != 2) t_mf[0] <= 1'b1;                            // (a slot collision is also a user dup)
                else if (!on_cal || (udup && !m2c)) t_mf[1] <= 1'b1;
            end
            // return of the oldest outstanding start, on its due edge
            t_ku <= 32'd0;
            if (hit) begin
                t_ku <= {1'b1, (MUT == 1) ? 10'd0 : eu[rp], ep[rp]};
                vld[rp] <= 1'b0; rp <= nxt(rp);
            end else if (!vld[rp] && !(rec && ss == rp)) rp <= nxt(rp);              // sweep an empty entry
            if (late) t_mf[2] <= 1'b1;
            if (rec) vld[ss] <= 1'b1;                                                // (rec && ss == rp && hit) is a collision: not recorded
            // the unit's done must land on exactly the edge t_ku announced
            kv_d <= t_ku[31];
            if (kd_q != kv_d) t_mf[2] <= 1'b1;
        end
    // entry payload (no reset: written at the start that sets vld, read only while vld)
    always @(posedge ck) if (rec) begin eu[ss] <= su; ep[ss] <= sp; ed[ss] <= tm + {8'd0, crl} - 32'd1; end
endmodule

// ---------------------------------------------------------------- the unit with the multi-user host slot table
// NSLOT 1 (default): dsdv_seq_host exactly (t_ku / t_mf tied 0, f_mc unused).  NSLOT > 1: t_kd's 32 spare zero bits
// carry {user, pos, 0} of the returning start; t_mf goes to the die status fold beside t_host.
module dsdv_seq_host_mu #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0,
                          parameter integer NSLOT = 1, parameter integer MU_MUT = 0) (
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
    dsdv_seq_host #(.V(V), .STAGE(STAGE), .MUT(MUT)) u_u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
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
