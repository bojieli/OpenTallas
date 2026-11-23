# S81 t30 station placement review, 2026-11-23

Both changed forms were rendered from their exact detailed placement databases with GRT disabled. The current signed-wave forms retain their prior verdicts.

| Type | Placed database | Capture p90 / max | Longest flop path | Nearest clock reach |
| --- | --- | --- | --- | --- |
| `slice_station__t30__cl6a190133` | `ec3043c7cd01` | 26.27 / 85.60 µm | 395.17 µm | 257.62 µm |
| `slice_station__t30__clcedefe91` | `422d2820ca83` | 22.82 / 70.91 µm | 293.57 µm | 403.24 µm |

Both have zero over-405 µm data captures, zero unregistered pins, zero collapsed stations and zero NEED-STATION groups.

- E10 `/srv/opentallas-scratch2/claude/kw43-wave-1109n/diagnostics/codex_station_west_0905/reset_pin_r2/slice_station__t30__cl6a190133/geom/auto_geom.png`, static worker `oth-ubuntu-1338268-1795457936`. The receive rings for FT0 and FT1 moved 12.96 µm north. Existing depth-10 `rst_n_t14` register `u_rrl_70` moves from x=138.168 to x=151.128 at y=1209.600. The previously 408.51 µm path now clears. The original west monitor panel remains near its source at y=366.39–375.03.
- E10 `/srv/opentallas-scratch2/claude/kw43-wave-1109n/diagnostics/codex_station_fstart_0937/clock_1001/slice_station__t30__clcedefe91/geom/auto_geom.png`, static worker `oth-ubuntu-1338289-1795457936`. Existing `rst_rl_47` register `u_rrl_47` moves from x=120.224 to x=141.824 at y=669.107. Its adjacent reset reach stays below 300 µm. The same monitor correction remains in this variant, and the previous 416.52 µm nearest-clock tail clears 405 µm. The two stages and all pin and clock names retain their source roles.

Low fill and partial faces reflect these sparse feed-through station forms. Stage the two corrections for the next eligible full J9 compose and independent exact-view qualification. Existing queue and release gates remain in force.
