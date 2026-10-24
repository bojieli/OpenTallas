# KV kv41 bound top (BINDER4 10-23): KV token proof top

Plan v3.6 (die_plan.json md5 32f500f0), as-built rtl6 GEN (die_bound.v, source e33504a6f). Recipe: `../asbuilt_v36e.json`.
Rebuild with `tools/die_plan/bind.py elab|bind|verify|portbind physical/die_plan/qwen_kvsys/die_plan.json --asbuilt .../asbuilt_v36e.json`.

- Landing: the R8 table `../../r8/qwen_kvsys_r8_landing.json` (KV-P5 @60404093c). On top of it two extra tables:
  - The PV ENTRY pad table @0ec5c902d, `../kv_pv_entry_r8_v36.json`. It covers 3,100 ids and 128 INNER re-depths.
  - The kg row pads, `../kv_kg_row_pads_v36.json`: 96 members, 8,257 flops.
  - stale 0, uncovered 0.
- RH a/b streams: aligned on the pass-a bind (as-built a2/b4 = landed a2/b4), so no RH pads.
- Parameters, set by `../kv_regen36e.py`:
  - ECTL: RESPONSE_LAT 12, QK_ISSUE_AGE 34.
  - SEQ: KVN_A0 34.
  - d2d_kv: TXDP 32'h03030443 (pair image, KV TX 67; regen_constants D2D_TXDP_K).
  - AHUB: AP_OFS, FR_OFS -7.
  - PV ctl: TRUNK_D 43, FLAG_D 0.
  - The boot values from the table (P0/P1 -11, cfg_fia 68, per-vport DQ/RT, W request pads) are in param_regen.json.
- Results:
  - bind: 160 partitions, 85 types, 0 errors, tied 0, undriven 0.
  - verify: PASS, lint 0.
  - strict port-bind: PASS, 85 masters, 160 instances.
- `bind.f` paths are relative to the e33504a6f source tree plus this repository.
- The full bind directory, including kit_rtl/ for 85 types, is at `/home/ubuntu/scratch/binder4-1023/kv/kv41` (localhost and ot-epyc9).
- Gate: bind_post.py (CAL-AUTO @6928789ab) -> bind_gate.json INCOMPLETE: regen PASS (15 OK, 4 WARN = TRUNK_D/FLAG_D/VPORT_DQ/CFG_FIA, where the KV-P5 law differs from the authoritative PV entry table), smoke NOT_RUN (no KV smoke vehicle yet, CAL-AUTO). regen/ = constants.json + qwen_kvsys_sched_pkg.sv (peer QC qc12).
