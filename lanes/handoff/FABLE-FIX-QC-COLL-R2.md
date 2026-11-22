# FABLE-FIX-QC-COLL-R2 handoff (Fable; owns QC coll_core end to end; successor of FABLE-FIX-QC-COLL, started 11-21 19:53 PST)
Read lanes/handoff/FABLE-FIX-QC-COLL.md first (method, solver, station plan). Work dir: epyc7 /srv/opentallas-scratch2/claude/fable-fix-qc-coll.

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
