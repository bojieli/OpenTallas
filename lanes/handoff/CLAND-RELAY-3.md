# CLAND-RELAY-3 handoff (successor of CLAND-RELAY-2; COORD is the coordinator)

## Scope (COORD rulings on CLAND-RELAY-2 asks, 11-13)
(3) APPROVED: reader-START copies at <= 48 loads (2 copies per 64-bit chunk, same K-1 / align +1 timing), ring module
change + equivalence proof (rsbench 203 cases + LEC), physical proof hd_turn_b (write_chunk 16) + hd_spn_wshim_rx to
sign-off (slew 0, DRC 0, land-ring hold >= 0), K recount per die, lane_asbuilt_latency KV vN2i + S81 r12bA PASS, ONE READY.
(1) write_chunk 16 on hd_turn_b/turn_a/st_n4 approved for the next HEAD event (plan change, not this lane's branch).
(4) cross-tap hold -> RELAY-PLACE-1 / HEAD clock owner.

## Worktree
epyc9 /srv/opentallas-scratch2/claude/cland-relay-3/wt, branch claude/cland-relay-3-1113 = origin/main 455a69fc3d +
cherry-pick of claude/cland-relay-2-1112 7073a6b4a5..c08c2078ea.

## Log
- 2026-11-13: lane started; worktree created.
- Commit 55c2175cfc (local, on epyc9): RSTH-1. ot_meso_dsel NR (align/on copies), ot_meso_ring_ca derives RH from
  RSTN (RSTN-1 = RH x NCH), clock_landings.ring_reset_copies_per_chunk (smallest h | DSREP with DSREP/h x 2 DEPTH + 1
  <= 48; D4 DSREP8 -> 2 = 33 loads), verify + tests. Default / legacy forms identical logic.
- Proofs: rsbench (lane dir rsbench/): RSN 19 PASS 203 valid / 26194 edges (same numbers as RELAY-2), RSN 10 PASS,
  mutant RSTH FAIL (match 0), mutant K FAIL. yosys eq (lane dir eq/, tools/die_plan/bench/landing_rsth/eq_rsth.py):
  IDENT 186 PROVED (main vs branch, same params), RSTH 5 PROVED (N=1+NCH vs 1+RH*NCH with relay_rep, opt_merge),
  RSTH_MUT UNPROVEN (36 cells) -> EQ PASS.
- K recount (lane dir kd/, kdelta_list.py + RSTH copy column): HEAD rp18r2 51/389/21, 11 boot; KV 828/2260/34, 867
  boot; QC 135/231/9, 135 boot; S81 0. Copy count changes: HEAD 60 buses/420 inst, KV 522/913, QC 784/1821, S81 0.
- Kits (rp18c prep == rp18r2 for these 2 types, sink bins sha-equal): proof_turn_b_wc16 (pd_wc16 plan = rp18c +
  hd_turn_b write_chunk 16), proof_wrx (wave export). Both RSTREP 19. Routes via ot-run epyc9, logs ~/cr3log/*_route.log
  (localhost). lat_all.sh / pytest via ot-run, logs ~/cr3log/lat.log, pytest.log.
- GitHub push: epyc9 has no GitHub key; push branch to hub from epyc9, then mirror to GitHub from localhost scratch.
- Results: hd_turn_b wc16 DRC 0, slew 0/0, fanout max 39, TT +104.02, FF hold -14.07 / 25 endpoints ALL u_ft_t_s0 ->
  u_ft_t_s1 (cross-tap, RELAY-PLACE-1), land-ring 0. hd_spn_wshim_rx DRC 0, slew 2/2 = u_srl_41 / u_rrl_75 reset relay
  long single-load wires (reset reach class, not CLAND; reader-START nets 0), TT +2.64, hold core PASS (port-only).
  lane_asbuilt KV vN2i PASS 2404, S81 r12bA PASS 873. pytest 138 landing/ring files: 1066 pass, 6 fail, all
  pre-existing (5 fail identically on main tools; strap_lec = host yosys without ORFS libs).
- BRANCH claude/cland-relay-3-1113@cc66ce9f82 pushed to hub AND GitHub (verified ls-remote).
- READY posted; lane STOPPED. Open: wshim_rx 2 reset-relay slew pins (reset reach owner); turn_b cross-tap hold
  (RELAY-PLACE-1); write_chunk 16 on hd_turn_b/turn_a/st_n4 is a plan change for the next HEAD event (not on branch).
