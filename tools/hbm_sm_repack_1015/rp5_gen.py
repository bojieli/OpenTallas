#!/usr/bin/env python3
"""HBM-OWN/SMH2 r5 (10-21, RELEASE_TREE H.STA.BLK.14 / 14.6): REGIONAL smh_attn halves.

Why: every one-root form of the rp4a halves fails the child-boundary clock rule (r3 K64 agg 244.8 TT / 218.3 FF; r4sp
spine placement-RC pin-flop spread 294-319 / r4spb 191-210 ps): the x store's boundary insertion (453-529 TT) and the
columns' (104-188) / PV merge's (263-313) cannot share one tree across a 691 x 1252..1512 um half.  r5 = structural: the
half is cut into REGIONS by register mass, each region its own CTS root (multiple_cts_roots, landed cluster), every region
crossing a 4-slot fixed-latency landing ring (tools/landed_parent/lp.py, reschedule mode: +E+1 = 3 edges per landed
net, priced below).

  MAIN (var m): 3 regions  x = x store + its operand registers (+ n: the bin/beat band, straps, gin entry, xb crossing
                start; s: the N-face bk1 landing u_lands + the gather-lane entry), c = rows + block-dot / BF16 columns / QK
                tree / sum capture / publication line, m = PV merge + result select + gather lanes + S-face outputs.
  FB   (var f): 2 regions  x as MAIN, c = c + m (merge on the column root).

This script writes, for half in (n, s) and var in (m, f):
  rtl/hbm_accel/sm/repack/h2a5/ot_hbm_smh_rp5<h>_<v>_flat.sv   wires-only flat parent (single clk; lp input)
  results/arch/hbm_smh_r5_1021/lp_spec_<h>_<v>.json             lp spec (regions, reschedule, chunked landings)
then `python3 tools/landed_parent/lp.py gen <spec>` emits the landed half ot_hbm_smh_rp5<h>_<v> (ck_x / ck_c [/ ck_m]).

Latency bookkeeping (frame = n over s, edges relative to the rp4a r3 halves, kits GN 2 GS 2 XB 2 LR 2 OS 1):
  n: rl1 lands c->x (+3 for the 2 LR relays: +1) -> bk1 / ohl / st relays 2 -> 3: leaf-0 inputs +1 (sigma_n = 1).
     leaf internal: x->c +3, c->m +3 (MAIN; FB +3 only): g0 +7 (FB +4); gin lane: 2 x-stages + land x->m + 6 (FB 3) pads.
     xb crossing: xb1, xb2 (x) + land x->m + xbo: bin -> xo_b 6 edges (was 5): xo_b +1 (delta_b = 1).
     xo_g0 / xo_gp +7 (FB +4); bout / rout_n 0.
  s: bk1 arrives +1 (delta_b): rl1 pad 5 -> 3 (+ land c->x + 2 relays = 8 = 7 + 1), straps m->c->x (MAIN) / c->x (FB):
     leaf-1 inputs +1; leaf internal as n: g1 +7 (FB +4); gather lanes: xgi, xg2 (x) + land x->m (FB x->c): +1 on the
     lanes (was xgi, xg2, xg3 x2); g1 pad 2 -> 3.  gout: every lane +8 (MAIN) / +5 (FB) vs r3; rout_s 0.
  Every consumer's reset depth = r3 depth + its shift (so every static child calendar shifts with its data, exact);
  the lp regional run supplies RB stages, ot_rp5_rst the rest (kept copies per consumer).
PRICED SCHEDULE CHANGE (checklist 8): rp4a gout lane G = 2+GN+GS+LR+2*OS = 10 -> 18 (MAIN) / 15 (FB) per SM tile hop;
the parent re-solves BE_DELAY / GPAD with the new G (smh_attn_rp4a_kit.py --half main=r5m).

    python3 tools/hbm_sm_repack_1015/rp5_gen.py            # writes the 4 flat parents + 4 lp specs
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL = "rtl/hbm_accel/sm/repack/h2a5"
REC = "results/arch/hbm_smh_r5_1021"
VM_TOP = {"n": "ot_hbm_smh_rp4ah_n", "s": "ot_hbm_smh_rp4ah_s"}
V2 = "{1'b1, 2068'b0}"
V50 = "{2'b11, 48'b0}"
V100 = "{2'b11, 48'b0, 2'b11, 48'b0}"
SIGMA = 1      # leaf input shift (both halves, frame)
REACH = 405.0
# region centres (um, half-local; the regional reset run hops <= 405 um from the reset root c)
CENTRES = {
    "n": {"x": [380.0, 1120.0], "c": [440.0, 560.0], "m": [475.0, 200.0]},
    "s": {"x": [410.0, 1000.0], "c": [440.0, 560.0], "m": [475.0, 200.0]},
}
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
    "rtl/hbm_accel/sm/repack/h2a/ot_hbm_smh_rp4ah.sv", f"{RTL}/ot_hbm_smh_rp5_soft.sv",
]
DEFINES = ["OT_SMH_CG_ENREG", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY", "OT_SMH_RSTPIN",
           "OT_SMH_HIER", "OT_SMH_PTW_OHDLY", "OT_SMH_PINREG", "OT_SMH_XREL", "OT_SMH_PRODUCTION_SHAPE", "OT_SMH_COMPACT_PT",
           "OT_SMH_GROUP_TRANSPORT", "OT_SMH_WEST_SPLIT", "OT_SMH_TRANSPORT_KEEP", "OT_SMH_RP4_SRST"]


def rb_of(half, regions):
    """lp.py reset_tree(): RB = 1 + max(max hops, 1), hops = ceil(manhattan / 405) from the reset region c"""
    c = CENTRES[half]
    hops = [0 if r == "c" else max(1, math.ceil((abs(c[r][0] - c["c"][0]) + abs(c[r][1] - c["c"][1])) / REACH)) for r in regions]
    return 1 + max(max(hops), 1)


class Half:
    def __init__(self, half, var):
        self.h, self.v = half, var
        self.regions = ["c", "x", "m"] if var == "m" else ["c", "x"]   # first = core region (clock_port / reset root)
        self.M = "m" if var == "m" else "c"
        self.LCM = 3 if var == "m" else 0                              # c -> m landing (+3) on the MAIN leaf
        self.tauM = 6 if var == "m" else 3                             # leaf-internal shift at the merge / result select
        self.RB = rb_of(half, self.regions)
        self.insts = []          # (region, text)
        self.wires = []
        self.rst_req = []        # (region, depth, inst-key) -> filled in by R()
        self.rst_nets = {}

    def W(self, decl):
        self.wires.append(decl)

    def R(self, region, depth):
        """reset net of total depth `depth` (lp run RB + ot_rp5_rst) for one consumer in `region`"""
        if depth == self.RB:
            return "rst_n"
        if depth < self.RB + 1:
            raise SystemExit(f"{self.h}{self.v}: reset depth {depth} < RB + 1 = {self.RB + 1}")
        k = (region, depth)
        n = self.rst_nets.setdefault(k, [])
        idx = len(n)
        n.append(idx)
        return f"r_{region}{depth}[{idx}]"

    def I(self, region, text):
        self.insts.append((region, text))

    def emit_rst(self):
        out = []
        for (region, depth), lst in sorted(self.rst_nets.items()):
            nc = len(lst)
            self.W(f"wire [{nc - 1}:0] r_{region}{depth};")
            out.append((region, f"ot_rp5_rst #(.N({depth - self.RB - 1}), .NC({nc})) u_rst_{region}{depth} (.clk(clk), "
                                f".rst_n(rst_n), .r(r_{region}{depth}));"))
        return out

    def straps(self, d):
        """the STATIC attention strap (attn: identity strap, case-analysed) lands in 2 kept stages in EVERY region that
        reads it (lp: a static port is read directly per region; a strap net crossing regions would be unlanded)"""
        for r in dict.fromkeys(["x", "c", self.M]):
            self.W(f"wire [4:0] at_{r};")
            self.I(r, f"ot_rp4a_astrap u_as_{r} (.clk(clk), .d({d}), .q(at_{r}));")

    # ---------------------------------------------------------------------------------------------- the attention leaf
    def leaf(self, j, st, at, rl1, bk1, rl1_relays, st_relays, bk_relays, dx):
        """leaf j: x part (relays, x store, xq), c part (bdc, h0, h1, qk, cap, pub), m part (fold pad, merge, go) -> g{j}.
        dx = reset depth of the r3 leaf core (n 6, s 11)."""
        M, s = self.M, SIGMA
        dX, dC, dM = dx + s, dx + s + 3, dx + s + self.tauM
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
            self.I("x", f"ot_rp4a_relay #(.W(818), .N({rl1_relays})) u_rl{p} (.clk(clk), .rst_n(1'b1), .d({rl1}), .q(rl1_r{p}));")
            rl1x = f"rl1_r{p}"
        self.I("x", f"ot_rp4a_relay #(.W(26), .N({st_relays})) u_st{p} (.clk(clk), .rst_n(1'b1), .d({st}), .q(st_r{p}));")
        self.I("x", f"ot_rp4a_relay #(.W(2069), .N({bk_relays})) u_bk{p} (.clk(clk), .rst_n(1'b1), .d({bk1}), .q(bk1_r{p}));")
        self.I("x", f"ot_rp4a_relay #(.W(13), .N({bk_relays})) u_oh{p} (.clk(clk), .rst_n(1'b1), .d({bk1}[2060:2048]), .q(ohl_r{p}));")
        self.I("x", f"ot_hbm_accel_smh_xs u_xs{p} (.clk(clk), .rst_a({self.R('x', dX)}), .xs_a1(st_r{p}[8:0]), .xs_g1(st_r{p}[13:9]), "
                    f".xs_a2(st_r{p}[20:14]), .xs_g2(st_r{p}[25:21]), .rl1({rl1x}), .bk1(bk1_r{p}), .ohl1(ohl_r{p}), "
                    f".o_iv_b(x{p}_iv_b), .o_iv_f(x{p}_iv_f), .o_ifirst(x{p}_ifirst), .o_ilast(x{p}_ilast), .o_ifp4(x{p}_ifp4), "
                    f".o_itag(x{p}_itag), .o_iw(x{p}_iw), .o_ix(x{p}_ix), .o_ifirst_e(x{p}_ifirst_e), .o_ilast_e(x{p}_ilast_e), "
                    f".o_itag_e(x{p}_itag_e));")
        self.I("x", f"ot_rp5_xq u_xq{p} (.clk(clk), .rst_n({self.R('x', dX)}), .at({at}_x), .x_iv_b(x{p}_iv_b), .x_iv_f(x{p}_iv_f), "
                    f".x_ifirst(x{p}_ifirst), .x_ilast(x{p}_ilast), .x_ifp4(x{p}_ifp4), .x_itag(x{p}_itag), .x_iw(x{p}_iw), "
                    f".x_ix(x{p}_ix), .x_ifirst_e(x{p}_ifirst_e), .x_ilast_e(x{p}_ilast_e), .x_itag_e(x{p}_itag_e), "
                    f".bb(bb{p}), .fb(fb{p}), .pp(pp{p}), .pf(pf{p}));")
        # c: block-dot column, BF16 column halves, QK tree, PV sum capture, publication line (all from the landed bundles)
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
        self.I("c", f"ot_rp5_pub u_pub{p} (.clk(clk), .rst_n({self.R('c', dC - 1)}), .at({at}_c), .pp(pp{p}), .pub_start(pst{p}), "
                    f".pub_slot(psl{p}), .published_h128(ph{p}));")
        # m (FB: c): fold alignment pad, PV merge, result select
        self.I(M, f"ot_rp5_pad #(.W(7), .N({self.LCM})) u_fp{p} (.clk(clk), .d(pf{p}), .q(pfp{p}));")
        self.I(M, f"ot_rp5_merge u_mg{p} (.clk(clk), .rst_n({self.R(M, dM)}), .ev(ev{p}), .sum(es{p}), .tag_d(et{p}), "
                  f".pub_start(pst{p}), .pub_slot(psl{p}), .fold_start(pfp{p}[6]), .fold_a(pfp{p}[5:3]), .fold_b(pfp{p}[2:0]), "
                  f".pub_v(pv{p}), .pub_data(pd{p}), .pub_word(pw{p}), .pub_out_slot(pos{p}), .pub_tag(ptg{p}), .fault(mf{p}));")
        self.I(M, f"ot_rp5_go u_go{p} (.clk(clk), .rst_n({self.R(M, dM)}), .at({at}_{M}), .bov(bov{p}), .by(by{p}), .bt(bt{p}), "
                  f".bfault(bf{p}), .fov(fov{p}), .fy(fy{p}), .ft(ft{p}), .qf(qf{p}), .mf(mf{p}), .ps_v(pv{p}), .ps_data(pd{p}), "
                  f".ps_word(pw{p}), .ps_slot(pos{p}), .published_h128(ph{p}), .g(g{p}));")
        return f"g{p}"

    # ------------------------------------------------------------------------------------------------------- halves
    def build_n(self):
        M = self.M
        self.ports = ["input wire clk", "input wire rst_n",
                      "input wire [8:0] xs_a1", "input wire [4:0] xs_g1", "input wire [6:0] xs_a2", "input wire [4:0] xs_g2",
                      "input wire [4:0] attn", "input wire [817:0] rin_n", "input wire [2068:0] bin", "input wire [99:0] gin",
                      "output wire [817:0] rout_n", "output wire [2068:0] bout",
                      "output wire [2068:0] xo_b", "output wire [49:0] xo_g0", "output wire [99:0] xo_gp"]
        for w in ["wire [25:0] st_n;", "wire [817:0] rl_n, rl1_n, rpm_n;",
                  "wire [2068:0] bin_l, bt1, bm, be1, bk1_n, xb1, xb2;", "wire [99:0] gin_a, gin_r, gpm, gpr;",
                  "wire [49:0] g0m, g0r;"]:
            self.W(w)
        self.I("x", "ot_rp4l_strap u_sr_n (.clk(clk), .d({xs_g2, xs_a2, xs_g1, xs_a1}), .q(st_n));")
        self.straps("(HMUT == 5) ? {attn[4:3] + 2'd1, attn[2:0]} : attn")
        self.I("c", f"ot_rp4l_pinrow u_pr_n (.clk(clk), .rst_n({self.R('c', 3)}), .d(rin_n), .q(rl_n));")
        self.I("x", f"ot_rp4l_pinbeat u_pb (.clk(clk), .rst_n({self.R('x', 3)}), .d(bin), .q(bin_l));")
        self.I("c", f"ot_smh_tr_group_row_w u_row0 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rl_n), .first(rl1_n), .last(rpm_n));")
        for nm, d, q in (("u_bt1", "bin_l", "bt1"), ("u_bt2", "bt1", "bm"), ("u_be1", "bm", "be1"), ("u_be2", "be1", "bout"),
                         ("u_landn", "bin_l", "bk1_n"), ("u_xb1", "bin_l", "xb1")):
            self.I("x", f"ot_rp4h_xreg #(.W(2069), .VMASK({V2})) {nm} (.clk(clk), .rst_n({self.R('x', 3)}), .d({d}), .q({q}));")
        self.I("c", f"ot_smh_tr_group_row_e u_rowe0 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rpm_n), .last(rout_n));")
        # leaf 0: rl1 lands c -> x straight into the x store (the 2 LR relays become the landing: +1); bk1 / ohl / st +1 relay
        g0 = self.leaf(0, "st_n", "at", "rl1_n", "bk1_n", None, 3, 3, 6)
        # gin: 2 x stages (N face, then toward the x/m seam) + land x -> m + tauM pads: +1 + tauM (= g0's shift) vs r3
        self.I("x", f"ot_rp4a_relay #(.W(100), .N(2), .VMASK({V100})) u_gi1 (.clk(clk), .rst_n({self.R('x', 3)}), .d(gin), .q(gin_a));")
        self.I(M, f"ot_rp4a_relay #(.W(100), .N({self.tauM}), .VMASK({V100})) u_gi2 (.clk(clk), .rst_n({self.R(M, 3)}), .d(gin_a), .q(gin_r));")
        self.I(M, f"ot_rp4l_gn u_gn (.clk(clk), .rst_n({self.R(M, 3 + SIGMA + self.tauM)}), .g0({g0}), .gin(gin_r), .g0m(g0m), .gpm(gpm));")
        # xb crossing: xb1, xb2 (x, W channel) + land x -> m + the S-face out register (bin -> xo_b 6 edges, r3 5)
        self.I("x", f"ot_rp4a_relay #(.W(2069), .N((HMUT == 1) ? 0 : 1), .VMASK({V2})) u_xb2 (.clk(clk), .rst_n({self.R('x', 3)}), .d(xb1), .q(xb2));")
        self.I(M, f"ot_rp4h_xreg #(.W(2069), .VMASK({V2})) u_xbo (.clk(clk), .rst_n({self.R(M, 3)}), .d(xb2), .q(xo_b));")
        self.I(M, f"ot_rp4a_relay #(.W(50), .N(2), .VMASK({V50})) u_xgr (.clk(clk), .rst_n({self.R(M, 3)}), .d(g0m), .q(g0r));")
        self.I(M, f"ot_rp4a_relay #(.W(100), .N(2), .VMASK({V100})) u_xpr (.clk(clk), .rst_n({self.R(M, 3)}), .d(gpm), .q(gpr));")
        self.I(M, f"ot_rp4h_xreg #(.W(50), .VMASK({V50})) u_xgo (.clk(clk), .rst_n({self.R(M, 3)}), .d(g0r), .q(xo_g0));")
        self.I(M, f"ot_rp4h_xreg #(.W(100), .VMASK({V100})) u_xpo (.clk(clk), .rst_n({self.R(M, 3)}), .d(gpr), .q(xo_gp));")
        self.static = ["attn"]

    def build_s(self):
        M = self.M
        self.ports = ["input wire clk", "input wire rst_n",
                      "input wire [8:0] xss_a1", "input wire [4:0] xss_g1", "input wire [6:0] xss_a2", "input wire [4:0] xss_g2",
                      "input wire [4:0] attn", "input wire [817:0] rin_s", "output wire [817:0] rout_s",
                      "input wire [2068:0] xi_b", "input wire [49:0] xi_g0", "input wire [99:0] xi_gp", "output wire [199:0] gout"]
        for w in ["wire [25:0] st_s, st_p;", "wire [817:0] rl_s, rl1_s, rl1_p, rpm_s;",
                  "wire [2068:0] bk1_s;", "wire [49:0] xg, xg2o, g1p;", "wire [99:0] xp, xp2;"]:
            self.W(w)
        # x: N-face bk1 landing register and the gather-lane entry (xgi, xg2 / xpi, xp2) beside the x store
        self.I("x", f"ot_rp4h_xreg #(.W(2069), .VMASK({V2})) u_lands (.clk(clk), .rst_n({self.R('x', 8 + 1)}), .d(xi_b), .q(bk1_s));")
        self.I("x", f"ot_rp4h_xreg #(.W(50), .VMASK({V50})) u_xgi (.clk(clk), .rst_n({self.R('x', 3)}), .d(xi_g0), .q(xg));")
        self.I("x", f"ot_rp4a_relay #(.W(50), .N(1), .VMASK({V50})) u_xg2 (.clk(clk), .rst_n({self.R('x', 3)}), .d(xg), .q(xg2o));")
        self.I("x", f"ot_rp4h_xreg #(.W(100), .VMASK({V100})) u_xpi (.clk(clk), .rst_n({self.R('x', 3)}), .d(xi_gp), .q(xp));")
        self.I("x", f"ot_rp4a_relay #(.W(100), .N((HMUT == 2) ? 0 : 1), .VMASK({V100})) u_xp2 (.clk(clk), .rst_n({self.R('x', 3)}), .d(xp), .q(xp2));")
        # S-face straps (MAIN: m region; FB: c)
        self.I(M, "ot_rp4l_strap u_sr_s (.clk(clk), .d({xss_g2, xss_a2, xss_g1, xss_a1}), .q(st_s));")
        self.straps("{attn[4:3] + 2'd1, attn[2:0]}")
        self.I("c", f"ot_rp4l_pinrow u_pr_s (.clk(clk), .rst_n({self.R('c', 3)}), .d(rin_s), .q(rl_s));")
        self.I("c", f"ot_smh_tr_group_row_w u_row1 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rl_s), .first(rl1_s), .last(rpm_s));")
        self.I("c", f"ot_smh_tr_group_row_e u_rowe1 (.clk(clk), .rst_a({self.R('c', 3)}), .d(rpm_s), .last(rout_s));")
        # rl1: pad 3 (c) + land c -> x + LR 2 relays (x) = 8 = r3 7 + delta_b; straps: MAIN land m->c, pad 1, land c->x, relay 1
        self.I("c", "ot_rp5_pad #(.W(818), .N((HMUT == 3) ? 2 : 3)) u_prl (.clk(clk), .d(rl1_s), .q(rl1_p));")
        self.I("c", f"ot_rp5_pad #(.W(26), .N({1 if self.v == 'm' else 3})) u_pst (.clk(clk), .d(st_s), .q(st_p));")
        g1 = self.leaf(1, "st_p", "at", "rl1_p", "bk1_s", "(HMUT == 6) ? 1 : 2", 1 if self.v == "m" else 2, 2, 11)
        gs_d = 8 + SIGMA + self.tauM + 1     # r_gs r3 depth 8 + gout shift
        self.I(M, f"ot_rp4a_relay #(.W(50), .N(3), .VMASK({V50})) u_g1p (.clk(clk), .rst_n({self.R(M, gs_d)}), .d({g1}), .q(g1p));")
        self.I(M, f"ot_rp4l_gs u_gs (.clk(clk), .rst_n({self.R(M, gs_d)}), .g1in(g1p), .g0m(xg2o), .gpm(xp2), .gout(gout));")
        self.static = ["attn"]

    def write(self):
        (self.build_n if self.h == "n" else self.build_s)()
        rst = self.emit_rst()
        top = f"ot_hbm_smh_rp5{self.h}_{self.v}_flat"
        L = ["`timescale 1ns/1ps",
             f"// GENERATED by tools/hbm_sm_repack_1015/rp5_gen.py (HBM-OWN/SMH2 r5, {'MAIN 3 regions x/c/m' if self.v == 'm' else 'FB 2 regions x/c'}):",
             f"// wires-only flat parent of the regional {self.h} half (single clk; lp.py lands it).  RB {self.RB} (lp regional reset run).",
             f"// Region of each child in the lp spec results/arch/hbm_smh_r5_1021/lp_spec_{self.h}_{self.v}.json.  HMUT: bench mutants (0 in kits).",
             f"module {top} #(parameter integer HMUT = 0) (", "    " + ",\n    ".join(self.ports), ");"]
        L += ["    " + w for w in self.wires]
        for r, t in rst + self.insts:
            L.append(f"    {t}")
        L.append("endmodule")
        (ROOT / RTL / f"{top}.sv").write_text("\n".join(L) + "\n")
        # region membership from the instance names
        names = {}
        import re
        for r, t in rst + self.insts:
            m = re.search(r"\)\s*(u_\w+)\s*\(|^\w+\s+(u_\w+)\s*\(", t)
            nm = m.group(1) or m.group(2)
            names.setdefault(r, []).append(nm)
        c = CENTRES[self.h]
        spec = dict(
            top=top, top_lp=f"ot_hbm_smh_rp5{self.h}_{self.v}",
            why=(f"HBM-OWN/SMH2 10-21 r5 {self.h} half {'MAIN' if self.v == 'm' else 'FB'}: per-register-mass regional roots, "
                 "every region crossing a 4-slot landing (reschedule: the latency shifts are priced in rp5_gen.py)"),
            sources=[f"{RTL}/{top}.sv"], child_sources=CHILD_SOURCES, defines=DEFINES,
            out_dir=f"{RTL}/lp_{self.h}_{self.v}", record_dir=REC,
            clock_ports=["clk"], clock_pins=["clk"], reset_port="rst_n", reset_pins=["rst_n", "rst_a"],
            regions=[dict(name=r, insts=sorted(names.get(r, [])), centre=c[r]) for r in self.regions],
            reset_region="c", static=self.static, D=4, E=2, reschedule=True, landing_chunk_bits=24,
            landing_reset_forest=True,
            bench=dict(cycles=3000, reset_cycles=16, sim="verilator"),
            tb_static={"attn": "5'd13"},
            mut_child=f"u_rst_c{(6 if self.h == 'n' else 11) + SIGMA + 3 - 1}",   # the publication line's reset (stateful)
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
