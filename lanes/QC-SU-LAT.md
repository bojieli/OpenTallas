# Lane QC-SU-LAT -- QC SU hard cores to ONE common clock latency (owner 2026-10-26 ~06:1x)
Parallel to EARLY-TAP (claude/qc-early-tap-1026, INFRA-FIRST/QC). Whichever reaches related-pair <=80 TT/FF first is used.
Branch claude/qc-su-lat-1026 (WT epyc1:/srv/opentallas-scratch2/claude/wt/qc-su-lat-1026). Data: {intel1,intel2,epyc1}:/srv/opentallas-scratch2/claude/qc-su-lat/

## 2026-10-26 05:45 PDT QC-SU-LAT: (1) INVENTORY -- every QC core with a core-offset tap (plan origin/main adb6c7adc die_plan.json)
72 offset taps = 12 su_c partitions (6 slw_su_c x 7 + 6 sle_su_c x 5). All other QC cores (A0 nk/nl, su_lane_w x96, su8_rst3, sle crh, coll face, UCIe) are declared 250.
Measured TODAY (QC-SU-LAT probe, GRT RC re-estimated from each kit's 5_1_grt.odb, all clock sinks; routed RCX runs ~5% lower, e.g. vmr 386.5 routed):
| core (inst/plan offset)          | kit                          | sinks | TT min/mean/max  | FF min/mean/max  | clock stages |
| qfd_dv_s8x_vmr (va/vb/vc, +136)   | intel1 codex-qc-sramif-1309/vmr_s6kc     | 4308 | 388.7/409.9/438.0 | 301.6/317.9/346.3 | 13-17 |
| qfd_dv_s8_crh_rp1 (slw cl/ch, +99)| epyc1 codex-qc-sramif-1309/rp1_f62 SIGNED | 2790 | 361.1/383.3/417.7 | 299.2/316.4/350.9 | 8-11 |
| qfd_dv_s8x_prog (pg, +231 plan)   | intel1 path-qc-sramif4/prog_fh16_s40 (route live, untouched) | 5291 | 525.7/568.1/616.2 | 397.3/446.4/497.8 | 17-22 |
| qfd_dv_s8x_btab (bt, +195 plan)   | intel2 path-qc-sramif4/btab_fh_s40 (route live, untouched)   | 5644 | 459.1/489.1/515.8 | 347.2/382.5/415.2 | 15-19 |
ROOT CAUSE (stage probes, qc-su-lat/{rp1,vmr,prog}/stage_TT.log): NOT macro latency, NOT distance (cores are 259-354 um). The insertion is STRUCTURE:
- MSCTS (vmr/prog/btab): equal-stage trunk with 45-60 um segments = 5-7 BUFx8 stages (~25 ps each) on EVERY tap path, even taps 4 um from the root (vmr SW/SEa); then BUFx4 pad chains balancing the taps to the slowest branch (vmr 1-4 pads, prog up to 11 = ~250 ps); then tap + 3-level local tree (~100 ps).
- prog: the 4 band trunks leave the S-face root (177,6) WEST to x=66, then north, then a 220-um leg EAST to the E sinks -> R*E taps 394-434 vs S taps 233-244 at CTS (window 201 ps); everything is padded up to R3E.
- rp1 (TritonCTS + core_taps): 9 BUFx24/16f stages, trunk doubles back (x 74->124->89->48) and one 120-um unrepeated leg (+42 ps).
Floor estimate: farthest sink <=430 um manhattan from the S-face ck pin; repeated M4/M5 ~0.3 ps/um -> ~130 ps + root 20 + tap/2-3-level local ~90 = ~240 ps TT. 250 TT is physically reachable in all four.

## 2026-10-26 05:45 PDT QC-SU-LAT: (2) COMMON TARGET (proposed, INFRA-FIRST please confirm)
Core boundary-flop insertion at the core ck pin = 250 ps TT / 202.5 ps FF (measured FF/TT 0.78-0.83 on these trees), tap-mean window <=20 ps, pin-reg spread inside the 80-ps related-pair budget. Same number as A0 (250 +/- 40) and the plan's clock.insertion_ps 250. Deep cores restructure to come in <=250 and pad up to it; shallow cores pad up (they already do via OT_TAP_TARGET_PS 250). When all 72 taps are 250, the die drops core_taps "early" and the 99/136/195/231 offsets.
Islands (COORD corrections 1+2): in-core INFRA islands are top-owned holes with an M9->M1 via stack for die clock/reset drivers ONLY; signal FT stations/repeaters stay pushed down in <=405-um bays, added in a core only where the INFRA-FIRST sufficiency gate shows a reach gap that leftover M8/M9 cannot fix. None of the 4 cores requests a bay now; island sites over su_c come from INFRA-FIRST (A0 channel cross + bay positions) -- no core change until INFRA-FIRST names a site inside one of these outlines.

## 2026-10-26 05:45 PDT QC-SU-LAT: (3) TRIALS (CTS + GRT only on the retained GEOM-reviewed 3_place; no route, no sign-off claim)
Variant A (all MSCTS cores): OT_MSCTS_SEG_UM 110, LEG_SEG_UM 120, TRUNK_CELL BUFx16f (trunk 5-7 -> 3 stages). Spec/pins/placement unchanged.
- vmr_A  intel1 qc-su-lat/vmr_A  ot-run oth-ubuntu-2896887-1793018660
- prog_A intel1 qc-su-lat/prog_A ot-run oth-ubuntu-2896883-1793018660
- btab_A intel2 qc-su-lat/btab_A ot-run oth-ubuntu-1825007-1793018660
Variant B (next, per core, after A numbers): topology fix -- prog/btab bands fed from the near channel (E sinks from an E trunk, not the W detour), taps split to <=~500 sinks (2-level local tree), rp1 ported to MSCTS (it has no structured trunk).
