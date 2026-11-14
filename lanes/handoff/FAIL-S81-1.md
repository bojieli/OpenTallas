# FAIL-S81-1 handoff
- 2026-11-13 23:09 PST FAIL-S81-1 STATE pass 1 (S81 KIT-WAVE FAIL since 11-13 15:00, AUTO-GEOM ignored; 56 lines):
  | class | n | cause | fix | owner |
  | reset_tree.pin_root_copies @kit_rtl | 39 | train-L overlay | already fixed 22:3x | KIT-OPS-3 (known) |
  | docker rc125 @gen_lint + CRASH flow-error asap7lock not found (ot_s81sl_leaf t33/t44) | 11+2 | epyc7 (loved-redfish) had ZERO docker images: openroad/orfs:asap7lock missing | docker save|load from epyc8 of asap7lock, latest, grtT1/T2/T3/grtoff on epyc7 at 2026-11-13 23:09 PST (rule 8, no delete) | FAIL-S81-1 done |
  | kit-rtl no partition type col_h9_r0_p* | 5 | stale r0 names (known) | none | - |
  | clock-landing band, 1 | 1 | single, below threshold | - | - |
  Note to KIT-OPS-3: epyc7 had no images; the 11 col_h9_r2 gen_lint rc125 and 2 leaf CRASH items are unchanged-input failures that now should pass on relaunch (inputs changed = host fixed). Check other newly provisioned hosts (epyc10) for images. No near-miss ECO candidates this pass.
- 2026-11-13 23:09 PST FAIL-S81-1: per COORD checked epyc10, intel1, epyc8, epyc9 docker images: all have the 6 orfs images (asap7lock, latest, grtT1/T2/T3/grtoff). No gaps; epyc7 was the only one (fixed). Next pass in ~75 min.
