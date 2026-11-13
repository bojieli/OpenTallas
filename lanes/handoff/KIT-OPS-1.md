# KIT-OPS-1 handoff (kit-wave operations lane; COORD is the coordinator) -- 2026-11-13 01:31 PST

## Done 11-13 (RESULT posted for each)
- (1) q_su30 held + stopped (00:11).
- (2) HBM pEv10 (01:16): 8 types launched. Event pEv10, plan epyc8:/srv/opentallas-scratch2/claude/kit-ops-1/hbm_pEv10/plan/die_plan.json (b334c92f7a84), src kw45/src_hbm_main_7073a6b4a5 (plain archive + RA=0 overlay), kit_rtl bind_out hbm_pEv10/bind_w, asbuilt hbm_pEv10/asbuilt_kitops1w.json. Revert = hbm.prev_kitops1_pEv10. Switch script: scratchpad hbm_pEv10_switch.py.
  epyc7 restored to hbm.gen_hosts (copy verified). The 42 held types: release exactly what DIE-HBM-102 posts. n4ext stays off the wave until DIE-HBM-102 gives it a form.
- (h) HEAD rp18r2 (01:27): plan kit-ops-1/head_rp18r2w/prep/source_plan.json 6d283b65ff9a; hd_spn + hd_mesh launched. Revert = s81_head.prev_kitops1_rp18r2.
- Train 29 merged: the S81 proof overlay line is dropped (an appended DROPPED line in KITOPS1_OVERLAY.txt, 5 hosts).
## Standing
- RA=0 overlay: drop when the wave src moves to a main containing train 30 (backups kit-ops-1/ra0/bak).
- Awaiting COORD: the 6 QC sle/slw_st kits (DIE-QC-100 WAIT-FORM).
## 11-13 02:1x
- Recipe-loss class: overlay #2 = KW-FIX-45 macro_skip_rtlmp (kit-ops-1/ms0, ms_overlay.sh) in src_hbm_main_7073a6b4a5 and src_kv_main_66e6607e3f on 5 hosts (gen_phys 3d5beb3720f5bfeb). PHY_NC/PHY_NW relaunched 02:07. READY claude/kit-ops-1-phy-skip-rtlmp-1113@427c251f4c; when MERGED (plus train 30), move the wave src to that main and drop both overlays.
- (i) Released root/q_spt1/q_spt2/vsN4/5/6 (+ xtap route holds). q_spb1/vsN1/vsN2 stay held for pEv11. q_spt2 has no row (OWNERS SIGNED-UNVERSIONED).
- (ii) ARMED: when ROOT-MERGE-61 posts train 33 MERGED (HBM pEv11c, plan c9ac33aeb09c, events/hbm_pEv11_1113), repeat the pEv10 switch: archive the new main, bind with the package recipe, run ra0 + ms0 overlays, probe old vs new, re-kit only the changed types (q_spb1, vsN1, vsN2, NW_io, q_b113 + probe), release the xtap holds on q_spb1/vsN1/vsN2, keep unchanged pEv10 keys, post a RESULT.
## 11-13 03:1x
- (ii) DONE: HBM on pEv11c (src kw45/src_hbm_main_d6b0b70323 + ms0 overlay; bind kit-ops-1/hbm_pEv11c). epyc7 out of HBM gen_hosts until its copy (copy_units pid 281144 on epyc8) verifies with manifest 7b8be3ee/8e24f2cb; then restore gen_hosts_prev_kitops1_pEv11c.
- take_states += SIGNED-UNVERSIONED (hbm) and a q_spt2 hold (KIT-OPS-1 xtap): revert both once q_spb1/vsN1 are past launch.
- Overlays: trains 34 and 35 MERGED 03:08. Drop RA=0 + ms0 at each die's next src switch (HBM, KV).
- epyc2: DISK-E2 cleanup removed die-hbm-92-*/ab sources and qc-transport-fix-4/src_sw2; restaged 03:1x.
## 11-13 03:4x OWNER DECISIONS
- visual_gate "signoff" live (branch claude/kit-ops-1-visual-signoff-1113@b73feceda8, deployed to kw38/rt; backup kit-ops-1/rt-bak-visual-1113). READY posted. Revert: visual_gate "route".
- HBM parked: hold_items "*" PARKED-OWNER-1113. Freeze to 2026-11-15 04:00: no src/plan switches; overlays stay.
- epyc2 qc-transport-fix-4 deleted twice (02:51 DISK-E2; ~03:32 unknown). Restaged from epyc9. Watch it.

## CODEX notes — 2026-11-13 13:47 PST KIT-OPS takeover
- Frozen QC s28 missing-input class repaired: restored qcs28in/bind_plan_qc99_s28 (445 MB) and sidecar_pv_s28.json from exact epyc8 donor to epyc4 + epyc2, rsync --ignore-existing. Checksum dry-run returned no differences. epyc2 kw45 resolves to scratch3 already (504 GB free); scratch2 141 GB below floor untouched. No plan/src/config switch.
- HEAD original head_rp18r2/prep asset tree (29 MB) was missing on E7/E9/E2/I1 although prepared plan receipt names its sink_bins_4.json. Restored exact epyc8 donor with --ignore-existing on all four. hd_host_e old-script input now present on every gen host. Armed ONE infrastructure re-launch hd_host_e@5; backup autopilot/kit_wave.json.bak-codex-head-input-1113. hd_mesh WAIT-FORM and hd_spn superseded left untouched.
- Healthy six R-FLOW launches13:41 retained. HBM PARK and freeze retained; no HBM source work or launches. AUTO-RESIGN untouched.

- 2026-11-13 14:17 PST CODEX milestone: HEAD required original receipt_inputs now declared in kit_rtl, consumed by existing host preflight and cleanup protection. All11 receiptassets SHAchecked once. After scheduler clears staleepochs, one-shot rearm fired14:02:55; host_e@6 PLACE14:07, turn_a@5 PLACE14:16, wshim_rx@4 GEN14:15. Source failure fixed, physical results pending. Watcher ended normally, no live rearmprocess.
- CODEX reviewed-bad S81t62a3: exactroute ID2d5aa4b69de5 appended supported withdrawal coord/state@d8c7795beda8, runtime14:03:09 says nojoblaunched/noevidenceremoved; negativeverdict path likewise CANCEL units[]containers[]keptdata. Exact route_hold_items retained until combinedevent.
- Source safety: E7 wt/qc-clkgate-1 orphaned gitdir sourceintact; .keep set and tools345MB+clock scripts180KB preserved under qc-clkgate-1/source_preserve_1113 (no gitrepair).

- 2026-11-13 14:47 PST CODEX: hd_host_e@6 source-staging achievedPLACE but actualimage remains historicalsameform ISSUES; exactroutehold set, noadmittednewroute. turn_a@5GOOD andwshim_rx@4ISSUES-ACCEPT actualimages byGEOM. hd_ctl_n currentacceptedISSUES-ACCEPT, oldjob992b8a45f39a DONE-CRASH DRT0255 M8RA0missing; currentfrozengenerator verifiedwritesRA0, normalone-shot staleepoch rearmfired14:45:32. Exactctl_n fresh-attempt imageholdbeforeanyroute; watcherkit-ops-1/codex_rearm_ctlra0_1113.py/log ended, originalfailedrecordkept.
