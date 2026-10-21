#!/usr/bin/env python3
"""S81-COLLECT2/LEPENH 10-21: LANDED-REGIONS rebuild of the MU72 E-end parent dsdv_slice_lepe_nh (s_7S), DIAGNOSTIC stand-in kits

  s81sl_lepenh_lra (MAIN)      slot 2851.2 x 6825.6 (G3 lepe MU72 slot), channel 172.8, K street 86.4, PD 0.45
  s81sl_lepenh_lrb (FALLBACK)  slot 3024.0 x 6825.6 (+172.8 enlarged, no squeeze), channel 259.2, K street 129.6, PD 0.40

Top ot_s81sl_slice_lepe_nh_mu_lr_lp = tools/landed_parent/lp.py on spec tools/landed_parent/specs/dsdv_slice_lepe_nh_mu_lr.json:
THREE local regions (S = slice | K = lep_mu_a + 2 lane_e_safe8_ntf, abutting | ML = dsdv_mu_land, the die master's ck_ML), every
crossing landed (8 rings D4/E2 chunk 8: line 1104 b each way, sl_f, ml_w 1+1104, ml_r 1+1104+1), regional reset ports rst_n_<r>
(no reset root, no cross-region reset hop: fixes d1a/d3a u_lpr_root -19.6/-48.6 ns and d3b undeclared u_lpr_root->u_lpr_K),
each landed by a fixed-depth forest on its own clock (DEPTH 7 = 5 registered prefix hops fenced along a street <= ~405 um apart,
branch, leaf per landing chunk; reset only on control/valid, ring data unreset).

Floorplan (findings FAM-S81-LEPENH 1-3):
  * u_lep in the E-end orientation at the slice ro_e/ri_e height (y 2592), line pins bit-aligned across the channel;
  * lanes E of the endpoint with their W faces abutting it (43.2 um), split about the endpoint centre line by a K STREET that
    carries every small K port (rst_n_K, ck_K, ch_b, mu_c, mu_rc, mu_rt, fault) straight from the E face to the endpoint's
    E-face control window -- no detour round a lane;
  * u_land (ML) N of the endpoint with a 129.6 gap holding the K->ML / ML->K rings;
  * ONE fence box per landing group beside the face it serves (S box at the slice E face, K box at the endpoint W face, K-N box
    at the endpoint N face, ML box at the land S face), plus one small box per reset prefix stage along its street; all fences
    RELEASED after global placement, before DPL + CTS (tools/landed_parent/lp_fence_release.tcl, pslice r10 lesson).
Stand-ins carry STANDIN_NOT_A_VIEW: never bind, never submit (slice k8/cap5r, lep_mu_a r6, lane s8n views still closing).
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D1A = ROOT / "physical/ref_tile/s81sl_lepenhmu_d1a"
TOP = "ot_s81sl_slice_lepe_nh_mu_lr_lp"
LP_SV = f"rtl/dsrom_sys/s81_dv/slice/landed/lepe_nh_mu_lr/{TOP}.sv"
RECORD = f"results/rtl/s81_lepenh_lr_1021/lp/{TOP}_record.json"
LANE_TOP, LEP_TOP = "dsfd_coll_lane_e_safe8_ntf", "ot_s81sl_lep_mu_a"
LAND_VIEW = "physical/ref_tile/dsdv_mu_land/views/dsdv_mu_land"
INS = {"ot_s81sl_slice": "250,200,330", LEP_TOP: "220,170,290", LANE_TOP: "419,347,537"}
H = 6825.6
SL_X, SL_Y, SL_W, SL_H = 43.2, 43.2, 1252.8, 6739.2       # k8 slice envelope (G3)
LEP_W, LEP_H, LEP_Y = 475.2, 561.6, 2592.0
LANE_W, LANE_H = 725.76, 583.2
LAND_W, LAND_H = 475.2, 216.0
CTRL = [237.6, 324.0]                                    # endpoint-local E-face control window (= the K street)
LANE_PR = {"rx": [2.16, 288.36], "tx": [290.52, 576.72], "lo_d": [2.16, 274.32], "lo_v": [276.48, 277.56],
           "lo_r": [278.64, 279.72], "chb": [280.8, 282.96], "ck": [298.08, 300.24], "rs": [302.4, 304.56],
           "li_v": [306.72, 307.8], "li_r": [308.88, 309.96], "flt": [312.12, 315.36], "li_d": [317.52, 581.04]}
STAGES = 7          # lp regional_reset_ports stages (forest DEPTH): 5 prefix hops + branch + leaf


def run(*a):
    subprocess.run([sys.executable, *map(str, a)], check=True, cwd=ROOT)


def geom(v):
    # street = 21.6 + k*43.2 so both lanes stay on the 43.2 lattice (lane height 583.2 = 13.5 x 43.2)
    ch, street, w, ln0 = (172.8, 108.0, 2851.2, 2246.4) if v == "a" else (259.2, 151.2, 3024.0, 2203.2)
    lep_x = SL_X + SL_W + ch
    lane_x = lep_x + LEP_W + 43.2
    ln1 = round(ln0 + LANE_H + street, 1)
    mid = ln0 + LANE_H + street / 2                           # K street centre line (abs y); covers the lep control window
    land_y = LEP_Y + LEP_H + 129.6
    return dict(v=v, ch=ch, street=street, W=w, lep_x=lep_x, lane_x=lane_x, mid=mid, ln0_y=ln0, ln1_y=ln1, land_y=land_y)


def chain(poly, n=5):
    """n registered reset prefix stages spread evenly along a polyline (first at the pin end, last at the landing box)."""
    seg = [((x0, y0), (x1, y1), abs(x1 - x0) + abs(y1 - y0)) for (x0, y0), (x1, y1) in zip(poly, poly[1:])]
    tot = sum(s[2] for s in seg)
    out = []
    for k in range(n):
        d = tot * k / (n - 1)
        for (x0, y0), (x1, y1), L in seg:
            if d <= L + 1e-6:
                f = d / L if L else 0
                out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
                break
            d -= L
    return out, tot / (n - 1)


def slice_standin():
    s = json.load(open(D1A / "standin/slice.json"))
    s["outline"] = {"w": SL_W, "h": SL_H}
    s["_note"] = ("S81-COLLECT2/LEPENH stand-in (DIAGNOSTIC) of the slice at the k8 envelope 1252.8 x 6739.2; pin REQUEST: E-face "
                  "ro_e/ri_e bit-aligned with the endpoint window (lep y 2592), clk/rst_n/fault just below it.")
    return s


def lep_standin():
    s = json.load(open(D1A / "standin/lep.json"))
    s["name"] = f"standin_{LEP_TOP}"
    lane0 = ["lo0_v", "lo0_r", "lo0_d", "li0_v", "li0_r", "li0_d"]
    lane1 = ["lo1_v", "lo1_r", "lo1_d", "li1_v", "li1_r", "li1_d"]
    ctrl = ["l0_f", "rxv", "clk", "rst_n", "mu_c", "mu_rt", "l1_f"]
    s["pins"]["E"] = lane0 + ctrl + lane1
    pr = {k: v for k, v in s["pin_ranges"].items() if k not in ("clk", "rst_n", "mu_c", "mu_rt")}
    # lane0 bundle in the lower half (toward lane 0), lane1 bundle in the upper half, control in the street window
    pr.update({"lo0_d": [2.0, 115.0], "lo0_v": [115.5, 116.0], "lo0_r": [116.5, 117.0], "li0_v": [117.5, 118.0],
               "li0_r": [118.5, 119.0], "li0_d": [120.0, 235.0],
               "l0_f": [238.0, 241.0], "rxv": [242.0, 244.0], "clk": [246.0, 252.0], "rst_n": [254.0, 258.0],
               "mu_c": [260.0, 290.0], "mu_rt": [291.0, 318.0], "l1_f": [319.0, 322.0],
               "lo1_d": [326.0, 440.0], "lo1_v": [440.5, 441.0], "lo1_r": [441.5, 442.0], "li1_v": [442.5, 443.0],
               "li1_r": [443.5, 444.0], "li1_d": [445.0, 559.0]})
    s["pin_ranges"] = pr
    s["_note"] = ("S81-COLLECT2/LEPENH stand-in (DIAGNOSTIC, STANDIN_NOT_A_VIEW) of lep_mu_a 475.2 x 561.6, E-end orientation. Pin "
                  "REQUEST for the real view: ro/ri W bit-aligned across the channel; E face = lane0 bundle (lower) | control "
                  "window clk/rst_n/mu_c/mu_rt/faults at local y 237.6-324 facing the parent K street | lane1 bundle (upper); "
                  "ml_* N under the dsdv_mu_land S-face pins; sl_f at the S channel corner.")
    return s


def lane_standin():
    return {"name": f"standin_{LANE_TOP}", "top": LANE_TOP, "sources": ["rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv"],
            "clock_port": "ck", "defines": ["OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF"], "outline": {"w": LANE_W, "h": LANE_H},
            "pins": {"E": ["rx", "tx"], "W": ["lo_v", "lo_r", "lo_d", "li_v", "li_r", "li_d", "flt", "ck", "rs", "chb"]},
            "pin_ranges": dict(LANE_PR),
            "_note": "stand-in (DIAGNOSTIC) of dsfd_coll_lane_e_safe8_ntf at the dscoll_lane_e_s8n outline 725.76 x 583.2."}


def fences(g):
    """(region key, box um, [regexps of instance-name prefixes]) -- first match wins; read halves pull their mux cone."""
    lx, ch, W = g["lep_x"], g["ch"], g["W"]
    sx0 = SL_X + SL_W + 5.4
    half = (ch - 11.8) / 2
    y0, y1 = LEP_Y - 43.2, LEP_Y + LEP_H
    gapx = g["lane_x"] - 21.6                                 # 43.2 column between endpoint/land and the lanes
    F = [("S", (sx0, y0, sx0 + half, y1), [r"u_lpl_(0_r|1_w|2_w)[./]"]),
         ("Kw", (sx0 + half + 1.0, y0, lx - 5.4, y1), [r"u_lpl_(0_w|1_r|2_r)[./]"]),
         ("Kn", (lx, y1 + 5.4, lx + LEP_W, y1 + 48.6), [r"u_lpl_(3_r|4_r|5_r|6_w|7_w)[./]"]),
         ("ML", (lx, g["land_y"] - 48.6, lx + LAND_W, g["land_y"] - 5.4), [r"u_lpl_(3_w|4_w|5_w|6_r|7_r)[./]"])]
    sy, my, ky = g["ln0_y"] - 40.0, g["ln1_y"] + LANE_H + 30.0, g["mid"]
    kgap = y1 + (g["land_y"] - y1) / 2                        # between the Kn and ML boxes
    polys = {"S": [(W - 60, sy), (lx - ch / 2, sy), (lx - ch / 2, y0 - 60)],
             "K": [(W - 60, ky), (gapx, ky), (gapx, kgap - 10.8), (lx + LEP_W / 2, kgap - 10.8)],
             "ML": [(W - 60, my), (gapx, my), (gapx, g["land_y"] - 21.6)]}
    hops = {}
    for r, poly in polys.items():
        pts, hop = chain(poly)
        hops[r] = round(hop, 1)
        for k, (x, y) in enumerate(pts):
            F.append((f"r{r}{k}", (round(x - 10.8, 3), round(y - 10.8, 3), round(x + 10.8, 3), round(y + 10.8, 3)),
                      [rf"u_lpr_{r}[./]g_prefix\[{k}\][./]"]))
    return F, hops


def fence_tcl(name, F):
    o = [f"# generated by tools/s81_slice/mk_lepenh_lr_kits.py ({name}): PRE_GLOBAL_PLACE landed-region fences (landing halves",
         "# beside the faces they serve, read halves + their mux cones, regional reset prefix hops along their streets);",
         "# released after GPL by tools/landed_parent/lp_fence_release.tcl (before DPL / CTS).",
         "set ::lpf_blk [ord::get_db_block]", "set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]",
         "array set ::lpf_g {}", "array set ::lpf_n {}", "array set ::lpf_c {}", "set ::lpf_rules {}"]
    for r, (x0, y0, x1, y1), pats in F:
        o.append(f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_{r}"]')
        o.append(f"odb::dbBox_create $::lpf_r [expr {{round({x0}*$::lpf_dbu)}}] [expr {{round({y0}*$::lpf_dbu)}}] "
                 f"[expr {{round({x1}*$::lpf_dbu)}}] [expr {{round({y1}*$::lpf_dbu)}}]")
        o.append(f'set ::lpf_g({r}) [odb::dbGroup_create $::lpf_r "lp_fence_grp_{r}"]')
        for p in pats:
            o.append("lappend ::lpf_rules [list {^" + p + "} " + r + "]")
    o += ["proc lpf_seq {m} {",
          "  foreach mt [$m getMTerms] { if {[$mt getSigType] eq \"CLOCK\"} { return 1 } }",
          "  return 0", "}",
          "set ::lpf_reads {}",
          "foreach i [$::lpf_blk getInsts] {",
          "  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne \"CORE\"} continue",
          "  if {[$i getGroup] ne \"NULL\"} continue",
          "  regsub -all {\\\\} [$i getName] {} n",
          "  foreach rule $::lpf_rules {",
          "    lassign $rule re r",
          "    if {[regexp $re $n]} {",
          "      $::lpf_g($r) addInst $i; incr ::lpf_n($r)",
          "      if {[regexp {^u_lpl_[0-9]+_r} $n] && [lpf_seq [$i getMaster]]} { lappend ::lpf_reads [list $i $r] }",
          "      break", "    }", "  }", "}",
          "foreach ir $::lpf_reads {",
          "  lassign $ir i r", "  set front [list $i]",
          "  for {set d 0} {$d < 16 && [llength $front]} {incr d} {",
          "    set nxt {}",
          "    foreach x $front {",
          "      foreach it [$x getITerms] {",
          "        if {![$it isInputSignal] || [[$it getMTerm] getSigType] eq \"CLOCK\"} continue",
          "        set net [$it getNet]",
          "        if {$net eq \"NULL\" || [$net getSigType] ne \"SIGNAL\"} continue",
          "        foreach dt [$net getITerms] {",
          "          if {![$dt isOutputSignal]} continue",
          "          set di [$dt getInst]", "          set dm [$di getMaster]",
          "          if {[$dm isBlock] || [$dm getType] ne \"CORE\" || [$di getGroup] ne \"NULL\" || [lpf_seq $dm]} continue",
          "          $::lpf_g($r) addInst $di; incr ::lpf_c($r); lappend nxt $di",
          "        }", "      }", "    }", "    set front $nxt", "  }", "}",
          "foreach r {" + " ".join(r for r, _b, _p in F) + "} {",
          "  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error \"LP_FENCE: fence $r got no cells\" }",
          "  if {![info exists ::lpf_c($r)]} { set ::lpf_c($r) 0 }",
          "  puts \"LP_FENCE $r cells=$::lpf_n($r) read_cone=$::lpf_c($r)\"", "}"]
    return "\n".join(o) + "\n"


def off(r, y):
    return [round(r[0] + y, 3), round(r[1] + y, 3)]


def build(name, v):
    g = geom(v)
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    views = {}
    for f, (m, s) in {"slice.json": ("ot_s81sl_slice", slice_standin()), "lep.json": (LEP_TOP, lep_standin()),
                      "lane.json": (LANE_TOP, lane_standin())}.items():
        json.dump(s, open(kd / "standin" / f, "w"), indent=1)
        out = kd / "standin_views" / m
        run(ROOT / "tools/qwen_dv/slice_standin.py", "--ins", INS[m], "--master", m, kd / "standin" / f, out.parent)
        views[m] = str(out.relative_to(ROOT))
    s = json.load(open(D1A / "spec.json"))
    s["name"], s["top"] = name, TOP
    s["sources"] = [LP_SV, "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
                    "rtl/common/landed_parent/ot_pl_land_reset_forest.sv"] + [f"{views[m]}/{m}_bb.v" for m in ("ot_s81sl_slice", LEP_TOP, LANE_TOP)]
    s["landed_record"] = RECORD
    s["clock_port"], s["clock_ports"] = "ck_S", ["ck_S", "ck_K", "ck_ML"]
    s["reset_ports"] = ["rst_n_S", "rst_n_K", "rst_n_ML"]
    s["reset_landing"] = {"enable": False, "reason": (f"the lp.py RTL lands every regional reset port: rst_n_<r> has ONE sink, u_lpr_<r> = "
                          f"ot_pl_land_reset_forest DEPTH {STAGES} on ck_<r> ({STAGES - 2} registered prefix hops fenced along the region's "
                          "street, branch, one leaf per landing chunk); no reset root, no cross-region reset path; a kit landing would add unpriced edges")}
    s["outline"] = {"w": g["W"], "h": H, "exact": True}
    lx = g["lep_x"]
    s["children"] = [{"view": views["ot_s81sl_slice"], "count": 1, "inst": "u_sl", "at": [SL_X, SL_Y]},
                     {"view": views[LEP_TOP], "count": 1, "inst": "u_lep", "at": [lx, LEP_Y]},
                     {"view": LAND_VIEW, "count": 1, "inst": "u_land", "at": [lx, g["land_y"]]},
                     {"view": views[LANE_TOP], "count": 1, "inst": "u_ln0", "at": [g["lane_x"], g["ln0_y"]]},
                     {"view": views[LANE_TOP], "count": 1, "inst": "u_ln1", "at": [g["lane_x"], g["ln1_y"]]}]
    d1 = s["pin_ranges"]
    ns = {k: d1[k] for k in ("bi", "bo", "xc", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "vi", "vo", "ri_w", "ro_w")}
    m, st = g["mid"], g["street"]
    sy, my = g["ln0_y"] - 40.0, g["ln1_y"] + LANE_H + 30.0
    lk = {"rst_n_S": [sy - 6, sy - 2], "ck_S": [sy + 2, sy + 8],
          "rx0": off(LANE_PR["rx"], g["ln0_y"]), "tx0": off(LANE_PR["tx"], g["ln0_y"]),
          "fault": [m - st / 2 + 4, m - st / 2 + 7], "mu_rt": [m - st / 2 + 9, m - 8], "rst_n_K": [m - 6, m - 3],
          "ck_K": [m - 1.5, m + 1.5], "ch_b": [m + 3, m + 5], "mu_c": [m + 7, m + st / 2 - 14], "mu_rc": [m + st / 2 - 12, m + st / 2 - 4],
          "rx1": off(LANE_PR["rx"], g["ln1_y"]), "tx1": off(LANE_PR["tx"], g["ln1_y"]),
          "rst_n_ML": [my - 6, my - 2], "ck_ML": [my + 2, my + 8]}
    order = ["rst_n_S", "ck_S", "rx0", "tx0", "fault", "mu_rt", "rst_n_K", "ck_K", "ch_b", "mu_c", "mu_rc", "rx1", "tx1", "rst_n_ML", "ck_ML"]
    s["pins"] = {"W": ["ri_w", "ro_w"], "N": ["sid", "vi", "vo"], "E": order, "S": s["pins"]["S"]}
    s["pin_ranges"] = {**ns, **lk}
    ced = s["clock_entry_domains"]
    ced["core"] = dict(ced["core"], ports=["ck_S"], inputs=["rst_n_S", "sid", "ri_w", "vi", "bi", "rt"])
    ced["lk"] = dict(ced["lk"], ports=["ck_K"], inputs=["rst_n_K", "ch_b", "rx0", "rx1", "mu_c", "mu_rc"],
                     outputs=["tx0", "tx1", "fault", "mu_rt"])
    ced["ml"] = {"ratio": [1, 1], "ports": ["ck_ML"], "inputs": ["rst_n_ML"], "outputs": []}
    s["route"] = dict(s["route"], pd=0.45 if v == "a" else 0.40)
    fz = f"physical/ref_tile/{name}/lr_fences.tcl"
    F, hops = fences(g)
    (ROOT / fz).write_text(fence_tcl(name, F))
    s["pin_hook_before_flops"] = [fz]
    s["pre_dpl_extra"] = ["tools/landed_parent/lp_fence_release.tcl"]
    s["landed"] = {"record": RECORD, "lp_spec": "tools/landed_parent/specs/dsdv_slice_lepe_nh_mu_lr.json", "landings": 8,
                   "landing_flops": 33776, "reset_depth": STAGES, "regions": ["S", "K", "ML"]}
    s["slot_change_request"] = (None if v == "a" else
                                "FALLBACK: lepe MU72 slot 2851.2 -> 3024.0 wide (+172.8 = channel 259.2 + street 129.6), height 6825.6 unchanged")
    s["structural_change"] = (
        f"S81-COLLECT2/LEPENH 10-21 {name}: LANDED-REGIONS rebuild of dsdv_slice_lepe_nh MU (DIAGNOSTIC stand-ins, never bindable). "
        "d1a/d1b/d3a/d3b FAILED: one ck_S/ck_K tree each over 10k soft ring flops (spread 275-1143 ps) + one reset root u_lpr_root "
        "across the 2.8x5.8 mm slot (in->reg -19.6/-48.6 ns, undeclared S->K reset crossing). Now: 3 regions S/K/ML with own roots, "
        "regional reset ports (no root, no cross-region reset), fixed-depth forest with fenced registered prefix hops, ring halves "
        "fenced beside the faces they serve (released before CTS), lanes abutting the endpoint split by a K street for the K control "
        f"ports; slot {g['W']} x {H}, channel {g['ch']}, street {g['street']}, PD {s['route']['pd']}.")
    s["safe_design_checklist"] = {
        "1_pins": "children register their pins; parent inputs land on a child pin register or a ring/forest stage; outputs leave a ring read / child register / fault out_regs 2",
        "2_reach": f"line 1104 b x2 bit-aligned across the channel (<= channel width); lane<->endpoint bundles abut (43.2 um, <= 340 um skew); K control ports run straight down the K street (~0.9 mm repeated, endpoint pin-registered: OPEN, gate measures); reset prefix hops fenced, mean hop S {hops['S']} / K {hops['K']} / ML {hops['ML']} um",
        "3_fanout": "lp chunk 8 rings + forest leaf per chunk (<= 32 loads); in-gate native census decides",
        "4_depth": "ring read = 4:1 slot mux + chunk decode; no deep logic in the parent",
        "5_storage": "WAIVED rings (landing contract D=4)",
        "6_floorplan": f"children on the 43.2 lattice, std-cell bands = channel + streets; slot {g['W']} x {H}",
        "7_clock": "3 local roots ck_S / ck_K / ck_ML, each tree = its children's clock pins + its fenced ring halves; every crossing landed (no S/K/ML phase alignment needed)",
        "8_reset": f"regional rst_n_S/K/ML, forest DEPTH {STAGES} on its own clock, release on one die edge (+{STAGES} edges, compiler record); reset on control/valid only"}
    j = s["job"]
    j.update(owner="Claude:S81-COLLECT2/LEPENH", branch="claude/s81-lepenh-lr-1021", tag=name.split("_")[-1],
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
             extra_paths=["results/rtl/s81_lepenh_lr_1021/lp"])
    sp = kd / "spec.json"
    json.dump(s, open(sp, "w"), indent=1)
    run(ROOT / "tools/ref_tile/ref_tile.py", "gen", sp.relative_to(ROOT))


if __name__ == "__main__":
    for v in sys.argv[1:] or ("a", "b"):
        build(f"s81sl_lepenh_lr{v}", v)
