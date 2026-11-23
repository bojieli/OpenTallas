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
