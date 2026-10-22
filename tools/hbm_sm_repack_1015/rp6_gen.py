#!/usr/bin/env python3
"""HBM-ELEM13/SMH-R6 r6 (10-21, RELEASE_TREE H.STA.BLK.14.6): GEOMETRIC regional smh_attn halves.

Why: r5 (rp5_gen.py) cut the half into clock DOMAINS by register mass, not geometric regions: ck_x held the top beat /
pin band (bin W face y1127-1507, bout E face, top pins) AND the x store (y734) AND its operand registers, ck_m held the
6-stage gin relay from the top pin to the bottom merge, so every root's tree spanned the whole 691 x 1512 half.  Measured
(gate smh_rp5n_m-20261021-154014 cts.log, TT): ck_c pin spread 242.3, ck_x 415.4 (45.4k sinks, 27 levels), ck_m 267.4.

r6 = every region is a geometric BAND of the half (placement fences, physical/hbm_smh_r6/fence_*.tcl); every child sits on
the root of the band it physically occupies; every band seam is a 4-slot fixed-latency landing (tools/landed_parent/lp.py,
reschedule mode, +E+1 = 3 edges per landed net); relay chains that cross bands are split at the seams; the pin registers
of each face are on the root of the band at that face; rout (the row-transport exit, driven by the hard child
ot_smh_tr_group_row_e whose internal insertion is 104-119 ps TT) gets a glue pin register (+1, priced) so every boundary
set is plain glue flops.  The reset port is captured on the root of the band at its pin (one stage, u_lpr_pin, uniform +1)
and handed to the lp regional run (reset_net) rooted in the band whose hops to every other band are <= 2 x 405 um.

  n half (691.2 x 1512; children: merge y43, rows / qk y388, bdc / h0 / h1 y518, x store y734-1123, beat band y1123+)
    MAIN (v m): 4 bands  t = beat / pin band (y >= 1123.2: bin / bout / gin / straps / attn), u = x store band
                (712.8-1123.2), c = rows + columns (302.4-712.8, rin / rout faces), m = merge + S-face outputs (< 302.4)
    FB   (v f): 3 bands  t, u as MAIN, c = rows + columns + merge + S-face outputs (y < 712.8; the PV merge on the column
                root as the r5 FB, no c -> m seam: fewer landings / sinks, the S-face and W/E-face pins share one root)
  s half (691.2 x 1252.8; N face = xi_* from the n half + rst_n, S face = gout + straps)
    MAIN (v m): 3 bands  u = x store + N-face entry (>= 712.8), c, m
    FB   (v f): 3 bands  t = N-face entry (>= 1123.2) apart from the x store band u, c = rows + columns + merge

Latency bookkeeping, MAIN vs r5 MAIN (edges; a landed net = +3):
  n: st / bk1 / ohl land t -> u (+3) with their 3 relays removed: 0.  rl1 c -> u, x->c bundles, pf u -> m, c -> m as r5.
     gin: gi1 2 (t) + land t -> c + gic 0 (c) + land c -> m + gim 3 (m) = 11 = r5 (2 + 3 + 6): 0.
     xb crossing: xb1 / xb2 removed, landn (t) -> land t -> c -> xbc 0 (c) -> land c -> m -> xbo: xo_b +2 (r3 +3).
     bout 0 (MAIN chain in t; FB pb -> land -> be2 = 5 = r5).  rout_n +1 (glue).  xo_g0 / xo_gp 0.
  s: xi_b arrives +2 -> MAIN leaf inputs +2 (bk1 path all in u as r5; rl1 pad 3 -> 5; strap pad 1 -> 3);
     FB +3 (u_lands in t, bk1 lands t -> u with its 2 relays removed: +1; rl1 pad 3 -> 6; strap pad 1 -> 4).
     gather lanes: xgi (u / t) -> land -> xg2 a (c) -> land c -> m: r5 1 + 1 + 3 -> r6 1 + 3 + a + 3: a = 0 (MAIN) / 1 (FB)
     so every gs lane shifts +2 (MAIN) / +3 (FB).  rout_s +1 (glue).
  Every consumer's reset depth = r5 depth + its shift; whole-half reset +1 (u_lpr_pin) on both halves (uniform).
FB vs r5 FB (tauM 3): n st / bk1 / ohl t -> u landings replace the 3 relays (0); gin 2 + land t -> c + 3 = r5 (0);
  xb landn (t) -> land t -> c -> xbo: xo_b -1; s u_lands (t) -> land t -> u with the 2 bk relays removed: +1, so the s leaf
  inputs shift 0; gather lanes xgi (t) -> land t -> c -> xg2 1: 0.  DG = 5 = r5 FB; rout +1 (glue).
PRICED SCHEDULE CHANGE: gout lane G = 10 + DG, DG = 8 (r5 MAIN) -> 10 (r6 MAIN) per SM tile hop (FB 5 = r5 FB); rout +1
per half (row transport); xo_b (n -> s beat crossing, inside the frame) +2 MAIN / -1 FB; half reset release +1 (uniform).

    python3 tools/hbm_sm_repack_1015/rp6_gen.py            # writes the 4 flat parents + 4 lp specs
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL = "rtl/hbm_accel/sm/repack/h2a6"
REC = "results/arch/hbm_smh_r6_1021"
V2 = "{1'b1, 2068'b0}"
V50 = "{2'b11, 48'b0}"
V100 = "{2'b11, 48'b0, 2'b11, 48'b0}"
REACH = 405.0
TAUM = {"m": 6, "f": 3}   # leaf-internal shift at the merge / result select (MAIN c -> m landing; FB merge on c, as r5)
LCM = {"m": 3, "f": 0}    # fold pad on the merge band (pf lands u -> merge band: +3, + pad = TAUM)
# geometric bands (um, half-local): name -> (x0, y0, x1, y1) and the reset-hop centre
H = {"n": 1512.0, "s": 1252.8}
W = 691.2
BANDS = {
    ("n", "m"): {"u": (0.0, 712.8, W, 1123.2), "t": (0.0, 1123.2, W, 1512.0), "c": (0.0, 302.4, W, 712.8),
                 "m": (0.0, 0.0, W, 302.4)},
    ("n", "f"): {"u": (0.0, 712.8, W, 1123.2), "t": (0.0, 1123.2, W, 1512.0), "c": (0.0, 0.0, W, 712.8)},
    ("s", "m"): {"c": (0.0, 302.4, W, 712.8), "u": (0.0, 712.8, W, 1252.8), "m": (0.0, 0.0, W, 302.4)},
    ("s", "f"): {"u": (0.0, 712.8, W, 1123.2), "t": (0.0, 1123.2, W, 1252.8), "c": (0.0, 0.0, W, 712.8)},
}
# reset-hop centres (register mass of each band; the merge sits at y 43-346, rows 388, columns 518-661)
CENTRES = {
    ("n", "m"): {"u": [410.0, 918.0], "t": [345.0, 1317.0], "c": [440.0, 507.0], "m": [475.0, 190.0]},
    ("n", "f"): {"u": [410.0, 918.0], "t": [345.0, 1317.0], "c": [450.0, 360.0]},
    ("s", "m"): {"c": [440.0, 507.0], "u": [410.0, 982.0], "m": [475.0, 190.0]},
    ("s", "f"): {"u": [410.0, 918.0], "t": [345.0, 1188.0], "c": [450.0, 360.0]},
}
RESET_REGION = {("n", "m"): "u", ("n", "f"): "u", ("s", "m"): "c", ("s", "f"): "u"}
EXTRA_S = {"m": 2, "f": 0}          # s leaf-input shift vs r5 of the same form
DG = {"m": 10, "f": 5}              # gout shift vs the r3 halves (r5 MAIN 8 / FB 5)
SIGMA_N = 1                         # n leaf input shift vs r3 (as r5)
CHILD_SOURCES = [
    "rtl/lib/ot_hdly.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/v41rom/ot_v41_bterm.sv", "rtl/v41rom/ot_v41_bterm2.sv",
    "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv",
    "rtl/gpu/ot_gpu_bd_col.sv", "rtl/hdc/v41/ot_hdc_blockdot.sv", "rtl/gpu/ot_gpu_bulk_copy.sv", "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv",
    "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv",
    "rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv", "rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv", "rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv",
    "rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv", "rtl/hbm_accel/sm/ot_hbm_accel_stack.sv", "rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv",
    "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv", "rtl/hbm_accel/sm/ot_hbm_accel_smh_gu.sv",
    "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
    "physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir.v",
    "rtl/lib/ot_rst_relay.sv", "rtl/hdc/ot_hdc_cg.sv", "rtl/hbm_accel/cg/ot_cg_tile.sv",
    "rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv", "rtl/hbm_accel/sm/ot_hbm_smh_transport_group_masters.sv",
    "rtl/hbm_accel/sm/ot_hbm_smh_transport_split_masters.sv", "rtl/hbm_accel/sm/ot_hbm_smh_transport_group.sv",
    "rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_clocks.sv", "rtl/hbm_accel/sm/repack/ot_rp4l_children.sv",
    "rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_s3.sv", "rtl/hbm_accel/sm/repack/h2/ot_hbm_smh_rp4h.sv",
    "rtl/hbm_accel/sm/repack/h2a/ot_hbm_smh_rp4ah.sv", "rtl/hbm_accel/sm/repack/h2a5/ot_hbm_smh_rp5_soft.sv",
]
DEFINES = ["OT_SMH_CG_ENREG", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY", "OT_SMH_RSTPIN",
           "OT_SMH_HIER", "OT_SMH_PTW_OHDLY", "OT_SMH_PINREG", "OT_SMH_XREL", "OT_SMH_PRODUCTION_SHAPE", "OT_SMH_COMPACT_PT",
           "OT_SMH_GROUP_TRANSPORT", "OT_SMH_WEST_SPLIT", "OT_SMH_TRANSPORT_KEEP", "OT_SMH_RP4_SRST"]


def rb_of(h, v):
    """lp.py reset_tree(): RB = 1 + max(max hops, 1), hops = ceil(manhattan / 405) from the reset region"""
    c = CENTRES[(h, v)]
    rr = RESET_REGION[(h, v)]
    hops = [0 if r == rr else max(1, math.ceil((abs(c[r][0] - c[rr][0]) + abs(c[r][1] - c[rr][1])) / REACH)) for r in c]
    return 1 + max(max(hops), 1)


class Half:
    def __init__(self, half, var):
        self.h, self.v = half, var
        self.regions = list(BANDS[(half, var)])            # first = core region (= reset root region)
        assert self.regions[0] == RESET_REGION[(half, var)]
        self.M = "m" if var == "m" else "c"                      # the merge / S-face band
        self.tau, self.lcm = TAUM[var], LCM[var]
        self.RB = rb_of(half, var)
        if self.RB != 3:
            raise SystemExit(f"{half}{var}: RB {self.RB} != 3 (r5 consumer depths assume 3)")
        self.insts = []
        self.wires = []
        self.rst_nets = {}

    def W(self, decl):
        self.wires.append(decl)

    def R(self, region, depth):
        """reset net of total depth `depth` after u_lpr_pin (lp regional run RB + ot_rp5_rst) for one consumer in `region`"""
        if depth == self.RB:
            return "lpr_pin"
        if depth < self.RB + 1:
            raise SystemExit(f"{self.h}{self.v}: reset depth {depth} < RB + 1 = {self.RB + 1}")
        lst = self.rst_nets.setdefault((region, depth), [])
        lst.append(len(lst))
        return f"r_{region}{depth}[{len(lst) - 1}]"

    def I(self, region, text):
        assert region in self.regions, (region, text)
        self.insts.append((region, text))

    def emit_rst(self):
        out = []
        for (region, depth), lst in sorted(self.rst_nets.items()):
            self.W(f"wire [{len(lst) - 1}:0] r_{region}{depth};")
            out.append((region, f"ot_rp5_rst #(.N({depth - self.RB - 1}), .NC({len(lst)})) u_rst_{region}{depth} (.clk(clk), "
                                f".rst_n(lpr_pin), .r(r_{region}{depth}));"))
        return out

    # ---------------------------------------------------------------------------------------------- the attention leaf
    def leaf(self, j, st, at, rl1, bk1, rl1_relays, st_relays, bk_relays, dx, sigma):
        """leaf j: u part (relays, x store, xq), c part (bdc, h0, h1, qk, cap, pub), m part (fold pad, merge, go) -> g{j}.
        at = {region: strap net}; dx = reset depth of the r3 leaf core (n 6, s 11); sigma = leaf input shift vs r3."""
        M = self.M
        dX, dC, dM = dx + sigma, dx + sigma + 3, dx + sigma + self.tau
        p = f"{j}"
        for w in [f"wire [25:0] st_r{p};", f"wire [817:0] rl1_r{p};", f"wire [2068:0] bk1_r{p};", f"wire [12:0] ohl_r{p};",
                  f"wire x{p}_iv_b, x{p}_iv_f, x{p}_ifirst, x{p}_ilast, x{p}_ifp4, x{p}_ifirst_e, x{p}_ilast_e;",
                  f"wire [15:0] x{p}_itag, x{p}_itag_e;", f"wire [787:0] x{p}_iw, x{p}_ix;",
                  f"wire [1083:0] bb{p};", f"wire [533:0] fb{p};", f"wire [4:0] pp{p};", f"wire [6:0] pf{p}, pfp{p};",
                  f"wire bov{p}, bf{p}, fov{p}, qf{p}, mf{p}, ev{p}, pst{p}, ph{p}, pv{p};",
                  f"wire [31:0] by{p}, fy{p}, pd{p};", f"wire [15:0] bt{p}, ft{p}, et{p}, ptg{p};", f"wire [511:0] es{p};",
                  f"wire [255:0] s0_{p}, s1_{p};", f"wire lf0_{p}, lf1_{p};", f"wire [2:0] psl{p}, pos{p};", f"wire [3:0] pw{p};",
                  f"wire [49:0] g{p};"]:
            self.W(w)
        if rl1_relays is None:
            rl1x = rl1
        else:
            self.I("u", f"ot_rp4a_relay #(.W(818), .N({rl1_relays})) u_rl{p} (.clk(clk), .rst_n(1'b1), .d({rl1}), .q(rl1_r{p}));")
            rl1x = f"rl1_r{p}"
        self.I("u", f"ot_rp4a_relay #(.W(26), .N({st_relays})) u_st{p} (.clk(clk), .rst_n(1'b1), .d({st}), .q(st_r{p}));")
        self.I("u", f"ot_rp4a_relay #(.W(2069), .N({bk_relays})) u_bk{p} (.clk(clk), .rst_n(1'b1), .d({bk1}), .q(bk1_r{p}));")
        self.I("u", f"ot_rp4a_relay #(.W(13), .N({bk_relays})) u_oh{p} (.clk(clk), .rst_n(1'b1), .d({bk1}[2060:2048]), .q(ohl_r{p}));")
        self.I("u", f"ot_hbm_accel_smh_xs u_xs{p} (.clk(clk), .rst_a({self.R('u', dX)}), .xs_a1(st_r{p}[8:0]), .xs_g1(st_r{p}[13:9]), "
                    f".xs_a2(st_r{p}[20:14]), .xs_g2(st_r{p}[25:21]), .rl1({rl1x}), .bk1(bk1_r{p}), .ohl1(ohl_r{p}), "
                    f".o_iv_b(x{p}_iv_b), .o_iv_f(x{p}_iv_f), .o_ifirst(x{p}_ifirst), .o_ilast(x{p}_ilast), .o_ifp4(x{p}_ifp4), "
                    f".o_itag(x{p}_itag), .o_iw(x{p}_iw), .o_ix(x{p}_ix), .o_ifirst_e(x{p}_ifirst_e), .o_ilast_e(x{p}_ilast_e), "
                    f".o_itag_e(x{p}_itag_e));")
        self.I("u", f"ot_rp5_xq u_xq{p} (.clk(clk), .rst_n({self.R('u', dX)}), .at({at['u']}), .x_iv_b(x{p}_iv_b), .x_iv_f(x{p}_iv_f), "
                    f".x_ifirst(x{p}_ifirst), .x_ilast(x{p}_ilast), .x_ifp4(x{p}_ifp4), .x_itag(x{p}_itag), .x_iw(x{p}_iw), "
                    f".x_ix(x{p}_ix), .x_ifirst_e(x{p}_ifirst_e), .x_ilast_e(x{p}_ilast_e), .x_itag_e(x{p}_itag_e), "
                    f".bb(bb{p}), .fb(fb{p}), .pp(pp{p}), .pf(pf{p}));")
        self.I("c", f"ot_hbm_accel_smh_bdc u_bdc{p} (.clk(clk), .rst_a({self.R('c', dC)}), .i_v(bb{p}[1083]), .i_first(bb{p}[1082]), "
                    f".i_last(bb{p}[1081]), .i_fp4(bb{p}[1080]), .i_tag(bb{p}[1079:1064]), .i_w(bb{p}[1063:532]), .i_x(bb{p}[531:0]), "
                    f".ov(bov{p}), .y(by{p}), .otag(bt{p}), .fault(bf{p}));")
        self.I("c", f"ot_hbm_accel_smh_tcl_gu u_h0{p} (.clk(clk), .rst_a({self.R('c', dC)}), .i_v(fb{p}[533]), .i_first(fb{p}[532]), "
                    f".i_w(fb{p}[383:256]), .i_x(fb{p}[127:0]), .sum_o(s0_{p}), .lfault(lf0_{p}));")
        self.I("c", f"ot_hbm_accel_smh_tcl_gu u_h1{p} (.clk(clk), .rst_a({self.R('c', dC)}), .i_v(fb{p}[533]), .i_first(fb{p}[532]), "
                    f".i_w(fb{p}[511:384]), .i_x(fb{p}[255:128]), .sum_o(s1_{p}), .lfault(lf1_{p}));")
        self.I("c", f"ot_hbm_accel_smh_tct u_qk{p} (.clk(clk), .rst_a({self.R('c', dC)}), .i_v(fb{p}[533]), .i_last(fb{p}[531]), "
                    f".i_tag(fb{p}[527:512]), .sum_i({{s1_{p}, s0_{p}}}), .lf_a(lf0_{p}), .lf_b(lf1_{p}), .ov(fov{p}), .y(fy{p}), "
                    f".otag(ft{p}), .fault(qf{p}));")
        self.I("c", f"ot_rp4a_cap #(.TAGW(16)) u_cap{p} (.clk(clk), .rst_n({self.R('c', dC)}), .i_v(fb{p}[533]), .i_last(fb{p}[530]), "
                    f".i_run_first(fb{p}[529]), .i_run_last(fb{p}[528]), .i_tag(fb{p}[527:512]), .sum_i({{s1_{p}, s0_{p}}}), "
                    f".event_v(ev{p}), .event_sum(es{p}), .event_tag(et{p}));")
        self.I("c", f"ot_rp5_pub u_pub{p} (.clk(clk), .rst_n({self.R('c', dC - 1)}), .at({at['c']}), .pp(pp{p}), .pub_start(pst{p}), "
                    f".pub_slot(psl{p}), .published_h128(ph{p}));")
        self.I(M, f"ot_rp5_pad #(.W(7), .N({self.lcm})) u_fp{p} (.clk(clk), .d(pf{p}), .q(pfp{p}));")
        self.I(M, f"ot_rp5_merge u_mg{p} (.clk(clk), .rst_n({self.R(M, dM)}), .ev(ev{p}), .sum(es{p}), .tag_d(et{p}), "
                    f".pub_start(pst{p}), .pub_slot(psl{p}), .fold_start(pfp{p}[6]), .fold_a(pfp{p}[5:3]), .fold_b(pfp{p}[2:0]), "
                    f".pub_v(pv{p}), .pub_data(pd{p}), .pub_word(pw{p}), .pub_out_slot(pos{p}), .pub_tag(ptg{p}), .fault(mf{p}));")
        self.I(M, f"ot_rp5_go u_go{p} (.clk(clk), .rst_n({self.R(M, dM)}), .at({at['m']}), .bov(bov{p}), .by(by{p}), .bt(bt{p}), "
                    f".bfault(bf{p}), .fov(fov{p}), .fy(fy{p}), .ft(ft{p}), .qf(qf{p}), .mf(mf{p}), .ps_v(pv{p}), .ps_data(pd{p}), "
                    f".ps_word(pw{p}), .ps_slot(pos{p}), .published_h128(ph{p}), .g(g{p}));")
        return f"g{p}"

    # ------------------------------------------------------------------------------------------------------- halves
    def build_n(self):
        M, MAIN = self.M, self.v == "m"
        self.ports = ["input wire clk", "input wire rst_n",
                      "input wire [8:0] xs_a1", "input wire [4:0] xs_g1", "input wire [6:0] xs_a2", "input wire [4:0] xs_g2",
                      "input wire [4:0] attn", "input wire [817:0] rin_n", "input wire [2068:0] bin", "input wire [99:0] gin",
                      "output wire [817:0] rout_n", "output wire [2068:0] bout",
                      "output wire [2068:0] xo_b", "output wire [49:0] xo_g0", "output wire [99:0] xo_gp"]
        for w in ["wire lpr_pin;", "wire [25:0] st_n;", "wire [817:0] rl_n, rl1_n, rpm_n, rout_q;",
                  "wire [2068:0] bin_l, bt1, bm, be1, bk1_n, xbc;", "wire [99:0] gin_a, gin_r, gpm, gpr;",
                  "wire [49:0] g0m, g0r;", "wire [4:0] at_t;"]:
            self.W(w)
        # reset: captured beside its S-face pin on the S-face band root (the pin stage of the regional run, uniform +1)
        self.I(M, "ot_rp5_pad #(.W(1), .N(1)) u_lpr_pin (.clk(clk), .d(rst_n), .q(lpr_pin));")
        # t: top straps, the attention strap, the bin pin beat + the beat chain to the bout pin flop, bk1 source, gin entry
        self.I("t", "ot_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));")
        self.I("t", "ot_rp4a_astrap u_as (.clk(clk), .d((HMUT == 5) ? {attn[4:3] + 2'd1, attn[2:0]} : attn), .q(at_t));")
        self.I("t", f"ot_rp4l_pinbeat u_pb (.clk(clk), .rst_n({self.R('t', 3)}), .d(bin), .q(bin_l));")
        for nm, d, q in (("u_bt1", "bin_l", "bt1"), ("u_bt2", "bt1", "bm"), ("u_be1", "bm", "be1"), ("u_be2", "be1", "bout")):
            self.I("t", f"ot_rp4h_xreg #(.W(2069), .VMASK({V2})) {nm} (.clk(clk), .rst_n({self.R('t', 3)}), .d({d}), .q({q}));")
        self.I("t", f"ot_rp4h_xreg #(.W(2069), .VMASK({V2})) u_landn (.clk(clk), .rst_n({self.R('t', 3)}), .d(bin_l), .q(bk1_n));")
        self.I("t", f"ot_rp4a_relay #(.W(100), .N(2), .VMASK({V100})) u_gi1 (.clk(clk), .rst_n({self.R('t', 3)}), .d(gin), .q(gin_a));")
        # c: row pin register, row transport (hard), rout glue pin register (+1), the xb pass-through (mutant hook)
        self.I("c", f"ot_rp4l_pinrow u_pr_n (.clk(clk), .rst_n({self.R('c', 3)}), .d(rin_n), .q(rl_n));")
        self.I("c", f"ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rl_n), .first(rl1_n), .last(rpm_n));")
        self.I("c", f"ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rpm_n), .last(rout_q));")
        self.I("c", "ot_rp5_pad #(.W(818), .N(1)) u_ro_n (.clk(clk), .d(rout_q), .q(rout_n));")
        self.I("c", f"ot_rp4a_relay #(.W(2069), .N((HMUT == 1) ? 1 : 0), .VMASK({V2})) u_xbc (.clk(clk), .rst_n({self.R('c', 3)}), "
                    f".d(bk1_n), .q(xbc));")
        if MAIN:
            # gin / strap pass-throughs on c (the t -> m distance is two landings: t -> c -> m)
            self.W("wire [99:0] gin_c;")
            self.W("wire [4:0] at_m;")
            self.I("c", f"ot_rp4a_relay #(.W(100), .N(0), .VMASK({V100})) u_gic (.clk(clk), .rst_n({self.R('c', 3)}), .d(gin_a), .q(gin_c));")
            self.I("c", "ot_rp5_pad #(.W(5), .N(0)) u_atc (.clk(clk), .d(at_t), .q(at_m));")
            gin_m, at_m, nland = "gin_c", "at_m", 2
        else:
            gin_m, at_m, nland = "gin_a", "at_t", 1
        # leaf 0: st / bk1 / ohl land t -> u (the landing replaces their 3 relays), rl1 lands c -> u as r5
        g0 = self.leaf(0, "st_n", {"u": "at_t", "c": "at_t", "m": at_m}, "rl1_n", "bk1_n", None, 0, 0, 6, SIGMA_N)
        # merge band: gin pad (2 + landings + pad = r5 2 + 3 + tauM), gather join, xb out register, xg / xp out stages
        self.I(M, f"ot_rp4a_relay #(.W(100), .N({self.tau - 3 * (nland - 1)}), .VMASK({V100})) u_gim (.clk(clk), "
                  f".rst_n({self.R(M, 3)}), .d({gin_m}), .q(gin_r));")
        self.I(M, f"ot_rp4l_gn u_gn (.clk(clk), .rst_n({self.R(M, 3 + SIGMA_N + self.tau)}), .g0({g0}), .gin(gin_r), .g0m(g0m), .gpm(gpm));")
        self.I(M, f"ot_rp4h_xreg #(.W(2069), .VMASK({V2})) u_xbo (.clk(clk), .rst_n({self.R(M, 3)}), .d(xbc), .q(xo_b));")
        self.I(M, f"ot_rp4a_relay #(.W(50), .N(2), .VMASK({V50})) u_xgr (.clk(clk), .rst_n({self.R(M, 3)}), .d(g0m), .q(g0r));")
        self.I(M, f"ot_rp4a_relay #(.W(100), .N(2), .VMASK({V100})) u_xpr (.clk(clk), .rst_n({self.R(M, 3)}), .d(gpm), .q(gpr));")
        self.I(M, f"ot_rp4h_xreg #(.W(50), .VMASK({V50})) u_xgo (.clk(clk), .rst_n({self.R(M, 3)}), .d(g0r), .q(xo_g0));")
        self.I(M, f"ot_rp4h_xreg #(.W(100), .VMASK({V100})) u_xpo (.clk(clk), .rst_n({self.R(M, 3)}), .d(gpr), .q(xo_gp));")
        self.mut_child = f"u_rst_c{6 + SIGMA_N + 3 - 1}"

    def build_s(self):
        M, MAIN = self.M, self.v == "m"
        X = EXTRA_S[self.v]
        sig = 1 + X
        E = "u" if MAIN else "t"                  # the N-face entry band
        self.ports = ["input wire clk", "input wire rst_n",
                      "input wire [8:0] xss_a1", "input wire [4:0] xss_g1", "input wire [6:0] xss_a2", "input wire [4:0] xss_g2",
                      "input wire [4:0] attn", "input wire [817:0] rin_s", "output wire [817:0] rout_s",
                      "input wire [2068:0] xi_b", "input wire [49:0] xi_g0", "input wire [99:0] xi_gp", "output wire [199:0] gout"]
        for w in ["wire lpr_pin;", "wire [25:0] st_s, st_p;", "wire [817:0] rl_s, rl1_s, rl1_p, rpm_s, rout_q;",
                  "wire [2068:0] bk1_s;", "wire [49:0] xg, xg2o, g1p;", "wire [99:0] xp, xp2;", "wire [4:0] at_m;"]:
            self.W(w)
        # N-face entry: reset capture (pin stage of the regional run, uniform +1), bk1 landing register, gather-lane entry
        # u_lands reset depth = r3 8 + its data shift (xi_b vs r3: r5 +1; r6 MAIN +3 (n xb +2), FB 0 (n xb -1))
        db = 3 if MAIN else 0
        self.I(E, "ot_rp5_pad #(.W(1), .N(1)) u_lpr_pin (.clk(clk), .d(rst_n), .q(lpr_pin));")
        self.I(E, f"ot_rp4h_xreg #(.W(2069), .VMASK({V2})) u_lands (.clk(clk), .rst_n({self.R(E, 8 + db)}), .d(xi_b), .q(bk1_s));")
        self.I(E, f"ot_rp4h_xreg #(.W(50), .VMASK({V50})) u_xgi (.clk(clk), .rst_n({self.R(E, 3)}), .d(xi_g0), .q(xg));")
        self.I(E, f"ot_rp4h_xreg #(.W(100), .VMASK({V100})) u_xpi (.clk(clk), .rst_n({self.R(E, 3)}), .d(xi_gp), .q(xp));")
        # gather lanes: MAIN land (u -> c) + 0 (c) + land (c -> m) = r5 + 2; FB land (t -> c) + 1 (c) = r5 FB
        a = 0 if MAIN else 1
        self.I("c", f"ot_rp4a_relay #(.W(50), .N({a}), .VMASK({V50})) u_xg2 (.clk(clk), .rst_n({self.R('c', 3)}), .d(xg), .q(xg2o));")
        self.I("c", f"ot_rp4a_relay #(.W(100), .N((HMUT == 2) ? {a + 1} : {a}), .VMASK({V100})) u_xp2 (.clk(clk), "
                    f".rst_n({self.R('c', 3)}), .d(xp), .q(xp2));")
        # S-face straps and the attention strap (merge band), read by xq (u) / pub (c) through landings (static)
        self.I(M, "ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));")
        self.I(M, "ot_rp4a_astrap u_as (.clk(clk), .d({attn[4:3] + 2'd1, attn[2:0]}), .q(at_m));")
        # c: row pin register, row transport, rout glue pin register (+1), rl1 / strap alignment pads
        self.I("c", f"ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n({self.R('c', 3)}), .d(rin_s), .q(rl_s));")
        self.I("c", f"ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rl_s), .first(rl1_s), .last(rpm_s));")
        self.I("c", f"ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rpm_s), .last(rout_q));")
        self.I("c", "ot_rp5_pad #(.W(818), .N(1)) u_ro_s (.clk(clk), .d(rout_q), .q(rout_s));")
        self.I("c", f"ot_rp5_pad #(.W(818), .N((HMUT == 3) ? {2 + X} : {3 + X})) u_prl (.clk(clk), .d(rl1_s), .q(rl1_p));")
        # straps: MAIN m -> land -> pst (c) -> land -> 1 relay (u); FB pst (c) -> land -> 2 relays (u) (r5 forms)
        self.I("c", f"ot_rp5_pad #(.W(26), .N({(1 if MAIN else 3) + X})) u_pst (.clk(clk), .d(st_s), .q(st_p));")
        bk_rel = 2 if MAIN else 0
        g1 = self.leaf(1, "st_p", {"u": "at_m", "c": "at_m", "m": "at_m"}, "rl1_p", "bk1_s", "(HMUT == 6) ? 1 : 2",
                       1 if MAIN else 2, bk_rel, 11, sig)
        gs_d = 8 + sig + self.tau + 1
        self.I(M, f"ot_rp4a_relay #(.W(50), .N(3), .VMASK({V50})) u_g1p (.clk(clk), .rst_n({self.R(M, gs_d)}), .d({g1}), .q(g1p));")
        self.I(M, f"ot_rp4l_gs u_gs (.clk(clk), .rst_n({self.R(M, gs_d)}), .g1in(g1p), .g0m(xg2o), .gpm(xp2), .gout(gout));")
        self.mut_child = f"u_rst_c{11 + sig + 3 - 1}"
    def write(self):
        (self.build_n if self.h == "n" else self.build_s)()
        rst = self.emit_rst()
        top = f"ot_hbm_smh_rp6{self.h}_{self.v}_flat"
        form = {"m": "MAIN", "f": "FALLBACK"}[self.v]
        L = ["`timescale 1ns/1ps",
             f"// GENERATED by tools/hbm_sm_repack_1015/rp6_gen.py (HBM-ELEM13/SMH-R6 r6 {form}, geometric bands "
             f"{'/'.join(self.regions)}):",
             f"// wires-only flat parent of the regional {self.h} half (single clk; lp.py lands it).  RB {self.RB} (lp regional run "
             "after the u_lpr_pin capture).",
             f"// Region of each child in the lp spec {REC}/lp_spec_{self.h}_{self.v}.json.  HMUT: bench mutants (0 in kits).",
             f"module {top} #(parameter integer HMUT = 0) (", "    " + ",\n    ".join(self.ports), ");"]
        L += ["    " + w for w in self.wires]
        for _, t in rst + self.insts:
            L.append(f"    {t}")
        L.append("endmodule")
        (ROOT / RTL).mkdir(parents=True, exist_ok=True)
        (ROOT / RTL / f"{top}.sv").write_text("\n".join(L) + "\n")
        names = {}
        for r, t in rst + self.insts:
            m = re.search(r"\)\s*(u_\w+)\s*\(|^\w+\s+(u_\w+)\s*\(", t)
            names.setdefault(r, []).append(m.group(1) or m.group(2))
        c = CENTRES[(self.h, self.v)]
        spec = dict(
            top=top, top_lp=f"ot_hbm_smh_rp6{self.h}_{self.v}",
            why=(f"HBM-ELEM13/SMH-R6 10-21 r6 {self.h} half {form}: geometric bands {'/'.join(self.regions)} (one CTS root per "
                 "band, placement fences), every band seam a 4-slot landing (reschedule: latency shifts priced in rp6_gen.py)"),
            sources=[f"{RTL}/{top}.sv"], child_sources=CHILD_SOURCES, defines=DEFINES,
            out_dir=f"{RTL}/lp_{self.h}_{self.v}", record_dir=REC,
            clock_ports=["clk"], clock_pins=["clk"], reset_port="rst_n", reset_net="lpr_pin", reset_pins=["rst_n", "rst_a"],
            regions=[dict(name=r, insts=sorted(names.get(r, [])), centre=c[r]) for r in self.regions],
            reset_region=RESET_REGION[(self.h, self.v)], D=4, E=2, reschedule=True, landing_chunk_bits=24,
            landing_reset_forest=True,
            bench=dict(cycles=3000, reset_cycles=16, sim="verilator", expr={"attn": "5'd13"}),
            tb_static={"attn": "5'd13"},
            mut_child=self.mut_child, mut4_stages=64,
            r6=dict(bands={r: BANDS[(self.h, self.v)][r] for r in self.regions}, dg=DG[self.v], rout_glue=1,
                    xo_b_shift_vs_r5_same_form=(2 if self.v == "m" else -1), reset_pin_stage=1,
                    tau_merge=self.tau),
        )
        (ROOT / REC).mkdir(parents=True, exist_ok=True)
        p = ROOT / REC / f"lp_spec_{self.h}_{self.v}.json"
        p.write_text(json.dumps(spec, indent=1) + "\n")
        print(f"{top}: RB {self.RB}, {len(self.insts) + len(rst)} children, regions "
              + ", ".join(f"{r}:{len(names.get(r, []))}" for r in self.regions) + f" -> {p.relative_to(ROOT)}")


def main():
    for h in ("n", "s"):
        for v in ("m", "f"):
            Half(h, v).write()


if __name__ == "__main__":
    main()
