`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// ot_hgi_sm_xload_static_cl2p (HBM-COLLQ/X, 2026-10-18): the static SM x-load with a PRE-QUANTISED block-dot format
// (x_fmt 3) for quantize-before-gather (QBG): the COLL gather lands FP8 codes + UE8M0 exponents (PRE-QUANTISED VM FORMAT
// v1) and the x-load delivers them to the block-dot ring WITHOUT re-quantising.  Successor modules (new names; every
// cl2 module stays byte-identical):
//   ot_hgi_sm_xload_cl2p_ctl / _ctlw / _ctlx   cl2 ctl/ctlw/ctlx + fmt 3; fmt 0/1/2 cycle-identical to cl2
//   ot_hgi_xp_aq_bypass13                      PRE bypass tile: same ports and 13-edge latency as the quantiser tile
//                                              ot_hbm_xp_aq_tree13; q = x[255:0], e = x[263:256] - 127
//   ot_hgi_sm_xload_cl2p_bdring                cl2 bdring + bypass word pins (pin-registered, selected after the pins)
//   ot_hgi_sm_xload_static_cl2p                wires-only cluster (bench vehicle; die: ctlx_p + 2 bypass tiles + bdring_p)
// FORMAT v1 (written by the COLL gather master): S <= 4 segments of Bs blocks (32 elements); segment s record at word
// base + s ss: words [0,Bs) codes of block r (element j at [8j+:8], = ot_hdc_actquant q / hdc_golden_v41.quant_fp8),
// words [Bs, Bs+Es) (Es = ceil(Bs/32)) exponents, byte k of word g = e(block 32g+k) + 127.  Per-p images at
// base + p x_stride.  Command (fmt 3): x_base[17:0] element address of the image (word [17:3]), x_base[27:18] = Bs
// (even, <= 128), x_base[39:28] = ss (words), x_n = K (elements, multiple of 32), x_p, x_stride as fmt 1.
// PRE timeline: start -> exponent preload, P x S x Es one-word reads (8-bank waves, same rq form as fmt 1), held in a
// 16-word exponent buffer (P S Es <= 16, else sticky x_fault); 2 idle issue edges; then fmt 1's BD issue sequence on the
// code words (word = p base + s ss + r for block b0 = s Bs + r; the pair b0, b0+1 shares one segment since Bs is even).
// Every pre read passes one address stage.  RESULT: every xw beat / x_done of fmt 3 is fmt 1's on the same vector
// exactly D = P S Es + 3 edges later (bench tb_hgi_xload_preq).  VM: each read is a full 8-bank wave as in fmt 1, so
// the calendar reserves the x-load read group on all 8 banks for NE = P S Es preload edges, then fmt 1's issue pattern
// shifted by D (no code/exponent bank conflict can arise: they never share an edge).
// MUT (bench): 7 exponent byte of the next pair (off by two blocks); 8 bypass bias 126 (must FAIL).
// =====================================================================================================================
module ot_hgi_xp_aq_bypass13 #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          fp4,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output reg           fault
);
    // 13 edges v -> vo (S0 input register ... output registers), as ot_hbm_xp_aq_tree13; data shifted with it
    reg [11:0] sv; reg [263:0] sd [0:11];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sv <= 12'd0; vo <= 1'b0; fault <= 1'b0; end
        else begin
            sv <= {sv[10:0], v}; vo <= sv[11];
            // a UE8M0 byte outside the FP8 range [-22, 120] + 127 cannot come from the quantiser (amax floor 1e-4)
            fault <= sv[11] && (sd[11][263:256] < 8'd105 || sd[11][263:256] > 8'd247 || fp4);
        end
    always @(posedge clk) begin
        sd[0] <= x[263:0];
        for (integer d = 1; d < 12; d = d + 1) sd[d] <= sd[d-1];
        q <= sd[11][255:0]; e <= $signed({2'b00, sd[11][263:256]}) - ((MUT == 8) ? 10'sd126 : 10'sd127); y <= 512'd0;
    end
endmodule

module ot_hgi_sm_xload_cl2p_ctl #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,
    parameter integer MUT    = 0,
    parameter integer NR     = 32,       // select replicas (each drives 2048 / NR data bits)
    parameter integer EGRESS_SPLIT = 0,  // XQL (H-SM 10-16): 1 = export the egress controls (eg_*) to pair-egress leaves
    // SEL_KEEP=1 (HBM-B 10-17, ctlx): the NR rotation-select replicas are (* keep *) flops, so synthesis keeps NR copies
    // (ctlw f20a: opt_merge folded them, u_ctl.s0r[26][*] drove 5,045 loads).  Same function, same edges.
    parameter integer SEL_KEEP = 0,
    parameter integer NEB = 16          // PRE: exponent words held per command (P x S x Es <= NEB)
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
    // ---- PRE (fmt 3): bypass tiles (ot_hgi_xp_aq_bypass13, same 13-edge latency as the quantisers; data from l_d_o)
    output reg                pv_lo, pv_hi,
    input  wire               po_lo, po_hi, pf_lo, pf_hi,
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
    wire c_bdf = c_fmt != 2'd0;           // 1 FP8, 2 FP4, 3 PRE (pre-quantised FP8 image)
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
    reg prm;                                // PRE mode of the running command
    wire pre_bad;
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
            if (resp_bad || bd_fault || pre_bad) x_fault <= 1'b1;
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
    // PRE: every pre-mode read (exponent preload or code wave) passes the P1 address stage (+1 edge)
    reg p1_v; reg [14:0] p1_wa; reg [15:0] p1_b0; reg [16:0] p1_meta; reg p1_pl; reg [2:0] p1_p; reg [1:0] p1_s;
    wire [14:0] p1_W = p1_pl ? p1_wa : p1_wa + p1_b0[14:0];
    wire [14:0] q_s0 = prm ? p1_W : i_s0;
    always @(posedge clk or negedge rn) if (!rn) q_v <= 8'd0; else q_v <= {8{prm ? p1_v : w_iss}};
    // lane b carries the wave's sector whose bank is b: {s0[14:3] + (b < s0[2:0]), b}  (= s0 + ((b - s0) mod 8))
    wire [11:0] s_hi = q_s0[14:3], s_hi1 = q_s0[14:3] + 12'd1;
    always @(posedge clk) for (integer b = 0; b < 8; b = b + 1)
        q_s[b] <= {1'b0, (3'(b) < q_s0[2:0]) ? s_hi1 : s_hi, 3'(b)};
    localparam integer MW = 1 + 4 + 3 + 3 + 3 + 7;
    reg [MW-1:0] md [0:RD_LAT+1];          // + 1: rr is captured raw at the pins, rotated one edge later
    wire [6:0] i_rem = (r_w <= 22'sd0) ? 7'd0 : (r_w >= 22'sd64) ? 7'd64 : r_w[6:0];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d <= RD_LAT + 1; d = d + 1) md[d] <= '0;
        else begin
            md[0] <= prm ? {p1_v, p1_meta[16:7], p1_W[2:0], p1_meta[6:0]} :
                     bdm ? {bd_iss, bd_meta[16:7], i_s0[2:0], bd_meta[6:0]} : {iss_w, ig[3:0], i_p[2:0], i_wq, i_s0[2:0], i_rem};
            for (integer d = 1; d <= RD_LAT + 1; d = d + 1) md[d] <= md[d-1];
        end
    end
    wire [MW-1:0] mr = md[RD_LAT+1];
    wire m_v = mr[MW-1];
    // PRE side pipe, aligned with md: {pl, p, s, b0} raw at [0], cooked {pl, code, eidx, r5} from [2] on
    reg pa_pl [0:1]; reg pa_cd [0:1]; reg [2:0] pa_p [0:1]; reg [1:0] pa_s [0:1]; reg [15:0] pa_b0 [0:1];
    reg pb_pl [2:RD_LAT+1]; reg pb_cd [2:RD_LAT+1]; reg [3:0] pb_ei [2:RD_LAT+1]; reg [4:0] pb_r [2:RD_LAT+1];
    reg [15:0] bmul [0:3]; reg [4:0] e_s;    // s x Bs, Es
    reg [6:0] e_se;                          // S x Es (per-p exponent words)
    wire [15:0] ck_r = pa_b0[1] - bmul[pa_s[1]];
    wire [6:0] ck_ei = 7'(pa_p[1]) * e_se + 7'(pa_s[1]) * 7'(e_s) + 7'(ck_r[15:5]);
    always @(posedge clk or negedge rn) begin
        if (!rn) begin pa_pl[0] <= 1'b0; pa_pl[1] <= 1'b0; pa_cd[0] <= 1'b0; pa_cd[1] <= 1'b0;
            for (integer d = 2; d <= RD_LAT + 1; d = d + 1) begin pb_pl[d] <= 1'b0; pb_cd[d] <= 1'b0; end end
        else begin
            pa_pl[0] <= prm && p1_v && p1_pl; pa_cd[0] <= prm && p1_v && !p1_pl;
            pa_pl[1] <= pa_pl[0]; pa_cd[1] <= pa_cd[0];
            pb_pl[2] <= pa_pl[1]; pb_cd[2] <= pa_cd[1];
            for (integer d = 3; d <= RD_LAT + 1; d = d + 1) begin pb_pl[d] <= pb_pl[d-1]; pb_cd[d] <= pb_cd[d-1]; end
        end
    end
    always @(posedge clk) begin
        pa_p[0] <= p1_p; pa_s[0] <= p1_s; pa_b0[0] <= p1_b0; pa_p[1] <= pa_p[0]; pa_s[1] <= pa_s[0]; pa_b0[1] <= pa_b0[0];
        pb_ei[2] <= pa_pl[1] ? pa_b0[1][3:0] : ck_ei[3:0]; pb_r[2] <= ck_r[4:0] + ((MUT == 7) ? 5'd2 : 5'd0);
        for (integer d = 3; d <= RD_LAT + 1; d = d + 1) begin pb_ei[d] <= pb_ei[d-1]; pb_r[d] <= pb_r[d-1]; end
    end
    wire m_pl = pb_pl[RD_LAT+1], m_cd = pb_cd[RD_LAT+1];
    reg [255:0] ebuf [0:NEB-1];
    reg l0_pl, l0_cd, l_pl; reg [3:0] l0_ei; reg [4:0] l0_r; reg [255:0] l0_ew;
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
            always @(posedge clk or negedge rn) if (!rn) q <= 3'd0; else q <= md[RD_LAT][9:7];
            assign s0r[k] = q;
        end
    end else begin : g_s0
        reg [2:0] s0q [0:NR-1];
        always @(posedge clk or negedge rn)
            if (!rn) for (integer k = 0; k < NR; k = k + 1) s0q[k] <= 3'd0;
            else for (integer k = 0; k < NR; k = k + 1) s0q[k] <= md[RD_LAT][9:7];
        for (genvar k = 0; k < NR; k = k + 1) begin : g_a
            assign s0r[k] = s0q[k];
        end
    end endgenerate
    always @(posedge clk or negedge rn) if (!rn) begin l0_v <= 1'b0; l_v <= 1'b0; l0_pl <= 1'b0; l0_cd <= 1'b0; l_pl <= 1'b0; end
        else begin l0_v <= m_v; l_v <= l0_v; l0_pl <= m_v && m_pl; l0_cd <= m_v && m_cd; l_pl <= l0_pl; end
    always @(posedge clk) begin
        {l0_g, l0_p, l0_wq} <= mr[MW-2 -: 10]; l0_rem <= mr[6:0];
        for (integer k = 0; k < NR; k = k + 1)
            l0_d[k*RB +: RB] <= rr_c[(3'(s0r[k] + 3'((k*RB) / 256) + ((MUT == 1) ? 3'd1 : 3'd0)))*257 + (k*RB) % 256 +: RB];
        {l_g, l_p, l_wq} <= {l0_g, l0_p, l0_wq}; l_rem <= l0_rem;
        // PRE: exponent word selected at L0, bytes at L1; code waves land as {e byte, codes} per block, rest 0
        l0_ei <= pb_ei[RD_LAT+1]; l0_r <= pb_r[RD_LAT+1]; l0_ew <= ebuf[pb_ei[RD_LAT+1]];
        if (l0_pl) ebuf[l0_ei] <= l0_d[255:0];
        if (l0_cd) l_d <= {760'd0, l0_ew[8*(l0_r+5'd1) +: 8], l0_d[511:256], 760'd0, l0_ew[8*l0_r +: 8], l0_d[255:0]};
        else l_d <= l0_d;
    end
    assign l_d_o = l_d;
    // quantiser valids registered with L1 (= l_v && bdm && l_wq[2] / [1] of cl)
    reg qv0_lo, qv0_hi;
    always @(posedge clk or negedge rn)
        if (!rn) begin qv0_lo <= 1'b0; qv0_hi <= 1'b0; qv_lo <= 1'b0; qv_hi <= 1'b0; end
        else begin qv0_lo <= m_v && bdm && !prm && mr[12]; qv0_hi <= m_v && bdm && !prm && mr[11]; qv_lo <= qv0_lo; qv_hi <= qv0_hi; end
    reg pv0_lo, pv0_hi;
    always @(posedge clk or negedge rn)
        if (!rn) begin pv0_lo <= 1'b0; pv0_hi <= 1'b0; pv_lo <= 1'b0; pv_hi <= 1'b0; end
        else begin pv0_lo <= m_v && m_cd && mr[12]; pv0_hi <= m_v && m_cd && mr[11]; pv_lo <= pv0_lo; pv_hi <= pv0_hi; end
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
    wire pl_go;
    always @(posedge clk or negedge rn) begin
        if (!rn) bi_on <= 1'b0;
        else begin
            if (start_bd && !c_pre) bi_on <= 1'b1;
            if (pl_go) bi_on <= 1'b1;
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
    // ================================================================================================================
    // PRE (fmt 3): exponent preload (P x S x Es one-word waves, order k = (p S + s) Es + g) then the BD issue sequence of
    // fmt 1 on the code words; each pre read passes the P1 address stage.  Command: x_base[17:0] element address of the
    // image (word = [17:3]), x_base[27:18] = Bs (blocks per segment, even, <= 128), x_base[39:28] = segment stride in
    // words; x_stride = per-p image stride (elements).  S = ceil(K / 32 / Bs) <= 4, P x S x Es <= NEB, else sticky fault.
    wire c_pre = c_fmt == 2'd3;
    reg [14:0] bw0, stw, ssw; reg [9:0] bs; reg [2:0] s_n; reg [3:0] p_n;
    reg [15:0] bnd1, bnd2, bnd3; reg [14:0] off1, off2, off3;
    reg pl_on; reg [3:0] pl_p; reg [1:0] pl_s; reg [4:0] pl_g; reg [3:0] pl_k; reg [14:0] pl_pa, pl_sa;
    reg [1:0] pl_w; reg [14:0] pre_pw; reg pre_chk;
    wire pl_last = pl_g == e_s - 5'd1 && 3'(pl_s) == s_n - 3'd1 && pl_p == p_n - 4'd1;
    assign pl_go = pl_w == 2'd2;
    wire [1:0] cs_s = (c_b0 >= bnd3) ? 2'd3 : (c_b0 >= bnd2) ? 2'd2 : (c_b0 >= bnd1) ? 2'd1 : 2'd0;
    wire [14:0] cs_off = (cs_s == 2'd3) ? off3 : (cs_s == 2'd2) ? off2 : (cs_s == 2'd1) ? off1 : 15'd0;
    wire [15:0] c_nbk = c_n[20:5]; wire [9:0] c_bs = c_base[27:18];
    wire [2:0] c_sn = (c_nbk <= 16'(c_bs)) ? 3'd1 : (c_nbk <= 16'(c_bs) * 16'd2) ? 3'd2 : (c_nbk <= 16'(c_bs) * 16'd3) ? 3'd3 :
                      (c_nbk <= 16'(c_bs) * 16'd4) ? 3'd4 : 3'd7;
    wire [4:0] c_es = 5'((c_bs + 10'd31) >> 5);
    reg pre_bad_q; assign pre_bad = pre_bad_q;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin prm <= 1'b0; pl_on <= 1'b0; pl_w <= 2'd0; pre_bad_q <= 1'b0; pre_chk <= 1'b0; end
        else begin
            pre_bad_q <= 1'b0;
            if (start) prm <= start_bd && c_pre;
            pre_chk <= start_bd && c_pre;
            if (pre_chk && (bs == 10'd0 || bs[0] || bs > 10'd128 || s_n > 3'd4 || 8'(p_n) * 8'(e_se) > 8'(NEB))) pre_bad_q <= 1'b1;
            if (start_bd && c_pre) pl_on <= 1'b1;
            else if (pl_on && pl_last) pl_on <= 1'b0;
            pl_w <= (pl_on && pl_last) ? 2'd1 : (pl_w == 2'd1) ? 2'd2 : 2'd0;
        end
    end
    always @(posedge clk) begin
        if (start_bd && c_pre) begin
            bw0 <= c_base[17:3]; stw <= c_stride[17:3]; ssw <= {3'd0, c_base[39:28]}; bs <= c_bs; s_n <= c_sn; p_n <= c_p;
            e_s <= c_es; e_se <= 7'(c_sn) * 7'(c_es);
            bnd1 <= 16'(c_bs); bnd2 <= 16'(c_bs) * 16'd2; bnd3 <= 16'(c_bs) * 16'd3;
            bmul[0] <= 16'd0; bmul[1] <= 16'(c_bs); bmul[2] <= 16'(c_bs) * 16'd2; bmul[3] <= 16'(c_bs) * 16'd3;
            off1 <= {3'd0, c_base[39:28]} - 15'(c_bs); off2 <= 15'(({3'd0, c_base[39:28]} - 15'(c_bs)) * 15'd2);
            off3 <= 15'(({3'd0, c_base[39:28]} - 15'(c_bs)) * 15'd3);
            pl_p <= 4'd0; pl_s <= 2'd0; pl_g <= 5'd0; pl_k <= 4'd0; pl_pa <= c_base[17:3]; pl_sa <= c_base[17:3];
            pre_pw <= c_base[17:3];
        end else begin
            if (pl_on) begin
                pl_k <= pl_k + 4'd1;
                if (pl_g == e_s - 5'd1) begin
                    pl_g <= 5'd0;
                    if (3'(pl_s) == s_n - 3'd1) begin pl_s <= 2'd0; pl_p <= pl_p + 4'd1; pl_pa <= pl_pa + stw; pl_sa <= pl_pa + stw; end
                    else begin pl_s <= pl_s + 2'd1; pl_sa <= pl_sa + ssw; end
                end else pl_g <= pl_g + 5'd1;
            end
            if (bi_on) begin
                if (bw_wrap) pre_pw <= bw0;
                else if (bj_wrap) pre_pw <= pre_pw + stw;
            end
        end
    end
    // P1 address stage (pre mode): preload word = s-record base + Bs + g; code word = p base + b0 + s (ss - Bs)
    always @(posedge clk or negedge rn) if (!rn) p1_v <= 1'b0; else p1_v <= prm && (pl_on || bd_iss);
    always @(posedge clk) begin
        p1_pl <= pl_on;
        p1_wa <= pl_on ? pl_sa + 15'(bs) + 15'(pl_g) : pre_pw + cs_off;
        p1_b0 <= pl_on ? {12'd0, pl_k} : c_b0;
        p1_meta <= pl_on ? 17'd0 : bd_meta; p1_p <= pl_on ? 3'd0 : b_p[2:0]; p1_s <= pl_on ? 2'd0 : cs_s;
    end
    assign bd_s0 = c_word[17:3];
    assign bd_meta = {bk[0], b_p[2:0], b_j, c_b0 < nbk, (c_b0 + 16'd1) < nbk, 1'b0, 7'd0};
    reg [9:0] qt [0:QL-1];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d < QL; d = d + 1) qt[d] <= '0;
        else begin
            qt[0] <= {l_v && bdm && !l_pl, l_g[3], l_g[2:0], l_p, l_wq[2:1]};
            for (integer d = 1; d < QL; d = d + 1) qt[d] <= qt[d-1];
        end
    end
    wire [9:0] qtl = qt[QL-1];
    // quantiser flags registered at the pins; the fault check compares them one edge later with the delayed tag
    reg qo_lo_c, qo_hi_c, qf_lo_c, qf_hi_c; reg [9:0] qtl_d;
    always @(posedge clk or negedge rn)
        if (!rn) begin qo_lo_c <= 1'b0; qo_hi_c <= 1'b0; qf_lo_c <= 1'b0; qf_hi_c <= 1'b0; qtl_d <= '0; end
        else begin qo_lo_c <= qo_lo || po_lo; qo_hi_c <= qo_hi || po_hi; qf_lo_c <= qf_lo || pf_lo; qf_hi_c <= qf_hi || pf_hi; qtl_d <= qtl; end
    assign bd_fault = (qo_lo_c && qf_lo_c) || (qo_hi_c && qf_hi_c) || (qtl_d[9] && (qtl_d[1] != qo_lo_c || qtl_d[0] != qo_hi_c));
    reg wv_b;
    // cl2d: the ring write controls leave ONE edge early (lookahead on the fixed tag delay line, qt[QL-2] = next qtl) so
    // the bdring leaf can capture them in pin registers on the same edge as its quantiser words wr_lo/wr_hi (native
    // capture: r_wsel/zlo/zhi no longer gate the 32 x 266 ring storage straight from the pins).  Ring write edge unchanged.
    wire [9:0] qtn = (MUT == 5) ? qtl : qt[QL-2];   // MUT 5: no lookahead (must FAIL the lock bench)
    always @(posedge clk or negedge rn)
        if (!rn) begin wv_b <= 1'b0; r_wsel <= 16'd0; end
        else begin
            wv_b <= qtl[9];
            for (integer s = 0; s < 16; s = s + 1)
                r_wsel[s] <= qtn[9] && {qtn[5], qtn[4:2] ^ ((MUT == 3) ? 3'd1 : 3'd0)} == 4'(s);
        end
    always @(posedge clk) begin zlo <= qtn[1]; zhi <= qtn[0]; end
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
    wire pair_rdy = (ek < wk) || ({1'b0, wc} >= need_q);
    wire bd_em = be_on && (ea || pair_rdy);
    wire bd_tail = bd_em && ea && eb2_last;
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
                if (eb2_last) begin eb2_n = 7'd0; ek_n = ek + 10'd1; end else eb2_n = eb2 + 7'd1;
            end
        end
    end
    wire [3:0] la_nx = start_bd ? la_c : la;
    wire [7:0] pla_nx = start_bd ? pla_c : pla;
    wire [6:0] nb_nx = start ? nb_c : nb;
    always @(posedge clk) begin
        ea <= ea_n; eb2 <= eb2_n; ek <= ek_n;
        need_q <= need_of(eb2_n, la_nx, pla_nx); eb2_last <= (eb2_n == nb_nx - 7'd1);
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
    always @(posedge clk_eg) begin
        if (bc_v) begin xw_addr <= bc_addr; xw_grp <= bc_b; end
        else begin xw_addr <= e6[13:7]; xw_grp <= e6[6:0]; end
        for (integer k = 0; k < NR; k = k + 1) xw_data[k*RB +: RB] <= bqvr[k] ? bq_c[k*RB +: RB] : xbeat[k*RB +: RB];
    end
endmodule

module ot_hgi_sm_xload_cl2p_ctlw #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,
    parameter integer MUT    = 0,
    parameter integer NR     = 32,
    parameter integer LEAD   = 8,
    parameter integer EGRESS_SPLIT = 0,  // XQL: export the egress controls (eg_*), see ot_hgi_sm_xload_static_xql
    parameter integer SEL_KEEP = 0       // kept rotation-select replicas (ot_hgi_sm_xload_cl2_ctl SEL_KEEP)
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
    output wire               pv_lo, pv_hi,
    input  wire               po_lo, po_hi, pf_lo, pf_hi,
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
    wire x_v, x_busy, x_fault; wire [107:0] xc;
    // issuer = ot_static_cmd_target_core + its calendar SRAM on the hard entry clk_cal (the multiple_cts_roots flow lets a
    // CTS root reach standard-cell clock pins only; same pattern as ot_hgi_dma_back_static_vp4_banks_cp's clk_tab)
    wire t_rce; wire [6:0] t_raddr, t_waddr; wire [0:0] t_wce; wire [255:0] t_wdata, t_rd;
    ot_static_cmd_target_core #(.TARGET(8'hff), .MODE(1), .CW(108), .RELF(0), .NA(1), .NF(1), .LEAD(LEAD),
                                .MUT((MUT == 6) ? 1 : 0), .TGT_PIN(1)) u_iss (
        .clk(clk), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .tgt_active(x_busy), .tgt_fault(x_fault),
        .a_we(), .a_addr(), .a_data(), .b_we(), .b_addr(), .b_data(), .run_v(), .run_base(), .run_count(),
        .cmd_v(x_v), .cmd(xc), .cycle(), .configured(configured), .fault(fault), .active(active),
        .tab_r_ce(t_rce), .tab_r_addr(t_raddr), .tab_rd_word(t_rd), .tab_w_ce(t_wce), .tab_w_addr(t_waddr), .tab_w_data(t_wdata));
    ot_sram_1r1w_128x256_m1_r2c2 u_tab (.clk(clk_cal), .r_ce_in(t_rce), .r_addr_in(t_raddr), .rd_out(t_rd),
        .w_ce_in(t_wce[0]), .w_addr_in(t_waddr), .wd_in(t_wdata), .w_mask_in({256{1'b1}}),
        .rr_en(2'b0), .rr_addr(12'b0), .cr_en(2'b0), .cr_sel(16'b0));
    // cmd = {x_xb7, x_fmt2, x_space2, x_stride32, x_p4, x_n21, x_base40} (die contract v16 cp1_194..201)
    ot_hgi_sm_xload_cl2p_ctl #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT((MUT == 6) ? 0 : MUT), .NR(NR), .EGRESS_SPLIT(EGRESS_SPLIT), .SEL_KEEP(SEL_KEEP)) u_ctl (
        .clk(clk), .clk_eg(clk_eg), .rst_n(rst_n), .x_v(x_v), .x_base(xc[39:0]), .x_n(xc[60:40]), .x_p(xc[64:61]),
        .x_stride(xc[96:65]), .x_space(xc[98:97]), .x_fmt(xc[100:99]), .x_xb(xc[107:101]),
        .x_busy(x_busy), .x_done(x_done), .x_fault(x_fault), .xw_en(xw_en), .xw_last(xw_last), .xw_addr(xw_addr),
        .xw_grp(xw_grp), .xw_data(xw_data), .rq(rq), .rr(rr), .rn_o(rn_o), .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi),
        .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(rwq), .l_d_o(l_d_o), .qv_lo(qv_lo), .qv_hi(qv_hi),
        .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi), .pv_lo(pv_lo), .pv_hi(pv_hi), .po_lo(po_lo), .po_hi(po_hi), .pf_lo(pf_lo), .pf_hi(pf_hi), .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel),
        .lane_en(lane_en), .bq_d(bq_d), .eg_ed5(eg_ed5), .eg_ede(eg_ede), .eg_bqv(eg_bqv), .eg_bqlast(eg_bqlast),
        .eg_bqaddr(eg_bqaddr), .eg_bqb(eg_bqb));
endmodule

module ot_hgi_sm_xload_cl2p_ctlx #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,
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
    output wire               pv_lo, pv_hi,
    input  wire               po_lo, po_hi, pf_lo, pf_hi,
    output wire [15:0]        r_wsel,
    output wire               zlo, zhi,
    output wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,
    output wire [PMAX*8-1:0]  lane_en,
    output wire [7:0]         eg_ed5,
    output wire [16:0]        eg_ede,
    output wire               eg_bqv, eg_bqlast,
    output wire [6:0]         eg_bqaddr, eg_bqb
);
    ot_hgi_sm_xload_cl2p_ctlw #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT(MUT), .NR(NR), .LEAD(LEAD), .EGRESS_SPLIT(1), .SEL_KEEP(1)) u_w (
        .clk(clk), .clk_eg(clk), .clk_cal(clk_cal), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target),
        .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit),
        .desc_loops(desc_loops), .launch_v(launch_v), .configured(configured), .fault(fault), .active(active),
        .x_done(), .xw_en(), .xw_last(), .xw_addr(), .xw_grp(), .xw_data(), .rq(rq), .rr(rr), .rn_o(rn_o),
        .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi), .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(1024'd0),
        .l_d_o(l_d_o), .qv_lo(qv_lo), .qv_hi(qv_hi), .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi), .pv_lo(pv_lo), .pv_hi(pv_hi), .po_lo(po_lo), .po_hi(po_hi), .pf_lo(pf_lo), .pf_hi(pf_hi),
        .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel), .lane_en(lane_en), .bq_d(2048'd0),
        .eg_ed5(eg_ed5), .eg_ede(eg_ede), .eg_bqv(eg_bqv), .eg_bqlast(eg_bqlast), .eg_bqaddr(eg_bqaddr), .eg_bqb(eg_bqb));
endmodule

module ot_hgi_sm_xload_cl2p_bdring #(
    parameter integer PMAX = 8,
    parameter integer NR   = 64
) (
    input  wire               clk,
    input  wire [15:0]        r_wsel,
    input  wire               zlo, zhi,
    input  wire [255:0]       qq_lo, qq_hi,
    input  wire signed [9:0]  qe_lo, qe_hi,
    // PRE: bypass tile words + their valids (same edge as the quantiser words); pin-registered, selected after the pins
    input  wire [255:0]       pq_lo, pq_hi,
    input  wire signed [9:0]  pe_lo, pe_hi,
    input  wire               pvo_lo, pvo_hi,
    input  wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,  // one-hot {parity, beat} (registered in ctl)
    input  wire [PMAX*8-1:0]  lane_en_i,
    output wire [2047:0]      bq_d
);
    // cl2e: the beat register holds the INVERTED beat so the ASAP7 QN-only flop (DFFHQN) drives bq_d with no output
    // inverter. cl2d placed 25 of the 2048 output-polarity INVs ~300 um from their pin flops (native launch 489.6 ps
    // on bq_d[420]); with the inversion folded into the D-side AND-OR (AOI) the pin is driven by the flop itself.
    // Same edge, same values at the pin.
    reg [2047:0] bq_n;
    assign bq_d = ~bq_n;
    localparam integer XC = 3152;
    localparam integer NBQ = (PMAX * XC + 2047) / 2048;
    localparam integer RB = 2048 / NR;
    reg [PMAX*8-1:0] lane_en;              // local copy (command constant; refreshed every edge)
    always @(posedge clk) lane_en <= lane_en_i;
    reg [265:0] wr_lo, wr_hi;              // quantiser words registered at the pins (cl's wd edge)
    reg [265:0] wp_lo, wp_hi; reg ps_lo, ps_hi;  // PRE bypass words / valids at the pins
    // cl2d: ring controls registered at the pins on the SAME edge as wr_lo/wr_hi (ctl sends them one edge early);
    // one enable copy per parity (532 loads each), no pin-to-storage gating left.
    reg [15:0] wsel_q [0:1];
    reg        zlo_q, zhi_q;
    always @(posedge clk) begin
        wr_lo <= {qe_lo, qq_lo}; wr_hi <= {qe_hi, qq_hi};
        wp_lo <= {pe_lo, pq_lo}; wp_hi <= {pe_hi, pq_hi}; ps_lo <= pvo_lo; ps_hi <= pvo_hi;
        wsel_q[0] <= r_wsel; wsel_q[1] <= r_wsel; zlo_q <= zlo; zhi_q <= zhi;
    end
    wire [265:0] wd_lo = zlo_q ? (ps_lo ? wp_lo : wr_lo) : 266'd0, wd_hi = zhi_q ? (ps_hi ? wp_hi : wr_hi) : 266'd0;
    wire [265:0] ring [0:1][0:15];
    genvar gpa, gsl;
    generate for (gpa = 0; gpa < 2; gpa = gpa + 1) begin : g_rp
        for (gsl = 0; gsl < 16; gsl = gsl + 1) begin : g_rs
            reg [265:0] w;
            always @(posedge clk) if (wsel_q[gpa][gsl]) w <= (gpa == 0) ? wd_lo : wd_hi;
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
        bq_n[k*RB +: RB] <= ~acc;
    end
endmodule

module ot_hgi_sm_xload_static_cl2p #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,
    parameter integer MUT    = 0
) (
    input  wire               clk,
    input  wire               clk_eg,    // cl2d: ctl egress root (rw / BD-beat capture, beat select, xw pins), related phase 0
    input  wire [3:0]         clk_bf,    // cl2d: one die clock entry per BF quarter leaf (was one scalar collapsing 4 roots)
    input  wire               clk_qlo,
    input  wire               clk_qhi,
    input  wire               clk_plo,   // PRE bypass tiles
    input  wire               clk_phi,
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
    wire pv_lo, pv_hi, po_lo, po_hi, pf_lo, pf_hi; wire [255:0] pq_lo, pq_hi; wire signed [9:0] pe_lo, pe_hi;
    ot_hgi_sm_xload_cl2p_ctl #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT(MUT)) u_ctl (
        .clk(clk), .clk_eg(clk_eg), .rst_n(rst_n), .x_v(x_v), .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space),
        .x_fmt(x_fmt), .x_xb(x_xb), .x_busy(x_busy), .x_done(x_done), .x_fault(x_fault), .xw_en(xw_en), .xw_last(xw_last),
        .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .rq(rq), .rr(rr), .rn_o(rn),
        .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi), .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(rwq),
        .l_d_o(l_d), .qv_lo(qv_lo), .qv_hi(qv_hi), .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi), .pv_lo(pv_lo), .pv_hi(pv_hi), .po_lo(po_lo), .po_hi(po_hi), .pf_lo(pf_lo), .pf_hi(pf_hi),
        .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel), .lane_en(lane_en), .bq_d(bq_d));
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
        ot_hgi_sm_xload_cl2_bfq u_bfq (.clk(clk_bf[gq]), .rst_n(rn), .c_d(c_d), .wce(c_wce[gq]), .mhi(c_mhi), .mlo(c_mlo),
            .wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(rwq[256*gq +: 256]));
    end endgenerate
    ot_hbm_xp_aq_tree13 u_aq_lo (.clk(clk_qlo), .rst_n(rn), .v(qv_lo), .fp4(1'b0), .x(l_d[1023:0]), .vo(qo_lo), .q(qq_lo),
                             .e(qe_lo), .y(), .fault(qf_lo));
    ot_hbm_xp_aq_tree13 u_aq_hi (.clk(clk_qhi), .rst_n(rn), .v(qv_hi), .fp4(1'b0), .x(l_d[2047:1024]), .vo(qo_hi), .q(qq_hi),
                             .e(qe_hi), .y(), .fault(qf_hi));
    ot_hgi_xp_aq_bypass13 #(.MUT(MUT)) u_bp_lo (.clk(clk_plo), .rst_n(rn), .v(pv_lo), .fp4(1'b0), .x(l_d[1023:0]), .vo(po_lo), .q(pq_lo),
                             .e(pe_lo), .y(), .fault(pf_lo));
    ot_hgi_xp_aq_bypass13 #(.MUT(MUT)) u_bp_hi (.clk(clk_phi), .rst_n(rn), .v(pv_hi), .fp4(1'b0), .x(l_d[2047:1024]), .vo(po_hi), .q(pq_hi),
                             .e(pe_hi), .y(), .fault(pf_hi));
    ot_hgi_sm_xload_cl2p_bdring #(.PMAX(PMAX)) u_bd (.clk(clk_bd), .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .qq_lo(qq_lo),
        .qq_hi(qq_hi), .qe_lo(qe_lo), .qe_hi(qe_hi), .pq_lo(pq_lo), .pq_hi(pq_hi), .pe_lo(pe_lo), .pe_hi(pe_hi),
        .pvo_lo(po_lo), .pvo_hi(po_hi), .bsel(bsel),
        .lane_en_i(lane_en), .bq_d(bq_d));
endmodule
`default_nettype wire
