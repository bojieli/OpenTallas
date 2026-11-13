# HARD-S81-DSDV-1 handoff (S81 dsdv_slice_*_C family, R-CAP-3 point 3; Fable lane; COORD) -- started 2026-11-13 05:51 PST

## Scope
- Harden u_c.u_xg.u_s = ot_s81sl_xs4 as ONE hard core for the 16 C types; iq/kv512 switch u_xg to xgt_xo; hand re-layout of the 16 rows;
  xs4 kit to sign-off; place proofs c1x t3 + one more; RULEBOOK note; ONE S81 event READY (adopted after 11-15 04:00).

## Worktree / files
- epyc7 /srv/opentallas-scratch2/claude/wt/hard-s81-dsdv-1, branch claude/hard-s81-dsdv-1-1113 off origin/main 87b85b86bd (own clone).
- Work dir epyc7 /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/ (rtype.py type renders, base_png/, kits/).
- Base plan: events/s81_ready12bA_1112/plan_ready12bA_18c864518844.json.gz.

## Decisions (2026-11-13 05:51)
- xs4 core: outline 648.0 x 518.4, ONE pin face (N in the core frame, M5, pitch 0.144, 4,365 pins), M5 cap. Macro map = xg5fa column
  order (b1 | b0 | ROM | ROM | b2), 4-stacks S and N of a 100-um centre band. Pin order: g_d slices over their banks, xw in the middle.
  Files: physical/die_plan/s81/xs4_core_contract_1113.py (LEF contract, provisional libs, pin table), physical/ref_tile/s81sl_xs4h/spec.json,
  cores/legacy/recipes_xs4h_1113.json, cores/views/xs4_prov_1113/.
- Family template (type frame; the xring W/E bars are at y 6-487 in ALL 16 types, so the ring band is always the bottom):
  cap top-left, xf row (MX, pins down) along the top right of cap, eg under the xf row, xs4 (MX, pin face down to the ring band) at the
  right (x >= 734.4, clear of the type clock tap 725.76/613.44), xr in the band left of the rstopt home. Per-row deltas from ft stations,
  landing bands, lep W pins (lepw_mus mirrors the template).
- xw (xs4) drives x_o (xw4); x_o is on N in 8 types and on S in 8, so some x_o lanes take stations (+cycles, pre-approved).

## State
- Kit build: sub-agent XS4-KIT generating + launching (kits under the work dir).
- Plan delta: in progress.
