# DS-ROM wavefront verify (model-first check, 2026-10-03)

Model only: no RTL, no P&R, no inference. Base: scenario C (`claude/dsrom-return-storage-hbm-20261003` @ ba4dc1a18). The per-stage figures come from `cons_v41_rom` on the HEAD unified model, run with the scenario C record's settings. The S58 run reproduces the record: 2,535.5 tok/s, and a verify of 932.97 µs.

## 1. How the m=1 verify is composed today

`v41_verify_T` and `_v41_graph` multiply every node's issue by p (lane nodes by ⌈p/m⌉) and then re-solve the graph. Each node therefore finishes all 6 positions before its successor starts. Fill, wires, hops and dependency latency are paid once, but the issue of every critical-path node is paid 6 times. While one stage works through its 6 positions, the other 72 stages sit idle for this user.

The verify is therefore **T1 + 5 × (critical-path issue)**, not 6 × AR:

| Run | T1 µs | Verify µs | Ratio | Critical-path issue µs | Latency µs | Slowest stage occupancy | Slowest window |
|---|---:|---:|---:|---:|---:|---|---|
| S73, 1M | 403.2 | 952.4 | 2.36 | 109.8 | 293.4 | head 12.37 (next: stage 36, 11.62) | stage 36, 19.24 |
| S73, 200K | 386.2 | 869.5 | 2.25 | 96.7 | 289.5 | head 12.37 (next: 4.51) | head 15.42 |

The wavefront replaces the issue summed over all stages (~110 µs) with the slowest stage's per-position interval (12.4–19.2 µs).

### What could forbid it (none does, at model level)

- **Causal in-block attention and index.** Position j at layer l needs the KV row and index key of positions < j at layer l. Those positions are at least one interval ahead (≥ 12.37 µs). Their rows are written early in the stage (by the KV projection), so visibility needs only write-to-read under ~12 µs.
  - This is new for the array. The array's multi-user pipelining never has a read-after-write hazard within one user in flight. It needs a per-stage forward buffer or a write-completion fence. The forward buffer holds ≤ 5 positions × (288 B CKV + 68 B index key + 528 B window row) per layer: a few KB a stage.
  - The CSA/HCA compressor sees the positions in order, as in the pass.
- **Routing, experts and collectives.** These are per position in both schemes, so there is no MoE union to lose: all experts are resident in ROM. TP-4 collectives stay inside a stage.
- **Stage-hop links.** Each hop carries one 4 × 5,120 BF16 hidden state (40 KB) per interval, at ≤ 0.48 µs per 12.37 µs (≤ 4% duty).
- **State.** A second in-flight activation per stage is what multi-user saturation already assumes.
- **Rollback.** Rows of rejected positions are simply never read, as today.
- **Drafter.** It is unchanged and serial after the verify, because it needs the accepted hidden state. Its cost is 0.1173 × AR (the scenario C composition).
- **Loss: index-key sharing.** The pass reads the index keys once per pass. The wavefront reads them once per position.

## 2. Wavefront priced on scenario C (draft 0.1173 × AR, II = slowest stage interval)

| | Verify/AR 1M | τ 3.649 1M | τ 4 1M | Verify/AR 200K | τ 3.649 200K | τ 4 200K |
|---|---:|---:|---:|---:|---:|---:|
| Pass m=1 (record) | 2.34 | 3,696 | 4,051 | 2.23 | 4,044 | 4,433 |
| **Wavefront, occupancy II (12.37 µs, head)** | **1.154** | **7,147** | **7,834** | **1.161** | **7,423** | **8,137** |
| Wavefront, window II (one position per stage) | 1.24 | 6,696 | 7,340 | 1.20 | 7,200 | 7,892 |
| HBM accelerator | — | 6,001 | 6,579 | ≈ | ≈ | ≈ |

**Ratio to the HBM accelerator:**
- Occupancy rule: 1.19× at 1M and 1.24× at 200K.
- Window rule: 1.12× at 1M and 1.20× at 200K.

**Notes on the composition:**
- The record's τ-3.649 figure of 3,762.7 uses the model's 0.075 draft. Applying the same 0.075 draft to the wavefront gives about 7,390 at 1M.
- At 1M, doubling the head dies (8 → 16) gains only 0.7%, because the next-slowest stage is the L20 scan at 11.62 µs. At 200K it gains 6.7% (7,921), for 8 more dies.

**Costs:**
- **Saturated MTP throughput:** unchanged, at 34,930 tok/s (1M), because the head binds in both schemes.
- **Energy:** +26.3 mJ per emitted token at 1M (on ~170) and +5.5 at 200K, from the index keys being re-read per position.
- **Area:** a few KB of forward buffer per stage and sequencer support for same-user in-flight tokens. No lanes and no dies are added.

### Does the HBM accelerator have an equivalent?

Only partly. It already batches the 6 positions on the MMA columns, reading the weights once; its verify plus draft is 1.83 × AR. A layer wavefront would re-read the weights per position, which is worse for a weight-bandwidth-bound design.

Its residual is the dedicated-unit issue repeated per position. Overlapping positions inside a die could hide some of that. This is not modelled, and a fair comparison must give the HBM accelerator the same chance.

## 3. Versus m=2/3/6 on C

The verify/AR ratios come from the S58 sweep (8bb540cd1). They are applied to C's AR, ignoring the stages that m ≥ 2 adds, so the m ≥ 2 rows are upper bounds.

| | Verify/AR | Dies vs m=1 | τ 3.649 1M | τ 4 1M | τ 4 200K |
|---|---:|---|---:|---:|---:|
| m=1 | 2.35 | 1.00 | 3,682 | 4,037 | 4,215 |
| m=2 | 1.80 | 1.00–1.08 | 4,739 | 5,195 | 5,424 |
| m=3 | 1.62 | 1.13–1.33 | 5,230 | 5,733 | 5,986 |
| m=6 | 1.43 | 1.57–2.06 | 5,872 | 6,437 | 6,721 |
| **Wavefront m=1** | **1.15** | **1.00** | **7,147** | **7,834** | **8,137** |

The wavefront beats m=6 at no added dies. Even m=6 keeps 1.43×, because the hub's vector and reduce work and the collectives are still paid per position, serially at every node. The wavefront hides that work too.

## 4. Verdict and what to measure in RTL first

**Verdict: adopt as the leading MTP lever, pending RTL.** On scenario C it is 1.9× the m=1 pass (7,147 vs 3,696 at τ 3.649, 1M) and 1.19× the HBM accelerator, with no added dies. The figure is bounded by the window rule at 1.12×. Saturated throughput is unchanged.

The model treats it as an upper bound because it assumes:
1. a stage accepts the next position after its occupancy (not its window);
2. KV and index-key visibility within one interval;
3. no extra sequencer bubble.

**Measure first:**
1. Two positions of the same user in one DS-ROM stage bench (L20 scan layer plus attention), recording:
   - the minimum entry spacing (occupancy 11.6 vs window 19.2 µs);
   - the KV and index-key write-to-read visibility latency.
2. The head die's per-position interval (12.37 µs is the II).
3. Bit-exactness of a 6-position wavefront against the existing m=1 verify golden (the DSpark m=1 bench, e694ceec5) with one rejected position, to check the rollback.
