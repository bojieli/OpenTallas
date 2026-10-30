# HBM-BIND-12 (2026-10-29): HBM-042 cleared, the SU 4-lane cuts expose the canon 9-bit lane id

Sub-lane of DIE-HBM-23 that follows HBM-BIND-11 (branch base ddf39a0b7e9). Plan d23a
(`intel1:/srv/opentallas-scratch2/claude/die-hbm-23/plan/d23a/die_plan.json`, sha256 4133ce1e4e0d) is unchanged.
Run dir `intel1:/srv/opentallas-scratch2/claude/hbm-bind-12-1029` (variant `g2`). No tool was changed.

## Cause
- **Source.** `ot_hbm_su_static_pgslice_s.sv` drives `.lane_id(11'(lid(n)))`, with `lid(n) = n<16 ? 16G+n : 64+16G+(n-16)`.
  A 4-lane cut holds lanes 4j..4j+3, so its four 11-bit ids are `{B, 2'd0..3}` with one 9-bit base B.
- **Plan.** The canon kits `lanes_plain__canon_663526` (Q0/Q1) and `lanes__canon_cf1e77` (Q2/Q3) expose
  `lane_lane_id[8:0]` (pins files; `mk_canon_wrappers.py`: lane k id = `{lane_lane_id, 2'd<k>}`). d23a declares
  `parent_id_straps lane_lane_id {width 9, value B}`, where B is 16..19 for Q0/Q1 plain (G 0 ⇒ 64/4 + j) and 8..11 or
  24..27 for Q2 lanes. These declarations follow the source and the kits.
- **As-built compose.** `hbm-bind-7-1029/c1/compose.json` (Codex `native_compounds.py`) exposes all 44 literal bits
  (4 × 11) as `lane_lane_id[43:0]` on `ot_hnx_su_plain4__7dd6a1bbbf47`. `parent_id_straps.py` therefore found no 9-bit input.
- **Owner rule (ID straps, option B).** The ID-only strap is the kit's input pin, tied at the parent and false-pathed. So the bound
  cut must expose the kit's pin, not the raw literals.

## Fix (die-local compose copy plus manifest pointer)
`mk_compose_lid9.py` fails closed: it asserts 44 bits = 4 distinct lanes × lane_id[0..10], declared width 9, and exactly one
plan descriptor. It rewrites only the cuts whose plan hard core declares the 9-bit strap: 44 cuts (32 `lanes_plain*`
Q0/Q1 + 12 Q2/Q3 `lanes*`). On each, `lane_lane_id[i]` = the alias of the four lanes' `lane_id[i+2]`. `bind_compose` requires
the four values to be identical, so it fails closed otherwise. Each lane's `lane_id[1:0]` stays an unexposed terminal and
keeps its as-built literal (k) inside. The new module is `ot_hnx_su_plain4__lid9` (`ot_hnx_su_plain4__lid9.sv`): lane k gets
`{lane_lane_id[8:0], k[1:0]}`, which equals the canon kit wrapper. The 4 `lanes8_11` cuts (Q2/Q3) are kept on the old module
because their kit has no lane-id pin and the plan declares no strap. `mk_g2_manifest.py` changes only the manifest's `compose`
path (g1 → g2). `bind.py validate_bound_id_bits` then checked every bound strap value against the as-built literals.

## Results (CHECKED = run here, read from out/bind_report.json and bind.log)
| run | errors | UNPLANNED (bits) | EMIT | tied / undriven / multiply_bound | straps | open_outputs | warnings |
|---|---|---|---|---|---|---|---|
| g1 (HBM-BIND-11) | 93 | 92 (82,285) | HBM-042 `parent ID q_su00.u_su_Q0_lanes_plain0_3: ... no actual input of width 9` | 0 / 0 / 0 | 11,485 | 3036 | 0 |
| g2 (+ lid9 compose) | 93 | 92 (82,285), the same set (CHECKED) | `wavefront core reset q_su00/u_su_Q0_lane_exp0.rst_n: expected one bound leaf, found 0 (partition NE_su00 root)` | 0 / 0 / 0 | 9,945 | 3036 | 0 |

The straps delta is −1,540, which equals the expected 44 × (44 − 9) (CHECKED). The `bind_tied.json` files are identical. The run took 2:53 with a peak of 7.3 GB (intel1, MemoryMax 64G).

## Next masked EMIT (a different pattern: reset, so this lane stops here)
`q_su00/u_su_Q0_lane_exp0.rst_n` has no bound leaf. The compose cut `su_NE0.__cut_lane_exp0` (`ot_hnx_su_exp__efa9ca4d9700`,
16 members) exposes only `bank_rst_n`; the plan's reset wavefront expects a core `rst_n` pin. This is a reset-contract or pin-name
question for the SU exp cut (the lane `rst_lane_n[n]` vs `bank_rst_n` in the composed port set). It is not an ID strap.

Files: `bind_summary.json`, `mk_compose_lid9.py`, `compose_lid9_report.json` (44 changed and 4 kept, with plan ids), `mk_g2_manifest.py`,
`ot_hnx_su_plain4__lid9.sv`, `run_bind.sh`, `cmp_vs_b2.py`.
