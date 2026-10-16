`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// ot_hgi_sm_xload_static_cl2 (H-SM 2026-10-15 r2): the static SM x-load as a CLUSTER OF HARDENED LEAVES.
// Structural successor of ot_hgi_sm_xload_static_cl, whose flat --cts gate failed (ba59d8b41 kit hgi_sm_xload_cl_ref):
//   (a) flow rule: a multiple_cts_roots source reached the 32 x-store SRAMs (clk_bf);
//   (b) fanout: bs_a 8,642 loads (BD beat parity select), md[6][8] 5,635 (landing rotation select), bq_v 4,125 (xw mux);
//   (c) depth: bw -> rq 21 levels ~797 ps (b_p x stride multiply + three adds + lane rotation add), rr -> l_d 6 levels.
// Leaves (each its own single clock root, every root < 15k sinks by construction; same edges as cl, cycle for cycle):
//   ot_hgi_sm_xload_cl2_ctl    clk + clk_eg (egress root: rw / BD-beat capture, beat select, xw pins; related phase 0;
//                                      cl2a: one 16,281-sink root, pin-flop arrival 375..526 ps, IO hold repair stalled)
//                                      command, INCREMENTAL issue addressing (no multiply: running word registers),
//                                      rq, wave metadata, landing (replicated rotation selects), BF16 convert, emission
//                                      sequencers with a one-edge LOOKAHEAD of the macro read enables, BD tags / write
//                                      stage (one-hot ring enables), rw capture, beat select (replicated selects), xw pins.
//   ot_hgi_sm_xload_cl2_bfq    clk_bf  one lane quarter of the x-store: 8 SRAMs (t 0..7) with their per-macro pin
//                                      registers, gated capture and OR-4 tree; outputs the quarter's rw word.  4 instances
//                                      of ONE master (the quarter index is wiring at the parent).
//   ot_hbm_xp_aq_tree13        clk_qlo / clk_qhi  the two block-dot quantisers: the CLOSED quantiser tile (kit hgi_xp_aq,
//                                      TT +21.56 / FF +14.95; same ports and 13-edge latency as ot_hdc_actquant, input S0
//                                      and output registers at its pins), reused (fewer distinct tiles, owner 19:50).
//   ot_hgi_sm_xload_cl2_bdring clk_bd  block-dot lane ring (2 x 16 x 266), beat assembly and the beat register, with
//                                      local replicated parity / beat selects and a local lane-enable copy.
// OWNER RULE 2026-10-15 19:50: every input and output of every leaf is registered AT ITS PIN (an enable flop counts;
// no gate between a pin and its flop).  Two boundaries cannot keep cl's edges under that rule and each costs ONE
// fixed edge: (1) landing: rr is captured raw at the ctl pins, the lane rotation moves to the next stage (+1);
// (2) egress: the quarters' rw words and the BD beat register are captured at the ctl pins before the xw mux (+1).
// Issue (rq) edges are unchanged; every x-store beat and x_done leave exactly XW_ADD = 2 edges later than cl, for
// both formats (BF em_off + 1; the BD sequencer follows its lane writes).  The compiler model adds 2 to the first-beat
// / CBD constants.  tb_hgi_xload_static_lock (-DXLOAD_CL2) runs cl beside cl2: rq identical every cycle, every xw / done
// output identical to cl's 2 edges earlier, besides the lock against the production credited x-load.
// =====================================================================================================================

module ot_hgi_sm_xload_cl2_ctl #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,
    parameter integer MUT    = 0,
    parameter integer NR     = 32        // select replicas (each drives 2048 / NR data bits)
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
    output reg                x_busy,
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
    input  wire [2047:0]      bq_d
);
    localparam integer XC = 3152, XOFF = 2128;
    localparam integer NBMAX = (PMAX * XC + 2047) / 2048;
    localparam integer LAND = 3;
    localparam integer RDP = 7;            // + 1: rw captured at the ctl pins (egress edge)
    localparam integer RB = 2048 / NR;     // data bits per select replica
    // ---- local reset relay
    reg rs1, rs2, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rs1, rs2, rn} <= 3'b000; else {rs1, rs2, rn} <= {1'b1, rs1, rs2};
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
    reg [17:0] base, st; reg [3:0] pp; reg [20:0] kk; reg [7:0] gn; reg [6:0] nb; reg [10:0] ew; reg [6:0] xb;
    reg [10:0] em_off;
    reg iss_on; reg [7:0] ig; reg [10:0] iw;
    reg [10:0] tc; reg em_wait;
    reg em_on; reg [7:0] eg; reg [2:0] et; reg [6:0] eb;
    wire start = cmd_v && !c_bad && !x_busy;
    wire start_bf = start && !c_bdf, start_bd = start && c_bdf;
    reg bdm;
    wire bd_fault;
    wire resp_bad;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin cmd_v <= 1'b0; x_busy <= 1'b0; x_fault <= 1'b0; iss_on <= 1'b0; em_wait <= 1'b0; em_on <= 1'b0; end
        else begin
            cmd_v <= x_v;
            if (cmd_v && (c_bad || x_busy)) x_fault <= 1'b1;
            if (start) x_busy <= 1'b1;
            if (start_bf) begin iss_on <= 1'b1; em_wait <= 1'b1; end
            if (iss_on && iw == ew - 11'd1 && ig == gn - 8'd1) iss_on <= 1'b0;
            if (em_wait && tc == em_off) begin em_wait <= 1'b0; em_on <= 1'b1; end
            if (em_on && et == 3'd7 && eb == nb - 7'd1 && eg == gn - 8'd1) em_on <= 1'b0;
            if (x_done) x_busy <= 1'b0;
            if (resp_bad || bd_fault) x_fault <= 1'b1;
        end
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
            gn <= 8'(((c_n - 21'd1) >> 9) + 21'd1);
            nb <= 7'((({12'd0, c_p} * 16'd3152) + 16'd2047) >> 11);
            ew <= 11'(((({12'd0, c_p} * 16'd3152) + 16'd2047) >> 11) * 8);
            em_off <= (MUT == 2) ? 11'(RD_LAT) : 11'({c_p, 3'd0} + RD_LAT + LAND + 2);   // + 1: raw rr pin capture
            ig <= 8'd0; iw <= 11'd0; tc <= 11'd0; eg <= 8'd0; et <= 3'd0; eb <= 7'd0;
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
            if (em_wait) tc <= tc + 11'd1;
            if (em_on) begin
                if (eb == nb - 7'd1) begin
                    eb <= 7'd0;
                    if (et == 3'd7) begin et <= 3'd0; eg <= eg + 8'd1; end else et <= et + 3'd1;
                end else eb <= eb + 7'd1;
            end
        end
    end
    wire iss_w = iss_on && iw < {4'd0, pp, 3'd0};
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
    always @(posedge clk or negedge rn) if (!rn) q_v <= 8'd0; else q_v <= {8{w_iss}};
    // lane b carries the wave's sector whose bank is b: {s0[14:3] + (b < s0[2:0]), b}  (= s0 + ((b - s0) mod 8))
    wire [11:0] s_hi = i_s0[14:3], s_hi1 = i_s0[14:3] + 12'd1;
    always @(posedge clk) for (integer b = 0; b < 8; b = b + 1)
        q_s[b] <= {1'b0, (3'(b) < i_s0[2:0]) ? s_hi1 : s_hi, 3'(b)};
    localparam integer MW = 1 + 4 + 3 + 3 + 3 + 7;
    reg [MW-1:0] md [0:RD_LAT+1];          // + 1: rr is captured raw at the pins, rotated one edge later
    wire [6:0] i_rem = (r_w <= 22'sd0) ? 7'd0 : (r_w >= 22'sd64) ? 7'd64 : r_w[6:0];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d <= RD_LAT + 1; d = d + 1) md[d] <= '0;
        else begin
            md[0] <= bdm ? {bd_iss, bd_meta[16:7], i_s0[2:0], bd_meta[6:0]} : {iss_w, ig[3:0], i_p[2:0], i_wq, i_s0[2:0], i_rem};
            for (integer d = 1; d <= RD_LAT + 1; d = d + 1) md[d] <= md[d-1];
        end
    end
    wire [MW-1:0] mr = md[RD_LAT+1];
    wire m_v = mr[MW-1];
    // raw rr pin registers (valid bits reset)
    reg [8*257-1:0] rr_c;
    always @(posedge clk or negedge rn)
        if (!rn) for (integer b = 0; b < 8; b = b + 1) rr_c[b*257 + 256] <= 1'b0;
        else for (integer b = 0; b < 8; b = b + 1) rr_c[b*257 + 256] <= rr[b*257 + 256];
    always @(posedge clk) for (integer b = 0; b < 8; b = b + 1) rr_c[b*257 +: 256] <= rr[b*257 +: 256];
    reg [7:0] rr_v_seen;
    always @* for (integer b = 0; b < 8; b = b + 1) rr_v_seen[b] = rr_c[b*257 + 256];
    assign resp_bad = (m_v && rr_v_seen != 8'hFF) || (!m_v && rr_v_seen != 8'h00);
    // ---- L: capture + rotate; the rotation select is replicated (NR copies of md[RD_LAT][9:7], same edge)
    reg l_v; reg [3:0] l_g; reg [2:0] l_p, l_wq; reg [6:0] l_rem; reg [8*256-1:0] l_d;
    reg [2:0] s0r [0:NR-1];
    always @(posedge clk or negedge rn)
        if (!rn) for (integer k = 0; k < NR; k = k + 1) s0r[k] <= 3'd0;
        else for (integer k = 0; k < NR; k = k + 1) s0r[k] <= md[RD_LAT][9:7];
    always @(posedge clk or negedge rn) if (!rn) l_v <= 1'b0; else l_v <= m_v;
    always @(posedge clk) begin
        {l_g, l_p, l_wq} <= mr[MW-2 -: 10]; l_rem <= mr[6:0];
        for (integer k = 0; k < NR; k = k + 1)
            l_d[k*RB +: RB] <= rr_c[(3'(s0r[k] + 3'((k*RB) / 256) + ((MUT == 1) ? 3'd1 : 3'd0)))*257 + (k*RB) % 256 +: RB];
    end
    assign l_d_o = l_d;
    // quantiser valids registered on the landing edge (= l_v && bdm && l_wq[2] / [1] of cl)
    always @(posedge clk or negedge rn)
        if (!rn) begin qv_lo <= 1'b0; qv_hi <= 1'b0; end
        else begin qv_lo <= m_v && bdm && mr[12]; qv_hi <= m_v && bdm && mr[11]; end
    // ---- C: BF16 convert (was clk_bf in cl; same edge), with the per-quarter write enables of the W stage
    reg c_v; reg [3:0] c_g; reg [2:0] c_pp, c_wq;
    always @(posedge clk or negedge rn)
        if (!rn) begin c_v <= 1'b0; c_wce <= 4'd0; end
        else begin
            c_v <= l_v && !bdm;
            for (integer q = 0; q < 4; q = q + 1) c_wce[q] <= l_v && !bdm && l_wq[2:1] == 2'(q);
        end
    always @(posedge clk) begin
        c_g <= l_g; c_pp <= l_p; c_wq <= l_wq; c_wa <= {l_g, l_p};
        c_mhi <= l_wq[0] ^ (MUT == 4); c_mlo <= ~l_wq[0] ^ (MUT == 4);
        for (integer l = 0; l < 8; l = l + 1) for (integer tv = 0; tv < 8; tv = tv + 1)
            c_d[(tv*8 + l)*16 +: 16] <= (7'(l * 8 + tv) < l_rem) ? bf16(l_d[l*256 + 32*tv +: 32]) : 16'd0;
    end
    // ---- emission decision E0 (as cl) ...
    reg [3:0] e_slot; reg e_has;
    always @* begin
        e_has = 1'b0; e_slot = 4'd0;
        for (integer x = 0; x < NBMAX; x = x + 1)
            if (eb == 7'(x) && bslot(x) >= 0) begin e_has = 1'b1; e_slot = 4'(bslot(x)); end
    end
    wire e_slot_ok = em_on && e_has && e_slot < pp;
    // ... and its one-edge LOOKAHEAD: the macro read enables / address registered here hold, during cycle n, the E0
    // decision of cycle n, so the quarter's per-macro pin registers load it on the same edge as cl's rp_ce / rp_a.
    reg em_on_n; reg [7:0] eg_n; reg [2:0] et_n; reg [6:0] eb_n; reg [3:0] pp_n;
    reg [3:0] e_slot_n; reg e_has_n;
    always @* begin
        em_on_n = em_on;
        if (em_wait && tc == em_off) em_on_n = 1'b1;
        if (em_on && et == 3'd7 && eb == nb - 7'd1 && eg == gn - 8'd1) em_on_n = 1'b0;
        eg_n = eg; et_n = et; eb_n = eb; pp_n = pp;
        if (start) begin eg_n = 8'd0; et_n = 3'd0; eb_n = 7'd0; pp_n = c_p; end
        else if (em_on) begin
            if (eb == nb - 7'd1) begin
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
    always @(posedge clk) r_a <= {eg_n[3:0], e_slot_n[2:0]};
    localparam integer EW = 1 + 1 + 1 + 7 + 7;
    reg [EW-1:0] ed [0:RDP-1];
    wire e_last = em_on && et == 3'd7 && eb == nb - 7'd1 && eg == gn - 8'd1;
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d < RDP; d = d + 1) ed[d] <= '0;
        else begin
            ed[0] <= {em_on, e_slot_ok, e_last, 7'({eg[3:0], et} + xb), eb};
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
            if (start_bd) bi_on <= 1'b1;
            if (bi_on && bw == wb - 11'd1 && bk == gtp - 10'd1) bi_on <= 1'b0;
        end
    end
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
            gtp <= 10'(((c_fmt == 2'd2) ? (((c_n - 21'd1) >> 11) + 21'd1) : (((c_n - 21'd1) >> 10) + 21'd1)) * 4);
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
    assign bd_meta = {bk[0], b_p[2:0], b_j, c_b0 < nbk, (c_b0 + 16'd1) < nbk, 1'b0, 7'd0};
    reg [9:0] qt [0:QL-1];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d < QL; d = d + 1) qt[d] <= '0;
        else begin
            qt[0] <= {l_v && bdm, l_g[3], l_g[2:0], l_p, l_wq[2:1]};
            for (integer d = 1; d < QL; d = d + 1) qt[d] <= qt[d-1];
        end
    end
    wire [9:0] qtl = qt[QL-1];
    // quantiser flags registered at the pins; the fault check compares them one edge later with the delayed tag
    reg qo_lo_c, qo_hi_c, qf_lo_c, qf_hi_c; reg [9:0] qtl_d;
    always @(posedge clk or negedge rn)
        if (!rn) begin qo_lo_c <= 1'b0; qo_hi_c <= 1'b0; qf_lo_c <= 1'b0; qf_hi_c <= 1'b0; qtl_d <= '0; end
        else begin qo_lo_c <= qo_lo; qo_hi_c <= qo_hi; qf_lo_c <= qf_lo; qf_hi_c <= qf_hi; qtl_d <= qtl; end
    assign bd_fault = (qo_lo_c && qf_lo_c) || (qo_hi_c && qf_hi_c) || (qtl_d[9] && (qtl_d[1] != qo_lo_c || qtl_d[0] != qo_hi_c));
    reg wv_b;
    always @(posedge clk or negedge rn)
        if (!rn) begin wv_b <= 1'b0; r_wsel <= 16'd0; end
        else begin
            wv_b <= qtl[9];
            for (integer s = 0; s < 16; s = s + 1)
                r_wsel[s] <= qtl[9] && {qtl[5], qtl[4:2] ^ ((MUT == 3) ? 3'd1 : 3'd0)} == 4'(s);
        end
    always @(posedge clk) begin zlo <= qtl[1]; zhi <= qtl[0]; end
    reg [6:0] wc; reg [9:0] wk;
    always @(posedge clk) begin
        if (start_bd) begin wc <= 7'd0; wk <= 10'd0; end
        else if (wv_b) begin
            if ({1'b0, wc} == pla - 8'd1) begin wc <= 7'd0; wk <= wk + 10'd1; end else wc <= wc + 7'd1;
        end
    end
    localparam integer NBQ = (PMAX * XC + 2047) / 2048;
    function automatic integer nall(input integer lav, input integer bb);
        integer p2, j2; nall = 0;
        for (p2 = 0; p2 < PMAX; p2 = p2 + 1) for (j2 = 0; j2 < lav; j2 = j2 + 1)
            if (p2 * XC + 266 * j2 < 2048 * (bb + 1)) nall = nall + 1;
    endfunction
    reg be_on; reg [9:0] ek; reg ea; reg [6:0] eb2;
    reg [7:0] need;
    always @* begin
        need = 8'd0;
        for (integer x = 0; x < NBQ; x = x + 1)
            if (eb2 == 7'(x)) need = (la == 4'd8) ? 8'(nall(8, x)) : 8'(nall(4, x));
        if (need > pla) need = pla;
        if (MUT == 2 && need != 8'd0) need = need - 8'd1;
    end
    wire pair_rdy = (ek < wk) || ({1'b0, wc} >= need);
    wire bd_em = be_on && (ea || pair_rdy);
    wire bd_tail = bd_em && ea && eb2 == nb - 7'd1;
    always @(posedge clk or negedge rn) begin
        if (!rn) be_on <= 1'b0;
        else begin
            if (start_bd) be_on <= 1'b1;
            if (bd_tail && ek == gtp - 10'd1) be_on <= 1'b0;
        end
    end
    // BD beat select exported ONE-HOT (bdring cl2a TT -78.7: bsb replica -> 13-way decode -> 2048-b mux; the decode now
    // happens here on the counters' next state, so the ring leaf's select registers load a one-hot word, same edge).
    reg ea_n; reg [6:0] eb2_n; reg [9:0] ek_n;
    always @* begin
        ea_n = ea; eb2_n = eb2; ek_n = ek;
        if (start_bd) begin ek_n = 10'd0; eb2_n = 7'd0; ea_n = 1'b0; end
        else if (bd_em) begin
            ea_n = ~ea;
            if (ea) begin
                if (eb2 == nb - 7'd1) begin eb2_n = 7'd0; ek_n = ek + 10'd1; end else eb2_n = eb2 + 7'd1;
            end
        end
    end
    always @(posedge clk) begin
        ea <= ea_n; eb2 <= eb2_n; ek <= ek_n;
        for (integer x = 0; x < NBQ; x = x + 1) begin
            bsel[x] <= !ea_n && eb2_n == 7'(x); bsel[NBQ + x] <= ea_n && eb2_n == 7'(x);
        end
    end
    always @(posedge clk) if (start_bd) for (integer l = 0; l < PMAX*8; l = l + 1)
        lane_en[l] <= (l / 8 < c_p) && (l % 8 < ((c_fmt == 2'd2) ? 8 : 4));
    reg bs_v, bs_last; reg [6:0] bs_b, bs_addr;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin bs_v <= 1'b0; bs_last <= 1'b0; end
        else begin bs_v <= bd_em; bs_last <= bd_tail && ek == gtp - 10'd1; end
    end
    always @(posedge clk) begin
        bs_b <= eb2; bs_addr <= 7'({ek[5:0], ea}) + xb;
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
    // ---- xw pins (egress root)
    always @(posedge clk_eg or negedge rn) begin
        if (!rn) begin xw_en <= 1'b0; xw_last <= 1'b0; x_done <= 1'b0; end
        else begin
            xw_en <= e6[EW-1] || bc_v; xw_last <= (e6[EW-1] && e6[EW-3]) || bc_last;
            x_done <= xw_en && xw_last;
        end
    end
    always @(posedge clk_eg) begin
        if (bc_v) begin xw_addr <= bc_addr; xw_grp <= bc_b; end
        else begin xw_addr <= e6[13:7]; xw_grp <= e6[6:0]; end
        for (integer k = 0; k < NR; k = k + 1) xw_data[k*RB +: RB] <= bqvr[k] ? bq_c[k*RB +: RB] : xbeat[k*RB +: RB];
    end
endmodule

// One lane quarter of the BF16 x-store: macros m[t] (t < 8) with per-macro pin registers, gated capture, OR-4 tree.
module ot_hgi_sm_xload_cl2_bfq (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [1023:0]      c_d,       // c_d[(t 8 + l) 16 +: 16]
    input  wire               wce,
    input  wire               mhi, mlo,
    input  wire [6:0]         wa,
    input  wire [7:0]         r_ce,
    input  wire [6:0]         r_a,
    output reg  [255:0]       rwq
);
    wire [255:0] cap [0:7];
    genvar gt;
    generate for (gt = 0; gt < 8; gt = gt + 1) begin : g_t
        (* keep = 1 *) reg rp_ce; (* keep = 1 *) reg [6:0] rp_a; reg rp_sel;
        (* keep = 1 *) reg wp_ce; (* keep = 1 *) reg [6:0] wp_a; reg [255:0] wp_d;
        (* keep = 1 *) reg mask_hi, mask_lo;
        wire [255:0] wp_m = {{128{mask_hi}}, {128{mask_lo}}};
        reg [255:0] cq;
        wire [255:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin rp_ce <= 1'b0; rp_sel <= 1'b0; wp_ce <= 1'b0; end
            else begin rp_ce <= r_ce[gt]; rp_sel <= rp_ce; wp_ce <= wce; end
        end
        always @(posedge clk) begin
            mask_hi <= mhi; mask_lo <= mlo;
            rp_a <= r_a; wp_a <= wa;
            for (integer l = 0; l < 8; l = l + 1) begin
                wp_d[16*l +: 16] <= c_d[(gt*8 + l)*16 +: 16];
                wp_d[128 + 16*l +: 16] <= c_d[(gt*8 + l)*16 +: 16];
            end
            cq <= rd & {256{rp_sel}};
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk),
            .r_ce_in(rp_ce), .r_addr_in(rp_a), .rd_out(rd),
            .w_ce_in(wp_ce), .w_addr_in(wp_a), .wd_in(wp_d), .w_mask_in(wp_m),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign cap[gt] = cq;
    end endgenerate
    reg [255:0] or4a, or4b;
    always @(posedge clk) begin
        or4a <= cap[0] | cap[1] | cap[2] | cap[3];
        or4b <= cap[4] | cap[5] | cap[6] | cap[7];
    end
    always @(posedge clk) rwq <= or4a | or4b;   // cl's rw edge
endmodule

// Block-dot lane ring + beat assembly + beat register (cl's ring / beat_w / bsel / bq_d), local replicated selects.
module ot_hgi_sm_xload_cl2_bdring #(
    parameter integer PMAX = 8,
    parameter integer NR   = 64
) (
    input  wire               clk,
    input  wire [15:0]        r_wsel,
    input  wire               zlo, zhi,
    input  wire [255:0]       qq_lo, qq_hi,
    input  wire signed [9:0]  qe_lo, qe_hi,
    input  wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,  // one-hot {parity, beat} (registered in ctl)
    input  wire [PMAX*8-1:0]  lane_en_i,
    output reg  [2047:0]      bq_d
);
    localparam integer XC = 3152;
    localparam integer NBQ = (PMAX * XC + 2047) / 2048;
    localparam integer RB = 2048 / NR;
    reg [PMAX*8-1:0] lane_en;              // local copy (command constant; refreshed every edge)
    always @(posedge clk) lane_en <= lane_en_i;
    reg [265:0] wr_lo, wr_hi;              // quantiser words registered at the pins (cl's wd edge)
    always @(posedge clk) begin wr_lo <= {qe_lo, qq_lo}; wr_hi <= {qe_hi, qq_hi}; end
    wire [265:0] wd_lo = zlo ? wr_lo : 266'd0, wd_hi = zhi ? wr_hi : 266'd0;
    wire [265:0] ring [0:1][0:15];
    genvar gpa, gsl;
    generate for (gpa = 0; gpa < 2; gpa = gpa + 1) begin : g_rp
        for (gsl = 0; gsl < 16; gsl = gsl + 1) begin : g_rs
            reg [265:0] w;
            always @(posedge clk) if (r_wsel[gsl]) w <= (gpa == 0) ? wd_lo : wd_hi;
            assign ring[gpa][gsl] = w;
        end
    end endgenerate
    wire [2047:0] beat_w [0:1][0:NBQ-1];
    genvar gbb2, gpp, gjj;
    generate for (gpa = 0; gpa < 2; gpa = gpa + 1) begin : g_ap
        for (gbb2 = 0; gbb2 < NBQ; gbb2 = gbb2 + 1) begin : g_ab
            wire [2047:0] parts [0:PMAX*8];
            assign parts[0] = 2048'd0;
            for (gpp = 0; gpp < PMAX; gpp = gpp + 1) begin : g_lp
                for (gjj = 0; gjj < 8; gjj = gjj + 1) begin : g_lj
                    localparam integer LI = gpp * 8 + gjj;
                    localparam integer ST = gpp * XC + 266 * gjj - 2048 * gbb2;
                    wire [265:0] lw = ring[gpa][(gpp % 2) * 8 + gjj] & {266{lane_en[LI]}};
                    if (ST >= 2048 || ST + 266 <= 0) begin : g_out
                        assign parts[LI + 1] = parts[LI];
                    end else if (ST >= 0) begin : g_in
                        wire [2048+266-1:0] sh = {2048'd0, lw} << ST;
                        assign parts[LI + 1] = parts[LI] | sh[2047:0];
                    end else begin : g_lo
                        wire [265:0] sh = lw >> (-ST);
                        assign parts[LI + 1] = parts[LI] | {1782'd0, sh};
                    end
                end
            end
            assign beat_w[gpa][gbb2] = parts[PMAX*8];
        end
    end endgenerate
    // NR replicas of the one-hot select (pin registers), each an AND-OR over 2 x NBQ beat words for RB output bits
    reg [2*NBQ-1:0] bs [0:NR-1];
    always @(posedge clk) for (integer k = 0; k < NR; k = k + 1) bs[k] <= bsel;
    always @(posedge clk) for (integer k = 0; k < NR; k = k + 1) begin : sel
        reg [RB-1:0] acc; acc = {RB{1'b0}};
        for (integer x = 0; x < NBQ; x = x + 1)
            acc = acc | ({RB{bs[k][x]}} & beat_w[0][x][k*RB +: RB]) | ({RB{bs[k][NBQ + x]}} & beat_w[1][x][k*RB +: RB]);
        bq_d[k*RB +: RB] <= acc;
    end
endmodule

// Wires-only parent: same ports, parameters and edges as ot_hgi_sm_xload_static_cl.
module ot_hgi_sm_xload_static_cl2 #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,
    parameter integer MUT    = 0
) (
    input  wire               clk,
    input  wire               clk_bf,
    input  wire               clk_qlo,
    input  wire               clk_qhi,
    input  wire               clk_bd,
    input  wire               rst_n,
    input  wire               x_v,
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    input  wire [6:0]         x_xb,
    output wire               x_busy,
    output wire               x_done,
    output wire               x_fault,
    output wire               xw_en,
    output wire               xw_last,
    output wire [6:0]         xw_addr,
    output wire [6:0]         xw_grp,
    output wire [2047:0]      xw_data,
    output wire [8*17-1:0]    rq,
    input  wire [8*257-1:0]   rr
);
    wire rn;
    wire [1023:0] c_d; wire [3:0] c_wce; wire c_mhi, c_mlo; wire [6:0] c_wa; wire [7:0] r_ce; wire [6:0] r_a;
    wire [1023:0] rwq;
    wire [2047:0] l_d; wire qv_lo, qv_hi, qo_lo, qo_hi, qf_lo, qf_hi; wire [255:0] qq_lo, qq_hi; wire signed [9:0] qe_lo, qe_hi;
    wire [15:0] r_wsel; wire zlo, zhi; wire [2*((PMAX*3152+2047)/2048)-1:0] bsel; wire [PMAX*8-1:0] lane_en; wire [2047:0] bq_d;
    ot_hgi_sm_xload_cl2_ctl #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT(MUT)) u_ctl (
        .clk(clk), .clk_eg(clk), .rst_n(rst_n), .x_v(x_v), .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space),
        .x_fmt(x_fmt), .x_xb(x_xb), .x_busy(x_busy), .x_done(x_done), .x_fault(x_fault), .xw_en(xw_en), .xw_last(xw_last),
        .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .rq(rq), .rr(rr), .rn_o(rn),
        .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi), .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(rwq),
        .l_d_o(l_d), .qv_lo(qv_lo), .qv_hi(qv_hi), .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi),
        .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel), .lane_en(lane_en), .bq_d(bq_d));
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
        ot_hgi_sm_xload_cl2_bfq u_bfq (.clk(clk_bf), .rst_n(rn), .c_d(c_d), .wce(c_wce[gq]), .mhi(c_mhi), .mlo(c_mlo),
            .wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(rwq[256*gq +: 256]));
    end endgenerate
    ot_hbm_xp_aq_tree13 u_aq_lo (.clk(clk_qlo), .rst_n(rn), .v(qv_lo), .fp4(1'b0), .x(l_d[1023:0]), .vo(qo_lo), .q(qq_lo),
                             .e(qe_lo), .y(), .fault(qf_lo));
    ot_hbm_xp_aq_tree13 u_aq_hi (.clk(clk_qhi), .rst_n(rn), .v(qv_hi), .fp4(1'b0), .x(l_d[2047:1024]), .vo(qo_hi), .q(qq_hi),
                             .e(qe_hi), .y(), .fault(qf_hi));
    ot_hgi_sm_xload_cl2_bdring #(.PMAX(PMAX)) u_bd (.clk(clk_bd), .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .qq_lo(qq_lo),
        .qq_hi(qq_hi), .qe_lo(qe_lo), .qe_hi(qe_hi), .bsel(bsel),
        .lane_en_i(lane_en), .bq_d(bq_d));
endmodule
`default_nettype wire
