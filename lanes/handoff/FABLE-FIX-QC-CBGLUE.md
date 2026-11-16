# FABLE-FIX-QC-CBGLUE handoff (owner of the QC cb / glue family + coll_n)

Updated 2026-11-16 09:0x PST. Commits from here on end with the Opus 5.5 trailer (COORD 08:xx).
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

## 3. glue d2d_rom store / reset_regions (-64..-152, ~400 ep): NOT fixed, decision needs the v2 kit
- WITHDRAWN form (do not redo): moving the 4 d2d store SRAMs to the N band + stations on the 5 FDI buses. FDI +3 cycles
  changes the PHY hop of the compiled static link calendars (tools/qwen_split/d2d_link_calendar.py --phy / --txl;
  regen_constants.py has no FDI rule), on both dies. It also broke 40 reader-START raw reset references (reach class 5).
- The probe ODB is gone (kit cleaned 05:36), endpoints had no coordinates. Next: glue a6 (v2 tree, S4q6d plan, epyc10
  .../s29q103S4Q6D/items/glue/attempt_6/gen/glue, in synth/LEC at 08:55) -> rerun the probe
  (epyc2 qc-cbglue-1116/probe/run_probe.sh; fix locof for escaped names so store / reset_regions flops get xy) on its
  post-CTS ODB. Then choose: (a) item_env OT_TT_SETUP_DESIGN=1 OT_TT_SETUP_MARGIN=30 (hc2 closed -178 -> -32 with it);
  (b) region rows for u_d2d_rom store flops next to the SRAMs; (c) RTL register (needs bench + LEC + link latency proof).
- cbn_q00 relay hop -78: read on the v2 kits now running (cbn_q01 a2, cbn_q11 a2 launched 08:2x-08:3x); no row yet.

## 4. Other lane's RTL (QC-CBGLUE-1116 @5e8855d43fe, r301): cal_fault_go + ot_qfd_xcst_rep, proven, merge priority.
   Its raw-branch generator is NOT used on QC (r303 form = local reset rows).

## 5. coll_n: no design change. a22 on v2 placed (geom PASS, GRT 0 overflow) 08:22 on epyc10; route result pending.
   Sign-off export when it passes: AGIdock /archive/opentallas-signed-1114 + rtx-pro.

## Next
1. KNEE-HC: adopt S4q9d (rebind clean), bind S4q9e in parallel. KIT-OPS-5 relaunches cbf_q01, cbf_q01_s2, glue.
2. Read post-CTS gates of the whole family on v2 (wave dirs intel2 ~/coord/autopilot/kit_wave/qwen_compute_<item>_*/aN).
3. Probe glue v2 ODB -> item 3 decision. Signed records -> archive.
