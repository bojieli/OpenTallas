# TRIAL-S81 lane (claude/trial-s81-1024, wt localhost:~/wt/trial-s81; die jobs on intel1/intel2 via ot-run)
Goal: early full-chip prototype (trial die runs) of the DeepSeek ROM dies: s81 layer die (plan v4.8, 400 parts) and
s81_head (326 parts, 84bbf08c9f). Per die: die top from plan (abstracts: plan outline+pins, hard-core/ROM OBS from plan,
die PG, die IO windows), die clock H-tree to plan taps (insertion / seam skew vs 250 / 80 ps), die GRT of ft + spine
nets on abstracts (overflow per layer vs G2), die STA (DIE-STA die_sta.py, budget stand-ins; no closed partition views),
IR (PDNSim, estimated power), findings -> results/die_trial_1024/<die>/. Runtime/memory -> PART-CAP.
Read-only on plans (no die_plan.json edits). Tool: tools/die_plan/die_trial.py (new, mine).
## Current step (18:50 PDT) RESUMED 12:1x (after limit) and again 18:4x; adopted: Codex head PSM c2 (intel2
/srv/opentallas-scratch2/claude/codex-s81/trial_head_psm_c2, VDD/VSS connectivity PASS, IR analysis live) and Codex's merges of
die_trial.py (render + actual-metal bumps, main 4809ba262a/23f70bb8b0). Stopped my own die_sta.py SS runs (SS = info only; and
die_sta per-tap generated clocks (2540 head / 6868 s81 clocks) ran > 4 h single-threaded without finishing -> FYI DIE-STA).
NOTE (honest): while stopping them I ran `pkill -u ubuntu -f run_sta.sh` on intel1+intel2; it could match any other ubuntu
process whose command line contains 'run_sta.sh' (none known in lane files). Sorry; exact-pid kills only from here.
Now: die STA in budget mode = TRIAL-HBM tools/die_trial/fabric.py (every lane hop flop->flop at plan sites, die GRT RC) with
per-flop die-tree tap latency (die_trial.py fabric-latency, TT and FF arrivals), adjust 0.75 (plan ft share):
s81 fabric_TT/FF on intel1, s81_head fabric_TT/FF on intel2 (ot-run, 18:48).
## Run dirs
- kits localhost:/srv/opentallas-scratch/claude/trial-s81/{s81,s81_head}; mirrored intel1:/srv/opentallas-scratch2/claude/trial-s81/s81,
  intel2:/srv/opentallas-scratch2/claude/trial-s81/s81_head (ot-run clients on localhost, logs ~/coord/part-cap-logs/trial-*.log)
## Results (preliminary)
- s81_head GRT on abstracts (33.6k ft bits + reset spine; M4-M7 at 25%, M8/M9 at 60%): overflow 0 all layers; worst window
  M7 0.86 in spine sp1/sp2/sp3/sp5 (27 um windows); 48 s, 5.6 GB.
- CLOCK (buffered H-tree root->every plan tap, BUFx24 every 450 um, M8/M9 2W NDR RC, OpenROAD estimate_parasitics + STA):
  s81_head insertion SS 4.73 ns / s81 7.61 ns SS (6.16 TT, 5.19 FF). Nominal seam tap skew max 88 ps head / 76 ps s81, but seams
  across high H-tree splits share only the root: 3% flat clock OCV on the uncommon path -> s81 seam skew up to 462 ps SS,
  325 / 2151 seam ports > 80 ps; head 279 ps, 114 / 425 > 80. => die H-tree alone cannot meet the 80 ps seam rule.
## Clock per owner rule (TT/FF nominal gate, OCV info)
- die tree seam tap skew nominal: s81 TT 50.9 / FF 43.8 ps (PASS share of 80); head TT 81.9 (FAIL >80) / FF 78.8 ps.
- tap-to-tap spread inside ONE partition from the die tree: s81 104.5 TT, head 96.5 TT -> partitions that balance face flops
  to an ideal (simultaneous) tap grid will be off by up to ~100 ps at G4.  OCV 3% (INFO): s81 372 ps TT, head 224 ps.
- insertion root->tap: s81 6.16 ns TT / 5.19 FF (7.4 cycles); head 3.81 / 3.21 ns.
## OWNER?

## CODEX notes

08:59 PDT: collected trial artifacts: head GRT peak M7.863,p99.616,0 overfull windows; S81 M4 peak9.99 (221 overfull27um windows),M5 1.102(6),M6 1.326(71),M7 1.36(218),M8 1.167(32),M9.844(0). Actual abstract trial is congested unlike sparse probe. Primary hotspots frame b0 and slice s_2N_L1/svc_1. Existing PSM client interruption left commands running per ot-run, do not duplicate; collecting outputs. Clock TT/FF spines exist, die closure NOT established.

09:10 PDT CODEX: CLOCK fallback is dedicated shared seam drops: common H-tree leaf -> matched short bifurcation (<100um last segments) feeding face flops on BOTH abutting partitions; retain interior R4 grid. Current independent face trees leave multi-mm uncommon paths and fail OCV regardless buffer pitch. Prototype tasks: (1) emit seam tap ports/groups from exact face-register census in gen_phys/gen_rtl and clock_taps.tcl, (2) assembly clock joins the two seam ports to one leaf, (3) build smallest two-part seam with same extracted grid RC, compare TT setup/FF hold/spread and uncommon path vs present H-tree, (4) account die clock/PDN corridor. Do not credit ideal mesh or relax80ps. OWNER? production clock-interface contract and physically distributed seam-group choice need coordinator decision; frames/replay proceed meanwhile.

10:29 PDT CODEX: Actual-metal bump fix merged4809ba262a (toolb475e57a6a+author66f241a303). OldheadPSMFAILEDVDDconnectivity/isolatedM9sourcepins; oldS81PSMinterruptedpdngen. Newbumpsquerysame-netactualM9SWireboxes,pinnedOpenROADtoyPASS exactoverlap. Freshcurrentheadr3abstract44W/11164sources rendered/reviewedPSM, runningintel2 scratch2.../codex-s81/trial_head_psm_c1,client2074292,ot-run256GB16threads. NoIRresultyet. ClockHtreefailsOCVseamrule; sharedseamdropfallback remainsactionableOWNERinterfaceitem.


CODEX 2026-10-24 11:24 PDT: HeadPSMc2 actualM9sources11164/232cachedcolumns, pdngen160s/bumps468s/connectivity1762s. BothVDD/VSS PGcheckPASS; VDDIRanalysisstilllive, noIRPASSclaim. Savedpdn_grid/pdn_bumpsODB supportsresume. EarlierheadPSMisolatedbumpfailure fixed actualmetalalignment; Htree80psfailure hasexplicitneighbor/sharedleafphysicalfallback, noidealcredit.

## PARKED 2026-10-24 18:56 PDT
- branch claude/trial-s81-1024 @ c2713abad0 (pushed; = main 7d75427c59 + WIP: die_trial.py fabric-latency + irwin, fabric.py
  S81 core_pins fix, results/die_trial_1024/{s81,s81_head}/trial_wip.json). NOT merged (WIP, not gated).
- LIVE jobs (mine, ot-run from localhost; leave running, collect):
  intel1 /srv/opentallas-scratch2/claude/trial-s81/s81/fabric_TT and fabric_FF (s81 die STA budget mode, 2.99M flops, 2.39M nets)
  intel2 /srv/opentallas-scratch2/claude/trial-s81/s81_head/fabric_TT and fabric_FF (head: GRT done 351 s, overflow 0; STA RC stage)
  local ot-run clients: pids 2212244 2213653 2214583 2215541; logs ~/coord/part-cap-logs/trial-s81*_fabric_{TT,FF}.log
  Result files: fabric_TT/sta_grt_TT_max.wns, fabric_FF/*FF_min*; summary.json.
- RESULTS so far:
  GRT on abstracts: s81 455k nets overflow 0 (3m16s/18.8 GB; still 0 at 2.5x less ft share); head 33.6k nets overflow 0 (48 s/5.6 GB).
  Die H-tree (nominal, gate rule): seam skew s81 TT 50.9/FF 43.8 ps PASS; head TT 81.9 ps FAIL(>80)/FF 78.8; in-partition tap
  spread ~100 ps (s81 104.5 TT, head 96.5); insertion s81 6.16 ns TT, head 3.81 ns TT. OCV3% INFO: s81 372, head 224 ps.
  IR (window PDNSim, 0.15 W/mm2, die C4 150 um lattice): interior worst 30 mV (4.3% of 0.7 V) both dies; over SerDes IO
  windows (no power bumps) worst 235 mV s81 (WS0/WS1) and 270 mV head (HOST0/HOST1/WS0) -> FAIL: needs power bumps/
  PHY own supply in IO windows (or the window load is wrong: PHY power not modelled separately).
  Full-die PSM: head (Codex c2) SEGFAULT in psm::IRSolver::solve at 119 GB after 2.4 h -> full-die PSM not viable; window PSM.
- FAILURES/notes: die_sta.py per-tap generated clocks did not finish >4 h (stopped; FYI DIE-STA). I used
  'pkill -u ubuntu -f run_sta.sh' on intel1/2 once (could have matched others' run_sta.sh; none known).
- NEXT: collect fabric TT max / FF min WNS (gate TT setup / FF hold 60/25); render IR window maps + Read them; write
  results/die_trial_1024/<die>/findings.md + geom_review entry; share with S81/S81-HEAD/DIE-STA/PART-CAP; merge.
- OWNER?: (1) head die-tree seam skew 81.9 ps TT > 80 -> accept shared seam drops (Codex proposal) or tighter tree;
  (2) power bumps over SerDes IO windows (IR 235-270 mV there).
