# DeepSeek-V4.1-Flash ROM machine: implementation and evaluation plan

> **Revised 2026-09-23 — read [the revision results](ANALYTICAL_REPORT.md) first.**
> The roofline framework was corrected and extended (per-metric comparison designs,
> energy at delivered users, consistent GPU expert reads, per-weight compute-in-ROM
> cells, prefill, batches to 4,096, expert-parallel GPUs). Annotated figures below
> were rebound to the regenerated artifacts; unannotated roofline figures and any
> interpretation written before the revision are superseded where they conflict.

**Plan ID:** TA-DS41-3.0

**Status:** proposed delivery plan, not implemented evidence

**Issued:** 2026-09-13 UTC

**Targets:** TA-DS41-ROM-WAFER (primary), TA-DS41-ROM-ARRAY (controlled
experiment), TA-DS41-HBM (comparator), all on DeepSeek-V4.1-Flash at revision
`dba1be0a40aa45a94ad051997016db3960a90277`

**Physical topology:** two wafer-scale logical ROM accelerators in a pipeline
with one inter-wafer crossing per token, the Engram tables and every live
buffer in wafer-edge HBM; a reticle-class ROM array on the TA-DS-HBM fabric as
the controlled experiment; the model-blind HBM/SRAM cluster as the comparator.

**Authority:** this document organizes work and acceptance gates for a seventh,
eighth and ninth product target. It amends
[`FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md`](FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md)
section 3 and [ADR-003 section 3.3](TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md#33-mandatory-physical-scale-profiles),
inherits every rule of
[`DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V4_ROM_HARDWARE_IMPLEMENTATION_PLAN.md)
and [`DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md)
that it does not restate, and is gated by the board of
[`OPENTALLAS_REDESIGN_PLAN.md`](OPENTALLAS_REDESIGN_PLAN.md). It does not
retire, weaken or replace any of them. Nothing here promotes planned behavior
into implemented evidence.

**Analytical basis:** [`ANALYTICAL_REPORT.md`](ANALYTICAL_REPORT.md),
whose every figure is bound to `results/iso-node/`, `results/model-traffic/`
and `results/roofline/candidates/`. No number below is a TPOT. Master plan
section 11.1 governs.

---

## 1. Purpose: the model this architecture was waiting for, and what it costs

DeepSeek-V4.1-Flash is the first released model whose per-token KV traffic is
small enough that a mask-ROM machine stays bound by its own collective rather
than by its HBM edge across the batch range this program serves. At 200,000
tokens it reads 46.76 MB <!-- figure: 46.76 src="results/model-traffic/sweep.csv#kv_read_bytes_per_user_token" where="model=DeepSeek-V4.1-Flash;context_tokens=200000;batch_size=1" scale="1e-6" name="V4.1 KV read at 200K" -->
of KV per token against 317.46 MB <!-- figure: 317.46 src="results/model-traffic/sweep.csv#kv_read_bytes_per_user_token" where="model=DeepSeek-V4-Flash-0731;context_tokens=200000;batch_size=1" scale="1e-6" name="V4-Flash KV read at 200K" -->
for DeepSeek-V4-Flash, and streams 13.035 GB <!-- figure: 13.035 src="results/model-traffic/sweep.csv#active_weight_read_bytes_per_step" where="model=DeepSeek-V4.1-Flash;context_tokens=200000;batch_size=1" scale="1e-9" name="V4.1 weights per step" -->
of weights per step. Three consequences the analytical layer has already
priced, and this plan has to deliver or refute:

1. **The packaged array holds its per-user rate as users are added.** With
   hardware-limited links, striped expert banks and one layer per package, the
   N5 array serves 4,176 <!-- figure: 4,176 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176,batch_size=1].rom_per_user_tokens_s" name="V4.1 array rate B1" -->
   tok/s per user at batch 1 and 3,402 <!-- figure: 3,402 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x132,batch_size=64].rom_per_user_tokens_s" name="V4.1 array rate B64" -->
   at batch 64, now that its serial path is the per-token operator graph (the
   hyper-connection Sinkhorn chains dominate it). V4-Flash goes from 3,370 <!-- figure: 3,370 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56,batch_size=1].rom_per_user_tokens_s" name="V4-Flash array rate B1" -->
   to 2,431 <!-- figure: 2,431 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56,batch_size=64].rom_per_user_tokens_s" name="V4-Flash array rate B64" -->,
   because its KV reads are larger. Striping and the link latency are what this
   plan's cycle model and RTL must confirm (gate C3, section 4.4).
2. **The machine is a capacity problem, not a bandwidth one.** The checkpoint
   is 510.3 GB <!-- figure: 510.3 src="data/inventory/deepseek-v4.1-flash.json#checkpoint_bytes" scale="1e-9" name="V4.1 checkpoint GB" -->,
   of which 202.8 GB <!-- figure: 202.8 src="data/inventory/deepseek-v4.1-flash.json#lookup_table_bytes.engram_table_packed" scale="1e-9" name="Engram table GB" -->
   is Engram lookup tables read 24 rows per module per token. Where those
   tables live decides whether the primary target is two wafers or three, and
   whether an array is 51 reticles or 84. Section 3 decides it.
3. **The packaged array is now the winning class for this model.** At N5 the
   best array is 5.99× <!-- figure: 5.99 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176,batch_size=1].per_user_speed_ratio" name="V4.1 N5 array ratio B1" -->
   B200 on NVL72 per user at batch 1 and 7.22× <!-- figure: 7.22 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x132,batch_size=64].per_user_speed_ratio" name="V4.1 N5 array ratio B64" -->
   at batch 64 ([analytical report](ANALYTICAL_REPORT.md)). With GPU-class
   NVLink and InfiniBand it would only tie: both would pay hundreds of µs of
   collectives per token. The array target exists
   here to make that a measured statement rather than a modelled one.

**What this plan does not claim.** No V4.1 token has been produced by any
lane in this repository. Every KV byte width is read off the released code
and the technical report, not measured by running the model; for V4 the
measured width differed from the recipe by 1.8×. The FP4 expert path of the
existing V4 oracle ladder records `fp4_gemm_agrees: false` against its
tolerance, and V4.1 inherits that open item. Nothing in sections 4 to 12 is
built.

---

## 2. Inventory: what exists, what is reused, what is new

| Layer | Exists today | Reused by V4.1 | New for V4.1 |
|---|---|---|---|
| Analytical profile | `configs/models/candidates/deepseek-v4.1-flash.json`, `-engram_host.json`, `data/inventory/deepseek-v4.1-flash.json` (96,085 tensors, all shapes and dtypes) | as is | a third placement, Engram in wafer-edge HBM (WP-A) |
| Analytical studies | iso-node, traffic screen, roofline candidates, `tests/test_deepseek_v41_profile.py` | as is | the HBM-placement rows |
| Release pin | `compiler/frontend/deepseek_v4_releases.py` (`FLASH`, `PRO`) | pattern | `V41_FLASH` release record; `compiler/models/deepseek-v4.1-flash/{config,inference_config,checkpoint_source}.json` |
| Tensor adapter | `compiler/frontend/deepseek_v4.py` (`build_official_tensor_specs`, `_add_block`, `fp8_linear`, `fp4_linear`) | `_TensorBuilder`, FP8 and MXFP4 expert expansion, lock verification | CSA2 per-mode block expansion; Engram tables and projections; DSpark-3 blocks with 128 experts |
| Graph contract | `compiler/frontend/deepseek_v4_graph.py` | ledger machinery | new source operators: shared-cache read, candidate mask, Engram hash, gate |
| Kernel IR v3 | `compiler/ir/v3/kernel_ir.py` (60 kinds, 14 dtypes), `lowering.py` (`KERNEL_TO_ENGINE`) | every kind V4 uses | dtype `fp4_e2m1_s16_e4m3`; kinds `BLOCK_MAX`, `CANDIDATE_MASK`, `NGRAM_HASH`, `ENGRAM_GATE`; engine sub-ops for each (section 5) |
| IR exporter | `compiler/frontends/v3/deepseek_v4.py` (`DeepSeekV4Profile`, `lowering_plan`, `export_deepseek_v4_kernel_graph`) | builder, binding reader, census | `DeepSeekV41Profile` with 40-layer CED pins; a lowering plan with three attention modes |
| ROM backend | `compiler/backends/rom/deepseek_v4.py` (wafer), `deepseek_v4_array.py`, `rom/common/{image,program,check,inverse}.py` | placer, image plan, repair map, inverse proof, schedule checker | `deepseek_v41.py`: two-wafer pipeline policy, shared-STATE placement rule, Engram-in-HBM resident policy; `deepseek_v41_array.py` |
| HBM backend | `compiler/backends/hbm_sram/{capability,plan,lower,check}.py` | **model-blind, as is** | none beyond the new IR kinds |
| Capability | `configs/hardware/abi3_capability/rom_deepseek_v4*.json` | schema, publisher | `rom_deepseek_v41_wafer.json`, `rom_deepseek_v41_array_N.json`: `max_expert_ids` 384, two-node wafer topology, new numeric contracts |
| Cost tables | `tools/build_abi3_cost_tables.py`, `abi3_cost_{wafer,rom_array,cluster32}_v2.json` | generator | entries for the new engine blocks once routed |
| Functional simulator | `runtime/sim/`, `runtime/sim/engines/` | every engine | four engine sub-ops; shared-STATE cross-layer reads |
| Reference oracle | `runtime/reference/` (51 modules), `tools/run_deepseek_v4_reference_oracle.py` | `sparse_attention`, `index_score`, `compression`, `routing`, `hyper_connection`, `lm_head`, formats | `runtime/reference/{fp4_kv,candidate_pool,engram}.py`; `tools/run_deepseek_v41_reference_oracle.py` with the indexer instrumented |
| Workloads | `compiler/workloads/deepseek_v4.py`, three builders | ladder shape, Gutenberg prompt | `deepseek_v41.py`: `TA-DS41-CTX-{1K,8K,32K,128K,200K}-1`, `TA-DS41-CHAT-1-P32`, `TA-DS41-AGENT-1`, `TA-DS41-EOS-1` |
| RTL | `rtl/abi3/` (104 files): microsequencer, engines, `ot_a3_vector_index_score.sv`, `ot_a3_vector_compress_project.sv`, mHC blocks, link, ROM service | all of it | `ot_a3_vector_fp4kv_dequant.sv`, `ot_a3_route_block_max.sv`, `ot_a3_route_candidate_mask.sv`, `ot_a3_dma_ngram_hash.sv`, `ot_a3_vector_engram_gate.sv`; wafer-pair link adapter |
| Vectors and campaigns | `tools/build_abi3_shipped_prefix_vectors.py`, operator-admission and G1 ladder builders | all | V4.1 shipped-prefix entrypoint, admission vectors for the five new sub-ops, a V4.1 G1 ladder at reduced dimension |
| Cycle model | `tools/derive_cycle_machine.py`, `runtime/cycle/` | one-derivation rule | the V4.1 anchor cells and shipped-deployment pins |
| Physical | `results/physical_abi3/{asap7,sky130hd}/*`, IHP ROM chain, `tools/run_abi3_physical.py` | every routed block | five new blocks routed on both views; the wafer-pair endpoint; HBM beachfront for 43 stacks |
| Comparison contracts | `configs/abi3/comparison_contracts/*_v1.json` | schema | three V4.1 contracts |

The reuse column is the argument that this is one model's worth of work on a
machine that already exists. The new column is the work.

---

## 3. Target definition

### 3.1 TA-DS41-ROM-WAFER, the primary target

| Field | Value | Source |
|---|---|---|
| Model | DeepSeek-V4.1-Flash, revision `dba1be0a…`, MIT | `SRC-DSV41-FLASH-CARD` |
| Wafer count | 2 wafer-scale logical devices, central N4-class envelope | `results/iso-node/leading_node_market/analytical.json`, `wafer_stages` for `DeepSeek-V4.1-Flash-engram-host` = 2 <!-- figure: 2 src="results/iso-node/leading_node_market/analytical.json#comparisons[wafer_architecture=ROM-wafer-N4-class-HBM3e-central,model=DeepSeek-V4.1-Flash-engram-host,context_tokens=200000,batch_per_stage=1].wafer_stages" name="engram-host central wafer stages" --> |
| Layer partition | wafer 1: layers 0 to 19 (the causal encoder); wafer 2: layers 20 to 39 (the decoder), head and embedding | minimax contiguous partition of the per-layer inventory, 148.2 GB and 147.8 GB (author's arithmetic on `layer_dense_weight_bytes` + `layer_routed_weight_bytes`; `workload.linear_partition`) |
| ROM content per wafer | 20 layers × 384 experts × 18.8 MB plus 170 to 344 MB of dense weights per layer; wafer 2 adds the 1.32 GB BF16 head and 1.32 GB embedding | `data/inventory/deepseek-v4.1-flash.json` |
| Engram tables | **wafer-edge HBM of wafer 1 and wafer 2, one module each** (layer 1 on wafer 1, layer 14 on wafer 1; both modules are encoder-side, so both tables sit on wafer 1's HBM); written at load, never at runtime | section 3.4 |
| Global KV | four owners: layers 2, 8, 14 (ratio 2, wafer 1) and layer 20 (ratio 1, wafer 2); no reader on a different wafer from its owner | `configs/models/candidates/deepseek-v4.1-flash.json#metadata.csa2_layer_modes` |
| KV per session at 200K | 180.7 MB global plus 2.7 MB of window (author's arithmetic on `kv_traffic`) | feasibility section 2 |
| Cross-wafer payload per token | 40,960 B, the four mHC residual streams at BF16 | `cross_stage_payload_bytes_per_user_step` |
| Mandatory context | exactly 200,000 natural prompt tokens, plus the 1M-token architectural ceiling as a degraded mode | master plan section 4 |
| Numeric formats | FP8 dense × FP8 activations; MXFP4 experts × FP8; FP4 E2M1 main KV with E4M3 per 16, dequantized before attention; FP8 window KV | `SRC-DSV41-FLASH-REPORT` section 2.4.4 |

### 3.2 TA-DS41-ROM-ARRAY, the controlled experiment

| Field | Value | Source |
|---|---|---|
| Node count | N = 51 reticle-class ROM chips with Engram off-ROM; N = 84 to 91 with Engram in ROM. The plan builds N = 51 | `results/roofline/candidates/deepseek-v41-flash-engram-host/n5_vs_b200/REPORT.md`, class comparison |
| Die | 815 mm² reticle, the same unit of silicon as every other array target | `technology.json#reticle.area_mm2` |
| Expert ownership | whole experts per node, no expert split across nodes, 40 × 384 / 51 ≈ 301 experts per node | array plan section 3.1 rule |
| Fabric | exactly the TA-DS-HBM fabric: NVLink-class intra-domain, InfiniBand-class inter-domain | `technology.json#links` |
| Topology class | `CLUSTER_N` under AM-R1 | array plan section 5 |
| Purpose | hold model, tile and weight tier fixed and vary only packaging against TA-DS41-ROM-WAFER; hold node count and fabric fixed against TA-DS41-HBM | array plan section 1 |

### 3.3 TA-DS41-HBM, the comparator

The HBM/SRAM backend is model-blind. TA-DS41-HBM is the existing
`cluster-32` profile of `tools/build_hbm_sram_deployment.py` fed the V4.1
kernel IR, with the node count raised until 307.5 GB of weights plus the
session KV fit, and the Engram tables in host memory as DeepSeek serves them.
No new backend code; one new profile and one comparison contract.

### 3.4 Where the Engram tables live: decided here, revisited once by evidence

Three placements were priced in the feasibility study. Mask ROM costs a third
central wafer for 12,672 B <!-- figure: 12,672 src="configs/models/candidates/deepseek-v4.1-flash.json#metadata.engram.lookup_bytes_per_token" name="Engram lookup bytes per token" -->
of reads per token. Host DRAM costs a 1 to 2 µs PCIe or RDMA round trip that
the layer-1 module can hide behind only about 1.8 µs of work on a 70 µs step.
Wafer-edge HBM costs 202.8 GB of a 1,440 GB store, a few hundred nanoseconds
of prefetchable random read, and nothing on the critical path.

**Decision:** TA-DS41-ROM-WAFER places both Engram tables in wafer-edge HBM as
a resident, load-once, read-only region. The ROM-resident placement is
retained as `TA-DS41-ROM-WAFER-3` for the aggressive-density envelope only.
The decision is revisited exactly once, at gate DS41-C2, when the cycle model
prices the lookup on the HBM path with a measured transaction size; if the
lookup then lands on the critical path the fallback is the ROM placement, not
host DRAM.

### 3.5 What is mandatory and what is not

The plan requires: the primary target compiled, admitted, executed and
RTL-witnessed on the mandatory workload; the array target compiled and
executed to the same descriptor multiset; the comparator built from the same
IR; every new operator qualified against the external oracle; the five new
blocks routed on both technology views; the three comparison contracts
executed under the iso-area rule.

The plan does **not** require: prefill or the vision encoder (decode only,
master plan section 4); DSpark speculation in the first release (a separately
versioned extension, section 3.2 of the V4 ROM plan applies); the 1M context
as a first-release acceptance point; a third wafer; foundry signoff, a
package, or silicon.

---

## 4. The evaluation stack: six layers, each with its own gate

### 4.1 L0, analytical (exists)

**Exists.** Every study carries the model; section 1 quotes them. The
Engram-in-HBM placement is the one missing row.

**Deliverable.** A `hbm_resident_weight_bytes` term in
`src/opentallas/deployment.py` and `analytical.py` that subtracts resident
tables from the KV capacity of the stage that holds them and adds their
lookup bytes to the HBM stream; the profile
`configs/models/candidates/deepseek-v4.1-flash-engram_hbm.json`; iso-node and
roofline candidate rows.

**Gate DS41-A0.** The three placements appear in every study; all prior rows
stay byte-identical; the feasibility document's section 6 table cites the
modelled row instead of arithmetic.

### 4.2 L1, compiled deployment

**Exists.** The V4 wafer and array backends, the image and inverse machinery,
the schedule checker.

**Deliverable.** `build/abi3/deepseek-v4.1-flash-rom-wafer-2/` from
`tools/build_rom_deployment.py deepseek-v4.1-flash --verify --inverse
--determinism`; `build/abi3/deepseek-v4.1-flash-rom-array-51/`;
`build/abi3/deepseek-v4.1-flash-hbm-tokens/`; certificate cases in
`results/abi3/rom_schedule_checks.json`.

**Gate DS41-P3.** Every included tensor inverse-reconstructs bit-exactly from
the two wafer images and from the 51 node images; the descriptor multiset of
the array equals the HBM cluster's; **no `STATE.READ` of a shared global cache
crosses a wafer or node boundary** (a new schedule-checker rule, section 6.3);
zero `STATE` resources in ROM; byte-identical rebuild.

### 4.3 L2, functional execution

**Exists.** `runtime/sim/`, the external oracle pattern, the accelerator
token runner.

**Deliverable.** `results/abi3/accelerator_tokens/deepseek_v41_flash_{rom,array,hbm}_p32.json`
on `TA-DS41-CHAT-1-P32`; `results/abi3/deepseek_v41_reference_oracle_context_ladder.json`
at 1K, 8K, 32K, 128K and 200K with `Indexer.forward` and the Engram lookup
instrumented; a measured KV entry width at every rung.

**Gate DS41-X4.** Greedy lowest-id tokens identical to the oracle on all three
targets for the P32 workload; the measured main, index and window entry
widths written into the profile with grade `executed`, replacing the read-off
widths; the 200K rung executed.

### 4.4 L3, cycle model

**Exists.** `tools/derive_cycle_machine.py`, the C1 to C4 gates.

**Deliverable.** V4.1 anchor cells for the recommended N5 wafer design and its
GPU comparator; shipped-deployment registrations for the three targets;
`results/derived/deepseek-v4.1-flash__*_machine_pair.json` and
`_reconciliation.json`.

**Gate DS41-C2.** C1 exits 0 with V4.1 cells; C2 `comparable == true` on
every V4.1 pair; **C3 finds the collective floor as the binding constraint at
batch 1 to 32 at 200K**, or records the disagreement as the result; the Engram
lookup priced on the HBM path is below 1% of the step, or section 3.4's
fallback fires.

### 4.5 L4, RTL correlation

**Exists.** The ABI 3.0 control plane and engines in `rtl/abi3/`, dual
simulators, the G1 ladder machinery bound to Qwen.

**Deliverable.** The five new engine blocks with dual-simulator campaigns;
operator-admission vectors for each; a V4.1 shipped-prefix campaign on the
wafer entrypoint; a V4.1 G1 ladder at reduced dimension (section 10.2).

**Gate DS41-R6.** Every issued (family, shape, contract) class of the V4.1
decode program bit-exact against golden on real checkpoint rows (a G1a-shaped
record for V4.1); one complete V4.1 layer closed in RTL (G1b-shaped); the
reduced whole workload run with nothing injected (G1f-shaped).

### 4.6 L5, physical

**Exists.** Routed ASAP7 and SKY130 records for the lane, tile, LQ8, RE8,
microsequencer, G2 cluster, reduction and vector blocks; the IHP ROM chain.

**Deliverable.** `results/physical_abi3/{asap7,sky130hd}/a3_{fp4kv_dequant,block_max,candidate_mask,ngram_hash,engram_gate}/pnr.json`;
a wafer-pair link endpoint record; cost-table entries derived from them.

**Gate DS41-PHY10.** DRC 0, antenna 0, `flow_completed`, clean worktree on
every new block on both views; per-MAC area and period of the shared
datapath unchanged (D4 still passes); the cost table's `characterized` count
rises by the five blocks.

---

## 5. Kernel IR: what the model needs that the IR does not have

The IR is the frozen boundary between model and machine. A kind that is not
in `OPERATION_KINDS`, `KERNEL_TO_ENGINE` and `runtime/sim/engines/` is a
compile error, so each addition is a three-party change with a test.

| Mechanism | Lowering today | Addition | Engine sub-op | Why not an existing kind |
|---|---|---|---|---|
| FP4 main KV, E2M1 with E4M3 per 16 | none: `DTYPES` has `mxfp4_e2m1` with E8M0 per 32 only | dtype `fp4_e2m1_s16_e4m3`; `DEQUANTIZE` accepts it | `VECTOR.CONVERT` with a scale-group operand | the scale format and group differ from MXFP4; the contract `fp4_e2m1_s16_e4m3_to_fp8_v1` is new |
| Candidate pool, blockwise max | none | `BLOCK_MAX(scores, block=8) -> block_scores` | `ROUTE.BLOCK_MAX` | `INDEX_TOPK` selects positions, not blocks |
| Candidate pool, mask | none | `CANDIDATE_MASK(block_ids, block=8, width) -> mask`; `INDEX_TOPK` gains an optional mask slot | `ROUTE.CANDIDATE_MASK`; `ROUTE.INDEX_TOPK` slot 3 | the reference masks scores to −inf inside the candidate blocks; a mask operand keeps the top-k engine unchanged |
| Engram n-gram hash | none | `NGRAM_HASH(token_ids, order, head) -> row_ids` | `DMA.NGRAM_HASH` | integer multiply-modulo over compressed ids, per `inference/engram.py`; not a lookup |
| Engram row read | `EMBEDDING_LOOKUP` | as is, 24 rows × 264 B | `TENSOR.EMBED_LOOKUP` | already how V4 hash tables lower |
| Engram gate | none | `ENGRAM_GATE(h, key, value, q, k) -> h'` | `VECTOR.ENGRAM_GATE` | normalized dot, signed sqrt, sigmoid, residual add; one fused kind keeps the numeric contract `engram_gate_fp32_v1` auditable |
| Shared global cache | `STATE_READ` | as is, with the owner's `StateResource` visible to later layers | `STATE.READ` | a placement rule, not a kind (section 6.1) |
| Reused top-k indices | `INDEX_TOPK` output | held as a `StateResource` across up to five layers | `STATE.READ` | a lifetime rule, not a kind |
| Ratio-1 compressor | `COMPRESS_PROJECT` | as is, without `COMPRESS_POOL` | `VECTOR.COMPRESS_PROJECT` | simpler than V4 |
| Single-pass mHC | `HYPER_CONNECT_PRE/POST` | coefficients from the previous block | `VECTOR.MHC` | a scheduling change |

`FORBIDDEN_TERMS` neutrality holds: none of the new kinds names a store, a
bank or a wafer.

---

## 6. ROM physical compiler: `compiler/backends/rom/deepseek_v41.py`

### 6.1 The shared-cache placement rule

CSA2's cross-layer sharing is a placement constraint the wafer backend has not
needed before: a `StateResource` written by layer 2 is read by layers 3 to 7,
one written by layer 20 by layers 21 to 39. The rule is stated as a checkable
clause: **every reader of a shared global cache is placed on the stage that
owns it.** With the encoder on wafer 1 and the decoder on wafer 2 the rule
holds by construction, and the checker proves it rather than assumes it.

### 6.2 Two-wafer pipeline policy

`deepseek_v41_layout_policy()` extends the V4 `_WaferPlacer` with a stage
axis: layers 0 to 19 to wafer 1, 20 to 39 plus the head to wafer 2; expert
regions of 18.8 MB placed whole; the BF16 head and embedding in wafer 2's
slack. The link plan is one `LINK` per token carrying the four residual
streams (40,960 B), on the `inter_wafer` class the roofline already prices at
an assumed 5 µs hop swept 1 to 10 µs.

### 6.3 Independent checker additions (`compiler/backends/rom/common/check.py`)

- `shared_state_locality`: no `STATE.READ` resolves to a resource whose
  writer is on another node or wafer.
- `resident_hbm_region`: the Engram tables are a load-once region with no
  `STATE.COMMIT` and no `DMA.SCATTER` targeting them.
- `candidate_pool_bound`: every `INDEX_TOPK` after the candidate source
  carries a mask whose population is at most 16,384.
- `expert_capacity`: 384 expert ids and top-6 admitted by the capability
  (`max_expert_ids`, `max_topk`), against the V4 limits of 256 and 8.

### 6.4 Capability

`configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json`: `abi 3.0`,
`topology_class 2` with `max_nodes 2`, engines as V4, `max_expert_ids 384`,
`max_context_positions 1048576`, memory `rom.bytes` ≥ 307.5 GB across two
devices, `hbm.bytes` ≥ 1,440 GB per device with a declared `resident_region`
of 202.8 GB, and the numeric contracts of V4 plus
`fp4_e2m1_s16_e4m3_to_fp8_v1`, `engram_gate_fp32_v1`, `ngram_hash_u32_v1`,
`candidate_mask_v1`. Published by the backend, checked by
`tools/publish_abi3_capabilities.py --check`.

---

## 7. Functional simulator and reference oracle

**Work.**

- `runtime/sim/engines/`: the five sub-ops; `STATE.READ` of a resource owned
  by an earlier layer; the resident HBM region.
- `runtime/reference/fp4_kv.py`: E2M1 quantize after RoPE in groups of 16
  with E4M3 scales, dequantize to FP8, matching `fp4_act_quant(latent, 16,
  True, scale_dtype=float8_e4m3fn)` in the pinned `model.py`.
- `runtime/reference/candidate_pool.py`: `select_candidate_blocks` semantics
  including the pinned-last-block rule and the −inf padding.
- `runtime/reference/engram.py`: the compressed-vocabulary hash, the 24-row
  gather, the FP32 gate with the `1e-6` clamp and signed square root, per
  `inference/engram.py`.
- `tools/run_deepseek_v41_reference_oracle.py`: external comparator over the
  vendor's own code, one block and one expert at a time, greedy lowest-id
  argmax, schema `opentallas.abi3.reference_oracle.v1`, with **`Indexer.forward`
  and `Engram.forward` wrapped from the first run** (the V4 ladder
  under-counted index scans by up to 1.60× because the indexer was not
  wrapped) and the KV entry widths measured, not read.

**Exit:** the L2 gate of section 4.3. One evidence document per qualified
operator, `docs/DEEPSEEK_V41_{FP4_KV,CANDIDATE_POOL,ENGRAM,CSA2_SHARED_CACHE}_EVIDENCE.md`,
each with evidence class, qualified boundary, release and revision, reference
profile id, graph-contract digest at qualification, and a "not established"
list.

---

## 8. Cycle model and cost tables

`tools/derive_cycle_machine.py` derives one machine per V4.1 anchor cell and
emits it twice. The V4.1 cells are the recommended N5 two-wafer design against
`b200_sxm-x58-tensor` and the 51-reticle array against `b200_sxm-x43-tensor`,
at batch 1, 8 and 32. The cost tables stay generated: the five new blocks
enter `abi3_cost_wafer_v3.json` and `abi3_cost_rom_array_v3.json` only from
routed records, with provenance `characterized`, and the Engram lookup is
priced on the HBM path with `hbm.transaction_bytes` from the measured table.
The cycle model must reproduce the analytical binding constraint
(C3) at 200K or say why not; that reconciliation is the deliverable, not a
matching number.

---

## 9. Prerequisite track, topology-independent

| Step | V4-Flash precedent | V4.1 work |
|---|---|---|
| Release record | `deepseek_v4_releases.py::FLASH` | `V41_FLASH` with `config_sha256 8be45ce0…`, `index_sha256 74b0686a…`, 48 shards, 96,085 tensors, 510,286,023,000 bytes |
| Checkpoint source | `compiler/models/deepseek-v4-flash-0731/checkpoint_source.json` | `compiler/models/deepseek-v4.1-flash/checkpoint_source.json` from `tools/build_checkpoint_source.py` with the registry listing as witness; **requires the 510 GB snapshot on a host with the space** (this host had 372 GB free) |
| Checkpoint lock | `tools/build_checkpoint_lock.py`, ~25 min per 156 GB | ~80 min at 100 MB/s over 510 GB |
| Tensor specs | `build_official_tensor_specs` | per-mode block expansion; 40 × 384 experts; two Engram tables; DSpark-3 |
| Graph contract | `deepseek_v4_graph.py` | the four new source operators |
| Kernel IR | `tools/build_deepseek_v4_kernel_ir_v3.py` | `--model deepseek-v4.1-flash` → `build/ir-v3/deepseek-v4.1-flash/kernel_ir.v3.json` + `census.json`; make `abi3-ir` |
| Workloads | `compiler/workloads/deepseek_v4.py` | `deepseek_v41.py`, same prompt corpus, prefix `TA-DS41`; pins under `results/abi3/deepseek_v41_*_workload_pins.json` |
| Tokenizer and encoding | `deepseek_v4_{tokenizer,encoding}.py` | V4.1 ships `encoding/encoding.py` and a tokenizer at the same revision; verify by hash, reuse the DSML grammar where identical |

---

## 10. Workload and correctness plan

### 10.1 Short ordinary generation

`TA-DS41-CHAT-1-P32`: a 32-token prefix, greedy decode of 4 tokens on each
of the three targets, compared to the external oracle token for token. This
is the first executable claim and gates everything after it.

### 10.2 Reduced whole-run ladder

The Qwen G1 ladder is bound to `TA-QW-EOS-1`. V4.1 gets its own ladder at
reduced dimension, built the way `tools/build_qwen3_reduced_model.py` builds
Qwen's: hidden, expert width and expert count reduced, **40 layers and the
CSA2 mode sequence kept exactly**, because the mode sequence is what is under
test. `TA-DS41-EOS-1` is the reduced workload; `results/abi3/deepseek_v41_reduced_reference_oracle.json`
its oracle; `results/rtl/abi3_g1{a,b,c,d,e,f}_deepseek_v41_*.json` the
records, in the shapes `configs/gates/redesign_gates.json` already evaluates.

### 10.3 Exact 200,000-token acceptance

`TA-DS41-CTX-200K-1` on the primary target: 200,000 natural prompt tokens
plus ordinary decode, with buffer, token and counter evidence in the shape of
`tools/check_deepseek_v4_200k_accelerator_acceptance.py`. The KV counters must
reproduce the model's own arithmetic: 890 <!-- figure: 890 src="configs/models/candidates/deepseek-v4.1-flash.json#metadata.global_kv_bytes_per_token" name="global KV bytes per token" -->
global bytes per position, four owners, and index scans of context/2 on
layers 2, 8, 14, context on layer 20, and at most 16,384 on layers 24, 28,
32, 36. A counter that disagrees with the profile is a finding about one of
them, and which one is decided by the oracle, not by editing the profile.

### 10.4 Agentic context

`TA-DS41-AGENT-1`: a tool-call transcript in the released `encoding.py`
grammar, multi-turn, exercising SWA Bounded Replay's decode-side behaviour
only insofar as decode reads a window the encoder wrote. Prefill replay itself
is out of scope.

---

## 11. Physical plan: SKY130, ASAP7, and the wafer boundary

Two technology views, never mixed, as the V4 ROM plan requires.

1. **Block characterization.** The five new blocks synthesized and routed on
   `sky130hd` and `asap7` by `tools/run_abi3_physical.py --view … --block …`,
   each with `constraint.sdc`, four SKY130 corners and the ASAP7 TT corner,
   DRC 0, antenna 0, `closed` with its basis, clean worktree. Expected block
   classes: `fp4kv_dequant` and `engram_gate` are T1 vector blocks;
   `block_max` and `candidate_mask` are T1 route blocks; `ngram_hash` is a
   small integer datapath. None approaches the 250k-cell flat limit.
2. **Datapath unchanged.** The MAC lane, tile and LQ8 records stand; D1 to D5
   are re-evaluated, not re-taken, unless a block shares a netlist with them.
3. **ROM service.** The IHP bitcell → read-energy → macro chain is reused
   unchanged; V4.1 changes what is stored, not how a row is read. The 18.8 MB
   expert region is the same region V4 sizes.
4. **HBM edge.** 43 HBM3e stacks per wafer at the recommended N5 design
   (`hbm_stacks` of `ROM-N5-native-HBMKV-wafer-hybrid-x2`), against the
   beachfront ceiling the roofline already applies; the PHY stays a sourced
   boundary component with a datasheet grade.
5. **Wafer pair.** The inter-wafer endpoint synthesized and placed in view;
   the link itself stays an `assumed` 5 µs hop until a datasheet or a measured
   part replaces it, and the plan reports the sensitivity rather than the
   point.
6. **Power.** Executed-activity power from the functional runs, the
   clocked-idle floor, and the wafer thermal limit the roofline charges
   (0.075 W/mm² at the recommended design against a 1 W/mm² cooling limit).

Closure is hierarchical, as before: characterize tiles, close representative
reticle regions, extract cross-reticle links, assemble the wafer-level model.
A tile-only result cannot close DS41-PHY10.

---

## 12. Milestones

| Gate | Outcome | Exit evidence |
|---|---|---|
| DS41-A0 | third Engram placement modelled | `hbm_resident_weight_bytes` in the analytical model; iso-node and roofline candidate rows for `deepseek-v4.1-flash-engram_hbm`; all prior rows byte-identical; feasibility section 6 re-bound |
| DS41-S1 | checkpoint contract | `compiler/models/deepseek-v4.1-flash/checkpoint_source.json` witnessed by the registry listing; lock built over every byte; `V41_FLASH` release record; tensor specs reproduce 96,085 tensors and 510,286,023,000 bytes |
| DS41-I2 | kernel IR | `build/ir-v3/deepseek-v4.1-flash/kernel_ir.v3.json` neutral, census with zero unknown, unpriced, unreferenced or unbound counts; the four new kinds and one dtype in `kernel_ir.py`, `lowering.py` and `runtime/sim/engines/` with tests |
| DS41-P3 | compiled deployments | wafer-2, array-51 and HBM deployments; inverse proofs; schedule certificates including `shared_state_locality`; descriptor multiset equality array = HBM; byte-identical rebuild |
| DS41-X4 | functional execution | P32 tokens identical to the oracle on all three targets; oracle ladder 1K to 200K with indexer and Engram instrumented; measured KV widths written into the profile at grade `executed` |
| DS41-N5 | numeric contracts qualified | the four evidence documents; `tools/qualify_numeric_contracts.py` rows for FP4 KV dequant and the Engram gate |
| DS41-C2 | cycle model and comparison gates | C1 exit 0 with V4.1 cells; C2 comparable on every pair; C3 reconciliation recorded; Engram lookup priced on the HBM path; section 3.4 decision confirmed or its fallback fired |
| DS41-R6 | RTL witness | five blocks dual-simulated; admission vectors pass; V4.1 shipped-prefix campaign; G1a-, G1b- and G1f-shaped records for `TA-DS41-EOS-1` |
| DS41-200K7 | exact mandatory context | `TA-DS41-CTX-200K-1` executed on the primary target with buffer, token and counter evidence |
| DS41-PHY10 | physical closure of the new blocks | routed records on both views, DRC 0, antenna 0, clean; D4 unchanged; cost table v3 with five more `characterized` entries; wafer-pair endpoint record |
| DS41-CMP11 | governed comparison | three contracts executed under the iso-area rule; `results/abi3/comparison_deepseek_v41_*.json`; each published ratio beside its binding constraint and resident-session count |
| DS41-REL12 | release | every gate above green; `STATUS.md` and the checklist rows updated; no number promoted past its evidence class |

DS41-A0 and DS41-S1 have no dependency and start now. DS41-I2 needs DS41-S1;
DS41-P3 needs DS41-I2; DS41-X4 needs DS41-P3 and the oracle, which needs only
DS41-S1. DS41-N5 runs beside DS41-X4. DS41-C2 needs DS41-P3 and DS41-A0.
DS41-R6 needs DS41-I2 for vectors and nothing else. DS41-PHY10 needs only
the RTL of DS41-R6's five blocks and can start the day they elaborate.
DS41-200K7 and DS41-CMP11 close last.

---

## 13. Work packages

Each package names its files, its tests and its make target. Ownership
follows master plan section 7.

### WP-A: Engram-in-HBM placement (DS41-A0)

- `src/opentallas/deployment.py`, `analytical.py`: `hbm_resident_weight_bytes`
  read from `metadata`, subtracted from the holding stage's KV capacity, its
  lookup bytes added to `kv_read_bytes_per_user_token` on that stage.
- `src/opentallas/profiling.py`: variant `engram_hbm`;
  `tools/profile_hf.py --model deepseek-v4.1-flash-engram_hbm`.
- `tools/run_iso_node_studies.py`, `tools/run_roofline_studies.py`
  `CANDIDATE_MODELS`, `configs/hardware/technology.json` by-model entry.
- `tests/test_deepseek_v41_profile.py`: the third placement's capacity and
  traffic identities.

### WP-B: checkpoint contract and release record (DS41-S1)

- `compiler/frontend/deepseek_v4_releases.py`: `V41_FLASH`.
- `compiler/models/deepseek-v4.1-flash/{config.json, inference_config.json,
  checkpoint_source.json, README.md}` via `tools/build_checkpoint_source.py`.
- `compiler/frontend/deepseek_v4.py` or a sibling `deepseek_v41.py`:
  `build_official_tensor_specs` for the V4.1 block; `validate_official_config`
  pins for the 40-layer CED, `kv_source_layer_ids`, `index_source_layer_ids`,
  `candidate_source_layer_id`, `engram_*`.
- `tests/compiler/test_deepseek_v41_release.py`, `test_deepseek_v41_tensor_specs.py`.

### WP-C: IR kinds, dtype and simulator engines (DS41-I2)

- `compiler/ir/v3/kernel_ir.py`: `fp4_e2m1_s16_e4m3`; `BLOCK_MAX`,
  `CANDIDATE_MASK`, `NGRAM_HASH`, `ENGRAM_GATE`; `OPTIONAL_INPUT_SLOTS`
  extends `INDEX_TOPK` with the mask slot.
- `compiler/ir/v3/lowering.py`: `ROUTE.BLOCK_MAX`, `ROUTE.CANDIDATE_MASK`,
  `DMA.NGRAM_HASH`, `VECTOR.ENGRAM_GATE`; `runtime/abi3/constants.py` sub-op
  numbers under AM-E10 (new amendment, section 15).
- `runtime/sim/engines/{route,dma,vector}.py`: the four sub-ops.
- `tests/abi3/test_am_e10_v41_kinds.py`: three-party presence, neutrality,
  absent-operand rules.

### WP-D: IR exporter (DS41-I2)

- `compiler/frontends/v3/deepseek_v41.py`: `DeepSeekV41Profile` with
  `architecture_pins`; `lowering_plan` with `attention_full`,
  `attention_reindex`, `attention_reuse`; Engram at layers 1 and 14; DSpark-3
  behind `--include-speculative`.
- `tools/build_deepseek_v4_kernel_ir_v3.py --model deepseek-v4.1-flash`;
  Makefile `abi3-ir`.
- `tests/compiler/test_deepseek_v41_kernel_ir.py`: census equals the
  operator inventory of `src/opentallas/operations.py` per layer (a cross-check
  between the analytical and executable layers that V4 never had).

### WP-E: ROM wafer backend (DS41-P3)

- `compiler/backends/rom/deepseek_v41.py`: `PRODUCT="deepseek-v4.1-flash-rom"`,
  `TARGET_ID="deepseek-v4.1-flash-rom-wafer-2"`, two-wafer placer, shared-STATE
  placement, resident HBM region, link plan; `PROFILES["rom-deepseek-v41-wafer-2"]`.
- `compiler/backends/rom/common/check.py`: the four checker rules of 6.3.
- `tools/build_rom_deployment.py` product `deepseek-v4.1-flash`; Makefile
  `abi3-rom-deepseek-v41-build`; `tools/check_rom_schedules.py` case.
- `tests/test_deepseek_v41_rom_backend.py`: inverse proof on a generated small
  checkpoint with the real mode sequence; locality rule violated on purpose
  and refused.

### WP-F: ROM array backend (DS41-P3)

- `compiler/backends/rom/deepseek_v41_array.py`: 51-node placer under
  `CLUSTER_N`, whole-expert ownership, Engram in node-local HBM.
- `tools/build_rom_deployment.py` product `deepseek-v4.1-flash-array`;
  Makefile `abi3-rom-deepseek-v41-array-build`.
- `tests/test_deepseek_v41_array_backend.py`: descriptor multiset equality
  with the HBM deployment from the same IR.

### WP-G: HBM comparator (DS41-P3)

- `tools/build_hbm_sram_deployment.py --profile cluster-N --model
  deepseek-v4.1-flash`; `tools/check_hbm_deployments.py --case
  deepseek-v41-flash-hbm-cluster`; Makefile `abi3-hbm-deepseek-v41-deployment`.

### WP-H: reference oracle and evidence (DS41-X4, DS41-N5)

- `runtime/reference/{fp4_kv,candidate_pool,engram}.py`.
- `tools/run_deepseek_v41_reference_oracle.py`; outputs
  `results/abi3/deepseek_v41_reference_oracle_{prefix,context_ladder}.json`.
- `tools/validate_kv_model_against_oracle.py` extended to write measured
  widths back with grade `executed`.
- `docs/DEEPSEEK_V41_*_EVIDENCE.md` (four documents).
- `tests/test_deepseek_v41_reference_boundaries.py`.

### WP-I: workloads (DS41-X4)

- `compiler/workloads/deepseek_v41.py`; `tools/build_deepseek_v41_workloads.py`,
  `_prefix_workloads.py`; pins under `results/abi3/`.
- `tools/run_accelerator_tokens.py` backends `rom_deepseek_v41`,
  `rom_deepseek_v41_array`; Makefile `abi3-tokens-deepseek-v41-{rom,array,hbm}`.

### WP-J: cycle model cells and pins (DS41-C2)

- `configs/abi3/shipped_deployments.json`: three registrations, `pin_kind
  live` until frozen by evidence.
- `tools/derive_cycle_machine.py`: V4.1 anchor cells; `--matrix` rows.
- `configs/hardware/abi3_cost_{wafer,rom_array}_v3.json` generated by
  `tools/build_abi3_cost_tables.py` once WP-M lands; until then the v2 tables
  with the five blocks marked `assumed`.
- `tests/test_derive_cycle_machine_v41.py`.

### WP-K: RTL blocks (DS41-R6)

- `rtl/abi3/ot_a3_vector_fp4kv_dequant.sv`, `ot_a3_route_block_max.sv`,
  `ot_a3_route_candidate_mask.sv`, `ot_a3_dma_ngram_hash.sv`,
  `ot_a3_vector_engram_gate.sv`; packages updated with the sub-op ids.
- `tools/build_a3_v41_{fp4kv,candidate,engram}_vectors.py`,
  `tools/run_a3_v41_*_rtl_campaign.py`; both simulators; records
  `results/rtl/a3_v41_*_campaign.json`.
- `tests/test_a3_v41_blocks.py`.

### WP-L: shipped-prefix and G1 ladder for V4.1 (DS41-R6)

- `tools/build_abi3_shipped_prefix_vectors.py`: the V4.1 wafer entrypoint;
  `tools/rtl_abi3_shipped_prefix_campaign.py` case; record
  `results/rtl/abi3_shipped_prefix_campaign_v41.json`.
- `tools/build_deepseek_v41_reduced_model.py` after
  `build_qwen3_reduced_model.py`; `TA-DS41-EOS-1`;
  `tools/build_abi3_g1{a,b,f}_*.py --model deepseek-v4.1-flash`.
- `configs/gates/redesign_gates.json`: the V4.1 ladder as a second workload
  binding, so the board reports it beside Qwen's rather than in place of it.

### WP-M: physical records (DS41-PHY10)

- `tools/run_abi3_physical.py --view {sky130hd,asap7} --block a3_{fp4kv_dequant,block_max,candidate_mask,ngram_hash,engram_gate}`;
  `constraint.sdc` per block; records under `results/physical_abi3/`.
- `tools/run_a3_link_physical.py` for the wafer-pair endpoint.
- `tools/build_abi3_cost_tables.py --check`; `tests/test_abi3_physical_*`.

### WP-N: comparison contracts (DS41-CMP11)

- `configs/abi3/comparison_contracts/deepseek_v41_rom_wafer_2_vs_hbm_cluster_v1.json`,
  `deepseek_v41_rom_array_51_vs_hbm_cluster_v1.json`,
  `deepseek_v41_rom_wafer_2_vs_rom_array_51_v1.json` under the v2 schema with
  the iso-area rule and 2% tolerance.
- `tools/build_comparison_report.py`; Makefile `abi3-comparison-deepseek-v41`.

### WP-P: registration and ledgers (every gate)

- Master plan section 3 rows for the three targets; ADR-003 section 3.3
  profile; `docs/README.md` implementation-plans index; checklist rows
  `W14.1` to `W14.12` in `UNIFIED_EXECUTION_CHECKLIST.md`; `PROGRAM_STATUS.md`
  and `EVIDENCE_LEDGER.md`; `CONTRIBUTOR_TASKS.md` entries sized S, M or L.
- Promotion of the profile from `configs/models/candidates/` to
  `configs/models/` happens at DS41-X4, when the model has produced a token,
  and carries the legacy standard run and its test with it.

---

## 14. Risks and open questions, stated before the work starts

1. **The KV widths are read, not measured, and for V4 that was a 1.8× error.**
   The main latent at 288 B, index key at 68 B and window at 528 B come from
   the report and the pinned code. WP-H measures them at five contexts before
   any ROM image depends on them. If a deployment reads the latent wider, the
   iso-node advantage moves with the KV read, and section 1's first claim is
   the one that weakens.
2. **The FP4 numerics are an open item in the existing lane.** The V4 ladder
   records the FP4 expert GEMM disagreeing with its tolerance. V4.1 adds a
   second FP4 path in the KV latent. WP-H qualifies both, and a disagreement
   is a result to publish, not a tolerance to widen.
3. **The Engram placement is a decision, not a measurement.** Section 3.4
   chooses wafer-edge HBM on a latency argument (1 to 2 µs of host round trip
   against a 70 µs step). DS41-C2 prices it; the fallback is stated.
4. **The wafer pair is priced on an assumed link.** One crossing per token at
   an assumed 5 µs, swept 1 to 10 µs. On the roofline the wafer binds on its
   own collectives (159 µs of the 246 µs step), so the crossing is second
   order there; on the iso-node study it is 0.1 µs of a 70 µs step. Either way
   the number stays graded `assumed` until a part is sourced.
5. **The array's comparator advantage is small and its device count is
   large.** 51 reticles with Engram off-ROM, 84 with it on. If the routed ROM
   density lands below the N5 analytical value, the count rises and the array
   falls below parity; the plan reports that as the outcome of the controlled
   experiment, which is the point of running it.
6. **The candidate pool is a training-aware mechanism.** The Hierarchical
   Sparse Indexer is applied identically in training and inference, so an
   implementation that scored the full context on Reindex layers would be
   numerically different from the reference, not merely slower. WP-H's
   evidence document must show the mask is applied, not just that the
   arithmetic is exact.
7. **The checkpoint is 510 GB and this host cannot hold it.** DS41-S1 needs
   a host with the space and about 80 minutes of read time for the lock; the
   header-only inventory is enough for everything up to that gate and for
   nothing after it.
8. **The G1 board is bound to Qwen.** Adding a V4.1 ladder as a second
   binding is a change to `configs/gates/redesign_gates.json` and to
   `tools/check_redesign_gates.py`; the board must report both, and a V4.1
   rung must be able to fail on its own.

---

## 15. Non-goals and change control

Not in this plan: prefill and the causal-encoder-only path; the vision
encoder and projector; SWA Bounded Replay on the encoder side; DSpark
speculation as a first-release claim; the 1M context as an acceptance point; a
three-wafer build; DeepSeek-V4.1-Pro, which does not exist at this date; any
silicon, package or foundry claim.

Changes to the ABI go through an amendment: **AM-E10** (the four kinds, one
dtype and four numeric contracts of section 5) and **AM-R1** as already
proposed for `CLUSTER_N`. A change to a gate's definition goes through
`configs/gates/redesign_gates.json` with its test. A change to an assumed
value goes through `technology.json` with its grade and sweep. A number in
this document that stops matching its artifact is corrected in place with a
dated note, never silently.

---

## 16. Immediate next work

In order, and none of it waiting on the others' results:

1. WP-A: the Engram-in-HBM placement in the analytical model, so section 3.4
   cites a modelled row (one session).
2. WP-B: the release record, the committed configs, and the checkpoint source
   on a host with 600 GB free (one session plus the download).
3. WP-C and WP-D: the four kinds, one dtype, four contracts, the exporter, and
   the census-versus-inventory cross-check (two sessions).
4. WP-H first half: the oracle with the indexer and Engram wrapped, run on the
   prefix workload, measuring the KV widths (one GPU session).
5. WP-K: the five RTL blocks and their dual-simulator campaigns, which need
   only the sub-op definitions of WP-C (two sessions).

Everything else follows the dependency order of section 12.

---

## 17. Registration checklist

The seventeen places a target must appear, and which package lands each:
master plan section 3 (WP-P); ADR-003 section 3.3 (WP-P); model profile and
inventory (exists); checkpoint contract (WP-B); front end and IR (WP-D);
backend with `PROFILES` and a product name (WP-E, WP-F); capability (WP-E,
WP-F); cost table (WP-J, WP-M); topology class (AM-R1); workloads and oracle
(WP-I, WP-H); shipped-deployment pins (WP-J); schedule-check case (WP-E);
comparison contracts (WP-N); technology constants (exists); sources register
(exists, `SRC-DSV41-FLASH-*`); ledgers and index (WP-P); tests (every WP).
