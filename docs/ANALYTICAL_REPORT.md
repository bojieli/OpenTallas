# OpenTallas analytical report: ROM versus HBM decode

Date: 2026-09-23. This is the project's only analytical performance report. It
replaces every earlier analytical comparison: the iso-area, wafer-versus-array,
technical-direction, compute-in-ROM mechanism, per-region and first-principles
memory documents; the DeepSeek-V4.1 feasibility screens; the Qwen and HC1
screens; and the iso-node prose reports. All of those were deleted on this date.
Every number below is produced by `python3 tools/run_roofline_studies.py --force`
and bound to its artifact by a checked annotation. The results are analytical
projections, not silicon or workload measurements.

## 1. The two machines

**ROM machine (model-specific).** Weights are masked into ROM on reticle-class
dies at N5 or N6.

- **Packaging:** four dies share an interposer package over UCIe-class links.
  Packages connect to neighbours over direct SerDes links in a board mesh.
- **Link latency:** priced from hardware primitives with no software stack.
  About 10 ns per die-to-die hop (a UCIe PHY under 2 ns, on-die routing and
  flit synchronisation) and about 100 ns per package hop (SerDes, light FEC,
  flight time, a router stage). These are assumed and swept, not measured.
- **Expert storage:** each expert is striped across every read bank of a die,
  so a token's selected experts are read at the die's full rate rather than
  sweeping the whole array.
- **Layout:** the layout search can put one layer's tensor group inside one
  package and pipeline layers across packages. A ROM stage reads its own
  weights locally, so pipelining costs it no bandwidth. This is the layout
  most redesigned winners use.
- **Arithmetic:** either ROM storage feeding MAC arrays, which amortises a
  weight over a batch, or HC1-style compute-in-ROM (one select cell per ≤4-bit
  weight, no batch amortisation), with per-expert-region ports as a middle
  option.
- **KV cache:** on-die SRAM or attached HBM stacks.

**HBM machine (general-purpose, best shipping practice).** NVIDIA A100 (N7) or
B200 (4NP) on their published NVLink fabrics:

- the 8-GPU HGX baseboard, plus the 72-GPU NVL72 domain for Blackwell;
- InfiniBand scale-out;
- tensor, pipeline, hybrid and expert-parallel layouts, the last being
  DeepSeek's own serving layout (attention replicated per NVLink domain,
  experts sharded, dispatch and combine per layer);
- native checkpoint formats: FP4 experts and FP8 dense.

The GPU is not given specialised links. Those are a property of the
model-specific machine.

## 2. Method

- **Resources first.** Each design fixes dies, area split, capacity, rates and
  links; tokens/s follows. Both sides are swept over device count and layout at
  every silicon area.
- **One critical path per token, from the operator graph.** The service time a
  token waits for on the slots it visits is spread over the token's operator
  dependency graph by the bytes each operator reads; the step is that graph's
  longest path plus every pipeline hop, and never less than the sweep. See
  *Serial latency and collectives* below.
- **Each metric compared best against best.** Per-user speed against the GPU's
  fastest per-user layout; throughput and energy against its best throughput
  and best-energy layouts at the same silicon.
- **Energy per delivered token.** Static power over the step plus the dynamic
  energy of the users actually served.
- **Prefill.** Time to first token is priced for a prompt the length of the
  context: 8,192-token chunks, collectives paid per chunk.
- **Batch sweep.** 1 to 4,096 users. Designs hold KV for the largest batch
  within their die-edge limits.

**Validation gates:**

- **Taalas HC1** (815 mm², N6, 16,960 tokens/s on Llama-3.1-8B, self-reported by
  Taalas): modelled at **0.64×** <!-- figure: 0.64 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1.ratio" name="HC1 gate ratio" -->, inside the gate's 2× tolerance but now
  **below** the shipping part: it binds on the dependent-operator chain of the
  Llama decode graph priced with our own RTL depths, not on the array sweep.
  Across the serial inputs' stated ranges it lands at
  0.44× <!-- figure: 0.44 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1.detail.layer_fixed_latency_band.high.ratio_to_published" name="HC1 gate ratio, slow serial end" -->–0.77× <!-- figure: 0.77 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1.detail.layer_fixed_latency_band.low.ratio_to_published" name="HC1 gate ratio, fast serial end" -->, so the band no longer brackets the
  published rate. It was 1.45× under the flat per-layer floor. Nothing was
  tuned to move it back: HC1's hardwired datapath is serially faster than ours.
  The gate uses one select cell per ≤4-bit weight, a figure taken from the
  vendor's own description, so it is not independent on capacity.
- **A100 weight-bound gate:** exact arithmetic, **1.000×** <!-- figure: 1.000 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.a100_weight_bound.ratio" name="A100 gate ratio" -->.
- **HC1 card-power gate:** still fails at **0.31×** <!-- figure: 0.31 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.ratio" name="HC1 power gate ratio" -->, lower than before because
  the modelled part now makes fewer tokens per second. ROM energy may be
  understated by up to ~2.3×.

### Serial latency and collectives

Until this revision the serial part of every step was a flat floor of about
250 ns per layer (four array-pass boundaries, a barrier and a sequencer issue)
plus two all-reduces per layer. The bottom-up critical path of the machine we
actually build found both badly low, and the model now uses that machinery
(`src/opentallas/critical_path.py`) for every point of every study, on both
sides:

- **The operator graph.** One DAG per token, built from the model profile and
  the pinned `config.json` values in `configs/models/decode_graph_shapes.json`:
  GQA (Qwen3, Llama, MiMo's sliding-window and global layers with sinks),
  DeepSeek V4/V4.1 (4-copy hyper-connections with the 20-iteration Sinkhorn,
  compressed and sparse attention, the indexer and top-k, reuse layers, Engram,
  hash routing) and Kimi K3 (KDA recurrent layers, MLA, a latent MoE and block
  attention-residuals, the last two read structurally and flagged as such). A
  model whose structure is not stated is refused, not defaulted.
- **ROM nodes** are priced with the measured depths of our hardwired decode
  datapath (`rtl/hdc`, `technology.json` `serial_latency.rom_datapath`, graded
  `executed`) at the slowest routed clock. On V4.1 a plain layer's chain is
  about 5 µs, and its two Sinkhorn normalisation chains are the longest steps
  (227 µs of chain on the ×188 array's 40 layers at batch 1 <!-- figure: 227 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_array_x188.after.by_batch.1.chain_s" scale="1e6" name="V4.1 x188 chain us b1" -->).
- **GPU nodes** pay a published CUDA-graph launch gap (1.3 µs, band 0.5–2.1 µs)
  per dependent kernel and published FP32 latencies for in-kernel chains, so the
  comparison stays fair: the flat floor charged the GPU nothing for launches.
- **Every collective the weight split needs** is a graph node with its latency
  and its real payload: FP32 partial sums, the 4-copy hyper-connection residual
  at stage hops, gathered KV rows and top-k candidates. V4.1 under a tensor
  group needs 6.25 per layer <!-- figure: 6.25 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_array_x188.after.by_batch.1.collectives_per_layer" name="V4.1 collectives per layer" -->, not 2.
- **Topology is searched per point.** A hybrid layout tries every power-of-two
  tensor group and multiples of its domain, and on hardware links (UCIe, board
  and wafer SerDes, the on-wafer mesh) each collective takes the cheapest of
  two-step, one-shot, ring, recursive doubling, tree and centre-rooted mesh,
  hierarchically across link classes, each with a fixed summation order. NVLink
  and InfiniBand keep their measured small-message floor.

Before and after, N5 against B200 (the "before" column is frozen in
`results/roofline/critical_path/legacy_serial_model_targets.json` from commit
ae4d7487):

| Target | Fastest ROM, batch 1: before → after (tok/s/user) | Batch 64: before → after (tok/s/user) | Batch 64 aggregate: before → after | Fastest B200, batch 1: before → after | Chosen ROM topology at batch 1 (group, algorithm) |
|---|---:|---:|---:|---:|---|
| V4.1-Flash array ×188 (`array-hw-hybrid-x188`) | 15,556 → **4,176 <!-- figure: 4,176 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_array_x188.after.per_user_b1" name="V4.1-Flash array ×188 (`array-hw-hybrid-x188`) b1 after" -->** | 12,208 → **3,962 <!-- figure: 3,962 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_array_x188.after.per_user_b64" name="V4.1-Flash array ×188 (`array-hw-hybrid-x188`) b64 after" -->** | 781,337 → 253,550 <!-- figure: 253,550 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_array_x188.after.aggregate_b64" name="V4.1-Flash array ×188 (`array-hw-hybrid-x188`) b64 aggregate after" --> | -- | group 16 of the declared 4, 12 stages, hierarchical, one_shot |
| V4.1-Flash wafer ×12 (`wafer-hybrid-x12`) | 5,653 → **3,235 <!-- figure: 3,235 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_wafer_x12.after.per_user_b1" name="V4.1-Flash wafer ×12 (`wafer-hybrid-x12`) b1 after" -->** | 5,158 → **3,235 <!-- figure: 3,235 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_wafer_x12.after.per_user_b64" name="V4.1-Flash wafer ×12 (`wafer-hybrid-x12`) b64 after" -->** | 330,104 → 278,210 <!-- figure: 278,210 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_wafer_x12.after.aggregate_b64" name="V4.1-Flash wafer ×12 (`wafer-hybrid-x12`) b64 aggregate after" --> | -- | group 8 of the declared 57, 40 stages, one_shot |
| Qwen3-8B 8K | 42,248 → **11,207 <!-- figure: 11,207 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.qwen3_8b.after.fastest_rom_b1.per_user" name="Qwen3-8B 8K fastest ROM b1 after" -->** | 9,373 → **7,164 <!-- figure: 7,164 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.qwen3_8b.after.fastest_rom_b64.per_user" name="Qwen3-8B 8K fastest ROM b64 after" -->** | 796,702 → 458,470 <!-- figure: 458,470 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.qwen3_8b.after.fastest_rom_b64.aggregate" name="Qwen3-8B 8K fastest ROM b64 aggregate after" --> | 4,444 → 1,269 <!-- figure: 1,269 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.qwen3_8b.after.fastest_gpu_b1.per_user" name="Qwen3-8B 8K fastest GPU b1 after" --> | `ROM-N5-native-SRAMKV-array-hw-tensor-x8-perstream-romfill`: group 8, hierarchical |
| V4-Flash 200K | 18,119 → **3,374 <!-- figure: 3,374 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_flash.after.fastest_rom_b1.per_user" name="V4-Flash 200K fastest ROM b1 after" -->** | 13,829 → **3,252 <!-- figure: 3,252 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_flash.after.fastest_rom_b64.per_user" name="V4-Flash 200K fastest ROM b64 after" -->** | 1,175,496 → 276,379 <!-- figure: 276,379 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_flash.after.fastest_rom_b64.aggregate" name="V4-Flash 200K fastest ROM b64 aggregate after" --> | 3,972 → 608 <!-- figure: 608 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_flash.after.fastest_gpu_b1.per_user" name="V4-Flash 200K fastest GPU b1 after" --> | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56`: group 4, one_shot |
| V4-Pro 1M | 6,111 → **1,539 <!-- figure: 1,539 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_pro.after.fastest_rom_b1.per_user" name="V4-Pro 1M fastest ROM b1 after" -->** | 4,226 → **1,491 <!-- figure: 1,491 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_pro.after.fastest_rom_b64.per_user" name="V4-Pro 1M fastest ROM b64 after" -->** | 422,634 → 149,103 <!-- figure: 149,103 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_pro.after.fastest_rom_b64.aggregate" name="V4-Pro 1M fastest ROM b64 aggregate after" --> | 2,456 → 379 <!-- figure: 379 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v4_pro.after.fastest_gpu_b1.per_user" name="V4-Pro 1M fastest GPU b1 after" --> | `ROM-N5-native-SRAMKV-wafer-hybrid-x6`: group 8, one_shot |
| V4.1-Flash 200K | 15,556 → **4,179 <!-- figure: 4,179 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_flash.after.fastest_rom_b1.per_user" name="V4.1-Flash 200K fastest ROM b1 after" -->** | 13,436 → **4,056 <!-- figure: 4,056 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_flash.after.fastest_rom_b64.per_user" name="V4.1-Flash 200K fastest ROM b64 after" -->** | 859,906 → 267,680 <!-- figure: 267,680 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_flash.after.fastest_rom_b64.aggregate" name="V4.1-Flash 200K fastest ROM b64 aggregate after" --> | 4,257 → 706 <!-- figure: 706 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.deepseek_v41_flash.after.fastest_gpu_b1.per_user" name="V4.1-Flash 200K fastest GPU b1 after" --> | `ROM-N5-native-HBMKV-array-hw-hybrid-x176`: group 16, hierarchical, one_shot |
| Kimi-K3 200K | 3,580 → **1,436 <!-- figure: 1,436 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.kimi_k3.after.fastest_rom_b1.per_user" name="Kimi-K3 200K fastest ROM b1 after" -->** | 1,237 → **986 <!-- figure: 986 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.kimi_k3.after.fastest_rom_b64.per_user" name="Kimi-K3 200K fastest ROM b64 after" -->** | 79,191 → 63,091 <!-- figure: 63,091 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.kimi_k3.after.fastest_rom_b64.aggregate" name="Kimi-K3 200K fastest ROM b64 aggregate after" --> | 1,275 → 291 <!-- figure: 291 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.kimi_k3.after.fastest_gpu_b1.per_user" name="Kimi-K3 200K fastest GPU b1 after" --> | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395`: group 32, hierarchical |
| MiMo-V2.6-Pro 200K | 6,779 → **3,084 <!-- figure: 3,084 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_pro.after.fastest_rom_b1.per_user" name="MiMo-V2.6-Pro 200K fastest ROM b1 after" -->** | 1,480 → **1,099 <!-- figure: 1,099 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_pro.after.fastest_rom_b64.per_user" name="MiMo-V2.6-Pro 200K fastest ROM b64 after" -->** | 94,715 → 70,349 <!-- figure: 70,349 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_pro.after.fastest_rom_b64.aggregate" name="MiMo-V2.6-Pro 200K fastest ROM b64 aggregate after" --> | 2,120 → 504 <!-- figure: 504 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_pro.after.fastest_gpu_b1.per_user" name="MiMo-V2.6-Pro 200K fastest GPU b1 after" --> | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140`: group 32, hierarchical |
| MiMo-V2.6-Flash 200K | 13,762 → **5,432 <!-- figure: 5,432 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_flash.after.fastest_rom_b1.per_user" name="MiMo-V2.6-Flash 200K fastest ROM b1 after" -->** | 2,588 → **2,954 <!-- figure: 2,954 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_flash.after.fastest_rom_b64.per_user" name="MiMo-V2.6-Flash 200K fastest ROM b64 after" -->** | 219,956 → 189,038 <!-- figure: 189,038 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_flash.after.fastest_rom_b64.aggregate" name="MiMo-V2.6-Flash 200K fastest ROM b64 aggregate after" --> | 3,532 → 753 <!-- figure: 753 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.mimo_v26_flash.after.fastest_gpu_b1.per_user" name="MiMo-V2.6-Flash 200K fastest GPU b1 after" --> | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45`: group 16, hierarchical |
| Qwen3-8B on one HC1-class reticle | 24,222 → **9,260 <!-- figure: 9,260 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.qwen3_8b_single_reticle.after.per_user_b1" name="Qwen3-8B single reticle after" -->** | -- | -- | -- | single die, no collective |
| Taalas HC1 gate (Llama-3.1-8B) | 24,675 → **10,803 <!-- figure: 10,803 src="results/roofline/critical_path/decode_critical_path.json#before_after.targets.hc1_llama31_8b.after.per_user_b1" name="HC1 modelled after" -->** | -- | -- | -- | published 16,960 |

Every target loses a factor of two to five per user, and the GPU loses more (a
launch gap per dependent kernel), so most per-user ratios **rise**. The ×188
V4.1 array now prefers a 16-die tensor group at batch 1 and a 4-die group at
batch 64; one-shot reduction wins inside a package and hierarchical across
packages. The wafer prefers groups of 8 fields over its declared 57, because a
mesh collective across a whole wafer costs ~100 µs a token.

The candidate models against B200 at the same silicon:

| Model | Batch | ROM design | GPU design | ROM tok/s per user | GPU tok/s per user | Ratio |
|---|---:|---|---|---:|---:|---:|
| Kimi-K3 200K | 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x395` | `b200_sxm-x201-nvl72-hybrid` | 1,436 | 288 | **4.98×** | <!-- figure: 1,436 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#comparisons[rom_design=Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x395,batch_size=1].rom_per_user_tokens_s" name="Kimi-K3 200K b1 ROM rate" --> <!-- figure: 288 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#comparisons[rom_design=Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x395,batch_size=1].iso_area_gpu_per_user_tokens_s" name="Kimi-K3 200K b1 GPU rate" --> <!-- figure: 4.98 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#comparisons[rom_design=Kimi-K3/ROM-N5-native-SRAMKV-array-hw-hybrid-x395,batch_size=1].per_user_speed_ratio" name="Kimi-K3 200K b1 ratio" -->
| Kimi-K3 200K | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x396` | `b200_sxm-x202-nvl72-hybrid` | 582 | 198 | **2.95×** | <!-- figure: 582 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#comparisons[rom_design=Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396,batch_size=64].rom_per_user_tokens_s" name="Kimi-K3 200K b64 ROM rate" --> <!-- figure: 198 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#comparisons[rom_design=Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396,batch_size=64].iso_area_gpu_per_user_tokens_s" name="Kimi-K3 200K b64 GPU rate" --> <!-- figure: 2.95 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#comparisons[rom_design=Kimi-K3/ROM-N5-native-HBMKV-array-hw-hybrid-x396,batch_size=64].per_user_speed_ratio" name="Kimi-K3 200K b64 ratio" -->
| MiMo-V2.6-Pro 200K | 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x140` | `b200_sxm-x71-nvl72-tensor` | 3,084 | 504 | **6.12×** | <!-- figure: 3,084 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x140,batch_size=1].rom_per_user_tokens_s" name="MiMo-V2.6-Pro 200K b1 ROM rate" --> <!-- figure: 504 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x140,batch_size=1].iso_area_gpu_per_user_tokens_s" name="MiMo-V2.6-Pro 200K b1 GPU rate" --> <!-- figure: 6.12 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Pro/ROM-N5-native-SRAMKV-array-hw-hybrid-x140,batch_size=1].per_user_speed_ratio" name="MiMo-V2.6-Pro 200K b1 ratio" -->
| MiMo-V2.6-Pro 200K | 64 | `ROM-N5-native-HBMKV-wafer-hybrid-x49` | `b200_sxm-x1416-nvl72-hybrid` | 1,099 | 463 | **2.37×** | <!-- figure: 1,099 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x49,batch_size=64].rom_per_user_tokens_s" name="MiMo-V2.6-Pro 200K b64 ROM rate" --> <!-- figure: 463 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x49,batch_size=64].iso_area_gpu_per_user_tokens_s" name="MiMo-V2.6-Pro 200K b64 GPU rate" --> <!-- figure: 2.37 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x49,batch_size=64].per_user_speed_ratio" name="MiMo-V2.6-Pro 200K b64 ratio" -->
| MiMo-V2.6-Flash 200K | 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x45` | `b200_sxm-x23-nvl72-tensor` | 5,432 | 713 | **7.62×** | <!-- figure: 5,432 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x45,batch_size=1].rom_per_user_tokens_s" name="MiMo-V2.6-Flash 200K b1 ROM rate" --> <!-- figure: 713 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x45,batch_size=1].iso_area_gpu_per_user_tokens_s" name="MiMo-V2.6-Flash 200K b1 GPU rate" --> <!-- figure: 7.62 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x45,batch_size=1].per_user_speed_ratio" name="MiMo-V2.6-Flash 200K b1 ratio" -->
| MiMo-V2.6-Flash 200K | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x188-romfill` | `b200_sxm-x96-nvl72-hybrid` | 1,747 | 447 | **3.90×** | <!-- figure: 1,747 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188-romfill,batch_size=64].rom_per_user_tokens_s" name="MiMo-V2.6-Flash 200K b64 ROM rate" --> <!-- figure: 447 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188-romfill,batch_size=64].iso_area_gpu_per_user_tokens_s" name="MiMo-V2.6-Flash 200K b64 GPU rate" --> <!-- figure: 3.90 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#comparisons[rom_design=MiMo-V2.6-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188-romfill,batch_size=64].per_user_speed_ratio" name="MiMo-V2.6-Flash 200K b64 ratio" -->

| Model | Silicon | ROM best throughput (design, batch) | GPU best throughput (design, batch) | Throughput ratio | Best tokens/J ratio |
|---|---:|---|---|---:|---:|
| Kimi-K3 200K | 739,600 mm² | 152,114 (`ROM-N5-native-HBMKV-wafer-pipeline-x16-perstream-romfill`, 4,096) | 150,234 (`b200_sxm-x462-nvl72-hybrid`, 4,096) | **1.01×** | **3.16×** | <!-- figure: 1.01 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#capacity_comparison[model=Kimi-K3,silicon_area_mm2=739600.0].aggregate_ratio" name="Kimi-K3 200K best-vs-best throughput" --> <!-- figure: 3.16 src="results/roofline/candidates/kimi-k3/n5_vs_b200/analytical.json#capacity_comparison[model=Kimi-K3,silicon_area_mm2=739600.0].tokens_per_joule_ratio" name="Kimi-K3 200K best tokens per joule" -->
| MiMo-V2.6-Pro 200K | 2,265,000 mm² | 165,069 (`ROM-N5-native-HBMKV-wafer-pipeline-x49`, 4,096) | 405,650 (`b200_sxm-x1416-nvl72-hybrid`, 4,096) | **0.41×** | **2.45×** | <!-- figure: 0.41 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#capacity_comparison[model=MiMo-V2.6-Pro,silicon_area_mm2=2265000.0].aggregate_ratio" name="MiMo-V2.6-Pro 200K best-vs-best throughput" --> <!-- figure: 2.45 src="results/roofline/candidates/mimo-v26-pro/n5_vs_b200/analytical.json#capacity_comparison[model=MiMo-V2.6-Pro,silicon_area_mm2=44800.0].tokens_per_joule_ratio" name="MiMo-V2.6-Pro 200K best tokens per joule" -->
| MiMo-V2.6-Flash 200K | 306,400 mm² | 244,568 (`ROM-N5-native-HBMKV-array-hw-hybrid-x376-romfill`, 4,096) | 210,529 (`b200_sxm-x192-nvl72-hybrid`, 4,096) | **1.16×** | **7.34×** | <!-- figure: 1.16 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#capacity_comparison[model=MiMo-V2.6-Flash,silicon_area_mm2=306400.0].aggregate_ratio" name="MiMo-V2.6-Flash 200K best-vs-best throughput" --> <!-- figure: 7.34 src="results/roofline/candidates/mimo-v26-flash/n5_vs_b200/analytical.json#capacity_comparison[model=MiMo-V2.6-Flash,silicon_area_mm2=46200.0].tokens_per_joule_ratio" name="MiMo-V2.6-Flash 200K best tokens per joule" -->

## 3. Per-user decode speed, N5 ROM against B200 at the same silicon

Best ROM array against the GPU's fastest per-user design at the same area.

| Model | Batch | ROM design | GPU design | ROM tok/s per user | GPU tok/s per user | Ratio |
|---|---:|---|---|---:|---:|---:|
| V4.1-Flash 200K | 1 | `ROM-N5-native-HBMKV-array-hw-hybrid-x176` | `b200_sxm-x90-nvl72-hybrid` | 4,179 | 697 | **5.99×** | <!-- figure: 4,179 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176,batch_size=1].rom_per_user_tokens_s" name="V4.1-Flash 200K b1 ROM rate" --> <!-- figure: 697 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176,batch_size=1].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b1 GPU rate" --> <!-- figure: 5.99 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x176,batch_size=1].per_user_speed_ratio" name="V4.1-Flash 200K b1 ratio" -->
| V4.1-Flash 200K | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x132` | `b200_sxm-x67-hybrid` | 3,417 | 471 | **7.25×** | <!-- figure: 3,417 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x132,batch_size=64].rom_per_user_tokens_s" name="V4.1-Flash 200K b64 ROM rate" --> <!-- figure: 471 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x132,batch_size=64].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b64 GPU rate" --> <!-- figure: 7.25 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x132,batch_size=64].per_user_speed_ratio" name="V4.1-Flash 200K b64 ratio" -->
| V4.1-Flash 200K | 1,024 | `ROM-N5-native-HBMKV-array-hw-pipeline-x264` | `b200_sxm-x134-nvl72-hybrid` | 1,326 | 210 | **6.31×** | <!-- figure: 1,326 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x264,batch_size=1024].rom_per_user_tokens_s" name="V4.1-Flash 200K b1024 ROM rate" --> <!-- figure: 210 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x264,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b1024 GPU rate" --> <!-- figure: 6.31 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x264,batch_size=1024].per_user_speed_ratio" name="V4.1-Flash 200K b1024 ratio" -->
| V4.1-Flash 200K | 4,096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | `b200_sxm-x179-nvl72-hybrid` | 559 | 133 | **4.20×** | <!-- figure: 559 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x352,batch_size=4096].rom_per_user_tokens_s" name="V4.1-Flash 200K b4096 ROM rate" --> <!-- figure: 133 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x352,batch_size=4096].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b4096 GPU rate" --> <!-- figure: 4.20 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x352,batch_size=4096].per_user_speed_ratio" name="V4.1-Flash 200K b4096 ratio" -->
| V4-Flash 200K | 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x56` | `b200_sxm-x29-nvl72-tensor` | 3,374 | 600 | **5.63×** | <!-- figure: 3,374 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56,batch_size=1].rom_per_user_tokens_s" name="V4-Flash 200K b1 ROM rate" --> <!-- figure: 600 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56,batch_size=1].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b1 GPU rate" --> <!-- figure: 5.63 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x56,batch_size=1].per_user_speed_ratio" name="V4-Flash 200K b1 ratio" -->
| V4-Flash 200K | 64 | `ROM-N5-native-HBMKV-array-hw-pipeline-x56` | `b200_sxm-x29-hybrid` | 2,436 | 318 | **7.66×** | <!-- figure: 2,436 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56,batch_size=64].rom_per_user_tokens_s" name="V4-Flash 200K b64 ROM rate" --> <!-- figure: 318 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56,batch_size=64].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b64 GPU rate" --> <!-- figure: 7.66 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x56,batch_size=64].per_user_speed_ratio" name="V4-Flash 200K b64 ratio" -->
| V4-Flash 200K | 1,024 | `ROM-N5-native-HBMKV-array-hw-pipeline-x113` | `b200_sxm-x58-hybrid` | 694 | 103 | **6.75×** | <!-- figure: 694 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x113,batch_size=1024].rom_per_user_tokens_s" name="V4-Flash 200K b1024 ROM rate" --> <!-- figure: 103 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x113,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b1024 GPU rate" --> <!-- figure: 6.75 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x113,batch_size=1024].per_user_speed_ratio" name="V4-Flash 200K b1024 ratio" -->
| V4-Flash 200K | 4,096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x168` | `b200_sxm-x86-nvl72-hybrid` | 289 | 61 | **4.71×** | <!-- figure: 289 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x168,batch_size=4096].rom_per_user_tokens_s" name="V4-Flash 200K b4096 ROM rate" --> <!-- figure: 61 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x168,batch_size=4096].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b4096 GPU rate" --> <!-- figure: 4.71 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x168,batch_size=4096].per_user_speed_ratio" name="V4-Flash 200K b4096 ratio" -->
| V4-Pro 1M | 1 | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | `b200_sxm-x203-nvl72-hybrid` | 1,491 | 378 | **3.94×** | <!-- figure: 1,491 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=1].rom_per_user_tokens_s" name="V4-Pro 1M b1 ROM rate" --> <!-- figure: 378 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=1].iso_area_gpu_per_user_tokens_s" name="V4-Pro 1M b1 GPU rate" --> <!-- figure: 3.94 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=1].per_user_speed_ratio" name="V4-Pro 1M b1 ratio" -->
| V4-Pro 1M | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | `b200_sxm-x203-nvl72-hybrid` | 1,491 | 257 | **5.80×** | <!-- figure: 1,491 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=64].rom_per_user_tokens_s" name="V4-Pro 1M b64 ROM rate" --> <!-- figure: 257 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=64].iso_area_gpu_per_user_tokens_s" name="V4-Pro 1M b64 GPU rate" --> <!-- figure: 5.80 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=64].per_user_speed_ratio" name="V4-Pro 1M b64 ratio" -->
| V4-Pro 1M | 1,024 | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | `b200_sxm-x203-nvl72-hybrid` | 340 | 65 | **5.24×** | <!-- figure: 340 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399,batch_size=1024].rom_per_user_tokens_s" name="V4-Pro 1M b1024 ROM rate" --> <!-- figure: 65 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="V4-Pro 1M b1024 GPU rate" --> <!-- figure: 5.24 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399,batch_size=1024].per_user_speed_ratio" name="V4-Pro 1M b1024 ratio" -->
| Qwen3-8B 8K | 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill` | `b200_sxm-x8-tensor` | 10,793 | 944 | **11.44×** | <!-- figure: 10,793 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill,batch_size=1].rom_per_user_tokens_s" name="Qwen3-8B 8K b1 ROM rate" --> <!-- figure: 944 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill,batch_size=1].iso_area_gpu_per_user_tokens_s" name="Qwen3-8B 8K b1 GPU rate" --> <!-- figure: 11.44 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x16-romfill,batch_size=1].per_user_speed_ratio" name="Qwen3-8B 8K b1 ratio" -->
| Qwen3-8B 8K | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill` | `b200_sxm-x25-nvl72-tensor` | 1,832 | 679 | **2.70×** | <!-- figure: 1,832 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill,batch_size=64].rom_per_user_tokens_s" name="Qwen3-8B 8K b64 ROM rate" --> <!-- figure: 679 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill,batch_size=64].iso_area_gpu_per_user_tokens_s" name="Qwen3-8B 8K b64 GPU rate" --> <!-- figure: 2.70 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill,batch_size=64].per_user_speed_ratio" name="Qwen3-8B 8K b64 ratio" -->
| Qwen3-8B 8K | 1,024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill` | `b200_sxm-x25-hybrid` | 116 | 106 | **1.09×** | <!-- figure: 116 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill,batch_size=1024].rom_per_user_tokens_s" name="Qwen3-8B 8K b1024 ROM rate" --> <!-- figure: 106 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="Qwen3-8B 8K b1024 GPU rate" --> <!-- figure: 1.09 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x49-romfill,batch_size=1024].per_user_speed_ratio" name="Qwen3-8B 8K b1024 ratio" -->

## 4. Each side at its best, N5 against B200

Best throughput and best tokens per joule over every design and batch at the
same silicon (maximum over areas).

| Model | Silicon | ROM best throughput (design, batch) | GPU best throughput (design, batch) | Throughput ratio | Best tokens/J ratio |
|---|---:|---|---|---:|---:|
| V4.1-Flash 200K | 554,700 mm² | 2,745,533 (`ROM-N5-native-HBMKV-wafer-hybrid-x12`, 4,096) | 653,528 (`b200_sxm-x347-nvl72-hybrid`, 4,096) | **4.20×** | **12.32×** | <!-- figure: 4.20 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=554700.0].aggregate_ratio" name="V4.1-Flash 200K best-vs-best throughput" --> <!-- figure: 12.32 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=554700.0].tokens_per_joule_ratio" name="V4.1-Flash 200K best tokens per joule" -->
| V4-Flash 200K | 277,100 mm² | 1,411,894 (`ROM-N5-native-HBMKV-array-hw-hybrid-x340`, 4,096) | 359,087 (`b200_sxm-x173-nvl72-hybrid`, 4,096) | **3.93×** | **7.96×** | <!-- figure: 3.93 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=277100.0].aggregate_ratio" name="V4-Flash 200K best-vs-best throughput" --> <!-- figure: 7.96 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=44800.0].tokens_per_joule_ratio" name="V4-Flash 200K best tokens per joule" -->
| V4-Pro 1M | 2,172,600 mm² | 690,484 (`ROM-N5-native-HBMKV-wafer-pipeline-x47`, 4,096) | 377,095 (`b200_sxm-x1358-nvl72-hybrid`, 4,096) | **1.83×** | **8.91×** | <!-- figure: 1.83 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=2172600.0].aggregate_ratio" name="V4-Pro 1M best-vs-best throughput" --> <!-- figure: 8.91 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=325200.0].tokens_per_joule_ratio" name="V4-Pro 1M best tokens per joule" -->
| Qwen3-8B 8K | 277,100 mm² | 823,812 (`ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill`, 4,096) | 682,398 (`b200_sxm-x173-nvl72-hybrid`, 4,096) | **1.21×** | **9.07×** | <!-- figure: 1.21 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=277100.0].aggregate_ratio" name="Qwen3-8B 8K best-vs-best throughput" --> <!-- figure: 9.07 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=1600.0].tokens_per_joule_ratio" name="Qwen3-8B 8K best tokens per joule" -->

## 5. Against the A100 (N6 ROM)

The same comparison one generation earlier is uniformly more favourable to ROM:

| Model | ROM per user, batch 1 | ROM per user, batch 64 | Best throughput | Best tokens/J |
|---|---:|---:|---:|---:|
| V4.1-Flash 200K | 11.56× | 12.34× | 10.41× | 23.47× | <!-- figure: 11.56 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x261,batch_size=1].per_user_speed_ratio" name="V4.1-Flash 200K b1 ratio N6" --> <!-- figure: 12.34 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x205-romfill,batch_size=64].per_user_speed_ratio" name="V4.1-Flash 200K b64 ratio N6" --> <!-- figure: 10.41 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=554700.0].aggregate_ratio" name="V4.1-Flash 200K best-vs-best throughput N6" --> <!-- figure: 23.47 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=554700.0].tokens_per_joule_ratio" name="V4.1-Flash 200K best tokens per joule N6" -->
| V4-Flash 200K | 9.82× | 11.68× | 8.33× | 9.88× | <!-- figure: 9.82 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N6-native-SRAMKV-array-hw-hybrid-x79,batch_size=1].per_user_speed_ratio" name="V4-Flash 200K b1 ratio N6" --> <!-- figure: 11.68 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x79,batch_size=64].per_user_speed_ratio" name="V4-Flash 200K b64 ratio N6" --> <!-- figure: 8.33 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=277100.0].aggregate_ratio" name="V4-Flash 200K best-vs-best throughput N6" --> <!-- figure: 9.88 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=277100.0].tokens_per_joule_ratio" name="V4-Flash 200K best tokens per joule N6" -->
| V4-Pro 1M | 9.35× | 6.41× | 1.89× | 6.08× | <!-- figure: 9.35 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x389,batch_size=1].per_user_speed_ratio" name="V4-Pro 1M b1 ratio N6" --> <!-- figure: 6.41 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x66,batch_size=64].per_user_speed_ratio" name="V4-Pro 1M b64 ratio N6" --> <!-- figure: 1.89 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=3050800.0].aggregate_ratio" name="V4-Pro 1M best-vs-best throughput N6" --> <!-- figure: 6.08 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=3050800.0].tokens_per_joule_ratio" name="V4-Pro 1M best tokens per joule N6" -->
| Qwen3-8B 8K | 22.87× | 3.89× | 1.42× | 9.54× | <!-- figure: 22.87 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x16-romfill,batch_size=1].per_user_speed_ratio" name="Qwen3-8B 8K b1 ratio N6" --> <!-- figure: 3.89 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x69,batch_size=64].per_user_speed_ratio" name="Qwen3-8B 8K b64 ratio N6" --> <!-- figure: 1.42 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=277100.0].aggregate_ratio" name="Qwen3-8B 8K best-vs-best throughput N6" --> <!-- figure: 9.54 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=3300.0].tokens_per_joule_ratio" name="Qwen3-8B 8K best tokens per joule N6" -->

## 6. Where the advantage comes from

The ROM design has two separable advantages, and the serial-latency model
changes their balance:

- **Weights in ROM.** An HBM step must read the union of every user's experts;
  a ROM weight never moves. This is what keeps ROM per-user speed nearly flat
  from batch 1 to 64 on the MoE models (section 3), while the GPU's falls.
- **Specialisation of the fabric and the datapath.** Hardware-limited links,
  striped expert banks and a layer-per-package pipeline still matter, but once
  the serial path is priced from the operator graph the dependent-operator
  chain, not the link, dominates the batch-1 step on every ROM design: V4.1's
  hyper-connection Sinkhorn, KDA's state update and the per-layer norms and
  top-k selections. The next gain is a shorter chain (a faster divider, fused
  norms), not a faster fabric.

Two things still limit the ratio:

- **Throughput at each side's best** (section 4) is set by arithmetic at
  thousands of users, where ROM dies spend area on storage that GPUs spend on
  multipliers.
- **KV-bound regimes narrow or reverse the advantage.** Dense-KV Qwen at 1,000+
  users, Kimi-K3 and MiMo-Pro beyond ~1,000 users are examples: ROM does not
  help KV reads.

## 7. Sweet spots

1. **Single-user latency on any model.** Several-fold for DeepSeek-class MoE
   and for Kimi-K3 and MiMo, and an order of magnitude for an 8B dense model
   (section 3 and the candidate table above).
2. **Interactive multi-user MoE serving, tens to hundreds of users.** The ROM
   keeps per-user speed while the GPU's expert reads grow with the batch.
3. **Energy per token** (section 4): the GPU now also pays its launch gaps in
   static power.
4. **Weak spots:**
   - dense-KV and large-KV serving at high concurrency;
   - maximum-throughput batch serving on the largest models;
   - ROM wafers, whose mesh collectives trail the packaged array.

## 8. Open limits

- ROM read bandwidth rests on a simulated 28 nm CIM macro scaled to N5.
- Striped expert banks need deep banks and muxing that no N5 macro qualifies.
  Their address map and stream schedule are now simulated in RTL
  (`rtl/rom/ot_rom_striped_expert_reader.sv`,
  `python3 tools/rtl_rom_striped_bank_campaign.py`). Across 56 scoreboarded
  runs, six selected experts take a constant 52 cycles striped, <!-- figure: 52 src="results/rtl/rom_striped_bank_campaign.json#striped_cycles_six_experts[0]" name="striped six-expert cycles" -->
  and dedicated banks take up to 7.46× as long on a concentrated route. <!-- figure: 7.46 src="results/rtl/rom_striped_bank_campaign.json#worst_dedicated_over_striped" name="dedicated over striped worst" -->
  That is functional evidence for the schedule, not for macro area, timing or
  energy.
- All ROM link latencies are hardware-floor estimates. The digital part of a
  package hop is now simulated in RTL (`rtl/rom/ot_rom_pkg_link.sv`,
  `python3 tools/rtl_rom_pkg_link_campaign.py`): cut-through forwarding with
  credits costs 5 cycles of framing, <!-- figure: 5 src="results/rtl/rom_pkg_link_campaign.json#digital_endpoint_cycles" name="link digital endpoint cycles" -->
  and one user's hidden state arrives 70 ns after it is sent with a 60-cycle PHY, <!-- figure: 70 src="results/rtl/rom_pkg_link_campaign.json#one_user_hidden_state_latency_ns" name="link one-user latency" -->
  with no loss under random back-pressure. So the ~100 ns per hop assumed above
  leaves about 95 ns for SerDes, FEC and flight, which remains unmeasured.
- The ROM power model reads HC1 low.
- Hot-expert skew is uniform-random plus a derate for ROM; the GPU is assumed to
  replicate hot experts.
- Speculative decoding is a separate study (`results/roofline/speculative/`).
- Mask cost and model churn are outside the model.
- Before any claim: test ROM bank striping, link latency and power in RTL and
  physical design (the next phase).

## 9. Implementation status: the three mechanisms in RTL

The report credits the ROM machine with three specialisations. Each now has a
functional RTL model, a scoreboarded Icarus simulation, a Verilator lint and a
campaign record under `results/rtl/`:

1. **Striped expert banks** (`ot_rom_striped_expert_reader`,
   `rom_striped_bank_campaign.json`). A token's selected experts are read at the
   full bank rate, with no bank conflicts, in any selection.
2. **Package links** (`ot_rom_pkg_link`, `rom_pkg_link_campaign.json`).
   Cut-through with credits and 5 cycles of digital framing; the PHY is a
   delay-line stand-in. On ASAP7 it routes at 1,339 MHz <!-- figure: 1339 src="results/physical_abi3/asap7/rom_pkg_link/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="link routed Fmax MHz" -->
   (64-byte flits, 16 credits). Setup timing is met at 1 GHz. The one open item
   is 58 max-slew violations from the flop-built receive buffer, which belongs
   in an SRAM macro. Routing first found the buffer's read mux as the critical
   path at 919 MHz; the registered output that fixed it costs one cycle.
3. **Layer-per-package pipeline** (`ot_rom_layer_stage`,
   `rom_layer_pipeline_campaign.json`). Four packages joined by links carry
   eight users' tokens, and every final hidden state matches a reference model.
   - The first token takes 550 cycles, <!-- figure: 550 src="results/rtl/rom_layer_pipeline_campaign.json#first_token_latency_cycles" name="pipeline first-token latency" -->
     which is four stage services plus five hops, as the framework's latency
     law says.
   - Later tokens leave every 56 cycles, one stage's service. <!-- figure: 56 src="results/rtl/rom_layer_pipeline_campaign.json#stage_service_cycles" name="pipeline stage service" -->
   - About ten users are in flight with no per-user slowdown.

These are functional and cycle-structure models only. The router and the
arithmetic in the pipeline are stated stand-ins. None of them establishes
macro area, timing closure, PHY latency or energy, and they are not yet part of
the ABI 3.0 token path.

### A per-token decode core in RTL

Section 6 attributes most of the ROM machine's gain to specialisation. The
hardwired decode core (`rtl/hdc/`, plan and iteration log in
[TOKEN_PIPELINE_OPTIMIZATION_PLAN.md](TOKEN_PIPELINE_OPTIMIZATION_PLAN.md)) is
that specialisation, taken to one token of the reduced Qwen3 vehicle.

- A static program drives two fully pipelined units: a 64-lane matrix engine
  and a stream unit with exp, reciprocal, rsqrt and sigmoid pipelines.
  Element-level chaining replaces most barriers.
- In Verilator it decodes a token in 32,196 cycles, <!-- figure: 32196 src="results/rtl/hdc_decode_campaign.json#single_step.cycles" name="HDC cycles per token" -->
  with every logit, the vector memory and the KV cache bit-exact against a
  golden model.
- From an empty KV cache it consumes the 16-token prompt and generates the
  torch oracle's three tokens.
- On ASAP7 the stream unit routes at 1,111 MHz. <!-- figure: 1111 src="results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json#place_and_route.metrics.fmax_hz" scale="1e-6" name="HDC stream unit routed fmax MHz" -->

The same vehicle takes 7.9 M cycles on the general ABI 3.0 token path, whose
slowest blocks route at 58–75 MHz.

## 10. Reproduce

```
python3 tools/run_roofline_studies.py --force   # several hours serially; --no-candidates and --candidates split it
python3 tools/rtl_rom_striped_bank_campaign.py  # section 9, seconds each
python3 tools/rtl_rom_pkg_link_campaign.py
python3 tools/rtl_rom_layer_pipeline_campaign.py
python3 tools/rtl_hdc_decode_campaign.py       # decode core, ~3 min
python3 tools/check_prose_figures.py            # every annotated figure above
```
