# FABLE-FIX-QC-COLL-R2 handoff (Fable; owns QC coll_core end to end; successor of FABLE-FIX-QC-COLL, started 11-21 19:53 PST)
Read lanes/handoff/FABLE-FIX-QC-COLL.md first (method, solver, station plan). Work dir: epyc7 /srv/opentallas-scratch2/claude/fable-fix-qc-coll.

## STATE 11-21 21:45 PST (work moved to epyc10 /srv/opentallas-scratch2/claude/fable-fix-qc-coll-r2; hub scripts/specs in the same path on intel2)
- Package v2 (legal re-seat) DELIVERED: lanes/handoff/FABLE-FIX-QC-COLL-V3-pkg.json, 28 rows on V3p5r; delta + relay_sites + apply tool on epyc7
  fable-fix-qc-coll/{pkg4,an/apply_delta.py}. Bind v2 clean 21:24 (epyc10 pk3: strict 0, LATCHECK 1921/1921). COORD: R13 swaps v2 into V3; v1 must not ship.
- Solver chain (epyc10 an/): solve3.py cfg5.json (legal map: box + 5.4 halo + slits < 13 um; macro_shift ring SRAMs -30.24) -> destack.py -> compose_r4.py; check_seats.py.
  Eval mode: cfg5_eval.json (init_seats, iters 0). Model after v2: 351 connections > 405 um (max 448; 4 at 558).
- coll_core proof kit: intel2 core_chain.sh (pid 3022559, log core_chain.log) waits for the epyc10 tree qwen_compute_v2r10_famqc_cr8 (famqc + refreshed R8 table,
  mktree10.sh) then private-spec (pspec_core1, rt db0d7630d4c2, --bind-out pk3/rebind, A/B OT_KEEP_WIRES) + run-item (goal auto) -> kit epyc10 pkit_core1.
  rt snapshots rotate: use rt/current on intel2 if a sha dir is gone.
- Reads owed on the proof kit (COORD accepted): post-CTS reset recovery (relay row only if still negative); g_wd[*].u_tcv -> qdata select fan-out
  (per-face replication RTL only if still failing); OT_RELAY_SITES unmatched; an/grp.py on the new geom.
- coll_ftc: V2 wave kit route resume CANCELLED (COORD). Spread form = Codex axis_r4 plan (ftc_plan/zz_ftc_axis_r4.json), private bind pkf clean (strict 0, LAT 1921),
  spec pspec_ftc2, run-item intel2 pid 2978227 (goal auto), kit epyc10 pkit_ftc2. pspec_ftc1 died KIT_TOPOLOGY_BIND_STALE (a private plan needs its own bind).
- If run-item stops at geom: resume with the kit's own run_kit.sh GOAL=route through ot-run (COORD).

## RULES ADDED 11-21 23:xx (COORD, after my shared-tree write incident)
- Private trees ONLY via ot-tree-fork (rt tools/fleet/ot-tree-fork SRC DST; real nlink-1 copies). A launch tree's physical/die_plan is a SYMLINK into its
  source tree: an R8 refresh in a "private launch copy" writes the shared tree. Before writing into a launch tree: no symlink, no nlink > 1, else fail
  (guard() in epyc10 fable-fix-qc-coll-r2/bind_pkg4.sh).
- epyc10 kw45/snap_qwen_compute/qwen_compute_v2r10_famqc_cr8 (hardlinked, made by delta-apply --link): the v2 proof kit pkit_core1 runs from it.
  NO writes into it (no bind, no R8 refresh). When the v2 proof ends: retire it via ot-delete (and its rt_tools_launch/qwen_compute_v2r10_famqc_cr8@* launch dirs).
- v3 seats (half-cycle INLOCK edges <= 120 um; an/solve4.py cfg7.json -> s7/seats_ds.json -> pkg5/): bind = epyc10 fork_bind.sh (ot-tree-fork -> tree_fork, pk4),
  unit oth-ubuntu-3836728-1795329935. Clean by 05:00 -> offer R13 a seat-file swap (relay_sites value_file only); else V3 keeps v2, v3 -> V4.
  v3 proof kit must use the fork tree (tree_fork carries the refreshed R8 after the bind), not cr8.
- Proof v2 placed read: WNS -170.23 (INLOCK half-cycle lock flops ir_n/srr_n/drr_n priced as full cycle), recovery +37.69, shr_p_rx_i ring -95.60.

## Delivered
- V3 package for QC-PLAN-R12: lanes/handoff/FABLE-FIX-QC-COLL-V3-pkg.json (delta keyed by type/row on V3p5r b1281d55e514; 24 rows).
  Files: pkg3/rows_v3p5r.delta.json + rows_v3p5r.relay_sites.json, apply tool an/apply_delta.py, generator an/compose_r2.py
  (= compose.py + six defines + lane old-value asserts + delta emit). gen.py latency on V3p5r+delta: exactly the 13 coll lanes move.
- The delta sets verilog_defines to the six OT_TP8S_* (V3p5r has one; seats need the six-define netlist).

## Bind
- pk1 (handed unit oth-ubuntu-3314323-1795319375): rc 3, 30 R8_STALE only (re-cycled coll lanes).
- Fix: standard r8_refresh.py with the QC s29 pin (--pin-pre zz_r8_s29q101O_g0.json.gz --pin-extra 0): 33 members, coll lanes only.
  NEVER install the fail-fast OUT/r8_derived.json (un-pinned: moves 672 dvs pads).
- pk2 = re-bind in a private launch copy (pk2/launch = cp -al of the shared launch tree, so the shared table is untouched):
  script bind_pkg2.sh, client log bind_pkg2.client.log, out pk2/{bind.log,latcheck.json,rebind,rebind_rtl,r8_final.json}. Ends COLL_PKG_BIND_DONE.

## Live units (latest post wins)
- see lanes/posts/FABLE-FIX-QC-COLL-R2.md
- reflow3 intel2 oth-ubuntu-2919937-1795318838 (fam-qc-coll/reflow3, log place.client.r1.log): cross-check only.
- coll_ftc V2 wave kit a1 (epyc8 kw43-wave-1109n/.../items/coll_ftc/gen/coll_ftc): placed 13:09, run-item ended at geom rc 1; nothing drives it to GRT.

## Next
1. pk2 strict 0 + LATCHECK 1921 -> update the V3 pkg file (private_proof.bind_2) and post to QC-PLAN-R12.
2. private-spec (rt 2c3fa5fd9727, tree qwen_compute_v2r10_famqc, plan pk1/bind_plan/zz_coll_core_pkg.json, --bind-out pk2/rebind, host epyc7, work pkit1,
   --ab OT_KEEP_WIRES = the pspec10wall gen_env value) -> diff config.mk vs the wave coll_core kit -> run-item on intel2.
3. Place log: OT_RELAY_SITES unmatched, OT_ISTATIONS, fault stations; an/grp.py on the new geom; post-hook CTS; final 5_1_grt.odb; route; sign-off; export.
4. Residual hi_q/lo_q -> g_pf (254 bits, 411 um): one station, decided on the placed read of the proof kit.
