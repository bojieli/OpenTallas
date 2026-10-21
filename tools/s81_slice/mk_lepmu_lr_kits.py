#!/usr/bin/env python3
"""S81-ELEM/ENDP 10-21: LANDED-REGIONS DIAGNOSTIC stand-in kits of the MU72 end parents lepe_mu_72 (s_7N) and lepw_mu_72 (s_0S),
the recipe of tools/s81_slice/mk_lepenh_lr_kits.py (s81sl_lepenh_lra/lrb, dsdv_slice_lepe_nh MU) applied to both ends:

  s81sl_lepemu_lra / lrb   ot_s81sl_slice_lepe_mu_lr_lp  E end: slice | lep_mu_h (+ host plane) + dsdv_mu_land | 2 lane_e_safe8_ntf
  s81sl_lepwmu_lra / lrb   ot_s81sl_slice_lepw_mu_lr_lp  W end: 2 lane_w_safe8_ntf | lep_mu_a + dsdv_mu_land | slice  (x-mirror)
  a = MAIN slot 2851.2 x 6825.6 (channel 172.8, K street 108, PD 0.45); b = FALLBACK 3024.0 (+172.8 enlarged, PD 0.40).

Tops = tools/landed_parent/lp.py on tools/landed_parent/specs/dsdv_slice_lep{e,w}_mu_lr.json: THREE local regions S (slice) /
K (endpoint + lanes) / ML (dsdv_mu_land, the die master's ck_ML), every crossing landed (8 rings D4/E2 chunk 8), regional reset
ports rst_n_S/K/ML with 7-stage forests (5 fenced registered prefix hops along each region's street), ring halves fenced
beside the faces they serve (boxes derived from the lp record), released after GPL (lp_fence_release.tcl, before DPL/CTS).
mu_rc (read only by u_land) is an ML-domain input pinned beside rst_n_ML / ck_ML (the lepenh lr b8b9de033 OT_MULTI_ROOT lesson).
E end adds the host plane (t_host 77 / t_kd 54 in, f_host 515 / f_lf 4 / f_ks 53 out, K domain): parent pins on the K face
BELOW lane 0 (y ln0-330 .. ln0-60), endpoint pins on its S face; that run (~1 mm) is OPEN = the gate measures it.
W end = exact x-mirror of the E plan, except u_land stays R0 (an MY flip puts its LEF pins off the asap7 tracks), so the
endpoint's N-face ml_* ranges stay un-mirrored under the land's S-face pins (LEP_W == LAND_W, same x).
Stand-ins carry STANDIN_NOT_A_VIEW: never bind, never submit.
"""
import copy, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/s81_slice"))
import mk_lepenh_lr_kits as B          # noqa: E402  (geometry, stand-ins, chain, fence_tcl of the reviewed lepenh lr kits)

REC_DIR = "results/rtl/s81_endp_lr_1021/lp"
LAND_VIEW = B.LAND_VIEW
H = B.H
HOST_IN, HOST_OUT = ["t_host", "t_kd"], ["f_host", "f_lf", "f_ks"]


def cfg(side):
    return dict(side=side, top=f"ot_s81sl_slice_lep{side}_mu_lr_lp",
                lep="ot_s81sl_lep_mu_h" if side == "e" else "ot_s81sl_lep_mu_a",
                lane=f"dsfd_coll_lane_{side}_safe8_ntf",
                spec=f"tools/landed_parent/specs/dsdv_slice_lep{side}_mu_lr.json",
                sv=f"rtl/dsrom_sys/s81_dv/slice/landed/lep{side}_mu_lr/ot_s81sl_slice_lep{side}_mu_lr_lp.sv",
                record=f"{REC_DIR}/ot_s81sl_slice_lep{side}_mu_lr_lp_record.json")


def mxr(r, w):
    return [round(w - r[1], 3), round(w - r[0], 3)]


def swap_faces(pins):
    sw = {"E": "W", "W": "E", "N": "N", "S": "S"}
    return {sw[f]: v for f, v in pins.items()}


def mirror_standin(s, w, keep=()):
    """x-mirror a stand-in: E<->W faces (y ranges kept), N/S ranges mirrored by the outline width (except `keep` pins)."""
    s = copy.deepcopy(s)
    ns = set(s["pins"].get("N", [])) | set(s["pins"].get("S", []))
    s["pins"] = swap_faces(s["pins"])
    s["pin_ranges"] = {k: (mxr(v, w) if k in ns and k not in keep else v) for k, v in s["pin_ranges"].items()}
    return s


def lep_standin(c):
    s = B.lep_standin()
    s["top"], s["name"] = c["lep"], f"standin_{c['lep']}"
    if c["side"] == "e":                     # lep_mu_h: lane status pins + host plane on the S face
        s["pins"]["E"] = ["l0_st"] + s["pins"]["E"] + ["l1_st"]
        s["pin_ranges"].update({"l0_st": [0.6, 1.6], "l1_st": [559.6, 560.6]})
        s["pins"]["S"] = ["sl_f", "f_host", "f_lf", "f_ks", "t_host", "t_kd", "fault"]
        s["pin_ranges"].update({"f_host": [160.0, 330.0], "f_lf": [331.0, 333.0], "f_ks": [334.0, 352.0],
                                "t_host": [354.0, 390.0], "t_kd": [391.0, 450.0]})
        s["_note"] += " lep_mu_h: l0_st/l1_st at the lane-bundle ends, host plane f_host/f_lf/f_ks/t_host/t_kd on S (x 160-450)."
        return s
    s = mirror_standin(s, B.LEP_W, keep=("ml_f", "ml_rv", "ml_wv", "ml_rd", "ml_wd"))
    s["_note"] += " W END: x-mirrored (line face E, lane face W); ml_* kept R0 under the R0 dsdv_mu_land."
    return s


def slice_standin(c):
    s = B.slice_standin()
    if c["side"] == "e":
        return s
    # W end: endpoint on the slice W face (slice ri_w/ro_w = lri/lro), parent line on the slice E face (ri_e/ro_e)
    pr = s["pin_ranges"]
    ren = {"ro_e": "ro_w", "ri_e": "ri_w", "ri_w": "ri_e", "ro_w": "ro_e"}
    m = mirror_standin(s, B.SL_W)
    m["pins"] = {f: [ren.get(p, p) for p in v] for f, v in m["pins"].items()}
    m["pin_ranges"] = {ren.get(k, k): v for k, v in m["pin_ranges"].items()}
    m["_note"] = s["_note"] + " W END: x-mirrored; W face = rst_n/clk/fault + ro_w/ri_w (to the endpoint), E face = ri_e/ro_e (die line)."
    return m


def lane_standin(c):
    s = B.lane_standin()
    s["top"], s["name"] = c["lane"], f"standin_{c['lane']}"
    if c["side"] == "w":
        s = mirror_standin(s, B.LANE_W)
        s["_note"] = s["_note"].replace("dsfd_coll_lane_e_safe8_ntf", c["lane"]) + " W END: x-mirrored (rx/tx on W, lane-side bundle on E)."
    return s


def fences(g, c):
    lx, ch, W = g["lep_x"], g["ch"], g["W"]
    sx0 = B.SL_X + B.SL_W + 5.4
    half = (ch - 11.8) / 2
    y0, y1 = B.LEP_Y - 43.2, B.LEP_Y + B.LEP_H
    gapx = g["lane_x"] - 21.6
    box = lambda reg, peer: {"S": "S", "ML": "ML"}.get(reg) or ("Kw" if peer == "S" else "Kn")
    halves = {"S": [], "Kw": [], "Kn": [], "ML": []}
    for L in json.load(open(ROOT / c["record"]))["landings"]:
        halves[box(L["src_region"], L["dst_region"])].append(f'{L["name"]}_w')
        halves[box(L["dst_region"], L["src_region"])].append(f'{L["name"]}_r')
    rx = lambda k: [r"u_lpl_(" + "|".join(sorted(halves[k])) + r")[./]"]
    F = [("S", (sx0, y0, sx0 + half, y1), rx("S")),
         ("Kw", (sx0 + half + 1.0, y0, lx - 5.4, y1), rx("Kw")),
         ("Kn", (lx, y1 + 5.4, lx + B.LEP_W, y1 + 48.6), rx("Kn")),
         ("ML", (lx, g["land_y"] - 48.6, lx + B.LAND_W, g["land_y"] - 5.4), rx("ML"))]
    sy, my, ky = g["ln0_y"] - 40.0, g["ln1_y"] + B.LANE_H + 30.0, g["mid"]
    kgap = y1 + (g["land_y"] - y1) / 2
    polys = {"S": [(W - 60, sy), (lx - ch / 2, sy), (lx - ch / 2, y0 - 60)],
             "K": [(W - 60, ky), (gapx, ky), (gapx, kgap - 10.8), (lx + B.LEP_W / 2, kgap - 10.8)],
             "ML": [(W - 60, my), (gapx, my), (gapx, g["land_y"] - 21.6)]}
    hops = {}
    for r, poly in polys.items():
        pts, hop = B.chain(poly)
        hops[r] = round(hop, 1)
        for k, (x, y) in enumerate(pts):
            F.append((f"r{r}{k}", (round(x - 10.8, 3), round(y - 10.8, 3), round(x + 10.8, 3), round(y + 10.8, 3)),
                      [rf"u_lpr_{r}[./]g_prefix\[{k}\][./]"]))
    if c["side"] == "w":
        F = [(r, (round(W - x1, 3), y0_, round(W - x0, 3), y1_), p) for r, (x0, y0_, x1, y1_), p in F]
    return F, hops


def build(name, side, v):
    c = cfg(side)
    g = B.geom(v)
    W = g["W"]
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    views = {}
    for f, (m, s) in {"slice.json": ("ot_s81sl_slice", slice_standin(c)), "lep.json": (c["lep"], lep_standin(c)),
                      "lane.json": (c["lane"], lane_standin(c))}.items():
        json.dump(s, open(kd / "standin" / f, "w"), indent=1)
        out = kd / "standin_views" / m
        ins = B.INS.get(m) or B.INS[B.LEP_TOP if m.startswith("ot_s81sl_lep") else B.LANE_TOP]
        B.run(ROOT / "tools/qwen_dv/slice_standin.py", "--ins", ins, "--master", m, kd / "standin" / f, out.parent)
        views[m] = str(out.relative_to(ROOT))
    s = json.load(open(B.D1A / "spec.json"))
    s["name"], s["top"] = name, c["top"]
    s["sources"] = [c["sv"], "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_field_copies.sv",
                    "rtl/common/landed_parent/ot_pl_land_reset_forest.sv",
                    "rtl/common/landed_parent/ot_pl_land_kept_enable.sv"] + [f"{views[m]}/{m}_bb.v" for m in ("ot_s81sl_slice", c["lep"], c["lane"])]
    s["landed_record"] = c["record"]
    s["clock_port"], s["clock_ports"] = "ck_S", ["ck_S", "ck_K", "ck_ML"]
    s["reset_ports"] = ["rst_n_S", "rst_n_K", "rst_n_ML"]
    s["reset_landing"] = {"enable": False, "reason": (f"the lp.py RTL lands every regional reset port: rst_n_<r> has ONE sink, u_lpr_<r> = "
                          f"ot_pl_land_reset_forest DEPTH {B.STAGES} on ck_<r> ({B.STAGES - 2} registered prefix hops fenced along the region's "
                          "street, branch, one leaf per landing chunk); no reset root, no cross-region reset path; a kit landing would add unpriced edges")}
    s["outline"] = {"w": W, "h": H, "exact": True}
    lx = g["lep_x"]
    at = {"u_sl": ([B.SL_X, B.SL_Y], B.SL_W), "u_lep": ([lx, B.LEP_Y], B.LEP_W), "u_land": ([lx, g["land_y"]], B.LAND_W),
          "u_ln0": ([g["lane_x"], g["ln0_y"]], B.LANE_W), "u_ln1": ([g["lane_x"], g["ln1_y"]], B.LANE_W)}
    if side == "w":
        # mirrored left edges snapped DOWN to the 43.2 lattice (lane 725.76 wide is not a lattice multiple: 138.24 -> 129.6,
        # lane-to-endpoint gap 51.84 instead of 43.2); every other child already lands on the lattice
        at = {k: ([round(int(round((W - p[0] - w) / 43.2, 6)) * 43.2, 3), p[1]], w) for k, (p, w) in at.items()}
    vw = {"u_sl": views["ot_s81sl_slice"], "u_lep": views[c["lep"]], "u_land": LAND_VIEW, "u_ln0": views[c["lane"]], "u_ln1": views[c["lane"]]}
    s["children"] = [{"view": vw[i], "count": 1, "inst": i, "at": at[i][0]} for i in ("u_sl", "u_lep", "u_land", "u_ln0", "u_ln1")]
    d1 = s["pin_ranges"]
    ns = {k: d1[k] for k in ("bi", "bo", "xc", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "vi", "vo", "ri_w", "ro_w")}
    m, st = g["mid"], g["street"]
    sy, my = g["ln0_y"] - 40.0, g["ln1_y"] + B.LANE_H + 30.0
    lk = {"rst_n_S": [sy - 6, sy - 2], "ck_S": [sy + 2, sy + 8],
          "rx0": B.off(B.LANE_PR["rx"], g["ln0_y"]), "tx0": B.off(B.LANE_PR["tx"], g["ln0_y"]),
          "fault": [m - st / 2 + 4, m - st / 2 + 7], "mu_rt": [m - st / 2 + 9, m - 8], "rst_n_K": [m - 6, m - 3],
          "ck_K": [m - 1.5, m + 1.5], "ch_b": [m + 3, m + 5], "mu_c": [m + 7, m + st / 2 - 4],
          "rx1": B.off(B.LANE_PR["rx"], g["ln1_y"]), "tx1": B.off(B.LANE_PR["tx"], g["ln1_y"]),
          "rst_n_ML": [my - 6, my - 2], "ck_ML": [my + 2, my + 8], "mu_rc": [my + 10, my + 18]}
    order = ["rst_n_S", "ck_S", "rx0", "tx0", "fault", "mu_rt", "rst_n_K", "ck_K", "ch_b", "mu_c", "rx1", "tx1", "rst_n_ML", "ck_ML", "mu_rc"]
    if side == "e":           # host plane below lane 0 (703 pins over 270 um = 2.6 /um), toward the endpoint S face
        h0 = g["ln0_y"] - 330.0
        hp = {"f_host": [h0, h0 + 197.0], "f_lf": [h0 + 199.0, h0 + 201.0], "f_ks": [h0 + 203.0, h0 + 223.0],
              "t_host": [h0 + 225.0, h0 + 245.0], "t_kd": [h0 + 247.0, h0 + 270.0]}
        lk.update({k: [round(a, 3), round(b, 3)] for k, (a, b) in hp.items()})
        order = ["f_host", "f_lf", "f_ks", "t_host", "t_kd"] + order
    line_in, line_out = ("ri_w", "ro_w") if side == "e" else ("ri_e", "ro_e")
    if side == "e":
        s["pins"] = {"W": ["ri_w", "ro_w"], "N": ["sid", "vi", "vo"], "E": order, "S": s["pins"]["S"]}
        s["pin_ranges"] = {**ns, **lk}
    else:
        nsm = {k: (mxr(r, W) if k not in ("ri_w", "ro_w") else r) for k, r in ns.items()}
        nsm["ri_e"], nsm["ro_e"] = nsm.pop("ri_w"), nsm.pop("ro_w")
        s["pins"] = {"E": ["ri_e", "ro_e"], "N": ["sid", "vi", "vo"], "W": order, "S": s["pins"]["S"]}
        s["pin_ranges"] = {**nsm, **lk}
    ced = s["clock_entry_domains"]
    ced["core"] = dict(ced["core"], ports=["ck_S"], inputs=["rst_n_S", "sid", line_in, "vi", "bi", "rt"],
                       outputs=[line_out, "vo", "bo", "xc", "ck_line", "ck_v", "ck_xc", "ck_rt"])
    ced["lk"] = dict(ced["lk"], ports=["ck_K"], inputs=["rst_n_K", "ch_b", "rx0", "rx1", "mu_c"] + (HOST_IN if side == "e" else []),
                     outputs=["tx0", "tx1", "fault", "mu_rt"] + (HOST_OUT if side == "e" else []))
    ced["ml"] = {"ratio": [1, 1], "ports": ["ck_ML"], "inputs": ["rst_n_ML", "mu_rc"], "outputs": []}
    s["route"] = dict(s["route"], pd=0.45 if v == "a" else 0.40)
    fz = f"physical/ref_tile/{name}/lr_fences.tcl"
    F, hops = fences(g, c)
    (ROOT / fz).write_text(B.fence_tcl(name, F).replace("mk_lepenh_lr_kits.py", "mk_lepmu_lr_kits.py"))
    s["pin_hook_before_flops"] = [fz]
    s["pre_dpl_extra"] = ["tools/landed_parent/lp_fence_release.tcl"]
    s["landed"] = {"record": c["record"], "lp_spec": c["spec"], "landings": 8, "landing_flops": 33776, "reset_depth": B.STAGES,
                   "regions": ["S", "K", "ML"]}
    s["slot_change_request"] = (None if v == "a" else
                                f"FALLBACK: lep{side} MU72 slot 2851.2 -> 3024.0 wide (+172.8 = channel 259.2 + street 151.2), height 6825.6 unchanged")
    s["structural_change"] = (
        f"S81-ELEM/ENDP 10-21 {name}: LANDED-REGIONS rebuild of dsdv_slice_lep{side}_mu (MU72 {'E end s_7N' if side == 'e' else 'W end s_0S'}; "
        "DIAGNOSTIC stand-ins, never bindable) = the s81sl_lepenh_lr{a,b} recipe: d1a/d1b had one ck_S/ck_K tree each over the soft "
        "ring flops + one reset root across the 2.8 mm slot. Now 3 regions S/K/ML with own roots, regional reset ports, fenced forests, "
        "ring halves fenced beside the faces they serve (released before CTS), lanes abutting the endpoint split by a K street; mu_rc in ML; "
        f"{'host plane below lane 0; ' if side == 'e' else 'x-mirror of the E plan (land R0); '}slot {W} x {H}, channel {g['ch']}, "
        f"street {g['street']}, PD {s['route']['pd']}.")
    s["safe_design_checklist"] = {
        "1_pins": "children register their pins; parent inputs land on a child pin register or a ring/forest stage; outputs leave a ring read / child register / fault out_regs 2",
        "2_reach": f"line 1104 b x2 bit-aligned across the channel; lanes abut the endpoint; K control ports straight down the K street (~0.9 mm repeated, endpoint pin-registered: OPEN, gate measures); mu_rc/rst_n_ML ~1.4 mm to the land (OPEN){'; host plane ~1 mm under lane 0 to the endpoint S face (OPEN)' if side == 'e' else ''}; reset prefix hops mean S {hops['S']} / K {hops['K']} / ML {hops['ML']} um",
        "3_fanout": "lp chunk 8 rings + forest leaf per chunk (<= 32 loads); in-gate native census decides",
        "4_depth": "ring read = 4:1 slot mux + chunk decode; no deep logic in the parent",
        "5_storage": "WAIVED rings (landing contract D=4)",
        "6_floorplan": f"children on the 43.2 lattice, std-cell bands = channel + streets; slot {W} x {H}",
        "7_clock": "3 local roots ck_S / ck_K / ck_ML, each tree = its children's clock pins + its fenced ring halves; every crossing landed",
        "8_reset": f"regional rst_n_S/K/ML, forest DEPTH {B.STAGES} on its own clock, release on one die edge; reset on control/valid only"}
    j = s["job"]
    j.update(owner="Claude:S81-ELEM/ENDP", branch="claude/s81-endp-lr-1021", tag=name.split("_")[-1],
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}", extra_paths=[REC_DIR])
    sp = kd / "spec.json"
    json.dump(s, open(sp, "w"), indent=1)
    B.run(ROOT / "tools/ref_tile/ref_tile.py", "gen", sp.relative_to(ROOT))


if __name__ == "__main__":
    for side in (sys.argv[1:2] or ["e", "w"]):
        for v in ("a", "b"):
            build(f"s81sl_lep{side}mu_lr{v}", side, v)
