# FAM-S81-SLICE-R4 handoff (Opus 5.5, 11-21 ~07:50 PST) -- ACTIVE
R3=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice-r3 (R4 works here too)  W=epyc10 .../fam-s81-slice (R1 root + clone)
L=epyc8 .../fam-s81-slice-r2   E8=epyc8 .../fam-s81-slice-r3
Local waiters die with this session: a successor must RE-ARM on every unit below.

## Units
- t36 SIGNABLE regen (wave env, J6r1 manifest tree 032305681645, bind ..._d8j6r1_1117_work_bind_11210658): kit_wave run-item,
  systemd user unit fam-s81-slice-r4-t36-runitem on intel2, spec ~/coord/autopilot/private_specs/FAM-S81-SLICE-R4/s81_slice_station__t36_1121074053/
  (run_item.log, result.json). Work epyc10 kw43-wave-1109n/runs/s81/kit-wave/s81/dc92652f0d5/private/FAM-S81-SLICE-R4/slice_station__t36_1121074053.
  After place PASS -> route to sign-off (signoff_chain on the run-item kit), export.
- t36 hand-env route (evidence only, not exportable): epyc10 oth-ubuntu-3910202-1795273859, log $R3/t36_route.log.
  Hold -79 = 2,321 input-port ft*_i bits only (internal 0 at CTS+GRT) -> meets gate. Port seam row (shallower ft landing tap) advisory to S81-J6-ASSEMBLY-R4.
- t37 FSTART rebased on J6r1: $R3/bindtree_r1.sh (mktree_r1 -> tree $R3/trees/src_s81_j6r1_t37fstart, strict bind + LATCHECK), log $R3/bindtree_r1.log.
  Then private-spec s81 slice_station__t37 --tree that tree --plan its plan --bind-out ${tree}_bind, run-item, route to sign-off.
  (Old J6-based tree src_s81_j6_t37reach1 superseded; its bind dir has hardlinked asbuilt from the J6 wave bind.)
- WREG LEC: epyc10 oth-ubuntu-124525-1795274689, out $R3/lec3/{lec.log,equiv_status.txt}. On EQUIVALENT: in $W/clone commit
  tools/s81_slice/xs4_lec.sh follow-up (msg $R3/commitmsg_wreg.txt, trailer), ot-push-main, post define/sha/+1 latency to S81-J6-ASSEMBLY-R4.
- t49 hold ECO pass 2: epyc8 oth-ubuntu-3969870-1795274939, log $E8/t49_eco2.log (base ot-jobs slice_station__t49-route-outgoing-giraffe-4139840).
- t9 WREG hand-env GRT (evidence only): epyc8 oth-ubuntu-949753-1795267285. Next t9 iteration via kit_wave private-spec.
- Lever 6: $R3/lever6.sh (reach_rules check/fix --rules 1 on all slice_station types, J6r1 plan) -> $R3/lever6/. Rows to S81-J6-ASSEMBLY-R4 for J7.
