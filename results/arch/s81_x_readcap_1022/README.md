# X read-stage closure successor

The current X SRAM access plus key/scale mux misses timing by 150 to 344 ps. READ_STAGE=1 inserts a 256-bit capture bank at each SRAM read face, then performs the existing key/scale mux. Both key and scale selectors advance through one matching register edge. Every kq bit arrives one edge later; xr stays unchanged. READ_STAGE defaults to zero. DIE4 and RTLGAP were notified before build; this is not an adopted calendar.

Model: MODEL.json records exact added storage, unchanged bandwidth/shape, and +0.833333 ns key arrival. This fixes a significant timing issue within the frozen interfaces.

Checklist before native-first gates:
1. Pins: unchanged source-registered faces; no additional pin layer or serialization.
2. Reach: local read capture per SRAM row, existing column size 237.6 by 432 um; capture-to-mux reach to be measured, reject any >405 um single-cycle path.
3. Fanout: per-bit capture loads at most key+scale (2); select copies retain 16 loads each. Native census must pass before floorplan.
4. Depth: macro access separated from the wide mux. Exact timing remains a gate obligation.
5. Storage: all existing bulk storage remains SRAM; added capture is pipeline state, 1024 bits per column, not an indexed array.
6. Floorplan: existing four-macro single-column arrangement retained, full-width cell band; measured synthesis area and fill will be collected. No density waiver.
7. Clock: existing source pin band retained; internal readcap flops join same clock. Clock spread <=80 ps at TT/FF remains mandatory, no clock waiver.
8. Schedule: kq +1, xr +0; notified DIE4/RTLGAP, adoption requires exact consumer calendar. No performance credit claimed.

Proof compares delayed kq against the original flat X for 20000 randomized changing-data cycles, reset pulses, and a dropped-write mutant. Default READ_STAGE=0 also runs unchanged.
