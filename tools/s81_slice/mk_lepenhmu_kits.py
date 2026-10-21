#!/usr/bin/env python3
"""DRIVE-S81-LEPENHMU 10-20: DIAGNOSTIC stand-in parent kits of dsdv_slice_lepe_nh_mus (s_7S, MU twin of lepe_nh):

  s81sl_lepenhmu_d1a / _d1b   ot_s81sl_slice_lepe_nh_mu_x_lp  (slice | lep_mu_a + dsdv_mu_land | 2 x lane_e_safe8_ntf)

Recipe = tools/s81_slice/mk_lepmu_kits.py (DRIVE-S81-SLICEP lepemu d1a/d1b, itself the DRIVE-S81-LEPENH d3a/d3b recipe:
172.8-um landing channel, line ports bit-aligned, sl_f at the S channel corner) with two changes:
  * endpoint = copy-A lep_mu_a (no host plane) drawn in the E-end orientation;
  * lanes = the REAL MU lane tops dsfd_coll_lane_e_safe8_ntf (DRIVE-S81-NTF, kit dscoll_lane_e_s8n) at their real outline
    725.76 x 583.2 with their real pin ranges (rx/tx E, lo/li/ck/rs/chb/flt W), stacked symmetrically about the endpoint
    window, 43.2 um E of the endpoint; parent widened to 2764.8 (64 x 43.2); parent E-face pins aligned to the lanes:
    rx/tx on the lane rows, ch_b/ck_K in the lane gap, rst_n/ck_S/fault just below lane 0, mu_* just above lane 1.
  a: port flops unanchored + PD 0.45 (d3a);  b: anchors kept, CTS 24 sinks / 30 um / 15-um buffers / -balance_levels (d3b).
Stand-ins carry STANDIN_NOT_A_VIEW: never bind, never submit.
"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mk_lepmu_kits as M  # noqa: E402

ROOT = M.ROOT
WOUT = 2764.8
LANE_W, LANE_H = 725.76, 583.2
LANE_X = 1468.8 + M.LEP_W + 43.2                     # 1987.2
LANE0_Y, LANE1_Y = 2289.6, 2894.4                    # symmetric about the endpoint window centre 2872.8
LANE_TOP = "dsfd_coll_lane_e_safe8_ntf"
LANE_SRC = "rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv"
LANE_PR = {"rx": [2.16, 288.36], "tx": [290.52, 576.72], "lo_d": [2.16, 274.32], "lo_v": [276.48, 277.56],
           "lo_r": [278.64, 279.72], "chb": [280.8, 282.96], "ck": [298.08, 300.24], "rs": [302.4, 304.56],
           "li_v": [306.72, 307.8], "li_r": [308.88, 309.96], "flt": [312.12, 315.36], "li_d": [317.52, 581.04]}
LEP_TOP = "ot_s81sl_lep_mu_a"
TOP = "ot_s81sl_slice_lepe_nh_mu_x_lp"
INS = dict(M.INS, **{LANE_TOP: "419,347,537"})


def lep_standin():
    s = M.lep_standin("e")
    s["top"], s["name"] = LEP_TOP, f"standin_{LEP_TOP}"
    s["pins"]["E"] = [p for p in s["pins"]["E"] if p not in ("l0_st", "l1_st")]
    host = ("f_host", "f_lf", "f_ks", "t_host", "t_kd")
    s["pins"]["S"] = [p for p in s["pins"]["S"] if p not in host]
    for p in host:
        s["pin_ranges"].pop(p, None)
    s["_note"] = ("DRIVE-S81-LEPENHMU stand-in (DIAGNOSTIC, STANDIN_NOT_A_VIEW) of lep_mu_a at the lepmua_n32 outline 475.2 x 561.6, "
                  "E-end (MY) orientation. Pin REQUEST for the real view: ro/ri W bit-aligned across the 172.8-um channel, ml_* N "
                  "under the dsdv_mu_land S-face pins, lane pins E toward the two lane_e_safe8_ntf tiles, sl_f at the S channel corner.")
    return s


def lane_standin():
    return {"name": f"standin_{LANE_TOP}", "top": LANE_TOP, "sources": [LANE_SRC], "clock_port": "ck",
            "defines": ["OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF"],
            "outline": {"w": LANE_W, "h": LANE_H},
            "pins": {"E": ["rx", "tx"], "W": ["lo_v", "lo_r", "lo_d", "li_v", "li_r", "li_d", "flt", "ck", "rs", "chb"]},
            "pin_ranges": dict(LANE_PR),
            "_note": "DRIVE-S81-LEPENHMU stand-in (DIAGNOSTIC) of the real MU lane top dsfd_coll_lane_e_safe8_ntf at its kit "
                     "dscoll_lane_e_s8n outline 725.76 x 583.2 and pin ranges (DRIVE-S81-NTF @445e6c74c)."}


def off(r, y):
    return [round(r[0] + y, 3), round(r[1] + y, 3)]


def build(name, variant):
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    stand = {"slice.json": ("ot_s81sl_slice", M.slice_standin("e")), "lep.json": (LEP_TOP, lep_standin()),
             "lane.json": (LANE_TOP, lane_standin())}
    views = {}
    for f, (master, s) in stand.items():
        json.dump(s, open(kd / "standin" / f, "w"), indent=1)
        out = kd / "standin_views" / master
        subprocess.run([sys.executable, str(ROOT / "tools/qwen_dv/slice_standin.py"), "--ins", INS[master], "--master", master,
                        str(kd / "standin" / f), str(out.parent)], check=True, cwd=ROOT)
        views[master] = str(out.relative_to(ROOT))
    s = json.load(open(ROOT / f"physical/ref_tile/s81sl_lepenh_d3{variant}/spec.json"))
    s["name"], s["top"] = name, TOP
    s["sources"] = ([f"rtl/dsrom_sys/s81_dv/slice/landed/lepe_nh_mu/{TOP}.sv"]
                    + [x for x in s["sources"] if x.startswith("rtl/common/landed_parent/")]
                    + [f"{views[m]}/{m}_bb.v" for m in ("ot_s81sl_slice", LEP_TOP, LANE_TOP)])
    s["landed_record"] = f"results/rtl/drive_s81_lepenhmu_1020/lp/{TOP}_record.json"
    if "outline" in s:
        s["outline"] = dict(s["outline"], w=WOUT)
    at = {"u_sl": [43.2, M.SL_Y], "u_lep": [1468.8, M.LEP_Y], "u_land": [1468.8, M.LAND_Y],
          "u_ln0": [LANE_X, LANE0_Y], "u_ln1": [LANE_X, LANE1_Y]}
    s["children"] = [{"view": views["ot_s81sl_slice"], "count": 1, "inst": "u_sl", "at": at["u_sl"]},
                     {"view": views[LEP_TOP], "count": 1, "inst": "u_lep", "at": at["u_lep"]},
                     {"view": M.LAND_VIEW, "count": 1, "inst": "u_land", "at": at["u_land"]},
                     {"view": views[LANE_TOP], "count": 1, "inst": "u_ln0", "at": at["u_ln0"]},
                     {"view": views[LANE_TOP], "count": 1, "inst": "u_ln1", "at": at["u_ln1"]}]
    d3pr = s["pin_ranges"]
    ns = {k: d3pr[k] for k in ("bi", "bo", "xc", "rt", "ck_line", "ck_v", "ck_xc", "ck_rt", "sid", "vi", "vo")}
    lk = {"rst_n": [2240.0, 2244.0], "ck_S": [2248.0, 2260.0], "fault": [2266.0, 2270.0],
          "rx0": off(LANE_PR["rx"], LANE0_Y), "tx0": off(LANE_PR["tx"], LANE0_Y),
          "ch_b": [2875.0, 2877.0], "ck_K": [2880.0, 2892.0],
          "rx1": off(LANE_PR["rx"], LANE1_Y), "tx1": off(LANE_PR["tx"], LANE1_Y),
          "mu_c": [3500.0, 3530.0], "mu_rt": [3532.0, 3562.0], "mu_rc": [3570.0, 3582.0]}
    lk_order = ["rst_n", "ck_S", "fault", "rx0", "tx0", "ch_b", "ck_K", "rx1", "tx1", "mu_c", "mu_rt", "mu_rc"]
    s["pins"] = {"W": ["ri_w", "ro_w"], "N": ["sid", "vi", "vo"], "E": lk_order, "S": s["pins"]["S"]}
    s["pin_ranges"] = {**ns, "ri_w": d3pr["ri_w"], "ro_w": d3pr["ro_w"], **lk}
    ced = s["clock_entry_domains"]
    ced["core"]["inputs"] = ["rst_n", "sid", "ri_w", "vi", "bi", "rt"]
    ced["core"]["outputs"] = ["ro_w", "vo", "bo", "xc", "ck_line", "ck_v", "ck_xc", "ck_rt"]
    ced["lk"]["inputs"] = ["ch_b", "rx0", "rx1", "mu_c", "mu_rc"]
    ced["lk"]["outputs"] = ["tx0", "tx1", "fault", "mu_rt"]
    s["reset_landing"] = dict(s["reset_landing"])
    s.setdefault("defines", [])
    for d in ("OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF"):
        if d not in s["defines"]:
            s["defines"].append(d)
    s["structural_change"] = (f"DRIVE-S81-LEPENHMU 10-20 {name}: DIAGNOSTIC stand-in parent of the MU die master "
                              "dsdv_slice_lepe_nh_mus (never bindable), recipe of s81sl_lepenh_d3" + variant +
                              " / s81sl_lepemu_d1" + variant + " (tools/s81_slice/mk_lepenhmu_kits.py): S = slice, K = lep_mu_a + "
                              "CLOSED dsdv_mu_land view + 2 REAL-outline lane_e_safe8_ntf stand-ins (725.76 x 583.2), rings only "
                              "at S<->K; " + ("a: port flops unanchored, PD 0.45." if variant == "a" else
                              "b: anchors kept, CTS 24 sinks/30 um/15-um buffers/-balance_levels."))
    j = s["job"]
    j["owner"] = "Claude:DRIVE-S81-LEPENHMU"
    j["branch"] = "claude/drive-s81-lepenhmu-1020"
    j["tag"] = name.split("_")[-1]
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    j["extra_paths"] = ["results/rtl/drive_s81_lepenhmu_1020/lp"]
    sp = kd / "spec.json"
    json.dump(s, open(sp, "w"), indent=1)
    subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(sp.relative_to(ROOT))], check=True, cwd=ROOT)


if __name__ == "__main__":
    for v in ("a", "b"):
        build(f"s81sl_lepenhmu_d1{v}", v)
