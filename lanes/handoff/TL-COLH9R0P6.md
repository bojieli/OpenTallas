# TL-COLH9R0P6 (s81 col_h9_r0_p6__t1) 11-14 04:45
- Base item fails: attempt19 kit_rtl "no partition type col_h9_r0_p6__t1 in the plan" (plan_h2_2249 renamed it to pv* variants; base row is dead, ignore).
- 12 pv variants (plan 4b7f1e0874) relaunched 04:15; earlier a1/a2 failed by infra only: run_kit.sh not in ot-store on epyc2 (KW_PLACE_RC=99), bind_report.json missing under s87bind/out_r11p2, plus plan-supersede cancels. Place itself runs ~2 min and passes (pvea45abf3 a2 RC=0). Geom auto FAIL (fill .011, empty .946, r2r 1180) is advisory.
- Now a3: stages gen..kit_rtl. Waiting; no change made yet.
- 08:20 route jobs all SIGTERMed 08:04; asked KIT-OPS-3 to resubmit; no sign-off yet.
- COORD 08:3x: kills were deliberate dedup; keeper pv082a7609 (epyc10). Follow it only; credit all 12 on pass; relaunch only the keeper if it dies.
