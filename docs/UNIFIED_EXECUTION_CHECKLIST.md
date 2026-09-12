# Unified ABI 3.0 execution checklist

**Checklist ID:** TA-CHK-3.0
**Owner:** single unified implementation agent (no parallel top-level owners)
**Baseline commit:** c83e543
**Issue date:** 2026-08-29
**Last reconciled:** 2026-09-04 — froze the simple ABI 3.0 live-buffer profile,
removed ABI 3.1/durable-restart work from the active path, re-read every current
deployment certificate, integrated host-only DeepSeek performance observation
and bounded decoded-weight caching, corrected DeepSeek learned-index rounding,
strengthened the Qwen long-run checker, regenerated the generic and shipped
control campaigns, made the exact-200K Gate-B launcher and final accelerator-pair
checker fail closed, derived required program features from emitted operations,
extended the source-bound shipped-program engine-prefix campaign through Qwen
query/key RoPE and DeepSeek wafer multicast, qualified exact DeepSeek `HC_PRE`
tile scheduling, standalone certifying nonpositive-exp/direct-sigmoid RTL, and
the atomic source-major 4x4 stable-softmax front end over first/final checkpoint
blocks,
added authenticated ABI 3.0 request-symbol transport for
genuine batch admission, made the authenticated request cap device-enforced
with independent heterogeneous-lane retirement, and retained the first
exact-token frozen-source Qwen HBM/SRAM accelerator diagnostic, then qualified
exact Qwen ROM/HBM PC-32/35 KV
appends and fixed-context-17 PC-38 GQA arithmetic. The production scalar token
runner now makes decoded-text legitimacy part of the run verdict: it binds the
checkpoint tokenizer, round-trips the frozen input context, and retains
raw/visible oracle-horizon output text rather than accepting integer equality
alone.
**Current execution checkpoint (2026-09-04):** all four current deployments
contain zero ABI `STATE` resources. Qwen HBM passes 21/21 deployment checks <!-- figure: 21 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].passed_check_count" name="current Qwen HBM checks, checkpoint" --> at
74 instructions <!-- figure: 74 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.instructions" name="current Qwen HBM instructions, checkpoint" --> and 221 descriptors <!-- figure: 221 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.descriptors" name="current Qwen HBM descriptors, checkpoint" -->; Qwen ROM passes 63/63 schedule checks <!-- figure: 63 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].passed_check_count" name="current Qwen ROM checks, checkpoint" --> at
74 instructions <!-- figure: 74 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.instructions" name="current Qwen ROM instructions, checkpoint" --> and 215 descriptors <!-- figure: 215 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.descriptors" name="current Qwen ROM descriptors, checkpoint" -->. DeepSeek HBM passes 36/36 checks <!-- figure: 36 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].passed_check_count" name="current DeepSeek HBM checks, checkpoint" --> at
1,286 instructions <!-- figure: 1286 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.instructions" name="current DeepSeek HBM instructions, checkpoint" -->, 3,341 descriptors <!-- figure: 3341 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.descriptors" name="current DeepSeek HBM descriptors, checkpoint" --> and exactly 32 nodes <!-- figure: 32 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.node_count" name="current DeepSeek HBM nodes, checkpoint" -->; DeepSeek ROM passes
129/129 checks <!-- figure: 129 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].passed_check_count" name="current DeepSeek ROM checks, checkpoint" --> at 1,323 instructions <!-- figure: 1323 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.instructions" name="current DeepSeek ROM instructions, checkpoint" --> and 3,135 descriptors <!-- figure: 3135 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.descriptors" name="current DeepSeek ROM descriptors, checkpoint" -->. The shipped RTL
campaign correlates prefill and decode for all four deployments on Icarus and
Verilator with 594,004 checks per simulator <!-- figure: 594004 src="results/rtl/abi3_deployment_campaign.json#cases[name=iverilog].checks" name="current shipped-profile RTL checks, checkpoint" --> and explicitly proves
`STATE_COMPAT=0` refusal before fetch. The standalone engine campaign correlates
11 bounded opcode pairs <!-- figure: 11 src="results/rtl/abi3_engine_campaign.json#correlation.family_count" name="current RTL engine families, checkpoint" --> over 135 cases <!-- figure: 135 src="results/rtl/abi3_engine_campaign.json#correlation.case_count" name="current RTL engine cases, checkpoint" --> with 40,878 checks per simulator <!-- figure: 40878 src="results/rtl/abi3_engine_campaign.json#checks_per_simulator.iverilog" name="current RTL engine checks, checkpoint" --> and
catches all 7 compiled RTL mutations <!-- figure: 7 src="results/rtl/abi3_engine_campaign.json#mutation_sensitivity.mutation_count" name="current caught RTL mutations, checkpoint" -->. These are control-plane and bounded
datapath evidence respectively. The bounded base integration witness runs 28
real launches across the four shipped decode prefixes, checks 91,136 compact
result words through 94 views under Verilator, and binds unchanged arithmetic
blocks to retained dual-simulator qualification. The frozen multicast overlay
adds one exact DeepSeek ROM PC-13 launch and checks all 4,194,304 writes across
256 participants. Its full Verilator replay passes 12,756,653 checks; focused
Icarus passes 12,587,599 with the same DeepSeek-ROM case record. Qwen next traps
at PC 32 `DMA.SCATTER` in that shared prefix. Focused continuations execute the
exact PC-32/35 KV appends and fixed-context-17 PC-38 `ATTENTION.GQA` for both
Qwen backends on Icarus and Verilator; PC 41 `TENSOR.MATMUL` is now the next
shipped Qwen operation without a connected datapath. DeepSeek ROM remains at PC
15 `VECTOR.MHC` after multicast, and DeepSeek HBM at PC 14 `VECTOR.MHC`. The
legal token ID 0 embedding remains a
bounded synthetic probe, not a decoded model token. The overlay is
classified `source_current_bounded_prefix_only`; it is source-current after the
canonical refresh but remains non-promotable as full model execution.
This is not a full token-producing RTL system and supplies no TPOT point.
**Controlling ABI profile:** KV, compressed KV, compressor history, tokens, and
intermediates are ordinary live HBM/SRAM buffers. Existing tensor views, events,
and a token-step fence provide addressing and ordering. Runs are uninterrupted
and fail-stop. Link retry is packet-only. There is no production state-member,
journal, rollback, checkpoint/restart, anti-rollback, durable publication, or
model-operation retry gate. Historical rows below that describe old `STATE`
or restart experiments remain provenance only and do not override this profile.
**Top-level progress:** **83/94 complete (88.3%)**, **10 partial**, **1 open**,
and **0 blocked**, counting only the `Wn.m` rows below.
**Remaining top-level rows:** partial — W8.3, W8.4, W8.5, W9.4, W9.5,
W10.1, W10.2, W11.1, W11.3, W13.4; open — W11.2.
**Certification freshness:** commit `6633a3b` canonically rebuilds the affected
deployments and refreshes the deployment-bound shipped-prefix campaigns after
the dynamic-batch/request-symbol, DeepSeek scheduler, and release-profile
integrations. The overlay is `source_current_bounded_prefix_only`: current for
its exact prefix, never a full token or TPOT result. DeepSeek token
captures predate the
`INDEX_SCORE` single-rounding repair and are prior-build evidence. One Qwen
exact-8K HBM/SRAM capture from Git tree
`008bf765e212c061f930d5a2726563f7ddeba740` produces the exact four-token oracle
sequence and EOS; it predates the later batch/request-symbol runtime changes
and is frozen-source diagnostic evidence. It may not be promoted or paired
with new HBM-B/ROM captures as current-release acceptance.
**DeepSeek Gate-B preflight:** the strict source-current EOS-or-256 oracle
checker is implemented (`7b3f77c`, hardened at `93a7c58`), and `9303615` adds
one fail-closed `--gate-b-production` launch profile. It admits only the exact
200,000-token workload, fixes first EOS or exactly 256 outputs, allocates
200,320 aligned KV positions, forces the qualified tiled-prefill geometry,
rejects alternate paths and stale input hashes before model construction,
requires a full 166.9 GB checkpoint hash before model import, validates the
qualified package/CUDA/`sm_120`/TF32-off/Hadamard/head-split/FP8-fallback stack,
and rehashes producer and input identities at completion. This is launch-ready
at tooling scope; the full hash and real production oracle have not run. The
canonical preflight still rejects the retained 200K eight-token record with 41
reported problems, so Gate B remains open.
**DeepSeek accelerator-pair preflight:**
`tools/check_deepseek_v4_200k_accelerator_acceptance.py` is implemented and
covered by 26 focused tests. It requires an accepted Gate-B oracle first, then
independently authenticates one exact ROM-wafer record and one exact 32-node-HBM
record, exact 200,000-token input, first-EOS-included or exactly-256 output,
zero production `STATE`, exact tokens/text, per-step success, counters,
implementation identity, and association equality after 32-node normalization.
This checked tooling item does not change the 83/10/1 top-level arithmetic and
does not substitute for the absent production pair.
**Generated companion:** `docs/PROGRAM_STATUS.md` and its JSON are regenerated
in a follow-on status commit after the source/documentation checkpoint is clean.
**Dependency spine:** W10.1 → W11.1; W10.2 is a parallel mandatory Phase-F
acceptance lane. W8.3/W8.4/W8.5/W9.4 → W9.5. W11.1 and W9.5, the DeepSeek
200K accelerator pair, and W11.2-specific capability, cycle, physical, fabric,
area/energy and uncertainty prerequisites all feed W11.2. W10.2, W11.3 and
W13.4 can otherwise proceed independently.
**Remaining-work order:** (1) finish the shared-cycle/co-issue and RTL-session
prerequisites, then freeze one final identity and relaunch Qwen W10.1 HBM A;
(2) launch independent HBM B and ROM from that same snapshot, pass the strict
three-capture gate, then complete the natural chat/reasoning/agentic/stress and
genuine heterogeneous B=2/4/8 matrix; (3) execute DeepSeek
`--gate-b-production` through EOS or 256 when resources permit, including both
full-byte identity boundaries; (4) canonically rebuild the stale deployment
certificate, generalize Qwen GQA beyond its fixed context-17 proof and extend
RTL from Qwen PC-41 `TENSOR.MATMUL`, DeepSeek ROM PC-15 `VECTOR.MHC`, and
DeepSeek HBM PC-14 `VECTOR.MHC` across every required
operator, memory/link service, selection, append, and EOS path;
(5) pass short integrated-token diagnostics, then run the wafer-ROM and
exact-32-node HBM
accelerators at exact 200K and pass the accelerator-pair checker; (6) accept
measured TPOT only from those same correctness-qualified executions, then run
correctness-qualified batch sweeps; (7) complete W8.3/W8.4/W8.5/W9.4 and the
four-target SKY130/ASAP7 characterized rerun in W9.5; and (8) close W11.2 only
when its
functional, cycle, physical, fabric, area/energy, and uncertainty prerequisites
are jointly admissible. W11.3 provenance work can proceed independently.
**Correctness-before-performance rule:** correct output tokens are Gate 1 and
desired TPOT is Gate 2. A batch point is promotable only when the same execution
records legal IDs, decoded text, complete oracle equality, first-EOS-included or
exact-cap stopping, no post-EOS step, correct-token count, first divergence,
prefill/TTFT, raw decode-step latencies, steady-state TPOT, aggregate throughput,
and all topology/process/capability/deployment/source identities. Existing
multi-batch roofline and cycle tables produce no model tokens and remain
projected columns, never executed TPOT.
**Current W10 preflight checklist:**

- [x] P10.1 Freeze exact first-EOS-or-256 natural and exact-32 stress terminal rules.
- [x] P10.2 Repair the attention and storage/placement compiler proof gates.
- [x] P10.3 Qualify the 8,256-row source/IR/KV/RoPE/workload/capability boundary.
- [x] P10.4 Harmonize both products at 512 rows and prove verifier-safe final-block padding.
- [x] P10.5 Record executed shapes and add independent natural/stress acceptance validators.
- [x] P10.6 Pass fresh temporary one-token HBM/ROM smoke with identical association manifests.
- [x] P10.7 Rebuild standard bundles and refresh retained deployment, schedule and numeric evidence — current Qwen HBM/ROM certificates pass 21/21 and 61/61 checks with zero `STATE`; current DeepSeek HBM/ROM certificates pass 36/36 and 123/123 with zero `STATE`.
- [ ] P10.8 Produce and accept two complete W10.1 HBM natural captures.
- [ ] P10.9 Produce and accept the complete W10.2 HBM/ROM stress pair.
- [x] P10.10 Remove restart exactness from the acceptance path — the frozen
  execution profile is uninterrupted and fail-stop; prior checkpoint experiments
  remain historical evidence only.
- [x] P10.11 Bind every execution-authoritative simulator source into W10
  acceptance provenance — `runtime/sim/weight_cache.py` is now mandatory even
  when the decoded immutable-weight cache budget is zero, so a cache-path change
  cannot inherit an older natural/stress acceptance identity (`b27dc80`).

**Execution concurrency:** requirement audits, dry lowerings, focused tests,
validators and documentation run in parallel. Each short source-current Qwen
smoke peaked near 18.5 GiB RSS and the two were safe to run independently. The
data-bearing 8K lanes remain serialized until the first complete source-current
run records trustworthy peak RSS and I/O headroom with `/usr/bin/time -v`;
subsequent clean runs may overlap only in distinct publish/output paths and only
when measured resource margin makes that safe. This preserves speed without
turning resource contention into another uncontrolled execution variable.
**Freshness boundary:** the marker count records milestones closed with retained
evidence; it is not a count of source-current evidence horizons. Longer Qwen
EOS, 24/192-token, reasoning, closed-loop agentic and historical 8K records, all
DeepSeek accelerator token records, and all restart records remain historical
evidence. None may be presented as a rerun of the current source.
**Status legend:** `[ ]` not started · `[~]` in progress · `[x]` done and evidenced · `[!]` blocked/deferred with reason

> This checklist is the single source of truth for program progress. It supersedes
> the per-lane status tables in the four planning documents where they disagree.
> Every `[x]` must name the artifact or test that proves it.

---

## W0 — Architecture freeze and plan repair

- [x] W0.1 Record TA-A3-ARCH-0 disposition (accept ADR-003 + wire format TA-ABI3-WIRE-1) — `docs/TA_A3_ARCH_0_REVIEW_AND_PLAN_REVISION.md`
- [x] W0.2 Revise plans: replace 4-parallel-owner model with unified-owner model — same document, section 4
- [x] W0.3 Freeze the *feasibility-corrected* workload contract (what actually runs, on what hardware, at what boundary) — same document, section 5
- [x] W0.4 Freeze the "engine arithmetic substrate" decision (numpy/torch as engine datapath, not as model) — same document, section 7
- [x] W0.5 Freeze repository ownership paths and module contracts — `runtime/abi3/`, `runtime/sim/`, `compiler/ir/v3/`, `compiler/backends/`

## W1 — ABI 3.0 core (blocking dependency for everything)

- [x] W1.1 `spec/abi3/` normative record definitions (from TA-ABI3-WIRE-1) — `spec/abi3/{records,descriptor_payloads,registries,counters}.json`, generated from the encoder with a `--check` drift gate
- [x] W1.2 `runtime/abi3/` encoder/decoder: program header, 32B instruction, descriptor header + 14 typed payloads — `runtime/abi3/records.py`, `descriptors.py`
- [x] W1.3 Host submission/completion record codec — `runtime/abi3/records.py` Submission/Completion
- [x] W1.4 Capability record + feature-bit registry + counter registry — `runtime/abi3/capability.py`, `runtime/sim/counters.py` (124 counters — `len(runtime.sim.counters.COUNTERS)`; the
  registry publishes the names in `spec/abi3/counters.json` but no scalar count, so
  this one figure has no producer a checker can read)
- [x] W1.5 Independent verifier (loop bounds, work bound, branch targets, event/state proofs, permissions, CRC/digests) — `runtime/abi3/verifier.py` (11 proofs)
- [x] W1.6 Deployment manifest + digest binding + signature metadata — `runtime/abi3/deployment.py`
- [x] W1.7 Tiny deterministic fixture lowered through HBM and ROM storage classes; byte-identical rebuild; corruption rejection — `runtime/abi3/fixture.py` — HBM and ROM builds, byte-identical rebuild, 4 corruption classes rejected
- [x] W1.8 Unit tests for every record type and every fail-closed path — `tests/abi3/` — 557/557 full tests pass; wire-format parser mutation-tested against 7 injected drifts

## W2 — Neutral IR v3

- [x] W2.1 Model Graph v3 schema (source semantics, phases, state effects, numeric-contract IDs) — `compiler/ir/v3/kernel_ir.py`
- [x] W2.2 Tensor Kernel IR v3 schema (target numerics, iteration domains, tensor views, deps, counter classes) — `compiler/ir/v3/kernel_ir.py` + `lowering.py` (53 kinds mapped)
- [x] W2.3 Neutrality checker (no ROM/HBM/SRAM/stage/queue/address terms in either IR) — `compiler/ir/v3/kernel_ir.py::check_neutral`
- [x] W2.4 Qwen3-8B exporter → Model Graph v3 → Kernel IR v3 — `compiler/frontends/v3/qwen3.py`; 728 kernels, 1165 tensors, 36 legacy semantic state declarations lowered to ordinary live buffers, all 399 weight bindings verified against 16,381,470,720 real checkpoint bytes; graph_id `84bb97dd1243…` <!-- figure: 728 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.kernels" name="Qwen kernels" --> <!-- figure: 1165 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.tensors" name="Qwen tensors" --> <!-- figure: 36 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.states" name="Qwen legacy semantic state declarations" --> <!-- figure: 16,381,470,720 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.bound_weight_bytes" name="Qwen bound weight bytes" --> <!-- figure: "84bb97dd1243…" src="results/abi3/program_status.json#neutral_ir.qwen3-8b.graph_id" name="Qwen graph id" -->
- [x] W2.5 DeepSeek-V4-Flash exporter → Model Graph v3 → Kernel IR v3 — `compiler/frontends/v3/deepseek_v4.py`; 3956 kernels, 7047 tensors, 229 legacy semantic state declarations lowered to ordinary live buffers, and 156,015,698,140 bound weight bytes <!-- figure: 3956 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.kernels" name="DeepSeek kernels" --> <!-- figure: 7047 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.tensors" name="DeepSeek tensors" --> <!-- figure: 229 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.states" name="DeepSeek legacy semantic state declarations" --> <!-- figure: 156,015,698,140 src="results/abi3/program_status.json#neutral_ir.deepseek-v4-flash-0731.bound_weight_bytes" name="DeepSeek bound weight bytes" -->
- [x] W2.6 Cross-model operator union report; both exporters pass one schema + verifier — `tests/compiler/test_neutral_ir_cross_model.py` (33 gates); union published as `spec/abi3/numeric_contract_union.json` (67 contracts) <!-- figure: 67 src="spec/abi3/numeric_contract_union.json#contract_count" name="numeric contract union size" -->

## W3 — Functional simulator (ABI 3.0 device)

- [x] W3.1 Device memory model (HBM/SRAM/ROM/host windows, permissions, mmap-backed weight regions) — `runtime/sim/memory.py` (mmap-backed, strided zero-copy views)
- [x] W3.2 Microsequencer: fetch/decode/retire, loops, predicates, events, waits, fences, traps, completion — `runtime/sim/device.py`
- [x] W3.3 Direct live-buffer execution — model caches and histories are
  ordinary HBM/SRAM memory objects addressed by tensor views and ordered by
  events plus the token-step fence. `runtime/sim/device.py` retains historical
  ABI 3.0 transactional-state compatibility code, but all four production
  deployments emit zero `STATE` resources and acceptance rejects any use of it
- [x] W3.4 DMA engine (transfer/fill/gather/scatter) — `runtime/sim/engines/dma.py`
- [x] W3.5 Tensor engine — `runtime/sim/engines/tensor.py` + `runtime/sim/formats.py`
- [x] W3.6 Vector engine (rmsnorm, head-rmsnorm, rope, add, silu-mul, convert, scale, softmax, compress, mhc, hadamard, index-score, sqrt-softplus) — `runtime/sim/engines/vector.py`
- [x] W3.7 Attention engine (dense/GQA/sparse) — `runtime/sim/engines/attention.py`
- [x] W3.8 Route engine — `runtime/sim/engines/route.py`
- [x] W3.9 Reduction engine — `runtime/sim/engines/reduction.py`
- [x] W3.10 Selection engine (argmax, token append, EOS) — `runtime/sim/engines/selection.py`, on-device
- [x] W3.11 Link engine (send/recv/remote-dma/multicast/gather/scatter/collective/barrier) for 32-node + wafer — `runtime/sim/engines/link.py`
- [x] W3.12 Observation plus compatibility-only recovery engines and full
  counter set — sequencer-executed; 124-counter registry published. Recovery
  remains legacy ABI 3.0 compatibility coverage and is absent from the
  zero-`STATE` production profile.
- [x] W3.13 Host queue driver — `runtime/driver.py`, real 128-byte submission/completion records per token

## W4 — HBM/SRAM backend (shared chip; 1 node Qwen, 32 nodes DeepSeek)

- [x] W4.1 Physical Plan IR (allocation, tiling, banks, schedules, topology) — `compiler/backends/hbm_sram/plan.py`
- [x] W4.2 Weight/live-buffer allocator + HBM address map (mmap-backed, no 16/156 GB copy) — zero-copy: 14 objects over 399 checkpoint ranges for Qwen, 224 objects over 68,214 ranges for DeepSeek; no monolithic weight image written
- [x] W4.3 Tiling + loop-nest schedule synthesis (loop-compressed programs) — current Qwen HBM deployment emits 74 instructions from 728 neutral kernels; tiling remains in SCHEDULE descriptors <!-- figure: 74 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.instructions" name="current Qwen HBM instructions" --> <!-- figure: 728 src="results/abi3/program_status.json#neutral_ir.qwen3-8b.kernels" name="Qwen kernels, W4.3" -->
- [x] W4.4 Descriptor + program emission (ABI 3.0) — `compiler/backends/hbm_sram/lower.py`
- [x] W4.5 Independent legality checker (reconstructs the plan without reusing the generator) — `compiler/backends/hbm_sram/check.py`, does not import the generator
- [x] W4.6 Qwen single-node deployment — `make abi3-hbm-qwen-deployment`
  rebuilds the current graph twice, checks both builds against the shipped
  bundle byte-for-byte, and publishes
  `results/abi3/hbm_qwen_deployment_certificate.json`. All **21/21** checks pass <!-- figure: 21 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].passed_check_count" name="Qwen HBM deployment checks passed, W4.6" -->.
  The independent checker and frozen verifier admit **74** instructions <!-- figure: 74 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.instructions" name="Qwen HBM deployment instructions, W4.6" --> and
  **221** descriptors <!-- figure: 221 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.descriptors" name="Qwen HBM deployment descriptors, W4.6" -->,
  including **0** `STATE` resources <!-- figure: 0 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.states" name="Qwen HBM STATE resources, W4.6" -->. Its **399** authenticated ranges <!-- figure: 399 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.weight_segments" name="Qwen HBM checkpoint ranges, W4.6" --> form
  **14** zero-copy weight objects <!-- figure: 14 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.weight_objects" name="Qwen HBM weight objects, W4.6" -->.
  The emitted live-buffer HBM map occupies **18,526,449,668** bytes per node <!-- figure: 18526449668 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.hbm_bytes_per_node" name="Qwen HBM bytes per node, W4.6" -->
  and the SRAM plan occupies 29,360,128 bytes <!-- figure: 29360128 src="results/abi3/hbm_qwen_deployment_certificate.json#cases[case=qwen3-hbm-single-chip].actual.sram_bytes_per_node" name="Qwen SRAM bytes per node, W4.6" -->. The topology is exactly one chip
  with no communication descriptors. This closes deterministic deployment, not
  W10 long-run correctness or RTL/physical closure.
- [x] W4.7 DeepSeek exact-32-node sharded deployment —
  `make abi3-hbm-deepseek-deployment` publishes
  `results/abi3/hbm_deepseek_deployment_certificate.json`; all **36/36** checks pass <!-- figure: 36 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].passed_check_count" name="DeepSeek HBM deployment checks passed, W4.7" -->.
  Two clean builds reproduce the shipped bundle byte-for-byte, and the verifier
  plus independent checker admit **1,286** instructions and **3,341** descriptors <!-- figure: 1286 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.instructions" name="DeepSeek HBM instructions, W4.7" --> <!-- figure: 3341 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.descriptors" name="DeepSeek HBM descriptors, W4.7" -->,
  with exactly **32** nodes <!-- figure: 32 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.node_count" name="DeepSeek HBM node count, W4.7" --> and **0** `STATE` resources <!-- figure: 0 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.states" name="DeepSeek HBM STATE resources, W4.7" -->. The global
  **256**-expert bank <!-- figure: 256 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.expert_bank_size" name="DeepSeek global expert bank, W4.7" --> is split into **8** consecutive experts per node <!-- figure: 8 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.experts_per_node" name="DeepSeek experts per node, W4.7" -->.
  Its **38** explicit communications <!-- figure: 38 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.communications" name="DeepSeek HBM communications, W4.7" -->
  comprise expert scatters, sparse-KV and activation all-gathers, expert
  all-reduces, and one token-step synchronization barrier. The certificate
  follows each data-bearing producer/link/consumer path and mutation-tests its
  queue, credit, predicate, and event ordering.
  The deployment retains **224** zero-copy weight objects <!-- figure: 224 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.weight_objects" name="DeepSeek HBM weight objects, W4.7" --> over
  **68,214** authenticated ranges <!-- figure: 68214 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.weight_segments" name="DeepSeek HBM checkpoint ranges, W4.7" -->
  and holds **13,445,013,724** weight bytes per node <!-- figure: 13445013724 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.weight_bytes_per_node" name="DeepSeek weight bytes per node, W4.7" -->.
  The maximum-context map occupies **88,080,248,832** bytes per node <!-- figure: 88080248832 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.hbm_bytes_per_node" name="DeepSeek HBM required bytes per node, W4.7" --> of
  **103,079,215,104** available <!-- figure: 103079215104 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.hbm_available_per_node" name="DeepSeek HBM available bytes per node, W4.7" --> and leaves **14,998,966,272** bytes of checked headroom <!-- figure: 14998966272 src="results/abi3/hbm_deepseek_deployment_certificate.json#cases[case=deepseek-v4-flash-hbm-cluster].actual.hbm_headroom_per_node" name="DeepSeek HBM headroom per node, W4.7" -->.
  This closes deterministic placement and causal cluster dataflow; full token,
  cycle, integrated RTL, and physical claims retain separate gates.

## W5 — ROM backends

- [x] W5.1 Common ROM contracts (immutable regions, repair map, inverse reconstruction) — `compiler/backends/rom/common/image.py` incl. repair map
- [x] W5.2 Qwen conventional single-chip ROM partition, images, schedules,
  and deployment — the current independent schedule certificate admits **74** instructions <!-- figure: 74 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.instructions" name="current Qwen ROM instructions, W5.2" -->,
  **215** descriptors <!-- figure: 215 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.descriptors" name="current Qwen ROM descriptors, W5.2" --> and **14** schedules <!-- figure: 14 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.schedules" name="current Qwen ROM schedules, W5.2" --> with **0** `STATE` resources <!-- figure: 0 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].actual.states" name="Qwen ROM STATE resources, W5.2" -->.
  Historical token records bind older 75-instruction/239-descriptor builds and
  remain prior-build execution evidence rather than the identity of this
  current deployment.
- [x] W5.3 DeepSeek wafer-scale reticle/tile ROM placement, on-wafer fabric,
  distributed live HBM buffers, and deployment — the current schedule
  certificate admits **1,323** instructions <!-- figure: 1323 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.instructions" name="current DeepSeek ROM instructions, W5.3" -->,
  **3,135** descriptors <!-- figure: 3135 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.descriptors" name="current DeepSeek ROM descriptors, W5.3" -->,
  **108** schedules <!-- figure: 108 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.schedules" name="current DeepSeek ROM schedules, W5.3" --> and **18** on-wafer communication records <!-- figure: 18 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.communications" name="current DeepSeek ROM communications, W5.3" -->,
  with **0** `STATE` resources <!-- figure: 0 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].actual.states" name="DeepSeek ROM STATE resources, W5.3" -->.
- [x] W5.4 Inverse proof: ROM image → original weights bit-exact — inverse proof passes bit-identically over 16.4 GB and 156 GB
- [x] W5.5 Independent schedule checker —
  `compiler/backends/rom/common/check.py` imports neither the ROM producer nor
  either product backend. It independently reconstructs engine mappings,
  shard/bank placement, mutable ports, queues, resources, events, loops,
  wafer participants, traffic classes, route tables, and byte/flit/stall
  bounds; the frozen ABI verifier is supplemental. `make
  abi3-rom-schedule-check` publishes `results/abi3/rom_schedule_checks.json`:
  Qwen passes **63/63** checks over 74 instructions and 14 schedules <!-- figure: 63 src="results/abi3/rom_schedule_checks.json#cases[case=qwen3-rom-single-chip].passed_check_count" name="Qwen independent ROM schedule checks passed" -->,
  while DeepSeek passes **129/129** checks <!-- figure: 129 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].passed_check_count" name="DeepSeek independent ROM schedule checks passed" --> over 1,323 instructions, 107 schedules and
  18 on-wafer communications.
  Both declare zero `STATE` resources. Capability-valid placement, dependency,
  queue, link-credit, and live-buffer mutations are rejected. This is an
  artifact-semantic schedule certificate, not cycle timing or physical-route
  evidence.

- [x] W5.6 DeepSeek 32-node reticle-class ROM **array** (TA-DS-ROM-ARRAY-FLASH,
  `compiler/backends/rom/deepseek_v4_array.py`, plan
  `docs/DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md`) — the same neutral graph
  on the HBM cluster's `CLUSTER_32` topology, link record and engine lane mix,
  with the routed expert banks node-sharded by consecutive ownership (eight
  experts per node, A28 `node_segments` images) and a data-bearing
  `LINK.COLLECTIVE SUM` per routed group ahead of `EXPERT_REDUCE`. The
  source-current sparse-corrected build admits **1,344** instructions <!-- figure: 1,344 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].actual.instructions" name="array ROM instructions, W5.6" -->,
  **3,165** descriptors <!-- figure: 3,165 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].actual.descriptors" name="array ROM descriptors, W5.6" -->,
  **19** cluster communication records <!-- figure: 19 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].actual.communications" name="array ROM communications, W5.6" -->,
  and **0** `STATE` resources <!-- figure: 0 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].actual.states" name="array ROM STATE resources, W5.6" -->,
  and is byte-identical on a second clean build. Its shared
  liveness allocator reduces 1,073,359,364,104 logical activation bytes to an
  83-slot, 172,292,907,016-byte arena; total per-node HBM use is
  178,281,603,216 bytes against the physical five-stack 180,000,000,000-byte
  declaration. `results/abi3/deepseek_v4_activation_liveness_capacity.json`
  retains the source identities, admission result, capacity arithmetic, and
  HBM-planner equivalence. Against this deployment identity the independent
  schedule checker passes **140/140** checks <!-- figure: 140 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].passed_check_count" name="array independent ROM schedule checks passed" -->,
  including the four phase-layout convergence rules the sparse-phase lowering
  required, and the regenerated inverse proof reconstructs all
  **156,015,698,140** payload bytes <!-- figure: 156,015,698,140 src="results/abi3/deepseek_v4_rom_array_inverse.json#report.payload_bytes" name="array inverse payload bytes, W5.6" -->
  bit-identically from the node-sharded images. This is compiler/capacity
  evidence, not cycle timing or a token result; the array's functional and
  cycle runs are tracked in the plan.

## W6 — Real end-to-end execution (the correctness spine)

> **Retained evidence freshness.** Every token record in W6 is prior-build
> milestone evidence at the 2026-09-03 checkpoint. Qwen records predate the
> current live-buffer runner/acceptance source. DeepSeek records additionally
> predate the `INDEX_SCORE` one-round product-add correction. They demonstrate
> earlier end-to-end reachability but do not close a source-current acceptance
> horizon.

- [x] W6.1 Qwen-HBM: short prompt → prefill → decode → real tokens — **token-identical to the reference oracle**, and **decode reaches a real EOS**. `TA-QW-AGENT-1` ran 112 prompt tokens to the natural stop at token 151645 after 23 tokens (`results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json`) <!-- figure: 112 src="results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json#record.workload.prompt_token_count" name="TA-QW-AGENT-1 prompt tokens" --> <!-- figure: 23 src="results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json#record.generated_token_count" name="TA-QW-AGENT-1 decoded tokens" --> <!-- figure: 151645 src="results/abi3/qwen3_hbm_ta-qw-agent-1_execution.json#record.generated_token_ids[22]" name="TA-QW-AGENT-1 final token is EOS" -->, `TA-QW-CHAT-1` ran 24 tokens (`..._ta-qw-chat-1_...`); both agree with the oracle at every position, with no legitimacy problems and every admission check passing — 27 of them on the agent record and 29 on the chat record, whose set is the agent's plus `block_extent` and `block_scale`, so it is a check set that grew between the two runs and not a run that skipped two
- [x] W6.2 Qwen-ROM: identical token sequence from the ROM deployment — **re-verified with retained execution evidence in the repository** (`results/abi3/qwen3_rom_ta-qw-chat-1_execution.json`, status pass, 24 tokens, `reference_agreement` true, no divergence index). The 24 tokens are identical to `qwen3_hbm_ta-qw-chat-1_execution.json` position for position, which is the claim this item makes. Both retained execution lanes admit at 75 instructions; the ROM lane emits 239 descriptors against HBM's 218 and declares 2,105 retired work against 22,715, because the two product backends block the token loop differently — see [OI-19] — 75 instructions, 239 descriptors, admitted; **24 tokens token-for-token identical to the external oracle and to the HBM target**. All 27 distinct prefill kernels diffed kernel-by-kernel against HBM through the `on_issue` hook: bit-identical, output hash for output hash, including the KV window and the final logits. Separately, the source-current static v2 storage-and-placement certificate reports 18 differing descriptors, all `MEMORY_OBJECT` and all ROM→HBM: 16 replace ROM-local placement with the required unplaced-HBM sentinel and 2 were already unplaced. Both generated builds admit, `holds` is true, and the residual-violation list is empty. That proof does not rerun or refresh the historical 24-token execution horizon, and its HBM-labelled member is not the shipped HBM product deployment <!-- figure: 18 src="results/abi3/storage_class_equivalence_qwen3.json#differing_descriptor_count" name="Qwen v2 differing descriptors" --> <!-- figure: 18 src="results/abi3/storage_class_equivalence_qwen3.json#storage_class_transitions['ROM->HBM']" name="Qwen v2 ROM to HBM transitions" --> <!-- figure: 16 src="results/abi3/storage_class_equivalence_qwen3.json#placement_transitions.rom_placement_to_hbm_unplaced" name="Qwen v2 placed to unplaced transitions" --> <!-- figure: 2 src="results/abi3/storage_class_equivalence_qwen3.json#placement_transitions.already_unplaced_to_hbm_unplaced" name="Qwen v2 already-unplaced transitions" --> <!-- figure: 75 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.instruction_count" name="Qwen ROM instructions, TA-QW-CHAT-1" --> <!-- figure: 239 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.descriptor_count" name="Qwen ROM descriptors" --> <!-- figure: 218 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.notes.verification.descriptor_count" name="Qwen HBM descriptors" --> <!-- figure: 2,105 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.notes.verification.declared_retired_work" name="Qwen ROM declared retired work" --> <!-- figure: 22,715 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.notes.verification.declared_retired_work" name="Qwen HBM declared retired work" -->
- [x] W6.3 DeepSeek-HBM (32 node): short prompt → real tokens — **retained
  prior-build evidence.** The recorded 32-token prompt completed one prefill
  plus three decode transactions and generated four oracle-identical tokens.
  Its topology and per-node counter checks remain useful milestone evidence,
  but the record predates the learned-index numeric repair and is not
  source-current acceptance.
- [x] W6.4 DeepSeek-ROM (wafer): identical short token sequence — **retained
  prior-build evidence.** Its one prefill plus three decode transactions matched
  the same four-token HBM/oracle prefix. It also predates the learned-index
  repair and must be rerun before any current cross-target claim.
- [x] W6.5 Independent reference oracle per model (from official modeling code) — external oracle: `tools/run_qwen3_reference_oracle.py`— token-level match
- [x] W6.6 Historical checkpoint/restart experiment on all four — **all four
  lanes passed at their recorded source identity, but restart is not an active
  ABI 3.0 production or acceptance requirement.**
  The historical campaign ran against one retained governed source map. Qwen
  HBM (`8e1185…`), Qwen ROM (`925351…`),
  DeepSeek ROM (`fa9077…`), and DeepSeek HBM (`a72c87…`) all bind the same
  governed **288-file** Python scope <!-- figure: 288 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.source_identity.baseline.python_file_count" name="restart governed Python file count" --> covering `compiler/`, `runtime/`, and
  `tools/run_abi3_restart_exactness.py`, with aggregate source digest
  `ee08b43d87bf6edbcd7b241e7c15a2c4c1a9cb180992dd2eeeee337902a18faf`.
  Every baseline, interrupt, fresh resume, negative control, and state-only
  control carries that complete per-file map, the current deployment, node
  count, and implementation identity; all **27/27** guards pass and the five
  phase/control PIDs are distinct in every artifact.

  The method runs an uninterrupted comparator and stops a second process after
  **2** generated tokens <!-- figure: 2 src="results/abi3/restart_exactness_qwen3_hbm.json#record.notes.stop_after_tokens" name="restart interruption token count" -->; it serialises the complete mutable simulator boundary and
  finishes the final token in a fresh process that loads only that checkpoint.
  Each lane reaches **3** generated tokens <!-- figure: 3 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.generated_token_count" name="restart generated-token horizon" --> with identical token
  sequence, retired work, aggregate architectural counters, every per-node
  counter, and sticky-overflow state. Erasing every STATE image changes the
  first resumed token; erasing HBM/HOST/SRAM scratch while retaining STATE
  reproduces the baseline, but that complementary observation is explicitly
  `reported_only`, not a pass gate. The current DeepSeek ROM checkpoint covers
  **438** mutable images <!-- figure: 438 src="results/abi3/restart_exactness_deepseek_rom_p32.json#record.notes.checkpoint.object_count" name="DeepSeek ROM restart object count" -->, **1,078,248,644,744** logical mutable bytes <!-- figure: 1,078,248,644,744 src="results/abi3/restart_exactness_deepseek_rom_p32.json#record.notes.checkpoint.mutable_bytes" name="DeepSeek ROM restart logical mutable bytes" -->,
  and **143,255,560** logical stored payload bytes <!-- figure: 143,255,560 src="results/abi3/restart_exactness_deepseek_rom_p32.json#record.notes.checkpoint.stored_bytes" name="DeepSeek ROM restart stored payload bytes" -->.

  The final 32-node HBM artifact binds deployment `2943197b…` and records the
  baseline and fresh-resume sequence `[13806, 345, 7472]`. The STATE-erased
  negative produces `[13806, 345, 7249]` and diverges at index **2** <!-- figure: 2 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.negative_control.first_divergence_index" name="DeepSeek HBM restart negative divergence index" -->; the state-only control matches and remains reported-only. Its schema-v2
  checkpoint spans **32** nodes <!-- figure: 32 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.checkpoint.node_count" name="DeepSeek HBM restart node count" --> and **8,992** writable objects <!-- figure: 8992 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.checkpoint.object_count" name="DeepSeek HBM restart object count" --> representing
  **2,447,390,804,224** logical mutable bytes <!-- figure: 2,447,390,804,224 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.checkpoint.mutable_bytes" name="DeepSeek HBM restart logical mutable bytes" --> in **5,136,187,520** logical stored payload bytes <!-- figure: 5,136,187,520 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.checkpoint.stored_bytes" name="DeepSeek HBM restart logical stored payload bytes" -->;
  checkpoint write and normal restore take **24.53** s <!-- figure: 24.53 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.checkpoint.write_seconds" name="DeepSeek HBM restart checkpoint write seconds" --> and **99.724** s <!-- figure: 99.724 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.checkpoint.restore_seconds" name="DeepSeek HBM restart checkpoint restore seconds" -->. The complete campaign records **10,599.7** s <!-- figure: 10599.7 src="results/abi3/restart_exactness_deepseek_hbm_p32.json#record.notes.wall_seconds" name="DeepSeek HBM restart campaign wall seconds" -->. These
  are sparse simulator-checkpoint quantities, not physical storage or
  performance evidence.

  The independent audit rehashed the exact 288-file set, all five phase
  identities, all 32 node-counter maps, every aggregate counter, process IDs,
  controls, and guards. The retained-artifact regression then passed all four
  current artifacts:
  `PYTHONPATH=. python3 -m pytest -q tests/test_abi3_restart_exactness.py -k
  retained_restart_artifacts_are_source_current_and_fully_gated`. The
  checkpoint writer replaces stale hardlinked payload paths atomically before
  current-run deduplication; its deterministic overwrite-after-hardlink
  regression remains in `tests/sim/test_checkpoint.py`. Evidence:
  `results/abi3/restart_exactness_{qwen3_hbm,qwen3_rom,deepseek_rom_p32,deepseek_hbm_p32}.json`.

  **Claim boundary:** this is functional NumPy restart over a **93**-token Qwen request <!-- figure: 93 src="results/abi3/restart_exactness_qwen3_hbm.json#record.workload.prompt_token_count" name="restart Qwen prompt length" -->
  and a 32-token DeepSeek prefix, split 2+1 generated tokens. It
  establishes no long-context, timing, performance, RTL, physical, silicon, or
  committed-durability result. OI-23 remains a historical diagnosis of that
  retired state-based profile; the shipped live-buffer profile neither depends
  on nor repairs its durability path.
- [x] W6.7 Historical fail-closed campaign —
  `tools/run_abi3_failclosed_campaign.py` refused 8/8 injected failures against
  its recorded Qwen deployment. Its prepared-state assertion belongs to the
  retired profile; the current production gate instead refuses all `STATE`
  resources/instructions before execution and terminates an admitted run
  fail-stop on its first fault.

## W7 — Cycle model and capability

- [x] W7.1 One event-driven cycle simulator over the same ABI 3.0 artifacts —
  `runtime/cycle/model.py`, with traces derived by running the frozen device
  itself. `runtime/cycle/batch.py` now schedules genuine B=1/2/4/8 ABI session
  waves over the same bounded queues, engines, memory, and fabric, and binds
  every request/token-commit tick to the exact functional transaction. The
  focused batch suite includes heterogeneous B=2 EOS and request-cap
  retirement: the request may narrow but cannot enlarge the compiled policy
  ceiling, the last non-EOS token carries the length-stop reason, and no
  post-terminal write or transaction is admitted. Commits `bb2ddf2`,
  `fd5dd1f`, and `daf6205` add the governed export path: authenticated
  workload/oracle/deployment inputs, exact per-lane tokens and raw/visible
  text, independent terminal evidence, source identities, and the raw
  request/token-commit ticks from the same physical batch. Its B=1/2/4/8
  focused tests qualify the mechanism only. No heterogeneous full-model B>1
  run, characterized target timebase, or correctness-qualified TPOT point
  exists yet; the existing singular-workload comparison contract also cannot
  promote a genuinely heterogeneous B>1 point until it gains a workload-set
  binding
- [x] W7.2 Capability records for SKY130 view and ASAP7 view (separately versioned) — five cost tables with per-parameter provenance
- [x] W7.3 32-node fabric model (latency, serialization, contention, credits, retry) — `runtime/cycle/fabric.py` ClusterFabric
- [x] W7.4 Wafer fabric model (reticle/tile routing, congestion, barriers) — `runtime/cycle/fabric.py` WaferFabric
- [x] W7.5 Counter reconciliation: functional == cycle == RTL for the same program — fixture/campaign coverage first established the three-way control-plane relation. The retained current-tree real-deployment result, `results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json`, now runs one 32-token prefill through the shipped DeepSeek HBM cluster deployment (`294319…`) and exits `SUCCESS` / `NONE`. Its independently rerun functional device agrees on all **66** compared architectural counters <!-- figure: 66 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#functional_agreement.counters_compared" name="DeepSeek HBM cycle counters reconciled, W7.5" --> with `differences: {}`; the schedule audit covers **447** operators <!-- figure: 447 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#schedule_audit.operators_checked" name="DeepSeek HBM cycle operators audited, W7.5" -->, is complete, and reports no findings or contract gaps. The model emits **244,691,019,251** cycles <!-- figure: 244,691,019,251 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#timing.total_cycles" name="DeepSeek HBM modeled prefill cycles, W7.5" --> only under a cost table with **124** assumed and **5** characterized parameters <!-- figure: 124 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#provenance.counts.assumed" name="DeepSeek HBM assumed cycle parameters, W7.5" --> <!-- figure: 5 src="results/abi3/deepseek_v4_flash_hbm_p32_prefill_cycle.json#provenance.counts.characterized" name="DeepSeek HBM characterized cycle parameters, W7.5" -->. It therefore closes governed schedule/counter reconciliation, not performance: the artifact is class `assumed`, has no full Python source map, does not stage the governed prompt payload, and does not compare its produced token with the external oracle. W8.8 separately correlates the shipped deployment control plane with RTL at its declared 16-token request shape; engine arithmetic is still not wired under that sequencer

## W8 — RTL 3.0

**Current sequencer/engine integration boundary:** the source-bound base
campaign connects the real sequencer and resolved-view stream to 28 exact
shipped-prefix launches and checks 91,136 compact result words through 94
resolved views under Verilator. It includes Qwen layer-zero Q/K/V MATMUL, head
RMSNorm, and query/key RoPE and binds the unchanged MAC and RoPE cores to
retained dual-simulator arithmetic evidence. Qwen next returns `CAPABILITY` at
PC 32 `DMA.SCATTER` in that shared bridge; the focused Qwen continuation below
advances the bounded arithmetic boundary through PC 38 to PC 41.
DeepSeek HBM does so at PC 14 `VECTOR.MHC`.

The frozen overlay
`results/rtl/abi3_shipped_prefix_multicast_campaign.json` additionally retires
the exact DeepSeek ROM PC-13 wafer `LINK.MULTICAST`. It checks all 4,194,304
destination writes for a nonzero 64-KiB live payload at 256 participants,
per-participant order, binomial-tree parents, CRC/NAK/replay, and deterministic
source/destination backpressure. The full four-case Verilator replay performs
12,756,653 checks; the DeepSeek-ROM-only Icarus replay performs 12,587,599 and
agrees on the normalized case. The ROM boundary is now PC 15 `VECTOR.MHC`
descriptor 381; aggregate prefix counts are 29 launches, 91,136 compact result
words, and 100 resolved views.

Commit `6633a3b` rebuilds the deployment certificate and retained campaign from
the current runtime source identity. The result is explicitly bounded-prefix
evidence rather than a full-execution promotion. Token ID
0 remains a bounded synthetic embedding probe, not a natural-context output.
These campaigns perform no prefill, whole transaction, token selection, EOS
handling, decoded-token validation, architectural TPOT, or physical
measurement. Correct output tokens remain Gate 1; TPOT from the same
correctness-qualified execution remains Gate 2.

The focused Qwen continuation
`results/rtl/a3_qwen_kv_scatter_campaign.json` closes both exact key/value KV
appends after that shared prefix for ROM and HBM. It validates the real
instruction, OPERATOR, TENSOR_VIEW, and NUMERIC records; consumes the retained
PC-29 key and PC-17 value result words; and compares all 69,632 words across
four active 17-row logical-plane results. Its six corruption/range negatives
and two exact PC-38 capability boundaries perform no writes. Icarus and pinned
Verilator each pass 209,076 focused checks.

The next focused continuation,
`results/rtl/a3_qwen_gqa_campaign.json`, promotes only that exact PC-38
capability boundary to fixed-context-17 arithmetic. One ROM case and one
backpressured HBM case each match all 4,096 BF16 outputs from an independent
scalar attention oracle. Across both simulators the retained evidence records
8,192 computed-word comparisons, 12,288 atomic sentinel checks, and 20,565
checks per simulator; a late input fault after all preceding arithmetic, a
valid-CRC wrong numeric contract, and an instruction-CRC corruption all
publish zero words. Generic Yosys 0.68 elaboration reports zero structural
problems. The query and current key/value row are authentic causal RTL results,
but prior-context rows 0 through 15 are deterministic synthetic transforms, so
this is not authentic context-17 model execution. The next shipped Qwen
operation without a connected datapath is PC 41 `TENSOR.MATMUL`, operators
134/137 for ROM/HBM. Neither focused run executes a whole layer or token,
handles EOS, emits architectural token-commit ticks, or establishes TPOT.

The separate exact `HC_PRE` scheduler campaign admits DeepSeek ROM PC 15 /
descriptor 381 and current HBM PC 14 / descriptor 545, proves the explicit
one-ID-shift semantic equivalence to the prior authenticated descriptor 546, and covers ROM T=1 and HBM
T=512/T=320/T=1 including `390 * 512 + 320 = 200,000`, and correlates 688,188
emitted tiles plus 11,346,434 checks on Icarus and Verilator. A focused T=1
continuation now runs exact BF16-by-FP32 fused accumulation, balanced
16,384-element RMS, all 24 projection rows, and the complete coefficient tail
behind both semantic configurations. Icarus 11.0 and pinned Verilator 5.050
agree on 1,379,450 checks, all 74 authenticated checkpoint numeric boundaries
per profile, and identical 24-word public results. It is not yet connected to
the ordinary shipped-prefix control/view/memory path and does not cover
T=512/T=320/all 200K prompt positions. Full layer integration, logits,
selection, append/EOS-or-cap control, and TPOT remain open. Standalone CR32
nonpositive exp and direct sigmoid pass 169,962 exact checks on both
simulators. The composed stable-softmax front end passes 2,394,764 checks per
simulator over 853 matrices, including every matrix in the first T=512 and
final T=320 checkpoint blocks; descriptor integration and the other 389
full-sized blocks remain open. The atomic stable-softmax/Sinkhorn composition
then passes 19,313,653 checks per simulator over those same 853 matrices,
reproduces the authenticated T=512 final combination output, and binds the
current HBM PC-14 descriptor 545 plus ROM PC-15 descriptor 381. The new T=1
continuation consumes the derived semantic configuration for each descriptor;
it still does not retire the raw shipped record through the ordinary prefix,
and none of these campaigns produces a token or TPOT point. All reported
operator/testbench cycles remain verification metadata, never TPOT.

- [x] W8.1 Microsequencer RTL (fetch/decode/loop/predicate/event/trap/complete) — `rtl/abi3/ot_a3_microsequencer.sv`; operand tensor-view resolution (A4 dynamic terms, A13 partial final extent, A18 extent axis/unit, A26 fixed-address edge masks) — `rtl/abi3/ot_a3_view_resolver.sv`
- [x] W8.2 Queue/event controller RTL and compatibility-only state controller —
  `rtl/abi3/ot_a3_event_scoreboard.sv` is active in the shipped profile.
  `rtl/abi3/ot_a3_state_controller.sv` remains available only when
  `STATE_COMPAT=1` for historical ABI 3.0 tests; the four-target production
  elaboration sets `STATE_COMPAT=0`, does not elaborate that controller, ties
  its counters to zero, and refuses a nonzero state-resource count before
  fetch.
- [~] W8.3 Representative engine datapaths (DMA, tensor MAC array, vector, selection) — **eleven `(family, subopcode)` pairs are bit-exact against the functional simulator's *real* engines within the campaign's stated bounds**: `TENSOR.MATMUL`, `DMA.GATHER`/`SCATTER`, `SELECTION.ARGMAX`, and seven VECTOR pairs (`ADD`, `CONVERT`, `SCALE`, `HADAMARD`, `INDEX_SCORE`, `COMPRESS`, `MHC`) in `rtl/abi3/`. The campaign correlates 135 generated ABI 3.0 programs <!-- figure: 135 src="results/rtl/abi3_engine_campaign.json#correlation.case_count" name="engine RTL cases, W8.3" --> executed by `runtime.sim.device.Device` with nothing stubbed — 14,468 result words compared <!-- figure: 14468 src="results/rtl/abi3_engine_campaign.json#correlation.result_word_count" name="engine RTL result words, W8.3" --> element by element on two simulators, 59,868 multiply-accumulates <!-- figure: 59868 src="results/rtl/abi3_engine_campaign.json#correlation.mac_count" name="engine RTL MACs, W8.3" -->, 92 refusals <!-- figure: 92 src="results/rtl/abi3_engine_campaign.json#correlation.fault_case_count" name="engine RTL faults, W8.3" --> with the destination proved untouched, and 2,576 exhaustive <!-- figure: 2576 src="results/rtl/abi3_engine_campaign.json#correlation.decode_probe_count" name="engine RTL decode probes, W8.3" --> storage-format decode probes and 5,200 <!-- figure: 5200 src="results/rtl/abi3_engine_campaign.json#correlation.arith_probe_count" name="engine RTL arithmetic probes, W8.3" --> binary32 add/multiply/round and exact-product-add probes against the exact `fractions.Fraction` reference; 40,878 checks per simulator <!-- figure: 40878 src="results/rtl/abi3_engine_campaign.json#checks_per_simulator.iverilog" name="engine RTL checks, W8.3" --> (`results/rtl/abi3_engine_campaign.json`). The refusals split into 17 Device faults <!-- figure: 17 src="results/rtl/abi3_engine_campaign.json#correlation.refusal_count_by_expectation_source.device_fault" name="engine RTL Device faults, W8.3" -->, 18 bounded-profile negatives <!-- figure: 18 src="results/rtl/abi3_engine_campaign.json#correlation.refusal_count_by_expectation_source.rtl_bounded_profile" name="engine RTL bound refusals, W8.3" --> and 57 descriptor-admission corruptions <!-- figure: 57 src="results/rtl/abi3_engine_campaign.json#correlation.refusal_count_by_expectation_source.rtl_descriptor_admission" name="engine RTL descriptor refusals, W8.3" -->. Contraction coverage remains BF16 x BF16, FP8 E4M3FN x FP8 E4M3FN and block-scaled MXFP4 E2M1 x FP8 E4M3FN under `bf16_bf16_fp32_sequential_rne_v1`, including amendment A15's two-dimensional scale block.
  The six VECTOR additions are deliberately bounded: unscaled one-input/one-output `CONVERT` (at most 512 elements); constant or same-shape BF16 `SCALE` (at most 512 elements); normalized 128-point BF16 `HADAMARD` (at most four rows); batch-one, four-head, unit-scale BF16 `INDEX_SCORE` (at most four sites, eight candidates and sixteen head channels); `COMPRESS_PROJECT` only (at most eight flattened rows, sixteen outputs and 64 reduction channels); and four-stream `HYPER_CONNECT_POST` only (at most four flattened sites and 32 hidden channels). `correlation.vector_rtl_scope` is the machine-readable authority. Late-poison vectors prove whole-destination atomicity in all six new blocks.
  **Still open, and named rather than implied:** general `SILU_MUL`, `SOFTMAX` and `SQRT_SOFTPLUS` remain absent from this engine array. A standalone certifying nonpositive-exp/direct-sigmoid unit, the fixed HC 4x4 stable-softmax composition, and a fixed-context-17 Qwen GQA datapath now exist; they are not general transcendental/softmax/attention engines and are not wired into this array or the shipped descriptor path. Sigmoid/general-broadcast SCALE, block-dequantizing/two-output-quantizing CONVERT, `COMPRESS_POOL`/`STATE_UPDATE`, `MHC_PRE`/`HEAD`, and non-unit-scale, non-four-head or batch-greater-than-one `INDEX_SCORE` are unsupported. Standalone `RMS_NORM`, `HEAD_RMS_NORM` and `ROPE` RTL remains outside this array. ATTENTION, ROUTE, REDUCTION and LINK remain absent from this engine-correlation campaign (W8.4 separately covers standalone link/channel/router/collective RTL); W8.2's state controller is compatibility-only and absent from the shipped profile. The *blocked* contraction contract is out of scope by construction; later-output atomicity remains unproved only for legacy `TENSOR.MATMUL` and `VECTOR.ADD`; and none of these datapaths is wired to the W8.6 sequencer. W8.8's separately promoted shipped-deployment evidence is control-plane correlation with recording no-op engines, not functional integration of this arithmetic.
  The retained campaign automatically compiles seven corrupted RTL variants — CONVERT rounding, SCALE arithmetic, Hadamard normalization, INDEX_SCORE ReLU, compressor plane order, compressor exact-product rounding and MHC matrix orientation — and both simulators reject all seven with no PASS marker. The earlier five-mutation exploratory exercise is preserved in the datapath report because **the reduction-order mutation it first missed is why two catastrophic-cancellation cases exist**. Physical evidence remains separate: **three legacy blocks are fully routed on SKY130 HD**, each meeting setup and hold with **0** DRC errors <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.drc_errors" name="selection DRC, W8.3" --> and **0** antenna violations <!-- figure: 0 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.antenna_violating_nets" name="selection antenna, W8.3" -->: `ot_a3_selection_argmax`, the block that decides the token, closes at 12 ns with **3.348** ns of slack <!-- figure: 3.348 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.setup_wns_ns" name="selection routed setup slack, W8.3" --> in a die of **47,430.3** um2 <!-- figure: 47,430.3 src="results/physical_abi3/sky130hd/a3_selection_argmax/physical.json#place_and_route.metrics.die_area_um2" name="selection die area, W8.3" -->; `ot_a3_vector_add` at 100 ns in **122,766** um2 <!-- figure: 122,766 src="results/physical_abi3/sky130hd/a3_vector_add/physical.json#place_and_route.metrics.die_area_um2" name="vector add die area, W8.3" -->; and `ot_a3_dma_index_mover` at 25 ns in **268,200** um2 <!-- figure: 268,200 src="results/physical_abi3/sky130hd/a3_dma_index_mover/physical.json#place_and_route.metrics.die_area_um2" name="dma die area, W8.3" -->. **`ot_a3_mac_lane` and all six new VECTOR blocks are not routed:** the lane's flow reached global routing and its driver was terminated before it could record, so its routed area, timing and power are unmeasured; the six additions have no physical artifacts at all. What the lane run did show is that it does *not* close at 60 ns, on the scale-address divider rather than the accumulator. **No frequency from a 130 nm open PDK may be scaled to N6/N5/N4 and none of this retires `power.fabric_clock_hz = 1e9`, which stays `assumed`.** `docs/ABI3_ENGINE_DATAPATH_RTL.md` states the boundary
- [~] W8.4 Inter-chip endpoint RTL (packets, credits, retry, collectives) — **the endpoint exists, and the traversal count the headline is priced on is now measured rather than derived.** `rtl/abi3/ot_a3_link_channel.sv` is one directed hop: a bounded credit window (`COMMUNICATION.credit_bound`), CRC32C per flit (`integrity_mode`), a monotone sequence, and go-back-N replay bounded by `retry_bound` and `timeout_class`. `ot_a3_mesh_router.sv` is a five-port X-then-Y dimension-ordered router; `ot_a3_collective_engine.sv` runs SUM/MAX/MIN all-reduce, BROADCAST, ALL_GATHER and a barrier; `ot_a3_link_node.sv` assembles them into a mesh node. Seven geometries x ten cases, **cycle-for-cycle identical** on Icarus 11.0 and Verilator 5.050, with every reduced binary32 code checked at every participant: 104,225 checks on the 8x8 mesh <!-- figure: 104225 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].simulators[name=iverilog].checks" name="A3 link checks, 8x8" --> and 8,225 on the 4x4 <!-- figure: 8225 src="results/rtl/a3_link_campaign.json#configurations[name=mesh4x4_vec16_hop1].simulators[name=verilator].checks" name="A3 link checks, 4x4" --> (`results/rtl/a3_link_campaign.json`).
  **What it measures, and why it was built.** A mesh all-reduce walks **exactly the mesh diameter** under recursive doubling — **14** traversals on the 8x8 mesh <!-- figure: 14 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].cases[label=synthetic_allreduce_sum_recursive_doubling].measured.traversals" name="measured all-reduce traversals, 8x8" --> against the **15.4** `src/opentallas/roofline.py` charges <!-- figure: 15.4 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].model_charged_traversals" name="model-charged traversals, 8x8" --> — and **exactly twice the diameter**, **12** on the 4x4 mesh <!-- figure: 12 src="results/rtl/a3_link_campaign.json#configurations[name=mesh4x4_vec16_hop1].cases[label=synthetic_allreduce_sum_halving_doubling].measured.traversals" name="measured halving/doubling traversals, 4x4" -->, under Rabenseifner halving/doubling. Those are two different algorithms and the model charges the **latency of the first and the bandwidth of the second** in the same event (`link_event_cost_s`: `depth = collective_traversals(...)` beside `payload = activation_bytes * 3 * (span-1)/span`). No single algorithm delivers both. Separately, a barrier's cycles are exactly linear in the declared hop occupancy: **6.000** cycles per hop-cycle <!-- figure: 6.000 src="results/rtl/a3_link_campaign.json#hop_latency_regression[label=synthetic_barrier].cycles_per_hop_cycle" name="measured cycles per hop cycle, barrier" --> on a diameter-6 mesh, zero residual, on top of a **43.0**-cycle per-collective fixed cost <!-- figure: 43.0 src="results/rtl/a3_link_campaign.json#hop_latency_regression[label=synthetic_barrier].fixed_cycles" name="measured per-collective fixed cycles" --> that the analytical model has no term for at all. Under a payload larger than the credit window the same all-reduce costs 18.5 cycles per hop-cycle, not 6, so `traversals x hop_latency` is the right form only while a collective fits inside its credit window.
  **What it refuses, and why that is the finding.** A binary32 SUM runs only under a reduction order the chosen algorithm can actually produce: recursive doubling folds the lowest participant bit first and is `PAIRWISE_TREE`; halving/doubling folds the highest first, which coincides with `BLOCKED_ASCENDING` only at sixteen participants. **No mesh algorithm that finishes in O(sqrt(P)) traversals produces `SEQUENTIAL_ASCENDING`** — and `compiler/backends/rom/common/program.py:5634` hard-codes `SEQUENTIAL_ASCENDING` for **every** arithmetic collective the ROM backend emits, including the on-wafer expert all-reduce the headline prices. The engine therefore traps (class 11) rather than returning different bits under the same name. The divergence is measured, not asserted: on the 8x8 vector set **54** of 64 reduced elements differ between the two orders <!-- figure: 54 src="results/rtl/a3_link_campaign.json#configurations[name=mesh8x8_vec64_hop1].sequential_vs_tree_differing_elements" name="elements differing between declared and achievable reduction order" -->.
  **Production admission boundary.** `record_valid` and `command_admitted` are deliberately separate. The certificate-bound DeepSeek HBM barrier at descriptor 2948 remains byte-exact, passes the complete COMMUNICATION structural/CRC decode, and retains its independently calculated CLUSTER_32 oracle of **160 messages and zero payload bytes**. It does **not** execute: its `ACQUIRE_RELEASE` ordering, permissions, route, object, completion-event and counter semantics are not implemented by this block, so it is refused with `COMM_REFUSE_CONTROL_METADATA` and contributes zero measured flits, crossings, traversals or cycles. All barrier timing is instead attributed to `synthetic_barrier`, a CRC32C-resealed probe with neutral ordering, permissions, route, object, event, counter and chunk fields. Thus `command_admitted` never means “dataplane-only despite ignored ABI semantics”; every unsupported integration semantic must be neutral before execution.
  **Physical, and it found something a cycle model cannot.** The endpoint is placed and routed in the installed IHP SG13G2 open foundry PDK with OpenROAD — **zero** detailed-route DRC violations <!-- figure: 0 src="results/rtl/a3_link_physical.json#implementation.detailed_route_drc_violations" name="A3 link endpoint route DRC violations" -->, **138,206** um2 of design area <!-- figure: 138,206 src="results/rtl/a3_link_physical.json#metrics.design_area_um2" name="A3 link endpoint routed design area" --> — and it **does not close timing** at a 10 ns period, missing by **-10.26** ns <!-- figure: -10.26 src="results/rtl/a3_link_physical.json#metrics.worst_setup_slack_ns" name="A3 link endpoint worst setup slack at 10 ns" -->; the archived failing path runs from `rx_w_flit[1]` through about forty XNOR/XOR stages, which is the single-cycle CRC32C over a 64-bit flit. At a 25 ns period the same block closes at **+0.24** ns <!-- figure: 0.24 src="results/rtl/a3_link_physical_25ns.json#metrics.worst_setup_slack_ns" name="A3 link endpoint worst setup slack at 25 ns" --> with zero total negative slack, so the integrity check — not the credit or replay logic — is what sets this endpoint's clock, and a parallel or pipelined CRC is the named next step. The whole mesh node synthesises at **1,034,069** um2 of cell area <!-- figure: 1,034,069 src="results/rtl/a3_link_node_synthesis.json#design.yosys_statistics.cell_area_um2" name="A3 link node synthesised cell area" --> (`results/rtl/a3_link_node_synthesis.json`, synthesis only, a flip-flop receive bank sized for clarity and not an area claim) and the router alone at **19,915** um2 <!-- figure: 19,915 src="results/rtl/a3_link_router_synthesis.json#design.yosys_statistics.cell_area_um2" name="A3 mesh router synthesised cell area" -->. IHP SG13G2 is a 130 nm open foundry PDK: no area or delay here may be scaled to N6/N5/N7/N4 (`docs/METHODOLOGY.md` section 9).
  **Still open, named rather than implied:** this endpoint does **not** measure wire delay, so `links.on_wafer`'s 125 ns stays derived from published geometry and the audit's open measurement #1 is only half answered — the traversal count now has an implementation, the nanoseconds do not. The complete COMMUNICATION and referenced NUMERIC records are decoded, but the collective algorithm remains an explicit sideband and no shipped deployment sequencer, event, counter or object-descriptor integration is present. There are no virtual channels, no wormhole flow control and no adaptive routing, so nothing here speaks to congestion. `CONCAT`, `REDUCE_SCATTER` as a standalone op, `LINK.SEND`/`RECEIVE`/`REMOTE_DMA` and multi-node scope resolution have no RTL. The engine is not wired to the W8.6 microsequencer, and `runtime/cycle/fabric.py` still runs a ring (`2(P-1)` rounds) where `roofline.py` charges `1.1 x` diameter — two algorithms for one machine, and nothing reconciles them
- [~] W8.5 ROM service RTL (Qwen chip, DeepSeek wafer tile) — **the read path is implemented and correlated on two simulators, and it contains no ROM array.** `rtl/rom/ot_rom_read_service.sv` turns `(object_id, byte_offset, byte_length)` into a physical access against the compiled region plan the deployment publishes as `notes.rom_plan`: object lookup, shard walk to a placement resource and an address inside it, row-redundancy translation, region masking, fail-closed quarantine and column-repair refusal, row-activation accounting against a persistent row buffer, and the column mux onto the operand bus. Three vector sets, all read back out of real ROM deployments — never hand written — and replayed under Icarus and Verilator through independently written checkers (`results/rtl/rom_service_campaign.json`):
  - `qwen_chip`: the **executed** ROM read stream of the Qwen ROM deployment on `runtime.sim.device.Device`, both accounting sites instrumented and reconciled against the device's own `rom.bytes_read`; **351** requests, **2,499,996** sense beats, **159,997,856** bytes and **39,213** row activations replayed beat by beat <!-- figure: 351 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.requests.count" name="Qwen ROM service requests" --> <!-- figure: 2,499,996 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.beats" name="Qwen ROM service beats" --> <!-- figure: 159,997,856 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.bytes" name="Qwen ROM service bytes" --> <!-- figure: 39,213 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.activations" name="Qwen ROM service activations" -->
  - `qwen_chip_degraded`: the same deployment recompiled against a BIST defect list, so the repair map comes from the real planner, plus a masked region and a quarantined bank as runtime health inputs — **365** requests and **170** refusals <!-- figure: 365 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.requests.count" name="Qwen degraded ROM service requests" --> <!-- figure: 170 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.totals.faults" name="Qwen degraded ROM service refusals" -->
  - `deepseek_wafer`: **10,835** requests over **9,527** shards on **9,300** placement resources, every shard boundary the plan declares crossed by one request, and **9,172** of the 9,300 resources entered by a served read -- the 128 that are not are the 127 owned only by the deliberately masked expert bank plus the one deliberately quarantined <!-- figure: 9,172 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.totals.placement_resources_entered" name="DeepSeek wafer resources entered" -->; **88** of its 228 regions are distributed over more than one resource and the largest spans **1,281** <!-- figure: 10,835 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.requests.count" name="DeepSeek wafer ROM service requests" --> <!-- figure: 9,527 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.shard_count" name="DeepSeek wafer ROM shards" --> <!-- figure: 9,300 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.resource_count" name="DeepSeek wafer ROM resources" --> <!-- figure: 88 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.distributed_region_count" name="DeepSeek wafer distributed regions" --> <!-- figure: 1,281 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.max_shards_in_one_region" name="DeepSeek wafer largest region shard count" -->. **This set is derived from the compiled plan, not executed.** The retained token lane completed four prior-build steps (W6.4), but no request stream from that run is retained in this campaign; plan coverage must not be relabelled as executed traffic.
  - **Why it stays `[~]`:** there is no ROM array in the RTL under test. The array sits behind a sense request/response interface and is supplied by the testbench, so this is a control and addressing claim — it establishes nothing about ROM cell area, read energy, sense margin, wordline or bitline delay, retention or defect rate, and the sense-granule width is a declared parameter of the block rather than a macro property. Column redundancy is refused rather than implemented; the view-to-byte-range walk and descriptor admission are out of scope; a whole decode step reads about fifteen gigabytes and is not replayed beat by beat. `docs/ROM_SERVICE_RTL.md` states the boundary
  - **What it found.** Both products declare ROM-class memory objects that the region plan does not place — generated rotary, `arange`, ring-index and constant tables — carrying `bank_or_tile` 0xFFFF and `base_address` 0 while their traffic is still counted by `rom.bytes_read`. **111** of the **265** replayed executed Qwen reads are to two such objects <!-- figure: 111 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.refusals_by_origin.executed" name="Qwen unplaced-object refusals from the executed stream" --> <!-- figure: 265 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.requests.by_origin.executed" name="Qwen executed reads replayed" --> and the wafer plan leaves six of them unplaced. The service refuses them rather than inventing a bank. That is a finding about `compiler/backends/rom`, which this item does not own
  - **Evidence freshness:** the campaign reports retained `status: pass` <!-- figure: "pass" src="results/rtl/rom_service_campaign.json#status" name="ROM service campaign status" --> and every recorded source/input hash has been rechecked after the P10.7 rebuild. Both Qwen streams were re-executed from the admitted ROM deployment (`274e4b…`) <!-- figure: "274e4b…" src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.deployment.deployment_sha256" name="Qwen nominal ROM-service deployment" --> and verified degraded rebuild (`ee47f8…`) <!-- figure: "ee47f8…" src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.deployment.deployment_sha256" name="Qwen degraded ROM-service deployment" --> against the authenticated Qwen snapshot. Each records and rechecks a complete admission/decode/numeric/all-engine source map, the exact capability and workload file hashes, a **399**-range checkpoint-map identity verified by `DeviceMemory` <!-- figure: 399 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.executed_source.checkpoint_binding.authenticated_range_count" name="Qwen ROM authenticated checkpoint ranges" -->, and successful admission; both report **0** unexpressible reads <!-- figure: 0 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.executed_source.events_not_expressible_as_contiguous_ranges" name="Qwen unexpressible ROM reads" --> <!-- figure: 0 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.executed_source.events_not_expressible_as_contiguous_ranges" name="Qwen degraded unexpressible ROM reads" -->. The retained campaign directly pins every source and loaded input it consumes, and `python3 tools/rtl_rom_service_campaign.py --verify` re-hashes them; `executed_stream_source_drift`, `executed_stream_source_missing`, and `executed_stream_integrity_problems` are empty at that identity. The DeepSeek set uses deployment `fa9077…` <!-- figure: "fa9077…" src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.deployment.deployment_sha256" name="DeepSeek ROM-service deployment" --> but remains deliberately plan-derived with a **0**-byte checkpoint window <!-- figure: 0 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.window.real_bytes" name="DeepSeek authenticated checkpoint bytes in plan-derived ROM-service set" -->: this campaign did not activate the DeepSeek checkpoint, so it does not call those bytes authenticated. The ignored deployment bundles are not retained dependencies; each vector's content-addressed ABI deployment digest is the durable boundary, not a claim that any arbitrary `build/` path still contains it.
  - **Physical proxy:** the current source-locked IHP SG13G2 run now closes its narrowly bounded open-PDK implementation: it writes a routed DEF with **0 tool-reported detailed-route DRC violations** <!-- figure: 0 src="results/rtl/rom_service_physical.json#implementation.detailed_route_drc_violations" name="ROM service physical DRC violations" -->, **+7.52 ns** worst setup slack <!-- figure: 7.52 src="results/rtl/rom_service_physical.json#metrics.worst_setup_slack_ns" name="ROM service physical setup slack" -->, **+0.01 ns** worst hold slack <!-- figure: 0.01 src="results/rtl/rom_service_physical.json#metrics.worst_hold_slack_ns" name="ROM service physical hold slack" -->, and zero TNS at the chosen 20 ns constraint. `results/rtl/rom_service_physical.json` records `status: pass` <!-- figure: "pass" src="results/rtl/rom_service_physical.json#status" name="ROM service physical status, checklist" --> for that implementation. This is not foundry signoff: timing is not SPEF-extracted, the DRC count is the detailed router's rather than a signoff deck's, and there is no LVS or GDS. The block contains no ROM array, and none of its 130 nm area or timing enters the leading-node studies.
- [x] W8.6 Verilator co-simulation vs functional simulator on generated programs — 65 cases, 185 issue events, 460 resolved tensor views (amendments A4, A13, A18 and A26), 11 traps matched on two simulators, 4,555 checks each <!-- figure: 65 src="results/rtl/abi3_campaign.json#correlation.case_count" name="RTL correlation cases" --> <!-- figure: 185 src="results/rtl/abi3_campaign.json#correlation.issue_event_count" name="RTL issue events" --> <!-- figure: 460 src="results/rtl/abi3_campaign.json#correlation.view_resolution_count" name="RTL resolved views" --> <!-- figure: 11 src="results/rtl/abi3_campaign.json#correlation.trap_count" name="RTL traps" --> <!-- figure: 4,555 src="results/rtl/abi3_campaign.json#cases[name=iverilog].checks" name="RTL checks per simulator" --> **These are programs built for the campaign, not programs this repository ships.** The shipped deployment images are covered by W8.8, which is where the boundary between "the RTL runs our test programs" and "the RTL runs the product" is actually drawn
- [x] W8.7 Fault/stall/backpressure/reset campaigns — 17 negative cases incl. CRC, illegal opcode, loop overrun, mid-transaction trap <!-- figure: 17 src="results/rtl/abi3_campaign.json#correlation.negative_case_count" name="RTL negative cases" -->
- [x] W8.8 Co-simulation against the **four shipped deployment images**, not
  programs built for the campaign — `tools/rtl_abi3_deployment_campaign.py`
  resolves every real image through its current passing ROM-schedule or
  HBM-deployment certificate, re-hashes the governed sources, Kernel IR,
  capability and bundle, and compares both prefill and decode with
  `runtime.sim.device.Device`. The refreshed artifact is `pass`, has no
  divergence, and records **594,004** checks per simulator <!-- figure: 594004 src="results/rtl/abi3_deployment_campaign.json#cases[name=iverilog].checks" name="shipped-profile RTL checks per simulator, W8.8" -->,
  **28,850** engine issues, **83,537** resolved views and **3,000**
  data-dependent predicate reads, as recorded in the artifact's required PASS
  marker. All eight cases now run to completion: under the AM-E9 v2
  re-lowering (`e6da961`) the two DeepSeek HBM cluster cases no longer trap
  class 13 at instruction 1,279, so `completions` in the marker is 8 where the
  previous record read 6. The campaign is driven through the design top
  `rtl/abi3/ot_a3_device_top.sv`, which both verification tops now wrap.
  The current images are Qwen ROM (`133afc1…`, 74 instructions/215
  descriptors), Qwen HBM (`cb9067f…`, 74/221), DeepSeek ROM wafer
  (`233494d…`, 1,323/3,134), and DeepSeek HBM cluster (`d832861…`,
  1,286/3,305). Every image contains zero `STATE` descriptors/instructions and
  the required `PROFILE: ABI3 live-buffer state exclusion PASS` marker is
  present.
  - DeepSeek ROM reaches **20,004** retired instructions in prefill <!-- figure: 20004 src="results/rtl/abi3_deployment_campaign.json#what_ran.depth_reached[case=deepseek-v4-flash-rom-wafer/prefill].golden_instructions_retired" name="DeepSeek wafer prefill instructions correlated, W8.8" --> and
    **12,934** in decode <!-- figure: 12934 src="results/rtl/abi3_deployment_campaign.json#what_ran.depth_reached[case=deepseek-v4-flash-rom-wafer/decode].golden_instructions_retired" name="DeepSeek wafer decode instructions correlated, W8.8" -->.
    DeepSeek HBM reaches **20,062** in prefill <!-- figure: 20062 src="results/rtl/abi3_deployment_campaign.json#what_ran.depth_reached[case=deepseek-v4-flash-hbm-cluster/prefill].golden_instructions_retired" name="DeepSeek HBM prefill instructions correlated, W8.8" --> and
    **12,392** in decode <!-- figure: 12392 src="results/rtl/abi3_deployment_campaign.json#what_ran.depth_reached[case=deepseek-v4-flash-hbm-cluster/decode].golden_instructions_retired" name="DeepSeek HBM decode instructions correlated, W8.8" -->, both
    to completion.
    No case lowers its work bound. One verification-top instance represents one
    sequencer node; cluster topology remains independently certified at exactly
    32 nodes.
  - **Claim boundary:** this closes control flow, predicates, issue records,
    resolved live-buffer views, terminal-fence completion and traps for those
    images at a **16**-token request shape <!-- figure: 16 src="results/rtl/abi3_deployment_campaign.json#what_ran.prompt_tokens" name="deployment co-simulation prompt length" -->.
    Engine arithmetic is a recording no-op on both sides; mutable memory bytes,
    datapath integration, descriptor CRC32C and header SHA-256 are not checked
    in RTL, and this establishes no area, timing, power or target-node quantity.
- [x] W8.9 Express every sequencer bound where a deployment can be refused for
  exceeding it — the event scoreboard is **2,048** entries <!-- figure: 2048 src="results/rtl/abi3_deployment_campaign.json#rtl_implementation_bounds.values.A3_EVENT_COUNT" name="RTL event-ID storage bound, W8.9" --> (AM-C1, widened from 1,024 with the asynchronous front end; the four capability records still publish `max_event_id` 1,023 because they are certificate inputs of the bound deployments) and all active
  bounds admit the four shipped images with no overrun. The retained **16** state-slot parameter <!-- figure: 16 src="results/rtl/abi3_deployment_campaign.json#rtl_implementation_bounds.values.A3_STATE_SLOTS" name="compatibility-only RTL state-slot bound, W8.9" --> applies only to
  `STATE_COMPAT=1` compatibility tests. Production elaborates no state
  controller and imposes the stricter zero-state rule before fetch.

## W9 — Physical (SKY130 implementation view, ASAP7 predictive view)

> **Claim boundary for every physical number in this section, and in any
> document that cites one.** `results/rtl/abi3_deployment_campaign.json` is
> currently `pass` for both entrypoints of all four shipped deployment images:
> Qwen ROM single-chip, Qwen HBM single-chip, DeepSeek-V4-Flash ROM wafer, and
> DeepSeek-V4-Flash HBM 32-node cluster.
> A physical number may describe only a design within the artifact's current
> `correlated_cases`; readers must use the artifact rather than a copied verdict.
>
> That correlation establishes control-flow, engine-issue, predicate,
> live-buffer-view, and terminal-fence/completion agreement with
> `runtime.sim.device.Device`. It does **not**
> establish engine arithmetic, sequencer-to-datapath integration, checkpoint
> bytes, longer request shapes, area, timing, or power. No physical result may
> silently inherit any of those claims from W8.8.
>
> No ABI 3.0 control-plane block has been synthesized or routed. The routed
> blocks below are ABI 2.5 engines, W8.3 datapaths and numeric probes, the ROM
> read service, and the W8.4 link endpoint; [OI-43] records the open sequencer
> synthesis issue. Finally, no frequency, area, energy, or density measured in
> IHP SG13G2 (130 nm), SKY130, or predictive ASAP7 may be scaled to
> N6/N5/N7/N4 (`docs/METHODOLOGY.md` §9).

- [x] W9.1 Inventory available PDKs/tools; record what can actually run offline — `docs/ABI3_PHYSICAL_VIEWS.md`
- [x] W9.2 SKY130 synthesis + place/route of RTL 3.0 blocks; area/timing/power — SKY130 HD full place-and-route, 0 DRC, 0 antenna
- [x] W9.3 ASAP7 synthesis (predictive) of the same blocks — ASAP7 full place-and-route; archived case reproduced bit-for-bit
- [~] W9.4 SRAM/ROM macro methodology per view — the IHP SG13G2 chain now has three passing, source-bound open-PDK artifacts: minimum-pitch ROM/SRAM bitcell geometry (`results/spice/ihp_sg13g2_bitcell/bitcell.json`), routed ROM arrays plus synthesized periphery (`results/spice/ihp_sg13g2_rom_macro/macro_route.json`), and extracted read-energy/PVT sweeps (`results/spice/ihp_sg13g2_rom_read_energy/read_energy.json`), documented in `docs/ROM_PHYSICAL_METHODOLOGY.md`. `docs/ROM_DENSITY_NODE_TRANSFER.md` adds a separate ASAP7 predictive comparison and demonstrates that the 130 nm ratio does not transfer. It remains `[~]` because none of these artifacts characterizes the N6/N5 views named by this authoritative row; every artifact explicitly prohibits target-node scaling. The master plan's Phase-G exit instead names SKY130 and ASAP7, a scope discrepancy that requires an explicit checklist amendment if the intended closure view changes.
- [~] W9.5 Feed characterized capability back into cycle model; recompile; rerun — `f16ffb2` made the ROM/SRAM cell ratio node-addressed, refuses unnamed nodes or bands that exclude either committed bitcell measurement, and reran both N6/A100 and N5/B200 studies at the declared band ends and at every measured ratio (`rom_cell_ratio_sensitivity` in each `analytical.json`). Later generated v2 cost tables and `results/abi3/cycle_characterization_feedback.json` propagate characterized tensor/vector/reduction feedback through one deployment-bound Qwen HBM decode transaction while preserving every compared architectural counter. That is still sensitivity propagation, not target-node characterization or the required four-target recompile/rerun: it omits workload/comparison-boundary identity, admissible same-view memory macros, both fabrics, several engine families and the other three deployments. The IHP 130 nm and predictive ASAP7 measurements are not substituted into N6/N5, and the unresolved question of whether read-bandwidth density scales with cell area still moves the ROM hard floor by 3×. W9.5 remains partial until W8.3/W8.4/W8.5/W9.4 supply complete same-view inputs, after which all four targets must be recompiled and rerun on governed comparison boundaries. A coupling rule may close the ROM-cell sensitivity question; it cannot replace missing same-view characterization.

## W10 — Mandatory workload campaigns

**W10.1 execution note:** one later source-locked Qwen HBM/SRAM natural capture
completed the exact-8K workload and produced `[18, 24, 16, 151645]`, raw text
`391<|im_end|>`, visible text `391`, and official EOS with no post-EOS
transaction. Its execution-authoritative hashes match Git tree
`008bf765e212c061f930d5a2726563f7ddeba740`; current runtime sources have since
changed, so it is a successful frozen-source diagnostic rather than final W10
acceptance. Its 5,659.73 s host wall time and 2,104 retired-instruction ticks
per later token are not architectural TPOT. A fresh HBM-A, independent HBM-B,
and ROM capture must all run from one final frozen release and pass the strict
three-record checker.

- [~] W10.1 Qwen exactly 8,000 natural prompt tokens → first official EOS or the frozen 256-token cap (HBM) — **one frozen-source HBM/SRAM execution is exact through EOS; current-release three-capture acceptance remains open**. The canonical diagnostic at `results/abi3/w10/qwen3_8b_hbm_natural_a.json` matches all four external-oracle IDs and independently decoded text, but later ABI 3.0 runtime changes make it non-current. The older retained HBM record decoded 193 tokens in 14,982 s (`results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json`): its first **137 tokens match the reference oracle**, then one argmax flips and the historical 8,192-row build reaches its capacity boundary at decode step 193 ([OI-33], [OI-34]). <!-- figure: 8,000 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.workload.prompt_token_count" name="TA-QW-8K-1 prompt tokens" --> <!-- figure: 193 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.generated_token_count" name="TA-QW-8K-1 decoded tokens" --> <!-- figure: 137 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.notes.first_divergence_index" name="TA-QW-8K-1 first divergence" --> The historical ROM lane completed the matched 192-token horizon and all **192** tokens match the oracle <!-- figure: 192 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.generated_token_count" name="Qwen ROM completed 8K comparison horizon" -->; that is prior-build evidence only. The current source adapter, neutral IR, 36 layer KV buffers, RoPE table and every published workload now share an exact **8,256-position** session contract; workload generation rejects 8,000+257 and stale retained metadata. The ROM capability is exactly 8,256, the HBM profile's 262,144 endpoint admits it, both temporary product deployments lower deterministically, and the final 512-row block has verifier-safe padded backing. `run_accelerator_tokens.py` accepts `exact_eos_or_cap` only when accelerator and oracle share the complete first-EOS sequence with no post-EOS execution, or both produce exactly 256 identical cap tokens. `check_qwen3_w10_acceptance.py natural` independently reopens and authenticates two serialized HBM deployments plus one ROM deployment and requires identical complete tokens, per-step results, architectural counters, tokenizer-decoded text, and nonempty executed-association manifests. W10.1 remains partial until all three clean current-release captures pass this gate.
- [~] W10.2 Qwen repeated-special-token stress run — **historically executed and divergent; same-association preflight is now implemented, but the source-current 32-token pair remains open**. The retained HBM record ran 8,000 copies of token id 151644 followed by 32 decoded tokens in 11,942 s and diverged at index 2 (`results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json`). <!-- figure: 32 src="results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json#record.generated_token_count" name="TA-QW-STRESS-1 decoded tokens" --> <!-- figure: 2 src="results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json#record.notes.first_divergence_index" name="TA-QW-STRESS-1 first divergence" --> <!-- figure: "diverged" src="results/abi3/qwen3_hbm_ta-qw-stress-1_execution.json#status" name="TA-QW-STRESS-1 status" --> That structured divergence does not waive A7's external-oracle gate. The runtime now records each blocked numeric contract with implementation identity, activation/weight/output shapes and call counts under a canonical digest. Qwen HBM and ROM both use 512-row token blocks; ROM's static buffers and generated ranges cover the 8,704-row padded final-block extent while the logical session remains 8,256. Fresh temporary one-token HBM/ROM diagnostics produced the same token and byte-identical manifests (five shapes, 253 calls), proving the short executed association is harmonized without claiming the long stress result. `check_qwen3_w10_acceptance.py stress` independently reopens and authenticates the source-current HBM and ROM deployments, requires zero `STATE` resources, verifies ordinary read/write live buffers and per-step status/counters/input/source evidence, and requires nonempty identical manifests plus exactly 32 oracle-identical and mutually identical tokens at `max_new_tokens`. Producing that full pair is still pending. See [OI-33].
- [x] W10.3 Qwen chat workload (pinned template) — `TA-QW-CHAT-1`, 93 prompt tokens, 24 decoded tokens, token-identical to the oracle; <!-- figure: 93 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.workload.prompt_token_count" name="TA-QW-CHAT-1 prompt tokens" --> <!-- figure: 24 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.generated_token_count" name="TA-QW-CHAT-1 decoded tokens, W10.3" --> the model is mid-derivation at the token cap (`We are given:\n\n- **Ship 1** (from Port A) leaves at **06:00**`), so this record proves token fidelity, not answer correctness; W10.1 owns the still-open exact EOS-or-256 natural-context requirement
- [x] W10.4 Qwen agentic workload — `TA-QW-AGENT-1` decoded a **complete, well-formed tool call and stopped at a real EOS** entirely on the accelerator: ```bash / awk -F',' '{sum += $2} END {print sum}' inventory.txt / ```. Token-identical to the oracle. Feeding the result back through the sandbox loop is `tools/run_qwen3_agent_episode.py`
- [x] W10.5 DeepSeek long-context campaign — **all five declared rungs have executed** — 1,000 / 8,000 / 32,000 / 128,000 / 200,000 tokens — so the largest context actually executed is **200,000** tokens (`results/abi3/deepseek_v4_reference_oracle_context_ladder.json`). <!-- figure: 200,000 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.largest_context_executed" name="largest DeepSeek context executed" --> The three upper rungs needed exactly the chunked prefill the projection called for and record `prefill_tiled` true; at 200,000 tokens peak device memory is **9.27** GB, the measured KV read is **317,435,904** B per decode step, and that is **0.9999** of the corrected profile's prediction. <!-- figure: 9.27 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.rungs[workload=TA-DS-CTX-200K-1].peak_device_bytes" scale="1e-9" name="200K rung peak device GB" --> <!-- figure: 317,435,904 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.rungs[workload=TA-DS-CTX-200K-1].measured_kv_bytes_per_decode_step" name="200K rung measured KV bytes per step" --> <!-- figure: 0.9999 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.rungs[workload=TA-DS-CTX-200K-1].measured_over_predicted" name="200K rung measured over predicted" --> The projection that motivated the rewrite stands as recorded and is why it was needed: unchunked, `hc_post` alone is **48.8** GiB at that context and the indexer term **2.33** TiB, while persistent KV state is only **2.32** GiB (`results/abi3/deepseek_v4_long_context_projection.json`). <!-- figure: 48.8 src="results/abi3/deepseek_v4_long_context_projection.json#derived.memory.hc_post_mix_intermediate_bytes" scale="0.000000000931322574615478515625" name="hc_post intermediate, GiB" --> <!-- figure: 2.33 src="results/abi3/deepseek_v4_long_context_projection.json#derived.memory.indexer_score_unchunked_bytes" scale="0.0000000000009094947017729282379150390625" name="unchunked indexer score, TiB" --> <!-- figure: 2.32 src="results/abi3/deepseek_v4_long_context_projection.json#derived.memory.persistent_kv_and_rope_bytes_measured" scale="0.000000000931322574615478515625" name="persistent KV and rope, GiB" --> *(This is the reference-oracle GPU lane, not the accelerator.)*
- [x] W10.6 DeepSeek agentic scenario — 47 tokens to EOS, well-formed DSML tool call, byte-identical across independent process invocations

The Qwen 8K, stress, 24-token chat, EOS-agentic, reasoning, and closed-loop
records in W10/W13 are retained historical executions. The hardened Qwen chat
captures re-established four oracle-identical tokens on both deployments at
their bound prior head; this W10 tranche does not silently carry that freshness
forward or extend it to the longer workload horizons.

## W13 — The end-to-end requirement, stated plainly

The stated requirement is that **every** design runs the real model end to end
and produces validated real tokens, on reasoning *and* agentic tasks. Against
that, the position is:

- [x] W13.1 Qwen3-8B **HBM** lane — 24 tokens, oracle-identical <!-- figure: 24 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.generated_token_count" name="Qwen HBM generated tokens, TA-QW-CHAT-1" -->
- [x] W13.2 Qwen3-8B **ROM** lane — 24 tokens, oracle-identical, and identical to <!-- figure: 24 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.generated_token_count" name="Qwen ROM generated tokens, TA-QW-CHAT-1" -->
  the HBM lane position for position
- [~] W13.3 DeepSeek-V4-Flash **HBM** (32 node) — **frozen-source short-token
  diagnostic.** One P32 prefill plus three decode steps through the compiled
  ABI 3.0 deployment produced `[13806, 345, 7472, 55560]`, matching all **4** oracle positions <!-- figure: 4 src="results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json#oracle.compared_tokens" name="DeepSeek HBM source-current oracle-compared tokens, W13.3" --> with no legality problem. The refreshed
  `results/abi3/deepseek_v4_context_gate.json` revalidates the selected HBM
  source set and reconciles every measured node plus cluster total. This closes
  that source snapshot's short HBM diagnostic after the sparse-layout and
  ordered-product repairs; later device-cap and release-lock changes mean it is
  no longer source-current acceptance;
  it does **not** close the exact-200K, EOS-or-256, reasoning/agentic, RTL-token,
  or characterized-TPOT requirements.
- [~] W13.4 Remaining multi-design reasoning/agentic coverage — **frozen-source
  short-token evidence exists for DeepSeek HBM, the 32-node ROM-array, and the
  required single-wafer topology, but no exact-200K or every-design workload
  matrix is closed.** The latest single-wafer DeepSeek ROM
  capture produced **4** tokens identical to the retained HBM/oracle prefix <!-- figure: 4 src="results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json#oracle.compared_tokens" name="DeepSeek ROM prior-build oracle-compared tokens, W13.4" -->,
  decoded as ` pump C alone empt`; its final ABI completion correctly reports
  device-side `MAX_NEW_TOKENS`. It nevertheless predates current
  execution-authoritative sources and decoded-text capture and is full
  functional execution only for P32/four outputs, not Gate-1 acceptance, a
  source-current cross-target result, or TPOT evidence.
  Neither DeepSeek backend has an accelerator reasoning or agentic capture: no
  DeepSeek reasoning workload is pinned, and the existing agentic result is
  external-oracle GPU evidence. In addition, W13.5 and W13.6 exercise Qwen HBM
  only; Qwen ROM has no reasoning or closed-loop agentic capture. This row owns
  all six missing cells so the explicit “every design” exit is not weakened:
  Qwen ROM reasoning/agentic plus DeepSeek HBM and ROM reasoning/agentic.
- [x] W13.5 Qwen **HBM reasoning** generation with thinking enabled — **closed.**
  `TA-QW-REASON-1` is the chat question rendered with thinking enabled, and the
  accelerator decoded **512** tokens of the model's own `<think>` block on the HBM <!-- figure: 512 src="results/abi3/qwen3_hbm_ta-qw-reason-1_execution.json#record.generated_token_count" name="TA-QW-REASON-1 tokens" -->
  lane: status `pass`, `reference_agreement` true, no divergence index <!-- figure: "pass" src="results/abi3/qwen3_hbm_ta-qw-reason-1_execution.json#status" name="TA-QW-REASON-1 status" -->
  (`results/abi3/qwen3_hbm_ta-qw-reason-1_execution.json`).
  The external oracle ran the same workload to **3,072** tokens and the <!-- figure: 3,072 src="results/abi3/qwen3_reference_oracle_reasoning.json#results.TA-QW-REASON-1.generated_token_count" name="reasoning oracle tokens" -->
  accelerator matches it token for token over the 512 it decoded, then stopped at
  its decode budget rather than at EOS. So what closes is *reasoning generation
  with thinking enabled*, evidenced; a reasoning run carried to its own EOS is
  not, and neither lane has one
- [x] W13.6 Qwen **HBM closed-loop agentic episode** — **closed.** `TA-QW-AGENT-2`
  closed the loop entirely on the accelerator: **2** turns, **1** command actually <!-- figure: 2 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#turn_count" name="agent episode turns" --> <!-- figure: 1 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#executed_command_count" name="agent episode commands executed" -->
  executed in the sandbox (`awk -F, '{sum += $2} END {print sum}' inventory.txt`,
  exit 0, stdout `239`), the observation fed back, and the second turn answered
  **239**, which equals the task's `expected_total`; `task_solved` true <!-- figure: 239 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#expected_total" name="agent episode expected total" --> <!-- figure: "239" src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#answer" name="agent episode answer" -->
  (`results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json`).
  Every command executed was produced by the accelerator and parsed fail-closed;
  the harness never writes or repairs one. **The record's own status is
  `diverged`, not `pass`**, and the reason is the token horizon of [OI-33] rather <!-- figure: "diverged" src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#status" name="agent episode status" -->
  than the loop: turn 0 leaves the oracle episode at generated index **286** and <!-- figure: 286 src="results/abi3/qwen3_hbm_ta-qw-agent-2_episode.json#turns[0].oracle_comparison.first_generated_divergence_index" name="agent episode first divergence" -->
  turn 1 at index 23, with both prompts matching exactly and both episodes
  reaching the same command and the same answer. The closed loop is what closes;
  the oracle-identity claim at this length does not, and W11.1 states that horizon

W13.4 is the remaining partial workload-coverage lane. At a retained prior
source identity, **all four designs ran the model end to end with a four-token
oracle-identical capture**. Those captures are now prior-build evidence.
Retained historical evidence extends both Qwen lanes
to 24 tokens, and the historical Qwen ROM lane to **192** <!-- figure: 192 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.generated_token_count" name="Qwen ROM 8K tokens" --> oracle-identical tokens
at the 8,000-token context; those longer horizons are not current-source reruns.
The retained DeepSeek ROM/HBM pairwise artifact records the exact historical
four-token agreement but is not promotable after the learned-index repair.
W13.4 remains partial because the six workload cells it owns have not run and
the DeepSeek short pair has not been refreshed.

## Findings of 2026-08-30 — three defects that passed every check

Three defects landed tonight that share one shape: **the verification was
self-consistent with the defect**, so nothing failed. They are recorded together
because the pattern matters more than any of them.

- **Both backends placed only the first segment of a segmented binding.** The
  256-expert stacked weights are bound as 256 authenticated ranges; both
  backends read `binding.path/offset/bytes` and ignored `binding.segments`, so
  each stack was placed as **one 1 GiB range from expert zero's offset** — 255
  of every 256 experts named by an address holding another expert's bytes. The
  byte totals reconciled and the digests were computed over what *was* placed
  rather than over what *should* have been, so every check passed. Fixed: 2,424
  → **68,214** authenticated ranges, the ROM deployment's 228 regions and
  156,015,698,140 payload bytes unmoved, and exactly **24 region content digests
  changed** — the 12 expert banks and their 12 scales.

- **The HBM lowering read a generation-policy key the IR does not emit.** It
  asked for `max_new_tokens` where the IR emits `maximum_new_tokens`, so the
  lookup always missed and every HBM deployment silently carried the 512
  default while the ROM backend read 8,192 from the same IR. **Two backends
  carrying different generation policies for one IR is the divergence a shared
  IR exists to prevent**, and it is invisible until a generation runs long
  enough to hit the smaller cap, where it looks like the model stopping early.
  Five synthetic test graphs declared the same wrong key, so they passed by
  agreeing with the defect rather than with the IR — the same shape as the block
  loop tests that asserted `step == bound_divisor` and pinned [OI-22] in place.
  Neither backend defaults now: a graph that appends tokens without declaring a
  budget is a graph whose decode length nobody chose.

- **The cycle model reported zero bytes for every storage class.** `8dfddac`
  gave the functional device a node dimension, and `_issue_nodes` rebinds
  `ctx.views` to the uninstrumented node-0 resolver before every engine issue —
  overwriting the recording resolver `TracingDevice` had installed. It stayed
  quiet because the *architectural* counters come from a different path
  (`EngineContext._account_read/_account_write`) and remained correct
  throughout, so the counter-agreement test stayed green while the memory report
  read zero. The same commit also made `run_node` time all 32 nodes and call it
  one: 17,986 per-node compute cycles against 564 for the identical program on
  one chip, then multiplied by 32 again in the aggregate. **A 32× timing error
  and a zeroed memory report, in the one component that models time at all.**

The common lesson is in the third: a check that passes because two paths agree
proves only that they agree. The memory report and the architectural counters
were never reconciled against each other, and the test that does that now is the
test that would have caught it on the day.

## OI-39 — the sparse KV model was 3x low, in the term the whole argument rests on

**Found by measuring, and it cost us our headline number.** The DeepSeek-V4-Flash
profile under-predicted KV read traffic by **2.72x at 32,000 tokens and 3.13x at
128,000**, with the error growing with context. It went unnoticed because
nothing had ever executed this model far enough to compare — the reference
oracle's context ladder declared five rungs and had run two.

The profile's **structure was correct and is unchanged**. The engine's per-layer
pair counts match it exactly at both contexts: `csa` reads `top_k + window` main
entries and scans `context/4` index entries, `hca` reads `context/128 + window`,
`window` reads 128. Two per-entry constants were wrong:

| | was | measured | factor |
|---|---:|---:|---:|
| `entry_bytes` (all groups) | 583 | **1,024** | 1.756 |
| `index_entry_bytes` (csa) | 68 | **256** | 3.765 |

Corrected, the profile predicts 64,800,000 B/step where the engine read
64,774,144 (**0.9996**) and 209,184,000 where it read 209,158,144 (**0.9999**).

**The root cause is a precision disagreement, not a transcription slip.** 583 is
an FP8 assumption — 576 elements (512 latent + 64 rope) at one byte plus scale
bytes — and the released implementation reads the 512-wide latent at BF16, which
is 1,024. A deployment that genuinely stored an FP8 latent *would* read 512
bytes; that is a design choice, it must then apply to both sides of a
comparison, and it is recorded in the profile rather than assumed.

**What it cost.** The weight-to-KV read ratio is the figure of merit for the
entire ROM case, and it was overstated:

| model | context | was | now | overstated |
|---|---:|---:|---:|---:|
| Flash | 8,192 | 853.2:1 | 387.3:1 | 2.20x |
| Flash | 200,000 | **113.2:1** | **35.3:1** | **3.20x** |
| Pro | 1,000,000 | 58.9:1 | 18.0:1 | 3.27x |

Every DeepSeek roofline number is stale in a known direction: KV is three times
heavier, so it binds earlier, the weight-bound regime in which a sparse model
batches for free ends at a lower batch, and the long-context advantage shrinks.
Qwen is unaffected — its KV term was already exact against executed hardware.

Pro carried the identical constants from the identical derivation and has been
corrected by analogy, graded `assumed_by_analogy` in the profile because no Pro
rung has ever been executed. **That grade is load-bearing on one of the three
headline claims and only a Pro execution retires it.**

`tools/validate_kv_model_against_oracle.py` makes this checkable. It reports
positions, bytes-per-position and the total *separately*, because a structural
error and an entry-size error look identical in the total and have completely
different fixes — that separation is what turned "the model is 3x off" into
"these two constants are wrong and the structure is right." Two regression
tests: both rungs within 1%, and the historical 583/68 pair rejected including
its growth with context, which a pure scale error would not show.

- **OI-40 — the IR binds 6.5% fewer weight bytes than the profile claims.** The
  neutral IR binds 156,015,698,140 bytes across its weight tensors where
  `checkpoint_bytes` declares 166,878,536,440, a 10.86 GB gap. This is
  *conservative* — it would size ROM larger than the executed graph needs — so
  it is not a flattering error, but it is unexplained, and after OI-39 an
  unexplained gap in the other half of the same ratio should not be left
  standing. Likely candidates: multi-token-prediction layers or other tensors
  the exporter correctly drops. Not yet investigated.

## W12 — First-principles roofline model *(the actual deliverable)*

### Where the model stands, 2026-08-31

Every W12 item is built and every published number has been re-derived at least
once tonight. **Each correction moved the result against us, and each was found
by measuring rather than by arguing.**

| the claim | was | is | why it moved |
|---|---:|---:|---|
| Pro @1M, 554,700 mm², batch 1 | 54.2× → 35.4× | **5.90×** | GPU denied a topology; then per-user latency conflated with throughput; the corrected physical/energy assumptions lowered it again | <!-- figure: 5.90 src="results/roofline/n6_vs_a100/REPORT.md#Ratio after" table="latency separation" where="Model=DeepSeek-V4-Pro-0813;mm2=554700" name="Pro batch-1 iso-area ratio at 554,700 mm2, N6" -->
| Flash weight:KV @200K | 113.2:1 | **35.3:1** | two KV entry sizes read off the implementation, not measured | <!-- figure: 35.3 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].weight_to_kv_read_ratio_b1" name="Flash W:KV at 200K" -->
| Pro weight:KV @1M | 58.9:1 | **18.0:1** | the same two constants, by analogy | <!-- figure: 18.0 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].weight_to_kv_read_ratio_b1" name="Pro W:KV at 1M" -->
| on-wafer tensor-parallel | 116,278 tok/s | **6,000–7,200** | an all-reduce charged one flat hop however far it reached | <!-- figure: 7,200 src="results/roofline/n5_vs_b200/REPORT.md#Hard ceiling" table="Array or wafer" where="Design=Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1" tol="1%" name="on-wafer tensor hard ceiling, Qwen3-8B" why="the row states a deliberately rounded band; the artifact's Qwen on-wafer hard ceiling is 7,215.0 tok/s and Flash's is 6,040.5. The tolerance is the rounding the band declares, not slack." -->
| N5 vs B200, Pro @1M | 27.3× | **2.67×** | both of the above, plus the corrected physical/energy assumptions | <!-- figure: 2.67 src="results/roofline/n5_vs_b200/REPORT.md#Ratio after" table="latency separation" where="Model=DeepSeek-V4-Pro-0813;mm2=554700" name="Pro batch-1 iso-area ratio at 554,700 mm2, N5" -->
| per-region over broadcast @b64 | 27× | **2.73×** | busiest-region load plus the corrected model inputs | <!-- figure: 2.73 src="results/roofline/n6_vs_a100/REPORT.md#Per-region over broadcast" table="batch-amortisation" where="Model=DeepSeek-V4-Flash-0731;B=64;Spare silicon=sram" name="per-region over broadcast, Flash b64 sram" -->

**Two conclusions inverted rather than shrank**, which matters more than the
magnitudes:

- *"The ROM advantage erodes with batch"* holds only for the **dense** model.
  Qwen goes 5.83× at batch 1 to **2.72× at 256** — more than half the lead is gone, though it no longer inverts now that the array class is sampled on its own device-count ladder. Both <!-- figure: 5.83 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=Qwen3-8B;B=1;Pick=fastest" name="Qwen per-user iso-area ratio at B=1" --> <!-- figure: 2.72 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=Qwen3-8B;B=256;Pick=fastest" name="Qwen per-user iso-area ratio at B=256" -->
  sparse models now **rise**: Flash 6.52× → **35.09×**, because a GPU's per-user <!-- figure: 6.52 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=DeepSeek-V4-Flash-0731;B=1;Pick=fastest" name="Flash per-user iso-area ratio at B=1" --> <!-- figure: 35.09 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=DeepSeek-V4-Flash-0731;B=256;Pick=fastest" name="Flash per-user iso-area ratio at B=256" -->
  rate collapses faster than a ROM machine's once KV dominates. The original
  thesis — that sparsity is what makes ROM worth building — survives in a
  stronger form than it was stated.
- *"Bigger is better"* is false for latency. ROM per-user throughput falls
  **monotonically** with area, 6,464.4 tok/s at one wafer to 3,495.6 at twelve, so <!-- figure: 6,464.4 src="results/roofline/n6_vs_a100/REPORT.md#ROM after" table="latency separation" where="Model=Qwen3-8B;mm2=46225" name="Qwen ROM user tok/s at one wafer" --> <!-- figure: 3,495.6 src="results/roofline/n6_vs_a100/REPORT.md#ROM after" table="latency separation" where="Model=Qwen3-8B;mm2=554700" name="Qwen ROM user tok/s at twelve wafers" -->
  the best latency machine is the **smallest one that holds the model**.

**What the gates say.** The A100 gate is arithmetic and holds at 1.000000× <!-- figure: 1.000000 src="results/roofline/n6_vs_a100/REPORT.md#Ratio" table="Validation gates" where="Gate=A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2" name="A100 validation gate ratio" -->
through every correction. The Taalas HC1 gate is now **infeasible**, modelled at
0 tok/s and ratio 0.00× <!-- figure: 0.00 src="results/roofline/n6_vs_a100/REPORT.md#Ratio" table="Validation gates" where="Gate=Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user" name="Taalas HC1 validation gate ratio" --> because the reconstructed array does not fit in the
published die.
That failure is reported rather than tuned away: at least one of the ROM cell
ratio, array efficiency, checkpoint-size reconstruction, or reserved-area
terms is wrong for the shipping part.

**What the power gates say, without smoothing the asymmetry.** The corrected
A100 saturating-load reconstruction is 461.7 W against 400 W (1.15×), inside
the declared 2× gate. HC1 is 87.6 W against its published 200–250 W band
(0.44×–0.35×), so that gate fails by 2.3–2.9× even after ROM-array leakage is
charged. Static power is paid whether traffic moves or not, and thermal scaling
now binds where the generated study reports it. The capacity-infeasible HC1
reconstruction delivers no admitted tokens, so its attempted-step energy cannot
support a tokens-per-joule claim.


The program's purpose is a quantitative ROM-versus-HBM comparison. The functional
lanes are a precondition for it, not the product. These items are the product.

- [x] W12.1 `src/opentallas/roofline.py` — area-constrained roofline: a silicon
  area budget is allocated across ROM array, compute, SRAM, interconnect and HBM
  PHY, and capacity, bandwidth and compute roof are **derived outputs**. Replaces
  the placeholder profiles whose capacity and compute roof were independent free
  parameters with nothing tying either to area
- [x] W12.2 `configs/hardware/technology.json` — every density, latency and
  energy figure graded `measured`/`published`/`derived`/`assumed` with a source
- [x] W12.3 Latency model for distributed decode — decode is sequential across
  tokens *and* layers, and at batch 1 a pipelined array supplies no parallelism
  at all, so topology is chosen by hop latency against the per-token budget:
  single chip (0 hops), array with pipeline parallelism (N−1 serial hops), array
  with tensor parallelism (2 × layers collectives), wafer (on-wafer hops)
- [x] W12.4 MoE utilisation term — ROM weights are local to compute, so an
  unselected expert region contributes neither bandwidth nor compute. Engagement
  is `1 − (1 − k/N)^B`, not a constant
- [x] W12.5 **Validation gates that fail loudly rather than fit the answer.** The
  Taalas HC1 check evaluates an 8B model on 815 mm² at N6 against 16,960 tok/s
  per user. The corrected reconstruction is capacity-infeasible and returns
  zero, so the gate FAIL is the result and every extrapolation remains
  conditional on resolving it. The second gate keeps an A100 on the same model
  at batch 1 weight-bound at ~254 tok/s; it is an arithmetic identity, not an
  independent silicon measurement
- [x] W12.6 Iso-area studies with the silicon area stated on **both** sides, both
  topologies where viable, and the latency crossover reported rather than a
  topology assumed
- [x] W12.8 **The model is validated by the executed machine, not asserted.**
  `tools/validate_model_against_execution.py` checks an analytical prediction
  against the counters a real token-producing run recorded. On Qwen3-8B at 8,192
  tokens the analytical weight traffic is 15,136,811,008 B per step; the ROM lane
  measured **15,244,065,514** (ratio 1.007) and the HBM lane **15,262,287,257**
  (1.008), and the two lanes performed **identical arithmetic** —
  820,644,937,728 multiplications each. The 0.7–0.8% excess is the scales, index
  tables, rotary coefficients and activations the analytical weight model does
  not count; a *shortfall* would be a failure rather than a tolerance, and the
  tool treats it that way.

  This is what separates the performance work from arithmetic on a whiteboard. A
  reviewer is entitled to ask whether a projected speedup accounted for the whole
  system, and the only answer that settles it is a machine that ran the model end
  to end and moved the same bytes the projection assumed. It also makes the
  storage-class thesis a measurement: the two lanes differ only in which memory
  the bytes came from, and the arithmetic is bit-identical.

  What it does not validate is *time* — the functional device has no clock. It
  validates the quantities a roofline consumes, so that the time a roofline
  computes from them is a statement about hardware rather than about unexamined
  traffic.

  **The KV term is now checked too, and it comes out exact.** Until tonight the
  tool predicted KV traffic and never compared it to anything, which left the
  most important number in the model resting on nothing: at the 8,000-token
  sweet spot KV is the term that decides the ROM argument. It is checked in two
  halves because they catch different failures. The count of (layer, position)
  pairs attention visited is compared against the causal triangle a prompt of
  *P* tokens and *D* decode steps requires, which catches a machine that
  recomputes, caches across queries, or attends to a window instead of the whole
  past. The byte count is then compared against the profile's own entry size,
  which catches a row read at the wrong precision or width. Unlike weight
  traffic this term admits no allowance in either direction — nothing rides
  along with a KV row — so the tolerance is 0.1%, not 15%.

  | run | causal pairs | ratio | KV bytes | ratio | B per layer-position |
  |---|---:|---:|---:|---:|---:|
  | `TA-QW-CHAT-1` HBM | 244,296 | 1.0000 | 1,000,636,416 | 1.0000 | 4,096 | <!-- figure: 244,296 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.counters['attention.context_positions']" name="chat HBM causal pairs" --> <!-- figure: 1,000,636,416 src="results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json#record.counters['attention.kv_bytes_read']" name="chat HBM KV bytes" -->
  | `TA-QW-CHAT-1` ROM | 244,296 | 1.0000 | 1,000,636,416 | 1.0000 | 4,096 | <!-- figure: 244,296 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.counters['attention.context_positions']" name="chat ROM causal pairs" --> <!-- figure: 1,000,636,416 src="results/abi3/qwen3_rom_ta-qw-chat-1_execution.json#record.counters['attention.kv_bytes_read']" name="chat ROM KV bytes" -->
  | `TA-QW-8K-1` HBM | 1,208,107,008 | 1.0000 | 4,948,406,304,768 | 1.0000 | 4,096 | <!-- figure: 1,208,107,008 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.counters['attention.context_positions']" name="8K HBM causal pairs" --> <!-- figure: 4,948,406,304,768 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution.json#record.counters['attention.kv_bytes_read']" name="8K HBM KV bytes" -->

  The 8,000-token row is the one that matters: a machine that generated 193 real
  tokens at the stated sweet spot moved **4.95 TB of KV** and visited
  **1,208,107,008** (layer, position) pairs, and both are the analytical formula
  to the byte. The roofline's own Qwen designs size SRAM for 1,207,959,552 B of
  resident KV — 100.4 mm² of an 815 mm² die at N6 — from the same 4,096 bytes
  per layer-position that the machine was just measured reading. The prediction
  and the measurement are not merely close; they are the same number arrived at
  from opposite directions.

  The entry size is derived from the profile's traffic model rather than restated
  in the tool, so editing a profile cannot silently pass the check, and two
  mutation tests in `tests/test_execution_validation.py` halve the KV bytes and
  narrow the attention span to prove the check can fail. A validator nobody can
  fail is decoration.

- [x] W12.7 `tools/run_roofline_studies.py` and `results/roofline/` — canonical
  JSON, rendered report, consistency audit

## W11 — Governed comparison and release

- [~] W11.1 Qwen ROM vs HBM — **produced at 24 tokens, and QUALIFIED at 192.** At the
  8,000-token sweet spot with a matched 192-token budget the two lanes **disagree**:
  ROM matches the reference oracle on all 192, HBM diverges at index 137, emitting <!-- figure: 192 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.generated_token_count" name="Qwen ROM 8K tokens, W11.1" --> <!-- figure: 137 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.notes.first_divergence_index" name="Qwen HBM 8K divergence index" -->
  " world" where ROM and the oracle emit " universe". The mechanism is countable
  rather than speculative. The two lanes perform the same arithmetic to the
  operation — `tensor.multiplications` 57,012,268,302,336 on both, identical <!-- figure: 57,012,268,302,336 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.counters['tensor.multiplications']" name="Qwen ROM 8K multiplications" --> <!-- figure: 57,012,268,302,336 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.counters['tensor.multiplications']" name="Qwen HBM 8K multiplications" -->
  `attention.context_positions`, `kv_bytes_read` and `vector.elements` — while
  `control.loop_iterations` differs, 138,816 against 149,121. Same operations, <!-- figure: 138,816 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.counters['control.loop_iterations']" name="Qwen ROM 8K loop iterations" --> <!-- figure: 149,121 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.counters['control.loop_iterations']" name="Qwen HBM 8K loop iterations" -->
  different tiling, different accumulation order, different last-ULP logits. The
  artifacts record different association tuples — (library,
  version, device, **shape**, thread count) and the storage class determines the
  shape. What decides index 137 is `selection.tie_multiplicity` — 192 over 192
  tokens on ROM, **193 over 192 on HBM**. Exactly one HBM token has two candidates <!-- figure: 192 src="results/abi3/qwen3_rom_ta-qw-8k-1_execution.json#record.counters['selection.tie_multiplicity']" name="Qwen ROM 8K tie multiplicity" --> <!-- figure: 193 src="results/abi3/qwen3_hbm_ta-qw-8k-1_execution_192.json#record.counters['selection.tie_multiplicity']" name="Qwen HBM 8K tie multiplicity" -->
  at the argmax and the tie rule takes the lowest id, 1879 over 15494.

  **So the thesis holds for traffic and arithmetic and does not extend to the
  token stream at long context.** *"The two deployments differ only in where the
  bytes live"* is demonstrated at 24 tokens and false at 192, because where the
  bytes live determines the tiling. A token-identity claim between two backends
  has a horizon and the horizon must be stated: the historical 8K ROM/HBM pair
  first differs at index 137. A separate HBM-only agent episode first differs
  from its oracle at index 286; because no ROM agentic capture exists, that is
  not a ROM/HBM comparison horizon. This qualifies the storage-class claim and
  does not satisfy A7's external-oracle acceptance gate for the HBM lane; the
  analytical model's ratio 1.0000 on KV traffic and causal pairs does not
  convert that divergent token stream into a correctness result.

  The original 24-token result stands as recorded: **produced, and it is the
  storage-class thesis in executed counters** (`results/abi3/comparison_qwen_rom_vs_hbm.json`). Both lanes decoded 24 tokens matching the oracle, the two token sequences are identical, evidence class `functional_artifact_only`, `depends_on_assumption` false. **Five counters differ and all five are memory traffic**: the ROM target reads 363,485,791,728 B from ROM and the HBM target reads 366,294,894,160 B from HBM <!-- figure: 363,485,791,728 src="results/abi3/comparison_qwen_rom_vs_hbm.json#counter_deltas['rom.bytes_read'].left" name="ROM target ROM bytes read" --> <!-- figure: 366,294,894,160 src="results/abi3/comparison_qwen_rom_vs_hbm.json#counter_deltas['hbm.bytes_read'].right" name="HBM target HBM bytes read" -->, and the ROM target moves 437 MB / 61 MB through SRAM where the HBM target moves none. Nothing else in the 124-counter registry differs. That is the claim — *the two deployments differ only in where the bytes live* — demonstrated on executed counters rather than argued. DeepSeek now has its own governed historical functional pair: `results/abi3/comparison_deepseek_rom_vs_hbm.json` records an identical **4**-token prefix <!-- figure: 4 src="results/abi3/comparison_deepseek_rom_vs_hbm.json#token_agreement.common_prefix_length" name="DeepSeek ROM/HBM common prefix" --> with `depends_on_assumption: false`, while explicitly retaining the wafer's one logical node and HBM's **32** nodes <!-- figure: 32 src="results/abi3/comparison_deepseek_rom_vs_hbm.json#topology_cost.right.node_count" name="DeepSeek HBM comparison node count" -->. Its 66 counter deltas include topology-scaled work and backend control differences, so it is a correctness/topology comparison and must not be relabelled as the Qwen five-memory-counter equivalence result. The exact-200K accelerator-pair checker intentionally rejects this short, stateful, prior-build evidence; no production exact-200K ROM/HBM pair result exists.
- [ ] W11.2 TA-CMP-7-ASAP7: same, predictive view, no cross-view mixing —
  `results/abi3/asap7_comparison_readiness.json` is the source-current,
  machine-readable preflight, generated by
  `make abi3-comparison-asap7-readiness`. Its preflight status is `blocked`
  with **17** <!-- figure: 17 src="results/abi3/asap7_comparison_readiness.json#blocker_count" name="W11.2 readiness blocker count" -->
  fail-closed blockers; the checklist row remains open (`[ ]`), not in the
  checklist's blocked (`[!]`) state. No mandatory functional pair is closed; no
  capability names an ASAP7 characterization view; the ASAP7 tables lack the
  cluster and wafer fabric parameters; no cycle result binds an ASAP7
  capability, ASAP7 cost table, workload digest, and comparison-boundary
  digest while also proving successful trap-free completion, complete schedule
  coverage, zero contract gaps, and the exact topology/node count. The physical
  view covers only tensor, vector, and reduction blocks; attention, DMA, link,
  route, selection, and state remain missing, as do control, ROM/SRAM macros, either
  fabric, full-target area/energy, or calibrated uncertainty. Other-view cost
  tables and cycle results are inventoried only as exclusions, never admitted
  into a composite. `make abi3-comparison-asap7-gate` checks artifact freshness
  and intentionally exits nonzero until all same-view prerequisites exist.
- [~] W11.3 Evidence ledger: every number traced to executed counters or labeled
  external — `tools/check_prose_figures.py` resolves every retained annotation
  against its producing JSON, CSV, or generated Markdown value, and its
  non-regression map now covers every release document that currently carries
  checked annotations. `tests/test_prose_figures.py` proves the committed tree,
  provenance-binding mutations, exact per-document floors, and whole-document
  coverage loss. `tools/audit_prose_figure_coverage.py` and the canonical
  `results/abi3/prose_figure_coverage.json` now census every Markdown document
  under the release-prose boundary and retain every candidate matching the
  evidence-ledger unit rule as provenance-bound, unbound, or explicitly
  excluded context. Its v2 report also records the live Markdown heading path
  and applies `configs/evidence/prose_figure_triage.json`: every explicit rule
  has an exact expected match count and the audit refuses stale or ambiguous
  selectors. The initial conservative pass resolves **8** <!-- figure: 8 src="results/abi3/prose_figure_coverage.json#totals.unbound_triage.normative_or_example" name="W11.3 explicitly triaged normative/example candidates" --> ABI shape/algebraic
  examples and rejected legacy proxies as `normative_or_example`.
  **3,368** candidates remain explicitly `untriaged`. <!-- figure: 3368 src="results/abi3/prose_figure_coverage.json#totals.unbound_triage.untriaged" name="W11.3 candidates still awaiting triage" -->
  `make check-figures` fails on annotation, census, policy, or classification
  drift. This remains partial: triage is not proof, produced figures still need
  resolving annotations, and the remaining population must be classified as
  produced/external, normative/example, or missing-producer before the
  original every-number requirement can close.
- [x] W11.4 Final status report and README update — `README.md`,
  `docs/README.md`, this checklist, `docs/ABI3_PROGRAM_REPORT.md`, and
  `docs/EVIDENCE_LEDGER.md` now separate source-current evidence from retained
  historical horizons and state every cycle/performance non-claim. The
  follow-on clean-tree `make abi3-status` snapshot republishes the current
  83/10/1 top-level milestone arithmetic in `docs/PROGRAM_STATUS.md` and
  `results/abi3/program_status.json`, with `worktree_dirty: false`; the
  generated artifact records the exact clean source/documentation commit it
  summarizes

---

## Open issues raised by workers (tracked, not deferred silently)

- **OI-1 — on-device selection numerics are unqualified.** The Qwen exporter
  names `greedy_lowest_token_id_argmax_v1` and `exact_token_append_eos_v1`, but
  no qualification evidence exists for either. ABI 2.5 kept argmax on the host,
  so this is genuinely new numeric surface. Evidence is required before an
  acceptance claim; a differential against the reference oracle's token IDs is
  the natural form.
- **OI-2 — `CheckpointBinding` carries no per-binding checkpoint identity.**
  Model Graph v2's binding carried a `checkpoint_lock_id`; v3 records the lock
  id once in `source`. Acceptable for one-checkpoint graphs, insufficient if a
  graph ever mixes checkpoints. Revisit before any multi-source deployment.
- **OI-3 — `Tensor` has no layout field.** Head-shaped views rely on row-major
  equivalence between `(tokens, heads, head_dim)` and `(tokens, heads*head_dim)`.
  True today; would break for any non-row-major source tensor.
- **OI-4 — no governed stochastic sampling contract.** The neutral IR cannot
  express randomness and `SELECTION.SAMPLE` is unimplemented, so neither lane
  can honour a `do_sample: true` request. Greedy acceptance is unaffected
  (ADR-003 section 7 makes sampling optional), but inventing an RNG to close
  this would make every future result irreproducible. Closing it needs a
  versioned RNG and probability contract first.
- **OI-5 — descriptor CRC and header digests are not checked in RTL.** The RTL
  microsequencer enforces instruction and header CRC32C, but descriptor record
  CRCs and the header's four SHA-256 digests need a digest engine that does not
  exist yet. Until it does, RTL's "fail before work is issued" is narrower than
  the ABI's.
- **OI-6 — Yosys 0.68 cannot parse SystemVerilog packages**, so `rtl/abi3`
  cannot enter the repository's existing synthesis flow unchanged. The
  synthesis probe required textually inlining the package.
- **OI-7 — DeepSeek 32-node HBM capacity: closed for the deployment profile.**
  Two profiles are now built: `kernel_ir.v3.json` declares an 8,192-token
  context, which is what actually executes and what fits the 32-node cluster,
  and `kernel_ir.v3.capacity200k.json` declares 200,064 for capacity study.
  Original diagnosis follows. The
  reported overflow (172 GB per node against 96 GB) came from sizing activation
  arenas at the *architectural* endpoint rather than the *deployment's* declared
  context. Measured, at a declared context of 8,192 tokens — which is what
  actually executes — the arenas are 3.64 GiB instead of 152.39 GiB, and the
  32-node plan **fits at 4.65 GiB per node** against 96 GiB available. Sizing
  arenas at the capability endpoint is the error; ADR-003 section 19 makes such
  values capability fields precisely so a deployment can declare less.
  Two things remain open at the mandatory context:
  - **200,000 is not an admissible deployment context.** It must be a whole
    number of 128-token sliding windows, so the nearest admissible value is
    200,064. The workload contract should either adopt 200,064 or state that the
    prompt is 200,000 within a 200,064 context.
  - At 200,064 the plan fails earlier, in `main.layer00.routed_experts.gate`,
    where a routed-expert weight multiply is being planned as a contraction:
    operands `(1200384, 4096)` and `(1200384, 1)` share no depth axis. That is a
    backend classification bug at scale, not a capacity result.

- **OI-8 — `MEMORY_OBJECT.base_address` defaults to zero.** Every object can
  present at address zero, so the cycle model cannot map objects onto HBM
  channels or SRAM banks and substitutes a synthetic packed placement. Channel
  and bank conflict numbers from such a deployment are a property of the model,
  not of the plan. Backends must assign real base addresses; `bank_or_tile` has
  the same problem.
- **OI-9 — `SCHEDULE.resource_bound` has no defined unit** and `priority` is
  unmodelled. Both are recorded and explicitly not timed rather than silently
  consumed. ABI 3.0 does not say whether `resource_bound` counts lanes, engine
  instances or SRAM regions.
- **OI-10 — `Symbolic.maximum` semantics were never frozen.** Qwen writes
  `multiplier=1` so both readings agree; DeepSeek writes `multiplier=6,
  maximum=1572864`, which only parses as the *extent* maximum. The ROM backend
  took that reading; the other inflates the activation footprint six-fold
  (2.14 TB against 916 GB). The contract should say which.
- **OI-11 — `queue.max_occupancy` is an architectural-group counter no
  functional model can fill.** It sits outside the timing group, so the cycle
  model declines to write it rather than break the counter-agreement rule.
  Either it belongs in the timing group or the rule needs a named exception.
- **OI-12 — no capability advertises queue depth or issue width.** ADR-003
  section 9 makes them capabilities rather than assumptions, but only
  `max_outstanding_per_queue` exists; everything else comes from a cost table
  and is labelled assumed.
- **OI-13 — the released TileLang `fp4_gemm` is wrong on sm_120.** Maximum
  absolute error 6.52 against a signal of mean magnitude 1.28, verified against
  two mutually independent references that agree with each other to half a
  bfloat16 ulp. Because the routed experts are most of the model it does not
  crash; it produces fluent, on-topic, semantically empty text. The oracle uses
  the release's own documented FP8 recast and re-proves the check at every
  start. Any future use of that kernel must repeat the check.
- **OI-14 — the released `sparse_attn` kernel cannot launch at 64 heads on
  sm_120**, requesting 141,312 bytes of dynamic shared memory against 101,376
  available. Split into four 16-head launches, which is bitwise identical
  because the heads are independent, and is the per-rank head count the
  vendor's own world_size=4 configuration produces.
- **OI-15 — closed by A13 block extents.** The old HBM lowering wrapped nineteen
  operations in `SPAN_TOKENS` loops, so a 93-token prefill issued roughly 63,600
  one-row dispatches. The current lowering carries the token axis through
  symbolic views and loops only over bounded token blocks; the shipped Qwen
  prefill issues 693 engine operations in the RTL correlation campaign. The
  historical count records the defect that motivated A13, not a current gate.
- **OI-16 — closed. RTL implements amendment A13.** `rtl/abi3/ot_a3_view_resolver.sv`
  resolves a tensor view's A4 dynamic index terms and its A13 partial final
  extent, and `ot_a3_microsequencer.sv` runs it over every operand view of an
  OPERATOR-family instruction before that instruction issues, publishing the
  resolved extent and element offset on a view port. The descriptor image now
  carries 192 bytes per record rather than 128, because a TENSOR_VIEW's dynamic
  terms start at payload offset 72 and a 128-byte prefix stopped one block
  short. The correlation campaign compares 460 resolved views against <!-- figure: 460 src="results/rtl/abi3_campaign.json#correlation.view_resolution_count" name="RTL resolved views, OI-16" -->
  `runtime.sim.memory.ViewResolver.resolve` — the functional device's own
  resolver, evaluated against the loop bindings the device recorded at each
  issue — over eleven new vectors covering N divisible by T, N with a partial
  final iteration, N < T, N = 0, a constant-bounded loop, nested block loops
  folded by `min()`, and the A4 maximum of four dynamic terms. Three deliberate
  mutations of the RTL rule — removing the clamp, using the prose formula of
  section 12.4 verbatim, and narrowing the term counter so a four-term view
  wraps — are each rejected by both simulators, so the vectors are not
  vacuous.
- **OI-16a — wire format section 12.4's prose formula is narrower than the
  reference resolver, and the resolver is normative.** Section 12.4 states
  `dim0 = remaining if 0 < remaining < dim0 else dim0`.
  `ViewResolver._remaining_rows` additionally requires `remaining <
  bound_divisor` before a loop bounds anything, and folds several
  symbol-bounded loops over one view with `min()`. The two disagree only when a
  view's leading extent exceeds the block size: with `bound_divisor = 4`,
  `dim0 = 6` and `SPAN_TOKENS = 5`, the resolver leaves `dim0 = 6` and the
  prose formula gives 5. The RTL follows the resolver, and vector
  `a13_extent_above_block` pins the disagreement so it cannot drift silently.
  Nothing in `runtime/abi3/` was changed; if the intent is the prose reading,
  the resolver is the place to decide it.
- **OI-16b — the RTL lagged commit 46b6fb5 on abort accounting.** That commit
  made an abort discard the whole *declared* prepared state set
  (`counters.add("state.discards", len(session.states))`), which the RTL's
  state controller did not do: it counted only STATE.DISCARD instructions. The
  divergence was invisible because the checked-in vectors predated the commit
  and nobody had regenerated them. `ot_a3_state_controller.sv` now takes a
  `session_state_count` and adds it on `discard_all`, and the case record
  carries the deployment's STATE-descriptor count.
- **OI-16c — the vector generator could not regenerate its own vectors.** Since
  the verifier gained its schedule-completeness proof, `Workspace` in
  `tools/build_abi3_rtl_vectors.py` was rejected for reusing one TENSOR
  SCHEDULE descriptor across every engine family. It now creates one schedule
  per family. Separately, `case_work_bound_deficit` documented a work-bound
  deficit that `DeploymentBuilder._proved_work` has since repaired, so the case
  no longer traps; the work-bound trap is still covered by
  `case_work_bound`.
- **OI-17 — the ABI 2.5 retained deployment cannot load in a fresh checkout.**
  Four `tests/runtime` tests fail with "deployment file set differs from the
  final manifest": the manifest names 31 files and 13 are present, the missing
  18 being the multi-gigabyte `memory/hbm/hbm.*.bin` images that were never
  tracked. This is pre-existing and unrelated to ABI 3.0 - the failing lane
  imports neither `runtime.sim` nor `runtime.abi3` - but it means those four
  tests fail on any clone, so either the loader should distinguish "artifact not
  built" from "artifact corrupted", or the tests should skip when the images are
  absent.


- **OI-18 — a campaign run writes its deployment into the checkpoint
  directory.** `tools/run_abi3_campaign.py` uses `--deployment-root` both to
  resolve the checkpoint's relative weight paths *and* as the place to publish
  `program.bin`, `descriptors.bin` and `deployment.json`. Running a Qwen
  campaign therefore drops 104 KB into the user's Hugging Face cache. It is
  small and it is not a weight image — zero-copy holds — but a read-only
  checkpoint, a read-only mount, or a cache the user cleans between runs would
  each break it for a reason that has nothing to do with the deployment. The
  publish target should be a separate argument defaulting to `build/abi3/<id>/`,
  with the checkpoint root used only for reading.

- **OI-48 — closed: the cluster now shards experts and causally consumes every
  required transfer.** The old `output_columns`-only plan replicated the expert
  bank and correctly refused to emit fabric traffic that no consumer read. The
  replacement hybrid plan assigns eight consecutive experts to each of 32
  nodes, scatters the bounded dispatch activation, runs only the selected IDs
  owned by that node, sums the disjoint expert contributions before
  `EXPERT_REDUCE`, and reconstructs sparse KV from distinct feature bands. The
  governed W4.7 certificate proves the pack/link/unpack/consumer chain and
  records an empty `replicated_link_sites` map. The retained failure remains in
  repository history; it is no longer the current deployment claim.

- **OI-49 — closed: `main.lm_head.select` now gathers the final token of the
  span.** The original lowering selected row `position_offset`; every operand
  remained well-formed, so the semantic error could survive admission and
  produce logits for the wrong token. Both HBM and ROM exporters now bind a
  one-row span-relative gather to amendment A12's `SPAN_LAST_INDEX`. The runtime
  driver supplies `len(prompt) - 1` for prefill and zero for a one-row decode,
  so the same descriptor selects the final row in both phases. The governed
  W6.3/W6.4 captures execute this path and produce the same four oracle-identical
  tokens.

- **OI-50 — partially closed: a static audit originally found 21 defect groups
  affecting 1,173 of 3,230 DeepSeek operators (36%), none span-dependent.**
  Roughly 705 sat in the HBM backend, 426 in the shared exporter and neutral IR,
  and 42 in the engines. Its generic arity finding remains open: nothing
  centrally compares `len(kernel.inputs)` against `engine_for(kind).inputs`, so
  malformed neutral operators can still reach lowering with `NO_ID` in a
  mandatory slot instead of failing at graph admission. The separate
  `EXPERT_DISPATCH` output defect is closed: `runtime/sim/engines/route.py` now
  writes the optional `output_view_1` with flattened expert IDs in the same
  `(group, slot)` order as the dispatched rows, and both backends bind that view
  for the routed contractions that consume it. The historical audit counts
  describe the discovery point, not the current number of unresolved groups.

- **OI-51 — the focused compiler gate is red because its tests and proof tool
  lag intentional source contracts, not because this audit found bad inference
  semantics.** The exact focused run collected 43 cases and reported 5 failed,
  13 passed and 25 setup errors. All 25 errors come from a fixture that treats
  every operator attributed to `main.layer02.sparse_attention` as the
  `ATTENTION.SPARSE` consumer; the HBM pack/link/unpack helpers correctly share
  that source attribution but have no second input. Restricting the fixture to
  the actual attention opcode makes every ROM/HBM extent case pass. The one
  causal assertion similarly requires each intermediate producer in a valid
  event chain to appear directly in the terminal wait; it must instead prove
  transitive reachability to that waited event.

  The storage-equivalence half of this finding is now repaired and regenerated.
  Commit `e932d92` intentionally lets comparison-HBM objects replace ROM-local
  placement with `bank_or_tile = NO_NODE` and `base_address = 0`; schema
  `opentallas.abi3.storage_and_placement_equivalence.v2` names that exact
  coupled transition rather than silently normalizing it. It also fails closed
  on descriptor-header drift, any payload drift outside `storage_class`,
  `bank_or_tile`, `base_address` and the explicit historical `integrity_mode`
  exception, any non-derived program-header drift, unequal object sources,
  entrypoints or required features, admission failure, or a descriptor present
  on only one side. The regenerated current-graph certificates admit both
  builds and report `holds: true`: Qwen has 75 instructions, 239 descriptors
  and 18 permitted transitions (16 placed-to-unplaced plus 2 already-unplaced);
  DeepSeek has 1,171 instructions, 3,403 descriptors and 318 (312 plus 6), with
  zero residual violations in both.
  This closes the proof-tool/artifact portion of OI-51, not the product-backend
  gap in OI-19 and not, by itself, the attention-fixture and transitive-causality
  portions above. Fresh temporary Qwen and DeepSeek IR exports were
  byte-identical to the build artifacts, so generated-state contamination is
  ruled out. This triage does not justify rerunning a high-memory campaign.

- **OI-34 — the retained Qwen HBM run reached its historical 8,192-position
  capability boundary, and the device said so exactly where it should.**
  `TA-QW-8K-1` stopped at decode step 193 with

      DMA index view 45 names row 8192, outside the 8192 rows of the addressed view

  which is arithmetic, not a bug in that retained artifact: 8,000 prompt tokens
  plus 192 decoded is 8,192. The 193rd token needs row 8,192 and there is no such
  row. It failed closed at precisely the right position rather than wrapping,
  truncating or quietly computing against stale rows.

  The workload contract is frozen as 8,000 natural prompt tokens followed by
  the first official EOS or exactly 256 generated tokens, whichever happens
  first, with exact external-oracle identity over the complete terminal
  sequence. The implementation-level capacity repair is now complete. The
  source adapter, neutral IR symbols, all 36 KV resources, RoPE qualification
  and workload metadata share **8,256** positions; the current HBM capability
  declares **262,144** positions <!-- figure: 262,144 src="configs/hardware/abi3_capability/hbm_sram_single_chip.json#limits.max_context_positions" name="current Qwen HBM maximum context" --> and the ROM capability declares exactly **8,256** <!-- figure: 8,256 src="configs/hardware/abi3_capability/rom_qwen3.json#limits.max_context_positions" name="current Qwen ROM maximum context" -->. Both fresh temporary deployments admit, and the HBM and ROM short smokes reach a normal token-cap stop rather than a capacity trap. The ROM/HBM planners also allocate the otherwise easy-to-miss padded final block. Thus the historical failure remains correctly diagnosed evidence for its old build, but it is no longer the expected result of current source. OI-34's implementation defect is repaired; W10.1 remains partial because no retained complete current-source EOS-or-256 capture has yet passed the independent acceptance gate.

- **OI-33 — the accelerator's tokens diverge from the oracle on the
  repeated-token stress workload, and this is the first token divergence this
  program has produced.** `TA-QW-STRESS-1` ran to completion — 8,000 prompt
  tokens, 32 decoded, 11,941 s — and was recorded `status: diverged`, not
  `pass`, which is the reference gate doing exactly the job it was given this
  morning. Under the campaign runner as it stood twelve hours ago this would
  have been recorded as a pass, because nothing compared the tokens to anything.

  The divergence is small and highly structured, and the structure is the
  finding:

  | | |
  |---|---|
  | prompt | 8,000 tokens, **one distinct token id** — maximally degenerate |
  | first divergence | index 2: accelerator `279` (" the"), oracle `264` (" a") |
  | then | the oracle emits a third `271` newline; the accelerator emits two |
  | after that | accelerator `[3:12]` **equals** oracle `[4:13]` exactly — a nine-token aligned run at shift +1 |
  | ties | `selection.tie_multiplicity` 33 over 32 tokens, so exactly one genuine tie |
  | legitimacy | no problems; every token in vocabulary |

  So the two are producing the *same continuation*, offset by one, after a
  single word choice flipped between near-tied candidates. This is not a broken
  computation; it is an argmax flip in a regime where the logits are nearly
  degenerate by construction.

  **What it falsifies is a claim this program has been resting on.** Amendment
  A7's justification measured the blocked contract against the sequential one
  and found 0.012–0.089% of elements differing by 1–5 ULP with *zero* vocabulary
  argmax changes. That measurement was taken on natural prompts. It does not
  hold here, and a workload of 8,000 identical tokens is precisely the instrument
  for finding that out — which is what the mandatory stress contract is for.

  **The discriminating experiment has now answered: degeneracy, not context
  length.** `TA-QW-8K-1` is natural prose at the same 8,000-token context. It
  agreed with the oracle for **137 consecutive tokens**, then substituted
  ` world` for ` universe` in *"the whole of the ___ and its inhabitants"* — two
  interchangeable words after an identical 137-token prefix — and **realigned
  immediately**, agreeing again from index 138. No ties were involved anywhere:
  `selection.tie_multiplicity` is 193 over 193 tokens, multiplicity one each.

  So A7's claim is **qualified, not withdrawn**. Zero argmax changes over 137
  tokens of natural prose at the mandatory context; an argmax flip at index 2 on
  a prompt of 8,000 identical tokens. The contract is sound for the inputs it
  was measured on and the stress workload marks the boundary — which is what it
  is for. The honest statement is that the blocked contract preserves the
  argmax on natural text and does not preserve it under engineered degeneracy,
  and A7 should say so rather than claiming a general invariance.

  The source-current acceptance audit found an additional provenance defect
  that must be resolved before interpreting a rerun. A7 says shape is part of
  blocked association identity, but `implementation_identity` records only the
  library/device/thread environment and prose saying that shape matters. It
  does not retain the executed contraction shapes. Current HBM lowering uses
  512-token blocks while ROM lowering's zero block setting resolves to the
  whole context, so equal top-level implementation dictionaries do not prove
  the same association. W10.2 now requires an executed-association manifest and
  a frozen harmonized-or-target-specific policy before either long capture.

- **OI-32 — one capability, two sources of truth, and they have now diverged.**
  `configs/hardware/abi3_capability/hbm_sram_single_chip.json` and
  `compiler.backends.hbm_sram.capability.PROFILES['single-chip']` both claim to
  be the shared single chip. They no longer agree: the code-built profile lists
  `deepseek_rmsnorm_binary32_v1` and the file on disk lists
  `normalization_rms_norm_bf16_v1`, so their digests are `7afce65b…` and
  `b2a1af21…`. The campaign runner takes the JSON; the tests and the checkers
  take the code.

  It surfaced because a byte-identity claim did not survive checking. Adopting
  A8's frozen RMSNorm contract name in the DeepSeek exporter changed the derived
  contract union, which changed the code-built capability, which changed **Qwen's
  deployment digest** — `11d825368add0494` → `bd80131488912974` — while Qwen's
  program body and descriptor table stayed byte-identical (all 75 instructions
  equal, table digest `7d599fdcd8c017ce` on both sides). The agent that made the
  change deliberately left the JSON alone *because* editing it would move Qwen's
  digest, and the digest moved anyway through the other source. That is the
  whole hazard in one sentence.

  Nothing here is wrong in itself: a deployment binds the capability it was
  admitted against, so a capability change *should* change its digest. What is
  wrong is that there are two capabilities with one name, and a change to either
  is invisible from the other. **One must be generated from the other, with a
  check that fails when they drift** — `tools/publish_abi3_capabilities.py`,
  added for this, makes the code profile the definition and the JSON a published
  artifact. It currently reports both files drifted
  (`hbm_sram_single_chip` profile `7afce65b…` against published `b2a1af21…`;
  `hbm_sram_cluster_32` profile `93fe2c66…` against published `3afaa0fa…`).
  **Republishing is deliberately deferred**: the two 8,000-token Qwen workloads
  are executing against the published files right now, and rewriting them
  mid-run would leave those records citing a capability digest the repository no
  longer contains. It is a one-command step once they land, and it will change
  the deployment digest of everything admitted against them — which is correct,
  and is exactly why it should be a deliberate act rather than a silent one — the same discipline `loop_trip_count` now
  enforces for the trip formula (OI-22) and for the same reason: two
  restatements of one thing is how two of them come apart.

- **OI-31 — a vector set can rot into agreeing with the implementation instead
  of checking it.** Refining A13 changed what `a13_nested_blocks` resolved to,
  and the obvious response — re-record the golden — would have been wrong: that
  case exists to exercise the `min()` fold of two clamping loops, and under the
  refined rule its second loop no longer qualified, so re-recording would have
  kept the test green while deleting what it tested. It was repaired instead, by
  changing the loop's block *and* its stride together.

  `a13_four_terms` had the identical defect and nobody had noticed. Its golden
  would have silently become `[4, 4, 1, 1]` on the next regeneration, with its
  docstring still describing a fold that no longer happened. It was found by
  someone reading the case, not by any test.

  The general point is worth keeping: a golden regenerated from the
  implementation it checks is only as good as the reason the case was written,
  and that reason lives in prose. When a rule changes, every case that depended
  on the old rule has to be re-read, not re-recorded. The two new cases here —
  the mHC shape and the mixed-axis view — had **no** coverage before, and the
  mutation evidence shows it: dropping the stride condition survives cases 0
  through 23 and dies only at case 24.

- **OI-30 — commit `8841b95` carries another change's admission proofs.** A14's
  two `participant_scope` refusals were staged into my A13 clamp fix, because I
  staged `runtime/abi3/verifier.py` whole while an agent was adding to it. The
  code is correct and present in HEAD; only the history misattributes it. This is
  the third time tonight that staging a file rather than a change has muddled a
  commit, and it is the reason a `git add <path>` on a shared file is not
  actually safer than `git add -A` while anyone else is writing.

- **OI-28 — CLOSED: the functional device now has a real node dimension.**
  Commit `8dfddac` binds node identity, executes peers, and makes collectives
  data-bearing rather than pretending node 0 is the cluster. The governed
  32-node HBM capture subsequently admitted, completed prefill and three decode
  transactions, and emitted four oracle-identical tokens. The post-fix decode
  gate is now closed; missing multi-node execution was not the issue.
- **OI-29 — CLOSED: the mHC branch reduction is executable in both backends.**
  The later A20 slot mapping and backend lowerings replaced the diagnostic
  `EXPERT_SUM` dead end. Current ROM and HBM token captures both run the full
  DeepSeek prefill and emit token 13806; ROM then completes three decode
  transactions. The old alternative-design discussion remains in Git history,
  but it is no longer an open ABI decision.

- **OI-27 — the governed comparison tool cannot produce a comparison. Any
  comparison.** *(Fixed; the first comparison now exists — see W11.1.)* `tools/build_comparison_report.py` exists to compare Qwen ROM
  against Qwen HBM and the DeepSeek wafer against the DeepSeek cluster. Run on
  the first pair that has ever had two real records, it refuses on three counts,
  and two of them are structural — no pair of distinct deployments can ever
  satisfy them.

  1. **`generation_policy_digest` digests deployment-local identifiers.** The
     two Qwen lanes are semantically identical — `selection_mode` 0, `tie_rule`
     0, the same two EOS tokens, the same vocabulary size, zero RNG seed. They
     differ on `token_ring_object_id` (36 vs 24), which two deployments *must*
     assign differently; on a declared `max_new_tokens` bound (512 vs 8192),
     which is a capability limit rather than the run's limit; and on
     `counter_class_id`. Comparing the whole record's digest therefore refuses
     every pair, forever. The gate should compare the policy's *semantics*.
  2. **The `technology_view` gate forbids the study.** "No number crosses views"
     is the right principle for the wrong field: it exists so a SKY130 number is
     never compared with an ASAP7 one. But the capability's `technology_view`
     conflates the *characterization* view with the *memory technology* —
     `single_chip_rom_declared_v1` against `shared-hbm-sram-chip-v3` — and the
     memory technology is the study's independent variable. It has to differ.
     The two axes need separating: gate on characterization, report both memory
     technologies side by side and never normalise them away, exactly as the
     tool already promises for topology cost.
  3. **`tokenizer_sha256` is empty on one side**, and that one is real but
     small: two different evidence writers source it differently. The campaign
     runner reads `workload.metadata.tokenizer_sha256`, which the workload files
     do not carry, while the earlier wrapper read it from the oracle. One
     source, and it should be the workload.

  That the tool has never run is itself the finding. W11.1 and W11.2 were
  blocked on something nobody had tried, and the gate — which is otherwise a
  good gate, and refused for exactly the reasons a good gate should look at —
  had never been exercised against two real records.

- **OI-26a — CLOSED: the concurrent-writer evidence incident is retained as
  a process guard.** An earlier DeepSeek record was written while its exporter
  and IR were still changing, so it never described one stable source tree.
  Evidence artifacts are now single-writer captures generated by committed
  tools; W6.3 and W6.4 cite those captures rather than the transient
  execution file. The old failure remains in Git history, not as current lane
  evidence.

- **OI-25 — fourteen test files still validate the retired ABI 2.5 lane, and
  one of them fails.** `tests/compiler/test_tensor_accelerator_qwen_rtl_rope.py`
  fails `test_rope_builder_reproduces_retained_artifact` — and it fails on a
  clean checkout of HEAD, so it predates tonight's work. It rebuilds a vector
  artifact from `results/tensor_accelerator/qwen3_full_model_physical/ir/tensor_kernel_ir.json`
  (the ABI 2.5 IR, not `build/ir-v3/qwen3-8b/kernel_ir.v3.json`) and from a
  second repository at `~/OpenTallas-ta-integration/`. Thirteen more
  files in `tests/compiler/test_tensor_accelerator_qwen_*.py` have the same two
  dependencies.

  Whether they pass tells us nothing about ABI 3.0: they exercise a pipeline
  this program has replaced, from inputs that are not the shared IR. **The lane
  should be quarantined** — moved to a clearly named directory with a note that
  it is superseded — so that no reader takes a green tick there as evidence for
  the new ABI, and so a red one is not mistaken for an ABI 3.0 regression.

  I have deliberately *not* silenced the failing test. Skipping the one that
  happens to be red, while leaving thirteen green ones making claims about a
  retired lane, would make the suite look better and the repository less honest.
  The quarantine is a single coherent change and belongs in one commit, once the
  concurrent backend work has settled. Related to [OI-17], which is the same
  lane failing for a different reason.


- **OI-26 — CLOSED: the compressed-attention join now carries an explicit
  phase binding.** Commit `77f847c` made the frontend publish
  `phase_symbol_binding` with `position_start = 0` for prefill and
  `span_tokens = 1` for decode. Those released phase facts collapse the
  two-symbol row sum onto existing affine ABI symbols: `5 × span / 4 + 128`
  in ratio-4 prefill and `context / 4 + 129` in ratio-4 decode (with the
  analogous ratio-128 forms). Both ROM and HBM lower one phase-specific extent,
  propagate it to the consumer, and refuse a missing or malformed binding.
  `tests/compiler/test_attention_join_phase_extent.py` exercises both phases
  and negative mutations. No new request-scoped symbol or wire-format amendment
  was needed. The ROM token artifact executes three decode steps with this
  lowering, and the fresh HBM artifact now does the same with four
  oracle-identical tokens. W6.3 therefore carries end-to-end evidence rather
  than relying on the unit proof.

- **OI-24 — a zero-source memory object committed its whole declared arena on
  activation, and the DeepSeek cluster plan declares 160.4 GiB of it.**
  `MemoryObject` built zero-sourced objects with `np.full`, which writes every
  byte and so commits the entire arena up front. The kernel killed the process:
  `Out of memory: Killed process 706797 (python3) ... anon-rss:153687324kB`.
  `np.zeros` is calloc-backed and faults lazily, giving identical bytes at a
  ~33 GB peak. The arena is sized by `span_tokens` at its 8,192 maximum, so this
  scales with the declared context and not with the workload — a short prompt
  paid the full price.

- **OI-23 — historical: the committed state image held one layer's KV window out of
  thirty-six, so the ABI's durability record is not a durability record.**
  *(Found by the withdrawn restart-exactness work; no production action remains
  under the frozen zero-`STATE` profile.)* `Device._apply_commit` reads
  `prepared[0 : rows × row_bytes]` and appends it to the committed image at the
  cursor. That is a coherent contract for one logical stream. But
  `_state_view` in the HBM backend merges 36 layer KV resources into a single
  physical resource whose prepared image holds 36 populated windows of 393,216
  bytes, one per layer. A commit publishes the window at offset 0 and nothing
  else, and the committed image is never read back. A restart from the ABI's own
  durability record would lose 35 of 36 layers of KV cache.

  The abandoned durability design would have required a different layout. The
  accepted implementation instead removed production `STATE` descriptors and
  writes every layer's KV directly to ordinary live buffers, so no durable row
  concatenation, committed image, or restart repair is required.

  The old observation remains useful provenance for why restart/durability
  claims were withdrawn. It is not an open implementation item and must not be
  restated as a requirement to "restart from the committed state."

- **OI-22 — the HBM lane's block loop ran once at any prompt length, so every
  token past the first 512 was silently dropped.** *(Found by the ROM lane; fixed.)*
  `Device._loop_trip` computes `trip = ceil(ceil(span / bound_divisor) / step)`
  — it has already divided the symbol by the divisor before the step applies.
  The HBM lowering emitted `step = bound_divisor`, which divides a second time
  and yields `trip = 1` at *every* span. Verified on a clean checkout of HEAD, by
  summing the rows a token-indexed view presents across all iterations:

  | span | trip | rows presented |
  |---:|---:|---:|
  | 93 | 1 | 93 |
  | 512 | 1 | 512 |
  | 600 | 1 | **512 of 600** |
  | 8,000 | 1 | **512 of 8,000** |

  Every gate this program has passed used a prompt of 93 or 112 tokens, which
  fits in one block, so the encoding was correct on every workload anyone had
  run. The mandatory 8,000-token workload would have returned an answer computed
  from one sixteenth of its prompt. It would not have looked wrong: it would
  have produced fluent tokens, and under the campaign runner as it stood this
  morning it would have been recorded as `status: pass`, because nothing
  compared them to anything (OI-18's sibling defect, fixed earlier today). The
  two findings are the same lesson from opposite ends.

  The fix is `step = 1` with `upper_bound = trip`: the induction variable counts
  blocks, not rows. Confirmed end to end as well as at the resolver: a
  600-token prompt (one block plus 88) now runs to completion with
  `tensor.embedding_rows = 600`, which is `prompt + generated - 1` because the
  last generated token is never fed back. Before the fix that number would have
  been 512. Coverage is then exact at 93, 512, 600, 1,024, 8,000 and
  8,192, and the deployment still admits with the same 75 instructions, 218
  descriptors and work bound 22,715. **It was found only because the ROM lane
  lowered the same graph independently and encoded the loop differently** —
  neither lane's tests could have caught it alone.

- **OI-21 — closed: prefill attention was a per-(token, head) Python loop that
  blocked the mandatory 8,000-token workload.**
  `runtime/sim/engines/attention.py::_execute_dense_gqa` iterates every (token,
  head) pair, and inside the token loop it copies the whole K cache
  (`np.ascontiguousarray(keys[:context, kv_head, :])`) though the copy depends
  only on the head and the context. Measured on this machine, one (token, head)
  score costs ~1.26 µs per context row, near-perfectly linear in context, so for
  Qwen3-8B's 32 query heads over 36 layers a prefill of T tokens costs
  `32 × 36 × 1.26 µs × T²/2` in score matmuls alone:

  | T | score matmuls | with the value matmul |
  |---:|---:|---:|
  | 93 | 6.3 s | ~13 s |
  | 1,000 | 726 s | ~24 min |
  | 8,000 | 12.9 h | **~26 h** |

  *Two corrections to that table, both from doing the work.* The `T²/2` is
  optimistic: prefill runs as a **single** span-8000 transaction with
  `context = 8000`, so every token contracts the full context and the cost is
  `T²`. The real 8K prefill was about 21.5 h of attention. **Fixed:** the engine
  now contracts a block of query rows per call rather than one (token, head)
  pair, with key and value blocks hoisted per KV head, and the BF16 kernel picks
  a K-major schedule for large tiles. Measured 8.5–10.3× on prefill and 2.0–2.2×
  on decode, which is memory-bound and has little to batch. The 8K prefill is now
  ~2.55 h.

  The arithmetic did not move, and that was checked rather than argued: 168
  engine comparisons against the pristine pre-change modules, bit-identical on
  raw `uint16` codes with every counter equal, plus 916 kernel comparisons, an
  adversarial operand pool of signed zeros and subnormals, and mutation testing
  that catches a reversed reduction, a `np.tile`-for-`np.repeat` mask swap and a
  transposed write-back. Both differentials refuse to report a pass at zero
  comparisons.

  At this historical discovery point, `TA-QW-8K-1` had run for 43 minutes and
  was still in prefill softmax; it and `TA-QW-STRESS-1`, which has the same
  8,000-token prompt, were stopped rather than left to run for a day and a half
  each. Both were subsequently completed to their retained divergence or
  boundary outcomes after the batching fix described above. The performance
  defect is closed; W10.1 and W10.2 remain partial for their separately recorded
  correctness and acceptance reasons.

- **OI-20 — the IR uses `CONCAT` for a broadcast along a new axis.** The
  DeepSeek mHC hyper-connection expansion is a `CONCAT` kernel whose four inputs
  are all the same tensor (`main.token_embed.output`, `[span_tokens, 4096]`) and
  whose output is `main.hc_expand.output`, `[span_tokens, 4, 4096]`. The ABI's
  `REDUCTION.GROUPED_CONCAT` concatenates along axis 0, giving `[416, 4096]` for
  a 104-token span, so the engine refuses — correctly — and the DeepSeek HBM
  deployment cannot prefill. Two things are worth recording beyond the fix.
  First, the engine's `np.concatenate(...).reshape(out_dims)` would have
  produced numerically wrong data had the shape check not stopped it, placing
  four consecutive *tokens* where four *streams* belong; the fail-closed check
  is the only thing between that and a plausible wrong answer. Second, since all
  four inputs are the same tensor, this is a broadcast, and ABI 3.0 views carry
  per-axis strides — a zero-stride axis expresses it with no operator and no
  data movement at all.

  **Corrected census, and half of it now closed.** The other 84 `CONCAT`
  kernels are not all axis-0. Forty-one of them
  (`main.layerNN.index_topk.concat`, `main.layerNN.compressed_dense_indices.concat`)
  join along **axis 1** — 128 window indices beside 512 selected indices, or
  beside a symbolic compressed-group width — which `REDUCTION.GROUPED_CONCAT`
  cannot express at all, since axis 0 would join two operands of different
  widths. These now lower as one `DMA.TRANSFER` per input into its own column
  range of the destination row: the same `key_then_value` idiom
  `_emit_state_append` already uses for a fused KV append, with an arena object
  in place of a state resource, and stated in offsets rather than performed by
  an operator. The remaining 43 are the `attention_kv_view` row-space
  compositions, which are a different problem entirely — see OI-26.

- **OI-19 — the storage-and-placement equivalence proof remains narrower than
  the product-backend claim resting on it.**
  `tools/prove_storage_class_equivalence.py` builds the same current graph twice
  *through the ROM backend*, varying immutable weights from ROM-local placement
  to HBM with the required unplaced sentinel. The regenerated v2 certificates
  are current and hold: Qwen emits 75 instructions and 239 descriptors on both
  sides, with 18 governed transitions; DeepSeek emits 1,171 and 3,403, with 318.
  No descriptor-header or non-permitted payload difference remains, both sides
  admit, and object sources, entrypoints, required features and instruction
  bodies are identical. This closes the stale-certificate half of OI-19.

  The stronger property—that the two *product backends* lower the graph to the
  same program—still does not hold. Current Qwen ROM is 75/239 and shipped HBM
  is 75/218; the proof's HBM-labelled member is a ROM-backend comparison build,
  not that shipped HBM deployment. Until product lowering agrees, a measured
  ROM-versus-HBM difference is partly a difference between two compilers. Keep
  every cross-backend comparison explicit about program and descriptor
  differences rather than treating it as pure storage evidence.

- **OI-35 — the DeepSeek compressor's decode position is off by `ratio - 1`, and
  the descriptor has no way to say otherwise.** The released compressor pools
  `ratio` tokens into one row and rotates that row at the position of the
  *first* token it pooled. In prefill that is `g * ratio` for group `g`, which
  is exactly what a strided view of the position range yields; in decode the
  vendor supplies `start_pos + 1 - ratio`, and the same view yields
  `start_pos`. The compressed KV write has the matching gap: its row is the
  completed group's ordinal, which prefill gets right as `g` and decode gets
  wrong as `start_pos`.

  A tensor view offsets by `symbol * stride` and cannot subtract a constant, so
  the two placements cannot be one descriptor. Three ways out, in order of
  preference: split the compressor's kernels by phase, which the neutral IR
  already supports (`phases`) and which no exporter currently uses; add a
  runtime symbol for the completed-group ordinal; or admit a signed dynamic
  term. Not reachable by `TA-DS-CHAT-1` at two decoded tokens — `should_compress`
  is `(start_pos + 1) % ratio == 0` and is false at both steps, so the
  compressor's rotation and write do not fire — but it will be reachable by any
  workload that decodes past a ratio boundary, which is every longer one.

- **OI-36 — the two backends disagree about what `VECTOR.ROPE`'s `aux_id_0`
  holds.** `compiler/backends/rom/common/program.py` falls back to the
  iteration domain's `head_dim`; `compiler/backends/hbm_sram/plan.py` falls back
  to the coefficient view's width, which is twice it. Both write the graph's
  `rotary_width` when it states one, so DeepSeek agrees across backends and
  Qwen — which states none — does not: 128 from one and 256 from the other, for
  the same operator of the same model.

  It surfaced the moment amendment A16 made the slot load-bearing: an engine
  that checked `aux_id_0` against the axis it rotates admitted the ROM
  deployment and refused the HBM one. The engine now reads the slot only under
  the partial-rotation contracts, which is correct — the whole-axis contract's
  result does not depend on it — but that leaves a frozen field carrying two
  different meanings depending on which backend emitted it, which is the same
  hazard as OI-32 in a smaller field. One fallback should be deleted, not
  reconciled: the graph states `rotary_width` or the operator does not rotate
  partially.

- **OI-37 — the partial quantiser's operand view is narrowed in one backend
  only.** DeepSeek quantises the 448 non-rotary channels of a 512-wide KV
  vector, and amendment A16 section 16.2 puts the narrowing in the view: same
  row stride, fewer elements of it. `compiler/backends/rom/common/program.py`
  does that; `compiler/backends/hbm_sram/lower.py` does not, so the shared-chip
  DeepSeek lowering still presents the full row to a code output that is 448
  wide and the vector engine refuses it. The ROM wafer lane reached this rung
  first because it is further along; the HBM lane will reach the identical one.

- **OI-38 — amendment A16 invalidated the retained RTL evidence binding, exactly
  as that binding is designed to.** `tools/rtl_abi3_campaign.py` hashes
  `docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md` into the campaign artifact
  "so that a change to the ABI invalidates this evidence instead of silently
  outdating it". Adding A16's row to the section 14 amendment index changed that
  document, so `tests/compiler/test_rtl_abi3.py::test_retained_campaign_artifact_is_bound_to_these_sources`
  now fails on `docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md changed since the
  campaign was recorded`. The mechanism worked; the evidence needs re-recording.

  The campaign was re-run to confirm the RTL itself is unaffected: **iverilog
  PASS, verilator PASS**, and the only differences from the retained artifact
  are that one document digest and the text of Verilator's compile log (a
  `PINCONNECTEMPTY` warning whose rendering is not byte-stable between runs).
  Every case, every check count and every correlation figure is identical.
  Re-recording is `python3 tools/rtl_abi3_campaign.py --force`, and it is left
  to the RTL lane rather than done here: `results/rtl/abi3_campaign.json` is
  that lane's evidence, and an evidence file with two writers is OI-26a.

  **Closed.** The RTL lane re-recorded it. Three of the thirty bound sources had
  moved, not one: the A16 index row in the wire format, and `runtime/sim/device.py`
  and `runtime/sim/memory.py` from the node-dimension commit. None of A13–A16
  needed an RTL change — A13 was already implemented in `ot_a3_view_resolver.sv`
  including the `stride0 * bound_divisor` leading-axis test, and A14, A15 and A16
  all land in fields the ABI 3.0 microsequencer never reads. The re-recording
  therefore added vectors that *say* so rather than asserting it: the set now
  issues LINK (it never had), carries a `participant_scope` of 2 and 1 at
  COMMUNICATION payload offset 80 against an otherwise identical NODE-scoped
  program, carries a `scale_block_rows` of 2 at TENSOR_VIEW payload offset 104 on
  a view A13 also clamps, and populates the three operand-multiplexer arms — a
  third input, a second output, a nonzero `aux_id_0` — that A16's conventions are
  the first to need and that nothing had ever selected. The marker moved from
  `cases=43 headers=43 programs=36 issues=143 views=368 traps=11` to
  `cases=50 headers=50 programs=41 issues=154 views=391 traps=11`, checks from
  3,017 to 3,282, both simulators identical.

  The same pass re-recorded the other stale retained RTL artifact,
  `testdata/compiler/tensor_accelerator/qwen3_rtl_rope_vectors.json`, which bound
  `runtime/tensor_accelerator/rope.py` and went stale on OI-34's
  `MAX_POSITIONS` 8000 → 8192. Exactly two fields moved — the oracle digest and
  the derived `vector_set_id`, now
  `3a792b0dec8dd7277540841409accca66521f2f05f977c1cd6b6d9e5361f4f76` — and every
  coefficient and output code is byte-identical, because `MAX_POSITIONS` is an
  input to `coefficient_table_bf16` and not to `rope_bf16`. That the digest could
  move without anything checking whether the deployed table still followed is now
  fixed at the source: the builder reproduces the shard's 8,000 rows from
  `coefficient_table_bf16(8000)` and compares them byte-for-byte, so the bound
  and the four near-midpoint corrections are load-bearing here rather than
  merely hashed. Re-derived at 200 decimal digits over the whole extended domain,
  **8,000..8,191 introduces no fifth correction**; and 8,191 is not a position
  these vectors can hold, because the deployed coefficient table is 8,000 rows
  and 7,999 remains its edge. The present 8,192→8,256 RoPE-source extension
  intentionally makes that retained vector source binding stale again. The
  legacy 8,000- and 8,192-row prefixes remain byte-identical and the new
  8,192..8,255 interval adds no correction, but the RTL vector artifact must be
  regenerated before it is described as source-current for this head.

- **OI-41 — CLOSED. `ATTENTION.SPARSE` was made data-bearing at `97c5fb6`, and
  this entry asserted otherwise for fourteen hours afterwards.**
  `runtime/sim/engines/attention.py:150` imports
  `runtime.tensor_accelerator.sparse_attention.sparse_attention_bf16_codes` and
  calls it; the scalar reference is kept only for the paths the kernel refuses.
  Measured head-to-head against the reference on the same operands, outputs
  compared as raw uint16: **682x** at 64 selected rows and **802x** at 128,
  bit-identical in both. The 12.5 ms per (head, row) this entry quoted
  reproduces exactly on the reference, so the defect was real when written.

  At the production shape on the ROM lane -- span 104 x 64 heads x 512, ~5,900
  gathered rows per site -- attention costs **0.29-0.33 s per site**, about
  **13.2 s** across 43 sites. It is **0.2% of the prefill** and does not appear
  in the profile. The oracle at that shape would be 1.36 h per site and 58.4 h
  for one prefill, so this entry's conclusion -- that no token was reachable
  through it -- was correct and had already been acted on.

  **The failure was mine and it belongs on the record rather than being quietly
  closed.** I renumbered this entry at `84f1194` to resolve a collision I had
  created, and renumbered it without reading whether it was still true. An entry
  in the register of record asserting a defect fixed half a day earlier is the
  same class as a document quoting a retracted figure, and the same class as
  W6.4 citing a record whose failure text contradicted it. Editing an entry is
  not verifying it, and touching one without checking it is how a register
  becomes fiction.

  What the work found in its place is where the time actually goes:
  `TENSOR.ROUTED_MATMUL` is **80.5%** of the prefill, 38% of it MXFP4 operand
  widening. That is [OI-42].

- **OI-42 — `TENSOR.ROUTED_MATMUL` is 80.5% of a DeepSeek prefill, and 38% of
  that is widening operands it will use once.** With `top_k` 6 over 256 experts,
  104 tokens make 624 assignments over about 552 (slot, expert) pairs, so a
  contraction averages **~1.1 rows** — and each one widens a full
  `[2048, 4096]` MXFP4 weight. That is 4.6e9 nibble decodes against 5.2e9 MACs
  per site: the widening is comparable to the arithmetic it feeds.

  **The sequential contract is not the wall, which was checked rather than
  assumed.** At the routed shape `np.matmul` under the blocked association is
  only 1.0–4.7x faster, against 5.3x at the dense shape, because the work is
  bandwidth-bound on the weight. Changing the MoE association would buy single
  digits, not orders of magnitude, so no contract needs weakening. Threading was
  tried and rejected: bit-exact at 4, 8 and 16 workers and 0.02–1.8x.

  The fix is expert-outer iteration in `runtime/sim/engines/tensor.py` — one
  partial per slot, widening each expert once — and it is bit-exact, since the
  ascending-slot combination is untouched. Worth about 20% of the prefill. It
  moves `rom.bytes_read` and the scale-multiplication accounting, both
  load-bearing figures, so it belongs to that engine's owner and wants
  re-recording with it.

- **OI-43 — two simulators disagreed about the same source text, and only the
  two-simulator rule made it visible.** Under Icarus 11, a wildcard-imported
  package identifier that appears *only* inside a module-instance
  port-connection expression is not resolved against the import: Icarus creates
  an implicit one-bit net of that name, and that net then shadows the constant
  **for the whole module**. In `rtl/abi3/ot_a3_engine_array.sv`, `DMA_SCATTER`
  read as `z`, every `DMA.SCATTER` dispatched as unimplemented, and
  `DMA_GATHER` — which never appears in a port connection — kept working. Three
  of twenty-nine cases failed and twenty-six passed; **Verilator resolved the
  constant correctly**, so the disagreement was between the simulators, not
  between the RTL and the model.

  The signature is the program's usual one: legal values, no trap, nothing
  refused. A single-simulator campaign would have recorded either a pass or a
  narrow failure and neither would have named the cause.

  **Closed.** Every file in the engine RTL now refers to package members as
  `pkg::name` and carries no `import`, pinned by
  `tests/compiler/test_rtl_abi3_engine.py::test_engine_rtl_carries_no_wildcard_package_import`.
  The same change is what makes those blocks synthesisable at all: the pinned
  Yosys 0.68 Verilog frontend rejects `import` in a module header and in a
  module body alike, so **every existing `rtl/abi3/` block that still carries a
  wildcard import — `ot_a3_microsequencer.sv`, `ot_a3_view_resolver.sv`,
  `ot_a3_state_controller.sv`, `ot_a3_event_scoreboard.sv`,
  `ot_a3_loop_stack.sv`, `ot_a3_program_header.sv`,
  `ot_a3_instruction_decoder.sv`, `ot_a3_collective_engine.sv` — cannot be
  synthesised or routed by this toolchain today.** That is why W9 has physical
  numbers for the ABI 2.5 blocks and none for the ABI 3.0 control plane, and it
  is a two-line change per file rather than a design problem.

  **Closed at the front end.** The seven blocks that still carried the import
  (`ot_a3_microsequencer.sv`, `ot_a3_view_resolver.sv`,
  `ot_a3_state_controller.sv`, `ot_a3_event_scoreboard.sv`,
  `ot_a3_loop_stack.sv`, `ot_a3_program_header.sv`,
  `ot_a3_instruction_decoder.sv`) now refer to every package member as
  `ot_a3_pkg::name`; `ot_a3_collective_engine.sv` already referred to
  `ot_a3_link_pkg` by scope and is unchanged.
  `tools/rtl_abi3_control_plane_synth_check.py` elaborates each of the eight
  standalone (`hierarchy -top`, `proc`, `check`) under the pinned local Yosys
  (the sky130hd synthesis path) and under the Yosys inside the pinned
  OpenROAD-flow-scripts image with the tree mounted read-only at `/src` (the
  asap7 path), and records the same run against the commit before the fix,
  where all seven fail with `syntax error, unexpected TOK_IMPORT`;
  `results/rtl/abi3_control_plane_yosys_elaboration.json` is the artifact and
  `tests/compiler/test_rtl_abi3.py::test_control_plane_rtl_carries_no_wildcard_package_import`
  pins the form shut. The control-plane campaigns
  (`tools/rtl_abi3_campaign.py`, `tools/rtl_abi3_deployment_campaign.py`,
  `tools/rtl_abi3_shipped_prefix_campaign.py` and its multicast variant) were
  re-run on Icarus and Verilator before and after the change from a pinned
  worktree of each commit: every observation is identical and only the seven
  source digests and the compile-log line numbers differ. What this does
  **not** close: no control-plane block has been synthesised to a netlist or
  routed; elaboration is the front-end precondition, W9's physical gap and G2
  stay open until a routed `microsequencer` block exists. The front-end block
  has since been routed on its own — `ot_a3_microsequencer` at
  `STATE_COMPAT = 0`, `results/physical_abi3/asap7/a3_microsequencer/pnr.json`,
  numbers and scope in that record's `notes` — and G2 stays open because its
  evaluator now requires the datapath array and the memory system in the same
  netlist (`configs/gates/redesign_gates.json`).

- **OI-44 — the shared binary32 *adder* is the critical path, and it is a
  coding shape rather than a technology limit.** Measured on SKY130 HD
  `tt_025C_1v80`, each operation synthesised alone as one combinational cloud
  between registers with the pinned Yosys 0.68 + ABC mapping and OpenSTA:
  `ot_fp32_rne_pkg::fp32_add_rne` needs a clock period of **66.97** ns <!-- figure: 66.97 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#static_timing.fmax_search.min_clock_period_ns" name="fp32 add min period, OI-44" -->
  in a cell area of **13,868.7** µm² <!-- figure: 13,868.7 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_add.json#synthesis.cell_area_um2" name="fp32 add cell area, OI-44" -->,
  while `fp32_mul_rne` needs **29.385** ns <!-- figure: 29.385 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#static_timing.fmax_search.min_clock_period_ns" name="fp32 mul min period, OI-44" -->
  in **33,660.4** µm² <!-- figure: 33,660.4 src="results/physical_abi3/sky130hd/a3_numeric_probes/fp32_mul.json#synthesis.cell_area_um2" name="fp32 mul cell area, OI-44" -->
  — the adder is 2.28x slower and 41% of the area. `fp32_to_bf16_rne` needs
  **3.84 ns** <!-- figure: 3.84 src="results/physical_abi3/sky130hd/a3_numeric_probes/bf16_round.json#static_timing.fmax_search.min_clock_period_ns" name="bf16 round min period, OI-44" -->
  and the whole storage-format decoder **2.62 ns** <!-- figure: 2.62 src="results/physical_abi3/sky130hd/a3_numeric_probes/format_decode.json#static_timing.fmax_search.min_clock_period_ns" name="decode min period, OI-44" -->.
  That adder is what sets `ot_a3_mac_lane`'s minimum period. Artifacts:
  `results/physical_abi3/sky130hd/a3_numeric_probes/*.json`, from
  `rtl/test/ot_a3_numeric_probes.sv` through
  `tools/run_abi3_physical.py --view sky130hd --stages synth,sta --fmax-search`.

  The cause is a 27-iteration cancellation-normalisation loop whose iterations
  are *dependent*, so it synthesises to twenty-seven conditional one-bit shifts
  and twenty-seven exponent decrements in series; `shift_right_jam_28`'s
  28-iteration sticky reduction has the same shape. A leading-zero count
  followed by one barrel shift is functionally identical and far shorter.

  **Not changed here, deliberately.** `rtl/ot_fp32_rne_pkg.sv` is shared with
  the ABI 2.5 production blocks and physical campaigns over those blocks were
  in flight while this was measured; editing a shared numeric package under
  another campaign's feet is how a correlated artifact quietly stops matching
  its sources. It belongs to that file's owner, and any rewrite must re-run
  `tools/rtl_abi3_engine_campaign.py`, which compares 10,000 result words
  bit for bit and is exactly the check that would catch a rewrite that moved
  one.

  **This does not retire `power.fabric_clock_hz = 1e9`.** SKY130 is a 130 nm
  open foundry PDK and `docs/OPEN_PDK_SELECTION.md` forbids feature-size
  scaling from it, so no frequency here transfers to N6, N5 or N4. That
  constant stays `assumed`. What does transfer is the structural statement:
  the lane's period is set by one unpipelined binary32 addition written as a
  serial shift chain, and that is true at any node.

- **OI-45 — fixed: the diagnostic CLIs allowed blocked-GEMM identity to drift.**
  The governed DeepSeek token records fix `OMP_NUM_THREADS`,
  `OPENBLAS_NUM_THREADS`, and `MKL_NUM_THREADS` at eight because the linked
  BLAS's thread count is part of the blocked binary32 association. A bare
  operator-bisect invocation inherited none of those variables and therefore
  produced different layer-0 hashes even though the deployment, workload, and
  runtime source hashes were unchanged. Repeating it with the governed identity
  reproduced the retained boundary hash exactly.

  The three accelerator CLIs now establish eight as their default before any
  NumPy/runtime import, preserve an explicit caller override, and record the
  implementation identity in diagnostic lanes as well as token captures.
  `results/abi3/deepseek_v4_layer00_norm_input_bisect.json` records both lanes
  as NumPy 2.2.6 with scipy-openblas 0.3.29 and all three thread variables at
  eight; it also records identical RMSNorm inputs, weights, frozen-contract
  outputs, and layer-1 boundary inputs. Subprocess tests remove the variables
  and prove the default, then set all three to another value and prove the
  override remains authoritative.

  **Claim boundary:** this closes replay identity, not DeepSeek ROM numeric
  correctness. It changed no numeric contract and did not by itself turn the
  then-divergent token sequence into a pass.

- **OI-46 — fixed: ROM discarded routed span batching.** With the OI-45
  implementation identity fixed, the historical
  `results/abi3/deepseek_v4_lane_activation_bisect.json` compares all 44
  logical P32 prefill boundaries: boundaries 0--31 are byte-identical and
  boundary 32, the layer-4 input produced by layer 3, is the first difference.

  The early-stop operator trace in
  `results/abi3/deepseek_v4_boundary32_operator_bisect.json` compares 193
  terminal layer-3 outputs and first differs at `EXPERT_REDUCE` source kernel
  331, invocation 2. Its 64 comparable reducer inputs make the direction
  unambiguous: all 32 shared-expert payloads match, and 31 of 32 routed payloads
  match. The only divergent routed payload is invocation 2, where leading
  slice 2 differs and the other five selected-expert slices are identical.
  Reducer arithmetic therefore cannot be the origin.

  The follow-on `results/abi3/deepseek_v4_routed_chain_input_bisect.json`
  traces sources 317--324. A shape-normalized inspection aligns ROM's 32 row
  invocations with HBM's batched leading axis: all 2,368 comparable slices
  match, including route IDs, normalized inputs, FP8 dispatch/QDQ data,
  gate/up outputs, SwiGLU and route-weight inputs, weighted activations, and the
  FP8 activation plus expert IDs entering source 324. The first semantic
  difference is source 324's routed down-projection output at global selected
  row 14, the same prompt-row-2 / selected-expert-slice-2 result observed by the
  reducer.

  HBM realizes source 324 as a `[192,128]` local projection followed by two
  collection/reshaping operators; the old ROM program computed `[6,4096]` once
  per prompt row. The defect was the batching, not the reducer or weight map:
  ROM retained the six selected experts but dropped the request's 32-row span
  across `EXPERT_DISPATCH`, QDQ, routed GEMMs, SwiGLU and route weighting. The
  fixed lowering carries `top_k * span_tokens` as one affine leading extent,
  broadcasts route weights across it, and copies selected expert IDs once for
  the complete request. The rebuilt source-324 result and every source-331
  reducer row match HBM, including the formerly divergent row 14; boundary 32
  is now the HBM hash `91a6ccd7…`.

  The retained bisectors remain useful causal evidence but are pre-fix
  artifacts. They stop before commit and make no token claim. The governed
  capture in W6.4 is the authority for the fixed program's tokens.

- **OI-47 — fixed: compressed ROM state views discarded their global base
  slot.** Each physical ROM state object pools congruent resources from all 43
  layers. Its dynamic loop term correctly advanced by one slot for the first
  run and by two for the period-2 body, but `_state_view` reset the static
  element offset to the row column whenever a loop existed. Layer 2 therefore
  started at cache slot 0 instead of 2, and the layer-3 and layer-4
  representatives both started at slot 0 instead of 3 and 4. Prefill survived
  because each layer wrote immediately before reading its current rows; decode
  consumed aliased history from another layer.

  The lowering now keeps `slot * window + column` as the static base and adds
  the loop induction stride to it. The alternating-stack regression checks
  each emitted sparse-attention representative against its deployment-global
  state slot. The production deployment independently admits with 1,171
  instructions and 3,403 descriptors; its window-cache representatives have
  bases 0, 2, 3 and 4, with the latter pair advancing by two. The governed run
  then produces `[13806, 345, 7472, 55560]`, compares all four oracle positions
  with no divergence, and matches the HBM capture. The governed pairwise report
  records the same four-token common prefix and `depends_on_assumption: false`.

  **Claim boundary:** this is full-depth functional execution over the
  32-token prompt plus three decode steps. It is not long-context threshold,
  timing, RTL arithmetic, physical or silicon evidence, and it says nothing
  about token 5.
