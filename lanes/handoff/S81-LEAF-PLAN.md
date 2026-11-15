# S81-LEAF-PLAN handoff (lane for COORD; cc DIE-S81-92, KIT-OPS-5), 2026-11-14

Input: lanes/handoff/FABLE-REVIEW-CONG.md + FABLE-REVIEW-CONG-leaf-violations.tsv (R-LEAF-1/2/3). All builds private, DO_NOT_COUNT.

## FILES FOR DIE-S81-92 MERGED B6 (READY 2026-11-14, newest)
- B6s leaf part for the single merged S81 B6 (not for separate adoption). Files (identical on epyc7, epyc8, epyc9): plan epyc7:/srv/opentallas-scratch2/claude/s81-leaf-plan/ev/B6s.json (aa2aa99e499a)
- sidecar epyc7:/srv/opentallas-scratch2/claude/s81-leaf-plan/ev/side_B6s.json (18941025a5f8)
- LF_CS netlist epyc7:/srv/opentallas-scratch2/claude/s81-leaf-plan/cp13/lfcs_B6s.v (e64c0106d0f3
- overlay copy /srv/opentallas-scratch2/claude/s81-leaf-plan/ovl_l6s/physical/die_plan/s81/bind/inputs/die_b178_lfcs.v
- re-stage on the merged plan with tools/die_plan/stage_lfcs_netlist.py)
- compose script epyc7:/srv/opentallas-scratch2/claude/s81-leaf-plan/cp13/compose_b6s_leafplan.sh (picks cp13/pick.txt, form outputs cp12/ cp10/t53d cp9/t34s4, signed keep cp10/signed_keep_leafplan.py)
- delta package epyc7:/srv/opentallas-scratch2/claude/s81-leaf-plan/ev/B6s_leaf_delta.json (6e5d167d041f: 114 type rows vs 92e2, 113 sidecar collector.types, signed list)
- type list epyc7:/srv/opentallas-scratch2/claude/s81-leaf-plan/ev/types_event_B6s.txt (114). Signed restore: 35 signed slice_station rows stay on 92e2 (re-key 0), consistent with FABLE-PLAN-B6A F1 (signed t41, t6 cl54a9ceeb, t29 cl2e5c855a/clc7772371 station rows stay at 1226.88 with the declared 51.84-um jumper channel). +1 feed-through list (COORD approved
- B6t, in progress, delta follows): ot_s81sl_leaf__t34 ft1/ft3/ft4
- t28 ft2/ft3/ft4/ft5/ft6/ft7/ft10/ft11
- t75 ft0/ft1/ft2/ft4/ft5
- t13 ft0/ft1/ft2/ft3
- t71 ft0/ft1/ft2/ft4/ft5
- t7 ft3
- t53__clb66fa5cb ft0 (27 slots
- latency.lanes +1 per crossed slot on 24 lanes, x_W4_in/x_W4_out/up_s_1N_L4 +2
- chained ft_add_station plan epyc7:/srv/opentallas-scratch2/claude/s81-leaf-plan/ev/B6t_ft.json, ledger cp13/ft_take_ledger.jsonl). M9 per-type grant list (layer_budget.type_m9_grant), in order: ot_s81sl_leaf__t34, t9, t73, t75, then t28, t13, t7, t71. core_place: branch claude/s81-leaf-plan-1114 a7c4842c82 (+ whole-slot ft re-route fallback, uncommitted, for B6t).


## STATE 2026-11-14 ~20:0x PST (successor; CURRENT, newest first)
- B5 bind DIED 19:08 epyc8 ELAB yosys rc 137 (OOM kill writing asbuilt.json), like B4L4. B5 is NOT adopted; it is carried by B6s.
- COORD signed check: B5 (and draft ev/B6.json 3fa698db24a1) re-key 35 SIGNED slice_station types (clock.landing_contract bands only). Fix: cp10/signed_keep_leafplan.py restores plan row + sidecar collector.types/parts from B3z2 92e2 / side_z2_92e2_fix (signed list ev/s81_signed_1114.txt from rtx-pro INDEX.tsv); check cp10/signed_rekey_leafplan.py. Adopt list excludes signed types.
- core_place: --take-regs (commit 671e2ed64a, COORD take +1 register) and --slot-ft UM (FABLE-HARD-S81 rule: registers in face-to-core slot < UM masked and re-sited, same count) in wt/ + tree/ (copy+mv).
- Trials: cp11 (take-regs + face-clear; face-clear alone leaves slot regs), cp12 (slot-ft 86.4; A = no face-clear, B = face-clear). Rule checker cp9/slot_rule_leafplan.py PLAN TYPES (B5: 172 regs in 14 types).
- Compose: cp13/compose_b6s_leafplan.sh (B5 + cp12 picks in cp13/pick.txt -> tapleg -> publish -> bands -> densify -> signed keep -> sync -> audit -> check -> LF_CS) -> ev/B6s.json / side_B6s.json / cp13/lfcs_B6s.v.
- M9 (ve/vs cores, FABLE-HARD-S81 sec 0/2): no per-type plan key exists (layer_budget.partition_signal_max die-wide, gen_phys clamps OT_CONS_MAX_LAYER to plan top); grant is DIE-S81-92 B6 / WAVE-RECIPE-1 (m9_grant like m8_grant.py). Posted as ASK.
- B6s = ev/B6s.json aa2aa99e499a / side_B6s.json 18941025a5f8 / LF_CS e64c0106d0f3 (overlay ovl_l6s, on epyc7/8/9), picks cp13/pick.txt (t24A t44A t4A t45A t51A t73A t9A from cp12; t53d cp10; t34s4 cp9), 114 types (ev/types_event_B6s.txt, signed excluded). ONE plan job intel2 ~/s81-leaf-plan/bind_leafplan_x3.sh admitted epyc8 (log epyc8 log/B6s_bind.log); G0 epyc7 log/G0B6s.log (compare with 296); watcher intel2 adopt_watch_leafplan_a5.sh (READY+ADOPT to KIT-OPS-5).
- Open (posted ASK DIE-S81-92 20:3x): ft slots in < 86.4 slot not re-sitable at same count (t34 ft1/3/4, t28, t75, t13, t71, t7, t53) -> +1 ft register = die lane change, or M9 grant for ve/vs class (no per-type plan key; DIE-S81-92 B6 / WAVE-RECIPE-1).
- core_place --slot-ft pushed on claude/s81-leaf-plan-1114 (needs READY to merge after B6s passes).
- Draft ev/B6.json (cp10) superseded by B6s (it re-keys signed types).

## STATE 2026-11-14 ~19:xx PST (predecessor)
- B4L4 cumulative (147 types) strict bind: ONE plan job intel2 bind_leafplan_x1.sh, admitted on epyc7 (log epyc7 log/B4L4_bind.log); watcher a3.
- B5 = B4L4 + 5 edge-ft-squeeze types (TL-LEAFT34 family): ev/B5.json 9d4bee9ea054 / side_B5.json 15f3f6c312db / LF_CS netlist cp5/lfcs_B5.v 2c3837b47ec6 (overlay ovl_l5 on epyc7+epyc8). Types t24__cl81374cd8, t44__clf4ea6d4b, t45, t4, t53__clb66fa5cb (cp5/<t>.json; compose cp5/compose_b5_leafplan.sh, pick cp5/pick.txt). 149 types (types_event_B5.txt). Cycle deltas: s_5S_L3 vni +1; s_5S_L2 u/ver/vni +1; s_0S_L3 vni +1. G0B5 running on epyc7 (log/G0B5.log); bind ONE plan job bind_leafplan_x2.sh admitted on epyc8 (log epyc8 log/B5_bind.log); watcher adopt_watch_leafplan_a4.sh.
- Survey tool cp5/edge_squeeze_leafplan.py PLAN [TYPES]; batch cp5/one_l5_leafplan.sh (face-clear W:86.4:. + ft-resite + taps-movable + link-reg any), results cp5/leaf__*_ev.json.
- core_place (wt, uncommitted): ft-resite re-sites only core-covered regs (base group overlaps ignored).
- Open: t34 (SW quadrant re-floor; street x 484-553 needs vq +60 east -> 4 bus links over limit), t73/t9/t75 (ve pair), t28/t71/t13/t51/t7/t10/t74/t1 squeeze not cleared; tool cp5/ft_street_leafplan.py (re-route an N<->S ft chain up a street, count kept) ready for the t34 form.

## STATE 2026-11-14 ~17:xx PST (CURRENT; supersedes everything below)
- Branch claude/s81-leaf-plan-1114 head 2bed907db4 pushed (core_place --ft-resite / --link-reg / --taps-movable, leaf_edge_squeeze.py, ft_street.py; tests pass); READY posted to ROOT-MERGE-63.
- G0L3f (B4L3f): 296 errors, identical finding set to G0L2f (and the same count as G0ctl3).
- CUMULATIVE (COORD 11-14): B4L4 = Lb+L2+L3+L4 (stacked events). Type list types_event_B4L4.txt = 147 = all types changed vs B3z2 92e2. The separate B4Lb/B4L2/B4L3 binds are cancelled (6 clients, races r1b/r2b, watcher a1 killed by exact PID). Only the twin pair B4L4/B4L48 + race r3b + watcher a2 remain.
- B4L4 = ev/B4L4.json 58f4d1f24d2e / side_B4L4.json f97909118cca, 1 type: ot_s81sl_leaf__t21 (partition s_2S_L2).
  - Form: vsw (86.4,302.4), rxsb (319.68,224.64), --window-clear --ft-resite --link-reg swr,rar. Gives R-LEAF-2 0 (was 2, ft2_o/ft3_o under vsw); 2 ft regs re-sited, count kept; 0 timing over; eq OK.
  - CYCLE DELTA: t21 link class rar (u_rxsb.o_f/o_r/o_v -> u_vs ra_fi/ra_ri/ra_vi, return path) CS_RAR_D 0 -> 1 = +1 cycle inside leaf s_2S_L2. That is 5 internal_stations rows (note "B4L4 link-reg"). No die lane changes in the plan latency table; LATCHECK on the bind confirms it.
  - LF_CS netlist: die_b178_lfcs.v re-staged by stage_lfcs_netlist from B4L4 = cp4/lfcs_B4L4.v 78800271b594. Only diff: u_s_2S LF_CS_RAR_D 20'h10000 -> 20'h10100. It ships in overlay ovl_l4 (= ovl_l + that file) on epyc7 and epyc8. Re-staging B4L3f reproduces the current file byte for byte.
  - G0L4: 296 errors, identical finding set to G0L3f (0 new).
  - ONE strict bind (COORD queue rule 17:4x, twins cancelled): intel2 bind_leafplan_x1.sh = ot-run --priority plan --hosts epyc7,epyc8 -- bindB4L4_leafplan.sh (identical on both hosts), log ~/s81-leaf-plan/bind_B4L4x.log + <host> log/B4L4_bind.log. Watcher adopt_watch_leafplan_a3.sh posts READY+ADOPT (147 types) to KIT-OPS-5 on BIND_RC=0 + LATCHECK_RC=0.
  - Compose script: cp4/compose_b4l4_leafplan.sh (pick list cp4/pick.txt).
- Race fix: race_leafplan_r1/r2 never matched the clients, which were started as ./bind_leafplan_*.sh, so a loser twin would not have been killed. Replaced by r1b/r2b/r3b (pattern accepts ./ or the full path); the old r1/r2 were killed by exact PID.
- Not in B4L4 (open):
  - t73 / t9: ve_m/ve_s 34.6 um off S. The S 86.4 face-clear needs vs/vq moved up too. Seeds cp4/seed_t9.json and cp4/seed_t73.json are space-legal after --taps-movable, but stations then stretch (tv 22/24, ft6/ft8 re-site fails).
  - t75: ve_m/ve_s have no legal W+S spot even with ft-resite + link-reg (ve/ver/rar classes would take +1).
  - Next form for all three: move the ve pair and its N neighbours as one block, with link-reg on station classes.
- COORD GEOM advisory t39 (a9 3_place, ~25 um channel x 985-1000, tap clk_t6 4577 sinks): no t39 GRT/DRT result exists yet (searched epyc7/8/9). In B4L3f the vn_a|E-lane channel is 37-58 um (vn_a ends x 969.8, ln_15/13/10 start 1006-1028). If t39 GRT/DRT struggles, widen it to >= 60 um and split clk_t6 as COORD describes. Not done in B4L4.

## Where things are
- epyc7 L=/srv/opentallas-scratch2/claude/s81-leaf-plan: wt/ (own clone, tools/die_plan/leaf_rules.py + side_band_sync.py uncommitted), tree/ (cp -al of kw45 src_s81_main_7073a6b4a5 + ovl_b3y + DIE-S81-92 cg tie files; NEVER edit files in place there, hardlinks), ovl_l/ (= ovl_b3y + cg tie files + leaf_rules.py; overlay for my binds), run_bind_l.sh (copy of s81-b3-clk/run_bind_b3.sh, F=$L/run, STOP_G0 option), ev/, log/, cp/ (core_place trials).
- epyc9 $L/k/{t32,t2,t61,t75}: private kit copies with the B4L bands written into landing_placement.tcl (bin/prep_proof_leafplan.py), runner leafplan_run.sh (3_3..3_place re-place + Fable proof2.tcl GRT M2-M8 adj 0.25, 30 it); outputs k/<t>/leafplan_place.log, k/<t>/proof/grt.log. Launched from intel2 ~/s81-leaf-plan/proofs_leafplan_w1.sh (ot-run --hosts epyc9 --mem 32, logs ~/s81-leaf-plan/proof_<t>.log).

## B4L-a (R-LEAF-1 bands) = B3z2.json 6d2b7b182853 + band re-site
- Tool: leaf_rules.py check PLAN --match RE (R-LEAF-1/2/3 rows from the plan itself) and leaf_rules.py bands PLAN SIDECAR OUT_PLAN OUT_SIDECAR REPORT: each single-rect band that breaks R-LEAF-1 (cover < 80 % of its window, near edge > 60.5 um from the face, or a column deeper than max(along, 43.2)) goes to the face strip over its own window: nearest inset first, window span (+-8.64 shifts, then widened in 4.32 steps; other >=16-bit windows of the face are soft obstacles), area >= current area, macros without the reset halo (kit cuts band rows at the macro edge; Fable t32 E1), notched around reset relay / collector sites and tap points (multi-rect rects_um, as fill_failed_bands). All copies updated (landing_contract.bands, collector_local_sources[].band, sidecar collector bands + local_sources). Only rect_um / rects_um / max_pin_to_band_hop_um / resited_from_um / resite change.
- Result: 106 bands in 44 types moved (16 multi-rect), area ratio >= 1.0, max pin hop 262 um. check R-LEAF-1: 120 items / 48 types -> 19 / 14. Left: 10 bands need a core move (t9/t73 ft8_i ve_m, t59 ft1_i/ft3_i ln_0/ln_1, t12 ft9_i ln_14, t44 cl f6cf8492 up_s ln_3, t36/t66/t70/t71 blocked by bands/stations), t8/t72 multi-rect bands not touched.
- Files: ev/B4L_a.json (64f5b23fdac6), ev/side_B4L_a2.json (6106f61b3e05), report ev/B4L_a_rep.json, log log/B4L_a.log, checks ev/check_B3z2.tsv, ev/check_B4L_a.tsv.
- Also found in the plan: 30 leaf types have outline 1278.72 / 1356.48 but their N ring bands still end at 1209.6 (69 um off the N face) and the first ft reg sits at y 1226.88; B4L moves those bands to the real face strip.

## Sidecar defect found (affects B3zq)
run_bind_b3.sh sidecar sync fails on B3z2 + side_z2: RuntimeError((ot_s81sl_leaf__t72, local_sources, band semantics differ)) RC=5 (b3z2.py added rects_um to the plan t72 ft0_i band, not to the sidecar copy). Fixed sidecar for B3zq: ev/side_z2_t72fix.json (93c4de451072, 1 record synced, tool bin_side_band_sync_leafplan.py). Posted ASK to DIE-S81-92. STILL PRESENT in 92e2f585dc06.

## B4L-b (CURRENT candidate, 2026-11-14 ~21:3x PST) -- supersedes B4L-a
Base B3z2 92e2f585dc06 (COORD: rows restored) + t72 sidecar band sync (ev/side_z2_92e2_fix.json).
- bands: leaf_rules.py bands -> ev/B4L_b0.json (106 moved / 10 need core move / 4 skipped, same as B4L-a)
- core moves (core_place, eq OK, 0 timing viol, station regs unchanged):
  - leaf__t69 (COORD DRT-0255 evidence, ft0_o/ft1_o S-face window, box column x=19.38 um): --face-clear "S:43.2:g_ln[(0|1)]", --fixed incl u_vn -> cp/t69_fl.json; L2 7->2 (left: vn_b 34.6 um under leafdn_i0/leafup_o0; moving vn_b = +1 reg on 4 stations (idx 140-143), not taken)
  - leaf__t25__cl431c660f: face-clear S 43.2 on ln_0/ln_1 -> cp/t25__cl431c660f_fc.json; L2 5->0
  - leaf__t68: Fable lane form seed + search -> cp/t68_f.json; R-LEAF-3 30->21
- reset re-publish of the 3 types: die-s81-90/h/tapleg.py (moved 0) + frame-forms-1 delta_frame_collector_1113.py (PUBLISH_RC 0; depth unchanged; relays t25 237->256, t68 278->276, t69 247->252) -> ev/B4L_b1.json 625b7c6b777c, ev/side_B4L_b1.json b9589178a764; audit cp/merge_cp_leafplan.py: 0 reset sites under cores, 0 bands under cores. Band x reset-site overlaps 458 (base) -> 370 (B4L), none new.
- rule counts B4L_b1: L1 19/14 types, L2 288/65, L3 2858/80 (base 120/298/2864)
- G0 pair: control G0ctl2 (92e2) vs G0L1b (B4L_b1), both with the 3 bad tap_offset rows dropped (G0-only copies); logs log/G0ctl2.log, log/G0L1b.log
- strict bind B4Lb: bindB4Lb_leafplan.sh via intel2 ~/s81-leaf-plan/bind_leafplan_w3.sh (ot-run 120 GB epyc7, queued), log log/B4Lb_bind.log + intel2 ~/s81-leaf-plan/bind_B4Lb.log
- B4L-a bind and G0 runs cancelled (old base).

## UPDATE 2026-11-14 ~16:xx PST
- Branch head d0a832c7999a: + R-LEAF-2b (leaf_rules.face_need: 86.4 um off any >= 512-pin window; used by check and core_place --window-clear).
- B4L4 (t21, t75, t73/t9 ve_m; COORD: mine): outline growth does not solve it. t21 push vsw +43.2 / rxsb +43.2 (cp3/seed_t21_push.json, cp3/t21_push_ev.json) is space-legal but sits on 26 fixed ft-station sites and stretches 21 direct core links over limit (+1 reg each). Needs ft-station re-site in core_place + core-link re-pipelining under LATCHECK; asked COORD to OK the +1 regs. No new outlines for DIE-S81-92.
- Watchers on intel2: adopt_watch_leafplan_a1.sh (pid 1647566), race_leafplan_r1.sh, race_leafplan_r2.sh.

## STATE 2026-11-14 ~15:4x PST (supersedes the block below)
- Branch claude/s81-leaf-plan-1114 ffbf22f844a3 pushed (core_place --slot-clear / --window-clear, multi-rect band rects; leaf_rules check/bands/--densify; side_band_sync; tests). READY (approved) posted to ROOT-MERGE-63.
- Events (type lists ~/coord/lanes/handoff/S81-LEAF-PLAN-types/types_event_*.txt):
  - B4Lb = ev/B4L_b2.json 199aadf6bac4 / side_B4L_b2.json a0a4bb73671c (48 types). G0 = control (identical errors).
  - B4L2 = ev/B4L2f.json 0eed18fe0e6d / side_B4L2f_s.json 204d809d818b (120 types vs b2). G0 296 = 296 (one die-cut density error moved s_5S_L0 -> s_6S_L0 at y 10750, same class).
  - B4L3 = ev/B4L3f.json 87f3d1b78812 / side_B4L3f_s.json 525af5c97f07 (13 types vs B4L2f; --window-clear slot-clear). R-LEAF-3b 156 -> 103 (B4L2) -> 89 (B4L3). G0L3f running (log/G0L3f.log).
- Strict binds: twins per event on epyc7 (bind_leafplan_w4/w5/w6.sh) and epyc8 (bind_leafplan_e8b8/e828/e83.sh), all ot-run --priority plan, all queued for memory. intel2 ~/s81-leaf-plan/race_leafplan_r1.sh (B4Lb, B4L2) and race_leafplan_r2.sh (B4L3) kill the loser by exact PID when one is admitted. adopt_watch_leafplan_a1.sh posts READY+ADOPT (KIT-OPS-5) per event on BIND_RC=0 + LATCHECK_RC=0, or a FAIL STATE.
  - Fixed bug: wrappers had passed the stale B4L-a plan as the candidate positional arg; first epyc8 attempts failed at sidecar (nothing bound); watcher posted 2 false FAIL lines, corrected in the queue.
  - epyc8 copies of the plan files + ovl_l (old core_place, unused by bind) under the same path.
- t21 / t75 (W face 2 x 1104-bit output windows, core 43.3 um off): face-clear 86.4 / 64.8 finds no legal timing-clean spot (t21 vsw: rxsb blocks; t75 ve_m: ve_s blocks) -> needs W-axis outline growth (B4L4 or DIE-S81-92). Rule ask R-LEAF-2b (>= 86.4 off windows >= 512 bits). t75 growth search cp3/t75_w_ev.json may still be running.
- Not in any event: t2, t22, kv_leaf t5 (+regs), t47 (band under lane), t73/t9 ve_m, kv_leaf t4 t11 t15 t3 t45 t68 (B4L3 gate).
- Proofs epyc9: t32 overflow 0; t2/t61/t75 GRT running.

## STATE 2026-11-14 late PST (older)
- Event 1 = B4L_b2 (ev/B4L_b2.json 199aadf6bac4 / side_B4L_b2.json a0a4bb73671c): G0 296 = control 296, identical error sets (full plans, gen_phys efd8a710944 + sdc_lint 10fbea62820 in tree/ + ovl_l/). Strict bind queued: intel2 ~/s81-leaf-plan/bind_leafplan_w4.sh (ot-run --priority plan, epyc7 120 GB) -> log/B4Lb_bind.log, writes B4LB_RC.
- Event 2 = B4L2 (ev/B4L2f.json 0eed18fe0e6d / side_B4L2f_s.json 204d809d818b): B4L_b2 + slot-clear core moves in 39 types (cp2/, types ev/types_B4L2f.txt) + reset re-publish + slice_station/col --densify (183 bands). R-LEAF-3b 156 -> 103 pairs. G0L2f running (log/G0L2f.log); strict bind queued: intel2 ~/s81-leaf-plan/bind_leafplan_w5.sh -> log/B4L2_bind.log, writes B4L2_RC.
- core_place.py --slot-clear REGEX + test_core_place_slot_clear.py (6 pass), leaf_rules.py --densify: in tree/, ovl_l/, wt/ (uncommitted, not pushed).
- GRT proofs (epyc9 k/<t>/proof/grt.log, B4L bands only): t32 Total overflow 0 after 4 extra it; t2/t61/t75 running.
- Rejected from B4L2: 16 types L2 up (kv_leaf t4; leaf t11 t15 t25__cl55642d17 t26 t35 t3 t40 x2 t45 t54 t58 t62 t68 t6 t7), 4 new band-under-lane (t47 t57 t66 t8), not applied (+regs) t2 t22 kv_leaf t5; t73/t9 ve_m face-clear no legal spot. Next: face-window (R-LEAF-2) term in slot-clear legaliser.
- slice_station densify: 143 bands / 44 types, 22 no-strip; col: 40 bands / 35 types (col_h9_r0_p1 ft0_i 4.69 -> 10.04 um2/bit), 42 no-strip (cp/ss_dens_rep.json, cp/col_dens_rep.json).

## B4L-b2 (CURRENT bind candidate) = B4L_b1 + slice_station__t8 band depth
- ev/B4L_b2.json 199aadf6bac4, ev/side_B4L_b2.json a0a4bb73671c
- t8 (TYPE-SLICET30 13:14 ask): leaf_rules.py bands --densify --per-bit 10 --max-depth 54 (new flag: also re-sites R-LEAF-1-legal bands below per-bit um2/bit): ft2_i/ft3_i 26 um strips -> 54/52 um deep, 10.35 um2/bit (multi-rect notched around reset sites); ft4_i 10.07 um2/bit. Report cp/t8_b_rep.json.
- G0 (on b1, the 3 bad tap_offset rows dropped in both): control 296 errors / B4L 296 errors, 0 new errors; +18 WARN (path text, G0C 8.64-lattice advisories on moved lanes).
- sdc_lint tap_offset fix 10fbea62820 (origin/claude/sdc-lint-tap-offset-1114) patched into tree/ and ovl_l/ (sdc_lint.py e3e66c8e3677, test_sdc_lint_tap_offset 2/2 pass) and cherry-picked uncommitted in wt/.
- t68 COORD column x 880-900 y 330-420: ln_12/ln_13 gone from it in B4L; vn_a east gap 153 um; vn_b|ln_3 23.7 um left (ln_3 +19.4 um shift: 15 timing viols, not applied).
- R-LEAF-3b class list (vn_a/vn_b to ln_* gap 4.32..40): 156 pairs in 61 types, ~/coord/lanes/handoff/S81-LEAF-PLAN-R-LEAF-3b.tsv. core_place --gap 43.2 does not clear existing slots (t62 trial: unchanged) -> needs a slot-clear objective in core_place.
- Strict bind: bindB4Lb_leafplan.sh now BASEP/BASESC = B4L_b2 (queued ot-run epyc7 120 GB, intel2 client bind_leafplan_w3.sh).

## Fable GRT Total lines
- epyc9 /srv/opentallas-scratch/claude/fable-review-cong/d/t68e2/grt.log (30 extra it): `Total 212813367 13867498 6.52% 13 / 6 / 8156` (8156 overflow left)
- epyc8 .../fable-review-cong/d/t75/fix.log (15 extra it): `Total 213287285 34889762 16.36% 46 / 31 / 476498` (476,498 overflow left)
- epyc7 .../fable-review-col/p_h10r0_base/proof.log: in extra iteration 15/15, no Total yet

## Second B3z2 defect (affects B3zq G0 and 2 kits)
G0 check.py on B3z2 crashes in gen_phys.tap_offset_table: clock.tap_offset.per_port_ps rows beyond T/2 (period 833 -> 416.5 ps): eng__t1 clk_c0 TT -550.2 / FF -490.8, bk_sel__t2 clk_c4 -454.5 / -408.2, clk_c0 -470.0 / -421.5. Posted ASK to DIE-S81-92. STILL PRESENT in 92e2f585dc06. My G0 comparison uses private copies with those 3 rows dropped (ev/G0only_*_tapoff3.json; never bound).

## R-LEAF-2/3 (core moves): NOT in B4L-a
core_place.py --seed / --face-clear trials (cp/): t68 ln_12/ln_13 -> (650.88,920.16)/(799.92,920.16) (Fable form): eq OK, 0 overlaps, but 2 timing limits over (core link 429 > 412 um, station 884 > 864 um) -> not applied; t68 vn_a -> x 507.6: 1 station needs +1 register -> not applied; t75 ve_m/ve_s/vsw/vs +43.2 or +129.6 um: every seeded core lands on fixed ft-slot station sites (core_place rule7, 26 points), so the move needs the ft stations re-sited in the same event (core_place keeps ft_slots fixed). face-clear S 86.4 on t68 ve_m/ve_s: no timing-clean spot. - t68 WORKS with search: seed ln_12/ln_13 = Fable form + core_place search (sweeps 6, big cores --fixed "u_ve|u_vsw|u_vs$|u_vn|u_rxs|u_vq", gap 4.32): applied True, eq OK, 0 timing violations, 605 -> 605 station regs, R-LEAF-3 slots 30 -> 21 (vn_a|ln_12, vn_a|ln_13, vn_a|vp_b0 gone: the GRT-proven class), RUDY ovf H 1.62M -> 0.78M; 10 vp cores moved (lane swaps). Plan cp/t68_f.json (type t68 only). Blocker before it can join B4L: 2 reset relay sites (981.9,151.2) and (1120.1,419.0) now sit under ln_0 / ln_8 (core_place does not see collector relays): needs the collector publish / re-site step of the DIE-S81-92 chain for t68.
=> R-LEAF-2/3 need an ft-station re-site step (or street_rule legalize with stations) + per-form templates; next step for this lane or a successor.
