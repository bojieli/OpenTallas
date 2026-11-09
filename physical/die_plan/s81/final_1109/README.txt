S81 ONE FINAL SWITCH (TYPE-SAFE-5 11-09, COORD 02:33 / GO 05:0x). DO_NOT_COUNT until signed off.
plan_h2_2249_final_65648816.json.gz : the final S81 plan (sha256 prefix 65648816b02d5057, gunzip -> physical/die_plan/s81/plan_h2_2249.json)
  = c72370 (romq-split base 188e646 + relay event: 48 types, 269 buses, 415 lanes, +1695 pin cycles)
  + leaf early-core-tap/macro-move event on 72 leaf types (OT_MACRO_MOVES folded into the plan; t7/t8/t17 stay kit-local)
  + tap-radius fixes: col_h10_r0_p4__t1 clk_t29, col_h10_r2__t1 x4 clk_t26/t27, 6 leaf types one added tap each.
asbuilt_b178_coll_h2_2249_final.json : bind manifest (romq split RTL + plan kits under romq/).
bind6/ : strict bind summary (n_errors 0, 398 partitions, 873 crossings, 606281 bits).
xs_asb_schedule/ : S81-PLAN-1 --bound-plan frame schedules -> OT_XS_ASB_SCHEDULE_DIR for token builds.
SWITCH.tsv : per-item switch actions vs the wave plan ba6292b0c502.
