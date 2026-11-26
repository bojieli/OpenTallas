# S81 North LEPE MUS C t1 face reach

The retained E11 I/O floorplan c71a6ecca39a and executed placement-hook site ledger reproduce the north face violations. The exact R11 North source is 1f8fcdd9c4d7. The source-only face candidate 072d6d20766c uses exact bound payload and epoch inventories. I viewed both the full plan and the native-row overlay. The gate applies six source changes, validates the stock output and packed input seat shapes, and finds no overlap among their exact seats. The strict 405 µm source model clears the four face rows covered here.

| Chain | Retained maximum | Source candidate maximum | Scope |
|---|---:|---:|---|
| leafdn_o1 rank0 to face | 450.090 µm | 396.900 µm | Same three stations, revised rank1 and rank2 seats |
| leafdn_o2 final leg | 415.530 µm | 385.560 µm | Same five stations, one moved epoch seat |
| leafup_i0 first and adjacent legs | 452.790 µm | 396.900 µm | Same packed D3 receiver, revised first two banks |
| leafup_i1 | 779.490 µm | 398.998 µm | Priced receiver D1 to D3; table 12 to 14 for up_s_7S_L3 |

The i1 exact wrapper actually emitted D1 despite three entries in the old floorplan. The i1 end-leg result uses the retained movable direct sinks, whose new geometry and timing require actual placement. The candidate preserves 559 live sites in the old middle bank and reserves the optimized-away epoch seat in all three banks. The stock source gate validates the proposed D3 exact bank against the independent reciprocal lane pricing proof.

The north face packet, image and gate logs are in E8 cut2100/codex-lepe-north-face. Apply its guarded face rows before the independent o1 source-leg and o2 upstream overrides, which use the same native pin and seat census. SID14 leafdn_o4 is a separate approved rank addition and remains the only old source-level exceedance in this scope's lean image. The lp_xf_driver fence belongs to its separate owner. Review the fully composed source and actual fresh placement before routing.
