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
// its due edge), [3] config (f_mc while armed / outstanding, or S < NSLOT, or RL <= NSLOT at the first start).
// Boot config f_mc = {v, sel, d 24} (host lane block CSR, boot only): sel 0 = slot period S (cycles), sel 1 = RL (edges
// from the f_ks capture edge to the t_kd pin edge).  Return order = start order (same RL for every start), so the
// return pointer rp only stops on valid entries and sweeps empty ones one an edge (needs RL > NSLOT, checked).
// Timing: f_ks / f_kd / f_mc land in pin flops; t_ku / t_mf leave flops.  Single clock ck (stream), ot_rst_relay.
// Area (NSLOT 47): 47 x 63 b entry flops + 47 10-b user compares + ~110 control flops ~ 3.9k flops; modelled
// ~0.004 mm^2 (design study item 6: 0.001 mm^2 for the field alone).
// NSLOT = 1 (default of dsdv_seq_host_mu): the leaf is not instantiated, t_kd / every pin = dsdv_seq_host exactly.
// MUT (bench negative controls): 1 user field dropped from t_ku (user 0 on every return), 2 slot-collision check
// dropped (the occupied entry is overwritten, no fault), 3 (NEV > 0) window ab bit dropped (copy B never selected),
// 4 (NEV > 0) replay enable ignored (cut-through users replayed).
// ---------------------------------------------------------------------------------------------------------------------
// MU-S81/DIE (2026-10-19): end-slice TX tag windows + landing replays + RX tag check (NEV > 0; NEV = 0 = the leaf above,
// byte-for-byte the same behaviour, the new ports unread / 0).  Under the shift calendar every user runs user 0's
// schedule shifted by its slot, so every per-user event on this die sits a FIXED offset D after that user's start
// capture edge.  NEV boot-loaded event rows {kind, endpoint, D}: kind 0 = TX tag window on endpoint ep (mu_c[ep] =
// {pos, user, land, ab, v} of the start D edges earlier), kind 1 = landing replay (mu_rc[ep] = {user, v}).  The
// per-slot attributes {land / replay-enable, ab} of each event (copy A / B, land vs cut-through: calendar_ar_q4 rows)
// are boot-loaded per calendar slot.  One pointer per event walks the slot table in start order (it parks only on a
// recorded, not yet fired entry; per-entry fired flags), so every event fires exactly on ts + D with no queue, no
// ready, no credit.  RX: every valid tag on mu_rt (NRT end slices: {v, user, pos} with ri) must name an outstanding
// start {user, pos} of this table, else t_mf[2] (sticky).  Two events on one endpoint output in one edge = t_mf[3].
// Config (NEV > 0 only): f_mc sel 1 with d[23] = 1 is a window word (sel 1 with d[23] = 0 is RL as before, RL < 2^23):
//   d[22:21] = 0 select event d[4:0], kind d[8], endpoint d[10:9];  1 offset D = d[20:0] of the selected event;
//   2 attribute of the selected event for slot d[9:0] = {land/replay-en d[11], ab d[10]};  3 = config fault.
// Checks at the first start (config fault t_mf[3]): every D in [NSLOT + 2, RL - 2] and S > NSLOT + 1.
module dsdv_mu_hslot #(parameter integer NSLOT = 47, parameter integer MUT = 0,
                       parameter integer NEV = 0, parameter integer NEP = 4, parameter integer NRT = 1) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [52:0]   f_ks,            // tap of the unit start pin {start, user 10, tok 21, pos 21}
    input  wire [53:0]   f_kd,            // tap of the unit t_kd {done, tok 21, 32'b0}
    input  wire [25:0]   f_mc,            // boot config {v, sel, d 24}
    output reg  [31:0]   t_ku,            // {v, user 10, pos 21}: same edge as the unit's t_kd done
    output reg  [3:0]    t_mf,            // sticky faults
    output wire [NEP*34-1:0] mu_c,        // per end slice: TX tag window {pos 21, user 10, land, ab, v}
    output wire [NEP*11-1:0] mu_rc,       // per end slice: landing replay {user 10, v}
    input  wire [NRT*32-1:0] mu_rt        // per returning end slice: RX tag {v, user 10, pos 21}
);
    localparam integer SI = (NSLOT > 1) ? $clog2(NSLOT) : 1;
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
    reg [NSLOT-1:0] vld; reg [9:0] eu [0:NSLOT-1]; reg [20:0] ep [0:NSLOT-1]; reg [31:0] ed [0:NSLOT-1];
    wire [SI-1:0] ss = armed ? sl : {SI{1'b0}};          // the start's calendar slot
    wire on_cal = !armed || ph == 24'd0;
    reg udup; integer i;
    always @* begin udup = 1'b0; for (i = 0; i < NSLOT; i = i + 1) if (vld[i] && eu[i] == su) udup = 1'b1; end
    wire col = vld[ss];
    wire wcfg_bad, wf2, wf3;                            // MU-S81/DIE window config / RX-tag / window faults (0 at NEV 0)
    wire cfg_bad = cs < 24'(NSLOT) || crl <= 24'(NSLOT) || wcfg_bad;
    wire m2c = MUT == 2 && col;                          // MUT 2: the collision (and the dup it implies) goes unchecked
    wire rec = st && on_cal && ((!col && !udup) || m2c) && !(!armed && cfg_bad);    // the start is recorded
    wire [31:0] rd = ed[rp];
    wire hit = vld[rp] && rd == tm;
    wire late = vld[rp] && rd != tm && rd - tm > 32'h7fffffff;                     // due edge already passed
    function automatic [SI-1:0] nxt(input [SI-1:0] p);
        nxt = (p == SI'(NSLOT - 1)) ? {SI{1'b0}} : p + 1'b1;
    endfunction
    always @(posedge ck or negedge rn)
        if (!rn) begin
            tm <= 32'd0; armed <= 1'b0; ph <= 24'd0; sl <= {SI{1'b0}}; rp <= {SI{1'b0}}; vld <= {NSLOT{1'b0}};
            t_ku <= 32'd0; kv_d <= 1'b0; t_mf <= 4'd0; cs <= 24'd0; crl <= 24'd0;
        end else begin
            tm <= tm + 32'd1;
            // boot config
            if (mc_q[25]) begin
                if (armed || |vld) t_mf[3] <= 1'b1;
                else if (mc_q[24] && !(NEV > 0 && mc_q[23])) crl <= mc_q[23:0];
                else if (!mc_q[24]) cs <= mc_q[23:0];
            end
            // slot timer: phase of the current edge, slot index advanced at the period wrap
            if (armed) begin
                if (ph == cs - 24'd1) begin ph <= 24'd0; sl <= nxt(sl); end else ph <= ph + 24'd1;
            end
            // start: record in its slot, or fault (never queued, never retried)
            if (st) begin
                if (!armed) begin
                    if (cfg_bad) t_mf[3] <= 1'b1;
                    else begin armed <= 1'b1; ph <= 24'd1; end
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
            if (wf2) t_mf[2] <= 1'b1;                                               // MU-S81/DIE (0 at NEV 0)
            if (wf3) t_mf[3] <= 1'b1;
        end
    // entry payload (no reset: written at the start that sets vld, read only while vld)
    always @(posedge ck) if (rec) begin eu[ss] <= su; ep[ss] <= sp; ed[ss] <= tm + {8'd0, crl} - 32'd1; end
    // ---- MU-S81/DIE: per-start event windows (NEV > 0) and RX tag check
    generate if (NEV > 0) begin : g_win
        localparam integer EI = (NEV > 1) ? $clog2(NEV) : 1;
        localparam integer PI = (NEP > 1) ? $clog2(NEP) : 1;
        reg [31:0] ts [0:NSLOT-1];                        // start capture edge of each entry
        reg [EI-1:0] esel; reg [NEV-1:0] ek; reg [PI-1:0] eep [0:NEV-1]; reg [20:0] eD [0:NEV-1];
        reg [1:0] eat [0:NEV-1][0:NSLOT-1];               // {land / replay-en, ab} per event and calendar slot
        reg [NSLOT-1:0] fd [0:NEV-1];                     // fired flags
        reg [SI-1:0] pe [0:NEV-1];
        reg [NRT*32-1:0] rt_q; reg wf2_q, wf3_q;
        integer e, r, p;
        reg bad_d; reg [NEV-1:0] fire, lt;
        always @* begin
            bad_d = cs <= 24'(NSLOT + 1);
            for (e = 0; e < NEV; e = e + 1)
                if ({3'd0, eD[e]} < 24'(NSLOT + 2) || {3'd0, eD[e]} + 24'd2 > crl) bad_d = 1'b1;
            for (e = 0; e < NEV; e = e + 1) begin
                fire[e] = vld[pe[e]] && !fd[e][pe[e]] && ts[pe[e]] + {11'd0, eD[e]} == tm;
                lt[e] = vld[pe[e]] && !fd[e][pe[e]] && (ts[pe[e]] + {11'd0, eD[e]} - tm) > 32'h7fffffff;
            end
        end
        assign wcfg_bad = bad_d; assign wf2 = wf2_q; assign wf3 = wf3_q;
        wire wv = mc_q[25] && mc_q[24] && mc_q[23];
        reg rtbad, m; reg [NEP*34-1:0] c_n, c_q; reg [NEP*11-1:0] rc_n, rc_q; reg col_w;
        assign mu_c = c_q; assign mu_rc = rc_q;
        always @* begin
            rtbad = 1'b0;
            for (r = 0; r < NRT; r = r + 1) begin
                m = 1'b0;
                for (p = 0; p < NSLOT; p = p + 1)
                    if (vld[p] && eu[p] == rt_q[32*r + 21 +: 10] && ep[p] == rt_q[32*r +: 21]) m = 1'b1;
                if (rt_q[32*r + 31] && !m) rtbad = 1'b1;
            end
            c_n = {NEP*34{1'b0}}; rc_n = {NEP*11{1'b0}}; col_w = 1'b0;
            for (e = 0; e < NEV; e = e + 1) if (fire[e]) begin
                if (!ek[e]) begin
                    if (c_n[34*eep[e]]) col_w = 1'b1;
                    c_n[34*eep[e] +: 34] = {ep[pe[e]], eu[pe[e]], eat[e][pe[e]][1], (MUT == 3) ? 1'b0 : eat[e][pe[e]][0], 1'b1};
                end else if (eat[e][pe[e]][1] || MUT == 4) begin
                    if (rc_n[11*eep[e]]) col_w = 1'b1;
                    rc_n[11*eep[e] +: 11] = {eu[pe[e]], 1'b1};
                end
            end
        end
        always @(posedge ck) begin
            rt_q <= mu_rt;
            for (r = 0; r < NRT; r = r + 1) rt_q[32*r + 31] <= rn & mu_rt[32*r + 31];
            if (rec) ts[ss] <= tm;
            if (wv && !armed && !(|vld)) begin
                case (mc_q[22:21])
                    2'd0: begin esel <= mc_q[EI-1:0]; ek[mc_q[EI-1:0]] <= mc_q[8]; eep[mc_q[EI-1:0]] <= mc_q[9 +: PI]; end
                    2'd1: eD[esel] <= mc_q[20:0];
                    2'd2: eat[esel][mc_q[SI-1:0]] <= mc_q[11:10];
                    default: ;
                endcase
            end
        end
        always @(posedge ck or negedge rn)
            if (!rn) begin
                c_q <= {NEP*34{1'b0}}; rc_q <= {NEP*11{1'b0}}; wf2_q <= 1'b0; wf3_q <= 1'b0;
                for (e = 0; e < NEV; e = e + 1) begin pe[e] <= {SI{1'b0}}; fd[e] <= {NSLOT{1'b0}}; end
            end else begin
                c_q <= c_n; rc_q <= rc_n;
                for (e = 0; e < NEV; e = e + 1) begin
                    if (rec) fd[e][ss] <= 1'b0;
                    if (fire[e]) begin fd[e][pe[e]] <= 1'b1; pe[e] <= nxt(pe[e]); end
                    else if ((!vld[pe[e]] || fd[e][pe[e]]) && !(rec && ss == pe[e])) pe[e] <= nxt(pe[e]);
                end
                wf3_q <= (wv && mc_q[22:21] == 2'd3) || col_w;
                wf2_q <= rtbad || (|lt);
            end
    end else begin : g_nowin
        assign wcfg_bad = 1'b0; assign wf2 = 1'b0; assign wf3 = 1'b0;
        assign mu_c = {NEP*34{1'b0}}; assign mu_rc = {NEP*11{1'b0}};
    end endgenerate
endmodule

// ---------------------------------------------------------------- the unit with the multi-user host slot table
// NSLOT 1 (default): dsdv_seq_host exactly (t_ku / t_mf tied 0, f_mc unused).  NSLOT > 1: t_kd's 32 spare zero bits
// carry {user, pos, 0} of the returning start; t_mf goes to the die status fold beside t_host.
// MU-S81/DIE: NEV > 0 adds the end-slice windows (mu_c / mu_rc per end slice, mu_rt RX tags back), see dsdv_mu_hslot.
module dsdv_seq_host_mu #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0,
                          parameter integer NSLOT = 1, parameter integer MU_MUT = 0,
                          parameter integer NEV = 0, parameter integer NEP = 4, parameter integer NRT = 1) (
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
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [NEP*34-1:0] mu_c, output wire [NEP*11-1:0] mu_rc, input wire [NRT*32-1:0] mu_rt
);
    wire [53:0] kd;
    dsdv_seq_host #(.V(V), .STAGE(STAGE), .MUT(MUT)) u_u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks),
        .t_kd(kd), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w),
        .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    generate if (NSLOT > 1) begin : g_mu
        wire [31:0] ku;
        dsdv_mu_hslot #(.NSLOT(NSLOT), .MUT(MU_MUT), .NEV(NEV), .NEP(NEP), .NRT(NRT)) u_hs (.ck(ck), .rst_n(rst_n),
            .f_ks(f_ks), .f_kd(kd), .f_mc(f_mc), .t_ku(ku), .t_mf(t_mf), .mu_c(mu_c), .mu_rc(mu_rc), .mu_rt(mu_rt));
        assign t_kd = {kd[53:32], ku[30:0], 1'b0};      // kd[31:0] = 0 by the unit's contract (sh_sq kd_o)
    end else begin : g_su
        assign t_kd = kd; assign t_mf = 4'd0; assign mu_c = {NEP*34{1'b0}}; assign mu_rc = {NEP*11{1'b0}};
    end endgenerate
endmodule

// ---------------------------------------------------------------- MU-S81/DIE: parameter-free p4l die master (MU dies)
// dsdv_seq_host_mux = dsdv_seq_host_mu NSLOT 47 (AR 46 / owner 47 users; MTP 10 + filler uses 11 slots), 8 window
// events, 4 end slices (mu_c / mu_rc to s_7N / s_7S / s_0N / s_0S), RX tags back from the 2 N-tier end slices
// (s_7N, s_0N: the S-tier tags carry the same user / pos and are not returned -- column-4 W lane margin has 2 free
// tracks below the seqhost; MU-S81/DIE plan note).  Boot config f_mc rides the host stream as class-0 CSR 0x15
// (d[57:32] = f_mc {v, sel, d 24}): the master decodes it from the f_host pin it already has (0 die wires).  Index 0x15
// is not one of sh_lk's intercepted CSRs (0x10/0x11/0x13/0x14), so it also reaches the ingest, which ignores class-0
// indices other than 0/1/2 (ot_rom_host_ingest CSR decode): seq_host behaviour unchanged.  t_mf leaves like the other
// block fault outputs (die status fold owed with them).
module dsdv_seq_host_mux (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [3:0]    t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n
);
    // CSR 0x15 decode (the f_host word {h_cls 2, h_d 512, h_v}; h_d[7:0] index, h_d[57:32] value) into one flop
    reg [25:0] mc;
    always @(posedge ck) mc <= (f_host[0] && f_host[514:513] == 2'd0 && f_host[8:1] == 8'h15) ? f_host[58:33] : 26'd0;
    dsdv_seq_host_mu #(.NSLOT(47), .NEV(8), .NEP(4), .NRT(2)) u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks),
        .t_kd(t_kd), .f_mc(mc), .t_mf(t_mf), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w),
        .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v),
        .cw_a(cw_a), .cw_d(cw_d), .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0n, mu_rt_7n}));
endmodule
// MU-DIE-S81/MAB (2026-10-19): the seqhost of the copy-A/B rank die (plan p4l_mab_lkcol: AB pair on s_0S).  Copy-B beats
// arrive on s_0S only, so its RX tags return on mu_rt_0s (lane rt_0S) and the RX tag check (t_mf[2]) covers 3 end
// slices (NRT 3).  Everything else is dsdv_seq_host_mux exactly.
module dsdv_seq_host_mab (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [3:0]    t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n, mu_rt_0s
);
    reg [25:0] mc;
    always @(posedge ck) mc <= (f_host[0] && f_host[514:513] == 2'd0 && f_host[8:1] == 8'h15) ? f_host[58:33] : 26'd0;
    dsdv_seq_host_mu #(.NSLOT(47), .NEV(8), .NEP(4), .NRT(3)) u (.ck(ck), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k),
        .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host), .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks),
        .t_kd(t_kd), .f_mc(mc), .t_mf(t_mf), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e), .s_hw_w(s_hw_w),
        .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e), .cw_v(cw_v),
        .cw_a(cw_a), .cw_d(cw_d), .mu_c({mu_c_0s, mu_c_0n, mu_c_7s, mu_c_7n}), .mu_rc({mu_rc_0s, mu_rc_0n, mu_rc_7s, mu_rc_7n}),
        .mu_rt({mu_rt_0s, mu_rt_0n, mu_rt_7n}));
endmodule
