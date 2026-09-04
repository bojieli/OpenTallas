# DeepSeek-V4 ROM array target: implementation and evaluation plan

**Status:** proposed delivery plan, not implemented evidence

**Issued:** 2026-09-03 UTC

**Targets:** TA-DS-ROM-ARRAY-FLASH (DeepSeek-V4-Flash-0731) and
TA-DS-ROM-ARRAY-PRO (DeepSeek-V4-Pro-0813)

**Physical topology:** N identical reticle-class mask-ROM accelerator chips on
the same NVLink-class external fabric that TA-DS-HBM already uses. No wafer,
no reticle stitching, no distributed-HBM-around-a-wafer package.

**Authority:** this document organizes work and acceptance gates for a fifth
and sixth product target. It amends
[`FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md`](FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md)
section 3 and
[ADR-003 section 3.3](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md#33-mandatory-physical-scale-profiles),
and it does not retire, weaken, or replace
[`DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md).
Nothing here promotes planned behavior into implemented evidence.

---

## 1. Purpose: the controlled experiment the program does not yet have

The current product matrix changes two variables at once on the DeepSeek row:

| | HBM weights | ROM weights |
|---|---|---|
| Qwen3-8B | one chip (TA-QW-HBM) | one chip (TA-QW-ROM) |
| DeepSeek-V4-Flash | **32-node array** over NVLink-class fabric (TA-DS-HBM) | **one wafer** over a stitched mesh (TA-DS-ROM) |

When the ROM wafer beats the HBM cluster, the result cannot say how much came
from the weight tier and how much from the packaging, because both moved.
This plan adds the missing cells:

| | HBM weights | ROM weights, array | ROM weights, wafer |
|---|---|---|---|
| DeepSeek-V4-Flash | 32 nodes, NVLink-class | **32 nodes, NVLink-class** | 1 wafer, stitched mesh |
| DeepSeek-V4-Pro | **N nodes, two-level fabric (TA-DS-HBM-PRO, new)** | **N nodes, two-level fabric (TA-DS-ROM-ARRAY-PRO, new)** | (not a current target) |

Two comparisons then become controlled:

- **ROM-array-32 versus HBM-cluster-32** holds node count, fabric, topology
  class, expert ownership, and link plan fixed. Only where the weight bytes
  live differs. This is the storage-class thesis of W11.1, extended from Qwen
  to DeepSeek at the same scale on both sides.
- **ROM-wafer versus ROM-array-32** holds the model, the ROM tile, and the
  weight tier fixed. Only the packaging and fabric differ. This is the
  question `WAFER_VERSUS_ARRAY_LATENCY.md` answers analytically and that no
  executed artifact answers today.
- **ROM-array-Pro versus HBM-cluster-Pro** repeats the first comparison at
  the scale where the array is the only ROM topology with a packaging path.
  The HBM/GPU side of Pro exists only analytically today: the iso-node studies
  carry Pro comparators at every context and batch, the roofline carries Pro
  GPU designs at 1,000,000 tokens only, and no compiled deployment, functional
  execution, cycle result, or oracle exists for Pro on the HBM lane. This plan
  builds that lane (section 3.3) so the Pro array is compared with an
  executed comparator, not a projected one.

Every one of these comparisons is read at **iso-area**. That is the
repository's governing rule for the analytical studies, and section 3.5 makes
it binding on the executed targets, where today no area is recorded at all.

Three facts from the executable roofline motivate the target rather than
merely permit it. All are read from
`results/roofline/n5_vs_b200/analytical.json`, and each is an analytical
result, not silicon:

1. The report's own selection rule already picks an array for Flash at 200K:
   `ROM-N5-native-SRAMKV-array-hybrid-x30` accepts at 107.5 tok/s per
   1,000 mm² and the wafer stops at 104.9. The program mandates by fiat the
   topology its own model declines.
2. Session capacity favors the array at every batch, because HBM beachfront
   scales with die count and only with the square root of one wafer's area.
   At one wafer of silicon, Flash at 200K: `HBMKV-wafer-tensor-x1` holds 630
   resident sessions; `HBMKV-array-hybrid-x62` holds 4,543. At batch 64 the
   wafer binds on `kv_read`; the array binds on `weight_read`.
3. The array meets sub-millisecond per-token latency without a wafer:
   0.38 ms/token for the 30-die design at batch 1. The wafer's 0.21 ms is a
   real 1.8x, not the difference between possible and impossible.

A fourth motivation is external. Wafer-scale silicon with HBM attached is a
TSMC SoW-X roadmap item now targeted at 2029, having slipped from 2027; no
shipping wafer-scale product carries HBM. Every component the array needs
exists in production packaging today. The array is the target whose physical
gates can be closed against components that exist.

**What this plan does not claim.** It does not claim the array is better. The
same roofline gives the wafer 1.8x to 3.8x the per-user rate of the array at
equal area, and at batch 64 the array's rate falls to 2.65 ms/token against the
wafer's 0.70 ms. The plan's product is a *reported crossover from executed
artifacts*, which is what the retracted section of
`WAFER_VERSUS_ARRAY_LATENCY.md` said the answer should be.

## 2. Inventory: what exists, what is reused, what is new

The array target is a composition of two existing lanes, not a new design.

| Layer | Exists today | Reused by the array | New for the array |
|---|---|---|---|
| Analytical roofline | `tools/run_roofline_studies.py` emits `array-{pipeline,tensor,hybrid}` designs for both models via `FabricPlan(kind="array")` | The design generator, iso-area rule, frontier, and `link_latency_sensitivity` | Array coverage at every context and a device-count ladder (section 4.1) |
| Neutral IR | `build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json`, graph `9ef6c3248d23` | Unchanged for Flash | Pro IR (section 9) |
| ROM lowering core | `compiler/backends/rom/common/{program,image,inverse,check}.py` (8,228 + 1,046 + 660 + 2,759 lines) | `RomLowering`, region planning, image emission, inverse proof, repair map | Nothing in the core; one new product module |
| ROM product backend | `compiler/backends/rom/deepseek_v4.py` (732 lines): `_WaferPlacer`, `_wafer_topology_factory`, `_wafer_link_plan_factory`, `deepseek_v4_rom_capability` | Layout policy, numeric contracts, feature bits, `RomTargetPolicy` shape | `compiler/backends/rom/deepseek_v4_array.py`: node-aware placer, cluster topology factory, node-scoped link plan (section 6) |
| HBM cluster backend | `compiler/backends/hbm_sram/{capability,plan,lower,check}.py`; `capability.py` builds the cluster record from a `node_count` argument and names `limits.max_nodes` a legal profile variant | The whole backend for the Pro HBM comparator lane | A `cluster-N` profile; removal of the 32-node assumptions at `plan.py` line 52, line 593, and line 4427 (section 3.3) |
| Cluster topology semantics | `compiler/backends/hbm_sram/plan.py` `TopologyPlan`; the exact 32-chip invariants of `DEEPSEEK_200K_SIMULATOR_EXECUTION_DESIGN.md` section 7 | Expert ownership (eight consecutive experts per node), A28 node segments, LINK-only cross-node data path, 37 communication descriptors | Applied to ROM-resident weights instead of HBM-resident weights |
| ABI 3.0 capability | `configs/hardware/abi3_capability/{rom_deepseek_v4,hbm_sram_cluster_32}.json`; `runtime/abi3/capability.py` validates `CLUSTER_32` and `WAFER_LOGICAL_DEVICE` | `TopologyClass.CLUSTER_32`, `Feature.INTER_CHIP_ENDPOINT`, `max_nodes` | `rom_deepseek_v4_array_32.json`; later `TopologyClass.CLUSTER_N` for Pro (section 5) |
| Functional simulator | `runtime/sim/device.py` already instantiates `node_count` node-private memories and per-node counters for the HBM cluster | Multi-node device, LINK engine, token-step fence, counters | The combination `StorageClass.ROM` with `node_count > 1` (section 7) |
| Independent schedule checker | `compiler/backends/rom/common/check.py`; `make abi3-rom-schedule-check`; cases in `results/abi3/rom_schedule_checks.json` | The checker | A third case, `deepseek-v4-flash-rom-array-32`, and node-scoped participant reconstruction |
| Cycle model | `runtime/cycle/fabric.py` `ClusterFabric` (link serialisation, switch levels, credits, retry) and `WaferFabric`; `runtime/cycle/machine.py` `ClusterFabricParams` | `ClusterFabric` unchanged for 32 nodes | `configs/hardware/abi3_cost_rom_array_v1.json`; two-level cluster parameters for Pro |
| RTL | `rtl/ot_rom_wrapper.sv`, `rtl/ot_rom_macro_periphery.sv`, `rtl/abi3/ot_a3_link_endpoint.sv`, `ot_a3_link_node.sv`, `ot_a3_collective_engine.sv`; `rtl/ot_stage_link_{endpoint,tx,rx}.sv` | ROM service block and the inter-chip link endpoint the HBM chip already carries | Elaboration profile that instantiates ROM service plus the inter-chip endpoint in one die |
| Physical | ASAP7 and SKY130 views of tensor/vector/reduction blocks (`ABI3_PHYSICAL_VIEWS.md`); IHP ROM bitcell, read-energy, and macro chain (`ROM_PHYSICAL_METHODOLOGY.md`) | Per-die closure methodology | Per-die assembly with a link PHY boundary; no stitching, no wafer clock/PDN |
| Comparison | `configs/abi3/comparison_contracts/deepseek_v4_rom_wafer_vs_hbm_cluster_32_v1.json`; `tools/build_comparison_report.py` | Contract schema, oracle, workload pins | Two sibling contracts (section 11) |
| Pro model | `configs/models/deepseek-v4-pro-0813.json`, `data/inventory/deepseek-v4-pro-0813.json` (analytical only) | Byte inventory | Everything from checkpoint lock to oracle (section 9) |

The reuse column is the argument that this is cheap relative to the program.
The new column is the work.

## 3. Target definition

### 3.1 TA-DS-ROM-ARRAY-FLASH

| Field | Value | Source |
|---|---|---|
| Model | DeepSeek-V4-Flash-0731, graph `9ef6c3248d23`, 156,015,698,140 bound weight bytes | `docs/PROGRAM_STATUS.md` |
| Node count | **exactly 32** | equals TA-DS-HBM; inside the roofline's emitted 29–32 range |
| Die area per node | graded value from DRA-PHY10; until then 815 mm² reticle-class, labeled assumed for this use | section 3.5 |
| Node | one reticle-class die: mask ROM for its weight shard, SRAM activation/index/accumulator service, node-local HBM for mutable KV, compressed-KV, window, and compressor buffers, one inter-chip fabric endpoint | ADR-003 sections 3.3 and 8.8 |
| Expert ownership | global expert `e` owned by node `floor(e / 8)`; eight consecutive experts per node | `DEEPSEEK_200K_SIMULATOR_EXECUTION_DESIGN.md` section 7, invariant 2 |
| Dense/shared weights | placed by the array backend; the controlled variant inherits TA-DS-HBM's shard axis so the two sides move the same activation bytes | `compiler/backends/hbm_sram/plan.py` line 52 |
| Fabric | the modeled NVLink-class switched fabric of TA-DS-HBM: `TopologyClass.CLUSTER_32`, `ClusterFabric`, cost-table family `fabric.cluster.*` | `runtime/cycle/fabric.py` |
| Topology class | `CLUSTER_32` (value 1), unchanged ABI | section 5 |
| Mandatory workload | `TA-DS-CTX-200K-1`, 200,000 prompt tokens, greedy argmax, first EOS or 256 tokens | the DeepSeek workload contract |
| KV per session at 200K | 1,381,646,336 B | `results/roofline/n5_vs_b200/analytical.json` `model_summaries` |

Choosing 32 is not a coincidence to be tolerated; it is the design. At 32 the
array target and the HBM cluster target share a topology class, a capability
validation branch, a fabric model, a cost-table family, an expert-ownership
rule, and the 37-descriptor link plan. The only admitted difference is
`StorageClass.ROM` on the weight objects. That is the sharpest experiment the
ABI can express without an amendment.

### 3.2 TA-DS-ROM-ARRAY-PRO

| Field | Value | Source |
|---|---|---|
| Model | DeepSeek-V4-Pro-0813, revision `72e1d3230f6c`, 892,727,580,904 checkpoint bytes, 149,782 tensors, 66 shards, 61 layers, 384 experts, 6 per token, hidden 7,168, two attention groups | `configs/models/deepseek-v4-pro-0813.json`, `data/inventory/deepseek-v4-pro-0813.json` |
| Ordinary-decode bytes | 26.822 GB dense, 822.054 GB routed | `docs/ASSUMPTIONS.md` section 2 |
| Node count | **to be derived**, in the roofline's emitted 155–167 range; 384 experts divide evenly into 48, 64, 96, 128, or 192 nodes, and the plan's working assumption is 192 nodes of two experts each, or 128 of three, chosen at DRA-N8 by capacity | section 6.4 |
| Die area per node | graded value from DRA-PHY10; until then 815 mm², labeled assumed | section 3.5 |
| Fabric | two-level: NVLink-class domains of `link_domain_size` nodes, an InfiniBand-NDR-class or scale-out inter-domain fabric | `configs/hardware/technology.json` `links.nvlink5`, `links.infiniband_ndr`; the roofline's `hybrid` plan |
| Topology class | `CLUSTER_N` (proposed value 3), an ABI amendment | section 5 |
| Mandatory workload | 200,000 prompt tokens as for Flash; 1,000,000 is the roofline context and is a stretch gate, not the mandatory one | section 9 |
| KV per session | **1,977,611,264 B at 200K**; 9,856,011,264 B at 1M | `results/roofline/context_ladder/n5_vs_b200/pro-200k/analytical.json` and `results/roofline/n5_vs_b200/analytical.json`, both `model_summaries[model=DeepSeek-V4-Pro-0813].kv_storage_bytes_per_user`. The row previously gave the 1M figure under the 200K label: the primary study runs Pro at 1,000,000 tokens and 200K is a context-ladder rung, so both numbers live under `model_summaries` in different trees |

Pro is the reason the array target matters beyond a controlled experiment. At
4 GiB of ROM per reticle field the wafer backend's own geometry
(`wafer_geometry()` in `compiler/backends/rom/deepseek_v4.py`) needs about
198 reticle fields for Pro's ordinary-decode bytes, and one wafer stitches 48.
Pro on the wafer topology is a four-wafer machine before compute, KV, or
beachfront are added; the roofline's own Pro recommendation is three wafers
with an inter-wafer link graded `assumed`. Pro on the array topology is a large
cluster of a die that exists. Neither is cheap. Only one has a packaging path
that does not wait for 2029.

### 3.3 TA-DS-HBM-PRO: the executed comparator the Pro array needs

| Field | Value | Source |
|---|---|---|
| Chip | the shared HBM/SRAM accelerator chip of TA-QW-HBM and TA-DS-HBM, unchanged netlist | master plan section 3: a model "may not select a different chip elaboration or netlist" |
| Per-node HBM | 103,079,215,104 B (96 GiB), eight channels | `configs/hardware/abi3_capability/hbm_sram_cluster_32.json` |
| Node count, primary | **derived by iso-area** (section 3.5): the node count at which N × A_hbm equals the Pro ROM array's silicon within 2%; at equal die area that is the array's own node count, and the HBM side then under-uses per-node capacity by design | section 3.5; fixed at DRA-N8 |
| Node count, capacity-optimal | **48**: 384 experts at eight consecutive experts per node, the same ownership rule as Flash; 17.1 GB of routed weights per node plus the dense shard; about five resident 200K sessions per node at 0.90 capacity utilisation. This is the HBM side's own best machine at any area and is reported beside the iso-area row, never as the headline | derived from the released byte inventory |
| Die area per node | graded value from DRA-PHY10; until then 815 mm², labeled assumed | section 3.5 |
| Fabric | two-level, as for the Pro array: 48 nodes exceed one NVLink-class domain | section 5.2 |
| Topology class | `CLUSTER_N` | section 5 |
| Mandatory workload | `TA-DSP-CTX-200K-1` | section 9 |

What exists for Pro on the HBM/GPU side today, by layer:

| Layer | Pro HBM/GPU coverage today |
|---|---|
| Iso-node analytical (`results/iso-node/*`) | A100 and B300 cluster comparators at 8,192 / 32,768 / 200,000 / 1,000,000 tokens and batch 1 / 8 / 32 / 64 |
| Roofline (`results/roofline/n5_vs_b200`) | `b200_sxm-*` designs at 1,000,000 tokens only |
| Compiled ABI 3.0 deployment | none; `tools/build_hbm_sram_deployment.py --profile` admits `single-chip` and `cluster-32` only |
| Functional execution, cycle model, RTL, governed comparison | none |

The HBM backend is closer to N-node than its name suggests.
`compiler/backends/hbm_sram/capability.py` builds the cluster capability from
a `node_count` argument (`limits["max_nodes"] = node_count`) and lists
`limits.max_nodes` in `PROFILE_VARIANT_FIELDS`. The 32-node assumption lives
in three places WP-M must generalize: `cluster32_capability` and the
`PROFILES` registry; the "exact 32-node deployment identity" docstring and
shard-axis rule in `plan.py`; and the 32-node tile-row projection at
`plan.py` line 4427. The functional simulator, cycle fabric, and verifier
already take the node count from the capability.

### 3.4 What is mandatory and what is not

The array boundary is mandatory in the same sense the wafer boundary is: the
critical model path runs on the modeled inter-chip fabric issued by the
authenticated device program, not host paging, host sequencing, or a shared
memory abstraction. The exact 32-chip invariants of the execution design's
section 7 apply verbatim to the Flash array, with "HBM" read as "node-local
memory" in invariant 1 and the weight objects placed in ROM.

The array target does **not** require:

- reticle stitching, wafer clock/reset/PDN, or a wafer thermal model;
- distributed HBM attachment around a wafer boundary;
- `Feature.WAFER_ENDPOINT` or `WaferFabric`;
- a reticle/tile coordinate table; the placement resource is the node.

It does require everything the HBM cluster requires: a versioned
node/switch/link topology, node-local object mapping, deterministic shard and
expert ownership, bounded credits, explicit completion, fail-stop on
unrecoverable link or node failure, and one coordinated run namespace.

### 3.5 Iso-area is the rule every comparison is read at

The governing comparison rule of this repository is iso-area: a ROM design and
its comparator are read at the same silicon area, and the comparator's device
count is *derived* from that area rather than chosen
(`ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` section 2;
`tools/run_roofline_studies.py` `_iso_area_gpu_counts`). The roofline applies
it to every recommendation: "iso-area, at the area the rule chose", with the
area ratio matched within 2% or a granularity correction stated. This plan
makes the same rule binding on the executed targets, which today it is not.
No ABI 3.0 capability, cost table, or comparison artifact carries a die area;
`results/abi3/comparison_deepseek_rom_vs_hbm.json` reports `topology_cost` as
node counts only, and its `claim_boundary` says `silicon: false`.

The rule, stated so it is checkable:

1. **Area is accelerator die area per node times node count.** It includes
   ROM, logic, SRAM, the HBM PHY, and the fabric endpoint. It excludes HBM
   stacks, package, switch silicon, and board, which are reported alongside
   and are never in the denominator. This is the roofline's convention
   (`silicon_area_mm2`, `area_fractions.hbm_phy`), and both sides receive the
   same beachfront rule for HBM stack count, so both have the same
   KV-bandwidth ceiling per die.
2. **The comparator's node count is derived from area.** For a ROM target of
   N_rom nodes at A_rom mm² each, the iso-area HBM comparator has
   N_hbm = round(N_rom × A_rom / A_hbm) nodes of the shared chip at A_hbm mm²
   each. The area ratio is reported and must lie within 2% or carry a stated
   granularity correction, exactly as the roofline reports it.
3. **Every quantity is read at that area:** per-user tok/s and executed TPOT,
   aggregate tok/s, resident sessions, W and W/mm², J/token, and the
   provenance class of each. The iso-area row is the headline. The
   comparator's own best machine at any area is quoted beside it so the
   iso-area row is not the only comparison on the page, which is the
   roofline's existing practice.
4. **Each target's per-node die area is a graded value.** Until DRA-PHY10
   produces one from a physical view, both dies carry the reticle-class
   figure of `configs/hardware/technology.json` `reticle.area_mm2` (815 mm²,
   graded published from the Taalas HC1 anchor), labeled assumed for this
   use, and every iso-area comparison made before then says so on the
   artifact.
5. **Iso-area is not iso-cost.** A ROM die is a logic wafer; an HBM die plus
   its stacks is not. Partial TCO remains the iso-node study's separate
   quantity (`ASSUMPTIONS.md` section 7), and no iso-area ratio is reported
   as a cost ratio.

Consequences for the targets above:

- **Flash.** 32 ROM nodes versus 32 HBM nodes is iso-area only if
  A_rom ≈ A_hbm. If the physical views put the two dies at different areas,
  the iso-area HBM comparator has a different node count, and the plan
  reports both the iso-area pair and the equal-node controlled pair, each
  labeled for what it holds fixed.
- **Pro.** The primary HBM comparator is sized by area, not by capacity. At
  equal die area that is the ROM array's own node count. The 48-node
  capacity-optimal cluster is the HBM side's best machine at any area and is
  reported beside the iso-area row.
- **Wafer versus array.** One wafer is 46,225 mm² of silicon; its iso-area
  array comparator is about 57 reticle-class dies, which is how
  `WAFER_VERSUS_ARRAY_LATENCY.md` already reads the crossover.

## 4. The evaluation stack: five layers, each with its own gate

A number reported for the array target names which layer produced it. Layers
do not substitute for each other; the roofline is a projection, the cycle
model is a model over authenticated artifacts, and only a token-correct
functional execution can carry a TPOT (master plan section 11.1).

### 4.1 L0: analytical roofline

**Exists.** `tools/run_roofline_studies.py` already emits array designs for
both models and reports "Array or wafer: the crossover, reported rather than
assumed" in `results/roofline/n5_vs_b200/REPORT.md`.

**Gaps the report itself names.** The array class "is sampled only at the
device counts each floorplan's own sizing sweep chose: `ROM_AREA_LADDER` is
applied where `plan.kind == "wafer"` and nowhere else." The emitted array
counts are 29–32 for Flash and 155–167 for Pro. Flash is run only at 200K
context and Pro only at 1,000,000; `ASSUMPTIONS.md` states both authoritative
studies run 8,192, 32,768, 200,000, and 1,000,000.

**DRA-R1 deliverable.**

1. Apply the area ladder to `plan.kind == "array"` so the array class is
   sampled on a device-count ladder (for Flash: 30, 32, 40, 48, 56, 64; for
   Pro: 128, 160, 192, 256, 320, 384) rather than only where a sizing sweep
   landed.
2. Run both models at all four contexts in both studies (`n5_vs_b200`,
   `n6_vs_a100`). For Pro this adds GPU comparator designs at 8,192, 32,768,
   and 200,000 tokens, which the roofline does not emit today, so that the
   Pro HBM lane of section 3.3 has an L0 projection at its mandatory context.
3. Add an `array-32-controlled` design for Flash that is forced to 32 nodes,
   expert-parallel ownership, and the exact link plan of `b200_sxm-x32`'s own
   topology choice, so the L0 projection matches the L1–L4 machine rather
   than the free optimum.
4. Publish per-batch tables for the three classes (GPU, ROM array, ROM wafer)
   at iso-area, with resident sessions on every row, per the report's own
   "read the resident-session row before the ratio row" rule.
5. Extend `link_latency_sensitivity` to the array's two link grades separately
   (`nvlink5` `derived`, `infiniband_ndr` `measured`), so the Pro two-level
   fabric's uncertainty is reported apart from the ROM side's.

Regenerate with `make roofline`. Every figure the plan cites from this layer
must carry a provenance annotation in the grammar of
`tools/check_prose_figures.py`, resolvable against the producing artifact.

### 4.2 L1: compiled deployment and its certificates

**Deliverable.** `build/abi3/deepseek-v4-flash-rom-array-32/` produced by
`tools/build_rom_deployment.py deepseek-v4-flash-array`, with `--verify
--inverse --determinism`, and an independent schedule certificate case in
`results/abi3/rom_schedule_checks.json`.

**Gate DRA-P3.** Every included tensor inverse-reconstructs bit-exactly from
the 32 node images; every routed expert's ROM bytes live on exactly its owning
node; node ROM, SRAM, and HBM capacity are legal; the link plan is complete,
disjoint, and digest-bound; zero `STATE` resources; the certificate is
byte-identical on a second clean build.

### 4.3 L2: functional execution

**Deliverable.** Artifact-only execution through `runtime/sim` on the
`TA-DS-*` workload ladder: `TA-DS-CTX-129-1`, `-160-1`, `-256-1`, `-1K-1`,
`-8K-1`, `-32K-1`, `-128K-1`, then `TA-DS-CTX-200K-1`; `TA-DS-CHAT-1`;
`TA-DS-AGENT-1`.

**Gate DRA-S4.** Oracle-identical tokens over each workload's compared span
under the correctness gates of master plan section 11; per-node counters
reconcile to cluster counters by the additive rule of invariant 7; the token
stream agrees with the HBM cluster's token stream over the same span, and any
divergence is recorded with its index and its `selection.tie_multiplicity`
mechanism as W11.1 does for Qwen.

### 4.4 L3: cycle model

**Deliverable.** `runtime/cycle/model.py` run over the same deployment under
`abi3_cost_rom_array_v1.json`, producing
`results/abi3/deepseek_v4_flash_rom_array_32_*_cycle.json`.

**Gate DRA-Y5.** Functional == cycle on every architectural counter; complete
schedule audit; provenance counts (`assumed` / `datasheet` /
`characterized`) published on the artifact; `assert_no_zero_latency_global_operations`
passes; every collective executed as an algorithm over link resources, not a
closed-form penalty.

### 4.5 L4: RTL correlation

**Deliverable.** The shipped-deployment RTL profile elaborated with ROM
service plus the inter-chip endpoint, driven by generated ABI 3.0 vectors for
one node's program, correlated with the functional device at the declared
request shape.

**Gate DRA-R6.** Control-plane and counter correlation under injected link
faults (CRC error, duplicate packet, retry exhaustion, credit loss) each
producing the declared fail-stop.

### 4.6 L5: physical view

**Deliverable.** Per-die closure in the ASAP7 predictive view and SKY130
implementation view of the blocks the die actually instantiates, plus a
sourced package and board boundary for the link PHY and node-local HBM.

**Gate DRA-PHY10.** Section 10.

## 5. Topology class: reuse for Flash, amend for Pro

`runtime/abi3/constants.py` defines three classes: `SINGLE_CHIP = 0`,
`CLUSTER_32 = 1`, `WAFER_LOGICAL_DEVICE = 2`. `runtime/abi3/capability.py`
validates `CLUSTER_32` by requiring `max_nodes >= 32` and
`Feature.INTER_CHIP_ENDPOINT`; `runtime/abi3/verifier.py` checks that the
described topology's node count equals the capability's `max_nodes`;
`runtime/cycle/fabric.py` `ClusterFabric` sets `topology_class =
TopologyClass.CLUSTER_32`.

### 5.1 Flash: `CLUSTER_32`, no ABI change

The Flash array declares `topology_class = 1`, `max_nodes = 32`,
`Feature.INTER_CHIP_ENDPOINT`, and `StorageClass.ROM` on weight objects.
Nothing in the capability validator, the verifier, or the cycle fabric
distinguishes a ROM-resident cluster node from an HBM-resident one, and that
is exactly the property the controlled comparison needs. **DRA-A0 must
confirm by test that no code path silently assumes a `CLUSTER_32` node's
weights are in HBM** (section 13, WP-A).

### 5.2 Pro: `CLUSTER_N`, an ADR-003 amendment

Pro does not fit 32 nodes. Its ordinary-decode bytes at the wafer backend's
4 GiB per reticle field need about 198 fields; at the roofline's 556 mm² of
ROM per 815 mm² die it needs 155–167 dies. Either way, `max_nodes = 32` is
wrong by five to six times.

The amendment adds `TopologyClass.CLUSTER_N = 3`: a conventional-chip cluster
whose node count is a capability value, not an ABI constant. Its contract is
the 32-node contract of ADR-003 section 3.3 with two additions:

- a two-level fabric: `fabric.cluster.domain_size` nodes per high-bandwidth
  domain, `fabric.cluster.domains`, an inter-domain link class with its own
  bytes-per-cycle, hop latency, switch levels, and radix; `ClusterFabric`
  already carries `switch_levels` and `switch_radix`, and the amendment makes
  the second level a distinct link resource rather than a deeper switch;
- expert ownership generalized to `experts_per_node = experts / nodes` with
  the divisibility requirement stated in the capability.

Both Pro lanes need the amendment: the Pro ROM array at 155–198 nodes and the
Pro HBM cluster at 48. Note that `Capability.validate` today checks only
`max_nodes >= 32` for `CLUSTER_32`, so a 48-node capability would pass the
validator under the wrong class name. The storage-neutrality test of WP-A
must also assert that a `CLUSTER_32` capability declares exactly 32 nodes,
so that loophole is closed before `CLUSTER_N` opens the honest path.

The amendment is written as a numbered section of
`TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md` in the style of A14 and
A21, reviewed under the master plan's section 6.3 contract-change rule, and
does not land until the Flash array (which needs none of it) has closed
DRA-S4. Sequencing the amendment behind Flash keeps the controlled experiment
free of ABI churn.

## 6. Compiler backend: `compiler/backends/rom/deepseek_v4_array.py`

The module mirrors `deepseek_v4.py` in shape and reuses its layout policy,
numeric contracts, and `RomTargetPolicy`. Three factories change.

### 6.1 Placer: `_ArrayPlacer` replaces `_WaferPlacer`

The wafer placer packs regions into tiles and tiles into reticles, advancing a
`RomCoordinate(node_id=0, reticle, tile, bank, ...)`. The array placer is
node-first:

- a routed expert region is placed on its owning node, `floor(e / experts_per_node)`,
  and never split across nodes;
- dense, shared, attention, indexer, mHC, embedding, and vocabulary regions are
  placed by the declared shard axis (the controlled variant inherits
  TA-DS-HBM's), one shard per node, so that the same activation bytes cross
  the fabric on both sides of the comparison;
- within a node, regions pack into banks with the existing alignment and
  repair-map machinery of `compiler/backends/rom/common/image.py`;
- `RomCoordinate.reticle` and `.tile` are both zero for every shard; the node
  is the placement resource.

### 6.2 Topology factory: `_array_topology_factory`

Emits `builder.topology(topology_class=CLUSTER_32, node_count=32, ...)` with
`reticle_count = tiles_per_reticle = 0` (the verifier's `legacy_empty`
branch already admits this shape for a cluster), `route_group_count` equal to
the NVLink domain count, link counts from `links_per_node`, and the
active-resource, quarantine, route-table, and health digests computed over the
node images rather than a tile coordinate table.

### 6.3 Link plan: `_array_link_plan_factory`

The wafer plan issues five `TILE`-scoped collectives per compressed layer body
(activation multicast, sparse-index gather, expert dispatch, expert reduction,
layer barrier) plus a residual unicast. The array plan issues the same six
services `NODE`-scoped, and for the controlled variant it must reproduce the
HBM cluster's descriptor census exactly: four expert scatters, seven sparse-KV
all-gathers, 21 activation all-gathers, four expert all-reduces, and one final
synchronization barrier (execution design section 7, invariant 8).
`_participant_count` in `compiler/backends/rom/common/program.py` already
derives `NODE -> node_count`; no change to the core is needed.

**Proof obligation.** A test asserts that the array deployment's
`COMMUNICATION` descriptor multiset equals the HBM cluster deployment's
multiset on `(collective_op, participant_scope, participant_count,
route_class, byte_extent)`. If it does not, the comparison is not controlled
and the difference must be named before either side is timed.

### 6.4 Capacity and the density reconciliation gate

Two models in this repository disagree on how many reticle-class dies Flash
needs:

| Model | ROM area per die | Density | Dies for 156.0 GB |
|---|---:|---:|---:|
| `wafer_geometry()` in the ABI3 wafer backend | 354.2 mm² usable of 858 mm² (41.3%) | 12.13 MB/mm² required | 36.3 fields of 4 GiB |
| `run_roofline_studies.py`, N5 | 556.0 mm² of 815 mm² (68.2%) | about 8.8 MB/mm² effective | 30–32 dies |

The gap is about 15%, not a factor of two, and it is a difference of area
fraction and of density grade rather than a contradiction. It is nonetheless a
gate: **DRA-P3 derives the array's per-node ROM bytes from one graded density
and one graded area fraction, records both in the capability's `notes`, and
the roofline's `array-32-controlled` design is re-run with the same two
values.** A 32-node Flash array must fit at the chosen numbers, or the node
count changes and the controlled comparison is re-stated against a 32-node
HBM cluster at a declared node-count ratio. The plan does not paper over that
with a silent change to either model.

For Pro, the same derivation sets the node count at DRA-N8 from the released
822.054 GB of routed bytes plus 26.822 GB dense plus scale, padding, integrity,
and repair overhead, subject to the 384-expert divisibility rule.

### 6.5 Capability

`configs/hardware/abi3_capability/rom_deepseek_v4_array_32.json`: the
`hbm_sram_cluster_32.json` link and limits sections (`max_nodes: 32`,
`peers_per_node: 31`, `endpoints_per_node`, `bisection_links`, `chunk_bytes`,
`credit_bound`, `virtual_channels`, `retry_bound`) with the
`rom_deepseek_v4.json` engine lane mix and numeric contracts, a per-node `rom`
memory section, node-local `hbm` and `sram` sections, and
`technology_view: "rom_array_cluster_32_declared_v1"`. One source of truth: a
`PROFILES["rom-deepseek-v4-array-32"]` factory in the new module, checked by
`tools/publish_abi3_capabilities.py --check`.

## 7. Functional simulator and schedule checker

`runtime/sim/device.py` already builds `node_count` node-private
`DeviceMemory` instances, per-node counter sets, and the additive cluster
counter rule for `CLUSTER_32`. The array target exercises one combination that
has never run: `StorageClass.ROM` weight objects inside a multi-node device.

Work:

- confirm `DeviceMemory(node_id=k)` resolves ROM windows from node `k`'s
  authenticated image (A28 `node_segments` binds a distinct image per node for
  HBM; the same record must bind per-node ROM images);
- confirm the ROM read counters (`rom.bytes_read`) are attributed per node and
  sum by invariant 7;
- confirm `weight_cache.py` and any host-side decoded-weight cache
  (execution design WP-D) either bypass ROM or attribute their effect to the
  same architectural counters on both sides;
- add `deepseek-v4-flash-rom-array-32` to `DEFAULT_CASES` in
  `tools/check_rom_schedules.py` and teach
  `compiler/backends/rom/common/check.py` to reconstruct node-scoped
  participants and per-node bank placement without importing the producer.

Exit: the L2 gate of section 4.3.

## 8. Cycle model and cost table

`configs/hardware/abi3_cost_rom_array_v1.json` is derived from
`abi3_cost_cluster32_v2.json` (fabric, HBM, SRAM, engine parameters) with the
`rom.*` parameters of `abi3_cost_wafer_v2.json`. Every parameter carries its
provenance class; the first table will be almost entirely `assumed`, as the
cluster table is (124 assumed, 5 characterized on the shipped HBM artifact),
and the artifact says so.

For Pro, `ClusterFabricParams` grows `domain_size`, `domains`, and an
inter-domain link parameter set; `ClusterFabric.route()` selects the
inter-domain resource when `src // domain_size != dst // domain_size`.
The `hybrid` collective algorithms (intra-domain ring, inter-domain tree) are
executed over those resources, not priced in closed form, per the fabric
module's own rule.

## 9. Pro prerequisite track: topology-independent

Nothing below depends on the array. It is needed for Pro on any target, and it
is the largest single body of work in this plan. It is tracked separately so
that array work is neither blocked by it nor blamed for it.

| Step | Flash precedent | Pro work |
|---|---|---|
| Checkpoint source contract | `compiler/models/deepseek-v4-flash-0731/checkpoint_source.json`, 48 shards, 26 non-shard files | `compiler/models/deepseek-v4-pro-0813/`: 66 shards at revision `72e1d3230f6c`, byte-identical `config.json` and `inference_config.json` |
| Checkpoint lock | 166.9 GB streamed and locked outside Git, lock `30b3d073…` | 892.7 GB streamed and locked; requires a volume and a run window the plan must schedule |
| Tensor contract | `describe-deepseek-v4` expands 72,317 tensors from the byte-exact config | Adapter generalized over layer count (61), expert count (384), hidden (7,168), and two attention groups; expands 149,782 tensors and matches the header inventory |
| Graph contract | `describe-deepseek-v4-graph`, 2,136 nodes over 43 main plus three DSpark stages, 46 operator kinds | Same 46 kinds expected; the adapter must not hard-code 43, 256, 4096, or the three-group attention census |
| Neutral IR | `build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json` via `tools/build_deepseek_v4_kernel_ir_v3.py` | `build/ir-v3/deepseek-v4-pro-0813/kernel_ir.v3.json` |
| Workloads | `tools/build_deepseek_v4_workloads.py`, `TA-DS-*` ladder | `TA-DSP-*` ladder with the same prompts re-tokenized under Pro's tokenizer if it differs, else the same pins |
| External oracle | `tools/run_deepseek_v4_reference_oracle.py`, context ladder to 200K | The Pro oracle is a 892 GB model; the plan schedules it on the same GPU host as the Flash oracle and records wall time (Flash's 200K rung took 435 s) |
| KV model validation | `results/roofline/deepseek_v4_kv_model_validation.json` | `configs/models/deepseek-v4-pro-0813.json` states its attention entry sizes are "corrected by architectural analogy … NOT independently measured"; a Pro rung with `--measure-kv` retires that grade |

Gate DRA-PRO7 closes when the Pro IR exists, the Pro tensor contract matches
the pinned header inventory, the `TA-DSP-CTX-200K-1` workload is pinned, and
the Pro oracle has produced the 200K rung. It serves both Pro lanes; the HBM
cluster lane and the ROM array lane consume the same IR, workload, and
oracle.

## 10. Physical view

The array target's physical closure is per-die plus a sourced boundary. It is
easier than the wafer's in exactly the places the wafer plan lists as open
(stitching, wafer clock/power/reset, distributed-HBM package, on-wafer link)
and no easier anywhere else.

Per die, in both views (`ABI3_PHYSICAL_VIEWS.md` methodology):

- ROM service: the IHP bitcell → read-energy → macro chain of
  `ROM_PHYSICAL_METHODOLOGY.md`, projected to the target view with the
  `rom.cell_to_sram_cell_area_ratio` and `rom.array_efficiency` constants
  that document names, at the node's ROM bytes;
- tensor, vector, reduction blocks: existing ASAP7/SKY130 runs;
- attention, DMA, route, selection: the blocks `ABI3_PHYSICAL_VIEWS.md`
  lists as missing for W11.2; the array needs them no more and no less than
  the wafer does;
- inter-chip endpoint: `ot_a3_link_endpoint.sv` and `ot_a3_link_node.sv`
  synthesized and placed in-view; the SerDes PHY is a sourced boundary
  component with a datasheet grade.

Sourced boundary:

- node-local HBM stacks by count and generation from the beachfront rule in
  `roofline.py` `max_hbm_stacks_per_device` (five stacks at 0.60 edge
  utilisation on an 815 mm² die at 12 mm pitch);
- package and board: a CoWoS-class package per die and an NVLink-class
  switch tray, source-locked to public documents as ADR-003 section 3.3
  requires for envelopes;
- system power: N dies plus switches plus HBM, with the clocked-idle floor
  measured in `results/roofline/gpu_clocked_idle_floor.json` applied per
  die as the GPU comparator already receives it.

Gate DRA-PHY10 closes when a per-die area, power, and Fmax exist in each view
for every block the die instantiates, the cost table's `characterized` count
rises above the cluster table's five, and the array's assembly model (N dies,
package, switch, HBM, board) is published with every external value graded.

## 11. Comparison contracts

Two siblings of
`configs/abi3/comparison_contracts/deepseek_v4_rom_wafer_vs_hbm_cluster_32_v1.json`,
same schema `opentallas.abi3.comparison_contract.v1`:

- `deepseek_v4_rom_array_32_vs_hbm_cluster_32_v1.json` — the storage-class
  comparison. `topology_class` is 1 on both sides; `node_count` is 32 on both
  sides; `topology_cost` is reported as equal, which is the point.
- `deepseek_v4_rom_wafer_vs_rom_array_32_v1.json` — the packaging
  comparison. `storage_class` is ROM on both sides; `topology_cost` is 1 node
  of class 2 against 32 nodes of class 1 and is reported, never equalised.

Both bind the same workload (`TA-DS-CTX-200K-1`, digest `803f0c3a…`), the same
oracle, the same numeric profile, and the same technology-view policy
(`predictive_asap7_characterized_or_explicit_assumption_v1`). The existing
`tools/abi3_comparison_boundary.py` and
`tools/audit_abi3_asap7_comparison_readiness.py` gain the contracts and
refuse cross-view mixing exactly as they do today.

**Every contract gains area.** Per side: `node_count`,
`die_area_mm2_per_node` with its grade, and `silicon_area_mm2`; top-level:
`iso_area_ratio` and `iso_area_tolerance` (0.02). The comparison-contract
schema moves to `v2` for these fields, `tools/build_comparison_report.py`
refuses a contract whose ratio is outside tolerance unless a
`granularity_correction` is stated, and the produced artifact's
`claim_boundary` gains `iso_area: true|false` beside its existing `silicon`
flag. The Flash array-versus-HBM contract is the iso-area contract when the
two dies match in area; if DRA-PHY10 finds they do not, a
`deepseek_v4_rom_array_vs_hbm_cluster_iso_area_v1.json` is added with the
derived HBM node count, and the 32-versus-32 contract is retained as the
equal-node controlled pair.

Three Pro contracts are added at DRA-X10, in this order of authority:

- `deepseek_v4_pro_rom_array_vs_hbm_cluster_iso_area_v1.json` — **the
  headline.** The HBM cluster at the node count section 3.5 derives from the
  array's silicon; at equal die area that is the array's own node count, and
  the artifact records that the HBM side under-uses per-node capacity by
  design. Performance, resident sessions, power, and J/token are read here.
- `deepseek_v4_pro_rom_array_vs_hbm_cluster_capacity_optimal_v1.json` — the
  48-node cluster of section 3.3, the HBM side's own best machine at any
  area. `topology_cost` reports both node counts and both areas and, as the
  schema says, is "reported, never equalised". Quoted beside the headline,
  never as it.
- `deepseek_v4_pro_rom_array_vs_hbm_cluster_equal_n_v1.json` — only if the
  two dies differ in area, so that the storage-class reading at equal node
  count exists as it does for Flash. If the dies match, this is the iso-area
  contract and is not duplicated.

Until DRA-H8 closes, any Pro array number may be compared only with the
roofline's projected GPU comparator, in a column labeled projected, per
master plan section 11.1.

## 12. Milestones

| Gate | Outcome | Exit evidence |
|---|---|---|
| DRA-A0 | architecture amendment accepted | The iso-area convention of section 3.5 is frozen in master plan section 12; master plan section 3 and ADR-003 section 3.3 add the N-node ROM array as a fourth physical profile; the "mandatory wafer / not legal to replace" clauses in `DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md` line 22 and master plan line 225 are re-scoped to TA-DS-ROM-WAFER; a test proves no `CLUSTER_32` code path assumes HBM-resident weights |
| DRA-R1 | roofline array coverage | both models, four contexts, two studies, array device-count ladder, `array-32-controlled` design, per-batch three-class tables with resident sessions |
| DRA-C2 | capability and cost table | `rom_deepseek_v4_array_32.json` validates and records per-node die area with its grade in `notes`; `abi3_cost_rom_array_v1.json` loads with full provenance; `publish_abi3_capabilities.py --check` passes |
| DRA-P3 | Flash array deployment | 32 node images inverse-reconstruct bit-exactly; density reconciliation recorded; descriptor multiset equals the HBM cluster's; schedule certificate case passes; byte-identical rebuild |
| DRA-S4 | Flash array functional execution | `TA-DS-CTX-*` ladder through 200K, `TA-DS-CHAT-1`, `TA-DS-AGENT-1`; oracle agreement; per-node counters reconcile; divergence from the HBM lane, if any, mechanised |
| DRA-Y5 | Flash array cycle closure | functional == cycle on all counters; complete schedule audit; provenance counts published |
| DRA-X6 | governed three-way Flash comparison | both contracts produce `results/abi3/comparison_deepseek_rom_array_vs_hbm.json` and `comparison_deepseek_rom_wafer_vs_rom_array.json` with `iso_area_ratio` within tolerance or a stated correction; W11.2 readiness gains the array rows |
| DRA-R6 | representative array RTL | one node's program through ROM service plus inter-chip endpoint; fault campaign fail-stops |
| DRA-PRO7 | Pro front end | checkpoint lock, tensor and graph contracts, neutral IR, workload pins, 200K oracle rung, KV grade retired |
| DRA-N8 | `CLUSTER_N` amendment and two-level fabric | operator-conventions amendment merged; `ClusterFabric` two-level route; Pro node count derived and recorded |
| DRA-H8 | Pro HBM cluster deployment, execution, cycle | `cluster-N` profile; `TA-DSP-CTX-*` ladder through 200K on the HBM lane with oracle agreement; per-node counters reconcile; functional == cycle; the executed comparator for Pro exists |
| DRA-PRO9 | Pro array deployment, execution, cycle | DRA-P3/S4/Y5 repeated for Pro at its node count; 1,000,000-token rung as a stretch |
| DRA-X10 | governed Pro comparison | the iso-area Pro contract produces its artifact within tolerance; the capacity-optimal and, if needed, equal-node contracts produce theirs, labeled; W11.2 readiness gains the Pro rows |
| DRA-PHY10 | per-die physical closure | section 10 |
| DRA-REL11 | release | reproducible release; array rows in `UNIFIED_EXECUTION_CHECKLIST.md`, `PROGRAM_STATUS.md`, `EVIDENCE_LEDGER.md`; the crossover published from executed artifacts |

DRA-A0 through DRA-X6 are the Flash track and need no ABI amendment.
DRA-PRO7 runs in parallel from day one. DRA-N8 waits for DRA-S4; DRA-H8 and
DRA-PRO9 then run in parallel on the shared Pro IR, and DRA-X10 follows both.

## 13. Work packages

Each package names its files, its tests, and its make target. Ownership
follows master plan section 7: the DeepSeek ROM agent owns the array backend;
the ABI/IR/integration agent owns the `CLUSTER_N` amendment; the shared
HBM/SRAM agent is consulted on the link plan because the controlled variant
copies theirs; the independent verification agent owns the checker cases and
the descriptor-multiset test.

### WP-A: amendment and invariant test (DRA-A0)

- Edit `FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md` section 3 (matrix rows
  TA-DS-ROM-ARRAY-FLASH, TA-DS-ROM-ARRAY-PRO), section 12 (comparison pairs),
  and line 225; edit `DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md` line 22
  to name TA-DS-ROM-WAFER explicitly; add a subsection to ADR-003 section 3.3.
- `tests/abi3/test_cluster_storage_neutrality.py`: build a minimal
  `CLUSTER_32` fixture deployment with `StorageClass.ROM` weight objects and
  assert `Capability.validate`, `verify_deployment`, `DeviceMemory` window
  resolution, and `build_fabric` all admit it without a ROM-specific branch.
- Register this document in `docs/README.md` under "Implementation plans".

### WP-B: roofline coverage (DRA-R1)

- `tools/run_roofline_studies.py`: apply `ROM_AREA_LADDER` to array plans;
  add `array-32-controlled`; add contexts; extend
  `link_latency_sensitivity` per link grade.
- `tests/test_roofline.py`: assert the array ladder is emitted for both models
  at every context, and that `array-32-controlled` has `device_count == 32`
  and the HBM cluster's parallelism.
- `make roofline`; annotate the figures this plan cites.

### WP-C: capability and cost table (DRA-C2)

- `compiler/backends/rom/deepseek_v4_array.py`: `PROFILES`,
  `deepseek_v4_array_rom_capability()`.
- `configs/hardware/abi3_capability/rom_deepseek_v4_array_32.json`,
  `configs/hardware/abi3_cost_rom_array_v1.json`.
- `tests/test_technology.py` and `tests/abi3/test_feature_requirements.py`
  extended; `tools/publish_abi3_capabilities.py --check`.

### WP-D: array backend (DRA-P3)

- `compiler/backends/rom/deepseek_v4_array.py`: `_ArrayPlacer`,
  `_array_topology_factory`, `_array_link_plan_factory`,
  `deepseek_v4_array_rom_policy`, `build_deepseek_v4_array_rom_deployment`,
  `lower_to_abi3`.
- `tools/build_rom_deployment.py`: add product `deepseek-v4-flash-array`
  (and later `deepseek-v4-pro-array`); Makefile target
  `abi3-rom-deepseek-array-build`.
- `tools/check_rom_schedules.py` `DEFAULT_CASES` and
  `compiler/backends/rom/common/check.py` node-scoped reconstruction; Makefile
  `abi3-rom-schedule-check` picks it up.
- `tests/test_deepseek_v4_array_backend.py`: expert ownership, no cross-node
  expert split, inverse proof on a generated small checkpoint, density
  reconciliation note present, descriptor multiset equality with the HBM
  cluster deployment built from the same IR.

### WP-E: functional execution (DRA-S4)

- `runtime/sim/device.py` and `runtime/sim/memory.py`: per-node ROM image
  binding through A28 node segments; per-node `rom.bytes_read`.
- `tools/build_abi3_deployment_rtl_vectors.py` and the accelerator-token
  campaign tools gain the array case; results land in
  `results/abi3/deepseek_v4_rom_array_ta-ds-*_execution.json` and
  `results/abi3/accelerator_tokens/deepseek_v4_flash_rom_array_p32.json`.
- `tools/check_deepseek_v4_200k_accelerator_acceptance.py` gains a third lane.

### WP-F: cycle closure (DRA-Y5)

- `runtime/cycle/model.py`: no change expected for 32 nodes; the artifact
  `results/abi3/deepseek_v4_flash_rom_array_32_p32_prefill_cycle.json` is the
  sibling of the HBM one at W7.5.
- `tests/test_cycle_rom_array.py`: counter reconciliation and the no-zero-latency
  assertion on the array fabric.

### WP-G: comparison (DRA-X6)

- Two contracts under `configs/abi3/comparison_contracts/`.
- `tools/build_comparison_report.py` runs twice; `tools/abi3_comparison_boundary.py`
  and `tools/audit_abi3_asap7_comparison_readiness.py` learn the contracts.
- `tests/test_abi3_comparison_boundary.py` extended.

### WP-H: RTL (DRA-R6)

- An elaboration profile in `rtl/abi3/` that instantiates ROM service and the
  inter-chip endpoint under the shared microsequencer; `tools/rtl_abi3_deployment_campaign.py`
  and `tools/rtl_fault_campaign.py` gain the array case.

### WP-P: Pro front end (DRA-PRO7)

- `compiler/models/deepseek-v4-pro-0813/{checkpoint_source.json,config.json,inference_config.json,README.md}`.
- Generalize the DeepSeek adapter under `compiler/tensor_accelerator/` and
  `compiler/scheduling/deepseek_v4_*.py` over layer, expert, hidden, and
  attention-group parameters; `tests/test_deepseek_v4_pro_contract.py`.
- `tools/build_deepseek_v4_kernel_ir_v3.py --model deepseek-v4-pro-0813`;
  `tools/build_deepseek_v4_workloads.py` for `TA-DSP-*`;
  `tools/run_deepseek_v4_reference_oracle.py` Pro profile with `--measure-kv`.

### WP-N: `CLUSTER_N` and two-level fabric (DRA-N8)

- `runtime/abi3/constants.py` (`CLUSTER_N = 3`), `capability.py` validation
  branch, `verifier.py` node-count rule, `runtime/cycle/machine.py`
  (`ClusterFabricParams` two-level fields), `runtime/cycle/fabric.py`
  (`ClusterFabric.route` inter-domain resource).
- Amendment text in `TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md`;
  wire-format note if the `TOPOLOGY` payload needs a `domain_size` field.
- `tests/abi3/test_cluster_n.py`.

### WP-M: Pro HBM cluster (DRA-H8)

- `compiler/backends/hbm_sram/capability.py`: `clusterN_capability(node_count)`
  and a `cluster-N` entry in `PROFILES`; `tools/build_hbm_sram_deployment.py`
  `--profile cluster-N --nodes 48`; Makefile `abi3-hbm-deepseek-pro-build`.
- `compiler/backends/hbm_sram/plan.py`: expert ownership
  `floor(e / experts_per_node)` with the divisibility rule; remove the 32-node
  tile-row projection at line 4427; `TopologyPlan` docstring and shard-axis
  rule generalized. `lower.py` and `check.py` follow.
- `configs/hardware/abi3_capability/hbm_sram_cluster_48.json`,
  `configs/hardware/abi3_cost_clusterN_v1.json` with the two-level fabric
  parameters of WP-N.
- `tools/check_hbm_deployments.py` gains the Pro case;
  `results/abi3/hbm_deepseek_pro_deployment_certificate.json`.
- Functional and cycle artifacts as for Flash:
  `results/abi3/deepseek_v4_pro_hbm_ta-dsp-*_execution.json`,
  `results/abi3/deepseek_v4_pro_hbm_p32_prefill_cycle.json`.
- `tests/test_hbm_cluster_n.py`: capacity fit at 48 nodes, ownership
  divisibility, descriptor census scales with node count, node-count
  identity between capability, topology descriptor, and verifier.

### WP-Q: Pro array (DRA-PRO9)

- WP-C through WP-G repeated with `deepseek-v4-pro-array` at the derived node
  count and the two-level fabric.

### WP-Y: physical (DRA-PHY10)

- `tools/build_qwen3_tensor_accelerator_full_physical.py`-style runner for
  the array die; results under `results/physical/` per view; cost-table
  `characterized` promotions with cited paths.

## 14. Risks and open questions, stated before the work starts

1. **ROM density is the load-bearing constant, and it is unverified.** The
   roofline's 7.4x weight-bandwidth advantage over the HBM cluster rests on a
   60 GB/s/mm² read-bandwidth density from a simulated 28 nm macro that the
   repository could not fetch (`EVIDENCE_LEDGER.md` line 449), times a node
   scaling factor. The array target does not retire this; a test chip does.
   Every array result inherits the grade until then.
2. **The array die is compute-thin.** At batch 8 the roofline's 32-die array
   binds on `link_latency` at 218 µs with compute at 201 µs and 7.6% of die
   area as compute. A compute-efficiency miss flips the binding constraint.
   DRA-R1 must sweep the compute area fraction and report the flip point.
3. **Cross-die expert dispatch on every token.** With eight experts per node
   and six experts per token, most tokens touch several nodes. This is the
   HBM cluster's situation too, which is why the controlled comparison is
   fair, but the *ROM* thesis is that weight reads are cheap, and the array
   converts part of that saving back into fabric traffic that the wafer's
   mesh was supposed to absorb. The retraction in
   `WAFER_VERSUS_ARRAY_LATENCY.md` says the wafer mesh does not absorb it
   either (138–235 µs for an on-wafer all-reduce). The real lever is a
   placement that keeps dispatch local, and that is compiler work this plan
   leaves to a later optimization package, not to the controlled variant.
4. **The density reconciliation may move the node count off 32.** If the
   graded density and area fraction at DRA-P3 do not fit Flash in 32
   reticle-class dies, the controlled comparison is re-stated at a declared
   node-count ratio, not silently rescued by a denser constant.
5. **Pro's front end is large.** 149,782 tensors, 66 shards, 892.7 GB to
   stream and lock, an oracle whose 200K rung will take longer than Flash's
   435 s, and an adapter that has only ever seen one model's constants. It is
   the longest pole and it is topology-independent; the plan does not let it
   gate the Flash track.
6. **`CLUSTER_N` is an ABI amendment.** ADR-003 section 3.3 calls the three
   topologies "non-interchangeable"; adding a fourth is a contract change and
   goes through section 6.3 review. Sequencing it behind DRA-S4 keeps the
   experiment clean but delays Pro.
7. **Session capacity and the beachfront rule.** The array's 7.2x session
   advantage over one wafer follows from `max_hbm_stacks_per_device`, which
   charges 0.60 edge utilisation from shipping GPU packages. The iso-node
   study's `hbm_package()` admits up to 100% and its published 48- and
   56-stack envelopes exceed the 0.60 rule. That inconsistency is in the
   wafer's model, not the array's, but the three-way comparison must apply
   one rule to all three classes.
8. **Vector, softmax, top-k, and Sinkhorn service is unmodeled.**
   `ASSUMPTIONS.md` section 3: "all token rates remain conditional." True for
   every target; stated here so the array is not read as an exception.
9. **The Pro HBM comparator's node count is derived, not chosen, and the
   alternatives are labeled.** Iso-area sets the headline comparator; at
   equal die area it is capacity-starved by design. The 48-node cluster is
   capacity-comfortable, holds about five 200K sessions per node, and is the
   HBM side's own best machine. Neither is the commercial GPU; both are the
   shared chip. The three Pro contracts of section 11 exist so the reader
   sees the iso-area comparison, the comparator's optimum, and the
   storage-class control side by side rather than one dressed as another.
10. **The Pro HBM lane is the second-longest pole.** It needs the `CLUSTER_N`
    amendment, the Pro IR, a 48-node deployment that has never been built,
    and a 200K functional run of a 892.7 GB model on the HBM lane. It is also
    the only thing that makes a Pro array result comparable to anything
    executed, which is why the plan carries it rather than settling for the
    projected comparator.
11. **Die areas are assumed until DRA-PHY10.** Every iso-area comparison made
    before a physical view produces per-node die areas for both dies is
    read at an assumed 815 mm² on each side, and the artifact says so. If the
    ROM die and the shared HBM die turn out to differ in area, the derived
    HBM node counts move, and the Flash 32-versus-32 pair becomes the
    equal-node control rather than the iso-area headline. The plan reports
    both rather than choosing the one that flatters either side.

## 15. Non-goals and change control

- This plan does not retire TA-DS-ROM (wafer). The wafer remains a target with
  its own plan and gates; this plan makes it a *compared* target rather than
  a mandated one.
- No result from the array target may be reported as a wafer result or vice
  versa. `topology_class` and `node_count` are on every artifact.
- No analytical or cycle number is a TPOT. Master plan section 11.1 governs.
- The controlled variant does not optimize placement, parallelism, or the
  link plan beyond what the HBM cluster does. An optimized array is a
  separate design with its own name and its own comparison.
- Speculative decoding, DSpark, prefill/decode disaggregation, and multi-wafer
  or multi-array scale-out are out of scope, as they are for the wafer plan.
- Changes to shared contracts (ABI, IR, capability schema, comparison contract
  schema) follow master plan section 6.3.

## 16. Immediate next work

The first tranche, in order, none of it waiting on the others' results:

1. WP-A: land the amendment text and the storage-neutrality test.
2. WP-B: apply the area ladder to arrays and add `array-32-controlled`;
   regenerate `make roofline`; confirm the 32-node point reproduces the
   figures this document cites.
3. WP-C: publish the array capability and the first cost table.
4. WP-P: open the Pro model directory and start the 892.7 GB checkpoint lock
   on a scheduled window.
5. WP-M, first half: the `cluster-N` capability profile and the removal of
   the three 32-node assumptions in the HBM backend, behind a test, so that
   the Pro HBM lane is ready to compile the moment the Pro IR and the
   `CLUSTER_N` amendment land.

Then WP-D, which is the first tranche that produces an artifact the wafer
plan does not already have: a 32-node ROM image set whose descriptor multiset
equals the HBM cluster's.

## 17. Status as built, 2026-09-03

Every row below is read from an artifact on disk; nothing here is a claim
about silicon. The gate letters are section 12's.

| Gate | Status | Evidence |
|---|---|---|
| DRA-A0 | **closed** | Master plan section 3 carries the three array rows and section 12 the iso-area rule; ADR-003 section 3.3 admits the fourth profile; `runtime/abi3/capability.py` requires exactly 32 nodes of a `CLUSTER_32`; `tests/abi3/test_cluster_storage_neutrality.py` proves a 32-node ROM-weight cluster is admitted, runs to `SUCCESS` on 32 node-private memories, and differs from the HBM build only in memory-traffic counters |
| DRA-R1 | **closed** | `tools/run_roofline_studies.py` samples the array class on an explicit device-count ladder (multiples of its floor and the counts whose silicon equals each wafer rung), publishes a three-class iso-area table per batch, and runs six context-ladder rungs per study under `results/roofline/context_ladder/`; the primary studies were regenerated (`make roofline`, 8m44s) and every document-bound figure re-synced |
| DRA-C2 | **closed** | `configs/hardware/abi3_capability/rom_deepseek_v4_array_32.json` (published from `compiler/backends/rom/deepseek_v4_array.py`, the cluster chip's topology class, link record and engine lane mix); `configs/hardware/abi3_cost_rom_array_v{1,2}.json` (the cluster table verbatim, v2 with the measured engine rates) |
| DRA-P3 | **closed for current Flash compiler/capacity boundary** | The sparse-corrected 3,956-kernel graph builds to 1,344 instructions and 3,423 descriptors, admits with zero errors and zero `STATE` resources, and is byte-identical on a second clean build. Backend-neutral liveness reduces 1,073,359,364,104 logical activation bytes to an 83-slot, 172,292,907,016-byte physical arena without shortening any IR extent. The array uses 178,281,603,216 of the physical 180,000,000,000 HBM bytes per node. The source-current identities and full capacity proof are retained in `results/abi3/deepseek_v4_activation_liveness_capacity.json`. Against this deployment identity the independent schedule checker passes **139** checks <!-- figure: 139 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].passed_check_count" name="array independent ROM schedule checks passed" --> over **1,344** instructions <!-- figure: 1,344 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].actual.instructions" name="array ROM instructions" --> and **3,423** descriptors <!-- figure: 3,423 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].actual.descriptors" name="array ROM descriptors" -->, and the regenerated inverse proof reconstructs all **156,015,698,140** checkpoint payload bytes <!-- figure: 156,015,698,140 src="results/abi3/deepseek_v4_rom_array_inverse.json#report.payload_bytes" name="array inverse payload bytes" --> bit-identically from the node-sharded images |
| DRA-S4 | **in flight on the fixed source; two runs lost, one refused** | `tools/run_accelerator_tokens.py --backend rom_deepseek_v4_array` on `TA-DS-CTX-129-1` lowers, publishes and is admitted. Two executions on the superseded source were lost from outside the tool: the first ran 2 h 45 min at 64 GB resident before the session's background job was stopped, the second 1 h 48 min to 76 GB resident before a SIGTERM no transcript or journal accounts for; the tool keeps nothing on either. The first execution on the source-current lowering was *refused* by the device after 22 s, at the first layer's prefill: `ATTENTION.SPARSE input 1 (view 548) is BF16 rank 3; amendment A6 requires a fused BF16 KV tensor [kv_rows, head_dim]` (the record is `results/abi3/deepseek_v4_rom_array_ta-ds-ctx-129_refusal.json`, status `failed`, zero tokens). Boundary 5 below records the defect and its fix. The execution on the fixed lowering started at 01:24 UTC on 2026-09-04 and writes `results/abi3/deepseek_v4_rom_array_ta-ds-ctx-129_execution.json` on completion. No token claim is made here |
| DRA-Y5 | **historical attempt failed; source-current retry open** | The old `tools/run_abi3_cycle.py` attempt was killed by the kernel OOM killer after 155 min of wall time and 29 h of CPU at 84 GB resident and wrote no cycle artifact. That deployment gave every logical activation a separate object and declared 1.2 TB per node. The source-current liveness build instead fits the physical 180 GB per-node boundary, so the historical OOM is not evidence about its host-resident behavior. A fresh run is required, sequenced after DRA-S4 on this shared host, and any resulting cycles remain ineligible for TPOT until the same execution passes exact token correctness |
| DRA-X6 | open | both contracts are written: the array-versus-HBM contract (`configs/abi3/comparison_contracts/deepseek_v4_rom_array_32_vs_hbm_cluster_32_v1.json`) and the wafer-versus-array contract (`configs/abi3/comparison_contracts/deepseek_v4_rom_wafer_vs_rom_array_32_v1.json`). The latter is admitted by an additive amendment of `schemas/abi3/comparison_contract_v1.schema.json`: `targets` now takes either the `{rom, hbm}` pair or a `{rom, rom_array}` pair, and every slot pins its target's `role` to the slot name and its `storage_class` to that role's storage (`rom` and `rom_array` ROM, `hbm` HBM), so a mislabelled role is refused by the schema and not only by the tool; the existing contracts validate unchanged, and `tools/abi3_comparison_boundary.py` and `tools/audit_abi3_asap7_comparison_readiness.py` register the contract and pair its sides by the roles it declares. Its `policy.technology_claim` states the iso-area rule for this pair with every figure's source. No comparison artifact exists: the wafer-versus-array artifact waits on an array token report for the same request as the wafer's `results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json` (`TA-DS-CHAT-1-P32`) |
| DRA-R6 | open | no array RTL elaboration profile |
| DRA-PRO7 | **front end closed; workloads and oracle open** | The released checkpoint is on this host and bound: `tools/build_checkpoint_source.py` derived `compiler/models/deepseek-v4-pro-0813/checkpoint_source.json` from the 92 files at revision `72e1d3230f6c`, 67 of them agreeing with the committed registry witness on digest and size and the 25 small files on size; `tools/build_checkpoint_lock.py` then read all **892,727,580,904** payload bytes across **149,782** tensors in 66 shards in 953 s, giving lock `4aff8a9e2455` and tensor content `be1727c7c091`, both pinned on the release record so a substituted checkpoint cannot pass. `compiler/frontend/deepseek_v4_releases.py` carries one frozen record per release and the front end confronts the released config with it key by key. The Pro kernel IR builds: **6,742** kernels over 12,116 tensors, graph `c4c7e5fd7aff`, 61 sparse-attention kernels against Flash's 43, with the Flash IR byte-identical throughout. The independently derived tensor count and payload match `data/inventory/deepseek-v4-pro-0813.json` exactly. Still open for the gate: `TA-DSP-*` workloads, the 200K reference oracle, and the numeric qualification |
| DRA-N8, DRA-H8, DRA-PRO9, DRA-PHY10, DRA-REL11 | open | not started |

### What the built array is, exactly

The controlled variant of section 6, as shipped: expert-parallel with
consecutive ownership (**8 experts per node** <!-- figure: 8 src="build/abi3/deepseek-v4-flash-rom-array-32/deployment.json#notes.array_placement.experts_per_node" name="array experts per node" -->), routed expert banks and their block-scale banks node-sharded as A28 `node_segments` images, every routed view presenting eight local experts against the global bound of 256, and one data-bearing `LINK.COLLECTIVE SUM` over the 32 nodes per routed group ahead of `EXPERT_REDUCE`. Dense, attention, indexer, hyper-connection, embedding and vocabulary weights are replicated on every node.

The per-node bytes, from the deployment's own notes:

| Quantity | Bytes | Source |
|---|---:|---|
| sharded routed ROM per node | 4,599,054,336 | `notes.array_placement.sharded_rom_bytes_per_node` |
| replicated dense ROM per node | 8,846,229,504 | `notes.array_placement.replicated_dense_rom_bytes_per_node` |
| ROM per node | 13,445,283,840 | `notes.array_placement.rom_bytes_per_node` |
| unique ROM in the plan | 156,015,968,256 | `notes.array_placement.rom_bytes_plan_unique` |
| physical ROM across 32 nodes | 430,249,082,880 | `notes.array_placement.rom_bytes_array_physical` |

That is the density-reconciliation gate of section 6.4 answered with numbers rather than an estimate: the replicated dense store costs 2.76x the unique checkpoint in physical ROM, and the per-node ROM implies **1,109 mm²** at the wafer backend's usable density and **1,533 mm²** at the roofline's N5 array density, both above one 815 mm² reticle. Under section 3.5 the iso-area comparator for *this* build is derived from those bytes, not from 32 x 815 mm². A column-sharded dense partition (WP-D2) remains the option that would bring ROM area per node back toward one reticle; it is no longer a prerequisite for mutable-buffer HBM capacity.

### Two boundaries the build declares rather than hides

1. **The full IR horizon fits the physical five-stack HBM boundary through proved liveness reuse.** The ROM program retains every tensor and state extent at the model's 1,048,576-position maximum. Its 407 poolable logical activation roots total 1,073,359,364,104 bytes, but only disjoint closed lifetimes with exactly equal size and dtype share an address. The resulting 83 physical slots occupy 172,292,907,016 bytes; with state and other mutable objects, the array uses 178,281,603,216 bytes per node and leaves 1,718,396,784 bytes below the declared and physical 180,000,000,000-byte boundary. This is neither context clamping nor host virtualization.
2. **Host-resident simulation remains an execution measurement, not an admission assumption.** The old cycle run's 84 GB OOM came from the superseded one-object-per-logical-buffer deployment and produced no artifact. The new program reduces the virtual per-node arena and admits, but 32 private node memories can still create a large resident working set. A fresh instrumented run must establish peak RSS and completion. Even then, simulator wall time is campaign throughput, not accelerator TPOT.
3. **The reduction's route class is the ROM lowering's, not the HBM cluster's numbering.** The ROM traffic semantics assign every collective route class 2; the execution design's "route class 3" is the HBM backend's own table. The meaning, the owner-partial sum before `EXPERT_REDUCE`, is what the checker proves.
4. **The independent checker now derives the phase-layout certificate instead of failing on it.** The sparse-phase lowering emits one operator per phase behind a `PHASE_IS` branch, each waiting on the producers of its own `phase_inputs` subset, and converges the block on a `CONTROL.FENCE` (or a guarded `CONTROL.WAIT` when an optional prefix splits the phase further) before control leaves it, which the operator conventions name as the certificate that program order carries the result into the consumer. The checker had no such rule: on the source-current builds it failed `producer_consumer_wait`, `producer_signals` and `rolling_history_terminal_fence` (128 of 130 on the array, 122 of 123 on the wafer). It now reconstructs the certificate from the graph attribute and the program under four rules (`phase_layout_wait`, `phase_layout_coverage`, `phase_layout_convergence`, `phase_layout_program_order`), keys the terminal token fence on the one fence that belongs to no kernel, and is proved to refuse a phase fence turned into a NOP and a consumer hoisted above its block (`tests/compiler/test_rom_array_backend.py`). The regenerated certificate passes **134** checks on the array and **128** <!-- figure: 128 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-wafer].passed_check_count" name="wafer independent ROM schedule checks passed" --> on the wafer.
5. **A terminal drain bucketed two mutually exclusive producers together and stalled every ROM execution.** The instruction that publishes a token is preceded by a drain that acquires each outstanding predicated producer, bucketed by its guard. A guard is only part of a producer's reachability condition; the enclosing branch is the rest. The phase-selected join emits the same operand-present condition once in the prefill block and again in the decode block, so two operators that can never both run shared one bucket and the drain waited on both. The wafer's 32-token run stopped after 2,438 s with `prefill failed: wait on event 177 that has not been signalled`, and the array carried the identical construct, which is why its 129-token functional run was killed at 1 h 27 min rather than allowed to reach the same stall. The drain now skips any event a wait already acquired under exactly its producer's guard, the in-block wait being the certificate that the live path retired. The independent checker gains `branch_exclusive_wait`, which is not a special case for phase layouts: an unconditional forward branch that jumps past a later instruction proves the two sides are mutually exclusive, so no wait set may name an event from each side. Run against the deployment that stalled, the rule refuses it and names instruction 1315 and the branch at 451, which is the instruction that hung; the rebuilt wafer passes 128 of 128.
6. **The collective summed a slot the pack had not filled, and one token into decode it overflowed.** A `LINK.COLLECTIVE` reduces `byte_extent` bytes from every participant and `byte_extent` is a descriptor constant, while the pack writes only the rows the step produced: a decode step's block is one token's rows where a prefill step's is the whole span. Whatever the pack leaves untouched, the collective still sums, and the staging objects are shared by byte size across every reduction site, so that tail holds another step's bytes read under this step's dtype. Thirty-two of them summed past the binary32 range: `decode step 1 failed: collective reduction overflowed binary32`, after a prefill that was correct — the array's first generated token, 13806, matches the reference oracle exactly. Each participant slot is now filled with positive zero over its declared maximum before the pack, which is the rule the non-owned expert rows already follow. Four checker rules hold it: the slot is cleared, the fill covers the declared maximum unconditionally, the code is positive zero, and the pack waits for the fill. The array rebuilds to **1,344** instructions <!-- figure: 1,344 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].actual.instructions" name="array ROM instructions" --> at **139** checks <!-- figure: 139 src="results/abi3/rom_schedule_checks.json#cases[case=deepseek-v4-flash-rom-array-32].passed_check_count" name="array independent ROM schedule checks passed" -->.
7. **The source-current lowering did not execute, on the wafer or the array, until the fused KV operand was exempted from the head broadcast.** `_operand_view` inserts the query's missing middle axis at stride zero whenever a second operand's leading extent equals the query's. A window-only layer's prefill layout selects the current rows alone, so its KV extent equals the query extent and the rule produced a `[rows, 64, 512]` view for `ATTENTION.SPARSE` input 1; amendment A6 requires `[kv_rows, head_dim]` and the engine refused the first layer's prefill. The compressed layers escaped only because their prefix made the extents differ, and the superseded source escaped because its join carried 128 extra rows. The exemption is in `compiler/backends/rom/common/program.py`; `tests/compiler/test_rom_array_backend.py` lowers the released IR and requires every sparse attention's KV view to be rank two in every phase. Both ROM builds were regenerated on the fixed lowering (the instruction and descriptor counts are unchanged; the view descriptors changed), so every certificate above is bound to the fixed identity.

### Analytical results at iso-area, the deliverable of DRA-R1

Read from `results/roofline/n5_vs_b200/analytical.json` and the context-ladder rungs, `design_selection.models[...].iso_area_by_batch`. Each ROM class enters at its fastest feasible design for the batch; the GPU beside it is the B200 comparator at that design's own silicon. "array @ wafer area" is the fastest reticle array within 5% of the wafer's silicon.

| Model, context | Batch | Class | Design | mm² | user tok/s | resident sessions | vs iso-area GPU | J/token adv. |
|---|---:|---|---|---:|---:|---:|---:|---:|
| Flash, 200K | 1 | array | `array-hybrid-x30` | 24,450 | 2,627.4 | 1 | 1.79x | 5.2x |
| Flash, 200K | 1 | wafer | `wafer-tensor-x1-romfill` | 46,225 | 4,850.6 | 1 | 3.73x | 11.1x |
| Flash, 200K | 8 | array | `HBMKV-array-hybrid-x37` | 30,155 | 2,365.6 | 2,711 | 2.76x | 9.4x |
| Flash, 200K | 8 | wafer | `HBMKV-wafer-hybrid-x2-romfill` | 92,450 | 4,553.2 | 1,260 | 5.47x | 13.4x |
| Flash, 200K | 8 | array @ wafer area | `HBMKV-array-hybrid-x116-romfill` | 94,540 | 2,009.0 | 8,500 | wafer/array 2.27x on rate; array/wafer 6.75x on sessions | |
| Flash, 200K | 64 | array | `HBMKV-array-hybrid-x87-romfill` | 70,905 | 1,994.8 | 6,375 | 5.54x | 11.5x |
| Flash, 200K | 64 | wafer | `HBMKV-wafer-hybrid-x12-romfill` | 554,700 | 3,511.7 | 7,562 | 12.95x | 28.3x |
| Pro, 200K | 1 | array | `SRAMKV-array-tensor-x340-romfill` | 277,100 | 1,062.6 | 1 | 1.37x | 3.7x |
| Pro, 200K | 1 | wafer | `SRAMKV-wafer-hybrid-x3` | 138,675 | 2,648.8 | 1 | 3.54x | 14.6x |
| Pro, 200K | 8 | array | `HBMKV-array-hybrid-x161` | 131,215 | 857.6 | 8,242 | 2.27x | 19.1x |
| Pro, 200K | 8 | wafer | `HBMKV-wafer-hybrid-x3` | 138,675 | 2,646.5 | 1,320 | 6.95x | 25.1x |
| Pro, 200K | 8 | array @ wafer area | `HBMKV-array-hybrid-x170` | 138,550 | 828.7 | 8,703 | wafer/array 3.19x on rate; array/wafer 6.59x on sessions | |
| Pro, 200K | 64 | array | `HBMKV-array-hybrid-x193` | 157,295 | 742.3 | 9,881 | 7.26x | 17.8x |
| Pro, 200K | 64 | wafer | `HBMKV-wafer-hybrid-x6-romfill` | 277,350 | 2,219.3 | 2,641 | 20.86x | 42.3x |

The shape is the same at 8K, 32K and 1M for Flash and at 1M for Pro (the rung reports carry the full tables): the wafer holds 2.2x to 3.8x the per-user rate of an array of the same silicon, the array holds about 6.6x the resident sessions at batch 8, and both beat the iso-area B200 comparator on per-user rate and by a larger factor on energy per token. The Pro array is the only ROM class of Pro with a packaging path that does not wait for wafer-scale HBM; at 200K it is 1.4x to 7.3x the GPU on per-user rate at equal silicon and 3.7x to 17.8x on tokens per joule, at 131,215 to 277,100 mm² of silicon. Every number in this table is a deterministic model output under the graded inputs of `docs/ASSUMPTIONS.md`, with the two most load-bearing ROM constants unverified (`EVIDENCE_LEDGER.md`).

One correction the ladder forced: at N6 the Qwen3-8B recommendation moved from a 7-die array to a denser 6-die array (4,890 mm², 636.1 tok/s per 1,000 mm²) that the previous sampling never emitted. The bound figures in the README, the technical direction, the iso-area anchor and the wafer-versus-array documents were re-synced to the regenerated artifacts.
