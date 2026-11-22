# ROM frontend coupon placement review

2026-11-21 16:12 PST, ROM-WEIGHTS-1119. Verdict PASS-COND for the private frontend coupon route.

I read the placed image at E10 `/srv/opentallas-scratch2/claude/romw-1119/array_frontend_1121/placed/frontend_placement.png`. The locked RVT map contains 100 logical instances and 13 input registers at 9.506 µm². The 35 physical rows fit in a 1.188 × 9.450 µm block inside the 1.248 µm center slit. The left row taps feed the same signed M4 supply stripes used by the native array. Register sources occupy the first 13 rows. Decode rows group the address consumers by output use. The placement leaves 21 µm of unused height above the block. Its longest direct pin-to-pin reach is below 10 µm.

The narrow X dimension limits vertical signal capacity. The coupon DEF keeps the existing supply risers and stripe shapes as routing obstacles. It exposes 17 input and 41 output bits on separate sides with individual M4 access rows. The occupancy and endpoint reviews support trying its short internal interconnect within M2–M4. This coupon has no die ports, hard-macro obs change, external clock tree, or array-integration release. Any route artifacts remain in its private E10 run directory. The first tool invocation exited on a negative default M2 track offset before any route.
