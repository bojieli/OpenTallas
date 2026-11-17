# PUBLISH-GATE Codex takeover 2026-11-16 22:18 PST

Clone intel2 /srv/opentallas-scratch2/claude/publish-gate/repo, existing branch claude/publish-gate-1116.
Unrelated dirty files in clone were left untouched; commits stage only owned source/test paths.

## Snapshot base source
1c33a1ac6b522a8a6fb2b5ddd5db5b6209a8dc03 (r460 APPROVED), normal GREEN150/150 on3eefb67d00a.
Actual D5 E8 dryGEN failure was NOT missing sidecar: snapshot000561 contains it under mirrored old-base.
Explicit asbuilt_manifest points into snapshot but manifest absolute base still old lane. native_contract re-rooted only absolute TABLE, not BASE.
Fix re-roots explicit snapshot absolute base before resolving table. Missing mirror and symlink escape refuse; live epoch never substituted.
Actual D5 snapshot reproduces all395type/ownership plus clocktable e630288, reset, transport against original bind receipt.
9 focused tests PASS. Source only; no published tree modified.
Gate1 log /tmp/pg/gate_snapshot1116_r2.out, E8 unit2181109-1794896722 DONE0.

## Exact inherited G0 baseline
Root-authorized policy: C3/s5f reviewed plan G0 has6 inherited errors, bind0/LAT873/873/FableGO.
Canonical record coord/lanes/handoff/S81-C3-G0-BASELINE-1116.json (coord5ae8c1defea5), SHA01c6f58d6de90c7c3a8dd1a0ee21d5c552177d05f9af548e5f5c6dd0431f6341.
Candidate marker.g0_baseline={path:ABS_RECORD,sha256:RECORD_SHA}.
Record pins reviewed plan c20ec9e4c3c4728dde433545b3dacd13418cf5c9296082d2fbd04cfb5dc50946 and originalG0report SHA plus full accepted ERROR dicts.
Only exact complete identity/context multiset subset accepted. No numeric/path masking; new errors, count mismatches, rc/report inconsistencies, checker crash, pending views refuse.
PRE/schema still require0, default no-baseline unchanged. New unique G0 output dirs prevent stale report acceptance.

Successor032333b42c6 implemented baseline; final45629bde775b0c8ae5674e33a5583e2ae68af832 also retains pending_view refusal. Focused8PASS.
Normal gates in progress, preserve:
-032333 E9 unit4149781-1794897050, client524353, /tmp/pg/gate_baseline1116.out.
-final45629 E2 unit2056924-1794897157, client566783, /tmp/pg/gate_baseline_final1116.out.
Root approval pending final GREEN. S81 die_geometry owns C3 contained D5b plan/bind/asbuilt package and actual static+dryGEN.
KV team owns D12/HG3b actual dryGEN; no duplicate KV or S81 physical launches here.

## Dispatcher coverage
22:20 last-hour class only KV kit_rtl4ab4e56491 (1); older3h S81 kit_rtl29+serdes4 same source-publication class, no new>=10/h event.
Exact33 S81 publication owner rows ->S81-TYPES-R2 committed01ff7a2214d2; current class owners now KV-R /S81-TYPES-R2, no orphan.
