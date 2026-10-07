# S81 v6b (hop stations in channels, meso d8g1, cfifo v2)

Round trip scan 161 / layer1 165; python legality 0, pin clashes 0.
PA overlaps 41 / 52 / 54 (all hop-fix stations, after the track snap: v6c pads them 2.16 um).
GRT i50 overflow scan 1,444 / layer1 223 / head 984 (v5 341 / 137 / 466): the hotspot is still the HC corridor crossing
(hb_hc_s<->hc_n 2 x 1,024 b, rE*, aSE, qSE, KE0r) at x 16.5-17.5, y 10.5-12.0 mm; the added forwarded hop stations sit there too.
Next design change: remove the hc_s <-> hc_n corridor crossing (HC halves exchange 2 x 1,024 b across the corridor).
