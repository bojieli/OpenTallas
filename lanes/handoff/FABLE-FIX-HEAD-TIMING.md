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

## CODEX takeover 11-16 10:0x
- All active candidates retained: sd6 route, sd7 GPL, hw4 FF pre-GRT repair, he9 route(trim DRC), he10 CTS(selective timing). DOREG exactness/gate completed; READY posted to COORD.
- Next reads retain r310 GRT-RC threshold(-42ps), not CTS placement RC. No additional ECO rounds started.

## CODEX he11 structural output boundary 11-16 10:27 PST
- PLACE-ONLY live: intel2 ot-run client562013, log ~/fht-logs/he11_place.log; epyc2 unit oth-ubuntu-2851571-1794853586, dir /srv/opentallas-scratch2/claude/fable-fix-head-timing/he11. Kit/runner inherited he10, fresh run/signoff/async state. RTL byte-identical. Already through synth and into macro floorplan; no route/GRT started.
- Source identity: output_capture.tcl sha2567bdd6f9752fe177e86752fd143c559c9b1189817867ff4f3e4937ed759dafb8e; rx_chain_sites.tcl6ffffe548fc0f0887884dfe426428defbae6afcd159f0cd75fc233bbea0ed0a8; rx_chain_sites.tsvf3bc7218e4219283f25e8c2b850fc09968eb62d8115ebe464e34dd18f55f3fee. Site solver/probes/TSV/JSON live under he11; geometric review picture/proof/notes under lane/results/geom_review/hd_host_e_he11.
- Fixed mechanism: hard EPC OUTPUT clk-to-Q~1024ps plus long wire into existing u_sko.l_data. Whole output capture/control bank563FF placed within2.523um of source pins. Entire existing RX data+valid pipeline554chains through r0/r1 and MID now max280.692/280.638/280.692um per existing edge,0overlaps vs32441fixedboxes, bank controls/faults co-sited. Output capture +1121 intermediate FFs are existing hardware; +0area/+0cycles, no protocol change.
- Clocks unchanged: clock_taps normal-grid regex excludesclk_c0, only hard EPC on earlycore tap; SDC source-38.3234/early-63.3234ps retained. SDCsha08e810aaeaa9fd96938ad0c97ad2edb52e2a71ce36f96a55c370a0fd308a89c0, clock_taps shab9eb663059a111229a9dc3ba18c06dfbeb2f1567861bd396dc6b0753ded39412. Actual relocated capture insertion must be read at CTS, not assumed375ps.
- Next: actual placed bank geometry/render. Fresh continuation must take nf15_gate shared TT-repair PG-capacity replay fix before final GRT; no running-kit patch. Existing he11 actual approved config: TRACK_TRUTH1/WIDE_SPACING1/PGCAP1/CELL_KEEPOUT0.
