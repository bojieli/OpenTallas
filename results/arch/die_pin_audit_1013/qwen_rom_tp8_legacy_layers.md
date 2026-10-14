# Legacy M6 / M7 tiles against the die cut model: qwen_rom

Die model qwen_rom_model.json (12180 instances, 15262 buses). Legacy = measured view top >= M6 on a die-placed master that is not hard IP; planned = no view, contract / generator plans M6+.

Legacy: 0 masters / 0 instances, 0 mm2, blocking 0 track-mm of die M6 and 0 track-mm of die M7. Planned: 2 masters / 131 instances.

| master | class | inst | top (source) | outline um | area mm2 | die M6 track-mm blocked | die M7 track-mm blocked |
|---|---|---:|---|---|---:|---:|---:|
| qkd_rhead | planned | 128 | M7 (contract) | 647.976 x 453.576 | 37.62 | 440859.5 | 440859.5 |
| qfd_sp_res_ser | planned | 3 | M7 (contract) | 777.576 x 518.376 | 1.209 | 14170.7 | 14170.7 |

## Cut windows (260 um, util >= 0.55)

708 window positions >= 0.55, 646 over 0.6; 0 of those are over 0.6 ONLY because legacy tiles hold M6 / M7 (they drop to <= 0.6 with the legacy tiles at M5); 593 more are over 0.6 only because of tiles the CONTRACT plans on M6 / M7 (clusters): over them the die has its own layer only, which a cut table that counts them as M5-capped does not show.

| cut | window | bits | util (closed views + contract layers) | util (legacy at M5) | util (all tiles M5) | legacy tiles over the window (um) | planned M6+ tiles over the window (um) |
|---|---|---:|---:|---:|---:|---|---|
| y = 23150 | 2860..3120 | 3185 | 1.033 | 1.033 | 0.55 | - | qkd_rhead 230.8 |
| x = 3100 | 16900..17160 | 4426 | 1.006 | 1.006 | 0.691 | - | qkd_rhead 171.4 |
| y = 18500 | 3120..3380 | 2210 | 0.907 | 0.907 | 0.403 | - | qkd_rhead 260 |
| y = 17850 | 3120..3380 | 2209 | 0.906 | 0.906 | 0.403 | - | qkd_rhead 260 |
| y = 15850 | 3120..3380 | 2185 | 0.896 | 0.896 | 0.398 | - | qkd_rhead 260 |
| x = 2900 | 22880..23140 | 2184 | 0.896 | 0.896 | 0.398 | - | qkd_rhead 260 |
| y = 22450 | 3120..3380 | 2174 | 0.892 | 0.892 | 0.396 | - | qkd_rhead 260 |
| y = 20550 | 3120..3380 | 2173 | 0.891 | 0.891 | 0.396 | - | qkd_rhead 260 |
| y = 19700 | 3120..3380 | 2172 | 0.891 | 0.891 | 0.396 | - | qkd_rhead 260 |
| y = 21800 | 28340..28600 | 2153 | 0.883 | 0.883 | 0.393 | - | qkd_rhead 260 |
| y = 22500 | 28340..28600 | 2151 | 0.882 | 0.882 | 0.392 | - | qkd_rhead 260 |
| y = 19900 | 28340..28600 | 2151 | 0.882 | 0.882 | 0.392 | - | qkd_rhead 260 |
| y = 20600 | 28340..28600 | 2150 | 0.882 | 0.882 | 0.392 | - | qkd_rhead 260 |
| y = 17850 | 28340..28600 | 2150 | 0.882 | 0.882 | 0.392 | - | qkd_rhead 260 |
| y = 16550 | 3120..3380 | 2150 | 0.882 | 0.882 | 0.392 | - | qkd_rhead 260 |
| y = 18600 | 28340..28600 | 2149 | 0.882 | 0.882 | 0.392 | - | qkd_rhead 260 |
| x = 3500 | 22880..23140 | 2067 | 0.848 | 0.848 | 0.377 | - | qkd_rhead 260 |
| x = 3500 | 10660..10920 | 2052 | 0.842 | 0.842 | 0.374 | - | qkd_rhead 260 |
| x = 28250 | 22880..23140 | 2051 | 0.841 | 0.841 | 0.374 | - | qkd_rhead 260 |
| x = 28250 | 10660..10920 | 2051 | 0.841 | 0.841 | 0.374 | - | qkd_rhead 260 |
| x = 2700 | 16900..17160 | 4427 | 0.807 | 0.807 | 0.807 | - | - |
| y = 14900 | 18980..19240 | 2528 | 0.728 | 0.728 | 0.728 | - | - |
| y = 18950 | 18720..18980 | 3040 | 0.708 | 0.708 | 0.708 | - | - |
| y = 18550 | 18720..18980 | 3040 | 0.708 | 0.708 | 0.708 | - | - |
| y = 17950 | 18720..18980 | 3040 | 0.708 | 0.708 | 0.708 | - | - |
| y = 16100 | 18720..18980 | 3040 | 0.708 | 0.708 | 0.708 | - | - |
| y = 10400 | 2340..2600 | 1647 | 0.676 | 0.676 | 0.3 | - | qkd_rhead 260 |
| y = 16500 | 28340..28600 | 1646 | 0.675 | 0.675 | 0.3 | - | qkd_rhead 260 |
| y = 15800 | 28340..28600 | 1645 | 0.675 | 0.675 | 0.3 | - | qkd_rhead 260 |
| x = 18600 | 14300..14560 | 1635 | 0.671 | 0.671 | 0.671 | - | - |
| y = 8400 | 28340..28600 | 1612 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 6300 | 3120..3380 | 1612 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 4350 | 3120..3380 | 1612 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 21900 | 3120..3380 | 1611 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 10400 | 29380..29640 | 1611 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 10300 | 3120..3380 | 1611 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 10250 | 28340..28600 | 1611 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 9850 | 28340..28600 | 1611 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 9700 | 29380..29640 | 1611 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
| y = 8350 | 3120..3380 | 1611 | 0.661 | 0.661 | 0.294 | - | qkd_rhead 260 |
