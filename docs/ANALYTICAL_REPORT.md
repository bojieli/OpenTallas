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
- **One critical path per token.** Service time on the slots a token visits,
  plus every collective and pipeline hop, plus a per-layer serial floor.
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
  Taalas): modelled at **1.45×** <!-- figure: 1.45 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1.ratio" name="HC1 gate ratio" -->. Its latency band brackets the published
  rate. The gate uses one select cell per ≤4-bit weight, a figure taken from the
  vendor's own description, so it is not independent on capacity.
- **A100 weight-bound gate:** exact arithmetic, **1.000×** <!-- figure: 1.000 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.a100_weight_bound.ratio" name="A100 gate ratio" -->.
- **HC1 card-power gate:** still fails at **0.44×** <!-- figure: 0.44 src="results/roofline/n6_vs_a100/analytical.json#validation_gates.taalas_hc1_card_power.ratio" name="HC1 power gate ratio" -->. ROM energy may be
  understated by up to ~2.3×.

## 3. Per-user decode speed, N5 ROM against B200 at the same silicon

Best ROM array against the GPU's fastest per-user design at the same area.

| Model | Batch | ROM design | GPU design | ROM tok/s per user | GPU tok/s per user | Ratio |
|---|---:|---|---|---:|---:|---:|
| V4.1-Flash 200K | 1 | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | `b200_sxm-x96-nvl72-hybrid` | 15,556 | 4,015 | **3.87×** | <!-- figure: 15,556 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188,batch_size=1].rom_per_user_tokens_s" name="V4.1-Flash 200K b1 ROM rate" --> <!-- figure: 4,015 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188,batch_size=1].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b1 GPU rate" --> <!-- figure: 3.87 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188,batch_size=1].per_user_speed_ratio" name="V4.1-Flash 200K b1 ratio" -->
| V4.1-Flash 200K | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x188` | `b200_sxm-x96-nvl72-hybrid` | 12,208 | 1,432 | **8.52×** | <!-- figure: 12,208 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188,batch_size=64].rom_per_user_tokens_s" name="V4.1-Flash 200K b64 ROM rate" --> <!-- figure: 1,432 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188,batch_size=64].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b64 GPU rate" --> <!-- figure: 8.52 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188,batch_size=64].per_user_speed_ratio" name="V4.1-Flash 200K b64 ratio" -->
| V4.1-Flash 200K | 1,024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x352` | `b200_sxm-x179-expert` | 2,381 | 484 | **4.92×** | <!-- figure: 2,381 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x352,batch_size=1024].rom_per_user_tokens_s" name="V4.1-Flash 200K b1024 ROM rate" --> <!-- figure: 484 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x352,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b1024 GPU rate" --> <!-- figure: 4.92 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x352,batch_size=1024].per_user_speed_ratio" name="V4.1-Flash 200K b1024 ratio" -->
| V4.1-Flash 200K | 4,096 | `ROM-N5-native-HBMKV-array-hw-pipeline-x352` | `b200_sxm-x179-expert` | 625 | 235 | **2.66×** | <!-- figure: 625 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x352,batch_size=4096].rom_per_user_tokens_s" name="V4.1-Flash 200K b4096 ROM rate" --> <!-- figure: 235 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x352,batch_size=4096].iso_area_gpu_per_user_tokens_s" name="V4.1-Flash 200K b4096 GPU rate" --> <!-- figure: 2.66 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-pipeline-x352,batch_size=4096].per_user_speed_ratio" name="V4.1-Flash 200K b4096 ratio" -->
| V4-Flash 200K | 1 | `ROM-N5-native-SRAMKV-array-hw-hybrid-x59` | `b200_sxm-x30-nvl72-tensor` | 18,119 | 3,566 | **5.08×** | <!-- figure: 18,119 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x59,batch_size=1].rom_per_user_tokens_s" name="V4-Flash 200K b1 ROM rate" --> <!-- figure: 3,566 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x59,batch_size=1].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b1 GPU rate" --> <!-- figure: 5.08 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-SRAMKV-array-hw-hybrid-x59,batch_size=1].per_user_speed_ratio" name="V4-Flash 200K b1 ratio" -->
| V4-Flash 200K | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x84` | `b200_sxm-x43-nvl72-tensor` | 8,204 | 1,138 | **7.21×** | <!-- figure: 8,204 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x84,batch_size=64].rom_per_user_tokens_s" name="V4-Flash 200K b64 ROM rate" --> <!-- figure: 1,138 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x84,batch_size=64].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b64 GPU rate" --> <!-- figure: 7.21 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x84,batch_size=64].per_user_speed_ratio" name="V4-Flash 200K b64 ratio" -->
| V4-Flash 200K | 1,024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x170` | `b200_sxm-x87-nvl72-hybrid` | 1,319 | 382 | **3.45×** | <!-- figure: 1,319 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170,batch_size=1024].rom_per_user_tokens_s" name="V4-Flash 200K b1024 ROM rate" --> <!-- figure: 382 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b1024 GPU rate" --> <!-- figure: 3.45 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x170,batch_size=1024].per_user_speed_ratio" name="V4-Flash 200K b1024 ratio" -->
| V4-Flash 200K | 4,096 | `ROM-N5-native-HBMKV-array-hw-hybrid-x224` | `b200_sxm-x114-hybrid` | 434 | 158 | **2.75×** | <!-- figure: 434 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x224,batch_size=4096].rom_per_user_tokens_s" name="V4-Flash 200K b4096 ROM rate" --> <!-- figure: 158 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x224,batch_size=4096].iso_area_gpu_per_user_tokens_s" name="V4-Flash 200K b4096 GPU rate" --> <!-- figure: 2.75 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x224,batch_size=4096].per_user_speed_ratio" name="V4-Flash 200K b4096 ratio" -->
| V4-Pro 1M | 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x184` | `b200_sxm-x94-nvl72-hybrid` | 5,064 | 2,193 | **2.31×** | <!-- figure: 5,064 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x184,batch_size=1].rom_per_user_tokens_s" name="V4-Pro 1M b1 ROM rate" --> <!-- figure: 2,193 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x184,batch_size=1].iso_area_gpu_per_user_tokens_s" name="V4-Pro 1M b1 GPU rate" --> <!-- figure: 2.31 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-SRAMKV-array-hw-tensor-x184,batch_size=1].per_user_speed_ratio" name="V4-Pro 1M b1 ratio" -->
| V4-Pro 1M | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x399` | `b200_sxm-x203-nvl72-hybrid` | 4,226 | 867 | **4.87×** | <!-- figure: 4,226 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=64].rom_per_user_tokens_s" name="V4-Pro 1M b64 ROM rate" --> <!-- figure: 867 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=64].iso_area_gpu_per_user_tokens_s" name="V4-Pro 1M b64 GPU rate" --> <!-- figure: 4.87 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-hybrid-x399,batch_size=64].per_user_speed_ratio" name="V4-Pro 1M b64 ratio" -->
| V4-Pro 1M | 1,024 | `ROM-N5-native-HBMKV-array-hw-pipeline-x399` | `b200_sxm-x203-nvl72-hybrid` | 463 | 163 | **2.83×** | <!-- figure: 463 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399,batch_size=1024].rom_per_user_tokens_s" name="V4-Pro 1M b1024 ROM rate" --> <!-- figure: 163 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="V4-Pro 1M b1024 GPU rate" --> <!-- figure: 2.83 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N5-native-HBMKV-array-hw-pipeline-x399,batch_size=1024].per_user_speed_ratio" name="V4-Pro 1M b1024 ratio" -->
| Qwen3-8B 8K | 1 | `ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill` | `b200_sxm-x3-tensor` | 18,588 | 979 | **18.99×** | <!-- figure: 18,588 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill,batch_size=1].rom_per_user_tokens_s" name="Qwen3-8B 8K b1 ROM rate" --> <!-- figure: 979 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill,batch_size=1].iso_area_gpu_per_user_tokens_s" name="Qwen3-8B 8K b1 GPU rate" --> <!-- figure: 18.99 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x6-romfill,batch_size=1].per_user_speed_ratio" name="Qwen3-8B 8K b1 ratio" -->
| Qwen3-8B 8K | 64 | `ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill` | `b200_sxm-x116-nvl72-hybrid` | 8,343 | 2,551 | **3.27×** | <!-- figure: 8,343 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill,batch_size=64].rom_per_user_tokens_s" name="Qwen3-8B 8K b64 ROM rate" --> <!-- figure: 2,551 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill,batch_size=64].iso_area_gpu_per_user_tokens_s" name="Qwen3-8B 8K b64 GPU rate" --> <!-- figure: 3.27 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x227-romfill,batch_size=64].per_user_speed_ratio" name="Qwen3-8B 8K b64 ratio" -->
| Qwen3-8B 8K | 1,024 | `ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill` | `b200_sxm-x173-hybrid` | 803 | 537 | **1.50×** | <!-- figure: 803 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill,batch_size=1024].rom_per_user_tokens_s" name="Qwen3-8B 8K b1024 ROM rate" --> <!-- figure: 537 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill,batch_size=1024].iso_area_gpu_per_user_tokens_s" name="Qwen3-8B 8K b1024 GPU rate" --> <!-- figure: 1.50 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hw-hybrid-x340-romfill,batch_size=1024].per_user_speed_ratio" name="Qwen3-8B 8K b1024 ratio" -->
| Qwen3-8B 8K | 4,096 | `ROM-N5-native-HBMKV-array-hybrid-x340-romfill` | `b200_sxm-x173-hybrid` | 201 | 170 | **1.19×** | <!-- figure: 201 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill,batch_size=4096].rom_per_user_tokens_s" name="Qwen3-8B 8K b4096 ROM rate" --> <!-- figure: 170 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill,batch_size=4096].iso_area_gpu_per_user_tokens_s" name="Qwen3-8B 8K b4096 GPU rate" --> <!-- figure: 1.19 src="results/roofline/n5_vs_b200/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N5-native-HBMKV-array-hybrid-x340-romfill,batch_size=4096].per_user_speed_ratio" name="Qwen3-8B 8K b4096 ratio" -->

## 4. Each side at its best, N5 against B200

Best throughput and best tokens per joule over every design and batch at the
same silicon (maximum over areas).

| Model | Silicon | ROM best throughput (design, batch) | GPU best throughput (design, batch) | Throughput ratio | Best tokens/J ratio |
|---|---:|---|---|---:|---:|
| V4.1-Flash 200K | 554,700 mm² | 4,954,943 (`ROM-N5-native-HBMKV-wafer-hybrid-x12`, 4,096) | 1,555,927 (`b200_sxm-x347-expert`, 4,096) | **3.18×** | **3.97×** | <!-- figure: 3.18 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=554700.0].aggregate_ratio" name="V4.1-Flash 200K best-vs-best throughput" --> <!-- figure: 3.97 src="results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=60300.0].tokens_per_joule_ratio" name="V4.1-Flash 200K best tokens per joule" -->
| V4-Flash 200K | 182,600 mm² | 1,800,830 (`ROM-N5-native-HBMKV-array-hw-hybrid-x227`, 4,096) | 655,138 (`b200_sxm-x116-hybrid`, 4,096) | **2.75×** | **3.15×** | <!-- figure: 2.75 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=182600.0].aggregate_ratio" name="V4-Flash 200K best-vs-best throughput" --> <!-- figure: 3.15 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=45600.0].tokens_per_joule_ratio" name="V4-Flash 200K best tokens per joule" -->
| V4-Pro 1M | 325,200 mm² | 545,111 (`ROM-N5-native-HBMKV-array-hw-hybrid-x399-perregion-romfill`, 4,096) | 167,368 (`b200_sxm-x203-nvl72-hybrid`, 1,024) | **3.26×** | **3.57×** | <!-- figure: 3.26 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=325200.0].aggregate_ratio" name="V4-Pro 1M best-vs-best throughput" --> <!-- figure: 3.57 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=92400.0].tokens_per_joule_ratio" name="V4-Pro 1M best tokens per joule" -->
| Qwen3-8B 8K | 1,600 mm² | 21,379 (`ROM-N5-native-SRAMKV-array-hw-tensor-x2-perstream`, 1) | 4,142 (`b200_sxm-x1`, 64) | **5.16×** | **13.41×** | <!-- figure: 5.16 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=1600.0].aggregate_ratio" name="Qwen3-8B 8K best-vs-best throughput" --> <!-- figure: 13.41 src="results/roofline/n5_vs_b200/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=1600.0].tokens_per_joule_ratio" name="Qwen3-8B 8K best tokens per joule" -->

## 5. Against the A100 (N6 ROM)

The same comparison one generation earlier is uniformly more favourable to ROM:

| Model | ROM per user, batch 1 | ROM per user, batch 64 | Best throughput | Best tokens/J |
|---|---:|---:|---:|---:|
| V4.1-Flash 200K | 11.94× | 21.86× | 5.15× | 5.80× | <!-- figure: 11.94 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340,batch_size=1].per_user_speed_ratio" name="N6 V4.1-Flash 200K b1 ratio" --> <!-- figure: 21.86 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#comparisons[rom_design=DeepSeek-V4.1-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x264,batch_size=64].per_user_speed_ratio" name="N6 V4.1-Flash 200K b64 ratio" --> <!-- figure: 5.15 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=54600.0].aggregate_ratio" name="N6 V4.1-Flash 200K throughput" --> <!-- figure: 5.80 src="results/roofline/candidates/deepseek-v41-flash/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4.1-Flash,silicon_area_mm2=49700.0].tokens_per_joule_ratio" name="N6 V4.1-Flash 200K tokens per joule" -->
| V4-Flash 200K | 13.45× | 18.55× | 3.26× | 4.53× | <!-- figure: 13.45 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x340-romfill,batch_size=1].per_user_speed_ratio" name="N6 V4-Flash 200K b1 ratio" --> <!-- figure: 18.55 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=DSV4-Flash/ROM-N6-native-HBMKV-array-hw-hybrid-x119,batch_size=64].per_user_speed_ratio" name="N6 V4-Flash 200K b64 ratio" --> <!-- figure: 3.26 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=277100.0].aggregate_ratio" name="N6 V4-Flash 200K throughput" --> <!-- figure: 4.53 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Flash-0731,silicon_area_mm2=46200.0].tokens_per_joule_ratio" name="N6 V4-Flash 200K tokens per joule" -->
| V4-Pro 1M | 7.08× | — | 0.85× | 1.80× | <!-- figure: 7.08 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=DSV4-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x343-romfill,batch_size=1].per_user_speed_ratio" name="N6 V4-Pro 1M b1 ratio" --> <!-- figure: 0.85 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=3050800.0].aggregate_ratio" name="N6 V4-Pro 1M throughput" --> <!-- figure: 1.80 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=DeepSeek-V4-Pro-0813,silicon_area_mm2=92400.0].tokens_per_joule_ratio" name="N6 V4-Pro 1M tokens per joule" -->
| Qwen3-8B 8K | 34.48× | 9.13× | 7.89× | 15.05× | <!-- figure: 34.48 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x11-romfill,batch_size=1].per_user_speed_ratio" name="N6 Qwen3-8B 8K b1 ratio" --> <!-- figure: 9.13 src="results/roofline/n6_vs_a100/analytical.json#comparisons[rom_design=Qwen3-8B/ROM-N6-native-HBMKV-array-hw-hybrid-x276-romfill,batch_size=64].per_user_speed_ratio" name="N6 Qwen3-8B 8K b64 ratio" --> <!-- figure: 7.89 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=3300.0].aggregate_ratio" name="N6 Qwen3-8B 8K throughput" --> <!-- figure: 15.05 src="results/roofline/n6_vs_a100/analytical.json#capacity_comparison[model=Qwen3-8B,silicon_area_mm2=3300.0].tokens_per_joule_ratio" name="N6 Qwen3-8B 8K tokens per joule" -->

## 6. Where the advantage comes from

The ROM design has two separable advantages. Take DeepSeek-V4.1-Flash, best
design at any area:

- **Weights in ROM.** With the GPU's own NVLink/InfiniBand, a ROM array gives
  3,943 tokens/s per user against 4,257 for B200 on NVL72: parity for one user.
  With 64 users it keeps 3,943 while the GPU falls to 2,544 (**1.55×**). An HBM
  step must read the union of every user's experts; a ROM weight never moves.
- **Specialisation.** Hardware-limited links, striped expert banks and a
  layer-per-package pipeline raise the same ROM machine to **15,556** tokens/s
  (13,436 at 64 users). Link time per token falls from 51 µs to 6 µs; B200 on
  NVL72 still spends ~195 µs.

For Qwen3-8B the first advantage alone is already 3.2× for one user, because the
model fits a handful of chips and the GPU is weight-bandwidth bound. The
specialised design reaches ~42,000 tokens/s per user on four dies with
compute-in-ROM.

Two things limit the ratio:

- **Throughput at each side's best stays near 3×** (2.8–3.3× on DeepSeek at N5).
  At thousands of users both machines become arithmetic-bound, and ROM dies
  spend area on storage that GPUs spend on multipliers.
- **KV-bound regimes narrow or reverse the advantage.** Dense-KV Qwen at 1,000+
  users and V4/V4-Pro wafers at 4,096 users are examples: ROM does not help KV
  reads.

## 7. Sweet spots

1. **Single-user latency on any model.** Several-fold for DeepSeek-class MoE
   (2.3–5× at batch 1), and an order of magnitude for an 8B dense model. This
   needs the specialised fabric; weights in ROM alone roughly tie on large MoE.
2. **Interactive multi-user MoE serving, tens to ~1,000 users.** 2.8–8.5× per user.
   The ROM keeps per-user speed while the GPU's expert reads grow with the batch.
3. **Energy per token:** 3–5× on DeepSeek, 13× on Qwen at N5.
4. **Weak spots:**
   - dense-KV serving at high concurrency;
   - maximum-throughput batch serving, where ROM is at most ~3×;
   - ROM wafers, whose mesh collectives now trail the packaged array.

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
python3 tools/run_roofline_studies.py --force   # ~26 min, writes results/roofline/
python3 tools/rtl_rom_striped_bank_campaign.py  # section 9, seconds each
python3 tools/rtl_rom_pkg_link_campaign.py
python3 tools/rtl_rom_layer_pipeline_campaign.py
python3 tools/rtl_hdc_decode_campaign.py       # decode core, ~3 min
python3 tools/check_prose_figures.py            # every annotated figure above
```
