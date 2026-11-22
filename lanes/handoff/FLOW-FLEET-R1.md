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
- COORD ruling error-on-new/warn-inherited + own-core exclusion: main b40d177ee8 + 53fba95dad; per-die list lanes/handoff/LANDING-BAND-CORE-1122.tsv (HEAD r17b 14 new hd_lep0N; QC V3 11-13 new; S81 2 / KV 8 inherited).

## Item 5 FABLE-FLOW-0000 F2/F3/F6/F7/F9 + DEATHCLASS 1-3: DONE (pushed)
- F9 main 2363679a9d: auto_export reads intel2's own spool (was missing from HOSTS); items >2 h retried once then set aside to spool/failed/<f>.reason; canary/test aside at once. Verified: intel2 canary records set aside 00:00.
- F3 main fbc8d99350: tools/fleet/tool_copies.py (TOOL-COPY line in fleet-ops-r/host_report.sh, ALERT >24 h). intel2 crons flow_health / ot-reaper / limit_outage moved to rt/current (backup ~/.local/state/crontab.bak-flowfleetr1-1122). Left: autopilot.service dead wt fallback path (reported ALERT); rtx-pro ~/.local/bin/ot-run is a Nov 14 copy (no rt/ on rtx-pro).
- F6 main 67607c6e47: UNDER-USE headline = measured load, committed threads beside it; cpu <70 % with rows waiting -> "BLOCKED ... top bucket".
- F2 + DEATHCLASS main bdc4b147c2:
  - ot-run --cancel SUBSTR --reason hang|design|infra (default manual); client prints OT-RUN-CANCEL reason=<r>; kit-wave books non-infra as CANCELLED class MANUAL-CANCEL (no free INFRA retry).
  - kit-wave HANG: place/cts/grt/route row with no stage-log output 90 min while CPU grows -> HANG-REPORT, cancel 30 min later on the same frozen log (option hang_output_min 0 = off). Private kits stay report-only (noprog lane-own rule).
  - SSH-DROP: cause = fleet names are ssh aliases (no DNS anywhere); on non-hub hosts `--hosts localhost` probed `ssh localhost` -> Host key verification failed -> NOT-RUN 78 (reproduced epyc8). canon_hosts() maps by `ssh -G` HostName vs local addrs; probe retries rc-255 resolve/transport 2x (2 s, 4 s). Old intel2 "Could not resolve intel2" logs are 11-02/03 (pre HUB_SELF).
  - RAIL-KILL: all pinned hosts held/draining/refusing -> one PIN-FALLBACK to pinned+pool with spill on; --strict-host keeps the pin.
  - SETUP: relative script / --stage missing on every --dir host -> NOT-RUN SETUP; --dir existing nowhere -> NOT-RUN SETUP message.
- F7 main bdc4b147c2: tools/autopilot/uncounted_signed.py; intel2 cron :25 (runs once rt/current has it) -> lanes/UNCOUNTED-SIGNED.md + one NEEDS-ACTION per new row. Dry run 00:2x: 20 rows (18 PENDING-LEC incl t52 + QC slw_hc3 x4; QC sle_st_b_v2 archive key 8.3 h; 2 fable-fix-kv-hub export set-aside, rtx-pro unverified).

## Item 6 COORD rulings 11-22 01:xx
1. epyc7 LOAD_CAP: user unit ffr1-e7-sample on epyc7 samples Dirty / dockerd D-state threads / load / units every 60 s until 2026-11-23 05:00Z (.../FLOW-FLEET-R1/tmp/e7_sample.tsv). First 26 min: max Dirty 98 MB, dockerd D 0, load <= 79/96. That is not full admission, because the 1.2 cap binds only at load 115. Decide at ~04:00Z: if max Dirty < 4 GB and D = 0 in samples at load >= 96, let it lapse (cp /etc/ot-heavy.conf.bak-fleet7r1-1122 values: LOAD_CAP_FACTOR=0); otherwise renew 48 h. Since the stall, the disk has gone from 92 % to 79 %, and vm.dirty_background_bytes is 1 GB.
2a. sle_st_b_v2__cl14c98df5__pv41c959f3: CANNOT EXPORT. Both signed copies were deleted before export: epyc2 attempt_2 (scratch3 eco signoff) by ot-auto-retire 11-21 17:01, and autopilot/closed/...pv41c959f3__eb1e73448b (signoff_eco_1795305239091771775, 1.6 GB ODB) by ot-delete 11-21 19:24 (manifests in epyc2 ~/.local/state/delete-manifests/2026-11-21/). It is in neither the export ledger nor INDEX. Needs a relaunch (QC-RELAUNCH-R1 private kit exists). Class bug for the cleanup lanes: a SIGNED unexported record was deleted.
2b. The fable-fix-kv-hub exports were blocked by an rtx-pro DISK HOLD (free 100 GB = reserve). Disk freed to 129 GB and the pull went through 00:22-00:48: zh ot_nhb_zh__ax_980bd1af62 + qkd_ahub__ax_00bf38a3f4, plus 8 more held units (s81 t41, t49; qc sle_hc1 cl7d360508, sle_st_b_v2 clfde1249e, sle_hc0 x3, slw_fw_v1). The zh spool item was re-admitted from spool/failed; the hub drain finished it (ledger done). The other kv-hub item (epyc7 qkd_ahub eco2) was already done. RISK: rtx-pro / is at 97 %, 109 GB free against a 100 GB reserve, so the next ~9 GB of exports will hold again.
3. 18 PENDING-LEC rows sent to FLOW-LECGATE-R2 (ab781683b253d9a33). It says all 18 were already in its queue: slw_fe_v1 cldb4efe33 counts again (new EQUIVALENT sign-off at 23:39), 4 slw_hc3 KEEP FAIL (HCST-R3), 2 s81 UNPROVEN, 5 wait for rebuilds, 2 failed staging, 2 lost.
4. rtx-pro ~/.local/bin/ot-run is now a symlink to ~/.local/lib/fleet/ot-run-main/current/tools/fleet/ot-run (git archive of main 3b1cea8bec21, includes bdc4b147c2). Old copy: ~/.local/bin/ot-run.bak-flowfleetr1-1122. `ot-run --pick` works. There is no auto-refresh yet; to refresh, repeat the git archive. A stray first extract sits at ~/.local/lib/fleet/ot-run-main/.stale-d7b8 (rtx-pro has no ot-delete).

## Item 7 OWNERS from bound plans: DONE main a90c6d61ab
- ownership.py + autopilot.ownership_inputs read kit_wave.json dies.<die>.plan/src (follows every apply); parked HBM keeps main d44f. Live check: S81 a9ed808a98d / HEAD r17b / QC R6V2 / KV D27d3 bound plans, all pins resolve; 2 S81 ghost NEEDS-KIT rows (ot_s81dv_xfin, ot_v41_rom_elem_q_qxpq_w10) drop at the next OWNERS tick.
