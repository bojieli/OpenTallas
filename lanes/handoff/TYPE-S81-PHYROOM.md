# TYPE-S81-PHYROOM handoff (2026-11-14 07:08 PST) -- STOOD DOWN (backup; COORD: phy fix = bus-window alignment by DIE-S81-92)

## Verdict: NO legal 3-move set opens >= 112 um above phy__t1.
Input: epyc7 /srv/opentallas-scratch2/claude/s81-b3-clk/ev/B3y_tl.json (398 partitions, die 32244.48 x 25980.48). Rect dump: epyc7 /srv/opentallas-scratch2/claude/type-s81-phyroom/parts.json. 17.28-um occupancy grid, partitions + 4 seal rings.

1. No free site for a moved row anywhere. No free rectangle >= 1442.88 x 1226.88 (either orientation) exists in the die. Total free area is 3.4%, all in streets and svc bands <= ~400 um wide. The "large free areas" (x 21893-32140 / 242-10350, y 1330-4302 and 5529-8363, upper right) are bounding boxes of thin street networks (5.2 mm2 inside a ~30 mm2 bbox), not open space. The only leaf-sized hole is the reserved SE corner keep-out (die.channels 29255.04-32140.8 x 103.68-1330.56, SerDes PHY bump/ESD). Die X spare cannot hold a 1227-1443 um column (X 32244.48, 755 spare if the limit is 33000).
2. The tight columns are a different set than in the NEEDS-LANE. Per-column slack above phy (all six columns sit on phy's top edge at y 1330.56):
   - x 11793.60: 129.6 (gap 7058.88-7188.48 above svc_3)
   - x 13236.48: 0 (stack runs to s_3N_L0 wide / gunit / top ring)
   - x 14679.36: 129.6 (above svc_7)
   - x 16122.24: 129.6 (above svc_9)
   - x 17565.12: 51.84 (top, under bk_sel)
   - x 19008.00: 0 (under bk_sel)
   Wide partitions couple the columns: s_3N_L0 (x 13236-17565, y 17236.80), gunit (13236-16122), bk_sel (16122-20450).
3. A partial no-relocation path exists but does not reach 112 um. In x 11793 / 14679 / 16122, svc_lo and svc_hi can shift +120.96 into their 129.6 gap (6 intra-column moves). B4's svc re-pack (lo 2998.08 + hi 2851.20 -> top 7179.84) consumes that same gap, so the two conflict. x 13236 and x 19008 have 0, and x 17565 has 51.84. Opening those three would need either:
   - reshaping partitions: shrink the 1278.72-tall leaf variants to 1226.88. That gives 2 x 51.84 = 103.68 below s_3N_L0 in x 13236, which is still < 112, and these are type changes plus re-sign; or
   - removing rows (type-count change), which has no destination, per point 1.
=> Option (b) is infeasible under the current outline. Phy room has to come from (c), the bus-window alignment.

## Side finding
die.channels top/side seal rings and the free-cell channels are at the OLD outline (top ring y 26421.12-26524.8; bk_col free cell 25194-26421), but the die is now 25980.48 (ring should be 25876.8-25980.48). The channels are stale after the refloor; DIE-S81-92 should regenerate them.

No builds were run and no plan files were written.
