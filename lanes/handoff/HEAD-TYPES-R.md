# HEAD-TYPES-R handoff

## HEAD-TYPES-R main (host_e / host_w / TP2) -- 11-16 17:5x PST
Successor of FABLE-FIX-HEAD-TIMING, HEAD-TYPES-O, HEAD-SERDES-O. Forks own the "### hd_serdes" and "### hd_spn_end SPEPRD3" sections. Client logs: intel2 ~/head-types-r-logs/.
COORD lever 6 (17:3x): M8 grant wherever M1-M7 reserved; sd9A to GRT; hw4 hold through HOLD-FLOW-R internal-only stage. STOP: host_e without M8 grant, merged OBS pins, four-net rip runs, sd9B.
- hd_host_e he12h: DRT live E9 client 26922 (intel2 ~/fht-logs/he12h_drt.log), iteration 1 at 17:25. Kit has MAX_ROUTING_LAYER M8 + m8_grant.json. run_drt.sh chains finish/abstract/pin audit/signoff_he12h; on SIGNED export with ffht_export.sh. E9 scratch2 fell 96 -> 46 GB free in 25 min (ALERT posted 17:34); watch it.
- hd_host_w eco_hw4: E10 controller 2317099, DRT iteration 2 at 17:10 (~2400 violations). Do not restart. Its nonport scope predates r371.
- hd_host_w hw5: LAUNCHED 17:50 to GOAL grt, epyc8 /srv/opentallas-scratch2/claude/head-types-r/hw5/hd_host_w (replica epyc7), intel2 client 306907, unit oth-ubuntu-3191148-1794878585, log ~/head-types-r-logs/hw5.log. = hw4 kit + hw5_bank_tap.tcl (sourced after clock_taps.tcl in pre_cts.tcl): u_bout_coll_o0 bank leaves clk_t1 for the single-sink tap clk_t6 (own tree).
  Measured basis (E9 fable-fix-head-types/hw5_tapread/tap_arrivals.tsv, routed hw4 FF): bank on clk_t1 297.8..378.3 ps, mean 341.0 (NOT the 254 quoted earlier); small taps 340..346, spread < 10; all taps sit at y <= 294 um, bank at y 342..547 on the W face, so no existing tap is near it.
  NEXT: at GRT read OT_HW5_BANK_TAP line, OT_TAP_BALANCE for clk_t6, TT/FF; LOOK at layout; internal-only hold stage (HOLD-FLOW-R, else he12h run_hold.sh recipe); then DRT by do-* targets as he12h/run_drt.sh.
- hd_tile TP2: waiting for the plan from HEAD-DIE-R (private type_m8_grant delta, guide a8dcf2f554252553).
