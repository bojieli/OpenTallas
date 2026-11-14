# PROFILE-1 handoff (R-MINIMAL sign-off profile; COORD is the coordinator) -- 2026-11-13

## Code
- Branch `profile-1` on origin (READY profile-1@6113c39168a posted to lanes/ROOT-MERGE.md for ROOT-MERGE-63, 11-13 ~18:5x) (worktree intel1 /srv/opentallas-scratch2/claude/profile-1; sparse test worktree epyc4 /srv/opentallas-scratch2/claude/profile-1-test, branch profile-1-test). Merges clean on main 4702c3c43a6.
- One switch: env `OT_SIGNOFF_PROFILE=minimal` (default) | `legacy` (= main behaviour; the 4 legacy test modules pin it and pass).
- tools/die_plan/signoff_profile.py: judge() = DRC 0, TT WNS >= -42 ps (R-PERIOD HELD: OT_DIE_PERIOD_PS[_<DIE>] opt-in only), internal FF hold >= 0 (port-start-only hold = advisory); INF slack = NOT RUN.
- signoff.py (verdict from profile, legacy_verdict kept), signoff_chain.py (re-judge, preflight + routed LEC advisory/async), autopilot.py (classify, chain LEC, WAIT-PARENT recheck, path gate, GEOM advisory, NEAR-MISS re-finish budget AP_MINIMAL_REJUDGE_PER_TICK), kit_wave.py (visual advisory mode, one auto retry ledger minimal_retry, unchanged/form/flow-repeat off, preflight advisory), pair_slack_gate.py (die gate at P_die, kit window advisory), gen_phys.py (pre-place LEC dropped via K/lec_preplace.off; OT_HOLD_STOP_PS=-1e6, OT_HOLD_STRUCTURAL_ADVISORY=1, OT_GRT_POST_MAX_S=43200 in new kits), orfs_hold_mm.tcl (env OT_HOLD_STOP_PS override).
- tools/die_plan/rejudge_minimal.py: re-judge tool (run on intel2: --local intel2 --scan).

## Runtime (intel2 /srv/opentallas-scratch2/claude/kw38/rt, what autopilot.service runs)
- Deployed: autopilot.py patch (backup autopilot.py.bak-profile1-1113, AP_MINIMAL_REJUDGE_PER_TICK default 8 there since 18:15) + tools/die_plan/signoff_profile.py (new file). Revert: copy .bak back, rm signoff_profile.py.
- NOT deployed: signoff_chain.py / kit_wave.py / gen_phys (KIT-OPS-2 did the kit_wave config equivalents). Deploy after merge.

## Results
- Re-judge: intel2 /tmp/p1rj/out/{rejudge.tsv,tiers.txt}; lanes/PROFILE-1-SIGNED-1113.tsv; RESULT in queue (81 signed types, 47 gained).
- tools/conftest.py pins every test to OT_SIGNOFF_PROFILE=legacy unless it opts in.

## Release tree DIGEST-KEEP (coord 5ae275b3c96)
- ~/coord/tools/release_tree_plan.py: type_blocks/digest_keep/ledger ~/.local/state/fleet-viz/release_tree_block_ledger.json (seeded 11-13 from counted plans). Backup of the previous file: intel2 /tmp/p1rj/rtp_before_dk.py (also git fd1fd24c015).
- Not yet covering bind/RTL digest (block only); hard-core designs still credit by pins as before.

## Open
- R-PERIOD held (owner decides on the evidence in the RESULT 11-13).
- After merge: refresh rt kit_wave/signoff_chain/signoff/pair_slack_gate/gen_phys (see READY note).
- 16 WAIT-PARENT jobs on epyc5 + 1 on epyc6 cannot archive (hosts gone).
- Post-archive BAD-visual demotion not implemented (BAD before archive withholds).
