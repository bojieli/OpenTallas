# FAM-QC-FEFW handoff (Sonnet 5.5, 2026-11-21 ~02:00 PST). Family: QC sle_fe*/slw_fe*/sle_fw*/slw_fw*. STOOD DOWN after census; successor needed.
NOTHING IS BUILT: no private bind, kit, GRT, sign-off or export exists for this family from this lane.

## Census (ROUTE-REACH-0020 + OWNERS-SWEEP 00:50): 13 unsigned current-plan types, all owner QC-PLAN-R8 (family), all furthest=place on current plan
sle_fe_v1__cl8210183c (192 att., sweep: running route), sle_fw_v1__cl9d029624 / clf58b4dfb (running route), sle_fw_v2__cl6740750e (running route),
sle_fw_v2__cl69f5e854 (cancelled superseded), slw_fe_v1__cl95cd1d0c (134 att., routed once, running route), slw_fe_v1__clfe325744__cldb4efe33 (place),
slw_fe_v2__clf110fab2 (running route), slw_fw_v1__clf51c11d8__cl592e3d37 (333 att., place), slw_fw_v2__cl8537f156, slw_fw_v2__cl8f84514c, slw_fw_v3 (running route).
## Findings (static, MEASURED on epyc9 with tools of fable-fix-qc-sle/clone; outputs epyc9 /srv/opentallas-scratch2/claude/fam-qc-fefw/{sc_v1.out,sc_v2b.out,pp_v1/place_precheck.tsv})
1. The sle_ctl core-slit station class (lever 3) does NOT show on fe/fw statically: station_core on V1 (qc103 s4q9n46r4 final preview) and V2b (v2b/c4/p_final.json)
   = 0 rows with station sites in / routes over a hard macro for (sle|slw)_f[ew]. So per-bit relay_sites (FABLE-FIX-QC-SLE-R3) has nothing to move on fe/fw. Do not copy it.
2. V1 KNEE (place_precheck, plan-decidable, matches PLACE-PRECHECK-2330): +1 station needed on
   sle_fe_v1__cl1cbb7497 arv_wi 584.9 um, arm_wi 506.5 um (1 -> 2 stations); sle_fe_v1__cl8210183c arv_wi 578.7, arm_wi 501.9 (1 -> 2);
   slw_fe_v2__cle312294d arv_ei 559.3 (1 -> 2); sle_fe_v2 x_fw_p2_i NEAR 399.4 (kit pins +-2 um). V2b has none of these. Rows for V1 relaunch go to QC-PLAN-R8.
3. Closest-to-signing fe kit: slw_fe_v1__clfe325744__cldb4efe33 (kw43 s29q103S4Q9N46C, epyc10, review 26c6b7661321): ROUTED, TT +51.9 ps, DRC 0, late ECO 1 it exhausted,
   FF hold core -60.89 -> -3.63 ps / 1 endpoint (3819 raw hold viol at sdc_min), "NOT SIGNED hold_ff". Hold paths: input port -> u_bin_x_stm_i flop (vclk ideal 199.9 vs clock 223 + 12.5 unc).
   Next lever: second ECO pass / shared-tap hold fix on those u_bin_* input flops, not a plan change. Sibling attempts of same type died FAIL_POSTCTS ft hop 2.06 / 2.17 mm
   (u_ft_x_su_l0_ctl_o / x_fw_ctl_p2_o, infra-oom) - a 2 mm pin-to-pin ft crossing.
4. slw_fe_v1 GRT overflow 50-56k, 99.5% vertical (FABLE-FIX-QC strategy lever 3) is NOT explained by station-in-core; diagnose from 5_1_grt congestion reports of the kit (ft channels / ft_spread).

## Next steps for successor
a. Pick representative slw_fe_v1__clfe325744__cldb4efe33 (routed, hold -3.6 ps): copy kit (git-archive tree), rerun hold ECO / tap balance; read CTS post-hook only.
b. Hand knee rows (item 2) to QC-PLAN-R8 if V1 relaunch is wanted; V2b is clean.
c. Check the 3 cancelled/infra-oom FAIL_POSTCTS ft-hop 2 km? (2.06-2.17 mm) rows for ft_spread cause.
