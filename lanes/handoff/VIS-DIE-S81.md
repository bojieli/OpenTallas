# VIS-DIE-S81 handoff (Opus, started 11-22 23:0x PST by COORD; brief scratchpad visual_brief.txt + visual_brief2.txt)
Scope: whole S81 die floorplan (core placement, channels, pin windows, ft, clock trunk/taps, reset, outline/reticle). Families: VIS-S81-COL (col), LEAF-ROUTE-CBC (leaf), VIS-S81-MISC (rest). Rows -> S81-J6-ASSEMBLY-R5 (J9 cut 11-23 12:00).
Work: epyc9 /srv/opentallas-scratch3/claude/vis-die-s81 (in/plan_j8.json = f65f62779bef copy of epyc10 s81-j6-r5/j8_cut_intake/plan_candidates/j8_v3_c67f_revert2_repriced.json; scripts die_vis.py, wuc.py, wmove.py, es_render.py; matplotlib via ~/.local site path under python3 -I). Outputs mirrored to intel2 /srv/opentallas-scratch2/claude/vis-die-s81/out.
## 11-23 00:0x status
- Renders READ: die_j8_status.png, die_j8_lanes.png, die_j8_edgestrip.png. Verdict in GEOM-REVIEW (00:0x).
- Findings: reticle-bound (Y +19.5 um, X +306 um); EDGE-STRIP 241 types (census lanes/handoff/VIS-DIE-S81-EDGESTRIP-J8.tsv); hub-star ft through leaf.
- Window-off-core die row (wmove.py, col excluded) rejected: 254/524 no free span, rest median 478-um shift. No die-level move row for J9; fix is type re-floor inside outlines (family lanes).
- Offer: svc_lo/svc_hi internal top bands (560/337 um) are the only Y slack in the central column if a family form needs Y growth.
## 11-23 00:3x EDGESTRIP-1 (COORD ruling: svc 16 + dsdv 16 + gunit 1 mine; leaf = LEAF-ROUTE-CBC row; col = VIS-S81-COL colstrip)
- Tool: intel2 /srv/opentallas-scratch2/claude/vis-die-s81/out/es1/edgestrip_row.py (sha 3402099f6841; needs adv_port_window_pair.py beside it). Rigid/band interior shift inside the outline; hard cores + placed contents macros move as boxes; points stay or ride so none lands in a moved core.
- Advisory: ADV-EDGE-STRIP on main @02f464834f (plan_advisory/plan_gate_pre, estimator only).
- svc row EDGESTRIP-1-SVC: es1s_ops.json 59fa16168dad (68 ops, die_row.v1) on J8 f65f62779bef -> plan 37071d327d45. S strip 69.12 on all 16 (rs +34.56 y, pvso -21.6 y); W/E 34.56/41.04 stay (u_c grid fills width, N band 52-195 um < 259 core) -> J10 re-shape needs Y. Render es1s_types.png READ. PRE: epyc10 run (logs/pre_es1s.otrun.log).
- dsdv: withdrawn from my row. With xg contents macros counted, 12/16 PARTIAL on J8 and on MISC xga1 b37598492d25 -> strip constraint goes into SLICEC-XGARRAY-1 (VIS-S81-MISC). gunit -> GUNIT-SPREAD-1 (MISC).
- Leaf: LEAF-ROUTE-CBC row PASS on 53 OK types (lanech_before_after.png READ); 20 PARTIAL-STRIP + t15/t30 on its J10 re-shape list.
- svc probe: no svc bind/placed DB since 11-19 (R9 hi4 bind OOM), so a placed probe waits on that bind; evidence = PRE + render.

## 2026-11-23 J9 die rows (VIS-DIE-S81)
- EDGESTRIP-1-TF: ops epyc10 /srv/opentallas-scratch2/claude/vis-die-s81/tmp/es1s_tf_ops.json 15c1e2a4c1d1, plan plan_j8_es1s_tf.json 5083e8acea36, PRE PASS. edgestrip_row.py 005d0a80844f takes --tapfix (tapfix.py 22c28916bb44) and re-seats the 8 table taps that ES1 put inside core halos.
- LEAF-GROW-276 v3 -> J9: tool die_grow.py cd6b7ac4526b (epyc9 /srv/opentallas-scratch3/claude/vis-die-s81/in/). On J8 it gives ops 27d92851eb60 and plan c9a4768659a1, die 32970.24 x 25980.48, PRE PASS. Row 19690: t8 does not grow and t75 takes +112.32, which avoids the 1600-um tap-grid renumber. The tool has a J8-width guard; a commutation test on misc_v2 kept 441 edits and changed none.
- COL-YGROW-1: tool col_ygrow.py 2dbaf2b1359d (epyc10 tmp/). On COL 56d5a17e72bc: 16 overlaps -> 0, 18 col parts moved down, 22 E/W port slides (strict bind), PRE PASS. Render: epyc9 out/ygrow.png.
- R5 compose order: type rows -> col_ygrow -> die_grow -> LEAF j9F -> WESTRIP -> ytrade -> edgestrip --tapfix -> tapfix -> PRE.
- Agreed with WESTRIP: its svc +69.12/column runs in the grown frame and takes the growth from the 578.88 seam gap; the station column is untouched.
- rc72 col_h9_r0: no growth (FAM chose a view pin-access fix). rc66 SPARSE-TAP-1 = 11 serdes types, to TAP-GRID-R5, co-owned by FABLE-UNC-S81-DIE. rc67 waits on HOP-GAPS.tsv. rc68 no-row verdict is waiting for FABLE-RC-S81 to accept it.
- Open: G0 on grow_tf is running on epyc9 (out/g0c_plan_j8_grow_tf.log). The svc W/E strip is covered by WESTRIP.

## 11-23 06:3x PST
- Real-frame G0 (81e1+tapfix) vs J8: 78 new. Breakdown: slab gap (WESTRIP closes) 16; hops+stations 49 (ft_hop_fix --limit 400 closes 51/52; order: after reprice, before PRE; LEAF runs it post-j9Z); WINCLASH 12; reset env 1.
- die_grow 93d12be1c5c5 WINCLASH-1 (pair-side + iterative side flip) -> frame epyc10 vis-die-s81/tmp/plan_g2_20900.16.json 828de609d6aa, ops 84c58f25c0bc, PRE PASS. Changes 4 non-leaf types + 5 ports vs 81e1. Sent to R5 + WESTRIP (rerun on 828de). checker tmp/winclash.py f789cbd26d6d.
- Evidence epyc9 /srv/opentallas-scratch2/claude/vis-die-s81/out/ (hopfix.log, hops_bytype_g20900.txt, g0_plan_g2tf/, g0_plan_g2hf/ running).
