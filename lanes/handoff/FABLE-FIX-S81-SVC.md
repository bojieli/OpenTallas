# FABLE-FIX-S81-SVC handoff (started 2026-11-20 23:20 PST; newest state first)

Owner of the S81 svc family (16 types: svc_hi rs t1-t6, pvso_entry t1-t2, svc_lo rs t1-t7, rs_w t1). Succeeds S81-SVC-R4 / FABLE-FIX-S81-SVC-R3 / -R2
(read those for the H8 bind history). Nothing pushed to main. Nothing signed, nothing exported.

## State 11-21 00:10 PST
1. MPL-0020: CLOSED for the current plan. All 11 svc macro_place fails of the last 24 h are event 465cb9fe2d3 (D8i) rows (one older: 3fa87b84b18).
   Cause (R3, confirmed): D8i bound RTL reads wq rd[255:0] zero-padded, synthesis drops wq macro g_m[2]. Not geometry.
   J5 224567138ab: hi rs t4 / t5 / t6, lo rs_w t1, pvso_entry t2 passed 2_2_floorplan_macro with 0 MPL-0020 (t4: 148 macros fixed).
   The other J5 svc rows were still in synth / 2_1 at 23:30; all read rd[340:0].
2. REAL BLOCKER: the J5 svc rows are the flat H16 body (72 hard cores + SRAMs, 3.4-4.9 M std cells; hi rs t4 native_cell_count 3,397,389).
   No svc row has ever finished the place stage (about 100 attempts, 9 events). Measured 23:30: hi rs t6 3_1 GPL diverging (overflow 0.2246 at
   iter 600, then HPWL x7.5, overflow 0.36 at iter 2050; OT_GPL_HPWL_RATIO 1.3 will fail it); pvso_entry t2 3_3 overflow stalls 0.46, routability
   congestion 1.5, virtual WNS -2.6 ns; lo rs_w t1 GPL utilisation 68 % vs density 0.5. I cancelled nothing; S81-DIE-R5 owns J5 ops.
   Do not expect a J5 svc sign-off. The wave representative svc_hi_dsdv_svc_rs__t4 a2 (intel1 unit oth-ubuntu-4054260-1795225734) is left running.
3. FIX = J6 H8 form, already in J6 candC3c / candC3d (epyc10 s81-j6/rows/svc/j6_delta_svc.json: 16 partition types replaced, hard providers
   sml_fold2 / smd_fold2 / merge_h4 / tr_x / smc / smr / idx_hslice_fp with prov_1119 signed views; manifest ops; reprove39). J6 needs no more rows from this lane.
   Earlier estimates of the H8 soft shell: hi rs 555-614k cells, lo 732-819k, pvso 732k (not re-measured in a real synth).
4. RUNNING: unattended private H8 proof chain, epyc10 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-1121/` (chain.sh PID 618307, log chain.log, 12 h cap):
   waits for `^BIND_RC=0` in s81-j6/logs/gate_candC3d.log (else gate_candC3c.log) -> ot-run prep.py (fresh_kit partition on the J6 tree, bind
   plan_of_record/native_bind/out, wave gen env + gen args, clock landing h2_2249/landed_sidecar_j6_rom_h8.json) -> run_kit.sh place 48 8 ->
   run_kit.sh route 64 8. Posts `H8-PROOF chain` lines under this lane at each step. Output kit `kit_hi4_<tree>/gen/svc_hi_dsdv_svc_rs__t4`.
   Private: not counted, not published. The chain does NOT run signoff.py / export.
   Untested assumptions: (a) the wave after J6 uses landed_sidecar_j6_rom_h8.json as --clock-landing (J5 used plan_of_record/sidecar_new.json);
   (b) fresh_kit's --trial / --util 0.4 gen flags equal the wave kit for a partition type; (c) no assembly_contracts needed (wave spec has none).
   If prep fails on (a), rerun `prep.py <tree> svc_hi_dsdv_svc_rs__t4 <new out name>` with the other sidecar (edit GARGS; output dir must not exist).

## Next steps
- Read the chain posts. Place result: check cells (native_cell_count.json), 2_2 MPL lines, 3_3 GPL convergence, 3_5 DPL, then post-hook CTS only.
- If place + GRT pass: sign-off with the kit's signoff flow (DRC 0, TT setup >= -42 ps, internal FF hold >= 0, LEC), then export to AGIdock /archive +
  rtx-pro ~/signed-export-1114 with an INDEX row (~/.local/bin/signed_store.py) ONLY if COORD agrees a private-kit sign-off is exportable; otherwise
  the countable sign-off is the wave row after the J6 apply.
- If the H8 hi shell fails GPL / congestion: send the measured cause to S81-J6-ASSEMBLY-R2 (J7 rows): next cuts in order were landing rings -> cland
  ring macros (129k), attn_tr_x, bind_native glue (S81-SVC-SPLIT handoff).
- After the J6 apply: watch the 16 wave svc rows on the new event; lo types (98 hard cores, 732-819k shell) are the worst case, not hi t4.

## Files
- epyc10 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-1121/` (prep.py, chain.sh, chain.log; later prep_*.log, place_*.log, route_*.log, kit_hi4_*).
- Predecessor dirs (read only): epyc9 fable-fix-s81-svc-r2 (ksrc, bind_r7/8), fable-fix-s81-svc-r3 (bind_r8c).
- Predecessor waiter still alive: intel2 PID 3327226 rep_waiter.sh (posts REP-ROW under FABLE-FIX-S81-SVC-R3).
