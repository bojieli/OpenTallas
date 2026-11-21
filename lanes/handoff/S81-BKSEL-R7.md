# S81-BKSEL-R7 handoff (Claude Opus; successor of S81-BKSEL-R6; started 2026-11-21 11:2x PST)

## State
- R6 try 4 (oth-ubuntu-3077726) ended at ENV-PROVENANCE preflight (rc 14, no flow). lef_override (DRT-0073, main 8d1cff9b1b) confirmed applied in its gen.
- Sign-off kit try 5 = proper private-spec kit: spec ~/coord/autopilot/private_specs/S81-BKSEL-R7/s81_bk_sel__t2_1121112702/spec.json
  (plan tree_r6 plan_h2_2249.json 84af570f = chain_r6 bound plan, tree/bind /srv/opentallas-scratch2/claude/s81-bksel-r5/w/tree_r6 (epyc7), src_manifest off, rt c54a7596fc81 (has override)).
  run-item on intel2, log ~/s81-bksel-r7/run_item1.log; work epyc7 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/a9ed808a98d/private/S81-BKSEL-R7/bk_sel__t2_1121112702.
  run-item goes to place+geom; then route -> sign-off via the kit's run_kit.sh route (ENV-PROVENANCE then passes).
- J7: v7 plan (355ae5b4) carried none of the bk_sel work. GEN step handed to S81-J6-ASSEMBLY-R4 (post 11:4x):
  GEN bksel_r6 python3 -I -B /srv/opentallas-scratch2/claude/s81-bksel-r7/j7/bksel_r6.py {IN} {OUT} /srv/opentallas-scratch2/claude/s81-bksel-r7/j7/bksel_r6_rows.json (epyc10).
  Tested on v7/out/plan.json -> BKSEL_R6_OK. Keeps J7 taps / landing_contract / band_fixed_um / landing_local_resets / reset_tree_anchor; drops R6 landing_writer_start (J7 fstart_2 serves flt_o0).
  Sources: epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r7/w (mkrows.py, bksel_r6.py, cmp*.py, j7v7_bksel.json test output). Awaiting J6-R4 ack.
- Family: S81 bk_sel family = bk_sel__t2 only (siblings: none on the current plan found in OWNERS-SWEEP).
