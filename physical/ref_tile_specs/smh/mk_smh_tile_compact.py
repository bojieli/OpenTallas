#!/usr/bin/env python3
"""el1014 H-ELEM-A (owner 18:45 PT 10-14, SM compact-first): the SM tile cluster WITHOUT the pt_w / pt_e
pass-through band.  Derived from mk_smh_tile_cluster.py (r16 smh_tile_eg_ref, unchanged there).

The 3,705-bit E-W transport (rin / bin -> rout / bout, four transit edges, first-edge landing to both leaves, valid /
x_ce reset masks, per-slice ot_rst_relay) is the Codex compact transport 3a1283ed5 (OT_SMH_COMPACT_PT,
rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv: 96 register slices of <= 128 bits), synthesised as tile-parent cells in
a channel between the two leaves instead of two hard frames.  The ten closed leaf views (2 x {xs, bdc, tct, 2 tcl}) and
their positions inside each leaf half are unchanged.

Channel height (xs1 top -> xs0 bottom), from arithmetic before any run:
  pins   : 3,705 rin / bin bits on the W face (rout / bout at the same y on E) on M4 (2-track 0.096 um, 10.42 / um) AND
           M6 (2-track 0.128 um, 7.81 / um) = 18.23 / um -> 203.3 um of face (pin_density 10.4 / 7.8 < 12 per layer)
  H cut  : 3,705 transit wires across every vertical cut; GRT H supply 22 tracks per 0.57-um gcell (38.6 / um, the r16
           smh_xb_cut.py figure) -> 3,705 / (38.6 x 0.55) = 174.5 um at cut 0.55
  cells  : transport ~19.0k DFF (+3,705 pin registers already in the tile) ~7.9k um2 cells: ~5 % of a 630 x 231 channel
  => channel 216 um target, on the 43.2 lattice 231.12 um (old: 58 + 371.52 band + 60 = 490.32 um)
Tile 630.72 x 993.6 (was 630.72 x 1,252.8).  Stations (straps, reset tree, g lanes) keep their leaf-relative positions:
above the channel they move down with leaf 0, inside it they scale with the channel (ymap).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
L = 43.2
import math
import os
XS_KIT = os.environ.get("SMT_XS_KIT", "smh_xs_ref_p45m")   # accepted mirror-safe p45m r3 view
V = "physical/ref_tile/{}/views/{}"
VIEWS = {"xs": V.format(XS_KIT, "ot_hbm_accel_smh_xs"),
         "bdc": V.format("smh_bdc_ref_p50", "ot_hbm_accel_smh_bdc"),
         "tcl": V.format("smh_tcl_ref_p45", "ot_hbm_accel_smh_tcl"),
         "tct": V.format("smh_tct_ref_p45", "ot_hbm_accel_smh_tct")}


def lef_size(view):
    t = (ROOT / view / f"{Path(view).name}.lef").read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    return float(m.group(1)), float(m.group(2))


DIM = {k: lef_size(v) for k, v in VIEWS.items()}
up = lambda v: round(math.ceil(round(v / L, 6)) * L, 3)       # next origin on the child lattice
# W column bottom-up: bdc1 / xs1 / pt band / xs0 / bdc0; landing channels (xs <-> pt_w) >= 55 um (cut <= 0.6), others >= 20
Y_BDC1 = 43.2
Y_XS1 = up(Y_BDC1 + DIM["bdc"][1] + 20.0)
# compact: the band and its two landing channels are replaced by one transport channel (see header)
HC = float(os.environ.get("SMC_CHANNEL_UM", "216"))
Y_CH0 = round(Y_XS1 + DIM["xs"][1], 3)                    # xs1 top = channel bottom
Y_XS0 = up(Y_CH0 + HC)
# r16 geometry the stations were placed against (old channel = xs1 top .. xs0 bottom)
OLD_CH0, OLD_CH1 = 373.68, 864.0
def ymap(y):
    """r16 station y -> compact y: below the old channel unchanged, above it shifted with leaf 0, inside scaled"""
    if y <= OLD_CH0:
        return y
    if y >= OLD_CH1:
        return round(y - (OLD_CH1 - Y_XS0), 3)
    return round(Y_CH0 + (y - OLD_CH0) * (Y_XS0 - Y_CH0) / (OLD_CH1 - OLD_CH0), 3)
Y_BDC0 = up(Y_XS0 + DIM["xs"][1] + 20.0)
W = 630.72
CH_X = 367.2      # eg: centre of the free N-S channel between the W column (ends 345.6) and the E column (starts 388.8)
H = round(math.ceil((Y_BDC0 + DIM["bdc"][1] + 22.16) / 8.64 - 1e-9) * 8.64, 3)
# eg (R0 leaf 0 above the band, MX leaf 1 below): (kind, instance glob, x, y, orient); E column relative to the band
EG = [("xs", "*g_lf?0?.u_lh.u_xs", 43.2, Y_XS0, "R0"), ("bdc", "*g_lf?0?.u_lh.u_bdc", 129.6, Y_BDC0, "R0"),
      ("tct", "*g_lf?0?.u_lh.u_tcc.u_tr", 388.8, Y_XS0, "R0"),
      ("tcl", "*g_lf?0?.u_lh.u_tcc.u_h0", 388.8, round(Y_XS0 + 129.6, 3), "R0"),
      ("tcl", "*g_lf?0?.u_lh.u_tcc.u_h1", 518.4, round(Y_XS0 + 129.6, 3), "R0"),
      ("xs", "*g_lf?1?.u_lh.u_xs", 43.2, Y_XS1, "MX"), ("bdc", "*g_lf?1?.u_lh.u_bdc", 129.6, Y_BDC1, "MX"),
      ("tct", "*g_lf?1?.u_lh.u_tcc.u_tr", 388.8, 129.6, "R0"),
      ("tcl", "*g_lf?1?.u_lh.u_tcc.u_h0", 388.8, 259.2, "R0"),
      ("tcl", "*g_lf?1?.u_lh.u_tcc.u_h1", 518.4, 259.2, "R0")]
MYO = {"R0": "MY", "MX": "R180"}
DEFINES = ["OT_SMH_CG_ENREG", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY", "OT_SMH_RSTPIN", "OT_SMH_HIER",
           "OT_SMH_PTW_OHDLY", "OT_SMH_PINREG", "OT_SMH_XREL", "OT_SMH_PRODUCTION_SHAPE", "OT_SMH_COMPACT_PT"]
BDEF = " ".join(f"--define {d}" for d in DEFINES)
BENCH = ("W=$(mktemp -d /tmp/smtb.XXXXXX); python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 8 --rmax 4096 --req-credit --smh --cg " + BDEF +
         " {mut}--cg-gap 300 --build-jobs 8 --workdir $W --out {{RUN}}/b_{n}.json > {{RUN}}/b_{n}.log 2>&1; rc=$?; "
         "cat {{RUN}}/b_{n}.log | tail -5; grep -h CG_LOCKSTEP $W/*/runtime.log; {tail}")
BENCHES = [
    {"name": "lockstep_enreg_xlk", "expect": "pass", "pass_regex": "SMT_LOCKSTEP_PASS", "threads": 8, "peak_ram_gb": 72,
     "cmd": BENCH.format(n="lockstep_enreg_xlk", mut="", tail=(
         "test $rc -eq 0 && grep -q 'CG_LOCKSTEP mismatches 0 ' $W/*/runtime.log && echo SMT_LOCKSTEP_PASS"))},
    {"name": "mut_late32", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 72,
     "cmd": BENCH.format(n="mut_late32", mut="--cg-mut-late ", tail=(
         "test $rc -eq 0 && ! grep -q 'CG_LOCKSTEP mismatches [1-9]' $W/*/runtime.log"))},
    {"name": "mut_hold0", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 72,
     "cmd": BENCH.format(n="mut_hold0", mut="--cg-mut-hold0 ", tail=(
         "test $rc -eq 0 && ! grep -q 'CG_LOCKSTEP mismatches [1-9]' $W/*/runtime.log"))}]


def bits(n, k):
    return [f"{n}[{i}]" for i in range(k)]


def face_slots(n):
    """n W/E face pin slots centred on the transport channel: every 2nd M4 track (0.096 um) and every 2nd M6 track
    (0.128 um), merged in y order; returns [(layer, y)] bottom-up"""
    yc = (Y_CH0 + Y_XS0) / 2
    span = n / (1 / 0.096 + 1 / 0.128) / 2 + 1.0
    while True:
        lo, hi = yc - span, yc + span
        s = [("M4", round(0.012 + 0.096 * k, 3)) for k in range(int(lo / 0.096), int(hi / 0.096) + 2)
             if lo <= 0.012 + 0.096 * k <= hi]
        s += [("M6", round(0.016 + 0.128 * k, 3)) for k in range(int(lo / 0.128), int(hi / 0.128) + 2)
              if lo <= 0.016 + 0.128 * k <= hi]
        if len(s) >= n:
            s.sort(key=lambda e: e[1])
            k0 = (len(s) - n) // 2
            s = s[k0:k0 + n]
            assert Y_CH0 + 2.0 <= s[0][1] and s[-1][1] <= Y_XS0 - 2.0, f"face pins {s[0][1]}-{s[-1][1]} leave the channel"
            return s
        span += 0.5


def io_tcl(variant):
    xin, xout = (0.0, W) if variant == "eg" else (W, 0.0)
    out = ["# generated by physical/ref_tile_specs/smh/mk_smh_tile_compact.py: compact SM tile pin plan (" + variant + ")",
           "# rin/bin on the input face over the transport channel (M4 + M6, 2-track pitch, bottom-up: row 1 = south leaf,",
           "# x-write beat, row 0 = north leaf); rout/bout at the SAME y on the far face (abutment with the next tile)"]
    def pp(n, layer, x, y):
        sz = {"M4": "0.192 0.024", "M5": "0.024 0.192", "M6": "0.256 0.032"}[layer]
        out.append(f"place_pin -pin_name {{{n}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{sz}}} "
                   "-force_to_die_boundary")
    names = [("rin", "rout", i) for i in range(818, 1636)] + [("bin", "bout", i) for i in range(2069)] + \
            [("rin", "rout", i) for i in range(818)]
    for (src, dst, i), (lay, y) in zip(names, face_slots(len(names))):
        pp(f"{src}[{i}]", lay, xin, y)
        pp(f"{dst}[{i}]", lay, xout, y)
    # N face: gin lanes (2 x 50) + straps, then clock / reset / wake over the centre channel; S face: gout lanes (4 x 50);
    # 0.48 um pitch on M5 tracks (0.012 + k * 0.048).  r11 (el1013-smh-r11): (1) gout started at x = 5,568 um (a 48 for
    # 0.048 in the track snap), off the die; (2) gin[i] now sits at the x of gout[i] of the tile above (straight seam);
    # (3) clk / rst_n / cgi / cgo sit over the free N-S centre channel (x 345.6-388.8 in eg), where the tile ICG, the
    # reset pin flop and the spine root go; (4) wg is the MY mirror, so its N / S pins mirror too.
    snap = lambda x: round(0.012 + 0.048 * round((x - 0.012) / 0.048), 3)
    mx = (lambda x: x) if variant == "eg" else (lambda x: W - x)
    def row(names, x0, y, pitch=0.48):
        for i, n in enumerate(names):
            pp(n, "M5", snap(mx(x0 + i * pitch)), y)
    gx0 = snap(W / 2 - 100 * 0.48)
    row(bits("gout", 200), gx0, 0.0)
    nn = bits("gin", 100) + bits("xs_a1", 18) + bits("xs_g1", 10) + bits("xs_a2", 14) + bits("xs_g2", 10)
    row(nn, gx0, H)
    assert gx0 + len(nn) * 0.48 < CH_X - 6
    row(["rst_n", "cgi", "cgo"], CH_X - 4.8, H)
    pp("clk", "M5", snap(mx(CH_X)), H)
    return "\n".join(out) + "\n"


def spec(variant):
    name = f"smh_tile_{variant}_cpt"
    kids = []
    for kind, inst, x, y, o in EG:
        if variant == "wg":
            w = DIM[kind][0]
            x = round(round((W - x - w) / L) * L, 3)
            o = MYO[o]
        kids.append({"view": VIEWS[kind], "count": 1, "at": [x, y], "orient": o, "inst": inst})
    io = f"physical/ref_tile_specs/smh/{name}_pins.tcl"
    (ROOT / io).write_text(io_tcl(variant))
    fin, fout = ("W", "E") if variant == "eg" else ("E", "W")
    src = json.loads((OUT / "smh_pt_w_ref_p45h.json").read_text())["sources"]
    src = src + [f for f in ("rtl/hdc/ot_hdc_cg.sv", "rtl/hbm_accel/cg/ot_cg_tile.sv",
                             "rtl/hbm_accel/sm/ot_hbm_smh_compact_transport.sv") if f not in src]
    return {
        "name": name, "top": f"ot_hbm_accel_smh_tile_{variant}", "kind": "cluster",
        "sources": src, "params": {}, "defines": DEFINES, "clock_port": "clk", "reset_ports": ["rst_n"],
        "spine_through_icg": True,
        "outline": {"w": W, "h": H},
        "children": kids,
        "pins": {fin: ["rin", "bin"], fout: ["rout", "bout"], "S": ["gout"],
                 "N": ["gin", "xs_a1", "xs_g1", "xs_a2", "xs_g2", "clk", "rst_n", "cgi", "cgo"]},
        "io_tcl": io,
        "orfs_vars": {"OT_CG_EXCLUDE": "*u_cgt.u_cg.u_icg", "OT_SPINE_SYM": "1", "OT_SPINE_TREE_PAD": "1", "OT_IO_REF_CLASS": "1", "POST_TAPCELL_TCL": f"physical/ref_tile_specs/smh/{name}_strap_regions.tcl"},
        "refglob": "*",
        # r14: every port's single launch / capture flop FIRM at its own pin through GPL (qwen_die_masters/
        # io_flop_at_pins.tcl; the 3,705 rin / bin landing registers of OT_SMH_PINREG, the gin landings, the gout
        # launches); the wake pin's kept HB4 hold stage (ot_hdly u_hdly_cgi) dont_touch'ed at PRE_FLOORPLAN
        "io_flop_at_pins": {"cols": 6, "allow_none": True},
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 96, "hold_delay": True},
        "job": {"owner": "Claude:H-ELEM-A", "branch": "claude/hbm-smcompact-1014", "tag": "cpt1",
                "structural_change": (
                    "OWNER 18:45 PT 10-14 SM compact-first: the pt_w / pt_e pass-through band (two hard frames, "
                    "0.185 mm2 a tile at 4.9 % / 3.6 % std utilisation, height set by 3,705 M4-only face pins) is "
                    "removed.  Its four transit edges, first-edge landing to both leaves, valid / x_ce reset masks and "
                    "per-slice reset relays are kept as the Codex compact transport 3a1283ed5 (OT_SMH_COMPACT_PT, 96 "
                    "register slices <= 128 bits; exact vs the original module bodies over 4,096 production cycles with "
                    "mid-stream resets, latency mutant FAIL) synthesised as tile-parent cells in a 231.12-um channel "
                    "between the leaves.  Face pins over the channel on M4 + M6 (18.2 / um, 203 um for 3,705 bits); "
                    "H cut 3,705 / (38.6 x 231) = 0.42.  Ten closed leaf views and their leaf-relative placement, RTL "
                    "cycles, benches unchanged; stations keep leaf-relative y (ymap).  Outline 630.72 x 993.6 (was "
                    "x 1,252.8)."),
                "purpose": ("[H-ELEM-A smcompact] ot_hbm_accel_smh_tile_eg WITHOUT the pass-through band (owner 18:45 "
                            "pilot: one tile, measure real area per SM): 10 closed ref_tile leaves (xs p45m, bdc p50, "
                            "tcl p45, tct p45) + tile glue + compact transport cells; spine through the tile ICG, "
                            "rst_n pin flop + registered reset tree, tile pin registers (OT_SMH_PINREG), g-lane / G1 / "
                            "xb / xf / strap stations at leaf-relative positions.  "
                            "production NC8 active8 RMAX4096 TAGW16 native-default lockstep exactness plus strap-offset/late32/hold0 mutants must fail."),
                "benches": BENCHES + [{"name": "mut_strap_region", "expect": "fail",
                "fail_regex": "SMT_STRAP_MUTANT_KILLED", "threads": 8, "peak_ram_gb": 72,
                "cmd": BENCH.format(n="mut_strap_region", mut="--define OT_SMH_MUT_STRAP_REGION ",
                    tail=("python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); "
                          "assert x[\"timeout\"] is None and x[\"mismatching_ops\"] > 0; "
                          "print(\"SMT_STRAP_MUTANT_KILLED\", x[\"mismatching_ops\"])' "
                          "{RUN}/b_mut_strap_region.json; test $rc -eq 0"))} ]},
    }


HALO = 2.16            # ref_tile macro-place halo (rows are cut this far from every child)
SBX, SBY = 8.0, 4.0    # station search window half extents (sr_place)


def child_boxes(variant):
    """(eg x, x0, y0, x1, y1) of every child as PLACED for this variant.  wg children are NOT the die mirror of eg: a
    mirrored origin W - x - w is off the 43.2-um child lattice (W = 14.6 pitches), so spec() snaps it and the whole wg
    image sits 17.28 um east of the die mirror."""
    out = []
    for kind, _inst, x, y, _o in EG:
        w, h = DIM[kind]
        px = x if variant == "eg" else round(round((W - x - w) / L) * L, 3)
        out.append((x, px, y, px + w, y + h))
    return out


def channel(variant):
    """free N-S centre channel (x_lo, x_hi) between the two child columns AS PLACED"""
    b = child_boxes(variant)
    wcol = [r for r in b if r[0] < CH_X]          # pt_w column (W in eg, E in wg)
    ecol = [r for r in b if r[0] > CH_X]
    left, right = (wcol, ecol) if variant == "eg" else (ecol, wcol)
    lo, hi = max(r[3] for r in left), min(r[1] for r in right)
    assert hi - lo >= 2 * (SBX + HALO + 0.5), f"{variant}: centre channel {lo}-{hi} narrower than a station window"
    return lo, hi


def station_x(variant, x):
    """eg station x -> this variant.  A station in the centre channel is mirrored about the CHANNEL centre of the placed
    wg image (r11 wg crash 10-13: the die mirror W - x put the reset stations at x 253.9, inside tcl h0 at 172.8-259.2:
    'STRAP_REGION no legal station site for u_rt.n3'); a station outside it is mirrored about the die (it follows the
    N / S pins, which are the die mirror)."""
    if variant == "eg":
        return x
    elo, ehi = channel("eg")
    if elo <= x <= ehi:
        wlo, whi = channel("wg")
        return round((wlo + whi) / 2 - (x - (elo + ehi) / 2), 3)
    return round(W - x, 3)


def station_check(variant, name, x, y, SBX=SBX, SBY=SBY):
    """the whole search window must be legal rows: inside the core and clear of every child + halo (0.5 um for the
    mirrored-pin track shift of a placed origin).  Fails at generation, not in the route."""
    m = HALO + 0.5
    assert m + SBX <= x <= W - m - SBX and m + SBY <= y <= H - m - SBY, f"{variant} {name}: window ({x}, {y}) leaves the core"
    for _ex, x0, y0, x1, y1 in child_boxes(variant):
        if x + SBX > x0 - m and x - SBX < x1 + m and y + SBY > y0 - m and y - SBY < y1 + m:
            raise AssertionError(f"{variant} station {name} window ({x}, {y}) +-({SBX}, {SBY}) overlaps a child + halo "
                                 f"at x {x0}-{x1} y {y0}-{y1}")


# el1013-smh-r14: g-lane relay and G1 select registers at fixed stations.  r13 post-CTS (wg): a relay register on a chain
# of 2-pin nets is HPWL-neutral anywhere along its wire, so the placer smeared every g-lane stage over the tile (u_d y
# 549..1,242, u_d3 y 7..807, leaf 0's u_god y 3..701): gin -> landing 185-753 um, launch -> gout 158-1,008 um, relay
# hops ~1 mm (TT -77).  The pin stages are fixed at their pins by io_flop_at_pins; these are the stages in between.
#   pass lanes (gin N -> gout S, 3 registers): u_d2 / u_v2 mid-channel, 650-700 um a hop
#   own rows: G1 (u_lh.gy / gt / gv / gf) midway between the bdc outputs (W column, outer face) and the tct outputs
#   (E column, outer face; 750 um apart, ~375 um each), then grd1 / grd2 down the channel (<= 450 um a hop) to gout
# (name, instance regexp, expected flops, eg x, y, half x, half y)
G_ST = [("g_pass2", r"g_gl\[[0-9]\]\.u_[dv]2/q\[[0-9]+\]\$_DFF", 100, CH_X, ymap(670.0), 17.0, 6.0),
        ("g1_l0", r"g_lf\[0\]\.u_lh\.g[ytvf](_q)?(\[[0-9]+\])?\$_DFF", 50, CH_X - 7.2, ymap(1080.0), 10.0, 7.0),
        ("grd1_l0", r"g_lf\[0\]\.u_gr[dv]1/q\[[0-9]+\]\$_DFF", 50, CH_X, ymap(720.0), 16.0, 6.0),
        ("grd2_l0", r"g_lf\[0\]\.u_gr[dv]2/q\[[0-9]+\]\$_DFF", 50, CH_X, ymap(380.0), 16.0, 6.0),
        ("g1_l1", r"g_lf\[1\]\.u_lh\.g[ytvf](_q)?(\[[0-9]+\])?\$_DFF", 50, CH_X - 7.2, 100.0, 10.0, 7.0),
        ("grd1_l1", r"g_lf\[1\]\.u_gr[dv]1/q\[[0-9]+\]\$_DFF", 50, 335.0, 62.0, 10.0, 6.0),
        ("grd2_l1", r"g_lf\[1\]\.u_gr[dv]2/q\[[0-9]+\]\$_DFF", 50, 310.0, 22.0, 10.0, 6.0)]
# el1013-smh-r15 OT_SMH_XREL: the leaf operand relay registers between the x store and the two columns.
#   xb_* (-> bdc, 1,084): in the xs | bdc gap (58 um leaf 0, 30 um leaf 1), under / over the bdc operand pins
#   xf_* (-> BF16 columns, 531): leaf 0 above the x store beside the centre channel (xs N pins -> ~300 um -> station ->
#   ~230 um -> tcl h1 N pins); leaf 1 in the centre channel between the x store's S pins and the tcl N pins
# (name, instance regexp, (min, max) flops, eg x, y, half x, half y): synthesis may trim unused tag / operand bits
YG0 = round((Y_XS0 + DIM["xs"][1] + Y_BDC0) / 2, 2)
YG1 = round((Y_BDC1 + DIM["bdc"][1] + Y_XS1) / 2, 2)
X_ST = [("xb_l0", r"g_lf\[0\]\.u_lh\.xb_[a-z0-9]+(\[[0-9]+\])?\$_DFF", (1000, 1084), 187.0, YG0, 50.0, 12.0),
        ("xf_l0", r"g_lf\[0\]\.u_lh\.xf_[a-z0-9]+(\[[0-9]+\])?\$_DFF", (480, 531), 325.0, round(Y_XS0 + DIM["xs"][1] + 113.0, 2), 40.0, 7.0),
        ("xb_l1", r"g_lf\[1\]\.u_lh\.xb_[a-z0-9]+(\[[0-9]+\])?\$_DFF", (1000, 1084), 187.0, YG1, 50.0, 10.0),
        ("xf_l1", r"g_lf\[1\]\.u_lh\.xf_[a-z0-9]+(\[[0-9]+\])?\$_DFF", (480, 531), CH_X, round(Y_XS1 + 84.0, 2), 17.0, 12.0)]


def g_stations(variant):
    lines = ["# el1013-smh-r14: g-lane relay / G1 select stations (window fill, nearest rows first, 1 um between cells)",
             "proc sr_place_win {insts x0 y0 x1 y1} {",
             "  set X0 [expr {round($x0*$::sr_dbu)}]; set Y0 [expr {round($y0*$::sr_dbu)}]; set X1 [expr {round($x1*$::sr_dbu)}]; set Y1 [expr {round($y1*$::sr_dbu)}]",
             "  set cy [expr {($Y0+$Y1)/2}]; set rows {}; set pad [expr {round(1.0*$::sr_dbu)}]",
             "  foreach r $::sr_rows {lassign $r ox oy xe ori; if {$oy >= $Y0 && $oy+$::sr_rh <= $Y1 && $xe > $X0 && $ox < $X1} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}",
             "  set rows [lsort -integer -index 0 $rows]",
             "  foreach i $insts {",
             "    set h [[$i getMaster] getHeight]; set w [expr {max([[$i getMaster] getWidth],$::sr_mw_dff)+4*$::sr_sw+$pad}]; set found 0",
             "    foreach r $rows {lassign $r delta ox oy xe ori",
             "      set x [expr {$ox+int(ceil(double(max($ox,$X0)-$ox)/$::sr_sw))*$::sr_sw}]",
             "      while {$x+$w <= min($xe,$X1)} {",
             "        set jump $x; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {",
             "          if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set jump [expr {max($jump,$ox+int(ceil(double($b-$ox)/$::sr_sw))*$::sr_sw)}]}}",
             "        }",
             "        if {$jump > $x} {set x $jump; continue}",
             "        $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; break",
             "      }; if {$found} break",
             "    }; if {!$found} {error \"G_STATION no legal site for [$i getName] in ($x0 $y0 $x1 $y1)\"}",
             "  }",
             "}",
             "# el1013-smh-r16: operand relay registers IN PIN ORDER.  r15 GRT (EARLY_FAIL_CONGESTION, both tiles): sr_place_win filled",
             "# the xb window in instance order, so a register sat anywhere in the 100-um window: its Q net ran sideways to its",
             "# bdc pin and its D net sideways from the x store (GRT: the 30.26-um leaf-1 gap full, H capacity 22 / usage 23 a",
             "# gcell at the window centre; markers on xb_w / xb_x / iw / ix nets only; the 58.32-um leaf-0 gap clean).",
             "# sr_pin_x: x of the hard-child pin a register drives (through <= 3 BUF / INV).",
             "proc sr_pin_x {i} {",
             "  set cur $i",
             "  for {set hop 0} {$hop < 4} {incr hop} {",
             "    set nxt {}",
             "    foreach it [$cur getITerms] { if {![$it isOutputSignal]} continue; set n [$it getNet]; if {$n eq \"NULL\"} continue",
             "      foreach jt [$n getITerms] { if {![$jt isInputSignal]} continue; set j [$jt getInst]",
             "        if {[[$j getMaster] isBlock]} { set bb [$jt getBBox]; return [expr {([$bb xMin]+[$bb xMax])/2}] }",
             "        if {[regexp {^(BUF|INV)} [[$j getMaster] getName]]} { set nxt $j } } }",
             "    if {$nxt eq {}} break; set cur $nxt",
             "  }; return -1",
             "}",
             "proc sr_sort_pin_x {insts} {",
             "  set l {}; foreach i $insts {lappend l [list [sr_pin_x $i] [$i getName] $i]}",
             "  set o {}; foreach e [lsort -integer -index 0 [lsort -dictionary -index 1 $l]] {lappend o [lindex $e 2]}; return $o",
             "}",
             "# sr_place_cols: every register in the row nearest the window centre that is free AT THE X OF ITS PIN (the Q net is a",
             "# vertical drop on the pin's own track column); a register with no pin or no free row takes the ordered window fill.",
             "proc sr_place_cols {insts x0 y0 x1 y1} {",
             "  set X0 [expr {round($x0*$::sr_dbu)}]; set Y0 [expr {round($y0*$::sr_dbu)}]; set X1 [expr {round($x1*$::sr_dbu)}]; set Y1 [expr {round($y1*$::sr_dbu)}]",
             "  set cy [expr {($Y0+$Y1)/2}]; set rows {}; set pad [expr {round(1.0*$::sr_dbu)}]; set rest {}; set ncol 0",
             "  foreach r $::sr_rows {lassign $r ox oy xe ori; if {$oy >= $Y0 && $oy+$::sr_rh <= $Y1 && $xe > $X0 && $ox < $X1} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}",
             "  set rows [lsort -integer -index 0 $rows]",
             "  foreach i [sr_sort_pin_x $insts] {",
             "    set px [sr_pin_x $i]; if {$px < 0} {lappend rest $i; continue}",
             "    set h [[$i getMaster] getHeight]; set w [expr {max([[$i getMaster] getWidth],$::sr_mw_dff)+4*$::sr_sw+$pad}]; set found 0",
             "    foreach r $rows {lassign $r delta ox oy xe ori",
             "      set x [expr {max($X0,min($px-$w/2,min($xe,$X1)-$w))}]; set x [expr {$ox+int(floor(double($x-$ox)/$::sr_sw))*$::sr_sw}]",
             "      if {$x < $ox || $x+$w > $xe} continue",
             "      set free 1; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {",
             "        if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set free 0; break}}",
             "        if {!$free} break }",
             "      if {!$free} continue",
             "      $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; incr ncol; break",
             "    }; if {!$found} {lappend rest $i}",
             "  }",
             "  if {[llength $rest]} {sr_place_win $rest $x0 $y0 $x1 $y1}",
             "  puts \"X_STATION_COLS $ncol registers at their pin column, [llength $rest] by ordered window fill\"",
             "}", "set gn 0"]
    tot = 0
    for name, rex, n, x, y, hx, hy in G_ST:
        x = station_x(variant, x)
        station_check(variant, name, x, y, hx, hy)
        lines += ["set gl {}",
                  "foreach i [$::sr_blk getInsts] {set nm [string map {\\\\ {}} [$i getName]]; "
                  f"if {{[regexp {{{rex}}} $nm] && [string match DFF* [[$i getMaster] getName]]}} {{lappend gl $i}}}}",
                  f"if {{[llength $gl] != {n}}} {{error \"G_STATION {name}: expected {n} registers, got [llength $gl]\"}}",
                  f"sr_place_win $gl {round(x - hx, 3)} {round(y - hy, 3)} {round(x + hx, 3)} {round(y + hy, 3)}",
                  "incr gn [llength $gl]"]
        tot += n
    for name, rex, (lo, hi), x, y, hx, hy in X_ST:
        x = station_x(variant, x)
        station_check(variant, name, x, y, hx, hy)
        lines += ["set gl {}",
                  "foreach i [$::sr_blk getInsts] {set nm [string map {\\\\ {}} [$i getName]]; "
                  f"if {{[regexp {{{rex}}} $nm] && [string match DFF* [[$i getMaster] getName]]}} {{lappend gl $i}}}}",
                  f"if {{[llength $gl] < {lo} || [llength $gl] > {hi}}} {{error \"G_STATION {name}: expected {lo}..{hi} registers, got [llength $gl]\"}}",
                  # r16: xb (under / over the bdc operand pins) at the pin columns; xf (station away from the tcl pins) filled in
                  # pin order
                  (f"sr_place_cols $gl {round(x - hx, 3)} {round(y - hy, 3)} {round(x + hx, 3)} {round(y + hy, 3)}" if name.startswith("xb_")
                   else f"sr_place_win [sr_sort_pin_x $gl] {round(x - hx, 3)} {round(y - hy, 3)} {round(x + hx, 3)} {round(y + hy, 3)}"),
                  f"puts \"X_STATION {name} [llength $gl]\"", "incr gn [llength $gl]"]
    lines += [f"puts \"G_STATION_PLACED {len(G_ST) + len(X_ST)} DFFS $gn FIXED_CELLS $::sr_fixed\""]
    return lines


def strap_regions(variant):
    # Five physical stages per leaf, kept on the gated cluster clock.
    points = [[(300,H-12),(365,ymap(1100)),(365,ymap(1060)),(300,ymap(1060)),(260,Y_XS0+DIM["xs"][1]+12)],
              [(340,H-12),(365,ymap(950)),(365,ymap(650)),(365,350),(260,Y_XS1-16)]]
    lines = ["# Generated fixed legal strap-stage stations: no child/clock/pin budget change.",
             "set ::sr_blk [ord::get_db_block]", "set ::sr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]", "set sn 0",
             "proc sr_init {} {",
             "  set ::sr_rows {}; set ::sr_used [dict create]; set ::sr_fixed 0",
             "  foreach r [$::sr_blk getRows] {set rb [$r getBBox]; lassign [$r getOrigin] ox oy; set ::sr_sw [[$r getSite] getWidth]; set ::sr_rh [[$r getSite] getHeight]; lappend ::sr_rows [list $ox $oy [$rb xMax] [$r getOrient]]}",
             "  set ::sr_mw_inv 0; set ::sr_mw_dff 0",
             "  foreach lib [[ord::get_db] getLibs] {foreach m [$lib getMasters] {set n [$m getName]; if {[regexp {^INV} $n]} {set ::sr_mw_inv [expr {max($::sr_mw_inv,[$m getWidth])}]} elseif {[regexp {^DFF} $n]} {set ::sr_mw_dff [expr {max($::sr_mw_dff,[$m getWidth])}]}}}",
             "  puts \"STRAP_GROWTH_RESERVE INV $::sr_mw_inv DFF $::sr_mw_dff DBU $::sr_dbu\"",
             "  foreach i [$::sr_blk getInsts] {if {[$i isPlaced]} {set bb [$i getBBox]; sr_occupy [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]}}",
             "}",
             "proc sr_occupy {x0 y0 x1 y1} {for {set k [expr {int(floor(double($y0)/$::sr_rh))}]} {$k <= int(floor(double($y1-1)/$::sr_rh))} {incr k} {dict lappend ::sr_used $k [list $x0 $x1]}}",
             "proc sr_place {group cx cy} {",
             "  set cx [expr {round($cx*$::sr_dbu)}]; set cy [expr {round($cy*$::sr_dbu)}]; set rows {}",
             "  foreach r $::sr_rows {lassign $r ox oy xe ori; if {abs($oy-$cy) < 4*$::sr_dbu} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}",
             "  set rows [lsort -integer -index 0 $rows]",
             "  foreach i [$group getInsts] {",
             "    set w [[$i getMaster] getWidth]; set h [[$i getMaster] getHeight]; set master [[$i getMaster] getName]; set mw [expr {[regexp {^INV} $master] ? $::sr_mw_inv : $::sr_mw_dff}]; set w [expr {max($w,$mw)+4*$::sr_sw}]; set found 0",
             "    foreach r $rows {lassign $r delta ox oy xe ori; if {$oy < $cy-4*$::sr_dbu || $oy+$h > $cy+4*$::sr_dbu} continue",
             "      set x [expr {$ox+int(ceil(double(max($ox,$cx-8*$::sr_dbu)-$ox)/$::sr_sw))*$::sr_sw}]",
             "      while {$x+$w <= min($xe,$cx+8*$::sr_dbu)} {",
             "        set jump $x; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {",
             "          if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set jump [expr {max($jump,$ox+int(ceil(double($b-$ox)/$::sr_sw))*$::sr_sw)}]}}",
             "        }",
             "        if {$jump > $x} {set x $jump; continue}",
             "        $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; break",
             "      }; if {$found} break",
             "    }; if {!$found} {error \"STRAP_REGION no legal station site for [$i getName]\"}",
             "  }",
             "}", "sr_init",
             "proc sr_bind {net group} {",
             "  for {set hop 0} {$hop < 5} {incr hop} {",
             "    set driver {}; foreach it [$net getITerms] {if {[$it isOutputSignal]} {lappend driver $it}}",
             "    if {[llength $driver] != 1} {error \"STRAP_REGION ambiguous driver\"}",
             "    set si [[lindex $driver 0] getInst]; set master [[$si getMaster] getName]",
             "    $group addInst $si",
             "    if {[string match *DFF* $master]} {return 1}",
             "    if {![regexp {^(INV|BUF)} $master]} {error \"STRAP_REGION non-register logic $master\"}",
             "    set ins {}; foreach it [$si getITerms] {if {[$it isInputSignal]} {lappend ins [$it getNet]}}",
             "    if {[llength $ins] != 1} {error \"STRAP_REGION buffer input ambiguity\"}; set net [lindex $ins 0]",
             "  }; error \"STRAP_REGION register not found\"", "}"]
    for leaf, ps in enumerate(points):
        for stage, (x,y) in enumerate(ps):
            x = station_x(variant, x)
            name=f"strap_l{leaf}_s{stage}"
            station_check(variant, name, x, y)
            lines += [f"set rg [odb::dbRegion_create $::sr_blk {name}]", "$rg setRegionType EXCLUSIVE",
                      f"odb::dbBox_create $rg [expr {{round({x-8}*$::sr_dbu)}}] [expr {{round({y-4}*$::sr_dbu)}}] [expr {{round({x+8}*$::sr_dbu)}}] [expr {{round({y+4}*$::sr_dbu)}}]",
                      f"set gr [odb::dbGroup_create $::sr_blk {name}]", "set nc 0",
                      "foreach net [$::sr_blk getNets] {", "  set nm [string map {\\\\ {}} [$net getName]]",
                      f"  if {{[string first {{g_strap[{leaf}].u_sr.s{stage}[}} $nm] >= 0 }} {{ sr_bind $net $gr; incr nc; incr sn }}",
                      "}", f"if {{$nc != 26}} {{error \"STRAP_REGION {name}: expected 26 DFFs, got $nc\"}}", f"sr_place $gr {x} {y}", "odb::dbGroup_destroy $gr", "odb::dbRegion_destroy $rg"]
    lines += ["if {$sn != 260} {error \"STRAP_REGION expected 260 DFFs\"}", "puts \"STRAP_REGION_PLACED 10 DFFS $sn FIXED_CELLS $::sr_fixed\""]
    # el1013-smh-r11: the reset tree's registers (ot_hbm_accel_smh_rst_tree) at fixed stations down the centre channel:
    # pin flop under the rst_n pin, one band station per stage, <= 340 um a hop (strap stations use x 365 at other y)
    rx = CH_X + 9.6
    rst = {"p0": H - 14, "n1": 1200, "n2": 1160, "n3": 1040, "f_gn": 1022, "f_lhn": 1014,
           "t1": 900, "m2": 760, "m3": 632, "f_gm": 618, "f_ptw": 610, "f_pte": 602,
           "t2": 560, "s3": 250, "f_gs": 232, "f_lhs": 224}
    rst = {k: (v if k == "p0" else ymap(v)) for k, v in rst.items()}
    lines += ["set rn 0"]
    for reg, y in rst.items():
        x = station_x(variant, rx)
        name = f"rst_{reg}"
        station_check(variant, name, x, y)
        lines += [f"set rg [odb::dbRegion_create $::sr_blk {name}]", "$rg setRegionType EXCLUSIVE",
                  f"odb::dbBox_create $rg [expr {{round({x-8}*$::sr_dbu)}}] [expr {{round({y-4}*$::sr_dbu)}}] [expr {{round({x+8}*$::sr_dbu)}}] [expr {{round({y+4}*$::sr_dbu)}}]",
                  f"set gr [odb::dbGroup_create $::sr_blk {name}]", "set nc 0",
                  "foreach net [$::sr_blk getNets] {", "  set nm [string map {\\\\ {}} [$net getName]]",
                  f"  if {{[regexp {{u_rt\\.{reg}$}} $nm]}} {{ sr_bind $net $gr; incr nc; incr rn }}",
                  "}", f"if {{$nc != 1}} {{error \"RESET_STATION {name}: expected 1 register, got $nc\"}}", f"sr_place $gr {x} {y}", "odb::dbGroup_destroy $gr", "odb::dbRegion_destroy $rg"]
    lines += [f"if {{$rn != {len(rst)}}} {{error \"RESET_STATION expected {len(rst)} registers\"}}", f"puts \"RESET_STATION_PLACED {len(rst)} FIXED_CELLS $::sr_fixed\""]
    lines += g_stations(variant)
    (OUT/f"smh_tile_{variant}_cpt_strap_regions.tcl").write_text("\n".join(lines)+"\n")


def main():
    for v in sys.argv[1:] or ["eg", "wg"]:
        strap_regions(v)
        s = spec(v)
        p = OUT / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
