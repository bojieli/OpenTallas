QC START transport class event qc53v4s (QC-TYPES-7s, 2026-11-08). WAVE plan event, candidate only.
Base: plan_of_record/plan_qc53v4t.json (the current kit-wave plan, sha256 18dc0ae20052..).
Tool: qc_start_1108/plan_start.py = Codex START4 tool (qc_start_1106, intel2 codex-qc-start-1106/src) with the type
list on argv and strict-bind RTL naming (<module>__<type>.sv).  Same knobs as START4 on coll_ftm / slw_fw_v2 /
slw_fw_v3 / slw_fe_v1: clock.landing_reader_start, landing_writer_start, landing_local_resets.  Hops <= 405 um,
boot +R+W cycles only, 0 steady data cycles, every other type and every top-level key byte-identical (asserted).
Class: QC SETUP-AT-GRT START broadcast (QC-SETUP-RF1 11-06 05:31): one shared cland reset / START raw drives far
FSTART face flops and the origin in one cycle (coll_ftc -141.30 cland_rst_ag_wo_ag5_i -> u_cland_fstart_ss_wo_ss5_o,
sle_fe_v3 -152.56 u_rrl_3 -> u_cland_rst_cws3_i (whose only loads are cland_start_raw and u_cland_rstart_rx),
coll_ucie -158.28 inside u_cland_origin).
Types: coll_ftc, coll_ucie, sle_fe_v3.  Report: qc_start_1108/report.json.
Reproduce (RAWDIR = the strict bind rtl dir the wave uses, codex-watch-qc-1107/bind_strict/rtl):
  python3 -I qc_start_1108/plan_start.py plan_of_record/plan_qc53v4t.json qc_start_1106/runtime/sidecar.json \
      RAWDIR plan_of_record/plan_qc53v4s.json qc_start_1108/report.json coll_ftc coll_ucie sle_fe_v3
Adoption: kit-wave qwen_compute.plan -> plan_qc53v4s.json, pick dry run (only these 3 types change), one batch.
Count plan (plan_qc52t) unchanged: START4 lives on the wave plan line only, as qc53v4t does.
