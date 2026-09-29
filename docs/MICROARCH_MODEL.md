# Microarchitecture analytical model

Tool: `tools/uarch_model.py`. Records: `results/uarch/v41_rom.json`, `results/uarch/qwen_rom.json`, `results/uarch/hbm_gpu.json`, `results/uarch/economics.json`. Tests: `tests/test_uarch_model.py`, `tests/test_uarch_economics.py`. The binding method is in [AGENTS.md](../AGENTS.md) rule 1.

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
| Columns | 16 (DFlash block 16, batch ≤ 16) | 8 (MTP m + 1 = 7 positions; batch > 8 runs a second pass) |
| MAC/clk per SM | 2,048 | 2,560 |
| Weight ingest | 128 B/clk | 128 B/clk |
| SMEM | 512 KB x store (16 × 32 KB macros, one fragment per slot revolution into a double-buffered register) + 128 KB staging ring + 64 KB scratch | x store 99 × 4 KB macros (a whole 8-column fragment every cycle, for group-slot issue) + 128 KB staging ring + 64 KB scratch |
| Area (logic at 50% density + SRAM) | 4.71 mm² | 2.27 mm² |
| Measured drain (last weight line → last row result) | 66 cycles | 70 cycles |

**Exactness (Icarus, every output bit against the golden):**
- `results/rtl/gpu_sm_exact.json`: 15/15 cases.
  - Qwen INT8 on 128 lanes: split = K (a pure tree), kc = 3, 4 and 32, split < lanes, and stream underflow. The golden is `hdc_golden.matvec`, then the BF16 row scale.
  - V4.1 BF16 chunk-8 `csum` on 64 lanes: K = 512, 1,004 (tail and padding) and 5,120.
  - Group-slot issue: 1-, 2- and 3-row slices (BF16 K = 5,120 and 1,004, Qwen INT8 K = 2,048).
  - The Qwen SM macro top `ot_gpu_sm_q` (3 cases): weights through its own bulk copy and SRAM staging ring from an out-of-order HBM model, x from its SRAM x store.
- `results/rtl/gpu_sm_blockdot_exact.json`: 12/12 cases.
  - V4.1 `linear_q` FP4 at K = 2,304 and 5,120.
  - V4.1 `linear_q` FP8 at K = 544, 1,280 and 5,120.
  - Group-slot issue on 1–3-row slices (FP8 K = 5,120 and 2,048, FP4 K = 5,120).
  - The V4.1 SM macro top `ot_gpu_sm_v` (4 cases): packed 136-B lines (FP4, FP8, BF16) through its bulk copy, per-cycle SRAM x store.

**Group-slot issue** (`op_gs` in `rtl/gpu/ot_gpu_issue.sv`) puts consecutive (row, group) items on the 8 accumulator slots instead of 8 rows.
- Why it is needed: on a 1/96 row slice, row-slot issue walks a row's groups one after another, which makes the op a K-chain.
- What changes:
  - The partials leave the column trees in group order on consecutive cycles.
  - The stack is keyed by row mod 8.
  - The golden order is unchanged, so the result is exact by construction (and checked above).
- Measured: an FP8 K = 5,120 single-row op takes 117 cycles, against 689 for 9 rows issued row-slot.
- Cost: the x store must deliver a new fragment every cycle. Sized for the 8 columns, that is 99 shallow 128 × 256 macros (0.5 mm² per SM).

### Count, supply and barrier

| Term | Qwen die | V4.1 die | Basis |
|---|---|---|---|
| SM count | 32 (minimum 28) | 32 | Smallest count within 0.5% of an unbounded array (fluid model), rounded to 8 per HBM stack quadrant |
| Bulk copy in flight | 512 lines of 128 B per SM | same | Little's law gives 440. Measured in RTL, 512 reaches the SM's full share (102.5 of 102.4 B/clk) under ±50 ns jitter; 7 outstanding gives 1.6 B/clk |
| SMEM staging | 128 KB/SM | 128 KB/SM | The fluid model's knee: 64 KB loses 0.7% on Qwen |
| Global barriers per token | 181 | 329 | One per matrix op and one per attention layer (V4.1 also one per index top-k and one for the argmax). Heads are SM-local; norms and the router top-6 run redundantly on the replicated x. The earlier 289 and 629 counted those |
| Barrier round trip | 30 cycles | 38 cycles | Floorplan: leaf 4.3 mm / trunk 6.8 mm (Qwen), 3.5 / 11.4 mm (V4.1). RTL bench: 32 SMs at 8 × 4 fan-in |
| Boundary cost | 46 cycles | 54 cycles | Round trip plus the x-broadcast tail |
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
| **V4.1 HBM, GPU die, K-chain-aware, group-slot issue (adopted)** | **2,920** |
| V4.1 HBM, same, row-slot issue (sensitivity) | 2,533 |
| V4.1 HBM, group-slot, V100 grid sync | 1,257 |
| V4.1 HBM published (additive, pooled widths, no barrier) | 3,579 |
| V4.1 HBM, pooled-width chain with prefetch (superseded upper bound) | 3,882 |

**How the V4.1 chain is priced** (`v41_hbm_chain`):
- It walks the arch DAG's critical path at 1M.
- Each matvec is an SM op on its 1/96 row slice (`sm_op_cycles`, calibrated on the RTL SM).
- The dedicated units' nodes are at their arch price (W11 spec widths).
- Barriers are at 54 cycles.
- Every SM needs the whole x after each collective: the die's 256 B/cycle x broadcast fills the 32 x stores (K × positions × 2 B / 256 cycles per matvec).
- The comparator's switched-fabric terms are 125.9 + 1.5 + 0.9 + 2.0 µs.
- The weight sweep (37.4 µs) streams under the chain.

Group-slot breakdown: SM matvecs 66.9 µs (row-slot: 119.3), x-broadcast fill 7.6, dedicated units and stream unit 120.4, barriers 17.3, fabric 130.3.

### Speculation on the SM design (`speculation` in the record): MODEL ONLY

Verify positions ride the MMA columns: 16 are built, one weight fetch serves the whole block, and each column keeps its own golden order.

| Design | tau | tok/s | Speedup |
|---|---:|---:|---:|
| Qwen HBM AR | 1 | 880.6 | 1.0× |
| Qwen HBM DFlash, block 5 | 2.859 | 2,089 | 2.37× |
| **Qwen HBM DFlash, block 16** (best; step cost is flat up to 16 columns) | 3.656 | **2,671** | **3.03×** |
| V4.1 HBM AR (group-slot) | 1 | 2,920 | 1.0× |
| **V4.1 HBM DSpark MTP, γ = 5, 6 positions** | 3.649 | **5,673** | **1.94×** |

- **Qwen:** a step streams the target's bytes plus the drafter's 1.05 B parameters (INT8, ASSUMED) and a re-read of the shared lm_head over the draft slots. tau is measured per block (`results/speculative/dflash_block_acceptance.json`).
- **V4.1:** verify runs the matvecs once, on the columns. The dedicated units issue every position's work, which adds 229 µs. Collective bytes and the x-broadcast fill scale with positions. The draft is 3/40 of an AR token (ASSUMED, as in the ROM rows).
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
   - V4.1: 196 mm², including the 112.7 mm² dedicated-unit hub between the SM half-arrays.
5. **V4.1 SMs issue group-slot on small slices.** This takes the HBM token from 2,533 to 2,920 tok/s. The x store that delivers a whole 8-column fragment every cycle is 99 shallow macros per SM.

## Summary: what the model changed

| Design | Previous figure | Microarchitecture model (fits die) | Largest lever |
|---|---:|---:|---|
| V4.1 ROM, 1M | 4,933 (architecture) | 4,167 | stripe rows over all macros; VM 64/128 ports; dedicated indexer, stream unit and reader at spec |
| Qwen ROM, 8K | 10,874 (published) | 9,968 | AR only (no drafter ROM) lets G = 6,144 pruned fit; wires +12%; vector stream unit |
| Qwen HBM, 8K | 881 | 880.6 (DFlash b16 2,671) | bulk-copy weight supply prefetching through boundaries; hardware barrier (30 cycles) |
| V4.1 HBM, 1M | 3,579 | 2,920 (MTP 5,673) | SM op latency on 1/96 row slices (group-slot issue); hardware barrier (40 cycles); bulk-copy supply |

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

## Fabric sensitivity and GPU tiers (`--fabric`, `results/uarch/fabric.json`)

Every multi-die design here assumes deterministic hardware collectives at link latency:
- **V4.1 ROM array:** direct UCIe/board links inside its TP-4 groups (the architecture prices 145–165 cycles, about 0.15 µs).
- **V4.1 HBM comparator:** TP-96 through an NVL-class switch (0.668 µs).
- **Qwen pair:** 73 UCIe exchanges per token (about 17.5 ns each).

### Collective latency sweep (tok/s, single user, 1M context for V4.1, 8K for Qwen)

| Collective / exchange latency | V4.1 ROM (AR) | V4.1 HBM (GPU org., AR) | Qwen ROM (AR, G = 6,144) | Qwen HBM (AR) |
|---|---:|---:|---:|---:|
| own baseline | **4,167** (~0.15 µs links) | **2,920** (0.668 µs switch) | **9,968** (17.5 ns UCIe) | **881** |
| 0.1–0.15 µs | 3,752 | 4,084 | 9,404 | 876 |
| 0.5–0.668 µs | 2,785 | 2,920 | 7,378 | 854 |
| 1 µs | 2,390 | 2,469 | 5,813 | 828 |
| 5 µs | 881 | 863 | 2,155 | 667 |
| 10 µs | 493 | 476 | — | — |

**At equal collective latency, V4.1 ROM and V4.1 HBM have almost the same single-user speed.** Both are latency-bound, not bandwidth-bound.
- The ROM array's advantage (4,167 against 2,920) is structural. Its weights are local, so small TP-4 groups on direct links suffice.
- The HBM machine must spread every matrix over 96 dies to reach its bandwidth, which needs a switched fabric.
- Qwen ROM stays about 11× faster than Qwen HBM at every latency, because the Qwen HBM machine is bandwidth-bound.
- Every headline depends strongly on deterministic hardware collectives. At NCCL-class latency (5–10 µs) both V4.1 designs fall to 500–900 tok/s.

### GPU tiers

Tier 1 is measured. Tier 2 is a projection calibrated on B200 measurements. Tier 3 is the idealised HBM machine with OpenTallas control.

| Tier | Design | tok/s AR | with speculation |
|---|---|---:|---:|
| 1 | Qwen3-8B-class, H200 NIM FP8 | 235 | — |
| 1 | Qwen3-8B, RTX PRO 6000 (this lab), FP8 | 151 | 390 (DFlash, τ 3.72, reasoning mix) |
| 1 | Qwen3-8B, 1× B200, SGLang FA4, BF16 (DFlash paper, Table 3) | 230 | **1,175** Math500 (τ 8.01, 5.1×) / 955 HumanEval (τ 6.50, 4.2×) |
| 1 | DeepSeek-R1 (V4.1-class anchor), 8× B200, TensorRT-LLM min-latency | — | 368 (3 MTP layers, relaxed acceptance) |
| 2 | Qwen3-8B, 1× B200, FP8, 8K (per-byte cost fitted to the B200 BF16 230; H200 fixed cost) | 331 | 853 (reasoning mix) / 1,390–1,690 (math/code τ 6.5–8.0) |
| 2 | DeepSeek-V4.1-Flash, 8× B200 (+ NCCL-class 8 µs all-reduce, ASSUMED) | 278 | 539 |
| 3 | Qwen HBM, idealised | 881 | 2,671 (τ 3.66) / 4,749 (τ 6.50) / 5,852 (τ 8.01) |
| 3 | V4.1 HBM, idealised | 2,920 | 5,673 |

**Acceptance is strongly workload-dependent.** Every speculative row must name its τ and workload:
- DFlash τ is 6.5–8.0 on math and code with thinking disabled (paper).
- It is 3.66 on this lab's reasoning mix of 264 turns.

**Tier 2 matches tier 1 in order of magnitude.** V4.1 on 8× B200 projects 539 with MTP against DeepSeek-R1's measured 368, a larger model with lossy acceptance.

**Against the best measured GPU result,** Qwen ROM AR (9,968) is 8.5× B200 DFlash on Math500 (1,175) and 43× B200 AR (230).

Against GPUs (tier 2), the ROM designs are:
- **Qwen:** about 30× in AR; 6–12× against GPU DFlash, depending on τ.
- **V4.1:** about 15× in AR and 11× with MTP.

Against the idealised HBM control (tier 3), the V4.1 ROM advantage is 1.4× in AR and about 1.07× with MTP, and it is structural (small TP groups on direct links).

## Economics: batch, energy, cost (`--economics`, `results/uarch/economics.json`)

User positioning (2026-09-29): the paper claims single-user speed against GPUs (tier 1 measured, tier 2 calibrated), makes energy per token and cost first-class, and reports aggregate throughput under batching. The idealised HBM machine (tier 3) is the architectural control. This section prices every design on those three axes. It calls the sections above and changes none of them. The record pins the sha256 of every source it reads. Test: `tests/test_uarch_economics.py`.

### How each design batches

- **V4.1 ROM array:** users fill the 28 pipeline stages.
  - The per-user rate stays at the single-user rate until the busiest stage is full. That stage's occupancy is the sum of its nodes' issue on one die, the same basis as the power ledger: 77,022 tok/s.
  - Capacity is 866 users at 1M (`arch_budget_v41` capacity, the layer-20 group's KV and index keys in 4 HBM3E stacks per die). The RTL key layout holds 551 (`results/arch/v41_hbm_region_preflight.json`, status `capacity_mismatch`).
  - MTP m = 1 re-issues all 6 positions on the same lanes. It raises the single-user rate but lowers the saturated aggregate (50,708 against 77,022). The draft is charged to the head dies.
- **Qwen ROM package:** m = 1, so batching reuses no weight word. The lanes (ME busy 54,432 of 110,219 cycles per die, from the calibrated replay's `unit_busy`), the stream unit and the KV stream each cap the aggregate:

  | Bound | Aggregate tok/s |
  |---|---:|
  | Lanes | 20,184 |
  | Stream unit | 101,641 |
  | **KV stream** (8 stacks at 0.9 TB/s; 604 MB of 8K FP8 KV per user-token) | **11,921** |

  **The KV stream binds from batch 2, not the lanes.** `arch_budget_qwen3.batch_model` gives the same 11,921.
- **HBM tier 3:** users ride the SM's MMA columns on one weight fetch (16 on the Qwen die, 8 on the V4.1 die). Beyond the columns, the weights are streamed again.
  - Qwen DFlash shares the columns between users and block positions, and takes the best block at each batch.
  - V4.1 at 8 users or fewer re-prices the W13 chain with that many columns; the dedicated-unit issue repeats per user.
  - Beyond 8 users, column passes interleave. The busiest of SM time, dedicated-unit issue and the weight sweep bounds each pass: 367 µs per 8-user pass (AR), 275 µs per 1-user MTP pass. Each pass's weight bytes are the union of its tokens' routed experts.
- **GPU tier 2:** the tier-2 step at batch 1, plus (B − 1) times a per-user increment.
  - A line fitted to the DFlash paper's B200 concurrency baselines (1/4/8/16/32 users: 230/861/1,666/3,133/5,694 tok/s) reproduces them within 3%. Its per-user increment is 38.5 µs.
  - At 8K the increment is one user's FP8 KV at the fitted B200 byte rate: 115 µs. The code takes the larger of the two, which is GPU-favourable because the paper's increment already contains its own shorter-context KV.
  - V4.1 on 8× B200 reads the routed-expert union and each user's index keys every step.
  - Capacity is 180 GB × 0.9 per GPU, less the weights.

### Batch, energy and capacity (8K Qwen, 1M V4.1)

| Design | tok/s, B = 1 | mJ/token, B = 1 | Saturated batch | Aggregate tok/s | Per-user tok/s | mJ/token, saturated | Users that fit |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen ROM AR (G = 6,144) | 9,968 | 86.4 | 2 | 11,921 | 5,960 | 84.7 | 268 |
| Qwen HBM tier 3, AR | 881 | 983 | 16 | 6,684 | 418 | 133 | 255 |
| Qwen HBM tier 3, DFlash | 2,671 | 358 | 8 | 7,101 | 888 | 129 | 255 |
| Qwen 1× B200, AR (tier 2) | 331 | 2,081 | 255 | 7,907 | 31.0 | 87.1 | 255 |
| V4.1 ROM, AR | 4,167 | 3,138 | 32 | 77,022 | 2,407 | 208 | 866 |
| V4.1 ROM, MTP m = 1 | 6,063 | 2,168 | 16 | 50,708 | 3,169 | 294 | 866 |
| V4.1 HBM tier 3, AR | 2,920 | 3,692 | 16 | 21,792 | 1,362 | 913 | 811 |
| V4.1 HBM tier 3, MTP | 5,673 | 2,287 | 4 | 12,122 | 3,030 | 1,676 | 811 |
| V4.1 8× B200, AR (tier 2) | 278 | 19,852 | 839 | 13,018 | 15.5 | 423 | 839 |

Per-batch rows (per-user rate, aggregate, per-user latency, energy, system power) are in the record. Measured anchors, at 689 W:
- B200 AR at 1 to 32 users: 2,996 to 121 mJ/token.
- B200 DFlash at batch 1: 586 mJ (Math500) and 722 mJ (HumanEval).
- DeepSeek-R1 on 8× B200: 14,978 mJ.

### Energy basis

- **V4.1 ROM:** the power ledger's terms (MACs by format, ROM words, x network, stream unit, the on-die HBM share, links), summed over every stage and multiplied by the 4 TP dies, plus the stacks' share of the index and KV reads.
  - Dynamic energy is 21.6 mJ on the dies and 19.3 mJ in the stacks per token.
  - Static power is 12.9 kW:
    - 112 layer dies at the ledger's ungated clock + leakage + HBM interface idle (48.1 W), plus the rack's always-on SerDes and UCIe (33.1 W);
    - head and Engram-table dies at the rack record's static.
  - **Static power dominates at every batch.** Stage clock gating is the energy lever.
- **Qwen ROM:** its own ledger with the same constants, both dies.
  - Dynamic energy is 76.2 mJ/token, of which 59.5 mJ is the HBM stack share of the KV read and 7.1 mJ its on-die share.
  - Static power is 101.5 W. The areas are the W12 ROM (265 mm²), the pruned group logic plus PHYs (173.8 mm²) and the KV ring (23.9 mm²).
- **HBM tier 3:** SM MACs; every weight and KV byte over the whole HBM path (104.9 pJ/B); SMEM staging write and read; stream elements; and, for V4.1, the dedicated units' energy per token taken from the ROM ledger and fabric bytes over two switch hops.
  - Static power per package: 69 W (Qwen); 6.5 kW for the 96 V4.1 dies.
  - The NVL-class switch is not charged.
- **GPU:** 689 W measured decode power per B200 (`technology.json` `power.gpu_reference_power`) × step time. The record also carries the rows at the 1,200 W TDP.
- MAC energy is 2 operations per MAC in this section, as in `technology.json` and `arch_budget_v41`. The V4.1 power ledger above charges 1 per MAC, which changes its busiest die by under 1%. The test checks that this section's ledger reproduces the power ledger's busiest stage when run at 1 operation per MAC.
- HBM background (refresh) power is not charged on any design.

### Cost

**The repository has no dollar model** (`docs/ANALYTICAL_REPORT.md`: "Mask cost and model churn are outside the model"). Every dollar figure below is ASSUMED.
- **Basis:**
  - **Iso-package.** Every two-reticle, 8-stack CoWoS-L-class package costs the repository's B200 device price, $25,000 (`configs/hardware/architectures.json`, graded assumed). That covers the ROM packages, the HBM comparator packages and a B200.
  - **ROM mask NRE,** amortised over the 1,000 production units of `technology_inputs.json`:
    - high case: a full 5 nm-class mask set per distinct ROM die, $15M (SemiAnalysis);
    - low case: the weight-coding (via/metal) layers only, ASSUMED 10% of a set.
  - Every V4.1 ROM die holds different weights, so there are 188 sets.
- **Component cross-check** (silicon at the wafer-device assumption of $2.16/mm², plus HBM3E at an ASSUMED $360 a stack; excludes packaging, test and margin):

  | Design | Silicon + stacks |
  |---|---:|
  | Qwen package | $6.4k |
  | V4.1 ROM array | $499k |
  | V4.1 HBM tier 3 | $307k |
  | 8× B200 | $51k |

| System | Packages | Dies | HBM stacks | ROM mask sets | Capex | $ per tok/s, B = 1 | $ per tok/s, saturated | $ per tok/s at ≥ 100 tok/s/user |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen ROM (AR, G = 6,144) | 1 | 2 | 8 | 2 | $28k–55k | 2.81–5.52 | 2.35–4.61 | 2.35–4.61 |
| Qwen HBM tier 3 (AR / DFlash) | 1 | 2 | 8 | 0 | $25k | 9.36 | 3.52 | 3.52 |
| Qwen 1× B200 (tier 2, AR) | 1 | 2 | 8 | 0 | $25k | 75.53 | 3.16 | 5.15 |
| V4.1 ROM array (AR / MTP m = 1) | 94 | 188 | 464 | 188 | $2.63M–5.17M | 434–853 | 34.2–67.1 | 34.2–67.1 |
| V4.1 HBM tier 3 (AR / MTP) | 48 | 96 | 384 | 0 | $1.20M | 212 | 55.1 | 55.1 |
| V4.1 8× B200 (tier 2, AR) | 8 | 16 | 64 | 0 | $200k | 720 | 15.4 | 51.4 |

Each system is costed at its best mode for each point: its fastest single-user mode at B = 1, and its largest aggregate within capacity when saturated. The ≥ 100 tok/s/user column is an ASSUMED illustrative interactivity floor.

### What the economics show

1. **Single-user speed is where ROM wins.**
   - At batch 1 the Qwen ROM package is 30× a B200 in tok/s, 24× in energy per token and 14–27× in $ per tok/s.
   - The V4.1 ROM array against 8× B200, both AR, is 15× in tok/s and 6.3× in energy per token. With MTP on both it is 11× in tok/s.
2. **Batching does not help the Qwen ROM package.** Its 8 HBM stacks must stream every user's 604 MB of 8K KV per token, so the aggregate saturates at 11,921 tok/s from batch 2. A B200, with the same 8 stacks, saturates at 7,907, and only at 31 tok/s per user. At saturation all three Qwen machines spend 85–133 mJ per token, dominated by the KV read. Cost per aggregate tok/s is then within 2× across them.
3. **V4.1 ROM has the largest aggregate** (77,022 tok/s against 21,792 for tier 3 and 13,018 for 8× B200) **and the lowest saturated energy** (208 mJ against 913 and 423).
   - Its capex is the highest: 94 packages plus 188 ROM mask sets, where the NRE is 0.3–2.8 M$ per system at 1,000 units.
   - Per aggregate tok/s it therefore costs 2–4× 8× B200 at saturation, where the GPU serves 15.5 tok/s per user.
   - At a ≥ 100 tok/s/user floor it is 0.7–1.3× the GPU.
4. **MTP m = 1 is a single-user lever on the ROM array.** It lowers the saturated aggregate by 34%. Run MTP only while the stages are not yet full (below about 12 users) and AR beyond.
5. **Static power sets the energy of both V4.1 designs.** V4.1 ROM runs at 3.1 J per token at batch 1 and 0.21 J saturated, against 19.9 and 0.42 J for 8× B200. Stage clock gating and SerDes idle states are the next energy levers.
