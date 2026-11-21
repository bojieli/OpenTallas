# HANDOFF FLOW-NOADV-R2 (11-20 13:45 PST)

Landed on main (each pushed separately): 9172a65b43 bound reset cap (receipt reach_cap_um, install_bound_native_reset under cbc_rules.bound_reset_hop_cap, test_bound_reset_cap.py);
00eec2a423 class label out of fail_key / fail sig / infra_key / REPEAT-STOP streak; eae5825732 ring fan + KV START corridor read the cap at call time, gen scopes each type to its receipt cap.
Config (kit_wave_edit): df3425a5c8 405 keys on 8 fallback trees; 5fd0144c29 kvsys canary drop; 81f6a90048 drops on s81 + qwen_compute (s81 and kvsys keep OT_CBC_REACH_UM=405).
Canary kvsys 12:38-13:40: 6 launches, 0 reset-identity refusals. Revert path: kit_wave_edit --set /dies/<die>/die_gen_env/OT_RESET_HOP_CAP_UM='"405"'.

OPEN 1: S81 ot_s81sl_leaf__t2 / __t10 collector_tree refusal (only 2 types since 12:30, both 12:42, gen on epyc9, rt 6a81626d915b).
 Captured 643 relays, solved 662, reach 180 both, tap 61 vs 62. Not the cap. 38cdd37cec9d (tap_resolve) is NOT on the gen path (plan-time only); plan_h2_2249.json predates the bind (09:30 UTC vs 12:01 UTC).
 Bisect queued: /srv/opentallas-scratch2/claude/flow-noadv-r2-w/rep_r2.py on epyc9 via ot-run (waits for memory admission), output scratchpad rep.out.
 Rerun by hand: ot-run --mem 24 --hosts <epyc9|intel1|epyc2|epyc8|epyc10> --dir <dir with rep_r2.py> --stage <rt dir> -- python3 -I rep_r2.py <rt dir>, for rt 219c38c9c285 (before) and 38cdd37cec9d (after). The bind is on epyc9/intel1/epyc2/epyc8/epyc10, not epyc7.
 If only the later rt differs: find the commit by bisecting rt dirs between them (list on epyc9 /srv/opentallas-scratch2/claude/rt), then gate the new behaviour to new binds via a receipt marker.
OPEN 2: drop s81/kvsys OT_CBC_REACH_UM=405 only after confirming no consumer outside reset needs it.
Notes: test_flow2045 failures were sparse-checkout artefacts. Clone: /srv/opentallas-scratch2/claude/flow-noadv-r2 (intel2, cone tools rtl physical/common_flow physical/die_plan). Push gate takes ~35 min (run ot-push-main with nohup).

## Update 14:xx
- REPEAT-STOP now holds an unchanged relaunch after 3 identical fails also under stops_off (main 6ea719be97): LAUNCH-HELD, explicit retry key overrides, auto-release on changed plan block / src sha / failing-stage files / runtime tools_sha, or an unblock line. Same-fail-key refusal stays log-only. Gap: a fix that only adds a file the failing stage never named (e.g. signoff.json in the QC lane views) does not release by itself; new tree/plan or unblock does.
- CLASS plan contract metadata missing (qwen_compute su_l0/su_l1, 22 fails): plan taps say SIGNED but views qcviews_1111/views/qfd_qc_su_lane_w_l0..l7 have no signoff.json; source records gone. Handed to DIE-QC-103 (export signoff.json or move taps to parent_budget).
- t10 rerun (OPEN 1): STILL QUEUED on epyc9 (ot-run waits, fleet admits 0 GB); no result yet. Output file scratchpad rep.out (/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/rep.out). If the process is gone, rerun with the command above on epyc2/intel1/epyc8/epyc10 (bind dir exists there too).

## Update 16:20 (context over 370k: successor takes the t10 verdict)
Landed on main since last update: ec16babe0d cross-row station site overlap check (kit_istations.cross_row_site_overlaps at gen + station_rows_check OVERLAP) and tools/failure_breakdown.py wrapper; d98908b665 GPL sparse-overflow / GPL-overflow exact die name s81 (HEAD kits were getting the S81 strip rule; test_gpl_die_scope.py). 6ea719be97 REPEAT-STOP holds under stops_off.
Coord repo: failure_breakdown.py is read-only by default; --write-release-tree splices RELEASE_TREE.md and commits via coord-commit.sh (04511974c2, test_failure_breakdown_write.py). Anything that relied on the old auto-write must pass the flag.
sd9g3 answer posted (it has -allow_congestion via OT_GRT_ALLOW_CONGESTION=1; no hd_serdes item_env sets it now; their decision).
t10 VERDICT STILL OPEN (does 38cdd37cec9d cause the t2/t10 collector tap shift?). Epyc9 waiters cancelled. Running on epyc7 (die priority) from W=/srv/opentallas-scratch2/claude/flow-noadv-r2-w: receipt in/receipt.json (643 relays, 81 taps, reach 180), plan + cores/inputs/plan_inputs copied to in2/physical/die_plan/s81/ (copy was still running at 16:20; check du of in2 ~ 900 MB), script rep7b.py (builds Plan with path= so core pin tables resolve), tools: rt219/ (a copy of rt 219c38c9c285 die_plan, BEFORE 38cdd) and /srv/opentallas-scratch2/claude/rt/38cdd37cec9d (AFTER).
Run: ssh epyc7; cd W; ot-run --priority die --mem 24 --threads 2 --hosts epyc7 --dir W --stage <rt> -- python3 -I rep7b.py <rt>   for rt219 and 38cdd.
Read: if solved relays == 643 for rt219 and 662 for 38cdd => 38cdd37cec9d changes the gen solve: gate its new assignment to new binds (receipt marker) or revert, with a test. If both give 662 (or both 643) it is something else: bisect rts on epyc9 /srv/opentallas-scratch2/claude/rt (list by mtime). Note tap_resolve is only plan-time by call graph, so expect another cause (e.g. a plan-time tap list carried in the bound plan differing from the gen solve).
