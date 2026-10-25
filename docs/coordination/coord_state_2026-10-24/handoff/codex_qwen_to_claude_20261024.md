# Qwen worker handback — Claude reset
All new work stopped. Running jobs kept alive. No merge in progress; central main clean when checked, HEAD24b2da3433 (root may advance it).

## Branches (pushed; do not whole-merge inherited lane branches)
- codex/qc-tok-1024 @210a1be64f: fixed required-role carve and integrates truthful numeric+fixed-consumer-edge mutant gate. Compiles; reused prior both14 receipts to check evaluationPASS. Capacity16 running; new gate not yet exercised by completed capacity run.
- codex/qc-capacity-1024 @72ece79138 (worktree codex-qc-a0): initial56-type capacity candidate, canonical433915pads,114lane changes, fullbind0errors. Lastchange only SUvariant declaration regex for parked66-type alternative. All/part R8 preserves597replicas. Alternative426373pads/66types saves7542 only; parked.
- codex/elem-qk-1024 @a8a31539a8: all own P6/recovery WIP parked, ASTK read-control replica candidate/proofs/reviews. Many edits already isolated/main, never wholemerge.
- codex/tok-qw-1024 @0a55cb9ec4: parked F5 SRAM rename and F7 exchange bench corrections already isolated/main.
- codex/kv-tok-1024 @201e4940f1: BO1 source gate copied/parked. Only remaining tracked dirtyfile ot_qwen_d2d_sfm.sv mirrors alreadymerged F6/main support, no cfg-only patch.
- codex/trial-qk-1024 @0cbbf200ab: clockprobe+IRreview. Existing uncommitted die_trial.py remains old copied paused WIP (SS/reporting/exit-mask issues); do not merge it blindly.
- codex/qwen-status-integration-1024 @eeb07138d4: all isolated edits mergedmain, clean.

## Main gates delivered (key merge SHAs)
- 60c21cd01d F6 OBS1_COMPAT opt-in receiver:530microchecks + bothT256/T8192 bound-master35-layer exchange exact, malformed/result/status controls caught, defaultlegacy/0cycles.
- b1e16de8f0 F5 actual p192 SRAM name, no fallback shim.
- 27d736c4e0 Binder defaults; cd2dc7f6d7 selected-variant own defaults (2realYosys gates, predecessor-only parameter rejected).
- 83e1cfdf48 F7 COMPLETE matching MU+RoPE/emb1627 package and4ROMs:fullframe exact63107C->K,58173K->C,1703STATUS,6628KVN; slot+1 mutant caught. Integrationcandidate, not product/profile/fulltoken adoption.
- aa6bdef01c corecorner LIB_FILES colon parser, TT/FFonly, failclosedemptylibs.
- 5ca632d670 P6 complete bind recovery:2723884compared,2723870matched,0mismatch/unbound/tied/undriven/multidriven/missingleaves,14declaredglueunmatched; splitlintPASS. StillG0C52/56 beforecapacitycandidate.
- 02b6d4110e preserve existing required head relayFFs, baseline4dropped vs kept28/28faceguardPASS,1000edge miterPASS+mutant.
- a2757edd53 BO1 additive opt-in HOST variant defaultD2D_BOOT_ORDER0, actual acceptedprogramme event, sixrealbc4 modesPASS andfullHOST/memoryclosurelintPASS; no canonical source/crossing adoption.
- 62a0eccca3 robust core ff_skip_re replacement/currentclockhook;1970bbbcb8 portable typedcore contract/context. Freshkit emits core.json boundary_role clk/clk_unused/reset/in/out and boundary_guard_context.json relativecore.json, no data exemptions. Root implementing shared signoff consumption.

## Live jobs — all own outputs, ot-run; keep alive
Check local logs under /srv/opentallas-scratch/claude/codex-qwen/*.log and remote namedrunlogs.
- intel2:/srv/opentallas-scratch2/claude/codex-qwen/xt1_capacity_both16_v2 —96GB24t boundbothcluster smoke, compiling; source matches initial56-type433915pad model,25/25regeneratedconstantsPASS, XT1lead16. Check build.log, then sim_m*.out/log_m*.txt.xt1n.json. Run tools/die_plan/xt1_schedule_gate.py on actual JSON afterwards; HR+1 can pass numbers but must fail fixedcalendar edges. Do not falsify numeric verdict.
- intel1:/srv/opentallas-scratch2/claude/codex-qwen/pvpair_m7 —32GB8t finish/TTFF, detailedroute2ndoptimization ~2635remainingviolations. PriorM5GRT1692/2548overflow; M7GRT0overflow,14.72%usage. Actualplacementreview saved. NotSIGNED.
- intel1:/srv/opentallas-scratch2/claude/codex-qwen/head_e1_hold40 —32GB8t oldkit hold40 retry, DRT70000groups; usesoldsource withoutnewkeep. Timingrepaircandidate only, cannotclose8missingboundarydataFFs.
- intel1:/srv/opentallas-scratch2/claude/codex-qwen/astk_WN_r4 —32GB8t freshroute, DRT20000groups. Same-cycle4x5bitread-control replicas perZ,80FF/core,0cycles. RealFPgate9992comparisons/2491valid/4982mutantmismatchesPASS. Canonical leaf unchanged, candidateonly.
- intel2:/srv/opentallas-scratch2/claude/codex-qwen/head_e2_keep/kv3_head_eighth_e2__285.12x285.12 —32GB8t freshcurrentgenerator keep/CTS_ARGS route, DRT40000groups. core.json+typedcontext staged. OriginalTT+28.29/FFhold-10.67ps; newresultpending.
- intel2:/srv/opentallas-scratch2/claude/codex-qwen/kv_ir_retry256 —256GB16t abstractKVIR. PDNcompleted2112s; ir_pdn.odb59.7MB saved; matrix/analysis ongoing. Old96GB jobOOM/137 preserved. Runnernowpropagatesrealexit. Abstractpower89Westimate only.
- epyc2:/srv/opentallas-scratch2/claude/codex-qwen/kv42_o1_perf —8GB1t originalRTL goldenshort MAXCYC2500+2000drain. Binary /.../kv42_o1/obj/Vtb_kvslice; all79hierlibsO1built. Reproducesexactboot_go453,fwd_epoch463,f_early539,d2dfault543. O1singlethreadspeedmodest~2..3cycles/s. Keep running.
- epyc2:/srv/opentallas-scratch2/claude/codex-qwen/kv42_parallel16_perf —16GB16t identicalRTL, cached79childlibs/TOPonly --threads16 --hierarchical-threads16. BuildPASS, sameevent/fault sequence reproduced, alreadyHB2500 at handback (material speedup vsO1single). MAXCYC2500+2000drain. Need final perf.time and tracecomparison before use for fullboot.
- Three old pausedKV simulations remainalive on epyc2 rootdisk: pids434532/434535 boot42 nominal/mut_frame and466382 tok42 FARtoken, originalkv42_build O0. Do not kill/move them. tok42 lastHB20000,528/7161frames,images_ready0,fault539.
- Old source s8exp compile STILLalive intel1:~/ot-scratch/tok-qw/r1024/s8exp/die/build/obj_n12; started07:22, >4hcompile, notfailed. Do notrestart or kill.

## Completed candidate builds/ECTLK diagnosis
- epyc2:/srv/opentallas-scratch2/claude/codex-qwen/kv42_bo1 —BO1candidate binary built/linkedPASS, NOT RUN yet. Uses sameactualboundhub_Wi wrapper with only dedicated L643 branch sourcedfromHOST.d2d_boot_begin, explicitparameter1. Old4HBMboot_go sinksunchanged. To accelerate fullboot, combine BO1 childwith successfulparallelTOP scheduler or rebuildonlyTOPinthisclone usingparallelprototype recipe. Scripts local/remote codex-qwen/build_kv42_{o1,bo1,parallel}.sh; fullBO1package /srv/opentallas-scratch/claude/codex-qwen/boot_bo1_bound_candidate (alsoepyc2scratch2).
- BO1newsource physicalcrossing is35landededges=28transport+7existingpad, NOT28. OnependingcontrolFF,0data-cyclechanges, allactualHOSTrequest/programme/bridge clocks mapcore. Fullfreshbindcachemissing; currentpackage has newdeclaredrewire/census edge/bus-groups candidate, but canonicalR8/rebind/fulltoken/physical stillrequired. cfg-base-only readiness is disproven; acceptedHOSTprogram_ready eventrequired.
- ECTLK originalGPLNaN sparse1.7%std/8%macro; bins256alone eventuallyPLACE/DPLPASS butheavyinflation persisted. /intel2scratch2/claude/codex-qwen/ectlk_bins256_noinflate PLACE/DPLPASS quickly withGPL_ROUTABILITY_DRIVEN0. Actualp90pin-reg8.33um (oldunplaced732). Lowfill3.4%/85%empty is fixedpinlimit3625S M5pins*.24um=870um vs881.28width; originalFAIL reportpreserved, separateconditionalpinlimitedreview documented.
- intel2:/srv/opentallas-scratch2/claude/codex-qwen/ectlk_m7 FINISHFAIL CTS:11371holdbuffers,maxbuffercount, residual-604.7ps. M7withinplanlayerbudget, no clock/IOrelaxation.
- intel2:/srv/opentallas-scratch2/claude/codex-qwen/ectlk_ctsdiag CTSsnapshotDONE (SKIP_CTS_REPAIR_TIMING1 diagnostic ONLY, notclosure). Realclockis LATE: expanded pathalready694ps after~18BUFx24stages beforefinalsink; inputhold-704ps/resetremoval-538ps, outputhold+494ps; TTinternalsetup-313/output-208. ck[0] drives12480FF+4SRAM. Addingclockdelay worsens; investigateCTSbranchdepth/clockentry/macrobalancing, never waive250psclockbudget. Exactreports cts_unrepaired_{hold,setup,clock}.rpt andsaved4_1_pre_repair_setup_hold.odb/4_cts.odb.

## Remaining gates / next steps
- All11originalcorecorner recoveries DONE, allNOTCLOSED. TT/FFholdps:head1+13.77/-9.54,head2+28.29/-10.67,head3+5.57/-10.12,head4+15.32/-9.95,head5+13.81/-7.89,head6+13.53/-11.17,head7+15.38/-11.76;astkEN-8.99/-36.44,ES-34.12/-35.02,WN-80.61/-37.42,WS-47.63/-37.83. OwnTTFFreports .../<core>_corner_recovery/views_safe onIntel1head1..3/Intel2others. Face/clock/DRVguards remain, noSIGNEDclaims.
- RootFF-onlywarmECO recipe /srv/opentallas-scratch/claude/codex-clock/r4b_ffeco/{run_kit.sh,slice_station__t7/route_slew_repair.tcl}; T7margin10fixedFF+4.23butTT-23.68, so margin0..2 mayfithead2TT+28.29. MustfinalTTsetup/FFholduniformgates; recipeisnotprovenclosure.
- A0NK/NL fullshape outputs both2560/2560words exactat+7cycles;neighbor6308edgesexact0shift. Tapmutants2560mismatches; NLneighborbit5controlineffective(unobservablezero), recordednotcaught. Specprices+6, residual+1mustintegrate beforeG3. NoG3adoption.
- F7completeROMpairready/main, actualboundfulltokenstillpending. ProductprofileMU+RoPE/emb1627 remainsqualifiedintegrationcandidate.
- TOK-QW xhead completedFAIL hoursago: calibrationsweep go_lag[-2..6] allPASS, xpfedge4, so noPASS/FAILgoedge -> noages. Existingbenchalready supports OT_XH_GO_MIN; next owncopy/reuse existingobj_xh/Vtb and widenmin -16/-32, thenper-consumersweep+4nominal/10mutants. NO newjobstarted afterreset. Oldpath intel1:~/ot-scratch/tok-qw/r1024/xhead/out/calibrate.out. Source stg527/527 andhead123+131PASS alreadycollected; source-onlynotbounds8proof.
- qkd_ctrl_kc oldODB sound; finalV has34falsefeedbackloops fromnet/BTermnamecollision; rootdiagnosed. RenamebeforebothVerilog AND SPEFexport iffixing, notafterSPEF. RootsignoffTT-1.13FFhold+15.39,SDClint150legacyerrors (833.333vs833 etc), NOTSIGNED. Do notuseexperimentalnetlistSTAasgate.
- Capacity150k isoptimizationtarget, nothardgate; initial56-type433915padtradeofftoadvanceonlymatchingcalendar/boundsmoke. Do notadoptparked66-typealternative.
