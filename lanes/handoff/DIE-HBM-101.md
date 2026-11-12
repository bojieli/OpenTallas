# DIE-HBM-101 lane handoff (HBM die owner, phase 2). Updated 2026-11-12 13:45 PST.

## 1 Scope
Single HBM owner for phase 2, and owner of EVENT-PLAN hbm: the one whole-die structural plan event. Succeeds DIE-HBM-100, HBM-HANDPLAN-1, VISLAYOUT2-HBM, CORES-HBM-1 and the hub/root/stale lanes; directs DIE-LAYOUT-HBM (a3080da31af94f3a0).
Owner rules in force: structural first (no per-type tries), re-floor/re-sign OK, plan changes pre-approved, visual gate before route and before sign-off, core shapes frozen (moves OK).
Visual gate: every new form stops at place until GEOM-VIS-8 says GOOD or ISSUES-ACCEPT. I view every render myself before the REVIEW-REQUEST.
FLEET BALANCE (COORD 08:4x): no HBM private job waits >20 min on a loaded host. Copy --dir to epyc9 (or the least-loaded host), re-submit, cancel the old waiter by exact client PID.

## 2 EVENT-PLAN hbm (the main line)
BASE (13:3x decision): pR3x 0431dc28051a + phantom_all_1112_r3x, WITHOUT qq. qq_b10x_1112_r3x (2737efc9dcdb) is void: all 34 qq lanes FAIL P1/P2. The 15 hp1 beat lanes in hp3 FAIL too, and L7500 is 8-beat (unsupported). Only L74 may have beats > 1 (its leaf RTL serialises the word). pR3x has only L74; pE1a has 35 (L74 + qq), so it is superseded.
Evidence: branch claude/hbm-qqbind-1-1112 @79c723e6a62b (hub:OpenTallas, UNMERGED, off the train until a lane passes P1/P2), tools/hbm_halfwidth/qq_p1p2_verdicts_1112.tsv. Emitter tests: test_bind_beats 5/5, bind/check regression 115 passed. Scratch epyc9 /srv/opentallas-scratch2/claude/hbm-qqbind-1 (57G) kept until I release it.
Parts, in order:
1. DIE-LAYOUT-HBM: pE1w = pR3x + phantom + its deltas re-scripted (NE_io, NW_io, b102grow, b113win re-checked at word width, phytap3, q_b010 pair0, b010pinch v2 L5064 regs to y 820, NE_io a30), with an assert that L74 is the only beat lane. Plus a G0 baseline on pR3x + phantom.
2. tiersS on q_b100/b102/b103, sized from the WORD-WIDTH demand: 65/65/44 + H +60.48 if that still holds, else bigger. The root tkm tile rows above root-frame y 1728.0 move up as a block, and everything above die y 6065.28 shifts with them (clock spine, ft_hop_lockup). Fallback (b) 40.6/40.6/36.3 from the same script. No M8 exception. The E-face L1220_i broadcast routes through the top-right free 220x516 block. The root move goes to GEOM-VIS-8 before any type rebuild.
3. Mine, by script on pE1w: the 10 seam turnarounds (hp5_rows.py rows 319..315, hp5_s1.py in-pin station +1 cyc declared, hp5_sp.py 0-cycle out-leg respace), then the y 11955.6 spread (L1271x8/L5076x2 spt0 turnarounds + b113 top regs, or L8350 pair to M6, whichever has the lower peak), then ft_nudge, gen.py latency, G0, and the station-aware fabric (tools/die_trial/fabric.py) against the base.
Spec for the 10 lanes: q_hub_nw:L1218x1,L1219x1,L1225x1,L1238x1,L1239x1 and q_hub_ne:L5018x1,L5019x1,L5025x1,L5039x1,L5040x1.

## 3 SEAM results on hp3 (G0 errors; hp3 = 544; relative only, because hp3 undercounts word width)
The channel forms (hp4..hp4i) are stopped; hp4i 520 is a reference only.
hp5 560 (+16 first-hop reach) -> hp5a 529 (in-pin stations; new: last station -> out pin 430-494 um) -> hp5b a2f3d8978d18 521: ZERO new errors, a strict subset of hp3 (gone: latency 19, stations 2, hops 2).
fab_hp3 / fab_hp5 (epyc9 .../hp1lane/fab_hp3, fab_hp5; window 0,9700,40000,12600; logs intel2 ~/die-hbm-101-logs/fab_hp*.otrun.log) are in GRT. When done, run rowm8.py on fabric.guide for rows 10335.6-10400.4, the moved rows and 11955.6-11988. Compare hp3 against hp5 only; absolute peaks come from the event plan.

## 4 Work files (analysis plans DO_NOT_COUNT)
Plans: epyc9 /srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane/plans/<plan>/die_plan.json. DIE-LAYOUT-HBM plans: epyc7 /srv/opentallas-scratch2/claude/die-layout-hbm/suchan/<plan>/.
Scripts: epyc9 .../hp1lane/hbm101/ and localhost scratch /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/hbm/ (hp5_rows.py, hp5_s1.py, hp5_sp.py, seam_*.py).
kw45 tools tree: /srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18 (ft_nudge.py PLAN OUT LEDGER; gen.py latency PLAN --inplace; check.py).
G0: sed s/hp5a/<plan>/g hbm101/g0_hp5a.sh > hbm101/g0_<plan>.sh; then from /tmp on intel2: nohup ~/.local/bin/ot-run --mem 16 --threads 2 --hosts epyc9 --dir .../hp1lane -- bash hbm101/g0_<plan>.sh. Report: .../g0_<plan>/g0_report.json/g0_report.json (level/check/msg). Compare with hp3 by exact message (scratch hp3_err.json).

## 5 Builds / agents (all report to me)
- DIE-LAYOUT-HBM (a3080da31af94f3a0): pE1w + tiersS (section 2). Awaiting the pE1w sha, which I asked for early.
- HBM-CORES-C (aa7c81666cfdde1de): WBQ H13 route to sign-off (on main, train 9; GEOM-VIS-8 OK to route). WBQ g0 ffc2 NOT SIGNED (hold -77.38 on 1087 + 6 DRC, pins in the macro footprint); g1 -124 rbin3: classifying, no new builds. opsa_group0 lattice fix PLACED, REVIEW-REQUEST posted; READY @2cd7ad3fb3c2 after the verdict.
- HBM-CORES-B (adf5204cb4034d7c1): TREG on main (train 6). RDREG=1 UNPROVEN until the k-induction / fault BMC lands; no claims without them.
- Q2N2-C2-1 (a4ef59c02a414ba7e): q2n2 C2 + vecd4ae P PLACED, REVIEW-REQUESTs posted; neg_select pending. Route only on GOOD / ISSUES-ACCEPT.
- VP4-RST-1 (a451df755f3d2c1c8): vPose3R PLACED, REVIEW-REQUEST posted (WNS -177). vPose3R2 ordered (per-side a_rows copies + g1 reg-guide boxes); it hit the usage limit, so resume it by SendMessage.
- GEOM-VIS-8: q_su20/q_su21 BAD / WAIT-FORM -> new form from the verdict classes (fold into the event if structural).
- HBM-QQBIND-1 (aa3256f7b06d5faaa): CLOSED (section 2).
- topk: C2 stopped at GRT (congested); D and A2 running.

## 6 Posted today (COORD-REVIEW-QUEUE, DIE-HBM-101)
post101_25..42 as before (failure owners, REVIEW-REQUESTs, STATE, seam table, hp5 approval, qq inside hp5). post101_43: hp5/hp5a/hp5b G0 + tiersS ruling. post101_44: event base drops qq. post101_45: hp1 beat lanes fail; base clean; hp3 numbers relative only. Each one is verified on origin.

## 7 Next steps
1. pE1w sha -> port hp5b parts by script -> G0.
2. fab_hp3/fab_hp5 done -> rowm8 -> post hp3 against hp5.
3. tiersS + root move -> GEOM-VIS-8 -> event G0 + fabric -> post -> type rebuilds.
4. y 11955.6 spread on the event plan.
5. STATE every 60 min (last 13:4x = post101_45).

## 8 Gotchas
- check.py: station 0 of a normal ft slot is the in-window pin; regs_um[0] "is not a native placement". bit_sites_um has one fewer entry than regs_um.
- G0 schema errors short-circuit the whole run.
- die triage (die_trial) is station-blind (one net pin-to-pin); fabric.py is station-aware.
- coord-commit can lose an append: verify with `git show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md | grep -c <text>`.
- Branches are pushed to hub:OpenTallas, not GitHub: verify with `git ls-remote hub:OpenTallas <branch>` from /tmp on intel2 (never git inside /home/ubuntu/OpenTallas).
- On intel2 under nohup use ~/.local/bin/ot-run. Kill only exact PIDs.
- Sealed ot-job dirs are deleted with their GRT logs: plain ot-run --dir kits keep artifacts.
- A plan lane with beats > 1 and no beat_endpoint binds as a narrow 1-beat lane and spills silently. Never add beats without a P1/P2 PASS.
