# S81 COL same-cycle register seats

I viewed the exact private R1 and R2 placement and density images. Both still show narrow channels between the central columns and storage macro pairs. The new seats preserve the registered stage counts. Both variants remain held for route.

- R1 `col_h9_r1__t1__clf32cde8d__pv387d6579`, epyc2 `kw43-wave-1109n/diagnostics/codex_h9r1_0926`. Place unit `3900719` matched all 193 overrides. The old 606.15 µm D7 path no longer appears as a need-station path. The affected frame input to rank zero dropped from 192 to 46 long bits. Overall 432 long bits remain in nine groups, with a 539.08 µm maximum on rt16a ranks 2 and 3. The next planned same-depth row `d7022d38e8ff` covers 238 exact placed residuals in five groups. It still needs placement.
- R2 `col_h9_r2__t1__cl774acf45__pve3ab90e7`, intel1 `kw43-wave-1109n/diagnostics/codex_h9r2_0948`. Place unit `3477406` matched all 131 overrides. Long bits dropped from 183 to 70 and no need-station paths remain. The three residuals are 50 rt22a rank-1 to lpl_2_w paths (worst 429.41 µm), 19 last frame rank to face paths, and one rt20b rank-2 to rank-3 path. Channel demand is still 2.522 times capacity. Busiest clock tap has 3,202 sinks. These measurements do not qualify the old macro and tap form for route.

Geometry collection had native global routing disabled in both cases.
