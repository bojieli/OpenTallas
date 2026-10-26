`timescale 1ns/1ps
// Q-VMWB 2026-10-16: landing-side KV calendar leaf (one per static landing group, 32 per KV die, ONE master).
//
// The producer the static landing and its four per-PC return slots were missing (tools/qwen_kv_die/
// kv_elastic_boundary.py MISSING_PRODUCERS).  Every value is a fixed function of the compiled pass starts (kgo, vgo),
// the context T of the token, the group identity and six boot constants; nothing here observes data, readiness or
// credits, and a missing or late word never moves a slot (the landing / return slots fault instead).
//
// Stream (kv_calendar.py, measured for every PC and every T): a pass puts its group's sectors one per HBM edge,
// put i at HBM edge A + H0 + off(i), off(i) = i up to the pass's ring-pacing index P0 and then GAP more HBM edges
// before every further 8-sector front block (PV16 V at the KV-die ring DEPTH 64: P0 160, GAP 5; K: no pacing),
// identical for every PC and a prefix at any T, where A is the HBM edge at which the front calendar (qkd_kv_front_cal) takes the
// pass start.  V streams the group's rows t < T in ascending t, a gap-free prefix of the stream position
// p = {t[12:9], t6, t[3:1]} (writer VMAP=1); sector(p) = {1, 0, p[3], p[7:4], p[2:0]}.  K follows the QK calendar
// (static_qk_calendar): while the stack's row count ns <= 1024 (T up to ~4.1k-4.5k by stack) also ascending t,
// p = {t[12:9], t6, t[5:3]}, sector {0, 0, p[3], p[7:4], p[2:0]}; above it the engine scan order is sector ascending:
// the t6 = 0 rows ([0, nb0)) then the t6 = 1 rows ([128, 128 + nb1)).  (The landing PC's row ordinal
// {sec[6:3], sec[7], sec[2:0]} is alias free in both orders with <= 64 rows outstanding.)  The lengths nk / nv are closed forms of T, the
// stack s and the group e (checked against kv_calendar for every T).
//
// Clocks: core 833.333 ps = 625 u, HBM 1024 ps = 768 u (one PLL; 768 core = 625 HBM edges).  q = u until the next
// HBM edge at / after this core edge; q = PH0 on the first edge after reset release (die contract: the reset
// release edge is beat aligned; PH0 is that phase).  At a pass start captured on core edge k0, A = the first HBM edge
// at / after k0 + XU u (XU < 768: the fixed compiled core -> HBM crossing of kgo / vgo), and put i is popped from
// the return ring (r_put / r_sector, the return slots' expected_*) on the first core edge >= A + 768 (H0 + i) + 625 RC
// (RC: the ring's publish -> core visibility edges); the landing sees the same row LD core edges later (l_put /
// l_sector: return slot output register + relays).  At most one HBM edge per core edge, so one put per edge.
//
// Boot constants (cfg_we / cfg_addr / cfg_data, written once at boot by the programme loader):
//   0: {stack[1:0], group[2:0]}   1: XU[9:0]   2: H0[7:0]   3: {LD[3:0] (0..8), RC[3:0]}
//   4: K pacing {GAP[3:0], P0[8:0]}   5: V pacing {GAP[3:0], P0[8:0]}   (P0 >= 256: none)
// Faults (sticky, never move a slot): a pass start while a pass is still putting, vgo before the layer's kgo.
// MUT (bench negative controls): 1 = V sector uses o[7] for the 128 bit, 2 = phase drifts one unit a beat,
// 3 = K sector = stream index (no order / segment mapping).
module qkd_kv_landing_cal #(parameter integer MUT = 0, parameter integer PH0 = 0, parameter integer SAME_CLOCK = 0) (
    input wire ck, rst_n,
    input wire cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    input wire kgo, input wire vgo,
    input wire [13:0] ctx_t, input wire [15:0] epoch, input wire [5:0] layer,
    output reg arm, output reg [15:0] l_epoch, output reg [5:0] l_layer,
    output reg [3:0] l_put, output reg [39:0] l_sector,
    output reg [3:0] r_put, output reg [39:0] r_sector, output reg [15:0] r_epoch, output reg [5:0] r_layer,
    output reg fault
);
    // ---- reset captured at its pin; every input pin registered ----
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    reg kgo_q, vgo_q, we_q;
    reg [7:0] ad_q; reg [63:0] cd_q; reg [13:0] ctx_q; reg [15:0] ep_q; reg [5:0] ly_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin kgo_q <= 1'b0; vgo_q <= 1'b0; we_q <= 1'b0; end
        else begin kgo_q <= kgo; vgo_q <= vgo; we_q <= cfg_we; end
    always @(posedge ck) begin ad_q <= cfg_addr; cd_q <= cfg_data; ctx_q <= ctx_t; ep_q <= epoch; ly_q <= layer; end
    // ---- boot constants ----
    reg [1:0] s_c; reg [2:0] e_c; reg [9:0] xu_c; reg [7:0] h0_c; reg [3:0] rc_c, ld_c, kg_c, vg_c; reg [8:0] kp_c, vp_c;
    always @(posedge ck or negedge rn)
        if (!rn) begin s_c <= 0; e_c <= 0; xu_c <= 0; h0_c <= 0; rc_c <= 0; ld_c <= 0; kg_c <= 0; vg_c <= 0; kp_c <= 9'h1ff; vp_c <= 9'h1ff; end
        else if (we_q) case (ad_q)
            8'd0: begin s_c <= cd_q[4:3]; e_c <= cd_q[2:0]; end
            8'd1: xu_c <= cd_q[9:0];
            8'd2: h0_c <= cd_q[7:0];
            8'd3: begin rc_c <= cd_q[3:0]; ld_c <= cd_q[7:4]; end
            8'd4: begin kp_c <= cd_q[8:0]; kg_c <= cd_q[12:9]; end
            8'd5: begin vp_c <= cd_q[8:0]; vg_c <= cd_q[12:9]; end
            default: ;
        endcase
    // ---- core / HBM phase: q = u until the next HBM edge at / after this edge ----
    reg [9:0] q;
    always @(posedge ck or negedge rn)
        if (!rn) q <= 10'(PH0);
        else if (SAME_CLOCK) q <= 0;
        else q <= (q >= 10'd625) ? q - 10'd625 : q + ((MUT == 2) ? 10'd144 : 10'd143);
    // ---- closed-form stream lengths (latched T of the layer) ----
    reg [13:0] t_l;
    // K row t = 512 a + 128 s + 64 b + 8 c + e; V row t = 512 a + 128 s + 64 b + 16 l + 2 c + par (e = {l, par})
    wire signed [15:0] xk = $signed({2'b0, (kgo_q ? ctx_q : t_l)}) - $signed({7'b0, s_c, 7'b0}) - $signed({13'b0, e_c});
    wire signed [15:0] xv = $signed({2'b0, t_l}) - $signed({7'b0, s_c, 7'b0}) - $signed({10'b0, e_c[2:1], 4'b0}) - $signed({15'b0, e_c[0]});
    // K t6 = 0 rows below x (order B first segment)
    function automatic [7:0] cnt0(input signed [15:0] x);
        reg [8:0] r; reg [9:0] h;
        begin
            r = x[8:0]; h = ({1'b0, r} + 10'd7) >> 3;
            cnt0 = (x <= 0) ? 8'd0 : (x[15:9] >= 7'd16) ? 8'd128 : {x[13:9], 3'b0} + ((h >= 10'd8) ? 8'd8 : 8'(h));
        end
    endfunction
    // QK calendar order: ns = 128 (T >> 9) + min(128, max(0, T[8:0] - 128 s)) > 1024 -> sector-ascending scan
    wire [13:0] tk = kgo_q ? ctx_q : t_l;
    wire ordb = (tk[13:9] > 5'd8) || (tk[13:9] == 5'd8 && {1'b0, tk[8:0]} > {1'b0, s_c, 7'b0});
    function automatic [8:0] cnt(input signed [15:0] x, input integer sh);   // rows below x: 16 per 512; c stride 1 << sh
        reg [8:0] r; reg [3:0] c0, c1; reg [9:0] h0, h1;
        begin
            r = x[8:0];
            h0 = ({1'b0, r} + 10'((1 << sh) - 1)) >> sh; h1 = (r > 9'd64) ? ({1'b0, r} - 10'd64 + 10'((1 << sh) - 1)) >> sh : 10'd0;
            c0 = (h0 >= 8) ? 4'd8 : 4'(h0); c1 = (h1 >= 8) ? 4'd8 : 4'(h1);
            cnt = (x <= 0) ? 9'd0 : (x[15:9] >= 7'd16) ? 9'd256 : {x[12:9], 4'b0} + {5'b0, c0} + {5'b0, c1};
        end
    endfunction
    // ---- pass state ----
    reg act, vpass, have_layer;
    reg [8:0] i, n; reg [7:0] nb0; reg kb;
    reg signed [19:0] d;                                // u until put i becomes visible, at the next edge
    wire [10:0] ta = SAME_CLOCK ? ((xu_c == 0) ? 11'd0 : ((xu_c <= 625) ? 11'd625 : 11'd1250))
                                     : ((q >= xu_c) ? {1'b0, q} : {1'b0, q} + 11'd768);     // A - k0 in u (XU < 768: at most one HBM edge later)
    wire signed [19:0] t0_ratio = $signed({9'b0, ta}) + $signed({2'b0, h0_c, 9'b0}) + $signed({3'b0, h0_c, 8'b0})
                          + $signed({6'b0, rc_c, 9'b0}) + $signed({9'b0, rc_c, 6'b0}) + $signed({10'b0, rc_c, 5'b0})
                          + $signed({11'b0, rc_c, 4'b0}) + $signed({15'b0, rc_c}) - 20'sd625;
    wire signed [19:0] t0 = SAME_CLOCK
        ? $signed({9'b0, ta}) + $signed({12'b0, h0_c}) * 20'sd625
          + $signed({16'b0, rc_c}) * 20'sd625 - 20'sd625
        : t0_ratio;
    wire start = kgo_q | vgo_q;
    // ring pacing: put i + 1 starts a paced front block -> GAP more HBM edges (768 u each)
    wire [8:0] pp = vpass ? vp_c : kp_c; wire [3:0] pg = vpass ? vg_c : kg_c;
    wire [8:0] i1 = i + 9'd1;
    wire pace = (i1 >= pp) && (i1[2:0] == pp[2:0]);
    wire signed [19:0] gapu = SAME_CLOCK ? $signed({16'b0, pg}) * 20'sd625
        : $signed({6'b0, pg, 10'b0}) - $signed({8'b0, pg, 8'b0});
    wire emit = act && (d <= 0);
    wire [7:0] vo = i[7:0];
    wire [9:0] sec = vpass ? {1'b1, 1'b0, ((MUT == 1) ? vo[7] : vo[3]), ((MUT == 1) ? {vo[3], vo[6:4]} : vo[7:4]), vo[2:0]}
                           : (MUT == 3) ? {2'b0, vo}
                           : kb ? ((vo < nb0) ? {2'b0, vo} : {2'b0, 1'b1, 7'(vo - nb0)})
                           : {2'b0, vo[3], vo[7:4], vo[2:0]};
    always @(posedge ck or negedge rn)
        if (!rn) begin act <= 0; vpass <= 0; have_layer <= 0; i <= 0; n <= 0; d <= 0; nb0 <= 0; kb <= 0; t_l <= 0; fault <= 0; arm <= 0; end
        else begin
            arm <= kgo_q;
            if (start) begin
                if (act && !(emit && i + 9'd1 == n)) fault <= 1'b1;
                if (vgo_q && !have_layer) fault <= 1'b1;
                act <= 1'b1; i <= 0; d <= t0; vpass <= vgo_q;
                if (kgo_q) begin
                    have_layer <= 1'b1; t_l <= ctx_q; n <= cnt(xk, 3); nb0 <= cnt0(xk); kb <= ordb;
                end else n <= cnt(xv, 1);
            end else if (act) begin
                if (i == n) act <= 1'b0;
                else if (emit) begin i <= i + 9'd1; d <= d - 20'sd625 + (SAME_CLOCK ? 20'sd625 : 20'sd768) + (pace ? gapu : 20'sd0); if (i + 9'd1 == n) act <= 1'b0; end
                else d <= d - 20'sd625;
            end
            if (kgo_q && vgo_q) fault <= 1'b1;
        end
    // ---- outputs: return slots now, landing LD edges later (all registered) ----
    wire put_now = emit && i < n && !start;
    reg [10:0] dl [0:7];                                // LD 0..8 (return slot output register + <= 6 relays)
    integer k;
    always @(posedge ck or negedge rn)
        if (!rn) begin r_put <= 0; l_put <= 0; for (k = 0; k < 8; k = k + 1) dl[k] <= 0; end
        else begin
            r_put <= {4{put_now}};
            dl[0] <= {put_now, sec};
            for (k = 1; k < 8; k = k + 1) dl[k] <= dl[k-1];
            l_put <= {4{(ld_c == 0) ? put_now : dl[3'(ld_c - 4'd1)][10]}};
        end
    always @(posedge ck) begin
        r_sector <= {4{sec}};
        l_sector <= {4{(ld_c == 0) ? sec : dl[3'(ld_c - 4'd1)][9:0]}};
        if (start) begin r_epoch <= ep_q; r_layer <= ly_q; end
        if (kgo_q) begin l_epoch <= ep_q; l_layer <= ly_q; end
    end
endmodule
