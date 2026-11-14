# UNOWNED-SWEEP handoff (updated 2026-11-14 08:10 PST, sweep 1)
Method: /api/elements localhost:8765 (non-HBM, state failed/not built) + grep of queue/handoff/wave log. Repeat hourly.
Sweep 1 counts (failed / not-built / unowned):
- s81: 22 failed (16 DEDUP/identity twins credited when twin signs, 5 restaged waiters KW-FIX-4, plus leaf__t32 grt-overflow, serdes__t2 timecap, 3 Tcl FT-site) / 8 not built / unowned: svc_hi_dsdv_svc_pvso_entry__t2, svc_hi_dsdv_svc_rs__t5, svc_hi_dsdv_svc_rs__t6 (GEN_LINT memory_bits since 11-13 01:xx), slice_station__t6__cl0755c26e (SRC-INCOMPLETE 11-12, handoff FAIL-S81-1 only)
- s81_head: 0 failed / 1 not built (hd_lep0N, queued post) / 0 unowned
- qwen_compute QC: 0 failed / 5 not built (all named in DIE-QC-103 posts; coll_s, qc_cland_w515_n_d8_local32_codex only in handoff, SRC-INCOMPLETE/KIT_NOT_SELF_CONTAINED 11-14 06:xx) / 0 hard unowned
- qwen_kvsys KV: 1 failed (kv3_hgi_v6, plan-B owner TYPE-KVHGI2) / 0 / 0
Relaunched: none (no infra-kill items; no rc137/143/241 rows).
NEEDS-LANE class: GEN_LINT memory_bits over SYNTH_MEMORY_MAX_BITS (3 svc_hi types).
