# Qwen3-8B HBM accelerator tile die: measured power at the P8191 decode (2026-10-06)

**Result (TT 0.70 V, 1.2 GHz, TP4 AR token at P8191).** The die averages **309.0 W over the decode token against the 474.6 W liquid-cooling budget: PASS, 165.6 W margin.** SS gives 267.3 W and FF 369.0 W, both PASS.

The 1,536 tiles draw:

- **689.6 W while the fabric clock runs**: 0.449 W a tile, **1.03 W/mm²** of tile area. The floorplan assumed 1.05 W/mm² at this in-phase point.
- **182.3 W averaged over the token** (0.27 W/mm²). The core's engine clock gate (`ME_IDLE_GATE`, an `ot_hdc_cg` ICG already in the RTL) stops the fabric for 73.3% of the token's cycles. The fabric runs 25.5% of an HBM layer, 57.7% of an SRAM layer and 82.5% of the head.

Peak and average:

| TT | W | W/mm² |
|---|---:|---:|
| Die, token average | 309.0 | 0.373 |
| Tiles, token average | 182.3 | 0.272 (tile area) |
| Tiles, in phase (fabric clocked, stage average, head) | 689.6 | 1.031 |
| Tiles, in phase, worst 512-cycle window (L0) | 787.6 | 1.177 |
| Die, in phase clocked | 869.8 | |
| Die, worst-window bound (every term at its own peak) | 967.9 | |

The in-phase peak exceeds 474.6 W, but only while the engine runs. That lasts from a few hundred cycles up to one stage: 3,223 cycles, or 2.7 µs, in the head. The cooling budget is time-averaged over far longer than a token (0.49 ms).

The figure that limits throughput is the fabric duty the budget allows: **0.504 at TT, 0.648 at SS and 0.380 at FF**, against 0.267 for single-user decode. Batched requests that fill the idle stages can therefore raise the fabric duty only to about 0.5 (TT) before the budget binds.

**Verdict: no fix is needed for the single-user rate, so none is priced.** `tools/three_machine_compose.py` does not compose the Qwen HBM row, and no rate changed. If batched fill pushes the duty past the cap, the fixes in order of throughput cost are:

1. **Tile-internal ICG (zero rate cost).** Gate each pipeline and lane group on its own enable. The clock network (0.146 W) plus the flop internal power (~0.11 W) is a fabric-clocked floor of ~0.26 W a tile, about 57% of the clocked tile power, paid even when the tile's datapath does not toggle. This needs RTL plus a re-route; it has not been measured.
2. **Fewer tiles per die across more dies.** Die count is not scarce. Tile power scales with tiles per die. The TP change has a collective cost that has not been measured.
3. **A lower clock.** It costs rate on the compute-bound stages only (L0 and head). HBM layers wait on the stream for 59% of their cycles.

## Method (every tile term measured)

1. **Vehicle.** TP4 HA8 at the routed tile's exact parameters: target arithmetic ACC_LAT 7 / TREE_LAT 7 / MUL_LAT 6 / FAST_ISSUE 1 / KV_PREP 3, MEM_EXTRA 1, SMIN 7, CODE_BANKS 5, plus spine_h SCALE_LAT 6 and w224. It ran L0 (SRAM layer, preroll 5,000), L20 (HBM layer, preroll 1,000) and the head at P8191. Every stage is bit-exact against the GPU golden: L0 and L20 X on all 4 dies show 0 mismatches, and the head token is 18 with logit bits 42282b99, equal to the oracle. Stage cycles: L0 6,227, L20 17,293, head 3,223. Fabric-clocked cycles: 3,591, 4,408 and 2,658.
2. **Tile port records.** `RT_TILE_TRACE` is a default-off env var in `rtl/test/qwen_rom_runtime/qwen_hbmacc_rt_w12.cpp`. On every fabric clock edge it records die 0's tiles 0, 1, 3, 7, 15, 31 and 1000: their inputs before the edge and their outputs after it. Those tiles cover one per split-tree host level k1..k5, one non-host, and a second k1. The die has 768 / 384 / 192 / 96 / 48 hosts and 48 non-hosts.
3. **Replay.** `rtl/test/qwen_rom_runtime/qwen_tile_replay.cpp` replays each record on the Verilated tile. All 21 replays are bit-exact on every output. The negative control inverts the first issued instruction word and is detected every time (rc 3). The replay streams a VCD through `tools/signoff/vcd2saif` for the whole stage and for 512-record windows. `tools/signoff_analysis.map_rtl_saif_to_netlist` then maps the register toggles onto the routed flops: 102,101 of 102,102 match, and all 7,920 ports. This RTL-name method is the one in `docs/POWER_CLOCK_SIGNOFF.md`.
4. **Power.** OpenSTA `report_power` runs on routed `tile_tp4_t4` (`hbm_accel_fmax_inventory_20261004/qwen_me/routes/tile_tp4_t4`, 6_final.odb + 6_final.spef + 6_final.sdc, 0.833 ns) at TT 0.70 V/25 C, SS 0.63 V/100 C and FF 0.77 V/0 C RVT. It reads each pin SAIF; 110,021 pins are annotated, and OpenSTA propagates the rest. Vectorless TT gives 0.832 W a tile, against 0.449 W measured while clocked.
5. **Composition.** `tools/qwen_hbm_die_power_compose.py` builds `die_power.json`:
   - Token: L0 × 5, L5 + L6 + L20 × 31 (the HBM layers carry L20's tile energy), and the head × 1.
   - Token time: the floorplan-priced 588,031 cycles (routed bound).
   - Gated cycles pay leakage only.

**Terms that are not measured tile power:**

- SRAM macros. Liberty read energy is charged per enabled access, with the compiler's write energy for the window fill and liberty leakage: 1.12 W dynamic plus 0.67 W leakage per die over the token (TT). Charging the liberty's unconditional clk energy on every fabric edge would add 5.3 W.
- Die wire. The routed q3a wire is taken at 0.2 fF/µm × 1.6, using the tile's measured port toggle densities (tree 0.31, broadcast 0.008 transitions per bit per clocked cycle). One register per 430.56 µm stage is charged at the tile's measured 2.6 fJ per flop-cycle. Total: 19.9 W average, 65.9 W peak.
- HBM PHY: 0.8 pJ/bit (O'Connor; 0.29 Chae) plus 2.8 W per stack idle. Total: 33.6 W.
- Assumed, not measured, taken from the floorplan: stream services 34.58 W, spine 34.52 W, hub 3.78 W, heads 0.21 W, waypoints 0.13 W.
- The combinational part is an upper bound, because OpenSTA's probabilistic propagation over-estimated the routed argmax by 2.1x. Halving it puts the token-average tiles at 157.8 W.
- Leakage is negligible in this ASAP7 PDK: 0.77 W per die at TT 25 C and 2.1 W at SS 100 C, SRAM macro leakage included.

**IR.** The floorplan's static IR drop (23.54 mV) was solved at the assumed 702.5 W of tile load. Scaled linearly to the measured worst window, it becomes 26.4 mV at TT and 34.5 mV at FF, both against the 35 mV budget. This is derived, not re-solved.

**Files.** `stages.json`, `activity/*.json` (exactness, negative control, reads, flop map), `ports.json`, `power_{TT,SS,FF}.json` (OpenSTA values per SAIF label), `die_power.json`, `runs/<stage>/` and `collect.py`. Remote: ot-epyc1tb `/srv/opentallas-scratch/claude/qwen-hbm-power` (pin SAIFs in `act/`, records in `runs/`).
