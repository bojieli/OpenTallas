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

## STATUS 2026-10-24 13:26 PDT (branch claude/s81-cores-1024 @ fae2bebc4c, pushed; NOT merged)
- G0 PASS, G0C PASS 174/174 (0 errors, die_io) on regen15 (~/scratch/s81-cores/regen15).
- Leaf placement now comes from cores/leaf/alt_place.json: a base layout plus 148 per-type candidates.
  - Each candidate keeps every hcpl lane within 300 um of vn (box) and within 450 um of vn's hq/hw pins.
  - The generator picks per type by (bus reach excess, ft stations added vs the no-core 405 model).
- ft delta vs the no-core baseline:
  - leaf: +58 stations on 55 slots.
  - svc: +31 on 29 slots (the GR8 grid at 405 reach).
  - eng: +2 on 1 slot.
  - Top latency 118439 -> 118442.
- A single shared leaf arrangement (the one-view case) would add +81 stations, with 63/74 types over reach.
- GEOM self-review: results/geom_review/s81_cores_1024/ (record s81_cores_plan__2ab05a2722ec.json + 5 renders).
  - Verdict PASS-COND for svc, eng and 61 leaf types.
  - FAIL for 13 leaf types: window->core reach > 750 um (t5 t6 t8 t11 t15 t28 t30 t36 t40 t49 t50 t54 t72).
  - FAIL for internal core-core bundles of 405-472 um, over the 405 kit reach.
- Asked S81 (S81.md) to accept per-type macro arrangements as decision (a) and the station/latency delta. Merge waits on that answer.
- OWNER?:
  - (1) Internal >405-um core bundles: FIRM internal stations, or the 750 plan rule?
  - (2) The 13 reach-FAIL leaf types: x-mirrored pin variants of vn/vq/vs (new core views), or relays (priced cycles)?
2026-10-24 13:26 PDT S81-CORES: G0C 174/174 on claude/s81-cores-1024 @fae2bebc4c (regen15); geom self-review recorded; awaiting S81 ack on per-type leaf arrangements + ft delta (+58 leaf/+31 svc/+2 eng, latency +3) before merge; 13 leaf types reach FAIL -> OWNER?

- 13:08 PDT kits_repin: scope expansion (S81-CORES 12:4x). Canonical kits (face_keep + face_guard on 1_synth.odb, clock balance to 250, hold budget 100%, post-GRT slew40/FF hold, MCMM, signoff.py final) for the leaf G0C hard cores, closed-view pins kept (closed LEF edge rects; the core_pins tables' largest-rect centres differ by up to 1.37 um on 13..362 pins/core, recorded per kit in pins_snapped.json), closed macro sites. Reviews (Read PNGs) results/geom_review/*_c__<hash>.json: hcpl PASS, vn PASS-COND, vsw PASS, rxsf/rxsb PASS-COND (pin clusters at face cap as closed), ve PASS. Launched c1 localhost:/srv/opentallas-scratch/claude/s81-cores-kits/c1/{ot_dsrom_su_hcpost_lane_pr_c,dsfd_su_t_rxsf_c,dsfd_su_t_rxsb_c,ot_s81sl_vsw_c,ot_s81sl_vn_c,ot_s81sl_ve_c}. hrow r13 in GRT. attn hcore = S81 lane (WPRE route DONE, signoff on epyc2), not rekitted. Branch 6be7b45a41.

## PARKED 18:55 PDT (kits_repin sub-agent)
- Branch claude/s81-cores-kits-1024 @9fc976f89f (pushed). Kit inputs, reviews and results are under physical/die_plan/s81/cores/kits_repin/.
- Live jobs (ot-run, run_kit.sh route; signoff.py runs as the final step):
  - localhost:/srv/opentallas-scratch/claude/s81-cores-kits/c2/:
    - dsdv_svc_sx_hrow_c (= hrow r14)
    - ot_dsrom_su_hcpost_lane_pr_c (PATHFINDING, face_guard_continue)
    - dsfd_su_t_rxsf_c
    - dsfd_su_t_rxsb_c
    - ot_s81sl_vsw_c
    - ot_s81sl_vn_c
    - dsdv_eng_rr_e_c
    - dsdv_eng_rr_h0_c
  - epyc3:/srv/opentallas-scratch/claude/s81-cores-kits/c2/:
    - dsdv_eng_rr_h1_c
    - ot_s81sl_ve_c
  - Logs: <dir>.otrun.log on localhost, plus KIT/run_route.log and KIT/signoff.log.
- Results:
  - vq: SIGNED (CODEX r12, main 24b2da3433).
  - hrow r13 NOT SIGNED: TT -50.12 / 233 endpoints, on role[1] -> decode fanout tree. FF +8.45. Spread 63.7. Clock balance gave insertion 268 (PASS). DRV 1 slew. Post-GRT estimate +0.5 -> RCX -50, so r14 adds setup margin 40 and a post-GRT setup repair.
  - CODEX r10: NOT SIGNED.
  - vs: PATHFINDING (OWNER).
  - c1 (superseded by c2) FAILED:
    - vsw, rxsf: SYNTH_MEMORY_MAX_BITS (now fixed).
    - ve: wrong spec (now the r5 spec).
    - hcpl: face_guard FAIL.
    - rxsb: face_guard FAIL.
    - vn: stopped as a duplicate.
- Known face_guard RTL blockers (no waiver; OWNER/RTL decision):
  - hcpl o[15:0] constant (ot_dsrom_su_hcpost.sv:129 o <= {hi,16'd0}), plus the sticky fault self-loop.
  - rxsb o_r[31] shares a tie net (constant bit). c2 rxsb will stop at face_guard.
- Pins: closed-view pins are taken from the closed LEF edge rects. The inputs/core_pins tables (largest-rect centre) differ by up to 1.37 um on 13..362 pins/core (kits/*/pins_snapped.json). The plan integrator should know.
- Next: collect c2 with collect.py (signoff authoritative) and iterate on failures, each after a recorded review. eng: verify macro placement and half-cycle SDC in synth/floorplan logs.
- OWNER?: hcpl/rxsb constant output pins (drop from the plan, or allow a const class); vs face_guard.
- Owner rulings for next steps (recorded 19:00, not yet acted on):
  - (a) Internal core bundles of 405-472 um get fixed internal stations; R3 reach applies inside cores.
  - (b) The 13 reach-fail leaf types get x-mirrored pin variants of vn/vq/vs as new core views.
  - (c) Reset: core kits take reset as a synchronous timed input (one root 2-flop synchroniser, pipelined relays every <=405 um at equal depth, no recovery waivers). The current kits_repin SDC models rst as async with recovery checked; the generator must change before the next rekit.

## PARKED 2026-10-24 18:59 PDT (S81-CORES main lane)
- Branch claude/s81-cores-1024 @ eee33cf766 is MERGED to main as e94d9bb329 (plain recipe).
  - Gates: G0 PASS and G0C PASS 174/174 (0 errors), re-run on the merged tree.
  - Plan diff vs main: only the leaf/svc/eng/pvso_entry hard_cores and their ft_slots.
  - Top latency 118439 -> 118442 (coordinator accepted this as S81 decision (a)).
  - tools/die_plan pytest: test_bind fails here (yosys/docker env). My files (gen_plan_v4 + s81 outputs) are not read by those tests.
  - Worktrees removed: ~/wt/s81-cores and ~/scratch/s81-cores/basewt.
- Live jobs (main lane): none. All opt4 searches are finished.
- Sub-agent kits_repin is parked separately (section above).
  - Branch claude/s81-cores-kits-1024 @9fc976f89f, NOT merged.
  - c2 runs keep going on localhost and epyc3 at /srv/opentallas-scratch/claude/s81-cores-kits/c2/.
  - vq is SIGNED. hrow r13 is NOT SIGNED (TT -50.12).
- Results: GEOM self-review at results/geom_review/s81_cores_1024/.
  - 13 leaf types FAIL reach: t5 t6 t8 t11 t15 t28 t30 t36 t40 t49 t50 t54 t72.
  - Internal core bundles are 405-472 um.
- Scratch tools are kept: ~/scratch/s81-cores/{regen.sh, plandiff.py, leaf/opt2.py, opt4.py, pick.py, mkalt.py}, plus regenbase (the no-core baseline).
- Next, per coordinator rulings (14:xx):
  - (2) Add fixed internal stations on core-core bundles over 405 um. R3 applies inside cores. Model this in core_conns and the kit specs.
  - (3) Build x-mirrored pin variants of vn/vq/vs for the 13 reach-fail types (new core views). Then add a "variant" choice to the generator candidate search.
  - Change the kit generator for the reset rule (BRIEFING OWNER DECISIONS #2: synchronous timed reset input, no recovery check). The kits currently model reset as async.
  - Collect the kits_repin c2 results; only SIGNED counts.
- OWNER?:
  - Constant output pins (hcpl o[15:0], rxsb o_r[31]): drop them from the plan, or let face_guard accept constants?
  - vs face_guard failure on the RTL.
2026-10-24 18:59 PDT S81-CORES: PARKED. claude/s81-cores-1024 merged to main e94d9bb329 (G0 PASS, G0C 174/174); kits_repin parked @9fc976f89f with c2 runs live; next = internal stations, vn/vq/vs x-mirror variants, sync-reset kit change.
2026-10-24 20:17 PDT RESET -> S81-CORES: core kits: rst_n becomes a timed synchronous input driven by the partition tap relay (the SDC line 'released by the partition's reset synchroniser one cycle ahead (recovery at 1 T)' stays valid as an IO budget); no async sync inside cores; declare any internal relay as core reset depth. recipes in lanes/RESET.md ## RECIPES; tool claude/reset-1024@d1152532c (READY)

## CODEX notes 2026-10-24 21:11 PDT (parked for Claude)
- CODEX took over C3 collection on intended codex/s81-cores-c3-1024 from claude/s81-kits-c3-1024r@88579eb4a4. IMPORTANT: simultaneous fetches changed shared FETCH_HEAD: worktree checkout actually targets 3b5eba8d1 (RESET), not C3. No source edits or commits in it; do not use until own checkout is corrected to exact 88579eb4a4. Git worktree add PID 2026860 was still completing at park; let finish, then correct own clean branch. Use exact SHA/origin ref for future worktrees.
- C2 failure census matches S81.md 19:34, already superseded by RTLA/C3; no duplicate C2 retry.
- C3 epyc2 stage-1: hcpl/rxsf/rxsb/vq completed placement with raw-netlist face_guard PASS. h0 floorplan, h1 synth, vn synth, vsw place optimization still active. VS FAILED (21:00) raw face_guard: 2728 bits, 1990 OK, 2 dropped s_d[63]/s_d[61], 736 shared outputs. Evidence epyc2:/srv/opentallas-scratch2/claude/s81-kits/c3/_fail/vs_face_guard.{json,txt}; needs genuine RTL boundary fix, no physical retry yet.
- Reviewed images and advanced four completed C3 kits in own isolated checkpoint copies to route. Run host epyc2:/srv/opentallas-scratch2/claude/codex-s81-cores/c4/{ot_dsrom_su_hcpost_lane_pr_c,dsfd_su_t_rxsf_c,dsfd_su_t_rxsb_c,ot_s81sl_vq_lfp}. 40GB/8threads each via epyc1 ot-run clients 2360040..2360043. Logs epyc1:/srv/opentallas-scratch2/claude/codex-s81-cores/clients/<kit>.log; route logs in each kit/run_route.log; final authority <kit>/signoff/signoff.json. All admitted, CTS at park (VQ hold repair), no SIGNED claim.
- Review PASS-COND: local /srv/opentallas-scratch/claude/codex-s81-cores/review/codex_s81_c4_review.json and four PNGs read. hcpl compact/clear/no macros, RXSF/B macrofree 140um crossing with dense closed-view E/W pin groups, VQ centered south SRAM/39um side channels/84um upper band. Preserve these into results/geom_review on correct C3 branch before merge. Review was written BEFORE route; no data cycle changes, no constraint changes.
- RTLA latest a2b6fb6d drops eng_e constant/unused ports; E rekit remains next. Const pin branch 1402d0b088/hrow 66e9ae4d3/three legacy views already READY (see S81 lane), not duplicated.
2026-10-24 22:25 PDT RESET -> S81-CORES: RESET wavefront API (OWNER DECISION 13), claude/reset-1024@0a08a66af (READY, not yet on main): plan "reset": {"release": "wavefront"} (opt relay_um 405, hop_um, in_sites {type:[x,y]}, root_part; hard types reset.tap_um / reset.depth). Then: gen.py rtl/phys emit u_rst_in (u_rst_root in the root's type) + equal-depth u_rrl tree to taps AND registered outs rst_o_<k> (interior pins, io.tcl + LEF), die top wires parent rst_o -> child arst_n; bound kits: kit_rsync.py PLAN TYPE KIT_RTL_DIR --release wavefront (adds rst_o to bound module + wrapper). Offsets: python3 tools/die_plan/reset_tree.py offsets PLAN.json [--release wavefront] --out J. G0 errors list partitions whose IN pin has no neighbour rst_o within hop (move IN / hard reset.tap_um to a face). Reset only control state; start broadcast after reset (13c/d) are RTL/schedule items.

## CODEX notes 2026-10-25 02:38 PDT
CODEX took over: current C3/station harvest and FTHOLD proof on codex/s81-fthold-1025 (isolated sparse tree localhost:/srv/opentallas-scratch/claude/wt/codex-s81-fthold). hcpost C3 m5/m0 NOT SIGNED: TT +80.81 ps, FF -2.31 ps / 2 endpoints; face_guard, DRC, DRV PASS. VQ f0 NOT SIGNED (-4.41 ps /60 FF endpoints +1 TT slew), f5b live epyc3. FTHOLD original t8/t37 proofs live intel2. Diagnosed t37 pre-placement setup-repair loop (6,873 endpoints -150.353 ps, >900 iterations zero changes): ideal capture clock and preserved hold cells, not propagated hold failure. Own t8 CTS successor uses REMOVE_ABC_BUFFERS=1 to bypass unplaced repair, holds remain dont_touch; images t8/t37 reviewed PASS-COND, record results/geom_review/codex_s81_fthold_1025.json. ot-run client log /srv/opentallas-scratch/claude/codex-s81-fthold/t8.cts.log. Original jobs untouched.

## CODEX notes 2026-10-25 02:42 PDT
Split ve_m/ve_s/vn_a/vn_b contact sheet viewed; GEOM PASS-COND records codex/geom-proto-1025@932357e56. Launched all 4 cores x m0/m5 in isolated CTS checkpoint copies /srv/opentallas-scratch2/claude/codex-s81-split, via ot-run from epyc1 (ve variants epyc1; vn variants spilled epyc2). FF-corner GRT repair before TT route/finish, no constraints/RTL/pins/cycles changed. Per-kit root *.otrun.log; run_route.log; final signoff/signoff.json. hcpost -2.31ps/2 output-endpoint failure has own FF-repair copies epyc2:/srv/opentallas-scratch2/claude/codex-s81-hcpost/hcpost_ff_m0,m5 (ot-run logs epyc1 same root/m0.otrun.log,m5.otrun.log). Original failures preserved signoff_parent_failure. Missing cores and PORTFIX gunit/bk_sel core_faces now delegated CODEX missing-cores sublane; source gaps being repaired.

## CODEX notes 2026-10-25 02:58 PDT — legacy rstg/payload closure
CODEX took over canonical legacy rstg/payload536 on codex/s81-legacy-1025, own WT /srv/opentallas-scratch/claude/wt/codex-s81-legacy. Viewed rstg_review.png + payload_review.png: aligned N/S buses, macro-free, short wires, sensible core margin; pin density below capacity; PASS-COND with actual CTS/routed RC pending. Copied placed r4 kits into epyc1:/srv/opentallas-scratch2/claude/codex-s81-legacy/kits/{rstg_m0,rstg_m5,payload_m0,payload_m5}, originals untouched. Updated current signoff/pair-skew,250ps±40ps clock-balance hooks, FF postCTS STOP gate and0/5ps hold variants; sameRTL/pins/SDC833/60/25. Four ot-run staged route/finish clients3602280..3602283; logs /srv/opentallas-scratch/claude/codex-s81-legacy/logs/*.log. Next harvestactual signoff and diagnoseeveryfailure.

2026-10-25 03:01 PDT CODEX legacy: initial4variants FAIL CTS RSZ0060 (528rstg/2417payload hold buffers). Cause1: clock tap regex excludes ck[0], so zero trees balanced. r2fix recognises trees (payload88->254ps,7delaycells) but FAILS same cap because cts_post runs unrestricted hold repair before the postCTSSTOPgate. r3successor copies use clockbalance only atCTS, then actualFFgate, then0/5ps GRT hold repair; launchedclients3613380..83, sameownkits parent.../{rstg_r3_m0,rstg_r3_m5,payload_r3_m0,payload_r3_m5}. Earlierfailures retained; noRTL/SDCchange.

2026-10-25 03:07 PDT CODEX legacy: r4route/finish collectedall4, NOTSIGNED. rstg TT/FF:m0+355.08/-9.48(60ep),m5+355.24/-5.99(32ep); payloadm0+339.33/-20.09(536ep),m5+344.18/-10.47(511ep); allDRC0,sdc_lint/face_guardPASS. Bothsingle-stagecores have no internalrelatedflop->floppaths, so pairgatefails nofinitepairs despite1psrstg/9.6pspayloadspread; escalatedtoCLOCKviaCOORD, nofalse0claim. Residualholds beingrepairedwithactual6finalSPEF andincrementalDRT inowncopy epyc1codex-s81-legacy/eco/{rstg_h0,rstg_h5,payload_h0,payload_h5}; clients3644314..17, holdmargins0/5, noRTL/SDC/clockchange. DefaultGRTrepairfailurefixedbySKIP_INCREMENTAL_REPAIR=1+explicitFFhold-onlyposthook; priorfailuresretained.
2026-10-25 03:16 PDT INFRA -> S81-CORES: epyc1 root disk (owner: no work on root): your LIVE item(s) still on the ROOT md0: ~/wt/s81-cores-kits. When the job ends, move it to the same path under /srv/opentallas-scratch2 (bash /srv/opentallas-scratch2/claude/infra-pass4/move_one.sh <path> -- copies, checks liveness, git worktree repair, symlink back) and create new run dirs/worktrees only under /srv/opentallas-scratch2/claude/.

2026-10-25 03:21 PDT CODEX took over narrow Engram inactive offset-read repair on codex/eng-inactive-1025@33408014b (S81 worker authorization; no overlapping engineRTL edits). Candidate bounds q_off read when ej==CPR after finalbeat;0cycles. Strict miter binds unchanged reference lookup and compares ALL13public outputs on EVERYcycle, no valid masking;3seeds + corrupted-HBM-input control compiling epyc3:/srv/opentallas-scratch2/claude/codex-eng-inactive-1025/test, unit oth-ubuntu-2480638-1792923369 (32GB/8requestedthreads,jcap1). No route/STA. If public invalid-payload bits differ, candidate will be rejected; any adopted RTL invalidates old synthesized/physical view and needs re-sign-off.

## CODEX notes 2026-10-25 03:25 PDT
- t12 wavefront m5/m0 NOT SIGNED: TT+18.81/+24.03ps, FF-11.95ps/2ep, pair TT43.99/FF38.66ps PASS, DRC0. Final guard falsely checked rst_o_0 as data (raw1374/1374 PASS): FIXED codex/s81-reset-signoff-1025@457ac639e, 34tests + actual t12 guard PASS1374/1374. Real residual reset output/internal relay hold has own extracted-SPEF ECO h0/h5 at codex-s81-station-eco; initial24GB attempt OOM25.15GB, resumed successful GRT at48GB via do-5_2_route. An ordinary-route driver mistakenly rebuilt frontend; only own exact containers stopped, diagnostics retained, direct-stage driver corrected.
- t30 m5/m0 NOT SIGNED: FF-8.01/245 and -11.46/281; TT related pair86.3/86.7ps (ft0_s2 bit541 clk_t9 ->s3 clk_t1), DRC3 on reset pins vsPG. CLOCK owns skew fix; RESET generic pin-PG fix codex/reset-pin-pg-1025@181eaa1e0 moves soft pins<=1.04um,0cycles, must regenerate/review before retry. Reset shared2 false guard failures fixed457ac.
- C3 RXSB NOT SIGNED solely FF-13.25ps/35ep. Own hcpost GRT-FF retries NOT SIGNED(-3.03/3,-3.57/1); true postRCX hold ECOs now codex-s81-core-eco/rxsb_route_h0,h5,hcpost_route_h0,h5 using do-route, hold-only0/5, latest signoff. Original failures untouched. Initial4 launches had missing external runner127, then wrong ordinary-route target; corrected self-contained copies and exact-stop records preserve those failures.
- Split VN_A m0/m5 GRT FAIL0183(net25861), after initial GRT0overflow inside native DRV insertion. New p0/p5 copies use placement RC for DRV, legalize before incremental route, skip native repair, FF hold-only0/5. Other split6 variants live; no SIGNED claim yet.
- FTHOLD t8 CTS structural PASS: FF-46.83/149ep (148FT input+1arst_n), TT input+54.5 across3732bits; t37 PASS FF-51.68/747ep. Old clock trees late(276..356ps), so CLOCK holds routes pending density fix. Actual discovered power failure14,928 disconnected PG terminals on7,464 dont_touch delay cells FIXED by explicit preGPL PG hookup; actual ODB now0missing. Source codex/s81-fthold-1025@9516fdda1 includes PG fix +181eaa +existing DEC12 two-beat contract;9Liberty tests+4096-cycle lockstep/mutantPASS,0cycles. New density-t8 proof39taps,max933sinks,max151.2um, image viewed, launching density_gen/slice_station__t8 (t8_density.cts.log).

2026-10-25 03:31 PDT CODEX CORRECTION legacy: historicalkit-localface_guardPASSusedrejectedpair-IN/OUTparser. CANONICAL face_guard FAIL merged132rstg/1072payload; notjustclockgate. Zero-internal-pairclockcensusnowPASS66/536allclocked. CLOCK/reset_targetsownsoff-defaultgenuine2stageRTL,+1cycleandphysicalgates. One-stageTT/FFpositiveevidenceretained; neverSIGNED/registered. results/s81_legacy_codex_1025/CANONICAL_FACE_GUARD_CORRECTION.json recordsfacts.

## CODEX notes 2026-10-25 03:35 PDT — HANDOFF
Parkednorm/frameFT/legacy/quantwork, fullhandoffCODEX-LOG.md. Latestquantprototypecodex/s81-quant-release-1025@35171f88a, correctedC8sharedLUTmax157/+154lastcapturecycles; finalnewtableproofQUALIFIEDexit0 epyc1codex-quant-release-c8-1025(unit3931212), logspreservednotyetcollectedtorepo. Actualfulltoken/P&Rstillowed. Legacyone-stagecanonicalfaceFAILmerged132/1072 despitepositiveTT/FF; CLOCKowns2stageOFF-defaultsuccessors. No livejobsornewOWNER? fromthissublane.

## CODEX parked 2026-10-25 03:35 PDT
Actualrstg/payloadTTFF+clockcensusPASSbutcanonicalface_guardFAILmerged132/1072; noSIGNEDclaim. Two-stageRTLonlyWIPca905aaf8 has12000-wordalignedlockstep+wrongdepth/data controlsPASS; model/geometry/physicalNOTRUN. Reviewce774d234. FullhandoffCODEX-LOG.md CLOCK/RESEThelper. No live jobsstartedbythishelper.

## CODEX notes — Handoff to Claude 2026-10-25 03:36 PDT
S81 subgroup parked on RESET; all jobs preserved. Main summary in CODEX-LOG.md Handoff S81 subgroup. Exact FT source36915c557 pushed;178type cached outputG0C0E at epyc1 codex-s81-ft-exact/adopt178, not committed yet and predates nine fault feeders. New hcpost_h5 actualSIGNED TT+61.39/FF+3.68ps, views unintegrated. Core-pair relay metadata missing actualRTL remains held/assigned; one-stage legacy canonicalfaceFAIL remains, two-stage ruling20:42 ownedCLOCK. Child detailed handoffs follow; no newjobs/merges.

## CODEX notes — Handoff to Claude 2026-10-25 03:37 PDT
NEW hcpost SIGNED epyc2:codex-s81-core-eco/hcpost_route_h5/signoff_codex/signoff.json TT+61.39/FF+3.68,pair25.40/22.33,all gates PASS;h0alsoSIGNED.Views integration owed.457ac reset-output signofffix READY;7fd4237cb FTHOLD experimental pushed.Full exact live jobs/results/failures/OWNER in matching CODEX-LOG handoff.Active jobs preserved,no new jobs/merges afterreset.
2026-10-25 04:24 PDT S81-CORES: fresh lane started (brief 04:25). Claimed S81 core near misses in lanes/NEARMISS-ECO.md.
2026-10-25 04:35 PDT S81-CORES: COLLECTED (fleet scan of every S81 core run, inventory rtx-pro /srv/opentallas-scratch/claude/s81-cores-1025/{inv.txt,scan1.txt}).
- New SIGNED (not yet on main): dsfd_su_t_rxsb (Codex hold-only ECO rxsb_route_h5, pre-04:13 rule) -> READY claude/s81-rxsb-view-1025@20acdc729b; dsdv_eng_rr_h1 (c3, 03:10, normal route) -> view integration by sub-agent C3.
- NOT SIGNED (routed): vn_a p0/p5 (pair 141 ps SRAM u_h0->g_x, insertion 426, FF -39/117), vn_b m0/m5 (insertion 424, FF -7.4/29), ve_m (insertion 316, FF -5.7/3), ve_s (FF -2.3/16), vsw (TT -11.4, FF -10.3, ins 301), rxsf (TT -6.2/1, FF -2.5/13), eng_rr_h0 (FF -0.08/1), eng_rr_e (GRT FAIL 04:12), vq f5b (TT -58.8/298) / f5 (FF -2.38/19), attn_hcore r3 (TT -4.91/18, old tool), legacy rstg/payload (canonical face FAIL; CLOCK owns 2-flop).
- Never routed on current RTL: gunit l0/l0r/l1/l1c/l2/l3/l4/l5, bk_g, bksel_c/q, qbank_N/S, cfg7_seq_bfp, eg, xrt1/3, xfin, base566, cfifo, capc5r, bf_front_roots, bf_col, elem_q, idx_tx_n32 (old 10-24 stage-1 kits predate RTLA/RTLC/DEC12).
- Station kitsB (st405, 10-24) list t1 t2 t11 t13 t33 t34 = types REMOVED/renumbered in the 178-type plan; t26 t30 t31 changed ft_slots; only t23/t24 (and t8 t12 t14 t17 t18 t19 t20 t22 t25) unchanged in content, but all kitsB predate the wavefront reset -> STALE, not re-collected. Live kitsW wavefront station runs (epyc1 s81-st-rst/kitsW,kitsW0 t6 t11 t24 t27; intel1 kitsW0 t24) left running (not mine).
- Inherited: 457ac guard fix already on main (439ee0819). 7fd FTHOLD prototype + 2f2a74656 legacy RCX ECO stay held (ECO class barred by owner rule).
- Sub-agents launched (~90 min each): SPLIT (vn_a/vn_b/ve_m/ve_s/vsw clock-structure fix, F1-F6), C3 (attn_hcore, rxsf, eng_rr_h0/e, vq; eng_rr_h1 view), LEGACY (re-kit wave from main for never-routed cores, stage-1 + GEOM REQ). Context: rtx-pro /srv/opentallas-scratch/claude/s81-cores-1025/SUBAGENT_CONTEXT.md.
