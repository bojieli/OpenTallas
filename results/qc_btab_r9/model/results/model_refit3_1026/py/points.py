"""MODEL-REFIT-3 calibration points: plan inputs (spec actually built, geo, seg) + measured per-sink CK arrivals.
Every path is repo-relative (results/...); provenance (origin host path, sha256) is in ../POINTS.md / points.json.
basis GRT = meas_ck on 5_1_grt.odb (estimate_parasitics -global_routing, rc_cal 0.8/0.9); RCX = meas_ck on the routed
DB with its SPEF (OpenRCX).  Never mixed without the explicit T8/T9 GRT->RCX terms (uf_phys3)."""
from pathlib import Path

RES = Path(__file__).resolve().parents[2]
K = RES / "qc_su_kits"
R2 = RES / "model_refit2_1026" / "meas"
L1 = RES / "qc_su_prog_l1_1026"
L2 = RES / "qc_su_prog_l2_1026"
P3 = RES / "model_refit3_1026" / "points"


def _p(*a):
    return str(Path(*a))


# name: dict(spec, seg (json with seg_um, or None = Manhattan between plan nodes), geo, grt=(TT,FF) tsv, rcx=(TT,FF) or None,
#            vias_rcx = routed via table (RCX DB) or None, netcap = GRT netcap dump or None, family)
POINTS = {
    "prog_r1": dict(spec=_p(K, "r2/prog_m0.ab.tcl"), seg=_p(K, "r2/prog_m0.ab.json"), geo=_p(K, "r2/prog_m0.geo"),
                    grt=(_p(R2, "prog_r1/meas_ck_TT.tsv"), _p(R2, "prog_r1/meas_ck_FF.tsv")), netcap=_p(R2, "prog_r1/netcap_TT.txt"), family="QC-SU prog"),
    "prog_r3": dict(spec=_p(K, "r3/out/prog_m0_r3.gate.asbuilt.tcl"), seg=_p(K, "r3/out/prog_m0_r3.gate.asbuilt.json"), geo=_p(K, "r2/prog_m0.geo"),
                    grt=(_p(R2, "prog_r3/meas_ck_TT.tsv"), _p(R2, "prog_r3/meas_ck_FF.tsv")), netcap=_p(R2, "prog_r3/netcap_TT.txt"), family="QC-SU prog"),
    "btab_r4": dict(spec=_p(K, "r4/btab_m0_r4/btab_ls_k6_L3.gate.asbuilt.tcl"), seg=_p(K, "r4/btab_m0_r4/btab_ls_k6_L3.gate.asbuilt.json"),
                    geo=_p(K, "r2/btab_m0.geo"), grt=(_p(R2, "btab_r4/meas_ck_TT.tsv"), _p(R2, "btab_r4/meas_ck_FF.tsv")),
                    netcap=_p(R2, "btab_r4/netcap_TT.txt"), family="QC-SU btab"),
    "prog_k5": dict(spec=_p(L1, "sweep_c/c_ls_k5_S13.gate.asbuilt.sized.tcl"), seg=_p(L1, "sweep_c/c_ls_k5_S13.gate.asbuilt.json"),
                    geo=_p(K, "r2/prog_m0.geo"), grt=(_p(R2, "prog_k5/meas_ck_TT.tsv"), _p(R2, "prog_k5/meas_ck_FF.tsv")),
                    netcap=_p(R2, "prog_k5/netcap_TT.txt"), family="QC-SU prog"),
    "prog_l2": dict(spec=_p(L2, "sweep/h3_d55_s95.sized.tcl"), seg=_p(L2, "sweep/h3_d55_s95.seg.json"), geo=_p(K, "r2/prog_m0.geo"),
                    grt=(_p(L2, "cts_grt_l2/grt_meas/meas_ck_TT.tsv"), _p(L2, "cts_grt_l2/grt_meas/meas_ck_FF.tsv")), family="QC-SU prog"),
    "btab_r5": dict(spec=_p(P3, "btab_r5/btab_r5_k6_L3.gate.asbuilt.tcl"), seg=_p(P3, "btab_r5/btab_r5_k6_L3.gate.asbuilt.json"),
                    geo=_p(P3, "btab_r5/btab_m0_r5.geo"), grt=(_p(P3, "btab_r5/meas_grt_TT.tsv"), _p(P3, "btab_r5/meas_grt_FF.tsv")),
                    rcx=(_p(P3, "btab_r5/meas_rcx_TT.tsv"), _p(P3, "btab_r5/meas_rcx_FF.tsv")), vias_rcx=_p(P3, "btab_r5/vias_rcx.tsv"), family="QC-SU btab"),
    "vmr_f4a": dict(spec=_p(P3, "vmr_f4a/mscts_spec_f4a.tcl"), seg=None, geo=_p(P3, "vmr_f4a/vmr_placed.geo"),
                    grt=(_p(P3, "vmr_f4a/grt_TT.tsv"), _p(P3, "vmr_f4a/grt_FF.tsv")),
                    rcx=(_p(P3, "vmr_f4a/rcx_TT_prehold.tsv"), _p(P3, "vmr_f4a/rcx_FF_prehold.tsv")), vias_rcx=_p(P3, "vmr_f4a/vias_rcx.tsv"), family="QC-SU F4A"),
    "rp1_f4a": dict(spec=_p(P3, "rp1_f4a/mscts_spec_f4a.tcl"), seg=None, geo=_p(P3, "rp1_f4a/rp1_placed.geo"),
                    grt=(_p(P3, "rp1_f4a/grt_TT.tsv"), _p(P3, "rp1_f4a/grt_FF.tsv")),
                    rcx=(_p(P3, "rp1_f4a/rcx_TT_prehold.tsv"), _p(P3, "rp1_f4a/rcx_FF_prehold.tsv")), vias_rcx=_p(P3, "rp1_f4a/vias_rcx.tsv"), family="QC-SU F4A"),
    "head_cal1": dict(spec=_p(P3, "head_cal1/mscts_spec_r5.tcl"), seg=_p(P3, "head_cal1/q44442_e1_b1.seg.json"), geo=_p(P3, "head_cal1/q44442_e1_b1.geo"),
                      grt=(_p(P3, "head_cal1/meas_ck_TT.tsv"), _p(P3, "head_cal1/meas_ck_FF.tsv")), family="S81-HEAD elemA"),
    "head_cal2": dict(spec=_p(P3, "head_cal2/mscts_spec_r5.tcl"), seg=_p(P3, "head_cal2/n_44442_b1.seg.json"), geo=_p(P3, "head_cal2/n_44442_b1.geo"),
                      grt=(_p(P3, "head_cal2/meas_ck_TT.tsv"), _p(P3, "head_cal2/meas_ck_FF.tsv")), family="S81-HEAD elemA"),
}
