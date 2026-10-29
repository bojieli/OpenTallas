Actual forced-on NL parent estimate, 833ps TT 0.7V, placement RC on the failed ICG1 native CTS prototype. This prices the ICG0 experiment conservatively but is not the new ICG0 tree's power qualification. Parent reports include all output clock branches and root clock cone (1805 reachable B/K cells, report clock group1341); child ETM internal power is zero, so separately add actual SIGNED child final routed ODB/SDC/SPEF reports. Forced ICG_EN=1 and unforced reports agree. Busy input activity0.5, floor0.0.

| Element | Busy mW | Floor mW | NL count |
|---|---:|---:|---:|
| Parent native CTS | 106.435679 | 46.331726 | 1 |
| Rawleaf SIGNED | 64.9079233 | 28.1749275 | 8 |
| ROMleaf SIGNED | 20.5477644 | 14.3167935 | 10 |

All ten ROMs busy:831.18mW/0.5301614592mm²=1.568W/mm². Two ROMs busy/eight floor:781.33mW=1.474W/mm². Floor414.90mW/tile, 48NL=19.915W; relative old~0.336W gated48NL floor this experiment costs~19.58W. No NK/720-copy adoption is authorized. Old PG-GRID-AUDIT 75um grid conservative linear estimate30.55mV is not a fresh PDNSim; fresh actual ICG0 tree power/PG required before adoption. Clock group28.183803mW is contained in parent106.435679mW, do not add twice.
