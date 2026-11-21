# FABLE-FIX-S81-SVC handoff (started 2026-11-20 23:20 PST; newest state first)

Owner of the S81 svc family (16 types: svc_hi rs t1-t6, pvso_entry t1-t2, svc_lo rs t1-t7, rs_w t1). Succeeds S81-SVC-R4 / FABLE-FIX-S81-SVC-R3 / -R2.
Nothing pushed to main. Nothing signed, nothing exported.

## STOOD DOWN 11-21 01:35 PST (context budget). Successor: assigned by COORD (none running). Read this block first.
- Census NOT finished. All 3 jobs are alive on epyc9 (ot-run clients 2565092 hi rs t4, 3777274 lo rs t7, 2565094 pvso_entry t1). hi rs t4 and
  pvso t1 have sat 40+ min in the synth abc step on ONE module, `ot_bind_native_4c805a5536bda0930879099e` = instance g_u_rsv_NN_u_u_att_land
  (the u_att landing glue: 374 word-level cells, 428k wire bits). It may take hours or not end. If it has not moved by about 04:00: cancel
  those units (ot-run --cancel <unit from <type>.otrun.log>), add `blackbox ot_bind_native_4c805a5536bda0930879099e` to the blackbox list in
  mkcensus.py (count that module on its own from bind_r8c/rtl/native_glue/<name>.json, or with `synth -noabc`), relaunch census.sh.
- Unattended poster epyc9 PID 541106 (census/cpost.sh, 16 h cap) posts a `CENSUS` line per type when its job ends (runs census/rd.py;
  rd.py is untested on real output: check its S_att sum against `<type>.hier.txt`).
- Posts of this lane to read: 11-20 23:32 (MPL closed, J5 flat bodies), 23:41 (H8 static geometry), 11-21 00:0x ACK, 01:2x SPLIT PROPOSAL for J7.
- Unsplit-H8 proof chain epyc10 PID 618307 still waits; J6 gate candC3c ended BIND_RC=2 (stale dead-input defines) and candC3d exited 143, so
  it will most likely end at its 12 h cap with one post. Harmless; kill the exact PID after a cmdline check if not wanted.
- Not done: split plan rows (none written), split half build / sign-off / export, J7 family rows. Section B below is the design to start from.

## ORDER CHANGE (COORD 11-20 23:45, from FABLE-CLOSURE): split svc into types of 400k cells or fewer
No outline growth, cuts at natural hierarchy boundaries, registered crossings (+cycles pre-approved). Census by hierarchy first; prove one
split half to sign-off; family rows go to J7 (not J6).

## State 11-21 00:25 PST
A. CENSUS RUNNING: epyc9 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-1121/census/` (mkcensus.py, census.sh; 3 ot-run jobs, clients
   2565092 hi rs t4, 2565093 lo rs t7, 2565094 pvso_entry t1). Hierarchical mapped yosys synth (no flatten) of the H8 bound type RTL from
   the svc-green bind epyc9 fable-fix-s81-svc-r3/bind_r8c; hard cores black-boxed by name, SRAMs read from their _tt.lib. census.sh
   retries when a module is missing from bind.f (adds the defining file from ksrc/rtl to <type>.extra). Result = `<type>.hier.txt`
   (`stat -top`: cells per module including submodules) and `<type>.json`. Marker `CENSUS_RC=0 <type>` in `<type>.otrun.log`.
   The bound top is already dissolved: its direct children are the natural units (dsdv_svc_sx, dsdv_svc_rs_up, dsdv_svc_sot, dsdv_svc_p_source,
   dsdv_svc_mem_la, dsdv_sm_gw, dsfd_svc_pc x2, attn_staging x2, relays, landings); instance names keep the path (u_u_rsv_NN_u_u_att_...),
   so sum the top-level cells by the `_u_att_` prefix to get the S_att share.
B. THE CUT ALREADY EXISTS ON MAIN (not used by any plan): `rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_cut.sv`, opt-in `-DOT_SVC_ATTCUT`
   (HARD-S81-SVC-1 11-13, commit 52dc675ba9, lock-step bench tools/s81_dv/svc_rs/run_att_cut.sh, CUTMUT 1/2 caught). dsdv_svc_att sits
   behind a registered boundary: dn stream in +1, every lane to the slice +1 (2 edges end to end); the 2 dsfd_svc_pc page-cache lanes are not
   registered and belong to the att part. Earlier estimate (SVC-BAND-3, epyc7 s81-cores-2/svc/plan_delta/DELTA_README.txt): S_att about
   261-269k, S_rs about 179k synthesised with providers hard; placed 555-819k for the unsplit H8 shell. Not built, never bound.
   So the J7 svc rows are: per svc type two partition types (S_att = part prefix ...u_att with its hard cores hcore / merge_h4 / tr_x and
   the att SRAMs; S_rs = the rest with sml / smd / smc / smr / sx_hrow), the two rectangles tiling the present outline (no growth),
   define OT_SVC_ATTCUT, pin-cycle deltas in +1 / out +1 on the att lanes, seam pins + clock / reset rows for both halves, dead-input
   re-proof under the new define set, die top unchanged (cut is inside the type). lo types probably need a third part (IRG / ctrl:
   32 idx_hslice_fp + dsfd_ctrl_rg3 + eng taps) - decide from the lo rs t7 census. NONE of these rows are written yet.
C. MPL-0020: closed, D8i-only (see post 11-20 23:32). J5 svc rows are the flat H16 body (3.4-4.9 M cells), never finished place; J6 C3c/C3d
   carries the unsplit H8 form for all 16 types (0 overlap, 0 out of outline, min channel 8.64 um, outlines = J5; post 23:41).
D. RUNNING: private unsplit-H8 proof chain epyc10 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-1121/chain.sh` PID 618307 (log chain.log,
   12 h cap): waits for `^BIND_RC=0` in s81-j6/logs/gate_candC3d.log (else C3c) -> prep.py (fresh_kit on the J6 tree + wave gen env/args)
   -> run_kit.sh place 48 8 -> route 64 8; posts `H8-PROOF chain` lines. It measures the unsplit H8 shell (real cell count, place); it is
   not the split proof. Untested: clock-landing sidecar choice (h2_2249/landed_sidecar_j6_rom_h8.json), --trial/--util flags.
   Stop it (kill exact PID 618307 after a cmdline check; ot-run --cancel its unit) if COORD does not want the unsplit evidence.

## Next steps
1. Read the census: per type, top-level children sorted by cells; S_att vs S_rs sums; confirm each half <= 400k mapped (placed is about
   1.3-1.5x synth on svc: 261k synth may place near 400k, so check the att half first; if over, move the 4 attn_tr_x bands or the landing
   rings out as the next cut).
2. Write the split plan delta on the J6 tree form (plan_delta.py format, see epyc10 s81-j6/rows/svc/j6_delta_svc.json) for ONE type first
   (svc_hi_dsdv_svc_rs__t4): two partition types, seam at a macro channel; private strict bind + LATCHECK; fresh_kit proof kit of the S_rs
   half (smaller) to sign-off (DRC 0, TT >= -42 ps, internal FF hold >= 0, LEC); export.
3. Give S81-J6-ASSEMBLY-R2 the 16-type family rows for J7.

## Files
- epyc9 fable-fix-s81-svc-1121/census/ (census), epyc10 fable-fix-s81-svc-1121/ (chain, prep.py).
- Predecessors (read only): epyc9 fable-fix-s81-svc-r2 (ksrc private source, wt lane clone with FETCH_HEAD = attcut branch), -r3 (bind_r8c).
- Old 11-19 text of this file: lanes/handoff/FABLE-FIX-S81-SVC-1119-archive.md.
