# QC West SC raw reset copy placement

The exact C1q bind for plan `00abead30cfa` retains the raw reset topology from the affected detailed placements. Both paths use an existing synchronous copy of a depth-six raw reset node. The copy serves the transmit-side START cone. C1q already has independent registered reader START branches. Moving the existing raw copy can shorten both its incoming and outgoing legs without spending a reset or mission cycle.

| Type | Raw source and consumers from the C1q RTL | Old worst direct span | New physical group rectangle in µm | Projected worst span with window |
| --- | --- | ---: | --- | ---: |
| `slw_sc_v3` | `rst_rl_322` through `u_cland_rst_x_fw_fe_i` to `u_cland_rst_tx_p0/p1` | 484.326 µm | [92.88, 511.92, 97.20, 516.24] | 341.685 µm |
| `slw_sc_v1__cl64543eaf__cl5e017c6f` | `rst_rl_219` through `u_cland_rst_x_fw_fe_p1_i` to `u_cland_rstart_tx` | 1,152.684 µm | [330.48, 935.28, 334.80, 939.60] | 303.723 µm |

The exact older placed endpoints are from I1 C1O West SC v3 attempt `1125084856` and E7 West SC v1 attempt `1124082545`, with the v1 result reproduced in `1124145602`. C1q emitted raw source coordinates agree with the measured launch flops. The new rectangle selection excludes the full hard macro row-cut halo and other generated landing reservations. Both exact group overrides are accepted by stock `landing_place.tcl`.

I viewed both revised stock type images and the focused old/new path plot for plan `516754bff56e`. The plan adds only the two corresponding `clock.landing_contract.group_rects_um` entries. No RTL, source depth, landing bus or latency field changes. Read the plan, focused `west_sc_raw_source.png`, both stock images under `render/`, and placement calculations at `epyc8:/srv/opentallas-scratch2/claude/CODEX-CLOSURE-SWEEP/west_sc_raw_1126/`.

The independently measured v3 `u_rrl_67` to `u_bin_x_ctl_i/eq` 994 µm leg has no intermediate raw copy and remains a separate hold. The prior pre-route setup estimates of −201.11 and −160.02 ps need fresh actual measurement on any successor. The reviewed plan is a source-only repair for the raw-copy cohort. C1q publication remains on its original exact source. No new placement or route was submitted.
