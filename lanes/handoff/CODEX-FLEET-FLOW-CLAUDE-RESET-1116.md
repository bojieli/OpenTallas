# Fleet/flow handback — Claude reset 2026-11-16

Root ordered stop new launches/edits/validation; children acknowledged. Existing fleet jobs continue. This record is a handoff, not a new verification.

## Explicit review holds — do not orphan

Canonical complete held/released ledger: `lanes/handoff/CODEX-S81-REVIEW-HOLDS-RESET-1116.json` (exact copy of live `autopilot/codex_s81_gen_review_freeze_1116.json`). The live ledger remains authoritative if the review owner completed a release while this copy was made.

- Latest delivered state: target29/29 dispatched; 10 actual geometries reviewed, including two early t24 PLACE runs plus eight reviewed/thawed controllers. Remaining19 intentionally held for existing review-before-physical rule: 15 release owner `/root/s81_plans/clock_reach`, four `/root/s81_congestion` (t14/t45/t46/t8).
- Two original held controllers (t40 cl1ea and t28) use systemd cgroup freeze. Root sanity check proved actual remote `gen.py phys` payloads were running, not rsync/wrapper (PIDs893172 and1183077 at that check). Release **after owner approval** with `ssh intel2 systemctl --user thaw <recorded-hub-unit>.service`.
- Other17 use SIGSTOP on the exact recorded hub Python run-item controller; local ot-run/SSH/rsync continue, remote GEN continues. Release **after approval and exact PID/spec identity check** with `ssh intel2 kill -CONT <recorded-controller-pid>`. Never signal remote GEN or a pattern of processes.
- Ledger includes exact units, PIDs, specs, work paths, methods, release owners, images and approvals. Eight earlier cgroup holds were thawed immediately and FreezerState running verified.
- First2 t24 cl648a2/cl66a20 had already entered actual remote PLACE before correct hold. Wrong `.service` lookup caused the missed boundary; ot-heavy uses `.scope`, now LoadState and actual payload verified. Owner subsequently looked at actual outputs: VALID; no byte-identical prior image claim (station spacing differs). Active PLACE preserved, boundary miss explicitly recorded; no retroactive prior approval. Actual image `/tmp/regen_actual2.png`, owner copying record/image to ep9 reach_codex.
- No KV controller holds: watcher1179161 already terminal THREE_REVIEW_BOUNDARIES_RECORDED, all3 ENDED_BEFORE_HOLD. No KV STOP/CONT signals.

## Temporary EP9 capacity control

Exact tag `TEMP-DISK-EP9-1116` was added to `/home/ubuntu/.config/ot-run/held_hosts` on intel2,intel1,epyc2,epyc7,epyc8,epyc9,epyc10. It blocks NEW admission only; existing SVC/GEN/PLACE untouched. Preserve other existing holds, notably retired epyc4.

Cause measured once: at least seven simultaneous rsync receivers copying the SAME `/srv/opentallas-scratch2/kit-store/snaps/89a70fcda26c60ad1e3cad227eb2d69858fba668/.../out_ctx2/bind_sinks.json`, each with a distinct temporary file, 48–85MiB/s. Free scratch oscillated133→43→130→73→133GB as transfers completed. Existing SVC dirs were only~150MB, not the cause. No writer was stopped/killed.

Remove ONLY lines containing `TEMP-DISK-EP9-1116`, on all seven clients, after actual duplicate temporary transfers drain and measured remaining headroom/reservation fits the next stage. No floor override/permanent drain. Prefer ready physical work ep7/8/Intel1 (subject to current admission). Do not remove unrelated ep9 holds if one was independently added.

## Actual source/runtime and dispatch

- Rootr331 adopted S81 F2s3 D2 tree `/srv/opentallas-scratch2/claude/kw45/src_s81_pin_3c913dbdfb23_f2s3_mainref_pg_d2`, hash aed3b3e059b20904d0125d0b89e6c8d0c0ce561247674c237df75a8db2d3d8a3. PortableAB65649... and out_ctx2 are in sibling s81bind directory. Exact tuple/proofs canonical `tree_switch_s81_F2s3_D2_portable_proposal.json` and adopted `tree_switch_s81.json`. Source/native395, LAT873, normal manifest0, actual station KITRTL0; source and bind replicas ep9/10.
- Keep accepted commit event3fa87b84b18 (S81 gate requires a commit); F2s3 typed event terms match plan filename. Declared plan SHA ed968f4cc6e6734b9b9d826e2e0c5bee74a220d8e55074f9a73fdc3e715f0e0d. Full source identity3c913dbdfb23d46e6efd5c985186c2b0f3b2a0e6, queue source same. No pinned old launch was relabelled.
- All source/physical holds retained:216col/16svc/exact6 measured-failed SerDes. Exact6 GEN+ROUTE holds require result:FABLE-FIX-S81-SERDES:serdes-corrected; no speculative t16 hold. Only generic source/lint and two SVC source-event terms rekeyed to successor F2s3 with real physical result terms retained/history kept.
- D2 source pollution repaired: four CAS and four inactive BK kit_inputs aliases detached byte-identically; original published inode/mode0444/hash unchanged, allnlink1. Evidence ep9 genbug-impl/snap_alias_repair_1116.json. Initial c703 hypothesis was filename-only, not inode; no c703 changes. Both-host source guard fresh normal readonly/unshared323266-file inventory+links_only PASS, exact result bb0b455... under autopilot/tree_checks, no JSON edits.
- Actual critical runtime c4b966db88d70017e642596f9a999305df70cc66 synced all six hosts12:53:22, includes1126+4677+ee39+e2e. One ordinary AP pass dispatched target29station/29 and KV C2/Wo2/pv26. Station dispatch artifact `lanes/handoff/CODEX-S81-REGEN-1116-D2-DISPATCH.json`; sample t24 constructors/topology all0. No whole-wave validation performed.
- Supported S81 breaker_fix tag names approvedr334 e2 source/CAS fix, set only after actual sync+fresh matching D2 source receipt; asserted only two open S81 classes, bothsrc_manifest. No state clear. Inactive obsolete source probe still needs gated a76 lifecycle bridge.

## Remaining KV blocker and parked source work

- KV adopted source431292... plan723fd5..., portableAB7f285.../out_h1_ctx2. All3 actual KITRTL constructors0. All3 then failed kit_topology before GEN: missing actual eW_sidecar in immutable old snapshot550ac5... . GEN and physical NOT_RUN; old failed snapshots untouched.
- Exact cause: required clock table is ALSO generic gen_args input; generic under_src in_place wins seen-dedup before required mirrored-copy dependency. GENBUG fix5a98a21325819dcd4d2d689db41423b5c4d12471 prioritizes required capture. Actual portableAB+table snapshot proof passed; no constructor/bind replay. Proof ep9 genbug-impl/kv_clock_priority_actual_1116/result.json. Normalgate owner merge_ops; last known queued/running, no new post-reset check.
- Sole full NEW closure capture already launched before reset: intel2 client1334843, log `/tmp/KV_full_snapshot_5a98_1116.log`, ep10 `tools-converge/kv/capture_KV_full_snapshot_5a98_1116.py`, immutable helper5a98 (fileSHAed6c460...). Expected `KV_new_snapshot_closure_receipt_1116.json`. Result intentionally uncollected after reset. Existing job continues.
- Old missing-input failure gate points at immutable old snapshot; proposed verified NEW closure receipt fingerprint release is NOT IMPLEMENTED. kv_pack owned proposal: prove new logical eW table expected SHA/context/file presence; wrong/same/unverified input must stay held. Do not churnAB/clear keys/mutate old snapshot or blindly retry.
- Future transport coalescing PARKED clean/pushed8b8f98ccb9fd3384601e0d98b33a84d27a771d48 on inherited claude/rc-signal-1115, ep9 fable-genbug/wt.37 focused cases pass. Destination per-snapshot/host lock, verified-complete recheck after wait, unique partial, atomic no-replace publication; failed/stale/unverified legacy target preserved. No timeout/size cap. Normalgate queued after5a; current writers unchanged.
- Source lifecycle bridge a76cc8633951b8ba7ab292f200d28d0d05c7017e GREEN135; exact fresh verified source identity only, inactive stale probe refresh/normalFG.close/history, active or unknown producer held. Root approval/integration pending at last handoff.
- Durable tree recovery9f20a4ccb07722c867dae28d0b08ffe1d832e8cc GREEN132, committed/pushed HOLDGEN branch; failed links cannot reuse historical full_ok, stale why cleared only on newsuccess. Actual production guard already refreshed normally. Later integration pending.

## Active private work and providers

- Strict five col nativeKITRTL/topology allPASS; commonGEN active ep10 unitoth-ubuntu-113323-1794861457, intel2 client896630, log fable-fix-s81-coltap/gen_five_prepared_f2s3_codex.log. Existing qualified e37 execroot ep10 tools-converge/s81/gen_e37_D2_exec, actual GEN proof gen_e37_probe/proof_exec1.json (executability only). Physical7/8/9/Intel1 when reviewed/admitted; no duplicate constructors or route.
- SVC current canonicalF2s3/D2 functional16/16APPLIED PASS (raw hashes match adopted out_ctx2). New actualF2s3 hi3/lo7 physical both live ep9, preflight0, prior actual reset-geometry review PASS-COND recorded before admission. Docker lo7 create delay resolved normally, no retry. Existing older F2sv pilots separate.
- Signed native_e provider added exact generated key s81p_slice_station__t51_ot_s81_station_t51_native_e -> ep8ne-signoff-r1116/view_hold5_m7; pins0d5391..., actual sourceb3cbd20de41 frozen/main recipe60d74 distinct. Gunit signed ep7provider remains armed, pins9f39..., FWPIPE RT_LAT66/64 stillrequired. No reproof/count rerun or physical hold release.
- Root asked ONLY2 new archive RMIN mappings (native_e r1116_hold5_m7 and HEAD hd_st_n3_turn__nf15_pin_pg_1116) after hourly counts unchanged. Minimum mapping check NOT PERFORMED before reset. Counts62/64,41/394;HEAD5/5,20/26;QC67/67,7/127;KV34/34,6/56 are root supplied, no forced rerun.
- QC private N43 scoped source/selected49 dependencies handed emitter owner. Its derived87fed inventory is NOT a complete publication hash (five later runtime assets separately byte-proven). No finalpublish/adopt. Active sourceN/privatePNR must not be deleted. QC E2 emitter blocked below50GB floor after owner pruned10.93GB own inactive derived variants; prefer actual admitted non-root capacity7/8, no floor override.

## Protection/cleanup

- Genuine token source COMPLETE8ranks36+HEAD,296inventories/384masks per owner. Registered ep7/8/10 tok-verify-2/recovery1116 in stable required coord PROTECTED-DBS.txt plus fresh local.keep; these banks/tables/masks/checkpoint are current source authority, NOT expendable completed scratch. Programme integration remains open.
- Existing guarded cleanup ran normaluser intel2/E2: E2 deleted3.13GB eligible intermediates/finished scratch; Intel2 none initially. Eight permission errors diagnosed. Privileged narrow Intel2 retry deleted ONLY seven paths already eligible under original user-context guards,908353536B, no new paths/finalODB/source removed. Do NOT reuse collector broadly as root: HOME/root changes counted-store lookup. Initial too-narrow-root positive control failed and deletednothing; second normal lane-root controls passed.
- For remaining E2 permission case, corrected only base-directory owner to match its ubuntu-owned kit root, then restarted normaluser ot-autoclean so real signed/count/protected guards remain intact. Result uncollected at reset. Existing cleanup jobs/timers continue; no new launch.
- TEMP ep9 guard remains as above; E2 andintel2 below relevant floors at last observations. No floor override, active tree retirement or source payload deletion.
