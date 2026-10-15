Static CDC leaf local pin assignment

The compute die accepts the 233.28 × 151.2 µm R0 leaf envelope and the real SRAM at (27.216, 34.56) µm from source request `5a33649d3`. The JSON assigns every bit of all 15 real ports to an exact M4/M5 track center. Each clock has its own measured phi − R delivery.

This assignment authorizes native leaf kits against these exact pins. It does not assign an absolute die location or qualify a route. Twelve role placements require the source-bound native producer/consumer map; the legacy monolithic IO slots and padded words do not establish that fit. Fixed write1/read3 and publication/reset guards remain in the static compiler contract. C14 is frozen and does not contain these new leaves.

The width revision preserves exact along-face positions and provides the required SRAM edge clearance. The native parent contract `qfd_io_xfifo_static.json` assigns all169 real parent ports, twelve explicit child homes and24 clock entries from `b53541400`/`7494a6c90`. The die generator exports this contract on every new compute build; it explicitly keeps the incomplete collective/calendar endpoint binding open. A legacy graph cannot pass as this production composition.
