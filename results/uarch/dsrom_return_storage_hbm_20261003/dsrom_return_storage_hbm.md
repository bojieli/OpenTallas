# DeepSeek-V4.1 ROM array: what "return storage" is, and the array with batch-sized KV HBM and minimal return

Model only: arithmetic on pinned records plus read-only runs of the unified model pinned at e634046fe (uarch_model sha256 2da5b6d9…, which reproduces 2,563.7 / 2,680.6 tok/s). No RTL, P&R or model inference. Numbers are in `model.json` and `raw.json`. Tool: `tools/dsrom_return_storage_hbm.py`.

## 1. What return storage is

**The hardware.** Return storage is the set of FIFOs inside the field's *adding return tree*:
- `rtl/v41rom/ot_v41_ret.sv`: `ot_v41_ret_node` and `ot_v41_ret_root`;
- `rtl/v41die/ot_v41_retn_w17w10.sv`.

**How the tree works.**
- Every ROM element pair produces FP32 partial dot products of matvec rows: a_proj, wq_b, wo, router, the expert gate-up and down projections, and so on. Each partial is tagged {position, row, lo, k, nseg}.
- A binary tree of 2·NP − R nodes collects these partials. A node adds two partials only when they are siblings in the golden csum tree, which keeps the K-split sums bit-exact in golden order. Otherwise it forwards one of them.
- R = 128 roots pair up the remaining siblings, round the result to BF16 and write finished rows to the vector memory.

**What is stored.** Each node has two 64-deep FIFOs, and each root has a 128-deep input FIFO plus a 128-entry held-sibling buffer. Entries are 65 bits: a 32-bit tag, a 32-bit FP32 value and an error bit. The root's held buffer adds a valid bit.

| | Formula / value |
|---|---|
| Bits per die | (2NP − 128)(2·64·65 + 66) + 128·128·131 |
| At NP 8192 | **138,469,120 bits** |
| Pricing | flip-flops: 0.379 µm² a bit, at 50% utilisation |
| Area at NP 8192 | 105.0 mm² |

**Why it exists.** Nothing in the path can push back on a sender:
- a node accepts every partial that arrives, and an overflow is a fault;
- the root has no ready/ACK signal;
- the VM write is implicitly always accepted.

Siblings arrive out of order, and two non-sibling inputs can arrive in one cycle while only one can leave. The FIFOs are therefore slack that lets a fault-free run avoid overflow *without flow control*. The depth RD = 64 is a W10 generator parameter. No measured occupancy sized it.

The only measured occupancy is one static legacy case: a peak of 1.015 Mbit, or 0.73% of the declared bits. The full occupancy join was requested and never run (return lifetime audit 93efabc2d).

**Was it a requirement?**
- The tool labels it "Explicit user requirement" (`dsrom_4096_comparable_capacity.py`).
- No owner or user text in AGENTS.md, docs/ or the memory notes asks for 138.5 Mbit or 105 mm².
- The owner's actual rules are: keep "finite producer/consumer flow control", keep "real macro read/capture timing", and keep the golden reduction order.
- "Full return" meant keeping every declared bit of the as-written NP 8192 RTL until a source ledger proved less. The records themselves say `return_is_fundamental_lower_bound: false`.

**Conclusion: it is a derived, conservative reservation, not an owner requirement.**

**How it scales.**
- It is linear in the compiled pairs per die, NP, which is a power of two.
- It does not depend on context length or stage count.

| Compiled pairs | Area |
|---|---|
| NP 8192 | 105.0 mm² |
| NP 4096 | 52.9 mm² |
| PAR2 shard (NP 2048, R 64) | 26.45 mm² |

(The "capture home" is unrelated: a 0.14 mm² enclosure for capture cells.)

**Why it led to 58 stages.** The ee3de0a11 screen charged 105 mm² (the NP 8192 figure) at *every* stage count, but S58 compiles NP 4096. Re-running the same screen with the return sized properly gives:

| Return sizing | Minimum stages | TP-4 dies |
|---|---:|---:|
| As charged (NP 8192 at every S) | 58 | 276 |
| As declared, at the compiled NP | **51** | 248 |
| Credit-based tree (see below) | 46 | 228 |
| None | 45 | 224 |

**Why it did *not* force PAR2.**

The S58 one-die-per-rank die is 924.3 mm², which is 66.3 mm² over the reticle. Its terms are:

| Term | mm² |
|---|---:|
| Frames | 322.1 |
| Configuration ROM | 69.2 |
| RNE | 13.0 |
| WAKE | 1.6 |
| **Return** | **52.9** |
| Fixed debit | 418.3 |
| Native residual | 47.2 |

- **Zero return** still leaves the die at 871.4 mm², 13.4 mm² over. Return storage alone could not have avoided PAR2.
- **The binding terms** are:
  - the 465.5 mm² of fixed services, of which 287 mm² is an *unmapped legacy complement*;
  - 721 power-of-two padding sites, worth 56.7 mm².
- **Credit return plus trimmed padding** brings the die to 821.5 mm², which fits on the r4 basis.

## 2. Minimum safe return (Little's law)

**Credit-based tree.** With credit flow control, a node side needs only (1 entry a cycle) × (a 4-cycle credit round trip) = 4 entries:
- the roots keep 128 entries;
- each pair gets one extra 8-row round buffer.

This needs **9.0 Mbit = 6.8 mm² at NP 4096**, and 3.4 mm² for a PAR2 shard.

**Without credits.** The upper envelope of live partials is two rounds × NP × 8 rows × 65 bits plus the roots. That is 6.4 Mbit, or 4.9 mm².

**Latency.** No change is priced: the drain rate is the same either way. Adoption still needs the RTL measurement AGENTS.md requires.

## 3. Scenarios

Common rules:
- **Per-user rates:** PAR2 rows use the C1 rates; one-die-per-rank (PAIR1) rows use the model's rank-die rate plus 0.407 µs for each added stage hop.
- **MTP:** τ = 4, using m = 1 verify plus draft.
- **Best batch:** 80,834 AR tok/s, bound by the head.
- **Power:** ICG-only always-on static plus dynamic.
- **Silicon:** logic plus 1,089 mm² of DRAM a stack.
- **HBM comparator:** TP-96 × 4: 5,314 τ4 tok/s, 1,117 / 1,264 tok/s per kW, 56.1k / 92.4k tok/s per M mm².

**KV rule for scenario A.** A rank die gets max(capacity, bandwidth floor) stacks.
- **Capacity is not the binding term.** One stack holds 216 users at 1M on the busiest die, while best batch needs about 35 users for AR and about 10 for MTP. So batch 1, 8, 32 and 64 all need the *same* stack count.
- **Bandwidth binds.** The model runs the index scan at the die's full stack bandwidth. At 1M with fewer stacks on the scanning dies:

| Stacks on scanning dies | AR tok/s | Saturated tok/s |
|---:|---:|---:|
| 3 | 2,536 | 75.6k |
| 2 | 2,483 | 60.5k |
| 1 | 2,336 | 37.8k |

- **Allocation in A:**
  - the 32 rank dies of the 8 scanning layers keep 4 stacks each;
  - every other rank die keeps 1;
  - head dies keep 4.

In the table, a/b gives the 1M value / the 200K value.

| Scenario | Stages | Dies / packages | Stacks | Total silicon (M mm²) | Static kW | AR a/b | τ4 a/b | Best tok/s per kW a/b (×HBM) | Best tok/s per M mm² a/b (×HBM) |
|---|---|---|---:|---:|---:|---|---|---|---|
| C1 today | 58 PAR2 | 508 / 254 | 960 | 1.445 | 30.9 | 2,347 / 2,445 | 3,813 / 4,149 | 1,997 / 2,064 (1.79 / 1.63) | 55.9k (1.00 / 0.61) |
| **A** KV sized | 58 PAR2 | 508 / 254 | 360 | 0.791 | 29.2 | same | same | 2,084 / 2,157 (1.86 / 1.71) | 102.1k (1.82 / 1.11) |
| B0 credit return only | 58 PAR2 | 508 / 254 | 960 | 1.434 | 30.9 | same | same | 1.79 / 1.63 | 1.00 / 0.61 |
| **B** credit return + trimmed padding | 73 PAIR1 | 336 / 168 | 1,200 | 1.591 | 22.1 | 2,524 / 2,637 | 4,077 / 4,463 | 2,553 / 2,663 (2.28 / 2.11) | 50.8k (0.91 / 0.55) |
| **C** A + B | 73 PAIR1 | 336 / 168 | 420 | 0.742 | 19.9 | 2,524 / 2,637 | 4,077 / 4,463 | 2,742 / 2,870 (2.45 / 2.27) | 109.0k (1.94 / 1.18) |
| ref: trimmed padding, return as declared | 79 PAIR1 | 360 | 1,296 | 1.716 | 23.6 | 2,509 / 2,621 | 4,065 / 4,449 | 2.18 / 2.01 | 0.84 / 0.51 |
| ref: no RTL change, PAIR1 at NP 2048 + A | 96 PAIR1 | 428 | 512 | 0.894 | 24.8 | 2,466 / 2,574 | 4,034 / 4,412 | 2.11 / 1.94 | 1.61 / 0.98 |
| ref: PAR2 re-staged to full shards (S48) + A | 48 PAR2 | 428 | 320 | 0.685 | 24.9 | 2,370 / 2,470 | 3,830 / 4,169 | 2.10 / 1.93 | 2.10 / 1.28 |

**Stage count for B.** B uses the conservative stage count, where the post-r4 increments scale with pairs. The lower bound, with the increments fixed per die, is:

| Variant | Conservative | Lower bound |
|---|---:|---:|
| Credit return + trimmed padding | S73 | **S69** |
| Trimmed padding, return as declared | S79 | S75 |
| Trimmed padding, zero return | S72 | S67 |

Under the power-of-two rule the result is S96 whatever the return size: padding, not return, decides it.

**Findings.**
1. KV right-sizing removes 600 of the 960 stacks with no rate loss. It is the largest single lever on silicon.
2. Return storage is about a 6-stage effect. It matters only once the power-of-two padding is trimmed.
3. Removing PAR2 by adding stages beats C1 on per-user rate (+7.5%), dies (−34%) and static power (−29%), because PAR2's crossings cost 35.9 µs (about 88 stage hops). The r4 record never swept depth (`successor_count_or_depth_sweep: false`).
4. Per-user MTP at τ4 is still 0.77× HBM. That is the verify problem, unchanged here.

## TODO for Codex

**Not done:**
1. Re-run on HEAD's model (32d865831 changes the 1M baseline to 2,490).
2. A batch-by-batch tok/s per kW table is in model.json (`by_batch`). Check it against stage power gating (PG); only ICG-only power is priced.
3. Verify that the 64.55 mm² post-r4 increments really scale with pairs. That decides S69 against S73.
4. Price the HBM PHY and shoreline area credit when a die drops from 4 stacks to 1. None is taken here.
5. Measure the credit-return tree in RTL: occupancy and rate, against the 64-deep reference.
6. Check that the gathers on 1-stack dies stay latency-bound in the model.

## Update 2026-10-03: scenario C adopted (owner), re-priced on HEAD's model

The owner approved C as the redesign direction.

**Re-run.** The re-run is on merged origin/main (32d865831 and later). There the PAIR1 baseline is 2,535.5 / 2,649.7 tok/s, not 2,563.7 / 2,680.6. The 4.34 µs shift is the hub-edge wire: 57 hops × 75 ns. The stage hop is therefore 0.482 µs.

The scenario table above predates this re-run. The current values are in `model.json` `scenarios` and `scenario_c`.

**C now:**
- 2,490 / 2,600 AR;
- 3,763 / 4,121 at τ 3.649;
- 4,051 / 4,433 at τ 4;
- 336 dies, 420 stacks, 0.742M mm²;
- 19.9 kW static with ICG only, or 7.07 kW at batch 1 with stage and link power gating;
- 2,742 / 2,870 best tok/s per kW, or 3,619 / 3,891 with power gating.

**Decisions and prices:**
- **S73 is kept.** Only about 6.5 of the 64.55 mm² post-r4 increment is traced, so S69 stays an upside.
- **HBM PHY credit:** 30 mm² a one-stack die (24–45), with 25.5 mm of edge freed. It is not yet creditable in the ledger.
- **Complement removal:** a sensitivity, not adopted. The array would be S54 with an explicit E of 150 mm², or S48 with 75 mm².

The implementation plan is in [HANDOFF_SCENARIO_C.md](HANDOFF_SCENARIO_C.md).
