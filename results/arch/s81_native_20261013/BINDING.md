# S81 die: by-name view binding

Built by `tools/s81/view_binding.py` from `results/arch/s81_native_20261013/qualification.json` (sha256 b8a69bcd82d9) and the c5 census (212 masters, 57015 instances). Table: `results/arch/s81_native_20261013/view_binding.json`; ledger: `results/arch/s81_native_20261013/binding_ledger.json`.

Rule: a master is bound to a real view (routed LEF + TT/FF/SS ETM of one export) only when `native_view_qualify.py` says QUALIFIED, its export replayed the verdict SDC sequence (main abc334b14: `abstract.json` verdict.check ok for the files on disk) and the placer can place the real outline. No gate is weakened; everything else is a generated placeholder.

| binding | masters | instances |
|---|---:|---:|
| BOUND | 0 | 0 |
| PLACEHOLDER | 207 | 43179 |
| CONSTANT_HARD_MACRO | 5 | 13836 |

Qualification gate today: 0 of 21 candidate bundles QUALIFIED (0 instances). CONSTANT_HARD_MACRO = real LEF bound by a generator constant (cfg ROM, PHY, SerDes, UCIe, q element), outside the native gate.

Placeholder instances by reason (a master with several failing gates counts under each):

| reason | instances |
|---|---:|
| relay kit not routed / no view exported | 29184 |
| no routed view (no kit / not hardened) | 12302 |
| gate thr failed | 1683 |
| gate export open | 1548 |
| gate pair failed | 1547 |
| gate lint failed | 1299 |
| gate pair open | 135 |
| gate clock failed | 128 |
| no complete native bundle (missing corner / LEF) | 10 |
| gate bench failed | 5 |
| gate current failed | 3 |

Placeholder masters with a candidate view (failed / open gates, owner):

| master | instances | failed | open | owner |
|---|---:|---|---|---|
| dsfd_stnh_512x1 | 598 | pair, lint, thr | export | Claude:s81-rerun |
| dsfd_stnh_566x1 | 391 | pair, lint, thr | export | Claude:s81-rerun |
| dsfd_stnv_512x1 | 383 | pair, thr | export | Claude:s81-rerun |
| dsfd_stnv_514x1 | 129 | pair, lint, thr | export | Claude:s81-rerun |
| dsfd_cfifo | 128 | lint, clock, thr | pair | Claude:setup-triage (block owner claude/s81-rerun-20261006 / Claude:s81-rerun) |
| dsfd_stnh_514x1 | 43 | pair, lint, thr | export | Claude:s81-rerun |
| dsfd_l2r_vr_564x1__hx_E | 1 | lint, thr | pair | Claude:el1011-reroute-m5 |
| dsfd_l2r_vr_564x1__hx_W | 1 | pair, lint, thr | - | Claude:s81-die |
| dsfd_m2l_raw_512x1__hl_E0 | 1 | bench, lint, thr | pair | Claude:el1011-reroute-m5 |
| dsfd_m2l_raw_512x1__hl_E2 | 1 | bench, lint, thr | pair, export | Claude:s81-die |
| dsfd_m2l_raw_512x1__hl_W1 | 1 | bench, lint, thr | pair, export | Claude:s81-die |
| dsfd_m2l_vr_512x1__hix_SW | 1 | bench, lint, thr, current | pair | Claude:el1011-reroute-m5 |
| dsfd_m2l_vr_512x1__hqe_SW | 1 | bench, lint, thr, current | pair, export | Claude:el1011-reroute-m5 |
| dsfd_r2l_vr_1024x1__ha_SW | 1 | lint, thr | pair | Claude:s81-die |
| dsfd_r2l_vr_512x1__hcol | 1 | pair, lint, thr | - | Claude:s81-die |
| dsfd_r2l_vr_512x1__hsel | 1 | pair, lint, thr, current | - | Claude:el1011-reroute-m5 |
| dsfd_svc_join | 1 | thr | export | Claude:el1012-svcjoin-ck |

4 qualification rows are masters the die netlist does not instantiate (ot_s81_hc_ctfn, ot_s81_hc_ctfs, ot_s81_hc_ctfx, ot_s81_hc_ctpl): none QUALIFIED; see `qualification_rows_not_on_die`.

## How it is consumed

- `tools/dsrom_s81_fulldie.py --view-binding TABLE` (or `OT_S81_VIEW_BINDING`; default the committed table; `none` binds nothing): `bound_views` verifies every file's sha256 against the table, `apply_view_binding` (end of `finalize_r8`) hard-errors when the LEF pins are not the die netlist's ports of that master, when an instance is not R0 or when the real outline exceeds the slot; `write_lefs` drops the generated macro and `case_real` writes `bound_views.lef`.
- `tools/s81/die_sta.py kit`: a bound master's corner libs come from the table. A generated-outline master that is not in the table is timed with the interim lib even when a routed-view ETM of that cell exists in the tree (`unqualified_views_not_bound` in the kit index); `--legacy-unqualified-libs` restores the tree scan for re-running an earlier case.
- Refresh: `python3 tools/s81/view_binding.py` (re-runs the qualification gate over the manifest bundles and `physical/ref_tile/s81_rly_*/views/*/*.lef`, so a relay view directory is picked up by master name when it appears).

## Placer assumptions (what still uses the generated outline)

1. tools/dsrom_s81_fulldie.py: _hop_fix.find (line 5019) and _col_relays (line 5469, _pick line 5565) choose every relay site from stn_dims([bits], horiz) (line 3132): the GENERATED outline (max(face need, 17.28) - SHAVE = 17.256 um minimum), before the relay's face pair is known.
2. The relay master name dsfd_rly_<W>_<fi><fo> (hence which real outline applies: 8.64 / 10.8 / 15.12 square; W 266 / 283: 34.56 x 19.44 N/S or 21.6 x 30.24 E/W) is assigned AFTER placement from the neighbours' directions (end of _hop_fix, line 4974; end of _col_relays), so the placer cannot size the site from the real LEF without a second placement pass.
3. apply_view_binding (line 466, end of finalize_r8 line 6571) therefore does not re-place: a bound instance keeps its slot ORIGIN (lower-left), takes the real LEF SIZE, must be R0 and must fit the slot; a larger real outline or a non-R0 instance is a hard error (and view_binding.py placer_fit keeps such a master a placeholder).  The slot remainder is left unused; occupancy / reach / --nxt-reach decisions were taken on the generated outline.
4. Real pin positions: k = 1 LEF (case_real line 1666: bound_views.lef, read before elements.lef) and tools/s81/die_hop_gate.py use the real pins.  masters_r8 / _faces_r8 (lines 6653 / 6750) still build a generated-face Master for a bound master at the real SIZE: the k > 1 bundled GRT view (case_grt line 1780) and the IR windows (case_irm line 2273) use those generated faces, and _lint_pin_pt (line 1479, --pin-need) returns the instance centre for a bound master (it reads real pins only for REAL_FILES hard macros).
5. The neighbours' generated pin faces (_faces_r8) aim at the bound instance's centre, not at its real pin face.
6. --gen r7 never calls finalize_r8: nothing binds there.  tools/budgets/extract_die.py (clock plan) was not changed or checked against bound masters.
