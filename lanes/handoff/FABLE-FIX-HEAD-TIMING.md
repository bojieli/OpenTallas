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
