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
| 2 | **Take a side on the compute-in-ROM fork, with evidence.** Compute-in-ROM costs up to 20.71× of aggregate throughput at batch 256 against A100 and 28.5× against B200. §5 frames this as a live architecture question rather than a settled one. | L | `COMPUTE_IN_ROM_MECHANISM.md` §5 |
| 3 | **Attribute the 1-in-1,024 compressor mismatch.** Official `0x3d08` vs target `0x3d09` at flat index 672. One bit, reproducible. | S | `DEEPSEEK_V4_COMPRESSOR_EVIDENCE.md` |
| 4 | **Attribute three BF16 sparse-attention differences** at flattened output indices 5,066 / 5,651 / 6,124 — Tensor Core MMA association order, or something else? | M | `DEEPSEEK_V4_SPARSE_ATTENTION_EVIDENCE.md` |
| 5 | **Retire an `assumed` input.** §9 defines exactly what turns `assumed` into `measured`: raw artifact, command, tool version, config, unit conversion, uncertainty, reproduction check. Anyone with the relevant hardware can close one. | M | `ASSUMPTIONS.md` §9, priorities in `COMPARISON_FAIRNESS_AUDIT.md` Part D |

---

## Physical design, PDKs and constraints

The weakest link in the project's claims. ASAP7 is predictive and
non-manufacturable; there is no foundry PDK and no signoff.

| # | Task | Size | Specified in |
|---|---|---|---|
| 6 | **Place one SRAM macro.** Both proven physical blocks contain *zero* macros, while the installed SKY130 full PDK has real `sky130_sram_macros` and IHP SG13G2 has `sg13g2_sram`. A self-contained first physical result. | M | `ABI3_PHYSICAL_VIEWS.md` §7 |
| 7 | **Pipeline the proxy RTL and re-measure.** The unpipelined one-cycle proxies close at only 243 / 84 / 455 MHz, which falsifies the 0.8–1.1 GHz whole-product clock assumption used in system envelopes. The document names this as the prerequisite for *any* frequency entering a performance claim. | M | `ASAP7_PHYSICAL.md` |
| 8 | **Add a numeric format case.** The campaign covers a 16-lane signed-integer dot product, a 64-term scaling point and an 8-source tagged reduction — and explicitly *not* the target MXFP4×FP8, FP8×FP8, BF16, FP4-index or FP32 datapaths. Each case has an existing acceptance list. | M | `ASAP7_PHYSICAL.md` |
| 9 | **Port the physical campaign to another open PDK.** SKY130 and IHP SG13G2 roots already exist; `tools/bootstrap_*_pdk.sh` shows the expected shape. | L | `OPEN_PDK_SELECTION.md`, `ROM_PHYSICAL_METHODOLOGY.md` |
| 10 | **Reconcile the two-library timing path.** §3.3 records that the P&R lane does not read the local ASAP7 liberty, so synthesis/STA and P&R are timed against *different* libraries. A bounded flow fix. | S | `ABI3_PHYSICAL_VIEWS.md` §3.3 |
| 11 | **Question the slew constraint.** The g2 cluster does not close at 4.75 ns at any utilisation from 20 to 40 — max-slew violations bottom at 3 near util 35 then rise, and util 40 introduces the sweep's first hold failures. The open question is whether the constraint itself is right. | M | `tools/audit_g2_cluster_operating_point.py` |
| 12 | **Route the uncharacterised blocks.** `ot_a3_mac_lane` and the six new VECTOR blocks have no physical characterisation at all. | M | `ABI3_ENGINE_DATAPATH_RTL.md` §5.3 |

---

## RTL and verification

| # | Task | Size | Specified in |
|---|---|---|---|
| 13 | **Flip `MAPPED_FAMILIES_WORD`.** One literal `0` (case-record word 59) fail-stops the integrated vehicle at PC 32 / `DMA.SCATTER` / trap class 4 and blocks **four rungs** (G1a–G1d). Flipping it is trivial; producing golden past it is the work, costed in MACs — the LM head alone is 622,329,856 MACs (~5.7 h whole, ~1.4 h sharded), and the head is separately refused above 4,096 weight rows. | L | `../STATUS.md`, `tools/build_abi3_shipped_prefix_vectors.py` |
| 14 | **Re-take G1e.** The cheapest structural fix on the board: ~586 s per store, ~1,169 s both. Converts the only green G1 rung from passing-on-stale-evidence to actually passing, and it feeds G1c and the composition certificate. | S | `../STATUS.md` |
| 15 | **Close whole-destination write atomicity** for `TENSOR.MATMUL` and `VECTOR.ADD`, which today stop at the first faulting output instead of validating before writing. Six VECTOR blocks already do it correctly — copy the pattern. | M | `ABI3_ENGINE_DATAPATH_RTL.md` |
| 16 | **Wire the next operator boundary** into the shipped-prefix campaign: Qwen `VECTOR.ROPE` at PC 26, DeepSeek HBM `VECTOR.MHC` at PC 14. | M | `ABI3_ENGINE_DATAPATH_RTL.md` |
| 17 | **Implement row folding in integrated RTL** so no padded logical row performs work, and make resolved extents, edge masks, lane valids and addresses agree across compiler, functional simulator, cycle model, checker *and* RTL — agreement is currently claimed only for the first three. | L | `ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md` §5.3, §11, §14 |
| 18 | **Extend the HC_PRE arithmetic to T=5.** A numbered five-step plan; step 2 is the tractable one, against an already-authenticated corpus. | M | `DEEPSEEK_V4_HC_PRE_ARITHMETIC_RTL_EVIDENCE.md` |
| 19 | **Extend the tile campaign to the full block sequence.** It runs one T=512 and one T=320 block and does not claim all 391 blocks of the 200,000-token partition. | M | `DEEPSEEK_V4_HC_PRE_TILE_RTL_EVIDENCE.md` |
| 20 | **Make the KV check-and-successor operation atomic** between independently scheduled service requests. The document names this hole in one sentence. | M | `DEEPSEEK_V4_KV_WINDOW_EVIDENCE.md` |

---

## Simulation, correctness and reference models

| # | Task | Size | Specified in |
|---|---|---|---|
| 21 | **Reproduce or refute the TileLang FP4 bug.** The released `fp4_gemm` gives max absolute error 6.52 against a signal of mean magnitude 1.28 on sm_120, confirmed against two independent references — so any routed-expert run through TileLang FP4 on that architecture is silently wrong, producing fluent but semantically empty output. Re-run on other GPU architectures, or fix the kernel. | M | `ABI3_PROGRAM_REPORT.md` §4 |
| 22 | **Chunk the 200K prefill.** `hc_post`'s 48.8 GiB binary32 intermediate is allocated twice per layer across 43 layers, and the unchunked indexer score tensor is 2.33 TiB. Chunked, the document estimates ~58 s. | M | `ABI3_PROGRAM_REPORT.md` §4 |
| 23 | **Reach a sparsity threshold.** No current accelerator run reaches any sparsity threshold — the successful governed HBM record reaches context 35. This is the clearest single blocking task in the DeepSeek family. | L | `DEEPSEEK_SPARSE_ATTENTION_GATE.md` |
| 24 | **Build a nonzero DSpark conditioning corpus.** The document states flatly that no checkpoint-derived one exists. | M | `DEEPSEEK_V4_DSPARK_PREFILL_KV_EVIDENCE.md` |
| 25 | **Stream a complete LM head.** `runtime/service_engine/lm_head_numeric.py` intentionally accepts at most 20 evidence rows; raise it to the complete vocabulary. | M | `DEEPSEEK_V4_LM_HEAD_EVIDENCE.md` |
| 26 | **Build a nonzero-temperature replay harness.** The Markov reference is greedy/explicit-entropy only and disclaims exact nonzero-temperature replay. | M | `DEEPSEEK_V4_MARKOV_LOOP_EVIDENCE.md` |
| 27 | **Extend the interacting-operator differential** past its 30 cases to stress circular-wrap behaviour. | S | `DEEPSEEK_V4_ATTENTION_KV_VIEW_EVIDENCE.md` |
| 28 | **Break the extent-corpus token monoculture.** The locked corpus repeats one authentic token (ID 19,923, `Hello`) at T=1,2,3,4, which the document flags itself. | S | `DEEPSEEK_V4_HC_PRE_EVIDENCE.md` |

---

## Infrastructure

| # | Task | Size | Specified in |
|---|---|---|---|
| 29 | **Cap the test-suite memory footprint.** `tests/runtime/test_abi3_cycle.py` measures 72–84 GB peak RSS, so the group is OOM-killed and cannot run in CI (a hosted runner has ~7 GB). `pytest-forked`, per-file invocation, or a smaller fixture. Pairwise runs already ruled out shared module-level state — do **not** look there. | M | `.github/workflows/README.md` |
| 30 | **Pay down the drift backlog.** 59 of 91 artifacts that pin source digests no longer bind current sources. `runtime/abi3/constants.py` alone invalidates 21. Re-taking a family together is far cheaper than one at a time; costs are recorded in each artifact. | M | `python3 tools/audit_source_currency_drift.py` |
| 31 | **Decide what G2 asserts.** Its evaluator never reads `design.closed`, and the record it cites reports `closed: false`. Either the evaluator should check closure, or the claim should say what it actually checks. | S | `../STATUS.md` |
| 32 | **Fix the D4 baseline.** `results/physical_abi3/asap7/matmul_bf16_sram_engine/pnr.json` carries `worktree_dirty: true` and one drifted source, so by the project's own admissibility rule it should not serve as a baseline — and it is never tested against that rule. | S | `../STATUS.md` |

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
