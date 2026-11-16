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
