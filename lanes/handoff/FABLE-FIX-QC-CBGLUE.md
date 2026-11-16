# FABLE-FIX-QC-CBGLUE handoff (owner of the QC cb / glue family + coll_n)

Updated 2026-11-16 10:1x PST. Commits from here on end with the Opus 5.5 trailer (COORD 08:xx).
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

