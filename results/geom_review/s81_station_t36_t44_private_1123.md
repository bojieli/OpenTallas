# S81 J8 station t36 and t44 changed placement review

Both exact private placements and static images were reviewed on 2026-11-23. Both remain held for route. There was no GRT or STA in the review.

| Type | Placement delta and exact result | Remaining hold |
|---|---|---|
| `slice_station__t36` | E10 `kw43-wave-1109n/diagnostics/codex_station_t36_0957`, place unit 809753 and static unit 2047046. Shifted seats of 95 existing FT1 START writers at the same depth. FT1 START capture improved 198.25→144.9 µm. Worst capture 148.75 µm on FT0. Maximum r2r 351.27 µm, zero over 405. Nearest-clock reach 300.95 µm. | P90 43.37 µm against 30. E/W partial faces each cover 50% and contain 2,636 pins. The view shows both large right-hand FT bands and the north receive bands. Preserve FT1 improvement and distribute the high-percentile captures before another placed check. |
| `slice_station__t44` | E8 `kw43-wave-1109n/diagnostics/codex_station_t44_1008`, static unit 2507854. Equal-area FT2 SOUTH band shift improved pin p90/max 67.46/191.76→45.63/146.30 µm. FT2 START 146.10 µm, with FT1 now worst. R2r max 361.45 µm and zero over 405. Nearest-clock reach 341.17 µm. | E/S partial faces and high pin p90. The image shows thick south receive bank, tight east capture and the sparse upper-right footprint. The band move is ready for another exact compose, with no route relief. |

Exact images, numbers and dump live in each diagnosis directory under `geom/auto_geom.png`, `geom/auto_geom.json` and `geom/geom.tsv`.
