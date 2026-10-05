# V4.1 ROM layer die: engine profile as the RTL instantiates it

Status: rung 1 ("resource inventory = RTL") record, plus a **proposal awaiting root decision** on discrepancy D1.
Record: `results/floorplan/v41_rtl_engine_profile.json`. Tool: `tools/v41_rtl_engine_profile.py`.
Test: `tests/test_v41_rtl_engine_profile.py`.

## D1 decision proposal: collective engines, package controllers, routers

The analytical ledger has 8 one-shot collective engines, 2 package controllers and 4 fabric routers per die. The die RTL has 1 of each.

| Option | Engines / ctrl / routers | Layer-0 collective cycles | Area (ASAP7 unit proxies) | Verdict |
|---|---|---:|---:|---|
| A: RTL as elaborated (16 lanes, DEPTH 256, GW 4) | 1 / 1 / 1 | 2,780 measured | 79,404 um2 | Matches the blocking schedule |
| B: literal ledger | 8 / 2 / 4 | 2,780 (no gain) | 574,159 um2 | Reject: seven engines would sit idle |
| C: one engine at 128 lanes (the ledger's real intent) | 1 / 1 / 1 | 2,149 to 2,780 (estimate) | 540,406 um2 | Belongs to D2/D4 (width, VM banking), not to the count |
| D: A plus the 7 independent expert-activation gathers issued as one | 1 / 1 / 1 | 1,741 (estimate) | 79,404 um2 | Largest lever found; must be measured |

Option C's low bound also requires 8x the VM write bandwidth. Without that, VM writes bind and nothing is saved.

**Recommendation: 1 collective engine, 1 package controller, 1 three-port router per die.**

- Correct the ledger rows to count 1. The engine area waits on the D2 width decision.
- Measure option D next.
- Package link endpoints are a separate gap. The die RTL has none (`ot_rom_pkg_link` sits outside the die). The derived need is 4: 1 UCIe, 2 T1 board links to the partner package, and 1 board stage-hop port.

Why:

- **Only one collective is ever outstanding.** COLL is blocking: `ot_chip_v41x_coll_dma` faults on go-while-busy. The 12 layer-0 collectives run back to back in `results/rtl/v41_tp_layer0_collective_sequence.json`.
- **Latency is mostly network, not engine count or width.** Of the 2,780 blocked cycles, 1,932 are network-to-first-VM latency, 727 are payload stream and 121 are startup/commit.
- **The ledger's 8 is an area multiplier, not a count.** `tools/arch_utilization_v41.py` lever `oneshot_128_lanes` has area 8 x `ot_rom_oneshot_die_d32`, i.e. 128 lanes / 16 lanes. `tools/v41_die_assembly.py` then entered it as count 8.
- **The 2 and 4 have no derivation** in any tool, doc or commit.
- **1/1/1 matches the die's actual interfaces.** The die has one core handshake and one VM port for the controller. The router has 3 ports: controller, UCIe, board. The peers are one in-package die and two partner-package dies.

Estimates are derived from the measured per-collective decomposition and are labelled `ESTIMATE` in the record. Unit areas come from routed records. The 16-lane DEPTH-32 `ot_rom_oneshot_die_d32` is not closed. There is no physical record for `ot_rom_oneshot_die_px` or `ot_chip_v41x_coll_dma`.

## Profile as elaborated (FULL_SHAPE=1, other parameters default)

Elaboration: Verilator 5.050 `--json-only`, which covers parse, link, parameter specialisation and generate unrolling, with no synthesis or ABC. It reads 97 source files (96 RTL and 1 include), resolved by module closure from `ot_chip_v41x_die` and each pinned by sha256.

Totals: 471,764 instances of 128 modules (259 specialisations), 345 behavioural arrays and **zero SRAM/ROM macro instances**. The ME, QE, attention and indexer engines share one issue slot, so only one of those ops runs at a time.

| Engine | Region | Leaf x per-leaf | MAC lanes/cycle | Analytical ledger |
|---|---|---|---:|---:|
| QE block-dot (BL 16, MP 1) | ROM_MAC | 16 x 32 | 512 | block-dot pool 1,059,840 (529,920 x m=2) |
| Indexer FP4 block-dot (G 4, L 32) | INDEX | 32 x 32 | 1,024 | (same pool) |
| ME BF16 (KIND 1, G 8, L 64, M 1) | ROM_MAC | 64 x 1 | 64 | BF16 pool 166,656 (83,328 x m=2) |
| Attention (NT 64 x H 16 x TD 32) | ATTENTION | 32,768 x 1 | 32,768 | (same pool) |
| Indexer head weight | INDEX | 32 x 1 | 32 | (same pool) |
| As-built matvec (fallback, never dispatched) | ROM_MAC | 64 x 1 | 64 | none |
| HC projection FP32 | ROM_MAC | 64 x 1 | 64 | 10,240 |
| Vector light / SFU lanes (SUN 16, SUM 8) | VM | 16 / 8 | 16 / 8 | 4,096 / 1,024 |
| Streaming select (4 slices x 16) | VM | 4 x 16 | 64 | 64 |

In total the RTL has 1,536 block-dot MACs/cycle against the ledger's 1,059,840, and 32,864 dispatched BF16 MACs/cycle against 166,656.

Unit counts that differ from the ledger (RTL vs ledger):

- Sinkhorn 1 vs 6.
- sqrt(softplus) 1 vs 2.
- Top-k select 1 vs 2. It is a different module: `ot_hdc_select_k6` is not instantiated.
- Activation quantiser 1 vs 4.
- FP4 QDQ 1 vs 4.
- Indexer head-sum 1 vs 4.

Units that match: indexer key control (4), Engram gather slices (24) and assembler (1). The HBM3E endpoints (4) are behavioural timing models, not PHYs.

**Gaps: ledger entries with no RTL instance (none substituted).**

- Logic:
  - Indexer output tail (4).
  - KV/key streamer `ot_hdc_kv_stream` (4). The keys stream through `ot_hdc_v41x_idx_kstream` x4 instead.
  - Package link endpoint (4).
  - Pool operand muxes.
- SRAM macros: all SRAM rows (KV row staging 42, HBM queues 8, VM 30, chaining buffers 4, collective queues).
- ROM macros: the mask-ROM array.
- Package interfaces: UCIe-A modules (17) and 112G SerDes lanes (45) are flit ports only.

Cross-check against the hand-written `v41_resource_inventory.json`:

- **`u_kv`.** At FULL_SHAPE=1 `ot_chip_v41x_kv_prefetch` is not instantiated. The KV service is `g_packed_kv` (`kv_rope_reqmux` -> `kv_reqmux`, `window_kv_prefetch`, `rope_hbm_cache`).
- **Window source.** With `WINDOW_HBM_ATTENTION=0` the window source is the external `window_kv_prefetch`.
- **Region of `u_tile.u_core`.** The inventory files the core under ROM_MAC. It actually splits across ROM_MAC, ATTENTION, INDEX and VM.
- **`qlist` word width.** It is 160 bits as elaborated, not 128.

All other instance counts and tile memory geometries agree.
