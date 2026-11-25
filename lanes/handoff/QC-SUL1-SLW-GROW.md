# QC-SUL1-SLW-GROW lane memory (child of QC-SUL1-SLW-REFLOOR, parent QC-ALLFIX)

Task (QC-ALLFIX ruling 08:4x-2): slw_su_l1 +86.4 um x growth as a die-level row SUL1-SLW-GROW, separate from SUL1-SLW-CHAN (27e842fb253f).
Base C1o v13 aa3a14fb7484 / sidecar a142fe516f24 (epyc10 launch_c1o_bind). Work dir epyc10 /srv/opentallas-scratch2/claude/QC-SUL1-SLW-GROW.

## Design (11-25 09:0x)
- W quads only (W5..W0, 6 x 86.4): die W 31216.32 -> 31734.72. E quads + W strip rigid (E shifts +518.4).
- su/fw/ctl/hc rows: column-0 types (slw_su_l1 x2, slw_fw x4, slw_st_a x4, slw_hc0 x2; all W-only) widen +86.4 at E;
  frame stretch phi x[432,622.08]->[432,708.48] (same phi in all four, N/S seams between them stay aligned).
  su_l1 S face and hc0 N face (abut cb-left, unmoved) keep their windows/face pins.
- cb rows: slab at local 1235.52 (cb-left|cb-right), DX gap -> die.channels rows (_01 rows carry a00/nb_i12 across; _00 voids).
- NS fixups: su_c cws1 -> bn_00 bc_i10, hc1 cw_n1 -> tn_00 bc_i10: cb-left bc_i10 landing +86.4 in type frame.
  cbn_q00__cl622f65d2 shared with E0 -> W clone cbn_q00__cl622f65d2__gx86 (11 inst); cbn_q00__cld7bf7197 in place.
- Script grow_x.py (generic: also run on SLW-CHAN 27e842fb253f, HC0-GROW v4/v5, PHY 98201d985d5a for cross-check).
- Host note: die-priority ot-run on epyc10 blocked by DIE-RESERVE disk (645 GB reserved); small jobs run normal priority.

## Status 11-25 09:55 PST: DEFERRED (not ROW-READY)
- v2 row (grow_x.py v2: rigid N/S windows, rigid core groups snapped to 0.216, kept cb-face landing core+band stay, abs paths):
  plan 4e86eee925d8 / sidecar d44c5978d6f2 (out2/). Die 31734.72 x 25643.52 (<33 mm). 377 partitions, 0 overlaps, 0 out of die, 0 hard-core overlaps.
- Cross-check (xcheck2.out): on SLW-CHAN 27e842fb253f, HC0 v4 5c1355002614, HC0 v5 cac71017fb46 (die H 25989.12) and PHY 98201d985d5a: 0 overlaps everywhere, 6 misaligned (0.033->0.048 um) same as standalone.
- RR checks (outrr2, sha 94df3fde0c78: RR imports mutate plan before dump, fix = dump first): lane hops new none, landing over none (worst 340), station-in-core new none, content_outside none.
- Worst hop: START edge 432.8 (49 edges newly >405, base worst 399.6); fw_v1 sc_wo 1286.2->1367 (already over at base).
- CA model (region_form, ca.out): fail 0, margins 107.1/112.4 unchanged, but 1758 CA rows + feed parent (sl_E0_fw->sl_E1_fw) differ from the plan tables: regenerate.
- guard: GUARD_RC 0. PRE (v1 plan, absbins): FAIL 25 findings: TAPNAME x7 + TAPNAME-RETAP, TAPOFF-MISSING x5, SITEGRID x5 (st_a bank sites off grid), DERIVEDNAME x2, LANDREMAP x3, RSTREACH x2 (su_l1 local resets up to 1047 um). PRE v2 (pre2.out) was running at 09:55.
- Fable v1 and v2 (scratchpad fable_review*.txt): (a) geometry ADOPT-WITH-FIXES, (b) bindable row FAIL.
- Blockers: per-type retap + tap_offset_cover + reset-tree re-anchor/landing_remap on 14 widened types; snap st_a bank sites to the site grid; START relay re-plan (clean provider); seam stations / hop check for 48 gap ports + 24 _00 ports; st_a_v2 x_fw_ctl landing group; regenerate CA/feed/taps; RR sha = row sha.
- ETA 11-25 15:30 PST for a v3 rerun of guard+PRE+Fable.
