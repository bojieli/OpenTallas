# Microarchitecture analytical model

Tool: `tools/uarch_model.py`. Records: `results/uarch/v41_rom.json`, `results/uarch/qwen_rom.json`, `results/uarch/hbm_gpu.json`. Test: `tests/test_uarch_model.py`. The binding method is in [AGENTS.md](../AGENTS.md) rule 1.

It covers all four designs: DeepSeek-V4.1 ROM (first), Qwen3-8B ROM, and the two GPU-organised HBM comparators.

## What this model adds

The architecture budget (`tools/arch_budget_v41.py`) prices the token's dependency DAG from die-level widths. It makes three simplifications:
- a matrix reads ROM at the whole die's aggregate rate (`bytes / spec.rom_bytes`);
- moving an activation vector in and the results out costs nothing;
- wire delay is one separate lump.

This model keeps the same DAG, the same per-token workload and the same dependency structure, and re-prices each node from the microarchitecture:

| Term | What sets it | Parameter |
|---|---|---|
| ROM read | The macros that actually hold the matrix. Contiguous: the matrix's own full-depth bank set. Striped: every macro, or the BF16-lane subset for BF16 matrices. | `mapping`, `macros`, `bf16_stripe_macros` |
| MAC | Lanes attached to the holding macros (one word per cycle per macro), or a die-wide cap for the as-built engines | `weight_macs_die`, `bf16_macs_die` |
| Activation in | The VM read port: K elements at `vm_read_elems` per cycle | `vm_read_elems` |
| Results out | The VM write port: rows at `vm_write_elems` per cycle | `vm_write_elems` |
| Fill | Element pipeline, plus broadcast and return wire stages from the W1 floorplan distances, plus return-tree levels | `elem_fill`, `bcast_um`, `return_fanin` |
| Stream unit, attention, indexer | Lane counts built, the index reader's measured sector rate, and measured attention and softmax job cycles | `su_lanes`, `sfu_lanes`, `att_macs`, `idx_macs`, `idx_reader_Bpc` |
| Collectives | Measured per-collective cycles | `collective_cycles` |

Two ledgers accompany every design:
- **Area:** ROM macros, lanes, capture registers and chunk partials against the W1 ROM-field MAC strips (132.34 mm²); dedicated units against the hub (233.7 mm²).
- **Network:** broadcast and return wires at the VM edge against spine tracks, per-column wires against the tracks available over the ROM, and register bits.

## Results at 1M context, busiest layer die (architecture target 4,933 tok/s)

| Design | tok/s | What binds | Area fit |
|---|---:|---|---|
| As built: RTL engines (512 QE lanes, 64 BF16, 4-element VM, 16-lane SU, 1,024 indexer MACs, measured attention and reader) | **56.8** | `wo_a` alone 5.1 ms, experts 2.7 ms, index scan 2.6 ms, lm_head 2.5 ms | trivially |
| Spec widths, W1 contiguous bank map | **400** | Every matrix is read from its own bank set: about 8,000 cycles each | yes |
| Spec widths, rows striped over every macro | **2,137** | VM read port: 4 elements/cycle, so 1,280 cycles per 5,120-wide projection | **no**: 184 of 132 mm² of strip |
| + VM 64/128 elements, BF16 on every macro | 4,761 | | **no**: 184 mm² |
| Striped whole rows, VM 64/128, BF16 lanes on 4,096 macros | 4,015 | whole-row reads (a BF16 row at K = 5,120 is 320 words in one macro) and expert tile collisions | yes: 104.8 mm² |
| **Proposal:** the same with each row's K split over macros in golden-aligned chunk runs, FP32 adders in the return tree | **4,336** | fixed per-phase fill (compute chain), index scan | **yes**: 107.5 of 132 mm² strip, 51.8 of 233.7 mm² hub |
| Proposal weight path with the dedicated units as built | 320 | index scan at 1,024 MACs: 2.6 ms; softmax at 16 lanes: 127 µs | |

Sweep: the VM port width and the BF16 stripe count (`results/uarch/v41_rom.json#sweep`) decide the physical design point.
- At 128 read elements or more, each ROM-field column needs 109–215% of the tracks over it. Those ports **cannot be routed** in the W1 floorplan.
- At 64 elements a column uses 56% of its tracks, the trunk needs 5 spine corridors, and the register overhead is about 2 mm².

## Design decisions this model makes (V4.1 ROM)

1. **Rows are striped over the whole ROM field, not given a bank set per matrix.**
   - The contiguous map caps every matrix at about 8,000 cycles, a 12× loss.
   - Consequences for W1's bank map: every matrix's rows interleave over all macros; a macro owns whole output rows (golden `csum` exactness is geometry-independent); expert sums happen in the element in id order.
2. **Rows are K-split over macros, not owned whole.** W10's striped bank map (`f02e4600`) measured whole-row ownership.
   - A macro reads one word per cycle, so a matrix with fewer rows than macros takes K / (weights per word) cycles per row, not words / macros.
   - Active experts also collide on shared tiles.
   - Whole-row ownership gives 4,015 tok/s. Splitting each row's K over up to 2^n macros, in power-of-two-aligned runs of golden chunks, gives 4,336 tok/s. That split is exact under the golden `csum` padded tree, with the partials added in the return tree in the same order.
   - It costs log2(split) FP32 adder levels (5 cycles each) and about 2.7 mm² of adders, and it also removes the routing-dependent collision variance.
3. **The element is one ROM macro, 2 FP4 block-dot lanes (64 MACs), a 274-bit capture register and 8 FP32 chunk partials.**
   - BF16 lanes (16 per macro) go on 4,096 of the 13,798 macros only.
   - Putting BF16 everywhere does not fit (+79 mm²) and gains only 2%.
4. **VM ports: 64 FP32 elements/cycle read (the x broadcast leaves as FP8, 512 bits) and 128 elements/cycle write.**
   - These are up from 4 read and 64 write.
   - This is a banked-VM design task: 8 + 16 banks of 256-bit SRAM.
5. **Dedicated units must be built at the spec widths; this is the largest remaining gap to the as-built RTL.**
   - **Indexer:** 248,832 FP4 MACs against 1,024 built (243×).
   - **Index reader:** at the HBM rate of 3,482 B/cycle against 1,920 measured.
   - **Stream unit:** 1,024 linear and 256 SFU lanes against 16/8.
   - **Attention probability loader:** the measured 609-cycle job against 141 cycles of issue.
6. **After these, the fixed per-phase fill of the compute chain binds** (about 125 µs of 231 µs). The next levers are fewer serial phases per layer and shorter pipelines, not more MACs. This matches W8's finding of about 530 fill cycles per layer against a 229-cycle read floor.

## Calibration and limits

Calibrated 2026-09-29:
- **Element fill:** 78 cycles, measured by W2's QE ROM/MAC exact bench (the formula gave 45–60).
- **Long-crossing wire:** 0.76 ps/µm, from W3's real-technology channel runs (0.72–0.81 under load). The fit's 0.60 is unloaded.
- **GPU grid sync:** 1.77 µs, measured on a V100 (L. Zhang et al., "A Study of Single and Multi-device Synchronization Methods in Nvidia GPUs", IPDPS 2020, Fig. 5).
- **Still ASSUMED:** the 200-cycle hardware barrier.

- Calibrated against measurements: the as-built engines, the index reader's sector rate, the attention and softmax jobs, and the collective cycles.
- Not yet calibrated against a routed element:
  - the element fill (55 cycles, from the weight-tile formula);
  - the return fan-in (8, ASSUMED);
  - the burst factor of 4 on column return (ASSUMED).
- One die's layer set: the busiest die (13,798 macros) is used for every layer.
- MTP verify, batch occupancy and power are not yet in this model. The architecture budget still carries them.

## Qwen3-8B ROM die (`--qwen`, `results/uarch/qwen_rom.json`)

The Qwen element is already weight-stationary: a group owns its ROM column and 16 lanes, and W5's tile holds 4 groups. The architecture replay (`arch_budget_qwen3.as_built`, RTL-calibrated) has single-cycle wires. The model adds W5's floorplan wire terms:
- **x broadcast:** 25 register stages versus the RTL's 1.
- **VM conflict register:** +1 cycle.
- **Result write:** +2 cycles.
- **Split-tree compaction:** +1,728 cycles per token.
- **UCIe crossings:** +1,898 cycles per token.

It also checks tile area against the 560 mm² tile array. The area model is calibrated to W5's two tile variants: pruned (without the unreachable post-scale multipliers and tree registers) at 18,063 µm² per group, and unpruned at 26,250.

| Design (8K context, one die of the TP-2 pair) | tok/s | Array need / 560 mm² |
|---|---:|---|
| As built (scalar stream unit, no wire registers) | 179 | 682 (no fit) |
| Architecture (G = 6,144, stream unit 1,024 wide, ideal wires) | 11,193 | 682 (no fit) |
| + floorplan wires | 9,968 | 682 (no fit) |
| + pruned logic | 9,968 | 583 (**no fit**) |
| **G = 5,120, pruned, with wires** | **9,063** | **540 (fits)** |
| G = 4,096, pruned | 8,383 | 496 (fits) |

**Decisions:**
- The largest group count that fits with wires is **5,120 groups with pruned logic**, giving 9,063 tok/s.
- The published 10,874 assumes 6,144 groups, which do not fit, and free wires.
- Two area levers could restore 6,144 groups, and both must be priced:
  - scale-ROM remap (11.8 → 0.77 mm², W5);
  - a denser code macro, which the timing rejects today.

**Build requirements the RTL lacks:**
- the vector stream unit (the shipped scalar one deadlocks layer 0, W6);
- a group-offset slice parameter and pruning parameters in `ot_hdc_matvec`;
- a registered VM conflict stage.

## GPU-organised HBM comparators (`--hbm`, `results/uarch/hbm_gpu.json`)

At batch 1 an HBM die is bandwidth-bound, so the element count is sized to bandwidth: 32 SMs per Qwen die, 131k INT8 MAC/clk (W9). Three microarchitecture terms decide the token:
- **Weight-supply fraction.** Bandwidth × latency must be in flight: 1.8 MB per die. The measured ROM-style QE adapter keeps about 7 words in flight and delivers 39 of 3,482 B/cycle.
- **Global barriers.** Needed at every non-fusable dependent boundary on the critical path: 289 per Qwen die token, 629 per V4.1 token.
- **The architecture's TP and collective terms.**

| Design | tok/s |
|---|---:|
| Qwen HBM ideal (8.18 GB at 7.2 TB/s) | 880 |
| Qwen HBM, today's adapter | **10.5** |
| Qwen HBM, GPU bulk-copy supply, hardware barrier network (200 cycles, ASSUMED) | **841** |
| Qwen HBM, GPU grid sync (1.77 µs, V100 measured) | 607 |
| V4.1 HBM published (no barrier cost) | 3,579 |
| V4.1 HBM, today's adapter | **279** |
| V4.1 HBM, GPU supply + hardware barrier | **2,520** |
| V4.1 HBM, GPU grid sync (1.77 µs) | 718 |

**Decisions:**
1. The HBM weight path must be a GPU-style bulk-copy engine with at least 1.8 MB per die in flight. Today's adapter is 90× short of that.
2. The comparator needs a hardware barrier network. Grid sync through L2 (1.77 µs measured on V100) would cost V4.1 5.0× and Qwen 1.45×.
3. **The published V4.1 HBM figure of 3,579 omits synchronisation and must be restated.** A 200-cycle barrier gives 2,520; the barrier cost needs a cited or measured number.

## Summary: what the model changed

| Design | Previous figure | Microarchitecture model (fits die) | Largest lever |
|---|---:|---:|---|
| V4.1 ROM, 1M | 4,933 (architecture) | 4,336 | stripe rows over all macros; VM 64/128 ports; dedicated indexer, stream unit and reader at spec |
| Qwen ROM, 8K | 10,874 (published) | 9,063 | G = 5,120 pruned; wires +12%; vector stream unit |
| Qwen HBM, 8K | 881 | 841 | bulk-copy weight supply; hardware barrier |
| V4.1 HBM, 1M | 3,579 | 2,520 | synchronisation cost; bulk-copy supply |
