# MU-DIE-S81 GEN mu1 (10-19): S81 multi-user release die, strict bind

- Branch claude/mu-die-s81-1019 @1d43f2c12; plan results/arch/s81_dv_1016/p4l_mu_lkcol/plan.json (p4l_mu + SerDes column rev2 slots);
  bind table bind/bind_table_p4l3_mu.json; land plan landing/p4l3/land_plan.json (MU lanes: K 1 default).
- dv_diecase --bind real: DIE_PORT_BIND PASS, 41 masters / 8,948 instances, every counter 0; frame_contract PASS; reset reach PASS (3,296 sinks).
- Real-view case case_mu1 (rv_case_mu1.json): 8,470 closed / 182 stand-ins; label PILOT_NOT_A_GATE (fclk audit non-fatal, counted).
  Chain running on ot-epyc8 (unit oth-ubuntu-724034-1792409869): repeaters -> GRT -> STA TT/FF/SS -> die_clock_check.
- Not yet in this GEN: index reader dsdv_idx_rg (no slot, COORD), copy-B (mab) variant, po2 landing views, MU lane landing K.
