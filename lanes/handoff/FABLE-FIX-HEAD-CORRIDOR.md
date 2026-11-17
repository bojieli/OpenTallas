# FABLE-FIX-HEAD-CORRIDOR handoff (Fable), 2026-11-17 08:57-14:1x PST -- to HEAD-PLAN-R4, COORD. Lane RETIRED on COORD's instruction.
s81_head hd_lep0N NF15f relay corridor. Work dir: epyc9 /srv/opentallas-scratch2/claude/fable-fix-head-corridor (F). Nothing written under head-die-r.
Evidence on the hub: lanes/evidence/fable_fix_head_corridor_1117/.

## Status: NOT READY. Cut, reach, vertical access, keepout and the plan gates pass; 367 nets are still unassigned. No branch.

## 1. Root cause (settled, COORD 13:xx)
hr4/edges_g1.py maps a model stage to the composed plan by group PREFIX. The NF15f chains are renumbered (PIN 4->6, POUT 4->8,
KRX 1330->2660, TXI 1221->2442), so model g_s[k] landed on plan g_s[k], a relay rect. Fix = map by TAG: F/edges_g3.py (104/104 rects).
Same plan (rs7 10e41a91), alloc_r4 unchanged:
| map | unassigned | reach-bad | worst full-rect cut | mandatory |
| prefix (edges_g1) | 3,244 | 8,345 | 1.297 at x=1180 | 0.826 |
| tag (edges_g3) | 4,295 | 0 | 0.903 at x=1180 (9,973 / 11,046) | 0.502 |
No corridor capacity limit; krx3_r0 is inside 405 um (no 4th KRX stage). Growth +60 / +120 and M8-all were measured on the old map
only (0.98 / 0.83 / 0.95 cut, reach-bad 3,309 each) and are not needed.

## 2. Candidate c3 (stage rects only; 54 tags change vs rs7)
- 26 base groups legalised (place_anchors2 step 2), 27 relay ranks (all *_r<k> and rxh_l<k>; rxh_ctl stays) as bit-slice columns
  10.8 um wide, 61-217 um tall, FF on its bit's trunk. Tool F/place_cols.py; rows ev stage_rect_rows_c3.tsv; apply with
  apply_stage_rects.py CAND TARGET OUT REPORT (by prefix + tag; KCRED ignored).
- Candidate plan F/c3/plan.json sha 24914810 (on g1e). Applied to rs7: F/prep_fc4/source_plan.json sha 65606a72.
- Check (alloc_r5 --columns, cut step 2 um; vert_access.py unchanged), F/c3/witness_b.json, access_b.json, receipt_c3.json:
  59,089 nets, reach-bad 0, worst full-rect cut 0.801 at x=988 (8,709 / 10,871), mandatory 0.598, stage-vs-macro 0,
  stage-on-reserved-site 0, column vs group overlap 0, vertical ratio 0 at every column, D-to-Q jog ratio <= 0.176, FF site
  ratio <= 1.0 (capped at the 0.55 target). UNASSIGNED 367: 176 Q nets of txi0_r0 / txi2_r0, 109 MU replay capture to RID,
  42 KRX to RX DQ, 40 Q nets of pin_r4. vert_access lists pin_r4 / txi0_r0 / txi2_r0 only because of those nets.
- Gates on 65606a72 (run fc4, rs7 recipe, code_rs6 tools): compose / receipt / kit RTL / bind PASS / cohort 26/26 /
  LATCHECK 329/329 / G0 0 errors, 220 warnings. F/gates_fc4.
- Hybrid c4 (txi0_r0, txi2_r0 kept compact): the TXI nets close, but 580 unassigned overall (230 MU replay, 145 KRX to RX DQ,
  135 pin_r4, 70 RX write). Not better; c3 is the hand-over.

## 3. What is left (owner of the next step: HEAD-PLAN-R4)
All residue sits in x 880-1160 (and pin_r4 Q nets x 1230-1472, y 682-804), where the witness uses 0.77-0.80 of the rows and M4 is
blocked over the SRAMs, so a 90-240 um net finds no free row and one-level rip-up cannot move the tied D/Q pairs. Not tried:
(a) columns for the s-ranks too (krx*_s*, txi*_s*, pin_s*, pout_s*): their 50-108 um wide rects are what lifts full-rect use to
    8,700 against 3,700-6,200 mandatory there; (b) moving mrd_bank / rid / rxbank groups out of x 905-1075;
(c) pin_r4 column further west (its hop is 430 um far edge to far edge, window 122 um); (d) a two-level rip-up in alloc_r5.

## 4. Caveats
- alloc_r5 = alloc_r4 + column mode + joint D|FF|Q track + rip-up repair. It is my extension, not reviewed by anyone else; with
  --repair 0 and no --columns it follows alloc_r4's path, but I did not run that regression.
- The column model assumes the placer puts each FF on its trunk row; the plan only gives the tall rect (no per-bit rows).
- Clock: 27 tall sink columns change the hd_lep0N sink census; no clock GEN was run.
- pc1 (rs5 base) bind FAIL and pc2 compose FAIL were harness (symlinked tools root; a kw45 asset file gone), not design.
- The unbounded repair pass ran > 1 h; I stopped my two allocator processes by PID and bounded it (--repair-rows 80).
- Scratch to remove when HEAD-PLAN-R4 has taken the rows: F/prep_pc1, prep_pc2, prep_fc3, prep_fc4, code, code6 (~1.6 GB), via ot-delete.
