# SVC H8 RTL takeover 2026-11-08

CODEX took over: R5 H8 parameterization and exactness proof on codex/svc-rtl-0222, epyc4 /srv/opentallas-scratch3/claude/codex-svc-rtl-0222/repo, base c477959f3c. Predecessor uncommitted diff and four role ROMs copied; source unchanged.

## CODEX notes
- Collected irg probe already documented by predecessor: 525245 cells/chunk, 110474 flops, 68134 um2. No new physical build needed for this estimate.
- Found stale protocol from pre-02:19 compiler agreement: SMJ filtered every kind by pass, which drops final SO for half the heads; SOT also filtered by pass. Own form now filters SE kind4 only, broadcasts final SO and single SOT to all heads. H16 default unchanged.
- Running minimal real-arithmetic H8 score-exchange bench plus order mutant, via ot-run --hosts epyc4 --mem24 --threads16. Host dir /srv/opentallas-scratch3/claude/codex-svc-rtl-0222; local unit log coord/tmp/codex-svc-rtl-0222/sx.otrun.log. This proves tree/tap remapping before full attention proof; not a slice closure claim.
- Next: collect bench; fix lint and run minimum H8 two-pass attention vs H16 arithmetic/protocol lockstep, mutants; report measured P path constants to compiler. H16 identity proof open. No P&R launched; POR event deferred under watcher rules.

## 02:32 collection and fixes
- Hub WIP branch codex/svc-rtl-0222@8d9b741c58 preserves predecessor work and two protocol fixes. This is not READY; full exactness/area form incomplete.
- Found production-rate error in predecessor compiler estimate: H8 fold emits one 512-bit P word every 2 cycles, engine consumes two words/cycle. Tail-safe accumulation lag = 2*(npw-1)-(npw-1)//2, npw=ceil(T/4); 47 cycles at T128, 239 at T640 (compiler agent derives/tests exact tail). No frame-lag H8 price invalid. Actual P_ARR/PIO/latencies remain uncalibrated.
- Found incomplete area cut: H8 patch leaves 16-lane ot_s81_su_sms unchanged. SVC-SM child now implements 8physical/16logical folded SM; no reticle-fit claim until measured.
- E4 own queued client3592809 canceled before admission and SX moved to E6; no other job touched. E6 SX unit oth-ubuntu-3115456-1794133890 (24GB), calibration unit oth-ubuntu-3067358-1794133673 (32GB). Production H8x2/H16 engine-only miter launched via own client3616789, 64GB; no full slice/physical release.

## 02:49 component results and source
- Actual engine candidate PASS T128/T640 with static paired-word feed every2cycles; T640 oldstride1 FAIL37 refusals evenPO800 and noPV. T128 candidate firstPV observedrc907..914; T6401035..1042 (POprobe800, actualfirsthandshake801). Same74cycle engine-only additive latency beyond8ceil(T/32); keepexistingclosingKPV78, no tightercalendar adopted. Fullrecord branch results/rtl/s81_r5_h8_1108/engine_stride.json.
- Supersedes analytical47/239 cycle accumulation for oldstride1: safe H8 stride2 requires lag32/160 atT128/T640. Compiler parent mirrors it. Native P_ARR/PIO/SOT still uncalibrated.
- Actual decoder/MORE control PASS, with arithmetic testdouble and explicitlandingpreload: hb_h from precedingATTN_Q selectsSE, finalSO broadcasts, MORE1preserveslanding/open and suppressesdone, MORE0closes. Threecontrols(headswap/SOdrop/MOREoff) failed4/2/1errors. E6unit3354223-1794134740 protocol_more; no fullnumeric/producerclaim.
- Published895f5d1506 includes hb_h interface and feed2. Prepared H8-only foldedSM overlay from7aec3929d4 atsameu_smsname; originalH16SMS untouched. FullSM proof stillownedSMchild; noPOR/noP&R/noSIGNEDclaim.
- StrictWIDTH FAIL10 inheritedenginewarnings (lint8.log). SELRANGE-only lint PASS(unit3164037-1794134092), not a strictWIDTHpass.
- SX initialbench oracle incorrectlyusedH8localhead asglobaldimtile; correctedsourceonownE4branch while existingE6buildcontinues. Collect first result unchanged, then rerun correctoracle withsplitC++output. RealSXH8tree not yet qualified.
