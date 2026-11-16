# FABLE-FIX-HEAD-TIMING handoff (owner of the open HEAD types; started 11-16 05:50 PST, last update 07:40 PST)
Lanes under this owner: HEAD-TYPES-O (hd_host_e/w, hd_ctl, hd_st_k5, hd_st_n3_turn, hd_spn_end), HEAD-SERDES-O (hd_serdes). I launched no builds.
Lane dir: epyc2 /srv/opentallas-scratch2/claude/fable-fix-head-timing/ab_epc (A/B reports); logs intel2 ~/fht-logs; scripts localhost scratchpad fht/.

## State per type (07:40)
- hd_st_k5: k5b SIGNED (TT +75.35, DRC 0, FF non-port PASS, LEC exit 0). EXPORTED by me 07:1x: s81_head/hd_st_k5__k5b_nf13b, ARCHIVED-BOTH,
  odb sha 1907a1dbc34c. Counts when HEAD-100 adopts NF13b (re-gate on src_head_pin_eb1e73448bd0 first; F1 closed 02:48).
- hd_serdes: sd5 numbers are NOT a decision (kit lacked the wave item_env). sd6 (full env) reads CTS TT -26.55, GRT done, route next.
  My 06:5x DIRECTION (site delta, sd7 now) is WITHDRAWN to reserve by my 07:4x post; sd6 GRT/route read decides.
  Facts that do not depend on the kit env: u_chn outputs (cw_q 544, apply 8) on its top edge y 386.0 under the VDDPHY floor 400;
  u_cmem/bsrc on the far side of u_dmem; u_chn lib max_clock_tree_path 315.1 ps, not led on pma_rck in sd5.
  Reserve rows if sd6 routed TT < -42 with the worst class from u_chn/clk: u_chn MY -> R180, u_dmem R0 -> MY, u_cmem to the
  u_chn output edge. Probe scripts: epyc10 fable-fix-head-serdes/diag5/fht_geo.tcl, fht_io.tcl (run on any stage DB via env ODB).
- hd_host_e: no ECO rounds (he3 -116.51 / DRC 27, he4 -66.93 / DRC 29: no gain). Structural forms in flight (HEAD-TYPES-O, epyc2):
  he5 = skid + isl_sd free-load RTL (GRT TT -109.48 -> -44.86, in detail route); he6 = he5 + u_epc PDN bottom halo 1.08 um.
  DRC class: 26 Lef58EolKeepOut M7 at the top end of 13 u_epc bottom-edge pins (y 60.672) + 3 Metal Spacing to VDD/VSS at y 60.38.
  My A/B on he4 5_route.odb (drt::check_drc, master edited in the DB): OBS merged into the pin (1 level / flood) and OBS trimmed
  0.261 um from the pin: the 26 markers stay (trim) or move to the new pin end (merge). So macro OBS touching the pin is NOT the
  cause; what is left is the die-phase M7 stripe ends below the macro = the he6 halo test. Do not land a LEF OBS trim.
- hd_host_w: hw3 routed DRC 0, TT -80.84 (BUFx2 on 64 loads), FF -34.19; eco_hw3 first round running (epyc10). One round only.
- hd_ctl: wave a2 (NF13a) was in route; DRT-0206 on route-keep ECO is with the new M7 scalar pin lane (track-truth refuted).
- hd_st_n3_turn, hd_spn_end: DRC 3 Rect Only on interior M7 rst_start_raw pins; row asked from HEAD-100 (M8 or track-width pins).

## Next
1. sd6 route + sign-off read -> either RESULT PASS naming head-serdes-fanout (releases HOLDGEN) or the reserve site rows.
2. he5/he6 sign-off: he6 DRC 0 -> gen_phys/pdn row (M7 halo under macros with M7 edge pins) + merge request for the skid RTL
   (branch claude/fable-fix-head-types-1115 @463b9396539 + free-load commit, bench + LATCHECK).
3. eco_hw3 result; if < -42: fan-out cap on the 64-load net (RTL or OT_PLACE_MAX_FANOUT 32), full build.
4. NF13b adopt on the v2 tree -> k5 + st_turn count; export each signed record with scratchpad ffht_export.sh.
