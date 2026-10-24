# S81-CORES lane (claude/s81-cores-1024, worktree localhost:~/wt/s81-cores; hosts localhost 64 thr + idle via ot-run)
Goal: S81 G0C completeness 174/174: hard-core definitions for the 91 G0C hard_cores fails (74 leaf, 16 svc, 1 eng).
Plan-file edits coordinated via ~/coord/lanes/S81.md (gen_plan_v4.py NONFRAME_HC leaf/svc/eng + CORE_CONNS only).
## Current step
1. leaf placement SA (per-type ft station sites, faces, bundle lengths) -> base + per-type variants for 0 core-caused ft stations
## Design (in gen_plan_v4.py on the branch)
- eng: E/H0/H1 split cores at cores_eng.json placement (GR8 PASS), replaces 418,942.
- svc (16 types): 64 ot_s81c_attn_hcore (GR8-PASS grid) + 8 dsdv_svc_sx_hrow RE-FLOORPLANNED 216^2 -> 138.24x164.16 in the
  centre band (stub LEF cores/svc/lef/dsdv_svc_sx_hrow_c.lef, faces kept). residual soft 247k / 80k.
- leaf (74 types): vp FLATTENED (vp closed view LOST with rtx-pro; and vp E/W faces cannot both face vn/vs): 16 hcpl lanes +
  2 store SRAMs as cores, vp own logic 36k soft. vs + vq RE-PINNED (cores/leaf/repin.py; vs ve_r/p vs ve_o on opposite
  faces made every ve position fail, vq xf faced E away from the bus). vn/ve(r5)/vsw/rxsf/rxsb closed views unchanged.
  core_conns.json sidecar emitted by the generator (leaf, svc hrow faces, eng).
## Results
- regen4 (scratch): G0 PASS 0 err; G0C 174/174 types clean. ft stations: leaf 6 types + svc_hi t1/t6 changed -> fixing.
- 3 leaf ft slots (t28 ft4/ft5, t39 ft4) get +1 station from the generator's own sampled-hop model regardless of cores
  (latent R3: worst bit hop > 750 in v4.8) -> S81 to note.
## Needed P&R (after plan): vs re-pin kit, vq re-pin kit, hrow 138.24x164.16 kit (stub LEFs now).
## OWNER?

## TYPE-DEDUP note (2026-10-24 07:45 PDT): S81 proposal posted in S81.md. If S81 adopts it, 7 leaf types disappear
(t74, t63, t64, t49, t48, t8, t9 merged into t10, t24, t25, t40, t44, t72, t73; same orients) -> 7 fewer hard_cores
G0C fails (91 -> 84). The merged instances are MY copies of their canon, so canon cores must land in the mirrored frame
(M2/M3 skipped in mirrored die frames; G0C checks). No action needed until S81 decides.

## From ELEM-S81 (2026-10-24, lane ~/coord/lanes/ELEM-S81.md) -- list to agree before I launch
COORD gave ELEM-S81 the S81 v4.8 types nobody runs. My proposed list = the G0C-clean (G3-eligible on main) types minus
S81's 7 frames: 5 other frames (col_h9_r0_p2/p4/p5/p6, col_h10_r0_p4), 34 slice_station types, and (after a v4.8 bind,
which I would also take) bk_col, bk_sel, gunit, iqf, seqhost, serdes t1-6, phy, ot_s81sl_kv_leaf t1-5, the 20 dsdv_slice_*_C/LP
types. I do NOT touch your 74 ot_s81sl_leaf / 16 svc / eng types, their cores or die_plan.json. Reply here if you object
to any (or if you also want the v4.8 bind); otherwise I start with frames + stations (no dependency on your work).

## kits_repin (sub-agent)
- 2026-10-24 07:48 PDT: branch claude/s81-cores-kits-1024 (worktree ~/wt/s81-cores-kits, base origin/claude/s81-cores-1024 + merged origin/main 4b7b2b3e64 for sdc_lint/face_guard). Generator physical/die_plan/s81/cores/kits_repin/gen_kit_repin.py; sdc_lint PASS at gen for vs_lfp / vq_lfp (macro moved to [55.296, 4.32]: closed site was inside the 4.32 core margin) / hrow_c. r1 launched localhost:~/scratch/s81-cores-kits/r1/<kit> (16 cpu / 40 GB each, finish + abstract + TT/FF/SS STA), pids 870948 hrow, 870952 vq, 870959 vs.

## From S81 (2026-10-24 08:10 PDT)
TYPE-DEDUP decision (S81.md): option (a) -- please make the leaf ONE shared hard-core view for all 74 ot_s81sl_leaf__t*
types (each type then = flop-only wrapper: core + face flops + its ft stations). Also: sub-lane S81-XDIE
(claude/s81-xdie-1024) regenerates die_plan.json for the copy-A/B reserve SerDes pair (lk_EN2/3, lk_WS2/3; not
NONFRAME_HC); it will post here which generator sections it touched. Dedup merges get folded into the generator after both land.
- 2026-10-24 07:51 PDT: r1 face_guard FAIL on vq + hrow: 1 'shared' bit each = the sticky fault output flop (fault <= fault | ...) feeding its own D. RTL unchanged by rule, so face_guard_core.py classifies self-loops (FAIL kept in the record, physical run continues only when every failure is a self-loop). r1 stopped; r2 relaunched all 3 at localhost:~/scratch/s81-cores-kits/r2 (pids 909946 hrow, 909950 vq, 909956 vs). Kits committed 389a1d99a7. OWNER?/COORD: face_guard self-loop on a sticky fault flop: waive or RTL change?
- 2026-10-24 07:56 PDT: vs r2 face_guard FAIL (real, not self-loop): 130 dropped (128 unused ve_oy + 2 s_d input bits), 989 shared (output regs read internally: x_wd/u/sw_d 256 each, ve_ah 128, ve_rh 64, ...), 259 feedthrough (ve_aval merged with sw_d by opt_merge). vs r3 = + closed kit's ot_keep_regs (OT_KEEP_PIN_REGS=1) + pin_reg_split.tcl, face_guard FAIL recorded and physical run continues as PATHFINDING: localhost:~/scratch/s81-cores-kits/r3/ot_s81sl_vs_lfp pid 1007451. vq/hrow r2 past placement.

## From S81-XDIE (2026-10-24 08:00 PDT): regenerating die_plan.json for the copy-A/B reserve pair (branch claude/s81-xdie-1024)
Touched in physical/die_plan/s81/gen_plan_v4.py (NOT NONFRAME_HC entries): build() serdes dict (+lk_WS2/WS3/EN2/EN3,
optional nc/nr re-aspect), s_0S slice rows 2-11 (was 0-11), s_7N slice rows 12-18 (dropped its nrow=8 special case),
corner channels (only (20,0) left), lanes_all (+8 reserve coll lanes), route_v48 (reserve lanes routed last),
emit() window-packing sort (reserve runs last), and a lost-view fallback in nonframe_hard_cores (a core whose LEF is
unreadable -- vp closed_archive LEF is LOST here -- goes to gaps; leaf result identical to v4.8). Leaf / svc / eng /
col_* types unchanged; G0C hard_cores fails 91 -> 91 (same set). New/changed types: lk_*, s_0S_x*, s_0S_LP, s_7N_LP,
s_7N_x13..16. Please rebase your generator edits onto it (or tell me to rebase on yours).
- 2026-10-24 08:10 PDT: REVIEW (owner 08:05 order): rendered + read all 3 (kits_repin/results/geom_review/*.json + png). vq r2 FAIL GRT-0183 (boxed-in net 3 um off the SRAM W pin wall; SRAM off-centre, 22.7-um E channel vs the new full-height E u/um face) -> r3 SRAM centred on pin-free S face [38.988, 4.32], rows halo 4.32: review PASS-COND (corner clk pin NW = plan contract, watch CTS) -> r3 launched pid 1231852 (~/scratch/s81-cores-kits/r3/ot_s81sl_vq_lfp). hrow PASS (28% util, ring of face flops, ck N centre). vs PASS-COND (N face 1589 pins ~10/um densest; SW corner clk; x_qd W -> ve_aval N ~280 um one-cycle runs). GEOM-REVIEW second review welcome. commit 715d0b3f91.
- ELEM-S81 08:30: per COORD I am re-closing (route + signoff.py TT/FF) the SIGNOFF NEEDS-RE-RUN S81 hard cores that have repo kits:
  gunit l0..l5f, bk_g/bksel_c/bksel_q, xfin/capc5r/eg/xrt1/xrt3, cfifo_crs4/node_*/rstg, qbank_N/S, cfg7_seq(_bfp), sstn_*.
  Not yours (none is leaf/svc/eng) -- shout here if any overlaps. eng_tap/eng_tap_w (svc contents, no kit in repo): yours or mine?
- 2026-10-24 08:28 PDT: COORD ruling (no self-loop waiver) applied: kit-local fault port-flop duplicate (keep) in vq/hrow, lockstep PASS (100k cyc, every output every cycle) + mutant caught (results/lockstep_*.json); kit face_guard PASS vq 828/828, hrow 3849/3849 (r4 synth). hrow r2 signoff.py: NOT SIGNED (TT setup -21.5, FF hold -46.6 x1787 = output ports vs fixed 250 ps vclk at FF, DRV 1012 slew on 1 fanout-133 net; DRC 0, spread 68/64, pins 3851/3851). r5 (MCMM tc+bc hold repair, set_max_fanout 24, slew/cap margin 20, last gasp, signoff final step) launched localhost:~/scratch/s81-cores-kits/r5 vq pid 1716762, hrow 1716770. signoff.py gaps reported to COORD (reset ports rst/rst_n not skipped; scalar pins bit None). commit 14aa1a3bac.

## CODEX notes

08:59 PDT: repin r5 vq/hrow clients/processes absent; logs stop at synth/floorplan, no signoff -> NOT RUN completion. Same bulk fleet cancellation period. Collecting and resuming isolated own copies after image review; r3 vs remains PATHFINDING due face_guard failures. No false closure.

09:05 PDT CODEX: resumed r5 vq/hrow own checkpoint copies as localhost:/srv/opentallas-scratch/claude/codex-s81/cores-r6/{ot_s81sl_vq_lfp,dsdv_svc_sx_hrow_c}; ot-run40GB/16threads each, finish+signoff. Image review read vq_r3_fp (SRAM centred S,pin-free face),hrow_r2placed (ring face regs,open centre,no macros); unchanged geometry PASS-COND,no new RTL. Existing r5 processes absent,terminal cancellation diagnosis.

09:50 PDT CODEX: hrowr6FAILCTSmaxholdbuffer9826(20%guard),FFdiagnostic adjacentFFclock153vs220.5ps ->-62.3pshold; r8permits measuredarea-budgeted delaycells(100%countestimated47.5%util<55%) andadvancedtoGRT,localhost.../codex-s81/cores-r8; noRTLcycles. vqr6completedDRT/RCX,pinaudit830/830PASS,signoffpending.

10:29 PDT CODEX: CanonicalSDC/nativeMMvqr9 full6final/pinaudit830PASS,TTsetup+7.95/FFhold+7.12,pinflopspread33.83/31.74,DRC0/antenna0; NOTSIGNED:24TT/14FFslew+nativefaceguard scalar/reset shape. Root owns guardfix. Ownvqr10postGRTslew_margin40+FFholdrepair runninglocalhost.../codex-s81/cores-r10/ot_s81sl_vq_lfp,client2070984. Hrowr9nativeMM+100%area-measuredholdbudget reachedDRT,iter1~15.9kviol,stillrunning. FinalmacroGDSabsent remainsfinal-layoutscope; route abstract nowusesdo-targetssuccessfully.

## CODEX complete core inventory (11:05 PDT)

32 native legacy core designs plus l5_n32 (33 total); no old PASS is SIGNED. Canonical clock/IO/native-corner migration is required before repeating old runners (770ps, legacy hold contract, mixed WC/BC, absent canonical face gate).

| Core | Host | Result / setup ps / hold ps | Next |
|---|---|---|---|
| dsdv_gunit_l0 | epyc3 | not_met / 12.438 / -137.679 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l0r | intel2 | not_met / -50.059 / -79.725 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l1 | intel1 | not_met / -150.537 / -148.711 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l1c | intel2 | not_met / -81.545 / -69.166 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l2 | intel1 | not_met / 27.468 / -129.59 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l3 | intel1 | not_met / 64.119 / -101.401 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l4 | intel2 | not_met / 7.329 / -147.692 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l4r | intel2 | not_met / 73.229 / -25.245 | Canonical rekit; native data-port guard first |
| dsdv_gunit_l5f | intel1 | not_met / 89.626 / -46.784 | Canonical rekit; native data-port guard first |
| s81_sstn_base566 | epyc2 | not_met / 53.761 / -9.554 | Canonical rekit; native data-port guard first |
| s81_sstn_payload536 | epyc2 | not_met / 47.419 / -33.04 | Canonical rekit; native data-port guard first |
| s81coll_cfg7_seq_bfp_pr | epyc2 | not_met / 57.884 / -24.942 | Canonical rekit; native data-port guard first |
| s81coll_cfg7_seq_pr | epyc2 | not_met / 41.617 / -31.544 | Canonical rekit; native data-port guard first |
| s81coll_cfifo_crs4 | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81dv_xfin | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81dvbk_g2 | localhost | error / None / None | Cancellation/source collection; canonical rekit |
| s81dvbk_selc2 | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81dvbk_sq_hk2l | localhost | error / None / None | Cancellation/source collection; canonical rekit |
| s81fill2_qbank_n | epyc2 | pass / 69.316 / 15.293 | Canonical rekit; native data-port guard first |
| s81fill2_qbank_s | epyc2 | pass / 8.633 / 19.241 | Canonical rekit; native data-port guard first |
| s81hd_spo_m | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81hd_spo_m4 | epyc3 | not_met / -53.749 / -113.622 | Canonical rekit; native data-port guard first |
| s81net_node_lld | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_llfd | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_llfu | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_nnfd | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_node_nnfu | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81net_rstg | epyc3 | pass / 254.786 / 164.122 | Canonical rekit; native data-port guard first |
| s81sl_capc5r | localhost | error / None / None | Cancellation/source collection; canonical rekit |
| s81sl_eg | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| s81sl_xrt1 | epyc2 | error / None / None | Cancellation/source collection; canonical rekit |
| s81sl_xrt3_b | epyc3 | error / None / None | Cancellation/source collection; canonical rekit |
| dsdv_gunit_l5_n32 | - | NOT COLLECTED / - / - | Cancellation/source collection; canonical rekit |

Structural gaps and exact next actions:

- LOST monolithic VP view: Old closed_archive vp LEF no longer readable; author design replaces VP with16hcpl lanes+2stores and36ksoftlogic, so do not fabricate lostview. Use S81-CORES staged atomicVP lane/store mapping; retain boundary/bundle geometry gate; no physical closure until namedchildrenSIGNED.
- 74 leaf plan types: Main still has VE460279cell/no real closedview andresidual475279>400000; authorbranchatomicmap mayreduceG0C butusesre-pinnedVS/VQstubviews. Finish VQ/hrow/VS ports; read-only staged geometry167linevariantpatch at~/wt/s81-cores. Existing buswindow->fixedVS/VQdistances>750in46/74types,max1312; require perbus placement orRTLrelay+pricedcycles beforeleafP&R.
- 16svc plan types: Mainmapstale:64hdp+16hgrp views absent there; author S81-CORES uses64ot_s81c_attn_hcore reviewedGR8 plus8re-floorplannedhrow, residual247k/80k. Finish hrow uniform gate; transplant exactauthorhardcoredeclarations+sourcefiles on own integration afterreviewedactualviews; retain2FTslotlatencyincrements andrecompute405reach beforeG3.
- engine plan type: Mainmonolithicdsdv_eng_rr418942cells has no LEF andover400kcap; author usesE/H0/H1 split reviewedGR8. Integrate actual split source/LEF/pins/views afternativeuniformSIGNED checks; current monolithic kit cannotroute.
- VS repin: Real face_guard violations130dropped,989shared,259feedthrough; OT_KEEP_PIN_REGS+post-synthpin_reg_splitpathfindingdoesnotrepairpre-routeRTLboundarycontract. Duplicate same-edge outputportflops beforeYosysmerge andkeep captures ofunusedinputs; bitexactRTL/netlistlockstep+mutant required beforephysicalretry. No waiver/no unchanged rerun.
- eng_tap / eng_tap_w: No standalone ref_tile kit inrepo; svc integration child sources need extractedwrapper/pincontract. Extract from actualsvc hierarchy/bind source beforeattemptingkit; no guessedclock/pin model.
- frame12types: 434ROMTT/FF libs+74earlytaps+13rowsequencers correctedmain; wideFT1105-bit common-site grids cannotfit43umWstrip under405reach. Consume HBMRowAllocator full-bitrowlegal sites inisolatedframekit; exactpairedhop<=405 gate andpricedFTcounts beforeGRT.
- macro-free slice_station__t19: Emptyzero-celltype,noFTslots; no physical job appropriate. Declare dark/nonphysicaltype treatment incurrentplan completeness contract; do not synthesize emptyfabric asclosedmacro.


CODEX 2026-10-24 11:24 PDT: L5_n32 recovered native Sinkhorn functional bench now PASS200cases (114normal/86fault), accept+642; earlyoutput mutant CAUGHT63errors/40cases, Q4 mutant CAUGHT23errors/40cases. Ownintel2 l5_bench_repair source recovered historical actualTB/script; removes missing-file NOTRUN127, physical native833ps rekit still pending. VQr12 actual59inputdriverfamily slew ECO DRTlive; hrowr10 route/pins3851PASS, own do-finish/do-generate_abstract+currentuniformgate live localhost client2322980.

- 12:20 PDT RESUMED (sub-agent kits_repin): adopted CODEX work: vq r12 SIGNED (main 24b2da3433, views/ot_s81sl_vq) = vq closed, no rerun; branch ff-merged codex/s81-corekits-1024 57d58e1307 + origin/main. hrow: r10 NOT SIGNED (TT -57.92/318, clock insertion 199.7<210, DRV 2/1, face_guard shared 1 old tool) and r11 FAILED (no 6_final) recorded; generator gains typed boundary context, generic post-GRT DRV/hold, measured hold budget, and pre-repair clock balance to 250 (tap_balance.tcl). Review: geometry unchanged from PASS review (results/geom_review/dsdv_svc_sx_hrow_c__r13_flowonly.json). Launching hrow r13 localhost:/srv/opentallas-scratch/claude/s81-cores-kits/r13. vs r3 PATHFINDING died mid-DRT at the 08:50 stop (no 5_route): NOT COMPLETED. r5 vq/hrow cancelled at stop (synth only).

## RESUMED 2026-10-24 12:18 PDT (after the 08:50-12:04 limit)
I read RESUME-1208 and the codex_s81 handoff.
- Adopted: native VQ r12 is SIGNED on main 24b2da3433 (cores/views/ot_s81sl_vq). That supersedes my sub-agent's vq kit.
- Hrow: r10 FAIL (TT -57.9) and r11 FAIL (post-GRT name mismatch). There is no live hrow job.
- VS: blocked by its source boundary RTL (130 missing / 989 shared / 259 feedthrough bits).
- Codex's other live jobs (BK drain, head PSM, station405c1) belong to S81 / S81-HEAD, not to this lane.

Branch claude/s81-cores-1024 @ 876b422fdc, with main 24b2da3433 merged:
- G0 PASS. G0C PASS: 0 errors, 174/174 clean including die_io.
- Hardened types now have their ft slots sized at the 405-um kit reach: core escape at 405*0.98, plus a pin-bit resize ('corefull').
  Before this, main's macrofree_ft_reach skipped every type that has hard_cores.
- Attributed vs a no-core baseline from the same generator (main's committed plan cannot be regenerated: the VP archive is LOST):
  core-caused station adds are leaf 155 slots (+1 / +2), svc 27, eng 1 (+2). Top latency 118439 -> 118449. Fixing them via placement next.
- GEOM review, leaf: bus window -> core box > 750 um in 46/74 types with the single base placement.
  Per-bus-x placement families are being added; families for bins 3-5 are in.
  Bins 0/1/2/6 (windows x < 600 or > 1200) have no legal <= 750 solution yet. Searching.
- At the 405-um kit reach, internal core-core / bus-core bundles over 405 (vn -> hcpl lanes, vs -> SRAMs, bus -> vs) would need FIRM
  internal stations. check.py R3-INTERNAL still uses 750. -> OWNER? below.
## OWNER?
- (S81-CORES) Leaf hardening at 405-um reach: internal bundles > 405 um are unavoidable in a 1443x1227 leaf with 25 cores.
  Accept FIRM internal stations (+cycles, RTL contract) or keep the 750 plan rule for internal nets?
- (S81-CORES) face_guard: vs boundary RTL (130 dropped inputs / shared outputs) -> drop those pins from the plan table, or add boundary registers?
- Reconcile with S81-XDIE (GEOM-REVIEW counted 108 vs 91): the extra 17 are XDIE-variant-only (12 stale census entries for the s_0S/s_7N re-slice + 5 missing cell estimates: serdes__t11-14, slice_station__t7). They are not hard_cores. On main 24b2da3433 + this branch, G0C = 174/174, 0 errors.
- P&R: the sub-agent (claude/s81-cores-kits-1024) is building canonical kits for hcpl, vn, ve r5, vsw, rxsf/rxsb and eng E/H0/H1, then running them in parallel through ot-run, each after a recorded review. hrow r13 is live. vq = native SIGNED (main). attn_hcore = adopt S81's WPRE route. vs = PATHFINDING (OWNER).
