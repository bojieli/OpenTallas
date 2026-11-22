# FABLE-FIX-QC-CBGLUE handoff (owner of the QC cb / glue family + coll_n)

Updated 2026-11-16 13:5x PST. Commits from here on end with the Opus 5.5 trailer (COORD 08:xx).
Lane dirs: epyc2 /srv/opentallas-scratch2/claude/fable-fix-qc-cbglue (repo = lane clone, branch
claude/fable-fix-qc-cbglue-1116 @e354fc3e4f6, MERGED to main ed3beac3e9); epyc9 same path (delta/ plans, mk_s4q9e.py).
QC event owner (binds, adopts): FABLE-FIX-QC-KNEE-HC, epyc9 fable-fix-qc-knee-hc (treeE = v2 tree copy, bin/chain.sh).

## 1. START raw reset -> FSTART face flops (glue -492, cbf_q01 -1,916, cbf_q01_s2 -3,020): FIX BOUND, timing not yet read
- Cause MEASURED: the only 3 of 19 cb / glue types without clock.landing_local_resets rows.
- S4q9d = S4q9c + rows (sha 9c0f8e750f07), r303. Bound by KNEE-HC: S4Q9DBQ LATCHECK 1921/1921, r8rc 0, leaves in the
  bound RTL (glue 5, cbf_q01 3 u_cland_lrst_fstart_*). The bind ended RC 1 on an unrelated PARAM_REGEN W5 pad error
  (knee stations vs st_a pad pin); KNEE-HC rebinds S4Q9DBQ2 / DBQ3 (08:37, ~35 min). Plan file unchanged.
- Proof still open: first cbf_q01 / cbf_q01_s2 / glue kit on S4q9d + v2: no rawreset->fstart path under -42 at the post-CTS gate.

## 2. glue fault hop (-330 and -129): DELTA S4q9e composed 09:0x, posted to KNEE-HC
- Cause MEASURED (probe paths.tsv): the 82-input re-emitted fault OR (bind u_or_0: 70 coll_fltv_i bits + ctlm + sys_face +
  mu faults + d2d transport faults) and the sys_face pin register obs_fault__ot_q sit at (668, 35) next to the E-face
  coll_fltv_i window (y 6..20); mu_dhobs mu_fault is at (561, 1383) and obs_fault_q at (399, 1277): two 1.3 - 1.5 mm
  unregistered hops (16 - 17 buffers).
- Fix: glue reach_homes sys [556, 1200, 770, 1440] for coll_flt_i, coll_fltv_i, ctlm_flt_i + internal_stations bus:
  chains (3 / 3 / 1 stations, sites from reach_rules' own route code, 214 flops), lanes coll_core__fltc 9 -> 12,
  coll_core__fltvc 9 -> 12, tt_ctlm__fltt 9 -> 10 (sticky fault lanes; reach_fix.sync_fixed_cycles: rule_broken 0, 0
  latency groups change). Only type glue + those 3 lanes / latency rows differ from S4q9d.
- File: epyc9 .../fable-fix-qc-cbglue/delta/zz_s29_qc103_s4q9d_cbgfault.json (sha aed254508723; renamed, S4q9e is FABLE-DIE-QC; rows file lanes/handoff/FABLE-FIX-QC-CBGLUE-fault-station-rows.json sha 7720eceed9a4, KNEE-HC composes the combined event) + 3 sidecars; composer mk_s4q9e.py;
  reports delta/s4q9e.report.json, s4q9e.sync.json. Gates: reach_rules glue 0 errors; plan_gate_pre + reach_fix see post.
- Needs: one bind (lanes change: LATCHECK must show exactly those 3 lane deltas as planned), then a glue kit.

## 3. glue d2d_rom store / reset_regions (-64..-152): form (B) COMPOSED 10:1x (COORD decision: I own B end to end)
- Cause MEASURED (glue a6 v2 placement, epyc2 fable-fix-qc-cbglue/probe/place_a6/out/xy.tsv): d2d_rom spans the 1.47 mm
  strip (native side y 1,300-1,400, FDI flops + 4 store SRAMs y 5-113): too few register stages.
- QC rows (event after combined S4q9e, KNEE-HC binds): lanes/handoff/FABLE-FIX-QC-CBGLUE-QC-CBG3-d2d-seam-station-rows.json
  sha 970719b75638; whole plan epyc2 fable-fix-qc-cbglue/deltaB/zz_s29_qc103_s4q9e_d2dsouth.json sha 42b8ae2b7256
  (composer ../mk_d2d_south.py TREE BASE OUT REPORT; report deltaB/d2dsouth.report.json). d2d home S end, 3 stations on
  all 17 d2d N-face buses, 17 lanes 4 -> 7. plan_gate_pre PASS 0, reach_rules 0 errors, reach_fix classes 1-5 0.
  If the base plan changes: rerun the composer on it (rows are type-local; glue must equal the glue of S4q9e).
- Pair calendar: epyc9 fable-fix-qc-cbglue/pair/{ctl,new} (run_mu833.sh on KV bind kw45/kvbind_pin_eb1e73448bd0/out_h1,
  env CST=... OT_KV_HEAD_PREP_EDGES=21 OT_KV_COMPUTE_RECORD_TXD=18 OT_KV_CAL_OFS=-2, via ot-run from localhost).
  ctl CST 4,4,4,5,4,4 -> TXDP_C 0e01120c (= bound glue today); new CST 7,7,7,8,7,7 -> TXDP_C 14011212, TXDP_K same,
  token period 293,376 same, service pad 104 -> 110, KV targets 1/3/11 + bundle change. COMPILED_NOT_QUALIFIED.
- KV side: no plan row; record lanes/handoff/FABLE-FIX-QC-CBGLUE-KV-side-d2d-seam-plus3.json sha c6a8f5df8b81.
- OPEN: (a) bind of the rows -> check XDIE_SEAM_C 7,7,7,8,7,7, one Delta per bundle, LATCHECK the 17 lanes; (b) recompile
  the pair image on the FINAL KV bind, swap d2d_cal_image_qc_pair.svh in the QC tree, both dies bind it; (c) pair co-sim /
  token gate (tools/qwen_tokfunc/xdie_bound/run_all.sh) NOT run; (d) glue kit GRT read (r310: TT >= -42 at GRT).
- WITHDRAWN form (do not redo): SRAM move + FDI stations (FDI = --phy hop, no regen rule; broke 40 reader-START refs).
- cbn / cbx fabric x-station class (cbn_q01 -270 / 248 ep, cbx_q10 _h -949 / 522 on v1 GRT repair logs): covered by
  ot_qfd_xcst_rep (r301); re-read on v2 kits with that RTL. cbn_q00 -78 same read.

## 4. Other lane's RTL (QC-CBGLUE-1116 @5e8855d43fe, r301): cal_fault_go + ot_qfd_xcst_rep, proven, merge priority.
   Its raw-branch generator is NOT used on QC (r303 form = local reset rows).

## 5. coll_n: no design change. a22 on v2 placed (geom PASS, GRT 0 overflow) 08:22 on epyc10; route result pending.
   Sign-off export when it passes: AGIdock /archive/opentallas-signed-1114 + rtx-pro.

## Next
1. KNEE-HC: adopt S4q9d (rebind clean), bind S4q9e in parallel. KIT-OPS-5 relaunches cbf_q01, cbf_q01_s2, glue.
2. Read post-CTS gates of the whole family on v2 (wave dirs intel2 ~/coord/autopilot/kit_wave/qwen_compute_<item>_*/aN).
3. Probe glue v2 ODB -> item 3 decision. Signed records -> archive.

## CODEX takeover 2026-11-16 10:20 PST — supersedes older adopt/source statements
- Active authoritative event: S4q9h, epyc2 `/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc/treeH`, plan `physical/die_plan/qwen_compute/plan_of_record/zz_s29_qc103_s4q9h.json`, sha `79bca8d5b9bb970900ff04922c97a0ff0d245aaf956ad7e4fae82253b042ae96`.
- H = F seam-station plan + corrected su_l1 geom2 equal-depth chains. Both su_l1 x_su_c_i shorter chains are now four stages along the east corridor and below lane6; max depth remains four, zero extra cycle price. Actual per-bit geometry and image reviewed; prior straight-line G failed macro overlap and is preserved.
- Crucial source correction: old treeE and published v2 lack r301 `ot_qfd_xcst_rep` and `cal_fault_go`. D/E/F binds cannot qualify those fixes and are not blanket-adopt candidates. Root directs coherent H for the next full release.
- H real cp-a source overlays: exact r301 `5e8855d43fe` qfd_c_stn.sv + qfd_sys_face_lctx3_core.sv; exact `0551428f55bee5deb5d916fb0a9fbd7782421ab6` kit_istations.py + test. Receipt `gates/treeH_overlay_receipt.json`; inventory `gates/treeH_manifest_inventory.json`, source hash `6a171b64af2fb819a188e77ddb0ac3a6d19558114d0a013831a6e6b8ea47f819`. No unexpected RTL/tool change.
- Fresh H ELAB/BIND started 10:17 via ot-run, no seed. Tag `s29q103S4Q9HBQI`; hub client PID 467756, log `~/fable-fix-qc-knee-hc/chain_s4q9h_I.client.log`; epyc2 unit `oth-ubuntu-2512480-1794853037`. Script `bin/chain_i.sh s4q9h I 0`; outputs `bind/bind_s29q103S4Q9HBQI`, `gates/`, `log/chain_s4q9h_I.log`. Then R8, LATCHECK, hcparam, G0. Actual start record captured fresh source hash and plan, seed=none.
- Old D/E/F jobs retained as pinned evidence. G stopped by exact owned unit after `gates/g_geometry_rejected.json` FAIL; no failed record overwritten.
- Still required: final KV-HG1 bind -> shared pair calendar compile CST 7,7,7,8,7,7 -> same image on QC/KV -> final QC calendar rebind + component/token gate. Current H calendar explicitly NOT programme-qualified. KV/token agents own the dependency; no source edits in running H.
- Class fixes: missing leaf_um failures on old S4Q6D are fixed in candidate plan (988 per-bit entries audited, none missing). Actual su_c failed RTL topology replay RC0; su_l1 additionally needs merged reader-driver fix 0551428 and corrected geom2 rows. New class 7ef21feb8e needs no extra H rows.

## CODEX 2026-11-16 10:34 PST — J replaces H as the active coherent candidate
- E finished: 37 strict errors = 1 expected fault R8_STALE + 24 false unsigned st_a registry mismatches + 12 REAL su_c MIF mismatches. LATCHECK 1921/1921 PASS; no adoption of this failed source.
- Root cause MIF: manifest omits existing OT_QC_SRAM_MIF. It selects MIF0 despite signed crh/prog/btab built at MIF1. Existing macro couples SUVM.MIF, parent wf_st start and all head MEMORY_READ_EXTRA; leaf-only override would be incorrect. Source H has same missing flag; immutable FAIL `gates/h_mif_profile_rejected.json`, only own H unit stopped exactly. No H source changed.
- J is a real cp-a treeH -> treeJ plus exact unsigned checker3db14d42 and one manifest define OT_QC_SRAM_MIF. Plan zz_s29_qc103_s4q9j.json has same corrected H geometry sha79bca8d5b9bb. Fresh J tag s29q103S4Q9JBQJ, script bin/chain_j.sh s4q9j J 0; client intel2 PID629124, log ~/fable-fix-qc-knee-hc/chain_s4q9j_J.client.log. Outputs bind/bind_s29q103S4Q9JBQJ and log/chain_s4q9j_J.log on epyc2 scratch3 KNEE.
- J source hash909a3b5fcf477b2650f099e9333a9554494f0a864d142af52e6fc3d6f544be8c. Inventory323916 files; exact6 source changes versusv2 = r3012RTL +055reader code/test +3dbunsigned code/test. Receipts gates/treeJ_overlay_receipt.json and treeJ_manifest_inventory.json.
- Unsigned3db fix passed24 tests and real E report replay: removes24 bogus unsigned st_a errors and retains12 genuine MIF errors (crh6/prog3/btab3), unresolved0. Normal source gate GREEN; root approval/merge lane owns integration.
- MIF profile has nonzero local latency: SU word-fetch start3->4, head memory read+1. gates/j_memory_profile_price.json records analytical effect with actual token cost PENDING. TOK-VERIFY-3 owns current one-SUVM/eight-head MIF1+CROM3 native age calibration and compiler repricing; historic +866-cycle sensitivity is not a current price. No P&R or rate claim from J yet.
- KV HG1A strict bind started10:28 on epyc10; final shared calendar remains a later source/image rebind. Current J programme is NOT qualified. Same final QC include/KV ROM64 via-map/boot targets/TXDP record must come from one final compiler output.
- Incoming shared TT PG replay fix: old tt_setup_repair reload loses PG capacity. HEAD nf15_gate owns focused fix; no running kit patched. Any DRT0255 after TT repair must distinguish that class before claiming pin/RTL failure. coll_n a22 currently live detail route; classB v2 runs do not contain r301xrep.

## Claude reset handback, 2026-11-16 — QC parked

Root ordered park. All QC children are parked: no new edits/launches/validation/retries. Progressing fleet jobs continue. Root writes global HANDOFF. Read QC-PINACCESS-O.md latest reset section for exact N43/coll_n scripts and every preserved failure.

Source: inherited epyc2 /srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/repo, branch claude/fable-fix-qc-cbglue-xdie-1116. Final44868df838a11577adfe2bf02b7df99313ed11c6 (segmented head, pinned ABI, eight unused m44s1 groups, exact native32 dependency) gate GREEN6/6 and root r334 approved; merged main3d0616c6aef. Model-only177bcb83f0d58bd50b51dfc948ac2777577479c9 gate GREEN6/6/root r338 approved. No physical adoption. General clock planner None fallback dec8cc442acfcee01c5f3f85fd363db15188ef9e gate GREEN37/root r334.

Functional mechanism: native proof token6b9d2833f9ebb135a8bc1fd55654f84da2014f6b. EXTRA9 short4+4 control128exact; actual E0req22/reply21 and W0req22/reply20 each128wrong with old9; SEG1/MEM44 E0 and MEM43 W0 each128exact. All KV_WR_PIPE1. COPY-only. Final N43 intentionally normalizes all480 read loops to43 and uses ONLY MEM44/SEG1/KV1/ALIGN3/nativeMIF1, not a MEM43 physical variant. S1D58=two29-edge8-bit rings, S2D60=two30-edge native32x64 SRAM segments; six new macros+two TLS128x64=eight/head. Legal head151.2x185.76. Full five-leaf group414.72x267.84 unchanged. Receiver-only normalization104436FF includes3060FF WROM word-skew fix; request-side shortcut rejected because read/write sampling phases would change.

ABI tooling:28 focused tests,36 reconstructed-L synthetic-frame contracts, eight shared-master candidates. Explicit full old c_i ABI + exact aliases, per-leaf bit/header/parameter/internal/reset checks; never strip pd names or waive code comparison. SEG1 loads exact native32 source and fails if missing. Synthetic replay is NOT actual future emitted-frame proof.

LIVE HEAD:
epyc2 unit oth-ubuntu-3610370-1794861923 / container ot-headseg44-kv1-mm.
Base /srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44.
runs_mm/headseg44_kv1/flow.log. Last known DRT optimization2, ~5130 intermediate violations/<10GB; NO final verdict. GRT all-layer0overflow, actual density54.2%CORE, eight clear macros. CTS implementation TT+2.27ps@770/60, FF+30; final canonical policy separate. Armed watcher local session45147 /tmp/headseg44_watch_mm_final.sh; hub log /home/ubuntu/fable-fix-qc-cbglue/headseg44_mm_final_gates.client.log. Waits own container then6_finalDB; one48GB/4thread final_gates_kv1_mm.sh -> final_nominal833/{corner_sta.json,lec/lec.json,timing_lec_outcome.json,status}. DRC separate. Do not duplicate watcher/gates. KV0 artifacts geometry only.

LIVE GROUP:
epyc2 unit oth-ubuntu-729807-1794862769 / container ot-group44-w0-route3; intel2 client1094414.
headseg44/group44/runs_route3/group44_w0_nominal/flow.log; hub intel2~/coord/tmp/group44-route3.log.
Exact804 master body (unchanged in44868), MEM44/SEG1/KV1,760inputs/302outputs. Actual833/0/25/HM0/MMTC+BC. Last known CTS done, TT+2.841ps/0; FFrepair -148.293/TNS-96576.227,429buffers improving. Actual placed review: eight macros,31%macro-subtracted fill, clear corridors, no outline growth. No watchers: final_ttff.py/final_lec.sh STAGED NOT RUN; one final full-group LEC/TT/FF/DRC still needed. Only variant0 in physical flow, not all eight.
Operational predecessor failures all preserved: helpers (four exact Tcl assets now restored,29-path closure); full MM env; make prerequisite remap attempts (all13 stage artifacts retained);12nm off-grid pins (coherently snapped). Original remote remap scope/container stopped exactly; killing ot-run client alone only detaches. Current route3 confirmed no remap. Preplace repair naturally terminated per pinned SetupLegacyBase::terminateProgress after1000+ no-progress iterations; no arbitrary cap. Pin-fix continuation omitted redundant nongating preplace limited repair privately; actual placed/full repair and all ordinary gates retained.

LIVE P3 HC2:
epyc10 /srv/opentallas-scratch2/claude/fable-fix-qc-hcfe/p3_fault_split_1116/gen/sle_hc2__cl9c4c4509__clf60c5152.
Unit oth-ubuntu-1523667-1794852278, container dpkit-sle_hc2__cl9c4c4509__clf60c5152-1524332 (+-lec async).
Last known real preGRT FF+4.808ps/0, TT+29.996,7517holdcells/403328instances; GRTpinaccess~30000groups, asyncLEC~3h CPUactive. No final routed/gate verdict. Paired PG-aware E1 p3_fault_split_e1_pg_1116 STAGED NOT RUN; baseline P2 PG-aware E1 -132.61ps/1. Source a37 default-off merged, physical adoption held. Actual placed review JSON uncommitted in existing HCFE lane; leave it.

N43 SOURCE/EMITTER (not running):
L=/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc; P=/srv/opentallas-scratch2/claude/qc-pinaccess-o.
Source L/treeN43_44868@44868. Private scoped inventory87fed6764a18ba2e470b88afa44652c4a847ebee328b279dc145a3b114190556,49 initial ASB dependencies byte-identical to J/six pinned cache artifacts. NOT publication inventory: five post-J runtime files absent from inherited manifest but separately hashed. Future final inventory required, no source publication.
Runtime L/n43_runtime_v2/asbuilt_n43_scoped_v2.json SHA4c94c85bea6bfd36b3ab3f53593f710491bd5f5583d48dd48a6cce9e103abff2.
Latest plan P/n43_event_v5/physical/die_plan/qwen_compute/plan_of_record/zz_s29_qc103_s4q9k_sunorm43_private44868_pinv5.json.
Native/count-frame constructor PASS before trim; after-trim cheap preflight session52880 outcome UNCOLLECTED at park. Emitter5 DID NOT RUN: scratch2 below50GB floor, lastfree45.94GB decimal after own unbound historical-plan pruning. No override/root fallback. Source/J and active jobs untouched. Emitter4 unit oth-ubuntu-971084-1794862920 terminal failed noncanonical feed/region layout; all attempts P/n43_emit1..4 preserved. Driver P/scoped_qc_emit_44868.py. No progressing emitter to stop.
Failures: absolute clock table outside source; missing group reset from removed pins_file; missing VMR sibling pin; noncanonical plan hierarchy. Latest v5 restores complete canonical hierarchy and unsigned reference pin reservations only, old lib/lef remain absent. No strict-bind/actual-pad/physical PASS claim.

CLOCK selected cost ZERO:
Exact468 changed C rows all same physical region under N43 and zero native CA overlap; allowed_n43_port_updates={} / allowed_n43_root_clock_updates={}. N43 selected2525 CA entries get NO phantom3rings/+833ps/counter regeneration. C2993 diagnostic3+1 and originalFAIL preserved only as diagnostic. Evidence actual mapping/table overlap, not node-count inference. FABLE-DIE-QC delta/ca_pair_diag_1116/planner_fixed/{ca_row_field_delta.json,n43_applicability_receipt.json}; canonical correction a9c9a5d1d6f68fda02eb6c976a871651147a4aea. Model177 selected_changes=[], selected edges/ps0.

COLL_N HOLD remains required:
a22 completed DRC0/antenna0/LECrc0, TT-1.09ps nominal, terminal NOT SIGNED FF-58.19ps/64endpoints. Original4final files837MB/hash receipt P/coll_n_a22_route_input/final_state. DRT0255 closed; no reroute unchanged.
Root17/18 local insertion mismatch explained by frozen affinity cohorts/fixed250ps balancing.80ps spread advisory. All-launch TT setup room over64captures min301.099ps. No existing root meets200um L1 for full bank; new root would change parent pin/model.
One reviewed/priced candidate P/hold64_priced_candidate.json + P/results/geom_review/coll_n_clock/coll_n_hold64_HB4_reservation.{json,png}:80HB4/64capture pins,8.1648um2,0cycles/0clock sinks, filler-only reservations; conditional FF+5.605/TT+52.980ps under bounded slew/load/stub envelope. Actual RC/envelope must be checked in one future pilot. NO insertion implementation or route launched. Installed detailed_route has no incremental option; supported flow continuation still needs work. No blind delay/clock offset tuning.

WRITE/PROGRAMME HOLD:
P/QC-PINACCESS-O-SU-write-return-census.{json,tsv}:96heads/9types/864 direct fields/replicas, aligned within each head/replica. Normal00 direct LRLY->u_vw; CTL/SC/STM parallel observers. Added L=Eeven24/26(heads0-3/4-7),Eodd25/27,W52/53all8. LRLY->macro commit L+u_vw1+MIF1VMR4=L+5; MIFwrite+1 included. Native ages sample a.L_vm_we AFTER LRLY; never charge LRLY3 twice. Direct-head ledger L+8. Scalar11 onlylane0 uses CTL register+return16, suffix L_CTL+22.
Native normal-write arbitration requires coincident lane0/same row+bank; duplicate offsets highest lane wins; w16 dominates/no retry. Added command-meta+write phases E43 forheads0-3/E47 for4-7, W71all8. TOKEN checking actual native/private control phase compensation. If uncompensated, coherent4cycle early-E write-tuple alignment is needed; compiler waiting cannot fix within-burst arbitration. NO pad or surcharge applied. TOKEN owns next-read sampling >=producerLRLY+L+5 reconciliation with spans/busy/read-forward terms counted once.
TOKEN also owns LOCAL4/HEAD37 default-off forwarding/paired guards and genuine checkpoint payloads. Actual tile coupon uses portbind_prefer rc14/rc15 body paths, not guessed XT1.

Current policy: canonical latest METHODOLOGY OWNER12.24c exact833ps, setup0unc/hold25unc; academic DRC0/TT>=-42/FF>=0/LECequiv. Related80ps advisory. Keep strict tool fields separate. No TT60 rerun/SS gate.


## STATE 13:5x PST (steps 2-4 of form B; retire when glue signs off)
- QC adopt bind = S4Q9JBQL (epyc2 /srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc/{treeJ,bind/bind_s29q103S4Q9JBQL}):
  carries reset leaves + fault stations + d2d seam stations + r301 RTL. regen_constants PASS: XDIE_SEAM_C 7,7,7,8,7,7,
  TXDP 14011212 in bound glue; LATCHECK 1921/1921.
- Co-sim harness: branch claude/fable-fix-qc-cbglue-xdie-1116 @ed74e6f26ae (gate GREEN 4/4, READY posted). Run:
  from localhost: ot-run --mem 64 --threads 16 --hosts epyc2 --dir TREE -- bash -c "cd TREE && JOBS=4 bash
  /srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/repo/tools/qwen_tokfunc/xdie_bound/run_binds.sh QC_BIND KV_BIND OUT"
  (TREE = full source tree, e.g. treeJ; ~8 min). Result on J + KV record bind out_h1: 8/8 expected
  (epyc2 fable-fix-qc-cbglue/xdie/j_h1). Bench limits: own profile, stand-in endpoints, no HOST/EMB ports.
- OPEN step 2: final KV bind (7yhr / KV-HG1) does not exist on the fleet (13:30). When it does: run_mu833.sh with
  CST=7,7,7,8,7,7 (env in section 3) on it -> img_bnd/d2d_cal_image.svh -> swap rtl/qwen_sys/d2d_static_20261015/
  d2d_cal_image_qc_pair.svh (QC, KNEE-HC) + KV boot targets (FABLE-DIE-KV); rerun run_binds.sh on both final binds.
- OPEN step 3b: token gate results/rtl/kv_img_mu833_1025/token_gate.sh NOT run (needs the final pair compile dir).
- OPEN step 4: no glue kit on S4q9j yet (wave on S4q6d at 13:27; asked KIT-OPS-5 to launch glue first at the adopt).
  r310 read = TT >= -42 at the GRT stage with die RC scale + overflow 0. Watch (FABLE-PD-QC-S4q9e): d2d_rom__x3 station 1
  0.44 um inside the codes SRAM halo edge -> if placement / congestion fails there, move the x3 sites 20 um west
  (rerun mk_d2d_south.py with the x3 route shifted, or edit regs_um of bus:d2d_rom__x3 / x3_generation / x3_identity).
- Baseline glue a6 (S4q6d, v2): epyc10 /srv/opentallas-scratch2/claude/ot-jobs/glue-route-civil-redfish-544246-1794849861
  in 5_1_grt 13:27; FF-corner setup WNS -324 / 35 ep = START-reset class only.
- OpenROAD repair table columns: WNS | StTNS | EnTNS | Viol endpoints | worst endpoint.

## CODEX final reset handoff 2026-11-16 — QC takeover parked on root reset order

All QC children parked. No new launches, edits, validation or source fixes after reset; only this authorized handoff. Existing admitted jobs/watchers continue. Physical details also committed in HCFE handoff 964ee76606ce3b4a9ff172e367ef760da95979c1 and FABLE-DIE-QC handoff aed5bc3611010deb7490358316e4562962b43bf6.

**Source / adoption.** Inherited branch `claude/fable-fix-qc-cbglue-xdie-1116` tip **9981db0b234fb13ac82e5c4b8f2a8a75ded3e786**: exact tail aliases/model ancestors c2f7a6c15712bc3c3dba26f122b5e6b71eaa7e23 and 38f66e2a17baabacfc5977af19ceb2f5f30dcb71; evidence-only geometry e1590349955; final9981 adds unified common+RED model plus exact96-head/storage/geometry packets, no engine RTL change. Tail38 normalGREEN4/4 (known historical fullmodel pin baseline); model9981 normal gate pending merge_ops. Tail source contains no extra fault-input wrapper FF. CTS scope source `claude/fable-fix-qc-hcfe-1115` a03a24edd878e1c40559962b4dcdadbc40e4347f: correct synchronized3_place/4_cts scope, local10STA+10dispatch pass; normal gate infrastructure ENOSPC, merge_ops owns E8 retry. No running epoch patched.

**Kf atomic adoption NOT performed.** Kf exact structural packet canonical `lanes/handoff/FABLE-FIX-QC-KNEE-HC-Kf-ready-1116.json`, SHA90b08c2ba59c8f9563e59bef51aa729523e70556fb829485b2417fdece7a330b. Plan SHAa826abb3a3fd7c2a57dc6a83e982da3cdcb9ac4ab47878b65ac32a75e601c69d, J source, strict0/R8check0/LAT1921of1921/HCPARAM20types0missing0mismatch;9FE rows noCTL. Existing G0 run PID154884 last known CPUactive; no fresh sweep, no G0PASS claim. Known sl_W5_fw.W/coll_f4.E holds remain, alongside existing clock52/st_a6/affectedSU typed holds. No blanket HC/programme hold.

Publication is the actual Kf blocker: current publishedv2 lacks2r301 RTL, and J909 inventory predates runtime assets. Fleet child `/root/fleet_flow/kv_pack` now owns normal-supported minimal J+Kf publication/guard, no full59GB copy/no ELAB. Real S2 base `/srv/opentallas-scratch2/claude/fable-fix-qc-knee-hc/l_private_1116_r2/treeL`,1.512GB/30102files, source_overlay_manifest.json inparent,49 selected bytes equal J. Exact Kf input packet S2 `l_private_1116/Kf_publication_inputs/selected_runtime_assets.json`, SHA3cfd5d765cca91b07276f4e8c3501fb851b6486d1afe8d2b36483f6eb7e24b35. ACTUAL selected assets4, notoldJ5: sidecarc71a3, derivedR838336c, extra0600980, extra146a62e. Original bound injectedAB and Kf plan copied there. Use authoritative Kf manifest; never oldJBQL/N43 tables. Original logical M path J/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_sw2_pv.json SHA86ede4003ca4. CM only has guarded inject/check, no make: kv_pack owns proper lineage/content revalidation helper, not manual hash substitution; KP supported make. Atomic helper intel2 `/srv/opentallas-scratch2/claude/tools-converge/apply_reviewed_tree_marker_1116.py`: fresh .coord.lock config+marker transaction, normal durable TC guard, exact old source/event, preserve holds and existing jobs, no state.json edits. Root approves/applies only once source/tuple ready.

**L private binds.** First S2 `l_private_1116` unit807499 failed2 because sidecar count-frame paths resolve from qwen_compute root; missing feed_s29.json/regions_s29.json,52KB. Preserved. Fresh S2 `l_private_1116_r2` unit1056142-1794873842/client3543758 failed58 after1576s: ONE `PARAM_REGEN coll_regen.py: No module named sc_hard_params`;48 tailHI/SKEW +9SC_HARD_PINREG mismatches are downstream of regen failure, not new hardware mismatches. Required closure: copy all12 small `.py` siblings under J/physical/die_plan/qwen_compute/bind (incl sc_hard_params.py and qc_fabric_transport.py),~60KB; Fleet publisher informed. Preserve r2 failure. Next fresh source/output epoch only, same49 eligible cache/no ELAB/no3h clock derive; all runtime/TMP/bind must stay real S2, never J/root-backed S3. No L adoption.

**Tail four physical views.** Real source S2 CBGLUE/tail1_params/src_38f66, exact J selected dependencies plus4 pure aliases. All4 actual162x162/fiveSRAM plans rendered/viewed PASS-COND, min macro gap20.304um/halo5.4. H17N9S10 unit331251 and H16N9S11 unit356829 completed route0/DRC0. Canonical final normal signoff fixedTT250/FF202.5,833/0/25 produced real internal hold failures: H17 TT+45.05/coreFF−15.69/327 (300D/27RESETN); H16S11 TT+61.17/coreFF−8.65/171 (146D/24RESETN/1SETN), all trunc0/err0. FullIO−88.09/−76.79 advisory. Reports tail1_params/final_gates/*/core_signoff. No SIGNED views. Other H15N9S10 unit652039 and H16N9S10 unit652848 route clients exit0; canonical final gates NOT run/metrics NOT collected. Do not infer family closure.

Minimum existing-RCX tail diagnostic completed: all327 H17 captures have TT all-start max slack≥343.400421; all171 H16≥432.146942. Data tail1_params/hold_diagnosis/*/{ff/endpoints.tsv,tt/setup_room.tsv}. One HB4/capture model: FFmin29.8081, TTmax171.239 at slew≤320/load≤2.88fF;132.796 TT only through160ps and must not be transferred blindly.0 cycles/clock sinks. H17 actual ODB geometry extraction unit1462841 PASS; reservation job1688072-1794876298 completed under tail1_params/hold_geometry/qc_tail1_h17_n9_s10/{reservation.json,reservation.png}. H17 image NOT YET LOOKED; NO insertion/route. Actual sourceODB/pin centers and rows,327 cells, conditional model. Generic helper copy reserve17.py uses correct171.239.

H16 reservation image viewed by parent+ABI;171 cells17.45226um2,252 filler candidates,max center distance2.178um,zero functional overlap. ONE structural insertion PASS unit1737364-1794876506, S2 QC-PINACCESS-O/tail_h16_hold171_geometry/structural_insert1,171HB4/252fillers, capture placement/non-target terms/newbuffer chains/nativePG assertionsPASS. Original sourceODB read-only. Inventory extraction PASS unit1760542-1794876618. Actual audit/render v2 already launched at reset, tool session27741, coordinator `/tmp/qc-h16-audit-compare2.log`; allow continue, completion and actual-image LOOK pending. v1 audit failed only new-name hierarchy assumption; v2 uses exact bbox/basename/chain. Inventory extractor reused inserted_cells.tsv; full actual inventory preserved audit_inserted_cells.tsv and mapping reconstruction explicit. No route/CTS/STA of inserted candidate. Generic helpers ep2P/qc_hold_insert_{prepare_generic.py,body.tcl}, explicitD/RESETN/SETN/wd_in*, actual-driver lookup; model helper qc_hold_reservation_model_v2.py.

**W0/head/P3.** Full five-leaf W0 DRC0 but canonical TT+12.40/REAL internalFF−16.89/858 (842D/13RESETN/3nativewd), no IO starts, complete census. All858 TT headroom toowner−42≥306.728ps. Preserve source804/44868/golden failure. All858 HB4 legal reservation now found: first846≤5um;12 needed5.985–7.173um, outputload estimate1.938–2.243fF≤2.88. Exact area87.56748um2/0cycles/clock sinks. Source collateral E10P/coll_n_clock_diag/{hb4_liberty_model,hb4_transition_bound}. Baseline caps/slews FF.802909/56.825, TT.73979/79.201; newHB4A envelope remains actual-measurement condition; conservatively use171.239 unless postinsertTT≤160 verified. W0 geometry personally viewed by physical owner; NO insertion/pilot launched. Remote receipts group44/hold858/reservation_complete and insertion_prepared_v2/insert.tcl. Completed wire model LOCAL ONLY `/tmp/group44prep/model_hold858.py` and reservation858_complete/microarch_price.json, not uploaded/committed; must apply unifiedmodel/qualified electrical domain before pilot. Original W0 asyncLEC unit1007791/client3517546 lastknownhyp9. Same-frame inventory disproves M6/M7calibration cause (layers unused); normal GRT estimate vs extracted drift, no RC/clock waiver.

W1 distinct248-output production form prepared ONLY group44/w1_44868:400MB source/spec/reviewed image/canonical runner, same414.72x267.84/eightmacro/760in248out. W0 has54 additional LRLY observers/302out; W1–7 exact graph under1008bit permutations but need distinct248-port physical view. Source14 files/nativeassets equal44868, -DSYNTHESIS only. No W1 launch. Actual W0 output5.532GiB, W1 budget7GiB. E2 S2 last64.6GiB leaves14.6 above50; other growth not reserved; E7 below50. NEVER root-backed E2S3 output.

Head original unit3610370/containerot-headseg44-kv1-mm continues; last DRT50@70%/5710 transient. Existing watcherPID24246/session45147 sleeping, no finalSTA yet. Proven5585 IO-only hold cells,581 in hot192um2 explain90.59→69.07% counterfactual fill; futurea03CTSscopefix, no livepatch/outlinegrowth/retry.

P3 GRT DB472.5MB closed, LEC111691/111691EQ. Prior+2.85/−.01 policy was staleP2 and withdrawn. Actual PG-aware fixedE1 TT−64.25/39→+16.84/0,+76cells, actual8dfreplay; P2sameE1−132.61. BC fixedE1 actual6internal−24.285740,port/oport0/trunc0err0 (ordinarywd640 worst, reset-removal classtoo). Current ONE qualified3725 native trial E10 HCFE/p3_fault_split_e1_hold_3725_1116/kit, unit1642495-1794876664/client23928,32GB4threads; nativeTC+39.045906 has knownRCbasis difference22.2059 fromFX1.5. Own nativeRC/SDC/TT250FF202.5,20/20 physical repair target, TTfloor−42. RSZ sees26258 below20 but only6 negative; measure real addedcellcost, never6-only claim. Firstiteration0lastknown. Atomic ownODB write only valid, wrapper DOES NOT launch DRT. Originalcallback continues async. Fixed image reviewed. Next collect repair/TT/internalFF, then supported exact originalmake/GRT183 continuation ordinaryroute, no source/resetstyle/constraint waiver.

**Coll_n hold80.** Pilot2 unit492248 terminal routePASS/DRC0, ODB683MB+V84MB,24.5GBpeak/~70min. GRT144 changed nets/no clocknets; DRT retained oldguides/wires and maytoucholdnets (no selectiveDRTflag). Same golden constraint SHA65a953; implementation6_final.sdc not substituted. Signoff unit1797052-1794876763/session95926 live at reset; TT cornerdone but numbers unread, FF/terminal unread. LEC2 unit1842966 UNPROVEN2 duephysical-only TAPCELL absentYosys design, not logicalcounterexample; needs normal physical-cell-clean export on resume, no reroute. LEC1 frontendNOTRUN outside-kitnetlist, isolatedlec_kit fixedthat. Originalfailure/input preserved.

**Producer closure / normalized epoch.** QC-PINACCESS branch finaladfd9688bb05ec8d16742b32fb7d6e63ea9d8b08. Originalcf532 normal6FAIL were real optional kit_rtl.json FileNotFoundError, fixed; all6 localPASS, real stageorder94PASS/mutation12PASS. Finaladfd NORMALRED1: test_kit_wave_nohub::test_place_async_and_otrun_have_the_guard asserts exact old function signature, added argument breaks literal fixture. Mainpasses; preserve nohub guard and update meaningful AST/signature regression on resume, then ONE finalnewSHA normalgate. Trace E8 mq-gate/slot0/mq/failure-output/gc-adfd9688bb-s1972-1794877010746729356.log. No fix after reset. PackageKf must carry exact final producer files/helper plus approved PG/clock metadata; not scheduler-only. No adfd adoption yet.

Common+RED prospective assets P/joint43_common_red_v2 receipt3bdc22edeec20fcc2ff7f09a05ef6b76607f945360feb9b668ae782ab70c1773,2148complete R8 rows,36ABIcontracts/281aliases20895bits,133386 addedFF/44729.66124um2 beforeclock/hold;96-head metadata corrected and oldbad receipt preserved. Plan delta c899cffa4e38e38fd3daecc54f5a74cfb9790928f0e37b7d0214e5de3cc1c68e touches12padtypes/36group updates only, retains rootclock/lane/reset/START/CST/TXDP, selectedN43clockcost0(nooldC2993graft). Source scratch draft S2 KNEE/joint_common_red_1116/tree1.624GB/30247files/cache49same, notpublished/notadopted. First unlaunched plan had my wrong relay_sites_um key; preserved unused. Correct NEW plan `.../plan_of_record/zz_s29_qc103_l_common43_red_sites_v2_prospective.json` SHA263307a6fea7c027045009943fff27e1d1fd76d4015542b7fc88b7274b91bb89,81156 correctlymergedrelay_sites, receiptplan_composition_v2.json. No GEN/bind launched. Draft lacks final producer/CTS tool integration and dynamic bind siblings; do not freeze/use oldstage receipt aspublication inventory. No extra5472FF collector-cohort pad adopted.

**TOKEN/ABI.** Actual MEM44 oneHEAD+nativeVM/CROM/SFUs proof fd2d806cb83:640exactFP32/80packbeats/49SFUwords,fusedSILU/RSQ/COPY,true22+21,MIF1/ALIGN3/EXTRA44/SEG1/KV1; KVFP8finish excluded. Collector G2 legal markers K64/V128/Q64 passed; wronginactivehead0kind→8typederrors/window→8missing, fault0;g3+2E fullmask8K/16V/8Q passed but NOT codec/programmeproof. G2/g3 lowbyte markers not actual formatter contract. Actual formatter wants FP8-representableFP32 +position/dim packedaddresses; TOKEN owns real local-dimension adapter, default0/0FF/0edges, sourcegate/component pending. Never adopt earlyEcollectorpad/quota changes from intermediate packet counts. ABI inversecodec254finiteFP8 codes passed exactencode; four independent512-bit golden words atP/formatter_reassembly1116/inverse. Candidate formatter packet prepared local/tmp/qc-formatter-candidate1116,11cases, sourceSHA263569a4d3be5547f13f0f7ac4e558e2fb4af353a2e3a2c7708257e1d8ff2857, NEVERlaunched; TOKEN actualproducer corpus/slots authority. Adapter3RTLfiles uncommitted inTOKENclone, ABI didnotedit. All ABI jobs parked except alreadyrunningH16audit.

**Clock diagnostic only.** Comb unit3438192-1794867000 CHAIN_DONE and gate/sta/die_sta_related.json exists, verdictUNREAD at reset. Template3512544-1794867366 lastBIND_C0/finalSTA notyetexists. BothCA2993/0,MC0,depth8=34. Diagnostic sums7493→7243→7271 nottokenprice; nativeN43selecteddelta0/noCtablegraft. See FABLE-DIE handoff aed5bc3.

Owner questions: none newly blocking. Procedural failure: istations removed6.10GB aborted .git-only clone without required2dda predeleteguard; acknowledged toFleet/root, no postdeleteALLOW substitute/furtherdeletes. ActiveP/r2/source/jobs unaffected; inventory preservedretired_empty_clone_1116. Do not repeat. Real S2 floor50 mandatory; avoid new large copies until currentsignoff/sourcepackage growth reconciled.

## Codex take-over 2026-11-21 17:00 PST

V1 Glue AP `1c68d99bc060`, epyc8 `oth-ubuntu-501096-1795277186`, exited 6 at 17:00. The actual GRT TT gate stopped at −161.47 < −150 ps after repair; detailed routing did not start. LEC exited 0. The run used 833 ps. GRT native CCC was 307,901/400,000 non-taps with zero PG openings and antenna violations. The ordinary +66.31 GRT stage report is FF. Scoped internal FF immediately after GRT repair was +40.07, zero violations. The work directory was cleaned by its runner; exact terminal `autopilot/jobs/1c68d99bc060/a1.log` and E8 retained logs/reports `/srv/opentallas-scratch2/claude/ot-job-failed-logs/glue-route-outgoing-giraffe-501855-1795277187`.

The exact GRT setup path is `u_record.u_1148/Q` to `tcyc[31]`, with counter OR depth after four long buffering hops. The already merged `b774adc1a2a` (main `2966b8cdf0c`) separates the increment from record-driven start/clear. The failed source predates it. The V2 successor source is staged on E2 at `/srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_v2r10_glue_keep_b774`; reviewed plan image `fam-qc-cb-r2/glue_tcyc_step/candidate_review.png`. Official private spec returns DRAIN with no eligible gen hosts (`glue_v2_keep_spec.log`), so the source change has no physical read yet. Further private counter variants passed sequential equivalence but had mixed generic mapped depth. No further RTL change was adopted.

Exact stock-basis E2 pre-GRT hold experiment `glue_chunk_e2_r3.log` exited 0. The six 1,000-cell RR chunks plus unchanged base and cross-tap passes use 15,410 hold cells, compared with ~45,511 in the uncapped run. Scoped internal violations are zero, cross-tap guard +45.005 ps and measured TT remains −50.234 ps. Boundary hold remains visible. Use as an independent optional future physical lever. It did not enter the failed job.


For the separate token alignment task, E7 physical geometry traced 524/524 X3 local D1 bits of the retained V1 `3_place`, the same local bank name emitted by current V2. Direct source-to-capture width max 210.365 µm; keeping existing repeaters leaves max new splice 98.155 µm. TSV and reviewed image `fam-qc-cb-r2/glue_x3_geometry/`, exact unit 182975. The native valid-only D1 physical read (4145200) gives final capture x308.44 from upstream shared pad Q x135.71. Existing y610 corridor allows same-polarity repeaters without another registered cycle. Token owns end-to-end GEN, calendar and age changes. No Glue transport changes were adopted here.

## November 22 late-morning Glue continuation

V2 wave attempt 5 AP 05ca36d93864 reached DRC0 at 833 ps. Minimal setup TT −93.36 ps is `rom_qr[33]` to `dh_prog_a[108]` through twelve route repeaters. Internal FF is −4.55 ps on two hard SRAM write-data pins, bits 323 and 319. The automatic ECO is in DRT, after GRT TT −94.46. It is a live run. The separate E8 attempt 1 AP 16ce96ed175e has pre-payload admission waits and an exact reviewed ISSUES row for its 10,225-sink clk_t19 and 1,135.03 µm own-clock reach.

E9 `fam-qc-cb-r2/nov22_glue_clock` contains three independently scoped physical options. Its exact in-memory production clock assignment stock to central+19 reduced cap debt from 18,254 to 977. The remaining bottom clk_t1 has 1,977 sinks. An independent +20 replay is queued. The 583-site FDI capture re-seat brings inbound maximum 680.13→386.37 µm with downstream 361.04 µm. The separate 146-site ROM/program re-seat brings the 128 selected branches 1114.34→480.06 µm while preserving the other cone envelope. Both site images were reviewed. The ROM candidate requires fresh timing and retains some above-limit geometry.

E10 `fam-qc-cb-r4/nov22_v4_sites/p7c5rt_{fdi,rom}.json` are independent exact-geometry projections onto the strict/LAT-green QC p7c5rt parent. No lane/port/cycle changes, and no new route from them. Token's private service patch preserves the relevant net names in source. Check actual mapped placement in the chosen combined form. The old strict E7 b774 counter correction passes all 1,921 LAT checks. Its a087 factory-compatible rebind is queued rather than bypassing the current tool floor.
