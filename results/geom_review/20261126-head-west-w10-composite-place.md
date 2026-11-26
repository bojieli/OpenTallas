# West LEP W10 detailed placement review

**FIX-FIRST.** I opened the native layout and density PNGs for the E7 detailed placement of the W10 composite plan `d51fe3b01ffe`. The two hard-pair macros and ten SRAMs are separated, including the narrow horizontal SRAM channels. The heat map shows concentrated cells along the center SRAM spine, the western corridor, and the upper-right landing band. The native occupancy and channel figures pass the scoped placement checks. The FCLK position mismatch and the two flagged clock and fanout measures hold this checkpoint downstream.

| Check from the exact placed database | W9 rows2 | W10 composite |
| --- | ---: | ---: |
| Peak standard-cell density per 10 µm bin | 0.667 | 0.667 |
| Bins above 0.700 density | 0 | 0 |
| Connected dense lumps meeting the area threshold | 0 | 0 |
| Peak density on the upper-right landing band | 0.610 | 0.596 |
| Peak estimated channel use, nets per track | 0.468 | 0.386 |
| Maximum pin-track use | 0.262 | 0.262 |

The upper-right maximum is at (789.3, 1379.3) µm. The center maximum remains at (439.3, 619.3) µm. The west corridor's peak is 0.645 at (19.3, 299.3) µm, compared with 0.632 in rows2. The highest channel estimate is between the two third SRAM banks near (452.496, 623.712) µm. The 44.472 µm channel uses an estimated 0.386 nets per track versus 0.274 at the same location in rows2. The west bank 0–1 channel retains its 14.04 µm gap and drops from 0.468 to 0.231. The renderer measures placed cell area against free area, excluding macro bodies, hard blockages, fillers, decaps, and tap cells. Channel demand is a pre-route pin-box estimate.

Detailed placement reports zero row alignment, overlap, edge spacing, and padding violations. It preserved 25,881 legally packed landing cells. No density or channel source change is indicated by these observations.

The exact FCLK pin `fclk_in_coll_i1` is physically at y924.256 µm. The upstream-aligned contract calls for y742.816 µm. The source-gated and visually reviewed one-port repair is `7d14ad1270aa`. Independently assigned diagnoses cover the raw pre-CTS `clk` centroid metric of 908.961 µm and the 1,040.9 µm fanout spread led by `u_run_in/_2_`. The current d51 checkpoint is an observation-only placement.

## Exact evidence

- E7 kit `/srv/opentallas-scratch2/claude/head-west/west_w10_place_1126/kit_work/gen/hd_lep0N_w`, physical unit `oth-ubuntu-2953783-1795693290` exit 0. The native `3_5_place_dp.odb` and copied `3_place.odb` share SHA-256 `917c3636bf1831f5a18c306138fedf2cad6ba94f29d681b076e9d1784dd73f47`.
- Opened `run/layout_review/place/layout.png`, SHA-256 `a3853a4dba9b331de5492bc9bfc87584fa92f4724dddf6f8549b94a3ee3a809e`, and `density.png`, SHA-256 `6893b646c9675fddb081ba22fa3d6b4156ef2f1cfe130294a7c197dc698f1417`. Native `smells.json` is colocated. The comparison uses the same native artifact from the retained E8 W9 rows2 kit `/srv/opentallas-scratch2/claude/head-w9-fp/west_rebalance_1125/hd_lep0N_w_1125192840/hd_lep0N_w`.
- The running flow emitted the independent visual-review request `3a02bc8f0f911cdef1662d9ce1289e755d9930617ba45e6de487c907b4776b2f`. This inspection records a separate reviewer observation.

## Lower SRAM junction and right bypass

The independent image reviewer flagged the lower SRAM aisle where it meets `u_rg2.u_pair`. Exact OpenDB extraction gives an open vertical aisle 44.472 µm wide. The junction at its base is 12.972 µm high, with 20 standard cells occupying 5.832 µm², or 1.01% of that window. The horizontal windows under the two lowest SRAMs have 4.30% and 4.16% standard-cell area. Stock pin-box demand for the west horizontal gap is 0.082 nets per track.

The two lowest SRAMs have 202 and 203 connected inward M4 signal pins. Both have zero south-facing signal pins. The lower pair has 100 north-facing signal pins at the throat and 479 below the west SRAM, on M5 and M7. The native overlay found zero positive-area same-layer intersections with actual VDD and VSS metal and via enclosures for all of these pins. Both supplies cross the junction on M5, M6 and M7 and have stacked vias there. The lower pair's right bypass is 8.64 µm to the die edge and 4.32 µm to the core edge. It has 0.67% standard-cell area and a pin-box estimate of 0.001 nets per track. The lower pair exposes its signal pins on the north and west faces.

The stock macro power probe found physical supply contact at all 24 macro PG terminals and all 1,462 shapes. Full OpenROAD connectivity reported two isolated VDD fragments and two isolated VSS fragments on M5 and M6 near the upper west SRAM row at y685–687 µm. The independent PG owner is working that class. The lower junction, bank pin shapes and right bypass support retaining their current geometry under these placement checks. Detailed signal access remains part of the eventual route qualification.

Read-only extraction and overlay outputs are in E7 `/srv/opentallas-scratch2/claude/head-west/west_d51_lower_access_1126/` as `lower_corridor.log`, `macro_pg.log`, `pin_access_local.log` and `native_checks.log`. The independent automated visual verdict is ISSUES for request `3a02bc8f0f91`. Its sidecar remains authoritative for the automated hold.
