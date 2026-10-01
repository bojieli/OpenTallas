# Microarchitecture analytical model

Tool: `tools/uarch_model.py`. Records: `results/uarch/v41_rom.json`, `results/uarch/qwen_rom.json`, `results/uarch/hbm_gpu.json`, `results/uarch/economics.json`, `results/uarch/economics_levers.json`. Tests: `tests/test_uarch_model.py`, `tests/test_uarch_economics.py`. The binding method is in [AGENTS.md](../AGENTS.md) rule 1.

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
| Spec widths, rows striped over every macro | **2,094** | VM read port: 4 elements/cycle, so 1,280 cycles per 5,120-wide projection | **no**: 292.8 of 132 mm² of strip |
| + VM 64/128 elements, BF16 on every macro | 4,226 | | **no**: 292.8 mm² |
| Striped whole rows, VM 64/128, BF16 lanes on 2,048 macros | 3,608 | whole-row reads (a BF16 row at K = 5,120 is 320 words in one macro) and expert tile collisions | yes: 115.1 mm² |
| **Proposal:** the same with each row's K split over macros in golden-aligned chunk runs, FP32 adders in the return tree | **3,809** | fixed per-phase fill (compute chain), index scan, W15-measured collectives | **yes**: 117.8 of 132 mm² strip, 56.6 of 233.7 mm² hub |
| Proposal weight path with the dedicated units as built | 317 | index scan at 1,024 MACs: 2.6 ms; softmax at 16 lanes: 127 µs | |

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
   - Whole-row ownership gives 3,608 tok/s. Splitting each row's K over up to 2^n macros, in power-of-two-aligned runs of golden chunks, gives 3,809 tok/s (both at 2,048 BF16 macros). That split is exact under the golden `csum` padded tree, with the partials added in the return tree in the same order.
   - It costs log2(split) FP32 adder levels (5 cycles each) and about 2.7 mm² of adders, and it also removes the routing-dependent collision variance.
   - **W10 interim corrections (all now in the model):**
     - Segments are golden-aligned: next_pow2(ceil(C/s)) chunks, not K/s.
     - The split is chosen per expert so that one expert covers the field. There are then no tile collisions, so the 6 active experts share every macro.
     - a_proj mixes FP8 rows with BF16 rows (index weights_proj, compressor wkv/wgate). It runs as two sub-phases, with x streamed twice.
     - A chain-recurrence floor applies: 8 sequential adds × latency 5 = 40 cycles per stream round.
     - Each row has ceil(C/c) segments, which is fewer than s when C is not a power of two. FP4 segments are whole chunk pairs, since an FP4 word carries block b of two sibling chunks. FP8 and FP4 matrices share one x stream. With these, W10's bank map matches the model's issue on every phase where read or x binds, and is below it elsewhere (verdict PASS_issue_match_t_read_below_model).
     - A BF16 element completes 16 chunk sums per cycle, so it needs a 15-adder tree and 128 chain registers. At 4,096 BF16 macros this breaks the fit (148.7 mm²).
3. **The element is one ROM macro, 2 FP4 block-dot lanes (64 MACs), a 274-bit capture register and 8 FP32 chunk partials.** BF16 lanes (16, plus a 15-adder chain tree) go on **2,048** macros: 3,809 tok/s at 117.8 mm². 3,072 gains 0.5% and does not fit (133.3 mm²).
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

**The ROM field is the measured pair** (`PAIR_W`, recalibrated 2026-09-30). W18 ran OpenSTA `report_power` on W10 p5's routed pair: `6_final.odb` with SPEF, TT 0.7 V, 1.087 GHz, input toggle density 0.5. A pair is 2 ROM macros plus their strip logic.

| Pair state | mW | Parts |
|---|---:|---|
| Busy | 229.6 | sequential 45.1, combinational 128.0, clock tree 23.7, ROM macros 32.7 |
| Idle, clock running | 83.5 | clock tree 23.7, flop clock pins 27.0, ROM macro clock 32.7, leakage 0.22 |
| Idle, ideal per-pair ICG (the ROM macro clock stopped too) | 0.22 | leakage: ROM 0.20, cells 0.02 |

How the ledger composes these:
- **Busy pairs:** each weight matvec keeps its holding macros' pairs (2 macros each) busy for its issue time; the other placed pairs (7,102, from W10's re-fit) idle.
- **Clock scaling:** clock and switching power scale linearly with the clock from the 1.087 GHz measurement, at the same 0.7 V (ASSUMED).
- **Energy outside the pair:** the x broadcast over the field, the VM read of x, the partial-sum return wires and the VM write. The pair's own MACs, ROM reads and x capture are inside `PAIR_W`.
- **Everything else is priced as before:** the stream unit and SFU element ops, the on-die share of HBM traffic (0.8 pJ/bit; the DRAM energy dissipates in the stack) and collective link bits.
- **Uncalibrated:** the hub's clock and leakage (dedicated units and VM ports) still come from its area and `technology.json`.
- **Wire energy:** 0.1 pJ/bit/mm (ASSUMED), with 0.4 as a sensitivity.

**The area-based ROM-field terms were wrong by more than an order of magnitude.** Their clock was 13.1 W against the measured 562.6 W (about 43×); their leakage was 13.2 W against 1.6 W (8× too high).

Proposal at 1M context, 1.034 GHz, 3,809 tok/s. The busiest die by energy is stage 9 (the field's busy energy now dominates; it was stage 14, the layer-20 index scan):

| W | Ungated | Per-pair ICG |
|---|---:|---:|
| ROM field clock (7,102 pairs × 79.2 mW) | 562.6 | charged only while busy |
| ROM field leakage | 1.6 | 1.6 |
| Hub clock / leakage (UNCALIBRATED) | 5.0 / 5.7 | 5.0 / 5.7 |
| HBM interface idle | 11.2 | 11.2 |
| **Static** | **586.0** | **23.4** |
| Energy per token, busiest die (µJ) | 1,252 | 1,811 |
| **Total, single user** | **590.7** | **30.3** |
| **Total, saturated** (stage occupancy bound, 77,022 tok/s) | **682.4** (720.1 at 0.4 pJ/bit/mm) | **162.9** (200.6) |
| Instantaneous peak at saturation (a whole-field op busies 6,899 pairs) | 1,565.6 | 1,549.5 |
| Liquid cooling limit | 474.56 | 474.56 |
| HBM stack power at saturation (in the stacks, not the die) | 68.9 | 68.9 |

- **A per-pair ICG that also stops the ROM macro clock is a design requirement, not an energy lever.**
  - Ungated, the field's clock alone (563 W) exceeds the 474.6 W cooling budget, even with no token in flight. No throughput is cool enough.
  - With the ICG the die averages 30 W for a single user and 163 W at saturation, well inside the budget.
- **The instantaneous peak is a power-delivery load, not a thermal one.** A whole-field matvec busies up to 6,899 pairs at 0.23 W for its issue time, about 1.55 kW. It lasts microseconds, so it bounds the PDN, IR drop and di/dt (W18), not the cooling.
- **Stage power-switch rings cost 24.0 mm² of the field** (`switch_rings`). W18 measured 14–17 mV IR drop on a 16-pair cluster. Switch rings that hold a 10 mV budget take 5% of the cluster area: 5% of 7,102 pairs at W18's 513.8 × 131.8 µm pair outline. The re-fit's spare slots hold it: 7,457 of 9,931 needed.
- **Busy duty is low.** At saturation the field averages 543 busy pairs of 7,102 (7.6%); a single user averages 27.

**Clock sensitivity** (`power_clock_sensitivity`; the architecture DAG and the uarch pricing are rebuilt at each clock; pair power scales × f / 1.087 GHz at 0.7 V, ASSUMED — a faster clock that needs a higher supply costs more):

| Clock | tok/s, single user | Saturated tok/s per stage | Field clock, ungated (W) | Per-pair ICG: single user / saturated / peak (W) |
|---|---:|---:|---:|---:|
| 1.034 GHz (model) | 3,809 | 77,022 | 562.6 | 30.3 / 162.9 / 1,550 |
| 1.25 GHz | 4,266 | 86,246 | 680.1 | 32.2 / 180.6 / 1,868 |
| 1.5 GHz | 4,709 | 95,351 | 816.2 | 34.2 / 198.3 / 2,235 |

- A faster clock buys +12% and +24% single-user tok/s, not the clock ratio: wire flight, HBM streams and the W15 collectives keep their times.
- Energy per token is unchanged at the same voltage: busy cycles × energy per cycle.
- With the per-pair ICG the saturated average stays inside cooling. The instantaneous peak grows with the clock (2.2 kW at 1.5 GHz), and that is the PDN's problem.
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
| As built (scalar stream unit, no wire registers) | 178 | 682 (no fit) |
| Architecture (G = 6,144, stream unit 1,024 wide, ideal wires) | 11,193 | 682 (no fit) |
| + floorplan wires | 9,851 | 682 (no fit) |
| + pruned logic | 9,851 | 583 (**no fit**) |
| G = 5,120, pruned, with wires (integer banks: 14 per column, 28 macros per tile; 10 port tiles) | 8,966 | 566.4 / 566.2 (**misses by 0.2**) |
| G = 4,096, pruned | 8,300 | 496 (fits) |

**Decisions:**
- **User decision, 2026-09-29: the Qwen ROM die is AR only**, so the DFlash drafter is not in ROM.
- With target-only banks (10 per column at G = 6,144; W12's integer placement: 34,669 macros, 265.0 mm²), **G = 6,144 pruned fits**: 552.9 / 560 mm², 9,851 tok/s. The scale-ROM remap adds about 11 mm² of margin.
- The hardened tile area decides. If the margin is under 2%, fall back to G = 5,632 pruned (533.9 / 560 mm², 9,390 tok/s).

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

## HBM comparator feasibility audit (W19, `tools/hbm_feasibility_audit.py`, `results/uarch/hbm_feasibility_audit.json`)

This audit is analysis only: no P&R and no RTL. It walks the V4.1 HBM chain node by node, exactly as `v41_hbm_chain` does. It then moves the chain to 1.2 GHz the way W16 does: cycle terms are rescaled and fabric seconds are kept. Each correction below is a switch on that walk, applied one at a time.

- **Baselines.** At main HEAD the walk gives 3,072 AR and 6,206 MTP tok/s. The W16 headline under audit (branch `claude/w16-consolidation`, 84aa38ce) is 3,194 AR and 6,350 MTP. That branch predates the SM constants merged from W13 at SS: drain 95 cycles and a 78-cycle boundary.
- **DRAM proxy.** DRAMsim3 ran on two HBM3E pseudo-channels, using HBM3-class timings in ns (ASSUMED), bank groups interleaved per burst, and all-bank refresh. The fraction of peak it reached, by access pattern:
  - weight stream: 0.898;
  - weight stream with KV writes: 0.873;
  - expert chunks of 1.5 KB at random rows: 0.797;
  - 288 B KV rows: 0.504.
  An idle first access costs 53 ns in the DRAM itself.

| Assumption | Model value | Evidence | Verdict | Corrected AR / MTP tok/s |
|---|---|---|---|---:|
| 1a HBM3E sustained bandwidth | 0.90 × 1.0 TB/s a stack; weight sweep 37.4 µs under a 326 µs chain | Proxy gives 0.87–0.90 on the stream. The sweep is 12% of the chain, so batch-1 AR is not bandwidth-bound | SOUND | 3,072 / 6,206 |
| 1b Routed-expert fetch after the router | Omitted: the uarch chain dropped W9's +1 µs a layer | Expert ids exist only after the top-6. Priced at 0.5 µs first access × 40 layers | OPTIMISTIC, −6% AR | 2,877 / 5,966 |
| 2a Switched collective latency | 0.668 µs × 188 on the path = 125.9 µs | W15 NVLS bench, TP-12, deterministic, SCRATCH: 0.81 µs all-reduce, 0.85–0.89 µs all-gather. 0.83 µs used | OPTIMISTIC, −8.6% | 2,808 / 5,878 |
| 2b Collective count | 188, from W9's K-split down projection | `sm_op_cycles` keeps each row's whole K in one SM, which is the exact golden order. That order needs the 6 × 2,304 intermediate gathered before the down projection: +1 collective per MoE layer | OPTIMISTIC, −7.9% | 2,829 / 5,846 |
| 3 MoE at TP-96 (384 experts, top-6, 2,304 × 5,120 FP4) | Each die holds 1/96 of every expert (184 KB a die an expert) | Balanced by construction. EP at batch 1 costs about +200 µs/token: at most 6 of 96 dies active, 4.9 µs an expert, E[max load] 1.15. Aligning 64 heads onto 96 dies costs +2 µs | SOUND (TP beats EP) | 3,052 / 6,182 |
| 4a MTP, dense matrices on 8 MMA columns | One weight pass serves 6 positions | `SM_ELEM` v41 has 8 columns; the RTL exactness cases use 2 columns | SOUND, not yet measured | — |
| 4b MTP, routed experts | 6 experts a layer | Each position routes its own top-6, giving a union U(6) = 34.6 experts. They are fetched after the router at the proxy's 0.797 | OPTIMISTIC, −10.7% MTP | — / 5,541 |
| 4c MTP, per-position KV rows (W11: 6 × 645) | kvscan issue ×6, collective bytes ×6 | The chain assumes no shared rows | SOUND | — |
| 5 KV at 1M | 0.936 GB a user; ~7,760 users a TP-96 group | Per token per user: 0.183 GB of index keys and 6 MB of rows, against 346 TB/s a group | SOUND | — |
| 6a Indexer | ROM TP-4 widths: 262,144 keys a die | TP-96 holds 1/96 of the keys; the merge becomes 96 × 512 | PESSIMISTIC, +3.3% | 3,174 / 6,958 |
| 6b Attention | 16 heads a die | ≤ 1 head a die at TP-96 | PESSIMISTIC, +3.5% | 3,179 / 6,997 |
| 6c Serial units | Rescaled to 1.2 GHz | AGENTS.md puts SU, SFU, reducers and select in the 0.9 GHz domain | OPTIMISTIC, −7.5% | 2,842 / 5,623 |
| 6d Drafter | 3/40 of an AR token (ASSUMED) | W9 `draft_g` at G = 96 gives 46.8 µs: 5 Markov steps, each with a collective | OPTIMISTIC, −3.7% MTP | — / 5,979 |
| 6e Barriers | 329 × 78 cycles, measured in RTL | This is a hardware-sequenced persistent program, not GPU kernels. With V100 `grid.sync` barriers the rate would be 1,246 | SOUND for this machine | — |
| Qwen 1: HBM efficiency | 0.90 of 8 × 1.0 TB/s | Proxy gives 0.873–0.898 | SOUND (0–3%) | 854 AR (model 881) |
| Qwen 4: DFlash b16 | Verify = AR bytes + draft bytes | GQA 4 × 16 positions = 64 query columns on 16 MMA columns, so K and V pass 4 times. Softmax runs on the SIMT lanes | OPTIMISTIC, −14% | 2,296 at b12 (model 2,670 at b16) |

- **Realistic V4.1 HBM per-user range.** These are all corrections combined, with the union for MTP and W9's drafter:
  - **AR: 2,196 – 2,395 – 2,905 tok/s**, against the 3,194 headline;
  - **MTP: 4,951 – 5,228 – 6,161 tok/s**, against 6,350.
  The first number is the pessimistic end: 1 µs fetch, 0.89 µs collectives, 0.795 expert efficiency. The middle number is central. The last is optimistic: 0.25 µs fetch, the model's own fabric and the 1.2 GHz chain.
- **No assumption is an architectural blocker.** Every gap is a latency term with a known build. The largest are the collectives (count and latency), the exposed expert fetch, and the serial-domain clock.
- **The model under-prices MTP more than AR.** The 6 verify positions do not share routed experts.
- **Build plan for a full-shape HBM token (W19):**
  1. The TP-96 program: exact row-split matvecs, head-aligned `wq_b`, and sequence-sharded KV and index keys. It is golden-checked per layer by extending W17's TP-4 ISA executor to TP-96 ranks.
  2. The expert fetch path: router top-6, then descriptors, then bulk copy into SMEM, with first-byte latency measured in RTL against a DRAM model.
  3. W15's P = 6 and P = 48 NVLS records, committed, with the expert-intermediate gather and the 96-way index merge added.
  4. 8-column SM exactness and timing.
  5. Dedicated units at TP-96 widths in the 0.9 GHz domain.
  6. One full-shape token by runtime composition over 96 ranks, checked against the 1M reference token (21946).
  7. Re-price the model from steps 1–6 and restate the headline.

## Summary: what the model changed

| Design | Previous figure | Microarchitecture model (fits die) | Largest lever |
|---|---:|---:|---|
| V4.1 ROM, 1M | 4,933 (architecture) | 3,809 | stripe rows over all macros; VM 64/128 ports; dedicated indexer, stream unit and reader at spec |
| Qwen ROM, 8K | 10,874 (published) | 9,851 | AR only (no drafter ROM) lets G = 6,144 pruned fit; wires +12%; vector stream unit |
| Qwen HBM, 8K | 881 | 880.6 (DFlash b16 2,671) | bulk-copy weight supply prefetching through boundaries; hardware barrier (30 cycles) |
| V4.1 HBM, 1M | 3,579 | 2,920 (MTP 5,673) | SM op latency on 1/96 row slices (group-slot issue); hardware barrier (40 cycles); bulk-copy supply |

## Speculation (`--spec`, `results/uarch/speculation.json`)

The lane multiplier m counts the positions that multiply one ROM weight word in the same cycle.
- **m = 1 (time-multiplexed):** issue time multiplies by the positions. Fill, wire stages and dependency latency are paid once per verify pass, so there are no new lanes.
- **m ≥ 2:** replicates every element's lanes beside its macro, plus wider broadcast and return.

| Design | Verify / AR time | tok/s | Speedup | Extra lane area | Decision (user, 2026-09-29) |
|---|---:|---:|---:|---:|---|
| V4.1 ROM MTP, 6 positions, m = 1 | 2.30× | **5,857** | **1.54×** | 0 | **adopted** |
| V4.1 ROM MTP, m = 2 | 1.89× | 7,064 | 1.86× | 86.0 mm² (does not fit) | rejected |
| V4.1 ROM MTP, m = 6 | 1.65× | 8,051 | 2.11× | 429.9 mm² | rejected |
| Qwen ROM DFlash, m = 1 (best block = 1, i.e. AR) | — | 9,017 | 1.0× | 0 (+29 mm² drafter ROM) | **AR only** |
| Qwen ROM DFlash, m = 5, block 5 | — | 18,720 | 2.08× | 178.7 mm² | rejected: does not fit |

**Why the two ROM designs differ:**
- **V4.1 tokens are latency-bound.** Fill is about half the token, so 6 positions share the expensive part.
- **Qwen tokens are lane-bound.** Each extra position costs a whole weight sweep, and only 1.7–3.7 tokens are accepted.

Removing the drafter frees about 12% of Qwen code ROM. Target-only banks are 10 per column at G = 6,144, and **G = 6,144 pruned then fits** (552.9 / 560 mm², 9,851 tok/s). The scale-ROM remap adds about 11 mm² of margin.

The V4.1 draft cost is ASSUMED at 3/40 of an AR token (3 draft blocks of 40 layers). The HBM comparators' DFlash and MTP rows come from W13's SM model.

## Fabric sensitivity and GPU tiers (`--fabric`, `results/uarch/fabric.json`)

Every multi-die design here assumes deterministic hardware collectives at link latency:
- **V4.1 ROM array:** direct UCIe/board links inside its TP-4 groups (the architecture prices 145–165 cycles, about 0.15 µs).
- **V4.1 HBM comparator:** TP-96 through an NVL-class switch (0.668 µs).
- **Qwen pair:** 73 UCIe exchanges per token (about 17.5 ns each).

### Collective latency sweep (tok/s, single user, 1M context for V4.1, 8K for Qwen)

| Collective / exchange latency | V4.1 ROM (AR) | V4.1 HBM (GPU org., AR) | Qwen ROM (AR, G = 6,144) | Qwen HBM (AR) |
|---|---:|---:|---:|---:|
| own baseline | **3,809** (W15-measured collectives) | **2,920** (0.668 µs switch) | **9,851** (W15-measured exchange; 9,968 at 17.5 ns) | **881** |
| 0.1–0.15 µs | 3,752 | 4,084 | 9,404 | 876 |
| 0.5–0.668 µs | 2,785 | 2,920 | 7,378 | 854 |
| 1 µs | 2,390 | 2,469 | 5,813 | 828 |
| 5 µs | 881 | 863 | 2,155 | 667 |
| 10 µs | 493 | 476 | — | — |

**At equal collective latency, V4.1 ROM and V4.1 HBM have almost the same single-user speed.** Both are latency-bound, not bandwidth-bound.
- The ROM array's advantage (3,809 against 2,920) is structural. Its weights are local, so small TP-4 groups on direct links suffice.
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
| Qwen ROM AR (G = 6,144) | 9,851 | 86.5 | 2 | 11,921 | 5,960 | 84.7 | 268 |
| Qwen HBM tier 3, AR | 881 | 983 | 16 | 6,684 | 418 | 133 | 255 |
| Qwen HBM tier 3, DFlash | 2,671 | 358 | 8 | 7,101 | 888 | 129 | 255 |
| Qwen 1× B200, AR (tier 2) | 331 | 2,081 | 255 | 7,907 | 31.0 | 87.1 | 255 |
| V4.1 ROM, AR (ungated) | 3,809 | 19,309 | 32 | 77,022 | 2,407 | 1,056 | 866 |
| V4.1 ROM, MTP m = 1 (ungated) | 5,857 | 12,637 | 16 | 50,708 | 3,169 | 1,591 | 866 |
| V4.1 HBM tier 3, AR | 2,920 | 3,692 | 16 | 21,792 | 1,362 | 913 | 811 |
| V4.1 HBM tier 3, MTP | 5,673 | 2,287 | 4 | 12,122 | 3,030 | 1,676 | 811 |
| V4.1 8× B200, AR (tier 2) | 278 | 19,852 | 839 | 13,018 | 15.5 | 423 | 839 |

Per-batch rows (per-user rate, aggregate, per-user latency, energy, system power) are in the record. Measured anchors, at 689 W:
- B200 AR at 1 to 32 users: 2,996 to 121 mJ/token.
- B200 DFlash at batch 1: 586 mJ (Math500) and 722 mJ (HumanEval).
- DeepSeek-R1 on 8× B200: 14,978 mJ.

### Energy basis

- **V4.1 ROM:** the power ledger's terms, summed over every stage and multiplied by the 4 TP dies, plus the stacks' share of the index and KV reads. The terms are the measured pair's busy excess over its clocked-idle floor, the x network, the stream unit, the on-die HBM share and the links.
  - Dynamic energy is 86.8 mJ on the dies (69.1 of it the pairs) and 19.3 mJ in the stacks per token.
  - Static power, ungated, is 73.1 kW:
    - 112 layer dies at the ledger's ungated clock + leakage + HBM interface idle (580 W: the measured field clock is 563 W), plus the rack's always-on SerDes and UCIe (33.1 W);
    - head and Engram-table dies at the rack record's static.
  - **The ungated rows are not a realisable design:** a layer die's field clock exceeds its cooling budget. The adopted per-pair ICG and stage power gating (the levers section and the gated-alike table) are the figures to compare.
- **Qwen ROM:** its own ledger with the same constants, both dies.
  - Dynamic energy is 76.2 mJ/token, of which 59.5 mJ is the HBM stack share of the KV read and 7.1 mJ its on-die share.
  - Static power is 101.5 W. The areas are the W12 ROM (265 mm²), the pruned group logic plus PHYs (173.8 mm²) and the KV ring (23.9 mm²).
- **HBM tier 3:** SM MACs; every weight and KV byte over the whole HBM path (104.9 pJ/B); SMEM staging write and read; stream elements; and, for V4.1, the dedicated units' energy per token taken from the ROM ledger and fabric bytes over two switch hops.
  - Static power per package: 69 W (Qwen); 6.5 kW for the 96 V4.1 dies.
  - The NVL-class switch is not charged.
- **GPU:** 689 W measured decode power per B200 (`technology.json` `power.gpu_reference_power`) × step time. The record also carries the rows at the 1,200 W TDP.
- MAC energy is 2 operations per MAC in this section, as in `technology.json` and `arch_budget_v41`. The V4.1 power ledger above charges 1 per MAC. Its ROM-field MACs are now inside the measured pair, so the operation count applies only to the hub (HC projection and attention/indexer MACs). The test checks that this section's ledger reproduces the power ledger's busiest stage when run at 1 operation per MAC.
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
| Qwen ROM (AR, G = 6,144) | 1 | 2 | 8 | 2 | $28k–55k | 2.84–5.58 | 2.35–4.61 | 2.35–4.61 |
| Qwen HBM tier 3 (AR / DFlash) | 1 | 2 | 8 | 0 | $25k | 9.36 | 3.52 | 3.52 |
| Qwen 1× B200 (tier 2, AR) | 1 | 2 | 8 | 0 | $25k | 75.53 | 3.16 | 5.15 |
| V4.1 ROM array (AR / MTP m = 1) | 94 | 188 | 464 | 188 | $2.63M–5.17M | 449–883 | 34.2–67.1 | 34.2–67.1 |
| V4.1 HBM tier 3 (AR / MTP) | 48 | 96 | 384 | 0 | $1.20M | 212 | 55.1 | 55.1 |
| V4.1 8× B200 (tier 2, AR) | 8 | 16 | 64 | 0 | $200k | 720 | 15.4 | 51.4 |

Each system is costed at its best mode for each point: its fastest single-user mode at B = 1, and its largest aggregate within capacity when saturated. The ≥ 100 tok/s/user column is an ASSUMED illustrative interactivity floor.

### What the economics show

1. **Single-user speed is where ROM wins.**
   - At batch 1 the Qwen ROM package is 30× a B200 in tok/s, 24× in energy per token and 14–27× in $ per tok/s.
   - The V4.1 ROM array against 8× B200, both AR, is 13.7× in tok/s. Ungated it spends about the same energy per token (19.3 against 19.9 J). With the adopted gating (per-pair ICG and stage power gating) it spends 41× less (481 mJ). With MTP on both it is 11× in tok/s.
2. **Batching does not help the Qwen ROM package.** Its 8 HBM stacks must stream every user's 604 MB of 8K KV per token, so the aggregate saturates at 11,921 tok/s from batch 2. A B200, with the same 8 stacks, saturates at 7,907, and only at 31 tok/s per user. At saturation all three Qwen machines spend 85–133 mJ per token, dominated by the KV read. Cost per aggregate tok/s is then within 2× across them.
3. **V4.1 ROM has the largest aggregate** (77,022 tok/s against 21,792 for tier 3 and 13,018 for 8× B200) **and, gated, the lowest saturated energy** (221 mJ against 755 for tier 3 gated and 423 for 8× B200; 1,056 ungated).
   - Its capex is the highest: 94 packages plus 188 ROM mask sets, where the NRE is 0.3–2.8 M$ per system at 1,000 units.
   - Per aggregate tok/s it therefore costs 2–4× 8× B200 at saturation, where the GPU serves 15.5 tok/s per user.
   - At a ≥ 100 tok/s/user floor it is 0.7–1.3× the GPU.
4. **MTP m = 1 is a single-user lever on the ROM array.** It lowers the saturated aggregate by 34%. Run MTP only while the stages are not yet full (below about 12 users) and AR beyond.
5. **Static power sets the energy of both V4.1 designs.**
   - Ungated, V4.1 ROM runs at 19.3 J per token at batch 1 and 1.06 J saturated, against 19.9 and 0.42 J for 8× B200. The measured field clock (563 W per layer die) dominates.
   - Gated (per-pair ICG, stage power gating, 1 µs wake) it runs at 0.48 and 0.22 J.

## Economics levers: static power, adaptive MTP, ROM masks (`--levers`, `results/uarch/economics_levers.json`)

These are root's follow-ups to the economics findings (2026-09-29). The test is in `tests/test_uarch_economics.py`.

### V4.1 ROM static-power reduction

At batch 1 the token visits the 28 stages one after another. Each stage is on the critical path for 5.1–22.0 µs of the 262.5 µs token and idle for the rest; the shortest idle is 240.6 µs. The model prices each layer die's static power by region: the ROM field from the measured pair (2026-09-30), the hub by class from the area ledger:

| Component | W per layer die |
|---|---:|
| ROM field (7,102 measured pairs): clock / leakage | 562.6 / 1.6 |
| Hub (dedicated units + VM ports): clock / leakage (UNCALIBRATED) | 5.0 / 5.7 |
| HBM interface idle (4 stacks) | 11.2 |
| Always-on 112G SerDes | 30.6 |
| UCIe idle | 2.5 |

**The ROM field's clock is the largest static item on a layer die**, 18× the always-on SerDes. The model then applies four cumulative policies:

1. **Stage clock gating.** A stage's clock runs only during its window. The rest of the period keeps an ASSUMED 10% clock residual (the global spine and the ICG enables).
2. **Region clock gating.** Inside the window, the ROM field and the hub each clock only while they are busy. For the field this is the per-pair ICG: only an op's holding pairs clock, charged for the pair-weighted busy time.
3. **Stage power gating** in the idle time, with these residuals:
   - logic and ROM leak 3% (ReGate, MICRO 2025, §6.1; a mask ROM holds no state, so it needs no retention);
   - the VM SRAM sleeps with retention at 25%;
   - the HBM controller and PHY are in power-down at 3%, with the DRAM self-refreshing (ReGate Table 3: 60-cycle wake);
   - SerDes and UCIe are in low-power idle at an ASSUMED 10%.
4. **Wake schedule.** The stage wakes an ASSUMED 1 µs ahead of its window: ~100 staggered sub-domains of ReGate's 10-cycle domains, to bound the rush current. The SerDes wake 5 µs ahead (IEEE 802.3bj EEE Tw target for 100 Gb/s).
   - Each gating event costs the stage's leakage × an ASSUMED 0.5 µs break-even time, from ReGate's 412–469-cycle BETs for the HBM, ICI and whole-array domains.
   - Wake is only scheduled where the idle gap fits the wake-up plus the break-even time.

**Engram table dies** (ROM tables, no state) stay awake only for their two gathers and the wake-up. Head dies scale by the layer-die policy ratio. Dynamic energy is unchanged from the economics section.

**No wake lands on the single-user token path.** At batch 1 the schedule is static and periodic, and the shortest idle (240.6 µs AR, 551.2 µs MTP) exceeds every wake-up, including the 133 µs sensitivity: the Haswell C6 worst case (Schöne et al. 2015), which includes a state restore that a ROM stage does not need.

| V4.1 ROM system (1M) | Static W | mJ/token, AR, B = 1 | mJ/token, AR, saturated | mJ/token, MTP, B = 1 | mJ/token, MTP, saturated |
|---|---:|---:|---:|---:|---:|
| Ungated (economics section) | 73,145 | 19,310 | 1,056 | 12,638 | 1,591 |
| Stage clock gating | 17,625 | 4,733 | 498 | 3,142 | 761 |
| + region clock gating (per-pair ICG) | 15,767 | 4,246 | 344 | 2,876 | 515 |
| **+ stage power gating, 1 µs wake** | **1,428** (B = 1) / 8,837 (saturated) | **481** | **221** | **412** | **296** |
| + stage power gating, 133 µs wake | 7,216 (B = 1) | 2,001 | 344 | 829 | 515 |

- **Both levers are now large, because the measured clock is.**
  - Clock is 568 of 613 W on a layer die. Stage clock gating cuts batch-1 energy 4.1× (AR).
  - What is left is the ASSUMED 10% ICG residual on the 563 W field clock, 56 W per idle die. The pair's own ICG measures 0.22 mW idle, so this residual is the global spine to 7,102 ICGs, and W18's die route must measure it.
  - Power gating the idle stages cuts batch-1 energy 40× (AR) and 31× (MTP), to 481 and 412 mJ/token. The 8× B200 AR figure is 19,852.
- **At saturation the gaps are short.** The period is 13.0 µs (AR) and 72 µs (MTP).
  - With a 1 µs wake, 28 of 29 stages still gate between tokens, and energy falls to 221 mJ (AR) and 296 mJ (MTP).
  - With a C6-class wake, no stage gates at saturation.
- **Build requirements:**
  - power switches per stage domain, with staggered wake;
  - retention only on the VM;
  - HBM PHY power-down;
  - SerDes low-power idle with a 5 µs pre-wake scheduled from the static token schedule.
- The HBM comparator (tier 3) is still priced ungated. Its dies are busy for most of the token, so this lever is mainly the ROM array's.

### Adaptive MTP

Use MTP while its aggregate exceeds AR's, and AR beyond. On the ROM array, AR's per-user rate stays flat until its own saturation, so the crossing is exact: MTP's saturated 50,708 / AR's 3,809 = **13.3 users**. On the HBM comparator the AR chain slows with every column-batched user, and the sweep brackets the crossing between 8 and 16 users.

| Batch | V4.1 ROM mode | Per-user tok/s | Aggregate tok/s | V4.1 HBM tier 3 mode | Per-user tok/s | Aggregate tok/s |
|---:|---|---:|---:|---|---:|---:|
| 1 | MTP | 5,857 | 5,857 | MTP | 5,673 | 5,673 |
| 2 | MTP | 5,857 | 11,713 | MTP | 5,673 | 11,346 |
| 4 | MTP | 5,857 | 23,426 | MTP | 3,031 | 12,122 |
| 8 | MTP | 5,857 | 46,852 | MTP | 1,515 | 12,122 |
| 16 | AR | 3,809 | 60,941 | AR | 1,362 | 21,792 |
| 32 | AR | 2,407 | 77,022 | AR | 681 | 21,792 |
| 866 / 811 (capacity) | AR | 88.9 | 77,022 | AR | 26.7 | 21,658 |

### ROM mask cost: via-programmable ROM

A via-programmable ROM shares base masks between dies of the same role and codes each die's weights in 1–2 masks:
- Taalas HC1 changes two metal masks per model (EE Times).
- A single EUV mask costs $0.5–1M (SemiEngineering, "Mask Complexity, Cost, And Change").
- V4.1 has 3 base designs (layer, head + DSpark, Engram table) at a full $15M each. Qwen has 1.
- NRE is amortised over 1,000 production units, as in the economics section.

| V4.1 ROM array (188 dies) | NRE | Capex per system | $ per tok/s, B = 1 | $ per tok/s, saturated | Saturated, base masks excluded |
|---|---:|---:|---:|---:|---:|
| Full mask set per die (economics high) | $2,820M | $5.17M | 853 | 67.1 | — |
| 10% of a set per die (economics low) | $282M | $2.63M | 434 | 34.2 | — |
| Via-programmable, 1 × $0.5M | $139M | $2.49M | 411 | 32.3 | 31.7 |
| Via-programmable, 2 × $0.5M or 1 × $1M | $233M | $2.58M | 426 | 33.5 | 33.0 |
| Via-programmable, 2 × $1M | $421M | $2.77M | 457 | 36.0 | 35.4 |

- **Via-programmable ROM removes the high case.** The V4.1 array costs $32–36 per saturated tok/s against the earlier $34–67, and against $15.4 for 8× B200 at saturation (whose users then get 15.5 tok/s each) and $51.4 at the ≥ 100 tok/s/user floor.
- **The packages, not the masks, set V4.1 ROM cost.** 94 packages at the iso-package price make up $2.35M of the $2.49–2.77M.
- **Qwen ROM:** $16–19M of NRE, $3.44–3.69 per saturated tok/s ($2.18–2.43 with the base excluded).

### Every design gated alike (`gated_alike` in the record)

This is root's fairness follow-up (2026-09-29). The same policies and cited constants now apply to every design:
- **Clock gating:** a domain clocks only while it is busy. When idle it keeps the 10% ICG residual.
- **Power gating:** a domain power-gates in every idle gap that fits its wake-up plus break-even time, with ReGate's residuals.
- **Wake constants:**
  - core domains (SMs, dedicated units, lanes, stream unit, L2): 1 µs wake, 0.5 µs break-even;
  - HBM controller and PHY: 60-cycle wake, 412-cycle break-even (ReGate Table 3);
  - SerDes and UCIe: 5 µs wake, 10% low-power-idle residual.
- **No wake on the token path.** Each wake finishes at the end of its gap, from the static schedule.
- **Busy time and gaps** come from each design's own schedule:
  - **V4.1 HBM comparator:** the W13 chain walked node by node (`v41_hbm_timeline`, which reproduces 342.5 µs AR and 617.5 µs MTP).
  - **Qwen dies:** their op boundaries (181), KV streams (36) and UCIe exchanges (73), with the gaps split evenly.
  - **At saturation,** each domain gets one contiguous idle gap per pass or token, the ROM array's rule.
- **GPU rows** stay at measured board power, which already contains whatever the GPU gates.

This table supersedes the energy columns of "Batch, energy and capacity" above.

| Design | Point | tok/s | Ungated mJ/token | Clock-gated | Clock + power gated | Static W, ungated → gated |
|---|---|---:|---:|---:|---:|---:|
| Qwen ROM AR (G = 6,144) | B = 1 | 9,851 | 86.5 | 84.7 | **84.6** | 102 → 82.8 |
| Qwen ROM AR (G = 6,144) | saturated | 11,921 | 84.7 | 83.5 | **83.5** | 102 → 87.3 |
| Qwen HBM tier 3 AR | B = 1 | 881 | 983 | 978 | **976** | 69.3 → 63.7 |
| Qwen HBM tier 3 AR | saturated | 6,684 | 133 | 132 | **132** | 69.3 → 62.0 |
| Qwen HBM tier 3 DFlash | B = 1 | 2,671 | 358 | 357 | **356** | 69.3 → 63.5 |
| Qwen HBM tier 3 DFlash | saturated | 7,101 | 129 | 129 | **128** | 69.3 → 62.4 |
| Qwen 1× B200 AR (tier 2) | B = 1 | 331 | 2,081 | — | **2,081** | measured |
| Qwen 1× B200 AR (tier 2) | saturated | 7,907 | 87.1 | — | **87.1** | measured |
| V4.1 ROM AR | B = 1 | 3,809 | 19,310 | 4,246 | **481** | 73,145 → 1,428 |
| V4.1 ROM AR | saturated | 77,022 | 1,056 | 344 | **221** | 73,145 → 8,837 |
| V4.1 ROM MTP m = 1 | B = 1 | 5,857 | 12,638 | 2,876 | **412** | 73,145 → 1,544 |
| V4.1 ROM MTP m = 1 | saturated | 50,708 | 1,591 | 515 | **296** | 73,145 → 7,501 |
| V4.1 HBM tier 3 AR | B = 1 | 2,920 | 3,692 | 3,468 | **3,246** | 6,513 → 5,210 |
| V4.1 HBM tier 3 AR | saturated | 21,792 | 913 | 895 | **755** | 6,513 → 3,067 |
| V4.1 HBM tier 3 MTP | B = 1 | 5,673 | 2,287 | 2,184 | **1,922** | 6,513 → 4,444 |
| V4.1 HBM tier 3 MTP | saturated | 12,122 | 1,676 | 1,654 | **1,475** | 6,513 → 4,081 |
| V4.1 8× B200 AR (tier 2) | B = 1 | 278 | 19,852 | — | **19,852** | measured |
| V4.1 8× B200 AR (tier 2) | saturated | 13,018 | 423 | — | **423** | measured |

- **Gating does not change the Qwen rows.** Their energy is dynamic: the ROM package's KV read and the HBM die's weight stream. Their idle gaps (under 1 µs between ops) are shorter than a core wake plus break-even. Gated or not, Qwen ROM uses 84.6 mJ/token against 356 for HBM tier 3 DFlash and 2,081 for a B200.
- **The V4.1 HBM comparator gains 12–16% at batch 1 and 12–17% at saturation.**
  - Its 96 TP dies are all on every token. Their idle comes in short gaps between phases: the SMs have 281 gaps within the 253 µs they are idle, and only 91 µs of them are long enough to gate.
  - The SerDes idle between collectives mostly in gaps under 5 µs.
- **The V4.1 ROM pipeline idles each stage in one long gap per token,** and gating takes its batch-1 energy down 40×.
- **Gated alike, V4.1 ROM uses 6.7× less energy per token than the HBM comparator at batch 1 in AR, 4.7× with MTP, and 3.4× (AR) / 5.0× (MTP) at saturation.** These figures use the measured ROM-field pair; the HBM comparator's SMs are still area-priced. The advantage is structural: a pipeline of weight-local stages idles in long gaps; a TP-96 machine does not.

### Adopted power and cost requirements (root, 2026-09-29)

1. **Stage power gating on the V4.1 ROM array.**
   - Power switches per stage domain, with a 1 µs staggered wake (about 100 sub-domains, to bound di/dt).
   - Retention only on the VM SRAM; the mask ROM and the logic hold no state across tokens.
   - HBM controller and PHY power-down, with the DRAM self-refreshing.
   - SerDes and UCIe low-power idle, with a 5 µs pre-wake.
   - Every wake is scheduled from the static token schedule into an idle gap that fits wake + break-even. No wake may land on the single-user token path.
2. **Adaptive MTP.** Run MTP while the batch is below the switch point and AR at or above it. The switch is 13.3 users on the V4.1 ROM array (exact) and between 8 and 16 users on the HBM comparator.
3. **Via-programmable ROM is the cost basis.**
   - Shared base mask sets per die role: 3 for V4.1 (layer, head + DSpark, Engram table), 1 for Qwen.
   - 1–2 EUV coding masks per die at $0.5–1M each.
   - V4.1 NRE is $139–421M, against $2,820M with full mask sets.
4. **Every energy comparison uses the gated-alike table above.** The same policies and cited constants apply to every design; GPU rows are at measured board power.

## Consolidation: die counts, clocks, right-sized HBM dies, the comparison rule (`--consolidation`, `results/uarch/consolidation.json`)

This is a user-approved study (W16, 2026-09-30). The physical floorplans leave spare area that the analytical die ledger did not predict. This section re-derives the die counts from the placed field geometry and prices the clock plan at SS sign-off. It also right-sizes the HBM dies and re-prices every design on die area. It calls the sections above; the only thing it changes elsewhere is the Qwen ROM product row (option C, below). Test: `tests/test_uarch_consolidation.py`.

**TT basis pending SS.** Rows are priced at the TT model clock (1.0339 GHz) unless they are labelled SS / 1.2 GHz. **The product V4.1 die count is OPEN**: it is re-derived when the closed element pair's pitch lands, so the rows below are the decision table, not a restatement.

### Headline comparison (user decision, 2026-09-30; `headline_table`)

- **V4.1 ROM:** the headline is saturated throughput, energy per token and cost at **equal manufacturing cost**. Per-user speed is claimed only against real GPUs (tier 1 measured, tier 2 calibrated), and is reported honestly against the idealised HBM machine (tier 3).
- **Qwen ROM** keeps its per-user claim.
- ROM energies include the adopted 256-cycle pre-ramp.
- GPU cost is the purchase price; the ROM and tier-3 cost is manufacturing capex (low NRE).
- The V4.1 tier-3 per-user rates are W19's COMPOSED token (`claude/w19-hbm-token` 23648fc3): every term priced along the executed TP-96 program, collectives on W15b's committed P=48 NVLS record and W15b's MEASURED 96-way top-k select (3,875 cycles at P = 64; blocking, so the MTP pass charges its 6 positions in series). Lane-local fusion applies to the comparator too, for fairness: AR 481.5 → 465.2 µs (2,077 → 2,150 tok/s), MTP verify pass 885.5 → 854.0 µs plus the audit's 49.9 µs drafter. The grouped o-reduce is still extrapolated from the all-reduce fit. The audit's central figures stay in the record as a reference. Qwen DFlash keeps the audit's −14%. The exact-order extra gather does not apply to the ROM array, which sums experts in id order inside the element.

| Design | Tier | Per-user AR | Per-user MTP | Saturated tok/s | mJ/token, B = 1 / saturated | Capex | Users at 1M |
|---|---|---:|---:|---:|---:|---:|---:|
| V4.1 ROM array (product basis, 1.2 GHz SS, SS wires, 50% cap + pre-ramp) | ROM | 2,838 | 4,618 | 89,972 | 672 / 312 | $727k | 866 |
| V4.1 HBM tier 3 (idealised), equal area: 5 x TP-96 (480 right-sized dies, 1.2 GHz, SS wires; W19 composed token) | 3 | 2,150 | 4,037 | 126,464 | 9,993 / 742 | $1,260k | 38,815 |
| V4.1 HBM tier 3 (idealised), equal cost: 2 x TP-96 (192 right-sized dies, 1.2 GHz, SS wires; W19 composed token) | 3 | 2,150 | 4,037 | 50,585 | 4,874 / 742 | $513k | 15,526 |
| V4.1 HBM tier 3 (idealised), equal power: 1 x TP-96 (96 right-sized dies, 1.2 GHz, SS wires; W19 composed token) | 3 | 2,150 | 4,037 | 25,293 | 3,168 / 742 | $264k | 7,763 |
| DeepSeek-V4.1-Flash on 8x B200 (tier 2, calibrated) | 2 | 278 | 539 | 13,018 | 19,852 / 423 | $200k | 839 |
| DeepSeek-R1 (V4.1-class anchor), 8x B200, TensorRT-LLM min-latency, 3 MTP layers (relaxed acceptance) | 1 | — | 368 | — | 14,978 / — | — | — |

| Design | Tier | Per-user AR | Per-user DFlash | Saturated tok/s | mJ/token, B = 1 / saturated | Capex | Users at 8K |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen ROM option C (4 dies, 2 packages, TP-4, G 6,144), TT | ROM | 9,368 | — | 23,842 | 98 / 85 | $29k | 536 |
| Qwen ROM option C at 1.2 GHz SS (W12 SS wires, LAT-7 ME, KV_PREP, droop cap75 + preramp256) | ROM | 8,460 | — | 23,842 | 120 / 107 | $29k | 536 |
| Qwen ROM option C at 1.2 GHz SS, RTL-attributed, as built: per-layer body x 1.0923 (W12b 2,687 / model 2,460) + 2 all-reduces at the measured 991 cycles (2 serialized 128-word TP segments; W12b a17a3c79) | ROM | 6,222 | — | 23,842 | — / — | $29k | 536 |
| Qwen ROM option C at 1.2 GHz SS, RTL-attributed, body only: per-layer body x 1.0923; all-reduces at the model's 442 cycles, PENDING W12b's one-segment fix (79783ff9, unmeasured; est. ~620 at LAT 339) | ROM | 7,921 | — | 23,842 | — / — | $29k | 536 |
| Qwen HBM, 1 right-sized die(s) x 6 stacks (388.9 mm2 each) (tier 3, idealised; DFlash W19 audit -14%) | 3 | 660 | 1,722 | 5,328 | 356 / 128 | $19k | 188 |
| Qwen HBM, 2 right-sized die(s) x 4 stacks (265.8 mm2 each) (tier 3, idealised; DFlash W19 audit -14%) | 3 | 880 | 2,296 | 7,104 | 356 / 128 | $20k | 255 |
| Qwen3-8B on 1x B200, FP8 (tier 2, calibrated) | 2 | 331 | 853 | 7,907 | 2,081 / 87 | $25k | 255 |
| Qwen3-8B, 1x B200, SGLang FA4, BF16, AR, concurrency 1 (DFlash paper Table 3) | 1 | 230 | — | — | 2,996 / — | — | — |
| Qwen3-8B, 1x B200, SGLang FA4, DFlash b16, Math500 (tau 8.01, 5.1x) | 1 | 1,175 | — | — | 586 / — | — | — |
| Qwen3-8B, 1x B200, SGLang FA4, DFlash b16, HumanEval (tau 6.50, 4.2x) | 1 | 955 | — | — | 722 / — | — | — |

**MTP acceptance** (`tau_sweep_1m`). The headline τ is third-party: 3.78, arena-hard (general chat), from LMSYS, 'DSpark in SGLang' (2026-07-06), https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ Figure 4: DeepSeek-V4-Flash, H200 TP4 DP-attention, block 6, cap-accept verify (acceptance ceiling). It is V4-Flash, not V4.1-Flash, and cap-accept is a ceiling. Our measured 3.649 corroborates it. γ = 5, so τ ≤ 6 always holds.

| Design | τ 2.91 | τ 3.649 | τ 3.78 | τ 4.5 | τ 5.24 |
|---|---:|---:|---:|---:|---:|
| V4.1 ROM array (product basis, 1.2 GHz SS, SS wires, 50% cap + pre-ramp) | 3,683 | 4,618 | 4,784 | 5,695 | 6,632 |
| V4.1 HBM tier 3 (idealised), equal area: 5 x TP-96 (480 right-sized dies, 1.2 GHz, SS wires; W19 composed token) | 3,219 | 4,037 | 4,182 | 4,978 | 5,797 |
| V4.1 HBM tier 3 (idealised), equal cost: 2 x TP-96 (192 right-sized dies, 1.2 GHz, SS wires; W19 composed token) | 3,219 | 4,037 | 4,182 | 4,978 | 5,797 |
| V4.1 HBM tier 3 (idealised), equal power: 1 x TP-96 (96 right-sized dies, 1.2 GHz, SS wires; W19 composed token) | 3,219 | 4,037 | 4,182 | 4,978 | 5,797 |
| DeepSeek-V4.1-Flash on 8x B200 (tier 2, calibrated) | 430 | 539 | 558 | 664 | 774 |
| DeepSeek-R1 (V4.1-class anchor), 8x B200, TensorRT-LLM min-latency, 3 MTP layers (relaxed acceptance) | 294 | 368 | 381 | 454 | 528 |

**Short context (8K)** (`short_context_8k`). The public GPU records are short-context; the 1M headline is dominated by the index scan and attention.

| Design | AR tok/s | MTP tok/s | Saturated | Dies / GPUs | Silicon mm² | Capex |
|---|---:|---:|---:|---:|---:|---:|
| V4.1 ROM product (columns, 1.2 GHz SS) | 3,341 | 5,575 | 115,770 | 208 | 169,520 | 727,026 |
| V4.1 HBM tier 3, equal cost (2 x TP-96), W19 composed/model ratio at 1M applied at ctx | 2,287 | 5,055 | 98,515 | 192 | 65,376 | 512,856 |
| V4.1-Flash, 8x B200 (tier 2, calibrated) | 283 | 548 | — | 8 | 12,800 | 200,000 |
| V4.1-Flash, 8x B300 (tier 2; = B200 within the model, ASSUMED) | 283 | 548 | — | 8 | 12,800 | — |

**GPU calibration** (`gpu_calibration`). Public single-user records: DeepSeek-R1 on 8x B200 at 368 tok/s (TensorRT-LLM blog 1: ISL 1K / OSL 2K, MTP-3) and DeepSeek-V3.2 at ~312 on B200 (blog 15). The ~1,000 tok/s/user public record is Llama 4 Maverick, not DeepSeek. Our tier-2 model at ~3K context gives V4.1-Flash 282.7 AR / 548.4 MTP, +49% against R1's 368. That comparison mixes model size (R1 has 37B active parameters, V4.1-Flash 13B) with model error.

**HBM tier-3 collective count** (W19's exact TP-96 program; sensitivity): the model has 188 collectives on the path, the audit 228, and the minimised exact program 265 → 2230.5 AR (305 → 2076.7), from the audit's central 2,394.5.

### Density basis (root ruling, 2026-09-30)

- **Fit basis for both ROM designs:** storage-only ROM at N5, 75.0 Mbit/mm² (a 0.021 µm² 6T cell × ROMA's ROM/SRAM 0.33 / array efficiency 0.52), plus SECDED 266/256.
- **Sensitivities:** ROMA's TSMC 7 nm compiler at 57.8 Mbit/mm² (conservative), and the placed predictive ASAP7 macro at about 150 Mbit/mm² raw (physical feasibility only; `results/floorplan/v41_rom_capacity.json` forbids substituting it).
- **Compute-in-ROM upside:** the Qwen ledger's 148 Mbit/mm² is N6 storage ÷ an ASSUMED 1.6× cell multiplier × a vendor-quoted 4 bits per cell. It may appear only as a labelled upside (an unimplemented mechanism).
- Neither 75 nor 148 is HC1-derived; HC1 is a cross-check only (4.31 MB/mm² whole die).

**Most of the floorplans' spare area is the ASAP7 macro being twice the fit density.**

### V4.1 ROM layer dies: stage table

**Field geometry.** The W10 re-fit is reproduced here, because its record is not committed; `refit` pins its hashes.

- Tool: `tools/v41_floorplan_refit.py` at `claude/w10-v41-rom-element` 1f598e0b.
- The FP8/FP4 pair p5 stands in for both pair types, because the BF16 pair q2 failed at detailed placement. p5 is not closed: 886 MHz, WNS −209 ps.
- The field is 9,931 pair rows at 485.136 × 120.96 µm = 582.77 mm².

**Overhead.** PDN bumps, IO/ESD, DFT, clock and decap are reserved at 12.5% of the die (band 10–15%, ASSUMED). On-chip decap alone takes up to 10% (Popovich, Mezhiba and Friedman, 2008), and 15–20% in high-performance processors; `technology.json` uses 0.10.

**Credit (root ruling: ring only).** The re-fit's 67.3 mm² of whitespace outside the field was measured on its rectangles:

- 53.5 mm² is the 1.0–1.1 mm die-edge ring left after the edge I/O;
- 13.8 mm² is hub halos, which are not field.

The overhead is charged to the ring first; the "none" column gives no credit. Fill is 90%.

**Table.** Each cell is TP-4 stages for storage-only 75 / ASAP7 / ROMA (layer dies = 4 × stages). Engram table dies are 36 / 20 / 46–48.

| BF16 | Pitch | Overhead | Credit: ring | Credit: none |
|---|---|---:|---|---|
| **standard pair (adopted)** | W10 budget 485 × 121 µm | 10% | 28 / 23 / 33 | 31 / 26 / 37 |
| **standard pair (adopted)** | W10 budget 485 × 121 µm | 12.5% | 29 / 24 / 34 | 32 / 27 / 38 |
| **standard pair (adopted)** | W10 budget 485 × 121 µm | 15% | 30 / 25 / 36 | 34 / 28 / 40 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 10% | 34 / 29 / 39 | 37 / 32 / 43 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 12.5% | 35 / 30 / 40 | 39 / 34 / 45 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 15% | 37 / 32 / 42 | 41 / 35 / 47 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 10% | 29 / 24 / 34 | 32 / 27 / 37 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 12.5% | 30 / 25 / 35 | 33 / 28 / 39 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 15% | 31 / 26 / 36 | 35 / 29 / 41 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 10% | 31 / 26 / 35 | 34 / 29 / 39 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 12.5% | 32 / 27 / 37 | 35 / 30 / 41 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 15% | 33 / 28 / 38 | 37 / 31 / 43 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 10% | 34 / 29 / 39 | 37 / 32 / 43 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 12.5% | 35 / 30 / 40 | 39 / 33 / 44 |
| **standard pair (adopted)** | W18 measured 522.7 × 140.4 µm | 15% | 36 / 31 / 42 | 41 / 35 / 46 |
| columns (reference) | W10 budget 485 × 121 µm | 10% | 34 / 28 / 40 | 38 / 32 / 45 |
| columns (reference) | W10 budget 485 × 121 µm | 12.5% | 35 / 29 / 41 | 40 / 33 / 47 |
| columns (reference) | W10 budget 485 × 121 µm | 15% | 37 / 31 / 43 | 42 / 35 / 50 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 10% | 39 / 34 / 45 | 44 / 38 / 50 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 12.5% | 41 / 35 / 47 | 46 / 40 / 53 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 15% | 43 / 37 / 49 | 49 / 42 / 56 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 10% | 34 / 29 / 40 | 39 / 32 / 45 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 12.5% | 36 / 30 / 42 | 41 / 34 / 48 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 15% | 38 / 32 / 44 | 43 / 36 / 50 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 10% | 36 / 31 / 42 | 41 / 35 / 48 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 12.5% | 38 / 32 / 44 | 43 / 36 / 50 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 15% | 40 / 34 / 46 | 45 / 38 / 53 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 10% | 39 / 34 / 45 | 44 / 38 / 50 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 12.5% | 41 / 35 / 47 | 46 / 40 / 53 |
| columns (reference) | W18 measured 522.7 × 140.4 µm | 15% | 43 / 37 / 49 | 48 / 42 / 56 |

Pitch and BF16 sources:

- **W18 measured pitch:** W10's p5 abstract tiled with an 8.64 µm pin channel (`claude/w18-die-assembly` d1e3c0aa), ×1.25 area.
- **BF16 columns:** 1,024 pairs at W10's planned outline of 1,063.7 × 131.76 µm in this table; the product row uses W10b's 1,002.89 × 142.56 µm column outline with the 510.84 × 126.9 µm q pair (step 5 below).
- **Standard pair (W10, adopted):** 16 BF16 weights per word, read once per 8 cycles into 2 exact BF16 multipliers per macro. It is exact, costs about +1.2 k µm² per pair (a closure risk at 85–87% utilisation), and adds 48 cycles per layer to `wo_a`.

At the ruled basis, **today's 28 stages do not fit a layer die**.

### Priced points (`points`)

| Point | Clock GHz | Stages / dies | AR tok/s | MTP tok/s | Saturated AR | Gated mJ, B = 1 / saturated |
|---|---:|---|---:|---:|---:|---:|
| as placed (188 dies, BF16 columns in the model's timing, TT) | 1.03 | 28 / 188 | 3,748 | 5,811 | 77,516 | 434 / 200 |
| BF16 lever: columns | 1.03 | 35 / 180 | 3,712 | 5,787 | 88,262 | 427 / 191 |
| BF16 lever: standard_pair | 1.03 | 29 / 156 | 3,717 | 5,705 | 87,637 | 408 / 196 |
| BF16 lever: hub_unit | 1.03 | 30 / 160 | 3,737 | 5,804 | 77,600 | 409 / 196 |
| 28 stages (stage-count comparison) | 1.03 | 28 / 152 | 3,722 | 5,709 | 76,962 | 405 / 199 |
| 34 stages (stage-count comparison) | 1.03 | 34 / 176 | 3,692 | 5,688 | 77,180 | 425 / 194 |
| density asap7 | 1.03 | 24 / 120 | 3,742 | 5,723 | 76,758 | 357 / 193 |
| density roma | 1.03 | 34 / 192 | 3,692 | 5,688 | 77,180 | 456 / 200 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ideal depths, no concurrency cap | 1.2 | 37 / 188 | 4,205 | 6,626 | 95,792 | 418 / 203 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: 50% field-concurrency cap (W18, adopted) | 1.2 | 37 / 188 | 3,896 | 5,485 | 92,256 | 438 / 207 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: cap + W11 hub latency inventory (estimates) | 1.2 | 37 / 188 | 3,667 | 5,381 | 92,256 | 454 / 207 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: cap + measured FP32 add: chain and element adds 8 stages | 1.2 | 37 / 188 | 2,730 | 4,566 | 90,676 | 548 / 209 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED (AGENTS.md c0894b1c): cap + 1.2 GHz streaming domain (LAT-7 adds, W11: 1,208 MHz SS) + 0.9 GHz chain domain (LAT 3), W18 ratio-FIFO CDC | 1.2 | 37 / 188 | 3,492 | 5,052 | 90,025 | 467 / 209 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 LAT-4 serial mul | 1.2 | 37 / 188 | 3,332 | 4,964 | 90,025 | 481 / 209 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) | 1.2 | 37 / 188 | 3,156 | 4,875 | 90,025 | 498 / 209 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) | 1.2 | 37 / 188 | 3,178 | 4,889 | 90,025 | 496 / 209 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass) | 1.2 | 37 / 188 | 3,153 | 4,859 | 90,025 | 498 / 209 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass) + W11 VM-H (12/12/12 slow stages, SU op +36.7 / red +44.9, issue x1.169) | 1.2 | 37 / 188 | 2,697 | 4,518 | 89,148 | 552 / 210 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass) + W11 VM-H (12/12/12 slow stages, SU op +36.7 / red +44.9, issue x1.169) + W10b tiles (q 510.84 x 126.9, BF16 column 1002.89 x 142.56 um) and the VM-H hub block (SU+VM 38.95 mm2): one stage re-fit -- REFERENCE (measured VM-H) | 1.2 | 41 / 208 | 2,680 | 4,475 | 89,096 | 599 / 217 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass) + W11 C_rotate VM, square layout (8/8/8 slow stages, SU op +37 / red +29, issue x1.0) + W10b tiles (q 510.84 x 126.9, BF16 column 1002.89 x 142.56 um) and the C_rotate hub block (SU+VM 38.60 mm2) -- SUPERSEDED (unplaced geometry) | 1.2 | 41 / 208 | 2,737 | 4,549 | 89,972 | 590 / 216 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass) + W11 C_rotate VM on W18b's compact hub (x 8 / scatter 7 / collective 13 slow stages, SU op +42 / red +32, issue x1.0) + W10b tiles (q 510.84 x 126.9, BF16 column 1002.89 x 142.56 um) and the C_rotate hub block (SU+VM 38.60 mm2): one stage re-fit | 1.2 | 41 / 208 | 2,690 | 4,513 | 89,972 | 597 / 216 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass) + W11 C_rotate VM on W18b's compact hub (x 8 / scatter 7 / collective 13 slow stages, SU op +42 / red +32, issue x1.0) + W10b tiles (q 510.84 x 126.9, BF16 column 1002.89 x 142.56 um) and the C_rotate hub block (SU+VM 38.60 mm2): one stage re-fit + lane-local operator fusion (conservative; modelled; RTL pending) | 1.2 | 41 / 208 | 2,838 | 4,618 | 89,972 | 576 / 216 |
| PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, light lane 929 MHz) + W18b shrunk-die interim crossings (669 mm2) + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass) + W11 C_rotate VM on W18b's compact hub (x 8 / scatter 7 / collective 13 slow stages, SU op +42 / red +32, issue x1.0) + W10b tiles (q 510.84 x 126.9, BF16 column 1002.89 x 142.56 um) and the C_rotate hub block (SU+VM 38.60 mm2): one stage re-fit + lane-local operator fusion, optimistic (BOUND; modelled; RTL pending) | 1.2 | 41 / 208 | 2,879 | 4,646 | 89,972 | 570 / 216 |

**More stages buy no throughput.** 28 → 34 stages costs 0.8% AR (+2.2 µs of hops) and leaves the saturated rate flat (76,962 vs 77,180). The reason is that the layer-20 index scan, which does not split, sets the stage period at about 13 µs.

### Clock plan at SS (user decisions 2026-09-30; adopted in AGENTS.md c0894b1c)

**Power accounting:** the per-pair ICG is adopted (W18 / power-cal). Idle pairs pay leakage only, and a busy pair's clock is dynamic energy. An interim 807 W layer-die figure came from charging every idle pair's ungated clock; it was corrected before landing. Each product row carries `cooling`, with the ungated form kept for reference.

**Adopted design:** a 1.2 GHz streaming domain and a 0.9 GHz serial-chain domain.

- **Streaming domain (1.2 GHz):** the ROM field and its elements with LAT-7 adds (W11: 1,208 MHz SS, 5.79 ns an add), the index scan and the attention tiles.
- **Serial-chain domain (0.9 GHz):** the SU, SFU, softplus, reducer, Sinkhorn, and the VM-H rotate network and group tiles. The product prices W11's MEASURED serial build (`claude/w11-suclose` ddd2f725): the SU light lane closes at 1.111 ns SS / FF hold, 60/25 (929 MHz), with a 5-cycle multiply and a 4-cycle add.
- **Crossings:** CDC at the VM port both ways, W18's ratio FIFO: 4 slow cycles fast→slow, 5 fast cycles slow→fast.
- **Other constraints:** a 50% field-concurrency cap (W18 peak current) and a 256-cycle pre-ramp (W18 droop).
- **Stage count:** macros are 4096m8 × 2 per slot, so the product basis is 41 stages / 208 dies (8 head dies).

**Named steps of the W16b passes (2026-09-30 / 10-01).** Each row adds one change to the row above it; the last row is the product.

1. **W11's measured serial build** (`claude/w11-suclose` ddd2f725). The 0.9 GHz units were priced at the model's 3-stage-add depths, plus one cycle a node for the LAT-4 multiply (a lower bound). They now use W11's measured depths in 0.9 GHz cycles: linear op 21 → 30, exp 49 → 71, sigmoid/silu 71 → 94, rsqrt 37 → 58, sqrt(softplus) 162 → 216, Engram gate 104 → 127, divide unchanged, and reducer tap 26 → 35 plus 3 → 4 cycles a tree level. The Sinkhorn unit is outside the serial build, so it keeps the one-cycle bound; its SFU front (row max and exp) takes the exp change (root-accepted).
2. **W18b's interim shrunk layer die** (`claude/w18-die-assembly` 996f7982). Root ruled that the die be sized to the product's 5,289 pairs a die plus about 10%, not the old pack's 7,628 slots. W18b's interim die is 669 mm² with 5,968 pair and 1,160 BF16 slots, routed with no overflow. Its crossings replace the old ones: expert trunks 63 cycles (was 76), collective to SerDes 45 (was 48), and the field regions at the die's linear scale 0.9062. Die area, cost and power stay on the 815 mm² ledger until the p12 floorplan lands. The √-area sensitivity of the previous pass is superseded.
3. **W11's streaming-unit depths at 1.2 GHz** (`claude/w11-stream` 540ef71c; the chunk and tile routes are still running). Indexer key to score 48 → 100 (+52), attention tile 33 → 72 (+39) and bank guard 20 → 44 (+24), each paid once a scores pass and once a p.v pass (W11: engine pipeline depths; the p.v pass reuses the tile).
4. **W11's VM-H distributed VM** (`claude/w11-vmh-land` 3cc18731, `results/uarch/w11_vm_options.json`, H_rtl). The client stages replace VM_DIST's 6/6/6 one-for-one in 0.9 GHz cycles at 748 µm a stage: x gather, result scatter and collective write 12/12/12. Every SU op pays the full-shape L0 program's per-op network average: +36.7 slow cycles a vector op, +44.9 a reduction, and issue × 1.169. These already contain the control broadcast (5) and the result tree (8), and the graph's SU nodes carry no separate broadcast or return stages, so nothing is counted twice (W11's +5.0% die-decode figure is the reduced vehicle at older stage counts, a correctness and hold-mechanism gate, not a full-shape rate; the full-shape L0 program, where 48 of 62 ops need the network, is this row's basis).
5. **One stage re-fit: W10b's tiles and the measured VM-H hub block — REFERENCE row.** The q pair widens to 510.84 × 126.9 µm (was 476.28; p12q3 failed CTS legalisation at 91–93% strip utilisation) and the BF16 column pair is 1,002.89 × 142.56 µm at density 0.5; latency is unchanged (BF16 split 8×4 + 8×4, still 5 cycles). These are floorplan sizes; routed closure (p12q4, c5) is pending. The tiles alone fit 39 stages. The hub then carries W11's measured VM-H SU+VM block, 38.951 mm² at 6,365 × 6,119 µm (128 tiles of 8 lanes and 12 VM SRAMs), in place of the lane-only 14.249 mm² stream unit (the measured light lane is 2.3× the ledger's). With the re-fit's 5% power-switch allowance the slot field gives up 25.9 mm². Dies are free, so the stage fit grows instead of the die: 41 stages, 208 dies. Root kept this as the measured VM-H reference and did not promote it.
6. **W11's C_rotate VM on W18b's compact hub** (root rulings 2026-10-01). C_rotate keeps the VM in a central strip: no issue penalty (ratio 1.0), so it wins the saturated rate. W18b placed it compactly (`claude/w18-die-assembly` 32155a8f: a 2,163 × 7,273 µm VM strip between two 1,787 µm SU halves), and W11 re-derived its stages there (`claude/w11-crot` `v41_vm_crot_stages.json`, provisional; 748 µm a stage at 1.111 ns): broadcast 7, operand read 18, element write 17, result 7, x gather 8, scatter 7, collective write 13, so **+42 slow cycles an op and +32 a reduction**. The rotate realises every (bank slot, lane) pair, so every op pays the hub's worst bank → lane run (10,735 µm), not the 1,787 µm lane-to-strip distance. W11's earlier square layout priced 37 / 29 (2,737 AR); it was never placed and is **superseded**. The block is 38.601 mm², the slot field less 25.57 mm²: **41 TP-4 stages** + 8 head + 36 table = **208 dies** (8 head dies on the model's storage-only rule; a W18b head re-fit may restore 4). The owner file is `results/arch/v41_stage_owner_product.json`. Measured VM-H stays the comparison row.
7. **Lane-local operator fusion, the PRODUCT** (USER RULE, AGENTS.md a6e86359; **modelled; RTL pending**). A dependent SU op pays the VM network only at a chain boundary (a VM read when an input comes from a matvec, collective, scan, select, Sinkhorn or hop; a VM write when a consumer is outside the SU) and at a true cross-lane move (a reduction's result tree, a quantiser's segmented absmax tree, a RoPE rotation). Conservative mode (the headline) keeps the control broadcast on every op and RoPE as a rotation: 2,690 → **2,838 AR**, 4,513 → **4,618 MTP** (τ 3.649). Optimistic mode (one broadcast a chain, RoPE pairs lane-local) is the bound: 2,879 AR, 4,646 MTP.

| Step | AR tok/s | MTP tok/s, τ 3.649 | MTP tok/s, τ 3.78 | Saturated tok/s |
|---|---:|---:|---:|---:|
| previous product (LAT-4 bound) | 3,332 | 4,964 | 5,142 | 90,025 |
| 1. measured serial build | 3,156 | 4,875 | 5,050 | 90,025 |
| 2. shrunk-die crossings | 3,178 | 4,889 | 5,065 | 90,025 |
| 3. streaming depths | 3,153 | 4,859 | 5,033 | 90,025 |
| 4. VM-H distributed VM | 2,697 | 4,518 | 4,681 | 89,148 |
| 5. W10b tiles + VM-H hub re-fit (comparison row) | 2,680 | 4,475 | 4,635 | 89,096 |
| C_rotate square layout, 37 / 29 (superseded, unplaced) | 2,737 | 4,549 | 4,712 | 89,972 |
| 6. C_rotate on the compact hub, 42 / 32 | 2,690 | 4,513 | 4,675 | 89,972 |
| 7. + lane-local fusion, conservative (PRODUCT; modelled, RTL pending) | 2,838 | 4,618 | 4,784 | 89,972 |
| 7. bound: fusion, optimistic | 2,879 | 4,646 | 4,813 | 89,972 |

**The VM waterfall** (`--vm-waterfall`, `results/uarch/v41_vm_waterfall.json`; root 2026-10-01). From the pre-VM-H product to the measured VM-H reference: -472.8 tok/s AR. The VM-H steps are cumulative at 37 stages; the per-op network latency on the SU chain is most of it.

| Step | AR tok/s | Δ AR | MTP tok/s, τ 3.649 | Stages / dies |
|---|---:|---:|---:|---|
| previous product (VM_DIST 6/6/6, ledger hub, W10 q 476 um) | 3,153.0 |  | 4,858.8 | 37 / 188 |
| VM-H x gather 6 -> 12 stages | 3,129.9 | -23.1 | 4,840.4 | 37 / 188 |
| VM-H result scatter 6 -> 12 | 3,107.1 | -22.8 | 4,822.2 | 37 / 188 |
| VM-H collective write 6 -> 12 | 3,092.9 | -14.2 | 4,814.2 | 37 / 188 |
| VM-H SU op network latency +36.7 slow cycles | 2,781.7 | -311.2 | 4,608.1 | 37 / 188 |
| VM-H reduction network latency +44.9 | 2,705.1 | -76.6 | 4,556.0 | 37 / 188 |
| VM-H issue x1.169 | 2,697.1 | -8.0 | 4,518.3 | 37 / 188 |
| W10b tiles (q 510.84 um): 37 -> 39 stages | 2,689.4 | -7.7 | 4,497.2 | 39 / 200 |
| VM-H hub block 38.95 mm2: 39 -> 41 stages (measured VM-H reference) | 2,680.2 | -9.2 | 4,474.8 | 41 / 208 |

**VM levers** at the product basis (W10b tiles, the block's hub area), against the measured VM-H reference:

| Lever | AR tok/s | vs VM-H reference | MTP tok/s, τ 3.649 | Stages / dies |
|---|---:|---:|---:|---|
| (a) C_rotate, W11 square layout (37 / 29): SUPERSEDED, unplaced geometry | 2,736.7 | +2.1% | 4,548.9 | 41 / 208 |
| (a) C_rotate on W18b's compact hub (42 / 32), unfused: PRODUCT basis | 2,690.4 | +0.4% | 4,512.9 | 41 / 208 |
| (a) C_rotate on W18b's compact hub, fused conservative: PRODUCT (modelled; RTL pending) | 2,837.8 | +5.9% | 4,618.3 | 41 / 208 |
| (a) C_rotate on W18b's compact hub, fused optimistic: BOUND | 2,878.8 | +7.4% | 4,646.3 | 41 / 208 |
| (a) VM-H, fused conservative (comparison) | 2,825.8 | +5.4% | 4,575.5 | 41 / 208 |
| (a) C_rotate on the compact hub at 481 um a stage (61 / 46; sensitivity: the 1.2 GHz reach) | 2,519.9 | -6.0% | 4,374.4 | 41 / 208 |
| (b) SU 2,048 / SFU 512 lanes, network unchanged (optimistic; block ~63 mm2) | 2,682.4 | +0.1% | 4,507.1 | 44 / 220 |
| (b) SU 2,048 / SFU 512 lanes, network stages x1.41 | 2,541.8 | -5.2% | 4,394.2 | 44 / 220 |
| (c) flat VM as buildable = W11 option C (central crossbar, 74.66 mm2) | 2,492.3 | -7.0% | 4,294.8 | 45 / 224 |
| (c) flat VM with no network (NOT physical; reference) | 3,130.0 | +16.8% | 4,808.6 | 41 / 208 |
| (d) VM-H per-op network latency -25% | 2,754.5 | +2.8% | 4,526.7 | 41 / 208 |
| (d) VM-H per-op network latency -50% | 2,833.2 | +5.7% | 4,579.8 | 41 / 208 |
| (d) VM-H client stages 12 -> 8 only | 2,704.0 | +0.9% | 4,495.1 | 41 / 208 |
| (d) VM-H issue x1.169 -> 1.0 only | 2,688.1 | +0.3% | 4,511.9 | 41 / 208 |
| (d) W11's 3,850 um sensitivity (one-way 8, op / red +21): SUPERSEDED -- the rotate pays the hub diameter | 2,875.0 | +7.3% | 4,644.2 | 41 / 208 |

More lanes or VM ports buy nothing because the SU chain is latency-bound (removing the 1.169 issue ratio alone gains 0.3%). The only buildable flat VM is W11's central crossbar, slower and twice the area. The rate is in the per-op network latency: about 8.5 tok/s a slow cycle. The compact C_rotate placement is W11's distance sensitivity, not yet a placed design.

**K arbiter with W18b's MERGE2 + HEADREG fix** (`claude/w18-die-assembly` e909156c; MERGE2 alone fails SS by 212 ps; MERGE2 + HEADREG is equivalence-clean 54/54 with P&R running; +2 on the round trip: 20/16/14/10/10/14/16/20 cycles over regions 0–7): -0.448% worst region, -0.336% region mean. It is a row only, not in the product.

**Qwen layer 0: RTL against the model** (`qwen_l0_rtl_vs_model`). W12b measured TP-4 layer 0 bit-exact on 4 dies (G 6,144, SU width 64, SS wire stages, original ME adders; `claude/w12-qwen-rom` 42ecf382) at 4,669 cycles. At that configuration the model prices 2,460 cycles of layer chain plus 2 × 442 all-reduce, 3,344 in all: 28.4% short.

W12b's per-instruction trace (a17a3c79) attributes the gap. Each all-reduce is 2 serialized 128-word TP segments (the count field is 8 bits), about 497 cycles each, so 991 an all-reduce: 1,098 of the gap. The body without collectives is 2,687 cycles against the model's 2,460 (× 1.0923, ME latency per op). Stage spans: QKV 431, attention 87, PV + O ME 769, O all-reduce 991, post 69, gate/up 528, SiLU 119, down 480, down all-reduce 991, tail 222.

Two attributed rows replace the single calibrated ratio. **As built:** the per-layer body × 1.0923 and the all-reduces at the measured 991 cycles give 6,222 tok/s. **Body only:** the same body with the all-reduces at the model's latency gives 7,921 tok/s; it waits on W12b's one-segment all-reduce (79783ff9, not yet measured). The model row is 8,460 tok/s. All three include KV_PREP (+216 cycles a token), and W12b's LAT-7 ME +54 is counted once.

**Clock-domain cases** (`clock_domain_cases`, all with the cap; the measured W11 FP32 add prices every serial chain):

| Case | AR tok/s | MTP tok/s | Saturated AR | Gated mJ, B = 1 / saturated | Top of the critical path (µs) |
|---|---:|---:|---:|---:|---|
| a: all 1.2 GHz, chain adds 8 stages | 2,669 | 4,325 | 89,560 | 593 / 215 | attn.wo_a 21.17, attn.out_allreduce 17.07, ffn.combine_allreduce 17.07 |
| a: all 1.2 GHz, chain adds 9 stages | 2,531 | 4,230 | 89,560 | 616 / 215 | attn.wo_a 21.17, ffn.softplus_sqrt 19.1, attn.out_allreduce 17.07 |
| b: 1.2 GHz field (LAT 7) + 0.9 GHz chain units (LAT 3), W18 CDC | 3,370 | 4,683 | 88,485 | 508 / 216 | attn.wo_a 21.33, attn.out_allreduce 17.07, ffn.combine_allreduce 17.07 |
| b: 1.2 GHz field (LAT 7) + 0.8 GHz chain units (LAT 3), W18 CDC | 3,246 | 4,600 | 87,856 | 521 / 217 | attn.wo_a 21.33, attn.out_allreduce 17.07, ffn.combine_allreduce 17.07 |
| c: all 0.9 GHz, LAT 3 | 2,870 | 3,737 | 71,927 | 549 / 209 | attn.wo_a 27.87, attn.out_allreduce 22.76, ffn.combine_allreduce 22.76 |

- **The measured add overturns "everything at 1.2 GHz".** At 1.2 GHz an add needs 8–9 stages (6.7–7.5 ns), so the serial chains slow down more than the clock gains.
- **The split design keeps the chains on the 906 MHz LAT-3 add**, and gives the best per-user rate with a saturated rate within a few percent.
- **The stage period is set by the layer-20 index scan throughout.**

**Droop pre-ramp energy** (W18 67b0bd49), on the adopted product:

- 50% cap + 256-cycle pre-ramp: +96.4 mJ per token, i.e. 672.3 / 312.3 mJ at B = 1 / saturated; ramped only after an idle gap longer than 256 cycles: +104.2 mJ.
- 1,024-cycle pre-ramp, no cap: +767.5 mJ per token, i.e. 1343.4 / 983.4 mJ at B = 1 / saturated; ramped only after an idle gap longer than 256 cycles: +829.5 mJ.
- 256-cycle pre-ramp, no cap (64 mV at 2 pH: fails 35 mV): +192.9 mJ per token, i.e. 768.7 / 408.7 mJ at B = 1 / saturated; ramped only after an idle gap longer than 256 cycles: +208.4 mJ.

The priced graph has 8.15 field-op starts per layer die per token, of which 6.05 follow an idle gap longer than 256 cycles (ASSUMED decay constant). W18's count was 6. The 1,024-cycle no-cap pre-ramp is rejected on energy.

**SS-clock curve** (`ss.curve`): AR / MTP / saturated tok/s against the logic's SS clock, capped at each macro's SS limit (the older single-domain basis, for reading off the depth):

| Depth | Logic SS GHz: AR tok/s |
|---|---|
| 8192m8 (29 stages) | 0.70: 2,556, 0.75: 2,726, 0.80: 2,899, 0.85: 3,066, 0.90: 3,234, 1.35: 3,292 |
| 4096m8 (30 stages) | 0.70: 2,554, 0.75: 2,724, 0.80: 2,896, 0.85: 3,062, 0.90: 3,230, 0.95: 3,394, 1.00: 3,557, 1.05: 3,717, 1.10: 3,869, 1.15: 4,015, 1.20: 4,166, 1.35: 4,185 |
| 2048m4 (31 stages) | 0.70: 2,552, 0.75: 2,721, 0.80: 2,892, 0.85: 3,059, 0.90: 3,226, 0.95: 3,390, 1.00: 3,552, 1.05: 3,712, 1.10: 3,863, 1.15: 4,009, 1.20: 4,160, 1.25: 4,303, 1.30: 4,445, 1.35: 4,514 |

**K arbiter** (W18: 7 + 2 × (hops − 1) cycles). There are 56 HBM-touching nodes on the path. The cost is -0.291% at 1 mm reach (13 cycles worst) and -0.336% at the 0.75 mm SS reach (15 cycles). It is not yet in the product.

### Engram table dies

- **Die count:** 72 → 36 at the storage-only density (5.67 GB per die); 20 at ASAP7, 48 at ROMA. A table die carries no MAC strips, hub or HBM.
- **Hops and latency: no change.** The path is a table package, then one 51.2T switch, then a layer package.
  - The rack's Engram L1 path is 1.874 µs, an upper bound for any table-die count, against 3.57 µs of slack.
  - On the priced DAG, the Engram value arrives at 1.34 µs and meets the residual at 5.01 µs.
  - No Engram node is on the critical path at any stage count tested.
- **Load:** 3.8 rows per die per layer (expected maximum), and 0.2% of a table package's lanes at saturation.

### Qwen ROM: option C (root / user decision, 2026-09-30)

The AR-only ROM does not fit the two-reticle package at 75 + ECC: it needs 746.5 of 560 mm² of tile array per die, and 883.3 at ROMA. `qwen_rom_options()` prices the alternatives, each with the busiest die's TP-k slice replayed, at 8K with W12 wires.

**W12 wires give 9,194 tok/s at the 2-die reference, where the economics section's W5 wires gave 9,851. W12 is used.**

| Option | G per die | tok/s AR | Saturated | Users | mJ, B = 1 / saturated | Hardware $ | Exchange per all-reduce |
|---|---:|---:|---:|---:|---:|---:|---|
| A: 3 dies in ONE package (12 stacks; not demonstrated), TP-3 over UCIe | 4,096 | 9,096 | 15,895 | 357 | 91 / 85 | 8,625 | 76.0 cycles (ASSUMED from the W15 TP-2 measurement: a one-shot to 2 peers over direct UCIe adds one FP32 add stage) |
| B: 3 single-die packages (4 stacks each, H100-class), TP-3 over board links | 4,096 | 7,433 | 15,895 | 357 | 94 / 85 | 11,065 | 446.8 cycles (MEASURED on the V4.1 TP-4 group) |
| C: 2 B200-class packages (2 dies + 8 stacks each), TP-4 with one package crossing | 6,144 | 9,368 | 23,842 | 536 | 98 / 85 | 12,113 | 446.8 cycles (MEASURED on the V4.1 TP-4 group) |
| D: the 2-die reference: fits only with the compute-in-ROM UPSIDE (148 Mbit/mm2; assumed cell multiplier, unimplemented mechanism) | 6,144 | 9,194 | 11,921 | 268 | 88 / 85 | 6,056 | 71.0 cycles (MEASURED) |

- **G = 6,144 (W12's die, layer 0 exact) is the product.** It uses 529.5 of 560 mm² (5.45% margin).
- **the TP-4 token is not lane-bound: G 6,144 -> 6,336 buys +0.04% (9,367.6 -> 9,371.4 tok/s) and the saturated rate is KV-stream bound at every G >= 4,096, so extra area does not buy per-user speed; legal G step is 64 groups (the program's embedding-word rule).**
- **ROMA-safe sensitivity:** G = 4,928 at 8,673 tok/s (−7.4%).
- **At 1.2 GHz SS:** C runs at 10,262 tok/s, and 10,556 with W12's TP-4 wire count (66 cycles per ME op, including the SS pin-capture register).
- **A smaller die** holds the placed tiles, spine, PHYs and UCIe with a 10% margin:
  - W12 estimate 308 mm2 (ASAP7 tiles): 443.9 mm², yield 0.661, $210.7 per die, $10,643 for 4 dies and 2 packages.
  - W12 estimate 359 mm2 (ASAP7 tiles): 504.0 mm², yield 0.6276, $256.3 per die, $10,825 for 4 dies and 2 packages.
  - storage-only 75 + ECC tile need (the ruled basis): 622.5 mm², yield 0.568, $360.8 per die, $11,243 for 4 dies and 2 packages.
  - 815 mm2 reference: 815.0 mm², yield 0.4863, $578.2 per die, $12,113 for 4 dies and 2 packages.

**Qwen context sweep** (`qwen_context_sweep`). W12b context audit (claude/w12-qwen-rom b4d2715f): KV read 18,432 x T bytes a token a die; HBM binds from ~32K (W12b ~1.4k tok/s at 128K, ~0.9k at 200K with SW 1,024, matching this sweep); 32K needs parameters and 2 larger SRAMs (+~10 mm2 a die); 128K and 200K need a 27-bit address and a larger VM (or head-serial scores).  Qwen3-8B is natively 32K and 128K with YaRN; 200K is beyond official support.  FP8 KV (baseline); the FP4/INT4-KV rows halve the KV bytes and are QUALITY-UNTESTED

| Context | Design | AR tok/s | KV bytes per token | KV read µs | Binding | Users | Saturated | mJ, B = 1 / saturated |
|---:|---|---:|---:|---:|---|---:|---:|---:|
| 8,192 | ROM option C (4 stacks a die, FP8 KV) | 9,384 | 603,979,776 | 41.9 | compute chain | 536 | 23,842 | 97.9 / 85.0 |
| 8,192 | ROM option C, 6 stacks a die | 9,384 | 603,979,776 | 28.0 | compute chain | 804 | 35,763 | 97.9 / 82.2 |
| 8,192 | ROM option C, FP4/INT4 KV (quality untested) | 9,384 | 301,989,888 | 21.0 | compute chain | 1,072 | 39,531 | 64.6 / 48.3 |
| 8,192 | Qwen HBM tier 3 (2 x 4-stack right-sized dies), AR | 880 | 603,979,776 | 83.9 | HBM stream | 255 | — | — / — |
| 8,192 | Qwen3-8B on 1x B200, FP8 (tier 2, calibrated), AR | 331 | 603,979,776 | 115.1 | — | 255 | — | 2,081.4 / — |
| 32,768 | ROM option C (4 stacks a die, FP8 KV) | 5,960 | 2,415,919,104 | 167.8 | KV stream | 134 | 5,960 | 310.0 / 310.0 |
| 32,768 | ROM option C, 6 stacks a die | 7,457 | 2,415,919,104 | 111.8 | compute chain | 201 | 8,941 | 303.3 / 298.8 |
| 32,768 | ROM option C, FP4/INT4 KV (quality untested) | 7,457 | 1,207,959,552 | 83.9 | compute chain | 268 | 11,921 | 170.0 / 160.0 |
| 32,768 | Qwen HBM tier 3 (2 x 4-stack right-sized dies), AR | 721 | 2,415,919,104 | 335.6 | HBM stream | 63 | — | — / — |
| 32,768 | Qwen3-8B on 1x B200, FP8 (tier 2, calibrated), AR | 297 | 2,415,919,104 | 460.3 | — | 63 | — | 2,319.3 / — |
| 131,072 | ROM option C (4 stacks a die, FP8 KV) | 1,490 | 9,663,676,416 | 671.1 | KV stream | 33 | 1,490 | 1,210.2 / 1,210.2 |
| 131,072 | ROM option C, 6 stacks a die | 2,235 | 9,663,676,416 | 447.4 | KV stream | 50 | 2,235 | 1,165.4 / 1,165.4 |
| 131,072 | ROM option C, FP4/INT4 KV (quality untested) | 2,980 | 4,831,838,208 | 335.5 | KV stream | 67 | 2,980 | 610.1 / 610.1 |
| 131,072 | Qwen HBM tier 3 (2 x 4-stack right-sized dies), AR | 418 | 9,663,676,416 | 1,342.4 | HBM stream | 15 | — | — / — |
| 131,072 | Qwen3-8B on 1x B200, FP8 (tier 2, calibrated), AR | 211 | 9,663,676,416 | 1,841.2 | — | 15 | — | 3,270.7 / — |
| 200,000 | ROM option C (4 stacks a die, FP8 KV) | 977 | 14,745,600,000 | 1,024.0 | KV stream | 21 | 977 | 1,841.3 / 1,841.3 |
| 200,000 | ROM option C, 6 stacks a die | 1,465 | 14,745,600,000 | 682.7 | KV stream | 32 | 1,465 | 1,773.1 / 1,773.1 |
| 200,000 | ROM option C, FP4/INT4 KV (quality untested) | 1,953 | 7,372,800,000 | 512.0 | KV stream | 43 | 1,953 | 925.7 / 925.7 |
| 200,000 | Qwen HBM tier 3 (2 x 4-stack right-sized dies), AR | 323 | 14,745,600,000 | 2,048.4 | HBM stream | 10 | — | — / — |
| 200,000 | Qwen3-8B on 1x B200, FP8 (tier 2, calibrated), AR | 175 | 14,745,600,000 | 2,809.5 | — | 10 | — | 3,937.9 / — |

**KV scale-out at 200K** (`qwen_helix_200k`). Extra HBM + attention dies hold context slices, with an exact ordered partial-softmax merge; the weights stay on the 4 ROM dies:

- +0 KV dies (4 total): 977 tok/s per user, 21 users.
- +4 KV dies (8 total): 1,921 tok/s per user, 43 users.
- +8 KV dies (12 total): 2,858 tok/s per user, 65 users.
- +16 KV dies (20 total): 3,040 tok/s per user, 109 users.

### Right-sized HBM dies and the V4.1 HBM die count

**Shoreline** (root): the H200 is GH100 (~814 mm²) with six HBM3e stacks, three per long edge, which gives 8.5 mm of edge per PHY. Six stacks per die is demonstrated; more is not.

| Die | Stacks | Outline mm | Area mm² | Package |
|---|---:|---|---:|---|
| qwen | 4 | 19.0 × 13.99 | 265.8 | 2 dies + 8 stacks (CoWoS-L, B200 class) |
| qwen | 6 | 27.5 × 14.14 | 388.9 | 1 die + 6 stacks (CoWoS-S, H100/H200 class) |
| v41 | 4 | 19.0 × 17.92 | 340.5 | 2 dies + 8 stacks (CoWoS-L, B200 class) |
| v41 | 6 | 27.5 × 15.5 | 426.2 | 1 die + 6 stacks (CoWoS-S, H100/H200 class) |
| v41 (12 mm PHY placeholder) | 4 | 26.0 × 13.42 | 349.0 | 2 dies + 8 stacks (CoWoS-L, B200 class) |
| qwen (12 mm PHY placeholder) | 6 | 38.0 × 10.59 | 402.5 | 1 die + 6 stacks (CoWoS-S, H100/H200 class) (exceeds the reticle) |

**V4.1 HBM sweep** (TP-N at 1.2 GHz for equal footing; 1M):

| Dies × stacks | Users at 1M | AR tok/s | MTP tok/s | Saturated AR | mJ, B = 1 / saturated | Capex $ |
|---|---:|---:|---:|---:|---:|---:|
| 7 × 4 (capacity minimum) | 60 | 1,370 | 2,579 | 4,760 | 1747 / 664 | 34,161 |
| 17 × 4 | 926 | 2,117 | 4,893 | 11,561 | 1910 / 664 | 60,091 |
| 24 × 4 | 1,531 | 2,413 | 5,339 | 16,321 | 2018 / 664 | 77,232 |
| 48 × 4 | 3,608 | 2,835 | 5,912 | 25,293 | 2408 / 678 | 139,464 |
| 96 × 4 | 7,763 | 3,146 | 6,294 | 25,293 | 3168 / 742 | 263,928 |
| 5 × 6 (capacity minimum) | 103 | 1,420 | 2,760 | 5,100 | 1694 / 653 | 35,141 |
| 11 × 6 | 882 | 2,108 | 4,879 | 11,221 | 1806 / 653 | 59,310 |
| 24 × 6 | 2,570 | 2,668 | 5,693 | 24,482 | 2055 / 653 | 111,677 |
| 48 × 6 | 5,685 | 3,023 | 6,147 | 25,293 | 2509 / 690 | 208,354 |
| 96 × 6 | 11,917 | 3,231 | 6,393 | 25,293 | 3422 / 765 | 401,707 |

- To hold 866 users at 1M, the comparator needs 17 dies × 4 stacks or 11 × 6.
- Its existing 811-user figure uses a pipelined busiest-die rule; under TP-96 it holds 7,763.
- W13 at SS pre-layout: an 8-stage fp32_add_rne_pipe breaks the IL = 8 circulating accumulator; IL = 16 gives V4.1 HBM ~2,500 AR (from ~2,920); a 7-stage adder keeps IL = 8 (W13 estimate, not priced here).

### Cost: die area with a yield model (`fab`), replacing the iso-package B200 price

- **Wafer:** $16,988 per N5 wafer (Khan and Mann, CSET 2020).
- **Yield:** D0 0.10/cm² (TSMC 2020 Technology Symposium), negative binomial with α = 3 (ASSUMED), no harvesting.
- **Packaging:** CoWoS-S $750, CoWoS-L $1,100, and $920 test and assembly per package (Raymond James via Silicon Analysts).
- **HBM3E:** $360 per stack.
- **NRE, via-programmable:** base sets + 1–2 coding masks per ROM die, and one full set per HBM die design, over 1,000 units.

### The comparison rule

The reference is the adopted V4.1 ROM product basis: 169,520 mm², $727,026 capex (low), and 19,421 W gated at the saturated AR rate. The HBM side runs at 1.2 GHz.

| Rule | HBM configuration | AR tok/s | MTP tok/s | Saturated AR | Users at 1M | mJ, B = 1 / saturated |
|---|---|---:|---:|---:|---:|---:|
| equal area | 5 × TP-96 (480 dies) | 3,146 | 6,294 | 126,464 | 38,815 | 9993 / 742 |
| equal cost (headline pairing) | 2 × TP-96 (192 dies) | 3,146 | 6,294 | 50,585 | 15,526 | 4874 / 742 |
| equal power | 1 × TP-96 (96 dies) | 3,146 | 6,294 | 25,293 | 7,763 | 3168 / 742 |

### Model caveats (`model_caveats`)

- **vm_per_op_latency:** Per-op network latency on the latency-bound SU chain was invisible in the throughput-style VM pricing. The VM was priced by port widths (vm_read_elems / vm_write_elems) and a few client wire stages, i.e. as bandwidth; the SU softmax / norm / Sinkhorn chains are dependent ops, so each op pays the VM network's full latency (control broadcast, operand read, element write or result tree).  W11's VM-H measured that at +36.7 slow cycles a vector op and +44.9 a reduction: -14.5% AR on the full-shape token, 82% of the 3,153 -> 2,680 drop (results/uarch/v41_vm_waterfall.json); more lanes or ports buy nothing (issue is not the bind).  Rule: any shared network on a dependent chain is priced as per-op latency on the chain, not as bandwidth.
- **rotate_span_is_the_hub_diameter:** A rotate network's latency is set by the hub's diameter, not by the lane-to-strip distance.  The rotate maps element slot p to lane (p - base) mod 1,024 and every (slot, lane) pair is realised by some base, so a fixed-latency strip pays the worst bank -> lane run on every op.  W18b's compact placement brought every lane within 1,787 um of the strip, yet C_rotate's per-op extra rose from the unplaced 37 to 42 (10,735 um bank -> lane at 748 um a stage).  Rule: price a network from the placed worst path of the access pattern it must serve, never from an unplaced geometry.

### Floorplan checks needed (coordinate through root)

- **W10:** a consolidated V4.1 layer die at the product basis: 4096m8 × 2 per slot, standard-pair BF16 at the 485 × 121 µm budget pitch with abutment pins, 30 stages' busiest-die macros, and the overhead in the edge ring. Also closure of the standard pair at +1.2 k µm².
- **W10 / W18:** an Engram table-die floorplan (about 628 mm² usable).
- **W13:** one right-sized HBM die: V4.1 with 4 stacks at 19.0 × 18.2 mm, on the legal 8.5 mm PHY.
- **W12:** the smaller Qwen die when the routed tile area lands.

