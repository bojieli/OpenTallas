# QC West SC v3 mission epoch reset localization

The exact C1q source `00abead30cfa` assigns three West SC v3 boundary epoch flops to mission tap `rst_n_t66` from `u_rrl_67`. All three long legs share that source. The existing mission tap `rst_n_t104` from `u_rrl_196` was present in the retained I1 C1O detailed placement `1125084856` and has no consumer in the current bound type. The replacement brings all three legs onto the same side of the hard SC core.

| Epoch flop | Retained t66 span | Projected t104 span |
| --- | ---: | ---: |
| `u_bin_x_ctl_i/eq` | 993.895 µm | 113.375 µm |
| `u_bout_x_ctl_o/eq` | 1,265.058 µm | 157.788 µm |
| `u_ft_x_ctl_su_c_o_0/eq` | 912.438 µm | 194.832 µm |

The t104 gate takes `rst_rl_194` and `rn_rst_rl_194`. Each rail has six relays from its existing synchronous input register before the depth-seven gate. I traced the t66 and t104 raw and START rails back to the same `u_rst_in` and `u_run_in`. Both taps carry the published mission role. This preserves both dates and moves three sinks with zero additional flops or clocks. The TX epoch data input stays on its existing independent t0 path.

The exact pinned C1q localizer reproduced the current bound RTL byte for byte from its existing 63 localization rows, then replayed all 63 with only the three t66 destinations changed to t104. It emitted exactly three `rst_n` pin changes. I viewed the focused exact source projection with the retained macro, gates and epoch flop coordinates. Plan `61f7ab9b423ad`, the bound replay, geometry and both traced rails are at `epyc8:/srv/opentallas-scratch2/claude/CODEX-CLOSURE-SWEEP/west_sc_epoch_1126/`.

The projection uses retained cell centers. The successor still needs a placement review and actual reset recovery/removal timing. The active C1q publication has no change from this packet, and no new placement or route was submitted.
