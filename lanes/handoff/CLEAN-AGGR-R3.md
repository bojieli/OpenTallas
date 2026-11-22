# CLEAN-AGGR-R3 handoff (2026-11-21 ~22:05 PST)

Lane clone: epyc8 /srv/opentallas-scratch2/claude/clean-aggr-r3/w. Scratch: <scratch2>/claude/clean-aggr-r3/tmp (epyc8, epyc2).

## Pushed to main
- 46d171c4e4 ot-autoclean docker inspect in chunks (epyc7 pass failed on a 300 s inspect since 11-16); ot-delete ROOT-FALLBACK (sudo -n rm --one-file-system, guard-approved canonical scratch tree only).
- eb170c1a34 SETUP_TRIAGE / TT-fail kits keep diagnostics 48 h (autoclean keep_reports); private-spec kits not protected by the kit-wave ancestor; dx test follows the 2 h routed grace.
- d82503914e + 86d1912318 guard list: paths named in enabled die plan + gen_args json are protected; hub ot-run --hosts and ssh <fleet host> paths host-scoped ("@h,intel2 /srv/...").
- 47a226faaa copied child-view signoffs (ft_physical/.cache/rtl/plandir) do not make a kit signed.
- a559ebdd33 ot-tools-sync prune keeps rt named by tools_sha/gen_tools_pin/rt/<hex>, live private specs (<7 d), 48 h of journal launches.
- 249135c503 leases: tools/fleet/ot_lease.py (take/release/list/renew-while); guard keeps live-leased paths; whole-path live-process match (specA vs specA7).

## Found
- Hosts ran an 11-14 ot-autoclean: the localhost ot-autoclean-push timer (:10) pushes its OWN copy. I installed main ot-autoclean.py + ot_delete_guard.py + wt-reaper.py into localhost ~/.local/share/ot-autoclean-auto (backup .bak-clean-aggr-r3) and directly on epyc7/epyc10. Verify after the 22:10 push that epyc8/9/intel1/intel2/epyc2 have DOCKER_INSPECT_CHUNK in the installed copy. Better: make the push run from rt/current (FLOW-OPS).
- s81_head_r4_s0 deleted by ot-retire-superseded (epyc9 03:13Z ... epyc8 03:16Z).
- ot-delete accepts a symlinked lane dir (seamrst2-gate, head-mytile-1115 on epyc2 -> scratch3); rmtree refuses it (FAILED, nothing lost). Guard should SKIP symlinks for dirs too.
- Killed orphaned CLEAN-AGGR-1121 kwbatch.sh on epyc7/9/10 (exact PIDs) before snap_* trees.

## Open
- epyc2 scratch2 410 GB (target 450). Last lever s81-die-r3-e8 (65 GB, also on intel1): 22 unique R-MINIMAL records, 16 exported, 6 spooled on epyc2 (5 gunit_*1117 signoff_rminimal1117 views not in main). R2's drain --scan (intel2 PID 2750745, holds the export lock) will drain the spool. Then verify the 6 shas in intel2 ~/.local/state/ot-delete-guard/exported_records.txt (list in epyc2 clean-aggr-r3/tmp via rmsha.py) and ot-delete on epyc2 + intel1. Guard still refuses it via marker paths d8e/r6/g0, d8dr2/r1, d8f, d8g (S81-DIE-R3 markers in lanes/handoff or state): retire those markers or add the tree to fleet-ops-r/unprotect.txt after export.
- 40%-free target not met on epyc7 (11%), epyc8 (17%), intel2 (16%), epyc10 (28%). epyc7 class a SKIP 449 GB / class c SKIP 424 GB in the last pass: read the reasons in its manifest next.
- ot-run/ot-wait auto-lease not wired (FLOW-OPS).
- base test FLOW-NOADV-R3 post was resolved by fixing test_ot_autoclean_dx in eb170c1a34.
