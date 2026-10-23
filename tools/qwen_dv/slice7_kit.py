#!/usr/bin/env python3
"""QW2-SLICE2 10-21 (Q.STA.SLICE.3/.4): TALL-SLOT kits of the slice2 W/E master -- QW2-NEXTGEN reticle move: the COORD slot
4060.8 x 2592 does not fit the die (12 columns -> die W 52,164 um > 33,000), same area moved into y: 2462.4 x 4276.8.
Successor of slice6_kit.py (w6/w6b/e6/e6b at 4060.8 x 2592; same landed parents qfd_dv_s6{,b}_lp, same RTL, same benches).

  python3 tools/qwen_dv/slice7_kit.py a|b|e|f -> qfd_dv_slice2_w7 / w7b / e7 / e7b  (a/b = D4E2 / D8E4 landings; e/f = MY mirror)

Floorplan (W master, y from S): S band 0..820.8 (stations 2x4, btab_s4, stream c3r + tload ns4, ctl5, sc) | pass channel |
VM8 BAND 1296..2980.8 (+1684.8: the VM8 group centred, P3 child layout 1425.6 x 993.6, slot sized for the P4 vm8rb
1555.2 x 1123.2; su8 above the group's PROG column; the 8 closed lane relays in one row at the band top, each under its lane
cell column) | SU block 2980.8..3672 (w5 lane cells 2 | centre 561.6 | 2, 4 hard children each) | tap row | head band (4
columns of 475.2).  Region fences as slice6; r_su = the band + the SU centre (two boxes).
OPEN (not in this kit): VM8 P4 qfd_dv_s5_vm8r binding (10 regional clock ports, VM +3 / BTAB,CROM +6 / reset +5) needs a
su8p4 adapter + regenerated s6 lp with the VM8 clock ports; until then the VM8 glue is SOFT under ck_r_su (risk measured).
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/landed_parent"))
sys.path.insert(0, str(ROOT / "tools/qwen_dv"))
import lp  # noqa: E402
import gen_slice6_lp_spec as g6  # noqa: E402

V = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("a", "b", "e", "f") else sys.exit("usage: slice6_kit.py a|b|e|f")
NAME = {"a": "qfd_dv_slice2_w7", "b": "qfd_dv_slice2_w7b", "e": "qfd_dv_slice2_e7", "f": "qfd_dv_slice2_e7b"}[V]
MIRROR = V in ("e", "f")          # E master: W geometry mirrored about x = W / 2
GEOB = V in ("b", "f")            # fallback geometry / D8-E4 landings
LPN = "qfd_dv_s6b" if GEOB else "qfd_dv_s6"
TOP = LPN + "_lp"
LP_SPEC = f"tools/landed_parent/specs/{LPN}.json"
REC = f"{g6.REC_DIR}/{TOP}_record.json"
SPEC_DIR = "tools/ref_tile/specs_qw2_slice2_tall"
W, H = 2462.376, 4276.776         # QW2-NEXTGEN 10-21 reticle move: 57 x 43.2 - 0.024 by 99 x 43.2 - 0.024 (same area as 4060.8 x 2592)
DY = 1684.8                       # the VM8 band inserted between the pass channel and the SU block
VSTN = "physical/ref_tile/qfd_dv_slice2_stnrgc/views/qfd_dv_redstn2_region"
VHEAD = "physical/ref_tile/qfd_dv_lane_h_safe2/views/qfd_dv_lane_h_safe2"
VSFU = {k: f"physical/ref_tile/qfd_su_sfu_{k}/views/ot_hdc_sfu_{k}_t" for k in ("exp", "rcp", "rsq")}
VLRLY = "physical/ref_tile/qfd_dv_s5_lrlyb/views/qfd_dv_s5_lrly" if GEOB else "physical/ref_tile/qfd_dv_s5_lrly/views/qfd_dv_s5_lrly"
VCTL = "physical/ref_tile/qfd_dv_s5_ctl5/views/qfd_dv_s5_ctl_repair4_leaf"
VSU8 = "physical/ref_tile/qfd_dv_s5_su8/views/qfd_dv_s5_su8_rst3"
VSTREAM = "physical/ref_tile/qfd_dv_stream_t3c_1020/views/qfd_dv_stream_tile"
VTLOAD = "physical/ref_tile/qfd_dv_slice_tload_ns4/views/qfd_dv_slice_tload"
VBTAB = "physical/ref_tile/qfd_dv_s5_btab_s4/views/qfd_dv_s5_btab_s4"
VVM8 = {"vmr": "physical/ref_tile/qfd_dv_s5_vmr/views/qfd_dv_s8x_vmr", "prog": "physical/ref_tile/qfd_dv_s5_prog/views/qfd_dv_s8x_prog",
        "crh": "physical/ref_tile/qfd_dv_s5_crh/views/qfd_dv_s8x_crh", "btab": "physical/ref_tile/qfd_dv_s5_btab/views/qfd_dv_s8x_btab"}
VM8Q_VIEW = None                  # physical/ref_tile/qfd_dv_slice2_vm8q{,b}/views/qfd_dv_s5_vm8q once a gate closes + routes
VM8Q_KIT = "physical/ref_tile/qfd_dv_slice2_vm8q"           # its child layout (P3 2-row) is reused for the soft group
SOURCES = [f"{g6.OUT_DIR}/{TOP}.sv", "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_rst_copy.sv",
           "rtl/common/landed_parent/ot_pl_land_split.sv", *g6.CHILD_SOURCES,
           "rtl/qwen_dv/qfd_dv_scalar2.sv", "rtl/qwen_dv/mu/qfd_dv_amax_mu.sv",
           "rtl/hdc/ot_hdc_vreduce.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
           "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv",
           "rtl/hdc/ot_hdc_sfu_q.sv", "rtl/lib/ot_rst_pipe.sv"]
# hard-child module names (SYNTH_BLACKBOXES): their RTL above is only for lp.py / the lint, never synthesised
KEEP = ["qfd_dv_s6_rk", "qfd_dv_s6_vk", "qfd_dv_s6_pk1", "qfd_dv_s6_pk4",
        "qfd_dv_s5_vm8q_rst", "qfd_dv_s5_vm8q_vrd", "qfd_dv_s5_vm8q_vwr", "qfd_dv_s5_vm8q_twb", "qfd_dv_s5_vm8q_twp",
        "qfd_dv_s5_vm8q_twc"]
PIN_SIZE = {"M3": "0.018 0.144", "M5": "0.024 0.192", "M4": "0.192 0.024", "M6": "0.192 0.032"}

# ------------------------------------------------------------------------------------------------ geometry (W master)
STN_X = [345.6 + 216.0 * c for c in range(4)]
STN_YB, STN_YT = 86.4, 345.6
CELL_X = [259.2, 604.8, 1512.0, 1857.6]          # lane cell columns: left 2 | centre 950.4..1512 | right 2 (w5 SU block)
CELL_Y = [1296.0 + DY, 1641.6 + DY]
CEN_X0, CEN_W = 950.4, 561.6                      # SU centre (su8 soft-group glue + red)
BAND_Y0, BAND_Y1 = 1296.0, 1296.0 + DY            # VM8 band: the VM8 group (sized for vm8rb 1555.2 x 1123.2) + the 8 lane relays
LANE_CELL = {0: (0, 0), 1: (1, 0), 2: (0, 1), 3: (1, 1), 4: (2, 0), 5: (3, 0), 6: (2, 1), 7: (3, 1)}
HC_X = [302.4 + 475.2 * c for c in range(4)]
HC_Y = [2073.6 + DY, 2203.2 + DY, 2332.8 + DY, 2462.4 + DY]
VM8_X0, VM8_Y0 = 518.4, BAND_Y0 + 86.4            # the group (1425.6 x 993.6 P3 layout) centred in x, S part of the band
SU8_AT = (1598.4, BAND_Y0 + 86.4 + 993.6 + 43.2)  # su8 (172.8 x 129.6) above the group's PROG column, below the lane relays
STREAM_AT, TLOAD_AT, CTL_AT, BTAB_AT = (1296.0, 43.2), (1598.4, 43.2), (1296.0, 518.4), (345.6, 518.4)
LRLY_Y = BAND_Y1 - 43.2 - 216.0                   # lane relay row at the band top, under its lane cell column

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


def lrly_place(l):
    """lane relay l in the band-top row directly under its lane cell column (cell row 0 -> left slot, row 1 -> right slot)."""
    cx, cy = LANE_CELL[l]
    x0 = CELL_X[cx] + (0.0 if cy == 0 else 172.8)
    return round(x0, 3), round(LRLY_Y if not GEOB else LRLY_Y + 43.2, 3)


def vm8_children():
    k = json.loads((ROOT / VM8Q_KIT / "spec.json").read_text())
    out = []
    for c in k["children"]:
        kind = {"qfd_dv_s8x_vmr": "vmr", "qfd_dv_s8x_prog": "prog", "qfd_dv_s8x_crh": "crh", "qfd_dv_s8x_btab": "btab"}[Path(c["view"]).name]
        out.append(dict(view=VVM8[kind], count=1, inst=f"u_suvm*u_vm8q*{c['inst']}",
                        at=[round(VM8_X0 + c["at"][0], 3), round(VM8_Y0 + c["at"][1], 3)], orient=c.get("orient", "R0"), exact=True))
    return out


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
        kids.append(dict(view=VLRLY, count=1, inst=f"u_lrly{l}", at=list(lrly_place(l)), orient="R0", exact=True))
    kids.append(dict(view=VCTL, count=1, inst="u_ctl", at=list(CTL_AT), orient="R0", exact=True))
    kids.append(dict(view=VSTREAM, count=1, inst="u_stm*u_stream", at=list(STREAM_AT), orient="R0", exact=True))
    kids.append(dict(view=VTLOAD, count=1, inst="u_stm*u_tload", at=list(TLOAD_AT), orient="R0", exact=True))
    kids.append(dict(view=VBTAB, count=1, inst="u_btab*u_bt", at=list(BTAB_AT), orient="R0", exact=True))
    kids.append(dict(view=VSU8, count=1, inst="u_suvm*u_su8", at=list(SU8_AT), orient="R0", exact=True))
    if VM8Q_VIEW:
        kids.append(dict(view=VM8Q_VIEW, count=1, inst="u_suvm*u_vm8q", at=[VM8_X0, VM8_Y0], orient="R0", exact=True))
    else:
        kids += vm8_children()
    # x leaves: the closed qfd_xs_leaf_w130 view is a legacy M6 abstract (child_lint (c) FAILs under a one-level M7
    # parent; pocket-closing LEF owed) -> LABELLED SOFT STAND-IN in their column region
    return kids


def snap(v, g):
    return round(round(v / g) * g, 3)


def macros():
    return []       # every SRAM / ROM now sits inside a hard child (VM8 split leaves, btab_s4, tload ns4)


# fence rectangles per region: (x0, y0, x1, y1); soft leaves + landing READ halves (b: + WRITE halves of the source)
def fences():
    F = {"r_fw": (4.32, 21.6, 254.88, 1274.4), "r_fe": (W - 254.88, 21.6, W - 4.32, 1274.4),
         "r_stm": (1252.8, 21.6, 2030.4, 475.2), "r_ctl": (1252.8, 496.8, 1663.2, 820.8),
         "r_sc": (1684.8, 496.8, 2181.6, 820.8),
         "r_su": [(259.2, BAND_Y0, W - 259.2, BAND_Y1), (CEN_X0, BAND_Y1, CEN_X0 + CEN_W, BAND_Y1 + 691.2)],
         "r_tap": (864.0, 1965.6 + DY, 1598.4, 2052.0 + DY)}
    for k in range(8):
        x, y, o = stn_place(k)
        if o == "MY":   # top row: local W (cfg / rs_s / ck) faces physical E
            F[f"r_st{k}"] = (x, y - 21.6, x + 194.4, y + 172.8) if k else (x, y - 21.6, x + 216.0, 777.6)
        else:
            F[f"r_st{k}"] = (x - 43.2, y - 21.6, x + 151.2, y + 172.8)
    for c in range(4):
        F[f"r_hc{c}"] = (HC_X[c], 2052.0 + DY, HC_X[c] + 475.2, 2570.4 + DY)
    return F


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
    o = ["# generated by tools/qwen_dv/slice6_kit.py: PRE_GLOBAL_PLACE fences -- every soft leaf and its landing READ halves "
         "in its region rectangle beside the region clock entry" + (" (b: WRITE halves beside their source too)" if GEOB else ""),
         "set ::lpf_blk [ord::get_db_block]", "set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]", "array set ::lpf_g {}",
         "array set ::lpf_n {}"]
    boxes = dict(F)
    if MIRROR:                                      # E master: fences mirrored with the children they hold
        boxes = {r: [(round(W - x1, 3), y0, round(W - x0, 3), y1) for (x0, y0, x1, y1) in (b if isinstance(b, list) else [b])]
                 for r, b in boxes.items()}
    for r, bl in sorted(boxes.items()):
        o.append(f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "s6_fence_{r}"]')
        for (x0, y0, x1, y1) in (bl if isinstance(bl, list) else [bl]):
            o.append(f"odb::dbBox_create $::lpf_r [expr {{round({x0}*$::lpf_dbu)}}] [expr {{round({y0}*$::lpf_dbu)}}] "
                     f"[expr {{round({x1}*$::lpf_dbu)}}] [expr {{round({y1}*$::lpf_dbu)}}]")
        o.append(f'set ::lpf_g({r}) [odb::dbGroup_create $::lpf_r "s6_fence_grp_{r}"]')
    soft = {i: r for r, l in SOFT.items() for i in l}
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
          "  puts \"S6_FENCE $r cells=$::lpf_n($r)\"",
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
CK = {"ck_r_fw": ("W", 1284), "ck_r_fe": ("E", 1284), "ck_r_stm": ("S", 1640), "ck_r_ctl": ("S", 1462),
      "ck_r_sc": ("S", 2120), "ck_r_su": ("W", BAND_Y0 + 900.0), "ck_r_tap": ("N", HC_X[2] - 16),
      **{f"ck_r_st{k}": ("S", STN_X[k // 2] + (200.0 if k % 2 == 0 else 2.0)) for k in range(8)},
      **{f"ck_r_hc{c}": ("N", HC_X[c] + 1.0 if c != 1 else HC_X[c] + 452.0) for c in range(4)}}


def port_widths():
    t = (ROOT / f"{g6.OUT_DIR}/{TOP}.sv").read_text()
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
            k["at"] = [snap(W - k["at"][0] - from_lef(k["view"]), 43.2), k["at"][1]]   # W = 94 x 43.2 - 0.024: back on the lattice
            k["orient"] = flipo[k["orient"]]
        for m in mac:
            mw = float(re.search(r"SIZE ([\d.]+) BY", (ROOT / m["view"] / (Path(m["view"]).name + ".lef")).read_text()).group(1))
            m["at"] = [round(math.floor((W - m["at"][0] - mw) / 0.432 + 1e-6) * 0.432, 3), m["at"][1]]   # macro x lattice 0.432
            m["orient"] = "MY"
    run_s6 = "bash rtl/test/qwen_dv/s5/run_s6.sh"
    benches = [
        dict(name="s6_lp_lockstep_mut0", cmd=f"SPEC={LPN} {run_s6} {{RUN}}/lp lp 0", expect="pass",
             pass_regex="LP_LOCKSTEP PASS", threads=16, peak_ram_gb=64, needs=["verilator"]),
        dict(name="s6_lp_mut1_bypass", cmd=f"SPEC={LPN} {run_s6} {{RUN}}/lp1 lp 1", expect="fail",
             fail_regex="LP_LOCKSTEP FAIL", threads=16, peak_ram_gb=64, needs=["verilator"]),
        dict(name="s6_lint", cmd=f"SPEC={LPN} {run_s6} {{RUN}}/lint lint", expect="pass", pass_regex=f"LINT {TOP}: errors=0",
             threads=4, peak_ram_gb=16, needs=["verilator"]),
    ]
    vm8 = "u_suvm.u_vm8q = HARD (" + VM8Q_VIEW + ")" if VM8Q_VIEW else ("u_suvm.u_vm8q glue SOFT (its 7 split leaves hard at the "
          "qfd_dv_slice2_vm8q P3 child layout; vm8q / vm8qb gates running, no view yet)")
    checklist = {
        "1_pins": "PASS (parent): every input port lands in its face / entry region (pin register in fdn / fup, or the landing "
                  "ring at the pin for fn / frs entries); every output leaves from a face-region flop. rst_n -> lp reset runs "
                  f"(depth {rec['reset']['depth']}, last stage = regional_reset_copies <= 32 loads) -> each leaf's own 2-stage "
                  "landing (s6 face / tap leaves: second stage = kept copies <= 32 loads; closed children: their own landing). "
                  "OPEN: the 182 slice<->slice face landings (plan claude/qw-slice4-face-1019) are NOT in this parent yet.",
        "2_reach": "OPEN / measured by the gate: cross-region nets are landings (" + ("E=2: <= ~1.3 mm per landing window"
                   if not GEOB else "E=4: <= ~2.6 mm per landing window") + "); the face<->face pass crossings (fdn <-> fup "
                   f"now {W - 2 * 259.2:.0f} um: chu_q, hr, cmd, chd, treq, l9) EXCEED that window after the enlargement -> "
                   "next GEN: a relay pad stage on those landings (lp pads, priced) or the D8/E4 fallback; the N<->S corridor "
                   "(rs_n, cw_s 2.2 mm) unchanged; SU gb/pd1 group relay su8 -> lrly <= ~1.2 mm (r_su region: single-cycle "
                   "reach measured by the gate textbook, lrly RD relays); 1-bit reset runs hop <= 405 um (lp reach)",
        "3_fanout": "PASS by construction (parent glue): landing_chunk_bits 24 (kept per-chunk selectors: the e5 census "
                    "rc[1]/exp_ 6,275 / sel 3,135 per landing is gone), > 32-chunk landings on ot_pl_land_split (rsi per 32 "
                    "chunks), regional_reset_copies (kept copies <= 32), s6 face/tap leaves valid-only reset with kept copies; "
                    "the pre-gate census of THIS kit is the proof (README census table)",
        "4_depth": "PASS (parent): wires only between children; landing read = registered slot select",
        "5_storage": "PASS: every SRAM / ROM inside a hard child (VM8 split leaves 18 SRAM, btab_s4 4 SRAM, tload ns4 4 ROM); "
                     f"landing rings D={rec['D']} are fixed-latency landings ({rec['flops']['landing']} flops)",
        "6_floorplan": f"PASS (plan): ENLARGED IN Y {W:.3f} x {H:.3f} (QW2-NEXTGEN reticle slot: +1684.8 VM8 band = VM8 group + "
                       "su8 + 8 lane relays; same area as the 4060.8 x 2592 COORD slot); hard children on "
                       "the 43.2 lattice (8 stnrgc, 8 heads, 24 SFU, 8 lrly, ctl5, su8, stream, tload, btab_s4, 7 VM8 leaves), "
                       "no parent macros; relay channels <= 405 um apart; parent pins "
                       f"<= {max(dens.values()):.2f}/um per port group",
        "7_clock": f"multiple_cts_roots: {len(rec['regions'])} regional roots (ck_r_*), entry on the nearest face beside the "
                   "region's register mass; fences hold every soft leaf + its landing read halves; judged per region at child "
                   "flops (TT / FF spread <= 80); io_hold_margin 0.03",
        "8_schedule": "static; compiler record " + REC + ": every cross-region reader pin +" + str(rec["E"] + 1) + " edges "
                      "(lp lag_pins, slice loops); leaf HARD registers as s5 (ctl bundles / VM writes / own word / ag, stm tw, "
                      "fdn pc_bad, tap cid); closed children: SU8 command visible +4 / reset +1 (Codex 5949f90af record), VM8 P3 "
                      "VM reads/writes +1 vs P2 (+0 vs vm8fh on VM reads, +2 BTAB/PROG, +4 CROM), reset +2; stream c3r +1 a "
                      "pass/tap, -1 own write; tload ns4 CAPTURE_STAGE 1; s6 face/tap leaves +0 (reset release edge unchanged); "
                      "landing chunks / reset copies / split landings +0 edges",
        "stand_ins": "SOFT in this kit: sc, red, xhead x4 (successor kits: QW-S5-SCRED / QW-S5-XHEAD), x leaves x32 (w130 view "
                     "legacy M6 abstract, pocket LEF owed), fdn / fup / tap (s6 census-safe leaves, no kit yet), " + vm8,
    }
    hard_masters = sorted({Path(k["view"]).name for k in kids})
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
        route=dict(pd=0.45, threads=32, peak_ram_gb=256, macro_halo_um=5.4, pin_h="M4 M6", pin_v="M3 M5",
                   hold_margin_ns=0.03, io_hold_margin_ns=0.03, synth_keep_modules=KEEP),
        recipe=4, inhold=False, outhold=False,
        io_flop_at_pins={"cols": 4, "allow_none": True},
        pin_regs=dict(enable=False, reason="landed parent: every input port is a face-leaf pin register or a landing ring at "
                      "the pin; every output is a face-region flop; lp.py lag / offsets are the compiler record"),
        reset_landing=dict(enable=False, reason=f"rst_n feeds the lp reset runs (depth {rec['reset']['depth']}, priced as boot "
                           "release, last stage kept copies <= 32 loads); each leaf lands its rst_n in 2 more stages"),
        safe_design_checklist=checklist,
        pin_density_per_um=dens,
        hard_child_masters=hard_masters,
        why_floorplan="w5 plan (results/arch/qw_slice5_1019) + VM8 band: S band station / btab_s4 | stream+tload / ctl5 / sc, "
                      "pass channel, VM8 band (group + su8 + lane relay row), SU block 2 cells | centre | 2 cells, tap row, "
                      "head band 4 columns at pitch 475.2; dn face W (slice2_w face map); tall reticle slot 2462.4 x 4276.8",
        landed=dict(record=REC, landings=len(rec["landings"]), landing_flops=rec["flops"]["landing"],
                    reset_depth=rec["reset"]["depth"], lp_spec=LP_SPEC, D=rec["D"], E=rec["E"],
                    landing_chunk_bits=24, regional_reset_copies=True),
        structural_change="QW2-SLICE2 10-21 tall slot 2462.4 x 4276.8 (reticle) of the w6 design; w6: successor of the e5/e5b census FAIL -- CLOSED children bound "
                          "(su8_rst3, stream c3r, tload ns4, ctl5, btab_s4, lrly, VM8 split leaves), census-safe landing "
                          "library (chunk 24 + reset copies + split landings), valid-only-reset face/tap leaves, outline "
                          "enlarged for the VM8 group + lrly strips; variant " + V +
                          {"a": ": D4/E2 landings (+3 a crossing), lrly view", "b": ": D8/E4 landings (+5 a crossing), "
                           "lrlyb view, left-half lane cells mirrored, write halves fenced at the source",
                           "e": ": E master (MY mirror of w7)", "f": ": E master of the fallback (MY mirror of w7b)"}[V],
        pin_hook_before_flops=[fen],
        job=dict(owner="Claude:QW2-SLICE2", branch="claude/qw2-slice2-tall-1021", tag="t1" + V,
                 purpose="QW2-SLICE2: slice2 W/E master, tall reticle slot 2462.4 x 4276.8, with closed children (CRITICAL: coordinator review before any route)",
                 views_to=f"physical/ref_tile/{NAME}/views", record_to=f"results/rtl/ref_tile/{NAME}",
                 hold_merge="CRITICAL qfd_dv_slice2 prefix: coordinator PNG review first; soft leaves pending their views",
                 extra_paths=["rtl/qwen_dv", "rtl/hdc", "rtl/common/landed_parent", "rtl/lib", "rtl/qwen_sys/dvm_20261014",
                              "rtl/test", "rtl/physical", "tools/landed_parent", "tools/qwen_dv",
                              "physical/asap7_memory_macros_v2", "physical/asap7_memory_macros/ot_rom_4096x266_m8",
                              *sorted({str(Path(k["view"]).parent) for k in kids}), VM8Q_KIT,
                              "physical/hbm_accel_die_views/stations/bench", g6.REC_DIR],
                 benches=benches))
    out = ROOT / f"{SPEC_DIR}/{NAME}.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out.relative_to(ROOT), len(placed), "pins; max density", max(dens.values()), "/um;", len(kids), "children,",
          len(mac), "macros;", len(dom), "clock domains")


if __name__ == "__main__":
    main()
