# Research provenance: what the seven-domain source hunt found

**Status:** applicable record — nothing in this document has been applied to
`configs/`, `src/`, `docs/SOURCES.md` or any results artifact.

**Written:** 2026-08-31 UTC
**Scope:** seven research domains covering 60 assumed constants in
`configs/hardware/technology.json`, each researched once and then verified
independently by a second agent who re-fetched the sources and re-ran the model.

**Why this file exists.** Another agent held `configs/hardware/technology.json`
and the roofline sources while this work was done, so none of it could be
applied at the time. This document is the whole of it — every recommendation,
every rejection, and every consequence measured against the committed
artifacts — written so a coordinator can apply it mechanically later without
losing anything. Where the researcher and the verifier disagreed, **the
verifier's finding governs** and the researcher's original is recorded in
§3 (Refuted) so it is not re-proposed.

## How to read the tables

Grades are this repository's own, from `technology.json → grade_definitions`:

| grade | means |
|---|---|
| `measured` | fabricated silicon reported in a peer-reviewed venue |
| `published` | stated by the vendor or standards body for a shipping part or process |
| `derived` | computed from published/measured entries by a formula stated in the note |
| `executed` | obtained by running something in this repository, with the artifact committed and named |
| `assumed` | no published value found; a stated judgement that must be swept |

**Direction** is the effect on the headline ROM-versus-GPU comparison if the
recommendation is adopted: *favours ROM*, *favours GPU*, or *neither*. Under the
program's asymmetry rule a change that favours ROM needs more evidence than one
that does not, so every ROM-favouring recommendation below carries its warrant
explicitly and several were declined on that ground.

**A caution about the denominator.** The verifiers reproduced the DeepSeek-V4-Pro
554,700 mm² batch-1 1M-context headline as **8.328×**
(`results/roofline/n6_vs_a100/analytical.json`, ROM
`DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` 1,863.23 tok/s against
`a100_sxm_80gb-x672-tensor` 223.743 tok/s). The "about 8.6×" figure quoted in
several places is the batch-1 figure at 92,450 mm²;
`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` contradicts itself inside one
file (line 11 says 8.6×, line 100 says 8.33×). Every movement stated below is
against 8.328×. Note also that at the time of verification both `analytical.json`
files and `REPORT.md` were **modified in the working tree** relative to HEAD;
re-derive against HEAD before quoting.

---

# 1. Domain tables

## 1.1 Taalas HC1 anchor

| key | current | recommended | grade | source | range | direction | one-line reasoning |
|---|---|---|---|---|---|---|---|
| `reference_parts.taalas_hc1.batch_size` | 1.0, `assumed`, "not published by Taalas" | 1.0 (unchanged) | `assumed` → **`published`** | Taalas launch deck footnote, verbatim "Taalas Llama 3.1 8B (BS=1 per chip, Run by Taalas Labs)", read at 3200 px on [nextplatform.com slide image 4092506](https://image.nextplatform.com/?imageId=4092506&width=3200), article [The Next Platform 2026-02-19](https://www.nextplatform.com/compute/2026/02/19/taalas-etches-ai-models-onto-transistors-to-rocket-boost-inference/4092140) | — | favours ROM | The batch size **is** published; the register's "stated nowhere" is wrong, and it forecloses the one correction that would have destroyed the gate. |
| `reference_parts.taalas_hc1.weight_bits_per_parameter` | 3.5, `assumed`, cited to CNX Software | 3.5 (unchanged); **replace the source**; keep range 3.0–6.0 | `assumed` | Ljubisa Bajic, ["The path to ubiquitous AI"](https://taalas.com/the-path-to-ubiquitous-ai/), taalas.com, 2026-02-19: "a custom 3-bit base data type … combining 3-bit and 6-bit parameters". Secondary should be [Wavect](https://wavect.io/blog/taalas-hc1-llm-asic-review/), not CNX | 3.0 – 6.0 | neither | The cited CNX article contains **zero** bit-width statements; the format is primary and first-party, only the 3/6 mix ratio is unpublished. |
| `reference_parts.taalas_hc1.weight_amortization` | `per_stream`, `assumed`, "Taalas publishes no batch size and no microarchitecture" | `per_stream` (unchanged); **replace the source field** | `assumed` | [US 2025/0123802 A1](https://patents.google.com/patent/US20250123802A1/en) (read via [FreePatentsOnline](https://www.freepatentsonline.com/y2025/0123802.html)) and [US 2025/0225198 A1](https://www.freepatentsonline.com/y2025/0225198.html), both assigned Taalas Inc. | — | neither at the gate | Both halves of the source field are false: the batch size is published and 13 Taalas patents exist, one of which is the architecture patent — and it describes output-parallelism per input and sequential passes, i.e. `per_stream`. |
| `reference_parts.taalas_hc1.power_w` | 250.0, `published`, cited to Kaitchup | **Do not move the value.** Record Bajic's 200 W as the better-sourced card figure in the note; keep the reported band 200–250 | `published` | Bajic in [The Next Platform 2026-02-19](https://www.nextplatform.com/compute/2026/02/19/taalas-etches-ai-models-onto-transistors-to-rocket-boost-inference/4092140): "The HC1 card burns about 200 watts … a two-socket X86 server with ten HC1 cards in it runs 2,500 watts" | 200 – 250 W | favours ROM if the value moves | `taalas_hc1_power_anchor` (`roofline.py:3957-3980`) reads `range_low` and `value` only; setting value = 200 collapses the reported band to [200, 200] and **deletes** the 0.28× conservative reading from `REPORT.md:82`. See §3. |
| `reference_parts.taalas_hc1.clock_frequency_hz` | absent | **leave absent** | `assumed` (negative) | Exhaustive negative: taalas.com (7 sitemap URLs), The Next Platform ("Clock speed information is not disclosed"), The Register, ServeTheHome, CNX, Wavect, Kaitchup, 13 Taalas patents (0 hits for GHz/MHz), [Hot Chips 2026 program](https://hotchips.org/), [ISSCC 2026 advance program](https://submissions.mirasmart.com/ISSCC2026/PDF/ISSCC2026AdvanceProgram.pdf) (`grep -ic taalas` = 0) | — | unknown | No published clock exists and none is derivable from the published set; the negative is already registered under `power.fabric_clock_hz`, which **does** feed the HC1 power gate. |
| `reference_parts.taalas_hc1.transistors` | 53e9, `published`, "No primary Taalas statement located" | 53e9 (unchanged); **citation repair only** | `published` | [taalas.com/products](https://taalas.com/products/) spec line, verbatim: "TSMC 6nm \| 815mm2 \| 53B Transistor"; corroborated by The Next Platform ("53 billion transistors on the package") | — | neither | A primary statement exists on the same vendor page the register already cites for die area; `docs/SOURCES.md:221` asserts a search failure that is not one. |
| `reference_parts.taalas_hc1.published_tokens_s_per_user` | 16960.0, `published`, cited to a page whose prose says only "17k" | 16960.0 (unchanged); **cite the chart image and the prose secondary** | `published` | Data label on [taalas.com/h-content/uploads/2026/02/graph.png](https://taalas.com/h-content/uploads/2026/02/graph.png) (H200 230, B200 353, Groq 594, Sambanova 932, Cerebras 1981, Taalas HC1 16960); prose secondary [The Register 2026-08-06](https://www.theregister.com/systems/2026/08/06/amd-acquires-ai-chip-startup-taalas-to-boost-inference-performance-by-etching-models-into-silicon/5284344) "16,960 tokens a second" | — | neither | The four digits are only on the chart image; the current citation points at prose a reader cannot check. Record the 0.0625 ms sibling-slide residual (6%) rather than hiding it. |
| *(proposed, absent)* multi-chip DeepSeek-R1-671B figure | not present | **do NOT adopt** — record as a named NON-source | `assumed` | Same deck footnote: "DeepSeek R1 (BS=1 per chip, **Simulated** by Taalas Labs)"; bar value 12,382 on [slide 4092480](https://image.nextplatform.com/?imageId=4092480&width=1600) | — | favours ROM if adopted | A vendor's simulation of a machine that does not exist is this repository's model checked against someone else's model, not a validation gate. |

**Gate arithmetic, reproduced twice** (in-memory copy of `technology.json`, no repo
file touched). Llama-3.1-8B, 2,048 context, 815 mm², published 16,960, tolerance
floor 0.5:

| batch | `per_stream` | ratio | `batched` | ratio |
|---:|---:|---:|---:|---:|
| 1 | 12,232.4 | **0.7213× PASS** | 12,232.4 | 0.7213× |
| 2 | 6,317.0 | 0.3725× FAIL | 6,107.1 | 0.3601× FAIL (compute-bound) |
| 3 | 4,257.9 | 0.2511× | 2,790.2 | — |
| 4 | INFEASIBLE (area) | — | 1,087.1 | 0.0641× |
| 8 | INFEASIBLE | — | INFEASIBLE | — |

`per_region` is bit-identical to `per_stream` at every batch. With an 8-bit KV,
B=4 becomes feasible at 0.1893× and B=8 is still infeasible — the qualitative
result survives any KV precision. **The gate's PASS is bought entirely by batch 1.**

## 1.2 ROM physical parameters

| key | current | recommended | grade | source | range | direction | one-line reasoning |
|---|---|---|---|---|---|---|---|
| `rom.cell_to_sram_cell_area_ratio` | 0.2, `assumed` | **0.33** | **`derived`** (not `published` — see §3) | Wang et al., "ROMA", ASP-DAC 2026, [doi:10.1109/ASP-DAC66049.2026.11420528](https://doi.org/10.1109/ASP-DAC66049.2026.11420528), preprint [arXiv:2503.12988](https://arxiv.org/abs/2503.12988) §II-C: "the area of the bit cell for the generated ROM is approximately one-third of that of the SRAM bit cell" (TSMC 7nm Memory Compiler) | 0.11 – 0.33 | favours GPU on capacity, favours ROM on latency | The only foundry-compiler statement at the modelled node says one-third, not one-fifth; the 0.11 end is a simulated academic cell two nodes away. |
| `rom.array_efficiency` | 0.7, `assumed` | **0.52** | `derived` | Same figure, deepest compiler instance: ROM macro 57.8 Mbit/mm² at 8192×64 ÷ 111.1 Mbit/mm² of bare cells. Bar values extracted from the figure's own SVG and each reproduces its printed label to three figures | 0.38 – 0.70 | favours GPU | ROM array efficiency is **below** SRAM's at every compiler depth (0.194/0.310/0.424/0.520 vs 0.354/0.591/0.637/0.694); the file's "no write drivers so higher" rationale is backwards for a structural reason that holds at any node. |
| `sram.array_efficiency` | 0.65, `assumed` | 0.65 (unchanged) | `derived` | Same figure: 0.354/0.591/0.637/0.694 at 1024/2048/4096/8192×64 against the repo's published 0.027 µm² N7 6T HD cell | 0.64 – 0.69 for KV-bank-sized macros; 0.35 recorded as the small-instance floor | neither | The file's guess ("0.55–0.75") is now measured against a real compiler at the target node and it was right; 0.65 sits where a KV bank sits and is 6% conservative against the largest instance. |
| `rom.cim_cell_area_multiplier` | 1.6, `assumed` | 1.6 (unchanged) | `assumed` | Bracketed from ROMA's own Fig. 11(a) area breakdown (L-Unit 73.2% of 503.7 mm² holding 1.86 GB = 40.4 Mbit/mm² fused) and Fig. 12 L-Unit areas (Standard SRAM+Compute 59.7 / Standard ROM+Compute 36.7 / B-ROM+Compute 26.0 / Fused 22.5 mm²) | **1.39 – 2.34** | neither | No published compute-in-ROM cell matches the partial-product-select structure this parameter describes; 1.6 sits inside the bracket that ROMA's own figures support. |
| `rom.cim_precompute_area_fraction` | 0.02, `assumed` | **0.18** | `assumed` | Guan et al., "TOM", [arXiv:2602.20662](https://arxiv.org/abs/2602.20662), stated in text: "The chip's total area is 56.9 mm², with the majority (58%) allocated to our … ROM. The on-chip SRAM … and the distributed compute logic account for 24% and 18% of the area" | 0.08 – 0.27 | favours GPU | The strongest leg is internal: `roofline.py:1745-1755` gives a compute-in-ROM die **no accumulator or adder-tree area at all**, so 0.02 asserts a floorplan no fabricated compute-in-ROM part is near. |
| `efficiencies.rom_read_bandwidth` | 0.75, `assumed` | 0.75 (unchanged) | `assumed` | No fabricated mask-ROM array has published a sustained-versus-peak read fraction. Anchor context: YOLoC, [doi:10.1145/3489517.3530576](https://doi.org/10.1145/3489517.3530576), Table I | 0.75 – 1.00 | neither | Nothing in the literature closes it; the researcher's argument for raising it was refuted (see §3) and raising it would be a straight 1.33× gift to every ROM weight-read rate. |
| `efficiencies.sram_read_bandwidth` | 0.75, `assumed` | 0.75 (unchanged) | `assumed` | No published achieved-versus-peak local SRAM read fraction. The anchor it derates (`SRC-CEREBRAS-WSE2`, 20 PB/s) is **confirmed broken**: [cerebras.ai/chip](https://www.cerebras.ai/chip) today describes WSE-3 only (21 PB/s); the string "20 PB" does not appear | 0.60 – 0.90 | neither | Not closable; record instead that the ROM side is charged 0.75 on its KV path while the GPU comparator is charged 0.85 on HBM, and that closing that gap would be a 1.13× pro-ROM move on 446 binding points. |

**What the ROM evidence actually fixes** is the *quotient*: `ratio /
array_efficiency = 0.6408`, forced by ROMA's single macro density plus the repo's
own published 0.027 µm² N7 cell. That gives **ROM capacity density 57.8 Mbit/mm² =
7.222 MB/mm² against the current 16.204 — a 2.243× correction.** The split into
0.33 and 0.52 rests on one sentence; the density does not. **Change both entries in
one edit, or record the density directly** — changing one alone produces a number
no source supports. Record which instance depth each number came from: ROM 0.52 is
the 8192×64 instance and nothing published reaches it at any smaller instance;
depth alone moves ROM density by 1.23×.

## 1.3 Energy per operation

**Read this row first.** `results/roofline/n6_vs_a100/analytical.json →
points[].operations_by_canonical_format`: DeepSeek-V4-Pro-0813 is **99.94% w4a8**
and 0.06% fp32, DSV4-Flash is 99.86% w4a8, Qwen3-8B is 100% bf16. **fp8 and fp4
are charged on zero operations at every point in this study.** The evidence in
this domain was spent almost exactly inversely to where it matters.

| key | current | recommended | grade | source | range | direction | one-line reasoning |
|---|---|---|---|---|---|---|---|
| `energy.mac_energy_j_per_op.bf16` | 1e-13, `assumed` | **3.3e-13** | `assumed` (not `derived` — the plane selection has no published basis, §3) | Antepara et al., SC'25, [doi:10.1145/3712285.3759815](https://doi.org/10.1145/3712285.3759815) ([open PDF](https://escholarship.org/content/qt6189368s/qt6189368s.pdf)), Table 3, A100 Matrix-FP16: control 0.37 / datapath 0.33 / total 0.70 pJ/FLOP | 1.3e-13 – 7.0e-13 | raises arithmetic on both sides | The incumbent is 3.3× below the measured datapath plane of a shipping N7 tensor core and 2.1× below Horowitz's 45 nm FP16 MAC; but the control/datapath split under it is not physical (§3), so the value stands on a bracket, not a derivation. |
| `energy.mac_energy_j_per_op.fp32` | 4e-13, `assumed` | **~1.09e-12** (the researcher's 1.2e-12 is 6–14% high on its own formula) | `assumed` | Same table × Horowitz's 45 nm FP32/FP16 MAC ratio. **Horowitz's 45 nm 32-bit float MULT is 3.7 pJ, not 4** (verified via EIE, [arXiv:1602.01528](https://arxiv.org/abs/1602.01528), Table I, Horowitz a co-author), so the MAC is 4.6 pJ and the ratio 3.29 | 4e-13 – 1.07e-11 (A100 Vector-FP32 total) | raises arithmetic on both sides | 0.06% of DSV4-Pro operations; the gap between 1.09e-12 and 1.07e-11 is the honest measure of how much of a GPU FP32 FLOP is not arithmetic. |
| `energy.mac_energy_j_per_op.fp8` | 3e-14, `assumed` | **5.4e-14** | `assumed` | Same table × Horowitz INT8/FP16 ratio; cross-checked against Keller et al., 2022 Symp. VLSI Tech. & Circuits, Digest pp.16-17, Table 2 (fabricated TSMC 5nm, INT8 39.1 TOPS/W at 0.46 V) — [NVIDIA-hosted PDF](https://d1qx31qr3h6wln.cloudfront.net/publications/C02-1.PDF) | 3e-14 – 6.8e-14 | **inert — zero operations** | Best-sourced rung in the ladder and it moves nothing in this study. |
| `energy.mac_energy_j_per_op.fp4` | 1.5e-14, `assumed` | **2.3e-14** | `assumed` | Keller et al. Table 2, one fabricated die: INT4 91.1 vs INT8 39.1 TOPS/W, both at 0.46 V, both at 50% density, two dedicated datapaths → energy ratio 0.4292 | 1.5e-14 – 2.9e-14 | **inert — zero operations** | Evidentially the cleanest leg (process, PVT, leakage and dataflow all cancel) and more conservative than argued — the pure-datapath ratio is nearer 0.38. |
| `energy.mac_energy_j_per_op.w4a8` | 2e-14, `assumed` | record as the **interval [2.33e-14, 5.42e-14]**, point 3.9e-14 | `assumed` | No source of any kind exists for a mixed 4-bit-weight × 8-bit-activation MAC energy; the interval is bounded by the fp4 and fp8 rungs above, which share the accumulator | 2.33e-14 – 5.42e-14 | raises arithmetic on both sides | **This rung carries 99.9% of the study's operations and has no source.** It is an arithmetic mean of two entries anchored on a split that is not physical. |
| `energy.sram_read_j_per_byte` | 1e-12, `assumed` ("no vendor macro energy published") | **2.6e-12**, explicitly labelled a **floor** | `assumed` (not `derived`, §3) | SC'25 Table 3, A100 L1: control 1.26 / datapath 0.33 / total 1.59 pJ/bit; ×8 = 2.64 / 12.72 pJ/B | 1.44e-12 (MI250X L1 datapath) – 1.27e-11 (A100 L1 total) | favours GPU | Charged only when `kv_store == 'sram'` (`roofline.py:2937-2940`), i.e. ROM-side designs; the A100's KV is HBM at 104.88 pJ/B and is untouched. The dropped control plane contains SRAM row decode, which a scratchpad does pay. |
| `energy.operand_delivery_j_per_byte` | 2.3e-13, `assumed` | 2.3e-13 (unchanged) | `assumed` | No source addresses this term's boundary (array output latch → arithmetic, tile-local). Existing chain: Horowitz ISSCC 2014 RF access + Dally 45 nm wire energy | 1.5e-13 – 8e-13 | neither | **Load-bearing dependency:** its note derives a 5.49× node factor as "the geometric mean of ratios implied by this file's own `mac_energy_j_per_op` entries"; adopting the MAC ladder makes that sentence false and the factor must be re-sourced. Honest interval 2.1×–5.5×; alternative point 3.8e-13. |
| `energy.rom_read_j_per_byte` | 8e-14, `assumed` | 8e-14 (unchanged) | `assumed` — **required**, not merely honest | Ankhdjet, [arXiv:2608.26206](https://arxiv.org/abs/2608.26206) Table VII (SKY130, ngspice on a C-extracted deck, **not silicon**); upper bound from TOM [arXiv:2602.20662](https://arxiv.org/abs/2602.20662) | 2e-14 – 5e-13 | neither | `docs/METHODOLOGY.md` §9 forbids scaling SKY130 energy into N7 by an SRAM-density ratio, which is exactly what the incumbent derivation does — so no improved decomposition can lift the grade. **Latent trap:** the note's "cell-to-cell area ratio of 14.3" is the **linear bitline-pitch** ratio (√204.6), and linear is the physically correct scaling; "correcting" the label into an area ratio would make the number 14.3× too small. |
| `power.static_leakage_w_per_mm2.rom_array` | 0.0, `assumed` (deliberately zero) | **6.7e-3** | `assumed` (rests on five `assumed` entries) | Derived on the file's own entries: 0.005 W/mm² ÷ (24.07e6 bits/mm² × 0.8 V) = 0.260 nA per 6T cell ÷ 4 devices = 0.065 nA/device; × 129.63e6 bits/mm² × 0.8 V = 6.73e-3 W/mm². Qualitative corroboration: TOM's entire third contribution is power-gating inactive ROM banks (25.813 W → 5.33 W) | 1.3e-3 – 2.6e-2 | favours GPU | A ROM array charged a physically impossible zero is most of a compute-in-ROM die; the derivation declines two real ROM-favourable credits (HVT/long-channel devices are free in an array with no read-stability constraint; ~50% of via-programmed NOR cells have no bitline leakage path). |

## 1.4 Latency primitives

| key | current | recommended | grade | source | range | direction | one-line reasoning |
|---|---|---|---|---|---|---|---|
| `latency.array_pass_boundaries_per_layer` | 4.0, `assumed` | **Make it per-model.** Qwen3-8B: from the executed artifacts. DeepSeek-V4: 5 under the entry's own definition (serially dependent *matrix* passes), 9–10 if `ATTEND`/`ROUTER_SCORE`/`MHC_PROJECT` each pay a full array pass | Qwen3 **`executed`**; DeepSeek `derived` with the Flash→Pro analogy declared | In-repo, executed: `results/abi3/qwen3_rom_ta-qw-chat-1_execution.json` — 6,096 tensor + 864 attention + 7,800 vector descriptors over 36 layers × 24 steps decomposes exactly as 7 tensor + 1 attention per layer per step, reproduced to four decimals across eight passing runs on two backends. Graph route: `compiler/frontend/deepseek_v4_graph.py`, `compiler/qwen3/graph.py` | 4 – 10 | favours GPU | The entry is graded `assumed` "because the model profiles do not state a pass structure", but the repository already contains **both** an executed counter (Qwen3) and a node-by-node graph contract (DeepSeek) — and they measure different quantities (occupancy vs serial depth), which is why one global scalar cannot be right. |
| `latency.layer_barrier_s` | 8e-09, `assumed` | **3.5e-08** | `assumed` | The model's own floor: √815 = 28.548 mm × 1.5e-10 s/mm = 4.282 ns one way, and a barrier is a reduction **plus** a completion broadcast. IPU bracket from Jia et al., [arXiv:1912.03413](https://arxiv.org/abs/1912.03413) §4.1.2; wafer AllReduce from Rocki et al., SC20, [arXiv:2010.03660](https://arxiv.org/abs/2010.03660) | 8.6e-09 (the model's own floor) – 2.0e-07 | favours GPU | **8 ns is below the model's own arithmetic floor of 8.565 ns of bare wire**, and both the point and the current `range_low` (4e-9) sit under it. The strongest finding in the domain and it is internal. |
| `latency.pipeline_fill_drain_s` | 3.2e-08, `assumed` | 3.2e-08 (unchanged) — but raise the ceiling | `assumed` | Jouppi et al., ISCA 2017, [arXiv:1704.04760](https://arxiv.org/abs/1704.04760): "It contains 256×256 MACs", "The TPU has a 700 MHz clock". A 2N−1 = 511-cycle drain **at the model's own 1 GHz fabric clock** is 5.11e-07 | 1.6e-08 – **5.11e-07** | favours GPU | 57% of the DSV4-Pro fixed budget, and its width is set by an architectural fact the model never states: a systolic array pays 2N−1, a CIM macro with an adder tree pays log₂(lanes). Do **not** use 7.3e-07 — that imports a 28 nm part's clock (§3). |
| `latency.sparse_index_dependency_s` | 1.28e-07, `assumed` | 1.28e-07 (unchanged) — but a constant is the wrong **shape** | `assumed` | Luo et al., [arXiv:2402.13499](https://arxiv.org/abs/2402.13499) Table IV: A100 shared 29.0 clocks = 20.6 ns, global 466.3 = 330.7 ns at 1.41 GHz | 6.4e-08 – 3.31e-07 | favours GPU | 28% of the fixed budget, priced as a constant while the candidate set it scans is ceil(context/4) — 2,048 at 8K and 250,000 at 1M, a 122× change — and the headline is quoted at the far end. |
| `latency.global_wire_delay_s_per_mm` | 1.5e-10, `assumed` | 1.5e-10 (unchanged); **keep `range_high` at 2.5e-10** | `assumed` | **Negative, reproduced independently:** the IRDS 2023 edition has no Interconnect chapter and `2023IRDS_MM.pdf` contains zero per-mm interconnect-delay statements. Realised traversals (all fabricated): IPU ~0.8 ns/mm marginal, CS-1 ~3.6–4 ns/mm, A100 L2 185 ns | 1.0e-10 – 2.5e-10 | neither | No primary document for "100–250 ps/mm at 7 nm class" was found by either agent; the value is a **bare-wire floor, not a fabric traversal**, and the note must say so or a later reader will mistake it for one. |
| `latency.sequencer_issue_decode_s` | 3e-09, `assumed` (no anchor at all) | **4e-09** | "published depth / **assumed clock**" — not `derived` | Jouppi et al., ISCA 2017: "It uses a 4-stage pipeline for these CISC instructions"; ÷ `power.fabric_clock_hz` = 1 GHz, itself `assumed` and swept 0.5–2 GHz | 1e-09 – 8e-09 | favours GPU | Published pipeline depth for the closest shipping statically-scheduled matrix accelerator; impact +0.4% on the fixed budget. Over the clock's own swept band this entry runs 2–8 ns, i.e. the whole existing range. |
| `latency.sram_access_s` | 2e-09, `assumed` | 2e-09 (unchanged); **keep the 1–4 ns band** | `assumed` | Fabricated: CS-1 48 KB tile-local "load-to-use latency is one cycle" ([arXiv:2010.03660](https://arxiv.org/abs/2010.03660)); IPU 256 KiB tile-local 3.75 ns / 6 cycles at 1.60 GHz ([arXiv:1912.03413](https://arxiv.org/abs/1912.03413) Table 1.1) | 1e-09 – 4e-09 | neither | 0.9% of the fixed budget — cannot move any answer. What the note should fix is the **boundary**: a leading-node macro is sub-nanosecond, so most of the 2 ns is bank select and return alignment, not the macro. |
| *(documentation)* `latency` block share of step | prose claims 28–35% for a batch-1 ROM design and 0.7–2.1% for a GPU | **ROM 0.0101%–4.79%, GPU 0.0014%–1.60%** at batch 1; **2.56%** at the headline | `derived` from committed artifacts | `results/roofline/{n6_vs_a100,n5_vs_b200}/analytical.json` field `layer_fixed_latency_fraction_of_step`, over all batch-1 points (n6: 458 ROM / 128 GPU; n5: 462 / 112) | 0.0101% – 4.79% | neither | The 28–35% claim (`docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:1169`) is ~7× the maximum this block reaches and could not be reproduced under any denominator. The companion "162.4 ns per dense layer, range 65.4–726.8 ns" **is** correct. |

## 1.5 Floorplan and HBM

| key | current | recommended | grade | source | range | direction | one-line reasoning |
|---|---|---|---|---|---|---|---|
| *(audit question)* does a published GPU die area already include overhead and interconnect? | unsettled | **SETTLED YES** — the floorplan fractions belong and must not be removed | `derived` (not `measured`, §3) | [NVIDIA A100 whitepaper](https://images.nvidia.com/aem-dam/en-zz/Solutions/data-center/nvidia-ampere-architecture-whitepaper.pdf) ("die size of 826 mm²", "6 HBM2 stacks, 12 512-bit Memory Controllers", Fig. 3 module photograph) + [GA100 die photograph, CC BY 3.0](https://commons.wikimedia.org/wiki/File:GA100_Die_Shot.jpg), measured in session | — | favours GPU | The 826 mm² contains six HBM PHY sites (12.5–14.9% of die), NVLink/PCIe SerDes strips (7.25–7.6%), L2/hub SRAM and everything else — and `gpu_device_budget` charges the GPU **none** of the fractions and credits it no area it lacks, so the ROM side must pay them out of the same die. |
| `hbm.hbm2e.stack_beachfront_mm` | 12.0, `assumed` | 12.0 (unchanged) | `derived` | GA100 die photograph at 237.11 px/mm: PHY site pitch 12.04–12.37 mm (mean ~12.13–12.15); package pitch 11.88 mm off NVIDIA's own Fig. 3; band length 6.08 mm matches SK hynix's published 6,050 µm HBM ballout ([Hot Chips 26, archived](https://web.archive.org/web/20150424141343/http://www.setphaserstostun.org/hc26/HC26-11-day1-epub/HC26.11-3-Technology-epub/HC26.11.310-HBM-Bandwidth-Kim-Hynix-Hot%20Chips%20HBM%202014%20v7.pdf)) | 11.9 – 12.4 | **favours ROM** (not neutral, §3) | `max_hbm_stacks_per_device` = floor(4·√46225 · 0.60 / 12.0) = floor(**43.0**) — an exact integer knife edge — and the winning ROM design at every batch ≥ 16 carries 43 stacks and binds `kv_read`. Holding 12.0 instead of the measured pitch is a 2.3% ROM-favouring choice. |
| `hbm.hbm2e.phy_area_mm2_per_stack` | 10.0, `assumed` ("commonly quoted 8–15 mm²") | 10.0 (unchanged) | `derived` | Same photograph: band 6.08–6.16 mm along the edge × ~1.65–1.90 mm strip depth. Independent convergence at the top: SK hynix's published ballout is 6,050 × 3,264 µm = **19.75 mm²** | 9.9 – **~20** (not 17.2, §3) | favours ROM | The measurement **excludes the digital memory controller**, which the photograph cannot separate from adjacent logic; charged only on the ROM side (`roofline.py:1691-1693`; `gpu_device_budget` sets `hbm_phy_mm2 = 0`), so the residual undercharge could be 2×. |
| `hbm.hbm3e.stack_beachfront_mm` | 12.0, `assumed` | 12.0 (unchanged) | **`assumed` (transferred from a measured HBM2e pitch)** — not `derived` | Transfer, warranted by the [Hopper whitepaper](https://www.advancedclustering.com/wp-content/uploads/2022/03/gtc22-whitepaper-hopper.pdf): GH100 supports "6 HBM3 **or** HBM2e stacks, 12 512-bit Memory Controllers" on one 814 mm² die — NVIDIA reused one edge structure across both generations | 11.9 – 12.4 | **unknown** (not favours_gpu, §3) | No HBM3E die photograph or mechanical drawing is public; the "11 × 11 mm HBM3E footprint" that made this conservative is unsourced folklore. Sets the n5_vs_b200 stack count by the same knife-edge arithmetic. |
| `hbm.hbm3e.phy_area_mm2_per_stack` | 10.0, `assumed` | 10.0 (unchanged) | `assumed` (transfer) | Same transfer; the per-stack interface is unchanged at 1024 bits | 9.9 – ~20 | favours ROM | HBM3E runs ~3× the per-pin rate and a faster serial front end is normally larger, so 10.0 is more likely a floor than a ceiling. |
| `floorplan.overhead_area_fraction` | 0.1, `assumed` ("no published floorplan for a mask-ROM inference die") | 0.10 (unchanged) | `derived` | Measured GA100 NVLink/PCIe SerDes strips = 7.25–7.6% of die; **published** TPU v1 floorplan ([arXiv:1704.04760](https://arxiv.org/abs/1704.04760) Fig. 2): Host 2% + PCIe 3% + Misc I/O 1% + Control 2% = 8% | 0.07 – 0.16 | favours GPU | "No published floorplan" is no longer true — there are two, and they bracket the enumerable part. Neither enumerates clock distribution, PLLs, power grid or DFT, so **0.10 is a floor for the category, not a midpoint**. |
| `floorplan.interconnect_area_fraction` | 0.08, `assumed` | 0.08 (unchanged) | `assumed` | Envelope only: TPU v1's printed blocks sum to 79% (caption independently: "data buffers 37%, compute 30%, I/O 10%, control 2%"), leaving 21% for interconnect + clock + power grid + DFT + whitespace | 0.05 – 0.15 | **unknown** | Could not be closed. This is not really a NoC charge — it is the bank-to-compute fabric multiplexing ROM banks onto a shared array, which has **no published analogue at all**. Worth ~5% on the headline by analogy with `COMPARISON_FAIRNESS_AUDIT.md` A4. |
| `power.memory_interface_idle_w_per_stack` | 2.8, `assumed`, range 1.2–6.4 | 2.8 (unchanged), **range unchanged at 1.2–6.4** (§3) | `derived` | Salami et al., DATE 2021, [arXiv:2101.00969](https://arxiv.org/abs/2101.00969) §III-A-2 / Fig. 2, measured on real HBM2 (Xilinx XCVU37P, two 4 GB 4-Hi stacks, VCC_HBM rail instrumented): "even when HBM is idle, it consumes nearly one-third of the power it consumes at full load" | 1.2 – 6.4 W | neither at the headline | Value stops being a guess. **Boundary warning:** do not run the formula with `energy.hbm_j_per_byte` (13.11 pJ/bit) — that figure's boundary is the whole path including the processor-side PHY and controller, while the DATE rail is the DRAM stack only; mixing them returns 7.1 W/stack from a units mismatch. |
| `power.gpu_logic_area_fraction` | 0.6, `assumed` ("no vendor floorplan published") | 0.60 (unchanged) | `derived` | Measured GA100 non-logic edge I/O = **21.3%** of die (HBM strips 14.9%, SerDes 7.6%, less corner overlap), which alone caps standard-cell logic at 0.787 before a bit of SRAM; published SRAM inventory ~104 MiB = 872 Mbit at 10–20 Mbit/mm² = 5.3–10.6% | 0.55 – 0.72 | favours GPU | 0.60 is the **floor** of the bracket, not its centre — the bracket's own midpoint is ~0.72. Adopting it would add ~4 W of leakage to a 400 W part and therefore favours ROM, which is why it is declined. Touches GPU static power (~1% of TDP) and not the throughput headline at all. |

## 1.6 Efficiency derates

| key | current | recommended | grade | source | range | direction | one-line reasoning |
|---|---|---|---|---|---|---|---|
| `efficiencies.compute` | 0.55, `assumed` | 0.55 (unchanged) | `assumed` (not `derived`, §3) | Narayanan et al., SC'21, [arXiv:2104.04473](https://arxiv.org/abs/2104.04473): 502 PF/s on 3,072 GPUs = 163.4 TF/s each = 52.4% of the A100's 312 TFLOPS. Pope et al., MLSys 2023, [arXiv:2211.05102](https://arxiv.org/abs/2211.05102) Tables 2–3: prefill MFU 76% / 73% | 0.52 – 0.76 | neither | Both cited endpoints are **whole-kernel MFUs** that already contain memory time and collectives, so both are *lower* bounds on a compute-only derate: 0.55 sits below the published floor, not inside a bracket. It is a ROM-only lever — 91 of 3,092 feasible points bind compute, all ROM, zero GPU — so keeping it low is the conservative-for-ROM choice. |
| `efficiencies.hbm_bandwidth` | 0.85, `assumed` ("commonly measured STREAM-class fraction", no document named) | **0.90** | `assumed` with citation (not `measured`, §3) | Luo et al., [arXiv:2402.13499](https://arxiv.org/abs/2402.13499) Table V: A100 PCIe 40GB 1407.2 / 1555 = 90.5%; H800 (HBM2e, 5120-bit, 2039 GB/s) 1861.5 / 2039 = 91.3%; text confirms "92%, 90%, and 91%" | 0.85 – 0.91 | **favours GPU** | 746 of 1,020 feasible GPU points bind HBM. **The A100 weight-bound gate reading 1.00× is not evidence for this parameter** — it is evaluated under `technology.ideal()`, which forces every efficiency to 1.0, and matches to sixteen digits. Nothing in this repository measures this constant. |
| `efficiencies.hbm_capacity` | 0.9, `assumed` | 0.90 (unchanged) | `assumed` citing a policy ceiling (not `derived` — no formula, §3) | vLLM `gpu_memory_utilization` default **0.92**, confirmed in both [the docs](https://docs.vllm.ai/en/latest/configuration/engine_args.html) and [`vllm/config/cache.py`](https://github.com/vllm-project/vllm/blob/main/vllm/config/cache.py) | 0.85 – 0.92 | favours GPU | The value is nearly inert (4 GPU exclusions of 4,688). **The finding is the asymmetry:** all 1,592 ROM capacity exclusions are SRAM-KV designs, and SRAM KV carries *no* capacity derate at all (`roofline.py:2236` vs `:2248`) — though a mirrored 0.90 would double-count, since `sram.array_efficiency` already charges write drivers and redundancy. |
| `efficiencies.stage_balance` | 0.9, `assumed`, applied when `device_count > 1` | **(a)** change the guard to `topology.pipeline_stages > 1`; **(b)** derive per-partition; **(c)** apply to **aggregate throughput only** — per-user latency carries none | `assumed` (the residual), the partition itself `derived` | `docs/METHODOLOGY.md` §6a's own derivation; per-layer bytes and `metadata.attention_sequence` in `configs/models/*.json`; the repository already implements the correct form at `src/opentallas/analytical.py:781-782` | 0.85 – 1.00 | **favours ROM** (+1.18%) — the researcher had this backwards (§3) | Stage imbalance cancels exactly for one user's serial pipeline traversal (stage *s* holds *f_s* of the work against 1/S of the resource → S·f_s·t, summing to S·t regardless of the cut). Removing it from both sides at batch 1: ROM 1,947.43, GPU 231.12, **8.328× → 8.4260×**. |
| `efficiencies.expert_router_imbalance` | 1.0, `assumed` (no imbalance charged) | **1.04** | `assumed` | Wang et al., [arXiv:2408.15664](https://arxiv.org/abs/2408.15664) Eq. (4) and Table 2: MaxVio_global = 0.04 for loss-free balancing, the exact strategy DeepSeek adopts ([DeepSeek-V3 report](https://arxiv.org/abs/2412.19437) §2.1.2) | 1.04 – 1.72 | favours GPU, but **structurally inert at batch 1** | 1.0 is excluded by a published measurement. Deliberately uses MaxVio_**global** (the B→∞ limit, which the paper itself frames that way) not MaxVio_batch, to avoid double-counting against `expected_max_region_load`. 1.04 is a **floor**: it is measured at 64 routed / 6 activated against DSV4-Pro's 384 top-6. |
| `kv.access_granularity_bytes.hbm` | 32.0, `assumed` | 32.0 (unchanged); **fix the derivation** | `assumed` → **`published`** | [NVIDIA CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html): "the data access unit is 32-byte"; [Nsight Compute glossary](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html): "Sector: Aligned 32 byte-chunk" | 32 – 32 | neither — **inert** | The number is right and NVIDIA states it directly; the **stated derivation is wrong for this study** (it argues from HBM3 pseudo-channels, and `technology.json` has no `hbm3` block at all — the A100 declares `hbm2e`). `kv_access_granularity_inflation` is exactly 1.0000 on all 4,688 points. |
| `kv.access_granularity_bytes.sram` | 128.0, `assumed` | 128.0 (unchanged) | `assumed` | No published value; SRAM compiler word widths are integrator-configurable with column muxing, so there is no single constant to find | 32 – 256 | neither — **inert** | Could not be closed and is reported open. The note is also stale and self-defeating: it argues a 64 B macro "halves the waste on a 68-byte entry" when 68 B at a 64 B granule costs 128 B — exactly what a 128 B granule costs. |
| `kv.index_layout` | "interleaved", `assumed` | "interleaved" (unchanged); **retract the 1.6× sensitivity claim** | `assumed` (a declared choice, not a constant) | In-repo: `analytical.json` field `kv_access_granularity_inflation`; `REPORT.md` §4 | contiguous ↔ interleaved | neither — **inert** | With 256 B index entries both granules divide exactly, so `_granule_factor` returns 1.0 and **contiguous and interleaved are numerically identical under every current profile**. The advertised 1.6× rests on the retracted 583/68 constants and the study's own output contradicts it. |

## 1.7 Remaining link constants

| key | current | recommended | grade | source | range | direction | one-line reasoning |
|---|---|---|---|---|---|---|---|
| `links.inter_wafer.switch_radix` | 16.0, `assumed`, "one tree level reaches the whole rack" | **4.0** | `published` | [Cerebras CS Weight Streaming white paper](https://8968533.fs1.hubspotusercontent-na2.net/hubfs/8968533/Virtual%20Booth%20Docs/CS%20Weight%20Streaming%20White%20Paper%20111521.pdf) §6.4: "Each broadcast-reduce node provides enough bandwidth to perform either 1:4 broadcast-reduce operations or a pair of 1:2"; Fig. 14 (rendered) shows an 8-system cluster costing **two** tiers | 2 – 8 | favours GPU, but **moves zero headline rows** (§3) | 16 is unsourced; 4 is published, and the model's `2·ceil(log_radix(span))` is already exactly the cost of a fan-out-4 broadcast-reduce tree. 336 of 4,688 points move; no headline row does. |
| `links.inter_wafer.hop_latency_s` | 5e-06, `assumed` | 5e-06 (unchanged) | `assumed` | [Cerebras Hot Chips 36 deck](https://hc2024.hotchips.org/assets/program/conference/day2/72_HC2024.Cerebras.Sean.v03.final.pdf) p.51 (rendered): "CS-3 IO is <5us / 4 hops required / <1% impact"; class measured by De Sensi et al., SC24, [arXiv:2408.14090](https://arxiv.org/abs/2408.14090) | 2.3e-06 (figure-read) or **3.7e-06 (prose-only)** – 1e-05 | neither | The slide's own arithmetic decides the ambiguity **toward the incumbent**: 4 × 5 µs of 2,222 µs = 0.90% → "<1%", where the whole-path reading gives 0.225%, which nobody writes as "<1%". Raising `range_low` off the unsourced 1.0 µs runs against the ROM side. |
| `links.inter_wafer.domain_size` | 16.0, `assumed` | **64.0**, and mark **reporting-only** | `published` | Same white paper §8.1: "near-linear scaling for Cerebras Wafer-Scale Clusters up to **64** CS-2s" | — | neither — **nothing reads it** | Re-running the whole study at domain_size 2/4/16/64 changes exactly **one leaf** of the result tree: the reporting echo at `run_roofline_studies.py:2356`. See §4. |
| `links.inter_wafer.fabric` | "switched", `assumed`, "the optimistic reading" | "switched" (unchanged); **replace the note** | `assumed` → **`derived`** | Same white paper §6.4: "SwarmX nodes are connected in a bidirectional tree topology" | — | neither | Once radix is 4, "switched" is a *correct encoding* of the published tree, not an optimistic approximation of one — and the sentence conceding optimism was doing real work only while radix was 16. |
| `links.on_package.hop_latency_s` | 3e-07, `assumed`, sourced to this repository | leave the number; **relabel as a placeholder with no consumer** | `assumed` | Physical bracket: Feng & Ma, [arXiv:2407.10290](https://arxiv.org/abs/2407.10290) Table II (on-wafer RDL ~5 ns, on-chip metal ~1 ns, cable 150 ns + ToF); nearest end-to-end is Tesla's [Hot Chips 34](https://doi.org/10.1109/HCS55958.2022.9895534) "100ns die-to-die latency", which is a **bonded in-tile** crossing | 1e-07 – 1e-06 | neither — **nothing reads it** | 300 ns is ~3× the only measured die-crossing figure and ~60× the on-wafer RDL hop, and it has never been checked because nothing charges it. See §4. |
| `links.ethernet.hop_latency_s` | 5e-06, `assumed`, sourced to this repository | **delete the block**, or label it a placeholder; if kept, 4.33e-06 | `assumed` | De Sensi et al., [arXiv:2408.14090](https://arxiv.org/abs/2408.14090) §V-B.1: Alps (Slingshot-11) 4.33 µs same switch, 5.56 µs across Dragonfly groups; LUMI 3.71 µs same switch | 3.7e-06 – 1e-05 | neither — **nothing reads it** | Exercised by no design in either study; the prose already says so in `docs/WAFER_VERSUS_ARRAY_LATENCY.md:106`, but the config entry still looks like a modelling input. |
| `links.ethernet.bytes_s` | 5e10, `assumed`, "400 GbE class NIC" | 5e10 (unchanged) | `assumed` → `published` | Tesla, [Hot Chips 34](https://doi.org/10.1109/HCS55958.2022.9895534), Dojo Interface Processor: "50 GB/s TTP over Ethernet (TTPoE) — Native hardware support" | 3.2e10 – 5e10 | neither — **nothing reads it** | Number is fine and can stop being assumed; the 32 vs 50 GB/s tension across the two Tesla decks is most likely the PCIe path (x16 Gen4 = 31.5 GB/s), not a contradiction. |
| `links.nvlink.hop_latency_s` | 1.5e-06, `assumed`, sourced to a vendor-marketing blog | **delete and repoint the tests at `nvlink5`**; if kept, 1.2e-06 | `assumed` | If kept, the sources `links.nvlink5.hop_latency_s` already carries: [arXiv:2607.16100](https://arxiv.org/abs/2607.16100) and NCCL `hwLatencies[NVLINK]` | 7e-07 – 5.5e-06 | neither — **no study reads it** | No design row, crossover or link plan names it; it survives only as the link of 24 synthetic `Topology` fixtures in `tests/test_roofline.py`. It is also the file's weakest citation while three measured NVLink latencies sit beside it. |
| `links.infiniband_hdr.hop_latency_s` | 4.5e-06, **`published`** | **Note MUST be corrected** (two factual errors). Point value should fall toward **~2.0–2.6 µs**; `range_high` must **rise** toward 22 µs | `published` (attribution), value unsettled | De Sensi et al., SC24, [arXiv:2408.14090](https://arxiv.org/abs/2408.14090) abstract, Table I and §V-B.1 | ~2.03e-06 – **2.2e-05** | **favours GPU** | The note says "five production supercomputers" (the paper characterizes **three**) and attributes Alps's Slingshot-Ethernet 4.33/5.56 µs pair to **Leonardo**, the A100 + InfiniBand-HDR machine this study actually prices — which measures **2.03 µs** same-switch and 4.23 µs across groups. |
| `links.infiniband_ndr.hop_latency_s` | 4.5e-06, **`published`**, note byte-identical to the HDR twin | same two corrections, **plus** disclose that it is a transfer from HDR-generation measurements | `published` (attribution), value unsettled | Same | ~2.03e-06 – 2.2e-05 | favours GPU | Listed separately so a writer does not fix one and miss the other. None of the three systems De Sensi et al. measured runs NDR — Leonardo is HDR, Alps and LUMI are Slingshot-11. |

---

# 2. READY TO APPLY

Ranked by how much each moves the DSV4-Pro / 554,700 mm² / batch 1 / 1M-context
headline of **8.328×**. Every direction is stated. Every mechanical edit is named.

### 2.1 — `links.infiniband_hdr` and `links.infiniband_ndr`: fix the note, then re-open the value. *Favours GPU. By far the largest single lever in the model.*

Two documentary errors, both verbatim-verified, duplicated word for word across
both entries:

1. "De Sensi et al. (SC24) measured 3.7–5.7 µs across **five** production
   supercomputers" — the abstract reads "This paper comprehensively characterizes
   **three** supercomputers — Alps, Leonardo, and LUMI"; Table I has three columns.
2. "on **Leonardo** (A100 + HDR InfiniBand) 4.33 µs within one switch rising to
   5.56 µs across switches" — §V-B.1 reads: "(from 4.33us to 5.56us **on Alps**),
   whereas **on Leonardo** it increases by 2× (from **2.03us to 4.23us**)". Alps is
   H100 + HPE Slingshot-11, an **Ethernet** Dragonfly. So the entry that prices the
   A100 study's scale-out fabric is carrying an Ethernet machine's number under an
   InfiniBand machine's name.

**The note fix is mandatory and uncontested. The value change is not a one-liner.**
Those figures are GPU-Aware **MPI** 1-byte ping-pongs (the paper states the choice
explicitly before Fig. 8), while a decode-step all-reduce runs on NCCL, and the
same paper's Observation 5 puts \*CCL an order of magnitude above MPI on small
inter-node transfers (~22 µs at 1 B on Leonardo, read off Fig. 7b). Under this
file's own convention for `nvlink3`/`nvlink5` — best measured kernel for the point,
hardware floor and shipped library for the ends — the point moves **down** to
~2.0–2.6 µs and `range_high` moves **up** toward 22 µs.

Headline sensitivity, re-run by the verifier:

| hop latency | headline ratio |
|---:|---:|
| 2.03 µs | 6.082× |
| 2.60 µs | 6.600× |
| 3.70 µs | 7.600× |
| 4.23 µs | 8.082× |
| **4.50 µs (current)** | **8.328×** |
| 5.70 µs | 9.419× |
| 22 µs | 24.240× |

Twenty-six of the thirty-two headline rows move. Qwen3-8B at 554,700 mm² goes
6.041× → 3.589×; n5_vs_b200 DSV4-Pro at 554,700 goes 4.006× → 2.728×. **The
honest output of this correction is not a new point value but a much wider
reported band: from ~7.6–9.4× today to ~6.1–24.2×.**

Also fix the mean-versus-median reading: the annotated Fig. 8a values are
outlier-inflated means (LUMI same-switch box ~2.5 µs against an annotated 3.71 µs
mean, Max 184.46 µs; Leonardo across-group median ~2.6 µs against a 4.23 µs mean,
Max 132 µs — the paper attributes this to network noise from other jobs). Only
Alps same-switch (4.33, min 3.64 / max 5.2) and Leonardo same-switch (2.03, min
1.9 / max 2.4) are tight enough for the mean to stand in for the distribution.

### 2.2 — `rom.cell_to_sram_cell_area_ratio` **and** `rom.array_efficiency`, applied atomically. *Favours GPU on capacity, favours ROM on latency — sign must be settled by a re-run, not an argument.*

0.2 → **0.33** and 0.7 → **0.52**, both `derived` from ROMA's compiler densities.
Net: **ROM capacity density 16.204 → 7.222 MB/mm², a 2.243× correction against the
ROM case.**

What this does, using the committed artifacts:

- DeepSeek-V4-Pro-0813's 892.7 GB checkpoint needs 55,091 mm² of ROM today and
  **123,557 mm²** corrected, while the headline point has only 75,809 mm² left
  after the 10% overhead and 8% interconnect fractions (charged additively) — so
  the headline design as configured becomes infeasible and must buy more wafers,
  and it is `link_latency`-bound, so more wafers cost it directly.
- 1,592 ROM points already fail on capacity and will fail harder.
- **But the offsetting effect is real and must not be dropped:** because the array
  is capacity-sized and `rom_read_bytes_s_per_mm2` is anchored separately (on
  YOLoC and the bitcell ratio — verified not to read either of these entries), a
  less dense array means *more* ROM mm² and therefore more parallel read
  bandwidth. The full-array sweep floor falls **76.6 µs → 34.1 µs** and the
  per-token ceiling rises **13,063 → 29,308 tok/s**. 773 ROM points bind on
  `weight_read` and will improve.

**Apply both in one edit and re-run, then diff the binding-constraint census.
Do not assume the sign.** If a reviewer rejects ROMA's one-third sentence, the
quotient `ratio / array_efficiency = 0.6408` and the 7.222 MB/mm² density still
stand; only the 0.33 / 0.52 split depends on it. Record which instance depth each
number came from — the internally consistent pairs from that one figure are
(ROM 0.424, SRAM 0.637) at 4096×64 and (ROM 0.520, SRAM 0.694) at 8192×64, and
depth alone moves ROM density by 1.23×.

### 2.3 — `rom.cim_precompute_area_fraction`: 0.02 → **0.18**. *Favours GPU. Compounds with 2.2.*

Applies to compute-in-ROM design rows only. Moves ~16% of the die from ROM array
to compute, cutting ROM from ~68% to ~52% of the die — a further ~1.3× on top of
the 2.243× above, so a compute-in-ROM point that fits today would need roughly
**2.9× more ROM silicon** under both corrections.

The strongest evidence is internal and checkable in this repository:
`roofline.py:1745-1755` sets `compute_mm2 = cim_precompute_area_fraction *
total_mm2` and that is the *only* compute area on a compute-in-ROM die — there is
no accumulator or adder-tree line item anywhere in the branch, and the ROM macro's
30% periphery budget is documented as decoders, sense amps and redundancy. **The
model charges a compute-in-ROM machine nothing for summing its selected partial
products.** That is a defect independent of what any paper says.

### 2.4 — `efficiencies.hbm_bandwidth`: 0.85 → **0.90**. *Favours GPU. ×0.982 on the headline.*

Headline GPU `weight_read` 1,282.38 → 1,211.03 µs, step 4,469.41 → 4,390.01 µs,
GPU 223.743 → 227.79 tok/s, **8.328× → 8.180×**. 746 of 1,020 feasible GPU points
bind HBM.

Apply the grade as `assumed` with the citation and the part named (the 90.5% is an
A100 PCIe 40GB at 1555 GB/s; the 91.3% is an H800 memory controller at the same
2039 GB/s HBM2e configuration as the modelled part). **Do not** implement the
proposed read/mixed split — Luo's method is already a mixed 5-read-to-1-write
coalesced stream (§3). And **delete any suggestion** that the A100 weight-bound
validation gate supports this number.

### 2.5 — `latency.array_pass_boundaries_per_layer`: make it per-model. *Favours GPU. ×0.9963 at the defensible reading.*

At 5.0 (DeepSeek's serially dependent matrix chain, the entry's own definition):
fixed budget 13,747 → 15,960 ns, +16.1%, headline **8.328× → 8.297×**. At 9.0
(counting `ATTEND`, `ROUTER_SCORE` and `MHC_PROJECT` as full array passes):
24,813 ns, +80.5% — a defensible upper reading but not the computed answer.

Apply as: **Qwen3-8B from the executed artifacts** (`executed`, artifact named);
**DeepSeek-V4-Flash derived from the graph contract**; **DeepSeek-V4-Pro by the
declared Flash→Pro architectural analogy**. State which quantity the entry holds —
serial dependency depth (4–5) or array occupancy (8) — because the same layer
honestly yields 4, 5 or 8 depending on which you name, and independent descriptors
pipeline rather than each paying a drain. **And fix the entry's
`what_would_settle_it`**, which currently tells the next reader that nothing
executed can be quoted; for Qwen3 something can.

### 2.6 — `latency.layer_barrier_s`: 8e-09 → **3.5e-08**, `range_low` → 8.6e-09. *Favours GPU. +12.0% on the fixed budget, ~+1.6 µs/token.*

The value is below the model's own arithmetic floor: crossing √815 = 28.548 mm at
1.5e-10 s/mm is 4.282 ns, and this entry is defined as a reduction *plus* a
completion broadcast over that same die — 8.565 ns of bare wire with zero logic.
`range_low` (4e-9) is below it too. The 3.5e-08 point is a bracket, not a
measurement (§3), and the note must say that the band contains **no fabricated
measurement of the thing it prices** — the nearest, IPU `popops::reduce` over
1,216 tiles, is 1.97 µs.

### 2.7 — `efficiencies.stage_balance`: guard fix, per-partition derivation, aggregate-only application. *Favours ROM, +1.18%. Flagged for extra scrutiny under the asymmetry rule.*

Three changes, of which the first is uncontested:

1. **Guard:** `device_count > 1` → `topology.pipeline_stages > 1`. Today 998 of
   3,092 feasible points (640 ROM, 358 GPU) pay 1/0.9 while having
   `pipeline_stages == 1`, and 130 ROM points with **zero** GPU points escape the
   derate entirely because they are one wafer — a structurally ROM-only escape
   hatch, since a GPU's partitions always equal its device count.
2. **Derive per partition** from `metadata.attention_sequence` plus the per-layer
   byte lists (both already in `configs/models/*.json`), using the minimax
   contiguous-partition formula the repository already implements at
   `analytical.py:781-782`. A single constant cannot be right for both DSV4-Pro at
   S=12 (0.8549 by that formula) and Qwen3-8B at S=12 (1.000).
3. **Apply to aggregate throughput only.** Per-user latency carries none —
   imbalance cancels for one token's serial traversal (§3).

Removing the derate from both sides at batch 1: ROM 1,947.43, GPU 231.12,
**8.328× → 8.4260×**. Because this favours ROM it deserves the extra scepticism
the program's rule demands; what stands behind it is `METHODOLOGY` §6a's own
derivation plus a checked second-order term (at the headline the busiest stage's
weight time, 20.35 µs, exceeds its KV time, 2.39 µs, by ~8.5×, so sum-of-max
equals sum-of-weight exactly).

### 2.8 — The energy ladder: apply the values, **drop the grades to `assumed`**, and record w4a8 as an interval. *Moves gates, not the headline.*

`bf16` 1e-13 → 3.3e-13, `fp32` 4e-13 → ~1.09e-12, `fp8` 3e-14 → 5.4e-14, `fp4`
1.5e-14 → 2.3e-14, `w4a8` 2e-14 → interval [2.33e-14, 5.42e-14],
`sram_read_j_per_byte` 1e-12 → 2.6e-12 (labelled a floor),
`static_leakage_w_per_mm2.rom_array` 0.0 → 6.7e-3.

At the DSV4-Pro batch-1 point the whole MAC ladder is **under 0.3% of ROM energy
per token and under 0.2% of GPU energy per token**, so none of this moves the
throughput headline. What it moves is gates, and the movements conflict:

- **A100 TDP gate 0.97× → 1.15×** (arithmetic 31.2 → 103.0 W, total 389.9 →
  461.7 W against a 400 W TDP). This is *more* correct, not less: SC'25 Table 2
  measures the A100 pinned at exactly 400 W while *losing* frequency (263 of
  312 TF/s) on HGEMM with random inputs, so a saturating-point model landing at
  1.15× is physical and the incumbent 0.97× was suspiciously good. Still inside
  the 2× tolerance.
- **HC1 gate 0.28× → ~0.34×** of 250 W (bf16 + sram_read: 70.2 → 84.0 W). It
  closes part of a failing gate, which is why it needs saying out loud — but it
  comes from a measured table on a GPU and it pushes the *other* gate away from
  1.0, which is the signature of a real correction rather than a fitted one.
- **ROM leakage moves the HC1 gate by nothing** (§3): HC1's static is
  max(enumerated 33.5 W, clocked-idle floor 50.0 W), so +2.3 W leaves the floor
  binding. It matters on wafer-class designs, where the 50 W-per-device floor
  cannot bind and 6.7e-3 W/mm² over hundreds of thousands of mm² is thousands of
  watts.

Every watt above is a register input under the `docs/SOURCES.md` power moratorium
and none of it is quotable as a result.

### 2.9 — `links.inter_wafer.switch_radix`: 16 → **4**. *Favours GPU. Moves zero headline rows.*

Published, conservative, and it should be applied — but it must be recorded as
moving nothing. Re-running both studies at radix 2/4/8 changes **no headline row
in either study**; the maximum headline ratio anywhere is unchanged at 10.781×.
336 of 4,688 points and 178 non-headline comparison rows move. The wafer-*hybrid*
topologies that are actually selected have `tensor_group = intra_domain_size = 57`,
so `across = ceil(57/57) = 1` and they emit no `inter_wafer` all-reduce at all.
Apply `links.inter_wafer.fabric` grade `assumed → derived` in the same edit, and
strike the "single switched domain / optimistic reading" sentence.

### 2.10 — Citation and documentation repairs with no numeric effect

These change no number and every one of them removes a false statement:

| what | where | fix |
|---|---|---|
| Taalas batch size | `technology.json`, `SOURCES.md` row `batch_size` | grade `assumed → published`; quote the deck footnote; delete "not published by Taalas" and "batch size stated nowhere" |
| **The batch-independence sentence — the highest-value documentary fix in the set** | `configs/hardware/technology.json:1019`, `docs/SOURCES.md:224`, `docs/COMPARISON_FAIRNESS_AUDIT.md:469` | **Strike it in all three files.** "The anchor rate is batch-independent for a dense model" is false under *every* policy: `roofline.py:2799` sets `engaged_weight_bytes = per_stream_bytes × effective_batch` (76.553 / 153.11 / 229.66 µs at B=1/2/3), and under `batched` the weight path is flat but compute rises 76.553 → 158.547 µs. Replace with the batch sweep in §1.1. |
| Taalas transistors | `SOURCES.md:221` | delete "No primary Taalas statement located"; cite the taalas.com/products spec line |
| Taalas 16,960 | `SOURCES.md` row `published_tokens_s_per_user` | cite the chart image URL and The Register's prose restatement; record the 0.0625 ms sibling residual |
| Taalas weight bits | `technology.json`, `SOURCES.md` | replace the CNX citation (verified to contain zero bit-width statements) with Bajic's taalas.com post; secondary should be Wavect |
| Taalas amortization | `technology.json` source field | replace "Taalas publishes no batch size and no microarchitecture" — both halves are false — with the two architecture patents; cite **13** US patents/applications, not 17; **do not record inventors** (unverifiable on the source used) |
| DeepSeek-R1 12,382 | `SOURCES.md` | add as a **named non-source** with "Simulated by Taalas Labs" quoted |
| `kv.index_layout` | `technology.json` note | retract the "more than 1.6×" sensitivity; state the current entry sizes and that the two layouts coincide |
| `kv.access_granularity_bytes.hbm` | `technology.json` note | grade → `published`; replace the HBM3 pseudo-channel derivation with the NVIDIA 32-byte sector statement; delete the retracted 68-byte index-entry example |
| `latency` block share | `docs/TECHNICAL_DIRECTION_RECOMMENDATION.md:1169` | replace "28–35% / 0.7–2.1%" with the artifact figures (ROM 0.0101–4.79%, GPU 0.0014–1.60%, 2.56% at the headline) |
| headline ratio | `docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md:11` vs `:100` | the file contradicts itself (8.6× vs 8.33×); 8.328× is the 554,700 mm² figure and 8.58× is the 92,450 mm² figure |
| `rom.cross_checks` | `technology.json` | disclose that the 28 nm 8,928 kb/mm² macro and the A-SSCC 2024 19,660 kb/mm² macro are **multi-level-cell** (2 and 4 bits/cell, BitROM Table III), and that 3D-METRO's 165.6 Mb/mm² is a **transistor-less 3D metal stack**, not a planar 1T upper bound |
| `efficiencies.no_clock_derate_rationale` | `technology.json` source field | its claim that "every density in this table is derived from an achieved shipping-silicon figure" is **false** for the ROM lane (YOLoC is SPICE-simulated with another paper's periphery grafted on) and unverifiable for the SRAM lane (dead Cerebras citation) |
| `power.fabric_clock_hz` | `technology.json` note | record that the HC1 clock negative is registered here, and that this key **does** feed the HC1 power gate (0.5 GHz → 70.16 W, 1.0 → 70.16 with the 50 W floor binding, 2.0 → 75.81 W; gate 0.2807 → 0.3032) |
| Config-drift hazard | `tools/run_roofline_studies.py:926` and `:931` | `stored = model.total_parameters * 3.5 / BITS_PER_BYTE` is **hard-coded** and emits `"weight_bits_per_parameter": 3.5` into the floorplan-comparison artifact without reading the config. If that entry ever moves, this line silently will not. |

### Net effect of applying everything in §2

The composable, sign-known corrections take the DSV4-Pro / 554,700 mm² headline
from **8.328× to roughly 6.0–6.6×** — the InfiniBand point value doing almost all
of it (×0.73–0.79), `hbm_bandwidth` ×0.982, `stage_balance` ×1.0118, array-pass
boundaries ×0.9963 — **a reduction of roughly 20–28%.** That is material.

The ROM capacity-density correction (§2.2) is **not** included in that figure
because its sign is genuinely unknown: it costs the ROM side 2.243× on capacity
and gains it 2.243× on the full-array sweep floor simultaneously, and which
dominates depends on which constraint each point binds. It must be settled by a
re-run and a binding-constraint census diff.

And the honest headline is not a point at all. Once `range_high` on the InfiniBand
entries rises to the shipped-library figure, **the reported GPU-scope band goes
from ~7.6–9.4× today to ~6.1–24.2×.**

---

# 3. STILL ASSUMED, AND WHY

Thirty-six of the fifty-six config keys in this document remain `assumed` after
verification. This is the list that tells a reader which conclusions are soft.

## 3.1 Where nothing is published, by domain

**Taalas HC1 (3)**

| key | what was searched | what would settle it |
|---|---|---|
| `weight_bits_per_parameter` | The whole of taalas.com (7 sitemap URLs, all substantive pages read), The Next Platform launch interview, The Register, ServeTheHome, Wavect ("Wavect did not independently benchmark HC1"), Kaitchup (author discloses he is a Taalas contractor), and 13 Taalas patents including the two on number format — which use 4-bit and 16-bit as **illustrative** alphabet sizes only | One number from Taalas or AMD: the fraction of Llama-3.1-8B parameters stored at 6 bits. Equivalently, HC1's total mask-ROM bit capacity, since parameters = 8,030,261,248 is fixed. A delayered cross-section with a countable ROM array pitch would close this **and** `rom.cell_to_sram_cell_area_ratio` at once. **No conference route exists** — Taalas appears in neither the Hot Chips 2026 nor the ISSCC 2026 program |
| `weight_amortization` | Both architecture patents read in full. US 2025/0123802 A1 states its parallelism axis three times in identical words ("a specific input can be multiplied by separate vectors simultaneously") and describes the serial alternative for multiple inputs; zero occurrences of "batch", "concurrent", "plurality of inputs" or "second side table". US 2025/0225198 A1's FIG. 4D applies four inputs at once but gives each its **own** side table and **own** storage area — weights replicated per input, the opposite of amortisation | A statement of HC1's per-chip **aggregate** token rate at any concurrency above one. If aggregate equals per-user, `per_stream` is confirmed; if it scales, the entry must move to `batched` and the study's aggregate ROM numbers change by up to 20.7× |
| `clock_frequency_hz` (absent) / `power.fabric_clock_hz` | See §1.1 — an exhaustive negative across vendor site, press, patents and two conference programs, reproduced independently | A vendor spec sheet, a Hot Chips or ISSCC paper (neither exists as of 2026-08-31), or a die photograph with an identifiable PLL and a stated operating point |

**ROM physical (4)**

| key | what was searched | what would settle it |
|---|---|---|
| `rom.cim_cell_area_multiplier` | Every published compute-in-ROM cell. Both analog CiM cells (YOLoC, Yin et al.) are literally 1T doing both jobs, so the multiplier is 1.0 *for those architectures* — but they multiply by dumping charge on a shared bitline, not by selecting a pre-computed partial product, and nobody has published the cell this model builds | A layout or die shot of a compute-in-ROM cell with a select/pass device, with its area given against a storage-only ROM cell **in the same paper's table**. Alternatively, laying out both cells on the SKY130 or IHP decks this program has already hardened would measure the ratio directly at level 8 of the open-PDK ladder |
| `rom.cim_precompute_area_fraction` | TOM's 18% is the only unambiguous die-level compute share found; 3D-METRO's area pie could not be opened (ACM DL returns 403) and the "value-aware balanced adder tree" attributed to DSC-ROM and the CCMCC macro appears in neither abstract retrieved | A floorplan of a compute-in-ROM tile separating the per-region pre-computation block from the accumulation and from the ROM array, with three areas stated. Failing that: synthesise the 2^b shift-add pre-compute block plus the accumulator tree against the ROM array it feeds, on the Nangate45 flow already used in GEN-RTL-IMPL |
| `efficiencies.rom_read_bandwidth` | No fabricated mask-ROM array has published a sustained-versus-peak read fraction | A sustained linear-read measurement on a fabricated ROM array reported against the same array's single-access cycle time — the ratio at the **array** boundary, not the macro-plus-compute boundary. A bounded version is available from this program's own SPICE ladder, but needs the compact-array gate that is already named as open |
| `efficiencies.sram_read_bandwidth` | No published achieved-versus-peak local SRAM read fraction for a wafer-scale or IPU-class part; Cerebras publishes an aggregate advertised bandwidth, not an achieved fraction under a gather | A Cerebras SDK microbenchmark, a Graphcore IPU exchange-memory benchmark, or any peer-reviewed sustained on-die SRAM read rate under a real gather. **Note the provenance problem underneath is worse than the derate:** `SRC-CEREBRAS-WSE2` carries no URL, document, date or hash, and its cited page no longer contains its value |

**Energy (9)** — all five MAC rungs, `sram_read_j_per_byte`,
`operand_delivery_j_per_byte`, `rom_read_j_per_byte`, `static_leakage.rom_array`.

| key | what was searched | what would settle it |
|---|---|---|
| `mac_energy_j_per_op.w4a8` **← the one that matters** | Nobody publishes a mixed 4-bit-weight × 8-bit-activation MAC energy | A fabricated w4a8 MAC macro at a leading node reporting per-op energy, or a per-format energy breakdown from a shipping part implementing w4a8 natively (NVIDIA's NVFP4 / MXFP4 paths would qualify if the vendor published per-format **energy** rather than only per-format throughput) |
| `.bf16`, `.fp32`, `.fp8`, `.fp4` | SC'25 resolves control vs datapath but cannot resolve register-file vs multiplier-array **inside** the datapath, and the split it does report is not physical (§4) | A vendor or peer-reviewed per-MAC energy for a leading-node BF16 tensor datapath measured at the ALU boundary alone; for fp8, a fabricated FP8 e4m3 MAC array at N6/N7 at nominal supply with SRAM traffic excluded (everything published is INT8, or whole-accelerator, or at a near-threshold voltage chosen to win a TOPS/W headline) |
| `sram_read_j_per_byte` | No vendor macro energy for the target arrays; the one Horowitz-sourced SRAM figure that could be opened (EIE Table I, 32-bit 32 KB SRAM = 5 pJ = 1.25 pJ/B at 45 nm) is **half** the 2.5 pJ/B the recommendation cited for the same cache | A foundry or memory-compiler datasheet giving read energy per access for an N6/N7 high-density SRAM macro ≥ 1 Mbit at a stated supply and access granularity. That single number would also settle whether the dropped row-decode share is 10% or 50% of the control plane |
| `operand_delivery_j_per_byte` | No source addresses this term's boundary at all | A per-byte energy for the path from an on-die array's output to a MAC input at N6/N7 with the array read excluded. Failing that, a foundry statement of the 45nm→N7 dynamic-energy ratio for standard-cell logic, which is the one assumption the register-file component rests on |
| `rom_read_j_per_byte` | Only Ankhdjet (SKY130 ngspice, not silicon) and TOM (7 nm synthesis + P&R, not silicon) | A fabricated leading-node mask-ROM macro reporting read energy at the macro boundary **and stating its sense scheme** — full-swing digital sampler vs clocked analog comparator, a distinction worth ~5× on this entry that no published macro reports at a leading node. **`assumed` is required here regardless**, by `METHODOLOGY` §9 |
| `static_leakage.rom_array` | Ankhdjet's leakage column exists but scaling 130 nm to N6 needs a per-device Ioff ratio that is itself unpublished and two orders of magnitude; the product lands above the cooling limit | A fabricated leading-node mask-ROM macro reporting standby current at a stated PVT, or a foundry Ioff-per-micron for the device flavour a ROM array would use. Failing either, an ASAP7 place-and-route of a large NOR mask-ROM array **in this repository** would turn every step into an `executed` number — the capability already exists at `results/physical_abi3/asap7` |

**Latency (5 + 1 hybrid)**

| key | what was searched | what would settle it |
|---|---|---|
| `pipeline_fill_drain_s` | TPUv1 is the only fabricated inference accelerator in this class publishing an array depth. The two CIM macros the register cites report TOPS/W, GOPS and Mb/mm² but no cycle time — **recorded as a single-agent negative**, since IEEE Xplore returned no body to either agent | A declared array organisation and depth for the modelled ROM fabric — systolic (2N−1) versus CIM-plus-adder-tree (log₂ lanes), a 32× difference. Or a published macro-level compute latency for a fabricated ROM-CiM array; no leading-node CIM macro found reports one |
| `layer_barrier_s` | IPU and Cerebras are the only fabricated on-die fabrics with published collective latencies, and neither isolates a barrier from its transfer | A declared on-die lane/tile topology and hop latency, after which this stops being a scalar and becomes derived by `METHODOLOGY` §6's own formula — which §6 already requires of every other collective. Failing that, a measured hardware-barrier latency with the barrier isolated from the transfer |
| `sparse_index_dependency_s` | Nothing published prices a top-k dependency of this shape | A declared top-k selection structure and its depth at 250,000 candidates (tournament tree is log-depth, ~11 vs 18 levels; bitonic partial sort is O(log²N), ~66 vs ~171 stages) plus the KV tier the dependent gather lands in — an on-die SRAM gather (20.6 ns) and an HBM gather (330.7 ns) differ by 16× and the entry charges one number to both |
| `global_wire_delay_s_per_mm` | IEEE Xplore returns no body; the IRDS 2023 edition has **no Interconnect chapter** (every chapter URL enumerated), and `2023IRDS_MM.pdf` has zero per-mm delay statements. Web-search budget exhausted before keyword search | A foundry-published repeatered-interconnect delay per mm at N6/N5 (a wire-load model or an IRDS Interconnect table). More to the point: a declared on-die distribution network, so the traversal is priced as hops × hop latency the way §6 already requires |
| `sram_access_s` | TSMC's own N7 256 Mb and N5 135 Mb macro papers exist but report Vmin, bitcell area and write-assist — **not clk-to-Q** | A published access time (clk-to-Q, not Vmin or density) for a leading-node macro at the capacity and bank organisation the model places for KV, plus a stated bank/crossbar organisation, so macro time and subsystem time stop hiding inside one scalar |
| `sequencer_issue_decode_s` *(hybrid)* | TPUv1's 4-stage CISC pipeline is published; the clock it is divided by is not | An RTL or published pipeline diagram for the modelled sequencer. A microcoded machine could be 8–16 stages, landing at the top of the band or above it. **Half of this is now in the repository and the useful half is not.** `rtl/abi3/ot_a3_microsequencer.sv` and its control plane exist and are correlated against `runtime.sim.device.Device` on the shipped deployment images (`results/rtl/abi3_deployment_campaign.json`; `correlated_cases` names which ones), so the *machine* is no longer hypothetical — but that campaign is functional and establishes **no timing quantity whatever**, and no block of that control plane has been synthesised or routed at all, so it yields neither a stage count that can be divided by a clock nor a clock. What would close this entry is a synthesis and static-timing run of `ot_a3_microsequencer` in one of the two established views, which would make it `executed` at that node and still forbid scaling to N6/N5/N7/N4 |

**Floorplan and HBM (3)**

| key | what was searched | what would settle it |
|---|---|---|
| `floorplan.interconnect_area_fraction` | No published die floorplan separates on-chip interconnect area from clock, power grid and whitespace. On GA100 the interconnect is invisible — the crossbar is distributed and the two central SRAM-dense blocks are L2/hub, not a separable NoC. NVIDIA's Simba (MICRO 2019) and Intel's 80-core TeraFLOPS chip are the obvious next leads and **neither was verified**; web-search budget was exhausted | A published accelerator floorplan with the on-chip network as a named area line item. **Far better for this specific term:** a floorplan of the bank-to-compute crossbar in this repository's own RTL campaign (`rtl/build/implementation_campaign` already produces post-route SPEF-extracted results), which would make this `executed` rather than borrowed |
| `hbm.hbm3e.stack_beachfront_mm`, `hbm.hbm3e.phy_area_mm2_per_stack` | No GH100, GB100 or B200 die photograph is on Wikimedia Commons; Micron's HBM3E product page states no package dimension; no JEDEC JESD238 package outline is public | A GH100 or B200 die photograph measured the same way, or an SK hynix / Samsung / Micron HBM3E mechanical drawing. For the PHY area specifically, ECTC 2026's "Signal and Power Integrity Co-Analysis of Chiplet(UCIe)-based GPU-HBM Interconnect for Reduced PHY Area" ([doi:10.1109/ectc51846.2026.00040](https://doi.org/10.1109/ectc51846.2026.00040)) is on exactly this quantity and is closed access |

**Efficiency derates (7)**

| key | what was searched | what would settle it |
|---|---|---|
| `efficiencies.compute` | Every published MFU figure found is whole-kernel and therefore a lower bound on a compute-only derate | An executed, compute-bound decode kernel on the modelled operator mix with achieved ops/s over the same part's published dense roof, memory and collectives excluded. This repository's own executed Qwen3 lane could produce it if it emitted achieved-ops counters |
| `efficiencies.hbm_bandwidth` | Closed for the sequential/mixed stream (§2.4); **open for the KV path** | A measured achieved/peak on a mixed read+write+**gather** stream at the modelled entry size on HBM2e silicon — a paged-KV kernel instrumented at the memory controller, not at wall clock |
| `efficiencies.hbm_capacity` | vLLM's 0.92 is a policy default, not a hardware limit | A measured allocator high-water mark for the modelled model and batch on an 80 GB part, separating weights, activation workspace and KV. For the missing SRAM counterpart: a floorplanned bank map for the proposed array — which does not exist because the array has not been floorplanned |
| `efficiencies.stage_balance` | The partition arithmetic is now derivable in-repo; what is not derivable is the residual | A measured layer-to-stage assignment and per-stage step time for a real DeepSeek-class pipeline deployment, giving the residual beyond the arithmetic (embedding on stage 0, LM head on the last, uneven attention cost) |
| `efficiencies.expert_router_imbalance` | Wang's MaxVio is published but at 64 routed / 6 activated, 6× coarser than DSV4-Pro's 384 top-6, and on mixed training data rather than serving traffic | A routing trace from production decode serving at the modelled expert count, giving the per-layer token distribution over experts for realistic concurrent batches. The profile's own `router_trace_status` already reads "synthetic except exact hash tables; no production activations", so this is a **named, open gate rather than a hidden one** |
| `kv.access_granularity_bytes.sram` | No published value; SRAM compiler word widths are integrator-configurable | A target-foundry SRAM macro datasheet giving word width and column-mux ratio — which `METHODOLOGY` §9 says does not exist until a foundry supplies a characterised macro. **Until a profile carries an entry size that is not a power-of-two multiple of the granule, a sweep will report zero sensitivity and should say so rather than reporting a flat line as robustness** |
| `kv.index_layout` | Not searchable — it is a declared design **choice**, and a choice cannot be graded published | Nothing external. Keep it a declared choice; if a future profile carries an index entry that does not divide the granule, sweep both layouts side by side rather than selecting one |

**Links (4)** — of which only `links.inter_wafer.hop_latency_s` is read by
anything. The other three (`links.on_package.hop_latency_s`,
`links.ethernet.hop_latency_s`, `links.nvlink.hop_latency_s`) have no consumer at
all; see §5.1.

| key | what was searched | what would settle it |
|---|---|---|
| `links.inter_wafer.hop_latency_s` | Cerebras publishes a **bound** ("<5us") and no vendor publishes a wafer-to-wafer latency. The physical floor is far below: a cable hop is 150 ns + time-of-flight at the PHY, so the 3.7–5.6 µs this rests on is ~25× protocol, NIC and software | A measured wafer-to-wafer latency: Cerebras publishing a SwarmX or CS-3-IO number rather than a bound, or a third-party ping-pong between buffers on two CS systems. Second best: any published RoCE-over-100GbE accelerator-buffer-to-accelerator-buffer ping-pong, which would pin the high end the way Slingshot pins the low end |

## 3.2 Values that carry a grade but whose point is genuinely unsettled

Three entries are formally graded `published` yet their **value** is open, which is
a subtler trap than an honest `assumed`:

1. **`links.infiniband_hdr` / `links.infiniband_ndr` `hop_latency_s`** — the
   attribution is wrong and the point sits between two measurement conventions
   (MPI ping-pong ~2.0 µs, shipped collective library ~22 µs on the same link).
   The headline is near-linear in it. See §2.1.
2. **`reference_parts.taalas_hc1.power_w`** — 250 W is graded `published` on a
   third-party Substack; the primary vendor figure is 200 W; and the anchor code
   reads only `range_low` and `value`, so the two cannot both be represented
   without either a code change or leaving the value at 250. See §4.
3. **`reference_parts.taalas_hc1.batch_size`** — recommended `published`, but the
   BS=1 footnote is on the sibling cost/latency slide rather than the 16,960
   throughput slide, and the two slides differ by 6% on the HC1 bar (and 10% on
   the Nvidia bar). A maximally conservative writer may grade it `derived` from
   the deck; the image URL is given so a reader checks rather than trusts.

---

# 4. REFUTED

What a researcher proposed and a verifier rejected, with the reason. Recording
these stops them being re-proposed, and the reasons are usually more instructive
than the accepted figures.

## 4.1 Refuted because the mechanism was misread in this repository's own code

**`taalas_hc1.power_w` → 200 W: the recommendation's own safeguard does not exist.**
The proposal was "keep 250 as `range_high` to preserve the harder end for
reporting". `taalas_hc1_power_anchor` (`roofline.py:3957-3980`) reads `low =
spec['power_w'].get('range_low', value)` and reports `published_band_w = [low,
published.value]`; **`range_high` is never read for power anywhere.** Verified by
running both: value=250 gives band [200, 250], ratio 0.2807, band-low 0.3508;
value=200 gives band [200, 200] and 0.3508 at *both* ends. The shipped artifact
today reads "200.0-250.0 W \| 70.2 W \| 0.28x \| FAIL" (`REPORT.md:82`).
**Adopting the recommendation as written deletes the 0.28× conservative reading
from the report** — an undeclared ROM-favouring side effect inside a
recommendation that flagged its direction honestly but mis-stated its mechanism.
*Disposition:* record 200 W as the better-sourced card figure; keep the reported
band 200–250; either leave value at 250 with a rewritten note, or change the
anchor to read `range_high` — **a code change the writer must not make silently.**
Note also that `thermal.cooling_limit_w_per_mm2`'s cross-check ("Taalas HC1 at a
reported 250 W over 815 mm² is 0.31 W/mm²") becomes 0.245 W/mm² if the value moves.

**ROM leakage "moves the HC1 gate from 0.281× to 0.290×": it moves it by nothing.**
Leakage is static, and HC1's static is charged as max(enumerated, clocked-idle
floor). `REPORT.md` states the enumerated static is 33.5 W and the floor is 50.0 W,
so the floor binds and the total reproduces exactly as 3.2 + 3.3 + 10.0 + 3.7 +
50.0 = 70.2 W. Adding 2.3 W takes the enumeration to 35.8 W, still below 50.0.
The entry still matters — on wafer-class designs the per-device floor cannot bind —
but the stated gate movement must not be recorded.

**`efficiencies.stage_balance` direction: the sign is backwards.** Proposed as
`favours_gpu`, ×0.9427 against ROM. Under `METHODOLOGY` §6a's own derivation stage
imbalance **cancels** for one user's serial traversal, and at batch 1 there is one
token in flight (the report says so itself: "where the batch is smaller than that,
the surplus slots idle"). Correct treatment gives ×1.0118 **for** ROM. Its stated
reason for `still_assumed` is also false — `metadata.attention_sequence` **is** the
per-layer attention-kind map, present in all three profiles, and using it
reproduces `kv_transfer_bytes_per_step` exactly on two independent points. And the
claim that the weight-byte balance is a *lower* bound on imbalance is false at the
headline: the KV-inclusive balance at S=12 is 0.8685 against the weight-only
0.8549, i.e. including KV makes the balance **better**. Finally, the reported
values do not come from the stated formula (0.848 is the uniform (L/S)/ceil(L/S)
form; the minimax binary search gives 0.8549 or 0.8472, and S=61 gives 0.9719 or
1.000, not 0.999).

**`hbm.hbm2e.stack_beachfront_mm` direction "neutral": it is one of the
highest-leverage entries in its domain.** `max_hbm_stacks_per_device`
(`roofline.py:1565-1582`) computes floor(4·√46225 · 0.60 / 12.0) = floor(**43.0**),
an exact integer knife edge, and the winning ROM design at every batch ≥ 16 carries
exactly 43 stacks per device and binds `kv_read`. Holding 12.0 rather than the
measured 12.13–12.15 mm silicon pitch is what keeps the count at 43 instead of 42 —
a 2.3% ROM-favouring choice presented as neutral.

**`gpu_device_budget` "takes capacity/bandwidth/roofs from `published_roofs`":
it does not for the anchor part.** `reference_parts.a100_sxm_80gb` has no
`published_format_roofs_ops_s` field, so the code falls through to
`devices × area × compute_ops_s_per_mm2`. Numerically a no-op (the density is
312e12/826 anchored on the A100 at N7, so it round-trips to exactly 312 TFLOPS)
and the conclusion stands — **but a note must not cite a code path the anchor part
does not take.**

## 4.2 Refuted because the source says something else

**`efficiencies.compute` "sits inside a published bracket of 0.52–0.76".** Both
endpoints are whole-kernel MFUs — observed FLOPs/s over peak across wall clock —
so they already contain memory time and collectives, which the model charges
separately. A 0.76 whole-kernel MFU on a compute-bound phase therefore implies a
compute-only sustained fraction of **at least** 0.76. Both endpoints are lower
bounds; **0.55 sits below the published floor, not inside a bracket.** Keep the
value (it is the conservative-for-ROM choice), keep the grade `assumed`, restate
the note as a one-sided bound.

**The bf16 boundary argument, refuted by the paper's own text.** The proposal keeps
the 0.33 datapath plane "to avoid double-counting the register file against
`operand_delivery`". SC'25 says the opposite twice: (i) "vector datapath energy
will include not only the computation itself, but also two register file accesses
on average", so the datapath plane is precisely the one that *contains* the RF; and
(ii) "tensor cores and matrix units further amortize not only control energy, but
also register file energy", so there is little RF energy in a matrix number to
double-count. The subsidiary claim that matrix "control" is instruction fetch is
refuted by the same table — A100 vector-FP16 control is 8.47 pJ/FLOP against matrix
control 0.37, a 23× amortization.

**The SC'25 planes are operational, not architectural.** §4.1: "When performing
computations on random values, we exercise both the control and data planes …
Conversely, by performing computations on zeros, we exercise only the control
plane." Datapath is the **data-dependent switching increment**, not "the energy
inside the ALU" — and the two are measured at different V/f points ("computation on
zeros never reaches TDP … clock rates are never capped … computation on random
numbers will hit TDP"). Table 2 confirms: A100 HGEMM random 400 W at 263 TF/s
(clipped) against zeros 271 W at 291 TF/s (boosted). Datapath = Total(clipped)
minus Control(boosted) is biased low by a known mechanism.

**The control/datapath split is not physical at the precision the whole ladder
leans on.** On the same die and the same tensor core, A100 Matrix-TF32 datapath is
0.11 pJ/FLOP against Matrix-FP16 datapath 0.33 — **three times less** datapath
energy for the same 10-bit mantissa — while control moves the other way (1.13 vs
0.37). The totals behave (1.24 vs 0.70 = 1.77×, the half-rate amortization Table 2
shows directly as 338 W at 141 TF/s against 271 W at 291 TF/s); the split does not.
**All five MAC entries are anchored on the FP16 datapath cell.**

**The fp32 Horowitz figure is misquoted.** 45 nm 32-bit float MULT is **3.7 pJ**,
not 4 (EIE Table I, Horowitz a co-author, citing his own Stanford VLSI wiki table:
int ADD 0.1, float ADD 0.9, int MULT 3.1, **float MULT 3.7**). So the MAC is 4.6 pJ
and the ratio 3.29 (or 3.07), not 3.50 — the recommended 1.2e-12 is 6–14% high on
its own stated formula. And the "cross-check that lands almost on top of it"
(Matrix-TF32 total 1.24 pJ/FLOP) is a coincidence: TF32 and FP16 share a 10-bit
mantissa, so the gap cannot be a mantissa-width effect.

**Luo's method already is a mixed stream.** The proposed split of
`efficiencies.hbm_bandwidth` into a 0.90 "read stream" and a 0.85 "mixed KV" is
refuted by the very table it cites: §III-A-4 states "**each thread reads 5 times
and writes 1 time**". The 90.5% is already a mixed 5:1 coalesced stream. The only
pattern genuinely uncovered is the random top-k **gather**, which is what a split
should be drawn around if one is wanted.

**The 63% HBM beachfront-utilisation reading.** Proposed as the physical ceiling a
shipping GPU takes, against the incumbent 52%. Two defects: 6 × 12.15 mm counts
**six** PHY sites while only **five** ship on any A100 (populated beachfront
5 × 11.92 = 59.6 mm of a 115.74 mm perimeter = 51.5%, which is what the incumbent
52% describes); and the three sites per edge span 30.42 mm of a 32.293 mm edge
while the packages **overhang the die** by ~1.5 mm at each end (measured on
NVIDIA's own Fig. 3: HBM column 484 px against die 443 px). Adopting 0.63 would
hand the headline ROM wafer 45 stacks instead of 43, **+4.7% ROM KV bandwidth on a
reading that charges pitch the die does not own.** This is the single change in the
whole body of work that would have moved the headline toward ROM on bad evidence.

**`power.memory_interface_idle_w_per_stack` `range_low` 1.2 → 2.1.** The formula
treats a published pJ/bit as *marginal dynamic* energy; DRAM pJ/bit figures are
conventionally *total* energy per bit at high utilisation (including the 7 pJ/bit
the DATE paper itself quotes, which comes from Xilinx WP485, **not** SK hynix Hot
Chips as stated). Under the total reading the same measurement gives 1.50 W at
3.9 pJ/bit and 2.69 W at 7 pJ/bit, so 1.2 is not refuted. This move favours ROM and
rests entirely on a units/boundary interpretation — the exact failure class the
program has been burned by. **Keep 2.8, keep the source, do not move `range_low`.**
The supporting sentence that "1.2 W omits the always-on base-die PHY, which the
measurement shows dominates" must **not** be recorded: the paper reports
**normalized** power only and never decomposes idle into core versus base die.

**Cerebras SwarmX radix: "the one load-bearing correction" is not load-bearing.**
Re-running both studies at radix 2/4/8 changes **zero headline rows** and leaves the
maximum headline ratio unchanged at 10.781×. The specific supporting claim — that
wafer-tensor designs are selected as headline rows at DSV4-Pro 277,350 / 369,800 /
554,700 mm² — is false against the artifact: those three rows are wafer-**hybrid**,
whose `tensor_group = intra_domain_size = 57` gives `across = ceil(57/57) = 1` and
generates no `inter_wafer` all-reduce at all. The only wafer-tensor rows selected
are the x1 rows at 46,225 mm² (single wafer, no inter-wafer event whatsoever). The
correction is still right and should be made; it must be recorded as moving no
headline.

**TOM is not independent corroboration of ROMA.** They share four authors
(including ROMA's first author) and TOM cites ROMA as its reference [49]. It
genuinely confirms the *reading* of ROMA's figure and the MB/Mbit convention —
worth having — but it is one measurement reported twice. The "I corroborated it two
ways" framing overstates the evidence base by exactly one source.

**TOM's area decomposition does not have four categories.** The cited "ROM 58%,
SRAM 24%, Compute 18%, KV inject 2%" sums to 102% and the fourth is not in the
paper. TOM's *text* states three, summing to 100%. Cite the sentence, not the pie.

**`efficiencies.rom_read_bandwidth`: both legs of the reasoning are wrong, though
the recommendation is right.** (i) YOLoC's 28.8 GOPS is **not** an achieved rate —
§4.1 verbatim: "SRAM-CiM and ROM-CiM macro parameters are all obtained from
parasitic extraction and SPICE simulation in 28nm CMOS", and its 5 Mb/mm² macro
density is quoted "using the computing peripheral circuits from [3]", another
paper's periphery grafted on. (ii) There is no tension with
`efficiencies.no_clock_derate_rationale`, whose last sentence explicitly exempts the
named sustained-fraction derates. **Do not record that rationale** — as written it
is a standing argument for raising the parameter to 1.0, worth a straight 1.33× to
every ROM weight-read rate, built on a premise the source refutes.

**The "TOM agrees with the model, not the published part" cross-check — the one
pro-ROM inference in the energy domain.** 5.33 W is the **post-gating** figure;
TOM's Fig. 12 is labelled "Power Breakdown Before and After Applying
Workload-Aware Dynamic Power Gating" with **Before = 25.813 W**. TOM's ungated
power density is 0.454 W/mm² — 5.3× the model's HC1 reconstruction and **above**
the published HC1's 0.25–0.31 W/mm². Read the other way, TOM is independent support
for `METHODOLOGY` §7a's own statement that the power model under-reports by 7–9×:
0.454 / 0.086 = 5.3× sits inside that band.

## 4.3 Refuted because the range or the grade outran the evidence

**`weight_bits_per_parameter` `range_high` 6.0 → 5.68: mislabelled, and it runs the
wrong way.** Proposed as "GPU-favouring in the trivial sense that it removes an
infeasible sweep point that was scoring zero anyway". It is the opposite:
`run_roofline_studies.py:2803` sweeps 3.0/3.5/4.0/5.0/6.0, so the artifact
currently **publishes a row in which the model's own reconstruction of a shipping
part is infeasible at the top of the vendor's own stated bit range.** Deleting that
point removes a visible failure of the reconstruction from the report, which
favours ROM. **Keep `range_high` at 6.0** and record the computed 5.678-bit
feasibility edge in the note as an outcome under `METHODOLOGY` §1a. Related: the
claim that 3.5 "sits in the ROM-favouring third of its own bracket with no evidence
placing it there" is wrong — Bajic in the same interview says "We can store four
bits away and do the multiply related to it — everything — with a single
transistor", which this repository **already quotes** in
`rom.compute_cell_to_rom_cell_area_ratio`, and it points at 4.0 bits.

**Grade `published` for `rom.cell_to_sram_cell_area_ratio` is not honest under this
repo's own taxonomy.** ROMA is a peer-reviewed **third party** quoting the output of
a proprietary TSMC compiler, in a synthesis-only paper with no place-and-route and
no tapeout ("We implement and synthesize ROMA in Verilog … Synopsys Design
Compiler with the TSMC 7nm standard library"). TSMC has said nothing. Record it as
`derived`, or keep `published` only with the source field naming ROMA as a third
party rather than the foundry.

**Grade `measured` for the GPU die-area audit answer.** A Wikimedia Commons upload
with Artist = "Unknown author", credited to a commercial die-shot gallery, uploaded
three months ago, is not "fabricated silicon reported in a peer-reviewed venue".
The NVIDIA whitepaper legs are `published`; the photographic legs are `derived`
from a self-performed measurement of a third-party image, and the note should say
so (corroborated by NVIDIA's Fig. 3 and the source gallery's stated
32.35 × 25.65 mm).

**Grades `derived` on `sram_read_j_per_byte`, `w4a8`, `efficiencies.hbm_capacity`,
`efficiencies.hbm_bandwidth` (`measured`), the hbm3e pair, and
`array_pass_boundaries_per_layer`.** In each case the label outruns the evidence:
"take the datapath column and multiply by 8" is a formula but the **plane
selection** does all the work and has no published basis; w4a8's interpolation
shape has no source; nothing computes 0.90 from vLLM's 0.92; `arXiv:2402.13499`
carries no journal reference and its own text says results can be reproduced
"after the review process"; the hbm3e entries are transfers, not derivations; and
running `build_official_graph_contract()` is closer to `executed` than `derived`,
except that `executed` requires a committed artifact naming the number.

**`rom.cim_cell_area_multiplier` bracket 1.16–1.94: wrong area, wrong label.**
ROMA's chip area is **503.7 mm²**, not 300 — the 300 is TOM's third-party estimate
of ROMA's ROM alone. From ROMA's own figures the correct bracket is **1.39–2.34**
(L-Units 73.2% of 503.7 = 368.7 mm² holding 1.86 GB = 40.4 Mbit/mm² fused; Fig. 12
L-Unit areas give a standard-compiler-ROM-plus-compute L-Unit at 24.7 Mbit/mm²).
1.6 still sits inside it, on a one-paper chain instead of a three-step chain across
two. And the route to 1.94 via ROMA's "40% smaller than standard ROM" is not a
bracket end at all — that is a B-ROM-versus-standard-ROM **storage** claim, not a
compute-versus-no-compute claim.

**`latency.pipeline_fill_drain_s` `range_high` 7.3e-07 imports a 28 nm part's
clock** — the exact error the same agent correctly refuses to make one entry later.
730 ns is 511 cycles at TPUv1's own 700 MHz; at the model's own
`power.fabric_clock_hz` = 1 GHz the same published depth gives **5.11e-07**.

**`latency.sram_access_s` `range_high` → 2.06e-08 is a granularity substitution.**
A100 "Shared 29.0 clocks" is a full LDS instruction round trip through the SM —
address computation, LSU issue, bank access, register writeback — while this entry
prices a macro access. The number is real; it measures something strictly larger,
the same way "a stitched mesh charged one flat hop" used a real hop latency for the
wrong span. **Keep the 1–4 ns band**; put the 20.6 ns in the note as what a GPU's
SRAM *path* costs.

**`latency.global_wire_delay_s_per_mm` `range_high` → 8e-10 mixes two physical
quantities.** 0.8 ns/mm is the marginal per-mm cost of a **buffered routed fabric**
(1.25 ns per island of routing), not wire RC — and the mm it is divided by is not
published, since the cited paper states no die area. `METHODOLOGY` §6 already
forbids pricing a traversal as a flat scalar. **Keep `range_high` at 2.5e-10**,
record the finding in the note, and add a separate derived traversal term.

**`layer_barrier_s` = 35 ns is not the quantity claimed.** 133 − 98 subtracts an
**average** from a **maximum** (Table 4.1(a): "average latency value over a large
number of experiments"; §4.1.2: "98 ns (the highest)"). The like-for-like
subtraction puts the IPU's synchronisation phase at ~70–80 ns. The error's
direction makes 35 ns an *understatement*, so it is conservative — but it should
not be sourced to an arithmetic the paper does not support. The entry also **missed
the paper's direct measurement** of what it prices: Table 4.16, "1 IPU, all 1,216
tiles, 1 operand per tile" = **1.97 µs** total (single-tile baseline 0.44 µs), 56×
the recommendation and 250× the incumbent — though it is `popops::reduce` through
the Poplar SDK, not a hardware barrier.

**`array_pass_boundaries_per_layer` = 9.0 is the top of the band, not its centre.**
Under the entry's own definition ("serially dependent **matrix** passes") the
DeepSeek value is 5 and the Qwen3 value is **4 — the incumbent, and exactly the
incumbent's own enumeration.** So "every model in the study exceeds 4" is false, and
`range_high = 5.0` is not "exactly the Qwen3 count" under the matmul reading.

**Adopting the latency ceilings jointly breaks the HC1 gate.** Fill 730 ns +
barrier 200 ns + boundaries 10 + sparse 331 ns takes the DSV4-Pro band-high fixed
budget from 52.0 to **469.3 µs/token** (87% of the 536.7 µs step), the headline
band-high ratio from 7.84× to 4.96×, and the HC1 anchor to ~0.19× against a stated
2× tolerance, where it currently passes at 0.59×. `METHODOLOGY` §1a requires a
failing gate to be reported rather than fitted — but the writer must know this
before recording the ceilings.

**`efficiencies.expert_router_imbalance`: 1.04 is a 6×-granularity extrapolation
and the wrong phase's redundancy is cited.** Wang's models carry 64 routed experts
with 6 activated against DSV4-Pro's 384 top-6. And this is a **decode-only** study
while the cited redundancy (32 experts, ~12.5%) is from DeepSeek-V3 §3.4.1
**prefilling**; §3.4.2 decoding provisions "64 GPUs … for hosting redundant experts
and shared experts" of 320, roughly twice. All of this pushes the plausible upper
end further against ROM, so it strengthens the direction; 1.04 as a floor and
`still_assumed` remain the honest call.

**A single `direction` label per entry is wrong for the energy domain.** All five
MAC entries were labelled `favours_gpu`, but the same op count is charged the same
J/op on both sides, so per-token arithmetic energy largely **cancels** in the ratio.
The real directions are per-gate and they conflict (A100 TDP gate moves *away* from
1.0; the failing HC1 gate moves *toward* closing), and at the DSV4-Pro batch-1
point the whole ladder is under 0.3% of ROM energy per token.

## 4.4 Arithmetic and citation errors that must not be copied forward

| claim | correction |
|---|---|
| "0.02 plus array efficiency 0.7 asserts 68.6% of a compute-in-ROM die is ROM cells" | Ignores the 18% that overhead + interconnect take first, additively. Correct: at most (1 − 0.18 − 0.02) × 0.7 = **56%** of die in ROM cells. Conclusion unaffected |
| "the modelled per-bit sweep rate is 7.4× below the anchor macro" | Uses the 0.75 derate to argue about the 0.75 derate. The mismatch is **5.5×**, falling to 2.46× if the capacity corrections land |
| "correcting the 14.3 label into an area ratio makes the number 3.8× too small" | **14.3× too small** (204.6 / 14.3); 3.8 is √14.3. The catch itself is correct and valuable |
| "a 64×32 macro holding 1,024 ternary weights" (Ankhdjet) | **2,048** ternary weights (32 per row at full 32-column sense); the bound is 10.6–53.5 µW/mm² at 130 nm, not 21.2–107 |
| "48 MB of L2 plus 57 MB of RF … 11–22% of the die" | 104 MiB = 872 Mbit at 10–20 Mbit/mm² = **5.3–10.6%**, moving the bracket to ~0.68–0.76 — so the recommended `range_high` of 0.72 is *below* the method's own midpoint. Also "48 MB of L2 on a full GA100" is not in the cited whitepaper (which states 40 MB for A100) |
| "the headline ROM design carries zero HBM stacks" | True only of the batch-1 SRAMKV winner. At every batch ≥ 16 the winner is the HBMKV design with 43 stacks per device. The asymmetry is **6.5×** (GPU 3,360 vs ROM 516), not infinite |
| "commonly quoted 8–15 mm²" is refuted folklore | Too strong — the measurement itself brackets 4.3 (I/O cell array only) to 20.4 mm² (whole strip), spanning that band |
| Kaitchup "is reasoning from the 2.5 kW server divided by ten" | His sentence runs the other way: "Power: reported around ~250W; **so** 10-card server at ~2.5kW". The conclusion survives on the correct ground — his 250 W is *unattributed*, not a division |
| "the 17 Taalas patents in the Google Patents assignee family" | Google Patents 503s to this environment; FreePatentsOnline returns **13**. Cite 13 or drop the count. Inventor names are **not** verifiable on that source — do not record them |
| "HBM3E stacks are widely described as an 11 × 11 mm footprint" | Unsourced. The conservatism argument, and therefore the `favours_gpu` direction label, rests on folklore. Honest direction: **unknown** |
| Yin et al. dated 2023 | JSSC vol. 59, no. 6, pp. 1912–1925, **2024** (the DOI is correct) |
| Pope PaLM 62B prefill 73% "on 64 chips" | **32 chips** |
| The Cerebras white paper "(Nov 2021)" | PDF CreationDate 2023-03-24; §8.1 discusses Andromeda, announced November 2022. The `111521` in the filename is not the document's date — cite by URL plus hash |
| CNX's "19.997 tokens/s" quoted unglossed | Almost certainly **19,997** — the same article writes "15,651 tokens/s" with a comma. Quoting it unglossed invites a reader to think the public demo ran at 20 tok/s |
| Jangam et al. ECTC 2017 SuperCHIPS Table III (300 ps interposer, 37–59 ps Si-IF) | **Could not be opened** by the verifier (escholarship returns HTTP 202 with an empty body). The conclusion it supports survives on Feng & Ma and the Tesla slide; that specific bracket line must not be written as if checked |
| "measured on an ~800 mm² TSMC 16 nm accelerator" (IPU) | Neither a die area nor a process node appears anywhere in the cited paper. That is public Graphcore product information, not this source |
| ROMA Fig. 2 "plots … at TSMC 7nm" | The figure carries **no node label**; the 7 nm attribution comes from surrounding text and TOM Table II, and should be stated that way |
| The YOLoC route to a 0.11 cell ratio | Its "16× smaller than a compact-rule 6T SRAM" implies a 0.224 µm² baseline, 1.76× this repo's own published 28 nm HD 6T of 0.127. The disagreement between 1/16 and 1/9.1 is a reason to distrust the whole YOLoC-cell route, not to pick an end of it — the *decision* not to use 0.11 as the point is right; the confidence attached to it as a bracket floor is not |
| "the model does not currently need a clock" (HC1) | `power.fabric_clock_hz` feeds `clock_energy_j_per_mm2_per_cycle` and therefore the HC1 **power** gate. The recommendation (leave the key absent) is right; the rationale is not |

---

# 5. INPUTS NOTHING READS

An unread input that carries a grade, a note, a source and a swept range is a trap
for the next reader. Naming them is the most durable thing this document does.

## 5.1 Entries with no consumer anywhere

Each was checked three ways: a scan of every string leaf of both committed study
artifacts (9,280 design points), a grep across `src/`, `tools/`, `compiler/`,
`runtime/`, `physical/`, `schemas/`, `spec/` and every other config, and a
perturbation run.

| entry | evidence | disposition |
|---|---|---|
| `links.inter_wafer.domain_size` | **Newly found — nobody had said so.** Re-running the whole n6_vs_a100 study at domain_size 2 / 4 / 16 / 64 changes **exactly one leaf** of the result tree: the reporting echo at `run_roofline_studies.py:2356`. `Technology.link_domain_size` is called from three places, none of which passes `inter_wafer`; `collective_traversals('inter_wafer', span)` returns 2.0 at every span for every value | Either wire it into the wafer `FabricPlan` (so a machine wider than one SwarmX domain pays a scale-out link), or **annotate it reporting-only**. A regression test pinning `collective_traversals` invariance under `domain_size` would keep it honest |
| `links.on_package.hop_latency_s` (and the whole `on_package` block) | Occurs at exactly one JSON path in each artifact — `link_latency_sensitivity[].scope_links[]`, the "joint" scope row filled by `sorted(technology.raw["links"])`. Never in `points[].link`, `points[].intra_link`, `designs[].topology.*`, `latency_crossovers[]` or `technology_derivations.link_plan`. Already pinned by `tests/test_roofline.py:1411` | Relabel as a placeholder with no consumer. Note that the 300 ns has **never been checked** and does not survive one: ~3× the only measured die-crossing figure (Tesla's 100 ns in-tile) and ~60× the on-wafer RDL hop |
| `links.ethernet.hop_latency_s` and `links.ethernet.bytes_s` | Same three-way check. Already stated in prose at `docs/WAFER_VERSUS_ARRAY_LATENCY.md:106`, but the config entries still look like modelling inputs | Delete the block, or label it in the entry itself rather than only in a document |
| `links.nvlink.*` | No study reads it; the one prefix match in the runner (`startswith("nvlink")`) filters real rows whose `intra_link` is `nvlink3`/`nvlink5`. Referenced nowhere in `docs/`. **But it is used 24 times in `tests/test_roofline.py`** as the link of synthetic `Topology` fixtures | Delete and repoint the fixtures at `nvlink5` **in the same change**, or keep it as an explicit test fixture and say so. Either way drop the marketing-blog citation |

**The trap in all four cases is the same:** the "joint" latency-sensitivity scope
prints every link name in the file whether or not anything charges it, so a reader
sees these listed beside constants that do real work.

## 5.2 Entries that are read but provably inert

A different class, worth naming so nobody spends evidence on them or reports a flat
sweep as robustness:

- **`kv.access_granularity_bytes.hbm` and `.sram`** —
  `kv_access_granularity_inflation` is exactly **1.0000 on all 4,688 points** in
  both studies, because every entry size in every profile (1024, 256, 4096, 0)
  divides both 32 and 128 exactly. The only non-dividing entry anywhere is
  Kimi-K3's 576 B gated-MLA entry, and Kimi-K3 is not in either study.
- **`kv.index_layout`** — contiguous and interleaved are **numerically identical**
  under every current profile; `REPORT.md` §4 prints 1.00× for all six model/store
  rows. The note's advertised 1.6× sensitivity contradicts the study's own output.
- **`efficiencies.expert_router_imbalance` at batch 1** — inert **structurally**,
  not merely empirically: `roofline.py:2765` clamps with
  `min(max(1.0, passes), effective_batch)`, and all 90 feasible per-region batch-1
  points show `rom_sweeps_per_step = 1.0`.
- **`efficiencies.hbm_capacity`** — excludes exactly 4 GPU points and 0 ROM-HBM
  points of 4,688.

## 5.3 The opposite failure: fields read differently than they are written

- **`reference_parts.taalas_hc1.power_w.range_high` is never read.**
  `taalas_hc1_power_anchor` reads `range_low` and `value` only, so an entry that
  presents a 200–250 W band actually reports [range_low, value]. See §4.1.
- **`weight_bits_per_parameter` is hard-coded downstream.**
  `tools/run_roofline_studies.py:926` computes
  `stored = model.total_parameters * 3.5 / BITS_PER_BYTE` and line 931 emits
  `"weight_bits_per_parameter": 3.5` into the floorplan-comparison artifact
  **without reading the config**. If the entry moves, this line silently will not.
- **The A100 weight-bound validation gate is a tautology.** `published_value`
  253.9145286845841 against `modelled_value` 253.91452868458407 — the same
  arithmetic to sixteen digits — because `roofline.py:3794` evaluates it under
  `technology.ideal()`, which forces every efficiency to 1.0. It is an arithmetic
  self-check, not a measurement, and **must never be quoted as evidence for
  `efficiencies.hbm_bandwidth`.**

---

# 6. The honest bottom line

**Thirty-six of the fifty-six config keys in this document remain `assumed` after
verification** — and that count is *after* the verifiers pushed eleven entries back
that the researchers had proposed upgrading. Three of the thirty-six feed nothing at
all (§5.1) and four more are provably inert at the headline operating point (§5.2),
which leaves roughly **twenty-nine live assumptions under the headline number**.

What genuinely moved off assumption: the Taalas batch size (published, and it is
the single fact the HC1 gate's PASS depends on), the HC1 transistor count and
throughput citations, the ROM and SRAM array densities at N6/N7, the GPU
floorplan's inclusiveness and four of its constants, the HBM beachfront and PHY
geometry, the HBM sequential bandwidth fraction, the KV access granularity, the
Cerebras SwarmX radix and domain size, and — for Qwen3 only — the per-layer array
pass count, which is now `executed`.

**The three that matter most, in order:**

1. **`links.infiniband_hdr.hop_latency_s`** (and its byte-identical NDR twin).
   Formally graded `published`, but it carries the wrong machine's number under the
   right machine's name, and the headline is near-linear in it: **6.08× at 2.03 µs
   to 24.24× at 22 µs**, against 8.328× today. Twenty-six of thirty-two headline
   rows move with it. Nothing else in the model comes close, and the honest output
   of fixing it is a much wider reported band, not a new point.

2. **`latency.pipeline_fill_drain_s`.** 32 ns assumed, 57% of the fixed per-layer
   budget, with a defensible band of 16 ns to 511 ns — a **32× span** — because the
   model never declares whether its array is systolic (2N−1 drain) or a CIM macro
   with an adder tree (log₂ lanes). At the top of that band it breaks the Taalas
   HC1 validation gate (~0.19× against a 2× tolerance). One architectural sentence
   in the design would collapse it.

3. **`energy.mac_energy_j_per_op.w4a8`.** **99.94% of the headline model's
   operations run on the one rung with no source of any kind** — an arithmetic mean
   of two entries that are themselves anchored on a control/datapath split shown
   not to be physical. It moves under 0.3% of energy per token today, so it is not
   a throughput risk; it is the reason no energy-per-token figure from this model
   should be quoted, which is what `METHODOLOGY` §7a already says for a different
   reason.

Two runners-up deserve a line. **`rom.cim_precompute_area_fraction`** sits at 0.02
while the model charges a compute-in-ROM die *nothing* for summing its partial
products — a defect visible in this repository's own source, not in any paper. And
the **ROM capacity-density quotient** (§2.2) is the largest correction found in the
whole survey at 2.243×, but its sign on the headline is genuinely unknown until
someone re-runs it and diffs the binding-constraint census, because it costs the
ROM side exactly as much on capacity as it gains on the sweep floor.

A program that knows exactly which of its inputs are guesses is in a far better
position than one that does not. This is that list. It is longer than anyone would
like, and every entry on it now says what single measurement or document would take
it off.
