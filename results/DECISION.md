# Technical gate decision

**Decision: continue the public pre-NDA characterization program; hold product
architecture freeze, tapeout, price, and production-throughput claims.**

The re-baseline is complete enough to justify targeted measurements. It is not
complete enough to validate an executable accelerator or choose a manufacturable
wafer. The repository does not yet compile complete checkpoint payloads into
physical images, execute generated microcode through an operator-complete service
engine, or match model state and logits end to end. The apparent advantage also
depends on target-node ROM service, format-specific compute, physical NoC, HBM
packaging, power, and yield that no public artifact establishes.

## What is now analytically closed

- The comparison is split into N7/HBM2e versus A100 and N4-class/HBM3e versus
  B300. WSE-2/WSE-3 are physical-feasibility anchors only.
- Flash and Pro checkpoint capacity is measured tensor by tensor from pinned
  released headers. Ordinary decode, draft-only, and resident-only bytes are
  separate.
- DeepSeek's official numerical roles are retained: routed MXFP4×FP8, dense
  FP8×FP8, BF16 paths, FP4 index work, and FP32 mHC work. Pure-FP4 marketing
  peaks are not used for mixed expert GEMMs.
- Decode tensor contractions are counted from exact operator shapes. At 200K they
  are 49.965 Gop/token for Flash and 145.068 Gop/token for Pro; the old `2 ×
  active parameters` proxy is no longer used. Selected auxiliary categories are
  counted and emit break-even rate requirements, but are not service-priced.
- Immutable weights and mutable KV are physically separate on the proposed ROM
  architecture. GPU HBM charges both streams; ROM never stores KV.
- Two DeepSeek all-reduces per layer, topology-derived wafer communication,
  pipeline residence (`batch × stages`), local capacity, cross-stage links, and
  thermal scaling are explicit.
- Both generated arithmetic audits pass: 12,091 checks for N7 and 7,881 for the
  leading-node study. This closes identities, configured tensor ceilings, and
  auxiliary break-even arithmetic only.

## Conditional 200K result

Central-envelope per-user speed ratios versus the fastest feasible same-batch GPU
are:

| Study/model | B1 | B8 | B32 | B64 |
|---|---:|---:|---:|---:|
| N7 ROM / A100 — Flash | 15.20× | 6.78× | 3.28× | 2.44× |
| N7 ROM / A100 — Pro | 18.08× | 5.42× | 2.71× | 2.11× |
| N4 ROM / B300 — Flash | 8.67× | 7.69× | 5.79× | 4.46× |
| N4 ROM / B300 — Pro | 12.68× | 11.12× | 9.55× | 7.93× |

These are simulation results under central assumptions, not expected silicon
performance. The deterministic envelope ranges remain wide. In the N7 study the
conservative envelope falls below parity for Flash at B32/B64 and Pro at B8/B32/
B64. The leading-node conservative envelope stays near or above parity at 200K,
but it still relies on unmeasured target ROM, NoC, package, and power assumptions.

The headline ratios are additionally conditional on auxiliary execution. The
reports now expose the normalization, nonlinear, attention/index-score, top-k,
compressor, and Sinkhorn rates required to fit each baseline interval, rather
than inventing a vector roof. Those paths do not yet extend modeled time or
energy, and activation quantization/scaling, RoPE, hyper-connection elementwise
work, and dispatch are not yet an operator-complete ledger. `COMP-01` must price
them from executable artifacts before performance can be promoted.

The B300 full-FP32 roof is not published in the checked official artifacts. A
19.5/45/90/180-TOP/s per-GPU sweep leaves every reported fastest-B300 200K rate
unchanged because those points are weight-memory-bound and FP32 is only
0.116–0.136% of counted operations. This removes that specific unknown from the
headline sensitivity; it does not validate the other B300 runtime assumptions.

## Architectural interpretation

The core thesis survives the accounting correction: immutable ROM can provide
much more local weight capacity per area than SRAM and can remove weight traffic
from HBM. The benefit is governed by the active weight-read/KV-service ratio and
shrinks as batch amortizes GPU weight reads or context increases mutable KV work.
ROM does not eliminate arithmetic, reductions, HBM KV service, or cooling.

The Graphcore-style SRAM control tests the same broad spatial-compute idea with a
writable storage tier. It can be fast where capacity fits, but its lower bytes/mm²
forces more stages and reaches KV/capacity cliffs sooner. Cerebras establishes
wafer-scale construction and mesh feasibility, not this design's ROM throughput.

Huawei Tau/韬 scaling is relevant as a co-design checklist for reducing device,
circuit, chip, and system delay. Public Huawei material does not disclose a
physical 3-D stack contract, so Tau and the projected 1.4-nm-equivalent density
are not applied to either result. A vertical-ROM scenario must separately model
tier count, bonds, vertical links, periphery, power, thermal resistance, yield,
repair, test, and packaging.

## Open gates that block product authorization

| Gate | Required evidence | Owner/dependency | Status |
|---|---|---|---|
| `COMP-01` executable mapping | Complete checkpoint payloads compiled into legal ROM/HBM images, microcode, and independently certified schedules; artifact-driven service-engine and representative RTL execution matching operators, routes, KV state, and logits with reconciled counters | Compiler/runtime/RTL/model verification | Open — a deterministic exact-integer fixture now compiles, inverse-checks, and executes generated artifacts with exact semantic counters, but it has no real checkpoint, target numeric formats, placement/schedule proof, DeepSeek operator coverage, or RTL execution |
| Checkpoint lifetime | Frozen model/image and multi-year service/change agreement | DeepSeek/model owner | Open |
| Router and KV traffic | Production per-layer routing, HBM reads/writes, rereads, allocator and tail traces | Model owner/runtime team | Open |
| GPU baseline | Exact A100 and B300 serving traces across the required batch/context matrix | Runtime/GPU lab | Open |
| ROM density/timing | Target-node bitcell/macro density, access time, sense margin, corners, ECC/repair | Foundry/memory IP | Open |
| Full-array activity | Simultaneous read current, energy, IR drop, noise, thermal map, duty cycle | Foundry/implementation | Open |
| Numeric compute | MXFP4×FP8, FP8×FP8, BF16, FP4, FP32, vector/normalization, softmax, top-k, Sinkhorn, quantization, and dispatch synthesis/P&R, power, and accuracy | Digital/PDK/model owner | Open — tensor contractions are scenario-priced; auxiliary paths expose only count-derived break-even requirements |
| Wafer NoC | Placed floorplan, wire/repeater/clock/skew timing, bisection and contention | Physical design | Open |
| HBM package | Stack count, beachfront escape, SI/PI, interposer/substrate, known-good-stack flow | OSAT/HBM vendor | Open |
| Power/cooling | PDN, EM/IR, transient load, junction temperature, cooling and facility envelope | Package/system | Open |
| Yield/repair/test | Reticle yield correlation, stitching, repair coverage, spares, DFT and failure domains | Foundry/DFT | Open |
| Economics | Foundry/OSAT/HBM quotes, NRE, volume/yield, spares and full TCO | Supply chain/finance | Open |

## Authorized next steps

1. Implement the governed executable path in
   `docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md`: semantic IR, complete checkpoint
   ingestion, physical image compiler, software service engine, independent
   checkers, and a real-model vertical slice. No headline performance result is
   promoted before `COMP-01` closes.
2. Obtain model-owner checkpoint-lifetime and trace access commitments. A negative
   answer can terminate product work before expensive silicon activity.
3. Run production A100/B300 baselines and collect router/KV/kernel/collective
   counters using the exact released checkpoint and required operating matrix.
4. Request foundry ROM feasibility under NDA and build a small target-node macro
   characterization plan covering density, timing, sense margin, energy, repair,
   and simultaneous activity.
5. Synthesize and place the exact format buckets and a representative hierarchical
   NoC at N7 and the intended leading node. Replace WSE/GC200 fraction ceilings.
6. Start OSAT/HBM beachfront and power/thermal studies using the explicit stack
   matrices, including a separately labelled vertical-integration option if useful.
7. Regenerate both studies with measurement distributions and production traces.
   Compare binding constraints before considering headline ratios.
8. Freeze a product architecture only if a conservative, measured scenario clears
   latency, throughput, capacity, power, yield, quality, and full-TCO gates.

The public RTL and open-PDK work may continue as interface/methodology preparation.
It cannot close any target-silicon gate or select one of the current deterministic
envelopes as a product specification.
