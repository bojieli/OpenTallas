# S81 die: by-name view binding

Built by `tools/s81/view_binding.py` from `results/arch/s81_native_20261013/qualification.json` (sha256 1628b7914fa1) and the c5 census (212 masters, 57015 instances). Table: `results/arch/s81_native_20261013/view_binding.json`; ledger: `results/arch/s81_native_20261013/binding_ledger.json`.

Rule: a master is bound to a real view (routed LEF + TT/FF/SS ETM of one export) only when `native_view_qualify.py` says QUALIFIED, its export replayed the verdict SDC sequence (main abc334b14: `abstract.json` verdict.check ok for the files on disk) and the placer can place the real outline. No gate is weakened; everything else is a generated placeholder.

| binding | masters | instances |
|---|---:|---:|
| BOUND | 21 | 25600 |
| PLACEHOLDER | 186 | 17579 |
| CONSTANT_HARD_MACRO | 5 | 13836 |

Qualification gate today: 27 of 48 candidate bundles QUALIFIED (29184 instances). CONSTANT_HARD_MACRO = real LEF bound by a generator constant (cfg ROM, PHY, SerDes, UCIe, q element), outside the native gate.

Placeholder instances by reason (a master with several failing gates counts under each):

| reason | instances |
|---|---:|
| no routed view (no kit / not hardened) | 12302 |
| gate placer_fit failed | 2560 |
| gate pair open | 1681 |
| gate export open | 1548 |
| gate lint failed | 1299 |
| gate export_fix failed | 1024 |
| gate clock failed | 128 |
| no complete native bundle (missing corner / LEF) | 10 |
| gate bench failed | 5 |
| gate current failed | 3 |
| gate pair failed | 1 |

Placeholder masters with a candidate view (failed / open gates, owner):

| master | instances | failed | open | owner |
|---|---:|---|---|---|
| dsfd_rly_1_WE | 640 | export_fix | - | S81 DIE stream lead (claude/el1011-s81dieit), relay kits (tools/s81/rly_kits.py) |
| dsfd_rly_266_SN | 640 | placer_fit | - | S81 DIE stream lead (claude/el1011-s81dieit), relay kits (tools/s81/rly_kits.py) |
| dsfd_rly_266_WE | 640 | placer_fit | - | S81 DIE stream lead (claude/el1011-s81dieit), relay kits (tools/s81/rly_kits.py) |
| dsfd_rly_283_SN | 640 | placer_fit | - | S81 DIE stream lead (claude/el1011-s81dieit), relay kits (tools/s81/rly_kits.py) |
| dsfd_rly_283_WE | 640 | placer_fit | - | S81 DIE stream lead (claude/el1011-s81dieit), relay kits (tools/s81/rly_kits.py) |
| dsfd_stnh_512x1 | 598 | lint | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_stnh_566x1 | 391 | lint | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_rly_1_EW | 384 | export_fix | - | S81 DIE stream lead (claude/el1011-s81dieit), relay kits (tools/s81/rly_kits.py) |
| dsfd_stnv_512x1 | 383 | - | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_stnv_514x1 | 129 | lint | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_cfifo | 128 | lint, clock | pair | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_stnh_514x1 | 43 | lint | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_l2r_vr_564x1__hx_E | 1 | lint | pair | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_l2r_vr_564x1__hx_W | 1 | lint | pair | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_m2l_raw_512x1__hl_E0 | 1 | bench, lint | pair | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_m2l_raw_512x1__hl_E2 | 1 | bench, lint | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_m2l_raw_512x1__hl_W1 | 1 | bench, lint | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_m2l_vr_512x1__hix_SW | 1 | bench, lint, current | pair | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_m2l_vr_512x1__hqe_SW | 1 | bench, lint, current | pair, export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_r2l_vr_1024x1__ha_SW | 1 | lint | pair | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_r2l_vr_512x1__hcol | 1 | lint | pair | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_r2l_vr_512x1__hsel | 1 | pair, lint, current | - | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |
| dsfd_svc_join | 1 | - | export | S81 DIE stream lead (claude/el1011-s81dieit) -- no hardening kit assigned |

4 qualification rows are masters the die netlist does not instantiate (ot_s81_hc_ctfn, ot_s81_hc_ctfs, ot_s81_hc_ctfx, ot_s81_hc_ctpl): none QUALIFIED; see `qualification_rows_not_on_die`.

## How it is consumed

- `tools/dsrom_s81_fulldie.py --view-binding TABLE` (or `OT_S81_VIEW_BINDING`; default the committed table; `none` binds nothing): `bound_views` verifies every file's sha256 against the table, `apply_view_binding` (end of `finalize_r8`) hard-errors when the LEF pins are not the die netlist's ports of that master, when an instance is not R0 or when the real outline exceeds the slot; `write_lefs` drops the generated macro and `case_real` writes `bound_views.lef`.
- `tools/s81/die_sta.py kit`: a bound master's corner libs come from the table. A generated-outline master that is not in the table is timed with the interim lib even when a routed-view ETM of that cell exists in the tree (`unqualified_views_not_bound` in the kit index); `--legacy-unqualified-libs` restores the tree scan for re-running an earlier case.
- Refresh: `python3 tools/s81/view_binding.py` (re-runs the qualification gate over the manifest bundles and `physical/ref_tile/s81_rly_*/views/*/*.lef`, so a relay view directory is picked up by master name when it appears).

## Placer assumptions (what still uses the generated outline)

1. tools/dsrom_s81_fulldie.py: _hop_fix.find (line 5088) and _col_relays (line 5538, _pick line 5634) choose every relay site from stn_dims([bits], horiz) (line 3185): the GENERATED outline (max(face need, 17.28) - SHAVE = 17.256 um minimum), before the relay's face pair is known.
2. The relay master name dsfd_rly_<W>_<fi><fo> (hence which real outline applies: 8.64 / 10.8 / 15.12 square; W 266 / 283: 34.56 x 19.44 N/S or 21.6 x 30.24 E/W) is assigned AFTER placement from the neighbours' directions (end of _hop_fix, line 5043; end of _col_relays), so the placer cannot size the site from the real LEF without a second placement pass.
3. apply_view_binding (line 466, end of finalize_r8 line 6724) therefore does not re-place: a bound instance keeps its slot ORIGIN (lower-left), takes the real LEF SIZE, must be R0 and must fit the slot; a larger real outline or a non-R0 instance is a hard error (and view_binding.py placer_fit keeps such a master a placeholder).  The slot remainder is left unused; occupancy / reach / --nxt-reach decisions were taken on the generated outline.
4. Real pin positions: k = 1 LEF (case_real line 1712: bound_views.lef, read before elements.lef) and tools/s81/die_hop_gate.py use the real pins.  masters_r8 / _faces_r8 (lines 6806 / 6909) still build a generated-face Master for a bound master at the real SIZE: the k > 1 bundled GRT view (case_grt line 1832) and the IR windows (case_irm line 2325) use those generated faces, and _lint_pin_pt (line 1479, --pin-need) returns the instance centre for a bound master (it reads real pins only for REAL_FILES hard macros).
5. The neighbours' generated pin faces (_faces_r8) aim at the bound instance's centre, not at its real pin face.
6. --gen r7 never calls finalize_r8: nothing binds there.  tools/budgets/extract_die.py (clock plan) was not changed or checked against bound masters.
