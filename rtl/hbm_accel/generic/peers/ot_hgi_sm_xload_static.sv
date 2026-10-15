`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// STATIC SM x-load (H-ELEM-A 2026-10-15; owner rule 2026-10-14 23:16: HBM on-chip paths run on compiler-assigned fixed
// cycles, NO credits / ready / backpressure).  Static successor of ot_hgi_sm_xload's BF16 path (fmt 0 / 3): same x-store
// fragment layout and the same x-store write set (address {g mod 16, t} + x_xb, beat b, 2,048-b data), but every read,
// landing, macro write and beat leaves on a cycle fixed by the command alone:
//   * VM reads use the quadrant VM slice's static wide READ GROUP (8 lanes = 8 banks, rq {v, sector16} / rr {v, data256}):
//     one wave = 8 consecutive sectors (lanes j = 8 wq .. 8 wq + 7 of slot p, group g) = one sector per bank, issued in
//     ONE edge; the bank of sector S is S[2:0], so lane b carries the wave's sector with S[2:0] == b (no conflicts).
//   * Group g owns an issue window of E = 8 nb edges (nb = ceil(P x 3,152 / 2,048) beats a fragment address) starting at
//     I0 + g E; its 8 P waves issue on the window's first 8 P edges (8 P < E for every P).  The VM calendar (compiler)
//     reserves read-group slots on exactly those edges.  Responses are REQUIRED at request + RD_LAT (rr valid checked:
//     a missing, early or unexpected response is a fault, never a wait).
//   * Emission of group g starts EM_OFF = 8 P + RD_LAT + LAND edges after its window start and takes exactly E edges
//     (t < 8, b < nb, one beat an edge), so emission windows abut and landing of g + 1 overlaps emission of g in the other
//     x-store words ({g mod 16, p}).  xw beats leave on fixed cycles; the x-write relay to the SMs is fixed latency.
//   * A command while busy, a refused command (not VM, misaligned, P out of range, block-dot fmt 1 / 2 not in this
//     successor yet) or a response timing violation raises x_fault; it never reschedules.
// Storage: 32 ot_sram_1r1w_128x256_m1 macros m[t][q] (t < 8, q < 4 lane quarter), word {g mod 16, p}: lanes 16 q ..
// 16 q + 15 of slot p, t-value t, BF16.  A wave writes the 8 macros m[t][wq >> 1] (half wq & 1: 8 lanes, masked).
// Read path (emission): per-macro pin flops -> macro -> gated capture -> registered OR-4 / OR-2 -> beat select -> pins.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_xload_static #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,       // VM read group: rq output edge -> rr valid edge (bank n+6 + slice/station edges)
    parameter integer MUT    = 0        // 1: lane rotation off by one (must fail); 2: emission one edge early (must fail)
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x_v,       // compiler-issued command edge (no ready)
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    input  wire [6:0]         x_xb,
    output reg                x_busy,    // diagnostic only (the compiler knows the command length)
    output reg                x_done,
    output reg                x_fault,
    output reg                xw_en,
    output reg                xw_last,
    output reg  [6:0]         xw_addr,
    output reg  [6:0]         xw_grp,
    output reg  [2047:0]      xw_data,
    output wire [8*17-1:0]    rq,        // VM read group lanes: {v, sector16}
    input  wire [8*257-1:0]   rr         // VM read group lanes: {v, data256}, at request + RD_LAT
);
    localparam integer XC = 3152, XOFF = 2128;
    localparam integer NBMAX = (PMAX * XC + 2047) / 2048;
    localparam integer LAND = 3;           // L capture, C convert, W macro pins (write at the next edge)
    localparam integer RDP = 6;            // emission meta: ed[d] at E0 + 1 + d; ed[4] with rw, ed[5] with the beat
    // ---- local reset relay: the port drives 3 flops only
    reg rs1, rs2, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rs1, rs2, rn} <= 3'b000; else {rs1, rs2, rn} <= {1'b1, rs1, rs2};
    // ---- helpers
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) bf16 = x[31:16] | 16'h0040;
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; bf16 = r[31:16]; end
        end
    endfunction
    function automatic integer bslot(input integer bb);       // the slot a beat overlaps, -1 none
        integer pp2; bslot = -1;
        for (pp2 = 0; pp2 < PMAX; pp2 = pp2 + 1)
            if (pp2 * XC + XOFF < bb * 2048 + 2048 && pp2 * XC + XOFF + 1024 > bb * 2048) bslot = pp2;
    endfunction
    // ---- command pin flops
    reg cmd_v; reg [39:0] c_base; reg [20:0] c_n; reg [3:0] c_p; reg [31:0] c_stride; reg [1:0] c_space, c_fmt; reg [6:0] c_xb;
    always @(posedge clk) begin
        c_base <= x_base; c_n <= x_n; c_p <= x_p; c_stride <= x_stride; c_space <= x_space; c_fmt <= x_fmt; c_xb <= x_xb;
    end
    wire c_bad = c_fmt == 2'd1 || c_fmt == 2'd2 || c_space != 2'd1 || |c_base[2:0] || |c_stride[2:0] ||
                 c_p > PMAX || c_p == 4'd0 || c_n == 21'd0;
    // ---- command state (data)
    reg [17:0] base, st; reg [3:0] pp; reg [20:0] kk; reg [7:0] gn; reg [6:0] nb; reg [10:0] ew; reg [6:0] xb;
    reg [10:0] em_off;
    // ---- issue side: group ig, edge iw of its window; emission side: eg, et, eb
    reg iss_on; reg [7:0] ig; reg [10:0] iw;
    reg [10:0] tc; reg em_wait;            // edges since start until emission begins
    reg em_on; reg [7:0] eg; reg [2:0] et; reg [6:0] eb;
    wire start = cmd_v && !c_bad && !x_busy;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin cmd_v <= 1'b0; x_busy <= 1'b0; x_fault <= 1'b0; iss_on <= 1'b0; em_wait <= 1'b0; em_on <= 1'b0; end
        else begin
            cmd_v <= x_v;
            if (cmd_v && (c_bad || x_busy)) x_fault <= 1'b1;
            if (start) begin x_busy <= 1'b1; iss_on <= 1'b1; em_wait <= 1'b1; end
            if (iss_on && iw == ew - 11'd1 && ig == gn - 8'd1) iss_on <= 1'b0;
            if (em_wait && tc == em_off) begin em_wait <= 1'b0; em_on <= 1'b1; end
            if (em_on && et == 3'd7 && eb == nb - 7'd1 && eg == gn - 8'd1) em_on <= 1'b0;
            if (x_done) x_busy <= 1'b0;
            if (resp_bad) x_fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        if (start) begin
            base <= c_base[17:0]; st <= c_stride[17:0]; pp <= c_p; kk <= c_n; xb <= c_xb;
            gn <= 8'(((c_n - 21'd1) >> 9) + 21'd1);
            nb <= 7'((({12'd0, c_p} * 16'd3152) + 16'd2047) >> 11);
            ew <= 11'(((({12'd0, c_p} * 16'd3152) + 16'd2047) >> 11) * 8);
            em_off <= 11'({c_p, 3'd0} + RD_LAT + LAND + 1 - ((MUT == 2) ? 3 : 0));
            ig <= 8'd0; iw <= 11'd0; tc <= 11'd0; eg <= 8'd0; et <= 3'd0; eb <= 7'd0;
        end else begin
            if (iss_on) begin
                if (iw == ew - 11'd1) begin iw <= 11'd0; ig <= ig + 8'd1; end else iw <= iw + 11'd1;
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
    // ---- issue: wave iw (< 8 P) of group ig: slot p = iw >> 3, wq = iw & 7
    wire iss_w = iss_on && iw < {4'd0, pp, 3'd0};
    wire [3:0] i_p = iw[6:3];
    wire [2:0] i_wq = iw[2:0];
    wire [17:0] i_word = base + 18'(i_p) * st + {ig, 9'd0} + {9'd0, i_wq, 6'd0};   // lane 0 of the wave (word)
    wire [14:0] i_s0 = i_word[17:3];
    reg [7:0] q_v; reg [15:0] q_s [0:7];
    genvar gl;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_rq
        assign rq[gl*17 +: 17] = {q_v[gl], q_s[gl]};
    end endgenerate
    always @(posedge clk or negedge rn) if (!rn) q_v <= 8'd0; else q_v <= {8{iss_w}};
    always @(posedge clk) for (integer b = 0; b < 8; b = b + 1)
        // lane b carries the wave's sector whose bank (S[2:0]) is b: l = (b - s0) mod 8
        q_s[b] <= {1'b0, i_s0 + 15'(3'(b - i_s0[2:0]))};
    // wave metadata on a fixed delay line (rq output edge -> rr valid edge): {v, g 4, p 3, wq 3, s0 3, rem 7}
    localparam integer MW = 1 + 4 + 3 + 3 + 3 + 7;
    reg [MW-1:0] md [0:RD_LAT];
    wire [20:0] i_rem_full = (kk > ({ig, 9'd0} + {9'd0, i_wq, 6'd0})) ? kk - ({ig, 9'd0} + {9'd0, i_wq, 6'd0}) : 21'd0;
    wire [6:0] i_rem = (i_rem_full > 21'd64) ? 7'd64 : i_rem_full[6:0];
    always @(posedge clk or negedge rn) begin
        if (!rn) for (integer d = 0; d <= RD_LAT; d = d + 1) md[d] <= '0;
        else begin
            md[0] <= {iss_w, ig[3:0], i_p[2:0], i_wq, i_s0[2:0], i_rem};
            for (integer d = 1; d <= RD_LAT; d = d + 1) md[d] <= md[d-1];
        end
    end
    // md[RD_LAT] is valid on the edge rr must carry the wave (request on rq at md[0]'s edge + RD_LAT)
    wire [MW-1:0] mr = md[RD_LAT];
    wire m_v = mr[MW-1];
    reg [7:0] rr_v_seen;
    always @* for (integer b = 0; b < 8; b = b + 1) rr_v_seen[b] = rr[b*257 + 256];
    wire resp_bad = (m_v && rr_v_seen != 8'hFF) || (!m_v && rr_v_seen != 8'h00);
    // ---- L: capture + rotate (x lane l <- VM lane (s0 + l) mod 8)
    reg l_v; reg [3:0] l_g; reg [2:0] l_p, l_wq; reg [6:0] l_rem; reg [8*256-1:0] l_d;
    always @(posedge clk or negedge rn) if (!rn) l_v <= 1'b0; else l_v <= m_v;
    always @(posedge clk) begin
        {l_g, l_p, l_wq} <= mr[MW-2 -: 10]; l_rem <= mr[6:0];
        for (integer l = 0; l < 8; l = l + 1)
            l_d[l*256 +: 256] <= rr[(3'(mr[9:7] + 3'(l) + ((MUT == 1) ? 3'd1 : 3'd0)))*257 +: 256];
    end
    // ---- C: BF16 (RNE) of every element inside K, 0 past it; layout c_d[t][l] (16 b)
    reg c_v; reg [3:0] c_g; reg [2:0] c_pp, c_wq; reg [8*8*16-1:0] c_d;
    always @(posedge clk or negedge rn) if (!rn) c_v <= 1'b0; else c_v <= l_v;
    always @(posedge clk) begin
        c_g <= l_g; c_pp <= l_p; c_wq <= l_wq;
        for (integer l = 0; l < 8; l = l + 1) for (integer tv = 0; tv < 8; tv = tv + 1)
            c_d[(tv*8 + l)*16 +: 16] <= (7'(l * 8 + tv) < l_rem) ? bf16(l_d[l*256 + 32*tv +: 32]) : 16'd0;
    end
    // ---- emission decision E0: (eg, et, eb) -> slot, read enables
    wire e_slot_ok;
    reg [3:0] e_slot; reg e_has;
    always @* begin
        e_has = 1'b0; e_slot = 4'd0;
        for (integer x = 0; x < NBMAX; x = x + 1)
            if (eb == 7'(x) && bslot(x) >= 0) begin e_has = 1'b1; e_slot = 4'(bslot(x)); end
    end
    assign e_slot_ok = em_on && e_has && e_slot < pp;
    // emission metadata delay line E0 -> E6: {v, ok, last, addr 7, b 7}
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
    // ---- macro field
    wire [255:0] cap [0:31];
    reg  [255:0] or4 [0:7];
    genvar gt, gq;
    generate for (gt = 0; gt < 8; gt = gt + 1) begin : g_t
        for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
            (* keep = 1 *) reg rp_ce; (* keep = 1 *) reg [6:0] rp_a; reg rp_sel;
            (* keep = 1 *) reg wp_ce; (* keep = 1 *) reg [6:0] wp_a; reg [255:0] wp_d; reg [255:0] wp_m;
            reg [255:0] cq;
            wire [255:0] rd;
            always @(posedge clk or negedge rn) begin
                if (!rn) begin rp_ce <= 1'b0; rp_sel <= 1'b0; wp_ce <= 1'b0; end
                else begin
                    rp_ce <= e_slot_ok && et == 3'(gt);
                    rp_sel <= rp_ce;
                    wp_ce <= c_v && c_wq[2:1] == 2'(gq);
                end
            end
            always @(posedge clk) begin
                rp_a <= {eg[3:0], e_slot[2:0]};
                wp_a <= {c_g, c_pp};
                for (integer l = 0; l < 8; l = l + 1) begin
                    wp_d[16*l +: 16] <= c_d[(gt*8 + l)*16 +: 16];
                    wp_d[128 + 16*l +: 16] <= c_d[(gt*8 + l)*16 +: 16];
                end
                wp_m <= c_wq[0] ? {{128{1'b1}}, 128'd0} : {128'd0, {128{1'b1}}};
                cq <= rd & {256{rp_sel}};
            end
            ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk),
                .r_ce_in(rp_ce), .r_addr_in(rp_a), .rd_out(rd),
                .w_ce_in(wp_ce), .w_addr_in(wp_a), .wd_in(wp_d), .w_mask_in(wp_m),
                .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
            assign cap[gt * 4 + gq] = cq;
        end
    end endgenerate
    always @(posedge clk) for (integer h = 0; h < 2; h = h + 1) for (integer q = 0; q < 4; q = q + 1)
        or4[h * 4 + q] <= cap[(4*h + 0)*4 + q] | cap[(4*h + 1)*4 + q] | cap[(4*h + 2)*4 + q] | cap[(4*h + 3)*4 + q];
    reg [1023:0] rw;
    always @(posedge clk) for (integer q = 0; q < 4; q = q + 1) rw[256*q +: 256] <= or4[q] | or4[4 + q];
    // ---- beat select (static per b) at E6 -> pins at E7
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
    // ed[RDP-2] = ed[4] is aligned with rw, ed[RDP-1] = ed[5] with the selected beat
    wire [EW-1:0] e5 = ed[RDP-2];
    wire [EW-1:0] e6 = ed[RDP-1];
    reg [2047:0] xbeat;
    always @(posedge clk) xbeat <= e5[EW-2] ? beats[e5[6:0]] : 2048'd0;
    always @(posedge clk or negedge rn) begin
        if (!rn) begin xw_en <= 1'b0; xw_last <= 1'b0; x_done <= 1'b0; end
        else begin xw_en <= e6[EW-1]; xw_last <= e6[EW-1] && e6[EW-3]; x_done <= xw_en && xw_last; end
    end
    always @(posedge clk) begin xw_addr <= e6[13:7]; xw_grp <= e6[6:0]; xw_data <= xbeat; end
endmodule
`default_nettype wire
