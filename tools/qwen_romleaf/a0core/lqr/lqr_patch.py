#!/usr/bin/env python3
"""QC-A0C-B5 11-06 vB form: LQR (default 0 = unchanged) for the A0 ROM tiles qfd_tile_nl_a0c / qfd_tile_nk_a0c.

Patches a kit's rtl/ copy in place (the kit RTL differs per core, like nkp15_patch.py):
  LQR bit0: one kept 512-bit capture register on every RPH 3 romleaf r_q output, on that leaf's own clock
            (the romleaf clk->q is ~385 ps of the 833 ps cycle; the OR tree to gs/gn gets its own cycle).  +1 RX.
  LQR bit1: one kept per-leaf request register {ce, any, ad} in front of every romleaf (the shared relay stage
            rq_*[ROM_ARELAY-1] -> leaf ad_d leg ends in a flop beside the leaf instead of the leaf pin).  +1 RX.
  LQR bit2: one kept register stage on the engine tree output -> hardened node leaf t_d / t_vd (NDH; rawleaf t_out ->
            node t_d leg).  The node passes t_d to the t_out pins: +1 cycle on t_out (PIN CYCLE), n_y unchanged.
RX (= the engine's MEM_EXTRA) absorbs bits 0/1, exactly as RQR / L1 do.  Bench mutants (`OT_LQR_MUT, non-synthesis
bench only): 1 = bit0 register without RX+1, 2 = RX+2, 3 = bank 0 column 1 r_q not registered.
usage: lqr_patch.py RTL_DIR TILE(nl|nk)
"""
import re, sys
from pathlib import Path

R = Path(sys.argv[1]); T = sys.argv[2]
DOC = "    // LQR (QC-A0C-B5 11-06 vB, opt-in, default 0 = unchanged): bit0 romleaf r_q capture register (+1 ROM cycle),\n" \
      "    // bit1 per-leaf request register (+1 ROM cycle), bit2 node t_d register (+1 t_out pin cycle)\n"

def sub(path, old, new, count=1, regex=False):
    p = R / path; s = p.read_text()
    n = len(re.findall(old, s)) if regex else s.count(old)
    if n != count:
        sys.exit(f"lqr_patch: {path}: expected {count} x {old!r}, found {n}")
    s = re.sub(old, new, s) if regex else s.replace(old, new)
    p.write_text(s)

W12 = "ot_qwen_rom_tile_w12_land32.sv"
# parameters: logic module + w12 wrapper, ot_qwen_rom_tile_nk, rp2_45
sub(W12, "    parameter integer NKP = 0\n) (", "    parameter integer NKP = 0,\n" + DOC + "    parameter integer LQR = 0\n) (", 2)
sub("ot_qwen_rom_tile_nk.sv", "    parameter integer NKP = 0\n) (", "    parameter integer NKP = 0,\n" + DOC + "    parameter integer LQR = 0\n) (")
sub(f"qfd_tile_{T}_rp2_45.sv", "    parameter integer NKP = 0\n) (", "    parameter integer NKP = 0,\n" + DOC + "    parameter integer LQR = 0\n) (")
if T == "nl":
    sub("qfd_tile_nl_a0c.sv", "  , parameter integer NKP = 0\n", "  , parameter integer NKP = 0\n" + DOC.replace("    //", "  //") + "  , parameter integer LQR = 0\n")
else:
    sub("qfd_tile_nk_a0c.sv", "    parameter integer NKP = 0,\n", "    parameter integer NKP = 0,\n" + DOC + "    parameter integer LQR = 0,\n")
# pass-through (not into the engine u_me)
sub(W12, r"\.NKP\(NKP\)\)(\s*u_logic\b)", r".NKP(NKP), .LQR(LQR))\1", 1, True)
sub("ot_qwen_rom_tile_nk.sv", r"\.NKP\(NKP\)\)(\s*u_tile\b)", r".NKP(NKP), .LQR(LQR))\1", 1, True)
sub(f"qfd_tile_{T}_rp2_45.sv", r"\.NKP\(NKP\)\)(\s*u_tile\b)", r".NKP(NKP), .LQR(LQR))\1", 1, True)
sub(f"qfd_tile_{T}_a0c.sv", r"\.NKP\(NKP\)\)(\s*u_g\b)", r".NKP(NKP), .LQR(LQR))\1", 2, True)

# RX (+ bench mutants)
OLD_RX = "+ ((L1 != 0) ? L1K : 0)) : 0;   // extra memory cycles of the ROM pipeline"
sub(W12, OLD_RX,
    "+ ((L1 != 0) ? L1K : 0) + LQRX) : 0;   // extra memory cycles of the ROM pipeline")
sub(W12, "    localparam integer L1K = 2;\n",
    "    localparam integer L1K = 2;\n"
    "`ifdef OT_LQR_MUT\n    localparam integer LQM = `OT_LQR_MUT;   // bench mutants only (see lqr_patch.py)\n`else\n"
    "    localparam integer LQM = 0;\n`endif\n"
    "    //: LQR (QC-A0C-B5 vB): + 1 ROM cycle per register stage on the romleaf loop (bit0 r_q capture, bit1 request)\n"
    "    localparam integer LQRX = (((LQR & 1) != 0 && LQM != 1) ? 1 : 0) + (((LQR & 1) != 0 && LQM == 2) ? 1 : 0)\n"
    "                            + (((LQR & 2) != 0) ? 1 : 0);\n", 1)

# romleaf: request + r_q registers
OLD_LEAF = re.compile(r"(                        ot_qwen_tile_romleaf\n`ifndef SYNTHESIS\n.*?`endif\n)"
                      r"                            u_leaf \(\.clk\(CHILD_CLOCKS \? \(col==0 \? ck_rpair\[b\] : ck_pair1\[b\]\) : clk\),\.rst_n\(rst_leaf\),\.ce_d\(ce_pre\[b\]\),\n"
                      r"                                \.any_d\(any_leaf\),\.ad_d\(\(b<SB\)\?adm_pre:adm_pre_n\),\.r_q\(r_q\[512\*col \+: 512\]\)\);\n", re.S)
NEW_LEAF = (
"                        //: LQR (QC-A0C-B5 vB): bit1 = kept {ce, any, ad} request copy beside the leaf, bit0 = kept r_q capture\n"
"                        //: register beside the leaf; both on the leaf's own clock, each + 1 ROM cycle (in RX)\n"
"                        wire ck_leaf = CHILD_CLOCKS ? (col==0 ? ck_rpair[b] : ck_pair1[b]) : clk;\n"
"                        wire lq_ce, lq_any; wire [11:0] lq_ad; wire [511:0] lq_rq;\n"
"                        if ((LQR & 2) != 0) begin : g_lqi\n"
"                            (* keep *) reg ce_l, any_l;\n"
"                            (* keep *) reg [11:0] ad_l;\n"
"                            always @(posedge ck_leaf or negedge rst_n) if (!rst_n) begin ce_l <= 1'b0; any_l <= 1'b0; end\n"
"                                else begin ce_l <= ce_pre[b]; any_l <= any_leaf; end\n"
"                            always @(posedge ck_leaf) ad_l <= (b<SB)?adm_pre:adm_pre_n;\n"
"                            assign lq_ce = ce_l; assign lq_any = any_l; assign lq_ad = ad_l;\n"
"                        end else begin : g_lqin\n"
"                            assign lq_ce = ce_pre[b]; assign lq_any = any_leaf; assign lq_ad = (b<SB)?adm_pre:adm_pre_n;\n"
"                        end\n"
"\\1"
"                            u_leaf (.clk(ck_leaf),.rst_n(rst_leaf),.ce_d(lq_ce),\n"
"                                .any_d(lq_any),.ad_d(lq_ad),.r_q(lq_rq));\n"
"                        if ((LQR & 1) != 0 && !(LQM == 3 && b == 0 && col == 1)) begin : g_lqr\n"
"                            (* keep *) reg [511:0] rq_l;\n"
"                            always @(posedge ck_leaf) rq_l <= lq_rq;\n"
"                            assign r_q[512*col +: 512] = rq_l;\n"
"                        end else begin : g_lqn\n"
"                            assign r_q[512*col +: 512] = lq_rq;\n"
"                        end\n")
p = R / W12; s = p.read_text()
s, n = OLD_LEAF.subn(NEW_LEAF, s)
if n != 1: sys.exit(f"lqr_patch: romleaf instance anchor found {n} x")
p.write_text(s)

# node t_d register (NK only: NODE 1, NDH)
if T == "nk":
    sub(W12, "        ot_qwen_tile_node u_node (.clk(CHILD_CLOCKS ? ck_node : clk), .rst_n(rst_n), .a(na_x), .b(n_b), .va(n_va),\n"
             "                                  .y(n_y), .vy(n_vy), .fault(node_fault),\n"
             "                                  .t_d(td_x), .t_vd(t_vout_i), .t_out(t_out_nd), .t_vout(t_vout_nd));\n",
        "        //: LQR bit2 (QC-A0C-B5 vB): kept t_d / t_vd register stage in front of the node leaf (+1 t_out pin cycle)\n"
        "        wire ck_nd = CHILD_CLOCKS ? ck_node : clk;\n"
        "        wire [W*32-1:0] td_n; wire tvd_n;\n"
        "        if ((LQR & 4) != 0) begin : g_lqt\n"
        "            (* keep *) reg [W*32-1:0] td_q;\n"
        "            (* keep *) reg            tvd_q;\n"
        "            always @(posedge ck_nd) td_q <= td_x;\n"
        "            always @(posedge ck_nd or negedge rst_n) if (!rst_n) tvd_q <= 1'b0; else tvd_q <= t_vout_i;\n"
        "            assign td_n = td_q; assign tvd_n = tvd_q;\n"
        "        end else begin : g_lqtn\n"
        "            assign td_n = td_x; assign tvd_n = t_vout_i;\n"
        "        end\n"
        "        ot_qwen_tile_node u_node (.clk(ck_nd), .rst_n(rst_n), .a(na_x), .b(n_b), .va(n_va),\n"
        "                                  .y(n_y), .vy(n_vy), .fault(node_fault),\n"
        "                                  .t_d(td_n), .t_vd(tvd_n), .t_out(t_out_nd), .t_vout(t_vout_nd));\n")

# form guard
sub(W12, "    localparam integer ME_EXTRA = MEM_EXTRA + RX;\n",
    "    localparam integer ME_EXTRA = MEM_EXTRA + RX;\n"
    "    generate if (LQR != 0 && (RPH != 3 || ROM_PIPE == 0 || LQR > 7)) begin : g_lqr_bad\n"
    "        initial $fatal(1, \"LQR needs RPH 3 (single romleaf form) and ROM_PIPE\");\n"
    "    end endgenerate\n")
print(f"lqr_patch: {R} ({T}) patched")
