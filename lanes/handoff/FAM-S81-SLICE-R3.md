# FAM-S81-SLICE-R3 handoff (Opus 5.5, 11-21 ~05:50 PST) -- ACTIVE
W=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice (R1 root, clone $W/clone branch claude/fam-s81-slice-wreg-1121)
L=epyc8 /srv/opentallas-scratch2/claude/fam-s81-slice-r2 (R2 root)   R3=epyc8 /srv/opentallas-scratch2/claude/fam-s81-slice-r3
Local waiters die with this session: a successor must RE-ARM on every unit below.

## Units
- WREG default-off LEC: epyc8 client PID 1126734, out $L/lec_off2/{lec.log,equiv_status.txt}. On EQUIVALENT: in $W/clone commit
  tools/s81_slice/xs4_lec.sh (already staged, untracked) as follow-up with full message + trailer, ot-push-main, then post the
  define, sha and +1 latency to S81-J6-ASSEMBLY-R3.
- t37 strict gate: epyc8 PID 1087032 / oth-ubuntu-1088408, log $L/t37_gate.log. When green: ot-run $R3/t37_kit.sh (exact wave env
  $R3/wave_env_slice_station__t37.json + wave gen args), diff config.mk vs wave attempt_13
  (epyc8 kw43-wave-1109n/.../b05c98f7919/items/slice_station__t37/attempt_13/gen/slice_station__t37/config.mk), then
  signoff_chain.py run_kit.sh KIT route.
- t9 WREG GRT: epyc8 PID 948431 / oth-ubuntu-949753 (hand-env proof; t9 is 486k, over the cap, so read it as WREG evidence only).
- t36 GRT: epyc10 oth-ubuntu-344587-1795255611, kit $W/t36_c1n/gen/slice_station__t36, GOAL grt. After DONE: ot-run
  signoff_chain.py (rt/current) $W/t36_c1n/gen/run_kit.sh KIT route 56 16 (auto-resume from GRT).
- census: DONE, posted 11-21 05:4x (body xgt_xo 172,629 generic cells on every type; strip 83k to 118k).

## Notes
- The missing OT_GPL_SPARSE_OVERFLOW=0.25 on t36/t9 is the CURRENT gen rule (FLOW-NOADV-R3: sparse exit is ot_s81sl_leaf only), not a gap.
