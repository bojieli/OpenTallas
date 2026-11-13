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

## 2026-11-13 06:46 update
- COORD message (DIEVIEW-S81 F4): break the xf wall, register ft0_i at the pin. DONE in the template: xf row is 3 + 2 with a 43.2-um N-S
  street at x 691.2-734.4 (the same street runs between eg and xs4 down to the ring band). ft0_i: OPEN, needs the pin_unreg list of a
  c1x t3 place proof (geom_rules.pin_reg_metrics: a landed input is judged on its declared ring slots; find why ft0_i is not in land).
- Template now: cap (43.2, 544.32) W side above the W bars; xf e0 e1 f x 129.6-691.2 | e2 e3 x 734.4-1105.92, y 993.6, MX; eg (423.36, 639.36);
  xs4 (734.4, 440.64) MX; xr (475.2, 216.0). Row deltas: c1x t1 and t4 mirrored in x; c1x t3 left xf group -25.92 (type tap);
  lepw_mus cap at (129.6, 129.6), xr +43.2. cap / xr flip = lowest bit-um.
- Plan chain (epyc7 worktree, physical/die_plan/s81/, untracked work files plan_xs4_*.json):
  base 18c864518844 -> delta_xs4_core_1113.py -> d1b d1c045231b23 -> reach_fix fix classes 1-5 (16 applied, 0 violations left)
  -> d2b 1ee87eb8472a -> stage_kit_source_table_refresh (0 lanes) + --dest (23 dn lanes, +43 cycles) -> d3 3e5d6a2c9d9f.
- RTL: rtl/dsrom_sys/s81_dv/slice/cap_end/ot_s81sl_slice_w3.sv (iq / kv512 parent): u_xg master ot_s81sl_xg -> ot_s81sl_xgt_xo and the
  x relay line D = DX - 1, so the xs4 capture edge replaces one relay stage: no calendar change at the x-chain heads.
- Bind: epyc8 /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/{bsrc_xs4 (cwd tree: FIN bsrc_r12bA_dst bulk + main rtl/tools + lane files),
  bbase_xs4 (asbuilt base: bsrc_main2_lfcs bulk + main rtl/tools), asbuilt_xs4b.json (asbuilt_ist + dissolve ot_s81sl_xgt_xo +
  instance_path_params ot_s81sl_xs4), run_bind_xs4.sh PLAN TAG}. Run b1 (plan d3) launched under ot-heavy --mem 200: logs b1.*.
- G0 baseline (base plan, main tools): 74 errors (= record). G0 / G0C of d2b running on epyc7 (work dir g0_d2b, g0c_d2b; g0cmp.py compares).
- xs4 kit: sub-agent XS4-KIT (kits under epyc7 work dir kits/); it edited cores/legacy/gen_core_kit_legacy.py (uncommitted; check its report).

## 2026-11-13 07:27 resume
- HARD-S81-DSDV-1 resumed (COORD, Fable reset). Read DSDV-FORMS-2 HANDBACK 07:27. Candidate plan g4 fb7f60293915; waiting on: g4 strict bind + latency (epyc8), G0/G0C g4 (epyc7), xs4 build epyc2 unit oth-ubuntu-2195141-1794582250. Next steps = DSDV-FORMS-2 NEXT STEPS 1-5.

## 2026-11-13 13:11
- Plan g4 = m4 fb7f60293915 on main 0a4b432de8 tools: G0 74 = base 74, G0C 0 errors on C rows, R-STREET 0, strict bind h2 rc 0 (0 tied; declared tie rstopt_xo ci_b[1103:1076], sidecar installed in the bind trees), LATCHECK 873/873. Branch pushed acac09abb5 (events/s81_xs4core_1113). RULEBOOK R-CAP dsdv note written.
- xs4 build r1 (epyc2) DIED at 07:50 after synth: FACE_GUARD RAW FAIL (g_v/g_fam/g_idx 21 kept copies per pin, is_v 2, xw_v/xw_d[0] one flop, fault flop second load, is_d[91:42] dead). Nobody saw it for 5 h (my waiter looked for place renders only).
- FIX in progress (helper XS4-FACE): xs4 ports one bit per kept capture copy (g_v 63, g_fam 63, g_idx 441, is_v 2), own flops for xw_v and fault, wrappers replicate; dead_inputs is_d[91:42]; benches xs4_equiv + xgtxo; kit regen (kits2) and relaunch run/xs4h_r2. Contract regenerated: 4,906 pins at 0.096 (xs4_core_contract_1113.py; old pin table saved W/ot_s81sl_xs4.pins4365.json). UNCOMMITTED in WT: contract files, RTL edits to come.
- AFTER the RTL is green: rerun W/chain6.sh (new plan sha: core pin table changes), rebind (run_bind_xs4.sh, AB=asbuilt_xs4c.json, NOSEED=1), refresh events/s81_xs4core_1113, then READY.
- Helper DSDV-PROOF: place proofs c1x t3 + c1x t8 from out_h2 (old 4,365-pin contract; layout view only) + ft0_i pin_unreg trace.
