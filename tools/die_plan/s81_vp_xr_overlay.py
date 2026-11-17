"""S81 strip form B (COORD 11-16 r4xx, VP family CTS class): VP write-port input stage XR, opt-in per leaf.

The strip leaf CTS reads (t28/t34/t47/t62/t75, -548..-3956 ps) all fail on ot_s81sl_vpw (WRP=1): it decodes the RAW
writer pins (x_wv/x_wa/x_wm from vs through cst_vsp at depth 0, sw_*/cw_* from the leafdn pad, hs_*) into its flops, and
the placer puts vpw among the lanes, far from the writers.  XR = 1 adds ONE register stage on every vpw input together
(all writers and their payloads, xwd included), so the write port lands exactly one clk later for every writer: store
order, writer priority and collision (wcol) behaviour are unchanged; vpw(XR=1)(t) == vpw(XR=0)(t-1).  XR also adds one
per-lane HI station (effective CS_HI_D + 1; shared depth unchanged; every derived vp timeline uses the effective depth)
and one VP reset relay stage (TREE_STAGES 1 -> 2).  With XR the dswp row-swap select of the hw_d / wl_d / lo_d output
registers is also 16 kept flop copies (DSR, 0 cycles; t62 dswp -> hw_d -548 ps at CTS).  XR = 0 is the source exactly
(no cycle, no cell).

Optional --lane-reset-copies (off by default): XR leaves use16 independent, same-depth kept reset outputs for
their lane HI/core/HO reset pins. This replaces the single rs_p fanout; +32 relay FF at TREE_STAGES2, no further
boot or data cycles. Physical placement and production-shape timing remain required.

Optional --cfr-with-xr (off by default): selected XR leaves also use the existing registered CFR coefficient-row
decode. It is cycle-exact, adds five RTL state bits and no further operation cycles, and preserves explicit legacy
CFR bits on unselected leaves. Production-shape timing is still required.

Latency contract (S81-DIE-R2 bind + LATCHECK): vp write availability +1 clk (SU x_w and sw/cw writes), hc_post
write-back +1 clk, VP boot reset release +1 edge; vp read port latency unchanged.

  python3 -I s81_vp_xr_overlay.py ROOT [--die PART=MASK ...]
ROOT = an S81 elaboration source tree that already carries the WRP overlay (module ot_s81sl_vpw).  Every file is edited
by exact, counted replacements (refuses on any miss) and is written by unlink + write (never through a link into a
shared tree).  --die sets .LF_VP_XR(5'bMASK) on die instance u_s_PART in die_b178.v and die_b178_lfcs.v
(e.g. --die 3S=01000 --die 6N=00010 = leaf__t34 (s_3S L3) and leaf__t62 (s_6N L1)).
"""
import argparse
import re
import sys
from pathlib import Path

VP = "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv"
SLICE_DIRS = ("rtl/dsrom_sys/s81_dv/slice", "physical/die_plan/s81/bind/source_modules")
DIES = ("physical/die_plan/s81/bind/inputs/die_b178.v", "physical/die_plan/s81/bind/inputs/die_b178_lfcs.v")
WRITERS = [("sw_v", 1), ("sw_a", 10), ("sw_m", 8), ("sw_d", 256), ("cw_v", 2), ("cw_a", 24), ("cw_d", 64),
           ("x_wv", 1), ("x_wa", 10), ("x_wm", 8), ("xwd", 256), ("hs_v", 1), ("hs_a", 10), ("hs_d", 256)]
VALIDS = {"sw_v", "cw_v", "x_wv", "hs_v"}
TAG = "S81-STRIP-XR"


def write(p, s):
    if p.is_symlink() or p.stat().st_nlink > 1:
        p.unlink()
    p.write_text(s)


def sub_exact(s, a, b, n, what):
    c = s.count(a)
    if c != n:
        raise SystemExit(f"XR_OVERLAY_MISS {what}: expected {n} x {a[:80]!r}, found {c}")
    return s.replace(a, b)


def patch_vp(s, lane_reset_copies=False):
    if TAG in s:
        raise SystemExit("XR_OVERLAY_TWICE ot_s81sl_vp.sv already carries XR")
    if "module ot_s81sl_vpw" not in s:
        raise SystemExit("XR_OVERLAY_NO_WRP ot_s81sl_vpw missing: apply the WRP overlay first")
    s = sub_exact(s, "module ot_s81sl_vp #(\n", f"`ifdef OT_S81SL_VP_XR\n`define OT_S81SL_VP_XR_DEFAULT 1\n`else\n"
                  f"`define OT_S81SL_VP_XR_DEFAULT 0\n`endif\n// {TAG}: XR = write-port input stage (see ot_s81sl_vpw)\n"
                  "module ot_s81sl_vp #(\n", 1, "vp header")
    s = sub_exact(s, "    parameter integer ML = 7,", "    parameter integer XR = `OT_S81SL_VP_XR_DEFAULT,\n"
                  "    parameter integer ML = 7,", 1, "vp XR param")
    s = sub_exact(s, "    wire [3:0] rsv;", "    // XR: one more local HI stage per lane and one more reset relay stage.\n"
                  "    localparam integer CS_HI_E = CS_HI_D + XR;\n    wire [3:0] rsv;", 1, "vp CS_HI_E")
    s = sub_exact(s, ".TREE_STAGES(1)) u_rr", ".TREE_STAGES(1 + XR)) u_rr", 1, "vp u_rr")
    n = s.count(".D(CS_HI_D - CS_HI_GS + HIM)")
    if n < 1:
        raise SystemExit("XR_OVERLAY_MISS per-lane HI station .D(CS_HI_D - CS_HI_GS + HIM)")
    s = s.replace(".D(CS_HI_D - CS_HI_GS + HIM)", ".D(CS_HI_E - CS_HI_GS + HIM)")
    m = 0
    for a in ("HPL + HQX + CS_HI_D + CS_HO_D + SRO", "HPL + CS_HI_D + CS_HO_D + SRO"):
        m += s.count(a)
        s = s.replace(a, a.replace("CS_HI_D", "CS_HI_E"))
    if m < 1:
        raise SystemExit("XR_OVERLAY_MISS hc_post timeline HPL + .. CS_HI_D + CS_HO_D + SRO")
    s = sub_exact(s, "    wire [127:0] qe = dswp ? q1 : q0, qo = dswp ? q0 : q1;",
                  f"    // {TAG} DSR (FABLE-PD-S81-STRIP fix 3, t62 dswp -> hw_d -548 ps): dswp selects all 3 x 256 output\n"
                  "    // register bits (hw_d / wl_d / lo_d).  With XR the select is DSR kept copies of the dswp flop, one per\n"
                  "    // 128 / DSR bits of qe / qo, loaded from dswp1 like dswp itself: dswp_q[g](t) == dswp(t), cycle-exact.\n"
                  "    localparam integer DSR = (XR != 0) ? 16 : 1;\n"
                  "    wire [127:0] qe, qo;\n"
                  "    generate if (DSR > 1) begin : g_dsr\n"
                  "        (* keep *) reg [DSR-1:0] dswp_q;\n"
                  "        always @(posedge clk) dswp_q <= {DSR{dswp1}};\n"
                  "        for (genvar g = 0; g < DSR; g = g + 1) begin : g_g\n"
                  "            assign qe[g * (128 / DSR) +: 128 / DSR] = dswp_q[g] ? q1[g * (128 / DSR) +: 128 / DSR] : q0[g * (128 / DSR) +: 128 / DSR];\n"
                  "            assign qo[g * (128 / DSR) +: 128 / DSR] = dswp_q[g] ? q0[g * (128 / DSR) +: 128 / DSR] : q1[g * (128 / DSR) +: 128 / DSR];\n"
                  "        end\n"
                  "    end else begin : g_ndsr\n"
                  "        assign qe = dswp ? q1 : q0; assign qo = dswp ? q0 : q1;\n"
                  "    end endgenerate", 1, "vp dswp select")
    s = sub_exact(s, "ot_s81sl_vpw u_w (", "ot_s81sl_vpw #(.XR(XR)) u_w (", 1, "vpw instance")
    s = sub_exact(s, "module ot_s81sl_vpw #(parameter integer REP = 8)",
                  "module ot_s81sl_vpw #(parameter integer REP = 8, parameter integer XR = 0)", 1, "vpw header")
    start = s.index("    localparam integer SL = 128 / REP;", s.index("module ot_s81sl_vpw"))
    end = s.index("endmodule", start)
    body = s[start:end]
    for name, _ in WRITERS:
        body = re.sub(r"\b" + name + r"\b", name + "_i", body)
    d = [f"    // {TAG}: XR adds exactly one edge to every writer and its payload (priorities and collisions unchanged)."]
    d += [f"    wire [{w - 1}:0] {n}_i;" for n, w in WRITERS]
    d += ["    generate if (XR != 0) begin : g_xr"]
    for n, w in WRITERS:
        d.append(f"        reg [{w - 1}:0] {n}_q;")
        if n in VALIDS:
            d.append(f"        always @(posedge clk or negedge rst_n) if (!rst_n) {n}_q <= {w}'d0; else {n}_q <= {n};")
        else:
            d.append(f"        always @(posedge clk) {n}_q <= {n};")
        d.append(f"        assign {n}_i = {n}_q;")
    d += ["    end else begin : g_nxr"] + [f"        assign {n}_i = {n};" for n, _ in WRITERS]
    d += ["    end endgenerate", ""]
    s = s[:start] + "\n".join(d) + body + s[end:]
    if lane_reset_copies:
        # The corrected t75 placement still has40 VP-reset endpoints below-42ps.
        # A second tree stage alone retains one rs_p driver for all16 lanes.
        # Copies at the same depth remove that fanout without another boot edge.
        s = sub_exact(s, "    wire [3:0] rsv;",
                      "    localparam integer RREG = (XR != 0) ? 20 : 4;\n"
                      "    wire [RREG-1:0] rsv;", 1, "per-lane reset regions")
        s = sub_exact(s, ".REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1 + XR)) u_rr",
                      ".REGIONS(RREG), .SYNC_STAGES(2), .TREE_STAGES(1 + XR)) u_rr", 1, "per-lane reset tree")
        rs = "    wire rs_c = rsv[0], rs_s = rsv[1], rs_p = rsv[2], rs_o = rsv[3];"
        s = sub_exact(s, rs, rs + "\n    // Same reset edge as rs_p, one kept driver per lane at XR1.\n"
                      "    wire [15:0] rs_ln;\n"
                      "    generate if (XR != 0) begin : g_lane_reset\n"
                      "        assign rs_ln = rsv[19:4];\n"
                      "    end else begin : g_common_reset\n"
                      "        assign rs_ln = {16{rs_p}};\n"
                      "    end endgenerate", 1, "lane reset wires")
        a = s.index("    generate for (gl = 0; gl < 16; gl = gl + 1) begin : g_ln")
        b = s.index("    // the h half row of POST step", a)
        segment = sub_exact(s[a:b], ".rst_n(rs_p)", ".rst_n(rs_ln[gl])", 4, "lane HI/core/HO reset pins")
        s = s[:a] + segment + s[b:]
    return s


HI_HDR = re.compile(r"parameter \[19:0\] LF_CS_HI_D = ")
HI_FWD = ".LF_CS_HI_D(LF_CS_HI_D)"
LEAF_HI = re.compile(r"\.CS_HI_D\(LF_CS_HI_D\[4 \* (\w+) \+: 4\]\)")


def patch_slice(s, f, cfr_with_xr=False):
    """Leaf: VP_XR -> u_vp.XR.  Every slice wrapper that declares LF_CS_HI_D declares LF_VP_XR; every forward of
    LF_CS_HI_D forwards LF_VP_XR; every leaf taking CS_HI_D from LF_CS_HI_D[4*k] takes VP_XR from LF_VP_XR[k]."""
    n = 0
    if "module ot_s81sl_leaf #(\n" in s:
        s = sub_exact(s, "module ot_s81sl_leaf #(\n", "module ot_s81sl_leaf #(\n    parameter integer VP_XR = 0,  // "
                      f"{TAG}: u_vp.XR (+1 write availability, +1 hc_post, +1 boot reset edge)\n", 1, f"{f} leaf hdr")
        s = sub_exact(s, "ot_s81sl_vp #(.CS_HI_D", "ot_s81sl_vp #(.XR(VP_XR), .CS_HI_D", 1, f"{f} leaf u_vp")
        if cfr_with_xr:
            # Use the existing, cycle-exact registered coefficient row decode
            # on selected XR leaves; preserve every explicit legacy CFR bit.
            s = sub_exact(s, ".CFR(VP_CFR)", ".CFR(VP_CFR || VP_XR)", 1, f"{f} CFR with XR")
        n += 2
    k = len(HI_HDR.findall(s))
    s = HI_HDR.sub("parameter [4:0] LF_VP_XR = 5'd0, parameter [19:0] LF_CS_HI_D = ", s)
    k2 = s.count(HI_FWD)
    s = s.replace(HI_FWD, ".LF_VP_XR(LF_VP_XR), " + HI_FWD)
    k3 = len(LEAF_HI.findall(s))
    s = LEAF_HI.sub(lambda m: f".VP_XR(LF_VP_XR[{m.group(1)}]), " + m.group(0), s)
    return s, n + k + k2 + k3, (k, k2, k3)


def die_mask(s, part, mask, f):
    """One die slice instance u_s_PART, with or without a parameter list on its line."""
    pat = re.compile(rf"^(\s*ot_s81sl_slice\w*)(\s+#\((.*?)\))?(\s+u_s_{part}\s*\()", re.M)
    hits = pat.findall(s)
    if len(hits) != 1:
        raise SystemExit(f"XR_DIE_MISS {f}: u_s_{part} instances {len(hits)}")
    if "LF_VP_XR" in hits[0][2]:
        raise SystemExit(f"XR_DIE_TWICE {f}: u_s_{part} already sets LF_VP_XR")

    def rep(m):
        if m.group(2):
            return f"{m.group(1)} #(.LF_VP_XR(5'b{mask}), {m.group(3)}){m.group(4)}"
        return f"{m.group(1)} #(.LF_VP_XR(5'b{mask})){m.group(4)}"
    return pat.sub(rep, s)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--die", action="append", default=[], metavar="PART=MASK")
    ap.add_argument("--lane-reset-copies", action="store_true",
                    help="XR leaves use16 same-depth local lane reset copies; +32 FF vs XR, no extra cycles")
    ap.add_argument("--cfr-with-xr", action="store_true",
                    help="XR leaves enable the existing cycle-exact CFR coefficient row decode")
    a = ap.parse_args(argv)
    root = Path(a.root)
    out = {}                                          # every edit is computed first; nothing is written on a miss
    vp = root / VP
    out[vp] = (patch_vp(vp.read_text(), a.lane_reset_copies), "vp")
    leaf_seen = 0
    for d in SLICE_DIRS:
        for f in sorted((root / d).rglob("*.sv")):
            if "/test/" in str(f):
                continue
            s = f.read_text(errors="replace")
            if "LF_CS_HI_D" not in s and "module ot_s81sl_leaf #(" not in s:
                continue
            t, n, ks = patch_slice(s, f, a.cfr_with_xr)
            if n:
                out[f] = (t, f"hdr/fwd/leaf {ks}")
                leaf_seen += "module ot_s81sl_leaf #(" in s
    if not leaf_seen:
        raise SystemExit("XR_OVERLAY_MISS module ot_s81sl_leaf not found under the slice dirs")
    for rel in DIES:
        p = root / rel
        if not p.is_file() or not a.die:
            continue
        s = p.read_text()
        for spec in a.die:
            part, mask = spec.split("=")
            if not re.fullmatch(r"[01]{5}", mask):
                raise SystemExit(f"XR_DIE_BAD_MASK {spec}")
            s = die_mask(s, part, mask, rel)
        out[p] = (s, "die " + " ".join(a.die))
    for p, (s, what) in out.items():
        write(p, s)
        print("ok", p.relative_to(root), what)
    return 0


if __name__ == "__main__":
    sys.exit(main())
