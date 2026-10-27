# INFRA-FIRST-QC-R17: identity 66/66 + 43.2-um centre channel die, dry 0/0 (UNCHECKED unless marked)

Branch claude/qc-mesh-r17-1027, off R16 a0cec27005. Run data: epyc2:/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg (out/d43b = the final variant).

## Tool changes (opt-in; defaults unchanged)
- `qc_clk_mesh3.py --lift-lane deepest`: a local row's lift repeater sits on the lane of the deepest y-tree depth on
  that row, for every row. Before this it used the row's own depth: rows 3 and 7 have depths 4 and 3, so cbx_q10's lift rep landed one slot apart. This was the R16 65/66 cause.
- `--row-slots holder`: a row's x slots come only from the partition that holds the row y. Before this, the union over
  partitions within tolerance let a neighbour of another type win the snap on one mirror half (the cbn_q00 4.86-um asymmetry that the R16 `--ytree-split` tried).
- `--centre-channel D`: the R16 PLAN-DELTA. The centre local rows move to YC - CC/2 - nudge. H_c sits on channel lane 2, and its Bt/Tm legs are mirrored about the die
  centre. The channel x-tree is a recursive merge over lanes (0,4,1,3) per depth, and none of its cells snap to an island.
- `die_clock_mesh.py build_explicit` spec key `channel_hosts`: a cell wholly inside a plan `clock_channel` rect is
  host-less die-top logic, not an island error.
- Tests: test_qc_clk_mesh3 + test_die_clock_mesh, 44 PASS.

## Plan delta
`scripts/r17_delta_inputs.py` applies the R16 rule to candidate_oneqc0733.json; the output is in `plan_delta/*.json.gz`.
- Rule: y > YC moves +43.2, the centre M8 strap moves to YC' = 13154.4, and the channel rect [1563.84, 13132.8, 31216.32, 13176.0] gets clock_channel=true.
- plan_d43 sha256 is f2c91d0338ee…. Its partition origins equal R16's G0-passed die_plan_r16_delta.json (checked by the script).

## Results, d43b (`--row-at 10471.68=10445.76,5227.2=5218.56 --lift-lane deepest --row-slots holder --centre-channel 43.2 --centre-split 30.24`)

| item | value | status |
|---|---|---|
| identity | 66/66 types, 324 instances, 0 violations; independent type-frame check (r15_idcheck --orient) IDENTICAL | CHECKED |
| export gate | PASS: 0 errors, 0 overlaps, off-lattice 0; 8330 BUFx24, 4644 nets | UNCHECKED |
| dry exact build | 0 plan errors, 0 overlaps, 0 keep-out, 1562.2 mm tree wire | UNCHECKED |
| nominal tap skew TT / FF | 25.64 / 24.36 ps | CHECKED (r17_numcheck) |
| MC 13 samples worst TT / FF | 328.8 / 283.3 (die-wide, not related) | UNCHECKED |
| TT setup (997 related pairs) | +540.10, 0 negative | CHECKED (independent recompute) |
| FF zero-logic hold | -115.32 ps; HB4 on all 997 | UNCHECKED |
| kit-contract FF hold, F4G RP1 + VMR core view | **+14.39 PASS** (need 25.61 <= W 40; worst sl_W1_su_c -> c_W1_bn_10; 1546 ordered pairs) | CHECKED (independent recompute) |
| kit-contract FF hold, plain | +29.36 | UNCHECKED |
| pair U max TT / FF | 122.25 / 116.57 | UNCHECKED |
| HB4 | 2,658,507 cells / 0.2714 mm2, 0 over headroom | UNCHECKED |
| H_c template imbalance | -1.57 ps TT; the Tm leg is 8.64 um longer, which is inherent to an odd H in 5 lanes | UNCHECKED |

r17b (the same fixes on the original die, for reference): identity 66/66; dry 84 errors, all in the centre channel; kit hold RP1+VMR +12.65.
Render `render/r17_render.png` (viewed): whole-die tree, the channel x-tree inside the 43.2 band, and the cbx_q10 frames.
