# TL-SERDEST14 (S81 serdes__t14) 2026-11-14 04:52 PST
Real cause: latest attempt (Codex wave b1a2125433d0, attempt_7, epyc4 -- host terminated, kit gone) FAILED at floorplan.tcl: OT_NATIVE_CELL_CAP actual std cells 460859 > 400000 run cap (tools/die_plan/native_cell_cap.tcl hard 400k). Earlier wave attempt_13 (11-13) failed PIN_AUDIT extra 1 on old src. Not a shared cause with serdes__t1 (that one is PHY/other); cell cap is shared with any serdes > 400k.
Fix already exists: LIMIT-BIND-1 overlay (lanes/overlays/LIMIT-BIND-1/apply.sh) turns the cap into ADVISORY (limit from cap_estimate/--native-cell-cap 517000 in type_args). Owner 11-14: cell cap removed.
Blocker: serdes__t14 is in hold_items (DIE-S81-87 ready11r HOLD, KW-FIX-45), not in only_items, wave config owned by KIT-OPS-3. No surviving kit dir found on fleet (no private rebuild source).
Forms requested of KIT-OPS-3: (A) release hold + only_items + retry serdes__t14@11 on wave src B3v with LIMIT-BIND-1 overlay; (B) same with item_env OT_GPL_SPARSE_UTIL=0.05 and GPL routability off (460k cells, rule 5); (C) if still >517k type_args cap raise/delete.
Next: after relaunch, drive to R-MINIMAL; add AUTO-RESIGN.tsv row on pass.
