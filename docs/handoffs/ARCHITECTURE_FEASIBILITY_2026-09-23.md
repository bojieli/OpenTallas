# Architecture feasibility handoff — 2026-09-23

Work is paused at the user's request to wrap up and continue later. **The objective
is incomplete. No architecture has passed whole-system feasibility; no ROM/HBM
speedup or physical maximum tokens/s is established.** This checkpoint contains
analysis and design candidates, not newly integrated RTL or workload simulation.

## Start here: latest user direction

Derive performance from physically constrained machines, then calculate latency
and tokens/s. **Do not design backward from 100 µs/token.** That number is now only
a sensitivity marker; earlier reports calling it an explicit target are superseded.
Separate single-sequence decode speed from aggregate multi-user throughput.

Three designs are required:

1. HBM accelerator array, GPU-style, as the primary optimized baseline.
2. ROM chip array with fast interconnect as the primary proposed design.
3. Integrated ROM wafer or connected wafers as a secondary design. External
   KV/Engram memory integration and manufacturing feasibility are not solved.

“Array” means multiple connected chips, not a single reticle. Compare equal total
die area and separately system power, plus capacity-matched systems where useful.
Allow both arrays caching, locality, batching and valid compute optimizations.
The objective is a several-fold ROM decode improvement if physically achievable,
not a result to assume. Keep **Qwen 8B** and **DeepSeek-V4.1-Flash** separate: the
former is compact/dense; the latter requires a distributed MoE study.

Verify feasibility before new implementation or workload/RTL simulation. Work on
`main`; commit and push meaningful progress. Preserve unrelated dirty files.
Do not spawn agents without explicit authorization. Do not mark the goal complete.

## Continuation progress (same day, second session)

The user directed that the ROM design **reference Taalas HC1**, the shipping part
that decodes Llama-3.1-8B at 16,960 tokens/s per user on one 815 mm² N6 die. Done:

1. **Qwen compact screen finished and tested** →
   [QWEN_COMPACT_RESOURCE_SCREEN.md](../QWEN_COMPACT_RESOURCE_SCREEN.md). Under the
   shipped BF16/sequential contract, equal-area ROM and HBM tie (1.0×); the
   recurrence binds both at 888.832 µs. The v1 draft's 275/1,101/1,125 ceilings are
   superseded.
2. **ROM density evidence register** →
   `configs/architecture/rom_density_evidence.json`. Compiler-class N7 ROM is
   2.73–4.30 MB/mm² (TOM paper, internally inconsistent), no denser than SRAM.
   HC1 averages 4.93 MB/mm² of 4-bit weights over its whole die, but only for
   compute-in-ROM select cells.
3. **HC1-referenced designs** →
   [HC1_REFERENCED_ARRAY_DESIGN.md](../HC1_REFERENCED_ARRAY_DESIGN.md). Qwen3-8B on
   one HC1-class die: 15.1–16.8K tokens/s, **7.6–8.4× a same-format HBM die**
   (2K context only; 8K KV exceeds HC1's SRAM ceiling). V4.1 on an 80-die HC1-class
   array: ~3.4–5.1K tokens/s per user, **0.87–1.21× an equal-area HBM array with
   the same hardwired dataflow** (0.96–1.29× equal power), **batch 1 only**. The
   roofline framework agrees at batch 1 (1.23–1.60×). Its larger V4.1 advantages
   come from multi-user batching (4.4–19.8× per user at batch 64–256), aggregate
   throughput (up to 44–71×) and wafers (3.0–5.7×). The standalone envelope omitted
   batching; future V4.1 work should extend the framework rather than parallel scripts.
4. `tools/audit_v41_streaming_schedule.py` remains unaccepted and is now
   **superseded** by the HC1 envelope's stage model; do not quote it.

Still open, in priority order:

- **Numerical contract for an HC1-class Qwen die** (3/6-bit weights, parallel
  accumulation). This decides whether the one several-fold result is a design.
- **Shorten the V4.1 dependency chain**: stage latency below HC1's 0.368 µs
  (needs evidence that HC1 is throughput-bound) and fewer hops per layer. This is
  the only lever for a per-user ROM advantage on V4.1.
- **Aggregate throughput** with the HC1 per-stream (no batch amortization) law vs
  a batched HBM array, using the existing roofline per-stream study.
- **Wafer designs** (secondary) on the same envelope, with explicit external
  KV/Engram interfaces.
- The repository's own HC1 reconstruction still fails capacity (1.6× cell per bit
  instead of one select transistor per ≤4-bit weight). Fixing it changes a
  validation gate and needs its own review.

## Repository and checkpoint

- Workspace: `/home/ubuntu/OpenTallas`; branch `main`.
- Latest commit before this handoff: `40b374fc`, address-striped ROM requirements.
- Its push initially failed twice with GitHub server errors; the pending retry was
  polled during wrap-up and **successfully pushed** `5d1bb977..40b374fc`.
- The commit containing this handoff also preserves the two unfinished analyses
  described below. Read `git log` for its ID; it cannot name its own hash in-file.
- HTTPS push command:

```bash
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push https://github.com/bojieli/OpenTallas.git main:main
```

`origin/main` may remain stale because this pushes directly to an HTTPS URL.
Verify remote state before interpreting local ahead/behind counts.

## Authoritative reading order

1. [Resource-first method](../RESOURCE_FIRST_PERFORMANCE_METHOD.md): current method.
2. [Three-design comparison](../DEEPSEEK_V41_THREE_DESIGN_COMPARISON.md): comparison
   scope and links. Its initial fixed-target wording is superseded by its top note.
3. [ROM macro evidence gate](../DEEPSEEK_V41_ROM_MACRO_GATE.md): major unresolved
   physical-evidence problem.
4. [Address-striped ROM candidate](../DEEPSEEK_V41_BANKED_ROM_CANDIDATE.md): concrete
   logical pooling design, bank/compute/power requirements.
5. [Array mapping](../DEEPSEEK_V41_ARRAY_MAPPING.md),
   [resource-constrained arrays](../DEEPSEEK_V41_RESOURCE_CONSTRAINED_ARRAYS.md),
   [expert striping](../DEEPSEEK_V41_EXPERT_STRIPING.md).
6. [Attention placement](../DEEPSEEK_V41_ATTENTION_PLACEMENT.md),
   [dense inventory](../DEEPSEEK_V41_DENSE_PLACEMENT.md),
   [traffic recalculation](../DEEPSEEK_V41_TRAFFIC_RECALCULATION.md).
7. Qwen: [performance gap](../ROM_HBM_PERFORMANCE_GAP.md),
   [ROM proposal](../ROM_FIRST_ARCHITECTURE_PROPOSAL.md),
   [recurrence/blocked feasibility](../ROM_REDESIGN_FEASIBILITY.md).

Older numerical tables remain conditional evidence, not accepted designs. Prefer
source hashes and explicit claim boundaries over report titles or PASS labels.

## Key established findings

### V4.1 inventory and semantics

Pinned source revision: `dba1be0a40aa45a94ad051997016db3960a90277`.
Local vendor snapshot:
`/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277`.

- 40 ordinary layers; hidden 5,120; intermediate 2,304; 384 routed experts/layer,
  six selected; one shared expert. Draft/vision require separate scope.
- Three matrices/expert: 35,389,440 values. FP4 payload plus one E8M0 scale byte
  per **row per 32 K values** gives 18,800,640 B/expert. A profile prose field says
  32×32 for routed weights; that is wrong, but its byte inventory matches 1×32.
- Selected routed reads: 112,803,840 B/layer; **4,512,153,600 B/token**.
  Routed arithmetic: 16,986,931,200 operations/token, MAC=2 operations.
- 112.8 TB/s came from an assumed 40 µs expert-service allocation, not intrinsic
  model demand. At 1 ms expert service, the same bytes need 4.512 TB/s.
- Non-routed inventory: **8,522,921,408 B**, reconciled against 1,253 tensor headers.
  Attention projection/norm 5.070 GB; shared experts 1.417 GB; head 1.324 GB.
  Together 91.64% of non-routed inventory. Text with no image mask does not read
  61,440 B of vision router biases; other conditional roles still need auditing.
- Full checkpoint 510.286 GB; Engram elsewhere leaves 307.528 GB retained in ROM.
  Engram tables 202.758 GB; nominal lookups 12,672 B/token. Engram projection/gate
  weights are separate and remain active.
- `wo_a` is block diagonal over eight head groups. Packed checkpoint bytes across
  layers are 1,343,488,000; vendor conversion materializes 2,684,354,560 BF16 bytes.
  On-read reconstruction and expanded storage are different deployment options.
- Vendor routed kernel uses independent 32-value partials then scaled accumulation.
  The earlier 74.24 µs whole-K g4 bound is **not universal for V4.1**. Scalar native
  block candidate gives conditional expert-only dependency schedules 11.84–35.52 µs
  at 1 GHz for recurrence 1–3, with unlimited parallel partial engines and omitted
  service. It is not a physical forecast or vendor bit-equivalence proof.
- External oracle uses vendor FP8 expert recast; it does not certify native FP4.
  Vendor expert applies routing weights before down projection; do not move them
  past rounding. Partial reduction/order changes require numerical qualification.
- Compressed KV owners: 2,8,14,20; index sources also 24,28,32,36. Shared ownership
  does not remove per-layer sliding-window `wkv` projection.

### Array capacity and communication

- Planning ROM density 9,379,500 B/mm² with 2% reserve is **unqualified at the
  required port/compute organization**. 815 mm² is a planning die size.
- Layer-dedicated hybrid capacity: 300/400 mm² ROM per die → 120 chips;
  500 mm² ROM → 80 chips. These do not prove compute, SRAM, links or power fit.
- For 80 chips with four-chip expert islands, two layers/stage gives only one
  island/stage. Six experts share it: expert-read sensitivity at 4.5 TB/s/chip is
  250.675 µs. Twenty layers/stage gives ten islands: best route 41.779 µs, worst
  still 250.675 µs. More layer sharing changes concurrent compute/pipeline service.
- Whole-expert HBM layout has at most six active expert chips. At assumed 4.5 TB/s,
  best expert-read floor is 167.117 µs across forty layers. This is not a universal
  HBM ceiling: tensor striping/caching can improve it.
- Expert-local BF16 dispatch/return: 4.915 MB/token endpoint traffic, not TB/s of
  external weight traffic. At illustrative 400 GB/s and 0.5 µs fixed one-way delay,
  serial forty-layer expert fabric costs 52.288 µs, excluding other work.
- Eight-group attention `wo_b` K-sharding adds 6.554 MB/token FP32 partial ingress;
  same illustrative link parameters → 36.384 µs, excluding merge/publication.
  Feature gathering plus output-row sharding is an alternative to qualify.
- Expert striping, FP32 returns and six disjoint sets: at assumed 4.5 TB/s/chip,
  400 GB/s endpoint and 0.5 µs fixed delay, read+fabric subtotal is lowest among
  tested points at four shards/expert (155.507 µs). More shards eventually worsen
  return traffic. This optimum cannot be copied into an incompatible capacity map.
- Non-routed caching and common critical-path work materially affect speedup;
  experts are only 34.6% of current active weight bytes. Expert-only infinite
  acceleration gives just 1.529× under equal-byte-service assumptions.

### Major ROM physical gate

The current technology inputs mix a fabricated 28 nm ROM-CIM density anchor and
another design's simulated CIM operation-derived bandwidth. The latter does not
prove external digital read bandwidth. Existing routed 130 nm IHP macro evidence
explicitly prohibits extrapolation to N5/N4 and excludes several physical costs.
No inspected evidence establishes joint advanced-node density, delivered bandwidth,
area, energy and required arithmetic semantics.

Uniform dedicated banks and fully pooled service differ dramatically. In a chip
holding 780 resident expert shards, hypothetical 72 TB/s region service gives
2.611 µs across forty layers for a single selected shard with ideal pooling, versus
2,036.736 µs if every shard owns 1/780 of bandwidth. Neither is a physical result.

An explicit pooling candidate stripes each expert over common banks in different
address ranges. Selected expert streams time-share them. At 4.596 GB/chip, 1 GHz,
256 B/word and 65% delivery:

| Delivered sensitivity | Logical banks | Bank capacity | Scalar lanes at 65% |
|---|---:|---:|---:|
| 4.5 TB/s | 28 | 164.14 MB | 13,032 |
| 18 TB/s | 109 | 42.16 MB | 52,127 |
| 72 TB/s | 433 | 10.61 MB | 208,507 |

Logical banks require physical subdivision/mux/routing. At 1 pJ/delivered bit,
72 TB/s costs 576 W in read service alone. A hypothetical 100 W allocation requires
≤0.174 pJ/bit, before compute and other power. No point is selected or qualified.

### Qwen compact design

- Retained BF16 checkpoint 16,381,470,720 B; active weights 15,136,811,008 B.
- Existing sequential whole-K RNE contract, whole-producer scheduling, unlimited
  output parallelism and 1 GHz yields 888.832 µs linear-only floor at recurrence 1;
  attention/memory/nonlinear/fabric omitted. More output lanes cannot remove it.
- Block reassociation is not universally bit-equivalent: the committed finite
  BF16 witness gives sequential 0 versus blocked 1. No contract amendment accepted.
- Latest unfinished compact screen below derives 1,782 mm² ROM area for the full
  BF16 checkpoint at assumed density/reserve. One 815 mm² die cannot hold it even
  with no compute. A compact multi-die package is different from a single tile.

## Unfinished work preserved in this checkpoint

1. `tools/audit_qwen_compact_resources.py` and
   `results/architecture/qwen_compact_resources.json`: created immediately before
   the user requested wrap-up. Script executed successfully; **no dedicated test
   or final report yet**. It derives capacity of 6/5/4 dies at 300/400/500 mm² ROM
   per die; 8K BF16 KV is 1.208 GB (~312 mm² at assumed SRAM density); combines
   shared memory-service and existing sequential recurrence floors using a max.
   Bandwidth 4.5/18/72 TB/s sensitivities give conditional ceilings about
   275/1,101/1,125 single-sequence tokens/s under that unchanged contract. These
   are not general model ceilings or achieved hardware performance. Review before
   incorporating into an authoritative report.
2. `tools/audit_v41_streaming_schedule.py` and
   `results/architecture/v41_streaming_schedule.json`: older interrupted analytical
   draft, previously untracked. **Not accepted or tested.** Attempts closed-form
   finite native-partial streaming with interleaved chains and ping-pong buffers.
   Recheck recurrence timing, port bursts, capacity, initial fill, scale work and
   whether its availability assumptions match a real schedule. Do not quote its
   timing as established. Retained solely to avoid losing prior work.

## Validation at wrap-up

Ran the 17 relevant analytical test files together: **61 tests passed**. They are
`test_v41_{array_mapping,attention_placement,banked_rom,budget_sensitivity,
dense_inventory,expert_groups,expert_striping,fabric_feasibility,layer_local_arrays,
numerical_structure,partial_resources,physical_envelope,rom_service_ownership,
speedup_conditions}.py` plus `test_blocked_rom_feasibility.py`,
`test_redesign_recurrence_feasibility.py`, `test_rom_hbm_redesign_budget.py`.
These test arithmetic and invariants, not physical feasibility or full inference.

Known broader failure: `tests/test_inventory.py` scans registry-listing JSON files
as if they were tensor inventories, raising missing `tensor_count`. The V4.1
inventory conservation check passes separately. No production inventory/test
selection was changed to conceal that unrelated failure.

## Workspace safety and running work

The worktree contains many unrelated modified compiler, RTL, physical-results and
prototype files. Do not bulk-stage, revert or clean them. Inspect `git status`.
In particular preserve `compiler/backends/rom/common/program.py`, multicast adapter
work, comparator configs, GEMM prototype work and `results/rtl/transcendental_tail_fold/`.
The latter is an unintegrated numerical experiment, not credited architecture speed.

No new physical jobs were launched in this feasibility phase. At wrap-up, live
OpenROAD processes were observed, including PIDs **2128587, 2758350, 2783431**
running global routing. This was a sampled process listing, not an exhaustive
inventory or proof of forward progress. Do not restart or terminate them based on
old summaries or absent result files. Inspect current processes/containers and
actual logs before taking action. User asked to stop our current work, not to kill
existing physical jobs.

Disk: about **6.4 GB available**, displayed 100% usage on the 3.7 TB volume. Avoid
large new jobs or broad cleanup. Earlier cleanup authorization does not imply
permission to delete arbitrary generated or unique evidence.

## Recommended next session actions

1. Read this handoff and the resource-first method; inspect branch, dirty state and
   remote push status. Do not repeat the completed inventories or restart jobs.
2. Finish reviewing/testing the compact Qwen screen and formulate its local
   multi-die candidate separately from V4.1. Retain numerical contract constraints.
3. For V4.1, obtain/inspect joint macro evidence or a defensible bank/subarray
   design boundary: density, digital read or native arithmetic rate, area, latency,
   energy and numeric semantics. Do not fill the gap with arbitrary favorable rates.
4. Constrain per-chip compute/SRAM/PHY/power in a small number of explicit stage/
   island maps. Combine operator service and actual communication into a finite
   whole-token dependency schedule; account for concentrated routes and caches.
5. Optimize HBM independently under equal area/power, including dense caching and
   stripe alternatives. Report conditional ceilings and constructive estimates
   separately, with unknowns. Extend to secondary wafer designs only with explicit
   external-memory and inter-wafer interfaces.
6. Proceed to implementation and simulation only after feasibility survives these
   checks. The full requested objective remains active in scope but paused for
   this handoff; it is not achieved.
