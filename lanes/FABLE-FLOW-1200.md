# FABLE-FLOW-1200: procedural / flow review, window 11-20 09:50 to 11:48 PST

Lane FABLE-FLOW-1200 (Fable 5.2). Read-only review, flow only. Previous: lanes/FABLE-FLOW-1000.md.
Sources: autopilot/log.txt, lanes/FLOW-HEALTH.tsv (11:08), ot-run --status 11:47, ot-heavy-reconcile --free (epyc2, intel1),
lanes/CANCEL-UNSIGNABLE-1120.tsv, ~/.local/state/noprog/hub_seen.json, kit run logs on epyc2 / intel1, kit_wave.json,
rt/current 123dc80f7964, lane posts.

## Headline

1. The unsignable watchdog's first act pass (11:30 to 11:42, 16 cancels) was NOT all correct. It reads only the post-CTS
   number (4_1_cts.json). At least one cancelled job was inside the sign-off gate in GRT repair, and two more were above
   the -300 ps line at their latest measurement. The next pass has 3 more jobs listed. Set NOPROG_UNSIGNABLE_MODE=report
   until the watchdog reads the newest setup number of the job.
2. 3 of the 16 cancelled jobs were resubmitted by the autopilot within 15 min as "infra-oom" and resume the same run
   dir. The watchdog cannot catch them again: it needs a 4_1_cts.json newer than the container start, and a resumed run
   keeps the old file (read from code).
3. The launch drop (456/h to 27/h) is not a stall and not a gate. Hour 09 was a one-off release (224 FLOW-REGEN,
   162 RELAUNCH-ON-FIX after the 405 env fix, 180 QC A4 launches). Since 10:00 every die has 0 to 13 eligible rows per
   tick; the fleet is 100 percent of threads used, 178 waiters ask about 6,900 GB.
4. FLOW-NOADV-0915 has still posted nothing and has no commit on main. None of its three items is visible as landed.
5. Host OOM kills went from 0 (08:00 to 11:00) to about 12 between 11:07 and 11:45; epyc8/9/10 are at 51 to 63 GB
   available.

## Watchdog cancels, checked one by one

Rule: over 3 h and measured unable to sign (setup under -300 ps). All 16 were over 3 h and had their own post-CTS setup
under -300 ps. No job named as a proof and no KEEP line was cancelled (pkw2b, pkw4 kept). Containers: none of the 16
exists any more (docker ps -a on epyc2, intel1, intel2 at 11:46).

| job | host | post-CTS setup | latest setup read in the GRT log | verdict |
|---|---|---|---|---|
| slw_st_b_v1__cle6023ec2 (QC N46C, attempt 3, 13.0 h) | intel1 | -405 | repair passes -52.6, -41.8, -7.1, last -0.494 ps (95 ends) | WRONG: inside the -42 gate when stopped |
| dsdv_slice_lepw_mus_LP__t2 (13.5 h) | epyc2 | -844 | -216.6 ps at iteration 1180, 222 ends | WRONG by the rule: above -300 |
| type-kvhgi2/v1/b/kit (private, 137 h) | intel1 | -651 | -281.4 ps, in the hold repair pass (2,984 hold ends) | above -300 and in hold repair; not covered by the rule |
| type-kvhgi2/v1/c/kit (private, 137 h) | intel1 | -569 | -311.7 ps, flat over 10 iterations | correct |
| cbn_q00__cldbcda913 (13.8 h) | intel1 | -1107 | -925.5 ps | correct (but resubmitted, see below) |
| kv3_hub_Eo (KV-D25d, 13.2 h) | intel1 | -511 | CTS ended 09:57, no GRT yet | correct by the rule |
| dsdv_slice_lepw_mu_LP__t2, ot_s81sl_leaf__t2, __t54, __t25, col_h9_r0_p5__t1, cbn_q01__cldd6ea846 | epyc2, intel1 | -1735, -510, -634, -495, -384, -1357 | GRT log has no repair table yet | post-CTS evidence only |
| ot_s81sl_kv_leaf__t5, ot_s81sl_leaf__t10, __t58, hd_lep0N (r8b private kit) | intel2 | -1302, -871, -349, -538 | not read (kit run dir not found at the recorded path) | post-CTS evidence only |

Other defects of the pass:
- Resubmitted after the cancel: s81/dsdv_slice_lepw_mu_LP__t2 (11:41, epyc2), qwen_compute/cbn_q00__cldbcda913 (11:42,
  intel1), s81/ot_s81sl_kv_leaf__t5 (11:44, epyc8). The classifier saw "Killed" and chose infra-oom. The other 13 were
  classed "infra-stopped" and recorded as CRASH in structural.tsv, which is also the wrong label.
- Every evidence row records "epyc10: ot-heavy-stop: 0 scope(s) stopped" as the cancel result, whatever the host. It is
  the last output line, not the line of the job's host.
- The watchdog writes lanes/NOPROG-ACTIONS.tsv in the hub checkout without coord-commit: ALERT HUB-SYNC-FAILED since
  11:32.

Cost of the class: the 16 jobs held 301 GB charged and 3.4 percent of running slots; 445 job-hours had run (274 of them
in the two 137 h kits). The wrong cancels lost 13 h and 13.5 h of GRT repair on two types.

## Classes

Fleet 11:47: epyc7 admits 208 GB, every other host 0. Available memory: epyc2 205, intel1 227, epyc8 63, epyc9 51,
epyc10 58 GB. Load per core 1.2 to 3.1. 178 waiters. FAIL lines per hour: 118 (08), 84 (09), 39 (10), 10 (11 to 11:44).

| # | class | count, trend | process root cause | structural fix | owner | fleet time |
|---|---|---|---|---|---|---|
| 1 | Unsignable cancel on a stale number | 16 cancels; 1 wrong, 2 above -300, 2 confirmed, 11 post-CTS only | measured_setup() reads only 4_1_cts.json; GRT repair moved one job from -405 to -0.5 ps | read the newest setup the job wrote (last WNS row of the GRT repair table, else 4_1_cts.json); never act while the job is in a hold repair pass; report mode until landed | FLEET-WATCH-1015 | 26.5 h of repair lost; resume slw_st_b_v1__cle6023ec2 and dsdv_slice_lepw_mus_LP__t2 from their run dirs |
| 2 | Cancelled job resubmitted | 3 of 16 | the cancel leaves no record the classifier reads; exit by kill looks like OOM; resumed runs are "unmeasured" to the watchdog | the watchdog writes a cancel marker in the run dir and the wave row; classifier maps it to a terminal UNSIGNABLE class (no retry on this plan block); measured_setup accepts the file of a resumed run | FLEET-WATCH-1015 | 3 slots, about 70 GB, open-ended |
| 3 | Host OOM kills | 0 per hour until 11:00; about 12 from 11:07 to 11:45 (epyc2 4, epyc10 4, epyc9 2, others 2) | three hosts at 51 to 63 GB available with 60 to 70 jobs each. Coincides with stage-peak charging for private kits (320709d617, 10:06) and with the receipt gate moving retries to fewer hosts. Cause not proven | owner condition for stage-peak admission was "OOM kills about 0": compare kills per host before and after 10:06 and return private kits to the requested charge on hosts that kill; the rail stays | FLEET-WATCH-1015 | each kill loses one place or GRT stage; under 1 percent, rising |
| 4 | Host receipt gate | from 11:09: 8 HOST-RECEIPT-MISS (intel1 4, epyc2 2, epyc9 2), 7 LAUNCH-DEFER on 4 types, on the live S81 d8i work tree and the KV d25e3 tree | cached-receipt refuses a file with nlink 2 that is not shared with the declared link base; "own verification started" repeats every tick on the same host and never ends in a receipt. launch_safe went from 38 s to 316 s and the tick from 315 s to 716 s | on a miss, the host re-publishes the file as its own inode (or the verify run writes the receipt it just proved); one receipt check per host and tree per tick, cached | FLEET-WATCH-1015 | 4 types not launched for 40 min; the tick cadence halved for every die |
| 5 | Reset identity refused at gen | 67 in hour 09, last at 09:37, 0 in two full result hours | as 10:00: a default change against live 405 binds; held off by die_gen_env | cap and reach read from the bound plan: NOT landed, no post, no commit | FLOW-NOADV-0915 (silent since 09:15: needs a successor) | 0 now |
| 6 | Fallback trees without reset keys | still 8 trees with no keys (KV 3, S81 2, QC 3); QC die env is now 300 for A4 | unchanged | unchanged | FLOW-NOADV-0915 successor | 0 seen |
| 7 | Retry on an unfixed cause | REPEAT lines 93 (09), 10 (10), 12 (11); REPEAT-STOP 34, 7, 1 | rt/current full_input_hash no longer holds the rt sha (comment FLOW-0245; I could not date the change; the log text still names it). FAIL-STALE re-arms 1 to 3 keys every tick. 9 types still failed the same text 2 to 4 times after 10:00 (kv3_hg_v3 4x, sle_su_l0 3x, slw_st_a_v2 3x) | class label out of the key is unverified; launch replicas of a type only after its first attempt passes the stage the class failed | FLOW-NOADV-0915 successor | about 1 percent |
| 8 | ssh loss classed as design | 6 UNCLASSIFIED at 10:31 to 10:39 (timeout or close on one host, roam pull-back), 4 NEEDS-LANE posts | ssh errors have no class | class as INFRA with a free retry on another host | FLOW-NOADV-0915 successor | small |
| 9 | Die tree missing at geom_run | 2 S81 FAILs (11:17, 11:28): d8i work tree missing on one host | same host-tree coverage gap as class 4 | geom host chosen by the same receipt as gen | FLEET-WATCH-1015 | small |
| 10 | Rows held, not flow | 57 to 67 rows: WAIT-FORM 26, q_running 17, WAIT-VISUAL 6 to 16 (rising), KW-FIX-45 8; 147 superseded-event rows | visual verdicts arrive slower than placements | reviewer capacity; not a flow fix | GEOM lanes | 16 rows wait at route |
| 11 | Disk, source skew, stale | no disk refusals; SRC-INCOMPLETE 5 in hour 09, 0 since 10:00; auto-clean ALERT epyc10 (100 min) and epyc7 (92 min) without a completed pass; TOOL-SKEW warn S81 413 and QC 485 modules off the pin, KV and HEAD unmeasured (pin manifest missing on the hub); HBM plan unreadable alert 12 per hour (parked) | standing | answer the two auto-clean alerts; publish the two pin manifests | FLEET-WATCH-1015 | 0 |

The 5 class breakers opened since 09:57 (KV gen_lint missing module, KV kit_topology packed banks, QC packed bank
overlap, QC station knee over 403 um, QC su_l0 clock contract) are design or plan classes with die owners; they are 35
of the 49 FAIL lines since 10:00.

## Do now (ordered)

1. FLEET-WATCH-1015: NOPROG_UNSIGNABLE_MODE=report now (3 jobs listed for the next pass: cbx_q10__cl94a12200_h,
   col_h9_r0_p4__t1__cl8ef405e8, ot_s81sl_leaf__t47). Resume the two wrong cancels. Decide the 3 resubmitted jobs.
2. FLEET-WATCH-1015: newest-setup read, cancel marker, receipt convergence, OOM count against the stage-peak change.
3. COORD: FLOW-NOADV-0915 is silent for 2.5 h; start a successor with classes 5 to 8.

Not checked: failure_breakdown (no output file found on the hub, not run); GRT numbers of the 4 intel2 cancels; why
intel1 admits 0 with about 120 GB under its limit; whether the class label is still in the repeat key.
