# KV D26 v1n raw reset geometry

Viewed the candidate relay windows and consumer pins on the D25f2 outline and hard macro footprints. The longest branches use the clear spine corridors and the horizontal gaps between macro rows. The shared north branch avoids replicating stages for 16 consumer pins. The review covers the candidate geometry. Mapped placement remains pending.

The first same-phase replay put two stages on overlapping 4.32 µm windows beside the northwest corner. The corrected rst_rl_30 site moved from [98.064, 1507.681] to [98.064, 1512.001] µm with the original register identity and connectivity. Its two neighboring macro-clear route lengths are 4.321 and 15.984 µm. The full literal replay still covers all 44 roles with 14 branches. All 96 stage-window interiors are disjoint from each other and from the hard macros. The longest planned raw hop is 300 µm. Local release is 10 to 13 clocks with zero data cycles.

Image SHA-256 8bc899af3dd879513c632982aa14209decb7a6ed90f5b5fb1e002ee673bdb9b6.
