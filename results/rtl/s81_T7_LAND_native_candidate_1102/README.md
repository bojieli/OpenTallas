# T7 LAND 12-SRAM + LVT data-cut candidate: native gate PASS (disabled)

This implements the LAND algorithm from PREP `s81_T7_LAND_native_PREP_1100` (2b45fe0b1) and runs its native gate. Nothing in production RTL, a manifest, a recipe or a live kit changes.

**Reference.** The unchanged native helper `ot_bind_native_4c805` (640x256, four async reads, seven write slots in one process) is read at the bound addresses 4*(rc-1)+j. Its data goes through the verbatim selected `rowword` function and `kc_w` loop. `prepare_reference.py` copies these from `dsdv_svc_att.sv` 107c4a lines 434-441 and 469-482 and refuses any other source hash. The unconditional `ekv_w <= kc_w` capture follows.

**Candidate** (`land_candidate.sv`, MUT=0):
- Three writer channels: PC0 = slots 0-2, PC1 = slots 3-5, ROWS = slot 6.
- 12 real `ot_sram_1r1w_256x256_m2_r2c2` macros, indexed [writer][bank r&3], local row r>>2. The aligned-v2 simulation view does read-before-write.
- A reset-free 640x2 latest-writer table (LVT), updated in source order PC0, PC1, ROWS.
- At the capture edge each lane reads bank j, local row rc-1, from all three writers. It captures the OLD LVT entry and the live valid/window/need/scale facts as one 10-bit code (773 states). The lane word is rebuilt from the code and the three macro outputs.
- Writes to rows >= 640 are dropped.
- Interface: the native write ports unchanged, plus `rc`, plus the parent's existing per-lane compares (row<tjob, row<wcount), `need` and the scale shifter output. The integration therefore duplicates no source logic.

**Cost:** -1060 `ekv_w` FF, +1280 LVT FF, +40 metadata FF, so +260 external FF. Also +12 macro clocks, 0 reset loads, 0 cycles. This is the PREP pricing. The LAND conversion buys no FF saving; it removes the 163840-bit FF array that fails the T7 kit `memory_bits` check (640x256 > SYNTH_MEMORY_MAX_BITS 15616).

**Result:** PASS over 4096 edges at 833 ps. All 1060 raw bits are compared on every edge.
- Seeding: all 640 rows written through the real channels.
- Writes: 3014 / 2954 / 2989 on PC0 / PC1 / ROWS.
- Concurrent writes: 352 three-writer same-bank different-row edges (the 128/132/136 class), 1750 two-writer same-bank pairs and 1333 same-row multi-writer pairs.
- Read/write collisions: 723 same-edge reads of a row being written.
- Out of range: 530 writes at rows >= 640, and 308 edges with tjob > 640.
- Lane mix: 4779 window, 4321 compressed-needed, 2312 ignored and 4972 invalid lanes. 7950 lanes were last written by PC1 or ROWS.

Five independent controls each fail the unchanged checker:
- wrong priority: edge 238;
- dropped lower same-bank writer: 257;
- post-write LVT: 222;
- stale metadata: 214;
- one-edge-late read: 214.

Run on intel2 (ot-run unit oth-ubuntu-2388643-1793674139, exit 0): build 118.9 s / 415 MB, sim 1.1 s.

**Held:**
- The gate is two-state zero-start only. It is not an all-initial-state proof.
- Rows 640..1023 agree only because the native out-of-range read is 0 under Verilator two-state and the candidate never writes those rows.
- Not yet done: bound integration (separate packet), physical collision/CE/repair, macro fit/clock, 833 ps TT/FF timing, and source cohort/provider/epoch qualification.
