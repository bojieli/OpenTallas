`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// ot_hgi_sm_xload_static_cl2xp (HBM-XLP10 2026-10-20): PIPELINED x-load control (TOK.HDS.SMMV).  New modules; every
// cl2 / xql module stays byte-identical and the CLOSED ctlx views stand (hgi_sm_xl2_ctlx, hgi_sm_xl2_ctlx_bl).
//   ot_hgi_sm_xload_cl2xp_ctl / _ctlw / _ctlx   cl2 ctl / ctlw / ctlx with the issue engine released on the LAST ISSUE
//                                              EDGE of a load (x_busy) instead of at x_done; the issuer status 'active'
//                                              follows x_act (any load in flight).  A single load is cycle-identical to
//                                              cl2 on every connected port (rq, c_*, r_ce, l_d_o, q*, r_wsel, z*, bsel,
//                                              lane_en, eg_* while their valid is set).
//   ot_hgi_sm_xload_static_xqlp                 ot_hgi_sm_xload_static_xql with the XP ctlx (bench / die binding).
// Why (HBM-SMMV9 b2ae8ec24): DS SM small dense records lose 39.6k cycles/token because x-loads run one at a time
// (cl2 ctlx x_busy until x_done).  With XP the compiler fires x-load i+1 at the issue end of x-load i:
//   at(i+1) >= at(i) + ISS(i)                      ISS = BF 8 nb gn, BD wb gtp (nb = ceil(3152 P / 2048))
//   at(i+1) >= at(i) + LAST(i) + 1 - FIRST(i+1)    every load's beats stay disjoint (P = 1: F + CAD n of XLAT)
// and every beat / x_done of every load is its cl2 beat, at(i) later.  The fields that later stages need ride the fixed
// pipeline (per-wave bits in md / L / C / tag; per-load egress fields in an 8-slot context ring keyed by the load id).
// MUT (bench): cl2's 1..5, 7; 8 = the egress xb does not ride (taken from the issue side): must FAIL with overlap.
// =====================================================================================================================

module ot_hgi_sm_xload_cl2xp_ctl #(
    parameter integer PMAX   = 8,
    // RD_LAT (HBM-BANKLAT-XL 10-19): VM read round trip in edges = registers between the rq pins and the rr pins
    // (ref 6 = ot_vms_bank_static n+6 with zero die stages; faces bank +1; + die lane stations each way).
    //   SCALAR (RD_LAT[63:8] == 0): every bank answers RD_LAT edges after its request (today's form, default 6;
    //     unequal lanes are padded by the die).
    //   PER-BANK VECTOR (die contract list [l0..l7], packed element b at RD_LAT[8b +: 8]): bank b answers l_b edges
    //     after ITS request.  The ctl issues bank b's request D_b = RLM - l_b edges late (RLM = max l_b) from ONE
    //     shared 16-bit tapped delay line of the wave issue {valid, s0} (DMX = max D_b stages), so every bank's
    //     answer reaches the rr pins on the same edge, RLM edges after the wave issue: no 257-bit lane padding.
    //   Everything after the rr pins sees RLM exactly as it saw the scalar RD_LAT (md depth, em_off, egress eg_*,
    //   x_done): the x-load schedule is the scalar schedule at RD_LAT = RLM.  VM calendar: bank b's x-load read
    //   arrives at its port D_b + lane_rq_b edges after the wave issue (the compiler's rslot for the x-load group).
    // MUT 7 (bench): the per-bank stagger is ignored (all D_b = 0, schedule still at RLM) -> must FAIL on unequal lanes.
    parameter [63:0] RD_LAT = 64'd6,
    parameter integer MUT    = 0,
    parameter integer NR     = 32,       // select replicas (each drives 2048 / NR data bits)
    parameter integer EGRESS_SPLIT = 0,  // XQL (H-SM 10-16): 1 = export the egress controls (eg_*) to pair-egress leaves
    // SEL_KEEP=1 (HBM-B 10-17, ctlx): the NR rotation-select replicas are (* keep *) flops, so synthesis keeps NR copies
    // (ctlw f20a: opt_merge folded them, u_ctl.s0r[26][*] drove 5,045 loads).  Same function, same edges.
    parameter integer SEL_KEEP = 0,
    // PIN_NATIVE=1 (ELEM-GAPS/HBMN1 10-18, ctlx native audit of CLOSED q1-7af6f4406: l_d_o launch 403 ps on 580 pins):
    // l_d_o leaves from a dedicated (* keep *) pin register copy of L1 (D = l0_d, same edge as l_d), so the l_d_o
    // pin flops sit at the E face while l_d feeds the C stage on the W side.  Same function, same edges.
    parameter integer PIN_NATIVE = 0,
    // RST_PRE=1: rst_n is already a relayed, synchronous reset (ctlx pin relay); rn = rst_n (no second relay).
    parameter integer RST_PRE = 0
) (
    input  wire               clk,
    input  wire               clk_eg,    // egress root (rw / BD-beat pin capture, beat select, xw pins): related phase 0
    input  wire               rst_n,
    input  wire               x_v,
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    input  wire [6:0]         x_xb,
    output reg                x_busy,    // XP: ISSUE busy (falls on the last issue edge; the next command may start there)
    output wire               x_act,     // XP: any load still in flight (issue, pipeline, emission) -> issuer status
    output reg                x_done,
    output reg                x_fault,
    output reg                xw_en,
    output reg                xw_last,
    output reg  [6:0]         xw_addr,
    output reg  [6:0]         xw_grp,
    output reg  [2047:0]      xw_data,
    output wire [8*17-1:0]    rq,
    input  wire [8*257-1:0]   rr,
    // leaf reset (relay output)
    output wire               rn_o,
    // ---- to the 4 BF quarters (write side, C stage registers)
    output reg  [1023:0]      c_d,
    output reg  [3:0]         c_wce,     // quarter q writes at W (= wp_ce of every macro of quarter q)
    output reg                c_mhi, c_mlo,   // lane-half write masks
    output reg  [6:0]         c_wa,      // {g mod 16, p}
    // ---- to the 4 BF quarters (read side, one-edge lookahead of the E0 decision)
    output reg  [7:0]         r_ce,      // macro t reads at E0 + 1
    output reg  [6:0]         r_a,
    // ---- from the 4 BF quarters
    input  wire [1023:0]      rwq,       // quarter q rw register at [256 q +: 256]
    // ---- quantisers (their data words go straight to the BD ring leaf; only the valid / fault flags come here)
    output wire [2047:0]      l_d_o,
    output reg                qv_lo, qv_hi,
    input  wire               qo_lo, qo_hi, qf_lo, qf_hi,
    // ---- BD ring
    output reg  [15:0]        r_wsel,    // one-hot ring slot write enable (both parities)
    output reg                zlo, zhi,  // block inside K (lane word kept) / outside (written as 0)
    output reg  [2*((PMAX*3152+2047)/2048)-1:0] bsel,   // one-hot {parity a, beat b} of (ea, eb2), same edge

    output reg  [PMAX*8-1:0]  lane_en,
    input  wire [2047:0]      bq_d,
    // ---- XQL egress controls (EGRESS_SPLIT = 1; tied 0 otherwise): ed[RDP-3] {ok, b}, ed[RDP-2], the BD beat tag
    output wire [7:0]         eg_ed5,
    output wire [16:0]        eg_ede,
    output wire               eg_bqv, eg_bqlast,
    output wire [6:0]         eg_bqaddr, eg_bqb
);
    localparam integer XC = 3152, XOFF = 2128;
    localparam integer NBMAX = (PMAX * XC + 2047) / 2048;
    localparam integer LAND = 4;           // cl2g: + 1 landing stage (L1) between the rotation mux and l_d_o / C
    localparam integer RDP = 7;            // + 1: rw captured at the ctl pins (egress edge)
    localparam integer RB = 2048 / NR;     // data bits per select replica
    // ---- per-bank read round trip (RD_LAT header): l_b, RLM = max l_b, D_b = RLM - l_b, DMX = max D_b
    function automatic integer rlat(input integer b);
        reg [63:0] v;
        begin
            v = (RD_LAT >> 8 == 64'd0) ? RD_LAT : (RD_LAT >> (8 * b));
            rlat = v[7:0];
        end
    endfunction
    function automatic integer rl_max(input integer dummy);
        integer b2;
        begin
            rl_max = 0;
            for (b2 = 0; b2 < 8; b2 = b2 + 1) if (rlat(b2) > rl_max) rl_max = rlat(b2);
        end
    endfunction
    localparam integer RLM = rl_max(0);
    function automatic integer dstag(input integer b);
        dstag = (MUT == 7) ? 0 : RLM - rlat(b);
    endfunction
    function automatic integer dst_max(input integer dummy);
        integer b2;
        begin
            dst_max = 0;
            for (b2 = 0; b2 < 8; b2 = b2 + 1) if (dstag(b2) > dst_max) dst_max = dstag(b2);
        end
    endfunction
    localparam integer DMX = dst_max(0);
    // ---- local reset relay
    wire rn;
    generate if (RST_PRE != 0) begin : g_rpre
        assign rn = rst_n;
    end else begin : g_rrel
        reg rs1, rs2, rnq;
        always @(posedge clk or negedge rst_n) if (!rst_n) {rs1, rs2, rnq} <= 3'b000; else {rs1, rs2, rnq} <= {1'b1, rs1, rs2};
        assign rn = rnq;
    end endgenerate
    assign rn_o = rn;
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) bf16 = x[31:16] | 16'h0040;
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; bf16 = r[31:16]; end
        end
    endfunction
    function automatic integer bslot(input integer bb);
        integer pp2; bslot = -1;
        for (pp2 = 0; pp2 < PMAX; pp2 = pp2 + 1)
            if (pp2 * XC + XOFF < bb * 2048 + 2048 && pp2 * XC + XOFF + 1024 > bb * 2048) bslot = pp2;
    endfunction
    // ---- command pin flops
    reg cmd_v; reg [39:0] c_base; reg [20:0] c_n; reg [3:0] c_p; reg [31:0] c_stride; reg [1:0] c_space, c_fmt; reg [6:0] c_xb;
    always @(posedge clk) begin
        c_base <= x_base; c_n <= x_n; c_p <= x_p; c_stride <= x_stride; c_space <= x_space; c_fmt <= x_fmt; c_xb <= x_xb;
    end
    wire c_bdf = c_fmt == 2'd1 || c_fmt == 2'd2;
    wire c_bad = c_space != 2'd1 || |c_base[2:0] || |c_stride[2:0] ||
                 c_p > PMAX || c_p == 4'd0 || c_n == 21'd0 || (c_bdf && |c_n[4:0]);
    reg [17:0] base, st; reg [3:0] pp; reg [20:0] kk; reg [7:0] gn; reg [10:0] ew; reg [6:0] xb;
    reg iss_on; reg [7:0] ig; reg [10:0] iw;
    reg em_on; reg [7:0] eg; reg [2:0] et; reg [6:0] eb;
    // ---- XP (HBM-XLP10 10-20): pipelined x-load.  The issue engine is free on the LAST ISSUE EDGE of a load (x_busy
    // falls there, the next command may start on that edge), so consecutive loads issue back to back.  Every field the
    // later stages need rides the fixed pipeline: per-wave bits (bdm, tpair-last, BF go marker + load id) in the md /
    // L / C / tag lines, and the per-load egress fields {bdf, la8, P, groups|tpairs, xb} in an NCTX-slot context ring
    // written at start and read by the load id at emission launch (BF: the go marker, RLM + 7 edges after the last wave
    // of group 0 = cl2's em_off; BD: the ring engine at its free edge or at the previous load's final tail).  x-store
    // rows and the BD write/emit tpair counts run continuously across loads.  Static: no ready, no stall; a command that
    // arrives while the issue is busy or its context slot is live, an emission launch over a running emission, a full
    // BD wait queue or a BF/BD beat collision at the egress is a sticky x_fault.
    localparam integer NCTX = 8;
    localparam integer CXW = 1 + 1 + 4 + 10 + 7;      // {bdf, la8, P, groups (BF gn) | tpairs (BD gtp), xb}
    function automatic [6:0] nb_of(input [3:0] p);
        nb_of = 7'((({12'd0, p} * 16'd3152) + 16'd2047) >> 11);
    endfunction
    reg [3:0] pp_e; reg [6:0] nb_e; reg [7:0] gn_e; reg [6:0] xb_e; reg [3:0] er;   // BF emission fields, x-store row
    reg [3:0] ir;                                      // running x-store group row of the BF issue
    wire bi_last;
    wire ii_last = iss_on && iw == ew - 11'd1 && ig == gn - 8'd1;
    wire iss_last = ii_last || bi_last;
    reg [2:0] id_w, id_i;                              // next load id (context slot) / id of the issuing load
    reg [NCTX-1:0] ctx_live;
    reg [CXW-1:0] ctx [0:NCTX-1];
    wire free_ok = !x_busy || iss_last;
    wire start = cmd_v && !c_bad && free_ok && !ctx_live[id_w];
    wire start_bf = start && !c_bdf, start_bd = start && c_bdf;
    wire [7:0] gn_c = 8'(((c_n - 21'd1) >> 9) + 21'd1);
    wire [9:0] gtp_c = 10'(((c_fmt == 2'd2) ? (((c_n - 21'd1) >> 11) + 21'd1) : (((c_n - 21'd1) >> 10) + 21'd1)) * 4);
    wire [CXW-1:0] nctx = {c_bdf, c_fmt == 2'd2, c_p, c_bdf ? gtp_c : {2'd0, gn_c}, c_xb};
    reg bdm;
    wire bd_fault;
    wire resp_bad;
    wire em_launch; wire [2:0] em_lid;                 // BF emission launch (go marker at the end of its fixed pipe)
    wire xp_fault;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin cmd_v <= 1'b0; x_busy <= 1'b0; x_fault <= 1'b0; iss_on <= 1'b0; id_w <= 3'd0; ir <= 4'd0; end
        else begin
            cmd_v <= x_v;
            if (cmd_v && (c_bad || !free_ok || ctx_live[id_w])) x_fault <= 1'b1;
            if (iss_last) x_busy <= 1'b0;
            if (ii_last) iss_on <= 1'b0;
            if (start) begin x_busy <= 1'b1; id_w <= id_w + 3'd1; end
            if (start_bf) iss_on <= 1'b1;
            if (iss_on && iw == ew - 11'd1) ir <= ir + 4'd1;
            if (resp_bad || bd_fault || xp_fault) x_fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        if (start) begin ctx[id_w] <= nctx; id_i <= id_w; end
    end
    // ---- BF issue: running word registers replace base + i_p x st + 512 ig (+ 64 i_wq)
    //   a_g  = base + 512 ig                (group origin)
    //   a_gp = base + 512 ig + i_p st       (wave row origin; + st when i_wq wraps, = a_g' at the group wrap)
    //   r_g  = K - 512 ig, r_w = K - 512 ig - 64 i_wq   (remaining elements; signed)
    reg [17:0] a_g, a_gp; reg signed [21:0] r_g, r_w;
    wire i_wrap = iw == ew - 11'd1;
    always @(posedge clk) begin
        if (start) bdm <= c_bdf;
        if (start) begin
            base <= c_base[17:0]; st <= c_stride[17:0]; pp <= c_p; kk <= c_n; xb <= c_xb;
            gn <= gn_c;
            ew <= 11'(((({12'd0, c_p} * 16'd3152) + 16'd2047) >> 11) * 8);
            ig <= 8'd0; iw <= 11'd0;
            a_g <= c_base[17:0]; a_gp <= c_base[17:0];
            r_g <= {1'b0, c_n}; r_w <= {1'b0, c_n};
        end else begin
            if (iss_on) begin
                if (i_wrap) begin
                    iw <= 11'd0; ig <= ig + 8'd1;
                    a_g <= a_g + 18'd512; a_gp <= a_g + 18'd512; r_g <= r_g - 22'sd512; r_w <= r_g - 22'sd512;
                end else begin
                    iw <= iw + 11'd1;
                    if (iw[2:0] == 3'd7) begin a_gp <= a_gp + st; r_w <= r_g; end
                    else r_w <= r_w - 22'sd64;
                end
            end
        end
    end
    wire iss_w = iss_on && iw < {4'd0, pp, 3'd0};
    // BF go marker: the last wave of group 0 (cl2's em_off = 8 P + RLM + LAND + 2 counts from it)
    wire i_go = iss_w && !bdm && ig == 8'd0 && iw == {4'd0, pp, 3'd0} - 11'd1;
    wire [3:0] i_p = iw[6:3];
    wire [2:0] i_wq = iw[2:0];
    wire [17:0] i_word = a_gp + {9'd0, i_wq, 6'd0};
    wire [14:0] i_s0_bf = i_word[17:3];
    wire bd_iss; wire [14:0] bd_s0; wire [16:0] bd_meta;
    wire w_iss = iss_w | bd_iss;
    wire [14:0] i_s0 = bdm ? bd_s0 : i_s0_bf;
    reg [7:0] q_v; reg [15:0] q_s [0:7];
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_rq
        assign rq[gl*17 +: 17] = {q_v[gl], q_s[gl]};
    end endgenerate
    // lane b carries the wave's sector whose bank is b: {s0[14:3] + (b < s0[2:0]), b}  (= s0 + ((b - s0) mod 8))
    generate if (DMX == 0) begin : g_iq0
        always @(posedge clk or negedge rn) if (!rn) q_v <= 8'd0; else q_v <= {8{w_iss}};
        wire [11:0] s_hi = i_s0[14:3], s_hi1 = i_s0[14:3] + 12'd1;
        always @(posedge clk) for (integer b = 0; b < 8; b = b + 1)
            q_s[b] <= {1'b0, (3'(b) < i_s0[2:0]) ? s_hi1 : s_hi, 3'(b)};
    end else begin : g_iqd
        // per-bank stagger: one shared tapped delay line of the wave issue {valid, s0}; lane b taps stage D_b
        reg [DMX-1:0] iq_v; reg [14:0] iq_s [0:DMX-1];
        always @(posedge clk or negedge rn) if (!rn) iq_v <= '0; else iq_v <= {iq_v, w_iss};
        always @(posedge clk) begin
            iq_s[0] <= i_s0;
            for (integer d = 1; d < DMX; d = d + 1) iq_s[d] <= iq_s[d-1];
        end
        for (genvar gb = 0; gb < 8; gb = gb + 1) begin : g_lane
            localparam integer DB = dstag(gb);
            wire tv; wire [14:0] ts;
            if (DB == 0) begin : g_d0
                assign tv = w_iss; assign ts = i_s0;
            end else begin : g_dn
                assign tv = iq_v[DB-1]; assign ts = iq_s[DB-1];
            end
            always @(posedge clk or negedge rn) if (!rn) q_v[gb] <= 1'b0; else q_v[gb] <= tv;
            always @(posedge clk) q_s[gb] <= {1'b0, (3'(gb) < ts[2:0]) ? ts[14:3] + 12'd1 : ts[14:3], 3'(gb)};
        end
    end endgenerate
    localparam integer MW = 1 + 4 + 3 + 3 + 3 + 7;
    localparam integer MX = MW + 5;        // XP: + {bdm, go, load id}
    reg [MX-1:0] md [0:RLM+1];             // + 1: rr is captured raw at the pins, rotated one edge later
    wire [6:0] i_rem = (r_w <= 22'sd0) ? 7'd0 : (r_w >= 22'sd64) ? 7'd64 : r_w[6:0];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d <= RLM + 1; d = d + 1) md[d] <= '0;
        else begin
            md[0] <= {bdm, i_go, id_i,
                      bdm ? {bd_iss, bd_meta[16:7], i_s0[2:0], bd_meta[6:0]} : {iss_w, ir, i_p[2:0], i_wq, i_s0[2:0], i_rem}};
            for (integer d = 1; d <= RLM + 1; d = d + 1) md[d] <= md[d-1];
        end
    end
    wire [MX-1:0] mr = md[RLM+1];
    wire m_v = mr[MW-1];
    wire m_bdm = mr[MX-1], m_go = mr[MX-2]; wire [2:0] m_id = mr[MX-3 -: 3];
    // raw rr pin registers (valid bits reset)
    reg [8*257-1:0] rr_c;
    always @(posedge clk or negedge rn)
        if (!rn) for (integer b = 0; b < 8; b = b + 1) rr_c[b*257 + 256] <= 1'b0;
        else for (integer b = 0; b < 8; b = b + 1) rr_c[b*257 + 256] <= rr[b*257 + 256];
    always @(posedge clk) for (integer b = 0; b < 8; b = b + 1) rr_c[b*257 +: 256] <= rr[b*257 +: 256];
    reg [7:0] rr_v_seen;
    always @* for (integer b = 0; b < 8; b = b + 1) rr_v_seen[b] = rr_c[b*257 + 256];
    assign resp_bad = (m_v && rr_v_seen != 8'hFF) || (!m_v && rr_v_seen != 8'h00);
    // ---- L: capture + rotate; the rotation select is replicated (NR copies of md[RLM][9:7], same edge)
    // cl2g (ctlw f20a route TT -58.79: rr_c / s0r / md -> rotation mux -> ~300 um wire -> l_d_o pin register, 399 paths):
    // the rotation result lands in L0 next to the rr pins and is re-registered in L1 (plain wire to the l_d_o pin
    // registers / the C stage).  + 1 edge on EVERY xw beat and x_done of both formats (LAND 3 -> 4, quantiser valids
    // and the BD tag line follow L1); rq unchanged.
    reg l0_v; reg [3:0] l0_g; reg [2:0] l0_p, l0_wq; reg [6:0] l0_rem; reg [8*256-1:0] l0_d;
    reg l_v; reg [3:0] l_g; reg [2:0] l_p, l_wq; reg [6:0] l_rem; reg [8*256-1:0] l_d;
    wire [2:0] s0r [0:NR-1];
    generate if (SEL_KEEP != 0) begin : g_s0k
        for (genvar k = 0; k < NR; k = k + 1) begin : g_r
            (* keep = 1 *) reg [2:0] q;
            always @(posedge clk or negedge rn) if (!rn) q <= 3'd0; else q <= md[RLM][9:7];
            assign s0r[k] = q;
        end
    end else begin : g_s0
        reg [2:0] s0q [0:NR-1];
        always @(posedge clk or negedge rn)
            if (!rn) for (integer k = 0; k < NR; k = k + 1) s0q[k] <= 3'd0;
            else for (integer k = 0; k < NR; k = k + 1) s0q[k] <= md[RLM][9:7];
        for (genvar k = 0; k < NR; k = k + 1) begin : g_a
            assign s0r[k] = s0q[k];
        end
    end endgenerate
    always @(posedge clk or negedge rn) if (!rn) begin l0_v <= 1'b0; l_v <= 1'b0; end else begin l0_v <= m_v; l_v <= l0_v; end
    reg l0_bdm, l_bdm;
    always @(posedge clk) begin l0_bdm <= m_bdm; l_bdm <= l0_bdm; end
    // go pipe: mr + 5 = cl2's (tc == em_off) edge; MUT 2: one edge early
    reg [4:0] gp_v; reg [2:0] gp_id [0:4];
    always @(posedge clk or negedge rn) if (!rn) gp_v <= 5'd0; else gp_v <= {gp_v[3:0], m_v && !m_bdm && m_go};
    always @(posedge clk) begin gp_id[0] <= m_id; for (integer d = 1; d < 5; d = d + 1) gp_id[d] <= gp_id[d-1]; end
    assign em_launch = (MUT == 2) ? gp_v[3] : gp_v[4];
    assign em_lid = (MUT == 2) ? gp_id[3] : gp_id[4];
    always @(posedge clk) begin
        {l0_g, l0_p, l0_wq} <= mr[MW-2 -: 10]; l0_rem <= mr[6:0];
        for (integer k = 0; k < NR; k = k + 1)
            l0_d[k*RB +: RB] <= rr_c[(3'(s0r[k] + 3'((k*RB) / 256) + ((MUT == 1) ? 3'd1 : 3'd0)))*257 + (k*RB) % 256 +: RB];
        {l_g, l_p, l_wq} <= {l0_g, l0_p, l0_wq}; l_rem <= l0_rem; l_d <= l0_d;
    end
    // l_dcs: the L1 data the C stage converts.  PIN_NATIVE n2 (10-18 gate n1: opt_merge folded the plain l_d into the
    // kept l_dpo, so ONE flop drove the E-face pins AND the W-side C stage, sat mid-tile, 2,048 l_d_o ports were "not
    // single-flop" for io_flop_at_pins and launched at 477 ps): the C stage reads its own kept copy l_dc (D = l0_d, same
    // edge), so l_dpo has the pins as its only load and is anchored at the E face.  Same function, same edges.
    wire [8*256-1:0] l_dcs;
    generate if (PIN_NATIVE != 0) begin : g_ldo
        (* keep = 1 *) reg [8*256-1:0] l_dpo;
        (* keep = 1 *) reg [8*256-1:0] l_dc;
        always @(posedge clk) begin l_dpo <= l0_d; l_dc <= l0_d; end
        assign l_d_o = l_dpo;
        assign l_dcs = l_dc;
    end else begin : g_ldw
        assign l_d_o = l_d;
        assign l_dcs = l_d;
    end endgenerate
    // quantiser valids registered with L1 (= l_v && bdm && l_wq[2] / [1] of cl)
    reg qv0_lo, qv0_hi;
    always @(posedge clk or negedge rn)
        if (!rn) begin qv0_lo <= 1'b0; qv0_hi <= 1'b0; qv_lo <= 1'b0; qv_hi <= 1'b0; end
        else begin qv0_lo <= m_v && m_bdm && mr[12]; qv0_hi <= m_v && m_bdm && mr[11]; qv_lo <= qv0_lo; qv_hi <= qv0_hi; end
    // ---- C: BF16 convert (was clk_bf in cl; same edge), with the per-quarter write enables of the W stage
    reg c_v; reg [3:0] c_g; reg [2:0] c_pp, c_wq;
    always @(posedge clk or negedge rn)
        if (!rn) begin c_v <= 1'b0; c_wce <= 4'd0; end
        else begin
            c_v <= l_v && !l_bdm;
            for (integer q = 0; q < 4; q = q + 1) c_wce[q] <= l_v && !l_bdm && l_wq[2:1] == 2'(q);
        end
    always @(posedge clk) begin
        c_g <= l_g; c_pp <= l_p; c_wq <= l_wq; c_wa <= {l_g, l_p};
        c_mhi <= l_wq[0] ^ (MUT == 4); c_mlo <= ~l_wq[0] ^ (MUT == 4);
        for (integer l = 0; l < 8; l = l + 1) for (integer tv = 0; tv < 8; tv = tv + 1)
            c_d[(tv*8 + l)*16 +: 16] <= (7'(l * 8 + tv) < l_rem) ? bf16(l_dcs[l*256 + 32*tv +: 32]) : 16'd0;
    end
    // ---- emission decision E0 (as cl) ...
    reg [3:0] e_slot; reg e_has;
    always @* begin
        e_has = 1'b0; e_slot = 4'd0;
        for (integer x = 0; x < NBMAX; x = x + 1)
            if (eb == 7'(x) && bslot(x) >= 0) begin e_has = 1'b1; e_slot = 4'(bslot(x)); end
    end
    wire e_slot_ok = em_on && e_has && e_slot < pp_e;
    // ... and its one-edge LOOKAHEAD: the macro read enables / address registered here hold, during cycle n, the E0
    // decision of cycle n, so the quarter's per-macro pin registers load it on the same edge as cl's rp_ce / rp_a.
    wire e_gend = em_on && et == 3'd7 && eb == nb_e - 7'd1;
    wire e_last = e_gend && eg == gn_e - 8'd1;
    wire [CXW-1:0] lctx = ctx[em_lid];
    reg em_on_n; reg [7:0] eg_n; reg [2:0] et_n; reg [6:0] eb_n; reg [3:0] pp_n; reg [3:0] er_n;
    reg [3:0] e_slot_n; reg e_has_n;
    always @* begin
        em_on_n = em_launch ? 1'b1 : e_last ? 1'b0 : em_on;
        er_n = er + (e_gend ? 4'd1 : 4'd0);
        eg_n = eg; et_n = et; eb_n = eb; pp_n = pp_e;
        if (em_launch) begin eg_n = 8'd0; et_n = 3'd0; eb_n = 7'd0; pp_n = lctx[20:17]; end
        else if (em_on) begin
            if (eb == nb_e - 7'd1) begin
                eb_n = 7'd0;
                if (et == 3'd7) begin et_n = 3'd0; eg_n = eg + 8'd1; end else et_n = et + 3'd1;
            end else eb_n = eb + 7'd1;
        end
        e_has_n = 1'b0; e_slot_n = 4'd0;
        for (integer x = 0; x < NBMAX; x = x + 1)
            if (eb_n == 7'(x) && bslot(x) >= 0) begin e_has_n = 1'b1; e_slot_n = 4'(bslot(x)); end
    end
    always @(posedge clk or negedge rn)
        if (!rn) r_ce <= 8'd0;
        else for (integer t = 0; t < 8; t = t + 1) r_ce[t] <= em_on_n && e_has_n && e_slot_n < pp_n && et_n == 3'(t);
    always @(posedge clk) r_a <= {er_n, e_slot_n[2:0]};
    always @(posedge clk or negedge rn) if (!rn) begin em_on <= 1'b0; er <= 4'd0; end else begin em_on <= em_on_n; er <= er_n; end
    always @(posedge clk) begin
        eg <= eg_n; et <= et_n; eb <= eb_n;
        if (em_launch) begin
            pp_e <= lctx[20:17]; nb_e <= nb_of(lctx[20:17]); gn_e <= lctx[14:7];
            xb_e <= (MUT == 8) ? xb : lctx[6:0];      // MUT 8: xb from the issue side (does not ride): must FAIL
        end
    end
    localparam integer EW = 1 + 1 + 1 + 7 + 7;
    reg [EW-1:0] ed [0:RDP-1];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d < RDP; d = d + 1) ed[d] <= '0;
        else begin
            ed[0] <= {em_on, e_slot_ok, e_last, 7'({eg[3:0], et} + xb_e), eb};
            for (integer d = 1; d < RDP; d = d + 1) ed[d] <= ed[d-1];
        end
    end
    // ---- rw: the quarters' rw registers are captured at the ctl pins (egress edge + 1)
    reg [1023:0] rw;
    always @(posedge clk_eg) rw <= rwq;
    // ---- beat select, replicated (ok, b) selects of ed[RDP-2] (each replica selects RB output bits)
    wire [2047:0] beats [0:NBMAX-1];
    genvar gb;
    generate for (gb = 0; gb < NBMAX; gb = gb + 1) begin : g_beat
        localparam integer PS = bslot(gb);
        localparam integer OFF = (PS < 0) ? 0 : PS * XC + XOFF - gb * 2048;
        if (PS < 0) begin : g_none
            assign beats[gb] = 2048'd0;
        end else if (OFF >= 0) begin : g_pos
            wire [4095:0] sh = {3072'd0, rw} << OFF;
            assign beats[gb] = sh[2047:0];
        end else begin : g_neg
            wire [1023:0] sh = rw >> (-OFF);
            assign beats[gb] = {1024'd0, sh};
        end
    end endgenerate
    wire [EW-1:0] e6 = ed[RDP-1];
    reg [7:0] e5r [0:NR-1];                // {ok, b} of ed[RDP-2], replicated
    always @(posedge clk_eg or negedge rn)
        if (!rn) for (integer k = 0; k < NR; k = k + 1) e5r[k] <= 8'd0;
        else for (integer k = 0; k < NR; k = k + 1) e5r[k] <= {ed[RDP-3][EW-2], ed[RDP-3][6:0]};
    reg [2047:0] xbeat;
    always @(posedge clk_eg) for (integer k = 0; k < NR; k = k + 1) begin
        xbeat[k*RB +: RB] <= {RB{1'b0}};
        if (e5r[k][7]) for (integer x = 0; x < NBMAX; x = x + 1) if (e5r[k][6:0] == 7'(x)) xbeat[k*RB +: RB] <= beats[x][k*RB +: RB];
    end
    // =================================================================================================================
    // BLOCK-DOT issue / tags / write stage / emission sequencer (as cl); the issue word is a running register.
    // =================================================================================================================
    localparam integer QL = 13;
    reg [3:0] la; reg [1:0] lsh; reg [15:0] nbk; reg [7:0] gnb; reg [9:0] gtp; reg [10:0] wb; reg [7:0] pla;
    reg bi_on; reg [9:0] bk; reg [10:0] bw;
    always @(posedge clk or negedge rn) begin
        if (!rn) bi_on <= 1'b0;
        else begin
            if (bi_last) bi_on <= 1'b0;
            if (start_bd) bi_on <= 1'b1;
        end
    end
    assign bi_last = bi_on && bw == wb - 11'd1 && bk == gtp - 10'd1;
    wire [6:0] nb_c = 7'((({12'd0, c_p} * 16'd3152) + 16'd2047) >> 11);
    wire [3:0] la_c = (c_fmt == 2'd2) ? 4'd8 : 4'd4;
    wire [7:0] pla_c = {4'd0, c_p} << ((c_fmt == 2'd2) ? 3 : 2);
    // running registers (b0 = (g LA + j) 8 + 2 tp; word = base + p st + 32 b0, mod 2^18):
    //   t_gla8 = 8 g LA, t_b0 = 8 g LA + 2 tp (tpair origin), c_b0 = t_b0 + 8 j
    //   t_gbase = base + 256 g LA, t_base = t_gbase + 64 tp, c_pst = t_base + p st, c_word = c_pst + 256 j
    reg [15:0] t_gla8, t_b0, c_b0; reg [17:0] t_gbase, t_base, c_pst, c_word;
    wire bw_wrap = bw == wb - 11'd1;
    wire bj_wrap = (bw & 11'(la - 4'd1)) == 11'(la - 4'd1);
    wire tp_wrap = bk[1:0] == 2'd3;
    wire [15:0] t_b0_nx = tp_wrap ? t_gla8 + {9'd0, la, 3'd0} : t_b0 + 16'd2;
    wire [17:0] t_base_nx = tp_wrap ? t_gbase + {6'd0, la, 8'd0} : t_base + 18'd64;
    always @(posedge clk) begin
        if (start_bd) begin
            la <= la_c; lsh <= (c_fmt == 2'd2) ? 2'd3 : 2'd2; nbk <= c_n[20:5];
            gnb <= (c_fmt == 2'd2) ? 8'(((c_n - 21'd1) >> 11) + 21'd1) : 8'(((c_n - 21'd1) >> 10) + 21'd1);
            gtp <= gtp_c;
            wb <= 11'((({3'd0, pla_c} > {1'b0, nb_c, 1'b0}) ? {3'd0, pla_c} : {3'd0, nb_c, 1'b0}) + 4);
            pla <= pla_c;
            bk <= 10'd0; bw <= 11'd0;
            t_gla8 <= 16'd0; t_b0 <= 16'd0; c_b0 <= 16'd0;
            t_gbase <= c_base[17:0]; t_base <= c_base[17:0]; c_pst <= c_base[17:0]; c_word <= c_base[17:0];
        end else begin
            if (bi_on) begin
                if (bw_wrap) begin
                    bw <= 11'd0; bk <= bk + 10'd1;
                    if (tp_wrap) begin t_gla8 <= t_gla8 + {9'd0, la, 3'd0}; t_gbase <= t_gbase + {6'd0, la, 8'd0}; end
                    t_b0 <= t_b0_nx; c_b0 <= t_b0_nx;
                    t_base <= t_base_nx; c_pst <= t_base_nx; c_word <= t_base_nx;
                end else begin
                    bw <= bw + 11'd1;
                    if (bj_wrap) begin c_b0 <= t_b0; c_pst <= c_pst + st; c_word <= c_pst + st; end
                    else begin c_b0 <= c_b0 + 16'd8; c_word <= c_word + 18'd256; end
                end
            end
        end
    end
    wire [3:0] b_p = 4'(bw >> lsh); wire [2:0] b_j = 3'(bw & 11'(la - 4'd1));
    assign bd_iss = bdm && bi_on && bw < (11'(pp) << lsh);
    assign bd_s0 = c_word[17:3];
    // XP: bit 0 = the last wave of its tpair (rides md -> L -> the tag line; the ring write count wraps on it)
    assign bd_meta = {bk[0], b_p[2:0], b_j, c_b0 < nbk, (c_b0 + 16'd1) < nbk, 1'b0, 6'd0, bw == {3'd0, pla} - 11'd1};
    reg [10:0] qt [0:QL-1];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d < QL; d = d + 1) qt[d] <= '0;
        else begin
            qt[0] <= {l_v && l_bdm, l_g[3], l_g[2:0], l_p, l_wq[2:1], l_rem[0]};
            for (integer d = 1; d < QL; d = d + 1) qt[d] <= qt[d-1];
        end
    end
    wire [10:0] qtl = qt[QL-1];
    // quantiser flags registered at the pins; the fault check compares them one edge later with the delayed tag
    reg qo_lo_c, qo_hi_c, qf_lo_c, qf_hi_c; reg [10:0] qtl_d;
    always @(posedge clk or negedge rn)
        if (!rn) begin qo_lo_c <= 1'b0; qo_hi_c <= 1'b0; qf_lo_c <= 1'b0; qf_hi_c <= 1'b0; qtl_d <= '0; end
        else begin qo_lo_c <= qo_lo; qo_hi_c <= qo_hi; qf_lo_c <= qf_lo; qf_hi_c <= qf_hi; qtl_d <= qtl; end
    assign bd_fault = (qo_lo_c && qf_lo_c) || (qo_hi_c && qf_hi_c) || (qtl_d[10] && (qtl_d[2] != qo_lo_c || qtl_d[1] != qo_hi_c));
    reg wv_b;
    // cl2d: the ring write controls leave ONE edge early (lookahead on the fixed tag delay line, qt[QL-2] = next qtl) so
    // the bdring leaf can capture them in pin registers on the same edge as its quantiser words wr_lo/wr_hi (native
    // capture: r_wsel/zlo/zhi no longer gate the 32 x 266 ring storage straight from the pins).  Ring write edge unchanged.
    wire [10:0] qtn = (MUT == 5) ? qtl : qt[QL-2];   // MUT 5: no lookahead (must FAIL the lock bench)
    always @(posedge clk or negedge rn)
        if (!rn) begin wv_b <= 1'b0; r_wsel <= 16'd0; end
        else begin
            wv_b <= qtl[10];
            for (integer s = 0; s < 16; s = s + 1)
                r_wsel[s] <= qtn[10] && {qtn[6], qtn[5:3] ^ ((MUT == 3) ? 3'd1 : 3'd0)} == 4'(s);
        end
    always @(posedge clk) begin zlo <= qtn[2]; zhi <= qtn[1]; end
    reg wtl; always @(posedge clk) wtl <= qtl[0];
    // XP: continuous ring write counts (wc lanes of the open tpair, wk tpairs written) -- never reset per load
    reg [6:0] wc; reg [9:0] wk;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin wc <= 7'd0; wk <= 10'd0; end
        else if (wv_b) begin
            if (wtl) begin wc <= 7'd0; wk <= wk + 10'd1; end else wc <= wc + 7'd1;
        end
    end
    localparam integer NBQ = (PMAX * XC + 2047) / 2048;
    function automatic integer nall(input integer lav, input integer bb);
        integer p2, j2; nall = 0;
        for (p2 = 0; p2 < PMAX; p2 = p2 + 1) for (j2 = 0; j2 < lav; j2 = j2 + 1)
            if (p2 * XC + 266 * j2 < 2048 * (bb + 1)) nall = nall + 1;
    endfunction
    reg be_on; reg [9:0] ek, ekg; reg ea; reg [6:0] eb2;
    reg [9:0] gtp_e; reg [3:0] la_e; reg [7:0] pla_e; reg [6:0] nb_b, xb_b;   // BD engine fields (from the context)
    // BD loads started while the engine still emits an earlier one wait in start order (FIFO of load ids)
    reg [2:0] bq_id [0:NCTX-1]; reg [2:0] bq_wp, bq_rp; reg [3:0] bq_n;
    wire bp_v = bq_n != 4'd0; wire [2:0] bp_id = bq_id[bq_rp];
    // cl2e (ctl cl2d TT -92.5: la/lane_en flop -> need table lookup -> wc >= need -> bd_em -> eb2 next state -> one-hot
    // decode -> bsel, ~8 levels + 400 ps of wire): need(eb2) and (eb2 == nb - 1) are REGISTERED one edge ahead from
    // the next-state eb2 and the next-state la/pla/nb, so bd_em and the one-hot decode see plain flops.  Same values on
    // every edge (need_q == need(eb2), eb2_last == (eb2 == nb - 1)); no edge added.
    function automatic [7:0] need_of(input [6:0] b, input [3:0] l, input [7:0] pl);
        need_of = 8'd0;
        for (integer x = 0; x < NBQ; x = x + 1)
            if (b == 7'(x)) need_of = (l == 4'd8) ? 8'(nall(8, x)) : 8'(nall(4, x));
        if (need_of > pl) need_of = pl;
        if (MUT == 2 && need_of != 8'd0) need_of = need_of - 8'd1;
    endfunction
    reg [7:0] need_q; reg eb2_last;
    wire pair_rdy = (ekg != wk) || ({1'b0, wc} >= need_q);
    wire bd_em = be_on && (ea || pair_rdy);
    wire bd_tail = bd_em && ea && eb2_last;
    wire bd_fin = bd_tail && ek == gtp_e - 10'd1;
    wire ld_new = start_bd && (!be_on || bd_fin) && !bp_v;   // engine free (or freeing on this edge): load the command
    wire ld_pend = bd_fin && bp_v;                           // final tail: load the pending load's context
    wire bd_ld = ld_new || ld_pend;
    wire [CXW-1:0] bctx = ld_pend ? ctx[bp_id] : nctx;
    wire bd_la8 = bctx[CXW-2]; wire [3:0] bd_p = bctx[20:17];
    always @(posedge clk or negedge rn) begin
        if (!rn) begin be_on <= 1'b0; bq_wp <= 3'd0; bq_rp <= 3'd0; bq_n <= 4'd0; ekg <= 10'd0; end
        else begin
            if (bd_fin) be_on <= 1'b0;
            if (bd_ld) be_on <= 1'b1;
            if (ld_pend) bq_rp <= bq_rp + 3'd1;
            if (start_bd && !ld_new) bq_wp <= bq_wp + 3'd1;
            bq_n <= bq_n + ((start_bd && !ld_new) ? 4'd1 : 4'd0) - (ld_pend ? 4'd1 : 4'd0);
            if (bd_tail) ekg <= ekg + 10'd1;
        end
    end
    always @(posedge clk) if (start_bd && !ld_new) bq_id[bq_wp] <= id_w;
    always @(posedge clk) if (bd_ld) begin
        gtp_e <= bctx[16:7]; la_e <= bd_la8 ? 4'd8 : 4'd4; pla_e <= {4'd0, bd_p} << (bd_la8 ? 3 : 2); nb_b <= nb_of(bd_p);
        xb_b <= (MUT == 8 && ld_pend) ? xb : bctx[6:0];         // MUT 8: xb from the issue side (does not ride)
    end
    // context slots: live from start to the launch that copies them (BF go marker / BD engine load)
    always @(posedge clk or negedge rn) begin
        if (!rn) ctx_live <= '0;
        else for (integer k = 0; k < NCTX; k = k + 1) begin
            if ((em_launch && em_lid == 3'(k)) || (ld_pend && bp_id == 3'(k))) ctx_live[k] <= 1'b0;
            if (start && !ld_new && id_w == 3'(k)) ctx_live[k] <= 1'b1;
        end
    end
    // BD beat select exported ONE-HOT (bdring cl2a TT -78.7: bsb replica -> 13-way decode -> 2048-b mux; the decode now
    // happens here on the counters' next state, so the ring leaf's select registers load a one-hot word, same edge).
    reg ea_n; reg [6:0] eb2_n; reg [9:0] ek_n;
    always @* begin
        ea_n = ea; eb2_n = eb2; ek_n = ek;
        if (bd_ld) begin ek_n = 10'd0; eb2_n = 7'd0; ea_n = 1'b0; end
        else if (bd_em) begin
            ea_n = ~ea;
            if (ea) begin
                if (eb2_last) begin eb2_n = 7'd0; ek_n = ek + 10'd1; end else eb2_n = eb2 + 7'd1;
            end
        end
    end
    wire [3:0] la_nx = bd_ld ? (bd_la8 ? 4'd8 : 4'd4) : la_e;
    wire [7:0] pla_nx = bd_ld ? ({4'd0, bd_p} << (bd_la8 ? 3 : 2)) : pla_e;
    wire [6:0] nb_nx = bd_ld ? nb_of(bd_p) : nb_b;
    always @(posedge clk) begin
        ea <= ea_n; eb2 <= eb2_n; ek <= ek_n;
        need_q <= need_of(eb2_n, la_nx, pla_nx); eb2_last <= (eb2_n == nb_nx - 7'd1);
        for (integer x = 0; x < NBQ; x = x + 1) begin
            bsel[x] <= !ea_n && eb2_n == 7'(x); bsel[NBQ + x] <= ea_n && eb2_n == 7'(x);
        end
    end
    always @(posedge clk) if (bd_ld) for (integer l = 0; l < PMAX*8; l = l + 1)
        lane_en[l] <= (l / 8 < bd_p) && (l % 8 < (bd_la8 ? 8 : 4));
    reg bs_v, bs_last; reg [6:0] bs_b, bs_addr;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin bs_v <= 1'b0; bs_last <= 1'b0; end
        else begin bs_v <= bd_em; bs_last <= bd_fin; end
    end
    always @(posedge clk) begin
        bs_b <= eb2; bs_addr <= 7'({ek[5:0], ea}) + xb_b;
    end
    // bq_* (the ring leaf's beat register edge) and bc_* (that beat captured at the ctl pins, egress + 1)
    reg bq_v, bq_last; reg [6:0] bq_addr, bq_b;
    reg bc_v, bc_last; reg [6:0] bc_addr, bc_b; reg [2047:0] bq_c;
    reg [NR-1:0] bqvr;                     // bc_v replicated (xw data select)
    always @(posedge clk or negedge rn) begin
        if (!rn) begin bq_v <= 1'b0; bq_last <= 1'b0; end
        else begin bq_v <= bs_v; bq_last <= bs_last; end
    end
    always @(posedge clk_eg or negedge rn) begin
        if (!rn) begin bc_v <= 1'b0; bc_last <= 1'b0; bqvr <= '0; end
        else begin bc_v <= bq_v; bc_last <= bq_last; bqvr <= {NR{bq_v}}; end
    end
    always @(posedge clk) begin bq_addr <= bs_addr; bq_b <= bs_b; end
    always @(posedge clk_eg) begin bc_addr <= bq_addr; bc_b <= bq_b; bq_c <= bq_d; end
    // ---- XQL: egress controls exported to the pair-egress leaves (their pin registers = this module's clk_eg stage)
    generate if (EGRESS_SPLIT != 0) begin : g_egx
        // x6 pegress pin-registers ed5 and bq_v once at its E face: export them one edge early (ed[RDP-4], bs_v) so the
        // leaf's replicas see exactly ed[RDP-3] / bq_v as before (0 added edges).
        assign eg_ed5 = {ed[RDP-4][EW-2], ed[RDP-4][6:0]}; assign eg_ede = ed[RDP-2];
        assign eg_bqv = bs_v; assign eg_bqlast = bq_last; assign eg_bqaddr = bq_addr; assign eg_bqb = bq_b;
    end else begin : g_egx0
        assign eg_ed5 = 8'd0; assign eg_ede = '0; assign eg_bqv = 1'b0; assign eg_bqlast = 1'b0; assign eg_bqaddr = 7'd0; assign eg_bqb = 7'd0;
    end endgenerate
    // ---- xw pins (egress root)
    always @(posedge clk_eg or negedge rn) begin
        if (!rn) begin xw_en <= 1'b0; xw_last <= 1'b0; x_done <= 1'b0; end
        else begin
            xw_en <= e6[EW-1] || bc_v; xw_last <= (e6[EW-1] && e6[EW-3]) || bc_last;
            x_done <= xw_en && xw_last;
        end
    end
    // XP status / faults: loads in flight (start .. x_done); BF launch over a running emission; a full BD
    // wait queue; a BF and a BD beat on the same egress edge (the compiler law keeps every load's beats disjoint)
    reg [3:0] nout;
    always @(posedge clk or negedge rn)
        if (!rn) nout <= 4'd0; else nout <= nout + (start ? 4'd1 : 4'd0) - (x_done ? 4'd1 : 4'd0);
    assign x_act = x_busy || nout != 4'd0;
    assign xp_fault = (em_launch && em_on && !e_last) || (start_bd && !ld_new && bq_n == 4'(NCTX)) || (e6[EW-1] && bc_v);
    always @(posedge clk_eg) begin
        if (bc_v) begin xw_addr <= bc_addr; xw_grp <= bc_b; end
        else begin xw_addr <= e6[13:7]; xw_grp <= e6[6:0]; end
        for (integer k = 0; k < NR; k = k + 1) xw_data[k*RB +: RB] <= bqvr[k] ? bq_c[k*RB +: RB] : xbeat[k*RB +: RB];
    end
endmodule

module ot_hgi_sm_xload_cl2xp_ctlw #(
    parameter integer PMAX   = 8,
    parameter [63:0]  RD_LAT = 64'd6,    // scalar or per-bank vector (ot_hgi_sm_xload_cl2_ctl RD_LAT)
    parameter integer MUT    = 0,
    parameter integer NR     = 32,
    parameter integer LEAD   = 8,
    parameter integer EGRESS_SPLIT = 0,  // XQL: export the egress controls (eg_*), see ot_hgi_sm_xload_static_xql
    parameter integer SEL_KEEP = 0,      // kept rotation-select replicas (ot_hgi_sm_xload_cl2_ctl SEL_KEEP)
    parameter integer PIN_NATIVE = 0,    // ot_hgi_sm_xload_cl2_ctl PIN_NATIVE (l_d_o pin register copy)
    parameter integer RST_PRE = 0        // rst_n already relayed (ctlx pin relay); see ot_hgi_sm_xload_cl2_ctl
) (
    input  wire               clk,
    input  wire               clk_eg,
    input  wire               clk_cal,   // hard clock entry of the issuer's calendar SRAM only (die: phi - R, as the DMA fold's clk_tab)
    input  wire               rst_n,
    input  wire [7:0]         tgt,       // identity strap (x-load issuer TARGET 100 + QID), die constant
    input  wire               cfg_v,
    input  wire [7:0]         cfg_target,
    input  wire [11:0]        cfg_addr,
    input  wire [255:0]       cfg_data,
    input  wire               desc_v,
    input  wire [11:0]        desc_base,
    input  wire [12:0]        desc_limit,
    input  wire [15:0]        desc_loops,
    input  wire               launch_v,
    output wire               configured,
    output wire               fault,
    output wire               active,
    output wire               x_done,
    output wire               xw_en,
    output wire               xw_last,
    output wire [6:0]         xw_addr,
    output wire [6:0]         xw_grp,
    output wire [2047:0]      xw_data,
    output wire [8*17-1:0]    rq,
    input  wire [8*257-1:0]   rr,
    output wire               rn_o,
    output wire [1023:0]      c_d,
    output wire [3:0]         c_wce,
    output wire               c_mhi, c_mlo,
    output wire [6:0]         c_wa,
    output wire [7:0]         r_ce,
    output wire [6:0]         r_a,
    input  wire [1023:0]      rwq,
    output wire [2047:0]      l_d_o,
    output wire               qv_lo, qv_hi,
    input  wire               qo_lo, qo_hi, qf_lo, qf_hi,
    output wire [15:0]        r_wsel,
    output wire               zlo, zhi,
    output wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,
    output wire [PMAX*8-1:0]  lane_en,
    input  wire [2047:0]      bq_d,
    output wire [7:0]         eg_ed5,
    output wire [16:0]        eg_ede,
    output wire               eg_bqv, eg_bqlast,
    output wire [6:0]         eg_bqaddr, eg_bqb
);
    wire x_v, x_busy, x_act, x_fault; wire [107:0] xc;
    // issuer = ot_static_cmd_target_core + its calendar SRAM on the hard entry clk_cal (the multiple_cts_roots flow lets a
    // CTS root reach standard-cell clock pins only; same pattern as ot_hgi_dma_back_static_vp4_banks_cp's clk_tab)
    wire t_rce; wire [6:0] t_raddr, t_waddr; wire [0:0] t_wce; wire [255:0] t_wdata, t_rd;
    ot_static_cmd_target_core #(.TARGET(8'hff), .MODE(1), .CW(108), .RELF(0), .NA(1), .NF(1), .LEAD(LEAD),
                                .MUT((MUT == 6) ? 1 : 0), .TGT_PIN(1)) u_iss (
        .clk(clk), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .tgt_active(x_act), .tgt_fault(x_fault),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(x_v), .cmd(xc), .cycle(), .configured(configured), .fault(fault), .active(active),
        .tab_r_ce(t_rce), .tab_r_addr(t_raddr), .tab_rd_word(t_rd), .tab_w_ce(t_wce), .tab_w_addr(t_waddr), .tab_w_data(t_wdata));
    ot_sram_1r1w_128x256_m1_r2c2 u_tab (.clk(clk_cal), .r_ce_in(t_rce), .r_addr_in(t_raddr), .rd_out(t_rd),
        .w_ce_in(t_wce[0]), .w_addr_in(t_waddr), .wd_in(t_wdata), .w_mask_in({256{1'b1}}),
        .rr_en(2'b0), .rr_addr(12'b0), .cr_en(2'b0), .cr_sel(16'b0));
    // cmd = {x_xb7, x_fmt2, x_space2, x_stride32, x_p4, x_n21, x_base40} (die contract v16 cp1_194..201)
    ot_hgi_sm_xload_cl2xp_ctl #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT((MUT <= 5 || MUT == 7 || MUT == 8) ? MUT : 0), .NR(NR), .EGRESS_SPLIT(EGRESS_SPLIT), .SEL_KEEP(SEL_KEEP),
                            .PIN_NATIVE(PIN_NATIVE), .RST_PRE(RST_PRE)) u_ctl (
        .clk(clk), .clk_eg(clk_eg), .rst_n(rst_n), .x_v(x_v), .x_base(xc[39:0]), .x_n(xc[60:40]), .x_p(xc[64:61]),
        .x_stride(xc[96:65]), .x_space(xc[98:97]), .x_fmt(xc[100:99]), .x_xb(xc[107:101]),
        .x_busy(x_busy), .x_act(x_act), .x_done(x_done), .x_fault(x_fault), .xw_en(xw_en), .xw_last(xw_last), .xw_addr(xw_addr),
        .xw_grp(xw_grp), .xw_data(xw_data), .rq(rq), .rr(rr), .rn_o(rn_o), .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi),
        .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(rwq), .l_d_o(l_d_o), .qv_lo(qv_lo), .qv_hi(qv_hi),
        .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi), .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel),
        .lane_en(lane_en), .bq_d(bq_d), .eg_ed5(eg_ed5), .eg_ede(eg_ede), .eg_bqv(eg_bqv), .eg_bqlast(eg_bqlast),
        .eg_bqaddr(eg_bqaddr), .eg_bqb(eg_bqb));
endmodule

// =====================================================================================================================
// ot_hgi_sm_xload_cl2_ctlx (HBM-B 10-17): the d4f die master of the x-load control leaf under XQL.  The d4f contract binds
// ctlw with EGRESS_SPLIT 1: the x egress (xw_*, x_done) leaves through the pair-egress leaves, so xw_* / x_done are open
// on the die and rwq / bq_d are undriven -- 5,121 of ctlw's 10,920 pin bits carry nothing, yet a ctlw hard tile keeps the
// whole xw egress datapath and its pins (f20a route: 11,007 pins, ~8-9 pins/um on W/E, util 0.14, TT -58.79).
// ctlx = ctlw EGRESS_SPLIT 1 with exactly the ports the die connects, rwq / bq_d = 0 and xw_* / x_done unconnected
// (the binding ot_hgi_sm_xload_static_xql already uses for ctlw), clk_eg = clk (its remaining sinks are the egress
// stage, phase 0 of clk, as in the XQL binding), and kept rotation-select replicas (SEL_KEEP 1).
// Every connected port has ctlw's function and edges; the XQL lock bench (XLOAD_XQL) runs through this module.
// =====================================================================================================================
module ot_hgi_sm_xload_cl2xp_ctlx #(
    parameter integer PMAX   = 8,
    parameter [63:0]  RD_LAT = 64'd6,    // scalar or per-bank vector (ot_hgi_sm_xload_cl2_ctl RD_LAT; die contract list)
    parameter integer MUT    = 0,
    parameter integer NR     = 32,
    parameter integer LEAD   = 8
) (
    input  wire               clk,
    input  wire               clk_cal,
    input  wire               rst_n,
    input  wire [7:0]         tgt,
    input  wire               cfg_v,
    input  wire [7:0]         cfg_target,
    input  wire [11:0]        cfg_addr,
    input  wire [255:0]       cfg_data,
    input  wire               desc_v,
    input  wire [11:0]        desc_base,
    input  wire [12:0]        desc_limit,
    input  wire [15:0]        desc_loops,
    input  wire               launch_v,
    output wire               configured,
    output wire               fault,
    output wire               active,
    output wire [8*17-1:0]    rq,
    input  wire [8*257-1:0]   rr,
    output wire               rn_o,
    output wire [1023:0]      c_d,
    output wire [3:0]         c_wce,
    output wire               c_mhi, c_mlo,
    output wire [6:0]         c_wa,
    output wire [7:0]         r_ce,
    output wire [6:0]         r_a,
    output wire [2047:0]      l_d_o,
    output wire               qv_lo, qv_hi,
    input  wire               qo_lo, qo_hi, qf_lo, qf_hi,
    output wire [15:0]        r_wsel,
    output wire               zlo, zhi,
    output wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,
    output wire [PMAX*8-1:0]  lane_en,
    output wire [7:0]         eg_ed5,
    output wire [16:0]        eg_ede,
    output wire               eg_bqv, eg_bqlast,
    output wire [6:0]         eg_bqaddr, eg_bqb
);
    // ELEM-GAPS/HBMN1 10-18 (native audit of CLOSED q1-7af6f4406: rst_n capture 455.7 ps): rst_n was the async clear
    // of the issuer (ot_static_cmd_target_core) flops and the ctl relay, i.e. a pin net across the tile.  Now the pin
    // drives ONE flop: rp1 (* keep *, async clear, D = 1) at the S face; rp2 / rq_n are plain flops (2-flop release
    // synchroniser behind rp1, no port load); rq_n is the tile's reset: issuer and ctl body (RST_PRE: no second relay).
    // Edges: assert reaches the issuer / ctl body 2 edges after rst_n falls (was 0 / 0); release 3 edges after rst_n
    // rises for both (was 0 issuer / 3 ctl body; rn_o unchanged at 3).  Data / command edges unchanged.
    // n2 (10-18 gate n1 probe: rn_o launched at 605 ps -- rn_o was rq_n itself, the reset net of 1,310 async clears):
    // rn_o now leaves from its own kept flop rn_q (D = rp2, the same edge as rq_n), anchored at the E-face rn_o pin.
    // rn_q == rq_n every cycle: rn_o assert / release edges unchanged.
    (* keep = 1 *) reg rp1;
    (* keep = 1 *) reg rp2, rq_n, rn_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rp1 <= 1'b0; else rp1 <= 1'b1;
    always @(posedge clk) begin rp2 <= rp1; rq_n <= rp2; rn_q <= rp2; end
    assign rn_o = rn_q;
    ot_hgi_sm_xload_cl2xp_ctlw #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT(MUT), .NR(NR), .LEAD(LEAD), .EGRESS_SPLIT(1), .SEL_KEEP(1),
                               .PIN_NATIVE(1), .RST_PRE(1)) u_w (
        .clk(clk), .clk_eg(clk), .clk_cal(clk_cal), .rst_n(rq_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target),
        .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit),
        .desc_loops(desc_loops), .launch_v(launch_v), .configured(configured), .fault(fault), .active(active),
        .x_done(), .xw_en(), .xw_last(), .xw_addr(), .xw_grp(), .xw_data(), .rq(rq), .rr(rr), .rn_o(),
        .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi), .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(1024'd0),
        .l_d_o(l_d_o), .qv_lo(qv_lo), .qv_hi(qv_hi), .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi),
        .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel), .lane_en(lane_en), .bq_d(2048'd0),
        .eg_ed5(eg_ed5), .eg_ede(eg_ede), .eg_bqv(eg_bqv), .eg_bqlast(eg_bqlast), .eg_bqaddr(eg_bqaddr), .eg_bqb(eg_bqb));
endmodule
`default_nettype wire
