#!/usr/bin/env python3
"""DRIVE-S81-SLICEP 10-20: DIAGNOSTIC stand-in parent kits of the MU end-slice clusters of the release die (mu7v2u):

  s81sl_lepemu_d1a / _d1b   ot_s81sl_slice_lepe_mu_x_lp  (s_7N: slice | lep_mu_h + dsdv_mu_land | 2 lane_e_ntf)
  s81sl_lepwmu_d1a / _d1b   ot_s81sl_slice_lepw_mu_x_lp  (s_0N: 2 lane_w_ntf | lep_mu_a + dsdv_mu_land | slice)
  (dsdv_slice_lepw_mus = lepw_mu minus mu_rt: served by the lepw kit; dsdv_slice_lepe_nh_mus = MU twin of lepe_nh: not here.)

Recipe = DRIVE-S81-LEPENH s81sl_lepenh_d3a / d3b (physical/ref_tile/s81sl_lepenh_d2/mk_d3.py): slice stand-in 1252.8 x 5702.4
(PL-SLICE outline), endpoint stand-in at the real lepmu*_n32 outline 475.2 x 561.6, landing channel 172.8 um with the line
ports bit-aligned, lanes 43.2 um beyond the endpoint.  NEW vs lepe_nh: the CLOSED dsdv_mu_land view (475.2 x 216, every pin
on its S face: rd x 3.8-238.5, wd 239.2-473.9, rc/clk/fault at x ~1-4) sits 43.2 um N of the endpoint, oriented so its
R0 on both ends (MY puts its pins off-track); on lepe its rc/clk/fault corner therefore faces the channel; the endpoint's ml_* pins are ranged under the matching land pins.
Region plan (10-20 clock rule): S = slice, K = endpoint + land + lanes; rings only at the S<->K crossings (lp.py).
  a: port flops unanchored + PD 0.45 (d3a);  b: anchors kept, CTS 24 sinks / 30 um / 15-um buffers / -balance_levels (d3b).
Stand-ins carry STANDIN_NOT_A_VIEW: never bind, never submit.
"""
import copy, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D3 = ROOT / "physical/ref_tile/s81sl_lepenh_d3a"
WOUT = 2462.4
SL_W, SL_H, SL_Y = 1252.8, 5702.4, 43.2
LEP_W, LEP_H, LEP_Y = 475.2, 561.6, 2592.0
LAND_Y = LEP_Y + LEP_H + 43.2
LANE_W = 432.0
INS = {"ot_s81sl_slice": "250,200,330", "ot_s81sl_lep_mu_h": "220,170,290", "ot_s81sl_lep_mu_a": "220,170,290",
       "dsfd_coll_lane_e_ntf": "419,347,537", "dsfd_coll_lane_w_ntf": "419,347,537"}
LAND_VIEW = "physical/ref_tile/dsdv_mu_land/views/dsdv_mu_land"
LANE_PINS = ["lo0_v", "lo0_r", "lo0_d", "li0_v", "li0_r", "li0_d", "lo1_v", "lo1_r", "lo1_d", "li1_v", "li1_r", "li1_d",
             "rxv", "l0_f", "l1_f"]


def mx(r, w):
    return [round(w - r[1], 3), round(w - r[0], 3)]


def lep_standin(side):
    host = side == "e"
    top = "ot_s81sl_lep_mu_h" if host else "ot_s81sl_lep_mu_a"
    lane_face, line_face = ("E", "W") if side == "e" else ("W", "E")
    lp = LANE_PINS + (["l0_st", "l1_st"] if host else []) + ["clk", "rst_n", "mu_c", "mu_rt"]
    pins = {line_face: ["ro", "ri"], lane_face: lp, "N": ["ml_wd", "ml_rd", "ml_wv", "ml_rv", "ml_f"],
            "S": ["sl_f", "fault"] + (["f_host", "f_lf", "f_ks", "t_host", "t_kd"] if host else [])}
    # land R0: rd 3.8-238.5, wd 239.2-473.9, clk/fault/rc at x 1.1-3.6, rst_n 238.75, rv 238.97, wv 474.1
    # land R0 on both ends (an MY flip puts its 1112 LEF pins off the asap7 tracks: ref_tile macro_grid FAIL)
    if True:
        ml = {"ml_f": [1.4, 2.0], "ml_rv": [2.4, 3.0], "ml_wv": [3.4, 3.9], "ml_rd": [4.4, 238.4], "ml_wd": [239.4, 473.6]}
    pr = {"ro": [4.0, 280.0], "ri": [282.0, 557.6], "clk": [272.8, 280.8], "rst_n": [280.8, 288.8],
          "mu_c": [520.0, 538.0], "mu_rt": [539.0, 556.0], **ml}
    # S face: sl_f at the channel corner, fault at the lane corner, host plane toward the lane / E side (lepe only)
    if side == "e":
        pr.update({"sl_f": [3.0, 10.0], "fault": [455.0, 472.0], "f_host": [160.0, 330.0], "f_lf": [331.0, 333.0],
                   "f_ks": [334.0, 352.0], "t_host": [354.0, 390.0], "t_kd": [391.0, 450.0]})
    else:
        pr.update({"sl_f": mx([3.0, 10.0], LEP_W), "fault": mx([455.0, 472.0], LEP_W)})
    return {"name": f"standin_{top}", "top": top, "sources": ["rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv"],
            "clock_port": "clk", "outline": {"w": LEP_W, "h": LEP_H}, "pins": pins, "pin_ranges": pr,
            "_note": (f"DRIVE-S81-SLICEP stand-in (DIAGNOSTIC, STANDIN_NOT_A_VIEW) at the lepmu{'h' if host else 'a'}_n32 outline "
                      f"475.2 x 561.6, drawn in the {'E-end (MY)' if side == 'e' else 'W-end (native)'} orientation. Pin REQUEST "
                      "for the real view: ro/ri on the slice face bit-aligned across the 172.8-um channel, ml_* on N under the "
                      "dsdv_mu_land S-face pins, mu_c/mu_rt at the top of the lane face, sl_f at the S channel corner.")}


def slice_standin(side):
    s = json.load(open(D3 / "standin/slice.json"))
    off = LEP_Y - SL_Y
    pr = s["pin_ranges"]
    if side == "w":           # mirror: lep on the slice W face, parent line port on the slice E face
        s["pins"] = {"W": ["rst_n", "clk", "fault", "ro_w", "ri_w"], "E": ["ri_e", "ro_e"], "N": s["pins"]["N"],
                     "S": s["pins"]["S"]}
        new = {k: mx(v, SL_W) for k, v in pr.items() if k in s["pins"]["N"] + s["pins"]["S"]}
        new.update({"ro_w": [round(off + 4.0, 3), round(off + 280.0, 3)], "ri_w": [round(off + 282.0, 3), round(off + 557.6, 3)],
                    "ri_e": [2160.0, 2851.2], "ro_e": [2851.2, 3542.4], "rst_n": pr["rst_n"], "clk": pr["clk"],
                    "fault": pr["fault"]})
        s["pin_ranges"] = new
    s["_note"] = (f"DRIVE-S81-SLICEP stand-in (DIAGNOSTIC): PL-SLICE pin REQUEST, {'E' if side == 'e' else 'W'} face line "
                  "ports bit-aligned with the endpoint window (lep y 2592), rst_n/clk/fault just below it.")
    return s


def lane_standin(side):
    s = json.load(open(D3 / "standin/lane_e.json"))
    s["top"] = f"dsfd_coll_lane_{side}_ntf"
    s["name"] = f"standin_{s['top']}"
    out, inn = ("E", "W") if side == "e" else ("W", "E")
    s["pins"] = {out: ["rx", "tx"], inn: ["lo_v", "lo_r", "lo_d", "li_v", "li_r", "li_d", "flt"], "N": ["ck", "rs", "chb"]}
    s["pin_ranges"] = {"rx": [10.0, 170.0], "tx": [170.0, 330.96]}
    s["_note"] = f"DRIVE-S81-SLICEP stand-in (DIAGNOSTIC) of the tf-less lane top {s['top']} (no tf pin), lane_e geometry."
    return s


def build(name, side, variant):
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    lep_m = "ot_s81sl_lep_mu_h" if side == "e" else "ot_s81sl_lep_mu_a"
    lane_m = f"dsfd_coll_lane_{side}_ntf"
    stand = {"slice.json": ("ot_s81sl_slice", slice_standin(side)), "lep.json": (lep_m, lep_standin(side)),
             "lane.json": (lane_m, lane_standin(side))}
    views = {}
    for f, (master, s) in stand.items():
        json.dump(s, open(kd / "standin" / f, "w"), indent=1)
        out = kd / "standin_views" / master
        subprocess.run([sys.executable, str(ROOT / "tools/qwen_dv/slice_standin.py"), "--ins", INS[master], "--master", master,
                        str(kd / "standin" / f), str(out.parent)], check=True, cwd=ROOT)
        views[master] = str(out.relative_to(ROOT))
    s = json.load(open(ROOT / f"physical/ref_tile/s81sl_lepenh_d3{variant}/spec.json"))
    top = f"ot_s81sl_slice_lep{side}_mu_x_lp"
    s["name"] = name
    s["top"] = top
    s["sources"] = ([f"rtl/dsrom_sys/s81_dv/slice/landed/lep{side}_mu/{top}.sv"]
                    + [x for x in s["sources"] if x.startswith("rtl/common/landed_parent/")]
                    + [f"{views[m]}/{m}_bb.v" for m in ("ot_s81sl_slice", lep_m, lane_m)])
    s["landed_record"] = f"results/rtl/drive_s81_slicep_1020/lp/ot_s81sl_slice_lep{side}_mu_x_lp_record.json"
    if side == "e":
        at = {"u_sl": [43.2, SL_Y], "u_lep": [1468.8, LEP_Y], "u_land": [1468.8, LAND_Y],
              "u_ln0": [1987.2, 2548.8], "u_ln1": [1987.2, 2937.6]}
    else:
        at = {"u_sl": [WOUT - 43.2 - SL_W, SL_Y], "u_lep": [WOUT - 1468.8 - LEP_W, LEP_Y], "u_land": [WOUT - 1468.8 - LEP_W, LAND_Y],
              "u_ln0": [WOUT - 1987.2 - LANE_W, 2548.8], "u_ln1": [WOUT - 1987.2 - LANE_W, 2937.6]}
    at = {k: [round(v[0], 3), v[1]] for k, v in at.items()}
    ch = [{"view": views["ot_s81sl_slice"], "count": 1, "inst": "u_sl", "at": at["u_sl"]},
          {"view": views[lep_m], "count": 1, "inst": "u_lep", "at": at["u_lep"]},
          {"view": LAND_VIEW, "count": 1, "inst": "u_land", "at": at["u_land"]},
          {"view": views[lane_m], "count": 1, "inst": "u_ln0", "at": at["u_ln0"]},
          {"view": views[lane_m], "count": 1, "inst": "u_ln1", "at": at["u_ln1"]}]
    s["children"] = ch
    d3pr = s["pin_ranges"]
    ns = {k: d3pr[k] for k in ("bi", "bo", "xc", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "vi", "vo")}
    lk = {"rst_n": [2436.0, 2440.0], "ck_S": [2444.0, 2456.0], "fault": [2500.0, 2504.0],
          "rx0": d3pr["rx0"], "tx0": d3pr["tx0"], "rx1": d3pr["rx1"], "tx1": d3pr["tx1"], "ch_b": d3pr["ch_b"],
          "ck_K": d3pr["ck_K"], "mu_c": [3330.0, 3360.0], "mu_rt": [3362.0, 3392.0], "mu_rc": [3400.0, 3412.0]}
    lk_order = ["rst_n", "ck_S", "fault", "rx0", "tx0", "rx1", "tx1", "ch_b", "ck_K", "mu_c", "mu_rt", "mu_rc"]
    if side == "e":
        lk.update({"f_host": [1700.0, 2060.0], "f_lf": [2062.0, 2068.0], "f_ks": [2070.0, 2130.0],
                   "t_host": [2135.0, 2300.0], "t_kd": [2302.0, 2420.0]})
        lk_order = ["f_host", "f_lf", "f_ks", "t_host", "t_kd"] + lk_order
        s["pins"] = {"W": ["ri_w", "ro_w"], "N": ["sid", "vi", "vo"], "E": lk_order, "S": s["pins"]["S"]}
        s["pin_ranges"] = {**ns, "ri_w": d3pr["ri_w"], "ro_w": d3pr["ro_w"], **lk}
        line_in, line_out = "ri_w", "ro_w"
    else:
        s["pins"] = {"E": ["ri_e", "ro_e"], "N": ["sid", "vi", "vo"], "W": lk_order, "S": s["pins"]["S"]}
        s["pin_ranges"] = {**{k: mx(v, WOUT) for k, v in ns.items()}, "ri_e": d3pr["ri_w"], "ro_e": d3pr["ro_w"], **lk}
        line_in, line_out = "ri_e", "ro_e"
    ced = s["clock_entry_domains"]
    ced["core"]["inputs"] = ["rst_n", "sid", line_in, "vi", "bi", "rt"]
    ced["core"]["outputs"] = [line_out, "vo", "bo", "xc", "ck_line", "ck_v", "ck_xc", "ck_rt"]
    ced["lk"]["inputs"] = ["ch_b", "rx0", "rx1", "mu_c", "mu_rc"] + (["t_host", "t_kd"] if side == "e" else [])
    ced["lk"]["outputs"] = ["tx0", "tx1", "fault", "mu_rt"] + (["f_host", "f_lf", "f_ks"] if side == "e" else [])
    s["reset_landing"] = dict(s["reset_landing"])
    s["structural_change"] = (f"DRIVE-S81-SLICEP 10-20 {name}: DIAGNOSTIC stand-in parent of the MU die master "
                              f"dsdv_slice_lep{side}_mu (never bindable), recipe of s81sl_lepenh_d3{variant} (see "
                              "tools/s81_slice/mk_lepmu_kits.py): S = slice, K = MU endpoint + CLOSED dsdv_mu_land view + 2 tf-less "
                              "lanes, rings only at S<->K; " + ("a: port flops unanchored, PD 0.45." if variant == "a" else
                              "b: anchors kept, CTS 24 sinks/30 um/15-um buffers/-balance_levels."))
    j = s["job"]
    j["owner"] = "Claude:DRIVE-S81-SLICEP"
    j["branch"] = "claude/drive-s81-slicep-lepmu-1020"
    j["tag"] = name.split("_")[-1]
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    j["extra_paths"] = ["results/rtl/drive_s81_slicep_1020/lp"]
    sp = kd / "spec.json"
    json.dump(s, open(sp, "w"), indent=1)
    subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(sp.relative_to(ROOT))], check=True, cwd=ROOT)


if __name__ == "__main__":
    for side in ("e", "w"):
        for v in ("a", "b"):
            build(f"s81sl_lep{side}mu_d1{v}", side, v)
