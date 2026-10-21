#!/usr/bin/env python3
"""S81-SLICE/ENDP 10-21: LANDED-REGIONS kits of the selected72 MU end parents (DIAGNOSTIC stand-in gates, never submit).

    mk_mu72_lr_kits.py [lepw_mab_mu lepw_mu lepe_mu]     -> physical/ref_tile/s81sl_endp_<tag>{a,b}

  a = MAIN     slot 2851.2 x 6825.6 (G8 end slot), lp E 2 (rings +3), PD 0.45
  b = FALLBACK slot 3024.0 x 6825.6 (+172.8 into the line channel), lp E 3 (rings +4: 3 T bank reach), PD 0.40
Top ot_s81sl_slice_<f>_lr{a,b}_lp (tools/s81_slice/mk_mu72_lr.py; regions S / K / ML / P, regional reset ports, see
mu72_lr_geom.py).  Floorplan: lep endpoint at the slice line height with its line face across the channel from the slice
line face (W end: lep R0 W of the slice; E end: lep drawn MY E of the slice), lanes ABUT the endpoint lane face (51.84),
MU land beside the lep ML face, P port group at the parent face in the lane street (mab: ln2/ln3 gap), host group (lepe_mu)
below lane 0.  One fence box per landing group beside the face it serves, five reset prefix boxes per region along its
street; all fences released after GPL, before DPL / CTS (tools/landed_parent/lp_fence_release.tcl).
Stand-ins carry STANDIN_NOT_A_VIEW (slice cap5r_lp, lep_mu_*, lane safe8_ntf views not closed): never bind, never submit.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mu72_lr_geom import geom, H, SL_W, SL_H, LANE_W, LANE_H, LAND_W, LAND_H   # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mk_lepenh_lr_kits import chain, fence_tcl, LANE_PR   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D1A = ROOT / "physical/ref_tile/s81sl_lepenhmu_d1a"
TAG = {"lepw_mab_mu": "wmab", "lepw_mu": "w", "lepe_mu": "e"}
LAND_VIEW = "physical/ref_tile/dsdv_mu_land/views/dsdv_mu_land"
SLICE = "ot_s81sl_slice_c1x_k8_cap5r_lp"
XCK = ["ck_L0", "ck_L1", "ck_L3", "ck_L4", "ck_CAP_RT", "ck_CAP_CW", "ck_CAP_CE", "ck_CAP_RN", "ck_CAP_RS"]
INS = {SLICE: "250,200,330", "lep": "220,170,290", "lane": "419,347,537"}
LEP_LINE_LOCAL = {"ot_s81sl_lep_mu_ab": (520.0, 1380.0), "ot_s81sl_lep_mu_a": (5.0, 385.0), "ot_s81sl_lep_mu_h": (5.0, 385.0)}
STAGES = 10


def run(*a):
    subprocess.run([sys.executable, *map(str, a)], check=True, cwd=ROOT)


def rec(f, v):
    return json.load(open(ROOT / f"results/rtl/s81_endp_1021/lp/ot_s81sl_slice_{f}_lr{v}_lp_record.json"))


def slice_standin(g):
    d = json.load(open(D1A / "standin/slice.json"))
    lw = g["side"] == "w"
    lo, hi = (g["lep_xy"][1] + a for a in LEP_LINE_LOCAL[g["lep"]])     # slice line pins bit-aligned with the lep line pins
    lo, hi = lo - 43.2, hi - 43.2
    mid = (lo + hi) / 2
    line = ["ri_w", "ro_w"] if lw else ["ri_e", "ro_e"]          # the face toward the channel
    outer = ["ri_e", "ro_e"] if lw else ["ri_w", "ro_w"]
    # ro_* (slice out) feeds the lep ri (upper half of the lep line band); ri_* (slice in) from the lep ro (lower half)
    pr = {k: v for k, v in d["pin_ranges"].items() if k in ("bi", "bo", "xc", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "vi", "vo")}
    pr.update({line[0]: [lo, mid - 1], line[1]: [mid + 1, hi], "fault": [lo - 12, lo - 8], "rst_n": [lo - 20, lo - 16],
               "ck_C": [lo - 34, lo - 24], outer[0]: [2160.0, 2851.2], outer[1]: [2851.2, 3542.4]})
    for k, c in enumerate(XCK):
        pr[c] = [2084.0 + 8 * k, 2088.0 + 8 * k]
    faces = {"N": d["pins"]["N"], "S": d["pins"]["S"]}
    faces["W" if lw else "E"] = ["ck_C", "rst_n", "fault"] + line
    faces["E" if lw else "W"] = XCK + outer
    return {"name": f"standin_{SLICE}", "top": SLICE,
            "sources": ["rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv"],
            "clock_port": "ck_C", "outline": {"w": SL_W, "h": SL_H}, "pins": faces, "pin_ranges": pr,
            "_note": ("S81-SLICE/ENDP stand-in (DIAGNOSTIC) of the end slice c1x_k8_cap5r_lp at 1252.8 x 6739.2 (single ck_C timing; the "
                      "nine other real roots are plain pins here). Pin REQUEST for the real view: line pins on the channel face "
                      "bit-aligned with the lep line pins, roots/reset on the outer face.")}


def lep_standin(g, f):
    lep, lw, lh = g["lep"], g["lep_w"], g["lep_h"]
    if lep == "ot_s81sl_lep_mu_ab":       # = the s81sl_lepmu_t5c kit pins (gating; R0 at the W end)
        t5 = json.load(open(ROOT / "physical/ref_tile/s81sl_lepmu_t5c/spec.json"))
        pins, pr = t5["pins"], t5["pin_ranges"]
    else:                                 # = the r6v / r6g kit face assignment, ranges made explicit
        ln0 = ["lo0_v", "lo0_r", "lo0_d", "li0_v", "li0_r", "li0_d"]
        ln1 = ["lo1_v", "lo1_r", "lo1_d", "li1_v", "li1_r", "li1_d"]
        lane_face = ln0 + ln1 + ["rxv", "l0_f", "l1_f"] + (["l0_st", "l1_st"] if lep.endswith("_h") else []) + ["clk", "rst_n"]
        pr = {"lo0_d": [4.0, 124.0], "lo0_v": [124.5, 125.0], "lo0_r": [125.5, 126.0], "li0_v": [126.5, 127.0],
              "li0_r": [127.5, 128.0], "li0_d": [129.0, 249.0], "lo1_d": [262.0, 382.0], "lo1_v": [382.5, 383.0],
              "lo1_r": [383.5, 384.0], "li1_v": [384.5, 385.0], "li1_r": [385.5, 386.0], "li1_d": [387.0, 507.0],
              "rxv": [251.0, 252.0], "l0_f": [252.5, 254.0], "l1_f": [254.5, 256.0], "clk": [256.5, 258.5], "rst_n": [259.0, 260.5],
              "ro": [5.0, 195.0], "ri": [195.0, 385.0], "mu_c": [388.0, 450.0], "mu_rt": [452.0, 515.0],
              "ml_wd": [4.0, 270.0], "ml_rd": [272.0, 538.0], "ml_wv": [540.0, 541.0], "ml_rv": [542.0, 543.0], "ml_f": [544.0, 545.0],
              "sl_f": [4.0, 8.0], "fault": [10.0, 14.0]}
        if lep.endswith("_h"):
            pr.update({"l0_st": [260.8, 261.4], "l1_st": [261.6, 262.0], "t_host": [20.0, 80.0], "t_kd": [82.0, 125.0],
                       "f_host": [127.0, 480.0], "f_lf": [482.0, 486.0], "f_ks": [488.0, 540.0]})
        pins = {"W": lane_face, "E": ["ro", "ri", "mu_c", "mu_rt"], "N": ["ml_wd", "ml_rd", "ml_wv", "ml_rv", "ml_f"],
                "S": ["sl_f", "fault"] + (["t_host", "t_kd", "f_host", "f_lf", "f_ks"] if lep.endswith("_h") else [])}
    if g["side"] == "e":                  # drawn in the placed MY orientation: E <-> W, x mirrored on N / S
        pins = {{"E": "W", "W": "E"}.get(k, k): v for k, v in pins.items()}
        ns = set(pins.get("N", []) + pins.get("S", []))
        pr = {k: ([round(lw - b, 3), round(lw - a, 3)] if k in ns else [a, b]) for k, (a, b) in pr.items()}
    return {"name": f"standin_{lep}", "top": lep, "sources": ["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv"],
            "clock_port": "clk", "outline": {"w": lw, "h": lh}, "pins": pins, "pin_ranges": pr,
            "_note": (f"S81-SLICE/ENDP stand-in (DIAGNOSTIC, STANDIN_NOT_A_VIEW) of {lep} {lw} x {lh}"
                      f"{' drawn MY (E end)' if g['side'] == 'e' else ''}: line pins face the slice across the channel, lane "
                      "pins face the abutting lanes, ml_* face the MU land.")}


def lane_standin(g):
    m = f"dsfd_coll_lane_{g['side']}_safe8_ntf"
    inner = ["lo_v", "lo_r", "lo_d", "li_v", "li_r", "li_d", "flt", "ck", "rs", "chb"]
    pins = {"W": inner, "E": ["rx", "tx"]} if g["side"] == "e" else {"E": inner, "W": ["rx", "tx"]}
    return {"name": f"standin_{m}", "top": m, "sources": ["rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv"],
            "clock_port": "ck", "outline": {"w": LANE_W, "h": LANE_H}, "pins": pins, "pin_ranges": dict(LANE_PR),
            "_note": f"stand-in (DIAGNOSTIC) of {m} at the s8n outline 725.76 x 583.2; lo/li face the endpoint, rx/tx the parent face."}


def off(r, y):
    return [round(r[0] + y, 3), round(r[1] + y, 3)]


def layout(g, R):
    """parent pins + fences from the geometry and the lp record (landing index -> net / regions)."""
    W, lw = g["W"], g["side"] == "w"
    lx, ly = g["lep_xy"]
    LW, LH = g["lep_w"], g["lep_h"]
    sx = g["sl"][0]
    lanes = g["lanes"]
    p0, p1 = g["pstreet"]
    # ---- parent pins (absolute y on E / W faces)
    lane_face, sl_face = ("W", "E") if lw else ("E", "W")
    lk, order = {}, []
    host = g["f"] == "lepe_mu"
    if host:
        hy = lanes[0] - 250.0
        for p, n in (("t_host", 77), ("t_kd", 54), ("f_host", 515), ("f_lf", 4), ("f_ks", 53)):
            lk[p] = [round(hy, 2), round(hy + n * 0.33, 2)]
            hy += n * 0.33 + 1.0
            order.append(p)
    small = [("rst_n_K", 2), ("ck_K", 3), ("ch_b", 1), ("rst_n_P", 2), ("ck_P", 3), ("mu_c", 34), ("mu_rc", 11), ("mu_rt", 32), ("fault", 1)]
    gap = p1 - p0
    step = (gap - 6.0) / sum(n + 1 for _, n in small)
    y = p0 + 3.0
    smallr = {}
    for p, n in small:
        smallr[p] = [round(y, 3), round(y + n * step, 3)]
        y += (n + 1) * step
    for i, yy in enumerate(lanes):
        lk[f"rx{i}"], lk[f"tx{i}"] = off(LANE_PR["rx"], yy), off(LANE_PR["tx"], yy)
    lk.update(smallr)
    land_x, land_y = g["land_xy"]
    top = max(lanes[-1] + LANE_H, land_y + LAND_H) + 20.0
    lk.update({"rst_n_ML": [top, top + 4], "ck_ML": [top + 8, top + 14]})
    for i, yy in enumerate(lanes):
        order += [f"rx{i}", f"tx{i}"]
        if i == len(lanes) // 2 - 1 and g["f"] != "lepw_mab_mu":
            order += [p for p, _ in small]
        if g["f"] == "lepw_mab_mu" and i == 2:
            order += [p for p, _ in small]
    order += ["rst_n_ML", "ck_ML"]
    d1 = json.load(open(D1A / "spec.json"))["pin_ranges"]
    dx = sx - 43.2
    ns = {k: off(d1[k], dx) for k in ("bi", "bo", "xc", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "vi", "vo")}
    outer = ["ri_e", "ro_e"] if lw else ["ri_w", "ro_w"]
    chx = (lx + LW + sx) / 2 if lw else (sx + SL_W + lx) / 2          # channel centre (S face, free column)
    sk = {outer[0]: [2203.2, 2894.4], outer[1]: [2894.4, 3585.6], "rst_n_S": [chx - 12, chx - 8], "ck_S": [chx - 4, chx + 4]}
    for k, c in enumerate(XCK):
        sk[c] = [2127.2 + 8 * k, 2131.2 + 8 * k]
    sface = ["bi", "bo", "xc", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt"]
    pins = {lane_face: order, sl_face: XCK + outer, "N": ["sid", "vi", "vo"],
            "S": (["rst_n_S", "ck_S"] + sface) if not lw else (["rst_n_S", "ck_S"] + sface)}
    pr = {**ns, **lk, **sk}
    # ---- fences
    if lw:
        cx0, cx1 = lx + LW + 5.4, sx - 5.4            # channel between lep E face and slice W face
        k_box_x, s_box_x = (cx0, (cx0 + cx1) / 2 - 0.5), ((cx0 + cx1) / 2 + 0.5, cx1)
        pbx = (5.0, 39.0)
    else:
        cx0, cx1 = sx + SL_W + 5.4, lx - 5.4
        s_box_x, k_box_x = (cx0, (cx0 + cx1) / 2 - 0.5), ((cx0 + cx1) / 2 + 0.5, cx1)
        pbx = (W - 39.0, W - 5.0)
    l0, l1 = (ly + a for a in LEP_LINE_LOCAL[g["lep"]])
    by0, by1 = l0 - 43.2, max(l1, ly + LH * 0.98) + 43.2
    lep_top, land_bot = ly + LH, land_y
    boxes = {"S": (s_box_x[0], by0, s_box_x[1], by1), "K": (k_box_x[0], by0, k_box_x[1], by1),
             "Kn": (lx + 5.4, lep_top + 5.4, lx + LW - 5.4, lep_top + 48.6),
             "ML": (land_x + 5.4, land_bot - 48.6, land_x + LAND_W - 5.4, land_bot - 5.4),
             "P": (pbx[0], p0 + 1.0, pbx[1], p1 - 1.0)}
    rules = {k: [] for k in boxes}
    if host:
        boxes["Kh"] = (lx + 5.4, ly - 48.6, lx + LW - 5.4, ly - 5.4)
        rules["Kh"] = []
        boxes["Ph"] = (pbx[0], lanes[0] - 252.0, pbx[1], lanes[0] - 8.0)
        rules["Ph"] = []
    for L in R["landings"]:
        n, net = L["name"], L["net"]
        rs = next(x for x in R["compiler"]["rescheduled_nets"] if x["net"] == net)
        sr, dr = rs["src_region"], rs["dst_region"]

        def box(region, end):
            if region == "S":
                return "S"
            if region == "ML":
                return "ML"
            if region == "P":
                return "Ph" if net in ("t_host", "t_kd") else "P"
            # K end: line + mu_c at the lep line face, ML traffic at the lep N face, host at the lep S face
            if net in ("t_host", "t_kd"):
                return "Kh"
            if sr == "ML" or dr == "ML":
                return "Kn"
            return "K"
        rules[box(sr, "w")].append(rf"u_lpl_{n}_w[./]")
        rules[box(dr, "r")].append(rf"u_lpl_{n}_r[./]")
    F = [(k, tuple(round(c, 3) for c in boxes[k]), v) for k, v in rules.items() if v]
    # ---- reset prefix chains: from each region's reset pin to its main box
    fx = 0.0 if lw else W
    inward = 60.0 if lw else -60.0
    rpin = {r: (pr[f"rst_n_{r}"][0] + pr[f"rst_n_{r}"][1]) / 2 for r in ("K", "ML")}
    col = (lanes and (g["lane_x"] + LANE_W + lx) / 2) if lw else (lx + LW + g["lane_x"]) / 2   # lane <-> lep 51.84 column
    kbx = (k_box_x[0] + k_box_x[1]) / 2
    ym = (p0 + p1) / 2                                # lane street / gap centre line
    if g["f"] == "lepw_mab_mu":
        around = lep_top + 60.0                       # above the lep, below the Kn box row / land
        kpoly = [(fx + 1.5 * inward, ym), (col, ym), (col, around), (kbx, around), (kbx, by1 + 25)]
    else:
        below = ly - 75.0                             # below the lep (clear of the host Kh box), lane 0 is W/E of the column
        kpoly = [(fx + 1.5 * inward, ym), (col, ym), (col, below), (kbx, below), (kbx, by0 - 25)]
    xe = land_x + LAND_W + 25.0
    polys = {"S": [(chx, 30.0), (chx, by0 - 25)],
             "K": kpoly,
             "ML": [(fx + inward, rpin["ML"]), (xe, rpin["ML"]), (xe, land_bot - 27)]}
    # P: the port-entry region sits at the face (its forest is local; no prefix fences)
    hops = {}
    for r, poly in polys.items():
        pts, hop = chain(poly, STAGES - 2)
        hops[r] = round(hop, 1)
        for k, (x, yy) in enumerate(pts):
            F.append((f"r{r}{k}", (round(x - 10.8, 3), round(yy - 10.8, 3), round(x + 10.8, 3), round(yy + 10.8, 3)),
                      [rf"u_lpr_{r}[./]g_prefix\[{k}\][./]"]))
    return pins, pr, F, hops


def build(f, v):
    g = geom(f, v)
    R = rec(f, v)
    name = f"s81sl_endp_{TAG[f]}{v}"
    top = f"ot_s81sl_slice_{f}_lr{v}_lp"
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    sts = {SLICE: (slice_standin(g), INS[SLICE]), g["lep"]: (lep_standin(g, f), INS["lep"])}
    ln = lane_standin(g)
    sts[ln["top"]] = (ln, INS["lane"])
    views = {}
    for m, (s, ins) in sts.items():
        sp = kd / "standin" / f"{m}.json"
        json.dump(s, open(sp, "w"), indent=1)
        out = kd / "standin_views" / m
        run(ROOT / "tools/qwen_dv/slice_standin.py", "--ins", ins, "--master", m, sp, out.parent)
        views[m] = str(out.relative_to(ROOT))
    s = json.load(open(D1A / "spec.json"))
    s["name"], s["top"] = name, top
    s["sources"] = [f"rtl/dsrom_sys/s81_dv/slice/mu72/lr/{top}.sv", "rtl/common/landed_parent/ot_pl_land.sv",
                    "rtl/common/landed_parent/ot_pl_land_field_copies.sv", "rtl/common/landed_parent/ot_pl_land_reset_forest.sv",
                    "rtl/common/landed_parent/ot_pl_land_kept_enable.sv"] + [f"{views[m]}/{m}_bb.v" for m in views]
    s["defines"] = json.load(open(ROOT / f"physical/ref_tile/s81_mu72_assembly/{f}.json"))["defines"]
    rpath = f"results/rtl/s81_endp_1021/lp/{top}_record.json"
    s["landed_record"] = rpath
    s["clock_port"], s["clock_ports"] = "ck_S", ["ck_S", "ck_K", "ck_ML", "ck_P"]
    s["reset_ports"] = ["rst_n_S", "rst_n_K", "rst_n_ML", "rst_n_P"]
    s["reset_landing"] = {"enable": False, "reason": (f"the lp.py RTL lands every regional reset port: rst_n_<r> has ONE sink, u_lpr_<r> = "
                          f"ot_pl_land_reset_forest DEPTH {STAGES} on ck_<r> ({STAGES - 2} registered prefix hops fenced along the region's "
                          "street, branch, one leaf per landing chunk); no reset root, no cross-region reset path")}
    s["outline"] = {"w": g["W"], "h": H, "exact": True}
    lx, ly = g["lep_xy"]
    s["children"] = ([{"view": views[SLICE], "count": 1, "inst": "u_sl", "at": list(g["sl"])},
                      {"view": views[g["lep"]], "count": 1, "inst": "u_lep", "at": [lx, ly]},
                      {"view": LAND_VIEW, "count": 1, "inst": "u_land", "at": list(g["land_xy"])}] +
                     [{"view": views[ln["top"]], "count": 1, "inst": f"u_ln{i}", "at": [g["lane_x"], y]} for i, y in enumerate(g["lanes"])])
    pins, pr, F, hops = layout(g, R)
    s["pins"], s["pin_ranges"] = pins, pr
    nl = len(g["lanes"])
    host = f == "lepe_mu"
    line_in, line_out = ("ri_e", "ro_e") if g["side"] == "w" else ("ri_w", "ro_w")
    s["clock_entry_domains"] = {
        "core": {"ratio": [1, 1], "ports": ["ck_S"], "inputs": ["rst_n_S", "sid", line_in, "vi", "bi", "rt"] + XCK,
                 "outputs": [line_out, "vo", "bo", "xc", "ck_line", "ck_v", "ck_xc", "ck_rt"]},
        "lk": {"ratio": [1, 1], "ports": ["ck_K"], "inputs": ["rst_n_K", "ch_b"] + [f"rx{i}" for i in range(nl)],
               "outputs": [f"tx{i}" for i in range(nl)] + ["fault", "mu_rt"] + (["f_host", "f_lf", "f_ks"] if host else [])},
        "ml": {"ratio": [1, 1], "ports": ["ck_ML"], "inputs": ["rst_n_ML"], "outputs": []},
        "p": {"ratio": [1, 1], "ports": ["ck_P"], "inputs": ["rst_n_P", "mu_c", "mu_rc"] + (["t_host", "t_kd"] if host else []), "outputs": []}}
    s["route"] = dict(s["route"], pd=0.45 if v == "a" else 0.40)
    fz = f"physical/ref_tile/{name}/lr_fences.tcl"
    (ROOT / fz).write_text(fence_tcl(name, F).replace("mk_lepenh_lr_kits.py", "mk_mu72_lr_kits.py"))
    s["pin_hook_before_flops"] = [fz]
    s["pre_dpl_extra"] = ["tools/landed_parent/lp_fence_release.tcl"]
    fl = R["flops"]
    s["landed"] = {"record": rpath, "lp_spec": f"tools/landed_parent/specs/mu72_{f}_lr{v}.json", "landings": len(R["landings"]),
                   "flops": fl, "reset_depth": STAGES, "regions": ["S", "K", "ML", "P"], "E": g["E"]}
    s["slot_change_request"] = None if v == "a" else f"FALLBACK: {f} end slot 2851.2 -> 3024.0 wide (+172.8 line channel), height 6825.6"
    s["structural_change"] = (
        f"S81-SLICE/ENDP 10-21 {name}: LANDED-REGIONS rebuild of the selected72 MU end parent {f} (G8 die source; DIAGNOSTIC "
        "stand-ins, never bindable). d1a/d1b/d3a/lepenhmu d1 FAILED: one ck_S/ck_K tree over the 2.8x5.8 mm slot (CTS pin spread "
        "275-1143 ps) + one reset root u_lpr_root (in->reg -19.6/-48.6 ns). Now 4 regions S/K/ML/P with own roots, regional reset "
        "ports (no root), fixed-depth forests with fenced prefix hops, every crossing a D4 chunk-8 ring fenced beside its face, "
        "lanes abutting the endpoint, P port group landed at the face, outputs through 3 OREG relay stages; "
        f"slot {g['W']} x {H}, channel {g['ch']}, lp E {g['E']}, PD {s['route']['pd']}.")
    s["safe_design_checklist"] = {
        "1_pins": "children register their pins; every input lands on a ring writer / forest stage / child pin register; outputs leave a child register or 3 OREG relay stages",
        "2_reach": f"line 1104 b x2 bit-aligned across the {g['ch']} um channel; lanes abut the endpoint (51.84 um); face->endpoint control/host runs = ring bank wires (multicycle E={g['E']} T) for inputs, 3 relay stages (~4 hops <= ~400 um) for outputs; reset prefix hops fenced, mean S {hops['S']} / K {hops['K']} / ML {hops['ML']} um (P local at the face)",
        "3_fanout": "chunk-8 kept-enable rings + forest leaf per chunk (<= 32 loads); in-gate native census decides",
        "4_depth": "ring read = 4:1 slot mux + chunk decode; no parent logic beyond rings / relays",
        "5_storage": "WAIVED rings (landing contract D=4)",
        "6_floorplan": f"children on the 43.2 lattice; std-cell bands = channel + lane street + free area; slot {g['W']} x {H}; PD {s['route']['pd']}",
        "7_clock": "4 local roots ck_S / ck_K / ck_ML / ck_P, each tree = own children's clock pins + own fenced ring halves; every crossing landed; u_sl's 9 other real roots pass straight to the slice (single-ck stand-in here)",
        "8_reset": f"regional rst_n_S/K/ML/P, forest DEPTH {STAGES} on its own clock (+{STAGES} edges at release, one die edge), reset on control/valid only"}
    j = s["job"]
    j.update(owner="Claude:S81-SLICE/ENDP", branch="claude/s81-endp-1021", tag=name.split("_")[-1],
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
             extra_paths=["results/rtl/s81_endp_1021/lp"])
    sp = kd / "spec.json"
    json.dump(s, open(sp, "w"), indent=1)
    run(ROOT / "tools/ref_tile/ref_tile.py", "gen", sp.relative_to(ROOT))
    return name, g, hops, F


if __name__ == "__main__":
    for f in sys.argv[1:] or ("lepw_mab_mu", "lepw_mu", "lepe_mu"):
        for v in ("a", "b"):
            name, g, hops, F = build(f, v)
            print(name, g["W"], "E", g["E"], "hops", hops, "fences", len(F))
