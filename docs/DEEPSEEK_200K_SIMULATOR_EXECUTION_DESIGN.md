# DeepSeek-V4 Flash exact-200K simulator execution design

**Design ID:** `TA-DS-200K-SIM-1`

**Status:** ABI 3.0 live-buffer Gate A is closed; WP-C/WP-D implementation is
complete at bounded-test scope; final execution and comparison remain blocked
by Gate B, source-current exact-200K accelerator runs, integrated RTL, and the
physical comparison gates

**Issued:** 2026-09-03

**Scope:** artifact-driven functional-simulator performance for the mandatory
DeepSeek-V4-Flash-0731 workload on one ROM wafer logical device and exactly 32
identical HBM/SRAM accelerator chips

## 1. Purpose and authority boundary

This document defines how to make the mandatory DeepSeek-V4 Flash 200,000-token
simulator executions tractable without weakening their numerical, mutable-buffer,
ordering, topology, provenance, or oracle contracts. It records the exact
routed-expert work implied by the currently emitted programs, identifies the
host-side materialization bottleneck, and divides implementation into independently
reviewable work packages.

The required execution remains:

- exactly 200,000 input tokens from the pinned workload;
- batch one and concurrency one;
- ordinary causal prefill followed by decode;
- greedy lowest-token-ID argmax;
- the first official EOS, included in the output, or exactly 256 generated
  tokens when no official EOS occurs first;
- external-oracle agreement over that complete generated sequence; and
- the exact ROM-wafer and 32-node HBM topology, object-source, numerical,
  counter, and execution contracts.

This document does **not** define a new ABI state encoding. ABI 3.0 is
sufficient. Mutable KV, compressed-KV, sliding-window, and compressor buffers
are ordinary HBM/SRAM memory objects with compiler-emitted ABI 3.0 tensor views
and operations. The implementation may decompose a complex live-buffer update
into multiple existing operations and scratch views. A token-step fence, plus
the existing cluster communication barriers, is the visibility boundary. A
failed run stops; no durable publication or retry protocol is required.

The implementation may remove host overhead. It may not shorten the workload,
replace execution with extrapolation, import values from a framework model,
flatten the 32-node machine into shared memory, change blocked contraction
association without proof, or make architectural counters describe less work
than the admitted program performs.

## 2. Hard admission gates

Both gates are mandatory. They are independent, and closing one does not relax
the other.

### 2.1 Gate A — ABI 3.0 direct live-buffer execution — closed

Earlier deployments routed a compressed-KV buffer through a `STATE.COMMIT`
copy whose row count was `SPAN_TOKENS`, although the buffer was indexed in
completed compression groups. That unnecessary shadow-copy capacity check
made both mandatory 200K paths unreachable:

| Lane | First prompt span that traps | Resource | Capacity rows |
|---|---:|---|---:|
| ROM wafer | 2,049 | state 321, `COMPRESSED_KV` | 2,048 |
| HBM cluster | 40,961 | state 340, `COMPRESSED_KV` | 40,960 |

This table is retained as the defect boundary, not as current behavior. The
source authority is
[operator conventions A21/A25](TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md#21-amendment-a21--a-state-resource-declares-its-own-commit)
and [wire format, “What is behind it”](TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md#what-is-behind-it).
The repaired source lowers every execution-authoritative KV, compressed-KV,
ring, and compressor-history value as an ordinary mutable HBM/SRAM object,
addresses completed groups through existing tensor views and loops, and orders
writes through existing events and the token-step fence. No state member,
descriptor minor, feature bit, or commit policy was introduced.

Gate A is closed at the compiler, admission, functional-engine, and RTL
control-plane boundary:

- the current DeepSeek HBM certificate passes 36/36 checks with zero `STATE`
  resources;
- the current DeepSeek ROM schedule certificate passes 123/123 checks with zero
  `STATE` resources; and
- the shipped-deployment RTL profile elaborates with `STATE_COMPAT=0`, rejects
  a nonzero state count before fetch, and correlates the same live-buffer views
  and terminal fence on two simulators.

This closure removes the obsolete request-span wall. It does not itself prove a
complete 200K run, engine arithmetic in the shipped RTL, or final performance.

### 2.2 Gate B — complete external EOS-or-256 oracle

The comparison contract requires the first official EOS or 256 generated tokens,
but its `external_oracle.status` is `pending`. The retained
`TA-DS-CTX-200K-1` oracle contains eight generated tokens and reports
`stop_reason = max_new_tokens`, not EOS. That prefix cannot establish the
required agreement.

Gate B closes only when the external comparator is extended through official EOS
or exactly 256 tokens with the same model revision, tokenizer, workload digest,
numeric path disclosure, greedy selection rule, and source hashes. The campaign
must not be redefined to stop after eight tokens.

The source-current Gate-B checker is now implemented in
[`check_deepseek_v4_200k_oracle.py`](../tools/check_deepseek_v4_200k_oracle.py),
and the oracle runner records its repository-owned producer map plus immutable
input identities at start; it rehashes the producer source map at completion so
a source edit during the long run invalidates the result. The retained result is
deliberately captured as a rejected
[`preflight artifact`](../results/abi3/deepseek_v4_200k_oracle_acceptance_preflight.json):
the exact prompt and tokenizer round trip pass, 74/74 checkpoint file sizes and
48/48 content-addressed shard links pass, and accelerator/oracle dependency
separation passes, but the eight-token horizon, invalid EOS-or-256 terminal
condition, insufficient prompt-plus-cap KV allocation, missing source-current
producer identity, missing explicit tiled-prefill enablement, and omitted
full-byte checkpoint hash keep `accepted = false`.

Acceptance also locks the exact qualified execution stack: tile geometry and
declared adaptations, bitwise 16-head sparse-attention splitting, the measured
FP4-fail/FP8-pass expert fallback, exact package versions, CUDA 12.8 on
`sm_120`, TF32 disabled, and the qualified Hadamard extension. A fluent token
sequence from an unqualified or undisclosed path does not close Gate B.

The contract's target capability, cost-lock, and full-workload deployment
digests are also pending. The source-locked final package must populate them for
both targets before a comparison is published.

### 2.3 Absolute promotion rule

**Gate A is now a regression invariant: every final deployment must continue to
emit zero `STATE` resources and use direct live buffers. No optimization is
admissible as a DeepSeek 200K result, and no final ROM-wafer versus 32-node-HBM
comparison is admissible, before Gate B closes and both full accelerator
executions pass.**

## 3. Audited execution identities

The static audit used the following exact identities:

| Item | Identity |
|---|---|
| Model | `deepseek-v4-flash-0731` |
| Kernel IR | `build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json` |
| Graph ID | `9ef6c3248d23c181c774fd43c09b0de2a19c8e23f344cb9a25c43040268337d9` |
| Workload | `build/workloads/deepseek-v4-flash-0731/TA-DS-CTX-200K-1.json` |
| Workload ID | `TA-DS-CTX-200K-1` |
| Workload digest | `803f0c3a3e9bf7ef68ddff00947576d2fab5703d1f4387df1eb2ec11be2c59bd` |
| Prompt tokens | exactly 200,000 |
| Maximum generation | 256 tokens |
| Comparison contract | `configs/abi3/comparison_contracts/deepseek_v4_rom_wafer_vs_hbm_cluster_32_v1.json` |
| Audited HBM bundle | `build/abi3/deepseek-v4-flash-hbm-tokens` |
| Audited ROM bundle | `build/abi3/deepseek-v4-flash-rom-tokens` |

The audited bundles establish the program structure and counts below. They are
not replacements for the pending, ABI-3.0-rebuilt, full-workload deployment
paths named by the comparison contract.

## 4. Exact routed-expert work model

### 4.1 Definitions

Let:

- `S` be prompt tokens, exactly 200,000 for the governed workload;
- `D` be post-prefill one-token decode steps;
- `L = 43` be routed layers;
- `M = 3` be routed contractions per layer: gate, up, and down;
- `P = L * M = 129` be routed operator issues per non-empty block or chunk;
- `R = 6` be selected experts per token;
- `E = 256` be global experts; and
- `N = 32` be HBM nodes.

The two loop counts are

```text
B_hbm(S) = ceil(S / 512)
B_rom(S) = ceil(S / 131072)
```

and the exact routed operator-issue counts are

```text
I_hbm(S, D) = P * (B_hbm(S) + D)
I_rom(S, D) = P * (B_rom(S) + D)
```

Every non-LINK compute instruction is invoked on every HBM node, so
the routed node-handler counts are

```text
H_hbm(S, D) = N * I_hbm(S, D)
H_rom(S, D) = I_rom(S, D)
```

The exact selected-row count accumulated by `tensor.routed_launches` over the
logical device is

```text
RoutedLaunches(S, D) = P * R * (S + D)
```

It is independent of physical ownership because exactly one HBM node contracts
each selected row.

The generation driver counts the token selected by the prefill step as
the first generated token. The governed no-EOS 256-output campaign therefore
has `D = 255`, not 256. `D = 256` is retained below only as a separately labelled
conservative stress envelope for capacity/performance planning.

### 4.2 Static program sites

Read-only decoding found 12 static `TENSOR.ROUTED_MATMUL` descriptors in each
program. None is predicated off.

```text
HBM PCs: 191/193/201, 508/510/518, 763/765/773, 1079/1081/1089
ROM PCs: 202/205/217, 523/526/538, 791/794/806, 1104/1107/1119
```

The layer-run trip counts expand these sites to 129 routed issues per non-empty
block/chunk. At 200,000 tokens:

- HBM has 391 blocks: 390 full 512-token blocks and a 320-token tail.
- ROM has two chunks: 131,072 tokens and a 68,928-token tail.

### 4.3 Exact counts and route-dependent bounds

The backend makes one contraction call per occupied global expert. For routed
issue `j` in prefill block/chunk `b`, let `U[b,j]` be that occupied-expert count.
Top-6 selections are distinct, so every non-empty block has
`6 <= U[b,j] <= 256`. Thus:

```text
C_prefill = sum over b,j of U[b,j]
6 * P * B <= C_prefill <= E * P * B
C_decode(D) = P * R * D = 774 * D
```

The prefill range is deliberately not presented as an exact backend-call count:
that count requires the actual route vectors. Full HBM blocks carry 3,072 route
assignments and its tail carries 1,920, so the 256-expert upper bound is a
realistic saturation bound rather than an impossible corner.

| Phase and target | Blocks/chunks | Routed operator issues | Routed node handlers | Backend contraction calls | `tensor.routed_launches` |
|---|---:|---:|---:|---:|---:|
| HBM prefill | 391 | 50,439 | 1,614,048 | 302,634–12,912,384 | 154,800,000 |
| ROM prefill | 2 | 258 | 258 | 1,548–66,048 | 154,800,000 |
| HBM, each post-prefill decode step | 1 | 129 | 4,128 | exactly 774 | 774 |
| ROM, each post-prefill decode step | 1 | 129 | 129 | exactly 774 | 774 |
| HBM, governed no-EOS 256-output campaign (`D = 255`) | 646 iterations | 83,334 | 2,666,688 | 500,004–13,109,754 | 154,997,370 |
| ROM, governed no-EOS 256-output campaign (`D = 255`) | 257 iterations | 33,153 | 33,153 | 198,918–263,418 | 154,997,370 |
| HBM, conservative prefill + 256-post-prefill-decode stress envelope | 647 iterations | 83,463 | 2,670,816 | 500,778–13,110,528 | 154,998,144 |
| ROM, conservative prefill + 256-post-prefill-decode stress envelope | 258 iterations | 33,282 | 33,282 | 199,692–264,192 | 154,998,144 |

In the campaign and stress-envelope rows, “iterations” is only a compact count
of one prefill's block/chunk iterations plus the stated one-token decode
steps. It does not mean the prefill is submitted 391 or two times.

## 5. Bottleneck and hazards

### 5.1 Current routed materialization path

The primary path is
[`_tensor_routed_matmul`](../runtime/sim/engines/tensor.py),
[`_stack_slice`](../runtime/sim/engines/tensor.py),
[`_contract`](../runtime/sim/engines/tensor.py),
[`_operand`](../runtime/sim/engines/tensor.py), and
[`_block_scales`](../runtime/sim/engines/tensor.py).

For every routed operator issue, every node currently recomputes `np.unique`
over the same global-ID vector. Each occupied local expert then causes a
`flatnonzero`, a contraction, weight widening, scale reading/decoding, and scale
multiplication. `_stack_slice` caches only a raw mapped slice for the duration of
one operator issue. The MXFP4 routed path does not use
`ViewResolver.device_array`.

One `[2048,4096]` or `[4096,2048]` expert matrix contains:

| Representation | Size |
|---|---:|
| Logical elements | 8,388,608 |
| Packed MXFP4 architectural bytes | 4 MiB |
| E8M0 scale bytes | 256 KiB |
| Decoded and scaled FP32 materialization | 32 MiB |

The source comment on `_stack_slice` records why whole-bank reads were removed:
one 2.147 GB ROM-bank issue measured 14.4 seconds cold and 2.0–3.6 seconds warm.
Slice reads solved that whole-bank copy, but repeated per-expert FP32
materialization remains.

### 5.2 Cache-thrash hazard

At saturation, a layer's reference stream is all gate experts, all up experts,
then all down experts. The approximate reuse distance is therefore

```text
256 experts * 3 matrices = 768 matrices
768 * 32 MiB = 24 GiB per layer
```

A conventional LRU below that distance can evict every entry immediately before
its next use and deliver effectively no hits. A cache must use an explicit byte
ceiling and scan-resistant admission/protected quotas. It remains disabled by
default until instrumentation demonstrates useful reuse.

The budget must be owned once by `Device`. `Device` owns 32 `ViewResolver`
instances for HBM, while the existing device-array cache gives every resolver
the backend's entire nominal budget. Copying that ownership model would allow
32-fold decoded-cache oversubscription.

### 5.3 Blocked-association hazard

The numerical contract pins blocked matrix association to the library, version,
device, operand shapes, and thread count. Concatenating rows from several
original expert calls changes the activation/output shape passed to the library
and may select a different association. The retained
[`numeric_contract_qualification.json`](../results/abi3/numeric_contract_qualification.json)
demonstrates that association changes alter binary32 accumulators and can alter
rounded outputs.

Caching an already validated decoded weight is safe when it leaves every
original contraction call, shape, association, and rounding point intact. Call
coalescing is a separate numerical change and is forbidden without the WP-G
proof.

### 5.4 Program-order and liveness hazard

The HBM 512-token loop encloses the whole 41-instruction expert pipeline:
dispatch, DMA, LINK scatter, routed gate/up/down, conversions and SwiGLU, shared
expert work, LINK collectives, and expert reduction. It also reuses rolling
arena storage.

Cross-block coalescing is therefore not an engine-local substitution. It crosses
explicit fences, collectives, lifetimes, trap order, and observable program
order. Only a compiler-emitted bounded superblock with new capacity and liveness
proof may perform it.

### 5.5 Retained timing boundary

The retained P32 NumPy/OpenBLAS, eight-thread runs measured:

| Target | Prefill seconds | Decode seconds |
|---|---:|---|
| HBM | 2,806.283 | 696.705 / 691.030 / 693.893 |
| ROM | 512.559 | 59.036 / 56.334 / 56.443 |

These are whole-path 32-token diagnostic timings, not routed-only timings and not
valid 200K extrapolations. The retained artifacts have no executed-association
manifest, although the current runner emits one. They prioritize the work below
but cannot serve as the final performance baseline.

## 6. Work packages

WP-A, the ABI 3.0 direct live-buffer lowering required by Gate A, is complete.
It removed the unnecessary request-span shadow commit, binds mutable buffers
through existing memory objects and views, and fences them at the token
boundary. It introduced no wire or descriptor revision. Gate A's zero-`STATE`
certificate and RTL-profile checks are permanent regression gates. The
performance-oriented simulator work starts at WP-B.

### 6.1 WP-B — oracle and final provenance package

**Goal.** Close Gate B and make the eventual result reproducible.

**Implementation.** Extend `TA-DS-CTX-200K-1` through official EOS or 256
tokens. Record model repository/revision, tokenizer digest, complete workload
identity, oracle tool/source hashes, numeric-path disclosure, generated token
IDs, EOS reason, and wall/footprint observations. After ABI 3.0 rebuilds, bind
the exact ROM and HBM program, descriptor, deployment, capability, cost, and A28
source-map digests in the comparison contract.

**Boundary.** The external comparator supplies expected tokens only. It supplies
no activation, route, weight, live-buffer, or timing value to simulator execution.

**Exit.** The strict checker returns accepted, every checkpoint byte is
verified, the exact qualified execution stack is retained, the contract is
non-pending, and the oracle contains the complete EOS-or-256 sequence for the
exact workload digest.

### 6.2 WP-C — measurement before optimization

**Status.** Implemented and focused-test complete. Production P32 and exact-200K
captures with these observations remain pending.

**Goal.** Separate materialization, route organization, contraction, memory, and
association costs without changing architectural behavior.

**Implementation.** Add non-architectural performance observations for:

- semantic routed segments and physical backend calls;
- decoded-weight materialization count, source bytes, result bytes, and time;
- route-bucket build count and time;
- cache hits, misses, bypasses, admissions, evictions, allocation failures,
  live bytes, and high-water bytes;
- process RSS/high-water mark and minor/major page faults; and
- ordered executed associations plus complete backend/device/thread identity.

Performance observations belong in the execution artifact, not in the ABI
counter registry. Architectural counters must remain byte-for-byte unchanged.

**Affected paths.** `runtime/sim/performance.py`,
`runtime/sim/engines/tensor.py`, `runtime/sim/engine.py`,
`runtime/sim/device.py`, `runtime/driver.py`, and
`tools/run_accelerator_tokens.py`.

**Exit.** Cache-off P32 and tail-boundary runs retain an association manifest,
reconcile all architectural counters, and attribute routed wall time without a
material instrumentation regression.

### 6.3 WP-D — centralized immutable decoded-weight cache

**Status.** Implemented and focused differential-test complete. The cache is
opt-in and defaults to a zero-byte budget. A bounded authenticated routed-weight
case proves cache-off/cache-on bit identity, architectural-counter identity,
association identity, exact central byte accounting, and reuse. This is not a
P32 or 200K performance result.

**Goal.** Reuse the exact validated FP32 weight materialization while preserving
the original contraction calls and architectural accounting.

**Cached value.** The read-only contiguous FP32 array produced by the existing
MXFP4 widening and E8M0 scale application. A value is inserted only after all
encoding, scale, finite-value, shape, and bounds checks succeed.

**Required key.** At minimum:

```text
Device/deployment epoch
deployment digest and generation
NODE_ID and A28 source-node identity
weight object ID and authenticated content identity
resolved weight offset, dimensions, strides, and dtype
scale object ID/content identity and resolved scale range
scale block-elements and block-rows
decode/materialization version
numeric contract
backend implementation identity and device
```

Both weight and scale objects must be verified immutable. Mutable activation and
other live-buffer objects are never cacheable. Object ID alone is never sufficient.

**Lifetime and ownership.** One thread-safe manager belongs to one activated
`Device` or explicit deployment epoch and covers all node resolvers. It is
cleared on deployment/source remap, backend/device/implementation change,
materializer-version change, or device deactivation. Immutable entries may be
shared by sessions only inside that epoch.

**Budget and admission.** Enforce one exact central byte ceiling, including all
nodes, and reserve enough working memory for an uncached contraction. Default
budget is zero. Use protected quotas per active layer, matrix family, and source
node. Once a protected quota is full, bypass scan entries rather than cyclically
evicting it. A full 24 GiB layer may retain everything; a smaller budget must
retain a deterministic useful subset rather than behave as a naïve LRU.

**Accounting.** A hit still charges the architectural 4 MiB weight read,
256 KiB scale read, all 8,388,608 scale multiplications, contraction work,
output conversions/saturations, and selected-row `tensor.routed_launches`.
Cache statistics are separate host-performance observations.

**Failure policy.** Oversize entries bypass. A cache-specific allocation
failure evicts or bypasses and invokes the existing uncached path; it never
creates or suppresses an architectural trap. A failed or poisoned
materialization is never inserted. Cache eviction changes no architectural
result or live-buffer content.

**Affected paths.** `runtime/sim/weight_cache.py`, `runtime/sim/device.py`, and
the routed operand/materialization path in `runtime/sim/engines/tensor.py`.

**Exit.** Cache-off and cache-on executions are bit-identical in outputs, traps,
destinations, architectural counters, and association manifests. Live cache
bytes never exceed the configured central ceiling.

### 6.4 WP-E — stable one-pass route buckets

**Goal.** Eliminate repeated `np.unique` and `flatnonzero` scans without changing
which contractions execute.

**Implementation.** Validate the complete ID matrix, then make one stable pass
that produces `(slot, global_expert) -> ascending row indices`. Preserve
duplicate rows, process slots in ascending order, apply routing multiplication
before accumulation, and write the destination only after the complete result
passes finite-value checks.

For HBM, map global expert `e` to its exact consecutive owner and local expert.
A bucket plan may be reused across the 32 node invocations only when admission or
the producer contract proves those ID views identical for that issue. Each node
still performs and accounts for its own architectural ID read and validation.
Otherwise construct a node-local plan; node-zero metadata must never become an
implicit cross-node data path.

DeepSeek's emitted routed descriptors expose `topk == 1` over six flattened
rows per token. This work removes host scans and sorts; it does not reduce
backend contraction calls.

**Affected paths.** `runtime/sim/engines/tensor.py`, `Device._issue_nodes`, and
distributed-dataflow verification/tests.

**Exit.** Backend calls, semantic segments, counters, association manifest,
outputs, and fault behavior equal baseline. A shared HBM plan is built once per
eligible routed issue rather than once per node.

### 6.5 WP-F — compiler-owned bounded superblocks

**Goal.** Reuse a decoded expert matrix over several original blocks without
changing the original blocked contraction segments.

**Start condition.** ABI 3.0 Gate A is closed, and WP-C through WP-E are
qualified.

**Implementation.** The compiler chooses a bounded window and allocates distinct
lifetimes for every activation, ID, gate/up/down intermediate, shared-expert
value, output, and communication scratch object in the window. It proves arena
capacity, non-aliasing, event dependencies, queue bounds, tail masks,
first-fault order, and token-step completion. LINK participant sets and
collective order remain explicit. The HBM 320-token and ROM 68,928-token final
tails remain exact.

Expert-outer execution may hold one 32 MiB decoded weight while performing each
original per-block call separately. It may not concatenate rows or change the
semantic call shapes. If computation is reordered, validation must preserve the
original first-fault PC and trap class before any destination is published.

**Affected paths.** `compiler/backends/hbm_sram/plan.py`,
`compiler/backends/hbm_sram/lower.py`,
`compiler/backends/rom/common/program.py`, deployment capacity checkers, and
source-lock/certificate tests. The runtime executes emitted program order; it
does not hide loop interchange inside a tensor opcode.

**Exit.** Compiler liveness/capacity certificates cover the complete window and
both exact tails. Semantic segments and their numerical associations remain the
baseline segments even if host materialization falls.

### 6.6 WP-G — association-preserving segmented contraction

**Goal.** Reduce physical backend dispatches only after numerical equivalence is
proved.

**Implementation.** Define a segmented backend primitive whose externally
visible manifest contains every original semantic segment, in order, with its
activation, weight, and output shapes, numeric contract, and implementation
identity. Instrument physical backend calls separately. The primitive must
produce the same accumulator and one output-rounding boundary for every segment;
packing rows is not permission to contract them under one larger-shape
association.

Two admission routes exist:

1. the primitive internally preserves each original blocked association; or
2. every emitted deployment-derived shape is bitwise qualified against the
   original calls under the exact backend/device/thread identity.

Plain concatenation has neither proof and remains forbidden.

**Affected paths.** `runtime/sim/backend.py`, `runtime/sim/engines/tensor.py`,
numeric-contract qualification, and the association-manifest schema/checker.

**Exit.** All randomized and deployment-derived segment tests are bit-identical,
the semantic manifest is unchanged, and the reduced physical-call count is
reported without reducing architectural work counters.

### 6.7 WP-H — bounded node concurrency

**Goal.** Parallelize node-private host computation only after the single-node
path is stable and measured.

**Implementation.** Run instances of one instruction on a bounded worker pool,
then join deterministically before the next dependent instruction and always
before LINK. Preserve lowest-node fault priority, per-node counters,
cluster-counter reconciliation, and fail-stop behavior.

The retained NumPy/OpenBLAS identity uses eight threads. Thirty-two simultaneous
workers would request 256 BLAS threads, change scheduling/RSS, and may change
blocked implementation identity. Worker count, BLAS thread count, affinity,
library version, and device are therefore one qualified identity. A different
thread configuration needs new association evidence.

**Affected paths.** `Device._issue_nodes`, backend thread/identity capture,
step fault handling, node counter aggregation, and LINK barrier tests.

**Exit.** Bounded concurrency is bit-identical and deterministically fault
equivalent to sequential node issue, respects the memory ceiling, and produces
a statistically significant wall-time improvement without oversubscription.

## 7. Exact 32-chip HBM invariants

The HBM target is one logical accelerator made from exactly 32 copies of the
same admitted chip. It is neither 32 independent model requests nor one shared
memory machine.

1. Every chip executes the same program and numeric implementation against its
   own node-private activation and live-buffer arenas.
2. The 256-expert bank is split into exactly eight consecutive experts per
   node. Global expert `e` is owned by node `floor(e / 8)`.
3. A node cannot read another node's activation or live buffers implicitly.
   LINK is the only cross-node data path.
4. A non-owning routed node contributes exact positive zero until the declared
   route-class-3 expert all-reduce.
5. A28 `node_segments` binds a distinct authenticated local object image to each
   consecutive node ID. There is no fallback to node zero or to a shared source.
   “Identical chip” does not mean identical weight bytes.
6. Compute instructions issue per node. LINK instructions issue once for the
   logical cluster and explicitly move bytes between node-private memories.
7. Cluster counters equal the sum of node engine work plus cluster-only
   LINK/control work. Dividing a cluster total by 32 is not a substitute
   for the recorded node counters.
8. The 37 communication descriptors remain four expert scatters, seven
   sparse-KV all-gathers, 21 activation all-gathers, four expert all-reduces,
   and one final synchronization barrier. Producer pack, endpoint, route,
   receive/unpack, consumer wait, ordering, integrity, and counters remain
   connected.
9. All nodes must agree on selected token and EOS reason before the terminal
   token-step fence completes.
10. Any concurrency or superblock implementation retains exact participant
    sets and instruction-level collective barriers.

The ROM wafer remains its separately admitted one-node logical topology; HBM
shortcuts and node-source identities are not transferred to it.

## 8. Cross-package correctness invariants

Every work package carries these invariants:

- exact graph, workload, tokenizer, deployment, capability, topology, and source
  provenance;
- exact global-to-local ownership and A28 source identity;
- no implicit remote read or write;
- complete ID validation and unchanged trap class/first-fault instruction;
- routing multiplication before ascending-slot accumulation;
- frozen increasing-K association and one output rounding boundary;
- destination untouched on operator failure;
- architectural reads, multiplications, additions, conversions, saturations,
  output elements, and routed-launch counters unchanged by host cache reuse;
- ABI 3.0 live-buffer addresses, completed-group boundaries, token-step
  fences, cursor, and tail behavior;
- exact HBM 391-block/320-token tail and ROM two-chunk/68,928-token tail;
- complete LINK order and participant scope; and
- an association manifest naming the operations and implementation actually
  executed.

The ROM/HBM target comparison additionally requires the same qualified numeric
backend and association identity. A speed result obtained from different
libraries, devices, shapes, or thread identities is a backend comparison, not
the governed target comparison.

Cache allocation, eviction, bypass, worker failure, and performance-observation
failure are host implementation conditions. None may partially publish an
architectural destination or live-buffer update.

## 9. Focused acceptance matrix

| Surface | Required cases | Acceptance oracle |
|---|---|---|
| Routed operator | Random rows, `topk`, expert counts, duplicates, skew, all-expert occupancy, routing weights | Cache/bucket off versus on: bit-identical output, counters, traps, and destinations |
| Exceptional inputs | IDs below zero and at/above 256, reserved encodings, NaNs, poisoned scales, late poison, overflow | Same trap class and first-fault PC; no success/token publication; the failed run's buffers are discarded |
| HBM ownership | 32 nodes; IDs 0, 7, 8, 255; routes spanning owners; deliberately distinct node weights | Exactly one owner contracts each selected row; remote contribution is positive zero until LINK |
| A28 source safety | Missing, swapped, duplicated, and changed node maps/content roots | Admission fails or cache keys remain distinct; no cross-node alias/fallback |
| HBM tails | 511, 512, 513 and governed final block of 320 | Exact loop count, view extent, tail mask, route rows, counters, and no phantom row |
| ROM tails | 131,071, 131,072, 131,073 and governed final chunk of 68,928 | Same exact properties as HBM under ROM divisor |
| Cache budgets | Zero, one entry, below reuse distance, protected subset, full layer; forced eviction, bypass, and allocation failure | Same architecture/association; live bytes at or below the single Device ceiling |
| Cache lifetime | New session, device reactivation, deployment/source/backend/materializer change | Reuse only inside the admitted epoch; mandatory invalidation at every identity change |
| Route sharing | Certified-identical and deliberately different per-node ID buffers | One plan only when certified; otherwise node-local; unchanged backend calls |
| Superblock liveness | Window sizes one, two, several, final partial window; injected fault in each stage | Capacity proof, no alias, original fault priority, LINK order, and completed-step fencing |
| Segmented primitive | Random segment partitions and every deployment-derived activation/weight/output shape | Bitwise equality per original segment and identical ordered semantic manifest |
| Node concurrency | Worker counts one through bound; fixed and changed BLAS thread counts; faults on different nodes | Qualified identities only; sequential-equivalent output, fault priority, and counter reconciliation |
| ABI 3.0 direct live buffers | Compression boundaries, ordinary mutable-object addresses, token-step fence, and fail-stop fault cases | Reference, compiler checker, functional simulator, cycle trace, and RTL address/control correlation agree without a new wire value |
| Historical state walls | ROM 2,048/2,049 and HBM 40,960/40,961 | The obsolete request-span shadow copy is absent and cannot cause a capacity refusal |
| Deployment trace | Regenerated P32 route traces with the current manifest-emitting runner | Baseline and WP-C/D/E results match bitwise before longer runs |
| Final workload | Exact 200K on rebuilt ROM and HBM deployments through first EOS or 256 | ROM/HBM agree with each other and the complete external oracle |

## 10. Benchmark and promotion criteria

### 10.1 Baselines

The production baseline is the current ABI 3.0 live-buffer deployment with WP-C
instrumentation enabled, cache disabled, original route scans, original
contractions, and sequential node issue. It must retain:

- the graph, workload, deployment, capability, cost, and source digests;
- backend/library/device/thread identity;
- cold/warm cache and page-cache state;
- ordered association manifest;
- phase and end-to-end wall times;
- physical backend calls and semantic segment counts;
- materialization count/bytes/time and route-bucket time;
- RSS/high-water mark and minor/major faults; and
- every architectural and per-node counter.

The official latency result begins from a newly activated, explicitly cold cache
unless the comparison contract is amended to name a different state. Warm
results are useful secondary evidence but cannot silently replace that boundary.

### 10.2 Correctness promotion gates

A package is promoted only when:

1. all applicable rows of Section 9 pass;
2. token/output arrays are bit-identical to its admitted baseline;
3. failure cases have identical trap class, first-fault PC, and untouched
   destination/live-buffer bytes;
4. architectural and node/cluster counters reconcile exactly;
5. cache and route changes retain the exact baseline association manifest and
   backend-call count;
6. a segmented primitive retains the exact ordered semantic manifest even when
   its physical backend-call count falls;
7. cache live/high-water bytes respect the single central budget;
8. topology, LINK, A28 source, and provenance checks remain admitted; and
9. the result artifact contains no null association or source identity.

For the final cross-target result, the ROM and HBM artifacts must name the same
qualified backend/association identity as well as their target-specific
deployment identities.

For a protected cache key used `A` times in an epoch, the expected result is one
materialization and `A - 1` hits. This per-key reconciliation is required; a
single aggregate hit-rate number is insufficient.

### 10.3 Performance promotion gates

Each work package declares its performance threshold before measuring. Unless a
package records a stricter target, the default promotion threshold is:

- at least 10% median improvement in its targeted routed phase or end-to-end
  boundary over at least three like-for-like measured repetitions;
- a 95% bootstrap confidence interval whose lower bound is greater than zero;
- no greater than 2% median regression in an untargeted phase;
- no central-cache budget violation or unbounded RSS growth;
- no sustained steady-state major-page-fault thrash; and
- no throughput result obtained by changing an unqualified backend or thread
  identity.

WP-D and WP-F must lower materialization count and bytes, not merely move their
time to an unreported warmup. WP-E must lower bucket builds/time while leaving
backend calls fixed. WP-G must separately show fewer physical calls and the same
number of semantic segments. WP-H must report total runnable BLAS threads and
show that its gain is not oversubscription noise.

### 10.4 Final comparison gate

The final result runs both source-locked, ABI 3.0 live-buffer targets on the exact
200,000-token workload and continues until first official EOS or 256 generated
tokens. It retains the exact tails, all provenance and association manifests,
per-node/cluster counters, cache state, memory/fault observations, and the
complete external comparison.

P32 timings, eight-token oracle prefixes, static route bounds, projected 200K
times, or a successful allocation/capacity check are not substitutes for this
execution.

## 11. Non-goals and change-control boundary

This design does not authorize:

- any program or descriptor ABI other than frozen ABI 3.0;
- context truncation, prompt tiling that changes semantics, or an eight-token
  final comparison;
- a shared-address-space model for the 32 chips;
- cache reuse across unauthenticated objects, node sources, deployments, or
  backend identities;
- hidden block/layer interchange in the runtime;
- concatenated contraction shapes without WP-G qualification;
- changed LINK algorithms, reduction order, participant scope, or barriers;
- changed architectural counters to make host optimization appear cheaper; or
- hardware PPA, cycle accuracy, or manufacturing claims from functional
  simulator wall time.

Shared checklists and master plans may link to an admitted revision of this
document later. They are not modified as part of this design package.
