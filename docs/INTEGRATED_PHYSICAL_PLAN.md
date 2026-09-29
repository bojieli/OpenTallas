# Integrated design plan: microarchitecture model first (revised 2026-09-29)

Root: Claude (`claude-main`). The binding method is in [AGENTS.md](../AGENTS.md) and Atlas Table 5-2.

**Objective order:** minimum single-user decode latency, then aggregate throughput from independent requests.

## What went wrong, and the correction

For several days work produced independently verified components: exact engines, routed microblocks and reservation floorplans. Composed, they missed the latency target, sometimes by orders of magnitude. The V4.1 die RTL has 1,536 block-dot MACs/cycle against a budgeted 264,960 per die (529,920 with the m=2 lane copies). Its single issue slot serialises every engine, and it instantiates no memory macros.

Those gaps were knowable at design time. We had an architecture-level budget (`tools/arch_budget_v41.py`, `tools/arch_budget_qwen3.py`) that states per-die block requirements, but no **microarchitecture** model. Nothing mapped a block requirement onto:
- elements, macros and replicas;
- the broadcast, reduction and multiplexer networks those replicas need;
- wires, tracks and pipeline stages;
- the floorplan.

Nothing fed that physical latency back into the token schedule. Place and route was being used to discover the architecture. It must only validate it.

The correction is to build one unified microarchitecture analytical model first, then build only what it sizes. Parallel component streams were frozen on 2026-09-29, and their measured facts become the model's calibration inputs.

## Priority 1: unified microarchitecture analytical model (root-owned)

Deliverables: `tools/uarch_model.py`, `docs/MICROARCH_MODEL.md`, `results/uarch/<design>.json`. One schema covers four designs: Qwen3-8B ROM, Qwen3-8B HBM, DeepSeek-V4.1 ROM and DeepSeek-V4.1 HBM.

1. **Workload per die per token** comes from the architecture budget: every operation's MACs, weight bytes, activation bytes, KV/index bytes and dependency order.
2. **Element definitions:**
   - ROM designs: a ROM macro group with capture registers and bank-local MACs sized to the macro word.
   - HBM designs: an SM-like element with Tensor-Core-style MMA, register file, shared memory and L2 share.
   - Dedicated units: Sinkhorn, indexer, attention, select, stream.
   Each element gets area, ports and latency from measured records where they exist, otherwise from stated technology constants.
3. **Mapping** of every matrix onto elements: striping (rows or K across macros), macro fill depth, and the fraction of elements active per operation. Sparse experts are the central case. Per-operation cycles are the maximum of compute, memory port, network and dependency time.
4. **Networks implied by the replicas:**
   - activation multicast: width, fanout, tree levels, and registers per level from wire length;
   - result return and reduction: order-preserving, with the golden rounding points;
   - descriptor broadcast;
   - multiplexer and demultiplexer widths wherever elements share MACs or ports;
   - tracks required against channel capacity per floorplan corridor.
5. **Floorplan fit:** element footprint × replicas plus networks and dedicated units against die area and slots, using the macro-packing results already measured.
6. **Token latency:** a critical path through the per-operation cycles plus network pipeline stages, then initiation interval and occupancy for the multi-user fill. Compared against the published targets, with every gap attributed to a block.
7. **Design-point search:** sweep element size, replica count, the MAC-sharing factor and macro fill depth, and pick the latency-optimal point that fits area and power.
8. **Calibration:** every measured cycle count, routed area and wire delay from the frozen workstreams is checked against the model's prediction for the same configuration, and disagreements are listed.

**Exit:** each design has a chosen element, count, networks, floorplan and a modelled token latency. Every block is traceable to a model line.

## Priority 2: floorplan from the model

The W1 (V4.1) and W5 (Qwen) floorplan generators take the model's element footprint, counts and corridors. Output is a legal macro placement plus channel widths. This is a check of the model's area and track numbers.

## Priority 3: build what the model sized

Build one element RTL sized as the model says, verify it exact against the golden, harden it once, then replicate it by parameter to the full count. Assemble the die from the element abstract with the model's networks. Connected exact execution then confirms the model's cycles.

## Frozen work retained as inputs

Handoffs are in `/tmp/claude-1000/handoff_w*.md`. Branches `claude/w1`–`claude/w9` stay unmerged until reviewed against the model. Earlier integrations on main (`d9d783b6`) remain evidence at their stated scope.

## Hosts

Priority 1 is analytical and runs locally. Priorities 2–3 use:
- ot-pve1 and ot-pve2 (227 GB each);
- ot-pve3 (108 GB);
- the six AGIdocks (≤30 GB per job, via `/tmp/claude-1000/remote_gate.sh`);
- the local machine.
