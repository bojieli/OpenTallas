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

## CODEX NF15 private pin proofs 11-16 11:0x
Both GEN jobs passed; original source/gen receipts preserved. Approved8df7 TT replay helper+TT Tcl staged into fresh CLOSED kits, hashes b8878af6/36f944e2, with source_delta_pg_replay.json and nf15_proof_identity.json. Only captured explicit PG flags missing from RFLOW0 generated config were appended: n3t truth1; spe truth1/wide1/cellkeepout0. PGCAP1/TTboth unchanged. No RO source or live-kit edits.
Rendered/VIEWED generated full type pin geometry plus old/new critical-pin PG zooms; PASS-COND records/images epyc10 fable-fix-head-types/results/geom_review/nf15_pin_1116. n3t rst_start_raw2 y291.744->293.920, spe rst_start_raw0 y1211.792->1213.984; each M7pin has0->7 legal M6 landing tracks, same x/size/layer. Nohardcores, unchanged RTL/+0cycles, existing ordered FT windows and clocks retained.
Both kits replicated to intel1/epyc8/epyc9/epyc10; unpinned admitted routes chose intel1. n3t client935676 unitoth-ubuntu-1851691-1794856072 mem32GB8threads (historical routepeak19.2GB); spe client936055 unitoth-ubuntu-1852231-1794856072 mem48GB8threads (historical routepeak28.0GB). Exactdirs /srv/opentallas-scratch2/claude/fable-fix-head-types/nf15_pin_proofs/<type>/kit/<type>. Logsintel2~/hto/nf15_n3t_route.log and nf15_spe_route.log; both preflightPASS. Not physically signed; collectTT/FF/DRC/LEC and export only valid records. Planreview/adopt remains pending, private proofs explicitly authorized.

## CODEX HEAD structural continuation 11-16 11:5x PDT
- Source branch claude/fable-fix-head-types-1115 now506b984ba466cbad7f1b54fce0cff64e42e14926 (463b skid +7707 CS copies +506b exact he11r free-load). Whole unmerged branch source gate GREEN1/1 maincf470568551; native full-width2M cycle exactness0 mismatches, shadow-drop mutant rejected746771mismatches. CS-copy inherited200k+mutant proof retained. Source approval/merge root-owned; physical adoption still requires SIGNED.
- Pin keepclear opt-in source3619db58d0d8fe585876f55531b9f1d6002b44d4 atop506b, normal gate GREEN2/2 main6eebdee6211. Exact full-shape actual host_e fixed IO +NF14r clock reservation regression0 overlaps; raw1x93.28→92.064, raw3/raw4x17.312→16.608; clock/sourceFF locations untouched. Future NF15 input-only bundle epyc2 fable-fix-head-timing/nf15_pinfix has exactly3 landing-contract x edits over PGR1 planc89216, sidecaraef151 unchanged, full2180pin regeneratedIO. Must generate fresh actual kit/audit/abstract/metadata and review before route; not a frozen kit/adopt.
- he7/he8 merged LEF and he9 trim proof failed GRT0116 (he9overflow44). he10 trimmed LEF completed DRT: EOL0 but final fixed-pin Short1, TT-125.19/FF-17.01. he11r coherent whole-bank deterministic layout completed DRT with ONLY same fixed reset_raw1/clk_t5 overlap, antenna0,area133357um2; automatic extraction/signoff continues. Full cause/source correction posted. No live-kit patch or route ECO.
- hw4 CS-copy form continues DRT, first iteration80%; GRT TT repair -31.26→-8.71ps, preGRT FF+4.85675/0ep, cross-tap+45.0001 after23314holdbuffers. No final verdict.
- DRT0206 named-four-net force-rip control retains all original PG protections and is progressing epyc10 eco_ab206_rip4/i1t. Pin-access>100k groups, exactOpenROAD process active. Earlier no-tracktruth eco_ab206 remains INCONCLUSIVE; no generic fix claim before real comparison finishes.
