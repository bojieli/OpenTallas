#!/usr/bin/env python3
"""ot_hfd_actquant_m: the margin-first (owner rule 2026-10-06) port of ot_dsrom_actquant_f12 (rtl/hdc/v41x/
ot_dsrom_su_f12.sv, lever su_swiglu 1d4ea2dc2, routed SS +11.51 ps at 833 ps).  Same function bit for bit; the
classes within 50 ps of failing in that route (aq_q5 6_final: g1_ev 89, g_lv[5] 30, scale multiplier rows 59,
g2_g / g2_rs 101, y 99 endpoints under +20 ps) each get one more stage:
  F   the floor compare after the last max level (was in M5 with the level-5 compare);
  K   the scale product as two constant-operand multipliers amax * (1/448) and amax * (1/6) (the same
      ot_hdc_qmul_lat #(MLAT) unit, the constant folded by synthesis), selected after the multiply;
  G0  e replicated in kept per-lane-group flops (ot_hfd_oreg1, 4 groups of 8 lanes) and the element exponent
      field decoded, so G1 is one subtract;
  G2a dd = min_exp - Ev registered, G2b the grid / shift select;
  C2a the BF16 exponent be = bb + p registered, C2b the select into y.
LATENCY = 13 + MLAT + 4 (22 at MLAT 5; f12 18; the original ot_hdc_actquant 13).
Writes ot_hfd_actquant_m.sv beside this script from the pinned f12 text (asserted edits)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
src = (ROOT / 'rtl/hdc/v41x/ot_dsrom_su_f12.sv').read_text().splitlines(keepends=True)
s0 = next(i for i, l in enumerate(src) if l.startswith('module ot_dsrom_actquant_f12'))
s1 = next(i for i in range(s0, len(src)) if src[i].startswith('endmodule'))
t = ''.join(src[s0:s1 + 1])


def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (a, t.count(a))
    t = t.replace(a, b)


rep('module ot_dsrom_actquant_f12 #(', 'module ot_hfd_actquant_m #(')
rep('localparam integer LATENCY = 13 + MLAT;', 'localparam integer LATENCY = 13 + MLAT + 4;')
# F: level 5 keeps the compare only; the floor compare moves to its own stage
rep("""                if (lv == 5) begin : g_fl            // the floor with the last level
                    wire [30:0] fl = lv_fp4[lv-1] ? FLOOR_FP4 : FLOOR_FP8;
                    wire gf;
                    ot_hdc_kge #(.W(31), .K(1)) u_gf (.a(m), .b(fl), .ge(gf));
                    always @(posedge clk) r[31*k +: 31] <= gf ? m : fl;
                end else begin : g_nf
                    always @(posedge clk) r[31*k +: 31] <= m;
                end""", """                always @(posedge clk) r[31*k +: 31] <= m;""")
rep("""    wire [30:0] amax = lvl[5][30:0];
""", """    // ---- F: the floor (its own stage: margin-first)
    reg [30:0] f_amax;
    reg f_v, f_fp4, f_nf;
    wire [30:0] fl = lv_fp4[5] ? FLOOR_FP4 : FLOOR_FP8;
    wire gf;
    ot_hdc_kge #(.W(31), .K(1)) u_gf (.a(lvl[5][30:0]), .b(fl), .ge(gf));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) f_v <= 1'b0; else f_v <= lv_v[5];
    end
    always @(posedge clk) begin f_amax <= gf ? lvl[5][30:0] : fl; f_fp4 <= lv_fp4[5]; f_nf <= lv_nf[5]; end
    wire [30:0] amax = f_amax;
""")
# K: two constant-operand multipliers, selected after the multiply (in E)
rep("""    wire [31:0] prod;
    wire        pfault;
    ot_hdc_qmul_lat #(MLAT) u_scale (clk, rst_n, lv_v[5], {1'b0, amax}, lv_fp4[5] ? INV_6 : INV_448, prod, pfault);
    wire [MLAT:0] vl;
    ot_hdc_vline #(.D(MLAT)) u_vl (.clk(clk), .rst_n(rst_n), .v(lv_v[5]), .vd(vl));
    wire p_fp4, p_nf;
    ot_hdc_delay #(.W(2), .D(MLAT)) u_dp (.clk(clk), .rst_n(rst_n), .d({lv_fp4[5], lv_nf[5]}), .q({p_fp4, p_nf}));""",
"""    wire [31:0] prod8, prod4, prod;
    wire        pfault8, pfault4, pfault;
    ot_hdc_qmul_lat #(MLAT) u_scale8 (clk, rst_n, f_v, {1'b0, amax}, INV_448, prod8, pfault8);
    ot_hdc_qmul_lat #(MLAT) u_scale4 (clk, rst_n, f_v, {1'b0, amax}, INV_6, prod4, pfault4);
    wire [MLAT:0] vl;
    ot_hdc_vline #(.D(MLAT)) u_vl (.clk(clk), .rst_n(rst_n), .v(f_v), .vd(vl));
    wire p_fp4, p_nf;
    ot_hdc_delay #(.W(2), .D(MLAT)) u_dp (.clk(clk), .rst_n(rst_n), .d({f_fp4, f_nf}), .q({p_fp4, p_nf}));
    assign prod = p_fp4 ? prod4 : prod8;
    assign pfault = p_fp4 ? pfault4 : pfault8;""")
rep('// the elements, S0 -> E (5 tree + MLAT multiply registers, then E itself: aligned at E\'s input)',
    '// the elements, S0 -> E (5 tree + F + MLAT multiply registers, then E itself: aligned at E\'s input)')
rep('ot_hdc_delay #(.W(1024), .D(6 + MLAT)) u_x', 'ot_hdc_delay #(.W(1024), .D(7 + MLAT)) u_x')
# G0: e replicated (kept), element exponent field decoded; G1 one subtract
rep("""    // ---- G1: Ev = exponent(x) - e, significand, sign
    reg               g1_v, g1_fp4, g1_nf;""", """    // ---- G0: e in 4 kept replicas (one per 8 lanes), the element fields decoded (margin-first)
    reg               g0_v, g0_fp4, g0_nf;
    reg signed [9:0]  g0_e;
    wire [39:0]       g0_er;                 // 4 x 10-bit replicas of e
    reg signed [10:0] g0_fe [0:31];
    reg [23:0]        g0_sig [0:31];
    reg [31:0]        g0_sgn;
    reg [7:0]         fld0;
    genvar gr, gb;
    generate for (gr = 0; gr < 4; gr = gr + 1) begin : g_er
        for (gb = 0; gb < 10; gb = gb + 1) begin : g_b
            ot_hfd_oreg1 u (.clk(clk), .d(e_e[gb]), .q(g0_er[10*gr + gb]));
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) g0_v <= 1'b0; else g0_v <= e_v;
    end
    reg [1023:0] xe1;
    always @(posedge clk) begin
        g0_fp4 <= e_fp4; g0_nf <= e_nf; g0_e <= e_e;
        for (i = 0; i < 32; i = i + 1) begin
            fld0 = xe[32*i + 23 +: 8];
            g0_fe[i] <= (fld0 == 8'd0) ? -11'sd126 : ($signed({3'b000, fld0}) - 11'sd127);
            g0_sig[i] <= {(fld0 != 8'd0), xe[32*i +: 23]};
            g0_sgn[i] <= xe[32*i + 31] && (xe[32*i +: 31] != 31'd0);
        end
    end

    // ---- G1: Ev = exponent(x) - e, significand, sign
    reg               g1_v, g1_fp4, g1_nf;""")
rep("""    reg [7:0]         fld;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) g1_v <= 1'b0; else g1_v <= e_v;
    end
    always @(posedge clk) begin
        g1_fp4 <= e_fp4; g1_nf <= e_nf; g1_e <= e_e;
        for (i = 0; i < 32; i = i + 1) begin
            fld = xe[32*i + 23 +: 8];
            g1_ev[i] <= ((fld == 8'd0) ? -11'sd126 : ($signed({3'b000, fld}) - 11'sd127)) - e_e;
            g1_sig[i] <= {(fld != 8'd0), xe[32*i +: 23]};
            g1_sgn[i] <= xe[32*i + 31] && (xe[32*i +: 31] != 31'd0);
        end
    end""", """    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) g1_v <= 1'b0; else g1_v <= g0_v;
    end
    always @(posedge clk) begin
        g1_fp4 <= g0_fp4; g1_nf <= g0_nf; g1_e <= g0_e;
        for (i = 0; i < 32; i = i + 1) begin
            g1_ev[i] <= g0_fe[i] - $signed(g0_er[10*(i/8) +: 10]);
            g1_sig[i] <= g0_sig[i];
            g1_sgn[i] <= g0_sgn[i];
        end
    end""")
# G2a / G2b
rep("""    reg signed [10:0] dd, mine;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) g2_v <= 1'b0; else g2_v <= g1_v;
    end
    always @(posedge clk) begin
        g2_fp4 <= g1_fp4; g2_nf <= g1_nf; g2_e <= g1_e; g2_sgn <= g1_sgn;
        mine = g1_fp4 ? 11'sd0 : -11'sd6;
        for (i = 0; i < 32; i = i + 1) begin
            dd = mine - g1_ev[i];
            g2_sig[i] <= g1_sig[i];
            if (dd > 11'sd0) begin
                g2_g[i] <= mine[4:0];
                g2_rs[i] <= (dd > (g1_fp4 ? 11'sd4 : 11'sd6)) ? 5'd26 : ((g1_fp4 ? 5'd22 : 5'd20) + dd[4:0]);
            end else begin
                g2_g[i] <= g1_ev[i][4:0];
                g2_rs[i] <= g1_fp4 ? 5'd22 : 5'd20;
            end
        end
    end""", """    reg signed [10:0] dd, mine;
    // G2a: dd = min_exp - Ev registered (margin-first)
    reg              ga_v, ga_fp4, ga_nf;
    reg signed [9:0] ga_e;
    reg [23:0]       ga_sig [0:31];
    reg signed [10:0] ga_dd [0:31];
    reg [4:0]        ga_ev [0:31];
    reg [31:0]       ga_sgn;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ga_v <= 1'b0; else ga_v <= g1_v;
    end
    always @(posedge clk) begin
        ga_fp4 <= g1_fp4; ga_nf <= g1_nf; ga_e <= g1_e; ga_sgn <= g1_sgn;
        mine = g1_fp4 ? 11'sd0 : -11'sd6;
        for (i = 0; i < 32; i = i + 1) begin
            ga_dd[i] <= mine - g1_ev[i];
            ga_ev[i] <= g1_ev[i][4:0];
            ga_sig[i] <= g1_sig[i];
        end
    end
    // G2b: the grid exponent and shift select
    reg signed [10:0] mineb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) g2_v <= 1'b0; else g2_v <= ga_v;
    end
    always @(posedge clk) begin
        g2_fp4 <= ga_fp4; g2_nf <= ga_nf; g2_e <= ga_e; g2_sgn <= ga_sgn;
        mineb = ga_fp4 ? 11'sd0 : -11'sd6;
        for (i = 0; i < 32; i = i + 1) begin
            g2_sig[i] <= ga_sig[i];
            if (ga_dd[i] > 11'sd0) begin
                g2_g[i] <= mineb[4:0];
                g2_rs[i] <= (ga_dd[i] > (ga_fp4 ? 11'sd4 : 11'sd6)) ? 5'd26 : ((ga_fp4 ? 5'd22 : 5'd20) + ga_dd[i][4:0]);
            end else begin
                g2_g[i] <= ga_ev[i];
                g2_rs[i] <= ga_fp4 ? 5'd22 : 5'd20;
            end
        end
    end""")
# C2a / C2b
rep("""    // ---- C2: the dequantised value c * 2^(g - mant_bits + e) as BF16
    reg signed [11:0] be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= c1_v; fault <= c1_v && c1_nf; end
    end
    always @(posedge clk) begin
        e <= c1_e;
        q <= c1_q;
        for (i = 0; i < 32; i = i + 1) begin
            be = c1_bb[i] + $signed({9'd0, c1_p[i]});
            if (c1_z[i])             y[16*i +: 16] <= {c1_sgn[i], 15'd0};
            else if (be >= 12'sd255) y[16*i +: 16] <= {c1_sgn[i], 8'hFF, 7'd0};
            else if (be >= 12'sd1)   y[16*i +: 16] <= {c1_sgn[i], be[7:0], c1_cn[i][6:0]};
            else                     y[16*i +: 16] <= {c1_sgn[i], 8'd0, c1_sub[i]};
        end
    end""", """    // ---- C2a: the BF16 exponent be = bb + p registered (margin-first)
    reg              ca_v, ca_nf;
    reg signed [9:0] ca_e;
    reg [255:0]      ca_q;
    reg signed [11:0] ca_be [0:31];
    reg [6:0]        ca_cn [0:31];
    reg [6:0]        ca_sub [0:31];
    reg [31:0]       ca_z, ca_sgn;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ca_v <= 1'b0; else ca_v <= c1_v;
    end
    always @(posedge clk) begin
        ca_nf <= c1_nf; ca_e <= c1_e; ca_q <= c1_q; ca_z <= c1_z; ca_sgn <= c1_sgn;
        for (i = 0; i < 32; i = i + 1) begin
            ca_be[i] <= c1_bb[i] + $signed({9'd0, c1_p[i]});
            ca_cn[i] <= c1_cn[i][6:0];
            ca_sub[i] <= c1_sub[i];
        end
    end
    // ---- C2b: the dequantised value c * 2^(g - mant_bits + e) as BF16
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= ca_v; fault <= ca_v && ca_nf; end
    end
    always @(posedge clk) begin
        e <= ca_e;
        q <= ca_q;
        for (i = 0; i < 32; i = i + 1) begin
            if (ca_z[i])                 y[16*i +: 16] <= {ca_sgn[i], 15'd0};
            else if (ca_be[i] >= 12'sd255) y[16*i +: 16] <= {ca_sgn[i], 8'hFF, 7'd0};
            else if (ca_be[i] >= 12'sd1)   y[16*i +: 16] <= {ca_sgn[i], ca_be[i][7:0], ca_cn[i]};
            else                           y[16*i +: 16] <= {ca_sgn[i], 8'd0, ca_sub[i]};
        end
    end""")
t = t.replace('reg [1023:0] xe1;\n', '')
hdr = ('// GENERATED by make_actquant_m.py from rtl/hdc/v41x/ot_dsrom_su_f12.sv (ot_dsrom_actquant_f12): margin-first port,\n'
       '// same function bit for bit, +4 stages (F, G0, G2a, C2a) and two constant-operand scale multipliers; see the script.\n'
       '`timescale 1ns/1ps\n')
Path(__file__).with_name('ot_hfd_actquant_m.sv').write_text(hdr + t)
print('ok')
