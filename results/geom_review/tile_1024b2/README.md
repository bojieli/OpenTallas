# GEOM-REVIEW tile batch 2 (2026-10-24 ~13:30 PDT) — new Codex kits (sub-agent GR-B2)
Images: localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-B2/<kit>/

| kit | stage | verdict | top finding |
|---|---|---|---|
| kv3_hub_Ei reach405 retry4 | 4_cts (GRT running) | PASS-COND | vC FAIL items fixed (out legs <=394 um, inner hops <=398, 0 empty taps); GRT hotspot at centre tap clk_t31 (1885 sinks > cap 1500, on ft63/64 column); arst_n single pin -> 126 syncs up to 2.6 mm (-846 ps) |
| CP1 col_h10_r1__t1 reach405 | 6_final | FAIL | -241.76 ps = 1191-um unpinned proof-leaf hop (977 bits >405 um); seam aligns exactly |
| CP1 col_h10_r0_p1__t1 reach405 | 5_1_grt | FAIL | ft slots fine (<=366 um) but proof leaf x/ret legs 1240-1550 um, CTS WNS -1042 ps |
| S81 hd_tile tap160c7 | 4_cts (GRT fail) | FAIL | elemA_cv M5 clock pin 24x24 nm accessible (own M5+M6 OBS); u_eA0/best_key 14-level path TT -627 ps |
| slice_station t3/t9/t25 405c1 | 5_1_grt | PASS-COND | 1104-b E-W slots now 4 stations, hops 357-363 um (v4.8 FAIL fixed); reset recovery -550..-578, in-hold -118..-148 |
| slice_station t33 405c1 | 6_final | PASS-COND | hops 302-310 um; NOT SIGNED TT -25.9, FF hold -45, spread 86.75 > 80, 1830 slew (BUFx6f too weak per hop) |
| slice_station t4/t32 405c1 | - | NOT REVIEWED | no ODB (ot-run: no host qualifies) |
