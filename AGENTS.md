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
3. **Two proposed designs: the ROM accelerator and the HBM accelerator** (owner decision, 2026-10-03; supersedes the earlier "HBM comparators replicate a GPU organisation" rule). The ROM accelerator places compute beside the weight banks and targets dense small-to-medium models. The HBM accelerator is an inference accelerator, not a GPU: it adopts our architectural improvements (static scheduling without kernel launches or software synchronisation, direct die-to-die links, fused/asynchronous collectives, near-memory attention and index scan, lane-local fusion, and any other improvement that is exact and priced) and is pushed to the best design possible; it targets large MoE models. The previous GPU-organised HBM design (SM-like matrix units, register files, L2 slices, shoreline HBM controllers, only GPU-standard features) is kept as an ablation that shows where the gain comes from. Fairness rests on real state-of-the-art GPU baselines (measured or published H100/B200-class results with production software stacks, including their speculative decoding) at matched workload, precision and context, with comparisons at equal total silicon (counting HBM DRAM dies) and equal power.
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
- Clock target (user decision, 2026-09-30): 1.2 GHz (0.833 ns) at SS; the V4.1 ROM uses 4096-row macros, 2 per element slot. Bottleneck blocks are pipelined or parallelised to meet it, and each added latency cycle is reported to the model.
- Clock domains (root, 2026-09-30, from the measured FP32 add: 3.31 ns per add at LAT 3 against ~7 ns at the 8–9 stages 1.2 GHz needs):
  - The streaming domain runs at 1.2 GHz: ROM field and elements, index scan, attention tiles, links, the HBM service.
  - The serial-chain domain runs at 0.9 GHz (3:4) on the LAT-3 FP32 add: SU, SFU, softplus, Sinkhorn, reducers.
  - The model prices it at +28% AR against all-1.2 GHz.
- Operator fusion (user decision, 2026-10-01): dependent operations are chained through lane-local registers as far as possible. A value goes back to the vector memory (or any shared memory) only when another lane, unit or die needs it, or at a true cross-lane step (reduction, rotation, misaligned access). Per-op round trips through a memory network are a latency cost on serial chains. Price them in the model, and design them out.
- Dataflow levels (user decision, 2026-10-01). Every design adopts levels 1-5 and only those:
  1. lane-local fusion;
  2. producer results (field, collective, scan) staged at the hub edge, preferably in the clock-crossing FIFO, and delivered straight into lane registers;
  3. reductions on the arriving stream in the golden's tree order, with a pipelined scalar broadcast;
  4. the compiler interleaves independent chains to hide network latency;
  5. collective fusion (residual and norm partials carried with the all-reduce, consecutive collectives merged) and cut-through stage hops.
- Excluded:
  - level 6: algebraic reordering such as folding norm weights into the ROM or applying the norm scalar after the matvec. It changes rounding, so it needs a separate user decision and a quality check.
  - level 7: a spatial, Cerebras-style redistribution of vector work.
- No risky changes. Each item:
  - is bit-exact against the golden (class A), or a reordering the golden mirrors exactly;
  - sits behind an opt-in parameter, off by default, until its exact gate passes;
  - leaves pinned files byte-identical;
  - passes the hub routing-layer check;
  - is adopted only if the model prices it at 1% or more of per-user rate.
- No numerical, performance or place-and-route risk (user, 2026-10-01):
  - a lever is adopted only after its RTL measurement confirms a gain, and any new hardware closes at SS/FF in context. A lever that measures slower, or fails to close, is rejected rather than tuned.
  - a contract change (class C) needs the pre-committed PPL/MMLU rule plus a numerical-stability check: no NaN/Inf, no FP8 saturation beyond the current contract's, and error and selection-flip rates within the noise floor across depth and context.
  - Norm-after-matvec, rejected 2026-09-27, is now under that check (stream QC-NAM). It is adopted only on PASS.
- The GPU-organised HBM ablation takes only what a real GPU generation or its software stack has (register and TMEM-style epilogues, fused all-reduce plus norm, in-switch reduction, collective overlap). The HBM accelerator may adopt any exact, priced improvement, including ones first developed for the ROM accelerator.
- Stage files by explicit path, never `git add -A`.
- Run long jobs in pinned clean worktrees, not in the main checkout.

## Workflow habits (owner, 2026-10-03)

- **Merge finished work at once.** When an agent finishes, its work is merged into main and pushed straight away. Use `~/OpenTallas` as the central merge point. Don't wait for another agent to merge it. When a merge conflicts with files main has since evolved, keep main's hunks (`-X ours`) and take the rest of the branch.
- **Delete the worktree after the merge.** After merging, remove the finished worktree and its local scratch.
- **Delete inactive worktrees and scratch.** A worktree is inactive when no live process uses it and it has been untouched for a day. Before removing one, keep its unique state as a `refs/preserve/*` ref plus a patch of any uncommitted changes. Write bulk run outputs to the large compute host, not the local disk.
- **Bound concurrency by headroom, not by job count.** Keep the fleet saturated with independent work, and launch a large job only through the host's admission guard.
- **Completion over ceremony.** Focus on finishing the task: build, integrate, measure. Don't add review, freeze or seal commits, proof re-runs, or test sweeps beyond what a change needs. One commit per real step.
- **Proposers validate their own ideas.** Whoever proposes an optimisation measures it in RTL at full shape. An idea handed off without an owner is not validated. Before accepting a rejection, check that it was measured on the right vehicle (full shape, not a reduced model).
- **Simulate the minimum component.** Never simulate a whole array or die when one stage, element or layer answers the question. Measure each stage in isolation (cycles, occupancy, latency, visibility) and compose system timing analytically, because the communication pattern is fixed and known, as GPU/TPU teams do. Prove exactness on the smallest vehicle that contains the mechanism. Run a whole-system simulation only as a final integration smoke test, and only when the owner asks for one.
- **Never run git in another agent's worktree.** Work only in your own worktree or the central checkout. Never `git stash` in a shared checkout.
- Costly-build resource policy (user reaffirmed 2026-10-02): never impose arbitrary wall-time or CPU-time deadlines, individual-file size caps, or guessed per-process address-space limits on large builds or simulations. Schedule against measured CPU, RAM and disk headroom and the actual build inventory; use capacity reservations, free-space monitoring and incremental outputs. Any protective bound must be justified by actual host capacity, not copied from a small pilot. Preserve completed objects and immutable failure evidence. Do not restart a progressing pinned job solely to change its settings.
- After editing any doc under `docs/`, regenerate the prose-figure census and sync its two untriaged-count annotations, then run `make check-figures`.

- ROM reliability policy (owner decision, 2026-10-02): ROM storage, including weight and configuration ROM, for Qwen3-8B and DeepSeek-V4.1 no longer requires ECC. The selected successor must omit ROM SECDED check/correction and ECC-only parity sidecars, mirrors, exception queues and held-check debt. Preserve all previous ECC pass/failure evidence as history. Keep the exact released-checkpoint payload, golden rounding/reduction order, real macro read/capture timing and finite producer/consumer flow control. This decision does not remove SRAM, HBM, link or mutable control-state protection; configuration/descriptor validity, address bounds and transaction identity checks remain required. Do not replace ECC with mandatory parity/CRC hardware without separately pricing it. Claims assume fault-free ROM reads; commercial reliability and yield qualification remain outside this research artifact. Legacy ECC-based area/latency/rate rows are historical until the coordinated no-ECC model, macro inventory and physical contracts are regenerated.

## Fleet and retirement policy (user reaffirmed 2026-10-01)

- Active tracks: Qwen3-8B ROM, DeepSeek-V4.1 ROM, the HBM accelerator for both models (with the GPU-organised design as its ablation), and Qwen3.8-27B as a third target model (model level first; owner decision 2026-10-03). Maximum per-user decode speed is primary; maximum batching throughput is secondary and must not delay the single-user path.
- Use parallel subagents and local, all three PVE hosts and all six AGIdock VMs for simulation and place-and-route, subject to measured memory, disk and CPU headroom. Reuse live pinned jobs instead of duplicating them.
- Remove retired legacy worktrees and build checkpoints to reclaim disk. Preserve unique source changes in lightweight refs or patches before retirement, and retain committed pass/failure evidence. Never remove sources or checkpoints still required by an active job or the current targets.
