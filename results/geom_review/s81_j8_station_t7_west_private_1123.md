# S81 station t7 west monitor placement

The private placement of `slice_station__t7__cl362204c4` completed on epyc8 in `kw43-wave-1109n/diagnostics/codex_station_t7_0910` (unit `3653405`). I viewed the exact placement and density images. The west boundary and central station strips have open channels. The densest clusters remain at the south edge.

The monitor-only move seated 80 flops at the revised west window. The old two worst pin reaches were 254.86 and 253.20 µm. After placement, the farthest input was 74.04 µm, at `cland_fstart_in_ft2_i[0]`. The maximum measured register-to-register leg remained 320.27 µm. The scoped plan row is `cb848ef279e0`.

Route remains held. The exact revised checkpoint still has 39.46 µm pin capture p90 against 30 µm and two partially occupied faces. The south-facing `ft2_i` band contributes the farthest captures. Unit `532697` collected geometry with global routing disabled.
