# ELEM-QK 2026-10-24: Qwen compute + KV re-runs and G3 kits

## signoff_1024 NEEDS RE-RUN (33 QC/KV ref_tile kits with a kit in the repo)
Each kit re-routed from its CLOSED record's own source commit with the job's own route stage
(tools/elem_qk/rerun_reftile.py, no closure-loop daemon), then main's tools/die_plan/signoff.py --corners tt,ff
(TT setup / FF hold, owner 2026-10-24 08:10).  Author floorplan reviews: results/geom_review/<module>__<kit>__<hash>.json,
contact sheets review/batch_0*.png.  Per kit: rerun/<kit>/{route_rc,signoff.json}; table rerun_summary.json.

Verdicts (32 routed, re-signed with main 24b2da3433; qkd_kvs_ctl route still running): ALL NOT SIGNED.
Failing checks over 32: sdc_lint 32, face_guard 26, FF hold 13, DRV 6, unconstrained 5, clock 5, TT setup 3
(TT setup fails: qkd_ctrl_kc -1.13, qfd_dv_stream_t2_1019 -1.88, qfd_dv_lane_h_safe2 -3.74).
- sdc_lint FAIL on every kit: the ref_tile sign-off SDC is a Tcl program (env-driven measured IO reference, period
  833.333) and the die-plan vocabulary needs one real tap clock + one virtual IO clock with latency, period 833.
  Evaluating it (tools/elem_qk/flatten_sdc.sh: OpenSTA write_sdc on the routed DB) still fails that vocabulary.
- face_guard FAIL on 11/12 (unregistered / dropped / shared / merged boundary bits): these closed-era designs predate
  the face-register contract.  qkd_ctrl_kc passes face_guard but fails TT setup -1.13 and clock spread 308.
- FF hold fails on 5 (qkh_r4_score4 -4.01, qkh_native_stin -6.83, qkd_pv_rs_hd_f -7.65, qkh_head_sstage -15.45; ...).
=> A ref_tile re-run cannot produce a SIGNED view; signing these modules needs a die-plan G3 re-kit (kit SDC form,
   face registers).  OWNER?/SIGNOFF asked (lanes/SIGNOFF.md 08:2x).
- 21 route attempts were killed at 08:33 PDT by a fleet-wide `docker stop` of all containers (not ELEM-QK); relaunched
  12:3x PDT.
