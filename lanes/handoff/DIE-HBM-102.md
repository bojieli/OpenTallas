# DIE-HBM-102 lane handoff (HBM die owner, phase 2). Updated 2026-11-13 (see the last section for the final state).

## 1 Scope
Successor of DIE-HBM-100/-101 (both stopped). Job: HBM plan event pEv11 from the pEv10 open list, post READY, stop.
Base: pEv10 b334c92f7a84 (main train 26, events/hbm_pEv10_1112/). wbq v8 on main (train 27). kitist tools (claude/hbm-kitist-1@deea4319e1, train 31) are NOT in main yet, so pad_landing / station_trees can't be bound from main.
Owner rules: an event posts when its current gates pass; new non-functional findings go to the open list; structural first, whole families; visual gate GOOD/OK/ISSUES-ACCEPT; core shapes frozen (move/rotate); growth/cycles/perf pre-approved.

## 2 Locations
- Worktree: epyc7 /srv/opentallas-scratch2/claude/die-hbm-102/wt (clone of hub:OpenTallas).
- Plans: epyc9 /srv/opentallas-scratch2/claude/die-hbm-102/plans/{pEv10,pEv11a,pEv11b,pEv11c}. The event plan is pEv11c, sha c9ac33aeb09c. pEv11b (4417c4c4da2f) is superseded: its L1219 move gave 2 new G0 errors.
- Scripts: epyc9 .../die-hbm-102/scripts/: d1_captap.py, d3_nwio.py, d4_rows.py, mk_ev11a.sh <out> (= pEv10 + d1 + d3 + d4 + ft_nudge + gen.py latency), g0.sh, g0diff.py, rownets.py (names the nets in a fabric row), render_ev11.py, pkg_stage.sh.
- G0: epyc9 .../die-hbm-102/g0_pEv11c/g0_report.json/g0_report.json. Bind: epyc9 .../die-hbm-102/bindEv11c/ (recipe = bindEv10, tree /srv/opentallas-scratch2/claude/wt/hbm101_main_12994e9e). Renders: epyc9 .../die-hbm-102/renders/pEv11c/. Logs: intel2 ~/die-hbm-102-logs/.
- Plan tools tree: epyc9 /srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18 (same as pEv10).

## 3 pEv11 content
1. d1: TIMING-CLASS SKEW family q_spb1/vsN1/vsN2. Every latched ft hop goes on its capture tap (plan clock.ft_hop_lockup.tap = capture: q_spb1 20 hops, vsN1 32, vsN2 28, of which 8 were launch). gen_phys now emits OT_HOP_LATCH_CAPTURE_TAP with 22/34/30 regexes. Before, q_spb1's L720x3 latches were not covered at all.
2. d3: NW_io gets the NE_io pR9b spread, mirrored. The 612-bit L51_i/L52_o W-pin chains run up the E channel and over the ep top. 67 shared small-slice reg sites are split. Max hop 391.5.
3. d4: fabric rows over 1.0. B y 12019.2: q_b113 L1271x7 legs 13-16 move to y 1562 (row 12048). AW y 10416 (q_hub_nw L1219x1): the move was WITHDRAWN in pEv11c. The fabric already spreads the bus over 5 rows, and dropping the line more than 87 um below the N pins breaks the real-bit in/out hop budget (G0 check_hops measures the worst real pin bit, not the window midpoint). q_hub_nw = pEv10.
Gates: G0 468 / 0 new vs pEv10. latcheck 0 mismatches. reset 0. pairsym 3 old q_sm3. Bind 0 errors. LANE_ASBUILT 420/420. The r8 table is identical to pEv10's.

## 4 COORD inputs handled
- PHY_NC/NW attempt_1: not routed. Single-tap class; pEv10's 3-tap form supersedes it (STATE 00:58).
- q_b010 pair0 177.12: already in pEv10.
- Fabric rows: nets named (see the READY). The DE/DW-4560 rows are a fabric.py artefact: it ignores bit_sites_um.

## 5 Gotchas
- check.py-style helpers need cwd = tools tree root and S.Plan(raw, Path(plan_dir)/'die_plan.json'), else the pin tables fail to resolve.
- python3 -I hides user-site matplotlib: render_ev11.py appends site.getusersitepackages().
- G0 report path is g0_<plan>/g0_report.json/g0_report.json (a directory).
- coord-commit can lose an append: verify on origin.
- G0 hops/stations take the max over the REAL window pin bits (die_hop_scan.first_internal_hops), so a plan-side check that uses window midpoints is too lenient.
- Commit identity in the epyc7 wt: -c user.email=contact@icourses.com (no global identity there).

## 6 Final state (2026-11-13 01:5x, lane STOPPED)
- READY posted: branch claude/die-hbm-102-event-pEv11-1113@38aa9680f8 (parent main 455a69fc3d), events/hbm_pEv11_1113 only (26 files), verified with ls-remote.
- Posted: STATE 00:58 (PHY attempt_1 superseded). RESULT 01:3x: the 42-hold list after pEv10 (release root + q_spt1/q_spt2/vsN4/5/6; q_spb1/vsN1/vsN2 wait for pEv11; the rest stay held with their reasons) and n4ext (the pEv10 form is the signed n4ext_1110 slot, so no P&R row; staged view + pin check). FINDING 01:3x: PHY_NC/NW pEv10 MPL-0006 = macro_skip_rtlmp.tcl generator (KW-FIX-45) missing from main.
- Next owner: the HBM-FORMS lane proposal (q_su family split/streets, q_spu1 re-pin), the AW L1219 structural option (bit sites or +1 station), the B-window fabric re-run on pEv11c, and the PHY_N overlay.
