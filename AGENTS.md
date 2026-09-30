# Binding rules for every agent working in this repository

These rules come from the project owner and bind Codex, Claude and every sub-agent. The architectural statement is Table 5-2 of [docs/ARCHITECTURE_ATLAS.html](docs/ARCHITECTURE_ATLAS.html). The current plan is [docs/INTEGRATED_PHYSICAL_PLAN.md](docs/INTEGRATED_PHYSICAL_PLAN.md).

## Design method (adopted 2026-09-29)

1. **Microarchitecture model before build.** Before writing engine RTL or launching place and route, the block must be sized in the unified microarchitecture analytical model (`tools/uarch_model.py`, [docs/MICROARCH_MODEL.md](docs/MICROARCH_MODEL.md)). The model covers every design: Qwen3-8B ROM, Qwen3-8B HBM, DeepSeek-V4.1 ROM and DeepSeek-V4.1 HBM. For every block it states:
   - MACs per cycle, and compute and communication intensity;
   - bytes per cycle at every memory port;
   - bits per cycle across every boundary;
   - routing tracks needed against channel capacity;
   - replica count, and the multiplexer, demultiplexer and fanout cost those replicas imply;
   - area and floorplan slot fit;
   - latency contribution to the single-user token.
   Back-of-the-envelope numbers decide whether to build a block and how big. Place and route validates the model; it must never be where the architecture is discovered. A block whose composed latency is not in the model is not ready to build.
2. **Floorplan, then one hardened element, then replicate.** Transformers are regular: replicated layers, experts and heads. Each die is therefore a symmetric array of one element with a real macro abstract, replicated to the count the model requires. No undersized instance is presented as a design. Irregular operators (Sinkhorn/mHC, indexer, specialised attention) keep dedicated units where dedicated logic beats general compute on latency.
3. **HBM comparators replicate a GPU organisation; only ROM designs are novel.** HBM-weight designs use SM-like elements: Tensor-Core-style matrix units, register files and shared memory, L2 slices and shoreline HBM controllers. Use another established organisation, such as a systolic array, only where it is shown better. ROM designs place compute beside the weight banks.
4. **Focus.** Work goes to the highest-ranked item in the plan. Do not open parallel streams whose outputs are not composed by the model.

## Objective

Minimum single-user decode latency first. Aggregate throughput from independent requests is secondary, filling idle stages without hurting the single-user latency. Exact arithmetic (the golden rounding points and reduction orders) is mandatory.

## Engineering rules

- Evidence is committed, source-pinned records.
- Failed verdicts are never overwritten.
- Clock and uncertainty constraints are never relaxed without pricing the change.
- Sign-off corners (user decision, 2026-09-30):
  - A headline clock frequency must close setup at the SS corner and hold at the FF corner, under the 60 ps setup / 25 ps hold uncertainty policy.
  - TT closures are pathfinding evidence only, labelled as TT.
  - Memory macros are checked at SS with their own clk→q; results/uarch/v41_rom_depth_study.json has the ROM macro figures.
- Clock target (user decision, 2026-09-30): 1.2 GHz (0.833 ns) at SS for all logic in every design; the V4.1 ROM uses 4096-row macros, 2 per element slot. Bottleneck blocks are pipelined or parallelised to meet it, and each added latency cycle is reported to the model.
- Stage files by explicit path, never `git add -A`.
- Run long jobs in pinned clean worktrees, not in the main checkout.
- After editing any doc under `docs/`, regenerate the prose-figure census and sync its two untriaged-count annotations, then run `make check-figures`.
