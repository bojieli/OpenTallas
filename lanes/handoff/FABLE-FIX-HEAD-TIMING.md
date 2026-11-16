# FABLE-FIX-HEAD-TIMING handoff (owner of the open HEAD types; update 11-16 10:05 PST)
Lanes under this owner: HEAD-TYPES-O (hd_host_e/w), HEAD-SERDES-O (hd_serdes). Reads judged by r310: GRT-RC or routed TT >= -42.
My dirs: epyc2 /srv/opentallas-scratch2/claude/fable-fix-head-timing/{ab_epc,he9,he10}; logs intel2 ~/fht-logs; scripts localhost
scratchpad fht/ (snap.sh = one-line state of every build; lef_pin_obs_trim.py; pinobs.tcl / pintrim.tcl static A/B; p8.tcl path read).

## hd_host_e (my builds he9, he10; lane builds he7, he8)
- Timing cause: u_epc captures on the early clk_c0 tap. Lib setup per input family (TT lib): in_valid +93.5, out_ready_v +73..131,
  r_rx x53 down to -41 = TIGHT; in_data x552 -256..-340, f_rx -274..-342 = ~555 ps of budget, no pin-row site needed.
- he8 (lane) / he9 (mine, trim LEF): pin-row hook took all 557 flops incl. isl_od -> post-CTS -55.41 / -129.79, worst = u_ski SRAM
  rd_out -> 400 ps wire -> isl_od D. Both are only DRC tests of the abstract now (he7/he8 merge form, he9 trim form).
- he10 (mine, launched 09:55): he9 + OT_MPF_PIN_RE limits pin-row flops to in_valid|out_ready_v|r_rx|f_rx_v|ch_b. THE timing form.
- LEF: 26 Lef58EolKeepOut at 13 u_epc M7 pins. Static A/B on he4: merge moves markers to new pin tops; trim inconclusive statically.
  Rule: first of merge (he7/he8) / trim (he9/he10) with 0 EOL at u_epc pins wins; both fail -> M8 pin shapes for the 15 pins.
  Winner goes into the abstract writer + a --check preflight (lef_pin_obs_trim.py is ready, not committed).
- When one signs: export (scratchpad ffht_export.sh HOST ELDIR BASE SIGNOFF NOTE), merge request for skid + free-load RTL
  (branch claude/fable-fix-head-types-1115, HEAD-TYPES-O) and the hook/abstract as gen_phys rows.
## hd_serdes
- sd6 GRT-RC -112.45 (u_chn apply -> bsrc, 400 ps clk->q + 480 ps wire). sd7 = DOREG seam register + oreg_site.tcl (552 flops FIRM
  at the u_chn edge, one row, DPL spreads). Read: flop -> u_chn pin distance <= 15 um, GRT-RC TT. If the flop -> u_out leg fails:
  reserve site rows to HEAD-100 (u_chn MY -> R180, u_dmem R0 -> MY, u_cmem to the u_chn output edge).
## hd_host_w
- hw3 -80.84 (BUFx2 on 64 loads), ECO no gain. hw4 (9 registered cs-decode copies) post-CTS -11.93; GRT-RC read decides; hold -34 open.
## Others
- hd_st_k5 k5b SIGNED + exported (s81_head/hd_st_k5__k5b_nf13b); counts on NF13b adopt. hd_ctl + hd_lep0N wait for NF14 sideband rows
  (FABLE-DIE-HEAD / HEAD-100). hd_st_n3_turn, hd_spn_end: pg_pin_rule=true in NF14 (M7PIN-STRIPE-1116).

## UPDATE 11-16 13:50 PST (after Codex window; supersedes the he9/he10/sd7 lines above)
- hd_host_e: he10 (trim LEF) routed 0 EOL at u_epc pins -> trim form is the abstract fix; TT -125.19 (r_rx WEST pins, out_data -> l_data).
  Codex he11r/he12 = whole-bank layout on NF15 pins (CTS TT +64.24); he12 failed GRT (13 clock entries cap 0, kit lacked M8 grant).
  he12r (MINE, live 13:35): epyc2 fable-fix-head-timing/he12r = he12 static kit + generated M8 grant overlay (pdn.tcl 2112 M8 PG-track
  obstructions, m8_grant.json/py, budget.json, config MAX M8 + RA 0; gen recipe epyc10 fable-fix-head-timing/run_gen_he12r.sh),
  synth reused (resume.json start floorplan), route goal + chained sign-off. Log intel2 ~/fht-logs/he12r.log.
- hd_serdes: sd8 (Codex) = form (a): u_chn R180, u_dmem MY 1749.1/160.9, u_cmem R0 1960.0/160.9 + DOREG; CTS seam stages +675/+338.
  sd8r TT repair -189.49 -> -50.01 (8 endpoints below -20: 6 u_bm.dz, 1 u_bm.d, 1 r_klo).
  sd8g (MINE, live 13:45): epyc8 fable-fix-head-timing/sd8g = sd8 kit + stages, 4_cts.odb = repaired DB, resume.json start grt,
  goal route + sign-off. Log intel2 ~/fht-logs/sd8g.log. r310 read = its GRT-stage OT_TT_SETUP lines.
  If GRT-RC TT < -42: per COORD size/duplicate the named drivers in the hook (u_syn done[0] fan-out chain, INVx1 before r_klo), new kit.
  Form (b) dropped; (a) without DOREG only as follow-up after a sign-off (hooks name g_oreg flops).
- hd_host_w: hw4 GRT-RC -8.71, in detail route (epyc10), sign-off chained, log intel2 ~/hto/hw4.log.
- State script: localhost scratchpad fht/snap2.sh. On SIGNED: ffht_export.sh HOST ELDIR BASE SIGNOFF NOTE, then post RESULT.

## UPDATE 11-16 14:5x PST Codex resumed ownership
- he12r remains the sole active host_e candidate; no duplicate build. Intel2 client1544881, unitoth-ubuntu-2937243-1794864902; initial GRT overflow0 after restored exact M8 grant. Full-scope FF target20 repair is progressing (latest+19.346ps), not terminal. Automatic route/signoff remains chained; no export/count/adopt yet. Existing he12 failed evidence unchanged.
- Whole WEST reverse-bank fallback offline reference fits:54pins (53data+valid),109existingFF/BUF/INV,18.28332um2,0overlap against48NF15 permanent clock reservations; wholelocalchain<=4.141um; predecessorcenter<=377.784um(+2pinallowance). Explicit historicalhe12 geometry/plot/budget/scripts persisted epyc2 fable-fix-head-timing/he12_west_geom/reference_he12_fit. Analytical TTfloor+111.589/FF+17.482ps under stated clock/slew assumptions;2HB4reserve+0.20412um2 yieldsFFfloor+32.990ps. This is model/geometry only, not current-he12r STA or physical qualification. Image viewed. No newroute if he12rqualifies.
- Matching currenthe12r read-only3_place probe client2545285 logintel2~/fht-logs/he12r_west_probe.log remains under normal epyc2 thread admission; outputfolder he12_west_geom/current_he12r. Rebind proof to its actual geometry before any future candidate. No admission bypass/duplicateprobe.
- HEAD-TYPES sourceclone reserved by parent for r365guard/HW followup; our geometry assets live outsideclone and it is untouched.
