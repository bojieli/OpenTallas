# Contributor tasks

Concrete, scoped work, taken from the documents that define each gap. Every task
below names the document that specifies it, so you can read the acceptance
criteria before writing code.

This index exists because the specification documents are dense and a newcomer
cannot tell from a filename which ones contain open work. **67 of the 69
documents in `docs/` name at least one actionable task.** These are the ones that
are self-contained enough to start on.

Read [`../STATUS.md`](../STATUS.md) first for what passes and what fails, and
[`../CONTRIBUTING.md`](../CONTRIBUTING.md#areas) for how to submit.

Difficulty is a rough guide, not a promise:
**S** = a focused change · **M** = a few days · **L** = a research effort.

---

## Open questions where the project might be wrong

These matter more than any feature. If one of them resolves against the design,
that is a more valuable contribution than making a number bigger.

| # | Task | Size | Specified in |
|---|---|---|---|
| 1 | **Resolve the 24× model disagreement (gate C3).** The analytical model says ROM is 5.05× faster than the HBM comparator for Qwen3-8B/8K; the cycle model says 0.179× — 5.6× *slower*. The cycle model reproduces the comparator to 1.5% and is 28.7× apart on the subject, and ~90% of the ROM cycle step is unattributed to any measured term. Either model could be wrong. | L | `results/derived/qwen3_n5_design_target_reconciliation.json` |
| 2 | **Take a side on the compute-in-ROM fork, with evidence.** Compute-in-ROM costs up to 20.71× of aggregate throughput at batch 256 against A100 and 28.5× against B200. §5 frames this as a live architecture question rather than a settled one. | L | `ANALYTICAL_REPORT.md` §5 |
| 3 | **Attribute the 1-in-1,024 compressor mismatch.** Official `0x3d08` vs target `0x3d09` at flat index 672. One bit, reproducible. | S | `DEEPSEEK_V4_COMPRESSOR_EVIDENCE.md` |
| 4 | **Calibrate ASAP7 against a foundry node.** Every frequency and density figure in this project is routed on ASAP7, a predictive and explicitly non-manufacturable PDK, and has no calibrated error bar against TSMC N7 — while the comparator (A100) is fabricated N7 silicon. Route any one of the redesigned blocks on a foundry 7 nm or 5 nm kit and publish **the ratio** to the ASAP7 result; the ratio is publishable even where the PDK is not, and one such ratio calibrates every figure here at once. The cheaper partial version is **already done for three changes** -- all reproduce on SKY130 within 1.28x, with area ratios matching to 0.01 (`audit_cross_node_reproducibility.py`) -- so what remains is the foundry ratio itself, plus extending the second-node check to the compute unit, which needs a SKY130 SRAM macro swap. | L | `ASAP7_PHYSICAL.md` "Why the comparison is ASAP7 against N7 silicon" |
| 5 | **Put a power and thermal budget on the comparison.** The A100 sustains 312 TFLOP/s inside 400 W. Nothing in this project is power-constrained, and a design that ignores power can always win on area — so this is plausibly the largest unmodelled term in the density comparison. Fully reachable with open tools. | M | `audit_chip_level_density.py` refusal `no-power-or-thermal-limit` |
| 6 | **Attribute three BF16 sparse-attention differences** at flattened output indices 5,066 / 5,651 / 6,124 — Tensor Core MMA association order, or something else? | M | `DEEPSEEK_V4_SPARSE_ATTENTION_EVIDENCE.md` |
| 7 | **Retire an `assumed` input.** §9 defines exactly what turns `assumed` into `measured`: raw artifact, command, tool version, config, unit conversion, uncertainty, reproduction check. Anyone with the relevant hardware can close one. | M | `ASSUMPTIONS.md` §9, priorities in `ANALYTICAL_REPORT.md` Part D |

---

## Physical design, PDKs and constraints

The weakest link in the project's claims. ASAP7 is predictive and
non-manufacturable; there is no foundry PDK and no signoff.

| # | Task | Size | Specified in |
|---|---|---|---|
| 8 | **Place one SRAM macro.** Both proven physical blocks contain *zero* macros, while the installed SKY130 full PDK has real `sky130_sram_macros` and IHP SG13G2 has `sg13g2_sram`. A self-contained first physical result. | M | `ABI3_PHYSICAL_VIEWS.md` §7 |
| 9 | **Pipeline the proxy RTL and re-measure.** The unpipelined one-cycle proxies close at only 243 / 84 / 455 MHz, which falsifies the 0.8–1.1 GHz whole-product clock assumption used in system envelopes. The document names this as the prerequisite for *any* frequency entering a performance claim. | M | `ASAP7_PHYSICAL.md` |
| 10 | **Add a numeric format case.** The campaign covers a 16-lane signed-integer dot product, a 64-term scaling point and an 8-source tagged reduction — and explicitly *not* the target MXFP4×FP8, FP8×FP8, BF16, FP4-index or FP32 datapaths. Each case has an existing acceptance list. | M | `ASAP7_PHYSICAL.md` |
| 11 | **Port the physical campaign to another open PDK.** SKY130 and IHP SG13G2 roots already exist; `tools/bootstrap_*_pdk.sh` shows the expected shape. | L | `OPEN_PDK_SELECTION.md`, `ROM_PHYSICAL_METHODOLOGY.md` |
| 12 | **Reconcile the two-library timing path.** §3.3 records that the P&R lane does not read the local ASAP7 liberty, so synthesis/STA and P&R are timed against *different* libraries. A bounded flow fix. | S | `ABI3_PHYSICAL_VIEWS.md` §3.3 |
| 13 | **Question the slew constraint.** The g2 cluster does not close at 4.75 ns at any utilisation from 20 to 40 — max-slew violations bottom at 3 near util 35 then rise, and util 40 introduces the sweep's first hold failures. The open question is whether the constraint itself is right. | M | `tools/audit_g2_cluster_operating_point.py` |
| 14 | **Route the uncharacterised blocks.** Partly done: 8 now have clean-tree synth+STA records under `results/physical_abi3/asap7/engine_blocks/`. What remains is **place-and-route** for those 8, and synth for `ot_a3_vector_rms_norm`, `ot_a3_vector_rope`, `ot_a3_vector_silu_mul` (deeper submodule chains). | M | `ABI3_ENGINE_DATAPATH_RTL.md` §5.3 |
| 12c | **Pipeline the floating-point primitives — the single biggest frequency lever, now measured end to end.** `fp32_add_rne` is 174 MHz unpipelined through a 524-bit exact intermediate and caps every block that calls it. A pipelined BF16 MAC with carry-save accumulation and a split resolve measures **1,469 MHz at 0.681 ns in roughly half the cells** — **8.4×**. The node is not the limit: a trivial flop-to-flop path measures 8,691 MHz here. See [DATAPATH_PIPELINE_REDESIGN.md](DATAPATH_PIPELINE_REDESIGN.md) for the precision table, array sizing and migration order, and `rtl/proto/ot_mac_bf16_fp32_pipe.sv` for the measured prototype. **Note the fairness constraint:** the HBM comparator must be modelled at the same fidelity, or gate C2 becomes meaningless. | L | `DATAPATH_PIPELINE_REDESIGN.md` |
| 12a | **Explain `ot_a3_vector_hadamard`'s frequency.** It synthesises at **3.6 MHz** — two orders of magnitude below the 280.9 MHz the g2 cluster reaches — with 119,841 cells and 16,259 µm². Either the block needs pipelining or its combinational depth is a design error. Nothing in the design can run at 3.6 MHz. | M | `results/physical_abi3/asap7/engine_blocks/` |
| 12b | **Fix the non-synthesizable loop bound in `rtl/ot_fp32_rne_pkg.sv:614`.** `for (bit_index = 0; bit_index < shift_distance-1; ...)` where `shift_distance` is a *variable* assigned `117` two lines above — Yosys rejects the non-constant bound, and `ot_a3_vector_compress_project` and `ot_a3_vector_index_score` therefore cannot synthesise at all. Verified: replacing the bound with the literal `116` makes both synthesise (67.2 MHz / 82.2 MHz). **But the change stales 34 artifacts that bind this package**, including hour-long physical routes, so it needs the cascade re-taken in the same change. An identical loop two lines above already uses a literal. | S fix, L cascade | measured, this session |

---

## RTL and verification

| # | Task | Size | Specified in |
|---|---|---|---|
| 15 | **Flip `MAPPED_FAMILIES_WORD`.** One literal `0` (case-record word 59) fail-stops the integrated vehicle at PC 32 / `DMA.SCATTER` / trap class 4 and blocks **four rungs** (G1a–G1d). Flipping it is trivial; producing golden past it is the work, costed in MACs — the LM head alone is 622,329,856 MACs (~5.7 h whole, ~1.4 h sharded), and the head is separately refused above 4,096 weight rows. | L | `../STATUS.md`, `tools/build_abi3_shipped_prefix_vectors.py` |
| 16 | **Re-take G1e.** The cheapest structural fix on the board: ~586 s per store, ~1,169 s both. Converts the only green G1 rung from passing-on-stale-evidence to actually passing, and it feeds G1c and the composition certificate. | S | `../STATUS.md` |
| 17 | **Close whole-destination write atomicity** for `TENSOR.MATMUL` and `VECTOR.ADD`, which today stop at the first faulting output instead of validating before writing. Six VECTOR blocks already do it correctly — copy the pattern. | M | `ABI3_ENGINE_DATAPATH_RTL.md` |
| 18 | **Wire the next operator boundary** into the shipped-prefix campaign: Qwen `VECTOR.ROPE` at PC 26, DeepSeek HBM `VECTOR.MHC` at PC 14. | M | `ABI3_ENGINE_DATAPATH_RTL.md` |
| 19 | **Implement row folding in integrated RTL** so no padded logical row performs work, and make resolved extents, edge masks, lane valids and addresses agree across compiler, functional simulator, cycle model, checker *and* RTL — agreement is currently claimed only for the first three. | L | `ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md` §5.3, §11, §14 |
| 20 | **Extend the HC_PRE arithmetic to T=5.** A numbered five-step plan; step 2 is the tractable one, against an already-authenticated corpus. | M | `DEEPSEEK_V4_HC_PRE_ARITHMETIC_RTL_EVIDENCE.md` |
| 21 | **Extend the tile campaign to the full block sequence.** It runs one T=512 and one T=320 block and does not claim all 391 blocks of the 200,000-token partition. | M | `DEEPSEEK_V4_HC_PRE_TILE_RTL_EVIDENCE.md` |
| 22 | **Make the KV check-and-successor operation atomic** between independently scheduled service requests. The document names this hole in one sentence. | M | `DEEPSEEK_V4_KV_WINDOW_EVIDENCE.md` |

---

## Simulation, correctness and reference models

| # | Task | Size | Specified in |
|---|---|---|---|
| 23 | **Reproduce or refute the TileLang FP4 bug.** The released `fp4_gemm` gives max absolute error 6.52 against a signal of mean magnitude 1.28 on sm_120, confirmed against two independent references — so any routed-expert run through TileLang FP4 on that architecture is silently wrong, producing fluent but semantically empty output. Re-run on other GPU architectures, or fix the kernel. | M | `ABI3_PROGRAM_REPORT.md` §4 |
| 24 | **Chunk the 200K prefill.** `hc_post`'s 48.8 GiB binary32 intermediate is allocated twice per layer across 43 layers, and the unchunked indexer score tensor is 2.33 TiB. Chunked, the document estimates ~58 s. | M | `ABI3_PROGRAM_REPORT.md` §4 |
| 25 | **Reach a sparsity threshold.** No current accelerator run reaches any sparsity threshold — the successful governed HBM record reaches context 35. This is the clearest single blocking task in the DeepSeek family. | L | `DEEPSEEK_SPARSE_ATTENTION_GATE.md` |
| 26 | **Build a nonzero DSpark conditioning corpus.** The document states flatly that no checkpoint-derived one exists. | M | `DEEPSEEK_V4_DSPARK_PREFILL_KV_EVIDENCE.md` |
| 27 | **Stream a complete LM head.** `runtime/service_engine/lm_head_numeric.py` intentionally accepts at most 20 evidence rows; raise it to the complete vocabulary. | M | `DEEPSEEK_V4_LM_HEAD_EVIDENCE.md` |
| 28 | **Build a nonzero-temperature replay harness.** The Markov reference is greedy/explicit-entropy only and disclaims exact nonzero-temperature replay. | M | `DEEPSEEK_V4_MARKOV_LOOP_EVIDENCE.md` |
| 29 | **Extend the interacting-operator differential** past its 30 cases to stress circular-wrap behaviour. | S | `DEEPSEEK_V4_ATTENTION_KV_VIEW_EVIDENCE.md` |
| 30 | **Break the extent-corpus token monoculture.** The locked corpus repeats one authentic token (ID 19,923, `Hello`) at T=1,2,3,4, which the document flags itself. | S | `DEEPSEEK_V4_HC_PRE_EVIDENCE.md` |

---

## Infrastructure

| # | Task | Size | Specified in |
|---|---|---|---|
| 31 | **Cap the test-suite memory footprint.** `tests/runtime/test_abi3_cycle.py` measures 72–84 GB peak RSS, so the group is OOM-killed and cannot run in CI (a hosted runner has ~7 GB). `pytest-forked`, per-file invocation, or a smaller fixture. Pairwise runs already ruled out shared module-level state — do **not** look there. | M | `.github/workflows/README.md` |
| 32 | **Pay down the drift backlog.** 59 of 91 artifacts that pin source digests no longer bind current sources. `runtime/abi3/constants.py` alone invalidates 21. Re-taking a family together is far cheaper than one at a time; costs are recorded in each artifact. | M | `python3 tools/audit_source_currency_drift.py` |
| 33 | **Decide what G2 asserts.** Its evaluator never reads `design.closed`, and the record it cites reports `closed: false`. Either the evaluator should check closure, or the claim should say what it actually checks. | S | `../STATUS.md` |
| 34 | **Fix the D4 baseline.** `results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json` carries `worktree_dirty: true` and one drifted source, so by the project's own admissibility rule it should not serve as a baseline — and it is never tested against that rule. | S | `../STATUS.md` |

---

## DeepSeek-V4.1-Flash, the three newest targets (plan TA-DS41-3.0)

Registered 2026-09-13. Nothing in this family has produced a token yet, so every
task here is upstream of any V4.1 number. Read
[`DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`](DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md)
first: it names the file, the test and the make target for each work package, and
checklist section W14 records which gate each task belongs to.

| # | Task | Size | Specified in |
|---|---|---|---|
| 35 | **Emit the V4.1 Kernel IR.** The front end carries the profile, the CSA2 mode sequence, the lowering plan and a 3,131-kernel census, and the checkpoint lock resolves all 96,085 tensor specs — but the node-by-node lowering is not written, so `tools/build_deepseek_v4_kernel_ir_v3.py --model deepseek-v4.1-flash` refuses and there is no `graph_id`. Every deployment, capability, cost table and comparison contract downstream is unbindable until this exists; it is the single highest-fan-out gap in the family. | L | plan §13 WP-D, gate DS41-I2 |
| 36 | **Derive the TA-DS41-HBM node count.** The comparator is the model-blind chip replicated until the HBM-resident weights plus the session KV fit, with the Engram tables in host memory. Both storage-class comparison contracts carry a null node count and the derivation rule beside it, and publish no ratio at all until it is a number — a placeholder here would become the denominator of every per-node figure. | M | plan §3.3, `configs/abi3/comparison_contracts/deepseek_v41_*_vs_hbm_cluster_v1.json` |
| 37 | **Measure the three KV entry widths.** The main latent at 288 B, the index key at 68 B and the window at 528 B are read off the released code and the technical report. For DeepSeek-V4 the measured width differed from the recipe by 1.8×, and the iso-node advantage moves with the KV read, so this is the measurement most likely to change a headline. | M | plan §14 risk 1, gate DS41-X4 |
| 38 | **Give the HBM comparator a die area, or prove no comparison may divide by one.** No artifact in this repository states the die area of the shared conventional accelerator chip, so the V4 array-versus-HBM comparison already records `hbm declares no geometry` and publishes no area ratio. The iso-area rule needs both sides; either produce the number from a physical record or establish formally that the HBM side's denominator is unavailable and what may be published without it. | L | plan §11, `results/abi3/comparison_deepseek_rom_array_vs_hbm.json#silicon` |
| 39 | **Print each ratio beside its binding constraint and its resident-session count.** `tools/build_comparison_report.py` emits neither field and does not read a comparison contract at all, so gate DS41-CMP11's central requirement has nowhere to live in the artifact. The three V4.1 contracts declare the requirement, the field names and the analytical antecedents; the tool has to honour them, and the gate cannot close until it does. | S | plan gate DS41-CMP11, the contracts' `reporting` block |
| 40 | **Add the V4.1 ladder as a second workload binding on the G1 board.** `configs/gates/redesign_gates.json` and `tools/check_redesign_gates.py` are bound to Qwen. The board must report a V4.1 rung *beside* Qwen's rather than in place of it, and a V4.1 rung must be able to fail on its own. | M | plan §13 WP-L, §14 risk 8 |
| 41 | **Finish the five new blocks on both technology views and derive cost tables v3.** The five AM-E10 blocks have ASAP7 routed records; SKY130 is incomplete and `configs/hardware/abi3_cost_{wafer,rom_array}_v3.json` do not exist, so the cycle model still reads v2 tables in which all five blocks are unpriced. | M | plan §11 and §13 WP-M, gate DS41-PHY10 |

---

## Picking something up

There is no issue tracker convention yet. Open a GitHub issue naming the task
number and the document, say what you intend to produce as evidence, and check
that nobody else has claimed it.

Two norms specific to this project:

- **Evidence, not assertions.** A change to a number needs the artifact that
  produces it, and `make check-figures` must pass. See
  `../CONTRIBUTING.md#generated-artifacts`.
- **Say what you did not check.** The documents here are unusually explicit
  about their own limits, and that is the standard to hold. "I did not verify X"
  is always an acceptable thing to write in a pull request.
