# KV stand-in handback — explicit reset 2026-10-29 02:03 PDT

PARKED. No new work/jobs/merges after explicit reset. Live jobs continue, no kills. Child KV-KITS and PHY/PV child parked.

## Source and ownership

- Local owned WT `/srv/opentallas-scratch/claude/wt/codex-kv-1028`, branch `codex/kv-1028`, parked commit `d95cbd4b5` (push in progress at packet write; later receipt in CODEX-LOG). Prior checkpoints07980c5be/95ca6e9cb. Current source/results in `results/die_kv_24_1029`, images/manual reviews in `results/geom_review/codex_kv_ectl_1029`.
- Owned fleet WT intel1 `/srv/opentallas-scratch2/claude/wt/codex-kv-ectl-1028`, branch `codex/kv-ectl-1028`, at937af41f8c (07980 + isolated parser). Uncommitted materialized current event/recipes/ASTK source intentionally preserved. First owned compiler WT `/srv/opentallas-scratch2/claude/wt/codex-kv-1028` also remains. Never mutate predecessor `/wt/die-kv-23`.
- Shared parser52d07/our9b650 and START_OUT fanout e22038f2e are published main30a26e92fc. Shared macroCTS676/virtualFF179 published b0fd1009b1. Do not merge the entire die branch just for shared changes.
- Full ALL-kit handback: `/home/ubuntu/coord/handoff/codex_kv_kits_20261029_0203.md` (branch codex/kv-kits-1028@6313b119d). PHY/PV child packet `/srv/opentallas-scratch/claude/wt/codex-kv-pv-clock-1029/results/codex_kv_pv_clock_1029/PARK_RESET_HANDOFF.txt` @2e5e7d96a. Use these for exact AHUB/SYS_C/HHP/PHY/CDC/core_tx/e0/PV unit paths.

## Actual clock and die event

- Inherited KV23 chain completed: bind7 strict PASS160parts/58types/2545crossings/430554bits/0errors; VDH512banks/2078members PASS; Voffset36 PASS; constants40OK2WARN. Its peer24/24 and mutant8/24 are the historical QCv6 C2,2,2,3,2,2 cohort, not current ONE-QC.
- Mixed proof final intel1 `/srv/opentallas-scratch2/claude/codex-clock-components-1028/proof/tap_arrivals_{TT,FF}.json` includes both edges all1920taps/15424nodes. Parity-safe source7caab/ea614; earlier b154 export HOLD superseded. Actual89BUFx24 have54even/35odd inputs; no invented fall edge.
- Own runtime intel1 `/srv/opentallas-scratch2/claude/codex-kv-1028/{proof_mixed,ca_mixed_replan.json,sta_replan,gate_replan.sh,mixed_source}`. Generic physical-graph replan:3595dataCA PASS TT104.733..515.865/FF109.333..516.265;139START sampling PASS,0missing/guards.50D8->D4/1063configchanges, sched9742->9327, regions162->140. NUMBER independent f8bef47d4 PASS: everytap/node/bothsourceedges recurrence <=6.4e-12ps;139START minima76.23TT/58.03FF>=26.5. Published SPICE factors reused, no new characterisation.
- Die remains FAIL: conservative glue FF-50.98, real-kit+6.64, seam+17.29. Four signed e1/e2/e5/e6 views were already applied; retaining every-tap glue budget causes mixed failures (same actual e6->real e1 pair positive). No budget was dropped, no freeze/G5 claim.
- One event24 on actual graph equalises ECTL RT16..18 to17/18:14 existing K-request paths +1 aggregate14, no new partition/clock-tap IDs. Normal future compiler/R8 pricing still required.
- ROOT-approved q1/q2 ECTL outline233.28x172.8 BEFORE collector composition,64instances/+0.191103mm2/0cycles, Eface+17.28, clock108/86.4 unchanged. q0/q3 retain216x172.8. Stock event24r and widened event24w both compose58types/160parts/0placementfailures. Main-source successor event24w_current also DONE; sidecar byte-identical to prior numeric source. LP source archive ea614 lacked HEAD21 declaration; current source corrects those metadata errors.
- Final materialized candidate in fleet own WT `results/die_kv_24_1029/event_current_lc/plan_sites_astk.json` with sidecar adjacent. It includes qualified LC512bankdefinitions/256typecore slots,36 reached pin docs, SYS_C140 static strap sites, and exact2 ASTK malformed scalar-name corrections. `plan_sites.json` predates the last ASTK names only; `plan.json` predates SYS_C sites. Early `event/` is preserved unqualified history, not adoption target.
- SYS_C site inventory exactly equals actual bind7/current CA25straps/140bits; child count_sites.py checks names/widths, M5 PG-free/M4 tracks, macro+1um clearance,0cycles. Receipt in results24/sysc. Actual B24 parent manifest can reassert before adoption.

## Physical START gap — unresolved, separate from sampling PASS

- Full G0C retained FAIL229:44 missing cell estimates plus185 landing_contract errors. Current-source HEAD21+published e220 removes45 declaration/fanout issues. **140 actual registered START-control hops exceed405um remain UNFIXED**:32same-region cland_relay,108direct real START. StockKV23 already had121=32+89, so19 are new. Same actual-graph stock24 and wide24 have identical185 error strings; widening did not cause START damage.
- Worst same-region example origin to PHY_EN_0 ~2956um. Do not waive, tie starts high, or use nearest arbitrary clk_tN phase. All actual `_origin_rtl` root/origin/relay use native partition `.clk(clk)`, authoritative physical `t_<part>__clk`; data/core clk_tN can have a different phase.
- FLOW/canary_release owns generic reach repair, no duplicate implementation. Proposed each of160physical partitions its own origin (remove32long relays), boundedvirtual START stages, actual single-source launch+capture physical mapping, uniform START pins adjacent primary GLUE clock entry, preserve real hub_C root; full N/K/sched and whole programme price after change.
- Canary parked before graph emission/heavy job. WT `/srv/opentallas-scratch/claude/wt/codex-kv-start-reach-1029`, branch same name; already-written count_align_plan.py/test_count_align_starttree.py fixedlaunchmap/actualXY separation,23tests PASS, local parking commit692be66ac (not pushed), packet codex_flow_canary_release_20261029_reset.md. No actual retimed candidate/proof exists yet.
- Independent wide-geometry light review:64expanded cores/8HGtypes,0core overlap/0FTbit inside expanded cores; declared FT hop389.61<405. This is not actual native parent pin-to-pin connectivity proof. New q1/q2 P&R remains held pending that readout and affected START regions.

## Own ECTL jobs and results

All paths below on intel1 under `/srv/opentallas-scratch2/claude/codex-kv-1028/ectl`.

- q1/q2 original synth PASS, LECEQ10655/10595. Both actual source has4SRAMs, not old2-site recipe.233.28 new kits `wide_final/kits/qkd_ectlk_q{1,2}__233.28x172.8` GEN PASS, exact plan_pins bundled, KIT_PREFLIGHT0,4sites legal. No placement launched. Raw middle819pins reduce to392..529active unique nets+2ties; M5two-ended escape capacity conditional, actual GRT required. Source geometry image viewed by us and GEOM.
- q3 original `kits/qkd_ectlk_q3__216x172.8`:2SRAMs, LECEQ9742, PREFLIGHT0, PLACE DONE. Actual3_place+50GRT probe0overflow, r2r176.26/0bad, pinreg p90=8.14/max72.3/unreg0, clockreach184.46/body0.
- q3 AUTOFAIL fill0.0713/empty0.7327 preserved. Manual PASS-COND **CTS/prototype only**, because fixed1988pins+2FT, twoSRAM+std26%grossarea, height tight172.788halo, width shrink moves569E/902S pins and parent ABI. Exact reviewed images/reviews `q3_placed.png`, `q3_placed_review.json`; ROOT received paths. Not a SIGNED waiver.
- Published helper-refreshed mixed-source successor `q3_macrocts_trial` preserves old07980 RTL/place/LEC, source/helper_refresh.json old/new hashes and helper_overlay_plan b0fd. CTS DONE:macroclockcluster2/size2/diameter40, TTsetup+138.63. ActualCTS image `q3_cts.png` personally viewed, read-only50GRT0; all meaningful geometry metrics pass, lowfill AUTOFAIL retained.
- **q3 normal5ps GRT `q3_grt5_trial` terminal FAIL** unit1472372-1793263890: GRT-0183 maze heap-underflow/boxed local net u_b.g_s1b[1].u_r/net5445 after2264holdbufs; FFhold-58.79 persists (rs_d[523] endpoint flat after620..1120iterations). No retry after reset. Legacy helper labels setup as SS94.24, not used as closure. Need actual worst FF path and local buffer-growth/channel diagnosis before successor.
- Earlier q3 prototype accidentally invoked repair margin0 instead of kit5; marked diagnostic-only, preserved at q3_macrocts_trial, terminal same GRT-0183/FF-58.79 unit1463196. Never changed833/60/25 or250/202.5 frames. Correct5 successor exists; no kills.
- q0 original stock synth FAILshared297 due required published ECTL face transform. Corrected `fp/kits/qkd_ectlk_q0__216x172.8` BOTH faceguards1478 PASS, **formal LEC still LIVE** unit882113-1793259972, python PID893968, hyp10 last progressing. Check `tail .../lec_run.log`, `find .../lec -name 'hyp*_failed.txt'`; do not duplicate/kill.
- Current-source ECTL private-face miter nominal PASS11980edges/2672requests/2672scores/251lmaxchanges; mutant5789mismatches. Full source/reference actualHXK13/QKage91/RL80,0cycles. First sim runtime attempted oldDocker GLIBC mismatch; same binary on build host viaot-run PASS, no design failure.

## ASTK fresh current source — coupon passes, GEN not yet complete

- Not forgotten: old pre-slice ASTK kits/old bbf hold are not routed. Actual bind7 already contains composed master kv3_astk, so old six-member-note extractor fails legitimately. Reached23-source parent closure materialized; raw ASTK c6b9852... hash in results24/astk/source_receipt.json.
- Native ctl_s_g0 already includes timing/replica/AM35 fixes. New thin actual physical source uses published PORT_REGS1 tc/qo private copies, scalar common CK/reset, static strap landing,1692canonical physical pins.0command/token cycles; existing published external fault_b+1 only. No reapply of old timing/AM transformations.
- Nominal actual-composed/reference miter PASS4800edges/all4corners; PORT_REGS-off control FAIL4798mismatches. Exact6 instance-only renames verified for canonical existing zone-clock regex. Source in results24/astk/{kv3_astk.sv,kv3_astk_core.json,deps,source_receipt.json,miter*.log}; scripts astk_native_face.py/astk_face_miter.py.
- GEN first found actual canonical pin defect: literal `ck[None]` / `rst_n[None]`, sole such reached doc. New `cores/kv3_astk_pins_r26q4_scalar.json` changes only those2names, no coordinate/layer/outline/latency; all4parent cores point at it in plan_sites_astk.json. Source/CJ normalised correctly, old files and failedGEN preserved.
- Latest GEN `astk/kits3` stops because `--astk-zone-fences` requires `--astk-write-decode`. Do not blindly reapply write-decode to already-modified native source. Next synth-only generation can omit physical fence/tap flags, then explicitly restore proper published source-aware physical hooks before P&R. No ASTK synth/P&R was launched. Planned image astk_planned.png was personally viewed; source core is macro-free and entry reach<=200, but no placed census or closed view.

## Logical B24 work

- intel1 runtime `/srv/opentallas-scratch2/claude/codex-kv-1028/event24_bind`.
- Elab t1 PASS73modules/38libs,0ambiguous/undefined. Initial bind operationally missed untracked composition_heads_astk_1clk_oddstrap.json, staged exact predecessor file. Next t1_stage2 FAIL only30R8_STALE as expected after event, no logical error. Own new out originally lacked asbuilt.json; exact immutable elaboration files copied, no repeated elab.
- New R8 regen PASS3835groups,0unequal/inversions,234replica sets0unequal, write-group PASS,79167padFF/max26. Inputs/results committed results24/r8_t1.
- Latest t2 FAIL operational missing results/die_kv_16_1028/pv_v_pads_b4.json. It was previously staged then sparse checkout/cherry-pick removed the out-of-cone tracked file. Add the correct sparse path/stage exact previous file before bind-only retry; no new elab needed. No retry after explicit reset. No final B24 strict bind/image/peer/fullprogramme claim.

## Other kits and tokens

Read full child packet for exact all-lane jobs. Highlights:
- e1/e2/e5/e6 SIGNED/versioned flow-20261029-a-kv; e0 stilllive AP, no missing-view closure claim. core_tx164.16 current3627facepins PASS/LEClive. Old276outline superseded.
- PV R0 terminal actualFF~-107.74/1658EP; exactCTS path s1_bad→s2_bad has~103ps cross-independent-root skew, data43.75. Family-atomic equal-count balanced source2265 preserves all32FP families/3658nonFPgroups, original7443/7442 counts, roots/masters/stages/SRAMbranches/ports unchanged. Deck-only starts used OLD3_placeownership, explicitly INVALID. Correct input must rebind actual ownedODB and census everyroot/family before CTS; distinct corrected input may run alongside invalid old scopes, no kills/live mutations. At park only binding jobs live, no verified corrected physical start.
- PHY legal raw-capture source merged main (no predicate-beforecapture shortcut). Route54d terminal NOTSIGNED TT+82.76/FF-11ps63EP/slew51TT64FF/DRC0; actual FF-sync/data-only hold+DRV loop fix requested sharedFLOW. No blind reroute. CDC_CH4shared→0; CDC_PC22→18 reserved constant pads, coherent18bit ABI projection still needed.
- SYS_C current bind7 standalone proof live; fresh syn portbind140extra was missing static strap sites, now delta prepared/integrated, not waiver. AHUB current3-clock627pin synth/preflight PASS/LEClive. HHP fresh currentfMY2991pins/4FTsynthPASS; duplicateCORE_CLOCK helper made Slang UNPROVEN, narrow6313 fixREADY then matching actual mapped-gate proof live.
- Token owner is /root/tokens_qwen. MissingROM exactbind5content recovered; own corrected runs then cancelled onlyexactowned5PIDs after missing29pst START provider diagnosed. Originals untouched/unqualified. Realhubroot+29virtualstages87FF provider now delivered; one top-only token successor ownedTOK, no duplicate.
- Phase packet intel1 codex-kv-kits-1028/start5 has regional_clock_contract.json, regional160 top/TT/FF benches. Original128input clocks alias32PC toPHY although160physicalparts/1920taps. Thin32input separation and all160measuredbaseclock rise/fall+29actualSDFstageA/Y are functional timing diagnostics only: within-part unmodelled leaf spread~83ps/providerloads prevent G5. Current nominal run untouched.
- CurrentONEQC119 ↔ KV7 component pair PASS24configs/35layers with STATUS45/servicepad5, C13 vs old8, layer7061, period258048 unchanged after768alignment. Native7g oldQC compiler293376 COMPILED_NOT_QUALIFIED; TOK owns current-QC native reprice: servicepad91 vs86, same293376 so far, but HEAD_PREP12 invalid actualminimum21; must use actualHOST join, no guessed scalar substitution or measured-rate claim.

## Immediate continuation and OWNER

1. Collect q0formal and all child live proofs/AP rows, preserve failures. Diagnose q3 trueFF/buffer-congestion before new physical attempt.
2. Finish generic native-clock physical START topology, then fullCA/G0/realview/programme reprice. Do not claim current139sampling pass solves140physical links.
3. Rebind B24 only after its missing input staged; new START topology may supersede it. Continue ASTK synth-only/current source and HHP/PV/PHY structural successors, never old held source.
4. No OWNER questions raised by this lane. CDC_PC18reserved padding projection is a known coherent plan/ABI delta, not an implicit waiver.
