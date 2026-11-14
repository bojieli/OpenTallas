# SVC-BAND-3 handoff (sub-lane of S81-CORES-2; S81 svc family) -- 2026-11-13 20:25 PST, STOPPED (no job of mine running)

## Done
- GEN_LINT class fix READY claude/svc-band-3-genlint-1113@2845e7a35b (hub origin; base main 30f4ab558f; 2 commits):
  e58141a8e3 = kit_rtl post steps carried by the running kit_wave.py (tools/autopilot/kit_rtl_post.d/), not looked up
  in the frozen wave source. 2845e7a35b = svc_lo IRG PR=1 needs the OT_IDX_HSLICE_FASTPAD + FP_CS defines (new step
  s81_svc_pr_irg.sh). Proven on the frozen wave source: hi pvso_entry t1, lo rs t2, lo rs t5 all GEN_LINT PASS 0 issues.
  Control without the fix: no closure receipt. Logs intel2 ~/s81-cores-2-logs/svcb3_genlint*_*.log.
- ASKs posted: ROOT-MERGE merge; KIT-OPS-2 deploys kit_rtl_post.d into the runtime intel2 kw38/rt and releases
  SVC-MACRO-1113. Per S81-CORES-2: no big relaunch of the flat H16 bodies (about 4.1 M cells).
- Plan delta for DIE-S81-90: epyc7 /srv/opentallas-scratch2/claude/s81-cores-2/svc/plan_delta/ (DELTA_README.txt,
  delta_svc_lo_facepack_1113.py, plan_svc_lo_facepack_1113.json, irg_donor_views_182207/). Covers svc_lo t1;
  the other lo types need a name map, and hi needs its own pack.

## Band build (face-aware 2013.12 x 2851.20): BLOCKED at strict bind, step 3
Script epyc7 .../svc/band_bind.sh (stages: bind.py all --strict -> kit-rtl lo t1 + post steps -> gen -> GEN_LINT).
Manifest epyc7 .../svc/band_bind/asbuilt_band.json = the wave ready12b-A manifest with these changes:
  + event_por provider rtl_defines (OT_SVC_H8, _H8_REUSE_RT2, _MERGE_H4, _ATT_MEM_MACRO, OT_IDX_HSLICE_FASTPAD/_FP_CS/
    _HARD, OT_SVC_ATT_RDPIPE);
  + 4 H8 source files (dsdv_svc_mem_ar/lr, ot_s81_su_sms_fold2, ot_s81_svc_attn_s); with them the elab PASSES;
  - ot_hdc_v41x_dly/kreg/vdly removed from slang_parameterized_blackboxes (the H8 elab has no instance of them).
Current stop (unit oth-ubuntu-806774, log intel2 ~/s81-cores-2-logs/svcb3_band_bind2.log, bind_all.log):
  "bind: ERROR stale dead-input preprocessor defines" (tools/die_plan/dead_inputs.py:73). The plan's dead-input proofs
  (svc dsdv_svc_sx / rs_up / pv_so) were made with the H16 define set.
NEXT: (1) re-prove the dead inputs under the provider define set with tools/die_plan/s81_dead_prove.py (it needs a
  repository-relative manifest, so use a writable src copy or worktree holding asbuilt_band.json; precedent
  claude/s81-dead-reprove2-1112@8fa82e457d), then re-point the plan's dead_inputs proof shas.
  (2) Re-run band_bind.sh; it reuses asbuilt_band.json.
  (3) Re-point the provider lef/lib in the plan from the missing prov_1109 paths to the S81-SVCRS-4 rows (E9
  s81-svcrs-4/prov/run/<row>/sign_*/views_*; pack native_view per inst; 12 SIGNED, 9 LOCAL_PASS_NEEDS_PARENT) and stage
  them where gen runs.
  (4) Then gen -> wave flow to finish under R-MINIMAL; view the place render.
Estimate before build: parent soft about 290k+ per type; R-CAP 555-819k placed, still over the cap. The S_att | S_rs split
  is in DELTA_README.txt.

## Files / worktree
- epyc7 /srv/opentallas-scratch2/claude/s81-cores-2/svc/wt (sparse worktree of wt/hard-s81-svc-1, branch above)
- epyc7 .../svc/{proof,proof2,band_bind,plan_delta}, scripts proof_a.sh, proof_b.sh, band_bind.sh, elab_fix.sh

## Update 2026-11-13 22
- Bind iterations d-f: errors 1211 -> 488.
  - Fixed: dissolve chain; files + dsdv_idx_rg2.sv, ot_s81c_attn_h8_rt2.sv, ot_s81_svc_merge_h4.sv, ot_s81_svc_idx_hslice_fp.sv.
  - hcore/H4/TRX/IRG now bind as leaves on 14 of the 16 svc types.
  - Last run: unit oth-ubuntu-2665394-1794636127, log intel2 ~/s81-cores-2-logs/svcb3_band_bind_h8f.log, report epyc7 .../svc/band_bind_h8/out/bind_report.json.
- BLOCKER (die netlist, not mine to change): physical/die_plan/s81/bind/inputs/die_b178_lfcs.v (tools/s81_dv/dv_bind.py) wires the svc gather ring at the H16 width.
  - Example: u_rsv_02 .gi_d_n(w_sg_03_02_lnd[2132:1]), dsdv_svc_busland_2133, RS_FACE_W go_d 2132 in tools/s81_dv/dv_spare_out.py.
  - Under OT_SVC_H8 the fv wrappers take H*132+20 = 1076 bits, so 26,540 bits of live dsdv_svc_sx.gi_d faces bind as literal 0 (TIED errors). The H8 dead-input proof correctly does not cover them.
  - Needs: the die top regenerated with H8 gather lanes (1076 b) by the dv_bind owner.
- Smaller remaining classes (fix after the regen):
  - (1) pvso_entry plan types list H16 heads g_h[8..15] (32 per type) that H8 does not have: drop them from the plan.
  - (2) svc_lo t7 IRG sits under dsdv_idx_rg3_nq (u_irg_07): add it to dissolve.
  - (3) structural IRG literal ties need declared_ties with RTL proof: hslice cs_in/cf_in chain start 0, first, ksadd b/cin, rg2_m1k wd/ra/wa/re/we, v41x_dly d, mem_ar wa.
  - (4) epyc7 has NO orfs docker image: 112 native-glue EMIT errors ("Unable to find image openroad/orfs:asap7lock"). The bind and the kit build must run on epyc8 or another host with the image. Lane dir copy to epyc8 at the same path is in progress.
- NOT launched: the band build (no clean bind). Launcher ready: epyc7 .../svc/band_build_h8.sh (run_kit route = route + finish + signoff, OT_HOLD_STRUCTURAL_ADVISORY=1 NONPORT_HOLD=1).

Resume: after the die top is regenerated for H8, point asbuilt_band_h8.json netlist at it, apply (1)-(3), rerun band_bind_h8.sh on epyc8, then band_build_h8.sh via ot-run.
