# Reply to "DeepSeek ROM accelerator: progress and architecture review"

**From:** Claude (DS ROM recovery owner) | **Date:** 2026-10-05 | **Re:** `reports/DeepSeek_ROM_Architecture_Review.md`

**Summary.** The target is to beat the matched HBM accelerator in both AR and MTP, on a matched workload, acceptance, precision, silicon and power. By owner decision (2026-10-05) the DS ROM continues to closure; the comparison is a measured checkpoint for the paper, not a kill switch. The dataflow principles target the right weakness of the current design. However, the brief uses a ROM reference that predates this week's measured recovery. Its candidate organization (TP96–128 plus a direct fabric) moves the bottleneck from hub round trips to communication. My recommendation is to apply the dataflow principles **inside** the current S81 pipeline organization and measure progress against matched, fully measured numbers. A new successor design should not start now.

## 1. Updated ROM reference

The brief's 725 µs is the fully measured S81 composition from before any recovery lever; recomposed with the S81-bound window it is 734.1 µs. All figures below are measured compositions on main at position 1,048,575, every term bit-exact.

**Acceptance (owner decision 2026-10-05).** Both sides use tau **4.159**, the owner 6-class workload blend (harmonic, greedy, gamma 5; `results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json`). The published V4.1 value 3.8879 is a single GSM8K dataset, and several published sources are V4-Flash, not V4.1. It and the published range 3.43–4.32 stay as a sensitivity. The MTP step does not depend on tau, and with one tau on both sides neither does the ROM:HBM MTP ratio.

| Configuration | AR µs/token | MTP step µs | MTP tok/s at tau 4.159 (at 3.8879) | Record |
|---|---:|---:|---:|---|
| S81, all-measured, before recovery | 734.1 | 1,600.1 | 2,599.2 (2,429.8) | `results/rtl/dsrom_1m_allmeasured_20261004/composition.json` |
| **S81 now**: head, router and draft-placement levers, window module bound, fused hc_post (`9082d0a53`) | **604.3** | **853.6** | **4,872.2** (4,554.6) | `results/rtl/dsrom_recovery_20261004/composition.json` |
| HBM reference (the brief's) | 460.1 | 888.1 | 4,683.2 (4,377.9) | `results/rtl/dshbm_1m_allmeasured_20261004/composition.json` |
| **Matched HBM reference** (`b39173b46`): corrections C1–C3 measured, shared levers credited, best configuration per mode | **474.8** | **1,050.6** | **3,958.5** (3,700.5) | `results/rtl/dshbm_matched_reference_20261005/composition.json` |

- **MTP:** the ROM is ahead of the matched reference: step 853.6 vs 1,050.6 µs, 1.23x the MTP rate.
- **AR:** the ROM trails by 129.5 µs (604.3 vs 474.8 µs, 0.79x the rate). The field-phase lever (PQ) is exact and worth +20.5% AR (measured on the 1,612.7 tok/s base), but it is rejected until its spine closes SS at 1.2 GHz (−722.8 ps).
- **The matched reference moved as expected.** The review's three corrections (unused issue slots, separate drains, activation loading), measured on the 1.2 GHz SM element, add 106.8 µs to the HBM AR; the shared levers win back 92.1 µs. At the clocks its blocks close today, the matched HBM is 596.0 µs AR and 1,289.4 µs MTP step.

## 2. Does a dataflow processor fix the current design's main weakness?

**Measured weakness.** At batch 1 the S81 token is latency-bound, not bandwidth-bound. On the measured critical path:

| Share | Component | Mechanism |
|---|---|---|
| ~37% | Field matvecs | Each operation is a phase: hub broadcast of x → ROM pairs → return tree → root → vector-memory write → re-read by the next operation. Every phase pays a fixed 200–260 cycles; phases (including routed experts) run one at a time. |
| ~26% | Serial vector-unit chains | Small dependent ops, each paying a memory round trip, wire stages, clock crossings and pipeline depth. |
| ~16% | Hops and collectives | Modest, because the pipeline layout keeps reductions inside TP4 groups. |

The first two are the same defect: a **hub-centric control and data loop**.

**What dataflow fixes.** Keeping state near consumers, forwarding results directly to the next operator, sizing compute for the selected work and grouping independent matrices removes most of that round trip. **In principle, yes.**

**What it does not fix:**
1. **The dependency floor.** 43 layers of dependent steps (norms, exact golden-order reductions, softmax, top-k, routing) remain. Dataflow removes overhead *between* steps, not their own latency.
2. **The cost of the proposed partition.** Re-partitioning to TP96–128 makes cross-rank exact reductions and gathers part of every layer. The brief concludes "communication is the largest unresolved lever" and needs a 1,128-link, about 3.2 kW fabric that is not qualified; cabled links need full-strength FEC, about 209 ns per crossing (`results/arch/vendor_assumption_check_20261004/`).
3. **The brief's own evidence.** The first proposal came to 1,303 µs and the adapted one to 708 µs. Both are slower than today's measured 604.3 µs: they traded hub overhead for activation/KV movement and communication.

## 3. Recommendation: dataflow principles inside the S81 pipeline

The pipeline organization already avoids most collectives; the levers below remove the hub round trip within it.

| Dataflow principle | S81 lever | Status |
|---|---|---|
| Compute sized for the work | Head redesign: lm_head 73.6 → 7.0 µs, argmax drain 35.5 → 0.01 µs | **Adopted.** Exact, routed closed at 1.2 GHz |
| Pipelined operators, no idle round trip between phases | Field phase overlap (PQ) | Exact; +20.5% AR; rejected until the field spine closes (PQ spine −722.8 ps; the baseline spine also fails by 684 ps) |
| Workgroups from dependencies | Concurrent routed experts on disjoint regions; gate/up as one row set; K-split for long rows | Next field lever, after the spine |
| State near consumers, fused dependent steps | Fused SU chains (norm, softmax, hc_post, router act + bias, swiglu/quant) with no VM round trip; SU in the 1.2 GHz domain (removes 4.3 µs of crossings) | hc_post **adopted** (`9082d0a53`, +2.60% AR, exact, routed closed); router adopted; the rest in progress |
| Direct links | Closed hop link, 0.757 → 0.454 µs per hop | Pre-layout passes; routes running |
| No needless HBM round trip | Stage the token's own KV row instead of writing then re-reading it (about 8 µs/token) | To start |
| Placement for MTP | Draft blocks co-located, experts replicated per row (+52 dies) | **Adopted**, +2.0% MTP |

**Projected range.** If the in-flight levers land, AR should fall to roughly 430–480 µs. This is an estimate, not a measurement: field PQ is measured, and the SU-chain and expert-concurrency savings are projected from the measured chain anatomy.

**Target and checkpoint (owner decision 2026-10-05).** The DS ROM continues to closure, including the S81 full-die rerun with the IR fix and the hub PG density at 0.088. The target is to beat the matched HBM accelerator in both AR and MTP (ROM AR ≤ 474.8 µs and ROM MTP step ≤ 1,050.6 µs). The comparison is a measured checkpoint for the paper, not a kill switch: each checkpoint publishes both sides as measured compositions, whichever way they fall. Today the ROM meets the MTP target and is 129.5 µs short on AR.

**The successor organization** (TP96–128, SRAM KV, direct fabric) stays an analytical design-space section unless its fully priced budget shows a credible margin over the S81 path.

## 4. Risks of this path

1. **Physical risk from added concurrency.**
   - The field spine fails 1.2 GHz today (baseline −684 ps, PQ −723 to −906 ps). Its redesign may add pipeline stages that eat part of the PQ gain.
   - Concurrent experts and K-split add wiring into an already dense spine.
2. **Power and IR.** More concurrent activity raises current density. The S81 sign-off window missed a 47.84 mV region, which needs hub PG at 0.088. Each lever must be re-checked for IR and power, not only for timing.
3. **Area and die count.** PQ adds +1.98 mm² per layer die. Draft placement adds +52 dies. Expert concurrency may add dies. Die count is not scarce, but power, cost and package count grow.
4. **Exactness under fusion.** Fused chains must reproduce the golden rounding and reduction order exactly. Every lever passes a bit-exact gate before adoption.
5. **Integration interactions.** Three silent bugs appeared only when adopted levers were combined (fused head missing on the S81 path, single candidate list under wavefront, element row-decode wrap). An all-on integration checkpoint is required after each batch of levers, plus enough per-user slots for overlapped state.
6. **The latency floor.** Even with every lever, the dependency chain sets a floor. If that floor sits above the matched HBM reference on AR, the paper reports the measured gap; closure continues.
7. **Schedule.** Closure has needed several iterations per block, and agent rate limits have cost hours per day. Routine route loops have moved to Codex to protect the design work.

## 5. Answers to the brief's four review questions

1. **Can ownership and communication shorten the dependency path without changing arithmetic?**
   - Ownership: yes. Keeping results near consumers and fusing dependent steps is measured to cut 20%+ (head, PQ).
   - Communication: not the main lever for the pipeline organization (about 16% of the path).
2. **Is the direct fabric credible?** Not in the current timeframe: 1,128 links, about 3.2 kW of PHY, cable FEC latency, and an unreconciled P6 reference. A pipeline organization with local TP4 groups is preferable.
3. **Is a heterogeneous dense/routed pool viable?** Plausibly: wide-column for dense and verify work, narrower for routed experts. S81's wavefront verify layer already costs 1.21× an AR layer for MTP. Evaluate it inside S81 via the field levers, not as a new organization.
4. **Missing costs:**
   - field-spine 1.2 GHz closure;
   - the IR window;
   - the own-row KV write (about 8 µs);
   - SU clock crossings (4.3 µs);
   - speculative-state slots (fixed: 8 slots);
   - Engram lookup (measured, 1.4 µs);
   - the HBM-side corrections and shared-lever credits.
