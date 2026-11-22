# FLOW-FLEET-R1 handoff (Opus 5.5, lane for COORD; source lanes/FABLE-FLOW-2200.md)

**EXPIRY 2026-11-23 06:00Z: epyc7 /etc/ot-heavy.conf LOAD_CAP_FACTOR=1.2 (owner FLOW-FLEET-R1). Renew (edit the #@cap expires=) or revert to 0 (value in /etc/ot-heavy.conf.bak-fleet7r1-1122). Shown hourly in FLEET-OPS-R host report HOST-CAPS line (main fd7e7d78a9).**

Lane clone: epyc9 /srv/opentallas-scratch2/claude/FLOW-FLEET-R1/repo (cone tools,bin,tests). Scratch tmp: .../FLOW-FLEET-R1/tmp.

## Item 1 epyc7 thread cap: DONE
- epyc7 THREAD_CAP_FACTOR 1.0 -> 0 (bak-fleet7r1b value); LOAD_CAP 1.2 kept with `#@cap ... owner=FLOW-FLEET-R1 expires=2026-11-23T06:00Z`.
  Pre-change copy /etc/ot-heavy.conf.bak-flowfleetr1-1122. Admits resumed (0 not-admitted on epyc7 since 22:00).
- main 3eb6e99f80 tools/fleet/host_caps.py; wired into intel2 fleet-ops-r/host_report.sh (HOST-CAPS line).
- TODO 2026-11-23 06:00Z: LOAD_CAP expiry -> revert to 0 or renew.

## Item 2 GRT-STUCK: DONE main 403477dcd9 (live in rt/current)
- COORD ruling 11-22 applied main 30b1f11ad5 (live): GRT-STUCK + NO-PROGRESS on lane-own kits (kit-wave .../private/<LANE>/ or lane scratch dir) = REPORT-ONLY + one NOTICE to owning lane, never auto-cancel; wave kits still cancel; CANCEL-NOW and UNSIGNABLE (NOTICE+KEEP) unchanged.
- 22:xx table: 2 GRT-STUCK REPORTED (sle_ctl padW5 epyc10, kv3_hgi_v1 intel2), cancel next pass.

## Item 3 tree copies + .fork.json: DONE main 36c00658e2
- src_manifest ignores .fork.json; copy slots (OT_TREE_COPY_SLOTS=2, /var/tmp/ot-tree-copy); replicate same-manifest reuse;
  ot-tree-fork --src-host (reuse / fetch once to <scratch>/claude/tree-cache/<hash16>).

## Item 4 count drift: DONE main 9a1daba2ca + coord b37338c787 (tools/archive_gate.py)
- 437 -> 430/431: 19:14 FLOW-LECGATE-R1 COUNT-REVOKED 24 PENDING-LEC rows (deliberate LEC gate, defer rose 15 -> 22).
  Their relec jobs were refused on epyc7 by the thread cap (item 1) until 21:55.
- 5 uncounted: archive gate looked types up by key only (t36, slw_sc_v2 archived under top module) -> fixed, S81 +1 QC +1;
  AUTO-EXPORT starved 19:15-22:2x by CLEAN-AGGR-R2 manual `drain --scan` runs (epyc10 scan hung 59 min; killed exact pids
  2750745, 2754377 intel2, 2275000 epyc10) -> sle_hc2 pvcf529cc9/pv0d63d22b unexported; fix: spools first + re-poll during scan;
  closed relocation copies (pv41c959f3, sle_hc0 cl38badc56) now exported. slice_station__t52 is PENDING-LEC (COUNT-REVOKED), not a bug.

## COORD item 11-22 symlinked-plan class fix: DONE main c7cf2178a9
- tools/die_plan/tree_write_guard.py wired into r8_refresh.py, land_r8_derive.py derive --out, ot_build in-place choice; ot-tree-fork PLAN links (refuse / --materialize, verify PLAN-LINK); kit_wave private_tree_plan_link_refusal.
- Audit lanes/handoff/TREE-LINK-AUDIT-1122.tsv (37 lane-dir trees linking out; 3 live FABLE-PIPELINE-R1 ot-build launch trees). Post 6878853ae3.

## COORD item 11-22 lever 7 landing band x core G0 check: DONE main b7e262fd60
- tools/die_plan/landing_band_core.py + check.py wiring (ERROR landing_band_core); existing findings S81 t3/t32, KV hg/hgi (16) posted.
