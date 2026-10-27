import json, glob, hashlib
from pathlib import Path
W = "/srv/opentallas-scratch2/claude/wt/qc-su-prog-l2-1026/results/"
sw = {}
for f in sorted(glob.glob(W + "qc_su_prog_l2_1026/sweep/*.ht2.json")):
    d = json.load(open(f)); p = d["phys"]
    sw[Path(f).name.split(".")[0]] = dict(D2=d["D2_um"], seg=d["seg_um"], structure=d["structure_verdict"], gate=d["phys"]["gate"]["verdict"],
        TT_rise=[p["TT_rise"]["mean"], p["TT_rise"]["window"]], FF_early=[p["FF_early"]["mean"], p["FF_early"]["window"]],
        levels=d["structure"]["G4_lengths"]["level_len_um"], K=d["structure"]["G4_lengths"]["segments_per_edge"],
        textbook_delta=p["sensitivity"]["textbook"]["delta_vs_gate"])
s = dict(lane="QC-SU-PROG-L2 (Claude) 2026-10-26", base="claude/qc-su-prog-l1-1026@d03d4aa38", numbers="UNCHECKED (plan model + lane STA)",
  refit=dict(
    data="4th point prog c_ls_k5_S13 CTS+GRT (intel1 kit_l1 5_1_grt.odb): meas_ck TT/FF re-dumped = build_k5 TSVs byte-identical; meas_stage TT/FF + netcap (report_net) via model-refit2 tools/run_stage.sh -> model_refit2_1026/meas/prog_k5",
    repro="3-build refit re-run (OT_REFIT_BUILDS) reproduces the frozen params max a.2/b.5/g5 min a.2/b.4/g4 and LOO TT max 7.09 / FF 4.21 (refit4/fit3_repro_ext.json)",
    params="refit4/uf_phys_refit4.json: PMAX a0/b.45/g5.0/kleaf1.2868 (fit4_ext), PMIN a0/b.5/g3.0/kleaf1.2868 (fit4_max_grid)",
    LOO_TT_max_analysis_maxabs=dict(prog_r1=9.54, prog_r3=9.31, btab_r4=4.59, prog_k5=11.63),
    LOO_FF_min_analysis_maxabs=dict(prog_r1=4.05, prog_r3=4.5, btab_r4=4.76, prog_k5=5.36),
    guard_band="TT LOO max 11.63 -> 12: TT rise mean 242..258; FF 5.36 -> 6: FF early mean 188.5..216.5; windows <= 20 (was 238..262 / 187.5..217.5)",
    finding="the refit got WORSE (TT LOO max 7.1 -> 11.6): residual tracks STAGE COUNT, not cell size. root->tap-A error (meas-pred, TT rise) -5.4/-4.4/+0.9/+4.8 ps at 5/6/8/9 stages per path (r1/r3/btab/k5); per-stage error by driver cell is small for BUFx4/x6f (+0.5/+0.7, same as BUFx12f/16f +0.3..+0.6); BUFx8/x10 fanout drivers -3..-4 in prog r1/r3. Global alpha/beta/gslew cannot absorb a stage-count trend -> a model-structure term is missing (MODEL lane). In-sample k5 mean residual +5.8 TT.",
    files=["model_refit2_1026/refit4/fit4_ext.json", "fit4_max_grid.json", "fit3_repro_ext.json", "resid4_ext.json", "stagecell_fit4.txt"]),
  htree3=dict(tool="qc_su_prog_l1_1026/ht_l2.py (+ render_ht2.py, test_ht_l2.py 9 tests; test_phys_gate 8 tests OK with libs)",
    structure="H5 L1 unchanged (GEOM-6 PASS) -> island -> sub-islands at ONE maze leg D2 (count ceil(B/2) per island = 10) -> B (frozen) -> leaves (frozen membership); all legs below L1 maze-routed with macros+2.2 halo AND pin columns +-4.32 blocked; B/leaf sites inside the band re-sited (31 nodes, to x>=283 on E); L3/L4 straight + plan-computed sizing (BUFx8..x24)",
    sweep=sw, chosen="h3_d55_s95"))
Path(W + "qc_su_prog_l2_1026/summary.json").write_text(json.dumps(s, indent=1))
print(json.dumps(sw, indent=0)[:3000])
