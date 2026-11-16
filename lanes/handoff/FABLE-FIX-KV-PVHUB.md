# FABLE-FIX-KV-PVHUB handoff (owner + decider of the open KV types; started 2026-11-16 05:45 PST)

Read first: lanes/handoff/KV-PVHG-O.md (existing Opus lane, keeps hg v25hv + pv k2 + pilots), KV-102.md.
Work dir: epyc9 /srv/opentallas-scratch2/claude/fable-fix-kv-pvhub (mktree.sh, run_gate_v2.sh, h/); logs intel2 ~/tmp/ffkph.

## Cause (measured 06:00)
kvgeom7yhr 723fd5b4b006 passed every gate at 03:59 (intel2 ~/kv102g7/gate_kvgeom7yhr.log ALL_DONE) and had the
no-blocking review at 02:01, but KV-102 has not posted since 01:54, so nobody posted READY/ADOPT. 13+ items are held on
event_adopt:kvgeom7yhr. That gate also ran on the c1 tree (main 8989ba7b1755), which lacks tt-keep and the KV RC x1.10.

## Decision
Adopt 7yhr on the v2 tree, not on c1. Event tree = real cp -a of kw45/src_kv_pin_eb1e73448bd0 (manifest 6dd08c2a09b4) +
plan 7yhr: epyc9 kw45/src_kv_kvgeom7yhr_eb1e73448bd0 (nlink 1, FFKPH_OVERLAY.txt). v2 already has r224, r249, r266 and
the pv_join RESET_PIN record (file-compared with the gated c1 7yhr tree), so no overlay is needed.

## In flight
- Gate (HCPARAM on) on epyc9: ot-run log intel2 ~/tmp/ffkph/gate_7yhr_v2.log, result epyc9 fable-fix-kv-pvhub/kvgeom7yhr.gate.out.
  Bind of record is written at its final path kw45/kvbind_kvgeom7yhr_eb1e73448bd0/out_h1. kit_rtl smoke for pv_v1n, hroot,
  hub_C/Wo/Eo, pv_v1/v7/v12, pc, pc_v1, sys_c; gen phys for hub_C, hub_Wo, pv_v1/v7/v12, pc, sys_c (reads the pv_join header class).

## Next
1. Gate ALL PASS -> copy tree + bind to epyc7/8/10/intel1 (real copy), READY+ADOPT to KIT-OPS-5/7 + HOLDGEN (event kvgeom7yhr).
2. KV-PVHG-O composes v25hv (and k2 when gated) onto this tree as the next event KV-HG1; pilots hg_v1, hg_v3, pv_v1n.
3. Read the first hub_C / hub_Wo place on 7yhr (ring_place ff) before any further hub row.

## CODEX takeover 2026-11-16 10:01 PST
- 7yhr continuation remains active epyc7 fable-fix-kv-pvhub/kvgeom7yhr.gate.tail.out; pv_v7/v12 kit+gen PASS. Do not rerun it.
- epyc10 source delta sync finished (intel2 client134114 exited clean); source renamed to final by HG1 setup.
- HG1 compose at epyc10 fable-fix-kv-pvhub/hg1: compose.py merges dictionaries + lanes by ID, refuses overlap; v25hv relative to7uh ->7yhr, then k2r relative to7yhr ->combined, then rows_reach.json. No change to the15 KV d2d lanes. plan_hgpv sha f62f4eb418c5, plan_hg1A carries13 START rows. Final clock sites/windows MUST be regenerated on composed tree.
- HG1 admitted full-tree setup/pre/G0/bind/LATCHECK: intel2 client185051, tmp/ffkph/codex_hg1_gate.log; epyc10 fable-fix-kv-pvhub/hg1/setup_gate.sh, output gate/. Copy48GB underway. No source edits to published tree or running kits.
- p1 die proof collected: GRT0 TT/FF; CA3915/3915 PASS, intra/seam TT+482/+510ps, FF kit-contract hold+0.01/+11.52ps, real measured hold0/unproven. p1 strict bind fails standalone qk1 path resolution (INPUT-MISSING x5), not physical design. Full-source HG1 compose resolves source-root cause; no override.
