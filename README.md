# OpenTallas

**Model-specific inference silicon, developed in the open.**

[Documentation](docs/README.md) · [Plain-language overview](docs/OVERVIEW.md) ·
[Specification](spec/README.md) · [Results](results/) ·
[Contributing](CONTRIBUTING.md)

![Conceptual OpenTallas fixed-model decode architecture](docs/assets/architecture-overview.svg)

OpenTallas explores a direct architectural question: if a deployed model's
weights are immutable, what changes when those weights live in mask ROM beside
the compute that consumes them instead of making a round trip through HBM for
every generated token?

This repository follows that question from model and traffic analysis through a
unified compiler/runtime ABI, functional and cycle simulation, public-reference
RTL, physical-design proxies, and extracted open-PDK circuit experiments. The
goal is not a persuasive spreadsheet. It is an inspectable evidence chain in
which every result states what produced it and what it does *not* prove.

> **Research status**
>
> OpenTallas is an active hardware research program, not a fabricated product.
> The performance numbers below are outputs of deterministic analytical models,
> not measured silicon benchmarks. Bounded functional executions, RTL campaigns,
> and public-PDK experiments exist at their explicitly documented scopes; a
> complete target implementation, foundry signoff, and silicon validation do not.
> Start with the [current program report](docs/ABI3_PROGRAM_REPORT.md), the
> [generated status](docs/PROGRAM_STATUS.md), and the
> [evidence methodology](docs/METHODOLOGY.md) before extending a claim.

## Why put model weights in ROM?

A conventional accelerator is flexible: both model weights and mutable KV state
live in off-chip memory, so the same hardware can run many models. Decode makes
that flexibility expensive because every new token reads a large fraction of
the active weights again.

OpenTallas trades model flexibility for locality. Immutable weights are encoded
in dense mask ROM and distributed alongside model-specific compute. Activations,
KV cache, session state, and all other mutable data remain in SRAM or HBM.

| | Conventional HBM accelerator | OpenTallas ROM architecture |
|---|---|---|
| Immutable weights | Share HBM capacity and bandwidth with mutable state | Fixed in local mask ROM |
| Mutable KV and session state | HBM/SRAM | HBM/SRAM; never placed in ROM |
| Decode data movement | Re-read active weights from HBM for each token | Sweep local ROM; reserve external bandwidth for mutable state |
| Deployment model | General-purpose and reloadable | Model-specific; changing weights requires a new ROM image/mask |
| Where it should help most | High batch can amortize weight reads | Low-batch, weight-dominated, stable deployments |
| Where the advantage recedes | — | Long contexts, large batches, collectives, KV service, power, or capacity become the bottleneck |

ROM is therefore not “faster HBM.” It changes the storage hierarchy and moves
the system bottleneck. The project measures where that shift helps, where it
stops helping, and which assumptions decide the answer.

## The architecture

The executable program uses one ABI 3.0 stack across two models and two storage
backends: Qwen3-8B and DeepSeek-V4-Flash, each lowered for a conventional
HBM/SRAM target and a model-specific ROM target. A target is a checked set of
descriptors, capabilities, and placement decisions—not a separate simulator.

```text
checkpoint + workload
        │
        ▼
canonical model graph ──► backend-neutral IR ──► ABI 3.0 program
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                    HBM/SRAM deployment                         ROM deployment
                              │                                           │
                              └──────── verifier + device + counters ─────┘
                                                    │
                                      functional / cycle / RTL evidence
```

At the hardware level, immutable weight service is spatially distributed,
mutable memory has a separate path, and deterministic stage/reticle/tile
communication carries activations and reductions. The
[architecture specification](spec/ARCHITECTURE.md),
[ABI decision](docs/TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md), and
[wire format](docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md) define the detailed
contract. The analytical studies also use DeepSeek-V4-Pro as a scaling workload;
that does not make it a third executable ABI target.

## Performance at a glance

OpenTallas publishes two complementary comparisons:

1. **Iso-node architecture attribution** asks what the storage architecture
   changes at a broadly matched technology generation. The “stock” side is the
   fastest feasible conventional HBM GPU cluster in the study at the same active
   microbatch—not a measured vendor benchmark.
2. **Area-constrained selection** gives each side approximately the same silicon,
   lets each choose its own parallelism, and selects a ROM design by a stated
   per-user-rate-per-area rule. This is the project's final area-aware
   comparison, not a claim about finished silicon.

For DeepSeek-V4-Flash at 200K context and batch 1, the central iso-node scenarios
produce:

| Study | OpenTallas ROM | Conventional HBM comparator | Per-user advantage | Binding ROM term |
|---|---:|---:|---:|---|
| N7-class ROM/HBM2e vs A100/HBM2e | **8,050.1 tok/s** | **614.4 tok/s** | **13.10×** | layer collectives | <!-- figure: 8,050.1 src="results/iso-node/n7_architecture_attribution/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N7 central ROM user rate, README" --> <!-- figure: 614.4 src="results/iso-node/n7_architecture_attribution/REPORT.md#GPU user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N7 central A100 user rate, README" --> <!-- figure: 13.10 src="results/iso-node/n7_architecture_attribution/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N7 central same-batch advantage, README" -->
| N4-class ROM/HBM3e vs B300/HBM3e | **12,629.3 tok/s** | **1,650.7 tok/s** | **7.65×** | layer collectives | <!-- figure: 12,629.3 src="results/iso-node/leading_node_market/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N4 central ROM user rate, README" --> <!-- figure: 1,650.7 src="results/iso-node/leading_node_market/REPORT.md#GPU user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N4 central B300 user rate, README" --> <!-- figure: 7.65 src="results/iso-node/leading_node_market/REPORT.md#Same-B ratio" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N4 central same-batch advantage, README" -->

These are per-user decode rates. Aggregate server throughput, resident-session
capacity, cost, and energy are separate quantities and must not be inferred from
this table.

### Back-of-the-envelope: where the benefit comes from

The hardware-independent traffic screen makes the opportunity visible. For one
DeepSeek-V4-Flash token at 200K context and batch 1:

| Active weight read | Mutable KV read | Weight / KV-read ratio |
|---:|---:|---:|
| **11.218 GB** | **317.456 MB** | **35.34×** | <!-- figure: 11.218 src="results/model-traffic/REPORT.md#B1 active weight" table="Raw traffic inputs" where="Model=DeepSeek-V4-Flash-0731;Context=200000" name="Flash active weight traffic at 200K, README" --> <!-- figure: 317.456 src="results/model-traffic/REPORT.md#KV read/user/token" table="Raw traffic inputs" where="Model=DeepSeek-V4-Flash-0731;Context=200000" name="Flash KV read traffic at 200K, README" --> <!-- figure: 35.34 src="results/model-traffic/REPORT.md#B1" table="Weight / KV-read ratio" where="Model=DeepSeek-V4-Flash-0731;Context=200000" name="Flash weight-to-KV traffic ratio at 200K, README" -->

That **35.34× is a traffic ratio, not a speedup**. Once weight service moves to
ROM, KV, compute, and communication remain. The central N7 point is computed from
these independently modeled service terms:

| Component | Time per token |
|---|---:|
| Local ROM weight service | **7.828 µs** | <!-- figure: 7.828 src="results/iso-node/n7_architecture_attribution/analytical.json#points[architecture=ROM-wafer-N7-HBM2e-central,model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_size=1].component_times_s.rom_full_array_read_C4" scale="1e6" name="N7 ROM weight service, README" -->
| Mutable HBM KV service | **41.979 µs** | <!-- figure: 41.979 src="results/iso-node/n7_architecture_attribution/analytical.json#points[architecture=ROM-wafer-N7-HBM2e-central,model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_size=1].component_times_s.kv_beachfront_C8" scale="1e6" name="N7 HBM KV service, README" -->
| Tensor compute service | **25.932 µs** | <!-- figure: 25.932 src="results/iso-node/n7_architecture_attribution/analytical.json#points[architecture=ROM-wafer-N7-HBM2e-central,model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_size=1].component_times_s.compute_C5" scale="1e6" name="N7 compute service, README" -->
| Serialized layer collectives | **69.821 µs** | <!-- figure: 69.821 src="results/iso-node/n7_architecture_attribution/analytical.json#points[architecture=ROM-wafer-N7-HBM2e-central,model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_size=1].component_times_s.collective_floor_C6" scale="1e6" name="N7 collective service, README" -->
| Pipeline efficiency | **0.90** | <!-- figure: 0.90 src="configs/hardware/n7_architecture_attribution.json#wafer_architectures[name=ROM-wafer-N7-HBM2e-central].pipeline_efficiency" name="N7 pipeline efficiency, README" -->

Weight, KV, and compute can overlap; the collective term is serialized. Using
the rounded report values:

```text
token interval = (max(7.828, 41.979, 25.932) + 69.821) / 0.90
               = 124.222 µs

per-user rate  = 1 / 124.222 µs
               = 8,050.1 tokens/s
```

The result is much smaller than the raw traffic ratio because the bottleneck has
moved to mutable-state service and communication—the behavior a full-system
model is supposed to expose.

### Back off the headline: deterministic envelopes

No leading-node OpenTallas ROM macro exists to supply one measured answer. Each
iso-node study therefore reruns the system under conservative, central, and
aggressive hardware scenarios. These are deterministic engineering envelopes,
not confidence intervals.

| Study | Central ROM rate | ROM rate, conservative–aggressive | ROM/HBM advantage, conservative–aggressive |
|---|---:|---:|---:|
| N7 vs A100 | **8,050.1 tok/s** | **1,287.0–23,767.7 tok/s** | **2.09×–38.69×** | <!-- figure: 8,050.1 src="results/iso-node/n7_architecture_attribution/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N7 central point in envelope, README" --> <!-- figure: 1,287.0 src="results/iso-node/n7_architecture_attribution/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].rom_per_user_tokens_s_low" name="N7 conservative ROM rate, README" --> <!-- figure: 23,767.7 src="results/iso-node/n7_architecture_attribution/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].rom_per_user_tokens_s_high" name="N7 aggressive ROM rate, README" --> <!-- figure: 2.09 src="results/iso-node/n7_architecture_attribution/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].same_batch_speed_ratio_low" name="N7 conservative advantage, README" --> <!-- figure: 38.69 src="results/iso-node/n7_architecture_attribution/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].same_batch_speed_ratio_high" name="N7 aggressive advantage, README" -->
| N4-class vs B300 | **12,629.3 tok/s** | **1,637.9–42,373.7 tok/s** | **0.99×–25.67×** | <!-- figure: 12,629.3 src="results/iso-node/leading_node_market/REPORT.md#ROM user tok/s" table="Central-envelope" where="Model=DeepSeek-V4-Flash-0731;B/stage=1" name="N4 central point in envelope, README" --> <!-- figure: 1,637.9 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].rom_per_user_tokens_s_low" name="N4 conservative ROM rate, README" --> <!-- figure: 42,373.7 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].rom_per_user_tokens_s_high" name="N4 aggressive ROM rate, README" --> <!-- figure: 0.99 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].same_batch_speed_ratio_low" name="N4 conservative advantage, README" --> <!-- figure: 25.67 src="results/iso-node/leading_node_market/analytical.json#uncertainty_bands[model=DeepSeek-V4-Flash-0731,context_tokens=200000,batch_per_stage=1].same_batch_speed_ratio_high" name="N4 aggressive advantage, README" -->

The conservative N4-class point is effectively parity, which is as important as
the central result. The envelope is computed by changing declared ROM capacity
and service assumptions, HBM resources, bandwidth/compute efficiencies, MoE
balance, repair, clock, synchronization, and pipeline derates, then rerunning
capacity, service, communication, and thermal gates. It is not a percentage
discount applied to the headline. See [assumptions](docs/ASSUMPTIONS.md) and the
[comparison methodology](docs/METHODOLOGY.md) for the complete contract.

### Final area-aware performance benefit

The area-constrained studies prevent a wafer from winning merely by being much
larger. They choose a non-dominated ROM design using per-user rate and rate per
square millimetre, then compare it with a conventional HBM design at the closest
whole-device silicon area. Both sides may choose their own parallelism.

The selected batch-1 points are:

| Technology study | Workload | Selected ROM organization | Silicon mm², ROM / HBM | User tok/s, ROM / HBM | Resident sessions, ROM / HBM | Per-user advantage |
|---|---|---|---:|---:|---:|---:|
| N6 vs A100 | Qwen3-8B, 8K | 7-die array, SRAM KV | **5,705 / 5,782** | **3,517.9 / 560.0** | **1 / 403** | **6.28×** | <!-- figure: 5,705 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="N6 Qwen ROM area, README" --> <!-- figure: 5,782 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_silicon_area_mm2" name="N6 Qwen HBM area, README" --> <!-- figure: 3,517.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="N6 Qwen ROM user rate, README" --> <!-- figure: 560.0 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_per_user_tokens_s" name="N6 Qwen HBM user rate, README" --> <!-- figure: 1 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.max_resident_users" name="N6 Qwen ROM residents, README" --> <!-- figure: 403 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_max_resident_users" name="N6 Qwen HBM residents, README" --> <!-- figure: 6.28 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_speed_ratio" name="N6 Qwen per-user advantage, README" -->
| N6 vs A100 | DeepSeek-V4-Flash, 200K | 1 wafer, HBM KV | **46,225 / 46,256** | **4,707.9 / 721.7** | **448 / 2,797** | **6.52×** | <!-- figure: 46,225 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.silicon_area_mm2" name="N6 Flash ROM area, README" --> <!-- figure: 46,256 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_silicon_area_mm2" name="N6 Flash HBM area, README" --> <!-- figure: 4,707.9 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="N6 Flash ROM user rate, README" --> <!-- figure: 721.7 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_per_user_tokens_s" name="N6 Flash HBM user rate, README" --> <!-- figure: 448 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.max_resident_users" name="N6 Flash ROM residents, README" --> <!-- figure: 2,797 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_max_resident_users" name="N6 Flash HBM residents, README" --> <!-- figure: 6.52 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_speed_ratio" name="N6 Flash per-user advantage, README" -->
| N6 vs A100 | DeepSeek-V4-Pro, 1M | 4 wafers, SRAM KV | **184,900 / 185,024** | **2,375.7 / 357.7** | **1 / 1,545** | **6.64×** | <!-- figure: 184,900 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.silicon_area_mm2" name="N6 Pro ROM area, README" --> <!-- figure: 185,024 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_silicon_area_mm2" name="N6 Pro HBM area, README" --> <!-- figure: 2,375.7 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_tokens_s" name="N6 Pro ROM user rate, README" --> <!-- figure: 357.7 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_per_user_tokens_s" name="N6 Pro HBM user rate, README" --> <!-- figure: 1 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.max_resident_users" name="N6 Pro ROM residents, README" --> <!-- figure: 1,545 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_max_resident_users" name="N6 Pro HBM residents, README" --> <!-- figure: 6.64 src="results/roofline/n6_vs_a100/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_speed_ratio" name="N6 Pro per-user advantage, README" -->
| N5 vs B200 | Qwen3-8B, 8K | 5-die array, SRAM KV | **4,075 / 4,800** | **4,941.0 / 978.7** | **1 / 388** | **5.05×** | <!-- figure: 4,075 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.silicon_area_mm2" name="N5 Qwen ROM area, README" --> <!-- figure: 4,800 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_silicon_area_mm2" name="N5 Qwen HBM area, README" --> <!-- figure: 4,941.0 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_tokens_s" name="N5 Qwen ROM user rate, README" --> <!-- figure: 978.7 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_per_user_tokens_s" name="N5 Qwen HBM user rate, README" --> <!-- figure: 1 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.max_resident_users" name="N5 Qwen ROM residents, README" --> <!-- figure: 388 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.iso_area_gpu_max_resident_users" name="N5 Qwen HBM residents, README" --> <!-- figure: 5.05 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=Qwen3-8B].recommended.per_user_speed_ratio" name="N5 Qwen per-user advantage, README" -->
| N5 vs B200 | DeepSeek-V4-Flash, 200K | 30-die array, SRAM KV | **24,450 / 24,000** | **2,627.4 / 1,465.1** | **1 / 1,637** | **1.79×** | <!-- figure: 24,450 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.silicon_area_mm2" name="N5 Flash ROM area, README" --> <!-- figure: 24,000 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_silicon_area_mm2" name="N5 Flash HBM area, README" --> <!-- figure: 2,627.4 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_tokens_s" name="N5 Flash ROM user rate, README" --> <!-- figure: 1,465.1 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_per_user_tokens_s" name="N5 Flash HBM user rate, README" --> <!-- figure: 1 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.max_resident_users" name="N5 Flash ROM residents, README" --> <!-- figure: 1,637 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.iso_area_gpu_max_resident_users" name="N5 Flash HBM residents, README" --> <!-- figure: 1.79 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Flash-0731].recommended.per_user_speed_ratio" name="N5 Flash per-user advantage, README" -->
| N5 vs B200 | DeepSeek-V4-Pro, 1M | 3 wafers, HBM KV | **138,675 / 139,200** | **2,648.8 / 746.8** | **265 / 1,339** | **3.55×** | <!-- figure: 138,675 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.silicon_area_mm2" name="N5 Pro ROM area, README" --> <!-- figure: 139,200 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_silicon_area_mm2" name="N5 Pro HBM area, README" --> <!-- figure: 2,648.8 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_tokens_s" name="N5 Pro ROM user rate, README" --> <!-- figure: 746.8 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_per_user_tokens_s" name="N5 Pro HBM user rate, README" --> <!-- figure: 265 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.max_resident_users" name="N5 Pro ROM residents, README" --> <!-- figure: 1,339 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.iso_area_gpu_max_resident_users" name="N5 Pro HBM residents, README" --> <!-- figure: 3.55 src="results/roofline/n5_vs_b200/analytical.json#design_selection.models[model=DeepSeek-V4-Pro-0813].recommended.per_user_speed_ratio" name="N5 Pro per-user advantage, README" -->

The resident-session columns are part of the result. A per-user ratio is a
latency comparison, not automatically an aggregate-throughput or serving-capacity
comparison. Whole-device granularity also means the areas are close rather than
always identical; notably, the N5 Qwen comparator receives more silicon than the
ROM side. Read the complete [N6/A100](results/roofline/n6_vs_a100/REPORT.md) and
[N5/B200](results/roofline/n5_vs_b200/REPORT.md) reports before quoting a row.

## What is implemented—and what is not

| Evidence layer | Present in the repository | Claim boundary |
|---|---|---|
| Model and architecture analysis | Checked traffic, iso-node, area-constrained, NoC, routing, cost, and sensitivity studies | Deterministic model output; not measured hardware |
| Compiler and runtime | Canonical model ingestion, backend-neutral IR, ABI 3.0 deployments, independent verification, functional and cycle devices | Bounded workloads and declared token-agreement horizons; not unrestricted model correctness |
| Digital implementation | Synthesizable public-reference RTL, formal/static/simulation/fault campaigns, and open-library implementation proxies | Qualified blocks and correlated deployments only; not a complete target chip or wafer |
| Circuit and physical methods | SKY130A and IHP controlled-via ROM slices, extracted simulations, and predictive/open-library routed blocks | Local methodology evidence; not leading-node ROM density, yield, or product signoff |
| Product silicon | **Not present** | No tapeout, fabricated OpenTallas device, package, full-chip P&R, foundry DRC/LVS, or silicon benchmark |

The [evidence ladder](docs/assets/README.md) defines how conceptual diagrams,
simulated results, routed geometry, and extracted circuits may be interpreted.
Functional, cycle, RTL, synthesis, place-and-route, SPICE, published, measured,
and assumed evidence are intentionally not interchangeable.

## Start exploring

| If you want to… | Start here |
|---|---|
| Understand the idea without hardware background | [OpenTallas in plain language](docs/OVERVIEW.md) |
| See every document by topic and authority | [Documentation hub](docs/README.md) |
| Audit the performance comparison | [Methodology](docs/METHODOLOGY.md), [assumptions](docs/ASSUMPTIONS.md), and [sources](docs/SOURCES.md) |
| Inspect the current executable program | [ABI 3.0 program report](docs/ABI3_PROGRAM_REPORT.md) and [compiler guide](compiler/README.md) |
| Implement against the contract | [Specification index](spec/README.md), [wire format](docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md), and [operator conventions](docs/TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md) |
| Review digital hardware evidence | [RTL inventory](rtl/README.md) and [RTL result reports](results/rtl/) |
| Review ROM circuit evidence | [SPICE guide](spice/README.md) and [physical methodology](docs/ROM_PHYSICAL_METHODOLOGY.md) |
| Track active work | [Unified execution checklist](docs/UNIFIED_EXECUTION_CHECKLIST.md) |

## Quick start

The core Python analyses and tests run on a CPU workstation with Python 3.10 or
newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[test]"

make model-traffic
make spec-check
make test
```

Rebuild the headline analytical studies and verify prose-to-artifact figure
links with:

```bash
make iso-node
make roofline
make check-figures
```

The complete `make verify` flow additionally needs RTL synthesis/simulation and
circuit tools. The optional extracted-layout campaigns require pinned SKY130A
and IHP SG13G2 PDK/tool installations; see [spice/README.md](spice/README.md).
Model profiling reads checkpoint metadata with range requests and does not
download full checkpoints by default.

## Repository map

| Path | Purpose |
|---|---|
| [`src/opentallas/`](src/opentallas/) | Analytical architecture and performance models |
| [`compiler/`](compiler/) | Model ingestion, canonical IR, ABI lowering, and deployment construction |
| [`runtime/`](runtime/) | Independent checks, functional device, cycle model, and reference numerics |
| [`spec/`](spec/) | Governed system, microarchitecture, interface, numeric, RAS, firmware, and verification contracts |
| [`rtl/`](rtl/) | Public-reference SystemVerilog, benches, formal harnesses, and campaigns |
| [`spice/`](spice/) and [`physical/`](physical/) | Circuit and physical-methodology vehicles |
| [`configs/`](configs/) | Explicit model, hardware, benchmark, and PDK inputs |
| [`results/`](results/) | Generated, reviewable evidence artifacts and reports |
| [`docs/`](docs/) | Orientation, methodology, decisions, evidence notes, plans, and status |
| [`tests/`](tests/) | Unit, differential, integration, ABI, runtime, and simulation tests |
| [`tools/`](tools/) | Reproduction, checking, reporting, and campaign entry points |

## Contributing

OpenTallas welcomes changes that make an assumption more explicit, a result more
reproducible, an implementation more complete, or a claim easier to audit. Read
[CONTRIBUTING.md](CONTRIBUTING.md) before changing a specification, generated
report, evidence grade, or headline figure. New documentation should be added to
the [documentation hub](docs/README.md), and active plans/checklists should not be
renamed or moved without coordinating with their current owners.

The most valuable contribution is often not a larger number. It is a tighter
boundary between what the repository demonstrates, what it models, and what
still has to be measured in silicon.
