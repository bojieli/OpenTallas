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

## Final integrated source (22:4x PST)
- 45629 normal RED: auto-retire's newly added rollback fixture called production apply without the existing PGOK-qualified helper. Exact failure retained E2 slot0/mq/failure-output/gc-45629*.log.
- 1ab5e1438fd corrected the fixture only; its normal gate reported add/add conflict with main's new rollback test. No production bypass added.
- Temporary same-lane integration worktree /srv/opentallas-scratch2/claude/publish-gate/integrate_1116 preserves original clone's18 inherited dirty files untouched.
  Plain merge main800d3f3a9c44; sole add/add test conflict resolved hunk-by-hunk using qualified helper while preserving rollback expectations/current main production.
- FINAL source6cf4d562fab3b500de50ab9a1fc59f97f9fc1b8e pushed same branch+GitHub.
  NORMAL GREEN13/13 on800d3f3a9c44, gate E9unit57848-1794897831 DONE0, record ~/merge-queue/gates/6cf4d562fab3b500de50ab9a1fc59f97f9fc1b8e.json.
  Focused baseline8+rollback1 PASS in merged source. Actual C3 report6PASS; same-count new-message mutantFAIL.
- Root canonical READY posted; approval/merge root-owned. Die teams own actual static+dryGEN/adopt.
- Approvedr460 snapshot twofiles staged E8 tools-converge/s81/d5b_1116/tool_overlay/tools/die_plan:
  kit_topology.py SHA8ea28749c3f11453ed12565be5509c169eaada47765f90d3a5b3b95d2501c412;
  test_native_topology_base.py SHA442cf1bee9b101c05bc6584295bf01d3bcc40cae754d963d9a854a1345606834.
- Old D4 G0 rc1/reportPASS confusion is not reproduced: actual E10 /runs/s81/kit-wave/pubgate/g0/g0_report.json at21:43 reads FAIL6.
  Fresh unique output directories in new helper avoid stale result authorization.
- All my source gates terminal. No physical job launched. Keep integration worktree until S81/KV helper users switch to merged runtime, then remove it.

## Publication PRE CPU admission, 2026-11-26

- QC 77f2's stock raw SSH static launcher had one unadmitted PRE tree with 106 descendants, about 72 runnable. Roughly 60 other runnable CPU workers were normal ROM image scopes declared and running at four workers each. E8 exceeded its normal 115 load cap. Existing jobs, stock die bind budgets and host policies were left in place.
- Candidate `acb1b70887044bd1073709a1e0b5c0a3644dca40` keeps exact prepared input paths and the typed `PG_STATIC` result. It admits a local PRE scope bounded by affinity and declares its worker count to the actual PRE fork pools. Qualifying inherited local leases are reused. Default request 32, optional `OT_PUBGATE_PRE_THREADS`. This publication call uses the existing ordinary-admission flag without changing fleet defaults. E7 fresh scope measured 7 PRE workers and Intel1 nested lease reused exactly 4.
- Two initial branch fetch holds were due to the fleet's bare mirror not yet holding the exact ref. The routine targeted fetch from origin registered the branch. The first actual gate exposed an inline checker context regression and a stale literal-nice fixture. Both are fixed in the successor. Exact E7 gate `oth-ubuntu-3516375-1795764123` GREEN 8/8 on main `eca7f429a3f`, rc0. Activation is root-owned. The running 77f2 PRE was untouched.
- The exact approved PRE candidate merged at 23:30:17 PST into main `d2064556a392e514cc249ad2f875ac08e4e09efb`. The Intel2 coordinator's normal `rt/current` activated the change. Existing jobs keep their pinned runtime.
