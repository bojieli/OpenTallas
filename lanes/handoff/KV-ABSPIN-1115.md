# KV-ABSPIN-1115 handoff (2026-11-15 ~19:0x PST)

Lane: KV abstract pin-wire scan (COORD r176 lever 7), plan kvgeom7u (plan_c b7156937f334).
Work dir (all 6 gen hosts: epyc2 epyc7 epyc8 epyc9 epyc10 intel1): /srv/opentallas-scratch2/claude/kv-abspin/
 tools/ (scan2.py grid-indexed scan, abstract_detail_cap.py capped pinwire, mkproof.py/proof.tcl/capread.tcl/capsum.py one-macro harness), views/ (new views), proof/ (route logs; epyc2 + epyc10 ex_plan).

## RESULT in one line
In the 13 plan-of-record KV hard-core LEFs (+ 7q ahub/kvs_ctl) pinwire finds 0 pins to move: no signal pin has its own same-layer wire in OBS; every signal pin (M4/M5) lies inside the BLANKET OBS of its own layer (M1-M5 + RVT). The cap-0 pin rows are that blanket, not a pin wire. No new view is needed for kvgeom7u; none is offered.

## Step 1 table (scan2.py, signal pins / pinwire pins / pins fully inside own-layer blanket OBS)
git view (physical/die_plan/qwen_kvsys/...) -> pins, pinwire, under-blanket
 kv3_head_eighth_e0 hgclk_1030 (sha 8169f9f4bf43) 1802 / 0 / 1802
 kv3_head_eighth_e1 hgclk_1030 (1fdc38bec2ff)      546 / 0 / 546
 kv3_head_eighth_e2 plan_of_record/views_e2s (04a8f2f4c0a8, 18 types) 1358 / 0 / 1358; hgclk_1030 e2 (b292451f782e, 1 type) same
 kv3_head_eighth_e5 (a41e22f7b6be) 546 / 0 / 546;  e6 (b532bf846d2d) 1358 / 0 / 1358
 kv3_pv_pair pvview_1103 (25ada09fdd3b) 1668 / 0 / 1668;  ot_qwen_tp8_pv_join_t pvview_1103 (dd2dfba96f19) 4621 / 0 / 4621
 qkd_astk_ex_s ref_tile/qkd_astk_ex_s_hg1101 (d967f9d5abfb) 102 / 0 / 102
 qkd_ectlk_q0..q3 hgclk_1030 (9ab7a65fbadd, 4f96..., e1719b2034c6 or 49d7.., 4590f59fc3bd) 1478/1968/1957/1990, all 0 / all under blanket
 7q views (epyc7 kv-102/kvgeom7/views7q): qkd_ahub f357274f6d49 631 / 0 / 631; qkd_kvs_ctl a2df4fbd0f84 7076 / 0 / 7076
 qkd_kvs_pcc / pcf / *_h_head_p (all 11 variants found): merge_pin_wires merged_rects 0.
 NOT FOUND as LEF on any host: qkd_hr_cdc_hi, qkd_hr_core_peer; qkd_hr_core_rx 02aefcb4bee0 merged 0.
Detail-form variants (pins have wires in OBS) exist for other masters: qkd_hr_* (ref_tile main + provenance/raw), qkd_astk_ex_s ref_tile detail (09c1d276efea, 3cf81fcfcfe9), ot_qwen_tp8_pv_join_t ref_tile qkd_pv_join*, kv3_pv_pair variants-1 kv3_pv_v8 (ded640208bb1), qkd_hr_core_prompt (2028c943eddb lef_overrides, c780630b88af kit-ops-6). The kvgeom7u plan row has no lef path for qkd_hr_* (kit resolves it); which sha a kit uses is for KV-102/KIT-OPS-5 to confirm.

## Finding: plain pinwire is UNSAFE on the detail forms
abstract_detail.py pinwire merges the whole touching OBS cluster into the first pin it reaches. On the detail views one cluster touches thousands of pins (qkd_astk_ex_s detail: all 102 pins touch one 11,784-rect M4 cluster; ot_qwen_tp8_pv_join_t: 4,620 of 4,621 pins; qkd_hr_core_order: 24,965 rects into 2 pins). So one pin (ck, clk, chain_f...) gets other nets' metal. MEASURED: qkd_astk_ex_s detail -> pinwire view, one-macro DRT stayed in "Start pin access" 55 min at 1 core and was killed (baseline detail view: 282 Lef58EolKeepOut M5 + 45 Lef58SpacingEndOfLine + 45 Lef58CutSpacingTable, DRT finishes). Uncapped views were deleted again.
Capped variant (abstract_detail_cap.py: a pin whose cluster exceeds 200 rects is left alone, receipts list the skipped pins) -> views/<master>_pwc_<sha8>/ with pinwire_receipt.json, new files, libs copied, on all 6 hosts:
 kv3_pv_pair_pwc_ded64020  base ded640208bb1 -> bf54a8bd4b3d (5889 rects, 1661 pins, 3 skipped)
 qkd_hr_core_prompt_pwc_2028c943 base 2028c943eddb -> d1fbdafed383 (1936 rects, 640 pins)
 qkd_hr_core_guard_pwc_27ec9f75 / 292cf997 / 43677f24 / d765f02f -> d0e73301d6b6 / d56af216452b / 700c24acf5cd / 044f1d763e05 (3-4 rects)
 ot_qwen_tp8_pv_join_t_pwc_8dc31fe2 -> b0379f38671d (1 rect); qkd_hr_cdc_pc_pwc_5001ab91 -> ed98e4fef926 (1 rect)
 no-change after cap (no new view): astk_ex_s detail x2, join_t x3 other, cdc_pc d1776ee3, order x2, queue x2, tx x2, prompt c780630b.
These are not kvgeom7u views (none of them is the plan LEF); read_lef OK on 3 of them (pin counts unchanged). Effect on route NOT proven (only 1-2 pins to a few hundred pins change).

## Step 3 proof, kv3_head_eighth_e2 plan view 04a8f2f4c0a8 (harness: macro + one BUFx2 2-4 um outside each of 1351 edge pins, 2-pin nets, M2-M8, tracks of the kit make_tracks.tcl, openroad asap7lock-grtT3)
 pinwire output is byte-identical (0 merged) so before = after.
 GRT 0 overflow, DRT: 10 violations, all M1 Short/Metal Spacing between harness buffers, 0 Lef58EolKeepOut, 0 on M4-M7 or at a macro pin; no DRT-0073.
 GRT capacity readout (free tracks = dbGCellGrid capacity - usage on an empty route; gcell 0.57 um; 1351 pin gcells): zero free M3 619, M4 623, M5 623, M8 534, M2 4; mean free M4 4.3, M5 3.1, M6 6.3, M7 8.4. One gcell inward: M2-M5 zero in all 1351, M6 534, M7 74, M8 677. 619 of 881 M5 pins sit in a gcell with 0 free M5.
 Cause: blanket OBS over M1-M5 (design), plus M6/M7 detailed OBS. Same numbers class for every head_eighth view (all pins under blanket).
 EXPERIMENT, not adoptable: M4/M5 blanket cut back 1.0 um at all edges (LEF in proof/e2s_win1_*): zero-free M4/M5 623 -> 0, mean free M4 8.8, M5 11.1; route same (10 buffer violations). The metal under the cut is not modeled, so the parent could short real core metal; adoptable only through abstract_detail.py splice --pin-window-um with the exact detailed export (-bloat_factor 0) of the signed e* ODBs: needs those ODBs (not found on the fleet).
 qkd_astk_ex_s plan view d967f9d5abfb (ex_plan, epyc10): GRT 0, DRT 0 violations.

## Open
- KV-102: no view swap needed for kvgeom7u from this lane. The hg/hgi cap-0 overflow inside head cores is blanket-OBS geometry; levers are the window with exact ODB export (above) or a router-side exemption, not pinwire.
- pwc views: only if a KV kit actually uses one of the listed detail shas.
