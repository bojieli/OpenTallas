# HBM die contract v14: area table (2026-10-14)

Die 32,984.288 x 25,980.528 um = 856.95 mm2. v14 plan blocks 467.88 mm2 + relays 49.61 mm2; free (100-um grid) 335.15 mm2 = 39.1 %.

| v14 change | n | mm2 |
|---|---:|---:|
| quadrant COLL SW (hfd_coll_q3: engine band + 3 hcoll ports + 32-tile TKM) | 1 | 6.1081 |
| quadrant COLL SE / NW / NE (hfd_coll_q2: engine + 2 hcoll ports) | 3 | 2.4634 |
| die clock root (hfd_ckgen) | 1 | 0.0467 |
| freed: central hfd_coll 1,399.68 x 1,561.68 + hb_tkm slot 2,255.04 x 1,844.64 | 0 | -6.3456 |

| element | n | slot mm2 | real mm2 | real / slot | v14 | status |
|---|---:|---:|---:|---:|---|---|
| IDX scorer (hfd_idx_score_native_grid) | 4 | 5.2924 | 9.5423 | 1.803 | four corner bands kept (default): 2,965 x 4,374 each, leaf + macro density 73.6 % | AREA OK at 73.6 % leaf density; glue / partition unproven (owner: native IDX) |
| SFU quarter (hfd_sfu) | 4 | 2.2079 | 1.6688 | 1.149 | slot grows +216 um into the equator band hb_hc_eng left (v14 hc_eng in the N spine band): 2,016.144 x 1,311.12 = 2.6434 mm2, usable 1.4531 + 0.4355 = 1.8886 >= real 1.6688 (13 % margin); the corridor repair stays an optional SFU-owner improvement | FITS (slot change, SFU owner re-pins against the assigned file) |
| FrontC (SM front cluster C, inside hfd_sm) | 32 | 1.0128 | 1.1641 | 1.149 | unchanged | OPEN: SM parent re-pack (owner: SM compaction) |
| HC scalar leaves (inside hfd_hc SYS reservations) | 4 | 1.0255 | 0.5797 | 0.565 | unchanged | GEOMETRY FIT; 660 residual roots + retained bank control have no outline yet (owner: HC) |
| SM (hfd_sm) | 32 | 3.6378 | 7.2380 | 1.990 | UNCHANGED BLOCKER: 32 x 7.238 = 231.6 mm2 of closed SM leaves (no channels) vs 32 x 3.638 = 116.4 mm2 of slots; the SM.MATVEC redesign (XP tiles eng_de 112.32 sq + aq / bfm / buf / 4 rd_ln / rdc / sps / xwm = 0.127 mm2 a quadrant set) does not change it; SM rows are 1,131.84 tall with 1,209 / 562 um channels between rows, so a 2x SM needs the SM owner's compacted native frame (FrontC alone 976.32 x 1,192.32 > the 1,131.84 slot height) | BLOCKER (owner: SM compaction / VM-SM 2240) |

Sources: v13 real-area receipts (area_v13_1014.json); v14 blocks from the model named above.
