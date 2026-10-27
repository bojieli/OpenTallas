# S81 graded mesh driver profile before build

Image `profile_sites.png` VIEWED 2026-10-27 by CODEX. Data are plan predictions, no routed successor.

Original proportional drivers in one row intersect132 hard-core/PHY bodies and2 clock cells. Compact multirow driver banks at exactly the existing4094 clock site centers eliminate all hard-core/PHY body crossings and all clock-cell overlap pairs (full body census,0/0). No site moves; existing driver feed/drop locations preserved. The image shows a symmetric graded cross with dense driving near the L1/L2 split; the enlarged site5_30 shows an open gap to the hard-core edge and compact bank. PASS-COND for driver geometry only. Route remains BLOCKED on full upper-tree405um repeated reach (86 unplanned pushdowns), upstream input loading, slew, PG/EM, width/shield profile import, and die timing predictor.

Count correction: base m2 matters. Actual+19520BUFx24, max20/site,8538.048um2 added cell body area; previous PD13 report+9760 undercounted physical buffers by2. NLDM upstream input-cap consequence separately adds up to18.52psTT/15.62psFF at1088 parent nodes (40ps input-slew prediction; not real timing).
