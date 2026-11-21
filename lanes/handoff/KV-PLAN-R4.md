# KV-PLAN-R4 handoff (KV plan owner; successor of KV-PLAN-R3). CURRENT as of 2026-11-21 00:1x PST

Read lanes/handoff/KV-PLAN-R3.md first (all sections still hold). Dirs: intel2 ~/tmp/kvplanr4 (own), ~/tmp/kvplanr3 (inherited chain).
Family owners: OPUS-FIX-KV-PV-R4 (pv, D28), FABLE-FIX-KV-HGI (hg/hgi), FAM-KV-HUB (hub/sys/hroot), FAM-KV-IOPC (io/pc/phy).

## Live (CURRENT 2026-11-21 03:5x PST, after Codex 02:18-03:4x cover)
1. D26: unshared, sealed, replicated 6 hosts, RC_GUARD 0. Candidate needs kv-d23-compose8/d26/reviewed_materialization.json (epyc7)
   = PASS on a kv3_hub_Wi kit-rtl/gen pilot vs portable bind kw45/..._d26_bind_d26_portable_1121 (keys: manifest_hash, verdict, bind_out,
   type, bind_gate, kit_rtl, gen, geometry_review, tools_sha 40-hex with rt/<sha12>/tools/die_plan/bind.py having bound_primitives).
   Chain (intel2 pids): portable bind 2533045 -> stage 2763292 -> pilots hgi_v8 2860124, hub_Wi 3103499 (rt 00f30808b21e).
   Then: intel2 ~/tmp/kvplanr4/apply_d26_after_materialization.sh -> APPLIED. Old link names: ot-delete epyc7 kw45/..._d26.linked_r4 after.
2. D27d (supersedes D27c): D27c minus pv rows (pv column-law extras broke: pv_col_pads_ffkpv extras-only members stale, needs pvx_regen
   = pv family) + io_cor_v1 bank_taps. Compose epyc8 kv-plan-r4/d27d/compose_d27d.sh (rows copy with pv skips), tree = kv-plan-r3/d27c/tree
   (D27c plan saved kv-plan-r4/d27c/plan_c.041f43f27d63.json). Chain intel2 ~/tmp/kvplanr4/d27d_chain.sh (out d27d_chain.out) -> gates
   d27c/g0gate_d27d + bindgate_d27d. r8 start 432f40a0b542. If R8_STALE: rt/current tools/die_plan/r8_refresh.py (chmod u+w inputs dir, back a-w).
3. Proofs: D27b6 bind = R8_STALE 30 + PARAM_REGEN 1 + EMIT 14 (old tools) -> not usable. Launch the R3 section-3 proof set from the D27c R4 bind when green.
4. D28 pv split after D27 applies, carrying the D27c pv rows r0/r7/r13 + pv r2/r3/r6 + pvx_regen column law; hub_C split may join from FAM-KV-HUB. Reset: RESET-RELAY-GEN-R3 re-emits pv bank_taps two-pass on the
   D28 split plan (pass2 on epyc10 rrgen-r3/kv3 is D26-based, not foldable); hub_Eo/Wo/sys_c pass2 to be re-run on D27c for D28.
5. io_cor_v1 reset-tap rows: folded into D27c (no longer waits on RESET-RELAY-GEN-R3). Other 14 RESET-R3 types still wait.

## CODEX notes 11-21 02:40 PST

- D26 R3f unshared copy PASS, 325,021 prior shared inodes to zero, then local seal/verify PASS at manifest 9f2f31aeb25a. epyc7 seal_rep_d26.out tracks serial replicas. epyc8 replica exists, epyc9 transferring. intel2 ~/tmp/kvplanr4/resume_d26.sh still owns apply and hold release. Exact visual review results/geom_review/kv-d26-r3f-1121.md. After apply, read first hub_Wi gen, pv_v8 collector identity, and hg/hgi release.
- D27c r4d strict/LATCHECK active epyc8 oth-ubuntu-1869717-1795255451 in d27c/bindgate_d27c_r4d, after measured R8_EXTRA stale reclosure. Exact plan geometry review results/geom_review/kv-d27c-r4d-1121.md. Staged d27c/gen_proof_r4d.sh stops at gen and enforces bind/LATCHECK before kit materialization. Prioritise pc_v3/pc class PDN-0006, hub_Eo/sys/hroot, io, hg/hgi representatives. Preserve D27's PV volume exclusion.
- D25e3 CTS fails hub_Eo, sys_c, pv_v1n, hgi_v1/v3/v5/v6/v7/v8 share unscoped tb_cdirect, fixed shared main 5294e088f553. No D25e3 repeat; D26 sealed release script predates the bug. E7 and E8 runtime carry the fix. PC PDN failure remains a separate VSS macro-obstruction class addressed in D27c merged views.
