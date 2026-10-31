# DIE-HBM-53 opstore_a/b plan-grow variants (10-31) -- NOT adopted

Input: GEOM-93 AUTO-GEOM FAIL PLAN on d44f (opstore_a a3: r2r 1200, channel_h 3.5, channel_v 3.06, col_v 2.62, clock_reach 851).
opstore_grow.py grows opstore_a 760.32x483.84 -> 760.32x609.12 and opstore_b width 976.32 (A) / 872.64 (B) into free q_b113 area,
re-spreads face pins, re-sites macros on static grids (A: 3 cols wide channels; B: 4 cols x 4 two-row bands) and the clock entry.
Plan checks (d44o base): station_resite +0 cycles; G0/G0C errors unchanged (2/10); 5 core_faces WARN new (g0*_delta_*.txt).
Kits: 4/4 GEN_OK + lint + preflight PASS; placed on epyc2 (PLACE_RC 0), AUTO-GEOM grt=false:

| opstore_a | d44f a3 | A | B |
|---|---|---|---|
| r2r max / count>405 | 1200 / 4993 | 1289 / 5066 | 1321 / 5036 |
| channel_h | 3.5 | 3.74 | 1.43 |
| channel_v | 3.06 | 1.44 | 2.47 |
| col_v | 2.62 | 1.42 | 2.42 |
| clock_reach | 851 | 679 | 675 |
| fill | ok | 0.138 FAIL | 0.132 FAIL |

Neither variant passes; grow trades fill for partial channel relief and makes r2r worse. r2r is RTL-structural
(r2r_hist_d44f.txt: wide bank read mux -> one face register bus, face inputs fanning to all banks); clock_reach is a face
register in the corner vs a single centre entry (685 um Manhattan floor at this outline). Fix = RTL column-local read
stage (+1 cycle) + core-internal clock tree / multi-entry, not plan geometry. opstore_b variants were still placing at park.
