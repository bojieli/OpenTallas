# MU-DIE-S81 GEN mu2 (10-19): S81 multi-user release die, strict bind

- Branch claude/mu-die-s81-mu2-1019: base claude/refill-mus81reg-1019 0e5fff3f9 (mu1 1d43f2c12 + MU-S81-2 ac336f805: closed dsdv_mu_hslot source,
  new dsdv_mu_hwin, s_0S copy-B + RX ddc529908; combined regression all legs as expected) + mu1 record a218435f6 + PO2 1768871c1 (po2 landing views
  276/276l/70 with landing_reset_stages 2, strict landing reset check) + PATH 11438a2e7 (dv_plan --pathfix).
- Plan p4l_lkcol_mu_pf = dv_plan --layout p4 --p4l --tier-w 276 --lanes 4 --p4h-drop 6 --frame-w 1436.832 --lk-slots p4l_lkcol/plan.json --mu 1 --pathfix
  (lane band over blocks 9,741 -> 32 bit-mm; without --pathfix the output is p4l_lkcol_mu byte for byte).
- DIE_PORT_BIND PASS 41 masters / 9,001 inst, every counter 0 incl. landing_reset_mismatch / unresolved; frame_contract PASS.
- Real-view case mu2: 8,523 closed / 182 stand-ins, PILOT_NOT_A_GATE (fclk non-fatal). Chain on ot-epyc7 (unit oth-ubuntu-2329132-1792417844).
- Not in mu2: copy-B MAB variant (separate chain case_mab; port of its 2x276 bundles + rt_0S onto ac336f805 owed), index reader (COORD), MU lane landing K rows,
  lep MU RX closed views (gates running, MU-S81-2), s_7N host endpoint lep_mu_h (gate running).
