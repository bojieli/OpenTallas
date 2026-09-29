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
| Striped whole rows, VM 64/128, BF16 lanes on 2,048 macros | 3,937 | whole-row reads (a BF16 row at K = 5,120 is 320 words in one macro) and expert tile collisions | yes: 104.8 mm² |
| **Proposal:** the same with each row's K split over macros in golden-aligned chunk runs, FP32 adders in the return tree | **4,167** | fixed per-phase fill (compute chain), index scan | **yes**: 117.8 of 132 mm² strip, 51.8 of 233.7 mm² hub |
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
   - Whole-row ownership gives 3,937 tok/s. Splitting each row's K over up to 2^n macros, in power-of-two-aligned runs of golden chunks, gives 4,172 tok/s (both at 2,048 BF16 macros). That split is exact under the golden `csum` padded tree, with the partials added in the return tree in the same order.
   - It costs log2(split) FP32 adder levels (5 cycles each) and about 2.7 mm² of adders, and it also removes the routing-dependent collision variance.
   - **W10 interim corrections (all now in the model):**
     - Segments are golden-aligned: next_pow2(ceil(C/s)) chunks, not K/s.
     - The split is chosen per expert so that one expert covers the field. There are then no tile collisions, so the 6 active experts share every macro.
     - a_proj mixes FP8 rows with BF16 rows (index weights_proj, compressor wkv/wgate). It runs as two sub-phases, with x streamed twice.
     - A chain-recurrence floor applies: 8 sequential adds × latency 5 = 40 cycles per stream round.
     - Each row has ceil(C/c) segments, which is fewer than s when C is not a power of two. FP4 segments are whole chunk pairs, since an FP4 word carries block b of two sibling chunks. FP8 and FP4 matrices share one x stream. With these, W10's bank map matches the model's issue on every phase where read or x binds, and is below it elsewhere (verdict PASS_issue_match_t_read_below_model).
     - A BF16 element completes 16 chunk sums per cycle, so it needs a 15-adder tree and 128 chain registers. At 4,096 BF16 macros this breaks the fit (148.7 mm²).
3. **The element is one ROM macro, 2 FP4 block-dot lanes (64 MACs), a 274-bit capture register and 8 FP32 chunk partials.** BF16 lanes (16, plus a 15-adder chain tree) go on **2,048** macros: 4,172 tok/s at 117.8 mm². 2,560 gains 0.3%, and 3,072 does not fit.
4. **VM ports: 64 FP32 elements/cycle read (the x broadcast leaves as FP8, 512 bits) and 128 elements/cycle write.**
   - These are up from 4 read and 64 write.
   - This is a banked-VM design task: 8 + 16 banks of 256-bit SRAM.
5. **Dedicated units must be built at the spec widths; this is the largest remaining gap to the as-built RTL.**
   - **Indexer:** 248,832 FP4 MACs against 1,024 built (243×).
   - **Index reader:** at the HBM rate of 3,482 B/cycle against 1,920 measured.
   - **Stream unit:** 1,024 linear and 256 SFU lanes against 16/8.
   - **Attention probability loader:** the measured 609-cycle job against 141 cycles of issue.
6. **After these, the fixed per-phase fill of the compute chain binds** (about 125 µs of 240 µs). The next levers are fewer serial phases per layer and shorter pipelines, not more MACs. This matches W8's finding of about 530 fill cycles per layer against a 229-cycle read floor.

## Power ledger (V4.1 ROM busiest die, `power` in each row of `results/uarch/v41_rom.json`)

Dynamic energy per token is summed from every priced node's work:
- MACs by format;
- ROM bytes;
- x read from the VM, broadcast over the field (wire), and delivered into each holding element;
- partial-sum return (wire) and result write into the VM;
- stream-unit and SFU element ops;
- the on-die share of HBM traffic (PHY and controller, 0.8 pJ/bit; the DRAM energy dissipates in the stack);
- collective link bits.

Clock and leakage come from the area ledger by class (logic, ROM, SRAM), plus HBM interface idle power. Constants are from `configs/hardware/technology.json`. Wire energy is 0.1 pJ/bit/mm (ASSUMED), with 0.4 as a sensitivity.

Proposal at 1M context, busiest die = stage 14 (the layer-20 index scan):

| | W |
|---|---:|
| Clock | 18.1 |
| Leakage | 18.8 |
| HBM interface idle | 11.2 |
| Dynamic, single user (4,167 tok/s) | 1.5 |
| Dynamic, saturated (stage occupancy bound, 77k tok/s) | 28.0 |
| **Total, single user** | **49.6** |
| **Total, saturated** | **76.0** (112.2 at 0.4 pJ/bit/mm wire) |
| Liquid cooling limit | 474.56 |
| HBM stack energy at saturation (dissipated in the stacks, not the die) | 136.5 |

- **Power does not bind the V4.1 ROM die.** Energy per token on the busiest die is 363 µJ on-die plus 1,772 µJ in the stacks, dominated by index-key reads.
- The architecture model's 396.6 W hottest die sizes static power from the analytical logic area, and includes MTP and 1,024-user batches. This ledger does not yet model MTP.

## Calibration and limits

Calibrated 2026-09-29:
- **Element fill:** 78 cycles, measured by W2's QE ROM/MAC exact bench (the formula gave 45–60).
- **Long-crossing wire:** 0.76 ps/µm, from W3's real-technology channel runs (0.72–0.81 under load). The fit's 0.60 is unloaded.
- **GPU grid sync:** 1.43 µs, measured on a V100 with 1 block/SM and 32 threads (L. Zhang et al., "A Study of Single and Multi-device Synchronization Methods in Nvidia GPUs", IPDPS 2020, Fig. 5). Sensitivities: 2.21 µs on V100 at 1,024 threads, 1.77 µs on P100. The earlier 1.77 µs "V100" was the P100 figure.
- **Hardware barrier:** 30 cycles (Qwen die) and 40 cycles (V4.1 die) from last arrival to every SM released. Derived from the floorplan's wire stages and measured in RTL (`results/rtl/gpu_supply_barrier.json`). This replaces the ASSUMED 200. Reference: H800 SM-to-SM DSMEM latency is 181–213 cycles (Luo et al., arXiv 2501.12084, §7.1).

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
| G = 5,120, pruned, with wires (integer banks: 14 per column, 28 macros per tile; 10 port tiles) | 9,063 | 566.4 / 566.2 (**misses by 0.2**) |
| G = 4,096, pruned | 8,383 | 496 (fits) |

**Decisions:**
- **User decision, 2026-09-29: the Qwen ROM die is AR only**, so the DFlash drafter is not in ROM.
- With target-only banks (10 per column at G = 6,144; W12's integer placement: 34,669 macros, 265.0 mm²), **G = 6,144 pruned fits**: 552.9 / 560 mm², 9,968 tok/s. The scale-ROM remap adds about 11 mm² of margin.
- The hardened tile area decides. If the margin is under 2%, fall back to G = 5,632 pruned (533.9 / 560 mm², 9,496 tok/s).

**Build requirements the RTL lacks:**
- the vector stream unit (the shipped scalar one deadlocks layer 0, W6);
- a group-offset slice parameter and pruning parameters in `ot_hdc_matvec`;
- a registered VM conflict stage.

## GPU-organised HBM comparators (`--hbm`, `results/uarch/hbm_gpu.json`)

Both HBM dies replicate a GPU organisation (AGENTS.md rule 3). `hbm_gpu_design()` sizes the element and its networks, and the RTL (`rtl/gpu/`) and floorplans (`results/floorplan/hbm_gpu/`) measure them.

### The SM element

The SM has four sub-partitions of an exact Tensor-Core-style MMA:
- **Lanes.** Each lane is the ROM lane's exact datapath: a BF16 × BF16 → FP32 product feeding a circulating FP32 RNE adder that holds 8 slots.
- **Chunk-to-lane mapping.** Lane j of the SM holds golden chunk g·L + j of its row.
- **Trees.** A fixed pairwise FP32 tree per column (32 leaves in a sub-partition, then 4 across the SM) is the bottom of the golden tree. A streaming pairwise stack continues it over the row's groups, with the golden's +0 padding.
- **Row placement.** A row's whole K and its whole tree stay inside one SM.

| | Qwen3-8B die | DeepSeek-V4.1 die |
|---|---|---|
| Lanes | 128 INT8 (decoded exactly to BF16) | 8 block-dot (k32 FP8/FP4, exact, one rounding) + 64 BF16 |
| Columns | 16 (DFlash block 16, batch ≤ 16) | 16 (MTP m + 1 = 7, batch ≤ 16) |
| MAC/clk per SM | 2,048 | 5,120 |
| Weight ingest | 128 B/clk | 128 B/clk |
| SMEM | 512 KB x store (16 × 32 KB macros, read one fragment per slot revolution) + 128 KB staging + 64 KB scratch | x store 99 × 4 KB macros (a new fragment of up to 8 columns every cycle for group-slot issue) + 128 KB staging + 64 KB scratch |
| Area (logic at 50% density + SRAM) | 4.71 mm² | 3.64 mm² |
| Measured drain (last weight line → last row result) | 65 cycles | 70 cycles |

**Exactness (Icarus, every output bit against the golden):**
- `results/rtl/gpu_sm_exact.json`: 12/12 cases.
  - Qwen INT8 on 128 lanes: split = K (a pure tree), kc = 3, 4 and 32, split < lanes, and stream underflow. The golden is `hdc_golden.matvec`, then the BF16 row scale.
  - V4.1 BF16 chunk-8 `csum` on 64 lanes: K = 512, 1,004 (tail and padding) and 5,120.
  - Group-slot issue: 1-, 2- and 3-row slices (BF16 K = 5,120 and 1,004, Qwen INT8 K = 2,048).
- `results/rtl/gpu_sm_blockdot_exact.json`: 8/8 cases.
  - V4.1 `linear_q` FP4 at K = 2,304 and 5,120.
  - V4.1 `linear_q` FP8 at K = 544, 1,280 and 5,120.
  - Group-slot issue on 1–3-row slices (FP8 K = 5,120 and 2,048, FP4 K = 5,120).

**Group-slot issue** (`op_gs` in `rtl/gpu/ot_gpu_issue.sv`) puts consecutive (row, group) items on the 8 accumulator slots instead of 8 rows.
- Why it is needed: on a 1/96 row slice, row-slot issue walks a row's groups one after another, which makes the op a K-chain.
- What changes:
  - The partials leave the column trees in group order on consecutive cycles.
  - The stack is keyed by row mod 8.
  - The golden order is unchanged, so the result is exact by construction (and checked above).
- Measured: an FP8 K = 5,120 single-row op takes 117 cycles, against 689 for 9 rows issued row-slot.
- Cost: the x store must deliver a new fragment every cycle. Sized for 8 columns, that is 99 shallow macros (0.5 mm² per SM, +0.1 mm² over row-slot).

### Count, supply and barrier

| Term | Qwen die | V4.1 die | Basis |
|---|---|---|---|
| SM count | 32 (minimum 28) | 32 | Smallest count within 0.5% of an unbounded array (fluid model), rounded to 8 per HBM stack quadrant |
| Bulk copy in flight | 512 lines of 128 B per SM | same | Little's law gives 440. Measured in RTL, 512 reaches the SM's full share (102.5 of 102.4 B/clk) under ±50 ns jitter; 7 outstanding gives 1.6 B/clk |
| SMEM staging | 128 KB/SM | 128 KB/SM | The fluid model's knee: 64 KB loses 0.7% on Qwen |
| Global barriers per token | 181 | 329 | One per matrix op and one per attention layer (V4.1 also one per index top-k and one for the argmax). Heads are SM-local; norms and the router top-6 run redundantly on the replicated x. The earlier 289 and 629 counted those |
| Barrier round trip | 30 cycles | 40 cycles | Floorplan: leaf 4.3 mm / trunk 6.8 mm (Qwen), 3.9 / 11.8 mm (V4.1). RTL bench: 32 SMs at 8 × 4 fan-in |
| Boundary cost | 46 cycles | 56 cycles | Round trip plus the x-broadcast tail |
| L2 | 4 slices × 2 MB | same | Holds x and result gather, TP staging and KV-write coalescing. Weights bypass L2: each SM's rows live in its own quadrant's stack |

### Token

The bulk copy prefetches the static weight stream through every boundary. A boundary is therefore exposed only when the SMEM staging cannot hide it (`stream_overlap`). The additive form (t_hbm + boundaries × barrier + tp) is kept as labelled no-prefetch rows.

| Design | tok/s |
|---|---:|
| Qwen HBM ideal (bandwidth only) | 880.7 |
| **Qwen HBM, GPU die (prefetching bulk copy, measured barrier)** | **880.6** (112 cycles exposed per token) |
| Qwen HBM, same, no prefetch | 873.8 |
| Qwen HBM, ASSUMED 200-cycle barrier, no prefetch | 854.9 |
| Qwen HBM, V100 grid sync 1.43 µs, with prefetch / without | 758.5 / 716.6 |
| Qwen HBM, today's adapter | 10.5 |
| **V4.1 HBM, GPU die, K-chain-aware, group-slot issue (adopted)** | **2,981** |
| V4.1 HBM, same, row-slot issue (sensitivity) | 2,578 |
| V4.1 HBM, group-slot, V100 grid sync | 1,269 |
| V4.1 HBM published (additive, pooled widths, no barrier) | 3,579 |
| V4.1 HBM, pooled-width chain with prefetch (superseded upper bound) | 3,882 |

**How the V4.1 chain is priced** (`v41_hbm_chain`):
- It walks the arch DAG's critical path at 1M.
- Each matvec is an SM op on its 1/96 row slice (`sm_op_cycles`, calibrated on the RTL SM).
- The dedicated units' nodes are at their arch price (W11 spec widths).
- Barriers are at 56 cycles.
- The comparator's switched-fabric terms are 125.9 + 1.5 + 0.9 + 2.0 µs.
- The weight sweep (37.4 µs) streams under the chain.

Group-slot breakdown: SM matvecs 66.9 µs (row-slot: 119.3), dedicated units and stream unit 120.4, barriers 17.8, fabric 130.3.

### Speculation on the SM design (`speculation` in the record): MODEL ONLY

Verify positions ride the MMA columns: 16 are built, one weight fetch serves the whole block, and each column keeps its own golden order.

| Design | tau | tok/s | Speedup |
|---|---:|---:|---:|
| Qwen HBM AR | 1 | 880.6 | 1.0× |
| Qwen HBM DFlash, block 5 | 2.859 | 2,089 | 2.37× |
| **Qwen HBM DFlash, block 16** (best; step cost is flat up to 16 columns) | 3.656 | **2,671** | **3.03×** |
| V4.1 HBM AR (group-slot) | 1 | 2,981 | 1.0× |
| **V4.1 HBM DSpark MTP, γ = 5, 6 positions** | 3.649 | **6,106** | **2.05×** |

- **Qwen:** a step streams the target's bytes plus the drafter's 1.05 B parameters (INT8, ASSUMED) and a re-read of the shared lm_head over the draft slots. tau is measured per block (`results/speculative/dflash_block_acceptance.json`).
- **V4.1:** verify runs the matvecs once, on the columns. The dedicated units issue every position's work, which adds 229 µs. Collective bytes scale with positions. The draft is 3/40 of an AR token (ASSUMED, as in the ROM rows).
- **RTL (user rule: build only if easy; root decision 2026-09-29): the speculation figures are model-only.** The column-parallel verify is built and exact per column. The other parts need units that are not easy for this workstream, so they were not built, and the token-level greedy check waits for a whole-die HBM RTL:
  - causal attention inside the verify block: the Qwen die's attention is not in the SM RTL, and V4.1 attention is W11's unit;
  - the KV commit and rollback pointer;
  - a token-level check against greedy non-speculative tokens, which needs a whole-die HBM RTL that does not exist.

**Decisions:**
1. **The weight path is a TMA-style bulk-copy engine** (`rtl/gpu/ot_gpu_bulk_copy.sv`): 512 outstanding 128-B lines and a 128 KB staging ring per SM. Today's adapter is 64× short in flight.
2. **A hardware barrier network**, a sense-reversing toggle tree with one register per node (`ot_gpu_barrier_node`), costs 30–40 cycles. Grid sync through L2 would cost Qwen 14% and V4.1 2.8×.
3. **The Qwen HBM die is bandwidth-bound at 880.6 tok/s.** The barrier and SM terms are hidden under the stream.
4. **The floorplans fit** (`results/floorplan/hbm_gpu/*.json`, legal, macro-placed SRAMs, 4 PHYs on 48 mm of the long edges):
   - Qwen: 160 of 688 mm² core used (SM array 155.6, L2 5.0).
   - V4.1: 240 mm², including the 112.7 mm² dedicated-unit hub between the SM half-arrays.
5. **V4.1 SMs issue group-slot on small slices.** This takes the HBM token from 2,578 to 2,981 tok/s for about 3 mm² of x-store SRAM per die.

## Summary: what the model changed

| Design | Previous figure | Microarchitecture model (fits die) | Largest lever |
|---|---:|---:|---|
| V4.1 ROM, 1M | 4,933 (architecture) | 4,167 | stripe rows over all macros; VM 64/128 ports; dedicated indexer, stream unit and reader at spec |
| Qwen ROM, 8K | 10,874 (published) | 9,968 | AR only (no drafter ROM) lets G = 6,144 pruned fit; wires +12%; vector stream unit |
| Qwen HBM, 8K | 881 | 880.6 (DFlash b16 2,671) | bulk-copy weight supply prefetching through boundaries; hardware barrier (30 cycles) |
| V4.1 HBM, 1M | 3,579 | 2,981 (MTP 6,106) | SM op latency on 1/96 row slices (group-slot issue); hardware barrier (40 cycles); bulk-copy supply |

## Speculation (`--spec`, `results/uarch/speculation.json`)

The lane multiplier m counts the positions that multiply one ROM weight word in the same cycle.
- **m = 1 (time-multiplexed):** issue time multiplies by the positions. Fill, wire stages and dependency latency are paid once per verify pass, so there are no new lanes.
- **m ≥ 2:** replicates every element's lanes beside its macro, plus wider broadcast and return.

| Design | Verify / AR time | tok/s | Speedup | Extra lane area | Decision (user, 2026-09-29) |
|---|---:|---:|---:|---:|---|
| V4.1 ROM MTP, 6 positions, m = 1 | 2.43× | **6,063** | **1.46×** | 0 | **adopted** |
| V4.1 ROM MTP, m = 2 | 1.99× | 7,366 | 1.77× | 86.0 mm² (does not fit) | rejected |
| V4.1 ROM MTP, m = 6 | 1.73× | 8,447 | 2.03× | 429.9 mm² | rejected |
| Qwen ROM DFlash, m = 1 (best block = 1, i.e. AR) | — | 9,017 | 1.0× | 0 (+29 mm² drafter ROM) | **AR only** |
| Qwen ROM DFlash, m = 5, block 5 | — | 18,720 | 2.08× | 178.7 mm² | rejected: does not fit |

**Why the two ROM designs differ:**
- **V4.1 tokens are latency-bound.** Fill is about half the token, so 6 positions share the expensive part.
- **Qwen tokens are lane-bound.** Each extra position costs a whole weight sweep, and only 1.7–3.7 tokens are accepted.

Removing the drafter frees about 12% of Qwen code ROM. Target-only banks are 10 per column at G = 6,144, and **G = 6,144 pruned then fits** (552.9 / 560 mm², 9,968 tok/s). The scale-ROM remap adds about 11 mm² of margin.

The V4.1 draft cost is ASSUMED at 3/40 of an AR token (3 draft blocks of 40 layers). The HBM comparators' DFlash and MTP rows come from W13's SM model.
