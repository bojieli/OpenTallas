Static CDC leaf local pin assignment

The compute die accepts the 216 × 151.2 µm R0 leaf envelope and the real SRAM at (19.44, 34.56) µm from source request `5a33649d3`. The JSON assigns every bit of all 15 real ports to an exact M4/M5 track center. Each clock has its own measured phi − R delivery.

This assignment authorizes native leaf kits against these exact pins. It does not assign an absolute die location or qualify a route. Twelve role placements require the source-bound native producer/consumer map; the legacy monolithic IO slots and padded words do not establish that fit. Fixed write1/read3 and publication/reset guards remain in the static compiler contract. C14 is frozen and does not contain these new leaves.
