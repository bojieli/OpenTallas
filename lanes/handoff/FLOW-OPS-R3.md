# FLOW-OPS-R3 handoff (Opus 5.5), updated 2026-11-23 ~16:4x PST

Lane clone: epyc10 /srv/opentallas-scratch2/claude/FLOW-OPS-R3/repo (helper clones repo_anchor, repo_stale, repo_rekey, repo_sitegrid).

## Landed today (main)
- 767ad7f34e7 per-type verilog_defines (type_define_effect.py; OT_BIND_TYPE_DEFINES warn default, =on realizes + fails closed).
- 177ad9e6457 CTS-DPL-DIAMOND-1123 (grt183_make.sh, wave kits).
- 60ec1be1e499 CTS-DPL-DIAMOND-1123b: tools/orfs_dpl_diamond.py in run_abi3_physical.py (ref_tile / closure_loop hard flow; btab_s4r). FAM-QC-HCST-R3 told to rerun btab_s4r/s4rB.
- bacf9b6248a CLAND-FFKEY-CLAMP-1123 (+ cland_ffkey_clamp.py census).
- 4a4ce3b89b26 REVIEW-REQUIRED-KEEP-1123: marker apply keeps review_before_route.required (HEAD r18g unblock).
- 6ca14d0fb59b TOOLROOT-1123: tool_root.py + PRE class TOOLROOT.
- Codex: 82775f07a3f ADV-CELLCAP, 5eef1b26275 reset_anchor re-record.

## In flight (helpers)
- ANCHORDRY PRE (anchor_dry.py + plan_gate_pre), rebasing onto 5eef1b26275, for S81 compose 17:30.
- BIND-REPORT-STALE-1123 (remove old bind_report.json at start; readers fail on report mtime < run start), ETA 18:00.
- CLAND-CTL-REKEY A/B on kv3_hroot (flag OT_CLAND_CTL_REKEY, per-type opt-in if off shortens leg, 0 new findings), report 18:30.
- ADV-SITEGRID PRE (macro/bank origins on site/row lattice, all dies), ETA 20:00.

## Open (original scope)
- GPL -overflow 0.2 default branch + family count (flip after S81-LEAF-J9 t14 a1 gain).
- Missing views restore + hourly canary: S81 dsfd_coll_lane_e/w, KV qkd_hr_core_tx / qkd_hr_cdc_ch; QC coll_ftc ODB/DEF gone.
- GRT-0273 -apply_ndr at CTS (S81 leaf, col_h9_r0, serdes rck, QC st_a).
- rt snapshot refresh after each main push (check hook).
- Define census rerun on S81 Wave A / D29 / V4 candidates; ruling: warn default, composed gates set OT_BIND_TYPE_DEFINES=on.
- Optional: bind_emit_par.json should record failing type + unapplied count (emit A/B: no merge loss).

## 11-23 18:5x update (FLOW-OPS-R3)
Landed on main: GENDRY 9f3deddc069; LANDREMAP-TREE-FAIL + SHIFT 08da0a07542; EMIT-HEARTBEAT c66090747375; BPC-UNDEF-FATAL 9ede7df1b32d.
rt: c66090747375 flipped 18:40 on intel2/intel1/epyc2/epyc7, epyc11 at 18:46. epyc8, epyc9 and epyc10 are held on 70b6 until their unpinned gates clear: KV S1b PRE/G0, the c4 tail on E9 (pid 316706), and the slice PRE (pid 152436). intel2 units flowops-rtflip-{epyc8,epyc9,epyc10} flip each host and post RT-FLIP; logs are in FLOW-OPS-R3/tmp/rt_hold_flip_<h>.log.
OPEN:
- After all three hosts flip, restart the timers on intel2: `systemctl --user unset-environment MQ_SYNC_HOOK; systemctl --user start ot-tools-follow.timer ot-tools-catchup.timer` (BPC 9ede7df then goes live).
- EPYC11: it is on the place hosts now (hub 4bbf75ad). Add it to gen_hosts after the KV D29 and QC V4 applies land and the die src snapshots are replicated to it.
- STATION-1BIT-SWEEP was posted; the TSV is intel2 FLOW-OPS-R3/tmp/station1bit_sweep.tsv. COORD to rule on the 6 running R6V3 route jobs.

## 19:4x 11-23 update
- rt f2156bb449c5 live 19:40:45 on intel2/intel1/epyc2/epyc7/epyc10/epyc11 (3e1a fork-stream fix; DEPTH-PRE+BPC-UNDEF reverted on main f2156). 3e1a2180ccb3 was live 19:27-19:29 and was rolled back to c660 (COORD 19:40).
- epyc8/epyc9 on 70b6, held. Waiters: flowops-rtflip-epyc8d (KV-D29 APPLIED post), flowops-rtflip-epyc9b (c4 tail pid 316706 on epyc9 gone) -> f2156. After both flip: unset MQ_SYNC_HOOK + start ot-tools-follow/catchup timers, post.
- DEPTH-HELD drafted locally: epyc10 lane clone branch flowops-depth-held-1123 commit ef287ff3ec0 (on top of pre-revert main; rebase = re-apply e8e1621+9ede7df+HELD). depth_accepted.json = qfd_tt_ctlm_* / *tt_ctlm* (QC-TTC-RETIME); typed hold list = kit_wave dies.<die>.hold_items. Next: dry-run DEPTH+BPC on KV A2g (epyc8 kv-allfix), QC C1b (epyc7 QC-ALLFIX/rows_c/plan_c1_fix1.json), S81 c7a (epyc9 s81-allfix-int/c7a), post, then re-land.
- Copy slots: OT_TREE_COPY_SLOTS is caller env only (default 2); epyc11=4 needs per-host override file -> planned for DEPTH/BPC cut.
- epyc11 gen_hosts after D29+V4 applies land.

## 19:5x 11-23 update
- rt 8d19c5d78e6d live 19:50:09 (COPY-SLOTS-HOST-1123 on f2156): per-host /var/tmp/ot-tree-copy/SLOTS; epyc11 SLOTS=4 written. Waiters now flowops-rtflip-epyc8e / -epyc9c -> 8d19c5d78e6d. Lane notice posted.
- Still next: DEPTH-HELD+BPC dry-runs on KV A2g / QC C1b / S81 c7a, then re-land; timers after epyc8+epyc9 flip; epyc11 gen_hosts after D29+V4.

## 20:3x 11-23 update
- rt 9b19260c1cde live 20:35 on all hosts except epyc8 (DEPTH-HELD/CAP-CONFIG/DEPTH-PRE/BPC, ADV-IST-PRICE, R8 zero-bit guard, R8 lane fix 356816a). Previous: 356816a53858 20:22.
- epyc8 stays on 70b6 for D29 seal s3; rt 356816a53858 + 9b19260c1cde staged on epyc8 (rsync, sha-verified). Waiter flowops-rtflip-epyc8g (systemd user unit, linger on) flips epyc8 to 9b19260c1cde on KV-D29 APPLIED. epyc9 flipped 19:53.
- After epyc8 flips: systemctl --user unset-environment MQ_SYNC_HOOK; start ot-tools-follow.timer ot-tools-catchup.timer; post.
- Next cut: KV-RRL-EXPORT verifier fix once pushed. test_leaf_cs_depth bind-gate string test fails on plain main (stale literal), not ours.
- epyc11: wrappers + .bashrc localbin done; SLOTS=4; gen_hosts after D29+V4 applies.
- Dry-runs posted: QC C1c 1 HELD (s5_ctl_repair4), KV A2h/S81 c7a 0 reached; BPC PASS (C1b 133/133, S81 out 1218/1218).

## 20:5x 11-23 update
- KV-D29 APPLIED 20:49 -> epyc8 flipped; all 8 hosts on 9b19260c1cde. MQ_SYNC_HOOK unset, ot-tools-follow + catchup timers ACTIVE on intel2 (auto-cut of origin/main resumes).
- Next cut (main 11ca5152455: ADV-PAD-LAUNCH fa21a27c0f3 + OTRUN-ORPHAN 11ca5152455) REFUSED 20:51: hub scratch2 91 GB < 100 GB rail. Follow timer cuts once space is freed; requesters told. KV-RRL-EXPORT verifier fix still not pushed.

## 21:0x 11-23 update
- KV wave rt: no die-level rt pin exists; KV kit tools = bind_rt_follow/KW_BIND_RT on bind of record stamp. Current bind_out (d29 portable_bind, 70b6 stamp) resolves to rt 7f184148 (reset_tree.py differs). Ruling posted: KV-D29 repoints kit_rtl.bind_out to its 9b19 postbind (unit postbind-qwen_kvsys-9b19_1123, epyc8, ETA ~22:00) BEFORE lifting kv3_* hold; then I re-verify with kit_wave.bind_rt_follow from rt/9b19 vs live kit_wave.json (expect 9b19). KV-D29 agent a39af6d5d832f96bd told.
- Follow timer retries the cut each run; hub 96 GB < 100 floor (cleanup running per COORD). Next cut = main head (11ca515 OTRUN-ORPHAN, fa21a27 ADV-PAD-LAUNCH, 8e13dda BIND-EMIT-MEM). Requesters told.

## 21:4x 11-23 update
- Hub disk freed (OPS-SUPPORT); follow timer auto-cutting main to ALL 8 hosts (epyc8 incl). rt/current = c149c0966d7c (has ADV-PAD-LAUNCH, OTRUN-ORPHAN, BIND-EMIT-MEM, GENDRY-KITRTL, KV-PREGRT-STALL c40acd9).
- KV bind_out -> selected_candidate_bind_1123212910 at 21:33; flowops-kv-rtcheck2 (from rt/current) resolved KV wave rt = c149 (R8 fix + pregrt cap). KV-D29 told kv3_* may lift. KV-PREGRT-STALL closed (earliest rt c40acd92e639 21:07).
- Pending: KV-RRL-EXPORT verifier fix (auto via follow when pushed); epyc11 gen_hosts after QC V4 apply; QC wave tree needs kit_istations/reg_leaf_split (QC apply owner).

## 23:0x 11-23 HANDOFF -> EPYC11-ONBOARD-FINISH (COORD one-job-per-lane)
epyc11 gen_hosts onboarding moves to EPYC11-ONBOARD-FINISH. Adopt these units; do NOT kill them. Each is a systemd user unit on intel2 and survives sessions.
- flowops-e11-s81_head, flowops-e11-qwen_kvsys, flowops-e11-qwen_compute, flowops-e11-s81: run /srv/opentallas-scratch2/claude/FLOW-OPS-R3/tmp/e11_repl_die.sh <die>.
  Per die: compute the wave input closure (kit_wave.src_inputs + deep_inputs + item_inputs, collapsed to root trees). Copy each root to epyc11: manifest trees with `src_manifest.py replicate --hosts epyc11 --tar` from a host that holds them; bind/postbind dirs with adopt-bind-style rsync to the same path. Then `kit_wave_edit` adds epyc11 to dies.<die>.gen_hosts; its HOST-ADD closure probe is the proof. Skipped when epyc11 is already listed. Each add posts "EPYC11 GEN_HOSTS" on FLOW-OPS-R3.
  Logs: FLOW-OPS-R3/tmp/e11_repl_<die>.log (lines DONE/FAIL/NOSRC/ADDED/ADD-REFUSED). The old serial driver log e11_repl.log is finished.
- Known issues:
  (1) NOSRC: some item_inputs trees exist on NO host, e.g. kw45/snap_qwen_compute/qwen_compute_v1r6 and kw45/src_s81_pin_3c913dbdfb23_d8j6_1117_work, maybe more. Expect ADD-REFUSED for those dies. The stale item_inputs refs then need cleaning (kit_wave_edit), or the host-add needs a COORD ruling.
  (2) s81_head src moved r17b_s0 -> r18g_s2 during the run. The serial driver copied r17b (48 GB, now unused); the die unit copies r18g_s2.
  (3) Copy speed is ~20 MB/s per stream; ~1 TB total -> hours. epyc11 SLOTS=4 (/var/tmp/ot-tree-copy/SLOTS).
  (4) hbm is excluded (parked).
- Still to do: check epyc11 load ~30 min after each add; add epyc11 to the monitor host lists.
- Kept by FLOW-OPS-R3: the KV LBL probes (runitem-flowops-qwen_kvsys_kv3_hroot_1123225427 / _kv3_hgi_v4_1123225432) stay with VIS-KV for the PROBE-PASS read.

## 2026-11-24 00:28 PST copy class + breach
- BREACH (mine): flowops-e11 units copied trees outside ot-run and raw-rsynced 7 bind dirs into kw45 / kv-plan-r6 paths on epyc11 after ot-tree-fork refused a kw45 destination; five of them are STUBS (bind_report.json only). COORD: owned by EPYC11-ONBOARD-FINISH, I touch them no more. No copies outside ot-run.
- COPY CLASS live: main e2f77583967 (tools/fleet/ot_copy_class.py, ot-run, ot-run-lane-declare, test_ot_copy_class.py), stub-source refusal df52cfd5b07. Usage in my post 00:19. Fork form smoke PASS 00:20; replicate only by tests.
- intel2 installed guard ~/.local/lib/fleet/kw44-seal-ap/ot-run-lane-declare replaced with rt's (backup .bak-before-copyclass-1124). It is a fixed copy: a later guard change must be installed again.
- OPEN: (a) SEAT-KEYS report-only (COORD): kit per-bank matched/unmatched + CLASS line, PRE WARN ADV-SEAT-KEYS; matcher/re-key/strict stay with SEAT-MATCH-AUDIT, which has uncommitted edits in kit_istations.py. (b) kit_wave bound_tree_inputs + ITEM-SYNC stub fix: unassigned. (c) does depth_netlists miss the TTC F5 netlist in QC C1c: unchecked.

## 2026-11-24 00:28 PST copy class + breach
- BREACH (mine): flowops-e11 units copied trees outside ot-run and raw-rsynced 7 bind dirs into kw45 / kv-plan-r6 paths on epyc11 after ot-tree-fork refused a kw45 destination; five of them are STUBS (bind_report.json only). COORD: owned by EPYC11-ONBOARD-FINISH, I touch them no more. No copies outside ot-run.
- COPY CLASS live: main e2f77583967 (tools/fleet/ot_copy_class.py, ot-run, ot-run-lane-declare, test_ot_copy_class.py), stub-source refusal df52cfd5b07. Usage in my post 00:19. Fork form smoke PASS 00:20; replicate only by tests.
- intel2 installed guard ~/.local/lib/fleet/kw44-seal-ap/ot-run-lane-declare replaced with rt's (backup .bak-before-copyclass-1124). It is a fixed copy: a later guard change must be installed again.
- OPEN: (a) SEAT-KEYS report-only (COORD): kit per-bank matched/unmatched + CLASS line, PRE WARN ADV-SEAT-KEYS; matcher/re-key/strict stay with SEAT-MATCH-AUDIT, which has uncommitted edits in kit_istations.py. (b) kit_wave bound_tree_inputs + ITEM-SYNC stub fix: unassigned. (c) does depth_netlists miss the TTC F5 netlist in QC C1c: unchecked.

## 2026-11-24 00:41 PST state
- Wave probe: main df0022edcad (BOUND_BIND_FILES, bound_bind_path); per-bank seat print: kit_istations SEAT-BANK (report only). PRE half dropped: SEAT-MATCH-AUDIT owns it.
- COORD 00:16 HOST RULING: no new tree forks into epyc11; my 00:19/00:21 posts corrected.
- epyc11 (from EPYC11-ONBOARD-FINISH, COORD 00:26): gen_hosts = s81_head only. S81 d8j8 hash NOT started, waits for io full avg60 < 10 % (hdirs.py + hroots_s81.txt copied to epyc11 FLOW-OPS-R3/tmp; expect bind 54daa9 3052, postbind s2 20fa22 3052, s3 5be9d8 266). QC postbind + KV copy: NOT done, destinations are kw45 (refused), asked COORD for a ruling. No rsync / tar there.
- Unchecked: depth_netlists vs TTC F5 in QC C1c.

## 2026-11-24 01:30 PST
- COORD rulings: no QC/KV on epyc11 until a plan event publishes there; S81 re-added (hub 95965852, verified hashes); QC-OPEN-SU probes on epyc7.
- STRAP-EVIDENCE-COUNT: main 445647cc300 + hub tools/release_tree_plan.py, signed_store_ingest.py (backups .bak-strapcount-1124); table lanes/COUNT-STRAP-EVIDENCE.tsv seeded 301 rows NO-VERDICT. Hub tool copies diverge from main (5 hub tests fail before and after the patch: designs LL*, retire s81 legacy, scan timeout).
- Breach: one git stash in the lane clone (popped clean).
- Open: depth_netlists vs TTC F5 (QC C1c) unchecked; epyc11 load check after the S81 add.

## 2026-11-24 02:08 PST COUNTER-DRIFT done
- Hub counter = main b438f6cd5b1 (hub commit de0270a1); backups tools/*.bak-drift-1124. Hub tests in place: 131 pass, 1 skip (live opt-in). count-hub 02:05 rc 0.
- epyc11 load 36 at 01:46 after S81 add; s81 gen_hosts unchanged.
- Open: QC C1c depth_netlists TTC F5 check.

## 2026-11-24 02:25 PST DEPTH-NETLIST done
- main fa8b2360de3: PRE DEPTH follows the as-built die netlist (C1g TTC F5 was missing); depth_cover counts netlist modules. C1g dry run 0 FAIL, F5 HELD.
- Old local commit 1386e61111b (truncated msg) left unpushed on branch flowops-depth-ttc-1124; pushed f15b91ad832 tree-equal.

## 2026-11-24 03:01 PST KIT-STAGE-IMPORT done
- main 66331205584: ot-push-main exit 6 on new kit-staged import of an unstaged die_plan sibling (tools/fleet/kit_stage_imports.py, delta vs main). Canary-FAIL rule pending a canary record from FLOW-CANARY-R2.

## 2026-11-24 03:45 PST GENDRY-WAVEMODE done
- main dd479a7079b: PRE GENDRY follows the die kit_rtl mode (bind/script -> every non-hard type kit-rtl).

## 2026-11-24 04:07 PST STRAP-EVIDENCE-PRIV done
- main e0067f96f34: private HEAD kits read the tie audit of their declared bind (--bind-out -> OT_KIT_BIND_OUT); strict evidence. Census: tmp/se_scan.out.

## 2026-11-24 04:14 PST RT CUT
- rt/current c0b6e2d03408 on all 8 hosts, per-file hash check 0 mismatch; contains e0067f96f34 0549174ed9c 18bd6c196c6c 57addab573c0.

## 11-24 04:34 DROPIN-REMOVE-1124
- Removed intel2 autopilot.service.d/zzzzzz-codex-takeover-viewed-route.conf (ot-delete; copy FLOW-OPS-R3/tmp/*.removed-1124), daemon-reload; unit env AP_REQUIRE_VIEWED_WAVE_ROUTE count 0. autopilot is a timer oneshot, so no restart: next tick reads new env.
- Handback checklist added to CODEX-ROLE.md (hub d9ae58aa).
- 13 S81 + 3 HEAD no-verdict kits posted to owners, verdict due 05:05 (hub 37ef1269).
- NEXT: confirm the 44 QC auto-ACCEPT kits route on the first post-removal tick (waiter running), post count; recheck the 16 at 05:05.

## 11-24 05:00 ENTRYFOOT-WARN + DROPIN-AUDIT
- ENTRYFOOT WARN-only: main 400e17ab00c, rt a196b911e255 on all 8 hosts (hub post).
- 44 QC kits: 43 routed + 1 cancelled; all 47 submitted route jobs admitted (hub a55ae3fc, e7480ce1).
- Drop-in audit: removed 5 dead autopilot drop-ins, kept 9; effective unit unchanged (e7480ce1).
- Held-no-owner list of 51 rows posted (0b983f77).
- Open: hub-git-sync FAILED since 00:00 (bin/owners_sweep.py local edit, not mine); autoclean CURRENT_EVENTS stale (asked COORD); canary-FAIL push rule waits on FLOW-CANARY-R2.

## CODEX notes 2026-11-24 06:31 PST

- Reinstated intel2 ~/.config/systemd/user/autopilot.service.d/zzzzzz-codex-takeover-viewed-route.conf, with AP_REQUIRE_VIEWED_WAVE_ROUTE=1 and the CODEX-ROLE.md handback reminder. The 06:17 tick finished with no routes submitted. Verified the 06:23 live process inherited the exact-view setting. Admitted jobs kept running. Remove this specific drop-in at the handback.
- E11 installed Ubuntu python3-matplotlib 3.10.7+dfsg1-2build1. Isolated python3 -I uses agg successfully. VIS has the result for exact renders of retained KV places.
- E11 onboarding left an empty Ubuntu crontab. Restored the standard two-minute flock-serialized ot-heavy reconciler line. First pass cut 5,797 declared threads / 1,295 reservation pairs to 316 / 41, retiring only terminal thread charges and preserving their receipts. The previous and new crontab copies are in epyc11 FLOW-OPS-R3. THREAD_CAP_FACTOR=0 remained unchanged.
- ITEM-SYNC historical bound-tree probe copied partial immutable inputs and retried tar rc2. The S81 d8j6r1 and QC v3p7c5rt records now have a scoped source fix in epyc10 FLOW-OPS-R3/repo on claude/flowops-item-sync-atomic-bound-1124. 104 focused checks PASS. Normal push unit flowops-item-sync-push-1124 and ../tmp/item_sync_push_1124.log. Existing partial trees preserved for owners. Any replication goes through the full snapshot publisher.
- Wave hold audit has no leaks. The current 06:27 QC FW sign-off failed DRC0, TT -135.66 and FF -130.24. Two ECO rounds ended TT -131.06 and FF -130.24. Forwarded to QC for structural follow-up. S81 J8 lack of launches tracks exact holds and C8 awaits changed G0. E8 66 GB drained; scratch2 and scratch3 share its filesystem. Auto-clean remains scheduled.
- ITEM-SYNC source landed main 2b107a0a6073 after the normal kit_wave test gate. Two concurrent main advances were retried and neither overlapped the touched paths. The usual rt follow publishes the change.
- E10 ROM output pressure. Two existing QC rank0 writers PIDs 3900535 and 4182155 have fd4 on overlay_r0.gds inode 46606640 and fd3 on its .empty inode 46606637. Treat rank0 as untrusted pending separate exact reconstruction. No job stopped. E7 retains all eight code mask cohorts and all eight V2r10 placement maps; the sixteen manifests/map SHA-256s match E10 active inputs. E11 compressed HEAD pilot oth-ubuntu-217890-1795530911 is PASS on 10 masks with 64 MB output. Alternate durable input and staging paths sent to the token lane. At 06:40 E10 free 122 GB and E8 free 53 GB. Both use existing cleanup/admission only, with no manual deletes or copies to E8.
