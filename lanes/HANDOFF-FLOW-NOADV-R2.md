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
