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

## CODEX notes 2026-10-24 21:11 PDT / PARKED back to Claude
- Collected terminal trial fabric WNS (old tree / budget mode): S81 intel1 fabric_TT setup -637.68 ps and fabric_FF hold -42.03 ps; HEAD intel2 setup +133.76 ps / FF hold -75.90 ps. No G4 credit.
- S81 cause: s_2S_C__st__ft0__39__1 -> stage2, 133.5fF cap, clk-Q364ps + wire759ps, receiving slew2623ps and setup252ps; needs real wire repeaters/station geometry correction. Head worst tW5b10->tW5b9 has capture74.6ps late versus31.7ps data; shared clock branch + real hold insertion needed. Sent causes to S81 parent; CLOCK rebuilding tree already.
- Full head PSM c2 remains historical SIGSEGV119GB; use PHY-domain/window method. No trial rerun launched.

## CODEX notes 2026-10-25 02:42 PDT
CODEX took over PHY window IR on codex/trial-phy-1025 (own sparse WT /srv/opentallas-scratch/claude/wt/codex-trial-phy). Existing xdie3/head3 plans declare separate VDDPHY domains but legacy die_trial.py ignores domains. New tools/die_plan/phy_ir.py selects exact declared domain mesh+dedicated45um PG rows; explicit uniform density0.15W/mm2, source plan xdie3@69f1ce1a87 / head3@612e029779. Reviewed both grid/bump PNGs, record results/geom_review/codex_phy_domains_1025.json. PSM live epyc2:/srv/opentallas-scratch2/claude/codex-trial-phy/{s81_WS0,head_HOST0} via ot-run64GB/8, units oth-ubuntu-3688946-1792921265 and3688950, local clients3507123/3507125. PG generation done5/7s,640/1728 actual-metal sources. Waiting solver; actual PHY power/package signal-PG collision remain assumptions. Historical failed235/270mV records retained.
2026-10-25 02:47 PDT CODEX: also reviewed narrow vertical reserve-PHY WS3 (593.7x2303.76um,539 PG sources) to cover non-horizontal geometry; epyc2 HELD for falling disk so first admission correctly NOT RUN, no work was lost. Re-staged on intel2 scratch2 codex-trial-phy/s81_WS3; ot-run unit oth-ubuntu-2595048-1792921556 active. WS0 VDDPHY connectivity PASS; head/WS3 checking. The domains are standalone pathfinding: legacy whole-die tool still needs domain-aware regional grids/shared-ground coupling, and neighboring head PHY halos overlap127um, requiring coalesced same-net PHY region treatment.

## CODEX notes 2026-10-25 03:30 PDT
READY codex/trial-phy-1025 own commits1ac73030d (standaloneIR) +1f9559e2d (regionalPGAPI); cherry-pick onlythese, not inheritedtrialWIP. Three actualwindow PSM PASS: S81WS0 max2.55/avg0.746mV,377s6.17GB; verticalWS3 2.74/0.562mV,470s5.47GB; headHOST0 3.12/0.591mV,822s15.72GB, allatassumed0.15W/mm2/0.7V, bothnetsconnected. Separate16-loadmixedPSM PASS CORE2.96mV/PHY0.873mV. Explicitcontaining-macro PGproof PASS12480legalVIA78contacts,0cross-supplycontacts,all3netsconnected. Nativeper-instance mixed-domain connector emptygrid andsrouteassert failures diagnosed/preserved; explicit2x2same-nettechnology contacts closeprototype. Gen.py opt-inassembly --pg-map validatesrealM7pins, rejects missingVDDPHY/COREpinmetalinsidePHY; mockview --planned-phy-pg islabelledprototypeonly. Currentupdatedheadplan planned326partassembly/664bindings/12PHYpins generated, noG4credit. Existing schema/CP2tests20PASS; initialtestfailures weresparsecheckout missingrtl/lib/common_flow, fixed. AllIR/PGfleetjobsstartedbythislanearecomplete, noleftoverwaiters. Source2ndstepgen.py/gen_phys.py onlyassemblyPG/mockviewsections; clock/FTcodeuntouched.

## CODEX PARKED 2026-10-25 03:35 PDT
Claude reset; all own jobs COMPLETE, sourcecommits1ac73030d/1f9559e2d andhead7cbf009cc pushed. NativePMAgenerator nextstep scoped, noedits/jobs started; full handoff CODEX-LOG latestTRIAL/PHYsection. ReleasednativeVDDPHYviews remaintechnicalnextstep; prototypePGgatespassed, noG4credit.

## CODEX notes — Handoff to Claude 2026-10-25 03:36 PDT
S81 subgroup parked on RESET; all jobs preserved. Main summary in CODEX-LOG.md Handoff S81 subgroup. Exact FT source36915c557 pushed;178type cached outputG0C0E at epyc1 codex-s81-ft-exact/adopt178, not committed yet and predates nine fault feeders. New hcpost_h5 actualSIGNED TT+61.39/FF+3.68ps, views unintegrated. Core-pair relay metadata missing actualRTL remains held/assigned; one-stage legacy canonicalfaceFAIL remains, two-stage ruling20:42 ownedCLOCK. Child detailed handoffs follow; no newjobs/merges.
