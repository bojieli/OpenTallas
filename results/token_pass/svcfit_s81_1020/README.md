# DRIVE-S81-SVCFIT (10-20): svc_rs slot vs attw head groups -- (A) time-multiplexed attw priced, (B) slot growth sized
MODEL. `compose_svcfit.py` (rate, tools/toksim_s81_compose.py on the RATEFIX both_p126_t276 base = the CAL1/CAL3 base,
reproduces it exactly at G16) -> summary.json; `fit_svcfit.py` (areas, frames, scaled stages) -> fit.json.

## (A) attw with G hard groups (hgrp8 432x432, 4 heads each) = 16/G passes over the same job
Measured base (svc 809c78aa5 full1m T 640, 16 slices): scores 289 = fill 130 + 160 q.k beats; pv 596 incl. 160 P.V words.
G 8 = engine NT 2, G 4 = NT 1 (existing parameters, same hgrp8 child); every beat/word issued 16/G times.
| G | scores / pv | AR fixed | AR solved (pv joins the path) | MTP | attw outline (mk_attw_lp law) |
|---|---|---|---|---|---|
| 16 | 289 / 596 | 1,065.9 | 1,065.9 | 3,286.0 | 2851.2 x 2160 = 6.16 mm2 (4 tile regions) |
| 8 | 449 / 756 | 1,059.9 (-0.57%) | 1,053.9 (-1.12%) | 3,269.8 (-0.49%) | 1814.4 x 2160 = 3.92 (2 regions) |
| 4 | 769 / 1,076 | 1,048.0 (-1.68%) | 1,030.7 (-3.30%) | 3,240.6 (-1.38%) | 1296 x 2160 = 2.80 (1 region) |
| 2 | 1,409 / 1,716 | 1,025.1 (-3.83%) | 987.3 (-7.37%) | 3,183.7 (-3.11%) | 1382.4 x 1512 = 2.09 |
MU stays per-user bound (calendar period 1.01 M < T), so the aggregate moves with the per-user rate.

## (B) the slot cannot fit at 122 frames for ANY G
Die 31968.5 x 25000 is at reticle (W margin 515.7, 294 um above the frames). Service region now 10.9 x 2.73 = 29.7 mm2
(16 x 1214.2 x 1344). svc_rs without attw is pin-bound at 1728 x 1555.2 / 1641.6 entry (Codex ebcb8a9d5) = 2.71 mm2
(hard content alone 1.46: 8 sx_hrow, 4 smhq, smhr, smq, 144 relays). Slot = attw + rest; band = 16 slots x 1.10 gaps.
Free die area is only in <= 1.04-mm PHY corner strips (idx rg3 readers) and <= 1.02-mm slice-column voids: no attw fits.
| G | slot mm2 | band need | extra | frames (4.09 mm2 each) | stages (201 x 116 / f) | AR all-in | MTP all-in | dies |
|---|---|---|---|---|---|---|---|---|
| 16 | 8.86 | 156 | +126 | 91 | ~257 | 964.8 (-9.5%) | 3,049 (-7.2%) | ~1,180 |
| 8 | 6.63 | 117 | +87 | 100 | ~234 | 973.0 (-8.7%) | 3,079 (-6.3%) | ~1,080 |
| 4 | 5.51 | 97 | +67 | 105 | ~223 | 961.6 (-9.8%) | 3,074 (-6.5%) | ~1,030 |
| 2 | 4.80 | 84 | +55 | 108 | ~216 | 928.8 (-12.9%) | 3,035 (-7.6%) | ~990 |
The qualified 116-frame map (s201: AR 1,011.1 / MTP 3,159.2, 888 dies) drops f_2R01..f_5L01 above the band, but that
region (~61 mm2: 39.4 contiguous below the S-tier slices at y 5372 + six 1437 x 2490 pockets) holds no G variant.
WHERE: the band must clear frame rows 0-1 over >= 4 cluster columns AND lift the S-tier slices s_2S..s_5S (they start
at y 5372; 2 slot rows of >= 2160 need >= 4.4 mm clear) -- a die re-plan, not a slot tweak. The granted bk_sel
907.2 x 3283.2 (col 4, y 10122.3..13405.5) and seq_host 432 x 777.6 (col 4, above bk_sel, y >= 13503.9) do not touch
the band; they go into the same plan rev. COORD 18:37 also asks a TALLER CTRL-top channel (y 1524..1724): same band.
Caveats: stage counts below 116 frames are NOT qualified (ep9 exact allocator must run on the new inventory); the
frame -> stage law is lumpy (122 -> 116 frames cost +61 stages).
