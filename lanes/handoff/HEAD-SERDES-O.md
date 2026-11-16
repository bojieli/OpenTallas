# HEAD-SERDES-O handoff (Opus successor of FABLE-FIX-HEAD-SERDES) 11-16 ~04:05 PST
Goal: sign off hd_serdes (s81_head): DRC 0, TT setup >= -42 ps, FF non-port hold >= 0, LEC.

## Where things are (epyc10 /srv/opentallas-scratch2/claude/fable-fix-head-serdes = W)
- Branch claude/head-serdes-fanout-1116 @3176b99392c PUSHED (on main c03ba6c3b9). W/repo is a SPARSE checkout of it.
  - ab32fbbe30 fanout copies DNGB 12 + RMRPC 32 (+0 cycles)
  - 3176b99392 DKREG 1: k_* seam register in front of hard u_chn in ot_s81_kp4_dec, ddly DDX 1 (DD 55->56), +1 pma_rck RX
  - only ot_s81hd_serdes_link(_ls).sv set the params; S81 defaults unchanged.
- Bench W/sim2 (bench script W/bench2.sh, log intel2 ~/head-serdes-o-logs/bench2.log): PDIE_FANOUT_EQ PASS (incl DKREG form,
  DKREG_MUT_NODD FAIL, RMRPC_MUT_STALE FAIL), PDIE_LINK_GATE PASS.
- Gate GREEN 5/5 on main 466e9e86202 (rerun with ROM dir staged: epyc2 mq-gate/lane/head-serdes-o-gate.sh sets MQ_SPARSE);
  READY posted 03:5x to MERGE-QUEUE-1. First gate was INFRA (sparse set lacked physical/asap7_memory_macros_v2/ot_rom_4096x274_m8).
- LATENCY row posted 03:40 (COORD: do not block on HEAD-100): +1 pma_rck (833 ps) per die-link RX, decoder 60->61;
  0 of 329 LATCHECK lanes touch lk_* (hd_serdes) partitions, so LATCHECK unchanged.
- HOLDGEN holds the hd_serdes wave item until a RESULT PASS line naming head-serdes-fanout (post after sd5 signs off).
- W/tree5 = cp -al copy (MISTAKE; COORD 11-16: never cp -al a published tree, use cp -a; TOOLS-CONVERGE breaks the links on
  their side so tree5 keeps working; W/mktree5.sh now uses cp -a) of TOOLS-CONVERGE pin tree kw45/src_head_pin_e594a73db756 + the 43 files that differ e594a73..branch
  of TOOLS-CONVERGE pin tree kw45/src_head_pin_e594a73db756 + the 43 files that differ e594a73..branch (script W/mktree5.sh).
- W/sd5 = kit from tree5 (W/gen_sd5.sh, log W/gen_sd5.log): plan NF13a, kit RTL W/sd5rtl (attempt_6 bootstrap + branch files),
  env = s81_head die_gen_env + OT_PG_DIE_PHASE=1 (M7 offset 8.448) + OT_PGCAP=1 + OT_TT_SETUP_REPAIR=both, no private leaf.
  Running from synth on epyc10: ot-run --mem 64 --threads 12 (log intel2 ~/head-serdes-o-logs/sd5.otrun.log), goal route.
- W/sd3: control kit (sd2 CTS DB + C3b + GRT repair keep-if-better + private leaf), in GRT TT repair (before -73.04).
- W/sd4: superseded, not launched.

## Next
1. sd5: read CTS/GRT TT repair numbers (tt_setup_repair.log, keep decision), route DRC, then signoff.py (TT setup, FF hold, LEC).
2. sd5 signed off -> RESULT PASS line naming head-serdes-fanout (releases the HOLDGEN hold).
3. If sd5 TT still < -42: classes from the reloaded GRT DB (W/diag/classes.tcl pattern), next structural form.

## 11-16 05:5x update
- r288 APPROVED (branch fanout + DKREG). sd5 FAILED GRT-0116 (congestion 2) + CTS TT -199: sd5 lacked the wave item_env
  (OT_CONS_KIT util 0.25, M9 ceiling, fanout 32, pma_rck secondary clock, M8 grant, PG track truth). diag W/diag5 (worst:
  u_chn -> u_out cmem/bsrc long wires). 
- sd6 = W/gen_sd6.sh (die_gen_env + item_env + PGCAP + TT repair + OT_GRT_ALLOW_CONGESTION=1), config equals sd2/sd3 form
  plus main additions; running from synth on epyc10 (log intel2 ~/head-serdes-o-logs/sd6.otrun.log). After route: signoff,
  then RESULT PASS head-serdes-fanout (HOLDGEN hold). If TT short: diag5/run.sh pattern on sd6 DBs.

## 11-16 09:2x update
- sd6 (fanout+DKREG): CTS TT -146.8 -> -26.6 kept; GRT TT -182.9 -> -112.5 kept. Worst class (W/diag6): 55 u_out.bsrc
  endpoints, u_chn clk->q 400 ps + ~480 ps wire/6 BUF. Also u_enc.rem_q -67.8. sd6 still running to route (wait by8qgs7ni).
- DOREG form: branch claude/head-serdes-doreg-1116 @67db0dbde3 (LOCAL in W/repo, not pushed): seam regs g_oreg.r_* on
  chn->out (cw/apply/one/unc/fs), DDX = DKREG+DOREG (+2 pma_rck per RX vs main). Bench W/bench3.sh (log
  intel2 ~/head-serdes-o-logs/bench3.log) must PASS doreg and FAIL doreg_mut_nodd; then push, gate via epyc2 wrapper
  mq-gate/lane/head-serdes-o-gate.sh, READY, LATENCY row -> +2 pma_rck.
- sd7 = DOREG RTL, sd6 kit form (W/gen_sd7.sh, log ~/head-serdes-o-logs/sd7.otrun.log). FABLE-CLOSURE-1143 ask done in
  place before placement: sd7/hd_serdes/oreg_site.tcl (sourced end of cons_gpl_pre.tcl) puts g_oreg flops FIRM 1.5 um
  outside u_chn on the driving-pin edge; released in face_flops_release.tcl. Check log line OT_OREG_SITE placed N.
  Kit-local; move into gen_phys if sd7 closes.

## CODEX takeover 11-16 10:0x
- bench3 completed PASS, no-DD DOREG mutant FAIL, link gate PASS. DOREG @67db0dbde3cb66803be3de32629da6e41bc79e4e pushed; remote gate GREEN5/5 main d26d283677ad, READY posted. +2 pma_rck total; no physical PASS yet.
- sd6 live detail route; sd7 live GPL (expect OT_OREG_SITE count after cons_gpl_pre). Preserve both; next read sd7 placed flop->u_chn distance and GRT TT.

## CODEX shared PG replay fix 11-16 10:4x
sd6 DRT-0255 diagnosed: initial GRT PG cuts were lost in the fresh TT repair router scene; new repaired buffer nets acquired long M6 guides on PG-pair rows. Source claude/head-tt-pg-replay-1116 @8df7c2f39188436136456c1d73d057271c9ee98e (from main06c5e501a8), normal remote gate65/65 and focused30tests PASS; merged main6ce01001775 per MERGE-QUEUE. Actual moved-buffer two-net guide A/B PASS: control net59940 longM6 PG-row guide, replay routes long segmentM8; bad longPG-row guides1->0. net60175 clean in both reroutes. Both jobs exit0; evidence pg_replay_ab2/result.json. First unchanged-pin roundtrip fixture INCONCLUSIVE/no-op and preserved pg_replay_ab/guide_ab_result.json. No DRT or physical signoff claim, no RTL/cycle change. Helper API: source grt_pg_replay.tcl; ot_grt_pg_replay_begin KIT before incrementalGRT; ot_grt_pg_replay_end after end before checkpoint. Stage BOTH Tcl files in fresh/pre-TT kits; already damaged kept-TT guides do not automatically reroute when pin gcells stay unchanged. Runtime files tools/die_plan/{grt_pg_replay.tcl,tt_setup_repair.tcl,gen_phys.py}; helper copied by gen_phys. Existing sd7 untouched.

## CODEX reset handback — 2026-11-16, parked on explicit Claude reset

No further work/launches after reset. Existing jobs continue. All paths below are in existing lane /srv/opentallas-scratch2/claude/fable-fix-head-serdes.

- sd8 CTS completed exit0 on epyc8. Immutable snapshot diag8_cts/4_cts.odb (319472601 bytes), original sd8 preserved. One planned read log intel2 ~/head-serdes-o-logs/sd8_cts_paths.log completed exit0. Nominal833 owner12.24b/c setup0/hold25 policy unchanged. Actual worst stages ps: syn→DKREG −189.49; DKREG→chn +142.47; chn→DOcapture +675.12; DOcapture→correction +338.19; correction→cwp +363.87; fs→os +533.48; cwp/os→qd −61.94; qd→rm +140.06. Changed dmem write data +351.04/address +656.66/readaddress +602.80; enables/masks constant; chnreset +126.04. Capture553 maxdistance74.473µm afterDPL (analytic6.643 NOT realized), but capture stage has large positive slack. Whole actualsite counts:554capture,320directDKREG (3resetmovable),544correction,428cwp/os,fullselectlogic;5251 qd/rm state anchors. No GRT/DRT launched.
- Root approved canonical TT repair before judging cycles. Fresh sd8r/hd_serdes epyc8 only: client1276496, log intel2 ~/head-serdes-o-logs/sd8r_tt.log; approved unchanged TT_SETUP_DESIGN1/repair, no newknobs/clock/PG/cycles. Before snapshot 4_cts_before_tt.odb preserved; expected 4_cts_after_tt.odb NOTYETpresent at handback. Last measured repair WNS −55.534 from−189.49, then legalizing (iter580). continuation.json has hashes. Keep running. After closure, reload actual repaired DB and read stage/write/control set before DRT; standardTT repair was intentionally skipped by original GOALcts. Driver cause: INVx1 at348ps/slew320ps onworstklo296; os→qd has BUFx2/OAI/OR drive chain. Do not blindly add cycles or reject pre-repair CTS.
- Exact write map log sd8_write_boundaries.log:546WD pins,544dynamic fromu_syn,2constants; oldsourcex1514..1848 andnewdmemwritepinsx1749..1927 bothWESTofcorrectioncorridorx1930..1954, so no extra544bits across that cut, but independent write timing obligation covered above. Address6+6 uses6u_dly counters; CE/mask constant. Onlynon-kchn SIGNALinputrst_n, transformedpin unchanged atmidline. ActualSD7 reset8BPinrects vsclock25 same-layercollisions0.
- Shared fixes8df7 TT PG replay merged6ce01001775 and d2f explicitPG export approvedr329, normalgate61;78895 physicalclocklayer metadata normalgate77, approvedr334 andmerged mainf5e80c4c826. No live kit patch for metadatafix. NF15 private proofs staged approved runtime/captured intent before launch.

UNFINISHED PMA SOURCE FIX (do NOT merge as READY):
Existing repo epyc10 .../fable-fix-head-serdes/repo, branch claude/head-phy-export-source-1116, HEAD/base631a6971d868da348a477a2792e8a1ad42773d17. Modified tools/die_plan/clock_taps.tcl, pad_clock.py, sdc_lint.py; NEW untracked tools/die_plan/phy_clock_export.tcl. No commit, no focusedPythonnegative tests, no normalgate. Preserve older untracked results/geom_review/head_sd3_control_sta_20261116.md and head_sd6_pg_replay_move_20261116.md.
Root approved exactscope: typed owned hook after every SDC reload +clock_taps end, only actual-retapped pma_tck source, no generic source escape/newruntimegate. Actual sd8 witness: pma export output3361 BUF/A onclk_t2 tree, A455.202/394.957 andY483.664/423.249ps; declaredgenerated source stillrawclk. fclk_out_coll_o0 actuallyrootsrawclk (Y450.429/392.735), leaveunchanged. Masterclk833 has22sourceports. ActualpmaTX andcolloutputtiming usesvclk (+564.68/+556.06), so dataIO policy staysunchanged. RXCDC maxdelay833/holdfalse staysunchanged. EmbeddedOpenSTA509913b1398b36eda23caa1f1f380167465dceee Sdc::makeGeneratedClock reusesClockobject; initGenerated preservesuncertainty/exception/latency maps but resetsis_propagated: helperexplicitly preservesflag.
MinimumactualSDK fixture files epyc10 clock_export_sdk/ (3BUF toyLEF/LIB/22masterports, nohardwareP&R). Client1340070 EXIT0 justatreset, log intel2 ~/head-serdes-o-logs/phy_export_sdk.log. Legacywarning/fixed833+SDK_FLAG1+REBOUNDclk_t2 observed. before.sdc/after.sdc/after2.sdc/reloaded.sdc exist BUT NOTYETcompared/asserted. Must finish exactbefore/after uncertainty/CDC/source-latency/waveform/propagated snapshots and negativecontrol stale-source failure before normal sourceREADY. Currentcodeispartial/unqualified. No newscene justforwarning.
