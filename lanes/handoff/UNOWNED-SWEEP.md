# UNOWNED-SWEEP handoff (updated 2026-11-14 08:10 PST, sweep 1)
Method: /api/elements localhost:8765 (non-HBM, state failed/not built) + grep of queue/handoff/wave log. Repeat hourly.
Sweep 1 counts (failed / not-built / unowned):
- s81: 22 failed (16 DEDUP/identity twins credited when twin signs, 5 restaged waiters KW-FIX-4, plus leaf__t32 grt-overflow, serdes__t2 timecap, 3 Tcl FT-site) / 8 not built / unowned: svc_hi_dsdv_svc_pvso_entry__t2, svc_hi_dsdv_svc_rs__t5, svc_hi_dsdv_svc_rs__t6 (GEN_LINT memory_bits since 11-13 01:xx), slice_station__t6__cl0755c26e (SRC-INCOMPLETE 11-12, handoff FAIL-S81-1 only)
- s81_head: 0 failed / 1 not built (hd_lep0N, queued post) / 0 unowned
- qwen_compute QC: 0 failed / 5 not built (all named in DIE-QC-103 posts; coll_s, qc_cland_w515_n_d8_local32_codex only in handoff, SRC-INCOMPLETE/KIT_NOT_SELF_CONTAINED 11-14 06:xx) / 0 hard unowned
- qwen_kvsys KV: 1 failed (kv3_hgi_v6, plan-B owner TYPE-KVHGI2) / 0 / 0
Relaunched: none (no infra-kill items; no rc137/143/241 rows).
NEEDS-LANE class: GEN_LINT memory_bits over SYNTH_MEMORY_MAX_BITS (3 svc_hi types).

## Sweep 2 (09:10 PST)
Counts (failed / not built): s81 66/5 (was 22/8), head 0/1, QC 0/4, KV 1/0 (kv3_io_ft_v1 routed-not-signed TT 17.6 FF -168.5 late-ECO exhausted, no lane post found = UNOWNED).
s81 +44 failures = new Tcl class "global_place.tcl explicit FT site is not on a row/site" on col_h9/h10 types; owned by TL-COLH9R0P1..P6 (FINDING 06:01, shared cause #2), die owner DIE-S81-90. Also kv_leaf__t4 + serdes__t2 grt-timecap (21.6 ks cap, structural, serdes__t2 has HARD-S81-SERDES-1), leaf__t73 CTS flow error.
slice_station__t6__cl0755c26e: KIT-OPS-3 did not answer ASK. Not relaunched by me: last real attempt 11-11 failed PLAN KIT_TOPOLOGY_BIND_STALE (regenerate canonical bind/kit), earlier classes STRUCTURAL routed-not-signed hold -45.9 ps; a plain relaunch would repeat it. Needs a bind regen = design lane.
Relaunched: none. Next sweep ~10:10 PST.

## Sweep 3 (10:10 PST)
Failed / not built: s81 16/149, head 0/1, QC 0/4, KV 2/0. s81 not-built jumped because B3x2b plan swap created new col_h9/h10 identities; wave launched 94 in the last 60 min, so draining, not stranded. 14 of 16 s81 failed are DEDUP twins.
Now owned: slice_station__t6__cl0755c26e (TYPE-SLICE-HOLD ASK to KIT-OPS-3 09:06), kv_leaf__t4 (TYPE-S81-GRTCAP, cap removed), kv3_io_ft_v1 (TYPE-KVIOFT), serdes__t2 (TL-SERDEST14).
Unowned (no queue post): s81 ot_s81sl_leaf__t29 and qwen_kvsys kv3_hroot (both OT_HOLD_STRUCTURAL failfast), kv3_hgi_v3 (grt-overflow; KV-FTGRID 02:13 older than 90 min).

## Sweep 4 (11:10 PST)
Failed / not built: s81 25/149, head 0/1, QC 0/4, KV 0/0 (kv3_hgi_v3 and kv3_hroot cleared; TYPE-KVHROOT READY 11:05; leaf__t29 owned by TYPE-S81LEAF29). Wave launched 104 in 60 min (s81 80, QC 12, KV 10, head 2). 149 s81 not-built = col twins in DEDUP-RELEASE/wait, not stranded. QC not-built cores sta_region_nb0 / station_tail1 are WAIT-CHILD (prov_require_cands), owned by DIE-QC-103.
Unowned: s81 ot_s81sl_leaf__t28 (flow-error exit 11), s81 slice_station__t27 (grt-overflow, GRT-0116). slice_station__t6__cl0755c26e: TYPE-SLICE-HOLD ASK to KIT-OPS-3 (09:06) still unanswered 2 h.

## Sweep 5 (12:10 PST)
Failed / not built: s81 25/148, head 0/1, QC 0/4, KV 1/0. Wave launched 78 in 60 min. leaf__t28 (TYPE-S81-T29, lec_async fix live 11:50), slice_station__t27 (TYPE-SLICE-HOLD) now owned. QC/HEAD not-built unchanged (WAIT-CHILD / dsdv cores).
New unowned: s81 serdes__t3 (attempt 24, labelled INFRA but real cause is plan: "macro u_bound.u_core.u_prx straddles PG domain phy_lk_WN0", so relaunch will not help); qwen_kvsys kv3_hgi (STRUCTURAL grt-overflow GRT-0116, recorded 11:53, no lane post in 90 min).
slice_station__t6__cl0755c26e still unstarted; escalated 11:10 to KIT-OPS-5, no reply.

## Sweep 6 (12:10 PST, final, run on COORD go-ahead)
Failed / not built: s81 25/148, head 0/1, QC 0/4, KV 1/0 (same as sweep 5). Wave launched 78/60 min. Unowned: 0 after COORD assignment: serdes__t3 -> TL-SERDEST14, kv3_hgi -> TYPE-KVHGI2, slice_station__t6__cl0755c26e -> TYPE-SLICE-HOLD (private attempt 3 at place), serdes__t2 -> TL-SERDEST14 family. QC/HEAD not-built = WAIT-CHILD/dsdv cores owned by DIE-QC-103/TYPE lanes. Relaunched over the 6 sweeps: none (no infra kills found).

## Method change 18:10 (COORD): unowned = lanes/STALE.tsv row (no live job, >=6 h) AND item not named in a non-automated queue post or a handoff <6 h old. Script: lanes/handoff/UNOWNED-SWEEP-stale_sweep.py. Wave state ignored. Live ps/systemd check is inherited from STALE.tsv (not re-run).
