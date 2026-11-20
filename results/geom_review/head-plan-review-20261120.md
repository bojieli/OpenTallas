# HEAD r11b and r13 floorplan review

Viewed head_r11b.png, head_r13.png, and r11b_serdes_kit.png on 2026-11-20. The die plan panels use the lane geometry and the frozen clock-tree endpoint table, using one representative clock endpoint pattern per type. The hd_serdes panel uses the exact r11b bootstrap kit pin, macro placement, and landing geometry.

The die places repeated tile arrays symmetrically east and west of the center spine. Most wide links meet their neighboring faces directly. The long north and south side corridors have relay positions along their spans. The r13 hd_lep0N clock endpoints concentrate at its side interfaces and the mid-block load band. The new taps do not move the die-level bus faces. The narrow center spine and the corner turns need route overflow measurements. The die image does not resolve PG via access.

The r11b hd_serdes has its south-facing coll_i0 window next to the receiver landing group. The adjacent coll_o0 window faces the KP4 core cluster. The two SRAMs and KP4 retain distinct macro channels, and the layout leaves routes around the outside of the cluster. Clock taps follow the populated southern region. The image cannot establish SRAM pin access or PG continuity.

Verdict: r11b hd_serdes geometry is suitable for an exploratory kit run with its adopted tools. r13 die-level planned geometry is suitable for kit generation after the bind gates. Review emitted r13 kits before dispatch to physical tools. Require the final r13 PG access read before a whole-die route.
