#!/usr/bin/env python3
"""MODEL-REFIT-3 summary.json: points (basis, origin, sha256), fits, LOO guard, RCX findings.  usage: summary_gen.py"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, sys.path[0])
import points as PT
R = Path(__file__).resolve().parents[1]
ORIGIN = {
    "prog_r1": "claude/model-refit2-1026@3d6754e1f4 meas/prog_r1 (KITS-2 r2 kit 5_1_grt)",
    "prog_r3": "claude/model-refit2-1026@3d6754e1f4 meas/prog_r3 (KITS-3 prog_m0 r3 5_1_grt)",
    "btab_r4": "claude/model-refit2-1026@3d6754e1f4 meas/btab_r4 (KITS-3 btab_m0 r4 5_1_grt); RCX pending intel2 oth-ubuntu-1332751 (DRT)",
    "prog_k5": "claude/qc-su-prog-l2-1026@5f2bf0d12 meas/prog_k5 (L1 kit_l1 c_ls_k5_S13 5_1_grt)",
    "prog_l2": "claude/qc-su-prog-l2-1026@7b065a34b cts_grt_l2/grt_meas == epyc2:/srv/opentallas-scratch2/claude/qc-su-prog-l2-1026/kit_l2/meas (sha equal, CHECKED; built spec kit_l2/mscts_spec_l2.tcl == sweep/h3_d55_s95.sized.tcl CHECKED); RCX pending (DRT 513 viol 17:46)",
    "btab_r5": "intel1:/srv/opentallas-scratch2/claude/qc-su-btab-r5-1026/{plan,meas} (branch 9a9b3382b8 local only); built spec mscts_spec_r5.tcl == plan asbuilt.tcl (CHECKED); RCX = MODEL-REFIT-3 meas_ck.tcl on 6_final.odb+spef (DRT 0, ANT 0) -> btab_r5_rcx/, vias from 6_final.def",
    "vmr_f4a": "intel1:/srv/opentallas-scratch2/claude/qc-plan-f4a-1026/kits/qfd_dv_s8x_vmr_f4a/meas (grt_*, rcx_*_prehold, ck_wires_prehold, nodes_*); spec == placed_g4c.tcl (CHECKED); geo claude/qc-su-f4a-sign-1026@ac473525d placed/vmr_placed.geo",
    "rp1_f4a": "intel1:/srv/opentallas-scratch2/claude/qc-plan-f4a-1026/kits/qfd_dv_s8_crh_rp1_f4a/meas (as vmr)",
    "head_cal1": "intel1:/srv/opentallas-scratch2/claude/head-core-lat-r5-1026 kits/elemA_n50_cal meas_ck_* + p/q44442_e1_b1.* (spec == kit mscts_spec_r5.tcl CHECKED)",
    "head_cal2": "intel1:/srv/opentallas-scratch2/claude/head-core-lat-r5-1026 kits/elemA_n50_cal2 meas_ck_* + p/n_44442_b1.* (spec == kit mscts_spec_r5.tcl CHECKED)",
}
def sha(p):
    q = Path(p) if Path(p).exists() else Path(p + ".gz")
    return hashlib.sha256(q.read_bytes()).hexdigest()
pts = {}
for b, p in PT.POINTS.items():
    pts[b] = dict(family=p["family"], basis=["GRT"] + (["RCX"] if p.get("rcx") else []), origin=ORIGIN[b],
                  files={k: dict(path=str(Path(v).relative_to(PT.RES.parent)), sha256=sha(v)) for k, v in
                         [("spec", p["spec"]), ("seg", p["seg"]), ("geo", p["geo"]), ("grt_TT", p["grt"][0]), ("grt_FF", p["grt"][1])] +
                         ([("rcx_TT", p["rcx"][0]), ("rcx_FF", p["rcx"][1]), ("vias_rcx", p["vias_rcx"])] if p.get("rcx") else []) if v})
pts["S81_l0r_R6"] = dict(excluded="no build: R6 tree plans FAIL STRUCTURAL (GEOM-REVIEW-7 17:11), R7 plan only (no CTS/GRT measurement)")
M = json.load(open(R / "uf_phys3_v1.json")); F = json.load(open(R / "fit3_grt.json"))
X = json.load(open(R / "island_shift.json")); T = json.load(open(R / "transfer_rcx.json"))
ab = {}
for nm in ("abl_nostage", "abl_nobleaf"):
    f = R / f"{nm}.json"
    if f.exists():
        A = json.load(open(f))
        ab[nm] = dict(params={k: A["fits"][k]["params"] for k in ("max", "min")},
                      LOO_max=dict(TT=max(v["test"]["TT"]["maxabs"] for v in A["loo"]["max"].values()), FF=max(v["test"]["FF"]["maxabs"] for v in A["loo"]["min"].values())))
json.dump(dict(lane="MODEL-REFIT-3", scope="uf_phys3 v1 GRT-basis refit + GRT->RCX analysis; numbers UNCHECKED unless marked", points=pts,
               model=dict(file="results/model_refit3_1026/uf_phys3_v1.json", PMAX=M["PMAX"], PMIN=M["PMIN"], LOO_MAX=M["LOO_MAX"], WIN_GUARD=M["WIN_GUARD"],
                          LOO_maxabs=M["LOO_maxabs"], LOO_window_err=M["LOO_window_err"]),
               ablation=ab, rcx=dict(transfer_stage_fit=T["fit"], transfer_holdout=T["holdout"], island_shift_fits=X["fits"],
                                     verdict="NOT ADOPTED: per-via stage term fits F4A stages (CV 0.13-0.16 ps/via) but fails hold-out btab_r5; RCX-GRT shift is per L1 island and tracks island size (~3 ps/leaf), not vias")),
          open(R / "summary.json", "w"), indent=1)
print("ok")
