#!/usr/bin/env python3
"""QW-SLICE6-KIT 10-20 (Q.STA.SLICE.2): ref_tile kits of the hardened one-level slice2 parent (lp.py landed parents of
tools/landed_parent/specs/qfd_dv_s5{,b}.json; plan claude/qw-slice5-1019 @961b2dafd results/arch/qw_slice5_1019).
CRITICAL prefix qfd_dv_slice2*: gate + packet to COORD-REVIEW-QUEUE only (no REVIEW.json, no submit).

  python3 tools/qwen_dv/slice5_kit.py a   -> qfd_dv_slice2_w5   (main: top qfd_dv_s5_lp, D4/E2 landings, +3 a crossing)
  python3 tools/qwen_dv/slice5_kit.py b   -> qfd_dv_slice2_w5b  (fallback: top qfd_dv_s5b_lp, D8/E4 landings, +5 a crossing;
                                                                 left-half lane cells mirrored MY so every lane head faces the
                                                                 SU centre; landing WRITE halves fenced beside their source too)
  python3 tools/qwen_dv/slice5_kit.py e   -> qfd_dv_slice2_e5   (the E master: main geometry mirrored MY, slice2_e face map)
  python3 tools/qwen_dv/slice5_kit.py f   -> qfd_dv_slice2_e5b  (QW-SLICE2E 10-20: E master of the fallback = w5b mirrored MY)
  E variants mirror EVERYTHING about x = W / 2: hard children, macros, pins AND the soft-leaf fences (QW-SLICE2E 10-20 fix:
  the e5 spec of 96f911c56 left the fences at the W positions while the hard children moved).

Floorplan (W master, dn face = W at x 0; outline 2462.376 x 2591.976 = the die slot of qfd_dv_slice2_{w,e}):
  r_fw / r_fe   face strips x 0..259.2 / 2203.2..2462.4, y 0..1296 (dn / up face pins, chain merges, pass-throughs)
  S band        station 2x4 (stnent geometry, x0 345.6 + 216 c, rows y 86.4 MX / 345.6 MY) + btab (4 SRAM above r_st0),
                stream + tload STAND-IN (4 ROM) / ctl / sc beside it (partition rects)
  pass channel  y 864..1296, std cells only (landing reads / writes of the face strips stay in the strips)
  SU block      y 1296..1987.2: 2 rows x (2 lane cells 345.6 | centre 561.6 | 2 lane cells); lane cell = exp + rsq on the
                bottom row, lane head + rcp on the top row (43.2-lattice origins, >= 21.6-um channels), lrly in its cell;
                centre = suvm (18 SRAM: VM 6 + CROM 4 + PROG 4 + BTAB-SU 4) + red
  tap row       y 1965.6..2052 (soft), head band: 4 columns of 475.2 (xhead soft + 8 x leaves 2 x 4 at pitch 129.6)
Every hard child origin on the 43.2 lattice; SRAM / ROM macros on the (0.432, 2.16) macro lattice with >= 20-um channels.
Regions: one clock port per lp region (ck_r_*), entry on the nearest face at the region's register mass.
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/landed_parent"))
import lp  # noqa: E402

V = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("a", "b", "e", "f") else sys.exit("usage: slice5_kit.py a|b|e|f")
NAME = {"a": "qfd_dv_slice2_w5", "b": "qfd_dv_slice2_w5b", "e": "qfd_dv_slice2_e5", "f": "qfd_dv_slice2_e5b"}[V]
MIRROR = V in ("e", "f")          # E master: W geometry mirrored about x = W / 2
GEOB = V in ("b", "f")            # fallback geometry / D8-E4 landings
LPN = "qfd_dv_s5b" if GEOB else "qfd_dv_s5"
TOP = LPN + "_lp"
LP_SPEC = f"tools/landed_parent/specs/{LPN}.json"
REC = f"results/arch/qw_slice6_1019/lp/{TOP}_record.json"
SPEC_DIR = "tools/ref_tile/specs_qw_slice6"
W, H = 2462.376, 2591.976
VSTN = "physical/ref_tile/qfd_dv_slice2_stnrgc/views/qfd_dv_redstn2_region"
VHEAD = "physical/ref_tile/qfd_dv_lane_h_safe2/views/qfd_dv_lane_h_safe2"
VSFU = {k: f"physical/ref_tile/qfd_su_sfu_{k}/views/ot_hdc_sfu_{k}_t" for k in ("exp", "rcp", "rsq")}
VXL = "physical/ref_tile/qfd_xs_leaf_w130/views/ot_qfd_xs_leaf"
M = "physical/asap7_memory_macros_v2/"
M1024, M128, M256 = M + "ot_sram_1r1w_1024x256_m2_r2c2", M + "ot_sram_1r1w_128x256_m1_r2c2", M + "ot_sram_1r1w_256x256_m2_r2c2"
MROM = "physical/asap7_memory_macros/ot_rom_4096x266_m8"
SOURCES = [f"rtl/qwen_dv/s5/lp/{TOP}.sv", "rtl/common/landed_parent/ot_pl_land.sv", "rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv",
           "rtl/qwen_dv/s5/qfd_dv_s5_vm.sv", "rtl/qwen_dv/qfd_dv_scalar2.sv", "rtl/qwen_dv/mu/qfd_dv_amax_mu.sv",
           "rtl/qwen_dv/qfd_dv_stream.sv", "rtl/qwen_dv/qfd_dv_slice_tload.sv", "rtl/qwen_dv/qfd_dv_table_rom_loader.sv",
           "rtl/hdc/ot_hdc_vreduce.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
           "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv",
           "rtl/hdc/ot_hdc_sfu_q.sv", "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv", "rtl/lib/ot_rst_pipe.sv",
           f"{M1024}/ot_sram_1r1w_1024x256_m2_r2c2_bb.v", f"{M128}/ot_sram_1r1w_128x256_m1_r2c2_bb.v",
           f"{M256}/ot_sram_1r1w_256x256_m2_r2c2_bb.v", f"{MROM}/ot_rom_4096x266_m8_bb.v"]
PIN_SIZE = {"M3": "0.018 0.144", "M5": "0.024 0.192", "M4": "0.192 0.024", "M6": "0.192 0.032"}

# ------------------------------------------------------------------------------------------------ geometry (W master)
STN_X = [345.6 + 216.0 * c for c in range(4)]
STN_YB, STN_YT = 86.4, 345.6
CELL_X = [259.2, 604.8, 1512.0, 1857.6]          # lane cell columns: left 2 | centre 950.4..1512 | right 2
CELL_Y = [1296.0, 1641.6]
LANE_CELL = {0: (0, 0), 1: (1, 0), 2: (0, 1), 3: (1, 1), 4: (2, 0), 5: (3, 0), 6: (2, 1), 7: (3, 1)}
HC_X = [302.4 + 475.2 * c for c in range(4)]
HC_Y = [2073.6, 2203.2, 2332.8, 2462.4]


def stn_place(k):
    top = k % 2 == 0
    return STN_X[k // 2], (STN_YT if top else STN_YB), ("MY" if top else "MX")


def lane_children(l):
    cx, cy = LANE_CELL[l]
    x0, y0 = CELL_X[cx], CELL_Y[cy]
    mir = GEOB and cx < 2                      # fallback: left half mirrored, so every lane head faces the SU centre
    if not mir:
        return [("exp", x0, y0, "R0"), ("rsq", x0 + 172.8, y0, "R0"), ("head", x0, y0 + 172.8, "R0"),
                ("rcp", x0 + 172.8, y0 + 172.8, "R0")]
    return [("rsq", x0, y0, "MY"), ("exp", x0 + 172.8, y0, "MY"), ("rcp", x0 + 43.2, y0 + 172.8, "MY"),
            ("head", x0 + 172.8, y0 + 172.8, "MY")]


def children():
    kids = []
    for k in range(8):
        x, y, o = stn_place(k)
        kids.append(dict(view=VSTN, count=1, inst=f"u_r{k}", at=[x, y], orient=o, exact=True))
    for l in range(8):
        for kind, x, y, o in lane_children(l):
            v = VHEAD if kind == "head" else VSFU[kind]
            inst = f"u_head{l}" if kind == "head" else f"u_{kind}{l}"
            kids.append(dict(view=v, count=1, inst=inst, at=[round(x, 3), round(y, 3)], orient=o, exact=True))
    # x leaves: the closed qfd_xs_leaf_w130 view is a legacy M6 abstract (child_lint (c) FAILs under a one-level M7
    # parent; the M5 re-kit qfd_xs_leaf_w130m5 has no view yet) -> LABELLED SOFT STAND-IN in their column region
    return kids


def snap(v, g):
    return round(round(v / g) * g, 3)


def macros():
    out = []
    ax, bx, cx = 972.0, 1168.56, 1365.12
    ys = [1317.6 + 92.88 * i for i in range(5)]
    py = [1782.0, 1844.64]
    col_a = ["*u_suvm*g_rep?0?*g_bank?0?*u_m", "*u_suvm*g_rep?0?*g_bank?1?*u_m", "*u_suvm*g_rep?1?*g_bank?0?*u_m",
             "*u_suvm*g_rep?1?*g_bank?1?*u_m", "*u_suvm*g_rep?2?*g_bank?0?*u_m"]
    col_b = ["*u_suvm*g_rep?2?*g_bank?1?*u_m", "*u_suvm*g_crom?0?*u_lo", "*u_suvm*g_crom?0?*u_hi", "*u_suvm*g_crom?1?*u_lo",
             "*u_suvm*g_crom?1?*u_hi"]
    for x, col in ((ax, col_a), (bx, col_b)):
        for y, inst in zip(ys, col):
            out.append(dict(view=M1024, count=1, inst=inst, at=[x, snap(y, 2.16)]))
    for x, b in ((ax, 0), (bx, 1)):
        out.append(dict(view=M256, count=1, inst=f"*u_suvm*g_prog?{b}?*u_lo", at=[x, py[0]]))
        out.append(dict(view=M256, count=1, inst=f"*u_suvm*g_prog?{b}?*u_hi", at=[x, py[1]]))
    for b, y in enumerate([1317.6, 1380.24, 1442.88, 1505.52]):
        out.append(dict(view=M128, count=1, inst=f"*u_suvm*g_btb?{b}?*u_m", at=[cx, y]))
    for b, (x, y) in enumerate([(345.6, 540.0), (462.24, 540.0), (345.6, 604.8), (462.24, 604.8)]):
        out.append(dict(view=M128, count=1, inst=f"*u_btab*g_btb?{b}?*u_m", at=[x, y]))
    for b, (x, y) in enumerate([(1296.0, 86.4), (1440.072, 86.4), (1296.0, 172.8), (1440.072, 172.8)]):
        out.append(dict(view=MROM, count=1, inst=f"*u_stm*u_tld*m{b}", at=[x, y]))
    return out


# fence rectangles per region: (x0, y0, x1, y1); soft leaves + landing READ halves (b: + WRITE halves of the source)
def fences():
    F = {"r_fw": (4.32, 21.6, 254.88, 1274.4), "r_fe": (2207.52, 21.6, 2458.08, 1274.4),
         "r_stm": (1252.8, 43.2, 1987.2, 453.6), "r_ctl": (1252.8, 496.8, 1641.6, 820.8),
         "r_sc": (1684.8, 496.8, 1987.2, 820.8), "r_su": (950.4, 1296.0, 1512.0, 1987.2),
         "r_tap": (864.0, 1965.6, 1598.4, 2052.0)}
    for k in range(8):
        x, y, o = stn_place(k)
        if o == "MY":   # top row: local W (cfg / rs_s / ck) faces physical E
            F[f"r_st{k}"] = (x, y - 21.6, x + 194.4, y + 172.8) if k else (x, y - 21.6, x + 216.0, 669.6)
        else:
            F[f"r_st{k}"] = (x - 43.2, y - 21.6, x + 151.2, y + 172.8)
    for c in range(4):
        F[f"r_hc{c}"] = (HC_X[c], 2052.0, HC_X[c] + 475.2, 2570.4)
    return F


# lane relay leaf fences: its own lane cell
def lrly_fence(l):
    cx, cy = LANE_CELL[l]
    return (CELL_X[cx], CELL_Y[cy], CELL_X[cx] + 345.6 - 10.8, CELL_Y[cy] + 345.6 - 2.16)


SOFT = {"r_fw": ["u_fdn"], "r_fe": ["u_fup"], "r_stm": ["u_stm", "u_fs"], "r_ctl": ["u_ctl"], "r_sc": ["u_sc"],
        "r_su": ["u_suvm", "u_red"], "r_tap": ["u_tap"], "r_st0": ["u_btab", "u_frs"],
        **{f"r_hc{c}": [f"u_xh{c}"] + [f"u_xl{c}_{lf}" for lf in range(8)] + (["u_fn"] if c == 1 else []) for c in range(4)}}


def fence_tcl(rec):
    F = fences()
    own = {}
    for L in rec["landings"]:
        own[f"u_lpl_{L['name']}_r"] = L["dst_region"]
        if GEOB:
            own[f"u_lpl_{L['name']}_w"] = L["src_region"]
    o = ["# generated by tools/qwen_dv/slice5_kit.py: PRE_GLOBAL_PLACE fences -- every soft leaf and its landing READ halves "
         "in its region rectangle beside the region clock entry" + (" (b: WRITE halves beside their source too)" if GEOB else ""),
         "set ::lpf_blk [ord::get_db_block]", "set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]", "array set ::lpf_g {}",
         "array set ::lpf_n {}"]
    boxes = dict(F)
    for l in range(8):
        boxes[f"r_lrly{l}"] = lrly_fence(l)
    if MIRROR:                                      # E master: fences mirrored with the children they hold
        boxes = {r: (round(W - x1, 3), y0, round(W - x0, 3), y1) for r, (x0, y0, x1, y1) in boxes.items()}
    for r, (x0, y0, x1, y1) in sorted(boxes.items()):
        o.append(f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "s5_fence_{r}"]')
        o.append(f"odb::dbBox_create $::lpf_r [expr {{round({x0}*$::lpf_dbu)}}] [expr {{round({y0}*$::lpf_dbu)}}] "
                 f"[expr {{round({x1}*$::lpf_dbu)}}] [expr {{round({y1}*$::lpf_dbu)}}]")
        o.append(f'set ::lpf_g({r}) [odb::dbGroup_create $::lpf_r "s5_fence_grp_{r}"]')
    soft = {i: r for r, l in SOFT.items() for i in l}
    soft.update({f"u_lrly{l}": f"r_lrly{l}" for l in range(8)})
    o.append("array set ::lpf_own {" + " ".join(f"{k} {v}" for k, v in sorted({**own, **soft}.items())) + "}")
    o += ["foreach i [$::lpf_blk getInsts] {",
          "  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne \"CORE\"} continue",
          "  regsub -all {\\\\} [$i getName] {} n",
          "  if {![regexp {^(u_lpl_[0-9]+_[wr]|u_[a-z0-9_]+?)[./]} $n -> h]} continue",
          "  if {![info exists ::lpf_own($h)]} continue",
          "  if {[$i getGroup] ne \"NULL\"} continue",
          "  set r $::lpf_own($h)",
          "  $::lpf_g($r) addInst $i",
          "  incr ::lpf_n($r)",
          "}",
          "foreach r [lsort [array names ::lpf_g]] {",
          "  if {![info exists ::lpf_n($r)]} { set ::lpf_n($r) 0 }",
          "  puts \"S5_FENCE $r cells=$::lpf_n($r)\"",
          "}"]
    return "\n".join(o) + "\n"


# ------------------------------------------------------------------------------------------------ ports / faces
FACE_W = ["cmd_i", "hr_i", "st_up_i", "st_dn_o", "sc_up_i", "sc_dn_o", "ch_dn_o", "ch_dn_i", "ag_dn_o", "st", "cc_o",
          "l9_i", "treq_i", "rst_n"]
FACE_E = ["cmd_o", "hr_o", "st_up_o", "st_dn_i", "sc_up_o", "sc_dn_i", "ch_up_i", "ch_up_o", "ag_up_i", "l9_o", "treq_o"]
FACE_N = ["rs_n", "cw_n0", "cw_n1", "cw_n2", "cw_n3"]
FACE_S = ["rs_s", "cw_s0", "cw_s1", "cw_s2", "cw_s3"]
# along-face ranges (um) of each port group (W/E: y; N/S: x), clocks beside their region mass
RANGE = {"cmd_i": (24, 140), "hr_i": (140, 300), "treq_i": (300, 304), "l9_i": (304, 420), "ch_dn_i": (420, 650),
         "ch_dn_o": (650, 900), "ag_dn_o": (900, 905), "st": (905, 940), "cc_o": (940, 955), "sc_up_i": (955, 970),
         "sc_dn_o": (970, 985), "st_up_i": (990, 1120), "st_dn_o": (1120, 1250), "rst_n": (1255, 1258),
         "cmd_o": (24, 60), "hr_o": (60, 170), "treq_o": (170, 174), "l9_o": (174, 300), "ch_up_i": (300, 560),
         "ch_up_o": (560, 800), "ag_up_i": (800, 805), "sc_up_o": (805, 820), "sc_dn_i": (820, 835),
         "st_up_o": (840, 1040), "st_dn_i": (1040, 1250),
         "rs_n": (HC_X[1] + 152, HC_X[1] + 470),
         **{f"cw_n{c}": (HC_X[c] + 2, HC_X[c] + (150 if c == 1 else 470)) for c in range(4)},
         "rs_s": (330, 1150), **{f"cw_s{c}": (1255 + 182 * c, 1255 + 182 * c + 176) for c in range(4)}}
CK = {"ck_r_fw": ("W", 1284), "ck_r_fe": ("E", 1284), "ck_r_stm": ("S", 1990), "ck_r_ctl": ("S", 2000),
      "ck_r_sc": ("S", 2010), "ck_r_su": ("N", HC_X[2] - 8), "ck_r_tap": ("N", HC_X[2] - 16),
      **{f"ck_r_st{k}": ("S", STN_X[k // 2] + (200.0 if k % 2 == 0 else 2.0)) for k in range(8)},
      **{f"ck_r_hc{c}": ("N", HC_X[c] + 1.0 if c != 1 else HC_X[c] + 452.0) for c in range(4)}}


def port_widths():
    t = (ROOT / f"rtl/qwen_dv/s5/lp/{TOP}.sv").read_text()
    hdr = t[t.index(f"module {TOP}"):t.index(");", t.index(f"module {TOP}"))]
    out = {}
    for m in re.finditer(r"(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)", hdr):
        out[m.group(3)] = (m.group(1), int(m.group(2)) + 1 if m.group(2) else 1)
    return out


def mirror_face(f):
    return {"W": "E", "E": "W"}.get(f, f)


def pins_tcl(pw):
    lines = [f"# generated by tools/qwen_dv/slice5_kit.py ({NAME}): exact parent pins, port groups at their region, "
             "clock entries beside their region's register mass"]
    placed = {}
    faces = {"N": [], "S": [], "W": [], "E": []}
    dens = {}

    def pin(n, f, v, i):
        if MIRROR:
            f = mirror_face(f)
            if f in ("N", "S"):
                v = W - v
        if f in ("N", "S"):
            layer = "M3" if i % 2 == 0 else "M5"
            x, y = v, (H if f == "N" else 0.0)
        else:
            layer = "M4" if i % 2 == 0 else "M6"
            x, y = (0.0 if f == "W" else W), v
        placed[n] = (layer, round(x, 3), round(y, 3))
        lines.append(f"place_pin -pin_name {{{n}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{PIN_SIZE[layer]}}} -force_to_die_boundary")

    rng = dict(RANGE)
    for f, ports in (("W", FACE_W), ("E", FACE_E)):          # face strips: groups in order, length ~ width (uniform density)
        tot = sum(pw[p][1] for p in ports)
        y, lo, hi = 24.0, 24.0, 1272.0
        for p in ports:
            h = (hi - lo) * pw[p][1] / tot
            rng[p] = (y, y + h)
            y += h
    for f, ports in (("W", FACE_W), ("E", FACE_E), ("N", FACE_N), ("S", FACE_S)):
        for p in ports:
            d, w = pw[p]
            a, b = rng[p]
            bits = [p] if w == 1 else [f"{p}[{i}]" for i in range(w)]
            # reserved 2-um windows around the clock entries on this face: the group's pins skip them
            hole = sorted(v for c, (ff, v) in CK.items() if ff == f and a - 1.0 < v < b + 1.0)
            free = (b - a) - 2.0 * len(hole)
            for i, n in enumerate(bits):
                v = a + free * (i + 0.5) / len(bits)
                for hv in hole:
                    if v >= hv - 1.0:
                        v += 2.0
                pin(n, f, v, i)
            dens[p] = round(len(bits) / (b - a), 2)
            faces[mirror_face(f) if MIRROR else f].append(p)
    for c, (f, v) in CK.items():
        pin(c, f, v, 1)
        faces[mirror_face(f) if MIRROR else f].append(c)
    tcl = ROOT / f"{SPEC_DIR}/{NAME}_pins.tcl"
    tcl.parent.mkdir(parents=True, exist_ok=True)
    tcl.write_text("\n".join(lines) + "\n")
    return placed, faces, dens


def port_regions(S):
    P = lp.Parent(dict(S, schedule="reference", _spec_path=LP_SPEC)).plan()
    out = {}
    for n, r in P["nreg"].items():
        if n.startswith("port:"):
            out[n[5:]] = r
    return out


def main():
    S = lp.load(LP_SPEC)
    rec = json.loads((ROOT / REC).read_text())
    pw = port_widths()
    placed, faces, dens = pins_tcl(pw)
    preg = port_regions(S)
    dom = {}
    for r, info in rec["regions"].items():
        name = "core" if r == "r_fw" else r
        ins = sorted(p for p, rr in preg.items() if rr == r and pw.get(p, ("", 0))[0] == "input")
        outs = sorted(p for p, rr in preg.items() if rr == r and pw.get(p, ("", 0))[0] == "output")
        if r == "r_fw":
            ins = sorted(set(ins) | {"rst_n"})
        dom[name] = dict(ratio=[1, 1], ports=[info["clock_port"]], inputs=ins, outputs=outs)
    fen = f"{SPEC_DIR}/{NAME}_fences.tcl"
    (ROOT / fen).write_text(fence_tcl(rec))
    kids = children()
    mac = macros()
    if MIRROR:                                     # the E master: the whole geometry mirrored about x = W / 2
        flipo = {"R0": "MY", "MY": "R0", "MX": "R180", "R180": "MX"}
        from_lef = lambda v: float(re.search(r"SIZE ([\d.]+) BY", (ROOT / v / (Path(v).name + ".lef")).read_text()).group(1))
        for k in kids:
            k["at"] = [snap(W - k["at"][0] - from_lef(k["view"]), 43.2), k["at"][1]]   # W = 57 x 43.2 - 0.024: back on the lattice
            k["orient"] = flipo[k["orient"]]
        for m in mac:
            mw = float(re.search(r"SIZE ([\d.]+) BY", (ROOT / m["view"] / (Path(m["view"]).name + ".lef")).read_text()).group(1))
            m["at"] = [round(math.floor((W - m["at"][0] - mw) / 0.432 + 1e-6) * 0.432, 3), m["at"][1]]   # macro x lattice 0.432
            m["orient"] = "MY"
    run_s5 = "bash rtl/test/qwen_dv/s5/run_s5.sh"
    benches = [
        dict(name="s5_flat0_eq_slice2", cmd=f"{run_s5} {{RUN}}/eq eq 0", expect="pass", pass_regex="S5_EQ PASS",
             threads=16, peak_ram_gb=48, needs=["verilator"]),
        dict(name="s5_lp_lockstep_mut0", cmd=f"SPEC={LPN} {run_s5} {{RUN}}/lp lp 0", expect="pass",
             pass_regex="LP_LOCKSTEP PASS", threads=16, peak_ram_gb=64, needs=["verilator"]),
        dict(name="s5_lp_mut1_bypass", cmd=f"SPEC={LPN} {run_s5} {{RUN}}/lp1 lp 1", expect="fail",
             fail_regex="LP_LOCKSTEP FAIL", threads=16, peak_ram_gb=64, needs=["verilator"]),
        dict(name="s5_audit", cmd=f"{run_s5} {{RUN}}/audit audit", expect="pass", pass_regex=f"AUDIT {LPN} PASS",
             threads=1, peak_ram_gb=4),
    ]
    checklist = {
        "1_pins": "PASS (parent): every input port lands in its face / entry region (pin register in fdn / fup, or the landing "
                  "ring at the pin for fn / frs entries); every output leaves from a face-region flop (fdn / fup merge or pin "
                  "register, or a landing read register; pass-through wires only inside the face leaves). rst_n -> lp reset "
                  "runs (depth 10) -> each leaf's own 2-stage landing. OPEN: the 182 slice<->slice face landings "
                  "(plan claude/qw-slice4-face-1019 @7811217d7) are NOT in this parent yet (QW-SLICE6 follow-up).",
        "2_reach": "OPEN / measured by the gate: cross-region nets are landings (" + ("E=2: <= ~1.3 mm per landing window"
                   if not GEOB else "E=4: <= ~2.6 mm per landing window") + "); the face<->face pass crossings (fdn <-> fup "
                   "2.2 mm: chu_q, hr, cmd, chd, treq, l9) and the N<->S corridor (rs_n, cw_s 2.2 mm) are the long ones; "
                   "1-bit reset runs hop <= 405 um (lp reach)",
        "3_fanout": "PASS by construction: one read half per (net, reader region), shared write rings (share_rings); leaf "
                    "internal fanout is the leaf kits' gates (sibling lanes)",
        "4_depth": "PASS (parent): wires only between children; landing read = registered slot select",
        "5_storage": "PASS: VM / CROM / PROG / BTAB in 22 SRAM macros (suvm 18, btab 4), tload tables in 4 ROM macros; "
                     f"landing rings D={rec['D']} are fixed-latency landings ({rec['flops']['landing']} flops)",
        "6_floorplan": "PASS (plan): hard children on the 43.2 lattice (8 stnrgc, 8 lane heads safe2, 24 SFU; 32 x leaves soft stand-in), "
                       "SRAM / ROM on the macro lattice with >= 20-um channels; one full-width std-cell band per region "
                       "between the child rows; outline = the die slot 2462.376 x 2591.976 (aspect 1.05); parent pins "
                       f"<= {max(dens.values()):.2f}/um per port group",
        "7_clock": f"multiple_cts_roots: {len(rec['regions'])} regional roots (ck_r_*), entry on the nearest face beside the "
                   "region's register mass; fences hold every soft leaf + its landing read halves beside its entry (stnent "
                   "gate3 lesson); judged per region at child flops (TT / FF spread <= 80); io_hold_margin 0.03",
        "8_schedule": "static; compiler record " + REC + ": every cross-region reader pin +" + str(rec["E"] + 1) + " edges "
                      "(lp lag_pins; slice loops ctl <-> SU / station / scalar, fdn <-> fup: the compiler re-schedules); "
                      "leaf HARD registers +1 (ctl bundles / VM writes / own word / ag, stm tw, suvm su_nr, fdn pc_bad, tap "
                      "cid); THRU stream / scalar chains +6 a hop vs the plan's FWD +3 (stand-in stream); NOTICE lanes/QW-GEN3.md",
        "stand_ins": "LABELLED STAND-INS: stream + tload (qfd_dv_s5_stm: QW-STREAM2 t2/t2c and QW-TLOAD2 ns3/ns3b pending), "
                     "x leaves = SOFT RTL stand-in (ot_qfd_xs_leaf at its defaults: the closed w130 view is a legacy M6 abstract that FAILs child_lint (c) under this one-level parent; M5 re-kit view owed); SOFT in this gate (kits gating in QW-SLICE6 "
                     "sub-lanes, no views yet): suvm, ctl, sc, red, tap, xhead, lrly, btab, fdn / fup",
    }
    spec = dict(
        name=NAME, top=TOP, kind="cluster", diagnostic=True,
        sources=SOURCES, params={}, defines=["OT_S5_HARD"], hard_define="OT_S5_HARD",
        clock="multiple_cts_roots", clock_port="ck_r_fw",
        clock_ports=[rec["regions"][r]["clock_port"] for r in rec["regions"]],
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dom,
        landed_record=REC,
        reset_ports=["rst_n"],
        outline=dict(w=W, h=H, exact=True),
        child_lattice_um=43.2,
        children=kids, macros=mac, inter=[],
        pins={f: sorted(set(v)) for f, v in faces.items() if v},
        io_tcl=f"{SPEC_DIR}/{NAME}_pins.tcl",
        layer_cap="M7",
        route=dict(pd=0.45, threads=32, peak_ram_gb=192, macro_halo_um=5.4, pin_h="M4 M6", pin_v="M3 M5",
                   hold_margin_ns=0.03, io_hold_margin_ns=0.03),
        recipe=4, inhold=False, outhold=False,
        io_flop_at_pins={"cols": 4, "allow_none": True},
        pin_regs=dict(enable=False, reason="landed parent: every input port is a face-leaf pin register or a landing ring at "
                      "the pin; every output is a face-region flop; lp.py lag / offsets are the compiler record"),
        reset_landing=dict(enable=False, reason=f"rst_n feeds the lp reset runs (depth {rec['reset']['depth']}, priced as boot "
                           "release); each leaf lands its rst_n in 2 more stages on its own root"),
        safe_design_checklist=checklist,
        pin_density_per_um=dens,
        why_floorplan="plan results/arch/qw_slice5_1019 (partition.json floorplan): S band station / stream / ctl / sc, pass "
                      "channel, SU block 2 x (2 | centre | 2), tap row, head band 4 columns; dn face W (slice2_w face map)",
        landed=dict(record=REC, landings=len(rec["landings"]), landing_flops=rec["flops"]["landing"],
                    reset_depth=rec["reset"]["depth"], lp_spec=LP_SPEC, D=rec["D"], E=rec["E"]),
        structural_change="QW-SLICE6 10-20 Q.STA.SLICE.2: slice2 rebuilt as a hardened ONE-LEVEL landed parent of leaves "
                          "(LEAD3-QW decision (a)), replacing the failed one-root slice2_e / slice2_wh cores; variant " + V +
                          {"a": ": D4/E2 landings (+3 a crossing)", "b": ": D8/E4 landings (+5 a crossing), left-half lane "
                           "cells mirrored, write halves fenced at the source", "e": ": E master (MY mirror of w5)",
                           "f": ": E master of the fallback (MY mirror of w5b: D8/E4, write halves fenced)"}[V],
        pin_hook_before_flops=[fen],
        job=dict(owner="Claude:QW-SLICE2E" if MIRROR else "Claude:QW-SLICE6",
                 branch="claude/qw-slice2e-1020" if MIRROR else "claude/qw-slice6-kit-1019", tag="g1" + V,
                 purpose="QW-SLICE6: hardened one-level slice2 parent (CRITICAL: coordinator review before any route)",
                 views_to=f"physical/ref_tile/{NAME}/views", record_to=f"results/rtl/ref_tile/{NAME}",
                 hold_merge="CRITICAL qfd_dv_slice2 prefix: coordinator PNG review first; soft leaves pending their views",
                 extra_paths=["rtl/qwen_dv", "rtl/hdc", "rtl/common/landed_parent", "rtl/lib", "rtl/qwen_sys/dvm_20261014",
                              "rtl/test", "tools/landed_parent", "tools/qwen_dv", "physical/asap7_memory_macros_v2",
                              "physical/asap7_memory_macros/ot_rom_4096x266_m8", "physical/ref_tile/qfd_dv_slice2_stnrgc/views",
                              "physical/ref_tile/qfd_dv_lane_h_safe2/views", "physical/ref_tile/qfd_su_sfu_exp/views",
                              "physical/ref_tile/qfd_su_sfu_rcp/views", "physical/ref_tile/qfd_su_sfu_rsq/views",
                              "physical/hbm_accel_die_views/stations/bench", "results/arch/qw_slice6_1019"],
                 benches=benches))
    out = ROOT / f"{SPEC_DIR}/{NAME}.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out.relative_to(ROOT), len(placed), "pins; max density", max(dens.values()), "/um;", len(kids), "children,",
          len(mac), "macros;", len(dom), "clock domains")


if __name__ == "__main__":
    main()
