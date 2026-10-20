# s81sl_ve_r2s -- PARALLEL outline variant of s81sl_ve r2 (S81-SLICE3-VE, 10-19)

Same RTL as s81sl_ve r2 (claude/s81-ve-1019 78ad1399f: static streaming pairwise beat tree, D>=3 delay lines as
ot_hdc_delay_rf rings). Only change: outline sized from the r2 gate's SYNTHESIS area (std 41,013 um2) at util 0.50
-> 291.6 x 291.6 (r2: 345.6^2 at a guessed 60,000 um2 = util 31%); pin ranges rescaled to the new face.

## SAFE-DESIGN checklist (owner 10-19), r2s
| # | item | result |
|---|------|--------|
| 1 | pins registered, reset landed 2 stages | PASS (source-registered pins; reset_landing 2) |
| 2 | reach <= 405 um single-cycle | PASS (291.6 um outline) |
| 3 | fanout <= ~32 loads (kept copies) | FAIL: one merged reset sync drives 2,320 flops; 1,230 non-clock roots > 32 (Codex census) -> fixed in r3 (s81sl_ve_r3) |
| 4 | depth <= ~600 ps | WARN 602 ps in the shared f12 LAT-4 adder (k1->k3); r2 gate reg->reg TT +90 ps; calendars kept |
| 5 | storage: D>=3 lines as rings, no >2 kb runtime-indexed flop array | PASS (largest ring 832 b) |
| 6 | floorplan util 40-60 %, aspect <= 2:1, one std band | PASS (0.50, 1:1, no macros) |
| 7 | clock spread <= 80 TT+FF, io_hold_margin >= 0.03 | r2: 30.5/30.9 ps; margin 0.03 |
| 8 | static schedule | PASS (no change: reduce 129 / add 44 cycles) |

Item 3 fails -> this variant is a gate/diagnostic parallel only; it is NOT submitted unless the r3 safe RTL fails.
