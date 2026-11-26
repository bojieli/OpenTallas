# HEAD N3 Turn W10 forwarded clocks and count straps

I opened the combined source plot for exact plan `c47315a62adb3685a70967e3c9b9788363753e3486f1396cce40254fa13d88f3`. The plot shows the two forwarded clock branches alongside the six M5 seats next to the northwest landing ring. This source is acceptable for one ordinary E7-only placement. CTS and routing require the fresh actual placement review.

The intermediate `4758c78a2c38` fixed the forwarded clocks, but native W10 detailed placement already showed six corresponding count inputs on the opposite side of the slot. The exact generated parent binds `nst3_turn.strap_ca_k_u1_i` to `6'b001110`. The retained partition physically contains all 292 first non-buffer inputs fed through those ports, at counts 269, 9, 9, 2, 2 and 1. All are in `u_cland_u1_i`. The previous six BTerms sat at y8.64–25.92 µm and the first real load centroids are at y568.5–580.1 µm. The static top tie leaves a real local access problem.

| Bit | New M5 seat, µm | Projected maximum pin-to-load span |
| --- | --- | ---: |
| 0 | (133.944, 578.880) | 114.180 µm |
| 1 | (142.584, 570.780) | 3.912 µm |
| 2 | (138.264, 569.160) | 4.080 µm |
| 3 | (142.584, 568.620) | 1.324 µm |
| 4 | (142.584, 566.460) | 3.000 µm |
| 5 | (142.584, 564.300) | 4.235 µm |

The projections use the existing fixed pin, OBS, via and PG geometry, with at least 1.968 µm of clearance to the nearest such shape and 1.392 µm between the closest new pin boxes. The worst bit-0 Manhattan span falls from 1,120.740 to 114.180 µm. Pin shape, layer, bit order, constant literal and wrapper interface are preserved.

The previously reviewed same-phase assignments remain `fclk_out_u1_o` from `clk_t4` and `fclk_out_d1_o` from `clk_t20`. Retain the six explicitly fixed data, FSTART and ready/fault launch groups and the clock-ancestry guard. Their same-phase source correction added zero cycles. The exact W10 sidecar remains `ba968452ea5a`.

Source plot and native replay artifacts are under E7 `/srv/opentallas-scratch2/claude/head-allfix/n3_turn_4758_ready_1126/combined`. The older N3 placement remains held.

The stock composed runtime exported the wrapper and all six exact M5 coordinates and confirmed the parent literal. Scoped PRE passed with zero findings. Its report-only estimates still flag the pre-existing per-bit FT hop projections on d1 and u1. Fresh placement will measure the realized geometry. The E7 readonly seal is `e5db2c325348d95bd2db40217be29ae979109f2bda9e78e49e8653110e2d8761`. The staged spec stays on E7 with no spill and `goal=place`.
