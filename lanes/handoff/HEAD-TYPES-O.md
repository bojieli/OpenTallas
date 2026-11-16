# HEAD-TYPES-O handoff (Opus successor of FABLE-FIX-HEAD-TYPES; started 11-16 02:36 PST)
Scope: hd_ctl, hd_spn, hd_host_e, hd_host_w, hd_serdes(-> FABLE-FIX-HEAD-SERDES), hd_lep0N, hd_mesh + hd_st_k5, hd_st_n3_turn, hd_host_n; r199 F1 recheck of NF13b.
Predecessor state: lanes/handoff/FABLE-FIX-HEAD-TYPES.md + lanes/posts/FABLE-FIX-HEAD-TYPES.md. Lane dir epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-types (all kits); epyc7 head-types-o (bind runs).
Client logs: localhost session scratchpad (c228d9e1...) <name>.log; watcher hto_watch.sh.
In flight 02:40: eco_he3 (i1t route), he4 (epyc2, skid RTL, from synth), eco_n3t (route), k5b (route), spe1 (route), hw3 (GRT), eco_ab206 (DRT-0206 A/B, GRT).
Done: skid RTL LATCHECK 329/329, tsv byte-equal; committed claude/fable-fix-head-types-1115 @463b9396539 (no merge until a signed he).
Export: scratchpad ffht_export.sh HOST ELDIR BASE SIGNOFF NOTE (rtx-pro + AGIdock + INDEX).
Pending: F1 verdict when HEAD-100 posts NF13b COMPOSED (check LATCHECK 329/329, fixed_in_core 12, delta -1 on coll_EN1_d/WS1_d/ES1_d/HOST0_u).

## 11-16 06:3x PST (after the 1-h limit)
- Posted: F1 VERDICT PASS (NF13b d43c54ae83ba); DRT-0206 A/B INCONCLUSIVE (no track-truth -> DRT-0255 in ECO, died before checkConnectivity); rst_start_raw interior M7 pin Rect Only class (hd_st_n3_turn, hd_spn_end); hd_lep0N a2 dead (fault/ready reach -4,225).
- Routed results: k5b SIGNED (proof kit NF13a+hand FREG, NOT countable; countable = NF13b kit), n3t ECO DRC 3 only (pin row), spe1 DRC 3 + hold -6.41 (pin row), hw3 TT -80.84 / hold -34.19 DRC 0 (BUFx2 64-load DRV path) -> eco_hw3 running (epyc10, client log intel2 ~/hto/eco_hw3.log), he3 ECO failed (-116.51), he4 -66.43 -> eco_he4 i1 -66.93 DRC 29 (ECO no help).
- he5 (epyc2 fable-fix-head-types/he5, from synth, client log localhost scratchpad he5.log) = he4 + isl_sd free-load (if (!isl_sv) isl_sd <= in): removes in_ready from the isl_sd enable path (he4 worst path); cycle-exact (skid2/tb_skid2 2M cycles PASS). lec_async.sh added to the kit. Needs LATCHECK + commit if it gates.
- ot-run: localhost ot-run only sees epyc2/intel1 now; launch via intel2 (ssh intel2 ot-run ... --hosts epyc10 --dir LANE_DIR; isolation refuses paths outside --dir).
- v2 HEAD tree src_head_pin_eb1e73448bd0 on epyc10 kw45 (ep_core = pointer form 4e9b35b2736a); use for decisions when its marker lands.

## 11-16 09:1x PST
- hd_spn SIGNED + exported (s81_head/hd_spn__nf13a_a5eco1116, sha b2cf3c7c8019, INDEX both).
- hd_host_e: he4 -66 / he5 -118 / he6 -125, all DRC ~30 (u_epc M7 pin-top Lef58EolKeepOut = macro LEF class, posted to M7PIN-STRIPE-1116; PDN halo does NOT fix it). Timing class = u_epc inputs captured on early clk_c0 tap (-63): flops must sit at pin row. Structural call = FABLE-FIX-HEAD-TIMING; nothing more started on hd_host_e. No ECO rounds (COORD).
- hd_host_w: eco_hw3 no gain (-80.96). hw4 (epyc10 fable-fix-head-types/hw4, client log intel2 ~/hto/hw4.log) = cs decode 9 copies @7707d785682 (LATCHECK 329/329, tsv equal); post-CTS gate est -62.26, tt repair -29.72 -> -11.93; routing. hold -33 on hw3 still to watch.
- Commits on claude/fable-fix-head-types-1115: 463b939653 (skid), 7707d78568 (hw cs copies). he5 free-load not committed (he5 failed for other reasons).
- Checker: localhost scratchpad hto/c2.sh.

## CODEX takeover 11-16 10:0x
- hw4 live pre-GRT FF hold pass2; pass1 -173.52/949ep after12551buffers, no final verdict. he9(trim abstract DRC test) in route; he10 selective pin-row flop timing form reached CTS.
- he10 copied tt_setup_repair.log initially contains he9 -129.79; do not collect until mtime/run-stage proves its own repair overwrote it. he7/he8 are merge abstract DRC tests; selective he10 remains the timing form.
