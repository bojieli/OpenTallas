# Executable H3 version/residence lowering, calibrated to actual H1

Base source: `4d7933caef35bd73794d9d945298cd1c0c585d16`. This package implements and runs a compiler over every macro in the current complete HBM programs. It emits immutable buffer versions, explicit read/write dependencies, native-service transaction paths, proposed RF/spill homes, workspace reservations, source-ordered normalization/HC instruction DAGs and a serial full-token duration expression. It performs no tensor arithmetic, checkpoint payload reads, RTL generation or hardware build.

## Delivered IR

| Target | Macro operations | Immutable buffer/state versions | Operations with native or mixed native path lowering |
|---|---:|---:|---:|
| Qwen HBM | 1737 | 2027 | 362 |
| DeepSeek HBM | 2213 | 3173 | 161 |

`Qwen.json.gz` and `DeepSeek.json.gz` are deterministic compressed JSON. `operations` contains each PC's source descriptor, input/output version IDs, participants, predecessor dependencies, golden contract, boundary traffic, native path and missing endpoint names. `operands` contains rank element counts, precision, birth/consumer/retirement PCs, owned write extents and proposed homes. `storage_demand` reports every rank. `token_schedule` includes every PC exactly once: no absent service term becomes zero. These are compiler outputs, not a passed native ISA execution.

DeepSeek lowering resolves all source dispatch kinds, gather/global extents, the seven partial SwiGLU slot writes, source rank-memory clearing at each layer, candidate keep flags, and compressed/index append generations. Each partial update explicitly depends on the previous version. An appended key generation replaces the entering history for subsequent index readers. All-gather uses global owned extent rather than summing 96 dense backing arrays. Engram hash ownership remains dynamic and explicitly unbound; its conservative decoded extent follows the emitted6144-element gather.

The proposed allocation policy serializes macro retirement and places transient buffers at SM0 on each participating rank. It reserves RF slots0..31 and shared bytes0..8191 for kernel workspace, then allocates live macro versions in slots32..511. RF contents retain ownership through consumer retirement; inputs and outputs cannot alias while simultaneously live. Oversized values receive non-overlapping logical spill offsets. These offsets have no actual HBM base/provider and cannot be admitted until mapped and priced. Persistent and selected KV/index histories have separate provider homes with explicit bytes and generation, rather than being squeezed into transient RF.

Under this conservative policy, peak RF usage including the32-vector workspace is258 vectors for Qwen and502 for DeepSeek. Peak proposed spill arenas are34,078,720 bytes/rank for Qwen and175,104 bytes/rank for DeepSeek. These are demands of this concrete unfused allocation, not minimal storage lower bounds or a proof of deployed residence. A source-exact tile/fusion successor can change them, with its own compiler certificate.

The unified-model join prices a replicated RF substrate of512KiB physical per SM (two copies),64KiB shared per SM,32SM per rank: Qwen TP2 is32MiB physical RF and4MiB shared; DeepSeek TP96 is1.5GiB physical RF and192MiB shared. SM0-only allocation does not shrink these declared substrates or authorize their floorplan. Mux/fanout, routes, slots and physical clocks remain Maxwell's composed admission dependencies. Qwen/DeepSeek ROM programs remain separate field/reticle targets; no GPU allocation or timing is substituted for their mapping.

## Native arithmetic and ordered kernel output

Qwen residual/scale/scalar multiply paths name actual `ot_gpu_full_sm_service` ADD/MUL, RF read/held-response, mirrored write/ACK and held done events. Matrix operations emit native module/NC, whole-K, rank output counts, x-store beat width, payload width, capture reservation and unresolved native column/row descriptor mapping. This is executable descriptor lowering with named missing adapters; it does not assert the full-shape descriptor is already wired.

`model.json.ordered_kernels` contains concrete chunk8 product/add nodes, fixed pairwise parent/child identities and normalization tails for Qwen128/4096 and DeepSeek5120. Qwen mean uses multiply by1/N; DeepSeek's source norm calendar uses DIV. Seed/shift/subtract and all three Newton steps remain explicit. HC pre/post emit ordered four-way mixes starting atp0, followed by the source BF16 rounding bit operations. No algebraic contraction, altered tree or FMA is used. Shared partial/tree offsets and native RF transaction demand are emitted; word extraction, lane gather and broadcasts are missing endpoints, not free transport.

Other operator families retain source-defined macro contracts and named endpoint requirements. The IR explicitly reports `all_macros_expanded_to_native_instructions=false` and `all_hidden_external_operand_layouts_bound=false`: weights, gamma/table delivery, packed-layout bridges and exceptional kernel interiors still need native bindings. Compiler coverage of all macro PCs is distinct from implementing every opcode.

## Actual H1 calibration, not oracle timing

The package retains raw DS simulation log, trace verdict, independent parent trace verdict and run receipt from `/tmp/hbm-ds-runtime-calibration-parent-20261002-r2`. The compiler checks equality of parent/owner verdicts and exact source hashes for the RF/SIMD modules. It parses all1028 alias accepts across four cases; the full4096-row cases each have512 accepts and all511 successive intervals equal19 cycles. Four-case/reset receipt PASS is directed native evidence only.

All emitted native transaction budgets now use the measured19-cycle alias-driver cadence as a **candidate service composition parameter**. The earlier14-cycle FSM-only estimate is retained as unqualified, not used to price emitted native operations. The driver includes handshake/control spacing; this record does not claim intrinsic minimum II19 under every arbitration or future loop. Qwen uses the same modules, but DS measurement transfer is explicitly candidate-only until its own chain gate passes.

The raw full-shape RF fence→dependent issue measurement is9775 cycles. Last-visible→issue is9779 with baseline ACKhold2 and10019 with held ACK242. These whole-fixture chains are separate from the charged alias transactions and must not be added again as a launch penalty. They include actual RF read/x-store/start/first-issue dependencies. There is no assumed tens-of-nanoseconds launch or ideal overlap.

The bench clock is10ns. Measured edge counts have **no SS/FF or native-GPU nanosecond credit**.1.2GHz streaming/.9GHz serial entries in the model remain candidate domain bindings. The full-token expression stays symbolic wherever an endpoint is absent; native ADD/MUL-only budget is not reported as full kernel latency.

## Missing endpoints for next implementation

Machine-readable per-PC endpoint lists are in both target files. The next ordinary path needs RF word/lane gather and coefficient broadcast, exact INT SHR/AND/XOR/IADD/ISUB/BF16 round support, and ordered shared-tree load/store/retirement. This closes the emitted normalization/HC nodes while preserving their existing rounding identities. Existing native matrix descriptors still need full-shape column/row mapping and actual versioned RF→x-store delivery. Attention/softmax additionally needs exact EXP/reciprocal, context tile/refill and denominator ownership; routing needs native compare/global-ID ties and IEEE sqrt for the DS router/Engram contracts. Packed QDQ, paired publication, persistent reader retirement and rank gather/reduce/expert/Engram services remain separate required endpoints.

Before new RTL, Maxwell can consume exact operand ranges, workspace/replica counts, per-port bit demand and per-PC duration terms from this package to admit an off-by-default INT/lane-route successor. The current IR cannot authorize build or token-rate claims while those routing/area/latency terms are unresolved. Goodall retains sole H1 runtime ownership; this work launches no successor or duplicate binary.

## Replay and guards

From this worktree:

```
python3 tools/h3_versioned_lowering.py --verify --out results/uarch/h3_versioned_lowering_20261002
python3 -m pytest -q tests/test_h3_versioned_lowering.py
```

Twelve tests pass: full graph coverage, correct gather extent and append-generation reads, live RF/spill alias rejection, workspace exclusion, early-retirement rejection, missing-duration rejection, chunk/tree order mutants and actual-H1 calibration/scope guards. Exact compiler replay independently regenerates both IR objects and all model data. A JSON integer/string case-key replay mismatch is also preserved in `preparation_failure2.json`; replay now compares normalized JSON objects. One metadata-preparation KeyError (`topk_local` carriesk, notn) is preserved under `preparation_failure1.json`; no simulation or numerical failure was involved.
