#!/usr/bin/env python3
"""S81-KITS-RTLC 10-25 (coordinator: bk_g non-vd face_guard): (1) dsdv_bk_vin lane data pin flops load the word only
(zero when no word: no hold self-loop); (2) per-lane kept live flops (no opt_merge of the 4 identical live chains);
(3) tap_k / sink_k bits 1 / 2 (kinds K_XQ / K_XB, never tapped or sunk: vstop excludes them) dropped at dsdv_bk_g:
packed strap [5:0] = {k[7:3], k[0]}."""
import re, sys
R = sys.argv[1] + "/rtl/dsrom_sys/s81_dv/unit/"
def sub(f, a, b, n=1):
    s = open(R + f).read(); c = s.count(a)
    assert c == n, (f, a[:70], c)
    open(R + f, "w").write(s.replace(a, b))
v = "bk/dsdv_bk_v.sv"
sub(v, '''    reg [4*515-1:0] lq;                   // lane registers; bit 515*l+513 (live) comes from u_live[l] instead
    genvar gl;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_live
        wire lv;
        dsdv_bk_live u_live (.clk(clk), .rst_n(rst_n), .q(lv));
        assign lanes[515 * gl +: 515] = {lq[515 * gl + 514], lv, lq[515 * gl + 1 +: 512], lq[515 * gl]};
    end endgenerate''',
'''    reg [4*515-1:0] lq;                   // lane registers; bit 515*l+513 (live) comes from lv_q[l] instead
    // S81-KITS-RTLC 10-25: one KEPT live chain per lane (the 4 identical chains were merged into one flop that fed all
    // four ln*[513] pins); the data bits load the word and are 0 when no word arrives (no hold self-loop at the pin)
    (* keep = "true" *) reg [3:0] lv_0, lv_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lv_0 <= 4'd0; lv_q <= 4'd0; end
        else begin lv_0 <= 4'hf; lv_q <= lv_0; end
    genvar gl;
    generate for (gl = 0; gl < 4; gl = gl + 1) begin : g_live
        assign lanes[515 * gl +: 515] = {lq[515 * gl + 514], lv_q[gl], lq[515 * gl + 1 +: 512], lq[515 * gl]};
    end endgenerate''')
sub(v, "            if (wv[l]) lq[515 * l + 1 +: 512] <= wd[l];",
"""`ifdef OT_RTLC_MUT_BKLN   // bench mutant: lane 1 keeps its previous word on a new word
            lq[515 * l + 1 +: 512] <= (wv[l] && l != 1) ? wd[l] : (l == 1 ? lq[515 * l + 1 +: 512] : 512'd0);
`else
            lq[515 * l + 1 +: 512] <= wv[l] ? wd[l] : 512'd0;     // wd[l] is 0 when !wv[l] (comb default)
`endif""")
g = "bk/dsdv_bk_g.sv"
s = open(R + g).read()
s = s.replace("    input  wire [7:0]        tap_k,\n    input  wire [7:0]        sink_k,",
 "    // S81-KITS-RTLC 10-25: tap_k / sink_k bits 1 / 2 (kinds K_XQ / K_XB) are never read by ot_dsdv_vstop (it\n"
 "    // excludes those kinds): packed straps {k[7:3], k[0]}, not pins\n"
 "    input  wire [5:0]        tap_k,\n    input  wire [5:0]        sink_k,", 1)
assert "input  wire [5:0]        tap_k" in s
a = "ot_dsdv_vstop #(.V(V), .BK_DRAIN_SINK(BK_DRAIN_SINK)) u_vs (.clk(clk[0]), .rst_n(rn), .tap_k(tap_k), .sink_k(sink_k),"
assert s.count(a) == 1
s = s.replace(a, "ot_dsdv_vstop #(.V(V), .BK_DRAIN_SINK(BK_DRAIN_SINK)) u_vs (.clk(clk[0]), .rst_n(rn), .tap_k({tap_k[5:1], 2'b00, tap_k[0]}), .sink_k({sink_k[5:1], 2'b00, sink_k[0]}),")
open(R + g, "w").write(s)
# every dsdv_bk_g instantiation: pack the straps
n = 0
for f in ["bk/dsdv_bk_sel.sv", "bk/dsdv_bk_sel_x.sv", "bk/dsdv_bk_col.sv", "bk/lp/dsdv_bk_sel_x_lp.sv", "bk/plana/dsdv_bk_sel_pa.sv",
          "bk/plana/lp/dsdv_bk_sel_pa_lp.sv", "bk/plana/n32/dsdv_bk_sel_pa_n32_lp.sv", "bk/plana/lp/tb_dsdv_bk_sel_pa_lp.sv"]:
    s = open(R + f).read()
    def fix(m):
        t = m.group(0)
        t = re.sub(r"\.tap_k\((\w+)\)", r".tap_k({\1[7:3], \1[0]})", t)
        t = re.sub(r"\.sink_k\((\w+)\)", r".sink_k({\1[7:3], \1[0]})", t)
        return t
    s2, k = re.subn(r"dsdv_bk_g\b[^;]*?\);", fix, s, flags=re.S)
    assert s2.count("[7:3]") - s.count("[7:3]") == 2 * k and k >= 1, (f, k)
    n += k; open(R + f, "w").write(s2)
print("ok", n)
