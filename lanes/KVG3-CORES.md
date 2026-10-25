# KVG3-CORES (sub-lane of KV-G3): hardened views of the KV die's planned hard cores
Updated 2026-10-24 07:40 PDT

## Scripts (~/wt/kv-g3/physical/die_plan/qwen_kvsys/cores/harden/)
kv_core_rtl.py (core RTL + split partition + flattened-connectivity equiv + lint + structural identity over all slots),
gen_core_kit_kv.py (+ run_kit_kv.sh, corners.tcl TT/FF/SS STA + ETM, pin_audit_core.py, recipes_kv.json); sdc_lint gate PASS.

## RTL (out: localhost ~/scratch/kv-g3/cores/rtl/<type>/)
hub_Eo/hub_Wo/hub_C/pc/pv split equiv PASS; hg/hgi rerun (strap const fix) -> rtl2/.
Added pins vs plan pins files: astk ck+rst_n (each); head_eighth e0/e2/e4/e6 hid[1:0] strap (head-dependent constant);
ectlk so[1..12] gap bits (tied 0). kvs_pc: 2 clocks ck+hck co-timed as one 833 ps clock (no HBM period in plan).

## Running (ORFS finish + abstract + corners), launched ~07:45-08:05 PDT via ot-run
- intel2:/srv/opentallas-scratch2/claude/kv-g3/cores/kits: kv3_astk_{EN,ES,WN,WS}, kv3_head_eighth_e4..e7, qkd_kvs_pc_h_head_p
- intel1:/srv/opentallas-scratch2/claude/kv-g3/cores/kits: kv3_head_eighth_e0..e3, qkd_kvs_pc, kv3_pv_pair
- epyc3:/srv/opentallas-scratch/claude/kv-g3/cores/kits: qkd_ahub
- localhost:~/scratch/kv-g3/cores/kits: qkd_ectlk

## Review before route (owner 08:05) — 09:20 PDT, author self-review (GEOM-REVIEW to second)
Pictures: ~/wt/kv-g3/physical/die_plan/qwen_kvsys/cores/harden/review/ (tile 3_place renders + partition core/pin renders,
render_part_cores.py flags pins facing a core < 60 um away that they do not connect to = DETOUR). Records: results/geom_review/*__kvg3cores_*.json
- astk EN/ES/WN/WS: PASS (fill 49%, no bin > 0.7, face flops at pins p90 8 um, 0 detour, ck/rst_n on W face toward tap)
- head_eighth e0..e7: PASS-COND (outline oversized: fill 22-33%; <= 337 detour pins per 34.56 um gap) -> plan: shrink outline
- qkd_ectlk: FAIL at plan placement: 1818 S-face pins detour in the 25.92 um gap over head e6/e7 (channel over capacity)
- qkd_kvs_pc: FAIL at plan placement: kvpc2/kvpc3 1107 S pins each detour in 25.92 um gaps (lower 750 um of kv3_pc empty) -> move kvpc0/1 down
- kv3_pv_pair: tile PASS-COND; FAIL at plan placement: p0/p3 1030 pins each detour in 25.92 um gaps (top 450 um of kv3_pv empty) -> spread pairs
- qkd_kvs_pc_h_head_p, qkd_ahub: PASS-COND (0 detour; tile review pending at 3_place)
Running jobs continue as pathfinding (fixes proposed are placement moves -> core views stay valid); no new submissions until KV-G3 rules.

## GEOM-REVIEW findings (2026-10-24 09:05 PDT)
See KV-G3.md: astk x4, head_eighth x8, pv_pair PASS-CONDITIONAL (records in results/geom_review on claude/geom-review-1024); straps-as-RTL-constants make them distinct netlists; head_eighth odd class wastes ~55% of the slot. kvs_pc / ahub / ectlk / kvs_pc_h_head_p: NOT REVIEWED (no placement yet).

## CODEX notes
- Existing 16 core runs span intel1/intel2/epyc3/local; results collection ongoing. Plan placement FAILs for ectlk/kvs_pc/pv_pair handled by main KV v3.8w spread revision. Astk/head/pv tile reviews conditional. Next collect routed corners/signoff and fix actual timing failures.

- CODEX collected kv3_pv_pair final GRT FAIL (GRT-0116): total congestion1692 (M2 631/M3 728/M4 264/M5 69), max H/V4/6; 166096 nets, wirelength1,138,423um. Layer cap M5, overall usage21.67%, so local bottleneck rather than die-wide capacity. Needs actual congestion/macro channel review and local placement revision before re-route. Other core jobs still live (head e1/e2 DRT, e0 GRT, kvs_pc optimization).

- CODEX pv_pair fix candidate: visual review of existing CTS image finds saturated N-edge band with27%empty/32.4%overallfill. Own place-only density0.45 candidate live intel1:/srv/opentallas-scratch2/claude/codex-qwen/pvpair_density45 (32GB/8threads ot-run; log localhost codex-qwen/pvpair_density45.log). Geometry/pins preserved; review new placement before anyroute. Root coordinator now owns hub_Ei vG diagnosis.

- CODEX: pv_pair density45 candidate still GRT FAIL2548overflow (M2 982,M3 1254,M4 168,M5 144), worse than1692original despite clean global place review. Same380.16x190.08outline and1652northpins; demand remains routing/pin-limited. Next expand geometry/channels with safe current SDC; preserve original and density45 failures.

- CODEX completed-run collection: head e1..e7 and astk4 routed/pinauditPASS but TT/FFcornerSTAFAIL emptyLIB_FILES, diagnosed pinned ORFS print helper emits NAME: not NAME=; runnerparserfix and failclosedguard in ownWT. Head e0 GRT5555, kvs_pc10284,pc_h_head_p4324overflow;allM5recipe. ectlkGPL0305 gradientdivergence after534percentroutabilityinflation; geometry has1818Sfacepins, proceedplace-density/routingcapacitycandidate afterreview. ahubstillDRT60percent~65kviolations. SafeSDC/Libertycornerrecovery of head e1 liveintel1scratch2/codex-qwen/head_e1_corner_recovery.

- CODEX M7PVfix: GRT PASS0overflowM2-M7/14.72percentusage; sameRTL/pins380.16x190.08density.45,mainplancorebudgetM7. DRT/TTFFfinishnowliveintel1scratch2/codex-qwen/pvpair_m7 usingfixedrunner/safeSDC.

CODEX progress: Freshhead_e2 keep-kitLIVE intel2:/srv/opentallas-scratch2/claude/codex-qwen/head_e2_keep; actualexistingrelayFF preservation,currentgenerator. ASTK4same-edge read-controlreplicas(+80FF/core,0cycles) gate9992comparisonsPASS/4982mutantmismatches; worstWNrouteLIVE intel1:/srv/opentallas-scratch2/claude/codex-qwen/astk_WN_r4. ECTLKplace-onlybins256LIVE samehost:/srv/opentallas-scratch2/claude/codex-qwen/ectlk_bins256; inflationstillbad, routingHELDpendingnewplacementreview.

## RESUMED 12:15 PDT (Claude), adopted Codex live jobs (no duplicates launched):
- intel1:/srv/opentallas-scratch2/claude/codex-qwen/pvpair_m7 (M7 recipe, GRT 0 ovf; in DRT 5_2_route)
- intel1:/srv/opentallas-scratch2/claude/codex-qwen/astk_WN_r4 (read-control replica candidate; 5_1_grt)
- intel1:/srv/opentallas-scratch2/claude/codex-qwen/head_e1_hold40 (old kit hold40 retry; DRT)
- intel2:/srv/opentallas-scratch2/claude/codex-qwen/head_e2_keep/kv3_head_eighth_e2__285.12x285.12 (keep kit; 5_1_grt)
Original 16 KVG3-CORES runs: all ended (Codex collected: none SIGNED; see CODEX notes). Open from KV-G3 ruling 09:xx:
head_eighth slot shrink 285.12 -> 216 (post_v38x + new pins files + re-review) — next.
- 2026-10-24 12:30 PDT ELEM-QK (fork ELEMQK-ASTK) runs ASTK EN/ES/WN/WS variants (hm55 / r4h / r4hs) under /srv/opentallas-scratch/claude/elem-qk/astk (localhost|epyc3) and ECTLK CTS variants e1-e3 at intel2:/srv/opentallas-scratch2/claude/elem-qk/ectlk; Codex astk_WN_r4 left alone, collected when done.
- 2026-10-24 12:31 PDT FROM ELEM-QK (fork ELEMQK-HOLD, COORD 12:4x): running warm FF-hold ECO variants a/b/c (FF-only m0 / FF-only m3 / MCMM tc+bc m0 setup-guarded) on the completed 285.12 head_eighth e1..e7 routes (copies; your kit/recovery dirs untouched) -> signoff.py tt,ff. Calibrates the hold recipe for your 216x216 re-kits; please don't duplicate. Dirs localhost/epyc3:/srv/opentallas-scratch/claude/elem-qk/hold/<head>/<v>.

## 13:25 PDT v3.8x head_eighth 216 (plan committed 5637117270, on main c98b74b466 via KV-G3)
Placement review (author): records results/geom_review/kv3_head_eighth_e*__kvg3cores_<hash>.json, pictures
cores/harden/review/kv3_head_eighth_e*_216_placed.png. Fill 40-59%, no hotspot, face flops p90 6-9 um.
e1/3/5/7 PASS; e0/2/4/6 PASS-COND: face_guard DATA fails RTL-intrinsic (f_t2->f_t3 feedthrough 41, e0 gf_in unregistered 28)
-> signoff face_guard FAIL expected (NEEDS_RTL / typed ft contract). Finish runs (M7) launched 13:25:
intel2:/srv/opentallas-scratch2/claude/kv-g3/cores/kits38x/kv3_head_eighth_e{0..3}__216x216 (queued for memory),
localhost:/srv/opentallas-scratch/claude/kv-g3/cores/kits38x/kv3_head_eighth_e{4..7}__216x216. Final step signoff.py.

## 14:10 PDT results
- kv3_pv_pair (adopted Codex pvpair_m7, M7/density .45): routed DRC 0/ant 0, pins 1652/1652; signoff NOT SIGNED:
  TT setup +2.32, FF hold -10.75 (470 ep), DRV slew TT 66/FF 96, pin-flop insertion 355.6 vs 250+-40, face_guard shared 3/dropped 1.
  Views abstract_only in physical/ref_tile/kv3_pv_pair/views/kv3_pv_pair (commit b494c0dd31). ORFS finish died at GDS merge
  (SRAM GDS missing) -> run_kit_kv.sh GOAL=route/post added (macro cores must use route).
- Systemic for SIGNED (all KV cores seen so far): FF hold ~ -10 ps after TC hold repair (Codex head_e1_hold40 tests margin 40),
  core-internal clock insertion > 250+-40 (needs a core-latency contract or larger budget: OWNER?), DRV slews.
Running: head_eighth 216 finish x8 (intel2 e0-e3 queued/admitted, localhost e4-e7); Codex-adopted astk_WN_r4, head_e1_hold40 (intel1), head_e2_keep (intel2) in DRT.

## PARKED 2026-10-24 (coordinator move to rtx-pro) — KVG3-CORES
Branch claude/kv-g3-1024 @229adce8f2 (local commits befed6a747, 229adce8f2 NOT pushed: lane rule "parent KV-G3 owns
push/merge"; earlier 5637117270/b1acb09077/b494c0dd31 — v3.8x already on main c98b74b466 via KV-G3). Untracked/modified
tools/die_plan/{face_flops.tcl,gen_phys.py,gen_rtl.py,kit_rsync.py,reset_taps.tcl,reset_tree.py} in ~/wt/kv-g3 are
KV-G3's WIP, not mine (left untouched).
Live jobs: none of mine. Codex-adopted, at generate_abstract (collect next): intel1:/srv/opentallas-scratch2/claude/codex-qwen/
{astk_WN_r4,head_e1_hold40}, intel2:/srv/opentallas-scratch2/claude/codex-qwen/head_e2_keep/kv3_head_eighth_e2__285.12x285.12.
Results (signoff.py, all DRC 0 / ant 0, clock PASS under the hard-core latency contract, none SIGNED):
- head_eighth 216 (v3.8x, M7): TT setup e0 +25.3, e1 +36.6, e2 +1.6, e3 +46.3, e4 +10.1, e5 +15.9, e6 -12.1, e7 -25.0;
  FF hold -4.3..-7.5 on all 8; face_guard FAIL e0/e2/e4/e6 (RTL), PASS e1/e3/e5/e7. Kits: intel2:/srv/opentallas-scratch2/
  claude/kv-g3/cores/kits38x/kv3_head_eighth_e{0..3}__216x216, localhost:/srv/opentallas-scratch/claude/kv-g3/cores/kits38x/
  kv3_head_eighth_e{4..7}__216x216 (signoff/signoff.json, views/). Not yet collected into results/ / ref_tile views.
- kv3_pv_pair: NOT SIGNED (FF hold -10.75, DRV, face_guard; clock check was pre-contract) views abstract_only (b494c0dd31).
Done this session: signoff.py hard-core latency contract (COORD ruling 1, test_signoff 22/22); kvs_pc 833 ps labelled
assumption (ruling 4; HBM period asked of KV-G3, no answer yet); RTL ruling 2 WIP 229adce8f2: frontq PORT_REGS=1
(0 cycles; miter PASS 6000 edges, mutant FAIL) and ktree_lk PORT_REGS=1 (g_f +1 edge fault path; bench PASS, mutant
FAIL) — opt-in, defaults unchanged, NOT yet wired into the core kits. (Note: frontq mutant shows port0 unchanged;
check genvar slice in the mutant before relying on it.)
Next: (1) collect the 8 head 216 + 3 Codex runs (collect_core.py -> results/ + ref_tile views); (2) ruling 3: compare
head_e1_hold40 FF hold vs the -4..-7 ps here; if it closes, make FF-hold margin the default core recipe; (3) wire
PORT_REGS=1 into kv_core_rtl.py head_eighth members (+ KV-G3 partition binding, price g_f +1 for e0) and rebuild kits;
(4) e6/e7 TT setup -12/-25 at 216 (review timing paths); (5) pv_pair/kvs_pc/ectlk/astk reruns on v3.8w/x geometry (route goal).
OWNER?: kvs_pc HBM clock period / CDC SDC vocabulary (KV-G3); PORT_REGS adoption in shared leaves (S81 ref tiles bind the
same r4.sv; defaults keep them unchanged).

## CODEX notes 2026-10-24 21:09 PDT
CODEX took over: KV core ECO collection and failed-route repair on codex/kv-cores-1024 (from claude/kv-cores-1024r@f3318adf3). New SIGNED views: head_eighth e5/m8 TT +24.26 / FF +4.31; e7/m8 TT +25.30 / FF +3.13, DRC/antenna0, sdc_lint/face_guard/DRV PASS. Collecting views. e6 b8+m8 FAIL DRT-1231 at same FAx1 CON pin (u_g_t_13_u_l8.g_d[6].u_p/_1086_): local pin-access defect after warm ECO, diagnosis active; other head/PV ECOs still routing or signing.

CODEX PARKED 2026-10-24 21:10 PDT on reset: two SIGNED collected views e5_m8/e7_m8 under localhost:/srv/opentallas-scratch/claude/codex-kv-cores/collected; not committed/published yet. e6 pin-access diagnosis and next local legalization in CODEX-LOG/handoff.json. No new route launched; own worktree checkout PID2026402 still finishes in background.

## CODEX notes 2026-10-25 02:38 PDT
CODEX took over: KV hard core collection and runner fixes on codex/kv-cores-1025. Existing pv_pair warm ECOs et_m5_dp/et_m5_dlr/s20_m5_dp/s20_m5_dlr remain LIVE on intel1:/srv/opentallas-scratch2/claude/kv-cores/eco/kv3_pv_pair (no duplicate route or cancellation). Fixed report-only core boundary guard: fail before floorplan using signoff typed control context on both raw synth and 1_synth.odb netlists; missing ODB/export fails closed. Added standalone SELRANGE gate (FAIL stops; frontend ERROR remains NOT RUN), and runner propagates final signoff status. Real fd3_et raw netlist PASS; invalid-control-context mutant and missing-netlist checks reject; bash syntax PASS. Existing pv_pair source failure remains TT -40.94 / FF -45.53 ps, output hold dominated by fixed early clock compensation; running ECOs are its pending fixes.

2026-10-25 02:43 PDT CODEX: core runner fixes pushed codex/kv-cores-1025@67327101f, historical r2 collection @3c74b406c. Started approved e2 PORT_REGS synthesis-only pilot intel2:/srv/opentallas-scratch2/claude/codex-kv-cores-1025/head_e2_portregs via ot-run mem32/thr8, unit oth-ubuntu-3774673-1792921331 (rtx-pro client3511844). Source parent kit copied, old freeze retained as source_parent_freeze.json; r4 leaf from claude/kv-cores-1024r and frontq .PORT_REGS(1), +123FF,0cycles, no pin/outline change. Existing 216 placement image reviewed (harden/review/kv3_head_eighth_e2_216_placed.png): macro-free,41%fill,no bins>.8,pin-regp907.1um; this only clears geometry sanity for synth, native dec17 kit still needed before route. SELRANGE PASS40files/0unwaived, synthesis mapping LIVE. P&R HELD until dec17.

2026-10-25 02:48 PDT CODEX: e2 PORT_REGS1 synth pilot reduced original boundary shared42/ft41 to shared1, but still FAIL: frontq pack_fault sticky-feedback flop also drives pin. Added separate synchronous fault-port flop with same sticky next-state (+1FF,0cycles), smallest lockstep6000edges PASS0mismatches; dedicated stuck0fault mutant FAIL5996mismatches (unit intel2 oth-ubuntu-2199813-1792921520). First fault-copy synth still shared1 from a kept alias wire creating BUFx2 on port chain; removed keep alias (sync vs async reset already keeps flops distinct). Successor synth-only LIVE intel2 scratch2/claude/codex-kv-cores-1025/head_e2_portregs_faultdup2 (local exec24876); failed pilot dirs kept. Also fixed standalone signoff /work import IndexError via repo-path fallback (a94900250 pushed). No P&R launched.

2026-10-25 02:52 PDT CODEX: even-head frontq boundary fix READY codex/kv-cores-1025@98c25c4a8 pushed. Actual e2 PORT_REGS1 + fault-pin copy synth PASS raw1344/1344 + ODB1344/1344 (unit intel2 oth-ubuntu-2742921-1792921692), SELRANGE PASS40files. Miter6000edge0mismatch; stuck0fault mutant5996mismatches. Frontq total+124FF,0cycles (e0 separate ktree fault+1 unchanged). New r4 source must be consumed with .PORT_REGS(1) on native even-head re-kits. No P&R pending dec17; not SIGNED. Sources/results in branch; failed pilots retained. Next ASTK face fixes (tc4aliases + fault input landing).

2026-10-25 03:21 PDT CODEX: ASTK boundary repair READY codex/kv-cores-1025@93a029930 pushed. coregen --astk-face-ports handles ctl_s/_p with independent tc/qo same-edge launch copies; faultb unreset landing+valid adds1external-fault detection cycle only (localfault unchanged,0nominal tokencycles), WN measured+78FF,total24684. First proto removed60feedthroughs but exposed16sharedqo bits+sync-reset logic atb; fixed with fullprivateqo launch and unresetb+valid. Final raw1690/1690PASS; synthODB initially dropped10unusedaq captureFF due partition-only keep regex, core-only keep/release hooks now PASS ODB1690/1690 (epyc3 astk_WN_keptfaces, unit oth-ubuntu-2506831-1792923489). SELRANGE29filesPASS. Small6000edge TC/fullQO andfaultcontract PASS, mutants24000/5969/1482mismatches. Evidence/modeldelta in harden/results/astk_faces_1025. Nativebind must budget+1externalfault collection AGE/observation edge; no P&R untildec17. Also native frontq_p refreshed dfd4acde9; prior reports0cycles refer frontq/newclone only, RETAIN approved+1parent PORT_REGS faultcycle. Next ECTLK3source localCTS pilot; CLOCK confirms ownership.

## CODEX notes — PARKED 2026-10-25 03:36 PDT
Claude resetorder received; stoppednewwork safely. Ownbranch codex/kv-cores-1025@24f08b1b1 pushed, clean. Frontq/ASTKpreflights fixed; nativebinderintegration owed. ECTLK3root sourceflag/proof ready but lateactualsynth FAIL rawshared446/dropped96 at epyc3:/srv/opentallas-scratch/claude/codex-kv-cores-1025/ectlk_3root_preflight (noP&R); finerdiagnosis leftexplicitlyOPEN inCODEX-LOG handoff. INFRA-FLEET ownsso401+parentpacking. Inheritedpv_pair 2GRT0013failures/2lastobservedlive preserved. Fullhandoff CODEX-LOG.

## KV-CORES lane (Claude, fresh) 2026-10-25 04:37 PDT
Branch claude/kv-cores-1025r@3818de1fac (epyc1 wt /srv/opentallas-scratch2/claude/wt/kv-cores-1025r), READY filed. Collected: inherited pv_pair warm ECOs et_m5_dp/et_m5_dlr/s20_m5_dp/s20_m5_dlr all FAILED in 5_1_grt (GRT-0013 merge x2, SIGSEGV DRT pin access in incremental GRT x2) -> verdicts kept (scratch localhost ~/scratch/kv-cores-1025r/eco_failed), dirs deleted; warm ECOs are dead for pv_pair -> structural rebuild. Deleted failed qkd_ahub 734x540 run (11 GB, GEOM FAIL 19:44).
Sub-agents: EVENHEADS (e0/e2/e4/e6 PORT_REGS+fault clone re-kits), ASTK-ECTLK (astk x4 face ports; ectlk 3-root preflight shared446/dropped96), PV-PC (pv_pair clock-entry/latency structural fix, kvs_pc/_h_head_p die-clock re-kits, re-sign REUSE-CLOSED kvs_ctl/pv_join + ahub children).
Lead: qkd_ahub r2 macro-composed kit (4 x ot_nhb_zh + recip FIRM per GEOM PASS-COND 10-24 22:36) place+CTS LIVE epyc1 (ot-run unit oth-ubuntu-1598337-1792928187, kit /srv/opentallas-scratch2/claude/kv-cores-1025r/ahub/kits/qkd_ahub__604.8x440.64, log .../logs/ahub_r2_cts.log). No route before GEOM conditions (2) zh N-face return path, (4) re-signed child views.
BLOCKER hr_* (15 hub_Wi host cores, 0 kits): kv_core_rtl.py excludes qkd_hr_*; their pins carry 1..8 separate host clocks each (ck_map/ck_sum/ck_order/...; prompt core 8) and 4 are CDC cores -> under BRIEFING 16a (host core logic on the die clock, CDC only at the PHY edge) the pins must collapse to one die clock pin and the cdc_* cores become plain register stages: needs a KV plan re-pin + host RTL clock collapse before hardening (proposal below).
2026-10-25 04:43 PDT GEOM-REVIEW-2 -> owner: KV routed POST-ROUTE verdicts in lanes/GEOM-REVIEW.md (2026-10-25 04:43 PDT block): io_cor/io_cor_v1/io_ft/io_ft_v1/hroot FAIL (2 ft stations per 1.0-1.9 mm slot, 1.26-1.95 mm unregistered host pass-throughs, portless ft8 in io_cor, tap spread ~100, single 250 vclk at TT+FF); head_eighth e0/e6 + pv_pair FAIL (9-11-level trees, lane pairs split across subtrees, per-corner core latency).
