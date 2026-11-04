# PG-CORECONN-3: M7-top macro PG publish + class-B stub PG (DIE-S81-51, 2026-11-03)

COORD GO 18:44 PST (one class lane, estimate first). DIE-S81-51 GO on both parts, with conditions (1) the bpin net comes from the master pin USE and other-net overlap fails loud, and (2) one floorplan-PDN probe plus a die-PDN mini-run. Base: origin/main b07b52ff0c7 + claude/die-s81-51-corepg2-1103@6b0c2b3b5f0.

## Class A: M7-top views (rom_elem_q, bf_col, capc5r, bksel_q)

- Problem: these views carry PG straps on M7 (pitch 10.8), which is also the tile's top PG layer. They have no OBS-free landing below M7. The tile has no layer above M7 (12.1a), so PG-CORECONN-2 skipped them, and their 180 placed uses were PG-open.
- Fix (industry hierarchical PG): the die M8 grid lands on them. die_pdn_tcl already has `{parts}` M7 -> M8 on every partition M7 PG pin. gen_phys now publishes the macro's M7 PG mpin boxes as tile VDD/VSS bpins: `core_pg_mode`, `core_pg_published`, `core_pg_publish_tcl` -> kit `pg_publish.tcl` as POST_PDN_TCL. When a type also has `pg_island_cut.tcl`, both run through `post_pdn.tcl` in that order. The bpin net is the ITerm's net, and that net's sig type must equal the master pin USE (POWER/GROUND). The script fails loud on:
  - overlap with other-net tile M7 PG metal or pins;
  - no instance match, or an unconnected PG ITerm;
  - no tile bterm, or an orientation other than R0/MX/MY/R180;
  - a macro with no M7 PG shape.
- `core_pg_unconnected` counts a publish-mode macro as landed only when it is published. No tile metal is added, no view changes, and the die PDN is unchanged.
- Plan census (`census.json`, plan_h2_2249): 158 types have core_pg on and a macro. After the fix: 0 skipped uses, 180 published uses in 43 types (rom_elem_q 104, bf_col 56, capc5r 16, bksel_q 4), 0 unconnected, 0 errors.

### Proof (epyc2 docker, orfs:asap7lock, memory cap)

- Vehicle: col_h10_r0_p4__t1. The 2_3 tapcell ODB comes from intel1 codex-s81-parent-1101/gen. That ODB names instances `u_bound.u_u_r0_*` (plan `u_r0.*`), so the probe renamed the generated patterns only.
- Step 1 (`probe_tile.tcl`): PDN_TCL = PDN + the PG-CORECONN-2/3 grids, then pdngen, then pg_publish.tcl inside a proc as ORFS runs it, then write_abstract_lef -bloat_occupied_layers.
  - Result: `OT_PG_PUBLISH macros=6/6 pins=552 layer=M7`, with 0 overlap errors. 552 equals the M7 PG rects of 4 x rom_elem_q + 2 x bf_col (one MY).
  - The tile abstract PIN VDD/VSS now holds 787/777 M7 rects.
- Step 2 (`probe_die.tcl`): the plan's die_pdn_tcl (M8/M9 8.64 grid + `{parts}` M7 -> M8) runs over one instance of that abstract. M7->M8 vias on each published macro's straps:

| macro | straps | M7-M8 vias |
|---|---|---|
| u_e0 / u_e2 / u_e3 / u_e4 (rom_elem_q) | 96 each | 2448 each |
| u_e1w / u_e1e (bf_col, R0 / MY) | 84 each | 1890 each |

  - Totals: 13,572 vias on macro straps out of 48,925 M7-M8 vias, with 0 net mismatches (every via lands on a strap of its own net).
  - Before this fix the count was 0: PG-SWEEP-1 measured no overlap or via on any M6/M7 PG pin of u_e0/u_e2.
  - pdngen dropped 8 sites x 4 vias (PDN-0195): 2 sites per rom_elem_q, at the same macro-relative spot in each copy.

## Class B: plan stubs without PIN VDD/VSS

- Views: dsdv_eng_rr_h0/h1, dsdv_eng_rr_e_clkm5_1101, H2 coll_{w,e}/lane.lef, and the H2 ot_s81_mu72_lnland(_nst) LN stubs. The census found the LN stubs as the next raise in the same 4 LP types after lane.lef was fixed.
- All 7 are plan stubs of unsigned cores. Their native recipe (gen_core_kit*.py) routes at most on M5, with pdn -pins M5. The routed H0 abstract (intel1 codex-s81-cohort-1101 dsdv_eng_rr_h0_ccA_g2typed) has VDD at x = 157.716, which is exactly this recipe.
- Fix: a `core_pg_stub.refresh` text rewrite adds the native M5 PG pins. `clip_obs` drops OBS above M5 (on the E stub). refresh now inserts before `END <macro>` when a stub has no OBS, and it finds PG pins at any indent.
- Result: 0 PG / M5-signal-pin conflicts at 0.072 spacing in all 7. The signed abstracts replace these stubs at sign-off.

## Tests

- `python3 -m pytest -q tools/die_plan/test_gen_phys_core_pg_connect.py tools/die_plan/test_gen_phys_pg_island_cut.py physical/die_plan/s81/test_core_pg_stub.py`
